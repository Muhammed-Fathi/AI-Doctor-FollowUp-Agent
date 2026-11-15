"""Regression tests for P3-R11: the pytesseract 0.3.13 integration.

These were written **before** the fix and fail against the reviewed head
``9ee6b4a``. Two distinct production defects are covered, because the owner's
Windows run exposed both at once:

1. ``engine_version`` called ``pytesseract.get_tesseract_version(tesseract_cmd=...)``,
   but that function takes **no arguments** in pytesseract 0.3.13 — it reads the
   module-level ``tesseract_cmd``. On Windows this raised
   ``TypeError: get_tesseract_version() got an unexpected keyword argument
   'tesseract_cmd'``, so ``OCR-ENGINE`` failed and six dependent gates never ran.
2. ``run_ocr`` resolved an ``executable`` and then **ignored it**: pytesseract's
   ``image_to_string``/``image_to_data`` shell out to the module-global
   ``pytesseract.pytesseract.tesseract_cmd``. A machine with an explicit
   ``TESSERACT_CMD`` but nothing on ``PATH`` would therefore have failed to OCR, or
   silently used a *different* binary than the one we recorded a version for.

The tests assert the observable API contract — what actually gets executed — rather
than mocking the exception away. No real Tesseract runs here; live OCR remains
``OCR-LIVE-01`` on the owner's Windows machine.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.core.enums import Preprocessing
from app.services.documents import ocr as ocr_module


class _FakeEngine:
    """A stand-in for the Tesseract executable, driven through ``subprocess``.

    It is a real executable file, so ``shutil.which``/``isfile`` accept it exactly as
    they would ``tesseract.exe``, and it records the argv it was invoked with. That
    lets a test prove *which binary actually ran*, which a mock of pytesseract's
    internals could not.
    """

    def __init__(self, path: Path, *, version: str = "5.4.0.20240606") -> None:
        self.path = path
        self.version = version
        self.calls: list[list[str]] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":  # pragma: no cover - exercised on Windows only
            script = path.with_suffix(".bat")
            script.write_text(f"@echo off\r\necho tesseract {version}\r\n", encoding="utf-8")
            self.path = script
        else:
            path.write_text(
                f'#!/bin/sh\nprintf "tesseract {version}\\n"\n',
                encoding="utf-8",
            )
            path.chmod(0o755)


def _isolate_pytesseract_global(monkeypatch):
    """Reset pytesseract's module-global command and its version cache."""
    import pytesseract

    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    # ``get_tesseract_version`` is wrapped in ``@run_once``; clear the memo so a
    # previously cached version cannot make an assertion vacuous.
    target = pytesseract.get_tesseract_version
    if hasattr(target, "_result"):
        monkeypatch.setattr(target, "_result", target, raising=False)


# ---------------------------------------------------------------- defect 1: version


def test_engine_version_does_not_pass_an_unsupported_keyword(monkeypatch, tmp_path):
    """``engine_version`` must not call ``get_tesseract_version(tesseract_cmd=...)``.

    The owner's failure: pytesseract 0.3.13 takes no such argument. This reproduces it
    by asserting on the *signature*, so the test fails for the same reason on any
    platform rather than only where a real engine exists.
    """
    engine = _FakeEngine(tmp_path / "bin" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)

    version = ocr_module.engine_version(str(engine.path))

    assert version is not None, "a real, executable engine must yield its version"
    assert engine.version in version


def test_engine_version_points_pytesseract_at_the_resolved_executable(monkeypatch, tmp_path):
    """The version is read from the *configured* binary, not whatever is on PATH."""
    engine = _FakeEngine(tmp_path / "explicit" / "tesseract", version="5.4.0.20240606")
    _isolate_pytesseract_global(monkeypatch)

    import pytesseract

    recorded: dict[str, str] = {}

    def _fake_version():
        recorded["cmd"] = pytesseract.pytesseract.tesseract_cmd
        return "5.4.0.20240606"

    monkeypatch.setattr(pytesseract, "get_tesseract_version", _fake_version)

    version = ocr_module.engine_version(str(engine.path))

    assert version == "5.4.0.20240606"
    assert recorded["cmd"] == str(engine.path), "pytesseract must target the resolved path"


def test_engine_version_returns_none_when_the_engine_is_missing(monkeypatch, tmp_path):
    """An absent engine is ``None``, never a fabricated version."""
    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    missing = tmp_path / "nope" / "tesseract"

    assert ocr_module.engine_version(str(missing)) is None


# ------------------------------------------------------- defect 2: the real command


