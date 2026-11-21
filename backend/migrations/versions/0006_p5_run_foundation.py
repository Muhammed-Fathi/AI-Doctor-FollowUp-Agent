"""P5-F0 genuine workflow-run parent and immutable selected-source manifest.

This strictly additive migration owns no graph execution, real VI gate or DR
rule activation. App SQLite remains the authoritative run-status store.
Downgrade refuses to delete any persisted run/selection/audit linkage.
SYNTHETIC EDUCATIONAL ONLY / NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_p5_run_foundation"
down_revision: str | None = "0005_p3_ocr_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOWNGRADE_REFUSED_MESSAGE = (
    "Refusing to downgrade 0006_p5_run_foundation: durable run or source-selection "
    "audit rows exist. Archive via an approved operator process; no data was removed."
)

MANIFEST_TABLES = (
    "run_selected_document",
    "run_selected_observation",
    "run_source_omission",
)
IMMUTABLE_EVENTS = ("UPDATE", "DELETE")


def upgrade() -> None:
    op.create_table(
        "workflow_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("doctor_id", sa.String(36), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workflow_version", sa.String(12), nullable=False),
        sa.Column("state_schema_version", sa.String(12), nullable=False),
        sa.Column("policy_version", sa.String(24), nullable=False),
        sa.Column("as_of_utc", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("current_node", sa.String(32)),
        sa.Column("halt_reason", sa.String(32)),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("retry_counts", sa.String(500), nullable=False, server_default="{}"),
        sa.Column("mapping_version", sa.String(16), nullable=False),
        sa.Column("checkpoint_ref", sa.String(120)),
        sa.Column("started_at", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.String(20), nullable=False),
        sa.Column("ended_at", sa.String(20)),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'needs_verification', "
            "'awaiting_decision', 'finalizing', 'completed', "
            "'failed_retryable', 'failed_terminal')",
            name="status_allowed",
        ),
        sa.CheckConstraint("length(idempotency_key) = 64", name="idem_sha_length"),
        sa.CheckConstraint("mapping_version LIKE 'map-%.%.%'", name="mapping_version_shape"),
    )
    op.create_index("ix_run_patient", "workflow_run", ["patient_id", "started_at"])

    op.create_table(
        "run_selected_document",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workflow_run_id",
            sa.String(36),
            sa.ForeignKey("workflow_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id", sa.String(36), sa.ForeignKey("document.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("source_status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.String(20), nullable=False),
        sa.UniqueConstraint("workflow_run_id", "document_id", name="ux_run_selected_document"),
        sa.CheckConstraint("length(source_sha256) = 64", name="source_sha_length"),
    )
    op.create_index("ix_selected_document_run", "run_selected_document", ["workflow_run_id"])

    op.create_table(
        "run_selected_observation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workflow_run_id",
            sa.String(36),
            sa.ForeignKey("workflow_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "observation_id",
            sa.String(36),
            sa.ForeignKey("observation.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observation_created_at", sa.String(20), nullable=False),
        sa.Column("trust_level", sa.String(28), nullable=False),
        sa.Column("source_fact_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.String(20), nullable=False),
        sa.UniqueConstraint(
            "workflow_run_id", "observation_id", name="ux_run_selected_observation"
        ),
    )
    op.create_index("ix_selected_observation_run", "run_selected_observation", ["workflow_run_id"])

    op.create_table(
        "run_source_omission",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workflow_run_id",
            sa.String(36),
            sa.ForeignKey("workflow_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_id", sa.String(36), sa.ForeignKey("document.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "vi002_issue_id",
            sa.String(36),
            sa.ForeignKey("verification_issue.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("doctor_id", sa.String(36), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(20), nullable=False),
        sa.UniqueConstraint("workflow_run_id", "document_id", name="ux_run_source_omission"),
        sa.CheckConstraint(
            "reason_code = 'selected_separate_recovery_source'", name="reason_allowed"
        ),
        sa.CheckConstraint("length(source_sha256) = 64", name="source_sha_length"),
    )
    op.create_index("ix_run_omission_run", "run_source_omission", ["workflow_run_id"])

    # Existing nullable P2/P3 run references gain real FKs only after their
    # parent exists. Batch mode recreates these two tables on SQLite; previous
    # CHECKs/indexes and historic rows must survive.
    with op.batch_alter_table("audit_event", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_audit_workflow_run", "workflow_run", ["workflow_run_id"], ["id"],
            ondelete="RESTRICT",
        )
    with op.batch_alter_table("verification_issue", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_vi_workflow_run", "workflow_run", ["workflow_run_id"], ["id"],
            ondelete="RESTRICT",
        )

    # A manifest is immutable even if SQL bypasses the P5 service layer. The
    # workflow_run row itself may change status later but not these selections.
    for table in MANIFEST_TABLES:
        for operation in IMMUTABLE_EVENTS:
            trigger = f"trg_{table}_{operation.lower()}_immutable"
            op.execute(
                f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
            )


def _persisted_run_evidence() -> bool:
    conn = op.get_bind()
    for table in ("workflow_run", *MANIFEST_TABLES):
        has_rows = conn.execute(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar_one()
        if has_rows:
            return True
    # Legacy audit and VI rows may name a run even after manual DB surgery.
    for table in ("audit_event", "verification_issue"):
        linked = conn.execute(
            sa.text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE workflow_run_id IS NOT NULL)")
        ).scalar_one()
        if linked:
            return True
    return False


def downgrade() -> None:
    if _persisted_run_evidence():
        raise RuntimeError(DOWNGRADE_REFUSED_MESSAGE)

    with op.batch_alter_table("verification_issue", schema=None) as batch_op:
        batch_op.drop_constraint("fk_vi_workflow_run", type_="foreignkey")
    with op.batch_alter_table("audit_event", schema=None) as batch_op:
        batch_op.drop_constraint("fk_audit_workflow_run", type_="foreignkey")

    for table in reversed(MANIFEST_TABLES):
        for operation in IMMUTABLE_EVENTS:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_{operation.lower()}_immutable")
        index = {
            "run_selected_document": "ix_selected_document_run",
            "run_selected_observation": "ix_selected_observation_run",
            "run_source_omission": "ix_run_omission_run",
        }[table]
        op.drop_index(index, table_name=table)
        op.drop_table(table)

    op.drop_index("ix_run_patient", table_name="workflow_run")
    op.drop_table("workflow_run")
