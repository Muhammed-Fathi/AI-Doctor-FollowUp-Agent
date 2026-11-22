"""P5-F2 synthetic-only evidence-bridge tests; no DR or graph execution."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
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
    RunGateBlocker,
    RunGateEvaluation,
    User,
    UserSession,
    WorkflowRun,
)
from app.services.p4_recovery_selection_candidate import CandidateDoctorOmission
from app.services.p5_evidence_bridge import build_run_evaluable_review_evidence
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
AT = "2026-06-14T08:00:00Z"


@pytest.fixture()
def scoped(engine):
    with Session(engine) as db:
        fixture_phrase = "-".join(("synthetic", "f2", "fixture", "only"))
        seed_demo_data(db, password=fixture_phrase, now=CLOCK, iterations=1000)
        db.commit()
        patient = db.execute(
            select(Patient).where(Patient.external_ref == "DEMO-A-001")
        ).scalar_one()
        user = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        session = UserSession(
            id="c2222222-2222-4222-8222-222222222222",
            user_id=user.id,
            token_sha256=hashlib.sha256(b"f2-synthetic-session").hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
        db.add(session)
        db.commit()
        principal = Principal(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=Role(user.role),
            patient_id=user.patient_id,
            session_id=session.id,
        )
        yield db, patient.id, principal


def _doc(db: Session, patient_id: str, root: Path, label: str) -> Document:
    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"F2 synthetic fixture {label}".encode()
    name = f"f2-{label}.pdf"
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
        uploaded_at=AT,
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
            created_at=AT,
        )
        db.add(fact)
        db.flush()
        db.add(
            FactVerification(
                fact_id=fact.id,
                decision="verified",
                verified_by_user_id=patient.assigned_doctor_id,
                decided_at=AT,
            )
        )
    db.commit()
    return document


def _observation(
    db: Session,
    patient_id: str,
    *,
    day: int,
    value: float,
    validation: str = "ok",
) -> Observation:
    row = Observation(
        patient_id=patient_id,
        measure_type="heart_rate",
        value=value,
        unit="bpm",
        measured_at=f"2026-11-{day:02d}T09:00:00Z",
        source="patient_checkin",
        validation=validation,
        trust_level="self_reported_validated",
        created_at=AT,
    )
    db.add(row)
    db.commit()
    return row


def _start(
    db: Session,
    patient_id: str,
    doctor: Principal,
    document_id: str,
    observation_ids: tuple[str, ...] = (),
) -> str:
    run = create_run_foundation(
        db,
        principal=doctor,
        patient_id=patient_id,
        document_ids=(document_id,),
        observation_ids=observation_ids,
        omissions=(),
        client_request_id="f2-synthetic-start",
        as_of_utc=CLOCK,
    )
    db.commit()
    return run.run_id


def _gate(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return evaluate_run_verification_gate(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def _bridge(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return build_run_evaluable_review_evidence(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def test_f2_requires_persisted_matching_f1_proceed(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "no-gate")
    run_id = _start(db, patient_id, doctor, document.id)
    with pytest.raises(ApiError):
        _bridge(engine, doctor, run_id, tmp_path)
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 0


def test_f2_clear_run_is_read_only_and_never_runtime_authorized(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "clear")
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    db.expire_all()
    gate_count = db.scalar(select(func.count()).select_from(RunGateEvaluation))
    audit_count = db.scalar(select(func.count()).select_from(AuditEvent))

    first = _bridge(engine, doctor, run_id, tmp_path)
    second = _bridge(engine, doctor, run_id, tmp_path)
    assert first == second
    assert first.contract_version == "2.0.0"
    assert first.bridge_validated and not first.runtime_evaluable
    assert first.policy_status == "unapproved" and not first.rules_executed
    assert first.verified_facts and all(f.verification_status == "verified" for f in first.verified_facts)
    assert first.comparisons == ()
    assert first.no_current_reason == "no_current_selected"
    assert first.gate_input_fingerprint_sha256
    assert first.bridge_input_fingerprint_sha256
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == gate_count
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == audit_count
    assert db.get(WorkflowRun, run_id).status == "queued"


def test_f2_halt_is_not_promoted_into_evidence(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "pending")
    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == document.id, ExtractedFact.field_name == "value"
        )
    ).scalar_one()
    run_id = _start(db, patient_id, doctor, document.id)
    fact.verification_status = "pending"
    db.commit()
    assert _gate(engine, doctor, run_id, tmp_path).decision in {"halt", "unavailable"}
    with pytest.raises(ApiError):
        _bridge(engine, doctor, run_id, tmp_path)


@pytest.mark.parametrize("mutation", ["file", "raw_fact", "verified_decision", "run_status"])
def test_f2_stale_or_corrupt_provenance_never_uses_cached_proceed(
    scoped, engine, tmp_path, mutation
):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, mutation)
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"

    if mutation == "file":
        (tmp_path / document.stored_path).write_bytes(b"altered synthetic bytes")
    elif mutation == "raw_fact":
        fact = db.execute(
            select(ExtractedFact).where(
                ExtractedFact.document_id == document.id,
                ExtractedFact.field_name == "value",
            )
        ).scalar_one()
        fact.raw_text = "106"
    elif mutation == "verified_decision":
        decision = db.execute(
            select(FactVerification)
            .join(ExtractedFact, FactVerification.fact_id == ExtractedFact.id)
            .where(ExtractedFact.document_id == document.id)
        ).scalars().first()
        assert decision is not None
        decision.decision = "rejected"
    else:
        run = db.get(WorkflowRun, run_id)
        assert run is not None
        run.status = "running"
    db.commit()
    with pytest.raises(ApiError):
        _bridge(engine, doctor, run_id, tmp_path)


def test_f2_rejects_forged_extra_gate_blocker(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "forged")
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    evaluation = db.execute(
        select(RunGateEvaluation).where(RunGateEvaluation.workflow_run_id == run_id)
    ).scalar_one()
    db.add(
        RunGateBlocker(
            gate_evaluation_id=evaluation.id,
            issue_type="VI-002",
            reason_code="fact_unverified",
            document_id=document.id,
            fact_ids="[]",
        )
    )
    db.commit()
    with pytest.raises(ApiError):
        _bridge(engine, doctor, run_id, tmp_path)


def test_f2_revoked_session_fails_closed(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "revoked")
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    session = db.get(UserSession, doctor.session_id)
    assert session is not None
    session.revoked_at = "2026-11-14T11:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as err:
        _bridge(engine, doctor, run_id, tmp_path)
    assert err.value.status_code == 403


def test_f2_selected_self_reported_current_and_history_preserve_trust(
    scoped, engine, tmp_path
):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "comparison")
    baseline = _observation(db, patient_id, day=12, value=70)
    current = _observation(db, patient_id, day=13, value=76)
    baseline.measured_at = "2026-11-14T11:58:00Z"
    current.measured_at = "2026-11-14T11:59:00Z"
    db.commit()
    run_id = _start(db, patient_id, doctor, document.id, observation_ids=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"

    evidence = _bridge(engine, doctor, run_id, tmp_path)
    assert evidence.selected_observations[0].observation_id == current.id
    assert evidence.selected_observations[0].trust_level == "self_reported_validated"
    assert evidence.comparisons[0].baseline_observation_id == baseline.id
    assert evidence.comparisons[0].delta == Decimal("6")
    assert evidence.comparisons[0].trust_basis == "self_reported"
    assert evidence.comparisons[0].comparable
    assert not evidence.runtime_evaluable


def test_f2_empty_baseline_is_explicit_no_baseline(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "no-baseline")
    current = _observation(db, patient_id, day=13, value=76)
    current.measured_at = "2026-01-01T09:00:00Z"
    db.commit()
    run_id = _start(db, patient_id, doctor, document.id, observation_ids=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    evidence = _bridge(engine, doctor, run_id, tmp_path)
    assert evidence.comparisons[0].comparable is False
    assert evidence.comparisons[0].incomparable_reason == "no_baseline"
    assert evidence.comparisons[0].delta is None


def test_f2_rejected_historical_row_is_excluded_not_accepted(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "bad-history")
    history = _observation(db, patient_id, day=12, value=70, validation="rejected")
    current = _observation(db, patient_id, day=13, value=76)
    run_id = _start(db, patient_id, doctor, document.id, observation_ids=(current.id,))
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    evidence = _bridge(engine, doctor, run_id, tmp_path)
    assert any(
        e.observation_id == history.id and e.reason_code == "validation_rejected"
        for e in evidence.history_exclusions
    )
    assert evidence.comparisons[0].baseline_observation_id != history.id


def test_f2_more_than_six_current_is_explicit_denial(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "over-cap")
    # Seven distinct synthetic check-ins are legitimate F0 selections (max 20)
    # but cannot silently become six F2 'current' comparisons.
    selected_ids = []
    for index in range(7):
        row = Observation(
            patient_id=patient_id,
            measure_type="heart_rate",
            value=70 + index,
            unit="bpm",
            measured_at=f"2026-11-13T{index + 1:02d}:00:00Z",
            source="patient_checkin",
            validation="ok",
            trust_level="self_reported_validated",
            created_at=AT,
        )
        db.add(row)
        db.flush()
        selected_ids.append(row.id)
    db.commit()
    run_id = _start(
        db, patient_id, doctor, document.id, observation_ids=tuple(selected_ids)
    )
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    with pytest.raises(ApiError):
        _bridge(engine, doctor, run_id, tmp_path)


def test_f2_document_only_verified_unit_never_becomes_observation(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "document-only")
    fact = ExtractedFact(
        document_id=document.id,
        patient_id=patient_id,
        field_name="reference_text",
        raw_text="Synthetic reference printed in g/dL",
        normalized_value="5",
        unit="g/dL",
        page_index=0,
        char_start=0,
        char_end=8,
        verification_status="verified",
        created_at=AT,
    )
    db.add(fact)
    db.flush()
    db.add(
        FactVerification(
            fact_id=fact.id,
            decision="verified",
            verified_by_user_id=doctor.user_id,
            decided_at=AT,
        )
    )
    db.commit()
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    result = _bridge(engine, doctor, run_id, tmp_path)
    assert any(item.fact_id == fact.id and item.unit == "g/dL" for item in result.verified_facts)
    assert result.selected_observations == ()


def test_f2_does_not_accept_untrusted_role_or_in_transaction_session(
    scoped, engine, tmp_path
):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "role")
    run_id = _start(db, patient_id, doctor, document.id)
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
        _bridge(engine, wrong, run_id, tmp_path)
    with Session(engine) as new_db:
        new_db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id)).first()
        with pytest.raises(ApiError):
            build_run_evaluable_review_evidence(
                new_db,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
            )


def test_f2_caller_cannot_supply_clearance_or_baseline_override(
    scoped, engine, tmp_path
):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "caller")
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    with Session(engine) as fresh:
        with pytest.raises(TypeError):
            build_run_evaluable_review_evidence(
                fresh,
                principal=doctor,
                run_id=run_id,
                validation_clock=CLOCK,
                upload_root=str(tmp_path),
                blocking_fact_count=0,
            )


def test_f2_frozen_evidence_cannot_become_graph_token(scoped, engine, tmp_path):
    db, patient_id, doctor = scoped
    document = _doc(db, patient_id, tmp_path, "frozen")
    run_id = _start(db, patient_id, doctor, document.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    envelope = _bridge(engine, doctor, run_id, tmp_path)
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        envelope.runtime_evaluable = True
    with pytest.raises(FrozenInstanceError):
        envelope.policy_status = "approved"
    assert not envelope.rules_executed
