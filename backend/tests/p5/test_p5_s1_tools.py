"""P5-S1 bounded read-only tool adapter tests - owner authorization 2026-11-24.

Every adapter is exercised against a *genuine* F0 -> F1 -> F2 chain on a
migrated disposable SQLite database: the run is created by the accepted
``create_run_foundation``, the F1 gate by the accepted evaluator and the
evidence by the accepted bridge. Nothing here is a real ingestion, OCR run,
human verification, clinical decision or runtime tool execution.

ACADEMIC / SYNTHETIC DATA ONLY - NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import dataclasses
import inspect
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.agents import state as S
from app.agents import tools as T
from app.core.enums import (
    FactField,
    ObservationSource,
    Role,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.core.policies import Principal
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    User,
    UserSession,
    WorkflowRun,
)
from app.services.p5_evidence_bridge import build_run_evaluable_review_evidence
from app.services.p5_run_foundation import create_run_foundation

# --------------------------------------------------------------------------- #
# Identity fixtures (same synthetic identities the accepted S0 evidence uses)
# --------------------------------------------------------------------------- #

PATIENT = "11111111-2222-4333-8444-555555555555"
DOC_A = "c0ffee00-0000-4000-8000-000000000001"
DOC_B = "c0ffee00-0000-4000-8000-000000000002"
#: Synthetic seed credential for the scripted fixture only; never a real secret.
SEED_PASSWORD = "p5-s1-synthetic-only-seed"
OBS_CURRENT = "a0000000-0000-4000-8000-000000000001"
WARN_OBS = "f0000000-0000-5000-8000-0000000000a1"
REJECTED_OBS = "f0000000-0000-5000-8000-0000000000a2"
CLOCK = datetime(2026, 11, 14, 12, tzinfo=UTC)

DEFERRED_TOOLS = (
    "validate_structured_fields",
    "get_document_pages",
    "extract_document",
    "evaluate_demo_review_rules",
    "draft_grounded_summary",
    "create_in_app_task",
    "list_due_tasks",
)


def _sha(seed: str) -> str:
    from hashlib import sha256

    return sha256(seed.encode()).hexdigest()


def _seed_session(engine) -> Session:
    from app.services.seed import seed_demo_data

    session = Session(engine)
    seed_demo_data(session, password=SEED_PASSWORD, now=CLOCK, iterations=1000)
    session.commit()
    return session


def _doctor(db: Session, username: str = "demo_doctor") -> Principal:
    row = db.execute(select(User).where(User.username == username)).scalar_one()
    session_id = "dddddddd-dddd-4ddd-8ddd-00000000s1" + username[-1]
    if db.get(UserSession, session_id) is None:
        db.add(
            UserSession(
                id=session_id,
                user_id=row.id,
                token_sha256=_sha(f"p5-s1-session-{username}"),
                created_at="2026-11-01T00:00:00Z",
                expires_at="2026-12-01T00:00:00Z",
            )
        )
        db.commit()
    return Principal(
        user_id=row.id,
        username=row.username,
        display_name=row.display_name,
        role=Role(row.role),
        patient_id=row.patient_id,
        session_id=session_id,
    )


def _patient(db: Session, external_ref: str = "DEMO-A-001") -> Any:
    return db.execute(select(Patient).where(Patient.external_ref == external_ref)).scalar_one()


def _add_checkin(
    db: Session,
    *,
    observation_id: str,
    patient_id: str,
    measure: str = "systolic_bp",
    value: float = 121,
    unit: str = "mmHg",
    measured_at: str = "2026-11-01T09:00:00Z",
    source: str = "patient_checkin",
    validation: str = "ok",
    trust_level: str = "self_reported_validated",
) -> Any:
    row = Observation(
        id=observation_id,
        patient_id=patient_id,
        measure_type=measure,
        value=value,
        unit=unit,
        measured_at=measured_at,
        source=source,
        validation=validation,
        trust_level=trust_level,
        created_at="2026-11-14T12:00:00Z",
    )
    db.add(row)
    db.commit()
    return row


def _add_document(
    db: Session,
    *,
    patient_id: str,
    root: Path,
    label: str,
    facts: bool = True,
) -> Any:
    """Store a scripted synthetic document; ``facts=False`` stores no fact rows."""
    import hashlib
    import json

    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"P5-S1 synthetic-only source: {label}".encode()
    name = f"p5-s1-{label}.pdf"
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
        extraction_status="verified",
        document_patient_ref=patient.external_ref,
        document_patient_refs=json.dumps([patient.external_ref]),
        uploaded_at="2026-06-14T08:00:00Z",
    )
    db.add(doc)
    db.flush()
    if facts:
        verifier = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
        specs = (
            ("report_date", "2026-10-20", "2026-10-20", None),
            ("test_name", "Hemoglobin", "Hemoglobin", None),
            ("value", "13.4", "13.4", "g/dL"),
            ("unit", "g/dL", "g/dL", None),
        )
        for field_name, raw_text, normalized, unit in specs:
            fact = ExtractedFact(
                document_id=doc.id,
                patient_id=patient_id,
                field_name=field_name,
                raw_text=raw_text,
                normalized_value=normalized,
                unit=unit,
                page_index=0,
                char_start=0,
                char_end=max(len(raw_text), 1),
                verification_status="verified",
                quality_flags="[]",
                created_at="2026-06-14T08:00:00Z",
            )
            db.add(fact)
            db.flush()
            db.add(
                FactVerification(
                    fact_id=fact.id,
                    decision="verified",
                    verified_by_user_id=verifier.id,
                    decided_at="2026-06-14T08:00:00Z",
                    source_image_compared=1,
                )
            )
    db.commit()
    return doc


@dataclass(frozen=True)
class _Run:
    run_id: str
    patient_id: str
    doctor: Principal
    document_id: str


def _make_run(
    engine,
    tmp_path: Path,
    *,
    documents: int = 1,
    observations: int = 1,
    history: bool = False,
    patient_ref: str = "DEMO-A-001",
) -> _Run:
    """Drive the accepted F0 foundation and F1 gate for real.

    ``history=True`` stores the GOLD-D-shaped prior rows *before* the run is
    created, because the F1 gate binds the patient's evidence snapshot: rows
    added afterwards would make the persisted gate stale.
    """
    db = _seed_session(engine)
    try:
        patient = _patient(db, patient_ref)
        doctor = _doctor(db)
        if history:
            _add_checkin(
                db,
                observation_id=WARN_OBS,
                patient_id=patient.id,
                value=150,
                measured_at="2026-10-20T09:00:00Z",
                source="seed_fixture",
                validation="ok_with_warning",
            )
            _add_checkin(
                db,
                observation_id=REJECTED_OBS,
                patient_id=patient.id,
                value=999,
                measured_at="2026-09-01T09:00:00Z",
                source="seed_fixture",
                validation="rejected",
            )
        docs = [
            _add_document(db, patient_id=patient.id, root=tmp_path, label=f"doc{index}").id
            for index in range(documents)
        ]
        for index in range(observations):
            _add_checkin(
                db,
                observation_id=OBS_CURRENT
                if index == 0
                else f"a0000000-0000-4000-8000-{index:012d}",
                patient_id=patient.id,
            )
        with Session(engine) as session:
            receipt = create_run_foundation(
                session,
                principal=doctor,
                patient_id=patient.id,
                document_ids=tuple(docs),
                observation_ids=tuple(
                    OBS_CURRENT if index == 0 else f"a0000000-0000-4000-8000-{index:012d}"
                    for index in range(observations)
                ),
                omissions=(),
                client_request_id="p5-s1-integration",
                as_of_utc=CLOCK,
            )
            session.commit()
        # The accepted F1 evaluator persists the gate the F2 bridge requires.
        from app.services.p5_run_gate import evaluate_run_verification_gate

        evaluate_run_verification_gate(
            Session(engine),
            principal=doctor,
            run_id=receipt.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
        return _Run(
            run_id=receipt.run_id, patient_id=patient.id, doctor=doctor, document_id=docs[0]
        )
    finally:
        db.close()


def _context(engine, run: _Run, tmp_path: Path, node: S.NodeName) -> T.ToolContext:
    """A fresh clean session per call, exactly as the bridge contract requires."""
    return T.ToolContext(
        db=Session(engine),
        principal=run.doctor,
        run_id=run.run_id,
        node=node,
        validation_clock=CLOCK,
        upload_root=str(tmp_path),
    )


def _call(engine, run: _Run, tmp_path: Path, node: S.NodeName, adapter) -> T.ToolResult:
    ctx = _context(engine, run, tmp_path, node)
    try:
        return adapter(ctx)
    finally:
        ctx.db.close()


@dataclass
class _Poison:
    """Any attribute access proves the adapter touched the session."""

    touched: bool = False

    def __getattr__(self, name: str) -> Any:
        self.touched = True
        raise AssertionError(f"session accessed before the allowlist check: {name}")


def _row_counts(db: Session) -> dict[str, int]:
    models = (Document, ExtractedFact, FactVerification, Observation, WorkflowRun)
    return {
        model.__name__: db.execute(select(func.count()).select_from(model)).scalar_one()
        for model in models
    }


# --------------------------------------------------------------------------- #
# Matrix: every node x tool combination
# --------------------------------------------------------------------------- #


def test_s1_allowlist_matches_the_frozen_s0_node_tools_exactly() -> None:
    """``assert_tool_allowed`` is a pure function of the S0 allowlist."""
    for node in S.NodeName:
        for tool in S.ToolName:
            allowed = tool in S.NODE_TOOLS[node]
            if allowed:
                T.assert_tool_allowed(node, tool)
            else:
                with pytest.raises(T.ToolPermissionError):
                    T.assert_tool_allowed(node, tool)


def test_s1_every_unauthorized_combination_fails_closed_before_any_read() -> None:
    """All 50 node x tool pairs: an unauthorized pair never reaches the bridge."""
    checked = 0
    for node in S.NodeName:
        for tool in S.ToolName:
            if tool in S.NODE_TOOLS[node]:
                continue
            poison = _Poison()
            ctx = T.ToolContext(
                db=poison,
                principal=None,
                run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5",
                node=node,
                validation_clock=CLOCK,
                upload_root="/tmp",
            )
            adapter = {
                S.ToolName.READ_VERIFIED_FACTS: T.read_verified_facts,
                S.ToolName.READ_OBSERVATIONS: T.read_observations,
                S.ToolName.COMPARE_OBSERVATIONS: T.compare_observations,
            }.get(tool)
            if adapter is None:
                continue
            result = adapter(ctx)
            checked += 1
            assert result.ok is False
            assert result.data is None
            assert result.error is not None
            assert result.error.code is T.ToolErrorCode.TOOL_NOT_ALLOWED
            assert result.error.reason is T.ToolErrorReason.TOOL_NOT_ALLOWED
            assert result.audit.outcome == "error"
            assert result.audit.error_code is T.ToolErrorCode.TOOL_NOT_ALLOWED
            assert not poison.touched
    assert checked > 0


def test_s1_allowlist_guard_is_structural_not_clinical_authority() -> None:
    """The guard never returns an authorization decision, only raises or None."""
    assert T.assert_tool_allowed(S.NodeName.REVIEW_RULES, S.ToolName.READ_VERIFIED_FACTS) is None
    assert "decision" not in inspect.signature(T.assert_tool_allowed).parameters


def test_s1_closed_error_vocabulary_is_local_and_complete() -> None:
    assert [code.value for code in T.ToolErrorCode] == [
        "E_TOOL_NOT_ALLOWED",
        "E_NOT_FOUND",
        "E_SCOPE_VIOLATION",
        "E_UNVERIFIED_FACT",
        "E_VALIDATION",
    ]
    assert len(T.ToolErrorReason) == 13
    assert "E_INTERNAL" not in {code.value for code in T.ToolErrorCode}


# --------------------------------------------------------------------------- #
# Genuine F0 -> F1 -> F2 integration
# --------------------------------------------------------------------------- #


def test_s1_read_verified_facts_projects_the_genuine_f2_facts(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)

    assert result.ok is True, result.error
    assert result.error is None
    assert isinstance(result.data, list)
    assert len(result.data) == 4
    assert {fact.field_name for fact in result.data} == {
        FactField.REPORT_DATE,
        FactField.TEST_NAME,
        FactField.VALUE,
        FactField.UNIT,
    }
    for fact in result.data:
        assert isinstance(fact, S.VerifiedFact)
        assert fact.document_id == run.document_id
        assert fact.patient_id == run.patient_id
        assert fact.verification_status == "verified"
        assert fact.trust_basis == "doctor_verified"
        assert fact.evidence == []
    assert result.audit.outcome == "ok"
    assert result.audit.error_code is None
    assert set(result.audit.evidence_ids) == {fact.fact_id for fact in result.data}
    assert result.audit.run_id == run.run_id
    assert result.audit.node is S.NodeName.REVIEW_RULES
    assert result.audit.tool is S.ToolName.READ_VERIFIED_FACTS
    assert result.duration_ms >= 0


def test_s1_read_verified_facts_empty_is_empty_not_promoted(engine, tmp_path, monkeypatch) -> None:
    """A producer envelope with no verified fact yields ``[]``, never a promotion.

    The F1 gate requires verified facts in every selected document, so an empty
    verified-fact projection cannot be produced by a *genuine* run. This branch
    is therefore exercised on the producer envelope itself, and the assertion is
    about adapter behaviour only: no pending or corrected fact is ever promoted.
    """
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(evidence, verified_facts=())

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is True, result.error
    assert result.data == []
    assert result.audit.outcome == "ok"
    assert result.audit.evidence_ids == ()


def test_s1_read_observations_is_labelled_f2_selected_only(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is True, result.error
    payload = result.data
    assert isinstance(payload, T.ObservationEvidence)
    assert payload.scope == "f2_selected_only"
    assert [row.observation_id for row in payload.observations] == [OBS_CURRENT]
    assert {item.observation_id for item in payload.exclusions} == {REJECTED_OBS}
    assert payload.exclusions[0].reason_code is S.ExclusionReason.VALIDATION_REJECTED
    assert payload.no_current_reason is None


def test_s1_read_observations_never_silently_drops_an_exclusion(engine, tmp_path) -> None:
    """The adapter's exclusions equal the bridge's own, one for one."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    with Session(engine) as db:
        expected = build_run_evaluable_review_evidence(
            db,
            principal=run.doctor,
            run_id=run.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, T.ObservationEvidence)
    assert [(item.observation_id, item.reason_code.value) for item in result.data.exclusions] == [
        (item.observation_id, item.reason_code) for item in expected.history_exclusions
    ]


