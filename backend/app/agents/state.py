"""P5-S0 typed shared-state contract — structural models only (no graph).

This is the first *executable* definition of the Pydantic v2 shared state
proposed in ``docs/contracts/STATE_AND_GRAPH_CONTRACT.md`` §3, reconciled with
the merged F0 run foundation, the F1 run-bound gate receipt, the F2 evaluable
evidence bridge and the sealed RB3 review-persistence receipt. The
reconciliation matrix, the decisions taken and the open owner questions are in
``docs/phase-reports/P5_S0_TYPED_STATE_IMPLEMENTATION_REVIEW_20261123.md``.

What this module is
-------------------
* Strict, frozen, JSON-round-trippable Pydantic v2 models. Unknown fields are
  rejected; every collection and numeric is bounded; every identifier is a
  real canonical UUIDv4 / UUIDv5 / SHA-256 / UTC instant / version token; and
  cross-field invariants are checked by validators, never repaired.
* Pure data. No I/O, no clock reads, no database, no HTTP, no model runtime.
  The only project imports are the shared vocabulary enums in
  ``app.core.enums`` and the RB3 denial-reason enum in
  ``app.schemas.p4_rb3_review_persistence`` (both pure constant modules).

What this module is NOT
----------------------
* Not a graph, checkpointer, node, tool adapter, model client, API, task or
  notification implementation. None of those modules are imported here.
* Not an authority. Passing validation proves *shape*, never authentication,
  authorization, clinical grounding, execution permission or policy approval.
  The honesty literals (``runtime_evaluable=False``, ``policy_status=
  "unapproved"``, …) cannot be flipped through validation, but
  ``model_copy(update=...)`` bypasses validation by design: consumers must
  build state through validation and re-check authorization out of band.
* Frozen models and private constructors are *data-integrity* aids, not a
  security boundary.

ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    TypeAdapter,
    WithJsonSchema,
    model_validator,
)

from app.core.enums import (
    MEASURE_UNITS,
    ExtractionPath,
    FactField,
    MeasureType,
    ObservationSource,
    Preprocessing,
    QualityFlag,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.schemas.p4_rb3_review_persistence import RB3DenialReason

# --- contract versions pinned by this module (drift-checked against F0) ---------------

#: Version of *this* state contract (``STATE_AND_GRAPH_CONTRACT.md`` §2).
STATE_SCHEMA_VERSION = "1.0.0"
#: Graph shape + node semantics the state is written for (§2).
WORKFLOW_VERSION = "1.0.0"
#: Demo rule-policy reference (not an activation claim).
POLICY_REFERENCE_VERSION = "demo-policy-1.1.0"
#: Fixed educational label every draft must carry (``REQ-SEC-05``).
DEMO_NOTICE = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"

# --- primitive types: real validation, not permissive regex --------------------------

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _canonical_uuid(value: str, *, version: int) -> str:
    """Accept only the canonical lowercase hyphenated RFC-4122 form of a UUID."""
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("not a UUID") from exc
    if str(parsed) != value or parsed.variant != uuid.RFC_4122 or parsed.version != version:
        raise ValueError(f"expected a canonical lowercase RFC-4122 UUIDv{version}")
    return value


def _uuid4(value: str) -> str:
    return _canonical_uuid(value, version=4)


def _uuid5(value: str) -> str:
    return _canonical_uuid(value, version=5)


def _sha256_text(value: str) -> str:
    if value == "0" * 64:
        raise ValueError("an all-zero digest is a placeholder, not a digest")
    return value


def _utc_instant(value: str) -> str:
    """Accept only ``YYYY-MM-DDTHH:MM:SSZ`` (the persisted P2/F0 storage format)."""
    try:
        parsed = datetime.strptime(value, _UTC_FORMAT)
    except ValueError as exc:
        raise ValueError("expected an ISO-8601 UTC instant 'YYYY-MM-DDTHH:MM:SSZ'") from exc
    if parsed.strftime(_UTC_FORMAT) != value:
        raise ValueError("non-canonical UTC instant (zero padding required)")
    return value


def _calendar_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("expected a real calendar date 'YYYY-MM-DD'") from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("non-canonical calendar date")
    return value


def _decimal_text(value: Decimal) -> str:
    """Canonical JSON text for a decimal: no exponent form, no trailing zeros."""
    return format(value.normalize(), "f")


#: Server-generated identity (run, patient, doctor, document, observation, fact …).
Uuid = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(_uuid4)]
#: Derived identity (``uuid5(namespace, action_key)``), never generated randomly.
UuidV5 = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(_uuid5)]
#: Lowercase hex SHA-256 digest; the all-zero placeholder is rejected.
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$"), AfterValidator(_sha256_text)]
#: Persisted UTC instant, exactly ``YYYY-MM-DDTHH:MM:SSZ`` (``DATA_DICTIONARY`` §1).
Iso = Annotated[str, Field(min_length=20, max_length=20), AfterValidator(_utc_instant)]
#: SemVer 2.0.0 numeric identifiers (no leading zeros), bounded to the persisted width.
SemVer = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", max_length=12)]
#: Closed fact→observation mapping table version (``map-<major>.<minor>.<patch>``, P0-R12).
MappingVersion = Annotated[
    str, Field(pattern=r"^map-(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", max_length=16)
]
#: Demo policy reference ``<name>-<semver>`` (e.g. ``demo-policy-1.1.0``); a version, not activation.
PolicyVersion = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*-(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$",
        max_length=24,
    ),
]
#: Prompt/template tag (e.g. ``draft-v1``): a bounded token, no format is invented.
PromptVersion = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")]
#: Snake_case machine reason code (F1/F2 exclusion and reason vocabularies).
ReasonCode = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
#: Typed error code ``E_<UPPER_SNAKE>`` (``app.core.errors.ErrorCode`` vocabulary shape).
ErrorCode = Annotated[str, Field(pattern=r"^E_[A-Z0-9_]{2,45}$", max_length=48)]
#: Bounded lowercase machine token (checkpoint ids, model metadata keys).
Token = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")]

#: Exact positive quantity (observation values): ``Decimal`` only, never a float.
ExactDecimal = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=4),
    PlainSerializer(_decimal_text, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string"}),
]
#: Exact signed difference; may be negative, never non-finite.
DeltaDecimal = Annotated[
    Decimal,
    Field(max_digits=10, decimal_places=4),
    PlainSerializer(_decimal_text, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string"}),
]
#: Model-metadata value (provider/model/latency summary text only; bounded).
MetadataValue = Annotated[str, Field(min_length=1, max_length=128)]
#: Engine-reported probability in ``[0, 1]``; ``NaN``/``inf`` are rejected.
Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


# --- vocabularies ----------------------------------------------------------------------


class RunStatus(StrEnum):
    """``workflow_run.status`` — the app DB is the only authority (``P0-R09``)."""

    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_VERIFICATION = "needs_verification"  # halted, resumable
    AWAITING_DECISION = "awaiting_decision"  # interrupted, resumable
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"  # halted, resumable
    FAILED_TERMINAL = "failed_terminal"


#: Statuses that carry a ``halt_reason`` (contract §4.2, §6).
HALTED_STATUSES = frozenset(
    {RunStatus.NEEDS_VERIFICATION, RunStatus.FAILED_RETRYABLE, RunStatus.FAILED_TERMINAL}
)


class HaltReason(StrEnum):
    UNVERIFIED_FACTS = "unverified_facts"
    MODEL_FAILED = "model_failed"
    RETRY_EXHAUSTED = "retry_exhausted"
    NEEDS_HUMAN_DECISION = "needs_human_decision"


class TrustBasis(StrEnum):
    SELF_REPORTED = "self_reported"
    DOCTOR_VERIFIED = "doctor_verified"
    MIXED = "mixed"


class IncomparableReason(StrEnum):
    """Union of the contract §3 reasons and the P4/F2 codes (never silently dropped)."""

    NO_BASELINE = "no_baseline"
    UNIT_MISMATCH = "unit_mismatch"
    STALE_BASELINE = "stale_baseline"
    MISSING_TIMESTAMP = "missing_timestamp"
    NOT_ADMISSIBLE = "not_admissible"


class ExclusionReason(StrEnum):
    """Closed set actually emitted by the F2 bridge (source checks + admissibility)."""

    VALIDATION_REJECTED = "validation_rejected"
    UNIT_MISMATCH = "unit_mismatch"
    MISSING_TIMESTAMP = "missing_timestamp"
    FUTURE_TIMESTAMP = "future_timestamp"
    VERIFIED_LINEAGE_UNAVAILABLE = "verified_lineage_unavailable"
    VERIFIED_MAPPING_UNPROVEN = "verified_mapping_unproven"
    STORED_TRUST_SOURCE_MISMATCH = "stored_trust_source_mismatch"
    MALFORMED_HISTORY = "malformed_history"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProvenanceKind(StrEnum):
    DOCUMENT_SPAN = "document_span"
    OBSERVATION = "observation"
    CHECKIN_NOTE = "checkin_note"


class Extractor(StrEnum):
    PYPDF = "pypdf"
    TESSERACT = "tesseract"
    MANUAL = "manual"
    PATIENT_FORM = "patient_form"


class IssueType(StrEnum):
    """Pre-verification blockers only (``VI-001``…``VI-006``)."""

    VI_001 = "VI-001"
    VI_002 = "VI-002"
    VI_003 = "VI-003"
    VI_004 = "VI-004"
    VI_005 = "VI-005"
    VI_006 = "VI-006"


class ReviewRuleId(StrEnum):
    """Post-verification demo review prompts; retired ``DR-002/004/007/010`` are absent (P0-R03)."""

    DR_001 = "DR-001"
    DR_003 = "DR-003"
    DR_005 = "DR-005"
    DR_006 = "DR-006"
    DR_008 = "DR-008"
    DR_009 = "DR-009"


class ReviewHint(StrEnum):
    DATA_QUALITY = "data_quality"
    VERIFICATION_NEEDED = "verification_needed"
    CHANGE_TO_REVIEW = "change_to_review"


class ReviewItemState(StrEnum):
    OPEN = "open"
    DECIDED = "decided"


class DraftProvider(StrEnum):
    OLLAMA = "ollama"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class DraftExecutionStatus(StrEnum):
    MODEL_OK = "model_ok"
    MODEL_INVALID_SCHEMA = "model_invalid_schema"
    MODEL_TIMEOUT = "model_timeout"
    MODEL_UNAVAILABLE = "model_unavailable"
    FALLBACK_NO_MODEL = "fallback_no_model"


class ApprovalChoice(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class NodeName(StrEnum):
    """The eleven graph nodes of contract §4.1 (``node_event.node`` vocabulary)."""

    INTAKE_VALIDATE = "intake_validate"
    DOCUMENT_EXTRACT = "document_extract"
    EXTRACTION_TRIAGE = "extraction_triage"
    FACT_VERIFY_GATE = "fact_verify_gate"
    MONITOR_COMPARE = "monitor_compare"
    REVIEW_RULES = "review_rules"
    DRAFT_SUMMARY = "draft_summary"
    DRAFT_VALIDATION = "draft_validation"
    CLINICIAN_APPROVAL = "clinician_approval"
    FINALIZE_ACTIONS = "finalize_actions"
    HALTED = "halted"


class NodeOutcome(StrEnum):
    OK = "ok"
    HALTED = "halted"
    INTERRUPTED = "interrupted"
    RETRIED = "retried"
    FAILED = "failed"


class ToolName(StrEnum):
    """Closed tool allowlist of contract §4.1."""

    EXTRACT_DOCUMENT = "extract_document"
    GET_DOCUMENT_PAGES = "get_document_pages"
    VALIDATE_STRUCTURED_FIELDS = "validate_structured_fields"
    READ_OBSERVATIONS = "read_observations"
    COMPARE_OBSERVATIONS = "compare_observations"
    READ_VERIFIED_FACTS = "read_verified_facts"
    EVALUATE_DEMO_REVIEW_RULES = "evaluate_demo_review_rules"
    DRAFT_GROUNDED_SUMMARY = "draft_grounded_summary"
    CREATE_IN_APP_TASK = "create_in_app_task"
    LIST_DUE_TASKS = "list_due_tasks"


#: Per-node tool allowlist (contract §4.1 "Tools (allowlist)" column, verbatim).
NODE_TOOLS: dict[NodeName, frozenset[ToolName]] = {
    NodeName.INTAKE_VALIDATE: frozenset(),
    NodeName.DOCUMENT_EXTRACT: frozenset(
        {
            ToolName.EXTRACT_DOCUMENT,
            ToolName.GET_DOCUMENT_PAGES,
            ToolName.VALIDATE_STRUCTURED_FIELDS,
        }
    ),
    NodeName.EXTRACTION_TRIAGE: frozenset(),
    NodeName.FACT_VERIFY_GATE: frozenset(),
    NodeName.MONITOR_COMPARE: frozenset(
        {ToolName.READ_OBSERVATIONS, ToolName.COMPARE_OBSERVATIONS}
    ),
    NodeName.REVIEW_RULES: frozenset(
        {ToolName.READ_VERIFIED_FACTS, ToolName.EVALUATE_DEMO_REVIEW_RULES}
    ),
    NodeName.DRAFT_SUMMARY: frozenset(
        {ToolName.READ_VERIFIED_FACTS, ToolName.DRAFT_GROUNDED_SUMMARY}
    ),
    NodeName.DRAFT_VALIDATION: frozenset(),
    NodeName.CLINICIAN_APPROVAL: frozenset(),
    NodeName.FINALIZE_ACTIONS: frozenset({ToolName.CREATE_IN_APP_TASK, ToolName.LIST_DUE_TASKS}),
    NodeName.HALTED: frozenset(),
}


class TriagePath(StrEnum):
    """Trace path vocabulary (contract §3/§4.2, OpenAPI ``TriageEventDetail``).

    Distinct from ``app.core.enums.TriagePath`` (the P3 *service* route), whose
    ``proceed`` maps onto ``text_layer`` or ``ocr_direct`` here (§4.2).
    """

    TEXT_LAYER = "text_layer"
    OCR_DIRECT = "ocr_direct"
    OCR_PREPROCESS_RETRY = "ocr_preprocess_retry"
    FLAG_FOR_HUMAN = "flag_for_human"


class PathReason(StrEnum):
    TEXT_LAYER_AVAILABLE = "text_layer_available"
    CONFIDENCE_OK = "confidence_ok"
    LOW_CONFIDENCE = "low_confidence"
    OCR_TRANSIENT_ERROR = "ocr_transient_error"
    RETRY_EXHAUSTED = "retry_exhausted"


class ValidationOutcome(StrEnum):
    ACCEPT = "accept"
    REPAIR_REQUESTED = "repair_requested"
    FALLBACK_SELECTED = "fallback_selected"


class ViolationCode(StrEnum):
    SCHEMA_INVALID = "schema_invalid"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    PROHIBITED_CONTENT = "prohibited_content"
    MISSING_DISCLAIMER = "missing_disclaimer"
    UNGROUNDED_NUMBER = "ungrounded_number"
    PATIENT_ADDRESSING = "patient_addressing"


TraceGateDecision = Literal["proceed", "halt"]


class DetailKind(StrEnum):
    TRIAGE = "triage"
    VALIDATION = "validation"
    GATE = "gate"
    FINALIZE = "finalize"


#: Nodes that make a bounded decision → ``detail`` is mandatory and must match (P0-R08).
DETAIL_KIND_BY_NODE: dict[NodeName, DetailKind] = {
    NodeName.EXTRACTION_TRIAGE: DetailKind.TRIAGE,
    NodeName.FACT_VERIFY_GATE: DetailKind.GATE,
    NodeName.DRAFT_VALIDATION: DetailKind.VALIDATION,
    NodeName.FINALIZE_ACTIONS: DetailKind.FINALIZE,
}


class GateDecision(StrEnum):
    """F1 receipt decision set (``p5_run_gate.RunGateReceipt.decision``)."""

    PROCEED = "proceed"
    HALT = "halt"
    UNAVAILABLE = "unavailable"


class GateUnavailableReason(StrEnum):
    """Closed set emitted by ``p5_run_gate._evaluate_locked`` (``unavailable = "…"``)."""

    RUN_EXECUTION_STATE_UNEXPECTED = "run_execution_state_unexpected"
    UNSUPPORTED_RUN_VERSION = "unsupported_run_version"
    INVALID_RUN_CLOCK = "invalid_run_clock"
    SOURCE_BYTES_UNAVAILABLE = "source_bytes_unavailable"
    SOURCE_BYTES_CHANGED_DURING_GATE = "source_bytes_changed_during_gate"
    SELECTED_DOCUMENT_CHANGED = "selected_document_changed"
    SELECTED_DOCUMENT_NOT_VERIFIED = "selected_document_not_verified"
    SELECTED_DOCUMENT_PREFLIGHT_UNPROVEN = "selected_document_preflight_unproven"
    SELECTED_DOCUMENT_HAS_NO_ACTIVE_FACTS = "selected_document_has_no_active_facts"
    SELECTED_OBSERVATION_MISSING = "selected_observation_missing"
    SELECTED_OBSERVATION_INADMISSIBLE = "selected_observation_inadmissible"
    SELECTED_RECOVERY_LINEAGE_CHANGED = "selected_recovery_lineage_changed"
    FACT_PATIENT_SCOPE_CHANGED = "fact_patient_scope_changed"
    HISTORICAL_OMISSION_CHANGED = "historical_omission_changed"
    INVALID_QUALITY_FLAGS = "invalid_quality_flags"
    TOO_MANY_BLOCKING_FACTS = "too_many_blocking_facts"
    TOO_MANY_PATIENT_OBSERVATIONS = "too_many_patient_observations"
    TOO_MANY_SELECTED_FACTS = "too_many_selected_facts"
    UNRESOLVED_P3_VI002 = "unresolved_p3_vi002"
    UNSUPPORTED_OPEN_ISSUE_TYPE = "unsupported_open_issue_type"


#: F2 bridge history policy actually implemented (``p5_evidence_bridge`` constants).
F2_CONTRACT_VERSION = Literal["2.0.0"]
F2_HISTORY_POLICY = Literal["f2-history-365d-v1"]
#: RB3 receipt contract actually implemented (``p4_rb3_review_persistence`` constants).
RB3_RECEIPT_CONTRACT_VERSION = Literal["p4-rb3-receipt-1.0.0"]
RB3_FINGERPRINT_VERSION = Literal["rb3-full-input-1.0.0"]
#: Doctor-authored omission reason fixed by the F0 schema (``RunSourceOmission`` CHECK).
OMISSION_REASON = Literal["selected_separate_recovery_source"]

MAX_BLOCKING_FACTS = 40


class Strict(BaseModel):
    """Shared configuration: unknown fields rejected, strict input, frozen instances.

    ``frozen=True`` prevents field rebinding; list contents are not deeply
    immutable, so nodes must build new lists instead of mutating in place.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def _unique(values: list[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")


def _sorted_unique(values: list[str], label: str) -> None:
    _unique(values, label)
    if values != sorted(values):
        raise ValueError(f"{label} must be in ascending canonical order")


# --- evidence --------------------------------------------------------------------------


class ProvenanceRef(Strict):
    kind: ProvenanceKind
    document_id: Uuid | None = None
    page_index: int | None = Field(default=None, ge=0, le=200)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    observation_id: Uuid | None = None
    raw_text: str | None = Field(default=None, max_length=500)
    extractor: Extractor | None = None

    @model_validator(mode="after")
    def _kind_shape(self) -> Self:
        if self.kind is ProvenanceKind.DOCUMENT_SPAN:
            if self.document_id is None or self.observation_id is not None:
                raise ValueError("document_span requires document_id and forbids observation_id")
        elif self.observation_id is None or self.document_id is not None:
            raise ValueError(f"{self.kind} requires observation_id and forbids document_id")
        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end <= self.char_start
        ):
            raise ValueError("char_end must be greater than char_start")
        return self


class ExtractedFact(Strict):
    """Raw extraction output. Never admissible downstream (``REQ-SEC-04``)."""

    fact_id: Uuid
    patient_id: Uuid
    document_id: Uuid
    field_name: FactField
    raw_text: str = Field(max_length=300)
    normalized_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    quality_flags: list[QualityFlag] = Field(default_factory=list, max_length=7)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    provenance: ProvenanceRef
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    verification_note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _decision_shape(self) -> Self:
        decided = self.verified_by is not None and self.verified_at is not None
        if self.verification_status is VerificationStatus.PENDING and decided:
            raise ValueError("a pending fact cannot carry a doctor decision")
        if self.verification_status is not VerificationStatus.PENDING and not decided:
            raise ValueError("a decided fact requires verified_by and verified_at")
        return self


class VerifiedFact(Strict):
    """Doctor-verified (or doctor-corrected) fact — the only fact type admissible downstream."""

    fact_id: Uuid
    patient_id: Uuid
    document_id: Uuid
    field_name: FactField
    normalized_value: str = Field(min_length=1, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    corrected_from_fact_id: Uuid | None = None
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=4)
    verified_by: Uuid
    verified_at: Iso
    verification_status: Literal["verified"] = "verified"
    trust_basis: Literal["doctor_verified"] = "doctor_verified"

    @model_validator(mode="after")
    def _lineage(self) -> Self:
        if self.corrected_from_fact_id is not None and self.corrected_from_fact_id == self.fact_id:
            raise ValueError("a fact cannot be corrected from itself")
        return self


class ObservationView(Strict):
    """Patient-scoped measurement with explicit trust and recorded provenance.

    Reconciles the P0 ``ObservationView`` with the F2 ``ObservationV2``: the
    value is an exact ``Decimal`` and the recorded ``source_fact_id`` /
    ``source_document_id`` lineage travels with the row (``REQ-DATA-04``).
    """

    observation_id: Uuid
    patient_id: Uuid
    measure_type: MeasureType
    value: ExactDecimal
    unit: Unit
    measured_at: Iso
    source: ObservationSource
    validation: ValidationState
    trust_level: TrustLevel
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    source_fact_id: Uuid | None = None
    source_document_id: Uuid | None = None

    @model_validator(mode="after")
    def _trust_and_provenance(self) -> Self:
        if self.unit not in MEASURE_UNITS[self.measure_type]:
            raise ValueError("unit does not match the measure type's closed unit")
        doctor_verified = self.trust_level is TrustLevel.DOCTOR_VERIFIED
        if doctor_verified != (self.verified_by is not None and self.verified_at is not None):
            raise ValueError(
                "doctor_verified requires verified_by and verified_at; otherwise neither"
            )
        from_document = self.source is ObservationSource.VERIFIED_DOCUMENT
        if from_document != doctor_verified:
            raise ValueError("only a verified_document observation can be doctor_verified")
        has_fact = self.source_fact_id is not None
        has_document = self.source_document_id is not None
        if has_fact != has_document:
            raise ValueError("source_fact_id and source_document_id are recorded together")
        if has_fact != from_document:
            raise ValueError("source lineage is recorded iff source is verified_document")
        return self


class ComparisonResult(Strict):
    """Deterministic comparison of one current observation with its latest prior."""

    measure_type: MeasureType
    unit: Unit
    current_observation_id: Uuid
    baseline_observation_id: Uuid | None = None
    current_value: ExactDecimal
    baseline_value: ExactDecimal | None = None
    delta: DeltaDecimal | None = None
    comparable: bool
    incomparable_reason: IncomparableReason | None = None
    trust_basis: TrustBasis
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.unit not in MEASURE_UNITS[self.measure_type]:
            raise ValueError("unit does not match the measure type's closed unit")
        if self.comparable:
            if (
                self.baseline_observation_id is None
                or self.baseline_value is None
                or self.delta is None
                or self.incomparable_reason is not None
            ):
                raise ValueError("a comparable result needs baseline id/value and delta, no reason")
            if self.delta != self.current_value - self.baseline_value:
                raise ValueError("delta must equal current_value - baseline_value exactly")
        elif self.incomparable_reason is None or self.delta is not None:
            raise ValueError("an incomparable result needs a reason and no delta")
        if self.baseline_observation_id == self.current_observation_id:
            raise ValueError("an observation cannot be its own baseline")
        return self


class EvidenceExclusion(Strict):
    observation_id: Uuid
    reason_code: ExclusionReason


class VerificationIssue(Strict):
    """Pre-verification blocker (``VI-*``), always blocking, never a review prompt."""

    issue_id: Uuid
    issue_type: IssueType
    reason_code: ReasonCode
    blocking: Literal[True] = True
    message: str = Field(max_length=240)
    document_id: Uuid | None = None
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    created_at: Iso

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        return self


class ReviewFlag(Strict):
    """Post-verification deterministic demo review prompt (``DR-*``)."""

    review_item_id: Uuid
    rule_id: ReviewRuleId
    reason_code: ReasonCode
    workflow_hint: ReviewHint | None = None
    message: str = Field(max_length=240)
    trust_basis: TrustBasis
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    policy_version: PolicyVersion
    demo_only: Literal[True] = True
    dedupe_key: Sha256
    state: ReviewItemState = ReviewItemState.OPEN

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        _unique(self.observation_ids, "observation_ids")
        return self


# --- draft / approval / task shapes (structure only) -----------------------------------


class ClaimCitation(Strict):
    text: str = Field(min_length=1, max_length=400)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=6)


