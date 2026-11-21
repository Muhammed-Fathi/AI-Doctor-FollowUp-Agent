# P5-F0 run identity and persistent doctor-scoped selection — code review report

**State:** IN_REVIEW / NOT MERGED / NOT ACCEPTED. **CH-01 ratified:** Owner posted exact `RATIFY-P4-P5-CONDITIONAL-HANDOFF-FOUNDATION-ONLY` on [PR #30](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/30#issuecomment-7063957797), merged it to `main@12c1920d2923e627621b16ac800d07a7054bad87`, and exact-main [CI #44913434002](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44913434002) completed SUCCESS. **Owner P5-F0-only scope applies;** P4 remains IN_REVIEW; no P5-F1/F2/graph permission implied. Synthetic educational project, NOT FOR CLINICAL USE.

## 1. Exactly what this PR proposes

- `backend/app/db/models.py`: genuine `workflow_run` parent with immutable initial versions/clock/patient/doctor/idempotency identity, initially **queued**; three selected-source tables `run_selected_document`, `run_selected_observation`, `run_source_omission`; previously deferred nullable run references on `audit_event` and `verification_issue` become real run FKs. There are **no** `review_item`, `evidence_link`, graph or draft objects here.
- `backend/migrations/versions/0006_p5_run_foundation.py`: additive, reversible-on-empty SQLite migration; strict FKs/indexes, DB-level UPDATE/DELETE blockers on the three selection tables; rollback refuses if any run, selection or run-linked historical audit/VI row remains. Existing P3 records and old terminal VI-002 must remain unchanged.
- `backend/app/services/p5_run_foundation.py`: internal-only, stored-session/doctor/assigned-synthetic-patient scope checked by the existing R21 selection preflight; canonical bounded doc/observation IDs, saved original source SHA (not OCR proof), selected observation trust/source identity, persisted doctor-context omission with OPEN historical VI-002 reference; real run row/manifest plus one audit event in the caller's app-DB transaction; same-request replay returns the same real run ID. It can only return `status=queued`, `run_gate_status=unavailable`, `run_gate_completed=False`, `runtime_evaluable=False`. No external API route, no tool, no LLM.
- `backend/tests/p5/test_p5_run_foundation.py`: migrated synthetic SQLite tests for identity, scope, replay, selected-source audit, OPEN VI-002 preservation, fail-closed invalid input, DB immutable manifest/FKs and empty-schema migration roundtrip.
- `docs/roadmap/PHASE_PROGRESS.md`: append-only progress note (not owner acceptance).

## 2. Defined limits and implementation risks

- The selected-source SHA is **persisted source metadata, not source-byte read/attestation**, accurate PDF glyph/OCR proof, or a signed clinician review. The prior P3 `GOLD-EX-11` original OCR `1O5`→`105` stays **FAIL / NOT PROVEN**.
- An internal authenticated-principal service call proves a stored doctor context when invoked correctly; P6 user-interface interaction, authorization of an actual doctor click/signature and exact end-to-end choice path have **not** been implemented or exercised.
- The existing P4 R21 inspector only validates a candidate shape. P5-F0 persists a reviewed source selection, but does **not** compute an exhaustive run-bound VI-001..006 gate, a durable same-snapshot freshness revalidation, or an actual run eligibility decision. Historical original VI-002 stays open. Snapshot/replay TOCTOU and concurrent start conflict handling require explicit subsequent design/testing.
- The pinned `demo-policy-1.1.0` string is a **reference identity**, not runtime policy authorization; no DR outputs are enabled or persisted.
- No `review_item`, `evidence_link`, task, notification, `agent`, `llm`, LangGraph, checkpoint, public endpoint, P6 UI, real patient data or external egress.
- P5-F0 is not P5 phase acceptance and cannot be interpreted as P4 phase PASS.

## 3. Known legacy compatibility blocker — requires owner scope decision

`backend/tests/p2/test_p2_migration.py` historically hardcodes `HEAD_REVISION="0005_p3_ocr_provenance"` and expects exact **P1+P2+P3** table sets after `upgrade head`. A legitimate new `0006_p5_run_foundation` revises `head`, so those P2 assertions will be stale, even when the new migration is correct.

**CH-01's narrow file allowlist does NOT permit updating `backend/tests/p2/**` inside this P5-F0 code PR.** Therefore, do not bypass or edit the test, invent a green CI result, or mark the PR merge-ready. The required next owner decision is a **separately scoped P2 migration-test maintenance PR** (or an explicit recorded P5-F0 exception for that one exact historical test file) to keep old P2/P3 acceptance assertions pinned to their historical revision while separately verifying new F0 head/schema. Until that change is authorized and independently merged/verified, the full suite may fail for a known historical expectation and this P5-F0 PR remains blocked.

## 4. Verification and owner gate

**Design reviewed in preparation:** CH-01, AGENTS.md, STATE_AND_GRAPH_CONTRACT.md §§2/7, DATA_DICTIONARY.md §§2.9/2.16/2.17, P4 R21-S1 inspector, ORM, existing P2/P3 migrations/tests, audit and scope utilities. **Executed to date:** connected GitHub exact-main CI check and source reviews. **Not executed here:** local Python 3.12, Ruff, full pytest, Alembic migration smoke, Windows PowerShell, actual OCR, LangGraph, browser, Ollama. Run exact-head CI after pushing and record actual outcomes with SHAs; never claim test PASS from a test definition.

**Before any owner merge:** resolve legacy migration-test version boundary by a scope-valid, separately reviewed correction; successful exact-head Backend and Frontend CI; owner isolated Windows PowerShell 5.1 `setup.ps1` + `test_all.ps1` on exact final branch SHA; review source/doctor session scope, nullable historical FK transition, DB trigger/rollback behavior, idempotency replay and absence of P4/clinical runtime activation. Optional Playwright SKIP must remain SKIP.

**Rollback:** close unmerged PR; no live DB changes. On migrated DB with saved runs, downgrade deliberately refuses to lose audit provenance. Preserve existing data and obtain an owner-reviewed archive/rollback plan, not force schema deletion.

**Tracking:** P4 [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) stays OPEN. CH-01 is a sequencing exception only. P4 IN_REVIEW; P5-F0 IN_REVIEW; no phase PASS.