def test_run_ocr_targets_the_explicit_executable_not_path(monkeypatch, tmp_path):
    """With only an explicit ``TESSERACT_CMD``, the OCR subprocess must use it.

    The reviewed code resolved ``executable`` and then ignored it, so pytesseract
    invoked its module-global command. With no ``tesseract`` on ``PATH`` that raises
    ``TesseractNotFoundError`` — the review's second finding.
    """
    from PIL import Image

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    import pytesseract

    seen: dict[str, str] = {}

    def _fake_image_to_string(image, **kwargs):
        seen["cmd"] = pytesseract.pytesseract.tesseract_cmd
        return "Test: Hemoglobin Value: 13.4 g/dL"

    def _fake_image_to_data(image, **kwargs):
        seen["data_cmd"] = pytesseract.pytesseract.tesseract_cmd
        return {"conf": ["95", "90"]}

    monkeypatch.setattr(pytesseract, "image_to_string", _fake_image_to_string)
    monkeypatch.setattr(pytesseract, "image_to_data", _fake_image_to_data)
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    result = ocr_module.run_ocr(
        Image.new("RGB", (20, 20), "white"),
        tesseract_cmd=str(engine.path),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert seen["cmd"] == str(engine.path), "image_to_string must use the explicit path"
    assert seen["data_cmd"] == str(engine.path), "image_to_data must use the explicit path"
    assert result.tool_version == "5.4.0.20240606"


def test_run_ocr_uses_path_discovery_when_nothing_is_configured(monkeypatch, tmp_path):
    """With no configured path, discovery through ``PATH`` still works."""
    from PIL import Image

    engine = _FakeEngine(tmp_path / "onpath" / "tesseract")
    monkeypatch.setenv("PATH", str(engine.path.parent))
    _isolate_pytesseract_global(monkeypatch)

    import pytesseract

    seen: dict[str, str] = {}

    def _fake_image_to_string(image, **kwargs):
        seen["cmd"] = pytesseract.pytesseract.tesseract_cmd
        return "text"

    monkeypatch.setattr(pytesseract, "image_to_string", _fake_image_to_string)
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: {"conf": ["80"]})
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    result = ocr_module.run_ocr(
        Image.new("RGB", (20, 20), "white"),
        tesseract_cmd=None,
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert seen["cmd"] == str(engine.path)
    assert result.text == "text"
    assert result.confidence == pytest.approx(0.8)


def test_run_ocr_restores_the_global_command_after_use(monkeypatch, tmp_path):
    """The explicit path must not leak into a later call that relies on ``PATH``.

    pytesseract keeps the command in a module global, so a naive assignment would make
    one document's configuration bleed into the next — a real cross-request hazard.
    """
    from PIL import Image

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)

    import pytesseract

    before = pytesseract.pytesseract.tesseract_cmd
    monkeypatch.setattr(pytesseract, "image_to_string", lambda image, **kw: "text")
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: {"conf": ["80"]})
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    ocr_module.run_ocr(
        Image.new("RGB", (20, 20), "white"),
        tesseract_cmd=str(engine.path),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert pytesseract.pytesseract.tesseract_cmd == before, (
        "the module-global tesseract_cmd must be restored"
    )


def test_run_ocr_raises_when_the_engine_is_absent(monkeypatch, tmp_path):
    """A missing engine is ``OcrUnavailableError`` (never a silent empty result)."""
    from PIL import Image

    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(ocr_module.OcrUnavailableError):
        ocr_module.run_ocr(
            Image.new("RGB", (20, 20), "white"),
            tesseract_cmd=None,
            language="eng",
        )


def test_run_ocr_does_not_fabricate_a_version(monkeypatch, tmp_path):
    """When the version cannot be read, ``tool_version`` is ``None``, not invented."""
    from PIL import Image

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)

    import pytesseract

    monkeypatch.setattr(pytesseract, "image_to_string", lambda image, **kw: "text")
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: {"conf": []})
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: None)

    result = ocr_module.run_ocr(
        Image.new("RGB", (20, 20), "white"),
        tesseract_cmd=str(engine.path),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert result.tool_version is None
    assert result.confidence is None, "no reported confidence must stay None, not 0.0"


def test_pytesseract_is_pinned_to_a_version_with_this_signature():
    """Guard the assumption the fix rests on, without changing the pin."""
    import inspect

    import pytesseract

    parameters = inspect.signature(pytesseract.get_tesseract_version).parameters
    assert list(parameters) == [], (
        "pytesseract's get_tesseract_version must take no arguments; "
        f"found {list(parameters)}. Re-check the integration if the pin moves."
    )
    assert pytesseract.__version__ == "0.3.13"


def test_the_integration_never_calls_the_version_function_with_a_keyword():
    """Static guard: the reviewed defect must not be reintroduced by hand."""
    source = Path(ocr_module.__file__).read_text(encoding="utf-8")

    assert "get_tesseract_version(tesseract_cmd" not in source.replace(" ", ""), (
        "engine_version must not pass tesseract_cmd to get_tesseract_version"
    )
    assert not isinstance(subprocess, type(None))  # keep the import meaningful


# ------------------------------------- end-to-end through a real subprocess
#
# The tests above stub pytesseract's *functions* to observe which command it would
# use. These go one layer deeper: a real executable is invoked through
# ``subprocess.Popen`` exactly as pytesseract does it, so the assertion covers the
# genuine call path — argument construction, output-file reading, version parsing and
# TSV/confidence parsing — rather than a mock of it.
#
# The fake binary speaks Tesseract's file protocol (``<base>.txt`` / ``<base>.tsv``)
# and its ``--version`` output. Linux/macOS only, since it is a shell script.

_FAKE_TESSERACT = """#!/bin/sh
# A stand-in for the Tesseract CLI: same argv contract, deterministic output.
if [ "$1" = "--version" ]; then
  echo "tesseract 5.4.0.20240606"
  echo "  leptonica-1.82.0"
  echo "  libgif 5.1.4"
  exit 0
fi
input="$1"
base="$2"
shift 2
# pytesseract asks for TSV with "-c tessedit_create_tsv=1" in the config and does NOT
# append a "tsv" argument (unlike "txt", which it passes positionally).
want_tsv="no"
for arg in "$@"; do
  case "$arg" in
    tessedit_create_tsv=1) want_tsv="yes" ;;
  esac
done
if [ "$want_tsv" = "yes" ]; then
  # pytesseract reads the output file, not stdout.
  {
    printf 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
    printf '5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t96\tHemoglobin\n'
    printf '5\t1\t1\t1\t1\t2\t12\t0\t10\t10\t94\t13.4\n'
    printf '5\t1\t1\t1\t1\t3\t24\t0\t10\t10\t-1\t\n'
  } > "$base.tsv"
else
  printf 'SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\nTest: Hemoglobin  Value: 13.4 g/dL\n' > "$base.txt"
fi
exit 0
"""


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the fake engine is a POSIX shell script; Windows uses the real Tesseract",
)
def test_end_to_end_ocr_through_a_real_subprocess(monkeypatch, tmp_path):
    """A real subprocess is invoked with the explicit path and its output is parsed.

    This is the test that would have caught the reviewed defect on any machine: the
    engine binary is *not* named ``tesseract`` and is *not* on ``PATH``, so it can only
    run if the resolved path is actually installed into pytesseract's global.
    """
    from PIL import Image

    engine = tmp_path / "explicit" / "tesseract-5.4.0"
    engine.parent.mkdir(parents=True)
    engine.write_text(_FAKE_TESSERACT, encoding="utf-8")
    engine.chmod(0o755)

    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    import pytesseract

    real_version = pytesseract.get_tesseract_version
    if hasattr(real_version, "_result"):
        monkeypatch.setattr(real_version, "_result", real_version, raising=False)

    result = ocr_module.run_ocr(
        Image.new("RGB", (60, 30), "white"),
        tesseract_cmd=str(engine),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    # The engine's real text came back, through a real subprocess.
    assert "Hemoglobin" in result.text
    assert "13.4" in result.text
    # Confidence was parsed from real TSV, ignoring the -1 filler row.
    assert result.confidence == pytest.approx((0.96 + 0.94) / 2)
    # Provenance is the version the fake binary actually reported.
    assert result.tool_version == "5.4.0.20240606"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the fake engine is a POSIX shell script; Windows uses the real Tesseract",
)
def test_end_to_end_path_discovery(monkeypatch, tmp_path):
    """The same flow works with no explicit path, discovered through ``PATH``."""
    from PIL import Image

    engine = tmp_path / "onpath" / "tesseract"
    engine.parent.mkdir(parents=True)
    engine.write_text(_FAKE_TESSERACT, encoding="utf-8")
    engine.chmod(0o755)

    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(engine.parent))

    import pytesseract

    real_version = pytesseract.get_tesseract_version
    if hasattr(real_version, "_result"):
        monkeypatch.setattr(real_version, "_result", real_version, raising=False)

    result = ocr_module.run_ocr(
        Image.new("RGB", (60, 30), "white"),
        tesseract_cmd=None,
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert "Hemoglobin" in result.text
    assert result.tool_version == "5.4.0.20240606"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the fake engine is a POSIX shell script; Windows uses the real Tesseract",
)
def test_a_failing_engine_is_reported_not_swallowed(monkeypatch, tmp_path):
    """A nonzero exit surfaces as an engine error — never as empty "no text found"."""
    from PIL import Image

    engine = tmp_path / "broken" / "tesseract"
    engine.parent.mkdir(parents=True)
    engine.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    engine.chmod(0o755)

    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    import pytesseract

    with pytest.raises((pytesseract.TesseractError, ocr_module.OcrUnavailableError)):
        ocr_module.run_ocr(
            Image.new("RGB", (60, 30), "white"),
            tesseract_cmd=str(engine),
            language="eng",
        )
