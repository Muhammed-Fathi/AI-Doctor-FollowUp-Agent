"""End-to-end HTTP lifecycle for the P2 doctor, patient and demo routes.

These are the tests that were **NOT RUN** before scope authorization: they drive
the route table through the production application
(:func:`app.main.create_app`) rather than calling services directly, so route
wiring, dependency injection, problem-envelope rendering and status codes are all
under test.

Covered here:

* ``REQ-AUTH-03``/``NEG-10`` — every protected route answers 401 without a token,
* ``REQ-SEC-01``/``NEG-02`` — assignment scope is enforced server-side,
* ``REQ-DATA-01/02``/``NEG-13`` — check-in validation and the unit allowlist,
* §1 idempotency — replay, conflict, duplicate,
* ``API_CONTRACT.md`` §2.6 — demo reset is admin-only and demo-mode-only.

The database is created by the **Alembic migration** (``conftest.migrated_api_db``)
so the tests also prove the migration and the ORM agree.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from support import (
    FIXED_NOW,
    PATIENT_A_ID,
    PATIENT_B_ID,
    PATIENT_C_ID,
    SEED_PASSWORD,
    TEST_HASH_ITERATIONS,
    bearer,
)

from app.api.v1.auth.dependencies import clear_limiter_cache, current_time
from app.core.config import Settings, reset_settings_cache
from app.db.session import create_db_engine, get_db_session
from app.main import create_app
from app.services.seed import seed_demo_data

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
DOCTOR_PATIENTS = "/api/v1/doctor/patients"
PATIENT_HEADER = f"/api/v1/doctor/patients/{PATIENT_A_ID}"
TIMELINE = f"/api/v1/doctor/patients/{PATIENT_A_ID}/timeline"
OBSERVATIONS = f"/api/v1/doctor/patients/{PATIENT_A_ID}/observations"
CHECK_INS = "/api/v1/patient/check-ins"
DEMO_RESET = "/api/v1/demo/reset"


def _settings(tmp_path: Path, *, demo_mode: bool) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'http.db').as_posix()}",
        app_env="test",
        demo_mode=demo_mode,
        demo_seed_password=SEED_PASSWORD,
        session_ttl_minutes=60,
        login_rate_limit_attempts=5,
        login_rate_limit_window_seconds=300,
    )


def _migrate(settings: Settings) -> None:
    """Apply the real migrations to the test database."""
    from alembic import command
    from alembic.config import Config

    from app.core.paths import REPO_ROOT

    config = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


def _client(settings: Settings, session: Session) -> TestClient:
    app = create_app(settings)
    app.dependency_overrides[current_time] = lambda: FIXED_NOW

    def _session_override() -> Iterator[Session]:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_db_session] = _session_override
    return TestClient(app)


@pytest.fixture()
def http_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Settings, Session]]:
    """A migrated, seeded database plus the production app bound to it."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_SEED_PASSWORD", SEED_PASSWORD)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'http.db').as_posix()}")
    reset_settings_cache()
    clear_limiter_cache()

    settings = _settings(tmp_path, demo_mode=True)
    _migrate(settings)

    engine = create_db_engine(settings.database_url)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    seed_demo_data(session, password=SEED_PASSWORD, now=FIXED_NOW, iterations=TEST_HASH_ITERATIONS)
    session.commit()
    try:
        yield settings, session
    finally:
        session.close()
        engine.dispose()
        clear_limiter_cache()
        reset_settings_cache()


