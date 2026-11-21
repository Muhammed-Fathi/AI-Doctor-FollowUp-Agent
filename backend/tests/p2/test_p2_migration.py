"""The P2 Alembic revision: schema, reversibility and foreign-key safety.

This module exercises the real migration files through the Alembic command API,
so the DDL under test is the DDL that ships. It covers the review items that the
earlier (metadata-only) tests could not:

* the exact schema at ``head``, at ``0001`` and at ``base``;
* ``0002 -> 0001`` leaves P1's ``schema_meta`` intact (``downgrade base`` cannot
  prove that, because it also drops P1);
* ``0002 -> base -> 0002`` round-trips to the documented empty state and back;
* migrations run with foreign-key enforcement off on their own connection while
  the runtime engine keeps it on;
* ``PRAGMA foreign_key_check`` is empty after every transition, and the
  ``user.patient_id`` foreign key really exists in the migrated schema;
* the migration agrees with the ORM metadata (no table/index drift).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.paths import REPO_ROOT
from app.db.base import Base
from app.db.session import create_db_engine

P1_TABLES = {"schema_meta", "alembic_version"}
P2_TABLES = {
    "audit_event",
    "checkin_idempotency",
    "encounter",
    "observation",
    "patient",
    "session",
    "user",
}
# Keep the historical P3 schema gate pinned to its own revision.
P3_STAGE1_REVISION = "0005_p3_ocr_provenance"
# Migration head advances for the owner-approved P5-F0 foundation.
HEAD_REVISION = "0006_p5_run_foundation"
P4_REVISION = "0004_p3_rejection_recovery"
P2_REVISION = "0002_p2_patient_domain"
P1_REVISION = "0001_p1_baseline"

#: Tables owned by P3 (``0003`` + Stage 1 ``0005``). The exact P2 assertions
#: below are kept by migrating to ``P2_REVISION`` rather than to ``head``, so
#: "0002 creates exactly the seven P2 tables" is still proven after P3 exists
#: (owner decision D-05).
P3_TABLES = {
    "document",
    "document_page_text",
    "extraction_attempt",
    "extracted_fact",
    "fact_verification",
    "verification_issue",
}
P5_F0_TABLES = {
    "workflow_run",
    "run_selected_document",
    "run_selected_observation",
    "run_source_omission",
}


def _config(tmp_path: Path) -> tuple[Config, str]:
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config, url


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar()


def _fk_violations(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        return connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()


def test_0002_creates_exactly_the_p2_allowlist(tmp_path: Path) -> None:
    """``0002`` adds the seven P2 tables and nothing else.

    Migrates to ``0002`` rather than ``head`` so the historical claim stays
    exactly checkable after P3 adds ``0003`` (owner decision D-05).
    """
    config, url = _config(tmp_path)
    command.upgrade(config, P2_REVISION)

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES
        assert _revision(engine) == P2_REVISION
        assert _fk_violations(engine) == []
        user_fks = inspect(engine).get_foreign_keys("user")
        assert any(fk["referred_table"] == "patient" for fk in user_fks)
        indexes = {index["name"] for index in inspect(engine).get_indexes("observation")}
        assert "uq_observation_checkin_identity" in indexes
    finally:
        engine.dispose()


def test_0003_creates_exactly_the_p3_allowlist(tmp_path: Path) -> None:
    """``0003`` adds the five P3 tables, the deferred column and the trigger.

    Exactness is preserved: ``P1 | P2 | P3`` and nothing else, so a P4+ table
    still fails this assertion.
    """
    config, url = _config(tmp_path)
    command.upgrade(config, P3_STAGE1_REVISION)

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES | P3_TABLES
        assert _revision(engine) == P3_STAGE1_REVISION
        assert _fk_violations(engine) == []

        observation_columns = {
            column["name"] for column in inspect(engine).get_columns("observation")
        }
        assert "source_fact_id" in observation_columns

        observation_indexes = {
            index["name"] for index in inspect(engine).get_indexes("observation")
        }
        assert "ux_obs_source_fact" in observation_indexes

        with engine.connect() as connection:
            triggers = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='trigger'")
                )
            }
        assert "trg_fact_verification_doctor_only" in triggers
    finally:
        engine.dispose()


def test_0003_downgrade_preserves_p2_rows(tmp_path: Path) -> None:
    """``0003 -> 0002`` keeps every P2 row and removes only P3's objects.

    This is the "preserve P1/P2 data" guarantee: the deferred column is additive
    and nullable, so existing observations survive with ``source_fact_id`` NULL.
    """
    config, url = _config(tmp_path)
    command.upgrade(config, P3_STAGE1_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO user (id, username, display_name, role, password_hash, "
                    "timezone, is_active, created_at) VALUES "
                    "('u-doc', 'doctor1', 'Dr', 'doctor', 'x', 'UTC', 1, '2026-11-14T12:00:00Z')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO patient (id, display_name, assigned_doctor_id, external_ref, "
                    "data_source, created_at, updated_at) VALUES "
                    "('p1', 'Demo Patient A', 'u-doc', 'DEMO-A', 'synthetic_fixture', "
                    "'2026-11-14T12:00:00Z', '2026-11-14T12:00:00Z')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO observation (id, patient_id, measure_type, value, unit, "
                    "measured_at, source, validation, trust_level, created_at) VALUES "
                    "('o1', 'p1', 'glucose', 98.0, 'mg/dL', '2026-10-02T08:10:00Z', "
                    "'seed_fixture', 'ok', 'self_reported_validated', '2026-11-14T12:00:00Z')"
                )
            )
    finally:
        engine.dispose()

    command.downgrade(config, P2_REVISION)

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES
        assert _revision(engine) == P2_REVISION
        assert _fk_violations(engine) == []
        columns = {column["name"] for column in inspect(engine).get_columns("observation")}
        assert "source_fact_id" not in columns
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM observation")).scalar_one() == 1
    finally:
        engine.dispose()


def test_downgrade_to_p1_preserves_the_baseline_table(tmp_path: Path) -> None:
    """``0002 -> 0001`` removes the P2 tables and leaves P1 exactly as it was."""
    config, url = _config(tmp_path)
    command.upgrade(config, "head")
    command.downgrade(config, P1_REVISION)

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES
        assert _revision(engine) == P1_REVISION
        with engine.connect() as connection:
            stored = connection.execute(text("SELECT count(*) FROM schema_meta")).scalar_one()
        assert stored == 0  # the table exists and is queryable
    finally:
        engine.dispose()


def test_full_round_trip_to_base_and_back(tmp_path: Path) -> None:
    """``head -> base -> head`` reaches the documented empty state and recovers."""
    config, url = _config(tmp_path)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == {"alembic_version"}
        assert _revision(engine) is None
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES | P3_TABLES | P5_F0_TABLES
        assert _revision(engine) == HEAD_REVISION
        assert _fk_violations(engine) == []
        run_fk_targets = {
            fk["referred_table"] for fk in inspect(engine).get_foreign_keys("run_selected_document")
        }
        assert run_fk_targets == {"workflow_run", "document"}
    finally:
        engine.dispose()


def test_p1_to_head_to_p1_to_head_is_stable(tmp_path: Path) -> None:
    """The sequence the gate runs (0001 -> head -> 0001 -> head) is clean each time."""
    config, url = _config(tmp_path)

    command.upgrade(config, P1_REVISION)
    command.upgrade(config, "head")
    command.downgrade(config, P1_REVISION)
    command.upgrade(config, "head")

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES | P3_TABLES | P5_F0_TABLES
        assert _revision(engine) == HEAD_REVISION
        assert _fk_violations(engine) == []
        run_fk_targets = {
            fk["referred_table"] for fk in inspect(engine).get_foreign_keys("run_selected_document")
        }
        assert run_fk_targets == {"workflow_run", "document"}
    finally:
        engine.dispose()


def test_migrations_do_not_leave_foreign_keys_disabled_for_runtime(tmp_path: Path) -> None:
    """Alembic disables enforcement on its own connection only.

    ``migrations/env.py`` attaches a ``connect`` listener that turns
    ``PRAGMA foreign_keys`` off for the migration engine, because ``DROP TABLE``
    of a referenced parent would otherwise fail. The runtime engine must still
    report ``ON`` — otherwise the P2 foreign keys would be decorative.
    """
    config, url = _config(tmp_path)
    command.upgrade(config, "head")
    command.downgrade(config, P1_REVISION)
    command.upgrade(config, "head")

    runtime = create_db_engine(url)
    try:
        with runtime.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        runtime.dispose()


def test_migrated_schema_enforces_the_patient_foreign_key(tmp_path: Path) -> None:
    """On the migrated database — not just the metadata one — orphans are rejected."""
    config, url = _config(tmp_path)
    command.upgrade(config, "head")

    engine = create_db_engine(url)
    try:
        with engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO user (id, username, display_name, role, password_hash, "
                    "patient_id, timezone, is_active, created_at, last_login_at) VALUES "
                    "('u1', 'ghost', 'Ghost', 'patient', 'x', 'missing-patient', "
                    "'Africa/Cairo', 1, '2026-11-14T12:00:00Z', NULL)"
                )
            )
    finally:
        engine.dispose()


def test_migration_matches_the_orm_metadata(tmp_path: Path) -> None:
    """No drift: the migrated tables and indexes equal the declarative metadata."""
    config, url = _config(tmp_path)
    command.upgrade(config, "head")

    engine = create_db_engine(url)
    try:
        migrated_tables = _tables(engine) - {"alembic_version"}
        metadata_tables = set(Base.metadata.tables)
        assert migrated_tables == metadata_tables

        inspector = inspect(engine)
        for table in sorted(metadata_tables):
            migrated_indexes = {index["name"] for index in inspector.get_indexes(table)}
            declared_indexes = {index.name for index in Base.metadata.tables[table].indexes}
            assert migrated_indexes == declared_indexes, table
    finally:
        engine.dispose()


# --- 0004_p3_rejection_recovery (R21 §4.10) --------------------------------
#
# The recovery column is a self-referencing foreign key on ``document``. SQLite
# cannot add a foreign key to an existing table with a plain ``ALTER TABLE``, so
# ``0004`` rebuilds the table in Alembic batch mode. A rebuild is exactly the
# operation that silently drops CHECK constraints, indexes or rows, so these
# tests assert what survives rather than trusting the DDL.

P3_REVISION = "0003_p3_documents"
RECOVERY_COLUMN = "recovered_from_document_id"
RECOVERY_INDEX = "ix_document_recovered_from"

#: Named CHECK constraints ``0003`` put on ``document``; all must survive the
#: ``0004`` rebuild. Losing one would let an invalid status or MIME type in
#: without any test failing elsewhere.
DOCUMENT_CHECK_CONSTRAINTS = (
    "mime_type_allowed",
    "status_allowed",
    "sha256_length",
    "size_within_cap",
    "page_count_within_cap",
    "filename_not_empty",
)


def _document_ddl(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='document'")
        ).scalar_one()


def _document_columns(engine: Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("document")}


def _document_indexes(engine: Engine) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes("document")}


def _seed_patient_and_doctor(engine: Engine) -> None:
    """Insert one doctor and one patient: the minimum a document row needs."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO user (id, username, display_name, role, password_hash, "
                "timezone, is_active, created_at) VALUES "
                "('u-doc', 'doctor1', 'Dr', 'doctor', 'x', 'UTC', 1, '2026-11-14T12:00:00Z')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO patient (id, display_name, date_of_birth, sex_at_birth, "
                "assigned_doctor_id, external_ref, data_source, created_at, updated_at) VALUES "
                "('p-1', 'Demo A', '1990-01-01', 'female', 'u-doc', 'DEMO-A-001', "
                "'synthetic_fixture', '2026-11-14T12:00:00Z', '2026-11-14T12:00:00Z')"
            )
        )


