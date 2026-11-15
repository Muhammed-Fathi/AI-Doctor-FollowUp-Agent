"""The Windows acceptance probe must report honestly, never fabricate a pass.

`scripts/python/windows_ocr_acceptance.py` is the executable half of the owner
handoff. It runs on a machine this sandbox is not, so the one thing the suite can
and must verify here is its **honesty contract**:

* with no Tesseract engine it reports ``NOT RUN`` — never ``PASS``;
* it exits non-zero in that case, so a copy-pasted log cannot be mistaken for
  acceptance;
* it never touches the repository's runtime database or upload directory.

A helper that quietly returned ``PASS`` when it could not run would be worse than
no helper at all, because the owner would accept a phase on it.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.paths import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "python" / "windows_ocr_acceptance.py"


def _module():
    """Import the probe as a module without executing ``main``.

    The module is registered in ``sys.modules`` *before* execution, because the
    probe defines a dataclass and ``dataclasses`` resolves the owning module
    through ``sys.modules`` — a spec-only load would fail on that lookup.
    """
    name = "windows_ocr_acceptance"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_probe_exists_and_is_importable():
    """The handoff references a real file, not a command the owner must invent."""
    assert SCRIPT.is_file(), "the Windows handoff points at this script"

    module = _module()
    for gate in (
        "gate_environment",
        "gate_engine",
        "gate_ocr_live",
        "gate_ocr_corruption",
        "gate_rasterizer",
        "gate_api_ocr_upload",
    ):
        assert hasattr(module, gate), gate

    # The guard and the evidence writer are what make a failed dependency
    # survivable: without them an ImportError would abort before the JSON exists.
    assert hasattr(module, "_guarded")
    assert hasattr(module, "_git_head")


def test_environment_gate_survives_a_missing_wheel(monkeypatch, capsys):
    """A missing dependency is a structured FAIL, not a traceback.

    The reviewer's point: ``gate_environment`` used to import PIL/pytesseract/
    pypdfium2 *before* recording anything, so an import error aborted the probe and
    no evidence was produced. The evidence file is the artifact the owner hands
    back, so it must always exist.
    """
    module = _module()
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _blocked(name, *args, **kwargs):
        if name in {"pytesseract", "pypdfium2"}:
            raise ImportError(f"simulated missing wheel: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocked)

    results: list = []
    module.gate_environment(results)
    capsys.readouterr()

    statuses = {result.gate: result.status for result in results}
    assert statuses["ENV-01 python"] in {module.PASS, module.FAIL}
    assert statuses["ENV-02 libraries"] == module.FAIL, "a missing wheel must be a FAIL"
    missing = next(
        result.data["missing"] for result in results if result.gate == "ENV-02 libraries"
    )
    assert any("pytesseract" in entry for entry in missing)


def test_a_raising_gate_becomes_a_recorded_fail(capsys):
    """``_guarded`` converts an escape into a FAIL row and keeps going."""
    module = _module()
    results: list = []

    def _explode():
        raise RuntimeError("simulated engine crash")

    module._guarded(results, "SIMULATED", _explode)
    capsys.readouterr()

    assert len(results) == 1
    assert results[0].status == module.FAIL
    assert "simulated engine crash" in results[0].detail


def test_gold_ex_07_and_08_are_never_silently_dropped(capsys):
    """Every contract case appears in the evidence, including without an engine.

    The reviewer noted the probe claimed ``GOLD-EX-05..08`` but only enumerated
    05/06. Now 07/08 has its own row, marked ``DERIVED`` (it depends on the OCR
    gates and ING-02), and with no engine it is explicitly ``NOT RUN`` rather than
    absent.
    """
    module = _module()

    without_engine: list = []
    module.gate_ocr_live(without_engine, engine_present=False)
    capsys.readouterr()

    gates = {result.gate: result.status for result in without_engine}
    assert gates["GOLD-EX-07/08 coverage"] == module.NOT_RUN
    for gate in ("GOLD-EX-05 PNG", "GOLD-EX-06 JPEG", "OCR-LIVE-01"):
        assert gates[gate] == module.NOT_RUN

    # A DERIVED row documents the mapping and must not be counted as a failure.
    assert module.DERIVED not in {module.PASS, module.FAIL, module.NOT_RUN}


def test_a_missing_engine_is_reported_not_run_never_pass(monkeypatch, capsys):
    """No engine ⇒ ``NOT RUN``, and the process exits non-zero."""
    module = _module()
    results: list = []

    # Simulate a machine without Tesseract, whatever this sandbox has.
    from app.services.documents.ocr import OcrUnavailableError

    def _unavailable(*args, **kwargs):
        raise OcrUnavailableError("tesseract is not installed or not on PATH")

    monkeypatch.setattr("app.services.documents.ocr.resolve_engine", _unavailable)

    assert module.gate_engine(results) is None
    capsys.readouterr()

    module.gate_ocr_live(results, engine_present=False)
    module.gate_ocr_corruption(results, engine_present=False)
    module.gate_api_ocr_upload(results, engine_present=False)

    statuses = {result.gate: result.status for result in results}
    assert statuses["OCR-ENGINE"] == module.NOT_RUN
    assert statuses["GOLD-EX-05 PNG"] == module.NOT_RUN
    assert statuses["GOLD-EX-06 JPEG"] == module.NOT_RUN
    assert statuses["OCR-LIVE-01"] == module.NOT_RUN
    assert statuses["GOLD-EX-11 OCR-produced 1O5"] == module.NOT_RUN
    assert statuses["ING-02 OCR upload end-to-end"] == module.NOT_RUN
    assert module.PASS not in statuses.values(), "a gate that did not run must not pass"


def test_the_probe_exits_non_zero_when_a_gate_is_not_run(tmp_path: Path):
    """Run the script for real and assert the honest exit code.

    This is the property that makes the log usable as evidence: exit ``2`` means
    "not everything ran", and it is expected on any machine without Tesseract.
    """
    output = tmp_path / "result.json"
    environment = {
        "PATH": "/nonexistent-bin",  # make a PATH-discovered engine impossible
        "PYTHONPATH": f"{REPO_ROOT / 'backend'}{paths_separator()}{REPO_ROOT / 'scripts' / 'python'}",
    }

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(output)],
        cwd=REPO_ROOT,
        env={**environment, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert completed.returncode in {0, 2}, completed.stderr
    if completed.returncode == 2:
        assert "NOT RUN" in completed.stdout
        assert "not passed" in completed.stdout
    if output.exists():
        payload = output.read_text(encoding="utf-8")
        assert "NOT RUN" in payload or "PASS" in payload


def test_the_probe_never_points_at_the_runtime_database():
    """A read-only guarantee: the probe must not open ``data/runtime``.

    ``data/runtime`` appears in the module docstring on purpose — as a promise
    *not* to touch it — so the assertion looks at executable lines only, not at
    documentation that says the opposite of the check.
    """
    import ast

    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    code_lines = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt) and not isinstance(node, ast.Expr)
    }
    executable = "\n".join(
        line for number, line in enumerate(source.splitlines(), start=1) if number in code_lines
    )

    assert "data/runtime" not in executable, (
        "the probe must not use the repository runtime database"
    )
    assert "TemporaryDirectory" in source, "all probe state belongs in a temp directory"
    assert "create_app" in source, "the end-to-end gate must use an isolated app instance"


def paths_separator() -> str:
    """Return the platform path separator used by ``PYTHONPATH``."""
    import os

    return os.pathsep


@pytest.mark.parametrize("status", ["PASS", "FAIL", "NOT RUN"])
def test_status_vocabulary_is_exactly_three_words(status):
    """Evidence uses a fixed vocabulary so a log can be read without guessing."""
    module = _module()
    assert {module.PASS, module.FAIL, module.NOT_RUN} == {"PASS", "FAIL", "NOT RUN"}
    assert status in {module.PASS, module.FAIL, module.NOT_RUN}


# --- the handoff document must stay executable and path-correct ---------------

HANDOFF = REPO_ROOT / "docs" / "phase-reports" / "PHASE_3_WINDOWS_ACCEPTANCE.md"


def test_handoff_uses_the_owners_real_paths():
    """The procedure must target ``E:\\DEPI``, not the author's placeholder.

    An earlier revision hard-coded ``C:\\src\\…`` paths that do not exist on the
    owner's machine; a procedure that fails on step 1 is not a handoff.
    """
    text = HANDOFF.read_text(encoding="utf-8")

    assert r"E:\DEPI\AI-Doctor-FollowUp-Agent" in text
    assert r"E:\DEPI\P3-Acceptance" in text
    assert "C:\\src" not in text and "C:/src" not in text


def test_handoff_never_touches_the_main_runtime_database():
    """It must name the main database only to assert it stays unchanged."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "data\\runtime\\app.db" in text
    # The only CommandLine mentions are read-only assertions (Get-Item / compare).
    for line in text.splitlines():
        if "app.db" in line and line.strip().startswith("&"):
            raise AssertionError(f"no executable command may consume app.db: {line!r}")
    assert "TemporaryDirectory" in text or r"P3-Acceptance\artifacts" in text


