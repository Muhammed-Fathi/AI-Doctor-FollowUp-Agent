"""P4-RB4 genuine run-backed GOLD A/B/C/D acceptance.

Every case uses a migrated disposable SQLite database at revision ``0008``,
deterministic synthetic fixtures, an active stored doctor session assigned to the
patient, real selected-source manifests, stored facts and decisions, valid
synthetic source bytes with matching SHA-256/size, and the pinned
``2026-11-14T12:00:00Z`` clock. The accepted services are exercised directly:

* F0 ``create_run_foundation`` (genuine run + selected-source manifest),
* F1 ``evaluate_run_verification_gate`` (actual verification gate decision),
* F2 ``build_run_evaluable_review_evidence`` (fresh read-only evidence),
* RB1 ``build_p4_run_bound_review_input_preview`` (run-bound 90-day preview),
* unchanged RB2 ``evaluate_p4_rb2_offline_fixture`` through RB3
  ``persist_run_review_items`` (durable review persistence, receipts, audit,
  replay).

Nothing here is a real ingestion, OCR run or human verification. Scripted
fixture construction is disclosed as such; it never substitutes a successful
result. Instrumentation only spies/delegates on the real evaluator.

Zero candidates means only "no candidate review items under these bounded demo
rules" -- never clinical normality or clearance. Zero counts are not clinical
clearance. NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.enums import AuditOutcome, Role
from app.core.errors import ApiError, ErrorCode
from app.core.paths import REPO_ROOT
from app.core.policies import Principal
from app.db.models import (
    AuditEvent,
    Document,
    EvidenceLink,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    ReviewEvaluation,
    ReviewItem,
    RunGateBlocker,
    RunGateEvaluation,
    RunSelectedDocument,
    RunSelectedObservation,
    RunSourceOmission,
    User,
    UserSession,
    VerificationIssue,
    WorkflowRun,
)
from app.schemas.p4_rb2_offline_rules import OfflineRuleInput, OfflineRuleResult
from app.schemas.p4_rb3_review_persistence import RB3DenialReason
from app.services import p4_rb3_review_persistence as rb3
from app.services.documents import quality
from app.services.documents.mapping import VerifiedFactView, decide_mapping
from app.services.p4_document_preflight import inspect_selected_document_verification
from app.services.p4_rb2_offline_rules import evaluate_p4_rb2_offline_fixture
from app.services.p4_run_bound_preview import (
    POLICY_CANONICAL_SHA256,
    build_p4_run_bound_review_input_preview,
)
from app.services.p5_evidence_bridge import build_run_evaluable_review_evidence
from app.services.p5_run_foundation import create_run_foundation
from app.services.p5_run_gate import evaluate_run_verification_gate
from app.services.seed import seed_demo_data

CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)
CLOCK_ISO = "2026-11-14T12:00:00Z"
AT_ISO = "2026-06-14T08:00:00Z"
SEED_PASSWORD = "rb4-synthetic-only-seed"
GOLD_DIR = REPO_ROOT / "data" / "synthetic" / "golden_cases"
D_PATIENT_ID = "44444444-4444-4444-8444-444444444444"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def sandbox(engine):
    """Migrated disposable SQLite seeded with the tracked synthetic fixtures."""
    with Session(engine) as db:
        seed_demo_data(db, password=SEED_PASSWORD, now=CLOCK, iterations=1000)
        db.commit()
        yield db


# --------------------------------------------------------------------------- #
# Stored-fixture helpers (scripted construction, NOT ingestion / OCR / human)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _Fact:
    field: str
    raw: str
    normalized: str | None
    unit: str | None = None
    status: str = "verified"
    flags: str = "[]"
    corrected_from: str | None = None
    decision: str | None = "verified"
    new_value: str | None = None
    new_unit: str | None = None
    previous_value: str | None = None
    decided_at: str = AT_ISO


def _doctor(db: Session, *, username: str = "demo_doctor", suffix: str) -> Principal:
    user = db.execute(select(User).where(User.username == username)).scalar_one()
    session_id = f"dddddddd-dddd-4ddd-8ddd-{suffix}"
    if db.get(UserSession, session_id) is None:
        db.add(
            UserSession(
                id=session_id,
                user_id=user.id,
                token_sha256=hashlib.sha256(f"rb4-synthetic-{suffix}".encode()).hexdigest(),
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


def _patient(db: Session, external_ref: str) -> Patient:
    row = db.execute(select(Patient).where(Patient.external_ref == external_ref)).scalar_one()
    return row


def _patient_d(db: Session) -> Patient:
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    if db.get(Patient, D_PATIENT_ID) is None:
        db.add(
            Patient(
                id=D_PATIENT_ID,
                display_name="Demo Patient D (Yara)",
                date_of_birth="1990-05-17",
                sex_at_birth="female",
                assigned_doctor_id=doctor.id,
                external_ref="DEMO-D-001",
                data_source="synthetic_fixture",
                created_at=CLOCK_ISO,
                updated_at=CLOCK_ISO,
            )
        )
        db.commit()
    patient = db.get(Patient, D_PATIENT_ID)
    assert patient is not None
    return patient


def _add_document(
    db: Session,
    *,
    patient_id: str,
    root: Path,
    label: str,
    facts: Sequence[_Fact],
    status: str = "verified",
    failure_code: str | None = None,
) -> tuple[Document, list[ExtractedFact]]:
    """Store a synthetic document with real bytes (matching SHA/size) and facts.

    This is scripted fixture construction. It is not a PDF ingestion, an OCR
    extraction or a clinician decision, and it is never described as one.
    """
    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"RB4 synthetic-only source: {label}".encode()
    name = f"rb4-{label}.pdf"
    (root / name).write_bytes(raw)
    doc = Document(
        patient_id=patient_id,
        uploaded_by_user_id=patient.assigned_doctor_id,
        original_filename=name,
        stored_path=name,
        mime_type="application/pdf",
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        page_count=1,
        extraction_status=status,
        failure_code=failure_code,
        document_patient_ref=patient.external_ref,
        document_patient_refs=json.dumps([patient.external_ref]),
        uploaded_at=AT_ISO,
    )
    db.add(doc)
    db.flush()
    created: list[ExtractedFact] = []
    for spec in facts:
        fact = ExtractedFact(
            document_id=doc.id,
            patient_id=patient_id,
            field_name=spec.field,
            raw_text=spec.raw,
            normalized_value=spec.normalized,
            unit=spec.unit,
            page_index=0,
            char_start=0,
            char_end=max(len(spec.raw), 1),
            verification_status=spec.status,
            quality_flags=spec.flags,
            corrected_from_fact_id=spec.corrected_from,
            created_at=AT_ISO,
        )
        db.add(fact)
        db.flush()
        if spec.decision is not None:
            db.add(
                FactVerification(
                    fact_id=fact.id,
                    decision=spec.decision,
                    previous_value=spec.previous_value,
                    new_value=spec.new_value,
                    new_unit=spec.new_unit,
                    verified_by_user_id=patient.assigned_doctor_id,
                    decided_at=spec.decided_at,
                )
            )
        created.append(fact)
    db.commit()
    return doc, created


def _verified_doc(
    db: Session,
    *,
    patient_id: str,
    root: Path,
    label: str,
    test_name: str,
    value: str,
    unit: str,
    report_date: str,
    with_unit_fact: bool = True,
) -> tuple[Document, dict[str, ExtractedFact]]:
    facts = [
        _Fact("report_date", report_date, report_date),
        _Fact("test_name", test_name, test_name),
        _Fact("value", value, value, unit=unit),
    ]
    if with_unit_fact:
        facts.append(_Fact("unit", unit, unit))
    doc, created = _add_document(db, patient_id=patient_id, root=root, label=label, facts=facts)
    return doc, {fact.field_name: fact for fact in created}


def _add_observation(
    db: Session,
    *,
    observation_id: str,
    patient_id: str,
    measure_type: str,
    value: float,
    unit: str,
    measured_at: str,
    created_at: str = CLOCK_ISO,
    source: str = "seed_fixture",
    validation: str = "ok",
    trust_level: str = "self_reported_validated",
    source_fact_id: str | None = None,
    verified_by_user_id: str | None = None,
    verified_at: str | None = None,
    created_by_user_id: str | None = None,
    note: str | None = None,
) -> Observation:
    row = Observation(
        id=observation_id,
        patient_id=patient_id,
        measure_type=measure_type,
        value=value,
        unit=unit,
        measured_at=measured_at,
        source=source,
        validation=validation,
        trust_level=trust_level,
        source_fact_id=source_fact_id,
        verified_by_user_id=verified_by_user_id,
        verified_at=verified_at,
        created_at=created_at,
        created_by_user_id=created_by_user_id,
        note=note,
    )
    db.add(row)
    db.commit()
    return row


def _mapped_observation_from_mapping(
    db: Session,
    *,
    observation_id: str,
    patient_id: str,
    document: Document,
    facts: Sequence[ExtractedFact],
    doctor_user_id: str,
) -> tuple[Observation, object]:
    """Exercise the accepted closed mapping and store its single mapped tuple.

    ``decide_mapping`` is the real promotion boundary; only its ``mapped``
    candidate is persisted, anchored on the document's ``value`` fact.
    """
    views = [
        VerifiedFactView(
            field_name=fact.field_name,
            normalized_value=fact.normalized_value,
            unit=fact.unit,
            verification_status=fact.verification_status,
        )
        for fact in facts
    ]
    decision = decide_mapping(views)
    assert decision.is_mapped and decision.mapped is not None
    candidate = decision.mapped
    value_fact = next(fact for fact in facts if fact.field_name == "value")
    observation = _add_observation(
        db,
        observation_id=observation_id,
        patient_id=patient_id,
        measure_type=candidate.measure_type.value,
        value=candidate.value,
        unit=candidate.unit,
        measured_at=candidate.measured_at,
        created_at=CLOCK_ISO,
        source="verified_document",
        validation="ok",
        trust_level="doctor_verified",
        source_fact_id=value_fact.id,
        verified_by_user_id=doctor_user_id,
        verified_at=CLOCK_ISO,
        created_by_user_id=doctor_user_id,
    )
    return observation, decision


# --------------------------------------------------------------------------- #
# Run / gate / persistence helpers
# --------------------------------------------------------------------------- #


def _start(
    engine,
    doctor: Principal,
    *,
    patient_id: str,
    document_ids: tuple[str, ...],
    observation_ids: tuple[str, ...],
    request_id: str,
    return_receipt: bool = False,
):
    with Session(engine) as db:
        receipt = create_run_foundation(
            db,
            principal=doctor,
            patient_id=patient_id,
            document_ids=document_ids,
            observation_ids=observation_ids,
            omissions=(),
            client_request_id=request_id,
            as_of_utc=CLOCK,
        )
        db.commit()
        return receipt if return_receipt else receipt.run_id


def _gate(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return evaluate_run_verification_gate(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def _preview(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return build_p4_run_bound_review_input_preview(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def _evidence(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return build_run_evaluable_review_evidence(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def _persist(engine, doctor: Principal, run_id: str, root: Path):
    with Session(engine) as db:
        return rb3.persist_run_review_items(
            db,
            principal=doctor,
            run_id=run_id,
            validation_clock=CLOCK,
            upload_root=str(root),
        )


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _review_counts(db: Session) -> tuple[int, int, int, int]:
    return (
        _count(db, ReviewItem),
        _count(db, EvidenceLink),
        _count(db, ReviewEvaluation),
        _count(db, AuditEvent),
    )


def _rows(db: Session, model: type) -> tuple:
    """Deterministic full-row snapshot of every column of ``model``."""
    result = []
    for row in db.execute(select(model)).mappings():
        result.append(tuple((key, row[key]) for key in sorted(row.keys())))
    return tuple(sorted(result, key=repr))


def _review_snapshot(db: Session) -> tuple:
    return (
        _rows(db, ReviewEvaluation),
        _rows(db, ReviewItem),
        _rows(db, EvidenceLink),
        _rows(db, RunSelectedDocument),
        _rows(db, RunSelectedObservation),
        _rows(db, RunSourceOmission),
        _rows(db, RunGateEvaluation),
        _rows(db, RunGateBlocker),
        _rows(db, AuditEvent),
    )


def _run_review_rows(db: Session, run_id: str) -> tuple:
    return (
        _rows(db, ReviewEvaluation),
        _rows(db, ReviewItem),
        _rows(db, EvidenceLink),
        tuple(row for row in _rows(db, AuditEvent) if dict(row).get("workflow_run_id") == run_id),
    )


def _review_audits(db: Session, run_id: str) -> list[AuditEvent]:
    return list(
        db.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == rb3.RB3_AUDIT_EVENT_TYPE,
                AuditEvent.workflow_run_id == run_id,
            )
        ).scalars()
    )


def _review_audit(db: Session, run_id: str) -> AuditEvent:
    rows = _review_audits(db, run_id)
    assert len(rows) == 1
    return rows[0]


def _gate_audits(db: Session, run_id: str) -> list[AuditEvent]:
    return list(
        db.execute(
            select(AuditEvent).where(
                AuditEvent.event_type == "workflow.gate.evaluated",
                AuditEvent.workflow_run_id == run_id,
            )
        ).scalars()
    )


def _audit_detail(row: AuditEvent) -> dict[str, str]:
    parts = (row.safe_detail or "").split("; ")
    return dict(part.split("=", 1) for part in parts if "=" in part)


def _blocker_set(receipt) -> set[tuple[str, str, str, tuple[str, ...]]]:
    return {
        (issue.issue_type, issue.reason_code, issue.document_id, tuple(issue.fact_ids))
        for issue in receipt.issues
    }


def _gold(case: str) -> dict:
    with (GOLD_DIR / f"GOLD-{case}.expected.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _comparison_fields(comparisons) -> tuple:
    """Field-wise comparison view shared by F2 (V2) and RB1 (preview) DTOs."""
    return tuple(
        (
            item.current_observation_id,
            item.baseline_observation_id,
            item.measure_type,
            item.unit,
            item.comparable,
            item.delta,
            item.incomparable_reason,
            item.trust_basis,
        )
        for item in comparisons
    )


def _item_links(db: Session, run_id: str) -> list[tuple[str, list[str]]]:
    items = (
        db.execute(
            select(ReviewItem)
            .where(ReviewItem.workflow_run_id == run_id)
            .order_by(ReviewItem.display_order)
        )
        .scalars()
        .all()
    )
    out: list[tuple[str, list[str]]] = []
    for item in items:
        links = sorted(
            link.observation_id
            for link in db.execute(
                select(EvidenceLink).where(EvidenceLink.owner_id == item.id)
            ).scalars()
        )
        out.append((item.rule_id, links))
    return out


def _items(db: Session, run_id: str) -> list[ReviewItem]:
    return (
        db.execute(
            select(ReviewItem)
            .where(ReviewItem.workflow_run_id == run_id)
            .order_by(ReviewItem.display_order)
        )
        .scalars()
        .all()
    )


class _Rb2Spy:
    """Observation-only instrumentation: delegate to the unchanged evaluator."""

    def __init__(self, original) -> None:
        self._original = original
        self.calls: list[tuple[OfflineRuleInput, OfflineRuleResult]] = []

    def __call__(self, rule_input: OfflineRuleInput) -> OfflineRuleResult:
        result = self._original(rule_input)
        self.calls.append((rule_input, result))
        return result


def _spy_rb2(monkeypatch: pytest.MonkeyPatch) -> _Rb2Spy:
    original = rb3.evaluate_p4_rb2_offline_fixture
    spy = _Rb2Spy(original)
    monkeypatch.setattr(rb3, "evaluate_p4_rb2_offline_fixture", spy)
    return spy


def _assert_bounded_audit(
    row: AuditEvent, receipt, *, items: int, links: int, exclusions: int
) -> None:
    detail = _audit_detail(row)
    assert tuple(detail) == rb3.RB3_AUDIT_DETAIL_KEYS
    assert len(detail) == 9
    assert detail["fingerprint_version"] == rb3.RB3_FINGERPRINT_VERSION
    assert detail["evaluation_id"] == receipt.evaluation_id
    assert detail["input"] == receipt.input_fingerprint_sha256
    assert detail["output"] == receipt.output_identity_sha256
    assert detail["lineage_label_policy"] == rb3.RB3_LINEAGE_LABEL_POLICY
    assert detail["dr006_policy"] == rb3.RB3_DR006_POLICY
    assert detail["items"] == str(items)
    assert detail["links"] == str(links)
    assert detail["exclusions"] == str(exclusions)
    assert row.safe_detail is not None and len(row.safe_detail) <= 500


def _assert_sealed_evaluation(
    db: Session,
    receipt,
    *,
    patient_id: str,
    doctor_id: str,
    run_id: str,
    items: int,
    links: int,
    exclusions: int,
) -> None:
    """One sealed evaluation, its parent F1 gate and its single audit event."""
    assert receipt.run_id == run_id
    assert receipt.patient_id == patient_id
    assert receipt.doctor_id == doctor_id
    assert receipt.as_of_utc == CLOCK_ISO
    assert receipt.policy_version == "demo-policy-1.1.0"
    assert receipt.policy_reference_sha256 == POLICY_CANONICAL_SHA256
    assert receipt.rb3_fingerprint_version == rb3.RB3_FINGERPRINT_VERSION
    assert receipt.lineage_label_policy == rb3.RB3_LINEAGE_LABEL_POLICY
    assert receipt.dr006_policy == rb3.RB3_DR006_POLICY
    assert receipt.offline_evaluator_invoked is True
    assert receipt.evaluation_completed is True
    assert receipt.runtime_evaluable is False
    assert receipt.policy_status == "unapproved"
    assert receipt.demo_only is True and receipt.not_for_clinical_use is True

    evaluations = (
        db.execute(select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_id))
        .scalars()
        .all()
    )
    assert len(evaluations) == 1
    evaluation = evaluations[0]
    assert evaluation.id == receipt.evaluation_id
    assert evaluation.patient_id == patient_id
    assert evaluation.doctor_id == doctor_id
    assert evaluation.as_of_utc == CLOCK_ISO
    assert evaluation.policy_version == "demo-policy-1.1.0"
    assert evaluation.fingerprint_version == rb3.RB3_FINGERPRINT_VERSION
    assert evaluation.gate_evaluation_id == receipt.gate_evaluation_id
    assert evaluation.gate_version == receipt.gate_version
    assert evaluation.lineage_label_policy == rb3.RB3_LINEAGE_LABEL_POLICY
    assert evaluation.item_count == items == receipt.review_items_total
    assert evaluation.evidence_link_count == links == receipt.evidence_links_total
    assert evaluation.exclusion_count == exclusions
    assert evaluation.audit_event_id == receipt.audit_event_id
    assert evaluation.demo_only == 1

    gate = db.get(RunGateEvaluation, receipt.gate_evaluation_id)
    assert gate is not None
    assert gate.workflow_run_id == run_id
    assert gate.decision == "proceed"
    assert gate.unavailable_reason is None
    assert gate.blocking_fact_count == 0
    assert gate.input_fingerprint_sha256 == receipt.gate_input_fingerprint_sha256
    assert gate.gate_version == receipt.gate_version

    audits = _review_audits(db, run_id)
    assert len(audits) == 1
    audit = audits[0]
    assert audit.id == receipt.audit_event_id
    assert audit.event_type == rb3.RB3_AUDIT_EVENT_TYPE
    assert audit.actor_id == doctor_id
    assert audit.patient_id == patient_id
    assert audit.subject_type == "workflow_run"
    assert audit.subject_id == run_id
    assert audit.outcome == AuditOutcome.OK.value
    _assert_bounded_audit(audit, receipt, items=items, links=links, exclusions=exclusions)


def _assert_observation_links_only(db: Session, run_id: str, *, count: int) -> None:
    """Every persisted link is an observation link owned by one of the run items."""
    item_ids = {item.id for item in _items(db, run_id)}
    assert len(item_ids) == _count(db, ReviewItem)
    links = (
        list(db.execute(select(EvidenceLink).where(EvidenceLink.owner_id.in_(item_ids))).scalars())
        if item_ids
        else []
    )
    assert len(links) == count == _count(db, EvidenceLink)
    assert {link.owner_type for link in links} <= {"review_item"}
    assert all(link.kind == "observation" for link in links)
    assert all(link.observation_id is not None for link in links)
    assert all(link.document_id is None for link in links)
    assert all(link.page_index is None for link in links)
    assert all(link.char_start is None and link.char_end is None for link in links)


# --------------------------------------------------------------------------- #
# GOLD-A — RB4-01
# --------------------------------------------------------------------------- #


def test_rb4_01_gold_a_zero_candidates_after_genuine_run(sandbox, engine, tmp_path, monkeypatch):
    """RB4-01: A stable follow-up -> F0 manifest, F1 PROCEED, zero candidates."""
    db = sandbox
    patient = _patient(db, "DEMO-A-001")
    doctor = _doctor(db, suffix="000000000001")

    # Live November check-in (patient_checkin, self-reported) is NOT seeded.
    checkins = []
    for suffix, (measure, value, unit) in {
        "01": ("systolic_bp", 121, "mmHg"),
        "02": ("diastolic_bp", 78, "mmHg"),
        "03": ("heart_rate", 71, "bpm"),
    }.items():
        checkins.append(
            _add_observation(
                db,
                observation_id=f"a0000000-0000-4000-8000-0000000000{suffix}",
                patient_id=patient.id,
                measure_type=measure,
                value=value,
                unit=unit,
                measured_at="2026-11-01T09:00:00Z",
                created_at=CLOCK_ISO,
                source="patient_checkin",
            )
        )
    gold = _gold("A")
    assert gold["case_id"] == "GOLD-A"
    assert gold["expected_live_checkin_count"] == 3
    assert len(checkins) == 3

    doc, facts = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-a-hemoglobin",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        report_date="2026-10-20",
    )

    # Accepted closed mapping: Hemoglobin + g/dL is deliberately unmapped.
    decision = decide_mapping(
        [
            VerifiedFactView(
                field_name=f.field_name,
                normalized_value=f.normalized_value,
                unit=f.unit,
                verification_status=f.verification_status,
            )
            for f in facts.values()
        ]
    )
    assert decision.mapped is None
    assert decision.reason == "unmapped_test_name"
    assert gold["document_mapping"]["mapped_observations"] == 0

    selected_obs = tuple(sorted(obs.id for obs in checkins))
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=selected_obs,
        request_id="rb4-01-start",
    )

    # Genuine F0 manifest.
    with Session(engine) as check:
        run = check.get(WorkflowRun, run_id)
        assert run is not None and run.status == "queued"
        assert run.doctor_id == doctor.user_id
        assert run.patient_id == patient.id
        assert set(
            check.execute(
                select(RunSelectedObservation.observation_id).where(
                    RunSelectedObservation.workflow_run_id == run_id
                )
            ).scalars()
        ) == set(selected_obs)
        assert (
            check.scalar(
                select(func.count())
                .select_from(RunSelectedDocument)
                .where(RunSelectedDocument.workflow_run_id == run_id)
            )
            == 1
        )

    gate = _gate(engine, doctor, run_id, tmp_path)
    assert gate.decision == "proceed"
    assert gate.issues == ()
    assert gate.blocking_fact_count == 0
    assert gate.unavailable_reason is None

    evidence = _evidence(engine, doctor, run_id, tmp_path)
    assert evidence.selected_observation_ids == selected_obs
    assert len(evidence.selected_observations) == 3
    assert evidence.history_exclusions == ()
    assert {c.current_observation_id for c in evidence.comparisons} == set(selected_obs)

    # Correct historical comparisons (signed current - most recent prior).
    by_measure = {c.measure_type: c for c in evidence.comparisons}
    # Most recent prior comparable baseline is the 2026-10-15 seeded reading.
    assert by_measure["systolic_bp"].baseline_observation_id == (
        "dc761a21-db6b-5507-b417-873d195f2876"
    )
    assert by_measure["systolic_bp"].delta == 1
    assert by_measure["diastolic_bp"].baseline_observation_id == (
        "7b03ed68-05cb-5dea-89f1-6497d2fb9164"
    )
    assert by_measure["diastolic_bp"].delta == -1
    assert by_measure["heart_rate"].baseline_observation_id == (
        "1f52b79b-b796-5976-8990-78a15626149c"
    )
    assert by_measure["heart_rate"].delta == -3
    assert {c.trust_basis for c in evidence.comparisons} == {"self_reported"}

    preview = _preview(engine, doctor, run_id, tmp_path)
    assert _comparison_fields(preview.policy_comparisons) == _comparison_fields(
        evidence.comparisons
    )
    assert preview.no_current_reason is None

    # No mapped hemoglobin observation was produced by the closed mapping.
    with Session(engine) as check:
        assert (
            check.scalar(
                select(func.count())
                .select_from(Observation)
                .where(Observation.source_fact_id == facts["value"].id)
            )
            == 0
        )

    spy = _spy_rb2(monkeypatch)
    before = _review_counts(db)
    first = _persist(engine, doctor, run_id, tmp_path)
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total == 0
    assert first.evidence_links_persisted == first.evidence_links_total == 0
    assert first.lineage_label_policy == "a2_transport_label"
    assert first.dr006_policy == "prohibited_denied"
    assert first.evaluation_completed is True
    assert first.runtime_evaluable is False
    # Zero rule candidates from the actual unchanged evaluator.
    assert len(spy.calls) == 1
    assert spy.calls[0][1].flags == ()

    after = _review_counts(db)
    assert after == (before[0], before[1], before[2] + 1, before[3] + 1)

    with Session(engine) as check:
        evaluation = check.execute(
            select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_id)
        ).scalar_one()
        assert evaluation.item_count == 0
        assert evaluation.evidence_link_count == 0
        assert evaluation.patient_id == patient.id
        assert evaluation.doctor_id == doctor.user_id
        assert evaluation.policy_version == "demo-policy-1.1.0"
        assert evaluation.policy_reference_sha256 == POLICY_CANONICAL_SHA256
        assert POLICY_CANONICAL_SHA256 == (
            "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
        )
        _assert_sealed_evaluation(
            check,
            first,
            patient_id=patient.id,
            doctor_id=doctor.user_id,
            run_id=run_id,
            items=0,
            links=0,
            exclusions=0,
        )
        _assert_observation_links_only(check, run_id, count=0)
        # The run stays queued: evaluation completion is not workflow completion.
        assert check.get(WorkflowRun, run_id).status == "queued"

    snapshot = _review_snapshot(db)
    second = _persist(engine, doctor, run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.evidence_links_persisted == 0
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert second.input_fingerprint_sha256 == first.input_fingerprint_sha256
    assert second.output_identity_sha256 == first.output_identity_sha256
    assert _review_snapshot(db) == snapshot

    gold_rule_ids = gold["expected_review_rule_ids"]
    assert gold_rule_ids == [] and gold["expected_review_count"] == 0
    with Session(engine) as check:
        assert _item_links(check, run_id) == []


# --------------------------------------------------------------------------- #
# GOLD-B — RB4-02 (+ RB4-08 bridge)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _GoldB:
    patient: Patient
    doctor: Principal
    document: Document
    value_fact: ExtractedFact
    glucose_observation: Observation
    selected: tuple[str, ...]
    run_id: str


def _setup_gold_b(db: Session, engine, tmp_path: Path, monkeypatch) -> _GoldB:
    patient = _patient(db, "DEMO-B-001")
    doctor = _doctor(db, suffix="000000000002")
    doc, facts = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-b-fasting-glucose",
        test_name="Fasting glucose",
        value="104",
        unit="mg/dL",
        report_date="2026-11-02",
    )
    glucose_observation, mapping = _mapped_observation_from_mapping(
        db,
        observation_id="b0000000-0000-4000-8000-000000000001",
        patient_id=patient.id,
        document=doc,
        facts=list(facts.values()),
        doctor_user_id=doctor.user_id,
    )
    gold = _gold("B")
    assert mapping.mapped is not None
    assert mapping.mapped.measure_type.value == "glucose"
    assert mapping.mapped.value == float(gold["document_mapping"]["value"])
    assert mapping.mapped.unit == gold["document_mapping"]["unit"]
    assert mapping.mapped.measured_at == gold["document_mapping"]["measured_at"]

    selected = (
        "a86e3fd9-e88f-551a-8041-46405097df6c",  # systolic 158 @ 2026-11-03 08:25
        "6becf300-30e3-55e0-b6c2-94a40eae9fae",  # diastolic 96 @ 2026-11-03 08:25
        "4738eb4f-edba-5e5b-9a6d-ea5e680500ce",  # heart rate 84 @ 2026-11-03 08:25
        glucose_observation.id,  # mapped glucose 104 @ 2026-11-02 00:00
    )
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=selected,
        request_id="rb4-02-start",
    )
    return _GoldB(
        patient=patient,
        doctor=doctor,
        document=doc,
        value_fact=facts["value"],
        glucose_observation=glucose_observation,
        selected=selected,
        run_id=run_id,
    )


def test_rb4_02_gold_b_exact_dr005_self_reported(sandbox, engine, tmp_path, monkeypatch):
    """RB4-02: B exact seeded values/times, one self-reported DR-005, 2 links."""
    db = sandbox
    b = _setup_gold_b(db, engine, tmp_path, monkeypatch)
    gold = _gold("B")

    gate = _gate(engine, b.doctor, b.run_id, tmp_path)
    assert gate.decision == "proceed"
    assert gate.issues == ()
    assert gate.blocking_fact_count == 0

    evidence = _evidence(engine, b.doctor, b.run_id, tmp_path)
    assert set(evidence.selected_observation_ids) == set(b.selected)
    assert set(evidence.selected_document_ids) == {b.document.id}
    assert evidence.history_exclusions == ()
    comparison = {
        c.measure_type: c for c in evidence.comparisons if c.measure_type == "systolic_bp"
    }
    sys_cmp = comparison["systolic_bp"]
    assert sys_cmp.current_observation_id == "a86e3fd9-e88f-551a-8041-46405097df6c"
    assert sys_cmp.baseline_observation_id == "4db31c0e-dc9c-5695-ad2f-ed612f80e308"
    assert sys_cmp.delta == 12
    assert sys_cmp.trust_basis == "self_reported"
    glucose_cmp = next(c for c in evidence.comparisons if c.measure_type == "glucose")
    assert glucose_cmp.baseline_observation_id == "0b55bc42-bfe4-570f-acfb-f98dfea56a87"
    assert glucose_cmp.delta == 6
    assert glucose_cmp.trust_basis == "mixed"

    preview = _preview(engine, b.doctor, b.run_id, tmp_path)
    assert _comparison_fields(preview.policy_comparisons) == _comparison_fields(
        evidence.comparisons
    )

    spy = _spy_rb2(monkeypatch)
    first = _persist(engine, b.doctor, b.run_id, tmp_path)
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total == 1
    assert first.evidence_links_persisted == first.evidence_links_total == 2
    assert first.lineage_label_policy == "a2_transport_label"
    assert first.dr006_policy == "prohibited_denied"

    assert len(spy.calls) == 1
    captured_input, captured_result = spy.calls[0]
    assert captured_input.patient_id == b.patient.id
    assert len(captured_input.selected_current) == 4
    assert captured_result.flags[0].rule_id == "DR-005"

    expected = gold["expected_dr005"]
    assert gold["expected_review_rule_ids"] == ["DR-005"]
    assert gold["expected_review_count"] == 1
    with Session(engine) as check:
        items = _items(check, b.run_id)
        assert len(items) == 1
        item = items[0]
        assert item.display_order == 0
        assert item.rule_id == "DR-005"
        assert item.reason_code == "change_exceeds_demo_parameter"
        assert item.workflow_hint == "change_to_review"
        assert item.trust_basis == expected["trust_basis"] == "self_reported"
        assert item.message == expected["message"]
        assert item.provenance_status == "fixture_asserted"
        assert item.stored_lineage_proved == 0
        assert item.demo_only == 1
        assert item.state == "open"
        links = _item_links(check, b.run_id)
        assert links == [
            (
                "DR-005",
                [
                    "4db31c0e-dc9c-5695-ad2f-ed612f80e308",
                    "a86e3fd9-e88f-551a-8041-46405097df6c",
                ],
            )
        ]
        # Frozen semantic dedupe key over patient|rule|evidence|trust.
        expected_dedupe = hashlib.sha256(
            "|".join(
                (
                    b.patient.id,
                    "DR-005",
                    "observation:4db31c0e-dc9c-5695-ad2f-ed612f80e308",
                    "observation:a86e3fd9-e88f-551a-8041-46405097df6c",
                    "self_reported",
                )
            ).encode()
        ).hexdigest()
        assert item.dedupe_key == expected_dedupe
        _assert_sealed_evaluation(
            check,
            first,
            patient_id=b.patient.id,
            doctor_id=b.doctor.user_id,
            run_id=b.run_id,
            items=1,
            links=2,
            exclusions=0,
        )
        _assert_observation_links_only(check, b.run_id, count=2)

    snapshot = _review_snapshot(db)
    second = _persist(engine, b.doctor, b.run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.evidence_links_persisted == 0
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert second.input_fingerprint_sha256 == first.input_fingerprint_sha256
    assert second.output_identity_sha256 == first.output_identity_sha256
    assert _review_snapshot(db) == snapshot

    # The doctor-verified glucose never upgrades the unrelated systolic trust.
    with Session(engine) as check:
        glucose = check.get(Observation, b.glucose_observation.id)
        assert glucose is not None
        assert glucose.trust_level == "doctor_verified"
        assert glucose.source == "verified_document"
        assert glucose.source_fact_id == b.value_fact.id
        assert glucose.verified_by_user_id == b.doctor.user_id
        items = _items(check, b.run_id)
        assert [i.trust_basis for i in items] == ["self_reported"]
        assert [i.stored_lineage_proved for i in items] == [0]


# --------------------------------------------------------------------------- #
# GOLD-C initial refusal — RB4-03
# --------------------------------------------------------------------------- #


def test_rb4_03_gold_c_initial_pending_document_is_refused_before_run(sandbox, engine, tmp_path):
    """RB4-03: pending C document -> genuine F0 refusal before any run insert."""
    db = sandbox
    patient = _patient(db, "DEMO-C-001")
    doctor = _doctor(db, suffix="000000000003")
    gold = _gold("C")

    pending_facts = [
        _Fact(
            "report_date",
            "03/11/2026",
            None,
            status="pending",
            flags='["ambiguous_date"]',
            decision=None,
        ),
        _Fact("test_name", "Glucose", "Glucose", status="pending", decision=None),
        _Fact(
            "value",
            "1O5",
            None,
            unit=None,
            status="pending",
            flags='["low_confidence","ambiguous_unit"]',
            decision=None,
        ),
    ]
    doc, created = _add_document(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-c-pending",
        facts=pending_facts,
        status="needs_verification",
    )
    assert len(created) == 3

    # Exercise the actual P3 issue synchronization (the only writer of issues).
    open_issues = quality.sync_issues(db, document=doc, conflict_tolerance=0.0)
    issue_types = {issue.issue_type for issue in open_issues}
    assert issue_types == set(gold["pre_verification"]["expected_open_verification_issue_ids"])
    assert issue_types == {"VI-001", "VI-002", "VI-003", "VI-005"}
    vi002 = next(issue for issue in open_issues if issue.issue_type == "VI-002")
    assert vi002.message == gold["pre_verification"]["expected_unverified_message"]
    assert vi002.message == "3 extracted value(s) are not yet verified."
    pending_count = sum(1 for fact in created if fact.verification_status != "verified")
    assert pending_count == gold["pre_verification"]["pending_active_fact_count"] == 3

    # Selected-document preflight is genuinely blocked (not fabricated).
    preflight = inspect_selected_document_verification(
        db,
        principal=doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
    )
    assert preflight.candidate_documents_clear is False
    assert {block.reason_code for block in preflight.blockers} >= {
        "active_fact_unverified",
        "open_verification_issue",
        "document_not_verified",
    }

    before = (
        _review_snapshot(db),
        _count(db, WorkflowRun),
        _count(db, ReviewEvaluation),
        _count(db, ReviewItem),
        _count(db, EvidenceLink),
    )
    with pytest.raises(ApiError) as exc:
        _start(
            engine,
            doctor,
            patient_id=patient.id,
            document_ids=(doc.id,),
            observation_ids=(),
            request_id="rb4-03-refusal",
        )
    assert exc.value.status_code == 409
    assert exc.value.code == ErrorCode.VALIDATION

    after = (
        _review_snapshot(db),
        _count(db, WorkflowRun),
        _count(db, ReviewEvaluation),
        _count(db, ReviewItem),
        _count(db, EvidenceLink),
    )
    assert after == before
    assert _count(db, WorkflowRun) == 0
    # No F1 decision can exist for a run that was never created.
    assert _count(db, RunGateEvaluation) == 0
    assert _count(db, RunGateBlocker) == 0
    # No downstream review persistence audit was written.
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.event_type == rb3.RB3_AUDIT_EVENT_TYPE)
        )
        == 0
    )


# --------------------------------------------------------------------------- #
# GOLD-C controlled deterioration — RB4-04 (+ RB4-11 blocked half)
# --------------------------------------------------------------------------- #


def _deteriorate_to_pending(document: Document, facts: dict[str, ExtractedFact]) -> None:
    """Controlled post-selection deterioration (disclosed synthetic setup).

    The document keeps ``extraction_status='verified'`` solely to isolate the
    F1 blocker branch; it does not reproduce the original OCR lifecycle.
    """
    document.extraction_status = "verified"
    document.failure_code = None
    report_date = facts["report_date"]
    test_name = facts["test_name"]
    value = facts["value"]
    report_date.verification_status = "pending"
    report_date.normalized_value = None
    report_date.quality_flags = '["ambiguous_date"]'
    test_name.verification_status = "pending"
    value.verification_status = "pending"
    value.normalized_value = None
    value.unit = None
    value.quality_flags = '["low_confidence","ambiguous_unit"]'


def test_rb4_04_gold_c_controlled_post_selection_deterioration_halts(
    sandbox, engine, tmp_path, monkeypatch
):
    """RB4-04: genuine run, controlled F1 HALT, zero RB2 invocation/writes."""
    db = sandbox
    patient = _patient(db, "DEMO-C-001")
    doctor = _doctor(db, suffix="000000000004")

    # Clear, unmapped scaffold so the run is genuinely valid before deterioration.
    doc, facts = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-c-deterioration",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        report_date="2026-10-20",
    )
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(),
        request_id="rb4-04-start",
    )
    initial = _gate(engine, doctor, run_id, tmp_path)
    assert initial.decision == "proceed"
    assert initial.issues == ()

    # Controlled post-selection deterioration (disclosed synthetic setup).
    _deteriorate_to_pending(doc, facts)
    db.commit()

    spy = _spy_rb2(monkeypatch)
    with pytest.raises(ApiError) as denied:
        _persist(engine, doctor, run_id, tmp_path)
    assert denied.value.status_code == 409
    assert denied.value.code == ErrorCode.VALIDATION
    assert spy.calls == []

    # Genuine F1 HALT (not a fabricated decision for the initial pending state).
    halt = _gate(engine, doctor, run_id, tmp_path)
    assert halt.decision == "halt"
    assert halt.unavailable_reason is None
    blockers = _blocker_set(halt)
    report_date_id = facts["report_date"].id
    test_name_id = facts["test_name"].id
    value_id = facts["value"].id
    assert blockers == {
        ("VI-001", "unit_missing_or_unsupported", doc.id, ()),
        ("VI-001", "unit_missing_or_unsupported", doc.id, (value_id,)),
        (
            "VI-002",
            "fact_unverified",
            doc.id,
            tuple(sorted((report_date_id, test_name_id, value_id))),
        ),
        ("VI-003", "date_ambiguous", doc.id, ()),
        ("VI-003", "date_ambiguous", doc.id, (report_date_id,)),
        ("VI-005", "value_unreadable", doc.id, (value_id,)),
    }
    assert {issue.issue_type for issue in halt.issues} == {
        "VI-001",
        "VI-002",
        "VI-003",
        "VI-005",
    }

    with Session(engine) as check:
        gate_rows = (
            check.execute(
                select(RunGateEvaluation).where(RunGateEvaluation.workflow_run_id == run_id)
            )
            .scalars()
            .all()
        )
        assert {row.decision for row in gate_rows} == {"proceed", "halt"}
        gate_audits = _gate_audits(check, run_id)
        assert len(gate_audits) == 2
        assert {row.safe_detail for row in gate_audits} >= {
            "phase=p5-f1; decision=proceed; runtime_evaluable=false",
            "phase=p5-f1; decision=halt; runtime_evaluable=false",
        }
        # Distinguish real gate audit evidence from denied review writes.
        assert (
            check.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.event_type == rb3.RB3_AUDIT_EVENT_TYPE)
            )
            == 0
        )
        assert _count(check, ReviewEvaluation) == 0
        assert _count(check, ReviewItem) == 0
        assert _count(check, EvidenceLink) == 0
        # No review-persistence audit was written for the denied invocation.
        assert (
            check.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.event_type == rb3.RB3_AUDIT_EVENT_TYPE,
                    AuditEvent.workflow_run_id == run_id,
                )
            )
            == 0
        )
        # The stored blocker rows are the exact F1 evidence.
        stored_blockers = {
            (
                row.issue_type,
                row.reason_code,
                row.document_id,
                tuple(json.loads(row.fact_ids)),
            )
            for row in check.execute(
                select(RunGateBlocker).where(
                    RunGateBlocker.gate_evaluation_id.in_(
                        [row.id for row in gate_rows if row.decision == "halt"]
                    )
                )
            ).scalars()
        }
        assert stored_blockers == blockers


def test_rb4_11_blocked_run_has_no_rb2_call_or_review_persistence(
    sandbox, engine, tmp_path, monkeypatch
):
    """RB4-11: a HALT run never invokes RB2 nor writes review rows.

    DR-006 end-to-end reachability is NOT claimed. The accepted direct boundary
    regression (RB3-66/99) is cited separately as supporting evidence only.
    """
    db = sandbox
    patient = _patient(db, "DEMO-C-001")
    doctor = _doctor(db, suffix="000000000005")
    doc, facts = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-c-blocked",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        report_date="2026-10-20",
    )
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(),
        request_id="rb4-11-start",
    )
    _deteriorate_to_pending(doc, facts)
    db.commit()
    assert _gate(engine, doctor, run_id, tmp_path).decision == "halt"

    spy = _spy_rb2(monkeypatch)
    before = _review_snapshot(db)
    with pytest.raises(ApiError) as exc:
        _persist(engine, doctor, run_id, tmp_path)
    assert exc.value.status_code == 409
    assert spy.calls == []
    assert _review_snapshot(db) == before

    # Separately attributed existing DR-006 boundary regression evidence.
    # Cited, not re-executed here: RB4 does not duplicate the RB3 matrix and
    # does not claim genuine DR-006 reachability.
    rb3_service_tests = (
        REPO_ROOT / "backend" / "tests" / "p4" / "test_p4_rb3_review_persistence.py"
    ).read_text(encoding="utf-8")
    assert (
        "def test_rb3_66_99_dr006_unit_level_boundary_denies_whole_invocation" in rb3_service_tests
    )
    assert "DR006_PERSISTENCE_NOT_AUTHORIZED" in rb3_service_tests
    assert RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED.value == (
        "dr006_persistence_not_authorized"
    )
    # This file asserts the blocked-run half only; it does not assert that a
    # genuine F1-PROCEED source reaches DR-006, and it never persists DR-006.
    with Session(engine) as check:
        assert _count(check, ReviewItem) == 0
        assert _count(check, EvidenceLink) == 0


# --------------------------------------------------------------------------- #
# GOLD-C corrected new run — RB4-05
# --------------------------------------------------------------------------- #


def _setup_gold_c_corrected(db: Session, engine, tmp_path: Path, monkeypatch):
    patient = _patient(db, "DEMO-C-001")
    doctor = _doctor(db, suffix="000000000006")

    # Rejected originals (preserved) + explicitly scripted correction lineage.
    original_specs = [
        _Fact(
            "report_date",
            "03/11/2026",
            None,
            status="rejected",
            flags='["ambiguous_date"]',
            decision="corrected",
            new_value="2026-11-03",
        ),
        _Fact(
            "test_name",
            "Glucose",
            "Glucose",
            status="rejected",
            decision="corrected",
            new_value="Glucose",
        ),
        _Fact(
            "value",
            "1O5",
            None,
            unit=None,
            status="rejected",
            flags='["low_confidence","ambiguous_unit"]',
            decision="corrected",
            new_value="105",
            new_unit="mg/dL",
        ),
    ]
    doc, originals = _add_document(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-c-corrected",
        facts=original_specs,
        status="needs_verification",
    )
    original_by_field = {fact.field_name: fact for fact in originals}

    # Exercise actual P3 issue synchronization on the pending originals first,
    # so the later correction resolves real issue rows through accepted logic.
    pre_issues = quality.sync_issues(db, document=doc, conflict_tolerance=0.0)
    assert {issue.issue_type for issue in pre_issues} == {
        "VI-001",
        "VI-002",
        "VI-003",
        "VI-005",
    }

    # Explicitly scripted synthetic verification: corrected replacements.
    corrected_specs = [
        _Fact(
            "report_date",
            "03/11/2026",
            "2026-11-03",
            corrected_from=original_by_field["report_date"].id,
            decision=None,
        ),
        _Fact(
            "test_name",
            "Glucose",
            "Glucose",
            corrected_from=original_by_field["test_name"].id,
            decision=None,
        ),
        _Fact(
            "value",
            "1O5",
            "105",
            unit="mg/dL",
            corrected_from=original_by_field["value"].id,
            decision=None,
        ),
    ]
    corrected: list[ExtractedFact] = []
    for spec in corrected_specs:
        fact = ExtractedFact(
            document_id=doc.id,
            patient_id=patient.id,
            field_name=spec.field,
            raw_text=spec.raw,
            normalized_value=spec.normalized,
            unit=spec.unit,
            page_index=0,
            char_start=0,
            char_end=max(len(spec.raw), 1),
            verification_status="verified",
            quality_flags="[]",
            corrected_from_fact_id=spec.corrected_from,
            created_at=AT_ISO,
        )
        db.add(fact)
        db.flush()
        corrected.append(fact)
    doc.extraction_status = "verified"
    doc.failure_code = None
    db.commit()

    # Resolve issues through accepted logic (sync moves them to resolved).
    open_issues = quality.sync_issues(db, document=doc, conflict_tolerance=0.0)
    assert open_issues == ()
    all_issues = (
        db.execute(select(VerificationIssue).where(VerificationIssue.document_id == doc.id))
        .scalars()
        .all()
    )
    assert all(issue.state == "resolved" for issue in all_issues)
    assert {issue.issue_type for issue in all_issues} == {"VI-001", "VI-002", "VI-003", "VI-005"}

    corrected_by_field = {fact.field_name: fact for fact in corrected}
    glucose_observation, mapping = _mapped_observation_from_mapping(
        db,
        observation_id="c0000000-0000-4000-8000-000000000001",
        patient_id=patient.id,
        document=doc,
        facts=corrected,
        doctor_user_id=doctor.user_id,
    )
    assert mapping.mapped is not None
    assert mapping.mapped.value == 105
    assert mapping.mapped.measured_at == "2026-11-03T00:00:00Z"

    # NEW genuine run after correction (not a resume of a never-created run).
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(glucose_observation.id,),
        request_id="rb4-05-start",
    )
    return patient, doctor, doc, corrected_by_field, originals, glucose_observation, run_id


def test_rb4_05_gold_c_corrected_new_run_proceeds_zero_candidates(
    sandbox, engine, tmp_path, monkeypatch
):
    """RB4-05: corrected lineage -> new run, fresh PROCEED, mixed delta 9."""
    db = sandbox
    (
        patient,
        doctor,
        _doc,
        corrected,
        originals,
        glucose_observation,
        run_id,
    ) = _setup_gold_c_corrected(db, engine, tmp_path, monkeypatch)
    gold = _gold("C")["post_fixture_correction"]

    # Rejected originals preserved with correction lineage.
    with Session(engine) as check:
        for original in originals:
            stored = check.get(ExtractedFact, original.id)
            assert stored is not None and stored.verification_status == "rejected"
        for fact in corrected.values():
            stored = check.get(ExtractedFact, fact.id)
            assert stored is not None and stored.verification_status == "verified"
            decision = check.execute(
                select(FactVerification).where(
                    FactVerification.fact_id == stored.corrected_from_fact_id
                )
            ).scalar_one()
            assert decision.decision == "corrected"
            assert decision.new_value == stored.normalized_value

    gate = _gate(engine, doctor, run_id, tmp_path)
    assert gate.decision == "proceed"
    assert gate.issues == ()
    assert gate.blocking_fact_count == 0

    evidence = _evidence(engine, doctor, run_id, tmp_path)
    assert set(evidence.selected_observation_ids) == {glucose_observation.id}
    comparison = evidence.comparisons[0]
    assert comparison.measure_type == "glucose"
    assert comparison.trust_basis == "mixed"
    assert comparison.delta == 9
    assert comparison.comparable is True

    preview = _preview(engine, doctor, run_id, tmp_path)
    assert _comparison_fields(preview.policy_comparisons) == _comparison_fields(
        evidence.comparisons
    )

    spy = _spy_rb2(monkeypatch)
    first = _persist(engine, doctor, run_id, tmp_path)
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total == 0
    assert first.evidence_links_persisted == first.evidence_links_total == 0
    assert len(spy.calls) == 1 and spy.calls[0][1].flags == ()
    assert gold["expected_review_rule_ids"] == []
    assert gold["expected_delta"] == 9
    assert gold["trust_basis"] == "mixed"

    with Session(engine) as check:
        assert _items(check, run_id) == []
        evaluation = check.execute(
            select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_id)
        ).scalar_one()
        assert evaluation.item_count == 0
        _assert_sealed_evaluation(
            check,
            first,
            patient_id=patient.id,
            doctor_id=doctor.user_id,
            run_id=run_id,
            items=0,
            links=0,
            exclusions=0,
        )
        _assert_observation_links_only(check, run_id, count=0)

    snapshot = _review_snapshot(db)
    second = _persist(engine, doctor, run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.evidence_links_persisted == 0
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert _review_snapshot(db) == snapshot

    # Scripted correction is not real OCR success.
    assert _gold("C")["real_ocr_result"].startswith("GOLD-EX-11 FAIL / NOT PROVEN")


# --------------------------------------------------------------------------- #
# GOLD-D — RB4-06 (+ RB4-08 reorder)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _GoldD:
    patient: Patient
    doctor: Principal
    hr: Observation
    sys_128: Observation
    dia_82: Observation
    sys_130_a: Observation
    sys_130_b: Observation
    dia_250: Observation
    run_id: str


def _setup_gold_d(db: Session, engine, tmp_path: Path, monkeypatch) -> _GoldD:
    patient = _patient_d(db)
    doctor = _doctor(db, suffix="000000000007")
    hr = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000001",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=68,
        unit="bpm",
        measured_at="2026-09-01T09:00:00Z",
    )
    sys_128 = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000002",
        patient_id=patient.id,
        measure_type="systolic_bp",
        value=128,
        unit="mmHg",
        measured_at="2026-10-05T09:00:00Z",
    )
    dia_82 = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000003",
        patient_id=patient.id,
        measure_type="diastolic_bp",
        value=82,
        unit="mmHg",
        measured_at="2026-10-05T09:00:00Z",
    )
    sys_130_a = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000004",
        patient_id=patient.id,
        measure_type="systolic_bp",
        value=130,
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
    )
    sys_130_b = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000005",
        patient_id=patient.id,
        measure_type="systolic_bp",
        value=130,
        unit="mmHg",
        measured_at="2026-10-20T09:00:00Z",
    )
    dia_250 = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000006",
        patient_id=patient.id,
        measure_type="diastolic_bp",
        value=250,
        unit="mmHg",
        measured_at="2026-10-25T09:00:00Z",
        validation="ok_with_warning",
    )
    # Clear patient-scoped unmapped scaffold document (F0 requires a document).
    scaffold, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="gold-d-scaffold",
        test_name="Hemoglobin",
        value="13.9",
        unit="g/dL",
        report_date="2026-11-01",
    )
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(scaffold.id,),
        observation_ids=(hr.id, sys_130_a.id, dia_250.id),
        request_id="rb4-06-start",
    )
    return _GoldD(
        patient=patient,
        doctor=doctor,
        hr=hr,
        sys_128=sys_128,
        dia_82=dia_82,
        sys_130_a=sys_130_a,
        sys_130_b=sys_130_b,
        dia_250=dia_250,
        run_id=run_id,
    )


def test_rb4_06_gold_d_exact_ordered_outputs_and_replay(sandbox, engine, tmp_path, monkeypatch):
    """RB4-06: D exact five ordered flags, seven links, deterministic reorder."""
    db = sandbox
    d = _setup_gold_d(db, engine, tmp_path, monkeypatch)
    gold = _gold("D")
    assert gold["patient_id"] == d.patient.id == D_PATIENT_ID

    gate = _gate(engine, d.doctor, d.run_id, tmp_path)
    assert gate.decision == "proceed"
    assert gate.issues == ()

    with Session(engine) as check:
        six = [d.hr.id, d.sys_128.id, d.dia_82.id, d.sys_130_a.id, d.sys_130_b.id, d.dia_250.id]
        rows = [check.get(Observation, oid) for oid in six]
        assert all(row is not None for row in rows)
        assert all(row.source == "seed_fixture" for row in rows)
        assert all(row.trust_level == "self_reported_validated" for row in rows)
        # Equal created times: no accidental out-of-order event is introduced.
        assert {row.created_at for row in rows} == {CLOCK_ISO}
        # The implausible diastolic row is admissible history/current input.
        assert check.get(Observation, d.dia_250.id).validation == "ok_with_warning"
        assert (
            gold["expected_duplicate"]["value"]
            == check.get(Observation, d.sys_130_a.id).value
            == check.get(Observation, d.sys_130_b.id).value
        )
        assert (
            gold["expected_duplicate"]["measured_at"]
            == check.get(Observation, d.sys_130_a.id).measured_at
        )

    evidence = _evidence(engine, d.doctor, d.run_id, tmp_path)
    assert set(evidence.selected_observation_ids) == {d.hr.id, d.sys_130_a.id, d.dia_250.id}
    assert evidence.history_exclusions == ()
    dia_cmp = next(c for c in evidence.comparisons if c.measure_type == "diastolic_bp")
    assert dia_cmp.current_observation_id == d.dia_250.id
    assert dia_cmp.baseline_observation_id == d.dia_82.id
    assert dia_cmp.delta == gold["expected_deltas"]["diastolic_bp"] == 168

    preview = _preview(engine, d.doctor, d.run_id, tmp_path)
    assert _comparison_fields(preview.policy_comparisons) == _comparison_fields(
        evidence.comparisons
    )

    spy = _spy_rb2(monkeypatch)
    first = _persist(engine, d.doctor, d.run_id, tmp_path)
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total == 5
    assert first.evidence_links_persisted == first.evidence_links_total == 7
    assert len(spy.calls) == 1

    with Session(engine) as check:
        links = _item_links(check, d.run_id)
        assert links == [
            ("DR-001", [d.hr.id]),
            ("DR-003", [d.hr.id]),
            ("DR-008", sorted([d.sys_130_a.id, d.sys_130_b.id])),
            ("DR-009", [d.dia_250.id]),
            ("DR-005", sorted([d.dia_82.id, d.dia_250.id])),
        ]
        items = _items(check, d.run_id)
        assert [item.display_order for item in items] == [0, 1, 2, 3, 4]
        assert all(item.provenance_status == "fixture_asserted" for item in items)
        assert all(item.stored_lineage_proved == 0 for item in items)
        assert all(item.trust_basis == "self_reported" for item in items)
        assert all(item.demo_only == 1 for item in items)
        assert all(item.state == "open" for item in items)
        by_rule = {item.rule_id: item for item in items}
        assert set(by_rule) == set(gold["expected_review_rule_ids"])
        assert len(items) == gold["expected_review_count"] == 5
        # Each rule maps to the frozen measure type via its evidence links.
        for item in items:
            measures = {
                check.get(Observation, link.observation_id).measure_type
                for link in check.execute(
                    select(EvidenceLink).where(EvidenceLink.owner_id == item.id)
                ).scalars()
            }
            assert measures == {gold["expected_by_rule"][item.rule_id]}
        # Exact semantic dedupe keys over patient|rule|sorted observation refs|trust.
        for item in items:
            refs = sorted(
                f"observation:{link.observation_id}"
                for link in check.execute(
                    select(EvidenceLink).where(EvidenceLink.owner_id == item.id)
                ).scalars()
            )
            expected_dedupe = hashlib.sha256(
                "|".join((d.patient.id, item.rule_id, *refs, item.trust_basis)).encode()
            ).hexdigest()
            assert item.dedupe_key == expected_dedupe
        assert by_rule["DR-008"].message == (
            "A repeated or out-of-order entry was detected for Systolic BP (self-reported)."
        )
        assert by_rule["DR-009"].message == (
            "A recorded value is outside the demo plausibility range and may be a typo "
            "(self-reported)."
        )
        _assert_sealed_evaluation(
            check,
            first,
            patient_id=d.patient.id,
            doctor_id=d.doctor.user_id,
            run_id=d.run_id,
            items=5,
            links=7,
            exclusions=0,
        )
        _assert_observation_links_only(check, d.run_id, count=7)

    # Deterministic output under reordered inputs with unchanged identities.
    captured_input, captured_result = spy.calls[0]
    reordered = OfflineRuleInput(
        patient_id=captured_input.patient_id,
        selected_current=tuple(reversed(captured_input.selected_current)),
        history=tuple(reversed(captured_input.history)),
        as_of_utc=captured_input.as_of_utc,
        policy=captured_input.policy,
        active_fact_verification_statuses=captured_input.active_fact_verification_statuses,
    )
    reordered_result = evaluate_p4_rb2_offline_fixture(reordered)
    assert reordered_result.flags == captured_result.flags

    snapshot = _review_snapshot(db)
    second = _persist(engine, d.doctor, d.run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.evidence_links_persisted == 0
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert _review_snapshot(db) == snapshot

    # Distinct duplicate identity and delta, per frozen JSON.
    assert d.sys_130_a.id != d.sys_130_b.id
    assert gold["expected_duplicate"]["distinct_observation_ids"] == 2
    assert gold["expected_deltas"]["diastolic_bp"] == 168


# --------------------------------------------------------------------------- #
# RB4-08 semantic RB2 -> RB3 equivalence (B and D)
# --------------------------------------------------------------------------- #


def test_rb4_08_semantic_bridge_equivalence_for_b_and_d(sandbox, engine, tmp_path, monkeypatch):
    """RB4-08: persisted semantics equal the actual unchanged RB2 execution."""
    db = sandbox
    b = _setup_gold_b(db, engine, tmp_path, monkeypatch)
    assert _gate(engine, b.doctor, b.run_id, tmp_path).decision == "proceed"
    spy = _spy_rb2(monkeypatch)
    _persist(engine, b.doctor, b.run_id, tmp_path)
    assert len(spy.calls) == 1
    _b_input, b_result = spy.calls[0]
    with Session(engine) as check:
        rows = _items(check, b.run_id)
        assert len(rows) == len(b_result.flags)
        for row, flag in zip(rows, b_result.flags, strict=True):
            assert row.rule_id == flag.rule_id
            assert row.reason_code == flag.reason_code
            assert row.workflow_hint == flag.workflow_hint
            assert row.trust_basis == flag.trust_basis
            assert row.message == flag.message
            assert row.policy_version == flag.policy_version
            assert row.dedupe_key == flag.dedupe_key
            assert row.provenance_status == flag.provenance_status
            assert sorted(
                link.observation_id
                for link in check.execute(
                    select(EvidenceLink).where(EvidenceLink.owner_id == row.id)
                ).scalars()
            ) == sorted(ref.removeprefix("observation:") for ref in flag.evidence)
        # A2 transport label and per-item lineage proof are correctly separated.
        assert all(row.provenance_status == "fixture_asserted" for row in rows)
        assert all(row.stored_lineage_proved == 0 for row in rows)

    d = _setup_gold_d(db, engine, tmp_path, monkeypatch)
    assert _gate(engine, d.doctor, d.run_id, tmp_path).decision == "proceed"
    spy.calls.clear()
    _persist(engine, d.doctor, d.run_id, tmp_path)
    assert len(spy.calls) == 1
    d_input, d_result = spy.calls[0]
    with Session(engine) as check:
        rows = _items(check, d.run_id)
        assert len(rows) == len(d_result.flags)
        for row, flag in zip(rows, d_result.flags, strict=True):
            assert row.rule_id == flag.rule_id
            assert row.message == flag.message
            assert row.dedupe_key == flag.dedupe_key
    # Unchanged evaluator semantics under reordered observation inputs.
    reordered = OfflineRuleInput(
        patient_id=d_input.patient_id,
        selected_current=tuple(reversed(d_input.selected_current)),
        history=tuple(reversed(d_input.history)),
        as_of_utc=d_input.as_of_utc,
        policy=d_input.policy,
        active_fact_verification_statuses=d_input.active_fact_verification_statuses,
    )
    assert evaluate_p4_rb2_offline_fixture(reordered).flags == d_result.flags


# --------------------------------------------------------------------------- #
# RB4-07 identity, F0 replay, scope and session boundaries
# --------------------------------------------------------------------------- #


def test_rb4_07_identity_scope_and_session_boundaries(sandbox, engine, tmp_path):
    """RB4-07: identity replay, authenticated scope, foreign source, sessions."""
    db = sandbox
    patient = _patient(db, "DEMO-A-001")
    doctor = _doctor(db, suffix="000000000008")
    doc, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-07-doc",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        report_date="2026-10-20",
    )
    obs = _add_observation(
        db,
        observation_id="a0000000-0000-4000-8000-0000000000aa",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=70,
        unit="bpm",
        measured_at="2026-11-01T09:00:00Z",
        source="patient_checkin",
    )

    # Genuine F0 replay reuses the identical run identity and manifest.
    first = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(obs.id,),
        request_id="rb4-07-replay",
        return_receipt=True,
    )
    assert first.replayed is False
    with Session(engine) as check:
        before_runs = _count(check, WorkflowRun)
        before_docs = _count(check, RunSelectedDocument)
        before_obs = _count(check, RunSelectedObservation)
        before_audits = _count(check, AuditEvent)
    second = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc.id,),
        observation_ids=(obs.id,),
        request_id="rb4-07-replay",
        return_receipt=True,
    )
    assert second.run_id == first.run_id
    assert second.replayed is True
    assert first.run_id == second.run_id
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == before_runs == 1
        assert _count(check, RunSelectedDocument) == before_docs == 1
        assert _count(check, RunSelectedObservation) == before_obs == 1
        assert _count(check, AuditEvent) == before_audits

    # Foreign selected source (another patient's document) is refused.
    other = _patient(db, "DEMO-B-001")
    foreign_doc, _ = _verified_doc(
        db,
        patient_id=other.id,
        root=tmp_path,
        label="rb4-07-foreign",
        test_name="Hemoglobin",
        value="14.1",
        unit="g/dL",
        report_date="2026-10-21",
    )
    with Session(engine) as check:
        runs_before = _count(check, WorkflowRun)
    with pytest.raises(ApiError) as foreign_exc:
        _start(
            engine,
            doctor,
            patient_id=patient.id,
            document_ids=(foreign_doc.id,),
            observation_ids=(),
            request_id="rb4-07-foreign",
        )
    assert foreign_exc.value.status_code == 404
    assert foreign_exc.value.code == ErrorCode.NOT_FOUND
    assert other.display_name not in str(foreign_exc.value)
    assert other.id not in str(foreign_exc.value)
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == runs_before
        assert _count(check, RunSelectedDocument) == before_docs == 1

    # A foreign observation (another patient's ID) is refused as unavailable.
    with Session(engine) as check:
        runs_before = _count(check, WorkflowRun)
        obs_before = _count(check, RunSelectedObservation)
    with pytest.raises(ApiError) as foreign_obs_exc:
        _start(
            engine,
            doctor,
            patient_id=patient.id,
            document_ids=(doc.id,),
            observation_ids=("4db31c0e-dc9c-5695-ad2f-ed612f80e308",),  # DEMO-B
            request_id="rb4-07-foreign-observation",
        )
    assert foreign_obs_exc.value.status_code == 404
    assert foreign_obs_exc.value.code == ErrorCode.NOT_FOUND
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == runs_before
        assert _count(check, RunSelectedObservation) == obs_before

    # A different (unassigned) doctor is refused without writes.
    unassigned = _doctor(db, username="demo_doctor_unassigned", suffix="000000000009")
    with Session(engine) as check:
        runs_before = _count(check, WorkflowRun)
    with pytest.raises(ApiError) as unassigned_exc:
        _start(
            engine,
            unassigned,
            patient_id=patient.id,
            document_ids=(doc.id,),
            observation_ids=(),
            request_id="rb4-07-unassigned",
        )
    assert unassigned_exc.value.status_code == 403
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == runs_before

    # A patient principal (even the right patient) cannot author a doctor run.
    patient_user = db.execute(select(User).where(User.username == "demo_patient_a")).scalar_one()
    patient_principal = Principal(
        user_id=patient_user.id,
        username=patient_user.username,
        display_name=patient_user.display_name,
        role=Role(patient_user.role),
        patient_id=patient_user.patient_id,
        session_id="dddddddd-dddd-4ddd-8ddd-00000000000e",
    )
    db.add(
        UserSession(
            id=patient_principal.session_id,
            user_id=patient_user.id,
            token_sha256=hashlib.sha256(b"rb4-synthetic-patient").hexdigest(),
            created_at="2026-11-01T00:00:00Z",
            expires_at="2026-12-01T00:00:00Z",
        )
    )
    db.commit()
    with Session(engine) as check:
        runs_before = _count(check, WorkflowRun)
        audits_before = _count(check, AuditEvent)
    with pytest.raises(ApiError) as patient_exc:
        _start(
            engine,
            patient_principal,
            patient_id=patient.id,
            document_ids=(doc.id,),
            observation_ids=(obs.id,),
            request_id="rb4-07-patient-principal",
        )
    assert patient_exc.value.status_code == 403
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == runs_before
        assert _count(check, AuditEvent) == audits_before

    # Expired stored session is refused before any write.
    expired = _doctor(db, suffix="00000000000a")
    with Session(engine) as check:
        session_row = check.get(UserSession, expired.session_id)
        assert session_row is not None
        session_row.expires_at = "2026-11-02T00:00:00Z"
        check.commit()
        runs_before = _count(check, WorkflowRun)
        audits_before = _count(check, AuditEvent)
    with pytest.raises(ApiError) as expired_exc:
        _start(
            engine,
            expired,
            patient_id=patient.id,
            document_ids=(doc.id,),
            observation_ids=(),
            request_id="rb4-07-expired",
        )
    assert expired_exc.value.status_code == 403
    with Session(engine) as check:
        assert _count(check, WorkflowRun) == runs_before
        assert _count(check, AuditEvent) == audits_before

    # Revoked session is refused by F1 without any gate rows.
    revoking = _doctor(db, suffix="00000000000b")
    revoke_doc, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-07-revoked",
        test_name="Hemoglobin",
        value="13.6",
        unit="g/dL",
        report_date="2026-10-22",
    )
    revoke_run = _start(
        engine,
        revoking,
        patient_id=patient.id,
        document_ids=(revoke_doc.id,),
        observation_ids=(),
        request_id="rb4-07-revoked",
    )
    with Session(engine) as check:
        session_row = check.get(UserSession, revoking.session_id)
        assert session_row is not None
        session_row.revoked_at = "2026-11-14T12:00:00Z"
        check.commit()
        audits_before = _count(check, AuditEvent)
    with pytest.raises(ApiError) as revoked_exc:
        _gate(engine, revoking, revoke_run, tmp_path)
    assert revoked_exc.value.status_code == 403
    assert revoked_exc.value.code == ErrorCode.FORBIDDEN
    with pytest.raises(ApiError) as revoked_persist:
        _persist(engine, revoking, revoke_run, tmp_path)
    assert revoked_persist.value.status_code == 403
    with Session(engine) as check:
        assert (
            check.scalar(
                select(func.count())
                .select_from(RunGateEvaluation)
                .where(RunGateEvaluation.workflow_run_id == revoke_run)
            )
            == 0
        )
        assert _count(check, AuditEvent) == audits_before
        assert _count(check, ReviewItem) == 0
        assert _count(check, EvidenceLink) == 0


# --------------------------------------------------------------------------- #
# RB4-09 stale / drift boundaries
# --------------------------------------------------------------------------- #


def test_rb4_09_selected_and_history_drift_denied_without_writes(
    sandbox, engine, tmp_path, monkeypatch
):
    """RB4-09: byte drift, fact drift and history drift all deny without writes."""
    db = sandbox
    patient = _patient(db, "DEMO-A-001")
    doctor = _doctor(db, suffix="00000000000c")

    # (a) Selected source byte drift after a successful persistence.
    doc_a, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-09-bytes",
        test_name="Hemoglobin",
        value="13.4",
        unit="g/dL",
        report_date="2026-10-20",
    )
    obs_a = _add_observation(
        db,
        observation_id="a0000000-0000-4000-8000-0000000000a1",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=70,
        unit="bpm",
        measured_at="2026-11-02T09:00:00Z",
        source="patient_checkin",
    )
    run_a = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc_a.id,),
        observation_ids=(obs_a.id,),
        request_id="rb4-09-bytes",
    )
    assert _gate(engine, doctor, run_a, tmp_path).decision == "proceed"
    first_a = _persist(engine, doctor, run_a, tmp_path)
    assert first_a.replayed is False

    (tmp_path / doc_a.stored_path).write_bytes(b"tampered synthetic bytes")
    refreshed = _gate(engine, doctor, run_a, tmp_path)
    assert refreshed.decision == "unavailable"
    assert refreshed.unavailable_reason == "source_bytes_unavailable"
    spy = _spy_rb2(monkeypatch)
    snapshot_a = _review_snapshot(db)
    with pytest.raises(ApiError) as exc_a:
        _persist(engine, doctor, run_a, tmp_path)
    assert exc_a.value.status_code == 409
    assert exc_a.value.code == ErrorCode.VALIDATION
    assert exc_a.value.detail == "Current F1 gate is not eligible."
    assert spy.calls == []
    assert _review_snapshot(db) == snapshot_a
    # Restore the exact bytes for the remaining independent subcases.
    raw = b"RB4 synthetic-only source: rb4-09-bytes"
    (tmp_path / doc_a.stored_path).write_bytes(raw)
    assert hashlib.sha256(raw).hexdigest() == doc_a.sha256

    # (b) Selected fact/decision drift after a successful persistence.
    doc_b, facts_b = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-09-fact",
        test_name="Hemoglobin",
        value="13.5",
        unit="g/dL",
        report_date="2026-10-21",
    )
    obs_b = _add_observation(
        db,
        observation_id="a0000000-0000-4000-8000-0000000000a2",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=71,
        unit="bpm",
        measured_at="2026-11-03T09:00:00Z",
        source="patient_checkin",
    )
    run_b = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc_b.id,),
        observation_ids=(obs_b.id,),
        request_id="rb4-09-fact",
    )
    assert _gate(engine, doctor, run_b, tmp_path).decision == "proceed"
    assert _persist(engine, doctor, run_b, tmp_path).replayed is False
    facts_b["value"].verification_status = "pending"
    db.commit()
    drifted_gate = _gate(engine, doctor, run_b, tmp_path)
    assert drifted_gate.decision == "halt"
    spy.calls.clear()
    snapshot_b = _review_snapshot(db)
    with pytest.raises(ApiError) as exc_b:
        _persist(engine, doctor, run_b, tmp_path)
    assert exc_b.value.status_code == 409
    assert exc_b.value.code == ErrorCode.VALIDATION
    assert exc_b.value.detail == "Current F1 gate is not eligible."
    assert spy.calls == []
    assert _review_snapshot(db) == snapshot_b

    # (c) Eligible history change after a successful persistence is sealed.
    doc_c, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-09-history",
        test_name="Hemoglobin",
        value="13.7",
        unit="g/dL",
        report_date="2026-10-23",
    )
    obs_c = _add_observation(
        db,
        observation_id="a0000000-0000-4000-8000-0000000000a3",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=72,
        unit="bpm",
        measured_at="2026-11-04T09:00:00Z",
        source="patient_checkin",
    )
    run_c = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(doc_c.id,),
        observation_ids=(obs_c.id,),
        request_id="rb4-09-history",
    )
    assert _gate(engine, doctor, run_c, tmp_path).decision == "proceed"
    first_c = _persist(engine, doctor, run_c, tmp_path)
    assert first_c.replayed is False
    _add_observation(
        db,
        observation_id="a0000000-0000-4000-8000-0000000000a4",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=75,
        unit="bpm",
        measured_at="2026-11-05T09:00:00Z",
        source="patient_checkin",
    )
    # Refresh F1 so a current persisted PROCEED exists; sealed completion stays.
    assert _gate(engine, doctor, run_c, tmp_path).decision == "proceed"
    spy.calls.clear()
    snapshot_c = _review_snapshot(db)
    with pytest.raises(ApiError) as exc_c:
        _persist(engine, doctor, run_c, tmp_path)
    assert exc_c.value.status_code == 409
    assert exc_c.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert exc_c.value.detail == "input_identity_changed"
    # The unchanged evaluator may run, but no sealed review row may be written.
    assert len(spy.calls) == 1
    assert _review_snapshot(db) == snapshot_c
    # The sealed first completion is exactly what remains.
    with Session(engine) as check:
        sealed = _review_audit(check, run_c)
        assert sealed.id == first_c.audit_event_id
        assert _count(check, ReviewEvaluation) >= 1
        assert (
            check.scalar(
                select(func.count())
                .select_from(ReviewEvaluation)
                .where(ReviewEvaluation.workflow_run_id == run_c)
            )
            == 1
        )


# --------------------------------------------------------------------------- #
# RB4-10 selected vs history / exclusions
# --------------------------------------------------------------------------- #


def test_rb4_10_zero_selected_current_history_admissibility_and_exclusions(
    sandbox, engine, tmp_path, monkeypatch
):
    """RB4-10: zero selected current -> zero flags, real completion, exclusions."""
    db = sandbox
    patient = _patient_d(db)
    doctor = _doctor(db, suffix="00000000000d")

    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000011",
        patient_id=patient.id,
        measure_type="systolic_bp",
        value=128,
        unit="mmHg",
        measured_at="2026-10-05T09:00:00Z",
    )
    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000012",
        patient_id=patient.id,
        measure_type="diastolic_bp",
        value=82,
        unit="mmHg",
        measured_at="2026-10-05T09:00:00Z",
    )
    # Inadmissible historical rows: wrong unit, rejected, future.
    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000013",
        patient_id=patient.id,
        measure_type="systolic_bp",
        value=120,
        unit="bpm",
        measured_at="2026-10-06T09:00:00Z",
    )
    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000014",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=60,
        unit="bpm",
        measured_at="2026-10-06T09:00:00Z",
        validation="rejected",
    )
    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000015",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=61,
        unit="bpm",
        measured_at="2026-12-01T09:00:00Z",
    )

    scaffold, _ = _verified_doc(
        db,
        patient_id=patient.id,
        root=tmp_path,
        label="rb4-10-scaffold",
        test_name="Hemoglobin",
        value="13.8",
        unit="g/dL",
        report_date="2026-11-02",
    )
    run_id = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(scaffold.id,),
        observation_ids=(),
        request_id="rb4-10-start",
    )

    gate = _gate(engine, doctor, run_id, tmp_path)
    assert gate.decision == "proceed"

    evidence = _evidence(engine, doctor, run_id, tmp_path)
    assert evidence.selected_observation_ids == ()
    assert evidence.no_current_reason == "no_current_selected"
    assert evidence.comparisons == ()
    exclusion_reasons = {
        item.observation_id: item.reason_code for item in evidence.history_exclusions
    }
    assert exclusion_reasons == {
        "d0000000-0000-4000-8000-000000000013": "unit_mismatch",
        "d0000000-0000-4000-8000-000000000014": "validation_rejected",
        "d0000000-0000-4000-8000-000000000015": "future_timestamp",
    }

    preview = _preview(engine, doctor, run_id, tmp_path)
    assert preview.no_current_reason == "no_current_selected"
    assert preview.policy_comparisons == ()
    assert preview.history_exclusions == evidence.history_exclusions

    spy = _spy_rb2(monkeypatch)
    first = _persist(engine, doctor, run_id, tmp_path)
    assert first.replayed is False
    assert first.review_items_persisted == first.review_items_total == 0
    assert first.evidence_links_persisted == first.evidence_links_total == 0
    assert len(spy.calls) == 1 and spy.calls[0][1].flags == ()
    assert first.l1_exclusion_count == 3
    assert first.l2_exclusion_count == 0  # inadmissible rows never reach RB2
    assert {item.reason_code for item in first.layered_exclusions.l3_merged} == {
        "unit_mismatch",
        "validation_rejected",
        "future_timestamp",
    }

    with Session(engine) as check:
        assert _items(check, run_id) == []
        evaluation = check.execute(
            select(ReviewEvaluation).where(ReviewEvaluation.workflow_run_id == run_id)
        ).scalar_one()
        assert evaluation.item_count == 0
        assert evaluation.evidence_link_count == 0
        assert evaluation.exclusion_count == 3
        _assert_sealed_evaluation(
            check,
            first,
            patient_id=patient.id,
            doctor_id=doctor.user_id,
            run_id=run_id,
            items=0,
            links=0,
            exclusions=3,
        )
        _assert_observation_links_only(check, run_id, count=0)

    snapshot = _review_snapshot(db)
    second = _persist(engine, doctor, run_id, tmp_path)
    assert second.replayed is True
    assert second.review_items_persisted == 0
    assert second.evidence_links_persisted == 0
    assert second.evaluation_id == first.evaluation_id
    assert second.audit_event_id == first.audit_event_id
    assert _review_snapshot(db) == snapshot

    # An inadmissible selected source cannot be smuggled into a current set.
    bad_run = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(scaffold.id,),
        observation_ids=("d0000000-0000-4000-8000-000000000013",),
        request_id="rb4-10-bad-selected",
    )
    bad_gate = _gate(engine, doctor, bad_run, tmp_path)
    assert bad_gate.decision == "unavailable"
    assert bad_gate.unavailable_reason == "selected_observation_inadmissible"
    with pytest.raises(ApiError) as bad_evidence:
        _evidence(engine, doctor, bad_run, tmp_path)
    assert bad_evidence.value.status_code == 409
    with pytest.raises(ApiError) as bad_persist:
        _persist(engine, doctor, bad_run, tmp_path)
    assert bad_persist.value.status_code == 409

    # 365-day F2 versus 90-day RB1/RB2 windows are preserved on a fresh run.
    _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000016",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=70,
        unit="bpm",
        measured_at="2026-06-20T09:00:00Z",  # 147 days before the clock
    )
    current_hr = _add_observation(
        db,
        observation_id="d0000000-0000-4000-8000-000000000017",
        patient_id=patient.id,
        measure_type="heart_rate",
        value=68,
        unit="bpm",
        measured_at="2026-11-10T09:00:00Z",
    )
    window_run = _start(
        engine,
        doctor,
        patient_id=patient.id,
        document_ids=(scaffold.id,),
        observation_ids=(current_hr.id,),
        request_id="rb4-10-window",
    )
    assert _gate(engine, doctor, window_run, tmp_path).decision == "proceed"
    window_evidence = _evidence(engine, doctor, window_run, tmp_path)
    # The same three inadmissible history rows stay excluded on the fresh run.
    assert {item.observation_id for item in window_evidence.history_exclusions} == {
        "d0000000-0000-4000-8000-000000000013",
        "d0000000-0000-4000-8000-000000000014",
        "d0000000-0000-4000-8000-000000000015",
    }
    f2_hr = window_evidence.comparisons[0]
    assert f2_hr.measure_type == "heart_rate"
    assert f2_hr.baseline_observation_id == "d0000000-0000-4000-8000-000000000016"
    assert f2_hr.comparable is True and f2_hr.delta == -2
    window_preview = _preview(engine, doctor, window_run, tmp_path)
    assert {item.observation_id for item in window_preview.history_exclusions} == {
        "d0000000-0000-4000-8000-000000000013",
        "d0000000-0000-4000-8000-000000000014",
        "d0000000-0000-4000-8000-000000000015",
    }
    rb1_hr = window_preview.policy_comparisons[0]
    assert rb1_hr.measure_type == "heart_rate"
    assert rb1_hr.baseline_observation_id is None
    assert rb1_hr.comparable is False
    assert rb1_hr.incomparable_reason == "no_baseline"
    spy.calls.clear()
    window_receipt = _persist(engine, doctor, window_run, tmp_path)
    assert window_receipt.review_items_total == 1
    assert window_receipt.evidence_links_total == 1
    assert window_receipt.l1_exclusion_count == 3
    assert window_receipt.l2_exclusion_count == 0
    assert [flag.rule_id for flag in spy.calls[0][1].flags] == ["DR-001"]
    with Session(engine) as check:
        _assert_sealed_evaluation(
            check,
            window_receipt,
            patient_id=patient.id,
            doctor_id=doctor.user_id,
            run_id=window_run,
            items=1,
            links=1,
            exclusions=3,
        )
        _assert_observation_links_only(check, window_run, count=1)
        assert _item_links(check, window_run) == [("DR-001", [current_hr.id])]


# --------------------------------------------------------------------------- #
# RB4-12 portability / migration guards (Linux only; Windows is owner-only)
# --------------------------------------------------------------------------- #


def test_rb4_12_migrated_head_and_r3_guards_present(sandbox, engine):
    """RB4-12 (partial): migrated head is 0008 with RB3 tables and guard test.

    This is a Linux-side schema/portability guard. It does NOT claim Windows
    execution; the owner's isolated PowerShell verification remains outstanding.
    """
    db = sandbox
    head = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert head == "0008_p4_rb3_review_persistence"
    tables = set(db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
    assert {"review_item", "evidence_link", "review_evaluation"} <= tables
    assert {"workflow_run", "run_gate_evaluation", "run_gate_blocker"} <= tables

    guards = (REPO_ROOT / "backend" / "tests" / "p4" / "test_p4_rb3_migration_guards.py").read_text(
        encoding="utf-8"
    )
    assert re.search(r"^def test_", guards, re.MULTILINE) is not None
    # Windows acceptance is owner-only and is not executed here.
    assert not (REPO_ROOT / "backend" / "tests" / "p4" / "test_p4_rb4_windows.py").exists()
