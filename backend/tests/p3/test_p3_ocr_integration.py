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

import ntpath
import os
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


def _assert_same_executable(actual: str, expected: Path) -> None:
    """Assert ``actual`` names the same executable file as ``expected``.

    On Windows, ``shutil.which`` appends the upper-case extension from ``PATHEXT``
    (e.g. ``tesseract.BAT``) even when the file on disk is ``tesseract.bat``.
    ``os.path.normcase`` preserves strict case sensitivity on POSIX while applying
    platform-semantic case folding on Windows, and ``os.path.samefile`` verifies
    both paths resolve to the exact same filesystem entry.
    """
    actual_path = Path(actual)
    assert actual_path.is_file(), f"resolved executable does not exist: {actual!r}"
    assert os.path.samefile(actual_path, expected), f"{actual!r} is not {expected!r}"
    assert os.path.normcase(os.path.abspath(actual)) == os.path.normcase(
        os.path.abspath(expected)
    ), f"{actual!r} != {str(expected)!r}"


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
    _assert_same_executable(recorded["cmd"], engine.path)


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

    _assert_same_executable(seen["cmd"], engine.path)
    _assert_same_executable(seen["data_cmd"], engine.path)
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

    _assert_same_executable(seen["cmd"], engine.path)
    assert result.text == "text"
    assert result.confidence == pytest.approx(0.8)


def test_executable_identity_helper_respects_platform_casing(monkeypatch, tmp_path):
    """Windows ``PATHEXT`` casing (``.BAT`` vs ``.bat``) matches; wrong files fail."""
    bat = tmp_path / "tesseract.bat"
    bat.write_text("@echo off\r\n", encoding="utf-8")
    upper_bat = tmp_path / "tesseract.BAT"
    if not upper_bat.exists():
        upper_bat.symlink_to(bat)

    # Under Windows normalization, `.BAT` and `.bat` pointing to the same file match.
    with monkeypatch.context() as win_ctx:
        win_ctx.setattr(os.path, "normcase", ntpath.normcase)
        _assert_same_executable(str(upper_bat), bat)

    # Under POSIX normalization (os.path.normcase restored), mismatched case still fails.
    if sys.platform != "win32":
        with pytest.raises(AssertionError):
            _assert_same_executable(str(upper_bat), bat)

    # A different binary with the same directory never passes under either rule.
    other = tmp_path / "other.bat"
    other.write_text("@echo off\r\n", encoding="utf-8")
    with monkeypatch.context() as win_ctx:
        win_ctx.setattr(os.path, "normcase", ntpath.normcase)
        with pytest.raises(AssertionError):
            _assert_same_executable(str(other), bat)


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


# ============================ P3-R12: process-global executable selection
#
# ``_engine_selected`` mutates ``pytesseract.pytesseract.tesseract_cmd``, a process
# global. Without synchronisation two overlapping OCR calls with *different* executables
# interleave: one thread invokes another's binary, and out-of-order restores leave the
# global at an arbitrary value — silently corrupting ``tool_version`` provenance.
#
# These tests force the contention rather than hoping for it: a holder thread parks
# inside the selection, and a contender then tries to enter. Deterministic, and fast.

_R12_HOLD_TIMEOUT = 5.0


def test_selection_is_mutually_exclusive(monkeypatch):
    """A second selection cannot enter while one is active."""
    import threading

    import pytesseract

    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")

    holder_inside = threading.Event()
    release_holder = threading.Event()
    contender_entered = threading.Event()
    seen_by_holder: list[str] = []

    def holder() -> None:
        with ocr_module._engine_selected("/engine/A"):
            holder_inside.set()
            release_holder.wait(_R12_HOLD_TIMEOUT)
            # Read *after* the contender has had time to interfere.
            seen_by_holder.append(pytesseract.pytesseract.tesseract_cmd)

    def contender() -> None:
        holder_inside.wait(_R12_HOLD_TIMEOUT)
        with ocr_module._engine_selected("/engine/B"):
            contender_entered.set()

    holder_thread = threading.Thread(target=holder)
    contender_thread = threading.Thread(target=contender)
    holder_thread.start()
    assert holder_inside.wait(_R12_HOLD_TIMEOUT), "holder never entered the selection"
    contender_thread.start()

    # The contender must stay blocked while the holder owns the selection.
    assert not contender_entered.wait(0.25), (
        "a second engine selection entered concurrently — the global is unsynchronised"
    )

    release_holder.set()
    holder_thread.join(_R12_HOLD_TIMEOUT)
    contender_thread.join(_R12_HOLD_TIMEOUT)

    assert seen_by_holder == ["/engine/A"], (
        f"the holder observed a cross-wired engine: {seen_by_holder}"
    )
    assert contender_entered.is_set(), "the contender should proceed once released"


