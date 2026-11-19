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
from pathlib import Path

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


# =============================================================================
# P3-G11 Phase 2A Proof: Route-Local Deferred ERROR Audit & FastAPI Lifecycle
# =============================================================================


def _read_source_path(settings, stored_path: str):
    from app.services.documents.storage import resolve_for_read

    return resolve_for_read(stored_path, upload_dir=settings.upload_dir)


def test_p3_g11_proof_teardown_order_file_backed_sqlite_no_lock_or_collateral_commit(
    p3_settings, p3_engine, fixtures, monkeypatch
):
    """OD-2b proof (file-backed SQLite + real get_db_session): teardown releases lock first."""
    from datetime import timedelta

    from sqlalchemy.orm import sessionmaker
    from support import FIXED_NOW, SEED_PASSWORD, TEST_HASH_ITERATIONS

    from app.api.v1.auth.dependencies import current_time
    from app.api.v1.documents import read as read_mod
    from app.core.config import get_settings
    from app.db.models import User, UserSession
    from app.db.session import get_db_session
    from app.main import create_app
    from app.services.accounts import issue_session
    from app.services.seed import seed_demo_data

    factory = sessionmaker(bind=p3_engine, autoflush=False, expire_on_commit=False)
    with factory() as seed_db:
        seed_demo_data(
            seed_db,
            password=SEED_PASSWORD,
            now=FIXED_NOW,
            iterations=TEST_HASH_ITERATIONS,
        )
        patient = seed_db.execute(
            select(User).where(User.username == "demo_patient_a")
        ).scalar_one()
        doctor = seed_db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        pat_tok, _ = issue_session(seed_db, user=patient, now=FIXED_NOW, ttl_minutes=120)
        doc_tok, doc_sess = issue_session(seed_db, user=doctor, now=FIXED_NOW, ttl_minutes=120)
        doc_sess_id = doc_sess.id
        doctor_id = doctor.id
        seed_db.commit()

    events: list[str] = []
    req_now = FIXED_NOW + timedelta(minutes=15)
    add_pending_orm = False

    def _instrumented_db_session():
        session = factory()
        events.append("db_enter")
        if add_pending_orm:
            session.add(
                AuditEvent(
                    id="collateral-orm-probe",
                    event_type="auth.login",
                    actor_type=ActorType.USER.value,
                    actor_id=doctor_id,
                    outcome=AuditOutcome.OK.value,
                    safe_detail="must-rollback",
                    idempotency_key="collateral-orm-probe-key",
                    created_at="2026-11-16T12:00:00Z",
                )
            )
            session.flush()
        try:
            yield session
            events.append("db_commit")
            session.commit()
        except Exception as exc:
            events.append(f"db_rollback:{type(exc).__name__}")
            session.rollback()
            raise
        finally:
            events.append("db_close")
            session.close()

    app = create_app(p3_settings)
    app.dependency_overrides[get_settings] = lambda: p3_settings
    app.dependency_overrides[current_time] = lambda: req_now
    app.dependency_overrides[get_db_session] = _instrumented_db_session

    # Spy on the deferred ERROR writer (must exist on read_mod and run AFTER db_close).
    orig_persist = getattr(read_mod, "_persist_deferred_file_read_error", None)
    assert orig_persist is not None, "route-local _persist_deferred_file_read_error missing"
    captured_intents: list[object] = []

    def _instrumented_persist(intent):
        events.append("deferred_error_audit_start")
        captured_intents.append(intent)
        result = orig_persist(intent)
        events.append("deferred_error_audit_done")
        return result

    monkeypatch.setattr(read_mod, "_persist_deferred_file_read_error", _instrumented_persist)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        png = fixtures.build_legible_scan_image("report_a_clean.txt")
        up = client.post(
            UPLOAD,
            headers={"Authorization": f"Bearer {pat_tok}"},
            files={"file": ("proof.png", png, "image/png")},
        )
        assert up.status_code == 202, up.text
        doc_id = up.json()["document_id"]

        with factory() as chk:
            doc_row = chk.get(Document, doc_id)
            assert doc_row is not None
            stored_path = doc_row.stored_path
            baseline_last_used = chk.get(UserSession, doc_sess_id).last_used_at

        # Tamper source bytes on disk without changing document.sha256.
        on_disk = _read_source_path(p3_settings, stored_path)
        on_disk.write_bytes(b"\x89PNG\r\n\x1a\ncorrupted-bytes")

        events.clear()
        add_pending_orm = True
        resp = client.get(
            f"/api/v1/documents/{doc_id}/file",
            headers={
                "Authorization": f"Bearer {doc_tok}",
                "X-Request-ID": "proof-req-tamper-1",
            },
        )
        assert resp.status_code == 404, resp.text
        assert resp.json()["code"] == "E_NOT_FOUND"
        assert resp.json()["detail"] == read_mod.NOT_FOUND_DETAIL
        assert resp.json()["request_id"] == "proof-req-tamper-1"
        assert str(p3_settings.upload_dir) not in resp.text
        assert stored_path not in resp.text

        # Second distinct request appends a second AuditOutcome.ERROR row (append-only).
        add_pending_orm = False
        resp2 = client.get(
            f"/api/v1/documents/{doc_id}/file",
            headers={
                "Authorization": f"Bearer {doc_tok}",
                "X-Request-ID": "proof-req-tamper-2",
            },
        )
        assert resp2.status_code == 404, resp2.text

    # Exact lifecycle proof: db rollback & close completed strictly BEFORE deferred audit write.
    assert events.index("db_rollback:ApiError") < events.index("deferred_error_audit_start"), events
    assert events.index("db_close") < events.index("deferred_error_audit_start"), events
    assert "db_commit" not in events, events
    assert events[-1] == "deferred_error_audit_done", events

    # Idempotent replay of exact same deferred intent does not duplicate or raise.
    orig_persist(captured_intents[0])

    # Verify durable ERROR audit, zero OK audit, and NO collateral commit of session.last_used_at / ORM row.
    with factory() as verify_db:
        assert verify_db.get(AuditEvent, "collateral-orm-probe") is None, (
            "unrelated pending ORM state on request session must roll back, not commit"
        )
        sess_after = verify_db.get(UserSession, doc_sess_id)
        assert sess_after is not None
        assert sess_after.last_used_at == baseline_last_used, (
            "resolve_session last_used_at must NOT be collaterally committed on 404"
        )
        file_audits = list(
            verify_db.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.event_type == "document.file_read",
                    AuditEvent.subject_id == doc_id,
                )
                .order_by(AuditEvent.created_at, text("rowid"))
            ).scalars()
        )
        assert len(file_audits) == 2
        err_row = file_audits[0]
        assert all(row.outcome == AuditOutcome.ERROR.value for row in file_audits)
        assert err_row.actor_id == doctor_id
        assert err_row.subject_type == "document"
        assert err_row.subject_id == doc_id
        assert "reason=integrity_mismatch" in (err_row.safe_detail or "")
        assert stored_path not in (err_row.safe_detail or "")
        assert "corrupted" not in (err_row.safe_detail or "")

        from app.services.audit import derive_audit_key

        expected_key = derive_audit_key(
            event_type="document.file_read",
            actor_type=ActorType.USER,
            actor_id=doctor_id,
            outcome=AuditOutcome.ERROR,
            subject_type="document",
            subject_id=doc_id,
            request_id="proof-req-tamper-1",
        )
        assert err_row.idempotency_key == expected_key


