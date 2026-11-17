"""Document intake: validation, deduplication, storage and extraction.

Owner decision D-10 shapes two important behaviours here:

* A **structural parse failure during upload validation creates no document
  row.** Validation runs before persistence, so a rejected upload leaves only an
  audit event.
* A previously accepted document may transition to ``failed`` when *extraction*
  later fails (dependency missing, timeout, unreadable page). That is a state
  change on an existing row, not a new one.

The intake order is fixed and each step is a separate, testable function.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import format_utc, utc_now
from app.core.config import Settings
from app.core.enums import (
    DocumentMimeType,
    DocumentStatus,
    ExtractionPath,
    FactVerificationStatus,
    Preprocessing,
    QualityFlag,
    TriagePath,
)
from app.core.errors import (
    DUPLICATE_DOCUMENT_DETAIL,
    ApiError,
    ErrorCode,
    document_error,
)
from app.db.models import Document, DocumentPageText, ExtractedFact, ExtractionAttempt
from app.services.documents.field_parser import (
    ParseResult,
    parse_pages,
    span_is_resolvable,
)
from app.services.documents.media import ValidatedUpload, validate_upload
from app.services.documents.ocr import (
    OcrUnavailableError,
    confidence_below_floor,
    looks_corrupted,
    run_ocr,
)
from app.services.documents.rasterize import RasterizationError, render_page
from app.services.documents.storage import (
    generate_stored_name,
    sanitize_filename,
    write_document,
)
from app.services.documents.text_extraction import (
    PageText,
    extract_pdf_pages,
    pages_needing_ocr,
)

#: ``document.failure_code`` used when an extraction exceeded its budget. There
#: is no ``E_TIMEOUT`` HTTP response: the value is surfaced through the
#: ``200 ExtractionResponse`` with ``document_status='failed'`` (D-10).
TIMEOUT_FAILURE_CODE = "E_TIMEOUT"

#: The terminal failure codes a document must carry to be a recovery **source**
#: (R21 §4.3). These are exactly the rejection codes: a recovery answers a doctor
#: rejection, not an unreadable file. An extraction failure such as
#: ``E_PARSE_FAILED`` or ``no_facts_extracted`` is terminal too, but there is
#: nothing a better copy of the same report could recover — the pipeline never
#: produced a reading to disagree with — so those are deliberately excluded.
RECOVERABLE_FAILURE_CODES: frozenset[str] = frozenset(
    {"all_facts_rejected", "measurement_rejected", "fact_rejected"}
)

#: Neutral wording for a ``recovery_of`` that names no document in the caller's
#: scope. Deliberately identical for "absent" and "belongs to another patient",
#: matching the read route's rule: a different answer would confirm existence.
RECOVERY_SOURCE_NOT_FOUND_DETAIL: str = "This document is not available."

#: Neutral refusal for a ``recovery_of`` that is not a recoverable source.
#: Says what is required without confirming whether some other id exists.
_RECOVERY_SOURCE_NOT_TERMINAL = (
    "recovery_of must name one of your own documents that ended in a rejection "
    "(status 'failed' with a rejection reason)."
)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """The result of an accepted upload."""

    document: Document
    duplicate: bool


@dataclass(frozen=True, slots=True)
class ExtractionOutcome:
    """The document after extraction, plus facts the caller must audit.

    ``untrusted_content_detected`` is reported upward rather than stored as a
    quality flag, because ``QualityFlag`` is a closed enum of *data* problems and
    injection is a *security* observation. ``CTR-EXTRACT-001`` §7.4 records it in
    the audit trail with a neutral note and never acts on it.
    """

    document: Document
    untrusted_content_detected: bool


def _existing_by_hash(db: Session, *, patient_id: str, sha256: str) -> Document | None:
    """Return this patient's document with the same bytes, if any."""
    return db.execute(
        select(Document).where(Document.patient_id == patient_id, Document.sha256 == sha256)
    ).scalar_one_or_none()


