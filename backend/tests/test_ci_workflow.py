"""Static checks for the GitHub Actions workflow and dependency locks.

Executed here: YAML syntax, structure, forbidden-service absence and lock-file
consistency. **Not executed here:** any actual GitHub Actions run — that can
only be observed on GitHub after the branch is pushed (see the P1 report).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core.paths import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    """Parsed CI workflow definition."""
    assert WORKFLOW.is_file(), "CI workflow is missing"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_is_valid_yaml_with_jobs(workflow: dict[str, Any]) -> None:
    """The workflow parses and declares the two expected jobs."""
    assert set(workflow["jobs"]) == {"backend", "frontend"}


def test_workflow_triggers(workflow: dict[str, Any]) -> None:
    """Runs on pull requests to main, pushes to the phase branches, and manually."""
    # ``on`` is parsed as the boolean True by YAML 1.1 parsers such as PyYAML.
    triggers = workflow.get("on", workflow.get(True))
    assert triggers is not None
    assert triggers["pull_request"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers
    assert "main" in triggers["push"]["branches"]


def test_backend_job_pins_python_312(workflow: dict[str, Any]) -> None:
    """The backend job runs on the target interpreter, Python 3.12."""
    steps = workflow["jobs"]["backend"]["steps"]
    setup = [step for step in steps if "setup-python" in str(step.get("uses", ""))]
    assert len(setup) == 1
    assert str(setup[0]["with"]["python-version"]) == "3.12"


def test_frontend_job_pins_node_22(workflow: dict[str, Any]) -> None:
    """The frontend job runs on Node 22 (Vite 7 requires >=22.12)."""
    steps = workflow["jobs"]["frontend"]["steps"]
    setup = [step for step in steps if "setup-node" in str(step.get("uses", ""))]
    assert len(setup) == 1
    assert str(setup[0]["with"]["node-version"]) == "22"


def _executable_text(workflow: dict[str, Any]) -> str:
    """Join step names, ``uses`` and ``run`` bodies (i.e. what actually executes)."""
    fragments: list[str] = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            fragments.extend(
                str(step.get(key, "")) for key in ("name", "uses", "run", "with", "env")
            )
    return "\n".join(fragments).lower()


def test_workflow_requires_no_secrets_or_services(workflow: dict[str, Any]) -> None:
    """CI must not need a local model, GPU, OCR engine, paid API or secrets."""
    executable = _executable_text(workflow)
    for forbidden in (
        "ollama",
        "gpu",
        "cuda",
        "tesseract",
        "openai",
        "anthropic",
        "secrets.",
        "services:",
        "docker",
        "playwright install",
    ):
        assert forbidden not in executable, f"CI must not reference {forbidden!r}"
    assert "services" not in workflow["jobs"]["backend"]
    assert "services" not in workflow["jobs"]["frontend"]


def test_workflow_has_minimal_permissions(workflow: dict[str, Any]) -> None:
    """Read-only contents permission; no write scopes are granted."""
    assert workflow["permissions"] == {"contents": "read"}


def test_workflow_runs_the_quality_gates(workflow: dict[str, Any]) -> None:
    """Every mandatory P1 gate is invoked by CI."""
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "ruff check",
        "ruff format --check",
        "pytest",
        "alembic",
        "check_openapi.py",
        "scan_repository.py",
        "npm ci",
        "npm run lint",
        "npm run typecheck",
        "npm test",
        "npm run build",
    )
    for command in required:
        assert command in text, f"CI is missing gate: {command}"


def test_jobs_have_timeouts(workflow: dict[str, Any]) -> None:
    """Short jobs keep the free Actions budget intact."""
    for name, job in workflow["jobs"].items():
        assert job.get("timeout-minutes", 0) <= 20, f"{name} has no reasonable timeout"


# --- dependency locks ---------------------------------------------------------
LOCK = REPO_ROOT / "requirements" / "requirements.lock"
DEV_LOCK = REPO_ROOT / "requirements" / "requirements-dev.lock"


@pytest.mark.parametrize("lock_path", [LOCK, DEV_LOCK])
def test_lock_file_pins_versions_with_hashes(lock_path: Path) -> None:
    """Every locked requirement is an exact pin with at least one sha256 hash."""
    assert lock_path.is_file()
    text = lock_path.read_text(encoding="utf-8")

    pinned = re.findall(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", text, flags=re.MULTILINE)
    assert len(pinned) >= 15, "lock file looks truncated"

    for name, version in pinned:
        assert re.match(r"^\d+\.\d+", version), f"{name} is not pinned to a real version"

    hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", text)
    assert len(hashes) >= len(pinned), "every pinned package needs a hash"


def test_lock_files_contain_no_wildcards() -> None:
    """No ``>=`` / ``~=`` / ``*`` specifier may survive into a lock file."""
    for lock_path in (LOCK, DEV_LOCK):
        text = lock_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line or line.startswith(("#", " ", "-")):
                continue
            assert ">=" not in line and "~=" not in line and "==" in line, line


def test_runtime_lock_excludes_test_tooling() -> None:
    """The runtime lock stays free of dev-only packages."""
    text = LOCK.read_text(encoding="utf-8").lower()
    for name in ("pytest==", "ruff==", "httpx2=="):
        assert name not in text


def test_dev_lock_includes_test_tooling() -> None:
    """The dev lock is a superset used by setup.ps1 and CI."""
    text = DEV_LOCK.read_text(encoding="utf-8").lower()
    for name in ("pytest==", "ruff==", "httpx2=="):
        assert name in text


def test_pyproject_pins_match_lock_files() -> None:
    """Every exact pin in pyproject.toml appears in the corresponding lock file."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runtime_lock = LOCK.read_text(encoding="utf-8").lower()
    dev_lock = DEV_LOCK.read_text(encoding="utf-8").lower()
    combined = runtime_lock + dev_lock

    pins = re.findall(r'"([a-z0-9_.-]+)==([0-9][^"]*)"', pyproject)
    assert pins, "pyproject.toml should declare exact pins"
    for name, version in pins:
        assert f"{name}=={version}" in combined, f"{name}=={version} is not locked"

    # Runtime dependencies specifically must be present in the runtime lock.
    runtime_section = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    for name, version in re.findall(r'"([a-z0-9_.-]+)==([0-9][^"]*)"', runtime_section):
        assert f"{name}=={version}" in runtime_lock


def test_frontend_package_json_has_no_ranges() -> None:
    """Frontend dependencies use exact versions; the lock file fixes the tree."""
    import json

    package = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    for section in ("dependencies", "devDependencies"):
        for name, version in package[section].items():
            assert re.match(r"^\d+\.\d+\.\d+", version), f"{section}.{name} = {version} is a range"


def test_frontend_lockfile_exists_and_locks_root() -> None:
    """``package-lock.json`` is committed and locks the root package."""
    import json

    lock = json.loads((REPO_ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["lockfileVersion"] == 3
    root = lock["packages"][""]
    assert root["name"] == "ai-doctor-followup-frontend"
    assert "react" in root["dependencies"]
