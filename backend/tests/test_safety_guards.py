"""P1 safety guards: scope containment, artefact hygiene and honest health.

These tests encode what the P1 foundation must **not** do. They are cheap,
deterministic and offline, and they fail loudly if a future phase smuggles a
forbidden capability in through the foundation files.

Requirement mapping:

* ``REQ-SEC-03`` — no outbound-messaging capability.
* ``REQ-SEC-05`` — educational/synthetic notice present.
* ``REQ-SEC-06`` — no secrets, databases or runtime artefacts tracked.
* ``REQ-OPS-02`` — health/version behaviour.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.core.paths import REPO_ROOT
from app.core.version import DEMO_NOTICE

BACKEND_APP = REPO_ROOT / "backend" / "app"

#: Modules that would indicate a Phase-2+ or forbidden capability in P1 code.
FORBIDDEN_IMPORTS = (
    "langgraph",
    "ollama",
    "pytesseract",
    "pypdf",
    "smtplib",
    "sendgrid",
    "twilio",
    "requests",
    "httpx",
    "aiohttp",
)


def _python_sources() -> list[Path]:
    return sorted(path for path in BACKEND_APP.rglob("*.py") if "__pycache__" not in path.parts)


def test_p1_backend_has_no_forbidden_imports() -> None:
    """P1 imports only FastAPI/Pydantic/SQLAlchemy/Alembic — no agent, OCR or egress."""
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for module in FORBIDDEN_IMPORTS:
            for pattern in (f"import {module}", f"from {module}"):
                if pattern in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} -> {module}")
    assert offenders == []


def test_p1_implements_no_clinical_capability() -> None:
    """No diagnostic/treatment vocabulary is implemented in P1 code."""
    forbidden_terms = (
        "diagnos",
        "prescrib",
        "dosage",
        "differential",
        "triage_score",
        "risk_score",
        "treatment_plan",
        "send_sms",
        "send_email",
        "whatsapp",
    )
    hits: list[str] = []
    for path in _python_sources():
        lowered = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            if term in lowered:
                hits.append(f"{path.relative_to(REPO_ROOT)} -> {term}")
    assert hits == []


def test_backend_exposes_only_health_and_version_routes() -> None:
    """The P1 app must not register speculative patient/auth/workflow routes."""
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])
    assert paths == {"/health", "/version"}


def test_educational_notice_constant_is_exact() -> None:
    """``REQ-SEC-05`` wording is fixed and must not drift."""
    assert DEMO_NOTICE == "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"


def test_no_runtime_artefacts_are_tracked_by_git() -> None:
    """``REQ-SEC-06``: no ``.env``, SQLite file, vhost or node_modules in the index."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - git absent
        pytest.skip("git is not available in this environment")

    if completed.returncode != 0:  # pragma: no cover - not a git checkout
        pytest.skip("not a git working tree")

    tracked = [item for item in completed.stdout.split("\0") if item]
    offenders = [
        path
        for path in tracked
        if path.endswith((".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log"))
        or path == ".env"
        or path.startswith(("node_modules/", ".venv/", "data/runtime/"))
    ]
    assert offenders == []


def test_env_example_is_tracked_and_contains_no_secret_values() -> None:
    """``.env.example`` documents keys only; it never carries a real credential."""
    example = REPO_ROOT / ".env.example"
    assert example.is_file()

    for line in example.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if any(
            word in key.lower() for word in ("secret", "token", "password", "key", "credential")
        ):
            assert value.strip() == "", f"{key} must have an empty placeholder value"


def test_health_does_not_claim_animal_or_model_state(client) -> None:
    """Ollama/Tesseract are ``not_configured`` until P3/P5 actually wire them."""
    payload = client.get("/health").json()
    assert payload["ollama"] == "not_configured"
    assert payload["tesseract"] == "not_configured"
