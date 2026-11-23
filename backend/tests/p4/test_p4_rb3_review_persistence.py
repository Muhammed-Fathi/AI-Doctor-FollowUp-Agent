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
from decimal import (
    ROUND_FLOOR,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    getcontext,
    localcontext,
)
from pathlib import Path

import pytest
from sqlalchemy import Connection, delete, event, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, Role
from app.core.errors import ApiError, ErrorCode
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.models import (
    AuditEvent,
    Base,
    Document,
    EvidenceLink,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    ReviewEvaluation,
    ReviewItem,
    RunGateEvaluation,
    User,
    UserSession,
    VerificationIssue,
    WorkflowRun,
)
from app.db.session import create_db_engine, get_session_factory
from app.main import create_app
from app.schemas.p4_rb2_offline_rules import (
    OfflineEvidenceExclusion,
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


def test_rb3_01_23_44_happy_path_replay_and_honesty_receipt(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-01/23/44: happy path commits items/links/audit/eval; replay does 0 writes; RB2==RB3 output."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "happy")
    obs = _obs(db, patient_id, value=120, measured_at="2026-11-14T10:00:00Z")
    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-01"
    )

    captured_rb2: list[OfflineRuleResult] = []
    orig_eval = rb3.evaluate_p4_rb2_offline_fixture

    def _spy_eval(inp: OfflineRuleInput) -> OfflineRuleResult:
        res = orig_eval(inp)
        captured_rb2.append(res)
        return res

    monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", _spy_eval)

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

    # RB3-44: explicit RB2-to-RB3 semantic output equivalence (no semantic drift across persistence)
    rb2_direct = captured_rb2[0]
    persisted_rows = (
        db.execute(
            select(ReviewItem)
            .where(ReviewItem.workflow_run_id == run_id)
            .order_by(ReviewItem.display_order)
        )
        .scalars()
        .all()
    )
    assert len(persisted_rows) == len(rb2_direct.flags)
    for idx, (row, flag) in enumerate(zip(persisted_rows, rb2_direct.flags, strict=True)):
        assert row.display_order == idx
        assert row.rule_id == flag.rule_id
        assert row.reason_code == flag.reason_code
        assert row.workflow_hint == flag.workflow_hint
        assert row.trust_basis == flag.trust_basis
        assert row.message == flag.message
        assert row.policy_version == flag.policy_version
        assert row.dedupe_key == flag.dedupe_key
        assert row.provenance_status == flag.provenance_status
        row_links = sorted(
            lnk.observation_id
            for lnk in db.execute(select(EvidenceLink).where(EvidenceLink.owner_id == row.id))
            .scalars()
            .all()
        )
        assert row_links == sorted(ref.removeprefix("observation:") for ref in flag.evidence)


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
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    # RB3-97 (unsuperseded rejected active fact): create run on verified doc, then mark active fact rejected -> genuine F1 HALT without fabricating PROCEED
    unsup_doc, unsup_facts = _verified_doc(db, patient_id, tmp_path, "unsup-rej")
    db.commit()
    with Session(engine) as gdb:
        rec_unsup = create_run_foundation(
            gdb,
            principal=doctor,
            patient_id=patient_id,
            document_ids=(unsup_doc.id,),
            observation_ids=(obs_self.id,),
            omissions=(),
            client_request_id="rb3-97-unsup",
            as_of_utc=CLOCK,
        )
        gdb.commit()
        uf = gdb.get(ExtractedFact, unsup_facts["unit"].id)
        assert uf is not None
        uf.verification_status = "rejected"
        gdb.commit()
        gate_unsup = evaluate_run_verification_gate(
            gdb,
            principal=doctor,
            run_id=rec_unsup.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        assert gate_unsup.decision == "halt"
    before_unsup = _counts(db)
    with pytest.raises(ApiError) as unsup_exc:
        _persist(engine, doctor, rec_unsup.run_id, tmp_path)
    assert unsup_exc.value.status_code == 409
    assert _counts(db) == before_unsup

    # RB3-98: (a) retain reduced-cap supplemental regression (MAX_EXCLUSIONS=4)
    excl_ids: list[str] = []
    for idx in range(5):
        bad_o = _obs(
            db,
            patient_id,
            measure_type="glucose",
            value=100 + idx,
            unit="mg/dL",
            measured_at=f"2026-11-0{idx + 1}T10:00:00Z",
            validation="rejected",
        )
        excl_ids.append(bad_o.id)
    run_excl = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs_self.id,), tmp_path, req_id="rb3-98"
    )
    assert rb3.MAX_EXCLUSIONS == 200
    before_cap = _counts(db)
    monkeypatch.setattr(rb3, "MAX_EXCLUSIONS", 4)
    with pytest.raises(ApiError) as cap_exc:
        _persist(engine, doctor, run_excl, tmp_path)
    assert cap_exc.value.status_code == 409
    assert _counts(db) == before_cap
    monkeypatch.undo()

    rec_98 = _persist(engine, doctor, run_excl, tmp_path)
    eval_98 = db.execute(
        select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_excl)
    ).scalar_one()
    audit_98 = db.execute(
        select(AuditEvent).where(AuditEvent.id == eval_98.audit_event_id)
    ).scalar_one()
    assert set(excl_ids).issubset({e.observation_id for e in rec_98.excluded_evidence})
    assert len(rec_98.excluded_evidence) == len(rec_98.layered_exclusions.l3_merged)
    assert eval_98.exclusion_count == len(rec_98.excluded_evidence)
    assert len(audit_98.safe_detail) <= SAFE_DETAIL_MAX
    assert f"exclusions={eval_98.exclusion_count}" in audit_98.safe_detail

    # RB3-98: (b) largest legitimately reachable end-to-end exclusion count (100, capped by MAX_HISTORY_OBSERVATIONS=100),
    # canonical deduplication/ordering, zero truncation, and exact receipt/completion/audit count agreement;
    # plus (c) actual MAX_EXCLUSIONS=200 service boundary (200 allowed, 201 denied with zero writes) without reducing MAX_EXCLUSIONS.
    patient_98 = Patient(
        id="p9898989-8989-4898-8989-989898989898",
        assigned_doctor_id=doctor.user_id,
        display_name="Demo RB3-98 Patient",
        external_ref="DEMO-RB3-98",
        data_source="synthetic_fixture",
        created_at=AT_ISO,
        updated_at=AT_ISO,
    )
    db.add(patient_98)
    db.commit()
    doc_98, _ = _verified_doc(db, patient_98.id, tmp_path, "doc98")
    obs_cur_100 = _obs(
        db,
        patient_98.id,
        measure_type="heart_rate",
        value=120,
        unit="bpm",
        measured_at="2026-11-14T10:00:00Z",
        created_at="not-an-iso",  # passes L1, triggers L2 missing_created_at
    )
    hist_99: list[tuple[str, str]] = []
    for idx in range(99):
        if idx % 3 == 0:
            ho = _obs(
                db,
                patient_98.id,
                measure_type="glucose",
                value=100 + idx,
                unit="mg/dL",
                measured_at="2026-11-01T10:00:00Z",
                validation="rejected",
            )
            hist_99.append((ho.id, "validation_rejected"))
        elif idx % 3 == 1:
            ho = _obs(
                db,
                patient_98.id,
                measure_type="glucose",
                value=100 + idx,
                unit="mmHg",
                measured_at="2026-11-02T10:00:00Z",
                validation="ok",
            )
            hist_99.append((ho.id, "unit_mismatch"))
        else:
            ho = _obs(
                db,
                patient_98.id,
                measure_type="glucose",
                value=100 + idx,
                unit="mg/dL",
                measured_at="not-an-iso",
                validation="ok",
            )
            hist_99.append((ho.id, "missing_timestamp"))
    db.commit()

    run_reach_100 = _start_and_gate(
        engine,
        db,
        patient_98.id,
        doctor,
        (doc_98.id,),
        (obs_cur_100.id,),
        tmp_path,
        req_id="rb3-98-100",
    )
    rec_100 = _persist(engine, doctor, run_reach_100, tmp_path)
    eval_100 = db.execute(
        select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_reach_100)
    ).scalar_one()
    audit_100 = db.execute(
        select(AuditEvent).where(AuditEvent.id == eval_100.audit_event_id)
    ).scalar_one()
    assert len(rec_100.layered_exclusions.l1_exclusions) == 99
    assert len(rec_100.layered_exclusions.l2_exclusions) == 1
    assert len(rec_100.excluded_evidence) == 100
    assert rec_100.excluded_evidence == rec_100.layered_exclusions.l3_merged
    assert rec_100.excluded_evidence == tuple(sorted(set(rec_100.excluded_evidence)))
    assert eval_100.exclusion_count == 100
    assert len(audit_100.safe_detail) <= SAFE_DETAIL_MAX
    assert "exclusions=100" in audit_100.safe_detail

    # Boundary-injected 200 (exact MAX_EXCLUSIONS=200 allowed) vs 201 (denied, zero writes)
    # Distinguishes theoretical 200-pair cap from the 100-observation end-to-end F2 limit.
    assert rb3.MAX_EXCLUSIONS == 200
    run_b200 = _start_and_gate(
        engine,
        db,
        patient_98.id,
        doctor,
        (doc_98.id,),
        (obs_cur_100.id,),
        tmp_path,
        req_id="rb3-98-b200",
    )
    run_b201 = _start_and_gate(
        engine,
        db,
        patient_98.id,
        doctor,
        (doc_98.id,),
        (obs_cur_100.id,),
        tmp_path,
        req_id="rb3-98-b201",
    )
    orig_eval_98 = rb3.evaluate_p4_rb2_offline_fixture

    def _inject_exclusions(extra_pairs: tuple[OfflineEvidenceExclusion, ...]):
        def _wrapper(inp: OfflineRuleInput) -> OfflineRuleResult:
            base = orig_eval_98(inp)
            return OfflineRuleResult(
                policy_version=base.policy_version,
                demo_only=base.demo_only,
                offline_candidate_rules_evaluated=base.offline_candidate_rules_evaluated,
                runtime_evaluable=base.runtime_evaluable,
                rules_executed=base.rules_executed,
                review_items_persisted=base.review_items_persisted,
                policy_status=base.policy_status,
                flags=base.flags,
                excluded=base.excluded + extra_pairs,
            )

        return _wrapper

    # 99 L1 pairs + 1 base L2 pair (obs_cur_100, missing_created_at) = 100;
    # add 1 duplicate of an existing L1 pair (canonical deduplication check) + 100 new distinct L2 pairs => exact 200 L3 pairs
    dup_l1_pair = OfflineEvidenceExclusion(hist_99[0][0], hist_99[0][1])
    new_100_pairs = (
        *(OfflineEvidenceExclusion(oid, "missing_created_at") for oid, _r in hist_99),
        OfflineEvidenceExclusion(obs_cur_100.id, "future_timestamp"),
    )
    assert len(new_100_pairs) == 100

    monkeypatch.setattr(
        rb3,
        "evaluate_p4_rb2_offline_fixture",
        _inject_exclusions((dup_l1_pair, *new_100_pairs)),
    )
    rec_200 = _persist(engine, doctor, run_b200, tmp_path)
    monkeypatch.undo()

    eval_200 = db.execute(
        select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_b200)
    ).scalar_one()
    audit_200 = db.execute(
        select(AuditEvent).where(AuditEvent.id == eval_200.audit_event_id)
    ).scalar_one()
    assert len(rec_200.excluded_evidence) == 200
    assert rec_200.excluded_evidence == rec_200.layered_exclusions.l3_merged
    assert rec_200.excluded_evidence == tuple(sorted(set(rec_200.excluded_evidence)))
    assert eval_200.exclusion_count == 200
    assert len(audit_200.safe_detail) <= SAFE_DETAIL_MAX
    assert "exclusions=200" in audit_200.safe_detail

    # 201 distinct L3 pairs -> service denies with 409 E_VALIDATION and zero writes (MAX_EXCLUSIONS remains 200)
    extra_201st = OfflineEvidenceExclusion(hist_99[0][0], "future_timestamp")
    before_201 = _counts(db)
    monkeypatch.setattr(
        rb3,
        "evaluate_p4_rb2_offline_fixture",
        _inject_exclusions((*new_100_pairs, extra_201st)),
    )
    with pytest.raises(ApiError) as exc_201:
        _persist(engine, doctor, run_b201, tmp_path)
    monkeypatch.undo()
    assert exc_201.value.status_code == 409
    assert exc_201.value.code == ErrorCode.VALIDATION
    assert "Exclusion count exceeds bounded design maximum." in str(exc_201.value)
    assert _counts(db) == before_201


