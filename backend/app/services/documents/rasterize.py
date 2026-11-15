"""Deterministic PDF rasterization for the OCR path.

Only pages whose text layer is unusable are rasterized. ``pypdfium2`` is used
instead of ``pdf2image``/Poppler (owner decision D-01) because it ships the
PDFium binary as a wheel: no external Poppler install, no ``PATH`` dependency,
and nothing extra for the owner's Windows machine to get wrong.

Bounded on purpose:

* one page at a time, never a whole-document render,
* an explicit pixel cap, checked *before* allocating the bitmap,
* a fixed render scale from configuration, never adaptive.

Rasterizing proves **PDF -> pixels**. It is not evidence of OCR accuracy and is
never reported as such.
"""

from __future__ import annotations

import io

import pypdfium2 as pdfium
from PIL import Image

#: Default render scale. 2.0 is the documented demo value: roughly 144 DPI for a
#: letter page, which is legible for the synthetic fixtures without producing a
#: bitmap large enough to matter on a laptop.
DEFAULT_RENDER_SCALE = 2.0


class RasterizationError(Exception):
    """Raised when a page cannot be rendered within the configured bounds."""


def page_count(payload: bytes) -> int:
    """Return the page count of ``payload`` without rendering anything."""
    try:
        document = pdfium.PdfDocument(io.BytesIO(payload))
        try:
            return len(document)
        finally:
            document.close()
    except Exception as error:  # pragma: no cover - PDFium raises broadly
        raise RasterizationError("pdf could not be opened for rasterization") from error


def render_page(
    payload: bytes,
    *,
    page_index: int,
    max_pixels: int,
    scale: float = DEFAULT_RENDER_SCALE,
) -> Image.Image:
    """Render one page to an RGB :class:`PIL.Image.Image`.

    Raises :class:`RasterizationError` when the page is out of range or the
    rendered bitmap would exceed ``max_pixels``. The pixel check uses the page's
    own geometry before allocating, so an oversized page costs nothing.
    """
    if page_index < 0:
        raise RasterizationError("page index must be non-negative")

    try:
        document = pdfium.PdfDocument(io.BytesIO(payload))
    except Exception as error:
        raise RasterizationError("pdf could not be opened for rasterization") from error

    try:
        if page_index >= len(document):
            raise RasterizationError("page index out of range")
        page = document[page_index]
        width_points, height_points = page.get_size()
        # Point -> pixel at ``scale``. Checked before rendering so a huge page
        # cannot allocate a huge bitmap.
        estimated_pixels = int(width_points * scale) * int(height_points * scale)
        if estimated_pixels > max_pixels:
            raise RasterizationError("rendered page would exceed the pixel cap")
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil().convert("RGB")
    except RasterizationError:
        raise
    except Exception as error:  # pragma: no cover - PDFium raises broadly
        raise RasterizationError("page could not be rendered") from error
    finally:
        document.close()

    if image.width * image.height > max_pixels:
        raise RasterizationError("rendered page would exceed the pixel cap")
    return image


__all__ = ["DEFAULT_RENDER_SCALE", "RasterizationError", "page_count", "render_page"]