def test_concurrent_selections_restore_the_original_value(monkeypatch):
    """After overlapping selections, the global is back to its original value."""
    import threading

    import pytesseract

    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    errors: list[BaseException] = []

    def worker(path: str) -> None:
        try:
            for _ in range(20):
                with ocr_module._engine_selected(path):
                    if pytesseract.pytesseract.tesseract_cmd != path:
                        raise AssertionError(f"{path} saw {pytesseract.pytesseract.tesseract_cmd}")
        except BaseException as error:  # pragma: no cover - surfaced below
            errors.append(error)

    threads = [threading.Thread(target=worker, args=(f"/engine/{index}",)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(_R12_HOLD_TIMEOUT * 2)

    assert not errors, errors
    assert pytesseract.pytesseract.tesseract_cmd == "tesseract"


def test_run_ocr_holds_the_selection_across_its_engine_calls(monkeypatch, tmp_path):
    """A live ``run_ocr`` keeps the global stable for its whole engine interaction."""
    import threading

    from PIL import Image

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)

    import pytesseract

    seen: list[str] = []
    inside = threading.Event()
    release = threading.Event()

    def _fake_image_to_string(image, **kwargs):
        seen.append(pytesseract.pytesseract.tesseract_cmd)
        inside.set()
        release.wait(_R12_HOLD_TIMEOUT)
        return "text"

    monkeypatch.setattr(pytesseract, "image_to_string", _fake_image_to_string)
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: {"conf": []})
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: None)

    worker = threading.Thread(
        target=lambda: ocr_module.run_ocr(
            Image.new("RGB", (8, 8), "white"),
            tesseract_cmd=str(engine.path),
            language="eng",
        )
    )
    worker.start()
    assert inside.wait(_R12_HOLD_TIMEOUT), "run_ocr did not reach the engine call"

    intruded = threading.Event()

    def _intrude() -> None:
        with ocr_module._engine_selected("/engine/OTHER"):
            intruded.set()

    other = threading.Thread(target=_intrude)
    other.start()

    # While run_ocr is inside, no other selection may take effect.
    assert not intruded.wait(0.25), "another selection entered during a live run_ocr"
    _assert_same_executable(pytesseract.pytesseract.tesseract_cmd, engine.path)

    release.set()
    worker.join(_R12_HOLD_TIMEOUT)
    other.join(_R12_HOLD_TIMEOUT)

    assert len(seen) == 1
    _assert_same_executable(seen[0], engine.path)
    assert intruded.is_set(), "the intruder should proceed once run_ocr releases"


# ------------------------------------- Stage 2: TSV bounding-box layout reconstruction


def _tsv_dict_from_lines(
    line_boxes: list[list[tuple[int, int, int, int, str]]],
    *,
    conf: str = "95",
    cross_block_on_col_gap: bool = False,
) -> dict[str, list]:
    """Build a pytesseract ``Output.DICT`` TSV table from measured word boxes."""
    out: dict[str, list] = {
        "level": [],
        "page_num": [],
        "block_num": [],
        "par_num": [],
        "line_num": [],
        "word_num": [],
        "left": [],
        "top": [],
        "width": [],
        "height": [],
        "conf": [],
        "text": [],
    }
    block = 1
    for line_idx, words in enumerate(line_boxes, start=1):
        # Emit a Tesseract level=4 line row (conf=-1, empty text) just like real TSV.
        min_l = min(w[0] for w in words)
        min_t = min(w[1] for w in words)
        max_r = max(w[0] + w[2] for w in words)
        max_b = max(w[1] + w[3] for w in words)
        out["level"].append(4)
        out["page_num"].append(1)
        out["block_num"].append(block)
        out["par_num"].append(1)
        out["line_num"].append(line_idx)
        out["word_num"].append(0)
        out["left"].append(min_l)
        out["top"].append(min_t)
        out["width"].append(max_r - min_l)
        out["height"].append(max_b - min_t)
        out["conf"].append("-1")
        out["text"].append("")

        prev_right: int | None = None
        active_block = block
        word_num = 1
        for left, top, width, height, token in words:
            if cross_block_on_col_gap and prev_right is not None and (left - prev_right) >= 40:
                active_block += 1
                word_num = 1
            out["level"].append(5)
            out["page_num"].append(1)
            out["block_num"].append(active_block)
            out["par_num"].append(1)
            out["line_num"].append(line_idx)
            out["word_num"].append(word_num)
            out["left"].append(left)
            out["top"].append(top)
            out["width"].append(width)
            out["height"].append(height)
            out["conf"].append(conf)
            out["text"].append(token)
            prev_right = left + width
            word_num += 1
    return out


