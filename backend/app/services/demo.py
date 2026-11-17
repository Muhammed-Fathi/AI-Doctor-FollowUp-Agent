"""Demo administration: guarded reset and seeded-case reporting.

The reset is the most destructive operation in the MVP, so it is guarded three
times over (``US-12``, ``THREAT_MODEL.md`` T-15):

1. the caller must hold the ``demo_admin`` role,
2. ``DEMO_MODE`` must be enabled locally (``NEG-12`` semantics),
3. the operation refuses while workflow state would make a rebuild unsafe.

Point 3 cannot be evaluated in P2 — ``workflow_run`` arrives in P5 — so
:func:`has_active_workflow_state` returns ``False`` with an explicit note instead
of silently inventing a table. The guard is wired now so P5 only has to replace
one function body, and the limitation is reported rather than glossed over.

What a reset removes: synthetic accounts, patients, encounters, observations,
sessions, check-in replay records, and synthetic document/extraction/page-text/
verification rows (when P3 tables are migrated). What it keeps: the audit trail
(the evidence of what the demo did) and every file on disk. It never deletes a
database file, an upload, a log or an unrelated path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, require_demo_admin
from app.db.models import AuditEvent
from app.services.audit import EVENT_DEMO_RESET, append_audit_event
from app.services.seed import SeedConfigurationError, reset_demo_data

#: Reasons a reset can be refused, recorded in the audit row when relevant.
REASON_MISSING_SEED_PASSWORD = "seed_password_not_configured"
REASON_ACTIVE_WORKFLOW = "active_workflow_run"


@dataclass(frozen=True, slots=True)
class DemoResetOutcome:
    """Result of a successful reset."""

    reset_at: datetime
    cases_loaded: tuple[str, ...]
    audit_events_retained: int


def has_active_workflow_state(db: Session) -> bool:
    """Return ``True`` when a run is ``running``/``awaiting_decision``/…

    P2 has no workflow state: the ``workflow_run`` table is created in P5. The
    guard therefore reports "nothing active" honestly instead of querying a table
    that does not exist, and P5 replaces this body with the real check.
    """
    return False


def reset_demo(
    db: Session,
    *,
    principal: Principal,
    demo_mode: bool,
    seed_password: str | None,
    now: datetime,
    request_id: str,
) -> DemoResetOutcome:
    """Reset the synthetic demo dataset.

    Raises:
        ApiError: ``403 E_FORBIDDEN`` for a non-admin, ``403
            E_DEMO_MODE_REQUIRED`` when demo mode is off, ``409`` when a run is
            active, ``500 E_INTERNAL`` when the local seed password is missing
            (a configuration problem, reported without echoing configuration).
    """
    require_demo_admin(principal, demo_mode=demo_mode)

    if has_active_workflow_state(db):
        raise ApiError(
            409,
            ErrorCode.INTERNAL,
            "A workflow run is active; reset is refused.",
            title="Reset refused",
        )

    if seed_password is None or not seed_password.strip():
        # Local operator error, not a client error. No secret value is echoed.
        raise ApiError(
            500,
            ErrorCode.INTERNAL,
            "Demo seeding requires DEMO_SEED_PASSWORD to be configured locally.",
        )

    retained = len(db.execute(select(AuditEvent.id)).scalars().all())
    try:
        result = reset_demo_data(db, password=seed_password, now=now)
    except SeedConfigurationError as error:
        raise ApiError(500, ErrorCode.INTERNAL, "Demo fixtures could not be loaded.") from error

    append_audit_event(
        db,
        event_type=EVENT_DEMO_RESET,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        subject_type="demo",
        subject_id=None,
        detail_fragments=(
            f"cases={','.join(result.cases_loaded)}",
            f"audit_retained={retained}",
        ),
    )
    db.flush()

    return DemoResetOutcome(
        reset_at=now,
        cases_loaded=result.cases_loaded,
        audit_events_retained=retained,
    )


__all__ = [
    "REASON_ACTIVE_WORKFLOW",
    "REASON_MISSING_SEED_PASSWORD",
    "DemoResetOutcome",
    "has_active_workflow_state",
    "reset_demo",
]