def test_s1_read_observations_preserves_self_reported_trust(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, T.ObservationEvidence)
    (row,) = result.data.observations
    assert row.trust_level is TrustLevel.SELF_REPORTED_VALIDATED
    assert row.verified_by is None
    assert row.verified_at is None
    assert row.source is ObservationSource.PATIENT_CHECKIN
    assert row.validation is ValidationState.OK
    assert row.role is S.ObservationRole.SELECTED_CURRENT
    assert row.value == Decimal("121")
    assert row.unit is Unit.MMHG
    assert row.source_fact_id is None
    assert row.source_document_id is None


def test_s1_read_observations_reports_no_current_reason_without_fabrication(
    engine, tmp_path
) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=0)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, T.ObservationEvidence)
    assert result.data.observations == []
    assert result.data.exclusions == []
    assert result.data.no_current_reason == "no_current_selected"


def test_s1_compare_projects_the_exact_f2_delta(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, list)
    assert len(result.data) == 1
    comparison = result.data[0]
    assert isinstance(comparison, S.ComparisonResult)
    assert comparison.current_observation_id == OBS_CURRENT
    assert comparison.baseline_observation_id == WARN_OBS
    assert comparison.current_value == Decimal("121")
    assert comparison.baseline_value == Decimal("150")
    assert comparison.delta == S.exact_delta(Decimal("121"), Decimal("150"))
    assert comparison.delta == Decimal("-29")
    assert comparison.comparable is True
    assert comparison.incomparable_reason is None
    assert comparison.trust_basis is S.TrustBasis.SELF_REPORTED
    assert comparison.history_policy is S.ComparisonWindow.F2_365D
    assert comparison.unit is Unit.MMHG
    assert result.audit.evidence_ids == (OBS_CURRENT, WARN_OBS)


