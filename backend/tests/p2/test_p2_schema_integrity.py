"""Schema-level integrity evidence for the Phase 2 tables.

These tests exist because the P2 review asked for *evidence*, not an argument:
every claim in ``app/db/models.py`` about referential integrity, uniqueness and
cycle handling is asserted here against a real SQLite database created from the
ORM metadata with ``PRAGMA foreign_keys=ON`` (which
:func:`app.db.session.create_db_engine` enables).

Nothing here needs the pending Alembic revision. Migration parity is a separate,
explicitly **not run** check listed in the PR until the migration is authorized.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from support import FIXED_NOW, PATIENT_A_ID, SEED_PASSWORD, TEST_HASH_ITERATIONS

from app.core.enums import Role
from app.db.base import Base
from app.db.models import (
    CheckinIdempotency,
    Encounter,
    Observation,
    Patient,
    User,
    UserSession,
)
from app.services.accounts import issue_session
from app.services.seed import seed_demo_data


def _seeded_session(engine: Engine) -> Session:
    """Return a session over ``engine`` with the demo dataset committed."""
    db = sessionmaker(bind=engine)()
    seed_demo_data(db, password=SEED_PASSWORD, now=FIXED_NOW, iterations=TEST_HASH_ITERATIONS)
    db.commit()
    return db


def _user_with_scope(db: Session, username: str) -> User:
    return db.execute(select(User).where(User.username == username)).scalar_one()


def _make_observation(db: Session, patient_id: str) -> str:
    """Insert a minimal valid observation row and return its id."""
    encounter_id = (
        db.execute(select(Encounter.id).where(Encounter.patient_id == patient_id)).scalars().first()
    )
    observation = Observation(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        encounter_id=encounter_id,
        measure_type="glucose",
        value=104.0,
        unit="mg/dL",
        measured_at="2026-11-02T00:00:00Z",
        source="seed_fixture",
        validation="ok",
        trust_level="self_reported_validated",
        note=None,
        created_at="2026-11-02T00:00:00Z",
        created_by_user_id=None,
    )
    db.add(observation)
    db.flush()
    return observation.id


def test_foreign_key_enforcement_is_on(p2_engine: Engine) -> None:
    """The engine turns SQLite foreign keys on; without it the FKs are inert."""
    with p2_engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_user_patient_id_is_a_real_foreign_key(p2_engine: Engine) -> None:
    """``DATA_DICTIONARY.md`` §2.1: ``user.patient_id`` references ``patient.id``."""
    fks = inspect(p2_engine).get_foreign_keys("user")

    targets = {(fk["referred_table"], tuple(fk["constrained_columns"])) for fk in fks}
    assert ("patient", ("patient_id",)) in targets


def test_patient_assignment_is_a_real_foreign_key(p2_engine: Engine) -> None:
    """The assignment column is a real FK, not a naming convention."""
    fks = inspect(p2_engine).get_foreign_keys("patient")

    targets = {(fk["referred_table"], tuple(fk["constrained_columns"])) for fk in fks}
    assert ("user", ("assigned_doctor_id",)) in targets


def test_orphan_patient_scope_is_rejected_by_the_database(p2_engine: Engine) -> None:
    """A ``user.patient_id`` that names no patient is refused by the database.

    This is the property the earlier "unique index only" version could not offer:
    a service-level check is bypassed the moment anyone writes SQL directly.
    """
    with sessionmaker(bind=p2_engine)() as db:
        # SQLite enforces foreign keys on the statement, not only at COMMIT.
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO user (id, username, display_name, role, password_hash, "
                    "patient_id, timezone, is_active, created_at, last_login_at) VALUES "
                    "(:id, :username, 'Ghost', 'patient', 'x', :patient_id, "
                    "'Africa/Cairo', 1, '2026-11-14T12:00:00Z', NULL)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "username": "ghost_patient",
                    "patient_id": "no-such-row",
                },
            )
            db.commit()
        db.rollback()


def test_patient_cannot_be_deleted_while_an_account_references_it(seeded: Session) -> None:
    """``ON DELETE RESTRICT`` protects the patient-account link."""
    patient_id = _user_with_scope(seeded, "demo_patient_a").patient_id
    assert patient_id == PATIENT_A_ID

    with pytest.raises(IntegrityError):
        seeded.execute(text("DELETE FROM patient WHERE id = :pid"), {"pid": patient_id})
        seeded.commit()
    seeded.rollback()


def test_one_account_per_patient_is_enforced_by_the_database(seeded: Session) -> None:
    """Two accounts cannot claim the same patient scope."""
    patient_id = _user_with_scope(seeded, "demo_patient_a").patient_id

    seeded.add(
        User(
            id=str(uuid.uuid4()),
            username="demo_patient_a_clone",
            display_name="Clone",
            role=Role.PATIENT.value,
            password_hash="pbkdf2_sha256$1000$00ff$00ff",
            patient_id=patient_id,
            timezone="Africa/Cairo",
            is_active=1,
            created_at="2026-11-14T12:00:00Z",
        )
    )
    with pytest.raises(IntegrityError):
        seeded.commit()
    seeded.rollback()


def test_patient_scope_matches_role_is_enforced(seeded: Session) -> None:
    """A doctor account may not carry a self scope."""
    doctor = _user_with_scope(seeded, "demo_doctor")
    doctor.patient_id = PATIENT_A_ID
    with pytest.raises(IntegrityError):
        seeded.commit()
    seeded.rollback()


def test_metadata_sorts_without_a_cycle_warning() -> None:
    """``use_alter`` marks the user/patient cycle so sorting is deterministic.

    ``pyproject.toml`` turns warnings into errors, so an unmarked cycle would fail
    every test that touches the metadata.
    """
    order = [table.name for table in Base.metadata.sorted_tables]

    assert order.index("patient") < order.index("encounter")
    assert order.index("user") < order.index("patient")


def test_seeded_database_has_no_foreign_key_violations(seeded: Session, p2_engine: Engine) -> None:
    """``PRAGMA foreign_key_check`` over the whole demo dataset is empty."""
    assert seeded is not None
    with p2_engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).fetchall() == []


def test_session_token_digest_is_unique(p2_engine: Engine) -> None:
    """A duplicate token digest is refused by the database, not only by code."""
    db = _seeded_session(p2_engine)
    try:
        user = _user_with_scope(db, "demo_doctor")
        _raw, session = issue_session(db, user=user, now=FIXED_NOW, ttl_minutes=30)
        db.commit()

        db.add(
            UserSession(
                id=str(uuid.uuid4()),
                user_id=user.id,
                token_sha256=session.token_sha256,
                created_at="2026-11-14T12:00:00Z",
                expires_at="2026-11-14T13:00:00Z",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_idempotency_key_is_unique_per_patient(p2_engine: Engine) -> None:
    """``(patient_id, idempotency_key)`` is a database-level unique constraint."""
    db = _seeded_session(p2_engine)
    try:
        patient = db.execute(select(Patient).where(Patient.id == PATIENT_A_ID)).scalar_one()
        observation_id = _make_observation(db, patient.id)
        key = str(uuid.uuid4())
        db.add(
            CheckinIdempotency(
                id=str(uuid.uuid4()),
                patient_id=patient.id,
                idempotency_key=key,
                request_fingerprint="0" * 64,
                observation_id=observation_id,
                created_at="2026-11-14T12:00:00Z",
            )
        )
        db.commit()

        db.add(
            CheckinIdempotency(
                id=str(uuid.uuid4()),
                patient_id=patient.id,
                idempotency_key=key,
                request_fingerprint="1" * 64,
                observation_id=observation_id,
                created_at="2026-11-14T12:00:01Z",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
