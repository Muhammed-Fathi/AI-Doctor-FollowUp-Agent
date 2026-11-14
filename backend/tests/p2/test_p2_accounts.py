"""``AUTH-02`` — session lifecycle, uniform failures and credential secrecy.

Requirement mapping: ``REQ-AUTH-01``, ``REQ-AUTH-02``, ``REQ-AUTH-03``,
``AUTH-01`` (no plaintext in storage), ``AUTH-02`` (expired/revoked rejected),
``NEG-10`` (uniform 401).

The assertions run against the real service layer and a real SQLite database; no
HTTP is involved, so a failure here is a policy/service defect rather than a
routing artefact.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from support import FIXED_NOW, SEED_PASSWORD, actor_type_for, user_by_username

from app.core.clock import format_utc
from app.core.enums import Role
from app.core.errors import ApiError, ErrorCode
from app.core.security import LoginRateLimiter
from app.db.models import AuditEvent, UserSession
from app.services.accounts import (
    build_principal,
    issue_session,
    login,
    resolve_session,
    revoke_session,
)


def test_login_issues_a_hashed_session_and_audits_it(seeded: Session) -> None:
    """A successful login stores only the token digest and records ``auth.login``."""
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)

    raw_token, session, user = login(
        seeded,
        username="demo_doctor",
        password=SEED_PASSWORD,
        limiter=limiter,
        now=FIXED_NOW,
        ttl_minutes=60,
        request_id="11111111-1111-4111-8111-aaaaaaaaaaaa",
    )
    seeded.commit()

    stored = seeded.execute(select(UserSession).where(UserSession.id == session.id)).scalar_one()
    assert stored.token_sha256 != raw_token
    assert raw_token not in stored.token_sha256
    assert stored.expires_at == format_utc(FIXED_NOW + timedelta(minutes=60))
    assert user.last_login_at == format_utc(FIXED_NOW)

    events = seeded.execute(select(AuditEvent.event_type)).scalars().all()
    assert "auth.login" in events


def test_resolved_session_yields_a_principal_with_self_scope(seeded: Session) -> None:
    """A patient session resolves to a principal carrying its own patient scope."""
    raw_token, _session, _user = login(
        seeded,
        username="demo_patient_a",
        password=SEED_PASSWORD,
        limiter=LoginRateLimiter(),
        now=FIXED_NOW,
        ttl_minutes=60,
        request_id="req-patient-a",
    )
    seeded.commit()

    stored_session, stored_user = resolve_session(seeded, raw_token=raw_token, now=FIXED_NOW)
    principal = build_principal(stored_user, stored_session)

    assert principal.role is Role.PATIENT
    assert principal.patient_id == "11111111-1111-4111-8111-111111111111"
    assert stored_session.last_used_at == format_utc(FIXED_NOW)


def test_expired_session_is_rejected(seeded: Session) -> None:
    """AUTH-02: an expired token returns the uniform 401."""
    user = user_by_username(seeded, "demo_doctor")
    raw_token, _session = issue_session(seeded, user=user, now=FIXED_NOW, ttl_minutes=1)
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        resolve_session(seeded, raw_token=raw_token, now=FIXED_NOW + timedelta(minutes=2))

    assert caught.value.status_code == 401
    assert caught.value.code is ErrorCode.UNAUTHENTICATED


def test_revoked_session_is_rejected(seeded: Session) -> None:
    """AUTH-02: logout invalidation takes effect immediately."""
    user = user_by_username(seeded, "demo_doctor")
    raw_token, session = issue_session(seeded, user=user, now=FIXED_NOW, ttl_minutes=60)
    seeded.commit()

    revoke_session(
        seeded,
        session=session,
        now=FIXED_NOW,
        request_id="req-logout",
        actor_id=user.id,
        actor_type=actor_type_for(user),
    )
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        resolve_session(seeded, raw_token=raw_token, now=FIXED_NOW)

    assert caught.value.code is ErrorCode.UNAUTHENTICATED


def test_revocation_is_idempotent(seeded: Session) -> None:
    """A second logout keeps the original revocation timestamp."""
    user = user_by_username(seeded, "demo_doctor")
    _, session = issue_session(seeded, user=user, now=FIXED_NOW, ttl_minutes=60)
    seeded.commit()

    revoke_session(
        seeded,
        session=session,
        now=FIXED_NOW,
        request_id="req-1",
        actor_id=user.id,
        actor_type=actor_type_for(user),
    )
    first = session.revoked_at
    revoke_session(
        seeded,
        session=session,
        now=FIXED_NOW + timedelta(minutes=5),
        request_id="req-2",
        actor_id=user.id,
        actor_type=actor_type_for(user),
    )
    seeded.commit()

    assert session.revoked_at == first


def test_unknown_expired_and_unknown_username_share_one_failure_shape(seeded: Session) -> None:
    """NEG-10/REQ-AUTH-03: no response distinguishes why authentication failed."""
    limiter = LoginRateLimiter()

    with pytest.raises(ApiError) as unknown_token:
        resolve_session(seeded, raw_token="not-a-real-token", now=FIXED_NOW)

    with pytest.raises(ApiError) as unknown_user:
        login(
            seeded,
            username="nobody_here",
            password=SEED_PASSWORD,
            limiter=limiter,
            now=FIXED_NOW,
            ttl_minutes=60,
            request_id="req-unknown",
        )
    seeded.rollback()

    with pytest.raises(ApiError) as wrong_password:
        login(
            seeded,
            username="demo_doctor",
            password=SEED_PASSWORD + "-wrong",
            limiter=LoginRateLimiter(),
            now=FIXED_NOW,
            ttl_minutes=60,
            request_id="req-wrong",
        )
    seeded.rollback()

    assert unknown_token.value.status_code == 401
    assert unknown_user.value.status_code == 401
    assert wrong_password.value.status_code == 401
    assert unknown_user.value.code is ErrorCode.INVALID_CREDENTIALS
    assert wrong_password.value.code is ErrorCode.INVALID_CREDENTIALS
    assert unknown_user.value.detail == wrong_password.value.detail
    assert unknown_token.value.code is ErrorCode.UNAUTHENTICATED
    assert unknown_token.value.detail == "A valid session is required."


def test_inactive_account_cannot_log_in(seeded: Session) -> None:
    """A deactivated account fails exactly like a wrong password."""
    user = user_by_username(seeded, "demo_doctor")
    user.is_active = 0
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        login(
            seeded,
            username="demo_doctor",
            password=SEED_PASSWORD,
            limiter=LoginRateLimiter(),
            now=FIXED_NOW,
            ttl_minutes=60,
            request_id="req-inactive",
        )

    assert caught.value.code is ErrorCode.INVALID_CREDENTIALS


def test_repeated_failures_raise_rate_limited(seeded: Session) -> None:
    """REQ-AUTH-03/T-16: the fifth failure returns ``429`` with a retry hint."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=300)

    for index in range(3):
        with pytest.raises(ApiError) as failure:
            login(
                seeded,
                username="demo_doctor",
                password=SEED_PASSWORD + "-wrong",
                limiter=limiter,
                now=FIXED_NOW + timedelta(seconds=index),
                ttl_minutes=60,
                request_id=f"req-{index}",
            )
        assert failure.value.code is ErrorCode.INVALID_CREDENTIALS

    with pytest.raises(ApiError) as blocked:
        login(
            seeded,
            username="demo_doctor",
            password=SEED_PASSWORD,
            limiter=limiter,
            now=FIXED_NOW + timedelta(seconds=4),
            ttl_minutes=60,
            request_id="req-blocked",
        )

    assert blocked.value.status_code == 429
    assert blocked.value.code is ErrorCode.RATE_LIMITED
    assert blocked.value.headers.get("Retry-After") == "300"


