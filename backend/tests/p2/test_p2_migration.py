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
HEAD_REVISION = "0002_p2_patient_domain"
P1_REVISION = "0001_p1_baseline"


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


def test_upgrade_head_creates_exactly_the_allowlisted_schema(tmp_path: Path) -> None:
    """``0002`` adds the seven P2 tables and nothing else."""
    config, url = _config(tmp_path)
    command.upgrade(config, "head")

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES
        assert _revision(engine) == HEAD_REVISION
        assert _fk_violations(engine) == []
        user_fks = inspect(engine).get_foreign_keys("user")
        assert any(fk["referred_table"] == "patient" for fk in user_fks)
        indexes = {index["name"] for index in inspect(engine).get_indexes("observation")}
        assert "uq_observation_checkin_identity" in indexes
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
    """``0002 -> base -> 0002`` reaches the documented empty state and recovers."""
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
        assert _tables(engine) == P1_TABLES | P2_TABLES
        assert _revision(engine) == HEAD_REVISION
        assert _fk_violations(engine) == []
    finally:
        engine.dispose()


def test_p1_to_p2_to_p1_to_p2_is_stable(tmp_path: Path) -> None:
    """The sequence the gate runs (0001 -> 0002 -> 0001 -> 0002) is clean each time."""
    config, url = _config(tmp_path)

    command.upgrade(config, P1_REVISION)
    command.upgrade(config, "head")
    command.downgrade(config, P1_REVISION)
    command.upgrade(config, "head")

    engine = create_db_engine(url)
    try:
        assert _tables(engine) == P1_TABLES | P2_TABLES
        assert _revision(engine) == HEAD_REVISION
        assert _fk_violations(engine) == []
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
