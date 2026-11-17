"""Regression suite for P3-R17: OCR substitution and end-to-end safety.

Written **before** the fix and failing against the reviewed head ``1b17a9a``.

Scope and honest labelling
--------------------------
The OCR text in every test here is **injected** by monkeypatching
``intake.run_ocr``. This is deliberate and is the only honest option in this
sandbox: there is no Tesseract binary, so nothing here is real-engine evidence.
Real recognition fidelity stays with the owner's Windows run (``OCR-RF`` axis in
``docs/phase-reports/P3_R17_OCR_SUBSTITUTION_ANALYSIS.md``).

What these tests *do* prove is the thing the engine cannot absolve: **what the
application does with engine output it cannot verify**. That is engine
independent, so a scripted engine is a valid instrument here and not a
substitute for the real one.

The text used by ``OWNER_OCR_TEXT`` is the owner's real Windows output at
``1b17a9a``, reproduced byte for byte:

    Test: Glucose Value: 105 mg/dL

One space before ``Value:``, ``105`` substituted for the source's ``1O5``.
The committed source is ``data/synthetic/documents/sources/report_ocr_o_confusion.txt``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DocumentStatus, IssueType
from app.db.models import ExtractedFact, FactVerification, Observation, VerificationIssue

UPLOAD = "/api/v1/documents/upload"

#: The owner's real Windows OCR output at ``1b17a9a``, verbatim.
OWNER_OCR_TEXT = (
    "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
    "\n"
    "Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20\n"
    "Test: Glucose Value: 105 mg/dL\n"
    "\n"
    "Reference range: 70 - 110 mg/dL\n"
)

#: Same content with the two-space column gap the parser requires, engine value
#: still substituted. This is the "parseable but substituted" pathway.
PARSEABLE_SUBSTITUTED_TEXT = OWNER_OCR_TEXT.replace(
    "Test: Glucose Value:", "Test: Glucose              Value:"
)

#: Two-space gap with the ambiguous token preserved: the case that *may* pass.
PARSEABLE_PRESERVED_TEXT = PARSEABLE_SUBSTITUTED_TEXT.replace("Value: 105", "Value: 1O5")

#: A measurement line the parser cannot read at all because the label was lost.
LOST_LABEL_TEXT = (
    "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
    "\n"
    "Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20\n"
    "Test Gluccse 105 mgldl\n"
    "\n"
    "Reference range: 70 - 110 mg/dL\n"
)

#: A genuinely document-only report: no measurement line was ever printed.
NO_MEASUREMENT_TEXT = (
    "SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD\n"
    "\n"
    "Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20\n"
    "\n"
    "Reference range: 70 - 110 mg/dL\n"
)


# --- helpers -----------------------------------------------------------------


def _inject_ocr(monkeypatch, text: str, *, confidence: float = 0.95) -> None:
    """Make the OCR path return exactly ``text``.

    The engine is scripted: this is a **simulation** of engine output, never a
    real-engine measurement.
    """
    from app.services.documents import intake, ocr

    def _fake_run_ocr(image, *, tesseract_cmd, language, preprocessing):
        return ocr.OcrResult(
            text=text,
            confidence=confidence,
            tool_version="scripted-engine-not-tesseract",
        )

    monkeypatch.setattr(intake, "run_ocr", _fake_run_ocr)


def _upload_scan(api, patient_headers, fixtures, *, filename: str = "scan.png") -> str:
    """Upload the committed rendered scan fixture and return the document id."""
    payload = fixtures.build_legible_scan_image("report_ocr_o_confusion.txt")
    response = api.post(
        UPLOAD,
        headers=patient_headers,
        files={"file": (filename, payload, "image/png")},
    )
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def _extraction(api, doctor_headers, document_id: str) -> dict:
    response = api.get(f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers)
    assert response.status_code == 200, response.text
    return response.json()


def _facts_by_field(body: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for fact in body["facts"]:
        grouped.setdefault(fact["field_name"], []).append(fact)
    return grouped


def _issue_types(body: dict) -> set[str]:
    return {issue["issue_type"] for issue in body["verification_issues"]}


def _verify(api, doctor_headers, document_id: str, fact_id: str, **body):
    return api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={"fact_id": fact_id, "decision": "verified", **body},
    )


def _document_observations(db: Session, document_id: str) -> list[Observation]:
    """Return observations derived from ``document_id`` only."""
    fact_ids = {
        fact.id
        for fact in db.execute(
            select(ExtractedFact).where(ExtractedFact.document_id == document_id)
        ).scalars()
    }
    if not fact_ids:
        return []
    return list(
        db.execute(select(Observation).where(Observation.source_fact_id.in_(fact_ids))).scalars()
    )


def _issue_row(db: Session, document_id: str, issue_type: str) -> VerificationIssue | None:
    return db.execute(
        select(VerificationIssue).where(
            VerificationIssue.document_id == document_id,
            VerificationIssue.issue_type == issue_type,
        )
    ).scalar_one_or_none()


def _status(api, doctor_headers, document_id: str) -> str:
    response = api.get(f"/api/v1/documents/{document_id}", headers=doctor_headers)
    assert response.status_code == 200, response.text
    return response.json()["extraction_status"]


# =============================================================================
# P0 — fail-closed document verification
# =============================================================================


def test_r17_owner_ocr_text_surfaces_the_missing_measurement(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0: the owner's real OCR line must not vanish silently.

    The engine emitted a full measurement line. The parser produced no value
    fact because the column gap is one space. The document must therefore carry
    a blocker that says a measurement could not be read — not merely the generic
    "N facts are unverified", which is identical to a document with no
    measurement at all.
    """
    _inject_ocr(monkeypatch, OWNER_OCR_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)

    # The index still cannot read the line, so no number may be produced. What
    # must change is that the *evidence* survives as a fact instead of vanishing.
    value_facts = _facts_by_field(body).get("value", [])
    assert len(value_facts) == 1, (
        "the printed measurement must be retained as evidence rather than dropped"
    )
    unread = value_facts[0]
    assert unread["normalized_value"] is None, "no number may be invented for an unread line"
    assert "page_missing" in unread["quality_flags"], (
        "the documented `page_missing` flag is the contract's marker for a value the "
        f"page declared but the extraction could not use; got {unread['quality_flags']}"
    )
    assert unread["evidence"]["extractor"] == "tesseract"

    issue_types = _issue_types(body)
    assert IssueType.VI_005.value in issue_types, (
        "an OCR line containing a value that produced no usable value must raise "
        f"VI-005 (unreadable value); got {sorted(issue_types)}"
    )

    row = _issue_row(db, document_id, IssueType.VI_005.value)
    assert row is not None
    assert row.reason_code == "value_unreadable"
    assert row.blocking == 1


