"""Filesystem layout helpers.

All paths are resolved relative to the repository root so that the application
behaves identically no matter which directory it is started from (including
Windows paths containing spaces).
"""

from __future__ import annotations

from pathlib import Path

# backend/app/core/paths.py -> backend/app/core -> backend/app -> backend -> repo root
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: Gitignored runtime directory: SQLite database, PID files, logs, uploads.
RUNTIME_DIR: Path = REPO_ROOT / "data" / "runtime"

#: Gitignored directory for uploaded synthetic documents (used from P3).
UPLOAD_DIR: Path = RUNTIME_DIR / "uploads"

#: Tracked synthetic fixture directory: the only patient-shaped data in git.
SYNTHETIC_DATA_DIR: Path = REPO_ROOT / "data" / "synthetic"


def ensure_runtime_dir() -> Path:
    """Create the runtime directory if it is missing and return it."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


__all__ = [
    "REPO_ROOT",
    "RUNTIME_DIR",
    "SYNTHETIC_DATA_DIR",
    "UPLOAD_DIR",
    "ensure_runtime_dir",
]
