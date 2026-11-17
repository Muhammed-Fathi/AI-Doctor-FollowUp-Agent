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
import statistics
import threading
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

import pytesseract
from PIL import Image

from app.core.enums import Preprocessing

#: Matches the confidence token ``tesseract`` emits per word, e.g. ``conf 95``.
_CONFIDENCE_PATTERN = re.compile(r"conf\s+(\d+)")

#: Maximum vertical center delta (as a multiple of reference word height) for merging
#: two TSV line segments onto one horizontal visual row.
_SAME_ROW_VERTICAL_TOLERANCE = 0.45

#: Maximum horizontal overlap (as a multiple of the shorter segment height) allowed when
#: merging two horizontally adjacent TSV segments onto the same row.
_SAME_ROW_MAX_HORIZONTAL_OVERLAP = 0.20

#: Minimum inter-word gap (as a multiple of robust line height) treated as an
#: inter-column break rather than an ordinary single word space. Calibrated against
#: 40 px Aileron renders and 2x upscaled variants: ordinary single spaces (including
#: around ``-`` in ``70 - 99`` and ``12.0 - 15.5``) stay <= ~0.63x height while real
#: column breaks (``Test: ...     Value: ...`` and header columns) are >= 1.26x height.
_COLUMN_GAP_HEIGHT_RATIO = 0.88

#: Approximate proportional width of one space character relative to line font height
#: (9.0 px advance at ~32 px median height in Aileron 40 px) for multi-space emission.
_SPACE_WIDTH_HEIGHT_RATIO = 0.28

#: Upper cap on emitted spaces for wide column gaps so spans stay compact and predictable.
_MAX_COLUMN_SPACES = 16


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