class DraftSummary(Strict):
    """Draft prose shape. Its presence never implies clinician approval."""

    draft_id: Uuid
    provider: DraftProvider
    model: str | None = Field(default=None, min_length=1, max_length=64)
    execution_status: DraftExecutionStatus
    prompt_version: PromptVersion
    latency_ms: int | None = Field(default=None, ge=0)
    claims: list[ClaimCitation] = Field(default_factory=list, max_length=20)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    not_asserted: list[str] = Field(default_factory=list, max_length=10)
    disclaimer: Literal["EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"] = DEMO_NOTICE
    created_at: Iso

    @model_validator(mode="after")
    def _provider_shape(self) -> Self:
        if any(len(item) > 240 for item in (*self.uncertainties, *self.not_asserted)):
            raise ValueError("uncertainty / not_asserted entries are bounded to 240 characters")
        if self.provider is DraftProvider.OLLAMA:
            if self.model is None or self.execution_status is not DraftExecutionStatus.MODEL_OK:
                raise ValueError("an ollama draft records a model and execution_status=model_ok")
        elif self.model is not None or self.execution_status is DraftExecutionStatus.MODEL_OK:
            raise ValueError("a fallback draft has no model and is never model_ok")
        return self


class ApprovalDecision(Strict):
    """Doctor decision shape. Validating it is not authentication (contract §5.2)."""

    decision_id: Uuid | None = None
    decision: ApprovalChoice | None = None
    edited_summary: str | None = Field(default=None, min_length=1, max_length=4000)
    reason: str | None = Field(default=None, max_length=500)
    doctor_id: Uuid | None = None
    decided_at: Iso | None = None

    @property
    def recorded(self) -> bool:
        return self.decision is not None

    @model_validator(mode="after")
    def _decision_shape(self) -> Self:
        present = (
            self.decision_id is not None,
            self.decision is not None,
            self.doctor_id is not None,
            self.decided_at is not None,
        )
        if any(present) and not all(present):
            raise ValueError(
                "decision_id, decision, doctor_id and decided_at are recorded together"
            )
        if self.decision is ApprovalChoice.EDIT and self.edited_summary is None:
            raise ValueError("an edit decision carries the edited summary")
        if self.decision is not ApprovalChoice.EDIT and self.edited_summary is not None:
            raise ValueError("edited_summary is only allowed with an edit decision")
        return self


