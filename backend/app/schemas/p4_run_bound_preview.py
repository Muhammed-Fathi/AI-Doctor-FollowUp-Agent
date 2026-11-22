"""P4-RB1 synthetic run-bound, READ-ONLY policy comparison preview DTO.

Not a rule evaluation, execution token, clinical result, API, or persistence
authorization. All content is sourced from F2's server-owned evidence check
and independently recomputed under the pinned R3-A 90-day demo policy.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.schemas.p5_review_evidence import EvidenceExclusionV2, ObservationV2, VerifiedFactV2


@dataclass(frozen=True, slots=True)
class PolicyComparisonPreviewV1:
    """One P4 90-day comparison; never a DR review flag or medical interpretation."""

    current_observation_id: str
    baseline_observation_id: str | None
    measure_type: str
    unit: str
    comparable: bool
    delta: Decimal | None
    incomparable_reason: Literal["no_baseline"] | None
    trust_basis: Literal["self_reported", "doctor_verified", "mixed"]


@dataclass(frozen=True, slots=True)
class RunBoundReviewInputPreviewV1:
    """Re-checked input shape only. This type has NO executable authority."""

    contract_version: Literal["p4-rb1-preview-1.0.0"]
    run_id: str
    patient_id: str
    doctor_id: str
    as_of_utc: str
    policy_version: str
    policy_reference_sha256: str
    policy_baseline_lookback_days: Literal[90]
    gate_evaluation_id: str
    gate_input_fingerprint_sha256: str
    bridge_input_fingerprint_sha256: str
    selected_document_ids: tuple[str, ...]
    selected_observation_ids: tuple[str, ...]
    verified_facts: tuple[VerifiedFactV2, ...]
    selected_observations: tuple[ObservationV2, ...]
    policy_comparisons: tuple[PolicyComparisonPreviewV1, ...]
    history_exclusions: tuple[EvidenceExclusionV2, ...]
    no_current_reason: Literal["no_current_selected"] | None
    runtime_evaluable: Literal[False] = field(default=False, init=False)
    rules_executed: Literal[False] = field(default=False, init=False)
    policy_status: Literal["unapproved"] = field(default="unapproved", init=False)
    review_items_persisted: Literal[False] = field(default=False, init=False)


__all__ = ["PolicyComparisonPreviewV1", "RunBoundReviewInputPreviewV1"]
