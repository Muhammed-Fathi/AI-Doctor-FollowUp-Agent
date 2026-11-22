# Shared State and Graph Contract (LangGraph)

| Field | Value |
|---|---|
| Document ID | `CTR-STATE-001` |
| Version | `0.4.0-p0` |
| Status | **IN REVIEW — proposal, not implemented** |
| Phase | `P0` (design). Implementation: P5 |
| Related | `REQ-GRAPH-01..05`, `REQ-LLM-02`, `REQ-RULE-03`, `REQ-DATA-04`, `REQ-DATA-05`, `REQ-OPS-04`, ADR-0006 |
| Revision | 0.2.0 added `VerificationIssue` vs `ReviewFlag` separation (`P0-R03`), trust level and injected as-of clock (`P0-R05`, `P0-R07`), deterministic task identity (`P0-R04`) and the bounded decision loops (ADR-0006). 0.3.0 adds **typed trace detail payloads and typed extraction attempts** (`P0-R08`), the **app-DB source-of-truth / checkpoint reconciliation contract** (`P0-R09`), the **closed verified-fact → observation mapping version** (`P0-R10`) and the **observation admissibility predicate** (`P0-R11`). 0.4.0 adds the distinct **`MappingVersion`** type (`P0-R12`), the **redacted API projection** note for attempts (`P0-R13`) and the **one-measurement-tuple-per-document association rule** (`P0-R14`) |
| Runtime assumption | Python 3.12 on the owner's laptop; LangGraph + `langgraph-checkpoint-sqlite` (versions unverified — see `DEPENDENCIES.md`) |

> This is a **contract proposal**. Nothing here is executed in P0. API details of LangGraph
> (`interrupt`, `Command(resume=...)`, checkpointer construction) must be re-verified against the
> official docs at P5 before implementation.

---

## 1. Scope

One graph, one workflow version, one run per follow-up request:

- run identity and idempotency,
- the typed shared state (Pydantic v2 models, JSON-serializable),
- per-node read/write permissions and tool allowlists,
- nodes, conditional edges, halt paths,
- checkpoint, interrupt/resume, retry and duplicate-suppression policy,
- validation and size limits.

Out of scope: prompt text, SQL schema (see `DATA_DICTIONARY.md`), HTTP shapes (see `API_CONTRACT.md`).

## 2. Run identity and versioning

| Concept | Definition | Example |
|---|---|---|
| `run_id` | UUIDv4 created when an authenticated doctor starts a workflow | `6f1c…` |
| `thread_id` | Checkpoint thread key; equals `run_id` (one thread per run, no reuse) | `6f1c…` |
| `workflow_version` | SemVer of the graph shape + node semantics | `1.0.0` |
| `state_schema_version` | SemVer of this state contract | `1.0.0` |
| `policy_version` | Version of the demo rule policy file | `demo-policy-1.1.0` |
| `as_of_utc` | Injected evaluation clock: policy value in demo mode, real instant otherwise; persisted on the run | `2026-11-14T12:00:00Z` |
| `prompt_version` | Version tag of the draft prompt/template | `draft-v1` |
| `mapping_version` | Version of the closed verified-fact → observation mapping table (`DATA_DICTIONARY.md` §3.3). Typed as **`MappingVersion`**, not `SemVer`: the format is `map-<major>.<minor>.<patch>` (`^map-\d+\.\d+\.\d+$`) | `map-1.0.0` |
| `idempotency_key` | Server-computed SHA-256 over stable inputs (§7) | hex digest |

Rules:

1. A run never changes `workflow_version` mid-flight. A version bump invalidates old in-flight runs at resume time with `E_WORKFLOW_VERSION_MISMATCH`.
2. A checkpoint with an unknown `state_schema_version` cannot be resumed; the run is marked `failed_terminal` and audited.
3. `workflow_version`, `policy_version`, `prompt_version` and model metadata are persisted on every draft/review record so that any output can be explained later.

## 3. Shared state (Pydantic v2 proposal)

All models are `extra="forbid"`, all collections are bounded by the caps in §8, and the whole state must round-trip through JSON (no ORM objects, file handles, bytes, or datetime objects without ISO-8601 serialization).

