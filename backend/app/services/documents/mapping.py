"""The closed verified-fact -> observation mapping (``map-1.0.0``).

This module is the **promotion boundary**. Everything before it deals with
unverified candidate facts; everything after it deals with comparable
measurements that downstream rules are allowed to read. Getting it wrong means
fabricating trusted clinical data, so the rules are deliberately rigid.

Contract source: ``DATA_DICTIONARY.md`` §3.3 and ``REQ-DATA-05``.

Rules implemented here
----------------------
1. A verified fact becomes an observation **only** if its normalized
   ``test_name`` and its unit both appear in the closed table.
2. Alias matching is **literal**: lowercase, collapse internal whitespace, strip a
   trailing colon, then exact set membership. No substring, prefix, stemming or
   fuzzy match.
3. The **test name** drives the mapping, not the unit. ``Hemoglobin 13.4 mg/dL``
   is still unmapped.
4. A recognized name with a non-matching unit maps to nothing.
5. **One measurement tuple per document.** Two distinct test names, or more than
   one unattributable value, means the document is *not* mapped at all and the
   gate raises ``VI-002``. There is no table detection and no heuristic
   association — this is a declared MVP limitation, not a feature gap.
6. ``measured_at`` comes from the verified report date at ``00:00Z``, never from
   the upload time or the demo clock.

Nothing here writes to the database. The caller inserts the observation in the
same transaction as the verification row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.enums import (
    MAPPING_TABLE,
    MAPPING_VERSION,
    DocumentUnit,
    FactField,
    FactVerificationStatus,
    MeasureType,
    QualityFlag,
)

#: Shape guard for a mapping version. A bare semver is not a mapping version.
MAPPING_VERSION_PATTERN = re.compile(r"^map-\d+\.\d+\.\d+$")

#: ``reason_code`` used when a document carries more than one measurement tuple.
MULTI_MEASUREMENT_REASON = "multi_measurement_document"

#: ``reason_code`` used for a verified name that is not in the closed table.
UNMAPPED_TEST_NAME_REASON = "unmapped_test_name"


def normalize_test_name(raw: str | None) -> str | None:
    """Return the canonical comparison form of a test name, or ``None``.

    Lowercase, collapse internal whitespace, strip a trailing colon. That is the
    entire normalization: anything more would be a guess about intent.
    """
    if raw is None:
        return None
    collapsed = " ".join(raw.split()).strip().lower()
    if collapsed.endswith(":"):
        collapsed = collapsed[:-1].strip()
    return collapsed or None


@dataclass(frozen=True, slots=True)
class MappingCandidate:
    """One ``(test_name, value, unit)`` tuple considered for mapping."""

    test_name: str
    value: float
    unit: str
    measure_type: MeasureType
    measured_at: str


@dataclass(frozen=True, slots=True)
class MappingDecision:
    """The outcome of applying the closed table to one document.

    Exactly one of three things happens:

    * ``mapped`` is a candidate and ``reason`` is ``None``;
    * ``reason`` is :data:`MULTI_MEASUREMENT_REASON` and nothing is mapped;
    * ``reason`` is :data:`UNMAPPED_TEST_NAME_REASON` and nothing is mapped.
    """

    mapped: MappingCandidate | None
    reason: str | None
    candidate_count: int

    @property
    def is_mapped(self) -> bool:
        """Return ``True`` when exactly one measurement tuple was produced."""
        return self.mapped is not None


@dataclass(frozen=True, slots=True)
class VerifiedFactView:
    """The minimum a verified fact must expose to be considered for mapping.

    Kept as a plain value object so the mapping is unit-testable without a
    database session or an ORM row.
    """

    field_name: str
    normalized_value: str | None
    unit: str | None
    verification_status: str


def _parse_float(value: str | None) -> float | None:
    """Return ``value`` as a float, or ``None`` when it is not numeric."""
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def measured_at_for(report_date: str | None) -> str | None:
    """Return ``<report_date>T00:00:00Z``, or ``None`` when the date is unusable.

    The report date is the *only* permitted origin of ``measured_at``. Upload
    time, ``checked_at``, ``as_of_utc`` and the wall clock are all forbidden by
    ``DATA_DICTIONARY.md`` §3.3 rule 5.
    """
    if report_date is None:
        return None
    candidate = report_date.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
        return None
    return f"{candidate}T00:00:00Z"


def resolve_alias(test_name: str | None) -> tuple[MeasureType, DocumentUnit] | None:
    """Return the closed-table entry for ``test_name``, or ``None``.

    Literal match only. A new alias is a mapping-version change, not a runtime
    guess, so no fuzzy fallback exists here.
    """
    normalized = normalize_test_name(test_name)
    if normalized is None:
        return None
    return MAPPING_TABLE.get(normalized)


def decide_mapping(
    facts: list[VerifiedFactView],
) -> MappingDecision:
    """Apply the closed table and the one-tuple rule to a document's facts.

    ``facts`` must be the document's facts with their **current** verification
    status. Only ``verified`` facts participate; a pending or rejected fact is
    invisible to the mapping, which is what stops a document from being mapped
    while a doctor has not finished deciding.

    Returns a :class:`MappingDecision`. When more than one distinct measurement
    tuple survives, **nothing** is mapped and ``reason`` explains why.
    """
    verified = [
        fact for fact in facts if fact.verification_status == FactVerificationStatus.VERIFIED.value
    ]

    # Group the verified fields the way the document presents them. The parser
    # emits one value and at most one test name per lab line, so the document's
    # distinct verified test names are the association candidates.
    test_names = [
        fact.normalized_value or fact.unit
        for fact in verified
        if fact.field_name == FactField.TEST_NAME.value
    ]
    resolved_names = {name for name in test_names if name}

    values = [
        fact
        for fact in verified
        if fact.field_name == FactField.VALUE.value and fact.normalized_value is not None
    ]
    units = {
        fact.normalized_value
        for fact in verified
        if fact.field_name == FactField.UNIT.value and fact.normalized_value
    }
    report_dates = [
        fact.normalized_value
        for fact in verified
        if fact.field_name == FactField.REPORT_DATE.value and fact.normalized_value
    ]

    # --- the association rule (P0-R14) -------------------------------------
    # Two distinct test names, or more than one value with no way to attribute
    # it, means the document is not mapped. We refuse to guess.
    if len({name for name in resolved_names if resolve_alias(name)}) > 1:
        return MappingDecision(
            mapped=None,
            reason=MULTI_MEASUREMENT_REASON,
            candidate_count=len(values),
        )
    if len(values) > 1:
        return MappingDecision(
            mapped=None,
            reason=MULTI_MEASUREMENT_REASON,
            candidate_count=len(values),
        )

    if len(resolved_names) != 1 or len(values) != 1:
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )

    name = next(iter(resolved_names))
    entry = resolve_alias(name)
    if entry is None:
        # A verified, well-formed value whose test name is not in the closed
        # table stays document-only. It is citable in a summary and produces no
        # comparison (Case A hemoglobin).
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )

    measure_type, required_unit = entry

    # The unit gates separately from the name.
    if len(units) != 1:
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )
    document_unit = next(iter(units))
    if document_unit != required_unit.value:
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )

    number = _parse_float(values[0].normalized_value)
    if number is None or number <= 0:
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )

    if len(report_dates) != 1:
        # An ambiguous or absent date is VI-003 territory; mapping must not
        # invent a timestamp.
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )
    measured_at = measured_at_for(report_dates[0])
    if measured_at is None:
        return MappingDecision(
            mapped=None,
            reason=UNMAPPED_TEST_NAME_REASON,
            candidate_count=len(values),
        )

    return MappingDecision(
        mapped=MappingCandidate(
            test_name=name,
            value=number,
            unit=required_unit.value,
            measure_type=measure_type,
            measured_at=measured_at,
        ),
        reason=None,
        candidate_count=1,
    )


def mapping_version_is_valid(version: str) -> bool:
    """Return ``True`` when ``version`` has the ``map-<major>.<minor>.<patch>`` form."""
    return bool(MAPPING_VERSION_PATTERN.match(version))


def current_mapping_version() -> str:
    """Return the mapping version this build implements."""
    return MAPPING_VERSION


#: Flags that make a value unusable. Any one of them blocks promotion.
BLOCKING_FLAGS: frozenset[QualityFlag] = frozenset(
    {
        QualityFlag.LOW_CONFIDENCE,
        QualityFlag.AMBIGUOUS_DATE,
        QualityFlag.AMBIGUOUS_UNIT,
        QualityFlag.UNPARSEABLE_VALUE,
        QualityFlag.SOURCE_CONFLICT,
        QualityFlag.PAGE_MISSING,
    }
)


__all__ = [
    "BLOCKING_FLAGS",
    "MAPPING_VERSION_PATTERN",
    "MULTI_MEASUREMENT_REASON",
    "UNMAPPED_TEST_NAME_REASON",
    "MappingCandidate",
    "MappingDecision",
    "VerifiedFactView",
    "current_mapping_version",
    "decide_mapping",
    "mapping_version_is_valid",
    "measured_at_for",
    "normalize_test_name",
    "resolve_alias",
]
