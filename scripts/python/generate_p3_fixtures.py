#!/usr/bin/env python
"""Generate the deterministic synthetic P3 document fixtures.

Owner decision D-04: **the repository commits textual sources, not binaries.**
Report bodies live in ``data/synthetic/documents/sources/*.txt`` and the expected
outcome lives in ``data/synthetic/documents/manifest.json``. This script turns
those sources into real PDF/PNG/JPEG bytes at test time.

Why generate instead of commit:

* a committed binary PDF is unreviewable in a diff;
* the secret/artefact scan treats unknown binaries as suspicious;
* ``REQ-OPS-01`` wants reproducibility, and a generator is reproducible by
  construction while a checked-in blob is only "whatever was uploaded".

Determinism
-----------
Every generator here is byte-deterministic for a given input:

* PDF: hand-built object table, no timestamps, no producer string, no random IDs.
* PNG/JPEG: fixed size, fixed palette, no metadata chunks.

``assert_deterministic()`` is used by the tests to prove it rather than claim it.

Usage::

    python scripts/python/generate_p3_fixtures.py            # verify determinism
    python scripts/python/generate_p3_fixtures.py --out DIR   # write for inspection

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = REPO_ROOT / "data" / "synthetic" / "documents"
SOURCES_DIR = DOCUMENTS_DIR / "sources"

#: A4-ish page box in points, used by every generated PDF.
PAGE_WIDTH = 612
PAGE_HEIGHT = 792

#: Helvetica font object number, fixed so the object table never shifts.
_FONT_OBJECT = 5


def _escape_pdf_text(line: str) -> str:
    """Escape the three characters that are special inside a PDF string."""
    return line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def build_pdf(pages: list[list[str]]) -> bytes:
    """Build a deterministic multi-page text PDF from ``pages``.

    Each inner list is one page's lines. Object layout is fixed:

    ``1`` catalog, ``2`` page tree, then two objects per page
    (page, content), and finally the font.

    Nothing time- or environment-dependent enters the bytes, so two calls with
    the same input return identical output.
    """
    if not pages:
        raise ValueError("a PDF needs at least one page")

    page_object_base = 3
    font_object = page_object_base + 2 * len(pages)

    objects: list[bytes] = []
    kids = " ".join(f"{page_object_base + index * 2} 0 R" for index in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())

    for index, lines in enumerate(pages):
        content = ["BT", "/F1 12 Tf", "14 TL", f"40 {PAGE_HEIGHT - 60} Td"]
        for line in lines:
            content.append(f"({_escape_pdf_text(line)}) Tj")
            content.append("T*")
        content.append("ET")
        stream = "\n".join(content).encode("latin-1")

        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_object} 0 R >> >> "
            f"/Contents {page_object_base + index * 2 + 1} 0 R >>"
        )
        objects.append(page_object.encode())
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return bytes(out)


def read_source(name: str) -> list[str]:
    """Return the lines of ``data/synthetic/documents/sources/<name>``."""
    path = SOURCES_DIR / name
    return path.read_text(encoding="utf-8").rstrip("\n").split("\n")


def build_report_pdf(source_name: str) -> bytes:
    """Build a one-page PDF from a committed text source."""
    return build_pdf([read_source(source_name)])


def build_blank_pdf(page_count: int) -> bytes:
    """Build a PDF with ``page_count`` near-empty pages.

    Used by the page-limit fixture. Each page carries one short line so the file
    stays structurally valid without being a text-layer candidate.
    """
    return build_pdf([[f"page {index}"] for index in range(page_count)])


def build_oversized_pdf(target_bytes: int) -> bytes:
    """Build a structurally valid PDF padded past ``target_bytes``.

    The padding is a PDF comment placed immediately after the header, so the
    document still parses while exceeding the size cap. That is exactly the
    ``NEG-04`` shape: a file that a naive extension check would accept.
    """
    base = build_pdf([["SYNTHETIC DEMO DATA - oversized fixture"]])
    header, remainder = base[:9], base[9:]
    padding_length = max(0, target_bytes - len(base))
    padding = b"%" + b"A" * max(0, padding_length - 1) + b"\n"
    return header + padding + remainder


def build_scan_image(source_name: str, *, size: tuple[int, int] = (1000, 500), fmt: str = "PNG"):
    """Render a text source to a ``PIL.Image``, standing in for a scan.

    This produces an **image of text**, not an OCR result. Whether a real engine
    can read it is measured separately on the owner's machine (``OCR-LIVE-01``);
    nothing here asserts that it can.
    """
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    line_height = 18
    for index, line in enumerate(read_source(source_name)):
        draw.text((20, 20 + index * line_height), line, fill="black")
    if fmt == "JPEG":
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")
    return image


#: Point size for the legible render. Tesseract needs roughly 30 px of glyph height to
#: identify characters reliably; the default PIL bitmap font is ~10 px, which is why the
#: original GOLD-EX-11 sample was unreadable in the owner's Windows run.
LEGIBLE_FONT_SIZE = 40

#: Extra whitespace between lines, in pixels, so descenders and the baseline stay clean.
LEGIBLE_LINE_SPACING = 18


def legible_font(size: int = LEGIBLE_FONT_SIZE):
    """Return a scalable TrueType font for the legible OCR render.

    ``PIL.ImageFont.load_default(size=...)`` loads **Aileron Regular**, which ships
    inside Pillow itself (added in Pillow 10.1) — so this needs no bundled font file, no
    system font, and no extra dependency. That matters for a repository that commits no
    binaries: the licence travels with Pillow, and rendering stays byte-identical across
    machines.

    Pillow older than 10.1 would return the legacy bitmap font here, which is exactly the
    illegible case this fixture exists to avoid — hence the explicit guard.
    """
    from PIL import ImageFont

    try:
        font = ImageFont.load_default(size=size)
    except TypeError as error:  # pragma: no cover - only on Pillow < 10.1
        raise RuntimeError(
            "a scalable default font requires Pillow >= 10.1; the legible OCR fixture "
            "cannot be rendered with the legacy bitmap font"
        ) from error

    if isinstance(font, ImageFont.ImageFont) and not hasattr(font, "path"):
        # The legacy bitmap font has no scalable metrics; refusing is safer than
        # silently producing the fixture that already failed on Windows.
        raise RuntimeError("load_default() returned a bitmap font, not a TrueType face")

    return font


def build_legible_scan_image(source_name: str, *, fmt: str = "PNG") -> bytes:
    """Render ``source_name`` at a size Tesseract can read reliably.

    Deterministic: fixed canvas, fixed font (Pillow's bundled Aileron), fixed size and
    no metadata. The point is legibility, **not** influencing which character the engine
    sees — the source keeps its literal ``1O5``, and whether Tesseract preserves or
    substitutes it is measured, never engineered.
    """
    from PIL import Image, ImageDraw

    lines = read_source(source_name)
    font = legible_font()

    # Size the canvas from real text metrics so no line is clipped on any platform.
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    line_height = LEGIBLE_FONT_SIZE + LEGIBLE_LINE_SPACING
    widest = max(
        (probe.textbbox((0, 0), line, font=font)[2] for line in lines),
        default=0,
    )
    width = max(1200, widest + 120)
    height = max(400, len(lines) * line_height + 120)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((60, 60 + index * line_height), line, font=font, fill="black")

    if fmt == "JPEG":
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()
    if fmt == "PNG":
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=False)
        return buffer.getvalue()
    raise ValueError(f"unsupported format: {fmt}")


def image_bytes(source_name: str, *, fmt: str = "PNG") -> bytes:
    """Return deterministic PNG or JPEG bytes for a committed text source."""
    image = build_scan_image(source_name, fmt=fmt)
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def assert_deterministic() -> list[str]:
    """Prove that every generator is deterministic, and return a summary."""
    checks: list[tuple[str, bytes, bytes]] = [
        (
            "report_pdf",
            build_report_pdf("report_a_clean.txt"),
            build_report_pdf("report_a_clean.txt"),
        ),
        ("blank_pdf", build_blank_pdf(25), build_blank_pdf(25)),
        (
            "oversized_pdf",
            build_oversized_pdf(12 * 1024 * 1024),
            build_oversized_pdf(12 * 1024 * 1024),
        ),
        (
            "png",
            image_bytes("report_a_clean.txt", fmt="PNG"),
            image_bytes("report_a_clean.txt", fmt="PNG"),
        ),
        (
            "jpeg",
            image_bytes("report_a_clean.txt", fmt="JPEG"),
            image_bytes("report_a_clean.txt", fmt="JPEG"),
        ),
        (
            "legible_png",
            build_legible_scan_image("report_a_glucose.txt", fmt="PNG"),
            build_legible_scan_image("report_a_glucose.txt", fmt="PNG"),
        ),
        (
            "legible_jpeg",
            build_legible_scan_image("report_a_glucose.txt", fmt="JPEG"),
            build_legible_scan_image("report_a_glucose.txt", fmt="JPEG"),
        ),
    ]
    summary: list[str] = []
    failures: list[str] = []
    for name, first, second in checks:
        same = first == second
        summary.append(f"{name}: {len(first)} bytes, deterministic={same}")
        if not same:
            failures.append(name)
    if failures:
        raise AssertionError(f"non-deterministic generators: {failures}")
    return summary


def main(argv: list[str]) -> int:
    """Verify determinism and optionally write the bytes for inspection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="write generated bytes here")
    args = parser.parse_args(argv[1:])

    try:
        for line in assert_deterministic():
            print(line)
    except AssertionError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "report_a_clean.pdf").write_bytes(build_report_pdf("report_a_clean.txt"))
        (args.out / "report_a_clean.png").write_bytes(image_bytes("report_a_clean.txt", fmt="PNG"))
        (args.out / "report_a_clean.jpg").write_bytes(image_bytes("report_a_clean.txt", fmt="JPEG"))
        print(f"wrote fixtures to {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
