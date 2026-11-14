# MVP Technical Specification — One Routine Outpatient Follow-Up

| Field | Value |
|---|---|
| Document ID | `SPEC-MVP-001` |
| Version | `0.4.0-p0` |
| Status | **IN REVIEW — not signed off** |
| Phase | `P0` (documentation and governance only) |
| Prepared by | Arena agent (Arena session branch `arena/ee7d211b-ai-doctor-followup-agent`) |
| Prepared on | 2026-11-14 |
| Requires owner signature | **Yes** — see [§12 Sign-off](#12-sign-off-block) |
| Supersedes | Draft statements in `docs/roadmap/MASTER_PLAN.md` v0.1 where they conflict |

> **Revision 0.3.0** reflects PR #2 rounds 1–2: observation trust levels, an injected demo clock, a
> pre-verification/post-verification output split, deterministic task identity, typed graph-trace decisions, the
> app-DB source-of-truth rule, the closed verified-fact → observation mapping and the observation admissibility
> predicate. Requirement IDs are stable; `REQ-DATA-04`, `REQ-DATA-05` and `REQ-OPS-04` are new, giving
> **50 requirements**.

> **SCOPE NOTICE — EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**
> This specification describes an academic graduation-project prototype. It is not a medical device, not diagnostic or treatment software, and must never be used with real patient data. Every clinical action in the described workflow is performed or approved by a human doctor.

---

## 1. Problem statement and product intent

A doctor supervising routine outpatient follow-ups receives sporadic patient check-ins (blood pressure, heart rate, optional glucose, free-text note) and occasional uploaded medical documents (text PDFs, scanned PDFs, photographs). Assembling "what changed since last time, with evidence" is repetitive manual work, and documents are easy to misread.

The prototype supports **one bounded workflow**: turn a patient's synthetic check-in plus uploaded report into a *source-cited draft review packet* that the doctor can verify, edit, and act on, with an auditable trail.

The system's product promise is **organizing evidence and draft prose for a doctor**. It is never "deciding for the doctor".

## 2. Actors

| Actor ID | Actor | Description | Authentication in MVP |
|---|---|---|---|
| `ACT-DOC` | Doctor (demo clinician) | Reviews patients/timeline, verifies extracted facts, reads drafts, approves/edits/rejects. Only role allowed to finalize a follow-up action. | Local seeded account, session token, role claim |
| `ACT-PAT` | Patient (demo persona) | Submits check-ins and uploads documents for **their own** synthetic record. Receives no clinical advice. | Local seeded account, session token, role claim, patient scope |
| `ACT-ADM` | Demo administrator | Seeds/resets synthetic demo data on a local machine. No clinical endpoints. | Local-only seeded account; reset endpoint disabled outside demo mode |
| `ACT-SYS` | System worker (orchestrator + agents) | Executes the bounded graph on behalf of a user request. Holds a restricted internal identity, not a user session. | Internal service call, no network exposure |
| `ACT-REV` | Clinical reviewer / project owner | Human governance role. Reviews PRs, approves phases, runs local verification. May also hold `ACT-DOC`. | GitHub + local machine, not an app account |

Non-actor: the local LLM. It is a **tool invoked by** `ACT-SYS`, not an actor with permissions.

## 3. The single in-scope workflow

```text
Patient check-in (measurements + note)
        + optional document upload
                    |
                    v
        intake validation (type, size, scope)
                    |
                    v
   text extraction -> OCR fallback -> candidate facts
                    |
                    v
        doctor verification of ambiguous facts
                    |
                    v
   baseline comparison -> deterministic DEMO review rules
                    |
                    v
     grounded draft summary (local LLM or labeled fallback)
                    |
                    v
        doctor interrupt: approve / edit / reject
                    |
                    v
   in-app follow-up task + notification + audit record
```

Every arrow is a **node transition** owned by the contract in
[`STATE_AND_GRAPH_CONTRACT.md`](STATE_AND_GRAPH_CONTRACT.md). No arrow exists that a doctor did not open or close.

## 4. User stories (MVP, testable)

Acceptance criteria are binding at the phase named in `Trace`; requirement IDs resolve in
[`../evaluation/TRACEABILITY_MATRIX.md`](../evaluation/TRACEABILITY_MATRIX.md).

| ID | As a | I want | So that | Acceptance criteria (observable) | Refs | Trace |
|---|---|---|---|---|---|---|
| `US-01` | Doctor | to sign in and see only my assigned synthetic patients | I cannot browse unrelated records | Login returns role + scope; patient list contains only assigned patients; direct access to another patient's ID returns `403`/`404` and writes an audit event | `REQ-AUTH-01/02`, `REQ-SEC-01` | P2 |
| `US-02` | Patient | to submit a timestamped check-in with units | my doctor sees measurements with an explicit source | Check-in rejected without timestamp, unit, or when the unit is not in the allowlist; accepted record stores `source=patient_checkin`; response echoes stored values | `REQ-DATA-01/02` | P2 |
| `US-03` | Patient | to upload a PDF or image for my own record | my report becomes structured information | Non-allowlisted MIME/magic type, oversize, or too many pages rejected with a typed error; accepted upload stored with hash and status `pending_extraction` | `REQ-ING-01` | P3 |
| `US-04` | System | to extract a declared field set with page/span provenance | every fact is traceable to its source | Each accepted fact carries document ID, page index, character span, raw text, normalized value/unit; no fact is created without a source reference | `REQ-ING-02/03`, `REQ-VERIFY-01` | P3 |
| `US-05` | Doctor | to see low-confidence, contradictory, or ambiguous fields flagged as **verification issues** for correction | ambiguous values are never silently trusted | Ambiguous date/unit/OCR cases produce blocking `VI-*` verification issues and `verification_status=pending`; unverified fields are excluded from comparisons, review rules, and drafts; `DR-*` review items do not exist until verification completes | `REQ-VERIFY-02`, `REQ-SEC-04`, `REQ-RULE-01` | P3 |
| `US-06` | Doctor | to confirm or correct an extracted field | the record reflects my judgment, not the OCR guess | Verification endpoint requires role `doctor`, patient scope, and an explicit value or rejection; audit stores before/after, verifier, and timestamp | `REQ-VERIFY-03`, `REQ-AUDIT-01` | P3 |
| `US-07` | Doctor | to see current vs prior measurements | I can judge change without recomputing | Timeline/compare output shows prior value, current value, delta, units, timestamps, source IDs and whether each value is self-reported or doctor-verified; missing baselines are labeled, not imputed | `REQ-MON-01/02`, `REQ-DATA-04` | P2/P4 |
| `US-08` | Doctor | a queue of post-verification items that a deterministic demo policy asked me to look at | nothing enters my attention silently or by model opinion | Each review item lists rule ID, evidence IDs, reason code, trust basis and policy version; the same input twice produces no duplicate item; pre-verification blockers are shown separately as verification issues | `REQ-RULE-01/02/03`, `REQ-DATA-04` | P4 |
| `US-09` | Doctor | a draft summary whose every claim links to evidence | I can verify before trusting | Each factual sentence maps to ≥1 evidence reference; unsupported statements are omitted or listed as "not asserted"; provider/model/prompt version recorded | `REQ-LLM-01/02/03` | P5 |
| `US-10` | Doctor | to approve, edit, or reject before anything is finalized | I remain the decision-maker | Workflow pauses at an interrupt; no task/notification exists before a decision; reject creates no task; resuming after a restart does not duplicate side effects | `REQ-GRAPH-03/04`, `REQ-TASK-01` | P5 |
| `US-11` | Doctor | an in-app task and notification for an approved action only | follow-up is organized without messaging patients automatically | Task references the approval decision ID; notification is in-app; no outbound SMS/email/WhatsApp code path exists | `REQ-TASK-01/02`, `REQ-SEC-03` | P6 |
| `US-12` | Project owner | to reset the demo to a known state and inspect the audit trail | I can demo reproducibly and defensibly | `POST /api/v1/demo/reset` restores only synthetic fixtures; audit events persist per run and exclude document text and secrets | `REQ-OPS-02/03`, `REQ-AUDIT-02` | P2/P6 |
| `US-13` | All users | to always see that this is a synthetic educational demo | no output can be mistaken for medical advice | Disclaimer present in UI shell, every generated draft, exported demo material, and every fixture file header | `REQ-SEC-05` | P6 |

## 5. Roles and permissions (summary)

Binding matrix lives in [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md#6-role-and-permission-matrix).
Headline rules:

- `ACT-DOC` may read any **assigned** patient and write only verification, review-decision, and task-completion records.
- `ACT-PAT` may read/write **only self-scoped** observations and documents, and may never read drafts, review items, or tasks.
- `ACT-SYS` may read the run's scoped context and write only audit, workflow-state, verification-issue, review-item, draft, and (post-approval) task records.
- No role may relabel a self-reported check-in as doctor-verified; the label is derived from provenance (`REQ-DATA-04`).
- No actor, including `ACT-SYS`, may send an external message, prescribe, or write a clinical plan.

## 6. Non-goals (MVP, binding)

Out of scope and must not appear in code, docs, or demo claims:

1. Diagnosis, differential diagnosis, risk scoring, triage, or emergency handling.
2. Prescriptions, dosing, treatment or medication-change recommendations.
3. Patient-facing medical advice, chat, or explanations of results.
4. Any automatic outbound communication (SMS, email, WhatsApp, push, phone).
5. FHIR/EHR/hospital integration, insurance, billing, scheduling engines.
6. Real patient data, real PII, cloud storage, hosted inference, paid APIs.
7. Mobile native apps, multi-tenant SaaS, RBAC beyond three local roles.
8. Vector database / RAG over a clinical corpus; fine-tuning or training a medical model.
9. Claims of clinical validation, accuracy, compliance (HIPAA/GDPR), or production readiness.
10. Ambient voice, video, or image diagnosis; multilingual OCR guarantees.

## 7. Requirement catalogue

IDs are stable; each must be traceable to a component, a test, and a phase.

### 7.1 Authentication and authorization
| ID | Requirement | Phase |
|---|---|---|
| `REQ-AUTH-01` | Seeded local accounts with salted password hashing; no committed production credentials or plaintext passwords. | P2 |
| `REQ-AUTH-02` | Role (`doctor`/`patient`/`demo_admin`) and patient-scope enforcement on every patient-data endpoint server-side. | P2 |
| `REQ-AUTH-03` | Session/token expiry and logout invalidation; unauthenticated access returns `401` without leaking record existence. | P2 |

### 7.2 Data domain
| ID | Requirement | Phase |
|---|---|---|
| `REQ-DATA-01` | Observations store patient, encounter, measured-at (UTC), type, numeric value, unit, source, and validation result. | P2 |
| `REQ-DATA-02` | Unit allowlist per observation type; unknown/absent units are rejected for check-ins and flagged for documents. | P2 |
| `REQ-DATA-03` | All identifiers are stable UUIDs; all timestamps stored UTC ISO-8601; display time zone is explicit. | P2 |
| `REQ-DATA-04` | Every observation carries `trust_level ∈ {self_reported_validated, doctor_verified}`; self-reported values are labelled as such everywhere and are never described as doctor-verified. Rejected observations are excluded from comparisons and rules. | P2 |
| `REQ-DATA-05` | A verified document fact becomes an observation **only** when its normalized test name and unit both match the closed, versioned mapping table (`map-1.0.0`, format `^map-\d+\.\d+\.\d+$`); every other verified fact stays document-only. A document contributes at most **one** measurement tuple — a document with several is flagged for manual verification and not mapped. `measured_at` derives from the verified report date, derivation is atomic with the verification and idempotent per fact. | P3 |

### 7.3 Document ingestion and OCR
| ID | Requirement | Phase |
|---|---|---|
| `REQ-ING-01` | Accept only allowlisted types (PDF, PNG, JPEG) checked by magic bytes; enforce max size and max page count; reject executable/archived content. | P3 |
| `REQ-ING-02` | Extract text with `pypdf` first; invoke OCR only when the page has insufficient text; record which path produced each character. | P3 |
| `REQ-ING-03` | Extract only the declared field set (`report_date`, `test_name`, `value`, `unit`, `reference_text`), never free-form invented facts. | P3 |
| `REQ-ING-04` | Persist SHA-256 of the upload, page count, extraction attempts, and failure reason. | P3 |
| `REQ-ING-05` | Bound parser resources: page limit, timeout, image size cap, and OCR language allowlist. | P3/P7 |

### 7.4 Verification and provenance
| ID | Requirement | Phase |
|---|---|---|
| `REQ-VERIFY-01` | Every extracted fact carries document ID, page index, span, raw text, quality flag. | P3 |
| `REQ-VERIFY-02` | Ambiguous date/unit/value or OCR confidence below the configured demo threshold sets `verification_status=pending`. | P3 |
| `REQ-VERIFY-03` | A doctor decision sets `verified` or `rejected` with verifier identity, timestamp, and reason; history is append-only. | P3 |

### 7.5 Monitoring and comparisons
| ID | Requirement | Phase |
|---|---|---|
| `REQ-MON-01` | Compare the current admissible observation (`validation != rejected`) to the **most recent prior** admissible value of the same type/unit, recording `trust_basis`; never against the oldest value and never with an imputed baseline. | P4 |
| `REQ-MON-02` | Never impute missing baselines or convert units silently; label unit mismatch as incomparable. | P4 |
| `REQ-MON-03` | Detect duplicate, out-of-order, and contradictory observations and surface them as data-quality items. | P4 |

### 7.6 Deterministic demo review rules
| ID | Requirement | Phase |
|---|---|---|
| `REQ-RULE-01` | Review items are generated only by versioned deterministic rules from an explicit demo policy file; never by the LLM. | P4 |
| `REQ-RULE-02` | Rule output includes rule ID, reason code, evidence references, and policy version; rules are labelled `DEMO_ONLY` in the UI. | P4 |
| `REQ-RULE-03` | Rule evaluation is idempotent per (patient, workflow_version, evidence set) and never consumes unverified facts. | P4 |

### 7.7 Local LLM drafting
| ID | Requirement | Phase |
|---|---|---|
| `REQ-LLM-01` | Summaries are produced through one adapter interface with a local Ollama provider and a deterministic fallback provider. | P5 |
| `REQ-LLM-02` | Output is schema-constrained, size-bounded, timeout-bounded, and every factual claim is evidence-linked. | P5 |
| `REQ-LLM-03` | Provider, model, prompt version, latency, and `execution_status` are stored and shown; fallback is visibly labelled and never presented as model output. | P5 |
| `REQ-LLM-04` | Model unavailability must degrade to the fallback or an explicit error, never to fabricated content. | P5 |

### 7.8 Orchestration
| ID | Requirement | Phase |
|---|---|---|
| `REQ-GRAPH-01` | One LangGraph `StateGraph` with a typed shared state, explicit nodes and conditional edges; no free-form agent-to-agent chat. | P5 |
| `REQ-GRAPH-02` | Checkpoint after every node to SQLite; runs are resumable by `thread_id`. | P5 |
| `REQ-GRAPH-03` | An interrupt precedes every finalizing action; resumption requires a doctor decision payload. | P5 |
| `REQ-GRAPH-04` | Node retries are bounded, classified (transient vs terminal), and never duplicate side effects. | P5 |
| `REQ-GRAPH-05` | Tool access is an explicit allowlist per agent node; unknown tools raise a typed error and audit event. | P5 |

### 7.9 UI
| ID | Requirement | Phase |
|---|---|---|
| `REQ-UI-01` | Doctor views: patient list, timeline, document/extraction review, review queue, run trace, draft, decisions, tasks. | P6 |
| `REQ-UI-02` | Patient views: check-in form and upload, with no clinical interpretation displayed. | P6 |
| `REQ-UI-03` | Loading, empty, error, unverified-data, fallback-model, and duplicate-submit states are explicit and tested. | P6 |

### 7.10 Tasks, notifications, audit
| ID | Requirement | Phase |
|---|---|---|
| `REQ-TASK-01` | Tasks are created only by an approved decision, are idempotent per decision, and are in-app only. | P5/P6 |
| `REQ-TASK-02` | Notifications are local DB records surfaced in-app; no external transport exists in the repo. | P6 |
| `REQ-AUDIT-01` | Verification, decision, task, workflow, and access events are appended with actor, timestamp, run ID. | P2/P5 |
| `REQ-AUDIT-02` | Audit records exclude document body text, credentials, and tokens. | P7 |

### 7.11 Security and safety
| ID | Requirement | Phase |
|---|---|---|
| `REQ-SEC-01` | Cross-patient access attempts return denial and are audited. | P2/P7 |
| `REQ-SEC-02` | Uploaded document text is untrusted data; prompt-injection content cannot alter instructions, tools, or approvals. | P3/P5/P7 |
| `REQ-SEC-03` | No outbound messaging/network side-effect code path exists; asserted by a repository-level test. | P6/P7 |
| `REQ-SEC-04` | Unverified facts cannot reach comparisons, rules, drafts, or tasks. | P4/P5/P7 |
| `REQ-SEC-05` | `EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE` appears in UI, drafts, and fixtures. | P6 |
| `REQ-SEC-06` | No secrets, `.env`, runtime DBs, uploads, or model weights are committed. | P1/P7 |

### 7.12 Operations and evaluation
| ID | Requirement | Phase |
|---|---|---|
| `REQ-OPS-01` | Deterministic seeding produces byte-stable fixture IDs for the three demo cases. | P2/P8 |
| `REQ-OPS-02` | One-command local start/stop/test/reset on the owner's Windows laptop; documented prerequisites. | P1/P8 |
| `REQ-OPS-04` | Demo-mode rule evaluation uses an injected `as_of_utc` fixed per run and persisted; fixtures and tests never call the wall clock, and the value used is returned by the API. | P4 |
| `REQ-EVAL-01` | Synthetic gold fixtures with expected rule IDs and expected decisions are versioned and replayed by tests. | P4/P7 |
| `REQ-EVAL-02` | Extraction precision/recall reported on labeled synthetic documents; ambiguous cases 100% routed to verification. | P3/P7 |
| `REQ-EVAL-03` | Runtime and fallback behavior measured on the owner's machine and reported honestly (including "not measured"). | P5/P7 |

## 8. Assumptions (require owner confirmation)

| ID | Assumption | Impact if wrong |
|---|---|---|
| `ASM-01` | The demo laptop runs Windows 10/11 with PowerShell 5.1+ and can install Python 3.12, Node LTS, Tesseract, and Ollama. | Startup scripts, CI parity, and the P5 benchmark plan change |
| `ASM-02` | The laptop can run a 3B-class quantized model on CPU (GPU optional). | Demo must rely on the labeled deterministic fallback for drafting |
| `ASM-03` | GitHub Free plan + included Actions minutes are sufficient. | CI design must shrink or move local-only |
| `ASM-04` | All demo documents and personas are authored synthetic fixtures. | Product scope is void; no real data may enter the repo |
| `ASM-05` | A clinician-adjacent reviewer is available to sanity-check the demo wording (not a clinical validation). | Wording remains explicitly non-clinical and unendorsed |
| `ASM-06` | The demo is single-machine, single-user-at-a-time. | Concurrency, locking, and multiuser auth must be redesigned |

## 9. Open questions for owner review

| ID | Question | Default if unanswered |
|---|---|---|
| `OQ-01` | Confirm the demo laptop spec (CPU, RAM, GPU/VRAM, Windows version) and available disk for models. | Plan targets CPU-only 3B quantized; benchmark marked "requires owner laptop" |
| `OQ-02` | Should the patient portal have a separate login wall or a role switch in one app? | Separate logins, one React app, role-scoped routes |
| `OQ-03` | Is a 2-field extraction set (BP from PDF + one lab value) enough for the graduation demo? | Keep the 5-field declared set, demo uses 2 |
| `OQ-04` | Should demo admin reset be reachable from the UI? | CLI/PowerShell only; endpoint disabled unless `DEMO_MODE=true` |
| `OQ-05` | Preferred Arabic/English balance in the UI? | English UI, Arabic explanation in discussion material only |
| `OQ-06` | Does the owner accept the numeric parameters in `DEMO_REVIEW_RULES.md` as arbitrary demo values? | Rules stay clearly non-clinical and parameterized |
| `OQ-07` | Is accepting **self-reported validated** check-ins as comparison inputs acceptable, or must every observation be doctor-verified (adding a verification workflow)? | Self-reported values are admissible but always labelled; document values require verification |

## 10. Success criteria for the MVP (definition of demo-done)

The MVP is demo-complete when, on the owner's laptop from a fresh checkout:

1. Three seeded synthetic cases (A stable, B changed, C ambiguous OCR) can be replayed in any order after reset.
2. Every drafted factual statement resolves to a stored evidence reference; unverified content never appears as fact.
3. No task or notification exists without an approval record, and rejection produces none.
4. Restarting the backend mid-approval and resuming produces exactly one task and one audit finalization.
5. The three security negatives (cross-patient, prompt injection, unverified fact) are demonstrated as blocked.
6. Fallback mode is visibly labeled and the demo runs with Ollama uninstalled.
7. No medical claim, clinical threshold claim, or compliance claim appears in the UI, docs, or demo script.

## 11. Glossary

| Term | Meaning in this project |
|---|---|
| Evidence reference | `{document_id, page, span}` or `{observation_id}` that supports a statement |
| Verified fact | Extracted value a doctor accepted or corrected; the only kind admissible downstream |
| Review item | Deterministic, non-clinical flag asking a doctor to look at something |
| Draft summary | Machine-written, evidence-linked prose intended for the doctor, never the patient |
| Interrupt | LangGraph pause requiring an external (doctor) decision before continuing |
| Fallback | Deterministic template output used when the local model is unavailable; labelled as such |
| DEMO_ONLY | Value/rule that exists for demo mechanics and carries no clinical validity |

## 12. Sign-off block

This document is **not signed off**. It becomes the accepted baseline only when the project owner records the decision here and in `docs/roadmap/PHASE_PROGRESS.md`.

| Role | Name / handle | Decision | Date |
|---|---|---|---|
| Prepared by | Arena agent (implementer) | Submitted for review | 2026-11-14 |
| Scope reviewed by | Project owner | ☐ Approved ☐ Changes requested | — |
| Safety wording reviewed by | Project owner (+ clinician-adjacent reviewer if available) | ☐ Approved ☐ Changes requested | — |

Agent self-approval is invalid by `AGENTS.md` §2.
