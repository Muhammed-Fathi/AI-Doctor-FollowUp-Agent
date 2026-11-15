"""Secure storage for uploaded synthetic documents.

Everything an attacker could influence about a filesystem path is removed here,
in one module, so the rest of the pipeline never builds a path from user input.

Rules (``EXTRACTION_PROVENANCE.md`` §1 rules 1-4):

1. The stored filename is **generated** (UUID + canonical extension). The client
   filename is metadata only.
2. The client filename is sanitized to a bounded, separator-free string. It is
   never used to build a path, and it is never trusted for type detection.
3. Every write is confined to the gitignored runtime upload directory. The
   resolved parent must still be that directory after following symlinks, so a
   symlink planted in the directory cannot redirect a write.
4. Nothing here executes, shells out to, or renders the file.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.core.paths import UPLOAD_DIR

#: Canonical extension per accepted MIME type. The extension is derived from the
#: *magic bytes*, never from the client-supplied name.
EXTENSION_BY_MIME: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

#: Characters that survive sanitisation. Everything else becomes ``_``.
_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")

#: Control characters, including NUL, are always stripped.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")

#: Longest original filename kept as metadata (``document.original_filename``).
MAX_FILENAME_LENGTH = 255


class UnsafePathError(Exception):
    """Raised when a write would escape the runtime upload directory.

    This is a programming-error guard, not a client-facing error: a client can
    never trigger it because no client value reaches a path.
    """


def sanitize_filename(raw: str | None) -> str:
    """Return a bounded, separator-free display name for ``raw``.

    The result is metadata only. It is safe to store and to echo back in
    ``DocumentMeta.filename`` because it contains no path separator, no control
    character and no leading dot run (so it can never be ``..``).
    """
    candidate = _CONTROL_CHARS.sub("", raw or "")
    # Strip any directory component the client may have sent, on either
    # separator convention. ``PurePosixPath``/``PureWindowsPath`` both reduce to
    # the last component for the common traversal shapes; doing it twice covers
    # a client that sends backslashes on a POSIX server.
    candidate = candidate.replace("\\", "/").split("/")[-1]
    candidate = _SAFE_FILENAME_CHARS.sub("_", candidate).strip()
    # Collapse a leading run of dots so the result can never be ``.`` or ``..``.
    candidate = candidate.lstrip(".").strip()
    if not candidate:
        return "upload"
    return candidate[:MAX_FILENAME_LENGTH]


def generate_stored_name(mime_type: str) -> str:
    """Return a fresh, unpredictable stored filename for ``mime_type``."""
    try:
        extension = EXTENSION_BY_MIME[mime_type]
    except KeyError:  # pragma: no cover - guarded by the MIME allowlist
        raise UnsafePathError(f"no canonical extension for {mime_type!r}") from None
    return f"{uuid.uuid4().hex}{extension}"


def _resolved_upload_root(upload_dir: str | None = None) -> Path:
    """Return the resolved upload directory, creating it if necessary.

    ``upload_dir`` is the configured root (``Settings.upload_dir``). When it is
    unset the gitignored runtime default is used. The root is resolved *once* and
    every candidate target is compared against it, so a configured directory
    cannot widen the escape check.
    """
    root = Path(upload_dir) if upload_dir else UPLOAD_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def write_document(stored_name: str, payload: bytes, *, upload_dir: str | None = None) -> Path:
    """Write ``payload`` under the runtime upload directory and return its path.

    ``stored_name`` must come from :func:`generate_stored_name`; it is validated
    anyway so a future caller cannot pass a hand-built name and reintroduce
    traversal. Raises :class:`UnsafePathError` when the target would fall outside
    the upload directory.
    """
    if not stored_name or "/" in stored_name or "\\" in stored_name or stored_name.startswith("."):
        raise UnsafePathError("stored name must be a generated basename")

    root = _resolved_upload_root(upload_dir)
    target = (root / stored_name).resolve()
    if target.parent != root:
        raise UnsafePathError("resolved path escapes the upload directory")

    # Refuse to follow a symlink that somehow exists at the target.
    if target.is_symlink():  # pragma: no cover - defensive
        raise UnsafePathError("refusing to write through a symlink")

    target.write_bytes(payload)
    return target


def resolve_for_read(stored_path: str, *, upload_dir: str | None = None) -> Path:
    """Return the on-disk path for a stored document, or raise ``FileNotFoundError``.

    ``stored_path`` comes from the database, which only ever holds a generated
    basename. It is re-validated so a corrupted or tampered row cannot read
    outside the upload directory.
    """
    if not stored_path or "/" in stored_path or "\\" in stored_path or stored_path.startswith("."):
        raise FileNotFoundError("invalid stored path")

    root = _resolved_upload_root(upload_dir)
    target = (root / stored_path).resolve()
    if target.parent != root:
        raise FileNotFoundError("stored path escapes the upload directory")
    if not target.is_file():
        raise FileNotFoundError("stored document is missing")
    return target


__all__ = [
    "EXTENSION_BY_MIME",
    "MAX_FILENAME_LENGTH",
    "UnsafePathError",
    "generate_stored_name",
    "resolve_for_read",
    "sanitize_filename",
    "write_document",
]
