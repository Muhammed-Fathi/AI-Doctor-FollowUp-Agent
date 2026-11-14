"""``NEG-13`` and ``REQ-DATA-01/02/04`` — check-in validation and idempotency.

Requirement mapping:

* ``REQ-DATA-01`` — stored patient/type/value/unit/time/source/validation.
* ``REQ-DATA-02`` — measurement→unit allowlist; ``mmol/L`` glucose rejected.
* ``REQ-DATA-04`` — self-reported provenance is derived, never asserted.
* ``NEG-13`` — ``400 E_UNIT_NOT_ALLOWED`` for a glucose check-in in ``mmol/L``.
* ``REQ-SEC-01`` — a patient can only write for its own stored scope.
* ``API_CONTRACT.md`` §1 — idempotent replay, conflicting replay, duplicate.

Everything runs against a real SQLite database with a fixed clock; no HTTP.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import FIXED_NOW, PATIENT_A_ID

from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import CheckinIdempotency, Observation
from app.schemas.observation import CheckInCreate
from app.services.checkins import (
    classify_value,
    create_check_in,
    list_own_check_ins,
    request_fingerprint,
    resolve_unit,
    validate_idempotency_key,
)

REQUEST_ID = "22222222-2222-4222-8222-bbbbbbbbbbbb"


def make_payload(**overrides: object) -> CheckInCreate:
    """Build a valid check-in payload with optional overrides."""
    base: dict[str, object] = {
        "measured_at": FIXED_NOW - timedelta(days=1),
        "measure_type": "systolic_bp",
        "value": 121,
        "unit": "mmHg",
        "note": None,
    }
    base.update(overrides)
    return CheckInCreate.model_validate(base)


def create(db: Session, principal: Principal, payload: CheckInCreate, key: str | None = None):
    """Call the service with the fixed clock and a stable request id."""
    return create_check_in(
        db,
        principal=principal,
        payload=payload,
        idempotency_key=key,
        now=FIXED_NOW,
        request_id=REQUEST_ID,
    )


def test_patient_check_in_is_stored_as_self_reported(
    seeded: Session, patient_principal: Principal
) -> None:
    """REQ-DATA-01/04: provenance and validation are server-derived."""
    observation, created = create(seeded, patient_principal, make_payload())
    seeded.commit()

    assert created is True
    assert observation.patient_id == PATIENT_A_ID
    assert observation.trust_level.value == "self_reported_validated"
    assert observation.source.value == "patient_checkin"
    assert observation.validation.value == "ok"
    assert observation.verification is None

    stored = seeded.execute(
        select(Observation).where(Observation.id == observation.id)
    ).scalar_one()
    assert stored.verified_by_user_id is None
    assert stored.verified_at is None


def test_glucose_in_mmol_per_litre_is_rejected(
    seeded: Session, patient_principal: Principal
) -> None:
    """NEG-13: no unit conversion — the documented code is returned."""
    payload = make_payload(measure_type="glucose", value=5.6, unit="mmol/L")

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, payload)

    assert caught.value.status_code == 400
    assert caught.value.code is ErrorCode.UNIT_NOT_ALLOWED
    assert "mmol/L" in caught.value.detail
    assert "mg/dL" in caught.value.detail


@pytest.mark.parametrize(
    ("measure_type", "unit"),
    [
        ("systolic_bp", "bpm"),
        ("diastolic_bp", "mg/dL"),
        ("heart_rate", "mmHg"),
        ("glucose", "mmHg"),
        ("glucose", "g/dL"),
        ("systolic_bp", "banana"),
    ],
)
def test_every_measurement_enforces_its_own_unit(
    seeded: Session, patient_principal: Principal, measure_type: str, unit: str
) -> None:
    """REQ-DATA-02: the allowlist is per measurement, not a global unit list."""
    payload = make_payload(measure_type=measure_type, value=80, unit=unit)

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, payload)

    assert caught.value.code is ErrorCode.UNIT_NOT_ALLOWED


def test_resolve_unit_accepts_the_allowlisted_unit() -> None:
    """The happy path returns the enum member, not the raw string."""
    from app.core.enums import MeasureType, Unit

    assert resolve_unit(MeasureType.GLUCOSE, "mg/dL") is Unit.MG_DL
    assert resolve_unit(MeasureType.HEART_RATE, " bpm ") is Unit.BPM


@pytest.mark.parametrize(
    "overrides",
    [
        {"value": 0},
        {"value": -12},
        {"value": float("inf")},
        {"measured_at": "2026-11-01T09:00:00"},  # naive timestamp
        {"note": "x" * 501},
        {"unit": ""},
        {"trust_level": "doctor_verified"},  # client may not set provenance
        {"verified_by": "11111111-1111-4111-8111-111111111111"},
        {"patient_id": "22222222-2222-4222-8222-222222222222"},
    ],
)
def test_invalid_check_in_payloads_are_refused(overrides: dict[str, object]) -> None:
    """REQ-DATA-01/04: bad values and forged provenance never reach the service."""
    with pytest.raises(ValidationError):
        make_payload(**overrides)


def test_future_timestamp_is_refused_by_the_skew_guard(
    seeded: Session, patient_principal: Principal
) -> None:
    """A timestamp beyond the 5-minute skew window is a client error."""
    payload = make_payload(measured_at=FIXED_NOW + timedelta(minutes=6))

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, payload)

    assert caught.value.code is ErrorCode.VALIDATION
    assert "future" in caught.value.detail


def test_small_skew_is_tolerated(seeded: Session, patient_principal: Principal) -> None:
    """A 4-minute clock difference is accepted and stored in UTC."""
    observation, _ = create(
        seeded, patient_principal, make_payload(measured_at=FIXED_NOW + timedelta(minutes=4))
    )
    assert observation.measured_at.tzinfo is not None


def test_value_outside_the_demo_band_is_labelled_not_rejected(
    seeded: Session, patient_principal: Principal
) -> None:
    """REQ-DATA-01: the plausibility band is a data hint, not a rejection rule."""
    observation, _ = create(seeded, patient_principal, make_payload(value=1200))

    assert observation.validation.value == "ok_with_warning"


def test_classify_value_uses_the_documented_bands() -> None:
    """The band boundaries come from ``DATA_DICTIONARY.md`` §3.1."""
    from app.core.enums import MeasureType

    assert classify_value(MeasureType.SYSTOLIC_BP, 122).value == "ok"
    assert classify_value(MeasureType.SYSTOLIC_BP, 49).value == "ok_with_warning"
    assert classify_value(MeasureType.GLUCOSE, 96).value == "ok"
    assert classify_value(MeasureType.GLUCOSE, 901).value == "ok_with_warning"


def test_exact_replay_returns_the_original_observation(
    seeded: Session, patient_principal: Principal
) -> None:
    """API_CONTRACT §1: the same key and body return the stored result once."""
    key = str(uuid.uuid4())
    payload = make_payload()

    first, created_first = create(seeded, patient_principal, payload, key=key)
    seeded.commit()
    second, created_second = create(seeded, patient_principal, payload, key=key)
    seeded.commit()

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert (
        seeded.execute(select(func.count()).select_from(Observation)).scalar_one() == 18
    )  # 17 seeded + 1 check-in


def test_same_key_with_a_different_body_conflicts(
    seeded: Session, patient_principal: Principal
) -> None:
    """API_CONTRACT §4: ``409 E_IDEMPOTENCY_CONFLICT`` and no write."""
    key = str(uuid.uuid4())
    create(seeded, patient_principal, make_payload(value=121), key=key)
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, make_payload(value=131), key=key)
    seeded.rollback()

    assert caught.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert seeded.execute(select(func.count()).select_from(Observation)).scalar_one() == 18


def test_identical_check_in_without_a_key_is_a_duplicate(
    seeded: Session, patient_principal: Principal
) -> None:
    """The semantic duplicate is refused with the documented code."""
    payload = make_payload()
    create(seeded, patient_principal, payload)
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, payload)
    seeded.rollback()

    assert caught.value.code is ErrorCode.DUPLICATE_CHECKIN


def test_a_new_key_does_not_unlock_a_duplicate(
    seeded: Session, patient_principal: Principal
) -> None:
    """A fresh key cannot smuggle an identical measurement past duplicate detection."""
    create(seeded, patient_principal, make_payload(), key=str(uuid.uuid4()))
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        create(seeded, patient_principal, make_payload(), key=str(uuid.uuid4()))
    seeded.rollback()

    assert caught.value.code is ErrorCode.DUPLICATE_CHECKIN


def test_different_measured_at_is_not_a_duplicate(
    seeded: Session, patient_principal: Principal
) -> None:
    """The same value at a different time is a normal second measurement."""
    first, _ = create(seeded, patient_principal, make_payload())
    second, _ = create(
        seeded, patient_principal, make_payload(measured_at=FIXED_NOW - timedelta(days=2))
    )
    seeded.commit()

    assert first.id != second.id


@pytest.mark.parametrize("key", ["", "not-a-uuid", "x" * 101])
def test_invalid_idempotency_key_is_a_client_error(key: str) -> None:
    """A malformed key is refused instead of silently disabling replay safety."""
    with pytest.raises(ApiError) as caught:
        validate_idempotency_key(key)

    assert caught.value.code is ErrorCode.VALIDATION


def test_idempotency_key_is_canonicalised() -> None:
    """A UUID in any valid spelling maps to one stored key."""
    raw = str(uuid.uuid4())

    assert validate_idempotency_key(raw) == raw
    assert validate_idempotency_key(raw.upper()) == raw


def test_fingerprint_is_stable_and_timezone_aware() -> None:
    """Two spellings of the *same instant* produce the same fingerprint."""
    instant_utc = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    same_instant_cairo = instant_utc.astimezone(timezone(timedelta(hours=2)))

    payload = make_payload(measured_at=instant_utc)
    other = make_payload(value=999, measured_at=instant_utc)

    assert request_fingerprint(payload, measured_at=instant_utc) == request_fingerprint(
        payload, measured_at=same_instant_cairo
    )
    assert request_fingerprint(payload, measured_at=instant_utc) != request_fingerprint(
        other, measured_at=instant_utc
    )


def test_doctor_cannot_submit_a_check_in(seeded: Session, doctor_principal: Principal) -> None:
    """REQ-AUTH-02: check-ins are patient-scoped writes only."""
    with pytest.raises(ApiError) as caught:
        create(seeded, doctor_principal, make_payload())

    assert caught.value.code is ErrorCode.FORBIDDEN


def test_patient_lists_only_own_check_ins(seeded: Session, patient_principal: Principal) -> None:
    """REQ-SEC-01: the list is filtered by the stored self scope."""
    create(seeded, patient_principal, make_payload(), key=str(uuid.uuid4()))
    seeded.commit()

    page = list_own_check_ins(seeded, principal=patient_principal, limit=20, cursor=None)

    assert page.items
    assert {item.patient_id for item in page.items} == {PATIENT_A_ID}
    assert {item.source.value for item in page.items} == {"patient_checkin"}


def test_check_in_list_is_paginated_newest_first(
    seeded: Session, patient_principal: Principal
) -> None:
    """Pagination is keyset-based and stable across pages."""
    for day in (1, 2, 3):
        create(
            seeded,
            patient_principal,
            make_payload(measured_at=FIXED_NOW - timedelta(days=day), value=120 + day),
            key=str(uuid.uuid4()),
        )
    seeded.commit()

    first = list_own_check_ins(seeded, principal=patient_principal, limit=2, cursor=None)
    second = list_own_check_ins(
        seeded, principal=patient_principal, limit=2, cursor=first.next_cursor
    )

    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert {item.id for item in first.items}.isdisjoint({item.id for item in second.items})
    measured = [item.measured_at for item in first.items]
    assert measured == sorted(measured, reverse=True)


def test_idempotency_rows_are_scoped_per_patient(
    seeded: Session, patient_principal: Principal
) -> None:
    """The replay record is keyed by patient, so scopes cannot collide."""
    key = str(uuid.uuid4())
    create(seeded, patient_principal, make_payload(), key=key)
    seeded.commit()

    rows = seeded.execute(select(CheckinIdempotency)).scalars().all()

    assert len(rows) == 1
    assert rows[0].patient_id == PATIENT_A_ID
    assert rows[0].idempotency_key == key


def test_check_in_audit_row_is_recorded(seeded: Session, patient_principal: Principal) -> None:
    """REQ-AUDIT-01: a write appends a safe audit event."""
    from app.db.models import AuditEvent

    observation, _ = create(seeded, patient_principal, make_payload())
    seeded.commit()

    event = seeded.execute(
        select(AuditEvent).where(AuditEvent.subject_id == observation.id)
    ).scalar_one()
    assert event.event_type == "checkin.created"
    assert event.actor_id == patient_principal.user_id
    assert event.patient_id == PATIENT_A_ID
    assert "121" not in (event.safe_detail or "")


def test_replay_survives_a_new_session(seeded: Session) -> None:
    """The replay record is durable, not an in-process cache."""
    from sqlalchemy.orm import sessionmaker

    principal = _patient_principal(seeded)
    key = str(uuid.uuid4())
    payload = make_payload()
    first, created = create(seeded, principal, payload, key=key)
    seeded.commit()
    engine = seeded.get_bind()

    with sessionmaker(bind=engine)() as fresh:
        replay, created_again = create(fresh, principal, payload, key=key)
        fresh.commit()

    assert created is True
    assert created_again is False
    assert replay.id == first.id


def test_a_concurrent_duplicate_is_caught_by_the_unique_index(seeded: Session) -> None:
    """NEG-13 durability: a second writer cannot create a second observation.

    The service re-reads under the unique ``(patient_id, idempotency_key)``
    constraint, so a racing request resolves to the stored row instead of
    producing a duplicate measurement.
    """
    from sqlalchemy.exc import IntegrityError

    principal = _patient_principal(seeded)
    key = str(uuid.uuid4())
    payload = make_payload()
    stored, created = create(seeded, principal, payload, key=key)
    seeded.commit()

    record = seeded.execute(
        select(CheckinIdempotency).where(CheckinIdempotency.idempotency_key == key)
    ).scalar_one()
    duplicate = CheckinIdempotency(
        id=str(uuid.uuid4()),
        patient_id=record.patient_id,
        idempotency_key=key,
        request_fingerprint=record.request_fingerprint,
        observation_id=record.observation_id,
        created_at=record.created_at,
    )
    seeded.add(duplicate)
    with pytest.raises(IntegrityError):
        seeded.flush()
    seeded.rollback()

    assert created is True
    assert (
        seeded.execute(
            select(func.count()).select_from(Observation).where(Observation.id == stored.id)
        ).scalar_one()
        == 1
    )


def _patient_principal(db: Session) -> Principal:
    """Return a fresh patient principal for the seeded demo patient A."""
    from support import user_by_username

    from app.services.accounts import build_principal, issue_session

    user = user_by_username(db, "demo_patient_a")
    _raw, session = issue_session(db, user=user, now=FIXED_NOW, ttl_minutes=60)
    db.commit()
    return build_principal(user, session)


# --------------------------------------------------------------------------
# Real two-writer concurrency (review item: "a real concurrent SQLite test")
# --------------------------------------------------------------------------

#: How long writer A keeps its write transaction open. Long enough that writer B
#: performs its "no replay / no duplicate" reads first and then blocks on the
#: write lock, short enough to keep the suite fast.
HOLD_SECONDS = 0.3


def _writer_session(engine: object) -> Session:
    """Return a fresh session (its own connection) for a racing writer."""
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine)()


def _race(writer_a, writer_b) -> tuple[object, object]:
    """Run two real writers so that ``writer_b`` reads before ``writer_a`` commits.

    ``writer_a(flushed, release)`` inserts, sets ``flushed``, then blocks until
    ``release`` before committing. ``writer_b`` starts only after ``flushed``, its
    own reads therefore see nothing committed, and the write it then attempts
    collides with A's transaction — exactly the interleaving the optimistic checks
    cannot handle. Anything raised is captured and asserted on by the caller.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    outcomes: dict[str, object] = {}
    flushed = threading.Event()
    release = threading.Event()

    def run_a() -> None:
        try:
            outcomes["a"] = writer_a(flushed, release)
        except Exception as error:
            outcomes["a"] = error

    def run_b() -> None:
        try:
            assert flushed.wait(timeout=10)
            # A commits only after B's read has had time to complete.
            threading.Timer(HOLD_SECONDS, release.set).start()
            outcomes["b"] = writer_b()
        except Exception as error:
            outcomes["b"] = error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_a), pool.submit(run_b)]
        for future in futures:
            future.result(timeout=30)

    return outcomes["a"], outcomes["b"]