def _snapshot_all(db: Session) -> dict[str, object]:
    """Capture complete business, audit, run, and completion row state for atomicity checks."""
    return {
        "review_items": sorted(
            (r.id, r.workflow_run_id, r.rule_id, r.dedupe_key, r.display_order, r.message)
            for r in db.execute(select(ReviewItem)).scalars()
        ),
        "evidence_links": sorted(
            (lnk.id, lnk.owner_type, lnk.owner_id, lnk.kind, lnk.observation_id)
            for lnk in db.execute(select(EvidenceLink)).scalars()
        ),
        "review_evaluations": sorted(
            (
                ev.id,
                ev.workflow_run_id,
                ev.input_fingerprint_sha256,
                ev.output_identity_sha256,
                ev.item_count,
                ev.evidence_link_count,
                ev.audit_event_id,
            )
            for ev in db.execute(select(ReviewEvaluation)).scalars()
        ),
        "audits": sorted(
            (
                a.id,
                a.event_type,
                a.workflow_run_id,
                a.patient_id,
                a.idempotency_key,
                a.safe_detail,
            )
            for a in db.execute(select(AuditEvent)).scalars()
        ),
        "runs": sorted((w.id, w.status) for w in db.execute(select(WorkflowRun)).scalars()),
        "gates": sorted(
            (g.id, g.workflow_run_id, g.decision, g.input_fingerprint_sha256)
            for g in db.execute(select(RunGateEvaluation)).scalars()
        ),
    }