def test_s1_compare_matches_the_bridge_comparison_field_for_field(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        expected = build_run_evaluable_review_evidence(
            db,
            principal=run.doctor,
            run_id=run.run_id,
            validation_clock=CLOCK,
            upload_root=str(tmp_path),
        )
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, list)
    assert len(result.data) == len(expected.comparisons) == 1
    produced, source = result.data[0], expected.comparisons[0]
    assert produced.current_observation_id == source.current_observation_id
    assert produced.baseline_observation_id == source.baseline_observation_id
    assert produced.measure_type.value == source.measure_type
    assert produced.unit.value == source.unit
    assert produced.comparable is source.comparable
    assert produced.delta == source.delta
    assert produced.trust_basis.value == source.trust_basis
    assert produced.incomparable_reason is None
    assert source.incomparable_reason is None


def test_s1_compare_preserves_an_incomparable_reason(engine, tmp_path) -> None:
    # DEMO-C-001 stores no systolic history, so the genuine producer has no baseline.
    run = _make_run(engine, tmp_path, documents=1, observations=1, patient_ref="DEMO-C-001")
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is True, result.error
    assert isinstance(result.data, list)
    (comparison,) = result.data
    # No admissible prior row exists, so the genuine producer reports no baseline.
    assert comparison.comparable is False
    assert comparison.delta is None
    assert comparison.incomparable_reason is S.IncomparableReason.NO_BASELINE
    assert comparison.baseline_observation_id is None