def resolve_recovery_source(db: Session, *, patient_id: str, recovery_of: str) -> Document:
    """Return the validated terminal document that ``recovery_of`` names.

    R21 §4.3. The link is a **patient-declared association**: this function only
    proves that the uploader owns a document that ended in a rejection. It does
    not — and must not — assert that the new bytes are clearer, related or
    clinically equivalent to it.

    Three refusals, each chosen so the response cannot be used to probe for other
    patients' documents:

    * malformed (not a UUID) → ``400 E_VALIDATION``: a client-side mistake that
      reveals nothing;
    * absent, or owned by someone else → ``404 E_NOT_FOUND``, with the *same*
      wording as the read route. Both cases are indistinguishable on purpose: a
      distinct "belongs to another patient" answer would confirm that the id
      exists, which is a cross-patient disclosure.
    * present and owned, but not in a recoverable terminal state →
      ``400 E_VALIDATION``. Here the caller has already proven ownership of the
      document, so explaining the state is not a leak.

    The identity check is done in SQL (``patient_id`` in the ``WHERE``) rather
    than by loading and comparing in Python, so there is no window in which an
    out-of-scope row is materialized.
    """
    try:
        parsed = uuid.UUID(recovery_of)
    except (ValueError, AttributeError, TypeError):
        raise ApiError(
            400,
            ErrorCode.VALIDATION,
            "recovery_of must be a document id (UUID).",
        ) from None

    source = db.execute(
        select(Document).where(
            Document.id == str(parsed),
            Document.patient_id == patient_id,
        )
    ).scalar_one_or_none()
    if source is None:
        # Identical wording for "no such document" and "not yours".
        raise ApiError(404, ErrorCode.NOT_FOUND, RECOVERY_SOURCE_NOT_FOUND_DETAIL)

    if (
        source.extraction_status != DocumentStatus.FAILED.value
        or source.failure_code not in RECOVERABLE_FAILURE_CODES
    ):
        raise ApiError(400, ErrorCode.VALIDATION, _RECOVERY_SOURCE_NOT_TERMINAL)

    return source


def accept_upload(
    db: Session,
    *,
    patient_id: str,
    uploaded_by_user_id: str,
    payload: bytes,
    original_filename: str | None,
    declared_type: str | None,
    settings: Settings,
    recovery_of: str | None = None,
) -> UploadOutcome:
    """Validate and persist one upload.

    Raises the contract ``ApiError`` for every rejection. **No row is created**
    for a validation failure (D-10): the exception propagates before any insert.

    ``recovery_of`` names a terminal document this upload replaces (R21 §4.3).
    It is validated **before** the duplicate check so a refused link can never
    leave a row behind, and the duplicate check still runs first-class: identical
    bytes are refused with or without a link (§4.6), because re-uploading the
    same bytes cannot be a better source.
    """
    validated: ValidatedUpload = validate_upload(
        payload,
        declared_type=declared_type,
        max_bytes=settings.max_upload_bytes,
        max_pages=settings.max_pdf_pages,
        max_pixels=settings.max_image_pixels,
    )

    # Validate the declared link before anything is written, so a bad link is a
    # pure refusal: no row, no stored file, no audit event (R21 §4.3).
    source: Document | None = None
    if recovery_of is not None:
        source = resolve_recovery_source(db, patient_id=patient_id, recovery_of=recovery_of)

    # Duplicate check happens before storage so a repeat upload does not create a
    # second file on disk. The unique index is the race-safe backstop.
    existing = _existing_by_hash(db, patient_id=patient_id, sha256=validated.sha256)
    if existing is not None:
        return UploadOutcome(document=existing, duplicate=True)

    stored_name = generate_stored_name(validated.mime_type)
    write_document(stored_name, payload, upload_dir=settings.upload_dir)

    document = Document(
        patient_id=patient_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=sanitize_filename(original_filename),
        stored_path=stored_name,
        mime_type=validated.mime_type,
        sha256=validated.sha256,
        size_bytes=validated.size_bytes,
        page_count=validated.page_count,
        extraction_status=DocumentStatus.PENDING_EXTRACTION.value,
        uploaded_at=format_utc(utc_now()),
        recovered_from_document_id=(source.id if source is not None else None),
    )
    db.add(document)

    try:
        db.flush()
    except IntegrityError:
        # Two racing uploads of identical bytes: the loser reuses the winner's
        # row rather than surfacing a 500.
        db.rollback()
        raced = _existing_by_hash(db, patient_id=patient_id, sha256=validated.sha256)
        if raced is None:  # pragma: no cover - index guarantees one of the two
            raise document_error(ErrorCode.DUPLICATE_DOCUMENT, DUPLICATE_DOCUMENT_DETAIL) from None
        return UploadOutcome(document=raced, duplicate=True)

    return UploadOutcome(document=document, duplicate=False)


