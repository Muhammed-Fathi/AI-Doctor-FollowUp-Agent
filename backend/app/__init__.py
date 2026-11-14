"""AI Doctor Follow-Up backend package.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.

Phase 1 contains only the foundation: configuration, database bootstrap, Alembic
baseline and the two public system endpoints (``/health`` and ``/version``).
No patient, authentication, OCR, monitoring or agent code exists yet (P2-P8).
"""

__all__ = ["__version__"]

from app.core.version import APP_VERSION as __version__
