"""P4-RB3 durable review persistence service acceptance matrix.

Covers RB3-01..28, RB3-33..53, RB3-59..66, RB3-70..74, RB3-79, RB3-82..88,
RB3-92..99, RB3-111..114, RB3-128 from
docs/phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md.

NOTE on RB3-75..77 (§7.2a future DR-006 span extension):
    RB3-75, RB3-76, and RB3-77 are intentionally NON-EXECUTABLE in this slice
    because D-RB3-08(ii) prohibits persisting DR-006 and G8 forbids writing
    ``document_span`` links. They are never marked or reported as passing.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import secrets
import threading
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path

import pytest
from sqlalchemy import Connection, delete, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, Role
from app.core.errors import ApiError, ErrorCode
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.models import (
    AuditEvent,
    Document,
    EvidenceLink,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    ReviewEvaluation,
    ReviewItem,
    User,
    UserSession,
    WorkflowRun,
)
from app.main import create_app
from app.schemas.p4_rb2_offline_rules import (
    OfflineObservation,
    OfflineRuleFlag,
    OfflineRuleInput,
    OfflineRulePolicy,
    OfflineRuleResult,
)
from app.schemas.p4_rb3_review_persistence import RB3DenialReason, ReviewPersistenceReceiptV1
from app.services import p4_rb3_review_persistence as rb3
from app.services.audit import SAFE_DETAIL_MAX, append_audit_event, safe_detail
from app.services.p4_rb2_offline_rules import evaluate_p4_rb2_offline_fixture
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CLOCK_ISO = "2026-11-14T12:00:00Z"
AT_ISO = "2026-06-14T08:00:00Z"


@pytest.fixture()
def scoped(engine):
    with Session(engine) as db:
        seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
        db.commit()
        patient = db.execute(
            select(Patient).where(Patient.external_ref == "DEMO-A-001")
        ).scalar_one()
        doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        sess = UserSession(
            id="f1111111-1111-4111-8111-111111111111",
            user_id=doctor.id,
            token_sha256=hashlib.sha256(b"rb3-synthetic-session").hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
        db.add(sess)
        db.commit()
        principal = Principal(
            user_id=doctor.id,
            username=doctor.username,
            display_name=doctor.display_name,
            role=Role(doctor.role),
            patient_id=doctor.patient_id,
            session_id=sess.id,
        )
        yield db, patient.id, principal


def _verified_doc(
    db: Session,
    patient_id: str,
    root: Path,
    label: str,
    *,
    test_name: str = "glucose",
    value: str = "105",
    unit: str = "mg/dL",
    report_date: str | None = "2026-06-14",
) -> tuple[Document, dict[str, ExtractedFact]]:
    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"RB3 synthetic-only source: {label}".encode()
    name = f"rb3-{label}.pdf"
    (root / name).write_bytes(raw)
    doc = Document(
        patient_id=patient_id,
        uploaded_by_user_id=patient.assigned_doctor_id,
        original_filename=name,
        stored_path=name,
        mime_type="application/pdf",
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        extraction_status="verified",
        failure_code=None,
        document_patient_ref=patient.external_ref,
        document_patient_refs=f'["{patient.external_ref}"]',
        uploaded_at=AT_ISO,
    )
    db.add(doc)
    db.flush()
    facts: dict[str, ExtractedFact] = {}
    items: list[tuple[str, str, str | None]] = [
        ("test_name", test_name, None),
        ("value", value, unit),
        ("unit", unit, None),
    ]
    if report_date is not None:
        items.insert(0, ("report_date", report_date, None))
    for field_name, val, u in items:
        ef = ExtractedFact(
            document_id=doc.id,
            patient_id=patient_id,
            field_name=field_name,
            raw_text=val,
            normalized_value=val,
            unit=u,
            page_index=0,
            char_start=0,
            char_end=len(val),
            verification_status="verified",
            created_at=AT_ISO,
        )
        db.add(ef)
        db.flush()
        db.add(
            FactVerification(
                fact_id=ef.id,
                decision="verified",
                verified_by_user_id=patient.assigned_doctor_id,
                decided_at=AT_ISO,
            )
        )
        facts[field_name] = ef
    db.commit()
    return doc, facts


def _obs(
    db: Session,
    patient_id: str,
    *,
    measure_type: str = "heart_rate",
    value: float | Decimal = 120,
    unit: str = "bpm",
    measured_at: str = "2026-11-14T10:00:00Z",
    created_at: str = "2026-11-14T10:00:00Z",
    source: str = "patient_checkin",
    validation: str = "ok",
    trust_level: str = "self_reported_validated",
    source_fact_id: str | None = None,
    verified_by_user_id: str | None = None,
    verified_at: str | None = None,
    note: str | None = None,
) -> Observation:
    row = Observation(
        patient_id=patient_id,
        measure_type=measure_type,
        value=float(value),
        unit=unit,
        measured_at=measured_at,
        source=source,
        validation=validation,
        trust_level=trust_level,
        source_fact_id=source_fact_id,
        verified_by_user_id=verified_by_user_id,
        verified_at=verified_at,
        created_at=created_at,
        note=note,
    )
    db.add(row)
    db.commit()
    return row


def _start_and_gate(
    engine,
    db: Session,
    patient_id: str,
    doctor: Principal,
    doc_ids: tuple[str, ...],
    selected_obs: tuple[str, ...],
    root: Path,
    *,
    req_id: str = "rb3-run",
    clock: datetime = CLOCK,
) -> str:
    rec = create_run_foundation(
        db,
        principal=doctor,
        patient_id=patient_id,
        document_ids=doc_ids,
        observation_ids=selected_obs,
        omissions=(),
        client_request_id=req_id,
        as_of_utc=clock,
    )
    db.commit()
    with Session(engine) as gdb:
        gate = evaluate_run_verification_gate(
            gdb,
            principal=doctor,
            run_id=rec.run_id,
            validation_clock=clock,
            upload_root=str(root),
        )
        assert gate.decision == "proceed"
    return rec.run_id


def _persist(
    engine,
    doctor: Principal,
    run_id: str,
    root: Path,
    *,
    clock: datetime = CLOCK,
) -> ReviewPersistenceReceiptV1:
    with Session(engine) as pdb:
        return rb3.persist_run_review_items(
            pdb,
            principal=doctor,
            run_id=run_id,
            validation_clock=clock,
            upload_root=str(root),
        )


def _counts(db: Session) -> tuple[int, int, int, int]:
    return (
        db.scalar(select(func.count()).select_from(ReviewItem)) or 0,
        db.scalar(select(func.count()).select_from(EvidenceLink)) or 0,
        db.scalar(select(func.count()).select_from(ReviewEvaluation)) or 0,
        db.scalar(select(func.count()).select_from(AuditEvent)) or 0,
    )


def test_rb3_01_23_44_happy_path_replay_and_honesty_receipt(scoped, engine, tmp_path: Path):
    """RB3-01/23/44: happy path commits items/links/audit/eval; replay does 0 writes."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "happy")
    obs = _obs(db, patient_id, value=120, measured_at="2026-11-14T10:00:00Z")
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-01"
    )

    before = _counts(db)
    first = _persist(engine, doctor, run_id, tmp_path)
    assert first.contract_version == "p4-rb3-receipt-1.0.0"
    assert first.evaluation_completed is True
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total >= 1
    assert first.evidence_links_persisted == first.evidence_links_total >= first.review_items_total
    assert first.lineage_label_policy == "a2_transport_label"
    assert first.dr006_policy == "prohibited_denied"
    assert first.offline_evaluator_invoked is True
    assert first.runtime_evaluable is False
    assert first.policy_status == "unapproved"
    assert first.demo_only is True
    assert first.not_for_clinical_use is True

    with pytest.raises(FrozenInstanceError):
        first.replayed = True  # type: ignore[misc]

    after_first = _counts(db)
    assert after_first == (
        before[0] + first.review_items_persisted,
        before[1] + first.evidence_links_persisted,
        before[2] + 1,
        before[3] + 1,
    )

    second = _persist(engine, doctor, run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.review_items_total == first.review_items_total
    assert second.evidence_links_persisted == 0
    assert second.evidence_links_total == first.evidence_links_total
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert second.input_fingerprint_sha256 == first.input_fingerprint_sha256
    assert second.output_identity_sha256 == first.output_identity_sha256
    assert _counts(db) == after_first


def test_rb3_02_to_06_gate_and_lock_failures_write_nothing(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-02..06: missing/stale/halt/unavailable F1 gate -> 409; BEGIN IMMEDIATE OperationalError -> 503."""
    db, patient_id, doctor = scoped
    doc, facts = _verified_doc(db, patient_id, tmp_path, "gate-fail")
    rec = create_run_foundation(
        db,
        principal=doctor,
        patient_id=patient_id,
        document_ids=(doc.id,),
        observation_ids=(),
        omissions=(),
        client_request_id="rb3-no-gate",
        as_of_utc=CLOCK,
    )
    db.commit()
    before = _counts(db)

    # RB3-02: missing gate
    with pytest.raises(ApiError) as missing_exc:
        _persist(engine, doctor, rec.run_id, tmp_path)
    assert missing_exc.value.status_code == 409
    assert _counts(db) == before

    # Gate PROCEED, then make stale (RB3-03) by adding a new unverified observation / modifying raw file
    with Session(engine) as gdb:
        assert (
            evaluate_run_verification_gate(
                gdb,
                principal=doctor,
                run_id=rec.run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            ).decision
            == "proceed"
        )

    # RB3-04: HALT gate
    facts["value"].verification_status = "pending"
    db.commit()
    with Session(engine) as gdb:
        halt_gate = evaluate_run_verification_gate(
            gdb,
            principal=doctor,
            run_id=rec.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        assert halt_gate.decision in {"halt", "unavailable"}
    before = _counts(db)
    with pytest.raises(ApiError) as halt_exc:
        _persist(engine, doctor, rec.run_id, tmp_path)
    assert halt_exc.value.status_code == 409
    assert _counts(db) == before

    # Restore verified & re-gate PROCEED for RB3-06 lock error test
    facts["value"].verification_status = "verified"
    db.commit()
    with Session(engine) as gdb:
        assert (
            evaluate_run_verification_gate(
                gdb,
                principal=doctor,
                run_id=rec.run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            ).decision
            == "proceed"
        )
    before = _counts(db)
    orig_exec = Connection.exec_driver_sql

    def _fail_begin_immediate(self, statement, *args, **kwargs):
        if isinstance(statement, str) and "BEGIN IMMEDIATE" in statement:
            raise OperationalError(statement, {}, Exception("database is locked"))
        return orig_exec(self, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "exec_driver_sql", _fail_begin_immediate)
    with pytest.raises(ApiError) as lock_exc:
        _persist(engine, doctor, rec.run_id, tmp_path)
    assert lock_exc.value.status_code == 503
    assert lock_exc.value.code == ErrorCode.VALIDATION
    assert _counts(db) == before


def test_rb3_07_to_18_authority_session_scope_run_and_byte_tampering(
    scoped, engine, tmp_path: Path
):
    """RB3-07..18: foreign scope, session invalid, reassigned/non-synthetic, version/bytes/clock."""
    db, patient_id, doctor = scoped
    doc, facts = _verified_doc(db, patient_id, tmp_path, "auth")
    obs = _obs(db, patient_id, value=120)
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-auth"
    )

    other_doc = User(
        id="d9999999-9999-4999-8999-999999999999",
        username="other_doctor",
        display_name="Other Doctor",
        role=Role.DOCTOR.value,
        password_hash="x",
        is_active=1,
        created_at="2026-11-01T00:00:00Z",
    )
    other_sess = UserSession(
        id="f9999999-9999-4999-8999-999999999999",
        user_id=other_doc.id,
        token_sha256=hashlib.sha256(b"other-sess").hexdigest(),
        created_at="2026-11-01T00:00:00Z",
        expires_at="2026-12-01T00:00:00Z",
    )
    db.add_all([other_doc, other_sess])
    db.commit()
    other_principal = Principal(
        user_id=other_doc.id,
        username=other_doc.username,
        display_name=other_doc.display_name,
        role=Role.DOCTOR,
        patient_id=None,
        session_id=other_sess.id,
    )

    # RB3-07: foreign doctor / reassigned patient
    with pytest.raises(ApiError) as f_exc:
        _persist(engine, other_principal, run_id, tmp_path)
    assert f_exc.value.status_code == 403

    # RB3-10: session owned by another user
    hijacked = Principal(
        user_id=doctor.user_id,
        username=doctor.username,
        display_name=doctor.display_name,
        role=doctor.role,
        patient_id=doctor.patient_id,
        session_id=other_sess.id,
    )
    with pytest.raises(ApiError) as s_exc:
        _persist(engine, hijacked, run_id, tmp_path)
    assert s_exc.value.status_code == 403

    # RB3-08/09: expired / revoked session
    sess = db.get(UserSession, doctor.session_id)
    assert sess is not None
    orig_exp = sess.expires_at
    sess.expires_at = "2026-11-10T00:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as exp_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert exp_exc.value.status_code == 403
    sess.expires_at = orig_exp
    sess.revoked_at = "2026-11-13T00:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as rev_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert rev_exc.value.status_code == 403
    sess.revoked_at = None
    db.commit()

    # RB3-11: reassigned patient
    patient = db.get(Patient, patient_id)
    assert patient is not None
    patient.assigned_doctor_id = other_doc.id
    db.commit()
    with pytest.raises(ApiError) as re_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert re_exc.value.status_code == 403
    patient.assigned_doctor_id = doctor.user_id
    db.commit()

    # RB3-18: clock mismatch
    with pytest.raises(ApiError) as clk_exc:
        _persist(engine, doctor, run_id, tmp_path, clock=CLOCK + timedelta(minutes=1))
    assert clk_exc.value.status_code == 409

    # RB3-13: run not queued
    run_row = db.get(WorkflowRun, run_id)
    assert run_row is not None
    run_row.status = "needs_verification"
    db.commit()
    with pytest.raises(ApiError) as st_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert st_exc.value.status_code == 409
    run_row.status = "queued"
    db.commit()

    # RB3-15: tampered source bytes
    doc_path = tmp_path / doc.stored_path
    orig_bytes = doc_path.read_bytes()
    doc_path.write_bytes(b"X" * len(orig_bytes))
    with pytest.raises(ApiError) as b_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert b_exc.value.status_code == 409
    doc_path.write_bytes(orig_bytes)

    # RB3-16: tampered FactVerification row
    fv = db.execute(
        select(FactVerification).where(FactVerification.fact_id == facts["value"].id)
    ).scalar_one()
    fv.source_image_compared = 1
    db.commit()
    with pytest.raises(ApiError) as fv_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert fv_exc.value.status_code == 409


def test_rb3_19_71_96_empty_selection_complete_t8a_path(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-19/71/96: empty selected_current takes T8a, never calls comparator, persists 0 items."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "zero-sel")
    # Even with eligible history present, zero selected_current yields 0 items & 0 links
    _obs(db, patient_id, value=250, measured_at="2026-06-01T10:00:00Z")
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (), tmp_path, req_id="rb3-zero"
    )

    calls: list[object] = []

    def _forbid_compare(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("compare_explicit_current_with_history must not be called in T8a")

    monkeypatch.setattr(rb3, "compare_explicit_current_with_history", _forbid_compare)
    rec = _persist(engine, doctor, run_id, tmp_path)
    assert calls == []
    assert rec.evaluation_completed is True
    assert rec.replayed is False
    assert rec.review_items_persisted == 0
    assert rec.review_items_total == 0
    assert rec.evidence_links_persisted == 0
    assert rec.evidence_links_total == 0

    ev = db.execute(
        select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_id)
    ).scalar_one()
    assert ev.item_count == 0
    assert ev.evidence_link_count == 0

    # RB3-19 / Case 7: repeated zero-item evaluation replays cleanly
    rec2 = _persist(engine, doctor, run_id, tmp_path)
    assert rec2.replayed is True
    assert rec2.review_items_total == 0


def test_rb3_20_input_caps_fail_closed(scoped, engine, tmp_path: Path):
    """RB3-20: >100 observations or >6 selected fails closed with 0 writes."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "caps")
    obs = _obs(db, patient_id, value=110, measured_at="2026-11-14T10:00:00Z")
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-cap"
    )

    # Add 100 more observations to exceed MAX_OFFLINE_ROWS = 100
    for idx in range(100):
        db.add(
            Observation(
                patient_id=patient_id,
                measure_type="heart_rate",
                value=70 + (idx % 20),
                unit="bpm",
                measured_at=f"2026-10-{(idx % 28) + 1:02d}T{(idx // 28):02d}:00:00Z",
                source="patient_checkin",
                validation="ok",
                trust_level="self_reported_validated",
                created_at="2026-10-01T00:00:00Z",
            )
        )
    db.commit()
    before = _counts(db)
    with pytest.raises(ApiError) as cap_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert cap_exc.value.code == ErrorCode.VALIDATION
    assert _counts(db) == before


def test_rb3_21_72_73_83_to_88_layered_exclusions_and_precedence(scoped, engine, tmp_path: Path):
    """RB3-21/72/73/83..88: L0, L1 precedence, L2 future skew, malformed_history, non-selected verified doc."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "excl")
    _other_doc, other_facts = _verified_doc(db, patient_id, tmp_path, "unselected")
    cur_obs = _obs(db, patient_id, value=120, measured_at="2026-11-14T10:00:00Z")

    # Non-selected verified_document history row (RB3-73) -> L1 verified_lineage_unavailable
    _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=105,
        unit="mg/dL",
        measured_at="2026-10-20T08:00:00Z",
        source="verified_document",
        trust_level="doctor_verified",
        source_fact_id=other_facts["value"].id,
        verified_by_user_id=doctor.user_id,
        verified_at=AT_ISO,
    )
    # Multi-defect historical row (RB3-83): validation='rejected' AND future timestamp -> validation_rejected
    multi_obs = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=80,
        unit="bpm",
        measured_at="2026-11-15T12:00:00Z",
        validation="rejected",
    )
    # Unit mismatch -> unit_mismatch
    unit_obs = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=80,
        unit="mg/dL",
        measured_at="2026-10-15T12:00:00Z",
    )
    # Malformed historical row (RB3-85): +Inf value satisfies SQLite CHECK (>0) and triggers MonitoringInputError -> malformed_history
    mal_obs = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=float("inf"),
        unit="bpm",
        measured_at="2026-10-16T12:00:00Z",
    )
    # Future skew boundary (RB3-87): +1min -> L2 future_timestamp; +6min -> L1 future_timestamp
    skew_1m = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=81,
        unit="bpm",
        measured_at="2026-11-14T12:01:00Z",
    )
    skew_6m = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=82,
        unit="bpm",
        measured_at="2026-11-14T12:06:00Z",
    )

    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (cur_obs.id,), tmp_path, req_id="rb3-excl"
    )
    rec = _persist(engine, doctor, run_id, tmp_path)

    excl_map = {(e.observation_id, e.reason_code) for e in rec.excluded_evidence}
    assert (multi_obs.id, "validation_rejected") in excl_map
    assert (unit_obs.id, "unit_mismatch") in excl_map
    assert (mal_obs.id, "malformed_history") in excl_map
    assert (skew_6m.id, "future_timestamp") in excl_map
    assert (skew_1m.id, "future_timestamp") in excl_map
    assert rec.l1_exclusion_count >= 4
    assert rec.l2_exclusion_count >= 1
    assert any(
        e.observation_id == skew_1m.id and e.reason_code == "future_timestamp"
        for e in rec.layered_exclusions.l2_exclusions
    )
    assert any(
        e.observation_id == skew_6m.id and e.reason_code == "future_timestamp"
        for e in rec.layered_exclusions.l1_exclusions
    )


def test_rb3_24_concurrent_invocation_single_winner_no_partial(scoped, engine, tmp_path: Path):
    """RB3-24: concurrent invocations produce exactly one evaluation and one audit."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "conc")
    obs = _obs(db, patient_id, value=120)
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-conc"
    )

    results: list[ReviewPersistenceReceiptV1] = []
    errors: list[ApiError] = []
    barrier = threading.Barrier(2)

    def _worker():
        barrier.wait()
        try:
            results.append(_persist(engine, doctor, run_id, tmp_path))
        except ApiError as err:
            errors.append(err)

    t1 = threading.Thread(target=_worker)
    t2 = threading.Thread(target=_worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) >= 1
    assert all(e.status_code in {409, 503} for e in errors)
    assert db.scalar(select(func.count()).select_from(ReviewEvaluation)) == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.event_type == rb3.RB3_AUDIT_EVENT_TYPE,
                AuditEvent.workflow_run_id == run_id,
            )
        )
        == 1
    )


