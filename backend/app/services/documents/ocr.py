"""Selective OCR through a real Tesseract engine.

Honesty rules for this module:

* **No model, no cloud, no network.** Tesseract is a local executable.
* When the engine is unavailable the result is ``E_DEPENDENCY_MISSING`` — never a
  crash, never an empty string presented as "no text found", and never a silent
  substitution with a text-layer guess (``TOOL_CONTRACTS.md`` §6 rule 5).
* ``engine_confidence`` is recorded **only** when the engine reports one. It is
  never estimated, averaged, or back-filled.
* Confidence means "does a human need to look at this", and nothing else. It is
  not an accuracy claim (``DEMO_REVIEW_RULES.md`` §9, ``ocr_confidence_floor``).

A mocked engine proves the wiring and the failure path. It is never reported as
evidence that OCR works correctly on a real scan; that is ``OCR-LIVE-01`` on the
owner's Windows machine.
"""

from __future__ import annotations

import contextlib
import re
import shutil
from collections.abc import Iterator
from dataclasses import dataclass

import pytesseract
from PIL import Image

from app.core.enums import Preprocessing

#: Matches the confidence token ``tesseract`` emits per word, e.g. ``conf 95``.
_CONFIDENCE_PATTERN = re.compile(r"conf\s+(\d+)")


class OcrUnavailableError(Exception):
    """Raised when the Tesseract engine is not configured or not on ``PATH``."""


@dataclass(frozen=True, slots=True)
class OcrResult:
    """The outcome of one OCR attempt.

    ``text`` is exactly what the engine returned. ``confidence`` is ``None`` when
    ``image_to_data`` was unavailable or reported nothing, because a fabricated
    confidence would corrupt the low-confidence routing rule.
    """

    text: str
    confidence: float | None
    tool_version: str | None


def resolve_engine(tesseract_cmd: str | None) -> str:
    """Return the engine command to use, or raise :class:`OcrUnavailableError`.

    A configured path must exist; otherwise fall back to ``PATH`` discovery. An
    unset configuration means OCR is *not configured*, which is reported honestly
    rather than attempted.
    """
    if tesseract_cmd:
        resolved = shutil.which(tesseract_cmd) or (
            tesseract_cmd if shutil.os.path.isfile(tesseract_cmd) else None
        )
        if resolved is None:
            raise OcrUnavailableError("configured tesseract executable not found")
        return resolved

    discovered = shutil.which("tesseract")
    if discovered is None:
        raise OcrUnavailableError("tesseract is not installed or not on PATH")
    return discovered


@contextlib.contextmanager
def _engine_selected(executable: str) -> Iterator[None]:
    """Point pytesseract at ``executable`` for the duration of the block.

    pytesseract 0.3.13 keeps the binary in a **module global**
    (``pytesseract.pytesseract.tesseract_cmd``) and every call —
    ``get_tesseract_version()``, ``image_to_string()``, ``image_to_data()`` — reads it.
    None of them accepts a path argument, so a resolved ``executable`` has no effect
    unless it is installed here first. This module previously resolved the path and
    then ignored it, so an explicit ``TESSERACT_CMD`` with nothing on ``PATH`` could
    not actually run OCR.

    The previous value is always restored, because leaking one document's engine into
    the next request would make provenance report a version that did not produce the
    text.
    """
    previous = pytesseract.pytesseract.tesseract_cmd
    pytesseract.pytesseract.tesseract_cmd = executable
    try:
        yield
    finally:
        pytesseract.pytesseract.tesseract_cmd = previous


def engine_version(tesseract_cmd: str | None) -> str | None:
    """Return the engine's self-reported version, or ``None`` when unavailable.

    Recorded on ``extraction_attempt.tool_version`` at execution time and never
    claimed in advance.

    ``get_tesseract_version()`` takes **no arguments** in the pinned pytesseract
    0.3.13 — passing ``tesseract_cmd=`` raised
    ``TypeError: get_tesseract_version() got an unexpected keyword argument``, which
    is what broke the Windows acceptance run. The version is therefore read through
    :func:`_engine_selected`, which sets the global the function actually consults.
    """
    try:
        executable = resolve_engine(tesseract_cmd)
        with _engine_selected(executable):
            version = str(pytesseract.get_tesseract_version())
    except (OcrUnavailableError, OSError, RuntimeError, pytesseract.TesseractNotFoundError):
        return None
    return version