```python
# backend/app/agents/state.py  (PROPOSAL ONLY — not created in P0)
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SemVer = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
# The mapping table is versioned with a prefixed id, so it needs its own annotated type:
# a bare SemVer would reject the published default "map-1.0.0" (resolves `P0-R12`).
MappingVersion = Annotated[str, StringConstraints(pattern=r"^map-\d+\.\d+\.\d+$")]
Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{36}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Iso = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    needs_verification = "needs_verification"   # halted, resumable
    awaiting_decision = "awaiting_decision"     # interrupted, resumable
    finalizing = "finalizing"
    completed = "completed"
    failed_retryable = "failed_retryable"       # halted, resumable
    failed_terminal = "failed_terminal"


class ProvenanceRef(Strict):
    kind: Literal["document_span", "observation", "checkin_note"]
    document_id: Uuid | None = None
    page_index: int | None = Field(default=None, ge=0, le=200)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    observation_id: Uuid | None = None
    raw_text: str | None = Field(default=None, max_length=500)
    extractor: Literal["pypdf", "tesseract", "manual", "patient_form"] | None = None


class QualityFlag(StrEnum):
    clean = "clean"
    low_confidence = "low_confidence"
    ambiguous_date = "ambiguous_date"
    ambiguous_unit = "ambiguous_unit"
    unparseable_value = "unparseable_value"
    source_conflict = "source_conflict"
    page_missing = "page_missing"


class VerificationStatus(StrEnum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class ExtractedFact(Strict):
    fact_id: Uuid
    patient_id: Uuid
    document_id: Uuid
    field_name: Literal["report_date", "test_name", "value", "unit", "reference_text"]
    raw_text: str = Field(max_length=300)
    normalized_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    quality_flags: list[QualityFlag] = Field(default_factory=list, max_length=6)
    verification_status: VerificationStatus = VerificationStatus.pending
    provenance: ProvenanceRef
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    verification_note: str | None = Field(default=None, max_length=300)


class VerifiedFact(Strict):
    """A fact a human accepted or corrected. The only fact type admissible downstream."""
    fact_id: Uuid
    patient_id: Uuid
    field_name: str
    value: str
    unit: str | None = None
    measured_at: Iso | None = None
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=4)
    verified_by: Uuid
    verified_at: Iso


class TrustLevel(StrEnum):
    self_reported_validated = "self_reported_validated"   # patient check-in; schema/unit/plausibility checked
    doctor_verified = "doctor_verified"                   # derived from a doctor-verified fact or a correction


class ObservationView(Strict):
    observation_id: Uuid
    patient_id: Uuid
    measure_type: Literal["systolic_bp", "diastolic_bp", "heart_rate", "glucose"]
    value: float
    unit: Literal["mmHg", "bpm", "mg/dL"]
    measured_at: Iso
    source: Literal["patient_checkin", "verified_document", "seed_fixture"]
    validation: Literal["ok", "ok_with_warning", "rejected"]   # schema/units/plausibility data check
    trust_level: TrustLevel                                    # provenance class, never conflated
    verified_by: Uuid | None = None                            # required iff doctor_verified
    verified_at: Iso | None = None
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)


class ComparisonResult(Strict):
    comparison_id: Uuid
    measure_type: str
    unit: str
    current_observation_id: Uuid
    baseline_observation_id: Uuid | None = None
    current_value: float
    baseline_value: float | None = None
    delta: float | None = None
    comparable: bool
    incomparable_reason: Literal["no_baseline", "unit_mismatch", "stale_baseline", "missing_timestamp",
                               "not_admissible"] | None = None   # inadmissible input is reported, never silently dropped
    trust_basis: Literal["self_reported", "doctor_verified", "mixed"]
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)


class VerificationIssue(Strict):
    """Pre-verification blocker emitted by the gate. Never a review rule, never trusted downstream."""
    issue_id: Uuid
    issue_type: Literal["VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006"]
    reason_code: str = Field(max_length=64)
    blocking: Literal[True] = True
    message: str = Field(max_length=240)          # neutral wording, no clinical interpretation
    document_id: Uuid | None = None
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    created_at: Iso


class ReviewFlag(Strict):
    """Post-verification deterministic review prompt; inputs are verified evidence only."""
    review_item_id: Uuid
    rule_id: str = Field(pattern=r"^DR-\d{3}$")
    reason_code: str = Field(max_length=64)
    workflow_hint: Literal["data_quality", "verification_needed", "change_to_review"] | None = None
    message: str = Field(max_length=240)          # neutral wording, no clinical interpretation
    trust_basis: Literal["self_reported", "doctor_verified", "mixed"]
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    policy_version: str
    demo_only: Literal[True] = True
    dedupe_key: Sha256
    state: Literal["open", "decided"] = "open"


class ClaimCitation(Strict):
    text: str = Field(max_length=400)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=6)


class DraftSummary(Strict):
    draft_id: Uuid
    provider: Literal["ollama", "deterministic_fallback"]
    model: str | None = None                      # null for fallback; never invented
    execution_status: Literal["model_ok", "model_invalid_schema", "model_timeout", "model_unavailable", "fallback_no_model"]
    prompt_version: str
    latency_ms: int | None = Field(default=None, ge=0)
    claims: list[ClaimCitation] = Field(default_factory=list, max_length=20)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    not_asserted: list[str] = Field(default_factory=list, max_length=10)
    disclaimer: Literal["EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"]
    created_at: Iso


class ApprovalDecision(Strict):
    decision_id: Uuid | None = None
    decision: Literal["approve", "edit", "reject"] | None = None
    edited_summary: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=500)
    doctor_id: Uuid | None = None
    decided_at: Iso | None = None


class TaskDraft(Strict):
    action_key: Sha256                             # derived from the persisted decision, never from task_id
    task_id: Uuid                                  # uuid5(namespace, action_key): stable across retries
    title: str = Field(max_length=160)
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: str | None = Field(default=None, max_length=500)
    notification_text: str | None = Field(default=None, max_length=240)


class AgentError(Strict):
    code: str = Field(max_length=48)              # e.g. E_EXTRACTION_FAILED, E_MODEL_TIMEOUT
    node: str = Field(max_length=48)
    message: str = Field(max_length=300)          # no document body, no secrets
    retryable: bool
    attempt: int = Field(ge=1, le=5)
    occurred_at: Iso


class TriagePath(StrEnum):
    text_layer = "text_layer"
    ocr_direct = "ocr_direct"
    ocr_preprocess_retry = "ocr_preprocess_retry"
    flag_for_human = "flag_for_human"


class PathReason(StrEnum):
    text_layer_available = "text_layer_available"      # no OCR needed at all
    confidence_ok = "confidence_ok"                    # OCR confidence at or above the floor
    low_confidence = "low_confidence"                  # below the floor, budget remaining
    ocr_transient_error = "ocr_transient_error"        # process error/timeout, budget remaining
    retry_exhausted = "retry_exhausted"                # budget spent -> human path


class ExtractionAttempt(Strict):
    """Typed per-attempt extraction metadata.

    This is the *only* input `extraction_triage` may read (besides the candidate facts). It exists
    because attempt metadata is not derivable from `ExtractedFact` and must not be inferred from free
    text. Values are reported by the extractor at runtime; nothing here is promised in P0 (`P0-R08`).

    This is the **internal** shape. The HTTP document endpoint exposes only a redacted projection
    (`ExtractionAttemptSummary` in `openapi.phase0.yaml`): route/outcome/duration/tool version/timestamp.
    Doctors see the derived decision through `TraceEvent.detail`; `engine_confidence` there is nullable and
    engine-reported (`P0-R13`).
    """
    attempt_id: Uuid
    document_id: Uuid
    path: Literal["pypdf", "tesseract", "manual"]
    preprocessing: Literal["none", "grayscale_upscale"]
    page_from: int = Field(ge=0, le=200)
    page_to: int = Field(ge=0, le=200)
    engine_confidence: float | None = Field(default=None, ge=0, le=1)   # null when the engine reports none
    text_char_count: int = Field(ge=0, le=200000)
    succeeded: bool
    error_code: str | None = Field(default=None, max_length=48)
    duration_ms: int = Field(ge=0)
    tool_version: str | None = Field(default=None, max_length=64)
    created_at: Iso                                     # attempt timestamp (also in the DB row)


class TriageDetail(Strict):
    kind: Literal["triage"] = "triage"
    path_selected: TriagePath
    path_reason: PathReason
    document_id: Uuid
    attempt_index: int = Field(ge=1, le=2)              # retry budget is 2 (ADR-0006 §4.1)
    engine_confidence: float | None = Field(default=None, ge=0, le=1)
    preprocessing_applied: bool


class ValidationDetail(Strict):
    kind: Literal["validation"] = "validation"
    validation_outcome: Literal["accept", "repair_requested", "fallback_selected"]
    attempt_index: int = Field(ge=1, le=2)
    violation_codes: list[Literal["schema_invalid", "unsupported_evidence", "prohibited_content",
                                  "missing_disclaimer", "ungrounded_number", "patient_addressing"]] = Field(
        default_factory=list, max_length=6)


class GateDetail(Strict):
    kind: Literal["gate"] = "gate"
    decision: Literal["proceed", "halt"]
    blocking_fact_count: int = Field(ge=0, le=40)
    issue_types: list[Literal["VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006"]] = Field(
        default_factory=list, max_length=6)


class FinalizeDetail(Strict):
    kind: Literal["finalize"] = "finalize"
    approval_decision: Literal["approve", "edit", "reject"]
    task_created: bool
    notification_created: bool


EventDetail = Annotated[
    TriageDetail | ValidationDetail | GateDetail | FinalizeDetail,
    Field(discriminator="kind"),
]


class NodeEvent(Strict):
    """One graph-node execution record. `detail` is typed and bounded, never free text."""
    node: str = Field(max_length=48)
    attempt: int = Field(default=1, ge=1, le=5)
    started_at: Iso
    ended_at: Iso | None = None
    outcome: Literal["ok", "halted", "interrupted", "retried", "failed"] | None = None
    tools_called: list[str] = Field(default_factory=list, max_length=6)
    detail: EventDetail | None = None


class SharedGraphState(Strict):
    # identity
    run_id: Uuid
    thread_id: Uuid
    workflow_version: SemVer
    state_schema_version: SemVer
    policy_version: str
    prompt_version: str
    as_of_utc: Iso
    mapping_version: MappingVersion
    idempotency_key: Sha256
    started_at: Iso

    # scope (set from the authenticated request, never from client-supplied facts)
    patient_id: Uuid
    doctor_id: Uuid
    encounter_id: Uuid | None = None
    document_ids: list[Uuid] = Field(default_factory=list, max_length=5)
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=20)

    # evidence
    extraction_facts: list[ExtractedFact] = Field(default_factory=list, max_length=40)
    extraction_attempts: list[ExtractionAttempt] = Field(default_factory=list, max_length=10)  # triage input
    verified_facts: list[VerifiedFact] = Field(default_factory=list, max_length=20)
    observations: list[ObservationView] = Field(default_factory=list, max_length=20)
    comparisons: list[ComparisonResult] = Field(default_factory=list, max_length=20)

    # agent outputs
    verification_issues: list[VerificationIssue] = Field(default_factory=list, max_length=20)
    review_flags: list[ReviewFlag] = Field(default_factory=list, max_length=20)
    draft_summary: DraftSummary | None = None
    approval: ApprovalDecision = Field(default_factory=ApprovalDecision)
    pending_tasks: list[TaskDraft] = Field(default_factory=list, max_length=5)
    created_task_ids: list[Uuid] = Field(default_factory=list, max_length=5)

    # control
    status: RunStatus = RunStatus.queued
    current_node: str | None = None
    halt_reason: Literal["unverified_facts", "model_failed", "retry_exhausted", "needs_human_decision"] | None = None
    retry_counts: dict[str, int] = Field(default_factory=dict)   # node -> attempts, capped in §8
    errors: list[AgentError] = Field(default_factory=list, max_length=10)
    events: list[NodeEvent] = Field(default_factory=list, max_length=40)
    model_metadata: dict[str, str] = Field(default_factory=dict) # provider/model/latency summary only
    updated_at: Iso
```

