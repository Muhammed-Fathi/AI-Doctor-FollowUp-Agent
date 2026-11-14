"""Shared pytest fixtures.

Every test is deterministic and offline: no network call, no wall-clock
dependency in assertions, and no interaction with the developer's real
``data/runtime`` directory. Each test that needs a database gets a fresh
temporary SQLite file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.core.paths import REPO_ROOT
from app.core.version import DEMO_NOTICE
from app.db.session import create_db_engine
from app.main import create_app

ALEMBIC_INI = REPO_ROOT / "backend" / "migrations" / "alembic.ini"


@pytest.fixture(scope="session")
def demo_notice() -> str:
    """The mandatory educational notice required by ``REQ-SEC-05``."""
    return DEMO_NOTICE


@pytest.fixture()
def sqlite_url(tmp_path: Path) -> str:
    """Filesystem SQLite URL inside pytest's temporary directory."""
    return f"sqlite:///{(tmp_path / 'test_app.db').as_posix()}"


@pytest.fixture()
def migrated_db(sqlite_url: str) -> str:
    """A database with the P1 baseline migration applied."""
    config = Config(str(ALEMBIC_INI))
    config.cmd_opts = None  # type: ignore[attr-defined]
    config.attributes["configure_logger"] = False
    config.set_main_option("sqlalchemy.url", sqlite_url)
    command.upgrade(config, "head")
    return sqlite_url


@pytest.fixture()
def alembic_config(sqlite_url: str) -> Config:
    """Alembic config pointed at the test database.

    The URL is passed through ``-x database_url=`` exactly the way the P1 smoke
    check and ``test_all.ps1`` do it, so the test exercises the real code path.
    """
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", sqlite_url)
    config.attributes["sqlalchemy_url_override"] = sqlite_url
    return config


@pytest.fixture()
def engine(migrated_db: str) -> Iterator[Engine]:
    """Engine bound to the migrated test database."""
    created = create_db_engine(migrated_db)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, migrated_db: str) -> Iterator[TestClient]:
    """Test client whose settings point at the migrated temporary database."""
    monkeypatch.setenv("DATABASE_URL", migrated_db)
    monkeypatch.setenv("APP_ENV", "test")

    from app.core.config import reset_settings_cache

    reset_settings_cache()
    try:
        with TestClient(create_app()) as test_client:
            yield test_client
    finally:
        reset_settings_cache()


@pytest.fixture()
def offline_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    """Test client whose database path does not exist (degraded liveness case)."""
    missing = f"sqlite:///{(tmp_path / 'absent' / 'missing.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", missing)
    monkeypatch.setenv("APP_ENV", "test")

    from app.core.config import reset_settings_cache

    reset_settings_cache()
    try:
        with TestClient(create_app()) as test_client:
            yield test_client
    finally:
        reset_settings_cache()