def test_r17_missing_measurement_never_reaches_verified(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0: `verified` must require a measurement, not just any decided fact."""
    _inject_ocr(monkeypatch, OWNER_OCR_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    for fact in body["facts"]:
        response = _verify(api, doctor_headers, document_id, fact["fact_id"])
        assert response.status_code == 200, response.text

    assert _status(api, doctor_headers, document_id) != DocumentStatus.VERIFIED.value, (
        "a document with no measurement value fact must never be reported verified"
    )
    assert _document_observations(db, document_id) == []


def test_r17_missing_measurement_blocks_document(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0: the blocks-everything state, distinct from `verified` and from `failed`."""
    _inject_ocr(monkeypatch, OWNER_OCR_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    for fact in body["facts"]:
        _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert _status(api, doctor_headers, document_id) == DocumentStatus.NEEDS_VERIFICATION.value
    assert IssueType.VI_005.value in _issue_types(_extraction(api, doctor_headers, document_id))


def test_r17_document_only_report_is_not_a_failed_measurement(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0: a report that never printed a measurement must not be labelled unreadable.

    This is the control that stops the fix from over-firing: a title/reference-only
    document legitimately has no value, so it must not raise the missing-measurement
    blocker. It stays document-only and unmapped.
    """
    _inject_ocr(monkeypatch, NO_MEASUREMENT_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    assert "value" not in _facts_by_field(body)

    row = _issue_row(db, document_id, IssueType.VI_005.value)
    assert row is None or row.reason_code != "measurement_not_read", (
        "a document-only report must not be reported as a failed measurement read"
    )

    for fact in body["facts"]:
        _verify(api, doctor_headers, document_id, fact["fact_id"])
    assert _document_observations(db, document_id) == []


def test_r17_lost_label_line_cannot_reach_verified(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0 limit, stated honestly: a destroyed label is *not* detectable.

    When OCR damages the ``Value:`` label itself, no deterministic signal remains
    that the document ever declared a measurement. The parser cannot invent one,
    so no blocker can be raised and the document looks document-only.

    What this test does assert is the property that actually protects the
    patient: such a document still cannot manufacture an observation, and the
    owner's real OCR (which preserved the label) *is* covered by the test above.
    Detectable-loss and undetectable-loss are different risks and are kept
    separate here rather than blurred into one passing claim.
    """
    _inject_ocr(monkeypatch, LOST_LABEL_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    assert "value" not in _facts_by_field(body), (
        "precondition: with the label destroyed there is nothing to attach evidence to"
    )

    for fact in body["facts"]:
        _verify(api, doctor_headers, document_id, fact["fact_id"])
    assert _document_observations(db, document_id) == []


def test_r17_substituted_value_creates_no_observation_without_a_decision(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P0/P124 guard: parsing alone must never create a trusted measurement.

    The substituted ``105`` is indistinguishable from a clean read once parsed.
    What protects the patient is that it is `pending` until a doctor decides.
    This test locks that in so a future fix cannot quietly relax it.
    """
    _inject_ocr(monkeypatch, PARSEABLE_SUBSTITUTED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    value_facts = _facts_by_field(body)["value"]
    assert len(value_facts) == 1
    assert value_facts[0]["verification_status"] == "pending"
    assert value_facts[0]["normalized_value"] == "105"
    assert _document_observations(db, document_id) == []


def test_r17_preserved_token_is_flagged_never_repaired(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """GOLD-EX-11 semantics: `1O5` is flagged, never silently normalized."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)

    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]
    assert value["raw_text"] == "1O5"
    assert value["normalized_value"] is None
    assert "unparseable_value" in value["quality_flags"]
    assert IssueType.VI_005.value in _issue_types(body)
    assert _document_observations(db, document_id) == []


# =============================================================================
# P1 — correction and issue lifecycle integrity
# =============================================================================


def test_r17_rejecting_a_substituted_value_creates_no_observation(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """A doctor who spots the substitution rejects it: nothing is promoted."""
    _inject_ocr(monkeypatch, PARSEABLE_SUBSTITUTED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)

    value = _facts_by_field(body)["value"][0]
    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={"fact_id": value["fact_id"], "decision": "rejected", "reason": "ocr substitution"},
    )
    assert response.status_code == 200, response.text
    assert _document_observations(db, document_id) == []


# --- correction value validation (field-specific) ----------------------------


@pytest.mark.parametrize(
    ("label", "corrected_value"),
    [
        ("whitespace only", "   "),
        ("non-numeric text", "abc"),
        ("mixed alphanumeric", "10x5"),
        ("not-a-number sentinel", "nan"),
        ("not finite", "inf"),
        ("value with newline", "10\n5"),
    ],
)
def test_r17_measurement_correction_rejects_inadmissible_values(
    api,
    patient_headers,
    doctor_headers,
    fixtures,
    db: Session,
    monkeypatch,
    label: str,
    corrected_value: str,
):
    """P1: a measurement correction must be a number, not any non-empty string."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": corrected_value,
            "reason": "ocr check",
        },
    )
    assert response.status_code == 400, (
        f"{label}: corrected measurement value {corrected_value!r} must be refused, "
        f"got {response.status_code} {response.text[:200]}"
    )

    # Nothing may have been accepted as a verified measurement.
    row = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == document_id,
            ExtractedFact.field_name == "value",
            ExtractedFact.verification_status == "verified",
        )
    ).scalar_one_or_none()
    assert row is None


def test_r17_measurement_correction_accepts_a_valid_number(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """Control: the validation must not block a legitimate source-reviewed correction."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    assert (
        api.get(f"/api/v1/documents/{document_id}/file", headers=doctor_headers).status_code == 200
    )
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "confirmed_unit": "mg/dL",
            "source_image_compared": True,
            "reason": "checked source image",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["fact"]["normalized_value"] == "105"
    assert payload["verification"]["decision"] == "corrected"


def test_r17_correction_keeps_the_original_ocr_evidence(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: lineage must keep `raw_text='1O5'` beside the accepted `105`."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    assert (
        api.get(f"/api/v1/documents/{document_id}/file", headers=doctor_headers).status_code == 200
    )
    body = _extraction(api, doctor_headers, document_id)
    original = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": original["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "confirmed_unit": "mg/dL",
            "source_image_compared": True,
            "reason": "checked source image",
        },
    )
    assert response.status_code == 200, response.text

    after = _extraction(api, doctor_headers, document_id)
    value_rows = _facts_by_field(after)["value"]
    assert len(value_rows) == 2, "history is retained, not rewritten"

    superseded = next(row for row in value_rows if row["verification_status"] == "rejected")
    corrected = next(row for row in value_rows if row["verification_status"] == "verified")

    assert superseded["fact_id"] == original["fact_id"]
    assert superseded["raw_text"] == "1O5", "the original excerpt is immutable"
    assert superseded["normalized_value"] is None
    assert corrected["raw_text"] == "1O5", (
        "a correction must not rewrite the excerpt to claim the page printed 105"
    )
    assert corrected["normalized_value"] == "105"

    corrected_row = db.get(ExtractedFact, corrected["fact_id"])
    assert corrected_row.corrected_from_fact_id == original["fact_id"]

    verification = db.execute(
        select(FactVerification).where(FactVerification.fact_id == original["fact_id"])
    ).scalar_one()
    assert verification.decision == "corrected"
    assert verification.new_value == "105"
    assert verification.previous_value is None
    assert verification.reason == "checked source image"


# --- VI-005 lifecycle --------------------------------------------------------


def test_r17_valid_correction_resolves_vi_005(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: a corrected value must clear the unreadable-value blocker it fixed."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    assert (
        api.get(f"/api/v1/documents/{document_id}/file", headers=doctor_headers).status_code == 200
    )
    body = _extraction(api, doctor_headers, document_id)
    assert IssueType.VI_005.value in _issue_types(body)

    value = _facts_by_field(body)["value"][0]
    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "confirmed_unit": "mg/dL",
            "source_image_compared": True,
            "reason": "checked source image",
        },
    )
    assert response.status_code == 200, response.text

    after = _extraction(api, doctor_headers, document_id)
    assert IssueType.VI_005.value not in _issue_types(after), (
        "VI-005 is still open after the value was corrected; the blocker is stuck"
    )
    resolved = _issue_row(db, document_id, IssueType.VI_005.value)
    assert resolved.state == "resolved"


