# P5-F2 — immutable V2 evidence bridge: implementation candidate for independent review

**Status:** IN_REVIEW / NOT OWNER ACCEPTED / NOT MERGED. **Scope:** local synthetic academic application ONLY, NOT FOR CLINICAL USE. **Design authority:** owner [ratified P5-F2 scope in PR #34](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/34#issuecomment-7070783010), merged design at `main@26aabd8a8d5d0987430e64e97cbd9ae110cb1a52`; [postmerge CI #44978669932](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44978669932) independently verified **COMPLETED SUCCESS** for Backend and Frontend. This is **F2 starting evidence**, not its own test result.

## Scope and reviewable diff

1. `backend/app/schemas/p5_review_evidence.py`: strict frozen, typed `EvaluableReviewEvidenceV2`, `VerifiedFactV2`, `ObservationV2`, `ComparisonV2`, `EvidenceExclusionV2` with `runtime_evaluable=False`, `rules_executed=False` and `policy_status=unapproved`. No API deserializer or caller-supplied clearance.
2. `backend/app/services/p5_run_gate.py`: additive `inspect_current_run_gate_locked` and `require_existing` guard inside the exact F1 snapshot evaluator; requires an existing persisted current matching immutable gate verdict and verifies stored blockers. It **cannot** create a gate row when called for F2; normal F1 behavior and tests remain unchanged.
3. `backend/app/services/p5_evidence_bridge.py`: server-owned internal-only entry point. Fresh SQLite `BEGIN IMMEDIATE`; F1 current-snapshot source bytes, doctor session, assignment, selected source, fact and issue recheck; F2 verified fact projection + selected observations and same-patient 365-day bounded history; fixed current cap 6 (F0 cap 20); deterministic P4 comparisons, typed missing-baseline and explicit historical exclusions. Rechecks F1 again near return; always rolls back; no graph or DR.
4. `backend/tests/p5/test_p5_evidence_bridge.py`: synthetic focused positive and negative cases (missing/halt/stale F1, changed file/fact/decision/run, forged blocker, revoked doctor, self-report history, missing/excluded baseline, >6 selection, document-only unit, invalid role, caller-override attempt, frozen non-runtime receipt). More independent review/coverage may be required before approval.
5. `docs/contracts/TOOL_CONTRACTS.md`: additive internal V2 bridge and §3.5/§3.7 non-executable adapter, no rewrite of existing tool declarations.
6. `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`: additive sealed V2 evidence boundary, explicit no-graph condition, no cached-token trust.
7. This `docs/phase-reports/P5_F2_IMPLEMENTATION_REVIEW_20261122.md`: required truthful execution/risk ledger.
8. `docs/roadmap/PHASE_PROGRESS.md`: append-only F2 candidate checkpoint.

**No other files authorized.** No database model/migration, P3 OCR, P4 rule policy/engine, API, agent/LLM, UI, tasks/notifications, or external services. None have been changed as part of this PR.

## Security properties to audit

- **F1 persisted authorization:** F2 only accepts a previously stored F1 PROCEED row matching exact `run_id,gate_version,fingerprint`, with old blocker rows matching deterministic recomputation and doctor/current synthetic patient scope. It cannot accept an F0-only queued run, F1 HALT/UNAVAILABLE, or stale cached gate after file/fact/issue/observation changes.
- **Read-only guarantee:** F2 owns an SQLite `BEGIN IMMEDIATE` and always `ROLLBACK`. Its F1 helper has an explicit `require_existing` path before any insertion. No F1 audit/event or other mutations from projection.
- **Provenance:** Existing P4 preflight validates the selected documents' actual persisted doctor decisions, not a caller-provided `verified` flag. The P4 provenance reader verifies stored document-source lineage and caps patient history. Selected invalid/current records fail closed; invalid history gets explicit exclusions and never shifts a baseline. `self_reported_validated` retains the trust label.
- **Versioned deterministic comparison:** only run-selected current 0..6; F0's 7..20 cannot be silently truncated. History is server-derived patient-scoped, ≤100, fixed 365 days and deterministic latest prior tie-break, with `no_baseline` rather than a fabricated normal or imputed reading. `g/dL` document-only facts never map into observation measurements.
- **No later authority:** `EvaluableReviewEvidenceV2` remains a non-executable typed projection. No `ReviewFlag` / `DR-*`, `review_item` or `evidence_link`, graph transition, task, summary, LLM call or patient messaging.
- **Residual risks:** filesystem bytes are not atomically held by SQLite. A future runner must independently revalidate scope, exact fingerprint, selected bytes and user session at execution. Existing F1 historical original `VI-002` stays OPEN when a separately verified recovery is selected. P3 real `GOLD-EX-11: 1O5 → 105` **FAIL / NOT PROVEN** remains unresolved and is NOT corrected/waived by a file checksum.

## Verification gate — evidence status at branch creation

- **Verified baseline**: exact merged F2 design and main Backend+Frontend CI SUCCESS on `26aabd8...`.
- **Executed in this development pass**: GitHub code inspection and branch plus source/test/document commits; these operations do **not** prove candidate correctness.
- **Candidate checks still required**: exact-head GitHub Python 3.12 Ruff lint + format, full pytest, Alembic upgrade/downgrade/re-upgrade, OpenAPI, secret scan; full Frontend Node 22 typecheck/lint/tests/build; explicit newly written F2 test results; independent code review; owner isolated Windows 5.1 `setup.ps1` + `test_all.ps1` at exact final reviewed SHA (Playwright SKIP remains SKIP). Record exact runs and failures before considering approval. Any CI problem must be fixed in the F2 allowlist, never by weakening a historical P3/F1 test or modifying policy.
- **No actual source-glyph/Ollama/LLM/browser execution** is claimed.

**Owner merge only after review.** P4 `IN_REVIEW`, issue #14 OPEN, P5 overall unaccepted; **NOT FOR CLINICAL USE**.
