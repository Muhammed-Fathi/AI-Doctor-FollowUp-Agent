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


# --- P1-R06: Invoke-Native must return ONLY the numeric exit code -------------
# Regression guard for the Windows defect where a native command's stdout was
# emitted alongside the exit code, so `$code = Invoke-Native ...` produced a
# multi-element array and every successful gate was reported as FAIL.
# Executable proof lives in ``scripts/powershell/tests/invoke_native.tests.ps1``.


def test_invoke_native_discards_native_output_from_the_pipeline() -> None:
    """Native stdout must be piped to ``Out-Host``, never left in the pipeline."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    function = text.split("function Invoke-Native", 1)[1].split("function Get-NativeOutput", 1)[0]
    assert "| Out-Host" in function, "Invoke-Native must route native stdout to Out-Host"
    # The raw `& $FilePath @Arguments` must never appear unbounded in the wrapper.
    for line in function.splitlines():
        stripped = line.strip()
        if stripped.startswith("& $FilePath @Arguments"):
            assert stripped.endswith("| Out-Host"), f"unpiped native call: {stripped!r}"


def test_invoke_native_returns_a_scalar_and_resets_last_exit_code() -> None:
    """The wrapper initialises its exit code so a stale value cannot leak."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    function = text.split("function Invoke-Native", 1)[1].split("function Get-NativeOutput", 1)[0]
    assert "$code = 0" in function
    assert "return $code" in function
    # Broadcasting an array would reintroduce the multi-value pipeline bug.
    assert "return ," not in function and "return @(" not in function


def test_invoke_native_does_not_merge_stderr_into_the_pipeline() -> None:
    """``2>&1`` under $ErrorActionPreference='Stop' can break PowerShell 5.1."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    function = text.split("function Invoke-Native", 1)[1].split("function Get-NativeOutput", 1)[0]
    assert "2>&1" not in function


def test_get_native_output_still_captures_stdout() -> None:
    """Capture semantics of ``Get-NativeOutput`` stay intact (it returns an object)."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    function = text.split("function Get-NativeOutput", 1)[1].split(
        "function ConvertTo-QuotedArgument"
    )[0]
    assert "@(& $FilePath @Arguments 2>&1)" in function
    assert "ExitCode = $code" in function
    assert "Output =" in function


def test_test_all_validates_the_exit_code_type() -> None:
    """``test_all.ps1`` refuses to classify a gate from a non-numeric value."""
    text = (SCRIPTS_DIR / "test_all.ps1").read_text(encoding="utf-8")
    assert "function Get-ExitCodeValue" in text
    assert "-is [int]" in text
    # Every gate must go through the tripwire: Invoke-Gate (7 gates) plus the
    # three gates that call Invoke-Native directly (alembic, openapi, scan).
    gate_function = text.split("function Invoke-Gate", 1)[1].split("# --- 1. Ruff", 1)[0]
    assert "Get-ExitCodeValue -Gate" in gate_function
    assert text.count("Get-ExitCodeValue -Gate") >= 4


def test_executable_powershell_regression_script_covers_the_three_cases() -> None:
    """The Windows-runnable test covers output, silence, and non-zero failure."""
    path = SCRIPTS_DIR / "tests" / "invoke_native.tests.ps1"
    assert path.is_file(), "missing executable regression script for Invoke-Native"
    text = path.read_text(encoding="utf-8")
    for case in (
        "successful command that prints output",
        "silent successful command",
        "failing command",
    ):
        assert case in text, f"regression script does not cover: {case}"


# --- P1-R03: paths containing spaces ------------------------------------------


def test_start_quotes_every_start_process_argument() -> None:
    """``-ArgumentList`` must receive a quoted command-line string (P1-R03)."""
    text = (SCRIPTS_DIR / "start.ps1").read_text(encoding="utf-8")
    start_process_calls = text.count("Start-Process -FilePath")
    assert start_process_calls >= 2
    # Each Start-Process that launches our own binaries quotes its arguments.
    for block in text.split("Start-Process -FilePath")[1:]:
        if "http://" in block.split("-ArgumentList")[0]:
            continue  # browser launcher, no -ArgumentList
        assert "-ArgumentList (ConvertTo-CommandLine" in block, block.splitlines()[0]


def test_common_exposes_command_line_quoting_helpers() -> None:
    """A single quoting helper is shared instead of ad-hoc string building."""
    text = (SCRIPTS_DIR / "_common.ps1").read_text(encoding="utf-8")
    assert "function ConvertTo-QuotedArgument" in text
    assert "function ConvertTo-CommandLine" in text
    # Arguments without whitespace stay unquoted for readable logs.
    assert "'[\\s\"]'" in text or "-notmatch '[\\s\"]'" in text


# --- P1-R05: frontend identity when the cmd.exe wrapper omits the repo path ---


def test_stop_accepts_npm_wrapper_identity_without_repo_path() -> None:
    """npm.cmd -> cmd.exe may not carry the repository path (P1-R05)."""
    text = (SCRIPTS_DIR / "stop.ps1").read_text(encoding="utf-8")
    function = text.split("function Test-OwnedProcess", 1)[1].split(
        "function Get-DescendantProcessIds"
    )[0]
    # Frontend identity no longer requires the repository path alone.
    assert "$referencesRepo" in function
    assert "run\\s+dev" in function
    assert "strictPort" in function
    # Backend identity stays strict.
    assert "$isOwned = $belongsToRepo -and $looksLikeBackend" in function
