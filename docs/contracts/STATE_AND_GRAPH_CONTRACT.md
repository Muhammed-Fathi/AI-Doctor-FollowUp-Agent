# Shared State and Graph Contract (LangGraph)

| Field | Value |
|---|---|
| Document ID | `CTR-STATE-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — proposal, not implemented** |
| Phase | `P0` (design). Implementation: P5 |
| Related | `REQ-GRAPH-01..05`, `REQ-LLM-02`, `REQ-RULE-03`, ADR-0006 |
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
| `policy_version` | Version of the demo rule policy file | `demo-policy-1.0.0` |
| `prompt_version` | Version tag of the draft prompt/template | `draft-v1` |
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


class ObservationView(Strict):
    observation_id: Uuid
    patient_id: Uuid
    measure_type: Literal["systolic_bp", "diastolic_bp", "heart_rate", "glucose"]
    value: float
    unit: Literal["mmHg", "bpm", "mg/dL"]
    measured_at: Iso
    source: Literal["patient_checkin", "verified_document"]
    validation: Literal["ok", "ok_with_warning", "rejected"]
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
    incomparable_reason: Literal["no_baseline", "unit_mismatch", "stale_baseline", "missing_timestamp"] | None = None
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)


class ReviewFlag(Strict):
    review_item_id: Uuid
    rule_id: str = Field(pattern=r"^DR-\d{3}$")
    reason_code: str = Field(max_length=64)
    workflow_hint: Literal["data_quality", "verification_needed", "change_to_review"] | None = None
    message: str = Field(max_length=240)          # neutral wording, no clinical interpretation
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
    task_id: Uuid | None = None
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


class NodeEvent(Strict):
    node: str
    started_at: Iso
    ended_at: Iso | None = None
    outcome: Literal["ok", "halted", "interrupted", "retried", "failed"] | None = None
    tools_called: list[str] = Field(default_factory=list, max_length=6)


class SharedGraphState(Strict):
    # identity
    run_id: Uuid
    thread_id: Uuid
    workflow_version: SemVer
    state_schema_version: SemVer
    policy_version: str
    prompt_version: str
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
    verified_facts: list[VerifiedFact] = Field(default_factory=list, max_length=20)
    observations: list[ObservationView] = Field(default_factory=list, max_length=20)
    comparisons: list[ComparisonResult] = Field(default_factory=list, max_length=20)

    # agent outputs
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
- `message` on `ReviewFlag` is restricted to neutral, non-clinical wording; see `docs/clinical-safety/DEMO_REVIEW_RULES.md` §5.
- `disclaimer` is a fixed literal, so a draft cannot exist without the educational label (`REQ-SEC-05`).

## 4. Nodes, reads/writes, and transitions

### 4.1 Node table

| # | Node (agent) | Reads | Writes | Tools (allowlist) | May interrupt? |
|---|---|---|---|---|---|
| N0 | `intake_validate` (orchestrator) | run request, scope | `observations`, `document_ids`, `status` | none — service-layer reads only | no |
| N1 | `document_extract` (`medical_document`) | `document_ids` | `extraction_facts` | `extract_document`, `get_document_pages`, `validate_structured_fields` | no |
| N2 | `fact_verify_gate` (orchestrator, deterministic) | `extraction_facts` | `verified_facts`, `status`, `halt_reason` | none — service-layer reads only | **yes** (halt `needs_verification`) |
| N3 | `monitor_compare` (`patient_monitoring`) | `verified_facts`, `observations` | `comparisons` | `read_observations`, `compare_observations` | no |
| N4 | `review_rules` (`review_priority`) | `verified_facts`, `comparisons` | `review_flags` | `read_verified_facts`, `evaluate_demo_review_rules` | no |
| N5 | `draft_summary` (`doctor_communication`) | `verified_facts`, `comparisons`, `review_flags` | `draft_summary`, `model_metadata` | `read_verified_facts`, `draft_grounded_summary` | no |
| N6 | `clinician_approval` (orchestrator) | `draft_summary`, `review_flags` | `approval`, `status` | none — service-layer reads only | **yes** (interrupt `awaiting_decision`) |
| N7 | `finalize_actions` (`follow_up`) | `approval` (must be approved/edited) | `pending_tasks`, `created_task_ids`, `status` | `create_in_app_task`, `list_due_tasks` | no |
| N8 | `halted` (orchestrator) | any | `status`, `halt_reason` | none | terminal-for-now, resumable |

### 4.2 Transition graph

```mermaid
stateDiagram-v2
    [*] --> intake_validate
    intake_validate --> document_extract: documents present and scoped
    intake_validate --> monitor_compare: no documents
    intake_validate --> failed_terminal: scope or schema invalid
    document_extract --> fact_verify_gate
    document_extract --> failed_retryable: extraction transient failure
    document_extract --> failed_terminal: unsupported or corrupt file
    fact_verify_gate --> monitor_compare: all blocking facts verified
    fact_verify_gate --> needs_verification: pending or rejected facts
    needs_verification --> fact_verify_gate: resume after doctor verification
    monitor_compare --> review_rules
    review_rules --> draft_summary
    draft_summary --> clinician_approval: draft ok or fallback
    draft_summary --> failed_retryable: model timeout after retry
    clinician_approval --> awaiting_decision: interrupt
    awaiting_decision --> finalize_actions: resume approve or edit
    awaiting_decision --> completed: resume reject - no task
    finalize_actions --> completed: tasks and audit written
    failed_retryable --> [*]: resumable halt
    failed_terminal --> [*]
    completed --> [*]
