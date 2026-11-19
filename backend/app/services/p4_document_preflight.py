"""Read-only P4-2f selected-document verification preflight (synthetic demo).

This is NOT the run-scoped fact_verify_gate: there is no workflow_run row,
approved policy, original-file/OCR fidelity proof or DR output here. Caller
must supply a server-authenticated Principal. Never call a live rule engine
based solely on this scoped preflight.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_assigned_patient, require_doctor
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Patient,
    User,
    VerificationIssue,
)

MAX_SELECTED_DOCUMENTS = 8
MAX_DOCUMENT_FACTS = 200
MAX_OPEN_ISSUES = 100


@dataclass(frozen=True, slots=True)
class CandidateDocumentBlock:
    document_id: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class SelectedDocumentPreflight:
    """A read-only snapshot, not an authorization to execute review rules."""

    patient_id: str
    document_ids: tuple[str, ...]
    active_fact_count: int
    verified_fact_count: int
    blockers: tuple[CandidateDocumentBlock, ...]
    candidate_documents_clear: bool
    run_gate_completed: bool = False


def _decision_matches(db: Session, fact: ExtractedFact, by_id: dict[str, ExtractedFact]) -> bool:
    """Require one recorded doctor decision for a current verified fact."""
    if fact.verification_status != "verified":
        return False
    source_id = fact.corrected_from_fact_id or fact.id
    events = list(
        db.execute(select(FactVerification).where(FactVerification.fact_id == source_id)).scalars()
    )
    if len(events) != 1:
        return False
    decision = events[0]
    user = db.execute(
        select(User).where(User.id == decision.verified_by_user_id)
    ).scalar_one_or_none()
    if user is None or user.role != Role.DOCTOR.value or user.is_active != 1:
        return False
    if fact.corrected_from_fact_id is None:
        return decision.decision == "verified"
    original = by_id.get(source_id)
    return (
        original is not None
        and original.document_id == fact.document_id
        and original.patient_id == fact.patient_id
        and original.verification_status == "rejected"
        and decision.decision == "corrected"
        and decision.new_value is not None
        and decision.new_value == fact.normalized_value
    )


def inspect_selected_document_verification(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    document_ids: tuple[str, ...],
) -> SelectedDocumentPreflight:
    """Inspect exactly the selected documents, fail-closed on unsound evidence.

    This function reads no upload bytes, writes nothing and never asks the
    caller for a blocking count. It intentionally cannot decide whether a
    future workflow run is eligible: run identity, recovery equivalence and
    source-image confirmation require a separately reviewed gate.
    """
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "A server identity is required.")
    require_doctor(principal)
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ApiError(400, ErrorCode.VALIDATION, "A patient scope is required.")
    if (
        not isinstance(document_ids, tuple)
        or not 1 <= len(document_ids) <= MAX_SELECTED_DOCUMENTS
        or any(not isinstance(item, str) or not item.strip() for item in document_ids)
        or len(set(document_ids)) != len(document_ids)
    ):
        raise ApiError(400, ErrorCode.VALIDATION, "Invalid selected document set.")

    with db.no_autoflush:
        user = db.execute(select(User).where(User.id == principal.user_id)).scalar_one_or_none()
        if user is None or user.role != Role.DOCTOR.value or user.is_active != 1:
            raise ApiError(403, ErrorCode.FORBIDDEN, "A stored doctor account is required.")
        patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
        if patient is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, "Patient record is not available.")
        require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
        if patient.data_source != "synthetic_fixture":
            raise ApiError(403, ErrorCode.FORBIDDEN, "Only synthetic demo records are supported.")

        docs = list(
            db.execute(
                select(Document).where(
                    Document.id.in_(document_ids), Document.patient_id == patient.id
                )
            ).scalars()
        )
        if len(docs) != len(document_ids):
            raise ApiError(404, ErrorCode.NOT_FOUND, "Selected document is not available.")
        by_document = {doc.id: doc for doc in docs}

        facts = list(
            db.execute(
                select(ExtractedFact)
                .where(ExtractedFact.document_id.in_(document_ids))
                .order_by(ExtractedFact.document_id, ExtractedFact.id)
                .limit(MAX_DOCUMENT_FACTS + 1)
            ).scalars()
        )
        if len(facts) > MAX_DOCUMENT_FACTS:
            raise ApiError(400, ErrorCode.VALIDATION, "Too many selected document facts.")

        issues = list(
            db.execute(
                select(VerificationIssue)
                .where(
                    VerificationIssue.document_id.in_(document_ids),
                    VerificationIssue.state == "open",
                )
                .limit(MAX_OPEN_ISSUES + 1)
            ).scalars()
        )
        if len(issues) > MAX_OPEN_ISSUES:
            raise ApiError(400, ErrorCode.VALIDATION, "Too many open verification issues.")

        blockers: set[CandidateDocumentBlock] = set()
        verified = 0
        active = 0
        for doc_id in document_ids:
            doc = by_document[doc_id]
            if doc.extraction_status != "verified" or doc.failure_code is not None:
                blockers.add(CandidateDocumentBlock(doc_id, "document_not_verified"))
            if not patient.external_ref or doc.document_patient_ref != patient.external_ref:
                blockers.add(CandidateDocumentBlock(doc_id, "document_identity_unresolved"))
            if any(issue.document_id == doc_id for issue in issues):
                blockers.add(CandidateDocumentBlock(doc_id, "open_verification_issue"))

            subset = [fact for fact in facts if fact.document_id == doc_id]
            if not subset:
                blockers.add(CandidateDocumentBlock(doc_id, "document_has_no_facts"))
                continue
            by_id = {fact.id: fact for fact in subset}
            valid_replacements = {
                fact.corrected_from_fact_id
                for fact in subset
                if fact.corrected_from_fact_id and _decision_matches(db, fact, by_id)
            }
            for fact in subset:
                if fact.patient_id != patient.id:
                    blockers.add(CandidateDocumentBlock(doc_id, "fact_scope_invalid"))
                    continue
                if fact.id in valid_replacements and fact.verification_status == "rejected":
                    continue
                active += 1
                if fact.verification_status != "verified":
                    blockers.add(CandidateDocumentBlock(doc_id, "active_fact_unverified"))
                elif _decision_matches(db, fact, by_id):
                    verified += 1
                else:
                    blockers.add(CandidateDocumentBlock(doc_id, "fact_decision_unproven"))

    ordered = tuple(sorted(blockers, key=lambda item: (item.document_id, item.reason_code)))
    return SelectedDocumentPreflight(
        patient_id=patient.id,
        document_ids=tuple(sorted(document_ids)),
        active_fact_count=active,
        verified_fact_count=verified,
        blockers=ordered,
        candidate_documents_clear=not ordered,
    )


__all__ = [
    "MAX_DOCUMENT_FACTS",
    "MAX_OPEN_ISSUES",
    "MAX_SELECTED_DOCUMENTS",
    "CandidateDocumentBlock",
    "SelectedDocumentPreflight",
    "inspect_selected_document_verification",
]