def _record_attempt(
    db: Session,
    *,
    document: Document,
    path: ExtractionPath,
    preprocessing: Preprocessing,
    engine_confidence: float | None,
    text_char_count: int,
    page_from: int,
    page_to: int,
    succeeded: bool,
    error_code: str | None,
    duration_ms: int,
    tool_version: str | None,
) -> ExtractionAttempt:
    """Persist one typed extraction attempt."""
    attempt = ExtractionAttempt(
        document_id=document.id,
        path=path.value,
        preprocessing=preprocessing.value,
        engine_confidence=engine_confidence,
        text_char_count=text_char_count,
        page_from=page_from,
        page_to=page_to,
        succeeded=1 if succeeded else 0,
        error_code=error_code,
        duration_ms=duration_ms,
        tool_version=tool_version,
        created_at=format_utc(utc_now()),
    )
    db.add(attempt)
    return attempt


def _persist_facts(
    db: Session,
    *,
    document: Document,
    parse_result: ParseResult,
    pages: list[PageText],
    ocr_confidence_floor: float,
) -> list[ExtractedFact]:
    """Persist candidate facts, refusing any fact whose span does not resolve.

    ``REQ-VERIFY-01``: every fact carries a source reference. A candidate whose
    span falls outside the stored page text is a programming error, so it is
    dropped rather than stored with an unusable provenance.
    """
    stored: list[ExtractedFact] = []
    for candidate in parse_result.facts:
        if not span_is_resolvable(pages, candidate):
            continue
        confidence = candidate.confidence
        flags = [flag.value for flag in candidate.quality_flags]

        # Engine-reported confidence below the demo floor blocks the value.
        if (
            confidence is not None
            and confidence_below_floor(confidence, floor=ocr_confidence_floor)
            and QualityFlag.LOW_CONFIDENCE.value not in flags
        ):
            flags.append(QualityFlag.LOW_CONFIDENCE.value)

        if (
            candidate.raw_text
            and looks_corrupted(candidate.raw_text)
            and QualityFlag.LOW_CONFIDENCE.value not in flags
        ):
            flags.append(QualityFlag.LOW_CONFIDENCE.value)

        fact = ExtractedFact(
            document_id=document.id,
            patient_id=document.patient_id,
            field_name=candidate.field_name.value,
            raw_text=candidate.raw_text[:300],
            normalized_value=candidate.normalized_value,
            unit=candidate.unit,
            page_index=candidate.page_index,
            char_start=candidate.char_start,
            char_end=candidate.char_end,
            quality_flags=_encode_flags(flags),
            confidence=confidence,
            extractor=candidate.extractor.value,
            verification_status=FactVerificationStatus.PENDING.value,
            created_at=format_utc(utc_now()),
        )
        db.add(fact)
        stored.append(fact)
    return stored


def _encode_flags(flags: list[str]) -> str:
    """Return a deterministic JSON array string of quality flags."""
    import json

    ordered = sorted(set(flags))
    return json.dumps(ordered, separators=(",", ":"))