def _seed_two_documents(engine: Engine) -> tuple[str, str]:
    """Insert one patient, one doctor and two document rows; return the ids.

    Explicit SQL again: the ORM models ``head``, so it cannot write rows into a
    database still at ``0003`` — which is exactly the pre-existing state this
    test needs.
    """
    parent = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _seed_patient_and_doctor(engine)
    with engine.begin() as connection:
        for index, sha in enumerate(("a" * 64, "b" * 64)):
            connection.execute(
                text(
                    "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                    "original_filename, stored_path, mime_type, sha256, size_bytes, "
                    "page_count, extraction_status, uploaded_at) VALUES "
                    "(:id, 'p-1', 'u-doc', 'r.pdf', 'r.pdf', 'application/pdf', :sha, "
                    "10, 1, 'failed', '2026-11-14T12:00:00Z')"
                ),
                {
                    "id": parent if index == 0 else "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    "sha": sha,
                },
            )
    return parent, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def test_0004_adds_the_recovery_column_index_and_restrict_self_fk(tmp_path: Path) -> None:
    """At ``0004`` the column, its index and a RESTRICT self-FK are all present."""
    config, url = _config(tmp_path)
    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        assert _revision(engine) == P4_REVISION
        assert RECOVERY_COLUMN in _document_columns(engine)
        assert RECOVERY_INDEX in _document_indexes(engine)
        # The pre-existing indexes must not have been lost in the rebuild.
        assert {"ix_document_patient", "ux_document_sha_patient"} <= _document_indexes(engine)

        with engine.connect() as connection:
            foreign_keys = [
                dict(row._mapping) if hasattr(row, "_mapping") else row
                for row in connection.exec_driver_sql("PRAGMA foreign_key_list('document')")
            ]
        self_fk = [
            row
            for row in foreign_keys
            if (row["from"] if isinstance(row, dict) else row[3]) == RECOVERY_COLUMN
        ]
        assert len(self_fk) == 1
        on_delete = self_fk[0]["on_delete"] if isinstance(self_fk[0], dict) else self_fk[0][6]
        assert on_delete == "RESTRICT"
        assert _fk_violations(engine) == []
    finally:
        engine.dispose()


