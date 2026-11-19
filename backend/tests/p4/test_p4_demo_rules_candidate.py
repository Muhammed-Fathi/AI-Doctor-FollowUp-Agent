"""P4-2A offline candidate rule tests; not an enabled clinical engine."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.services.demo_rules_candidate import (
    CandidateDemoPolicy,
    CandidateRuleError,
    evaluate_candidate_review_subset,
)
from app.services.monitoring import (
    MonitoringResult,
    ObservationSnapshot,
    compare_observation_history,
)

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)
PATIENT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def policy(**changes: object) -> CandidateDemoPolicy:
    initial = CandidateDemoPolicy(
        policy_version="candidate-p4-2a-0.1.0",
        demo_only=True,
        demo_as_of_utc=AS_OF,
        baseline_lookback_days=90,
        stale_measurement_days=30,
        demo_delta_systolic_mmHg=10,
        demo_delta_diastolic_mmHg=8,
        demo_delta_heart_rate_bpm=15,
        demo_delta_glucose_mgdl=40,
        max_items_per_type=3,
        enabled_rule_ids=("DR-001", "DR-003", "DR-005"),
    )
    return replace(initial, **changes)


def obs(
    identifier: str,
    timestamp: str,
    value: int | str,
    measure: str = "systolic_bp",
    unit: str = "mmHg",
    trust: str = "self_reported_validated",
    patient: str = PATIENT,
) -> ObservationSnapshot:
    return ObservationSnapshot(
        id=identifier,
        patient_id=patient,
        measure_type=measure,
        value=value,
        unit=unit,
        measured_at=timestamp,
        validation="ok",
        trust_level=trust,
    )


def run(
    *rows: ObservationSnapshot,
    candidate: CandidateDemoPolicy | None = None,
    clock: datetime = AS_OF,
    blocked: int = 0,
    comparisons: MonitoringResult | None = None,
):
    chosen = candidate if candidate is not None else policy()
    history = tuple(rows)
    if comparisons is None:
        comparisons = compare_observation_history(
            history,
            patient_id=PATIENT,
            as_of_utc=clock,
            baseline_lookback_days=chosen.baseline_lookback_days,
        )
    return evaluate_candidate_review_subset(
        patient_id=PATIENT,
        observations=history,
        comparisons=comparisons,
        policy=chosen,
        as_of_utc=clock,
        blocking_fact_count=blocked,
    )


def test_case_b_emits_exactly_one_dr005() -> None:
    result = run(
        obs("a", "2026-10-02T08:00:00Z", 138),
        obs("b", "2026-10-20T08:00:00Z", 146),
        obs("c", "2026-11-03T08:00:00Z", 158),
        obs("d", "2026-10-20T08:00:00Z", 92, "diastolic_bp"),
        obs("e", "2026-11-03T08:00:00Z", 96, "diastolic_bp"),
        obs("f", "2026-10-20T08:00:00Z", 80, "heart_rate", "bpm"),
        obs("g", "2026-11-03T08:00:00Z", 84, "heart_rate", "bpm"),
        obs("h", "2026-10-02T08:00:00Z", 98, "glucose", "mg/dL"),
        obs(
            "i",
            "2026-11-02T08:00:00Z",
            104,
            "glucose",
            "mg/dL",
            trust="doctor_verified",
        ),
    )
    assert len(result.flags) == 1
    flag = result.flags[0]
    assert (flag.rule_id, flag.workflow_hint, flag.trust_basis) == (
        "DR-005",
        "change_to_review",
        "self_reported",
    )
    assert flag.message == (
        "Systolic BP differs from the previous recorded value by 12 mmHg (self-reported)."
    )
    assert flag.evidence == ("observation:b", "observation:c")
    assert flag.demo_only is True
    assert len(flag.dedupe_key) == 64
    assert result.disabled_rule_ids == ("DR-006", "DR-008", "DR-009")


def test_case_a_stable_produces_no_flags() -> None:
    result = run(
        obs("a", "2026-10-15T08:00:00Z", 120),
        obs("b", "2026-11-01T08:00:00Z", 121),
        obs("c", "2026-10-15T08:00:00Z", 79, "diastolic_bp"),
        obs("d", "2026-11-01T08:00:00Z", 78, "diastolic_bp"),
        obs("e", "2026-10-15T08:00:00Z", 74, "heart_rate", "bpm"),
        obs("f", "2026-11-01T08:00:00Z", 71, "heart_rate", "bpm"),
    )
    assert result.flags == ()


def test_case_c_blocks_before_review_and_after_correction_has_no_flag() -> None:
    first = obs("baseline", "2026-10-10T08:00:00Z", 96, "glucose", "mg/dL")
    after = obs(
        "corrected",
        "2026-11-03T08:00:00Z",
        105,
        "glucose",
        "mg/dL",
        trust="doctor_verified",
    )
    with pytest.raises(CandidateRuleError) as error:
        run(first, after, blocked=3)
    assert error.value.code == "E_UNVERIFIED_FACT"
    assert run(first, after).flags == ()


def test_dr001_single_missing_baseline() -> None:
    result = run(obs("solo", "2026-11-01T08:00:00Z", 120))
    assert [x.rule_id for x in result.flags] == ["DR-001"]
    assert result.flags[0].reason_code == "missing_baseline"


def test_dr003_stale_depends_on_explicit_clock() -> None:
    rows = (
        obs("old", "2026-08-01T08:00:00Z", 120),
        obs("new", "2026-10-05T08:00:00Z", 121),
    )
    first = run(*rows)
    assert [x.rule_id for x in first.flags] == ["DR-003"]
    assert "recorded 40 days ago" in first.flags[0].message
    later = AS_OF + timedelta(days=5)
    second = run(
        *rows,
        candidate=policy(
            demo_as_of_utc=later,
            policy_version="candidate-p4-2a-0.1.1",
        ),
        clock=later,
    )
    assert "recorded 45 days ago" in second.flags[0].message


def test_dr005_requires_strictly_greater_than_parameter() -> None:
    base = obs("base", "2026-10-15T08:00:00Z", 120)
    equal = obs("equal", "2026-11-03T08:00:00Z", 130)
    greater = obs("greater", "2026-11-03T08:00:00Z", 131)
    assert not any(x.rule_id == "DR-005" for x in run(base, equal).flags)
    assert any(x.rule_id == "DR-005" for x in run(base, greater).flags)


def test_dr005_uses_absolute_change_without_direction() -> None:
    result = run(
        obs("a", "2026-10-15T08:00:00Z", 158),
        obs("b", "2026-11-03T08:00:00Z", 146),
    )
    assert [x.rule_id for x in result.flags] == ["DR-005"]
    assert "12 mmHg" in result.flags[0].message
    assert "worsen" not in result.flags[0].message


def test_mixed_provenance_and_order_independence() -> None:
    before = obs(
        "a",
        "2026-10-15T08:00:00Z",
        120,
        trust="doctor_verified",
    )
    current = obs("b", "2026-11-03T08:00:00Z", 140)
    assert run(before, current) == run(current, before)
    flag = run(before, current).flags[0]
    assert flag.trust_basis == "mixed"
    assert flag.message.endswith(" (includes self-reported values).")


def test_verified_provenance_has_no_self_reported_suffix() -> None:
    result = run(
        obs("a", "2026-10-15T08:00:00Z", 120, trust="doctor_verified"),
        obs("b", "2026-11-03T08:00:00Z", 140, trust="doctor_verified"),
    )
    assert result.flags[0].trust_basis == "doctor_verified"
    assert "self-reported" not in result.flags[0].message


@pytest.mark.parametrize(
    "ids",
    [
        ("DR-002",),
        ("DR-006",),
        ("DR-001", "DR-001"),
        ("DR-007",),
    ],
)
def test_retired_unknown_and_unimplemented_rules_are_rejected(ids) -> None:
    with pytest.raises(CandidateRuleError) as error:
        run(
            obs("a", "2026-11-01T08:00:00Z", 120),
            candidate=policy(enabled_rule_ids=ids),
        )
    assert error.value.code == "E_RULE_POLICY_INVALID"


@pytest.mark.parametrize(
    "invalid",
    [
        {"demo_only": False},
        {"policy_version": "demo-policy-1.1.0"},
        {"baseline_lookback_days": 0},
        {"stale_measurement_days": 366},
        {"demo_delta_systolic_mmHg": "NaN"},
        {"demo_delta_glucose_mgdl": -1},
        {"max_items_per_type": 0},
    ],
)
def test_invalid_candidate_policy_fails_closed(invalid) -> None:
    with pytest.raises(CandidateRuleError) as error:
        run(
            obs("a", "2026-11-01T08:00:00Z", 120),
            candidate=policy(**invalid),
        )
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_unapproved_clock_change_is_blocked() -> None:
    with pytest.raises(CandidateRuleError) as error:
        run(
            obs("a", "2026-11-01T08:00:00Z", 120),
            clock=AS_OF + timedelta(days=1),
        )
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_wrong_patient_cannot_be_included() -> None:
    with pytest.raises(Exception) as error:
        run(
            obs("a", "2026-11-01T08:00:00Z", 120),
            obs(
                "other",
                "2026-11-01T08:00:00Z",
                150,
                patient=OTHER,
            ),
        )
    assert error.value is not None


def test_tampered_comparison_rejected_before_emitting() -> None:
    rows = (
        obs("a", "2026-10-15T08:00:00Z", 120),
        obs("b", "2026-11-03T08:00:00Z", 135),
    )
    original = compare_observation_history(
        rows,
        patient_id=PATIENT,
        as_of_utc=AS_OF,
        baseline_lookback_days=90,
    )
    altered = MonitoringResult((), original.excluded)
    with pytest.raises(CandidateRuleError) as error:
        run(*rows, comparisons=altered)
    assert error.value.code == "E_VALIDATION"


def test_mismatched_unit_never_shifts_baseline() -> None:
    wrong = obs("wrong", "2026-10-15T08:00:00Z", 120, unit="bpm")
    current = obs("current", "2026-11-03T08:00:00Z", 135)
    assert [x.rule_id for x in run(wrong, current).flags] == ["DR-001"]


def test_policy_can_disable_every_subset_rule() -> None:
    result = run(
        obs("a", "2026-11-01T08:00:00Z", 120),
        candidate=policy(enabled_rule_ids=()),
    )
    assert result.flags == ()
    assert result.disabled_rule_ids == (
        "DR-001",
        "DR-003",
        "DR-005",
        "DR-006",
        "DR-008",
        "DR-009",
    )


def test_candidate_item_cap_fails_closed() -> None:
    with pytest.raises(CandidateRuleError) as error:
        run(
            obs("only", "2026-09-01T08:00:00Z", 120),
            candidate=policy(max_items_per_type=1),
        )
    assert error.value.code == "E_RULE_POLICY_INVALID"