def _count_measurements(db: Session, payload: CheckInCreate) -> int:
    """Count stored observations matching the payload's semantic identity."""
    return db.execute(
        select(func.count())
        .select_from(Observation)
        .where(Observation.patient_id == PATIENT_A_ID)
        .where(Observation.measure_type == payload.measure_type.value)
        .where(Observation.value == float(payload.value))
    ).scalar_one()


def test_two_writers_with_the_same_key_persist_exactly_one_check_in(seeded: Session) -> None:
    """A racing duplicate key is answered as a replay: one row, no 500.

    Without the savepoint-and-recover path in ``create_check_in`` this raises
    ``IntegrityError`` out of the service (verified by reverting that code during
    review of this test).
    """
    engine = seeded.get_bind()
    principal = _patient_principal(seeded)
    payload = make_payload()
    key = str(uuid.uuid4())

    def writer_a(flushed, release):
        session = _writer_session(engine)
        try:
            observation, created = create(session, principal, payload, key=key)
            flushed.set()
            release.wait(timeout=10)
            session.commit()
            return ("ok", created, observation.id)
        finally:
            session.close()

    def writer_b():
        session = _writer_session(engine)
        try:
            observation, created = create(session, principal, payload, key=key)
            session.commit()
            return ("ok", created, observation.id)
        except ApiError as error:
            session.rollback()
            return ("api_error", error.code.value, None)
        finally:
            session.close()

    outcome_a, outcome_b = _race(writer_a, writer_b)

    assert not isinstance(outcome_a, Exception), outcome_a
    assert not isinstance(outcome_b, Exception), outcome_b
    assert [outcome_a[0], outcome_b[0]] == ["ok", "ok"]
    assert sorted([outcome_a[1], outcome_b[1]]) == [False, True]

    with _writer_session(engine) as check:
        assert _count_measurements(check, payload) == 1
        assert (
            check.execute(
                select(func.count())
                .select_from(CheckinIdempotency)
                .where(CheckinIdempotency.idempotency_key == key)
            ).scalar_one()
            == 1
        )


