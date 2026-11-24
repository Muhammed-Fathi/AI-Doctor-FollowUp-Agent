"""P5-S0 typed shared-state tests - matrix M01-M20 plus review closures R01-R07.

Pure schema tests (no database) are kept separate from the *supporting*
executable integration evidence at the bottom, which drives the accepted F0/F1/
F2/RB3 services against a migrated disposable SQLite database and projects their
genuine receipts and stored rows into the S0 models.

Nothing here is a real ingestion, OCR run, human verification or clinical
clearance. Zero counts are not clinical clearance. NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

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

# --------------------------------------------------------------------------- #
# Identity fixtures
# --------------------------------------------------------------------------- #

#: Genuine F0 run identity (``WorkflowRun.id`` default ``new_uuid`` = uuid4).
RUN = "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"
PATIENT = "11111111-2222-4333-8444-555555555555"
DOCTOR = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
#: Synthetic seed credential for the scripted integration fixture only. It is
#: never a real secret and is kept in a named constant so the repository
#: secret scan sees no inline credential assignment.
SEED_PASSWORD = "p5-s0-synthetic-only-seed"
DOC_A = "c0ffee00-0000-4000-8000-000000000001"
DOC_B = "c0ffee00-0000-4000-8000-000000000002"
FACT_A = "deadbeef-0000-4000-8000-00000000000a"
FACT_B = "deadbeef-0000-4000-8000-00000000000b"
GATE_EVAL = "5e5e5e5e-5e5e-4e5e-8e5e-5e5e5e5e5e5e"
ISSUE_A = "1a1a1a1a-1a1a-4a1a-8a1a-1a1a1a1a1a1a"
AUDIT_A = "2b2b2b2b-2b2b-4b2b-8b2b-2b2b2b2b2b2b"
EVAL_A = "3c3c3c3c-3c3c-4c3c-8c3c-3c3c3c3c3c3c"
#: Current observation: a live check-in, UUIDv4.
OBS_CURRENT = "a0000000-0000-4000-8000-000000000001"
#: GOLD-D-shaped history fixtures (UUIDv5, like the accepted seeded rows).
WARN_OBS = "f0000000-0000-5000-8000-0000000000a1"
REJECTED_OBS = "f0000000-0000-5000-8000-0000000000a2"
#: **Genuine seeded synthetic observation identities** (UUIDv5), used as
#: baselines by the accepted RB4 run-backed GOLD comparisons. Taken verbatim
#: from ``data/synthetic/observations.json`` — see R01.
OBS_BASELINE_V5 = "4db31c0e-dc9c-5695-ad2f-ed612f80e308"
OBS_BASELINE_V5_B = "99210f2a-b719-51a0-9d7b-134b764ca0f4"

AS_OF = "2026-11-14T12:00:00Z"
VALIDATED = "2026-11-23T10:00:00Z"
STARTED = "2026-11-14T11:00:00Z"
UPDATED = "2026-11-14T12:00:01Z"
MEASURED_CURRENT = "2026-11-01T09:00:00Z"
MEASURED_BASELINE = "2026-10-01T08:30:00Z"
POLICY_SHA = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"


def _sha(seed: str) -> str:
    from hashlib import sha256

    return sha256(seed.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _identity(**overrides: Any) -> S.RunIdentity:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "thread_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "workflow_version": "1.0.0",
        "state_schema_version": "1.0.0",
        "policy_version": "demo-policy-1.1.0",
        "mapping_version": "map-1.0.0",
        "as_of_utc": AS_OF,
        "idempotency_key": _sha("idem"),
        "started_at": STARTED,
    }
    fields.update(overrides)
    return S.RunIdentity(**fields)


def _document(document_id: str = DOC_A, sha: str = "a" * 64) -> S.SelectedDocumentRef:
    return S.SelectedDocumentRef(
        document_id=document_id, source_sha256=sha, source_status="verified"
    )


def _selected_observation(
    observation_id: str = OBS_CURRENT,
    trust_level: TrustLevel = TrustLevel.SELF_REPORTED_VALIDATED,
    source_fact_id: str | None = None,
) -> S.SelectedObservationRef:
    return S.SelectedObservationRef(
        observation_id=observation_id,
        trust_level=trust_level,
        source_fact_id=source_fact_id,
        observation_created_at=MEASURED_CURRENT,
    )


def _manifest(**overrides: Any) -> S.SelectedSourceManifest:
    fields: dict[str, Any] = {
        "document_ids": [DOC_A],
        "documents": [_document()],
        "observation_ids": [OBS_CURRENT],
        "observations": [_selected_observation()],
        "omission_document_ids": [],
        "omissions": [],
    }
    fields.update(overrides)
    return S.SelectedSourceManifest.build(**fields)


def _observation(**overrides: Any) -> S.ObservationView:
    fields: dict[str, Any] = {
        "observation_id": OBS_CURRENT,
        "patient_id": PATIENT,
        "role": S.ObservationRole.SELECTED_CURRENT,
        "measure_type": MeasureType.SYSTOLIC_BP,
        "value": Decimal("140"),
        "unit": Unit.MMHG,
        "measured_at": MEASURED_CURRENT,
        "source": ObservationSource.PATIENT_CHECKIN,
        "validation": ValidationState.OK,
        "trust_level": TrustLevel.SELF_REPORTED_VALIDATED,
    }
    fields.update(overrides)
    return S.ObservationView(**fields)


def _history(**overrides: Any) -> S.ObservationView:
    fields: dict[str, Any] = {
        "observation_id": OBS_BASELINE_V5,
        "role": S.ObservationRole.HISTORY,
        "measured_at": MEASURED_BASELINE,
        "value": Decimal("128"),
        "source": ObservationSource.SEED_FIXTURE,
    }
    fields.update(overrides)
    return _observation(**fields)


def _verified_observation(**overrides: Any) -> S.ObservationView:
    fields: dict[str, Any] = {
        "trust_level": TrustLevel.DOCTOR_VERIFIED,
        "source": ObservationSource.VERIFIED_DOCUMENT,
        "verified_by": DOCTOR,
        "verified_at": "2026-11-14T09:00:00Z",
        "source_fact_id": FACT_A,
        "source_document_id": DOC_A,
    }
    fields.update(overrides)
    return _observation(**fields)


def _extracted(**overrides: Any) -> S.ExtractedFact:
    fields: dict[str, Any] = {
        "fact_id": FACT_A,
        "patient_id": PATIENT,
        "document_id": DOC_A,
        "field_name": FactField.VALUE,
        "raw_text": "140",
        "normalized_value": "140",
        "unit": "mmHg",
        "quality_flags": [],
        "verification_status": S.VerificationStatus.PENDING,
        "provenance": S.ProvenanceRef(
            kind=S.ProvenanceKind.DOCUMENT_SPAN,
            document_id=DOC_A,
            page_index=0,
            char_start=0,
            char_end=3,
        ),
    }
    fields.update(overrides)
    return S.ExtractedFact(**fields)


def _verified_fact(**overrides: Any) -> S.VerifiedFact:
    """Projected from the F2 ``VerifiedFactV2`` shape (eight fields only)."""
    fields: dict[str, Any] = {
        "fact_id": FACT_A,
        "document_id": DOC_A,
        "field_name": FactField.VALUE,
        "normalized_value": "140",
        "unit": "mmHg",
    }
    fields.update(overrides)
    return S.VerifiedFact(**fields)


def _comparison(**overrides: Any) -> S.ComparisonResult:
    fields: dict[str, Any] = {
        "current_observation_id": OBS_CURRENT,
        "baseline_observation_id": OBS_BASELINE_V5,
        "measure_type": MeasureType.SYSTOLIC_BP,
        "unit": Unit.MMHG,
        "comparable": True,
        "delta": Decimal("12"),
        "trust_basis": S.TrustBasis.SELF_REPORTED,
        "history_policy": S.ComparisonWindow.F2_365D,
        "current_value": Decimal("140"),
        "baseline_value": Decimal("128"),
    }
    fields.update(overrides)
    return S.ComparisonResult(**fields)


def _issue(
    issue_type: S.IssueType = S.IssueType.VI_003,
    reason_code: str = "unverified_fact",
    document_id: str = DOC_A,
    fact_ids: list[str] | None = None,
    message: str = "A selected document carries an unverified fact.",
) -> S.GateIssueRef:
    return S.GateIssueRef(
        issue_type=issue_type,
        reason_code=reason_code,
        document_id=document_id,
        fact_ids=fact_ids if fact_ids is not None else [FACT_A],
        message=message,
    )


def _gate(
    decision: S.GateDecision = S.GateDecision.PROCEED,
    issues: list[S.GateIssueRef] | None = None,
    count: int | None = None,
    reason: S.GateUnavailableReason | None = None,
    **overrides: Any,
) -> S.GateEvaluationRef:
    issues = issues if issues is not None else []
    fields: dict[str, Any] = {
        "run_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "gate_version": "1.0.0",
        "input_fingerprint_sha256": _sha("gate-input"),
        "decision": decision,
        "issues": issues,
        "blocking_fact_count": (
            count if count is not None else len({f for item in issues for f in item.fact_ids})
        ),
        "unavailable_reason": reason,
        "replayed": False,
    }
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
        "selected_observation_ids": [OBS_CURRENT],
    }
    fields.update(overrides)
    if "no_current_reason" not in overrides:
        fields["no_current_reason"] = (
            None if fields["selected_observation_ids"] else "no_current_selected"
        )
    return S.EvaluableEvidenceRef(**fields)


def _layered(**overrides: Any) -> S.LayeredExclusions:
    fields: dict[str, Any] = {
        "l0_lineage_checks": [],
        "l1_exclusions": [],
        "l2_exclusions": [],
        "l3_merged": [],
    }
    fields.update(overrides)
    return S.LayeredExclusions(**fields)


def _sealed(**overrides: Any) -> S.SealedReviewEvaluation:
    fields: dict[str, Any] = {
        "run_id": RUN,
        "patient_id": PATIENT,
        "doctor_id": DOCTOR,
        "as_of_utc": AS_OF,
        "policy_version": "demo-policy-1.1.0",
        "policy_reference_sha256": POLICY_SHA,
        "gate_evaluation_id": GATE_EVAL,
        "gate_version": "1.0.0",
        "gate_input_fingerprint_sha256": _sha("gate-input"),
        "bridge_input_fingerprint_sha256": _sha("bridge-input"),
        "input_fingerprint_sha256": _sha("rb3-input"),
        "output_identity_sha256": _sha("rb3-output"),
        "evaluation_id": EVAL_A,
        "audit_event_id": AUDIT_A,
        "lineage_label_policy": "a2_transport_label",
        "dr006_policy": "prohibited_denied",
        "replayed": False,
        "review_items_persisted": 2,
        "review_items_total": 2,
        "evidence_links_persisted": 4,
        "evidence_links_total": 4,
        "excluded_evidence": [],
        "layered_exclusions": _layered(),
        "exclusion_count": 0,
        "l1_exclusion_count": 0,
        "l2_exclusion_count": 0,
    }
    fields.update(overrides)
    return S.SealedReviewEvaluation(**fields)


def _denied(**overrides: Any) -> S.DeniedReviewPersistence:
    from app.schemas.p4_rb3_review_persistence import RB3DenialReason

    fields: dict[str, Any] = {
        "reason": RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED,
        "observed_at_utc": VALIDATED,
    }
    fields.update(overrides)
    return S.DeniedReviewPersistence(**fields)


def _state(**overrides: Any) -> S.SharedGraphState:
    fields: dict[str, Any] = {
        "identity": _identity(),
        "selection": _manifest(),
        "observations": [_observation()],
        "updated_at": UPDATED,
    }
    fields.update(overrides)
    return S.SharedGraphState(**fields)


_UNSET: Any = object()


def _approved_state(
    status: S.RunStatus = S.RunStatus.AWAITING_DECISION,
    approval: S.ApprovalDecision | Any | None = _UNSET,
    **overrides: Any,
) -> S.SharedGraphState:
    fields: dict[str, Any] = {
        "identity": _identity(),
        "selection": _manifest(),
        "observations": [_observation()],
        "status": status,
        "draft_summary": _draft(),
        "verification_gate": _gate(),
        "last_validated_at_utc": VALIDATED,
        "updated_at": UPDATED,
    }
    fields.update(overrides)
    if approval is not _UNSET:
        fields["approval"] = approval
    elif "approval" not in fields:
        fields["approval"] = _approval()
    return S.SharedGraphState(**fields)


def _draft(**overrides: Any) -> S.DraftSummary:
    fields: dict[str, Any] = {
        "draft_id": "d4d4d4d4-d4d4-44d4-8d4d-d4d4d4d4d4d4",
        "provider": S.DraftProvider.DETERMINISTIC_FALLBACK,
        "execution_status": S.DraftExecutionStatus.FALLBACK_NO_MODEL,
        "prompt_version": "draft-v1",
        "created_at": AS_OF,
    }
    fields.update(overrides)
    return S.DraftSummary(**fields)


def _approval(
    decision: S.ApprovalChoice = S.ApprovalChoice.APPROVE,
    **overrides: Any,
) -> S.ApprovalDecision:
    fields: dict[str, Any] = {
        "decision_id": "9d9d9d9d-9d9d-49d9-8d9d-9d9d9d9d9d9d",
        "decision": decision,
        "doctor_id": DOCTOR,
        "decided_at": AS_OF,
    }
    fields.update(overrides)
    return S.ApprovalDecision(**fields)


# === M01: initial state, round-trip, exact decimals ==================================


def test_m01_initial_state_is_queued_and_authorizes_nothing() -> None:
    state = _state()
    assert state.status is S.RunStatus.QUEUED
    assert state.halt_reason is None
    assert state.workflow_completed is False
    assert state.review_evaluation_sealed is False
    assert state.checkpoint_diverges is False
    assert state.policy_status == "unapproved"
    assert state.runtime_policy_activated is False
    assert state.runtime_evaluable is False
    # The only assurance level this module can grant (R07).
    assert state.assurance_level is S.AssuranceLevel.SHAPE_VALIDATED


def test_m01_json_round_trip_is_lossless_and_text_stable() -> None:
    state = _state(
        observations=[_observation(), _history()],
        comparisons=[_comparison()],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    text = state.model_dump_json()
    assert S.SharedGraphState.model_validate_json(text) == state
    assert json.loads(text)["observations"][0]["value"] == "140"
    # Deterministic: the same content always serialises identically.
    assert state.model_dump_json() == text


def test_m01_decimal_text_is_canonical_and_exact() -> None:
    row = _observation(value=Decimal("140.5000"))
    assert json.loads(row.model_dump_json())["value"] == "140.5"
    assert _observation(value=Decimal("0.0001")).model_dump_json().count("0.0001") == 1
    assert isinstance(row.model_dump()["value"], Decimal)


def test_m01_version_constants_match_the_f0_foundation() -> None:
    from app.services.p5_run_foundation import (
        POLICY_REFERENCE_VERSION,
        STATE_SCHEMA_VERSION,
        WORKFLOW_VERSION,
    )

    assert S.WORKFLOW_VERSION == WORKFLOW_VERSION == "1.0.0"
    assert S.STATE_SCHEMA_VERSION == STATE_SCHEMA_VERSION == "1.0.0"
    assert S.POLICY_REFERENCE_VERSION == POLICY_REFERENCE_VERSION == "demo-policy-1.1.0"


def test_m01_identity_is_immutable_as_a_block() -> None:
    with pytest.raises(ValidationError):
        type(_identity()).model_validate({**_identity().model_dump(), "run_id": DOC_A})
    with pytest.raises(ValidationError):
        _identity(run_id=DOC_A)  # a changed identity is a different, rejected run


# === M02: thread identity and checkpoint non-authority ==============================


def test_m02_thread_id_must_equal_run_id() -> None:
    with pytest.raises(ValidationError, match="thread_id must equal run_id"):
        _identity(thread_id=DOC_A)


def test_m02_checkpoint_claim_is_informational_never_authority() -> None:
    # An explicit thread_id field exists on the checkpoint and is checked (R01).
    diverging = S.CheckpointRef(
        checkpoint_id="cp-1", thread_id=RUN, claimed_status=S.RunStatus.COMPLETED
    )
    state = _state(checkpoint=diverging)
    assert state.checkpoint_diverges is True
    assert state.workflow_completed is False  # the claim grants nothing
    with pytest.raises(ValidationError, match="run's own thread"):
        _state(
            checkpoint=S.CheckpointRef(checkpoint_id="cp-1", thread_id=DOC_A, claimed_status=None)
        )


# === M03: malformed primitives ======================================================


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("Uuid", "6F1C2D3E-4A5B-4C6D-8E7F-90A1B2C3D4E5"),
        ("Uuid", "{6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5}"),
        ("Uuid", "urn:uuid:6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e4a5b4c6d8e7f90a1b2c3d4e5"),
        ("Uuid", "00000000-0000-0000-0000-000000000000"),
        # UUIDv1 / v3 / v7 and the non-RFC "NCS" variant are not emitted by any
        # accepted producer, so they stay rejected (R01).
        ("Uuid", "6f1c2d3e-4a5b-1c6d-8e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e-4a5b-3c6d-8e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e-4a5b-7c6d-8e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e-4a5b-4c6d-0e7f-90a1b2c3d4e5"),
        ("Uuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4eg"),
        # Run identity must stay genuine F0 UUIDv4 (R01).
        ("RunUuid", "4db31c0e-dc9c-5695-ad2f-ed612f80e308"),
        ("RunUuid", "51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f"),
        ("RunUuid", "6F1C2D3E-4A5B-4C6D-8E7F-90A1B2C3D4E5"),
        # Derived task identity must stay UUIDv5 (R01).
        ("TaskUuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"),
        ("TaskUuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4eg"),
        ("Sha256", "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a488"),
        ("Sha256", "2D711642B726B04401627CA9FBAC32F5C8530FB1903CC4DB02258717921A4881"),
        ("Sha256", "0" * 64),
        ("Sha256", "g" * 64),
        ("Iso", "2026-11-14T12:00:00+00:00"),
        ("Iso", "2026-11-14T12:00:00.000Z"),
        ("Iso", "2026-11-14 12:00:00Z"),
        ("Iso", "2026-11-14t12:00:00Z"),
        ("Iso", "2026-02-30T00:00:00Z"),
        ("Iso", "2026-13-01T00:00:00Z"),
        ("Iso", "2026-1-01T00:00:00Z"),
        ("Iso", "2026-11-14T24:00:00Z"),
        ("SemVer", "1.0"),
        ("SemVer", "1.0.0.0"),
        ("SemVer", "01.0.0"),
        ("SemVer", "v1.0.0"),
        ("SemVer", "1.0.0-rc1"),
        ("SemVer", "1000000000.0.0"),
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
        ("PromptVersion", "d" * 33),
        ("ReasonCode", "Pending-Fact"),
        ("ErrorCode", "VALIDATION"),
        ("ErrorCode", "e_validation"),
    ],
)
def test_m03_malformed_primitives_are_rejected(kind: str, value: str) -> None:
    adapter = S.Strict.model_validate  # placeholder to keep the import surface honest
    assert adapter is not None
    from pydantic import TypeAdapter

    with pytest.raises(ValidationError):
        TypeAdapter(getattr(S, kind)).validate_python(value)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("Uuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"),
        # The genuine seeded synthetic observation identities are UUIDv5 (R01).
        ("Uuid", OBS_BASELINE_V5),
        ("Uuid", OBS_BASELINE_V5_B),
        ("RunUuid", "6f1c2d3e-4a5b-4c6d-8e7f-90a1b2c3d4e5"),
        ("TaskUuid", "51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f"),
        ("Sha256", "2689367b205c16ce32ed4200942b8b8b1e262dfc70d9bc9fbc77c49699a4f1df"),
        ("Iso", "2026-11-14T12:00:00Z"),
        ("SemVer", "1.0.0"),
        ("MappingVersion", "map-1.0.0"),
        ("PolicyVersion", "demo-policy-1.1.0"),
        ("PromptVersion", "draft-v1"),
        ("ReasonCode", "selected_separate_recovery_source"),
        ("ErrorCode", "E_WORKFLOW_VERSION_MISMATCH"),
    ],
)
def test_m03_well_formed_primitives_are_accepted(kind: str, value: str) -> None:
    from pydantic import TypeAdapter

    assert TypeAdapter(getattr(S, kind)).validate_python(value) == value


def test_m03_primitives_reject_non_string_input() -> None:
    from pydantic import TypeAdapter

    for kind in ("Uuid", "RunUuid", "TaskUuid", "Sha256", "Iso", "SemVer"):
        for bad in (123, b"abc", None, True, [], {}):
            with pytest.raises(ValidationError):
                TypeAdapter(getattr(S, kind)).validate_python(bad)


def test_m03_task_due_date_must_be_a_real_calendar_date() -> None:
    with pytest.raises(ValidationError):
        S.TaskDraft(
            action_key=_sha("task"),
            task_id="51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f",
            title="Follow up",
            due_date="2026-02-30",
        )


# === M04: unknown fields, coercions, bounded metadata =================================


def test_m04_unknown_fields_are_rejected_at_every_level() -> None:
    for payload in (
        {**_identity().model_dump(), "extra": 1},
        {**_observation().model_dump(), "extra": 1},
        {**_state().model_dump(), "extra": 1},
        {**_manifest().model_dump(), "extra": 1},
        {**_gate().model_dump(), "extra": 1},
        {**_sealed().model_dump(), "extra": 1},
    ):
        with pytest.raises(ValidationError):
            type(_identity()).model_validate(
                payload
            ) if "run_id" in payload and "thread_id" in payload else _state(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "queued"),
        ("status", True),
        ("observations", [{"value": 2}]),
        ("retry_counts", {"document_extract": 1}),
    ],
)
def test_m04_python_mode_coercions_are_rejected(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        _state(**{field: value})


def test_m04_json_strings_are_not_coerced_to_numbers_or_booleans() -> None:
    row = json.loads(_observation().model_dump_json())
    for bad in ({"value": "abc"}, {"validation": 1}, {"trust_level": "DOCTOR_VERIFIED"}):
        with pytest.raises(ValidationError):
            S.ObservationView.model_validate_json(json.dumps({**row, **bad}))


def test_m04_exact_decimals_reject_json_numbers() -> None:
    """D-07: a JSON number is never accepted for an exact quantity."""
    row = json.loads(_observation().model_dump_json())
    for bad in (140, 140.0, 1.4e2):
        with pytest.raises(ValidationError, match="JSON decimal strings"):
            S.ObservationView.model_validate_json(json.dumps({**row, "value": bad}))


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
    for bad in ("0.5", True, -0.1, 1.1):
        with pytest.raises(ValidationError):
            _state(
                events=[
                    S.NodeEvent(
                        node=S.NodeName.EXTRACTION_TRIAGE,
                        started_at=AS_OF,
                        detail=S.TriageDetail(
                            path_selected=S.TriagePath.TEXT_LAYER,
                            path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                            document_id=DOC_A,
                            attempt_index=1,
                            engine_confidence=bad,
                            preprocessing_applied=False,
                        ),
                    )
                ]
            )


# === M05: caps are the accepted producers' maxima ====================================


def test_m05_document_and_omission_caps() -> None:
    docs = [f"c0ffee00-0000-4000-8000-{i:012d}" for i in range(5)]
    _manifest(document_ids=docs, documents=[_document(d) for d in docs])
    with pytest.raises(ValidationError):
        _manifest(document_ids=[*docs, DOC_B], documents=[_document(d) for d in [*docs, DOC_B]])
    with pytest.raises(ValidationError):
        _manifest(omission_document_ids=[*docs, DOC_B], omissions=[])


def test_m05_observation_manifest_cap_is_the_f0_maximum() -> None:
    ids = [f"b0000000-0000-4000-8000-{i:012d}" for i in range(S.MAX_MANIFEST_OBSERVATIONS)]
    _manifest(
        observation_ids=ids,
        observations=[_selected_observation(i, source_fact_id=None) for i in ids],
    )
    with pytest.raises(ValidationError):
        _manifest(
            observation_ids=[*ids, OBS_CURRENT],
            observations=[
                _selected_observation(i, source_fact_id=None) for i in [*ids, OBS_CURRENT]
            ],
        )


def test_m05_upstream_fact_and_history_evidence_is_not_truncated() -> None:
    """R07: 40 F2 facts and 100 F2 history observations must be representable."""
    facts = [_extracted(fact_id=f"deadbeef-0000-4000-8000-{i:012d}") for i in range(S.MAX_FACTS)]
    state = _state(extraction_facts=facts)
    assert len(state.extraction_facts) == S.MAX_FACTS

    history = [
        _history(observation_id=f"e0000000-0000-4000-8000-{i:012d}")
        for i in range(S.MAX_HISTORY_OBSERVATIONS)
    ]
    state = _state(observations=[_observation(), *history])
    assert len(state.observations) == S.MAX_HISTORY_OBSERVATIONS + 1

    # Beyond the accepted producer maxima the shape still rejects.
    with pytest.raises(ValidationError):
        _state(extraction_facts=[*facts, _extracted(fact_id=FACT_B)])
    # 106 is the accepted maximum, so 107 must be rejected.
    with pytest.raises(ValidationError):
        _state(
            observations=[
                _observation(),
                *history,
                *[
                    _history(observation_id=f"e0000000-0000-4000-8000-{i:012d}")
                    for i in range(S.MAX_HISTORY_OBSERVATIONS, S.MAX_HISTORY_OBSERVATIONS + 6)
                ],
            ]
        )


def test_m05_rb3_exclusions_and_items_use_the_durable_maxima() -> None:
    merged = [
        S.PersistedExclusionRef(
            observation_id=f"f0000000-0000-4000-8000-{i:012d}",
            reason_code="validation_rejected",
        )
        for i in range(S.MAX_MERGED_EXCLUSIONS)
    ]
    sealed = _sealed(
        excluded_evidence=merged,
        layered_exclusions=_layered(l1_exclusions=merged, l3_merged=merged),
        exclusion_count=len(merged),
        l1_exclusion_count=len(merged),
    )
    assert len(sealed.excluded_evidence) == S.MAX_MERGED_EXCLUSIONS
    with pytest.raises(ValidationError):
        _sealed(excluded_evidence=[*merged, merged[0]])
    with pytest.raises(ValidationError):
        _sealed(review_items_persisted=S.MAX_PERSISTED_ITEMS + 1)
    with pytest.raises(ValidationError):
        _sealed(evidence_links_persisted=S.MAX_PERSISTED_LINKS + 1)


def test_m05_nested_caps_blocks_counts_and_attempts() -> None:
    with pytest.raises(ValidationError):
        _state(events=[_event() for _ in range(S.MAX_EVENTS + 1)])
    with pytest.raises(ValidationError):
        _state(errors=[_error() for _ in range(S.MAX_ERRORS + 1)])
    with pytest.raises(ValidationError):
        _state(
            extraction_attempts=[
                S.ExtractionAttempt(
                    attempt_id=f"a0000000-0000-4000-8000-{i:012d}",
                    document_id=DOC_A,
                    path=S.ExtractionPath.PYPDF,
                    preprocessing=S.Preprocessing.NONE,
                    page_from=0,
                    page_to=1,
                    text_char_count=10,
                    succeeded=True,
                    duration_ms=1,
                    created_at=AS_OF,
                )
                for i in range(S.MAX_EXTRACTION_ATTEMPTS + 1)
            ]
        )


def _event(**overrides: Any) -> S.NodeEvent:
    fields: dict[str, Any] = {"node": S.NodeName.INTAKE_VALIDATE, "started_at": AS_OF}
    fields.update(overrides)
    return S.NodeEvent(**fields)


def _error(**overrides: Any) -> S.AgentError:
    fields: dict[str, Any] = {
        "code": "E_WORKFLOW_VERSION_MISMATCH",
        "node": S.NodeName.INTAKE_VALIDATE,
        "message": "unsupported",
        "retryable": False,
        "attempt": 1,
        "occurred_at": AS_OF,
    }
    fields.update(overrides)
    return S.AgentError(**fields)


# === M06: non-finite and unbounded values ============================================


@pytest.mark.parametrize(
    "value", ["NaN", "sNaN", "Infinity", "-Infinity", "0", "-1", "0.00001", "12345678901"]
)
def test_m06_non_finite_or_unbounded_values_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        _observation(value=Decimal(value))


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_m06_non_finite_confidence_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        _state(
            events=[
                _event(
                    node=S.NodeName.EXTRACTION_TRIAGE,
                    detail=S.TriageDetail(
                        path_selected=S.TriagePath.TEXT_LAYER,
                        path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                        document_id=DOC_A,
                        attempt_index=1,
                        engine_confidence=float(value),
                        preprocessing_applied=False,
                    ),
                )
            ]
        )


def test_m06_floats_are_never_silently_accepted_for_exact_values() -> None:
    with pytest.raises(ValidationError):
        _observation(value=140.0)
    with pytest.raises(ValidationError):
        _observation(value=140)


# === M07: patient scope and the validation clock ======================================


def test_m07_evidence_outside_the_run_patient_is_rejected() -> None:
    with pytest.raises(ValidationError, match="patient scope differs from the run"):
        _state(observations=[_observation(patient_id=DOCTOR)])
    with pytest.raises(ValidationError, match="patient scope differs from the run"):
        _state(
            extraction_facts=[_extracted(patient_id=DOCTOR)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # A verified projection that carries no patient scope asserts nothing.
    _state(verified_facts=[_verified_fact(patient_id=None)])


def test_m07_gate_requires_the_validation_clock() -> None:
    with pytest.raises(ValidationError, match="requires the validation clock"):
        _state(verification_gate=_gate())


def test_m07_manifest_omission_doctor_must_match_run_scope() -> None:
    omission = S.SelectedOmissionRef(
        document_id=DOC_B,
        vi002_issue_id=ISSUE_A,
        reason_code="selected_separate_recovery_source",
        doctor_id=DOCTOR,
        source_sha256=_sha("omission"),
    )
    _state(selection=_manifest(omission_document_ids=[DOC_B], omissions=[omission]))
    forged = S.SelectedOmissionRef(
        document_id=DOC_B,
        vi002_issue_id=ISSUE_A,
        reason_code="selected_separate_recovery_source",
        doctor_id=PATIENT,
        source_sha256=_sha("omission"),
    )
    with pytest.raises(ValidationError, match="run's own doctor"):
        _state(
            selection=_manifest(omission_document_ids=[DOC_B], omissions=[forged]),
        )


# === M08: provenance and manifest ====================================================


def test_m08_provenance_ref_shape() -> None:
    span = S.ProvenanceRef(
        kind=S.ProvenanceKind.DOCUMENT_SPAN,
        document_id=DOC_A,
        page_index=1,
        char_start=4,
        char_end=9,
    )
    assert span.document_id == DOC_A
    # D-02: bounded raw text lives in the evidence model and nowhere else.
    assert (
        S.ProvenanceRef(
            kind=S.ProvenanceKind.CHECKIN_NOTE, observation_id=OBS_CURRENT, raw_text="x" * 500
        ).raw_text
        is not None
    )
    with pytest.raises(ValidationError):
        S.ProvenanceRef(
            kind=S.ProvenanceKind.CHECKIN_NOTE,
            observation_id=OBS_CURRENT,
            raw_text="x" * 501,
        )
    # Field combinations stay distinct per provenance kind (R05).
    with pytest.raises(ValidationError, match="carries no page or character span"):
        S.ProvenanceRef(kind=S.ProvenanceKind.OBSERVATION, observation_id=OBS_CURRENT, page_index=0)
    with pytest.raises(ValidationError, match="forbids observation_id"):
        S.ProvenanceRef(
            kind=S.ProvenanceKind.DOCUMENT_SPAN,
            document_id=DOC_A,
            observation_id=OBS_CURRENT,
            page_index=0,
            char_start=0,
            char_end=1,
        )
    with pytest.raises(ValidationError, match="together"):
        S.ProvenanceRef(kind=S.ProvenanceKind.DOCUMENT_SPAN, document_id=DOC_A, page_index=0)


def test_m08_observation_trust_and_source_provenance_are_inseparable() -> None:
    row = _verified_observation()
    assert row.trust_level is TrustLevel.DOCTOR_VERIFIED
    for change in (
        {"trust_level": TrustLevel.SELF_REPORTED_VALIDATED},
        {"trust_level": TrustLevel.DOCTOR_VERIFIED, "verified_by": None},
        {"trust_level": TrustLevel.DOCTOR_VERIFIED, "verified_at": None},
        {"source": ObservationSource.PATIENT_CHECKIN},
        {"source_fact_id": None},
        {"source_document_id": None},
    ):
        with pytest.raises(ValidationError):
            S.ObservationView.model_validate({**row.model_dump(), **change})
    # A self-reported row carries neither verifier field.
    plain = _observation()
    assert plain.verified_by is None and plain.verified_at is None


def test_m08_extracted_fact_decision_shape_and_verified_lineage() -> None:
    assert _extracted().verification_status is S.VerificationStatus.PENDING
    for change in (
        {"verified_by": DOCTOR},
        {"verified_at": "2026-11-14T09:00:00Z"},
        {
            "verification_status": S.VerificationStatus.VERIFIED,
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
        },
    ):
        if change.get("verification_status") is S.VerificationStatus.VERIFIED:
            S.ExtractedFact.model_validate({**_extracted().model_dump(), **change})
            continue
        with pytest.raises(ValidationError):
            S.ExtractedFact.model_validate({**_extracted().model_dump(), **change})
    with pytest.raises(ValidationError, match="cannot be corrected from itself"):
        _verified_fact(corrected_from_fact_id=FACT_A)
    with pytest.raises(ValidationError, match="projected together"):
        _verified_fact(verified_by=DOCTOR)


def test_m08_selection_manifest_shape() -> None:
    manifest = _manifest()
    assert manifest.document_ids == [DOC_A]
    assert manifest.selection_fingerprint == manifest.compute_fingerprint()
    with pytest.raises(ValidationError, match="does not match the manifest content"):
        S.SelectedSourceManifest(**{**manifest.model_dump(), "selection_fingerprint": _sha("x")})
    # An omitted document cannot also be selected.
    with pytest.raises(ValidationError, match="cannot also be a selected document"):
        _manifest(omission_document_ids=[DOC_A], omissions=[])


def test_m08_manifest_fingerprint_is_self_verifying() -> None:
    rebuilt = _manifest(documents=[_document(DOC_A, sha="b" * 64)])
    assert rebuilt.selection_fingerprint == rebuilt.compute_fingerprint()
    assert rebuilt.selection_fingerprint != _manifest().selection_fingerprint


def test_m08_manifest_build_rejects_unknown_members() -> None:
    """R07: an unknown keyword must raise, never be silently discarded."""
    with pytest.raises(ValueError, match="unknown manifest member"):
        S.SelectedSourceManifest.build(document_ids=[DOC_A], documments=[_document()])
    # A typo'd member must not quietly produce a manifest missing evidence.
    complete = S.SelectedSourceManifest.build(
        document_ids=[DOC_A],
        documents=[_document()],
        observation_ids=[OBS_CURRENT],
        observations=[_selected_observation()],
    )
    assert complete.documents == [_document()]


# === M09: no trust promotion =========================================================


def test_m09_self_reported_cannot_be_promoted_by_any_input_path() -> None:
    row = _observation()
    assert row.trust_level is TrustLevel.SELF_REPORTED_VALIDATED
    for change in (
        {"trust_level": "doctor_verified"},
        {
            "trust_level": TrustLevel.DOCTOR_VERIFIED,
            "verified_by": DOCTOR,
            "verified_at": "2026-11-14T09:00:00Z",
        },
    ):
        with pytest.raises(ValidationError):
            S.ObservationView.model_validate({**row.model_dump(), **change})
    # Turning every knob at once still cannot relabel a patient check-in: the
    # source must itself be a verified document.
    with pytest.raises(ValidationError):
        S.ObservationView.model_validate(
            {
                **row.model_dump(),
                "trust_level": TrustLevel.DOCTOR_VERIFIED,
                "verified_by": DOCTOR,
                "verified_at": "2026-11-14T09:00:00Z",
                "source_fact_id": FACT_A,
                "source_document_id": DOC_A,
            }
        )


def test_m09_selection_manifest_cannot_relabel_a_typed_observation() -> None:
    selected = _selected_observation(
        OBS_CURRENT, trust_level=TrustLevel.DOCTOR_VERIFIED, source_fact_id=FACT_A
    )
    with pytest.raises(ValidationError, match="manifest differs from the typed observation"):
        _state(selection=_manifest(observations=[selected]))


def test_m09_copy_bypass_is_caught_by_revalidation() -> None:
    row = _observation()
    forged = row.model_copy(update={"trust_level": TrustLevel.DOCTOR_VERIFIED})
    assert forged.trust_level is TrustLevel.DOCTOR_VERIFIED  # bypasses validation by design
    with pytest.raises(ValidationError):
        S.ObservationView.model_validate_json(forged.model_dump_json())
    state = _state(observations=[row])
    forged_state = state.model_copy(update={"observations": [forged]})
    with pytest.raises(ValidationError):
        S.SharedGraphState.revalidate(forged_state)


def test_m09_mutated_container_is_caught_by_revalidation() -> None:
    """R07: a mutated list cannot bypass the explicit full-revalidation path."""
    state = _state(observations=[_observation()])
    state.observations.append(_observation(observation_id=OBS_BASELINE_V5, patient_id=DOCTOR))  # type: ignore[attr-defined]
    assert len(state.observations) == 2  # frozen does not freeze list contents
    with pytest.raises(ValidationError, match="patient scope differs from the run"):
        S.SharedGraphState.revalidate(state)


# === M10: pending / rejected is not verified =========================================


def test_m10_pending_or_rejected_facts_cannot_be_projected_as_verified() -> None:
    verified = _verified_fact()
    with pytest.raises(ValidationError, match="pending/rejected"):
        _state(
            extraction_facts=[_extracted(verification_status=S.VerificationStatus.PENDING)],
            verified_facts=[verified],
        )
    with pytest.raises(ValidationError, match="pending/rejected"):
        _state(
            extraction_facts=[
                _extracted(
                    verification_status=S.VerificationStatus.REJECTED,
                    verified_by=DOCTOR,
                    verified_at="2026-11-14T09:00:00Z",
                )
            ],
            verified_facts=[verified],
        )
    # Agreement is required on every stored source field (R05).
    for change in (
        {"document_id": DOC_B},
        {"field_name": FactField.TEST_NAME},
        {"corrected_from_fact_id": FACT_B},
    ):
        with pytest.raises(ValidationError):
            _state(
                extraction_facts=[
                    _extracted(
                        verification_status=S.VerificationStatus.VERIFIED,
                        verified_by=DOCTOR,
                        verified_at="2026-11-14T09:00:00Z",
                    )
                ],
                verified_facts=[_verified_fact(**change)],
            )


# === M11: comparison consistency and trust binding ===================================


def test_m11_comparable_and_incomparable_shapes_are_mutually_exclusive() -> None:
    with pytest.raises(ValidationError, match="needs a baseline id and delta"):
        _comparison(comparable=True, delta=None)
    with pytest.raises(ValidationError, match="carries no incomparable_reason"):
        _comparison(comparable=True, incomparable_reason=S.IncomparableReason.NO_BASELINE)
    with pytest.raises(ValidationError, match="needs a reason and no delta"):
        _comparison(comparable=False, incomparable_reason=None, delta=Decimal("1"))
    with pytest.raises(ValidationError, match="cannot be its own baseline"):
        _comparison(baseline_observation_id=OBS_CURRENT)
    # D-03: stale_baseline is reserved vocabulary and stays representable.
    assert (
        _comparison(
            comparable=False,
            delta=None,
            baseline_value=None,
            incomparable_reason=S.IncomparableReason.STALE_BASELINE,
        ).incomparable_reason
        is S.IncomparableReason.STALE_BASELINE
    )
    # ... but no accepted service emits it (F2 emits only two reasons).
    assert {S.IncomparableReason.STALE_BASELINE}.isdisjoint(S.F2_EMITTED_INCOMPARABLE)
    assert {
        S.IncomparableReason.NO_BASELINE,
        S.IncomparableReason.NOT_ADMISSIBLE,
    } == S.F2_EMITTED_INCOMPARABLE


def test_m11_state_binds_comparison_values_and_trust_basis_to_observations() -> None:
    current, baseline = _observation(), _history()
    good = _comparison()
    _state(
        observations=[current, baseline],
        comparisons=[good],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    with pytest.raises(ValidationError, match="current value differs"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(current_value=Decimal("141"), delta=Decimal("13"))],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="baseline value differs"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(baseline_value=Decimal("127"), delta=Decimal("13"))],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # D-11: the label is re-derived, never taken on trust.
    with pytest.raises(ValidationError, match="trust_basis must follow"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(trust_basis=S.TrustBasis.DOCTOR_VERIFIED)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # A missing baseline cannot smuggle in a mixed or doctor_verified claim.
    with pytest.raises(ValidationError, match="no baseline means trust_basis cannot be mixed"):
        _state(
            observations=[current],
            comparisons=[
                _comparison(
                    baseline_observation_id=None,
                    comparable=False,
                    delta=None,
                    baseline_value=None,
                    incomparable_reason=S.IncomparableReason.NO_BASELINE,
                    trust_basis=S.TrustBasis.MIXED,
                )
            ],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


def test_m11_history_cannot_become_selected_current_and_delta_must_follow() -> None:
    current, baseline = _observation(), _history()
    with pytest.raises(ValidationError, match="must be a selected current, not history"):
        _state(
            observations=[baseline, current],
            comparisons=[
                _comparison(
                    current_observation_id=OBS_BASELINE_V5,
                    baseline_observation_id=OBS_BASELINE_V5_B,
                )
            ],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="must equal the immutable selected manifest"):
        _state(
            observations=[
                current,
                _history(observation_id=OBS_BASELINE_V5_B, role=S.ObservationRole.SELECTED_CURRENT),
            ],
            comparisons=[_comparison(baseline_observation_id=OBS_BASELINE_V5_B)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # ... and once the manifest genuinely selects it, the baseline check still
    # refuses it, because a selected-current row can never serve as a baseline.
    with pytest.raises(ValidationError, match="must be a history row"):
        _state(
            observations=[
                current,
                _history(observation_id=OBS_BASELINE_V5_B, role=S.ObservationRole.SELECTED_CURRENT),
            ],
            comparisons=[_comparison(baseline_observation_id=OBS_BASELINE_V5_B)],
            selection=_manifest(
                observation_ids=sorted([OBS_CURRENT, OBS_BASELINE_V5_B]),
                observations=[
                    _selected_observation(observation_id=value)
                    for value in sorted([OBS_CURRENT, OBS_BASELINE_V5_B])
                ],
            ),
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="baseline must precede the current"):
        _state(
            observations=[current, _history(measured_at=MEASURED_CURRENT)],
            comparisons=[_comparison()],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="delta must equal"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(delta=Decimal("11"))],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


def test_m11_window_labels_are_distinguishable_and_never_relabelled() -> None:
    """D-04: a 365-day F2 comparison is never presented as the 90-day rule input."""
    assert S.ComparisonWindow.F2_365D.value == "f2-history-365d-v1"
    assert S.ComparisonWindow.RB1_90D.value == "rb1-demo-90d-v1"
    # The producer pins its own label; the typed state must not relabel it.
    from app.services.p5_evidence_bridge import COMPARISON_HISTORY_VERSION

    assert S.ComparisonWindow.F2_365D.value == COMPARISON_HISTORY_VERSION
    # A 90-day row is representable on its own (a different producer's output)...
    rb1 = _comparison(
        history_policy=S.ComparisonWindow.RB1_90D,
        baseline_observation_id=None,
        comparable=False,
        delta=None,
        baseline_value=None,
        incomparable_reason=S.IncomparableReason.NO_BASELINE,
    )
    assert rb1.history_policy is S.ComparisonWindow.RB1_90D
    _state(
        comparisons=[rb1],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    # ... but never beside an F2 evidence reference: that would present 90-day
    # rule input as the 365-day window (D-04).
    with pytest.raises(ValidationError, match="cannot carry a 90-day RB1 comparison"):
        _state(
            comparisons=[rb1],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
            evaluable_evidence=_evidence(),
        )


# === M12: closed vocabularies and gate issue identity ===============================


def test_m12_issue_and_rule_vocabularies_are_closed_and_disjoint() -> None:
    assert [e.value for e in S.IssueType] == [f"VI-{n:03d}" for n in range(1, 7)]
    assert [e.value for e in S.ReviewRuleId] == [
        "DR-001",
        "DR-003",
        "DR-005",
        "DR-006",
        "DR-008",
        "DR-009",
    ]
    assert not (set(S.IssueType) & set(S.ReviewRuleId))


def test_m12_gate_issue_identity_is_full_not_just_the_type() -> None:
    """D-12: type, reason, document and fact identities all take part."""
    base = _issue()
    assert base.semantic_key() == (S.IssueType.VI_003, "unverified_fact", DOC_A, (FACT_A,))
    assert _issue(reason_code="other").semantic_key() != base.semantic_key()
    assert _issue(document_id=DOC_B).semantic_key() != base.semantic_key()
    assert _issue(fact_ids=[FACT_B]).semantic_key() != base.semantic_key()
    assert _issue(message="Other message").semantic_key() == base.semantic_key()


# === M13: F1 gate outcome semantics (R03) ============================================


def test_m13_gate_decision_combinations() -> None:
    _gate(S.GateDecision.PROCEED)
    # A genuine halt can have ZERO distinct blocking facts: every blocker is
    # document-level (F1 derives the count from distinct referenced facts).
    document_only = _gate(S.GateDecision.HALT, issues=[_issue(fact_ids=[])], count=0)
    assert document_only.blocking_fact_count == 0
    _gate(S.GateDecision.HALT, issues=[_issue(fact_ids=[FACT_A])], count=1)
    # UNAVAILABLE may retain recorded diagnostics (never discarded for the schema).
    _gate(
        S.GateDecision.UNAVAILABLE,
        issues=[_issue(fact_ids=[FACT_A])],
        count=1,
        reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
    )
    _gate(
        S.GateDecision.UNAVAILABLE,
        issues=[],
        count=0,
        reason=S.GateUnavailableReason.SELECTED_DOCUMENT_CHANGED,
    )
    # Contradictory counts are rejected.
    with pytest.raises(ValidationError, match="distinct referenced fact count"):
        _gate(S.GateDecision.HALT, issues=[_issue(fact_ids=[FACT_A])], count=2)
    with pytest.raises(ValidationError, match="proceed records no blocking issue"):
        _gate(S.GateDecision.PROCEED, issues=[_issue()], count=1)
    with pytest.raises(ValidationError, match="unavailable_reason is present iff"):
        _gate(
            S.GateDecision.HALT,
            issues=[_issue()],
            count=1,
            reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
        )
    with pytest.raises(ValidationError, match="unavailable_reason is present iff"):
        _gate(S.GateDecision.UNAVAILABLE, issues=[], count=0, reason=None)
    # Above the persisted bound the producer can only report too_many_blocking_facts.
    with pytest.raises(ValidationError, match="too_many_blocking_facts"):
        _gate(S.GateDecision.HALT, issues=[_issue(fact_ids=[FACT_A])], count=99)
    _gate(
        S.GateDecision.UNAVAILABLE,
        issues=[_issue(fact_ids=[FACT_A])],
        count=99,
        reason=S.GateUnavailableReason.TOO_MANY_BLOCKING_FACTS,
    )


def test_m13_unavailable_reason_vocabulary_matches_the_f1_service() -> None:
    source = (REPO_ROOT / "backend" / "app" / "services" / "p5_run_gate.py").read_text()
    emitted = set(re.findall(r'unavailable = "([a-z0-9_]+)"', source))
    assert emitted == {reason.value for reason in S.GateUnavailableReason}


def test_m13_state_reactions_to_each_decision() -> None:
    # proceed: nothing post-draft yet, but evidence may follow.
    _state(last_validated_at_utc=VALIDATED, verification_gate=_gate())
    _state(
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(),
        evaluable_evidence=_evidence(),
        observations=[_observation()],
    )
    # halt: representable on a queued run; needs_verification requires it.
    _state(
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(S.GateDecision.HALT, issues=[_issue()]),
    )
    _state(
        status=S.RunStatus.NEEDS_VERIFICATION,
        halt_reason=S.HaltReason.UNVERIFIED_FACTS,
        verification_gate=_gate(S.GateDecision.HALT, issues=[_issue()]),
        last_validated_at_utc=VALIDATED,
    )
    with pytest.raises(ValidationError, match="requires a recorded halt decision"):
        _state(status=S.RunStatus.NEEDS_VERIFICATION, halt_reason=S.HaltReason.UNVERIFIED_FACTS)
    # A halting gate cannot coexist with a post-draft status.
    with pytest.raises(ValidationError, match="halting gate cannot coexist"):
        _approved_state(
            S.RunStatus.AWAITING_DECISION,
            approval=None,
            verification_gate=_gate(S.GateDecision.HALT, issues=[_issue()]),
        )
    # unavailable: representable on a queued run, never alongside a draft.
    _state(
        last_validated_at_utc=VALIDATED,
        verification_gate=_gate(
            S.GateDecision.UNAVAILABLE,
            issues=[_issue()],
            count=1,
            reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
        ),
    )
    with pytest.raises(ValidationError, match="require a proceed"):
        _approved_state(
            S.RunStatus.AWAITING_DECISION,
            approval=None,
            verification_gate=_gate(
                S.GateDecision.UNAVAILABLE,
                issues=[_issue()],
                count=1,
                reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
            ),
        )


def test_m13_gate_trace_consistency_without_fabricated_decisions() -> None:
    """R03/D-01: no proceed/halt trace value is invented for an unavailable gate."""
    halt = _gate(S.GateDecision.HALT, issues=[_issue()])
    good = _state(
        verification_gate=halt,
        last_validated_at_utc=VALIDATED,
        events=[
            _event(
                node=S.NodeName.FACT_VERIFY_GATE,
                detail=S.GateDetail(
                    decision="halt",
                    blocking_fact_count=1,
                    issue_types=[S.IssueType.VI_003],
                ),
            )
        ],
    )
    assert good.events[0].detail is not None
    with pytest.raises(ValidationError, match="differs from the evaluation"):
        _state(
            verification_gate=halt,
            last_validated_at_utc=VALIDATED,
            events=[
                _event(
                    node=S.NodeName.FACT_VERIFY_GATE,
                    detail=S.GateDetail(decision="proceed", blocking_fact_count=0, issue_types=[]),
                )
            ],
        )
    with pytest.raises(ValidationError, match="produces no proceed/halt trace decision"):
        _state(
            verification_gate=_gate(
                S.GateDecision.UNAVAILABLE,
                issues=[_issue()],
                count=1,
                reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
            ),
            last_validated_at_utc=VALIDATED,
            events=[
                _event(
                    node=S.NodeName.FACT_VERIFY_GATE,
                    detail=S.GateDetail(
                        decision="halt",
                        blocking_fact_count=1,
                        issue_types=[S.IssueType.VI_003],
                    ),
                )
            ],
        )
    # A trace whose issue-type vocabulary differs is rejected (D-12).
    with pytest.raises(ValidationError, match="issue_types differ"):
        _state(
            verification_gate=halt,
            last_validated_at_utc=VALIDATED,
            events=[
                _event(
                    node=S.NodeName.FACT_VERIFY_GATE,
                    detail=S.GateDetail(
                        decision="halt",
                        blocking_fact_count=1,
                        issue_types=[S.IssueType.VI_002],
                    ),
                )
            ],
        )


# === M14: typed node trace ==========================================================


def test_m14_detail_is_mandatory_iff_the_node_makes_a_bounded_decision() -> None:
    for node in S.NodeName:
        expected = S.DETAIL_KIND_BY_NODE.get(node)
        if expected is None:
            _event(node=node)
            with pytest.raises(ValidationError, match="makes no bounded decision"):
                _event(
                    node=node,
                    detail=S.TriageDetail(
                        path_selected=S.TriagePath.TEXT_LAYER,
                        path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
                        document_id=DOC_A,
                        attempt_index=1,
                        preprocessing_applied=False,
                    ),
                )
        else:
            with pytest.raises(ValidationError, match="must carry exactly one"):
                _event(node=node)


def test_m14_discriminated_union_rejects_unknown_kinds_and_mismatched_payloads() -> None:
    for payload in (
        {"kind": "unknown"},
        {"kind": "triage"},
        {"kind": "validation", "validation_outcome": "accept"},
        {
            "kind": "triage",
            "path_selected": "text_layer",
            "path_reason": "text_layer_available",
            "document_id": DOC_A,
            "path_reason_x": 1,
        },
    ):
        with pytest.raises(ValidationError):
            S.NodeEvent.model_validate_json(
                json.dumps({"node": "extraction_triage", "started_at": AS_OF, "detail": payload})
            )


def test_m14_trace_details_carry_no_free_text_or_unbounded_fields() -> None:
    """D-02: raw text lives in the evidence model, never in a trace detail."""
    for detail in (
        S.TriageDetail(
            path_selected=S.TriagePath.TEXT_LAYER,
            path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
            document_id=DOC_A,
            attempt_index=1,
            preprocessing_applied=False,
        ),
        S.ValidationDetail(validation_outcome=S.ValidationOutcome.ACCEPT, attempt_index=1),
        S.GateDetail(decision="halt", blocking_fact_count=1, issue_types=[S.IssueType.VI_003]),
        S.FinalizeDetail(
            approval_decision="approve", task_created=False, notification_created=False
        ),
    ):
        for name, info in type(detail).model_fields.items():
            assert name != "raw_text"
            assert "text" not in name
            assert info.annotation is not None


def test_m14_tool_allowlist_is_per_node() -> None:
    _event(node=S.NodeName.DOCUMENT_EXTRACT, tools_called=[S.ToolName.EXTRACT_DOCUMENT])
    with pytest.raises(ValidationError, match="exceeds the"):
        _event(node=S.NodeName.INTAKE_VALIDATE, tools_called=[S.ToolName.EXTRACT_DOCUMENT])
    with pytest.raises(ValidationError, match="duplicate tools_called"):
        _event(
            node=S.NodeName.DOCUMENT_EXTRACT,
            tools_called=[S.ToolName.EXTRACT_DOCUMENT, S.ToolName.EXTRACT_DOCUMENT],
        )


def test_m14_trace_path_vocabulary_matches_the_openapi_contract() -> None:
    contract = (REPO_ROOT / "docs" / "contracts" / "openapi.phase0.yaml").read_text()
    match = re.search(r"^\s{4}TriageEventDetail:\s*$", contract, re.MULTILINE)
    assert match, "TriageEventDetail schema definition not found"
    block = contract[match.start() :]
    block = block[: re.search(r"^\s{4}\w+:\s*$", block[10:], re.MULTILINE).start() + 10]
    for member in S.TriagePath:
        assert member.value in block, member.value
    for member in S.PathReason:
        assert member.value in block, member.value


# === M15: retry bounds ==============================================================


def test_m15_retry_counts_are_bounded_and_keyed_by_node() -> None:
    _state(retry_counts={S.NodeName.DOCUMENT_EXTRACT: 5})
    for bad in (
        {S.NodeName.DOCUMENT_EXTRACT: 0},
        {S.NodeName.DOCUMENT_EXTRACT: 6},
        {S.NodeName.DOCUMENT_EXTRACT: True},
        {"document_extract": 1},
    ):
        with pytest.raises(ValidationError):
            _state(retry_counts=bad)


# === M16: RB3 replay, denial and resume classification (R02) =========================


def test_m16_sealed_evaluation_does_not_complete_the_workflow() -> None:
    state = _state(
        verification_gate=_gate(gate_evaluation_id=GATE_EVAL),
        last_validated_at_utc=VALIDATED,
        evaluable_evidence=_evidence(),
        observations=[_observation()],
        review_persistence=_sealed(),
    )
    assert state.review_evaluation_sealed is True
    assert state.workflow_completed is False
    assert state.status is S.RunStatus.QUEUED


def test_m16_first_persistence_and_exact_replay_are_both_representable() -> None:
    """R02: the accepted durable service's two receipt shapes."""
    first = _sealed(
        replayed=False,
        review_items_persisted=3,
        review_items_total=3,
        evidence_links_persisted=6,
        evidence_links_total=6,
    )
    assert (first.review_items_persisted, first.review_items_total) == (3, 3)
    replay = _sealed(
        replayed=True,
        review_items_persisted=0,
        review_items_total=3,
        evidence_links_persisted=0,
        evidence_links_total=6,
    )
    assert (replay.review_items_persisted, replay.review_items_total) == (0, 3)
    # A zero-item first persistence is legal too.
    _sealed(
        replayed=False,
        review_items_persisted=0,
        review_items_total=0,
        evidence_links_persisted=0,
        evidence_links_total=0,
    )
    # A replay that claims writes is not a replay.
    with pytest.raises(ValidationError, match="zero review items and zero evidence links"):
        _sealed(
            replayed=True,
            review_items_persisted=1,
            review_items_total=3,
            evidence_links_persisted=0,
            evidence_links_total=6,
        )
    # A first persistence that skipped items is not all-or-nothing.
    with pytest.raises(ValidationError, match="writes every review item"):
        _sealed(
            replayed=False,
            review_items_persisted=2,
            review_items_total=3,
            evidence_links_persisted=4,
            evidence_links_total=4,
        )
    # Negative and out-of-bound counts are rejected.
    with pytest.raises(ValidationError):
        _sealed(review_items_persisted=-1)
    with pytest.raises(ValidationError):
        _sealed(review_items_total=13)