def test_0004_rebuild_preserves_the_document_check_constraints(tmp_path: Path) -> None:
    """A batch rebuild must not silently drop ``0003``'s CHECK constraints."""
    config, url = _config(tmp_path)
    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        ddl = _document_ddl(engine)
        for name in DOCUMENT_CHECK_CONSTRAINTS:
            assert name in ddl, f"CHECK constraint {name} was lost by the 0004 rebuild"
        # And they are still *enforced*, not merely present as text.
        _seed_patient_and_doctor(engine)
        with engine.begin() as connection, pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                    "original_filename, stored_path, mime_type, sha256, size_bytes, "
                    "page_count, extraction_status, uploaded_at) VALUES "
                    "('bad', 'p-1', 'u-doc', 'r.pdf', 'r.pdf', 'text/plain', :sha, 10, 1, "
                    "'failed', '2026-11-14T12:00:00Z')"
                ),
                {"sha": "c" * 64},
            )
    finally:
        engine.dispose()


def test_0004_preserves_existing_rows_through_the_rebuild(tmp_path: Path) -> None:
    """Rows written at ``0003`` keep their values and read ``NULL`` afterwards."""
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        _seed_two_documents(engine)
        with engine.connect() as connection:
            before = connection.execute(text("SELECT COUNT(*) FROM document")).scalar()
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM document")).scalar() == before
            links = connection.execute(
                text(f"SELECT {RECOVERY_COLUMN} FROM document ORDER BY id")
            ).fetchall()
            assert [row[0] for row in links] == [None, None]
            # Existing non-null values must be intact, not reset by the copy.
            statuses = {
                row[0] for row in connection.execute(text("SELECT extraction_status FROM document"))
            }
            assert statuses == {"failed"}
        assert _fk_violations(engine) == []
    finally:
        engine.dispose()


