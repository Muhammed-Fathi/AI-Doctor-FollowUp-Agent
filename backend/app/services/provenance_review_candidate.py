"""P4-2d pure, offline DR-006/DR-008 candidate checks over SYNTHETIC records.

Not wired into the approved policy, DB, API, verification gate or P5 agents.
Source lineage fields are fixture assertions, NOT proof of server verification.
A future scoped DB adapter and real verification gate are mandatory before use.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from itertools import combinations

from app.core.clock import format_utc, parse_utc, to_utc
from app.core.enums import TrustLevel
from app.services.demo_rules_candidate import CandidateReviewFlag, CandidateRuleError
from app.services.monitoring import (
    MonitoringInputError,
    ObservationSnapshot,
    compare_observation_history,
)

_RULES = frozenset({"DR-006", "DR-008"})
_VERSION = re.compile(r"candidate-p4-2d-[0-9]{1,20}\.[0-9]{1,20}\.[0-9]{1,20}\Z")
_LABELS = {
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "heart_rate": "Heart rate",
    "glucose": "Glucose",
}
_ORDER = {"verification_needed": 0, "data_quality": 1}
_MAX_ROWS = 100


@dataclass(frozen=True, slots=True)
class CandidateProvenancePolicy:
    """Explicit offline test input, never an active or approved demo policy."""

    policy_version: str
    demo_only: bool
    demo_as_of_utc: datetime
    conflict_tolerance: Decimal | str | int
    max_items_per_type: int
    enabled_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateRecordedObservation:
    """Synthetic stored-row projection; not a trusted DB-backed projection."""

    observation: ObservationSnapshot
    created_at: datetime | str | None = None
    source: str | None = None
    source_fact_id: str | None = None
    source_document_id: str | None = None
    source_fact_verification_status: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateEvidenceExclusion:
    observation_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class CandidateProvenanceResult:
    flags: tuple[CandidateReviewFlag, ...]
    excluded: tuple[CandidateEvidenceExclusion, ...]
    disabled_rule_ids: tuple[str, ...]
    policy_version: str
    demo_only: bool = True


def _clock(value: datetime | str | None) -> datetime | None:
    try:
        if isinstance(value, datetime):
            return to_utc(value)
        if isinstance(value, str):
            return parse_utc(value)
    except (ValueError, TypeError, OverflowError, AttributeError):
        return None
    return None


def _value(amount: Decimal | str | int | float) -> Decimal:
    try:
        number = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        raise CandidateRuleError("E_VALIDATION", "Invalid candidate numeric value.") from None
    if not number.is_finite() or number <= 0:
        raise CandidateRuleError("E_VALIDATION", "Invalid candidate numeric value.")
    return number


def _policy(policy: CandidateProvenancePolicy, clock: datetime) -> Decimal:
    if not isinstance(policy, CandidateProvenancePolicy):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid candidate policy type.")
    if (
        not isinstance(policy.policy_version, str)
        or _VERSION.fullmatch(policy.policy_version) is None
        or policy.demo_only is not True
    ):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid offline policy identity.")
    try:
        matches = to_utc(policy.demo_as_of_utc) == clock
    except (TypeError, ValueError, AttributeError):
        matches = False
    if not matches:
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Candidate clock mismatch.")
    if (
        not isinstance(policy.max_items_per_type, int)
        or isinstance(policy.max_items_per_type, bool)
        or not 1 <= policy.max_items_per_type <= 3
    ):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid candidate item cap.")
    rules = policy.enabled_rule_ids
    if (
        not isinstance(rules, tuple)
        or any(not isinstance(name, str) for name in rules)
        or len(set(rules)) != len(rules)
        or any(name not in _RULES for name in rules)
    ):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Unsupported candidate rule.")
    try:
        tolerance = Decimal(str(policy.conflict_tolerance))
    except (InvalidOperation, ValueError, TypeError):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid candidate tolerance.") from None
    if (
        isinstance(policy.conflict_tolerance, bool)
        or not tolerance.is_finite()
        or not Decimal(0) <= tolerance <= Decimal(1000000)
    ):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid candidate tolerance.")
    return tolerance


def _verified_document_source(entry: CandidateRecordedObservation) -> bool:
    """Candidate shape-check ONLY: cannot independently verify fixture assertions."""
    row = entry.observation
    return (
        row.trust_level == TrustLevel.DOCTOR_VERIFIED.value
        and entry.source == "verified_document"
        and entry.source_fact_verification_status == "verified"
        and isinstance(entry.source_fact_id, str)
        and bool(entry.source_fact_id.strip())
        and isinstance(entry.source_document_id, str)
        and bool(entry.source_document_id.strip())
    )


def _trust(a: ObservationSnapshot, b: ObservationSnapshot) -> str:
    if a.trust_level == b.trust_level == TrustLevel.DOCTOR_VERIFIED.value:
        return "doctor_verified"
    if a.trust_level == b.trust_level == TrustLevel.SELF_REPORTED_VALIDATED.value:
        return "self_reported"
    return "mixed"


def _flag(
    *,
    patient_id: str,
    policy: CandidateProvenancePolicy,
    rule_id: str,
    reason: str,
    hint: str,
    text: str,
    first: ObservationSnapshot,
    second: ObservationSnapshot,
) -> CandidateReviewFlag:
    evidence = tuple(sorted((f"observation:{first.id}", f"observation:{second.id}")))
    trust = _trust(first, second)
    suffix = {
        "doctor_verified": "",
        "self_reported": " (self-reported)",
        "mixed": " (includes self-reported values)",
    }[trust]
    message = text.removesuffix(".") + suffix + "."
    if len(message) > 240:
        raise CandidateRuleError("E_VALIDATION", "Candidate message too long.")
    digest = sha256("|".join((patient_id, rule_id, *evidence, trust)).encode("utf-8"))
    return CandidateReviewFlag(
        rule_id=rule_id,
        reason_code=reason,
        workflow_hint=hint,
        message=message,
        evidence=evidence,
        trust_basis=trust,
        policy_version=policy.policy_version,
        dedupe_key=digest.hexdigest(),
    )


def evaluate_offline_provenance_candidates(
    *,
    patient_id: str,
    records: tuple[CandidateRecordedObservation, ...],
    policy: CandidateProvenancePolicy,
    as_of_utc: datetime,
    blocking_fact_count: int,
) -> CandidateProvenanceResult:
    """Evaluate two *unwired* synthetic rules; no real verification assurance.

    In particular, source attributes and the blocking count are supplied by
    the fixture, NOT independently queried from a scoped database.
    """
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid evaluation clock.") from None
    tolerance = _policy(policy, clock)
    if (
        not isinstance(blocking_fact_count, int)
        or isinstance(blocking_fact_count, bool)
        or not 0 <= blocking_fact_count <= 40
    ):
        raise CandidateRuleError("E_VALIDATION", "Invalid test-only blocking fact count.")
    if blocking_fact_count:
        raise CandidateRuleError("E_UNVERIFIED_FACT", "Offline fixture has blocking facts.")
    if not isinstance(records, tuple) or len(records) > _MAX_ROWS:
        raise CandidateRuleError("E_VALIDATION", "Invalid candidate record collection.")
    if any(not isinstance(entry, CandidateRecordedObservation) for entry in records):
        raise CandidateRuleError("E_VALIDATION", "Typed synthetic evidence is required.")

    observations = tuple(entry.observation for entry in records)
    try:
        checked = compare_observation_history(
            observations, patient_id=patient_id, as_of_utc=clock, baseline_lookback_days=0
        )
    except (MonitoringInputError, AttributeError, TypeError) as exc:
        code = exc.code if isinstance(exc, MonitoringInputError) else "E_VALIDATION"
        raise CandidateRuleError(code, "Candidate observation evidence rejected.") from None

    skipped = {item.observation_id for item in checked.excluded}
    exclusions = [
        CandidateEvidenceExclusion(item.observation_id, item.skip_reason)
        for item in checked.excluded
    ]
    enabled = frozenset(policy.enabled_rule_ids)
    eligible: list[tuple[CandidateRecordedObservation, datetime, datetime | None]] = []
    fact_documents: dict[str, str] = {}
    for entry in records:
        row = entry.observation
        if row.id in skipped:
            continue
        measured = _clock(row.measured_at)
        if measured is None:
            raise CandidateRuleError("E_VALIDATION", "Invalid admitted timestamp.")
        created = _clock(entry.created_at)
        if "DR-008" in enabled and created is None:
            exclusions.append(CandidateEvidenceExclusion(row.id, "creation_time_unavailable"))
        if "DR-006" in enabled and not _verified_document_source(entry):
            exclusions.append(CandidateEvidenceExclusion(row.id, "verified_lineage_unavailable"))
        if (
            "DR-006" in enabled
            and _verified_document_source(entry)
            and entry.source_fact_id is not None
            and entry.source_document_id is not None
        ):
            prior = fact_documents.setdefault(entry.source_fact_id, entry.source_document_id)
            if prior != entry.source_document_id:
                raise CandidateRuleError("E_VALIDATION", "Inconsistent source fact lineage.")
        eligible.append((entry, measured, created))

    outputs: list[CandidateReviewFlag] = []
    for (a, measured_a, created_a), (b, measured_b, created_b) in combinations(
        sorted(eligible, key=lambda item: item[0].observation.id), 2
    ):
        first, second = a.observation, b.observation
        if first.measure_type != second.measure_type or first.unit != second.unit:
            continue
        # A replay of the *same* source fact is not an independent observation.
        if a.source_fact_id and a.source_fact_id == b.source_fact_id:
            continue

        if (
            "DR-006" in enabled
            and measured_a == measured_b
            and _verified_document_source(a)
            and _verified_document_source(b)
            and a.source_document_id != b.source_document_id
            and abs(_value(first.value) - _value(second.value)) > tolerance
        ):
            outputs.append(
                _flag(
                    patient_id=patient_id,
                    policy=policy,
                    rule_id="DR-006",
                    reason="verified_source_conflict",
                    hint="verification_needed",
                    text=(
                        f"Two verified sources disagree for {_LABELS[first.measure_type]} "
                        f"at {format_utc(measured_a)}."
                    ),
                    first=first,
                    second=second,
                )
            )

        if "DR-008" in enabled:
            exact_duplicate = measured_a == measured_b and _value(first.value) == _value(
                second.value
            )
            out_of_order = (
                created_a is not None
                and created_b is not None
                and (
                    (created_a > created_b and measured_a < measured_b)
                    or (created_b > created_a and measured_b < measured_a)
                )
            )
            if exact_duplicate or out_of_order:
                outputs.append(
                    _flag(
                        patient_id=patient_id,
                        policy=policy,
                        rule_id="DR-008",
                        reason="duplicate_or_out_of_order",
                        hint="data_quality",
                        text=(
                            f"A repeated or out-of-order entry was detected "
                            f"for {_LABELS[first.measure_type]}."
                        ),
                        first=first,
                        second=second,
                    )
                )

    counts: dict[str, int] = {}
    types = {entry.observation.id: entry.observation.measure_type for entry in records}
    for item in outputs:
        observation_id = item.evidence[0].split(":", 1)[1]
        measure = types[observation_id]
        counts[measure] = counts.get(measure, 0) + 1
        if counts[measure] > policy.max_items_per_type:
            raise CandidateRuleError("E_RULE_POLICY_INVALID", "Candidate item cap exceeded.")

    return CandidateProvenanceResult(
        flags=tuple(
            sorted(
                outputs, key=lambda item: (_ORDER[item.workflow_hint], item.rule_id, item.evidence)
            )
        ),
        excluded=tuple(
            sorted(set(exclusions), key=lambda item: (item.observation_id, item.reason))
        ),
        disabled_rule_ids=tuple(sorted(_RULES - enabled)),
        policy_version=policy.policy_version,
    )


__all__ = [
    "CandidateEvidenceExclusion",
    "CandidateProvenancePolicy",
    "CandidateProvenanceResult",
    "CandidateRecordedObservation",
    "evaluate_offline_provenance_candidates",
]
