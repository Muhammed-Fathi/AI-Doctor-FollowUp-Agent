"""Doctor verification of extracted facts, and the atomic mapping transaction.

Two invariants from the contracts live here, and both are enforced in the
database as well as in code:

1. **Append-only.** A fact has at most one decision. A second decision on the
   same fact returns ``409 E_FACT_ALREADY_DECIDED`` — *including* an identical
   repeated decision (owner decision D-11). Nothing is silently re-accepted.
2. **Atomic lineage.** When a decision makes a fact promotable, the
   ``fact_verification`` row and the derived ``observation`` are written in the
   same app-DB transaction, so a crash cannot leave one without the other
   (``DATA_DICTIONARY.md`` §3.3 rule 6).

The doctor-only rule is enforced by the calling route (``require_doctor``), by
this service, *and* by a ``BEFORE INSERT`` trigger installed by migration 0003
(owner decision D-07). No layer alone is load-bearing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, utc_now
from app.core.config import get_settings
from app.core.enums import (
    DocumentStatus,
    FactField,
    FactVerificationStatus,
    QualityFlag,
    ValidationState,
    VerificationDecision,
)
from app.core.errors import (
    FACT_ALREADY_DECIDED_DETAIL,
    VI_004_UNRESOLVED_DETAIL,
    ApiError,
    ErrorCode,
    document_error,
)
from app.db.models import Document, ExtractedFact, FactVerification, Observation
from app.services.documents import quality
from app.services.documents.field_parser import normalize_corrected_value
from app.services.documents.mapping import (
    MappingDecision,
    VerifiedFactView,
    decide_mapping,
    measured_at_for,
)

#: Neutral detail reused for every "already decided" case (D-11).
_ALREADY_DECIDED = FACT_ALREADY_DECIDED_DETAIL

#: Terminal failure codes for a document whose facts a doctor rejected
#: (R21 §4.1). ``all_facts_rejected`` keeps its existing meaning and precedence;
#: the two new codes describe the *partial* rejection that used to be silent.
#:
#: These are enum-like tokens stored in ``document.failure_code``, never document
#: text, so they are safe to expose to the owning patient in Stage 3 (§4.9).
FAILURE_ALL_FACTS_REJECTED = "all_facts_rejected"
FAILURE_MEASUREMENT_REJECTED = "measurement_rejected"
FAILURE_FACT_REJECTED = "fact_rejected"

#: Promotion reason returned when the document is not ``verified`` (R21 §4.2).
_REASON_NOT_VERIFIED = "document_not_verified"

#: Neutral detail for a correction that is not admissible for its own field.
#: Says what is wrong without quoting the document or the rejected input.
_INADMISSIBLE_CORRECTION = (
    "A corrected value must be admissible for the field being corrected "
    "(a number for a measurement, an ISO date for a report date, "
    "a documented unit for a unit)."
)


@dataclass(frozen=True, slots=True)
class VerificationOutcome:
    """The result of one doctor decision.

    ``fact`` is the **decided** fact: for a correction that is the new verified
    row, not the superseded original, so a caller renders the accepted value
    without a second read. ``superseded_fact_id`` names the original when a
    correction created one, keeping both ends of the lineage reachable.
    """

    #: Always the fact that is now current: the decided fact, or — for a
    #: correction — the new verified row that supersedes it. Never ``None``, so the
    #: response keeps the contract's required ``fact``.
    fact: ExtractedFact
    verification: FactVerification
    document_status: str
    observation_created: bool
    mapped_reason: str | None
    superseded_fact_id: str | None = None


def _existing_decision(db: Session, fact_id: str) -> FactVerification | None:
    """Return the first recorded decision for ``fact_id``, if any."""
    return db.execute(
        select(FactVerification)
        .where(FactVerification.fact_id == fact_id)
        .order_by(FactVerification.decided_at)
        .limit(1)
    ).scalar_one_or_none()


def _document_fact_views(db: Session, document_id: str) -> list[VerifiedFactView]:
    """Return the *active* facts of ``document_id`` as mapping views.

    **R06:** a superseded original (``rejected`` because a correction replaced it)
    is deliberately absent. ``decide_mapping`` only reads ``verified`` facts, so
    leaving it out changes nothing for it — but the same helper feeds the anchor
    logic, and counting a replaced reading as a second measurement tuple is what
    broke parsing after a correction.
    """
    rows = db.execute(
        select(ExtractedFact)
        .where(
            ExtractedFact.document_id == document_id,
            ExtractedFact.verification_status != FactVerificationStatus.REJECTED.value,
        )
        .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
    ).scalars()
    return [
        VerifiedFactView(
            field_name=row.field_name,
            normalized_value=row.normalized_value,
            unit=row.unit,
            verification_status=row.verification_status,
        )
        for row in rows
    ]


def _blocking_facts_remaining(db: Session, document_id: str) -> int:
    """Return the number of facts still ``pending`` for ``document_id``."""
    rows = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == document_id,
            ExtractedFact.verification_status == FactVerificationStatus.PENDING.value,
        )
    ).scalars()
    return len(list(rows))


def _unread_measurement_blocks_verification(db: Session, document_id: str) -> bool:
    """Return ``True`` when a measurement was declared but never successfully read.

    **P3-R17.** ``verified`` used to be reachable from "every fact row is decided
    and at least one is verified". That is wrong for a document whose ``Value:``
    line the parser could not attribute: the date and reference range could be
    approved and the document became ``verified`` carrying no measurement at all.
    Measured on the owner's real Windows OCR at ``1b17a9a``.

    The parser now preserves such a line as a ``value`` fact flagged
    ``page_missing`` (``field_parser._unattributed_value_facts``), so the
    declaration survives in the database and this rule can be evaluated on every
    later read without storing page text.

    The document stops being blocked once a **verified value fact carrying a
    normalized number** exists — which is exactly what a doctor correction
    produces. Rejecting or acknowledging the unread line is not enough, because
    the measurement itself is still unknown.

    A superseded original is ignored: after a correction the history row keeps
    its flag for audit, but it no longer describes the document's current state.
    """
    facts = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document_id)).scalars()
    )
    superseded = quality.superseded_fact_ids(facts)
    declared = [
        fact
        for fact in facts
        if fact.field_name == FactField.VALUE.value
        and fact.id not in superseded
        and QualityFlag.PAGE_MISSING.value in quality.decode_flags(fact.quality_flags)
    ]
    if not declared:
        return False
    return not any(
        fact.field_name == FactField.VALUE.value
        and fact.verification_status == FactVerificationStatus.VERIFIED.value
        and fact.normalized_value is not None
        for fact in facts
    )


def _active_rejected_facts(facts: list[ExtractedFact], superseded: set[str]) -> list[ExtractedFact]:
    """Return the rejected facts that still describe the document's state.

    A **plain** rejection is active: it is a doctor's verdict about a current
    reading, and it must never be able to coexist with ``verified`` (R21 §4.1).
    A rejection that a correction superseded is *history* — the corrected row is
    the document's current value — so it is excluded, which is what keeps a valid
    first-decision correction able to reach ``verified`` (``R09``).
    """
    return [
        fact
        for fact in facts
        if fact.verification_status == FactVerificationStatus.REJECTED.value
        and fact.id not in superseded
    ]


def _rejection_failure_code(active_rejected: list[ExtractedFact]) -> str:
    """Return the terminal code for a document with active rejections.

    Rejecting the ``value`` is the case the patient needs to understand: the
    reading itself was refused, so no measurement can come from this document.
    Any other field is a narrower, non-measurement rejection.
    """
    if any(fact.field_name == FactField.VALUE.value for fact in active_rejected):
        return FAILURE_MEASUREMENT_REJECTED
    return FAILURE_FACT_REJECTED


def _recompute_document_status(db: Session, document: Document) -> str:
    """Derive and store the document status from its facts.

    ``verified`` requires every blocking fact decided, at least one fact verified,
    **and** no declared-but-unread measurement (R17).

    **Rejection-first terminal rule (R21 §4.1).** Any *active* rejected fact — one
    that no correction superseded — makes the document terminally ``failed``,
    **even while sibling facts are still pending**. Two properties depend on this:

    * a document can never be ``verified`` while an active rejection exists, so the
      patient is never shown a clean status for a reading a doctor refused;
    * the terminal state does not depend on the *order* decisions are recorded in,
      which is what makes reject-first and reject-last equivalent (R1b).

    The all-rejected case is checked first so ``all_facts_rejected`` keeps its
    existing meaning and precedence; the new codes only describe the partial
    rejection that used to be silently reported as ``verified`` or
    ``needs_verification``.

    Deciding a still-pending sibling afterwards is allowed and simply recomputes
    the same ``failed`` state — a later decision cannot resurrect the document.
    """
    facts = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document.id)).scalars()
    )
    if not facts:
        document.extraction_status = DocumentStatus.FAILED.value
        return document.extraction_status

    statuses = [fact.verification_status for fact in facts]
    if all(status == FactVerificationStatus.REJECTED.value for status in statuses):
        document.extraction_status = DocumentStatus.FAILED.value
        document.failure_code = FAILURE_ALL_FACTS_REJECTED
        return document.extraction_status

    # Rejection-first: evaluated before the pending check, so a first rejection is
    # terminal immediately rather than waiting for the siblings (R1a). Superseded
    # originals are excluded, so a correction still reaches ``verified`` (R09).
    active_rejected = _active_rejected_facts(facts, quality.superseded_fact_ids(facts))
    if active_rejected:
        document.extraction_status = DocumentStatus.FAILED.value
        document.failure_code = _rejection_failure_code(active_rejected)
        return document.extraction_status

    if any(status == FactVerificationStatus.PENDING.value for status in statuses):
        document.extraction_status = DocumentStatus.NEEDS_VERIFICATION.value
        return document.extraction_status

    if _unread_measurement_blocks_verification(db, document.id):
        # Fail closed: the document declares a measurement nobody has read.
        # ``VI-005`` stays open, so the doctor still has an actionable blocker.
        document.extraction_status = DocumentStatus.NEEDS_VERIFICATION.value
        return document.extraction_status

    document.extraction_status = DocumentStatus.VERIFIED.value
    return document.extraction_status


def _active_value_candidates(db: Session, document_id: str) -> list[ExtractedFact]:
    """Return the ``value`` facts that still describe the document's measurement.

    **R06:** only a *current* reading qualifies. A fact that a doctor superseded
    (``rejected`` by a correction) is history: it is retained for lineage, but it
    is no longer one of the document's measurement tuples. Counting it made a
    corrected-but-parseable document look like a two-value document, which broke
    the anchor and silently dropped a valid mapping.

    ``pending`` facts are excluded too, so an undecided document has no anchor and
    cannot be promoted before its facts are decided (``VI-002``).
    """
    return list(
        db.execute(
            select(ExtractedFact)
            .where(
                ExtractedFact.document_id == document_id,
                ExtractedFact.field_name == FactField.VALUE.value,
                ExtractedFact.normalized_value.is_not(None),
                ExtractedFact.verification_status != FactVerificationStatus.REJECTED.value,
            )
            .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
        ).scalars()
    )


def _document_measurement_anchor(db: Session, document_id: str) -> ExtractedFact | None:
    """Return the single fact that owns the document's measurement, if any.

    ``DATA_DICTIONARY.md`` §3.3 rule 10 requires **at most one observation per
    document**, anchored on the ``value`` field. Anchoring on "whichever fact was
    verified last" would create one observation per verified field — a real bug
    this design avoids by resolving the anchor deterministically from the facts
    themselves, independent of decision order.

    Only the *active* (unrejected) value facts are considered (R06).
    """
    candidates = _active_value_candidates(db, document_id)
    return candidates[0] if len(candidates) == 1 else None


def _maybe_promote_document(
    db: Session,
    *,
    document: Document,
    doctor_user_id: str,
    decided_at: str,
    conflict_tolerance: float,
) -> tuple[bool, str | None]:
    """Promote a fully decided document to one observation, if the rules allow.

    Returns ``(created, reason)``. A partially decided document, an unmapped
    document, a multi-measurement document and an already-promoted document all
    return ``False`` with a reason; none of them raises, because promotion is a
    consequence of a decision, never a failure of it.

    **R03:** an open ``VI-006`` conflict also refuses promotion. Recording a second
    contradicting measurement for the same patient, measure, unit and UTC day would
    manufacture two disagreeing "verified" values, which is exactly what the
    ``DEMO_ONLY`` conflict policy is meant to prevent. The decision itself is still
    recorded — a doctor's verdict on a fact is data — but no observation is derived
    from a document whose value contradicts the stored record.
    """
    open_issue_types = {
        issue.issue_type
        for issue in quality.sync_issues(
            db, document=document, conflict_tolerance=conflict_tolerance
        )
    }

    # **R21 §4.2.** A clinical record may only be promoted from a document the
    # system considers ``verified``. Checked *after* ``sync_issues`` on purpose:
    # that call is the only writer of ``verification_issue`` rows, so returning
    # early would silently stop ``VI-002``/``VI-005``/``VI-006`` from being
    # recorded — and D-14 requires a rejection to keep counting toward ``VI-002``
    # whether or not promotion is possible. Gating here keeps the issue ledger a
    # pure consequence of the facts and makes ``failed`` unbeatable by any
    # mapping shortcut.
    if document.extraction_status != DocumentStatus.VERIFIED.value:
        return False, _REASON_NOT_VERIFIED

    if quality.ISSUE_SOURCE_CONFLICT in open_issue_types:
        return False, "source_conflict_at_intake"
    if quality.IDENTITY_ISSUE_TYPE.value in open_issue_types:  # pragma: no cover - defensive
        return False, "wrong_patient_document"

    anchor = _document_measurement_anchor(db, document.id)
    if anchor is None:
        return False, "no_single_measurement_fact"
    return _create_observation_from_mapping(
        db,
        document=document,
        source_fact=anchor,
        doctor_user_id=doctor_user_id,
        decided_at=decided_at,
    )


def _create_observation_from_mapping(
    db: Session,
    *,
    document: Document,
    source_fact: ExtractedFact,
    doctor_user_id: str,
    decided_at: str,
) -> tuple[bool, str | None]:
    """Insert the mapped observation for ``document`` if the rule allows it.

    Returns ``(created, reason)``. ``reason`` is the mapping's rejection reason
    when nothing was created. Replay is a no-op: the unique
    ``ux_obs_source_fact`` index makes a second observation for the same fact
    impossible, and this function checks first so the caller sees a clean result
    rather than an ``IntegrityError``.
    """
    decision: MappingDecision = decide_mapping(_document_fact_views(db, document.id))
    if not decision.is_mapped or decision.mapped is None:
        return False, decision.reason

    # Defence in depth: only the document's single ``value`` fact may own the
    # observation. Every other verified field is evidence for it, not an owner.
    anchor = _document_measurement_anchor(db, document.id)
    if anchor is None or anchor.id != source_fact.id:
        return False, "not_the_measurement_fact"

    existing = db.execute(
        select(Observation).where(Observation.source_fact_id == source_fact.id)
    ).scalar_one_or_none()
    if existing is not None:
        return False, "already_mapped"

    candidate = decision.mapped
    measured_at = measured_at_for(candidate.measured_at[:10])
    if measured_at is None:  # pragma: no cover - mapping already validated it
        return False, "unmapped_test_name"

    observation = Observation(
        patient_id=document.patient_id,
        measure_type=candidate.measure_type.value,
        value=candidate.value,
        unit=candidate.unit,
        measured_at=measured_at,
        source="verified_document",
        validation=ValidationState.OK.value,
        trust_level="doctor_verified",
        verified_by_user_id=doctor_user_id,
        verified_at=decided_at,
        source_fact_id=source_fact.id,
        created_at=decided_at,
        created_by_user_id=doctor_user_id,
    )
    db.add(observation)
    try:
        db.flush()
    except IntegrityError:
        # A racing writer won; the unique index did its job.
        db.rollback()
        raise document_error(ErrorCode.FACT_ALREADY_DECIDED, _ALREADY_DECIDED) from None
    return True, None


def record_decision(
    db: Session,
    *,
    document: Document,
    fact: ExtractedFact,
    decision: VerificationDecision,
    doctor_user_id: str,
    corrected_value: str | None = None,
    corrected_unit: str | None = None,
    reason: str | None = None,
    conflict_tolerance: float | None = None,
) -> VerificationOutcome:
    """Record one doctor decision and, if warranted, the derived observation.

    Raises ``409 E_FACT_ALREADY_DECIDED`` for **any** second decision on the same
    fact, including an identical one (D-11).

    The caller is responsible for the doctor/scope check; this function assumes
    an authorized doctor and additionally relies on the database trigger.
    """
    # R02: an identity blocker cannot be cleared by a fact decision. Checked
    # before the append-only guard so the caller learns the real reason: the
    # document may not belong to this patient, which is more actionable than
    # "already decided" and prevents any silent attribution.
    if quality.ensure_identity_evaluated(db, document=document):
        raise document_error(ErrorCode.VI_004_UNRESOLVED, VI_004_UNRESOLVED_DETAIL)

    if _existing_decision(db, fact.id) is not None:
        raise document_error(ErrorCode.FACT_ALREADY_DECIDED, _ALREADY_DECIDED)

    if fact.verification_status != FactVerificationStatus.PENDING.value:
        # Defensive: status and log must never disagree.
        raise document_error(ErrorCode.FACT_ALREADY_DECIDED, _ALREADY_DECIDED)

    # **P3-R17 (P1).** A correction is a doctor's claim about what the page says,
    # so it is held to the same admissibility as the extractor's own reading —
    # per field. Without this, ``'   '`` or ``'abc'`` was recorded as a *verified*
    # measurement: doctor-verified evidence with no numeric meaning behind it.
    #
    # Deliberately evaluated **after** the identity guard and the append-only
    # guard. Precedence is part of the contract: a document that may belong to
    # another patient must answer ``409 E_VI_004_UNRESOLVED``, not a cosmetic
    # "your date is malformed" 400 that hides the real reason it is refused
    # (R02, preserved by ``test_p3_r02_corrected_fact_cannot_bypass_the_identity_blocker``).
    if decision is VerificationDecision.CORRECTED:
        correctable = True
        normalized = normalize_corrected_value(fact.field_name, corrected_value or "")
        if normalized is None:
            correctable = False
        if correctable and corrected_unit is not None:
            unit = normalize_corrected_value(FactField.UNIT.value, corrected_unit)
            if unit is None:
                correctable = False
            else:
                corrected_unit = unit
        if not correctable:
            # ``E_VALIDATION`` is the contract's general 400 (§4), not a
            # document-specific code, so it is raised directly — the same way the
            # route raises it for a missing ``corrected_value``.
            raise ApiError(400, ErrorCode.VALIDATION, _INADMISSIBLE_CORRECTION)
        corrected_value = normalized

    decided_at = format_utc(utc_now())
    previous_value = fact.normalized_value

    verification = FactVerification(
        fact_id=fact.id,
        decision=decision.value,
        previous_value=previous_value,
        new_value=corrected_value if decision is VerificationDecision.CORRECTED else None,
        new_unit=corrected_unit if decision is VerificationDecision.CORRECTED else None,
        reason=reason,
        verified_by_user_id=doctor_user_id,
        decided_at=decided_at,
    )
    db.add(verification)

    # The original fact is marked rejected when a correction supersedes it, and a
    # new corrected fact carries the verified value (§6 "corrected").
    if decision is VerificationDecision.CORRECTED:
        fact.verification_status = FactVerificationStatus.REJECTED.value
        # The corrected row is a *new verified value*, not a rewritten excerpt.
        # It copies the immutable provenance (`raw_text`, span, page, extractor,
        # confidence) from the fact it supersedes, so the evidence still says what
        # the page actually contains — a corrected `1O5` keeps `raw_text='1O5'`
        # while carrying `normalized_value='105'`. Writing the human value into
        # `raw_text` would assert that the page printed `105`, which it did not.
        corrected = ExtractedFact(
            document_id=fact.document_id,
            patient_id=fact.patient_id,
            field_name=fact.field_name,
            raw_text=fact.raw_text,
            normalized_value=corrected_value,
            unit=corrected_unit or fact.unit,
            page_index=fact.page_index,
            char_start=fact.char_start,
            char_end=fact.char_end,
            extractor=fact.extractor,
            # Lineage: the human decision is distinguishable from the extraction.
            corrected_from_fact_id=fact.id,
            quality_flags=json.dumps(["clean"], separators=(",", ":")),
            confidence=fact.confidence,
            verification_status=FactVerificationStatus.VERIFIED.value,
            created_at=decided_at,
        )
        db.add(corrected)
        db.flush()
        # Report the corrected row: the caller asked for a correction, so the
        # response must show the accepted value, not the superseded original.
        reported_fact = corrected
    elif decision is VerificationDecision.VERIFIED:
        fact.verification_status = FactVerificationStatus.VERIFIED.value
        db.flush()
        reported_fact = fact
    else:
        fact.verification_status = FactVerificationStatus.REJECTED.value
        reported_fact = fact

    document_status = _recompute_document_status(db, document)

    # Promotion happens **after** the status is recomputed, so it is driven by the
    # document being fully decided rather than by which field happened to be
    # decided last. Deciding ``value`` before ``unit`` is a normal sequence; keying
    # promotion to that single moment would silently never promote.
    mapped, mapped_reason = _maybe_promote_document(
        db,
        document=document,
        doctor_user_id=doctor_user_id,
        decided_at=decided_at,
        conflict_tolerance=(
            conflict_tolerance
            if conflict_tolerance is not None
            else get_settings().conflict_tolerance
        ),
    )

    return VerificationOutcome(
        fact=reported_fact,
        verification=verification,
        document_status=document_status,
        observation_created=mapped,
        mapped_reason=mapped_reason,
        superseded_fact_id=(fact.id if decision is VerificationDecision.CORRECTED else None),
    )


def fact_blocks_document(fact: ExtractedFact) -> bool:
    """Return ``True`` when ``fact`` is not yet decided."""
    return fact.verification_status == FactVerificationStatus.PENDING.value


def mapping_ready(db: Session, document_id: str) -> bool:
    """Return ``True`` when no fact of ``document_id`` is still pending."""
    return _blocking_facts_remaining(db, document_id) == 0


def is_measurement_value_fact(fact: ExtractedFact) -> bool:
    """Return ``True`` when ``fact`` is the ``value`` field of a report."""
    return fact.field_name == FactField.VALUE.value


__all__ = [
    "VerificationOutcome",
    "fact_blocks_document",
    "is_measurement_value_fact",
    "mapping_ready",
    "record_decision",
]
