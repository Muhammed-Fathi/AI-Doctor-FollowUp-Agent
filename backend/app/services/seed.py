"""Deterministic synthetic seeding and demo reset.

``REQ-OPS-01`` requires byte-stable fixture identifiers and reproducible values,
so the seeder is a plain function over the tracked JSON fixtures: no random UUID,
no wall-clock value, no generated patient. Two consecutive seeds produce the same
rows, and re-running a seed never duplicates a record.

What seeding does **not** do
----------------------------
* It never writes a password into a file or a log. The demo account password
  comes from ``DEMO_SEED_PASSWORD`` at seed time and only the salted hash is
  stored (``REQ-AUTH-01``).
* It never touches files. ``reset`` deletes application rows only — no database
  file, no upload directory and no unrelated file is removed.
* It never deletes the audit trail. Audit rows are the evidence of what the demo
  did, so they survive a reset by design (``US-12``: "audit events persist per
  run"). The reset itself appends a ``demo.reset`` row.

Seeding order matters because of two references:

``patient.assigned_doctor_id → user.id`` and ``user.patient_id → patient``. The
foreign key is declared on the patient side only (see ``app/db/models.py``), so a
seed runs in three phases: accounts without a self scope, then patients, then the
patient accounts' self scope.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import format_utc
from app.core.enums import Role
from app.core.paths import SYNTHETIC_DATA_DIR
from app.core.security import hash_password
from app.db.models import (
    CheckinIdempotency,
    Encounter,
    Observation,
    Patient,
    User,
    UserSession,
)
from app.schemas.fixtures import (
    EncounterFixtureFile,
    ObservationFixtureFile,
    PatientFixtureFile,
    UserFixtureFile,
)

#: Fixture format version written in every file in ``data/synthetic``.
SEED_FORMAT: str = "p2-1.0.0"

#: Demo cases exposed by the seed (`GOLD_FIXTURES.md` §2-§4). Case D is the
#: internal rule-coverage fixture and belongs to P4, not to the demo seed.
DEMO_CASES: dict[str, str] = {
    "A_stable": "DEMO-A-001",
    "B_changed": "DEMO-B-001",
    "C_ambiguous_ocr": "DEMO-C-001",
}


@dataclass(frozen=True, slots=True)
class FixtureBundle:
    """The validated contents of ``data/synthetic``."""

    users: UserFixtureFile
    patients: PatientFixtureFile
    encounters: EncounterFixtureFile
    observations: ObservationFixtureFile


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Summary of a seed or reset run (counts only, no patient values)."""

    users_created: int
    patients_created: int
    encounters_created: int
    observations_created: int
    cases_loaded: tuple[str, ...]


class SeedConfigurationError(RuntimeError):
    """Raised when seeding cannot proceed (e.g. no demo password configured)."""


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_fixtures(directory: Path | None = None) -> FixtureBundle:
    """Load and validate every fixture file.

    Raises:
        FileNotFoundError: if a fixture file is missing.
        pydantic.ValidationError: if a fixture violates the schema (missing
            synthetic notice, non-DEMO external ref, doctor-verified seed, …).
    """
    base = directory or SYNTHETIC_DATA_DIR
    bundle = FixtureBundle(
        users=UserFixtureFile.model_validate(_read_json(base / "users.json")),
        patients=PatientFixtureFile.model_validate(_read_json(base / "patients.json")),
        encounters=EncounterFixtureFile.model_validate(_read_json(base / "encounters.json")),
        observations=ObservationFixtureFile.model_validate(_read_json(base / "observations.json")),
    )
    for file in (bundle.users, bundle.patients, bundle.encounters, bundle.observations):
        if file.fixture_version != SEED_FORMAT:
            raise SeedConfigurationError(
                f"fixture version {file.fixture_version!r} does not match {SEED_FORMAT!r}"
            )
    return bundle