class TaskDraft(Strict):
    """Follow-up task *draft*. ``task_id`` is derived (UUIDv5), never random (P0-R04).

    The exact ``uuid5(TASK_NAMESPACE, action_key)`` check is **not** enforced here:
    the namespace has no pinned value in any contract (S0 open decision D-05).
    """

    action_key: Sha256
    task_id: UuidV5
    title: str = Field(min_length=1, max_length=160)
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: str | None = Field(default=None, max_length=500)
    notification_text: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def _due_date(self) -> Self:
        if self.due_date is not None:
            _calendar_date(self.due_date)
        return self


class AgentError(Strict):
    code: ErrorCode
    node: NodeName
    message: str = Field(max_length=300)
    retryable: bool
    attempt: int = Field(ge=1, le=5)
    occurred_at: Iso


# --- typed node trace (REQ-AUDIT-01, P0-R08) -------------------------------------------


class ExtractionAttempt(Strict):
    """Typed per-attempt extraction metadata — the only triage input besides facts."""

    attempt_id: Uuid
    document_id: Uuid
    path: ExtractionPath
    preprocessing: Preprocessing
    page_from: int = Field(ge=0, le=200)
    page_to: int = Field(ge=0, le=200)
    engine_confidence: Confidence | None = None
    text_char_count: int = Field(ge=0, le=200000)
    succeeded: bool
    error_code: str | None = Field(default=None, max_length=48)
    duration_ms: int = Field(ge=0)
    tool_version: str | None = Field(default=None, max_length=64)
    created_at: Iso

    @model_validator(mode="after")
    def _pages(self) -> Self:
        if self.page_to < self.page_from:
            raise ValueError("page_to must not precede page_from")
        return self


