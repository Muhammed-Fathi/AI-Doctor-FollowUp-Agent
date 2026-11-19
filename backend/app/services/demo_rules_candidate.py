"""P4-2A offline candidate review rules; NOT an enabled agent tool or policy.

Only DR-001/003/005/009 are implemented. DR-006/008 and the proposed
official demo policy await a separate owner review. The module has no API,
database, workflow, task, or notification integration.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256

from app.core.clock import parse_utc, to_utc
from app.core.enums import MEASURE_PLAUSIBLE_BANDS, MeasureType, TrustLevel
from app.services.monitoring import (
    MonitoringInputError,
    MonitoringResult,
    ObservationSnapshot,
    compare_observation_history,
)

_SUPPORTED = frozenset({"DR-001", "DR-003", "DR-005", "DR-009"})
_ALL_ACTIVE = frozenset({"DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009"})
_LABELS = {
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "heart_rate": "Heart rate",
    "glucose": "Glucose",
}
_HINT_ORDER = {"verification_needed": 0, "data_quality": 1, "change_to_review": 2}


class CandidateRuleError(ValueError):
    """Typed error; callers must emit no flags on any error."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CandidateDemoPolicy:
    """Explicit test-only demo parameters; no default or clinical activation."""

    policy_version: str
    demo_only: bool
    demo_as_of_utc: datetime
    baseline_lookback_days: int
    stale_measurement_days: int
    demo_delta_systolic_mmHg: Decimal | str | int
    demo_delta_diastolic_mmHg: Decimal | str | int
    demo_delta_heart_rate_bpm: Decimal | str | int
    demo_delta_glucose_mgdl: Decimal | str | int
    max_items_per_type: int
    enabled_rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateReviewFlag:
    rule_id: str
    reason_code: str
    workflow_hint: str
    message: str
    evidence: tuple[str, ...]
    trust_basis: str
    policy_version: str
    dedupe_key: str
    demo_only: bool = True


@dataclass(frozen=True, slots=True)
class CandidateReviewResult:
    flags: tuple[CandidateReviewFlag, ...]
    disabled_rule_ids: tuple[str, ...]
    policy_version: str
    demo_only: bool = True


def _threshold(value: Decimal | str | int) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid demo parameter.") from None
    if not amount.is_finite() or not Decimal(0) <= amount <= Decimal(1000000):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Parameter out of bounds.")
    return amount


def _check_policy(policy: CandidateDemoPolicy, clock: datetime) -> dict[str, Decimal]:
    if not isinstance(policy, CandidateDemoPolicy):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Unknown policy type.")
    version = (
        re.fullmatch(r"candidate-p4-2a-([0-9]{1,20})\.([0-9]{1,20})\.([0-9]{1,20})", policy.policy_version)
        if isinstance(policy.policy_version, str)
        else None
    )
    if version is None:
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Not a candidate policy.")
    if policy.demo_only is not True:
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Only test policies are accepted.")
    try:
        if to_utc(policy.demo_as_of_utc) != clock:
            raise CandidateRuleError("E_RULE_POLICY_INVALID", "Clock does not match policy.")
    except (TypeError, AttributeError, ValueError):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid policy clock.") from None
    for days in (policy.baseline_lookback_days, policy.stale_measurement_days):
        if not isinstance(days, int) or isinstance(days, bool) or not 0 < days <= 365:
            raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid day limit.")
    cap = policy.max_items_per_type
    if not isinstance(cap, int) or isinstance(cap, bool) or not 1 <= cap <= 3:
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid item cap.")
    rules = policy.enabled_rule_ids
    if not isinstance(rules, tuple) or any(not isinstance(x, str) for x in rules):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid rule list.")
    if len(set(rules)) != len(rules) or any(x not in _SUPPORTED for x in rules):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Retired or unimplemented rule.")
    if "DR-009" in rules and tuple(int(n) for n in version.groups()) < (0, 2, 0):
        raise CandidateRuleError(
            "E_RULE_POLICY_INVALID", "New candidate rule requires version bump."
        )
    return {
        "systolic_bp": _threshold(policy.demo_delta_systolic_mmHg),
        "diastolic_bp": _threshold(policy.demo_delta_diastolic_mmHg),
        "heart_rate": _threshold(policy.demo_delta_heart_rate_bpm),
        "glucose": _threshold(policy.demo_delta_glucose_mgdl),
    }


