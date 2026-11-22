"""RB2 offline GOLD A/B/C/D tests: fixture replay, NOT genuine run-backed proof.

The GOLD-C real Tesseract false-clean case is still FAIL / NOT PROVEN.
No real OCR, SQLite, doctor source assurance, approval, or persisted review rows.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from app.core.paths import REPO_ROOT
from app.schemas.p4_rb2_offline_rules import (
    OfflineObservation,
    OfflineRuleError,
    OfflineRuleInput,
    OfflineRulePolicy,
)
from app.services.p4_rb2_offline_rules import evaluate_p4_rb2_offline_fixture

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)
SHA = {
    "A": "643c219ba15c77e2ddd1f7273931aafc40d3bf37725386c590dc2535ff5211be",
    "B": "4019f1700fd7407e5df9f264dcd73b317d3b61d8e511e7ad8689a2de2d054cd3",
    "C": "555d41d5d52187a154a2d3e258e94cc9f1e5dd3bee6ab67aa4ac1d359156f6f0",
    "D": "d4aea8155f690c4420a194e317b7fc202a9d3a3e7671bb22d363c70092065940",
}
POLICY_SHA = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"


def _canonical(raw: bytes) -> bytes:
    assert b"\r" not in raw.replace(b"\r\n", b"")
    return raw.replace(b"\r\n", b"\n")


def _expected(case: str) -> dict:
    file = REPO_ROOT / "data/synthetic/golden_cases" / f"GOLD-{case}.expected.json"
    raw = _canonical(file.read_bytes())
    assert sha256(raw).hexdigest() == SHA[case]
    result = json.loads(raw)
    assert result["case_id"] == f"GOLD-{case}"
    assert result["demo_as_of_utc"] == "2026-11-14T12:00:00Z"
    assert result["candidate_policy_status"] == "test-only-unapproved"
    return result


def _ob(
    name: str, measure: str, value: int, date: str, *,
    patient: str, trust: str = "self_reported_validated",
    validation: str = "ok",
) -> OfflineObservation:
    return OfflineObservation(
        id=name, patient_id=patient, measure_type=measure, value=value,
        unit={"systolic_bp": "mmHg", "diastolic_bp": "mmHg",
              "heart_rate": "bpm", "glucose": "mg/dL"}[measure],
        measured_at=f"{date}T09:00:00Z", validation=validation,
        trust_level=trust, source="seed_fixture",
        created_at="2026-11-04T08:00:00Z",
    )


def _run(patient: str, selected, history, *, statuses=()):
    return evaluate_p4_rb2_offline_fixture(
        OfflineRuleInput(
            patient_id=patient, selected_current=tuple(selected),
            history=tuple(history), policy=OfflineRulePolicy(),
            as_of_utc=AS_OF, active_fact_verification_statuses=tuple(statuses),
        )
    )


def test_gold_reference_files_and_offline_policy_bytes_are_unchanged() -> None:
    for case in "ABCD":
        _expected(case)
    path = REPO_ROOT / "data/synthetic/policy/demo_review_policy.yaml"
    assert sha256(_canonical(path.read_bytes())).hexdigest() == POLICY_SHA


def test_gold_a_stable_three_current_measurements_zero_flags() -> None:
    spec = _expected("A")
    patient = spec["patient_external_ref"]
    history = [
        _ob("a-s1", "systolic_bp", 122, "2026-10-01", patient=patient),
        _ob("a-s2", "systolic_bp", 120, "2026-10-15", patient=patient),
        _ob("a-d1", "diastolic_bp", 78, "2026-10-01", patient=patient),
        _ob("a-d2", "diastolic_bp", 79, "2026-10-15", patient=patient),
        _ob("a-h1", "heart_rate", 72, "2026-10-01", patient=patient),
        _ob("a-h2", "heart_rate", 74, "2026-10-15", patient=patient),
    ]
    current = [
        _ob("a-s3", "systolic_bp", 121, "2026-11-01", patient=patient),
        _ob("a-d3", "diastolic_bp", 78, "2026-11-01", patient=patient),
        _ob("a-h3", "heart_rate", 71, "2026-11-01", patient=patient),
    ]
    output = _run(patient, current, history)
    assert [f.rule_id for f in output.flags] == spec["expected_review_rule_ids"] == []
    assert spec["document_mapping"]["mapped_observations"] == 0
    assert len(current) == spec["expected_live_checkin_count"]


def test_gold_b_one_self_reported_systolic_change_without_other_rule() -> None:
    spec = _expected("B")
    patient = spec["patient_external_ref"]
    selected = [
        _ob("b-s", "systolic_bp", 132, "2026-11-03", patient=patient),
        _ob("b-g", "glucose", 104, "2026-11-02", patient=patient,
            trust="doctor_verified"),
    ]
    history = [
        _ob("b-s0", "systolic_bp", 120, "2026-10-20", patient=patient),
        _ob("b-g0", "glucose", 98, "2026-10-02", patient=patient),
    ]
    result = _run(patient, selected, history)
    assert [f.rule_id for f in result.flags] == spec["expected_review_rule_ids"]
    assert len(result.flags) == spec["expected_review_count"] == 1
    gold = spec["expected_dr005"]
    assert (result.flags[0].reason_code, result.flags[0].trust_basis,
            result.flags[0].message) == (
        "change_exceeds_demo_parameter", gold["trust_basis"], gold["message"]
    )


def test_gold_c_before_fixture_correction_blocks_and_after_is_clean() -> None:
    spec = _expected("C")
    patient = spec["patient_external_ref"]
    current = [_ob("c-g", "glucose", 105, "2026-11-03", patient=patient,
                   trust="doctor_verified")]
    history = [_ob("c-base", "glucose", 96, "2026-10-10", patient=patient)]
    before = spec["pre_verification"]
    assert before["pending_active_fact_count"] == 3
    assert before["expected_review_rule_ids"] == []
    with pytest.raises(OfflineRuleError) as error:
        _run(patient, current, history, statuses=("pending", "pending", "pending"))
    assert error.value.code == "E_UNVERIFIED_FACT"
    after = spec["post_fixture_correction"]
    result = _run(patient, current, history, statuses=("verified",) * 3)
    assert [flag.rule_id for flag in result.flags] == after["expected_review_rule_ids"]
    assert after["expected_delta"] == 9
    assert "FAIL / NOT PROVEN" in spec["real_ocr_result"]


def test_gold_d_five_rules_without_doctor_verified_source_conflict() -> None:
    spec = _expected("D")
    patient = spec["patient_external_ref"]
    rows = [
        _ob("d-hr", "heart_rate", 68, "2026-09-01", patient=patient),
        _ob("d-s0", "systolic_bp", 128, "2026-10-05", patient=patient),
        _ob("d-d0", "diastolic_bp", 82, "2026-10-05", patient=patient),
        _ob("d-s1", "systolic_bp", 130, "2026-10-20", patient=patient),
        _ob("d-s2", "systolic_bp", 130, "2026-10-20", patient=patient),
        _ob("d-d1", "diastolic_bp", 250, "2026-10-25", patient=patient,
            validation="ok_with_warning"),
    ]
    selected = (rows[0], rows[4], rows[5])
    history = (rows[1], rows[2], rows[3])
    a = _run(patient, selected, history)
    b = _run(patient, tuple(reversed(selected)), tuple(reversed(history)))
    assert a == b
    assert sorted(item.rule_id for item in a.flags) == spec["expected_review_rule_ids"]
    assert len(a.flags) == spec["expected_review_count"] == 5
    assert all(item.trust_basis == "self_reported" for item in a.flags)
    assert not any(item.rule_id == "DR-006" for item in a.flags)
    assert spec["expected_source_conflicts"] == 0
    assert abs(250 - 82) == spec["expected_deltas"]["diastolic_bp"]
    assert a.review_items_persisted is False


def test_no_current_selected_even_with_all_gold_d_history_produces_zero() -> None:
    patient = "DEMO-D-001"
    old = _ob("d-old", "heart_rate", 68, "2026-09-01", patient=patient)
    output = _run(patient, (), (old,))
    assert output.flags == ()


def test_gold_cases_are_pure_and_never_claim_real_run_or_ocr() -> None:
    result = _run("demo-test", (), ())
    assert result.policy_status == "unapproved"
    assert not result.runtime_evaluable
    assert not result.rules_executed
    assert not result.review_items_persisted
    with pytest.raises(TypeError):
        replace(result, runtime_evaluable="authorized", extra=True)