Design notes:

- **No ORM objects** in state: nodes receive IDs and receive facts through tool calls returning typed DTOs.
- **Verified-only gate** is enforced structurally: downstream nodes may only read `VerifiedFact` and `ObservationView`, never `ExtractedFact` (`REQ-SEC-04`).
- `message` on `ReviewFlag` and `VerificationIssue` is restricted to neutral, non-clinical wording; see `docs/clinical-safety/DEMO_REVIEW_RULES.md` §6.
- `disclaimer` is a fixed literal, so a draft cannot exist without the educational label (`REQ-SEC-05`).
- **Two distinct outputs.** `verification_issues` (pre-verification blockers, `VI-*`) and `review_flags`
  (post-verification prompts, `DR-*`) are separate state fields produced by separate nodes. A `VI-*` item can
  never be promoted into a `DR-*` flag, and neither is derived from the other (`P0-R03`).
- **Trust is explicit.** Every observation carries `trust_level`; `self_reported_validated` values are never
  described as doctor-verified, and `verified_by` is null for them (`REQ-DATA-04`).
- **Clock is injected.** `as_of_utc` is set once per run and used by every time-dependent rule, so the same
  run replays identically on any date (`REQ-OPS-04`).
- **Trace decisions are typed, not prose.** `NodeEvent.detail` is a discriminated union over the four decisions
  the graph actually makes (`triage`, `validation`, `gate`, `finalize`). Every field is an enum, an ID, a
  bounded count or a probability in `[0,1]`; **no field may carry document text, raw values or model output**
  (`P0-R08`). `additionalProperties`/`extra` are forbidden, so an ad-hoc extra key is a schema error, not a
  silent extension.
