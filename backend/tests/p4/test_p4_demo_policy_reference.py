"""R3-A owner-pinned DEMO reference tests: offline, not a runtime policy gate.

The owner approved synthetic-only reference numbers after PR #27 merged.
This test-only loader does NOT authorize a run, a rule tool or a patient action.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

import pytest
import yaml

from app.core.paths import REPO_ROOT
from app.services.demo_policy import DemoPolicyError, validate_demo_policy

POLICY_PATH = REPO_ROOT / "data" / "synthetic" / "policy" / "demo_review_policy.yaml"
POLICY_SHA256 = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
AS_OF = "2026-11-14T12:00:00Z"
VERIFICATION_ISSUES = ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")
RULES = ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
GOLD_SHA256 = {
    "A": "643c219ba15c77e2ddd1f7273931aafc40d3bf37725386c590dc2535ff5211be",
    "B": "4019f1700fd7407e5df9f264dcd73b317d3b61d8e511e7ad8689a2de2d054cd3",
    "C": "555d41d5d52187a154a2d3e258e94cc9f1e5dd3bee6ab67aa4ac1d359156f6f0",
    "D": "d4aea8155f690c4420a194e317b7fc202a9d3a3e7671bb22d363c70092065940",
}
EXPECTED_NUMBERS = (
    90,
    30,
    Decimal("10"),
    Decimal("8"),
    Decimal("15"),
    Decimal("40"),
    Decimal("0.70"),
    Decimal("0"),
    3,
)


class _NoDuplicateSafeLoader(yaml.SafeLoader):
    """YAML loader used ONLY by this fixture test; duplicate keys fail closed."""


def _mapping_without_duplicates(
    loader: _NoDuplicateSafeLoader, node: yaml.nodes.MappingNode
) -> dict:
    values: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in values:
            raise DemoPolicyError("Duplicate YAML key in the offline reference.")
        values[key] = loader.construct_object(value_node)
    return values


_NoDuplicateSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_without_duplicates
)


def _decoded(source: str) -> dict:
    raw = yaml.load(source, Loader=_NoDuplicateSafeLoader)
    if not isinstance(raw, dict):
        raise DemoPolicyError("The offline reference is not a mapping.")
    return raw


def _approved_reference(raw: object):
    """Test-only owner reference assertion; NOT a runtime approval function."""
    policy = validate_demo_policy(raw)
    values = (
        policy.baseline_lookback_days,
        policy.stale_measurement_days,
        policy.demo_delta_systolic_mmHg,
        policy.demo_delta_diastolic_mmHg,
        policy.demo_delta_heart_rate_bpm,
        policy.demo_delta_glucose_mgdl,
        policy.ocr_confidence_floor,
        policy.conflict_tolerance,
        policy.max_items_per_type,
    )
    if (
        policy.policy_version != "demo-policy-1.1.0"
        or policy.demo_as_of_utc != datetime(2026, 11, 14, 12, tzinfo=UTC)
        or policy.notice
        != "DEMO review prompts only — not clinical risk assessment. Not for clinical use."
        or values != EXPECTED_NUMBERS
        or policy.enabled_verification_issues != VERIFICATION_ISSUES
        or policy.disabled_verification_issues
        or policy.enabled_rules != RULES
        or policy.disabled_rules
    ):
        raise DemoPolicyError("Unapproved synthetic policy revision or disabled blocker.")
    return policy


def _canonical_lf_bytes(content: bytes) -> bytes:
    """Allow full LF or full CRLF checkouts; reject mixed/bare CR.

    Hash the canonical LF Git blob representation. Neither whitespace nor
    fixture content is discarded; only Git's platform line endings normalize.
    This is strictly TEST-ONLY, never a runtime trust/approval token.
    """
    without_crlf = content.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise DemoPolicyError("Unsupported bare carriage return in reference.")
    if b"\r\n" in content and b"\n" in without_crlf:
        raise DemoPolicyError("Mixed LF and CRLF line endings in reference.")
    return content.replace(b"\r\n", b"\n")


def _reference():
    content = _canonical_lf_bytes(POLICY_PATH.read_bytes())
    if sha256(content).hexdigest() != POLICY_SHA256:
        raise DemoPolicyError("Synthetic policy bytes changed without review and versioning.")
    return _approved_reference(_decoded(content.decode("utf-8")))


def _gold(case: str) -> dict:
    path = REPO_ROOT / "data" / "synthetic" / "golden_cases" / f"GOLD-{case}.expected.json"
    content = _canonical_lf_bytes(path.read_bytes())
    if sha256(content).hexdigest() != GOLD_SHA256[case]:
        raise DemoPolicyError("Golden case changed without separate review.")
    return json.loads(content)


def test_reference_has_exact_owner_pinned_sha256() -> None:
    normalized = _canonical_lf_bytes(POLICY_PATH.read_bytes())
    assert sha256(normalized).hexdigest() == POLICY_SHA256
    assert sha256(_canonical_lf_bytes(normalized.replace(b"\n", b"\r\n"))).hexdigest() == (
        POLICY_SHA256
    )
    # A line-ending conversion is allowed; a mixed checkout or bare CR is not.
    with pytest.raises(DemoPolicyError, match="Mixed"):
        _canonical_lf_bytes(normalized.replace(b"\n", b"\r\n", 1))
    with pytest.raises(DemoPolicyError, match="bare carriage return"):
        _canonical_lf_bytes(normalized.replace(b"\n", b"\r", 1))
    assert _reference().policy_version == "demo-policy-1.1.0"


def test_reference_has_all_exact_synthetic_numbers_and_fixed_clock() -> None:
    policy = _reference()
    assert policy.demo_as_of_utc == datetime(2026, 11, 14, 12, tzinfo=UTC)
    assert (
        policy.baseline_lookback_days,
        policy.stale_measurement_days,
        policy.demo_delta_systolic_mmHg,
        policy.demo_delta_diastolic_mmHg,
        policy.demo_delta_heart_rate_bpm,
        policy.demo_delta_glucose_mgdl,
        policy.ocr_confidence_floor,
        policy.conflict_tolerance,
        policy.max_items_per_type,
    ) == EXPECTED_NUMBERS


def test_owner_reference_is_immutable_after_validation() -> None:
    policy = _reference()
    with pytest.raises(FrozenInstanceError):
        policy.max_items_per_type = 9


def test_all_blocking_vi_and_current_dr_ids_are_preserved() -> None:
    policy = _reference()
    assert policy.enabled_verification_issues == VERIFICATION_ISSUES
    assert policy.disabled_verification_issues == ()
    assert policy.enabled_rules == RULES
    assert policy.disabled_rules == ()


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("demo-policy-1.1.0", "demo-policy-1.1.1"),
        ("2026-11-14T12:00:00Z", "2026-11-15T12:00:00Z"),
        ("  demo_delta_systolic_mmHg: 10", "  demo_delta_systolic_mmHg: 11"),
        ("  - id: VI-002\n    enabled: true", "  - id: VI-002\n    enabled: false"),
        ("  max_items_per_type: 3", "  max_items_per_type: 4"),
    ],
)
def test_any_file_edit_invalidates_owner_reference_seal(before: str, after: str) -> None:
    source = POLICY_PATH.read_text(encoding="utf-8")
    assert source.count(before) == 1
    mutated = source.replace(before, after, 1)
    assert sha256(mutated.encode("utf-8")).hexdigest() != POLICY_SHA256


def test_duplicate_yaml_keys_fail_closed_before_policy_validation() -> None:
    source = POLICY_PATH.read_text(encoding="utf-8")
    mutated = source.replace(
        "  baseline_lookback_days: 90",
        "  baseline_lookback_days: 90\n  baseline_lookback_days: 30",
    )
    with pytest.raises(DemoPolicyError, match="Duplicate YAML key"):
        _decoded(mutated)


@pytest.mark.parametrize("vi_id", VERIFICATION_ISSUES)
def test_validator_accepting_disabled_candidate_never_makes_owner_reference_valid(
    vi_id: str,
) -> None:
    candidate = _decoded(POLICY_PATH.read_text(encoding="utf-8"))
    changed = deepcopy(candidate)
    next(x for x in changed["verification_issues"] if x["id"] == vi_id)["enabled"] = False
    # The existing generic candidate validator is intentionally structural.
    assert vi_id in validate_demo_policy(changed).disabled_verification_issues
    # Owner's approved reference cannot turn off ANY blocking verification issue.
    with pytest.raises(DemoPolicyError, match="Unapproved synthetic policy"):
        _approved_reference(changed)


@pytest.mark.parametrize("change", ["version", "clock", "delta", "rule_disabled"])
def test_syntactically_valid_new_policy_is_not_automatically_approved(change: str) -> None:
    altered = _decoded(POLICY_PATH.read_text(encoding="utf-8"))
    if change == "version":
        altered["policy_version"] = "demo-policy-1.1.1"
    elif change == "clock":
        altered["demo_as_of_utc"] = "2026-11-15T12:00:00Z"
    elif change == "delta":
        altered["parameters"]["demo_delta_glucose_mgdl"] = 41
    else:
        altered["rules"][0]["enabled"] = False
    validate_demo_policy(altered)
    with pytest.raises(DemoPolicyError, match="Unapproved synthetic policy"):
        _approved_reference(altered)


@pytest.mark.parametrize("case", ["A", "B", "C", "D"])
def test_all_four_golden_expected_fixtures_remain_pinned_and_offline(case: str) -> None:
    golden_path = (
        REPO_ROOT / "data" / "synthetic" / "golden_cases" / f"GOLD-{case}.expected.json"
    )
    canonical = _canonical_lf_bytes(golden_path.read_bytes())
    assert sha256(canonical).hexdigest() == GOLD_SHA256[case]
    assert sha256(_canonical_lf_bytes(canonical.replace(b"\n", b"\r\n"))).hexdigest() == (
        GOLD_SHA256[case]
    )
    expected = _gold(case)
    assert expected["case_id"] == f"GOLD-{case}"
    assert expected["demo_as_of_utc"] == AS_OF
    assert expected["candidate_policy_status"] == "test-only-unapproved"
    if case != "C":
        assert len(expected["expected_review_rule_ids"]) == expected["expected_review_count"]
    else:
        assert expected["pre_verification"]["expected_review_rule_ids"] == []
        assert expected["post_fixture_correction"]["expected_review_rule_ids"] == []


def test_gold_cases_keep_delta_semantics_and_c_blocker_before_scripted_fix() -> None:
    policy = _reference()
    a, b, c, d = (_gold(case) for case in ("A", "B", "C", "D"))
    assert a["expected_review_rule_ids"] == []
    assert b["expected_review_rule_ids"] == ["DR-005"]
    assert Decimal(str(b["expected_dr005"]["delta"])) > policy.demo_delta_systolic_mmHg
    assert c["pre_verification"]["expected_open_verification_issue_ids"] == [
        "VI-001",
        "VI-002",
        "VI-003",
        "VI-005",
    ]
    assert c["pre_verification"]["pending_active_fact_count"] == 3
    assert Decimal(str(c["post_fixture_correction"]["expected_delta"])) <= (
        policy.demo_delta_glucose_mgdl
    )
    assert "FAIL / NOT PROVEN" in c["real_ocr_result"]
    assert d["expected_review_rule_ids"] == ["DR-001", "DR-003", "DR-005", "DR-008", "DR-009"]
    assert Decimal(str(d["expected_deltas"]["diastolic_bp"])) > (policy.demo_delta_diastolic_mmHg)


def test_reference_artifact_is_not_imported_by_app_runtime() -> None:
    # This is a fixture, NOT a loaded/approved runtime policy. No new API or
    # trusted EvaluableReviewEvidenceV2 source is granted by this file.
    for source in (REPO_ROOT / "backend" / "app").rglob("*.py"):
        assert "demo_review_policy.yaml" not in source.read_text(encoding="utf-8")
