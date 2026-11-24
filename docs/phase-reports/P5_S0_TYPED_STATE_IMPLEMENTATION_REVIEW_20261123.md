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

### 5.2 Exact-head GitHub Actions

At head `e70d2ea9b5cc6446e06f336b40e83bdc3df73052` (push [#45277330559](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277330559), pull_request [#45277408623](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277408623)): both COMPLETED / **FAILURE**.

| Job | Result |
|---|---|
| Frontend (Node 22) | **SUCCESS** |
| Backend (Python 3.12) — Ruff lint | **SUCCESS** |
| Backend (Python 3.12) — Ruff format check | **SUCCESS** |
| Backend (Python 3.12) — Backend tests | **FAILURE** |
| Backend — Alembic smoke, OpenAPI, repository scanner | **SKIPPED — not reached**, so no CI claim is made for them |

**Attribution honesty:** the CI job log could not be downloaded in this sandbox (the logs endpoint redirects to a blob host outside the permitted egress allowlist). The failing-test identity was therefore **not read from CI**; it is **inferred** from the byte-identical local run at the same clean tree, where exactly `test_no_later_phase_module_exists` and `test_handoff_test_count_matches_the_suite_it_describes` fail and nothing else does (re-verified at the committed HEAD with a clean `git status`: 2 failed in 3.90 s).

**This is not a green run and is not presented as one.** The two failures are the guard collisions in §5.1 (D-14, D-09), neither of which was weakened.

### 5.3 Explicitly NOT executed

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

---

## 10. Round 2 — consolidated independent-review closure (2026-11-24)

**Authorization.** Repository comment [`7122838674`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/47#issuecomment-7122838674) — `Muhammed-Fathi`, `author_association=OWNER`, created `2026-11-24T05:19:23Z`, marker `APPROVE-P5-S0-D09-D14-BOUNDED-COMPATIBILITY`, issued at reviewed HEAD `f6394f1c6e670562dae74bafef5190c396c629d2`. It authorizes two bounded compatibility exceptions only (D-14 exact-path allowlist, D-09 append-only collection pairing), requires both to be recorded in `PHASE_PROGRESS.md` **before** the exceptional paths are edited, and requires fresh explicit authorization if the measured pairing changes. No P3/P4 authorization was reused.

**What changed in the two S0 source paths.** `backend/app/agents/state.py` was rewritten around the review findings (not patched): 2377 lines, 29 `StrEnum` vocabularies, 34 models, 31 validators. `backend/tests/p5/test_p5_state.py` was rewritten as a 150-test matrix (was 124). Neither file touches any F0/F1/F2/RB* service, schema, migration, policy, fixture, OpenAPI route or CI workflow.

### 10.1 R01–R07 closure evidence

| Finding | Closure in `state.py` (symbol) | Executable evidence (test) |
|---|---|---|
| **R01** field-specific UUID validation and exact projection sources | `_canonical_uuid` (v4 **or** v5), `_stored_uuid`, `_run_uuid` (**v4 only**), `_task_uuid` (**v5 only**); `RunIdentity.thread_id` is derived from `run_id`, never caller-supplied; `GateEvaluationRef.gate_evaluation_id` and `EvaluableEvidenceRef.gate_evaluation_id` are optional because the F1 receipt genuinely does not carry the stored gate row id, while the F2 DTO does; `VerifiedFact` documents its three projection sources field by field (F2 DTO, stored `ExtractedFact.patient_id`, stored `FactVerification`) | `test_m03_malformed_primitives_are_rejected`, `test_m03_well_formed_primitives_are_accepted`, `test_m01_identity_is_immutable_as_a_block`, `test_r01_genuine_stored_identities_include_uuid5_observations`, `test_r01_genuine_stored_run_projects_every_accepted_producer`, `test_r01_genuine_seeded_observation_rows_are_representable` |
| **R02** RB3 replay arithmetic and durable bounds | `SealedReviewEvaluation` pins `policy_reference_sha256`, `rb3_fingerprint_version="rb3-full-input-1.0.0"`, `dr006_policy="prohibited_denied"`, and binds `gate_evaluation_id` / `evaluation_id` / `audit_event_id`; `MAX_PERSISTED_ITEMS=12`, `MAX_PERSISTED_LINKS=24`, `MAX_MERGED_EXCLUSIONS=200`; `_gate_binding` requires first-call persisted counts to equal the totals and replay persisted counts to be 0 with non-zero totals; `LayeredExclusions.l3_merged` is the **deduplicated union** of l1 and l2, never their sum | `test_m16_first_persistence_and_exact_replay_are_both_representable`, `test_m16_exclusion_counts_follow_the_deduplicated_merged_semantics`, `test_m16_sealed_evaluation_pins_the_policy_sha_fingerprint_and_dr006`, `test_m16_sealed_evaluation_is_bound_to_its_evidence_and_scope`, `test_m16_denied_persistence_is_an_outcome_not_a_completion`, `test_r01_genuine_stored_run_projects_every_accepted_producer` (real replay: `review_items_persisted == 0`, same `evaluation_id` and `audit_event_id`) |
| **R03** HALT is decided by recorded issues; precedence and exact issue binding | `GateEvaluationRef._decision_consistency`: `proceed` records no issue and zero blocking facts, `halt` requires ≥1 issue, `unavailable` may keep both; `blocking_fact_count` must equal `_distinct_fact_count(issues)`; precedence is encoded by `_lifecycle` + `_gate_binding` so an `unavailable` gate can never be read as `halt` or `proceed`; the F1 receipt id, the stored `RunGateEvaluation.id` and the P3 `VerificationIssue.issue_id` are three distinct id spaces and are never cross-assigned | `test_m13_gate_decision_combinations`, `test_m13_unavailable_reason_vocabulary_matches_the_f1_service`, `test_m13_state_reactions_to_each_decision`, `test_m12_gate_issue_identity_is_full_not_just_the_type`, `test_m16_sealed_evaluation_does_not_complete_the_workflow` |
| **R04** context-free decimal serialization and arithmetic | `_decimal_text` serializes from `Decimal.as_tuple()` (never `normalize()`, so `140.50` and `140.5` stay distinguishable and no ambient rounding applies); `_EXACT_CONTEXT` is an explicit local `decimal.Context(prec=60, ROUND_HALF_EVEN, traps=[InvalidOperation])` used by `exact_delta`; `_decimal_string_only` rejects `bool`/`int`/`float`, constructs `Decimal(text)` explicitly and converts `InvalidOperation` into a `ValueError` (a malformed string is a validation error, never an escaping `decimal` exception) | `test_r04_exact_values_and_deltas_under_the_default_context`, `test_r04_behaviour_is_identical_under_a_hostile_decimal_context` (`prec=3`, `ROUND_UP`, `InvalidOperation` trapped), `test_m01_decimal_text_is_canonical_and_exact` |
| **R05** strong evidence binding | `_evidence_binding`: a comparison current must resolve to a `SELECTED_CURRENT` row that passes the data check, with matching measure/unit/value; a baseline must resolve to a `HISTORY` row that precedes the current and passes the data check; `delta` must equal `exact_delta(current, baseline)`; `trust_basis` is **re-derived** from the two typed trust levels (`derived_trust_basis`) and never taken from input; `_selected_current_roles` pins the `SELECTED_CURRENT` set to the F2 `selected_observation_ids`; `EvaluableEvidenceRef.history_policy` is the F2 label and a 90-day RB1 label beside an F2 evidence reference is rejected | `test_m11_state_binds_comparison_values_and_trust_basis_to_observations`, `test_m11_history_cannot_become_selected_current_and_delta_must_follow`, `test_m11_window_labels_are_distinguishable_and_never_relabelled`, `test_m11_comparable_and_incomparable_shapes_are_mutually_exclusive`, `test_m18_evidence_reference_is_bound_to_the_selection_and_gate` |
| **R06** lifecycle and approval | `_lifecycle`: `awaiting_decision` requires a draft and no recorded decision; `completed` requires an approval **and** a draft, carries zero pending tasks and no `finalize_actions` event; a rejection may complete with zero tasks/notifications; `_gate_binding` refuses to let a sealed evaluation or a denied RB3 outcome stand in for workflow completion; `test_m16_denied_persistence_is_an_outcome_not_a_completion` keeps `DeniedReviewPersistence` a separate outcome; `test_m18_tasks_exist_only_after_a_decision_and_within_its_task_ids` forbids task ids outside the decision | `test_m18_status_lifecycle_invariants`, `test_m16_resume_classification_distinguishes_unchanged_changed_and_corrected`, `test_m18_draft_provider_and_execution_status_are_consistent` |
| **R07** producer-aligned bounds, no silent truncation, no bypass | every bound equals the producer's own constant (`MAX_FACTS=40`, `MAX_HISTORY_OBSERVATIONS=100`, `MAX_SELECTED_CURRENT=6`, `MAX_SELECTED_DOCUMENTS=5`, `MAX_PERSISTED_ITEMS=12`, `MAX_PERSISTED_LINKS=24`, `MAX_MERGED_EXCLUSIONS=200`, `MAX_EVENTS=40`, `MAX_ERRORS=10`, `MAX_PENDING_TASKS=5`, `MAX_BLOCKING_FACTS=40`); `SelectedSourceManifest.build` raises on unknown keyword arguments instead of dropping them; `SharedGraphState.revalidate()` re-parses from JSON text, so `model_copy`/`model_construct` and mutated list contents cannot skip validation; honesty literals are `Literal` types | `test_m05_upstream_fact_and_history_evidence_is_not_truncated`, `test_m05_rb3_exclusions_and_items_use_the_durable_maxima`, `test_m05_nested_caps_blocks_counts_and_attempts`, `test_m08_manifest_build_rejects_unknown_members`, `test_m09_copy_bypass_is_caught_by_revalidation`, `test_m09_mutated_container_is_caught_by_revalidation`, `test_m17_honesty_literals_cannot_be_flipped_through_any_input`, `test_m17_model_copy_bypass_is_documented_and_revalidation_restores_the_boundary` |

### 10.2 Producer compatibility evidence (executed, not asserted from reading)

`test_r01_genuine_stored_run_projects_every_accepted_producer` drives the **real accepted services** against a seeded SQLite database — `seed_demo_data` → `create_run_foundation` (F0) → `evaluate_run_verification_gate` (F1) → `build_run_evaluable_review_evidence` (F2) → `persist_run_review_items` twice (RB3 first write and replay) — and then projects every genuine receipt into the S0 models and assembles one `SharedGraphState` from them. Facts it pins, each of which contradicted an earlier assumption:

- the F1 `RunGateReceipt` has **no** `gate_evaluation_id` attribute; the S0 ref therefore leaves it `None`, and the stored `RunGateEvaluation.id` is projected as a **separate** identity space;
- the F2 `ComparisonV2` carries **no** `history_policy` field and **no** values — the window label comes from `p5_evidence_bridge.COMPARISON_HISTORY_VERSION`, which the bridge folds into its own canonical fingerprint;
- the F2 `ObservationV2` carries **no** validation state and **no** verifier, so `validation`, `verified_by` and `verified_at` are projected from the authoritative stored `Observation` row and the DTO is cross-checked against it rather than assumed;
- the F0 `RunFoundationReceipt` exposes only ids, so `SelectedSourceManifest` members are projected from the stored `Document` / `Observation` rows;
- the synthetic observation fixture uses UUIDv5 ids and the run uses UUIDv4, exactly as the primitives require;
- the RB3 replay genuinely returns `review_items_persisted == 0` with non-zero totals and the same `evaluation_id` / `audit_event_id`.

`test_m20_vocabulary_single_sources_of_truth` re-derives the closed vocabularies from the services and the persisted CHECK constraint instead of trusting a copy: `IssueType` and `TrustLevel` from `app.core.enums`, the `DR-*` ids from the `ck_review_item_review_item_rule_allowed` constraint, and every numeric bound from the producing module.

### 10.3 Owner decision disposition (D-01 … D-14)

| Decision | Disposition in this revision |
|---|---|
| D-01 two-valued `GateDetail.decision` | Kept two-valued; F1 `unavailable` is the separate `GateDecision.UNAVAILABLE` outcome with `GateUnavailableReason` mirroring the service vocabulary; no DB or OpenAPI enum change. |
| D-02 bounded raw text only in `ProvenanceRef.raw_text` | Kept bounded and confined to `ProvenanceRef`; trace details carry no free text (`test_m14_trace_details_carry_no_free_text_or_unbounded_fields`). No new span persistence authority. |
| D-03 `stale_baseline` reserved | Kept inside the closed `IncomparableReason` union as reserved vocabulary; no service is claimed to emit it. |
| D-04 F2 365-day vs RB1 90-day | Typed labels `ComparisonWindow.F2_365D` / `RB1_90D`; `RB1_LOOKBACK_DAYS` is `Literal[90]` and `F2_HISTORY_POLICY` is `Literal["f2-history-365d-v1"]`, both re-derived from the producers; no configurable lookback; relabelling across an F2 evidence reference is rejected. |
| D-05 namespace and action key deferred to S4 | `derive_task_id(namespace, action_key)` is a pure UUIDv5 derivation helper only — no namespace constant is invented and no task is created. |
| D-06 bounded version token | `PromptVersion` is a 32-character lowercase token; `RunIdentity.prompt_version` stays `None` because F0 persists no such column (`test_m20_f0_persists_no_prompt_version_and_the_state_does_not_claim_it`). |
| D-07 JSON decimal strings only | Enforced in `_decimal_string_only` (JSON numbers and non-finite values rejected, Python-mode `Decimal` accepted) and made independent of the ambient context in `_decimal_text` / `exact_delta`. |
| D-08 copy/construct bypass documented | `revalidate()` is the documented boundary; `frozen=True` and private constructors are explicitly described as **not** authority; shallow container mutability is addressed by re-parsing from JSON text. |
| D-09 collection pairing | Executed append-only under the verified comment for the authorized literal, then **re-authorized in session** for the changed pairing `**1447 collected**, of which **443** are the P3 suite` after the S0 test rewrite moved the whole-backend total; recorded in `PHASE_PROGRESS.md` before the edit. |
| D-10 app DB authoritative | `CheckpointRef.claimed_status` is informational only (`test_m02_checkpoint_claim_is_informational_never_authority`); the integration test projects manifest and observation members from stored rows. |
| D-11 explicit `trust_basis` | `ComparisonResult.trust_basis` is re-derived from the typed trust levels on every validation pass and cannot be supplied; a missing baseline cannot yield `mixed` or `doctor_verified`. |
| D-12 full semantic issue identity | `GateIssueRef` carries type, reason code, document id, fact ids and message; `test_m12_gate_issue_identity_is_full_not_just_the_type` rejects a mirrored issue that differs in any one of them; id spaces stay distinct and no P3 issue id is manufactured. |
| D-13 `doctor_verified` + `validation=rejected` | Representable and labelled (`test_m08_observation_trust_and_source_provenance_are_inseparable`, `test_m13_*`); such a row is never eligible as a comparison current or baseline (`_evidence_binding`). |
| D-14 P2 scope guard | Executed exactly as authorized: blanket `agents` prohibition replaced by the exact two-path allowlist in `backend/tests/p2/test_p2_scope_guards.py`, with `_stray_agent_modules()` and a rejection test covering orchestrator, tool adapter, checkpoint, LLM and nested sub-packages. |

### 10.4 Executed verification (Linux CPython 3.11.2 — disclosed deviation from CI 3.12)

Focused S0 suite **150 passed / 0 failed**; P5 suite **209 passed**; P2 guards **92 in file / 282 in directory, 0 failed** (D-14 now green, including the new rejection test); P3 suite **443 passed** (D-09 guard now green); P4 suite green; F0/F1/F2 files 18 / 24 / 17 collected and passing; **full backend 1447 passed / 0 failed in 258 s**; Ruff lint and format PASS (149 files); Alembic smoke PASS (head `0008_p4_rb3_review_persistence`, upgrade → downgrade → upgrade); OpenAPI PASS (17 paths / 18 operations / 43 schemas); repository scan PASS (303 tracked files, 7 secret patterns, 4 claim patterns). **Collection measured: 1447 / 443 / 209.**

### 10.5 What this revision still does not claim

No graph, tool adapter, checkpoint, interrupt, resume, LLM, API, UI, approval execution, task or notification exists. `state.py` is imported by tests only. Schema validity is not authentication, grounding or authorization: a structurally valid `SharedGraphState` remains non-authoritative, and `revalidate()` re-establishes shape, not trust. Windows PowerShell / `test_all.ps1` was **not** run by the agent and no Windows result is claimed. Exact-head GitHub Actions results are read from CI after push and reported separately, never asserted from a local run.

---

## 11. Round 3 — targeted independent-review corrections (2026-11-24)

**Scope discipline.** This round is *targeted*, not a rewrite: `backend/app/agents/state.py` was edited in place (R2-02 … R2-06), existing tests were strengthened where the finding concerned them, and new tests were added for the new behaviours. No accepted Round-2 behaviour was removed, no case was deleted to preserve a count, and no F0/F1/F2/RB* service, schema, migration, policy, fixture, OpenAPI route or CI workflow changed.

**Authorization.** D-14 remains authorized by comment [`7122838674`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/47#issuecomment-7122838674). D-09 required fresh authorization again because the pairing moved (1447 → **1466**); it was obtained in session and recorded in `PHASE_PROGRESS.md` **before** the handoff was edited.

### 11.1 Finding → code → test

| Finding | Code correction | Executable evidence |
|---|---|---|
| **R2-01** Windows path portability + D-14 preservation | `_stray_agent_modules()` now reports `path.relative_to(app_root).as_posix()`, so a Windows run reports `agents/state.py` and never a backslash path; the extraction-module scope assertion was **restored to `test_no_later_phase_module_exists`** where it originally lived; the two-file allowlist (`agents/__init__.py`, `agents/state.py`) is unchanged and no directory-wide exception exists | `test_no_later_phase_module_exists`, `test_d14_allowlist_rejects_every_other_agents_module` (now also asserts every reported path contains `/` and no `\`, so the comparison is platform-independent) |
| **R2-02** actual observation admissibility | `ObservationView.admissible` returns `validation is not ValidationState.REJECTED`, mirroring `monitoring.admissibility_reason`, which returns `"validation_rejected"` and nothing else for the data check. A warning is neither promoted nor hidden: `validation` keeps its stored value and `trust_level` is untouched | `test_r202_ok_with_warning_is_admissible_and_rejected_is_not`, `test_r202_eligible_warning_rows_participate_as_current_and_baseline`, plus genuine producer evidence in `test_r01_genuine_stored_run_projects_every_accepted_producer` |
| **R2-03** incomplete comparison binding | `_evidence_binding` now always validates a comparable `delta` against the **resolved** observation values (`current.value`, `baseline.value`), so omitting the optional projected values cannot hide a wrong delta; `_selected_current_roles` binds the `SELECTED_CURRENT` set to the **immutable selected manifest** whether or not an F2 reference exists; a baseline must lie inside the **labelled** window (`F2_HISTORY_LOOKBACK_DAYS=365`, `RB1_HISTORY_LOOKBACK_DAYS=90`); a no-baseline row cannot claim `comparable` | `test_r203_delta_is_always_checked_against_the_resolved_rows`, `test_r203_unselected_current_is_rejected_by_the_immutable_manifest`, `test_r203_baseline_must_lie_inside_the_labelled_window`, `test_r203_contradictory_no_baseline_and_comparable_shapes_are_rejected`, `test_r203_structural_binding_does_not_claim_latest_prior_correctness` |
| **R2-04** typed trace contract | new `TraceGateIssue` (identity only: issue type, reason code, document id, fact ids — **no message field**); `GateDetail.issues` is now `list[TraceGateIssue]`; `GateDetail.from_gate_evaluation()` derives the trace from a gate outcome and raises for `unavailable` instead of fabricating `proceed`/`halt`; `GateIssueRef` keeps the canonical rendered message because it is the gate/evidence reference; `_trace_gate_consistency` now requires only the **latest** gate event to mirror the current evaluation and treats earlier events as historical, recording the association as an S2 obligation | `test_r204_gate_detail_projection_keeps_identity_and_drops_the_message`, `test_r204_every_nested_trace_payload_is_free_of_arbitrary_text` (recursive walk over every serialized detail and every nesting node event, with a negative control that detects free text when present), `test_r204_only_the_latest_gate_event_mirrors_the_current_evaluation` |
| **R2-05** exact layered exclusion semantics | `_all_or_nothing` now validates **content**, not just counts: `l3_merged` must equal `_sorted_exclusions([*l1, *l2])` — the canonical deduplicated union, as RB3 computes it — `excluded_evidence` must equal `l3_merged` exactly, l1/l2 must be in canonical order, and `l0_lineage_checks` stays outside the merge | `test_r205_equal_length_contradictory_exclusion_lists_are_rejected` (same lengths, reason replaced; same lengths, observation identity replaced; `excluded_evidence` ≠ l3; non-canonical order), `test_r205_l0_lineage_checks_stay_separate_from_the_merged_layer`, `test_r205_first_write_and_zero_total_replay_arithmetic_are_preserved` |
| **R2-06** remaining structural consistency | `_evidence_binding` now also requires normalized value, unit, patient scope, verifier and decision time to agree between extracted and verified projections, and rejects an observation whose `source_document_id` contradicts the document of the fact it cites; `_references` binds the F1 and F2 historical VI-002 identities, checks the sealed evaluation's gate identity directly against the F2 gate identity, and treats an **absent** F1 row-id projection as absent rather than as a contradiction | `test_r206_extracted_and_verified_projections_must_agree`, `test_r206_absent_optional_projections_stay_absent`, `test_r206_contradictory_provenance_document_identities_are_rejected`, `test_r206_historical_excluded_vi002_identities_are_bound`, `test_r206_sealed_gate_identity_is_reconciled_honestly`, `test_r206_inconsistent_selected_evidence_cannot_be_presented_as_bound` |
| **R2-07** genuine producer compatibility | the integration test now loads the **stored F0 manifest rows** (`run_selected_document`, `run_selected_observation`) instead of substituting current source rows, resolves comparison baselines from stored evidence, projects the actual comparisons with the F2 label, projects the actual history exclusions, assembles the complete state, round-trips it through JSON, fully revalidates it, assembles the exact replay state and asserts unchanged sealed identity with zero per-call writes, and asserts the projected collections equal the producer outputs | `test_r01_genuine_stored_run_projects_every_accepted_producer` (single test, ten explicit stages) |

### 11.2 What the strengthened integration test now proves — and what it does not

Executed against the **real accepted services** (`seed_demo_data` → F0 → F1 → F2 → RB3 write → RB3 replay):

- the F0 manifest snapshot is loaded from its own tables and agrees with the F2 selection;
- the producer emits **one** comparison, whose baseline is the stored `ok_with_warning` row, with `delta = -29.0`, and the state reproduces it exactly;
- the producer emits **one** history exclusion (`validation_rejected`), and the state reproduces it exactly;
- the rejected row is excluded **by the producer**, not by the state;
- the state round-trips through JSON and survives `revalidate()` unchanged, and so does the replay state;
- the replay keeps the same `evaluation_id`, `audit_event_id` and `input_fingerprint_sha256` with zero per-call writes;
- the eligible `ok_with_warning` baseline is admissible **and** keeps `trust_level=self_reported_validated`.

**Not represented, and not claimed:** RB3 review items and evidence links are counted by the sealed receipt but are not projected as state collections in S0; the test asserts the receipt's totals are non-zero and that no such attribute exists, rather than implying completeness.

### 11.3 Structural checks are not authoritative selection

`_evidence_binding` can prove that a baseline is *a* history row of the right measure inside the labelled window. It cannot prove the row is the *latest prior* among all history, because the state carries a bounded projection. That selection belongs to the authoritative service. This distinction is asserted by `test_r203_structural_binding_does_not_claim_latest_prior_correctness`, and it is why no "latest prior" language appears in the validator.

### 11.4 Executed verification (Linux CPython 3.11.2 — disclosed deviation from CI 3.12; no Windows execution)

Focused S0 **169 passed / 0 failed**; P5 **228 passed**; P2 **282 passed**; P3 **443 passed** (D-09 guard green after the authorized append); P4 green; **full backend 1466 passed / 0 failed in 237 s**; Ruff lint and format PASS (149 files); Alembic smoke PASS at head `0008_p4_rb3_review_persistence` (upgrade → downgrade → upgrade); OpenAPI PASS (17 paths / 18 operations / 43 schemas); repository scan PASS (303 tracked files, 7 secret patterns, 4 claim patterns). **Collection measured: 1466 / 443 / 228** (+19 P5-S0 tests versus Round 2; P3 and P2 unchanged; nothing deleted).

---

## 12. Final narrow contract correction (2026-11-24) — append-only clarification

This section **corrects** the Round-3 description of the gate trace in §11.1/§11.2 and records the two narrow corrections that follow the Round-3 independent review. §11's executed evidence, its genuine producer integration results and its explicitly limited projection scope **remain valid and unchanged**; only the description of `GateDetail` was stale and is superseded here.

### 12.1 Correction: `GateDetail` is the normative contract shape (supersedes §11.1 R2-04)

§11.1 described `GateDetail` as carrying `issues: list[TraceGateIssue]`. That was **not** the normative shape. The authoritative definition is `GateEventDetail` in `docs/contracts/openapi.phase0.yaml` (`additionalProperties: false`) and `GateDetail` in `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, both of which specify exactly four fields:

| Field | Contract | Implementation now |
|---|---|---|
| `kind` | `const: gate` | `Literal["gate"] = "gate"` |
| `decision` | `enum: [proceed, halt]` | `TraceGateDecision` (two-valued) |
| `blocking_fact_count` | `integer 0..40` | `Field(ge=0, le=MAX_BLOCKING_FACTS)` with `MAX_BLOCKING_FACTS = 40` |
| `issue_types` | `array maxItems 6`, items `enum: [VI-001 … VI-006]` | `list[IssueType] = Field(max_length=6)` — the **closed** enum, unique and canonically ordered |

Consequences, all intentional:

- **`issue_types` replaced `issues`.** The non-normative `TraceGateIssue` payload was **removed** from the module. Full blocker semantic identities (`issue_type`, `reason_code`, `document_id`, `fact_ids`) and the canonical rendered `message` live only in `GateEvaluationRef`, which is the gate/evidence reference and is not a trace event.
- **No arbitrary reason-code text is serialized in the trace.** `GateIssueRef.reason_code` remains a bounded machine token that mirrors the F1 producer; it is **not** presented as a closed vocabulary anywhere, and it no longer reaches the trace at all.
- **A regex-conforming token is not a vocabulary.** `issue_types` is an enum list, so a string that merely matches a token pattern is rejected. The recursive trace test in §12.3 asserts membership in the *actual* closed vocabularies rather than a token regex.
- **`GateDetail.from_gate_evaluation()`** derives `issue_types` as the canonical (unique, ordered) set of the evaluation's blocker types, so a forged or reordered list cannot be substituted, and raises for `unavailable` instead of fabricating `proceed`/`halt`.
- **Document-only HALT with zero blocking facts is preserved and asserted**: `issue_types` is non-empty while `blocking_fact_count` may be `0`, because a document-level blocker references no distinct fact.
- **Historical-event association and `unavailable` routing stay assigned to S2.** Only the *latest* gate event must mirror the current evaluation; binding an earlier event to the evaluation that produced it, and routing an `unavailable` evaluation, are recorded S2 obligations and are not implemented here. No graph execution exists in S0.
- No OpenAPI, database schema or F1 change was made.

### 12.2 Correction: temporal structural eligibility

`monitoring.admissibility_reason` rejects a measurement beyond `as_of_utc + MAX_FUTURE_SKEW_MINUTES` (`"future_timestamp"`). The Round-3 selected-current validator checked the validation label but not this temporal condition. It now mirrors the accepted boundary for **selected-current** and **comparison current/baseline** rows:

- `MAX_FUTURE_SKEW_MINUTES = 5` is pinned in the state module (which imports no service) and drift-checked against `app.core.clock.MAX_FUTURE_SKEW_MINUTES` by `test_m20_vocabulary_single_sources_of_truth`. It is the accepted boundary, **not a new policy parameter**, and it grants no runtime authorization.
- Only the upper bound is enforced, exactly as the service does: a past measurement stays eligible however old it is, because window membership is a separate, labelled check (`R2-03`).
- The baseline rule is **defence in depth**: a baseline must precede its current, so a current inside the boundary already forces the baseline inside it. The predicate is nevertheless applied to the baseline row on every pass, and the test says so rather than pretending to exercise an unreachable path.
- **Structural eligibility is not authoritative selection.** Nothing here selects a baseline, proves it is the latest prior, or authorizes a runtime decision (`test_r202_structural_eligibility_grants_no_runtime_authority`).

### 12.3 Closure evidence for the final correction

| Requirement | Code | Test |
|---|---|---|
| Normative four-field shape | `GateDetail` fields; `TraceGateIssue` removed | `test_r204_gate_detail_is_the_normative_contract_shape` (asserts the field set, the OpenAPI `GateEventDetail` property names, `additionalProperties: false`, the `VI-00x` enum and the markdown contract block) |
| Canonical unique `issue_types` from the evaluation | `GateDetail.from_gate_evaluation()` | `test_r204_projection_keeps_the_closed_vocabulary_and_no_blocker_text` |
| No blocker text in the trace | identity/message only on `GateEvaluationRef` | same test — asserts `semantic_key()` and `message` remain on the reference |
| Closed vocabulary, not a token regex | `list[IssueType]` | `test_r204_every_nested_trace_payload_is_closed_vocabulary` (recursive walk over every detail and nesting event, with a negative control) |
| Reject unexpected nested text/token fields | `extra="forbid"` + enum list | `test_r204_unexpected_nested_text_and_token_fields_are_rejected` (8 payloads incl. `issues`, nested objects, `message`, `reason_code`, `VI-999`, duplicates, non-canonical order) |
| Document-only HALT with zero facts | `_consistent` no longer couples count to issue count | `test_r204_projection_keeps_the_closed_vocabulary_and_no_blocker_text` |
| Never fabricate `proceed`/`halt` | `from_gate_evaluation()` raises | same test |
| Latest-event-only mirroring (S2 association recorded) | `_trace_gate_consistency` | `test_r204_only_the_latest_gate_event_mirrors_the_current_evaluation` |
| Temporal boundary mirrored | `_beyond_future_skew` + `_selected_current_roles` / `_evidence_binding` | `test_r202_temporal_eligibility_mirrors_the_accepted_future_skew_boundary`, `test_r202_structural_eligibility_grants_no_runtime_authority` |

### 12.4 Executed verification for this correction (Linux CPython 3.11.2 — disclosed deviation from CI 3.12; no Windows execution)

Focused S0 **173 passed / 0 failed**; P5 **232 passed**; P2 **282 passed**; P3 **443 passed** (D-09 guard green after the authorized append); P4 green; **full backend 1470 passed / 0 failed**; Ruff lint and format PASS (149 files); Alembic smoke PASS at head `0008_p4_rb3_review_persistence`; OpenAPI PASS (17 paths / 18 operations / 43 schemas); repository scan PASS (303 tracked files, 7 secret patterns, 4 claim patterns). **Collection measured: 1470 / 443 / 232.**

### 12.5 Projection scope, restated unchanged

The genuine Round-3 integration evidence stands: the real F0 → F1 → F2 → RB3 (write and replay) producers are driven, their receipts are projected, and the complete state round-trips and revalidates. **RB3 review items and evidence links remain counted by the sealed receipt but are not projected as state collections**, and the test asserts that rather than implying completeness.
