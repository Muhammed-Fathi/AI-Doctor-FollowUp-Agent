# P4-2f — selected-document verification preflight from stored SQLite evidence

**Status:** OFFLINE INTERNAL CANDIDATE / OWNER REVIEW REQUIRED. No run-scoped verification gate, P4 acceptance, or runtime review-rule activation.
**Baseline:** owner-merged PR #21 at `main@1ca8a839c563589ce37f85d86d4fa4251ffe1c8c`; [postmerge CI #44500187766](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44500187766) **SUCCESS**.
**Data:** fictitious local educational fixtures ONLY; NOT FOR CLINICAL USE. P3 GOLD-EX-11 real OCR failure stays FAIL / NOT PROVEN.

## Goal and exact scope

PR #21 projects SQLite patient-scoped observation/source lineage, but `evaluate_offline_provenance_candidates` still uses a *caller-controlled* `blocking_fact_count`. It would be unsafe to describe a supplied zero as a true verification clearance. This PR adds a distinct **read-only selected-document preflight** which derives blockers directly from SQLite, **without** passing any computed count into a live rule evaluator.

- Require a server-supplied authenticated `Principal`, and verify stored active doctor role, assigned synthetic patient and 1–8 distinct explicitly selected document IDs. Unknown/foreign documents return neutral 404; unassigned roles return 403.
- Read bounded per-selection rows (≤200 facts, ≤100 open issues); fail closed above caps and do not assume missing rows are clean.
- On each selected document: require stored `extraction_status='verified'`, no terminal `failure_code`, a matching patient reference, no persisted `verification_issue.state='open'`, at least one fact.
- Count active facts. A pending/plain rejected fact is a blocker (`VI-002`-compatible conservative scope); a rejected original with a corrected successor is historical **only when its successor is verified and the original fact has an exactly-one recorded `corrected` decision from a stored active doctor with a matching replacement value**. Invalid corrections do not clear a rejected original.
- Verify each active `verified` fact against exactly one persisted doctor `FactVerification`. Derived results are immutable and deterministic, with *reason codes*, fact counts and selected document IDs, **not patient text, PDF bytes or medical advice**.
- `candidate_documents_clear=True` is only a statement about **these selected stored document rows** at inspection time. `run_gate_completed=False` ALWAYS, even when no blocker is found. No workflow_run identity, recovery semantics, unrelated documents, full VI-001..006 recomputation, original source OCR quality or integrity check is supplied. A later real run-scoped gate must not blindly reuse the boolean.

## Changed paths

1. `backend/app/services/p4_document_preflight.py` — new independent read-only selected-document preflight.
2. `backend/tests/p4/test_p4_document_preflight.py` — ten synthetic migrated-SQLite tests (verified, corrected original, missing decision, pending/rejected, open/resolved issue, printed patient reference, scope, duplicate/unknown document, tampered correction, purity/determinism).
3. `docs/phase-reports/P4_2F_SELECTED_DOCUMENT_PREFLIGHT.md` — this report.
4. `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — append-only provisional pytest collection checkpoint.
5. `docs/phase-reports/PHASE_4_REPORT.md` — append-only phase tracking.

## Safety boundaries / remaining work

No modifications to old P3 verification pipeline, database migrations, source-image comparison, API routes, tool contracts or existing rule engines. No P5, LLM, approvals, tasks, messages or external calls. A future caller must supply a *session-derived* server Principal, not user-entered identity. The new preflight must not be called by the agent or API until a separate reviewed adapter with a real `workflow_run` selection and policy is explicitly approved.

**Deferred:** `TOOL_CONTRACTS.md` `3.5/`3.7 interface reconciliation; full VI-001/003/004/005/006 re-evaluation over exactly the run's inputs, source-file integrity and correction/recovery lineage policy; OQ-R01 demonstration numeric thresholds; P4-3 workflow run/review item persistence strategy; end-to-end GOLD-A/B/C/D; owner Windows acceptance and explicit P4 phase sign-off.

## Test evidence / merge criteria

At authoring, **no local Python/Windows test has been run** in this assistant environment. Ten new tests give an **estimated collected** total of `987 backend / 443 P3` (up from the measured PR #21 baseline of 977). This is a provisional test-count pairing, **not 987 successful tests**. Exact-head CI must confirm the collection count and pass full pytest, Ruff lint/format, Alembic, OpenAPI, scanner, and Node frontend. Owner must run the same-head Windows `setup.ps1` + `test_all.ps1` in a separate worktree before authorizing merge. No self-approval/merge.

**P4 IN_REVIEW; P3 GOLD-EX-11 FAIL / NOT PROVEN.**