def test_p3_g11_proof_static_pool_in_memory_sqlite_supported(p3_engine, tmp_path: Path, fixtures):
    """OD-2b proof (StaticPool sqlite:///:memory:): deferred ERROR audit commits without collateral commit."""
    from datetime import timedelta

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from support import FIXED_NOW, SEED_PASSWORD, TEST_HASH_ITERATIONS

    from app.api.v1.auth.dependencies import current_time
    from app.core.config import Settings, get_settings
    from app.db.models import User, UserSession
    from app.db.session import get_db_session
    from app.main import create_app
    from app.services.accounts import issue_session
    from app.services.seed import seed_demo_data

    mem_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(mem_engine, "connect")
    def _fk_on(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()

    try:
        # Clone exact migrated schema (tables, indexes, triggers) from p3_engine into StaticPool :memory:.
        src_raw = p3_engine.raw_connection()
        dst_raw = mem_engine.raw_connection()
        try:
            src_raw.driver_connection.backup(dst_raw.driver_connection)
        finally:
            dst_raw.close()
            src_raw.close()

        factory = sessionmaker(bind=mem_engine, autoflush=False, expire_on_commit=False)
        with factory() as seed_db:
            seed_demo_data(
                seed_db,
                password=SEED_PASSWORD,
                now=FIXED_NOW,
                iterations=TEST_HASH_ITERATIONS,
            )
            patient = seed_db.execute(
                select(User).where(User.username == "demo_patient_a")
            ).scalar_one()
            doctor = seed_db.execute(
                select(User).where(User.username == "demo_doctor")
            ).scalar_one()
            pat_tok, _ = issue_session(seed_db, user=patient, now=FIXED_NOW, ttl_minutes=120)
            doc_tok, doc_sess = issue_session(seed_db, user=doctor, now=FIXED_NOW, ttl_minutes=120)
            doc_sess_id = doc_sess.id
            seed_db.commit()

        settings = Settings(
            database_url="sqlite:///:memory:",
            upload_dir=str(tmp_path / "mem_uploads"),
            tesseract_cmd="",
            _env_file=None,
        )
        req_now = FIXED_NOW + timedelta(minutes=20)

        def _mem_db_session():
            s = factory()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[current_time] = lambda: req_now
        app.dependency_overrides[get_db_session] = _mem_db_session

        with TestClient(app) as client:
            png = fixtures.build_legible_scan_image("report_a_clean.txt")
            up = client.post(
                UPLOAD,
                headers={"Authorization": f"Bearer {pat_tok}"},
                files={"file": ("mem.png", png, "image/png")},
            )
            assert up.status_code == 202, up.text
            doc_id = up.json()["document_id"]

            with factory() as chk:
                doc_row = chk.get(Document, doc_id)
                assert doc_row is not None
                stored_path = doc_row.stored_path
                baseline_last_used = chk.get(UserSession, doc_sess_id).last_used_at

            # Delete file on disk to trigger missing-file path -> AuditOutcome.ERROR
            _read_source_path(settings, stored_path).unlink()

            resp = client.get(
                f"/api/v1/documents/{doc_id}/file",
                headers={
                    "Authorization": f"Bearer {doc_tok}",
                    "X-Request-ID": "mem-proof-missing-1",
                },
            )
            assert resp.status_code == 404, resp.text
            assert resp.json()["code"] == "E_NOT_FOUND"

        with factory() as chk2:
            sess_after = chk2.get(UserSession, doc_sess_id)
            assert sess_after is not None
            assert sess_after.last_used_at == baseline_last_used
            audits = list(
                chk2.execute(
                    select(AuditEvent).where(
                        AuditEvent.event_type == "document.file_read",
                        AuditEvent.subject_id == doc_id,
                    )
                ).scalars()
            )
            assert len(audits) == 1
            assert audits[0].outcome == AuditOutcome.ERROR.value
            assert "reason=source_unavailable" in (audits[0].safe_detail or "")
    finally:
        mem_engine.dispose()


def test_p3_g11_proof_scoping_and_deferred_audit_failure_behavior(
    p3_settings,
    p3_engine,
    api,
    patient_headers,
    other_patient_headers,
    doctor_headers,
    unassigned_doctor_headers,
    fixtures,
    db: Session,
    monkeypatch,
):
    """OD-2b proof: 401/403/absent-404 emit no ERROR audit; deferred DB error fails closed (500)."""
    from fastapi.testclient import TestClient

    from app.api.v1.documents import read as read_mod
    from app.core.config import get_settings
    from app.db.session import get_db_session
    from app.main import create_app

    png = fixtures.build_legible_scan_image("report_a_clean.txt")
    up = api.post(
        UPLOAD,
        headers=patient_headers,
        files={"file": ("scope.png", png, "image/png")},
    )
    assert up.status_code == 202, up.text
    doc_id = up.json()["document_id"]
    doc_row = db.get(Document, doc_id)
    assert doc_row is not None
    # Corrupt the file on disk!
    _read_source_path(p3_settings, doc_row.stored_path).write_bytes(b"bad")

    # 1. Unauthenticated (401), nonexistent doc (404), out-of-scope callers (403) MUST NOT emit ERROR audit.
    assert api.get(f"/api/v1/documents/{doc_id}/file").status_code == 401
    assert (
        api.get("/api/v1/documents/nonexistent-id/file", headers=doctor_headers).status_code == 404
    )
    assert (
        api.get(f"/api/v1/documents/{doc_id}/file", headers=other_patient_headers).status_code
        == 403
    )
    assert (
        api.get(f"/api/v1/documents/{doc_id}/file", headers=unassigned_doctor_headers).status_code
        == 403
    )

    err_rows = list(
        db.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "document.file_read",
                AuditEvent.outcome == AuditOutcome.ERROR.value,
            )
        ).scalars()
    )
    assert err_rows == []

    # 2. If deferred ERROR persistence itself raises, app returns sanitized 500 E_INTERNAL (no leak, no OK).
    from support import FIXED_NOW

    from app.api.v1.auth.dependencies import current_time

    def _boom(_intent):
        raise RuntimeError("simulated audit disk full /secret/path")

    monkeypatch.setattr(read_mod, "_persist_deferred_file_read_error", _boom)

    def _override_db():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    fail_app = create_app(p3_settings)
    fail_app.dependency_overrides[get_settings] = lambda: p3_settings
    fail_app.dependency_overrides[current_time] = lambda: FIXED_NOW
    fail_app.dependency_overrides[get_db_session] = _override_db

    with TestClient(fail_app, raise_server_exceptions=False) as fail_client:
        resp = fail_client.get(f"/api/v1/documents/{doc_id}/file", headers=doctor_headers)
        assert resp.status_code == 500
        body = resp.json()
        assert body["code"] == "E_INTERNAL"
        assert "/secret/path" not in resp.text
        assert "simulated" not in resp.text

    ok_rows = list(
        db.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "document.file_read",
                AuditEvent.subject_id == doc_id,
                AuditEvent.outcome == AuditOutcome.OK.value,
            )
        ).scalars()
    )
    assert ok_rows == []