def select_path(
    *, page_count: int, ocr_candidate_pages: list[int], ocr_available: bool
) -> tuple[TriagePath, str]:
    """Choose the bounded extraction path and its reason (``ADR-0006`` §3.1).

    Pure and deterministic. Returned as a **value**, not executed as a graph
    node: P3 ships no LangGraph node (owner decision D-09). The reason string is
    an enum-like token, never free text, and never a document snippet.
    """
    if not ocr_candidate_pages:
        return TriagePath.PROCEED, "text_layer_available"
    if not ocr_available:
        return TriagePath.FLAG_FOR_HUMAN, "dependency_missing"
    if page_count > 0:
        return TriagePath.OCR_PREPROCESS_RETRY, "low_confidence"
    return TriagePath.FLAG_FOR_HUMAN, "no_pages"


def _bound_pages(pages: list[PageText], *, max_chars: int) -> list[PageText]:
    """Truncate every page's text to ``max_chars`` before parsing and storage.

    Guarantees ``ExtractedFact`` spans index the exact string saved in
    ``document_page_text``.
    """
    bounded: list[PageText] = []
    for page in pages:
        text = page.text[:max_chars]
        bounded.append(
            PageText(
                page_index=page.page_index,
                text=text,
                extractor=page.extractor,
                confidence=page.confidence,
                tool_version=page.tool_version,
            )
        )
    return bounded


def _persist_page_texts(
    db: Session, *, document: Document, pages: list[PageText]
) -> list[DocumentPageText]:
    """Persist one ``DocumentPageText`` row per extracted page."""
    stored: list[DocumentPageText] = []
    now = format_utc(utc_now())
    for page in pages:
        row = DocumentPageText(
            document_id=document.id,
            page_index=page.page_index,
            extractor=page.extractor.value,
            tool_version=page.tool_version,
            text=page.text,
            text_length=len(page.text),
            non_whitespace_chars=page.char_count,
            text_sha256=hashlib.sha256(page.text.encode("utf-8")).hexdigest(),
            created_at=now,
        )
        db.add(row)
        stored.append(row)
    return stored


