"""Stage 3 RED-first verification safety hardening tests (`G11-D1`..`G11-D6`).

Covers all 9 mandatory Stage 3 scenarios:
1. `G11-D1`: `GOLD-EX-11` (`report_ocr_o_confusion.txt`, `1O5`, parser refusal) unchanged.
2. `G11-D2`: Fresh post-extraction `GET /file` audit required (pre-extraction / stale /
   failed / other-doctor / other-doc reads fail closed; fresh post-extraction read succeeds).
3. `G11-D3`: Non-measurement OCR `report_date` requires source confirmation + matching
   `confirmed_value` (and `ambiguous_date` cannot verify as-is).
4. `G11-D3`: Non-measurement OCR `test_name` and `reference_text` require source confirmation
   + matching `confirmed_value` (`requires_source_confirmation=True` on all OCR facts).
5. `G11-D4`: Pending-sibling unit consistency check (cannot override/diverge from `pending`
   sibling unit on `value` correction, nor verify disagreeing `pending` siblings; `WRONG_UNIT_OCR`
   remains recoverable via `unit` correction first without deadlock).
6. `G11-D5`: Defense-in-depth in `_create_observation_from_mapping` checks `confirmed_value`,
   sibling `unit` `confirmed_unit`, fresh post-extraction `GET /file`, and non-measurement OCR
   confirmations.
7. `G11-D6`: Mandatory `reason` on OCR `decision='corrected'` across all declared fields.
8. `G11-D6`: Mandatory `reason` on OCR `decision='verified'` when confusable digits
   (`0`/`1`/`5`/`8`) are present (while non-confusable OCR facts succeed without `reason`).
9. End-to-end full Stage 3 OCR promotion, R21 rejection preservation, and `pypdf` compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.enums import ActorType, AuditOutcome, ExtractionPath, FactField
from app.core.paths import REPO_ROOT
from app.db.models import (
    AuditEvent,
    Document,
    ExtractedFact,
    ExtractionAttempt,
    FactVerification,
    Observation,
)
from app.services.documents.field_parser import _normalize_number
from app.services.documents.intake import accept_upload, run_extraction
from app.services.documents.verification import _create_observation_from_mapping

UPLOAD = "/api/v1/documents/upload"

CLEAN_GLUCOSE_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
    "Test: Fasting glucose     Value: 104 mg/dL\n"
    "Reference range: 70 - 99 mg/dL\n"
)

SUBSTITUTED_105_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-10-20\n"
    "Test: Glucose              Value: 105 mg/dL\n"
    "Reference range: 70 - 110 mg/dL\n"
)

NO_CONFUSABLE_DIGITS_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
    "Test: Glucose              Value: 74 mg/dL\n"
    "Reference range: 70 - 99 mg/dL\n"
)

AMBIGUOUS_DATE_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 03/11/2026\n"
    "Test: Glucose              Value: 104 mg/dL\n"
    "Reference range: 70 - 99 mg/dL\n"
)

WRONG_UNIT_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
    "Test: Fasting glucose     Value: 104 g/dL\n"
    "Reference range: 70 - 99 mg/dL\n"
)

PRESERVED_1O5_OCR = (
    "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
    "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
    "Test: Fasting glucose     Value: 1O5 mg/dL\n"
    "Reference range: 70 - 99 mg/dL\n"
)


# --- helpers -----------------------------------------------------------------


def _inject_ocr(monkeypatch, text_out: str, *, confidence: float = 0.95) -> None:
    from app.services.documents import intake, ocr

    def _fake_run_ocr(image, *, tesseract_cmd, language, preprocessing):
        return ocr.OcrResult(
            text=text_out,
            confidence=confidence,
            tool_version="scripted-engine-stage3",
        )

    monkeypatch.setattr(intake, "run_ocr", _fake_run_ocr)


def _upload_scan(
    api,
    patient_headers,
    fixtures,
    *,
    filename: str = "scan-stage3.png",
    source_name: str = "report_a_glucose.txt",
) -> str:
    payload = fixtures.build_legible_scan_image(source_name)
    resp = api.post(
        UPLOAD,
        headers=patient_headers,
        files={"file": (filename, payload, "image/png")},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()["document_id"]


def _extraction(api, doctor_headers, document_id: str) -> dict:
    resp = api.get(f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _facts_by_field(ext_body: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for fact in ext_body["facts"]:
        grouped.setdefault(fact["field_name"], []).append(fact)
    return grouped


def _verify(api, doctor_headers, document_id: str, fact_id: str, **body):
    return api.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=doctor_headers,
        json={"fact_id": fact_id, "decision": "verified", **body},
    )


def _fetch_file(api, headers, document_id: str) -> bytes:
    resp = api.get(f"/api/v1/documents/{document_id}/file", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.content


def _clear_same_day_glucose(db: Session) -> None:
    for row in db.execute(
        select(Observation).where(Observation.measure_type == "glucose")
    ).scalars():
        if row.measured_at.startswith(("2026-10-20", "2026-11-02")):
            db.delete(row)
    db.commit()


def _document_observations(db: Session, document_id: str) -> list[Observation]:
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


def _doctor_user_id(db: Session, username: str = "demo_doctor") -> str:
    return db.execute(text("SELECT id FROM user WHERE username = :u"), {"u": username}).scalar_one()


# =============================================================================
# Scenario 1 (G11-D1): GOLD-EX-11 source & parser integrity preserved
# =============================================================================


def test_stage3_s1_g11_d1_gold_ex_11_source_and_parser_unmodified(fixtures):
    """G11-D1: `report_ocr_o_confusion.txt` stays `1O5` and parser still refuses `1O5`."""
    source_path = (
        REPO_ROOT / "data" / "synthetic" / "documents" / "sources" / "report_ocr_o_confusion.txt"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "1O5 mg/dL" in source_text
    assert "105 mg/dL" not in source_text
    assert _normalize_number("1O5") is None

    img1 = fixtures.build_legible_scan_image("report_ocr_o_confusion.txt", fmt="PNG")
    img2 = fixtures.build_legible_scan_image("report_ocr_o_confusion.txt", fmt="PNG")
    assert img1 == img2
    assert img1.startswith(b"\x89PNG")


# =============================================================================
# Scenario 2 (G11-D2): Fresh post-extraction GET /file audit enforcement
# =============================================================================


def test_stage3_s2_g11_d2_pre_extraction_and_stale_file_read_are_refused(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D2: Pre-extraction GET /file and pre-re-extraction stale GET /file fail closed."""
    from app.core.config import get_settings

    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)

    patient_id = db.execute(
        text("SELECT patient_id FROM user WHERE username = 'demo_patient_a'")
    ).scalar_one()
    patient_uid = db.execute(
        text("SELECT id FROM user WHERE username = 'demo_patient_a'")
    ).scalar_one()

    # Step 1: accept_upload leaves status pending_extraction (no ExtractionAttempt yet).
    t_upload = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
    outcome = accept_upload(
        db,
        patient_id=patient_id,
        uploaded_by_user_id=patient_uid,
        payload=fixtures.build_legible_scan_image("report_a_glucose.txt"),
        original_filename="pre-extract.png",
        declared_type="image/png",
        settings=get_settings(),
        now=t_upload,
    )
    db.commit()
    doc_id = outcome.document.id

    # Doctor reads GET /file BEFORE extraction runs (under same FIXED_NOW timestamp).
    _fetch_file(api, doctor_headers, doc_id)

    # Now extraction runs AFTER that GET /file (both same second FIXED_NOW and later check).
    doc_row = db.get(Document, doc_id)
    assert doc_row is not None
    run_extraction(db, document=doc_row, settings=get_settings(), now=t_upload)
    db.commit()

    ext = _extraction(api, doctor_headers, doc_id)
    value_fact = _facts_by_field(ext)["value"][0]

    # Pre-extraction GET /file MUST NOT satisfy source review for either verified or corrected!
    pre_verify = _verify(
        api,
        doctor_headers,
        doc_id,
        value_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="checked pre-extraction image",
    )
    assert pre_verify.status_code == 400, pre_verify.text
    assert pre_verify.json()["code"] == "E_VALIDATION"

    pre_correct = _verify(
        api,
        doctor_headers,
        doc_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
        source_image_compared=True,
        reason="attempted correction with stale file read",
    )
    assert pre_correct.status_code == 400, pre_correct.text
    assert pre_correct.json()["code"] == "E_VALIDATION"

    # Also negative controls: patient GET /file, denied audit row, and another doc GET /file do NOT satisfy.
    other_doc_id = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="other-doc.png",
        source_name="report_a_clean.txt",
    )
    _fetch_file(api, patient_headers, doc_id)
    _fetch_file(api, doctor_headers, other_doc_id)
    db.add(
        AuditEvent(
            event_type="document.file_read",
            actor_type=ActorType.USER.value,
            actor_id=_doctor_user_id(db),
            patient_id=patient_id,
            subject_type="document",
            subject_id=doc_id,
            outcome=AuditOutcome.DENIED.value,
            safe_detail="route=GET /api/v1/documents/{document_id}/file; reason=denied",
            idempotency_key=f"denied-file-read-{doc_id}",
            created_at="2026-11-16T18:00:00Z",
        )
    )
    db.commit()
    still_pre = _verify(
        api,
        doctor_headers,
        doc_id,
        value_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="patient read + other doc read only",
    )
    assert still_pre.status_code == 400, still_pre.text

    # Now doctor fetches GET /file AFTER extraction -> fresh audit unblocks verification.
    _fetch_file(api, doctor_headers, doc_id)
    fresh_verify = _verify(
        api,
        doctor_headers,
        doc_id,
        value_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="fresh post-extraction file review",
    )
    assert fresh_verify.status_code == 200, fresh_verify.text


