"""P4 R2-A/C-37A internal SQLite inspection: synthetic, never runtime eligible."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import ApiError
from app.core.policies import Principal
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    User,
    UserSession,
    VerificationIssue,
)
from app.services.p4_evidence_inspection import inspect_selected_evidence
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CREATED = "2026-11-04T08:00:00Z"
SYNTHETIC_TEST_CREDENTIAL = "r2a-synthetic-test-only-password"


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(session, password=SYNTHETIC_TEST_CREDENTIAL, now=CLOCK, iterations=1000)
        session.commit()
        yield session


def patient(db: Session, reference: str = "DEMO-A-001") -> Patient:
    return db.execute(select(Patient).where(Patient.external_ref == reference)).scalar_one()


def identity(db: Session, username: str = "demo_doctor", *, session_suffix: str = "1") -> Principal:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    token_sha = sha256(f"synthetic-session-{session_suffix}".encode()).hexdigest()
    session_id = f"bbbbbbbb-bbbb-4bbb-8bbb-{int(session_suffix):012d}"
    if db.get(UserSession, session_id) is None:
        db.add(
            UserSession(
                id=session_id,
                user_id=user.id,
                token_sha256=token_sha,
                created_at="2026-11-01T00:00:00Z",
                expires_at="2026-12-01T00:00:00Z",
            )
        )
        db.commit()
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=Role(user.role),
        patient_id=user.patient_id,
        session_id=session_id,
    )


def call(
    db: Session,
    current_ids: tuple[str, ...],
    *,
    document_ids: tuple[str, ...] = (),
    as_of_utc: datetime = CLOCK,
    principal: Principal | None = None,
    patient_id: str | None = None,
):
    return inspect_selected_evidence(
        db,
        principal=principal or identity(db),
        patient_id=patient_id or patient(db).id,
        document_ids=document_ids,
        current_observation_ids=current_ids,
        as_of_utc=as_of_utc,
        baseline_lookback_days=90,
    )


def selected_systolic(db: Session) -> Observation:
    return db.execute(
        select(Observation)
        .where(
            Observation.patient_id == patient(db).id,
            Observation.measure_type == "systolic_bp",
        )
        .order_by(Observation.measured_at.desc())
        .limit(1)
    ).scalar_one()


def doc_with_fact(db: Session, *, status: str = "verified", decision: bool = True):
    owner = patient(db)
    user = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    doc = Document(
        patient_id=owner.id,
        uploaded_by_user_id=user.id,
        original_filename="r2a-synthetic-document.pdf",
        stored_path="r2a-not-a-file.pdf",
        mime_type="application/pdf",
        sha256=sha256(b"r2a-synthetic").hexdigest(),
        size_bytes=1,
        extraction_status=status,
        document_patient_ref=owner.external_ref,
        uploaded_at=CREATED,
    )
    db.add(doc)
    db.flush()
    fact = ExtractedFact(
        document_id=doc.id,
        patient_id=owner.id,
        field_name="value",
        raw_text="130",
        normalized_value="130",
        unit="mmHg",
        page_index=0,
        char_start=0,
        char_end=3,
        verification_status="verified" if decision else "pending",
        created_at=CREATED,
    )
    db.add(fact)
    db.flush()
    if decision:
        db.add(
            FactVerification(
                fact_id=fact.id,
                decision="verified",
                verified_by_user_id=user.id,
                decided_at=CREATED,
            )
        )
    observation = Observation(
        patient_id=owner.id,
        measure_type="systolic_bp",
        value=130,
        unit="mmHg",
        measured_at="2026-11-03T09:00:00Z",
        source="verified_document",
        source_fact_id=fact.id,
        trust_level="doctor_verified",
        validation="ok",
        verified_by_user_id=user.id,
        verified_at=CREATED,
        created_at=CREATED,
        created_by_user_id=user.id,
    )
    db.add(observation)
    db.commit()
    return doc, fact, observation


def test_scoped_persisted_session_and_explicit_history(db: Session) -> None:
    current = selected_systolic(db)
    before = db.scalar(select(func.count()).select_from(Observation))
    result = call(db, (current.id,))
    assert result.run_gate_status == "unavailable"
    assert result.run_gate_completed is False
    assert result.runtime_evaluable is False
    assert result.policy_status == "unapproved"
    assert result.selected_document_preflight is None
    assert result.document_ids == ()
    assert result.current_observation_ids == (current.id,)
    assert len(result.comparison.comparisons) == 1
    assert result.comparison.comparisons[0].current_observation_id == current.id
    assert db.scalar(select(func.count()).select_from(Observation)) == before
    assert not db.new and not db.dirty and not db.deleted
    assert result == call(db, (current.id,))


def test_selected_verified_doc_and_mapped_source_keep_trust(db: Session) -> None:
    doc, _, observation = doc_with_fact(db)
    result = call(db, (observation.id,), document_ids=(doc.id,))
    assert result.selected_document_preflight is not None
    assert result.selected_document_preflight.candidate_documents_clear
    assert result.run_gate_completed is False
    assert result.comparison.comparisons[0].trust_basis in {"mixed", "doctor_verified"}
    assert not any(item.observation_id == observation.id for item in result.source_exclusions)


def test_pending_document_does_not_become_approved_run(db: Session) -> None:
    current = selected_systolic(db)
    doc, fact, observation = doc_with_fact(db, status="needs_verification", decision=False)
    result = call(db, (current.id,), document_ids=(doc.id,))
    assert result.selected_document_preflight is not None
    assert not result.selected_document_preflight.candidate_documents_clear
    assert result.run_gate_status == "unavailable"
    assert any(item.observation_id == observation.id for item in result.source_exclusions)
    assert any(item.reason == "verified_lineage_unavailable" for item in result.source_exclusions)
    with pytest.raises(ApiError) as denied:
        call(db, (observation.id,), document_ids=(doc.id,))
    assert denied.value.status_code == 400
    assert fact.verification_status == "pending"


def test_open_vi_issue_remains_visible_then_resolved_without_runtime_clearance(db: Session) -> None:
    current = selected_systolic(db)
    doc, fact, _ = doc_with_fact(db)
    issue = VerificationIssue(
        patient_id=patient(db).id,
        document_id=doc.id,
        issue_type="VI-002",
        reason_code="fact_unverified",
        fact_ids=f'["{fact.id}"]',
        blocking=1,
        message="1 extracted value(s) are not yet verified.",
        state="open",
        created_at=CREATED,
    )
    db.add(issue)
    db.commit()
    blocked = call(db, (current.id,), document_ids=(doc.id,))
    assert not blocked.selected_document_preflight.candidate_documents_clear
    assert [(i.issue_type, i.state) for i in blocked.selected_issue_states] == [("VI-002", "open")]
    issue.state = "resolved"
    db.commit()
    after = call(db, (current.id,), document_ids=(doc.id,))
    assert after.selected_document_preflight.candidate_documents_clear
    assert [(i.issue_type, i.state) for i in after.selected_issue_states] == [
        ("VI-002", "resolved")
    ]
    assert after.run_gate_completed is False


@pytest.mark.parametrize("user_name", ["demo_doctor_unassigned", "demo_patient_a", "demo_admin"])
def test_unassigned_non_doctor_and_admin_rejected(db: Session, user_name: str) -> None:
    row = selected_systolic(db)
    with pytest.raises(ApiError) as denied:
        call(db, (row.id,), principal=identity(db, user_name, session_suffix="3"))
    assert denied.value.status_code == 403


def test_no_session_expired_revoked_and_wrong_user_session_refused(db: Session) -> None:
    current = selected_systolic(db)
    p = identity(db)
    with pytest.raises(ApiError) as missing:
        call(
            db,
            (current.id,),
            principal=Principal(
                user_id=p.user_id,
                username=p.username,
                display_name=p.display_name,
                role=p.role,
                patient_id=p.patient_id,
                session_id="missing",
            ),
        )
    assert missing.value.status_code == 403
    session = db.get(UserSession, p.session_id)
    session.expires_at = "2026-11-12T00:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as expired:
        call(db, (current.id,), principal=p)
    assert expired.value.status_code == 403
    session.expires_at = "2026-12-01T00:00:00Z"
    session.revoked_at = CREATED
    db.commit()
    with pytest.raises(ApiError) as revoked:
        call(db, (current.id,), principal=p)
    assert revoked.value.status_code == 403


def test_missing_and_foreign_current_never_leak(db: Session) -> None:
    first = selected_systolic(db)
    other = (
        db.execute(
            select(Observation).where(Observation.patient_id == patient(db, "DEMO-B-001").id)
        )
        .scalars()
        .first()
    )
    assert other is not None
    for unknown in ("not-present", other.id):
        with pytest.raises(ApiError) as denied:
            call(db, (unknown,))
        assert denied.value.status_code == 404
    with pytest.raises(ApiError) as invalid:
        call(db, (first.id, first.id))
    assert invalid.value.status_code == 400


def test_missing_or_foreign_document_and_bad_document_selection(db: Session) -> None:
    first = selected_systolic(db)
    for unknown in ("not-present",):
        with pytest.raises(ApiError) as denied:
            call(db, (first.id,), document_ids=(unknown,))
        assert denied.value.status_code == 404
    doc, _, _ = doc_with_fact(db)
    with pytest.raises(ApiError) as duplicate:
        call(db, (first.id,), document_ids=(doc.id, doc.id))
    assert duplicate.value.status_code == 400


def test_uncommitted_changes_and_naive_clock_fail_closed(db: Session) -> None:
    current = selected_systolic(db)
    doctor = identity(db)
    owner_id = patient(db).id
    with pytest.raises(ApiError) as invalid:
        call(
            db,
            (current.id,),
            principal=doctor,
            patient_id=owner_id,
            as_of_utc=datetime(2026, 11, 14),
        )
    assert invalid.value.status_code == 400
    current.value = 555
    with pytest.raises(ApiError) as dirty:
        call(db, (current.id,), principal=doctor, patient_id=owner_id)
    assert dirty.value.status_code == 400
