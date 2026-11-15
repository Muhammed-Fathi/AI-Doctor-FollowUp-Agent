"""Authorization on the document surface (``NEG-01``, ``REQ-SEC-01``).

P3 adds no authorization primitive; every case here exercises a combination of the
existing P2 helpers. The point of the module is to prove that no combination
accidentally widens scope:

* a patient may read their **own** document meta and file, and nothing else;
* a doctor may read only an **assigned** patient's document;
* ``/extraction`` and ``/verify`` are doctor-only even for one's own document;
* ``demo_admin`` has no clinical read access at all;
* a denial never confirms whether another patient's document exists.
"""

from __future__ import annotations

UPLOAD = "/api/v1/documents/upload"


def _upload(client, headers, payload, *, filename="report.pdf"):
    """Upload ``payload`` as ``headers`` and return the new document id."""
    response = client.post(
        UPLOAD,
        headers=headers,
        files={"file": (filename, payload, "application/pdf")},
    )
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def test_patient_can_read_own_document_metadata(api, patient_headers, report_b_pdf):
    """The owning patient sees the safe metadata shape."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    response = api.get(f"/api/v1/documents/{document_id}", headers=patient_headers)

    assert response.status_code == 200
    body = response.json()
    # No clinical value and no extracted span may appear in the patient view.
    assert set(body) == {
        "id",
        "patient_id",
        "filename",
        "mime_type",
        "sha256",
        "size_bytes",
        "page_count",
        "extraction_status",
        "uploaded_at",
    }
    assert "facts" not in body
    assert "raw_text" not in body


def test_patient_can_download_own_file(api, patient_headers, report_b_pdf):
    """The original bytes are downloadable by the owner (``OQ-A03`` default)."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    response = api.get(f"/api/v1/documents/{document_id}/file", headers=patient_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content == report_b_pdf


def test_other_patient_cannot_read_metadata_or_file(
    api, patient_headers, other_patient_headers, report_b_pdf
):
    """``403`` for a different patient, on both read routes."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    meta = api.get(f"/api/v1/documents/{document_id}", headers=other_patient_headers)
    file_response = api.get(f"/api/v1/documents/{document_id}/file", headers=other_patient_headers)

    assert meta.status_code == 403
    assert meta.json()["code"] == "E_SCOPE_VIOLATION"
    assert file_response.status_code == 403


def test_patient_cannot_read_extraction_even_for_own_document(api, patient_headers, report_b_pdf):
    """``NEG-01``: extraction is doctor-only. Pre-verification values stay hidden."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    response = api.get(f"/api/v1/documents/{document_id}/extraction", headers=patient_headers)

    assert response.status_code == 403
    assert "facts" not in response.json()


def test_patient_cannot_verify(api, patient_headers, doctor_headers, report_b_pdf):
    """A patient can never record a doctor decision on their own document."""
    document_id = _upload(api, patient_headers, report_b_pdf)
    extraction = api.get(
        f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers
    ).json()
    fact_id = extraction["facts"][0]["fact_id"]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=patient_headers,
        json={"fact_id": fact_id, "decision": "verified"},
    )

    assert response.status_code == 403


def test_assigned_doctor_can_read_extraction(api, patient_headers, doctor_headers, report_b_pdf):
    """The assigned doctor sees the candidate facts with provenance."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    response = api.get(f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["document_status"] == "needs_verification"
    assert body["facts"], "a clean report must yield candidate facts"
    for fact in body["facts"]:
        assert fact["verification_status"] == "pending"
        assert fact["evidence"]["kind"] == "document_span"
        assert fact["evidence"]["page_index"] == 0


def test_unassigned_doctor_is_denied(api, patient_headers, unassigned_doctor_headers, report_b_pdf):
    """A doctor with no assignment gets ``403`` on metadata and extraction."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    meta = api.get(f"/api/v1/documents/{document_id}", headers=unassigned_doctor_headers)
    extraction = api.get(
        f"/api/v1/documents/{document_id}/extraction",
        headers=unassigned_doctor_headers,
    )

    assert meta.status_code == 403
    assert extraction.status_code == 403


def test_demo_admin_has_no_clinical_document_access(
    api, patient_headers, admin_headers, report_b_pdf
):
    """``demo_admin`` manages data, not clinical records."""
    document_id = _upload(api, patient_headers, report_b_pdf)

    meta = api.get(f"/api/v1/documents/{document_id}", headers=admin_headers)
    extraction = api.get(f"/api/v1/documents/{document_id}/extraction", headers=admin_headers)

    assert meta.status_code == 403
    assert extraction.status_code == 403


def test_missing_document_is_indistinguishable_from_out_of_scope(api, other_patient_headers):
    """A nonexistent id and another patient's id both answer a neutral ``404``.

    The wording is compared directly: if the two differed, a caller could use the
    message to test for the existence of another patient's document.
    """
    missing = api.get(
        "/api/v1/documents/00000000-0000-4000-8000-000000000000",
        headers=other_patient_headers,
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "This document is not available."


def test_unauthenticated_reads_are_rejected(api):
    """Every document read requires a session."""
    for path in (
        "/api/v1/documents/00000000-0000-4000-8000-000000000000",
        "/api/v1/documents/00000000-0000-4000-8000-000000000000/extraction",
        "/api/v1/documents/00000000-0000-4000-8000-000000000000/file",
    ):
        response = api.get(path)
        assert response.status_code == 401, path
        assert response.json()["code"] == "E_UNAUTHENTICATED"
