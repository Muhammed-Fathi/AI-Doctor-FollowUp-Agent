"""``POST /api/v1/documents/{document_id}/verify`` (``API_CONTRACT.md`` §2.4).

Doctor-only and assignment-scoped. One call decides exactly one fact; there is no
bulk endpoint and no "verify all" convenience, because a bulk accept would turn a
human decision into a formality.

Append-only semantics (owner decisions D-11/D-13)
-------------------------------------------------
**Any** second decision on a fact — including an identical repeat of the same
decision — answers ``409 E_FACT_ALREADY_DECIDED``. The contract's
``Idempotency-Key`` convention (§1) would normally make a repeat a ``200``; this
endpoint deliberately deviates and the deviation is recorded in
``PHASE_3_REPORT.md`` and the PR body. Rationale: a doctor's decision is a
clinical record, and a client that silently re-submits it cannot tell whether the
first decision was recorded — the explicit ``409`` forces the client to re-read the
fact and see what is stored.

The internal mapping stays **transactionally idempotent**: ``ux_obs_source_fact``
makes a second observation for the same source fact impossible, so even a
concurrent double-accept cannot produce duplicate measurements. The rejection
happens at the API boundary; the database is the backstop.
"""

from __future__ import annotations

from fastapi import APIRouter, Security
from sqlalchemy import select

from app.api.v1.auth.dependencies import (
    AppSettings,
    DbSession,
    Now,
    PrincipalDep,
    RequestId,
    bearer_scheme,
)
from app.core.enums import AuditOutcome, VerificationDecision
from app.core.errors import ApiError, ErrorCode
from app.db.models import ExtractedFact
from app.schemas.document import VerificationRecord, VerifyRequest, VerifyResponse
from app.services.audit import append_audit_event
from app.services.documents import EVENT_FACT_VERIFIED
from app.services.documents.access import load_document, require_doctor_document_scope
from app.services.documents.verification import record_decision

from .read import _fact_schema, _not_found

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_VERIFY = "POST /api/v1/documents/{document_id}/verify"

#: Neutral wording for a fact that is not in this document.
_FACT_NOT_IN_DOCUMENT = "This fact is not part of this document."


@router.post(
    "/{document_id}/verify",
    response_model=VerifyResponse,
    summary="Doctor verifies, corrects or rejects one extracted fact",
    description=(
        "Append-only human decision; required before a pending fact may be used "
        "downstream. A second decision on the same fact is refused with "
        "`409 E_FACT_ALREADY_DECIDED`, including an identical repeat."
    ),
    responses={
        400: {"description": "Validation error (e.g. corrected without a value)"},
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Caller is not the assigned doctor"},
        404: {"description": "No such document or fact in the caller's scope"},
        409: {
            "description": (
                "This fact already has a recorded decision, or the document's "
                "identity is unresolved (`VI-004`)"
            )
        },
    },
)
def verify_fact(
    document_id: str,
    payload: VerifyRequest,
    principal: PrincipalDep,
    db: DbSession,
    settings: AppSettings,
    now: Now,
    request_id: RequestId,
) -> VerifyResponse:
    """Record one doctor decision on one fact."""
    document = load_document(db, document_id)
    if document is None:
        raise _not_found()
    require_doctor_document_scope(db, principal, document)

    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.id == payload.fact_id,
            ExtractedFact.document_id == document.id,
        )
    ).scalar_one_or_none()
    if fact is None:
        # A fact id from another document must not be distinguishable from a
        # nonexistent one.
        raise ApiError(404, ErrorCode.NOT_FOUND, _FACT_NOT_IN_DOCUMENT)

    if payload.decision is VerificationDecision.CORRECTED and not payload.corrected_value:
        raise ApiError(
            400,
            ErrorCode.VALIDATION,
            "A correction must supply corrected_value.",
        )

    outcome = record_decision(
        db,
        document=document,
        fact=fact,
        decision=payload.decision,
        doctor_user_id=principal.user_id,
        corrected_value=payload.corrected_value,
        corrected_unit=payload.corrected_unit,
        reason=payload.reason,
        conflict_tolerance=settings.conflict_tolerance,
        source_image_compared=payload.source_image_compared,
        confirmed_value=payload.confirmed_value,
        confirmed_unit=payload.confirmed_unit,
    )

    append_audit_event(
        db,
        event_type=EVENT_FACT_VERIFIED,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=document.patient_id,
        subject_type="extracted_fact",
        subject_id=fact.id,
        detail_fragments=(
            ROUTE_VERIFY,
            f"decision={payload.decision.value}",
            f"document_status={outcome.document_status}",
            f"source_image_compared={bool(outcome.verification.source_image_compared)}",
        ),
    )

    return VerifyResponse(
        fact=_fact_schema(outcome.fact),
        verification=VerificationRecord(
            decision=outcome.verification.decision,
            verified_by=outcome.verification.verified_by_user_id,
            decided_at=outcome.verification.decided_at,
            reason=outcome.verification.reason,
            previous_value=outcome.verification.previous_value,
            new_value=outcome.verification.new_value,
            new_unit=outcome.verification.new_unit,
            superseded_fact_id=outcome.superseded_fact_id,
            source_image_compared=bool(outcome.verification.source_image_compared),
            confirmed_value=outcome.verification.confirmed_value,
            confirmed_unit=outcome.verification.confirmed_unit,
        ),
        document_status=outcome.document_status,
    )


__all__ = ["ROUTE_VERIFY", "router"]
