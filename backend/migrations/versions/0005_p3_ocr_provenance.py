"""P3 Stage 1 OCR provenance: document_page_text and source-comparison confirmation.

Revision ID: 0005_p3_ocr_provenance
Revises: 0004_p3_rejection_recovery
Create Date: 2026-11-16

Scope
-----
Adds two additive, Stage 1 provenance extensions without touching
``trg_fact_verification_doctor_only`` or rebuilding ``fact_verification``:

1. Table ``document_page_text`` storing bounded per-page text-layer / OCR output
   (``extractor IN ('pypdf', 'tesseract')``), so every ``extracted_fact`` span
   indexes persisted text and doctors can inspect OCR transcriptions via
   ``GET /api/v1/documents/{document_id}/text``.
2. Three nullable/defaulted columns on ``fact_verification`` via plain
   ``ALTER TABLE ... ADD COLUMN`` (never ``batch_alter_table``):
   - ``source_image_compared`` (``INTEGER NOT NULL DEFAULT 0 CHECK (IN (0, 1))``)
   - ``confirmed_value`` (``VARCHAR(120) NULL``)
   - ``confirmed_unit`` (``VARCHAR(32) NULL``)

Reversibility, and why ``downgrade`` refuses when provenance exists
-------------------------------------------------------------------
Dropping ``document_page_text`` or the confirmation columns when rows contain
stored page text or OCR verification provenance would silently erase audit
evidence. ``downgrade()`` checks before touching the schema and raises
``RuntimeError`` if any ``document_page_text`` row exists or any
``fact_verification`` row carries ``source_image_compared = 1``,
``confirmed_value IS NOT NULL``, or ``confirmed_unit IS NOT NULL``.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_p3_ocr_provenance"
down_revision: str | None = "0004_p3_rejection_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOWNGRADE_REFUSED_MESSAGE = (
    "Refusing to downgrade 0005_p3_ocr_provenance: persisted document_page_text "
    "or source-confirmation provenance exists. Dropping these objects would "
    "destroy OCR audit provenance. Archive or clear those records first, then downgrade."
)


def _provenance_present() -> bool:
    """Return True if any Stage 1 provenance rows would be destroyed by downgrade."""
    connection = op.get_bind()
    has_page_text = connection.execute(
        sa.text("SELECT COALESCE(MAX(1), 0) FROM document_page_text")
    ).scalar_one()
    has_verification_provenance = connection.execute(
        sa.text(
            "SELECT COALESCE(MAX(CASE WHEN source_image_compared = 1 "
            "OR confirmed_value IS NOT NULL "
            "OR confirmed_unit IS NOT NULL THEN 1 ELSE 0 END), 0) "
            "FROM fact_verification"
        )
    ).scalar_one()
    return bool(has_page_text) or bool(has_verification_provenance)


def upgrade() -> None:
    """Create ``document_page_text`` and add confirmation columns to ``fact_verification``."""
    op.create_table(
        "document_page_text",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("extractor", sa.String(length=16), nullable=False),
        sa.Column("tool_version", sa.String(length=64), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_length", sa.Integer(), nullable=False),
        sa.Column("non_whitespace_chars", sa.Integer(), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=20), nullable=False),
        sa.CheckConstraint("page_index >= 0", name="page_index_non_negative"),
        sa.CheckConstraint(
            "extractor IN ('pypdf', 'tesseract')", name="extractor_allowed"
        ),
        sa.CheckConstraint(
            "text_length >= 0 AND text_length <= 20000", name="text_length_bounded"
        ),
        sa.CheckConstraint("length(text) <= 20000", name="text_bounded"),
        sa.CheckConstraint(
            "non_whitespace_chars >= 0", name="non_whitespace_non_negative"
        ),
        sa.CheckConstraint("length(text_sha256) = 64", name="sha256_hex_length"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_page_text", schema=None) as batch_op:
        batch_op.create_index(
            "ux_page_text_doc_page", ["document_id", "page_index"], unique=True
        )
        batch_op.create_index("ix_page_text_document", ["document_id"], unique=False)

    # Plain ALTER TABLE keeps ``trg_fact_verification_doctor_only`` untouched.
    op.execute(
        "ALTER TABLE fact_verification ADD COLUMN source_image_compared "
        "INTEGER NOT NULL DEFAULT 0 CHECK (source_image_compared IN (0, 1))"
    )
    op.execute("ALTER TABLE fact_verification ADD COLUMN confirmed_value VARCHAR(120)")
    op.execute("ALTER TABLE fact_verification ADD COLUMN confirmed_unit VARCHAR(32)")


def downgrade() -> None:
    """Drop Stage 1 provenance objects cleanly unless provenance rows exist."""
    if _provenance_present():
        raise RuntimeError(DOWNGRADE_REFUSED_MESSAGE)

    op.execute("ALTER TABLE fact_verification DROP COLUMN confirmed_unit")
    op.execute("ALTER TABLE fact_verification DROP COLUMN confirmed_value")
    op.execute("ALTER TABLE fact_verification DROP COLUMN source_image_compared")

    with op.batch_alter_table("document_page_text", schema=None) as batch_op:
        batch_op.drop_index("ix_page_text_document")
        batch_op.drop_index("ux_page_text_doc_page")

    op.drop_table("document_page_text")