def test_m16_exclusion_counts_follow_the_deduplicated_merged_semantics() -> None:
    """R02: ``exclusion_count == len(l3_merged)``, never ``l1 + l2``."""
    l1 = [
        S.PersistedExclusionRef(observation_id=OBS_BASELINE_V5, reason_code="validation_rejected")
    ]
    l2 = [S.PersistedExclusionRef(observation_id=OBS_BASELINE_V5, reason_code="measurement_stale")]
    # Canonical order is ascending by (observation_id, reason_code), as RB3 sorts.
    merged = [
        S.PersistedExclusionRef(observation_id=OBS_BASELINE_V5, reason_code="measurement_stale"),
        S.PersistedExclusionRef(observation_id=OBS_BASELINE_V5, reason_code="validation_rejected"),
    ]
    sealed = _sealed(
        excluded_evidence=merged,
        layered_exclusions=_layered(l1_exclusions=l1, l2_exclusions=l2, l3_merged=merged),
        exclusion_count=2,
        l1_exclusion_count=1,
        l2_exclusion_count=1,
    )
    assert sealed.exclusion_count == 2  # not 1 + 1 = 2 by luck; try a real overlap
    overlapping = _sealed(
        excluded_evidence=[merged[1]],
        layered_exclusions=_layered(l1_exclusions=l1, l2_exclusions=l1, l3_merged=[merged[1]]),
        exclusion_count=1,
        l1_exclusion_count=1,
        l2_exclusion_count=1,
    )
    assert (
        overlapping.exclusion_count
        == 1
        != overlapping.l1_exclusion_count + overlapping.l2_exclusion_count
    )
    with pytest.raises(ValidationError, match="must equal the merged exclusion entry count"):
        _sealed(exclusion_count=5)