def test_r17_correction_does_not_clear_unrelated_blockers(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: resolving VI-005 must not sweep other blockers away with it.

    ``VI-002`` must still be present while any other fact is undecided.
    """
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "reason": "ocr check",
        },
    )

    after = _extraction(api, doctor_headers, document_id)
    pending = [f for f in after["facts"] if f["verification_status"] == "pending"]
    if pending:
        assert IssueType.VI_002.value in _issue_types(after), (
            "other facts are still undecided, so VI-002 must remain open"
        )


def test_r17_rejection_leaves_vi_005_open(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: rejecting is not correcting — the read is still unreadable."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={"fact_id": value["fact_id"], "decision": "rejected", "reason": "unreadable"},
    )
    assert response.status_code == 200, response.text

    after = _extraction(api, doctor_headers, document_id)
    assert IssueType.VI_005.value in _issue_types(after), (
        "rejecting a value leaves no reading at all; VI-005 must stay open"
    )


# --- corrected unit validation ----------------------------------------------


def test_r17_correction_rejects_an_unsupported_unit(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: corrected units obey the existing document unit contract."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "corrected_unit": "mmol/L",
            "reason": "ocr check",
        },
    )
    assert response.status_code == 400, (
        "mmol/L is outside the document unit list and must be refused, "
        f"got {response.status_code} {response.text[:200]}"
    )


def test_r17_correction_accepts_a_supported_unit(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """Control: an allowlisted unit is accepted when source-reviewed."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    assert (
        api.get(f"/api/v1/documents/{document_id}/file", headers=doctor_headers).status_code == 200
    )
    body = _extraction(api, doctor_headers, document_id)
    value = _facts_by_field(body)["value"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": value["fact_id"],
            "decision": "corrected",
            "corrected_value": "105",
            "corrected_unit": "mg/dL",
            "source_image_compared": True,
            "reason": "ocr check",
        },
    )
    assert response.status_code == 200, response.text


