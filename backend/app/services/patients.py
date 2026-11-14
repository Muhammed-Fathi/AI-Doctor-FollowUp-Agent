"""Doctor-scoped patient reads: list, header, timeline and observation series.

Every function here resolves the patient row from the database and compares its
stored ``assigned_doctor_id`` with the authenticated user id. A patient id from
the path is only ever an **address**, never evidence of authorization
(``THREAT_MODEL.md`` T-01).

Denial behaviour:

* unknown patient id → ``404 E_NOT_FOUND`` (nothing is acknowledged),
* known patient outside the doctor's assignment → ``403 E_SCOPE_VIOLATION``,
* either way the denial is appended to the audit trail with the route template
  and a reason code, never with the requested record's content
  (``REQ-AUDIT-01``, ``AUD-01``).

Series semantics: ``GET .../observations`` is the admissible series that P4
comparisons will build on, so rows with ``validation='rejected'`` are excluded
there. ``GET .../timeline`` is the record view and includes every row with its
``validation`` label, so a doctor can see that a rejected entry exists instead of
it disappearing silently.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc
from app.core.enums import MeasureType, ValidationState
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_assigned_patient, require_doctor
from app.db.models import Observation, Patient
from app.schemas.observation import ObservationList
from app.schemas.patient import PatientList, PatientRead, Timeline
from app.services.audit import REASON_NOT_ASSIGNED, record_denial
from app.services.checkins import observation_to_read
from app.services.pagination import decode_cursor, encode_cursor

#: Default and maximum page size (``API_CONTRACT.md`` §1).
DEFAULT_LIMIT: int = 20
MAX_LIMIT: int = 100


def validate_patient_id(raw: str) -> str:
    """Validate a path ``patient_id`` as a UUID, raising ``400 E_VALIDATION``."""
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "patient_id must be a UUID.") from None


def _clamp_limit(limit: int) -> int:
    """Clamp a page size into the contract range."""
    if limit < 1:
        raise ApiError(400, ErrorCode.VALIDATION, "limit must be between 1 and 100.")
    return min(limit, MAX_LIMIT)


def _get_scoped_patient(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    route: str,
    request_id: str,
    now: datetime,
) -> Patient:
    """Return the patient when the doctor is assigned, else raise and audit."""
    require_doctor(principal)
    patient = db.get(Patient, validate_patient_id(patient_id))
    if patient is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Patient not found.")

    try:
        require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
    except ApiError:
        record_denial(
            db,
            actor_type=principal.actor_type,
            actor_id=principal.user_id,
            route=route,
            reason=REASON_NOT_ASSIGNED,
            request_id=request_id,
            now=now,
            patient_id=patient.id,
            subject_type="patient",
            subject_id=patient.id,
        )
        raise
    return patient


def list_assigned_patients(
    db: Session,
    *,
    principal: Principal,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> PatientList:
    """List only the patients assigned to the authenticated doctor."""
    require_doctor(principal)
    page_size = _clamp_limit(limit)

    statement = select(Patient).where(Patient.assigned_doctor_id == principal.user_id)
    if cursor:
        external_ref, row_id = decode_cursor(cursor)
        statement = statement.where(
            or_(
                Patient.external_ref > external_ref,
                and_(Patient.external_ref == external_ref, Patient.id > row_id),
            )
        )
    statement = statement.order_by(Patient.external_ref.asc(), Patient.id.asc()).limit(
        page_size + 1
    )

    rows = list(db.execute(statement).scalars().all())
    has_more = len(rows) > page_size
    page = rows[:page_size]

    items = [
        PatientRead(
            id=patient.id,
            display_name=patient.display_name,
            external_ref=patient.external_ref or "",
            data_source="synthetic_fixture",
            date_of_birth=patient.date_of_birth,
            observation_count=_admissible_observation_count(db, patient.id),
            document_count=0,
            open_review_item_count=0,
        )
        for patient in page
    ]
    next_cursor = (
        encode_cursor(page[-1].external_ref or "", page[-1].id) if has_more and page else None
    )
    return PatientList(items=items, next_cursor=next_cursor)


def _admissible_observation_count(db: Session, patient_id: str) -> int:
    """Count observations a future comparison may consume."""
    statement = (
        select(func.count())
        .select_from(Observation)
        .where(
            Observation.patient_id == patient_id,
            Observation.validation != ValidationState.REJECTED.value,
        )
    )
    return int(db.execute(statement).scalar_one())


def patient_header(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    route: str,
    request_id: str,
    now: datetime,
) -> PatientRead:
    """Return the patient header with record counts."""
    patient = _get_scoped_patient(
        db, principal=principal, patient_id=patient_id, route=route, request_id=request_id, now=now
    )
    return PatientRead(
        id=patient.id,
        display_name=patient.display_name,
        external_ref=patient.external_ref or "",
        data_source="synthetic_fixture",
        date_of_birth=patient.date_of_birth,
        observation_count=_admissible_observation_count(db, patient.id),
        # Documents arrive in P3 and review items in P4; reporting a count here
        # would require tables that do not exist yet.
        document_count=0,
        open_review_item_count=0,
    )


def patient_timeline(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    route: str,
    request_id: str,
    now: datetime,
) -> Timeline:
    """Return the longitudinal record view for an assigned patient."""
    patient = _get_scoped_patient(
        db, principal=principal, patient_id=patient_id, route=route, request_id=request_id, now=now
    )
    statement = (
        select(Observation)
        .where(Observation.patient_id == patient.id)
        .order_by(Observation.measured_at.desc(), Observation.id.desc())
    )
    rows = list(db.execute(statement).scalars().all())
    return Timeline(
        patient_id=patient.id,
        observations=[observation_to_read(row) for row in rows],
        documents=[],
        review_items=[],
        tasks=[],
    )


def list_patient_observations(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    route: str,
    request_id: str,
    now: datetime,
    measure_type: MeasureType | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> ObservationList:
    """Return the admissible observation series for an assigned patient."""
    patient = _get_scoped_patient(
        db, principal=principal, patient_id=patient_id, route=route, request_id=request_id, now=now
    )
    page_size = _clamp_limit(limit)

    if from_ is not None and to is not None and from_ > to:
        raise ApiError(400, ErrorCode.VALIDATION, "from must not be after to.")

    statement = select(Observation).where(
        Observation.patient_id == patient.id,
        Observation.validation != ValidationState.REJECTED.value,
    )
    if measure_type is not None:
        statement = statement.where(Observation.measure_type == measure_type.value)
    if from_ is not None:
        statement = statement.where(Observation.measured_at >= format_utc(from_))
    if to is not None:
        statement = statement.where(Observation.measured_at <= format_utc(to))
    if cursor:
        measured_at, row_id = decode_cursor(cursor)
        statement = statement.where(
            or_(
                Observation.measured_at < measured_at,
                and_(Observation.measured_at == measured_at, Observation.id < row_id),
            )
        )
    statement = statement.order_by(Observation.measured_at.desc(), Observation.id.desc()).limit(
        page_size + 1
    )

    rows = list(db.execute(statement).scalars().all())
    has_more = len(rows) > page_size
    page = rows[:page_size]
    next_cursor = encode_cursor(page[-1].measured_at, page[-1].id) if has_more and page else None
    return ObservationList(
        items=[observation_to_read(row) for row in page], next_cursor=next_cursor
    )


def parse_bound(value: str | None, *, field: str) -> datetime | None:
    """Parse an optional ISO-8601 query bound, raising ``400 E_VALIDATION``."""
    if value is None or not value.strip():
        return None
    try:
        return parse_utc(value)
    except ValueError:
        raise ApiError(
            400, ErrorCode.VALIDATION, f"{field} must be an ISO-8601 UTC timestamp."
        ) from None


__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "list_assigned_patients",
    "list_patient_observations",
    "parse_bound",
    "patient_header",
    "patient_timeline",
    "validate_patient_id",
]