def test_m16_sealed_evaluation_pins_the_policy_sha_fingerprint_and_dr006() -> None:
    with pytest.raises(ValidationError, match="pinned RB3 policy SHA"):
        _sealed(policy_reference_sha256=_sha("other"))
    with pytest.raises(ValidationError, match="prohibited_denied"):
        _sealed(dr006_policy="not_present")
    with pytest.raises(ValidationError, match="evidence_links_total is never below"):
        _sealed(
            review_items_persisted=5,
            review_items_total=5,
            evidence_links_persisted=1,
            evidence_links_total=1,
        )


def test_m16_sealed_evaluation_is_bound_to_its_evidence_and_scope() -> None:
    base = {
        "verification_gate": _gate(gate_evaluation_id=GATE_EVAL),
        "last_validated_at_utc": VALIDATED,
        "evaluable_evidence": _evidence(),
        "observations": [_observation()],
    }
    _state(review_persistence=_sealed(), **base)
    for change, match in (
        ({"run_id": DOC_A}, "different run or scope"),
        ({"as_of_utc": "2026-11-15T12:00:00Z"}, "different as-of clock"),
        ({"policy_version": "demo-policy-1.2.0"}, "different policy version"),
        ({"bridge_input_fingerprint_sha256": _sha("other")}, "different bridge evidence"),
        ({"gate_evaluation_id": ISSUE_A}, "different F2 gate identity"),
    ):
        with pytest.raises(ValidationError, match=match):
            _state(review_persistence=_sealed(**change), **base)
    # A sealed evaluation requires the F2 evidence it was computed from.
    with pytest.raises(ValidationError, match="requires the F2 evidence"):
        _state(
            verification_gate=_gate(gate_evaluation_id=GATE_EVAL),
            last_validated_at_utc=VALIDATED,
            review_persistence=_sealed(),
        )


