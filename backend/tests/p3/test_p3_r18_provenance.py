"""Regression tests for P3-R18: source-evidence exactness in the R17 fallback.

Written **before** the fix and failing against the reviewed head ``73639d0``.

Two defects in ``field_parser._unattributed_value_facts()`` — the R17 fallback that
preserves a ``Value:`` line the lab-line grammar could not attribute.

**A — the span did not match ``raw_text``.** ``raw_text`` was computed from a
*stripped* token while ``char_start``/``char_end`` were derived from the unstripped
source, so the emitted span included leading whitespace and dropped trailing
characters. For the owner's real OCR line the fact claimed ``raw_text='105 mg/dL'``
while its own span resolved to ``' 105 mg/d'``. ``EXTRACTION_PROVENANCE.md`` §3/§5
requires the span to be the exact source slice, and ``span_is_resolvable()`` only
checked bounds, so nothing caught it.

**B — an empty token lost the only declaration.** ``if not token: continue`` meant a
line ending in ``Test: Glucose Value:`` produced no candidate at all. The label was
present, so this is *not* the documented destroyed-label limit: the document declares
a measurement, nothing records it, and approving the date and reference range alone
could reach ``verified`` — the exact failure R17 set out to prevent.

Honest labelling: OCR text here is **injected**. This is a simulation of engine
output, not real-engine evidence. Real recognition remains the owner's Windows run.
"""

from __future__ import annotations

import pytest

from app.core.enums import ExtractionPath, QualityFlag
from app.services.documents.field_parser import parse_pages
from app.services.documents.text_extraction import PageText

UPLOAD = "/api/v1/documents/upload"

#: The owner's real Windows OCR line at ``1b17a9a``, verbatim.
OWNER_LINE = "Test: Glucose Value: 105 mg/dL"


def _parse(text: str) -> list:
    page = PageText(page_index=0, text=text, extractor=ExtractionPath.TESSERACT)
    return [fact for fact in parse_pages([page]).facts if fact.field_name.value == "value"]


def _assert_span_is_the_exact_source_slice(fact, text: str) -> None:
    """Assert the fact's span resolves to exactly its stored ``raw_text``."""
    slice_ = text[fact.char_start : fact.char_end]
    assert slice_ == fact.raw_text, (
        f"span [{fact.char_start}:{fact.char_end}] resolves to {slice_!r} but raw_text is "
        f"{fact.raw_text!r}; the evidence must be the exact source slice"
    )


# =============================================================================
# A — exact provenance span integrity
# =============================================================================


def test_r18_a_owner_ocr_line_span_matches_raw_text_exactly():
    """The owner's real OCR line: span must equal ``raw_text`` character for character.

    Reviewed head produced ``raw_text='105 mg/dL'`` with a span resolving to
    ``' 105 mg/d'`` — leading space retained, final character lost.
    """
    text = f"SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n{OWNER_LINE}\n"
    facts = _parse(text)

    assert len(facts) == 1, "the unattributed line must still be preserved as evidence"
    fact = facts[0]
    assert fact.normalized_value is None, "no number may be invented"
    _assert_span_is_the_exact_source_slice(fact, text)
    assert fact.raw_text == "105 mg/dL"


@pytest.mark.parametrize(
    "line",
    [
        "Test: Glucose Value: 105 mg/dL",  # single leading space (owner's real case)
        "Test: Glucose Value:      105 mg/dL",  # several leading spaces
        "Test: Glucose Value: 105 mg/dL   ",  # trailing spaces
        "Test: Glucose Value:      105 mg/dL   ",  # both
        "Test: Glucose Value:\t105 mg/dL",  # tab as the separator
    ],
)
def test_r18_a_span_is_exact_across_whitespace_variants(line: str):
    """Leading/trailing whitespace must not shift the span away from ``raw_text``."""
    text = f"{line}\n"
    facts = _parse(text)

    assert len(facts) == 1
    _assert_span_is_the_exact_source_slice(facts[0], text)
    assert facts[0].raw_text == "105 mg/dL", "surrounding whitespace is not part of the value token"
    assert facts[0].normalized_value is None


def test_r18_a_long_token_is_bounded_and_still_an_exact_slice():
    """A >120-char token is truncated in ``raw_text``, so the span must match the truncation.

    At the reviewed head the span was ``char_start + len(token)``, which exceeded the
    stored 120 chars and swallowed leading whitespace, so the slice never matched.
    """
    long_token = "1" * 200
    text = f"Test: Glucose Value: {long_token}\n"
    facts = _parse(text)

    assert len(facts) == 1
    fact = facts[0]
    assert len(fact.raw_text) == 120, "still bounded"
    _assert_span_is_the_exact_source_slice(fact, text)
    assert fact.normalized_value is None, "a 200-digit token must not be normalized"


def test_r18_a_span_stays_within_page_bounds():
    """The span must never address text outside the page it belongs to."""
    text = "Test: Glucose Value: 105 mg/dL"
    facts = _parse(text)

    fact = facts[0]
    assert 0 <= fact.char_start < fact.char_end <= len(text)
    assert fact.page_index == 0


# =============================================================================
# B — empty token after an existing label
# =============================================================================


def test_r18_b_bare_value_label_still_produces_preserved_evidence():
    """``Test: Glucose Value:`` with nothing after it must not vanish.

    The label proves the document declares a measurement. Dropping the line meant no
    candidate existed, so no blocker could be raised against it.
    """
    text = (
        "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
        "Report date: 2026-10-20\n"
        "Test: Glucose Value:\n"
        "Reference range: 70 - 110 mg/dL\n"
    )
    facts = _parse(text)

    assert len(facts) == 1, "a declared measurement with no token must still be recorded"
    fact = facts[0]
    assert fact.normalized_value is None, "no number may be fabricated"
    assert QualityFlag.PAGE_MISSING in fact.quality_flags
    assert fact.raw_text, "the evidence must be a literal, non-empty source slice"
    _assert_span_is_the_exact_source_slice(fact, text)


