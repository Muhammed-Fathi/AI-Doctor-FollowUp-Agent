# P4-3 run identity, trusted evidence boundary, and P4-4 order — OWNER DECISION REQUEST

**State:** DRAFT / REVIEW ONLY / NO DECISION MADE, P4 remains **IN_REVIEW**.  
**Date:** 2026-11-19. **Issue:** [P4 #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).  
**Base:** Owner-merged [PR #22](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/22), `main@e20bbe088146f920c492e60ed2320b282252cde9`; its [postmerge CI #44505736877](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44505736877) **COMPLETED/SUCCESS** for backend and frontend.  
**Status:** Local, synthetic educational demo. **NOT FOR CLINICAL USE.** P3 `GOLD-EX-11` original OCR result remains **FAIL / NOT PROVEN**.

## 1. Existing verified implementation — not a complete P4 run

| Implemented in main | What it is | What it is NOT |
|---|---|---|
| `monitoring.compare_observation_history` (P4-1) | Pure patient-scoped, bounded, admissibility-checked history comparison | The `compare_observations` agent tool from `TOOL_CONTRACTS.md` `3.5 |
| `demo_rules_candidate` (P4-2) | Offline DR-001/003/005/009 proof with explicit **test-only** blocking count and candidate policy | Approved live `demo-policy-1.1.0` |
| `provenance_review_candidate` (P4-2d) | Offline DR-006/008 source/chronology proof on synthetic records | Trusted source lineage or a real verified-fact gate |
| `p4_readonly_provenance` (P4-2e) | Stored doctor role, patient assignment, document/fact decision lineage, and persisted creation timestamps | Original PDF/OCR byte-level or clinician review fidelity proof |
| `p4_document_preflight` (P4-2f) | Read-only selected-document blocker inspection: active/pending/rejected/corrected facts and open persisted issues | Run-complete VI-001..VI-006 gate; its `run_gate_completed` is **always False** |

All six intended `DR-*` identifiers have offline candidate coverage, but there is **no** approved unified evaluator, active policy, trusted full-run evidence bundle, `ReviewItem` table or agent workflow. P4 cannot be accepted solely from existing green unit tests.

## 2. Contract/dependency conflict — resolve before P4-3 schema

The normative draft [`DATA_DICTIONARY.md` `2.9](../contracts/DATA_DICTIONARY.md) defines `review_item.workflow_run_id` as **NOT NULL / FK workflow_run.id** and dedupe unique on `(workflow_run_id, dedupe_key)`; evidence links are ``2.10`. The same dictionary's `2.16` gives `workflow_run` a patient, doctor, injected clock, mapping/policy/workflow versions, immutable idempotency identity and app-DB status. [`STATE_AND_GRAPH_CONTRACT.md` `2/`7](../contracts/STATE_AND_GRAPH_CONTRACT.md) declares the app DB, not a graph checkpoint, the durable source of run status.

Current migrated SQLite ends at `0005_p3_ocr_provenance`. It has `observation`, `document`, `extracted_fact`, `fact_verification` and `verification_issue`, but **not** `workflow_run`, `review_item` or `evidence_link`. P4's plan describes review-item persistence while the workflow run owner is P5. No PR has authorized a P4 deviation from that boundary.

**Forbidden shortcuts:** do not put an arbitrary `run_id` into a `review_item`; do not create placeholder P5 graph/run nodes; do not nullable-ize or drop the normative FK just to make tests pass; do not treat a client-supplied blocker count, a selected-document clear result, or a persisted `VerificationIssue` with `workflow_run_id=NULL` as a whole-run clearance.

## 3. Decision R1 — run identity / review persistence dependency

### Option R1-A — Keep P4 persistence blocked until P5 (recommended under current AGENTS.md)

- **Allow now:** within P4, independently test the pure rules, source/scope blockers, full synthetic GOLD-A/B/C/D inputs and negative replay, while preserving `P4 IN_REVIEW`.
- **Defer:** P4-3 `review_item`, `evidence_link` DB migration, durable audit of review actions, review read/decision API and P4 acceptance until a separately authorized phase provides a real `workflow_run` identity.
- **Benefit:** honors [`AGENTS.md` `1/`2/`5](../../AGENTS.md) “one phase per PR / no early future-phase code,” preserves normative FK and keeps no false run statuses or synthetic clinical evidence.
- **Cost:** cannot claim to have *completed the planned P4 phase* or P4-3 until dependent run identity exists. A possible owner-approved **P4 scope amendment/conditional checkpoint** would be separate and explicitly recorded; no auto-acceptance here.

### Option R1-B — Owner-approved minimal P4 run-ledger exception (NOT authorized here)

- Requires a separately written **owner exception** to `AGENTS.md` phase/file rules, documented in `docs/roadmap/PHASE_PROGRESS.md`, and a revised, reviewed ADR/contract **before code**.
- Would define a real persisted, server-authored synthetic run selection and its stable identity/version/clock/idempotency/doctor/patient/document/observation binding, without LangGraph agents/checkpointer, LLM, API tasks or simulated “running/completed” decisions.
- Requires first specifying how P5 adopts the exact durable run identity and statuses, how run-selected document/observation IDs are stored/validated, and how P4 can distinguish incomplete vs eligible runs without inventing a fake successful gate.
- A separately reviewed P4 migration can be considered **only after** owner chooses this architecture and a real run-status lifecycle is designed. This note does not approve it.
- **Benefit:** potential P4-3 independent persistence work before P5. **Cost:** architecture coupling and phase exception; higher migration/replay risk.

### Rejected R1-C — Fake IDs, no FK, or untrusted ephemeral run clearances