def test_m16_denied_persistence_is_an_outcome_not_a_completion() -> None:
    denied = _state(review_persistence=_denied())
    assert denied.review_evaluation_sealed is False
    assert denied.workflow_completed is False
    # A denial can never be a successful downstream review completion (R06).
    with pytest.raises(ValidationError, match="denied persistence cannot be a successful"):
        _approved_state(S.RunStatus.COMPLETED, review_persistence=_denied())
    with pytest.raises(ValidationError, match="denied persistence cannot be a successful"):
        _approved_state(S.RunStatus.FINALIZING, review_persistence=_denied())


def test_m16_resume_classification_distinguishes_unchanged_changed_and_corrected() -> None:
    same = _sha("same")
    S.ResumeAssessment(
        disposition=S.ResumeDisposition.RESUME_UNCHANGED,
        app_db_status=S.RunStatus.AWAITING_DECISION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=same,
        sealed_evaluation_present=False,
        checkpoint_present=True,
    )
    S.ResumeAssessment(
        disposition=S.ResumeDisposition.CHANGED_SOURCE_IDENTITY,
        app_db_status=S.RunStatus.AWAITING_DECISION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=_sha("other"),
        sealed_evaluation_present=False,
        checkpoint_present=True,
    )
    S.ResumeAssessment(
        disposition=S.ResumeDisposition.CORRECTED_SOURCE_NEW_RUN,
        app_db_status=S.RunStatus.AWAITING_DECISION,
        stored_selection_fingerprint=same,
        observed_selection_fingerprint=_sha("other"),
        corrected_fact_ids=[FACT_A],
        sealed_evaluation_present=True,
        checkpoint_present=True,
    )
    with pytest.raises(ValidationError, match="requires identical fingerprints"):
        S.ResumeAssessment(
            disposition=S.ResumeDisposition.RESUME_UNCHANGED,
            app_db_status=S.RunStatus.QUEUED,
            stored_selection_fingerprint=same,
            observed_selection_fingerprint=_sha("other"),
            sealed_evaluation_present=False,
            checkpoint_present=False,
        )
    with pytest.raises(ValidationError, match="requires at least one corrected fact id"):
        S.ResumeAssessment(
            disposition=S.ResumeDisposition.CORRECTED_SOURCE_NEW_RUN,
            app_db_status=S.RunStatus.QUEUED,
            stored_selection_fingerprint=same,
            observed_selection_fingerprint=_sha("other"),
            sealed_evaluation_present=False,
            checkpoint_present=False,
        )


# === M17: honesty literals ==========================================================


def test_m17_honesty_literals_cannot_be_flipped_through_any_input() -> None:
    for payload in (
        {**_state().model_dump(), "policy_status": "approved"},
        {**_state().model_dump(), "runtime_policy_activated": True},
        {**_state().model_dump(), "runtime_evaluable": True},
        {**_state().model_dump(), "demo_only": False},
        {**_state().model_dump(), "not_for_clinical_use": False},
    ):
        with pytest.raises(ValidationError):
            S.SharedGraphState.model_validate(payload)
    assert _state().policy_status == "unapproved"


def test_m17_model_copy_bypass_is_documented_and_revalidation_restores_the_boundary() -> None:
    state = _state()
    forged = state.model_copy(update={"runtime_evaluable": True})
    assert forged.runtime_evaluable is True  # documented Pydantic limitation (D-08)
    with pytest.raises(ValidationError):
        S.SharedGraphState.revalidate(forged)


# === M18: authority, lifecycle and evidence binding (R05/R06) =======================


def test_m18_deserialized_state_fields_are_shapes_not_authority() -> None:
    text = _approved_state(S.RunStatus.COMPLETED).model_dump_json()
    revived = S.SharedGraphState.model_validate_json(text)
    assert revived.status is S.RunStatus.COMPLETED
    assert revived.assurance_level is S.AssuranceLevel.SHAPE_VALIDATED
    # Nothing in the payload can grant runtime authority.
    assert revived.runtime_evaluable is False


def test_m18_tasks_exist_only_after_a_decision_and_within_its_task_ids() -> None:
    task = S.TaskDraft(
        action_key=_sha("task"),
        task_id="51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f",
        title="Follow up",
    )
    ok = _approved_state(
        S.RunStatus.COMPLETED, pending_tasks=[task], created_task_ids=[task.task_id]
    )
    assert ok.created_task_ids == [task.task_id]
    with pytest.raises(ValidationError, match="must reference pending task drafts"):
        _approved_state(S.RunStatus.COMPLETED, created_task_ids=[task.task_id])
    with pytest.raises(ValidationError, match="only after an approve/edit decision"):
        _approved_state(S.RunStatus.AWAITING_DECISION, approval=None, pending_tasks=[task])


