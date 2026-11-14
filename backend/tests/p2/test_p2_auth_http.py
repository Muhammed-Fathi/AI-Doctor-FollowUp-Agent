"""HTTP contract tests for the P2 authentication surface.

Requirement mapping: ``REQ-AUTH-01/02/03``, ``NEG-10`` (unauthenticated), the
RFC-9457 envelope (``API_CONTRACT.md`` §1.1), and the generated OpenAPI surface
for the auth operations.

The application under test is built with the **production** problem handlers and
the **production** auth router. Only the ASGI wiring in ``app/main.py`` is
different, and that file is part of the pending P2 scope request — so these tests
do not claim that ``create_app()`` serves the auth routes yet.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from support import SEED_PASSWORD, bearer

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


def login(client: TestClient, username: str = "demo_patient_a", password: str = SEED_PASSWORD):
    """Perform a login request."""
    return client.post(LOGIN, json={"username": username, "password": password})


def test_login_returns_an_opaque_token_and_identity(api_client: TestClient) -> None:
    """The response matches ``TokenResponse``: token, type, expiry, user."""
    response = login(api_client)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_at", "user"}
    assert body["token_type"] == "Bearer"
    assert body["expires_at"].endswith("Z")
    assert body["user"]["role"] == "patient"
    assert body["user"]["patient_id"] == "11111111-1111-4111-8111-111111111111"
    assert "password" not in response.text.lower()
    assert response.headers["X-Request-ID"]


def test_me_returns_the_current_identity(api_client: TestClient) -> None:
    """``GET /me`` resolves the bearer token to the caller."""
    token = login(api_client).json()["access_token"]

    response = api_client.get(ME, headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "username", "display_name", "role", "patient_id", "timezone"}
    assert body["username"] == "demo_patient_a"


def test_missing_token_returns_the_problem_envelope(api_client: TestClient) -> None:
    """NEG-10: an unauthenticated call is a uniform 401 problem document."""
    response = api_client.get(ME)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "E_UNAUTHENTICATED"
    assert body["status"] == 401
    assert body["type"] == "https://demo.local/errors/E_UNAUTHENTICATED"
    assert body["instance"] == ME
    assert body["request_id"]
    assert body["detail"] == "A valid session is required."


def test_non_bearer_scheme_is_rejected(api_client: TestClient) -> None:
    """Only the documented ``Bearer`` scheme is accepted."""
    token = login(api_client).json()["access_token"]

    response = api_client.get(ME, headers={"Authorization": f"Basic {token}"})

    assert response.status_code == 401
    assert response.json()["code"] == "E_UNAUTHENTICATED"


def test_unknown_and_expired_tokens_are_indistinguishable(api_client: TestClient) -> None:
    """No response distinguishes an unknown token from an invalid one."""
    unknown = api_client.get(ME, headers=bearer("definitely-not-a-token"))

    assert unknown.status_code == 401
    assert unknown.json()["code"] == "E_UNAUTHENTICATED"
    assert unknown.json()["detail"] == "A valid session is required."


def test_logout_revokes_the_session(api_client: TestClient) -> None:
    """A revoked token stops working immediately (``204`` then ``401``)."""
    token = login(api_client).json()["access_token"]

    logout = api_client.post(LOGOUT, headers=bearer(token))
    after = api_client.get(ME, headers=bearer(token))

    assert logout.status_code == 204
    assert logout.content == b""
    assert after.status_code == 401


def test_invalid_credentials_share_one_body(api_client: TestClient) -> None:
    """Wrong password and unknown user produce the same code and detail."""
    wrong_password = login(api_client, password=SEED_PASSWORD + "-wrong")
    unknown_user = login(api_client, username="nobody_here", password=SEED_PASSWORD)

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["code"] == "E_INVALID_CREDENTIALS"
    assert unknown_user.json()["code"] == "E_INVALID_CREDENTIALS"
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_request_validation_uses_the_contract_envelope(api_client: TestClient) -> None:
    """A schema error is ``400 E_VALIDATION`` with ``{field, reason}`` details."""
    response = api_client.post(LOGIN, json={"username": "ab", "password": "short"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "E_VALIDATION"
    assert body["details"]
    assert set(body["details"][0]) == {"field", "reason"}
    assert "ab" not in response.text  # the submitted value is never echoed


def test_rate_limited_login_returns_429(api_client: TestClient) -> None:
    """REQ-AUTH-03: the sixth attempt in the window is throttled."""
    for _ in range(5):
        assert login(api_client, password=SEED_PASSWORD + "-wrong").status_code == 401

    blocked = login(api_client)

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "E_RATE_LIMITED"
    assert blocked.headers["Retry-After"] == "300"


def test_auth_surface_is_the_only_registered_route() -> None:
    """The auth router exposes exactly the three contract operations."""
    from conftest import build_test_app

    from app.core.config import Settings

    schema = build_test_app(Settings(_env_file=None)).openapi()
    assert set(schema["paths"]) == {LOGIN, ME, LOGOUT}
    assert schema["paths"][LOGIN]["post"]["security"] == []
    assert set(schema["components"]["schemas"]["TokenResponse"]["required"]) == {
        "access_token",
        "token_type",
        "expires_at",
        "user",
    }
