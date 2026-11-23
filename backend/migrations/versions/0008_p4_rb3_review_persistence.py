"""P4-RB3: durable WITHOUT ROWID run-bound review persistence tables and guards.

Additive-only migration from 0007_p5_run_gate. Creates review_item,
evidence_link, and review_evaluation with WITHOUT ROWID, matching indexes
(including the inert prospective span index), and 25 structural triggers
(G1-G25). No existing table, column, constraint, index, trigger, or pragma
is altered.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008_p4_rb3_review_persistence"
down_revision: str | tuple[str, ...] | None = "0007_p5_run_gate"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

DOWNGRADE_REFUSED_MESSAGE = (
    "Cannot downgrade 0008_p4_rb3_review_persistence while persisted review items, "
    "evidence links, or evaluations exist; archive via an approved operator process."
)

TRIGGER_CREATION_ORDER: tuple[tuple[str, str], ...] = (
    (
        "trg_review_item_update_immutable",
        """
        CREATE TRIGGER trg_review_item_update_immutable
        BEFORE UPDATE ON review_item
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'review_item is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_review_item_delete_immutable",
        """
        CREATE TRIGGER trg_review_item_delete_immutable
        BEFORE DELETE ON review_item
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'review_item is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_review_item_insert_open_only",
        """
        CREATE TRIGGER trg_review_item_insert_open_only
        BEFORE INSERT ON review_item
        FOR EACH ROW
        WHEN NEW.state <> 'open'
        BEGIN
            SELECT RAISE(ABORT, 'only open review items may be written in P4-RB3');
        END
        """,
    ),
    (
        "trg_review_item_run_scope_consistent",
        """
        CREATE TRIGGER trg_review_item_run_scope_consistent
        BEFORE INSERT ON review_item
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM workflow_run
            WHERE id = NEW.workflow_run_id
              AND patient_id = NEW.patient_id
              AND policy_version = NEW.policy_version
        )
        BEGIN
            SELECT RAISE(ABORT, 'review item must match its run scope');
        END
        """,
    ),
    (
        "trg_evidence_link_update_immutable",
        """
        CREATE TRIGGER trg_evidence_link_update_immutable
        BEFORE UPDATE ON evidence_link
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'evidence_link is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_evidence_link_delete_immutable",
        """
        CREATE TRIGGER trg_evidence_link_delete_immutable
        BEFORE DELETE ON evidence_link
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'evidence_link is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_evidence_link_owner_review_item_only",
        """
        CREATE TRIGGER trg_evidence_link_owner_review_item_only
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN NEW.owner_type <> 'review_item'
        BEGIN
            SELECT RAISE(ABORT, 'only review_item owners are supported in P4-RB3');
        END
        """,
    ),
    (
        "trg_evidence_link_kind_observation_only",
        """
        CREATE TRIGGER trg_evidence_link_kind_observation_only
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN NEW.kind <> 'observation'
        BEGIN
            SELECT RAISE(ABORT, 'only observation evidence links are writable in P4-RB3');
        END
        """,
    ),
    (
        "trg_evidence_link_owner_exists",
        """
        CREATE TRIGGER trg_evidence_link_owner_exists
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN (SELECT id FROM review_item WHERE id = NEW.owner_id) IS NULL
        BEGIN
            SELECT RAISE(ABORT, 'evidence link owner must be an existing review item');
        END
        """,
    ),
    (
        "trg_evidence_link_reference_same_patient",
        """
        CREATE TRIGGER trg_evidence_link_reference_same_patient
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN (
            NEW.observation_id IS NOT NULL AND (
                (SELECT patient_id FROM observation WHERE id = NEW.observation_id) IS NULL
                OR (SELECT patient_id FROM observation WHERE id = NEW.observation_id)
                   IS NOT (SELECT patient_id FROM review_item WHERE id = NEW.owner_id)
            )
        ) OR (
            NEW.document_id IS NOT NULL AND (
                (SELECT patient_id FROM document WHERE id = NEW.document_id) IS NULL
                OR (SELECT patient_id FROM document WHERE id = NEW.document_id)
                   IS NOT (SELECT patient_id FROM review_item WHERE id = NEW.owner_id)
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'evidence must belong to the review item patient');
        END
        """,
    ),
    (
        "trg_evidence_link_duplicate_identity",
        """
        CREATE TRIGGER trg_evidence_link_duplicate_identity
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM evidence_link
            WHERE owner_type IS NEW.owner_type
              AND owner_id IS NEW.owner_id
              AND kind IS NEW.kind
              AND document_id IS NEW.document_id
              AND observation_id IS NEW.observation_id
              AND page_index IS NEW.page_index
              AND char_start IS NEW.char_start
              AND char_end IS NEW.char_end
        )
        BEGIN
            SELECT RAISE(ABORT, 'duplicate typed evidence identity');
        END
        """,
    ),
    (
        "trg_review_evaluation_update_immutable",
        """
        CREATE TRIGGER trg_review_evaluation_update_immutable
        BEFORE UPDATE ON review_evaluation
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'review_evaluation is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_review_evaluation_delete_immutable",
        """
        CREATE TRIGGER trg_review_evaluation_delete_immutable
        BEFORE DELETE ON review_evaluation
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'review_evaluation is immutable in P4-RB3');
        END
        """,
    ),
    (
        "trg_review_evaluation_run_scope_consistent",
        """
        CREATE TRIGGER trg_review_evaluation_run_scope_consistent
        BEFORE INSERT ON review_evaluation
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM workflow_run
            WHERE id = NEW.workflow_run_id
              AND patient_id = NEW.patient_id
              AND doctor_id = NEW.doctor_id
              AND policy_version = NEW.policy_version
              AND as_of_utc = NEW.as_of_utc
        )
        OR NOT EXISTS (
            SELECT 1 FROM run_gate_evaluation
            WHERE id = NEW.gate_evaluation_id
              AND workflow_run_id = NEW.workflow_run_id
              AND decision = 'proceed'
              AND gate_version = NEW.gate_version
              AND input_fingerprint_sha256 = NEW.gate_input_fingerprint_sha256
        )
        OR NOT EXISTS (
            SELECT 1 FROM audit_event
            WHERE id = NEW.audit_event_id
              AND workflow_run_id = NEW.workflow_run_id
              AND subject_type = 'workflow_run'
              AND subject_id = NEW.workflow_run_id
              AND actor_type = 'user'
              AND actor_id = NEW.doctor_id
              AND outcome = 'ok'
              AND event_type = 'workflow.review.persisted'
              AND patient_id = NEW.patient_id
        )
        OR NEW.item_count <> (
            SELECT COUNT(*) FROM review_item
            WHERE workflow_run_id = NEW.workflow_run_id
        )
        OR NEW.evidence_link_count <> (
            SELECT COUNT(*) FROM evidence_link
            WHERE owner_type = 'review_item'
              AND owner_id IN (
                  SELECT id FROM review_item
                  WHERE workflow_run_id = NEW.workflow_run_id
              )
        )
        BEGIN
            SELECT RAISE(ABORT, 'review evaluation must match its run, gate, audit and rows');
        END
        """,
    ),
    (
        "trg_review_item_insert_sealed",
        """
        CREATE TRIGGER trg_review_item_insert_sealed
        BEFORE INSERT ON review_item
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM review_evaluation
            WHERE workflow_run_id = NEW.workflow_run_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'review result is sealed for this run');
        END
        """,
    ),
    (
        "trg_evidence_link_insert_sealed",
        """
        CREATE TRIGGER trg_evidence_link_insert_sealed
        BEFORE INSERT ON evidence_link
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM review_evaluation e
            JOIN review_item i ON i.workflow_run_id = e.workflow_run_id
            WHERE i.id = NEW.owner_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'review result is sealed for this run');
        END
        """,
    ),
    (
        "trg_review_evaluation_insert_sealed",
        """
        CREATE TRIGGER trg_review_evaluation_insert_sealed
        BEFORE INSERT ON review_evaluation
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM review_evaluation
            WHERE workflow_run_id = NEW.workflow_run_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'review evaluation already sealed for this run');
        END
        """,
    ),
    (
        "trg_review_item_insert_id_conflict",
        """
        CREATE TRIGGER trg_review_item_insert_id_conflict
        BEFORE INSERT ON review_item
        WHEN EXISTS (SELECT 1 FROM review_item WHERE id = NEW.id)
        BEGIN
            SELECT RAISE(
                ABORT,
                'review_item insert would replace an existing immutable row (primary key)'
            );
        END
        """,
    ),
    (
        "trg_review_item_insert_dedupe_conflict",
        """
        CREATE TRIGGER trg_review_item_insert_dedupe_conflict
        BEFORE INSERT ON review_item
        WHEN EXISTS (
            SELECT 1 FROM review_item
            WHERE workflow_run_id = NEW.workflow_run_id
              AND dedupe_key = NEW.dedupe_key
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'review_item insert would replace an existing immutable row (run dedupe identity)'
            );
        END
        """,
    ),
    (
        "trg_review_item_insert_order_conflict",
        """
        CREATE TRIGGER trg_review_item_insert_order_conflict
        BEFORE INSERT ON review_item
        WHEN EXISTS (
            SELECT 1 FROM review_item
            WHERE workflow_run_id = NEW.workflow_run_id
              AND display_order = NEW.display_order
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'review_item insert would replace an existing immutable row (run display order)'
            );
        END
        """,
    ),
    (
        "trg_evidence_link_insert_id_conflict",
        """
        CREATE TRIGGER trg_evidence_link_insert_id_conflict
        BEFORE INSERT ON evidence_link
        WHEN EXISTS (SELECT 1 FROM evidence_link WHERE id = NEW.id)
        BEGIN
            SELECT RAISE(
                ABORT,
                'evidence_link insert would replace an existing immutable row (primary key)'
            );
        END
        """,
    ),
    (
        "trg_evidence_link_insert_observation_identity_conflict",
        """
        CREATE TRIGGER trg_evidence_link_insert_observation_identity_conflict
        BEFORE INSERT ON evidence_link
        WHEN NEW.kind = 'observation'
         AND EXISTS (
            SELECT 1 FROM evidence_link
            WHERE kind = 'observation'
              AND owner_id = NEW.owner_id
              AND observation_id = NEW.observation_id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'evidence_link insert would replace an existing immutable row (observation identity)'
            );
        END
        """,
    ),
    (
        "trg_evidence_link_insert_span_identity_conflict",
        """
        CREATE TRIGGER trg_evidence_link_insert_span_identity_conflict
        BEFORE INSERT ON evidence_link
        WHEN NEW.kind = 'document_span'
         AND EXISTS (
            SELECT 1 FROM evidence_link
            WHERE kind = 'document_span'
              AND owner_id = NEW.owner_id
              AND document_id = NEW.document_id
              AND page_index = NEW.page_index
              AND char_start = NEW.char_start
              AND char_end = NEW.char_end
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'evidence_link insert would replace an existing immutable row (document span identity)'
            );
        END
        """,
    ),
    (
        "trg_review_evaluation_insert_id_conflict",
        """
        CREATE TRIGGER trg_review_evaluation_insert_id_conflict
        BEFORE INSERT ON review_evaluation
        WHEN EXISTS (SELECT 1 FROM review_evaluation WHERE id = NEW.id)
        BEGIN
            SELECT RAISE(
                ABORT,
                'review_evaluation insert would replace an existing immutable row (primary key)'
            );
        END
        """,
    ),
    (
        "trg_review_evaluation_insert_run_conflict",
        """
        CREATE TRIGGER trg_review_evaluation_insert_run_conflict
        BEFORE INSERT ON review_evaluation
        WHEN EXISTS (
            SELECT 1 FROM review_evaluation
            WHERE workflow_run_id = NEW.workflow_run_id
        )
        BEGIN
            SELECT RAISE(
                ABORT,
                'review_evaluation insert would replace an existing immutable row (unique run)'
            );
        END
        """,
    ),
)


