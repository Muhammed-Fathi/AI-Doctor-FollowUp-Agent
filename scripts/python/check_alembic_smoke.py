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
    revision ``0008_p4_rb3_review_persistence``; exact P1/P2/P3/F0/F1 objects
    PLUS the three WITHOUT ROWID P4-RB3 tables (``review_item``,
    ``evidence_link``, ``review_evaluation``), nine named indexes including
    both partial unique predicates, 25 RB3 triggers scoped to those three
    tables, all 11 preserved historical triggers, and explicit ``WITHOUT ROWID``
    assertions from ``sqlite_master.sql``.
``p5_f1``
    revision ``0007_p5_run_gate``; exact F0+F1 tables and all earlier
    assertions, excluding the 0008 P4-RB3 tables.
``p5_f0``
    revision ``0006_p5_run_foundation``; exact F0 tables and all earlier
    assertions, excluding the 0007 F1 gate-evidence tables.
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
HEAD_REVISION = "0008_p4_rb3_review_persistence"
P5_F1_REVISION = "0007_p5_run_gate"
P5_F0_REVISION = "0006_p5_run_foundation"
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

#: Exactly the two additional F1 evidence tables ratified for revision 0007.
P5_F1_TABLES = {"run_gate_evaluation", "run_gate_blocker"}
P5_F1_INDEXES = {"ix_gate_run", "ix_gate_blocker_gate"}
P5_F1_FKS = {
    ("run_gate_evaluation", "workflow_run_id", "workflow_run"),
    ("run_gate_blocker", "gate_evaluation_id", "run_gate_evaluation"),
    ("run_gate_blocker", "document_id", "document"),
}
P5_F1_UNIQUE_KEYS = {
    ("run_gate_evaluation", ("idempotency_key",)),
    ("run_gate_evaluation", ("workflow_run_id", "input_fingerprint_sha256", "gate_version")),
}
P5_F1_IMMUTABLE_TABLES = {"run_gate_evaluation", "run_gate_blocker"}