def test_rb3_33_to_40_r01_to_r08_and_rb3_94_95_decimal_and_range(scoped, engine, tmp_path: Path):
    """RB3-33..40/94/95: R01-R08 regressions, Decimal context restoration, malformed created_at, year-1 denial."""
    db, patient_id, doctor = scoped
    db.execute(delete(Observation).where(Observation.patient_id == patient_id))
    db.commit()
    doc, _ = _verified_doc(db, patient_id, tmp_path, "reg")

    # Baseline 100.0 & current 121.1 systolic_bp (R08 exact decimal delta 21.1 >= 10),
    # plus malformed created_at historical row (RB3-94 -> R03 missing_created_at)
    _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=Decimal("100.0"),
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
        created_at="2026-10-20T09:00:00Z",
    )
    bad_created = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=Decimal("101.0"),
        unit="mmHg",
        measured_at="2026-10-21T09:00:00Z",
        created_at="not-an-iso-timestamp",
    )
    cur = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=Decimal("121.1"),
        unit="mmHg",
        measured_at="2026-11-14T10:00:00Z",
        created_at="2026-11-14T10:00:00Z",
    )
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (cur.id,), tmp_path, req_id="rb3-r08"
    )

    # RB3-95(a): mutate ambient decimal context to prec=5, assert prec=28 computation & restoration
    low_ctx = Context(prec=5)
    with localcontext(low_ctx):
        from decimal import getcontext

        rec = _persist(engine, doctor, run_id, tmp_path)
        assert getcontext().prec == 5

    items = (
        db.execute(select(ReviewItem).where(ReviewItem.workflow_run_id == run_id)).scalars().all()
    )
    assert any(it.rule_id == "DR-005" for it in items)
    assert any(
        e.observation_id == bad_created.id and e.reason_code == "missing_created_at"
        for e in rec.layered_exclusions.l2_exclusions
    )

    # RB3-95(b): year-1 observation -> 409 E_VALIDATION measurement_timestamp_out_of_supported_range
    yr1_obs = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=90,
        unit="bpm",
        measured_at="0001-06-01T00:00:00Z",
        created_at="2026-11-14T10:00:00Z",
    )
    yr1_run = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (yr1_obs.id,), tmp_path, req_id="rb3-yr1"
    )
    with localcontext(low_ctx):
        from decimal import getcontext

        with pytest.raises(ApiError) as yr1_exc:
            _persist(engine, doctor, yr1_run, tmp_path)
        assert getcontext().prec == 5
    assert yr1_exc.value.status_code == 409
    assert yr1_exc.value.code == ErrorCode.VALIDATION
    assert RB3DenialReason.MEASUREMENT_TIMESTAMP_OUT_OF_SUPPORTED_RANGE.value in str(yr1_exc.value)


