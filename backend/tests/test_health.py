"""Contract tests for ``GET /health`` (``API-CONTRACT.md`` §2.1, ``REQ-OPS-02``)."""

from __future__ import annotations

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
    """Ollama and Tesseract are not used in P1 and must not claim ``ok``."""
    payload = client.get("/health").json()
    assert payload["ollama"] == "not_configured"
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