#: P4-RB3 WITHOUT ROWID durable run-bound review persistence (0008).
P4_RB3_TABLES = {"review_item", "evidence_link", "review_evaluation"}
P4_RB3_INDEXES = {
    "ux_review_dedupe",
    "ux_review_order",
    "ix_review_patient_state",
    "ix_review_run",
    "ix_evidence_owner",
    "ux_evidence_link_observation",
    "ux_evidence_link_span",
    "ux_review_evaluation_run",
    "ix_review_evaluation_patient",
}
P4_RB3_TRIGGERS = {
    "trg_review_item_update_immutable",
    "trg_review_item_delete_immutable",
    "trg_review_item_insert_open_only",
    "trg_review_item_run_scope_consistent",
    "trg_evidence_link_update_immutable",
    "trg_evidence_link_delete_immutable",
    "trg_evidence_link_owner_review_item_only",
    "trg_evidence_link_kind_observation_only",
    "trg_evidence_link_owner_exists",
    "trg_evidence_link_reference_same_patient",
    "trg_evidence_link_duplicate_identity",
    "trg_review_evaluation_update_immutable",
    "trg_review_evaluation_delete_immutable",
    "trg_review_evaluation_run_scope_consistent",
    "trg_review_item_insert_sealed",
    "trg_evidence_link_insert_sealed",
    "trg_review_evaluation_insert_sealed",
    "trg_review_item_insert_id_conflict",
    "trg_review_item_insert_dedupe_conflict",
    "trg_review_item_insert_order_conflict",
    "trg_evidence_link_insert_id_conflict",
    "trg_evidence_link_insert_observation_identity_conflict",
    "trg_evidence_link_insert_span_identity_conflict",
    "trg_review_evaluation_insert_id_conflict",
    "trg_review_evaluation_insert_run_conflict",
}
HISTORICAL_11_TRIGGER_SQL = {
    DOCTOR_TRIGGER_NAME: (
        "CREATE TRIGGER trg_fact_verification_doctor_only "
        "BEFORE INSERT ON fact_verification FOR EACH ROW "
        "WHEN (SELECT role FROM user WHERE id = NEW.verified_by_user_id) IS NOT 'doctor' "
        "BEGIN SELECT RAISE(ABORT, 'fact_verification.verified_by_user_id must reference a doctor'); END"
    ),
    "trg_run_selected_document_update_immutable": (
        "CREATE TRIGGER trg_run_selected_document_update_immutable "
        "BEFORE UPDATE ON run_selected_document "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_selected_document_delete_immutable": (
        "CREATE TRIGGER trg_run_selected_document_delete_immutable "
        "BEFORE DELETE ON run_selected_document "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_selected_observation_update_immutable": (
        "CREATE TRIGGER trg_run_selected_observation_update_immutable "
        "BEFORE UPDATE ON run_selected_observation "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_selected_observation_delete_immutable": (
        "CREATE TRIGGER trg_run_selected_observation_delete_immutable "
        "BEFORE DELETE ON run_selected_observation "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_source_omission_update_immutable": (
        "CREATE TRIGGER trg_run_source_omission_update_immutable "
        "BEFORE UPDATE ON run_source_omission "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_source_omission_delete_immutable": (
        "CREATE TRIGGER trg_run_source_omission_delete_immutable "
        "BEFORE DELETE ON run_source_omission "
        "BEGIN SELECT RAISE(ABORT, 'run source manifest is immutable'); END"
    ),
    "trg_run_gate_evaluation_update_immutable": (
        "CREATE TRIGGER trg_run_gate_evaluation_update_immutable "
        "BEFORE UPDATE ON run_gate_evaluation "
        "BEGIN SELECT RAISE(ABORT, 'run gate evidence is immutable'); END"
    ),
    "trg_run_gate_evaluation_delete_immutable": (
        "CREATE TRIGGER trg_run_gate_evaluation_delete_immutable "
        "BEFORE DELETE ON run_gate_evaluation "
        "BEGIN SELECT RAISE(ABORT, 'run gate evidence is immutable'); END"
    ),
    "trg_run_gate_blocker_update_immutable": (
        "CREATE TRIGGER trg_run_gate_blocker_update_immutable "
        "BEFORE UPDATE ON run_gate_blocker "
        "BEGIN SELECT RAISE(ABORT, 'run gate evidence is immutable'); END"
    ),
    "trg_run_gate_blocker_delete_immutable": (
        "CREATE TRIGGER trg_run_gate_blocker_delete_immutable "
        "BEFORE DELETE ON run_gate_blocker "
        "BEGIN SELECT RAISE(ABORT, 'run gate evidence is immutable'); END"
    ),
}

#: Pre-0008 forbidden downstream entities; at 0008 head the three authorized
#: RB3 tables are permitted while all remaining future tables stay forbidden.
P4_PLUS_TABLES = {
    "review_item",
    "evidence_link",
    "review_evaluation",
    "summary_draft",
    "approval_decision",
    "follow_up_task",
    "in_app_notification",
    "node_event",
    "summary_claim",
}
POST_RB3_FUTURE_TABLES = P4_PLUS_TABLES - P4_RB3_TABLES

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

