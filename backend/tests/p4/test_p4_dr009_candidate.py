"""P4-2b offline DR-009 entry-quality candidate tests; synthetic data only."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.services.demo_rules_candidate import (
    CandidateDemoPolicy,
    CandidateRuleError,
    evaluate_candidate_review_subset,
)
from app.services.monitoring import (
    MonitoringInputError,
    ObservationSnapshot,
    compare_observation_history,
)

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)
PATIENT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def candidate(**changes: object) -> CandidateDemoPolicy:
    initial = CandidateDemoPolicy(
        policy_version="candidate-p4-2a-0.2.0",
        demo_only=True,
        demo_as_of_utc=AS_OF,
        baseline_lookback_days=90,
        stale_measurement_days=30,
        demo_delta_systolic_mmHg=10,
        demo_delta_diastolic_mmHg=8,
        demo_delta_heart_rate_bpm=15,
        demo_delta_glucose_mgdl=40,
        max_items_per_type=3,
        enabled_rule_ids=("DR-009",),
    )
    return replace(initial, **changes)


def observation(
    identifier: str,
    value: str | int,
    *,
    timestamp: str = "2026-11-03T08:00:00Z",
    measure: str = "systolic_bp",
    unit: str = "mmHg",
    validation: str = "ok_with_warning",
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
        validation=validation,
        trust_level=trust,
    )


def run(*rows: ObservationSnapshot, policy: CandidateDemoPolicy | None = None, blocked: int = 0):
    selected = policy if policy is not None else candidate()
    history = tuple(rows)
    compared = compare_observation_history(
        history, patient_id=PATIENT, as_of_utc=AS_OF, baseline_lookback_days=90
    )
    return evaluate_candidate_review_subset(
        patient_id=PATIENT,
        observations=history,
        comparisons=compared,
        policy=selected,
        as_of_utc=AS_OF,
        blocking_fact_count=blocked,
    )


def test_dr009_synthetic_typo_uses_exact_message_and_source_label() -> None:
    result = run(observation("typo", "1200"))
    assert len(result.flags) == 1
    item = result.flags[0]
    assert (item.rule_id, item.reason_code, item.workflow_hint) == (
        "DR-009",
        "implausible_value",
        "data_quality",
    )
    assert item.evidence == ("observation:typo",)
    assert item.message == (
        "A recorded value is outside the demo plausibility range and may be a typo (self-reported)."
    )
    assert item.trust_basis == "self_reported"
    assert item.demo_only is True


def test_dr009_below_demo_band_generates_a_prompt() -> None:
    result = run(observation("low-value", 49))
    assert [item.rule_id for item in result.flags] == ["DR-009"]


def test_dr009_inclusive_band_endpoints_do_not_trigger() -> None:
    result = run(
        observation("lower", 50, validation="ok", timestamp="2026-10-10T08:00:00Z"),
        observation("upper", 300, validation="ok"),
    )
    assert result.flags == ()


def test_dr009_uses_the_existing_four_measure_bands() -> None:
    result = run(
        observation("sys", 301),
        observation("dia", 201, measure="diastolic_bp"),
        observation("heart", 251, measure="heart_rate", unit="bpm"),
        observation("sugar", 901, measure="glucose", unit="mg/dL"),
    )
    assert len(result.flags) == 4
    assert {flag.rule_id for flag in result.flags} == {"DR-009"}
    assert len({flag.dedupe_key for flag in result.flags}) == 4


def test_dr009_doctor_verified_provenance_is_not_relabelled() -> None:
    result = run(observation("verified", 301, trust="doctor_verified"))
    assert result.flags[0].trust_basis == "doctor_verified"
    assert "self-reported" not in result.flags[0].message


def test_dr009_historical_admissible_warning_is_not_hidden() -> None:
    result = run(
        observation("old-warning", 301, timestamp="2026-10-01T08:00:00Z"),
        observation("current", 120, validation="ok"),
    )
    assert [f.evidence for f in result.flags] == [("observation:old-warning",)]


def test_dr009_rejected_garbage_does_not_block_clean_data() -> None:
    result = run(
        observation("rejected", "not-a-value", validation="rejected"),
        observation("valid", 120, validation="ok"),
    )
    assert result.flags == ()


def test_dr009_wrong_unit_is_excluded_even_if_value_out_of_band() -> None:
    result = run(
        observation("wrong-unit", 1200, unit="bpm"),
        observation("valid", 120, validation="ok"),
    )
    assert result.flags == ()


def test_dr009_validated_intake_label_is_not_a_prerequisite_for_rechecking() -> None:
    result = run(observation("possible-entry-error", 1200, validation="ok"))
    assert [f.rule_id for f in result.flags] == ["DR-009"]


def test_dr009_disabled_rule_returns_no_prompt() -> None:
    result = run(observation("value", 1200), policy=candidate(enabled_rule_ids=()))
    assert result.flags == ()
    assert "DR-009" in result.disabled_rule_ids


def test_dr009_policy_requires_versioned_opt_in() -> None:
    with pytest.raises(CandidateRuleError) as exc:
        run(observation("value", 1200), policy=candidate(policy_version="candidate-p4-2a-0.1.0"))
    assert exc.value.code == "E_RULE_POLICY_INVALID"


def test_dr009_policy_rejects_oversized_version_with_typed_error() -> None:
    oversized = "candidate-p4-2a-" + "9" * 5000 + ".2.0"
    with pytest.raises(CandidateRuleError) as exc:
        run(observation("value", 1200), policy=candidate(policy_version=oversized))
    assert exc.value.code == "E_RULE_POLICY_INVALID"


@pytest.mark.parametrize(
    ("bad_timestamp", "reason"),
    [
        (None, "missing_timestamp"),
        ("2026-11-14T12:06:00Z", "future_timestamp"),
    ],
)
def test_dr009_excludes_missing_or_future_timestamp_with_reason(
    bad_timestamp: str | None, reason: str
) -> None:
    excluded = replace(observation("excluded", 1200), measured_at=bad_timestamp)
    clean = observation("clean", 120, validation="ok")
    rows = (excluded, clean)
    comparisons = compare_observation_history(
        rows, patient_id=PATIENT, as_of_utc=AS_OF, baseline_lookback_days=90
    )
    assert [(item.observation_id, item.skip_reason) for item in comparisons.excluded] == [
        ("excluded", reason)
    ]
    result = evaluate_candidate_review_subset(
        patient_id=PATIENT,
        observations=rows,
        comparisons=comparisons,
        policy=candidate(),
        as_of_utc=AS_OF,
        blocking_fact_count=0,
    )
    assert result.flags == ()


def test_dr009_order_independent_and_repeatable() -> None:
    a = observation("b", 301, timestamp="2026-10-01T08:00:00Z")
    b = observation("a", 302)
    first = run(a, b)
    assert first == run(b, a)
    assert first == run(a, b)
    assert [f.evidence for f in first.flags] == [
        ("observation:a",),
        ("observation:b",),
    ]


def test_dr009_item_limit_fails_closed_instead_of_silent_dropping() -> None:
    with pytest.raises(CandidateRuleError) as exc:
        run(
            observation("a", 301, timestamp="2026-10-01T08:00:00Z"),
            observation("b", 302, timestamp="2026-10-02T08:00:00Z"),
            observation("c", 303, timestamp="2026-10-03T08:00:00Z"),
            observation("d", 304, timestamp="2026-10-04T08:00:00Z"),
        )
    assert exc.value.code == "E_RULE_POLICY_INVALID"


def test_dr009_verification_blocker_prevents_any_review_output() -> None:
    with pytest.raises(CandidateRuleError) as exc:
        run(observation("value", 1200), blocked=1)
    assert exc.value.code == "E_UNVERIFIED_FACT"


def test_dr009_other_patient_fails_scope_validation_before_review() -> None:
    with pytest.raises(MonitoringInputError) as exc:
        run(observation("other", 301, patient=OTHER))
    assert exc.value.code == "E_SCOPE_VIOLATION"


def test_dr009_invalid_numeric_candidate_is_rejected() -> None:
    with pytest.raises(MonitoringInputError) as exc:
        run(observation("bad", "NaN"))
    assert exc.value.code == "E_VALIDATION"
