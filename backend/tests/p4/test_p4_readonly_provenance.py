"""P4-2e migrated SQLite projection tests; fictitious accounts and data only.

This verifies stored provenance/doctor assignment only. It is NOT an OCR
fidelity test, a complete VI-* verification gate or a live review endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.errors import ApiError
from app.core.policies import Principal
from app.db.models import Document, ExtractedFact, FactVerification, Observation, Patient, User
from app.services.p4_readonly_provenance import load_readonly_provenance_evidence
from app.services.provenance_review_candidate import (
    CandidateProvenancePolicy,
    evaluate_offline_provenance_candidates,
)
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
MEASURED = "2026-11-03T08:00:00Z"
CREATED = "2026-11-04T08:00:00Z"


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(session, password="synthetic-ci-password", now=CLOCK, iterations=1000)
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
        session_id="synthetic-internal-fixture",
    )


def patient(db: Session, reference: str = "DEMO-A-001") -> Patient:
    return db.execute(select(Patient).where(Patient.external_ref == reference)).scalar_one()


def stored_document_observation(
    db: Session,
    *,
    suffix: str,
    value: float,
    original_corrected: bool = False,
    decision_present: bool = True,
) -> tuple[Observation, Document, ExtractedFact]:
    owner = patient(db)
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    doc = Document(
        patient_id=owner.id,
        uploaded_by_user_id=doctor.id,
        original_filename=f"synthetic-{suffix}.pdf",
        stored_path=f"synthetic-{suffix}.pdf",
        mime_type="application/pdf",
        sha256=sha256(suffix.encode("utf-8")).hexdigest(),
        size_bytes=1,
        extraction_status="verified",
        document_patient_ref=owner.external_ref,
        uploaded_at=CREATED,
    )
    db.add(doc)
    db.flush()
    initial = ExtractedFact(
        document_id=doc.id,
        patient_id=owner.id,
        field_name="value",
        raw_text=str(value),
        normalized_value=str(value),
        unit="mmHg",
        page_index=0,
        char_start=0,
        char_end=3,
        verification_status="rejected" if original_corrected else "verified",
        created_at=CREATED,
    )
    db.add(initial)
    db.flush()
    chosen = initial
    if original_corrected:
        chosen = ExtractedFact(
            document_id=doc.id,
            patient_id=owner.id,
            field_name="value",
            raw_text=str(value),
            normalized_value=str(value),
            unit="mmHg",
            page_index=0,
            char_start=0,
            char_end=3,
            verification_status="verified",
            corrected_from_fact_id=initial.id,
            created_at=CREATED,
        )
        db.add(chosen)
        db.flush()
    if decision_present:
        db.add(
            FactVerification(
                fact_id=initial.id,
                decision="corrected" if original_corrected else "verified",
                new_value=str(value) if original_corrected else None,
                new_unit="mmHg" if original_corrected else None,
                verified_by_user_id=doctor.id,
                decided_at=CREATED,
            )
        )
    obs = Observation(
        patient_id=owner.id,
        measure_type="systolic_bp",
        value=value,
        unit="mmHg",
        measured_at=MEASURED,
        source="verified_document",
        source_fact_id=chosen.id,
        validation="ok",
        trust_level="doctor_verified",
        verified_by_user_id=doctor.id,
        verified_at=CREATED,
        created_at=CREATED,
        created_by_user_id=doctor.id,
    )
    db.add(obs)
    db.commit()
    return obs, doc, chosen


def test_migrated_sqlite_verified_source_projection_and_offline_pair(db: Session) -> None:
    a, doc_a, fact_a = stored_document_observation(db, suffix="a", value=120)
    b, doc_b, fact_b = stored_document_observation(db, suffix="b", value=130)
    owner = patient(db)
    result = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=owner.id, as_of_utc=CLOCK
    )
    two = tuple(
        item for item in result.records if item.observation.id in {a.id, b.id}
    )
    assert len(two) == 2
    assert {item.source_document_id for item in two} == {doc_a.id, doc_b.id}
    assert {item.source_fact_id for item in two} == {fact_a.id, fact_b.id}
    assert {item.source_fact_verification_status for item in two} == {"verified"}
    fixture_only = evaluate_offline_provenance_candidates(
        patient_id=owner.id,
        records=two,
        policy=CandidateProvenancePolicy(
            policy_version="candidate-p4-2d-0.1.0",
            demo_only=True,
            demo_as_of_utc=CLOCK,
            conflict_tolerance="0",
            max_items_per_type=3,
            enabled_rule_ids=("DR-006",),
        ),
        as_of_utc=CLOCK,
        blocking_fact_count=0,
    )
    assert [flag.rule_id for flag in fixture_only.flags] == ["DR-006"]


def test_missing_decision_and_bad_document_status_fail_closed(db: Session) -> None:
    row, document, _ = stored_document_observation(
        db, suffix="missing-decision", value=120, decision_present=False
    )
    owner = patient(db)
    first = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=owner.id, as_of_utc=CLOCK
    )
    entry = next(x for x in first.records if x.observation.id == row.id)
    assert entry.source_fact_verification_status is None
    assert (row.id, "verified_lineage_unavailable") in [
        (x.observation_id, x.reason) for x in first.lineage_exclusions
    ]
    docver = db.execute(
        select(Document).where(Document.id == document.id)
    ).scalar_one()
    docver.extraction_status = "needs_verification"
    db.commit()
    second = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=owner.id, as_of_utc=CLOCK
    )
    assert next(x for x in second.records if x.observation.id == row.id).source_document_id is None


def test_corrected_fact_gets_lineage_from_original_decision(db: Session) -> None:
    observation, document, fact = stored_document_observation(
        db, suffix="corrected", value=105, original_corrected=True
    )
    result = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=patient(db).id, as_of_utc=CLOCK
    )
    projected = next(x for x in result.records if x.observation.id == observation.id)
    assert projected.source_fact_id == fact.id
    assert projected.source_document_id == document.id
    assert projected.source_fact_verification_status == "verified"


@pytest.mark.parametrize(
    "username",
    ["demo_doctor_unassigned", "demo_patient_a", "demo_admin"],
)
def test_only_assigned_stored_doctor_can_use_internal_projection(
    db: Session, username: str
) -> None:
    with pytest.raises(ApiError) as error:
        load_readonly_provenance_evidence(
            db, principal=identity(db, username), patient_id=patient(db).id, as_of_utc=CLOCK
        )
    assert error.value.status_code == 403


def test_patient_b_record_never_leaks_into_patient_a_projection(db: Session) -> None:
    owner = patient(db)
    other = patient(db, "DEMO-B-001")
    result = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=owner.id, as_of_utc=CLOCK
    )
    assert result.records
    assert all(item.observation.patient_id == owner.id for item in result.records)
    assert all(item.observation.patient_id != other.id for item in result.records)


def test_projection_is_read_only_and_requires_aware_clock(db: Session) -> None:
    original = db.scalar(select(func.count()).select_from(Observation))
    result = load_readonly_provenance_evidence(
        db, principal=identity(db), patient_id=patient(db).id, as_of_utc=CLOCK
    )
    assert result.patient_id == patient(db).id
    assert result.as_of_utc == CLOCK
    assert db.scalar(select(func.count()).select_from(Observation)) == original
    assert not db.new and not db.dirty
    with pytest.raises(ApiError) as invalid:
        load_readonly_provenance_evidence(
            db,
            principal=identity(db),
            patient_id=patient(db).id,
            as_of_utc=datetime(2026, 11, 14, 12),
        )
    assert invalid.value.status_code == 400


def test_over_100_scoped_rows_refused_not_silently_truncated(db: Session) -> None:
    owner = patient(db)
    existing = db.scalar(
        select(func.count()).select_from(Observation).where(Observation.patient_id == owner.id)
    )
    assert existing is not None
    for index in range(101):
        db.add(
            Observation(
                patient_id=owner.id,
                measure_type="heart_rate",
                value=60 + index,
                unit="bpm",
                measured_at=MEASURED,
                source="seed_fixture",
                trust_level="self_reported_validated",
                validation="ok",
                created_at=CREATED,
            )
        )
    db.commit()
    with pytest.raises(ApiError) as too_many:
        load_readonly_provenance_evidence(
            db, principal=identity(db), patient_id=owner.id, as_of_utc=CLOCK
        )
    assert too_many.value.status_code == 400
