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
from app.core.enums import AuditOutcome, DocumentStatus, ExtractionPath, FactField
from app.core.errors import EXTRACTION_PENDING_DETAIL, ApiError, ErrorCode, document_error
from app.db.models import DocumentPageText, ExtractedFact, ExtractionAttempt
from app.schemas.document import (
    DocumentMeta,
    DocumentPageTextItem,
    DocumentTextResponse,
    EvidenceRef,
    ExtractionAttemptSummary,
    ExtractionResponse,
    VerificationIssue,
)
from app.schemas.document import (
    ExtractedFact as ExtractedFactSchema,
)
from app.services.audit import append_audit_event
from app.services.documents import (
    EVENT_DOCUMENT_FILE_READ,
    EVENT_DOCUMENT_TEXT_READ,
    EVENT_EXTRACTION_READ,
)
from app.services.documents.access import (
    load_document,
    require_doctor_document_scope,
    require_document_read_access,
)
from app.services.documents.intake import RECOVERABLE_FAILURE_CODES
from app.services.documents.quality import (
    QualitySummary,
    decode_fact_ids,
    decode_flags,
    summarize,
)
from app.services.documents.storage import UnsafePathError, resolve_for_read

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_READ_META = "GET /api/v1/documents/{document_id}"
ROUTE_READ_EXTRACTION = "GET /api/v1/documents/{document_id}/extraction"
ROUTE_READ_FILE = "GET /api/v1/documents/{document_id}/file"
ROUTE_READ_TEXT = "GET /api/v1/documents/{document_id}/text"

#: Neutral wording for an absent *or* out-of-scope document.
NOT_FOUND_DETAIL = "This document is not available."


def _recovery_eligible(document) -> bool:
    """Return whether ``document`` may be named in a later ``recovery_of``.

    **R21 §4.9.** Derived from exactly the two conditions the upload route
    enforces (``intake.resolve_recovery_source``), read from the same constant so
    the advertised affordance and the accepted request cannot drift apart:

    * the document is terminally ``failed``, and
    * its ``failure_code`` is one of the rejection codes.

    An extraction failure (``E_PARSE_FAILED``, ``no_facts_extracted``) is terminal
    but *not* recoverable: there is no doctor rejection for a better copy of the
    report to answer. Reporting it as eligible would offer the patient an action
    the endpoint then refuses.
    """
    return (
        document.extraction_status == DocumentStatus.FAILED.value
        and document.failure_code in RECOVERABLE_FAILURE_CODES
    )


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
        # R01: the real route that produced this fact. A scanned page inside a
        # text PDF is a ``tesseract`` fact, and claiming ``pypdf`` for it would
        # misrepresent where the evidence came from.
        extractor=fact.extractor,
    )


def _requires_source_confirmation(fact: ExtractedFact) -> bool:
    """Return True when an OCR measurement or unit requires source-image review."""
    return fact.extractor == ExtractionPath.TESSERACT.value and fact.field_name in {
        FactField.VALUE.value,
        FactField.UNIT.value,
    }


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
        requires_source_confirmation=_requires_source_confirmation(fact),
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


def _default_document_extractor(
    attempts: list[ExtractionAttemptSummary], facts: list[ExtractedFact]
) -> str:
    """Resolve the fallback extractor when a document-level issue has no linked facts."""
    for fact in facts:
        if fact.extractor in {ExtractionPath.PYPDF.value, ExtractionPath.TESSERACT.value}:
            return fact.extractor
    for attempt in reversed(attempts):
        if attempt.succeeded and attempt.path in {
            ExtractionPath.PYPDF,
            ExtractionPath.TESSERACT,
        }:
            return attempt.path.value
    for attempt in reversed(attempts):
        if attempt.path in {ExtractionPath.PYPDF, ExtractionPath.TESSERACT}:
            return attempt.path.value
    return ExtractionPath.PYPDF.value


