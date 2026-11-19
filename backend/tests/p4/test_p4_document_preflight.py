"""P4-2f selected-document preflight on real migrated test SQLite.

All data is synthetic. This is NOT a runtime or OCR fidelity gate.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
    VerificationIssue,
)
from app.services.p4_document_preflight import inspect_selected_document_verification
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CREATED = "2026-11-04T08:00:00Z"
DEMO_TEST_CREDENTIAL = "p4-synthetic-only-credential"


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(
            session, password=DEMO_TEST_CREDENTIAL, now=CLOCK, iterations=1000
        )
        session.commit()
        yield session


def identity(db: Session, username: str = "demo_doctor") -> Principal:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=Role(user.role),
        patient_id=user.patient_id,
        session_id="p4-synthetic-fixture-session",
    )


def patient(db: Session, ref: str = "DEMO-A-001") -> Patient:
    return db.execute(select(Patient).where(Patient.external_ref == ref)).scalar_one()


def prepared_document(
    db: Session, *,
    owner: Patient | None = None,
    status: str = "verified",
    verified_status: str = "verified",
    with_decision: bool = True,
    correction: bool = False,
) -> tuple[Document, ExtractedFact, ExtractedFact | None]:
    owner = owner or patient(db)
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    doc = Document(
        patient_id=owner.id,
        uploaded_by_user_id=doctor.id,
        original_filename="synthetic-document.pdf",
        stored_path="synthetic-only.pdf",
        mime_type="application/pdf",
        sha256="0" * 64,
        size_bytes=1,
        extraction_status=status,
        document_patient_ref=owner.external_ref,
        uploaded_at=CREATED,
    )
    db.add(doc)
    db.flush()
    first = ExtractedFact(
        document_id=doc.id,
        patient_id=owner.id,
        field_name="value",
        raw_text="105",
        normalized_value="105",
        unit="mg/dL",
        page_index=0,
        char_start=0,
        char_end=3,
        verification_status="rejected" if correction else verified_status,
        created_at=CREATED,
    )
    db.add(first)
    db.flush()
    corrected = None
    if correction:
        corrected = ExtractedFact(
            document_id=doc.id,
            patient_id=owner.id,
            field_name="value",
            raw_text="1O5",
            normalized_value="105",
            unit="mg/dL",
            page_index=0,
            char_start=0,
            char_end=3,
            verification_status="verified",
            corrected_from_fact_id=first.id,
            created_at=CREATED,
        )
        db.add(corrected)
        db.flush()
    if with_decision:
        db.add(
            FactVerification(
                fact_id=first.id,
                decision="corrected" if correction else "verified",
                new_value="105" if correction else None,
                verified_by_user_id=doctor.id,
                decided_at=CREATED,
            )
        )
    db.commit()
    return doc, first, corrected


def inspect(db: Session, *docs: Document, principal: Principal | None = None):
    return inspect_selected_document_verification(
        db,
        principal=principal or identity(db),
        patient_id=patient(db).id,
        document_ids=tuple(doc.id for doc in docs),
    )


def reasons(result) -> set[str]:
    return {item.reason_code for item in result.blockers}


def test_verified_selected_document_is_clear_only_as_internal_candidate(db: Session) -> None:
    document, _, _ = prepared_document(db)
    result = inspect(db, document)
    assert result.candidate_documents_clear is True
    assert result.run_gate_completed is False
    assert result.blockers == ()
    assert result.active_fact_count == 1
    assert result.verified_fact_count == 1


def test_doctor_correction_original_rejected_is_not_active_blocker(db: Session) -> None:
    document, original, corrected = prepared_document(db, correction=True)
    assert corrected is not None
    result = inspect(db, document)
    assert result.candidate_documents_clear is True
    assert result.active_fact_count == 1
    assert result.verified_fact_count == 1
    assert original.verification_status == "rejected"


def test_pending_and_plain_rejection_both_block_without_masking(db: Session) -> None:
    document, fact, _ = prepared_document(db, verified_status="pending")
    pending = inspect(db, document)
    assert not pending.candidate_documents_clear
    assert "active_fact_unverified" in reasons(pending)
    fact.verification_status = "rejected"
    db.commit()
    rejected = inspect(db, document)
    assert "active_fact_unverified" in reasons(rejected)


def test_verified_fact_without_human_decision_still_blocks(db: Session) -> None:
    document, _, _ = prepared_document(db, with_decision=False)
    result = inspect(db, document)
    assert result.active_fact_count == 1
    assert result.verified_fact_count == 0
    assert "fact_decision_unproven" in reasons(result)


def test_open_vi_issue_blocks_and_resolved_issue_does_not(db: Session) -> None:
    document, fact, _ = prepared_document(db)
    issue = VerificationIssue(
        patient_id=patient(db).id,
        document_id=document.id,
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
    blocked = inspect(db, document)
    assert "open_verification_issue" in reasons(blocked)
    assert not blocked.candidate_documents_clear
    issue.state = "resolved"
    db.commit()
    clear = inspect(db, document)
    assert clear.candidate_documents_clear


def test_non_verified_status_or_identity_mismatch_blocks(db: Session) -> None:
    document, _, _ = prepared_document(db)
    document.extraction_status = "needs_verification"
    db.commit()
    assert "document_not_verified" in reasons(inspect(db, document))
    document.extraction_status = "verified"
    document.document_patient_ref = "DEMO-OTHER-001"
    db.commit()
    assert "document_identity_unresolved" in reasons(inspect(db, document))


def test_cross_patient_and_unassigned_doctor_fail_before_fact_inspection(db: Session) -> None:
    document, _, _ = prepared_document(db, owner=patient(db, "DEMO-B-001"))
    with pytest.raises(ApiError) as cross:
        inspect(db, document)
    assert cross.value.status_code == 404
    with pytest.raises(ApiError) as unassigned:
        inspect_selected_document_verification(
            db,
            principal=identity(db, "demo_doctor_unassigned"),
            patient_id=patient(db).id,
            document_ids=(document.id,),
        )
    assert unassigned.value.status_code == 403


def test_bad_set_and_missing_document_fail_closed(db: Session) -> None:
    document, _, _ = prepared_document(db)
    with pytest.raises(ApiError) as duplicate:
        inspect(db, document, document)
    assert duplicate.value.status_code == 400
    with pytest.raises(ApiError) as empty:
        inspect(db)
    assert empty.value.status_code == 400
    with pytest.raises(ApiError) as missing:
        inspect_selected_document_verification(
            db, principal=identity(db),
            patient_id=patient(db).id,
            document_ids=("00000000-0000-4000-8000-000000000000",),
        )
    assert missing.value.status_code == 404


def test_invalid_corrected_lineage_never_clears_rejected_original(db: Session) -> None:
    document, _, corrected = prepared_document(db, correction=True)
    assert corrected is not None
    decision = db.execute(
        select(FactVerification).where(FactVerification.fact_id == corrected.corrected_from_fact_id)
    ).scalar_one()
    decision.new_value = "999"
    db.commit()
    result = inspect(db, document)
    assert not result.candidate_documents_clear
    assert "active_fact_unverified" in reasons(result)
    assert "fact_decision_unproven" in reasons(result)


def test_snapshot_deterministic_and_read_only(db: Session) -> None:
    document, _, _ = prepared_document(db)
    before = db.scalar(select(func.count()).select_from(Observation))
    first = inspect(db, document)
    second = inspect(db, document)
    assert first == second
    assert first.document_ids == (document.id,)
    assert db.scalar(select(func.count()).select_from(Observation)) == before
    assert not db.new and not db.dirty