class TriageDetail(Strict):
    kind: Literal["triage"] = "triage"
    path_selected: TriagePath
    path_reason: PathReason
    document_id: Uuid
    attempt_index: int = Field(ge=1, le=2)
    engine_confidence: Confidence | None = None
    preprocessing_applied: bool


class ValidationDetail(Strict):
    kind: Literal["validation"] = "validation"
    validation_outcome: ValidationOutcome
    attempt_index: int = Field(ge=1, le=2)
    violation_codes: list[ViolationCode] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.violation_codes, "violation_codes")
        return self


class GateDetail(Strict):
    """Bounded gate decision recorded in the trace.

    ``decision`` is deliberately the two-valued persisted/OpenAPI vocabulary
    (``node_event.gate_decision CHECK IN ('proceed','halt')``). The F1
    ``unavailable`` outcome is an *evaluation* outcome, carried by
    ``GateEvaluationRef`` — not a bounded node decision.
    """

    kind: Literal["gate"] = "gate"
    decision: TraceGateDecision
    blocking_fact_count: int = Field(ge=0, le=MAX_BLOCKING_FACTS)
    issue_types: list[IssueType] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _unique(self.issue_types, "issue_types")
        if (self.decision == "proceed") != (self.blocking_fact_count == 0):
            raise ValueError("proceed requires zero blocking facts; halt requires at least one")
        return self


class FinalizeDetail(Strict):
    kind: Literal["finalize"] = "finalize"
    approval_decision: Literal["approve", "edit"]
    task_created: bool
    notification_created: bool

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.notification_created and not self.task_created:
            raise ValueError("a notification is only created together with its task")
        return self


EventDetail = Annotated[
    TriageDetail | ValidationDetail | GateDetail | FinalizeDetail, Field(discriminator="kind")
]


class NodeEvent(Strict):
    """One graph-node execution record: enums, IDs, counts and probabilities only."""

    node: NodeName
    attempt: int = Field(default=1, ge=1, le=5)
    started_at: Iso
    ended_at: Iso | None = None
    outcome: NodeOutcome | None = None
    tools_called: list[ToolName] = Field(default_factory=list, max_length=6)
    detail: EventDetail | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at precedes started_at")
        _unique(self.tools_called, "tools_called")
        allowed = NODE_TOOLS[self.node]
        if not set(self.tools_called) <= allowed:
            raise ValueError(f"tools_called exceeds the {self.node} allowlist")
        expected = DETAIL_KIND_BY_NODE.get(self.node)
        if expected is None:
            if self.detail is not None:
                raise ValueError(f"{self.node} makes no bounded decision; detail must be null")
        elif self.detail is None or self.detail.kind != expected:
            raise ValueError(f"{self.node} must carry exactly one {expected} detail")
        return self