def _login(client: TestClient, username: str, password: str = SEED_PASSWORD) -> str:
    response = client.post(LOGIN, json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def http(http_env: tuple[Settings, Session]) -> Iterator[TestClient]:
    settings, session = http_env
    with _client(settings, session) as client:
        yield client


# --------------------------------------------------------------------------
# Authentication gate (NEG-10): every protected route is 401 without a token
# --------------------------------------------------------------------------


PROTECTED_GETS = [ME, DOCTOR_PATIENTS, PATIENT_HEADER, TIMELINE, OBSERVATIONS, CHECK_INS]


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_get_routes_require_a_token(http: TestClient, path: str) -> None:
    """NEG-10: no token, no data — uniform 401 problem envelope."""
    response = http.get(path)

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "E_UNAUTHENTICATED"
    assert body["request_id"]
    assert "Demo Patient" not in response.text


def test_protected_post_routes_require_a_token(http: TestClient) -> None:
    """NEG-10: the write routes and logout are equally closed."""
    check_in = http.post(
        CHECK_INS,
        json={
            "measured_at": (FIXED_NOW - timedelta(days=1)).isoformat(),
            "measure_type": "systolic_bp",
            "value": 121,
            "unit": "mmHg",
        },
    )
    logout = http.post("/api/v1/auth/logout")
    reset = http.post(DEMO_RESET)

    assert check_in.status_code == 401
    assert logout.status_code == 401
    assert reset.status_code == 401


# --------------------------------------------------------------------------
# Doctor routes (US-07, NEG-02, REQ-SEC-01)
# --------------------------------------------------------------------------


def test_doctor_lists_only_assigned_patients(http: TestClient) -> None:
    """The list comes from assignments, never from a query parameter."""
    token = _login(http, "demo_doctor")

    response = http.get(DOCTOR_PATIENTS, headers=bearer(token))

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {PATIENT_A_ID, PATIENT_B_ID, PATIENT_C_ID}
    assert all(item["data_source"] == "synthetic_fixture" for item in response.json()["items"])


def test_unassigned_doctor_gets_an_empty_page_not_someone_elses_patients(http: TestClient) -> None:
    """NEG-02 at HTTP level: an empty page, not a 200 with foreign rows."""
    token = _login(http, "demo_doctor_unassigned")

    response = http.get(DOCTOR_PATIENTS, headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_unassigned_doctor_is_denied_with_the_problem_envelope(http: TestClient) -> None:
    """NEG-02: 403 ``E_SCOPE_VIOLATION`` and no patient content in the body."""
    token = _login(http, "demo_doctor_unassigned")

    response = http.get(TIMELINE, headers=bearer(token))

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "E_SCOPE_VIOLATION"
    assert "Sara" not in response.text
    assert "DEMO-A-001" not in response.text


def test_doctor_reads_the_timeline_and_observation_series(http: TestClient) -> None:
    """US-07: timeline carries observations; later-phase collections stay empty."""
    token = _login(http, "demo_doctor")
    headers = bearer(token)

    timeline = http.get(TIMELINE, headers=headers)
    observations = http.get(OBSERVATIONS, headers=headers)
    header = http.get(PATIENT_HEADER, headers=headers)

    assert timeline.status_code == 200
    body = timeline.json()
    assert body["patient_id"] == PATIENT_A_ID
    assert body["documents"] == []
    assert body["review_items"] == []
    assert body["tasks"] == []
    assert len(body["observations"]) == 6
    assert all(item["trust_level"] == "self_reported_validated" for item in body["observations"])

    assert observations.status_code == 200
    assert {item["measure_type"] for item in observations.json()["items"]} <= {
        "systolic_bp",
        "diastolic_bp",
        "heart_rate",
        "glucose",
    }

    assert header.status_code == 200
    assert header.json()["external_ref"].startswith("DEMO-")


def test_observation_filters_are_applied_server_side(http: TestClient) -> None:
    """``measure_type`` filtering happens in SQL, not in the client."""
    token = _login(http, "demo_doctor")

    response = http.get(OBSERVATIONS, params={"measure_type": "systolic_bp"}, headers=bearer(token))

    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert {item["measure_type"] for item in items} == {"systolic_bp"}


def test_invalid_measure_type_is_a_validation_problem(http: TestClient) -> None:
    """An unsupported filter is a 400 problem, not a 500."""
    token = _login(http, "demo_doctor")

    response = http.get(OBSERVATIONS, params={"measure_type": "hba1c"}, headers=bearer(token))

    assert response.status_code == 400
    assert response.json()["code"] == "E_VALIDATION"


def test_unknown_and_malformed_patient_ids_are_distinguished(http: TestClient) -> None:
    """``404`` for a well-formed unknown id, ``400`` for a malformed one."""
    token = _login(http, "demo_doctor")
    unknown = http.get(f"/api/v1/doctor/patients/{uuid.uuid4()}", headers=bearer(token))
    malformed = http.get("/api/v1/doctor/patients/not-a-uuid", headers=bearer(token))

    assert unknown.status_code == 404
    assert unknown.json()["code"] == "E_NOT_FOUND"
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "E_VALIDATION"


def test_patient_role_cannot_use_the_doctor_surface(http: TestClient) -> None:
    """REQ-SEC-01: role gating is independent of the assignment check."""
    token = _login(http, "demo_patient_a")

    response = http.get(TIMELINE, headers=bearer(token))

    assert response.status_code == 403
    assert response.json()["code"] == "E_FORBIDDEN"


# --------------------------------------------------------------------------
# Patient check-in routes (§3.5, NEG-13, §1 idempotency)
# --------------------------------------------------------------------------


def _check_in_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "measured_at": (FIXED_NOW - timedelta(hours=3)).isoformat(),
        "measure_type": "heart_rate",
        "value": 72,
        "unit": "bpm",
    }
    body.update(overrides)
    return body


def test_patient_creates_and_reads_back_a_check_in(http: TestClient) -> None:
    """REQ-DATA-01/04: stored as self-reported; provenance is server-derived."""
    token = _login(http, "demo_patient_a")
    headers = bearer(token)

    created = http.post(CHECK_INS, json=_check_in_body(), headers=headers)
    listed = http.get(CHECK_INS, headers=headers)

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["trust_level"] == "self_reported_validated"
    assert body["source"] == "patient_checkin"
    assert body["validation"] == "ok"
    assert body["verification"] is None
    assert body["patient_id"] == PATIENT_A_ID

    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json()["items"])


