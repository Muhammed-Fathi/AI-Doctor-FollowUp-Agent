"""Fixtures for the Phase 3 test package.

Design notes that matter for review:

* **Real migrated database, not ``create_all``.** Unlike the P2 package (whose
  migration was not yet authorized when it was written), P3 ships
  ``0003_p3_documents``. These tests migrate to ``head`` so the trigger, the
  unique index and the additive column are all exercised as they will be in
  production. A metadata-only schema would silently skip the trigger, which is
  the single most important guard in this phase.
* **Uploads go to a temporary directory.** ``Settings.upload_dir`` is pointed at
  ``tmp_path`` so no test can write into ``data/runtime``. A test that forgot this
  would pollute the working tree, so it is set globally here.
* **The clock is frozen.** ``current_time`` is overridden exactly as the P2 suite
  does, so no assertion depends on the machine date.
* **PDFs are generated in memory** by the committed fixture script rather than
  read from disk, because ``D-04`` forbids committing binary fixtures.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

# The P2 support module holds the shared clock, password and patient ids. Reusing
# it keeps the two suites consistent instead of forking a second set of constants.
sys.path.insert(0, str(Path(__file__).parent.parent / "p2"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "python"))

from support import FIXED_NOW, PATIENT_A_ID, PATIENT_B_ID, SEED_PASSWORD, TEST_HASH_ITERATIONS

from app.api.v1.auth.dependencies import clear_limiter_cache, current_time
from app.core.config import Settings, get_settings, reset_settings_cache
from app.core.paths import REPO_ROOT
from app.db.models import User
from app.db.session import create_db_engine, get_db_session
from app.main import create_app
from app.services.accounts import issue_session
from app.services.seed import seed_demo_data

ALEMBIC_INI = REPO_ROOT / "backend" / "migrations" / "alembic.ini"


@pytest.fixture()
def p3_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Settings pointing at a per-test database and a per-test upload directory."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'p3.db').as_posix()}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("DEMO_SEED_PASSWORD", SEED_PASSWORD)
    monkeypatch.setenv("SESSION_TTL_MINUTES", "60")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "50")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300")
    # Keep every byte a test writes inside tmp_path.
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    # OCR is deliberately *not* configured: the sandbox has no engine, and a test
    # must never silently depend on a machine binary. The real-engine path is
    # marked Windows-only in the report.
    monkeypatch.delenv("TESSERACT_CMD", raising=False)

    reset_settings_cache()
    try:
        yield Settings()
    finally:
        reset_settings_cache()
        clear_limiter_cache()


@pytest.fixture()
def p3_engine(p3_settings: Settings) -> Iterator[Engine]:
    """A database migrated to ``head`` so the P3 trigger and index are real."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", p3_settings.database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")

    engine = create_db_engine(p3_settings.database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db(p3_engine: Engine) -> Iterator[Session]:
    """A seeded session on the migrated per-test database."""
    factory = sessionmaker(bind=p3_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    seed_demo_data(
        session,
        password=SEED_PASSWORD,
        now=FIXED_NOW,
        iterations=TEST_HASH_ITERATIONS,
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _token(db: Session, username: str, now: datetime | None = None) -> str:
    """Issue a real bearer token for ``username``."""
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    raw, _ = issue_session(db, user=user, now=now or FIXED_NOW, ttl_minutes=60)
    db.commit()
    return raw


@pytest.fixture()
def token(db: Session):
    """Return a callable issuing a raw bearer token for a seeded username."""

    def _issue(username: str) -> str:
        return _token(db, username)

    return _issue


@pytest.fixture()
def patient_headers(token) -> dict[str, str]:
    """Headers for demo patient A's own account."""
    return {"Authorization": f"Bearer {token('demo_patient_a')}"}


@pytest.fixture()
def other_patient_headers(token) -> dict[str, str]:
    """Headers for demo patient B's own account (a different patient)."""
    return {"Authorization": f"Bearer {token('demo_patient_b')}"}


@pytest.fixture()
def doctor_headers(token) -> dict[str, str]:
    """Headers for the doctor assigned to demo patient A."""
    return {"Authorization": f"Bearer {token('demo_doctor')}"}


@pytest.fixture()
def unassigned_doctor_headers(token) -> dict[str, str]:
    """Headers for a doctor with no assignments."""
    return {"Authorization": f"Bearer {token('demo_doctor_unassigned')}"}


@pytest.fixture()
def admin_headers(token) -> dict[str, str]:
    """Headers for the demo administrator."""
    return {"Authorization": f"Bearer {token('demo_admin')}"}


def _build_app(settings: Settings, session: Session) -> FastAPI:
    """Build the shipped app with the per-test database and a frozen clock."""
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[current_time] = lambda: FIXED_NOW

    def _session_override() -> Iterator[Session]:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _session_override
    return app


@pytest.fixture()
def api(p3_settings: Settings, db: Session) -> Iterator[TestClient]:
    """The production application bound to the seeded migrated database."""
    with TestClient(_build_app(p3_settings, db)) as client:
        yield client


# --- generated fixtures ------------------------------------------------------


@pytest.fixture(scope="session")
def fixtures():
    """The committed deterministic fixture builder (``generate_p3_fixtures``).

    Imported lazily so a broken fixture script fails in the tests that need it
    rather than at collection time for the whole suite.
    """
    import generate_p3_fixtures

    return generate_p3_fixtures


@pytest.fixture(scope="session")
def report_b_pdf(fixtures) -> bytes:
    """Case B: a clean fasting-glucose report with a ``mg/dL`` unit."""
    return fixtures.build_report_pdf("report_b_glucose.txt")


@pytest.fixture(scope="session")
def glucose_pdf(fixtures) -> bytes:
    """Case A's own fasting-glucose report (``report_a_glucose.txt``).

    Use this whenever a test needs a *verifiable* glucose document for patient A.
    ``report_b_pdf`` carries patient **B**'s printed reference (``GOLD_FIXTURES.md``
    §3.2), so filing it under patient A is a wrong-patient document by definition
    and correctly raises ``VI-004`` (P3-R02). Keeping the two fixtures separate is
    what makes that distinction testable instead of accidental.
    """
    return fixtures.build_report_pdf("report_a_glucose.txt")


@pytest.fixture(scope="session")
def report_a_pdf(fixtures) -> bytes:
    """Case A: a clean hemoglobin report in ``g/dL``."""
    return fixtures.build_report_pdf("report_a_clean.txt")


@pytest.fixture(scope="session")
def ambiguous_pdf(fixtures) -> bytes:
    """An ambiguous date and a corrupt value token (``1O5``), filed by its owner.

    Same content as Case C, but printed with **patient A**'s reference so it can be
    uploaded by patient A without tripping ``VI-004`` (P3-R02). The correction and
    ``VI-003``/``VI-005`` tests need a document that reaches verification; a
    wrong-patient document is correctly refused before any decision is recorded.
    """
    return fixtures.build_report_pdf("report_a_ambiguous.txt")


@pytest.fixture(scope="session")
def case_c_ambiguous_pdf(fixtures) -> bytes:
    """Case C exactly as ``GOLD_FIXTURES.md`` prints it (``DEMO-C-001``)."""
    return fixtures.build_report_pdf("report_c_ambiguous.txt")


@pytest.fixture(scope="session")
def multi_test_pdf(fixtures) -> bytes:
    """Two measurements in one document (``GOLD-NEG-10``)."""
    return fixtures.build_report_pdf("report_multi_test.txt")


@pytest.fixture(scope="session")
def missing_unit_pdf(fixtures) -> bytes:
    """A value with no unit at all (``VI-001``)."""
    return fixtures.build_report_pdf("report_missing_unit.txt")


@pytest.fixture(scope="session")
def injection_pdf(fixtures) -> bytes:
    """A report containing instruction-like text (``NEG-11``)."""
    return fixtures.build_report_pdf("report_injection.txt")


__all__ = [
    "FIXED_NOW",
    "PATIENT_A_ID",
    "PATIENT_B_ID",
    "SEED_PASSWORD",
    "TEST_HASH_ITERATIONS",
]
