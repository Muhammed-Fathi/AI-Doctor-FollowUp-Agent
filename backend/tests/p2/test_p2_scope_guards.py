"""Static guards: P2 must not smuggle a later phase into the codebase.

Requirement mapping: ``REQ-SEC-03`` (no outbound-messaging path),
``REQ-SEC-06`` (no committed secrets/artefacts), ``AGENTS.md`` §1 (one phase per
PR) and §3 (medical boundaries).

These tests read files; they do not exercise behaviour. They exist because the
cheapest way for a later-phase capability to appear is an innocuous-looking
import or table, and a reviewer should not have to grep for it by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.paths import REPO_ROOT, SYNTHETIC_DATA_DIR
from app.db.base import Base
from app.schemas.auth import UserRead
from app.schemas.observation import ObservationRead

BACKEND_APP = REPO_ROOT / "backend" / "app"

#: Tables this phase is allowed to create. Anything else belongs to P3+.
P2_TABLES = {
    "schema_meta",
    "user",
    "patient",
    "encounter",
    "observation",
    "session",
    "checkin_idempotency",
    "audit_event",
}

#: Imports that would indicate OCR, agents, a model or network egress.
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

#: Vocabulary that must not appear in P2 application code (``AGENTS.md`` §3).
FORBIDDEN_TERMS = (
    "diagnos",
    "prescrib",
    "dosage",
    "differential_diagnosis",
    "risk_score",
    "treatment_plan",
    "send_sms",
    "send_email",
    "whatsapp",
)


def app_sources() -> list[Path]:
    """Every Python source file under ``backend/app``."""
    return sorted(path for path in BACKEND_APP.rglob("*.py") if "__pycache__" not in path.parts)


def test_p2_adds_no_tables_owned_by_later_phases() -> None:
    """The ORM metadata contains exactly the P2 tables."""
    assert set(Base.metadata.tables) == P2_TABLES


def test_no_later_phase_module_exists() -> None:
    """No documents/workflows/reviews/tasks router or agent package is created."""
    forbidden = {
        "documents.py",
        "workflows.py",
        "reviews.py",
        "tasks.py",
        "extraction.py",
        "review_rules.py",
        "comparisons.py",
        "orchestrator.py",
    }
    present = {path.name for path in app_sources()}
    assert forbidden.isdisjoint(present)

    assert not (BACKEND_APP / "agents").exists()
    assert not (BACKEND_APP / "llm").exists()


def test_no_forbidden_import_appears_in_application_code() -> None:
    """No OCR, model, agent or egress library is imported."""
    offenders: list[str] = []
    for path in app_sources():
        text = path.read_text(encoding="utf-8")
        for module in FORBIDDEN_IMPORTS:
            if f"import {module}" in text or f"from {module}" in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} -> {module}")

    assert offenders == []


def test_no_clinical_capability_vocabulary() -> None:
    """P2 code contains no diagnostic/prescribing/messaging vocabulary."""
    hits: list[str] = []
    for path in app_sources():
        lowered = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_TERMS:
            if term in lowered:
                hits.append(f"{path.relative_to(REPO_ROOT)} -> {term}")

    assert hits == []


def test_api_models_never_expose_credential_material() -> None:
    """No response model carries a hash, a verifier a client could set, or a token table."""
    user_fields = set(UserRead.model_fields)
    observation_fields = set(ObservationRead.model_fields)

    assert user_fields == {"id", "username", "display_name", "role", "patient_id", "timezone"}
    assert "password_hash" not in user_fields
    assert "verified_by_user_id" not in observation_fields
    assert "trust_level" in observation_fields


def test_every_fixture_file_is_labelled_synthetic() -> None:
    """REQ-SEC-05: fixtures carry the notice and the disclaimer."""
    fixture_files = sorted(SYNTHETIC_DATA_DIR.glob("*.json"))

    assert fixture_files, "the synthetic fixture directory must not be empty"
    for path in fixture_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["notice"] == "SYNTHETIC DEMO DATA — NOT A REAL MEDICAL RECORD"
        assert payload["disclaimer"] == "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"


def test_fixture_patients_are_demo_prefixed() -> None:
    """``external_ref`` uses the DEMO- prefix and no real identifier appears."""
    payload = json.loads((SYNTHETIC_DATA_DIR / "patients.json").read_text(encoding="utf-8"))

    for patient in payload["patients"]:
        assert patient["external_ref"].startswith("DEMO-")
        assert "data_source" not in patient  # implied synthetic_fixture; never client-supplied
        assert patient["display_name"].startswith("Demo Patient")


def test_no_module_reads_the_wall_clock_outside_the_clock_module() -> None:
    """Timestamps flow through ``app.core.clock`` so tests can inject a clock."""
    offenders: list[str] = []
    for path in app_sources():
        if path.name in {"clock.py", "version.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "datetime.now(" in text or "utcnow(" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


@pytest.mark.parametrize("path", sorted(BACKEND_APP.rglob("*.py")))
def test_application_modules_are_typed(path: Path) -> None:
    """Every P2 module opts into ``from __future__ import annotations``."""
    text = path.read_text(encoding="utf-8")
    assert "from __future__ import annotations" in text or path.name == "__init__.py"
