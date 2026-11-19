"""Document quality gating: assembling, persisting and resolving blockers.

This module owns the *whole* lifecycle of a ``VI-*`` blocker, because splitting
"compute" from "store" is what produced the R02/R03/R04 defects:

* **R02** — the identity comparison was fed the document's own patient id twice,
  so it always agreed with itself and ``VI-004`` was unreachable through the API.
  :func:`evaluate_identity` now compares the reference *printed in the document*
  against the **uploading patient's** ``external_ref``.
* **R03** — ``VI-006`` vocabulary existed but nothing ever compared a candidate
  against stored observations. :func:`evaluate_conflicts` does that comparison
  using the approved ``DEMO_ONLY`` policy in :mod:`app.services.documents.issues`.
* **R04** — issues were recomputed with fresh UUIDs on every GET. They are now
  persisted rows keyed on ``(document_id, issue_type)``, so an issue keeps its id
  and ``created_at`` for its whole life and its ``state`` moves in place.

Nothing here can mark a fact verified. A quality problem is always resolved by a
doctor decision — except ``VI-004``, which fact verification can never clear and
therefore blocks it entirely.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import format_utc, utc_now
from app.core.enums import (
    FactField,
    FactVerificationStatus,
    IssueState,
    IssueType,
)
from app.db.models import Document, ExtractedFact, Observation, Patient, VerificationIssue, new_uuid
from app.services.documents.issues import (
    ConflictCandidate,
    IssueDraft,
    collect_flag_issues,
    collect_multi_measurement_issue,
    collect_source_conflict_issue,
    collect_unverified_issue,
    collect_wrong_patient_issue,
    render_message,
)
from app.services.documents.mapping import decide_mapping

#: Issues that are *derived* from the facts and therefore recomputed on each
#: sync. ``VI-004`` is excluded: it is an identity finding about the document, not
#: about a fact, and once raised it stays until an explicit re-attribution.
DERIVED_ISSUE_TYPES: tuple[IssueType, ...] = (
    IssueType.VI_001,
    IssueType.VI_002,
    IssueType.VI_003,
    IssueType.VI_005,
    IssueType.VI_006,
)

#: The single issue type that fact verification can never clear.
IDENTITY_ISSUE_TYPE = IssueType.VI_004

#: The issue type that refuses *promotion* while it is open (R03): a doctor may
#: still decide the facts, but no observation may be derived from a value that
#: contradicts the patient's stored record.
ISSUE_SOURCE_CONFLICT = IssueType.VI_006.value


@dataclass(frozen=True, slots=True)
class QualitySummary:
    """The document's currently **open** blockers, as persisted rows."""

    issues: tuple[VerificationIssue, ...]
    pending_fact_count: int
    candidate_value_count: int

    @property
    def has_blocking_issue(self) -> bool:
        """Return ``True`` when at least one blocker is open."""
        return bool(self.issues)

    @property
    def has_identity_blocker(self) -> bool:
        """Return ``True`` when ``VI-004`` is open.

        Verification must be refused while this is true: the document may not
        belong to the patient it was filed under, so recording a decision on it
        would launder a mis-filed record into verified clinical data
        (``DEMO_REVIEW_RULES.md`` §4 ``VI-03``).
        """
        return any(issue.issue_type == IDENTITY_ISSUE_TYPE.value for issue in self.issues)


def decode_flags(raw: str | None) -> tuple[str, ...]:
    """Return the stored quality flags of a fact as a tuple.

    Stored as a compact JSON array so the database column stays a plain TEXT
    while the reader gets a typed sequence. Unparseable text yields an empty
    tuple rather than raising: a display path must not fail on bad data.
    """
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return ()
    if not isinstance(decoded, list):
        return ()
    return tuple(str(item) for item in decoded if isinstance(item, str))


def decode_fact_ids(raw: str | None) -> tuple[str, ...]:
    """Return the persisted fact linkage of an issue."""
    return decode_flags(raw)


def decode_text_list(raw: str | None) -> tuple[str, ...]:
    """Return a stored compact JSON string array as a tuple (R07)."""
    return decode_flags(raw)


