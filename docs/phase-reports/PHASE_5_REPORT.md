# Phase 5 — Agent Workflow (LangGraph)

**Status:** IN_REVIEW — P5-S0 contract reconciliation and typed shared state only; **NOT ACCEPTED**  
**Owner kickoff / tracking:** [Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) — **OPEN**  
**Start date:** 2026-11-23  
**Baseline:** `main` at `121e1dbe8580d3d3da19c4c66d2391096d59bc52` (owner-merged PR #46; merged-main CI [#45268774759](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45268774759) SUCCESS)  
**Safety:** ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

## 1. Phase contract and planned stages

This is **P5 only**, and inside P5 only **S0** is authorized so far. Primary sources: `MASTER_PLAN.md` §5 P5, `MVP_SPEC.md` REQ-AGENT-*, `STATE_AND_GRAPH_CONTRACT.md`, `TOOL_CONTRACTS.md` §3.4–§3.7, `LLM_ADAPTER.md`, `ADR-0006`. P4 is `CONDITIONALLY_ACCEPTED_SYNTHETIC`; that acceptance does **not** authorize P5 execution, runtime policy activation or any merge.

- **P5-S0 (this PR):** contract reconciliation (§4 A–F) plus executable typed shared-state models with schema tests. Pure data. No graph, no checkpoint, no LLM, no API, no task, no notification.
- **P5-S1 (later):** tool adapters over the S0 types. No new free-text fields, no trust promotion, no widening of the state.
- **P5-S2 (later):** orchestrator + N2 verification gate + checkpoint *wiring*. App DB authoritative; checkpoint is replay material only.
- **P5-S3 (later):** LLM adapter, fallback, validation and grounding.
- **P5-S4 (later):** N6 interrupt/resume + restart reconciliation. Corrected source identity ⇒ **new run**, never an in-place resume over a sealed evaluation.
- **P5-S5 (later):** gold summaries + benchmark.

Each later slice requires its own branch, its own exact path allowlist, exact-head CI, the owner's Windows gate and the owner's merge. **P5-S1 is NOT started.**

## 2. This PR — exact scope

| File | Change |
|---|---|
| `backend/app/agents/__init__.py` | **New.** Package docstring; `__all__ = ["state"]`. No imports beyond `state`. |
| `backend/app/agents/state.py` | **New.** Pydantic v2 typed shared state: strict base, primitive aliases, 26 closed enums, 32 models, pure helpers, cross-field invariants. No I/O, no side effects, no service/graph/LLM/API import. |
| `backend/tests/p5/test_p5_state.py` | **New.** 124 collected tests across matrix M01–M20. |
| `docs/phase-reports/P5_S0_TYPED_STATE_IMPLEMENTATION_REVIEW_20261123.md` | **New.** Full §4 A–F reconciliation matrix, invariants, verification log, 14 owner decisions, S1/S2/S4/S5 requirements, safety-boundary review. |
| `docs/phase-reports/PHASE_5_REPORT.md` | **New.** This staged scope and honest test/remaining-work record. |
| `docs/roadmap/PHASE_PROGRESS.md` | **Existing, append-only.** One new section; zero deletions. |

**No other path changes.** No dependency change (no `langgraph` install), no migration, no F0/F1/F2/P4 service or schema change, no route, no UI, no CI change, no P3 handoff edit.

## 3. Verification — label evidence correctly

Local interpreter: **CPython 3.11.2** (disclosed deviation from the CI baseline of 3.12; no retry attempted). Libraries: pydantic 2.14.3, pytest 9.2.0, sqlalchemy 2.1.8, alembic 1.20.1, PyYAML 6.0.3, ruff 0.17.5.

- **Executed locally:** focused P5-S0 **124 passed / 0 failed / 0 skipped** (0.77 s). P5 + safety + OpenAPI **206 passed**. P5 + P4 + API regression **604 passed**. Ruff lint **All checks passed**; Ruff format **149 files already formatted**. Alembic smoke **PASS** (upgrade → downgrade base → upgrade; head `0008_p4_rb3_review_persistence`). OpenAPI **PASS (17 paths / 18 operations, 43 schemas)**.
- **Executed locally, with expected failures:** full backend **2 failed, 1418 passed** in 268.65 s. Both failures are *guards colliding with the authorized scope*, and **neither was weakened**:
  1. `backend/tests/p2/test_p2_scope_guards.py::test_no_later_phase_module_exists` — the P2 guard asserts `backend/app/agents/` must not exist, while P5-S0 was authorized to create exactly that package. **New conflict, blocking owner decision D-14.**
  2. `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` — the collection guard; the collection moved **1294 → 1420** with P3 unchanged at **443**. The handoff note is not an authorized path. **Owner decision D-09.**
- **Executed locally:** collection measurement. Current **1420** total / **443** P3 / **183** P5. Base, re-measured in a detached worktree at `121e1dbe…`: **1294** / **443** / **59**. Delta = **+126** = 124 new P5-S0 tests + 2 new parametrized `test_application_modules_are_typed` cases (which pass).
- **Exact-head GitHub Actions at `e70d2ea9b5cc6446e06f336b40e83bdc3df73052`** (push [#45277330559](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277330559), pull_request [#45277408623](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277408623)): both COMPLETED / **FAILURE**, confined to one step. **Frontend (Node 22) SUCCESS** in both. Backend (Python 3.12): Ruff lint **SUCCESS**, Ruff format check **SUCCESS**, **Backend tests FAILURE**; Alembic smoke, OpenAPI and scanner **SKIPPED — not reached**. The failing-test identity was **not read from the CI log** (the logs endpoint redirects to a blob host outside the sandbox egress allowlist); it is **inferred** from the byte-identical local run at the same clean tree, where exactly those two guard tests fail and nothing else does. **This is not a green run and is not presented as one.** A green exact-head run requires an owner decision on D-14 and D-09.
- **Not executed locally:** Windows PowerShell / `test_all.ps1` (owner laptop only — **no Windows claim is made**); any LangGraph, Ollama, LLM, GPU or browser check (not applicable to this slice); frontend build (read from CI only).
- **Not run by design:** no graph, checkpoint, interrupt, resume, tool adapter or model execution exists in this slice, so none was exercised.

## 4. Safety, correctness and residual risks

- **No runtime capability.** `state.py` is imported by tests only. No service, route, migration, task, notification or model runtime imports it; nothing outside the test suite constructs `SharedGraphState`.
- **Serialized state authorizes nothing.** Honesty literals are `Literal` types: `policy_status="unapproved"`, `runtime_policy_activated=False`, `runtime_evaluable=False`, `demo_only=True`, `not_for_clinical_use=True`. No JSON or Python input can set them otherwise (asserted by M17).
- **Strictness is real but not a security boundary.** `extra="forbid"`, `strict=True`, `frozen=True` reject unknown fields and unsafe coercions in every input path *except* `model_copy(update=...)`, which bypasses validation by Pydantic design. This is documented and covered by two tests that re-validate and catch the forgery. **Frozen/private does not establish authority** — see D-08.
- **Known residual risks:** (i) D-14 blocks a green suite; (ii) D-09 blocks the collection guard; (iii) D-01/D-02/D-03/D-04/D-05/D-06 are contract ambiguities resolved provisionally and reversible; (iv) D-07 means a JSON *number* is accepted for an exact decimal field; (v) no runtime authorization check exists yet — the schema only *represents* one.

## 5. Owner review checklist

- [ ] Decide **D-14** (P2 scope guard vs the authorized `backend/app/agents/` package) — blocking.
- [ ] Decide **D-09** (append-only collection note `1420 / 443` to `PHASE_3_WINDOWS_ACCEPTANCE.md`) — separate authorization required.
- [ ] Confirm or revise **D-01 … D-13** in the S0 review §6.
- [ ] Independent engineering review of `state.py` and the test matrix.
- [ ] Exact-head CI green (except the two documented guard collisions, if D-14/D-09 are not yet decided).
- [ ] Owner Windows verification of this slice.
- [ ] Only then: owner merge decision. **No agent merge, no auto-merge, no direct `main` edit, no self-approval.**

## 6. Open questions

See S0 review §6 (D-01 … D-14) and §7 (requirements recorded for S1/S2/S4/S5). Issue #14 stays **OPEN**.
