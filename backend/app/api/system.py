"""Public system endpoints: ``GET /health`` and ``GET /version``.

These are the only endpoints implemented in Phase 1 (``MASTER_PLAN.md`` §5,
P1). They are public by contract (``API_CONTRACT.md`` §2.1) and must not leak
secrets, file paths or exception text.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.version import (
    API_VERSION,
    APP_VERSION,
    DEMO_NOTICE,
    POLICY_VERSION,
    WORKFLOW_VERSION,
)
from app.db.session import check_database
from app.schemas.system import DependencyState, Health, VersionInfo

#: Both P1 operations are public by contract. Declaring ``security: []``
#: explicitly documents that in the generated OpenAPI schema instead of leaving
#: it to the reader's assumption (``API_CONTRACT.md`` §2.1).
_PUBLIC = {"security": []}

router = APIRouter(tags=["system"])

#: Dependency components that are not implemented yet (P3/P5). They are reported
#: as ``not_configured`` — an honest state, never a fake ``ok``.
_UNIMPLEMENTED: DependencyState = "not_configured"


@router.get(
    "/health",
    response_model=Health,
    summary="Liveness and dependency status",
    description=(
        "Process liveness plus dependency facts. Never reports a clinical or "
        "demo-success state, and a missing local model never fails liveness."
    ),
    openapi_extra=_PUBLIC,
)
def get_health() -> Health:
    """Return liveness with honest dependency states."""
    db_state: DependencyState = "ok" if check_database() else "unavailable"
    status: str = "ok" if db_state == "ok" else "degraded"
    return Health(
        status="ok" if status == "ok" else "degraded",
        version=APP_VERSION,
        db=db_state,
        ollama=_UNIMPLEMENTED,  # P5: OllamaProvider health probe
        tesseract=_UNIMPLEMENTED,  # P3: OCR engine availability probe
        disclaimer=DEMO_NOTICE,
    )


@router.get(
    "/version",
    response_model=VersionInfo,
    summary="Build and contract versions",
    description="Application, API, workflow and demo-policy versions plus the build SHA.",
    openapi_extra=_PUBLIC,
)
def get_version() -> VersionInfo:
    """Return deterministic version metadata resolved from constants and build SHA."""
    settings = get_settings()
    return VersionInfo(
        app_version=APP_VERSION,
        api_version=API_VERSION,
        workflow_version=WORKFLOW_VERSION,
        policy_version=POLICY_VERSION,
        git_sha=settings.git_sha,
    )


__all__ = ["router"]