def run_extraction(db: Session, *, document: Document, settings: Settings) -> ExtractionOutcome:
    """Extract a document, recording attempts and candidate facts.

    Transitions ``pending_extraction`` to ``extracted``/``needs_verification``/
    ``failed``. A failure never produces ``verified`` and never creates facts
    from a guess.
    """
    from app.services.documents.storage import resolve_for_read

    started = time.monotonic()
    try:
        payload = resolve_for_read(
            document.stored_path, upload_dir=settings.upload_dir
        ).read_bytes()
    except FileNotFoundError:
        document.extraction_status = DocumentStatus.FAILED.value
        document.failure_code = ErrorCode.PARSE_FAILED.value
        return ExtractionOutcome(document=document, untrusted_content_detected=False)

    pages: list[PageText] = []

    if document.mime_type == DocumentMimeType.PDF.value:
        try:
            pages = extract_pdf_pages(payload)
        except ValueError:
            document.extraction_status = DocumentStatus.FAILED.value
            document.failure_code = ErrorCode.PARSE_FAILED.value
            _record_attempt(
                db,
                document=document,
                path=ExtractionPath.PYPDF,
                preprocessing=Preprocessing.NONE,
                engine_confidence=None,
                text_char_count=0,
                page_from=0,
                page_to=max(0, (document.page_count or 1) - 1),
                succeeded=False,
                error_code=ErrorCode.PARSE_FAILED.value,
                duration_ms=int((time.monotonic() - started) * 1000),
                tool_version=None,
            )
            return ExtractionOutcome(document=document, untrusted_content_detected=False)

        _record_attempt(
            db,
            document=document,
            path=ExtractionPath.PYPDF,
            preprocessing=Preprocessing.NONE,
            engine_confidence=None,
            text_char_count=sum(page.char_count for page in pages),
            page_from=0,
            page_to=max(0, len(pages) - 1),
            succeeded=True,
            error_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            tool_version=None,
        )

        needed = pages_needing_ocr(pages, min_chars=settings.text_layer_min_chars)
        if needed:
            ocr_pages, ocr_failure = _ocr_pages(
                db, document=document, payload=payload, needed=needed, settings=settings
            )
            if ocr_failure is not None:
                document.extraction_status = DocumentStatus.FAILED.value
                document.failure_code = ocr_failure
                return ExtractionOutcome(document=document, untrusted_content_detected=False)
            by_index = {page.page_index: page for page in pages}
            for page in ocr_pages:
                by_index[page.page_index] = page
            pages = [by_index[index] for index in sorted(by_index)]
    else:
        ocr_pages, ocr_failure = _ocr_image_document(
            db, document=document, payload=payload, settings=settings
        )
        if ocr_failure is not None:
            document.extraction_status = DocumentStatus.FAILED.value
            document.failure_code = ocr_failure
            return ExtractionOutcome(document=document, untrusted_content_detected=False)
        pages = ocr_pages

    pages = _bound_pages(pages, max_chars=settings.max_page_text_chars)
    _persist_page_texts(db, document=document, pages=pages)
    parse_result = parse_pages(pages)

    # The document's own identity claim, stored once so ``VI-004`` can be
    # evaluated on every read without re-parsing the file.
    #
    # **R07:** the single reference and the *set* of references are stored
    # separately, because they answer different questions. One distinct value ->
    # ``document_patient_ref`` is that value. Several distinct values -> the
    # document is unattributable: ``document_patient_ref`` stays ``None`` and the
    # conflict is recorded in ``document_patient_refs`` so ``VI-004`` can fail
    # closed instead of silently trusting whichever reference came first.
    document.document_patient_ref = parse_result.document_patient_ref
    document.document_patient_refs = (
        json.dumps(list(parse_result.patient_refs_seen), separators=(",", ":"))
        if parse_result.patient_refs_seen
        else None
    )

    stored = _persist_facts(
        db,
        document=document,
        parse_result=parse_result,
        pages=pages,
        ocr_confidence_floor=settings.ocr_confidence_floor,
    )

    if not stored:
        # Nothing usable was extracted. The document is kept for the doctor to
        # inspect but cannot become verified.
        document.extraction_status = DocumentStatus.FAILED.value
        document.failure_code = "no_facts_extracted"
        return ExtractionOutcome(
            document=document,
            untrusted_content_detected=parse_result.untrusted_content_detected,
        )

    document.extraction_status = DocumentStatus.NEEDS_VERIFICATION.value
    return ExtractionOutcome(
        document=document,
        untrusted_content_detected=parse_result.untrusted_content_detected,
    )