def test_p3_g11_proof_direct_python_call_distinction(
    p3_settings, api, patient_headers, fixtures, db: Session
):
    """OD-2b proof: direct Python read_file() skips FastAPI cleanup, preserves db state, raises 404."""
    from datetime import UTC, datetime

    from app.api.v1.documents.read import read_file
    from app.core.enums import Role
    from app.core.errors import ApiError
    from app.core.policies import Principal
    from app.db.models import User

    png = fixtures.build_legible_scan_image("report_a_clean.txt")
    up = api.post(
        UPLOAD,
        headers=patient_headers,
        files={"file": ("direct.png", png, "image/png")},
    )
    assert up.status_code == 202, up.text
    doc_id = up.json()["document_id"]
    doc_row = db.get(Document, doc_id)
    assert doc_row is not None
    _read_source_path(p3_settings, doc_row.stored_path).write_bytes(b"tampered-direct")

    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    principal = Principal(
        user_id=doctor.id,
        username=doctor.username,
        display_name=doctor.display_name,
        role=Role.DOCTOR,
        patient_id=None,
        session_id="direct-sess",
        timezone=doctor.timezone,
    )
    # Add unrelated pending ORM write on `db` before direct Python call.
    pending_marker = AuditEvent(
        id="pending-direct-marker",
        event_type="auth.login",
        actor_type=ActorType.USER.value,
        actor_id=doctor.id,
        outcome=AuditOutcome.OK.value,
        safe_detail="pending-uncommitted",
        idempotency_key="pending-direct-marker-key",
        created_at="2026-11-16T12:00:00Z",
    )
    db.add(pending_marker)
    db.flush()

    with pytest.raises(ApiError) as exc_info:
        read_file(
            document_id=doc_id,
            principal=principal,
            db=db,
            settings=p3_settings,
            now=datetime(2026, 11, 16, 12, 0, 0, tzinfo=UTC),
            request_id="direct-call-req-1",
        )
    assert exc_info.value.status_code == 404

    # Pending ORM state on `db` was neither committed nor rolled back by direct call,
    # and zero OK audits were emitted (nor did SQLite deadlock on a concurrent write).
    assert pending_marker in db
    db.rollback()
    assert db.get(AuditEvent, "pending-direct-marker") is None
    assert (
        db.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "document.file_read",
                AuditEvent.subject_id == doc_id,
            )
        )
        .scalars()
        .all()
        == []
    )


