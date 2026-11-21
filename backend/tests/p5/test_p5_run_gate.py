"""P5-F1 synthetic evidence-gate integration tests; never clinical verification."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import ApiError
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    RunGateBlocker,
    RunGateEvaluation,
    User,
    UserSession,
    VerificationIssue,
    WorkflowRun,
)
from app.services.p4_recovery_selection_candidate import CandidateDoctorOmission
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
AT = "2026-06-14T08:00:00Z"
REASON = "selected_separate_recovery_source"


@pytest.fixture()
def scoped(engine):
    with Session(engine) as db:
        seed_phrase = "-".join(("synthetic", "f1", "fixture", "only"))
        seed_demo_data(db, password=seed_phrase, now=CLOCK, iterations=1000)
        db.commit()
        patient = db.execute(
            select(Patient).where(Patient.external_ref == "DEMO-A-001")
        ).scalar_one()
        user = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        session = UserSession(
            id="a1111111-1111-4111-8111-111111111111",
            user_id=user.id,
            token_sha256=hashlib.sha256(b"f1-synthetic-session").hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
        db.add(session)
        db.commit()
        doctor = Principal(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=Role(user.role),
            patient_id=user.patient_id,
            session_id=session.id,
        )
        yield db, patient.id, doctor


def _doc(
    db: Session,
    patient_id: str,
    root: Path,
    label: str,
    *,
    parent: Document | None = None,
    rejected: bool = False,
) -> Document:
    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"F1 synthetic PDF fixture {label}".encode()
    name = f"synthetic-{label}.pdf"
    (root / name).write_bytes(raw)
    doc = Document(
        patient_id=patient_id,
        uploaded_by_user_id=patient.assigned_doctor_id,
        original_filename=name,
        stored_path=name,
        mime_type="application/pdf",
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        extraction_status="failed" if rejected else "verified",
        failure_code="measurement_rejected" if rejected else None,
        document_patient_ref=patient.external_ref,
        document_patient_refs=f'["{patient.external_ref}"]',
        uploaded_at=AT,
        recovered_from_document_id=parent.id if parent else None,
    )
    db.add(doc)
    db.flush()
    fields = (
        ("report_date", "2026-06-14", None),
        ("test_name", "glucose", None),
        ("value", "105", "mg/dL"),
        ("unit", "mg/dL", None),
    )
    for field, value, unit in fields:
        fact = ExtractedFact(
            document_id=doc.id,
            patient_id=patient_id,
            field_name=field,
            raw_text=value,
            normalized_value=value,
            unit=unit,
            page_index=0,
            char_start=0,
            char_end=len(value),
            verification_status="rejected" if rejected else "verified",
            created_at=AT,
        )
        db.add(fact)
        db.flush()
        db.add(
            FactVerification(
                fact_id=fact.id,
                decision="rejected" if rejected else "verified",
                verified_by_user_id=patient.assigned_doctor_id,
                decided_at=AT,
            )
        )
    if rejected:
        db.add(
            VerificationIssue(
                patient_id=patient_id,
                document_id=doc.id,
                issue_type="VI-002",
                reason_code="fact_unverified",
                fact_ids="[]",
                blocking=1,
                message="Synthetic source rejected.",
                state="open",
                created_at=AT,
            )
        )
    db.commit()
    return doc


def _start(
    db: Session,
    patient_id: str,
    doctor: Principal,
    document_id: str,
    *,
    omissions: tuple[CandidateDoctorOmission, ...] = (),
    observation_ids: tuple[str, ...] = (),
) -> str:
    started = create_run_foundation(
        db,
        principal=doctor,
        patient_id=patient_id,
        document_ids=(document_id,),
        observation_ids=observation_ids,
        omissions=omissions,
        client_request_id="f1-start-synthetic",
        as_of_utc=CLOCK,
    )
    db.commit()
    return started.run_id


def _gate(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return evaluate_run_verification_gate(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def test_run_gate_proceed_is_durable_but_not_runtime_evaluable(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "clear")
    run_id = _start(db, patient_id, doctor, doc.id)
    first = _gate(engine, doctor, run_id, tmp_path)
    assert first.decision == "proceed"
    assert first.issues == ()
    assert first.runtime_evaluable is False
    assert first.gate_evaluated is True
    assert first.replayed is False
    second = _gate(engine, doctor, run_id, tmp_path)
    assert second.decision == "proceed" and second.replayed
    assert second.input_fingerprint_sha256 == first.input_fingerprint_sha256
    db.expire_all()
    assert db.get(WorkflowRun, run_id).status == "queued"
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 1
    assert db.scalar(select(func.count()).select_from(RunGateBlocker)) == 0


def test_missing_actual_source_is_never_a_pass(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "missing")
    run_id = _start(db, patient_id, doctor, doc.id)
    (tmp_path / doc.stored_path).unlink()
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "unavailable"
    assert result.unavailable_reason == "source_bytes_unavailable"
    assert result.runtime_evaluable is False


def test_selected_unverified_fact_blocks_even_if_original_run_queued(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "pending")
    run_id = _start(db, patient_id, doctor, doc.id)
    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == doc.id, ExtractedFact.field_name == "value"
        )
    ).scalar_one()
    fact.verification_status = "pending"
    db.commit()
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "halt"
    assert any(issue.issue_type == "VI-002" for issue in result.issues)
    assert db.get(WorkflowRun, run_id).status == "queued"


def test_source_byte_drift_invalidates_old_proceed_receipt(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "source-drift")
    run_id = _start(db, patient_id, doctor, doc.id)
    assert _gate(engine, doctor, run_id, tmp_path).decision == "proceed"
    (tmp_path / doc.stored_path).write_bytes(b"tampered")
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "unavailable"
    assert result.input_fingerprint_sha256 != ""
    assert not result.replayed


def test_historical_vi002_stays_open_with_audited_recovery(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    original = _doc(db, patient_id, tmp_path, "terminal", rejected=True)
    recovered = _doc(db, patient_id, tmp_path, "recovered", parent=original)
    omission = CandidateDoctorOmission(terminal_document_id=original.id, reason_code=REASON)
    run_id = _start(db, patient_id, doctor, recovered.id, omissions=(omission,))
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "proceed"
    historical = db.execute(
        select(VerificationIssue).where(VerificationIssue.document_id == original.id)
    ).scalar_one()
    assert historical.state == "open"
    assert result.historical_excluded_vi002_ids == (historical.id,)


def test_selected_self_reported_observation_keeps_its_label(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "checkin")
    obs = (
        db.execute(select(Observation).where(Observation.patient_id == patient_id))
        .scalars()
        .first()
    )
    assert obs is not None
    run_id = _start(db, patient_id, doctor, doc.id, observation_ids=(obs.id,))
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision in {"proceed", "halt"}
    assert result.unavailable_reason is None
    db.expire_all()
    assert db.get(Observation, obs.id).trust_level == obs.trust_level


def test_revoked_stored_doctor_session_denies_without_gate_rows(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "revocation")
    run_id = _start(db, patient_id, doctor, doc.id)
    session = db.get(UserSession, doctor.session_id)
    session.revoked_at = "2026-11-14T12:00:00Z"
    db.commit()
    with pytest.raises(ApiError):
        _gate(engine, doctor, run_id, tmp_path)
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 0


def test_gate_tables_and_triggers_are_enforced_by_sqlite(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "immutable-gate")
    run_id = _start(db, patient_id, doctor, doc.id)
    _gate(engine, doctor, run_id, tmp_path)
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM run_gate_evaluation"))
    db.rollback()
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 1


def test_p5_f1_schema_empty_downgrade_and_reupgrade(alembic_config, sqlite_url):
    from app.db.session import create_db_engine

    command.upgrade(alembic_config, "head")
    eng = create_db_engine(sqlite_url)
    try:
        tables = set(inspect(eng).get_table_names())
        assert {"run_gate_evaluation", "run_gate_blocker"} <= tables
        assert any(
            fk["referred_table"] == "workflow_run"
            for fk in inspect(eng).get_foreign_keys("run_gate_evaluation")
        )
    finally:
        eng.dispose()
    command.downgrade(alembic_config, "0006_p5_run_foundation")
    eng = create_db_engine(sqlite_url)
    try:
        assert "run_gate_evaluation" not in inspect(eng).get_table_names()
    finally:
        eng.dispose()
    command.upgrade(alembic_config, "head")


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ("missing_unit", "VI-001"),
        ("missing_date", "VI-003"),
        ("wrong_patient_reference", "VI-004"),
        ("low_confidence", "VI-005"),
    ],
)
def test_vi_001_003_004_005_recomputed_from_selected_source(
    scoped, tmp_path, engine, changed: str, expected: str
):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, f"vi-{changed}")
    run_id = _start(db, patient_id, doctor, doc.id)
    if changed == "wrong_patient_reference":
        doc.document_patient_ref = "DEMO-B-001"
    else:
        field = "report_date" if changed == "missing_date" else "value"
        fact = db.execute(
            select(ExtractedFact).where(
                ExtractedFact.document_id == doc.id, ExtractedFact.field_name == field
            )
        ).scalar_one()
        if changed == "missing_unit":
            fact.unit = None
        elif changed == "missing_date":
            fact.normalized_value = None
        else:
            fact.quality_flags = '["low_confidence"]'
    db.commit()
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "halt"
    assert expected in {issue.issue_type for issue in result.issues}
    assert not result.runtime_evaluable


def _conflicting_checkin(db: Session, patient_id: str):
    db.add(
        Observation(
            patient_id=patient_id,
            measure_type="glucose",
            value=106,
            unit="mg/dL",
            measured_at="2026-06-14T00:00:00Z",
            source="seed_fixture",
            validation="ok",
            trust_level="self_reported_validated",
            created_at=AT,
        )
    )
    db.commit()


def test_vi006_conflict_recomputed_against_current_stored_history(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "vi-conflict")
    run_id = _start(db, patient_id, doctor, doc.id)
    _conflicting_checkin(db, patient_id)
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "halt"
    assert any(issue.issue_type == "VI-006" for issue in result.issues)


def test_new_history_conflict_invalidates_prior_matching_proceed(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "new-history-conflict")
    run_id = _start(db, patient_id, doctor, doc.id)
    prior = _gate(engine, doctor, run_id, tmp_path)
    assert prior.decision == "proceed"
    _conflicting_checkin(db, patient_id)
    later = _gate(engine, doctor, run_id, tmp_path)
    assert later.decision == "halt"
    assert not later.replayed
    assert later.input_fingerprint_sha256 != prior.input_fingerprint_sha256


def test_verified_multimeasurement_document_is_not_promoted(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "multimeasurement")
    run_id = _start(db, patient_id, doctor, doc.id)
    fact = ExtractedFact(
        document_id=doc.id,
        patient_id=patient_id,
        field_name="value",
        raw_text="110",
        normalized_value="110",
        unit="mg/dL",
        page_index=0,
        char_start=0,
        char_end=3,
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
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "halt"
    assert any(
        issue.issue_type == "VI-002" and issue.reason_code == "multi_measurement_document"
        for issue in result.issues
    )


def test_mutated_selected_observation_is_not_silently_dropped(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "rejected-observation")
    obs = (
        db.execute(select(Observation).where(Observation.patient_id == patient_id))
        .scalars()
        .first()
    )
    assert obs is not None
    run_id = _start(db, patient_id, doctor, doc.id, observation_ids=(obs.id,))
    obs.validation = "rejected"
    db.commit()
    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "unavailable"
    assert result.unavailable_reason == "selected_observation_inadmissible"


def test_reassigned_patient_denied_before_any_gate_evidence(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "reassignment")
    run_id = _start(db, patient_id, doctor, doc.id)
    patient = db.get(Patient, patient_id)
    other = db.execute(select(User).where(User.username == "demo_doctor_unassigned")).scalar_one()
    patient.assigned_doctor_id = other.id
    db.commit()
    with pytest.raises(ApiError):
        _gate(engine, doctor, run_id, tmp_path)
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 0


def test_gate_evidence_update_is_rejected_at_database_layer(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "gate-update")
    run_id = _start(db, patient_id, doctor, doc.id)
    _gate(engine, doctor, run_id, tmp_path)
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE run_gate_evaluation SET decision='halt'"))
    db.rollback()
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 1


def test_alembic_smoke_retains_all_historical_states(alembic_config, sqlite_url: str):
    """The exact 0007 smoke, 0006 F0 and P3/P2/P1 states are all enforced."""
    smoke = REPO_ROOT / "scripts" / "python" / "check_alembic_smoke.py"
    database = sqlite_url.removeprefix("sqlite:///")
    revisions = [
        ("head", "head"),
        ("0006_p5_run_foundation", "p5_f0"),
        ("0005_p3_ocr_provenance", "p3_stage1"),
        ("0004_p3_rejection_recovery", "p3_recovery"),
        ("0003_p3_documents", "p3"),
        ("0002_p2_patient_domain", "p2"),
        ("0001_p1_baseline", "p1"),
        ("base", "base"),
    ]
    command.upgrade(alembic_config, "head")
    for revision, state in revisions:
        if revision != "head":
            command.downgrade(alembic_config, revision)
        completed = subprocess.run(
            [sys.executable, str(smoke), database, "--state", state],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        assert completed.returncode == 0, (
            state,
            completed.stdout[-1500:],
            completed.stderr[-1500:],
        )


def test_provenance_raw_text_change_invalidates_previous_gate_fingerprint(
    scoped, tmp_path, engine
):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "raw-source-change")
    run_id = _start(db, patient_id, doctor, doc.id)
    earlier = _gate(engine, doctor, run_id, tmp_path)
    assert earlier.decision == "proceed"

    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == doc.id,
            ExtractedFact.field_name == "value",
        )
    ).scalar_one()
    fact.raw_text = "106"
    db.commit()

    later = _gate(engine, doctor, run_id, tmp_path)
    assert later.input_fingerprint_sha256 != earlier.input_fingerprint_sha256
    assert not later.replayed
    assert not later.runtime_evaluable


def test_unknown_quality_flag_fails_closed(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "invalid-quality-flag")
    run_id = _start(db, patient_id, doctor, doc.id)
    fact = db.execute(
        select(ExtractedFact).where(
            ExtractedFact.document_id == doc.id,
            ExtractedFact.field_name == "value",
        )
    ).scalar_one()
    fact.quality_flags = '["unsupported_future_quality_flag"]'
    db.commit()

    result = _gate(engine, doctor, run_id, tmp_path)
    assert result.decision == "unavailable"
    assert result.unavailable_reason == "invalid_quality_flags"
    assert not result.runtime_evaluable


def test_replay_rejects_forged_additional_gate_blocker(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "forged-gate-blocker")
    run_id = _start(db, patient_id, doctor, doc.id)
    earlier = _gate(engine, doctor, run_id, tmp_path)
    assert earlier.decision == "proceed"

    evaluation = db.execute(
        select(RunGateEvaluation).where(RunGateEvaluation.workflow_run_id == run_id)
    ).scalar_one()
    db.add(
        RunGateBlocker(
            gate_evaluation_id=evaluation.id,
            issue_type="VI-002",
            reason_code="fact_unverified",
            document_id=doc.id,
            fact_ids="[]",
        )
    )
    db.commit()

    with pytest.raises(ApiError):
        _gate(engine, doctor, run_id, tmp_path)
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 1


def test_concurrent_gate_attempts_create_one_durable_evaluation(scoped, tmp_path, engine):
    db, patient_id, doctor = scoped
    doc = _doc(db, patient_id, tmp_path, "concurrent-gate")
    run_id = _start(db, patient_id, doctor, doc.id)
    barrier = Barrier(2, timeout=10)

    def evaluate_once():
        barrier.wait()
        return _gate(engine, doctor, run_id, tmp_path)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(evaluate_once)
        second_future = pool.submit(evaluate_once)
        first, second = first_future.result(), second_future.result()

    assert [first.decision, second.decision] == ["proceed", "proceed"]
    assert sorted([first.replayed, second.replayed]) == [False, True]
    assert first.input_fingerprint_sha256 == second.input_fingerprint_sha256
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(RunGateEvaluation)) == 1