# --------------------------------------------------------------------------- #
# Rejected caller authority
# --------------------------------------------------------------------------- #


def test_s1_no_adapter_accepts_a_baseline_lookback_or_patient_argument() -> None:
    for adapter in (T.read_verified_facts, T.read_observations, T.compare_observations):
        parameters = list(inspect.signature(adapter).parameters)
        assert parameters == ["ctx"], adapter.__name__
    fields = {f.name for f in dataclasses.fields(T.ToolContext)}
    assert fields == {
        "db",
        "principal",
        "run_id",
        "node",
        "validation_clock",
        "upload_root",
    }


def test_s1_tool_context_rejects_a_forged_patient_or_baseline() -> None:
    with pytest.raises(TypeError):
        T.ToolContext(
            db=None,
            principal=None,
            run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5",
            node=S.NodeName.MONITOR_COMPARE,
            validation_clock=CLOCK,
            upload_root="/tmp",
            patient_id=PATIENT,
        )
    with pytest.raises(TypeError):
        T.ToolContext(
            db=None,
            principal=None,
            run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5",
            node=S.NodeName.MONITOR_COMPARE,
            validation_clock=CLOCK,
            upload_root="/tmp",
            baseline_observation_id=OBS_CURRENT,
        )
    with pytest.raises(TypeError):
        T.ToolContext(
            db=None,
            principal=None,
            run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5",
            node=S.NodeName.MONITOR_COMPARE,
            validation_clock=CLOCK,
            upload_root="/tmp",
            lookback_days=365,
        )