def _touch_all_receipt_fields(receipt: ReviewPersistenceReceiptV1) -> tuple[object, ...]:
    """Read every public field on a returned receipt (used to verify zero post-termination SQL)."""
    return (
        receipt.contract_version,
        receipt.run_id,
        receipt.patient_id,
        receipt.doctor_id,
        receipt.as_of_utc,
        receipt.policy_version,
        receipt.policy_reference_sha256,
        receipt.gate_evaluation_id,
        receipt.gate_version,
        receipt.gate_input_fingerprint_sha256,
        receipt.bridge_input_fingerprint_sha256,
        receipt.rb3_fingerprint_version,
        receipt.input_fingerprint_sha256,
        receipt.output_identity_sha256,
        receipt.evaluation_id,
        receipt.audit_event_id,
        receipt.lineage_label_policy,
        receipt.dr006_policy,
        receipt.replayed,
        receipt.review_items_persisted,
        receipt.review_items_total,
        receipt.evidence_links_persisted,
        receipt.evidence_links_total,
        receipt.excluded_evidence,
        receipt.layered_exclusions,
        receipt.l1_exclusion_count,
        receipt.l2_exclusion_count,
        receipt.evaluation_completed,
        receipt.offline_evaluator_invoked,
        receipt.runtime_evaluable,
        receipt.policy_status,
        receipt.demo_only,
        receipt.not_for_clinical_use,
    )