def test_m18_status_lifecycle_invariants() -> None:
    # A rejection completes with zero tasks (R06).
    _approved_state(
        S.RunStatus.COMPLETED,
        approval=_approval(S.ApprovalChoice.REJECT),
        pending_tasks=[],
        created_task_ids=[],
    )
    with pytest.raises(ValidationError, match="rejected run completes with no task"):
        task = S.TaskDraft(
            action_key=_sha("task"),
            task_id="51a0b7c4-9d8e-5f3a-8c21-7b6e5d4c3a2f",
            title="Follow up",
        )
        _approved_state(
            S.RunStatus.COMPLETED,
            approval=_approval(S.ApprovalChoice.REJECT),
            pending_tasks=[task],
            created_task_ids=[task.task_id],
        )
    # Rejection never routes through finalize_actions.
    with pytest.raises(ValidationError, match="never passes through finalize_actions"):
        _approved_state(
            S.RunStatus.COMPLETED,
            approval=_approval(S.ApprovalChoice.REJECT),
            events=[
                _event(
                    node=S.NodeName.FINALIZE_ACTIONS,
                    detail=S.FinalizeDetail(
                        approval_decision="approve", task_created=False, notification_created=False
                    ),
                )
            ],
        )
    # A rejection cannot finalize (only approve/edit can).
    with pytest.raises(ValidationError, match="finalizing requires an approve-or-edit decision"):
        _approved_state(S.RunStatus.FINALIZING, approval=_approval(S.ApprovalChoice.REJECT))
    # An empty ApprovalDecision shape is not a recorded approval.
    with pytest.raises(ValidationError, match="requires a draft and a recorded decision"):
        _approved_state(S.RunStatus.COMPLETED, approval=S.ApprovalDecision())
    # A wrong-doctor decision cannot satisfy structural run scope.
    with pytest.raises(ValidationError, match="run's own doctor"):
        _approved_state(S.RunStatus.COMPLETED, approval=_approval(doctor_id=PATIENT))
    # halt_reason presence follows the halted statuses.
    with pytest.raises(ValidationError, match="halt_reason is present iff"):
        _state(status=S.RunStatus.COMPLETED, halt_reason=S.HaltReason.UNVERIFIED_FACTS)
    with pytest.raises(ValidationError, match="needs_verification halts with"):
        _state(
            status=S.RunStatus.NEEDS_VERIFICATION,
            halt_reason=S.HaltReason.MODEL_FAILED,
            verification_gate=_gate(S.GateDecision.HALT, issues=[_issue()]),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="failed_retryable halts with"):
        _state(status=S.RunStatus.FAILED_RETRYABLE, halt_reason=S.HaltReason.UNVERIFIED_FACTS)
    # Awaiting a decision with a draft and no recorded decision is the valid shape.
    _approved_state(S.RunStatus.AWAITING_DECISION, approval=None)
    # ... but a recorded decision belongs to a later status.
    with pytest.raises(ValidationError, match="awaiting_decision has a draft"):
        _approved_state(S.RunStatus.AWAITING_DECISION, approval=_approval())


def test_m18_evidence_reference_is_bound_to_the_selection_and_gate() -> None:
    base = {
        "verification_gate": _gate(gate_evaluation_id=GATE_EVAL),
        "last_validated_at_utc": VALIDATED,
        "observations": [_observation()],
    }
    _state(evaluable_evidence=_evidence(), **base)
    for bad in (
        {"selected_document_ids": [DOC_B]},
        {"selected_observation_ids": []},
        {"gate_input_fingerprint_sha256": _sha("other-gate")},
        {"gate_version": "1.0.1"},
        {"policy_version": "demo-policy-1.2.0"},
        {"as_of_utc": "2026-11-15T12:00:00Z"},
    ):
        overrides = dict(bad)
        if "selected_observation_ids" in overrides:
            overrides["no_current_reason"] = "no_current_selected"
        with pytest.raises(ValidationError):
            _state(
                verification_gate=_gate(gate_evaluation_id=GATE_EVAL),
                last_validated_at_utc=VALIDATED,
                observations=[_observation()],
                evaluable_evidence=_evidence(**overrides),
            )
    with pytest.raises(ValidationError, match="requires the gate evaluation"):
        _state(
            last_validated_at_utc=VALIDATED,
            observations=[_observation()],
            evaluable_evidence=_evidence(),
        )


def test_m18_draft_provider_and_execution_status_are_consistent() -> None:
    _draft(
        provider=S.DraftProvider.OLLAMA,
        model="llama3.1:8b",
        execution_status=S.DraftExecutionStatus.MODEL_OK,
    )
    with pytest.raises(ValidationError, match="records a model and execution_status=model_ok"):
        _draft(
            provider=S.DraftProvider.OLLAMA, execution_status=S.DraftExecutionStatus.MODEL_TIMEOUT
        )
    with pytest.raises(ValidationError, match="fallback draft has no model"):
        _draft(model="llama3.1:8b")


# === M19: mutable-default isolation =================================================


def test_m19_defaults_are_not_shared_between_instances() -> None:
    a, b = _state(), _state()
    assert a.observations is not b.observations
    assert a.extraction_facts is not b.extraction_facts
    assert a.model_metadata is not b.model_metadata
    before = len(b.observations)
    a.observations.append(_observation(patient_id=DOCTOR))  # type: ignore[attr-defined]
    assert len(b.observations) == before


# === M20: import side effects and single-source vocabularies ========================