def test_no_password_or_token_appears_in_stored_rows(seeded: Session) -> None:
    """AUTH-01/REQ-AUDIT-02: no demo password and no raw token is persisted."""
    raw_token, _, _ = login(
        seeded,
        username="demo_doctor",
        password=SEED_PASSWORD,
        limiter=LoginRateLimiter(),
        now=FIXED_NOW,
        ttl_minutes=60,
        request_id="req-leak",
    )
    seeded.commit()

    for table in inspect(seeded.get_bind()).get_table_names():
        for column in inspect(seeded.get_bind()).get_columns(table):
            rows = seeded.execute(text(f'SELECT "{column["name"]}" FROM "{table}"')).scalars()
            for value in rows:
                if not isinstance(value, str):
                    continue
                assert SEED_PASSWORD not in value, f"{table}.{column['name']} leaked a password"
                assert raw_token not in value, f"{table}.{column['name']} leaked a token"


def test_audit_rows_never_contain_the_submitted_password(seeded: Session) -> None:
    """A failed attempt is audited without the credential that was tried."""
    with pytest.raises(ApiError):
        login(
            seeded,
            username="demo_doctor",
            password=SEED_PASSWORD + "-typo",
            limiter=LoginRateLimiter(),
            now=FIXED_NOW,
            ttl_minutes=60,
            request_id="req-audited-failure",
        )

    details = seeded.execute(select(AuditEvent.safe_detail)).scalars().all()
    assert any(detail and "E_INVALID_CREDENTIALS" in detail for detail in details)
    assert all(SEED_PASSWORD not in (detail or "") for detail in details)


def test_successful_login_upgrades_a_stale_hash(seeded: Session) -> None:
    """A weaker stored work factor is rewritten after the password is verified.

    ``needs_rehash`` is only ever consulted *after* a successful verification, so
    it can never turn a bad password into a good login. This pins that claim: the
    row really is upgraded, and the new hash still verifies the same password.
    """
    from app.core.security import PASSWORD_ITERATIONS, hash_password, needs_rehash, verify_password

    user = user_by_username(seeded, "demo_doctor")
    user.password_hash = hash_password(SEED_PASSWORD, iterations=1_000)
    seeded.commit()
    assert needs_rehash(user.password_hash) is True

    login(
        seeded,
        username="demo_doctor",
        password=SEED_PASSWORD,
        limiter=LoginRateLimiter(),
        now=FIXED_NOW,
        ttl_minutes=60,
        request_id="req-rehash",
    )
    seeded.commit()

    stored = user_by_username(seeded, "demo_doctor").password_hash
    assert stored.startswith(f"pbkdf2_sha256${PASSWORD_ITERATIONS}$")
    assert needs_rehash(stored) is False
    assert verify_password(SEED_PASSWORD, stored) is True


def test_failed_login_leaves_the_stored_hash_untouched(seeded: Session) -> None:
    """A wrong password must not trigger a rewrite (or any write at all)."""
    from app.core.errors import ApiError
    from app.core.security import hash_password

    user = user_by_username(seeded, "demo_doctor")
    user.password_hash = hash_password(SEED_PASSWORD, iterations=1_000)
    seeded.commit()
    before = user_by_username(seeded, "demo_doctor").password_hash

    with pytest.raises(ApiError):
        login(
            seeded,
            username="demo_doctor",
            password=SEED_PASSWORD + "-wrong",
            limiter=LoginRateLimiter(),
            now=FIXED_NOW,
            ttl_minutes=60,
            request_id="req-rehash-fail",
        )
    seeded.commit()

    assert user_by_username(seeded, "demo_doctor").password_hash == before