def seed_demo_data(
    db: Session,
    *,
    password: str,
    now: datetime,
    directory: Path | None = None,
) -> SeedResult:
    """Insert missing synthetic rows; existing rows are left untouched.

    Idempotent by primary key: a second call creates nothing, changes no password
    hash and leaves every fixture value identical.

    Raises:
        SeedConfigurationError: if ``password`` is empty, because an account
            without a usable credential would make the demo unreachable.
    """
    if not password.strip():
        raise SeedConfigurationError("a non-empty demo seed password is required")

    bundle = load_fixtures(directory)
    # Phase 1: staff accounts (no self scope), which patients reference.
    created_users = _seed_staff_accounts(db, fixture=bundle.users, password=password, now=now)
    # Phase 2: patient rows, whose ``assigned_doctor_id`` resolves to phase 1.
    created_patients = _seed_patients(db, fixture=bundle.patients, now=now)
    # Phase 3: patient accounts, which require their patient row to exist because
    # ``user.patient_id`` must be non-NULL exactly when the role is ``patient``.
    created_users += _seed_patient_accounts(db, fixture=bundle.users, password=password, now=now)
    created_encounters = _seed_encounters(db, fixture=bundle.encounters, now=now)
    encounter_ids = {record.ref: record.id for record in bundle.encounters.encounters}
    created_observations = _seed_observations(
        db,
        fixture=bundle.observations,
        encounter_ids=encounter_ids,
        now=now,
    )
    db.flush()

    return SeedResult(
        users_created=created_users,
        patients_created=created_patients,
        encounters_created=created_encounters,
        observations_created=created_observations,
        cases_loaded=tuple(DEMO_CASES),
    )


def _new_account(record: object, *, password: str, now: datetime) -> User:
    """Build a user row from a fixture record."""
    return User(
        id=record.id,  # type: ignore[attr-defined]
        username=record.username,  # type: ignore[attr-defined]
        display_name=record.display_name,  # type: ignore[attr-defined]
        role=record.role.value,  # type: ignore[attr-defined]
        # A fresh salt per account: two accounts never share a hash.
        password_hash=hash_password(password),
        patient_id=record.patient_id,  # type: ignore[attr-defined]
        timezone=record.timezone,  # type: ignore[attr-defined]
        is_active=1,
        created_at=format_utc(now),
        last_login_at=None,
    )


def _seed_staff_accounts(
    db: Session, *, fixture: UserFixtureFile, password: str, now: datetime
) -> int:
    """Insert doctor and demo-admin accounts (rows with no patient self scope)."""
    created = 0
    for record in fixture.users:
        if record.role is Role.PATIENT:
            continue
        if db.get(User, record.id) is not None:
            continue
        db.add(_new_account(record, password=password, now=now))
        created += 1
    db.flush()
    return created


def _seed_patient_accounts(
    db: Session, *, fixture: UserFixtureFile, password: str, now: datetime
) -> int:
    """Insert patient accounts once their patient rows exist."""
    created = 0
    for record in fixture.users:
        if record.role is not Role.PATIENT:
            continue
        if db.get(User, record.id) is not None:
            continue
        db.add(_new_account(record, password=password, now=now))
        created += 1
    db.flush()
    return created


def _seed_patients(db: Session, *, fixture: PatientFixtureFile, now: datetime) -> int:
    """Insert missing patients (phase 2: assignment resolves to an account)."""
    created = 0
    for record in fixture.patients:
        if db.get(Patient, record.id) is not None:
            continue
        doctor = _user_by_username(db, record.assigned_doctor_username)
        if doctor is None:
            raise SeedConfigurationError(
                f"patient {record.external_ref} references an unknown doctor account"
            )
        db.add(
            Patient(
                id=record.id,
                display_name=record.display_name,
                date_of_birth=record.date_of_birth,
                sex_at_birth=record.sex_at_birth.value if record.sex_at_birth else None,
                assigned_doctor_id=doctor.id,
                external_ref=record.external_ref,
                data_source=record.data_source,
                created_at=format_utc(now),
                updated_at=format_utc(now),
            )
        )
        created += 1
    db.flush()
    return created


