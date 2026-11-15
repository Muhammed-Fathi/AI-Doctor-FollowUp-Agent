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

#: Modules that would indicate a later-phase or forbidden capability in this code.
#:
#: ``pypdf`` and ``pytesseract`` left this list in P3: OCR and PDF text extraction
#: are now authorized deliverables. They did **not** become freely importable —
#: ``OCR_IMPORTS`` below confines them to the one extraction package, so a
#: notification service or a workflow node still cannot pull in an OCR engine.
FORBIDDEN_IMPORTS = (
    "langgraph",
    "ollama",
    "smtplib",
    "sendgrid",
    "twilio",
    "requests",
    "httpx",
    "aiohttp",
)

#: OCR/PDF libraries, importable only from the authorized extraction package.
OCR_IMPORTS = ("pypdf", "pypdfium2", "pytesseract", "PIL")

#: The single package allowed to import :data:`OCR_IMPORTS` (owner authorization,
#: Phase 3). Path-scoped rather than name-scoped: any file outside this directory
#: that imports an OCR library fails, whatever it is called.
OCR_ALLOWED_PREFIX = BACKEND_APP / "services" / "documents"


def _python_sources() -> list[Path]:
    return sorted(path for path in BACKEND_APP.rglob("*.py") if "__pycache__" not in path.parts)


def test_backend_has_no_forbidden_imports() -> None:
    """No agent, model-runtime or egress library is imported anywhere in the app.

    OCR/PDF libraries are checked separately by
    :func:`test_ocr_imports_are_confined_to_the_authorized_extraction_package`.
    """
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for module in FORBIDDEN_IMPORTS:
            for pattern in (f"import {module}", f"from {module}"):
                if pattern in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} -> {module}")
    assert offenders == []


def test_ocr_imports_are_confined_to_the_authorized_extraction_package() -> None:
    """Only ``backend/app/services/documents`` may import an OCR/PDF library.

    This replaces a blanket ban with a narrower, still-exact rule: the capability
    is authorized for Phase 3 extraction, and nowhere else. A new consumer outside
    the package — a route, a schema, a future workflow node — fails here.
    """
    offenders: list[str] = []
    for path in _python_sources():
        if OCR_ALLOWED_PREFIX in path.parents:
            continue
        text = path.read_text(encoding="utf-8")
        for module in OCR_IMPORTS:
            for pattern in (f"import {module}", f"from {module}"):
                if pattern in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} -> {module}")

    assert offenders == []


def test_ocr_libraries_are_declared_and_not_optional() -> None:
    """The extraction dependencies are real project dependencies, not imports of chance.

    Pinning them in ``pyproject.toml`` is what makes ``E_DEPENDENCY_MISSING`` a
    statement about the *engine*, not about a missing Python package.
    """
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    # Exact pins only: a floating range would make the install non-reproducible
    # and the lockfiles unverifiable.
    for declaration in (
        "python-multipart==0.0.33",
        "pypdf==7.1.0",
        "pypdfium2==5.15.2",
        "pytesseract==0.3.13",
        "pillow==13.0.0",
    ):
        assert f'"{declaration}"' in pyproject, f"{declaration} is not pinned"


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


#: The complete P3 document surface.
P3_ROUTES = {
    "/api/v1/documents/upload",
    "/api/v1/documents/{document_id}",
    "/api/v1/documents/{document_id}/extraction",
    "/api/v1/documents/{document_id}/verify",
    "/api/v1/documents/{document_id}/file",
}

#: The complete P2 surface. Anything outside this set is out of scope, and the
#: assertion below is an equality check for exactly that reason.
P2_ROUTES = {
    "/api/v1/auth/login",
    "/api/v1/auth/me",
    "/api/v1/auth/logout",
    "/api/v1/doctor/patients",
    "/api/v1/doctor/patients/{patient_id}",
    "/api/v1/doctor/patients/{patient_id}/timeline",
    "/api/v1/doctor/patients/{patient_id}/observations",
    "/api/v1/patient/check-ins",
    "/api/v1/demo/reset",
}


def test_backend_exposes_only_health_version_and_allowlisted_p2_p3_routes() -> None:
    """The app must not register speculative P4+ routes or a demo seed endpoint.

    P1's two paths are still required, and the P2 and P3 additions are enumerated:
    a third-party route slipping in (workflows, review items, tasks, summaries)
    fails this guard.
    """
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])

    assert {"/health", "/version"} <= paths
    assert paths == {"/health", "/version"} | P2_ROUTES | P3_ROUTES

    # Later-phase surfaces are named explicitly as well as excluded by equality.
    for forbidden in (
        "/api/v1/workflows/follow-up",
        "/api/v1/review-items",
        "/api/v1/tasks",
        "/api/v1/notifications",
        "/api/v1/summaries",
        "/api/v1/demo/seed",
        "/api/v1/demo/status",
    ):
        assert forbidden not in paths
    assert "/api/v1/demo/seed" not in paths
    assert "/api/v1/demo/status" not in paths

    # "document" left this keyword list in P3 because document routes are the
    # phase's deliverable. The remaining words are later-phase surfaces, so the
    # check stays as a substring guard over the whole path set.
    assert not any(
        keyword in path
        for path in paths
        for keyword in ("workflow", "review", "task", "notification", "summary")
    )


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
