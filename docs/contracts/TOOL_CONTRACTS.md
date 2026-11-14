# Agent Tool Contracts

| Field | Value |
|---|---|
| Document ID | `CTR-TOOL-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — allowlist proposal, not implemented** |
| Phase | `P0` (design). Implementation: P3–P6 |
| Related | `REQ-GRAPH-05`, `REQ-LLM-02`, `REQ-SEC-02/03/04`, ADR-0006, ADR-0005 |

---

## 1. Principles

1. **Allowlist only.** A node may call only the tools in its row of `STATE_AND_GRAPH_CONTRACT.md` §4.1. Unknown tool name → `E_TOOL_NOT_ALLOWED`, audit event, no retry.
2. **Narrow signatures.** Tools accept IDs and typed options, never raw SQL, URLs, shell strings, file paths, or credentials.
3. **Scope server-side.** Every tool resolves `patient_id` from the run context, not from arguments. There is no `patient_id` parameter an agent can set freely.
4. **Deterministic by default.** Of the ten tools, seven are pure reads or deterministic computations; one is model-backed (`draft_grounded_summary`); one persists unverified candidate facts (`extract_document`); and **only one mutates durable follow-up state** (`create_in_app_task`).
5. **Explicit side effects.** Only idempotent, in-app writes are permitted. No network egress, no messaging, no file deletion.
6. **Bounded.** Every tool has a timeout, an output cap, and a typed error. Tools return data, never instructions.

## 2. Common envelope

Every tool returns a discriminated result:

```python
# PROPOSAL ONLY
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str            # E_TOOL_NOT_ALLOWED | E_NOT_FOUND | E_SCOPE_VIOLATION | E_UNVERIFIED_FACT
                         # | E_UNSUPPORTED_MEDIA | E_PARSE_FAILED | E_TIMEOUT | E_DEPENDENCY_MISSING
                         # | E_RULE_POLICY_INVALID | E_MODEL_UNAVAILABLE | E_DUPLICATE_IGNORED
    message: str         # <=300 chars, no document body, no secrets
    retryable: bool