def test_client_cannot_forge_provenance(http: TestClient) -> None:
    """REQ-DATA-04: extra fields are rejected, not silently ignored."""
    token = _login(http, "demo_patient_a")

    for field, value in (
        ("trust_level", "doctor_verified"),
        ("verification", {"verified_by": "x", "verified_at": "2026-11-14T00:00:00Z"}),
        ("patient_id", PATIENT_B_ID),
    ):
        response = http.post(
            CHECK_INS, json=_check_in_body(**{field: value}), headers=bearer(token)
        )
        assert response.status_code == 400, field
        assert response.json()["code"] == "E_VALIDATION"


def test_glucose_in_mmol_per_litre_is_refused_over_http(http: TestClient) -> None:
    """NEG-13 exactly: ``400 E_UNIT_NOT_ALLOWED`` and no stored row."""
    token = _login(http, "demo_patient_a")

    response = http.post(
        CHECK_INS,
        json=_check_in_body(measure_type="glucose", value=5.6, unit="mmol/L"),
        headers=bearer(token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "E_UNIT_NOT_ALLOWED"
    assert "mmol/L" in response.json()["detail"]


def test_idempotency_key_replay_returns_the_same_observation(http: TestClient) -> None:
    """§1: the same key and body is a replay, flagged by a response header."""
    token = _login(http, "demo_patient_a")
    key = str(uuid.uuid4())
    headers = {**bearer(token), "Idempotency-Key": key}
    body = _check_in_body()

    first = http.post(CHECK_INS, json=body, headers=headers)
    second = http.post(CHECK_INS, json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert "Idempotent-Replay" not in first.headers
    assert second.headers["Idempotent-Replay"] == "true"


def test_same_key_different_body_conflicts(http: TestClient) -> None:
    """§1: reuse with a different payload is ``409 E_IDEMPOTENCY_CONFLICT``."""
    token = _login(http, "demo_patient_a")
    key = str(uuid.uuid4())
    headers = {**bearer(token), "Idempotency-Key": key}

    assert http.post(CHECK_INS, json=_check_in_body(), headers=headers).status_code == 201
    conflicting = http.post(CHECK_INS, json=_check_in_body(value=99), headers=headers)

    assert conflicting.status_code == 409
    assert conflicting.json()["code"] == "E_IDEMPOTENCY_CONFLICT"


def test_duplicate_measurement_without_a_key_is_a_conflict(http: TestClient) -> None:
    """``409 E_DUPLICATE_CHECKIN`` for the same measurement twice."""
    token = _login(http, "demo_patient_a")
    headers = bearer(token)

    assert http.post(CHECK_INS, json=_check_in_body(), headers=headers).status_code == 201
    duplicate = http.post(CHECK_INS, json=_check_in_body(), headers=headers)

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "E_DUPLICATE_CHECKIN"


def test_check_ins_are_self_scoped(http: TestClient) -> None:
    """REQ-SEC-01: patient A's list never shows patient B's rows."""
    token_a = _login(http, "demo_patient_a")
    token_b = _login(http, "demo_patient_b")

    created = http.post(CHECK_INS, json=_check_in_body(), headers=bearer(token_a))
    assert created.status_code == 201

    list_a = http.get(CHECK_INS, headers=bearer(token_a)).json()["items"]
    list_b = http.get(CHECK_INS, headers=bearer(token_b)).json()["items"]

    assert all(item["patient_id"] == PATIENT_A_ID for item in list_a)
    assert list_b == []


def test_doctor_cannot_post_a_check_in(http: TestClient) -> None:
    """REQ-SEC-01: the patient write surface rejects a doctor."""
    token = _login(http, "demo_doctor")

    response = http.post(CHECK_INS, json=_check_in_body(), headers=bearer(token))

    assert response.status_code == 403
    assert response.json()["code"] == "E_FORBIDDEN"


def test_future_measurement_is_refused(http: TestClient) -> None:
    """The clock-skew guard uses the injected clock, not the wall clock."""
    token = _login(http, "demo_patient_a")
    body = _check_in_body(measured_at=(FIXED_NOW + timedelta(hours=2)).isoformat())

    response = http.post(CHECK_INS, json=body, headers=bearer(token))

    assert response.status_code == 400
    assert response.json()["code"] == "E_VALIDATION"


# --------------------------------------------------------------------------
# Demo reset (API_CONTRACT §2.6, US-12)
# --------------------------------------------------------------------------


def test_demo_reset_requires_the_admin_role(http: TestClient) -> None:
    """``403`` for a doctor even with demo mode on."""
    token = _login(http, "demo_doctor")

    response = http.post(DEMO_RESET, headers=bearer(token))

    assert response.status_code == 403
    assert response.json()["code"] == "E_FORBIDDEN"


def test_demo_reset_succeeds_for_the_admin_and_keeps_the_audit_trail(http: TestClient) -> None:
    """US-12: reset reloads the fixtures and reports the cases."""
    token = _login(http, "demo_admin")

    response = http.post(DEMO_RESET, headers=bearer(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cases_loaded"] == ["A_stable", "B_changed", "C_ambiguous_ocr"]
    assert body["disclaimer"].startswith("Synthetic demo data only")
    assert body["reset_at"].startswith("2026-11-14T12:00:00")


def test_demo_reset_is_refused_when_demo_mode_is_off(tmp_path: Path) -> None:
    """``403 E_DEMO_MODE_REQUIRED``: the safe default cannot be bypassed."""
    settings = _settings(tmp_path, demo_mode=False)
    _migrate(settings)
    engine = create_db_engine(settings.database_url)
    session = Session(engine, autoflush=False, expire_on_commit=False)
    seed_demo_data(session, password=SEED_PASSWORD, now=FIXED_NOW, iterations=TEST_HASH_ITERATIONS)
    session.commit()

    try:
        with _client(settings, session) as client:
            token = _login(client, "demo_admin")
            response = client.post(DEMO_RESET, headers=bearer(token))
    finally:
        session.close()
        engine.dispose()

    assert response.status_code == 403
    assert response.json()["code"] == "E_DEMO_MODE_REQUIRED"


def test_demo_status_is_not_implemented(http: TestClient) -> None:
    """``OQ-P2-01``: the conditional endpoint is deferred, so it 404s."""
    token = _login(http, "demo_admin")

    response = http.get("/api/v1/demo/status", headers=bearer(token))

    assert response.status_code == 404


def test_demo_seed_route_does_not_exist(http: TestClient) -> None:
    """No seed endpoint is exposed; first-run seeding is the local CLI."""
    token = _login(http, "demo_admin")

    response = http.post("/api/v1/demo/seed", headers=bearer(token))

    assert response.status_code == 404
