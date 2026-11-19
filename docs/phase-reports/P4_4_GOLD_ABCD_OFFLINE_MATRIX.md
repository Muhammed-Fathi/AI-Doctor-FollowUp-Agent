# P4-4 / R4 — GOLD-A/B/C/D offline SQLite expected-output matrix

**STATUS: OWNER-AUTHORIZED COMPONENT TESTING / PR REVIEW, NOT A P4 ACCEPTANCE.**  
**Date:** 2026-11-19. **Issue:** [#14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).  
**Baseline:** Owner-merged [PR #23](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/23), `main@d100df80ebaf8a0dd8b98128ea936e495fbb320a`. Post-merge main [CI #44510682860](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44510682860) started after merge; record its **observed result**, not assumed success, at owner review time.  
**Owner decision in chat:** `"تم دمج PR #23، وموافق على R1-A وR4"`. This **authorizes R1-A/R4 only**; it does NOT ratify R2 evidence/tool adapter, R3/OQ-R01 policy values, P4 phase acceptance, P5, real OCR, or any runtime integration.

## 1. Architecture and test-only boundary

**R1-A selected:** Defer P4-3 `review_item` / `evidence_link` persistence until a real P5-owned, durable `workflow_run` identity is available. Preserve the normative `review_item.workflow_run_id NOT NULL FK`. There are no fake run IDs, placeholder schema, waived FKs, or workflow-state claims in this PR.

**R4 selected:** Execute *offline component verification* of the published [GOLD_FIXTURES.md](../evaluation/GOLD_FIXTURES.md) `2–5 using **real migrated test SQLite** and existing P4-1/P4-2a/P4-2d/P4-2e/P4-2f pure services. Every document in this harness is **synthetic staged database metadata/facts** matching the declared fixture text, not a real PDF, PNG, OCR result, source-image comparison, uploaded report, or a P3 workflow run. Verification decisions inserted by the test are scripted fixture state, not witnessed clinician interaction.

All `CandidateDemoPolicy` / `CandidateProvenancePolicy` values (lookback 90; stale 30; deltas 10/8/15/40; test-only conflict tolerance 0; item cap 3; `as_of_utc=2026-11-14T12:00:00Z`) are **arbitrary candidate test inputs** from the design examples, NOT active `demo-policy-1.1.0`, approved clinical boundaries, or R3 signoff. Both candidate evaluators still accept a **caller-controlled TEST-ONLY `blocking_fact_count`**. Tests independently check the stored selected-document preflight where relevant and **always require `run_gate_completed=False`**, never claim a run was cleared.

## 2. Exactly-scoped expected matrix

| Case | Stored input setup | Only the offline candidate output asserted |
|---|---|---|
| **GOLD-A** | P2-seeded A Oct observations, three *test-injected* Nov 1 check-ins; one synthetic `Hemoglobin 13.4 g/dL` verified document fact collection | Closed mapping produces **0** observation for hemoglobin; no candidate DR items for the post-check-in series |
| **GOLD-B** | P2-seeded B time series; synthetic already-verified `Fasting glucose 104 mg/dL` fact and a *test-created* mapped observation at Nov 2 00:00Z | Exactly one `DR-005`, systolic 158–146 = **12 mmHg**, trust `self_reported`, exact neutral message and two observation refs; glucose has a baseline and no rule |
| **GOLD-C, pre** | P2 baseline 96 mg/dL; synthetic `REPORT-C-01` as **three pending stored facts** (`report_date` ambiguous, `test_name` clean, `value` literal `1O5` / missing unit), flags exactly as in fixture spec | Existing P3 `quality.sync_issues` computes `VI-001, VI-002, VI-003, VI-005`, including the 3-fact message; P4 document preflight says blocked and **run_gate_completed=False**. No post-verification DR evaluator called |
| **GOLD-C, corrected fixture** | Test creates script-only, stored doctor correction decisions retaining rejected originals, verified corrected value/date; P3 quality sync re-derives open blockers; test constructs mapped observation | VI blockers resolve in *test database*; corrected `glucose 105` maps to Nov 3 00:00Z; baseline 96; mixed trust, delta **9**, no candidate DR flags; **still no run gate** |
| **GOLD-D** | New synthetic D patient/6 persisted observations: HR singleton Sep 1, sys 128→130 and exact duplicate 130 Oct 20, dia 82→250 | Exactly one each `DR-001` HR, `DR-003` HR, `DR-005` dia, `DR-008` sys duplicate, `DR-009` dia; `DR-006` none (no two distinct persisted verified document sources) |

Additional negative checks: cross-patient mixed evidence raises scope error, rejected/wrong-unit/future values are excluded with reason, pre-verification blocking count produces `E_UNVERIFIED_FACT` in the **test-only candidate** and cannot mutate the independent stored preflight, reverse-order/replay stable output and dedupe, no new observation or workflow rows from pure evaluation.

## 3. Exact file inventory

1. `data/synthetic/golden_cases/GOLD-A.expected.json` — immutable test expectation.
2. `data/synthetic/golden_cases/GOLD-B.expected.json` — immutable test expectation.
3. `data/synthetic/golden_cases/GOLD-C.expected.json` — immutable pre- and post-correction test expectations.
4. `data/synthetic/golden_cases/GOLD-D.expected.json` — immutable test expectation.
5. `backend/tests/p4/test_p4_gold_abcd_offline_replay.py` — nine offline tests on migrated SQLite plus existing pure P3/P4 helpers, no API/LLM.
6. `docs/phase-reports/P4_4_GOLD_ABCD_OFFLINE_MATRIX.md` — this report.
7. `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — append-only provisional test-count integrity note (does not overwrite P3).
8. `docs/phase-reports/PHASE_4_REPORT.md` — append-only P4-4 checkpoint.
9. `docs/roadmap/PHASE_PROGRESS.md` — append-only owner R1-A/R4 authorization note, as required by `AGENTS.md` `1–2.

## 4. Limitations, explicit non-goals and gated next work

- **NOT a P3 OCR evidence acceptance test.** Original real `GOLD-EX-11=FAIL / NOT PROVEN` due to `1O5`→`105` remains unchanged. The test intentionally feeds the **declared** raw `1O5` into synthetic SQLite; no real Tesseract, image upload, source bytes or glyph detection is tested.
- **NOT P5 end-to-end workflow or runtime integration.** No `workflow_run` / `review_item` persistence, draft summary, approval, task, notification, agent tool, live API, external side effect, or browser/E2E test. No source attestation from an actual physician.
- **NOT a real verification gate.** The read-only selected-document preflight covers only chosen documents; it does not re-evaluate all run-selected documents, ongoing recovery, or the run-level VI-001..VI-006 gate. `run_gate_completed=False` is always preserved.
- **No approved demo-policy values.** R3/OQ-R01 remains OPEN. Reconcile `TOOL_CONTRACTS.md` ``3.5/3.7 and R2 before any trusted adapter.
- **No approved P4 closure.** R1-A explicitly defers P4-3. P4 must remain **IN_REVIEW** until the owner revises its scope or the P5 run-ledger dependency is implemented, and full safety/acceptance tests complete.

## 5. Test and owner-gate evidence

At initial authoring: **No local Python/Windows tests executed here**. Existing pytest collection before this file: **988 backend / 443 P3**. Nine test functions give a *provisional* expectation **997 backend / 443 P3**, **not a pass count**. The actual collection must be derived from exact-head GitHub CI, with handoff corrections append-only as required. Ruff lint/format, full pytest, Alembic smoke, OpenAPI 17/18/43, scanner, Node 22 checks, and owner Windows `setup.ps1` + `test_all.ps1` are required before owner reviews merge.

**Reproducible targeted test** (from isolated worktree with dependencies installed):
`.\.venv\Scripts\python.exe -m pytest -q backend/tests/p4/test_p4_gold_abcd_offline_replay.py`

**Owner control:** PR remains unmerged until exact-head CI and Windows evidence are reviewed. Owner retains all merges, parameter approvals, P4/P5 phase decisions and open issue #14. **NOT FOR CLINICAL USE.**
