"""Contract tests for ``GET /version`` (``API_CONTRACT.md`` §2.1, ``REQ-OPS-02``)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.version import API_VERSION, APP_VERSION, POLICY_VERSION, WORKFLOW_VERSION

EXPECTED_KEYS = {
    "app_version",
    "api_version",
    "workflow_version",
    "policy_version",
    "git_sha",
}


def test_version_returns_200(client: TestClient) -> None:
    """P1 acceptance: ``/version`` is functional and returns HTTP 200."""
    assert client.get("/version").status_code == 200


def test_version_matches_contract_schema(client: TestClient) -> None:
    """Required fields from the accepted P0 ``VersionInfo`` schema are present."""
    payload = client.get("/version").json()

    assert set(payload) == EXPECTED_KEYS
    assert payload["api_version"] == API_VERSION
    assert payload["workflow_version"] == WORKFLOW_VERSION
    assert payload["policy_version"] == POLICY_VERSION
    assert payload["app_version"] == APP_VERSION


def test_version_git_sha_is_real_or_unknown(client: TestClient) -> None:
    """``git_sha`` is a 7-40 char lowercase hex SHA or the literal ``unknown``."""
    sha = client.get("/version").json()["git_sha"]

    assert sha == "unknown" or (7 <= len(sha) <= 40 and all(ch in "0123456789abcdef" for ch in sha))


def test_version_uses_explicit_app_git_sha(
    monkeypatch: pytest.MonkeyPatch, migrated_db: str
) -> None:
    """An explicit ``APP_GIT_SHA`` is reported verbatim (deterministic, CI-friendly)."""
    monkeypatch.setenv("DATABASE_URL", migrated_db)
    monkeypatch.setenv("APP_GIT_SHA", "0123456789abcdef0123456789abcdef01234567")

    from app.core.config import reset_settings_cache
    from app.main import create_app

    reset_settings_cache()
    try:
        with TestClient(create_app()) as test_client:
            assert test_client.get("/version").json()["git_sha"] == (
                "0123456789abcdef0123456789abcdef01234567"
            )
    finally:
        reset_settings_cache()


def test_version_is_deterministic(client: TestClient) -> None:
    """Two consecutive calls return identical metadata."""
    assert client.get("/version").json() == client.get("/version").json()


def test_version_leaks_no_secrets_or_paths(client: TestClient) -> None:
    """``/version`` exposes versions only — no paths, credentials or env dumps."""
    body = client.get("/version").text.lower()

    for forbidden in ("password", "secret", "token", "api_key", "data/runtime", "c:\\", "/home/"):
        assert forbidden not in body


def test_invalid_git_sha_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed ``APP_GIT_SHA`` fails fast instead of being echoed."""
    from app.core.config import Settings, reset_settings_cache

    monkeypatch.setenv("APP_GIT_SHA", "not-a-sha")
    reset_settings_cache()
    try:
        with pytest.raises(ValueError, match="APP_GIT_SHA"):
            Settings()
    finally:
        reset_settings_cache()