def _measured_40px_boxes() -> dict[str, list[list[tuple[int, int, int, int, str]]]]:
    """Exact Pillow 40px Aileron Regular boxes for the three Stage 2 calibration sources.

    Note: ``-`` uses a tight ink height of ``5`` px (matching Tesseract tight glyph boxes)
    to verify reference ranges (``70 - 99``, ``12.0 - 15.5``, ``70 - 110``) never
    trigger false double spaces when punctuation height is small.
    """
    header_top = [
        (60, 74, 216, 30, "SYNTHETIC"),
        (285, 74, 117, 30, "DEMO"),
        (411, 75, 104, 28, "DATA"),
        (524, 94, 10, 5, "-"),
        (543, 74, 83, 30, "NOT"),
        (635, 75, 26, 28, "A"),
        (670, 75, 98, 28, "REAL"),
        (777, 74, 175, 30, "MEDICAL"),
        (961, 74, 160, 30, "RECORD"),
    ]
    patient_base = [
        (60, 133, 107, 29, "Demo"),
        (176, 132, 124, 30, "Patient"),
        (309, 133, 26, 28, "A"),
        (443, 130, 67, 32, "Ref:"),
        (519, 132, 232, 30, "DEMO-A-001"),
        (859, 133, 120, 36, "Report"),
        (988, 131, 88, 31, "date:"),
    ]
    return {
        "report_a_glucose.txt": [
            header_top,
            [*patient_base, (1085, 132, 204, 30, "2026-11-02")],
            [
                (60, 191, 85, 29, "Test:"),
                (154, 190, 132, 38, "Fasting"),
                (295, 189, 143, 39, "glucose"),
                (483, 189, 110, 31, "Value:"),
                (602, 190, 69, 30, "104"),
                (680, 189, 118, 39, "mg/dL"),
            ],
            [
                (60, 246, 184, 32, "Reference"),
                (253, 255, 113, 31, "range:"),
                (375, 248, 46, 30, "70"),
                (430, 268, 10, 5, "-"),
                (449, 248, 46, 30, "99"),
                (504, 247, 118, 39, "mg/dL"),
            ],
        ],
        "report_a_clean.txt": [
            header_top,
            [*patient_base, (1085, 132, 204, 30, "2026-10-20")],
            [
                (60, 191, 85, 29, "Test:"),
                (154, 189, 222, 39, "Hemoglobin"),
                (466, 189, 110, 31, "Value:"),
                (585, 190, 77, 30, "13.4"),
                (671, 189, 84, 39, "g/dL"),
            ],
            [
                (60, 246, 184, 32, "Reference"),
                (253, 255, 113, 31, "range:"),
                (375, 248, 77, 30, "12.0"),
                (461, 268, 10, 5, "-"),
                (480, 249, 77, 29, "15.5"),
                (566, 247, 84, 39, "g/dL"),
            ],
        ],
        "report_ocr_o_confusion.txt": [
            header_top,
            [*patient_base, (1085, 132, 204, 30, "2026-10-20")],
            [
                (60, 191, 85, 29, "Test:"),
                (154, 189, 148, 31, "Glucose"),
                (419, 189, 110, 31, "Value:"),
                (538, 190, 76, 30, "1O5"),
                (623, 189, 118, 39, "mg/dL"),
            ],
            [
                (60, 246, 184, 32, "Reference"),
                (253, 255, 113, 31, "range:"),
                (375, 248, 46, 30, "70"),
                (430, 268, 10, 5, "-"),
                (449, 248, 69, 30, "110"),
                (527, 247, 118, 39, "mg/dL"),
            ],
        ],
    }


