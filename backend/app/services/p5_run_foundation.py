"""P5-F0: server-owned run identity and auditable selected-source manifest.

The *only* operation here is a local database foundation insert. It never
executes a graph, resolves VI-002, evaluates DR flags or calls an LLM.
All source IDs are untrusted selectors until validated against stored
authenticated doctor/assigned-patient context. NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import format_utc, to_utc
from app.core.enums import MAPPING_VERSION, AuditOutcome
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import (
    Document,
    Observation,
    RunSelectedDocument,
    RunSelectedObservation,
    RunSourceOmission,
    VerificationIssue,
    WorkflowRun,
    new_uuid,
)
from app.services.audit import append_audit_event
from app.services.p4_recovery_selection_candidate import (
    CandidateDoctorOmission,
    inspect_offline_recovery_selection,
)

WORKFLOW_VERSION = "1.0.0"
STATE_SCHEMA_VERSION = "1.0.0"
POLICY_REFERENCE_VERSION = "demo-policy-1.1.0"
MAX_SELECTED_OBSERVATIONS = 20
MAX_REQUEST_ID_LENGTH = 64
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
OMISSION_REASON = "selected_separate_recovery_source"


@dataclass(frozen=True, slots=True)
class RunFoundationReceipt:
    """Receipt only: no real verification gate or run execution is claimed."""

    run_id: str
    thread_id: str
    patient_id: str
    doctor_id: str
    document_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    omission_document_ids: tuple[str, ...]
    status: Literal["queued"]
    replayed: bool
    run_gate_status: Literal["unavailable"] = field(default="unavailable", init=False)
    run_gate_completed: bool = field(default=False, init=False)
    runtime_evaluable: bool = field(default=False, init=False)


def _canonical_ids(value: object, max_size: int, label: str) -> tuple[str, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) > max_size
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(set(value)) != len(value)
    ):
        raise ApiError(400, ErrorCode.VALIDATION, f"Invalid {label} selection.")
    return tuple(sorted(value))


def _request_key(
    *,
    patient_id: str,
    document_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    client_request_id: str,
) -> str:
    """State contract §7: only stable input identifiers enter the start key."""
    parts = (
        patient_id,
        WORKFLOW_VERSION,
        ",".join(document_ids),
        ",".join(observation_ids),
        client_request_id,
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _receipt(
    run: WorkflowRun,
    *,
    document_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    omitted_ids: tuple[str, ...],
    replayed: bool,
) -> RunFoundationReceipt:
    # F0 has only queued runs; any later lifecycle needs a separately
    # ratified P5 implementation and may not be called through this starter.
    if run.status != "queued":
        raise ApiError(409, ErrorCode.IDEMPOTENCY_CONFLICT, "Run is no longer in F0 scope.")
    return RunFoundationReceipt(
        run_id=run.id,
        thread_id=run.id,
        patient_id=run.patient_id,
        doctor_id=run.doctor_id,
        document_ids=document_ids,
        observation_ids=observation_ids,
        omission_document_ids=omitted_ids,
        status="queued",
        replayed=replayed,
    )


def create_run_foundation(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    document_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    omissions: tuple[CandidateDoctorOmission, ...],
    client_request_id: str,
    as_of_utc: datetime,
) -> RunFoundationReceipt:
    """Persist the first honest run with doctor-authored source selection.

    Caller owns the transaction (commit or rollback). A clean Session is
    mandatory so an unreviewed pending write cannot autoflush before checks.
    The P4 R21 inspector runs before any F0 write and authenticates the
    persisted doctor session/assignment and full recovery chain. Its result
    remains a shape check, not a run gate.
    """
    if db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A clean session is required.")
    if not isinstance(client_request_id, str) or not _REQUEST_ID.fullmatch(client_request_id):
        raise ApiError(400, ErrorCode.VALIDATION, "Invalid client request identifier.")
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "Authenticated doctor required.")
    chosen_docs = _canonical_ids(document_ids, 5, "document")
    chosen_obs = _canonical_ids(observation_ids, MAX_SELECTED_OBSERVATIONS, "observation")
    try:
        clock = to_utc(as_of_utc)
        timestamp = format_utc(clock)
    except (TypeError, ValueError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "Aware evaluation clock required.") from None

    with db.no_autoflush:
        inspected = inspect_offline_recovery_selection(
            db,
            principal=principal,
            patient_id=patient_id,
            selected_document_ids=chosen_docs,
            omission_proposals=omissions,
            as_of_utc=clock,
        )
        if not inspected.offline_selection_shape_valid:
            raise ApiError(409, ErrorCode.VALIDATION, "Selected sources require review.")

        # Nothing from client-provided identifiers may be trusted as evidence.
        documents = {
            row.id: row
            for row in db.execute(
                select(Document).where(
                    Document.patient_id == patient_id,
                    Document.id.in_(chosen_docs),
                )
            ).scalars()
        }
        observations = (
            {
                row.id: row
                for row in db.execute(
                    select(Observation).where(
                        Observation.patient_id == patient_id,
                        Observation.id.in_(chosen_obs),
                    )
                ).scalars()
            }
            if chosen_obs
            else {}
        )
        if len(documents) != len(chosen_docs) or len(observations) != len(chosen_obs):
            raise ApiError(404, ErrorCode.NOT_FOUND, "Selected patient sources unavailable.")

        omitted = tuple(sorted(item.terminal_document_id for item in inspected.omission_proposals))
        history: dict[str, tuple[Document, VerificationIssue]] = {}
        for document_id in omitted:
            parent = db.execute(
                select(Document).where(
                    Document.id == document_id,
                    Document.patient_id == patient_id,
                )
            ).scalar_one_or_none()
            issues = list(
                db.execute(
                    select(VerificationIssue).where(
                        VerificationIssue.document_id == document_id,
                        VerificationIssue.patient_id == patient_id,
                        VerificationIssue.issue_type == "VI-002",
                    )
                ).scalars()
            )
            if (
                parent is None
                or len(issues) != 1
                or issues[0].state != "open"
                or issues[0].blocking != 1
            ):
                raise ApiError(409, ErrorCode.VALIDATION, "Historical omission cannot be audited.")
            history[document_id] = (parent, issues[0])

        key = _request_key(
            patient_id=patient_id,
            document_ids=chosen_docs,
            observation_ids=chosen_obs,
            client_request_id=client_request_id,
        )
        previous = db.execute(
            select(WorkflowRun).where(WorkflowRun.idempotency_key == key)
        ).scalar_one_or_none()
        if previous is not None:
            # A replay can never adopt a different doctor, clock, version,
            # omission decision, or a partially persisted manifest.
            docs_saved = set(
                db.execute(
                    select(RunSelectedDocument.document_id).where(
                        RunSelectedDocument.workflow_run_id == previous.id
                    )
                ).scalars()
            )
            obs_saved = set(
                db.execute(
                    select(RunSelectedObservation.observation_id).where(
                        RunSelectedObservation.workflow_run_id == previous.id
                    )
                ).scalars()
            )
            omissions_saved = set(
                db.execute(
                    select(RunSourceOmission.document_id).where(
                        RunSourceOmission.workflow_run_id == previous.id
                    )
                ).scalars()
            )
            if (
                previous.doctor_id != principal.user_id
                or previous.patient_id != patient_id
                or previous.as_of_utc != timestamp
                or previous.policy_version != POLICY_REFERENCE_VERSION
                or previous.mapping_version != MAPPING_VERSION
                or docs_saved != set(chosen_docs)
                or obs_saved != set(chosen_obs)
                or omissions_saved != set(omitted)
            ):
                raise ApiError(
                    409,
                    ErrorCode.IDEMPOTENCY_CONFLICT,
                    "Run request conflicts with saved selection.",
                )
            return _receipt(
                previous,
                document_ids=chosen_docs,
                observation_ids=chosen_obs,
                omitted_ids=omitted,
                replayed=True,
            )

    run = WorkflowRun(
        id=new_uuid(),
        patient_id=patient_id,
        doctor_id=principal.user_id,
        workflow_version=WORKFLOW_VERSION,
        state_schema_version=STATE_SCHEMA_VERSION,
        policy_version=POLICY_REFERENCE_VERSION,
        as_of_utc=timestamp,
        status="queued",
        idempotency_key=key,
        mapping_version=MAPPING_VERSION,
        started_at=timestamp,
        updated_at=timestamp,
    )
    db.add(run)
    db.flush()

    for doc_id in chosen_docs:
        doc = documents[doc_id]
        db.add(
            RunSelectedDocument(
                workflow_run_id=run.id,
                document_id=doc_id,
                source_sha256=doc.sha256,
                source_status=doc.extraction_status,
                created_at=timestamp,
            )
        )
    for obs_id in chosen_obs:
        obs = observations[obs_id]
        db.add(
            RunSelectedObservation(
                workflow_run_id=run.id,
                observation_id=obs_id,
                observation_created_at=obs.created_at,
                trust_level=obs.trust_level,
                source_fact_id=obs.source_fact_id,
                created_at=timestamp,
            )
        )
    for doc_id in omitted:
        parent, issue = history[doc_id]
        db.add(
            RunSourceOmission(
                workflow_run_id=run.id,
                document_id=doc_id,
                vi002_issue_id=issue.id,
                doctor_id=principal.user_id,
                reason_code=OMISSION_REASON,
                source_sha256=parent.sha256,
                created_at=timestamp,
            )
        )
    db.flush()

    # One atomic app-DB transaction with the authoritative run + manifest.
    # Audit details are enum-like, never document text, OCR snippets or PHI.
    append_audit_event(
        db,
        event_type="workflow.run.started",
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=client_request_id,
        now=clock,
        patient_id=patient_id,
        workflow_run_id=run.id,
        subject_type="workflow_run",
        subject_id=run.id,
        detail_fragments=("phase=p5-f0", "gate=unavailable"),
    )
    return _receipt(
        run,
        document_ids=chosen_docs,
        observation_ids=chosen_obs,
        omitted_ids=omitted,
        replayed=False,
    )


__all__ = [
    "RunFoundationReceipt",
    "create_run_foundation",
]
