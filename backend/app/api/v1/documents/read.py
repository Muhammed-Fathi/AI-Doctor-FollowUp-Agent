"""Document read endpoints (``API_CONTRACT.md`` §2.4).

``GET  /api/v1/documents/{document_id}``            metadata, patient-self or doctor-assigned
``GET  /api/v1/documents/{document_id}/extraction``  facts + issues, doctor-assigned only
``GET  /api/v1/documents/{document_id}/file``        original bytes, patient-self or doctor-assigned

The metadata and file routes are readable by the owning patient, but they expose
**no clinical value** and **no extracted span**: ``DocumentMeta`` has no field for
one, so a patient can see that their report exists without seeing the
pre-verification readings. That is the point of splitting the schemas
(``P0-R13``).

``/extraction`` is doctor-only because it necessarily contains the candidate
values, their raw text and their spans.

A missing document and a document outside the caller's scope answer differently
by contract (``403`` vs ``404``) but with wording that confirms nothing about
existence: the ``404`` detail is the same for "absent" and "not yours".
"""

from __future__ import annotations

from fastapi import APIRouter, Security
from fastapi.responses import Response
from sqlalchemy import select

from app.api.v1.auth.dependencies import (
    AppSettings,
    DbSession,
    Now,
    PrincipalDep,
    RequestId,
    bearer_scheme,
)
from app.core.clock import format_utc, utc_now
from app.core.enums import AuditOutcome, DocumentStatus
from app.core.errors import EXTRACTION_PENDING_DETAIL, ApiError, ErrorCode, document_error
from app.db.models import ExtractedFact, ExtractionAttempt, new_uuid
from app.schemas.document import (
    DocumentMeta,
    EvidenceRef,
    ExtractionAttemptSummary,
    ExtractionResponse,
    VerificationIssue,
)
from app.schemas.document import (
    ExtractedFact as ExtractedFactSchema,
)
from app.services.audit import append_audit_event
from app.services.documents import EVENT_EXTRACTION_READ
from app.services.documents.access import (
    load_document,
    require_doctor_document_scope,
    require_document_read_access,
)
from app.services.documents.quality import QualitySummary, decode_flags, summarize
from app.services.documents.storage import UnsafePathError, resolve_for_read

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_READ_META = "GET /api/v1/documents/{document_id}"
ROUTE_READ_EXTRACTION = "GET /api/v1/documents/{document_id}/extraction"
ROUTE_READ_FILE = "GET /api/v1/documents/{document_id}/file"

#: Neutral wording for an absent *or* out-of-scope document.
NOT_FOUND_DETAIL = "This document is not available."


def _not_found() -> Exception:
    """Return the neutral ``404`` used for absent and out-of-scope documents.

    ``E_NOT_FOUND`` is a general catalogue code (``API_CONTRACT.md`` §4), not a
    P3-specific one, so it is raised directly at ``404`` rather than through
    :func:`document_error`, whose table deliberately covers only the P3 codes.
    """
    return ApiError(404, ErrorCode.NOT_FOUND, NOT_FOUND_DETAIL)


def _evidence_for(fact: ExtractedFact) -> EvidenceRef:
    """Build the provenance reference for one stored fact.

    The span is copied from the stored row, never recomputed from the current
    file, so re-rendering a document cannot silently move a citation.
    """
    return EvidenceRef(
        kind="document_span",
        document_id=fact.document_id,
        page_index=fact.page_index,
        char_start=fact.char_start,
        char_end=fact.char_end,
        raw_text=fact.raw_text,
        extractor="pypdf",
    )


def _fact_schema(fact: ExtractedFact) -> ExtractedFactSchema:
    """Project a stored ``ExtractedFact`` row into the response schema."""
    return ExtractedFactSchema(
        fact_id=fact.id,
        document_id=fact.document_id,
        field_name=fact.field_name,
        raw_text=fact.raw_text,
        normalized_value=fact.normalized_value,
        unit=fact.unit,
        page_index=fact.page_index,
        char_start=fact.char_start,
        char_end=fact.char_end,
        quality_flags=list(decode_flags(fact.quality_flags)),
        confidence=fact.confidence,
        verification_status=fact.verification_status,
        evidence=_evidence_for(fact),
    )


def _fact_rows(db: DbSession, *, document_id: str) -> list[ExtractedFact]:
    """Return the document's facts in a stable order."""
    return list(
        db.execute(
            select(ExtractedFact)
            .where(ExtractedFact.document_id == document_id)
            .order_by(ExtractedFact.page_index, ExtractedFact.char_start, ExtractedFact.id)
        ).scalars()
    )


