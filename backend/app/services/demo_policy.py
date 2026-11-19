"""Strict P4 demo-policy validation, without policy activation or rule evaluation.

A parsed mapping is an untrusted candidate, never a default/approved policy.
This module has no filesystem, database, network, agent, or medical side effects.
DEMO / SYNTHETIC ONLY — NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.clock import format_utc, parse_utc

_ACTIVE_RULES = ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
_VERIFICATION_ISSUES = ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")
_REQUIRED_PARAMETERS = frozenset(
    {
        "baseline_lookback_days",
        "stale_measurement_days",
        "demo_delta_systolic_mmHg",
        "demo_delta_diastolic_mmHg",
        "demo_delta_heart_rate_bpm",
        "demo_delta_glucose_mgdl",
        "ocr_confidence_floor",
        "conflict_tolerance",
        "max_items_per_type",
    }
)
_TOP_KEYS = frozenset(
    {
        "policy_version",
        "demo_only",
        "demo_as_of_utc",
        "notice",
        "parameters",
        "verification_issues",
        "rules",
    }
)
_VERSION = re.compile(r"demo-policy-[0-9]+\.[0-9]+\.[0-9]+\Z")
_NOTICE = "DEMO review prompts only — not clinical risk assessment. Not for clinical use."


class DemoPolicyError(ValueError):
    """Reject the entire policy without partial items or default values."""

    def __init__(self, message: str) -> None:
        self.code = "E_RULE_POLICY_INVALID"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class DemoPolicyCandidate:
    """A structurally verified *candidate*, NOT owner-approved or activated."""

    policy_version: str
    demo_as_of_utc: datetime
    notice: str
    baseline_lookback_days: int
    stale_measurement_days: int
    demo_delta_systolic_mmHg: Decimal
    demo_delta_diastolic_mmHg: Decimal
    demo_delta_heart_rate_bpm: Decimal
    demo_delta_glucose_mgdl: Decimal
    ocr_confidence_floor: Decimal
    conflict_tolerance: Decimal
    max_items_per_type: int
    enabled_rules: tuple[str, ...]
    disabled_rules: tuple[str, ...]
    enabled_verification_issues: tuple[str, ...]
    disabled_verification_issues: tuple[str, ...]


def _exact_keys(value: object, keys: frozenset[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise DemoPolicyError(f"{field}: missing, extra, or duplicate field.")
    if not all(isinstance(key, str) for key in value):
        raise DemoPolicyError(f"{field}: only string keys are supported.")
    return value


def _whole_number(value: object, field: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise DemoPolicyError(f"{field}: invalid bounded integer.")
    return value


def _decimal(value: object, field: str, low: Decimal, high: Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise DemoPolicyError(f"{field}: not a numeric demo parameter.")
    try:
        number = Decimal(str(value))
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise DemoPolicyError(f"{field}: invalid number.") from exc
    if not number.is_finite() or not low <= number <= high:
        raise DemoPolicyError(f"{field}: nonfinite or outside engineering bounds.")
    return number


def _switches(value: object, allowed: tuple[str, ...], field: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(value, list) or len(value) != len(allowed):
        raise DemoPolicyError(f"{field}: expected complete closed catalogue.")
    found: dict[str, bool] = {}
    for entry in value:
        if not isinstance(entry, Mapping) or set(entry) != {"id", "enabled"}:
            raise DemoPolicyError(f"{field}: invalid entry shape.")
        identifier = entry["id"]
        enabled = entry["enabled"]
        if not isinstance(identifier, str) or identifier not in allowed or identifier in found:
            raise DemoPolicyError(f"{field}: unknown, retired or duplicate identifier.")
        if type(enabled) is not bool:
            raise DemoPolicyError(f"{field}: enabled must be boolean.")
        found[identifier] = enabled
    if set(found) != set(allowed):
        raise DemoPolicyError(f"{field}: incomplete catalogue.")
    return (
        tuple(identifier for identifier in allowed if found[identifier]),
        tuple(identifier for identifier in allowed if not found[identifier]),
    )


def validate_demo_policy(raw: object) -> DemoPolicyCandidate:
    """Validate a parsed mapping; never activate thresholds or create ReviewFlags.

    No fallback when a field, rule ID, version, parameter or clock is invalid.
    The P4-2b rules engine and policy approval remain separate work.
    """
    data = _exact_keys(raw, _TOP_KEYS, "policy")
    version = data["policy_version"]
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise DemoPolicyError("policy_version: expected demo-policy-major.minor.patch.")
    if data["demo_only"] is not True:
        raise DemoPolicyError("demo_only must be true.")
    if data["notice"] != _NOTICE:
        raise DemoPolicyError("notice: not the fixed synthetic-use disclaimer.")

    as_of = data["demo_as_of_utc"]
    if not isinstance(as_of, str) or not as_of.endswith("Z"):
        raise DemoPolicyError("demo_as_of_utc: expected a canonical UTC string.")
    try:
        clock = parse_utc(as_of)
        if format_utc(clock) != as_of:
            raise ValueError("noncanonical UTC string")
    except (ValueError, TypeError, OverflowError) as exc:
        raise DemoPolicyError("demo_as_of_utc: invalid canonical UTC instant.") from exc

    p = _exact_keys(data["parameters"], _REQUIRED_PARAMETERS, "parameters")
    enabled_rules, disabled_rules = _switches(data["rules"], _ACTIVE_RULES, "rules")
    enabled_issues, disabled_issues = _switches(
        data["verification_issues"], _VERIFICATION_ISSUES, "verification_issues"
    )
    # These ceilings are implementation resource bounds, NOT diagnostic cutoffs.
    return DemoPolicyCandidate(
        policy_version=version,
        demo_as_of_utc=clock,
        notice=_NOTICE,
        baseline_lookback_days=_whole_number(p["baseline_lookback_days"], "lookback", 1, 365),
        stale_measurement_days=_whole_number(p["stale_measurement_days"], "staleness", 1, 365),
        demo_delta_systolic_mmHg=_decimal(p["demo_delta_systolic_mmHg"], "delta_sbp", Decimal("0.001"), Decimal("1000000")),
        demo_delta_diastolic_mmHg=_decimal(p["demo_delta_diastolic_mmHg"], "delta_dbp", Decimal("0.001"), Decimal("1000000")),
        demo_delta_heart_rate_bpm=_decimal(p["demo_delta_heart_rate_bpm"], "delta_hr", Decimal("0.001"), Decimal("1000000")),
        demo_delta_glucose_mgdl=_decimal(p["demo_delta_glucose_mgdl"], "delta_glucose", Decimal("0.001"), Decimal("1000000")),
        ocr_confidence_floor=_decimal(p["ocr_confidence_floor"], "ocr_floor", Decimal("0"), Decimal("1")),
        conflict_tolerance=_decimal(p["conflict_tolerance"], "conflict_tolerance", Decimal("0"), Decimal("1000000")),
        max_items_per_type=_whole_number(p["max_items_per_type"], "max_items", 1, 20),
        enabled_rules=enabled_rules,
        disabled_rules=disabled_rules,
        enabled_verification_issues=enabled_issues,
        disabled_verification_issues=disabled_issues,
    )


__all__ = ["DemoPolicyCandidate", "DemoPolicyError", "validate_demo_policy"]
