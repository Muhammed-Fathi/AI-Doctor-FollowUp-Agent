"""Pure P4 monitoring comparisons for fictional educational measurements.

No database writes, policy thresholds, risk scoring, clinical inference, agent,
notification or task imports. Every time-dependent decision takes as_of_utc.

Contracts: REQ-MON-01/02, REQ-DATA-04, TOOL_CONTRACTS.md §3.4/3.5.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.clock import MAX_FUTURE_SKEW_MINUTES, parse_utc, to_utc
from app.core.enums import MEASURE_UNITS, MeasureType, TrustLevel, ValidationState


class MonitoringInputError(ValueError):
    """An invalid or out-of-scope monitoring request, without record content."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    """Immutable projection of a stored observation; no clinician-derived claims."""

    id: str
    patient_id: str
    measure_type: str
    value: Decimal | int | float | str
    unit: str
    measured_at: datetime | str | None
    validation: str
    trust_level: str


@dataclass(frozen=True, slots=True)
class ExcludedObservation:
    observation_id: str
    skip_reason: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    measure_type: str
    current_observation_id: str
    baseline_observation_id: str | None
    comparable: bool
    delta: Decimal | None  # Signed difference, never a clinical interpretation.
    incomparable_reason: str | None
    trust_basis: str
    unit: str


@dataclass(frozen=True, slots=True)
class MonitoringResult:
    comparisons: tuple[ComparisonResult, ...]
    excluded: tuple[ExcludedObservation, ...]


def _timestamp(value: datetime | str | None) -> datetime | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        if isinstance(value, datetime):
            return to_utc(value)
        if isinstance(value, str):
            return parse_utc(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return None


def _amount(value: Decimal | int | float | str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise MonitoringInputError("E_VALIDATION", "Observation value is invalid.") from None
    if not amount.is_finite() or amount <= 0:
        raise MonitoringInputError("E_VALIDATION", "Observation value is invalid.")
    return amount


def _validate_record(row: ObservationSnapshot, *, patient_id: str) -> None:
    # Abort the whole evaluation before returning anything if scopes are mixed.
    if row.patient_id != patient_id:
        raise MonitoringInputError("E_SCOPE_VIOLATION", "Observation patient scope mismatch.")
    if row.measure_type not in MeasureType._value2member_map_:
        raise MonitoringInputError("E_VALIDATION", "Unknown observation measure type.")
    if row.trust_level not in TrustLevel._value2member_map_:
        raise MonitoringInputError("E_VALIDATION", "Unknown observation trust label.")
    if row.validation not in ValidationState._value2member_map_:
        raise MonitoringInputError("E_VALIDATION", "Unknown observation validation label.")
    _amount(row.value)


def admissibility_reason(
    row: ObservationSnapshot, *, patient_id: str, as_of_utc: datetime
) -> str | None:
    """Return a documented skip reason or None for an admissible value.

    Invalid trust/measure/scope are errors, not unlabelled filter results.
    """
    _validate_record(row, patient_id=patient_id)
    if row.validation == ValidationState.REJECTED.value:
        return "validation_rejected"
    allowed = MEASURE_UNITS[MeasureType(row.measure_type)]
    if row.unit not in {unit.value for unit in allowed}:
        return "unit_mismatch"
    stamp = _timestamp(row.measured_at)
    if stamp is None:
        return "missing_timestamp"
    if stamp > to_utc(as_of_utc) + timedelta(minutes=MAX_FUTURE_SKEW_MINUTES):
        return "future_timestamp"
    return None


def _trust_basis(first: ObservationSnapshot, second: ObservationSnapshot | None) -> str:
    labels = {first.trust_level}
    if second is not None:
        labels.add(second.trust_level)
    if labels == {TrustLevel.DOCTOR_VERIFIED.value}:
        return "doctor_verified"
    if labels == {TrustLevel.SELF_REPORTED_VALIDATED.value}:
        return "self_reported"
    return "mixed"


def compare_observations(
    observations: Iterable[ObservationSnapshot],
    *,
    patient_id: str,
    as_of_utc: datetime,
    baseline_lookback_days: int,
) -> MonitoringResult:
    """Compare each type's latest eligible value with its latest prior value.

    Uses exact decimal subtraction (current minus most recent prior value).
    Rules must use abs(delta) when applying arbitrary demo parameters.
    Missing baselines remain incomparable; no imputation or unit conversion.
    The same immutable inputs and explicit clock yield the same ordered output.
    """
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise MonitoringInputError("E_VALIDATION", "as_of_utc must be timezone-aware.") from None
    if (
        not isinstance(baseline_lookback_days, int)
        or isinstance(baseline_lookback_days, bool)
        or not 0 <= baseline_lookback_days <= 365
    ):
        raise MonitoringInputError("E_VALIDATION", "Invalid baseline lookback period.")

    rows = tuple(observations)
    if len(rows) > 100:
        raise MonitoringInputError("E_VALIDATION", "Too many observations for one comparison.")
    eligible: dict[str, list[tuple[datetime, ObservationSnapshot]]] = {}
    excluded: list[ExcludedObservation] = []
    for row in rows:
        reason = admissibility_reason(row, patient_id=patient_id, as_of_utc=clock)
        if reason is not None:
            excluded.append(ExcludedObservation(row.id, reason))
            continue
        stamp = _timestamp(row.measured_at)
        assert stamp is not None  # The admissibility predicate has already checked this.
        eligible.setdefault(row.measure_type, []).append((stamp, row))

    results: list[ComparisonResult] = []
    for measure_type in MeasureType:
        ordered = sorted(eligible.get(measure_type.value, ()), key=lambda x: (x[0], x[1].id))
        if not ordered:
            continue
        current_time, current = ordered[-1]
        prior = [
            row
            for stamp, row in ordered[:-1]
            if current_time - timedelta(days=baseline_lookback_days) <= stamp < current_time
        ]
        baseline = prior[-1] if prior else None
        results.append(
            ComparisonResult(
                measure_type=measure_type.value,
                current_observation_id=current.id,
                baseline_observation_id=baseline.id if baseline else None,
                comparable=baseline is not None,
                delta=_amount(current.value) - _amount(baseline.value) if baseline else None,
                incomparable_reason=None if baseline else "missing_baseline",
                trust_basis=_trust_basis(current, baseline),
                unit=current.unit,
            )
        )
    return MonitoringResult(tuple(results), tuple(sorted(excluded, key=lambda x: x.observation_id)))


__all__ = [
    "ComparisonResult",
    "ExcludedObservation",
    "MonitoringInputError",
    "MonitoringResult",
    "ObservationSnapshot",
    "admissibility_reason",
    "compare_observations",
]
