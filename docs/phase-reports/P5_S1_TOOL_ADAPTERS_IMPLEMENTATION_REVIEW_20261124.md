# P5-S1 — Bounded Read-Only Tool Adapters: Implementation Review

**Date:** 2026-11-24  
**Phase status:** P5 **IN_REVIEW / NOT ACCEPTED**. This document reviews one bounded slice (P5-S1) and is **not** a phase PASS, not an acceptance, and not an authorization to start P5-S2.  
**Scope authorized:** P5-S1 only — three narrowed read-only adapters plus the D-15 scope-guard decision.  
**Safety:** ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

---

## 0. Branch, base and identity

| Item | Value |
|---|---|
| Branch | `arena/a61b8893-p5-s1-tool-adapters` |
| Base commit (exact `main`) | `4e92abbde1ad1c3a8e77e0a741617c19c8133413` |
| Base source | `origin/main` after PR #47 owner merge; `gh pr view 47` → **MERGED**, mergeCommit `4e92abb` |
| Base verification (executed before any edit) | new clean worktree; `git diff --exit-code` against `4e92abb` → exit 0; `4e92abb` is an ancestor of the branch; **0 commits ahead** |
| PR | ONE **draft** PR from this branch |
| Tracking issue | [#14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) — **OPEN**, must stay open |
| Workspace safety | the earlier Arena sandbox branch (`arena/a61b8893-ai-doctor-followup-agent` @ `8f341b0`, 11 status entries) was **not touched** and no PR is opened from it |

P4 status at the time of writing: **`CONDITIONALLY_ACCEPTED_SYNTHETIC`**. GOLD-EX-11 **FAIL / NOT PROVEN**. RB3-75..77 **deferred / NOT EXECUTED**. DR-006 persistence **prohibited**. Runtime demo policy **not activated / unapproved**.

---

## 1. Authorization and non-goals

**Owner authorization (in-session, 2026-11-24):** implement exactly **three** bounded read-only adapters over the frozen S0 state, plus the D-15 scope-guard decision. The authorization explicitly records that this covers **narrowed S1 internal projection semantics**, not the broader `TOOL_CONTRACTS.md` signatures.

| Adapter | Authorized semantics |
|---|---|
| `read_verified_facts` | F2 verified facts only. Never accepts caller-authored evidence; never promotes a pending or unverified fact |
| `read_observations` | F2-selected observations plus the **actual** F2 exclusions, labelled `f2_selected_only`. Scoped read-only stored-row lookup reconstructs the S0 types. No full-history claim; no exclusion is silently dropped |
| `compare_observations` | Projects F2 comparisons exactly. No caller baseline or lookback; no reselection, delta calculation or unit conversion; preserves trust labels and incomparable reasons |

**Deferred — 7 tools, no stubs, no placeholders:** `validate_structured_fields`, `get_document_pages`, `extract_document`, `evaluate_demo_review_rules`, `draft_grounded_summary` (S3), `create_in_app_task` (S4), `list_due_tasks`.

**Non-goals, honoured strictly:**

- No graph, node wiring, checkpointer, interrupt or resume execution.
- No LLM, Ollama, HTTP client, route, task creation, notification, finalization or UI.
- No change to F0 / F1 / F2 / P3 / P4 services, schemas, migrations, routes or tests.
- No DB write and no audit row: S1 emits **bounded structured audit metadata** only. S2 owns durable persistence.
- No dependency, CI, OpenAPI, migration, policy or contract change.
- `backend/app/agents/__init__.py` untouched (not required by this slice).
- `backend/app/agents/state.py` untouched (frozen).

---

## 2. What was implemented

### 2.1 `backend/app/agents/tools.py` (new, ASCII-only)

**Public surface (`__all__`, 14 names):** `MAX_AUDIT_EVIDENCE_IDS`, `ObservationEvidence`, `ToolAuditMetadata`, `ToolContext`, `ToolError`, `ToolErrorCode`, `ToolErrorReason`, `ToolPermissionError`, `ToolResult`, `assert_tool_allowed`, `compare_observations`, `read_observations`, `read_verified_facts`.

| Element | Decision |
|---|---|
| `ToolContext` | Frozen, slotted dataclass with exactly six trusted fields: `db`, `principal`, `run_id`, `node`, `validation_clock`, `upload_root`. There is **no** `patient_id`, document id, baseline, lookback, trust label or fact-list field, so a caller cannot supply one |
| `assert_tool_allowed(node, tool)` | Pure structural pre-call guard over the frozen S0 `NODE_TOOLS` map. Raises `ToolPermissionError`; returns no decision object |
| `ToolResult[T]` | Discriminated envelope. Validators make `ok=True ⇒ data present, error None` and `ok=False ⇒ error present, data None` exclusive, and bind `audit.outcome` to the result |
| `ToolError` | `code` + `reason` + bounded `message` (≤300 chars) + `retryable` (always `False`). Carries no document body and no secret |
| `ToolErrorCode` | Closed local vocabulary: `E_TOOL_NOT_ALLOWED`, `E_NOT_FOUND`, `E_SCOPE_VIOLATION`, `E_UNVERIFIED_FACT`, `E_VALIDATION`. A local literal set is used because `app.core.errors.ErrorCode` has no `E_TOOL_NOT_ALLOWED` member and the enum is not an authorized path |
| `ToolErrorReason` | 13 closed machine reasons (`tool_not_allowed_for_node`, `run_not_found`, `fact_not_found`, `observation_not_found`, `document_not_found`, `access_denied`, `patient_scope_mismatch`, `document_scope_mismatch`, `unverified_fact`, `producer_evidence_inconsistent`, `session_not_clean`, `producer_not_evaluable`, `invalid_context`) |
| `ToolAuditMetadata` | `tool`, `node`, `run_id`, `outcome`, `error_code`, `evidence_ids` (bounded by `MAX_SELECTED_CURRENT + MAX_HISTORY_OBSERVATIONS`). No payload, prompt or document text |
| `ObservationEvidence` | `scope="f2_selected_only"` literal, `observations` (≤20), `exclusions` (≤40), optional `no_current_reason` |

**Call order in every adapter:** allowlist → context validation → session cleanliness → accepted F2 bridge → per-row reconciliation → typed projection.

**Bridge contract honoured.** The accepted `build_run_evaluable_review_evidence` requires a fresh clean `Session`, opens its own `BEGIN IMMEDIATE` and always rolls back. The adapter therefore checks `db.in_transaction() / db.new / db.dirty / db.deleted` **before** the call and returns `session_not_clean` instead of calling it. The adapter performs its own read-only `Session.get` reconciliation *after* the bridge has returned and rolled back, so it never hands the bridge a dirty session.

**Reconciliation rules (fail closed, typed error, no partial payload):**

| Check | Error |
|---|---|
| fact not stored | `E_NOT_FOUND / fact_not_found` |
| fact not `verified` | `E_UNVERIFIED_FACT / unverified_fact` |
| stored fact patient ≠ producer patient | `E_SCOPE_VIOLATION / patient_scope_mismatch` |
| stored document ≠ F2 document, or field drift | `E_VALIDATION / producer_evidence_inconsistent` |
| document belongs to another patient | `E_SCOPE_VIOLATION / document_scope_mismatch` |
| document outside the run selection | `E_SCOPE_VIOLATION / document_scope_mismatch` |
| observation value/timestamp/unit/source/trust drift | `E_VALIDATION / producer_evidence_inconsistent` |
| comparison current outside the F2 selection | `E_VALIDATION / producer_evidence_inconsistent` |
| comparison baseline not stored / other patient | `E_NOT_FOUND / observation_not_found`, `E_SCOPE_VIOLATION / patient_scope_mismatch` |

`compare_observations` passes the F2 `delta` through unchanged and re-derives `current_value` / `baseline_value` from the bound stored rows; the S0 `ComparisonResult` validator then re-checks `delta == current_value - baseline_value` exactly. Nothing is recalculated and no unit is converted.

### 2.2 `backend/tests/p5/test_p5_s1_tools.py` (new, ASCII-only, 35 collected)

| Area | Tests |
|---|---|
| Allowlist matrix | exact equality with frozen `NODE_TOOLS`; all unauthorized node×tool pairs fail closed **before** any session access (poison session); guard is structural, returns no decision |
| Error vocabulary | closed 5-code / 13-reason set |
| Genuine F0→F1→F2 integration | run created by `create_run_foundation`, gate persisted by `evaluate_run_verification_gate`, evidence by the accepted bridge; 4 verified facts projected with patient id, document id and audit identities |
| Empty / unverified | empty producer envelope → `[]`; a pending fact is refused as `unverified_fact`, never promoted |
| Selected-only | `scope == "f2_selected_only"`; one selected row; the rejected history row appears as `validation_rejected` |
| No silent exclusion drop | adapter exclusions equal the bridge's own `history_exclusions`, one for one |
| Self-reported trust | `self_reported_validated` preserved with `verified_by`/`verified_at` absent and `patient_checkin` source |
| No current | `no_current_selected` reported, nothing fabricated |
| Exact comparison | `delta == -29 == exact_delta(121, 150)`; field-for-field equality with the bridge; `no_baseline` incomparable case preserved |
| Caller authority | adapters take only `ctx`; `ToolContext` rejects `patient_id`, `baseline_observation_id`, `lookback_days` |
| Identity | forged run id → `run_not_found`; another doctor → `access_denied`; cross-patient fact/observation → `patient_scope_mismatch` |
| Producer evidence | missing fact, drift, unselected document, comparison current outside selection |
| Stale gate | a pending fact in the selected document makes the gate ineligible → `producer_not_evaluable`, no evidence returned |
| Session | dirty session → `session_not_clean` before the bridge; empty run id / upload root → `invalid_context` |
| Envelope / audit | error invariants; audit is bounded and carries no payload; success audit carries exactly the evidence identities |
| No side effects | row counts identical before/after all three adapters; `new`/`dirty`/`deleted` empty; no socket; no runtime/egress import; no deferred tool implemented or stubbed |

### 2.3 `backend/tests/p2/test_p2_scope_guards.py` — D-15 only

```python
AUTHORIZED_AGENT_MODULE_PATHS = ("__init__.py", "state.py", "tools.py")
```

- The constant becomes **exactly** the three-tuple; asserted by a new test, so a future fourth path cannot slip in unnoticed.
- The existing rejection test now proves that `orchestrator.py`, `tool_adapter.py`, `tool_adapters.py`, `agent_tools.py`, `tools_v2.py`, `tools_extra.py`, `checkpoint.py`, `checkpoints.py`, `llm.py`, `runtime.py`, a nested `graph/nodes.py` and a nested `tools/adapters.py` are **all** still reported as violations. A near-miss filename is never treated as the authorized module, and the nested `tools/` package is not the authorized flat `tools.py`.
- No other P2 guard was touched: `FORBIDDEN_IMPORTS`, `OCR_IMPORTS`, `OCR_ALLOWED_PREFIX`, `FORBIDDEN_TERMS`, `test_no_later_phase_module_exists` and `test_application_modules_are_typed` are unchanged in behaviour.

---

## 3. D-15 — scope-guard decision (recorded, new, not retroactive)

**Decision D-15 (owner, in-session, 2026-11-24):** `AUTHORIZED_AGENT_MODULE_PATHS` becomes exactly `("__init__.py", "state.py", "tools.py")`.

- This is a **new S1 decision**. It does not widen, rewrite or re-label D-14, which authorized only the two S0 modules.
- It remains an **exact-path allowlist**. There is no directory-wide exemption: every other file under `backend/app/agents`, including any nested package, stays forbidden, and `backend/app/llm` stays forbidden.
- **Authorization channel:** stated by the owner in this Arena session on 2026-11-24, narrowing an earlier proposal to the three adapters and the exact tuple. No other channel (issue, PR comment, document) was used or implied.
- The decision and its channel are recorded here and in `docs/roadmap/PHASE_PROGRESS.md`.

---

## 4. Security and authority boundary review

**What this change can make the system do at runtime: nothing.** `tools.py` is imported by its own test module only. No service, route, migration, task, notification, graph or model runtime imports it, and nothing constructs a `ToolContext` outside the tests.

**Authority that is enforced structurally:**

- The server supplies `principal`, `run_id`, `node` and both clocks. A patient id, document id, baseline, lookback, trust label or fact list **cannot** be passed: the context type has no such field and each adapter accepts only `ctx`.
- `assert_tool_allowed` runs before any database access in every adapter; an unauthorized combination never reaches the bridge or the session.
- The accepted bridge still authenticates the doctor session, the patient assignment and the current F1 gate. The adapter adds no authority and removes none.
- Every projected row is re-checked against its stored row for patient scope, document scope, selection membership and field equality. A mismatch returns a typed error and **no partial payload**.

**Authority that is *not* claimed:**

- The allowlist check is a **shape check, not clinical authorization** and not a runtime permission system. Nothing here decides whether a run may proceed.
- No trust promotion: a pending fact is refused, and `trust_level` / `trust_basis` are copied from the producer and the stored row, never upgraded.
- No medical decision, no review-item persistence, no task execution, no notification, no self-approval.
- No durable audit trail: `ToolAuditMetadata` is a bounded in-memory payload for S2 to persist. S1 writes no audit row and does not claim one exists.
- No active runtime tool system: these are projection functions over accepted producer output, not an executing agent loop.

**Bounded messages:** every error message is whitespace-collapsed and truncated to 300 characters and is drawn from a fixed set of producer-safe strings; no document body, raw text, normalized value, credential or session token reaches an error or an audit payload.

---

## 5. Verification executed in this session

All commands were run from the repository root. The local interpreter is **CPython 3.11.2**, a **disclosed deviation** from the CI baseline of 3.12. No Windows execution was performed and none is claimed.

| Check | Command | Result |
|---|---|---|
| Focused S1 | `pytest backend/tests/p5/test_p5_s1_tools.py` | **35 passed / 0 failed** |
| P5 suite | `pytest backend/tests/p5` | **267 collected** (173 S0 + 35 S1 + 59 existing P5 suites) |
| P2 suite | `pytest backend/tests/p2` | **284 collected** (282 at base + 2) |
| P3 suite | `pytest backend/tests/p3` | **443 collected** (unchanged) |
| Whole backend | `pytest backend/tests` | **1 failed, 1506 passed** in ~234 s — see §5.1 |
| Ruff lint | `ruff check backend scripts` | **All checks passed** (exit 0) |
| Ruff format | `ruff format --check backend scripts` | **151 files already formatted** (exit 0) |
| Alembic smoke | `upgrade head` → `downgrade base` → `upgrade head` + `check_alembic_smoke.py` | **PASS**, head `0008_p4_rb3_review_persistence` |
| OpenAPI contract | `scripts/python/check_openapi.py` | **PASS (17 paths / 18 operations, 43 schemas)** |
| Repository scanner | `scripts/python/scan_repository.py` | **PASS** (305 tracked files; 7 secret patterns, 4 claim patterns) |

### 5.1 The one failure — the collection guard, held for D-09

```
FAILED backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes
AssertionError: handoff should quote the whole-backend collection 1507
```

Base collection (verified in a detached worktree at `4e92abb`): **1470** whole backend / **443** P3 / **232** P5 / **282** P2.

New collection at this branch: **1507** whole backend / **443** P3 / **267** P5 / **284** P2.

The delta is **+37** = 35 new S1 tests + 1 new D-15 scope-guard test + 1 new parametrized `test_application_modules_are_typed` case for `agents/tools.py`.

- `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` was **not modified**. It is not an authorized path for this slice, and the earlier D-09 authorization covered an earlier pairing, not this one.
- The guard was **not weakened**, skipped or deleted.
- **Owner decision D-09 (fresh, required):** authorize the append-only collection note `**1507 collected**, of which **443** are the P3 suite` (and the P5/P2 movement) as a separate documentation-only step. Until then the suite is honestly red at exactly that one guard.

---

## 6. Owner decisions required

| ID | Question | What S1 does today | Options |
|---|---|---|---|
| **D-09** (fresh) | Collection moved `1470 → 1507`; the P3 handoff still quotes 1470 | Not edited; guard fails as designed | (a) authorize the append-only note `**1507 collected**, of which **443** are the P3 suite`; (b) hold the note and accept the red guard; (c) re-scope the guard |
| **D-15** (recorded) | Which `agents` modules are authorized | Exactly `("__init__.py", "state.py", "tools.py")` | (a) confirm as recorded; (b) narrow; (c) widen |
| **D-16** (new, minor) | Should the 13 `ToolErrorReason` values be merged into a shared contract vocabulary later? | Local closed literal set in `tools.py`; `ErrorCode` untouched | (a) keep local until S2; (b) promote to `TOOL_CONTRACTS.md`; (c) fold into `app.core.errors` |

---

## 7. What this slice does not claim

- It does not claim an executing agent, a graph, a checkpoint, a runtime tool system or a durable audit trail.
- It does not claim clinical authorization: structural eligibility is not a decision to proceed.
- It does not claim Windows verification. No `test_all.ps1` run was performed.
- It does not claim a green whole-backend suite: exactly one guard is red pending D-09.
- It does not claim that the three adapters cover `TOOL_CONTRACTS.md` §3.4–3.5; the authorized semantics are deliberately narrower.
- It does not claim that the remaining seven tools are designed, stubbed or scheduled beyond their recorded deferral.

---

## 8. Requirements recorded for S2 (not implemented here)

- S2 must persist `ToolAuditMetadata`; it must not re-derive audit data from the payload.
- S2 must supply `ToolContext` from trusted server state and must never build it from agent arguments.
- S2 must treat `assert_tool_allowed` as a shape check only and must add its own runtime authorization.
- S2 must not widen the adapters to accept baselines, lookbacks, patient ids or caller-authored evidence without a fresh owner authorization.
- S2 must preserve the fresh-clean-session contract around every bridge call.

---

## 9. D-09 fresh authorization obtained — collection note appended (2026-11-24)

- **Authorization (disclosed channel):** the repository owner selected the explicit option *Authorize the append-only edit* in this Arena working session on 2026-11-24, for exactly `**1507 collected**, of which **443** are the P3 suite`. The authorization was given in reply to a direct question in the session; **no** new signed GitHub comment exists for it. It was recorded in `docs/roadmap/PHASE_PROGRESS.md` before the handoff was edited.
- **Edit executed:** one append-only section at the end of `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` carrying the paired literal above. No other line of that file changed; every historical P3 result, every earlier collection checkpoint and the real `GOLD-EX-11 FAIL / NOT PROVEN` outcome remain verbatim.
- **Guard re-run after the edit:** `pytest backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` → **passed**. The guard itself was not modified.
- **Whole-backend re-run after the edit:** `pytest backend/tests` → **1507 passed / 0 failed** in 243 s. The suite is green at this head; the earlier "held for D-09" statements in §5.1 and in `PHASE_5_REPORT.md` §12 / `PHASE_PROGRESS.md` describe the state *before* this authorization and are superseded by this section.
- **Status unchanged:** P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; draft PR only; no merge, auto-merge, self-approval, main change or S2 work.

---

## 10. Exact-head GitHub Actions (2026-11-24)

Pushed head `08b457fb80bbf1c1150c3552444f52e4af49e7b7` — draft PR [#48](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/48), run [#45480318202](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45480318202): **COMPLETED / SUCCESS**.

| Job | Result |
|---|---|
| Frontend (Node 22) | **SUCCESS** |
| Backend (Python 3.12) — Ruff lint | **SUCCESS** |
| Backend (Python 3.12) — Ruff format check | **SUCCESS** |
| Backend (Python 3.12) — Backend tests | **SUCCESS** |
| Backend — Alembic smoke (upgrade, downgrade, upgrade) | **SUCCESS** |
| Backend — Generated OpenAPI contract check | **SUCCESS** |
| Backend — Repository secret and artefact scan | **SUCCESS** |

This is the first green exact-head run for the slice. It was read from the Actions API, not inferred. Windows `test_all.ps1` was **not** run by the agent; owner Windows acceptance remains outstanding.

**Status:** PR #48 **OPEN / DRAFT / NOT MERGED**; P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; no merge, auto-merge, self-approval, main change or P5-S2 work. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## 11. Final-head CI verification (2026-11-24)

After the documentation-only commits, the branch head is `85b8f47cfc67a9ee0cc8c3c181842b86b618d62f`. Both exact-head runs at that SHA — push [#45481000638](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45481000638) and pull_request [#45480990524](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45480990524) — are **COMPLETED / SUCCESS** (Frontend Node 22 and Backend Python 3.12, including Ruff lint/format, backend tests, Alembic smoke, OpenAPI and repository scan). This section is a documentation-only append: no application or test blob changes after `08b457f`, so the CI evidence above covers the reviewed code exactly. Windows `test_all.ps1` remains **not run** by the agent.

**Status:** PR #48 **OPEN / DRAFT / NOT MERGED**; P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; no merge, auto-merge, self-approval, main change or P5-S2 work. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

---

## 12. S1-R1 — post-bridge transaction lifecycle closed (2026-11-24)

**Finding (independent review).** The accepted F2 bridge rolls back its own `BEGIN IMMEDIATE` snapshot before returning, but the adapters then reconcile stored rows with `ctx.db.get(...)`, which autobegins a fresh read transaction under SQLAlchemy. The adapters returned without ending it, and the tests opened a new session per call, so neither safe sequential reuse nor a clean post-return state was proven.

**Correction (in `backend/app/agents/tools.py` only).**

- `_session_is_clean(db)` captures the bridge's own precondition once per call, after the allowlist check and before the bridge is called.
- `_end_adapter_transaction(ctx, started_clean=...)` ends the transaction **with `ROLLBACK`**, and only when the session was already clean on entry. `COMMIT` is never used as a cleanup mechanism, the session is never closed, and a caller-owned dirty session is left untouched.
- Every adapter now wraps its reconciliation in `try / except _Drift / except (ValidationError, ValueError) / finally`, so the rollback runs on success, on a typed error, on a validation failure and on an unexpected exception.
- `_evidence(...)` takes the pre-computed `started_clean` instead of re-reading session state, so there is exactly one definition of the precondition per call.

**Proof (new tests).**

| Test | Proves |
|---|---|
| `test_s1_sequential_same_context_calls_end_their_transactions` | the two permitted `monitor_compare` adapters run on **one** context, both succeed, and `in_transaction()` is `False` with empty `new`/`dirty`/`deleted` after each return |
| `test_s1_early_error_return_leaves_no_open_transaction` | a `run_not_found` early return still ends the transaction |
| `test_s1_denied_call_never_touches_the_session` | an unauthorized pair never opens a transaction |
| `test_s1_no_adapter_ever_commits` | `Session.commit` is patched to record calls; both adapters run and **zero** commits happen |
| strengthened `test_s1_dirty_session_is_refused_before_the_bridge` | the caller's pending row is still pending (`len(new) == 1`), the session is still in its own transaction and still active — nothing was rolled back or closed for it |
| strengthened `test_s1_adapters_never_write_to_the_database` | no open transaction after the call, in addition to unchanged row counts |

**Explicit non-claims.** Ending the read transaction does **not** make the bridge's snapshot and the adapter's stored-row reads one atomic snapshot, and no such claim is made. The F2 bridge's accepted `BEGIN IMMEDIATE` / rollback semantics are untouched. No caller-owned session is closed.

---

## 13. S1-R2 — complete stored-row reconciliation (2026-11-24)

**Finding (independent review).** `compare_observations` checked only the current row's patient scope, and took `current_value` from the F2 envelope while `baseline_value` came from a stored row. A drifted current row could therefore be combined with a baseline from a different read. `read_observations` also did not re-check whether a selected row was still eligible after the bridge's snapshot.

**Correction (in `backend/app/agents/tools.py` only).**

- `_reconcile_selected(ctx, evidence, row)` now reads the selected row and compares **value, measure type, unit, timestamp, source, trust label and fact lineage** against the F2 `ObservationV2`. Any drift raises a typed `producer_evidence_inconsistent`; the returned `ObservationView` is built from the **stored** row, so `current_value` and `baseline_value` always come from the same read.
- `_require_admissible(...)` re-applies the **accepted** `monitoring.admissibility_reason` predicate to the stored row with the run clock. A row that became `validation=rejected`, or that now exceeds the accepted future-skew boundary, fails closed. No new boundary or policy parameter is introduced.
- `_history_view(...)` builds the baseline's `HISTORY` view, resolving `source_document_id` only through the stored `ExtractedFact`, and the S0 `ObservationView` validators enforce trust/provenance consistency (a `doctor_verified` row requires a verifier; a document row requires its fact lineage).
- The baseline is additionally checked for patient scope, identical measure type and unit, strict temporal precedence (`baseline.measured_at < current.measured_at`) and admissibility.
- `_expected_trust_basis(...)` mirrors the accepted producer's derivation exactly (`mixed` when the two labels differ, else `doctor_verified` or `self_reported`) and the F2 label is cross-checked against it.
- The F2 `delta` remains the **output**: it is never recalculated or replaced. When both values are present the S0 `ComparisonResult` validator re-checks `delta == current_value - baseline_value` exactly, and the `f2-history-365d-v1` label and `no_baseline` semantics are preserved unchanged.

**Proof (new tests).**

| Test | Proves |
|---|---|
| `test_s1_compare_rejects_a_drifted_stored_current_row` (5 cases) | a stored current **value, unit, measure type, timestamp or source** that drifted after the bridge fails closed |
| `test_s1_compare_rejects_a_drifted_stored_trust_label` | a stored **trust label** that drifted fails closed |
| `test_s1_compare_rejects_a_baseline_that_became_rejected` | the baseline is re-checked with the accepted predicate |
| `test_s1_compare_rejects_a_baseline_measured_after_its_current` | strict temporal precedence is enforced |
| `test_s1_compare_rejects_a_cross_patient_baseline` | a forged baseline identity from another patient is refused with `patient_scope_mismatch` |
| `test_s1_compare_rejects_a_baseline_with_a_different_measure` | measure/unit comparability is enforced |
| `test_s1_compare_rejects_a_drifted_trust_basis_label` | the F2 trust label must follow from the reconciled rows |
| `test_s1_read_observations_rejects_a_selected_row_that_became_rejected` | a selected row that turned `rejected` is not returned as eligible |
| `test_s1_read_observations_rejects_a_selected_row_beyond_the_future_skew` | the accepted 5-minute future-skew boundary is re-checked |

Drift is produced by a **real** second session committing after the genuine bridge returns and rolls back, so the F2 envelope and the adapter's read genuinely disagree — the tests do not fabricate an envelope for these cases. `ok_with_warning` admissibility and self-reported trust labels are preserved: the warning baseline is still used as a baseline in the exact-delta test.

**Residual authority limit (documented, not fixed).** The bridge's snapshot and the adapter's stored-row reads are two independent reads. Detectable drift fails closed; an undetectable change that leaves every compared field identical would not be caught, and nothing here claims the two reads are one atomic snapshot.

---

## 14. Collection re-measurement after the corrections (2026-11-24)

| Suite | Before corrections | After corrections |
|---|---|---|
| Focused S1 | 35 | **52** (+17) |
| P5 | 267 | **284** |
| P2 | 284 | **284** (unchanged) |
| P3 | 443 | **443** (unchanged) |
| Whole backend | 1507 | **1524** |

`docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` was **not** edited at this point: the pairing moved, so a fresh D-09 authorization is required before the append-only note. The guard was not weakened.

---

## 15. D-09 fresh authorization obtained — collection note appended (2026-11-24)

- **Authorization (disclosed channel):** the repository owner selected the explicit option *Authorize the append-only edit* in this Arena working session on 2026-11-24, for exactly `**1524 collected**, of which **443** are the P3 suite`. Given in reply to a direct question in the session; **no** new signed GitHub comment exists for it. Recorded in `docs/roadmap/PHASE_PROGRESS.md` before the handoff was edited.
- **Edit executed:** one append-only section at the end of `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`. No other line of that file changed; every historical P3 result, every earlier collection checkpoint and the real `GOLD-EX-11 FAIL / NOT PROVEN` outcome remain verbatim.
- **Guard re-run after the edit:** `test_handoff_test_count_matches_the_suite_it_describes` → **passed**. The guard itself was not modified.
- **Whole backend after the edit:** **1524 passed / 0 failed**.
- **Status unchanged:** P5 **IN_REVIEW / NOT ACCEPTED**; PR #48 **OPEN / DRAFT / NOT MERGED**; issue #14 **OPEN**; no merge, auto-merge, self-approval, main change, S2 work or Windows acceptance claim.

---

## 16. Exact-head CI for the corrections (2026-11-24)

Correction head `8cb05d08788c6510211d11156584464c59f67a9a` — push [#45649051373](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45649051373) and pull_request [#45649044112](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45649044112): both **COMPLETED / SUCCESS** (Frontend Node 22; Backend Python 3.12 with Ruff lint, Ruff format, backend tests, Alembic smoke, OpenAPI and repository scan). Read from the Actions API. This section is a documentation-only append; no application or test blob changes after `8cb05d0`.

Windows `test_all.ps1` remains **not run** by the agent; no Windows acceptance is claimed. PR #48 **OPEN / DRAFT / NOT MERGED**; P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; no merge, auto-merge, self-approval, main change or P5-S2 work. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

---

## 17. S1-R3 — baseline window drift closed (2026-11-24)

**Finding (independent review).** The accepted F2 producer calls `compare_explicit_current_with_history` with `HISTORY_LOOKBACK_DAYS = 365`, and its baseline eligibility is inclusive at the lower boundary and exclusive at the upper one: `current - 365d <= baseline < current`. `compare_observations` re-checked only the upper bound ("earlier than its current"), so a second writer could move the stored baseline before the 365-day window after the genuine bridge returned; with value, unit and trust label unchanged, the original F2 delta would still be emitted although the stored baseline was no longer temporally eligible.

**Correction (in `backend/app/agents/tools.py` only).**

- The baseline block now validates the accepted window against the reconciled stored timestamps:
  `current_stamp - timedelta(days=HISTORY_LOOKBACK_DAYS) <= baseline_stamp < current_stamp`.
- `HISTORY_LOOKBACK_DAYS` is imported from the accepted F2 bridge module. **No new configurable period is introduced** and no new policy parameter appears.
- An out-of-window baseline raises the existing typed `producer_evidence_inconsistent` error and returns **no payload**.
- The F2 `delta`, `baseline_observation_id`, `trust_basis` and the `no_baseline` semantics are untouched: the window is only re-validated, never reselected.
- Transaction cleanup is unchanged: the `finally` rollback still runs on this rejection path.

**Proof (new tests).**

| Test | Proves |
|---|---|
| `test_s1_compare_rejects_a_baseline_outside_the_365_day_window` | the genuine F2 bridge runs, then a separate session commits a baseline timestamp of `2025-06-01` (earlier than the current, outside 365 days); the adapter returns `producer_evidence_inconsistent`, no data, `in_transaction() is False` and empty `new`/`dirty`/`deleted` |
| `test_s1_compare_accepts_the_exact_inclusive_365_day_boundary` | a baseline committed at exactly `current - 365 days` (`2025-11-01T09:00:00Z` vs current `2026-11-01T09:00:00Z`) is still accepted, with `baseline_observation_id`, `comparable`, `delta == -29`, `delta == exact_delta(121, 150)` and the `f2-history-365d-v1` label intact |
| existing `test_s1_compare_rejects_a_baseline_measured_after_its_current` | the exclusive upper bound is still rejected (now through the same window check) |

Both new tests use `_write_after_bridge`, i.e. the genuine bridge plus a real second committed session, not a fabricated envelope.

**Explicit non-claim.** This closes the *detectable* lower-bound drift. It still does not make the bridge snapshot and the adapter's read one atomic snapshot, and it does not re-derive the F2 delta — the delta remains the producer's output.

---

## 18. D-09 fresh authorization obtained for S1-R3 (2026-11-24)

- **Authorization (disclosed channel):** the repository owner selected the explicit option *Authorize the append-only edit* in this Arena working session on 2026-11-24, for exactly `**1526 collected**, of which **443** are the P3 suite`. Given in reply to a direct question in the session; **no** new signed GitHub comment exists for it. Recorded in `docs/roadmap/PHASE_PROGRESS.md` before the handoff was edited.
- **Edit executed:** one append-only section at the end of `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`. No other line of that file changed; every historical P3 result, every earlier collection checkpoint and the real `GOLD-EX-11 FAIL / NOT PROVEN` outcome remain verbatim.
- **Guard re-run after the edit:** `test_handoff_test_count_matches_the_suite_it_describes` → **passed**. The guard itself was not modified.
- **Status unchanged:** P5 **IN_REVIEW / NOT ACCEPTED**; PR #48 **OPEN / DRAFT / NOT MERGED**; issue #14 **OPEN**; no merge, auto-merge, self-approval, main change, S2 work or Windows acceptance claim.
