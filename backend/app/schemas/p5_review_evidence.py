"""P5-F2 strictly typed, immutable, synthetic run-bound evidence (not execution).

These internal data-transfer objects carry no clinician-facing text, no OCR
snippet, no API field accepting a client-crafted clearance and no DR output.
The server-only builder validates every member before constructing this type.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, slots=True)
class VerifiedFactV2:
    fact_id: str
    document_id: str
    field_name: str
    normalized_value: str | None
    unit: str | None
    corrected_from_fact_id: str | None
    verification_status: Literal["verified"] = field(default="verified", init=False)
    trust_basis: Literal["doctor_verified"] = field(default="doctor_verified", init=False)


@dataclass(frozen=True, slots=True)
class ObservationV2:
    observation_id: str
    patient_id: str
    measure_type: str
    value: Decimal
    unit: str
    measured_at: str
    source: str
    trust_level: Literal["self_reported_validated", "doctor_verified"]
    source_fact_id: str | None
    source_document_id: str | None


@dataclass(frozen=True, slots=True)
class ComparisonV2:
    current_observation_id: str
    baseline_observation_id: str | None
    measure_type: str
    unit: str
    comparable: bool
    delta: Decimal | None
    incomparable_reason: Literal["no_baseline", "not_admissible"] | None
    trust_basis: Literal["self_reported", "doctor_verified", "mixed"]


@dataclass(frozen=True, slots=True)
class EvidenceExclusionV2:
    observation_id: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class EvaluableReviewEvidenceV2:
    """V2 means *evidence shape*, never runtime permission or clinical clearance."""

    contract_version: Literal["2.0.0"]
    run_id: str
    patient_id: str
    doctor_id: str
    as_of_utc: str
    workflow_version: str
    state_schema_version: str
    mapping_version: str
    policy_version: str
    gate_evaluation_id: str
    gate_version: str
    gate_input_fingerprint_sha256: str
    bridge_input_fingerprint_sha256: str
    selected_document_ids: tuple[str, ...]
    selected_observation_ids: tuple[str, ...]
    historical_excluded_vi002_ids: tuple[str, ...]
    verified_facts: tuple[VerifiedFactV2, ...]
    selected_observations: tuple[ObservationV2, ...]
    comparisons: tuple[ComparisonV2, ...]
    history_exclusions: tuple[EvidenceExclusionV2, ...]
    no_current_reason: Literal["no_current_selected"] | None = None
    bridge_validated: Literal[True] = field(default=True, init=False)
    runtime_evaluable: Literal[False] = field(default=False, init=False)
    rules_executed: Literal[False] = field(default=False, init=False)
    policy_status: Literal["unapproved"] = field(default="unapproved", init=False)


__all__ = [
    "ComparisonV2",
    "EvaluableReviewEvidenceV2",
    "EvidenceExclusionV2",
    "ObservationV2",
    "VerifiedFactV2",
]