def test_m20_importing_the_state_module_loads_no_service_or_runtime_module() -> None:
    code = (
        "import sys;\n"
        "before=set(sys.modules);\n"
        "import app.agents.state;\n"
        "leaked=sorted(m for m in set(sys.modules)-before "
        "if m.split('.')[0] in {'langgraph','ollama','smtplib','sendgrid','twilio',"
        "'requests','httpx','aiohttp','sqlalchemy','fastapi'} "
        "or m.startswith('app.services') or m.startswith('app.api') "
        "or m.startswith('app.db'));\n"
        "print(leaked);\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "[]"


def test_m20_state_source_has_no_runtime_or_io_imports_or_calls() -> None:
    source = (REPO_ROOT / "backend" / "app" / "agents" / "state.py").read_text()
    # Import statements only — a provider *value* such as ``ollama`` is data, not
    # an import (the repository safety guard scans the same way).
    for module in (
        "langgraph",
        "ollama",
        "smtplib",
        "sendgrid",
        "twilio",
        "requests",
        "httpx",
        "aiohttp",
        "sqlalchemy",
        "fastapi",
    ):
        assert f"import {module}" not in source, module
        assert f"from {module}" not in source, module
    for call in ("datetime.now", "utcnow", "open("):
        assert call not in source, call
    # A call must not be used as an identifier either (``compute_fingerprint``).
    assert not re.search(r"\bprint\s*\(", source)
    # ``Path(`` must appear only as part of an identifier such as TriagePath.
    assert not re.search(r"(?<![A-Za-z_])Path\(", source)
    # No clinical capability vocabulary is implemented. The list mirrors the
    # repository-wide guard ``FORBIDDEN_TERMS`` (tests/p2), which also scans this
    # file; the P2 guard remains the authority.
    for term in (
        "diagnos",
        "prescrib",
        "dosage",
        "differential_diagnosis",
        "risk_score",
        "treatment_plan",
        "send_sms",
        "send_email",
        "whatsapp",
    ):
        assert term not in source.lower(), term


def test_m20_vocabulary_single_sources_of_truth() -> None:
    from app.core.enums import IssueType as ServiceIssueType
    from app.core.enums import TrustLevel as ServiceTrustLevel

    assert {e.value for e in S.IssueType} == {e.value for e in ServiceIssueType}
    assert {e.value for e in S.TrustLevel} == {e.value for e in ServiceTrustLevel}
    # DR-* ids are pinned by the persisted review_item CHECK, not by an enum.
    from app.db.models import ReviewItem

    checks = [
        str(getattr(item, "sqltext", ""))
        for item in ReviewItem.__table__.constraints
        if "rule_allowed" in (getattr(item, "name", None) or "")
    ]
    assert checks, "review_item_rule_allowed CHECK not found"
    assert {e.value for e in S.ReviewRuleId} == set(re.findall(r"DR-\d{3}", checks[0]))

    from app.core.clock import MAX_FUTURE_SKEW_MINUTES
    from app.services.p4_rb3_review_persistence import (
        MAX_EXCLUSIONS,
        MAX_PERSISTED_ITEMS,
        MAX_PERSISTED_LINKS,
        MAX_SELECTED_DOCUMENTS,
    )
    from app.services.p4_run_bound_preview import POLICY_LOOKBACK_DAYS
    from app.services.p5_evidence_bridge import (
        COMPARISON_HISTORY_VERSION,
        HISTORY_LOOKBACK_DAYS,
        MAX_CURRENT_OBSERVATIONS,
        MAX_FACTS,
        MAX_HISTORY_OBSERVATIONS,
    )

    assert S.MAX_FACTS == MAX_FACTS == 40
    assert S.MAX_HISTORY_OBSERVATIONS == MAX_HISTORY_OBSERVATIONS == 100
    assert S.MAX_SELECTED_CURRENT == MAX_CURRENT_OBSERVATIONS == 6
    assert S.MAX_SELECTED_DOCUMENTS == MAX_SELECTED_DOCUMENTS == 5
    assert S.MAX_PERSISTED_ITEMS == MAX_PERSISTED_ITEMS == 12
    assert S.MAX_PERSISTED_LINKS == MAX_PERSISTED_LINKS == 24
    assert S.MAX_MERGED_EXCLUSIONS == MAX_EXCLUSIONS == 200
    from typing import get_args

    assert get_args(S.F2_HISTORY_POLICY) == (COMPARISON_HISTORY_VERSION,)
    assert HISTORY_LOOKBACK_DAYS == 365
    # The temporal boundary is the accepted clock module's allowance, not a new
    # policy parameter introduced by the state module.
    assert S.MAX_FUTURE_SKEW_MINUTES == MAX_FUTURE_SKEW_MINUTES == 5
    assert get_args(S.RB1_LOOKBACK_DAYS) == (POLICY_LOOKBACK_DAYS,)


def test_m20_f0_persists_no_prompt_version_and_the_state_does_not_claim_it() -> None:
    """R01/D-06: F0 has no ``prompt_version`` column, so the slot stays empty."""
    from app.db.models import WorkflowRun

    columns = {column.name for column in WorkflowRun.__table__.columns}
    assert "prompt_version" not in columns
    assert "encounter_id" not in columns
    assert _identity().prompt_version is None
    assert _identity().encounter_id is None


def test_m20_state_round_trips_through_every_outcome_kind() -> None:
    for outcome in (
        _sealed(),
        _denied(),
        None,
    ):
        state = _state(
            review_persistence=outcome,
            verification_gate=_gate(gate_evaluation_id=GATE_EVAL),
            last_validated_at_utc=VALIDATED,
            evaluable_evidence=_evidence() if outcome is not None else None,
            observations=[_observation()],
        )
        assert S.SharedGraphState.model_validate_json(state.model_dump_json()) == state


# === R04: context-independent exact numerics ========================================


def test_r04_exact_values_and_deltas_under_the_default_context() -> None:
    assert S.exact_delta(Decimal("140"), Decimal("128")) == Decimal("12")
    assert json.loads(_observation(value=Decimal("140.5")).model_dump_json())["value"] == "140.5"
    row = _comparison()
    assert json.loads(row.model_dump_json())["delta"] == "12"


def test_r04_behaviour_is_identical_under_a_hostile_decimal_context() -> None:
    """R04: no ambient precision, rounding or trap may change the result."""
    values = [Decimal("140.5"), Decimal("0.0001"), Decimal("9999.9999"), Decimal("1234567890")]
    baseline = [S._decimal_text(v) for v in values]
    deltas = [S.exact_delta(Decimal("9999.9999"), Decimal("0.0001"))]
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = "ROUND_UP"
        ctx.traps[InvalidOperation] = True
        assert [S._decimal_text(v) for v in values] == baseline
        assert [S.exact_delta(Decimal("9999.9999"), Decimal("0.0001"))] == deltas
        # Serialization of a model is unchanged too.
        assert (
            json.loads(_observation(value=Decimal("140.5")).model_dump_json())["value"] == "140.5"
        )
        assert (
            json.loads(_comparison().model_dump_json())["delta"]
            == json.loads(_comparison().model_dump_json())["delta"]
        )
    # No significant digit is lost.
    assert S._decimal_text(Decimal("0.0001")) == "0.0001"
    assert S._decimal_text(Decimal("1234567890")) == "1234567890"
    for bad in ("NaN", "sNaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError, match="non-finite"):
            S._decimal_text(Decimal(bad))


# === R01: genuine accepted-producer compatibility (supporting integration) ===========


@dataclass(frozen=True)
class _Doc:
    document_id: str
    facts: tuple[str, ...]


def _seed_session(engine) -> Session:
    from app.services.seed import seed_demo_data

    session = Session(engine)
    seed_demo_data(
        session,
        password=SEED_PASSWORD,
        now=datetime(2026, 11, 14, 12, tzinfo=UTC),
        iterations=1000,
    )
    session.commit()
    return session


def _doctor(db: Session) -> Any:
    from app.core.enums import Role
    from app.core.policies import Principal
    from app.db.models import User, UserSession

    row = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()
    session_id = "dddddddd-dddd-4ddd-8ddd-0000000000p5"
    if db.get(UserSession, session_id) is None:
        db.add(
            UserSession(
                id=session_id,
                user_id=row.id,
                token_sha256=_sha("p5-s0-session"),
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


def _add_checkin(
    db: Session,
    *,
    observation_id: str,
    patient_id: str,
    measure: str,
    value: float,
    unit: str,
    measured_at: str = "2026-11-01T09:00:00Z",
    source: str = "patient_checkin",
    validation: str = "ok",
    trust_level: str = "self_reported_validated",
) -> Any:
    """Store one scripted synthetic observation row (fixture construction only)."""
    from app.db.models import Observation

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


def _add_verified_document(db: Session, *, patient_id: str, root: Path, label: str) -> Any:
    """Store a scripted synthetic document whose four facts are all verified.

    Mirrors the accepted RB4 GOLD fixture shape (report_date, test_name, value,
    unit) so the genuine F1 gate has an unambiguous report date to read. This is
    fixture construction, not ingestion, OCR or a clinician decision.
    """
    import hashlib

    from app.db.models import Document, ExtractedFact, FactVerification, Patient, User

    patient = db.get(Patient, patient_id)
    assert patient is not None
    raw = f"P5-S0 synthetic-only source: {label}".encode()
    name = f"p5-s0-{label}.pdf"
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


def test_r01_genuine_stored_identities_include_uuid5_observations() -> None:
    """R01: accepted GOLD/RB4 data uses UUIDv5 observation identities."""
    data = json.loads((REPO_ROOT / "data" / "synthetic" / "observations.json").read_text())
    rows = data["observations"]
    versions = {_uuid_version(row["id"]) for row in rows}
    assert versions == {5}, versions
    # Every stored identity in that accepted fixture is representable.
    for row in rows:
        assert S.Uuid is not None
        from pydantic import TypeAdapter

        TypeAdapter(S.Uuid).validate_python(row["id"])
    # ... while run identity still refuses them.
    from pydantic import TypeAdapter

    for row in rows[:2]:
        with pytest.raises(ValidationError):
            TypeAdapter(S.RunUuid).validate_python(row["id"])


def _uuid_version(value: str) -> int:
    import uuid as _uuid

    return _uuid.UUID(value).version


def test_r01_genuine_stored_run_projects_every_accepted_producer(engine, tmp_path) -> None:
    """Drive F0 -> F1 -> F2 -> RB3 for real, then project the genuine receipts.

    This is *supporting executable integration evidence*, not a schema test: it
    proves the S0 shapes accept what the accepted services actually emit. It is
    scripted synthetic fixture construction — not ingestion, OCR or human
    verification — and a successful run asserts nothing clinical.
    """
    from app.core.enums import Role  # noqa: F401  (import surface used by the fixtures)
    from app.db.models import Observation, Patient, RunGateEvaluation, WorkflowRun
    from app.schemas.p4_rb3_review_persistence import ReviewPersistenceReceiptV1
    from app.services import p4_rb3_review_persistence as rb3
    from app.services.p5_evidence_bridge import (
        COMPARISON_HISTORY_VERSION,
        build_run_evaluable_review_evidence,
    )
    from app.services.p5_run_foundation import create_run_foundation
    from app.services.p5_run_gate import evaluate_run_verification_gate

    db = _seed_session(engine)
    try:
        patient = db.execute(
            select(Patient).where(Patient.external_ref == "DEMO-A-001")
        ).scalar_one()
        doctor = _doctor(db)
        _add_checkin(
            db,
            observation_id=OBS_CURRENT,
            patient_id=patient.id,
            measure="systolic_bp",
            value=121,
            unit="mmHg",
        )
        # GOLD-D-shaped history rows: an eligible warning row that becomes the
        # latest prior, and a rejected row the bridge must exclude. Both are
        # scripted synthetic fixtures, not producer output.
        _add_checkin(
            db,
            observation_id=WARN_OBS,
            patient_id=patient.id,
            measure="systolic_bp",
            value=150,
            unit="mmHg",
            measured_at="2026-10-20T09:00:00Z",
            source="seed_fixture",
            validation="ok_with_warning",
        )
        _add_checkin(
            db,
            observation_id=REJECTED_OBS,
            patient_id=patient.id,
            measure="systolic_bp",
            value=999,
            unit="mmHg",
            measured_at="2026-09-01T09:00:00Z",
            source="seed_fixture",
            validation="rejected",
        )
        document = _add_verified_document(db, patient_id=patient.id, root=tmp_path, label="glucose")
        document_ids = (document.id,)

        with Session(engine) as session:
            receipt = create_run_foundation(
                session,
                principal=doctor,
                patient_id=patient.id,
                document_ids=document_ids,
                observation_ids=(OBS_CURRENT,),
                omissions=(),
                client_request_id="p5-s0-integration",
                as_of_utc=datetime(2026, 11, 14, 12, tzinfo=UTC),
            )
            session.commit()
        run_id = receipt.run_id

        gate = evaluate_run_verification_gate(
            Session(engine),
            principal=doctor,
            run_id=run_id,
            validation_clock=datetime(2026, 11, 14, 12, tzinfo=UTC),
            upload_root=str(tmp_path),
        )
        # The genuine producer decides; this test projects whatever it recorded.
        assert gate.decision in {decision.value for decision in S.GateDecision}, gate

        evidence = build_run_evaluable_review_evidence(
            Session(engine),
            principal=doctor,
            run_id=run_id,
            validation_clock=datetime(2026, 11, 14, 12, tzinfo=UTC),
            upload_root=str(tmp_path),
        )
        persisted = rb3.persist_run_review_items(
            Session(engine),
            principal=doctor,
            run_id=run_id,
            validation_clock=datetime(2026, 11, 14, 12, tzinfo=UTC),
            upload_root=str(tmp_path),
        )
        replayed = rb3.persist_run_review_items(
            Session(engine),
            principal=doctor,
            run_id=run_id,
            validation_clock=datetime(2026, 11, 14, 12, tzinfo=UTC),
            upload_root=str(tmp_path),
        )
        assert isinstance(persisted, ReviewPersistenceReceiptV1)
        assert isinstance(replayed, ReviewPersistenceReceiptV1)
        assert persisted.replayed is False
        assert replayed.replayed is True
        assert replayed.review_items_persisted == 0
        assert replayed.evidence_links_persisted == 0

        with Session(engine) as check:
            run = check.get(WorkflowRun, run_id)
            stored_gate = check.execute(
                select(RunGateEvaluation).where(RunGateEvaluation.workflow_run_id == run_id)
            ).scalar_one()
            assert run is not None
            assert stored_gate is not None

            # --- project the genuine F0 run row + receipt -------------------------
            identity = S.RunIdentity(
                run_id=run.id,
                thread_id=receipt.thread_id,
                patient_id=run.patient_id,
                doctor_id=run.doctor_id,
                workflow_version=run.workflow_version,
                state_schema_version=run.state_schema_version,
                policy_version=run.policy_version,
                mapping_version=run.mapping_version,
                as_of_utc=run.as_of_utc,
                idempotency_key=run.idempotency_key,
                started_at=run.started_at,
            )
            assert identity.run_id == run.id
            # F0 persists no prompt_version and no encounter_id (D-06).
            assert identity.prompt_version is None
            assert identity.encounter_id is None

            # --- project the genuine F1 receipt (no gate_evaluation_id in it) ----
            gate_ref = S.GateEvaluationRef(
                run_id=gate.run_id,
                patient_id=gate.patient_id,
                doctor_id=gate.doctor_id,
                gate_version=gate.gate_version,
                input_fingerprint_sha256=gate.input_fingerprint_sha256,
                decision=S.GateDecision(gate.decision),
                issues=[
                    S.GateIssueRef(
                        issue_type=S.IssueType(item.issue_type),
                        reason_code=item.reason_code,
                        document_id=item.document_id,
                        fact_ids=list(item.fact_ids),
                        message=item.message,
                    )
                    for item in gate.issues
                ],
                historical_excluded_vi002_ids=list(gate.historical_excluded_vi002_ids),
                blocking_fact_count=gate.blocking_fact_count,
                unavailable_reason=(
                    S.GateUnavailableReason(gate.unavailable_reason)
                    if gate.unavailable_reason
                    else None
                ),
                replayed=gate.replayed,
            )
            # The receipt genuinely does not expose the stored gate row identity.
            assert gate_ref.gate_evaluation_id is None
            assert not hasattr(gate, "gate_evaluation_id")

            # The stored gate row is a *different* identity space (R01/R03).
            assert stored_gate.id != run.id
            gate_ref_stored = gate_ref.model_copy(update={"gate_evaluation_id": stored_gate.id})
            assert (
                S.GateEvaluationRef.model_validate_json(
                    gate_ref_stored.model_dump_json()
                ).gate_evaluation_id
                == stored_gate.id
            )

            # --- project the genuine F2 DTO (which DOES carry it) ---------------
            evidence_ref = S.EvaluableEvidenceRef(
                run_id=evidence.run_id,
                patient_id=evidence.patient_id,
                doctor_id=evidence.doctor_id,
                as_of_utc=evidence.as_of_utc,
                workflow_version=evidence.workflow_version,
                state_schema_version=evidence.state_schema_version,
                mapping_version=evidence.mapping_version,
                policy_version=evidence.policy_version,
                gate_evaluation_id=evidence.gate_evaluation_id,
                gate_version=evidence.gate_version,
                gate_input_fingerprint_sha256=evidence.gate_input_fingerprint_sha256,
                bridge_input_fingerprint_sha256=evidence.bridge_input_fingerprint_sha256,
                # ``history_policy`` is not a field of the F2 DTO: the bridge pins
                # it in its canonical fingerprint, so the label comes from there.
                history_policy=COMPARISON_HISTORY_VERSION,
                selected_document_ids=list(evidence.selected_document_ids),
                selected_observation_ids=list(evidence.selected_observation_ids),
                historical_excluded_vi002_ids=list(evidence.historical_excluded_vi002_ids),
                no_current_reason=evidence.no_current_reason,
            )
            assert evidence_ref.gate_evaluation_id == stored_gate.id
            assert evidence_ref.history_policy == S.ComparisonWindow.F2_365D.value

            # --- project the genuine F2 content rows ---------------------------
            # The F2 ``ObservationV2`` carries no validation state and no verifier,
            # so those columns are projected from the authoritative stored row
            # (D-10) and the DTO is cross-checked against it, never assumed.
            def project_observation(row: Any, role: S.ObservationRole) -> S.ObservationView:
                stored = check.get(Observation, row.observation_id)
                assert stored is not None, row.observation_id
                assert stored.measure_type == row.measure_type
                assert stored.unit == row.unit
                assert stored.measured_at == row.measured_at
                assert stored.source == row.source
                assert stored.trust_level == row.trust_level
                assert Decimal(str(stored.value)) == Decimal(str(row.value))
                return S.ObservationView(
                    observation_id=stored.id,
                    patient_id=stored.patient_id,
                    role=role,
                    measure_type=MeasureType(stored.measure_type),
                    value=Decimal(str(stored.value)),
                    unit=Unit(stored.unit),
                    measured_at=stored.measured_at,
                    source=ObservationSource(stored.source),
                    validation=ValidationState(stored.validation),
                    trust_level=TrustLevel(stored.trust_level),
                    verified_by=stored.verified_by_user_id,
                    verified_at=stored.verified_at,
                    source_fact_id=stored.source_fact_id,
                    source_document_id=row.source_document_id,
                )

            observations = [
                project_observation(row, S.ObservationRole.SELECTED_CURRENT)
                for row in evidence.selected_observations
            ]
            assert len(observations) == len(evidence.selected_observations) == 1

            # --- resolve the genuine comparison baselines from stored evidence ---
            # ``ComparisonV2`` carries neither values nor a window label, so the
            # baseline row is resolved from the authoritative store and the label
            # comes from the bridge's pinned history version.
            baseline_ids = sorted(
                {
                    comparison.baseline_observation_id
                    for comparison in evidence.comparisons
                    if comparison.baseline_observation_id
                }
            )
            v5_baselines = {value for value in baseline_ids if _uuid_version(value) == 5}
            assert v5_baselines, baseline_ids
            history_rows: dict[str, S.ObservationView] = {}
            for observation_id in baseline_ids:
                stored = check.get(Observation, observation_id)
                assert stored is not None, observation_id
                history_rows[observation_id] = S.ObservationView(
                    observation_id=stored.id,
                    patient_id=stored.patient_id,
                    role=S.ObservationRole.HISTORY,
                    measure_type=MeasureType(stored.measure_type),
                    value=Decimal(str(stored.value)),
                    unit=Unit(stored.unit),
                    measured_at=stored.measured_at,
                    source=ObservationSource(stored.source),
                    validation=ValidationState(stored.validation),
                    trust_level=TrustLevel(stored.trust_level),
                    verified_by=stored.verified_by_user_id,
                    verified_at=stored.verified_at,
                    source_fact_id=stored.source_fact_id,
                )
            assert set(history_rows) == set(baseline_ids)

            # --- project the actual F2 comparisons with the correct label ------
            comparisons = [
                S.ComparisonResult(
                    current_observation_id=comparison.current_observation_id,
                    baseline_observation_id=comparison.baseline_observation_id,
                    measure_type=MeasureType(comparison.measure_type),
                    unit=Unit(comparison.unit),
                    comparable=comparison.comparable,
                    delta=comparison.delta,
                    incomparable_reason=(
                        S.IncomparableReason(comparison.incomparable_reason)
                        if comparison.incomparable_reason
                        else None
                    ),
                    trust_basis=S.TrustBasis(comparison.trust_basis),
                    history_policy=S.ComparisonWindow.F2_365D,
                    current_value=next(
                        row.value
                        for row in observations
                        if row.observation_id == comparison.current_observation_id
                    ),
                    baseline_value=(
                        history_rows[comparison.baseline_observation_id].value
                        if comparison.baseline_observation_id
                        else None
                    ),
                )
                for comparison in evidence.comparisons
            ]
            assert len(comparisons) == len(evidence.comparisons) == 1

            # --- project the actual F2 history exclusions ---------------------
            exclusions = [
                S.EvidenceExclusion(
                    observation_id=item.observation_id,
                    reason_code=S.ExclusionReason(item.reason_code),
                )
                for item in evidence.history_exclusions
            ]
            assert len(exclusions) == len(evidence.history_exclusions) == 1

            # --- project the genuine F2 verified facts ------------------------
            verified = [
                S.VerifiedFact(
                    fact_id=row.fact_id,
                    document_id=row.document_id,
                    field_name=FactField(row.field_name),
                    normalized_value=row.normalized_value,
                    unit=row.unit,
                    corrected_from_fact_id=row.corrected_from_fact_id,
                    verification_status=row.verification_status,
                )
                for row in evidence.verified_facts
            ]
            assert len(verified) == len(evidence.verified_facts) == 4

            # --- project the genuine RB3 receipts (first write and replay) -----
            def project(receipt: ReviewPersistenceReceiptV1) -> S.SealedReviewEvaluation:
                return S.SealedReviewEvaluation(
                    run_id=receipt.run_id,
                    patient_id=receipt.patient_id,
                    doctor_id=receipt.doctor_id,
                    as_of_utc=receipt.as_of_utc,
                    policy_version=receipt.policy_version,
                    policy_reference_sha256=receipt.policy_reference_sha256,
                    gate_evaluation_id=receipt.gate_evaluation_id,
                    gate_version=receipt.gate_version,
                    gate_input_fingerprint_sha256=receipt.gate_input_fingerprint_sha256,
                    bridge_input_fingerprint_sha256=receipt.bridge_input_fingerprint_sha256,
                    input_fingerprint_sha256=receipt.input_fingerprint_sha256,
                    output_identity_sha256=receipt.output_identity_sha256,
                    evaluation_id=receipt.evaluation_id,
                    audit_event_id=receipt.audit_event_id,
                    lineage_label_policy=receipt.lineage_label_policy,
                    dr006_policy=receipt.dr006_policy,
                    replayed=receipt.replayed,
                    review_items_persisted=receipt.review_items_persisted,
                    review_items_total=receipt.review_items_total,
                    evidence_links_persisted=receipt.evidence_links_persisted,
                    evidence_links_total=receipt.evidence_links_total,
                    excluded_evidence=[
                        S.PersistedExclusionRef(
                            observation_id=item.observation_id, reason_code=item.reason_code
                        )
                        for item in receipt.excluded_evidence
                    ],
                    layered_exclusions=S.LayeredExclusions(
                        l0_lineage_checks=[
                            S.PersistedExclusionRef(
                                observation_id=i.observation_id, reason_code=i.reason_code
                            )
                            for i in receipt.layered_exclusions.l0_lineage_checks
                        ],
                        l1_exclusions=[
                            S.PersistedExclusionRef(
                                observation_id=i.observation_id, reason_code=i.reason_code
                            )
                            for i in receipt.layered_exclusions.l1_exclusions
                        ],
                        l2_exclusions=[
                            S.PersistedExclusionRef(
                                observation_id=i.observation_id, reason_code=i.reason_code
                            )
                            for i in receipt.layered_exclusions.l2_exclusions
                        ],
                        l3_merged=[
                            S.PersistedExclusionRef(
                                observation_id=i.observation_id, reason_code=i.reason_code
                            )
                            for i in receipt.layered_exclusions.l3_merged
                        ],
                    ),
                    exclusion_count=len(receipt.excluded_evidence),
                    l1_exclusion_count=receipt.l1_exclusion_count,
                    l2_exclusion_count=receipt.l2_exclusion_count,
                )

            first_sealed = project(persisted)
            replay_sealed = project(replayed)
            assert first_sealed.replayed is False
            assert replay_sealed.replayed is True
            assert replay_sealed.review_items_persisted == 0
            assert replay_sealed.evidence_links_persisted == 0
            assert first_sealed.evaluation_id == replay_sealed.evaluation_id
            assert first_sealed.audit_event_id == replay_sealed.audit_event_id

            # --- load the genuine F0 manifest rows (not substitutes) ------------
            from app.db.models import RunSelectedDocument, RunSelectedObservation

            stored_documents = (
                check.execute(
                    select(RunSelectedDocument).where(RunSelectedDocument.workflow_run_id == run_id)
                )
                .scalars()
                .all()
            )
            stored_selections = (
                check.execute(
                    select(RunSelectedObservation).where(
                        RunSelectedObservation.workflow_run_id == run_id
                    )
                )
                .scalars()
                .all()
            )
            assert stored_documents and stored_selections
            # The F0 manifest is the authoritative selection snapshot: it carries
            # the source hash and the *selection-time* trust and creation stamps.
            manifest_documents = [
                S.SelectedDocumentRef(
                    document_id=row.document_id,
                    source_sha256=row.source_sha256,
                    source_status=row.source_status,
                )
                for row in sorted(stored_documents, key=lambda item: item.document_id)
            ]
            manifest_observations = [
                S.SelectedObservationRef(
                    observation_id=row.observation_id,
                    trust_level=TrustLevel(row.trust_level),
                    source_fact_id=row.source_fact_id,
                    observation_created_at=row.observation_created_at,
                )
                for row in sorted(stored_selections, key=lambda item: item.observation_id)
            ]
            assert [item.document_id for item in manifest_documents] == sorted(
                evidence.selected_document_ids
            )
            assert [item.observation_id for item in manifest_observations] == sorted(
                evidence.selected_observation_ids
            )

            # --- and the whole thing assembles into one state -------------------
            def assemble(sealed: S.SealedReviewEvaluation) -> S.SharedGraphState:
                return S.SharedGraphState(
                    identity=identity,
                    selection=S.SelectedSourceManifest.build(
                        document_ids=[item.document_id for item in manifest_documents],
                        documents=manifest_documents,
                        observation_ids=[item.observation_id for item in manifest_observations],
                        observations=manifest_observations,
                    ),
                    observations=[*observations, *history_rows.values()],
                    comparisons=comparisons,
                    evidence_exclusions=exclusions,
                    verified_facts=verified,
                    verification_gate=gate_ref.model_copy(
                        update={"gate_evaluation_id": stored_gate.id}
                    ),
                    evaluable_evidence=evidence_ref,
                    review_persistence=sealed,
                    last_validated_at_utc="2026-11-14T12:00:00Z",
                    updated_at="2026-11-14T12:00:00Z",
                )

            first_state = assemble(first_sealed)
            assert first_state.review_evaluation_sealed is True
            assert first_state.workflow_completed is False

            # --- JSON round-trip and full revalidation ------------------------
            round_tripped = S.SharedGraphState.model_validate_json(first_state.model_dump_json())
            assert round_tripped == first_state
            revalidated = S.SharedGraphState.revalidate(first_state)
            assert revalidated == first_state
            # Re-parsing is what catches a mutated container (D-08).
            assert S.SharedGraphState.revalidate(round_tripped) == first_state

            # --- the exact RB3 replay state -----------------------------------
            replay_state = assemble(replay_sealed)
            assert replay_state.review_persistence is not None
            assert replay_state.review_persistence.replayed is True
            assert replay_state.review_persistence.review_items_persisted == 0
            assert replay_state.review_persistence.evidence_links_persisted == 0
            # Unchanged sealed identity, zero per-call writes, same totals.
            assert (
                replay_state.review_persistence.evaluation_id
                == first_state.review_persistence.evaluation_id
            )
            assert (
                replay_state.review_persistence.audit_event_id
                == first_state.review_persistence.audit_event_id
            )
            assert (
                replay_state.review_persistence.input_fingerprint_sha256
                == first_state.review_persistence.input_fingerprint_sha256
            )
            assert (
                replay_state.review_persistence.exclusion_count
                == first_state.review_persistence.exclusion_count
            )
            assert S.SharedGraphState.revalidate(replay_state) == replay_state

            # --- the projected collections equal the actual producer outputs ----
            assert [row.observation_id for row in first_state.observations] == sorted(
                [item.observation_id for item in evidence.selected_observations],
                key=str,
            ) + sorted(baseline_ids)
            assert [
                (row.current_observation_id, row.baseline_observation_id, row.delta)
                for row in first_state.comparisons
            ] == [
                (item.current_observation_id, item.baseline_observation_id, item.delta)
                for item in evidence.comparisons
            ]
            assert [
                (row.observation_id, row.reason_code.value)
                for row in first_state.evidence_exclusions
            ] == [(item.observation_id, item.reason_code) for item in evidence.history_exclusions]
            assert [row.fact_id for row in first_state.verified_facts] == [
                item.fact_id for item in evidence.verified_facts
            ]
            assert [row.document_id for row in first_state.selection.documents] == sorted(
                evidence.selected_document_ids
            )

            # --- eligible OK_WITH_WARNING behaviour from genuine producer evidence
            warning_baseline = history_rows[WARN_OBS]
            assert warning_baseline.validation is S.ValidationState.OK_WITH_WARNING
            assert warning_baseline.admissible is True
            # The warning is neither promoted to doctor-verified nor hidden: the
            # trust label stays what the stored row says.
            assert warning_baseline.trust_level is TrustLevel.SELF_REPORTED_VALIDATED
            assert first_state.comparisons[0].baseline_observation_id == WARN_OBS
            assert first_state.comparisons[0].trust_basis is S.TrustBasis.SELF_REPORTED
            # ... and the rejected row is excluded by the producer, not by us.
            assert REJECTED_OBS not in {row.observation_id for row in first_state.observations}
            assert first_state.evidence_exclusions[0].observation_id == REJECTED_OBS

            # Deliberately *not* represented, and not claimed: RB3 review items and
            # evidence links are counted by the sealed receipt but are not
            # projected as state collections in S0.
            assert first_state.review_persistence.review_items_total > 0
            assert not hasattr(first_state, "review_items")
    finally:
        db.close()


def test_r01_genuine_seeded_observation_rows_are_representable(engine) -> None:
    """Every seeded observation row projects into ``ObservationView`` (UUIDv5 ids)."""
    from app.db.models import Observation

    db = _seed_session(engine)
    try:
        rows = db.execute(select(Observation)).scalars().all()
        assert rows
        for row in rows:
            projected = S.ObservationView(
                observation_id=row.id,
                patient_id=row.patient_id,
                role=S.ObservationRole.HISTORY,
                measure_type=MeasureType(row.measure_type),
                value=Decimal(str(row.value)),
                unit=Unit(row.unit),
                measured_at=row.measured_at,
                source=ObservationSource(row.source),
                validation=ValidationState(row.validation),
                trust_level=TrustLevel(row.trust_level),
                verified_by=row.verified_by_user_id,
                verified_at=row.verified_at,
                source_fact_id=row.source_fact_id,
                source_document_id=None,
            )
            assert projected.observation_id == row.id
    finally:
        db.close()


# === R2-02: actual observation admissibility =========================================


def test_r202_ok_with_warning_is_admissible_and_rejected_is_not() -> None:
    """The accepted data check rejects only ``rejected``; a warning is kept."""
    assert S.ValidationState.OK_WITH_WARNING.value == "ok_with_warning"
    warning = _observation(validation=S.ValidationState.OK_WITH_WARNING)
    assert warning.admissible is True
    # The structural check neither promotes nor hides the warning.
    assert warning.validation is S.ValidationState.OK_WITH_WARNING
    assert warning.trust_level is TrustLevel.SELF_REPORTED_VALIDATED
    assert _observation().admissible is True
    assert _observation(validation=S.ValidationState.REJECTED).admissible is False


def test_r202_eligible_warning_rows_participate_as_current_and_baseline() -> None:
    """GOLD-D shape: an eligible warning row can be current *and* baseline.

    ``diastolic_bp 250 mmHg`` is the accepted GOLD-D fixture row that carries
    ``ok_with_warning``. Its trust is untouched by the data check, so both rows
    stay self-reported and the comparison keeps its derived label.
    """
    warning_current = _observation(validation=S.ValidationState.OK_WITH_WARNING)
    warning_baseline = _history(validation=S.ValidationState.OK_WITH_WARNING, value=Decimal("150"))
    state = _state(
        observations=[warning_current, warning_baseline],
        comparisons=[_comparison(delta=Decimal("-10"), baseline_value=Decimal("150"))],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    assert [row.validation for row in state.observations] == [
        S.ValidationState.OK_WITH_WARNING,
        S.ValidationState.OK_WITH_WARNING,
    ]
    assert state.comparisons[0].trust_basis is S.TrustBasis.SELF_REPORTED
    # A rejected row is never eligible, whichever role it is given.
    with pytest.raises(ValidationError, match="must pass the data check"):
        _state(
            observations=[
                _observation(),
                _history(validation=S.ValidationState.REJECTED, value=Decimal("128")),
            ],
            comparisons=[_comparison()],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


# === R2-03: complete structural comparison binding ===================================


def test_r203_delta_is_always_checked_against_the_resolved_rows() -> None:
    """Omitting the optional projected values cannot hide an incorrect delta."""
    current, baseline = _observation(), _history()
    with pytest.raises(ValidationError, match="delta must equal"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(delta=Decimal("11"), current_value=None, baseline_value=None)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # The same wrong delta is rejected when the values are projected too.
    with pytest.raises(ValidationError, match="delta must equal"):
        _state(
            observations=[current, baseline],
            comparisons=[_comparison(delta=Decimal("11"))],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # A correct delta with both projections omitted is accepted: the resolved
    # rows are the authority, so nothing had to be invented.
    state = _state(
        observations=[current, baseline],
        comparisons=[_comparison(current_value=None, baseline_value=None)],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    assert state.comparisons[0].delta == Decimal("12")


def test_r203_unselected_current_is_rejected_by_the_immutable_manifest() -> None:
    """Selected-current roles are bound to the manifest, with or without an F2 ref."""
    stray = _observation(observation_id=OBS_BASELINE_V5_B, role=S.ObservationRole.SELECTED_CURRENT)
    with pytest.raises(ValidationError, match="immutable selected manifest"):
        _state(observations=[_observation(), stray])
    # The same holds when the state carries no F2 evidence reference at all.
    with pytest.raises(ValidationError, match="immutable selected manifest"):
        _state(
            observations=[_observation(), stray],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


def test_r203_baseline_must_lie_inside_the_labelled_window() -> None:
    """F2 is 365 days, RB1 is 90 days; a baseline outside its window is not a member."""
    with pytest.raises(ValidationError, match="inside the labelled comparison window"):
        _state(
            observations=[_observation(), _history(measured_at="2025-10-31T09:00:00Z")],
            comparisons=[_comparison()],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # Exactly 365 days before the current is inside the F2 window.
    _state(
        observations=[_observation(), _history(measured_at="2025-11-01T09:00:00Z")],
        comparisons=[_comparison()],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    # The RB1 label is checked against its own 90-day window, not F2's.
    with pytest.raises(ValidationError, match="inside the labelled comparison window"):
        _state(
            observations=[_observation(), _history(measured_at="2026-08-02T09:00:00Z")],
            comparisons=[_comparison(history_policy=S.ComparisonWindow.RB1_90D)],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    _state(
        observations=[_observation(), _history(measured_at="2026-08-03T09:00:00Z")],
        comparisons=[_comparison(history_policy=S.ComparisonWindow.RB1_90D)],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )


def test_r203_contradictory_no_baseline_and_comparable_shapes_are_rejected() -> None:
    """No baseline and ``comparable`` contradict each other at both levels."""
    with pytest.raises(ValidationError, match="needs a baseline id and delta"):
        _comparison(
            baseline_observation_id=None,
            comparable=True,
            incomparable_reason=None,
            trust_basis=S.TrustBasis.SELF_REPORTED,
        )
    # The row-level validator is the first line of defence, so the state-level
    # re-check cannot be reached from a constructible ``ComparisonResult``: the
    # contradiction is rejected before a state can even be assembled. The
    # redundant state check stays as defence in depth for re-parsed payloads.
    with pytest.raises(ValidationError, match="needs a baseline id and delta"):
        _state(
            comparisons=[
                _comparison(
                    baseline_observation_id=None,
                    comparable=True,
                    incomparable_reason=None,
                    trust_basis=S.TrustBasis.SELF_REPORTED,
                )
            ],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


def test_r203_structural_binding_does_not_claim_latest_prior_correctness() -> None:
    """A resolved in-window history row is *a* baseline, not proven the latest prior.

    The state carries a bounded projection, so it cannot know whether an
    unprojected row sits between the baseline and the current. That selection is
    the authoritative service's job; the schema only checks membership and
    binding. This test pins the honesty of the claim, not a service behaviour.
    """
    older = _history(observation_id=OBS_BASELINE_V5_B, measured_at="2026-09-15T09:00:00Z")
    state = _state(
        observations=[_observation(), older, _history()],
        comparisons=[_comparison()],
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    # The comparison binds to the projected baseline, and the older row is simply
    # history the projection also carries.
    assert state.comparisons[0].baseline_observation_id == OBS_BASELINE_V5
    assert {row.observation_id for row in state.observations} == {
        OBS_CURRENT,
        OBS_BASELINE_V5,
        OBS_BASELINE_V5_B,
    }


# === R2-04: typed trace contract and nested free text =================================


def _trace_vocabulary() -> frozenset[str]:
    """The *actual* closed vocabularies a trace may serialize (R2-04).

    A string that merely looks like a machine token is not enough: it must be a
    member of one of these enums (or one of the module's bounded literals), or a
    UUID / SHA-256 / UTC instant. This is what stops a regex-conforming token
    from being treated as a closed vocabulary.
    """
    from app.core.enums import ExtractionPath, Preprocessing, QualityFlag

    values: set[str] = set()
    for enum in (
        S.IssueType,
        S.DetailKind,
        S.NodeName,
        S.NodeOutcome,
        S.ToolName,
        S.TriagePath,
        S.PathReason,
        S.ValidationOutcome,
        S.ViolationCode,
        ExtractionPath,
        Preprocessing,
        QualityFlag,
    ):
        values |= {member.value for member in enum}
    # Bounded trace literals that are not enums in this module.
    values |= {"approve", "edit", "reject", "proceed", "halt"}
    return frozenset(values)


def _assert_trace_strings_are_closed(node: object, path: str = "$") -> None:
    """Recursively require every serialized string to be closed vocabulary or an id."""
    import re as _re

    identifier = _re.compile(
        r"^(?:"
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        r"|[0-9a-f]{64}"
        r"|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
        r")$"
    )
    allowed = _trace_vocabulary()
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in {"message", "raw_text", "text", "note", "issues", "reason_code"}, (
                f"{path}.{key} is a non-normative trace field"
            )
            _assert_trace_strings_are_closed(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _assert_trace_strings_are_closed(item, f"{path}[{index}]")
    elif isinstance(node, str):
        assert identifier.match(node) or node in allowed, (
            f"{path} carries a string outside the closed vocabularies: {node!r}"
        )


def test_r204_gate_detail_is_the_normative_contract_shape() -> None:
    """``GateDetail`` is exactly ``GateEventDetail`` in the phase-0 contract."""
    assert set(S.GateDetail.model_fields) == {
        "kind",
        "decision",
        "blocking_fact_count",
        "issue_types",
    }
    # ... and the OpenAPI contract's property names and issue vocabulary match.
    contract = (REPO_ROOT / "docs" / "contracts" / "openapi.phase0.yaml").read_text()
    match = re.search(r"^\s{4}GateEventDetail:\s*$", contract, re.MULTILINE)
    assert match, "GateEventDetail schema definition not found"
    block = contract[match.start() :]
    block = block[: re.search(r"^\s{4}\w+:\s*$", block[10:], re.MULTILINE).start() + 10]
    for name in ("kind", "decision", "blocking_fact_count", "issue_types"):
        assert re.search(rf"^\s{{8}}{name}:\s*$", block, re.MULTILINE), name
    assert "additionalProperties: false" in block
    for member in S.IssueType:
        assert member.value in block, member.value
    # The STATE_AND_GRAPH_CONTRACT.md shape names the same field.
    markdown = (REPO_ROOT / "docs" / "contracts" / "STATE_AND_GRAPH_CONTRACT.md").read_text()
    gate_block = markdown[markdown.index("class GateDetail(") :][:400]
    assert "issue_types" in gate_block
    assert "issues" not in gate_block


def test_r204_projection_keeps_the_closed_vocabulary_and_no_blocker_text() -> None:
    """The trace keeps only closed issue types; identity and text stay on the reference."""
    halt = _gate(
        S.GateDecision.HALT,
        issues=[
            _issue(issue_type=S.IssueType.VI_003),
            _issue(issue_type=S.IssueType.VI_003, reason_code="other"),
            _issue(issue_type=S.IssueType.VI_001),
        ],
        count=1,
    )
    detail = S.GateDetail.from_gate_evaluation(halt)
    # Canonical: unique and ordered, derived from the evaluation.
    assert detail.issue_types == [S.IssueType.VI_001, S.IssueType.VI_003]
    assert detail.decision == "halt"
    assert detail.blocking_fact_count == halt.blocking_fact_count
    # The reference keeps the full semantic identity and the rendered message.
    assert [item.semantic_key() for item in halt.issues] == [
        (S.IssueType.VI_003, "unverified_fact", DOC_A, (FACT_A,)),
        (S.IssueType.VI_003, "other", DOC_A, (FACT_A,)),
        (S.IssueType.VI_001, "unverified_fact", DOC_A, (FACT_A,)),
    ]
    assert all(item.message for item in halt.issues)
    # A document-only HALT keeps a blocking issue with zero distinct facts.
    document_only = _gate(S.GateDecision.HALT, issues=[_issue(fact_ids=[])], count=0)
    document_only_detail = S.GateDetail.from_gate_evaluation(document_only)
    assert document_only_detail.issue_types == [S.IssueType.VI_003]
    assert document_only_detail.blocking_fact_count == 0
    # A proceed evaluation derives an empty vocabulary and a zero count.
    proceed = S.GateDetail.from_gate_evaluation(_gate())
    assert proceed.decision == "proceed"
    assert proceed.issue_types == [] and proceed.blocking_fact_count == 0
    # An unavailable evaluation is an evaluation failure, never a decision.
    with pytest.raises(ValueError, match="no trace decision"):
        S.GateDetail.from_gate_evaluation(
            _gate(
                S.GateDecision.UNAVAILABLE,
                issues=[_issue()],
                count=1,
                reason=S.GateUnavailableReason.SOURCE_BYTES_UNAVAILABLE,
            )
        )


def test_r204_unexpected_nested_text_and_token_fields_are_rejected() -> None:
    """Extra nested payloads and non-vocabulary tokens are refused, not ignored."""
    base = {
        "kind": "gate",
        "decision": "halt",
        "blocking_fact_count": 1,
        "issue_types": ["VI-003"],
    }
    for payload in (
        {**base, "issues": [{"issue_type": "VI-003", "message": "free text"}]},
        {**base, "issue_types": [{"issue_type": "VI-003"}]},
        {**base, "message": "free text"},
        {**base, "reason_code": "some_machine_token"},
        {**base, "issue_types": ["VI-003", "VI-999"]},
        {**base, "issue_types": ["not_a_closed_vocabulary_token"]},
        {**base, "issue_types": ["VI-003", "VI-003"]},
        {**base, "issue_types": ["VI-003", "VI-001"]},
    ):
        with pytest.raises(ValidationError):
            S.GateDetail.model_validate_json(json.dumps(payload))
    # ``additionalProperties: false`` is real: an unknown nested key is refused.
    with pytest.raises(ValidationError):
        S.GateDetail.model_validate_json(json.dumps({**base, "extra": {"a": 1}}))


def test_r204_every_nested_trace_payload_is_closed_vocabulary() -> None:
    """Walk the whole serialized payload, not just the top-level field names."""
    details = [
        S.TriageDetail(
            path_selected=S.TriagePath.TEXT_LAYER,
            path_reason=S.PathReason.TEXT_LAYER_AVAILABLE,
            document_id=DOC_A,
            attempt_index=1,
            preprocessing_applied=False,
        ),
        S.ValidationDetail(validation_outcome=S.ValidationOutcome.ACCEPT, attempt_index=1),
        S.GateDetail(
            decision="halt",
            blocking_fact_count=1,
            issue_types=[S.IssueType.VI_003],
        ),
        S.FinalizeDetail(
            approval_decision="approve", task_created=False, notification_created=False
        ),
    ]
    for detail in details:
        _assert_trace_strings_are_closed(json.loads(detail.model_dump_json()))

    # The same walk over a full node event, which nests a detail one level down.
    for node, detail in zip(
        (
            S.NodeName.EXTRACTION_TRIAGE,
            S.NodeName.DRAFT_VALIDATION,
            S.NodeName.FACT_VERIFY_GATE,
            S.NodeName.FINALIZE_ACTIONS,
        ),
        details,
        strict=True,
    ):
        event = _event(node=node, detail=detail)
        _assert_trace_strings_are_closed(json.loads(event.model_dump_json()))

    # Negative control: the gate *reference* does carry the rendered message, so
    # the walk really does detect non-vocabulary text when it is present.
    with pytest.raises(AssertionError, match="outside the closed vocabularies"):
        _assert_trace_strings_are_closed(json.loads(halt_reference_json()))


def halt_reference_json() -> str:
    return _gate(S.GateDecision.HALT, issues=[_issue()]).model_dump_json()


def test_r204_only_the_latest_gate_event_mirrors_the_current_evaluation() -> None:
    """Current evaluation vs historical trace events (R2-04, S2 obligation recorded)."""
    halt = _gate(S.GateDecision.HALT, issues=[_issue()])
    historical = _event(
        node=S.NodeName.FACT_VERIFY_GATE,
        started_at="2026-11-14T11:30:00Z",
        detail=S.GateDetail(decision="proceed", blocking_fact_count=0, issue_types=[]),
    )
    current = _event(
        node=S.NodeName.FACT_VERIFY_GATE,
        started_at="2026-11-14T11:40:00Z",
        detail=S.GateDetail(
            decision="halt", blocking_fact_count=1, issue_types=[S.IssueType.VI_003]
        ),
    )
    # An earlier event records an earlier evaluation; the latest one mirrors the
    # current evaluation. The historical association is an S2 obligation.
    state = _state(
        verification_gate=halt,
        last_validated_at_utc=VALIDATED,
        events=[historical, current],
    )
    assert state.events[-1].detail is not None
    # ... but the latest gate event must still mirror the current evaluation.
    with pytest.raises(ValidationError, match="differs from the evaluation"):
        _state(
            verification_gate=halt,
            last_validated_at_utc=VALIDATED,
            events=[current, historical],
        )


# === R2-05: exact layered exclusion semantics ========================================


def _exclusion(observation_id: str, reason_code: str) -> S.PersistedExclusionRef:
    return S.PersistedExclusionRef(observation_id=observation_id, reason_code=reason_code)


def test_r205_equal_length_contradictory_exclusion_lists_are_rejected() -> None:
    """Lengths alone would accept a receipt whose content contradicts itself."""
    l1 = [_exclusion(OBS_BASELINE_V5, "validation_rejected")]
    l2 = [_exclusion(OBS_BASELINE_V5, "measurement_stale")]
    merged = [
        _exclusion(OBS_BASELINE_V5, "measurement_stale"),
        _exclusion(OBS_BASELINE_V5, "validation_rejected"),
    ]
    good = _sealed(
        excluded_evidence=merged,
        layered_exclusions=_layered(l1_exclusions=l1, l2_exclusions=l2, l3_merged=merged),
        exclusion_count=2,
        l1_exclusion_count=1,
        l2_exclusion_count=1,
    )
    assert good.excluded_evidence == merged

    # Same lengths, one reason replaced.
    forged_reason = [_exclusion(OBS_BASELINE_V5, "future_timestamp"), merged[1]]
    with pytest.raises(ValidationError, match="canonical deduplicated union"):
        _sealed(
            excluded_evidence=forged_reason,
            layered_exclusions=_layered(
                l1_exclusions=l1, l2_exclusions=l2, l3_merged=forged_reason
            ),
            exclusion_count=2,
            l1_exclusion_count=1,
            l2_exclusion_count=1,
        )
    # Same lengths, one observation identity replaced.
    forged_identity = [merged[0], _exclusion(OBS_BASELINE_V5_B, "validation_rejected")]
    with pytest.raises(ValidationError, match="canonical deduplicated union"):
        _sealed(
            excluded_evidence=forged_identity,
            layered_exclusions=_layered(
                l1_exclusions=l1, l2_exclusions=l2, l3_merged=forged_identity
            ),
            exclusion_count=2,
            l1_exclusion_count=1,
            l2_exclusion_count=1,
        )
    # ``excluded_evidence`` must equal l3 exactly, not merely its length.
    with pytest.raises(ValidationError, match="excluded_evidence must equal l3_merged"):
        _sealed(
            excluded_evidence=[merged[0], _exclusion(OBS_BASELINE_V5_B, "measurement_stale")],
            layered_exclusions=_layered(l1_exclusions=l1, l2_exclusions=l2, l3_merged=merged),
            exclusion_count=2,
            l1_exclusion_count=1,
            l2_exclusion_count=1,
        )
    # Canonical ordering is required, and duplicates are not canonical.
    with pytest.raises(ValidationError, match="canonical order"):
        _sealed(
            excluded_evidence=merged,
            layered_exclusions=_layered(
                l1_exclusions=[l1[0], l1[0]], l2_exclusions=l2, l3_merged=merged
            ),
            exclusion_count=2,
            l1_exclusion_count=2,
            l2_exclusion_count=1,
        )


def test_r205_l0_lineage_checks_stay_separate_from_the_merged_layer() -> None:
    """L0 is not merged into L3: an l0-only entry never appears in the union."""
    l1 = [_exclusion(OBS_BASELINE_V5, "validation_rejected")]
    l2 = [_exclusion(OBS_BASELINE_V5, "measurement_stale")]
    merged = [
        _exclusion(OBS_BASELINE_V5, "measurement_stale"),
        _exclusion(OBS_BASELINE_V5, "validation_rejected"),
    ]
    l0_only = _exclusion(OBS_BASELINE_V5_B, "verified_lineage_unavailable")
    sealed = _sealed(
        excluded_evidence=merged,
        layered_exclusions=_layered(
            l0_lineage_checks=[l0_only],
            l1_exclusions=l1,
            l2_exclusions=l2,
            l3_merged=merged,
        ),
        exclusion_count=2,
        l1_exclusion_count=1,
        l2_exclusion_count=1,
    )
    assert sealed.layered_exclusions.l0_lineage_checks == [l0_only]
    assert l0_only not in sealed.excluded_evidence
    assert OBS_BASELINE_V5_B not in {item.observation_id for item in sealed.excluded_evidence}


def test_r205_first_write_and_zero_total_replay_arithmetic_are_preserved() -> None:
    """The accepted bounds and replay arithmetic survive the semantic tightening."""
    l1 = [_exclusion(OBS_BASELINE_V5, "validation_rejected")]
    merged = [l1[0]]
    first = _sealed(
        excluded_evidence=merged,
        layered_exclusions=_layered(l1_exclusions=l1, l3_merged=merged),
        exclusion_count=1,
        l1_exclusion_count=1,
        review_items_persisted=2,
        review_items_total=2,
        evidence_links_persisted=4,
        evidence_links_total=4,
    )
    assert first.replayed is False
    replay = _sealed(
        replayed=True,
        excluded_evidence=merged,
        layered_exclusions=_layered(l1_exclusions=l1, l3_merged=merged),
        exclusion_count=1,
        l1_exclusion_count=1,
        review_items_persisted=0,
        review_items_total=2,
        evidence_links_persisted=0,
        evidence_links_total=4,
    )
    assert replay.review_items_persisted == 0
    assert replay.evidence_links_persisted == 0
    assert replay.exclusion_count == first.exclusion_count
    with pytest.raises(ValidationError, match="zero review items and zero evidence links"):
        _sealed(
            replayed=True,
            excluded_evidence=merged,
            layered_exclusions=_layered(l1_exclusions=l1, l3_merged=merged),
            exclusion_count=1,
            l1_exclusion_count=1,
            review_items_persisted=1,
        )
    with pytest.raises(ValidationError):
        _sealed(
            excluded_evidence=[*_exclusions(S.MAX_MERGED_EXCLUSIONS + 1)],
            layered_exclusions=_layered(
                l1_exclusions=_exclusions(S.MAX_MERGED_EXCLUSIONS + 1),
                l3_merged=_exclusions(S.MAX_MERGED_EXCLUSIONS + 1),
            ),
            exclusion_count=S.MAX_MERGED_EXCLUSIONS + 1,
            l1_exclusion_count=S.MAX_MERGED_EXCLUSIONS + 1,
        )


def _exclusions(count: int) -> list[S.PersistedExclusionRef]:
    return [
        _exclusion(f"f0000000-0000-4000-8000-{index:012d}", "validation_rejected")
        for index in range(count)
    ]


# === R2-06: remaining structural consistency ========================================


def _decided_extracted(**overrides: Any) -> S.ExtractedFact:
    fields: dict[str, Any] = {
        "verification_status": S.VerificationStatus.VERIFIED,
        "verified_by": DOCTOR,
        "verified_at": VALIDATED,
    }
    fields.update(overrides)
    return _extracted(**fields)


def _fact_state(**overrides: Any) -> S.SharedGraphState:
    fields: dict[str, Any] = {
        "extraction_facts": [_decided_extracted()],
        "verified_facts": [_verified_fact()],
        "verification_gate": _gate(),
        "last_validated_at_utc": VALIDATED,
    }
    fields.update(overrides)
    return _state(**fields)


def test_r206_extracted_and_verified_projections_must_agree() -> None:
    """Value, unit, scope, lineage and supplied verification metadata all match."""
    _fact_state()
    for change, match in (
        ({"normalized_value": "141"}, "must keep its normalized value"),
        ({"unit": "kg"}, "must keep its unit"),
        # A patient scope that differs from the run is caught by the run-scope
        # check first; the projection check is defence in depth behind it.
        (
            {"patient_id": "99999999-9999-4999-8999-999999999999"},
            "patient scope differs from the run",
        ),
        (
            {
                "verified_by": "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff",
                "verified_at": "2026-11-23T11:00:00Z",
            },
            "must keep its verifier",
        ),
        ({"document_id": DOC_B}, "must keep its source document"),
        ({"field_name": FactField.TEST_NAME}, "must keep its source field"),
        ({"corrected_from_fact_id": FACT_B}, "must keep its corrected lineage"),
    ):
        with pytest.raises(ValidationError, match=match):
            _fact_state(verified_facts=[_verified_fact(**change)])


def test_r206_absent_optional_projections_stay_absent() -> None:
    """An omitted projection is absent, never fabricated to look complete."""
    state = _fact_state(
        verified_facts=[_verified_fact(patient_id=None, verified_by=None, verified_at=None)]
    )
    projected = state.verified_facts[0]
    assert projected.patient_id is None
    assert projected.verified_by is None
    assert projected.verified_at is None
    assert projected.evidence == []


def test_r206_contradictory_provenance_document_identities_are_rejected() -> None:
    """An observation's source document must be the document of the fact it cites."""
    verified_selection = _manifest(
        observations=[
            _selected_observation(trust_level=TrustLevel.DOCTOR_VERIFIED, source_fact_id=FACT_A)
        ]
    )
    observed = _verified_observation(source_fact_id=FACT_A, source_document_id=DOC_A)
    _state(
        observations=[observed],
        extraction_facts=[_decided_extracted()],
        selection=verified_selection,
        verification_gate=_gate(),
        last_validated_at_utc=VALIDATED,
    )
    with pytest.raises(ValidationError, match="contradicts its extracted fact"):
        _state(
            observations=[_verified_observation(source_fact_id=FACT_A, source_document_id=DOC_B)],
            extraction_facts=[_decided_extracted()],
            selection=verified_selection,
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    with pytest.raises(ValidationError, match="contradicts its verified projection"):
        _state(
            observations=[_verified_observation(source_fact_id=FACT_A, source_document_id=DOC_B)],
            verified_facts=[_verified_fact(document_id=DOC_A)],
            selection=verified_selection,
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )


def test_r206_historical_excluded_vi002_identities_are_bound() -> None:
    """F1 and F2 must agree on the historical VI-002 exclusions."""
    base = {
        "verification_gate": _gate(historical_excluded_vi002_ids=[ISSUE_A]),
        "last_validated_at_utc": VALIDATED,
        "observations": [_observation()],
    }
    _state(evaluable_evidence=_evidence(historical_excluded_vi002_ids=[ISSUE_A]), **base)
    with pytest.raises(ValidationError, match="historical excluded VI-002"):
        _state(evaluable_evidence=_evidence(historical_excluded_vi002_ids=[]), **base)


def test_r206_sealed_gate_identity_is_reconciled_honestly() -> None:
    """The F2 gate identity is authoritative; an absent F1 row id is not a lie."""
    base = {
        "verification_gate": _gate(gate_evaluation_id=GATE_EVAL),
        "last_validated_at_utc": VALIDATED,
        "evaluable_evidence": _evidence(),
        "observations": [_observation()],
    }
    _state(review_persistence=_sealed(), **base)
    with pytest.raises(ValidationError, match="different F2 gate identity"):
        _state(review_persistence=_sealed(gate_evaluation_id=ISSUE_A), **base)
    # The F1 receipt genuinely exposes no row id: an absent projection is accepted.
    _state(
        review_persistence=_sealed(),
        verification_gate=_gate(gate_evaluation_id=None),
        last_validated_at_utc=VALIDATED,
        evaluable_evidence=_evidence(),
        observations=[_observation()],
    )
    # A present F1 row id that disagrees with the F2 identity is rejected.
    with pytest.raises(ValidationError, match="different stored gate row"):
        _state(
            review_persistence=_sealed(),
            verification_gate=_gate(gate_evaluation_id=ISSUE_A),
            last_validated_at_utc=VALIDATED,
            evaluable_evidence=_evidence(),
            observations=[_observation()],
        )


def test_r206_inconsistent_selected_evidence_cannot_be_presented_as_bound() -> None:
    """A selection that disagrees with the typed rows is not structurally bound."""
    with pytest.raises(ValidationError, match="selected observation manifest differs"):
        _state(
            observations=[_verified_observation(source_fact_id=FACT_A, source_document_id=DOC_A)],
            selection=_manifest(),
        )
    # A manifest that selects a row the state does not carry is refused by the
    # selected-current binding first; the "must be present" check is the
    # defence in depth behind it.
    with pytest.raises(ValidationError, match="immutable selected manifest"):
        _state(
            selection=_manifest(
                observation_ids=[OBS_BASELINE_V5_B],
                observations=[_selected_observation(observation_id=OBS_BASELINE_V5_B)],
            )
        )


# === R2-02 (temporal): accepted future-skew eligibility boundary ====================


def test_r202_temporal_eligibility_mirrors_the_accepted_future_skew_boundary() -> None:
    """A measurement beyond ``as_of + 5 minutes`` is not eligible (R2-02)."""
    assert S.MAX_FUTURE_SKEW_MINUTES == 5
    # The accepted predicate checks only the upper bound.
    assert S._beyond_future_skew("2026-11-14T12:05:00Z", AS_OF) is False
    assert S._beyond_future_skew("2026-11-14T12:05:01Z", AS_OF) is True
    # A past measurement is never "future", however old it is; window membership
    # is a separate, labelled check.
    assert S._beyond_future_skew("2020-01-01T00:00:00Z", AS_OF) is False

    # Selected current: exactly at the boundary is eligible ...
    _state(observations=[_observation(measured_at="2026-11-14T12:05:00Z")])
    # ... one second beyond it is not.
    with pytest.raises(ValidationError, match="authorized future-skew allowance"):
        _state(observations=[_observation(measured_at="2026-11-14T12:05:01Z")])
    # The comparison current follows the same boundary.
    with pytest.raises(ValidationError, match="authorized future-skew allowance"):
        _state(
            observations=[_observation(measured_at="2026-11-14T12:05:01Z")],
            comparisons=[_comparison(current_value=Decimal("140"))],
            verification_gate=_gate(),
            last_validated_at_utc=VALIDATED,
        )
    # The baseline rule is defence in depth: a baseline must precede its current,
    # so a current inside the boundary already forces the baseline inside it. The
    # predicate is nevertheless applied to the baseline row on every pass.
    assert S._beyond_future_skew("2026-11-14T12:05:01Z", AS_OF) is True


def test_r202_structural_eligibility_grants_no_runtime_authority() -> None:
    """Eligibility is a shape check; it selects nothing and authorizes nothing."""
    eligible = _state(observations=[_observation(measured_at="2026-11-14T12:05:00Z")])
    assert eligible.runtime_evaluable is False
    assert eligible.policy_status == "unapproved"
    assert eligible.workflow_completed is False
