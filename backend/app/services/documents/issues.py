"""Deterministic pre-verification blockers (``VI-001..VI-006``).

A ``VerificationIssue`` is a **different output type** from a ``DR-*`` review
item (``DEMO_REVIEW_RULES.md`` §3). It is produced before verification, it
carries no rule id, and it never becomes a review flag. There is deliberately no
``rule_id`` field here or in the table.

Wording is fixed by ``DEMO_REVIEW_RULES.md`` §6.1 and is neutral: a message states
what could not be read and asks for confirmation, nothing more. It never names a
condition, grades a value or suggests an action. ``backend/tests/p3`` asserts that
property mechanically against the rendered templates, so the vocabulary list lives
in the test suite rather than in shipped code.

Everything in this module is a pure function of its inputs. It cannot write a
verified fact; only a doctor decision does that.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import (
    FactField,
    FactVerificationStatus,
    IssueType,
    QualityFlag,
)

#: Exact message templates from ``DEMO_REVIEW_RULES.md`` §6.1. Do not paraphrase.
MESSAGES: dict[IssueType, str] = {
    IssueType.VI_001: "A recorded value has no usable unit. Please confirm the unit.",
    IssueType.VI_002: "{count} extracted value(s) are not yet verified.",
    IssueType.VI_003: "A date could not be read unambiguously.",
    IssueType.VI_004: "A document may not belong to this patient; please confirm.",
    IssueType.VI_005: "A value could not be read reliably and needs correction.",
    IssueType.VI_006: "A document value conflicts with an existing record for {measure_type}.",
}

#: ``VI-004`` is unresolvable through fact verification. Resolving it requires
#: explicit re-attribution with an audit record (``DEMO_REVIEW_RULES.md`` §4,
#: ``VI-03``), which is why the verify route refuses while it is open.
WRONG_PATIENT_ISSUE = IssueType.VI_004

#: Reason code per issue type (``DEMO_REVIEW_RULES.md`` §4).
REASON_CODES: dict[IssueType, str] = {
    IssueType.VI_001: "unit_missing_or_unsupported",
    IssueType.VI_002: "fact_unverified",
    IssueType.VI_003: "date_ambiguous",
    IssueType.VI_004: "wrong_patient_document",
    IssueType.VI_005: "value_unreadable",
    IssueType.VI_006: "source_conflict_at_intake",
}

#: Longest message the contract allows.
MAX_MESSAGE_LENGTH = 240


@dataclass(frozen=True, slots=True)
class IssueDraft:
    """An issue ready to persist, before it has an id or document id attached.

    ``reason_code`` defaults to the contract code for ``issue_type``. The
    multi-measurement case passes an explicit override
    (``multi_measurement_document``) rather than subclassing, so there is exactly
    one issue type with two documented reasons and no inheritance tricks.
    """

    issue_type: IssueType
    message: str
    fact_indices: tuple[int, ...] = ()
    reason_code_override: str | None = None

    @property
    def reason_code(self) -> str:
        """Return the reason code stored on ``verification_issue.reason_code``."""
        return self.reason_code_override or REASON_CODES[self.issue_type]

    def __post_init__(self) -> None:
        if len(self.message) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"message exceeds {MAX_MESSAGE_LENGTH} characters")
        if not self.message:
            raise ValueError("message must not be empty")


def render_message(issue_type: IssueType, *, count: int = 0, measure_type: str = "") -> str:
    """Render the exact neutral template for ``issue_type``.

    ``VI-002`` interpolates a computed count and ``VI-006`` a measure type; both
    are structural, never clinical. Neither is ever hard-coded to a fixture's
    value.
    """
    template = MESSAGES[issue_type]
    return template.format(count=count, measure_type=measure_type)


def _flags_of(fact_flags: tuple[str, ...]) -> set[QualityFlag]:
    """Convert stored flag strings to their enum members, ignoring unknowns."""
    resolved: set[QualityFlag] = set()
    for raw in fact_flags:
        try:
            resolved.add(QualityFlag(raw))
        except ValueError:
            continue
    return resolved


def collect_flag_issues(
    facts: list[tuple[int, str, tuple[str, ...]]],
) -> list[IssueDraft]:
    """Return issues implied by quality flags.

    ``facts`` is ``(index, field_name, quality_flags)`` per candidate fact. Each
    blocking flag maps to exactly one issue type (``EXTRACTION_PROVENANCE.md`` §4):
    ``ambiguous_unit`` -> ``VI-001``, ``ambiguous_date`` -> ``VI-003``,
    ``unparseable_value``/``low_confidence`` -> ``VI-005``,
    ``source_conflict`` -> ``VI-006``.
    """
    by_type: dict[IssueType, list[int]] = {
        IssueType.VI_001: [],
        IssueType.VI_003: [],
        IssueType.VI_005: [],
        IssueType.VI_006: [],
    }

    for index, field_name, raw_flags in facts:
        flags = _flags_of(raw_flags)
        if QualityFlag.AMBIGUOUS_UNIT in flags and field_name == FactField.VALUE.value:
            by_type[IssueType.VI_001].append(index)
        if QualityFlag.AMBIGUOUS_DATE in flags:
            by_type[IssueType.VI_003].append(index)
        if QualityFlag.UNPARSEABLE_VALUE in flags or QualityFlag.LOW_CONFIDENCE in flags:
            by_type[IssueType.VI_005].append(index)
        # ``page_missing`` is the documented flag for "OCR yielded nothing usable
        # for the page / blocking if the field was expected there"
        # (``EXTRACTION_PROVENANCE.md`` §4). P3-R17 makes it reachable: the parser
        # emits it for a ``Value:`` line it could not attribute, so a measurement
        # that was printed but never parsed becomes a blocking ``VI-005`` instead
        # of vanishing. Without this mapping the flag is dead code.
        if QualityFlag.PAGE_MISSING in flags and field_name == FactField.VALUE.value:
            by_type[IssueType.VI_005].append(index)
        if QualityFlag.SOURCE_CONFLICT in flags:
            by_type[IssueType.VI_006].append(index)

    drafts: list[IssueDraft] = []
    # Emitted in a fixed order so output is deterministic across runs.
    for issue_type in (IssueType.VI_001, IssueType.VI_003, IssueType.VI_005, IssueType.VI_006):
        indices = by_type[issue_type]
        if not indices:
            continue
        drafts.append(
            IssueDraft(
                issue_type=issue_type,
                message=render_message(issue_type),
                fact_indices=tuple(sorted(indices)),
            )
        )
    return drafts


def collect_unverified_issue(
    facts: list[tuple[int, str]],
) -> IssueDraft | None:
    """Return ``VI-002`` when any fact is not yet verified.

    The ``{count}`` is the number of candidate rows whose status is not
    ``verified``, computed at render time — never a fixture constant
    (``GOLD_FIXTURES`` Case C declares exactly 3, which the test asserts).
    """
    pending = [index for index, status in facts if status != FactVerificationStatus.VERIFIED.value]
    if not pending:
        return None
    return IssueDraft(
        issue_type=IssueType.VI_002,
        message=render_message(IssueType.VI_002, count=len(pending)),
        fact_indices=tuple(sorted(pending)),
    )


def collect_wrong_patient_issue(
    *, document_patient_ref: str | None, scope_patient_ref: str | None
) -> IssueDraft | None:
    """Return ``VI-004`` when the document's patient reference does not match.

    A missing reference on either side is treated as a mismatch: this demo never
    assumes an unstated patient identity. ``VI-004`` cannot be resolved by
    verifying the fact — it requires explicit re-attribution with an audit record
    (``VI-03``).
    """
    if document_patient_ref is None or scope_patient_ref is None:
        return IssueDraft(
            issue_type=IssueType.VI_004,
            message=render_message(IssueType.VI_004),
        )
    if document_patient_ref.strip() != scope_patient_ref.strip():
        return IssueDraft(
            issue_type=IssueType.VI_004,
            message=render_message(IssueType.VI_004),
        )
    return None


@dataclass(frozen=True, slots=True)
class ConflictCandidate:
    """One candidate measurement compared against the patient's stored history.

    Everything needed for the comparison is passed in explicitly so the policy is
    auditable in one place rather than scattered across a query.
    """

    fact_index: int
    measure_type: str
    value: float
    unit: str
    measured_at: str


def collect_source_conflict_issue(
    *,
    candidate: ConflictCandidate,
    existing: list[tuple[str, float, str]],
    tolerance: float,
) -> IssueDraft | None:
    """Return ``VI-006`` when ``candidate`` contradicts an existing record.

    The approved ``DEMO_ONLY`` policy (owner decision D-08/D-12) is evaluated here
    and nowhere else:

    * **Same patient** — the caller only ever passes this document's own patient's
      observations, so a cross-patient row cannot produce a conflict.
    * **Same mapped measure and unit** — the comparison is only meaningful once
      ``map-1.0.0`` has resolved both sides to one measure. An unmapped candidate
      never reaches this function.
    * **Same UTC calendar day** — ``measured_at`` for a document value is
      ``report_date T00:00:00Z``, so the day prefix is the comparison key.
    * **``conflict_tolerance = 0``** — exact equality is required, so *any*
      different value is a conflict. The tolerance is a parameter, not a constant,
      because it is configuration (``Settings.conflict_tolerance``).

    The candidate value is read from the **document**; ``existing`` is the
    patient's stored history. This function never proposes which value is right —
    that is a doctor decision, and stating a preference would be a clinical claim.
    """
    if not existing:
        return None

    day = candidate.measured_at[:10]
    for existing_unit, existing_value, existing_at in existing:
        if existing_unit != candidate.unit:
            continue
        if existing_at[:10] != day:
            continue
        if abs(existing_value - candidate.value) > tolerance:
            return IssueDraft(
                issue_type=IssueType.VI_006,
                message=render_message(IssueType.VI_006, measure_type=candidate.measure_type),
                fact_indices=(candidate.fact_index,),
            )
    return None


def collect_multi_measurement_issue(*, candidate_count: int) -> IssueDraft | None:
    """Return the blocking ``VI-002`` for a multi-test document (``P0-R14``).

    The ``reason_code`` is ``multi_measurement_document`` rather than the generic
    ``fact_unverified``: the document is not mapped because its value-to-test
    association is ambiguous, and the message count is the number of candidate
    values that could not be attributed.
    """
    if candidate_count <= 1:
        return None
    return IssueDraft(
        issue_type=IssueType.VI_002,
        message=render_message(IssueType.VI_002, count=candidate_count),
        reason_code_override="multi_measurement_document",
    )


__all__ = [
    "MAX_MESSAGE_LENGTH",
    "MESSAGES",
    "REASON_CODES",
    "WRONG_PATIENT_ISSUE",
    "ConflictCandidate",
    "IssueDraft",
    "collect_flag_issues",
    "collect_multi_measurement_issue",
    "collect_source_conflict_issue",
    "collect_unverified_issue",
    "collect_wrong_patient_issue",
    "render_message",
]
