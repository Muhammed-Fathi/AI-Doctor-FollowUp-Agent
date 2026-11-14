"""Doctor-facing patient reads (``API_CONTRACT.md`` §2.1).

Four operations, all assignment-scoped on the server:

``GET /api/v1/doctor/patients``
    The patients assigned to the caller.
``GET /api/v1/doctor/patients/{patient_id}``
    The patient header (counts only, no measurements).
``GET /api/v1/doctor/patients/{patient_id}/timeline``
    Observations newest-first plus ``documents``/``review_items``/``tasks``, which
    are **always empty in P2** because those phases do not exist yet.
``GET /api/v1/doctor/patients/{patient_id}/observations``
    A filtered, cursor-paginated observation series.

Authorization is never derived from the request: the assignment is read from
``patient.assigned_doctor_id`` by ``services.patients``, so a body or query
parameter cannot widen scope. A denied attempt appends an ``access.denied`` audit
row before the ``403`` is returned (``AUD-01``).
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Security

from app.api.v1.auth.dependencies import DbSession, Now, PrincipalDep, RequestId, bearer_scheme
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.schemas.observation import ObservationList
from app.schemas.patient import PatientList, PatientRead, Timeline
from app.services.patients import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    list_assigned_patients,
    list_patient_observations,
    parse_bound,
    patient_header,
    patient_timeline,
    validate_patient_id,
)

router = APIRouter(
    prefix="/api/v1/doctor",
    tags=["doctor"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_PATIENTS = "GET /api/v1/doctor/patients"
ROUTE_PATIENT = "GET /api/v1/doctor/patients/{patient_id}"
ROUTE_TIMELINE = "GET /api/v1/doctor/patients/{patient_id}/timeline"
ROUTE_OBSERVATIONS = "GET /api/v1/doctor/patients/{patient_id}/observations"

_SCOPED_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"description": "Not authenticated (uniform body)"},
    403: {"description": "Caller is not the assigned doctor"},
    404: {"description": "Patient does not exist"},
}


def _require_doctor(principal: Principal) -> None:
    """Reject a non-doctor caller with the role error, not a scope error.

    The service layer repeats this check, so a direct service call is equally
    safe; doing it here keeps the ``403 E_FORBIDDEN`` answer (role) distinct from
    ``403 E_SCOPE_VIOLATION`` (assignment), which is what
    ``ARCHITECTURE.md`` §6 describes.
    """
    from app.core.policies import require_doctor

    require_doctor(principal)


@router.get(
    "/patients",
    response_model=PatientList,
    summary="Patients assigned to the caller",
    description=(
        "Assignment-scoped list. An unassigned doctor receives an empty page, "
        "never somebody else's patients."
    ),
    responses=_SCOPED_RESPONSES,
)
def read_patients(
    principal: PrincipalDep,
    db: DbSession,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None, max_length=200),
) -> PatientList:
    """Return a page of the caller's patients."""
    _require_doctor(principal)
    return list_assigned_patients(db, principal=principal, limit=limit, cursor=cursor)


@router.get(
    "/patients/{patient_id}",
    response_model=PatientRead,
    summary="Patient header",
    description="Counts and synthetic-data labels only; no measurement values.",
    responses=_SCOPED_RESPONSES,
)
def read_patient(
    patient_id: str,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
) -> PatientRead:
    """Return one patient header if the caller is assigned to that patient."""
    _require_doctor(principal)
    return patient_header(
        db,
        principal=principal,
        patient_id=validate_patient_id(patient_id),
        route=ROUTE_PATIENT,
        request_id=request_id,
        now=now,
    )


@router.get(
    "/patients/{patient_id}/timeline",
    response_model=Timeline,
    summary="Patient timeline",
    description=(
        "Observations newest-first. `documents`, `review_items` and `tasks` are "
        "empty in P2: those phases are not implemented and nothing is fabricated."
    ),
    responses=_SCOPED_RESPONSES,
)
def read_timeline(
    patient_id: str,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
) -> Timeline:
    """Return the patient timeline for the assigned doctor."""
    _require_doctor(principal)
    return patient_timeline(
        db,
        principal=principal,
        patient_id=validate_patient_id(patient_id),
        route=ROUTE_TIMELINE,
        request_id=request_id,
        now=now,
    )


@router.get(
    "/patients/{patient_id}/observations",
    response_model=ObservationList,
    summary="Patient observation series",
    description=(
        "Cursor-paginated observations. `measure_type`, `from` and `to` filter "
        "server-side; rows with `validation='rejected'` are never returned."
    ),
    responses=_SCOPED_RESPONSES,
)
def read_observations(
    patient_id: str,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
    measure_type: str | None = Query(default=None, max_length=24),
    from_: str | None = Query(default=None, alias="from", max_length=40),
    to: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None, max_length=200),
) -> ObservationList:
    """Return a filtered observation page for the assigned doctor."""
    _require_doctor(principal)
    from app.core.enums import MeasureType

    parsed_type: MeasureType | None = None
    if measure_type is not None:
        try:
            parsed_type = MeasureType(measure_type)
        except ValueError as error:
            raise ApiError(
                400,
                ErrorCode.VALIDATION,
                "Measure type is not one of the supported measurements.",
                details=[
                    {
                        "field": "measure_type",
                        "message": f"Unsupported value {measure_type!r}.",
                    }
                ],
            ) from error

    return list_patient_observations(
        db,
        principal=principal,
        patient_id=validate_patient_id(patient_id),
        route=ROUTE_OBSERVATIONS,
        request_id=request_id,
        now=now,
        measure_type=parsed_type,
        from_=parse_bound(from_, field="from"),
        to=parse_bound(to, field="to"),
        limit=limit,
        cursor=cursor,
    )


__all__ = [
    "ROUTE_OBSERVATIONS",
    "ROUTE_PATIENT",
    "ROUTE_PATIENTS",
    "ROUTE_TIMELINE",
    "router",
]
