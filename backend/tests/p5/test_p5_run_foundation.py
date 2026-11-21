"""P5-F0 owner-ratified CH-01 foundation, with no workflow execution.

Every test uses migrated disposable SQLite and synthetic rows. These tests
exercise app-DB identity, immutable selections, doctor scope and audit;
they do NOT claim a real VI gate, LLM, DR rule or clinical validity.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from alembic import command
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import DatabaseError, IntegrityError
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
    RunSelectedDocument,
    RunSelectedObservation,
    RunSourceOmission,
    User,
    UserSession,
    VerificationIssue,
    WorkflowRun,
)
from app.services.p4_recovery_selection_candidate import CandidateDoctorOmission
from app.services.p5_run_foundation import create_run_foundation
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
AT = "2026-11-04T08:00:00Z"
SEED_PASSWORD = "synthetic-p5-f0-only-seed"
REASON = "selected_separate_recovery_source"


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(session, password=SEED_PASSWORD, now=CLOCK, iterations=1000)
        session.commit()
        yield session


def _patient(db: Session, reference: str = "DEMO-A-001") -> Patient:
    return db.execute(
        select(Patient).where(Patient.external_ref == reference)
    ).scalar_one()


def _doctor(db: Session, username: str = "demo_doctor", suffix: int = 1) -> Principal:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    session_id = f"dddddddd-dddd-4ddd-8ddd-{suffix:012d}"
    if db.get(UserSession, session_id) is None:
        db.add(UserSession(
            id=session_id,
            user_id=user.id,
            token_sha256=sha256(f"p5-f0-synthetic-{suffix}".encode()).hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        ))
        db.commit()
    return Principal(
        user_id=user.id, username=user.username, display_name=user.display_name,
        role=Role(user.role), patient_id=user.patient_id, session_id=session_id,
    )


def _document(
    db: Session, owner: Patient, label: str, *, parent: Document | None = None,
    terminal: bool = False,
) -> Document:
    doc = Document(
        patient_id=owner.id,
        uploaded_by_user_id=owner.assigned_doctor_id,
        original_filename=f"{label}-synthetic.pdf",
        stored_path=f"{label}-dummy.pdf",
        mime_type="application/pdf",
        sha256=sha256(label.encode()).hexdigest(),
        size_bytes=1,
        extraction_status="failed" if terminal else "verified",
        failure_code="measurement_rejected" if terminal else None,
        document_patient_ref=owner.external_ref,
        uploaded_at=AT,
        recovered_from_document_id=parent.id if parent is not None else None,
    )
    db.add(doc)
    db.flush()
    fact = ExtractedFact(
        document_id=doc.id, patient_id=owner.id,
        field_name="value", raw_text="105", normalized_value="105",
        unit="mg/dL", page_index=0, char_start=0, char_end=3,
        verification_status="rejected" if terminal else "verified",
        created_at=AT,
    )
    db.add(fact)
    db.flush()
    db.add(FactVerification(
        fact_id=fact.id, decision="rejected" if terminal else "verified",
        verified_by_user_id=owner.assigned_doctor_id, decided_at=AT,
    ))
    if terminal:
        db.add(VerificationIssue(
            patient_id=owner.id, document_id=doc.id,
            issue_type="VI-002", reason_code="fact_unverified",
            fact_ids=f'["{fact.id}"]', blocking=1,
            message="Synthetic source rejected.", state="open", created_at=AT,
        ))
    db.commit()
    return doc


def _start(
    db: Session,
    patient: Patient, doctor: Principal, document_ids: tuple[str, ...],
    observation_ids: tuple[str, ...] = (),
    omissions: tuple[CandidateDoctorOmission, ...] = (),
    request_id: str = "f0-start-001",
):
    return create_run_foundation(
        db, principal=doctor, patient_id=patient.id,
        document_ids=document_ids, observation_ids=observation_ids,
        omissions=omissions, client_request_id=request_id, as_of_utc=CLOCK,
    )


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_run_foundation_stores_real_identity_scoped_manifest_and_audit(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "standalone")
    observation = db.execute(
        select(Observation).where(Observation.patient_id == owner.id)
    ).scalars().first()
    assert observation is not None

    result = _start(db, owner, doctor, (doc.id,), (observation.id,))
    db.commit()
    assert result.thread_id == result.run_id
    assert result.status == "queued"
    assert result.run_gate_status == "unavailable"
    assert result.run_gate_completed is False
    assert result.runtime_evaluable is False
    assert not result.replayed
    with pytest.raises(FrozenInstanceError):
        result.run_gate_completed = True
    run = db.get(WorkflowRun, result.run_id)
    assert run is not None
    assert run.patient_id == owner.id
    assert run.doctor_id == doctor.user_id
    assert run.mapping_version == "map-1.0.0"
    assert run.policy_version == "demo-policy-1.1.0"
    assert run.as_of_utc == "2026-11-14T12:00:00Z"
    selected_doc = db.execute(select(RunSelectedDocument)).scalar_one()
    selected_obs = db.execute(select(RunSelectedObservation)).scalar_one()
    assert selected_doc.source_sha256 == doc.sha256
    assert selected_obs.observation_id == observation.id
    assert selected_obs.trust_level == observation.trust_level
    assert _count(db, AuditEvent) >= 1
    assert any(
        event.event_type == "workflow.run.started" and event.workflow_run_id == result.run_id
        for event in db.execute(select(AuditEvent)).scalars()
    )


def test_identical_request_replays_same_run_without_duplicate_rows(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "replay")
    first = _start(db, owner, doctor, (doc.id,))
    db.commit()
    second = _start(db, owner, doctor, (doc.id,))
    db.commit()
    assert second.run_id == first.run_id and second.replayed is True
    assert _count(db, WorkflowRun) == 1
    assert _count(db, RunSelectedDocument) == 1
    assert sum(
        event.event_type == "workflow.run.started"
        for event in db.execute(select(AuditEvent)).scalars()
    ) == 1


def test_recovered_selection_is_durable_but_does_not_resolve_old_vi(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    original = _document(db, owner, "failed-original", terminal=True)
    recovered = _document(db, owner, "separate-recovery", parent=original)
    omission = CandidateDoctorOmission(
        terminal_document_id=original.id, reason_code=REASON
    )
    result = _start(db, owner, doctor, (recovered.id,), omissions=(omission,))
    db.commit()
    stored = db.execute(select(RunSourceOmission)).scalar_one()
    assert stored.document_id == original.id
    assert stored.doctor_id == doctor.user_id
    assert stored.workflow_run_id == result.run_id
    assert db.get(VerificationIssue, stored.vi002_issue_id).state == "open"
    assert db.get(Document, original.id).extraction_status == "failed"
    assert result.run_gate_completed is False
    assert result.omission_document_ids == (original.id,)


@pytest.mark.parametrize("selection", ["original", "both", "no_omission"])
def test_terminal_original_and_unapproved_omissions_never_start_run(
    db: Session, selection: str
):
    owner, doctor = _patient(db), _doctor(db)
    original = _document(db, owner, "blocked-original", terminal=True)
    recovered = _document(db, owner, "blocked-recovery", parent=original)
    docs = (
        (original.id,) if selection == "original"
        else (original.id, recovered.id) if selection == "both"
        else (recovered.id,)
    )
    with pytest.raises(ApiError):
        _start(db, owner, doctor, docs)
    assert _count(db, WorkflowRun) == 0


@pytest.mark.parametrize("username", ["demo_patient_a", "demo_doctor_unassigned", "demo_admin"])
def test_wrong_role_or_assignment_denied_without_writes(db: Session, username: str):
    owner = _patient(db)
    doc = _document(db, owner, f"scope-{username}")
    principal = _doctor(db, username, suffix=2)
    with pytest.raises(ApiError):
        _start(db, owner, principal, (doc.id,))
    assert _count(db, WorkflowRun) == 0


def test_cross_patient_document_denied(db: Session):
    doctor = _doctor(db)
    first, second = _patient(db), _patient(db, "DEMO-B-001")
    foreign = _document(db, second, "foreign")
    with pytest.raises(ApiError):
        _start(db, first, doctor, (foreign.id,))
    assert _count(db, WorkflowRun) == 0


def test_cross_patient_observation_denied(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "obs-scope")
    foreign_obs = db.execute(
        select(Observation).where(Observation.patient_id != owner.id)
    ).scalars().first()
    assert foreign_obs is not None
    with pytest.raises(ApiError):
        _start(db, owner, doctor, (doc.id,), (foreign_obs.id,))
    assert _count(db, WorkflowRun) == 0


@pytest.mark.parametrize("identifiers", ["duplicate", "oversize", "invalid_request_id"])
def test_invalid_selection_or_request_id_rejected(db: Session, identifiers: str):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, f"invalid-{identifiers}")
    if identifiers == "duplicate":
        call = lambda: _start(db, owner, doctor, (doc.id, doc.id))
    elif identifiers == "oversize":
        call = lambda: _start(db, owner, doctor, (doc.id,), ("x",) * 21)
    else:
        call = lambda: _start(db, owner, doctor, (doc.id,), request_id="bad request id")
    with pytest.raises(ApiError):
        call()
    assert _count(db, WorkflowRun) == 0


def test_dirty_session_fails_before_any_database_write(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "dirty")
    owner.display_name = "Unsaved synthetic value"
    with pytest.raises(ApiError):
        _start(db, owner, doctor, (doc.id,))
    assert _count(db, WorkflowRun) == 0
    db.rollback()


def test_selected_source_manifest_is_database_immutable(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "immutable")
    _start(db, owner, doctor, (doc.id,))
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE run_selected_document SET source_status='failed'"))
    db.rollback()
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM run_selected_document"))
    db.rollback()
    assert _count(db, RunSelectedDocument) == 1


def test_real_foreign_keys_enforced_for_manifest(db: Session):
    owner, doctor = _patient(db), _doctor(db)
    doc = _document(db, owner, "fk")
    _start(db, owner, doctor, (doc.id,))
    db.commit()
    with pytest.raises(IntegrityError):
        db.add(RunSelectedDocument(
            workflow_run_id="00000000-0000-4000-8000-000000000000",
            document_id=doc.id, source_sha256=doc.sha256,
            source_status="verified", created_at=AT,
        ))
        db.flush()
    db.rollback()


def test_p5_migration_is_additive_and_reversible_on_empty_schema(
    alembic_config, sqlite_url
):
    command.upgrade(alembic_config, "head")
    from app.db.session import create_db_engine

    engine = create_db_engine(sqlite_url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "workflow_run", "run_selected_document",
            "run_selected_observation", "run_source_omission"
        } <= tables
        assert any(
            fk["referred_table"] == "workflow_run"
            for fk in inspect(engine).get_foreign_keys("audit_event")
        )
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()

    command.downgrade(alembic_config, "0005_p3_ocr_provenance")
    engine = create_db_engine(sqlite_url)
    try:
        assert "workflow_run" not in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        engine.dispose()
    command.upgrade(alembic_config, "head")
