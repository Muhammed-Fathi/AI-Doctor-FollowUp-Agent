"""UTC clock helpers and the injected clock contract.

Every P2 timestamp is stored and transported as UTC ISO-8601 text
``YYYY-MM-DDTHH:MM:SSZ`` (``DATA_DICTIONARY.md`` §1). Wall-clock access is
confined to this module so services can accept an explicit ``now`` value and
tests can inject a fixed clock instead of depending on the machine date
(``AGENTS.md`` §3.2, ``REQ-OPS-04``).

Phase 2 did not need a rule engine, so the demo ``as_of_utc`` evaluation clock
(P4) is not implemented here. Only the primitive is defined: a caller passes a
``datetime`` and never calls the wall clock inside a rule.
"""

from __future__ import annotations

from datetime import UTC, datetime

#: Storage/transport format for every P2 UTC timestamp (``DATA_DICTIONARY.md`` §1).
UTC_ISO_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"

#: Maximum tolerated client clock skew for a check-in ``measured_at``
#: (``DATA_DICTIONARY.md`` §2.8: "must be ≤ now + 5 min").
MAX_FUTURE_SKEW_MINUTES: int = 5


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC ``datetime``.

    This is the only wall-clock read in the P2 code path. Services take ``now``
    as a parameter so callers (and tests) can supply a deterministic value.
    """
    return datetime.now(UTC)


def to_utc(moment: datetime) -> datetime:
    """Normalise ``moment`` to UTC, rejecting naive datetimes.

    Raises:
        ValueError: if ``moment`` carries no timezone information.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return moment.astimezone(UTC)


def format_utc(moment: datetime) -> str:
    """Render ``moment`` in the storage format ``YYYY-MM-DDTHH:MM:SSZ``."""
    normalised = to_utc(moment)
    return normalised.strftime(UTC_ISO_FORMAT)


def parse_utc(value: str) -> datetime:
    """Parse a stored UTC timestamp, accepting a trailing ``Z``.

    Raises:
        ValueError: if the text is not a timezone-aware ISO-8601 timestamp.
    """
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    parsed = datetime.fromisoformat(candidate)
    return to_utc(parsed)


__all__ = [
    "MAX_FUTURE_SKEW_MINUTES",
    "UTC_ISO_FORMAT",
    "format_utc",
    "parse_utc",
    "to_utc",
    "utc_now",
]
