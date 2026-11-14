"""FastAPI dependencies for the P2 authentication surface.

Only three things are resolved here, all from server-side state:

* the current UTC time (:func:`current_time`) — injected so tests can freeze it,
* the active session and its user (:func:`current_identity`), and
* the immutable :class:`Principal` used by every authorization check.

The bearer token is read from the ``Authorization`` header only. No cookie, no
query parameter and no body field can authenticate a request, which keeps the
surface small and matches ``OQ-A01``'s default (bearer header for the MVP).

Every failure raises the uniform ``401`` envelope with a ``WWW-Authenticate``
header, so a caller cannot distinguish "no token" from "expired token" from
"unknown token".
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import Settings, get_settings
from app.core.errors import UNAUTHENTICATED_DETAIL, ApiError, ErrorCode, request_id_for
from app.core.policies import Principal
from app.core.security import LoginRateLimiter
from app.db.models import UserSession
from app.db.session import get_db_session
from app.services.accounts import build_principal, resolve_session

#: Database session dependency.
DbSession = Annotated[Session, Depends(get_db_session)]

#: Application settings dependency.
AppSettings = Annotated[Settings, Depends(get_settings)]


def current_time() -> datetime:
    """Return the current UTC time through a single, replaceable seam."""
    return utc_now()


#: Injected clock dependency.
Now = Annotated[datetime, Depends(current_time)]


def current_request_id(request: Request) -> str:
    """Return the correlation id for this request (audit + problem envelope)."""
    return request_id_for(request)


#: Request correlation id dependency.
RequestId = Annotated[str, Depends(current_request_id)]


def login_rate_limiter(settings: AppSettings) -> LoginRateLimiter:
    """Return the process-wide login failure counter.

    The limiter is a module-level singleton because throttling must be shared
    across requests; it is rebuilt whenever the settings object changes so a test
    can pick different limits without leaking state between cases.
    """
    return _limiter_for(
        settings.login_rate_limit_attempts,
        settings.login_rate_limit_window_seconds,
    )


_limiter_cache: dict[tuple[int, int], LoginRateLimiter] = {}


def _limiter_for(max_attempts: int, window_seconds: int) -> LoginRateLimiter:
    key = (max_attempts, window_seconds)
    limiter = _limiter_cache.get(key)
    if limiter is None:
        limiter = LoginRateLimiter(max_attempts=max_attempts, window_seconds=window_seconds)
        _limiter_cache[key] = limiter
    return limiter


def clear_limiter_cache() -> None:
    """Drop every cached limiter (tests and demo reset)."""
    for limiter in _limiter_cache.values():
        limiter.clear()
    _limiter_cache.clear()


#: Login rate-limit dependency.
RateLimiter = Annotated[LoginRateLimiter, Depends(login_rate_limiter)]


def _bearer_token(request: Request) -> str:
    """Extract a bearer token, rejecting any other scheme."""
    header = request.headers.get("Authorization", "")
    scheme, _, credentials = header.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise ApiError(
            401,
            ErrorCode.UNAUTHENTICATED,
            UNAUTHENTICATED_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.strip()


def current_session(db: DbSession, now: Now, request: Request) -> tuple[UserSession, object]:
    """Resolve the bearer token to its session and user rows."""
    raw_token = _bearer_token(request)
    try:
        return resolve_session(db, raw_token=raw_token, now=now)
    except ApiError as error:
        # Attach the scheme hint without changing the uniform message.
        error.headers.setdefault("WWW-Authenticate", "Bearer")
        raise


def current_principal(
    db: DbSession,
    now: Now,
    request: Request,
) -> Principal:
    """Return the authenticated principal, or raise the uniform ``401``."""
    session, user = current_session(db, now, request)
    return build_principal(user, session)  # type: ignore[arg-type]


#: Authenticated principal dependency.
PrincipalDep = Annotated[Principal, Depends(current_principal)]


__all__ = [
    "AppSettings",
    "DbSession",
    "Now",
    "PrincipalDep",
    "RateLimiter",
    "RequestId",
    "clear_limiter_cache",
    "current_principal",
    "current_request_id",
    "current_session",
    "current_time",
    "login_rate_limiter",
]