# --- run identity and immutable selection ---------------------------------------------


class RunIdentity(Strict):
    """Immutable identity block of one run (contract §2): ``thread_id == run_id``.

    ``as_of_utc`` is the *pinned evaluation clock* used by every time-dependent
    rule (``REQ-OPS-04``). It is not the authorization/validation clock.
    """

    run_id: Uuid
    thread_id: Uuid
    patient_id: Uuid
    doctor_id: Uuid
    encounter_id: Uuid | None = None
    workflow_version: SemVer
    state_schema_version: SemVer
    policy_version: PolicyVersion
    prompt_version: PromptVersion
    mapping_version: MappingVersion
    as_of_utc: Iso
    idempotency_key: Sha256
    started_at: Iso

    @model_validator(mode="after")
    def _thread(self) -> Self:
        if self.thread_id != self.run_id:
            raise ValueError("thread_id must equal run_id (one thread per run)")
        return self

    def supported_versions(self) -> bool:
        """Pure predicate: do the run's versions match *this* contract module?"""
        return (
            self.workflow_version == WORKFLOW_VERSION
            and self.state_schema_version == STATE_SCHEMA_VERSION
        )

    def assert_unchanged(self, previous: RunIdentity) -> None:
        """Raise if any immutable identity field differs from ``previous`` (§2, §5.3)."""
        if self != previous:
            changed = sorted(
                name
                for name in type(self).model_fields
                if getattr(self, name) != getattr(previous, name)
            )
            raise ValueError(f"run identity changed: {', '.join(changed)}")


class SelectedDocumentRef(Strict):
    document_id: Uuid
    source_sha256: Sha256
    source_status: str = Field(pattern=r"^[a-z_]{1,24}$")


class SelectedObservationRef(Strict):
    """Manifest identity of a selected observation (``RunSelectedObservation``)."""

    observation_id: Uuid
    trust_level: TrustLevel
    source_fact_id: Uuid | None = None
    observation_created_at: Iso

    @model_validator(mode="after")
    def _trust(self) -> Self:
        if (self.trust_level is TrustLevel.DOCTOR_VERIFIED) != (self.source_fact_id is not None):
            raise ValueError("doctor_verified selection requires source_fact_id; otherwise none")
        return self


class SelectedOmissionRef(Strict):
    """Doctor-authored, audited omission of an excluded recovery ancestor (F0)."""

    document_id: Uuid
    vi002_issue_id: Uuid
    reason_code: OMISSION_REASON
    doctor_id: Uuid
    source_sha256: Sha256


#: Member adapters used by ``SelectedSourceManifest.build`` (validated before digesting).
_MANIFEST_MEMBER_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "document_ids": TypeAdapter(list[Uuid]),
    "documents": TypeAdapter(list[SelectedDocumentRef]),
    "observation_ids": TypeAdapter(list[Uuid]),
    "observations": TypeAdapter(list[SelectedObservationRef]),
    "omission_document_ids": TypeAdapter(list[Uuid]),
    "omissions": TypeAdapter(list[SelectedOmissionRef]),
}


class SelectedSourceManifest(Strict):
    """Immutable selected-source manifest; ``selection_fingerprint`` is self-verifying.

    The fingerprint is a SHA-256 over the canonical JSON of every other field
    (sorted keys, compact separators). It is the state-level identity of *what
    was selected* and is distinct from the F1 ``gate_input_fingerprint_sha256``,
    which additionally covers recomputed gate inputs.
    """

    document_ids: list[Uuid] = Field(default_factory=list, max_length=5)
    documents: list[SelectedDocumentRef] = Field(default_factory=list, max_length=5)
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=20)
    observations: list[SelectedObservationRef] = Field(default_factory=list, max_length=20)
    omission_document_ids: list[Uuid] = Field(default_factory=list, max_length=5)
    omissions: list[SelectedOmissionRef] = Field(default_factory=list, max_length=5)
    selection_fingerprint: Sha256

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.document_ids, "document_ids")
        _sorted_unique(self.observation_ids, "observation_ids")
        _sorted_unique(self.omission_document_ids, "omission_document_ids")
        if set(self.omission_document_ids) & set(self.document_ids):
            raise ValueError("an omitted document cannot also be a selected document")
        if [item.document_id for item in self.documents] != self.document_ids:
            raise ValueError("documents must list exactly document_ids in order")
        if [item.observation_id for item in self.observations] != self.observation_ids:
            raise ValueError("observations must list exactly observation_ids in order")
        if [item.document_id for item in self.omissions] != self.omission_document_ids:
            raise ValueError("omissions must list exactly omission_document_ids in order")
        if self.selection_fingerprint != self.compute_fingerprint():
            raise ValueError("selection_fingerprint does not match the manifest content")
        return self

    def compute_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"selection_fingerprint"})
        return _canonical_sha256(payload)

    @classmethod
    def build(cls, **fields: object) -> Self:
        """Validate the content members, stamp the canonical digest, validate the whole.

        Every member is validated by its own type before it enters the digest
        payload (no unvalidated scratch instance, no ``model_construct``), and
        the returned manifest passes the same full validation as any other input
        — including the self-check ``selection_fingerprint == compute_fingerprint()``.
        """
        members: dict[str, Any] = {}
        for name, adapter in _MANIFEST_MEMBER_ADAPTERS.items():
            members[name] = adapter.validate_python(fields.get(name, []))
        payload = {
            name: (
                [item.model_dump(mode="json") for item in value]
                if name in {"documents", "observations", "omissions"}
                else value
            )
            for name, value in members.items()
        }
        return cls(**{**members, "selection_fingerprint": _canonical_sha256(payload)})


def _canonical_sha256(payload: object) -> str:
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(stable.encode("utf-8")).hexdigest()


def derived_trust_basis(current: TrustLevel, baseline: TrustLevel | None) -> TrustBasis:
    """Pure derivation mirroring ``monitoring._trust_basis`` (same labels, same rules)."""
    labels = {current} if baseline is None else {current, baseline}
    if labels == {TrustLevel.DOCTOR_VERIFIED}:
        return TrustBasis.DOCTOR_VERIFIED
    if labels == {TrustLevel.SELF_REPORTED_VALIDATED}:
        return TrustBasis.SELF_REPORTED
    return TrustBasis.MIXED


def selection_fingerprint(payload: object) -> str:
    """Public pure helper so S2/S4 compute the manifest digest with one recipe."""
    return _canonical_sha256(payload)


# --- F1 gate evaluation, F2 evidence identity, RB3 persistence outcome ------------------


class GateIssueRef(Strict):
    """``RunGateIssue`` shape as emitted by the F1 gate."""

    issue_type: IssueType
    reason_code: ReasonCode
    document_id: Uuid
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=40)
    message: str = Field(max_length=240)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        return self