def _rb3_persisted_evidence() -> bool:
    conn = op.get_bind()
    for table in ("review_item", "evidence_link", "review_evaluation"):
        if conn.execute(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar_one():
            return True
    return False


def upgrade() -> None:
    op.create_table(
        "review_item",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=8), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("workflow_hint", sa.String(length=24), nullable=False),
        sa.Column("trust_basis", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=240), nullable=False),
        sa.Column("policy_version", sa.String(length=24), nullable=False),
        sa.Column("demo_only", sa.Integer(), server_default="1", nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), server_default="open", nullable=False),
        sa.Column("provenance_status", sa.String(length=24), nullable=False),
        sa.Column("stored_lineage_proved", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint("length(id) = 36", name="review_item_id_len"),
        sa.CheckConstraint("length(patient_id) = 36", name="review_item_patient_id_len"),
        sa.CheckConstraint("length(workflow_run_id) = 36", name="review_item_run_id_len"),
        sa.CheckConstraint(
            "rule_id IN ('DR-001','DR-003','DR-005','DR-006','DR-008','DR-009')",
            name="review_item_rule_allowed",
        ),
        sa.CheckConstraint("length(rule_id) = 6", name="review_item_rule_len"),
        sa.CheckConstraint(
            "reason_code IN ('missing_baseline','measurement_stale',"
            "'change_exceeds_demo_parameter','verified_source_conflict',"
            "'duplicate_or_out_of_order','implausible_value')",
            name="review_item_reason_allowed",
        ),
        sa.CheckConstraint("length(reason_code) BETWEEN 1 AND 64", name="review_item_reason_len"),
        sa.CheckConstraint(
            "workflow_hint IN ('data_quality','verification_needed','change_to_review')",
            name="review_item_hint_allowed",
        ),
        sa.CheckConstraint(
            "trust_basis IN ('self_reported','doctor_verified','mixed')",
            name="review_item_trust_allowed",
        ),
        sa.CheckConstraint("length(message) BETWEEN 1 AND 240", name="review_item_message_len"),
        sa.CheckConstraint("policy_version = 'demo-policy-1.1.0'", name="review_item_policy_pinned"),
        sa.CheckConstraint("length(policy_version) <= 24", name="review_item_policy_len"),
        sa.CheckConstraint("demo_only = 1", name="review_item_demo_only"),
        sa.CheckConstraint("length(dedupe_key) = 64", name="review_item_dedupe_len"),
        sa.CheckConstraint(
            "state IN ('open','decided','superseded')",
            name="review_item_state_allowed",
        ),
        sa.CheckConstraint(
            "provenance_status = 'fixture_asserted'",
            name="review_item_provenance_pinned",
        ),
        sa.CheckConstraint(
            "stored_lineage_proved IN (0, 1)",
            name="review_item_lineage_proved_bool",
        ),
        sa.CheckConstraint("display_order >= 0", name="review_item_display_order_nonneg"),
        sa.CheckConstraint("length(created_at) = 20", name="review_item_created_at_len"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sqlite_with_rowid=False,
    )
    op.create_index(
        "ux_review_dedupe",
        "review_item",
        ["workflow_run_id", "dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ux_review_order",
        "review_item",
        ["workflow_run_id", "display_order"],
        unique=True,
    )
    op.create_index(
        "ix_review_patient_state",
        "review_item",
        ["patient_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_review_run",
        "review_item",
        ["workflow_run_id"],
        unique=False,
    )

    op.create_table(
        "evidence_link",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_type", sa.String(length=24), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("observation_id", sa.String(length=36), nullable=True),
        sa.Column("page_index", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint("length(id) = 36", name="evidence_link_id_len"),
        sa.CheckConstraint(
            "owner_type IN ('review_item','verification_issue','summary_claim')",
            name="evidence_link_owner_type_allowed",
        ),
        sa.CheckConstraint("length(owner_id) = 36", name="evidence_link_owner_id_len"),
        sa.CheckConstraint(
            "kind IN ('document_span','observation','checkin_note')",
            name="evidence_link_kind_allowed",
        ),
        sa.CheckConstraint(
            "page_index IS NULL OR page_index >= 0",
            name="evidence_link_page_nonneg",
        ),
        sa.CheckConstraint(
            "(char_start IS NULL AND char_end IS NULL) OR "
            "(char_start IS NOT NULL AND char_end IS NOT NULL "
            "AND char_start >= 0 AND char_end > char_start)",
            name="evidence_link_span_ordered",
        ),
        sa.CheckConstraint(
            "(kind = 'document_span' AND document_id IS NOT NULL AND observation_id IS NULL "
            "AND page_index IS NOT NULL AND char_start IS NOT NULL AND char_end IS NOT NULL) "
            "OR (kind = 'observation' AND observation_id IS NOT NULL AND document_id IS NULL "
            "AND page_index IS NULL AND char_start IS NULL AND char_end IS NULL) "
            "OR (kind = 'checkin_note' AND document_id IS NULL AND observation_id IS NULL)",
            name="evidence_link_kind_fields",
        ),
        sa.CheckConstraint("length(created_at) = 20", name="evidence_link_created_at_len"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["observation_id"], ["observation.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sqlite_with_rowid=False,
    )
    op.create_index(
        "ix_evidence_owner",
        "evidence_link",
        ["owner_type", "owner_id"],
        unique=False,
    )
    op.create_index(
        "ux_evidence_link_observation",
        "evidence_link",
        ["owner_id", "observation_id"],
        unique=True,
        sqlite_where=sa.text("kind = 'observation'"),
    )
    op.create_index(
        "ux_evidence_link_span",
        "evidence_link",
        ["owner_id", "document_id", "page_index", "char_start", "char_end"],
        unique=True,
        sqlite_where=sa.text("kind = 'document_span'"),
    )

    op.create_table(
        "review_evaluation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("as_of_utc", sa.String(length=20), nullable=False),
        sa.Column("policy_version", sa.String(length=24), nullable=False),
        sa.Column("policy_reference_sha256", sa.String(length=64), nullable=False),
        sa.Column("fingerprint_version", sa.String(length=32), nullable=False),
        sa.Column("input_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("output_identity_sha256", sa.String(length=64), nullable=False),
        sa.Column("gate_evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("gate_input_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("bridge_input_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("f2_contract_version", sa.String(length=8), nullable=False),
        sa.Column("gate_version", sa.String(length=8), nullable=False),
        sa.Column("rb2_policy_version", sa.String(length=24), nullable=False),
        sa.Column("lineage_label_policy", sa.String(length=32), nullable=False),
        sa.Column("dr006_policy", sa.String(length=24), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("evidence_link_count", sa.Integer(), nullable=False),
        sa.Column("exclusion_count", sa.Integer(), nullable=False),
        sa.Column("audit_event_id", sa.String(length=36), nullable=False),
        sa.Column("demo_only", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint("length(id) = 36", name="review_eval_id_len"),
        sa.CheckConstraint("length(workflow_run_id) = 36", name="review_eval_run_id_len"),
        sa.CheckConstraint("length(patient_id) = 36", name="review_eval_patient_id_len"),
        sa.CheckConstraint("length(doctor_id) = 36", name="review_eval_doctor_id_len"),
        sa.CheckConstraint("as_of_utc = '2026-11-14T12:00:00Z'", name="review_eval_clock_pinned"),
        sa.CheckConstraint("length(as_of_utc) = 20", name="review_eval_clock_len"),
        sa.CheckConstraint("policy_version = 'demo-policy-1.1.0'", name="review_eval_policy_pinned"),
        sa.CheckConstraint("length(policy_reference_sha256) = 64", name="review_eval_policy_sha_len"),
        sa.CheckConstraint(
            "policy_reference_sha256 = "
            "'f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36'",
            name="review_eval_policy_sha_pinned",
        ),
        sa.CheckConstraint(
            "fingerprint_version = 'rb3-full-input-1.0.0'",
            name="review_eval_fp_version_pinned",
        ),
        sa.CheckConstraint("length(input_fingerprint_sha256) = 64", name="review_eval_input_sha_len"),
        sa.CheckConstraint("length(output_identity_sha256) = 64", name="review_eval_output_sha_len"),
        sa.CheckConstraint("length(gate_evaluation_id) = 36", name="review_eval_gate_id_len"),
        sa.CheckConstraint(
            "length(gate_input_fingerprint_sha256) = 64",
            name="review_eval_gate_sha_len",
        ),
        sa.CheckConstraint(
            "length(bridge_input_fingerprint_sha256) = 64",
            name="review_eval_bridge_sha_len",
        ),
        sa.CheckConstraint("f2_contract_version = '2.0.0'", name="review_eval_f2_ver_pinned"),
        sa.CheckConstraint("gate_version = '1.0.0'", name="review_eval_gate_ver_pinned"),
        sa.CheckConstraint(
            "rb2_policy_version = 'demo-policy-1.1.0'",
            name="review_eval_rb2_policy_pinned",
        ),
        sa.CheckConstraint(
            "lineage_label_policy = 'a2_transport_label'",
            name="review_eval_lineage_policy_pinned",
        ),
        sa.CheckConstraint(
            "dr006_policy = 'prohibited_denied'",
            name="review_eval_dr006_policy_pinned",
        ),
        sa.CheckConstraint("item_count BETWEEN 0 AND 12", name="review_eval_item_count_range"),
        sa.CheckConstraint(
            "evidence_link_count BETWEEN 0 AND 24",
            name="review_eval_link_count_range",
        ),
        sa.CheckConstraint(
            "evidence_link_count >= item_count",
            name="review_eval_link_ge_item",
        ),
        sa.CheckConstraint(
            "exclusion_count BETWEEN 0 AND 200",
            name="review_eval_excl_count_range",
        ),
        sa.CheckConstraint("length(audit_event_id) = 36", name="review_eval_audit_id_len"),
        sa.CheckConstraint("demo_only = 1", name="review_eval_demo_only"),
        sa.CheckConstraint("length(created_at) = 20", name="review_eval_created_at_len"),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_event.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["doctor_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["gate_evaluation_id"], ["run_gate_evaluation.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sqlite_with_rowid=False,
    )
    op.create_index(
        "ux_review_evaluation_run",
        "review_evaluation",
        ["workflow_run_id"],
        unique=True,
    )
    op.create_index(
        "ix_review_evaluation_patient",
        "review_evaluation",
        ["patient_id", "created_at"],
        unique=False,
    )

    for _, trigger_sql in TRIGGER_CREATION_ORDER:
        op.execute(trigger_sql)


def downgrade() -> None:
    if _rb3_persisted_evidence():
        raise RuntimeError(DOWNGRADE_REFUSED_MESSAGE)

    for trigger_name, _ in reversed(TRIGGER_CREATION_ORDER):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")

    op.drop_index("ix_review_evaluation_patient", table_name="review_evaluation")
    op.drop_index("ux_review_evaluation_run", table_name="review_evaluation")
    op.drop_table("review_evaluation")

    op.drop_index("ux_evidence_link_span", table_name="evidence_link")
    op.drop_index("ux_evidence_link_observation", table_name="evidence_link")
    op.drop_index("ix_evidence_owner", table_name="evidence_link")
    op.drop_table("evidence_link")

    op.drop_index("ix_review_run", table_name="review_item")
    op.drop_index("ix_review_patient_state", table_name="review_item")
    op.drop_index("ux_review_order", table_name="review_item")
    op.drop_index("ux_review_dedupe", table_name="review_item")
    op.drop_table("review_item")