# =============================================================================
# P3-G11 Phase 2B: A1-Anchored Integrity, Scoping, Controls & False Attestation
# =============================================================================


def _verify_all_ocr_facts(api, doctor_headers, doc_id: str, *, reason_prefix: str = "confirmed"):
    """Verify every pending OCR fact on ``doc_id`` with source confirmation."""
    ext = _extraction(api, doctor_headers, doc_id)
    responses = []
    for fact in ext["facts"]:
        body: dict[str, object] = {"source_image_compared": True}
        if fact["field_name"] == "value":
            body.update(
                confirmed_value=fact["normalized_value"],
                confirmed_unit=fact["unit"],
                reason=f"{reason_prefix} value",
            )
        elif fact["field_name"] == "unit":
            body.update(
                confirmed_unit=fact["normalized_value"],
                reason=f"{reason_prefix} unit",
            )
        elif fact["field_name"] in {"report_date", "reference_text"}:
            body.update(
                confirmed_value=fact["normalized_value"],
                reason=f"{reason_prefix} {fact['field_name']}",
            )
        else:
            body.update(
                confirmed_value=fact["normalized_value"],
                reason=f"{reason_prefix} {fact['field_name']}",
            )
        responses.append(_verify(api, doctor_headers, doc_id, fact["fact_id"], **body))
    return responses


