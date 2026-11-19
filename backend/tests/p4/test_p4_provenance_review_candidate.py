"""P4-2d test-only DR-006/008 semantics; no database/API/policy activation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.demo_rules_candidate import CandidateRuleError
from app.services.monitoring import ObservationSnapshot
from app.services.provenance_review_candidate import (
    CandidateProvenancePolicy,
    CandidateRecordedObservation,
    evaluate_offline_provenance_candidates,
)

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
PATIENT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
MEASURE = "2026-11-03T08:00:00Z"
CREATED = "2026-11-04T08:00:00Z"


def policy(**changes: object) -> CandidateProvenancePolicy:
    source = CandidateProvenancePolicy(
        policy_version="candidate-p4-2d-0.1.0",
        demo_only=True,
        demo_as_of_utc=CLOCK,
        conflict_tolerance="0",
        max_items_per_type=3,
        enabled_rule_ids=("DR-006", "DR-008"),
    )
    return replace(source, **changes)


def record(
    identifier: str,
    value: str | int = 130,
    *,
    measured_at: str | datetime | None = MEASURE,
    created_at: str | datetime | None = CREATED,
    measure: str = "systolic_bp",
    unit: str = "mmHg",
    validation: str = "ok",
    trust: str = "doctor_verified",
    source: str = "verified_document",
    fact: str | None = None,
    document: str | None = None,
    verification: str | None = "verified",
    patient: str = PATIENT,
) -> CandidateRecordedObservation:
    return CandidateRecordedObservation(
        observation=ObservationSnapshot(
            id=identifier,
            patient_id=patient,
            measure_type=measure,
            value=value,
            unit=unit,
            measured_at=measured_at,
            validation=validation,
            trust_level=trust,
        ),
        created_at=created_at,
        source=source,
        source_fact_id=fact or ("fact-" + identifier),
        source_document_id=document or ("doc-" + identifier),
        source_fact_verification_status=verification,
    )


def run(
    *rows: CandidateRecordedObservation,
    candidate: CandidateProvenancePolicy | None = None,
    blocked: int = 0,
    clock: datetime = CLOCK,
):
    return evaluate_offline_provenance_candidates(
        patient_id=PATIENT,
        records=tuple(rows),
        policy=candidate or policy(),
        as_of_utc=clock,
        blocking_fact_count=blocked,
    )


def test_dr006_two_independent_verified_documents_same_instant_flag_once() -> None:
    result = run(record("a", 120), record("b", 130))
    assert [(f.rule_id, f.reason_code, f.workflow_hint) for f in result.flags] == [
        ("DR-006", "verified_source_conflict", "verification_needed")
    ]
    flag = result.flags[0]
    assert flag.message == "Two verified sources disagree for Systolic BP at 2026-11-03T08:00:00Z."
    assert flag.evidence == ("observation:a", "observation:b")
    assert flag.trust_basis == "doctor_verified"
    assert len(flag.dedupe_key) == 64
    assert flag.demo_only is True


@pytest.mark.parametrize(
    "second,why",
    [
        (record("b", 120), "same value"),
        (record("b", 130, measured_at="2026-11-03T08:00:01Z"), "different instant"),
        (record("b", 130, document="doc-a"), "same source document"),
        (record("b", 130, fact="fact-a", document="doc-a"), "same mapped fact"),
        (record("b", 130, trust="self_reported_validated"), "not doctor-verified"),
        (record("b", 130, verification="pending"), "pending source"),
        (record("b", 130, source="patient_checkin"), "not mapped document"),
    ],
)
def test_dr006_does_not_infer_independent_compatible_sources(
    second: CandidateRecordedObservation, why: str
) -> None:
    del why
    result = run(record("a", 120), second, candidate=policy(enabled_rule_ids=("DR-006",)))
    assert result.flags == ()


def test_dr006_tolerance_must_be_explicit_and_strictly_exceeded() -> None:
    rows = (record("a", 120), record("b", 130))
    assert (
        run(*rows, candidate=policy(enabled_rule_ids=("DR-006",), conflict_tolerance="10")).flags
        == ()
    )
    assert [
        flag.rule_id
        for flag in run(
            *rows, candidate=policy(enabled_rule_ids=("DR-006",), conflict_tolerance="9.9")
        ).flags
    ] == ["DR-006"]


def test_dr006_one_source_fact_two_claimed_documents_rejected() -> None:
    with pytest.raises(CandidateRuleError) as error:
        run(
            record("a", 120, fact="same", document="doc1"),
            record("b", 130, fact="same", document="doc2"),
        )
    assert error.value.code == "E_VALIDATION"


def test_dr008_exact_duplicate_distinct_records_no_creation_order_needed() -> None:
    result = run(
        record(
            "a", 130, created_at=None, trust="self_reported_validated", source="patient_checkin"
        ),
        record(
            "b", 130, created_at=None, trust="self_reported_validated", source="patient_checkin"
        ),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert [flag.rule_id for flag in result.flags] == ["DR-008"]
    assert result.flags[0].reason_code == "duplicate_or_out_of_order"
    assert result.flags[0].message == (
        "A repeated or out-of-order entry was detected for Systolic BP (self-reported)."
    )
    assert (
        len([item for item in result.excluded if item.reason == "creation_time_unavailable"]) == 2
    )


def test_dr008_creation_order_strictly_later_while_measurement_earlier() -> None:
    result = run(
        record(
            "early-record",
            120,
            measured_at="2026-11-05T08:00:00Z",
            created_at="2026-11-06T09:00:00Z",
        ),
        record(
            "late-record",
            130,
            measured_at="2026-11-04T08:00:00Z",
            created_at="2026-11-07T09:00:00Z",
        ),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert [f.rule_id for f in result.flags] == ["DR-008"]
    assert result.flags[0].evidence == ("observation:early-record", "observation:late-record")


@pytest.mark.parametrize(
    "created_at,measured_at",
    [
        ("2026-11-04T08:00:00Z", "2026-11-03T08:00:00Z"),
        (None, "2026-11-01T08:00:00Z"),
        ("bad-created", "2026-11-01T08:00:00Z"),
    ],
)
def test_dr008_tied_or_unknown_creation_does_not_infer_order(
    created_at: str | None, measured_at: str
) -> None:
    result = run(
        record("a", 120, measured_at="2026-11-02T08:00:00Z", created_at=CREATED),
        record("b", 130, measured_at=measured_at, created_at=created_at),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert result.flags == ()


def test_dr008_in_order_and_same_time_different_value_do_not_fire() -> None:
    result = run(
        record("a", 120, measured_at="2026-11-01T08:00:00Z", created_at="2026-11-03T08:00:00Z"),
        record("b", 130, measured_at=MEASURE, created_at="2026-11-04T08:00:00Z"),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert result.flags == ()
    same = run(
        record("a", 120),
        record("b", 130),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert same.flags == ()


def test_dr008_same_source_fact_replay_cannot_be_a_duplicate() -> None:
    result = run(
        record("a", 130, fact="same", document="one"),
        record("b", 130, fact="same", document="one"),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert result.flags == ()


def test_dr008_mixed_trust_is_never_promoted_to_verified() -> None:
    result = run(
        record("a", 130),
        record("b", 130, trust="self_reported_validated", source="patient_checkin"),
        candidate=policy(enabled_rule_ids=("DR-008",)),
    )
    assert [f.rule_id for f in result.flags] == ["DR-008"]
    assert result.flags[0].trust_basis == "mixed"
    assert "(includes self-reported values)" in result.flags[0].message


def test_excluded_rows_never_form_006_or_008_pairs() -> None:
    clean = record("clean", 120)
    for bad in (
        record("badunit", 130, unit="bpm"),
        record("rejected", 130, validation="rejected"),
        record("missing", 130, measured_at=None),
        record("future", 130, measured_at=CLOCK + timedelta(minutes=6)),
    ):
        result = run(clean, bad)
        assert result.flags == ()
        assert any(ex.observation_id == bad.observation.id for ex in result.excluded)


def test_scope_mismatch_rejects_all_candidate_flags() -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(record("a", 120), record("b", 130, patient=OTHER))
    assert err.value.code == "E_SCOPE_VIOLATION"


def test_blocked_unverified_facts_stop_offline_candidate_evaluation() -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(record("a", 120), record("b", 130), blocked=1)
    assert err.value.code == "E_UNVERIFIED_FACT"


@pytest.mark.parametrize(
    "override",
    [
        {"policy_version": "demo-policy-1.1.0"},
        {"policy_version": "candidate-p4-2d-" + "9" * 5000 + ".1.0"},
        {"demo_only": False},
        {"conflict_tolerance": "-1"},
        {"conflict_tolerance": "NaN"},
        {"conflict_tolerance": True},
        {"max_items_per_type": True},
        {"enabled_rule_ids": ("DR-009",)},
        {"enabled_rule_ids": ("DR-006", "DR-006")},
    ],
)
def test_unknown_unapproved_or_ill_formed_policy_fails_closed(override: dict[str, object]) -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(record("a", 120), candidate=policy(**override))
    assert err.value.code == "E_RULE_POLICY_INVALID"


def test_wrong_clock_rejected() -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(record("a", 120), clock=datetime(2026, 11, 14, 12))
    assert err.value.code == "E_RULE_POLICY_INVALID"


def test_permutation_and_replay_determinism() -> None:
    a, b = record("a", 120), record("b", 130)
    first = run(a, b)
    assert first == run(b, a)
    assert first == run(a, b)
    assert first.flags[0].evidence == ("observation:a", "observation:b")


def test_max_items_per_measure_fails_closed_no_partial_output() -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(
            record("a", 120),
            record("b", 130),
            record("c", 140),
            candidate=policy(enabled_rule_ids=("DR-006",), max_items_per_type=2),
        )
    assert err.value.code == "E_RULE_POLICY_INVALID"


def test_duplicate_record_id_and_many_rows_fails_closed() -> None:
    with pytest.raises(CandidateRuleError) as err:
        run(record("same"), record("same"))
    assert err.value.code == "E_VALIDATION"
    with pytest.raises(CandidateRuleError) as many:
        run(*(record(str(i)) for i in range(101)))
    assert many.value.code == "E_VALIDATION"


def test_disabled_rules_reported_without_activation() -> None:
    result = run(
        record("a", 120),
        record("b", 130),
        candidate=policy(enabled_rule_ids=()),
    )
    assert result.flags == ()
    assert result.disabled_rule_ids == ("DR-006", "DR-008")
    assert result.demo_only is True


def test_utc_instant_equality_handles_timezone_offset() -> None:
    # Equal physical instant despite distinct ISO representations.
    result = run(
        record("a", 120, measured_at="2026-11-03T08:00:00Z"),
        record("b", 130, measured_at="2026-11-03T10:00:00+02:00"),
        candidate=policy(enabled_rule_ids=("DR-006",)),
    )
    assert [f.rule_id for f in result.flags] == ["DR-006"]


def test_no_activation_when_records_empty() -> None:
    result = run(candidate=policy(enabled_rule_ids=("DR-006", "DR-008")))
    assert result.flags == ()
    assert result.excluded == ()


def test_typed_output_and_no_long_message_for_four_measure_types() -> None:
    rows = (
        record("a", 85, measure="heart_rate", unit="bpm"),
        record("b", 95, measure="heart_rate", unit="bpm"),
    )
    item = run(*rows, candidate=policy(enabled_rule_ids=("DR-006",))).flags[0]
    assert "Heart rate" in item.message
    assert isinstance(item.dedupe_key, str)
    assert Decimal("0.1") < Decimal("1")
