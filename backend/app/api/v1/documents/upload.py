"""``POST /api/v1/documents/upload`` (``API_CONTRACT.md`` §2.4).

Patient-only, self-scoped. The patient identity comes from the bearer session;
the request has no patient field at all, so a cross-patient upload cannot be
expressed.

Validation happens **before** any row is written (owner decision D-10): a
structural parse failure, oversize payload, wrong media type or excess page count
leaves no ``document`` row behind. A duplicate is not an error to the caller in
the sense of data loss — the existing document is returned with
``duplicate_ignored=true`` — but the contract still requires
``409 E_DUPLICATE_DOCUMENT`` for the re-upload case, so the documented code is
what the client sees and the header marks the reuse.

Extraction is attempted immediately in the same request. A dependency failure
(Tesseract absent) is **not** a failed upload: the document exists, its status is
``failed`` and the client polls ``GET /documents/{id}``. The upload response
schema documents only ``202`` and the error set, so the response stays truthful.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Response, Security, UploadFile, status

from app.api.v1.auth.dependencies import (
    AppSettings,
    DbSession,
    Now,
    PrincipalDep,
    RequestId,
    bearer_scheme,
)
from app.core.enums import AuditOutcome, DocumentMimeType
from app.core.errors import (
    DUPLICATE_DOCUMENT_DETAIL,
    FILE_TOO_LARGE_DETAIL,
    ApiError,
    ErrorCode,
    document_error,
)
from app.core.policies import self_patient_id
from app.schemas.document import DocumentUploadResponse
from app.services.audit import append_audit_event
from app.services.documents import (
    EVENT_DOCUMENT_DUPLICATE,
    EVENT_DOCUMENT_UPLOADED,
    EVENT_UNTRUSTED_CONTENT,
)
from app.services.documents.intake import accept_upload, run_extraction

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Security(bearer_scheme)],
)

ROUTE_UPLOAD = "POST /api/v1/documents/upload"

_RESPONSES: dict[int | str, dict[str, object]] = {
    400: {"description": "Malformed multipart request (validation error)"},
    401: {"description": "Not authenticated (uniform body)"},
    403: {"description": "Caller is not a patient"},
    409: {"description": "Identical bytes already uploaded for this patient"},
    413: {"description": "Payload exceeds 10 MiB"},
    415: {"description": "Media type is not PDF, PNG or JPEG"},
    422: {"description": "Page limit exceeded or the file cannot be parsed"},
}

#: Contract-declared media types. A ``declared_type`` outside this set is a
#: validation error, not an ``E_UNSUPPORTED_MEDIA``: the *declaration* is wrong,
#: while the magic-byte check decides whether the *content* is acceptable.
_DECLARED_TYPES = frozenset(mime.value for mime in DocumentMimeType)


def _read_bounded(stream, *, max_bytes: int) -> bytes:
    """Read at most ``max_bytes + 1`` from ``stream``, refusing an oversize part.

    **R08.** ``stream.read()`` with no argument materializes the *entire* multipart
    part in memory before ``accept_upload`` ever looks at its length, so a
    deliberately huge body would be fully buffered before being rejected. Reading
    ``max_bytes + 1`` is the smallest read that can still distinguish the two
    boundary cases — exactly at the cap is allowed, one byte over is refused — and
    nothing larger is ever held.

    Raises the documented ``413 E_FILE_TOO_LARGE`` for anything past the cap, from
    here rather than from the later byte validation, so the refusal happens before
    parsing, hashing or storage. No row and no file are created (D-10).
    """
    payload = stream.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise document_error(ErrorCode.FILE_TOO_LARGE, FILE_TOO_LARGE_DETAIL)
    return payload


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a synthetic medical report (PDF, PNG, JPEG)",
    description=(
        "Accepts a PDF, PNG or JPEG up to 10 MiB and 20 pages. The document is "
        "stored unverified; candidate facts require a doctor decision before "
        "they can be used downstream."
    ),
    responses=_RESPONSES,
)
def upload_document(
    principal: PrincipalDep,
    db: DbSession,
    settings: AppSettings,
    now: Now,
    request_id: RequestId,
    response: Response,
    file: Annotated[UploadFile, File(description="PDF, PNG or JPEG; max 10 MiB")],
    declared_type: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    """Validate, store and extract one patient upload."""
    patient_id = self_patient_id(principal)

    if declared_type is not None and declared_type not in _DECLARED_TYPES:
        # The schema enum is the contract's; a value outside it is a client error
        # caught here rather than being smuggled through as a sniff hint.
        raise ApiError(
            400,
            ErrorCode.VALIDATION,
            "declared_type must be application/pdf, image/png or image/jpeg.",
        )

    payload = _read_bounded(file.file, max_bytes=settings.max_upload_bytes)
    outcome = accept_upload(
        db,
        patient_id=patient_id,
        uploaded_by_user_id=principal.user_id,
        payload=payload,
        original_filename=file.filename,
        declared_type=declared_type,
        settings=settings,
    )

    if outcome.duplicate:
        # Record the refusal-reason as an audit event before raising, so a
        # duplicate is visible in the trail without being a data change.
        append_audit_event(
            db,
            event_type=EVENT_DOCUMENT_DUPLICATE,
            actor_type=principal.actor_type,
            actor_id=principal.user_id,
            outcome=AuditOutcome.DENIED,
            request_id=request_id,
            now=now,
            patient_id=patient_id,
            subject_type="document",
            subject_id=outcome.document.id,
            detail_fragments=(ROUTE_UPLOAD, "reason=sha256_match"),
        )
        raise document_error(ErrorCode.DUPLICATE_DOCUMENT, DUPLICATE_DOCUMENT_DETAIL)

    extraction = run_extraction(db, document=outcome.document, settings=settings)
    document = extraction.document

    append_audit_event(
        db,
        event_type=EVENT_DOCUMENT_UPLOADED,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=patient_id,
        subject_type="document",
        subject_id=document.id,
        detail_fragments=(
            ROUTE_UPLOAD,
            f"status={document.extraction_status}",
            # Neutral, structural note. Never the document's own text: an injected
            # instruction must not be quoted into the audit trail
            # (CTR-EXTRACT-001 §7.4, REQ-AUDIT-02).
            "untrusted_content_detected" if extraction.untrusted_content_detected else "none",
        ),
    )

    if extraction.untrusted_content_detected:
        # Separate event type so a security reviewer can filter for it without
        # parsing a free-text field.
        append_audit_event(
            db,
            event_type=EVENT_UNTRUSTED_CONTENT,
            actor_type=principal.actor_type,
            actor_id=principal.user_id,
            outcome=AuditOutcome.OK,
            request_id=request_id,
            now=now,
            patient_id=patient_id,
            subject_type="document",
            subject_id=document.id,
            detail_fragments=(ROUTE_UPLOAD, "note=content_class=instruction_like"),
        )

    if document.failure_code:
        # The client learns the category from the document resource, never from
        # this response body, which stays exactly as the contract declares.
        response.headers["X-Extraction-Status"] = document.extraction_status

    return DocumentUploadResponse(
        document_id=document.id,
        sha256=document.sha256,
        page_count=document.page_count,
        duplicate_ignored=False,
    )


__all__ = ["ROUTE_UPLOAD", "router"]
