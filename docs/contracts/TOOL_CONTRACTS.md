# Agent Tool Contracts

| Field | Value |
|---|---|
| Document ID | `CTR-TOOL-001` |
| Version | `0.3.0-p0` |
| Status | **IN REVIEW — allowlist proposal, not implemented** |
| Phase | `P0` (design). Implementation: P3–P6 |
| Related | `REQ-GRAPH-05`, `REQ-LLM-02`, `REQ-SEC-02/03/04`, `REQ-DATA-04`, ADR-0006, ADR-0005 |
| Revision | 0.3.0: observation **admissibility predicate** replacing the "non-verified observation" error (`P0-R11`), two-phase finalize + app-DB authority (`P0-R09`), typed extraction-attempt output for triage (`P0-R08`). 0.2.0 added trust-aware observation reads, deterministic task identity (`P0-R04`) and the draft-validation note |

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
    code: str            # E_TOOL_NOT_ALLOWED | E_NOT_FOUND | E_SCOPE_VIOLATION | E_UNVERIFIED_FACT (facts only)
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
| Output | `list[ExtractedFact]` with `verification_status="pending"` always, plus `page_index`, `char_start/end`, `raw_text`, `quality_flags`, `confidence`, and the extraction `path` (`pypdf`/`tesseract`) used for each page |
| Side effects | persists `extraction_attempt` rows (typed: `path`, `preprocessing`, `engine_confidence`, `text_char_count`) + facts (candidate, unverified) |
| Timeout / cap | 20 s per document; ≤ 5 pages OCR; ≤ 40 facts |
| Errors | `E_UNSUPPORTED_MEDIA`, `E_PARSE_FAILED`, `E_TIMEOUT`, `E_DEPENDENCY_MISSING` (Tesseract missing) |
| Notes | Text-first (`pypdf`); OCR fallback only when the page text layer is insufficient. Returns the confidence and path that `extraction_triage` uses for bounded retry (`ADR-0006` §3.1). The returned facts are **never** verified. |

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
| Input | `measure_types: list[str] ≤ 4`, `from_iso: Iso`, `to_iso: Iso`, `only_admissible: bool = True` (excludes `validation='rejected'`), `trust_levels: list[Literal["self_reported_validated","doctor_verified"]] = both` |
| Output | `{observations: list[ObservationView], excluded: list[{observation_id, skip_reason}]}` — scoped to the run's patient, each observation with `trust_level` and `verified_by` (null for self-reported); `skip_reason ∈ {validation_rejected, unit_mismatch, missing_timestamp, future_timestamp}` |
| Side effects | none |
| Timeout / cap | 2 s; ≤ 100 rows (most recent first) |
| Errors | `E_SCOPE_VIOLATION`, `E_VALIDATION` — **never** `E_UNVERIFIED_FACT` (observations are not facts) |
| Notes | Cannot be called with another patient's ID: there is no such parameter. `only_admissible` never returns rejected rows (`REQ-DATA-04`; `NEG-19`). `trust_levels` defaults to **both**: a validated self-reported check-in is admissible and stays labelled. |

**Admissibility predicate (`is_admissible_observation`, shared verbatim by `read_observations`,
`compare_observations`, `evaluate_demo_review_rules` and the UI; resolves `P0-R11`).** An observation is
admissible iff **all** of:

1. `validation != "rejected"` (a data check failed);
2. `patient_id` equals the run's patient (a mismatch is `E_SCOPE_VIOLATION`, not a skip);
3. `unit` equals the unit fixed for its `measure_type` (`DATA_DICTIONARY.md` §3.1);
4. `measured_at` is a parseable ISO-8601 UTC instant, and is `≤ as_of_utc + 5 min`;
5. `trust_level ∈ {self_reported_validated, doctor_verified}`.

Admissibility is **not** a doctor-verification requirement: a `self_reported_validated` observation passes and
must carry its label downstream. Inadmissible rows are excluded and reported with a
`skip_reason ∈ {validation_rejected, unit_mismatch, missing_timestamp, future_timestamp}` — never silently
dropped and never relabelled.

### 3.5 `compare_observations` — pure