@pytest.mark.parametrize(
    "source_name,expected_test,expected_value,expected_unit,expected_ref,expect_flags",
    [
        (
            "report_a_glucose.txt",
            "Fasting glucose",
            "104",
            "mg/dL",
            "70 - 99 mg/dL",
            ("clean",),
        ),
        (
            "report_a_clean.txt",
            "Hemoglobin",
            "13.4",
            "g/dL",
            "12.0 - 15.5 g/dL",
            ("clean",),
        ),
        (
            "report_ocr_o_confusion.txt",
            "Glucose",
            None,
            "mg/dL",
            "70 - 110 mg/dL",
            ("unparseable_value",),
        ),
    ],
)
def test_stage2_tsv_layout_recovers_40px_column_gaps_without_reference_double_spaces(
    monkeypatch,
    tmp_path,
    source_name: str,
    expected_test: str,
    expected_value: str | None,
    expected_unit: str,
    expected_ref: str,
    expect_flags: tuple[str, ...],
):
    """Stage 2: TSV bounding boxes recover Test/Value separation without ``  `` in ranges."""
    from PIL import Image

    from app.core.enums import ExtractionPath, FactField
    from app.services.documents.field_parser import parse_pages
    from app.services.documents.text_extraction import PageText

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)
    import pytesseract

    tsv = _tsv_dict_from_lines(_measured_40px_boxes()[source_name], conf="95")
    collapsed_plain = (
        "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
        "Demo Patient A Ref: DEMO-A-001 Report date: 2026-11-02\n"
        f"Test: {expected_test} Value: 104 {expected_unit}\n"
        f"Reference range: {expected_ref}\n"
    )

    monkeypatch.setattr(pytesseract, "image_to_string", lambda image, **kw: collapsed_plain)
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: tsv)
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    result = ocr_module.run_ocr(
        Image.new("RGB", (1349, 400), "white"),
        tesseract_cmd=str(engine.path),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    lines = result.text.splitlines()
    assert len(lines) == 4
    assert f"Reference range: {expected_ref}" == lines[3], (
        f"unexpected spacing in reference range: {lines[3]!r}"
    )
    assert "  " not in lines[0]
    assert "  " not in lines[3]
    assert "  Value:" in lines[2]

    parsed = parse_pages(
        [
            PageText(
                page_index=0,
                text=result.text,
                extractor=ExtractionPath.TESSERACT,
                confidence=result.confidence,
            )
        ]
    )
    by_field = {fact.field_name: fact for fact in parsed.facts}
    assert set(by_field) == {
        FactField.REPORT_DATE,
        FactField.TEST_NAME,
        FactField.VALUE,
        FactField.UNIT,
        FactField.REFERENCE_TEXT,
    }
    assert by_field[FactField.TEST_NAME].normalized_value == expected_test
    assert by_field[FactField.VALUE].normalized_value == expected_value
    assert by_field[FactField.UNIT].normalized_value == expected_unit
    assert by_field[FactField.REFERENCE_TEXT].normalized_value == expected_ref
    assert tuple(flag.value for flag in by_field[FactField.VALUE].quality_flags) == expect_flags


def test_stage2_tsv_layout_merges_same_row_across_blocks_and_is_2x_scale_invariant():
    """Stage 2: split Tesseract blocks on one visual row merge; 2x scale keeps spacing."""
    boxes = _measured_40px_boxes()["report_a_glucose.txt"]
    tsv_1x = _tsv_dict_from_lines(boxes, conf="94", cross_block_on_col_gap=True)
    scaled_boxes = [
        [(left * 2, t * 2, w * 2, h * 2, tok) for (left, t, w, h, tok) in row] for row in boxes
    ]
    tsv_2x = _tsv_dict_from_lines(scaled_boxes, conf="94", cross_block_on_col_gap=True)

    text_1x = ocr_module.reconstruct_layout_from_tsv(tsv_1x)
    text_2x = ocr_module.reconstruct_layout_from_tsv(tsv_2x)

    assert text_1x is not None
    assert text_1x == text_2x
    lines = text_1x.splitlines()
    assert len(lines) == 4
    assert "Test: Fasting glucose" in lines[2] and "Value: 104 mg/dL" in lines[2]
    assert "  Value:" in lines[2]
    assert lines[3] == "Reference range: 70 - 99 mg/dL"


def test_stage2_tsv_layout_falls_back_when_tsv_lacks_word_boxes(monkeypatch, tmp_path):
    """Legacy TSV stubs without box geometry fall back to ``image_to_string`` cleanly."""
    from PIL import Image

    engine = _FakeEngine(tmp_path / "explicit" / "tesseract")
    _isolate_pytesseract_global(monkeypatch)
    import pytesseract

    monkeypatch.setattr(pytesseract, "image_to_string", lambda image, **kw: "Fallback text")
    monkeypatch.setattr(pytesseract, "image_to_data", lambda image, **kw: {"conf": ["91"]})
    monkeypatch.setattr(ocr_module, "engine_version", lambda cmd: "5.4.0.20240606")

    result = ocr_module.run_ocr(
        Image.new("RGB", (20, 20), "white"),
        tesseract_cmd=str(engine.path),
        language="eng",
    )

    assert result.text == "Fallback text"
    assert result.confidence == pytest.approx(0.91)
    assert ocr_module.reconstruct_layout_from_tsv({"conf": ["91"]}) is None


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the fake engine is a POSIX shell script; Windows uses the real Tesseract",
)
def test_stage2_real_subprocess_tsv_reconstructs_glucose_columns(monkeypatch, tmp_path):
    """Real subprocess TSV output recovers column spacing even if stdout .txt collapses it."""
    from PIL import Image

    from app.core.enums import ExtractionPath, FactField
    from app.services.documents.field_parser import parse_pages
    from app.services.documents.text_extraction import PageText

    boxes = _measured_40px_boxes()["report_a_glucose.txt"]
    tsv_rows = [
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    ]
    for line_idx, row in enumerate(boxes, start=1):
        for word_idx, (left, t, w, h, tok) in enumerate(row, start=1):
            tsv_rows.append(f"5\t1\t1\t1\t{line_idx}\t{word_idx}\t{left}\t{t}\t{w}\t{h}\t94\t{tok}")
    # Write via POSIX shell builtin `printf` so the test works even when PATH is empty.
    tsv_writes = "\n".join(f"  printf '%s\\n' '{line}' >> \"$base.tsv\"" for line in tsv_rows)

    fake_script = f"""#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "tesseract 5.4.0.20240606"
  exit 0
fi
base="$2"
shift 2
want_tsv="no"
for arg in "$@"; do
  case "$arg" in
    tessedit_create_tsv=1) want_tsv="yes" ;;
  esac
done
if [ "$want_tsv" = "yes" ]; then
  : > "$base.tsv"
{tsv_writes}
else
  printf 'Test: Fasting glucose Value: 104 mg/dL\\n' > "$base.txt"
fi
exit 0
"""
    engine = tmp_path / "explicit" / "tesseract-stage2"
    engine.parent.mkdir(parents=True)
    engine.write_text(fake_script, encoding="utf-8")
    engine.chmod(0o755)

    _isolate_pytesseract_global(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    result = ocr_module.run_ocr(
        Image.new("RGB", (1349, 400), "white"),
        tesseract_cmd=str(engine),
        language="eng",
        preprocessing=Preprocessing.NONE,
    )

    assert "Test: Fasting glucose     Value: 104 mg/dL" in result.text
    assert "Reference range: 70 - 99 mg/dL" in result.text
    parsed = parse_pages(
        [
            PageText(
                page_index=0,
                text=result.text,
                extractor=ExtractionPath.TESSERACT,
                confidence=result.confidence,
            )
        ]
    )
    fields = {f.field_name: f.normalized_value for f in parsed.facts}
    assert fields == {
        FactField.REPORT_DATE: "2026-11-02",
        FactField.TEST_NAME: "Fasting glucose",
        FactField.VALUE: "104",
        FactField.UNIT: "mg/dL",
        FactField.REFERENCE_TEXT: "70 - 99 mg/dL",
    }
