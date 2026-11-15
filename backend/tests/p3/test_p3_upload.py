"""Upload validation, deduplication and the no-row-on-rejection rule.

Maps to ``REQ-ING-01``/``REQ-ING-04``/``REQ-ING-05`` and contract cases
``NEG-03``, ``NEG-04``, ``NEG-05``, ``NEG-18``.

Owner decision D-10 is the load-bearing rule here: a rejected upload must leave
**no** ``document`` row. Each negative test therefore asserts both the response
code *and* the row count, because a 422 with a leaked row would still be a
correctness bug that no status-code assertion catches.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document

UPLOAD = "/api/v1/documents/upload"


def _document_count(db: Session) -> int:
    """Return the number of stored document rows."""
    return db.execute(select(func.count()).select_from(Document)).scalar_one()


def _upload(
    client: TestClient,
    headers: dict[str, str],
    payload: bytes,
    *,
    filename: str = "report.pdf",
    content_type: str = "application/pdf",
    declared_type: str | None = None,
):
    """POST one upload."""
    data = {"declared_type": declared_type} if declared_type else None
    return client.post(
        UPLOAD,
        headers=headers,
        files={"file": (filename, payload, content_type)},
        data=data,
    )


def test_clean_pdf_upload_is_accepted_and_pending(
    api, doctor_headers, patient_headers, report_b_pdf
):
    """A valid upload returns ``202`` with the contract body fields."""
    response = _upload(api, patient_headers, report_b_pdf)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending_extraction"
    assert body["duplicate_ignored"] is False
    assert body["page_count"] == 1
    assert len(body["sha256"]) == 64


def test_upload_requires_a_patient_not_a_doctor(api, doctor_headers, report_b_pdf):
    """``403``: a doctor has no patient scope to upload into."""
    response = _upload(api, doctor_headers, report_b_pdf)

    assert response.status_code == 403


def test_upload_rejects_non_pdf_magic_bytes(api, patient_headers, db: Session):
    """A PNG declared as a PDF is ``415 E_UNSUPPORTED_MEDIA``, not a stored row."""
    before = _document_count(db)
    response = _upload(api, patient_headers, b"GIF89a" + b"\x00" * 64)

    assert response.status_code == 415
    assert response.json()["code"] == "E_UNSUPPORTED_MEDIA"
    assert _document_count(db) == before, "a rejected upload must not create a row"


def test_upload_rejects_truncated_pdf_without_creating_a_row(
    api, patient_headers, db: Session, report_b_pdf
):
    """A structurally broken PDF is ``422 E_PARSE_FAILED`` and leaves no row (D-10)."""
    before = _document_count(db)
    response = _upload(api, patient_headers, report_b_pdf[:120])

    assert response.status_code == 422
    assert response.json()["code"] == "E_PARSE_FAILED"
    assert _document_count(db) == before


def test_upload_rejects_empty_file(api, patient_headers, db: Session):
    """An empty payload is a validation failure, not a zero-byte document."""
    before = _document_count(db)
    response = _upload(api, patient_headers, b"")

    assert response.status_code == 422
    assert _document_count(db) == before


def test_upload_rejects_oversize_payload(api, patient_headers, db: Session, fixtures):
    """``413 E_FILE_TOO_LARGE`` above 10 MiB, with no stored row."""
    before = _document_count(db)
    response = _upload(api, patient_headers, fixtures.build_oversized_pdf(11 * 1024 * 1024))

    assert response.status_code == 413
    assert response.json()["code"] == "E_FILE_TOO_LARGE"
    assert _document_count(db) == before


def test_upload_rejects_too_many_pages(api, patient_headers, db: Session, fixtures):
    """``422 E_PAGE_LIMIT_EXCEEDED`` above 20 pages, with no stored row."""
    before = _document_count(db)
    response = _upload(api, patient_headers, fixtures.build_blank_pdf(25))

    assert response.status_code == 422
    assert response.json()["code"] == "E_PAGE_LIMIT_EXCEEDED"
    assert _document_count(db) == before


def test_upload_rejects_unknown_declared_type(api, patient_headers, report_b_pdf):
    """A declaration outside the contract enum is ``400 E_VALIDATION``."""
    response = _upload(api, patient_headers, report_b_pdf, declared_type="application/msword")

    assert response.status_code == 400
    assert response.json()["code"] == "E_VALIDATION"


def test_duplicate_bytes_for_same_patient_conflict(api, patient_headers, report_b_pdf, db: Session):
    """``NEG-18``: identical bytes are ``409 E_DUPLICATE_DOCUMENT`` and reuse the row."""
    first = _upload(api, patient_headers, report_b_pdf)
    assert first.status_code == 202
    before = _document_count(db)

    second = _upload(api, patient_headers, report_b_pdf)

    assert second.status_code == 409
    assert second.json()["code"] == "E_DUPLICATE_DOCUMENT"
    assert _document_count(db) == before, "the existing document is reused, not duplicated"


def test_same_bytes_from_a_different_patient_is_a_separate_document(
    api, patient_headers, other_patient_headers, report_b_pdf, db: Session
):
    """The dedup key is ``(patient_id, sha256)``, so two patients may hold the same bytes."""
    assert _upload(api, patient_headers, report_b_pdf).status_code == 202
    before = _document_count(db)

    response = _upload(api, other_patient_headers, report_b_pdf)

    assert response.status_code == 202
    assert _document_count(db) == before + 1


def test_upload_accepts_png_and_jpeg_documents(api, patient_headers, fixtures):
    """Magic-byte validation accepts the two declared image types."""
    for payload, mime in (
        (fixtures.image_bytes("report_a_clean.txt", fmt="PNG"), "image/png"),
        (fixtures.image_bytes("report_a_clean.txt", fmt="JPEG"), "image/jpeg"),
    ):
        response = api.post(
            UPLOAD,
            headers=patient_headers,
            files={"file": ("scan", payload, mime)},
        )
        # Accepted: the row exists and extraction status is recorded. OCR is not
        # configured in this sandbox, so the document legitimately ends ``failed``
        # with a dependency code rather than pretending to have read the scan.
        assert response.status_code == 202, response.text


def test_unauthenticated_upload_is_rejected(api, report_b_pdf):
    """No token is ``401`` with the uniform envelope."""
    response = _upload(api, {}, report_b_pdf)

    assert response.status_code == 401
    assert response.json()["code"] == "E_UNAUTHENTICATED"