def test_r18_b_bare_label_evidence_is_the_label_itself():
    """The preserved evidence is the label text, not an invented placeholder."""
    text = "Report date: 2026-10-20\nTest: Glucose Value:\n"
    facts = _parse(text)

    fact = facts[0]
    assert fact.raw_text.strip().rstrip(":").lower() == "value", (
        f"expected the literal label as evidence, got {fact.raw_text!r}"
    )
    _assert_span_is_the_exact_source_slice(fact, text)


def test_r18_b_trailing_whitespace_only_is_still_empty():
    """A label followed only by spaces is still an empty measurement."""
    text = "Test: Glucose Value:    \nReport date: 2026-10-20\n"
    facts = _parse(text)

    assert len(facts) == 1
    assert facts[0].normalized_value is None
    _assert_span_is_the_exact_source_slice(facts[0], text)


# --- HTTP: the bare label cannot reach verified ------------------------------


def _inject_ocr(monkeypatch, text: str, *, confidence: float = 0.95) -> None:
    from app.services.documents import intake, ocr

    def _fake_run_ocr(image, *, tesseract_cmd, language, preprocessing):
        return ocr.OcrResult(
            text=text, confidence=confidence, tool_version="scripted-engine-not-tesseract"
        )

    monkeypatch.setattr(intake, "run_ocr", _fake_run_ocr)


def _upload_scan(api, patient_headers, fixtures) -> str:
    payload = fixtures.build_legible_scan_image("report_ocr_o_confusion.txt")
    response = api.post(
        UPLOAD, headers=patient_headers, files={"file": ("scan.png", payload, "image/png")}
    )
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def _extraction(api, doctor_headers, document_id: str) -> dict:
    response = api.get(f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers)
    assert response.status_code == 200, response.text
    return response.json()


def _status(api, doctor_headers, document_id: str) -> str:
    return api.get(f"/api/v1/documents/{document_id}", headers=doctor_headers).json()[
        "extraction_status"
    ]


BARE_LABEL_TEXT = (
    "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
    "\n"
    "Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20\n"
    "Test: Glucose Value:\n"
    "\n"
    "Reference range: 70 - 110 mg/dL\n"
)


def test_r18_b_bare_label_raises_vi_005_and_creates_no_observation(
    api, patient_headers, doctor_headers, fixtures, db, monkeypatch
):
    """HTTP: a bare label must produce a blocking ``VI-005``, not a silent document."""
    from app.db.models import ExtractedFact, Observation

    _inject_ocr(monkeypatch, BARE_LABEL_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    value_facts = [f for f in body["facts"] if f["field_name"] == "value"]
    assert len(value_facts) == 1, "the declared measurement must be recorded as evidence"
    assert value_facts[0]["normalized_value"] is None
    assert "page_missing" in value_facts[0]["quality_flags"]

    issue_types = {issue["issue_type"] for issue in body["verification_issues"]}
    assert "VI-005" in issue_types, (
        f"a declared but unread measurement must raise VI-005; got {sorted(issue_types)}"
    )

    fact_ids = {
        fact.id for fact in db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id)
    }
    assert not db.query(Observation).filter(Observation.source_fact_id.in_(fact_ids)).all()


def test_r18_b_bare_label_cannot_reach_verified_after_approving_other_facts(
    api, patient_headers, doctor_headers, fixtures, db, monkeypatch
):
    """HTTP: the exact fail-closed property R17 established, for the bare-label case.

    Approving every *non-measurement* fact must never produce ``verified`` while the
    declared measurement is unread.
    """
    from app.db.models import ExtractedFact, Observation

    _inject_ocr(monkeypatch, BARE_LABEL_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    non_measurement = [f for f in body["facts"] if f["field_name"] != "value"]
    assert non_measurement, "precondition: the document carries other readable facts"

    for fact in non_measurement:
        response = api.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={"fact_id": fact["fact_id"], "decision": "verified"},
        )
        assert response.status_code == 200, response.text

    assert _status(api, doctor_headers, document_id) != "verified", (
        "a document that declares a measurement it never read must not become verified"
    )

    after = _extraction(api, doctor_headers, document_id)
    assert "VI-005" in {issue["issue_type"] for issue in after["verification_issues"]}, (
        "VI-005 must remain open until the measurement is actually resolved"
    )

    fact_ids = {
        fact.id for fact in db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id)
    }
    assert not db.query(Observation).filter(Observation.source_fact_id.in_(fact_ids)).all(), (
        "no observation may be derived from an unread measurement"
    )


def test_r18_b_bare_label_is_not_treated_as_document_only(
    api, patient_headers, doctor_headers, fixtures, db, monkeypatch
):
    """Control: the bare label differs from a report that never declared a measurement.

    A title/reference-only document legitimately raises no missing-measurement
    blocker; a bare ``Value:`` label is a declaration and must be treated differently.
    """
    document_only = (
        "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
        "\n"
        "Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20\n"
        "\n"
        "Reference range: 70 - 110 mg/dL\n"
    )
    _inject_ocr(monkeypatch, document_only)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    assert not [f for f in body["facts"] if f["field_name"] == "value"]
    assert "VI-005" not in {issue["issue_type"] for issue in body["verification_issues"]}
