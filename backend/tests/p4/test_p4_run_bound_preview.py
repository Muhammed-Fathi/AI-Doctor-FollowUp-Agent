"""P4-RB1 synthetic bounded READ-ONLY run-bound preview acceptance matrix.

No rule evaluation, DR output, migrations, agent/LLM, graph or patient actions.
The parent F1 gate is persisted separately and must be rechecked by the preview.
"""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import ApiError
from app.core.policies import Principal
from app.db.models import (
    AuditEvent,
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    RunGateEvaluation,
    User,
    UserSession,
    WorkflowRun,
)
from app.services import p4_run_bound_preview as rb
from app.services.p5_evidence_bridge import build_run_evaluable_review_evidence
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
RECORDED_AT = "2026-06-14T08:00:00Z"


@pytest.fixture()
def scoped(engine):
    with Session(engine) as db:
        seed_demo_data(db, password="synthetic-rb1-fixture", now=CLOCK, iterations=1000)
        db.commit()
        patient = db.execute(
            select(Patient).where(Patient.external_ref == "DEMO-A-001")
        ).scalar_one()
        doctor = db.execute(
            select(User).where(User.username == "demo_doctor")
        ).scalar_one()
        session = UserSession(
            id="d5555555-5555-4555-8555-555555555555",
            user_id=doctor.id,
            token_sha256=hashlib.sha256(b"rb1-synthetic-session").hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
        db.add(session)
        db.commit()
        principal = Principal(
            user_id=doctor.id,
            username=doctor.username,
            display_name=doctor.display_name,
            role=Role(doctor.role),
            patient_id=doctor.patient_id,
            session_id=session.id,
        )
        yield db, patient.id, principal


def _verified_document(db: Session, patient_id: str, root: Path, label: str) -> Document:
    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"RB1 synthetic-only source: {label}".encode()
    name = f"rb1-{label}.pdf"
    (root / name).write_bytes(raw)
    document = Document(
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
        uploaded_at=RECORDED_AT,
    )
    db.add(document)
    db.flush()
    for field, value, unit in (
        ("report_date", "2026-06-14", None),
        ("test_name", "glucose", None),
        ("value", "105", "mg/dL"),
        ("unit", "mg/dL", None),
    ):
        fact = ExtractedFact(
            document_id=document.id,
            patient_id=patient_id,
            field_name=field,
            raw_text=value,
            normalized_value=value,
            unit=unit,
            page_index=0,
            char_start=0,
            char_end=len(value),
            verification_status="verified",
            created_at=RECORDED_AT,
        )
        db.add(fact)
        db.flush()
        db.add(
            FactVerification(
                fact_id=fact.id,
                decision="verified",
                verified_by_user_id=patient.assigned_doctor_id,
                decided_at=RECORDED_AT,
            )
        )
    db.commit()
    return document


def _observation(
    db: Session,
    patient_id: str,
    *,
    measured_at: str,
    value: int,
    validation: str = "ok",
) -> Observation:
    row = Observation(
        patient_id=patient_id,
        measure_type="heart_rate",
        value=value,
        unit="bpm",
        measured_at=measured_at,
        source="patient_checkin",
        validation=validation,
        trust_level="self_reported_validated",
        created_at=RECORDED_AT,
    )
    db.add(row)
    db.commit()
    return row


def _start(
    db: Session,
    patient_id: str,
    doctor: Principal,
    document: Document,
    selected: tuple[str, ...] = (),
    *,
    clock: datetime = CLOCK,
) -> str:
    receipt = create_run_foundation(
        db,
        principal=doctor,
        patient_id=patient_id,
        document_ids=(document.id,),
        observation_ids=selected,
        omissions=(),
        client_request_id="rb1-preview-run",
        as_of_utc=clock,
    )
    db.commit()
    return receipt.run_id


def _gate(engine, doctor: Principal, run_id: str, root: Path, *, clock: datetime = CLOCK):
    with Session(engine) as db:
        return evaluate_run_verification_gate(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=clock,
            upload_root=str(root),
        )


def _preview(engine, doctor: Principal, run_id: str, root: Path, *, clock: datetime = CLOCK):
    with Session(engine) as db:
        return rb.build_p4_run_bound_review_input_preview(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=clock,
            upload_root=str(root),
        )


def test_rb1_requires_persisted_fresh_f1_proceed(scoped, engine, tmp_path):
    """RB-01/02: a queued F0 run is not a gate, even if its facts are verified."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "missing-gate")
    run_id = _start(db, patient_id, doctor, doc)
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path)
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 0


def test_rb1_zero_selected_is_deterministic_and_has_no_writes(scoped, engine, tmp_path):
    """RB-01/06/12/21: no invented current or DR, stable replay, no DB writes."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "no-current")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    db.expire_all()
    before_gate = db.scalar(select(func.count()).select_from(RunGateEvaluation))
    before_audit = db.scalar(select(func.count()).select_from(AuditEvent))

    one = _preview(engine, doctor, run_id, tmp_path)
    two = _preview(engine, doctor, run_id, tmp_path)
    assert one == two
    assert one.policy_version == "demo-policy-1.1.0"
    assert one.policy_reference_sha256 == rb.POLICY_CANONICAL_SHA256
    assert one.policy_baseline_lookback_days == 90
    assert one.policy_comparisons == ()
    assert one.selected_observations == ()
    assert one.no_current_reason == "no_current_selected"
    assert one.verified_facts
    assert not one.runtime_evaluable and not one.rules_executed
    assert not one.review_items_persisted and one.policy_status == "unapproved"
    with pytest.raises(FrozenInstanceError):
        one.runtime_evaluable = True
    with pytest.raises(FrozenInstanceError):
        one.policy_status = "approved"
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == before_gate
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == before_audit
    assert db.get(WorkflowRun, run_id).status == "queued"


def test_rb1_365_day_f2_baseline_is_not_a_90_day_policy_baseline(
    scoped, engine, tmp_path
):
    """RB-04: day-180 F2 comparison is NOT admitted by R3-A's 90-day policy."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "long-history")
    # This scenario deliberately isolates heart-rate history from the seeded
    # Oct heart-rate values; other patient measures and all documents remain.
    db.execute(
        delete(Observation).where(
            Observation.patient_id == patient_id,
            Observation.measure_type == "heart_rate",
        )
    )
    db.commit()
    baseline = _observation(
        db, patient_id, measured_at="2026-05-19T09:00:00Z", value=70
    )
    current = _observation(
        db, patient_id, measured_at="2026-11-14T11:59:00Z", value=76
    )
    run_id = _start(db, patient_id, doctor, doc, selected=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    with Session(engine) as fresh:
        f2 = build_run_evaluable_review_evidence(
            fresh,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
    assert f2.comparisons[0].baseline_observation_id == baseline.id
    assert f2.comparisons[0].delta == Decimal("6")
    rb1 = _preview(engine, doctor, run_id, tmp_path)
    assert len(rb1.policy_comparisons) == 1
    compared = rb1.policy_comparisons[0]
    assert compared.current_observation_id == current.id
    assert not compared.comparable
    assert compared.baseline_observation_id is None
    assert compared.delta is None
    assert compared.incomparable_reason == "no_baseline"


def test_rb1_90_day_baseline_is_latest_prior_and_trust_retained(
    scoped, engine, tmp_path
):
    """RB-05/10: recent source is chosen, Decimal delta; no self-report promotion."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "recent")
    prev = _observation(
        db, patient_id, measured_at="2026-11-12T09:00:00Z", value=70
    )
    current = _observation(
        db, patient_id, measured_at="2026-11-14T11:59:00Z", value=76
    )
    run_id = _start(db, patient_id, doctor, doc, selected=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    result = _preview(engine, doctor, run_id, tmp_path)
    comparison = result.policy_comparisons[0]
    assert comparison.baseline_observation_id == prev.id
    assert comparison.comparable and comparison.delta == Decimal("6")
    assert comparison.incomparable_reason is None
    assert comparison.trust_basis == "self_reported"
    assert result.selected_observations[0].trust_level == "self_reported_validated"


def test_rb1_history_exclusions_remain_explicit(scoped, engine, tmp_path):
    """RB-08: rejected history is excluded, never silently used as a baseline."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "excluded")
    invalid = _observation(
        db, patient_id, measured_at="2026-11-13T09:00:00Z", value=75,
        validation="rejected",
    )
    current = _observation(
        db, patient_id, measured_at="2026-11-14T11:59:00Z", value=76
    )
    run_id = _start(db, patient_id, doctor, doc, selected=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    result = _preview(engine, doctor, run_id, tmp_path)
    assert any(
        item.observation_id == invalid.id and item.reason_code == "validation_rejected"
        for item in result.history_exclusions
    )
    assert result.policy_comparisons[0].baseline_observation_id != invalid.id


def test_rb1_source_file_change_denied_not_cached(scoped, engine, tmp_path):
    """RB-03: recheck raw source bytes even after a previously successful gate."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "tamper")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    (tmp_path / doc.stored_path).write_bytes(b"tampered synthetic source")
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path)


def test_rb1_revoked_doctor_denied(scoped, engine, tmp_path):
    """RB-02: a stale doctor session must not be reused as a gate."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "revoked")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    session = db.get(UserSession, doctor.session_id)
    assert session is not None
    session.revoked_at = "2026-11-14T11:00:00Z"
    db.commit()
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path)


def test_rb1_wrong_role_and_dirty_session_fail_closed(scoped, engine, tmp_path):
    """RB-02/20: do not accept caller role escalation or already active SQL state."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "role")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    wrong = Principal(
        user_id=doctor.user_id,
        username=doctor.username,
        display_name=doctor.display_name,
        role=Role.PATIENT,
        patient_id=doctor.patient_id,
        session_id=doctor.session_id,
    )
    with pytest.raises(ApiError):
        _preview(engine, wrong, run_id, tmp_path)
    with Session(engine) as tx:
        tx.execute(select(WorkflowRun).where(WorkflowRun.id == run_id)).first()
        with pytest.raises(ApiError):
            rb.build_p4_run_bound_review_input_preview(
                tx,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )


