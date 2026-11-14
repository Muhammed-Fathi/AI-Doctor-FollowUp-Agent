"""Opaque, stateless pagination cursors.

``API_CONTRACT.md`` §1 requires ``?limit=`` / ``?cursor=`` and a ``next_cursor``
in the response. Cursors are an encoding of the last row's sort key — not an
offset — so inserting a row between two page requests cannot duplicate or skip an
entry. Encoding is deliberately opaque (base64url of ``key|id``) so a client
treats it as a token rather than a query language.

Invalid or tampered cursors raise ``400 E_VALIDATION``; a malformed cursor is
never silently treated as "first page", because that would hide a client bug
behind a misleadingly successful response.
"""

from __future__ import annotations

import base64
import binascii

from app.core.errors import ApiError, ErrorCode

#: Maximum length of a cursor field before decoding is attempted.
MAX_CURSOR_FIELD_LENGTH: int = 64

_SEPARATOR = "|"


def encode_cursor(primary: str, row_id: str) -> str:
    """Encode a sort key plus row id into an opaque cursor."""
    raw = f"{primary}{_SEPARATOR}{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode a cursor, raising ``400 E_VALIDATION`` when it is not well formed."""
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode()
    except (UnicodeDecodeError, binascii.Error, ValueError):
        raise _invalid_cursor() from None

    primary, separator, row_id = decoded.partition(_SEPARATOR)
    if not separator or not primary or not row_id:
        raise _invalid_cursor()
    if len(primary) > MAX_CURSOR_FIELD_LENGTH or len(row_id) > MAX_CURSOR_FIELD_LENGTH:
        raise _invalid_cursor()
    return primary, row_id


def _invalid_cursor() -> ApiError:
    return ApiError(400, ErrorCode.VALIDATION, "The pagination cursor is not valid.")


__all__ = ["MAX_CURSOR_FIELD_LENGTH", "decode_cursor", "encode_cursor"]
