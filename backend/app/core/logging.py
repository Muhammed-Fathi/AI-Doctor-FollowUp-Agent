"""Structured, non-clinical logging setup.

Logs must never contain document text, credentials or patient content
(``REQ-AUDIT-02``, ``AGENTS.md`` §3.1). Phase 1 therefore configures a plain
formatter and only logs operational facts (startup, bind address, DB path).
"""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s :: %(message)s"


def configure_logging(level: str = "info") -> None:
    """Configure the root logger once, writing to stdout.

    Idempotent: calling it twice does not duplicate handlers. Uvicorn keeps its
    own handlers, so the root configuration only affects ``app.*`` loggers.
    """
    root = logging.getLogger()
    if any(getattr(handler, "_app_owned", False) for handler in root.handlers):
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler._app_owned = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level.upper())


__all__ = ["LOG_FORMAT", "configure_logging"]