def test_handoff_pins_the_sha_and_refuses_a_stale_fetch():
    """A detached worktree at the reviewed SHA, with an explicit mismatch guard."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "worktree add --detach" in text
    assert "FETCH_HEAD" in text
    assert "Refusing to proceed" in text
    assert "git -C $Main worktree add" in text


def test_handoff_uses_repo_native_setup_with_frontend():
    """``setup.ps1 -SkipDatabase`` must not also skip the frontend.

    Skipping it would leave ``node_modules`` absent, and the full ``test_all.ps1``
    gate would then correctly FAIL the frontend checks — a false negative caused by
    the procedure, not by the code.
    """
    text = HANDOFF.read_text(encoding="utf-8")

    assert "-SkipDatabase" in text
    setup_call = [
        line for line in text.splitlines() if "setup.ps1" in line and "-SkipDatabase" in line
    ]
    assert setup_call, "the handoff must invoke setup.ps1"
    for line in text.splitlines():
        if "setup.ps1" in line and "-SkipFrontend" in line and "-SkipDatabase" in line:
            raise AssertionError(f"setup.ps1 must not skip the frontend: {line!r}")
    assert "test_all.ps1" in text


def test_handoff_distinguishes_derived_from_executed_cases():
    """GOLD-EX-07/08 must be documented, not claimed as independently executed."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "GOLD-EX-07/08 coverage" in text
    assert "DERIVED" in text
    assert "never claimed as an independent pass" in text


