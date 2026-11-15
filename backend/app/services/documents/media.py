"""Byte-level media validation for synthetic uploads.

The intake order is fixed by ``EXTRACTION_PROVENANCE.md`` §1 and
``API_CONTRACT.md`` §2.4:

```text
size  -> magic bytes -> MIME allowlist -> structural parse
      -> page count / image pixels  -> sha256  -> store
```

Nothing here trusts the filename or the declared extension. A `.pdf` name over
PNG bytes is ``E_UNSUPPORTED_MEDIA`` (``NEG-03``), not a parse attempt.

Owner decision D-10: a **structural parse failure during upload validation does
not create a document row**. Validation raises before any persistence happens,
so a rejected upload leaves no trace beyond the audit event.
"""

from __future__ import annotations

import hashlib
import io

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.enums import DocumentMimeType
from app.core.errors import (
    FILE_TOO_LARGE_DETAIL,
    PAGE_LIMIT_EXCEEDED_DETAIL,
    PARSE_FAILED_DETAIL,
    UNSUPPORTED_MEDIA_DETAIL,
    ErrorCode,
    document_error,
)

#: Magic-byte signatures. A file must match one of these **and** parse
#: structurally; the extension is irrelevant.
_PDF_MAGIC = b"%PDF-"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"

#: Bytes needed to sniff every accepted signature.
SNIFF_LENGTH = 8


class ValidatedUpload:
    """The outcome of byte-level validation for one accepted upload.

    Only values derived from the **bytes** appear here; the client filename is
    deliberately absent, because it is metadata that intake sanitizes separately.
    """

    __slots__ = ("mime_type", "page_count", "sha256", "size_bytes")

    def __init__(
        self, *, mime_type: str, page_count: int | None, size_bytes: int, sha256: str
    ) -> None:
        self.mime_type = mime_type
        self.page_count = page_count
        self.size_bytes = size_bytes
        self.sha256 = sha256

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"ValidatedUpload(mime_type={self.mime_type!r}, "
            f"page_count={self.page_count!r}, size_bytes={self.size_bytes!r})"
        )


def sha256_of(payload: bytes) -> str:
    """Return the lowercase hex SHA-256 of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


def sniff_mime_type(payload: bytes) -> str:
    """Return the MIME type implied by the leading bytes of ``payload``.

    Raises ``415 E_UNSUPPORTED_MEDIA`` for anything unrecognised. This is the
    only place a MIME type is decided.
    """
    head = payload[:SNIFF_LENGTH]
    if head.startswith(_PDF_MAGIC):
        return DocumentMimeType.PDF.value
    if head.startswith(_PNG_MAGIC):
        return DocumentMimeType.PNG.value
    if head.startswith(_JPEG_MAGIC):
        return DocumentMimeType.JPEG.value
    raise document_error(ErrorCode.UNSUPPORTED_MEDIA, UNSUPPORTED_MEDIA_DETAIL)


def _check_declared_type(declared_type: str | None, detected: str) -> None:
    """Reject a client that declares a type the bytes do not support.

    A declaration is optional; when present it must agree with the magic bytes.
    A mismatch is the exact ``NEG-03`` case (``.pdf`` extension/declared type
    over PNG bytes) and is reported as unsupported media rather than parsed.
    """
    if declared_type is None:
        return
    if declared_type != detected:
        raise document_error(ErrorCode.UNSUPPORTED_MEDIA, UNSUPPORTED_MEDIA_DETAIL)


def _validate_pdf(payload: bytes, *, max_pages: int) -> int:
    """Structurally parse a PDF and return its page count.

    Encrypted, truncated, zero-page and malformed PDFs are rejected outright
    (``EXTRACTION_PROVENANCE.md`` §1 rule 2) — never "best effort parsed".
    """
    try:
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            # Do not attempt decryption: a password-protected report is not a
            # file this demo process. Reject rather than silently try to crack.
            raise document_error(ErrorCode.UNSUPPORTED_MEDIA, UNSUPPORTED_MEDIA_DETAIL)
        page_count = len(reader.pages)
    except (PdfReadError, ValueError, OSError, KeyError, TypeError):
        # ``pypdf`` raises a family of errors for malformed input; all of them
        # mean the same thing to the client. Never let a parser exception escape
        # as a 500.
        raise document_error(ErrorCode.PARSE_FAILED, PARSE_FAILED_DETAIL) from None

    if page_count == 0:
        raise document_error(ErrorCode.PARSE_FAILED, PARSE_FAILED_DETAIL)
    if page_count > max_pages:
        raise document_error(ErrorCode.PAGE_LIMIT_EXCEEDED, PAGE_LIMIT_EXCEEDED_DETAIL)
    return page_count


def _validate_image(payload: bytes, *, max_pixels: int) -> None:
    """Decode an image header and enforce the pixel cap.

    ``Image.open`` reads the header lazily; ``verify()`` then checks the encoded
    data. The pixel cap runs **before** a full decode so a decompression bomb
    cannot exhaust memory.
    """
    try:
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise document_error(ErrorCode.PARSE_FAILED, PARSE_FAILED_DETAIL)
            if width * height > max_pixels:
                raise document_error(ErrorCode.PAGE_LIMIT_EXCEEDED, PAGE_LIMIT_EXCEEDED_DETAIL)
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise document_error(ErrorCode.PARSE_FAILED, PARSE_FAILED_DETAIL) from None


def validate_upload(
    payload: bytes,
    *,
    declared_type: str | None,
    max_bytes: int,
    max_pages: int,
    max_pixels: int,
) -> ValidatedUpload:
    """Run the fixed intake validation chain and return verified metadata.

    No persistence happens here. Every failure raises the contract's typed
    ``ApiError``; the caller writes a single audit event and returns it.
    """
    size_bytes = len(payload)

    # 1. Size, before any parser sees the bytes.
    if size_bytes == 0:
        raise document_error(ErrorCode.PARSE_FAILED, PARSE_FAILED_DETAIL)
    if size_bytes > max_bytes:
        raise document_error(ErrorCode.FILE_TOO_LARGE, FILE_TOO_LARGE_DETAIL)

    # 2-3. Magic bytes decide the type; the declaration must agree.
    detected = sniff_mime_type(payload)
    _check_declared_type(declared_type, detected)

    # 4-5. Structural parse plus bounds.
    page_count: int | None
    if detected == DocumentMimeType.PDF.value:
        page_count = _validate_pdf(payload, max_pages=max_pages)
    else:
        _validate_image(payload, max_pixels=max_pixels)
        page_count = None

    return ValidatedUpload(
        mime_type=detected,
        page_count=page_count,
        size_bytes=size_bytes,
        sha256=sha256_of(payload),
    )


__all__ = [
    "SNIFF_LENGTH",
    "ValidatedUpload",
    "sha256_of",
    "sniff_mime_type",
    "validate_upload",
]
