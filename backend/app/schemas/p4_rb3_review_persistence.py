"""P4-RB3 frozen receipt, layered exclusion, and typed denial schemas.

This module defines the immutable output receipt and typed denial reasons for
P4-RB3 durable run-bound review persistence. A receipt reports a completed
durable demo persistence transaction; it is never a clinical clearance,
execution token, or policy approval.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class RB3DenialReason(StrEnum):
    """Bounded machine-readable denial and replay-conflict reason codes."""

    MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE = "measurement_timestamp_out_of_supported_range"
    DR006_PERSISTENCE_NOT_AUTHORIZED = "dr006_persistence_not_authorized"
    HISTORICAL_EXCLUSION_EVIDENCE_CHANGED = "historical_exclusion_evidence_changed"
    STORED_LINEAGE_EVIDENCE_INCONSISTENT = "stored_lineage_evidence_inconsistent"
    SELECTED_CURRENT_EVIDENCE_EXCLUDED = "selected_current_evidence_excluded"
    EVIDENCE_UNRESOLVABLE = "evidence_unresolvable"
    COMPLETION_EVIDENCE_MISSING = "completion_evidence_missing"
    ORPHAN_REVIEW_AUDIT = "orphan_review_audit"
    EXTRA_PERSISTED_ITEMS = "extra_persisted_items"
    MISSING_PERSISTED_EVIDENCE = "missing_persisted_evidence"
    INPUT_IDENTITY_CHANGED = "input_identity_changed"
    OUTPUT_IDENTITY_CHANGED = "output_identity_changed"
    AUDIT_BUSINESS_INCONSISTENT = "audit_business_inconsistent"
    AUDIT_KEY_COLLISION = "audit_key_collision"
    INTEGRITY_CONFLICT = "integrity_conflict"


@dataclass(frozen=True, slots=True, order=True)
class PersistedEvidenceExclusionV1:
    """One deterministic exclusion entry surfaced in an RB3 receipt."""

    observation_id: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class LayeredEvidenceExclusionsV1:
    """Explicit separation of L0 loader checks, L1 F2-compatible, L2 RB2, and L3 merged."""

    l0_lineage_checks: tuple[PersistedEvidenceExclusionV1, ...]
    l1_exclusions: tuple[PersistedEvidenceExclusionV1, ...]
    l2_exclusions: tuple[PersistedEvidenceExclusionV1, ...]
    l3_merged: tuple[PersistedEvidenceExclusionV1, ...]


@dataclass(frozen=True, slots=True)
class ReviewPersistenceReceiptV1:
    """Durable write/replay receipt for one sealed RB3 run evaluation."""

    contract_version: Literal["p4-rb3-receipt-1.0.0"]
    run_id: str
    patient_id: str
    doctor_id: str
    as_of_utc: str
    policy_version: str
    policy_reference_sha256: str
    gate_evaluation_id: str
    gate_version: str
    gate_input_fingerprint_sha256: str
    bridge_input_fingerprint_sha256: str
    rb3_fingerprint_version: str
    input_fingerprint_sha256: str
    output_identity_sha256: str
    evaluation_id: str
    audit_event_id: str
    lineage_label_policy: Literal["a2_transport_label"]
    dr006_policy: Literal["prohibited_denied", "not_present"]
    replayed: bool
    review_items_persisted: int
    review_items_total: int
    evidence_links_persisted: int
    evidence_links_total: int
    excluded_evidence: tuple[PersistedEvidenceExclusionV1, ...]
    layered_exclusions: LayeredEvidenceExclusionsV1
    l1_exclusion_count: int
    l2_exclusion_count: int
    evaluation_completed: Literal[True] = field(default=True, init=False)
    offline_evaluator_invoked: Literal[True] = field(default=True, init=False)
    runtime_evaluable: Literal[False] = field(default=False, init=False)
    policy_status: Literal["unapproved"] = field(default="unapproved", init=False)
    demo_only: Literal[True] = field(default=True, init=False)
    not_for_clinical_use: Literal[True] = field(default=True, init=False)


__all__ = [
    "LayeredEvidenceExclusionsV1",
    "PersistedEvidenceExclusionV1",
    "RB3DenialReason",
    "ReviewPersistenceReceiptV1",
]
