# ADR-0006 — Five bounded agent nodes inside one orchestrated graph

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 (v0.3 addresses PR review `5904505998` point `P0-R08`: typed trace payloads and a deterministic harness for `AD-01`) |
| Phase | P0 (design); implementation P5; demonstration P8 |
| Related | `REQ-GRAPH-01/05`, `REQ-LLM-01/02`, ADR-0001, ADR-0002 |
| Review reference | PR #2 reviews `5904454222` (agentic depth) and `5904505998` (`P0-R08`) |

## Context

The graduation requirement speaks of a "multi-agent" system with five agents. A literal implementation as five
autonomous LLM peers would multiply cost, latency, and unpredictability; it would make the doctor gate,
idempotency and audit nearly impossible to guarantee. At the same time, a graph that is merely a fixed sequence
of function calls is legitimately open to the criticism that it is *not* agentic at all.

The project must therefore answer two questions explicitly:

1. What does "agent" mean here, and what is genuinely decision-making behaviour?
2. What exactly does the system *not* do, so nobody claims autonomy it does not have?

## Decision

### 1. Structure

One LangGraph `StateGraph` with five **named, bounded agent nodes**: `medical_document`,
`patient_monitoring`, `review_priority`, `doctor_communication`, `follow_up`, plus orchestrator/router nodes
(`intake_validate`, `extraction_triage`, `fact_verify_gate`, `draft_validation`, `clinician_approval`,
`finalize_actions`, `halted`).

### 2. Semantics of "agent" (explicit definition)

An **agent node** here is a bounded component that (a) owns exactly one responsibility, (b) may call only an
allowlisted set of tools, (c) reads and writes only declared state fields, and (d) returns a typed result that
deterministically influences routing. It is **not** an independent LLM with free choice, and only
`doctor_communication` calls a model. This is stated as the accepted interpretation of the assignment wording;
if an evaluator requires five separately-prompted models, that is a **scope change** for the owner to decide,
not something this ADR assumes.

### 3. Genuine decision-making, not a fixed chain

