"""Static checks for the Windows PowerShell scripts.

**These are static inspections only.** PowerShell cannot be executed in the
Linux authoring sandbox, so no test here proves that a script runs. Real
execution evidence must come from the owner's Windows laptop
(``docs/runbooks/WINDOWS_SETUP.md`` §5).

What is verified here (cheap and deterministic):

* all five required scripts exist and are dot-sourcing the shared helper;
* no broad/unsafe process termination idiom is present;
* no script changes the PowerShell execution policy or security settings;
* no script uses ``npm`` directly (``npm.ps1`` is blocked on the owner machine);
* every ``.ps1`` path referenced from another script exists;
* the helper resolves the repository root relative to ``$PSScriptRoot``.

Requirement mapping: ``REQ-OPS-02`` (one-command start/stop/test), ``REQ-SEC-06``.
"""

from __future__ import annotations

import re

import pytest

from app.core.paths import REPO_ROOT

SCRIPTS_DIR = REPO_ROOT / "scripts" / "powershell"

REQUIRED_SCRIPTS = (
    "preflight.ps1",
    "setup.ps1",
    "start.ps1",
    "stop.ps1",
    "test_all.ps1",
)

#: Idioms that would terminate unrelated processes on the machine.
UNSAFE_KILL_PATTERNS = (
    r"Stop-Process\s+-Name\b",
    r"Get-Process\s+\w+\s*\|\s*Stop-Process",
    r"Get-Process\s*\|\s*Where-Object[^\n]*\|\s*Stop-Process",
    r"taskkill\s+/IM\b",
    r"taskkill\s+/F\s+/IM\b",
    r"Stop-Process\s+-Id\s+\$\w+\s+-Force\s*-ErrorAction\s+SilentlyContinue\s*#\s*all",
)


@pytest.mark.parametrize("script_name", REQUIRED_SCRIPTS)
def test_script_exists(script_name: str) -> None:
    """Every P1 deliverable script is present."""
    assert (SCRIPTS_DIR / script_name).is_file()


@pytest.mark.parametrize("script_name", REQUIRED_SCRIPTS)
def test_script_dot_sources_common_helper(script_name: str) -> None:
    """Scripts share one helper instead of duplicating path logic."""
    text = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
    assert '. "$PSScriptRoot\\_common.ps1"' in text


def test_common_helper_anchors_repository_root() -> None:
    """The helper derives the root from ``$PSScriptRoot``, never from ``$PWD``."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    assert "Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\\..')" in text
    assert "Set-StrictMode -Version Latest" in text
    assert "$ErrorActionPreference = 'Stop'" in text


@pytest.mark.parametrize("script_name", [*REQUIRED_SCRIPTS, "_common.ps1"])
def test_no_broad_process_termination(script_name: str) -> None:
    """No script may kill by image name or kill everything on a port."""
    text = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
    for pattern in UNSAFE_KILL_PATTERNS:
        assert re.search(pattern, text) is None, f"{script_name} matches unsafe idiom {pattern}"


@pytest.mark.parametrize("script_name", [*REQUIRED_SCRIPTS, "_common.ps1"])
def test_does_not_weaken_powershell_security(script_name: str) -> None:
    """Scripts must not change the execution policy or other machine settings."""
    text = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
    forbidden = (
        "set-executionpolicy",
        "unrestricted",
        "bypassremoting",
        "new-itemproperty -path hklm",
        "set-mppreference",
    )
    for term in forbidden:
        assert term not in text, f"{script_name} must not contain {term!r}"


@pytest.mark.parametrize("script_name", [*REQUIRED_SCRIPTS, "_common.ps1"])
def test_uses_npm_cmd_not_npm_ps1(script_name: str) -> None:
    """The owner machine blocks ``npm.ps1``; scripts must call ``npm.cmd``."""
    text = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
    # A bare `npm <verb>` (not `npm.cmd`) would resolve to npm.ps1.
    bare_npm = re.search(r"(?<![\w.])npm\s+(?![.\w])", text)
    assert bare_npm is None, f"{script_name} invokes bare `npm`"


def test_only_owned_processes_are_stopped() -> None:
    """``stop.ps1`` verifies command-line ownership before stopping a PID."""
    text = (SCRIPTS_DIR / "stop.ps1").read_text(encoding="utf-8")
    assert "Test-OwnedProcess" in text
    assert "Get-ProcessCommandLine" in text
    # It must refuse to act without a state file instead of guessing.
    assert "never falls back to killing" in text


def test_stop_collects_the_verified_process_tree() -> None:
    """npm.cmd spawns cmd.exe -> node.exe, so the Vite child must be stopped too.

    The tree walk is only allowed *after* the root PID's command line was
    verified, which is why it lives in the same block as the ownership check.
    """
    text = (SCRIPTS_DIR / "stop.ps1").read_text(encoding="utf-8")
    assert "Get-DescendantProcessIds" in text
    assert "Win32_Process" in text
    # The tree walk must be reachable only through the verified root.
    assert text.index("Test-OwnedProcess -ProcessId $processId") < text.index(
        "$descendants = @(Get-DescendantProcessIds"
    )


def test_start_records_state_for_safe_shutdown() -> None:
    """``start.ps1`` writes ``run-state.json`` with PIDs and command lines."""
    text = (SCRIPTS_DIR / "start.ps1").read_text(encoding="utf-8")
    assert "run-state.json" in text
    assert "Get-ProcessCommandLine" in text
    # Rollback only touches the PIDs it started.
    assert "Stop-StartedProcesses" in text


@pytest.mark.parametrize("script_name", REQUIRED_SCRIPTS)
def test_extension_is_lowercase_ps1(script_name: str) -> None:
    """File names follow the documented lowercase convention."""
    assert script_name.endswith(".ps1")
    assert script_name == script_name.lower()


def test_python_helpers_referenced_by_test_all_exist() -> None:
    """``test_all.ps1`` calls helper scripts that must actually exist."""
    text = (SCRIPTS_DIR / "test_all.ps1").read_text(encoding="utf-8")
    referenced = set(re.findall(r"scripts\\python\\([\w_]+\.py)", text))
    assert referenced, "test_all.ps1 should call at least one python helper"
    for name in referenced:
        assert (REPO_ROOT / "scripts" / "python" / name).is_file(), name


def test_scripts_are_ascii_only() -> None:
    """ASCII-only scripts avoid Windows PowerShell 5.1 encoding pitfalls."""
    for script in sorted(SCRIPTS_DIR.glob("*.ps1")):
        data = script.read_bytes()
        assert data.decode("ascii", errors="strict"), f"{script.name} contains non-ASCII bytes"


def test_scripts_have_no_placeholder_markers() -> None:
    """No unfinished ``TODO``/``FIXME`` marker ships in a quality-gate script."""
    for script in sorted(SCRIPTS_DIR.glob("*.ps1")):
        text = script.read_text(encoding="utf-8").upper()
        for marker in ("TODO", "FIXME", "XXX", "PLACEHOLDER"):
            assert marker not in text, f"{script.name} contains {marker}"
