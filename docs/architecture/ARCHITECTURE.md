# Architecture Baseline — AI Doctor Follow-Up

| Field | Value |
|---|---|
| Document ID | `ARCH-001` |
| Version | `0.3.0-p0` |
| Status | **IN REVIEW — architecture baseline for owner acceptance** |
| Phase | `P0` (documentation only; no component is implemented) |
| Revision | 0.3.0: pre/post-verification split, observation trust levels, injected demo clock, deterministic task identity, bounded extraction/drafting decision loops (PR #2 review) |
| Supersedes | `ARCHITECTURE.md` v0.1 draft (expanded, not contradicted) |

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.** A local, single-machine academic prototype.
> The doctor makes every clinical decision; the software organizes evidence and drafts prose.

This architecture is doctor-centered, local-first, evidence-first and human-controlled. It exists to make
**one routine outpatient follow-up** observable, resumable and auditable — not to automate medicine.

## 1. Design principles

1. **Evidence before prose.** Structured, source-linked facts are the only input to comparisons, rules, and drafting.
2. **Deterministic where it matters.** Review triggers, permissions, state transitions, and side effects are plain code, never model output.
3. **The model is a tool, not an actor.** One adapter boundary, schema-constrained, timeout-bounded, replaceable by a labelled fallback.
4. **Bounded autonomy.** Five agents, each with a fixed tool allowlist and no direct database, shell, network, or approval capability.
5. **Durable and idempotent.** Every node checkpoints; every finalizing action is guarded by an idempotency key.
6. **Honest uncertainty.** Ambiguous dates, units, OCR text, or conflicting sources stop the pipeline at a human verification gate.
7. **Boring infrastructure.** One API, one React app, SQLite, local files. No cloud, no microservices, no vector DB, no paid inference.

## 2. Finalized logical architecture

```mermaid
flowchart TB
    subgraph Browser["Browser - one React + TypeScript app"]
        PatUI["Patient portal /patient/*<br/>check-in + upload"]
        DocUI["Doctor dashboard /doctor/*<br/>timeline, verification, review queue, drafts, tasks"]
    end

    subgraph API["FastAPI service - localhost:8000"]
        AuthN["Auth + role/scope authorization"]
        Routes["Typed REST endpoints<br/>/api/v1/*"]
        Validate["Validation, size limits, idempotency keys"]
    end

    subgraph Domain["Domain services - deterministic, no LLM"]
        Intake["Document intake<br/>magic-byte check, hash, page cap"]
        Extract["Extraction<br/>pypdf text-first, Tesseract OCR fallback"]
        Prov["Provenance + verification status"]
        Compare["Baseline comparison<br/>verified facts only"]
        Rules["DEMO review rule engine<br/>versioned policy file"]
        Tasks["In-app tasks + notifications"]
        Audit["Append-only audit trail"]
    end

    subgraph Orchestration["LangGraph StateGraph - single orchestrator"]
        direction LR
        G1["document_extract"]
        G1a["extraction_triage<br/>bounded path choice"]
        G2["fact_verify_gate<br/>VI-* issues, halt"]
        G3["monitor_compare"]
        G4["review_rules<br/>DR-* prompts"]
        G5["draft_summary"]
        G5a["draft_validation<br/>accept / repair / fallback"]
        G6["clinician_approval - interrupt"]
        G7["finalize_actions"]
        G8["halted - resumable"]
    end

    subgraph Model["Local model boundary"]
        Adapter["LLM adapter Protocol"]
        Ollama["OllamaProvider<br/>127.0.0.1:11434"]
        Fallback["DeterministicFallbackProvider<br/>labelled, no model"]
    end

    subgraph Storage["Local storage"]
        DB[("SQLite app DB<br/>SQLAlchemy + Alembic")]
        CKPT[("SQLite LangGraph checkpoints<br/>thread_id per run")]
        Files[("runtime uploads - gitignored")]
    end

    PatUI --> Routes
    DocUI --> Routes
    Routes --> AuthN
    AuthN --> Validate
    Validate --> DB
    Validate --> Intake
    Validate --> Orchestration
    Intake --> Files
    Intake --> Extract
    Extract --> Prov
    Prov --> DB
    Prov --> Orchestration
    Compare --> DB
    Rules --> DB
    Orchestration --> Compare
    Orchestration --> Rules
    Orchestration --> Adapter
    Adapter --> Ollama
    Adapter --> Fallback
    Orchestration --> CKPT
    Orchestration --> Audit
    G1 -.-> G1a
    G5 -.-> G5a
    G6 -.->|"doctor decision"| G7
    G2 -.->|"unverified facts"| G8
    G7 --> Tasks
    G7 --> DB
    Tasks --> DB
    Audit --> DB
```

The graph node set, edges, retry classification and interrupt semantics are normative in
[`../contracts/STATE_AND_GRAPH_CONTRACT.md`](../contracts/STATE_AND_GRAPH_CONTRACT.md).

## 3. Layers and their contracts

| Layer | Owns | Must not | Contract |
|---|---|---|---|
| Browser/UI | Role-scoped views, evidence display, explicit uncertainty and fallback labels | Compute clinical logic, hide unverified data, call the model directly | `../contracts/API_CONTRACT.md` |
| API | AuthN/AuthZ, typed schemas, request validation, idempotency, size limits, error envelope | Contain clinical thresholds, call Ollama | `../contracts/API_CONTRACT.md` |
| Domain services | Deterministic parsing, comparison, rules, tasks, audit | Invent facts, call the LLM for decisions | `../contracts/DATA_DICTIONARY.md`, `../clinical-safety/DEMO_REVIEW_RULES.md` |
| Orchestrator | Node ordering, state, checkpoint, interrupt/resume, tool dispatch, bounded path selection | Let agents chat freely, self-approve, or route on model opinion | `../contracts/STATE_AND_GRAPH_CONTRACT.md` |
| Agent nodes | One bounded responsibility each, allowlisted tools | Direct SQL, shell, HTTP, approval, prescribing | `../contracts/TOOL_CONTRACTS.md` |
| Model boundary | One method: grounded draft from verified evidence | Decide review items, approve, transmit data elsewhere | `../contracts/LLM_ADAPTER.md` |
| Storage | SQLite app data, checkpoints, local uploads | Hold real patient data; be committed to git | `.gitignore`, `../contracts/DATA_DICTIONARY.md` |

## 4. The five agents — bounded components, not five model servers

All five run as **nodes inside one LangGraph graph** and share one typed state. Only
`doctor_communication` may invoke the model; the rest are deterministic Python. See
[`ADR-0006`](ADR-0006-five-bounded-agents-single-graph.md).

| # | Agent node | Responsibility (one sentence) | Allowed tools | Cannot |
|---|---|---|---|---|
| 1 | `medical_document` | Turn a stored document into candidate structured facts with page/span provenance and quality flags | `get_document_pages`, `extract_document`, `validate_structured_fields` | Accept an ambiguous value as verified; read other patients' documents |
| 2 | `patient_monitoring` | Compare current verified observations against the most recent verified baseline of the same type/unit | `read_observations`, `compare_observations` | Diagnose; impute a missing baseline; convert units silently |
| 3 | `review_priority` | Evaluate versioned deterministic demo rules over verified facts and open review items | `read_verified_facts`, `evaluate_demo_review_rules` | Invent thresholds; rank by clinical risk; use the LLM |
| 4 | `doctor_communication` | Draft a doctor-facing, evidence-linked summary (model or labelled fallback) | `read_verified_facts`, `draft_grounded_summary` | Approve, send, address the patient, or state unsupported facts |
| 5 | `follow_up` | Materialize doctor-approved in-app tasks and notifications, idempotently | `create_in_app_task`, `list_due_tasks` | Contact anyone externally; create a task without an approval record |

Only `doctor_communication` calls the model. Two **bounded decision mechanisms** provide the agentic depth:
`extraction_triage` selects a tool path (text layer / OCR / OCR-with-preprocessing / flag-for-human) and retries
at most twice, and `draft_validation` accepts, repairs once, or falls back. Both record their choice in the run
trace. Semantics, trade-off and acceptance test `AD-01` are in `ADR-0006` §3–§4.

Shared-state shape, per-node read/write permissions and the `VI-*`/`DR-*` separation are defined in
`../contracts/STATE_AND_GRAPH_CONTRACT.md` §3–§4.

## 5. End-to-end sequence (with the doctor gate)

```mermaid
sequenceDiagram
    autonumber
    participant P as Patient portal
    participant A as FastAPI
    participant E as Intake + extraction
    participant DB as SQLite
    participant G as LangGraph
    participant L as LLM adapter
    participant D as Doctor dashboard
    P->>A: POST check-in (typed, timestamped, unit-checked)
    A->>DB: store observation (source=patient_checkin)
    P->>A: POST document upload
    A->>E: magic-byte + size + page validation
    E->>DB: store document + sha256, status=pending_extraction
    E->>DB: store candidate facts + spans + quality flags
    D->>A: GET extraction, POST verify (accept/correct/reject)
    A->>DB: append verification record, set verification_status
    D->>A: POST /workflows/follow-up (idempotency key)
    A->>G: start run (thread_id) with scoped IDs
    G->>DB: read verified facts + baseline
    G->>G: compare, evaluate demo rules
    alt ambiguous or unverified facts present
        G->>DB: verification_issues VI-*, checkpoint state=needs_verification, halt
        D->>A: correct fields, resume
    end
    G->>L: draft grounded summary (schema, timeout)
    alt Ollama unavailable or invalid schema
        L->>G: fallback draft, execution_status=fallback_no_model
    end
    G->>G: draft_validation - accept, one repair, or fallback
    G->>DB: checkpoint state=awaiting_decision, interrupt
    D->>A: review evidence, approve / edit / reject
    A->>G: resume with decision + doctor identity
    G->>DB: task + notification + audit (idempotent, post-approval only)
    D->>A: view task, run timeline, audit trail
```

## 6. Role and permission matrix

Legend: **A** = allowed · **C** = allowed only within own patient scope · **S** = allowed only for an assigned patient · **D** = allowed after an explicit doctor decision · **–** = denied (must test as `403`).

| Capability | Doctor `ACT-DOC` | Patient `ACT-PAT` | Demo admin `ACT-ADM` | System worker `ACT-SYS` |
|---|---|---|---|---|
| Sign in / own session | A | A | A (local only) | – (internal identity) |
| List patients | S | – | – | – |
| Read own profile | A | A | A | – |
| Read patient timeline / observations | S | C | – | C (run scope) |
| Create check-in | – | C | – | – |
| Upload document | – | C | – | – |
| Read raw document file | S | C | – | C (run scope) |
| Read extraction result / provenance | S | C (status only, no clinical values) | – | C |
| Verify / correct / reject extracted fact | S | – | – | – (must be human) |
| Read review items | S | – | – | C (write own generated items) |
| Create review item | – (human raises manually only via note) | – | – | A (deterministic rules only) |
| Read draft summary | S | – | – | C (write own draft) |
| Approve / edit / reject decision | S | – | – | – |
| Create follow-up task | – | – | – | D (approved decision only, run `finalizing`, atomic commit) |
| Complete task | S | – | – | – |
| Read in-app notifications | S | C (no clinical content) | – | A (own generated) |
| Read audit trail | S (own patients) | C (own actions only) | A (local DB/CLI only; no API endpoint in MVP) | A (write only) |
| Seed / reset synthetic demo | – | – | A (local, demo mode) | – |
| Start / resume workflow run | S | C (own check-in triggers intake only) | – | A (internal) |
| Read model/provider metadata | S | – | – | A |
| Send external message | – | – | – | – |
| Prescribe / alter treatment | – | – | – | – |
| Grant a role | – | – | – | – |
| Read another patient's data | – | – | – | – |

Enforcement rules:

1. Authorization is evaluated **server-side per request**, derived from the session identity plus the stored doctor–patient assignment. The UI is never the enforcement point.
2. Denials return `403` (authenticated but out of scope) or `404` (resource does not exist for this actor) with no field-level leakage, and append an audit event.
3. `ACT-SYS` is a process identity, not a login. It can never satisfy a verification or approval check because those require a human actor ID from an authenticated session.
4. No role has an outbound-communication capability; there is no code path to grant one (`REQ-SEC-03`).
5. Patient-visible document status is limited to `received` / `processing` / `needs_attention` — never an interpreted value.

## 7. Data flow and trust boundaries

| Boundary | Trust | Rule |
|---|---|---|
| Browser → API | Untrusted input | Typed validation, size caps, auth per request, CSRF/session policy at P2 |
| Uploaded document bytes | Untrusted content | Magic-byte check, page/timeout caps, text treated as data only, never as instructions (`REQ-SEC-02`) |
| OCR/text layer → facts | Untrusted until verified | Provenance + quality flags + human gate (`REQ-VERIFY-01/02`) |
| Verified facts → rules/draft | Trusted *for demo purposes only* | Only `verification_status=verified` reaches these nodes (`REQ-SEC-04`) |
| Observations → comparisons | Mixed provenance, explicitly labelled | Every observation carries `trust_level`; self-reported values are labelled in review messages and drafts and are never called doctor-verified (`REQ-DATA-04`) |
| Clock | Injected, not implicit | `as_of_utc` is fixed per run and persisted, so staleness expectations are reproducible (`REQ-OPS-04`) |
| API → local Ollama (`127.0.0.1:11434`) | Trusted local process, untrusted output | Schema validation, timeout, size cap, no tool access, no network egress beyond loopback |
| Model output → UI | Displayed, never authoritative | Citations required; unsupported claims dropped; provider metadata shown (`REQ-LLM-02/03`) |
| Runtime data → git | Forbidden | Synthetic fixtures only in repo; uploads/DBs/model weights gitignored (`REQ-SEC-06`) |

## 8. Checkpoint, interrupt and recovery model (summary)

- One graph thread per workflow run; `thread_id` is derived from `run_id`.
- A checkpoint is written after each node; the checkpoint store is a separate SQLite file guarded by `AGENTS.md`.
- Before `finalize_actions` the graph executes an `interrupt`, persisting `state=awaiting_decision`.
- Resumption requires `(run_id, decision, doctor_id, decision_reason)`; the resumed node re-reads verified evidence and never trusts client-supplied clinical facts.
- Side effects are keyed by an `action_key` derived **only** from immutable stored values
  (`sha256(workflow_version | patient_id | approval_decision_id | action_type | slot)`) and the task UUID is
  derived from that key (`uuid5`), so a retry or restart recomputes the same identity; a unique index makes a
  duplicate insert a no-op, and the response stays consistent (`P0-R04`).
- Decision, task, notification, audit finalization and the `finalizing → completed` transition commit in **one**
  SQLite transaction (`STATE_AND_GRAPH_CONTRACT.md` §7.2).
- Crash or restart mid-approval must yield exactly one task and exactly one finalization audit event (`REQ-GRAPH-02/03/04`).

Normative detail: `../contracts/STATE_AND_GRAPH_CONTRACT.md`.

## 9. Clinical-safety architecture checks

These must be demonstrable, not merely claimed:

1. Unverified or rejected facts never reach `compare_observations`, `evaluate_demo_review_rules`, or `draft_grounded_summary`.
2. No task, notification, or finalized summary exists without an approval record referencing a doctor identity.
2a. Pre-verification blockers appear as `VI-*` verification issues only; `DR-*` review items are computed only
   from verified evidence — the two are never mixed (`P0-R03`).
2b. Every observation is labelled `self_reported_validated` or `doctor_verified`; no self-reported value is
   described as doctor-verified (`REQ-DATA-04`).
3. A prompt-injection payload inside a document cannot change tool allowlists, system instructions, approval state, or patient scope.
4. Cross-patient access attempts are denied and audited.
5. Fallback output is labelled at the API and in the UI; it is never presented as model output.
6. Repository scan finds no outbound-messaging dependency or endpoint (`REQ-SEC-03`).
7. The UI, drafts, and fixtures carry the educational/synthetic notice (`REQ-SEC-05`).

Owner-facing wording: `../clinical-safety/CLINICAL_SAFETY.md`. Attack cases: `../clinical-safety/THREAT_MODEL.md`.

## 10. Architecture decisions

| ADR | Decision | Status |
|---|---|---|
| [ADR-0001](ADR-0001-monorepo-single-service.md) | Monorepo with one FastAPI service and one React app; no microservices | Proposed (P0) |
| [ADR-0002](ADR-0002-local-ollama-with-labelled-fallback.md) | Local Ollama behind an adapter, with an explicitly labelled deterministic fallback | Proposed (P0) |
| [ADR-0003](ADR-0003-sqlite-app-and-checkpoints.md) | SQLite for application data and LangGraph checkpoints, single machine only | Proposed (P0) |
| [ADR-0004](ADR-0004-evidence-verified-review-queue.md) | Evidence-verified facts plus a deterministic review queue, never a risk prediction | Proposed (P0) |
| [ADR-0005](ADR-0005-defer-external-comms-and-ehr.md) | Defer external communications and EHR/FHIR integration beyond the MVP | Proposed (P0) |
| [ADR-0006](ADR-0006-five-bounded-agents-single-graph.md) | Five bounded agent nodes inside one orchestrated graph, not five model servers; agentic depth via bounded path selection + repair, with acceptance test `AD-01` | Proposed (P0, extended after review) |

ADR status becomes `Accepted` only when the project owner approves the P0 PR.

## 11. Deliberately deferred design work

| Area | Deferred to | Why |
|---|---|---|
| Concrete SQLAlchemy models, migrations, index tuning | P2 | Data dictionary is enough for review now |
| Exact extraction regex/heuristics and OCR preprocessing | P3 | Needs real (synthetic) fixture iteration to tune |
| Numeric demo-rule parameters | P4 | Values must stay arbitrary and reviewable, not implied clinical cut-offs |
| Prompt templates and token budgets | P5 | Depend on the benchmarked local model |
| UI component design system and route guards | P6 | Depends on the finalized API contract |
| Concurrency, multiuser, deployment, backups | Post-graduation | Explicit non-goal (`ASM-06`) |
| Real clinical validation | Out of scope | Cannot be done with synthetic data |

## 12. Consistency notes for the reviewer

- This document, `docs/contracts/*`, `docs/clinical-safety/*`, `docs/evaluation/*`, `docs/demo/*` and
  `docs/roadmap/MASTER_PLAN.md` describe the same workflow; requirement IDs are the join key.
- Where v0.1 `ARCHITECTURE.md` said "Review-Priority Agent", this baseline keeps the name but forbids clinical
  prioritization: it produces deterministic review items whose severity is a **workflow hint** only.
- Where `MASTER_PLAN.md` §2 lists an external web-search agent as excluded, ADR-0005 restates and extends that exclusion.
- Any remaining conflict is recorded in `docs/phase-reports/PHASE_0_REPORT.md` §"Unresolved assumptions".
