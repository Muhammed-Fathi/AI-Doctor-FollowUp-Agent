"""P4 C-35A pure selected-current/history contract: no DB or runtime policy."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from app.services.monitoring import MonitoringInputError, ObservationSnapshot
from app.services.p4_explicit_history import compare_explicit_current_with_history

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)


def obs(
    id: str,
    value: float = 120,
    date: str = "2026-11-03T09:00:00Z",
    *,
    patient: str = "synthetic-a",
    trust: str = "self_reported_validated",
    validation: str = "ok",
    unit: str = "mmHg",
) -> ObservationSnapshot:
    return ObservationSnapshot(
        id=id,
        patient_id=patient,
        measure_type="systolic_bp",
        value=value,
        unit=unit,
        measured_at=date,
        validation=validation,
        trust_level=trust,
    )


def compare(current, history, days: int = 90):
    return compare_explicit_current_with_history(
        current=tuple(current),
        history=tuple(history),
        patient_id="synthetic-a",
        as_of_utc=CLOCK,
        baseline_lookback_days=days,
    )


def test_explicit_history_uses_latest_prior_not_nearest_future() -> None:
    current = obs("current", 158)
    history = [
        obs("ancient", 130, "2026-08-01T09:00:00Z"),
        obs("older", 140, "2026-10-01T09:00:00Z"),
        obs("nearest", 146, "2026-11-02T09:00:00Z"),
        obs("future", 170, "2026-11-04T09:00:00Z"),
    ]
    actual = compare([current], history)
    reading = actual.comparisons[0]
    assert reading.comparable
    assert reading.baseline_observation_id == "nearest"
    assert reading.delta == 12
    assert reading.trust_basis == "self_reported"
    assert reading.skip_reason is None


def test_current_rejected_reports_not_admissible_without_e_unverified_fact() -> None:
    result = compare(
        [obs("current", validation="rejected")],
        [obs("baseline", 110, "2026-10-01T09:00:00Z")],
    )
    item = result.comparisons[0]
    assert not item.comparable
    assert item.delta is None
    assert item.incomparable_reason == "not_admissible"
    assert item.skip_reason == "validation_rejected"
    assert item.trust_basis is None


def test_current_future_and_wrong_unit_have_typed_exclusions() -> None:
    bad_unit = obs("unit", unit="bpm")
    future = obs("future", date="2026-11-15T09:00:00Z")
    result = compare([bad_unit, future], [])
    by_id = {item.current_observation_id: item for item in result.comparisons}
    assert by_id["unit"].skip_reason == "unit_mismatch"
    assert by_id["future"].skip_reason == "future_timestamp"


def test_history_rejected_unit_and_future_are_excluded_never_baselines() -> None:
    result = compare(
        [obs("current", 145)],
        [
            obs("rejected", 100, "2026-11-02T09:00:00Z", validation="rejected"),
            obs("unit", 110, "2026-11-02T09:00:00Z", unit="bpm"),
            obs("future", 110, "2026-11-15T09:00:00Z"),
        ],
    )
    assert not result.comparisons[0].comparable
    assert result.comparisons[0].incomparable_reason == "missing_baseline"
    assert {item.skip_reason for item in result.excluded_history} == {
        "validation_rejected",
        "unit_mismatch",
        "future_timestamp",
    }


def test_mixed_trust_keeps_self_report_label() -> None:
    result = compare(
        [obs("current", 125, trust="doctor_verified")],
        [obs("baseline", 120, "2026-10-20T09:00:00Z")],
    )
    item = result.comparisons[0]
    assert item.delta == 5
    assert item.trust_basis == "mixed"


def test_same_time_does_not_become_prior_and_tied_prior_is_deterministic() -> None:
    target = obs("current", 135)
    old_a = obs("old-a", 120, "2026-10-20T08:00:00Z")
    old_b = obs("old-b", 125, "2026-10-20T08:00:00Z")
    same = obs("same", 999, "2026-11-03T09:00:00Z")
    a = compare([target], [same, old_b, old_a])
    b = compare([target], [old_a, same, old_b])
    assert a == b
    assert a.comparisons[0].baseline_observation_id == "old-b"
    assert a.comparisons[0].delta == 10


def test_window_zero_and_expired_history_cannot_impute_baseline() -> None:
    a = compare([obs("current", 130)], [obs("old", 120, "2026-10-20T09:00:00Z")], 0)
    b = compare([obs("current", 130)], [obs("old", 120, "2026-01-01T09:00:00Z")])
    assert not a.comparisons[0].comparable
    assert not b.comparisons[0].comparable


@pytest.mark.parametrize(
    ("current", "history", "error_code"),
    [
        ([obs("a", patient="synthetic-b")], [], "E_SCOPE_VIOLATION"),
        ([obs("a")], [obs("x", patient="synthetic-b")], "E_SCOPE_VIOLATION"),
        ([obs("x")], [obs("x")], "E_VALIDATION"),
        ([obs("x"), obs("x")], [], "E_VALIDATION"),
        ([], [], "E_VALIDATION"),
        ([obs("x")] * 7, [], "E_VALIDATION"),
        ([obs("x")], [obs(str(i)) for i in range(101)], "E_VALIDATION"),
    ],
)
def test_scope_duplicates_empty_and_caps_fail_closed(current, history, error_code) -> None:
    with pytest.raises(MonitoringInputError) as failure:
        compare(current, history)
    assert failure.value.code == error_code


def test_invariance_immutable_result_and_invalid_window() -> None:
    current = [obs("z"), obs("a", 140)]
    historical = [obs("prior", 110, "2026-10-01T09:00:00Z")]
    first = compare(current, historical)
    again = compare(list(reversed(current)), historical)
    assert first == again
    with pytest.raises(FrozenInstanceError):
        first.comparisons[0].comparable = True
    with pytest.raises(MonitoringInputError) as invalid:
        compare_explicit_current_with_history(
            current=(obs("a"),),
            history=(),
            patient_id="synthetic-a",
            as_of_utc=CLOCK,
            baseline_lookback_days=True,
        )
    assert invalid.value.code == "E_VALIDATION"
