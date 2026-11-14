"""P1 baseline model: schema metadata only.

``schema_meta`` is a single key/value table used to record which schema baseline
was applied and by which Alembic revision. It supplies the P1 requirement of a
*minimal* initialised database without pre-empting any P2 patient-domain table.

No patient, user, document, observation, review or workflow table is created in
Phase 1 (``docs/contracts/DATA_DICTIONARY.md`` §2 belongs to P2+).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchemaMeta(Base):
    """Key/value record describing the applied schema baseline."""

    __tablename__ = "schema_meta"
    __table_args__ = (
        CheckConstraint("length(key) > 0", name="key_not_empty"),
        CheckConstraint("length(value) > 0", name="value_not_empty"),
    )

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    # Match the baseline migration exactly (``CURRENT_TIMESTAMP``), so Alembic
    # autogenerate reports no spurious diff.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"SchemaMeta(key={self.key!r}, value={self.value!r})"


__all__ = ["SchemaMeta"]
