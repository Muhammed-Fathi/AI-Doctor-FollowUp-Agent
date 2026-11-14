"""Local authentication and opaque session lifecycle.

Behaviour fixed by the contracts:

* **Uniform failures.** Unknown username, wrong password, inactive account,
  expired session, revoked session and unknown token all produce the same
  ``401`` envelope wording (``REQ-AUTH-03``, ``NEG-10``). A failed login for an
  unknown user still performs a dummy PBKDF2 verification so the response time
  does not advertise whether the account exists ("constant-time-ish", §2.2).
* **Bounded attempts.** ``LoginRateLimiter`` returns ``429 E_RATE_LIMITED``
  once the configured failure budget for a username is exhausted
  (``REQ-AUTH-03`` / T-16). It is in-process and reset on restart — an honest
  MVP limitation, recorded in the P2 report.
* **Hashed tokens at rest.** The raw token is returned once and never stored;
  the row keeps ``sha256(token)``.
* **No credential in a log or an audit row.** Only the username and a stable
  reason code are recorded, never the submitted password or the token.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import format_utc, parse_utc
from app.core.enums import ActorType, AuditOutcome, Role
from app.core.errors import (
    INVALID_CREDENTIALS_DETAIL,
    UNAUTHENTICATED_DETAIL,
    ApiError,
    ErrorCode,
)
from app.core.policies import Principal
from app.core.security import (
    LoginRateLimiter,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.db.models import User, UserSession, new_uuid
from app.services.audit import EVENT_AUTH_LOGIN, EVENT_AUTH_LOGIN_FAILED, append_audit_event


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A throwaway hash used to equalise the unknown-user login path."""
    return hash_password("synthetic-demo-placeholder")


def normalise_username(username: str) -> str:
    """Normalise a username for lookup (the stored form is lowercase)."""
    return username.strip().lower()


def find_user_by_username(db: Session, username: str) -> User | None:
    """Return the account for ``username`` or ``None``."""
    return db.execute(
        select(User).where(User.username == normalise_username(username))
    ).scalar_one_or_none()


def _invalid_credentials() -> ApiError:
    return ApiError(401, ErrorCode.INVALID_CREDENTIALS, INVALID_CREDENTIALS_DETAIL)


def _unauthenticated() -> ApiError:
    return ApiError(401, ErrorCode.UNAUTHENTICATED, UNAUTHENTICATED_DETAIL)


def authenticate(
    db: Session,
    *,
    username: str,
    password: str,
    limiter: LoginRateLimiter,
    now: datetime,
) -> User:
    """Verify credentials and return the active user.

    Raises:
        ApiError: ``429 E_RATE_LIMITED`` when the attempt budget is exhausted,
            otherwise ``401 E_INVALID_CREDENTIALS`` for any credential failure —
            identical for an unknown account and a wrong password.
    """
    if limiter.is_blocked(username, now):
        raise ApiError(
            429,
            ErrorCode.RATE_LIMITED,
            "Too many failed attempts. Try again later.",
            headers={"Retry-After": str(int(limiter.window_seconds))},
        )

    user = find_user_by_username(db, username)
    if user is None:
        # Dummy verification: same work as a real check, no account enumeration.
        verify_password(password, _dummy_hash())
        limiter.register_failure(username, now)
        raise _invalid_credentials()

    if not verify_password(password, user.password_hash):
        limiter.register_failure(username, now)
        raise _invalid_credentials()

    if not user.is_active:
        # An inactive account is reported exactly like a credential failure.
        limiter.register_failure(username, now)
        raise _invalid_credentials()

    limiter.reset(username)
    return user


def issue_session(
    db: Session,
    *,
    user: User,
    now: datetime,
    ttl_minutes: int,
) -> tuple[str, UserSession]:
    """Create a session row and return ``(raw_token, session)``.

    The raw token is returned to the caller for the response body only; the row
    stores its SHA-256 digest.
    """
    raw_token = generate_session_token()
    session = UserSession(
        id=new_uuid(),
        user_id=user.id,
        token_sha256=hash_session_token(raw_token),
        created_at=format_utc(now),
        expires_at=format_utc(now + timedelta(minutes=ttl_minutes)),
        revoked_at=None,
        last_used_at=None,
    )
    db.add(session)
    user.last_login_at = format_utc(now)
    db.flush()
    return raw_token, session