def _facts(db: Session, document_id: str) -> list[ExtractedFact]:
    """Return the document's facts in a stable order.

    Ordered by position in the page rather than by creation time: every fact of a
    document is written in one transaction, so ``created_at`` is identical for all
    of them and would leave the order to an arbitrary tiebreak.
    """
    return list(
        db.execute(
            select(ExtractedFact)
            .where(ExtractedFact.document_id == document_id)
            .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
        ).scalars()
    )


def superseded_fact_ids(facts: list[ExtractedFact]) -> set[str]:
    """Return the facts a correction replaced (``R09``).

    A fact is **superseded** — not merely rejected — when it is ``rejected`` *and*
    another fact of the same document points at it through
    ``corrected_from_fact_id``. That is the signature of an immutable historical
    version kept for provenance, and it is precisely the row that must stop being
    counted as an active measurement tuple.

    A plain rejection is deliberately **not** in this set: rejecting a value is a
    doctor's verdict about a current reading, and ``DEMO_REVIEW_RULES.md`` §4
    counts it. Only correction *history* is excluded.
    """
    replaced = {
        fact.corrected_from_fact_id for fact in facts if fact.corrected_from_fact_id is not None
    }
    return {
        fact.id
        for fact in facts
        if fact.verification_status == FactVerificationStatus.REJECTED.value and fact.id in replaced
    }


def _structural_measurement_count(facts: list[ExtractedFact]) -> int:
    """Return how many measurement tuples the document describes **now**.

    Counted from the stored candidate facts with no regard to verification
    *verdicts*: two ``test_name`` fields, or two ``value`` fields, describe two
    measurements whatever a doctor has decided about them. A document with one of
    each is a single tuple.

    **R09:** a superseded version is not one of those tuples. A correction keeps
    the rejected original beside the verified correction, and counting both made a
    one-measurement report look like a two-test document, so a false
    ``VI-002 / multi_measurement_document`` was persisted as OPEN on a document
    that had just mapped correctly. History is retained (status, excerpt, span and
    lineage all stay), but it no longer participates in the count.
    """
    superseded = superseded_fact_ids(facts)
    active = [fact for fact in facts if fact.id not in superseded]

    test_names = {
        (fact.normalized_value or "").strip().lower()
        for fact in active
        if fact.field_name == FactField.TEST_NAME.value and fact.normalized_value
    }
    values = [
        fact
        for fact in active
        if fact.field_name == FactField.VALUE.value and fact.normalized_value is not None
    ]
    return max(len(test_names), len(values))


# --- identity (R02) ---------------------------------------------------------


def uploader_patient_ref(db: Session, patient_id: str) -> str | None:
    """Return the synthetic reference of the patient the document was filed under."""
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    return patient.external_ref if patient is not None else None


def evaluate_identity(db: Session, *, document: Document) -> IssueDraft | None:
    """Return ``VI-004`` when the document's own reference contradicts its filing.

    Both operands are real, independent values:

    * ``document.document_patient_ref`` — what the *paper* says (parsed at intake);
    * the uploading patient's ``external_ref`` — what the *record* says.

    A document that printed no reference at all cannot contradict anything, so it
    is not flagged on absence alone. A document that printed a reference which
    does not match the filing is the exact wrong-patient case ``VI-004`` describes.

    **R07:** a document that printed *several distinct* references is treated as a
    contradiction in its own right. It cannot be attributed to anybody, so it must
    fail closed rather than be reduced to whichever reference the parser happened
    to see first. ``document_patient_refs`` records that set; ``document_patient_ref``
    is then ``None``, which is why the check happens here and not on the pointer.
    """
    if decode_text_list(document.document_patient_refs):
        # More than one distinct reference (a single one is also stored in the
        # list, so re-check the count before declaring a conflict).
        refs = decode_text_list(document.document_patient_refs)
        if len(set(refs)) > 1:
            return IssueDraft(
                issue_type=IDENTITY_ISSUE_TYPE,
                message=render_message(IDENTITY_ISSUE_TYPE),
            )

    printed = document.document_patient_ref
    if printed is None:
        return None
    return collect_wrong_patient_issue(
        document_patient_ref=printed,
        scope_patient_ref=uploader_patient_ref(db, document.patient_id),
    )


# --- conflicts (R03) --------------------------------------------------------