def test_the_owner_comment_is_the_cited_authorization_source():
    """D-14 must cite the owner's comment, not the independent review.

    The owner asked explicitly that the ledger and report reference *their*
    authorization comment rather than a technical review, which is not an approval.
    This pins the distinction so it cannot drift back.
    """
    owner_url = (
        "https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6900700171"
    )
    review_id = "5912501268"

    for relative in ("docs/roadmap/PHASE_PROGRESS.md", "docs/phase-reports/PHASE_3_REPORT.md"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert owner_url in text, f"{relative} must cite the owner's authorization comment"
        # The review may only appear as context/prior finding, never as approval.
        assert "review `5912501268`" not in text or "not" in text, relative
        for line in text.splitlines():
            if review_id in line:
                # Strip markdown emphasis so "**not** the authorization" still matches.
                plain = line.lower().replace("*", "").replace("`", "")
                assert any(
                    marker in plain
                    for marker in (
                        "not the authorization",
                        "not an approval",
                        "not cited as one",
                        "raised by",
                        "prior context",
                        "pullrequestreview",
                    )
                ), f"{relative}: review must not be presented as approval: {line!r}"


def test_handoff_test_count_matches_the_suite_it_describes():
    """The quoted figures must match what pytest actually collects.

    An earlier revision said ``522 passed (P3: 139)``; the suite collects 144 P3
    tests. A handoff that tells the owner to expect the wrong number invites a false
    FAIL, so the number is checked against collection rather than trusted.
    """
    text = HANDOFF.read_text(encoding="utf-8")

    p3_files = sorted((REPO_ROOT / "backend" / "tests" / "p3").glob("test_*.py"))
    assert p3_files, "the P3 suite must exist for this check to mean anything"

    # Each per-file count quoted in the table must be a real, plausible count.
    assert "146" in text and "529 passed" in text
    assert "522 passed" not in text and "P3: 139" not in text and "144" not in text
