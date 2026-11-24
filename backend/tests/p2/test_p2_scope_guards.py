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
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.paths import REPO_ROOT, SYNTHETIC_DATA_DIR
from app.db.base import Base
from app.db.session import create_db_engine
from app.schemas.auth import UserRead
from app.schemas.observation import ObservationRead

BACKEND_APP = REPO_ROOT / "backend" / "app"

#: Tables P2 owns. They must all still exist: P3 may not drop or rename one.
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

#: The six tables P3 owns (five from ``0003`` + ``document_page_text`` from Stage 1 ``0005``).
P3_TABLES = {
    "document",
    "document_page_text",
    "extraction_attempt",
    "extracted_fact",
    "fact_verification",
    "verification_issue",
}

#: P5-F0 tables approved through owner-ratified CH-01. These and only these
#: are allowed while review items, agents and task tables are still forbidden.
P5_F0_TABLES = {
    "workflow_run",
    "run_selected_document",
    "run_selected_observation",
    "run_source_omission",
}

#: Exactly the two F1 tables authorized by owner-ratified PR #32.
P5_F1_TABLES = {"run_gate_evaluation", "run_gate_blocker"}

#: Exactly the three WITHOUT ROWID P4-RB3 tables authorized at 0008 (PR #42 / PR #43).
P4_RB3_TABLES = {"review_item", "evidence_link", "review_evaluation"}

#: Pre-0008 forbidden later-phase tables (RB3 tables remain forbidden at 0001..0007;
#: all remaining summary/approval/graph/task tables stay forbidden at 0008 too).
P4_PLUS_TABLES = {
    "review_item",
    "evidence_link",
    "review_evaluation",
    "summary_draft",
    "summary_claim",
    "approval_decision",
    "follow_up_task",
    "in_app_notification",
    "node_event",
}
POST_RB3_FUTURE_TABLES = P4_PLUS_TABLES - P4_RB3_TABLES

#: Imports that would indicate agents, a model or network egress. These stay
#: forbidden in **every** module, in every phase.
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

#: Document-parsing dependencies. Owner decision D-05: they are permitted
#: **only** inside the explicitly authorized P3 extraction modules, never
#: globally. Adding one anywhere else fails this guard.
OCR_IMPORTS = ("pypdf", "pytesseract", "pypdfium2", "PIL")

#: The only package prefix allowed to import an OCR/PDF dependency.
OCR_ALLOWED_PREFIX = BACKEND_APP / "services" / "documents"

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


def test_p2_tables_still_exist_and_no_later_phase_table_appears() -> None:
    """Preserve P2/P3 exactly, permit RB3 only at 0008, and forbid all other future tables.

    All three RB3 tables remain forbidden at pre-0008 revisions (verified at
    ``0007_p5_run_gate``), and all remaining summary/approval/graph/task tables
    stay forbidden at ``0008``.
    """
    tables = set(Base.metadata.tables)

    assert tables >= P2_TABLES
    assert tables >= P3_TABLES
    assert tables.isdisjoint(POST_RB3_FUTURE_TABLES)
    assert tables == P2_TABLES | P3_TABLES | P5_F0_TABLES | P5_F1_TABLES | P4_RB3_TABLES

    with tempfile.TemporaryDirectory() as tmpdir:
        db_url = f"sqlite:///{(Path(tmpdir) / 'scope_0007.db').as_posix()}"
        cfg = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", db_url)
        cfg.attributes["configure_logger"] = False
        command.upgrade(cfg, "0007_p5_run_gate")
        eng = create_db_engine(db_url)
        try:
            tables_0007 = set(inspect(eng).get_table_names())
        finally:
            eng.dispose()
    assert tables_0007.isdisjoint(P4_PLUS_TABLES)


#: Owner decision D-14 (PR #47 comment 7122838674): the *only* authorized P5-S0
#: application modules, as paths relative to ``backend/app/agents``. Every other
#: path under ``agents`` - and the whole ``llm`` package - stays forbidden. This
#: is an exact-path allowlist, never a directory-wide exemption.
AUTHORIZED_AGENT_MODULE_PATHS = ("__init__.py", "state.py")