def test_s1_forged_run_identity_is_not_found(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    forged = dataclasses.replace(run, run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5")
    for node, adapter in (
        (S.NodeName.REVIEW_RULES, T.read_verified_facts),
        (S.NodeName.MONITOR_COMPARE, T.read_observations),
        (S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ):
        result = _call(engine, forged, tmp_path, node, adapter)
        assert result.ok is False
        assert result.error is not None
        assert result.error.code is T.ToolErrorCode.NOT_FOUND
        assert result.error.reason is T.ToolErrorReason.RUN_NOT_FOUND
        assert result.data is None


def test_s1_another_doctor_cannot_read_the_run(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        stranger = _doctor(db, username="demo_doctor_unassigned")
    forged = dataclasses.replace(run, doctor=stranger)
    for node, adapter in (
        (S.NodeName.REVIEW_RULES, T.read_verified_facts),
        (S.NodeName.MONITOR_COMPARE, T.read_observations),
        (S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ):
        result = _call(engine, forged, tmp_path, node, adapter)
        assert result.ok is False
        assert result.error is not None
        assert result.error.code is T.ToolErrorCode.SCOPE_VIOLATION
        assert result.error.reason is T.ToolErrorReason.ACCESS_DENIED
        assert result.data is None


# --------------------------------------------------------------------------- #
# Producer-evidence reconciliation (fail closed)
# --------------------------------------------------------------------------- #


def _patch_bridge(monkeypatch: pytest.MonkeyPatch, mutate) -> None:
    real = T.build_run_evaluable_review_evidence

    def fake(db, *, principal, run_id, validation_clock, upload_root):
        return mutate(
            real(
                db,
                principal=principal,
                run_id=run_id,
                validation_clock=validation_clock,
                upload_root=upload_root,
            )
        )

    monkeypatch.setattr(T, "build_run_evaluable_review_evidence", fake)


def _second_patient_fact(db: Session, root: Path) -> str:
    """A genuine stored verified fact belonging to a different patient."""
    patient = _patient(db, external_ref="DEMO-B-001")
    document = _add_document(db, patient_id=patient.id, root=root, label="other-patient")
    return (
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document.id))
        .scalars()
        .first()
        .id
    )


def test_s1_cross_patient_fact_is_rejected(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        other_fact = _second_patient_fact(db, tmp_path)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            verified_facts=(dataclasses.replace(evidence.verified_facts[0], fact_id=other_fact),),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.SCOPE_VIOLATION
    assert result.error.reason is T.ToolErrorReason.PATIENT_SCOPE_MISMATCH
    assert result.data is None


def test_s1_fact_outside_the_run_selection_is_rejected(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(evidence, selected_document_ids=())

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.SCOPE_VIOLATION
    assert result.error.reason is T.ToolErrorReason.DOCUMENT_SCOPE_MISMATCH


def test_s1_unverified_fact_is_never_promoted(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        patient = db.get(Patient, run.patient_id)
        assert patient is not None
        unselected = _add_document(db, patient_id=patient.id, root=tmp_path, label="pending")
        pending = ExtractedFact(
            document_id=unselected.id,
            patient_id=patient.id,
            field_name="value",
            raw_text="13.9",
            normalized_value="13.9",
            unit="g/dL",
            page_index=0,
            char_start=0,
            char_end=4,
            verification_status="pending",
            quality_flags="[]",
            created_at="2026-06-14T08:00:00Z",
        )
        db.add(pending)
        db.commit()
        pending_id = pending.id

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            verified_facts=(dataclasses.replace(evidence.verified_facts[0], fact_id=pending_id),),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.UNVERIFIED_FACT
    assert result.error.reason is T.ToolErrorReason.UNVERIFIED_FACT


def test_s1_missing_stored_fact_is_not_found(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            verified_facts=(
                dataclasses.replace(
                    evidence.verified_facts[0], fact_id="deadbeef-0000-4000-8000-0000000000ff"
                ),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.NOT_FOUND
    assert result.error.reason is T.ToolErrorReason.FACT_NOT_FOUND


def test_s1_stored_fact_drift_is_inconsistent_evidence(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            verified_facts=(
                dataclasses.replace(evidence.verified_facts[0], normalized_value="13.9"),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.VALIDATION
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_observation_drift_is_inconsistent_evidence(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            selected_observations=(
                dataclasses.replace(evidence.selected_observations[0], value=Decimal("122")),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_cross_patient_observation_is_rejected(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        other = _patient(db, external_ref="DEMO-B-001")
        _add_checkin(
            db,
            observation_id="a0000000-0000-4000-8000-0000000000b1",
            patient_id=other.id,
        )

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            selected_observations=(
                dataclasses.replace(
                    evidence.selected_observations[0],
                    observation_id="a0000000-0000-4000-8000-0000000000b1",
                ),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.SCOPE_VIOLATION
    assert result.error.reason is T.ToolErrorReason.PATIENT_SCOPE_MISMATCH


def test_s1_comparison_current_outside_selection_is_rejected(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            comparisons=(
                dataclasses.replace(
                    evidence.comparisons[0],
                    current_observation_id="a0000000-0000-4000-8000-0000000000ff",
                ),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_stale_gate_is_not_evaluable_not_an_error_payload_of_evidence(engine, tmp_path) -> None:
    """A run whose F1 gate is no longer eligible fails closed with no evidence."""
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    # A pending fact in the *selected* document makes the current gate ineligible.
    with Session(engine) as db:
        patient = db.get(Patient, run.patient_id)
        assert patient is not None
        db.add(
            ExtractedFact(
                document_id=run.document_id,
                patient_id=patient.id,
                field_name="value",
                raw_text="?",
                normalized_value="?",
                unit=None,
                page_index=0,
                char_start=0,
                char_end=1,
                verification_status="pending",
                quality_flags="[]",
                created_at="2026-06-14T08:00:00Z",
            )
        )
        db.commit()
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.VALIDATION
    assert result.error.reason is T.ToolErrorReason.PRODUCER_NOT_EVALUABLE
    assert result.data is None


# --------------------------------------------------------------------------- #
# Envelope, audit and session invariants
# --------------------------------------------------------------------------- #


def test_s1_dirty_session_is_refused_before_the_bridge(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    ctx = _context(engine, run, tmp_path, S.NodeName.REVIEW_RULES)
    try:
        ctx.db.add(
            Observation(
                id="a0000000-0000-4000-8000-0000000000cc",
                patient_id=run.patient_id,
                measure_type="systolic_bp",
                value=1,
                unit="mmHg",
                measured_at="2026-11-01T09:00:00Z",
                source="patient_checkin",
                validation="ok",
                trust_level="self_reported_validated",
                created_at="2026-11-14T12:00:00Z",
            )
        )
        result = T.read_verified_facts(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.code is T.ToolErrorCode.VALIDATION
        assert result.error.reason is T.ToolErrorReason.SESSION_NOT_CLEAN
        # S1-R1: a caller-owned pending write is neither rolled back nor closed.
        assert ctx.db.in_transaction() is True
        assert len(ctx.db.new) == 1
        assert ctx.db.is_active
        ctx.db.rollback()
    finally:
        ctx.db.close()


def test_s1_invalid_context_is_refused(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    for mutation in ({"run_id": ""}, {"upload_root": ""}):
        forged = dataclasses.replace(run, **{})
        ctx = T.ToolContext(
            db=Session(engine),
            principal=forged.doctor,
            run_id=mutation.get("run_id", forged.run_id),
            node=S.NodeName.REVIEW_RULES,
            validation_clock=CLOCK,
            upload_root=mutation.get("upload_root", str(tmp_path)),
        )
        try:
            result = T.read_verified_facts(ctx)
            assert result.ok is False
            assert result.error is not None
            assert result.error.reason is T.ToolErrorReason.INVALID_CONTEXT
        finally:
            ctx.db.close()


def test_s1_error_envelope_invariants(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    forged = dataclasses.replace(run, run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5")
    for node, adapter in (
        (S.NodeName.REVIEW_RULES, T.read_verified_facts),
        (S.NodeName.MONITOR_COMPARE, T.read_observations),
        (S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ):
        result = _call(engine, forged, tmp_path, node, adapter)
        assert result.ok is False
        assert result.data is None
        assert isinstance(result.error, T.ToolError)
        assert isinstance(result.error.code, T.ToolErrorCode)
        assert isinstance(result.error.reason, T.ToolErrorReason)
        assert 0 < len(result.error.message) <= 300
        assert result.error.retryable is False
        assert result.audit.outcome == "error"
        assert result.audit.error_code == result.error.code
        assert result.duration_ms >= 0


def test_s1_audit_metadata_is_bounded_and_carries_no_payload(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    results = [
        _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts),
        _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations),
        _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ]
    for result in results:
        assert result.ok is True, result.error
        audit_json = result.audit.model_dump_json()
        assert len(result.audit.evidence_ids) <= T.MAX_AUDIT_EVIDENCE_IDS
        assert "synthetic-only source" not in audit_json
        assert SEED_PASSWORD not in audit_json
        assert "raw_text" not in audit_json
        assert "normalized_value" not in audit_json
        assert set(result.audit.model_dump()) == {
            "tool",
            "node",
            "run_id",
            "outcome",
            "error_code",
            "evidence_ids",
        }


def test_s1_adapters_never_write_to_the_database(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    with Session(engine) as db:
        before = _row_counts(db)
    for node, adapter in (
        (S.NodeName.REVIEW_RULES, T.read_verified_facts),
        (S.NodeName.MONITOR_COMPARE, T.read_observations),
        (S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ):
        ctx = _context(engine, run, tmp_path, node)
        try:
            result = adapter(ctx)
            assert result.ok is True, result.error
            # S1-R1: the adapter ends the read transaction it opened itself.
            assert ctx.db.in_transaction() is False
            assert len(ctx.db.new) == 0
            assert len(ctx.db.dirty) == 0
            assert len(ctx.db.deleted) == 0
        finally:
            ctx.db.close()
    with Session(engine) as db:
        assert _row_counts(db) == before


def test_s1_adapters_open_no_socket(engine, tmp_path, monkeypatch) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)

    def _no_socket(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("network egress attempted")

    monkeypatch.setattr(socket, "socket", _no_socket)
    monkeypatch.setattr(socket, "create_connection", _no_socket)
    for node, adapter in (
        (S.NodeName.REVIEW_RULES, T.read_verified_facts),
        (S.NodeName.MONITOR_COMPARE, T.read_observations),
        (S.NodeName.MONITOR_COMPARE, T.compare_observations),
    ):
        assert _call(engine, run, tmp_path, node, adapter).ok is True


def test_s1_no_deferred_tool_is_implemented_or_stubbed() -> None:
    for name in DEFERRED_TOOLS:
        assert not hasattr(T, name), name
    public = {name for name in dir(T) if not name.startswith("_")}
    assert public.isdisjoint(DEFERRED_TOOLS)
    assert T.__all__ == sorted(T.__all__)


def test_s1_module_has_no_runtime_or_egress_dependency() -> None:
    import ast

    source = Path(T.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules.isdisjoint(
        {
            "langgraph",
            "langchain",
            "ollama",
            "openai",
            "requests",
            "httpx",
            "aiohttp",
            "socket",
            "smtplib",
            "sendgrid",
            "twilio",
            "celery",
            "redis",
        }
    ), modules
    # No runtime policy, graph, checkpoint, LLM or route surface is exposed.
    for forbidden in (
        "build_graph",
        "StateGraph",
        "get_checkpointer",
        "llm_client",
        "router",
        "notify",
    ):
        assert not hasattr(T, forbidden), forbidden
    assert set(T.__all__) == {
        "MAX_AUDIT_EVIDENCE_IDS",
        "ObservationEvidence",
        "ToolAuditMetadata",
        "ToolContext",
        "ToolError",
        "ToolErrorCode",
        "ToolErrorReason",
        "ToolPermissionError",
        "ToolResult",
        "assert_tool_allowed",
        "compare_observations",
        "read_observations",
        "read_verified_facts",
    }


def test_s1_payloads_carry_no_runtime_or_clinical_authority(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    result = _call(engine, run, tmp_path, S.NodeName.REVIEW_RULES, T.read_verified_facts)
    assert result.ok is True
    assert isinstance(result.data, list)
    for fact in result.data:
        dumped = fact.model_dump()
        assert "decision" not in dumped
        assert "proceed" not in dumped
        assert "halt" not in dumped
        assert "clinical" not in dumped
    comparison = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert comparison.ok is True
    assert isinstance(comparison.data, list)
    for row in comparison.data:
        dumped = row.model_dump()
        assert dumped["history_policy"] == S.ComparisonWindow.F2_365D.value
        assert "decision" not in dumped


# --------------------------------------------------------------------------- #
# S1-R1: post-bridge transaction lifecycle
# --------------------------------------------------------------------------- #


def test_s1_sequential_same_context_calls_end_their_transactions(engine, tmp_path) -> None:
    """Both permitted monitor_compare adapters reuse one context and leave it clean."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    ctx = _context(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE)
    try:
        first = T.read_observations(ctx)
        assert first.ok is True, first.error
        assert isinstance(first.data, T.ObservationEvidence)
        assert len(first.data.observations) == 1
        assert ctx.db.in_transaction() is False
        assert len(ctx.db.new) == len(ctx.db.dirty) == len(ctx.db.deleted) == 0

        second = T.compare_observations(ctx)
        assert second.ok is True, second.error
        assert isinstance(second.data, list)
        assert len(second.data) == 1
        assert ctx.db.in_transaction() is False
        assert len(ctx.db.new) == len(ctx.db.dirty) == len(ctx.db.deleted) == 0
    finally:
        ctx.db.close()


def test_s1_early_error_return_leaves_no_open_transaction(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    forged = dataclasses.replace(run, run_id="6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5")
    ctx = _context(engine, forged, tmp_path, S.NodeName.MONITOR_COMPARE)
    try:
        result = T.compare_observations(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.reason is T.ToolErrorReason.RUN_NOT_FOUND
        assert ctx.db.in_transaction() is False
    finally:
        ctx.db.close()


def test_s1_denied_call_never_touches_the_session(engine, tmp_path) -> None:
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    ctx = _context(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE)
    try:
        result = T.read_verified_facts(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.code is T.ToolErrorCode.TOOL_NOT_ALLOWED
        assert ctx.db.in_transaction() is False
    finally:
        ctx.db.close()


def test_s1_no_adapter_ever_commits(engine, tmp_path, monkeypatch) -> None:
    """ROLLBACK only: an adapter may never turn its read into a durable write."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    ctx = _context(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE)
    commits: list[str] = []
    monkeypatch.setattr(ctx.db, "commit", lambda: commits.append("commit"))
    try:
        assert T.read_observations(ctx).ok is True
        assert T.compare_observations(ctx).ok is True
        assert commits == []
    finally:
        ctx.db.close()


# --------------------------------------------------------------------------- #
# S1-R2: complete stored-row reconciliation
# --------------------------------------------------------------------------- #


def _write_after_bridge(monkeypatch: pytest.MonkeyPatch, engine, mutation) -> None:
    """Simulate a concurrent writer committing between the bridge and the read.

    The real bridge still runs and still rolls back its own snapshot; the
    mutation is committed by a second session afterwards, so the adapter's
    stored-row reads see the drifted row while the F2 envelope does not.
    """

    real = T.build_run_evaluable_review_evidence

    def fake(db, *, principal, run_id, validation_clock, upload_root):
        evidence = real(
            db,
            principal=principal,
            run_id=run_id,
            validation_clock=validation_clock,
            upload_root=upload_root,
        )
        with Session(engine) as writer:
            mutation(writer)
            writer.commit()
        return evidence

    monkeypatch.setattr(T, "build_run_evaluable_review_evidence", fake)


def _mutate_current(**values):
    return lambda writer: writer.execute(
        update(Observation).where(Observation.id == OBS_CURRENT).values(**values)
    )


@pytest.mark.parametrize(
    ("values", "label"),
    [
        ({"value": 999}, "value"),
        ({"unit": "bpm"}, "unit"),
        ({"measure_type": "heart_rate"}, "measure_type"),
        ({"measured_at": "2026-11-14T12:30:00Z"}, "measured_at"),
        ({"source": "seed_fixture"}, "source"),
    ],
)
def test_s1_compare_rejects_a_drifted_stored_current_row(
    engine, tmp_path, monkeypatch, values, label
) -> None:
    """S1-R2: the current value/unit/measure/timestamp/source must match F2."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    _write_after_bridge(monkeypatch, engine, _mutate_current(**values))
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False, label
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.VALIDATION
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT
    assert result.data is None


def test_s1_compare_rejects_a_drifted_stored_trust_label(engine, tmp_path, monkeypatch) -> None:
    """S1-R2: a stored trust label that moved after the bridge fails closed."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    with Session(engine) as db:
        verifier = _doctor(db).user_id
    _write_after_bridge(
        monkeypatch,
        engine,
        _mutate_current(
            trust_level="doctor_verified",
            verified_by_user_id=verifier,
            verified_at="2026-11-01T09:00:00Z",
        ),
    )
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_compare_rejects_a_baseline_that_became_rejected(engine, tmp_path, monkeypatch) -> None:
    """S1-R2: the baseline is re-checked with the accepted admissibility predicate."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    _write_after_bridge(
        monkeypatch,
        engine,
        lambda writer: writer.execute(
            update(Observation).where(Observation.id == WARN_OBS).values(validation="rejected")
        ),
    )
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_compare_rejects_a_baseline_measured_after_its_current(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R2: a baseline must be strictly earlier than its current row."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    _write_after_bridge(
        monkeypatch,
        engine,
        lambda writer: writer.execute(
            update(Observation)
            .where(Observation.id == WARN_OBS)
            .values(measured_at="2026-11-10T09:00:00Z")
        ),
    )
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_compare_rejects_a_cross_patient_baseline(engine, tmp_path, monkeypatch) -> None:
    """S1-R2: a forged baseline identity from another patient is refused."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    with Session(engine) as db:
        other_observation = (
            db.execute(select(Observation).where(Observation.patient_id != run.patient_id))
            .scalars()
            .first()
        )
        assert other_observation is not None
        other_id = other_observation.id

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            comparisons=(
                dataclasses.replace(evidence.comparisons[0], baseline_observation_id=other_id),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.code is T.ToolErrorCode.SCOPE_VIOLATION
    assert result.error.reason is T.ToolErrorReason.PATIENT_SCOPE_MISMATCH


def test_s1_compare_rejects_a_baseline_with_a_different_measure(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R2: a baseline must carry the comparison's own measure type and unit."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    with Session(engine) as db:
        heart_rate = (
            db.execute(
                select(Observation).where(
                    Observation.patient_id == run.patient_id,
                    Observation.measure_type == "heart_rate",
                )
            )
            .scalars()
            .first()
        )
        assert heart_rate is not None
        heart_rate_id = heart_rate.id

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            comparisons=(
                dataclasses.replace(evidence.comparisons[0], baseline_observation_id=heart_rate_id),
            ),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_compare_rejects_a_drifted_trust_basis_label(engine, tmp_path, monkeypatch) -> None:
    """S1-R2: the F2 trust label must follow from the reconciled rows."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)

    def mutate(evidence):
        return dataclasses.replace(
            evidence,
            comparisons=(dataclasses.replace(evidence.comparisons[0], trust_basis="mixed"),),
        )

    _patch_bridge(monkeypatch, mutate)
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.compare_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_read_observations_rejects_a_selected_row_that_became_rejected(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R2: a selected row that turned rejected is no longer an eligible current."""
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    _write_after_bridge(monkeypatch, engine, _mutate_current(validation="rejected"))
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


def test_s1_read_observations_rejects_a_selected_row_beyond_the_future_skew(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R2: the accepted future-skew boundary is re-checked after the bridge."""
    run = _make_run(engine, tmp_path, documents=1, observations=1)
    _write_after_bridge(monkeypatch, engine, _mutate_current(measured_at="2026-11-14T12:30:00Z"))
    result = _call(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE, T.read_observations)
    assert result.ok is False
    assert result.error is not None
    assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT


# --------------------------------------------------------------------------- #
# S1-R3: baseline window drift
# --------------------------------------------------------------------------- #


def test_s1_compare_rejects_a_baseline_outside_the_365_day_window(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R3: a baseline that drifted before the window fails closed, cleanly."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    # Earlier than the current row but outside the accepted 365-day window.
    _write_after_bridge(
        monkeypatch,
        engine,
        lambda writer: writer.execute(
            update(Observation)
            .where(Observation.id == WARN_OBS)
            .values(measured_at="2025-06-01T09:00:00Z")
        ),
    )
    ctx = _context(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE)
    try:
        result = T.compare_observations(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.code is T.ToolErrorCode.VALIDATION
        assert result.error.reason is T.ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT
        assert result.data is None
        assert ctx.db.in_transaction() is False
        assert len(ctx.db.new) == len(ctx.db.dirty) == len(ctx.db.deleted) == 0
    finally:
        ctx.db.close()


def test_s1_compare_accepts_the_exact_inclusive_365_day_boundary(
    engine, tmp_path, monkeypatch
) -> None:
    """S1-R3: the inclusive lower bound stays acceptable, with F2's delta intact."""
    run = _make_run(engine, tmp_path, documents=1, observations=1, history=True)
    # Exactly current - 365 days: the accepted lower boundary is inclusive.
    _write_after_bridge(
        monkeypatch,
        engine,
        lambda writer: writer.execute(
            update(Observation)
            .where(Observation.id == WARN_OBS)
            .values(measured_at="2025-11-01T09:00:00Z")
        ),
    )
    ctx = _context(engine, run, tmp_path, S.NodeName.MONITOR_COMPARE)
    try:
        result = T.compare_observations(ctx)
        assert result.ok is True, result.error
        assert isinstance(result.data, list)
        (comparison,) = result.data
        assert comparison.baseline_observation_id == WARN_OBS
        assert comparison.comparable is True
        assert comparison.current_value == Decimal("121")
        assert comparison.baseline_value == Decimal("150")
        # The F2 delta is preserved, never recalculated from the drifted row.
        assert comparison.delta == Decimal("-29")
        assert comparison.delta == S.exact_delta(Decimal("121"), Decimal("150"))
        assert comparison.history_policy is S.ComparisonWindow.F2_365D
        assert ctx.db.in_transaction() is False
    finally:
        ctx.db.close()