class ToolResult(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    data: T | None = None
    error: ToolError | None = None
    duration_ms: int
```

Invariants: `ok=True ⇒ error is None` and `ok=False ⇒ data is None`; every call is recorded in the run trace with name, duration, and outcome class (not payload).

## 3. Tool catalogue

### 3.1 `get_document_pages` — read-only

| Field | Value |
|---|---|
| Owner node | `medical_document`, `intake_validate` |
| Input | `document_id: Uuid`, `page_from: int = 0`, `page_to: int ≤ 9` |
| Output | `list[{page_index, width_px, height_px, has_text_layer: bool, text_excerpt: str ≤ 1500}]` |
| Side effects | none |
| Timeout / cap | 3 s; ≤ 10 pages, ≤ 15 000 chars |
| Errors | `E_NOT_FOUND` (not in run scope), `E_SCOPE_VIOLATION`, `E_PARSE_FAILED`, `E_UNSUPPORTED_MEDIA` |
| Notes | Returns text excerpts for extraction only; **never** interpreted as instructions (`REQ-SEC-02`). |

### 3.2 `extract_document` — read-only computation

| Field | Value |
|---|---|
| Owner node | `medical_document` |
| Input | `document_id: Uuid`, `fields: list[Literal["report_date","test_name","value","unit","reference_text"]]` |
| Output | `list[ExtractedFact]` with `verification_status="pending"` always, plus `page_index`, `char_start/end`, `raw_text`, `quality_flags` |
| Side effects | persists extraction attempts + facts (candidate, unverified) |
| Timeout / cap | 20 s per document; ≤ 5 pages OCR; ≤ 40 facts |
| Errors | `E_UNSUPPORTED_MEDIA`, `E_PARSE_FAILED`, `E_TIMEOUT`, `E_DEPENDENCY_MISSING` (Tesseract missing) |
| Notes | Text-first (`pypdf`); OCR fallback only when the page text layer is insufficient. The returned facts are **never** verified. |

### 3.3 `validate_structured_fields` — pure

| Field | Value |
|---|---|
| Owner node | `medical_document` |
| Input | `facts: list[ExtractedFact]` |
| Output | `list[{fact_id, quality_flags, requires_human: bool, reason_code}]` |
| Side effects | none |
| Errors | `E_VALIDATION` (schema), never raises on clinically odd but well-formed values |
| Notes | Flags ambiguous dates/units, conflicting duplicates, values outside the *demo plausibility* band (a data-quality heuristic, not a medical judgement). |

### 3.4 `read_observations` — read-only

| Field | Value |
|---|---|
| Owner node | `patient_monitoring`, `intake_validate` |
| Input | `measure_types: list[str] ≤ 4`, `from_iso: Iso`, `to_iso: Iso`, `only_verified: bool = True` |
| Output | `list[ObservationView]` scoped to the run's patient |
| Side effects | none |
| Timeout / cap | 2 s; ≤ 100 rows (most recent first) |
| Errors | `E_SCOPE_VIOLATION`, `E_VALIDATION` |
| Notes | Cannot be called with another patient's ID: there is no such parameter. |

### 3.5 `compare_observations` — pure

| Field | Value |
|---|---|
| Owner node | `patient_monitoring` |
| Input | `current: list[ObservationView]` (≤ 6), `baseline_lookback_days: int ≤ 365` |
| Output | `list[ComparisonResult]` including `comparable`, `delta`, and `incomparable_reason` |
| Side effects | none |
| Errors | `E_VALIDATION`, `E_UNVERIFIED_FACT` if a non-verified observation is passed |
| Notes | No unit conversion and no imputation (`REQ-MON-02`). A unit mismatch is reported, not reconciled. |

### 3.6 `read_verified_facts` — read-only

| Field | Value |
|---|---|
| Owner node | `review_priority`, `doctor_communication`, `follow_up`, `fact_verify_gate` |
| Input | `fact_ids: list[Uuid] | None`, `document_ids: list[Uuid] | None` |
| Output | `list[VerifiedFact]` (only `verification_status="verified"`) |
| Side effects | none |
| Errors | `E_SCOPE_VIOLATION`, `E_NOT_FOUND` |
| Notes | Returns an empty list rather than pending facts. Callers must treat empty as "no evidence", never as "normal". |

### 3.7 `evaluate_demo_review_rules` — pure, versioned

| Field | Value |
|---|---|
| Owner node | `review_priority` |
| Input | `verified_facts: list[VerifiedFact]`, `comparisons: list[ComparisonResult]`, `policy_version: str` |
| Output | `list[ReviewFlag]` with `rule_id`, `reason_code`, `workflow_hint`, neutral `message`, `evidence`, `dedupe_key`, `demo_only=True` |
| Side effects | none in the engine; the node persists flags via the service layer |
| Errors | `E_RULE_POLICY_INVALID`, `E_UNVERIFIED_FACT`, `E_VALIDATION` |
| Notes | Deterministic and side-effect free: the same input and `policy_version` always produce the same ordered output. No LLM involvement (`REQ-RULE-01`). |

### 3.8 `draft_grounded_summary` — model-backed, bounded

| Field | Value |
|---|---|
| Owner node | `doctor_communication` |
| Input | `verified_facts: list[VerifiedFact]` (≤ 20), `comparisons: list[ComparisonResult]` (≤ 20), `review_flags: list[ReviewFlag]` (≤ 20), `tone: Literal["neutral_doctor_facing"]`, `max_claims: int ≤ 20` |
| Output | `DraftSummary` with `provider`, `model`, `execution_status`, `prompt_version`, `claims[]` (each with ≥ 1 evidence ref), `uncertainties`, `not_asserted`, fixed `disclaimer` |
| Side effects | persists the draft and model metadata; no external call beyond `127.0.0.1:11434` |
| Timeout / cap | configurable, default 45 s; ≤ 1500 output tokens; one repair attempt |
| Errors | `E_MODEL_UNAVAILABLE` → fallback path, `E_TIMEOUT` → fallback after retry, schema violation → one repair then fallback |
| Notes | The tool may **not** add facts, change numbers, cite a document it was not given, or address the patient. Output validation drops any claim whose evidence is not in the provided set. |

### 3.9 `create_in_app_task` — mutating, idempotent

| Field | Value |
|---|---|
| Owner node | `follow_up` |
| Input | `approval_decision_id: Uuid`, `title: str ≤ 160`, `due_date: date?`, `note: str ≤ 500`, `notification_text: str ≤ 240` |
| Preconditions | run `status` paused at the approval interrupt; `approval.decision ∈ {approve, edit}`; `doctor_id` authenticated; patient in scope; title/note contain no prohibited clinical content patterns (see safety doc) |
| Output | `{task_id, notification_id, created: bool, duplicate_ignored: bool}` |
| Side effects | inserts one `follow_up_task` + one `in_app_notification` + audit events |
| Idempotency | key = `sha256(workflow_version | patient_id | approval_decision_id | "task" | task_id)`; duplicate → `created=false, duplicate_ignored=true`, HTTP-equivalent success without a new row |
| Errors | `E_APPROVAL_REQUIRED`, `E_SCOPE_VIOLATION`, `E_VALIDATION`, `E_DUPLICATE_IGNORED` |
| Notes | There is no delivery channel: the "notification" is a row. Nothing leaves the machine (`ADR-0005`). |

### 3.10 `list_due_tasks` — read-only

| Field | Value |
|---|---|
| Owner node | `follow_up` |
| Input | `within_days: int ≤ 30`, `status: Literal["open","completed"] = "open"` |
| Output | `list[{task_id, patient_id (scoped), title, due_date, status}]` |
| Side effects | none |
| Errors | `E_SCOPE_VIOLATION` |
| Notes | Doctor-scoped only; a patient cannot enumerate tasks (`US-11`). |

## 4. Explicitly denied capabilities

These must not exist as tools, helper functions, or TODO stubs (`REQ-SEC-03`):

| Denied | Why |
|---|---|
| `send_email` / `send_sms` / `send_whatsapp` / `push_notification` | Real-world side effects (ADR-0005) |
| `http_request` / `web_search` / `fetch_url` | Egress, injection surface, paid/unsafe dependency |
| `run_sql` / `execute_python` / `run_shell` | Unbounded capability; agents talk to typed tools only |
| `prescribe` / `set_dosage` / `recommend_treatment` | Forbidden medical authority |
| `set_review_flag` (agent-authored severity) | Rules only, deterministic and versioned |
| `approve` / `sign_off` / `resolve_approval` | Human-only authority |
| `delete_patient` / `delete_document` / `export_dataset` | Destructive or privacy-risky |
| `read_all_patients` / `search_patients` | Cross-patient exposure |
| `download_model` / `pull_model` | Supply-chain and disk risk; owner-driven only |

A test at P7 asserts no such symbol or outbound dependency exists (`SEC-03`).

Orchestrator nodes (`intake_validate`, `fact_verify_gate`, `clinician_approval`, `halted`) read through the
domain service layer and hold no agent tools; the allowlist below applies to the five agent nodes only.

## 5. Tool permission matrix

| Tool | `medical_document` | `patient_monitoring` | `review_priority` | `doctor_communication` | `follow_up` |
|---|---|---|---|---|---|
| `get_document_pages` | ✅ | – | – | – | – |
| `extract_document` | ✅ | – | – | – | – |
| `validate_structured_fields` | ✅ | – | – | – | – |
| `read_observations` | – | ✅ | – | – | – |
| `compare_observations` | – | ✅ | – | – | – |
| `read_verified_facts` | – | – | ✅ | ✅ | ✅ |
| `evaluate_demo_review_rules` | – | – | ✅ | – | – |
| `draft_grounded_summary` | – | – | – | ✅ | – |
| `create_in_app_task` | – | – | – | – | ✅ |
| `list_due_tasks` | – | – | – | – | ✅ |

## 6. Error, audit and observability rules

1. Every failed call produces a typed `AgentError` in state and an audit event; failures never mutate clinical data.
2. Tool errors surfaced to users are mapped to `API_CONTRACT.md` codes; internal details stay in logs without document text.
3. The run trace records tool name, duration, outcome, and evidence IDs — not payload bodies, not prompts, not document text.
4. Retries follow `STATE_AND_GRAPH_CONTRACT.md` §6; mutating tools are retried only via their idempotency key.
5. A missing dependency (Tesseract, Ollama) is a first-class `E_DEPENDENCY_MISSING`/`E_MODEL_UNAVAILABLE`, never a crash and never a silent substitution.

## 7. Open questions

| ID | Question | Default |
|---|---|---|
| `OQ-T01` | Should `extract_document` support multi-document batches in one run? | No; one document per run in the demo |
| `OQ-T02` | Is a manual "raise for review" note needed for the doctor? | Deferred to P6 UI; not an agent tool |
| `OQ-T03` | Should task creation also schedule a next check-in date? | No; the doctor sets a due date manually |
