"""P4-2e internal read-only SQLite projection for *synthetic* provenance.

Not an API, agent tool, verification gate, or review-rule activation.
The caller must supply a server-authenticated Principal. This function
independently re-checks persisted doctor/assignment scope, observation lineage
and human decisions, but does not verify original PDF/OCR fidelity or the
run-scoped VI-* gate. No writes, policy defaults or notifications.
EDUCATIONAL / SYNTHETIC / NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import to_utc
from app.core.enums import Role
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_assigned_patient, require_doctor
from app.db.models import Document, ExtractedFact, FactVerification, Observation, Patient, User
from app.services.monitoring import ObservationSnapshot
from app.services.provenance_review_candidate import (
    CandidateEvidenceExclusion,
    CandidateRecordedObservation,
)

MAX_OFFLINE_ROWS = 100


@dataclass(frozen=True, slots=True)
class ReadonlyProvenanceEvidence:
    """Scoped, bounded evidence snapshot; NOT a post-verification gate verdict."""

    records: tuple[CandidateRecordedObservation, ...]
    lineage_exclusions: tuple[CandidateEvidenceExclusion, ...]
    patient_id: str
    as_of_utc: datetime


def _number(value: str | float | None) -> Decimal | None:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount


def _stored_verified_lineage(
    db: Session,
    *,
    row: Observation,
    patient: Patient,
) -> tuple[str, str] | None:
    """Check persisted human-decision lineage; cannot attest physical file review.

    Corrected values are verified through the original fact's 'corrected'
    decision, not through a non-existent decision on the corrected row.
    """
    if (
        row.source != "verified_document"
        or row.trust_level != "doctor_verified"
        or not row.source_fact_id
        or not row.verified_by_user_id
        or not row.verified_at
    ):
        return None

    verifier = db.execute(
        select(User).where(User.id == row.verified_by_user_id)
    ).scalar_one_or_none()
    if verifier is None or verifier.role != Role.DOCTOR.value or verifier.is_active != 1:
        return None
    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.id == row.source_fact_id,
            ExtractedFact.patient_id == patient.id,
        )
    ).scalar_one_or_none()
    if fact is None or fact.field_name != "value" or fact.verification_status != "verified":
        return None
    document = db.execute(
        select(Document).where(
            Document.id == fact.document_id,
            Document.patient_id == patient.id,
        )
    ).scalar_one_or_none()
    if (
        document is None
        or document.extraction_status != "verified"
        or document.document_patient_ref != patient.external_ref
        or fact.unit != row.unit
        or _number(fact.normalized_value) is None
        or _number(fact.normalized_value) != _number(row.value)
    ):
        return None

    original_id = fact.corrected_from_fact_id or fact.id
    decisions = list(
        db.execute(
            select(FactVerification).where(FactVerification.fact_id == original_id)
        ).scalars()
    )
    if len(decisions) != 1:
        return None
    decision = decisions[0]
    decision_doctor = db.execute(
        select(User).where(User.id == decision.verified_by_user_id)
    ).scalar_one_or_none()
    if (
        decision_doctor is None
        or decision_doctor.role != Role.DOCTOR.value
        or decision_doctor.is_active != 1
    ):
        return None

    if fact.corrected_from_fact_id:
        original = db.execute(
            select(ExtractedFact).where(
                ExtractedFact.id == fact.corrected_from_fact_id,
                ExtractedFact.document_id == document.id,
                ExtractedFact.patient_id == patient.id,
            )
        ).scalar_one_or_none()
        if (
            original is None
            or original.field_name != "value"
            or original.verification_status != "rejected"
            or decision.decision != "corrected"
            or _number(decision.new_value) != _number(fact.normalized_value)
        ):
            return None
    elif decision.decision != "verified":
        return None
    return fact.id, document.id


def load_readonly_provenance_evidence(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    as_of_utc: datetime,
) -> ReadonlyProvenanceEvidence:
    """Project up to 100 observations through stored doctor-only patient scope.

    This internal function is intentionally NOT callable from an API router.
    Never pass its returned rows to a live rule executor while a real
    run-scoped verification gate and policy adapter are absent.
    """
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "A server identity is required.")
    require_doctor(principal)
    if not isinstance(patient_id, str) or not patient_id.strip():
        raise ApiError(400, ErrorCode.VALIDATION, "A patient scope is required.")
    try:
        clock = to_utc(as_of_utc)
    except (ValueError, TypeError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "An explicit UTC clock is required.") from None

    with db.no_autoflush:
        doctor = db.execute(select(User).where(User.id == principal.user_id)).scalar_one_or_none()
        if doctor is None or doctor.role != Role.DOCTOR.value or doctor.is_active != 1:
            raise ApiError(403, ErrorCode.FORBIDDEN, "A stored doctor account is required.")
        patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
        if patient is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, "Patient record is not available.")
        require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
        if patient.data_source != "synthetic_fixture":
            raise ApiError(403, ErrorCode.FORBIDDEN, "Only synthetic demo records are supported.")

        rows = list(
            db.execute(
                select(Observation)
                .where(Observation.patient_id == patient.id)
                .order_by(Observation.measured_at.desc(), Observation.id)
                .limit(MAX_OFFLINE_ROWS + 1)
            ).scalars()
        )
        if len(rows) > MAX_OFFLINE_ROWS:
            raise ApiError(400, ErrorCode.VALIDATION, "Too many scoped observations.")

        entries: list[CandidateRecordedObservation] = []
        excluded: list[CandidateEvidenceExclusion] = []
        for row in rows:
            lineage = _stored_verified_lineage(db, row=row, patient=patient)
            if row.source == "verified_document" and lineage is None:
                excluded.append(CandidateEvidenceExclusion(row.id, "verified_lineage_unavailable"))
            entry = CandidateRecordedObservation(
                observation=ObservationSnapshot(
                    id=row.id,
                    patient_id=row.patient_id,
                    measure_type=row.measure_type,
                    value=row.value,
                    unit=row.unit,
                    measured_at=row.measured_at,
                    validation=row.validation,
                    trust_level=row.trust_level,
                ),
                created_at=row.created_at,
                source=row.source,
                source_fact_id=lineage[0] if lineage is not None else None,
                source_document_id=lineage[1] if lineage is not None else None,
                source_fact_verification_status="verified" if lineage is not None else None,
            )
            entries.append(entry)

    return ReadonlyProvenanceEvidence(
        records=tuple(entries),
        lineage_exclusions=tuple(sorted(excluded, key=lambda x: x.observation_id)),
        patient_id=patient.id,
        as_of_utc=clock,
    )


__all__ = ["MAX_OFFLINE_ROWS", "ReadonlyProvenanceEvidence", "load_readonly_provenance_evidence"]
