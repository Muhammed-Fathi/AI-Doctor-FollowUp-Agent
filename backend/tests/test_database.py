"""Database foundation tests: SQLite initialisation and the Alembic baseline.

Covers the P1 exit gate "database initialization and Alembic migration succeed"
and the requirement that migrations are reversible (``AGENTS.md`` §7).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.db.models import SchemaMeta
from app.db.session import create_db_engine, ensure_sqlite_directory

BASELINE_REVISION = "0001_p1_baseline"


def _alembic_config(database_url: str) -> Config:
    from app.core.paths import REPO_ROOT

    config = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migration_creates_baseline_table(engine: Engine) -> None:
    """The baseline migration creates ``schema_meta`` and an ``alembic_version`` row."""
    tables = set(inspect(engine).get_table_names())

    assert "schema_meta" in tables
    assert "alembic_version" in tables

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert revision == BASELINE_REVISION


def test_baseline_creates_no_patient_domain_tables(engine: Engine) -> None:
    """Phase 1 must not pre-empt P2: no patient-domain table may exist yet."""
    tables = set(inspect(engine).get_table_names())
    forbidden = {
        "user",
        "patient",
        "encounter",
        "document",
        "observation",
        "extracted_fact",
        "fact_verification",
        "review_item",
        "workflow_run",
        "follow_up_task",
        "audit_event",
    }
    assert tables.isdisjoint(forbidden)


def test_migration_is_reversible(sqlite_url: str) -> None:
    """``upgrade head`` → ``downgrade base`` → ``upgrade head`` succeeds."""
    config = _alembic_config(sqlite_url)

    command.upgrade(config, "head")
    engine = create_db_engine(sqlite_url)
    try:
        assert "schema_meta" in inspect(engine).get_table_names()
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_db_engine(sqlite_url)
    try:
        assert "schema_meta" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_db_engine(sqlite_url)
    try:
        assert "schema_meta" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_schema_meta_roundtrip(engine: Engine) -> None:
    """The model can persist and read back a baseline marker row."""
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        session.add(SchemaMeta(key="baseline", value="0001_p1_baseline"))
        session.commit()

    with Session(engine) as session:
        row = session.get(SchemaMeta, "baseline")
        assert row is not None
        assert row.value == "0001_p1_baseline"
        assert row.updated_at is not None


def test_schema_meta_rejects_empty_key(engine: Engine) -> None:
    """The CHECK constraint rejects an empty key instead of storing junk."""
    from sqlalchemy.orm import Session

    with Session(engine) as session, pytest.raises(IntegrityError):
        session.add(SchemaMeta(key="", value="x"))
        session.flush()


def test_foreign_keys_are_enabled(engine: Engine) -> None:
    """The connection event turns on SQLite ``PRAGMA foreign_keys``."""
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_ensure_sqlite_directory_creates_parent(tmp_path: Path) -> None:
    """A nested SQLite path gets its parent directory created on demand."""
    target = tmp_path / "nested" / "deeper" / "app.db"
    ensure_sqlite_directory(f"sqlite:///{target.as_posix()}")
    assert target.parent.is_dir()


def test_in_memory_url_is_left_alone() -> None:
    """``sqlite:///:memory:`` must not be rewritten into a filesystem path."""
    from app.core.config import Settings

    settings = Settings(database_url="sqlite:///:memory:", _env_file=None)
    assert settings.database_url == "sqlite:///:memory:"


def test_relative_sqlite_url_is_anchored_to_repo_root() -> None:
    """A relative URL resolves against the repository root, not the process CWD."""
    from app.core.config import Settings
    from app.core.paths import REPO_ROOT

    settings = Settings(database_url="sqlite:///data/runtime/app.db", _env_file=None)
    assert settings.database_url == f"sqlite:///{(REPO_ROOT / 'data/runtime/app.db').as_posix()}"
