"""Patient check-in routes (``API_CONTRACT.md`` §1, §2.4).

``POST /api/v1/patient/check-ins``
    Self-scoped write. The patient identity comes from the bearer session; a body
    field cannot select another patient. ``Idempotency-Key`` makes the write
    replay-safe (``NEG-13`` durability, §1 semantics):

    * first use → ``201`` and the stored observation,
    * exact replay → ``201`` and the **same** observation (``created=False``),
    * same key, different body → ``409 E_IDEMPOTENCY_CONFLICT``,
    * identical measurement with a new/no key → ``409 E_DUPLICATE_CHECKIN``.

``GET /api/v1/patient/check-ins``
    The caller's own check-ins, newest-first and cursor-paginated.

Provenance is derived server-side: ``trust_level`` is always
``self_reported_validated`` and the request schema forbids client-supplied
``trust_level``/``verification`` fields (``REQ-DATA-04``).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, Query, Response, Security, status

from app.api.v1.auth.dependencies import DbSession, Now, PrincipalDep, RequestId, bearer_scheme
from app.schemas.observation import CheckInCreate, ObservationList, ObservationRead
from app.services.checkins import create_check_in, list_own_check_ins
from app.services.patients import DEFAULT_LIMIT, MAX_LIMIT

router = APIRouter(
    prefix="/api/v1/patient",
    tags=["patient"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_CHECKINS = "POST /api/v1/patient/check-ins"

_RESPONSES: dict[int | str, dict[str, object]] = {
    400: {"description": "Validation error or unit not allowed"},
    401: {"description": "Not authenticated (uniform body)"},
    403: {"description": "Caller is not a patient"},
    409: {"description": "Duplicate check-in or conflicting idempotency key"},
}


@router.post(
    "/check-ins",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a self-reported measurement",
    description=(
        "Stores a check-in for the authenticated patient. Replaying the same "
        "`Idempotency-Key` returns the original observation instead of creating "
        "a second one."
    ),
    responses=_RESPONSES,
)
def submit_check_in(
    payload: CheckInCreate,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ObservationRead:
    """Create (or replay) one check-in."""
    observation, created = create_check_in(
        db,
        principal=principal,
        payload=payload,
        idempotency_key=idempotency_key,
        now=now,
        request_id=request_id,
    )
    if not created:
        # A replay is not a creation; say so in a header rather than a 200 body
        # change, so a client can detect it without parsing prose.
        response.headers["Idempotent-Replay"] = "true"
    return observation


@router.get(
    "/check-ins",
    response_model=ObservationList,
    summary="The caller's own check-ins",
    description="Newest-first, cursor-paginated, self-scoped.",
    responses={
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Caller is not a patient"},
    },
)
def read_own_check_ins(
    principal: PrincipalDep,
    db: DbSession,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None, max_length=200),
) -> ObservationList:
    """Return the caller's own check-in page."""
    return list_own_check_ins(db, principal=principal, limit=limit, cursor=cursor)


__all__ = ["ROUTE_CHECKINS", "router"]