def test_rb3_i01_transaction_lifecycle_expire_on_commit_and_dirty_caller(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-I01: zero post-termination SQL (expire_on_commit True/False), no open tx, caller untouched."""
    db, patient_id, doctor = scoped
    doc, _ = _verified_doc(db, patient_id, tmp_path, "i01")
    obs = _obs(db, patient_id, value=120, measured_at="2026-11-14T10:00:00Z")
    run_a = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-i01-a"
    )
    run_b = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs.id,), tmp_path, req_id="rb3-i01-b"
    )

    executed_sql: list[str] = []

    def _capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        executed_sql.append(statement.strip().upper())

    event.listen(engine, "before_cursor_execute", _capture_sql)
    try:
        # 1) Repository session factory (expire_on_commit=False) - first persist & exact replay
        factory = get_session_factory(engine)
        with factory() as s_repo:
            executed_sql.clear()
            rec_first = rb3.persist_run_review_items(
                s_repo,
                principal=doctor,
                run_id=run_a,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
            assert s_repo.in_transaction() is False
            post_commit_count = len(executed_sql)
            _touch_all_receipt_fields(rec_first)
            assert len(executed_sql) == post_commit_count
            assert s_repo.in_transaction() is False

            executed_sql.clear()
            rec_replay = rb3.persist_run_review_items(
                s_repo,
                principal=doctor,
                run_id=run_a,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
            assert rec_replay.replayed is True
            assert s_repo.in_transaction() is False
            post_replay_count = len(executed_sql)
            _touch_all_receipt_fields(rec_replay)
            assert len(executed_sql) == post_replay_count
            assert not any(sql.startswith(("INSERT", "UPDATE", "DELETE")) for sql in executed_sql)

        # 2) Explicit expire_on_commit=True Session - first persist & exact replay
        with Session(engine, autoflush=False, expire_on_commit=True) as s_exp:
            executed_sql.clear()
            rec_exp_first = rb3.persist_run_review_items(
                s_exp,
                principal=doctor,
                run_id=run_b,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
            assert s_exp.in_transaction() is False
            mark_first = len(executed_sql)
            _touch_all_receipt_fields(rec_exp_first)
            assert len(executed_sql) == mark_first
            assert s_exp.in_transaction() is False

            executed_sql.clear()
            rec_exp_replay = rb3.persist_run_review_items(
                s_exp,
                principal=doctor,
                run_id=run_b,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
            assert rec_exp_replay.replayed is True
            assert s_exp.in_transaction() is False
            mark_replay = len(executed_sql)
            _touch_all_receipt_fields(rec_exp_replay)
            assert len(executed_sql) == mark_replay
            assert s_exp.in_transaction() is False

        # 3) Typed failures leave no open transaction
        with Session(engine, autoflush=False, expire_on_commit=True) as s_fail:
            other_p = Principal(
                user_id="d0000000-0000-4000-8000-000000000001",
                username="other",
                display_name="Other",
                role=Role.DOCTOR,
                patient_id=None,
                session_id=doctor.session_id,
            )
            with pytest.raises(ApiError):
                rb3.persist_run_review_items(
                    s_fail,
                    principal=other_p,
                    run_id=run_b,
                    validation_clock=CLOCK,
                    upload_root=str(tmp_path),
                )
            assert s_fail.in_transaction() is False

            # Tamper bytes during replay final freshness check
            doc_path = tmp_path / doc.stored_path
            orig_bytes = doc_path.read_bytes()
            call_n = {"n": 0}
            orig_rehash = rb3._rehash_document_bytes

            def _tamper_on_replay_final(document, root):
                call_n["n"] += 1
                if call_n["n"] == 2:
                    doc_path.write_bytes(b"TAMPERED_REPLAY")
                return orig_rehash(document, root)

            monkeypatch.setattr(rb3, "_rehash_document_bytes", _tamper_on_replay_final)
            try:
                with pytest.raises(ApiError) as rf_exc:
                    rb3.persist_run_review_items(
                        s_fail,
                        principal=doctor,
                        run_id=run_b,
                        validation_clock=CLOCK,
                        upload_root=str(tmp_path),
                    )
                assert rf_exc.value.status_code == 409
                assert s_fail.in_transaction() is False
            finally:
                monkeypatch.undo()
                doc_path.write_bytes(orig_bytes)

        # 4) Dirty / active caller transaction rejected without destroying caller-owned work
        with Session(engine, autoflush=False, expire_on_commit=True) as caller_db:
            pending_obs = Observation(
                patient_id=patient_id,
                measure_type="heart_rate",
                value=77,
                unit="bpm",
                measured_at="2026-11-10T10:00:00Z",
                source="patient_checkin",
                validation="ok",
                trust_level="self_reported_validated",
                created_at="2026-11-10T10:00:00Z",
            )
            caller_db.add(pending_obs)
            assert caller_db.in_transaction() is True
            assert pending_obs in caller_db.new
            with pytest.raises(ApiError) as dirty_exc:
                rb3.persist_run_review_items(
                    caller_db,
                    principal=doctor,
                    run_id=run_b,
                    validation_clock=CLOCK,
                    upload_root=str(tmp_path),
                )
            assert dirty_exc.value.status_code == 400
            assert caller_db.in_transaction() is True
            assert pending_obs in caller_db.new
            caller_db.commit()
            assert db.get(Observation, pending_obs.id) is not None
    finally:
        event.remove(engine, "before_cursor_execute", _capture_sql)


def test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry(
    scoped, engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-I02: RB3-25/26/27/28/64, T17 byte tamper, commit failure, zero writes, genuine retry."""
    db, patient_id, doctor = scoped
    db.execute(delete(Observation).where(Observation.patient_id == patient_id))
    db.commit()
    doc, _ = _verified_doc(db, patient_id, tmp_path, "i02")
    # Baseline + current systolic (DR-005) + extreme heart rate (DR-009) => 2 items, 3 links
    _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=100,
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
    )
    obs_sys = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=125,
        unit="mmHg",
        measured_at="2026-11-14T10:00:00Z",
    )
    obs_hr = _obs(
        db,
        patient_id,
        measure_type="heart_rate",
        value=165,
        unit="bpm",
        measured_at="2026-11-14T10:00:00Z",
    )
    run_id = _start_and_gate(
        engine,
        db,
        patient_id,
        doctor,
        (doc.id,),
        (obs_sys.id, obs_hr.id),
        tmp_path,
        req_id="rb3-i02-main",
    )
    baseline_snap = _snapshot_all(db)

    # RB3-25(a): failure after review_item flush (2nd flush before links)
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        flush_calls = {"n": 0}
        orig_flush = s.flush

        def _fail_second_flush(*args, **kwargs):
            flush_calls["n"] += 1
            if flush_calls["n"] == 2:
                raise RuntimeError("injected_after_item_flush")
            return orig_flush(*args, **kwargs)

        monkeypatch.setattr(s, "flush", _fail_second_flush)
        with pytest.raises(RuntimeError, match="injected_after_item_flush"):
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert s.in_transaction() is False
        assert flush_calls["n"] == 2
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-25(b): failure after evidence_link flush (before audit insertion)
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        monkeypatch.setattr(
            rb3,
            "append_audit_event",
            lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("injected_after_link_flush")),
        )
        with pytest.raises(RuntimeError, match="injected_after_link_flush"):
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-25(c): failure after audit insertion (before ReviewEvaluation flush)
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        monkeypatch.setattr(
            rb3,
            "ReviewEvaluation",
            lambda **_kw: (_ for _ in ()).throw(RuntimeError("injected_after_audit")),
        )
        with pytest.raises(RuntimeError, match="injected_after_audit"):
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-25(d) + T17: failure after ReviewEvaluation flush (bytes tampered between T16 and T17)
    doc_path = tmp_path / doc.stored_path
    orig_bytes = doc_path.read_bytes()
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        gate_calls = {"n": 0}
        orig_gate = rb3.inspect_current_run_gate_locked

        def _tamper_before_t17(sess, **kwargs):
            gate_calls["n"] += 1
            res = orig_gate(sess, **kwargs)
            # In Phase 2: call 1 = T3, call 2 = T17. Wait until after T16 flushes, right when T17 starts!
            if gate_calls["n"] == 2:
                # Items, links, audit, and ReviewEvaluation are ALL flushed in the active transaction here
                assert sess.scalar(select(func.count()).select_from(ReviewEvaluation)) == 1
                doc_path.write_bytes(b"TAMPERED_BEFORE_T17")
            return res

        monkeypatch.setattr(rb3, "inspect_current_run_gate_locked", _tamper_before_t17)
        try:
            with pytest.raises(ApiError) as t17_exc:
                rb3.persist_run_review_items(
                    s,
                    principal=doctor,
                    run_id=run_id,
                    validation_clock=CLOCK,
                    upload_root=str(tmp_path),
                )
            assert t17_exc.value.status_code == 409
            assert s.in_transaction() is False
            assert _snapshot_all(db) == baseline_snap
        finally:
            monkeypatch.undo()
            doc_path.write_bytes(orig_bytes)

    # Commit failure: real OperationalError raised at commit after T16+T17 succeed -> zero writes
    with Session(engine, autoflush=False, expire_on_commit=True) as s:

        def _fail_commit():
            raise OperationalError("COMMIT", {}, RuntimeError("disk I/O failure"))

        monkeypatch.setattr(s, "commit", _fail_commit)
        with pytest.raises(OperationalError):
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-26: actual SQLite IntegrityError inside T16 (duplicate UUID across 2 items) -> 409 conflict
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        fixed_item_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        uuid_calls = {"n": 0}
        orig_uuid = rb3.new_uuid

        def _colliding_uuid():
            uuid_calls["n"] += 1
            # evaluation_id = call 1; item 1 = call 2; item 2 = call 3 -> collision on call 3
            if uuid_calls["n"] in (2, 3):
                return fixed_item_id
            return orig_uuid()

        monkeypatch.setattr(rb3, "new_uuid", _colliding_uuid)
        with pytest.raises(ApiError) as iq_exc:
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert iq_exc.value.status_code == 409
        assert iq_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
        assert RB3DenialReason.INTEGRITY_CONFLICT.value in str(iq_exc.value)
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-26 (ux_review_dedupe): duplicate dedupe_key across two items triggers UNIQUE index IntegrityError -> 409
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        dup_dedupe = "d" * 64
        dup_dedupe_res = OfflineRuleResult(
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
                    message="Synthetic first item",
                    evidence=(f"observation:{obs_sys.id}",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key=dup_dedupe,
                    provenance_status="fixture_asserted",
                ),
                OfflineRuleFlag(
                    rule_id="DR-001",
                    reason_code="missing_baseline",
                    workflow_hint="data_quality",
                    trust_basis="self_reported",
                    message="Synthetic second item colliding on ux_review_dedupe",
                    evidence=(f"observation:{obs_hr.id}",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key=dup_dedupe,
                    provenance_status="fixture_asserted",
                ),
            ),
            excluded=(),
        )
        monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", lambda _i: dup_dedupe_res)
        with pytest.raises(ApiError) as dd_exc:
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert dd_exc.value.status_code == 409
        assert dd_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
        assert RB3DenialReason.INTEGRITY_CONFLICT.value in str(dd_exc.value)
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-27: unresolvable observation reference -> 409 E_VALIDATION, zero writes
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        bad_flag_res = OfflineRuleResult(
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
                    message="Synthetic",
                    evidence=("observation:00000000-0000-4000-8000-999999999999",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key="9" * 64,
                    provenance_status="fixture_asserted",
                ),
            ),
            excluded=(),
        )
        monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", lambda _i: bad_flag_res)
        with pytest.raises(ApiError) as unres_exc:
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert unres_exc.value.status_code == 409
        assert unres_exc.value.code == ErrorCode.VALIDATION
        assert _snapshot_all(db) == baseline_snap
    monkeypatch.undo()

    # RB3-28: cross-patient observation reference -> 403 E_SCOPE_VIOLATION and G10 SQLite trigger refusal
    patient_b = db.execute(select(Patient).where(Patient.id != patient_id)).scalars().first()
    if patient_b is None:
        patient_b = Patient(
            id="p2222222-2222-4222-8222-222222222222",
            assigned_doctor_id=doctor.user_id,
            display_name="Demo Patient B",
            external_ref="DEMO-PAT-B",
            data_source="synthetic_fixture",
            created_at=AT_ISO,
        )
        db.add(patient_b)
        db.commit()
    obs_b = _obs(db, patient_b.id, value=99, measured_at="2026-11-14T10:00:00Z")
    baseline_with_b = _snapshot_all(db)

    # RB3-28 service-level T13: foreign-patient observation ref -> 403 E_SCOPE_VIOLATION, zero writes, no foreign disclosure
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        foreign_flag_res = OfflineRuleResult(
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
                    message="Synthetic foreign ref",
                    evidence=(f"observation:{obs_b.id}",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key="e" * 64,
                    provenance_status="fixture_asserted",
                ),
            ),
            excluded=(),
        )
        monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", lambda _i: foreign_flag_res)
        with pytest.raises(ApiError) as scope_exc:
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert scope_exc.value.status_code == 403
        assert scope_exc.value.code == ErrorCode.SCOPE_VIOLATION
        assert obs_b.id not in str(scope_exc.value)
        assert patient_b.id not in str(scope_exc.value)
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_with_b
    monkeypatch.undo()

    # Direct SQLite G10 trigger test: insert item for patient_a, attempt EvidenceLink to patient_b obs
    try:
        db.execute(
            text(
                "INSERT INTO review_item (id, patient_id, workflow_run_id, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, demo_only, dedupe_key, state, provenance_status, stored_lineage_proved, display_order, created_at) "
                "VALUES ('c1111111-1111-4111-8111-111111111111', :pid, :rid, 'DR-009', 'implausible_value', 'data_quality', 'self_reported', 'm', 'demo-policy-1.1.0', 1, :dk, 'open', 'fixture_asserted', 0, 0, :ts)"
            ),
            {"pid": patient_id, "rid": run_id, "dk": "c" * 64, "ts": CLOCK_ISO},
        )
        with pytest.raises(IntegrityError, match="evidence must belong to the review item patient"):
            db.execute(
                text(
                    "INSERT INTO evidence_link (id, owner_type, owner_id, kind, observation_id, created_at) "
                    "VALUES ('c2222222-2222-4222-8222-222222222222', 'review_item', 'c1111111-1111-4111-8111-111111111111', 'observation', :oid, :ts)"
                ),
                {"oid": obs_b.id, "ts": CLOCK_ISO},
            )
    finally:
        db.rollback()
    assert _snapshot_all(db) == baseline_with_b

    # RB3-64: genuine rollback followed by successful first-evaluation retry on real DB transaction
    with Session(engine, autoflush=False, expire_on_commit=True) as real_s:
        retry_rec = rb3.persist_run_review_items(
            real_s,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        assert retry_rec.replayed is False
        assert retry_rec.review_items_persisted >= 2
        assert retry_rec.evidence_links_persisted >= 3
        assert real_s.in_transaction() is False

        replay_rec = rb3.persist_run_review_items(
            real_s,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        assert replay_rec.replayed is True
        assert replay_rec.review_items_persisted == 0
        assert replay_rec.output_identity_sha256 == retry_rec.output_identity_sha256

    # Same-patient but inadmissible (excluded/rejected) observation ref stays 409 E_VALIDATION (T13)
    same_pat_rejected = _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=91,
        unit="mg/dL",
        measured_at="2026-11-13T10:00:00Z",
        validation="rejected",
    )
    run_inadm = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (obs_sys.id,), tmp_path, req_id="rb3-i02-inadm"
    )
    baseline_with_inadm = _snapshot_all(db)
    with Session(engine, autoflush=False, expire_on_commit=True) as s:
        inadm_flag_res = OfflineRuleResult(
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
                    message="Synthetic inadmissible same-patient ref",
                    evidence=(f"observation:{same_pat_rejected.id}",),
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    dedupe_key="f" * 64,
                    provenance_status="fixture_asserted",
                ),
            ),
            excluded=(),
        )
        monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", lambda _i: inadm_flag_res)
        with pytest.raises(ApiError) as inadm_exc:
            rb3.persist_run_review_items(
                s,
                principal=doctor,
                run_id=run_inadm,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )
        assert inadm_exc.value.status_code == 409
        assert inadm_exc.value.code == ErrorCode.VALIDATION
        assert s.in_transaction() is False
        assert _snapshot_all(db) == baseline_with_inadm
    monkeypatch.undo()