def login(
    db: Session,
    *,
    username: str,
    password: str,
    limiter: LoginRateLimiter,
    now: datetime,
    ttl_minutes: int,
    request_id: str,
) -> tuple[str, UserSession, User]:
    """Authenticate, audit the attempt and issue a session.

    Returns:
        ``(raw_token, session, user)`` — the token is the only place the caller
        can obtain the raw credential.

    Raises:
        ApiError: propagated from :func:`authenticate` after the audit row for a
            failed attempt has been appended.
    """
    try:
        user = authenticate(db, username=username, password=password, limiter=limiter, now=now)
    except ApiError as error:
        append_audit_event(
            db,
            event_type=EVENT_AUTH_LOGIN_FAILED,
            actor_type=ActorType.USER,
            actor_id=None,
            outcome=AuditOutcome.DENIED if error.status_code == 401 else AuditOutcome.ERROR,
            request_id=request_id,
            now=now,
            subject_type="login",
            subject_id=None,
            detail_fragments=(f"code={error.code.value}",),
        )
        # A failed attempt is evidence: commit before propagating the 401/429 so
        # the request-scoped rollback cannot discard it. No business row is
        # pending on this path.
        db.commit()
        raise

    raw_token, session = issue_session(db, user=user, now=now, ttl_minutes=ttl_minutes)
    append_audit_event(
        db,
        event_type=EVENT_AUTH_LOGIN,
        actor_type=build_principal(user, session).actor_type,
        actor_id=user.id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        subject_type="session",
        subject_id=session.id,
        detail_fragments=("method=password",),
    )
    return raw_token, session, user


def resolve_session(db: Session, *, raw_token: str, now: datetime) -> tuple[UserSession, User]:
    """Resolve a bearer token to its active session and user.

    Raises:
        ApiError: ``401 E_UNAUTHENTICATED`` with the uniform message for a
            missing, unknown, revoked, expired or deactivated session.
    """
    if not raw_token:
        raise _unauthenticated()

    digest = hash_session_token(raw_token)
    session = db.execute(
        select(UserSession).where(UserSession.token_sha256 == digest)
    ).scalar_one_or_none()
    if session is None:
        raise _unauthenticated()

    if session.revoked_at is not None:
        raise _unauthenticated()

    try:
        expires_at = parse_utc(session.expires_at)
    except ValueError:
        # A malformed stored expiry is treated as expired, never as valid.
        raise _unauthenticated() from None

    if expires_at <= now:
        raise _unauthenticated()

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise _unauthenticated()

    session.last_used_at = format_utc(now)
    db.flush()
    return session, user


def build_principal(user: User, session: UserSession) -> Principal:
    """Construct the immutable request principal from stored rows."""
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=Role(user.role),
        patient_id=user.patient_id,
        session_id=session.id,
        timezone=user.timezone,
    )


def revoke_session(
    db: Session,
    *,
    session: UserSession,
    now: datetime,
    request_id: str,
    actor_id: str,
    actor_type: ActorType,
) -> None:
    """Mark a session revoked (logout) and append the audit row.

    Revocation is idempotent: a second logout keeps the original timestamp so the
    audit trail still shows when the session actually ended.
    """
    if session.revoked_at is None:
        session.revoked_at = format_utc(now)
        db.flush()

    append_audit_event(
        db,
        event_type="auth.logout",
        actor_type=actor_type,
        actor_id=actor_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        subject_type="session",
        subject_id=session.id,
        detail_fragments=("revoked=true",),
    )


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Bundle used by routers: the raw identity plus its stored rows."""

    session: UserSession
    user: User
    principal: Principal


__all__ = [
    "SessionContext",
    "authenticate",
    "build_principal",
    "find_user_by_username",
    "issue_session",
    "login",
    "normalise_username",
    "resolve_session",
    "revoke_session",
]