def test_rb3_41_to_43_82_no_http_surface_no_caller_authority_and_model_fields():
    """RB3-41..43/53/82: no HTTP routes, strict keyword signature, ORM columns match payload."""
    app = create_app()
    paths = set(app.openapi()["paths"])
    assert not any("review" in p for p in paths)

    sig = inspect.signature(rb3.persist_run_review_items)
    assert set(sig.parameters) == {"db", "principal", "run_id", "validation_clock", "upload_root"}

    src = (REPO_ROOT / "backend" / "app" / "services" / "p4_rb3_review_persistence.py").read_text()
    tree = ast.parse(src)
    # Static check: no access to Document.created_at or FactVerification.status / .verified_at
    assert "docs_by_id[doc_id].uploaded_at" in src
    assert "d.decision" in src and "d.decided_at" in src and "d.source_image_compared" in src
    assert "Document.created_at" not in src
    assert "FactVerification.status" not in src
    assert isinstance(tree, ast.Module)


def test_rb3_45_to_52_93_input_identity_sensitivity_note_isolation_and_order(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-45..52/93: input identity detects history/eligibility changes, ignores Note-only in RB3, T9->T10 order."""
    db, patient_id, doctor = scoped
    db.execute(delete(Observation).where(Observation.patient_id == patient_id))
    db.commit()
    doc, _ = _verified_doc(db, patient_id, tmp_path, "ident")

    hist_nonbase = _obs(
        db, patient_id, measure_type="heart_rate", value=70, measured_at="2026-09-01T08:00:00Z"
    )
    _obs(db, patient_id, measure_type="heart_rate", value=72, measured_at="2026-10-25T08:00:00Z")
    cur = _obs(
        db, patient_id, measure_type="heart_rate", value=110, measured_at="2026-11-14T10:00:00Z"
    )

    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (cur.id,), tmp_path, req_id="rb3-id"
    )

    # RB3-93: verify T9 OfflineRuleInput is built before _compute_input_identity is invoked
    order_log: list[str] = []
    orig_compute = rb3._compute_input_identity

    def _spy_compute(**kwargs):
        assert isinstance(kwargs.get("rule_input"), OfflineRuleInput)
        order_log.append("compute_after_t9")
        return orig_compute(**kwargs)

    monkeypatch.setattr(rb3, "_compute_input_identity", _spy_compute)
    rec = _persist(engine, doctor, run_id, tmp_path)
    # Called at T10 (after T9 OfflineRuleInput construction) and re-verified at T17
    assert order_log == ["compute_after_t9", "compute_after_t9"]
    monkeypatch.undo()

    # RB3-46: change non-baseline historical observation value -> denied 409 (F1/RB3 detect change)
    hist_nonbase.value = 75.0
    db.commit()
    with pytest.raises(ApiError) as ch_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert ch_exc.value.status_code == 409
    assert ch_exc.value.code == ErrorCode.VALIDATION
    hist_nonbase.value = 70.0
    db.commit()

    # Precedence 5 (input_identity_changed) when RB3 input identity differs on replay
    monkeypatch.setattr(rb3, "_compute_input_identity", lambda **_kw: "d" * 64)
    with pytest.raises(ApiError) as p5_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert p5_exc.value.status_code == 409
    assert p5_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.INPUT_IDENTITY_CHANGED.value in str(p5_exc.value)
    monkeypatch.undo()

    # RB3-52: change Observation.note only -> RB3 input identity unaffected, F1 gate digest mismatch -> 409
    cur.note = "free text changed"
    db.commit()
    with pytest.raises(ApiError) as note_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert note_exc.value.status_code == 409
    cur.note = None
    db.commit()

    # RB3-51: identity stable across repeated replay
    assert (
        _persist(engine, doctor, run_id, tmp_path).input_fingerprint_sha256
        == rec.input_fingerprint_sha256
    )


def test_rb3_59_to_65_70_92_111_to_114_128_replay_conflicts_and_audit_contract(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-59..65/70/92/111..114/128: conflict precedence 1..8, 9-key audit <= 500 chars, round trip."""
    # RB3-111/113/114: prove 9-key audit detail <= SAFE_DETAIL_MAX across whole permitted domain
    eval_id = "11111111-1111-4111-8111-111111111111"
    sha_a = "a" * 64
    sha_b = "b" * 64
    max_len = 0
    for ic in (0, 1, 12):
        for lc in (0, 1, 24):
            for ec in (0, 9, 200):
                _frags, composed = rb3._compose_audit_fragments(
                    evaluation_id=eval_id,
                    input_fingerprint_sha256=sha_a,
                    output_identity_sha256=sha_b,
                    item_count=ic,
                    evidence_link_count=lc,
                    exclusion_count=ec,
                )
                assert len(composed) <= SAFE_DETAIL_MAX
                keys = tuple(p.split("=", 1)[0] for p in composed.split("; "))
                assert keys == rb3.RB3_AUDIT_DETAIL_KEYS
                for absent_key in ("gate", "bridge", "policy", "demo_only"):
                    assert absent_key not in keys
                max_len = max(max_len, len(composed))
    assert max_len == 346

    # Contrast: old 13-fragment shape exceeded SAFE_DETAIL_MAX=500 and truncated exclusions
    old_13 = safe_detail(
        f"fingerprint_version={rb3.RB3_FINGERPRINT_VERSION}",
        f"evaluation_id={eval_id}",
        f"input={sha_a}",
        f"output={sha_b}",
        f"gate={sha_a}",
        f"bridge={sha_b}",
        "policy=demo-policy-1.1.0",
        "lineage_label_policy=a2_transport_label",
        "dr006_policy=prohibited_denied",
        "items=12",
        "links=24",
        "exclusions=200",
        "demo_only=1",
    )
    assert len(old_13) == SAFE_DETAIL_MAX
    assert "exclusions=200" not in old_13

    # Replay conflict precedence tests (1..8)
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "conflicts")
    obs = _obs(db, patient_id, value=120)

    # Precedence 2: orphan_review_audit when no ReviewEvaluation exists
    run_orphan = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (), tmp_path, req_id="rb3-orphan"
    )
    req_id_hash = hashlib.sha256(
        "|".join(
            ("p4-rb3-audit-request", rb3.RB3_AUDIT_EVENT_TYPE, run_orphan, doctor.user_id)
        ).encode()
    ).hexdigest()
    append_audit_event(
        db,
        event_type=rb3.RB3_AUDIT_EVENT_TYPE,
        actor_type=doctor.actor_type,
        actor_id=doctor.user_id,
        outcome=AuditOutcome.OK,
        request_id=req_id_hash,
        now=CLOCK,
        patient_id=patient_id,
        workflow_run_id=run_orphan,
        subject_type="workflow_run",
        subject_id=run_orphan,
        detail_fragments=("orphan=1",),
    )
    db.commit()
    with pytest.raises(ApiError) as orph_exc:
        _persist(engine, doctor, run_orphan, tmp_path)
    assert orph_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.ORPHAN_REVIEW_AUDIT.value in str(orph_exc.value)

    # Precedence 1: completion_evidence_missing (ReviewItem exists without ReviewEvaluation)
    run_comp_miss = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-cm"
    )
    db.execute(
        text(
            "INSERT INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
            "VALUES ('91111111-1111-4111-8111-111111111111', :pid, :rid, 'DR-009', 'implausible_value', 'data_quality', 'self_reported', 'msg', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 0, :ts)"
        ),
        {"pid": patient_id, "rid": run_comp_miss, "dk": "e" * 64, "ts": CLOCK_ISO},
    )
    db.commit()
    with pytest.raises(ApiError) as cm_exc:
        _persist(engine, doctor, run_comp_miss, tmp_path)
    assert cm_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.COMPLETION_EVIDENCE_MISSING.value in str(cm_exc.value)

    # Precedence 8 (RB3-70): append_audit_event returns pre-existing colliding row -> audit_key_collision
    run_col = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-col"
    )
    fake_audit = AuditEvent(
        id="92222222-2222-4222-8222-222222222222",
        event_type="checkin.created",
        actor_type="user",
        actor_id=doctor.user_id,
        patient_id=patient_id,
        workflow_run_id=None,
        subject_type="patient",
        subject_id=patient_id,
        outcome="ok",
        idempotency_key="f" * 64,
        safe_detail="collided",
        created_at=CLOCK_ISO,
    )
    db.add(fake_audit)
    db.commit()
    monkeypatch.setattr(rb3, "append_audit_event", lambda *a, **kw: fake_audit)
    with pytest.raises(ApiError) as col_exc:
        _persist(engine, doctor, run_col, tmp_path)
    assert col_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.AUDIT_KEY_COLLISION.value in str(col_exc.value)
    monkeypatch.undo()

    # Happy persist on run_col, then RB3-128: tamper audit_event safe_detail -> precedence 7 audit_business_inconsistent
    rec_col = _persist(engine, doctor, run_col, tmp_path)
    audit_row = db.get(AuditEvent, rec_col.audit_event_id)
    assert audit_row is not None
    audit_row.safe_detail = "tampered=1"
    db.commit()
    with pytest.raises(ApiError) as aud_exc:
        _persist(engine, doctor, run_col, tmp_path)
    assert aud_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.AUDIT_BUSINESS_INCONSISTENT.value in str(aud_exc.value)

    # Precedence 6: output_identity_changed (zero-item persisted -> evaluator patched to return 1 item)
    run_zero_to_one = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (), tmp_path, req_id="rb3-z2o"
    )
    _persist(engine, doctor, run_zero_to_one, tmp_path)
    monkeypatch.setattr(
        rb3,
        "evaluate_p4_rb2_offline_fixture",
        lambda inp: OfflineRuleResult(
            policy_version=rb3.RB3_POLICY_VERSION,
            demo_only=True,
            offline_candidate_rules_evaluated=True,
            runtime_evaluable=False,
            rules_executed=False,
            review_items_persisted=False,
            policy_status="unapproved",
            flags=(
                OfflineRuleFlag(
                    rule_id="DR-009",
                    reason_code="implausible_value",
                    workflow_hint="data_quality",
                    trust_basis="self_reported",
                    message="Synthetic change",
                    evidence=(f"observation:{obs.id}",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key="1" * 64,
                    provenance_status="fixture_asserted",
                ),
            ),
            excluded=(),
        ),
    )
    # Note: obs.id is not in allowed_obs_ids unless obs exists; let's attach obs to allowed_obs_ids (it's in history)
    with pytest.raises(ApiError) as out_exc:
        _persist(engine, doctor, run_zero_to_one, tmp_path)
    assert out_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.OUTPUT_IDENTITY_CHANGED.value in str(out_exc.value)


def test_rb3_66_99_dr006_unit_level_boundary_denies_whole_invocation(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-66/99 (unit-level boundary ONLY — does NOT prove end-to-end DR-006 reachability).

    Verifies that whenever the frozen RB2 evaluator emits a DR-006 flag for two
    qualifying stored-proved rows, T12 denies the ENTIRE invocation with
    409 E_VALIDATION (dr006_persistence_not_authorized) and zero writes.
    """
    db, patient_id, doctor = scoped
    d1, f1 = _verified_doc(db, patient_id, tmp_path, "dr6-1", value="105")
    d2, f2 = _verified_doc(db, patient_id, tmp_path, "dr6-2", value="140")
    o1 = _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=105,
        unit="mg/dL",
        measured_at="2026-10-20T09:00:00Z",
        source="verified_document",
        trust_level="doctor_verified",
        source_fact_id=f1["value"].id,
        verified_by_user_id=doctor.user_id,
        verified_at=AT_ISO,
    )
    o2 = _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=140,
        unit="mg/dL",
        measured_at="2026-10-20T09:00:00Z",
        source="verified_document",
        trust_level="doctor_verified",
        source_fact_id=f2["value"].id,
        verified_by_user_id=doctor.user_id,
        verified_at=AT_ISO,
    )
    # Verify frozen RB2 emits DR-006 on two qualifying stored-proved rows
    policy = OfflineRulePolicy(
        policy_version="demo-policy-1.1.0",
        demo_only=True,
        demo_as_of_utc=CLOCK,
        baseline_lookback_days=90,
        stale_measurement_days=30,
        demo_delta_systolic_mmHg=Decimal("10"),
        demo_delta_diastolic_mmHg=Decimal("8"),
        demo_delta_heart_rate_bpm=Decimal("15"),
        demo_delta_glucose_mgdl=Decimal("40"),
        ocr_confidence_floor=Decimal("0.70"),
        conflict_tolerance=Decimal("0"),
        max_items_per_type=3,
        enabled_verification_issues=rb3.RB3_EXPECTED_VI_ISSUES,
        enabled_rules=rb3.RB3_EXPECTED_RULES,
        notice=rb3.RB3_NOTICE,
    )
    direct_res = evaluate_p4_rb2_offline_fixture(
        OfflineRuleInput(
            patient_id=patient_id,
            selected_current=(
                OfflineObservation(
                    id=o1.id,
                    patient_id=patient_id,
                    measure_type="glucose",
                    value=Decimal("105"),
                    unit="mg/dL",
                    measured_at="2026-10-20T09:00:00Z",
                    validation="ok",
                    trust_level="doctor_verified",
                    created_at="2026-10-20T09:00:00Z",
                    source="verified_document",
                    source_document_id=d1.id,
                    source_fact_id=f1["value"].id,
                    source_fact_verification_status="verified",
                    lineage_status="fixture_asserted",
                ),
                OfflineObservation(
                    id=o2.id,
                    patient_id=patient_id,
                    measure_type="glucose",
                    value=Decimal("140"),
                    unit="mg/dL",
                    measured_at="2026-10-20T09:00:00Z",
                    validation="ok",
                    trust_level="doctor_verified",
                    created_at="2026-10-20T09:00:00Z",
                    source="verified_document",
                    source_document_id=d2.id,
                    source_fact_id=f2["value"].id,
                    source_fact_verification_status="verified",
                    lineage_status="fixture_asserted",
                ),
            ),
            history=(),
            as_of_utc=CLOCK,
            policy=policy,
            active_fact_verification_statuses=("verified",),
        )
    )
    assert any(fl.rule_id == "DR-006" for fl in direct_res.flags)

    # Now verify T12 denies whole invocation with zero writes
    doc_clean, _ = _verified_doc(db, patient_id, tmp_path, "dr6-clean")
    obs_clean = _obs(db, patient_id, value=120, measured_at="2026-11-14T10:00:00Z")
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc_clean.id,), (obs_clean.id,), tmp_path, req_id="rb3-dr6"
    )
    before = _counts(db)
    monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", lambda _inp: direct_res)
    with pytest.raises(ApiError) as dr6_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert dr6_exc.value.status_code == 409
    assert dr6_exc.value.code == ErrorCode.VALIDATION
    assert RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED.value in str(dr6_exc.value)
    assert _counts(db) == before


def test_rb3_79_97_98_provenance_stored_lineage_proved_superseded_facts_and_exclusion_bounds(
    scoped, engine, tmp_path: Path
):
    """RB3-79/97/98: stored_lineage_proved=1 for verified_document, 0 for checkin; superseded facts."""
    db, patient_id, doctor = scoped
    doc, facts = _verified_doc(db, patient_id, tmp_path, "lineage")
    # Supersede facts["unit"] with a valid rejected->corrected chain (RB3-97)
    facts["unit"].verification_status = "rejected"
    orig_fv = db.execute(
        select(FactVerification).where(FactVerification.fact_id == facts["unit"].id)
    ).scalar_one()
    orig_fv.decision = "corrected"
    orig_fv.previous_value = "wrong"
    orig_fv.new_value = "mg/dL"
    corr = ExtractedFact(
        document_id=doc.id,
        patient_id=patient_id,
        field_name="unit",
        raw_text="mg/dL",
        normalized_value="mg/dL",
        unit=None,
        page_index=0,
        char_start=0,
        char_end=5,
        verification_status="verified",
        corrected_from_fact_id=facts["unit"].id,
        created_at=AT_ISO,
    )
    db.add(corr)
    db.commit()

    obs_doc = _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=105,
        unit="mg/dL",
        measured_at="2026-11-14T10:00:00Z",
        source="verified_document",
        trust_level="doctor_verified",
        source_fact_id=facts["value"].id,
        verified_by_user_id=doctor.user_id,
        verified_at=AT_ISO,
    )
    obs_self = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=120,
        unit="bpm",
        measured_at="2026-11-14T10:00:00Z",
    )
    run_id = _start_and_gate(
        engine,
        db,
        patient_id,
        doctor,
        (doc.id,),
        (obs_doc.id, obs_self.id),
        tmp_path,
        req_id="rb3-lin",
    )
    _persist(engine, doctor, run_id, tmp_path)

    items = (
        db.execute(
            select(ReviewItem)
            .where(ReviewItem.workflow_run_id == run_id)
            .order_by(ReviewItem.display_order)
        )
        .scalars()
        .all()
    )
    assert items
    for item in items:
        assert item.provenance_status == "fixture_asserted"
        links = (
            db.execute(select(EvidenceLink).where(EvidenceLink.owner_id == item.id)).scalars().all()
        )
        obs_ids = {lnk.observation_id for lnk in links}
        if obs_ids == {obs_doc.id}:
            assert item.stored_lineage_proved == 1
        elif obs_self.id in obs_ids:
            assert item.stored_lineage_proved == 0