def preprocess(image: Image.Image, preprocessing: Preprocessing) -> Image.Image:
    """Apply a deterministic preprocessing step.

    The set is closed and reproducible: ``none`` and ``grayscale_upscale`` only.
    No adaptive thresholding, no deskew, no contrast guessing — a retry must be
    attributable to a specific, recorded transform.
    """
    if preprocessing is Preprocessing.NONE:
        return image

    grayscale = image.convert("L")
    return grayscale.resize(
        (grayscale.width * 2, grayscale.height * 2), resample=Image.Resampling.NEAREST
    )


def _mean_confidence(data: dict[str, list[str]] | dict[str, list[int]]) -> float | None:
    """Return the mean word confidence on a 0-1 scale, or ``None``.

    ``None`` means the engine reported no usable confidence; it is not ``0.0``,
    and it is never replaced by an estimate.
    """
    raw_confidences = data.get("conf", [])
    values: list[float] = []
    for raw in raw_confidences:
        try:
            number = float(raw)
        except (TypeError, ValueError):
            continue
        if number >= 0:  # Tesseract uses -1 for non-text rows.
            values.append(number / 100.0)
    if not values:
        return None
    return sum(values) / len(values)


def run_ocr(
    image: Image.Image,
    *,
    tesseract_cmd: str | None,
    language: str,
    preprocessing: Preprocessing = Preprocessing.NONE,
) -> OcrResult:
    """Run one OCR attempt and return the engine's text and confidence.

    Raises :class:`OcrUnavailableError` when the engine is missing, so the caller
    maps it to ``E_DEPENDENCY_MISSING`` and marks the document failed rather than
    verified.
    """
    executable = resolve_engine(tesseract_cmd)
    prepared = preprocess(image, preprocessing)

    config = f"--psm 6 -l {language}"
    confidence: float | None = None
    with _engine_selected(executable):
        # Both calls must run inside the selection: pytesseract shells out to the
        # module-global command, so without this the resolved path would be ignored.
        text = pytesseract.image_to_string(prepared, lang=language, config=config, timeout=20)

        try:
            data = pytesseract.image_to_data(
                prepared,
                lang=language,
                config=config,
                output_type=pytesseract.Output.DICT,
                timeout=20,
            )
            confidence = _mean_confidence(data)
        except (OSError, RuntimeError, pytesseract.TesseractError):
            # Confidence is optional telemetry; text extraction already succeeded.
            confidence = None

    # Read the version from the same executable that produced the text, so the
    # recorded provenance cannot name a different binary.
    return OcrResult(
        text=text,
        confidence=confidence,
        tool_version=engine_version(executable),
    )


def confidence_below_floor(confidence: float | None, *, floor: float) -> bool:
    """Return ``True`` when a reported confidence is below the demo floor.

    ``None`` means "not reported" and is *not* counted as low-confidence here;
    the value-level readability checks decide usability instead. Conflating
    "unreported" with "bad" would fabricate a signal.
    """
    if confidence is None:
        return False
    return confidence < floor


def looks_corrupted(text: str) -> bool:
    """Return ``True`` for the documented OCR confusion patterns.

    Only the substitutions named by the contract are checked (``O``/``0`` and
    ``l``/``1`` inside a numeric token). This is a readability heuristic for
    routing to a human, never a correctness judgement.
    """
    for token in text.split():
        stripped = token.strip(".,;:")
        if not stripped:
            continue
        has_digit = any(character.isdigit() for character in stripped)
        if not has_digit:
            continue
        if "O" in stripped or "l" in stripped:
            return True
    return False


__all__ = [
    "OcrResult",
    "OcrUnavailableError",
    "confidence_below_floor",
    "engine_version",
    "looks_corrupted",
    "preprocess",
    "resolve_engine",
    "run_ocr",
]