def test_p3_g11_a1_s1_tamper_failed_read_invalidates_prior_ok_and_recovers(
    p3_settings, api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """A1-Anchored S1: ERROR after OK invalidates anchor even after restore until new intact GET."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="a1-s1.png")
    doc_row = db.get(Document, doc_id)
    assert doc_row is not None
    on_disk = _read_source_path(p3_settings, doc_row.stored_path)
    original_bytes = on_disk.read_bytes()

    # Intact GET /file succeeds with ETag, nosniff, and document.mime_type.
    ok_resp = api.get(f"/api/v1/documents/{doc_id}/file", headers=doctor_headers)
    assert ok_resp.status_code == 200
    assert ok_resp.headers["content-type"].startswith("image/png")
    assert ok_resp.headers["etag"] == f'"{doc_row.sha256}"'
    assert ok_resp.headers["x-content-type-options"] == "nosniff"

    # Tamper bytes -> doctor GET /file returns neutral 404 and records AuditOutcome.ERROR.
    on_disk.write_bytes(b"tampered-s1-bytes")
    err_resp = api.get(f"/api/v1/documents/{doc_id}/file", headers=doctor_headers)
    assert err_resp.status_code == 404
    assert err_resp.json()["code"] == "E_NOT_FOUND"

    # Restore exact original bytes on disk, WITHOUT performing a new GET /file.
    on_disk.write_bytes(original_bytes)
    ext = _extraction(api, doctor_headers, doc_id)
    val_fact = _facts_by_field(ext)["value"][0]

    # S1: Stale OK anchor invalidated by intervening ERROR -> verified & corrected must FAIL 400.
    stale_verify = _verify(
        api,
        doctor_headers,
        doc_id,
        val_fact["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="stale after failed read",
    )
    assert stale_verify.status_code == 400, stale_verify.text
    assert stale_verify.json()["code"] == "E_VALIDATION"

    stale_correct = _verify(
        api,
        doctor_headers,
        doc_id,
        val_fact["fact_id"],
        decision="corrected",
        corrected_value="106",
        corrected_unit="mg/dL",
        source_image_compared=True,
        reason="stale correction after failed read",
    )
    assert stale_correct.status_code == 400, stale_correct.text
    assert stale_correct.json()["code"] == "E_VALIDATION"

    # Recovery: a NEW intact GET /file appends a fresher OK row strictly after ERROR -> verify succeeds.
    recovered_get = api.get(f"/api/v1/documents/{doc_id}/file", headers=doctor_headers)
    assert recovered_get.status_code == 200
    assert recovered_get.headers["etag"] == f'"{doc_row.sha256}"'

    responses = _verify_all_ocr_facts(api, doctor_headers, doc_id, reason_prefix="recovered")
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    assert _extraction(api, doctor_headers, doc_id)["document_status"] == "verified"
    assert len(_document_observations(db, doc_id)) == 1


def test_p3_g11_a1_s1_patient_error_invalidates_doc_while_other_doc_isolated(
    p3_settings, api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """A1-Anchored scoping: patient-triggered ERROR invalidates doc_a only, not doc_b."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_a = _upload_scan(api, patient_headers, fixtures, filename="scope-a.png")
    doc_b = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="scope-b.png",
        source_name="report_a_clean.txt",
    )
    row_a = db.get(Document, doc_a)
    assert row_a is not None
    path_a = _read_source_path(p3_settings, row_a.stored_path)
    orig_a = path_a.read_bytes()

    # Doctor reads both doc_a and doc_b while intact.
    assert api.get(f"/api/v1/documents/{doc_a}/file", headers=doctor_headers).status_code == 200
    assert api.get(f"/api/v1/documents/{doc_b}/file", headers=doctor_headers).status_code == 200

    # Tamper doc_a; permitted patient read triggers document-level AuditOutcome.ERROR on doc_a.
    path_a.write_bytes(b"corrupt-a")
    pat_err = api.get(f"/api/v1/documents/{doc_a}/file", headers=patient_headers)
    assert pat_err.status_code == 404
    path_a.write_bytes(orig_a)

    # doc_a's prior doctor OK anchor is invalidated by the document-level ERROR.
    val_a = _facts_by_field(_extraction(api, doctor_headers, doc_a))["value"][0]
    refused_a = _verify(
        api,
        doctor_headers,
        doc_a,
        val_a["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="doc_a invalidated by patient error audit",
    )
    assert refused_a.status_code == 400, refused_a.text

    # doc_b remains completely unaffected and verifies cleanly!
    resp_b = _verify_all_ocr_facts(api, doctor_headers, doc_b, reason_prefix="doc_b unaffected")
    assert all(r.status_code == 200 for r in resp_b), [r.text for r in resp_b]
    assert len(_document_observations(db, doc_b)) == 1


def test_p3_g11_a1_s2_silent_tamper_blocks_verify_and_promotion_preserves_r21(
    p3_settings, api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """A1-Anchored S2: silent on-disk tamper (no GET /file ERROR) blocks verify, correct & promotion, preserves R21."""
    _clear_same_day_glucose(db)
    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    doc_id = _upload_scan(api, patient_headers, fixtures, filename="a1-s2.png")
    doc_row = db.get(Document, doc_id)
    assert doc_row is not None
    on_disk = _read_source_path(p3_settings, doc_row.stored_path)

    # Doctor completes valid intact GET /file.
    assert api.get(f"/api/v1/documents/{doc_id}/file", headers=doctor_headers).status_code == 200

    # Doctor verifies 4 non-value facts while file is intact.
    by_field = _facts_by_field(_extraction(api, doctor_headers, doc_id))
    for fname in ("report_date", "test_name", "reference_text"):
        f = by_field[fname][0]
        r = _verify(
            api,
            doctor_headers,
            doc_id,
            f["fact_id"],
            source_image_compared=True,
            confirmed_value=f["normalized_value"],
            reason=f"ok {fname}",
        )
        assert r.status_code == 200, r.text
    unit_f = by_field["unit"][0]
    assert (
        _verify(
            api,
            doctor_headers,
            doc_id,
            unit_f["fact_id"],
            source_image_compared=True,
            confirmed_unit=unit_f["normalized_value"],
            reason="ok unit",
        ).status_code
        == 200
    )

    # Now file is SILENTLY tampered on disk (no GET /file called).
    on_disk.write_bytes(b"silently-tampered-bytes")
    val_f = by_field["value"][0]

    # S2: Both verified and corrected MUST fail closed (400 E_VALIDATION) with 0 Observations.
    s2_ver = _verify(
        api,
        doctor_headers,
        doc_id,
        val_f["fact_id"],
        source_image_compared=True,
        confirmed_value="104",
        confirmed_unit="mg/dL",
        reason="s2 tampered verify",
    )
    assert s2_ver.status_code == 400, s2_ver.text
    assert s2_ver.json()["code"] == "E_VALIDATION"

    s2_corr = _verify(
        api,
        doctor_headers,
        doc_id,
        val_f["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
        source_image_compared=True,
        reason="s2 tampered correct",
    )
    assert s2_corr.status_code == 400, s2_corr.text
    assert _document_observations(db, doc_id) == []

    # R21 preserved: doctor CAN still reject the fact cleanly even while source file is tampered/missing!
    on_disk.unlink()
    r21_rej = _verify(
        api,
        doctor_headers,
        doc_id,
        val_f["fact_id"],
        decision="rejected",
        reason="source unusable -> reject",
    )
    assert r21_rej.status_code == 200, r21_rej.text
    assert r21_rej.json()["document_status"] == "failed"
    assert _document_observations(db, doc_id) == []

    # Defense-in-depth at _create_observation_from_mapping on a second doc whose facts were all verified before silent tamper.
    doc2 = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="a1-s2-direct.png",
        source_name="report_ocr_o_confusion.txt",
    )
    row2 = db.get(Document, doc2)
    assert row2 is not None
    assert api.get(f"/api/v1/documents/{doc2}/file", headers=doctor_headers).status_code == 200
    facts2 = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == doc2)).scalars()
    )
    doctor_id = _doctor_user_id(db)
    for row in facts2:
        row.verification_status = "verified"
        db.add(
            FactVerification(
                fact_id=row.id,
                decision="verified",
                previous_value=row.normalized_value,
                reason="pre-tamper verified",
                verified_by_user_id=doctor_id,
                decided_at="2026-11-14T12:00:00Z",
                source_image_compared=1,
                confirmed_value=row.normalized_value if row.field_name != "unit" else None,
                confirmed_unit="mg/dL" if row.field_name in {"value", "unit"} else None,
            )
        )
    row2.extraction_status = "verified"
    db.flush()

    _read_source_path(p3_settings, row2.stored_path).write_bytes(b"post-verify-silent-tamper")
    val2 = next(f for f in facts2 if f.field_name == FactField.VALUE.value)
    created, reason = _create_observation_from_mapping(
        db,
        document=row2,
        source_fact=val2,
        doctor_user_id=doctor_id,
        decided_at="2026-11-14T12:00:00Z",
        upload_dir=p3_settings.upload_dir,
    )
    assert created is False
    assert reason == "ocr_source_review_required"
    assert _document_observations(db, doc2) == []