| Field | Value |
|---|---|
| Owner node | `patient_monitoring` |
| Input | `current: list[ObservationView]` (≤ 6), `baseline_lookback_days: int ≤ 365` |
| Output | `list[ComparisonResult]` including `comparable`, `delta`, and `incomparable_reason` |
| Side effects | none |
| Errors | `E_VALIDATION`, `E_SCOPE_VIOLATION` (cross-patient input). **`E_UNVERIFIED_FACT` is retired for this tool** (`P0-R11`) |
| Notes | Input must already satisfy `is_admissible_observation` (§3.4). Inadmissible input is **not** an error: the tool returns `comparable=false` with `incomparable_reason="not_admissible"` plus the `skip_reason`, so a rejected row can never shift a delta. `trust_basis` is derived from the two input labels: both `doctor_verified` → `doctor_verified`; both `self_reported_validated` → `self_reported`; mixed → `mixed`. The tool may never emit or imply `doctor_verified` for an input that was self-reported, may not convert units, and may not impute a baseline (`REQ-MON-02`, `REQ-DATA-04`). |

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
| Notes | Deterministic and side-effect free: the same input and `policy_version` always produce the same ordered output. No LLM involvement (`REQ-RULE-01`). `E_UNVERIFIED_FACT` applies **only** to an `ExtractedFact`/pending fact in the input, never to an observation: observations are filtered by `is_admissible_observation` (§3.4) and `self_reported_validated` values are consumed **as labelled** (`trust_basis`), never promoted (`P0-R11`). |

### 3.8 `draft_grounded_summary` — model-backed, bounded

| Field | Value |
|---|---|
| Owner node | `doctor_communication` |
| Input | `verified_facts: list[VerifiedFact]` (≤ 20), `comparisons: list[ComparisonResult]` (≤ 20), `review_flags: list[ReviewFlag]` (≤ 20), `tone: Literal["neutral_doctor_facing"]`, `max_claims: int ≤ 20` |
| Output | `DraftSummary` with `provider`, `model`, `execution_status`, `prompt_version`, `claims[]` (each with ≥ 1 evidence ref), `uncertainties`, `not_asserted`, fixed `disclaimer` |
| Side effects | persists the draft and model metadata; no external call beyond `127.0.0.1:11434` |
| Timeout / cap | configurable, default 45 s; ≤ 1500 output tokens; one repair attempt |
| Errors | `E_MODEL_UNAVAILABLE` → fallback path, `E_TIMEOUT` → fallback after retry, schema violation → one repair then fallback |
| Notes | The tool may **not** add facts, change numbers, cite a document it was not given, or address the patient. Output validation (`draft_validation`, `ADR-0006` §3.2) drops any claim whose evidence is not in the provided set, requires `(self-reported)` wording for claims citing self-reported observations, and either accepts, repairs once, or falls back. |

### 3.9 `create_in_app_task` — mutating, idempotent

| Field | Value |
|---|---|
| Owner node | `follow_up` |
| Input | `approval_decision_id: Uuid`, `title: str ≤ 160`, `due_date: date?`, `note: str ≤ 500`, `notification_text: str ≤ 240` |
| Preconditions | run `status == finalizing` (reached only after a paused `awaiting_decision` run is resumed with a persisted `approve`/`edit` decision); `approval.doctor_id` authenticated and patient-scoped; title/note contain no prohibited clinical content patterns (see safety doc) |
| Output | `{task_id, notification_id, created: bool, duplicate_ignored: bool}` |
| Side effects | inserts one `follow_up_task` + one `in_app_notification` + audit events |
| Idempotency | `action_key = sha256(workflow_version | patient_id | approval_decision_id | "followup_task" | "slot:1")`; `task_id = uuid5(TASK_NAMESPACE, action_key)` is derived, never regenerated; duplicate → `created=false, duplicate_ignored=true`, existing row returned, no new row (`P0-R04`) |
| Atomicity | Task + notification + audit finalization + the `finalizing → completed` transition commit in **one app-DB transaction** (phase B). The approval decision and the entry into `finalizing` committed earlier, in their own transaction (phase A), because the LangGraph checkpoint file cannot join it. Replay of phase B is a no-op via the derived keys (`STATE_AND_GRAPH_CONTRACT.md` §7.2–§7.3, `P0-R09`). |
| Errors | `E_APPROVAL_REQUIRED` (wrong state or missing decision), `E_RUN_NOT_PAUSED`, `E_SCOPE_VIOLATION`, `E_VALIDATION`, `E_DUPLICATE_IGNORED` |
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

