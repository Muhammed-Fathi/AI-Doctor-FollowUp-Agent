"""P1 baseline: create the ``schema_meta`` table.

Revision ID: 0001_p1_baseline
Revises: None
Create Date: 2026-11-14

Phase 1 scope only. This is the minimal, reversible baseline required to prove
that Alembic can create and drop the application schema. Patient-domain tables
(``DATA_DICTIONARY.md`` §2) are introduced by P2 migrations and must not be
added here.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_p1_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "schema_meta"


def upgrade() -> None:
    """Create the baseline metadata table."""
    op.create_table(
        TABLE,
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("key", name="pk_schema_meta"),
        sa.CheckConstraint("length(key) > 0", name="ck_schema_meta_key_not_empty"),
        sa.CheckConstraint("length(value) > 0", name="ck_schema_meta_value_not_empty"),
    )


def downgrade() -> None:
    """Drop the baseline metadata table (fully reversible)."""
    op.drop_table(TABLE)
