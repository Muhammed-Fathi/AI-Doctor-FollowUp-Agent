# P5-S0 — Typed Shared State: Contract Reconciliation and Implementation Review

**Date:** 2026-11-23  
**Phase status:** P5 **IN_REVIEW / NOT ACCEPTED**. This document is a design + implementation review of one bounded slice (P5-S0). It is **not** a phase PASS, not an acceptance, and not an authorization to start P5-S1.  
**Scope authorized:** P5-S0 only — contract reconciliation and executable typed shared-state models with schema tests.  
**Safety:** ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

---

## 0. Branch, base and identity

| Item | Value |
|---|---|
| Branch | `arena/a61b8893-p5-s0-typed-state` |
| Base commit (exact `main`) | `121e1dbe8580d3d3da19c4c66d2391096d59bc52` |
| Base source | `origin/main` after PR #46 owner merge (`2026-11-23T21:21:10Z`) |
| Merged-main CI at base | [#45268774759](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45268774759) **SUCCESS** |
| PR | ONE draft PR from this branch (URL recorded in the PR body / final report) |
| Tracking issue | [#14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) — **OPEN**, must stay open |

P4 status at the time of writing: **`CONDITIONALLY_ACCEPTED_SYNTHETIC`** (owner marker `OWNER-ACCEPT-P4-BOUNDED-CLOSURE-B`, PR #46 comment #7114121198). GOLD-EX-11 **FAIL / NOT PROVEN**. RB3-75..77 **deferred / NOT EXECUTED**. DR-006 persistence **prohibited**. Runtime demo policy **not activated / unapproved**.

---

## 1. Objective and non-goals

**Objective (owner wording):** a *useful, tested foundation for the actual LangGraph workflow* — not an empty module. Reconciliation of the merged contracts and the S0 schema land together in **one PR**.

**Non-goals, honoured strictly:**

- No LangGraph import, graph construction, node wiring, tool adapter, checkpointer, interrupt or resume execution.
- No LLM/Ollama call, no HTTP client, no API route, no task creation, no notification, no finalization, no UI.
- No change to any F0 / F1 / F2 / P4 service, schema, migration, route or test.
- No dependency change; no `langgraph` install.
- No claim that frozen models or private constructors establish security authority. They do not. Trust boundaries remain server-side runtime checks that this slice only *represents*.
- No invention of disputed contract semantics. Every genuine ambiguity is consolidated in §6 as an owner decision.

---

## 2. Contract sources reconciled

| Source | What S0 took from it |
|---|---|
| `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §2 | `run_id` UUIDv4; `thread_id == run_id`; `state_schema_version`/`workflow_version`/`policy_version`/`prompt_version`/`mapping_version` shapes; `as_of_utc` format; idempotency sha256; unknown `state_schema_version` → terminal failure |
| §3 | P0 model shapes: `ProvenanceRef`, `ExtractedFact`, `ObservationView`, `ComparisonResult`, `VerificationIssue`, `ReviewFlag`, `ClaimCitation`, `DraftSummary`, `TaskDraft`, `AgentError`, `ExtractionAttempt`, `retry_counts` |
| §4.1 / §4.2 | Node/tool allowlist per node; detail payload iff the node makes a bounded decision; transitions incl. `fact_verify_gate → needs_verification` and `awaiting_decision → finalize_actions` |
| §8 | Collection bounds: 5 documents, 20 observations, 40 extraction facts, 20 verified facts, 20 flags, 20 claims, 10 attempts, 40 events, 5 pending tasks, 5 created task ids, 10 errors, retries ≤ 5 |
| `docs/contracts/openapi.phase0.yaml` | `TraceEvent` discriminated detail shapes; `TriageEventDetail` / `ValidationEventDetail` / `GateEventDetail` / `FinalizeEventDetail` |
| `docs/contracts/TOOL_CONTRACTS.md` §3.4 | Comparison admissibility: `validation != rejected`, patient scope, unit match, `measured_at ≤ as_of_utc + 5 min`; skip codes encoded into `ExclusionReason` |
| `docs/contracts/DATA_DICTIONARY.md` §2.18 | Extracted/verified fact and observation columns and enum sets |
| `docs/architecture/ADR-0006-…` | Typed node-trace detail shapes |
| `backend/app/services/p5_run_foundation.py` | `WORKFLOW_VERSION`, `STATE_SCHEMA_VERSION`, `POLICY_REFERENCE_VERSION` — imported as the single source of truth, not re-typed |
| `backend/app/services/p5_run_gate.py` | F1 `unavailable_reason` closed set (20 values) — scanned by test, not duplicated |
| `backend/app/services/p5_evidence_bridge.py` + `schemas/p5_review_evidence.py` | F2 `contract_version="2.0.0"`, `history_policy="f2-history-365d-v1"`, `runtime_evaluable=False`, `rules_executed=False`, `policy_status="unapproved"` |
| `backend/app/services/p4_rb3_review_persistence.py` + `schemas/p4_rb3_review_persistence.py` | RB3 receipt literals, `RB3DenialReason`, `lineage_label_policy="a2_transport_label"`, DR-006 `prohibited_denied` |
| `backend/app/services/monitoring.py` | `_trust_basis` derivation — mirrored by the pure helper `derived_trust_basis`, asserted equal in tests |

---

## 3. Reconciliation matrix (§4 A–F)

Status legend: **RESOLVED** = one reading is clearly supported by the merged contracts and is implemented. **REPRESENTED** = both readings are representable in the schema without deciding policy. **OWNER** = genuine ambiguity; nothing was implemented that pre-empts the decision.

### A. Identity and versions

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| A-01 | `run_id` persisted vs. derived | `RunIdentity.run_id` is a real validated UUIDv4; `thread_id == run_id` enforced; checkpoint `thread_id` must equal it | RESOLVED |
| A-02 | `thread_id` semantics | `thread_id` is *not* a separate field on the state at all — the only thread identity is `identity.run_id`, so the two can never diverge by construction | RESOLVED |
| A-03 | Patient / doctor scope | Nested immutable `RunIdentity(patient_id, doctor_id)`; every fact, observation, gate ref, evidence ref and sealed evaluation must match it exactly | RESOLVED |
| A-04 | Which version fields exist | `workflow_version`, `state_schema_version`, `mapping_version`, `policy_version`, `prompt_version` on `RunIdentity`; F0 constants imported rather than retyped | RESOLVED |
| A-05 | Real UUID validation vs regex | Real `uuid.UUID` parse + explicit v4/v5 check + canonical lowercase round-trip (`str(uuid) == input`) | RESOLVED |
| A-06 | Timestamp format | Exactly `YYYY-MM-DDTHH:MM:SSZ`; rejects offsets, fractional seconds, lowercase `t`, space separator, impossible dates and hour 24 | RESOLVED |
| A-07 | Evaluation clock vs authorization clock | `identity.as_of_utc` is the pinned **evaluation** clock; `last_validated_at_utc` is the separate **authorization/validation** clock; gate and evidence refs require the latter and are rejected without it | RESOLVED |
| A-08 | Bounded numerics | `Decimal(max_digits=10, decimal_places=4)`; `Confidence` is `float` in `[0,1]` with `allow_inf_nan=False`; retry counts `1..5` | RESOLVED |
| A-09 | Immutable selected-source identities | `SelectedSourceManifest` with sorted-unique ids + optional typed `documents`/`observations`/`omissions` refs; `selection_fingerprint` recomputed by a validator | RESOLVED |
| A-10 | Does serialized state authorize anything? | **No.** `SharedGraphState` is pure data. `policy_status="unapproved"`, `runtime_policy_activated=False`, `runtime_evaluable=False`, `demo_only=True`, `not_for_clinical_use=True` are `Literal` fields that no input can change | RESOLVED |

### B. Typed evidence and provenance

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| B-01 | F2 DTOs vs state fields | `EvaluableEvidenceRef` carries the F2 contract version, history policy, bridge fingerprint and the exact selected document/observation ids | RESOLVED |
| B-02 | `ObservationView.value` float (P0) vs exact decimal | `Decimal` with 4 decimal places; JSON emits a **string**; JSON numbers are accepted by Pydantic and normalized — see D-07 | RESOLVED (with D-07) |
| B-03 | Self-reported vs doctor-verified trust | `trust_level` is bound to `verified_by`/`verified_at` and to `source`/`source_fact_id`/`source_document_id`; JSON tampering of `trust_level` alone is rejected | RESOLVED |
| B-04 | Corrected-fact lineage | `VerifiedFact.corrected_from_fact_id` must differ from its own `fact_id` | RESOLVED |
| B-05 | Exclusions and incomparable reasons | `EvidenceExclusion` with a closed `ExclusionReason` union = exactly the 8 codes the F2 bridge emits (`validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp`, `verified_lineage_unavailable`, `verified_mapping_unproven`, `stored_trust_source_mismatch`, `malformed_history`); `IncomparableReason` = contract §3 ∪ F2 codes | RESOLVED |
| B-06 | F2 365-day vs RB1 90-day window | The state carries `history_policy="f2-history-365d-v1"` as the only policy literal; RB1's 90-day preview is not executable and is not encoded | OWNER (D-04) |
| B-07 | VI vs DR separation | `VerificationIssue` (VI-xxx) and `ReviewFlag` (`ReviewRuleId`, DR-001/003/005/006/008/009) are distinct types with disjoint vocabularies, asserted by test | RESOLVED |
| B-08 | Comparison semantics | `ComparisonResult` is mutually exclusive: `incomparable_reason` XOR (`current_value` + `baseline_*` + `delta` + `unit`); state re-checks current value/measure type against the typed observation | RESOLVED |
| B-09 | `trust_basis` binding | State re-derives `trust_basis` from the two bound observations and rejects a mismatch; helper mirrors `monitoring._trust_basis` | RESOLVED (D-11 to confirm) |

### C. Verification and completion

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| C-01 | F1 `unavailable` vs contract `proceed/halt` | `GateEvaluationRef.decision ∈ {proceed, halt, unavailable}`; `unavailable_reason` required iff unavailable; `GateDetail.decision` stays 2-valued | OWNER (D-01) |
| C-02 | Can a stale receipt/state bool bypass revalidation? | No. `verification_gate` and `evaluable_evidence` are *references* bound to `gate_evaluation_id` + `input_fingerprint_sha256`; the state cannot carry a bare boolean "verified" flag | RESOLVED |
| C-03 | Can a checkpoint bypass? | No. `CheckpointRef` is explicitly informational; `checkpoint_diverges` is a read-only property and no validator consults it for authority | RESOLVED |
| C-04 | Can a caller-supplied blocker count bypass? | No. Blockers are typed `VerificationIssue` rows mirrored against the gate evaluation, never a scalar | RESOLVED |
| C-05 | RB3 sealed completion ≠ graph completion | `workflow_completed` (`status == completed`) and `review_evaluation_sealed` (`review_persistence.kind == "sealed"`) are **independent properties**; `SealedReviewEvaluation` requires `evaluation_completed=True` but the run may be `queued` | RESOLVED |
| C-06 | One immutable review evaluation per run | `review_persistence: ReviewPersistenceOutcome | None` — a single slot; `SealedReviewEvaluation` requires `persisted == total` | RESOLVED |
| C-07 | Exact replay only | `SealedReviewEvaluation.exact_replay` is `Literal[True]`; no auto-reuse field exists | RESOLVED |
| C-08 | No auto-reuse after corrected source | No field can express reuse. Correction is a *new run* by `ResumeAssessment.corrected_source_new_run` | RESOLVED (representation) |
| C-09 | DR-006 whole-invocation denial | `DeniedReviewPersistence` with `dr006_policy ∈ {prohibited_denied, not_present}` and an RB3 `denial_reason` | RESOLVED |
| C-10 | Runtime policy unapproved | Literal `policy_status="unapproved"` on both the state and the evidence ref | RESOLVED |

### D. Halt and resume

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| D-01 | Resumable-unchanged vs changed source identity | `ResumeDisposition.{resume_unchanged, changed_source_identity, corrected_source_new_run}` | RESOLVED (schema only) |
| D-02 | Which store is authoritative | App DB. The state is replay material; `CheckpointRef.claimed_status` never overrides `status` | RESOLVED |
| D-03 | Checkpoint = replay state only | Documented in the module docstring and enforced by absence of any authority field | RESOLVED |
| D-04 | S2/S4 reconciliation requirements | Recorded in §7 for the later slices | RESOLVED (recorded) |
| D-05 | Checkpoint / resume **implementation** | **NOT IMPLEMENTED** — out of S0 scope by owner instruction | OUT OF SCOPE |

### E. Typed node trace

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| E-01 | Four detail shapes | `TriageDetail` / `ValidationDetail` / `GateDetail` / `FinalizeDetail`, discriminated by `kind` (`DetailKind`) | RESOLVED |
| E-02 | Detail iff a bounded decision is made | `NodeEvent` enforces `detail is not None ⇔ node ∈ DETAIL_KIND_BY_NODE`, and the detail type must match the node | RESOLVED |
| E-03 | No raw text / model output / secrets | Detail fields are enums, UUIDs, bounded reason codes and small integers only; asserted by a reflective test that scans every detail field | RESOLVED |
| E-04 | Finite confidence | `Confidence` rejects `nan`/`inf`/`-inf` and out-of-range values | RESOLVED |
| E-05 | Bounded attempts | `ExtractionAttempt` bounded; `retry_counts` `1..5`; per-node keys only | RESOLVED |
| E-06 | Tool allowlist per node | `NODE_TOOLS` copied verbatim from contract §4.1; `NodeEvent` rejects a tool outside its node's allowlist | RESOLVED |

### F. Draft and approval shapes

| # | Conflict / question | Resolution | Status |
|---|---|---|---|
| F-01 | Structural only | `DraftSummary`/`TaskDraft`/`ApprovalDecision` are shapes. **Shape validation is not authentication, not grounding, not execution and not authorization.** | RESOLVED (documented) |
| F-02 | No task/notification/finalization/model execution | No such field, method or import exists; the only task-related field is `created_task_ids` (a bounded uuid5 list) and `pending_tasks` (drafts) | RESOLVED |
| F-03 | `DraftProvider` consistency | `provider=ollama` requires a `model` and `execution_status=model_ok`; `local_stub` forbids a model | RESOLVED |

---

## 4. What was implemented

### 4.1 `backend/app/agents/state.py` (new, ~1750 lines)

Pydantic v2 only (`pydantic 2.14.3` locally). No I/O, no side effects, no service import.

**Base configuration.** `Strict(BaseModel)` with `extra="forbid"`, `strict=True`, `frozen=True`. Unknown fields rejected at every level. Strict Python mode rejects `str → StrEnum`, `int/float → Decimal`, `bool → int`, `str → int`, tuple → list.

**Primitive aliases** (all Annotated, all with explicit rejection tests):

| Alias | Rule |
|---|---|
| `Uuid` | real UUIDv4, canonical lowercase |
| `UuidV5` | real UUIDv5, canonical lowercase |
| `Sha256` | `^[0-9a-f]{64}$`, rejects all-zero |
| `Iso` | exact `YYYY-MM-DDTHH:MM:SSZ`, real calendar validation |
| `SemVer` | `MAJOR.MINOR.PATCH`, numeric-only, no leading zeros, bounded width for the 12-char column |
| `MappingVersion` | `map-<semver>` |
| `PolicyVersion` | `<name>-<semver>` |
| `PromptVersion` | bounded token |
| `ExactDecimal` / `DeltaDecimal` | `Decimal(max_digits=10, decimal_places=4)` + JSON string serializer |
| `Confidence` | `float` in `[0,1]`, `allow_inf_nan=False` |
| `ReasonCode`, `ErrorCode`, `Token`, `MetadataValue` | bounded machine tokens |

**Enumerations** (26, closed, `StrEnum`): `RunStatus`, `HaltReason`, `TrustBasis`, `IncomparableReason`, `ExclusionReason`, `VerificationStatus`, `ProvenanceKind`, `Extractor`, `IssueType`, `ReviewRuleId`, `ReviewHint`, `ReviewItemState`, `DraftProvider`, `DraftExecutionStatus`, `ApprovalChoice`, `NodeName`, `NodeOutcome`, `ToolName`, `TriagePath`, `PathReason`, `ValidationOutcome`, `ViolationCode`, `DetailKind`, `GateDecision`, `GateUnavailableReason`, `ResumeDisposition`.

**Models** (32): `ProvenanceRef`, `ExtractedFact`, `VerifiedFact`, `ObservationView`, `ComparisonResult`, `EvidenceExclusion`, `VerificationIssue`, `ReviewFlag`, `ClaimCitation`, `DraftSummary`, `ApprovalDecision`, `TaskDraft`, `AgentError`, `ExtractionAttempt`, `TriageDetail`, `ValidationDetail`, `GateDetail`, `FinalizeDetail`, `NodeEvent`, `RunIdentity`, `SelectedDocumentRef`, `SelectedObservationRef`, `SelectedOmissionRef`, `SelectedSourceManifest`, `GateIssueRef`, `GateEvaluationRef`, `EvaluableEvidenceRef`, `SealedReviewEvaluation`, `DeniedReviewPersistence`, `CheckpointRef`, `ResumeAssessment`, `SharedGraphState`.

**Pure helpers:** `derived_trust_basis(current, baseline)`, `selection_fingerprint(payload)`, `derive_task_id(namespace, action_key)`.

**`SelectedSourceManifest.build()`** validates each member through its own `TypeAdapter` **before** the digest is computed — no `model_construct` escape hatch. The returned manifest is re-validated in full.

### 4.2 `SharedGraphState` cross-field invariants

| Validator | Invariant |
|---|---|
| `_scope_and_uniqueness` | `updated_at ≥ started_at`; checkpoint thread == run id; unique attempt/fact/observation/issue/flag/task ids; unique action keys; unique created task ids; unique comparison current ids; patient scope of every fact and observation |
| `_evidence_binding` | every selected observation present and identical to its typed row; a verified fact cannot project a pending/rejected extracted fact; comparison current value and measure type match the observation; `trust_basis` re-derived |
| `_references` | gate ref scope; gate ref requires validation clock; evidence ref scope/version/as-of equality; evidence documents and observations equal the manifest; evidence bound to the exact gate id/version/fingerprint; evidence only after `proceed`; sealed evaluation scope + gate binding + bridge binding; sealed requires the evidence it was computed from |
| `_lifecycle` | `halt_reason` iff halted status; `needs_verification → unverified_facts`; `failed_retryable → retry_exhausted`; no approval before the draft; `finalizing/completed` need an approve-or-edit decision and a draft; `awaiting_decision` needs a draft and no decision; tasks only after a decision; `created_task_ids ⊆ pending task ids`; finalize detail agrees with the approval and created ids; retry counts `1..5` |
| `_gate_binding` | a halting gate cannot coexist with a post-draft status; comparisons/flags/draft require `proceed`; post-draft statuses require `proceed`; `needs_verification` requires a recorded halt; `verification_issues` mirror the gate's blocking issues (except when the gate is `unavailable`) |

**Read-only projections (never serialized, never authority):** `workflow_completed`, `review_evaluation_sealed`, `checkpoint_diverges`.

### 4.3 `backend/tests/p5/test_p5_state.py` (new, 124 collected tests)

Matrix M01–M20 maps one-to-one onto the owner's 20 required areas:

| Matrix | Area | Tests |
|---|---|---|
| M01 | initial state, JSON round-trip, exact decimals, version constants, immutable identity | 5 |
| M02 | `thread_id == run_id`; checkpoint claim is informational | 2 |
| M03 | malformed UUID / hash / version / UTC rejected (44 negative + 10 positive cases); non-string input; real calendar date | 56 |
| M04 | unknown fields; strict-mode coercions; JSON strings not coerced; bounded metadata; bounded confidence | 12 |
| M05 | collection caps | 4 |
| M06 | non-finite and out-of-range values; floats never silently accepted | 14 |
| M07 | patient scope; gate requires the validation clock | 2 |
| M08 | provenance shape; trust+source inseparable; extracted-fact/verified lineage; manifest shape; self-verifying fingerprint | 5 |
| M09 | self-reported cannot be promoted by any input path; manifest cannot relabel; `model_copy` bypass caught by revalidation | 3 |
| M10 | pending/rejected cannot be projected as verified | 1 |
| M11 | comparable/incomparable mutual exclusion; comparison binding to observations | 2 |
| M12 | closed disjoint vocabularies; issues mirror the gate | 2 |
| M13 | gate decision combinations; F1 vocabulary equality; state reactions per decision | 3 |
| M14 | detail iff decision; discriminated union; no free text; per-node tool allowlist; OpenAPI vocabulary equality | 5 |
| M15 | retry bounds | 1 |
| M16 | sealed ≠ workflow completion; sealed bound + all-or-nothing; denied persistence is an outcome; resume classification | 4 |
| M17 | honesty literals unflippable; `model_copy` documented | 2 |
| M18 | deserialized state is shape not authority; tasks only after decision; lifecycle invariants; evidence binding; draft provider consistency | 5 |
| M19 | no shared mutable defaults | 1 |
| M20 | import side effects (subprocess); source import scan; vocabulary single sources; full-population round-trip | 4 |

---

## 5. Verification executed in this session

All commands were run from the repository root. Local interpreter is **CPython 3.11.2**, a **disclosed deviation** from the CI baseline of 3.12. No retry on 3.12 was attempted.

| Check | Command | Result |
|---|---|---|
| Focused P5-S0 | `pytest backend/tests/p5/test_p5_state.py` | **124 passed / 0 failed / 0 skipped** in 0.77 s |
| Focused + safety + OpenAPI | `pytest backend/tests/p5 backend/tests/test_safety_guards.py backend/tests/test_openapi.py` | **206 passed** in 27.41 s |
| P5 + P4 + API regression | `pytest backend/tests/p5 backend/tests/p4 backend/tests/test_openapi.py backend/tests/test_safety_guards.py backend/tests/test_version.py backend/tests/test_health.py` | **604 passed** in 83.76 s |
| Full backend | `pytest backend/tests` | **2 failed, 1418 passed** in 268.65 s — see §5.1 |
| Collection | `pytest backend/tests --collect-only` | **1420 collected**; P3 **443**; P5 **183** |
| Base collection (verified in a detached worktree at `121e1dbe…`) | `pytest backend/tests --collect-only` | **1294**; P3 **443**; P5 **59** |
| Ruff lint | `ruff check .` | **All checks passed** (exit 0) |
| Ruff format | `ruff format --check .` | **149 files already formatted** (exit 0) |
| Alembic smoke | `alembic upgrade head` → `downgrade base` → `upgrade head` + `check_alembic_smoke.py` | **PASS**, head `0008_p4_rb3_review_persistence`, exit 0 for all four commands |
| OpenAPI contract | `scripts/python/check_openapi.py` | **PASS (17 paths / 18 operations, 43 schemas)**, exit 0 |

### 5.1 Full-backend failures — both expected, neither weakened

```
FAILED backend/tests/p2/test_p2_scope_guards.py::test_no_later_phase_module_exists
FAILED backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes
2 failed, 1418 passed in 268.65s
```

**(1) `test_no_later_phase_module_exists` — NEW conflict discovered in this session.**
`backend/tests/p2/test_p2_scope_guards.py:171` asserts `not (BACKEND_APP / "agents").exists()`. That P2-era guard forbids the creation of an `agents` package until the agent phase. The owner's P5-S0 authorization explicitly lists `backend/app/agents/__init__.py` and `backend/app/agents/state.py` as two of the six authorized paths, so the guard and the authorization now contradict each other directly.

- The guard was **not modified** — it is not one of the six authorized paths, and weakening a scope guard is forbidden.
- The failure is therefore **expected and honest**, not a regression in behaviour.
- This is a **blocking owner decision (D-14)**: either authorize a narrow carve-out for `backend/app/agents/` in that P2 guard, or direct that P5-S0 be relocated. The agent does not choose.

**(2) `test_handoff_test_count_matches_the_suite_it_describes` — the known collection guard.**
It asserts that `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` quotes the current whole-backend collection. The collection moved `1294 → 1420` because 124 new P5-S0 tests plus 2 new parametrized P2 scope-guard cases (`test_application_modules_are_typed[path80]`, `[path81]`, which **pass**) now exist.

- `PHASE_3_WINDOWS_ACCEPTANCE.md` was **not modified** — it is not an authorized path, and a prior owner authorization covered only the earlier pairing, not this one.
- The guard was **not weakened**.
- **Owner decision D-09**: authorize the append-only collection note (`**1420 collected**, of which **443** are the P3 suite`) as a separate documentation-only step.

### 5.2 Explicitly NOT executed

- Windows PowerShell / `test_all.ps1` — **NOT RUN**, owner laptop only. No Windows claim is made anywhere in this document.
- Any LangGraph, Ollama, LLM, GPU or browser check — not applicable to this slice and not run.
- Exact-head GitHub Actions — read from CI after push, reported in the PR, not asserted here.
- Frontend build — unchanged by this slice; read from CI only.

---

## 6. Owner decisions required

Nothing below was implemented in a way that pre-empts the decision. Where the schema must pick *something* to be executable, the choice is listed and reversible.

| ID | Question | What S0 does today | Options |
|---|---|---|---|
| **D-01** | `GateDetail.decision` is `[proceed, halt]` in the OpenAPI + DB CHECK, but the F1 receipt adds `unavailable` | `GateDetail.decision` stays 2-valued; `unavailable` is carried by `GateEvaluationRef.decision` and `GateUnavailableReason` | (a) keep the split; (b) widen the OpenAPI/DB enum to 3 values; (c) add a separate `unavailable` detail kind |
| **D-02** | Contract §3 allows `ProvenanceRef.raw_text ≤ 500` but the safety rule forbids raw text in traces | `ProvenanceRef.raw_text` exists on the *evidence* model (not on any trace detail) with `max_length=500` | (a) keep on evidence only; (b) drop it entirely; (c) replace with a span locator only |
| **D-03** | `ComparisonResult.incomparable_reason` includes `stale_baseline`, which no current code emits | `stale_baseline` **is** kept in the closed union `no_baseline, unit_mismatch, stale_baseline, missing_timestamp, not_admissible` so that a contract-conformant producer is representable; no validator requires it | (a) confirm retention as reserved; (b) remove it from the contract; (c) define when it fires |
| **D-04** | F2 uses a 365-day history window; RB1's 90-day preview is non-executable | Only `f2-history-365d-v1` is representable | (a) confirm 365 days; (b) add a bounded window parameter; (c) keep 90 days for RB1 |
| **D-05** | `TaskDraft.task_id` is `uuid5(namespace, action_key)` but no contract pins the namespace | `derive_task_id(namespace, action_key)` takes the namespace as an argument; **no namespace is invented** | (a) owner pins a namespace constant; (b) derive from `run_id`; (c) defer to S2 |
| **D-06** | `prompt_version` format is unspecified (`draft-v1` is the only example) | Bounded token `^[a-z0-9][a-z0-9._-]{0,63}$` | (a) confirm; (b) require semver; (c) require `draft-vN` |
| **D-07** | Pydantic accepts JSON *numbers* for `Decimal` fields and normalizes them (JSON `1e2` → `Decimal("100")`); Python-mode floats are rejected | JSON numbers accepted and normalized; JSON output is always a string; Python floats rejected | (a) accept as-is; (b) force JSON-string-only via a pre-parse hook; (c) document as a known limitation |
| **D-08** | `model_copy(update=...)` bypasses validation by Pydantic design | Documented in the module docstring and proven by two tests that re-validate and catch the forgery | (a) accept + require re-validation at trust boundaries; (b) forbid `model_copy` by lint rule; (c) wrap construction behind a private factory (still not a security boundary) |
| **D-09** | Collection guard pairing must move `1294/443 → 1420/443` | Not edited; guard fails as designed | (a) authorize the append-only note; (b) hold the note and accept the red guard; (c) re-scope the guard |
| **D-10** | Is `CheckpointRef.claimed_status` ever authoritative? | No — informational only; `checkpoint_diverges` is a read-only hint | (a) confirm; (b) drop the field entirely for S2/S4 |
| **D-11** | Should `trust_basis` be *derived* by the schema or *supplied* by the caller? | Supplied by the caller, then re-derived and checked by the state validator | (a) confirm; (b) make it a computed field and remove it from input |
| **D-12** | Must `verification_issues` mirror the gate's blocking issues exactly? | Yes, except when the gate decision is `unavailable` | (a) confirm; (b) allow a subset; (c) allow a superset |
| **D-13** | A `doctor_verified` observation whose data check failed (`validation=rejected`) — representable or rejected by type? | **Representable but labelled**: the row exists, trust is provenance not validity, and the F2 admissibility predicate excludes it downstream | (a) confirm; (b) reject at the type level; (c) force `trust_level` downgrade |
| **D-14** | **NEW / BLOCKING** — P2 scope guard `test_no_later_phase_module_exists` forbids `backend/app/agents/` from existing, but P5-S0 was authorized to create it | Guard untouched; suite honestly red at that one test | (a) authorize a narrow carve-out for `backend/app/agents/` only; (b) relocate P5-S0 state to another package; (c) hold P5-S0 |

---

## 7. Requirements recorded for later P5 slices (not implemented here)

- **S1 (tool adapters):** must consume these types without widening them; no new free-text fields; no trust promotion.
- **S2 (orchestrator + N2 gate + checkpoints):** must treat the app DB as authoritative and the checkpoint as replay material only; must re-run the gate rather than trust a deserialized receipt; must not carry `policy_status` forward as approval.
- **S4 (N6 interrupt/resume + restart reconciliation):** must classify resume via `ResumeAssessment`; a corrected source identity must produce a **new run**, never an in-place resume over a sealed evaluation; `CheckpointRef.claimed_status` must never be read as authority (D-10).
- **S5 (gold summaries + benchmark):** must not treat `review_evaluation_sealed` as workflow completion.

---

## 8. Safety-boundary review

**What this change could make the system do:** nothing at runtime. `state.py` is imported by tests only; no service, route, migration, task, notification or model runtime imports it, and no code path in the repository constructs `SharedGraphState` outside the test suite.

**Evidence it still cannot diagnose, prescribe, message or self-approve:**

- No diagnostic, prescriptive or dosing vocabulary exists in the module (asserted by `test_p1_implements_no_clinical_capability`, which scans `backend/app/**`).
- No messaging, notification or HTTP import exists (asserted by `test_backend_has_no_forbidden_imports` and by M20's own import scan).
- No approval can be self-granted: `ApprovalChoice` values can only be *represented*; the lifecycle validator requires a draft and a decision, and nothing in this slice can produce either.
- Honesty literals are `Literal` types, so no JSON or Python input can set `runtime_evaluable=True` or `policy_status="approved"`.

**What the tests cannot prove:** they prove schema behaviour. They do not prove that a future graph, tool adapter or persistence layer will use these types correctly, nor that any runtime authorization check exists. That is precisely the unresolved runtime-check surface listed in §7 and in D-08.

---

## 9. Iteration history (honest)

The first full run of the new test file produced **26 failed / 14 passed**. Causes, all fixed in this session:

1. `EvaluableEvidenceRef` and `SealedReviewEvaluation` declared required `Literal` aliases (`contract_version`, `history_policy`, `rb3_fingerprint_version`) that fixtures did not supply → defaults added matching the F2/RB3 service constants.
2. Four `@model_validator(mode="after")` methods were annotated `-> None` and returned nothing; under pydantic 2.14 this emits `UserWarning: A custom validator is returning a value other than self`, which `filterwarnings=["error"]` escalates to a failure → annotated `-> Self` and `return self`.
3. Strict-mode fixtures passed raw strings for enum-typed fields → fixtures now pass enum instances.
4. Fixture builders used `helper(**overrides)` producing duplicate keyword arguments → builders now merge dicts.
5. A `GateEvaluationRef` with `decision=halt` and no issues was accepted → genuine validator gap, fixed (`halt records at least one blocking issue`).
6. `model_metadata` accepted an uppercase key and a 200-character value → genuine validator gap, fixed by typing the mapping `dict[Token, MetadataValue]` with `max_length=8`.
7. `trust_basis` check rejected a legitimate `mixed` label when only the current observation was present in state → fixed.
8. Error-precedence: several tests matched a message produced by a *different* validator. `_gate_binding` now runs after `_lifecycle`, and the halting-gate check runs first inside it, so the most specific invariant reports.

The final state is 124/124 with no `pytest.warns` suppression and `filterwarnings=["error"]` active.