- **Attempts are state, not inference.** `extraction_triage` reads `extraction_attempts[]` (written by
  `document_extract`); it never re-reads the document, never parses prose, and never guesses a confidence.
  When the engine reports no confidence, `engine_confidence` is `null` and the reason code says so
  (`ocr_transient_error`) rather than inventing a number.
- **Mapping is closed and versioned.** Only a fixed alias/unit table (`map-1.0.0`, `DATA_DICTIONARY.md` §3.3)
  turns a verified fact into an observation; `mapping_version` is persisted with the run so a later mapping
  change cannot silently reinterpret old data (`REQ-DATA-05`). `MappingVersion` accepts exactly
  `^map-\d+\.\d+\.\d+$`, so `"map-1.0.0"` validates while `"1.0.0"`, `"map-1.0"` and `"map-1.0.0-rc1"`
  are rejected. `mapping_version` and `state_schema_version` are deliberately different types: one names a
  policy table, the other a schema (`P0-R12`).

## 4. Nodes, reads/writes, and transitions

### 4.1 Node table

| # | Node (agent) | Reads | Writes | Tools (allowlist) | May interrupt? |
|---|---|---|---|---|---|
| N0 | `intake_validate` (orchestrator) | run request, scope | `observations`, `document_ids`, `status` | none — service-layer reads only | no |
| N1 | `document_extract` (`medical_document`) | `document_ids` | `extraction_facts`, `extraction_attempts` | `extract_document`, `get_document_pages`, `validate_structured_fields` | no |
| N1a | `extraction_triage` (orchestrator, deterministic router) | `extraction_facts`, `extraction_attempts` (**typed**), `retry_counts` | `events[].detail` = `TriageDetail`, `retry_counts` | none — reads typed attempt metadata only (`P0-R08`) | no |
| N2 | `fact_verify_gate` (orchestrator, deterministic) | `extraction_facts`, document↔patient reference | `verification_issues`, `status`, `halt_reason`, `events[].detail` = `GateDetail` | none — service-layer reads only | **yes** (halt `needs_verification`) |
| N3 | `monitor_compare` (`patient_monitoring`) | `verified_facts`, `observations` | `comparisons` | `read_observations`, `compare_observations` | no |
| N4 | `review_rules` (`review_priority`) | `verified_facts`, `comparisons` | `review_flags` | `read_verified_facts`, `evaluate_demo_review_rules` | no |
| N5 | `draft_summary` (`doctor_communication`) | `verified_facts`, `comparisons`, `review_flags` | `draft_summary`, `model_metadata` | `read_verified_facts`, `draft_grounded_summary` | no |
| N5a | `draft_validation` (orchestrator, deterministic) | `draft_summary` | `events[].detail` = `ValidationDetail`, `retry_counts` | none — schema/citation/content validator | no |
| N6 | `clinician_approval` (orchestrator) | `draft_summary`, `review_flags` | `approval`, `status` | none — service-layer reads only | **yes** (interrupt `awaiting_decision`) |
| N7 | `finalize_actions` (`follow_up`) | `approval` (must be approved/edited) | `pending_tasks`, `created_task_ids`, `status`, `events[].detail` = `FinalizeDetail` | `create_in_app_task`, `list_due_tasks` | no |
| N8 | `halted` (orchestrator) | any | `status`, `halt_reason` | none | terminal-for-now, resumable |

### 4.2 Transition graph

```mermaid
stateDiagram-v2
    [*] --> intake_validate
    intake_validate --> document_extract: documents present and scoped
    intake_validate --> monitor_compare: no documents
    intake_validate --> failed_terminal: scope or schema invalid
    document_extract --> extraction_triage
    extraction_triage --> document_extract: ocr_preprocess_retry - budget remaining
    extraction_triage --> fact_verify_gate: proceed - text layer or confidence ok
    extraction_triage --> fact_verify_gate: flag_for_human - retry exhausted
    document_extract --> failed_retryable: extraction transient failure
    document_extract --> failed_terminal: unsupported or corrupt file
    fact_verify_gate --> monitor_compare: all blocking facts verified
    fact_verify_gate --> needs_verification: pending or rejected facts
    needs_verification --> fact_verify_gate: resume after doctor verification
    monitor_compare --> review_rules
    review_rules --> draft_summary
    draft_summary --> draft_validation
    draft_validation --> draft_summary: repair - one attempt, stricter constraints
    draft_validation --> clinician_approval: accept model draft
    draft_validation --> clinician_approval: accept labelled fallback
    draft_summary --> failed_retryable: model timeout after retry
    clinician_approval --> awaiting_decision: interrupt
    awaiting_decision --> finalize_actions: resume approve or edit - status finalizing
    awaiting_decision --> completed: resume reject - no task
    finalize_actions --> completed: task + notification + audit in one app-DB transaction
    failed_retryable --> [*]: resumable halt
    failed_terminal --> [*]
    completed --> [*]
```

Path vocabulary (the enum, not the edge label): `text_layer` = no OCR needed; `ocr_direct` = OCR used and its
confidence is at or above the floor (this includes a retried pass whose preprocessing already ran);
`ocr_preprocess_retry` = the decision to run OCR again with deterministic preprocessing; `flag_for_human` =
budget exhausted, human must act. The mermaid labels `proceed` / `ocr_preprocess_retry` / `flag_for_human` are
edges; `proceed` maps to `text_layer` or `ocr_direct` depending on whether OCR ran.

Routing rules:

1. Conditional edge decisions are **deterministic functions of state**, never model output (`REQ-GRAPH-01`).
2. `extraction_triage` is the bounded tool-selection step described in ADR-0006 §4. Its entire input is
   `extraction_attempts[]` (typed: `path`, `preprocessing`, `engine_confidence`, `text_char_count`,
   `succeeded`) plus `retry_counts`. It emits exactly one `TriageDetail` per invocation:
   `path_selected ∈ {text_layer, ocr_direct, ocr_preprocess_retry, flag_for_human}`,
   `path_reason ∈ {text_layer_available, confidence_ok, low_confidence, ocr_transient_error, retry_exhausted}`,
   `attempt_index ∈ {1,2}`, plus `engine_confidence`/`preprocessing_applied`. Retry budget is 2; the router
   cannot loop and cannot skip verification. A triage decision that would need information not present in
   `extraction_attempts` is a **schema gap**, not an invitation to read the document (`P0-R08`).
