"""Document quality gating: assembling the pre-verification summary.

This module is the single place that decides which :class:`IssueDraft` objects a
document carries. It composes the pure collectors in
:mod:`app.services.documents.issues` and the mapping decision in
:mod:`app.services.documents.mapping` so that the route layer never invents a
reason code.

No function here can mark a fact verified. A quality problem is always resolved
by a doctor decision, never by an automatic repair.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import FactField, FactVerificationStatus
from app.db.models import Document, ExtractedFact
from app.services.documents.issues import (
    IssueDraft,
    collect_flag_issues,
    collect_multi_measurement_issue,
    collect_unverified_issue,
    collect_wrong_patient_issue,
)


@dataclass(frozen=True, slots=True)
class QualitySummary:
    """Everything the read endpoints need to describe a document's state."""

    issues: tuple[IssueDraft, ...]
    pending_fact_count: int
    candidate_value_count: int

    @property
    def has_blocking_issue(self) -> bool:
        """Return ``True`` when at least one issue is unresolved."""
        return bool(self.issues)


def decode_flags(raw: str | None) -> tuple[str, ...]:
    """Return the stored quality flags of a fact as a tuple.

    Stored as a compact JSON array so the database column stays a plain TEXT
    while the reader gets a typed sequence. Unparseable text yields an empty
    tuple rather than raising: a display path must not 500 on bad data.
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


def _facts(db: Session, document_id: str) -> list[ExtractedFact]:
    """Return the document's facts in a stable order."""
    return list(
        db.execute(
            select(ExtractedFact)
            .where(ExtractedFact.document_id == document_id)
            .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
        ).scalars()
    )


def _structural_measurement_count(facts: list[ExtractedFact]) -> int:
    """Return how many measurement tuples the document appears to describe.

    Counted from the stored candidate facts with **no** regard to verification
    status: two ``test_name`` fields, or two ``value`` fields, describe two
    measurements whatever a doctor has decided so far. A document with one of each
    is a single tuple.
    """
    test_names = {
        (fact.normalized_value or "").strip().lower()
        for fact in facts
        if fact.field_name == FactField.TEST_NAME.value and fact.normalized_value
    }
    values = [
        fact
        for fact in facts
        if fact.field_name == FactField.VALUE.value and fact.normalized_value is not None
    ]
    return max(len(test_names), len(values))


def summarize(
    db: Session,
    *,
    document: Document,
    document_patient_ref: str | None,
    scope_patient_ref: str | None,
) -> QualitySummary:
    """Build the quality summary for ``document``.

    Ordering is fixed: ``VI-004`` (identity) first because nothing else matters if
    the document may belong to someone else, then the flag-derived issues, then
    the multi-measurement association block, then ``VI-002`` for remaining
    undecided facts. Tests assert this order, so a reordering is a visible change.
    """
    facts = _facts(db, document.id)

    flag_input = [
        (index, fact.field_name, decode_flags(fact.quality_flags))
        for index, fact in enumerate(facts)
    ]
    drafts: list[IssueDraft] = []

    wrong_patient = collect_wrong_patient_issue(
        document_patient_ref=document_patient_ref,
        scope_patient_ref=scope_patient_ref,
    )
    if wrong_patient is not None:
        drafts.append(wrong_patient)

    drafts.extend(collect_flag_issues(flag_input))

    # The association block is a **structural** property of the document, not a
    # function of how much of it has been decided. It must be visible at intake,
    # while every fact is still pending, otherwise the doctor is told nothing
    # about the reason the document can never be mapped.
    structural_candidates = _structural_measurement_count(facts)
    multi = collect_multi_measurement_issue(candidate_count=structural_candidates)
    if multi is not None:
        drafts.append(multi)

    pending = [
        (index, fact.verification_status)
        for index, fact in enumerate(facts)
        if fact.verification_status != FactVerificationStatus.VERIFIED.value
    ]
    unverified = collect_unverified_issue(pending)
    if unverified is not None:
        drafts.append(unverified)

    candidate_values = [fact for fact in facts if fact.field_name == FactField.VALUE.value]

    return QualitySummary(
        issues=tuple(drafts),
        pending_fact_count=len(pending),
        candidate_value_count=len(candidate_values),
    )


def blocking_issue_types(db: Session, *, document: Document) -> list[str]:
    """Return the issue-type values currently blocking ``document``."""
    summary = summarize(
        db,
        document=document,
        document_patient_ref=document.patient_id,
        scope_patient_ref=document.patient_id,
    )
    return [draft.issue_type.value for draft in summary.issues]


__all__ = [
    "QualitySummary",
    "blocking_issue_types",
    "decode_flags",
    "summarize",
]