def _existing_measurements(
    db: Session,
    *,
    patient_id: str,
    measure_type: str,
    unit: str,
    day: str,
    exclude_document_id: str,
) -> list[tuple[str, float, str]]:
    """Return admissible stored measurements for the same patient/measure/unit/day.

    "Admissible" excludes rows the data check rejected (``validation='rejected'``
    is retained for audit but inadmissible by contract) and the document's own
    derived observation, so a document cannot conflict with itself.
    """
    rows = db.execute(
        select(Observation).where(
            Observation.patient_id == patient_id,
            Observation.measure_type == measure_type,
            Observation.unit == unit,
            Observation.measured_at.like(f"{day}%"),
            Observation.source_fact_id.is_(None)
            | Observation.source_fact_id.not_in(
                select(ExtractedFact.id).where(ExtractedFact.document_id == exclude_document_id)
            ),
        )
    ).scalars()
    return [
        (row.unit, float(row.value), row.measured_at)
        for row in rows
        if row.validation != "rejected"
    ]


def evaluate_conflicts(
    db: Session,
    *,
    document: Document,
    facts: list[ExtractedFact],
    tolerance: float,
) -> list[IssueDraft]:
    """Return the ``VI-006`` conflicts for one document.

    A conflict is only meaningful once the document resolves to a single mapped
    measurement **and** has a usable date: otherwise there is no candidate to
    compare and the document is already blocked by ``VI-002``/``VI-003``/``VI-004``.
    Reusing :func:`decide_mapping` means the comparison can never disagree with
    ``map-1.0.0`` about which measure a document describes.
    """
    from app.services.documents.mapping import VerifiedFactView

    # **R06:** a superseded original is excluded *before* the status is forced,
    # because it is not one of the document's measurement tuples any more. Forcing
    # every row — including the rejected one a correction left behind — to look
    # verified made a corrected parseable document look like a two-value document,
    # so ``decide_mapping`` reported ambiguity and ``VI-006`` was silently dropped.
    active = [
        fact for fact in facts if fact.verification_status != FactVerificationStatus.REJECTED.value
    ]
    views = [
        VerifiedFactView(
            field_name=fact.field_name,
            normalized_value=fact.normalized_value,
            unit=fact.unit,
            # Conflicts are evaluated on the *candidate*, so **pending** facts must
            # participate. Passing the real status would hide every conflict until a
            # doctor had already decided the facts the conflict is meant to warn
            # them about.
            verification_status=FactVerificationStatus.VERIFIED.value,
        )
        for fact in active
    ]
    decision = decide_mapping(views)
    if not decision.is_mapped or decision.mapped is None:
        return []

    mapped = decision.mapped
    value_index = next(
        (
            index
            for index, fact in enumerate(facts)
            if fact.field_name == FactField.VALUE.value
            and fact.normalized_value is not None
            and fact.verification_status != FactVerificationStatus.REJECTED.value
        ),
        None,
    )
    if value_index is None:  # pragma: no cover - mapping already required a value
        return []

    existing = _existing_measurements(
        db,
        patient_id=document.patient_id,
        measure_type=mapped.measure_type.value,
        unit=mapped.unit,
        day=mapped.measured_at[:10],
        exclude_document_id=document.id,
    )
    conflict = collect_source_conflict_issue(
        candidate=ConflictCandidate(
            fact_index=value_index,
            measure_type=mapped.measure_type.value,
            value=mapped.value,
            unit=mapped.unit,
            measured_at=mapped.measured_at,
        ),
        existing=existing,
        tolerance=tolerance,
    )
    return [conflict] if conflict is not None else []


# --- composition ------------------------------------------------------------