VALID_STATES = {"head", "p5_f1", "p5_f0", "p3_stage1", "p3_recovery", "p3", "p2", "p1", "base"}


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
        return (
            P1_TABLES
            | P2_TABLES
            | P3_TABLES
            | {PAGE_TEXT_TABLE}
            | P5_F0_TABLES
            | P5_F1_TABLES
            | P4_RB3_TABLES
        )
    if state == "p5_f1":
        return P1_TABLES | P2_TABLES | P3_TABLES | {PAGE_TEXT_TABLE} | P5_F0_TABLES | P5_F1_TABLES
    if state == "p5_f0":
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
    if state == "p5_f1":
        return [P5_F1_REVISION]
    if state == "p5_f0":
        return [P5_F0_REVISION]
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
            "[--state head|p5_f1|p5_f0|p3_stage1|p3_recovery|p3|p2|p1|base]",
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

    early = (POST_RB3_FUTURE_TABLES if state == "head" else P4_PLUS_TABLES) & tables
    if early:
        problems.append(f"later-phase tables must not exist: {sorted(early)}")

    # --- P3 structural assertions (owner decision D-05) ---------------------
    # At ``head``/``p3``: the deferred P2 column, its unique index and the
    # doctor-only trigger must all exist. A "later-phase" table check alone
    # would not catch a P3 revision that forgot one of them.
    if state in {"head", "p5_f1", "p5_f0", "p3_stage1", "p3_recovery", "p3"}:
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
    if state in {"head", "p5_f1", "p5_f0", "p3_stage1", "p3_recovery"}:
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
    if state in {"head", "p5_f1", "p5_f0", "p3_stage1"}:
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
    if state in {"head", "p5_f1", "p5_f0"}:
        with sqlite3.connect(database) as connection:
            all_indexes = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
            missing_indexes = P5_F0_INDEXES - all_indexes
            if missing_indexes:
                problems.append(f"P5-F0 missing required indexes: {sorted(missing_indexes)}")

            fk_set = set()
            for table in sorted(P5_F0_TABLES | {"audit_event", "verification_issue"}):
                for fk in connection.execute(f"PRAGMA foreign_key_list('{table}')"):
                    fk_set.add((table, fk[3], fk[2]))
                    if (table, fk[3], fk[2]) in P5_F0_FKS and fk[6] != "RESTRICT":
                        problems.append(f"P5-F0 {table}.{fk[3]} must use ON DELETE RESTRICT")
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
                        item[2] for item in connection.execute(f"PRAGMA index_info('{index_name}')")
                    )
                    unique_column_sets.add(columns)
                if expected_columns not in unique_column_sets:
                    problems.append(f"P5-F0 {table} missing unique key {expected_columns}")

            for table in sorted(P5_F0_IMMUTABLE_TABLES):
                for operation in ("update", "delete"):
                    name = f"trg_{table}_{operation}_immutable"
                    if name not in triggers:
                        problems.append(f"P5-F0 missing immutable trigger {name}")

    # --- 0007 P5-F1 immutable run-gate evidence (no graph execution) ------
    if state in {"head", "p5_f1"}:
        with sqlite3.connect(database) as connection:
            all_indexes = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
            missing_indexes = P5_F1_INDEXES - all_indexes
            if missing_indexes:
                problems.append(f"P5-F1 missing required indexes: {sorted(missing_indexes)}")

            foreign_keys = set()
            for table in sorted(P5_F1_TABLES):
                for fk in connection.execute(f"PRAGMA foreign_key_list('{table}')"):
                    key = (table, fk[3], fk[2])
                    foreign_keys.add(key)
                    if key in P5_F1_FKS and fk[6] != "RESTRICT":
                        problems.append(f"P5-F1 {table}.{fk[3]} must use ON DELETE RESTRICT")
            missing_fks = P5_F1_FKS - foreign_keys
            if missing_fks:
                problems.append(f"P5-F1 missing real foreign keys: {sorted(missing_fks)}")

            for table, expected_columns in sorted(P5_F1_UNIQUE_KEYS):
                found = set()
                for index_row in connection.execute(f"PRAGMA index_list('{table}')"):
                    if not index_row[2]:
                        continue
                    index_name = index_row[1]
                    found.add(
                        tuple(
                            item[2]
                            for item in connection.execute(f"PRAGMA index_info('{index_name}')")
                        )
                    )
                if expected_columns not in found:
                    problems.append(f"P5-F1 {table} missing unique key {expected_columns}")

            for table in sorted(P5_F1_IMMUTABLE_TABLES):
                for operation in ("update", "delete"):
                    name = f"trg_{table}_{operation}_immutable"
                    if name not in triggers:
                        problems.append(f"P5-F1 missing immutable trigger {name}")

            table_ddl = {
                row[0]: row[1] or ""
                for row in connection.execute(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type='table' AND name IN ('run_gate_evaluation', 'run_gate_blocker')"
                )
            }
            for name in (
                "decision_allowed",
                "fingerprint_sha_length",
                "idem_sha_length",
                "block_count",
            ):
                if name not in table_ddl.get("run_gate_evaluation", ""):
                    problems.append(f"P5-F1 missing run_gate_evaluation CHECK {name}")
            if "issue_type_allowed" not in table_ddl.get("run_gate_blocker", ""):
                problems.append("P5-F1 missing closed run_gate_blocker issue_type CHECK")

    # --- 0008 P4-RB3 WITHOUT ROWID durable review persistence -------------
    if state == "head":
        with sqlite3.connect(database) as connection:
            rb3_indexes = {
                row[0]: row[1] or ""
                for row in connection.execute(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type='index' AND tbl_name IN ('review_item', 'evidence_link', 'review_evaluation') "
                    "AND name NOT LIKE 'sqlite_autoindex_%'"
                )
            }
            if set(rb3_indexes) != P4_RB3_INDEXES:
                problems.append(
                    f"P4-RB3 index mismatch: expected {sorted(P4_RB3_INDEXES)}, "
                    f"found {sorted(rb3_indexes)}"
                )
            if "WHERE kind = 'observation'" not in rb3_indexes.get(
                "ux_evidence_link_observation", ""
            ):
                problems.append(
                    "P4-RB3 ux_evidence_link_observation missing WHERE kind = 'observation' predicate"
                )
            if "WHERE kind = 'document_span'" not in rb3_indexes.get("ux_evidence_link_span", ""):
                problems.append(
                    "P4-RB3 ux_evidence_link_span missing WHERE kind = 'document_span' predicate"
                )

            rb3_triggers = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='trigger' "
                    "AND tbl_name IN ('review_item', 'evidence_link', 'review_evaluation')"
                )
            }
            if rb3_triggers != P4_RB3_TRIGGERS:
                problems.append(
                    f"P4-RB3 triggers mismatch: missing={sorted(P4_RB3_TRIGGERS - rb3_triggers)}, "
                    f"extra={sorted(rb3_triggers - P4_RB3_TRIGGERS)}"
                )

            hist_trigger_sql = {
                row[0]: " ".join((row[1] or "").split())
                for row in connection.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='trigger' "
                    "AND tbl_name NOT IN ('review_item', 'evidence_link', 'review_evaluation')"
                )
            }
            if set(hist_trigger_sql) != set(HISTORICAL_11_TRIGGER_SQL):
                problems.append(
                    f"Historical triggers mismatch after 0008: "
                    f"missing={sorted(set(HISTORICAL_11_TRIGGER_SQL) - set(hist_trigger_sql))}, "
                    f"extra={sorted(set(hist_trigger_sql) - set(HISTORICAL_11_TRIGGER_SQL))}"
                )
            for hname, expected_sql in sorted(HISTORICAL_11_TRIGGER_SQL.items()):
                actual_sql = hist_trigger_sql.get(hname)
                if actual_sql != expected_sql:
                    problems.append(
                        f"Historical trigger {hname} definition altered: "
                        f"expected {expected_sql!r}, found {actual_sql!r}"
                    )

            all_table_ddl = {
                row[0]: row[1] or ""
                for row in connection.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='table'"
                )
            }
            for rb3_tbl in sorted(P4_RB3_TABLES):
                if "WITHOUT ROWID" not in all_table_ddl.get(rb3_tbl, "").upper():
                    problems.append(f"P4-RB3 table {rb3_tbl} must be declared WITHOUT ROWID")
            for other_tbl, ddl in sorted(all_table_ddl.items()):
                if other_tbl not in P4_RB3_TABLES and "WITHOUT ROWID" in ddl.upper():
                    problems.append(f"Pre-existing table {other_tbl} must not carry WITHOUT ROWID")

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

    if state in {"head", "p5_f1", "p5_f0", "p3_stage1"}:
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