3. `fact_verify_gate` blocks the pipeline when any fact that a downstream node would consume is `pending` or
   `rejected`. It emits `VerificationIssue` items (`VI-*`) — never `ReviewFlag`s — and halts with
   `needs_verification`. Non-blocking informational facts may remain pending only if no downstream node reads them.
4. `draft_summary` may proceed on fallback (labelled); it may **not** proceed if it would fabricate to fill a gap.
   `draft_validation` accepts, requests one bounded repair, or rejects to the fallback path (ADR-0006 §4.2).
5. `finalize_actions` is unreachable unless `approval.decision in {approve, edit}` **and**
   `approval.doctor_id` matches an authenticated doctor with patient scope. `reject` routes straight to
   `completed` with no task (`US-10`).
6. `finalize_actions` runs only while the run is `finalizing` (entered when a paused `awaiting_decision` run is
   resumed with a persisted approve/edit decision), and commits task + notification + audit finalization in **one**
   transaction (§7.2).
7. Every node appends exactly one `NodeEvent` on entry/exit; the trace is part of the demo evidence.
8. `NodeEvent.detail` is present **iff** the node makes a bounded decision: N1a → `triage`, N2 → `gate`,
   N5a → `validation`, N7 → `finalize`. All other nodes must carry `detail = null` (schema-validated), so an
   untyped extra key cannot appear. `attempt` is the retry index of that node (`1` for the first execution).

## 5. Checkpoint, interrupt and resume

### 5.1 Checkpoint policy

- Checkpointer: `langgraph-checkpoint-sqlite` on a dedicated SQLite file (ADR-0003).
- A checkpoint is written **after** each node completes and **before** each interrupt is surfaced.
- `thread_id == run_id`; one thread per run, never reused across patients.
- Sync is not forced on every node, but the approval interrupt explicitly flushes so a hard kill preserves `awaiting_decision`.
- **The app DB is the single source of truth for run status, the approval decision, tasks and notifications
  (`P0-R09`).** The checkpoint DB is *replay state only*: it may lag behind the app DB (a node committed, the
  checkpoint write did not), and a lagging checkpoint is normal, not corruption.
- The two SQLite files cannot share a transaction. Nothing in this contract claims they can; consistency is
  achieved by ordering (app-DB commit **before** checkpoint write) plus an idempotent, replayable finalize step
  (§7.2).
- Retention: checkpoints are runtime artifacts. Reset (`POST /api/v1/demo/reset`) deletes app DB + checkpoint DB + uploads together.

### 5.2 Interrupt contract

| Property | Rule |
|---|---|
| Where | Only N2 (`needs_verification`) and N6 (`awaiting_decision`) |
| Payload surfaced to UI | run ID, status, `as_of_utc`, draft + citations, `verification_issues[]` (pre-verification) or `review_flags[]` (post-verification), blocking fact IDs, provider metadata, allowed actions |
| Resume input | `{run_id, decision, doctor_id (from session, never body), reason?, edited_summary?}` |
| Resume validation | run status must be the expected paused state; doctor must be authenticated and patient-scoped; `decision` must be in the allowed set; `edited_summary` capped at 4000 chars |
| Resume after verification | blocked fact IDs must now be `verified`; otherwise re-interrupt with the same reason and increment no side effects |
| Idempotent resume | Resuming a run already `completed` returns the stored result with `200` and no new task (no `409` loop) |
| Crash mid-resume | Node is not checkpointed as complete until its writes commit; resume reconciles against the **app DB** (§7.3), recomputes deterministically, and the derived `action_key` suppresses duplicates |

### 5.3 What the agent may never do on resume

- Accept client-supplied clinical facts, observation values, or evidence as authoritative.
- Skip verification because a request says `force=true`.
- Create a task because a request says `approved=true` without a matching approval record.
- Change `workflow_version`, `policy_version`, patient scope, or `doctor_id`.

## 6. Retry and failure policy

| Failure class | Examples | Behaviour | Max attempts |
|---|---|---|---|
| Validation / authorization | bad schema, out-of-scope patient, unsupported file type | Terminal immediately, typed error, no retry | 1 |
| Document parse permanent | corrupt PDF, encrypted PDF, zero extractable pages | Terminal for that document; run halts with `failed_terminal` only if the document was required | 1 |
| OCR transient | Tesseract process error, timeout on a large page | Retry with image downscale once, then flag `page_missing`/low confidence | 2 |
| OCR low confidence | Engine confidence below `ocr_confidence_floor` | `extraction_triage` selects `ocr_preprocess_retry` (deterministic preprocessing), then `flag_for_human` with `VI-005` | 2 |
| Draft schema/citation failure | invalid JSON, unsupported evidence ID, prohibited content | `draft_validation` requests one repair with stricter constraints, then labelled fallback | 2 |
| Model transport | connection refused, socket timeout | Retry once with reduced output budget, then fallback | 2 |
| Model output invalid | JSON schema violation, unsupported claim citation | One repair attempt with a stricter instruction; then fallback | 2 |
| Database busy | `database is locked` | Bounded backoff (e.g. 50/150/400 ms) | 3 |
| Unknown exception | bug | No retry, `failed_terminal`, audit with stack-class summary only (no data) | 1 |

Rules:

- Retries are **per node**, counted in `retry_counts`, and never re-run earlier successful nodes.
- A retried node must be a pure function of state plus external reads; a mutating tool must be idempotent by key.
- No unbounded loops: `retry_counts[node]` capped at 5; exceeding it forces `failed_retryable` with `halt_reason=retry_exhausted`.
- Backoff uses the configured demo values; no jitter claim is made in P0.