class GateEvaluationRef(Strict):
    """``RunGateReceipt`` shape: all three F1 outcomes, with no caller-supplied blocker count.

    This is a *reference* to a server evaluation. Its presence says nothing
    about graph completion, and it never substitutes for revalidation.
    """

    run_id: Uuid
    patient_id: Uuid
    doctor_id: Uuid
    #: ``RunGateEvaluation.id`` of the persisted F1 row (F2 reads the same row).
    gate_evaluation_id: Uuid
    gate_version: SemVer
    input_fingerprint_sha256: Sha256
    decision: GateDecision
    issues: list[GateIssueRef] = Field(default_factory=list, max_length=MAX_BLOCKING_FACTS)
    historical_excluded_vi002_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_BLOCKING_FACTS
    )
    blocking_fact_count: int = Field(ge=0, le=MAX_BLOCKING_FACTS)
    unavailable_reason: GateUnavailableReason | None = None
    replayed: bool
    gate_evaluated: Literal[True] = True
    runtime_evaluable: Literal[False] = False

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.historical_excluded_vi002_ids, "historical_excluded_vi002_ids")
        if (self.decision is GateDecision.UNAVAILABLE) != (self.unavailable_reason is not None):
            raise ValueError("unavailable_reason is present iff decision is unavailable")
        if self.decision is GateDecision.PROCEED and self.blocking_fact_count != 0:
            raise ValueError("proceed requires zero blocking facts")
        if self.decision is GateDecision.HALT and self.blocking_fact_count == 0:
            raise ValueError("halt requires at least one blocking fact")
        if self.decision is GateDecision.HALT and not self.issues:
            raise ValueError("halt records at least one blocking issue")
        if self.decision is not GateDecision.HALT and self.issues:
            raise ValueError("blocking issues are recorded only with a halt decision")
        return self


class EvaluableEvidenceRef(Strict):
    """Identity of one F2 ``EvaluableReviewEvidenceV2`` projection (not its content).

    The typed content lives in the state's evidence collections; this reference
    binds them to the gate evaluation and bridge fingerprint they were computed
    from. ``history_policy`` records the implemented 365-day window.
    """

    contract_version: F2_CONTRACT_VERSION = "2.0.0"
    run_id: Uuid
    patient_id: Uuid
    doctor_id: Uuid
    as_of_utc: Iso
    workflow_version: SemVer
    state_schema_version: SemVer
    mapping_version: MappingVersion
    policy_version: PolicyVersion
    gate_evaluation_id: Uuid
    gate_version: SemVer
    gate_input_fingerprint_sha256: Sha256
    bridge_input_fingerprint_sha256: Sha256
    history_policy: F2_HISTORY_POLICY = "f2-history-365d-v1"
    history_lookback_days: Literal[365] = 365
    selected_document_ids: list[Uuid] = Field(min_length=1, max_length=5)
    selected_observation_ids: list[Uuid] = Field(default_factory=list, max_length=6)
    historical_excluded_vi002_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_BLOCKING_FACTS
    )
    no_current_reason: Literal["no_current_selected"] | None = None
    bridge_validated: Literal[True] = True
    runtime_evaluable: Literal[False] = False
    rules_executed: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.selected_document_ids, "selected_document_ids")
        _sorted_unique(self.selected_observation_ids, "selected_observation_ids")
        _sorted_unique(self.historical_excluded_vi002_ids, "historical_excluded_vi002_ids")
        if (self.no_current_reason is None) != bool(self.selected_observation_ids):
            raise ValueError("no_current_reason is set iff no current observation was selected")
        return self


class SealedReviewEvaluation(Strict):
    """Shape of one sealed RB3 ``ReviewPersistenceReceiptV1`` (``ux_review_evaluation_run``).

    A sealed evaluation is **not** graph completion. It is immutable, replay
    is exact-only, and it must never be reused after a corrected source
    identity (a corrected source requires a new run — RB4-05).
    """

    kind: Literal["sealed"] = "sealed"
    contract_version: RB3_RECEIPT_CONTRACT_VERSION = "p4-rb3-receipt-1.0.0"
    run_id: Uuid
    patient_id: Uuid
    doctor_id: Uuid
    as_of_utc: Iso
    policy_version: PolicyVersion
    policy_reference_sha256: Sha256
    gate_evaluation_id: Uuid
    gate_version: SemVer
    gate_input_fingerprint_sha256: Sha256
    bridge_input_fingerprint_sha256: Sha256
    rb3_fingerprint_version: RB3_FINGERPRINT_VERSION = "rb3-full-input-1.0.0"
    input_fingerprint_sha256: Sha256
    output_identity_sha256: Sha256
    evaluation_id: Uuid
    audit_event_id: Uuid
    lineage_label_policy: Literal["a2_transport_label"]
    dr006_policy: Literal["prohibited_denied", "not_present"]
    replayed: bool
    review_items_persisted: int = Field(ge=0)
    review_items_total: int = Field(ge=0)
    evidence_links_persisted: int = Field(ge=0)
    evidence_links_total: int = Field(ge=0)
    l1_exclusion_count: int = Field(ge=0)
    l2_exclusion_count: int = Field(ge=0)
    evaluation_completed: Literal[True] = True
    offline_evaluator_invoked: Literal[True] = True
    runtime_evaluable: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"
    demo_only: Literal[True] = True
    not_for_clinical_use: Literal[True] = True

    @model_validator(mode="after")
    def _all_or_nothing(self) -> Self:
        if self.review_items_persisted != self.review_items_total:
            raise ValueError("a sealed evaluation persisted every review item (one transaction)")
        if self.evidence_links_persisted != self.evidence_links_total:
            raise ValueError("a sealed evaluation persisted every evidence link (one transaction)")
        return self


class DeniedReviewPersistence(Strict):
    """A denied persistence is an outcome, never a completion: zero writes, no ids.

    ``DR-006`` presence denies the whole invocation
    (``dr006_persistence_not_authorized``); the graph's reaction to any denial
    is an open S2/S4 decision and is deliberately not encoded here.
    """

    kind: Literal["denied"] = "denied"
    reason: RB3DenialReason
    writes_performed: Literal[0] = 0
    observed_at_utc: Iso
    runtime_evaluable: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"


ReviewPersistenceOutcome = Annotated[
    SealedReviewEvaluation | DeniedReviewPersistence, Field(discriminator="kind")
]


# --- checkpoint reference and resume classification (shape only) ----------------------


class CheckpointRef(Strict):
    """Replay-state reference. ``claimed_status`` is informational, never authority.

    A lagging or diverging checkpoint is normal (contract §5.1) and is
    reconciled against the app DB per §7.3 at runtime — unexecuted here.
    """

    checkpoint_id: Token
    thread_id: Uuid
    last_completed_node: NodeName | None = None
    claimed_status: RunStatus | None = None


class ResumeDisposition(StrEnum):
    RESUME_UNCHANGED = "resume_unchanged"
    CHANGED_SOURCE_IDENTITY = "changed_source_identity"
    CORRECTED_SOURCE_NEW_RUN = "corrected_source_new_run"


class ResumeAssessment(Strict):
    """Schema-level halt/resume distinction for S4 (no resume implementation).

    * ``resume_unchanged`` — selection identity unchanged, nothing corrected.
    * ``changed_source_identity`` — observed selection differs from the stored one.
    * ``corrected_source_new_run`` — at least one selected source fact was
      corrected; RB4-05 requires a **new** run identity, never a resumed one.
    """

    disposition: ResumeDisposition
    app_db_status: RunStatus
    stored_selection_fingerprint: Sha256
    observed_selection_fingerprint: Sha256
    corrected_fact_ids: list[Uuid] = Field(default_factory=list, max_length=20)
    sealed_evaluation_present: bool
    checkpoint_present: bool

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.corrected_fact_ids, "corrected_fact_ids")
        same = self.stored_selection_fingerprint == self.observed_selection_fingerprint
        corrected = bool(self.corrected_fact_ids)
        if self.disposition is ResumeDisposition.RESUME_UNCHANGED and (not same or corrected):
            raise ValueError("resume_unchanged requires identical fingerprints and no correction")
        if self.disposition is ResumeDisposition.CHANGED_SOURCE_IDENTITY and (same or corrected):
            raise ValueError(
                "changed_source_identity requires differing fingerprints, no correction"
            )
        if self.disposition is ResumeDisposition.CORRECTED_SOURCE_NEW_RUN and not corrected:
            raise ValueError("corrected_source_new_run requires at least one corrected fact id")
        return self


# --- the shared state ------------------------------------------------------------------