def _stray_agent_modules(app_root: Path) -> list[str]:
    """Every file under ``app_root/agents`` that the D-14 allowlist does not name.

    Relative paths are compared as canonical POSIX-style paths, so a nested
    package (``agents/graph/nodes.py``) is rejected exactly like a stray
    top-level module *and* the comparison does not depend on the platform's
    path separator (a Windows run must not report ``agents\\state.py``).
    """
    agents_root = app_root / "agents"
    if not agents_root.exists():
        return []
    return sorted(
        path.relative_to(app_root).as_posix()
        for path in agents_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.relative_to(agents_root).as_posix() not in AUTHORIZED_AGENT_MODULE_PATHS
    )


def test_no_later_phase_module_exists() -> None:
    """No P4+ review/workflow/task/agent module is created.

    ``documents.py`` and ``extraction.py`` were on this list before P3 existed.
    They are now authorized P3 routes/modules, so they are permitted **only**
    under their exact P3 paths; every later-phase module name stays forbidden.
    """
    forbidden = {
        "workflows.py",
        "reviews.py",
        "tasks.py",
        "review_rules.py",
        "comparisons.py",
        "orchestrator.py",
        "summary.py",
        "notifications.py",
    }
    present = {path.name for path in app_sources()}
    assert forbidden.isdisjoint(present)

    # D-14: the ``agents`` package may hold only the two authorized S0 modules.
    stray = _stray_agent_modules(BACKEND_APP)
    assert stray == [], f"unauthorized module(s) under agents: {stray}"
    assert not (BACKEND_APP / "llm").exists()

    # ``extraction.py`` may exist only as the P3 service module, never as a
    # top-level router or an agent-side module.
    extraction_modules = [path for path in app_sources() if path.name == "extraction.py"]
    assert all(
        path == BACKEND_APP / "services" / "documents" / "text_extraction.py"
        for path in extraction_modules
    )


def test_d14_allowlist_rejects_every_other_agents_module(tmp_path: Path) -> None:
    """Rejection proof for the D-14 allowlist (owner decision, PR #47).

    The allowlist admits exactly ``__init__.py`` and ``state.py``; a graph, an
    orchestrator, a tool adapter, a checkpoint module, an LLM module and any
    nested sub-package are all reported as violations.
    """
    app_root = tmp_path / "app"
    (app_root / "agents").mkdir(parents=True)
    assert _stray_agent_modules(app_root) == []
    (app_root / "agents" / "__init__.py").write_text("", encoding="utf-8")
    (app_root / "agents" / "state.py").write_text("", encoding="utf-8")
    assert _stray_agent_modules(app_root) == []

    for name in ("orchestrator.py", "tool_adapter.py", "checkpoint.py", "llm.py"):
        stray_path = app_root / "agents" / name
        stray_path.write_text("", encoding="utf-8")
        assert _stray_agent_modules(app_root) == [f"agents/{name}"], name
        stray_path.unlink()

    nested = app_root / "agents" / "graph" / "nodes.py"
    nested.parent.mkdir()
    nested.write_text("", encoding="utf-8")
    assert _stray_agent_modules(app_root) == ["agents/graph/nodes.py"]
    # The reported path is canonical and POSIX-style on every platform, so this
    # assertion compares no platform-dependent separator.
    assert all("/" in item and "\\" not in item for item in _stray_agent_modules(app_root))


def test_no_forbidden_import_appears_in_application_code() -> None:
    """No model, agent or egress library is imported anywhere.

    These stay forbidden globally in every phase; P3 did not relax this list.
    """
    offenders: list[str] = []
    for path in app_sources():
        text = path.read_text(encoding="utf-8")
        for module in FORBIDDEN_IMPORTS:
            if f"import {module}" in text or f"from {module}" in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} -> {module}")

    assert offenders == []


def test_ocr_imports_are_confined_to_the_authorized_extraction_package() -> None:
    """PDF/OCR libraries may be imported only under ``services/documents``.

    Owner decision D-05: the OCR allowlist is path-scoped, not global. A route,
    schema, model or core module that imports ``pypdf``/``pytesseract`` fails
    here even though those packages are legitimate in the extraction services.
    """
    offenders: list[str] = []
    for path in app_sources():
        if OCR_ALLOWED_PREFIX in path.parents:
            continue
        text = path.read_text(encoding="utf-8")
        for module in OCR_IMPORTS:
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
