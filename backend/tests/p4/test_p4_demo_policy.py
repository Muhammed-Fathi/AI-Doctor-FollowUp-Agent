"""P4-2a: fail-closed, side-effect-free candidate demo-policy validation tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.services.demo_policy import DemoPolicyError, validate_demo_policy


def candidate() -> dict:
    return {
        "policy_version": "demo-policy-1.1.0",
        "demo_only": True,
        "demo_as_of_utc": "2026-11-14T12:00:00Z",
        "notice": "DEMO review prompts only — not clinical risk assessment. Not for clinical use.",
        "parameters": {
            "baseline_lookback_days": 90,
            "stale_measurement_days": 30,
            "demo_delta_systolic_mmHg": 10,
            "demo_delta_diastolic_mmHg": 8,
            "demo_delta_heart_rate_bpm": 15,
            "demo_delta_glucose_mgdl": 40,
            "ocr_confidence_floor": 0.70,
            "conflict_tolerance": 0,
            "max_items_per_type": 3,
        },
        "verification_issues": [
            {"id": identifier, "enabled": True}
            for identifier in ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")
        ],
        "rules": [
            {"id": identifier, "enabled": True}
            for identifier in ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
        ],
    }


def fails(data: object) -> None:
    with pytest.raises(DemoPolicyError) as error:
        validate_demo_policy(data)
    assert error.value.code == "E_RULE_POLICY_INVALID"


def test_all_catalogued_candidate_values_validate_without_activation() -> None:
    result = validate_demo_policy(candidate())
    assert result.policy_version == "demo-policy-1.1.0"
    assert result.demo_as_of_utc == datetime(2026, 11, 14, 12, tzinfo=UTC)
    assert result.demo_delta_systolic_mmHg == Decimal("10")
    assert result.enabled_rules == (
        "DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009"
    )
    assert result.disabled_rules == ()


def test_enabled_and_disabled_ids_are_sorted_by_closed_catalogue() -> None:
    data = candidate()
    data["rules"].reverse()
    data["rules"][0]["enabled"] = False
    result = validate_demo_policy(data)
    assert result.enabled_rules == ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008")
    assert result.disabled_rules == ("DR-009",)


def test_disabled_verification_issue_is_recorded_not_dropped() -> None:
    data = candidate()
    data["verification_issues"][1]["enabled"] = False
    result = validate_demo_policy(data)
    assert result.disabled_verification_issues == ("VI-002",)
    assert "VI-002" not in result.enabled_verification_issues


def test_unknown_rule_id_fails_closed() -> None:
    data = candidate()
    data["rules"][0]["id"] = "DR-999"
    fails(data)


def test_retired_rule_id_fails_closed() -> None:
    data = candidate()
    data["rules"][0]["id"] = "DR-002"
    fails(data)


def test_missing_rule_id_fails_closed() -> None:
    data = candidate()
    data["rules"].pop()
    fails(data)


def test_duplicate_rule_id_fails_closed() -> None:
    data = candidate()
    data["rules"][-1]["id"] = "DR-005"
    fails(data)


def test_unknown_verification_issue_fails_closed() -> None:
    data = candidate()
    data["verification_issues"][0]["id"] = "VI-999"
    fails(data)


def test_missing_top_level_key_fails_closed() -> None:
    data = candidate()
    del data["notice"]
    fails(data)


def test_extra_top_level_key_fails_closed() -> None:
    data = candidate()
    data["unreviewed_behavior"] = True
    fails(data)


def test_missing_parameter_fails_closed() -> None:
    data = candidate()
    del data["parameters"]["baseline_lookback_days"]
    fails(data)


def test_unknown_parameter_fails_closed() -> None:
    data = candidate()
    data["parameters"]["medical_threshold"] = 1
    fails(data)


def test_boolean_not_accepted_as_integer() -> None:
    data = candidate()
    data["parameters"]["baseline_lookback_days"] = True
    fails(data)


def test_invalid_parameter_range_fails_closed() -> None:
    data = candidate()
    data["parameters"]["max_items_per_type"] = 100000
    fails(data)


def test_nonfinite_decimal_fails_closed() -> None:
    data = candidate()
    data["parameters"]["demo_delta_systolic_mmHg"] = float("nan")
    fails(data)


def test_wrong_boolean_enabled_fails_closed() -> None:
    data = candidate()
    data["rules"][0]["enabled"] = "true"
    fails(data)


def test_demo_only_false_fails_closed() -> None:
    data = candidate()
    data["demo_only"] = False
    fails(data)


def test_wrong_version_format_fails_closed() -> None:
    data = candidate()
    data["policy_version"] = "1.1.0"
    fails(data)


def test_noncanonical_or_naive_demo_clock_fails_closed() -> None:
    data = candidate()
    data["demo_as_of_utc"] = "2026-11-14T12:00:00"
    fails(data)


def test_missing_synthetic_disclaimer_fails_closed() -> None:
    data = candidate()
    data["notice"] = "Everything is fine."
    fails(data)


def test_candidate_is_immutable_and_does_not_mutate_source() -> None:
    data = candidate()
    before = deepcopy(data)
    result = validate_demo_policy(data)
    assert data == before
    with pytest.raises(FrozenInstanceError):
        result.max_items_per_type = 99


def test_empty_or_wrong_typed_payload_fails_closed() -> None:
    fails(None)
    fails({})
    fails([])
