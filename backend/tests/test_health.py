"""Contract tests for ``GET /health`` (``API-CONTRACT.md`` §2.1, ``REQ-OPS-02``)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

EXPECTED_KEYS = {"status", "version", "db", "ollama", "tesseract", "disclaimer"}
DEPENDENCY_VALUES = {"ok", "unavailable", "not_configured"}


def test_health_returns_200(client: TestClient) -> None:
    """P1 acceptance: ``/health`` returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_matches_contract_schema(client: TestClient) -> None:
    """Response keys and enum values match the accepted P0 OpenAPI contract."""
    payload = client.get("/health").json()

    assert set(payload) == EXPECTED_KEYS
    assert payload["status"] in {"ok", "degraded"}
    assert isinstance(payload["version"], str) and payload["version"]
    for field in ("db", "ollama", "tesseract"):
        assert payload[field] in DEPENDENCY_VALUES


def test_health_reports_database_ok_when_migrated(client: TestClient) -> None:
    """A reachable, migrated SQLite database reports ``ok`` and overall ``ok``."""
    payload = client.get("/health").json()
    assert payload["db"] == "ok"
    assert payload["status"] == "ok"


def test_health_reports_degraded_without_leaking_details(offline_client: TestClient) -> None:
    """An unreachable database degrades health without leaking paths or errors."""
    response = offline_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["db"] == "unavailable"
    assert payload["status"] == "degraded"

    body = response.text
    assert "missing.db" not in body
    assert "Traceback" not in body
    assert "OperationalError" not in body


def test_health_reports_unimplemented_dependencies_honestly(client: TestClient) -> None:
    """When unconfigured, Ollama and Tesseract report ``not_configured`` honestly."""
    payload = client.get("/health").json()
    assert payload["ollama"] == "not_configured"
    assert payload["tesseract"] == "not_configured"


def test_health_reports_tesseract_ok_when_configured_and_working(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, tmp_path: Path
) -> None:
    """A configured, runnable Tesseract engine surfaces as ``ok``."""
    from app.core.config import reset_settings_cache
    from app.services.documents import ocr as ocr_module

    fake_engine = tmp_path / "tesseract"
    fake_engine.write_text("", encoding="utf-8")
    monkeypatch.setenv("TESSERACT_CMD", str(fake_engine))
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")
    reset_settings_cache()

    payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert payload["tesseract"] == "ok"
    assert payload["ollama"] == "not_configured"


def test_health_reports_tesseract_unavailable_when_configured_path_missing(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, tmp_path: Path
) -> None:
    """A configured path that cannot run reports ``unavailable``, keeping liveness ``ok``."""
    from app.core.config import reset_settings_cache

    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "absent" / "tesseract"))
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    reset_settings_cache()

    payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert payload["tesseract"] == "unavailable"


def test_client_fixture_ignores_host_tesseract_cmd(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """Ambient ``TESSERACT_CMD`` on the host does not leak into ``client``-based tests."""
    from app.services.documents import ocr as ocr_module

    fake_engine = tmp_path / "tesseract"
    fake_engine.write_text("", encoding="utf-8")
    monkeypatch.setenv("TESSERACT_CMD", str(fake_engine))
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    isolated_client: TestClient = request.getfixturevalue("client")
    payload = isolated_client.get("/health").json()
    assert payload["tesseract"] == "not_configured"


def test_health_carries_educational_disclaimer(client: TestClient, demo_notice: str) -> None:
    """``REQ-SEC-05``: the educational notice is present on the public surface."""
    assert client.get("/health").json()["disclaimer"] == demo_notice


def test_health_is_deterministic(client: TestClient) -> None:
    """Two consecutive calls return byte-identical payloads."""
    first = client.get("/health")
    second = client.get("/health")
    assert first.json() == second.json()


def test_health_never_reports_clinical_state(client: TestClient) -> None:
    """Health reports process facts only — no clinical or demo-success fields."""
    payload = client.get("/health").json()
    forbidden = {"diagnosis", "risk", "triage", "alert", "clinical_status", "demo_ok"}
    assert forbidden.isdisjoint(payload)


def test_health_rejects_unknown_query_parameters(client: TestClient) -> None:
    """Arguments are ignored by FastAPI, but the endpoint must stay side-effect free."""
    response = client.get("/health", params={"patient_id": "ignored"})
    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_KEYS
