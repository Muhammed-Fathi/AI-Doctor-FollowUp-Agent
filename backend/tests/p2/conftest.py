"""Fixtures for the Phase 2 tests.

Everything here is deterministic and offline:

* a fresh SQLite database per test, created from the ORM metadata because the
  P2 Alembic revision is not yet authorised by the owner (see the P2 PR scope
  request). The migration-parity test is therefore **not run** in this change and
  is listed as such in the report;
* a fixed clock, so no assertion depends on the machine date;
* a fixed demo seed password supplied through the environment, never a literal
  committed to the repository.

The HTTP fixture builds an isolated application that installs the **production**
problem handlers and the **production** auth router. Only the ASGI wiring in
``app/main.py`` differs, and that file is part of the pending scope request.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).parent))

from support import FIXED_NOW, SEED_PASSWORD, user_by_username

from app.api.v1.auth import router as auth_router
from app.api.v1.auth.dependencies import clear_limiter_cache, current_time
from app.core.config import Settings, get_settings, reset_settings_cache
from app.core.errors import install_problem_handlers
from app.core.paths import SYNTHETIC_DATA_DIR
from app.core.policies import Principal
from app.db.base import Base
from app.db.session import create_db_engine, get_db_session
from app.services.accounts import build_principal, issue_session
from app.services.seed import seed_demo_data


@pytest.fixture()
def p2_engine(tmp_path: Path) -> Iterator[Engine]:
    """A fresh SQLite database with the P2 schema created from metadata."""
    url = f"sqlite:///{(tmp_path / 'p2.db').as_posix()}"
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db(p2_engine: Engine) -> Iterator[Session]:
    """A session bound to the per-test database."""
    factory = sessionmaker(bind=p2_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fixtures_dir() -> Path:
    """The tracked synthetic fixture directory."""
    return SYNTHETIC_DATA_DIR


@pytest.fixture()
def seeded(db: Session) -> Session:
    """A database with the deterministic demo dataset."""
    seed_demo_data(db, password=SEED_PASSWORD, now=FIXED_NOW)
    db.commit()
    return db


def _principal_for(db: Session, username: str, now: datetime) -> Principal:
    """Create a real session row for ``username`` and return its principal."""
    user = user_by_username(db, username)
    _, session = issue_session(db, user=user, now=now, ttl_minutes=60)
    db.commit()
    return build_principal(user, session)


@pytest.fixture()
def doctor_principal(seeded: Session) -> Principal:
    """Principal for the assigned demo doctor."""
    return _principal_for(seeded, "demo_doctor", FIXED_NOW)


@pytest.fixture()
def unassigned_doctor_principal(seeded: Session) -> Principal:
    """Principal for a doctor with no patient assignments."""
    return _principal_for(seeded, "demo_doctor_unassigned", FIXED_NOW)


@pytest.fixture()
def patient_principal(seeded: Session) -> Principal:
    """Principal for demo patient A's own account."""
    return _principal_for(seeded, "demo_patient_a", FIXED_NOW)


@pytest.fixture()
def admin_principal(seeded: Session) -> Principal:
    """Principal for the demo administrator."""
    return _principal_for(seeded, "demo_admin", FIXED_NOW)


@pytest.fixture()
def token_for(seeded: Session) -> Any:
    """Return a callable issuing a raw bearer token for a seeded username."""

    def _issue(username: str, now: datetime | None = None) -> str:
        user = user_by_username(seeded, username)
        raw, _ = issue_session(seeded, user=user, now=now or FIXED_NOW, ttl_minutes=60)
        seeded.commit()
        return raw

    return _issue


@pytest.fixture()
def app_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Settings pointing at a per-test database with a known demo password."""
    database_url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("DEMO_SEED_PASSWORD", SEED_PASSWORD)
    monkeypatch.setenv("SESSION_TTL_MINUTES", "60")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")

    reset_settings_cache()
    try:
        yield Settings()
    finally:
        reset_settings_cache()
        clear_limiter_cache()


@pytest.fixture()
def api_db(app_settings: Settings) -> Iterator[Session]:
    """A metadata-created database for the API tests, seeded with fixtures."""
    engine = create_db_engine(app_settings.database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    seed_demo_data(session, password=SEED_PASSWORD, now=FIXED_NOW)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def build_test_app(settings: Settings, now: datetime = FIXED_NOW) -> FastAPI:
    """Build a FastAPI app with the production handlers and the auth router.

    ``app/main.py`` calls exactly these two functions once the router integration
    is authorised; until then this harness is the only ASGI surface and it is
    confined to tests.
    """
    app = FastAPI(title="P2 test surface", version="0.2.0")
    install_problem_handlers(app)
    app.include_router(auth_router.router)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[current_time] = lambda: now
    return app


@pytest.fixture()
def api_client(app_settings: Settings, api_db: Session) -> Iterator[TestClient]:
    """A test client bound to the seeded per-test database."""

    def _session_override() -> Iterator[Session]:
        try:
            yield api_db
            api_db.commit()
        except Exception:
            api_db.rollback()
            raise

    app = build_test_app(app_settings)
    app.dependency_overrides[get_db_session] = _session_override
    with TestClient(app) as client:
        yield client
