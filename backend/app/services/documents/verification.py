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
    ValidationState,
    VerificationDecision,
)
from app.core.errors import (
    FACT_ALREADY_DECIDED_DETAIL,
    VI_004_UNRESOLVED_DETAIL,
    ErrorCode,
    document_error,
)
from app.db.models import Document, ExtractedFact, FactVerification, Observation
from app.services.documents import quality
from app.services.documents.mapping import (
    MappingDecision,
    VerifiedFactView,
    decide_mapping,
    measured_at_for,
)

#: Neutral detail reused for every "already decided" case (D-11).
_ALREADY_DECIDED = FACT_ALREADY_DECIDED_DETAIL


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
    """Return every fact of ``document_id`` as a mapping view."""
    rows = db.execute(
        select(ExtractedFact)
        .where(ExtractedFact.document_id == document_id)
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


def _recompute_document_status(db: Session, document: Document) -> str:
    """Derive and store the document status from its facts.

    ``verified`` requires every blocking fact decided **and** at least one fact
    verified. A document whose facts are all rejected becomes ``failed``.
    """
    facts = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document.id)).scalars()
    )
    if not facts:
        document.extraction_status = DocumentStatus.FAILED.value
        return document.extraction_status

    statuses = [fact.verification_status for fact in facts]
    if any(status == FactVerificationStatus.PENDING.value for status in statuses):
        document.extraction_status = DocumentStatus.NEEDS_VERIFICATION.value
        return document.extraction_status

    if all(status == FactVerificationStatus.REJECTED.value for status in statuses):
        document.extraction_status = DocumentStatus.FAILED.value
        document.failure_code = "all_facts_rejected"
        return document.extraction_status

    document.extraction_status = DocumentStatus.VERIFIED.value
    return document.extraction_status


def _document_measurement_anchor(db: Session, document_id: str) -> ExtractedFact | None:
    """Return the single fact that owns the document's measurement, if any.

    ``DATA_DICTIONARY.md`` §3.3 rule 10 requires **at most one observation per
    document**, anchored on the ``value`` field. Anchoring on "whichever fact was
    verified last" would create one observation per verified field — a real bug
    this design avoids by resolving the anchor deterministically from the facts
    themselves, independent of decision order.
    """
    candidates = list(
        db.execute(
            select(ExtractedFact)
            .where(
                ExtractedFact.document_id == document_id,
                ExtractedFact.field_name == FactField.VALUE.value,
                ExtractedFact.normalized_value.is_not(None),
            )
            .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
        ).scalars()
    )
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