def test_stage3_s2_g11_d2_newer_attempt_timestamp_invalidates_older_file_read(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D2: A file read with timestamp strictly earlier than latest ExtractionAttempt fails."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="stale-ts.png")

    # Doctor fetches GET /file (at FIXED_NOW 2026-11-14T12:00:00Z).
    _fetch_file(api, doctor_headers, doc_id)

    # Simulate a later extraction attempt strictly after the file read.
    db.add(
        ExtractionAttempt(
            document_id=doc_id,
            path=ExtractionPath.TESSERACT.value,
            preprocessing="grayscale_upscale",
            engine_confidence=0.95,
            text_char_count=120,
            page_from=0,
            page_to=0,
            succeeded=1,
            error_code=None,
            duration_ms=5,
            tool_version="scripted-engine-stage3",
            created_at="2026-11-16T15:00:00Z",
        )
    )
    db.commit()

    ext = _extraction(api, doctor_headers, doc_id)
    value_fact = _facts_by_field(ext)["value"][0]
    resp = _verify(
        api,
        doctor_headers,
        doc_id,
        value_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="old file read before re-extraction",
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "E_VALIDATION"
    assert db.execute(select(FactVerification)).scalars().all() == []


# =============================================================================
# Scenario 3 (G11-D3): OCR `report_date` confirmation & ambiguous date refusal
# =============================================================================


def test_stage3_s3_g11_d3_ocr_report_date_requires_source_confirmation(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D3: OCR `report_date` requires GET /file, source_image_compared, and confirmed_value."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="date-check.png")

    ext = _extraction(api, doctor_headers, doc_id)
    date_fact = _facts_by_field(ext)["report_date"][0]
    assert date_fact["requires_source_confirmation"] is True

    # Before GET /file: both bare verify and confirmed verify fail closed.
    assert _verify(api, doctor_headers, doc_id, date_fact["fact_id"]).status_code == 400
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            date_fact["fact_id"],
            source_image_compared=True,
            confirmed_value="2026-11-02",
            reason="confirmed date",
        ).status_code
        == 400
    )

    _fetch_file(api, doctor_headers, doc_id)

    # After GET /file: missing flag, missing confirmed_value, mismatched date, bad date fail.
    for bad in (
        {"confirmed_value": "2026-11-02", "reason": "confirmed date"},
        {"source_image_compared": True, "reason": "confirmed date"},
        {"source_image_compared": True, "confirmed_value": "2026-11-03", "reason": "wrong date"},
        {"source_image_compared": True, "confirmed_value": "not-a-date", "reason": "malformed"},
    ):
        resp = _verify(api, doctor_headers, doc_id, date_fact["fact_id"], **bad)
        assert resp.status_code == 400, (bad, resp.text)
        assert resp.json()["code"] == "E_VALIDATION"

    ok = _verify(
        api,
        doctor_headers,
        doc_id,
        date_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="2026-11-02",
        reason="verified printed date against scan",
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification"]["source_image_compared"] is True
    assert ok.json()["verification"]["confirmed_value"] == "2026-11-02"


def test_stage3_s3_g11_d3_ambiguous_ocr_date_cannot_be_verified_as_is(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D3: Ambiguous OCR `report_date` (`03/11/2026`) cannot pass `decision='verified'`."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, AMBIGUOUS_DATE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="ambig-date.png")
    _fetch_file(api, doctor_headers, doc_id)

    date_fact = _facts_by_field(_extraction(api, doctor_headers, doc_id))["report_date"][0]
    assert date_fact["normalized_value"] is None

    bad = _verify(
        api,
        doctor_headers,
        doc_id,
        date_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="2026-11-03",
        reason="tried verified on ambiguous date",
    )
    assert bad.status_code == 400, bad.text
    assert bad.json()["code"] == "E_VALIDATION"

    ok = _verify(
        api,
        doctor_headers,
        doc_id,
        date_fact["fact_id"],
        decision="corrected",
        corrected_value="2026-11-03",
        source_image_compared=True,
        reason="confirmed day-first format from source header",
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["fact"]["normalized_value"] == "2026-11-03"


# =============================================================================
# Scenario 4 (G11-D3): OCR `test_name` & `reference_text` source confirmation
# =============================================================================


def test_stage3_s4_g11_d3_ocr_test_name_and_reference_text_require_source_confirmation(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D3: OCR `test_name` & `reference_text` enforce `requires_source_confirmation`."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="non-meas.png")

    by_field = _facts_by_field(_extraction(api, doctor_headers, doc_id))
    test_fact = by_field["test_name"][0]
    ref_fact = by_field["reference_text"][0]
    assert test_fact["requires_source_confirmation"] is True
    assert ref_fact["requires_source_confirmation"] is True

    # Without GET /file -> 400
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            test_fact["fact_id"],
            source_image_compared=True,
            confirmed_value="Fasting glucose",
        ).status_code
        == 400
    )
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            ref_fact["fact_id"],
            source_image_compared=True,
            confirmed_value="70 - 99 mg/dL",
            reason="checked ref range",
        ).status_code
        == 400
    )

    _fetch_file(api, doctor_headers, doc_id)

    # Bare / missing / mismatched confirmed_value -> 400
    assert _verify(api, doctor_headers, doc_id, test_fact["fact_id"]).status_code == 400
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            test_fact["fact_id"],
            source_image_compared=True,
            confirmed_value="Hemoglobin",
        ).status_code
        == 400
    )
    assert _verify(api, doctor_headers, doc_id, ref_fact["fact_id"]).status_code == 400
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            ref_fact["fact_id"],
            source_image_compared=True,
            confirmed_value="70 - 140 mg/dL",
            reason="checked ref",
        ).status_code
        == 400
    )

    ok_test = _verify(
        api,
        doctor_headers,
        doc_id,
        test_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="Fasting glucose",
    )
    assert ok_test.status_code == 200, ok_test.text
    assert ok_test.json()["verification"]["confirmed_value"] == "Fasting glucose"

    ok_ref = _verify(
        api,
        doctor_headers,
        doc_id,
        ref_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="70 - 99 mg/dL",
        reason="confirmed reference interval on source scan",
    )
    assert ok_ref.status_code == 200, ok_ref.text
    assert ok_ref.json()["verification"]["confirmed_value"] == "70 - 99 mg/dL"


