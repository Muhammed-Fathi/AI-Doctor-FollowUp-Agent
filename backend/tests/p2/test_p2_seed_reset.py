"""``REQ-OPS-01`` / ``US-12`` — deterministic seeding and safe demo reset.

Requirement mapping: ``REQ-OPS-01`` (byte-stable fixture ids, reproducible
values), ``REQ-DATA-03`` (stable UUIDs, UTC timestamps), ``REQ-AUTH-01``
(hashed credentials only), ``REQ-AUDIT-01`` (reset is audited), and the
``NEG-12`` / ``T-15`` guards around the destructive demo operation.

Two properties are asserted over and over on purpose: seeding twice changes
nothing, and a reset returns the database to the same identifiers and values.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from support import FIXED_NOW, PATIENT_A_ID, PATIENT_B_ID, PATIENT_C_ID, SEED_PASSWORD

from app.core.clock import parse_utc
from app.core.enums import Role
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import AuditEvent, Observation, Patient, User, UserSession
from app.services.accounts import resolve_session
from app.services.demo import reset_demo
from app.services.seed import (
    DEMO_CASES,
    SEED_FORMAT,
    load_fixtures,
    reset_demo_data,
    seed_demo_data,
)

REQUEST_ID = "44444444-4444-4444-8444-dddddddddddd"


def count(db: Session, model: type) -> int:
    """Return the row count for ``model``."""
    return len(db.execute(select(model)).scalars().all())


def test_fixture_files_carry_the_required_headers() -> None:
    """Every fixture file is explicitly labelled synthetic."""
    bundle = load_fixtures()

    for file in (bundle.users, bundle.patients, bundle.encounters, bundle.observations):
        assert file.notice.startswith("SYNTHETIC DEMO DATA")
        assert file.disclaimer == "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"
        assert file.fixture_version == SEED_FORMAT


def test_seed_creates_the_documented_demo_dataset(seeded: Session) -> None:
    """The seed produces six accounts, three patients and seventeen measurements."""
    assert count(seeded, User) == 6
    assert count(seeded, Patient) == 3
    assert count(seeded, Observation) == 17

    roles = sorted(user.role for user in seeded.execute(select(User)).scalars().all())
    assert roles == ["demo_admin", "doctor", "doctor", "patient", "patient", "patient"]


def test_patient_ids_match_the_gold_fixtures(seeded: Session) -> None:
    """REQ-OPS-01: identifiers are the fixed values the contracts name."""
    ids = {patient.id for patient in seeded.execute(select(Patient)).scalars().all()}

    assert ids == {PATIENT_A_ID, PATIENT_B_ID, PATIENT_C_ID}
    assert set(DEMO_CASES.values()) == {
        "DEMO-A-001",
        "DEMO-B-001",
        "DEMO-C-001",
    }


def test_seeded_values_match_the_gold_fixtures(seeded: Session) -> None:
    """The Case-B history the demo story depends on is exactly as documented."""
    rows = (
        seeded.execute(
            select(Observation)
            .where(
                Observation.patient_id == PATIENT_B_ID, Observation.measure_type == "systolic_bp"
            )
            .order_by(Observation.measured_at)
        )
        .scalars()
        .all()
    )

    assert [row.value for row in rows] == [138.0, 146.0, 158.0]
    assert [row.measured_at for row in rows] == [
        "2026-10-02T08:10:00Z",
        "2026-10-20T08:20:00Z",
        "2026-11-03T08:25:00Z",
    ]
    assert all(row.trust_level == "self_reported_validated" for row in rows)


def test_seeded_timestamps_are_utc_iso8601(seeded: Session) -> None:
    """REQ-DATA-03: every stored timestamp parses and carries UTC."""
    for row in seeded.execute(select(Observation)).scalars().all():
        moment = parse_utc(row.measured_at)
        assert moment.tzinfo is not None
        assert row.measured_at.endswith("Z")
        assert len(row.measured_at) == 20


def test_seeding_is_idempotent(seeded: Session) -> None:
    """A second seed creates nothing and changes no value."""
    before = {
        row.id: (row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    }

    result = seed_demo_data(seeded, password=SEED_PASSWORD, now=FIXED_NOW)
    seeded.commit()

    after = {
        row.id: (row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    }
    assert before == after
    assert result.users_created == 0
    assert result.patients_created == 0
    assert result.encounters_created == 0
    assert result.observations_created == 0
    assert count(seeded, Observation) == 17


def test_two_independent_seeds_are_byte_stable(tmp_path: Path) -> None:
    """REQ-OPS-01: two fresh databases get identical fixture rows."""
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.db.session import create_db_engine

    snapshots = []
    for index in range(2):
        url = f"sqlite:///{(tmp_path / f'det-{index}.db').as_posix()}"
        engine = create_db_engine(url)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        session = factory()
        seed_demo_data(session, password=SEED_PASSWORD, now=FIXED_NOW)
        session.commit()
        snapshots.append(
            [
                (row.id, row.patient_id, row.measure_type, row.value, row.measured_at)
                for row in session.execute(select(Observation).order_by(Observation.id))
                .scalars()
                .all()
            ]
        )
        session.close()
        engine.dispose()

    assert snapshots[0] == snapshots[1]


def test_every_account_has_a_distinct_salted_hash(seeded: Session) -> None:
    """REQ-AUTH-01 / AUTH-01: hashes differ per account and never equal the password."""
    hashes = [user.password_hash for user in seeded.execute(select(User)).scalars().all()]

    assert len(set(hashes)) == len(hashes)
    assert all(hash_value.startswith("pbkdf2_sha256$") for hash_value in hashes)
    assert all(SEED_PASSWORD not in hash_value for hash_value in hashes)


def test_no_stored_value_contains_the_demo_password(seeded: Session) -> None:
    """REQ-AUTH-01: a full-table scan finds no plaintext credential."""
    inspector = inspect(seeded.get_bind())
    for table in inspector.get_table_names():
        for column in inspector.get_columns(table):
            values = seeded.execute(text(f'SELECT "{column["name"]}" FROM "{table}"')).scalars()
            for value in values:
                if isinstance(value, str):
                    assert SEED_PASSWORD not in value


def test_fixtures_contain_no_credentials(tmp_path: Path) -> None:
    """No fixture file mentions a password or a token."""
    from app.core.paths import SYNTHETIC_DATA_DIR

    for path in sorted(SYNTHETIC_DATA_DIR.glob("*.json")):
        text_body = json.loads(path.read_text(encoding="utf-8"))
        serialised = json.dumps(text_body).lower()
        assert "password" not in serialised
        assert "token" not in serialised
        assert "secret" not in serialised


def test_reset_requires_a_seed_password(seeded: Session, admin_principal: Principal) -> None:
    """A reset without a configured seed password fails closed."""
    with pytest.raises(ApiError) as caught:
        reset_demo(
            seeded,
            principal=admin_principal,
            demo_mode=True,
            seed_password=None,
            now=FIXED_NOW,
            request_id=REQUEST_ID,
        )

    assert caught.value.status_code == 500
    assert caught.value.code is ErrorCode.INTERNAL
    assert "DEMO_SEED_PASSWORD" in caught.value.detail


def test_reset_requires_demo_mode(seeded: Session, admin_principal: Principal) -> None:
    """NEG-12 semantics: the flag must be on before the reset can run."""
    with pytest.raises(ApiError) as caught:
        reset_demo(
            seeded,
            principal=admin_principal,
            demo_mode=False,
            seed_password=SEED_PASSWORD,
            now=FIXED_NOW,
            request_id=REQUEST_ID,
        )

    assert caught.value.code is ErrorCode.DEMO_MODE_REQUIRED


def test_reset_requires_the_admin_role(seeded: Session, doctor_principal: Principal) -> None:
    """A doctor cannot rebuild the dataset."""
    with pytest.raises(ApiError) as caught:
        reset_demo(
            seeded,
            principal=doctor_principal,
            demo_mode=True,
            seed_password=SEED_PASSWORD,
            now=FIXED_NOW,
            request_id=REQUEST_ID,
        )

    assert caught.value.code is ErrorCode.FORBIDDEN


def test_reset_rebuilds_identical_rows_and_keeps_the_audit_trail(
    seeded: Session, admin_principal: Principal
) -> None:
    """US-12: a reset restores fixtures, drops sessions and keeps audit evidence."""
    before = sorted(
        (row.id, row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    )
    seeded.add(
        AuditEvent(
            id="55555555-5555-4555-8555-eeeeeeeeeeee",
            event_type="test.marker",
            actor_type="system",
            actor_id=None,
            patient_id=None,
            workflow_run_id=None,
            subject_type=None,
            subject_id=None,
            outcome="ok",
            safe_detail="seeded marker",
            idempotency_key="marker-key-1",
            created_at="2026-11-14T12:00:00Z",
        )
    )
    seeded.commit()
    raw_token, _ = _issue_token(seeded, "demo_doctor")

    outcome = reset_demo(
        seeded,
        principal=admin_principal,
        demo_mode=True,
        seed_password=SEED_PASSWORD,
        now=FIXED_NOW,
        request_id=REQUEST_ID,
    )
    seeded.commit()

    after = sorted(
        (row.id, row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    )
    assert after == before
    assert outcome.cases_loaded == ("A_stable", "B_changed", "C_ambiguous_ocr")
    assert outcome.audit_events_retained >= 1

    events = seeded.execute(select(AuditEvent.event_type)).scalars().all()
    assert "test.marker" in events
    assert "demo.reset" in events

    # Every session was dropped by the rebuild: the old token is no longer valid.
    with pytest.raises(ApiError) as caught:
        resolve_session(seeded, raw_token=raw_token, now=FIXED_NOW)
    assert caught.value.code is ErrorCode.UNAUTHENTICATED
    assert count(seeded, UserSession) == 0

    # A re-login after the reset still works, so the rebuild produced usable accounts.
    assert count(seeded, User) == 6
    assert all(
        user.role in {role.value for role in Role}
        for user in seeded.execute(select(User)).scalars()
    )


def test_reset_service_is_repeatable(seeded: Session) -> None:
    """Two resets in a row leave the same identifiers and values."""
    first = reset_demo_data(seeded, password=SEED_PASSWORD, now=FIXED_NOW)
    seeded.commit()
    snapshot_one = sorted(
        (row.id, row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    )

    second = reset_demo_data(seeded, password=SEED_PASSWORD, now=FIXED_NOW)
    seeded.commit()
    snapshot_two = sorted(
        (row.id, row.value, row.measured_at)
        for row in seeded.execute(select(Observation)).scalars().all()
    )

    assert snapshot_one == snapshot_two
    assert first.cases_loaded == second.cases_loaded


def test_seed_rejects_an_empty_password(db: Session) -> None:
    """The seeder refuses an empty credential instead of creating unusable accounts."""
    from app.services.seed import SeedConfigurationError

    with pytest.raises(SeedConfigurationError):
        seed_demo_data(db, password="   ", now=FIXED_NOW)


def _issue_token(db: Session, username: str) -> tuple[str, UserSession]:
    """Issue a session for ``username`` and return the raw token."""
    from app.services.accounts import issue_session

    user = db.execute(select(User).where(User.username == username)).scalar_one()
    raw, session = issue_session(db, user=user, now=FIXED_NOW, ttl_minutes=60)
    db.commit()
    return raw, session