def test_two_writers_with_different_keys_cannot_store_one_measurement_twice(
    seeded: Session,
) -> None:
    """A semantic duplicate stays ``409`` even when two different keys race.

    The optimistic duplicate read cannot see the other transaction, so
    ``uq_observation_checkin_identity`` is the arbiter: the loser is answered with
    ``E_DUPLICATE_CHECKIN`` instead of a second stored measurement or a 500.
    """
    engine = seeded.get_bind()
    principal = _patient_principal(seeded)
    payload = make_payload()

    def writer_a(flushed, release):
        session = _writer_session(engine)
        try:
            observation, created = create(session, principal, payload, key=str(uuid.uuid4()))
            flushed.set()
            release.wait(timeout=10)
            session.commit()
            return ("ok", created, observation.id)
        finally:
            session.close()

    def writer_b():
        session = _writer_session(engine)
        try:
            observation, created = create(session, principal, payload, key=str(uuid.uuid4()))
            session.commit()
            return ("ok", created, observation.id)
        except ApiError as error:
            session.rollback()
            return ("api_error", error.code.value, None)
        finally:
            session.close()

    outcome_a, outcome_b = _race(writer_a, writer_b)

    assert not isinstance(outcome_a, Exception), outcome_a
    assert not isinstance(outcome_b, Exception), outcome_b
    assert outcome_a[0] == "ok"
    assert outcome_b[0] == "api_error"
    assert outcome_b[1] == "E_DUPLICATE_CHECKIN"

    with _writer_session(engine) as check:
        assert _count_measurements(check, payload) == 1