def _ocr_pages(
    db: Session,
    *,
    document: Document,
    payload: bytes,
    needed: list[int],
    settings: Settings,
) -> tuple[list[PageText], str | None]:
    """OCR the selected pages, honouring the bounded retry budget.

    Returns the OCR page results and a failure code (``None`` on success). At most
    two attempts per page: the first plain, the second with the deterministic
    ``grayscale_upscale`` preprocessing. The budget cannot grow.
    """
    results: list[PageText] = []
    for page_index in needed[: settings.max_pdf_pages]:
        try:
            image = render_page(
                payload,
                page_index=page_index,
                max_pixels=settings.max_image_pixels,
            )
        except RasterizationError:
            return results, ErrorCode.PARSE_FAILED.value

        succeeded = False
        for attempt_index, preprocessing in enumerate(
            (Preprocessing.NONE, Preprocessing.GRAYSCALE_UPSCALE), start=1
        ):
            if attempt_index > 2:  # pragma: no cover - enumerate bounds this
                break
            started = time.monotonic()
            try:
                ocr = run_ocr(
                    image,
                    tesseract_cmd=settings.tesseract_cmd,
                    language=settings.ocr_language,
                    preprocessing=preprocessing,
                )
            except OcrUnavailableError:
                _record_attempt(
                    db,
                    document=document,
                    path=ExtractionPath.TESSERACT,
                    preprocessing=preprocessing,
                    engine_confidence=None,
                    text_char_count=0,
                    page_from=page_index,
                    page_to=page_index,
                    succeeded=False,
                    error_code=ErrorCode.DEPENDENCY_MISSING.value,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    tool_version=None,
                )
                return results, ErrorCode.DEPENDENCY_MISSING.value

            char_count = sum(1 for character in ocr.text if not character.isspace())
            _record_attempt(
                db,
                document=document,
                path=ExtractionPath.TESSERACT,
                preprocessing=preprocessing,
                engine_confidence=ocr.confidence,
                text_char_count=char_count,
                page_from=page_index,
                page_to=page_index,
                succeeded=char_count > 0,
                error_code=None if char_count > 0 else "empty_ocr",
                duration_ms=int((time.monotonic() - started) * 1000),
                tool_version=ocr.tool_version,
            )

            if char_count >= settings.text_layer_min_chars:
                results.append(
                    PageText(
                        page_index=page_index,
                        text=ocr.text,
                        extractor=ExtractionPath.TESSERACT,
                        confidence=ocr.confidence,
                        tool_version=ocr.tool_version,
                    )
                )
                succeeded = True
                break

        if not succeeded:
            # Both attempts were unusable for this page: keep an empty page so a
            # page_missing style issue can be raised by the caller, rather than
            # silently dropping the page.
            results.append(
                PageText(
                    page_index=page_index,
                    text="",
                    extractor=ExtractionPath.TESSERACT,
                    confidence=None,
                )
            )
    return results, None


def _ocr_image_document(
    db: Session, *, document: Document, payload: bytes, settings: Settings
) -> tuple[list[PageText], str | None]:
    """OCR a PNG/JPEG document as a single page."""
    import io

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(payload)) as handle:
            image = handle.convert("RGB")
    except (UnidentifiedImageError, OSError):
        return [], ErrorCode.PARSE_FAILED.value

    started = time.monotonic()
    try:
        ocr = run_ocr(
            image,
            tesseract_cmd=settings.tesseract_cmd,
            language=settings.ocr_language,
            preprocessing=Preprocessing.NONE,
        )
    except OcrUnavailableError:
        _record_attempt(
            db,
            document=document,
            path=ExtractionPath.TESSERACT,
            preprocessing=Preprocessing.NONE,
            engine_confidence=None,
            text_char_count=0,
            page_from=0,
            page_to=0,
            succeeded=False,
            error_code=ErrorCode.DEPENDENCY_MISSING.value,
            duration_ms=int((time.monotonic() - started) * 1000),
            tool_version=None,
        )
        return [], ErrorCode.DEPENDENCY_MISSING.value

    char_count = sum(1 for character in ocr.text if not character.isspace())
    _record_attempt(
        db,
        document=document,
        path=ExtractionPath.TESSERACT,
        preprocessing=Preprocessing.NONE,
        engine_confidence=ocr.confidence,
        text_char_count=char_count,
        page_from=0,
        page_to=0,
        succeeded=char_count > 0,
        error_code=None if char_count > 0 else "empty_ocr",
        duration_ms=int((time.monotonic() - started) * 1000),
        tool_version=ocr.tool_version,
    )
    return [
        PageText(
            page_index=0,
            text=ocr.text,
            extractor=ExtractionPath.TESSERACT,
            confidence=ocr.confidence,
            tool_version=ocr.tool_version,
        )
    ], None


__all__ = [
    "TIMEOUT_FAILURE_CODE",
    "ExtractionOutcome",
    "UploadOutcome",
    "accept_upload",
    "run_extraction",
    "select_path",
]
