"""Text-layer extraction and bounded page handling.

Strategy (``EXTRACTION_PROVENANCE.md`` §2):

* For PDFs, extract the text layer with ``pypdf`` first.
* A page with at least ``text_layer_min_chars`` **non-whitespace** characters
  counts as having a usable text layer.
* Only pages below that threshold are candidates for OCR.

This module never calls a model and never invents text: what ``pypdf`` returns is
what is stored, bounded, with the page index that produced it.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.enums import ExtractionPath


@dataclass(frozen=True, slots=True)
class PageText:
    """Extracted text for one page, with the route that produced it.

    ``char_count`` is the number of **non-whitespace** characters, which is the
    signal the triage rule uses. ``confidence`` is ``None`` for a text layer:
    a text layer has no engine confidence, and inventing one would be a
    fabricated metric (``DATA_DICTIONARY.md`` §2.5).
    """

    page_index: int
    text: str
    extractor: ExtractionPath
    confidence: float | None = None
    tool_version: str | None = None

    @property
    def char_count(self) -> int:
        """Return the non-whitespace character count for this page."""
        return sum(1 for character in self.text if not character.isspace())


def count_non_whitespace(text: str) -> int:
    """Return the number of non-whitespace characters in ``text``."""
    return sum(1 for character in text if not character.isspace())


def extract_pdf_pages(payload: bytes) -> list[PageText]:
    """Return one :class:`PageText` per page of a text-layer PDF.

    A page whose text layer is empty still yields an entry (with empty text), so
    the caller can *select* it for OCR rather than silently losing it. Parser
    failures raise ``ValueError``; the intake validator has already rejected
    structurally invalid PDFs, so reaching that here means the bytes changed.
    """
    try:
        reader = PdfReader(io.BytesIO(payload))
        pages: list[PageText] = []
        for page_index, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            pages.append(
                PageText(
                    page_index=page_index,
                    text=raw,
                    extractor=ExtractionPath.PYPDF,
                    confidence=None,
                )
            )
        return pages
    except (PdfReadError, ValueError, OSError, KeyError, TypeError) as error:
        raise ValueError("pdf text layer could not be read") from error


def pages_needing_ocr(pages: list[PageText], *, min_chars: int) -> list[int]:
    """Return the page indexes whose text layer is below ``min_chars``.

    Deterministic and order-preserving: the same pages always produce the same
    selection, so the retry budget cannot grow (``ADR-0006`` §3.1).
    """
    return [page.page_index for page in pages if page.char_count < min_chars]


def total_char_count(pages: list[PageText]) -> int:
    """Return the total non-whitespace character count across ``pages``."""
    return sum(page.char_count for page in pages)


__all__ = [
    "PageText",
    "count_non_whitespace",
    "extract_pdf_pages",
    "pages_needing_ocr",
    "total_char_count",
]