def test_0004_downgrade_refuses_and_changes_nothing_when_links_exist(tmp_path: Path) -> None:
    """A live recovery link must make ``0004 -> 0003`` refuse, losing nothing."""
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        parent, second = _seed_two_documents(engine)
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(f"UPDATE document SET {RECOVERY_COLUMN} = :parent WHERE id = :child"),
                {"parent": parent, "child": second},
            )
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError) as refusal:
        command.downgrade(config, P3_REVISION)
    # The refusal must explain itself, not merely fail.
    assert RECOVERY_COLUMN in str(refusal.value)

    engine = create_db_engine(url)
    try:
        # Nothing was dropped and no row was changed.
        assert RECOVERY_COLUMN in _document_columns(engine)
        assert RECOVERY_INDEX in _document_indexes(engine)
        assert _revision(engine) == P4_REVISION
        with engine.connect() as connection:
            link = connection.execute(
                text(f"SELECT {RECOVERY_COLUMN} FROM document WHERE id = :child"),
                {"child": second},
            ).scalar_one()
        assert link == parent
    finally:
        engine.dispose()


def test_0004_downgrade_round_trips_when_no_links_exist(tmp_path: Path) -> None:
    """With no links, ``0004 -> 0003 -> 0004`` is clean and rows survive."""
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        _seed_two_documents(engine)
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT COUNT(*) FROM document")).scalar()
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)
    command.downgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        assert RECOVERY_COLUMN not in _document_columns(engine)
        assert RECOVERY_INDEX not in _document_indexes(engine)
        assert _revision(engine) == P3_REVISION
        assert {"ix_document_patient", "ux_document_sha_patient"} <= _document_indexes(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM document")).scalar() == rows
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        assert RECOVERY_COLUMN in _document_columns(engine)
        assert _revision(engine) == P4_REVISION
        assert _fk_violations(engine) == []
    finally:
        engine.dispose()


# --- 0004 against a fully populated P3 dependency graph --------------------
#
# `0004` rebuilds ``document`` — the parent of every P3 table — while the
# migration engine runs with foreign keys OFF. The tests above prove the
# *schema* survives that rebuild; this one proves the *data graph* does, which is
# the property a real deployment actually depends on.
#
# The graph is seeded at 0003 through explicit SQL (the ORM models `head`, so it
# cannot write into a pre-0004 database) and every value is chosen to satisfy the
# real CHECK constraints, so nothing here invents a column or bypasses a rule.

#: Stable ids so a failure message points at a named row rather than a random uuid.
GRAPH_PATIENT = "11111111-1111-4111-8111-111111111111"
GRAPH_DOCTOR = "22222222-2222-4222-8222-222222222222"
GRAPH_DOCUMENT = "33333333-3333-4333-8333-333333333333"
GRAPH_RECOVERY_DOCUMENT = "44444444-4444-4444-8444-444444444444"
GRAPH_ATTEMPT = "55555555-5555-4555-8555-555555555555"
GRAPH_FACT_VALUE = "66666666-6666-4666-8666-666666666666"
GRAPH_FACT_TEST = "77777777-7777-4777-8777-777777777777"
GRAPH_VERIFICATION = "88888888-8888-4888-8888-888888888888"
GRAPH_ISSUE = "99999999-9999-4999-8999-999999999999"
GRAPH_OBSERVATION = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def _seed_populated_p3_graph(engine: Engine) -> None:
    """Seed one full P3 graph at revision ``0003``.

    Shape: a patient, their assigned doctor, an uploaded document with one
    extraction attempt and two candidate facts, one append-only decision that
    verified the ``value`` fact, one open ``VI-002`` issue linked to both facts,
    and one ``doctor_verified`` observation whose ``source_fact_id`` is the
    verified fact.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO user (id, username, display_name, role, password_hash, "
                "timezone, is_active, created_at) VALUES "
                "(:id, 'doctor1', 'Dr One', 'doctor', 'x', 'UTC', 1, '2026-11-14T12:00:00Z')"
            ),
            {"id": GRAPH_DOCTOR},
        )
        connection.execute(
            text(
                "INSERT INTO patient (id, display_name, date_of_birth, sex_at_birth, "
                "assigned_doctor_id, external_ref, data_source, created_at, updated_at) "
                "VALUES (:id, 'Demo Patient A', '1990-01-01', 'female', :doctor, "
                "'DEMO-A-001', 'synthetic_fixture', '2026-11-14T12:00:00Z', "
                "'2026-11-14T12:00:00Z')"
            ),
            {"id": GRAPH_PATIENT, "doctor": GRAPH_DOCTOR},
        )
        connection.execute(
            text(
                "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                "original_filename, stored_path, mime_type, sha256, size_bytes, "
                "page_count, extraction_status, failure_code, document_patient_ref, "
                "uploaded_at) VALUES (:id, :patient, :doctor, 'report.pdf', 'stored.pdf', "
                "'application/pdf', :sha, 1024, 1, 'needs_verification', NULL, "
                "'DEMO-A-001', '2026-11-14T12:00:00Z')"
            ),
            {
                "id": GRAPH_DOCUMENT,
                "patient": GRAPH_PATIENT,
                "doctor": GRAPH_DOCTOR,
                "sha": "a" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO extraction_attempt (id, document_id, path, preprocessing, "
                "engine_confidence, text_char_count, page_from, page_to, succeeded, "
                "error_code, duration_ms, tool_version, created_at) VALUES "
                "(:id, :document, 'pypdf', 'none', 0.92, 240, 0, 0, 1, NULL, 37, "
                "'pypdf-1.0', '2026-11-14T12:00:01Z')"
            ),
            {"id": GRAPH_ATTEMPT, "document": GRAPH_DOCUMENT},
        )

        facts = (
            # (id, field_name, raw_text, normalized_value, unit, extractor, status, flags)
            (GRAPH_FACT_VALUE, "value", "104", "104", "mg/dL", "pypdf", "verified", '["clean"]'),
            (
                GRAPH_FACT_TEST,
                "test_name",
                "Fasting glucose",
                None,
                None,
                "tesseract",
                "pending",
                '["clean"]',
            ),
        )
        for fact_id, field, raw, normalized, unit, extractor, status, flags in facts:
            connection.execute(
                text(
                    "INSERT INTO extracted_fact (id, document_id, patient_id, field_name, "
                    "raw_text, normalized_value, unit, page_index, char_start, char_end, "
                    "extractor, corrected_from_fact_id, quality_flags, confidence, "
                    "verification_status, created_at) VALUES "
                    "(:id, :document, :patient, :field, :raw, :normalized, :unit, 0, 10, 20, "
                    ":extractor, NULL, :flags, 0.9, :status, '2026-11-14T12:00:02Z')"
                ),
                {
                    "id": fact_id,
                    "document": GRAPH_DOCUMENT,
                    "patient": GRAPH_PATIENT,
                    "field": field,
                    "raw": raw,
                    "normalized": normalized,
                    "unit": unit,
                    "extractor": extractor,
                    "flags": flags,
                    "status": status,
                },
            )

        connection.execute(
            text(
                "INSERT INTO fact_verification (id, fact_id, decision, previous_value, "
                "new_value, new_unit, reason, verified_by_user_id, decided_at) VALUES "
                "(:id, :fact, 'verified', '104', NULL, NULL, NULL, :doctor, "
                "'2026-11-14T12:05:00Z')"
            ),
            {"id": GRAPH_VERIFICATION, "fact": GRAPH_FACT_VALUE, "doctor": GRAPH_DOCTOR},
        )
        connection.execute(
            text(
                "INSERT INTO verification_issue (id, patient_id, workflow_run_id, "
                "document_id, issue_type, reason_code, fact_ids, blocking, message, "
                "state, created_at) VALUES (:id, :patient, NULL, :document, 'VI-002', "
                "'fact_unverified', :fact_ids, 1, 'One extracted value is not yet verified.', "
                "'open', '2026-11-14T12:05:01Z')"
            ),
            {
                "id": GRAPH_ISSUE,
                "patient": GRAPH_PATIENT,
                "document": GRAPH_DOCUMENT,
                "fact_ids": f'["{GRAPH_FACT_VALUE}","{GRAPH_FACT_TEST}"]',
            },
        )
        connection.execute(
            text(
                "INSERT INTO observation (id, patient_id, encounter_id, measure_type, value, "
                "unit, measured_at, source, validation, trust_level, verified_by_user_id, "
                "verified_at, note, created_at, created_by_user_id, source_fact_id) VALUES "
                "(:id, :patient, NULL, 'glucose', 104.0, 'mg/dL', '2026-11-14T00:00:00Z', "
                "'verified_document', 'ok', 'doctor_verified', :doctor, "
                "'2026-11-14T12:05:00Z', NULL, '2026-11-14T12:05:00Z', :doctor, :fact)"
            ),
            {
                "id": GRAPH_OBSERVATION,
                "patient": GRAPH_PATIENT,
                "doctor": GRAPH_DOCTOR,
                "fact": GRAPH_FACT_VALUE,
            },
        )


def _graph_counts(engine: Engine) -> dict[str, int]:
    """Row counts for every table in the seeded P3 graph."""
    tables = (
        "user",
        "patient",
        "document",
        "extraction_attempt",
        "extracted_fact",
        "fact_verification",
        "verification_issue",
        "observation",
    )
    with engine.connect() as connection:
        return {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in tables
        }


def _graph_links(engine: Engine) -> dict[str, object]:
    """Every cross-row reference the graph depends on, read back from storage."""
    with engine.connect() as connection:
        return {
            "attempt_document": connection.execute(
                text("SELECT document_id FROM extraction_attempt WHERE id = :id"),
                {"id": GRAPH_ATTEMPT},
            ).scalar_one(),
            "fact_documents": sorted(
                row[0]
                for row in connection.execute(
                    text("SELECT document_id FROM extracted_fact WHERE id IN (:a, :b)"),
                    {"a": GRAPH_FACT_VALUE, "b": GRAPH_FACT_TEST},
                )
            ),
            "fact_statuses": sorted(
                row[0]
                for row in connection.execute(
                    text("SELECT verification_status FROM extracted_fact WHERE id IN (:a, :b)"),
                    {"a": GRAPH_FACT_VALUE, "b": GRAPH_FACT_TEST},
                )
            ),
            "verification_fact": connection.execute(
                text("SELECT fact_id FROM fact_verification WHERE id = :id"),
                {"id": GRAPH_VERIFICATION},
            ).scalar_one(),
            "verification_doctor": connection.execute(
                text("SELECT verified_by_user_id FROM fact_verification WHERE id = :id"),
                {"id": GRAPH_VERIFICATION},
            ).scalar_one(),
            "issue_document": connection.execute(
                text("SELECT document_id FROM verification_issue WHERE id = :id"),
                {"id": GRAPH_ISSUE},
            ).scalar_one(),
            "issue_type": connection.execute(
                text("SELECT issue_type FROM verification_issue WHERE id = :id"),
                {"id": GRAPH_ISSUE},
            ).scalar_one(),
            "issue_state": connection.execute(
                text("SELECT state FROM verification_issue WHERE id = :id"),
                {"id": GRAPH_ISSUE},
            ).scalar_one(),
            "issue_fact_ids": connection.execute(
                text("SELECT fact_ids FROM verification_issue WHERE id = :id"),
                {"id": GRAPH_ISSUE},
            ).scalar_one(),
            "observation_source_fact": connection.execute(
                text("SELECT source_fact_id FROM observation WHERE id = :id"),
                {"id": GRAPH_OBSERVATION},
            ).scalar_one(),
            "observation_trust": connection.execute(
                text("SELECT trust_level FROM observation WHERE id = :id"),
                {"id": GRAPH_OBSERVATION},
            ).scalar_one(),
            "observation_doctor": connection.execute(
                text("SELECT verified_by_user_id FROM observation WHERE id = :id"),
                {"id": GRAPH_OBSERVATION},
            ).scalar_one(),
        }


def _assert_graph_intact(engine: Engine, before: dict[str, object]) -> None:
    """Assert nothing in the seeded graph changed and FK integrity holds."""
    after = _graph_links(engine)
    assert after == before, "a reference in the populated P3 graph was rewritten"
    # Runtime-equivalent enforcement: the migration engine runs with FKs off, so
    # this must be asserted on a connection that turns them back on.
    assert _fk_violations(engine) == []
    # The observation still points at a fact that still belongs to the document,
    # which is the two-hop lineage the recovery link sits beside.
    assert after["observation_source_fact"] == GRAPH_FACT_VALUE
    assert after["verification_fact"] == GRAPH_FACT_VALUE
    assert after["issue_document"] == GRAPH_DOCUMENT


def test_0004_preserves_a_populated_p3_graph(tmp_path: Path) -> None:
    """``0003 -> 0004`` keeps every P3 row, reference, decision and lineage."""
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        _seed_populated_p3_graph(engine)
        counts_before = _graph_counts(engine)
        links_before = _graph_links(engine)
        assert counts_before["extracted_fact"] == 2
        assert counts_before["fact_verification"] == 1
        assert counts_before["verification_issue"] == 1
        assert counts_before["observation"] == 1
        assert _fk_violations(engine) == [], "the seeded graph must itself be consistent"
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        assert _revision(engine) == P4_REVISION
        assert _graph_counts(engine) == counts_before
        _assert_graph_intact(engine, links_before)
    finally:
        engine.dispose()


def test_0004_graph_survives_downgrade_round_trip_when_no_link_exists(tmp_path: Path) -> None:
    """``0004 -> 0003 -> 0004`` must not disturb a populated graph or its lineage.

    No recovery link exists, so the downgrade is permitted. The point is that the
    column drop and re-add — both of which rebuild ``document`` — leave the P3
    graph, the append-only decision and the observation lineage untouched.
    """
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        _seed_populated_p3_graph(engine)
        counts_before = _graph_counts(engine)
        links_before = _graph_links(engine)
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)
    command.downgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        # At 0003 the recovery column is gone, but nothing else moved.
        assert RECOVERY_COLUMN not in _document_columns(engine)
        assert _graph_counts(engine) == counts_before
        _assert_graph_intact(engine, links_before)
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        assert RECOVERY_COLUMN in _document_columns(engine)
        assert _graph_counts(engine) == counts_before
        _assert_graph_intact(engine, links_before)
    finally:
        engine.dispose()


def test_0004_records_a_recovery_link_without_touching_the_source_graph(tmp_path: Path) -> None:
    """A recovery link is additive: the source graph and its lineage are unchanged.

    This exercises the migration's own purpose against real rows rather than a
    synthetic insert: linking a second document to the terminal one must not
    rewrite the source document, its decisions, its issue or its observation.
    """
    config, url = _config(tmp_path)
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        _seed_populated_p3_graph(engine)
        counts_before = _graph_counts(engine)
        links_before = _graph_links(engine)
    finally:
        engine.dispose()

    command.upgrade(config, P4_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                    "original_filename, stored_path, mime_type, sha256, size_bytes, "
                    "page_count, extraction_status, uploaded_at, "
                    "recovered_from_document_id) VALUES (:id, :patient, :doctor, "
                    "'recovery.pdf', 'recovery.pdf', 'application/pdf', :sha, 2048, 1, "
                    "'pending_extraction', '2026-11-16T09:00:00Z', :source)"
                ),
                {
                    "id": GRAPH_RECOVERY_DOCUMENT,
                    "patient": GRAPH_PATIENT,
                    "doctor": GRAPH_DOCTOR,
                    "sha": "b" * 64,
                    "source": GRAPH_DOCUMENT,
                },
            )
        assert _fk_violations(engine) == []

        # Only the new document row was added; the source graph is untouched.
        after_counts = _graph_counts(engine)
        assert after_counts["document"] == counts_before["document"] + 1
        for table in (
            "extraction_attempt",
            "extracted_fact",
            "fact_verification",
            "verification_issue",
            "observation",
        ):
            assert after_counts[table] == counts_before[table], table
        _assert_graph_intact(engine, links_before)

        # The source document itself must be byte-for-byte unchanged in the
        # columns the recovery touches: status, failure code and the link.
        with engine.connect() as connection:
            source = connection.execute(
                text(
                    "SELECT extraction_status, failure_code, recovered_from_document_id "
                    "FROM document WHERE id = :id"
                ),
                {"id": GRAPH_DOCUMENT},
            ).one()
        assert tuple(source) == ("needs_verification", None, None)

        # And the link is now live provenance, so the downgrade must refuse.
        with pytest.raises(RuntimeError) as refusal:
            command.downgrade(config, P3_REVISION)
        assert RECOVERY_COLUMN in str(refusal.value)
    finally:
        engine.dispose()

    # The refusal left every row and the schema untouched.
    engine = create_db_engine(url)
    try:
        assert RECOVERY_COLUMN in _document_columns(engine)
        assert _revision(engine) == P4_REVISION
        assert _graph_counts(engine)["document"] == counts_before["document"] + 1
        _assert_graph_intact(engine, links_before)
    finally:
        engine.dispose()