def test_r17_date_correction_is_not_held_to_the_numeric_rule(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: validation is field-specific; a date is not a number."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    date_fact = _facts_by_field(body)["report_date"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": date_fact["fact_id"],
            "decision": "corrected",
            "corrected_value": "2026-10-21",
            "reason": "printed date confirmed",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["fact"]["normalized_value"] == "2026-10-21"


def test_r17_date_correction_rejects_a_malformed_date(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """P1: a date correction must be an ISO date, not arbitrary text."""
    _inject_ocr(monkeypatch, PARSEABLE_PRESERVED_TEXT)
    document_id = _upload_scan(api, patient_headers, fixtures)
    body = _extraction(api, doctor_headers, document_id)
    date_fact = _facts_by_field(body)["report_date"][0]

    response = api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={
            "fact_id": date_fact["fact_id"],
            "decision": "corrected",
            "corrected_value": "not-a-date",
            "reason": "typo",
        },
    )
    assert response.status_code == 400, f"got {response.status_code} {response.text[:200]}"


# =============================================================================
# P1 — acceptance evidence must reflect real API state
# =============================================================================


def test_r17_gate_human_review_flag_is_derived_not_hardcoded():
    """P1: the probe must not assert a review state it never checked.

    ``human_review_required=True`` was a literal in the gate payload. It must be
    computed from a persisted ``verification_issue`` row for the gate's own
    document, or the gate must stop claiming it.
    """
    from pathlib import Path

    source = Path("scripts/python/windows_ocr_acceptance.py").read_text(encoding="utf-8")
    assert '"human_review_required": True' not in source, (
        "the acceptance payload still hard-codes human_review_required=True; it must be "
        "derived from the persisted verification issues"
    )
    assert "human_review_required" in source, (
        "the field should be reported, but derived rather than asserted"
    )