def test_rb1_cannot_accept_caller_policy_or_gate_override(
    scoped, engine, tmp_path
):
    """RB-11/21: caller cannot inject 90/365, gate status or cached V2 DTO."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "override")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    with Session(engine) as fresh, pytest.raises(TypeError):
        rb.build_p4_run_bound_review_input_preview(
            fresh,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
            baseline_lookback_days=365,
            blocking_fact_count=0,
        )


def test_rb1_pinned_policy_tamper_is_not_a_fallback(
    scoped, engine, tmp_path, monkeypatch
):
    """RB-11: a modified reference is never a second unapproved policy."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "policy-change")
    run_id = _start(db, patient_id, doctor, doc)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    bad_reference = tmp_path / "reference.yaml"
    bad_reference.write_text("policy_version: demo-policy-1.1.0\n", encoding="utf-8")
    monkeypatch.setattr(rb, "POLICY_PATH", bad_reference)
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path)


def test_rb1_rejects_unpinned_run_clock(scoped, engine, tmp_path):
    """RB-11: this R3-A demo preview is pinned to the approved injected clock."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "clock")
    another = CLOCK - timedelta(days=1)
    run_id = _start(db, patient_id, doctor, doc, clock=another)
    assert _gate(engine, doctor, run_id, tmp_path, clock=another).decision == "proceed"
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path, clock=another)


def test_rb1_7_selected_does_not_truncate_to_six(scoped, engine, tmp_path):
    """RB-07: F0 accepts seven but F2/RB1 must deny, not pick six."""
    db, patient_id, doctor = scoped
    doc = _verified_document(db, patient_id, tmp_path, "seven")
    selected = []
    for index in range(7):
        row = _observation(
            db,
            patient_id,
            measured_at=f"2026-11-13T{index + 1:02d}:00:00Z",
            value=70 + index,
        )
        selected.append(row.id)
    run_id = _start(db, patient_id, doctor, doc, selected=tuple(selected))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    with pytest.raises(ApiError):
        _preview(engine, doctor, run_id, tmp_path)
