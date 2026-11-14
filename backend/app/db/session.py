"""Engine and session factory.

SQLite is the only supported backend (``ADR-0003``). The engine is created
lazily so that importing the app never touches the filesystem, which keeps the
API tests deterministic and independent of the developer's runtime directory.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import url as sa_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.paths import RUNTIME_DIR


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    """SQLite ignores foreign keys unless enabled per connection.

    Turning this on now means P2 migrations inherit correct behaviour instead of
    silently accepting orphan rows.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for ``database_url`` (defaults to settings)."""
    url = database_url or get_settings().database_url
    is_sqlite = url.startswith("sqlite")

    connect_args: dict[str, Any] = {}
    if is_sqlite:
        # Allow use from uvicorn's worker thread as well as the test client.
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args, future=True)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def ensure_sqlite_directory(database_url: str | None = None) -> None:
    """Create the parent directory for a file-backed SQLite database."""
    url = database_url or get_settings().database_url
    parsed = sa_url.make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return
    database = parsed.database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def get_session_factory(bind: Engine | None = None) -> sessionmaker[Session]:
    """Return a session factory bound to ``bind`` (or a fresh engine)."""
    engine = bind or create_db_engine()
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    """Transactional session context manager."""
    session_factory = factory or get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@lru_cache(maxsize=4)
def _engine_for_url(database_url: str) -> Engine:
    """Return a cached engine per URL so requests share one connection pool."""
    return create_db_engine(database_url)


def get_engine() -> Engine:
    """Return the engine for the current settings (cache key = resolved URL)."""
    return _engine_for_url(get_settings().database_url)


def get_db_session() -> Iterator[Session]:
    """Yield a request-scoped session; commit on success, roll back on error.

    Used as a FastAPI dependency. The session is closed in every case, so a
    raised ``ApiError`` cannot leak a connection or leave a half-applied
    transaction behind.
    """
    session = get_session_factory(get_engine())()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database(database_url: str | None = None) -> bool:
    """Return ``True`` when the database answers a trivial ``SELECT 1``.

    Used by ``/health``. The caller never sees the exception text, only the
    ``ok``/``unavailable`` dependency state, so no path or credential leaks.
    """
    try:
        engine = create_db_engine(database_url)
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        finally:
            engine.dispose()
    except Exception:  # health must never raise
        return False
    return True


__all__ = [
    "RUNTIME_DIR",
    "check_database",
    "create_db_engine",
    "ensure_sqlite_directory",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
