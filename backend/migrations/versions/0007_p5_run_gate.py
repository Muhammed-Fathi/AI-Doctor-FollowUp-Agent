"""P5-F1 run-bound immutable gate evidence (not graph execution).

Two additive, strictly typed tables. The pre-existing P3 document issues
and the F0 run manifest remain untouched. Refuse destructive downgrade
whenever gate evidence exists. SYNTHETIC / NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_p5_run_gate"
down_revision: str | None = "0006_p5_run_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("run_gate_evaluation", "run_gate_blocker")


def upgrade() -> None:
    op.create_table(
        "run_gate_evaluation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workflow_run_id",
            sa.String(36),
            sa.ForeignKey("workflow_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("gate_version", sa.String(16), nullable=False),
        sa.Column("input_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("unavailable_reason", sa.String(64), nullable=True),
        sa.Column("blocking_fact_count", sa.Integer(), nullable=False),
        sa.Column(
            "historical_excluded_vi002_ids",
            sa.String(2000),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("as_of_utc", sa.String(20), nullable=False),
        sa.Column("evaluated_at", sa.String(20), nullable=False),
        sa.CheckConstraint(
            "decision IN ('proceed', 'halt', 'unavailable')", name="decision_allowed"
        ),
        sa.CheckConstraint("length(input_fingerprint_sha256) = 64", name="fingerprint_sha_length"),
        sa.CheckConstraint("length(idempotency_key) = 64", name="idem_sha_length"),
        sa.CheckConstraint(
            "blocking_fact_count >= 0 AND blocking_fact_count <= 40", name="block_count"
        ),
        sa.UniqueConstraint(
            "workflow_run_id",
            "input_fingerprint_sha256",
            "gate_version",
            name="ux_gate_run_fingerprint_version",
        ),
    )
    op.create_index("ix_gate_run", "run_gate_evaluation", ["workflow_run_id", "evaluated_at"])

    op.create_table(
        "run_gate_blocker",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "gate_evaluation_id",
            sa.String(36),
            sa.ForeignKey("run_gate_evaluation.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("issue_type", sa.String(8), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("document.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("fact_ids", sa.String(600), nullable=False, server_default="[]"),
        sa.CheckConstraint(
            "issue_type IN ('VI-001','VI-002','VI-003','VI-004','VI-005','VI-006')",
            name="issue_type_allowed",
        ),
    )
    op.create_index("ix_gate_blocker_gate", "run_gate_blocker", ["gate_evaluation_id"])

    # An audited gate decision cannot be rewritten or deleted through SQL.
    for table in TABLES:
        for operation in ("UPDATE", "DELETE"):
            trigger = f"trg_{table}_{operation.lower()}_immutable"
            op.execute(
                f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, 'run gate evidence is immutable'); END"
            )


def downgrade() -> None:
    connection = op.get_bind()
    for table in TABLES:
        if connection.execute(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar_one():
            raise RuntimeError(
                "Refusing 0007 downgrade: immutable run gate evidence exists; archive by "
                "approved operator procedure before any destructive schema change."
            )

    for table in reversed(TABLES):
        for operation in ("UPDATE", "DELETE"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_{operation.lower()}_immutable")
    op.drop_index("ix_gate_blocker_gate", table_name="run_gate_blocker")
    op.drop_table("run_gate_blocker")
    op.drop_index("ix_gate_run", table_name="run_gate_evaluation")
    op.drop_table("run_gate_evaluation")