# =============================================================================
# Scenario 5 (G11-D4): Pending-sibling unit consistency check
# =============================================================================


def test_stage3_s5_g11_d4_pending_sibling_unit_conflict_fails_regardless_of_order(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D4: Conflicting `corrected_unit` on `value` fails even when `unit` is still `pending`."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="pending-unit.png")
    _fetch_file(api, doctor_headers, doc_id)

    by_field = _facts_by_field(_extraction(api, doctor_headers, doc_id))
    val_fact = by_field["value"][0]
    unit_fact = by_field["unit"][0]
    assert unit_fact["verification_status"] == "pending"
    assert unit_fact["normalized_value"] == "mg/dL"

    # Attempt to change `value`'s unit to `g/dL` while sibling `unit` is still `pending` (`mg/dL`).
    conflict = _verify(
        api,
        doctor_headers,
        doc_id,
        val_fact["fact_id"],
        decision="corrected",
        corrected_value="104",
        corrected_unit="g/dL",
        source_image_compared=True,
        reason="attempted divergent unit correction on value",
    )
    assert conflict.status_code == 400, conflict.text
    assert conflict.json()["code"] == "E_VALIDATION"
    assert db.execute(select(FactVerification)).scalars().all() == []


def test_stage3_s5_g11_d4_pending_sibling_disagreement_blocks_verified_decision(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D4: If pending value (`mg/dL`) disagrees with pending unit (`g/dL`), neither verifies."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, WRONG_UNIT_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="pending-disagree.png")
    _fetch_file(api, doctor_headers, doc_id)

    # Manually align value.unit = mg/dL while unit sibling remains g/dL (both pending).
    val_row = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == doc_id,
            ExtractedFact.field_name == FactField.VALUE.value,
        )
    ).scalar_one()
    val_row.unit = "mg/dL"
    db.commit()

    by_field = _facts_by_field(_extraction(api, doctor_headers, doc_id))
    bad_val = _verify(
        api,
        doctor_headers,
        doc_id,
        by_field["value"][0]["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="tried verifying value against disagreeing pending unit",
    )
    assert bad_val.status_code == 400, bad_val.text

    bad_unit = _verify(
        api,
        doctor_headers,
        doc_id,
        by_field["unit"][0]["fact_id"],
        source_image_compared=True,
        confirmed_unit="g/dL",
        reason="tried verifying unit against disagreeing pending value",
    )
    assert bad_unit.status_code == 400, bad_unit.text


def test_stage3_s5_g11_d4_wrong_unit_ocr_can_be_corrected_unit_first_without_deadlock(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D4: Correcting `unit` first (`g/dL` -> `mg/dL`) then `value` avoids deadlock."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, WRONG_UNIT_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="wrong-unit-order.png")
    _fetch_file(api, doctor_headers, doc_id)

    by_field = _facts_by_field(_extraction(api, doctor_headers, doc_id))

    # Correct unit fact first -> verified mg/dL
    ok_unit = _verify(
        api,
        doctor_headers,
        doc_id,
        by_field["unit"][0]["fact_id"],
        decision="corrected",
        corrected_value="mg/dL",
        source_image_compared=True,
        reason="source image prints mg/dL",
    )
    assert ok_unit.status_code == 200, ok_unit.text

    # Then correct value fact to matching mg/dL
    ok_val = _verify(
        api,
        doctor_headers,
        doc_id,
        by_field["value"][0]["fact_id"],
        decision="corrected",
        corrected_value="104",
        corrected_unit="mg/dL",
        source_image_compared=True,
        reason="source image prints 104 mg/dL",
    )
    assert ok_val.status_code == 200, ok_val.text


# =============================================================================
# Scenario 6 (G11-D5): `_create_observation_from_mapping` defense-in-depth
# =============================================================================


@pytest.mark.parametrize(
    "tamper_mode",
    [
        "bad_value",
        "bad_unit_confirm",
        "bad_date",
        "bad_test_name",
        "missing_reason_confusable",
        "stale_read",
    ],
)
def test_stage3_s6_g11_d5_internal_mapping_guard_blocks_incomplete_ocr_confirmations(
    api,
    patient_headers,
    doctor_headers,
    fixtures,
    db: Session,
    monkeypatch,
    tamper_mode: str,
):
    """G11-D5: Direct `_create_observation_from_mapping` refuses tampered OCR verification."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename=f"tamper-{tamper_mode}.png")
    doc = db.get(Document, doc_id)
    assert doc is not None
    doctor_id = _doctor_user_id(db)

    if tamper_mode != "stale_read":
        _fetch_file(api, doctor_headers, doc_id)
    else:
        # Insert only a stale pre-extraction file read event.
        db.add(
            AuditEvent(
                event_type="document.file_read",
                actor_type=ActorType.USER.value,
                actor_id=doctor_id,
                patient_id=doc.patient_id,
                subject_type="document",
                subject_id=doc.id,
                outcome=AuditOutcome.OK.value,
                safe_detail="route=GET /api/v1/documents/{document_id}/file",
                idempotency_key=f"stale-key-{doc.id}",
                created_at="2026-11-01T00:00:00Z",
            )
        )

    facts = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == doc_id)).scalars()
    )
    for row in facts:
        row.verification_status = "verified"
        conf_val = row.normalized_value
        conf_unit = "mg/dL" if row.field_name in {"value", "unit"} else None
        reason_val: str | None = "tamper test"
        if tamper_mode == "bad_value" and row.field_name == FactField.VALUE.value:
            conf_val = "105"  # Mismatched confirmed_value while confirmed_unit matches!
        elif tamper_mode == "bad_unit_confirm" and row.field_name == FactField.UNIT.value:
            conf_unit = None  # Sibling unit lacks confirmed_unit == candidate.unit!
        elif tamper_mode == "bad_date" and row.field_name == FactField.REPORT_DATE.value:
            conf_val = None  # OCR report_date lacks confirmed_value!
        elif tamper_mode == "bad_test_name" and row.field_name == FactField.TEST_NAME.value:
            conf_val = "Hemoglobin"  # Mismatched confirmed_value on test_name!
        elif tamper_mode == "missing_reason_confusable" and row.field_name == FactField.VALUE.value:
            reason_val = None  # Value "104" includes confusable '0' and '1' without reason!
        db.add(
            FactVerification(
                fact_id=row.id,
                decision="verified",
                previous_value=row.normalized_value,
                reason=reason_val,
                verified_by_user_id=doctor_id,
                decided_at="2026-11-14T12:00:00Z",
                source_image_compared=1,
                confirmed_value=conf_val,
                confirmed_unit=conf_unit,
            )
        )
    doc.extraction_status = "verified"
    db.flush()

    value_row = next(row for row in facts if row.field_name == FactField.VALUE.value)
    created, reason = _create_observation_from_mapping(
        db,
        document=doc,
        source_fact=value_row,
        doctor_user_id=doctor_id,
        decided_at="2026-11-14T12:00:00Z",
    )
    assert created is False
    assert reason == "ocr_source_review_required"
    assert _document_observations(db, doc_id) == []


# =============================================================================
# Scenario 7 (G11-D6): Mandatory `reason` on OCR `decision='corrected'`
# =============================================================================


@pytest.mark.parametrize(
    ("field_name", "payload"),
    [
        ("value", {"corrected_value": "74", "corrected_unit": "mg/dL"}),
        ("unit", {"corrected_value": "g/dL"}),
        ("report_date", {"corrected_value": "2026-11-03"}),
        ("test_name", {"corrected_value": "Plasma glucose"}),
        ("reference_text", {"corrected_value": "70 - 105 mg/dL"}),
    ],
)
def test_stage3_s7_g11_d6_ocr_corrections_require_non_empty_reason(
    api,
    patient_headers,
    doctor_headers,
    fixtures,
    db: Session,
    monkeypatch,
    field_name: str,
    payload: dict,
):
    """G11-D6: Every OCR correction requires a non-empty `reason`, across all 5 fields."""
    _clear_same_day_glucose(db)
    ocr_text = WRONG_UNIT_OCR if field_name == "unit" else NO_CONFUSABLE_DIGITS_OCR
    _inject_ocr(monkeypatch, ocr_text, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename=f"corr-reason-{field_name}.png")
    _fetch_file(api, doctor_headers, doc_id)

    target = _facts_by_field(_extraction(api, doctor_headers, doc_id))[field_name][0]
    missing_reason = _verify(
        api,
        doctor_headers,
        doc_id,
        target["fact_id"],
        decision="corrected",
        source_image_compared=True,
        **payload,
    )
    assert missing_reason.status_code == 400, missing_reason.text
    assert missing_reason.json()["code"] == "E_VALIDATION"

    with_reason = _verify(
        api,
        doctor_headers,
        doc_id,
        target["fact_id"],
        decision="corrected",
        source_image_compared=True,
        reason=f"corrected {field_name} after reviewing scan",
        **payload,
    )
    assert with_reason.status_code == 200, with_reason.text


# =============================================================================
# Scenario 8 (G11-D6): Mandatory `reason` on confusable digits (`0`/`1`/`5`/`8`)
# =============================================================================


def test_stage3_s8_g11_d6_confusable_digit_ocr_confirmation_requires_reason(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """G11-D6: OCR `verified` with `0/1/5/8` requires `reason`; non-confusable passes without."""
    _clear_same_day_glucose(db)
    # 1) Value 105 (contains 1, 0, 5) without reason -> 400; with reason -> 200.
    _inject_ocr(monkeypatch, SUBSTITUTED_105_OCR, confidence=0.95)
    doc_conf = _upload_scan(api, patient_headers, fixtures, filename="conf-105.png")
    _fetch_file(api, doctor_headers, doc_conf)
    by_conf = _facts_by_field(_extraction(api, doctor_headers, doc_conf))

    for field_name, extra in (
        ("value", {"confirmed_value": "105", "confirmed_unit": "mg/dL"}),
        ("report_date", {"confirmed_value": "2026-10-20"}),
        ("reference_text", {"confirmed_value": "70 - 110 mg/dL"}),
    ):
        fid = by_conf[field_name][0]["fact_id"]
        no_reason = _verify(
            api,
            doctor_headers,
            doc_conf,
            fid,
            source_image_compared=True,
            **extra,
        )
        assert no_reason.status_code == 400, (field_name, no_reason.text)
        assert no_reason.json()["code"] == "E_VALIDATION"

        ok = _verify(
            api,
            doctor_headers,
            doc_conf,
            fid,
            source_image_compared=True,
            reason=f"confirmed confusable digits in {field_name}",
            **extra,
        )
        assert ok.status_code == 200, ok.text

    # 2) Non-confusable OCR facts (`74`, `Glucose`, `mg/dL` — no 0/1/5/8) succeed without `reason`.
    _inject_ocr(monkeypatch, NO_CONFUSABLE_DIGITS_OCR, confidence=0.95)
    doc_clean = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="non-conf-74.png",
        source_name="report_a_clean.txt",
    )
    _fetch_file(api, doctor_headers, doc_clean)
    by_clean = _facts_by_field(_extraction(api, doctor_headers, doc_clean))

    assert (
        _verify(
            api,
            doctor_headers,
            doc_clean,
            by_clean["value"][0]["fact_id"],
            source_image_compared=True,
            confirmed_value="74",
            confirmed_unit="mg/dL",
        ).status_code
        == 200
    )
    assert (
        _verify(
            api,
            doctor_headers,
            doc_clean,
            by_clean["unit"][0]["fact_id"],
            source_image_compared=True,
            confirmed_unit="mg/dL",
        ).status_code
        == 200
    )
    assert (
        _verify(
            api,
            doctor_headers,
            doc_clean,
            by_clean["test_name"][0]["fact_id"],
            source_image_compared=True,
            confirmed_value="Glucose",
        ).status_code
        == 200
    )


# =============================================================================
# Scenario 9: End-to-end Stage 3 OCR promotion, R21 rejection & pypdf compat
# =============================================================================


def test_stage3_s9_full_stage3_ocr_promotion_r21_rejection_and_pypdf_compat(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session, monkeypatch
):
    """End-to-end Stage 3 verification + R21 rejection without friction + pypdf compat."""
    _clear_same_day_glucose(db)

    # Part A: pypdf text-layer documents still require zero source-confirmation fields or reason.
    pdf_resp = api.post(
        UPLOAD,
        headers=patient_headers,
        files={"file": ("clean.pdf", glucose_pdf, "application/pdf")},
    )
    assert pdf_resp.status_code == 202, pdf_resp.text
    pdf_doc_id = pdf_resp.json()["document_id"]
    pdf_ext = _extraction(api, doctor_headers, pdf_doc_id)
    for fact in pdf_ext["facts"]:
        assert fact["requires_source_confirmation"] is False
        assert _verify(api, doctor_headers, pdf_doc_id, fact["fact_id"]).status_code == 200
    assert _extraction(api, doctor_headers, pdf_doc_id)["document_status"] == "verified"
    pdf_obs = _document_observations(db, pdf_doc_id)
    assert len(pdf_obs) == 1
    db.delete(pdf_obs[0])
    db.commit()

    # Part B: R21 rejection works on any OCR fact without GET /file, flag, or confirmation.
    _inject_ocr(monkeypatch, SUBSTITUTED_105_OCR, confidence=0.95)
    rej_doc_id = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="r21-reject.png",
        source_name="report_a_clean.txt",
    )
    rej_date = _facts_by_field(_extraction(api, doctor_headers, rej_doc_id))["report_date"][0]
    rej_resp = _verify(
        api,
        doctor_headers,
        rej_doc_id,
        rej_date["fact_id"],
        decision="rejected",
    )
    assert rej_resp.status_code == 200, rej_resp.text
    assert rej_resp.json()["document_status"] == "failed"
    assert _document_observations(db, rej_doc_id) == []

    # Part C: Full Stage 3 OCR promotion across all 5 declared fields.
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    ocr_doc_id = _upload_scan(api, patient_headers, fixtures, filename="full-stage3.png")
    _fetch_file(api, doctor_headers, ocr_doc_id)
    ocr_ext = _extraction(api, doctor_headers, ocr_doc_id)
    assert len(ocr_ext["facts"]) == 5
    for fact in ocr_ext["facts"]:
        assert fact["requires_source_confirmation"] is True
        body: dict[str, object] = {"source_image_compared": True}
        if fact["field_name"] == "value":
            body.update(
                confirmed_value="104",
                confirmed_unit="mg/dL",
                reason="confirmed 104 mg/dL on scan",
            )
        elif fact["field_name"] == "unit":
            body.update(confirmed_unit="mg/dL")
        elif fact["field_name"] in {"report_date", "reference_text"}:
            body.update(
                confirmed_value=fact["normalized_value"],
                reason=f"confirmed {fact['field_name']} on scan",
            )
        else:
            body.update(confirmed_value=fact["normalized_value"])
        resp = _verify(api, doctor_headers, ocr_doc_id, fact["fact_id"], **body)
        assert resp.status_code == 200, (fact["field_name"], resp.text)

    assert _extraction(api, doctor_headers, ocr_doc_id)["document_status"] == "verified"
    ocr_obs = _document_observations(db, ocr_doc_id)
    assert len(ocr_obs) == 1
    assert ocr_obs[0].value == pytest.approx(104.0)
    assert ocr_obs[0].unit == "mg/dL"