def compute_drafts(
    db: Session,
    *,
    document: Document,
    conflict_tolerance: float,
) -> list[IssueDraft]:
    """Return the complete set of *desired* open issues for ``document``.

    Order is fixed: ``VI-004`` (identity) first because nothing else matters if the
    document may belong to someone else, then flag-derived issues, then the
    structural association block, then conflicts, then ``VI-002``.
    """
    facts = _facts(db, document.id)
    drafts: list[IssueDraft] = []

    identity = evaluate_identity(db, document=document)
    if identity is not None:
        drafts.append(identity)

    # **R17:** a flag on a *superseded* original describes a reading the doctor
    # has already replaced. Reading it kept ``VI-005`` (and every other
    # flag-derived blocker) open forever on a document that was fully resolved —
    # the same permanent-blocker defect D-14 fixed for ``VI-002``. The history row
    # keeps its flags for audit; it simply stops generating blockers.
    # A plain rejection is **not** superseded, so its flag still blocks, exactly
    # as ``DEMO_REVIEW_RULES.md`` §4 requires.
    superseded_for_flags = superseded_fact_ids(facts)
    flag_input = [
        (index, fact.field_name, decode_flags(fact.quality_flags))
        for index, fact in enumerate(facts)
        if fact.id not in superseded_for_flags
    ]
    drafts.extend(collect_flag_issues(flag_input))

    structural_candidates = _structural_measurement_count(facts)
    multi = collect_multi_measurement_issue(candidate_count=structural_candidates)
    if multi is not None:
        drafts.append(multi)

    drafts.extend(
        evaluate_conflicts(db, document=document, facts=facts, tolerance=conflict_tolerance)
    )

    # **R09:** ``VI-002`` counts facts that still need a decision, not the
    # immutable history a correction leaves behind. A superseded original is
    # ``rejected`` by construction and would otherwise keep "1 extracted value(s)
    # are not yet verified." open forever on a document that is fully decided —
    # a permanent blocker no doctor action could ever clear. A plain rejection
    # still counts, exactly as ``DEMO_REVIEW_RULES.md`` §4/§6.1 specifies.
    pending = [
        (index, fact.verification_status)
        for index, fact in enumerate(facts)
        if fact.verification_status != FactVerificationStatus.VERIFIED.value
        and fact.id not in superseded_for_flags
    ]
    unverified = collect_unverified_issue(pending)
    # ``VI-002`` has two documented reasons: the generic ``fact_unverified`` and
    # the specific ``multi_measurement_document``. Issues are persisted one row
    # per ``(document, issue_type)``, so appending both would make the later one
    # silently overwrite the earlier one's reason. The specific reason is the one
    # that tells the doctor why the document cannot be mapped, so it wins.
    already_specific = any(draft.issue_type == IssueType.VI_002 for draft in drafts)
    if unverified is not None and not already_specific:
        drafts.append(unverified)

    return drafts


def _fact_ids_for(draft: IssueDraft, facts: list[ExtractedFact]) -> str | None:
    """Return the JSON linkage for ``draft``, or ``None`` when it names no fact."""
    ids = [facts[index].id for index in draft.fact_indices if 0 <= index < len(facts)][:8]
    return json.dumps(ids, separators=(",", ":")) if ids else None


def sync_issues(
    db: Session,
    *,
    document: Document,
    conflict_tolerance: float,
) -> tuple[VerificationIssue, ...]:
    """Reconcile the persisted issue rows with the document's current state.

    This is the only writer of ``verification_issue`` rows. The rules:

    * an issue that should be open **and already exists** keeps its ``id`` and
      ``created_at`` and has its message/linkage refreshed (R04);
    * an issue that should be open but does not exist is **created once**;
    * an issue that exists but should no longer be open moves to ``resolved``;
    * ``VI-004`` is never auto-resolved: resolving it needs an explicit
      re-attribution, which is not a fact decision.

    Returns the currently open issues, ordered by issue type.
    """
    facts = _facts(db, document.id)
    drafts = compute_drafts(db, document=document, conflict_tolerance=conflict_tolerance)
    desired = {draft.issue_type: draft for draft in drafts}

    existing = {
        row.issue_type: row
        for row in db.execute(
            select(VerificationIssue).where(VerificationIssue.document_id == document.id)
        ).scalars()
    }

    now = format_utc(utc_now())

    for issue_type, draft in desired.items():
        row = existing.get(issue_type.value)
        if row is None:
            row = VerificationIssue(
                id=new_uuid(),
                patient_id=document.patient_id,
                document_id=document.id,
                issue_type=issue_type.value,
                reason_code=draft.reason_code,
                fact_ids=_fact_ids_for(draft, facts),
                blocking=1,
                message=draft.message,
                state=IssueState.OPEN.value,
                created_at=now,
            )
            db.add(row)
            existing[issue_type.value] = row
            continue

        # Existing row: refresh the volatile parts, keep the identity.
        row.message = draft.message
        row.reason_code = draft.reason_code
        row.fact_ids = _fact_ids_for(draft, facts)
        if row.state != IssueState.OPEN.value:
            # A blocker that came back (e.g. a conflict reappears) re-opens the
            # same row rather than minting a second one.
            row.state = IssueState.OPEN.value

    for issue_type_value, row in existing.items():
        if issue_type_value in {issue_type.value for issue_type in desired}:
            continue
        if row.state == IssueState.RESOLVED.value:
            continue
        if row.issue_type == IDENTITY_ISSUE_TYPE.value:
            # Never auto-clear an identity blocker.
            continue
        row.state = IssueState.RESOLVED.value

    db.flush()
    return open_issues(db, document=document)