def test_p3_g11_a1_settings_upload_dir_propagated_from_verify_route(
    p3_settings, p3_engine, tmp_path: Path, fixtures, monkeypatch
):
    """V21: verify.py passes overridden settings.upload_dir instead of falling back to global settings."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from support import FIXED_NOW, SEED_PASSWORD, TEST_HASH_ITERATIONS

    from app.api.v1.auth.dependencies import current_time
    from app.core.config import Settings, get_settings, reset_settings_cache
    from app.db.models import User
    from app.db.session import get_db_session
    from app.main import create_app
    from app.services.accounts import issue_session
    from app.services.seed import seed_demo_data

    custom_upload_dir = tmp_path / "custom_route_uploads"
    wrong_global_dir = tmp_path / "wrong_empty_global_uploads"
    wrong_global_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("UPLOAD_DIR", str(wrong_global_dir))
    reset_settings_cache()
    custom_settings = Settings(
        database_url=p3_settings.database_url,
        upload_dir=str(custom_upload_dir),
        tesseract_cmd="",
        _env_file=None,
    )
    factory = sessionmaker(bind=p3_engine, autoflush=False, expire_on_commit=False)
    with factory() as seed_db:
        seed_demo_data(
            seed_db,
            password=SEED_PASSWORD,
            now=FIXED_NOW,
            iterations=TEST_HASH_ITERATIONS,
        )
        pat = seed_db.execute(select(User).where(User.username == "demo_patient_a")).scalar_one()
        doc = seed_db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        pat_tok, _ = issue_session(seed_db, user=pat, now=FIXED_NOW, ttl_minutes=60)
        doc_tok, _ = issue_session(seed_db, user=doc, now=FIXED_NOW, ttl_minutes=60)
        seed_db.commit()

    def _db_override():
        s = factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    _inject_ocr(monkeypatch, CLEAN_GLUCOSE_OCR, confidence=0.95)
    app = create_app(custom_settings)
    app.dependency_overrides[get_settings] = lambda: custom_settings
    app.dependency_overrides[current_time] = lambda: FIXED_NOW
    app.dependency_overrides[get_db_session] = _db_override

    pat_hdr = {"Authorization": f"Bearer {pat_tok}"}
    doc_hdr = {"Authorization": f"Bearer {doc_tok}"}
    try:
        with TestClient(app) as client:
            doc_id = _upload_scan(client, pat_hdr, fixtures, filename="custom-dir.png")
            assert (custom_upload_dir).exists()
            assert list(wrong_global_dir.iterdir()) == []
            assert (
                client.get(f"/api/v1/documents/{doc_id}/file", headers=doc_hdr).status_code == 200
            )

            responses = _verify_all_ocr_facts(
                client, doc_hdr, doc_id, reason_prefix="custom upload_dir"
            )
            assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
            assert _extraction(client, doc_hdr, doc_id)["document_status"] == "verified"

            # Second doc inside custom_upload_dir: tamper it and prove verify fails 400.
            doc_tamper = _upload_scan(
                client,
                pat_hdr,
                fixtures,
                filename="custom-tamper.png",
                source_name="report_a_clean.txt",
            )
            assert (
                client.get(f"/api/v1/documents/{doc_tamper}/file", headers=doc_hdr).status_code
                == 200
            )
            with factory() as chk_tamper:
                t_row = chk_tamper.get(Document, doc_tamper)
                assert t_row is not None
                stored = custom_upload_dir / t_row.stored_path
                assert stored.is_file()
                stored.write_bytes(b"tampered-inside-custom-dir")
            val_t = _facts_by_field(_extraction(client, doc_hdr, doc_tamper))["value"][0]
            refused_t = _verify(
                client,
                doc_hdr,
                doc_tamper,
                val_t["fact_id"],
                source_image_compared=True,
                confirmed_value="104",
                confirmed_unit="mg/dL",
                reason="tampered in custom_upload_dir",
            )
            assert refused_t.status_code == 400

        with factory() as chk_db:
            assert len(_document_observations(chk_db, doc_id)) == 1
            assert _document_observations(chk_db, doc_tamper) == []
    finally:
        reset_settings_cache()


def test_p3_g11_controls_m2_unmapped_hemoglobin_and_m6_false_attestation_sequence(
    api, patient_headers, doctor_headers, fixtures, db: Session, monkeypatch
):
    """M2 (13.4 g/dL clean UNMAPPED), M1 (104 mg/dL mapped), and M6 (1O5->105 sibling sequence)."""
    _clear_same_day_glucose(db)

    # M2: Clean Hemoglobin 13.4 g/dL verifies cleanly -> verified document, UNMAPPED, 0 Observations.
    hgb_ocr = (
        "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
        "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
        "Test: Hemoglobin          Value: 13.4 g/dL\n"
        "Reference range: 12.0 - 15.5 g/dL\n"
    )
    _inject_ocr(monkeypatch, hgb_ocr, confidence=0.95)
    doc_hgb = _upload_scan(
        api, patient_headers, fixtures, filename="hgb.png", source_name="report_a_clean.txt"
    )
    _fetch_file(api, doctor_headers, doc_hgb)
    hgb_resps = _verify_all_ocr_facts(api, doctor_headers, doc_hgb, reason_prefix="hgb clean")
    assert all(r.status_code == 200 for r in hgb_resps), [r.text for r in hgb_resps]
    assert _extraction(api, doctor_headers, doc_hgb)["document_status"] == "verified"
    assert _document_observations(db, doc_hgb) == []

    # M6: Substituted `1O5` -> `105 mg/dL` OCR: value-only verification must leave Observation == 0;
    # Observation creates ONLY after ALL required OCR siblings are attested after GET /file.
    _inject_ocr(monkeypatch, SUBSTITUTED_105_OCR, confidence=0.95)
    doc_105 = _upload_scan(
        api,
        patient_headers,
        fixtures,
        filename="false-105.png",
        source_name="report_ocr_o_confusion.txt",
    )
    by_105 = _facts_by_field(_extraction(api, doctor_headers, doc_105))
    assert len(by_105) == 5

    # Without GET /file -> refused
    val_105 = by_105["value"][0]
    assert _verify(api, doctor_headers, doc_105, val_105["fact_id"]).status_code == 400
    assert (
        _verify(
            api,
            doctor_headers,
            doc_105,
            val_105["fact_id"],
            source_image_compared=True,
            confirmed_value="105",
            confirmed_unit="mg/dL",
            reason="false attest before file",
        ).status_code
        == 400
    )
    assert _document_observations(db, doc_105) == []

    _fetch_file(api, doctor_headers, doc_105)

    # Step 1: Verify ONLY `value` (`105`) -> still needs_verification, Observation == 0!
    r_val = _verify(
        api,
        doctor_headers,
        doc_105,
        val_105["fact_id"],
        source_image_compared=True,
        confirmed_value="105",
        confirmed_unit="mg/dL",
        reason="doctor falsely attested 105",
    )
    assert r_val.status_code == 200, r_val.text
    assert r_val.json()["document_status"] == "needs_verification"
    assert _document_observations(db, doc_105) == []

    # Intermediate siblings keep Observation == 0 until the FINAL sibling completes.
    for fname in ("report_date", "test_name", "reference_text"):
        f = by_105[fname][0]
        r_mid = _verify(
            api,
            doctor_headers,
            doc_105,
            f["fact_id"],
            source_image_compared=True,
            confirmed_value=f["normalized_value"],
            reason=f"attested {fname}",
        )
        assert r_mid.status_code == 200, r_mid.text
        assert r_mid.json()["document_status"] == "needs_verification"
        assert _document_observations(db, doc_105) == []

    # Final sibling `unit`: completes document -> single doctor_verified Observation (105.0 mg/dL).
    unit_105 = by_105["unit"][0]
    r_last = _verify(
        api,
        doctor_headers,
        doc_105,
        unit_105["fact_id"],
        source_image_compared=True,
        confirmed_unit=unit_105["normalized_value"],
        reason="attested mg/dL",
    )
    assert r_last.status_code == 200, r_last.text
    assert r_last.json()["document_status"] == "verified"
    obs_105 = _document_observations(db, doc_105)
    assert len(obs_105) == 1
    assert obs_105[0].value == pytest.approx(105.0)
    assert obs_105[0].unit == "mg/dL"
    assert obs_105[0].trust_level == "doctor_verified"
