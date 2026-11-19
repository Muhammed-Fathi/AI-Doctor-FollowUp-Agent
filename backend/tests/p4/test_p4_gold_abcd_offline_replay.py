"""P4-4 R4 GOLD-A/B/C/D replay: migrated synthetic SQLite, OFFLINE ONLY.

Reads the committed expected JSONs and seeded rows. Non-seeded report facts,
live check-ins and Case D are *test-created synthetic records*, NOT Tesseract
outputs or a workflow execution. No run authorization, review-item writes,
approved demo-policy thresholds, P5, diagnosis or real medical data.
P3 GOLD-EX-11 real OCR remains FAIL / NOT PROVEN.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid5

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    User,
)
from app.services.demo_rules_candidate import (
    CandidateDemoPolicy,
    CandidateRuleError,
    evaluate_candidate_review_subset,
)
from app.services.documents.mapping import VerifiedFactView, decide_mapping
from app.services.documents.quality import sync_issues
from app.services.monitoring import (
    MonitoringInputError,
    ObservationSnapshot,
    compare_observation_history,
)
from app.services.p4_document_preflight import inspect_selected_document_verification
from app.services.provenance_review_candidate import (
    CandidateProvenancePolicy,
    CandidateRecordedObservation,
    evaluate_offline_provenance_candidates,
)
from app.services.seed import seed_demo_data

AS_OF = datetime(2026, 11, 14, 12, tzinfo=UTC)
UTC_TEXT = "2026-11-14T12:00:00Z"
CREATED = "2026-11-04T08:00:00Z"
TEST_CREDENTIAL = "p4-gold-fictitious-seed-only"
ID_SPACE = UUID("12345678-1234-4234-8234-123456789abc")
EXPECTED_ROOT = REPO_ROOT / "data" / "synthetic" / "golden_cases"


def fixture_id(label: str) -> str:
    return str(uuid5(ID_SPACE, label))


def expected(case: str) -> dict:
    path = EXPECTED_ROOT / f"GOLD-{case}.expected.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["case_id"] == f"GOLD-{case}"
    assert data["demo_as_of_utc"] == UTC_TEXT
    assert data["candidate_policy_status"] == "test-only-unapproved"
    return data


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_demo_data(session, password=TEST_CREDENTIAL, now=AS_OF, iterations=1000)
        session.commit()
        yield session


def patient(db: Session, reference: str) -> Patient:
    return db.execute(select(Patient).where(Patient.external_ref == reference)).scalar_one()


def doctor(db: Session) -> User:
    return db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()


def principal(db: Session) -> Principal:
    user = doctor(db)
    return Principal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=Role(user.role),
        patient_id=user.patient_id,
        session_id="synthetic-gold-only",
    )


def snapshots(db: Session, owner: Patient) -> tuple[ObservationSnapshot, ...]:
    rows = db.execute(
        select(Observation)
        .where(Observation.patient_id == owner.id)
        .order_by(Observation.id)
    ).scalars()
    return tuple(
        ObservationSnapshot(
            id=row.id,
            patient_id=row.patient_id,
            measure_type=row.measure_type,
            value=row.value,
            unit=row.unit,
            measured_at=row.measured_at,
            validation=row.validation,
            trust_level=row.trust_level,
        )
        for row in rows
    )


def base_policy() -> CandidateDemoPolicy:
    # Values copied from the proposal solely for fixture assertion. R3 is OPEN.
    return CandidateDemoPolicy(
        policy_version="candidate-p4-2a-0.2.0",
        demo_only=True,
        demo_as_of_utc=AS_OF,
        baseline_lookback_days=90,
        stale_measurement_days=30,
        demo_delta_systolic_mmHg=10,
        demo_delta_diastolic_mmHg=8,
        demo_delta_heart_rate_bpm=15,
        demo_delta_glucose_mgdl=40,
        max_items_per_type=3,
        enabled_rule_ids=("DR-001", "DR-003", "DR-005", "DR-009"),
    )


def source_policy() -> CandidateProvenancePolicy:
    return CandidateProvenancePolicy(
        policy_version="candidate-p4-2d-0.1.0",
        demo_only=True,
        demo_as_of_utc=AS_OF,
        conflict_tolerance="0",
        max_items_per_type=3,
        enabled_rule_ids=("DR-006", "DR-008"),
    )


def compare_and_candidates(
    db: Session, owner: Patient
) -> tuple[tuple[ObservationSnapshot, ...], tuple]:
    rows = snapshots(db, owner)
    compared = compare_observation_history(
        rows,
        patient_id=owner.id,
        as_of_utc=AS_OF,
        baseline_lookback_days=90,
    )
    result = evaluate_candidate_review_subset(
        patient_id=owner.id,
        observations=rows,
        comparisons=compared,
        policy=base_policy(),
        as_of_utc=AS_OF,
        blocking_fact_count=0,  # Explicit TEST-ONLY input. Never a trusted gate.
    )
    return rows, result.flags


def stored_report(
    db: Session,
    *,
    owner: Patient,
    label: str,
    report_date: str,
    test_name: str,
    value: str,
    unit: str,
    include_reference: bool = False,
) -> tuple[Document, ExtractedFact]:
    """Plant *already verified* synthetic fact rows, not a P3 promotion test."""
    doc = Document(
        id=fixture_id(f"{label}-document"),
        patient_id=owner.id,
        uploaded_by_user_id=doctor(db).id,
        original_filename=f"{label}-synthetic-only.pdf",
        stored_path=f"{label}-fixture-no-file.pdf",
        mime_type="application/pdf",
        sha256=sha256(label.encode("utf-8")).hexdigest(),
        size_bytes=1,
        extraction_status="verified",
        document_patient_ref=owner.external_ref,
        uploaded_at=CREATED,
    )
    db.add(doc)
    db.flush()
    fields = [
        ("report_date", report_date, report_date, None),
        ("test_name", test_name, test_name, None),
        ("value", value, value, unit),
        ("unit", unit, unit, unit),
    ]
    if include_reference:
        fields.append(("reference_text", "SYNTHETIC REFERENCE", "SYNTHETIC REFERENCE", None))
    value_fact = None
    for index, (name, raw, normal, fact_unit) in enumerate(fields):
        fact = ExtractedFact(
            id=fixture_id(f"{label}-fact-{name}"),
            document_id=doc.id,
            patient_id=owner.id,
            field_name=name,
            raw_text=raw,
            normalized_value=normal,
            unit=fact_unit,
            page_index=0,
            char_start=index * 20,
            char_end=index * 20 + len(raw),
            verification_status="verified",
            created_at=CREATED,
        )
        db.add(fact)
        db.flush()
        db.add(
            FactVerification(
                id=fixture_id(f"{label}-decision-{name}"),
                fact_id=fact.id,
                decision="verified",
                verified_by_user_id=doctor(db).id,
                decided_at=CREATED,
            )
        )
        if name == "value":
            value_fact = fact
    assert value_fact is not None
    db.commit()
    return doc, value_fact


def stored_mapping(db: Session, document: Document):
    facts = list(
        db.execute(
            select(ExtractedFact).where(ExtractedFact.document_id == document.id)
        ).scalars()
    )
    return decide_mapping(
        [
            VerifiedFactView(
                field_name=fact.field_name,
                normalized_value=fact.normalized_value,
                unit=fact.unit,
                verification_status=fact.verification_status,
            )
            for fact in facts
        ]
    )


def add_mapped_observation(
    db: Session, owner: Patient, *, label: str, document: Document, value_fact: ExtractedFact
) -> Observation:
    """Fixture construction only: do NOT represent this as P3 mapping API execution."""
    mapping = stored_mapping(db, document)
    assert mapping.mapped is not None
    item = mapping.mapped
    row = Observation(
        id=fixture_id(f"{label}-observation"),
        patient_id=owner.id,
        measure_type=item.measure_type.value,
        value=item.value,
        unit=item.unit,
        measured_at=item.measured_at,
        source="verified_document",
        source_fact_id=value_fact.id,
        validation="ok",
        trust_level="doctor_verified",
        verified_by_user_id=doctor(db).id,
        verified_at=CREATED,
        created_at=CREATED,
        created_by_user_id=doctor(db).id,
    )
    db.add(row)
    db.commit()
    return row


def assert_selected_doc_preflight(db: Session, owner: Patient, doc: Document, *, clear: bool):
    result = inspect_selected_document_verification(
        db,
        principal=principal(db),
        patient_id=owner.id,
        document_ids=(doc.id,),
    )
    assert result.candidate_documents_clear is clear
    assert result.run_gate_completed is False  # P5 not implemented; NEVER claim a cleared run.
    return result


def test_gold_a_seed_plus_live_checkin_and_document_only_test(db: Session) -> None:
    spec = expected("A")
    owner = patient(db, spec["patient_external_ref"])
    doc, _ = stored_report(
        db,
        owner=owner,
        label="gold-a",
        report_date="2026-10-20",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        include_reference=True,
    )
    mapping = stored_mapping(db, doc)
    assert not mapping.is_mapped
    assert mapping.reason == spec["document_mapping"]["reason"]
    assert spec["document_mapping"]["mapped_observations"] == 0
    assert_selected_doc_preflight(db, owner, doc, clear=True)
    for measure, value, unit in [
        ("systolic_bp", 121, "mmHg"),
        ("diastolic_bp", 78, "mmHg"),
        ("heart_rate", 71, "bpm"),
    ]:
        db.add(
            Observation(
                id=fixture_id(f"gold-a-live-{measure}"),
                patient_id=owner.id,
                measure_type=measure,
                value=value,
                unit=unit,
                measured_at="2026-11-01T09:00:00Z",
                source="patient_checkin",
                trust_level="self_reported_validated",
                validation="ok",
                created_at=CREATED,
            )
        )
    db.commit()
    rows, flags = compare_and_candidates(db, owner)
    assert len(rows) == 6 + spec["expected_live_checkin_count"]
    assert [f.rule_id for f in flags] == spec["expected_review_rule_ids"] == []
    assert spec["expected_open_verification_issue_ids"] == []


def test_gold_b_exact_most_recent_prior_and_verified_document_value(db: Session) -> None:
    spec = expected("B")
    owner = patient(db, spec["patient_external_ref"])
    doc, value_fact = stored_report(
        db, owner=owner, label="gold-b", report_date="2026-11-02",
        test_name="Fasting glucose", value="104", unit="mg/dL",
    )
    mapped = stored_mapping(db, doc)
    assert mapped.mapped is not None
    assert mapped.mapped.measured_at == spec["document_mapping"]["measured_at"]
    row = add_mapped_observation(db, owner, label="gold-b", document=doc, value_fact=value_fact)
    assert row.measured_at == spec["document_mapping"]["measured_at"]
    assert row.trust_level == spec["document_mapping"]["trust_level"]
    assert_selected_doc_preflight(db, owner, doc, clear=True)
    rows, flags = compare_and_candidates(db, owner)
    assert len(flags) == spec["expected_review_count"] == 1
    assert [x.rule_id for x in flags] == spec["expected_review_rule_ids"]
    flag = flags[0]
    gold = spec["expected_dr005"]
    assert (flag.reason_code, flag.trust_basis, flag.message) == (
        "change_exceeds_demo_parameter", gold["trust_basis"], gold["message"]
    )
    assert len(flag.evidence) == gold["evidence_count"]
    by_id = {row.id: row for row in rows}
    relevant = [by_id[item.removeprefix("observation:")] for item in flag.evidence]
    assert {r.measured_at for r in relevant} == {
        gold["baseline_measured_at"], gold["current_measured_at"]
    }
    assert abs(float(relevant[0].value) - float(relevant[1].value)) == gold["delta"]
    assert all(r.trust_level == "self_reported_validated" for r in relevant)
    assert flag.demo_only is True
    assert len(flag.dedupe_key) == 64


def test_gold_c_preverification_four_real_issue_types_and_no_run_clearance(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.documents import quality

    spec = expected("C")
    owner = patient(db, spec["patient_external_ref"])
    monkeypatch.setattr(quality, "utc_now", lambda: AS_OF)
    doc, _ = pending_c_document(db, owner)
    issues = sync_issues(db, document=doc, conflict_tolerance=0)
    db.commit()
    before = spec["pre_verification"]
    assert sorted(issue.issue_type for issue in issues) == before["expected_open_verification_issue_ids"]
    vi2 = next(issue for issue in issues if issue.issue_type == "VI-002")
    assert vi2.message == before["expected_unverified_message"]
    blocked = assert_selected_doc_preflight(db, owner, doc, clear=False)
    assert blocked.active_fact_count == before["pending_active_fact_count"]
    assert "active_fact_unverified" in {item.reason_code for item in blocked.blockers}
    assert "open_verification_issue" in {item.reason_code for item in blocked.blockers}
    # No DR evaluator is invoked here. A caller's fake '0' is NOT a run gate.
    assert before["expected_review_rule_ids"] == []
    assert "FAIL / NOT PROVEN" in spec["real_ocr_result"]


def pending_c_document(db: Session, owner: Patient) -> tuple[Document, dict[str, ExtractedFact]]:
    doc = Document(
        id=fixture_id("gold-c-document"),
        patient_id=owner.id,
        uploaded_by_user_id=doctor(db).id,
        original_filename="gold-c-abstract-ocr-fixture.png",
        stored_path="gold-c-no-real-ocr.png",
        mime_type="image/png",
        sha256=sha256(b"gold-c-synthetic-not-an-image").hexdigest(),
        size_bytes=1,
        extraction_status="needs_verification",
        document_patient_ref=owner.external_ref,
        uploaded_at=CREATED,
    )
    db.add(doc)
    db.flush()
    details = [
        ("report_date", "03/11/2026", None, None, ["ambiguous_date"]),
        ("test_name", "Glucose", "Glucose", None, []),
        ("value", "1O5", None, None, ["low_confidence", "ambiguous_unit"]),
    ]
    facts = {}
    for index, (name, raw, normal, unit, flags) in enumerate(details):
        fact = ExtractedFact(
            id=fixture_id(f"gold-c-pending-{name}"),
            document_id=doc.id,
            patient_id=owner.id,
            field_name=name,
            raw_text=raw,
            normalized_value=normal,
            unit=unit,
            quality_flags=json.dumps(flags),
            page_index=0,
            char_start=index * 20,
            char_end=index * 20 + len(raw),
            verification_status="pending",
            created_at=CREATED,
        )
        db.add(fact)
        facts[name] = fact
    db.commit()
    return doc, facts


def correct_c_fixture(db: Session, doc: Document, facts: dict[str, ExtractedFact]) -> ExtractedFact:
    """Script synthetic human decisions only; does NOT prove source-image review."""
    verifier = doctor(db)
    for name in ("report_date", "test_name", "value"):
        original = facts[name]
        changed = name != "test_name"
        original.verification_status = "rejected" if changed else "verified"
        replacement = "2026-11-03" if name == "report_date" else "105"
        db.add(
            FactVerification(
                id=fixture_id(f"gold-c-decision-{name}"),
                fact_id=original.id,
                decision="corrected" if changed else "verified",
                new_value=replacement if changed else None,
                new_unit="mg/dL" if name == "value" else None,
                verified_by_user_id=verifier.id,
                decided_at=CREATED,
            )
        )
        if changed:
            db.add(
                ExtractedFact(
                    id=fixture_id(f"gold-c-corrected-{name}"),
                    document_id=doc.id,
                    patient_id=doc.patient_id,
                    field_name=name,
                    raw_text=replacement,
                    normalized_value=replacement,
                    unit="mg/dL" if name == "value" else None,
                    corrected_from_fact_id=original.id,
                    quality_flags="[]",
                    page_index=0,
                    char_start=original.char_start,
                    char_end=original.char_end,
                    verification_status="verified",
                    created_at=CREATED,
                )
            )
    doc.extraction_status = "verified"
    db.commit()
    return db.execute(
        select(ExtractedFact).where(ExtractedFact.id == fixture_id("gold-c-corrected-value"))
    ).scalar_one()


def test_gold_c_postfixture_correction_resolves_issues_and_mixed_delta(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.documents import quality

    spec = expected("C")
    owner = patient(db, spec["patient_external_ref"])
    monkeypatch.setattr(quality, "utc_now", lambda: AS_OF)
    doc, original = pending_c_document(db, owner)
    assert len(sync_issues(db, document=doc, conflict_tolerance=0)) == 4
    db.commit()
    value = correct_c_fixture(db, doc, original)
    assert sync_issues(db, document=doc, conflict_tolerance=0) == ()
    db.commit()
    mapped = stored_mapping(db, doc)
    gold = spec["post_fixture_correction"]
    assert mapped.mapped is not None
    assert mapped.mapped.value == gold["document_mapping"]["value"]
    assert mapped.mapped.measured_at == gold["document_mapping"]["measured_at"]
    new_row = add_mapped_observation(
        db, owner, label="gold-c", document=doc, value_fact=value
    )
    assert new_row.trust_level == gold["document_mapping"]["trust_level"]
    assert_selected_doc_preflight(db, owner, doc, clear=True)
    rows, flags = compare_and_candidates(db, owner)
    assert [flag.rule_id for flag in flags] == gold["expected_review_rule_ids"]
    compared = compare_observation_history(
        rows, patient_id=owner.id, as_of_utc=AS_OF, baseline_lookback_days=90
    )
    glucose = next(item for item in compared.comparisons if item.measure_type == "glucose")
    assert glucose.comparable and glucose.trust_basis == gold["trust_basis"]
    assert float(glucose.delta) == gold["expected_delta"]
    assert all(item.rule_id not in {"DR-006", "DR-008"} for item in flags)
    assert "FAIL / NOT PROVEN" in spec["real_ocr_result"]


def setup_gold_d(db: Session) -> Patient:
    spec = expected("D")
    user = doctor(db)
    owner = Patient(
        id=spec["patient_id"],
        display_name="Demo Patient D (Yara)",
        assigned_doctor_id=user.id,
        external_ref=spec["patient_external_ref"],
        data_source="synthetic_fixture",
        created_at=CREATED,
        updated_at=CREATED,
    )
    db.add(owner)
    db.flush()
    readings = [
        ("heart_rate", 68, "bpm", "2026-09-01T09:00:00Z", "ok"),
        ("systolic_bp", 128, "mmHg", "2026-10-05T09:00:00Z", "ok"),
        ("diastolic_bp", 82, "mmHg", "2026-10-05T09:00:00Z", "ok"),
        ("systolic_bp", 130, "mmHg", "2026-10-20T09:00:00Z", "ok"),
        ("systolic_bp", 130, "mmHg", "2026-10-20T09:00:00Z", "ok"),
        ("diastolic_bp", 250, "mmHg", "2026-10-25T09:00:00Z", "ok_with_warning"),
    ]
    for index, (measure, value, unit, measured_at, validation) in enumerate(readings):
        db.add(
            Observation(
                id=fixture_id(f"gold-d-observation-{index}"),
                patient_id=owner.id,
                measure_type=measure,
                value=value,
                unit=unit,
                measured_at=measured_at,
                created_at=CREATED,
                source="seed_fixture",
                validation=validation,
                trust_level="self_reported_validated",
            )
        )
    db.commit()
    return owner


def dr008_rows(db: Session, owner: Patient) -> tuple[CandidateRecordedObservation, ...]:
    rows = list(
        db.execute(
            select(Observation).where(Observation.patient_id == owner.id)
        ).scalars()
    )
    return tuple(
        CandidateRecordedObservation(
            observation=ObservationSnapshot(
                id=row.id, patient_id=row.patient_id, measure_type=row.measure_type,
                value=row.value, unit=row.unit, measured_at=row.measured_at,
                validation=row.validation, trust_level=row.trust_level,
            ),
            created_at=row.created_at,
            source=row.source,
        )
        for row in rows
    )


def test_gold_d_all_five_positive_ids_from_stored_rows(db: Session) -> None:
    spec = expected("D")
    owner = setup_gold_d(db)
    rows, base = compare_and_candidates(db, owner)
    source_rows = dr008_rows(db, owner)
    provenance = evaluate_offline_provenance_candidates(
        patient_id=owner.id,
        records=source_rows,
        policy=source_policy(),
        as_of_utc=AS_OF,
        blocking_fact_count=0,  # Fixture-only, no source-gate attestation.
    )
    all_flags = (*base, *provenance.flags)
    assert len(rows) == 6
    assert len(all_flags) == spec["expected_review_count"] == 5
    assert sorted(flag.rule_id for flag in all_flags) == spec["expected_review_rule_ids"]
    for flag in all_flags:
        assert flag.demo_only
        assert len(flag.dedupe_key) == 64
        assert flag.trust_basis == "self_reported"
        assert len(flag.message) <= 240
        assert all(ref.startswith("observation:") for ref in flag.evidence)
    assert [flag.rule_id for flag in provenance.flags] == ["DR-008"]
    assert len({ref.removeprefix("observation:") for ref in provenance.flags[0].evidence}) == 2
    assert all(flag.rule_id != "DR-006" for flag in all_flags)
    assert spec["expected_source_conflicts"] == 0
    assert {flag.rule_id: flag.workflow_hint for flag in all_flags}["DR-009"] == "data_quality"
    asserted = {flag.rule_id for flag in base}
    assert asserted == {"DR-001", "DR-003", "DR-005", "DR-009"}
    diastolic = [row for row in rows if row.measure_type == "diastolic_bp"]
    assert abs(float(diastolic[1].value) - float(diastolic[0].value)) == (
        spec["expected_deltas"]["diastolic_bp"]
    )


def test_gold_d_replay_and_reordered_rows_are_identical(db: Session) -> None:
    owner = setup_gold_d(db)
    persisted = snapshots(db, owner)
    compared = compare_observation_history(
        persisted, patient_id=owner.id, as_of_utc=AS_OF, baseline_lookback_days=90
    )
    shuffled = tuple(reversed(persisted))
    again = compare_observation_history(
        shuffled, patient_id=owner.id, as_of_utc=AS_OF, baseline_lookback_days=90
    )
    assert compared == again
    first = evaluate_candidate_review_subset(
        patient_id=owner.id, observations=persisted, comparisons=compared,
        policy=base_policy(), as_of_utc=AS_OF, blocking_fact_count=0,
    )
    repeated = evaluate_candidate_review_subset(
        patient_id=owner.id, observations=shuffled, comparisons=again,
        policy=base_policy(), as_of_utc=AS_OF, blocking_fact_count=0,
    )
    assert first == repeated
    sources = dr008_rows(db, owner)
    a = evaluate_offline_provenance_candidates(
        patient_id=owner.id, records=sources, policy=source_policy(),
        as_of_utc=AS_OF, blocking_fact_count=0,
    )
    b = evaluate_offline_provenance_candidates(
        patient_id=owner.id, records=tuple(reversed(sources)), policy=source_policy(),
        as_of_utc=AS_OF, blocking_fact_count=0,
    )
    assert a == b
    assert len({item.dedupe_key for item in (*a.flags, *first.flags)}) == 5


def test_gold_negative_cross_patient_and_rejected_row_fail_or_exclude(db: Session) -> None:
    first = patient(db, "DEMO-A-001")
    second = patient(db, "DEMO-B-001")
    mixed = (*snapshots(db, first), *snapshots(db, second))
    with pytest.raises(MonitoringInputError) as denied:
        compare_observation_history(
            mixed, patient_id=first.id, as_of_utc=AS_OF, baseline_lookback_days=90
        )
    assert denied.value.code == "E_SCOPE_VIOLATION"
    rows = list(snapshots(db, first))
    bad = replace(rows[0], id=fixture_id("rejected-observation"), validation="rejected")
    wrong_unit = replace(rows[1], id=fixture_id("wrong-unit-observation"), unit="bpm")
    future = replace(
        rows[2], id=fixture_id("future-observation"), measured_at="2026-11-15T08:00:00Z"
    )
    result = compare_observation_history(
        (*rows, bad, wrong_unit, future),
        patient_id=first.id, as_of_utc=AS_OF, baseline_lookback_days=90,
    )
    reasons = {excluded.skip_reason for excluded in result.excluded}
    assert reasons == {"validation_rejected", "unit_mismatch", "future_timestamp"}


def test_gold_negative_unverified_fact_count_is_not_an_authorized_gate(db: Session) -> None:
    owner = patient(db, "DEMO-C-001")
    doc, _ = pending_c_document(db, owner)
    before = assert_selected_doc_preflight(db, owner, doc, clear=False)
    # Even a forged test-only zero below would not change the independent DB read.
    assert before.run_gate_completed is False
    assert before.active_fact_count == 3
    with pytest.raises(CandidateRuleError) as err:
        rows = snapshots(db, owner)
        comparisons = compare_observation_history(
            rows, patient_id=owner.id, as_of_utc=AS_OF, baseline_lookback_days=90
        )
        evaluate_candidate_review_subset(
            patient_id=owner.id, observations=rows, comparisons=comparisons,
            policy=base_policy(), as_of_utc=AS_OF, blocking_fact_count=3,
        )
    assert err.value.code == "E_UNVERIFIED_FACT"
    assert_selected_doc_preflight(db, owner, doc, clear=False)


def test_gold_d_no_review_items_or_workflow_rows_written_by_pure_rules(db: Session) -> None:
    owner = setup_gold_d(db)
    prior = db.scalar(select(func.count()).select_from(Observation))
    before = len(db.new), len(db.dirty), len(db.deleted)
    compare_and_candidates(db, owner)
    evaluate_offline_provenance_candidates(
        patient_id=owner.id, records=dr008_rows(db, owner), policy=source_policy(),
        as_of_utc=AS_OF, blocking_fact_count=0,
    )
    assert db.scalar(select(func.count()).select_from(Observation)) == prior
    assert (len(db.new), len(db.dirty), len(db.deleted)) == before == (0, 0, 0)
