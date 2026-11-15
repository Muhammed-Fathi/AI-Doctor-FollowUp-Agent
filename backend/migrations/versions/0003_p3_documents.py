"""P3 document ingestion: document, extraction_attempt, extracted_fact, fact_verification, verification_issue.

Revision ID: 0003_p3_documents
Revises: 0002_p2_patient_domain
Create Date: 2026-11-15

Scope
-----
Creates exactly the five P3 tables declared in ``app/db/models.py`` and derived
from ``DATA_DICTIONARY.md`` §2.4-§2.8a:

``document``            an uploaded synthetic report (hash, bounds, status),
``extraction_attempt``  typed provenance of every bounded extraction attempt,
``extracted_fact``      a candidate fact — unverified by construction,
``fact_verification``   append-only human decision log,
``verification_issue``  pre-verification blockers (``VI-001..VI-006``).

It also adds P2's deliberately deferred column:

``observation.source_fact_id`` + ``ux_obs_source_fact``

P2 wrote that the column was *"deferred to P3 with extracted_fact: the column's
foreign key target does not exist yet"*. It is added here additively as a
nullable column, so every existing ``observation`` row keeps
``source_fact_id = NULL``. SQLite treats NULLs as distinct in a unique index, so
seeded and check-in rows are unaffected, while a replayed verification can never
create a second observation for the same fact (``REQ-DATA-05``, ``P0-R10``).

Doctor-role trigger (accepted data-dictionary design)
-----------------------------------------------------
``DATA_DICTIONARY.md`` §2.7 requires ``fact_verification.verified_by_user_id`` to
be a doctor, enforced by *"service + CHECK trigger"*. A cross-table role lookup
cannot be expressed as a SQL ``CHECK`` on SQLite, so it is a ``BEFORE INSERT``
trigger. ``IS NOT 'doctor'`` is used rather than ``<>`` on purpose: it also
rejects a row whose user row is missing, closing the NULL-comparison hole.
The service layer enforces the same rule independently, so neither layer alone
is load-bearing.

Reversibility
-------------
``downgrade()`` drops the trigger first, then the unique index and column from
``observation``, then the five tables in reverse dependency order. It touches
none of P2's other objects and no P1 object, so ``0003 -> 0002`` leaves the P2
schema — and every P2 row — exactly as ``0002`` created it.

``ALTER TABLE ... DROP COLUMN`` is used for the rollback because it is supported
by SQLite >= 3.35 without rebuilding the table (verified locally on 3.40.1; the
project's SQLite is whatever CPython 3.12 bundles). The index that references
the column is dropped *before* the column, which SQLite requires.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_p3_documents"
down_revision: str | None = "0002_p2_patient_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Name of the doctor-only guard installed by this revision.
DOCTOR_TRIGGER_NAME = "trg_fact_verification_doctor_only"

#: Message raised when a non-doctor tries to record a decision. Neutral wording;
#: it echoes no document text and no user-supplied value.
DOCTOR_TRIGGER_MESSAGE = "fact_verification.verified_by_user_id must reference a doctor"


def upgrade() -> None:
    op.create_table(
        "document",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "extraction_status",
            sa.String(length=24),
            server_default="pending_extraction",
            nullable=False,
        ),
        sa.Column("failure_code", sa.String(length=48), nullable=True),
        sa.Column("uploaded_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "mime_type IN ('application/pdf', 'image/png', 'image/jpeg')",
            name="mime_type_allowed",
        ),
        sa.CheckConstraint(
            "extraction_status IN ('pending_extraction', 'extracted', "
            "'needs_verification', 'verified', 'failed')",
            name="status_allowed",
        ),
        sa.CheckConstraint("length(sha256) = 64", name="sha256_length"),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="size_within_cap"),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count <= 20", name="page_count_within_cap"
        ),
        sa.CheckConstraint("length(original_filename) > 0", name="filename_not_empty"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.create_index("ix_document_patient", ["patient_id"], unique=False)
        batch_op.create_index("ux_document_sha_patient", ["patient_id", "sha256"], unique=True)

    op.create_table(
        "extraction_attempt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("path", sa.String(length=16), nullable=False),
        sa.Column("preprocessing", sa.String(length=20), server_default="none", nullable=False),
        sa.Column("engine_confidence", sa.Float(), nullable=True),
        sa.Column("text_char_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("page_from", sa.Integer(), server_default="0", nullable=False),
        sa.Column("page_to", sa.Integer(), server_default="0", nullable=False),
        sa.Column("succeeded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=48), nullable=True),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tool_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint("path IN ('pypdf', 'tesseract', 'manual')", name="path_allowed"),
        sa.CheckConstraint(
            "preprocessing IN ('none', 'grayscale_upscale')", name="preprocessing_allowed"
        ),
        sa.CheckConstraint(
            "engine_confidence IS NULL OR "
            "(engine_confidence >= 0.0 AND engine_confidence <= 1.0)",
            name="confidence_in_range",
        ),
        sa.CheckConstraint("text_char_count >= 0", name="text_char_count_non_negative"),
        sa.CheckConstraint("duration_ms >= 0", name="duration_non_negative"),
        sa.CheckConstraint("page_from >= 0 AND page_to >= page_from", name="page_range_valid"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("extraction_attempt", schema=None) as batch_op:
        batch_op.create_index("ix_attempt_document", ["document_id", "created_at"], unique=False)
        batch_op.create_index(
            "ix_attempt_doc_conf", ["document_id", "engine_confidence"], unique=False
        )

    op.create_table(
        "extracted_fact",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=24), nullable=False),
        sa.Column("raw_text", sa.String(length=300), nullable=False),
        sa.Column("normalized_value", sa.String(length=120), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("quality_flags", sa.String(length=200), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("verification_status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "field_name IN ('report_date', 'test_name', 'value', 'unit', 'reference_text')",
            name="field_allowed",
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected')",
            name="verification_status_allowed",
        ),
        sa.CheckConstraint("raw_text <> ''", name="raw_text_not_empty"),
        sa.CheckConstraint("length(raw_text) <= 300", name="raw_text_bounded"),
        sa.CheckConstraint("page_index >= 0", name="page_index_non_negative"),
        sa.CheckConstraint("char_start >= 0 AND char_end >= char_start", name="span_ordered"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="confidence_in_range",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("extracted_fact", schema=None) as batch_op:
        batch_op.create_index("ix_fact_document", ["document_id"], unique=False)
        batch_op.create_index(
            "ix_fact_status", ["patient_id", "verification_status"], unique=False
        )

    op.create_table(
        "fact_verification",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fact_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("previous_value", sa.String(length=120), nullable=True),
        sa.Column("new_value", sa.String(length=120), nullable=True),
        sa.Column("new_unit", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("verified_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("decided_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "decision IN ('verified', 'rejected', 'corrected')", name="decision_allowed"
        ),
        sa.ForeignKeyConstraint(["fact_id"], ["extracted_fact.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("fact_verification", schema=None) as batch_op:
        batch_op.create_index("ix_factver_fact", ["fact_id", "decided_at"], unique=False)

    op.create_table(
        "verification_issue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("issue_type", sa.String(length=8), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("blocking", sa.Integer(), server_default="1", nullable=False),
        sa.Column("message", sa.String(length=240), nullable=False),
        sa.Column("state", sa.String(length=12), server_default="open", nullable=False),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "issue_type IN ('VI-001', 'VI-002', 'VI-003', 'VI-004', 'VI-005', 'VI-006')",
            name="issue_type_allowed",
        ),
        sa.CheckConstraint("blocking = 1", name="always_blocking"),
        sa.CheckConstraint("state IN ('open', 'resolved', 'superseded')", name="state_allowed"),
        sa.CheckConstraint("length(message) <= 240", name="message_bounded"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("verification_issue", schema=None) as batch_op:
        batch_op.create_index("ix_vi_document_state", ["document_id", "state"], unique=False)
        batch_op.create_index("ix_vi_run", ["workflow_run_id"], unique=False)

    # --- P2's deliberately deferred column, added additively -----------------
    # No table rebuild: nullable column + inline REFERENCES, so every existing
    # row is preserved with NULL and remains untouched by the unique index.
    op.execute(
        "ALTER TABLE observation ADD COLUMN source_fact_id VARCHAR(36) "
        "REFERENCES extracted_fact (id) ON DELETE RESTRICT"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_obs_source_fact ON observation (source_fact_id)"
    )

    # --- doctor-only guard: service AND database (DATA_DICTIONARY.md §2.7) ---
    op.execute(
        f"""
        CREATE TRIGGER {DOCTOR_TRIGGER_NAME}
        BEFORE INSERT ON fact_verification
        FOR EACH ROW
        WHEN (SELECT role FROM user WHERE id = NEW.verified_by_user_id) IS NOT 'doctor'
        BEGIN
            SELECT RAISE(ABORT, '{DOCTOR_TRIGGER_MESSAGE}');
        END
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {DOCTOR_TRIGGER_NAME}")
    # Index first: SQLite refuses to drop a column an index still references.
    op.execute("DROP INDEX IF EXISTS ux_obs_source_fact")
    op.execute("ALTER TABLE observation DROP COLUMN source_fact_id")

    with op.batch_alter_table("verification_issue", schema=None) as batch_op:
        batch_op.drop_index("ix_vi_run")
        batch_op.drop_index("ix_vi_document_state")

    op.drop_table("verification_issue")
    with op.batch_alter_table("fact_verification", schema=None) as batch_op:
        batch_op.drop_index("ix_factver_fact")

    op.drop_table("fact_verification")
    with op.batch_alter_table("extracted_fact", schema=None) as batch_op:
        batch_op.drop_index("ix_fact_status")
        batch_op.drop_index("ix_fact_document")

    op.drop_table("extracted_fact")
    with op.batch_alter_table("extraction_attempt", schema=None) as batch_op:
        batch_op.drop_index("ix_attempt_doc_conf")
        batch_op.drop_index("ix_attempt_document")

    op.drop_table("extraction_attempt")
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.drop_index("ux_document_sha_patient")
        batch_op.drop_index("ix_document_patient")

    op.drop_table("document")