def _attempt_summaries(db: DbSession, *, document_id: str) -> list[ExtractionAttemptSummary]:
    """Return the redacted attempt projection for ``document_id``."""
    rows = db.execute(
        select(ExtractionAttempt)
        .where(ExtractionAttempt.document_id == document_id)
        .order_by(ExtractionAttempt.created_at, ExtractionAttempt.id)
    ).scalars()
    return [
        ExtractionAttemptSummary(
            path=row.path,
            succeeded=bool(row.succeeded),
            error_code=row.error_code,
            duration_ms=row.duration_ms,
            tool_version=row.tool_version,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _issue_schemas(
    summary: QualitySummary, *, document_id: str, facts: list[ExtractedFact]
) -> list[VerificationIssue]:
    """Project computed issue drafts into the response schema.

    ``fact_ids`` links each blocking issue to the stored facts it refers to so a
    doctor can act on it. Both lists are capped at 8 by the contract. ``issue_id``
    is derived from the document, the issue type and the linked facts, so the same
    unchanged document yields the same ids across reads (no id churn in a UI that
    polls).
    """
    created_at = format_utc(utc_now())
    issues: list[VerificationIssue] = []
    for draft in summary.issues:
        indices = [index for index in draft.fact_indices if 0 <= index < len(facts)]
        linked = [facts[index].id for index in indices][:8]
        evidence = [_evidence_for(facts[index]) for index in indices][:8]
        if not evidence:
            # Document-level issues (VI-004) have no single fact; point at the
            # document itself rather than emitting an empty evidence array, which
            # the contract forbids (minItems: 1).
            evidence = [
                EvidenceRef(kind="document_span", document_id=document_id, extractor="pypdf")
            ]
        issues.append(
            VerificationIssue(
                issue_id=new_uuid(),
                issue_type=draft.issue_type,
                reason_code=draft.reason_code,
                blocking=True,
                message=draft.message,
                document_id=document_id,
                fact_ids=linked,
                evidence=evidence,
                created_at=created_at,
            )
        )
    return issues


@router.get(
    "/{document_id}",
    response_model=DocumentMeta,
    summary="Document metadata and extraction status",
    description=(
        "Metadata only: no clinical value and no extracted text are returned, so "
        "the owning patient and the assigned doctor see the same safe shape."
    ),
    responses={
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Document is outside the caller's scope"},
        404: {"description": "No such document in the caller's scope"},
    },
)
def read_document(document_id: str, principal: PrincipalDep, db: DbSession) -> DocumentMeta:
    """Return metadata for one document the caller may see."""
    document = load_document(db, document_id)
    if document is None:
        raise _not_found()
    require_document_read_access(db, principal, document)

    return DocumentMeta(
        id=document.id,
        patient_id=document.patient_id,
        filename=document.original_filename,
        mime_type=document.mime_type,
        sha256=document.sha256,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        extraction_status=document.extraction_status,
        uploaded_at=document.uploaded_at,
    )


@router.get(
    "/{document_id}/extraction",
    response_model=ExtractionResponse,
    summary="Extracted candidate facts with provenance (doctor only)",
    description=(
        "Returns `409 E_EXTRACTION_PENDING` only while extraction has not finished. "
        "A terminal extraction failure is a `200` with `document_status='failed'` and "
        "the redacted attempt error code, so a client is never asked to poll a "
        "document that will not change (owner decision D-10)."
    ),
    responses={
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Caller is not the assigned doctor"},
        404: {"description": "No such document in the caller's scope"},
        409: {"description": "Extraction is still pending"},
    },
)
def read_extraction(
    document_id: str,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
) -> ExtractionResponse:
    """Return the doctor's view of extraction, or ``409`` while pending."""
    document = load_document(db, document_id)
    if document is None:
        raise _not_found()
    require_doctor_document_scope(db, principal, document)

    status = document.extraction_status

    # Owner decision D-10: pending is the *only* state that answers 409. A
    # terminal failure is reported through the declared 200 shape, never as an
    # undocumented 503 or a bare error.
    if status == DocumentStatus.PENDING_EXTRACTION.value:
        raise document_error(ErrorCode.EXTRACTION_PENDING, EXTRACTION_PENDING_DETAIL)

    summary = summarize(
        db,
        document=document,
        document_patient_ref=document.patient_id,
        scope_patient_ref=document.patient_id,
    )
    facts = _fact_rows(db, document_id=document.id)

    append_audit_event(
        db,
        event_type=EVENT_EXTRACTION_READ,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=document.patient_id,
        subject_type="document",
        subject_id=document.id,
        detail_fragments=(ROUTE_READ_EXTRACTION, f"status={status}"),
    )

    return ExtractionResponse(
        document_id=document.id,
        document_status=status,
        facts=[_fact_schema(fact) for fact in facts],
        attempts=_attempt_summaries(db, document_id=document.id),
        verification_issues=_issue_schemas(summary, document_id=document.id, facts=facts),
    )


@router.get(
    "/{document_id}/file",
    summary="Stream the stored synthetic upload",
    description=(
        "Returns the original bytes for the owning patient or the assigned doctor. "
        "The stored name is resolved through the storage guard, so a tampered row "
        "cannot escape the upload directory."
    ),
    response_class=Response,
    responses={
        200: {
            "description": "Original bytes",
            "content": {"application/pdf": {}, "image/png": {}, "image/jpeg": {}},
        },
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Document is outside the caller's scope"},
        404: {"description": "No such document in the caller's scope"},
    },
)
def read_file(
    document_id: str,
    principal: PrincipalDep,
    db: DbSession,
    settings: AppSettings,
) -> Response:
    """Stream the original upload, scope-checked first."""
    document = load_document(db, document_id)
    if document is None:
        raise _not_found()
    require_document_read_access(db, principal, document)

    try:
        payload = resolve_for_read(
            document.stored_path, upload_dir=settings.upload_dir
        ).read_bytes()
    except (FileNotFoundError, UnsafePathError, ValueError):
        # The row exists but the bytes do not (or the name is unsafe): report the
        # same neutral 404 rather than leaking a filesystem detail.
        raise _not_found() from None

    return Response(
        content=payload,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.original_filename}"',
            "Cache-Control": "no-store",
        },
    )


__all__ = [
    "NOT_FOUND_DETAIL",
    "ROUTE_READ_EXTRACTION",
    "ROUTE_READ_FILE",
    "ROUTE_READ_META",
    "router",
]
