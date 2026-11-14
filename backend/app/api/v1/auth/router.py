"""Authentication endpoints: ``/api/v1/auth/login``, ``/me`` and ``/logout``.

Contract: ``API_CONTRACT.md`` §2.2 and ``openapi.phase0.yaml`` operations
``login``, ``getMe`` and ``logout``.

* ``login`` is public, rate limited and answers with the opaque token once.
* ``me`` returns the caller's identity and is the only place a client learns its
  own ``patient_id`` scope; the server never accepts one from the client.
* ``logout`` revokes the current session and returns ``204``; reusing the token
  afterwards is unauthenticated because the session row is revoked.

Passwords and tokens are never logged and never appear in an audit row: only the
username, the outcome and the session id are recorded.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, Security, status

from app.api.v1.auth.dependencies import (
    AppSettings,
    DbSession,
    Now,
    PrincipalDep,
    RateLimiter,
    RequestId,
    bearer_scheme,
)
from app.core.clock import parse_utc
from app.core.errors import UNAUTHENTICATED_DETAIL, ApiError, ErrorCode
from app.db.models import User, UserSession
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.accounts import login as login_service
from app.services.accounts import revoke_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_UNAUTHENTICATED_RESPONSE: dict[int | str, dict[str, object]] = {
    401: {"description": "Not authenticated (uniform body)"}
}


def _user_read(user: User) -> UserRead:
    """Project a stored account into the response model."""
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,  # type: ignore[arg-type]
        patient_id=user.patient_id,
        timezone=user.timezone,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Local demo login",
    description=(
        "Exchange local demo credentials for an opaque bearer session. Rate "
        "limited; every credential failure returns the same 401 body."
    ),
    openapi_extra={"security": []},
    responses={
        401: {"description": "Invalid credentials (uniform body)"},
        429: {"description": "Too many failed attempts"},
    },
)
def login(
    payload: LoginRequest,
    db: DbSession,
    settings: AppSettings,
    limiter: RateLimiter,
    now: Now,
    request_id: RequestId,
) -> TokenResponse:
    """Authenticate and issue a session token."""
    raw_token, session, user = login_service(
        db,
        username=payload.username,
        password=payload.password,
        limiter=limiter,
        now=now,
        ttl_minutes=settings.session_ttl_minutes,
        request_id=request_id,
    )
    return TokenResponse(
        access_token=raw_token,
        token_type="Bearer",
        expires_at=parse_utc(session.expires_at),
        user=_user_read(user),
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Current session identity",
    description="Caller identity and role, resolved from the stored session.",
    dependencies=[Security(bearer_scheme)],
    responses=_UNAUTHENTICATED_RESPONSE,
)
def read_me(principal: PrincipalDep, db: DbSession) -> UserRead:
    """Return the authenticated identity."""
    user = db.get(User, principal.user_id)
    if user is None:  # pragma: no cover - a session always references a user
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, UNAUTHENTICATED_DETAIL)
    return _user_read(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate the current session",
    description="Revokes the bearer session; reuse afterwards returns 401.",
    dependencies=[Security(bearer_scheme)],
    responses={
        204: {"description": "Session invalidated"},
        401: {"description": "Not authenticated (uniform body)"},
    },
)
def logout(
    db: DbSession,
    principal: PrincipalDep,
    now: Now,
    request_id: RequestId,
) -> Response:
    """Revoke the caller's session and return ``204``."""
    session = db.get(UserSession, principal.session_id)
    if session is None:  # pragma: no cover - resolves from the session row itself
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, UNAUTHENTICATED_DETAIL)
    revoke_session(
        db,
        session=session,
        now=now,
        request_id=request_id,
        actor_id=principal.user_id,
        actor_type=principal.actor_type,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