```

Routing rules:

1. Conditional edge decisions are **deterministic functions of state**, never model output (`REQ-GRAPH-01`).
2. `fact_verify_gate` blocks the pipeline when any fact that a downstream node would consume is `pending` or `rejected`. Non-blocking informational facts may remain pending only if no downstream node reads them; the gate lists what blocks.
3. `draft_summary` may proceed on fallback (labelled); it may **not** proceed if it would fabricate to fill a gap.
4. `finalize_actions` is unreachable unless `approval.decision in {approve, edit}` **and** `approval.doctor_id` matches an authenticated doctor with patient scope. `reject` routes straight to `completed` with no task (`US-10`).
5. Every node appends exactly one `NodeEvent` on entry/exit; the trace is part of the demo evidence.

## 5. Checkpoint, interrupt and resume

### 5.1 Checkpoint policy

- Checkpointer: `langgraph-checkpoint-sqlite` on a dedicated SQLite file (ADR-0003).
- A checkpoint is written **after** each node completes and **before** each interrupt is surfaced.
- `thread_id == run_id`; one thread per run, never reused across patients.
- Sync is not forced on every node, but the approval interrupt explicitly flushes so a hard kill preserves `awaiting_decision`.
- Retention: checkpoints are runtime artifacts. Reset (`POST /api/v1/demo/reset`) deletes app DB + checkpoint DB + uploads together.

### 5.2 Interrupt contract

| Property | Rule |
|---|---|
| Where | Only N2 (`needs_verification`) and N6 (`awaiting_decision`) |
| Payload surfaced to UI | run ID, status, draft + citations, review flags + evidence, blocking facts, provider metadata, allowed actions |
| Resume input | `{run_id, decision, doctor_id (from session, never body), reason?, edited_summary?}` |
| Resume validation | run status must be the expected paused state; doctor must be authenticated and patient-scoped; `decision` must be in the allowed set; `edited_summary` capped at 4000 chars |
| Resume after verification | blocked fact IDs must now be `verified`; otherwise re-interrupt with the same reason and increment no side effects |
| Idempotent resume | Resuming a run already `completed` returns the stored result with `200` and no new task (no `409` loop) |
| Crash mid-resume | Node is not checkpointed as complete until its writes commit; resume recomputes deterministically and the unique idempotency index suppresses duplicates |

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
| Task creation | `sha256(workflow_version | patient_id | decision_id | "task" | task_id)` | Unique index on `follow_up_task.idempotency_key`; duplicate insert is a no-op |
| Notification | `sha256(decision_id | "notification")` | Unique index; one notification per decision |
| Audit event | `sha256(run_id | node | event_type | sequence)` | Unique index; replay cannot duplicate audit rows |

Guarantees to test (`REQ-GRAPH-04`, P7):

1. Double-clicking "Approve" produces one approval record and one task.
2. Killing the API after task commit but before the response, then resuming, produces no second task.
3. Replaying the same `POST /workflows/follow-up` with the same body and `Idempotency-Key` returns the same `run_id`.
4. Rejection can never create a task (no key exists for it).

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
| Upload size / page count | set in `API_CONTRACT.md` | Resource protection |

Additional invariants:

1. `patient_id` and `doctor_id` in state must equal the authenticated request identity; a mismatch is `E_SCOPE_VIOLATION` (`REQ-SEC-01`).
2. `verified_facts[].verified_by` must be a doctor identity; `ACT-SYS` cannot supply it.
3. Every `VerifiedFact` has ≥ 1 evidence reference (`REQ-VERIFY-01`).
4. `ReviewFlag.dedupe_key = sha256(patient_id | rule_id | sorted(evidence keys))`; duplicates collapse.
5. State is rejected (not repaired) if it violates the schema; recovery is resume from the last valid checkpoint, never a best-effort cast.

## 9. Traceability of this contract

| Contract section | Requirement | Planned verification |
|---|---|---|
| State models, caps | `REQ-GRAPH-01` | Schema unit tests (P5) |
| Verified-only gate | `REQ-SEC-04` | Negative integration test: pending fact in draft → rejected (P5) |
| Interrupt/resume | `REQ-GRAPH-02/03` | Restart-mid-approval test with one task only (P7) |
| Retry policy | `REQ-GRAPH-04` | Simulated timeout/DB-busy tests (P5/P7) |
| Idempotency | `REQ-GRAPH-04`, `REQ-TASK-01` | Duplicate-request and double-approve tests (P7) |
| Trace events | `REQ-AUDIT-01` | Run timeline assertions (P6/P7) |

## 10. Explicit non-goals of this contract

- No autonomous re-planning, self-critique loops, or agent-created subgraphs.
- No cross-run memory, no long-term semantic memory, no vector store.
- No multi-user concurrency guarantees.
- No clinical prioritization: `workflow_hint` is ordering metadata, not severity.
- No silent recovery that drops evidence to "make it work".