Orchestrator nodes (`intake_validate`, `extraction_triage`, `fact_verify_gate`, `draft_validation`,
`clinician_approval`, `halted`) read through the domain service layer and hold no agent tools; the allowlist
below applies to the five agent nodes only.

`fact_verify_gate` calls the deterministic domain service `collect_verification_issues` (not an agent tool):
input = candidate facts + document↔patient reference + existing admissible observations; output =
`VerificationIssue[]` (`VI-001..VI-006`), never `ReviewFlag`. This service cannot write verified facts — only a
doctor decision does that.

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

## P5-F2 V2 evidence bridge (separate owner-ratified code slice, read-only)

**Versioned internal proposal now implemented for review only:** `EvaluableReviewEvidenceV2`, contract `2.0.0`, is a **server-built and frozen in-process object**, not a graph, DR rule or external API. The trusted entry point is `build_run_evaluable_review_evidence(db, principal, run_id, validation_clock, upload_root)`; no caller-selected documents/current IDs, baseline lookback, gate flag, `blocking_fact_count`, `already_verified`, `policy_version` or trust-role override. It requires a current, immutable, source-fingerprinted F1 `proceed` recorded on that run, then rechecks F1 under an SQLite `BEGIN IMMEDIATE` snapshot **without writing any gate or audit rows**. The bridge also rehashes current bytes and rechecks the same F1 state at the end. Because the filesystem cannot be transactionally locked by SQLite, **all future graph/rule consumers must recheck freshness and scope again**. `bridge_validated=true` denotes only a bounded evidence-shape check; `runtime_evaluable=false`, `rules_executed=false`, `policy_status=unapproved` stay fixed.

**Additive §3.5 adapter contract:** `compare_run_observations_v2(evidence)` is the typed comparison projection carried by the envelope, computed from **F0-stored current observation IDs** and the fixed, versioned `f2-history-365d-v1` same-patient historical policy. F0 may select 0..20 observations; F2 accepts 0..6 only, refusing >6. Zero returns `comparisons=()` and `no_current_reason=no_current_selected`; it does not mean normality. History is bounded at 100 observations (overflow denies), excludes invalid/other-source rows with typed reason codes, uses the latest prior valid observation with stable tie-break and no imputation or unit conversion. The current V2 comparison maps the older P4 `missing_baseline` to `no_baseline` while preserving the original P4 class/test behavior. The trust basis is derived, never supplied. `self_reported_validated` stays labelled and never becomes `doctor_verified`.

**Additive §3.7 adapter boundary:** `prepare_run_review_inputs_v2` is the not-yet-activated conceptual P4 rule-input projection of the immutable V2 `verified_facts`, `selected_observations` and `comparisons`. In this F2 slice, **no call to `evaluate_demo_review_rules`**, no `ReviewFlag`/DR output, no `review_item` or `evidence_link` insertion and no `LangGraph` execution is permitted. These later tools require a separate P4 owner decision and independently reviewed run-bound persistence. F2's existing V2 envelope exposes only strict typed inputs and comparison results. No new endpoint or model-backed feature exists.

All earlier §3.4 admission and original §3.5/§3.7 API drafts remain unchanged: observations can be admissible as self-reported; `E_UNVERIFIED_FACT` applies only to extracted facts. Selected invalid/current facts fail closed; history exclusions are explicit. Source file SHA proves current byte agreement, **not original OCR glyph fidelity** (real P3 `GOLD-EX-11 FAIL / NOT PROVEN`). Synthetic educational only, **NOT FOR CLINICAL USE**.

## P4-RB1 internal run-bound 90-day comparison-input PREVIEW — no rule tool invocation

