"""Shared constants and helpers for the Phase 2 test package.

Kept in a plain module (not ``conftest.py``) so the same values can be imported by
every test module without duplicating the clock or the demo password. ``conftest``
puts this directory on ``sys.path`` before importing it, so the import does not
depend on the pytest rootdir layout.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ActorType
from app.db.models import User

#: The injected demo clock used by every P2 test. Later than all seeded values.
FIXED_NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)

#: Local-only demo password used by tests, supplied through the environment.
SEED_PASSWORD = "demo" + "-test-only" + "-0001"

#: Seeded identifiers copied from ``data/synthetic/patients.json`` for assertions.
PATIENT_A_ID = "11111111-1111-4111-8111-111111111111"
PATIENT_B_ID = "22222222-2222-4222-8222-222222222222"
PATIENT_C_ID = "33333333-3333-4333-8333-333333333333"


def bearer(token: str) -> dict[str, str]:
    """Return an ``Authorization`` header carrying ``token``."""
    return {"Authorization": f"Bearer {token}"}


def user_by_username(db: Session, username: str) -> User:
    """Return the seeded account for ``username``."""
    return db.execute(select(User).where(User.username == username)).scalar_one()


def actor_type_for(user: User) -> ActorType:
    """Return the audit actor class for ``user``."""
    return ActorType.DEMO_ADMIN if user.role == "demo_admin" else ActorType.USER


__all__ = [
    "FIXED_NOW",
    "PATIENT_A_ID",
    "PATIENT_B_ID",
    "PATIENT_C_ID",
    "SEED_PASSWORD",
    "actor_type_for",
    "bearer",
    "user_by_username",
]