Two mechanisms provide observable, bounded decision-making while preserving every deterministic clinical and
approval guard. Both are specified in `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §4.

#### 3.1 `extraction_triage` — bounded tool-path selection with recovery

After extraction, a deterministic router selects among three paths from **typed evidence** (text-layer coverage,
OCR confidence, attempt count, page count):

| Condition | Selected path | Recorded trace fields |
|---|---|---|
| Text layer present on all required pages | `proceed` (no OCR) | `path_selected=text_layer`, `path_reason=text_layer_available` |
| Text insufficient, OCR confidence ≥ `ocr_confidence_floor` | `proceed` | `path_selected=ocr_direct`, `path_reason=confidence_ok` |
| Text insufficient, OCR confidence < floor, attempts < 2 | `ocr_preprocess_retry` | `path_selected=ocr_preprocess_retry`, `path_reason=low_confidence` |
| Confidence still < floor, or attempts exhausted | `flag_for_human` | `path_selected=flag_for_human`, `path_reason=retry_exhausted` |

This is real tool selection with recovery: the agent chooses *how* to extract from the observed result of its
own tool call, retries with different parameters, and stops at a fixed budget. The retry cannot exceed 2, cannot
skip the verification gate, and cannot widen its own allowlist.

#### 3.2 `draft_validation` — bounded output repair

`doctor_communication` drafts in a constrained schema. A deterministic validator then either accepts,
requests **one** repair with stricter constraints (schema violation, unknown evidence citation, prohibited
content), or rejects to the labelled fallback. The chosen outcome and reason are recorded
(`validation_outcome`), so the retry loop is visible in the run trace.

#### 3.3 The trace is a typed artifact, not prose

Both decision loops emit a **discriminated, schema-checked** `detail` payload on their `NodeEvent`
(`STATE_AND_GRAPH_CONTRACT.md` §3, `openapi.phase0.yaml` `TriageEventDetail`/`ValidationEventDetail`,
`DATA_DICTIONARY.md` §2.18 `node_event`):

| Node | Payload fields | Forbidden content |
|---|---|---|
| `extraction_triage` | `path_selected`, `path_reason`, `document_id`, `attempt_index`, `engine_confidence`, `preprocessing_applied` | document text, extracted values, page content |
| `draft_validation` | `validation_outcome`, `attempt_index`, `violation_codes[]` | model output, draft text |
| `fact_verify_gate` | `decision`, `blocking_fact_count`, `issue_types[]` | fact values |
| `finalize_actions` | `approval_decision`, `task_created`, `notification_created` | note text, patient data |

The triage router's entire input is `extraction_attempts[]` — typed records of `path`, `preprocessing`,
`engine_confidence` (or `null` when the engine reports none), `text_char_count`, `succeeded`, `error_code`. It
never re-reads a document and never infers a confidence from prose, so "why did the agent choose this path" is
answerable from the DB alone (`P0-R08`).

#### 3.4 What this buys

- A trace a reviewer can read: which path, why, how many attempts, what was accepted.
- Failure recovery without human intervention *before* the doctor gate (better demo resilience).
- Determinism: identical input → identical path, because the predicates are typed-state functions.

### 4. Executable acceptance test `AD-01` (P5, demonstrated at P8)

Fixture `GOLD-EX-13` (see `docs/evaluation/GOLD_FIXTURES.md` §6) supplies a scanned report whose first OCR pass
reports confidence below the floor:

| Assertion | Expected |
|---|---|
| Path selection recorded | `path_selected=ocr_preprocess_retry`, `path_reason=low_confidence` |
| Second attempt executed | Exactly 2 extraction attempts; second uses the deterministic preprocessing path |
| Bounded | A third failure does **not** retry; it emits `VI-005` and halts `needs_verification` |
| Clean-PDF counterpart | `path_selected=text_layer`, zero OCR attempts (no needless work) |
| Guard integrity | No `DR-*` evaluation and no draft exists while any blocking fact is pending; approval still required after resume |
| Trace integrity | Both attempts plus the selection appear in `GET /workflows/{run_id}/trace` |

**Determinism boundary (added in v0.3).** `AD-01` runs against a **mocked extractor** that returns scripted
attempt metadata, so the assertions above are exact and repeatable on any machine with no OCR binary. The real
Tesseract is exercised separately as `OCR-LIVE-01` on the owner laptop, where confidence and recovered text are
**measured and recorded** (`LOCAL_BENCHMARK_PLAN.md`) rather than asserted in advance — real engine scores vary
by build, locale and rasterization, and a contract test must not pretend otherwise.

`AD-01` is a P5 integration test and a P8 demo segment (`DEMO_SCENARIOS.md` step C2a). It is **not executed in
P0** — no graph exists yet.

## Consequences

Positive:

- Deterministic, testable, cheap, fast, and offline-capable.
- A defensible answer to "where is the agency?": observable path selection, bounded recovery, and a human
  interrupt/resume gate — not a chat between models.
- The model's blast radius stays one node with one non-mutating tool.

Negative / accepted costs:

- Routing is deliberately **not** emergent: no open-ended planning, no self-authored goals, no agent that
  writes new nodes or tools. This is a conscious trade-off of autonomy for auditability and safety; it is
  documented rather than dressed up.
- An evaluator expecting autonomous multi-LLM collaboration will not find it here. The owner may reinterpret
  the requirement, but any change must preserve the verified-facts gate, deterministic review rules, and
  human approval (`docs/clinical-safety/CLINICAL_SAFETY.md` §6).
- Shared-state schema evolution must be managed carefully (`state_schema_version`).

## Alternatives rejected

| Alternative | Reason |
|---|---|
| Five autonomous LLM agents with a conversation bus | Unbounded cost/latency, unverifiable, unsafe, hard to audit; explicitly out of scope |
| AutoGen/CrewAI-style role chat | Same problems; approval and idempotency guarantees become fragile |
| Plain sequential function calls with no graph | Loses checkpointing, interrupt/resume, and any defensible decision-making evidence |
| One mega-agent calling all tools | No separation of responsibility; a single prompt failure compromises everything |
| Adding a "planner" LLM node that invents steps | Unbounded, untestable, and would sit next to clinical data without a guard |

## Verification (P0, docs-only)

- Structure, per-node tool allowlists and state permissions: `STATE_AND_GRAPH_CONTRACT.md` §3–§4,
  `TOOL_CONTRACTS.md` §5.
- Triage/validation semantics and trace fields: `STATE_AND_GRAPH_CONTRACT.md` §4.2 routing rules and §6.
- Test specification: `EVALUATION_MATRIX.md` `AD-01`.
- **Not executed:** no graph compiled, no checkpoint written, no triage path selected, no interrupt exercised.
  Scheduled P5; resume-after-restart evidence P7; `AD-01` demonstration P8.

## Review notes for owner

1. Confirm the semantics in §2 ("five bounded agent components in one graph, only one calls an LLM") is
   acceptable for the assignment wording.
2. Confirm that `extraction_triage` + `draft_validation` are sufficient evidence of agentic depth for your
   evaluator, or state what additional bounded mechanism you require.
3. Confirm the trade-off in §5 is acceptable: auditable determinism **instead of** emergent planning.
