"""P4 C-35A: explicit current plus historical observations, pure/offline.

Not the P5 compare_observations tool. No implicit DB access, wall clock,
clinical interpretation, source verification, rule invocation or writes.
All data must already be patient-scoped; cross-patient records are errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.clock import parse_utc, to_utc
from app.core.enums import MeasureType
from app.services.monitoring import (
    ExcludedObservation,
    MonitoringInputError,
    ObservationSnapshot,
    admissibility_reason,
)

MAX_CURRENT = 6
MAX_HISTORY = 100


@dataclass(frozen=True, slots=True)
class ExplicitCurrentComparison:
    current_observation_id: str
    measure_type: str
    baseline_observation_id: str | None
    comparable: bool
    delta: Decimal | None
    incomparable_reason: str | None
    skip_reason: str | None
    trust_basis: str | None
    unit: str


@dataclass(frozen=True, slots=True)
class ExplicitHistoryResult:
    comparisons: tuple[ExplicitCurrentComparison, ...]
    excluded_history: tuple[ExcludedObservation, ...]


def _time(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        return to_utc(value)
    if isinstance(value, str):
        return parse_utc(value)
    raise MonitoringInputError("E_VALIDATION", "Expected an admissible timestamp.")


def _number(value: object) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise MonitoringInputError("E_VALIDATION", "Invalid comparison value.") from None
    if not amount.is_finite() or amount <= 0:
        raise MonitoringInputError("E_VALIDATION", "Invalid comparison value.")
    return amount


def compare_explicit_current_with_history(
    *,
    current: tuple[ObservationSnapshot, ...],
    history: tuple[ObservationSnapshot, ...],
    patient_id: str,
    as_of_utc: datetime,
    baseline_lookback_days: int,
) -> ExplicitHistoryResult:
    """Compare each explicitly selected current record against *prior* history.

    Rejected/malformed current readings return a typed not_admissible response.
    Rejected/malformed historical readings are excluded and never become a
    baseline. Duplicate IDs (including cross-set duplication) fail closed.
    """
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise MonitoringInputError("E_VALIDATION", "An aware clock is required.") from None
    if (
        not isinstance(current, tuple)
        or not 1 <= len(current) <= MAX_CURRENT
        or not isinstance(history, tuple)
        or len(history) > MAX_HISTORY
        or not isinstance(baseline_lookback_days, int)
        or isinstance(baseline_lookback_days, bool)
        or not 0 <= baseline_lookback_days <= 365
    ):
        raise MonitoringInputError("E_VALIDATION", "Invalid current/history selection or window.")

    seen: set[str] = set()
    usable_history: list[tuple[datetime, ObservationSnapshot]] = []
    excluded_history: list[ExcludedObservation] = []
    for row in (*current, *history):
        if not isinstance(row, ObservationSnapshot):
            raise MonitoringInputError("E_VALIDATION", "Typed observations required.")
        if row.id in seen:
            raise MonitoringInputError("E_VALIDATION", "Duplicate observation ID.")
        seen.add(row.id)
        reason = admissibility_reason(row, patient_id=patient_id, as_of_utc=clock)
        if row in history:
            if reason is not None:
                excluded_history.append(ExcludedObservation(row.id, reason))
            else:
                usable_history.append((_time(row.measured_at), row))

    result: list[ExplicitCurrentComparison] = []
    for row in sorted(current, key=lambda x: (x.measure_type, x.id)):
        reason = admissibility_reason(row, patient_id=patient_id, as_of_utc=clock)
        if reason is not None:
            result.append(
                ExplicitCurrentComparison(
                    current_observation_id=row.id,
                    measure_type=row.measure_type,
                    baseline_observation_id=None,
                    comparable=False,
                    delta=None,
                    incomparable_reason="not_admissible",
                    skip_reason=reason,
                    trust_basis=None,
                    unit=row.unit,
                )
            )
            continue
        stamp = _time(row.measured_at)
        candidates = [
            (prior_stamp, prior)
            for prior_stamp, prior in usable_history
            if prior.measure_type == row.measure_type
            and prior.unit == row.unit
            and stamp - timedelta(days=baseline_lookback_days) <= prior_stamp < stamp
        ]
        prior = max(candidates, key=lambda item: (item[0], item[1].id))[1] if candidates else None
        trust_basis = (
            "mixed"
            if prior is not None and row.trust_level != prior.trust_level
            else "doctor_verified"
            if row.trust_level == "doctor_verified"
            else "self_reported"
        )
        result.append(
            ExplicitCurrentComparison(
                current_observation_id=row.id,
                measure_type=row.measure_type,
                baseline_observation_id=prior.id if prior else None,
                comparable=prior is not None,
                delta=_number(row.value) - _number(prior.value) if prior else None,
                incomparable_reason=None if prior else "missing_baseline",
                skip_reason=None,
                trust_basis=trust_basis,
                unit=row.unit,
            )
        )
    return ExplicitHistoryResult(
        comparisons=tuple(result),
        excluded_history=tuple(
            sorted(excluded_history, key=lambda row: (row.observation_id, row.skip_reason))
        ),
    )


__all__ = [
    "MAX_CURRENT",
    "MAX_HISTORY",
    "ExplicitCurrentComparison",
    "ExplicitHistoryResult",
    "compare_explicit_current_with_history",
]
