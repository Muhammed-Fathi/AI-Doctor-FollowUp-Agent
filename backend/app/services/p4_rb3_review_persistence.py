"""P4-RB3: internal, authenticated, run-bound durable review persistence.

Honest non-atomicity scope (§3.1):
    * SQLite cannot transact with filesystem bytes; ``BEGIN IMMEDIATE`` locks
      only the database. Re-hashing selected bytes at T3 and T17 narrows but
      does not close a filesystem race occurring between T17 and T18.
    * Phase 1 (P1-P6) runs read-only F2 and RB1 pins; each owns and rolls back
      its own SQLite lock and is never shared with Phase 2.
    * Phase 2 (T1-T18) owns a single committing ``BEGIN IMMEDIATE`` write
      transaction. Every denial raises inside the transaction and rolls back
      with zero writes.

No HTTP router, agent tool, graph node, task, notification, clinical claim, or
policy activation is created here.
EDUCATIONAL / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc, to_utc
from app.core.enums import MAPPING_TABLE, MAPPING_VERSION, AuditOutcome, Role
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_assigned_patient, require_doctor
from app.db.models import (
    AuditEvent,
    Document,
    EvidenceLink,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    ReviewEvaluation,
    ReviewItem,
    RunGateEvaluation,
    RunSelectedDocument,
    RunSelectedObservation,
    RunSourceOmission,
    User,
    UserSession,
    WorkflowRun,
    new_uuid,
)
from app.schemas.p4_rb2_offline_rules import (
    OfflineObservation,
    OfflineRuleError,
    OfflineRuleInput,
    OfflineRulePolicy,
)
from app.schemas.p4_rb3_review_persistence import (
    LayeredEvidenceExclusionsV1,
    PersistedEvidenceExclusionV1,
    RB3DenialReason,
    ReviewPersistenceReceiptV1,
)
from app.services.audit import SAFE_DETAIL_MAX, append_audit_event, derive_audit_key, safe_detail
from app.services.demo_policy import DemoPolicyCandidate, DemoPolicyError, validate_demo_policy
from app.services.documents import storage
from app.services.monitoring import MonitoringInputError, ObservationSnapshot, admissibility_reason
from app.services.p4_explicit_history import (
    ExplicitCurrentComparison,
    compare_explicit_current_with_history,
)
from app.services.p4_rb2_offline_rules import evaluate_p4_rb2_offline_fixture
from app.services.p4_readonly_provenance import MAX_OFFLINE_ROWS, load_readonly_provenance_evidence
from app.services.p4_run_bound_preview import build_p4_run_bound_review_input_preview
from app.services.p5_evidence_bridge import CONTRACT_VERSION, build_run_evaluable_review_evidence
from app.services.p5_run_foundation import (
    POLICY_REFERENCE_VERSION,
    STATE_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)
from app.services.p5_run_gate import GATE_VERSION, inspect_current_run_gate_locked

RB3_RECEIPT_CONTRACT_VERSION: Literal["p4-rb3-receipt-1.0.0"] = "p4-rb3-receipt-1.0.0"
RB3_FINGERPRINT_VERSION = "rb3-full-input-1.0.0"
RB3_AUDIT_EVENT_TYPE = "workflow.review.persisted"
RB3_LINEAGE_LABEL_POLICY: Literal["a2_transport_label"] = "a2_transport_label"
RB3_DR006_POLICY: Literal["prohibited_denied"] = "prohibited_denied"
RB3_POLICY_VERSION = "demo-policy-1.1.0"
RB3_PINNED_AS_OF_UTC = "2026-11-14T12:00:00Z"
RB3_PINNED_POLICY_SHA256 = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
RB3_NOTICE = "DEMO review prompts only — not clinical risk assessment. Not for clinical use."
RB3_EXPECTED_RULES = ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
RB3_EXPECTED_VI_ISSUES = ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")
RB3_AUDIT_DETAIL_KEYS: tuple[str, ...] = (
    "fingerprint_version",
    "evaluation_id",
    "input",
    "output",
    "lineage_label_policy",
    "dr006_policy",
    "items",
    "links",
    "exclusions",
)

SUPPORTED_MIN_MEASURED_AT = datetime(2, 1, 1, 0, 0, 0, tzinfo=UTC)
MAX_SELECTED_DOCUMENTS = 5
MAX_SELECTED_CURRENT = 6
MAX_MANIFEST_OBSERVATIONS = 20
MAX_MANIFEST_OMISSIONS = 20
MAX_SELECTED_FACTS = 40
MAX_PERSISTED_ITEMS = 12
MAX_PERSISTED_LINKS = 24
MAX_EXCLUSIONS = 200

_L0_COVERING_L1_REASONS = frozenset(
    {
        "verified_lineage_unavailable",
        "verified_mapping_unproven",
        "stored_trust_source_mismatch",
    }
)

# Default-equivalent Decimal context: protects 90-day and DR-005 arithmetic from
# ambient caller precision leaks without imposing RB2's Inexact trap upstream.
_RB3_ARITHMETIC_CONTEXT = Context(
    prec=28,
    rounding=ROUND_HALF_EVEN,
    Emin=-999999,
    Emax=999999,
    capitals=1,
    clamp=0,
    flags=[],
    traps=[InvalidOperation, DivisionByZero, Overflow],
)


def _deny(message: str) -> ApiError:
    return ApiError(409, ErrorCode.VALIDATION, message)


def _conflict(reason: RB3DenialReason | str) -> ApiError:
    value = reason.value if isinstance(reason, RB3DenialReason) else reason
    return ApiError(409, ErrorCode.IDEMPOTENCY_CONFLICT, value)


def _canonical_sha(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rehash_document_bytes(doc: Document, upload_root: str) -> str:
    try:
        path = storage.resolve_for_read(doc.stored_path, upload_dir=upload_root)
        content = path.read_bytes()
    except (FileNotFoundError, OSError, ValueError):
        raise _deny("Selected source bytes are unavailable.") from None
    if len(content) != doc.size_bytes:
        raise _deny("Selected source byte length changed.")
    digest = hashlib.sha256(content).hexdigest()
    if digest != doc.sha256:
        raise _deny("Selected source bytes do not match stored digest.")
    return digest


def _validated_pinned_policy() -> DemoPolicyCandidate:
    raw: dict[str, object] = {
        "policy_version": RB3_POLICY_VERSION,
        "demo_only": True,
        "demo_as_of_utc": RB3_PINNED_AS_OF_UTC,
        "notice": RB3_NOTICE,
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
        "verification_issues": [{"id": key, "enabled": True} for key in RB3_EXPECTED_VI_ISSUES],
        "rules": [{"id": key, "enabled": True} for key in RB3_EXPECTED_RULES],
    }
    try:
        candidate = validate_demo_policy(raw)
    except DemoPolicyError:
        raise _deny("Pinned synthetic comparison policy reference is invalid.") from None
    if (
        candidate.policy_version != RB3_POLICY_VERSION
        or format_utc(candidate.demo_as_of_utc) != RB3_PINNED_AS_OF_UTC
        or candidate.baseline_lookback_days != 90
        or candidate.stale_measurement_days != 30
        or candidate.demo_delta_systolic_mmHg != Decimal("10")
        or candidate.demo_delta_diastolic_mmHg != Decimal("8")
        or candidate.demo_delta_heart_rate_bpm != Decimal("15")
        or candidate.demo_delta_glucose_mgdl != Decimal("40")
        or candidate.ocr_confidence_floor != Decimal("0.70")
        or candidate.conflict_tolerance != Decimal("0")
        or candidate.max_items_per_type != 3
        or candidate.enabled_rules != RB3_EXPECTED_RULES
        or candidate.disabled_rules
        or candidate.enabled_verification_issues != RB3_EXPECTED_VI_ISSUES
        or candidate.disabled_verification_issues
    ):
        raise _deny("Pinned synthetic comparison policy reference drifted.")
    return candidate


def _l1_source_reason(
    db: Session,
    *,
    entry: object,
    patient_id: str,
    doc_set: set[str],
) -> str | None:
    """Reproduce F2's source_reason contract and precedence via public queries."""
    source = getattr(entry, "source", None)
    obs = getattr(entry, "observation", None)
    if obs is None:
        return "stored_trust_source_mismatch"
    source_fact_id = getattr(entry, "source_fact_id", None)
    source_document_id = getattr(entry, "source_document_id", None)
    source_fact_status = getattr(entry, "source_fact_verification_status", None)

    if source == "verified_document":
        if (
            source_fact_status != "verified"
            or not isinstance(source_fact_id, str)
            or not source_fact_id
            or source_document_id not in doc_set
            or obs.trust_level != "doctor_verified"
        ):
            return "verified_lineage_unavailable"
        source_fact = db.get(ExtractedFact, source_fact_id)
        if (
            source_fact is None
            or source_fact.patient_id != patient_id
            or source_fact.document_id != source_document_id
            or source_fact.field_name != "value"
            or source_fact.verification_status != "verified"
        ):
            return "verified_lineage_unavailable"
        names = list(
            db.execute(
                select(ExtractedFact)
                .where(
                    ExtractedFact.document_id == source_document_id,
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
            or mapped[0].value != obs.measure_type
            or mapped[1].value != obs.unit
            or mapped[1].value != source_fact.unit
        ):
            return "verified_mapping_unproven"
        return None
    if source in {"patient_checkin", "seed_fixture"}:
        if obs.trust_level != "self_reported_validated" or source_fact_id is not None:
            return "stored_trust_source_mismatch"
        return None
    return "stored_trust_source_mismatch"


def _compute_input_identity(
    *,
    run: WorkflowRun,
    patient: Patient,
    stored_gate: RunGateEvaluation,
    receipt_gate_version: str,
    receipt_gate_fingerprint: str,
    receipt_gate_decision: str,
    receipt_gate_blocking_count: int,
    receipt_gate_vi002_ids: tuple[str, ...],
    bridge_fingerprint: str,
    rb1_contract_version: str,
    policy: DemoPolicyCandidate,
    clock: datetime,
    selected_docs_manifest: tuple[RunSelectedDocument, ...],
    selected_obs_manifest: tuple[RunSelectedObservation, ...],
    omissions_manifest: tuple[RunSourceOmission, ...],
    docs_by_id: dict[str, Document],
    file_hashes: dict[str, str],
    obs_rows_by_id: dict[str, Observation],
    selected_current_ids: tuple[str, ...],
    eligible_history_ids: tuple[str, ...],
    l1_exclusions: tuple[PersistedEvidenceExclusionV1, ...],
    l0_checks: tuple[PersistedEvidenceExclusionV1, ...],
    proved_by_obs: dict[str, bool],
    provenance_by_obs: dict[str, object],
    all_facts: tuple[ExtractedFact, ...],
    all_decisions: tuple[FactVerification, ...],
    active_statuses: tuple[str, ...],
    comparisons_90d: tuple[ExplicitCurrentComparison, ...],
    rule_input: OfflineRuleInput,
) -> str:
    """Compute rb3-full-input-1.0.0 over the constructed T9 input and stored proofs."""
    current_set = set(selected_current_ids)
    history_obs_ids = sorted(obs_id for obs_id in obs_rows_by_id if obs_id not in current_set)

    def _obs_fields(obs: Observation) -> list[object]:
        return [
            obs.id,
            obs.patient_id,
            obs.measure_type,
            str(Decimal(str(obs.value))),
            obs.unit,
            obs.measured_at,
            obs.validation,
            obs.trust_level,
            obs.source,
            obs.source_fact_id,
            obs.verified_by_user_id,
            obs.verified_at,
            obs.created_at,
            obs.encounter_id,
            obs.created_by_user_id,
        ]

    payload: dict[str, object] = {
        "fingerprint_version": RB3_FINGERPRINT_VERSION,
        "contracts": {
            "f1_gate": GATE_VERSION,
            "f2_bridge": CONTRACT_VERSION,
            "rb1_preview": rb1_contract_version,
            "mapping": MAPPING_VERSION,
            "workflow": run.workflow_version,
            "state_schema": run.state_schema_version,
        },
        "run": [
            run.id,
            run.patient_id,
            run.doctor_id,
            run.status,
            run.as_of_utc,
            run.mapping_version,
            run.policy_version,
            run.workflow_version,
            run.state_schema_version,
            run.idempotency_key,
            run.started_at,
            run.updated_at,
            run.current_node,
            run.halt_reason,
            run.checkpoint_ref,
            patient.assigned_doctor_id,
        ],
        "gate": [
            stored_gate.id,
            receipt_gate_version,
            receipt_gate_fingerprint,
            receipt_gate_decision,
            receipt_gate_blocking_count,
            sorted(receipt_gate_vi002_ids),
        ],
        "bridge": [bridge_fingerprint],
        "policy": [
            policy.policy_version,
            RB3_PINNED_POLICY_SHA256,
            policy.baseline_lookback_days,
            policy.stale_measurement_days,
            str(policy.demo_delta_systolic_mmHg),
            str(policy.demo_delta_diastolic_mmHg),
            str(policy.demo_delta_heart_rate_bpm),
            str(policy.demo_delta_glucose_mgdl),
            str(policy.ocr_confidence_floor),
            str(policy.conflict_tolerance),
            policy.max_items_per_type,
            list(policy.enabled_rules),
            list(policy.enabled_verification_issues),
        ],
        "clock": [format_utc(clock), run.as_of_utc],
        "manifest": {
            "selected_documents": [
                [
                    m.id,
                    m.workflow_run_id,
                    m.document_id,
                    m.source_sha256,
                    m.source_status,
                    m.created_at,
                ]
                for m in selected_docs_manifest
            ],
            "selected_observations": [
                [
                    m.id,
                    m.workflow_run_id,
                    m.observation_id,
                    m.observation_created_at,
                    m.trust_level,
                    m.source_fact_id,
                    m.created_at,
                ]
                for m in selected_obs_manifest
            ],
            "omissions": [
                [
                    m.id,
                    m.workflow_run_id,
                    m.document_id,
                    m.vi002_issue_id,
                    m.doctor_id,
                    m.reason_code,
                    m.source_sha256,
                    m.created_at,
                ]
                for m in omissions_manifest
            ],
        },
        "selected_documents": [
            [
                docs_by_id[doc_id].id,
                docs_by_id[doc_id].patient_id,
                docs_by_id[doc_id].stored_path,
                docs_by_id[doc_id].mime_type,
                docs_by_id[doc_id].page_count,
                docs_by_id[doc_id].uploaded_at,
                docs_by_id[doc_id].document_patient_ref,
                docs_by_id[doc_id].document_patient_refs,
                docs_by_id[doc_id].extraction_status,
                docs_by_id[doc_id].failure_code,
                docs_by_id[doc_id].recovered_from_document_id,
                docs_by_id[doc_id].sha256,
                docs_by_id[doc_id].size_bytes,
            ]
            for doc_id in sorted(docs_by_id)
        ],
        "source_byte_digests": [[doc_id, file_hashes[doc_id]] for doc_id in sorted(file_hashes)],
        "selected_observations": [
            _obs_fields(obs_rows_by_id[obs_id]) for obs_id in selected_current_ids
        ],
        "history_observations": [_obs_fields(obs_rows_by_id[obs_id]) for obs_id in history_obs_ids],
        "eligible_history_ids": [[obs_id] for obs_id in eligible_history_ids],
        "selected_current_ids": [[obs_id] for obs_id in selected_current_ids],
        "l1_exclusions": [[e.observation_id, e.reason_code] for e in l1_exclusions],
        "l0_lineage_checks": [[e.observation_id, e.reason_code] for e in l0_checks],
        "lineage_proofs": [
            [
                obs_id,
                proved_by_obs[obs_id],
                getattr(provenance_by_obs[obs_id], "source_document_id", None),
                getattr(provenance_by_obs[obs_id], "source_fact_id", None),
                getattr(provenance_by_obs[obs_id], "source_fact_verification_status", None),
                obs_rows_by_id[obs_id].verified_by_user_id,
                obs_rows_by_id[obs_id].verified_at,
            ]
            for obs_id in sorted(obs_rows_by_id)
        ],
        "verified_facts": [
            [
                f.id,
                f.document_id,
                f.patient_id,
                f.field_name,
                f.page_index,
                f.char_start,
                f.char_end,
                f.created_at,
                f.normalized_value,
                f.unit,
                f.verification_status,
                f.corrected_from_fact_id,
                f.quality_flags,
                f.confidence,
                f.extractor,
            ]
            for f in all_facts
        ],
        "verification_decisions": [
            [
                d.id,
                d.fact_id,
                d.decision,
                d.previous_value,
                d.new_value,
                d.new_unit,
                d.confirmed_value,
                d.confirmed_unit,
                d.verified_by_user_id,
                d.decided_at,
                d.source_image_compared,
            ]
            for d in all_decisions
        ],
        "active_fact_verification_statuses": list(active_statuses),
        "comparisons_90d": [
            [
                c.current_observation_id,
                c.baseline_observation_id,
                c.measure_type,
                c.unit,
                c.comparable,
                str(c.delta) if c.delta is not None else None,
                c.incomparable_reason,
                c.skip_reason,
                c.trust_basis,
            ]
            for c in comparisons_90d
        ],
        "evaluator_input_shape": {
            "selected_current_count": len(rule_input.selected_current),
            "history_count": len(rule_input.history),
            "as_of_utc": format_utc(clock),
            "policy_version": rule_input.policy.policy_version,
            "policy_reference_sha256": RB3_PINNED_POLICY_SHA256,
            "active_fact_status_count": len(rule_input.active_fact_verification_statuses),
        },
    }
    return _canonical_sha(payload)


def _link_sort_key(
    kind: str,
    observation_id: str | None,
    document_id: str | None,
    page_index: int | None,
    char_start: int | None,
    char_end: int | None,
) -> tuple[str, str, str, int, int, int]:
    return (
        kind,
        observation_id or "",
        document_id or "",
        page_index if page_index is not None else -1,
        char_start if char_start is not None else -1,
        char_end if char_end is not None else -1,
    )


def _compute_output_identity(
    *,
    items_with_links: list[
        tuple[
            int,
            str,
            str,
            str,
            str,
            str,
            str,
            str,
            str,
            str,
            int,
            list[tuple[str, str | None, str | None, int | None, int | None, int | None]],
        ]
    ],
    l2_exclusions: tuple[PersistedEvidenceExclusionV1, ...],
) -> str:
    total_links = sum(len(entry[11]) for entry in items_with_links)
    payload: dict[str, object] = {
        "items": [
            [
                display_order,
                rule_id,
                reason_code,
                workflow_hint,
                trust_basis,
                message,
                policy_version,
                dedupe_key,
                state,
                provenance_status,
                stored_lineage_proved,
                [
                    [kind, doc_id, obs_id, page_idx, c_start, c_end]
                    for kind, doc_id, obs_id, page_idx, c_start, c_end in sorted(
                        links,
                        key=lambda row: _link_sort_key(
                            row[0], row[2], row[1], row[3], row[4], row[5]
                        ),
                    )
                ],
            ]
            for (
                display_order,
                rule_id,
                reason_code,
                workflow_hint,
                trust_basis,
                message,
                policy_version,
                dedupe_key,
                state,
                provenance_status,
                stored_lineage_proved,
                links,
            ) in items_with_links
        ],
        "item_count": len(items_with_links),
        "evidence_link_count": total_links,
        "lineage_label_policy": RB3_LINEAGE_LABEL_POLICY,
        "dr006_policy": RB3_DR006_POLICY,
        "l2_exclusions": [[e.observation_id, e.reason_code] for e in l2_exclusions],
        "span_proofs": [],
    }
    return _canonical_sha(payload)


def _compose_audit_fragments(
    *,
    evaluation_id: str,
    input_fingerprint_sha256: str,
    output_identity_sha256: str,
    item_count: int,
    evidence_link_count: int,
    exclusion_count: int,
) -> tuple[tuple[str, ...], str]:
    fragments = (
        f"fingerprint_version={RB3_FINGERPRINT_VERSION}",
        f"evaluation_id={evaluation_id}",
        f"input={input_fingerprint_sha256}",
        f"output={output_identity_sha256}",
        f"lineage_label_policy={RB3_LINEAGE_LABEL_POLICY}",
        f"dr006_policy={RB3_DR006_POLICY}",
        f"items={item_count}",
        f"links={evidence_link_count}",
        f"exclusions={exclusion_count}",
    )
    composed = safe_detail(*fragments)
    joined = "; ".join(f.strip() for f in fragments if f and f.strip())
    collapsed = " ".join(joined.split())
    if len(composed) > SAFE_DETAIL_MAX or composed != collapsed:
        raise _deny("Audit detail exceeded safe_detail length contract.")
    if tuple(part.split("=", 1)[0] for part in composed.split("; ")) != RB3_AUDIT_DETAIL_KEYS:
        raise _deny("Audit detail keys do not match contract.")
    return fragments, composed


def _parse_and_verify_audit_detail(
    stored_detail: str | None,
    *,
    expected_evaluation_id: str,
    expected_input_sha: str,
    expected_output_sha: str,
    expected_item_count: int,
    expected_link_count: int,
    expected_exclusion_count: int,
) -> bool:
    if not stored_detail or len(stored_detail) > SAFE_DETAIL_MAX:
        return False
    parts = stored_detail.split("; ")
    if len(parts) != len(RB3_AUDIT_DETAIL_KEYS):
        return False
    parsed_keys: list[str] = []
    parsed_map: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            return False
        key, val = part.split("=", 1)
        if key in parsed_map:
            return False
        parsed_keys.append(key)
        parsed_map[key] = val
    if tuple(parsed_keys) != RB3_AUDIT_DETAIL_KEYS:
        return False
    expected_map = {
        "fingerprint_version": RB3_FINGERPRINT_VERSION,
        "evaluation_id": expected_evaluation_id,
        "input": expected_input_sha,
        "output": expected_output_sha,
        "lineage_label_policy": RB3_LINEAGE_LABEL_POLICY,
        "dr006_policy": RB3_DR006_POLICY,
        "items": str(expected_item_count),
        "links": str(expected_link_count),
        "exclusions": str(expected_exclusion_count),
    }
    return parsed_map == expected_map


def persist_run_review_items(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
) -> ReviewPersistenceReceiptV1:
    """Verify, evaluate, and durably persist RB3 demo review items for one queued run."""
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "Authenticated doctor required.")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ApiError(400, ErrorCode.VALIDATION, "Run identifier required.")
    if not isinstance(upload_root, str) or not upload_root:
        raise ApiError(400, ErrorCode.VALIDATION, "Trusted local source root required.")
    try:
        clock = to_utc(validation_clock)
    except (TypeError, ValueError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "Aware validation clock required.") from None

    # --- Phase 1: read-only pins (P1-P6; helpers own & roll back their own locks) ---
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A fresh clean Session is required.")

    with localcontext(_RB3_ARITHMETIC_CONTEXT):
        return _persist_run_review_items_pinned(
            db,
            principal=principal,
            run_id=run_id,
            clock=clock,
            upload_root=upload_root,
        )


def _persist_run_review_items_pinned(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    clock: datetime,
    upload_root: str,
) -> ReviewPersistenceReceiptV1:
    """Execute Phase 1 and Phase 2 inside RB3's pinned Decimal context."""
    try:
        evidence = build_run_evaluable_review_evidence(
            db,
            principal=principal,
            run_id=run_id,
            validation_clock=clock,
            upload_root=upload_root,
        )
    except OverflowError:
        raise _deny(RB3DenialReason.MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE.value) from None

    try:
        preview = build_p4_run_bound_review_input_preview(
            db,
            principal=principal,
            run_id=run_id,
            validation_clock=clock,
            upload_root=upload_root,
        )
    except OverflowError:
        raise _deny(RB3DenialReason.MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE.value) from None

    # P4: frozen preview & F2 literals
    if (
        preview.contract_version != "p4-rb1-preview-1.0.0"
        or preview.policy_version != RB3_POLICY_VERSION
        or preview.policy_reference_sha256 != RB3_PINNED_POLICY_SHA256
        or preview.policy_baseline_lookback_days != 90
        or preview.as_of_utc != RB3_PINNED_AS_OF_UTC
        or preview.runtime_evaluable is not False
        or preview.rules_executed is not False
        or preview.policy_status != "unapproved"
        or preview.review_items_persisted is not False
        or evidence.contract_version != CONTRACT_VERSION
        or evidence.gate_version != GATE_VERSION
        or evidence.bridge_validated is not True
        or evidence.runtime_evaluable is not False
        or evidence.rules_executed is not False
        or evidence.policy_status != "unapproved"
    ):
        raise _deny("Phase-1 preview or F2 literals do not match pinned RB3 bounds.")

    # P5: clock agreement
    try:
        preview_clock = parse_utc(preview.as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise _deny("Invalid preview UTC clock.") from None
    if clock != preview_clock:
        raise _deny("Validation clock does not match pinned run clock.")

    # P6: cross-DTO agreement
    if (
        preview.run_id != evidence.run_id
        or preview.run_id != run_id
        or preview.patient_id != evidence.patient_id
        or preview.doctor_id != evidence.doctor_id
        or preview.as_of_utc != evidence.as_of_utc
        or preview.policy_version != evidence.policy_version
        or preview.gate_evaluation_id != evidence.gate_evaluation_id
        or preview.gate_input_fingerprint_sha256 != evidence.gate_input_fingerprint_sha256
        or preview.bridge_input_fingerprint_sha256 != evidence.bridge_input_fingerprint_sha256
        or preview.selected_document_ids != evidence.selected_document_ids
        or preview.selected_observation_ids != evidence.selected_observation_ids
        or preview.history_exclusions != evidence.history_exclusions
        or preview.verified_facts != evidence.verified_facts
        or preview.selected_observations != evidence.selected_observations
        or preview.no_current_reason != evidence.no_current_reason
    ):
        raise _deny("Phase-1 F2 and RB1 DTOs disagree.")

    # --- Phase 2: single committing write transaction (T1-T18) ---
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A fresh clean Session is required.")
    try:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except OperationalError:
        db.rollback()
        raise ApiError(503, ErrorCode.VALIDATION, "Verification database is unavailable.") from None
    if not db.in_transaction():
        db.rollback()
        raise _deny("Failed to acquire SQLite write lock.")

    try:
        # T2: re-prove §2.2 authorization chain from stored rows
        require_doctor(principal)
        run = db.get(WorkflowRun, run_id)
        if run is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, "Run is unavailable.")
        if run.doctor_id != principal.user_id:
            raise ApiError(403, ErrorCode.FORBIDDEN, "Run is unavailable to this doctor.")

        stored_session = db.execute(
            select(UserSession).where(
                UserSession.id == principal.session_id,
                UserSession.user_id == principal.user_id,
            )
        ).scalar_one_or_none()
        try:
            session_active = (
                stored_session is not None
                and stored_session.revoked_at is None
                and parse_utc(stored_session.created_at)
                <= clock
                < parse_utc(stored_session.expires_at)
            )
        except (TypeError, ValueError, AttributeError):
            session_active = False
        user = db.get(User, principal.user_id)
        if (
            not session_active
            or user is None
            or user.role != Role.DOCTOR.value
            or user.is_active != 1
        ):
            raise ApiError(403, ErrorCode.FORBIDDEN, "An active doctor session is required.")

        patient = db.get(Patient, run.patient_id)
        if (
            patient is None
            or patient.data_source != "synthetic_fixture"
            or patient.id != run.patient_id
        ):
            raise ApiError(403, ErrorCode.FORBIDDEN, "Synthetic patient scope is required.")
        require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)

        if run.status != "queued":
            raise _deny("Run is not queued for review persistence.")
        if (
            run.mapping_version != MAPPING_VERSION
            or run.workflow_version != WORKFLOW_VERSION
            or run.state_schema_version != STATE_SCHEMA_VERSION
            or run.policy_version != POLICY_REFERENCE_VERSION
            or any(
                value is not None
                for value in (run.current_node, run.halt_reason, run.checkpoint_ref)
            )
        ):
            raise _deny("Run version identity or execution state is invalid.")
        try:
            run_clock = parse_utc(run.as_of_utc)
        except (TypeError, ValueError, AttributeError):
            raise _deny("Invalid persisted run clock.") from None
        if run.as_of_utc != RB3_PINNED_AS_OF_UTC or run_clock != clock:
            raise _deny("Persisted run clock does not match pinned evaluation clock.")
        if run.patient_id != preview.patient_id or run.doctor_id != preview.doctor_id:
            raise _deny("Run scope differs from Phase-1 pin.")

        # T3: locked F1 revalidation
        receipt_gate = inspect_current_run_gate_locked(
            db,
            principal=principal,
            run_id=run.id,
            at=clock,
            upload_root=upload_root,
        )
        if (
            receipt_gate.decision != "proceed"
            or receipt_gate.blocking_fact_count != 0
            or receipt_gate.gate_version != GATE_VERSION
        ):
            raise _deny("Current F1 gate is not eligible.")

        stored_gate = db.execute(
            select(RunGateEvaluation).where(
                RunGateEvaluation.workflow_run_id == run.id,
                RunGateEvaluation.gate_version == GATE_VERSION,
                RunGateEvaluation.input_fingerprint_sha256 == receipt_gate.input_fingerprint_sha256,
                RunGateEvaluation.decision == "proceed",
            )
        ).scalar_one_or_none()
        if (
            stored_gate is None
            or stored_gate.id != preview.gate_evaluation_id
            or receipt_gate.input_fingerprint_sha256 != preview.gate_input_fingerprint_sha256
            or receipt_gate.gate_version != evidence.gate_version
        ):
            raise _deny("F1 gate identity changed since Phase-1 pin.")

        # T4: re-pin run and manifest
        selected_docs_manifest = tuple(
            db.execute(
                select(RunSelectedDocument)
                .where(RunSelectedDocument.workflow_run_id == run.id)
                .order_by(RunSelectedDocument.document_id)
            ).scalars()
        )
        selected_obs_manifest = tuple(
            db.execute(
                select(RunSelectedObservation)
                .where(RunSelectedObservation.workflow_run_id == run.id)
                .order_by(RunSelectedObservation.observation_id)
            ).scalars()
        )
        omissions_manifest = tuple(
            db.execute(
                select(RunSourceOmission)
                .where(RunSourceOmission.workflow_run_id == run.id)
                .order_by(RunSourceOmission.document_id)
            ).scalars()
        )
        if (
            not 1 <= len(selected_docs_manifest) <= MAX_SELECTED_DOCUMENTS
            or len(selected_obs_manifest) > MAX_MANIFEST_OBSERVATIONS
            or len(omissions_manifest) > MAX_MANIFEST_OMISSIONS
            or len(selected_obs_manifest) > MAX_SELECTED_CURRENT
        ):
            raise _deny("Run manifest bounds exceeded.")
        document_ids = tuple(item.document_id for item in selected_docs_manifest)
        observation_ids = tuple(item.observation_id for item in selected_obs_manifest)
        if len(set(document_ids)) != len(document_ids) or len(set(observation_ids)) != len(
            observation_ids
        ):
            raise _deny("Run manifest contains duplicate identifiers.")
        if (
            document_ids != evidence.selected_document_ids
            or observation_ids != evidence.selected_observation_ids
        ):
            raise _deny("Run manifest selection changed since Phase-1 pin.")

        docs_by_id: dict[str, Document] = {}
        file_hashes: dict[str, str] = {}
        for item in selected_docs_manifest:
            doc = db.get(Document, item.document_id)
            if doc is None:
                raise _deny("Selected document scope changed.")
            if doc.patient_id != run.patient_id:
                raise ApiError(
                    403, ErrorCode.SCOPE_VIOLATION, "Selected document belongs to another patient."
                )
            if (
                doc.sha256 != item.source_sha256
                or doc.extraction_status != item.source_status
                or doc.extraction_status != "verified"
                or doc.failure_code is not None
            ):
                raise _deny("Selected document state changed.")
            docs_by_id[doc.id] = doc
            file_hashes[doc.id] = _rehash_document_bytes(doc, upload_root)

        all_facts = tuple(
            db.execute(
                select(ExtractedFact)
                .where(ExtractedFact.document_id.in_(document_ids))
                .order_by(ExtractedFact.id)
                .limit(MAX_SELECTED_FACTS + 1)
            ).scalars()
        )
        if len(all_facts) > MAX_SELECTED_FACTS:
            raise _deny("Selected facts exceed bounded cap.")
        for fact in all_facts:
            if fact.patient_id != run.patient_id:
                raise ApiError(
                    403, ErrorCode.SCOPE_VIOLATION, "Selected fact belongs to another patient."
                )
        fact_ids = tuple(f.id for f in all_facts)
        all_decisions = (
            tuple(
                db.execute(
                    select(FactVerification)
                    .where(FactVerification.fact_id.in_(fact_ids))
                    .order_by(FactVerification.id)
                ).scalars()
            )
            if fact_ids
            else ()
        )

        # T5-T16 under RB3's default-equivalent pinned Decimal context (§4.7)
        with localcontext(_RB3_ARITHMETIC_CONTEXT):
            # T5: reconstruct complete authoritative stored snapshot
            obs_rows = tuple(
                db.execute(
                    select(Observation)
                    .where(Observation.patient_id == run.patient_id)
                    .order_by(Observation.id)
                    .limit(MAX_OFFLINE_ROWS + 1)
                ).scalars()
            )
            if len(obs_rows) > MAX_OFFLINE_ROWS:
                raise _deny("Too many scoped patient observations.")
            obs_rows_by_id = {row.id: row for row in obs_rows}

            provenance = load_readonly_provenance_evidence(
                db,
                principal=principal,
                patient_id=run.patient_id,
                as_of_utc=clock,
            )
            if len(provenance.records) > MAX_OFFLINE_ROWS or len(provenance.records) != len(
                obs_rows_by_id
            ):
                raise _deny("Scoped patient observation snapshot changed.")
            provenance_by_obs = {entry.observation.id: entry for entry in provenance.records}
            if len(provenance_by_obs) != len(provenance.records) or set(provenance_by_obs) != set(
                obs_rows_by_id
            ):
                raise _deny("Scoped observation snapshot mismatch.")

            l0_checks = tuple(
                sorted(
                    PersistedEvidenceExclusionV1(item.observation_id, item.reason)
                    for item in provenance.lineage_exclusions
                )
            )
            l0_excluded_ids = {item.observation_id for item in l0_checks}

            # T6: L1 exact F2-compatible eligibility/exclusion reconstruction
            doc_set = set(document_ids)
            current_set = set(observation_ids)
            l1_list: list[PersistedEvidenceExclusionV1] = []
            eligible_history_ids_list: list[str] = []
            eligible_history_snapshots: list[ObservationSnapshot] = []
            proved_by_obs: dict[str, bool] = {}

            for obs_id in sorted(provenance_by_obs):
                entry = provenance_by_obs[obs_id]
                obs_row = obs_rows_by_id[obs_id]
                src_reason = _l1_source_reason(
                    db, entry=entry, patient_id=run.patient_id, doc_set=doc_set
                )
                proved_by_obs[obs_id] = bool(
                    entry.source == "verified_document"
                    and obs_row.trust_level == "doctor_verified"
                    and obs_row.verified_by_user_id is not None
                    and obs_row.verified_at is not None
                    and entry.source_fact_id is not None
                    and entry.source_document_id is not None
                    and entry.source_fact_verification_status == "verified"
                    and obs_id not in l0_excluded_ids
                    and src_reason is None
                )
                if obs_id in current_set:
                    continue
                reason = src_reason
                if reason is None:
                    try:
                        reason = admissibility_reason(
                            entry.observation,
                            patient_id=run.patient_id,
                            as_of_utc=clock,
                        )
                    except MonitoringInputError:
                        reason = "malformed_history"
                if reason is not None:
                    l1_list.append(PersistedEvidenceExclusionV1(obs_id, reason))
                else:
                    eligible_history_ids_list.append(obs_id)
                    eligible_history_snapshots.append(entry.observation)

            l1_exclusions = tuple(sorted(l1_list))
            eligible_history_ids = tuple(eligible_history_ids_list)
            l1_by_obs = {item.observation_id: item.reason_code for item in l1_exclusions}

            # L0 consistency check (never merged into L1, never compared to cached F2)
            for check_item in l0_checks:
                if check_item.observation_id in current_set:
                    raise _deny(RB3DenialReason.STORED_LINEAGE_EVIDENCE_INCONSISTENT.value)
                l1_reason = l1_by_obs.get(check_item.observation_id)
                if l1_reason not in _L0_COVERING_L1_REASONS:
                    raise _deny(RB3DenialReason.STORED_LINEAGE_EVIDENCE_INCONSISTENT.value)

            # L1 drift cross-check against cached F2/RB1 sets (never authority)
            cached_f2 = tuple(
                sorted(
                    PersistedEvidenceExclusionV1(e.observation_id, e.reason_code)
                    for e in evidence.history_exclusions
                )
            )
            cached_rb1 = tuple(
                sorted(
                    PersistedEvidenceExclusionV1(e.observation_id, e.reason_code)
                    for e in preview.history_exclusions
                )
            )
            if l1_exclusions != cached_f2 or l1_exclusions != cached_rb1:
                raise _deny(RB3DenialReason.HISTORICAL_EXCLUSION_EVIDENCE_CHANGED.value)
            if set(l1_by_obs).intersection(current_set):
                raise _deny(RB3DenialReason.SELECTED_CURRENT_EVIDENCE_EXCLUDED.value)

            # T7: selected-current stored-value proof & §4.7 supported-domain preflight
            projected_by_id = {obs.observation_id: obs for obs in evidence.selected_observations}
            if len(projected_by_id) != len(observation_ids) or set(projected_by_id) != current_set:
                raise _deny("Selected observation projection mismatch.")

            selected_snapshots: list[ObservationSnapshot] = []
            for manifest_obs in selected_obs_manifest:
                obs_id = manifest_obs.observation_id
                entry = provenance_by_obs.get(obs_id)
                obs_row = obs_rows_by_id.get(obs_id)
                projected = projected_by_id.get(obs_id)
                if entry is None or obs_row is None or projected is None:
                    raise _deny("Selected current observation missing from stored scope.")
                if (
                    _l1_source_reason(db, entry=entry, patient_id=run.patient_id, doc_set=doc_set)
                    is not None
                ):
                    raise _deny("Selected observation has invalid recorded provenance.")
                if (
                    manifest_obs.trust_level != obs_row.trust_level
                    or manifest_obs.source_fact_id != entry.source_fact_id
                    or manifest_obs.observation_created_at != entry.created_at
                    or obs_row.created_at != entry.created_at
                ):
                    raise _deny("Selected observation manifest changed.")
                try:
                    obs_value = Decimal(str(obs_row.value))
                    obs_measured = parse_utc(obs_row.measured_at)
                    obs_measured_str = format_utc(obs_measured)
                except (InvalidOperation, TypeError, ValueError, AttributeError):
                    raise _deny("Selected current observation is malformed.") from None
                if (
                    obs_row.patient_id != run.patient_id
                    or obs_row.patient_id != projected.patient_id
                    or obs_row.measure_type != projected.measure_type
                    or obs_row.unit != projected.unit
                    or obs_value != projected.value
                    or obs_measured_str != projected.measured_at
                    or obs_row.trust_level != projected.trust_level
                    or entry.source != projected.source
                    or obs_row.source != projected.source
                    or entry.source_fact_id != projected.source_fact_id
                    or entry.source_document_id != projected.source_document_id
                ):
                    raise _deny("Selected observation stored values changed.")
                try:
                    why = admissibility_reason(
                        entry.observation,
                        patient_id=run.patient_id,
                        as_of_utc=clock,
                    )
                except MonitoringInputError:
                    raise _deny("Selected current observation is malformed.") from None
                if why is not None:
                    raise _deny("Selected current observation is inadmissible.")
                selected_snapshots.append(entry.observation)

            # §4.7 supported-domain preflight on every comparator row
            for snap in (*selected_snapshots, *eligible_history_snapshots):
                try:
                    stamp = parse_utc(cast(str, snap.measured_at))
                except (TypeError, ValueError, AttributeError):
                    raise _deny("Malformed measurement timestamp in supported domain.") from None
                if stamp < SUPPORTED_MIN_MEASURED_AT:
                    raise _deny(RB3DenialReason.MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE.value)

            # T8a / T8b: 90-day comparison pin
            if not selected_snapshots:
                if (
                    preview.no_current_reason != "no_current_selected"
                    or preview.policy_comparisons != ()
                    or evidence.comparisons != ()
                    or evidence.no_current_reason != "no_current_selected"
                ):
                    raise _deny("Zero-selection preview/F2 semantics mismatch.")
                comparisons_90d: tuple[ExplicitCurrentComparison, ...] = ()
            else:
                if preview.no_current_reason is not None or evidence.no_current_reason is not None:
                    raise _deny("Non-empty selection unexpected no_current_reason.")
                try:
                    compared = compare_explicit_current_with_history(
                        current=tuple(selected_snapshots),
                        history=tuple(eligible_history_snapshots),
                        patient_id=run.patient_id,
                        as_of_utc=clock,
                        baseline_lookback_days=90,
                    )
                except MonitoringInputError:
                    raise _deny("90-day comparison input is invalid.") from None
                except OverflowError:
                    raise _deny(
                        RB3DenialReason.MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE.value
                    ) from None
                if compared.excluded_history or len(compared.comparisons) != len(
                    selected_snapshots
                ):
                    raise _deny("90-day comparison produced unexpected exclusions or mismatch.")
                if len(compared.comparisons) != len(preview.policy_comparisons):
                    raise _deny("90-day comparison count differs from preview.")
                for comp_item, prev_item in zip(
                    compared.comparisons, preview.policy_comparisons, strict=True
                ):
                    mapped_reason = (
                        "no_baseline"
                        if comp_item.incomparable_reason == "missing_baseline"
                        else None
                    )
                    if (
                        comp_item.current_observation_id != prev_item.current_observation_id
                        or comp_item.baseline_observation_id != prev_item.baseline_observation_id
                        or comp_item.measure_type != prev_item.measure_type
                        or comp_item.unit != prev_item.unit
                        or comp_item.comparable != prev_item.comparable
                        or comp_item.delta != prev_item.delta
                        or mapped_reason != prev_item.incomparable_reason
                        or comp_item.trust_basis != prev_item.trust_basis
                    ):
                        raise _deny("90-day comparison differs from Phase-1 preview.")
                comparisons_90d = compared.comparisons

            # T9: construct exact typed OfflineRuleInput from stored rows
            policy_candidate = _validated_pinned_policy()
            if (
                policy_candidate.policy_version != preview.policy_version
                or preview.policy_reference_sha256 != RB3_PINNED_POLICY_SHA256
            ):
                raise _deny("Pinned policy differs from Phase-1 preview.")

            active_statuses_list: list[str] = []
            for doc_id in document_ids:
                doc_facts = [f for f in all_facts if f.document_id == doc_id]
                verified_corrections = {
                    f.corrected_from_fact_id
                    for f in doc_facts
                    if f.corrected_from_fact_id and f.verification_status == "verified"
                }
                active_facts = [f for f in doc_facts if f.id not in verified_corrections]
                active_statuses_list.extend(f.verification_status for f in active_facts)
            active_statuses = tuple(active_statuses_list)

            def _to_offline_observation(obs_id: str) -> OfflineObservation:
                entry = provenance_by_obs[obs_id]
                obs_row = obs_rows_by_id[obs_id]
                proved = proved_by_obs[obs_id]
                return OfflineObservation(
                    id=obs_row.id,
                    patient_id=obs_row.patient_id,
                    measure_type=obs_row.measure_type,
                    value=Decimal(str(obs_row.value)),
                    unit=obs_row.unit,
                    measured_at=obs_row.measured_at,
                    validation=obs_row.validation,
                    trust_level=obs_row.trust_level,
                    created_at=obs_row.created_at,
                    source=obs_row.source,
                    source_document_id=getattr(entry, "source_document_id", None),
                    source_fact_id=getattr(entry, "source_fact_id", None),
                    source_fact_verification_status=getattr(
                        entry, "source_fact_verification_status", None
                    ),
                    lineage_status="fixture_asserted" if proved else "unavailable",
                )

            rb2_policy = OfflineRulePolicy(
                policy_version=policy_candidate.policy_version,
                demo_only=True,
                demo_as_of_utc=policy_candidate.demo_as_of_utc,
                baseline_lookback_days=policy_candidate.baseline_lookback_days,
                stale_measurement_days=policy_candidate.stale_measurement_days,
                demo_delta_systolic_mmHg=policy_candidate.demo_delta_systolic_mmHg,
                demo_delta_diastolic_mmHg=policy_candidate.demo_delta_diastolic_mmHg,
                demo_delta_heart_rate_bpm=policy_candidate.demo_delta_heart_rate_bpm,
                demo_delta_glucose_mgdl=policy_candidate.demo_delta_glucose_mgdl,
                ocr_confidence_floor=policy_candidate.ocr_confidence_floor,
                conflict_tolerance=policy_candidate.conflict_tolerance,
                max_items_per_type=policy_candidate.max_items_per_type,
                enabled_verification_issues=policy_candidate.enabled_verification_issues,
                enabled_rules=policy_candidate.enabled_rules,
                notice=policy_candidate.notice,
            )
            rule_input = OfflineRuleInput(
                patient_id=run.patient_id,
                selected_current=tuple(_to_offline_observation(oid) for oid in observation_ids),
                history=tuple(_to_offline_observation(oid) for oid in eligible_history_ids),
                as_of_utc=clock,
                policy=rb2_policy,
                active_fact_verification_statuses=active_statuses,
            )

            # T10: compute complete canonical input identity over T9 input + stored proofs
            input_fingerprint_sha256 = _compute_input_identity(
                run=run,
                patient=patient,
                stored_gate=stored_gate,
                receipt_gate_version=receipt_gate.gate_version,
                receipt_gate_fingerprint=receipt_gate.input_fingerprint_sha256,
                receipt_gate_decision=receipt_gate.decision,
                receipt_gate_blocking_count=receipt_gate.blocking_fact_count,
                receipt_gate_vi002_ids=receipt_gate.historical_excluded_vi002_ids,
                bridge_fingerprint=evidence.bridge_input_fingerprint_sha256,
                rb1_contract_version=preview.contract_version,
                policy=policy_candidate,
                clock=clock,
                selected_docs_manifest=selected_docs_manifest,
                selected_obs_manifest=selected_obs_manifest,
                omissions_manifest=omissions_manifest,
                docs_by_id=docs_by_id,
                file_hashes=file_hashes,
                obs_rows_by_id=obs_rows_by_id,
                selected_current_ids=observation_ids,
                eligible_history_ids=eligible_history_ids,
                l1_exclusions=l1_exclusions,
                l0_checks=l0_checks,
                proved_by_obs=proved_by_obs,
                provenance_by_obs=provenance_by_obs,
                all_facts=all_facts,
                all_decisions=all_decisions,
                active_statuses=active_statuses,
                comparisons_90d=comparisons_90d,
                rule_input=rule_input,
            )

            # T11: invoke frozen RB2 evaluator
            try:
                rule_result = evaluate_p4_rb2_offline_fixture(rule_input)
            except OfflineRuleError as err:
                if err.code == "E_SCOPE_VIOLATION":
                    raise ApiError(403, ErrorCode.SCOPE_VIOLATION, f"{err.code}: {err}") from None
                raise _deny(f"{err.code}: {err}") from None

            if (
                rule_result.policy_version != RB3_POLICY_VERSION
                or rule_result.demo_only is not True
                or rule_result.offline_candidate_rules_evaluated is not True
                or rule_result.runtime_evaluable is not False
                or rule_result.rules_executed is not False
                or rule_result.review_items_persisted is not False
                or rule_result.policy_status != "unapproved"
            ):
                raise _deny("Evaluator result honesty literals drifted.")

            l2_exclusions = tuple(
                PersistedEvidenceExclusionV1(item.observation_id, item.reason)
                for item in rule_result.excluded
            )
            l3_merged = tuple(sorted(set(l1_exclusions) | set(l2_exclusions)))
            if len(l3_merged) > MAX_EXCLUSIONS:
                raise _deny("Exclusion count exceeds bounded design maximum.")

            # T12: conservative DR-006 gate
            if any(flag.rule_id == "DR-006" for flag in rule_result.flags):
                raise _deny(RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED.value)

            # T13: resolve and validate every permitted evidence reference
            allowed_obs_ids = current_set | set(eligible_history_ids)
            if len(rule_result.flags) > MAX_PERSISTED_ITEMS:
                raise _deny("Evaluator item count exceeds bounded design maximum.")

            prepared_items: list[
                tuple[
                    int,
                    str,
                    str,
                    str,
                    str,
                    str,
                    str,
                    str,
                    str,
                    str,
                    int,
                    list[tuple[str, str | None, str | None, int | None, int | None, int | None]],
                ]
            ] = []
            total_links = 0
            for display_order, flag in enumerate(rule_result.flags):
                if (
                    flag.provenance_status != "fixture_asserted"
                    or flag.policy_version != RB3_POLICY_VERSION
                    or flag.demo_only is not True
                    or not flag.evidence
                    or len(flag.evidence) > 2
                ):
                    raise _deny("Evaluator flag metadata or evidence shape invalid.")
                item_obs_ids: list[str] = []
                for ref in flag.evidence:
                    if not isinstance(ref, str) or not ref.startswith("observation:"):
                        raise _deny("Evidence is not resolvable to stored sources.")
                    ref_obs_id = ref.removeprefix("observation:")
                    obs_row = obs_rows_by_id.get(ref_obs_id)
                    if obs_row is None:
                        raise _deny("Evidence is not resolvable to stored sources.")
                    if obs_row.patient_id != run.patient_id:
                        raise ApiError(
                            403, ErrorCode.SCOPE_VIOLATION, "Evidence belongs to another patient."
                        )
                    if ref_obs_id not in allowed_obs_ids:
                        raise _deny("Evidence is not resolvable to stored sources.")
                    item_obs_ids.append(ref_obs_id)
                if len(set(item_obs_ids)) != len(item_obs_ids):
                    raise _deny("Duplicate observation reference within one flag.")
                stored_lineage_proved = 1 if all(proved_by_obs[oid] for oid in item_obs_ids) else 0
                links_for_item = [
                    ("observation", None, oid, None, None, None) for oid in sorted(item_obs_ids)
                ]
                total_links += len(links_for_item)
                prepared_items.append(
                    (
                        display_order,
                        flag.rule_id,
                        flag.reason_code,
                        flag.workflow_hint,
                        flag.trust_basis,
                        flag.message,
                        flag.policy_version,
                        flag.dedupe_key,
                        "open",
                        flag.provenance_status,
                        stored_lineage_proved,
                        links_for_item,
                    )
                )
            if total_links > MAX_PERSISTED_LINKS:
                raise _deny("Evidence link count exceeds bounded design maximum.")

            # T14: compute complete semantic output identity
            output_identity_sha256 = _compute_output_identity(
                items_with_links=prepared_items,
                l2_exclusions=l2_exclusions,
            )

            # T15: compare replay identities with deterministic conflict precedence (§8.2)
            existing_eval = db.execute(
                select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run.id)
            ).scalar_one_or_none()
            existing_items = list(
                db.execute(
                    select(ReviewItem)
                    .where(ReviewItem.workflow_run_id == run.id)
                    .order_by(ReviewItem.display_order)
                ).scalars()
            )
            existing_item_ids = [item.id for item in existing_items]
            existing_links = (
                list(
                    db.execute(
                        select(EvidenceLink).where(
                            EvidenceLink.owner_type == "review_item",
                            EvidenceLink.owner_id.in_(existing_item_ids),
                        )
                    ).scalars()
                )
                if existing_item_ids
                else []
            )

            audit_request_identity = hashlib.sha256(
                "|".join(
                    ("p4-rb3-audit-request", RB3_AUDIT_EVENT_TYPE, run.id, principal.user_id)
                ).encode("utf-8")
            ).hexdigest()
            expected_audit_key = derive_audit_key(
                event_type=RB3_AUDIT_EVENT_TYPE,
                actor_type=principal.actor_type,
                actor_id=principal.user_id,
                outcome=AuditOutcome.OK,
                subject_type="workflow_run",
                subject_id=run.id,
                request_id=audit_request_identity,
            )
            audit_by_key = db.execute(
                select(AuditEvent).where(AuditEvent.idempotency_key == expected_audit_key)
            ).scalar_one_or_none()
            audits_by_run = list(
                db.execute(
                    select(AuditEvent).where(
                        AuditEvent.event_type == RB3_AUDIT_EVENT_TYPE,
                        AuditEvent.workflow_run_id == run.id,
                    )
                ).scalars()
            )

            if existing_eval is None:
                if existing_items or existing_links:
                    raise _conflict(RB3DenialReason.COMPLETION_EVIDENCE_MISSING)
                if audit_by_key is not None or audits_by_run:
                    raise _conflict(RB3DenialReason.ORPHAN_REVIEW_AUDIT)
            else:
                expected_item_tuples = {
                    (
                        item[0],
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        item[5],
                        item[6],
                        item[7],
                        item[8],
                        item[9],
                        item[10],
                    )
                    for item in prepared_items
                }
                persisted_item_tuples = {
                    (
                        item.display_order,
                        item.rule_id,
                        item.reason_code,
                        item.workflow_hint,
                        item.trust_basis,
                        item.message,
                        item.policy_version,
                        item.dedupe_key,
                        item.state,
                        item.provenance_status,
                        item.stored_lineage_proved,
                    )
                    for item in existing_items
                }
                item_key_by_id = {item.id: item.dedupe_key for item in existing_items}
                expected_link_tuples = {
                    (item[7], lnk[0], lnk[1], lnk[2], lnk[3], lnk[4], lnk[5])
                    for item in prepared_items
                    for lnk in item[11]
                }
                persisted_link_tuples = {
                    (
                        item_key_by_id.get(lnk.owner_id),
                        lnk.kind,
                        lnk.document_id,
                        lnk.observation_id,
                        lnk.page_index,
                        lnk.char_start,
                        lnk.char_end,
                    )
                    for lnk in existing_links
                }

                same_output_claim = existing_eval.output_identity_sha256 == output_identity_sha256
                # Precedence 3: extra_persisted_items
                if (
                    len(existing_items) > existing_eval.item_count
                    or len(existing_links) > existing_eval.evidence_link_count
                    or (
                        same_output_claim
                        and (
                            bool(persisted_item_tuples - expected_item_tuples)
                            or bool(persisted_link_tuples - expected_link_tuples)
                        )
                    )
                ):
                    raise _conflict(RB3DenialReason.EXTRA_PERSISTED_ITEMS)

                # Precedence 4: missing_persisted_evidence
                if (
                    len(existing_items) < existing_eval.item_count
                    or len(existing_links) < existing_eval.evidence_link_count
                    or (
                        same_output_claim
                        and (
                            bool(expected_item_tuples - persisted_item_tuples)
                            or bool(expected_link_tuples - persisted_link_tuples)
                        )
                    )
                ):
                    raise _conflict(RB3DenialReason.MISSING_PERSISTED_EVIDENCE)

                # Precedence 5: input_identity_changed
                if (
                    existing_eval.fingerprint_version != RB3_FINGERPRINT_VERSION
                    or existing_eval.input_fingerprint_sha256 != input_fingerprint_sha256
                    or existing_eval.gate_evaluation_id != stored_gate.id
                    or existing_eval.gate_input_fingerprint_sha256
                    != receipt_gate.input_fingerprint_sha256
                    or existing_eval.bridge_input_fingerprint_sha256
                    != evidence.bridge_input_fingerprint_sha256
                    or existing_eval.f2_contract_version != CONTRACT_VERSION
                    or existing_eval.gate_version != GATE_VERSION
                    or existing_eval.rb2_policy_version != rule_result.policy_version
                    or existing_eval.policy_version != RB3_POLICY_VERSION
                    or existing_eval.policy_reference_sha256 != RB3_PINNED_POLICY_SHA256
                    or existing_eval.as_of_utc != run.as_of_utc
                    or existing_eval.patient_id != run.patient_id
                    or existing_eval.doctor_id != run.doctor_id
                    or existing_eval.lineage_label_policy != RB3_LINEAGE_LABEL_POLICY
                    or existing_eval.dr006_policy != RB3_DR006_POLICY
                    or existing_eval.exclusion_count != len(l3_merged)
                    or existing_eval.demo_only != 1
                ):
                    raise _conflict(RB3DenialReason.INPUT_IDENTITY_CHANGED)

                # Precedence 6: output_identity_changed
                links_by_owner: dict[
                    str,
                    list[tuple[str, str | None, str | None, int | None, int | None, int | None]],
                ] = {}
                for lnk in existing_links:
                    links_by_owner.setdefault(lnk.owner_id, []).append(
                        (
                            lnk.kind,
                            lnk.document_id,
                            lnk.observation_id,
                            lnk.page_index,
                            lnk.char_start,
                            lnk.char_end,
                        )
                    )
                persisted_for_hash = [
                    (
                        item.display_order,
                        item.rule_id,
                        item.reason_code,
                        item.workflow_hint,
                        item.trust_basis,
                        item.message,
                        item.policy_version,
                        item.dedupe_key,
                        item.state,
                        item.provenance_status,
                        item.stored_lineage_proved,
                        links_by_owner.get(item.id, []),
                    )
                    for item in existing_items
                ]
                recomputed_persisted_output_sha = _compute_output_identity(
                    items_with_links=persisted_for_hash,
                    l2_exclusions=l2_exclusions,
                )
                if (
                    existing_eval.item_count != len(prepared_items)
                    or existing_eval.evidence_link_count != total_links
                    or existing_eval.output_identity_sha256 != output_identity_sha256
                    or recomputed_persisted_output_sha != existing_eval.output_identity_sha256
                    or persisted_item_tuples != expected_item_tuples
                    or persisted_link_tuples != expected_link_tuples
                ):
                    raise _conflict(RB3DenialReason.OUTPUT_IDENTITY_CHANGED)

                # Precedence 7: audit_business_inconsistent
                audit_row = db.get(AuditEvent, existing_eval.audit_event_id)
                if (
                    audit_row is None
                    or audit_row.event_type != RB3_AUDIT_EVENT_TYPE
                    or audit_row.actor_type != principal.actor_type.value
                    or audit_row.actor_id != principal.user_id
                    or audit_row.patient_id != run.patient_id
                    or audit_row.workflow_run_id != run.id
                    or audit_row.subject_type != "workflow_run"
                    or audit_row.subject_id != run.id
                    or audit_row.outcome != AuditOutcome.OK.value
                    or audit_row.idempotency_key != expected_audit_key
                    or len(audits_by_run) != 1
                    or audits_by_run[0].id != audit_row.id
                    or not _parse_and_verify_audit_detail(
                        audit_row.safe_detail,
                        expected_evaluation_id=existing_eval.id,
                        expected_input_sha=input_fingerprint_sha256,
                        expected_output_sha=output_identity_sha256,
                        expected_item_count=len(prepared_items),
                        expected_link_count=total_links,
                        expected_exclusion_count=len(l3_merged),
                    )
                ):
                    raise _conflict(RB3DenialReason.AUDIT_BUSINESS_INCONSISTENT)

                # Final freshness verification before completing exact replay
                replay_final_gate = inspect_current_run_gate_locked(
                    db,
                    principal=principal,
                    run_id=run.id,
                    at=clock,
                    upload_root=upload_root,
                )
                replay_rehashed = {
                    doc_id: _rehash_document_bytes(docs_by_id[doc_id], upload_root)
                    for doc_id in sorted(docs_by_id)
                }
                if (
                    replay_final_gate.input_fingerprint_sha256
                    != receipt_gate.input_fingerprint_sha256
                    or replay_rehashed != file_hashes
                ):
                    raise _deny("Source evidence changed during replay.")

                # Construct complete frozen receipt from verified data while transaction is active.
                replay_receipt = ReviewPersistenceReceiptV1(
                    contract_version=RB3_RECEIPT_CONTRACT_VERSION,
                    run_id=run.id,
                    patient_id=run.patient_id,
                    doctor_id=run.doctor_id,
                    as_of_utc=run.as_of_utc,
                    policy_version=RB3_POLICY_VERSION,
                    policy_reference_sha256=RB3_PINNED_POLICY_SHA256,
                    gate_evaluation_id=existing_eval.gate_evaluation_id,
                    gate_version=existing_eval.gate_version,
                    gate_input_fingerprint_sha256=existing_eval.gate_input_fingerprint_sha256,
                    bridge_input_fingerprint_sha256=existing_eval.bridge_input_fingerprint_sha256,
                    rb3_fingerprint_version=existing_eval.fingerprint_version,
                    input_fingerprint_sha256=existing_eval.input_fingerprint_sha256,
                    output_identity_sha256=existing_eval.output_identity_sha256,
                    evaluation_id=existing_eval.id,
                    audit_event_id=existing_eval.audit_event_id,
                    lineage_label_policy=cast(
                        Literal["a2_transport_label"], existing_eval.lineage_label_policy
                    ),
                    dr006_policy=cast(
                        Literal["prohibited_denied", "not_present"], existing_eval.dr006_policy
                    ),
                    replayed=True,
                    review_items_persisted=0,
                    review_items_total=existing_eval.item_count,
                    evidence_links_persisted=0,
                    evidence_links_total=existing_eval.evidence_link_count,
                    excluded_evidence=l3_merged,
                    layered_exclusions=LayeredEvidenceExclusionsV1(
                        l0_lineage_checks=l0_checks,
                        l1_exclusions=l1_exclusions,
                        l2_exclusions=l2_exclusions,
                        l3_merged=l3_merged,
                    ),
                    l1_exclusion_count=len(l1_exclusions),
                    l2_exclusion_count=len(l2_exclusions),
                )
                # Exact replay (Case 1 / Case 7): zero writes; roll back read transaction cleanly.
                db.rollback()
                return replay_receipt

            # T16: atomic first-evaluation persistence in FK-safe order
            created_ts = format_utc(clock)
            evaluation_id = new_uuid()
            try:
                persisted_item_objs: list[ReviewItem] = []
                for item_tuple in prepared_items:
                    item_obj = ReviewItem(
                        id=new_uuid(),
                        patient_id=run.patient_id,
                        workflow_run_id=run.id,
                        rule_id=item_tuple[1],
                        reason_code=item_tuple[2],
                        workflow_hint=item_tuple[3],
                        trust_basis=item_tuple[4],
                        message=item_tuple[5],
                        policy_version=item_tuple[6],
                        demo_only=1,
                        dedupe_key=item_tuple[7],
                        state="open",
                        provenance_status=item_tuple[9],
                        stored_lineage_proved=item_tuple[10],
                        display_order=item_tuple[0],
                        created_at=created_ts,
                    )
                    db.add(item_obj)
                    persisted_item_objs.append(item_obj)
                db.flush()

                for item_obj, item_tuple in zip(persisted_item_objs, prepared_items, strict=True):
                    for link_tuple in item_tuple[11]:
                        db.add(
                            EvidenceLink(
                                id=new_uuid(),
                                owner_type="review_item",
                                owner_id=item_obj.id,
                                kind=link_tuple[0],
                                document_id=link_tuple[1],
                                observation_id=link_tuple[2],
                                page_index=link_tuple[3],
                                char_start=link_tuple[4],
                                char_end=link_tuple[5],
                                created_at=created_ts,
                            )
                        )
                db.flush()

                fragments, composed_detail = _compose_audit_fragments(
                    evaluation_id=evaluation_id,
                    input_fingerprint_sha256=input_fingerprint_sha256,
                    output_identity_sha256=output_identity_sha256,
                    item_count=len(prepared_items),
                    evidence_link_count=total_links,
                    exclusion_count=len(l3_merged),
                )
                audit_event = append_audit_event(
                    db,
                    event_type=RB3_AUDIT_EVENT_TYPE,
                    actor_type=principal.actor_type,
                    actor_id=principal.user_id,
                    outcome=AuditOutcome.OK,
                    request_id=audit_request_identity,
                    now=clock,
                    patient_id=run.patient_id,
                    workflow_run_id=run.id,
                    subject_type="workflow_run",
                    subject_id=run.id,
                    detail_fragments=fragments,
                )
                if (
                    audit_event.event_type != RB3_AUDIT_EVENT_TYPE
                    or audit_event.actor_type != principal.actor_type.value
                    or audit_event.actor_id != principal.user_id
                    or audit_event.patient_id != run.patient_id
                    or audit_event.workflow_run_id != run.id
                    or audit_event.subject_type != "workflow_run"
                    or audit_event.subject_id != run.id
                    or audit_event.outcome != AuditOutcome.OK.value
                    or audit_event.idempotency_key != expected_audit_key
                    or audit_event.safe_detail != composed_detail
                ):
                    raise _conflict(RB3DenialReason.AUDIT_KEY_COLLISION)

                db.add(
                    ReviewEvaluation(
                        id=evaluation_id,
                        workflow_run_id=run.id,
                        patient_id=run.patient_id,
                        doctor_id=run.doctor_id,
                        as_of_utc=run.as_of_utc,
                        policy_version=RB3_POLICY_VERSION,
                        policy_reference_sha256=RB3_PINNED_POLICY_SHA256,
                        fingerprint_version=RB3_FINGERPRINT_VERSION,
                        input_fingerprint_sha256=input_fingerprint_sha256,
                        output_identity_sha256=output_identity_sha256,
                        gate_evaluation_id=stored_gate.id,
                        gate_input_fingerprint_sha256=receipt_gate.input_fingerprint_sha256,
                        bridge_input_fingerprint_sha256=evidence.bridge_input_fingerprint_sha256,
                        f2_contract_version=CONTRACT_VERSION,
                        gate_version=GATE_VERSION,
                        rb2_policy_version=rule_result.policy_version,
                        lineage_label_policy=RB3_LINEAGE_LABEL_POLICY,
                        dr006_policy=RB3_DR006_POLICY,
                        item_count=len(prepared_items),
                        evidence_link_count=total_links,
                        exclusion_count=len(l3_merged),
                        audit_event_id=audit_event.id,
                        demo_only=1,
                        created_at=created_ts,
                    )
                )
                db.flush()
            except IntegrityError:
                raise _conflict(RB3DenialReason.INTEGRITY_CONFLICT) from None

            # T17: pre-commit revalidation
            final_gate = inspect_current_run_gate_locked(
                db,
                principal=principal,
                run_id=run.id,
                at=clock,
                upload_root=upload_root,
            )
            rehashed_final = {
                doc_id: _rehash_document_bytes(docs_by_id[doc_id], upload_root)
                for doc_id in sorted(docs_by_id)
            }
            final_input_fingerprint = _compute_input_identity(
                run=run,
                patient=patient,
                stored_gate=stored_gate,
                receipt_gate_version=final_gate.gate_version,
                receipt_gate_fingerprint=final_gate.input_fingerprint_sha256,
                receipt_gate_decision=final_gate.decision,
                receipt_gate_blocking_count=final_gate.blocking_fact_count,
                receipt_gate_vi002_ids=final_gate.historical_excluded_vi002_ids,
                bridge_fingerprint=evidence.bridge_input_fingerprint_sha256,
                rb1_contract_version=preview.contract_version,
                policy=policy_candidate,
                clock=clock,
                selected_docs_manifest=selected_docs_manifest,
                selected_obs_manifest=selected_obs_manifest,
                omissions_manifest=omissions_manifest,
                docs_by_id=docs_by_id,
                file_hashes=rehashed_final,
                obs_rows_by_id=obs_rows_by_id,
                selected_current_ids=observation_ids,
                eligible_history_ids=eligible_history_ids,
                l1_exclusions=l1_exclusions,
                l0_checks=l0_checks,
                proved_by_obs=proved_by_obs,
                provenance_by_obs=provenance_by_obs,
                all_facts=all_facts,
                all_decisions=all_decisions,
                active_statuses=active_statuses,
                comparisons_90d=comparisons_90d,
                rule_input=rule_input,
            )
            if (
                final_gate.input_fingerprint_sha256 != receipt_gate.input_fingerprint_sha256
                or rehashed_final != file_hashes
                or final_input_fingerprint != input_fingerprint_sha256
            ):
                raise _deny("Source evidence changed before commit.")

            # Construct complete frozen receipt while the owned transaction is still active
            # so post-commit ORM attribute access (even with expire_on_commit=True) is zero.
            first_receipt = ReviewPersistenceReceiptV1(
                contract_version=RB3_RECEIPT_CONTRACT_VERSION,
                run_id=run.id,
                patient_id=run.patient_id,
                doctor_id=run.doctor_id,
                as_of_utc=run.as_of_utc,
                policy_version=RB3_POLICY_VERSION,
                policy_reference_sha256=RB3_PINNED_POLICY_SHA256,
                gate_evaluation_id=stored_gate.id,
                gate_version=final_gate.gate_version,
                gate_input_fingerprint_sha256=final_gate.input_fingerprint_sha256,
                bridge_input_fingerprint_sha256=evidence.bridge_input_fingerprint_sha256,
                rb3_fingerprint_version=RB3_FINGERPRINT_VERSION,
                input_fingerprint_sha256=input_fingerprint_sha256,
                output_identity_sha256=output_identity_sha256,
                evaluation_id=evaluation_id,
                audit_event_id=audit_event.id,
                lineage_label_policy=RB3_LINEAGE_LABEL_POLICY,
                dr006_policy=RB3_DR006_POLICY,
                replayed=False,
                review_items_persisted=len(prepared_items),
                review_items_total=len(prepared_items),
                evidence_links_persisted=total_links,
                evidence_links_total=total_links,
                excluded_evidence=l3_merged,
                layered_exclusions=LayeredEvidenceExclusionsV1(
                    l0_lineage_checks=l0_checks,
                    l1_exclusions=l1_exclusions,
                    l2_exclusions=l2_exclusions,
                    l3_merged=l3_merged,
                ),
                l1_exclusion_count=len(l1_exclusions),
                l2_exclusion_count=len(l2_exclusions),
            )

        # T18: single durable commit; if commit fails, rollback runs and nothing is returned.
        db.commit()
    except Exception:
        db.rollback()
        raise

    return first_receipt


__all__ = [
    "RB3_AUDIT_DETAIL_KEYS",
    "RB3_AUDIT_EVENT_TYPE",
    "RB3_DR006_POLICY",
    "RB3_FINGERPRINT_VERSION",
    "RB3_LINEAGE_LABEL_POLICY",
    "RB3_PINNED_AS_OF_UTC",
    "RB3_PINNED_POLICY_SHA256",
    "RB3_POLICY_VERSION",
    "RB3_RECEIPT_CONTRACT_VERSION",
    "SUPPORTED_MIN_MEASURED_AT",
    "persist_run_review_items",
]
