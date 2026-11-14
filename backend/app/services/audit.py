"""Append-only audit trail.

``REQ-AUDIT-01`` requires actor, timestamp and run/request context for access
events; ``REQ-AUDIT-02`` forbids document text, credentials and tokens in the
record. This module is the **only** writer of ``audit_event`` rows and exposes no
update or delete helper, so an audit row cannot be rewritten by application code.

Safety rules enforced here, not just documented:

* ``safe_detail`` is composed from literals, enum values and validated ids. It is
  never built from a request body, a password, a token or a free-text note.
* Every row has a deterministic ``idempotency_key``; a replay of the same event
  in the same request collides on the unique index instead of appending twice.
* Denials record the **route template** (no path parameters with real record
  ids) plus a machine-readable reason — enough for `AUD-01`, nothing more.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import format_utc
from app.core.enums import ActorType, AuditOutcome
from app.db.models import AuditEvent, new_uuid

#: Longest ``safe_detail`` the column accepts (``DATA_DICTIONARY.md`` §2.17).
SAFE_DETAIL_MAX: int = 500

#: Event type vocabulary used by P2. Namespaced so P3+ can extend it additively.
EVENT_ACCESS_DENIED = "access.denied"
EVENT_AUTH_LOGIN = "auth.login"
EVENT_AUTH_LOGIN_FAILED = "auth.login_failed"
EVENT_AUTH_LOGOUT = "auth.logout"
EVENT_DEMO_RESET = "demo.reset"
EVENT_DEMO_SEEDED = "demo.seeded"
EVENT_CHECKIN_CREATED = "checkin.created"

#: Reasons recorded on ``access.denied`` rows (stable, enum-like).
REASON_NOT_ASSIGNED = "patient_not_assigned"
REASON_NOT_SELF_SCOPE = "not_self_scope"
REASON_ROLE_NOT_ALLOWED = "role_not_allowed"
REASON_DEMO_MODE_DISABLED = "demo_mode_disabled"


def derive_audit_key(
    *,
    event_type: str,
    actor_type: ActorType,
    actor_id: str | None,
    outcome: AuditOutcome,
    subject_type: str | None,
    subject_id: str | None,
    request_id: str,
) -> str:
    """Return the deterministic idempotency key for one audit event.

    The inputs are immutable facts of the request, never a freshly generated row
    id, so a retried request computes the same key and cannot append a duplicate
    (``AGENTS.md`` §3.2).
    """
    parts = (
        event_type,
        actor_type.value,
        actor_id or "-",
        outcome.value,
        subject_type or "-",
        subject_id or "-",
        request_id,
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def safe_detail(*fragments: str) -> str:
    """Join ``fragments`` into a bounded, single-line ``safe_detail`` value.

    Callers pass keys/values they constructed themselves (route template, reason
    code, enum name). The result is whitespace-collapsed and truncated so a
    pathological input can never exceed the column or smuggle a multi-line
    payload into a log view.
    """
    joined = "; ".join(fragment.strip() for fragment in fragments if fragment and fragment.strip())
    collapsed = " ".join(joined.split())
    return collapsed[:SAFE_DETAIL_MAX]


def append_audit_event(
    db: Session,
    *,
    event_type: str,
    actor_type: ActorType,
    actor_id: str | None,
    outcome: AuditOutcome,
    request_id: str,
    now: datetime,
    patient_id: str | None = None,
    workflow_run_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    detail_fragments: tuple[str, ...] = (),
) -> AuditEvent:
    """Append one audit row to ``db`` and return it.

    The caller owns the transaction: the row commits with the business change it
    describes, so a denial cannot be recorded without its request and a success
    cannot be lost if the audit insert fails.

    Appending is idempotent per derived key: a retried request recomputes the same
    ``idempotency_key`` and gets the already-stored row back instead of a second
    one, so the trail stays append-only *and* duplicate-free.
    """
    idempotency_key = derive_audit_key(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        outcome=outcome,
        subject_type=subject_type,
        subject_id=subject_id,
        request_id=request_id,
    )
    existing = db.execute(
        select(AuditEvent).where(AuditEvent.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    event = AuditEvent(
        id=new_uuid(),
        event_type=event_type,
        actor_type=actor_type.value,
        actor_id=actor_id,
        patient_id=patient_id,
        workflow_run_id=workflow_run_id,
        subject_type=subject_type,
        subject_id=subject_id,
        outcome=outcome.value,
        safe_detail=safe_detail(*detail_fragments) or None,
        idempotency_key=idempotency_key,
        created_at=format_utc(now),
    )
    db.add(event)
    db.flush()
    return event


def record_denial(
    db: Session,
    *,
    actor_type: ActorType,
    actor_id: str | None,
    route: str,
    reason: str,
    request_id: str,
    now: datetime,
    patient_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> AuditEvent:
    """Append an ``access.denied`` row and commit it immediately.

    ``route`` must be the **template** (e.g. ``GET /api/v1/doctor/patients/{id}``)
    so the audit trail does not turn into a directory of record ids, and no
    patient *content* is copied into the row. ``patient_id``/``subject_id`` are
    references to the record the caller tried to reach, which is what makes the
    denial reviewable later.

    The row is committed here on purpose: the caller raises a ``403`` straight
    afterwards, and the request-scoped session rolls back on that exception. A
    denial is evidence that must outlive the request, and nothing else is pending
    on a denial path.
    """
    event = append_audit_event(
        db,
        event_type=EVENT_ACCESS_DENIED,
        actor_type=actor_type,
        actor_id=actor_id,
        outcome=AuditOutcome.DENIED,
        request_id=request_id,
        now=now,
        patient_id=patient_id,
        subject_type=subject_type,
        subject_id=subject_id,
        detail_fragments=(f"route={route}", f"reason={reason}"),
    )
    db.commit()
    return event


__all__ = [
    "EVENT_ACCESS_DENIED",
    "EVENT_AUTH_LOGIN",
    "EVENT_AUTH_LOGIN_FAILED",
    "EVENT_AUTH_LOGOUT",
    "EVENT_CHECKIN_CREATED",
    "EVENT_DEMO_RESET",
    "EVENT_DEMO_SEEDED",
    "REASON_DEMO_MODE_DISABLED",
    "REASON_NOT_ASSIGNED",
    "REASON_NOT_SELF_SCOPE",
    "REASON_ROLE_NOT_ALLOWED",
    "SAFE_DETAIL_MAX",
    "append_audit_event",
    "derive_audit_key",
    "record_denial",
    "safe_detail",
]