def _seed_encounters(db: Session, *, fixture: EncounterFixtureFile, now: datetime) -> int:
    """Insert missing encounters, resolving patients by ``external_ref``."""
    created = 0
    for record in fixture.encounters:
        if db.get(Encounter, record.id) is not None:
            continue
        patient = _patient_by_external_ref(db, record.patient_external_ref)
        if patient is None:
            raise SeedConfigurationError(f"encounter {record.ref} references an unknown patient")
        db.add(
            Encounter(
                id=record.id,
                patient_id=patient.id,
                encounter_date=record.encounter_date,
                encounter_type=record.encounter_type,
                note=record.note,
                created_at=format_utc(now),
            )
        )
        created += 1
    db.flush()
    return created


def _seed_observations(
    db: Session,
    *,
    fixture: ObservationFixtureFile,
    encounter_ids: dict[str, str],
    now: datetime,
) -> int:
    """Insert missing observations, resolving encounter fixture refs."""
    created = 0
    for record in fixture.observations:
        if db.get(Observation, record.id) is not None:
            continue
        patient = _patient_by_external_ref(db, record.patient_external_ref)
        if patient is None:
            raise SeedConfigurationError(f"observation {record.id} references an unknown patient")
        encounter_id = None
        if record.encounter_ref is not None:
            encounter_id = encounter_ids.get(record.encounter_ref)
            if encounter_id is None:
                raise SeedConfigurationError(
                    f"observation {record.id} references an unknown encounter"
                )
        db.add(
            Observation(
                id=record.id,
                patient_id=patient.id,
                encounter_id=encounter_id,
                measure_type=record.measure_type.value,
                value=float(record.value),
                unit=record.unit.value,
                measured_at=record.measured_at,
                source=record.source.value,
                validation=record.validation.value,
                trust_level=record.trust_level.value,
                verified_by_user_id=None,
                verified_at=None,
                note=record.note,
                created_at=format_utc(now),
                created_by_user_id=None,
            )
        )
        created += 1
    db.flush()
    return created


def _user_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def _patient_by_external_ref(db: Session, external_ref: str) -> Patient | None:
    return db.execute(
        select(Patient).where(Patient.external_ref == external_ref)
    ).scalar_one_or_none()


def clear_demo_data(db: Session) -> None:
    """Delete synthetic rows in foreign-key safe order, keeping the audit trail.

    Order: replay records → sessions → observations → encounters → patient
    accounts → patients → staff accounts. Patient accounts are deleted whole
    rather than detached from their patient, because ``user.patient_id`` must be
    non-NULL exactly when the role is ``patient``. Audit rows are untouched.
    """
    db.execute(delete(CheckinIdempotency))
    db.execute(delete(UserSession))
    db.execute(delete(Observation))
    db.execute(delete(Encounter))
    db.execute(delete(User).where(User.role == Role.PATIENT.value))
    db.execute(delete(Patient))
    db.execute(delete(User))
    db.flush()


def reset_demo_data(
    db: Session,
    *,
    password: str,
    now: datetime,
    directory: Path | None = None,
) -> SeedResult:
    """Clear synthetic rows and reseed from the fixtures.

    Audit rows survive; everything else is rebuilt from tracked fixtures so the
    identifiers, values and timestamps are identical after every reset.
    """
    clear_demo_data(db)
    return seed_demo_data(db, password=password, now=now, directory=directory)


def seeded_cases(db: Session) -> list[dict[str, object]]:
    """Return which demo cases exist in this database.

    Used by the demo administration service. It reports only identifiers and
    seeded flags — never a measurement value.
    """
    cases: list[dict[str, object]] = []
    for case_id, external_ref in DEMO_CASES.items():
        patient = _patient_by_external_ref(db, external_ref)
        cases.append(
            {
                "case_id": case_id,
                "seeded": patient is not None,
                "patient_id": patient.id if patient is not None else None,
            }
        )
    return cases


__all__ = [
    "DEMO_CASES",
    "SEED_FORMAT",
    "FixtureBundle",
    "SeedConfigurationError",
    "SeedResult",
    "clear_demo_data",
    "load_fixtures",
    "reset_demo_data",
    "seed_demo_data",
    "seeded_cases",
]