def _timestamp(value: datetime | str | None) -> datetime:
    try:
        if isinstance(value, datetime):
            return to_utc(value)
        if isinstance(value, str):
            return parse_utc(value)
    except (TypeError, ValueError, AttributeError):
        pass
    raise CandidateRuleError("E_VALIDATION", "Unparseable evidence timestamp.")


def _message(base: str, trust: str) -> str:
    suffix = {
        "self_reported": " (self-reported)",
        "mixed": " (includes self-reported values)",
        "doctor_verified": "",
    }.get(trust)
    if suffix is None:
        raise CandidateRuleError("E_VALIDATION", "Unknown trust basis.")
    result = base.removesuffix(".") + suffix + "."
    if len(result) > 240:
        raise CandidateRuleError("E_VALIDATION", "Message length exceeded.")
    return result


def _flag(
    *,
    patient_id: str,
    policy: CandidateDemoPolicy,
    rule: str,
    reason: str,
    hint: str,
    message: str,
    evidence: tuple[str, ...],
    trust: str,
) -> CandidateReviewFlag:
    refs = tuple(sorted({f"observation:{x}" for x in evidence}))
    if len(refs) != len(evidence) or not refs:
        raise CandidateRuleError("E_VALIDATION", "Duplicate or empty evidence.")
    digest = sha256("|".join((patient_id, rule, *refs, trust)).encode("utf-8")).hexdigest()
    return CandidateReviewFlag(
        rule_id=rule,
        reason_code=reason,
        workflow_hint=hint,
        message=_message(message, trust),
        evidence=refs,
        trust_basis=trust,
        policy_version=policy.policy_version,
        dedupe_key=digest,
    )