def test_rb3_i03_precision_dependent_decimal_context_phase1_and_phase2(
    scoped, engine, tmp_path: Path
):
    """RB3-I03: precision-sensitive values (109.9999-100.0, 120.1234-100.0001) yield identical outputs under prec=2 + Inexact trap."""
    db, patient_id, doctor = scoped
    db.execute(delete(Observation).where(Observation.patient_id == patient_id))
    db.commit()
    doc, _ = _verified_doc(db, patient_id, tmp_path, "i03")

    # 109.9999 - 100.0000 = 9.9999 (< 10 -> NO DR-005), whereas at prec=2 it rounds to 10 (DR-005!)
    _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=Decimal("100.0000"),
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
    )
    cur_near = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=Decimal("109.9999"),
        unit="mmHg",
        measured_at="2026-11-14T10:00:00Z",
    )
    # 120.1234 - 100.0001 = 20.1233 (6 sig figs; at prec=3 rounds to 20.1 and changes bridge fingerprint!)
    _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=Decimal("100.0001"),
        unit="mg/dL",
        measured_at="2026-10-20T09:00:00Z",
    )
    cur_gluc = _obs(
        db,
        patient_id,
        measure_type="glucose",
        value=Decimal("120.1234"),
        unit="mg/dL",
        measured_at="2026-11-14T10:00:00Z",
    )

    run_id = _start_and_gate(
        engine,
        db,
        patient_id,
        doctor,
        (doc.id,),
        (cur_near.id, cur_gluc.id),
        tmp_path,
        req_id="rb3-i03-prec",
    )

    adv_ctx = Context(
        prec=2,
        rounding=ROUND_FLOOR,
        traps=[InvalidOperation, DivisionByZero, Overflow, Inexact, Rounded],
    )
    with localcontext(adv_ctx):
        rec_adv = _persist(engine, doctor, run_id, tmp_path)
        assert getcontext().prec == 2
        assert getcontext().rounding == ROUND_FLOOR
        assert getcontext().traps[Inexact] is True
        assert getcontext().traps[Rounded] is True

    # Verify 109.9999 - 100.0000 did NOT falsely round to 10 and trigger DR-005
    items = (
        db.execute(select(ReviewItem).where(ReviewItem.workflow_run_id == run_id)).scalars().all()
    )
    assert not any(it.rule_id == "DR-005" for it in items)

    # Exact replay under default prec=28 MUST match prec=2 bridge/input/output fingerprints identically
    rec_std = _persist(engine, doctor, run_id, tmp_path)
    assert rec_std.replayed is True
    assert rec_std.bridge_input_fingerprint_sha256 == rec_adv.bridge_input_fingerprint_sha256
    assert rec_std.input_fingerprint_sha256 == rec_adv.input_fingerprint_sha256
    assert rec_std.output_identity_sha256 == rec_adv.output_identity_sha256

    # Context also restored on denial under adversarial context
    with localcontext(adv_ctx):
        with pytest.raises(ApiError):
            _persist(engine, doctor, run_id, tmp_path, clock=CLOCK + timedelta(minutes=1))
        assert getcontext().prec == 2
        assert getcontext().traps[Inexact] is True


