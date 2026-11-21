"""P4 R21-S1: offline-only, read-only future recovery source-set *proposal*.

A passed *candidate* is NOT a selected workflow run, a durable doctor decision,
or an authorization to run rules. The owner approved source-selection semantics
for future implementation, not a P4 run gate. NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import parse_utc, to_utc
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import Document, UserSession, VerificationIssue
from app.services.documents.intake import RECOVERABLE_FAILURE_CODES
from app.services.p4_document_preflight import (
    MAX_SELECTED_DOCUMENTS,
    inspect_selected_document_verification,
)

MAX_LINEAGE_DEPTH = 8
MAX_LINEAGE_DOCUMENTS = 32
MAX_HISTORICAL_ISSUES = 100
_OMISSION_REASON = "selected_separate_recovery_source"


@dataclass(frozen=True, slots=True)
class CandidateDoctorOmission:
    """Unpersisted offline proposal, NOT a doctor-authored audited decision."""

    terminal_document_id: str
    reason_code: str


@dataclass(frozen=True, slots=True, order=True)
class RecoverySelectionBlock:
    document_id: str
    reason_code: str


@dataclass(frozen=True, slots=True, order=True)
class HistoricalRejectedSource:
    document_id: str
    failure_code: str
    vi002_state: str


@dataclass(frozen=True, slots=True)
class RecoverySelectionInspection:
    patient_id: str
    doctor_user_id: str
    selected_document_ids: tuple[str, ...]
    omission_proposals: tuple[CandidateDoctorOmission, ...]
    historical_rejected_sources: tuple[HistoricalRejectedSource, ...]
    blockers: tuple[RecoverySelectionBlock, ...]
    offline_selection_shape_valid: bool
    doctor_selection_audited: bool = field(default=False, init=False)
    run_gate_completed: bool = field(default=False, init=False)
    runtime_evaluable: bool = field(default=False, init=False)
    run_gate_status: Literal["unavailable"] = field(default="unavailable", init=False)


def _selection_ids(ids: object) -> tuple[str, ...]:
    if (
        not isinstance(ids, tuple)
        or len(ids) > MAX_SELECTED_DOCUMENTS
        or any(not isinstance(value, str) or not value.strip() for value in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ApiError(400, ErrorCode.VALIDATION, "Invalid selected source set.")
    return tuple(sorted(ids))


def _proposals(value: object) -> tuple[CandidateDoctorOmission, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) > MAX_LINEAGE_DOCUMENTS
        or any(
            not isinstance(item, CandidateDoctorOmission)
            or not isinstance(item.terminal_document_id, str)
            or not item.terminal_document_id.strip()
            or item.reason_code != _OMISSION_REASON
            for item in value
        )
        or len({item.terminal_document_id for item in value}) != len(value)
    ):
        raise ApiError(400, ErrorCode.VALIDATION, "Invalid doctor omission proposal.")
    return tuple(sorted(value, key=lambda x: x.terminal_document_id))


def inspect_offline_recovery_selection(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    selected_document_ids: tuple[str, ...],
    omission_proposals: tuple[CandidateDoctorOmission, ...],
    as_of_utc: datetime,
) -> RecoverySelectionInspection:
    """Inspect stored synthetic lineage and an *untrusted* omission proposal.

    Requires an actual stored principal session, but does not authenticate or
    persist the proposed future doctor's *selection decision*. No run identity,
    no source-byte/OCR attestation, and no full VI-001..006 reevaluation.
    """
    chosen = _selection_ids(selected_document_ids)
    omissions = _proposals(omission_proposals)
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "An authenticated principal is required.")
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ApiError(400, ErrorCode.VALIDATION, "Patient scope required.")
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "Aware evaluation clock required.") from None
    if db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "A clean read-only session is required.")

    with db.no_autoflush:
        session = db.execute(
            select(UserSession).where(
                UserSession.id == principal.session_id,
                UserSession.user_id == principal.user_id,
            )
        ).scalar_one_or_none()
        try:
            session_valid = (
                session is not None
                and session.revoked_at is None
                and parse_utc(session.created_at) <= clock < parse_utc(session.expires_at)
            )
        except (TypeError, ValueError, AttributeError):
            session_valid = False
        if not session_valid:
            raise ApiError(403, ErrorCode.FORBIDDEN, "Active stored session required.")

        # Existing inspector checks stored doctor role, active assignment and
        # synthetic patient. For an empty selection, use a scoped independent
        # read with identical checks, without requiring an artificial doc ID.
        if chosen:
            selected_preflight = inspect_selected_document_verification(
                db, principal=principal, patient_id=patient_id, document_ids=chosen
            )
        else:
            from app.core.enums import Role
            from app.core.policies import require_assigned_patient, require_doctor
            from app.db.models import Patient, User

            require_doctor(principal)
            user = db.execute(select(User).where(User.id == principal.user_id)).scalar_one_or_none()
            if user is None or user.role != Role.DOCTOR.value or user.is_active != 1:
                raise ApiError(403, ErrorCode.FORBIDDEN, "Stored doctor account required.")
            patient = db.execute(
                select(Patient).where(Patient.id == patient_id)
            ).scalar_one_or_none()
            if patient is None:
                raise ApiError(404, ErrorCode.NOT_FOUND, "Patient unavailable.")
            require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
            if patient.data_source != "synthetic_fixture":
                raise ApiError(403, ErrorCode.FORBIDDEN, "Only synthetic patients supported.")
            selected_preflight = None

        # Bound every row read to this patient; unrelated/missing ancestor IDs
        # produce the same neutral error, preventing cross-patient disclosure.
        docs: dict[str, Document] = {}

        def get_document(identifier: str) -> Document:
            if identifier not in docs:
                if len(docs) >= MAX_LINEAGE_DOCUMENTS:
                    raise ApiError(400, ErrorCode.VALIDATION, "Recovery lineage too large.")
                row = db.execute(
                    select(Document).where(
                        Document.id == identifier, Document.patient_id == patient_id
                    )
                ).scalar_one_or_none()
                if row is None:
                    raise ApiError(404, ErrorCode.NOT_FOUND, "Selected source lineage unavailable.")
                docs[identifier] = row
            return docs[identifier]

        blocks: set[RecoverySelectionBlock] = set()
        ancestry: set[str] = set()
        if not chosen:
            blocks.add(RecoverySelectionBlock("", "empty_selected_source_set"))
        if selected_preflight is not None and not selected_preflight.candidate_documents_clear:
            for block in selected_preflight.blockers:
                blocks.add(RecoverySelectionBlock(block.document_id, block.reason_code))

        for selected in chosen:
            current = get_document(selected)
            if (
                current.extraction_status == "failed"
                and current.failure_code in RECOVERABLE_FAILURE_CODES
            ):
                blocks.add(RecoverySelectionBlock(current.id, "selected_terminal_rejected_source"))
            if current.recovered_from_document_id and current.sha256 is None:
                blocks.add(RecoverySelectionBlock(current.id, "source_hash_missing"))
            visited = {current.id}
            depth = 0
            while current.recovered_from_document_id:
                depth += 1
                if depth > MAX_LINEAGE_DEPTH:
                    blocks.add(RecoverySelectionBlock(selected, "recovery_chain_too_deep"))
                    break
                parent_id = current.recovered_from_document_id
                if parent_id in visited:
                    blocks.add(RecoverySelectionBlock(selected, "recovery_lineage_cycle"))
                    break
                visited.add(parent_id)
                parent = get_document(parent_id)
                ancestry.add(parent.id)
                if parent.id in chosen:
                    blocks.add(RecoverySelectionBlock(parent.id, "rejected_ancestor_also_selected"))
                if parent.extraction_status != "failed" or parent.failure_code not in (
                    RECOVERABLE_FAILURE_CODES
                ):
                    blocks.add(RecoverySelectionBlock(parent.id, "invalid_recovery_parent_status"))
                if current.sha256 == parent.sha256:
                    blocks.add(
                        RecoverySelectionBlock(current.id, "recovery_identical_source_bytes")
                    )
                current = parent

        # Every omitted terminal ancestor must remain visible with its P3 VI-002;
        # never turn that historical issue into a resolved run-gate result.
        history: list[HistoricalRejectedSource] = []
        if ancestry:
            issues = list(
                db.execute(
                    select(VerificationIssue)
                    .where(
                        VerificationIssue.patient_id == patient_id,
                        VerificationIssue.document_id.in_(sorted(ancestry)),
                        VerificationIssue.issue_type == "VI-002",
                    )
                    .limit(MAX_HISTORICAL_ISSUES + 1)
                ).scalars()
            )
            if len(issues) > MAX_HISTORICAL_ISSUES:
                raise ApiError(
                    400, ErrorCode.VALIDATION, "Too many historical verification issues."
                )
            by_doc = {issue.document_id: issue for issue in issues}
            for doc_id in sorted(ancestry):
                doc = docs[doc_id]
                issue = by_doc.get(doc_id)
                state = issue.state if issue is not None else "missing"
                history.append(HistoricalRejectedSource(doc.id, doc.failure_code or "", state))
                if issue is None or issue.state != "open" or issue.blocking != 1:
                    blocks.add(RecoverySelectionBlock(doc.id, "historical_vi002_not_open"))

        omission_ids = {item.terminal_document_id for item in omissions}
        for ancestor in sorted(ancestry - set(chosen)):
            if ancestor not in omission_ids:
                blocks.add(RecoverySelectionBlock(ancestor, "missing_doctor_omission_proposal"))
        for extra in sorted(omission_ids - (ancestry - set(chosen))):
            blocks.add(RecoverySelectionBlock(extra, "omission_not_a_selected_recovery_ancestor"))

    ordered = tuple(sorted(blocks))
    return RecoverySelectionInspection(
        patient_id=patient_id,
        doctor_user_id=principal.user_id,
        selected_document_ids=chosen,
        omission_proposals=omissions,
        historical_rejected_sources=tuple(history),
        blockers=ordered,
        offline_selection_shape_valid=not ordered,
    )


__all__ = [
    "CandidateDoctorOmission",
    "HistoricalRejectedSource",
    "RecoverySelectionBlock",
    "RecoverySelectionInspection",
    "inspect_offline_recovery_selection",
]
