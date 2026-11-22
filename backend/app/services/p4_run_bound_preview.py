"""P4-RB1: internal, bounded, READ-ONLY run-bound 90-day demo comparison preview.

F2 first validates the real run and immutable F1 PROCEED against current
sources. A *separate* locked read recomputes 90-day (not F2 365-day) history
comparisons; fresh F2 validation after that read prevents returning a stale
successful preview observed during the computation. The SQLite and filesystem
snapshots are not atomic and no downstream caller may treat this preview as
an execution/DR authorization. No rule evaluation, migration or write.
SYNTHETIC EDUCATIONAL ONLY — NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc, to_utc
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import RunSelectedObservation, WorkflowRun
from app.schemas.p4_run_bound_preview import (
    PolicyComparisonPreviewV1,
    RunBoundReviewInputPreviewV1,
)
from app.services.demo_policy import DemoPolicyCandidate, DemoPolicyError, validate_demo_policy
from app.services.monitoring import MonitoringInputError
from app.services.p4_explicit_history import compare_explicit_current_with_history
from app.services.p4_readonly_provenance import load_readonly_provenance_evidence
from app.services.p5_evidence_bridge import build_run_evaluable_review_evidence
from app.services.p5_run_gate import inspect_current_run_gate_locked

POLICY_CANONICAL_SHA256 = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
POLICY_VERSION = "demo-policy-1.1.0"
POLICY_LOOKBACK_DAYS = 90
EXPECTED_RULE_IDS = ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
EXPECTED_VI_IDS = ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")


def _deny(message: str) -> ApiError:
    return ApiError(409, ErrorCode.VALIDATION, message)


def _pinned_policy() -> DemoPolicyCandidate:
    """Reference-only immutable literals; DO NOT load test-only policy files here.

    The owner-pinned LF source hash is asserted by the offline P4 reference
    tests. This internal adapter merely recompiles its exact reviewed values
    as non-executable comparison settings, NEVER a runtime policy permission.
    """
    raw: dict[str, object] = {
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
        "verification_issues": [{"id": key, "enabled": True} for key in EXPECTED_VI_IDS],
        "rules": [{"id": key, "enabled": True} for key in EXPECTED_RULE_IDS],
    }
    try:
        candidate = validate_demo_policy(raw)
    except DemoPolicyError:
        raise _deny("The fixed synthetic comparison reference is invalid.") from None
    if (
        candidate.policy_version != POLICY_VERSION
        or candidate.baseline_lookback_days != POLICY_LOOKBACK_DAYS
        or candidate.enabled_rules != EXPECTED_RULE_IDS
        or candidate.disabled_rules
        or candidate.enabled_verification_issues != EXPECTED_VI_IDS
        or candidate.disabled_verification_issues
    ):
        raise _deny("The fixed synthetic comparison reference was altered.")
    return candidate

def _policy_projection_locked(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
    evidence,
    policy: DemoPolicyCandidate,
) -> tuple[PolicyComparisonPreviewV1, ...]:
    """Caller holds a fresh BEGIN IMMEDIATE; never inserts or updates anything."""
    gate = inspect_current_run_gate_locked(
        db,
        principal=principal,
        run_id=run_id,
        at=validation_clock,
        upload_root=upload_root,
    )
    if (
        gate.input_fingerprint_sha256 != evidence.gate_input_fingerprint_sha256
        or gate.gate_version != evidence.gate_version
    ):
        raise _deny("The source gate changed since the F2 evidence projection.")

    run = db.get(WorkflowRun, run_id)
    if (
        run is None
        or run.status != "queued"
        or run.patient_id != evidence.patient_id
        or run.doctor_id != evidence.doctor_id
        or run.as_of_utc != evidence.as_of_utc
        or run.policy_version != policy.policy_version
        or run.policy_version != evidence.policy_version
        or format_utc(policy.demo_as_of_utc) != run.as_of_utc
    ):
        raise _deny("Run identity, demo policy or injected clock differs from the pinned scope.")

    selection = tuple(
        db.execute(
            select(RunSelectedObservation.observation_id)
            .where(RunSelectedObservation.workflow_run_id == run.id)
            .order_by(RunSelectedObservation.observation_id)
        ).scalars()
    )
    if (
        selection != evidence.selected_observation_ids
        or len(selection) > 6
        or len(selection) != len(set(selection))
        or tuple(x.observation_id for x in evidence.selected_observations) != selection
    ):
        raise _deny("Immutable F0 current selection changed.")

    provenance = load_readonly_provenance_evidence(
        db,
        principal=principal,
        patient_id=run.patient_id,
        as_of_utc=parse_utc(run.as_of_utc),
    )
    by_id = {entry.observation.id: entry for entry in provenance.records}
    if len(by_id) != len(provenance.records) or len(by_id) > 100:
        raise _deny("Bounded patient history is unavailable.")

    excluded_ids = {item.observation_id for item in evidence.history_exclusions}
    if len(excluded_ids) != len(evidence.history_exclusions) or not excluded_ids.issubset(
        by_id.keys()
    ):
        raise _deny("Historical exclusion evidence changed.")
    if excluded_ids.intersection(selection):
        raise _deny("Selected current evidence may not be excluded.")

    selected_rows = []
    for projected in evidence.selected_observations:
        entry = by_id.get(projected.observation_id)
        if entry is None:
            raise _deny("Selected current observation is no longer scoped.")
        row = entry.observation
        try:
            measured = format_utc(parse_utc(cast(str, row.measured_at)))
            value = Decimal(str(row.value))
        except (ValueError, TypeError, AttributeError):
            raise _deny("Selected current observation is malformed.") from None
        if (
            row.patient_id != evidence.patient_id
            or row.measure_type != projected.measure_type
            or row.unit != projected.unit
            or value != projected.value
            or measured != projected.measured_at
            or row.trust_level != projected.trust_level
            or entry.source != projected.source
            or entry.source_fact_id != projected.source_fact_id
            or entry.source_document_id != projected.source_document_id
        ):
            raise _deny("Selected observation values or provenance changed.")
        selected_rows.append(row)

    if not selected_rows:
        if evidence.no_current_reason != "no_current_selected" or evidence.comparisons:
            raise _deny("Zero selected current observations must remain an explicit no-current.")
        return ()

    history_rows = tuple(
        by_id[observation_id].observation
        for observation_id in sorted(by_id)
        if observation_id not in excluded_ids and observation_id not in selection
    )
    try:
        compared = compare_explicit_current_with_history(
            current=tuple(selected_rows),
            history=history_rows,
            patient_id=run.patient_id,
            as_of_utc=parse_utc(run.as_of_utc),
            baseline_lookback_days=policy.baseline_lookback_days,
        )
    except MonitoringInputError:
        raise _deny("The 90-day synthetic comparison inputs are invalid.") from None
    if compared.excluded_history or len(compared.comparisons) != len(selected_rows):
        raise _deny("Unreported history exclusion or incomplete comparison.")

    return tuple(
        PolicyComparisonPreviewV1(
            current_observation_id=item.current_observation_id,
            baseline_observation_id=item.baseline_observation_id,
            measure_type=item.measure_type,
            unit=item.unit,
            comparable=item.comparable,
            delta=item.delta,
            incomparable_reason=(
                "no_baseline" if item.incomparable_reason == "missing_baseline" else None
            ),
            trust_basis=cast(
                Literal["self_reported", "doctor_verified", "mixed"], item.trust_basis
            ),
        )
        for item in compared.comparisons
    )


def build_p4_run_bound_review_input_preview(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
) -> RunBoundReviewInputPreviewV1:
    """Return only a non-executable, no-write preview from fresh server evidence.

    No cached F2 DTO can be injected. Recheck F2 again after the independent
    policy-window read, rejecting state changes; still not a cross-resource
    atomic snapshot. No caller-specified lookback, policy version or gate flag.
    """
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A fresh clean Session is required.")
    first = build_run_evaluable_review_evidence(
        db,
        principal=principal,
        run_id=run_id,
        validation_clock=validation_clock,
        upload_root=upload_root,
    )
    policy = _pinned_policy()
    if first.policy_version != policy.policy_version:
        raise _deny("Run policy is not the pinned synthetic reference.")
    try:
        clock = to_utc(validation_clock)
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except (TypeError, ValueError, AttributeError):
        db.rollback()
        raise ApiError(400, ErrorCode.VALIDATION, "Aware validation clock required.") from None
    except OperationalError:
        db.rollback()
        raise ApiError(503, ErrorCode.VALIDATION, "Verification database is unavailable.") from None

    try:
        comparisons = _policy_projection_locked(
            db,
            principal=principal,
            run_id=run_id,
            validation_clock=clock,
            upload_root=upload_root,
            evidence=first,
            policy=policy,
        )
    finally:
        db.rollback()

    # Separate locks, not an atomic filesystem+DB read. Never authorize writes
    # or rule execution from this value, even if the final recheck succeeds.
    last = build_run_evaluable_review_evidence(
        db,
        principal=principal,
        run_id=run_id,
        validation_clock=clock,
        upload_root=upload_root,
    )
    if first != last:
        raise _deny("Run evidence changed during policy-window projection.")
    if _pinned_policy() != policy:
        raise _deny("Pinned demo policy changed during the projection.")

    return RunBoundReviewInputPreviewV1(
        contract_version="p4-rb1-preview-1.0.0",
        run_id=first.run_id,
        patient_id=first.patient_id,
        doctor_id=first.doctor_id,
        as_of_utc=first.as_of_utc,
        policy_version=first.policy_version,
        policy_reference_sha256=POLICY_CANONICAL_SHA256,
        policy_baseline_lookback_days=POLICY_LOOKBACK_DAYS,
        gate_evaluation_id=first.gate_evaluation_id,
        gate_input_fingerprint_sha256=first.gate_input_fingerprint_sha256,
        bridge_input_fingerprint_sha256=first.bridge_input_fingerprint_sha256,
        selected_document_ids=first.selected_document_ids,
        selected_observation_ids=first.selected_observation_ids,
        verified_facts=first.verified_facts,
        selected_observations=first.selected_observations,
        policy_comparisons=comparisons,
        history_exclusions=first.history_exclusions,
        no_current_reason=first.no_current_reason,
    )


__all__ = ["POLICY_VERSION", "build_p4_run_bound_review_input_preview"]