## 7. Idempotency

| Operation | Idempotency key | Storage guard |
|---|---|---|
| Start a workflow run | `sha256(patient_id | workflow_version | sorted(document_ids) | sorted(observation_ids) | client_request_id)` | Unique index on `workflow_run.idempotency_key`; repeat returns the existing run |
| Verification decision | `sha256(fact_id | decision | normalized_value | doctor_id)` | Append-only; identical repeat is a no-op, conflicting repeat is rejected |
| Approval decision | `sha256(run_id | decision | doctor_id | sha256(edited_summary or ""))` | Unique per run; a second different decision is `409 E_APPROVAL_CONFLICT` |
| Task creation | `action_key = sha256(workflow_version | patient_id | approval_decision_id | "followup_task" | "slot:1")`; `task_id = uuid5(TASK_NAMESPACE, action_key)` (derived, never regenerated); row key = `action_key` | Unique index on `follow_up_task.idempotency_key`; duplicate insert is a no-op and the stored row is returned |
| Notification | `sha256(approval_decision_id | "notification")`; id = `uuid5(TASK_NAMESPACE, key + ":notification")` | Unique index; one notification per decision |
| Audit event | `sha256(run_id | node | event_type | sequence)` | Unique index; replay cannot duplicate audit rows |

**Why the task key no longer contains `task_id` (resolves `P0-R04`).** A generated ID is not stable across a
retry, so including it allowed a second row. The key is now derived **only** from immutable, already-persisted
values: the workflow version, the patient, and the approval decision ID, plus a fixed task slot. The task UUID
is then derived from that key, so a replay computes the identical row identity. `TaskDraft.action_key` and
`TaskDraft.task_id` are both required (non-optional) fields.

### 7.1 Decision → finalize state sequence

```text
awaiting_decision --resume(approve|edit)--> finalizing --finalize--> completed
awaiting_decision --resume(reject)--------> completed            (no task, no notification)
```

`create_in_app_task`'s precondition is **`status == finalizing`** (not `awaiting_decision`), which is only
reachable after the approval decision row has **committed**. A tool call attempted in any other state returns
`E_APPROVAL_REQUIRED` or `E_RUN_NOT_PAUSED`.

### 7.2 Two-phase finalize (resolves `P0-R09`)

The app DB and the LangGraph checkpoint DB are **separate SQLite files with no shared transaction**. This
contract therefore never asserts an atomic span across both; it asserts two ordered app-DB transactions and
an idempotent replay:

| Phase | Transaction scope (app DB only) | Durability consequence |
|---|---|---|
| **A — decision** | INSERT `approval_decision` **and** UPDATE `workflow_run.status = 'finalizing'`, in one transaction. The decision `id` (UUIDv4) is generated inside this transaction and is the value `action_key` consumes. | Commit is the moment a decision "exists". Before it, no decision was made — a client retry is a normal first attempt. After it, the decision is immutable (unique per run; a different second decision is `409 E_APPROVAL_CONFLICT`). |
| **B — finalize** | INSERT `follow_up_task` + `in_app_notification` + audit `workflow.run.completed` **and** UPDATE `status = 'completed'`, in one transaction. Keys are derived from the **already committed** decision. | Replay-safe: `follow_up_task.idempotency_key` / `action_key` is unique, so a repeated phase B is a no-op returning the stored rows. |

Ordering rule: **the checkpoint for `finalize_actions` is written after phase B commits.** A checkpoint can
therefore claim `finalizing` while phase B has not run (crash), but it can never claim `completed` unless the
task row exists. Status is still read from the app DB, not from the checkpoint.

### 7.3 Restart reconciliation (the authoritative algorithm)

On every process start, and on every resume request, the service runs this ordered reconciliation **before**
touching the graph. It reads `workflow_run.status` and the `approval_decision` row from the app DB; the
checkpoint is consulted only for the last completed node.

| # | App-DB facts (source of truth) | Checkpoint may say | Action | Result |
|---|---|---|---|---|
| 1 | no run / run `completed` | anything | return the stored result (`200`); do not resume; no new task | idempotent read |
| 2 | `awaiting_decision`, **no** decision row | `awaiting_decision` | normal interrupted resume: wait for a decision, or apply the incoming one via phase A | exactly one decision |
| 3 | `awaiting_decision`, decision row present | `awaiting_decision` | impossible via phase A alone (they commit together), but reconciled defensively: promote status to `finalizing`, audit `workflow.reconciled`, continue at row 4 | no duplicate |
| 4 | `finalizing`, decision row present | `awaiting_decision` or `finalizing` (**lagging**) | expected crash window: run phase B directly from the stored decision (idempotent), then mark `completed`. No re-interrupt, no second task | exactly one task |
| 5 | `finalizing`, **no** decision row | `finalizing` or `completed` (**checkpoint ahead**) | divergence: the checkpoint is not authority. Discard the optimistic checkpoint status, rewind the run to `awaiting_decision`, write audit `workflow.checkpoint.diverged` (`E_CHECKPOINT_DIVERGENCE`), and **never** create a task | zero tasks, doctor re-decides |
| 6 | `failed_retryable` | any | resume from the last completed node recorded in the checkpoint; `retry_counts` persisted in the app DB bound the attempt | bounded retry |
| 7 | `needs_verification` | `needs_verification` | resume only after the blocking facts are verified; otherwise re-interrupt, no side effects | no side effect |

Crash-window table (all six windows, and what a restart does):

| Crash point | Rows written | Checkpoint | Restart behaviour (§7.3 row) |
|---|---|---|---|
| before phase A commits | none | `awaiting_decision` | decision never existed; client may retry (row 2) |
| after phase A, before the approval checkpoint write | decision + `finalizing` | `awaiting_decision` | row 4 — finalize once |
| during phase B (task inserted, notification not) | partial (transaction rolled back) | `finalizing` | row 4 — phase B replayed; unique keys make it whole |
| after phase B commits, before the finalize checkpoint write | task + notification + `completed` | `finalizing` | row 1 — return stored result |
| after phase B, checkpoint written, before the HTTP response | complete | `completed` | row 1 |
| checkpoint advanced without the app-DB commit (only possible through manual DB surgery or file swap) | none | `completed` | row 5 — divergence, zero tasks, audited |