class SharedGraphState(Strict):
    """Typed shared state of one run. Pure data; serializing it authorizes nothing.

    Field groups follow the contract §3 proposal. Reconciled differences are
    documented in the S0 review: nested immutable ``identity`` and
    ``selection`` blocks, exact ``Decimal`` values, the F1 gate reference, the
    F2 evidence reference, the RB3 persistence outcome, the checkpoint
    reference, and fixed honesty literals.
    """

    identity: RunIdentity
    selection: SelectedSourceManifest
    status: RunStatus = RunStatus.QUEUED
    current_node: NodeName | None = None
    halt_reason: HaltReason | None = None
    #: Authorization/validation clock of the latest gate/bridge revalidation —
    #: deliberately distinct from the pinned ``identity.as_of_utc``.
    last_validated_at_utc: Iso | None = None

    # evidence
    extraction_attempts: list[ExtractionAttempt] = Field(default_factory=list, max_length=10)
    extraction_facts: list[ExtractedFact] = Field(default_factory=list, max_length=40)
    verified_facts: list[VerifiedFact] = Field(default_factory=list, max_length=20)
    observations: list[ObservationView] = Field(default_factory=list, max_length=20)
    comparisons: list[ComparisonResult] = Field(default_factory=list, max_length=20)
    evidence_exclusions: list[EvidenceExclusion] = Field(default_factory=list, max_length=20)
    verification_gate: GateEvaluationRef | None = None
    evaluable_evidence: EvaluableEvidenceRef | None = None

    # agent outputs
    verification_issues: list[VerificationIssue] = Field(default_factory=list, max_length=20)
    review_flags: list[ReviewFlag] = Field(default_factory=list, max_length=20)
    draft_summary: DraftSummary | None = None
    approval: ApprovalDecision | None = None
    pending_tasks: list[TaskDraft] = Field(default_factory=list, max_length=5)
    created_task_ids: list[UuidV5] = Field(default_factory=list, max_length=5)

    # control
    retry_counts: dict[NodeName, int] = Field(default_factory=dict, max_length=11)
    errors: list[AgentError] = Field(default_factory=list, max_length=10)
    events: list[NodeEvent] = Field(default_factory=list, max_length=40)
    model_metadata: dict[Token, MetadataValue] = Field(default_factory=dict, max_length=8)
    checkpoint: CheckpointRef | None = None
    review_persistence: ReviewPersistenceOutcome | None = None
    updated_at: Iso

    # honesty literals: shape can never claim runtime authority
    policy_status: Literal["unapproved"] = "unapproved"
    runtime_policy_activated: Literal[False] = False
    runtime_evaluable: Literal[False] = False
    demo_only: Literal[True] = True
    not_for_clinical_use: Literal[True] = True

    # -- convenience read-only projections (not serialized, not authority) --
    @property
    def run_id(self) -> str:
        return self.identity.run_id

    @property
    def patient_id(self) -> str:
        return self.identity.patient_id

    @property
    def document_ids(self) -> list[str]:
        return list(self.selection.document_ids)

    @property
    def observation_ids(self) -> list[str]:
        return list(self.selection.observation_ids)

    @property
    def workflow_completed(self) -> bool:
        """Graph completion is exactly ``status == completed`` (app DB authority)."""
        return self.status is RunStatus.COMPLETED

    @property
    def review_evaluation_sealed(self) -> bool:
        """A sealed RB3 evaluation exists for this run — independent of completion."""
        return self.review_persistence is not None and self.review_persistence.kind == "sealed"

    @property
    def checkpoint_diverges(self) -> bool:
        """Checkpoint claims a status the app DB does not (informational only)."""
        return self.checkpoint is not None and self.checkpoint.claimed_status not in (
            None,
            self.status,
        )

    # -- cross-field invariants --
    @model_validator(mode="after")
    def _scope_and_uniqueness(self) -> Self:
        ident = self.identity
        if self.updated_at < ident.started_at:
            raise ValueError("updated_at precedes started_at")
        if self.checkpoint is not None and self.checkpoint.thread_id != ident.run_id:
            raise ValueError("checkpoint thread must be the run's own thread")
        for group, key in (
            (self.extraction_attempts, "attempt_id"),
            (self.extraction_facts, "fact_id"),
            (self.verified_facts, "fact_id"),
            (self.observations, "observation_id"),
            (self.verification_issues, "issue_id"),
            (self.review_flags, "review_item_id"),
        ):
            _unique([str(getattr(item, key)) for item in group], key)
        _unique([item.task_id for item in self.pending_tasks], "task_id")
        _unique([item.action_key for item in self.pending_tasks], "action_key")
        _unique(self.created_task_ids, "created_task_ids")
        _unique(
            [item.current_observation_id for item in self.comparisons], "current_observation_id"
        )
        for fact in (*self.extraction_facts, *self.verified_facts):
            if fact.patient_id != ident.patient_id:
                raise ValueError("fact patient scope differs from the run")
        for observation in self.observations:
            if observation.patient_id != ident.patient_id:
                raise ValueError("observation patient scope differs from the run")
        return self

    @model_validator(mode="after")
    def _evidence_binding(self) -> Self:
        observations = {item.observation_id: item for item in self.observations}
        for selected in self.selection.observations:
            row = observations.get(selected.observation_id)
            if row is None:
                raise ValueError("every selected observation must be present in observations")
            if (
                row.trust_level is not selected.trust_level
                or row.source_fact_id != selected.source_fact_id
            ):
                raise ValueError("selected observation manifest differs from the typed observation")
        extracted = {item.fact_id: item for item in self.extraction_facts}
        for verified in self.verified_facts:
            source = extracted.get(verified.fact_id)
            if source is not None and (
                source.verification_status is not VerificationStatus.VERIFIED
                or source.document_id != verified.document_id
            ):
                raise ValueError("a verified fact cannot project a pending/rejected extracted fact")
        for comparison in self.comparisons:
            current = observations.get(comparison.current_observation_id)
            if current is not None and (
                current.measure_type is not comparison.measure_type
                or current.value != comparison.current_value
            ):
                raise ValueError("comparison current value differs from the typed observation")
            if current is None:
                continue
            baseline = observations.get(comparison.baseline_observation_id or "")
            if baseline is not None:
                if comparison.trust_basis is not derived_trust_basis(
                    current.trust_level, baseline.trust_level
                ):
                    raise ValueError("trust_basis must follow both observations' trust levels")
            elif comparison.trust_basis not in {
                TrustBasis.MIXED,
                derived_trust_basis(current.trust_level, None),
            }:
                raise ValueError("trust_basis contradicts the current observation's trust level")
        return self

    @model_validator(mode="after")
    def _references(self) -> Self:
        ident = self.identity
        gate = self.verification_gate
        if gate is not None:
            if (gate.run_id, gate.patient_id, gate.doctor_id) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
            ):
                raise ValueError("gate evaluation belongs to a different run or scope")
            if self.last_validated_at_utc is None:
                raise ValueError("a gate reference requires the validation clock")
        evidence = self.evaluable_evidence
        if evidence is not None:
            if (
                evidence.run_id,
                evidence.patient_id,
                evidence.doctor_id,
                evidence.as_of_utc,
                evidence.workflow_version,
                evidence.state_schema_version,
                evidence.mapping_version,
                evidence.policy_version,
            ) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
                ident.as_of_utc,
                ident.workflow_version,
                ident.state_schema_version,
                ident.mapping_version,
                ident.policy_version,
            ):
                raise ValueError("evidence reference belongs to a different run identity")
            if self.last_validated_at_utc is None:
                raise ValueError("an evidence reference requires the validation clock")
            if evidence.selected_document_ids != self.selection.document_ids:
                raise ValueError("evidence documents differ from the selected manifest")
            if evidence.selected_observation_ids != self.selection.observation_ids:
                raise ValueError("evidence observations differ from the selected manifest")
            if gate is None:
                raise ValueError(
                    "evidence reference requires the gate evaluation it was built from"
                )
            if (
                evidence.gate_evaluation_id != gate.gate_evaluation_id
                or evidence.gate_version != gate.gate_version
                or evidence.gate_input_fingerprint_sha256 != gate.input_fingerprint_sha256
            ):
                raise ValueError("evidence reference is bound to a different gate evaluation")
            if gate.decision is not GateDecision.PROCEED:
                raise ValueError("evaluable evidence can only follow a proceed decision")
        persistence = self.review_persistence
        if isinstance(persistence, SealedReviewEvaluation):
            if (persistence.run_id, persistence.patient_id, persistence.doctor_id) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
            ):
                raise ValueError("sealed evaluation belongs to a different run or scope")
            if gate is not None and (
                persistence.gate_evaluation_id != gate.gate_evaluation_id
                or persistence.gate_input_fingerprint_sha256 != gate.input_fingerprint_sha256
            ):
                raise ValueError("sealed evaluation is bound to a different gate evaluation")
            if evidence is not None and persistence.bridge_input_fingerprint_sha256 != (
                evidence.bridge_input_fingerprint_sha256
            ):
                raise ValueError("sealed evaluation is bound to different bridge evidence")
            if evidence is None:
                raise ValueError(
                    "a sealed evaluation requires the F2 evidence it was computed from"
                )
        return self

    @model_validator(mode="after")
    def _lifecycle(self) -> Self:
        status = self.status
        halted = status in HALTED_STATUSES
        if halted != (self.halt_reason is not None):
            raise ValueError("halt_reason is present iff the run is in a halted status")
        if status is RunStatus.NEEDS_VERIFICATION and self.halt_reason is not (
            HaltReason.UNVERIFIED_FACTS
        ):
            raise ValueError("needs_verification halts with halt_reason=unverified_facts")
        if (
            status is RunStatus.FAILED_RETRYABLE
            and self.halt_reason is not HaltReason.RETRY_EXHAUSTED
        ):
            raise ValueError("failed_retryable halts with halt_reason=retry_exhausted")
        approved = self.approval is not None and self.approval.decision in {
            ApprovalChoice.APPROVE,
            ApprovalChoice.EDIT,
        }
        if (
            status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.NEEDS_VERIFICATION}
            and self.approval is not None
        ):
            raise ValueError("no approval can exist before the draft is approved-for-decision")
        if status in {RunStatus.FINALIZING, RunStatus.COMPLETED} and (
            not approved or self.draft_summary is None
        ):
            raise ValueError("finalizing/completed require an approve-or-edit decision and a draft")
        if status is RunStatus.AWAITING_DECISION and (
            self.approval is not None or self.draft_summary is None
        ):
            raise ValueError("awaiting_decision has a draft and no recorded decision")
        if self.pending_tasks and (
            status not in {RunStatus.FINALIZING, RunStatus.COMPLETED} or not approved
        ):
            raise ValueError("task drafts exist only after an approve/edit decision")
        task_ids = {item.task_id for item in self.pending_tasks}
        if not set(self.created_task_ids) <= task_ids:
            raise ValueError("created_task_ids must reference pending task drafts")
        if self.created_task_ids and status not in {RunStatus.FINALIZING, RunStatus.COMPLETED}:
            raise ValueError("tasks are created only while finalizing or completed")
        finalize_events = [
            event for event in self.events if event.node is NodeName.FINALIZE_ACTIONS
        ]
        if finalize_events:
            detail = finalize_events[-1].detail
            if not isinstance(detail, FinalizeDetail):  # pragma: no cover - NodeEvent guarantees it
                raise ValueError("finalize event must carry a finalize detail")
            if detail.task_created != bool(self.created_task_ids):
                raise ValueError("finalize detail task_created must match created_task_ids")
            if self.approval is not None and detail.approval_decision != self.approval.decision:
                raise ValueError("finalize detail decision must match the approval")
        if self.retry_counts:
            for _node, count in self.retry_counts.items():
                if not 1 <= count <= 5:
                    raise ValueError("retry_counts values are bounded to 1..5")
        return self

    @model_validator(mode="after")
    def _gate_binding(self) -> Self:
        """No draft, comparison, prompt or decision can exist past a gate that did not proceed."""
        gate = self.verification_gate
        proceeded = gate is not None and gate.decision is GateDecision.PROCEED
        post_draft = self.status in {
            RunStatus.AWAITING_DECISION,
            RunStatus.FINALIZING,
            RunStatus.COMPLETED,
        }
        if gate is not None and gate.decision is GateDecision.HALT and post_draft:
            raise ValueError("a halting gate cannot coexist with a post-draft status")
        if (
            self.comparisons or self.review_flags or self.draft_summary is not None
        ) and not proceeded:
            raise ValueError("comparisons, review prompts and drafts require a proceed decision")
        if post_draft and not proceeded:
            raise ValueError("post-draft statuses require a proceed decision")
        if self.status is RunStatus.NEEDS_VERIFICATION and (
            gate is None or gate.decision is not GateDecision.HALT
        ):
            raise ValueError("needs_verification requires a recorded halt decision")
        if gate is not None and gate.decision is not GateDecision.UNAVAILABLE:
            state_types = sorted(item.issue_type for item in self.verification_issues)
            gate_types = sorted(item.issue_type for item in gate.issues)
            if state_types != gate_types:
                raise ValueError(
                    "verification_issues must mirror the gate evaluation's blocking issues"
                )
        return self