**Separate and non-executable from the §3.5 `compare_observations` agent tool and §3.7 `evaluate_demo_review_rules`.** Owner-ratified [P4 design PR #36](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/36#issuecomment-7075542080) authorizes only the read-only P4-RB1 scope. This additive internal server function `build_p4_run_bound_review_input_preview(db, principal, run_id, validation_clock, upload_root)` never evaluates a DR rule, creates a `ReviewFlag`, writes `review_item`/`evidence_link`, changes a workflow status or produces graph/LLM tasks. `RunBoundReviewInputPreviewV1` contains immutable identities, verified fact references, trust-labelled current observations, policy-window comparisons and explicit source exclusions, with fixed `runtime_evaluable=False`, `rules_executed=False`, `review_items_persisted=False` and `policy_status=unapproved`. It is NOT a permission to evaluate later.

**Two independent lookback contracts:** Existing F2 V2 retains `f2-history-365d-v1`, whereas owner-pinned R3-A `demo-policy-1.1.0` uses `baseline_lookback_days=90`. P4-RB1 reads the F2 reverified server-scope evidence, then independently computes the latest valid earlier value in the **90-day** window using bounded same-patient provenance in a fresh SQLite lock and pure P4 comparison logic. A 180-day F2 baseline is **not** an eligible 90-day baseline: return `comparable=False, delta=None, incomparable_reason=no_baseline`, not an imputed number. Zero run-selected current records means `policy_comparisons=()` / `no_current_selected`; >6 denies rather than silently truncating. No caller-supplied baseline, policy override or zero-blocker flag; self-reported trust labels remain unchanged.

The R3-A synthetic reference must match its canonical LF SHA-256 `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36` (uniform checkout CRLF allowed by normalization, mixed/bare CR denied), all VI-001..006 and six published DR catalogue switches on, exact `demo-policy-1.1.0`, and fixed educational fixture clock `2026-11-14T12:00:00Z`. A valid reference is **not** an active policy. F2 checks fresh selected source bytes, current F1 PROCEED and patient/doctor/decision scope before and after RB1's independently locked comparison read; separate transactions and filesystem operations are **not atomic**. Any later rule or persistence service must revalidate identity, gate, hashes, clock and provenance in its own transaction and obtain separate owner approval for RB2/RB3. P4 `IN_REVIEW`, P3 real `GOLD-EX-11 FAIL / NOT PROVEN`; **NOT FOR CLINICAL USE**.


## P4-RB2 pure offline evaluator — implementation candidate (NOT a runtime tool)

**Educational synthetic fixtures only, not clinically or operationally approved.** This append-only section specifies a *local test-invoked pure function*, not the `evaluate_demo_review_rules` agent tool in §3.7 and not an API/Graph/LLM action:

`evaluate_p4_rb2_offline_fixture(data: OfflineRuleInput) -> OfflineRuleResult`

- `OfflineRuleInput`: explicit `patient_id`, 0–6 `selected_current` typed observations, 0–100 historical typed observations, injected `as_of_utc`, exact owner-pinned R3-A `OfflineRulePolicy`, optional **synthetic test assertions** of active fact statuses. No run ID, session credential, doctor assignment, stored F1 receipt, `blocking_fact_count`, caller `run_gate_completed` or caller policy-approval authority.
- `OfflineObservation`: patient/measure/value/unit/timestamps/validation/trust/source; optional fixture-declared document and fact IDs. `lineage_status=fixture_asserted` labels *fictional* lineage. `stored_independently_verified` is rejected as a forged RB2 caller authority; a future RB3 verifier must instead query and prove the actual selected stored sources.
- `OfflineRuleResult`: frozen candidate flags with typed evidence, deterministic SHA-256 dedupe, neutral messages/trust labels, typed exclusions, `demo_only=true`, `offline_candidate_rules_evaluated=true`, `runtime_evaluable=false`, `rules_executed=false` (run sense), `review_items_persisted=false`, `policy_status=unapproved`. A DR-006 fixture candidate has `provenance_status=fixture_asserted` and is **never** a real doctor attestation.
- Strict R3-A reference-only values: `demo-policy-1.1.0`, `2026-11-14T12:00:00Z`, 90-day baseline, 30-day stale, four deltas 10/8/15/40, zero conflict tolerance, OCR reference 0.70, max 3 per type, all six `VI-*` and six active `DR-001/003/005/006/008/009`. The committed YAML is pinned and read by **tests only**, never by application runtime. Thresholds are arbitrary demo figures, not clinical guidelines.
- Input failures produce `OfflineRuleError(code,detail)` with **no partial flags**; rejected/unit-mismatched/future observations produce typed exclusions where applicable. No current selected readings yields zero candidates irrespective of historical records. Retired/unknown/disabled rule IDs fail policy validation. Cap overflow fails closed. No persistence, notifications, Graph, LLM, task, browser, real OCR or runtime invocation in RB2.
- The separate RB3 and RB4 implementations, owner acceptance and actual end-to-end evaluation remain **not approved** by this interface. The original real OCR `GOLD-EX-11 FAIL / NOT PROVEN` is unchanged. See `docs/phase-reports/P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md`.