Guarantees to test (`REQ-GRAPH-04`, P7): `RESUME-01..05` in `EVALUATION_MATRIX.md`.

1. Double-clicking "Approve" produces one decision and one task (`RESUME-01`).
2. Kill the API after phase B commits but before the response, then restart: no second task (`RESUME-02`).
3. Kill the API after phase A commits but before the checkpoint write, then restart: exactly one task (`RESUME-04`).
4. Replace the checkpoint with a stale/absent one while the decision exists: still exactly one task (`RESUME-04`).
5. Force a checkpoint that claims `completed` with no decision row: zero tasks, run rewound to `awaiting_decision`, divergence audited (`RESUME-05`).
6. Replaying the same `POST /workflows/follow-up` with the same body and `Idempotency-Key` returns the same `run_id` (`RESUME-03`).
7. Rejection can never create a task (no key exists for it).

## 8. Validation, bounds and defensive limits

| Bound | Value (demo default) | Rationale |
|---|---|---|
| `document_ids` per run | 5 | Small demo scope |
| `observation_ids` per run | 20 | Prevents unbounded state |
| `extraction_facts` | 40 | 5 declared fields × pages ceiling |
| `verified_facts` | 20 | Downstream usability |
| `review_flags` | 20 | De-duplicated |
| `claims` in a draft | 20 | Bounded output |
| Free text per field | 300–4000 chars by field | Prompt/size control |
| `retry_counts[node]` | ≤ 5 | Loop prevention |
| `events` | 40 | Trace size |
| `extraction_attempts` | 10 | Typed triage input (2 per document, 5 documents) |
| Upload size / page count | set in `API_CONTRACT.md` | Resource protection |

Additional invariants:

1. `patient_id` and `doctor_id` in state must equal the authenticated request identity; a mismatch is `E_SCOPE_VIOLATION` (`REQ-SEC-01`).
2. `verified_facts[].verified_by` must be a doctor identity; `ACT-SYS` cannot supply it.
3. Every `VerifiedFact` has ≥ 1 evidence reference (`REQ-VERIFY-01`).
4. `ReviewFlag.dedupe_key = sha256(patient_id | rule_id | sorted(evidence keys) | trust_basis)`; duplicates collapse.
5. State is rejected (not repaired) if it violates the schema; recovery is resume from the last valid checkpoint, never a best-effort cast.
6. `verification_issues` may contain only `VI-001..VI-006`; `review_flags` may contain only `DR-001/003/005/006/008/009`.
   The retired IDs `DR-002/004/007/010` are schema-invalid (`P0-R03`).
7. Every `ObservationView` has a `trust_level`; `doctor_verified` requires `verified_by` + `verified_at`, and
   `self_reported_validated` must have both null (`REQ-DATA-04`).
8. `as_of_utc` is immutable for the lifetime of a run and is the only clock used by `DR-001`/`DR-003` (`REQ-OPS-04`).
9. `TaskDraft.action_key` and `TaskDraft.task_id` are required and must satisfy
   `task_id == uuid5(TASK_NAMESPACE, action_key)` (`P0-R04`).
10. `NodeEvent.detail` is present **iff** the node is N1a/N2/N5a/N7, and its `kind` matches that node
    (`P0-R08`). Any detail payload containing a raw document string, a patient name, or a free-form note is
    schema-invalid; `attempt_index` ∈ {1,2} and `attempt` ≤ 5.
11. `extraction_attempts[].engine_confidence` is `null` when the engine reported none; a fabricated confidence
    is a data-quality defect. Triage never reads the document itself (`P0-R08`).
12. Run status, the approval decision, tasks and notifications are read from the **app DB**; a checkpoint that
    disagrees is reconciled per §7.3 and never trusted for status (`P0-R09`).
13. `mapping_version` is immutable per run and must satisfy `^map-\d+\.\d+\.\d+$` (`MappingVersion`); an
    observation may only be created from a verified fact whose normalized test name **and** unit appear in the
    closed table for that `mapping_version` (`P0-R10`, `P0-R12`, `REQ-DATA-05`).
13a. **One measurement tuple per document** (`P0-R14`): a document contributes at most one
    `(test_name, value, unit)` mapping candidate. A document whose verified facts hold more than one distinct
    measurement tuple is not mapped at all; it raises a blocking `VI-002` with
    `reason_code=multi_measurement_document` and stays document-only until exactly one tuple is verified. The
    rule is a **declared limitation for this MVP**, not an extraction feature. Asserted by `MAP-01`.
14. Observations handed to `compare_observations` pass the admissibility predicate
    (`TOOL_CONTRACTS.md` §3.4): `validation != rejected`, patient scope match, unit equals the measure's unit,
    parseable `measured_at`. `self_reported_validated` is **admissible and labelled**, never promoted
    (`P0-R11`).

## 9. Traceability of this contract

| Contract section | Requirement | Planned verification |
|---|---|---|
| State models, caps | `REQ-GRAPH-01` | Schema unit tests (P5) |
| Verified-only gate | `REQ-SEC-04` | Negative integration test: pending fact in draft → rejected (P5) |
| Interrupt/resume | `REQ-GRAPH-02/03` | Restart-mid-approval test with one task only (P7) |
| Retry policy | `REQ-GRAPH-04` | Simulated timeout/DB-busy tests (P5/P7) |
| Idempotency | `REQ-GRAPH-04`, `REQ-TASK-01` | Duplicate-request and double-approve tests (P7) |
| Trace events | `REQ-AUDIT-01` | Run timeline assertions (P6/P7) |
| Typed trace detail (`triage`/`validation`/`gate`/`finalize`) | `REQ-AUDIT-01`, `REQ-GRAPH-01` | `AD-01` schema assertions on `events[].detail` (P5) |
| Restart reconciliation vs checkpoint | `REQ-GRAPH-04`, `REQ-TASK-01` | `RESUME-04`, `RESUME-05` (P7) |
| Closed fact → observation mapping | `REQ-DATA-05` | `MAP-01`, plus per-case expectations in `GOLD_FIXTURES.md` (P3/P4) |
| Observation admissibility predicate | `REQ-DATA-04`, `REQ-MON-01` | `TRUST-02`, `NEG-19`, `RULE-03` (P4) |
| Trust levels on observations | `REQ-DATA-04` | `TRUST-01`, `NEG-19` (P4/P7) |
| Injected as-of clock | `REQ-OPS-04` | `RULE-08` (P4) |
| Bounded path selection (`extraction_triage`, `draft_validation`) | `REQ-GRAPH-01`, ADR-0006 | `AD-01` (P5, demonstrated P8) |