def evaluate_candidate_review_subset(
    *,
    patient_id: str,
    observations: tuple[ObservationSnapshot, ...],
    comparisons: MonitoringResult,
    policy: CandidateDemoPolicy,
    as_of_utc: datetime,
    blocking_fact_count: int,
) -> CandidateReviewResult:
    """Evaluate a quarantined offline subset; NOT the agent tool in section 3.7.

    The external verification gate is NOT implemented. It must be integrated
    with the real scoped service before any rule engine is exposed to users.
    """
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise CandidateRuleError("E_RULE_POLICY_INVALID", "Invalid evaluation clock.") from None
    params = _check_policy(policy, clock)
    if (
        not isinstance(blocking_fact_count, int)
        or isinstance(blocking_fact_count, bool)
        or not 0 <= blocking_fact_count <= 40
    ):
        raise CandidateRuleError("E_VALIDATION", "Invalid verification count.")
    if blocking_fact_count:
        raise CandidateRuleError("E_UNVERIFIED_FACT", "Verification is required.")
    if not isinstance(comparisons, MonitoringResult) or not isinstance(observations, tuple):
        raise CandidateRuleError("E_VALIDATION", "Typed comparison evidence required.")
    try:
        expected = compare_observation_history(
            observations,
            patient_id=patient_id,
            as_of_utc=clock,
            baseline_lookback_days=policy.baseline_lookback_days,
        )
    except MonitoringInputError as error:
        raise CandidateRuleError(error.code, "Comparison evidence was rejected.") from None
    if expected != comparisons:
        raise CandidateRuleError("E_VALIDATION", "Comparison evidence mismatch.")

    by_id = {row.id: row for row in observations}
    enabled = frozenset(policy.enabled_rule_ids)
    output: list[CandidateReviewFlag] = []
    for comp in comparisons.comparisons:
        if comp.measure_type not in MeasureType._value2member_map_:
            raise CandidateRuleError("E_VALIDATION", "Invalid comparison type.")
        current = by_id[comp.current_observation_id]
        label = _LABELS[comp.measure_type]
        trust = comp.trust_basis
        if "DR-001" in enabled and not comp.comparable:
            output.append(
                _flag(
                    patient_id=patient_id,
                    policy=policy,
                    rule="DR-001",
                    reason="missing_baseline",
                    hint="data_quality",
                    message=f"No previous recorded {label} to compare against.",
                    evidence=(current.id,),
                    trust=trust,
                )
            )
        if "DR-003" in enabled:
            days = (clock - _timestamp(current.measured_at)).days
            if days > policy.stale_measurement_days:
                output.append(
                    _flag(
                        patient_id=patient_id,
                        policy=policy,
                        rule="DR-003",
                        reason="measurement_stale",
                        hint="data_quality",
                        message=f"The most recent {label} was recorded {days} days ago.",
                        evidence=(current.id,),
                        trust=trust,
                    )
                )
        if "DR-005" in enabled and comp.comparable:
            if comp.delta is None or comp.baseline_observation_id is None:
                raise CandidateRuleError("E_VALIDATION", "Baseline not supplied.")
            delta = abs(comp.delta)
            if delta > params[comp.measure_type]:
                amount = format(delta.normalize(), "f")
                output.append(
                    _flag(
                        patient_id=patient_id,
                        policy=policy,
                        rule="DR-005",
                        reason="change_exceeds_demo_parameter",
                        hint="change_to_review",
                        message=(
                            f"{label} differs from the previous recorded value "
                            f"by {amount} {comp.unit}."
                        ),
                        evidence=(current.id, comp.baseline_observation_id),
                        trust=trust,
                    )
                )
    # DR-009 evaluates each *admissible* recorded value, including historical
    # rows. This is a deterministic typo/unit-check prompt, not a care boundary.
    # A warning-labelled value stays admissible; its trust label never changes.
    if "DR-009" in enabled:
        skipped = {entry.observation_id for entry in expected.excluded}
        for row in sorted(observations, key=lambda entry: entry.id):
            if row.id in skipped:
                continue
            band = MEASURE_PLAUSIBLE_BANDS[MeasureType(row.measure_type)]
            value = Decimal(str(row.value))
            if value < Decimal(str(band[0])) or value > Decimal(str(band[1])):
                trust = (
                    "doctor_verified"
                    if row.trust_level == TrustLevel.DOCTOR_VERIFIED.value
                    else "self_reported"
                )
                output.append(
                    _flag(
                        patient_id=patient_id,
                        policy=policy,
                        rule="DR-009",
                        reason="implausible_value",
                        hint="data_quality",
                        message=(
                            "A recorded value is outside the demo plausibility range "
                            "and may be a typo."
                        ),
                        evidence=(row.id,),
                        trust=trust,
                    )
                )
    counts: dict[str, int] = {}
    types_by_id = {row.id: row.measure_type for row in observations}
    for item in output:
        first_ref = item.evidence[0].split(":", 1)[1]
        measure = types_by_id[first_ref]
        counts[measure] = counts.get(measure, 0) + 1
        if counts[measure] > policy.max_items_per_type:
            raise CandidateRuleError("E_RULE_POLICY_INVALID", "Candidate item cap exceeded.")
    ordered = tuple(
        sorted(
            output,
            key=lambda item: (_HINT_ORDER[item.workflow_hint], item.rule_id, item.evidence),
        )
    )
    return CandidateReviewResult(
        flags=ordered,
        disabled_rule_ids=tuple(sorted(_ALL_ACTIVE - enabled)),
        policy_version=policy.policy_version,
    )


__all__ = [
    "CandidateDemoPolicy",
    "CandidateReviewFlag",
    "CandidateReviewResult",
    "CandidateRuleError",
    "evaluate_candidate_review_subset",
]
