"""Typed fixtures for P4-RB2's PURE OFFLINE six-rule educational evaluator.

These dataclasses are not runtime authorizations and carry no ORM/session/agent
handles. The result cannot be persisted or dispatched to a doctor or patient.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


class OfflineRuleError(ValueError):
    """Fail-closed evaluation; no partially evaluated flags escape on error."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class OfflineRulePolicy:
    """Explicit R3-A candidate values, never an approved runtime policy."""

    policy_version: str = "demo-policy-1.1.0"
    demo_only: bool = True
    demo_as_of_utc: datetime = datetime(2026, 11, 14, 12, tzinfo=UTC)
    baseline_lookback_days: int = 90
    stale_measurement_days: int = 30
    demo_delta_systolic_mmHg: Decimal | str | int = 10
    demo_delta_diastolic_mmHg: Decimal | str | int = 8
    demo_delta_heart_rate_bpm: Decimal | str | int = 15
    demo_delta_glucose_mgdl: Decimal | str | int = 40
    ocr_confidence_floor: Decimal | str | int = "0.70"
    conflict_tolerance: Decimal | str | int = 0
    max_items_per_type: int = 3
    enabled_verification_issues: tuple[str, ...] = (
        "VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006"
    )
    enabled_rules: tuple[str, ...] = (
        "DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009"
    )
    notice: str = (
        "DEMO review prompts only — not clinical risk assessment. "
        "Not for clinical use."
    )


@dataclass(frozen=True, slots=True)
class OfflineObservation:
    """Synthetic test record; source fields are untrusted fixture assertions."""

    id: str
    patient_id: str
    measure_type: str
    value: Decimal | int | float | str
    unit: str
    measured_at: datetime | str | None
    validation: str
    trust_level: str
    created_at: datetime | str | None = None
    source: str = "seed_fixture"
    source_document_id: str | None = None
    source_fact_id: str | None = None
    source_fact_verification_status: str | None = None
    # "stored_independently_verified" is a FUTURE RB3 server-side state; never
    # a valid caller claim on the RB2 pure fixture interface.
    lineage_status: str = "unavailable"


@dataclass(frozen=True, slots=True)
class OfflineRuleInput:
    patient_id: str
    selected_current: tuple[OfflineObservation, ...]
    history: tuple[OfflineObservation, ...]
    as_of_utc: datetime | str
    policy: OfflineRulePolicy
    # Fixture assertions, NOT a caller-supplied blocker count or F1 gate receipt.
    active_fact_verification_statuses: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OfflineEvidenceExclusion:
    observation_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class OfflineRuleFlag:
    rule_id: str
    reason_code: str
    workflow_hint: str
    message: str
    evidence: tuple[str, ...]
    trust_basis: str
    policy_version: str
    dedupe_key: str
    # A DR-006 with this marker is never an authenticated doctor verification.
    provenance_status: str = "fixture_asserted"
    demo_only: bool = True


@dataclass(frozen=True, slots=True)
class OfflineRuleResult:
    flags: tuple[OfflineRuleFlag, ...]
    excluded: tuple[OfflineEvidenceExclusion, ...]
    policy_version: str
    demo_only: bool = True
    offline_candidate_rules_evaluated: bool = True
    runtime_evaluable: bool = False
    rules_executed: bool = False
    review_items_persisted: bool = False
    policy_status: str = "unapproved"


__all__ = [
    "OfflineEvidenceExclusion",
    "OfflineObservation",
    "OfflineRuleError",
    "OfflineRuleFlag",
    "OfflineRuleInput",
    "OfflineRulePolicy",
    "OfflineRuleResult",
]
