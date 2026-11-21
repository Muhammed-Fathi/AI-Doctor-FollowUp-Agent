"""P4 R21-S1 migrated SQLite: offline future selection, never a real run-gate.

Synthetic only. Do not treat an in-memory omission proposal as an audited
doctor decision, or a patient recovery link as proof of source equivalence.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
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
    Patient,
    User,
    UserSession,
    VerificationIssue,
)
from app.services.p4_recovery_selection_candidate import (
    CandidateDoctorOmission,
    inspect_offline_recovery_selection,
)
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CREATED = "2026-11-04T08:00:00Z"
SYNTHETIC_SEED_CREDENTIAL = "r21s1-offline-only-fixture-value"
REASON = "selected_separate_recovery_source"


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(session, password=SYNTHETIC_SEED_CREDENTIAL, now=CLOCK, iterations=1000)
        session.commit()
        yield session


def patient(db: Session, reference: str = "DEMO-A-001") -> Patient:
    return db.execute(select(Patient).where(Patient.external_ref == reference)).scalar_one()


def identity(db: Session, username: str = "demo_doctor", *, suffix: int = 1) -> Principal:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    session_id = f"aaaaaaaa-aaaa-4aaa-8aaa-{suffix:012d}"
    if db.get(UserSession, session_id) is None:
        db.add(
            UserSession(
                id=session_id,
                user_id=user.id,
                token_sha256=sha256(f"r21-synthetic-session-{suffix}".encode()).hexdigest(),
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


@pytest.fixture()
def context(db: Session):
    owner = patient(db)
    principal = identity(db)
    return owner, principal


def report(
    db: Session,
    owner: Patient,
    label: str,
    *,
    parent: Document | None = None,
    terminal: bool = False,
    status: str = "verified",
    with_decision: bool = True,
    vi_state: str | None = "open",
    document_ref: str | None = None,
) -> Document:
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    doc = Document(
        patient_id=owner.id,
        uploaded_by_user_id=doctor.id,
        original_filename=f"{label}-synthetic-only.pdf",
        stored_path=f"{label}-not-a-real-file.pdf",
        mime_type="application/pdf",
        sha256=sha256(label.encode()).hexdigest(),
        size_bytes=1,
        extraction_status="failed" if terminal else status,
        failure_code="measurement_rejected" if terminal else None,
        document_patient_ref=document_ref if document_ref is not None else owner.external_ref,
        uploaded_at=CREATED,
        recovered_from_document_id=parent.id if parent is not None else None,
    )
    db.add(doc)
    db.flush()
    fact = ExtractedFact(
        document_id=doc.id,
        patient_id=owner.id,
        field_name="value",
        raw_text="105",
        normalized_value="105",
        unit="mg/dL",
        page_index=0,
        char_start=0,
        char_end=3,
        verification_status="rejected" if terminal else "verified" if with_decision else "pending",
        created_at=CREATED,
    )
    db.add(fact)
    db.flush()
    if with_decision:
        db.add(
            FactVerification(
                fact_id=fact.id,
                decision="rejected" if terminal else "verified",
                verified_by_user_id=doctor.id,
                decided_at=CREATED,
            )
        )
    if terminal and vi_state is not None:
        db.add(
            VerificationIssue(
                patient_id=owner.id,
                document_id=doc.id,
                issue_type="VI-002",
                reason_code="fact_unverified",
                fact_ids=f'["{fact.id}"]',
                blocking=1,
                message="1 extracted value(s) are not yet verified.",
                state=vi_state,
                created_at=CREATED,
            )
        )
    db.commit()
    return doc


def omission(doc: Document, reason: str = REASON) -> CandidateDoctorOmission:
    return CandidateDoctorOmission(terminal_document_id=doc.id, reason_code=reason)


def inspect(
    db: Session,
    owner: Patient,
    principal: Principal,
    selected: tuple[Document, ...],
    *,
    omissions: tuple[CandidateDoctorOmission, ...] = (),
):
    return inspect_offline_recovery_selection(
        db,
        principal=principal,
        patient_id=owner.id,
        selected_document_ids=tuple(doc.id for doc in selected),
        omission_proposals=omissions,
        as_of_utc=CLOCK,
    )


def reasons(result) -> set[str]:
    return {item.reason_code for item in result.blockers}


def test_recovery_only_with_doctor_proposal_is_still_not_a_real_run_gate(
    db: Session, context
) -> None:
    owner, doctor = context
    original = report(db, owner, "original", terminal=True)
    recovered = report(db, owner, "recovered", parent=original)
    issue_before = db.execute(
        select(VerificationIssue).where(VerificationIssue.document_id == original.id)
    ).scalar_one()
    before = db.scalar(select(func.count()).select_from(Document))
    a = inspect(db, owner, doctor, (recovered,), omissions=(omission(original),))
    b = inspect(db, owner, doctor, (recovered,), omissions=(omission(original),))
    assert a == b
    assert a.offline_selection_shape_valid is True
    assert a.blockers == ()
    assert a.historical_rejected_sources[0].document_id == original.id
    assert a.historical_rejected_sources[0].vi002_state == "open"
    assert a.doctor_selection_audited is False
    assert a.run_gate_completed is False
    assert a.runtime_evaluable is False
    assert a.run_gate_status == "unavailable"
    assert db.scalar(select(func.count()).select_from(Document)) == before
    assert issue_before.state == "open"
    assert db.get(Document, original.id).extraction_status == "failed"
    assert not db.new and not db.dirty and not db.deleted
    with pytest.raises(FrozenInstanceError):
        a.run_gate_completed = True


@pytest.mark.parametrize("choice", ["original", "both"])
def test_selected_failed_original_always_halts_even_with_recovery(
    db: Session, context, choice: str
) -> None:
    owner, doctor = context
    original = report(db, owner, "terminal-original", terminal=True)
    recovered = report(db, owner, "replacement", parent=original)
    chosen = (original,) if choice == "original" else (original, recovered)
    result = inspect(db, owner, doctor, chosen)
    assert not result.offline_selection_shape_valid
    assert "selected_terminal_rejected_source" in reasons(result)
    assert result.run_gate_completed is False
    assert (
        db.execute(
            select(VerificationIssue.state).where(VerificationIssue.document_id == original.id)
        ).scalar_one()
        == "open"
    )


def test_recovery_without_doctor_proposal_never_silently_excludes_original(
    db: Session, context
) -> None:
    owner, doctor = context
    original = report(db, owner, "rejected-a", terminal=True)
    new = report(db, owner, "new-a", parent=original)
    result = inspect(db, owner, doctor, (new,))
    assert not result.offline_selection_shape_valid
    assert "missing_doctor_omission_proposal" in reasons(result)
    assert result.historical_rejected_sources[0].vi002_state == "open"


@pytest.mark.parametrize("state", [None, "resolved", "superseded"])
def test_recovery_does_not_clear_or_invent_historical_vi002(
    db: Session, context, state: str | None
) -> None:
    owner, doctor = context
    original = report(db, owner, "rejected-no-vi", terminal=True, vi_state=state)
    new = report(db, owner, "new-no-vi", parent=original)
    outcome = inspect(db, owner, doctor, (new,), omissions=(omission(original),))
    assert not outcome.offline_selection_shape_valid
    assert "historical_vi002_not_open" in reasons(outcome)
    assert outcome.historical_rejected_sources[0].vi002_state == (state or "missing")


@pytest.mark.parametrize("status", ["needs_verification", "failed"])
def test_recovered_document_not_independently_verified_halts(
    db: Session, context, status: str
) -> None:
    owner, doctor = context
    original = report(db, owner, "rejected-pending", terminal=True)
    new = report(db, owner, f"recovered-{status}", parent=original, status=status)
    result = inspect(db, owner, doctor, (new,), omissions=(omission(original),))
    assert not result.offline_selection_shape_valid
    assert "document_not_verified" in reasons(result)
    assert result.run_gate_completed is False


def test_recovered_document_without_fact_decision_is_not_verified(db: Session, context) -> None:
    owner, doctor = context
    original = report(db, owner, "orig-no-decision", terminal=True)
    new = report(db, owner, "recovery-no-decision", parent=original, with_decision=False)
    outcome = inspect(db, owner, doctor, (new,), omissions=(omission(original),))
    assert "active_fact_unverified" in reasons(outcome)
    assert not outcome.offline_selection_shape_valid


def test_identity_mismatch_blocks_even_when_recovery_link_valid(db: Session, context) -> None:
    owner, doctor = context
    original = report(db, owner, "orig-identity", terminal=True)
    new = report(db, owner, "recovery-identity", parent=original, document_ref="DEMO-B-001")
    outcome = inspect(db, owner, doctor, (new,), omissions=(omission(original),))
    assert "document_identity_unresolved" in reasons(outcome)
    assert not outcome.offline_selection_shape_valid


def test_chained_recovery_requires_proposal_for_every_terminal_ancestor(
    db: Session, context
) -> None:
    owner, doctor = context
    first = report(db, owner, "first-terminal", terminal=True)
    second = report(db, owner, "second-terminal", parent=first, terminal=True)
    third = report(db, owner, "third-recovery", parent=second)
    partial = inspect(db, owner, doctor, (third,), omissions=(omission(first),))
    assert not partial.offline_selection_shape_valid
    assert "missing_doctor_omission_proposal" in reasons(partial)
    complete = inspect(db, owner, doctor, (third,), omissions=(omission(first), omission(second)))
    assert complete.offline_selection_shape_valid
    assert len(complete.historical_rejected_sources) == 2
    assert {item.vi002_state for item in complete.historical_rejected_sources} == {"open"}
    assert complete.doctor_selection_audited is False
    assert complete.run_gate_completed is False


def test_extra_or_unrelated_omission_cannot_be_a_legal_future_selection(
    db: Session, context
) -> None:
    owner, doctor = context
    original = report(db, owner, "orig-related", terminal=True)
    other = report(db, owner, "orig-unrelated", terminal=True)
    recovered = report(db, owner, "related-recovery", parent=original)
    outcome = inspect(
        db,
        owner,
        doctor,
        (recovered,),
        omissions=(omission(original), omission(other)),
    )
    assert not outcome.offline_selection_shape_valid
    assert "omission_not_a_selected_recovery_ancestor" in reasons(outcome)


def test_no_selected_sources_does_not_create_fake_run_baseline(db: Session, context) -> None:
    owner, doctor = context
    result = inspect(db, owner, doctor, ())
    assert not result.offline_selection_shape_valid
    assert reasons(result) == {"empty_selected_source_set"}
    assert result.run_gate_status == "unavailable"


def test_declared_recovery_of_verified_parent_halts(db: Session, context) -> None:
    owner, doctor = context
    original = report(db, owner, "parent-verified")
    child = report(db, owner, "child-invalid-parent", parent=original)
    outcome = inspect(db, owner, doctor, (child,), omissions=(omission(original),))
    assert "invalid_recovery_parent_status" in reasons(outcome)
    assert "historical_vi002_not_open" in reasons(outcome)
    assert not outcome.offline_selection_shape_valid


def test_cross_patient_selected_and_cross_patient_recovery_ancestor_are_unavailable(
    db: Session, context
) -> None:
    owner, doctor = context
    foreign = report(db, patient(db, "DEMO-B-001"), "foreign-terminal", terminal=True)
    with pytest.raises(ApiError) as selected:
        inspect(db, owner, doctor, (foreign,))
    assert selected.value.status_code == 404
    parent = report(db, owner, "same-patient-parent", terminal=True)
    child = report(db, owner, "same-patient-recovery", parent=parent)
    child.recovered_from_document_id = foreign.id
    db.commit()
    with pytest.raises(ApiError) as ancestor:
        inspect(db, owner, doctor, (child,), omissions=(omission(foreign),))
    assert ancestor.value.status_code == 404


def test_cycle_is_detected_without_infinite_traversal(db: Session, context) -> None:
    owner, doctor = context
    first = report(db, owner, "cycle-a", terminal=True)
    second = report(db, owner, "cycle-b", parent=first)
    first.recovered_from_document_id = second.id
    db.commit()
    result = inspect(db, owner, doctor, (second,), omissions=(omission(first),))
    assert not result.offline_selection_shape_valid
    assert "recovery_lineage_cycle" in reasons(result)


@pytest.mark.parametrize("name", ["demo_doctor_unassigned", "demo_patient_a", "demo_admin"])
def test_unassigned_or_non_doctor_principal_refused(db: Session, context, name: str) -> None:
    owner, _ = context
    original = report(db, owner, f"auth-{name}", terminal=True)
    replacement = report(db, owner, f"replacement-{name}", parent=original)
    with pytest.raises(ApiError) as denied:
        inspect(db, owner, identity(db, name, suffix=3), (replacement,))
    assert denied.value.status_code == 403


def test_expired_or_revoked_session_rejected(db: Session, context) -> None:
    owner, doctor = context
    doc = report(db, owner, "auth-source")
    session = db.get(UserSession, doctor.session_id)
    session.expires_at = "2026-11-13T00:00:00Z"
    db.commit()
    with pytest.raises(ApiError) as expired:
        inspect(db, owner, doctor, (doc,))
    assert expired.value.status_code == 403
    session.expires_at = "2026-12-01T00:00:00Z"
    session.revoked_at = CREATED
    db.commit()
    with pytest.raises(ApiError) as revoked:
        inspect(db, owner, doctor, (doc,))
    assert revoked.value.status_code == 403


def test_dirty_session_refused_without_implicit_flush(db: Session, context) -> None:
    owner, doctor = context
    doc = report(db, owner, "dirty-source")
    owner_id = owner.id
    doc_id = doc.id
    doc.extraction_status = "needs_verification"
    assert doc in db.dirty
    with pytest.raises(ApiError) as error:
        inspect_offline_recovery_selection(
            db,
            principal=doctor,
            patient_id=owner_id,
            selected_document_ids=(doc_id,),
            omission_proposals=(),
            as_of_utc=CLOCK,
        )
    assert error.value.status_code == 400
    assert doc in db.dirty
    assert doc.extraction_status == "needs_verification"


def test_empty_duplicate_and_invalid_omission_proposals_fail_closed(db: Session, context) -> None:
    owner, doctor = context
    doc = report(db, owner, "bad-selection")
    for docs in [(doc, doc), tuple(doc for _ in range(9))]:
        with pytest.raises(ApiError) as bad:
            inspect(db, owner, doctor, docs)
        assert bad.value.status_code == 400
    with pytest.raises(ApiError) as bad_reason:
        inspect(
            db,
            owner,
            doctor,
            (doc,),
            omissions=(CandidateDoctorOmission(doc.id, "trust_recovery_automatically"),),
        )
    assert bad_reason.value.status_code == 400
    with pytest.raises(ApiError) as bad_dup:
        inspect(db, owner, doctor, (doc,), omissions=(omission(doc), omission(doc)))
    assert bad_dup.value.status_code == 400


def test_unlinked_selected_verified_document_is_only_offline_candidate(
    db: Session, context
) -> None:
    owner, doctor = context
    doc = report(db, owner, "no-recovery")
    result = inspect(db, owner, doctor, (doc,))
    assert result.offline_selection_shape_valid
    assert result.historical_rejected_sources == ()
    assert result.doctor_selection_audited is False
    assert result.run_gate_completed is False


def test_missing_recovery_ancestor_fails_neutrally(db: Session, context) -> None:
    owner, doctor = context
    # A dangling foreign key cannot exist in ordinary DB writes; selecting
    # a missing identifier is refused using the same neutral 404 as a foreign ID.
    with pytest.raises(ApiError) as denied:
        inspect_offline_recovery_selection(
            db,
            principal=doctor,
            patient_id=owner.id,
            selected_document_ids=("00000000-0000-4000-8000-000000000000",),
            omission_proposals=(),
            as_of_utc=CLOCK,
        )
    assert denied.value.status_code == 404
