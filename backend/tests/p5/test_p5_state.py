"""P5-S0 typed shared-state schema tests (structural only; never runtime authority).

Every test maps to the S0 matrix item (M01-M20) in
``docs/phase-reports/P5_S0_TYPED_STATE_IMPLEMENTATION_REVIEW_20261123.md`` and to
the requirement it protects (``REQ-GRAPH-01``, ``REQ-SEC-04``, ``REQ-DATA-04``,
``REQ-DATA-05``, ``REQ-OPS-04``, ``REQ-AUDIT-01``, ``REQ-VERIFY-01``,
``REQ-SEC-05``, ``REQ-TASK-01``, ``P0-R03/R04/R08/R09/R11/R12``).

Real validators run in every case — nothing is mocked. Passing these tests
proves *shape* only: no authentication, authorization, grounding, execution or
policy approval is exercised (see M17/M18/M20).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
import yaml
from pydantic import AfterValidator, TypeAdapter, ValidationError

from app.agents import state as S
from app.core.enums import (
    FactField,
    MeasureType,
    ObservationSource,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.core.paths import REPO_ROOT
from app.schemas.p4_rb3_review_persistence import RB3DenialReason
from app.services.p5_run_foundation import (
    POLICY_REFERENCE_VERSION,
    STATE_SCHEMA_VERSION,
    WORKFLOW_VERSION,
)

# --- synthetic identifiers (all canonical lowercase UUIDv4 / v5) -----------------------

RUN = "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"
PATIENT = "11111111-1111-4111-8111-111111111111"
OTHER_PATIENT = "99999999-9999-4999-8999-999999999999"
DOCTOR = "22222222-2222-4222-8222-222222222222"
DOC_A = "33333333-3333-4333-8333-333333333333"
DOC_B = "44444444-4444-4444-8444-444444444444"
FACT_A = "55555555-5555-4555-8555-555555555555"
FACT_B = "66666666-6666-4666-8666-666666666666"
OBS_A = "77777777-7777-4777-8777-777777777777"
OBS_B = "88888888-8888-4888-8888-888888888888"
OBS_HIST = "a0a0a0a0-a0a0-4a0a-8a0a-a0a0a0a0a0a0"
GATE_EVAL = "b1b1b1b1-b1b1-4b1b-8b1b-b1b1b1b1b1b1"
EVALUATION = "c2c2c2c2-c2c2-4c2c-8c2c-c2c2c2c2c2c2"
AUDIT_EVENT = "d3d3d3d3-d3d3-4d3d-8d3d-d3d3d3d3d3d3"
ISSUE_A = "e4e4e4e4-e4e4-4e4e-8e4e-e4e4e4e4e4e4"
APPROVAL_ID = "f5f5f5f5-f5f5-4f5f-8f5f-f5f5f5f5f5f5"
DERIVED_TASK = "51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f"  # version nibble 5, RFC variant
OMISSION_ISSUE = "0e0e0e0e-0e0e-4e0e-8e0e-0e0e0e0e0e0e"

AS_OF = "2026-11-14T12:00:00Z"
STARTED = "2026-11-23T10:00:00Z"
UPDATED = "2026-11-23T10:00:01Z"
VALIDATED = "2026-11-23T10:00:02Z"

STATE_MODULE = REPO_ROOT / "backend" / "app" / "agents" / "state.py"


def _sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _identity(**overrides: Any) -> S.RunIdentity:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "thread_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "workflow_version": "1.0.0",
        "state_schema_version": "1.0.0",
        "policy_version": "demo-policy-1.1.0",
        "prompt_version": "draft-v1",
        "mapping_version": "map-1.0.0",
        "as_of_utc": AS_OF,
        "idempotency_key": _sha("start"),
        "started_at": STARTED,
    }
    fields.update(overrides)
    return S.RunIdentity(**fields)


def _document(document_id: str = DOC_A, sha: str = "doc-a") -> S.SelectedDocumentRef:
    return S.SelectedDocumentRef(
        document_id=document_id, source_sha256=_sha(sha), source_status="verified"
    )


def _manifest(**overrides: Any) -> S.SelectedSourceManifest:
    documents = overrides.pop("documents", [_document()])
    fields: dict[str, Any] = {
        "document_ids": [item.document_id for item in documents],
        "documents": documents,
    }
    if "observations" in overrides:
        fields["observation_ids"] = [item.observation_id for item in overrides["observations"]]
    if "omissions" in overrides:
        fields["omission_document_ids"] = [item.document_id for item in overrides["omissions"]]
    fields.update(overrides)
    return S.SelectedSourceManifest.build(**fields)


def _observation(**overrides: Any) -> S.ObservationView:
    fields: dict[str, Any] = {
        "observation_id": OBS_A,
        "patient_id": PATIENT,
        "measure_type": MeasureType.SYSTOLIC_BP,
        "value": Decimal("140.5"),
        "unit": Unit.MMHG,
        "measured_at": "2026-11-14T08:00:00Z",
        "source": ObservationSource.PATIENT_CHECKIN,
        "validation": ValidationState.OK,
        "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
    }
    fields.update(overrides)
    return S.ObservationView(**fields)


def _verified_observation(**overrides: Any) -> S.ObservationView:
    fields: dict[str, Any] = {
        "observation_id": OBS_B,
        "source": ObservationSource.VERIFIED_DOCUMENT,
        "trust_level": TrustLevel.DOCTOR_VERIFIED,
        "verified_by": DOCTOR,
        "verified_at": "2026-11-14T09:00:00Z",
        "source_fact_id": FACT_A,
        "source_document_id": DOC_A,
        "value": Decimal("135"),
        "measured_at": "2026-11-14T09:30:00Z",
    }
    fields.update(overrides)
    return _observation(**fields)


def _selected_observation(row: S.ObservationView) -> S.SelectedObservationRef:
    return S.SelectedObservationRef(
        observation_id=row.observation_id,
        trust_level=row.trust_level,
        source_fact_id=row.source_fact_id,
        observation_created_at=row.measured_at,
    )


def _gate(
    decision: S.GateDecision = S.GateDecision.PROCEED, **overrides: Any
) -> S.GateEvaluationRef:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "gate_evaluation_id": GATE_EVAL,
        "gate_version": "1.0.0",
        "input_fingerprint_sha256": _sha("gate-input"),
        "decision": decision,
        "blocking_fact_count": 0 if decision is S.GateDecision.PROCEED else 1,
        "replayed": False,
    }
    if decision is S.GateDecision.HALT:
        fields["issues"] = [
            S.GateIssueRef(
                issue_type=S.IssueType.VI_001,
                reason_code="pending_fact",
                document_id=DOC_A,
                fact_ids=[FACT_A],
                message="One fact is pending verification.",
            )
        ]
    if decision is S.GateDecision.UNAVAILABLE:
        fields["unavailable_reason"] = S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE
    fields.update(overrides)
    return S.GateEvaluationRef(**fields)


def _evidence(**overrides: Any) -> S.EvaluableEvidenceRef:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "as_of_utc": AS_OF,
        "workflow_version": "1.0.0",
        "state_schema_version": "1.0.0",
        "mapping_version": "map-1.0.0",
        "policy_version": "demo-policy-1.1.0",
        "gate_evaluation_id": GATE_EVAL,
        "gate_version": "1.0.0",
        "gate_input_fingerprint_sha256": _sha("gate-input"),
        "bridge_input_fingerprint_sha256": _sha("bridge-input"),
        "selected_document_ids": [DOC_A],
    }
    fields.update(overrides)
    fields.setdefault("selected_observation_ids", [])
    if "no_current_reason" not in overrides:
        fields["no_current_reason"] = (
            None if fields["selected_observation_ids"] else "no_current_selected"
        )
    return S.EvaluableEvidenceRef(**fields)


def _sealed(**overrides: Any) -> S.SealedReviewEvaluation:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "as_of_utc": AS_OF,
        "policy_version": "demo-policy-1.1.0",
        "policy_reference_sha256": _sha("policy"),
        "gate_evaluation_id": GATE_EVAL,
        "gate_version": "1.0.0",
        "gate_input_fingerprint_sha256": _sha("gate-input"),
        "bridge_input_fingerprint_sha256": _sha("bridge-input"),
        "input_fingerprint_sha256": _sha("rb3-input"),
        "output_identity_sha256": _sha("rb3-output"),
        "evaluation_id": EVALUATION,
        "audit_event_id": AUDIT_EVENT,
        "lineage_label_policy": "a2_transport_label",
        "dr006_policy": "not_present",
        "replayed": False,
        "review_items_persisted": 1,
        "review_items_total": 1,
        "evidence_links_persisted": 1,
        "evidence_links_total": 1,
        "l1_exclusion_count": 0,
        "l2_exclusion_count": 0,
    }
    fields.update(overrides)
    return S.SealedReviewEvaluation(**fields)


def _state(**overrides: Any) -> S.SharedGraphState:
    fields: dict[str, Any] = {
        "identity": _identity(),
        "selection": _manifest(),
        "updated_at": UPDATED,
    }
    fields.update(overrides)
    return S.SharedGraphState(**fields)


def _approved_state(status: S.RunStatus, **overrides: Any) -> S.SharedGraphState:
    """A post-draft state: proceed gate, draft, approve decision, consistent status."""
    observation = _observation()
    fields: dict[str, Any] = {
        "observations": [observation],
        "selection": _manifest(observations=[_selected_observation(observation)]),
        "status": status,
        "last_validated_at_utc": VALIDATED,
        "verification_gate": _gate(),
        "draft_summary": S.DraftSummary(
            draft_id=APPROVAL_ID,
            provider=S.DraftProvider.DETERMINISTIC_FALLBACK,
            execution_status=S.DraftExecutionStatus.FALLBACK_NO_MODEL,
            prompt_version="draft-v1",
            created_at=VALIDATED,
        ),
        "approval": S.ApprovalDecision(
            decision_id=APPROVAL_ID,
            decision=S.ApprovalChoice.APPROVE,
            doctor_id=DOCTOR,
            decided_at=VALIDATED,
        ),
    }
    fields.update(overrides)
    return _state(**fields)


def _json(model: Any) -> dict[str, Any]:
    return json.loads(model.model_dump_json())


def _revalidated(model: Any, **changes: Any) -> Any:
    """Re-validate through JSON with the same string forms a serialized state would carry."""
    payload = _json(model)
    payload.update(changes)
    return type(model).model_validate_json(json.dumps(payload))


# --- M01: valid initial state and deterministic round trip ----------------------------


def test_m01_initial_state_is_queued_and_authorizes_nothing() -> None:
    state = _state()
    assert state.status is S.RunStatus.QUEUED
    assert state.approval is None and state.draft_summary is None and state.pending_tasks == []
    assert state.verification_gate is None and state.evaluable_evidence is None
    assert state.review_persistence is None and state.checkpoint is None
    assert state.workflow_completed is False
    assert state.review_evaluation_sealed is False
    assert state.checkpoint_diverges is False
    assert state.policy_status == "unapproved"
    assert state.runtime_policy_activated is False
    assert state.runtime_evaluable is False
    assert state.document_ids == [DOC_A] and state.observation_ids == []
    assert state.identity.supported_versions() is True


def test_m01_json_round_trip_is_lossless_and_text_stable() -> None:
    observation = _verified_observation()
    state = _state(
        observations=[observation],
        selection=_manifest(observations=[_selected_observation(observation)]),
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(),
        evaluable_evidence=_evidence(
            selected_observation_ids=[OBS_B],
            bridge_input_fingerprint_sha256=_sha("bridge-input"),
        ),
        comparisons=[
            S.ComparisonResult(
                measure_type=MeasureType.SYSTOLIC_BP,
                unit=Unit.MMHG,
                current_observation_id=OBS_B,
                baseline_observation_id=OBS_HIST,
                current_value=Decimal("135"),
                baseline_value=Decimal("140.5"),
                delta=Decimal("-5.5"),
                comparable=True,
                trust_basis=S.TrustBasis.MIXED,
            )
        ],
    )
    text = state.model_dump_json()
    revived = S.SharedGraphState.model_validate_json(text)
    assert revived == state
    assert revived.model_dump_json() == text
    assert json.loads(text) == state.model_dump(mode="json")
    assert revived.observations[0].value == Decimal("135")
    assert revived.comparisons[0].delta == Decimal("-5.5")
    # Decimal values travel as canonical strings; enums as their values.
    payload = json.loads(text)
    assert payload["observations"][0]["value"] == "135"
    assert payload["status"] == "queued"
    assert payload["retry_counts"] == {}
    # Properties are not serialized fields.
    assert "workflow_completed" not in payload and "document_ids" not in payload


def test_m01_decimal_text_is_canonical_and_exact() -> None:
    a = _observation(value=Decimal("140.50"))
    b = _observation(value=Decimal("140.5"))
    c = _observation(value=Decimal("1.4050E+2"))
    assert a.model_dump_json() == b.model_dump_json() == c.model_dump_json()
    assert json.loads(a.model_dump_json())["value"] == "140.5"
    # Python-mode dumping keeps the exact Decimal object (no float anywhere).
    assert isinstance(a.model_dump()["value"], Decimal)
    assert S.ExactDecimal is not None  # annotated type exported for S2 adapters


def test_m01_version_constants_match_the_f0_foundation() -> None:
    assert S.STATE_SCHEMA_VERSION == STATE_SCHEMA_VERSION
    assert S.WORKFLOW_VERSION == WORKFLOW_VERSION
    assert S.POLICY_REFERENCE_VERSION == POLICY_REFERENCE_VERSION
    assert _identity().supported_versions() is True
    assert (
        _identity(state_schema_version="1.1.0").supported_versions() is False
    )  # format valid; service decides


def test_m01_identity_is_immutable_as_a_block() -> None:
    before = _identity()
    before.assert_unchanged(_identity())
    with pytest.raises(ValueError, match="as_of_utc"):
        _identity(as_of_utc="2026-11-15T12:00:00Z").assert_unchanged(before)
    with pytest.raises(ValidationError, match="frozen_instance"):
        before.as_of_utc = "2026-11-15T12:00:00Z"


# --- M02: run / thread identity ---------------------------------------------------------


def test_m02_thread_id_must_equal_run_id() -> None:
    with pytest.raises(ValidationError, match="thread_id must equal run_id"):
        _identity(thread_id=OBS_A)
    with pytest.raises(ValidationError, match="thread must be the run"):
        _state(
            checkpoint=S.CheckpointRef(
                checkpoint_id="ckpt-1",
                thread_id=OBS_A,
                last_completed_node=None,
                claimed_status=None,
            )
        )
    ref = S.CheckpointRef(
        checkpoint_id="ckpt-1",
        thread_id=RUN,
        last_completed_node=S.NodeName.DOCUMENT_EXTRACT,
        claimed_status=S.RunStatus.QUEUED,
    )
    assert _state(checkpoint=ref).checkpoint_diverges is False


def test_m02_checkpoint_claim_is_informational_never_authority() -> None:
    ahead = S.CheckpointRef(
        checkpoint_id="ckpt-2",
        thread_id=RUN,
        last_completed_node=S.NodeName.FINALIZE_ACTIONS,
        claimed_status=S.RunStatus.COMPLETED,
    )
    state = _state(checkpoint=ahead)  # §7.3 row 5 is representable so the reconciler can see it
    assert state.status is S.RunStatus.QUEUED
    assert state.workflow_completed is False
    assert state.checkpoint_diverges is True


# --- M03: malformed identifiers, digests, versions and timestamps ---------------------


@pytest.mark.parametrize(
    ("type_name", "bad"),
    [
        ("Uuid", "6F1C2D3E-4A5B-4C6D-8E7F-90A1B2C3D4E5"),  # uppercase
        ("Uuid", "{6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5}"),  # braces
        ("Uuid", "urn:uuid:6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e4a5b4c6d8e7f90a1b2c3d4e5"),  # no hyphens
        ("Uuid", "00000000-0000-0000-0000-000000000000"),  # nil: not v4, not RFC variant
        ("Uuid", DERIVED_TASK),  # v5 in a v4 slot
        ("Uuid", "6f1c2d3e-4a5b-4c6d-0e7f-90a1b2c3d4e5"),  # wrong variant nibble
        ("Uuid", "6f1c2d3e-4a5b-1c6d-8e7f-90a1b2c3d4e5"),  # version 1
        ("Uuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4eg"),  # non-hex
        ("UuidV5", RUN),  # v4 in a v5 slot
        ("Sha256", _sha("x")[:-1]),
        ("Sha256", _sha("x").upper()),
        ("Sha256", "0" * 64),  # placeholder
        ("Sha256", "g" * 64),
        ("Iso", "2026-11-14T12:00:00+00:00"),
        ("Iso", "2026-11-14T12:00:00.000Z"),
        ("Iso", "2026-11-14 12:00:00Z"),
        ("Iso", "2026-11-14t12:00:00Z"),
        ("Iso", "2026-02-30T00:00:00Z"),  # impossible day
        ("Iso", "2026-13-01T00:00:00Z"),  # impossible month
        ("Iso", "2026-1-01T00:00:00Z"),  # not zero padded
        ("Iso", "2026-11-14T24:00:00Z"),
        ("SemVer", "1.0"),
        ("SemVer", "1.0.0.0"),
        ("SemVer", "01.0.0"),
        ("SemVer", "v1.0.0"),
        ("SemVer", "1.0.0-rc1"),
        ("SemVer", "1000000000.0.0"),  # exceeds the persisted 12-char column
        ("MappingVersion", "1.0.0"),
        ("MappingVersion", "map-1.0"),
        ("MappingVersion", "map-1.0.0-rc1"),
        ("MappingVersion", "map-01.0.0"),
        ("PolicyVersion", "demo-policy-1.1"),
        ("PolicyVersion", "Demo-Policy-1.1.0"),
        ("PolicyVersion", "demo-policy-1.1.0-rc1"),
        ("PolicyVersion", "demo-policy-v1.1.0"),
        ("PromptVersion", "draft v1"),
        ("PromptVersion", "-draft"),
        ("ReasonCode", "Pending-Fact"),
        ("ErrorCode", "VALIDATION"),
        ("ErrorCode", "e_validation"),
    ],
)
def test_m03_malformed_primitives_are_rejected(type_name: str, bad: str) -> None:
    adapter = TypeAdapter(getattr(S, type_name))
    with pytest.raises(ValidationError):
        adapter.validate_python(bad)


@pytest.mark.parametrize(
    ("type_name", "good"),
    [
        ("Uuid", RUN),
        ("UuidV5", DERIVED_TASK),
        ("Sha256", _sha("ok")),
        ("Iso", AS_OF),
        ("SemVer", "1.0.0"),
        ("MappingVersion", "map-1.0.0"),
        ("PolicyVersion", "demo-policy-1.1.0"),
        ("PromptVersion", "draft-v1"),
        ("ReasonCode", "selected_separate_recovery_source"),
        ("ErrorCode", "E_WORKFLOW_VERSION_MISMATCH"),
    ],
)
def test_m03_well_formed_primitives_are_accepted(type_name: str, good: str) -> None:
    adapter = TypeAdapter(getattr(S, type_name))
    assert adapter.validate_python(good) == good


def test_m03_primitives_reject_non_string_input() -> None:
    for type_name in ("Uuid", "Sha256", "Iso", "SemVer"):
        with pytest.raises(ValidationError):
            TypeAdapter(getattr(S, type_name)).validate_python(12345)


def test_m03_task_due_date_must_be_a_real_calendar_date() -> None:
    good = S.TaskDraft(
        action_key=_sha("task"), task_id=DERIVED_TASK, title="Follow-up", due_date="2026-12-01"
    )
    assert good.due_date == "2026-12-01"
    for bad in ("2026-02-30", "2026-13-01", "2026-1-01", "01-12-2026", "2026-12-01T00:00:00Z"):
        with pytest.raises(ValidationError):
            S.TaskDraft(
                action_key=_sha("task"), task_id=DERIVED_TASK, title="Follow-up", due_date=bad
            )


# --- M04: unknown fields and unsafe coercions ------------------------------------------


def test_m04_unknown_fields_are_rejected_at_every_level() -> None:
    for payload in (
        {**_json(_state()), "approved": True},
        {**_json(_state()), "run_gate_completed": True},
        {**_json(_state()), "blocking_fact_count": 0},
        {**_json(_state()), "identity": {**_json(_identity()), "nickname": "demo"}},
        {**_json(_state()), "selection": {**_json(_manifest()), "extra_document": DOC_B}},
    ):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            S.SharedGraphState.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "queued"),  # str instead of enum in Python mode
        ("status", True),
        ("observations", ()),  # tuple instead of list
        ("retry_counts", {"document_extract": 1}),  # str key instead of NodeName
    ],
)
def test_m04_python_mode_coercions_are_rejected(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        _state(**{field: value})


def test_m04_json_strings_are_not_coerced_to_numbers_or_booleans() -> None:
    payload = _json(_state())
    payload["events"] = [
        {
            "node": "intake_validate",
            "attempt": "1",
            "started_at": STARTED,
            "tools_called": [],
            "detail": None,
        }
    ]
    with pytest.raises(ValidationError):
        S.SharedGraphState.model_validate_json(json.dumps(payload))
    payload["events"][0]["attempt"] = True
    with pytest.raises(ValidationError):
        S.SharedGraphState.model_validate_json(json.dumps(payload))


def test_m04_model_metadata_is_bounded_and_keyed() -> None:
    ok = {"provider": "ollama", "latency_ms": "1200"}
    assert _state(model_metadata=ok).model_metadata == ok
    for bad in (
        {"Provider": "x"},
        {"a" * 70: "x"},
        {"k": "v" * 200},
        {f"k{i}": "v" for i in range(9)},
        "",
    ):
        with pytest.raises(ValidationError):
            _state(model_metadata=bad)


def test_m04_confidence_rejects_strings_booleans_and_out_of_range() -> None:
    for bad in ("0.5", True, -0.01, 1.01, "1"):
        with pytest.raises(ValidationError):
            S.TriageDetail(
                path_selected=S.TriagePath.TEXT_LAYER,
                path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                document_id=DOC_A,
                attempt_index=1,
                engine_confidence=bad,
                preprocessing_applied=False,
            )
    for good in (0, 1, 0.5, None):
        S.TriageDetail(
            path_selected=S.TriagePath.TEXT_LAYER,
            path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
            document_id=DOC_A,
            attempt_index=1,
            engine_confidence=good,
            preprocessing_applied=False,
        )


# --- M05: collection caps ---------------------------------------------------------------


def _capped(builder: Any, cap: int) -> None:
    builder(cap)
    with pytest.raises(ValidationError):
        builder(cap + 1)


def test_m05_document_and_omission_caps() -> None:
    ids = [f"33333333-3333-4333-8333-33333333333{i}" for i in range(6)]

    def documents(count: int) -> None:
        _manifest(
            documents=[
                _document(document_id=identifier, sha=identifier) for identifier in ids[:count]
            ]
        )

    _capped(documents, 5)


def test_m05_observation_manifest_cap() -> None:
    rows = [_observation(observation_id=f"77777777-7777-4777-8777-{i:012d}") for i in range(21)]

    def observations(count: int) -> None:
        selected = [_selected_observation(row) for row in rows[:count]]
        _state(observations=rows[:count], selection=_manifest(observations=selected))

    _capped(observations, 20)


def test_m05_fact_attempt_issue_flag_error_and_event_caps() -> None:
    def fact(identifier: str) -> S.ExtractedFact:
        return S.ExtractedFact(
            fact_id=identifier,
            patient_id=PATIENT,
            document_id=DOC_A,
            field_name=FactField.VALUE,
            raw_text="140",
            provenance=S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A),
        )

    def facts(count: int) -> None:
        _state(extraction_facts=[fact(f"55555555-5555-4555-8555-{i:012d}") for i in range(count)])

    _capped(facts, 40)

    def attempts(count: int) -> None:
        _state(
            extraction_attempts=[
                S.ExtractionAttempt(
                    attempt_id=f"66666666-6666-4666-8666-{i:012d}",
                    document_id=DOC_A,
                    path=S.ExtractionPath.PYPDF,
                    preprocessing=S.Preprocessing.NONE,
                    page_from=0,
                    page_to=1,
                    text_char_count=10,
                    succeeded=True,
                    duration_ms=5,
                    created_at=STARTED,
                )
                for i in range(count)
            ]
        )

    _capped(attempts, 10)

    def events(count: int) -> None:
        _state(
            events=[
                S.NodeEvent(node=S.NodeName.INTAKE_VALIDATE, started_at=STARTED, ended_at=STARTED)
                for _ in range(count)
            ]
        )

    _capped(events, 40)

    def errors(count: int) -> None:
        _state(
            errors=[
                S.AgentError(
                    code="E_INTERNAL",
                    node=S.NodeName.INTAKE_VALIDATE,
                    message="Unexpected failure.",
                    retryable=False,
                    attempt=1,
                    occurred_at=STARTED,
                )
                for _ in range(count)
            ]
        )

    _capped(errors, 10)


def test_m05_nested_caps_blocks_counts_and_attempts() -> None:
    with pytest.raises(ValidationError):
        _gate(
            issues=[
                S.GateIssueRef(
                    issue_type=S.IssueType.VI_001,
                    reason_code="x",
                    document_id=DOC_A,
                    fact_ids=[FACT_A] * 41,
                    message="m",
                )
            ]
        )
    with pytest.raises(ValidationError):
        _gate(blocking_fact_count=41)
    with pytest.raises(ValidationError):
        S.GateDetail(decision="halt", blocking_fact_count=1, issue_types=[S.IssueType.VI_001] * 7)
    for bad_attempt in (0, 6):
        with pytest.raises(ValidationError):
            S.NodeEvent(node=S.NodeName.INTAKE_VALIDATE, attempt=bad_attempt, started_at=STARTED)
    for bad_index in (0, 3):
        with pytest.raises(ValidationError):
            S.TriageDetail(
                path_selected=S.TriagePath.TEXT_LAYER,
                path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                document_id=DOC_A,
                attempt_index=bad_index,
                preprocessing_applied=False,
            )
    with pytest.raises(ValidationError):
        S.ValidationDetail(
            validation_outcome=S.ValidationOutcome.REPAIR_REQUESTED,
            attempt_index=1,
            violation_codes=[S.ViolationCode.SCHEMA_INVALID] * 7,
        )
    with pytest.raises(ValidationError):
        S.ExtractionAttempt(
            attempt_id=FACT_A,
            document_id=DOC_A,
            path=S.ExtractionPath.TESSERACT,
            preprocessing=S.Preprocessing.GRAYSCALE_UPSCALE,
            page_from=0,
            page_to=201,
            text_char_count=200001,
            succeeded=False,
            error_code="E_TESSERACT_TIMEOUT",
            duration_ms=1,
            created_at=STARTED,
        )
    with pytest.raises(ValidationError):
        S.DraftSummary(
            draft_id=APPROVAL_ID,
            provider=S.DraftProvider.DETERMINISTIC_FALLBACK,
            execution_status=S.DraftExecutionStatus.FALLBACK_NO_MODEL,
            prompt_version="draft-v1",
            claims=[
                S.ClaimCitation(
                    text="c",
                    evidence=[
                        S.ProvenanceRef(kind=S.ProvenanceKind.OBSERVATION, observation_id=OBS_A)
                    ],
                )
                for _ in range(21)
            ],
            created_at=VALIDATED,
        )


# --- M06: non-finite and out-of-bound numerics ----------------------------------------


@pytest.mark.parametrize(
    "bad", ["NaN", "sNaN", "Infinity", "-Infinity", "0", "-1", "0.00001", "12345678901"]
)
def test_m06_non_finite_or_unbounded_values_are_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        _observation(value=Decimal(bad))
    payload = _json(_observation())
    payload["value"] = bad
    with pytest.raises(ValidationError):
        S.ObservationView.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_m06_non_finite_confidence_is_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        S.TriageDetail(
            path_selected=S.TriagePath.OCR_DIRECT,
            path_reason=S.PathReason.CONFIDENCE_OK,
            document_id=DOC_A,
            attempt_index=1,
            engine_confidence=bad,
            preprocessing_applied=False,
        )


def test_m06_floats_are_never_silently_accepted_for_exact_values() -> None:
    with pytest.raises(ValidationError):
        _observation(value=140.5)
    with pytest.raises(ValidationError):
        _observation(value="140.5")
    with pytest.raises(ValidationError):
        _observation(value=True)
    # JSON numbers are parsed from their text: exact.
    assert S.ObservationView.model_validate_json(
        json.dumps({**_json(_observation()), "value": 0.1})
    ).value == Decimal("0.1")


# --- M07: patient / doctor scope -------------------------------------------------------


def test_m07_evidence_outside_the_run_patient_is_rejected() -> None:
    with pytest.raises(ValidationError, match="patient scope"):
        _state(
            extraction_facts=[
                S.ExtractedFact(
                    fact_id=FACT_A,
                    patient_id=OTHER_PATIENT,
                    document_id=DOC_A,
                    field_name=FactField.VALUE,
                    raw_text="140",
                    provenance=S.ProvenanceRef(
                        kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A
                    ),
                )
            ]
        )
    with pytest.raises(ValidationError, match="patient scope"):
        _state(observations=[_observation(patient_id=OTHER_PATIENT)])
    with pytest.raises(ValidationError, match="different run or scope"):
        _state(last_validated_at_utc=VALIDATED, verification_gate=_gate(patient_id=OTHER_PATIENT))
    with pytest.raises(ValidationError, match="different run or scope"):
        _state(last_validated_at_utc=VALIDATED, verification_gate=_gate(doctor_id=OBS_A))
    with pytest.raises(ValidationError, match="different run identity"):
        _state(
            last_validated_at_utc=VALIDATED,
            verification_gate=_gate(),
            evaluable_evidence=_evidence(run_id=OBS_A),
        )


def test_m07_gate_requires_the_validation_clock() -> None:
    with pytest.raises(ValidationError, match="validation clock"):
        _state(verification_gate=_gate())


# --- M08: provenance combinations ------------------------------------------------------


def test_m08_provenance_ref_shape() -> None:
    span = S.ProvenanceRef(
        kind=S.ProvenanceKind.DOCUMENT_SPAN,
        document_id=DOC_A,
        page_index=1,
        char_start=10,
        char_end=20,
        extractor=S.Extractor.PYPDF,
        raw_text="140",
    )
    assert span.char_end == 20
    for bad in (
        {"kind": S.ProvenanceKind.DOCUMENT_SPAN},
        {"kind": S.ProvenanceKind.DOCUMENT_SPAN, "document_id": DOC_A, "observation_id": OBS_A},
        {"kind": S.ProvenanceKind.OBSERVATION},
        {"kind": S.ProvenanceKind.CHECKIN_NOTE, "observation_id": OBS_A, "document_id": DOC_A},
        {
            "kind": S.ProvenanceKind.DOCUMENT_SPAN,
            "document_id": DOC_A,
            "char_start": 20,
            "char_end": 20,
        },
        {"kind": S.ProvenanceKind.DOCUMENT_SPAN, "document_id": DOC_A, "page_index": 201},
        {"kind": S.ProvenanceKind.DOCUMENT_SPAN, "document_id": DOC_A, "raw_text": "x" * 501},
    ):
        with pytest.raises(ValidationError):
            S.ProvenanceRef(**bad)


def test_m08_observation_trust_and_source_provenance_are_inseparable() -> None:
    base = {
        "observation_id": OBS_A,
        "patient_id": PATIENT,
        "measure_type": MeasureType.SYSTOLIC_BP,
        "value": Decimal("140"),
        "unit": Unit.MMHG,
        "measured_at": "2026-11-14T08:00:00Z",
    }
    good_cases = [
        {
            "source": ObservationSource.PATIENT_CHECKIN,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
        },
        {
            "source": ObservationSource.SEED_FIXTURE,
            "validation": ValidationState.OK_WITH_WARNING,
            "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
        },
        {
            "source": ObservationSource.VERIFIED_DOCUMENT,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.DOCTOR_VERIFIED,
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
            "source_fact_id": FACT_A,
            "source_document_id": DOC_A,
        },
    ]
    for case in good_cases:
        S.ObservationView(**base, **case)
    bad_cases = [
        {
            "source": ObservationSource.PATIENT_CHECKIN,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.DOCTOR_VERIFIED,
        },
        {
            "source": ObservationSource.PATIENT_CHECKIN,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
        },
        {
            "source": ObservationSource.VERIFIED_DOCUMENT,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
        },
        {
            "source": ObservationSource.VERIFIED_DOCUMENT,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.DOCTOR_VERIFIED,
            "verified_by": DOCTOR,
            "source_fact_id": FACT_A,
            "source_document_id": DOC_A,
        },  # no verified_at
        {
            "source": ObservationSource.VERIFIED_DOCUMENT,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.DOCTOR_VERIFIED,
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
            "source_fact_id": FACT_A,
        },  # partial lineage
        {
            "source": ObservationSource.SEED_FIXTURE,
            "validation": ValidationState.OK,
            "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
            "source_fact_id": FACT_A,
            "source_document_id": DOC_A,
        },
    ]
    for case in bad_cases:
        with pytest.raises(ValidationError):
            S.ObservationView(**base, **case)
    for measure, unit in (
        (MeasureType.HEART_RATE, Unit.MMHG),
        (MeasureType.GLUCOSE, Unit.BPM),
        (MeasureType.DIASTOLIC_BP, Unit.MG_DL),
    ):
        with pytest.raises(ValidationError, match="closed unit"):
            S.ObservationView(
                **{**base, "measure_type": measure, "unit": unit},
                source=ObservationSource.PATIENT_CHECKIN,
                validation=ValidationState.OK,
                trust_level=TrustLevel.SELF_REPORTED_VALIDATED,
            )


def test_m08_extracted_fact_decision_shape_and_verified_lineage() -> None:
    def fact(**overrides: Any) -> S.ExtractedFact:
        fields: dict[str, Any] = {
            "fact_id": FACT_A,
            "patient_id": PATIENT,
            "document_id": DOC_A,
            "field_name": FactField.VALUE,
            "raw_text": "140",
            "provenance": S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A),
        }
        fields.update(overrides)
        return S.ExtractedFact(**fields)

    assert fact().verification_status is S.VerificationStatus.PENDING
    fact(
        verification_status=S.VerificationStatus.VERIFIED,
        verified_by=DOCTOR,
        verified_at="2026-11-14T09:00:00Z",
    )
    fact(
        verification_status=S.VerificationStatus.REJECTED,
        verified_by=DOCTOR,
        verified_at="2026-11-14T09:00:00Z",
    )
    for bad in (
        {"verified_by": DOCTOR, "verified_at": "2026-11-14T09:00:00Z"},  # pending with a decision
        {"verification_status": S.VerificationStatus.VERIFIED},
        {"verification_status": S.VerificationStatus.REJECTED},
        {"field_name": "diagnosis"},
        {"quality_flags": [S.QualityFlag.CLEAN] * 8},
    ):
        with pytest.raises(ValidationError):
            fact(**bad)

    evidence = [S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A)]
    S.VerifiedFact(
        fact_id=FACT_A,
        patient_id=PATIENT,
        document_id=DOC_A,
        field_name=FactField.VALUE,
        normalized_value="140",
        unit="mg/dL",
        corrected_from_fact_id=FACT_B,
        evidence=evidence,
        verified_by=DOCTOR,
        verified_at="2026-11-14T09:00:00Z",
    )
    base = {
        "fact_id": FACT_A,
        "patient_id": PATIENT,
        "document_id": DOC_A,
        "field_name": FactField.VALUE,
        "normalized_value": "140",
        "evidence": evidence,
        "verified_by": DOCTOR,
        "verified_at": "2026-11-14T09:00:00Z",
    }
    for bad in (
        {"corrected_from_fact_id": FACT_A},  # corrected from itself
        {"evidence": []},  # REQ-VERIFY-01
        {"normalized_value": ""},
    ):
        with pytest.raises(ValidationError):
            S.VerifiedFact(**{**base, **bad})


def test_m08_selection_manifest_shape() -> None:
    with pytest.raises(ValidationError, match="exactly document_ids"):
        _manifest(document_ids=[DOC_A], documents=[_document(DOC_B)])
    with pytest.raises(ValidationError, match="ascending"):
        _manifest(document_ids=[DOC_B, DOC_A], documents=[_document(DOC_B), _document(DOC_A)])
    with pytest.raises(ValidationError, match="omitted document"):
        _manifest(
            omissions=[
                S.SelectedOmissionRef(
                    document_id=DOC_A,
                    vi002_issue_id=OMISSION_ISSUE,
                    reason_code="selected_separate_recovery_source",
                    doctor_id=DOCTOR,
                    source_sha256=_sha("o"),
                )
            ]
        )
    with pytest.raises(ValidationError, match="source_fact_id"):
        S.SelectedObservationRef(
            observation_id=OBS_A,
            trust_level=TrustLevel.DOCTOR_VERIFIED,
            observation_created_at=STARTED,
        )
    with pytest.raises(ValidationError, match="selected_separate_recovery_source"):
        S.SelectedOmissionRef(
            document_id=DOC_B,
            vi002_issue_id=OMISSION_ISSUE,
            reason_code="because",
            doctor_id=DOCTOR,
            source_sha256=_sha("o"),
        )


def test_m08_manifest_fingerprint_is_self_verifying() -> None:
    manifest = _manifest()
    payload = _json(manifest)
    payload["documents"][0]["source_sha256"] = _sha("changed")
    with pytest.raises(ValidationError, match="selection_fingerprint does not match"):
        S.SelectedSourceManifest.model_validate_json(json.dumps(payload))
    rebuilt = _manifest(documents=[_document(DOC_A, sha="changed")])
    assert rebuilt.selection_fingerprint != manifest.selection_fingerprint
    assert rebuilt.selection_fingerprint == rebuilt.compute_fingerprint()
    assert S.selection_fingerprint({"a": 1}) == S.selection_fingerprint({"a": 1})
    assert S.selection_fingerprint({"a": 1}) != S.selection_fingerprint({"a": 2})


# --- M09: self-reported cannot be promoted --------------------------------------------


def test_m09_self_reported_cannot_be_promoted_by_any_input_path() -> None:
    row = _observation()
    assert row.trust_level is TrustLevel.SELF_REPORTED_VALIDATED
    for change in (
        {"trust_level": "doctor_verified"},
        {
            "trust_level": "doctor_verified",
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
        },
    ):
        with pytest.raises(ValidationError):
            _revalidated(row, **change)
    # Turning every knob at once still cannot relabel a patient check-in: the
    # source must itself be a verified document.
    with pytest.raises(ValidationError):
        _revalidated(
            row,
            trust_level="doctor_verified",
            verified_by=DOCTOR,
            verified_at="2026-11-14T09:00:00Z",
            source_fact_id=FACT_A,
            source_document_id=DOC_A,
        )
    # A doctor-verified projection whose data check failed stays representable and
    # labelled; the admissibility predicate (F2) excludes it downstream — the type
    # does not pretend the row never existed.
    rejected = _revalidated(_verified_observation(), validation=ValidationState.REJECTED)
    assert rejected.trust_level is TrustLevel.DOCTOR_VERIFIED
    assert rejected.validation is ValidationState.REJECTED
    verified = _verified_observation()
    assert verified.trust_level is TrustLevel.DOCTOR_VERIFIED
    assert verified.source_fact_id == FACT_A and verified.source_document_id == DOC_A


def test_m09_selection_manifest_cannot_relabel_a_typed_observation() -> None:
    row = _observation()
    selected = _selected_observation(row)
    with pytest.raises(ValidationError, match="manifest differs"):
        _state(
            observations=[row],
            selection=_manifest(
                observations=[
                    S.SelectedObservationRef(
                        observation_id=OBS_A,
                        trust_level=TrustLevel.DOCTOR_VERIFIED,
                        source_fact_id=FACT_A,
                        observation_created_at=row.measured_at,
                    )
                ]
            ),
        )
    with pytest.raises(ValidationError, match="must be present in observations"):
        _state(selection=_manifest(observations=[selected]))


def test_m09_copy_bypass_is_caught_by_revalidation() -> None:
    row = _observation()
    forged = row.model_copy(
        update={"trust_level": TrustLevel.DOCTOR_VERIFIED}
    )  # bypasses validation by design
    assert forged.trust_level is TrustLevel.DOCTOR_VERIFIED
    with pytest.raises(ValidationError):
        S.ObservationView.model_validate_json(forged.model_dump_json())


# --- M10: pending / rejected is not verified ------------------------------------------


def _extracted(status: S.VerificationStatus, **overrides: Any) -> S.ExtractedFact:
    fields: dict[str, Any] = {
        "fact_id": FACT_A,
        "patient_id": PATIENT,
        "document_id": DOC_A,
        "field_name": FactField.VALUE,
        "raw_text": "140",
        "verification_status": status,
        "provenance": S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A),
    }
    if status is not S.VerificationStatus.PENDING:
        fields.update(verified_by=DOCTOR, verified_at="2026-11-14T09:00:00Z")
    fields.update(overrides)
    return S.ExtractedFact(**fields)


def _verified(**overrides: Any) -> S.VerifiedFact:
    fields: dict[str, Any] = {
        "fact_id": FACT_A,
        "patient_id": PATIENT,
        "document_id": DOC_A,
        "field_name": FactField.VALUE,
        "normalized_value": "140",
        "evidence": [S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A)],
        "verified_by": DOCTOR,
        "verified_at": "2026-11-14T09:00:00Z",
    }
    fields.update(overrides)
    return S.VerifiedFact(**fields)


def test_m10_pending_or_rejected_facts_cannot_be_projected_as_verified() -> None:
    for status in (S.VerificationStatus.PENDING, S.VerificationStatus.REJECTED):
        with pytest.raises(ValidationError, match="pending/rejected"):
            _state(extraction_facts=[_extracted(status)], verified_facts=[_verified()])
    with pytest.raises(ValidationError, match="pending/rejected"):
        _state(
            extraction_facts=[_extracted(S.VerificationStatus.VERIFIED)],
            verified_facts=[_verified(document_id=DOC_B)],
        )
    _state(
        extraction_facts=[_extracted(S.VerificationStatus.VERIFIED)], verified_facts=[_verified()]
    )
    with pytest.raises(ValidationError, match="duplicate"):
        _state(extraction_facts=[_extracted(S.VerificationStatus.PENDING)] * 2)


# --- M11: comparison consistency -------------------------------------------------------


def _comparison(**overrides: Any) -> S.ComparisonResult:
    fields: dict[str, Any] = {
        "measure_type": MeasureType.SYSTOLIC_BP,
        "unit": Unit.MMHG,
        "current_observation_id": OBS_A,
        "baseline_observation_id": OBS_HIST,
        "current_value": Decimal("140.5"),
        "baseline_value": Decimal("140.5"),
        "delta": Decimal("0"),
        "comparable": True,
        "trust_basis": S.TrustBasis.SELF_REPORTED,
    }
    fields.update(overrides)
    return S.ComparisonResult(**fields)


def test_m11_comparable_and_incomparable_shapes_are_mutually_exclusive() -> None:
    _comparison()  # exact zero delta is a valid comparable result
    for bad in (
        {
            "baseline_observation_id": None,
            "baseline_value": None,
            "delta": None,
        },  # comparable w/o baseline
        {"incomparable_reason": S.IncomparableReason.NO_BASELINE},  # comparable with a reason
        {"comparable": False, "delta": Decimal("1")},  # incomparable with a delta
        {"comparable": False, "incomparable_reason": None},  # incomparable w/o reason
        {"delta": Decimal("0.0001")},  # delta must equal current - baseline exactly
        {"baseline_observation_id": OBS_A},  # own baseline
        {"baseline_value": Decimal("0")},
        {"current_value": Decimal("-1")},
        {"unit": Unit.BPM},
        {"trust_basis": "mixed"},
    ):
        with pytest.raises(ValidationError):
            _comparison(**bad)
    _comparison(
        comparable=False,
        baseline_value=None,
        delta=None,
        incomparable_reason=S.IncomparableReason.STALE_BASELINE,
    )
    _comparison(
        comparable=False,
        baseline_observation_id=None,
        baseline_value=None,
        delta=None,
        incomparable_reason=S.IncomparableReason.NOT_ADMISSIBLE,
    )


def test_m11_state_binds_comparison_values_and_trust_basis_to_observations() -> None:
    current = _observation()
    baseline = _verified_observation(
        observation_id=OBS_HIST, value=Decimal("135"), measured_at="2026-11-01T08:00:00Z"
    )
    good = _comparison(
        current_value=Decimal("140.5"),
        baseline_value=Decimal("135"),
        delta=Decimal("5.5"),
        trust_basis=S.TrustBasis.MIXED,
    )
    state = _state(
        observations=[current, baseline],
        comparisons=[good],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    assert state.comparisons[0].trust_basis is S.TrustBasis.MIXED
    for bad in (
        _comparison(
            current_value=Decimal("140.5"),
            baseline_value=Decimal("135"),
            delta=Decimal("5.5"),
            trust_basis=S.TrustBasis.SELF_REPORTED,
        ),  # mixed pair labelled self_reported
        _comparison(
            current_value=Decimal("141"), baseline_value=Decimal("135"), delta=Decimal("6")
        ),
    ):
        with pytest.raises(ValidationError):
            _state(
                observations=[current, baseline],
                comparisons=[bad],
                verification_gate=_gate(),
                last_validated_at_utc=VALIDATED,
            )
    with pytest.raises(ValidationError, match="require a proceed"):
        _state(observations=[current, baseline], comparisons=[good])  # no gate at all
    # Baseline outside the state: the label may only match the current trust or be mixed.
    _state(
        observations=[current],
        comparisons=[_comparison(trust_basis=S.TrustBasis.SELF_REPORTED)],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    with pytest.raises(ValidationError, match="contradicts the current observation"):
        _state(
            observations=[current],
            comparisons=[_comparison(trust_basis=S.TrustBasis.DOCTOR_VERIFIED)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


# --- M12: VI vs DR separation ---------------------------------------------------------


def test_m12_issue_and_rule_vocabularies_are_closed_and_disjoint() -> None:
    assert {item.value for item in S.IssueType} == {f"VI-{n:03d}" for n in range(1, 7)}
    assert {item.value for item in S.ReviewRuleId} == {
        "DR-001",
        "DR-003",
        "DR-005",
        "DR-006",
        "DR-008",
        "DR-009",
    }
    assert not {item.value for item in S.IssueType} & {item.value for item in S.ReviewRuleId}
    with pytest.raises(ValidationError):
        S.GateDetail(decision="halt", blocking_fact_count=1, issue_types=["DR-001"])
    with pytest.raises(ValidationError):
        S.GateIssueRef(issue_type="DR-001", reason_code="x", document_id=DOC_A, message="m")
    for rule in ("DR-002", "DR-004", "DR-007", "DR-010", "VI-001", "DR-000", "DR-0100"):
        with pytest.raises(ValidationError):
            S.ReviewFlag(
                review_item_id=ISSUE_A,
                rule_id=rule,
                reason_code="r",
                message="m",
                trust_basis=S.TrustBasis.DOCTOR_VERIFIED,
                evidence=[S.ProvenanceRef(kind=S.ProvenanceKind.OBSERVATION, observation_id=OBS_A)],
                policy_version="demo-policy-1.1.0",
                dedupe_key=_sha("k"),
            )
    flag = S.ReviewFlag(
        review_item_id=ISSUE_A,
        rule_id=S.ReviewRuleId.DR_008,
        reason_code="duplicate",
        message="m",
        workflow_hint=S.ReviewHint.DATA_QUALITY,
        trust_basis=S.TrustBasis.SELF_REPORTED,
        evidence=[S.ProvenanceRef(kind=S.ProvenanceKind.OBSERVATION, observation_id=OBS_A)],
        policy_version="demo-policy-1.1.0",
        dedupe_key=_sha("k"),
    )
    assert flag.demo_only is True and flag.state is S.ReviewItemState.OPEN


def test_m12_state_verification_issues_mirror_the_gate_evaluation() -> None:
    gate = _gate(S.GateDecision.HALT)
    issue = S.VerificationIssue(
        issue_id=ISSUE_A,
        issue_type=S.IssueType.VI_001,
        reason_code="pending_fact",
        message="One fact is pending verification.",
        document_id=DOC_A,
        fact_ids=[FACT_A],
        evidence=[S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A)],
        created_at=VALIDATED,
    )
    halted = _state(
        status=S.RunStatus.NEEDS_VERIFICATION,
        halt_reason=S.HaltReason.UNVERIFIED_FACTS,
        last_validated_at_utc=VALIDATED,
        verification_gate=gate,
        verification_issues=[issue],
    )
    assert halted.halt_reason is S.HaltReason.UNVERIFIED_FACTS
    with pytest.raises(ValidationError, match="mirror the gate"):
        _state(
            status=S.RunStatus.NEEDS_VERIFICATION,
            halt_reason=S.HaltReason.UNVERIFIED_FACTS,
            last_validated_at_utc=VALIDATED,
            verification_gate=gate,
        )
    with pytest.raises(ValidationError, match="needs_verification requires"):
        _state(
            status=S.RunStatus.NEEDS_VERIFICATION,
            halt_reason=S.HaltReason.UNVERIFIED_FACTS,
            last_validated_at_utc=VALIDATED,
            verification_gate=_gate(),
        )
    with pytest.raises(ValidationError, match="blocking"):
        S.VerificationIssue(
            issue_id=ISSUE_A,
            issue_type=S.IssueType.VI_001,
            reason_code="r",
            message="m",
            evidence=[S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A)],
            created_at=VALIDATED,
            blocking=False,
        )


# --- M13: F1 proceed / halt / unavailable ---------------------------------------------


def test_m13_gate_decision_combinations() -> None:
    _gate(S.GateDecision.PROCEED)
    _gate(S.GateDecision.HALT)
    _gate(S.GateDecision.UNAVAILABLE)
    for bad in (
        {"decision": S.GateDecision.PROCEED, "blocking_fact_count": 1},
        {"decision": S.GateDecision.HALT, "blocking_fact_count": 0},
        {"decision": S.GateDecision.HALT, "issues": []},
        {"decision": S.GateDecision.PROCEED, "issues": _gate(S.GateDecision.HALT).issues},
        {"decision": S.GateDecision.UNAVAILABLE, "unavailable_reason": None},
        {
            "decision": S.GateDecision.PROCEED,
            "unavailable_reason": S.GateUnavailableReason.INVALID_RUN_CLOCK,
        },
        {"decision": "paused"},
        {"gate_evaluated": False},
        {"runtime_evaluable": True},
        {"unavailable_reason": "made_up_reason"},
    ):
        with pytest.raises(ValidationError):
            _gate(**bad)
    assert _gate().runtime_evaluable is False and _gate().gate_evaluated is True


def test_m13_unavailable_reason_vocabulary_matches_the_f1_service() -> None:
    source = (REPO_ROOT / "backend" / "app" / "services" / "p5_run_gate.py").read_text(
        encoding="utf-8"
    )
    emitted = set(re.findall(r'unavailable = "([a-z0-9_]+)"', source))
    assert emitted, "F1 source scan found no unavailable reasons"
    assert emitted == {item.value for item in S.GateUnavailableReason}


def test_m13_state_reactions_to_each_decision() -> None:
    # halt + needs_verification is consistent; halt + post-draft is impossible
    _state(
        status=S.RunStatus.NEEDS_VERIFICATION,
        halt_reason=S.HaltReason.UNVERIFIED_FACTS,
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(S.GateDecision.HALT),
        verification_issues=[
            S.VerificationIssue(
                issue_id=ISSUE_A,
                issue_type=S.IssueType.VI_001,
                reason_code="pending_fact",
                message="m",
                document_id=DOC_A,
                evidence=[S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A)],
                created_at=VALIDATED,
            )
        ],
    )
    with pytest.raises(ValidationError, match="halting gate cannot coexist"):
        _approved_state(
            S.RunStatus.AWAITING_DECISION,
            approval=None,
            verification_gate=_gate(S.GateDecision.HALT),
        )
    # unavailable: representable on a queued run, never alongside a draft
    _state(last_validated_at_utc=VALIDATED, verification_gate=_gate(S.GateDecision.UNAVAILABLE))
    with pytest.raises(ValidationError, match="require a proceed"):
        _approved_state(
            S.RunStatus.AWAITING_DECISION,
            approval=None,
            verification_gate=_gate(S.GateDecision.UNAVAILABLE),
        )
    # gate evaluation alone changes nothing about completion
    gated = _state(last_validated_at_utc=VALIDATED, verification_gate=_gate())
    assert gated.workflow_completed is False and gated.status is S.RunStatus.QUEUED


# --- M14: typed node trace -------------------------------------------------------------


def _event(node: S.NodeName, **overrides: Any) -> S.NodeEvent:
    fields: dict[str, Any] = {"node": node, "started_at": STARTED, "ended_at": STARTED}
    fields.update(overrides)
    return S.NodeEvent(**fields)


def test_m14_detail_is_mandatory_iff_the_node_makes_a_bounded_decision() -> None:
    for node in S.NodeName:
        if node in S.DETAIL_KIND_BY_NODE:
            with pytest.raises(ValidationError, match="must carry exactly one"):
                _event(node)
        else:
            assert _event(node).detail is None
    triage = S.TriageDetail(
        path_selected=S.TriagePath.TEXT_LAYER,
        path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
        document_id=DOC_A,
        attempt_index=1,
        preprocessing_applied=False,
    )
    with pytest.raises(ValidationError, match="must carry exactly one gate"):
        _event(S.NodeName.FACT_VERIFY_GATE, detail=triage)
    with pytest.raises(ValidationError, match="detail must be null"):
        _event(S.NodeName.INTAKE_VALIDATE, detail=triage)
    assert _event(S.NodeName.EXTRACTION_TRIAGE, detail=triage).detail is triage


def test_m14_discriminated_union_rejects_unknown_kinds_and_mismatched_payloads() -> None:
    good = {
        "node": "draft_validation",
        "started_at": STARTED,
        "detail": {"kind": "validation", "validation_outcome": "accept", "attempt_index": 1},
    }
    assert S.NodeEvent.model_validate_json(json.dumps(good)).detail is not None
    for bad in (
        {**good, "detail": {"kind": "validation"}},  # missing required members
        {**good, "detail": {"kind": "triage", "validation_outcome": "accept", "attempt_index": 1}},
        {**good, "detail": {"kind": "prose", "text": "anything"}},
        {
            **good,
            "detail": {
                "kind": "validation",
                "validation_outcome": "accept",
                "attempt_index": 1,
                "note": "x",
            },
        },
        {
            **good,
            "detail": {"kind": "validation", "validation_outcome": "accepted", "attempt_index": 1},
        },
    ):
        with pytest.raises(ValidationError):
            S.NodeEvent.model_validate_json(json.dumps(bad))


def test_m14_trace_details_carry_no_free_text_or_unbounded_fields() -> None:
    for model in (S.TriageDetail, S.ValidationDetail, S.GateDetail, S.FinalizeDetail):
        for name, info in model.model_fields.items():
            if info.annotation is str:
                # the only string fields are canonical UUIDs enforced by an AfterValidator
                assert any(isinstance(item, AfterValidator) for item in info.metadata), (
                    f"{model.__name__}.{name} is free text"
                )
    text = S.TriageDetail.model_json_schema()
    assert "document text" not in json.dumps(text)


def test_m14_tool_allowlist_is_per_node() -> None:
    assert set(S.NODE_TOOLS) == set(S.NodeName)
    details: dict[S.NodeName, Any] = {
        S.NodeName.EXTRACTION_TRIAGE: S.TriageDetail(
            path_selected=S.TriagePath.TEXT_LAYER,
            path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
            document_id=DOC_A,
            attempt_index=1,
            preprocessing_applied=False,
        ),
        S.NodeName.FACT_VERIFY_GATE: S.GateDetail(decision="proceed", blocking_fact_count=0),
        S.NodeName.DRAFT_VALIDATION: S.ValidationDetail(
            validation_outcome=S.ValidationOutcome.ACCEPT, attempt_index=1
        ),
        S.NodeName.FINALIZE_ACTIONS: S.FinalizeDetail(
            approval_decision="approve", task_created=False, notification_created=False
        ),
    }
    for node, allowed in S.NODE_TOOLS.items():
        if allowed:
            _event(node, tools_called=list(allowed), detail=details.get(node))
        for tool in set(S.ToolName) - allowed:
            with pytest.raises(ValidationError, match="allowlist"):
                _event(node, tools_called=[tool], detail=details.get(node))
    with pytest.raises(ValidationError, match="duplicate"):
        _event(S.NodeName.DOCUMENT_EXTRACT, tools_called=[S.ToolName.EXTRACT_DOCUMENT] * 2)
    with pytest.raises(ValidationError):
        _event(S.NodeName.INTAKE_VALIDATE, tools_called=["extract_document"])  # str in Python mode
    with pytest.raises(ValidationError, match="ended_at precedes"):
        _event(S.NodeName.INTAKE_VALIDATE, ended_at="2026-11-23T09:59:59Z")
    with pytest.raises(ValidationError, match="zero blocking"):
        S.GateDetail(decision="proceed", blocking_fact_count=1)
    with pytest.raises(ValidationError, match="notification"):
        S.FinalizeDetail(approval_decision="approve", task_created=False, notification_created=True)
    with pytest.raises(ValidationError):
        S.FinalizeDetail(approval_decision="reject", task_created=False, notification_created=False)


def test_m14_trace_path_vocabulary_matches_the_openapi_contract() -> None:
    spec = yaml.safe_load(
        (REPO_ROOT / "docs" / "contracts" / "openapi.phase0.yaml").read_text(encoding="utf-8")
    )
    triage = spec["components"]["schemas"]["TriageEventDetail"]["properties"]
    assert set(triage["path_selected"]["enum"]) == {item.value for item in S.TriagePath}
    assert set(triage["path_reason"]["enum"]) == {item.value for item in S.PathReason}
    validation = spec["components"]["schemas"]["ValidationEventDetail"]["properties"]
    assert set(validation["validation_outcome"]["enum"]) == {
        item.value for item in S.ValidationOutcome
    }
    assert set(validation["violation_codes"]["items"]["enum"]) == {
        item.value for item in S.ViolationCode
    }
    gate = spec["components"]["schemas"]["GateEventDetail"]["properties"]
    assert set(gate["decision"]["enum"]) == {"proceed", "halt"}  # trace stays two-valued
    finalize = spec["components"]["schemas"]["FinalizeEventDetail"]["properties"]
    assert set(finalize["approval_decision"]["enum"]) == {"approve", "edit", "reject"}
    models = (REPO_ROOT / "backend" / "app" / "db" / "models.py").read_text(encoding="utf-8")
    workflow_run = models.split("class WorkflowRun(")[1].split("\n\nclass ")[0]
    statuses = re.search(r"status IN \((.*?)\)", workflow_run, re.S)
    assert statuses is not None
    assert set(re.findall(r"'([a-z_]+)'", statuses.group(1))) == {
        item.value for item in S.RunStatus
    }


# --- M15: retry budget -----------------------------------------------------------------


def test_m15_retry_counts_are_bounded_and_keyed_by_node() -> None:
    state = _state(retry_counts={S.NodeName.DOCUMENT_EXTRACT: 1, S.NodeName.DRAFT_SUMMARY: 5})
    assert state.retry_counts[S.NodeName.DOCUMENT_EXTRACT] == 1
    for bad in (
        {S.NodeName.DOCUMENT_EXTRACT: 0},
        {S.NodeName.DOCUMENT_EXTRACT: 6},
        {"document_extract": 1},
        {S.NodeName.HALTED: -1},
    ):
        with pytest.raises(ValidationError):
            _state(retry_counts=bad)
    payload = _json(_state())
    payload["retry_counts"] = {"not_a_node": 2}
    with pytest.raises(ValidationError):
        S.SharedGraphState.model_validate_json(json.dumps(payload))


# --- M16: review completion is not workflow completion --------------------------------


def _sealed_state(**overrides: Any) -> S.SharedGraphState:
    observation = _verified_observation()
    fields: dict[str, Any] = {
        "observations": [observation],
        "selection": _manifest(observations=[_selected_observation(observation)]),
        "last_validated_at_utc": VALIDATED,
        "verification_gate": _gate(),
        "evaluable_evidence": _evidence(selected_observation_ids=[OBS_B]),
        "review_persistence": _sealed(),
    }
    fields.update(overrides)
    return _state(**fields)


def test_m16_sealed_evaluation_does_not_complete_the_workflow() -> None:
    sealed = _sealed_state()  # status stays queued
    assert sealed.review_evaluation_sealed is True
    assert sealed.workflow_completed is False
    assert sealed.review_persistence is not None and sealed.review_persistence.kind == "sealed"
    completed = _approved_state(S.RunStatus.COMPLETED)
    assert completed.workflow_completed is True
    assert (
        completed.review_evaluation_sealed is False
    )  # completion without a sealed evaluation is legal
    both = _sealed_state(
        status=S.RunStatus.COMPLETED,
        draft_summary=_approved_state(S.RunStatus.COMPLETED).draft_summary,
        approval=_approved_state(S.RunStatus.COMPLETED).approval,
    )
    assert both.workflow_completed and both.review_evaluation_sealed


def test_m16_sealed_evaluation_is_bound_to_its_evidence_and_all_or_nothing() -> None:
    for bad in (
        {"review_items_persisted": 0},
        {"evidence_links_persisted": 0},
        {"bridge_input_fingerprint_sha256": _sha("other-bridge")},
        {"gate_evaluation_id": OBS_A},
        {"patient_id": OTHER_PATIENT},
        {"dr006_policy": "allowed"},
        {"evaluation_completed": False},
        {"runtime_evaluable": True},
        {"policy_status": "approved"},
    ):
        with pytest.raises(ValidationError):
            _sealed_state(review_persistence=_sealed(**bad))
    with pytest.raises(ValidationError, match="requires the F2 evidence"):
        _state(
            last_validated_at_utc=VALIDATED, verification_gate=_gate(), review_persistence=_sealed()
        )


def test_m16_denied_persistence_is_an_outcome_not_a_completion() -> None:
    denied = S.DeniedReviewPersistence(
        reason=RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED, observed_at_utc=VALIDATED
    )
    state = _state(review_persistence=denied)
    assert state.review_evaluation_sealed is False
    assert state.workflow_completed is False
    assert denied.writes_performed == 0 and "evaluation_id" not in denied.model_dump()
    for bad in (
        {"writes_performed": 1},
        {"reason": "made_up"},
        {"kind": "sealed"},  # discriminator mismatch
    ):
        with pytest.raises(ValidationError):
            S.DeniedReviewPersistence(
                **{
                    "reason": RB3DenialReason.INTEGRITY_CONFLICT,
                    "observed_at_utc": VALIDATED,
                    **bad,
                }
            )
    assert S.RB3DenialReason is RB3DenialReason  # single source of truth
    for reason in RB3DenialReason:
        S.DeniedReviewPersistence(reason=reason, observed_at_utc=VALIDATED)


def test_m16_resume_classification_distinguishes_unchanged_changed_and_corrected() -> None:
    same = _sha("same")
    unchanged = S.ResumeAssessment(
        disposition=S.ResumeDisposition.RESUME_UNCHANGED,
        app_db_status=S.RunStatus.AWAITING_DECISION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=same,
        sealed_evaluation_present=True,
        checkpoint_present=True,
    )
    assert unchanged.corrected_fact_ids == []
    changed = S.ResumeAssessment(
        disposition=S.ResumeDisposition.CHANGED_SOURCE_IDENTITY,
        app_db_status=S.RunStatus.NEEDS_VERIFICATION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=_sha("changed"),
        sealed_evaluation_present=False,
        checkpoint_present=False,
    )
    corrected = S.ResumeAssessment(
        disposition=S.ResumeDisposition.CORRECTED_SOURCE_NEW_RUN,
        app_db_status=S.RunStatus.AWAITING_DECISION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=same,
        corrected_fact_ids=[FACT_A],
        sealed_evaluation_present=True,
        checkpoint_present=True,
    )
    assert changed.disposition is S.ResumeDisposition.CHANGED_SOURCE_IDENTITY
    assert corrected.disposition is S.ResumeDisposition.CORRECTED_SOURCE_NEW_RUN
    for bad in (
        {
            "disposition": S.ResumeDisposition.RESUME_UNCHANGED,
            "observed_selection_fingerprint": _sha("changed"),
        },
        {"disposition": S.ResumeDisposition.RESUME_UNCHANGED, "corrected_fact_ids": [FACT_A]},
        {"disposition": S.ResumeDisposition.CHANGED_SOURCE_IDENTITY},
        {
            "disposition": S.ResumeDisposition.CHANGED_SOURCE_IDENTITY,
            "corrected_fact_ids": [FACT_A],
        },
        {"disposition": S.ResumeDisposition.CORRECTED_SOURCE_NEW_RUN},
        {"corrected_fact_ids": [FACT_A, FACT_A]},
    ):
        with pytest.raises(ValidationError):
            S.ResumeAssessment(
                **{
                    "disposition": unchanged.disposition,
                    "app_db_status": S.RunStatus.QUEUED,
                    "stored_selection_fingerprint": same,
                    "observed_selection_fingerprint": same,
                    "sealed_evaluation_present": False,
                    "checkpoint_present": False,
                    **bad,
                }
            )
    assert (
        "reuse_sealed_evaluation" not in S.ResumeAssessment.model_fields
    )  # no reuse path exists by design


# --- M17: unapproved runtime policy boundary ------------------------------------------


def test_m17_honesty_literals_cannot_be_flipped_through_any_input() -> None:
    payload = _json(_state())
    for field, bad in (
        ("policy_status", "approved"),
        ("runtime_policy_activated", True),
        ("runtime_evaluable", True),
        ("demo_only", False),
        ("not_for_clinical_use", False),
    ):
        with pytest.raises(ValidationError, match=field):
            S.SharedGraphState.model_validate_json(json.dumps({**payload, field: bad}))
    with pytest.raises(ValidationError, match="policy_status"):
        _state(policy_status="approved")
    evidence = _json(_evidence())
    for field, bad in (
        ("rules_executed", True),
        ("runtime_evaluable", True),
        ("policy_status", "approved"),
        ("bridge_validated", False),
    ):
        with pytest.raises(ValidationError):
            S.EvaluableEvidenceRef.model_validate_json(json.dumps({**evidence, field: bad}))
    sealed = _json(_sealed())
    for field, bad in (
        ("offline_evaluator_invoked", False),
        ("runtime_evaluable", True),
        ("policy_status", "approved"),
        ("demo_only", False),
    ):
        with pytest.raises(ValidationError):
            S.SealedReviewEvaluation.model_validate_json(json.dumps({**sealed, field: bad}))
    flag = {
        "review_item_id": ISSUE_A,
        "rule_id": "DR-008",
        "reason_code": "r",
        "message": "m",
        "trust_basis": "mixed",
        "evidence": [{"kind": "observation", "observation_id": OBS_A}],
        "policy_version": "demo-policy-1.1.0",
        "dedupe_key": _sha("k"),
        "demo_only": False,
    }
    with pytest.raises(ValidationError, match="demo_only"):
        S.ReviewFlag.model_validate_json(json.dumps(flag))


def test_m17_model_copy_bypass_is_documented_and_revalidation_restores_the_boundary() -> None:
    state = _state()
    forged = state.model_copy(
        update={"runtime_policy_activated": True, "policy_status": "approved"}
    )
    assert forged.runtime_policy_activated is True  # the bypass is real: frozen ≠ authority
    with pytest.raises(ValidationError):
        S.SharedGraphState.model_validate_json(forged.model_dump_json())
    with pytest.raises(ValidationError, match="policy_status"):
        _state(policy_status="approved")


# --- M18: deserialization creates no approval / task / execution authority -------------


def test_m18_deserialized_state_fields_are_shapes_not_authority() -> None:
    forbidden = {
        "approved",
        "approval_granted",
        "gate_passed",
        "run_gate_completed",
        "cleared",
        "authorized",
        "executed",
    }
    assert not forbidden & set(S.SharedGraphState.model_fields)
    assert not {"verified", "trusted", "grounded"} & set(S.ApprovalDecision.model_fields)
    # approval shape validates on its own — and authorizes nothing on its own
    decision = S.ApprovalDecision(
        decision_id=APPROVAL_ID,
        decision=S.ApprovalChoice.APPROVE,
        doctor_id=DOCTOR,
        decided_at=VALIDATED,
    )
    assert decision.recorded is True
    # but it cannot be attached to a pre-draft run
    with pytest.raises(ValidationError, match="no approval can exist before"):
        _state(approval=decision)
    with pytest.raises(ValidationError, match="finalizing/completed require"):
        _state(status=S.RunStatus.COMPLETED, approval=decision)
    with pytest.raises(ValidationError, match="awaiting_decision has a draft"):
        _state(status=S.RunStatus.AWAITING_DECISION, approval=None)
    # an approval is bound to a consistent status and a draft through the proceed gate
    approved = _approved_state(S.RunStatus.AWAITING_DECISION, approval=None)
    assert approved.approval is None and approved.draft_summary is not None
    _approved_state(S.RunStatus.FINALIZING)
    _approved_state(S.RunStatus.COMPLETED)


def test_m18_tasks_exist_only_after_a_decision_and_within_its_task_ids() -> None:
    task = S.TaskDraft(
        action_key=_sha("task"), task_id=DERIVED_TASK, title="Call the patient (synthetic)"
    )
    with pytest.raises(ValidationError, match="task drafts exist only after"):
        _state(pending_tasks=[task])
    with pytest.raises(ValidationError, match="must reference pending task drafts"):
        _approved_state(S.RunStatus.FINALIZING, created_task_ids=[DERIVED_TASK])
    ok = _approved_state(
        S.RunStatus.FINALIZING, pending_tasks=[task], created_task_ids=[DERIVED_TASK]
    )
    assert ok.created_task_ids == [DERIVED_TASK]
    with pytest.raises(ValidationError, match="task_created must match"):
        _approved_state(
            S.RunStatus.COMPLETED,
            pending_tasks=[task],
            created_task_ids=[],
            events=[
                _event(
                    S.NodeName.FINALIZE_ACTIONS,
                    detail=S.FinalizeDetail(
                        approval_decision="approve", task_created=True, notification_created=True
                    ),
                )
            ],
        )
    with pytest.raises(ValidationError, match="UUIDv5"):
        S.TaskDraft(action_key=_sha("task"), task_id=RUN, title="t")
    namespace = UUID(DOC_A)
    assert S.derive_task_id(namespace, "action") == S.derive_task_id(namespace, "action")
    assert UUID(S.derive_task_id(namespace, "action")).version == 5
    assert S.derive_task_id(namespace, "action") != S.derive_task_id(UUID(DOC_B), "action")


def test_m18_status_lifecycle_invariants() -> None:
    # halt_reason iff halted
    with pytest.raises(ValidationError, match="halt_reason is present iff"):
        _state(halt_reason=S.HaltReason.MODEL_FAILED)
    for status in (
        S.RunStatus.NEEDS_VERIFICATION,
        S.RunStatus.FAILED_RETRYABLE,
        S.RunStatus.FAILED_TERMINAL,
    ):
        with pytest.raises(ValidationError, match="halt_reason is present iff"):
            _state(status=status)
    # needs_verification must halt on unverified facts with a halting gate
    with pytest.raises(ValidationError, match="unverified_facts"):
        _state(status=S.RunStatus.NEEDS_VERIFICATION, halt_reason=S.HaltReason.RETRY_EXHAUSTED)
    # failed_retryable must be retry_exhausted
    with pytest.raises(ValidationError, match="retry_exhausted"):
        _state(status=S.RunStatus.FAILED_RETRYABLE, halt_reason=S.HaltReason.MODEL_FAILED)
    assert (
        _state(
            status=S.RunStatus.FAILED_RETRYABLE, halt_reason=S.HaltReason.RETRY_EXHAUSTED
        ).halt_reason
        is S.HaltReason.RETRY_EXHAUSTED
    )
    assert (
        _state(status=S.RunStatus.FAILED_TERMINAL, halt_reason=S.HaltReason.MODEL_FAILED).status
        is S.RunStatus.FAILED_TERMINAL
    )
    with pytest.raises(ValidationError, match="updated_at precedes"):
        _state(updated_at="2026-11-23T09:59:59Z")


def test_m18_evidence_reference_is_bound_to_the_selection_and_gate() -> None:
    good = _state(
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(),
        evaluable_evidence=_evidence(
            selected_observation_ids=[], no_current_reason="no_current_selected"
        ),
    )
    assert (
        good.evaluable_evidence is not None
        and good.evaluable_evidence.no_current_reason == "no_current_selected"
    )
    for bad in (
        {"selected_document_ids": [DOC_B]},
        {"gate_input_fingerprint_sha256": _sha("other-gate")},
        {"policy_version": "demo-policy-1.2.0"},
        {"as_of_utc": "2026-11-15T12:00:00Z"},
    ):
        with pytest.raises(ValidationError):
            _state(
                last_validated_at_utc=VALIDATED,
                verification_gate=_gate(),
                evaluable_evidence=_evidence(**bad),
            )
    with pytest.raises(ValidationError, match="requires the gate evaluation"):
        _state(last_validated_at_utc=VALIDATED, evaluable_evidence=_evidence())
    with pytest.raises(ValidationError, match="only follow a proceed"):
        _state(
            last_validated_at_utc=VALIDATED,
            verification_gate=_gate(S.GateDecision.HALT),
            evaluable_evidence=_evidence(),
        )
    # absent vs empty is explicit: None ≠ an evaluated projection with zero current observations
    assert _state().evaluable_evidence is None
    assert good.evaluable_evidence.selected_observation_ids == []


def test_m18_draft_provider_and_execution_status_are_consistent() -> None:
    def draft(**overrides: Any) -> S.DraftSummary:
        fields: dict[str, Any] = {
            "draft_id": APPROVAL_ID,
            "provider": S.DraftProvider.OLLAMA,
            "model": "llama3.1:8b",
            "execution_status": S.DraftExecutionStatus.MODEL_OK,
            "prompt_version": "draft-v1",
            "latency_ms": 900,
            "created_at": VALIDATED,
        }
        fields.update(overrides)
        return S.DraftSummary(**fields)

    ok = draft()
    assert ok.disclaimer == "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"
    for bad in (
        {"model": None},
        {"execution_status": S.DraftExecutionStatus.MODEL_TIMEOUT},
        {"provider": S.DraftProvider.DETERMINISTIC_FALLBACK},
        {"prompt_version": "draft v1"},
        {"latency_ms": -1},
        {"uncertainties": ["x" * 241]},
        {"disclaimer": "Educational only"},
    ):
        with pytest.raises(ValidationError):
            draft(**bad)
    fallback = draft(
        provider=S.DraftProvider.DETERMINISTIC_FALLBACK,
        model=None,
        execution_status=S.DraftExecutionStatus.FALLBACK_NO_MODEL,
        latency_ms=None,
    )
    assert fallback.model is None


# --- M19: mutable-default isolation ---------------------------------------------------


def test_m19_defaults_are_not_shared_between_instances() -> None:
    first = _state()
    second = _state()
    assert first.observations is not second.observations
    assert first.retry_counts is not second.retry_counts
    first.observations.append(_observation())
    first.retry_counts[S.NodeName.HALTED] = 1
    first.events.append(_event(S.NodeName.INTAKE_VALIDATE))
    first.model_metadata["provider"] = "ollama"
    assert second.observations == [] and second.retry_counts == {} and second.events == []
    assert second.model_metadata == {}
    # Pydantic's own default-factory semantics are what we rely on; nothing is mocked.
    assert S.SharedGraphState.model_fields["observations"].default_factory is not None
    assert (
        S.SharedGraphState.model_fields["identity"].default_factory is None
    )  # required, no shared default


# --- M20: import / execution side-effect boundaries -----------------------------------


FORBIDDEN_MODULE_PREFIXES = (
    "langgraph",
    "app.main",
    "app.api",
    "app.db",
    "app.services",
    "app.llm",
    "sqlalchemy",
    "sqlite3",
    "requests",
    "httpx",
    "ollama",
    "fastapi",
    "alembic",
)
IO_TOKENS = (
    "datetime.now(",
    "utcnow(",
    "time.time(",
    "subprocess",
    "socket",
    "open(",
    "Path(",
    "os.environ",
    "print(",
)


def test_m20_importing_the_state_module_loads_no_service_or_runtime_module() -> None:
    code = (
        "import json, sys\n"
        "before = set(sys.modules)\n"
        "import app.agents.state as state\n"
        "after = set(sys.modules)\n"
        "loaded = sorted(m for m in after - before if m.startswith('app') or m.startswith('langgraph'))\n"
        "print(json.dumps({'loaded': loaded, 'has_db': 'app.db' in sys.modules, 'has_services': 'app.services' in sys.modules}))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT / "backend",
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONPATH": str(REPO_ROOT / "backend"), "PATH": "/usr/bin:/bin"},
    )
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report["has_db"] is False and report["has_services"] is False
    assert report["loaded"] == [
        "app",
        "app.agents",
        "app.agents.state",
        "app.core",
        "app.core.enums",
        "app.core.version",
        "app.schemas",
        "app.schemas.p4_rb3_review_persistence",
        "app.schemas.system",
    ]
    for name in report["loaded"]:
        assert not name.startswith(FORBIDDEN_MODULE_PREFIXES), name


def test_m20_state_source_has_no_runtime_or_io_imports_or_calls() -> None:
    text = STATE_MODULE.read_text(encoding="utf-8")
    for prefix in FORBIDDEN_MODULE_PREFIXES:
        for pattern in (f"import {prefix}", f"from {prefix}"):
            assert pattern not in text, pattern
    for token in IO_TOKENS:
        assert re.search(r"(?<![A-Za-z_])" + re.escape(token), text) is None, token
    imported = set(re.findall(r"^(?:from|import)\s+([\w\.]+)", text, re.M))
    assert imported == {
        "__future__",
        "json",
        "uuid",
        "datetime",
        "decimal",
        "enum",
        "hashlib",
        "typing",
        "pydantic",
        "app.core.enums",
        "app.schemas.p4_rb3_review_persistence",
    }


def test_m20_vocabulary_single_sources_of_truth() -> None:
    # enums reused from app.core.enums are the same objects (no drift possible)
    assert S.MeasureType is MeasureType and S.TrustLevel is TrustLevel and S.Unit is Unit
    assert S.ObservationSource is ObservationSource and S.ValidationState is ValidationState
    # exclusion reasons cover what the F2 bridge and admissibility predicate actually emit
    bridge = (REPO_ROOT / "backend" / "app" / "services" / "p5_evidence_bridge.py").read_text(
        encoding="utf-8"
    )
    monitoring = (REPO_ROOT / "backend" / "app" / "services" / "monitoring.py").read_text(
        encoding="utf-8"
    )
    bridge_codes = set(re.findall(r'return "([a-z_]+)"', bridge))
    admissible_codes = set(
        re.findall(
            r'return "([a-z_]+)"',
            monitoring.split("def admissibility_reason")[1].split("def _trust_basis")[0],
        )
    )
    members = {item.value for item in S.ExclusionReason}
    assert {
        "verified_lineage_unavailable",
        "verified_mapping_unproven",
        "stored_trust_source_mismatch",
        "malformed_history",
    } <= members
    assert bridge_codes <= members, bridge_codes - members
    assert admissible_codes == {
        "validation_rejected",
        "unit_mismatch",
        "missing_timestamp",
        "future_timestamp",
    }
    assert admissible_codes <= members
    assert (
        S.derived_trust_basis(
            TrustLevel.SELF_REPORTED_VALIDATED, TrustLevel.SELF_REPORTED_VALIDATED
        )
        is S.TrustBasis.SELF_REPORTED
    )
    assert (
        S.derived_trust_basis(TrustLevel.DOCTOR_VERIFIED, TrustLevel.SELF_REPORTED_VALIDATED)
        is S.TrustBasis.MIXED
    )
    assert S.derived_trust_basis(TrustLevel.DOCTOR_VERIFIED, None) is S.TrustBasis.DOCTOR_VERIFIED


def test_m20_state_round_trips_through_every_outcome_kind() -> None:
    """A fully populated state (halt, resumed, approved, sealed) survives one round trip."""
    sealed = _sealed_state(
        status=S.RunStatus.COMPLETED,
        draft_summary=_approved_state(S.RunStatus.COMPLETED).draft_summary,
        approval=_approved_state(S.RunStatus.COMPLETED).approval,
        pending_tasks=[
            S.TaskDraft(action_key=_sha("task"), task_id=DERIVED_TASK, title="Synthetic follow-up")
        ],
        created_task_ids=[DERIVED_TASK],
        events=[
            _event(
                S.NodeName.FACT_VERIFY_GATE,
                detail=S.GateDetail(decision="proceed", blocking_fact_count=0),
            ),
            _event(
                S.NodeName.EXTRACTION_TRIAGE,
                detail=S.TriageDetail(
                    path_selected=S.TriagePath.TEXT_LAYER,
                    path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                    document_id=DOC_A,
                    attempt_index=1,
                    engine_confidence=0.93,
                    preprocessing_applied=False,
                ),
            ),
            _event(
                S.NodeName.FINALIZE_ACTIONS,
                detail=S.FinalizeDetail(
                    approval_decision="approve", task_created=True, notification_created=True
                ),
                tools_called=[S.ToolName.CREATE_IN_APP_TASK],
            ),
        ],
        checkpoint=S.CheckpointRef(
            checkpoint_id="ckpt-final",
            thread_id=RUN,
            last_completed_node=S.NodeName.FINALIZE_ACTIONS,
            claimed_status=S.RunStatus.COMPLETED,
        ),
    )
    text = sealed.model_dump_json()
    revived = S.SharedGraphState.model_validate_json(text)
    assert revived == sealed and revived.model_dump_json() == text
    assert (
        revived.workflow_completed
        and revived.review_evaluation_sealed
        and not revived.checkpoint_diverges
    )
    assert revived.runtime_evaluable is False and revived.policy_status == "unapproved"
    # the only truth the deserialized shape carries is its own status field
    assert (
        revived.status is S.RunStatus.COMPLETED
        and revived.approval is not None
        and revived.approval.decision is S.ApprovalChoice.APPROVE
    )
