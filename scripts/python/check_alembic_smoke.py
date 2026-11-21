#!/usr/bin/env python
"""Assert the state of a SQLite database after an Alembic migration sequence.

Called by ``.github/workflows/ci.yml`` (after ``upgrade head``) and usable
locally. Phase 2 replaces the old "no patient-domain tables" assertion with an
**exact** expected schema per revision state, so neither a missing table nor an
unplanned one can pass.

Usage::

    python scripts/python/check_alembic_smoke.py <path-to-sqlite-db> [--state STATE]

``--state`` (default ``head``):

``head``
    revision ``0006_p5_run_foundation``; **exactly** the historical P1/P2/P3
    schema plus the four authorized P5-F0 tables (``workflow_run`` and three
    immutable selected-source tables). All P3 checks below remain enforced,
    including provenance columns/indexes, the doctor-only verification trigger,
    the document recovery self-FK, and empty ``PRAGMA foreign_key_check``.
    P5-F0 FKs, run identity uniqueness, manifest uniqueness, expected indexes
    and UPDATE/DELETE immutability triggers are checked in addition.
``p3_stage1``
    revision ``0005_p3_ocr_provenance``; exact original P1+P2+P3 Stage 1
    schema, all P3 provenance/recovery checks, and NO P5-F0 table.
``p3_recovery``
    revision ``0004_p3_rejection_recovery``; everything ``head`` asserts **except**
    the Stage 1 ``0005`` provenance table/columns, which must be **absent**.
``p3``
    revision ``0003_p3_documents``; everything ``p3_recovery`` asserts **except**
    the three recovery objects, which must be **absent**. This is what
    ``0004 -> 0003`` must leave behind, and the only way to prove the recovery
    revision is additive and cleanly reversible.
``p2``
    revision ``0002_p2_patient_domain``; tables = P1 + the seven P2 tables and
    **no** P3 table and **no** ``observation.source_fact_id``. This is what
    ``0003 -> 0002`` must leave behind, and it is how the exact P2 schema is
    proven to survive P3 (owner decision D-05).
``p1``
    revision ``0001_p1_baseline``; tables = ``schema_meta`` + ``alembic_version``
    and **no** P2 table — this is what ``0002 -> 0001`` must leave behind, and the
    only way to test "P1 is preserved" (``downgrade base`` cannot test it, because
    it also drops ``schema_meta``).
``base``
    no revision recorded; only ``alembic_version`` remains — the documented empty
    state after ``0002 -> base``.

``PRAGMA foreign_key_check`` is evaluated on a connection with
``PRAGMA foreign_keys=ON``, i.e. the same setting the runtime engine uses, not the
migration engine's.

Exit code 0 = PASS, 1 = FAIL.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

P1_REVISION = "0001_p1_baseline"

#: Doctor-only guard installed by ``0003`` (``DATA_DICTIONARY.md`` §2.7).
DOCTOR_TRIGGER_NAME = "trg_fact_verification_doctor_only"

#: Recovery objects owned by ``0004`` (``DATA_DICTIONARY.md`` §2.4, R21 §4.10).
RECOVERY_COLUMN = "recovered_from_document_id"
RECOVERY_INDEX = "ix_document_recovered_from"
HEAD_REVISION = "0006_p5_run_foundation"
P3_STAGE1_REVISION = "0005_p3_ocr_provenance"
P4_REVISION = "0004_p3_rejection_recovery"
P3_REVISION = "0003_p3_documents"
P2_REVISION = "0002_p2_patient_domain"

#: Stage 1 provenance objects owned by ``0005``.
PAGE_TEXT_TABLE = "document_page_text"
PAGE_TEXT_INDEXES = {"ux_page_text_doc_page", "ix_page_text_document"}
FACT_VERIFICATION_STAGE1_COLUMNS = {
    "source_image_compared",
    "confirmed_value",
    "confirmed_unit",
}

P1_TABLES = {"schema_meta", "alembic_version"}

#: Tables owned by the P2 revision (exactly the seven in ``0002``).
P2_TABLES = {
    "audit_event",
    "checkin_idempotency",
    "encounter",
    "observation",
    "patient",
    "session",
    "user",
}

#: Tables owned by the P3 revision (exactly the five in ``0003``).
P3_TABLES = {
    "document",
    "extraction_attempt",
    "extracted_fact",
    "fact_verification",
    "verification_issue",
}

#: CH-01 authorizes *only* four new durable P5-F0 tables at ``head``.
P5_F0_TABLES = {
    "workflow_run",
    "run_selected_document",
    "run_selected_observation",
    "run_source_omission",
}

#: Still-forbidden downstream P4/P5/P6 entities (never waived by CH-01).
P4_PLUS_TABLES = {
    "review_item",
    "summary_draft",
    "approval_decision",
    "follow_up_task",
    "in_app_notification",
    "evidence_link",
    "node_event",
    "summary_claim",
}

#: F0 tables own these named non-unique lookup indexes.
P5_F0_INDEXES = {
    "ix_run_patient",
    "ix_selected_document_run",
    "ix_selected_observation_run",
    "ix_run_omission_run",
}

P5_F0_IMMUTABLE_TABLES = {
    "run_selected_document",
    "run_selected_observation",
    "run_source_omission",
}

#: (table, column, referenced table) — run and audit FKs must all be genuine.
P5_F0_FKS = {
    ("workflow_run", "patient_id", "patient"),
    ("workflow_run", "doctor_id", "user"),
    ("run_selected_document", "workflow_run_id", "workflow_run"),
    ("run_selected_document", "document_id", "document"),
    ("run_selected_observation", "workflow_run_id", "workflow_run"),
    ("run_selected_observation", "observation_id", "observation"),
    ("run_source_omission", "workflow_run_id", "workflow_run"),
    ("run_source_omission", "document_id", "document"),
    ("run_source_omission", "vi002_issue_id", "verification_issue"),
    ("run_source_omission", "doctor_id", "user"),
    ("audit_event", "workflow_run_id", "workflow_run"),
    ("verification_issue", "workflow_run_id", "workflow_run"),
}

#: Unique identity / selected-source keys; no duplicate source per run.
P5_F0_UNIQUE_KEYS = {
    ("workflow_run", ("idempotency_key",)),
    ("run_selected_document", ("workflow_run_id", "document_id")),
    ("run_selected_observation", ("workflow_run_id", "observation_id")),
    ("run_source_omission", ("workflow_run_id", "document_id")),
}

VALID_STATES = {"head", "p3_stage1", "p3_recovery", "p3", "p2", "p1", "base"}


def _parse_args(argv: list[str]) -> tuple[Path, str] | None:
    """Return ``(database, state)`` or ``None`` for a usage error."""
    args = list(argv[1:])
    state = "head"
    if "--state" in args:
        index = args.index("--state")
        try:
            state = args[index + 1]
        except IndexError:
            return None
        del args[index : index + 2]
    if len(args) != 1 or state not in VALID_STATES:
        return None
    return Path(args[0]), state


def _expected_tables(state: str) -> set[str]:
    if state == "head":
        return P1_TABLES | P2_TABLES | P3_TABLES | {PAGE_TEXT_TABLE} | P5_F0_TABLES
    if state == "p3_stage1":
        return P1_TABLES | P2_TABLES | P3_TABLES | {PAGE_TEXT_TABLE}
    if state in {"p3_recovery", "p3"}:
        return P1_TABLES | P2_TABLES | P3_TABLES
    if state == "p2":
        return P1_TABLES | P2_TABLES
    if state == "p1":
        return set(P1_TABLES)
    return {"alembic_version"}


def _expected_revisions(state: str) -> list[str]:
    if state == "head":
        return [HEAD_REVISION]
    if state == "p3_stage1":
        return [P3_STAGE1_REVISION]
    if state == "p3_recovery":
        return [P4_REVISION]
    if state == "p3":
        return [P3_REVISION]
    if state == "p2":
        return [P2_REVISION]
    if state == "p1":
        return [P1_REVISION]
    return []


def main(argv: list[str]) -> int:
    """Validate the SQLite database at ``argv[1]`` for ``--state``."""
    parsed = _parse_args(argv)
    if parsed is None:
        print(
            "usage: check_alembic_smoke.py <path-to-sqlite-db> "
            "[--state head|p3_stage1|p3_recovery|p3|p2|p1|base]",
            file=sys.stderr,
        )
        return 1

    database, state = parsed
    if not database.is_file():
        print(f"FAIL: database file not found: {database}", file=sys.stderr)
        return 1

    with sqlite3.connect(database) as connection:
        # Runtime-equivalent enforcement, so a broken FK surfaces here rather
        # than at the first application query.
        connection.execute("PRAGMA foreign_keys=ON")
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        revisions = [
            row[0] for row in connection.execute("SELECT version_num FROM alembic_version")
        ]
        user_foreign_keys = (
            list(connection.execute("PRAGMA foreign_key_list('user')")) if "user" in tables else []
        )
        observation_columns = (
            [row[1] for row in connection.execute("PRAGMA table_info('observation')")]
            if "observation" in tables
            else []
        )
        observation_indexes = (
            [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='observation'"
                )
            ]
            if "observation" in tables
            else []
        )
        triggers = (
            [
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
            ]
            if tables
            else []
        )
        document_columns = (
            [row[1] for row in connection.execute("PRAGMA table_info('document')")]
            if "document" in tables
            else []
        )
        document_indexes = (
            [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='document'"
                )
            ]
            if "document" in tables
            else []
        )
        document_foreign_keys = (
            list(connection.execute("PRAGMA foreign_key_list('document')"))
            if "document" in tables
            else []
        )
        fact_verification_columns = (
            {row[1] for row in connection.execute("PRAGMA table_info('fact_verification')")}
            if "fact_verification" in tables
            else set()
        )
        page_text_indexes = (
            {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    f"AND tbl_name='{PAGE_TEXT_TABLE}'"
                )
            }
            if PAGE_TEXT_TABLE in tables
            else set()
        )
        foreign_key_violations = (
            connection.execute("PRAGMA foreign_key_check").fetchall() if tables else []
        )

    problems: list[str] = []

    expected_tables = _expected_tables(state)
    missing = expected_tables - tables
    if missing:
        problems.append(f"missing tables for state {state!r}: {sorted(missing)}")
    unexpected = tables - expected_tables
    if unexpected:
        problems.append(f"unexpected tables for state {state!r}: {sorted(unexpected)}")

    early = P4_PLUS_TABLES & tables
    if early:
        problems.append(f"later-phase tables must not exist: {sorted(early)}")

    # --- P3 structural assertions (owner decision D-05) ---------------------
    # At ``head``/``p3``: the deferred P2 column, its unique index and the
    # doctor-only trigger must all exist. A "later-phase" table check alone
    # would not catch a P3 revision that forgot one of them.
    if state in {"head", "p3_stage1", "p3_recovery", "p3"}:
        if "source_fact_id" not in observation_columns:
            problems.append("observation.source_fact_id must exist after 0003")
        if "ux_obs_source_fact" not in observation_indexes:
            problems.append("observation must carry the unique index ux_obs_source_fact")
        if DOCTOR_TRIGGER_NAME not in triggers:
            problems.append(f"migration 0003 must install the trigger {DOCTOR_TRIGGER_NAME}")

    # --- 0004 recovery self-reference (R21 §4.10) ---------------------------
    # At ``head`` and ``p3_recovery`` the column, its index and its RESTRICT
    # self-FK must all exist. At ``p3`` the same three must be absent.
    recovery_fk = [
        row
        for row in document_foreign_keys
        if row[3] == RECOVERY_COLUMN and row[2] == "document" and row[6] == "RESTRICT"
    ]
    if state in {"head", "p3_stage1", "p3_recovery"}:
        if RECOVERY_COLUMN not in document_columns:
            problems.append(f"document.{RECOVERY_COLUMN} must exist after 0004")
        if RECOVERY_INDEX not in document_indexes:
            problems.append(f"document must carry the index {RECOVERY_INDEX} after 0004")
        if not recovery_fk:
            problems.append(
                f"document must carry the ON DELETE RESTRICT self-FK on {RECOVERY_COLUMN}"
            )
    if state in {"p3", "p2", "p1", "base"}:
        if RECOVERY_COLUMN in document_columns:
            problems.append(f"document.{RECOVERY_COLUMN} must not exist below 0004")
        if RECOVERY_INDEX in document_indexes:
            problems.append(f"index {RECOVERY_INDEX} must not exist below 0004")
        if recovery_fk:
            problems.append(f"the {RECOVERY_COLUMN} self-FK must not exist below 0004")

    # --- 0005 Stage 1 OCR provenance ----------------------------------------
    if state in {"head", "p3_stage1"}:
        missing_fv_cols = FACT_VERIFICATION_STAGE1_COLUMNS - fact_verification_columns
        if missing_fv_cols:
            problems.append(f"fact_verification missing Stage 1 columns: {sorted(missing_fv_cols)}")
        missing_pt_idx = PAGE_TEXT_INDEXES - page_text_indexes
        if missing_pt_idx:
            problems.append(f"{PAGE_TEXT_TABLE} missing expected indexes: {sorted(missing_pt_idx)}")
    if state in {"p3_recovery", "p3", "p2", "p1", "base"}:
        leaked_fv_cols = FACT_VERIFICATION_STAGE1_COLUMNS & fact_verification_columns
        if leaked_fv_cols:
            problems.append(
                f"fact_verification Stage 1 columns must not exist below 0005: {sorted(leaked_fv_cols)}"
            )

    # --- 0006 CH-01 P5-F0 durable identity/manifest (owner scoped) ---------
    # This *adds* to, never replaces, the original strict P3 assertions.
    # Old states reject F0 tables through the exact _expected_tables comparison.
    if state == "head":
        with sqlite3.connect(database) as connection:
            all_indexes = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            missing_indexes = P5_F0_INDEXES - all_indexes
            if missing_indexes:
                problems.append(
                    f"P5-F0 missing required indexes: {sorted(missing_indexes)}"
                )

            fk_set = set()
            for table in sorted(P5_F0_TABLES | {"audit_event", "verification_issue"}):
                for fk in connection.execute(f"PRAGMA foreign_key_list('{table}')"):
                    fk_set.add((table, fk[3], fk[2]))
                    if (table, fk[3], fk[2]) in P5_F0_FKS and fk[6] != "RESTRICT":
                        problems.append(
                            f"P5-F0 {table}.{fk[3]} must use ON DELETE RESTRICT"
                        )
            missing_fks = P5_F0_FKS - fk_set
            if missing_fks:
                problems.append(f"P5-F0 missing real foreign keys: {sorted(missing_fks)}")

            for table, expected_columns in sorted(P5_F0_UNIQUE_KEYS):
                unique_column_sets = set()
                for index_row in connection.execute(f"PRAGMA index_list('{table}')"):
                    if not index_row[2]:
                        continue
                    index_name = index_row[1]
                    columns = tuple(
                        item[2]
                        for item in connection.execute(
                            f"PRAGMA index_info('{index_name}')"
                        )
                    )
                    unique_column_sets.add(columns)
                if expected_columns not in unique_column_sets:
                    problems.append(
                        f"P5-F0 {table} missing unique key {expected_columns}"
                    )

            for table in sorted(P5_F0_IMMUTABLE_TABLES):
                for operation in ("update", "delete"):
                    name = f"trg_{table}_{operation}_immutable"
                    if name not in triggers:
                        problems.append(f"P5-F0 missing immutable trigger {name}")

    # At ``p2`` the exact P2 schema must be intact: the P3 column and trigger
    # must be gone, which is what ``0003 -> 0002`` has to leave behind.
    if state in {"p2", "p1", "base"}:
        if "source_fact_id" in observation_columns:
            problems.append("observation.source_fact_id must not exist below 0003")
        if DOCTOR_TRIGGER_NAME in triggers:
            problems.append(f"trigger {DOCTOR_TRIGGER_NAME} must not exist below 0003")

    expected_revisions = _expected_revisions(state)
    if revisions != expected_revisions:
        problems.append(f"expected alembic_version {expected_revisions}, found {revisions}")

    if state in {"head", "p3_stage1"}:
        references_patient = any(row[2] == "patient" for row in user_foreign_keys)
        if not references_patient:
            problems.append("user.patient_id foreign key to patient is missing")
        if foreign_key_violations:
            problems.append(f"foreign key violations: {foreign_key_violations}")
        partial_index = "uq_observation_checkin_identity"
        with sqlite3.connect(database) as connection:
            indexes = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
        if partial_index not in indexes:
            problems.append(f"missing unique index {partial_index}")

    if problems:
        print("Alembic smoke check: FAIL", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"Alembic smoke check: PASS (state {state}, revision {expected_revisions or 'none'}, "
        f"tables {sorted(tables)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