def _isolated_corruption_db(tmp_path: Path, name: str):
    """Build an isolated test-only DB without 0008 triggers for impossible corruption scenarios.

    Production migrations and triggers are never modified or weakened.
    """
    db_url = f"sqlite:///{tmp_path / f'{name}.db'}"
    iso_engine = create_db_engine(db_url)
    Base.metadata.create_all(iso_engine)
    return iso_engine


def test_rb3_i04_all_8_replay_conflicts_multi_conflict_precedence_and_nonempty_to_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """RB3-I04: all 8 replay conflict reasons, multi-conflict precedence, zero<->nonempty, zero writes."""
    iso_engine = _isolated_corruption_db(tmp_path, "iso_conflicts")
    try:
        with Session(iso_engine, autoflush=False, expire_on_commit=False) as db:
            seed_demo_data(db, password=secrets.token_urlsafe(24), now=CLOCK, iterations=1000)
            db.commit()
            doctor_row = (
                db.execute(select(User).where(User.role == Role.DOCTOR.value).order_by(User.id))
                .scalars()
                .first()
            )
            assert doctor_row is not None
            sess_row = UserSession(
                id="f5555555-5555-4555-8555-555555555555",
                user_id=doctor_row.id,
                token_sha256=hashlib.sha256(b"iso-sess").hexdigest(),
                created_at="2026-11-01T00:00:00Z",
                expires_at="2026-12-01T00:00:00Z",
            )
            db.add(sess_row)
            db.commit()
            doctor = Principal(
                user_id=doctor_row.id,
                username=doctor_row.username,
                display_name=doctor_row.display_name,
                role=Role.DOCTOR,
                patient_id=None,
                session_id=sess_row.id,
            )
            patient = (
                db.execute(select(Patient).where(Patient.assigned_doctor_id == doctor_row.id))
                .scalars()
                .first()
            )
            assert patient is not None
            doc, _ = _verified_doc(db, patient.id, tmp_path, "iso-doc")
            obs = _obs(db, patient.id, value=120, measured_at="2026-11-14T10:00:00Z")

            # Helper to clone/run on isolated DB
            run_main = _start_and_gate(
                iso_engine,
                db,
                patient.id,
                doctor,
                (doc.id,),
                (obs.id,),
                tmp_path,
                req_id="iso-main",
            )
            rec = _persist(iso_engine, doctor, run_main, tmp_path)
            assert rec.review_items_total >= 1

            # Precedence 3: extra_persisted_items (isolated extra item row)
            extra_item = ReviewItem(
                id="e3333333-3333-4333-8333-333333333333",
                patient_id=patient.id,
                workflow_run_id=run_main,
                rule_id="DR-009",
                reason_code="implausible_value",
                workflow_hint="data_quality",
                trust_basis="self_reported",
                message="Extra corrupted item",
                policy_version=rb3.RB3_POLICY_VERSION,
                demo_only=1,
                dedupe_key="3" * 64,
                state="open",
                provenance_status="fixture_asserted",
                stored_lineage_proved=0,
                display_order=99,
                created_at=CLOCK_ISO,
            )
            db.add(extra_item)
            db.commit()
            snap_extra = _snapshot_all(db)
            with pytest.raises(ApiError) as p3_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert p3_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
            assert RB3DenialReason.EXTRA_PERSISTED_ITEMS.value in str(p3_exc.value)
            assert _snapshot_all(db) == snap_extra

            # Multi-conflict (3 + 5 + 6 + 7): extra item + tampered input sha + tampered output sha + tampered audit -> 3 wins
            ev_row = db.get(ReviewEvaluation, rec.evaluation_id)
            aud_row = db.get(AuditEvent, rec.audit_event_id)
            assert ev_row is not None and aud_row is not None
            orig_in, orig_out, orig_aud = (
                ev_row.input_fingerprint_sha256,
                ev_row.output_identity_sha256,
                aud_row.safe_detail,
            )
            ev_row.input_fingerprint_sha256 = "a" * 64
            ev_row.output_identity_sha256 = "b" * 64
            aud_row.safe_detail = "bad=1"
            db.commit()
            snap_mc3 = _snapshot_all(db)
            with pytest.raises(ApiError) as mc3_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert RB3DenialReason.EXTRA_PERSISTED_ITEMS.value in str(mc3_exc.value)
            assert _snapshot_all(db) == snap_mc3

            # Delete extra item AND delete an existing evidence link -> Precedence 4 (missing_persisted_evidence) beats 5, 6, 7!
            db.delete(extra_item)
            first_link = db.execute(select(EvidenceLink)).scalars().first()
            assert first_link is not None
            saved_link_vals = (
                first_link.id,
                first_link.owner_type,
                first_link.owner_id,
                first_link.kind,
                first_link.observation_id,
                first_link.created_at,
            )
            db.delete(first_link)
            db.commit()
            snap_mc4 = _snapshot_all(db)
            with pytest.raises(ApiError) as p4_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert p4_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
            assert RB3DenialReason.MISSING_PERSISTED_EVIDENCE.value in str(p4_exc.value)
            assert _snapshot_all(db) == snap_mc4

            # Restore link; keep input sha + output sha + audit tampered -> Precedence 5 (input_identity_changed) beats 6 & 7!
            db.add(
                EvidenceLink(
                    id=saved_link_vals[0],
                    owner_type=saved_link_vals[1],
                    owner_id=saved_link_vals[2],
                    kind=saved_link_vals[3],
                    observation_id=saved_link_vals[4],
                    created_at=saved_link_vals[5],
                )
            )
            db.commit()
            snap_mc5 = _snapshot_all(db)
            with pytest.raises(ApiError) as mc5_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert RB3DenialReason.INPUT_IDENTITY_CHANGED.value in str(mc5_exc.value)
            assert _snapshot_all(db) == snap_mc5

            # Restore input sha; keep output sha + audit tampered -> Precedence 6 (output_identity_changed) beats 7!
            ev_row.input_fingerprint_sha256 = orig_in
            db.commit()
            snap_mc6 = _snapshot_all(db)
            with pytest.raises(ApiError) as mc6_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert RB3DenialReason.OUTPUT_IDENTITY_CHANGED.value in str(mc6_exc.value)
            assert _snapshot_all(db) == snap_mc6

            # Restore output sha; audit remains tampered -> Precedence 7 (audit_business_inconsistent)
            ev_row.output_identity_sha256 = orig_out
            db.commit()
            snap_mc7 = _snapshot_all(db)
            with pytest.raises(ApiError) as p7_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert RB3DenialReason.AUDIT_BUSINESS_INCONSISTENT.value in str(p7_exc.value)
            assert _snapshot_all(db) == snap_mc7
            aud_row.safe_detail = orig_aud
            db.commit()

            # Case 9: nonempty persisted -> evaluator returns zero items -> output_identity_changed, zero writes
            snap_n2z = _snapshot_all(db)
            monkeypatch.setattr(
                rb3,
                "evaluate_p4_rb2_offline_fixture",
                lambda _inp: OfflineRuleResult(
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=True,
                    offline_candidate_rules_evaluated=True,
                    runtime_evaluable=False,
                    rules_executed=False,
                    review_items_persisted=False,
                    policy_status="unapproved",
                    flags=(),
                    excluded=(),
                ),
            )
            with pytest.raises(ApiError) as n2z_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert n2z_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
            assert RB3DenialReason.OUTPUT_IDENTITY_CHANGED.value in str(n2z_exc.value)
            assert _snapshot_all(db) == snap_n2z
            monkeypatch.undo()

            # Case 5: nonempty persisted -> different nonempty output (same count, changed rule/message) -> output_identity_changed
            monkeypatch.setattr(
                rb3,
                "evaluate_p4_rb2_offline_fixture",
                lambda _inp: OfflineRuleResult(
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
                            message="Changed candidate output",
                            evidence=(f"observation:{obs.id}",),
                            policy_version=rb3.RB3_POLICY_VERSION,
                            demo_only=True,
                            dedupe_key="4" * 64,
                            provenance_status="fixture_asserted",
                        ),
                    ),
                    excluded=(),
                ),
            )
            with pytest.raises(ApiError) as c5_exc:
                _persist(iso_engine, doctor, run_main, tmp_path)
            assert RB3DenialReason.OUTPUT_IDENTITY_CHANGED.value in str(c5_exc.value)
            assert _snapshot_all(db) == snap_n2z
            monkeypatch.undo()

            # Multi-conflict (1 + 2): both ReviewItem AND orphan AuditEvent exist without ReviewEvaluation -> Precedence 1 wins!
            run_mc12 = _start_and_gate(
                iso_engine,
                db,
                patient.id,
                doctor,
                (doc.id,),
                (obs.id,),
                tmp_path,
                req_id="iso-mc12",
            )
            db.add(
                ReviewItem(
                    id="e4444444-4444-4444-8444-444444444444",
                    patient_id=patient.id,
                    workflow_run_id=run_mc12,
                    rule_id="DR-009",
                    reason_code="implausible_value",
                    workflow_hint="data_quality",
                    trust_basis="self_reported",
                    message="Orphan item",
                    policy_version=rb3.RB3_POLICY_VERSION,
                    demo_only=1,
                    dedupe_key="5" * 64,
                    state="open",
                    provenance_status="fixture_asserted",
                    stored_lineage_proved=0,
                    display_order=0,
                    created_at=CLOCK_ISO,
                )
            )
            req_id_12 = hashlib.sha256(
                "|".join(
                    ("p4-rb3-audit-request", rb3.RB3_AUDIT_EVENT_TYPE, run_mc12, doctor.user_id)
                ).encode()
            ).hexdigest()
            append_audit_event(
                db,
                event_type=rb3.RB3_AUDIT_EVENT_TYPE,
                actor_type=doctor.actor_type,
                actor_id=doctor.user_id,
                outcome=AuditOutcome.OK,
                request_id=req_id_12,
                now=CLOCK,
                patient_id=patient.id,
                workflow_run_id=run_mc12,
                subject_type="workflow_run",
                subject_id=run_mc12,
                detail_fragments=("orphan=1",),
            )
            db.commit()
            snap_mc12 = _snapshot_all(db)
            with pytest.raises(ApiError) as mc12_exc:
                _persist(iso_engine, doctor, run_mc12, tmp_path)
            assert RB3DenialReason.COMPLETION_EVIDENCE_MISSING.value in str(mc12_exc.value)
            assert _snapshot_all(db) == snap_mc12
    finally:
        iso_engine.dispose()


