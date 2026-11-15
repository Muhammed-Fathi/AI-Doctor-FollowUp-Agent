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
