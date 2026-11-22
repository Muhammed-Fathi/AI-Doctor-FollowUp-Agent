"""P5-F2: internal read-only, run-owned deterministic evidence bridge.

A persisted F1 PROCEED is necessary, never sufficient. Recompute the exact F1
fingerprint, blockers, source byte hashes and doctor scope under BEGIN IMMEDIATE;
project only server-recorded and properly attributed synthetic P4 inputs.
No DR evaluation, graph transition, API, LLM, task or writable evidence token.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc, to_utc
from app.core.enums import MAPPING_TABLE
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import (
    Document,
    ExtractedFact,
    RunGateEvaluation,
    RunSelectedDocument,
    RunSelectedObservation,
    WorkflowRun,
)
from app.schemas.p5_review_evidence import (
    ComparisonV2,
    EvaluableReviewEvidenceV2,
    EvidenceExclusionV2,
    ObservationV2,
    VerifiedFactV2,
)
from app.services.monitoring import MonitoringInputError, ObservationSnapshot, admissibility_reason
from app.services.p4_document_preflight import inspect_selected_document_verification
from app.services.p4_explicit_history import compare_explicit_current_with_history
from app.services.p4_readonly_provenance import load_readonly_provenance_evidence
from app.services.p5_run_gate import GATE_VERSION, inspect_current_run_gate_locked

CONTRACT_VERSION = "2.0.0"
COMPARISON_HISTORY_VERSION = "f2-history-365d-v1"
HISTORY_LOOKBACK_DAYS = 365
MAX_CURRENT_OBSERVATIONS = 6
MAX_FACTS = 40
MAX_HISTORY_OBSERVATIONS = 100


def _invalid(message: str) -> ApiError:
    return ApiError(409, ErrorCode.VALIDATION, message)


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _number(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise _invalid("Invalid scoped observation value.") from None
    if not parsed.is_finite() or parsed <= 0:
        raise _invalid("Invalid scoped observation value.")
    return parsed


def _projection(
    db: Session, *, principal: Principal, run_id: str, validation_clock: datetime, upload_root: str
) -> EvaluableReviewEvidenceV2:
    """Called solely while the wrapper holds a fresh SQLite IMMEDIATE lock."""
    gate = inspect_current_run_gate_locked(
        db,
        principal=principal,
        run_id=run_id,
        at=validation_clock,
        upload_root=upload_root,
    )
    if gate.decision != "proceed" or gate.blocking_fact_count != 0:
        raise _invalid("Run is not eligible for V2 evidence.")

    run = db.get(WorkflowRun, run_id)
    if run is None or run.status != "queued":
        raise _invalid("Run state changed before V2 projection.")
    try:
        run_clock = parse_utc(run.as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise _invalid("Invalid persisted run clock.") from None

    stored_gate = db.execute(
        select(RunGateEvaluation).where(
            RunGateEvaluation.workflow_run_id == run.id,
            RunGateEvaluation.gate_version == GATE_VERSION,
            RunGateEvaluation.input_fingerprint_sha256 == gate.input_fingerprint_sha256,
        )
    ).scalar_one_or_none()
    if stored_gate is None or stored_gate.decision != "proceed":
        raise _invalid("A matching stored F1 PROCEED is required.")

    selected_docs = tuple(
        db.execute(
            select(RunSelectedDocument)
            .where(RunSelectedDocument.workflow_run_id == run.id)
            .order_by(RunSelectedDocument.document_id)
        ).scalars()
    )
    selected_obs = tuple(
        db.execute(
            select(RunSelectedObservation)
            .where(RunSelectedObservation.workflow_run_id == run.id)
            .order_by(RunSelectedObservation.observation_id)
        ).scalars()
    )
    document_ids = tuple(x.document_id for x in selected_docs)
    observation_ids = tuple(x.observation_id for x in selected_obs)
    if not 1 <= len(document_ids) <= 5 or len(observation_ids) > MAX_CURRENT_OBSERVATIONS:
        raise _invalid("Run-selected current sources exceed the F2 evidence boundary.")
    if len(set(document_ids)) != len(document_ids) or len(set(observation_ids)) != len(
        observation_ids
    ):
        raise _invalid("Run-selected sources contain duplicate IDs.")

    # F1 recomputes all VI blockers; this independent P4 check also enforces
    # actual stored doctor decisions (including corrected-from lineage).
    preflight = inspect_selected_document_verification(
        db, principal=principal, patient_id=run.patient_id, document_ids=document_ids
    )
    if not preflight.candidate_documents_clear:
        raise _invalid("Selected facts do not have current verified lineage.")

    verified: list[VerifiedFactV2] = []
    for document_id in document_ids:
        document = db.get(Document, document_id)
        if document is None or document.patient_id != run.patient_id:
            raise _invalid("Selected document scope changed.")
        facts = tuple(
            db.execute(
                select(ExtractedFact)
                .where(ExtractedFact.document_id == document_id)
                .order_by(ExtractedFact.id)
                .limit(MAX_FACTS + 1)
            ).scalars()
        )
        if len(facts) > MAX_FACTS:
            raise _invalid("Selected facts exceed the F2 evidence bound.")
        # F1 preflight already establishes that these verified replacement
        # facts have valid current original doctor-decision lineage.
        for fact in facts:
            if fact.patient_id != run.patient_id:
                raise _invalid("Selected fact scope changed.")
            if fact.verification_status == "verified":
                verified.append(
                    VerifiedFactV2(
                        fact_id=fact.id,
                        document_id=document.id,
                        field_name=fact.field_name,
                        normalized_value=fact.normalized_value,
                        unit=fact.unit,
                        corrected_from_fact_id=fact.corrected_from_fact_id,
                    )
                )
    if len(verified) > MAX_FACTS:
        raise _invalid("Verified fact projection exceeds the F2 evidence bound.")
    verified_rows = tuple(sorted(verified, key=lambda item: (item.document_id, item.fact_id)))

    # Read the same SQLite snapshot, not an external caller-crafted list.
    provenance = load_readonly_provenance_evidence(
        db, principal=principal, patient_id=run.patient_id, as_of_utc=run_clock
    )
    if len(provenance.records) > MAX_HISTORY_OBSERVATIONS:
        raise _invalid("Scoped history exceeds the F2 evidence bound.")
    by_id = {record.observation.id: record for record in provenance.records}
    if len(by_id) != len(provenance.records):
        raise _invalid("Duplicate observation records in scope.")
    doc_set = set(document_ids)
    current_set = set(observation_ids)

    def source_reason(entry) -> str | None:
        if entry.source == "verified_document":
            if (
                entry.source_fact_verification_status != "verified"
                or not entry.source_fact_id
                or entry.source_document_id not in doc_set
                or entry.observation.trust_level != "doctor_verified"
            ):
                return "verified_lineage_unavailable"
            source_fact = db.get(ExtractedFact, entry.source_fact_id)
            if (
                source_fact is None
                or source_fact.patient_id != run.patient_id
                or source_fact.document_id != entry.source_document_id
                or source_fact.field_name != "value"
                or source_fact.verification_status != "verified"
            ):
                return "verified_lineage_unavailable"
            # Both systolic and diastolic use mmHg: a matching unit/value
            # alone cannot establish the correct measurement identity.
            names = list(
                db.execute(
                    select(ExtractedFact)
                    .where(
                        ExtractedFact.document_id == entry.source_document_id,
                        ExtractedFact.field_name == "test_name",
                        ExtractedFact.verification_status == "verified",
                    )
                    .limit(2)
                ).scalars()
            )
            if len(names) != 1 or not names[0].normalized_value:
                return "verified_mapping_unproven"
            alias = " ".join(names[0].normalized_value.lower().strip().rstrip(":").split())
            mapped = MAPPING_TABLE.get(alias)
            if (
                mapped is None
                or mapped[0].value != entry.observation.measure_type
                or mapped[1].value != entry.observation.unit
                or mapped[1].value != source_fact.unit
            ):
                return "verified_mapping_unproven"
        elif entry.source in {"patient_checkin", "seed_fixture"}:
            if (
                entry.observation.trust_level != "self_reported_validated"
                or entry.source_fact_id is not None
            ):
                return "stored_trust_source_mismatch"
        else:
            return "stored_trust_source_mismatch"
        return None

    current: list[ObservationSnapshot] = []
    projected_current: list[ObservationV2] = []
    excluded: list[EvidenceExclusionV2] = []
    for selected in selected_obs:
        entry = by_id.get(selected.observation_id)
        if entry is None:
            raise _invalid("Selected current observation is not in the patient-scoped history.")
        row = entry.observation
        if source_reason(entry):
            raise _invalid("Selected observation has invalid recorded provenance.")
        if (
            selected.trust_level != row.trust_level
            or selected.source_fact_id != entry.source_fact_id
            or selected.observation_created_at != entry.created_at
        ):
            raise _invalid("Selected observation manifest changed.")
        try:
            why = admissibility_reason(row, patient_id=run.patient_id, as_of_utc=run_clock)
        except MonitoringInputError:
            raise _invalid("Selected current observation is malformed.") from None
        if why is not None:
            raise _invalid("Selected current observation is inadmissible.")
        try:
            measured = format_utc(parse_utc(row.measured_at))
        except (TypeError, ValueError, AttributeError):
            raise _invalid("Invalid selected current observation clock.") from None
        projected_current.append(
            ObservationV2(
                observation_id=row.id,
                patient_id=run.patient_id,
                measure_type=row.measure_type,
                value=_number(row.value),
                unit=row.unit,
                measured_at=measured,
                source=entry.source,
                trust_level=row.trust_level,
                source_fact_id=entry.source_fact_id,
                source_document_id=entry.source_document_id,
            )
        )
        current.append(row)

    history: list[ObservationSnapshot] = []
    for observation_id in sorted(by_id):
        if observation_id in current_set:
            continue
        entry = by_id[observation_id]
        reason = source_reason(entry)
        if reason is None:
            try:
                reason = admissibility_reason(
                    entry.observation, patient_id=run.patient_id, as_of_utc=run_clock
                )
            except MonitoringInputError:
                reason = "malformed_history"
        if reason is not None:
            excluded.append(EvidenceExclusionV2(observation_id, reason))
        else:
            history.append(entry.observation)

    if not current:
        comparisons: tuple[ComparisonV2, ...] = ()
        no_current_reason = "no_current_selected"
    else:
        try:
            compared = compare_explicit_current_with_history(
                current=tuple(current),
                history=tuple(history),
                patient_id=run.patient_id,
                as_of_utc=run_clock,
                baseline_lookback_days=HISTORY_LOOKBACK_DAYS,
            )
        except MonitoringInputError:
            raise _invalid("Deterministic observation comparison is not available.") from None
        if compared.excluded_history:
            raise _invalid("Unreported history exclusion would weaken V2 provenance.")
        comparisons = tuple(
            ComparisonV2(
                current_observation_id=item.current_observation_id,
                baseline_observation_id=item.baseline_observation_id,
                measure_type=item.measure_type,
                unit=item.unit,
                comparable=item.comparable,
                delta=item.delta,
                incomparable_reason=(
                    "no_baseline" if item.incomparable_reason == "missing_baseline" else None
                ),
                trust_basis=item.trust_basis,
            )
            for item in compared.comparisons
        )
        no_current_reason = None

    # Re-read and re-hash every selected byte against the authoritative F1
    # fingerprint as close as possible to completion. Filesystem and DB are
    # not jointly transactional; future runtime consumers must repeat checks.
    final_gate = inspect_current_run_gate_locked(
        db,
        principal=principal,
        run_id=run_id,
        at=validation_clock,
        upload_root=upload_root,
    )
    if (
        final_gate.input_fingerprint_sha256 != gate.input_fingerprint_sha256
        or final_gate.decision != gate.decision
        or final_gate.historical_excluded_vi002_ids != gate.historical_excluded_vi002_ids
    ):
        raise _invalid("Source evidence changed during the F2 projection.")

    projected_current_rows = tuple(sorted(projected_current, key=lambda item: item.observation_id))
    exclusions = tuple(sorted(excluded, key=lambda item: (item.observation_id, item.reason_code)))
    fingerprint = _canonical_digest(
        {
            "contract": CONTRACT_VERSION,
            "history_policy": COMPARISON_HISTORY_VERSION,
            "gate": [stored_gate.id, gate.gate_version, gate.input_fingerprint_sha256],
            "run": [
                run.id,
                run.patient_id,
                run.doctor_id,
                run.as_of_utc,
                run.workflow_version,
                run.state_schema_version,
                run.mapping_version,
                run.policy_version,
            ],
            "documents": document_ids,
            "selected": observation_ids,
            "facts": [
                [
                    item.fact_id,
                    item.document_id,
                    item.field_name,
                    item.normalized_value,
                    item.unit,
                    item.corrected_from_fact_id,
                ]
                for item in verified_rows
            ],
            "observations": [
                [
                    item.observation_id,
                    str(item.value),
                    item.measured_at,
                    item.measure_type,
                    item.unit,
                    item.trust_level,
                    item.source,
                    item.source_fact_id,
                    item.source_document_id,
                ]
                for item in projected_current_rows
            ],
            "comparisons": [
                [
                    item.current_observation_id,
                    item.baseline_observation_id,
                    item.comparable,
                    str(item.delta) if item.delta is not None else None,
                    item.trust_basis,
                    item.incomparable_reason,
                ]
                for item in comparisons
            ],
            "history_exclusions": [[item.observation_id, item.reason_code] for item in exclusions],
            "historical_issues": gate.historical_excluded_vi002_ids,
        }
    )
    return EvaluableReviewEvidenceV2(
        contract_version="2.0.0",
        run_id=run.id,
        patient_id=run.patient_id,
        doctor_id=run.doctor_id,
        as_of_utc=run.as_of_utc,
        workflow_version=run.workflow_version,
        state_schema_version=run.state_schema_version,
        mapping_version=run.mapping_version,
        policy_version=run.policy_version,
        gate_evaluation_id=stored_gate.id,
        gate_version=gate.gate_version,
        gate_input_fingerprint_sha256=gate.input_fingerprint_sha256,
        bridge_input_fingerprint_sha256=fingerprint,
        selected_document_ids=document_ids,
        selected_observation_ids=observation_ids,
        historical_excluded_vi002_ids=gate.historical_excluded_vi002_ids,
        verified_facts=verified_rows,
        selected_observations=projected_current_rows,
        comparisons=comparisons,
        history_exclusions=exclusions,
        no_current_reason=no_current_reason,
    )


def build_run_evaluable_review_evidence(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
) -> EvaluableReviewEvidenceV2:
    """Produce a read-only synthetic V2 contract; NEVER a graph or DR token.

    The caller supplies identifiers for one persisted run only. BEGIN IMMEDIATE
    protects SQLite rows from concurrent writes; no new F1 evaluation, audit,
    review item, source correction or graph event is written. Always ROLLBACK.
    """
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "Authenticated doctor required.")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ApiError(400, ErrorCode.VALIDATION, "Run identifier required.")
    if not isinstance(upload_root, str) or not upload_root:
        raise ApiError(400, ErrorCode.VALIDATION, "Trusted local source root required.")
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A fresh clean Session is required.")
    try:
        clock = to_utc(validation_clock)
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except (ValueError, TypeError, AttributeError):
        db.rollback()
        raise ApiError(400, ErrorCode.VALIDATION, "Aware validation clock required.") from None
    except OperationalError:
        db.rollback()
        raise ApiError(503, ErrorCode.VALIDATION, "Verification database is unavailable.") from None

    try:
        return _projection(
            db,
            principal=principal,
            run_id=run_id,
            validation_clock=clock,
            upload_root=upload_root,
        )
    finally:
        # Even a successful F2 read is never an implicit SQLite commit.
        db.rollback()


__all__ = ["CONTRACT_VERSION", "build_run_evaluable_review_evidence"]
