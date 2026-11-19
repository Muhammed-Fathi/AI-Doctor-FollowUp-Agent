"""P3 rejection recovery: document.recovered_from_document_id self-reference.

Revision ID: 0004_p3_rejection_recovery
Revises: 0003_p3_documents
Create Date: 2026-11-16

Scope
-----
Adds exactly one nullable column, one index and one self-referencing foreign
key to the existing ``document`` table:

``recovered_from_document_id``
    The *terminal* document a recovery upload replaces (R21 §4.3). ``NULL`` for
    every ordinary upload, including every row that already exists.

This is a **patient-declared association**, not a clinical equivalence claim:
nothing in this schema asserts that the recovered bytes are clearer, related or
safer than the source. The new document is extracted, identity-checked
(``VI-004``), conflict-checked (``VI-006``) and doctor-verified through the
existing endpoints, and the link never substitutes for any of them.

Why the operations are written this way
---------------------------------------
SQLite has **no** standalone ``ALTER TABLE ... ADD CONSTRAINT`` or
``DROP CONSTRAINT``. The foreign key therefore cannot be bolted onto the
existing table with a plain ``ALTER TABLE``, and the accepted way to express it
in Alembic is a batch-mode table copy (``batch_alter_table``), which SQLite
implements by rebuilding ``document`` with the new definition and copying every
row across.

A rebuild is exactly the operation that can silently lose schema objects, so the
following are preserved deliberately and asserted by the migration test:

* all seven named ``CHECK`` constraints (``mime_type_allowed``,
  ``status_allowed``, ``sha256_length``, ``size_within_cap``,
  ``page_count_within_cap``, ``filename_not_empty``) survive the copy;
* both existing indexes (``ix_document_patient``, ``ux_document_sha_patient``)
  and their uniqueness survive;
* the two existing foreign keys (``patient``, ``user``) and their
  ``ON DELETE RESTRICT`` behaviour survive;
* every existing P2 and P3 row keeps its values, with the new column ``NULL``.

The self-reference is a normal inline foreign key. SQLAlchemy emits it without a
cycle warning — unlike the ``user <-> patient`` two-table cycle — because a
self-reference needs no deferred dependency resolution.

Reversibility, and why ``downgrade`` can refuse
-----------------------------------------------
Dropping the column would silently destroy recovery provenance: after the drop
there is no record that document *B* was declared a recovery of document *A*.
A migration that quietly deletes an audit-relevant relationship is worse than
one that stops, so ``downgrade()`` **refuses** when any link exists, and it
refuses *before* touching the schema, so the schema and every row are left
exactly as they were.

The refusal raises a plain ``RuntimeError`` with a neutral message. Recovering
from it is an explicit operator decision — archive the links first, then
downgrade — which is stated in the error text rather than guessed at here.

When no link exists the downgrade drops the foreign key (via the same batch
rebuild), then the index, then the column, returning the table to the exact
``0003`` definition.

Migration-engine note
---------------------
``backend/migrations/env.py`` deliberately sets ``PRAGMA foreign_keys=OFF`` for
migrations and the runtime engine sets it ``ON``. Enforcement is therefore not
proven by running the migration; the migration test and the smoke check assert
the resulting schema and then verify enforcement on a runtime-equivalent
connection with ``PRAGMA foreign_keys=ON``.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_p3_rejection_recovery"
down_revision: str | None = "0003_p3_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The column this revision owns.
COLUMN_NAME = "recovered_from_document_id"

#: Its index, and the foreign key name the model declares.
INDEX_NAME = "ix_document_recovered_from"
FOREIGN_KEY_NAME = "fk_document_recovered_from"

#: Raised (and asserted by the tests) when a downgrade would destroy lineage.
DOWNGRADE_REFUSED_MESSAGE = (
    "Refusing to downgrade 0004_p3_rejection_recovery: document rows still carry "
    "recovered_from_document_id. Dropping the column would destroy recovery "
    "provenance. Archive or clear the recovery links first, then downgrade."
)

#: The named CHECK constraints that must survive a batch rebuild. Kept here so
#: the test and the migration agree on the list rather than restating it.
PRESERVED_CHECK_CONSTRAINTS = (
    "mime_type_allowed",
    "status_allowed",
    "sha256_length",
    "size_within_cap",
    "page_count_within_cap",
    "filename_not_empty",
)

#: The indexes that must survive the rebuild.
PRESERVED_INDEXES = ("ix_document_patient", "ux_document_sha_patient")


def _recovery_links_present() -> bool:
    """Return ``True`` when any document row already carries a recovery link.

    Uses ``COALESCE(MAX(...), 0)`` rather than ``SELECT 1 ... LIMIT 1`` so the
    answer is a value, not a row-count that depends on how the driver fetched.
    """
    connection = op.get_bind()
    result = connection.execute(
        sa.text(
            f"SELECT COALESCE(MAX(CASE WHEN {COLUMN_NAME} IS NOT NULL THEN 1 ELSE 0 END), 0) "
            "FROM document"
        )
    ).scalar_one()
    return bool(result)


def upgrade() -> None:
    """Add the nullable self-reference, its index and its foreign key."""
    # One batch block so SQLite rebuilds the table once, not three times. The
    # column is nullable with no server default, so every existing row keeps its
    # values and reads ``NULL`` for the new column.
    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.add_column(sa.Column(COLUMN_NAME, sa.String(length=36), nullable=True))
        batch_op.create_index(INDEX_NAME, [COLUMN_NAME], unique=False)
        batch_op.create_foreign_key(
            FOREIGN_KEY_NAME,
            "document",
            [COLUMN_NAME],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Drop the foreign key, index and column — but never destroy a live link.

    The guard runs first so a refused downgrade leaves the schema and every row
    untouched: nothing is dropped, and the transaction has done no DDL yet.
    """
    if _recovery_links_present():
        raise RuntimeError(DOWNGRADE_REFUSED_MESSAGE)

    with op.batch_alter_table("document", schema=None) as batch_op:
        batch_op.drop_constraint(FOREIGN_KEY_NAME, type_="foreignkey")
        batch_op.drop_index(INDEX_NAME)
        batch_op.drop_column(COLUMN_NAME)