def derive_task_id(namespace: uuid.UUID, action_key: str) -> str:
    """Pure helper: the derived ``uuid5(namespace, action_key)`` task identity (P0-R04).

    ``TASK_NAMESPACE`` is not pinned by any contract; S0 does not invent one.
    """
    return str(uuid.uuid5(namespace, action_key))


__all__ = [
    "DEMO_NOTICE",
    "DETAIL_KIND_BY_NODE",
    "F2_CONTRACT_VERSION",
    "F2_HISTORY_POLICY",
    "HALTED_STATUSES",
    "NODE_TOOLS",
    "OMISSION_REASON",
    "POLICY_REFERENCE_VERSION",
    "RB3_FINGERPRINT_VERSION",
    "RB3_RECEIPT_CONTRACT_VERSION",
    "STATE_SCHEMA_VERSION",
    "WORKFLOW_VERSION",
    "AgentError",
    "ApprovalChoice",
    "ApprovalDecision",
    "CheckpointRef",
    "ClaimCitation",
    "ComparisonResult",
    "Confidence",
    "DeltaDecimal",
    "DeniedReviewPersistence",
    "DetailKind",
    "DraftExecutionStatus",
    "DraftProvider",
    "DraftSummary",
    "EvaluableEvidenceRef",
    "EventDetail",
    "EvidenceExclusion",
    "ExactDecimal",
    "ExclusionReason",
    "ExtractedFact",
    "ExtractionAttempt",
    "Extractor",
    "FinalizeDetail",
    "GateDecision",
    "GateDetail",
    "GateEvaluationRef",
    "GateIssueRef",
    "GateUnavailableReason",
    "HaltReason",
    "IncomparableReason",
    "Iso",
    "IssueType",
    "MappingVersion",
    "MetadataValue",
    "NodeEvent",
    "NodeName",
    "NodeOutcome",
    "ObservationView",
    "PathReason",
    "PolicyVersion",
    "PromptVersion",
    "ProvenanceKind",
    "ProvenanceRef",
    "QualityFlag",
    "RB3DenialReason",
    "ResumeAssessment",
    "ResumeDisposition",
    "ReviewFlag",
    "ReviewHint",
    "ReviewItemState",
    "ReviewPersistenceOutcome",
    "ReviewRuleId",
    "RunIdentity",
    "RunStatus",
    "SealedReviewEvaluation",
    "SelectedDocumentRef",
    "SelectedObservationRef",
    "SelectedOmissionRef",
    "SelectedSourceManifest",
    "SemVer",
    "Sha256",
    "SharedGraphState",
    "Strict",
    "TaskDraft",
    "ToolName",
    "TriageDetail",
    "TriagePath",
    "TrustBasis",
    "Uuid",
    "UuidV5",
    "ValidationDetail",
    "ValidationOutcome",
    "VerificationIssue",
    "VerificationStatus",
    "ViolationCode",
    "derive_task_id",
    "derived_trust_basis",
    "selection_fingerprint",
]