def open_issues(db: Session, *, document: Document) -> tuple[VerificationIssue, ...]:
    """Return the document's open blockers in contract order."""
    rows = list(
        db.execute(
            select(VerificationIssue)
            .where(
                VerificationIssue.document_id == document.id,
                VerificationIssue.state == IssueState.OPEN.value,
            )
            .order_by(VerificationIssue.issue_type)
        ).scalars()
    )
    return tuple(rows)


def summarize(
    db: Session,
    *,
    document: Document,
    conflict_tolerance: float,
) -> QualitySummary:
    """Reconcile the blockers and return the open set.

    Kept as the single entry point the read path calls, so "read" and "reconcile"
    can never diverge: whichever route asks for the blockers also brings the stored
    rows up to date.
    """
    issues = sync_issues(db, document=document, conflict_tolerance=conflict_tolerance)
    facts = _facts(db, document.id)
    pending = [
        fact for fact in facts if fact.verification_status != FactVerificationStatus.VERIFIED.value
    ]
    values = [fact for fact in facts if fact.field_name == FactField.VALUE.value]
    return QualitySummary(
        issues=issues,
        pending_fact_count=len(pending),
        candidate_value_count=len(values),
    )


def identity_blocked(db: Session, *, document: Document) -> bool:
    """Return ``True`` when ``VI-004`` is open for ``document``.

    Used by the verification service *before* recording a decision, so the
    safeguard does not depend on the read path having been called first.
    """
    return any(
        row.issue_type == IDENTITY_ISSUE_TYPE.value
        for row in db.execute(
            select(VerificationIssue).where(
                VerificationIssue.document_id == document.id,
                VerificationIssue.state == IssueState.OPEN.value,
            )
        ).scalars()
    )


def ensure_identity_evaluated(db: Session, *, document: Document) -> bool:
    """Create the ``VI-004`` row if the document contradicts its filing.

    Verification calls this so a doctor can never record a decision on a
    mismatched document that was never read first. It is idempotent: the unique
    ``(document_id, issue_type)`` lookup means a second call finds the row.
    """
    draft = evaluate_identity(db, document=document)
    if draft is None:
        return False

    existing = db.execute(
        select(VerificationIssue).where(
            VerificationIssue.document_id == document.id,
            VerificationIssue.issue_type == IDENTITY_ISSUE_TYPE.value,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing.state == IssueState.OPEN.value

    db.add(
        VerificationIssue(
            id=new_uuid(),
            patient_id=document.patient_id,
            document_id=document.id,
            issue_type=IDENTITY_ISSUE_TYPE.value,
            reason_code=draft.reason_code,
            fact_ids=None,
            blocking=1,
            message=draft.message,
            state=IssueState.OPEN.value,
            created_at=format_utc(utc_now()),
        )
    )
    db.flush()
    return True


__all__ = [
    "DERIVED_ISSUE_TYPES",
    "IDENTITY_ISSUE_TYPE",
    "QualitySummary",
    "compute_drafts",
    "decode_fact_ids",
    "decode_flags",
    "ensure_identity_evaluated",
    "evaluate_conflicts",
    "evaluate_identity",
    "identity_blocked",
    "open_issues",
    "summarize",
    "superseded_fact_ids",
    "sync_issues",
    "uploader_patient_ref",
]