def _issue_schemas(
    summary: QualitySummary,
    *,
    document_id: str,
    facts: list[ExtractedFact],
    attempts: list[ExtractionAttemptSummary],
) -> list[VerificationIssue]:
    """Project the **persisted** blocker rows into the response schema.

    R04: ``issue_id``/``created_at`` come from the stored row, so a repeated GET of
    unchanged state returns identical identities. The row is the source of truth
    for the linkage too: ``fact_ids`` was resolved when the issue was raised, not
    recomputed per request.
    """
    by_id = {fact.id: fact for fact in facts}
    fallback_extractor = _default_document_extractor(attempts, facts)
    issues: list[VerificationIssue] = []
    for row in summary.issues:
        linked_ids = [fact_id for fact_id in decode_fact_ids(row.fact_ids) if fact_id in by_id][:8]
        evidence = [_evidence_for(by_id[fact_id]) for fact_id in linked_ids]
        if not evidence:
            # Document-level issues (VI-004) have no single fact; point at the
            # document itself rather than emitting an empty evidence array, which
            # the contract forbids (minItems: 1).
            evidence = [
                EvidenceRef(
                    kind="document_span",
                    document_id=document_id,
                    extractor=fallback_extractor,
                )
            ]
        issues.append(
            VerificationIssue(
                issue_id=row.id,
                issue_type=row.issue_type,
                reason_code=row.reason_code,
                blocking=True,
                message=row.message,
                document_id=document_id,
                fact_ids=linked_ids,
                evidence=evidence,
                created_at=row.created_at,
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
        failure_code=document.failure_code,
        recovery_eligible=_recovery_eligible(document),
        recovered_from_document_id=document.recovered_from_document_id,
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
    settings: AppSettings,
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

    # R02/R03/R04: reconcile and read the persisted blockers. The identity
    # comparison and the conflict evaluation both happen inside `summarize`, so
    # the read path can no longer feed itself a tautology.
    summary = summarize(
        db,
        document=document,
        conflict_tolerance=settings.conflict_tolerance,
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

    attempts = _attempt_summaries(db, document_id=document.id)
    return ExtractionResponse(
        document_id=document.id,
        document_status=status,
        facts=[_fact_schema(fact) for fact in facts],
        attempts=attempts,
        verification_issues=_issue_schemas(
            summary, document_id=document.id, facts=facts, attempts=attempts
        ),
        failure_code=document.failure_code,
        recovered_from_document_id=document.recovered_from_document_id,
    )


@router.get(
    "/{document_id}/text",
    response_model=DocumentTextResponse,
    summary="Persisted per-page extracted/OCR text (assigned doctor only)",
    description=(
        "Returns the bounded per-page text-layer or OCR transcriptions stored at "
        "extraction time. OCR text is untrusted engine output, not original source "
        "truth; doctors must still compare against GET /file."
    ),
    responses={
        401: {"description": "Not authenticated (uniform body)"},
        403: {"description": "Caller is not the assigned doctor"},
        404: {"description": "No such document in the caller's scope"},
        409: {"description": "Extraction is still pending"},
    },
)
def read_document_text(
    document_id: str,
    principal: PrincipalDep,
    db: DbSession,
    now: Now,
    request_id: RequestId,
) -> DocumentTextResponse:
    """Return persisted extracted/OCR page text for the assigned doctor only."""
    document = load_document(db, document_id)
    if document is None:
        raise _not_found()
    require_doctor_document_scope(db, principal, document)

    status = document.extraction_status
    if status == DocumentStatus.PENDING_EXTRACTION.value:
        raise document_error(ErrorCode.EXTRACTION_PENDING, EXTRACTION_PENDING_DETAIL)

    rows = list(
        db.execute(
            select(DocumentPageText)
            .where(DocumentPageText.document_id == document.id)
            .order_by(DocumentPageText.page_index)
        ).scalars()
    )

    append_audit_event(
        db,
        event_type=EVENT_DOCUMENT_TEXT_READ,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=document.patient_id,
        subject_type="document",
        subject_id=document.id,
        detail_fragments=(
            ROUTE_READ_TEXT,
            f"page_count={len(rows)}",
            f"status={status}",
        ),
    )

    return DocumentTextResponse(
        document_id=document.id,
        document_status=status,
        pages=[
            DocumentPageTextItem(
                page_index=row.page_index,
                extractor=row.extractor,
                tool_version=row.tool_version,
                text=row.text,
                text_length=row.text_length,
                non_whitespace_chars=row.non_whitespace_chars,
                text_sha256=row.text_sha256,
                created_at=row.created_at,
            )
            for row in rows
        ],
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
    now: Now,
    request_id: RequestId,
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

    append_audit_event(
        db,
        event_type=EVENT_DOCUMENT_FILE_READ,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=document.patient_id,
        subject_type="document",
        subject_id=document.id,
        detail_fragments=(ROUTE_READ_FILE, f"mime_type={document.mime_type}"),
    )

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
    "ROUTE_READ_TEXT",
    "router",
]
