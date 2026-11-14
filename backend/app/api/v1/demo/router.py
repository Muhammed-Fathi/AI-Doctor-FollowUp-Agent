"""Demo administration (``API_CONTRACT.md`` §2.6).

Only ``POST /api/v1/demo/reset`` exists. It is guarded three times over:

1. caller must hold the ``demo_admin`` role — enforced by ``services.demo``,
2. ``DEMO_MODE`` must be ``true`` — otherwise ``403 E_DEMO_MODE_REQUIRED``,
3. ``DEMO_SEED_PASSWORD`` must be configured locally — otherwise a ``500`` that
   never echoes configuration.

The reset rebuilds the synthetic dataset from the tracked fixtures and keeps the
audit trail, appending a ``demo.reset`` row.

``GET /api/v1/demo/status`` is **not implemented** (``OQ-P2-01``): the accepted
response schema requires a drafting-provider status whose enum only admits
components introduced in P5, and answering it in P2 would assert a component that
does not exist. ``POST /api/v1/demo/seed`` does not exist in any phase; first-run
accounts are created by the local ``python -m app.services.seed`` bootstrap.
"""

from __future__ import annotations

from fastapi import APIRouter, Security

from app.api.v1.auth.dependencies import (
    AppSettings,
    DbSession,
    Now,
    PrincipalDep,
    RequestId,
    bearer_scheme,
)
from app.schemas.patient import DemoResetResponse
from app.services.demo import reset_demo

router = APIRouter(
    prefix="/api/v1/demo",
    tags=["demo"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_RESET = "POST /api/v1/demo/reset"


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    summary="Reset the synthetic demo dataset",
    description=(
        "Admin-only and demo-mode-only. Deletes application rows, reseeds the "
        "tracked fixtures and keeps the audit trail. Never deletes files or the "
        "database."
    ),
    responses={
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Not a demo admin, or demo mode is disabled"},
        409: {"description": "A workflow run is active"},
    },
)
def reset(
    principal: PrincipalDep,
    db: DbSession,
    settings: AppSettings,
    now: Now,
    request_id: RequestId,
) -> DemoResetResponse:
    """Reset the demo dataset and report what was loaded."""
    password = (
        settings.demo_seed_password.get_secret_value() if settings.demo_seed_password else None
    )
    outcome = reset_demo(
        db,
        principal=principal,
        demo_mode=settings.demo_mode,
        seed_password=password,
        now=now,
        request_id=request_id,
    )
    return DemoResetResponse(
        reset_at=outcome.reset_at,
        cases_loaded=list(outcome.cases_loaded),
        disclaimer=("Synthetic demo data only. Educational use; not for clinical decisions."),
    )


__all__ = ["ROUTE_RESET", "router"]