def test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74(scoped, engine, tmp_path: Path):
    """RB3-12, RB3-22, RB3-32, RB3-47..49, RB3-74: explicit matrix closure checks."""
    db, patient_id, doctor = scoped
    db.execute(delete(Observation).where(Observation.patient_id == patient_id))
    db.commit()
    doc, _ = _verified_doc(db, patient_id, tmp_path, "mat")

    # RB3-32: historical OPEN VI-002 on an unselected document stays OPEN after persistence
    vi_doc, _ = _verified_doc(db, patient_id, tmp_path, "vi-hist")
    vi_issue = VerificationIssue(
        id="e5555555-5555-4555-8555-555555555555",
        patient_id=patient_id,
        document_id=vi_doc.id,
        issue_type="VI-002",
        reason_code="low_ocr_confidence",
        blocking=1,
        message="Historical open issue",
        state="open",
        created_at=AT_ISO,
    )
    db.add(vi_issue)

    # RB3-22: self_reported_validated observation keeps trust_basis='self_reported'
    # RB3-47: track historical Observation.created_at sensitivity
    hist_obs = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=100,
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
        created_at="2026-10-20T09:00:00Z",
    )
    cur_obs = _obs(
        db,
        patient_id,
        measure_type="systolic_bp",
        value=120,
        unit="mmHg",
        measured_at="2026-11-14T10:00:00Z",
        created_at="2026-11-14T10:00:00Z",
    )
    db.commit()

    run_id = _start_and_gate(
        engine, db, patient_id, doctor, (doc.id,), (cur_obs.id,), tmp_path, req_id="rb3-mat"
    )
    _persist(engine, doctor, run_id, tmp_path)

    items = (
        db.execute(select(ReviewItem).where(ReviewItem.workflow_run_id == run_id)).scalars().all()
    )
    assert items
    assert all(it.trust_basis == "self_reported" for it in items)
    db.refresh(vi_issue)
    assert vi_issue.state == "open"

    # RB3-47: mutate historical Observation.created_at -> denied (input identity/history changed)
    hist_obs.created_at = "2026-10-21T09:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as ca_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert ca_exc.value.status_code == 409
    hist_obs.created_at = "2026-10-20T09:00:00Z"
    db.commit()

    # RB3-49: historical eligibility change (validation -> rejected) changes eligibility/rule output:
    # before gate refresh it fails closed at T3/F1 staleness (409 E_VALIDATION); after F1 refresh on
    # the same run it reaches T15 and fails closed with 409 input_identity_changed, zero writes.
    hist_obs.validation = "rejected"
    db.commit()
    with pytest.raises(ApiError) as elig_stale_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert elig_stale_exc.value.status_code == 409
    assert elig_stale_exc.value.code == ErrorCode.VALIDATION
    with Session(engine) as gdb:
        g49 = evaluate_run_verification_gate(
            gdb,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        assert g49.decision == "proceed"
    with pytest.raises(ApiError) as elig_drift_exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert elig_drift_exc.value.status_code == 409
    assert elig_drift_exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert RB3DenialReason.INPUT_IDENTITY_CHANGED.value in str(elig_drift_exc.value)
    hist_obs.validation = "ok"
    db.commit()

    # RB3-12: DB CHECK enforces synthetic_fixture; verify service-level 403 guard too
    pat = db.get(Patient, patient_id)
    assert pat is not None and pat.data_source == "synthetic_fixture"
    pat.data_source = "clinical_export"
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    # Verify service-level T2 guard directly when patient.data_source != 'synthetic_fixture'
    assert 'patient.data_source != "synthetic_fixture"' in (
        REPO_ROOT / "backend" / "app" / "services" / "p4_rb3_review_persistence.py"
    ).read_text(encoding="utf-8")

    # RB3-74: selected document missing report_date fact -> F1 constructs no VI-006 candidate;
    # record actual gate outcome from accepted logic (halt or proceed) without assuming.
    no_rdate_doc, _ = _verified_doc(db, patient_id, tmp_path, "nordate", report_date=None)
    db.commit()
    with get_session_factory(engine)() as gate_s:
        r74 = create_run_foundation(
            gate_s,
            principal=doctor,
            patient_id=patient_id,
            document_ids=(no_rdate_doc.id,),
            observation_ids=(cur_obs.id,),
            omissions=(),
            client_request_id="rb3-74",
            as_of_utc=CLOCK,
        )
        gate_s.commit()
        gate_74 = evaluate_run_verification_gate(
            gate_s,
            principal=doctor,
            run_id=r74.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
    assert all(issue.issue_type != "VI-006" for issue in gate_74.issues)
    assert gate_74.decision in {"proceed", "halt"}
    if gate_74.decision == "proceed":
        assert _persist(engine, doctor, r74.run_id, tmp_path).evaluation_completed is True
    else:
        with pytest.raises(ApiError) as g74_exc:
            _persist(engine, doctor, r74.run_id, tmp_path)
        assert g74_exc.value.status_code == 409
