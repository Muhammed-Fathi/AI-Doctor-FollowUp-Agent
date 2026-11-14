"""Password hashing, opaque session tokens and the login rate limiter.

Design notes
------------
* **Salted hashing only.** ``DATA_DICTIONARY.md`` §2.1 requires a salted hash and
  forbids plaintext passwords. It names argon2/bcrypt as candidates and leaves
  the choice to P2. Those libraries are **not** current project dependencies, and
  adding one would require ``pyproject.toml`` plus both hash-locked requirement
  files — outside the P2 file scope.

  This module therefore uses the standard library ``hashlib.pbkdf2_hmac`` —
  **PBKDF2-HMAC-SHA256 with 600 000 iterations**, which is the OWASP Password
  Storage Cheat Sheet work factor for SHA-256 (600 000), rather than the older
  210 000 figure that belongs to PBKDF2-HMAC-SHA512. Each password gets a fresh
  16-byte random salt and verification uses ``hmac.compare_digest``. Argon2id
  remains the preferred long-term choice; moving to it is a dependency decision
  for a later phase, and it is *not* blocked by stored data because the encoded
  form is self-describing (algorithm, iteration count and salt are all in the
  string), so old and new rows can coexist and be upgraded on next login via
  :func:`needs_rehash`.

* **No raw session token is stored.** ``issue_session_token`` returns the raw
  token once for the client; the database keeps only its SHA-256 digest
  (``session.token_sha256``), so a database read does not yield usable bearer
  credentials.

* **Nothing here logs.** No password, hash or token is ever passed to a logger
  (``REQ-AUDIT-02``, ``AGENTS.md`` §3.1).

* **Rate limiting is in-process and clock-injected** (``REQ-AUTH-03``/T-16).
  The limiter is keyed by normalised username and evaluated against a caller
  supplied ``now``, so tests are deterministic. It is deliberately simple: the
  MVP is a single-machine, single-process local demo (``ASM-06``); the
  limitation is documented rather than presented as production throttling.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

#: Encoded-hash algorithm label. Part of the stored string so a future
#: algorithm change is detectable per row instead of guessed.
PASSWORD_ALGORITHM: str = "pbkdf2_sha256"

#: PBKDF2-HMAC-SHA256 work factor. Matches the OWASP Password Storage Cheat
#: Sheet recommendation for SHA-256 (600 000). Changing this value does **not**
#: invalidate stored hashes: the count is part of the encoded string and
#: :func:`verify_password` uses the stored count, so a rotation is incremental.
PASSWORD_ITERATIONS: int = 600_000

#: Random salt size in bytes, per user.
SALT_BYTES: int = 16

#: Entropy of an opaque session token in bytes (URL-safe base64 encoded).
TOKEN_BYTES: int = 32

#: Longest password the API will hash (``LoginRequest.password`` maxLength 200).
MAX_PASSWORD_LENGTH: int = 200

_HASH_SEPARATOR = "$"


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = PASSWORD_ITERATIONS,
) -> str:
    """Return a salted, self-describing hash for ``password``.

    The encoded form is ``pbkdf2_sha256$<iterations>$<salt-hex>$<digest-hex>``.
    ``salt`` and ``iterations`` are explicit parameters so tests can pin a cheap
    work factor for speed; production callers omit both and get a fresh random
    salt at :data:`PASSWORD_ITERATIONS`.
    """
    if not password:
        raise ValueError("password must not be empty")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("password is too long")
    if iterations < 1:
        raise ValueError("iterations must be positive")

    chosen_salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    if len(chosen_salt) < SALT_BYTES:
        raise ValueError("salt is too short")

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), chosen_salt, iterations)
    return _HASH_SEPARATOR.join(
        (PASSWORD_ALGORITHM, str(iterations), chosen_salt.hex(), digest.hex())
    )


def verify_password(password: str, encoded: str) -> bool:
    """Return ``True`` when ``password`` matches the stored ``encoded`` hash.

    Malformed or unsupported encodings return ``False`` instead of raising, so a
    corrupted row cannot turn into a 500 response that distinguishes it from a
    normal credential mismatch. The comparison itself is constant-time.
    """
    if not password or len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        algorithm, raw_iterations, salt_hex, digest_hex = encoded.split(_HASH_SEPARATOR)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(raw_iterations)
        if iterations < 1:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False

    if len(salt) < SALT_BYTES or not expected:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(encoded: str) -> bool:
    """Return ``True`` when a stored hash uses weaker parameters than current.

    Used to upgrade a row on its next successful login; it must never be
    consulted to decide whether a login is *allowed*, only whether to rewrite the
    stored value afterwards. Malformed encodings report ``False`` because
    :func:`verify_password` already rejects them.
    """
    try:
        algorithm, raw_iterations, salt_hex, digest_hex = encoded.split(_HASH_SEPARATOR)
        iterations = int(raw_iterations)
        bytes.fromhex(salt_hex)
        bytes.fromhex(digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False
    if algorithm != PASSWORD_ALGORITHM:
        # A different (future) algorithm is not "weaker"; leave it alone here.
        return False
    return iterations < PASSWORD_ITERATIONS


def generate_session_token() -> str:
    """Return a fresh opaque, URL-safe session token (never persisted raw)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_session_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest stored in ``session.token_sha256``."""
    if not raw_token:
        raise ValueError("session token must not be empty")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass
class _AttemptWindow:
    """Failure timestamps recorded for one limiter key."""

    failures: list[datetime] = field(default_factory=list)


class LoginRateLimiter:
    """Bounded, in-process failure counter for local demo login.

    A key is blocked once it has ``max_attempts`` failures inside
    ``window_seconds``. Evaluation uses the caller's ``now``, never the wall
    clock, so the behaviour is reproducible in tests.
    """

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 300) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if window_seconds < 1:
            raise ValueError("window_seconds must be positive")
        self._max_attempts = max_attempts
        self._window = timedelta(seconds=window_seconds)
        self._windows: dict[str, _AttemptWindow] = {}

    @property
    def max_attempts(self) -> int:
        """Number of failures tolerated inside the window."""
        return self._max_attempts

    @property
    def window_seconds(self) -> float:
        """Length of the rolling window in seconds."""
        return self._window.total_seconds()

    @staticmethod
    def _key(username: str) -> str:
        return username.strip().lower()

    def _recent(self, key: str, now: datetime) -> list[datetime]:
        window = self._windows.get(key)
        if window is None:
            return []
        cutoff = now - self._window
        window.failures = [moment for moment in window.failures if moment > cutoff]
        return window.failures

    def is_blocked(self, username: str, now: datetime) -> bool:
        """Return ``True`` when this key has exhausted its allowance."""
        return len(self._recent(self._key(username), now)) >= self._max_attempts

    def register_failure(self, username: str, now: datetime) -> None:
        """Record one failed attempt for ``username`` at ``now``."""
        key = self._key(username)
        self._recent(key, now)
        self._windows.setdefault(key, _AttemptWindow()).failures.append(now)

    def reset(self, username: str) -> None:
        """Clear the failure history for ``username`` (called on success)."""
        self._windows.pop(self._key(username), None)

    def clear(self) -> None:
        """Drop every recorded failure (used by tests and demo reset)."""
        self._windows.clear()


__all__ = [
    "MAX_PASSWORD_LENGTH",
    "PASSWORD_ALGORITHM",
    "PASSWORD_ITERATIONS",
    "SALT_BYTES",
    "TOKEN_BYTES",
    "LoginRateLimiter",
    "generate_session_token",
    "hash_password",
    "hash_session_token",
    "verify_password",
]
