"""The documented first-run bootstrap: ``python -m app.services.seed``.

The API has no registration endpoint, so a fresh installation needs an
operator-run command to create the synthetic accounts. This module pins that
command's contract: it refuses without ``DEMO_MODE=true`` and an operator-supplied
password, it never prints the password, it never creates schema, and it is
idempotent.

The CLI writes at the real 600 000-iteration work factor, so this file is
deliberately small: one successful seed plus the refusal paths.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from support import SEED_PASSWORD

from app.core.config import Settings
from app.db.base import Base
from app.db.models import User
from app.db.session import create_db_engine
from app.services.seed import REQUIRED_TABLES, _demo_mode_is_on, bootstrap_demo_accounts

PASSWORD = SEED_PASSWORD


def _settings(tmp_path: Path, *, demo_mode: bool = True) -> Settings:
    """Settings pointing at a throwaway SQLite file."""
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'bootstrap.db').as_posix()}",
        demo_mode=demo_mode,
        demo_seed_password=None,
    )


def _create_schema(settings: Settings) -> None:
    """Stand in for ``alembic upgrade head`` (the migration is not authorized yet)."""
    engine = create_db_engine(settings.database_url)
    Base.metadata.create_all(engine)
    engine.dispose()


def _run(settings: Settings, env: dict[str, str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = bootstrap_demo_accounts(settings=settings, env=env, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_bootstrap_refuses_when_demo_mode_is_off(tmp_path: Path) -> None:
    """A production-shaped configuration cannot create demo credentials."""
    settings = _settings(tmp_path, demo_mode=False)
    _create_schema(settings)

    code, out, err = _run(settings, {"DEMO_SEED_PASSWORD": PASSWORD})

    assert code == 2
    assert "DEMO_MODE=true" in err
    assert out == ""
    engine = create_db_engine(settings.database_url)
    with Session(engine) as db:
        assert db.execute(select(User)).scalars().all() == []
    engine.dispose()


def test_bootstrap_refuses_without_a_password(tmp_path: Path) -> None:
    """Credentials are never defaulted or shipped."""
    settings = _settings(tmp_path)
    _create_schema(settings)

    code, out, err = _run(settings, {"DEMO_MODE": "true"})

    assert code == 2
    assert "DEMO_SEED_PASSWORD" in err
    assert out == ""


def test_bootstrap_refuses_an_empty_password(tmp_path: Path) -> None:
    """An empty or whitespace-only password is not a password."""
    settings = _settings(tmp_path)
    _create_schema(settings)

    code, _out, err = _run(settings, {"DEMO_MODE": "true", "DEMO_SEED_PASSWORD": "   "})

    assert code == 2
    assert "DEMO_SEED_PASSWORD" in err


def test_bootstrap_refuses_an_unmigrated_database(tmp_path: Path) -> None:
    """Alembic owns DDL; the CLI will not create tables of its own."""
    settings = _settings(tmp_path)
    engine = create_db_engine(settings.database_url)
    engine.dispose()

    code, _out, err = _run(settings, {"DEMO_MODE": "true", "DEMO_SEED_PASSWORD": PASSWORD})

    assert code == 2
    assert "alembic upgrade head" in err
    assert sorted(REQUIRED_TABLES)  # the message names the missing schema


def test_bootstrap_seeds_and_never_prints_the_password(tmp_path: Path) -> None:
    """The successful path reports counts and usernames only."""
    settings = _settings(tmp_path)
    _create_schema(settings)

    code, out, err = _run(settings, {"DEMO_MODE": "true", "DEMO_SEED_PASSWORD": PASSWORD})

    assert code == 0, err
    assert "6 users" in out
    assert "3 patients" in out
    assert "17 observations" in out
    assert "demo_doctor (doctor)" in out
    assert PASSWORD not in out
    assert PASSWORD not in err

    engine = create_db_engine(settings.database_url)
    with Session(engine) as db:
        usernames = sorted(db.execute(select(User.username)).scalars())
        hashes = [user.password_hash for user in db.execute(select(User)).scalars()]
    engine.dispose()

    assert usernames == [
        "demo_admin",
        "demo_doctor",
        "demo_doctor_unassigned",
        "demo_patient_a",
        "demo_patient_b",
        "demo_patient_c",
    ]
    assert all(entry.startswith("pbkdf2_sha256$600000$") for entry in hashes)


def test_bootstrap_is_idempotent(tmp_path: Path) -> None:
    """A second run creates nothing and reports zero new rows."""
    settings = _settings(tmp_path)
    _create_schema(settings)
    env = {"DEMO_MODE": "true", "DEMO_SEED_PASSWORD": PASSWORD}

    first_code, first_out, _ = _run(settings, env)
    second_code, second_out, second_err = _run(settings, env)

    assert (first_code, second_code) == (0, 0), second_err
    assert "6 users" in first_out
    assert "0 users" in second_out


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_demo_mode_accepts_the_documented_truthy_spellings(tmp_path: Path, value: str) -> None:
    """``DEMO_MODE`` parsing is explicit rather than ``bool('false') is True``.

    Checked on the guard itself: the guard is what decides, and this keeps the
    test free of five real 600 000-iteration seed runs.
    """
    settings = _settings(tmp_path, demo_mode=False)

    assert _demo_mode_is_on(settings, {"DEMO_MODE": value}) is True
    assert _demo_mode_is_on(settings, {"DEMO_MODE": "false"}) is False
    assert _demo_mode_is_on(settings, {}) is False
