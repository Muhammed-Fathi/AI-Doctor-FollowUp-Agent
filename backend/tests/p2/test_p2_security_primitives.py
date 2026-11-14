"""``AUTH-01`` — salted hashing, token hygiene, bounded login attempts.

Requirement mapping: ``REQ-AUTH-01`` (salted hashing, no plaintext), ``REQ-AUTH-03``
(expiry/revocation primitives), ``AUTH-01`` (hash prefix differs per user, no
plaintext in output), T-16 (bounded attempts).

These are unit tests of ``app.core.security``: they need no database and no HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import (
    PASSWORD_ALGORITHM,
    PASSWORD_ITERATIONS,
    LoginRateLimiter,
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)

NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
DEMO_PASSWORD = "demo" + "-only" + "-secret"


def test_hash_is_salted_so_two_users_never_share_a_digest() -> None:
    """AUTH-01: the same password hashed twice produces different stored values."""
    first = hash_password(DEMO_PASSWORD)
    second = hash_password(DEMO_PASSWORD)

    assert first != second
    assert first.split("$")[2] != second.split("$")[2]


def test_hash_is_verifiable_and_never_contains_the_plaintext() -> None:
    """AUTH-01: verification succeeds and the stored value is opaque."""
    encoded = hash_password(DEMO_PASSWORD)

    assert verify_password(DEMO_PASSWORD, encoded) is True
    assert DEMO_PASSWORD not in encoded
    assert encoded.startswith(f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}$")


def test_wrong_password_is_rejected() -> None:
    """A wrong password never verifies."""
    encoded = hash_password(DEMO_PASSWORD)

    assert verify_password(DEMO_PASSWORD + "x", encoded) is False
    assert verify_password(DEMO_PASSWORD.upper(), encoded) is False


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "not-a-hash",
        "pbkdf2_sha256$notanint$abcd$ef01",
        "pbkdf2_sha256$210000$zz$ef01",
        "md5$1$abcd$ef01",
        "pbkdf2_sha256$0$abcd$ef01",
    ],
)
def test_malformed_stored_hash_is_rejected_without_raising(malformed: str) -> None:
    """A corrupted row returns ``False`` rather than turning into a 500 error."""
    assert verify_password(DEMO_PASSWORD, malformed) is False


def test_empty_password_is_refused_at_hash_time() -> None:
    """No empty credential can be stored."""
    with pytest.raises(ValueError):
        hash_password("")


def test_session_tokens_are_opaque_and_hashed_at_rest() -> None:
    """AUTH-01/AUTH-02: the database digest is not the usable bearer token."""
    raw = generate_session_token()
    digest = hash_session_token(raw)

    assert raw != digest
    assert len(digest) == 64
    assert raw not in digest
    assert digest == hash_session_token(raw)
    assert generate_session_token() != raw


def test_rate_limiter_blocks_after_the_budget() -> None:
    """T-16: the fifth failure blocks the account inside the window."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)

    for _ in range(2):
        limiter.register_failure("demo_doctor", NOW)
        assert limiter.is_blocked("demo_doctor", NOW) is False

    limiter.register_failure("demo_doctor", NOW)
    assert limiter.is_blocked("demo_doctor", NOW) is True


def test_rate_limiter_window_expires_with_the_injected_clock() -> None:
    """The limiter uses the injected clock, not the wall clock."""
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.register_failure("demo_doctor", NOW)

    assert limiter.is_blocked("demo_doctor", NOW + timedelta(seconds=30)) is True
    assert limiter.is_blocked("demo_doctor", NOW + timedelta(seconds=61)) is False


def test_rate_limiter_is_case_insensitive_and_resettable() -> None:
    """Username casing cannot bypass the budget; success clears it."""
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.register_failure("Demo_Doctor", NOW)

    assert limiter.is_blocked("demo_doctor", NOW) is True
    limiter.reset("DEMO_DOCTOR")
    assert limiter.is_blocked("demo_doctor", NOW) is False


#: OWASP Password Storage Cheat Sheet work factor for PBKDF2-HMAC-SHA256.
OWASP_PBKDF2_SHA256_ITERATIONS = 600_000


def test_pbkdf2_work_factor_meets_the_owasp_minimum() -> None:
    """AUTH-01: the stored work factor is the documented SHA-256 recommendation.

    The earlier 210 000 value belongs to PBKDF2-HMAC-SHA512 guidance and was
    flagged in review; 600 000 is the SHA-256 figure.
    """
    assert PASSWORD_ITERATIONS >= OWASP_PBKDF2_SHA256_ITERATIONS

    encoded = hash_password(DEMO_PASSWORD)
    algorithm, iterations, salt_hex, digest_hex = encoded.split("$")

    assert algorithm == PASSWORD_ALGORITHM
    assert int(iterations) == PASSWORD_ITERATIONS
    assert len(bytes.fromhex(salt_hex)) >= 16
    assert len(bytes.fromhex(digest_hex)) == 32  # SHA-256 output


def test_a_stored_hash_verifies_at_its_own_work_factor() -> None:
    """Hash compatibility: verification reads the count from the row, not a constant.

    This is what makes a future work-factor bump or an Argon2id move incremental
    instead of a forced reset.
    """
    legacy = hash_password(DEMO_PASSWORD, iterations=1_000)

    assert verify_password(DEMO_PASSWORD, legacy) is True
    assert verify_password("wrong-password", legacy) is False
    assert needs_rehash(legacy) is True

    current = hash_password(DEMO_PASSWORD)
    assert needs_rehash(current) is False


def test_work_factor_cost_is_bounded_on_this_machine() -> None:
    """A real 600 000-iteration hash+verify stays inside a usable login budget.

    The bound is deliberately generous (seconds, not milliseconds) so the test is
    meaningful on a slow CI box while still catching an accidental 10x increase.
    It measures one hash and one verify only — no database, no HTTP.
    """
    import time

    started = time.perf_counter()
    encoded = hash_password(DEMO_PASSWORD)
    accepted = verify_password(DEMO_PASSWORD, encoded)
    elapsed = time.perf_counter() - started

    assert accepted is True
    assert elapsed < 5.0, f"hash+verify took {elapsed:.2f}s at {PASSWORD_ITERATIONS} iterations"
