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

#: Dependency components that are not implemented yet (P5). They are reported
#: as ``not_configured`` — an honest state, never a fake ``ok``.
_UNIMPLEMENTED: DependencyState = "not_configured"


def _tesseract_state() -> DependencyState:
    """Report the local OCR engine truthfully.

    Three states, each meaning exactly one thing:

    * ``ok`` — an engine was located and reported a version;
    * ``not_configured`` — no engine path is configured on this host, so OCR was
      never attempted (the default for a sandbox or CI run);
    * ``unavailable`` — a path *is* configured but the engine could not be run.

    The probe never raises: liveness must not fail because a local binary is
    missing (``API_CONTRACT.md`` §2.1). It also never claims ``ok`` without having
    asked the engine for its version, so a stale config cannot produce a false
    positive.
    """
    settings = get_settings()
    if not settings.tesseract_cmd:
        return "not_configured"

    from app.services.documents.ocr import engine_version

    return "ok" if engine_version(settings.tesseract_cmd) else "unavailable"


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
        tesseract=_tesseract_state(),
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
