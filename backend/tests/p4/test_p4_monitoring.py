"""P4-1 offline regressions: REQ-MON-01/02, REQ-DATA-04 and NEG cross-scope."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.monitoring import (
    MonitoringInputError,
    ObservationSnapshot,
    compare_observations,
)

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)
PATIENT_A = "11111111-1111-4111-8111-111111111111"
PATIENT_B = "22222222-2222-4222-8222-222222222222"


def row(
    identifier: str,
    when: datetime | str | None,
    value: int | str,
    *,
    measure_type: str = "systolic_bp",
    patient: str = PATIENT_A,
    unit: str = "mmHg",
    validation: str = "ok",
    trust: str = "self_reported_validated",
) -> ObservationSnapshot:
    return ObservationSnapshot(
        id=identifier,
        patient_id=patient,
        measure_type=measure_type,
        value=value,
        unit=unit,
        measured_at=when,
        validation=validation,
        trust_level=trust,
    )


def run(*items: ObservationSnapshot, days: int = 90, clock: datetime = AS_OF):
    return compare_observations(
        items, patient_id=PATIENT_A, as_of_utc=clock, baseline_lookback_days=days
    )


def test_req_mon_01_case_b_uses_most_recent_prior_not_oldest() -> None:
    result = run(
        row("oct02", "2026-10-02T08:00:00Z", 138),
        row("nov03", "2026-11-03T08:00:00Z", 158),
        row("oct20", "2026-10-20T08:00:00Z", 146),
    )
    assert len(result.comparisons) == 1
    actual = result.comparisons[0]
    assert (actual.current_observation_id, actual.baseline_observation_id) == (
        "nov03", "oct20"
    )
    assert actual.comparable is True
    assert actual.delta == Decimal("12")
    assert actual.trust_basis == "self_reported"
    assert result.excluded == ()


def test_req_mon_02_missing_baseline_is_incomparable_without_imputation() -> None:
    result = run(row("only", "2026-11-03T08:00:00Z", 158))
    actual = result.comparisons[0]
    assert actual.baseline_observation_id is None
    assert actual.delta is None
    assert actual.comparable is False
    assert actual.incomparable_reason == "missing_baseline"


def test_req_mon_01_lookback_uses_current_measurement_not_as_of() -> None:
    result = run(
        row("too-old", "2026-05-01T00:00:00Z", 138),
        row("current", "2026-11-03T08:00:00Z", 158),
        days=90,
    )
    assert result.comparisons[0].baseline_observation_id is None


def test_req_mon_01_exact_boundary_is_included() -> None:
    current = datetime(2026, 11, 3, tzinfo=UTC)
    result = run(row("prior", current - timedelta(days=90), 140), row("now", current, 150))
    assert result.comparisons[0].delta == Decimal("10")


def test_req_data_04_rejected_and_incompatible_unit_do_not_shift_baseline() -> None:
    result = run(
        row("valid", "2026-10-20T08:00:00Z", 146),
        row("rejected", "2026-11-01T08:00:00Z", 190, validation="rejected"),
        row("unit", "2026-11-02T08:00:00Z", 200, unit="bpm"),
        row("current", "2026-11-03T08:00:00Z", 158),
    )
    assert result.comparisons[0].baseline_observation_id == "valid"
    assert result.comparisons[0].delta == Decimal("12")
    assert [(x.observation_id, x.skip_reason) for x in result.excluded] == [
        ("rejected", "validation_rejected"),
        ("unit", "unit_mismatch"),
    ]


def test_req_mon_02_missing_and_future_time_are_reported_not_hidden() -> None:
    result = run(
        row("null", None, 151),
        row("naive", datetime(2026, 11, 1), 151),
        row("future", AS_OF + timedelta(minutes=6), 151),
        row("allowed", AS_OF + timedelta(minutes=5), 152),
    )
    assert result.comparisons[0].current_observation_id == "allowed"
    assert [(x.observation_id, x.skip_reason) for x in result.excluded] == [
        ("future", "future_timestamp"),
        ("naive", "missing_timestamp"),
        ("null", "missing_timestamp"),
    ]


def test_req_data_04_self_reported_and_mixed_are_never_mislabelled() -> None:
    mixed = run(
        row("old", "2026-10-20T08:00:00Z", 146, trust="doctor_verified"),
        row("current", "2026-11-03T08:00:00Z", 158),
    )
    assert mixed.comparisons[0].trust_basis == "mixed"
    verified = run(
        row("old", "2026-10-20T08:00:00Z", 146, trust="doctor_verified"),
        row("current", "2026-11-03T08:00:00Z", 158, trust="doctor_verified"),
    )
    assert verified.comparisons[0].trust_basis == "doctor_verified"


def test_req_mon_01_decimal_arithmetic_is_exact() -> None:
    result = run(
        row("before", "2026-10-20T08:00:00Z", "0.1"),
        row("now", "2026-11-03T08:00:00Z", "0.3"),
    )
    assert result.comparisons[0].delta == Decimal("0.2")


def test_req_mon_03_same_timestamp_duplicate_does_not_become_baseline() -> None:
    result = run(
        row("a", "2026-11-03T08:00:00Z", 146),
        row("b", "2026-11-03T08:00:00Z", 158),
    )
    assert result.comparisons[0].current_observation_id == "b"
    assert result.comparisons[0].baseline_observation_id is None


def test_req_mon_01_result_is_order_independent_and_clock_injected() -> None:
    a = row("a", "2026-10-20T08:00:00Z", 146)
    b = row("b", "2026-11-03T08:00:00Z", 158)
    assert run(a, b) == run(b, a)
    assert run(a, b) == run(a, b, clock=AS_OF)


def test_req_sec_01_cross_patient_fails_before_returning_any_data() -> None:
    with pytest.raises(MonitoringInputError, match="scope") as error:
        run(row("valid", "2026-11-03T08:00:00Z", 158), row("other", AS_OF, 145, patient=PATIENT_B))
    assert error.value.code == "E_SCOPE_VIOLATION"


@pytest.mark.parametrize("label", ["verified", "untrusted", ""])
def test_req_data_04_invalid_trust_fails_closed(label: str) -> None:
    with pytest.raises(MonitoringInputError) as error:
        run(row("one", AS_OF, 145, trust=label))
    assert error.value.code == "E_VALIDATION"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "not-a-number", 0, -10])
def test_req_mon_02_invalid_value_fails_closed(value: str | int) -> None:
    with pytest.raises(MonitoringInputError) as error:
        run(row("one", AS_OF, value))
    assert error.value.code == "E_VALIDATION"


def test_req_mon_01_naive_as_of_rejected() -> None:
    with pytest.raises(MonitoringInputError) as error:
        run(row("a", AS_OF, 140), clock=datetime(2026, 11, 14))
    assert error.value.code == "E_VALIDATION"


def test_req_mon_01_max_input_and_lookback_bounds() -> None:
    with pytest.raises(MonitoringInputError):
        run(*(row(str(i), AS_OF, 140) for i in range(101)))
    with pytest.raises(MonitoringInputError):
        run(row("a", AS_OF, 140), days=366)
    with pytest.raises(MonitoringInputError):
        run(row("a", AS_OF, 140), days=True)