#: Serialises every operation that depends on pytesseract's process-global command.
#:
#: ``pytesseract.pytesseract.tesseract_cmd`` is a single mutable module attribute, and
#: ``get_tesseract_version``, ``image_to_string`` and ``image_to_data`` all read it. Two
#: overlapping OCR requests with *different* executables could therefore interleave: one
#: thread would invoke another's binary, and out-of-order restores could leave the global
#: at an arbitrary value — silently corrupting ``tool_version`` provenance. A re-entrant
#: lock is used because ``run_ocr`` holds it while calling :func:`engine_version`, which
#: takes it again.
#:
#: The lock is process-local. It does not protect against separate *processes* sharing one
#: pytesseract module — each process has its own global, so none is shared.
_ENGINE_LOCK = threading.RLock()


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

    The whole save/select/call/restore span is held under :data:`_ENGINE_LOCK`, so a
    concurrent request cannot swap the global mid-call. The previous value is always
    restored, so one document's engine cannot leak into the next.
    """
    with _ENGINE_LOCK:
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


def _mean_confidence(data: Mapping[str, Sequence[object]]) -> float | None:
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


@dataclass(frozen=True, slots=True)
class _TsvWord:
    """One non-empty recognized word box parsed from Tesseract TSV output."""

    tsv_line_key: tuple[int, int, int] | None
    left: int
    top: int
    width: int
    height: int
    text: str

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def y_center(self) -> float:
        return self.top + (self.height / 2.0)


@dataclass(slots=True)
class _LineSegment:
    """One intermediate visual line segment of TSV word boxes."""

    words: list[_TsvWord]
    y_center: float
    ref_height: float
    min_left: int
    max_right: int


def _coerce_tsv_int(raw: object) -> int | None:
    """Parse an integer TSV cell cleanly, returning ``None`` on invalid values."""
    try:
        return int(float(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _robust_height(words: Sequence[_TsvWord], *, fallback: float) -> float:
    """Return robust median font height for ``words``, ignoring tiny punctuation boxes."""
    alnum_heights = [word.height for word in words if any(ch.isalnum() for ch in word.text)]
    if alnum_heights:
        return max(float(statistics.median(alnum_heights)), 1.0)
    all_heights = [word.height for word in words if word.height > 0]
    if all_heights:
        return max(float(statistics.median(all_heights)), fallback, 1.0)
    return max(fallback, 1.0)


def _segment_y_center(words: Sequence[_TsvWord]) -> float:
    """Return representative vertical midpoint for ``words``, preferring alphanumeric words."""
    alnum = [word.y_center for word in words if any(ch.isalnum() for ch in word.text)]
    centers = alnum or [word.y_center for word in words]
    return float(statistics.median(centers))


def _make_segment(words: list[_TsvWord], *, page_ref_height: float) -> _LineSegment:
    ordered = sorted(words, key=lambda word: (word.left, word.right))
    return _LineSegment(
        words=ordered,
        y_center=_segment_y_center(ordered),
        ref_height=_robust_height(ordered, fallback=page_ref_height),
        min_left=min(word.left for word in ordered),
        max_right=max(word.right for word in ordered),
    )


def _parse_tsv_words(data: Mapping[str, Sequence[object]]) -> list[_TsvWord] | None:
    """Extract word-level TSV boxes from ``image_to_data`` output, or ``None`` if absent."""
    required = ("text", "left", "top", "width", "height")
    if not all(key in data for key in required):
        return None

    texts = data["text"]
    lefts = data["left"]
    tops = data["top"]
    widths = data["width"]
    heights = data["height"]
    row_count = min(len(texts), len(lefts), len(tops), len(widths), len(heights))
    if row_count == 0:
        return None

    levels = data.get("level")
    has_line_ids = all(key in data for key in ("block_num", "par_num", "line_num"))
    blocks = data.get("block_num") if has_line_ids else None
    pars = data.get("par_num") if has_line_ids else None
    lines = data.get("line_num") if has_line_ids else None

    words: list[_TsvWord] = []
    for idx in range(row_count):
        if levels is not None and idx < len(levels):
            lvl = _coerce_tsv_int(levels[idx])
            if lvl is not None and lvl != 5:
                continue

        raw_text = texts[idx]
        if not isinstance(raw_text, str):
            raw_text = str(raw_text or "")
        token = raw_text.strip()
        if not token:
            continue

        left = _coerce_tsv_int(lefts[idx])
        top = _coerce_tsv_int(tops[idx])
        width = _coerce_tsv_int(widths[idx])
        height = _coerce_tsv_int(heights[idx])
        if left is None or top is None or width is None or height is None:
            continue
        if width < 0 or height <= 0:
            continue

        tsv_line_key: tuple[int, int, int] | None = None
        if (
            blocks is not None
            and pars is not None
            and lines is not None
            and idx < len(blocks)
            and idx < len(pars)
            and idx < len(lines)
        ):
            b = _coerce_tsv_int(blocks[idx])
            p = _coerce_tsv_int(pars[idx])
            ln = _coerce_tsv_int(lines[idx])
            if b is not None and p is not None and ln is not None:
                tsv_line_key = (b, p, ln)

        words.append(
            _TsvWord(
                tsv_line_key=tsv_line_key,
                left=left,
                top=top,
                width=width,
                height=height,
                text=token,
            )
        )

    return words or None


def reconstruct_layout_from_tsv(data: Mapping[str, Sequence[object]]) -> str | None:
    """Reconstruct line breaks and inter-column spacing from Tesseract TSV boxes.

    Returns ``None`` when ``data`` does not contain usable word bounding-box geometry
    (so callers can cleanly fall back to ``image_to_string``).
    """
    words = _parse_tsv_words(data)
    if not words:
        return None

    alnum_heights = [word.height for word in words if any(ch.isalnum() for ch in word.text)]
    all_heights = [word.height for word in words if word.height > 0]
    page_ref_height = max(float(statistics.median(alnum_heights or all_heights)), 1.0)

    # Group words belonging to the same TSV line first, then sort segments top-to-bottom
    # and merge split blocks that occupy the same visual baseline without overlapping.
    grouped: dict[tuple[int, int, int, int], list[_TsvWord]] = {}
    for idx, word in enumerate(words):
        key = (*word.tsv_line_key, 0) if word.tsv_line_key is not None else (-1, -1, -1, idx)
        grouped.setdefault(key, []).append(word)

    segments = sorted(
        (_make_segment(group, page_ref_height=page_ref_height) for group in grouped.values()),
        key=lambda seg: (seg.y_center, seg.min_left),
    )

    visual_lines: list[_LineSegment] = []
    for seg in segments:
        if not visual_lines:
            visual_lines.append(seg)
            continue
        prev_seg = visual_lines[-1]
        max_h = max(prev_seg.ref_height, seg.ref_height)
        min_h = min(prev_seg.ref_height, seg.ref_height)
        vertical_delta = abs(seg.y_center - prev_seg.y_center)
        horizontal_overlap = min(prev_seg.max_right, seg.max_right) - max(
            prev_seg.min_left, seg.min_left
        )
        if (
            vertical_delta <= _SAME_ROW_VERTICAL_TOLERANCE * max_h
            and horizontal_overlap <= _SAME_ROW_MAX_HORIZONTAL_OVERLAP * min_h
        ):
            merged_words = [*prev_seg.words, *seg.words]
            visual_lines[-1] = _make_segment(merged_words, page_ref_height=page_ref_height)
        else:
            visual_lines.append(seg)

    rendered_lines: list[str] = []
    for line in visual_lines:
        ordered = line.words
        line_ref_h = line.ref_height
        col_threshold = _COLUMN_GAP_HEIGHT_RATIO * line_ref_h
        space_unit = max(line_ref_h * _SPACE_WIDTH_HEIGHT_RATIO, 1.0)

        parts: list[str] = [ordered[0].text]
        prev_word = ordered[0]
        for word in ordered[1:]:
            gap = word.left - prev_word.right
            if gap >= col_threshold:
                spaces = max(2, min(_MAX_COLUMN_SPACES, round(gap / space_unit)))
                parts.append(" " * spaces)
            else:
                parts.append(" ")
            parts.append(word.text)
            prev_word = word
        rendered_lines.append("".join(parts))

    return "\n".join(rendered_lines)


def run_ocr(
    image: Image.Image,
    *,
    tesseract_cmd: str | None,
    language: str,
    preprocessing: Preprocessing = Preprocessing.NONE,
) -> OcrResult:
    """Run one OCR attempt and return layout-reconstructed text and confidence.

    Raises :class:`OcrUnavailableError` when the engine is missing, so the caller
    maps it to ``E_DEPENDENCY_MISSING`` and marks the document failed rather than
    verified.
    """
    executable = resolve_engine(tesseract_cmd)
    prepared = preprocess(image, preprocessing)

    config = f"--psm 6 -l {language}"
    confidence: float | None = None
    reconstructed_text: str | None = None
    with _engine_selected(executable):
        # Both calls must run inside the selection: pytesseract shells out to the
        # module-global command, so without this the resolved path would be ignored.
        plain_text = pytesseract.image_to_string(prepared, lang=language, config=config, timeout=20)

        try:
            data = pytesseract.image_to_data(
                prepared,
                lang=language,
                config=config,
                output_type=pytesseract.Output.DICT,
                timeout=20,
            )
            if isinstance(data, Mapping):
                confidence = _mean_confidence(data)
                reconstructed_text = reconstruct_layout_from_tsv(data)
        except (OSError, RuntimeError, pytesseract.TesseractError):
            # Confidence and TSV layout are optional when image_to_string succeeded.
            confidence = None
            reconstructed_text = None

    text = reconstructed_text if reconstructed_text is not None else plain_text

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
    "reconstruct_layout_from_tsv",
    "resolve_engine",
    "run_ocr",
]