## 10. Bounded decision-making (agentic depth)

The graph contains two genuine, observable decision loops that are **not** simple function chaining:
`extraction_triage` (chooses a tool path from typed attempt metadata and retries preprocessing, bounded at 2)
and `draft_validation` (accepts, repairs once, or falls back). Both are deterministic routers over typed
evidence, both emit a typed `detail` payload in the trace (`P0-R08`), and neither can bypass verification or approval. ADR-0006 §4–§6 defines the semantics,
the trade-off, and the acceptance test `AD-01`; the demo shows one selection (`DEMO_SCENARIOS.md` step C2a).

## 11. Explicit non-goals of this contract

- No autonomous re-planning, self-critique loops, or agent-created subgraphs.
- No free-roaming multi-LLM conversation, and no self-modifying tool allowlist.
- No model-controlled routing: every edge predicate is a deterministic function of typed state.
- No cross-run memory, no long-term semantic memory, no vector store.
- No multi-user concurrency guarantees.
- No clinical prioritization: `workflow_hint` is ordering metadata, not severity.
- No silent recovery that drops evidence to "make it work".


## P5-F1 non-graph gate boundary (owner-ratified design, PR #32)

The separate internal `evaluate_run_verification_gate` F1 service operates on a real F0 `workflow_run.id` and its immutable selected-source manifest. It is **NOT** node N2, does not write `NodeEvent` or checkpoints, and does not transition `workflow_run.status` out of `queued`. Its frozen `RunGateReceipt` carries `run_id,patient_id,doctor_id,gate_version,input_fingerprint_sha256,decision,issues,historical_excluded_vi002_ids,blocking_fact_count,unavailable_reason,replayed,gate_evaluated=True,runtime_evaluable=False`. `decision` is `proceed/halt/unavailable`; `proceed` means only that this bounded internal preflight saw no known blockers in the inspected synthetic snapshot, **not** approval to evaluate DR rules or generate an agent draft. Only a later separately approved F2 may build trusted `EvaluableReviewEvidenceV2` after independent recheck.

The gate's read/write transaction is SQLite `BEGIN IMMEDIATE` on a fresh session; stable run/doc/observation/omission/fact/decision/issue/source-SHA state is fingerprinted, and a repeat matching source fingerprint reuses the same immutable gate result. File bytes are checked against stored SHA and checked again near DB commit; the filesystem is not atomically locked with SQLite, so **F2 MUST recheck** byte identity and all relevant state. Missing or altered bytes, unsupported version, changed selection or unproven lineage never yield `proceed`. The original P3 issue ledger, including OPEN terminal `VI-002`, is never updated by F1. `self_reported_validated` remains a distinct admissible trust class, not clinician verification.

**Invariant:** F1 output alone never sets `run_gate_completed=True` on a graph or P4 adapter, never marks `runtime_evaluable=True`, never creates `review_item`, audit exceptions or tasks, and does not imply any real OCR glyph fidelity. P3 `GOLD-EX-11 FAIL / NOT PROVEN` remains disclosed, and this remains a synthetic educational demo, **NOT FOR CLINICAL USE**.

## P5-F2 immutable run-bound evidence: non-executable bridge (separate reviewed scope)

`backend/app/schemas/p5_review_evidence.py` defines the strict frozen `EvaluableReviewEvidenceV2` DTO and typed `VerifiedFactV2`, `ObservationV2`, `ComparisonV2` and `EvidenceExclusionV2` values. It contains the persisted F0 run identity/clock/versions and F1 gate decision identity/fingerprint; the server-only `build_run_evaluable_review_evidence` refuses a stale/missing F1 PROCEED or altered selected provenance. F2 uses a fresh session with `BEGIN IMMEDIATE` and **rollback even on success**, and obtains an already-existing F1 result through `inspect_current_run_gate_locked`, a read-only branch of F1's *same* recomputation/immutable blocker comparison. It never invokes the write-capable F1 evaluator to manufacture a new decision.

F0-selected document facts must pass the existing persisted doctor-decision preflight; corrected originals remain only historical provenance and are never silently promoted. F0-selected observations (0..6 for this adapter; 7..20 fail) are current; the fixed 365-day ≤100 scoped observational history is used only for deterministic comparisons, with explicit exclusions, `no_baseline`, and correct `self_reported_validated` versus `doctor_verified` trust derivation. No source value conversion or clinical rule is permitted. If no current selection, comparison inputs are empty and `no_current_selected` is recorded. Bridge fingerprints include gate, run, selected fact references, observation values, comparisons and excluded history.

**Non-bypassable boundary:** `bridge_validated=true` describes a typed source snapshot, **not** graph readiness. The DTO always keeps `runtime_evaluable=false`, `policy_status=unapproved`, `rules_executed=false` and does not update `workflow_run.status`, transition N2, persist DR, create a task or call an LLM. Future F2/P4 consumers cannot trust an old V2 object across database/filesystem changes; repeated authoritative fresh verification is compulsory. SQLite does not atomically pin upload files. P4 stays `IN_REVIEW`, original P3 `GOLD-EX-11 FAIL / NOT PROVEN`, local synthetic academic scope, **NOT FOR CLINICAL USE**.