Not suitable. These produce silent false trust, broken idempotency and non-replayable evidence. **Do not implement.**

**Proposed choice:** **R1-A**, unless the owner explicitly prioritizes full P4 persistence before P5 *and* approves and reviews R1-B's phase/architecture exception. No owner decision is inferred from merging this proposal.

## 4. Decision R2 — trusted review evidence adapter / tool contracts

**Open:** [`TOOL_CONTRACTS.md` `3.5](../contracts/TOOL_CONTRACTS.md) pure `compare_observations(current≤6, lookback_days)` has no authorized baseline-history source, while existing pure comparison works with historical observations. `3.7` takes `verified_facts`, `comparisons`, `policy_version` but omits server-scoped observations, clock, trusted VI gate and policy content.

**Recommended contract-only next step (separate owner review):**
1. Define a **server-owned, run-bound** immutable evidence input containing authenticated doctor/patient, selected IDs, injected UTC clock, stored fact/document decision provenance, eligibility exclusions, and *independently computed* comparisons. A caller may not declare identity, verified lineage or gate state.
2. Define a gate that counts **active** facts selected by an actual run, excludes corrected originals **only** on valid persisted correction lineage, treats ordinary rejected facts as blockers, recomputes VI-001..VI-006 as required, and resolves document recovery and persistent open `VI-002` policy **explicitly**. `E_UNVERIFIED_FACT` refers to extracted facts, never a self-reported admissible observation.
3. Clarify `compare_observations` history acquisition vs pure comparison and `evaluate_demo_review_rules` evidence/clock/policy signature **before** changing normative tool APIs. Keep no tools/agents/APIs implemented in this decision PR.
4. Until that interface and R1 are signed off, P4 candidate outputs are *non-persisted, educational test results*, never live draft inputs.

## 5. Decision R3 — OQ-R01 demo policy version / parameters

The proposal `demo-policy-1.1.0` in `DEMO_REVIEW_RULES.md` is a **proposed arbitrary synthetic demo configuration**, not approved values. Ruff/pytest green does not authorize any numeric value. The owner must separately ratify a particular file/version, parameters and mapping-version compatibility. The “conflict_tolerance=0” used in tests is not a medical threshold and is **not** automatic approval for runtime.

**Recommended:** leave all policy values unactivated until R1/R2 and an explicit owner OQ-R01 ratification. No thresholds added or changed in this PR.

## 6. P4-4 work that is still safe before R1–R3

Prepare a separately reviewed **offline-only**, deterministic, typed synthetic GOLD-A/B/C/D fixture-replay matrix, reading facts and observations from test SQLite (including actual corrected/superseded lineage) and asserting:
- Case A/B/C/D expected `VI-*` vs `DR-*` **separation**, admissibility and trust labels; each fixture supplies exact expected flags for its approved candidate scope only.
- Rejected/missing/wrong-patient/unsupported-unit/ambiguous-time/multi-document/out-of-order/duplicate cases; same-source fact/observation never treated as two independent sources.
- Fake `blocking_fact_count=0` **cannot authorize** the downstream live path. Tests must never label `run_gate_completed=True`, because there is no real workflow run.
- Repeat/permutation stability, bounded inputs, no writes or side effects; no document-source file claim, LLM, task, notification or patient message.
- `GOLD-EX-11` remains a **technical P3 FAIL**, never converted into a passing OCR detection merely because a synthetic rule test passes.

A green offline matrix will count as **P4 component verification only**, not end-to-end workflow/P4-3 acceptance.

## 7. Owner decision table — no implicit approval

| Decision | Choices | State now |
|---|---|---|
| **R1: P4-3 run identity** | **A** defer DB persistence until real P5 run identity; **B** authorize a minimal P4 run-ledger exception with formal ADR/scope approval | **OPEN; recommend A** |
| **R2: tool/evidence contract** | Approve a separately reviewed typed run-bound evidence adapter and VI gate contract (do not silently edit `3.5/`3.7) | **OPEN** |
| **R3: OQ-R01 synthetic parameters** | Explicitly approve or reject a specific version and every named demo threshold; no medical interpretation | **OPEN** |
| **R4: sequencing** | Authorize **isolated P4-4 offline GOLD A/B/C/D verification**, while R1–R3 remain unresolved and P4 stays IN_REVIEW | **RECOMMENDED, NOT AUTHORIZED BY THIS DOC** |

**Required owner response:** identify R1-A or R1-B and, independently, whether the limited R4 offline fixture-replay work may proceed. If R1-B, authorize a separate ADR/phase-scope exception review *before code*. R2/R3 are separate approvals. Merging a docs-only PR is **not itself** an approval of any option or phase status.

## 8. Evidence, paths, rollback

**Executed here:** private GitHub read-only review of `AGENTS.md`, `DATA_DICTIONARY.md` ``2.9/2.16, `STATE_AND_GRAPH_CONTRACT.md` `2/`7, `TOOL_CONTRACTS.md` ``3.5/3.7 and merged P4 service modules; PR #22 merge verified at exact `main@e20bbe088146f920c492e60ed2320b282252cde9`; postmerge GitHub Actions `44505736877` **SUCCESS**.  
**Not executed:** local Python/Windows tests, P4-3 migration, P4-4 gold suite, Playwright or any agent/LLM; this is a docs-only decision document. New docs PR CI must independently succeed before owner merge.  
**Exact changed paths:** this new proposal document, plus **append-only** `docs/phase-reports/PHASE_4_REPORT.md` checkpoint. No existing normative contract modified.  
**Rollback:** close the docs-only PR unmerged; no executable/data effect. Tracking issue #14 remains OPEN. **Phase P4 remains IN_REVIEW.**
