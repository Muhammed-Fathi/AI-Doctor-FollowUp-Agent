"""Alembic environment.

The database URL precedence is:

1. ``-x database_url=...`` command-line option (used by tests and smoke checks),
2. ``ALEMBIC_DATABASE_URL`` environment variable,
3. ``DATABASE_URL`` from application settings / ``.env``,
4. the settings default (``data/runtime/app.db``).

Using application settings keeps a single source of truth for the SQLite path,
so ``setup.ps1``, ``start.ps1``, pytest and Alembic always agree.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine

# ``prepend_sys_path = %(here)s/..`` in alembic.ini makes ``import app`` work
# regardless of the working directory.
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import SchemaMeta  # noqa: F401 - imported for autogenerate metadata
from app.db.session import ensure_sqlite_directory

config = context.config

if config.config_file_name is not None:
    # ``disable_existing_loggers`` defaults to True and would silence the app
    # loggers that were configured before Alembic ran.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Return the database URL for this invocation (see module docstring)."""
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("database_url"):
        return x_args["database_url"]

    env_url = os.environ.get("ALEMBIC_DATABASE_URL")
    if env_url:
        return env_url

    # ``alembic.ini`` deliberately declares no URL, but tests and tooling may set
    # one programmatically (``config.set_main_option("sqlalchemy.url", ...)``).
    config_url = config.get_main_option("sqlalchemy.url", None)
    if config_url:
        return config_url

    return get_settings().database_url


def run_migrations_offline() -> None:
    """Render migrations to SQL without a live connection."""
    database_url = _resolve_database_url()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=database_url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    # ``render_as_batch`` is what makes SQLite ALTER-style migrations reversible.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    database_url = _resolve_database_url()
    ensure_sqlite_directory(database_url)

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            _run_migrations(connection)
            connection.commit()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
