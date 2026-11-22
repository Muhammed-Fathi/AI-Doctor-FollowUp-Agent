"""P5-F1: bounded, internal, run-bound synthetic verification gate.

No graph, DR review, API, LLM, approval, clinical advice or messaging.
Only a current, authenticated synthetic doctor's F0-selected evidence is read.
P3 historic verification issues are never modified. A 'proceed' is an F1
preflight receipt ONLY, not authority to execute an agent or DR rules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc, to_utc
from app.core.config import get_settings
from app.core.enums import (
    MAPPING_TABLE,
    MAPPING_VERSION,
    MEASURE_UNITS,
    AuditOutcome,
    DocumentUnit,
    IssueType,
    MeasureType,
    QualityFlag,
    Role,
)
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_assigned_patient, require_doctor
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    RunGateBlocker,
    RunGateEvaluation,
    RunSelectedDocument,
    RunSelectedObservation,
    RunSourceOmission,
    User,
    UserSession,
    VerificationIssue,
    WorkflowRun,
    new_uuid,
)
from app.services.audit import append_audit_event
from app.services.documents import storage
from app.services.documents.issues import (
    ConflictCandidate,
    collect_source_conflict_issue,
    render_message,
)
from app.services.p4_document_preflight import inspect_selected_document_verification
from app.services.p4_recovery_selection_candidate import (
    CandidateDoctorOmission,
    inspect_offline_recovery_selection,
)
from app.services.p5_run_foundation import (
    POLICY_REFERENCE_VERSION,
    STATE_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)

GATE_VERSION = "1.0.0"
MAX_GATE_FACTS = 40
MAX_GATE_OBSERVATIONS = 100
VI_TYPES = frozenset(f"VI-{number:03d}" for number in range(1, 7))


@dataclass(frozen=True, order=True, slots=True)
class RunGateIssue:
    issue_type: str
    reason_code: str
    document_id: str
    fact_ids: tuple[str, ...] = ()
    message: str = ""


@dataclass(frozen=True, slots=True)
class RunGateReceipt:
    run_id: str
    patient_id: str
    doctor_id: str
    gate_version: str
    input_fingerprint_sha256: str
    decision: Literal["proceed", "halt", "unavailable"]
    issues: tuple[RunGateIssue, ...]
    historical_excluded_vi002_ids: tuple[str, ...]
    blocking_fact_count: int
    unavailable_reason: str | None
    replayed: bool
    gate_evaluated: bool = field(default=True, init=False)
    runtime_evaluable: bool = field(default=False, init=False)


def _sha(payload: object) -> str:
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _issue(
    issue_type: str,
    document_id: str,
    reason_code: str,
    fact_ids: tuple[str, ...] = (),
    *,
    count: int = 0,
    measure_type: str = "",
) -> RunGateIssue:
    if issue_type not in VI_TYPES:
        raise ValueError("Invalid VI issue type")
    return RunGateIssue(
        issue_type=issue_type,
        document_id=document_id,
        reason_code=reason_code,
        fact_ids=tuple(sorted(set(fact_ids))),
        message=render_message(IssueType(issue_type), count=count, measure_type=measure_type),
    )


def _file_sha(document: Document, upload_root: str) -> str | None:
    """Check a trusted-root path and byte integrity, not original OCR glyphs."""
    try:
        path = storage.resolve_for_read(document.stored_path, upload_dir=upload_root)
        content = path.read_bytes()
    except (FileNotFoundError, OSError, ValueError):
        return None
    if len(content) != document.size_bytes:
        return None
    digest = hashlib.sha256(content).hexdigest()
    return digest if digest == document.sha256 else None


def _authorize(db: Session, principal: Principal, run: WorkflowRun, at: datetime) -> Patient:
    require_doctor(principal)
    if run.doctor_id != principal.user_id:
        raise ApiError(403, ErrorCode.FORBIDDEN, "Run is unavailable to this doctor.")
    stored_session = db.execute(
        select(UserSession).where(
            UserSession.id == principal.session_id,
            UserSession.user_id == principal.user_id,
        )
    ).scalar_one_or_none()
    user = db.get(User, principal.user_id)
    try:
        active = (
            stored_session is not None
            and stored_session.revoked_at is None
            and parse_utc(stored_session.created_at) <= at
            and at < parse_utc(stored_session.expires_at)
        )
    except (TypeError, AttributeError, ValueError):
        active = False
    if not active or user is None or user.role != Role.DOCTOR.value or user.is_active != 1:
        raise ApiError(403, ErrorCode.FORBIDDEN, "An active doctor session is required.")
    patient = db.get(Patient, run.patient_id)
    if patient is None or patient.data_source != "synthetic_fixture":
        raise ApiError(403, ErrorCode.FORBIDDEN, "Synthetic patient scope is required.")
    require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
    return patient


def _receipt(
    run: WorkflowRun,
    fingerprint: str,
    decision: str,
    issues: tuple[RunGateIssue, ...],
    historical: tuple[str, ...],
    count: int,
    reason: str | None,
    *,
    replayed: bool,
) -> RunGateReceipt:
    if decision not in {"proceed", "halt", "unavailable"}:
        raise ValueError("Invalid decision")
    return RunGateReceipt(
        run_id=run.id,
        patient_id=run.patient_id,
        doctor_id=run.doctor_id,
        gate_version=GATE_VERSION,
        input_fingerprint_sha256=fingerprint,
        decision=decision,
        issues=issues,
        historical_excluded_vi002_ids=historical,
        blocking_fact_count=count,
        unavailable_reason=reason,
        replayed=replayed,
    )


def _evaluate_locked(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    at: datetime,
    upload_root: str,
    require_existing: bool = False,
) -> RunGateReceipt:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Run is unavailable.")
    patient = _authorize(db, principal, run, at)
    if run.status != "queued":
        raise ApiError(409, ErrorCode.VALIDATION, "Run is not queued for F1 evaluation.")

    docs_saved = list(
        db.execute(
            select(RunSelectedDocument)
            .where(RunSelectedDocument.workflow_run_id == run.id)
            .order_by(RunSelectedDocument.document_id)
        ).scalars()
    )
    obs_saved = list(
        db.execute(
            select(RunSelectedObservation)
            .where(RunSelectedObservation.workflow_run_id == run.id)
            .order_by(RunSelectedObservation.observation_id)
        ).scalars()
    )
    omissions = list(
        db.execute(
            select(RunSourceOmission)
            .where(RunSourceOmission.workflow_run_id == run.id)
            .order_by(RunSourceOmission.document_id)
        ).scalars()
    )
    if not 1 <= len(docs_saved) <= 5 or len(obs_saved) > 20 or len(omissions) > 20:
        raise ApiError(409, ErrorCode.VALIDATION, "Run manifest is invalid.")
    doc_ids = tuple(row.document_id for row in docs_saved)
    obs_ids = tuple(row.observation_id for row in obs_saved)
    if len(set(doc_ids)) != len(doc_ids) or len(set(obs_ids)) != len(obs_ids):
        raise ApiError(409, ErrorCode.VALIDATION, "Run manifest contains duplicate sources.")

    snapshot: dict[str, object] = {
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
        "documents": [],
        "facts": [],
        "decisions": [],
        "issues": [],
        "observations": [],
        "selected": [doc_ids, obs_ids],
        "policy_settings": [
            get_settings().ocr_confidence_floor,
            get_settings().conflict_tolerance,
        ],
        "omissions": [],
    }
    unavailable: str | None = None
    if any(value is not None for value in (run.current_node, run.halt_reason, run.checkpoint_ref)):
        unavailable = "run_execution_state_unexpected"
    if (
        run.mapping_version != MAPPING_VERSION
        or run.policy_version != POLICY_REFERENCE_VERSION
        or run.workflow_version != WORKFLOW_VERSION
        or run.state_schema_version != STATE_SCHEMA_VERSION
    ):
        unavailable = "unsupported_run_version"
    try:
        as_of = parse_utc(run.as_of_utc)
    except (TypeError, ValueError, AttributeError):
        as_of = at
        unavailable = "invalid_run_clock"

    recorded: set[RunGateIssue] = set()
    docs: dict[str, Document] = {}
    file_hashes: dict[str, str] = {}
    total_facts = 0
    for item in docs_saved:
        doc = db.get(Document, item.document_id)
        if doc is None or doc.patient_id != run.patient_id:
            raise ApiError(409, ErrorCode.VALIDATION, "Selected document scope changed.")
        docs[doc.id] = doc
        sha = _file_sha(doc, upload_root)
        if sha is None:
            unavailable = "source_bytes_unavailable"
        if doc.sha256 != item.source_sha256 or doc.extraction_status != item.source_status:
            unavailable = "selected_document_changed"
        if sha is not None:
            file_hashes[doc.id] = sha
        snapshot["documents"].append(
            [
                doc.id,
                doc.patient_id,
                doc.stored_path,
                doc.mime_type,
                doc.page_count,
                doc.uploaded_at,
                doc.document_patient_ref,
                doc.document_patient_refs,
                doc.extraction_status,
                doc.failure_code,
                doc.recovered_from_document_id,
                doc.sha256,
                doc.size_bytes,
                sha,
            ]
        )
        if doc.document_patient_ref != patient.external_ref:
            recorded.add(_issue("VI-004", doc.id, "wrong_patient_document"))
        if doc.extraction_status != "verified" or doc.failure_code is not None:
            unavailable = "selected_document_not_verified"
        if sha is None:
            continue

        facts = list(
            db.execute(
                select(ExtractedFact)
                .where(ExtractedFact.document_id == doc.id)
                .order_by(ExtractedFact.id)
                .limit(MAX_GATE_FACTS + 1)
            ).scalars()
        )
        total_facts += len(facts)
        if total_facts > MAX_GATE_FACTS:
            unavailable = "too_many_selected_facts"
            break
        by_id = {f.id: f for f in facts}
        verified_corrections = {
            f.corrected_from_fact_id
            for f in facts
            if f.corrected_from_fact_id and f.verification_status == "verified"
        }
        active = [f for f in facts if f.id not in verified_corrections]
        decisions = (
            list(
                db.execute(
                    select(FactVerification)
                    .where(FactVerification.fact_id.in_(tuple(by_id)))
                    .order_by(FactVerification.id)
                ).scalars()
            )
            if by_id
            else []
        )
        for f in facts:
            snapshot["facts"].append(
                [
                    f.id,
                    f.document_id,
                    f.patient_id,
                    f.field_name,
                    f.raw_text,
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
            )
            if f.patient_id != patient.id:
                unavailable = "fact_patient_scope_changed"
        for dec in decisions:
            snapshot["decisions"].append(
                [
                    dec.id,
                    dec.fact_id,
                    dec.decision,
                    dec.previous_value,
                    dec.new_value,
                    dec.new_unit,
                    dec.confirmed_value,
                    dec.confirmed_unit,
                    dec.reason,
                    dec.verified_by_user_id,
                    dec.decided_at,
                    dec.source_image_compared,
                ]
            )
        # A malformed or unknown quality flag is NOT a clean fact. This is a
        # closed P3 enum; never accept arbitrary JSON list elements as evidence.
        flags: dict[str, tuple[str, ...]] = {}
        allowed_flags = {flag.value for flag in QualityFlag}
        for fact in active:
            try:
                parsed_flags = json.loads(fact.quality_flags)
                if not isinstance(parsed_flags, list) or any(
                    not isinstance(value, str) or value not in allowed_flags
                    for value in parsed_flags
                ):
                    unavailable = "invalid_quality_flags"
                    flags[fact.id] = ()
                else:
                    flags[fact.id] = tuple(parsed_flags)
            except (TypeError, ValueError):
                unavailable = "invalid_quality_flags"
                flags[fact.id] = ()

        if not active:
            unavailable = "selected_document_has_no_active_facts"
        measurement_values = [f for f in active if f.field_name == "value"]
        if len(measurement_values) > 1:
            recorded.add(
                _issue(
                    "VI-002",
                    doc.id,
                    "multi_measurement_document",
                    tuple(f.id for f in measurement_values),
                    count=len(measurement_values),
                )
            )
        pending = tuple(f.id for f in active if f.verification_status != "verified")
        if pending:
            recorded.add(_issue("VI-002", doc.id, "fact_unverified", pending, count=len(pending)))
        if any(
            f.field_name == "value" and f.unit not in {unit.value for unit in DocumentUnit}
            for f in active
        ):
            recorded.add(_issue("VI-001", doc.id, "unit_missing_or_unsupported"))
        dates = [
            f.normalized_value
            for f in active
            if f.field_name == "report_date" and f.normalized_value
        ]
        if not dates or len(set(dates)) != 1:
            recorded.add(_issue("VI-003", doc.id, "date_ambiguous"))
        else:
            try:
                datetime.strptime(dates[0], "%Y-%m-%d")
            except ValueError:
                recorded.add(_issue("VI-003", doc.id, "date_ambiguous"))
        for f in active:
            bits = set(flags.get(f.id, ()))
            if "ambiguous_unit" in bits and f.field_name == "value":
                recorded.add(_issue("VI-001", doc.id, "unit_missing_or_unsupported", (f.id,)))
            if "ambiguous_date" in bits:
                recorded.add(_issue("VI-003", doc.id, "date_ambiguous", (f.id,)))
            if (
                "unparseable_value" in bits
                or "low_confidence" in bits
                or ("page_missing" in bits and f.field_name == "value")
                or (
                    f.extractor == "tesseract"
                    and f.confidence is not None
                    and f.confidence < get_settings().ocr_confidence_floor
                )
            ):
                recorded.add(_issue("VI-005", doc.id, "value_unreadable", (f.id,)))
            if "source_conflict" in bits:
                recorded.add(_issue("VI-006", doc.id, "source_conflict_at_intake", (f.id,)))
            if f.field_name == "value":
                try:
                    float(f.normalized_value or "")
                except (TypeError, ValueError):
                    recorded.add(_issue("VI-005", doc.id, "value_unreadable", (f.id,)))

        existing_issues = list(
            db.execute(
                select(VerificationIssue)
                .where(VerificationIssue.document_id == doc.id)
                .order_by(VerificationIssue.id)
            ).scalars()
        )
        for issue in existing_issues:
            snapshot["issues"].append(
                [
                    issue.id,
                    issue.patient_id,
                    issue.document_id,
                    issue.issue_type,
                    issue.reason_code,
                    issue.fact_ids,
                    issue.blocking,
                    issue.state,
                ]
            )
            if issue.state == "open":
                if issue.issue_type == "VI-002":
                    if pending:
                        recorded.add(
                            _issue(
                                "VI-002",
                                doc.id,
                                issue.reason_code,
                                pending,
                                count=len(pending),
                            )
                        )
                    else:
                        unavailable = "unresolved_p3_vi002"
                elif issue.issue_type in VI_TYPES:
                    recorded.add(_issue(issue.issue_type, doc.id, issue.reason_code))
                else:
                    unavailable = "unsupported_open_issue_type"
        preflight = inspect_selected_document_verification(
            db,
            principal=principal,
            patient_id=patient.id,
            document_ids=(doc.id,),
        )
        if not preflight.candidate_documents_clear:
            expected_blocks = {
                "active_fact_unverified",
                "open_verification_issue",
                "document_identity_unresolved",
            }
            if any(block.reason_code not in expected_blocks for block in preflight.blockers):
                unavailable = "selected_document_preflight_unproven"

    # The observation history contributes to conflict detection and fingerprint,
    # including unselected same-day records: no new conflict can be ignored.
    history = list(
        db.execute(
            select(Observation)
            .where(Observation.patient_id == patient.id)
            .order_by(Observation.id)
            .limit(MAX_GATE_OBSERVATIONS + 1)
        ).scalars()
    )
    if len(history) > MAX_GATE_OBSERVATIONS:
        unavailable = "too_many_patient_observations"
    by_obs = {obs.id: obs for obs in history}
    for obs in history:
        snapshot["observations"].append(
            [
                obs.id,
                obs.patient_id,
                obs.measure_type,
                obs.value,
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
                obs.note,
                obs.created_by_user_id,
            ]
        )
    for row in obs_saved:
        obs = by_obs.get(row.observation_id)
        if obs is None:
            unavailable = "selected_observation_missing"
            continue
        try:
            measure = MeasureType(obs.measure_type)
            measured_at = parse_utc(obs.measured_at)
            valid = (
                obs.patient_id == run.patient_id
                and obs.validation != "rejected"
                and obs.unit in {u.value for u in MEASURE_UNITS[measure]}
                and measured_at <= as_of + timedelta(minutes=5)
                and row.observation_created_at == obs.created_at
                and row.trust_level == obs.trust_level
                and row.source_fact_id == obs.source_fact_id
            )
            if obs.trust_level == "self_reported_validated":
                valid = valid and (
                    obs.source in {"seed_fixture", "patient_checkin"}
                    and obs.verified_by_user_id is None
                    and obs.verified_at is None
                    and obs.source_fact_id is None
                )
            elif obs.trust_level == "doctor_verified":
                source_fact = (
                    db.get(ExtractedFact, obs.source_fact_id) if obs.source_fact_id else None
                )
                valid = valid and (
                    obs.source == "verified_document"
                    and source_fact is not None
                    and source_fact.document_id in docs
                    and source_fact.patient_id == run.patient_id
                    and source_fact.verification_status == "verified"
                    and obs.verified_by_user_id is not None
                    and obs.verified_at is not None
                )
            else:
                valid = False
            if not valid:
                unavailable = "selected_observation_inadmissible"
        except (TypeError, ValueError, AttributeError):
            unavailable = "selected_observation_inadmissible"

    for doc_id in doc_ids:
        facts = list(
            db.execute(
                select(ExtractedFact)
                .where(ExtractedFact.document_id == doc_id)
                .order_by(ExtractedFact.id)
                .limit(MAX_GATE_FACTS + 1)
            ).scalars()
        )
        # Constrained, deterministic synthetic same-day VI-006 comparison.
        tests = [f for f in facts if f.field_name == "test_name" and f.normalized_value]
        dates = [f for f in facts if f.field_name == "report_date" and f.normalized_value]
        values = [
            f for f in facts if f.field_name == "value" and f.verification_status == "verified"
        ]
        if len(tests) != 1 or len(dates) != 1 or len(values) != 1:
            continue
        alias = " ".join(tests[0].normalized_value.lower().strip().rstrip(":").split())
        mapped = MAPPING_TABLE.get(alias)
        if mapped is None or values[0].unit != mapped[1].value:
            continue
        try:
            candidate = ConflictCandidate(
                fact_index=0,
                measure_type=mapped[0].value,
                value=float(values[0].normalized_value),
                unit=values[0].unit,
                measured_at=dates[0].normalized_value + "T00:00:00Z",
            )
        except (TypeError, ValueError):
            continue
        comparables = [
            (obs.unit, obs.value, obs.measured_at)
            for obs in history
            if obs.measure_type == mapped[0].value
            and obs.validation != "rejected"
            and obs.trust_level in {"self_reported_validated", "doctor_verified"}
            and obs.source_fact_id not in {fact.id for fact in facts}
        ]
        conflict = collect_source_conflict_issue(
            candidate=candidate,
            existing=comparables,
            tolerance=get_settings().conflict_tolerance,
        )
        if conflict is not None:
            recorded.add(
                _issue(
                    "VI-006",
                    doc_id,
                    "source_conflict_at_intake",
                    (values[0].id,),
                    measure_type=mapped[0].value,
                )
            )

    # Re-read lineage and historical issues using ONLY the persisted omission
    # manifest, not newly supplied patient/doctor proposals.
    historical: list[str] = []
    for item in omissions:
        original = db.get(Document, item.document_id)
        issue = db.get(VerificationIssue, item.vi002_issue_id)
        if (
            original is None
            or issue is None
            or original.patient_id != patient.id
            or item.doctor_id != principal.user_id
            or original.sha256 != item.source_sha256
            or issue.document_id != original.id
            or issue.issue_type != "VI-002"
            or issue.state != "open"
            or issue.blocking != 1
            or item.reason_code != "selected_separate_recovery_source"
        ):
            unavailable = "historical_omission_changed"
            continue
        snapshot["omissions"].append(
            [
                original.id,
                original.sha256,
                original.extraction_status,
                original.failure_code,
                issue.id,
                issue.patient_id,
                issue.reason_code,
                issue.blocking,
                issue.state,
                item.doctor_id,
                item.vi002_issue_id,
                item.reason_code,
            ]
        )
        historical.append(issue.id)
    inspection = inspect_offline_recovery_selection(
        db,
        principal=principal,
        patient_id=patient.id,
        selected_document_ids=doc_ids,
        omission_proposals=tuple(
            CandidateDoctorOmission(
                terminal_document_id=item.document_id,
                reason_code=item.reason_code,
            )
            for item in omissions
        ),
        as_of_utc=at,
    )
    if not inspection.offline_selection_shape_valid:
        # The R21 shape inspector also reports document-level pending facts.
        # Those are known VI-002 HALT outcomes; do not mislabel them as a
        # broken recovery lineage. Every unrelated lineage defect still
        # invalidates the entire snapshot.
        vi_only = {
            "active_fact_unverified",
            "open_verification_issue",
            "document_not_verified",
            "fact_decision_unproven",
            "document_has_no_facts",
            "document_identity_unresolved",
        }
        if any(block.reason_code not in vi_only for block in inspection.blockers):
            unavailable = "selected_recovery_lineage_changed"

    # F1 cannot atomically pin disk bytes with SQLite, but rechecking here
    # catches a replacement before the commit; F2 must validate again.
    for doc_id, before in file_hashes.items():
        if _file_sha(docs[doc_id], upload_root) != before:
            unavailable = "source_bytes_changed_during_gate"

    fingerprint = _sha(snapshot)
    ordered = tuple(sorted(recorded))
    blocking_count = len({fact for item in ordered for fact in item.fact_ids})
    if blocking_count > MAX_GATE_FACTS:
        unavailable = "too_many_blocking_facts"
    decision: Literal["proceed", "halt", "unavailable"] = (
        "unavailable" if unavailable else "halt" if ordered else "proceed"
    )
    stable_idem = _sha([run.id, fingerprint, GATE_VERSION])
    previous = db.execute(
        select(RunGateEvaluation).where(RunGateEvaluation.idempotency_key == stable_idem)
    ).scalar_one_or_none()
    if previous is not None:
        # The immutable parent alone is insufficient: a forged extra blocker
        # INSERT or mismatched stored historical-exclusion list must not be
        # accepted as a valid replay of previously certified evidence.
        stored_blockers = list(
            db.execute(
                select(RunGateBlocker).where(RunGateBlocker.gate_evaluation_id == previous.id)
            ).scalars()
        )
        try:
            recorded_blockers = sorted(
                (
                    item.issue_type,
                    item.reason_code,
                    item.document_id,
                    tuple(json.loads(item.fact_ids)),
                )
                for item in stored_blockers
            )
        except (TypeError, ValueError):
            raise ApiError(
                409, ErrorCode.IDEMPOTENCY_CONFLICT, "Gate blocker evidence is invalid."
            ) from None
        expected_blockers = sorted(
            (item.issue_type, item.reason_code, item.document_id or None, item.fact_ids)
            for item in ordered
        )
        if (
            previous.workflow_run_id != run.id
            or previous.gate_version != GATE_VERSION
            or previous.as_of_utc != run.as_of_utc
            or previous.decision != decision
            or previous.blocking_fact_count != blocking_count
            or previous.unavailable_reason != unavailable
            or previous.historical_excluded_vi002_ids != json.dumps(sorted(historical))
            or recorded_blockers != expected_blockers
        ):
            raise ApiError(409, ErrorCode.IDEMPOTENCY_CONFLICT, "Gate replay evidence changed.")
        return _receipt(
            run,
            fingerprint,
            decision,
            ordered,
            tuple(sorted(historical)),
            blocking_count,
            unavailable,
            replayed=True,
        )

    # F2 MUST NOT persist a new gate/audit row when it inspects the
    # current authoritative snapshot. Its read-only caller requires an
    # already-existing matching immutable F1 PROCEED decision.
    if require_existing:
        raise ApiError(
            409, ErrorCode.VALIDATION, "No current persisted F1 gate evidence is available."
        )

    evaluation = RunGateEvaluation(
        id=new_uuid(),
        workflow_run_id=run.id,
        gate_version=GATE_VERSION,
        input_fingerprint_sha256=fingerprint,
        idempotency_key=stable_idem,
        decision=decision,
        unavailable_reason=unavailable,
        blocking_fact_count=blocking_count,
        historical_excluded_vi002_ids=json.dumps(sorted(historical)),
        as_of_utc=run.as_of_utc,
        evaluated_at=format_utc(at),
    )
    db.add(evaluation)
    db.flush()
    for issue in ordered:
        db.add(
            RunGateBlocker(
                gate_evaluation_id=evaluation.id,
                issue_type=issue.issue_type,
                reason_code=issue.reason_code,
                document_id=issue.document_id or None,
                fact_ids=json.dumps(issue.fact_ids),
            )
        )
    db.flush()
    append_audit_event(
        db,
        event_type="workflow.gate.evaluated",
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=stable_idem,
        now=at,
        patient_id=run.patient_id,
        workflow_run_id=run.id,
        subject_type="workflow_run",
        subject_id=run.id,
        detail_fragments=("phase=p5-f1", f"decision={decision}", "runtime_evaluable=false"),
    )
    return _receipt(
        run,
        fingerprint,
        decision,
        ordered,
        tuple(sorted(historical)),
        blocking_count,
        unavailable,
        replayed=False,
    )


def inspect_current_run_gate_locked(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    at: datetime,
    upload_root: str,
) -> RunGateReceipt:
    """Re-evaluate current F1 state without writes inside a caller-owned SQLite lock.

    Only the F2 bridge may call this with an already open BEGIN IMMEDIATE
    transaction. The existing F1 evaluator retains its exact original
    persisted-decision behavior. Missing or stale gate decisions cannot be
    manufactured here. Never treat this as a graph/DR execution token.
    """
    if not db.in_transaction():
        raise ApiError(409, ErrorCode.VALIDATION, "A locked read transaction is required.")
    result = _evaluate_locked(
        db,
        principal=principal,
        run_id=run_id,
        at=at,
        upload_root=upload_root,
        require_existing=True,
    )
    if result.decision != "proceed" or result.issues or result.unavailable_reason:
        raise ApiError(409, ErrorCode.VALIDATION, "Current F1 gate is not eligible.")
    return result


def evaluate_run_verification_gate(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
) -> RunGateReceipt:
    """Own a SQLite IMMEDIATE transaction and commit only typed F1 gate evidence.

    A fresh, clean Session is required; no caller transaction or unreviewed
    autoflush is permitted. Lock acquisition failure never claims PROCEED.
    """
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "Authenticated doctor required.")
    if not isinstance(run_id, str) or not run_id:
        raise ApiError(400, ErrorCode.VALIDATION, "Run identifier required.")
    if not isinstance(upload_root, str) or not upload_root:
        raise ApiError(400, ErrorCode.VALIDATION, "Trusted local upload root required.")
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A fresh clean Session is required.")
    try:
        clock = to_utc(validation_clock)
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except (TypeError, AttributeError, ValueError):
        db.rollback()
        raise ApiError(400, ErrorCode.VALIDATION, "Aware validation clock required.") from None
    except OperationalError:
        db.rollback()
        raise ApiError(503, ErrorCode.VALIDATION, "Verification database is unavailable.") from None
    try:
        result = _evaluate_locked(
            db, principal=principal, run_id=run_id, at=clock, upload_root=upload_root
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


__all__ = [
    "GATE_VERSION",
    "RunGateIssue",
    "RunGateReceipt",
    "evaluate_run_verification_gate",
    "inspect_current_run_gate_locked",
]
