"""SQLAlchemy declarative base and naming conventions.

An explicit naming convention keeps Alembic autogenerate deterministic and makes
the baseline migration reversible (``AGENTS.md`` §7: migrations are additive and
reversible).

The baseline is intentionally minimal: Phase 1 has **one** table
(``schema_meta``) that records which schema baseline was applied. Patient-domain
tables belong to P2 and must not be created here.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

#: Deterministic constraint naming used by every future migration.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


__all__ = ["NAMING_CONVENTION", "Base"]
