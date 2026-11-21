# P5-F1 — internal run-bound verification gate: implementation review (in progress)

**Status: IN_REVIEW, NOT MERGED, NOT OWNER ACCEPTED.** Base `main@55e86083dec15334344917fdeac38516f6413957`, owner-merged [PR #32](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/32), exact-main [CI #44922487176](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44922487176) **COMPLETED SUCCESS** for Backend+Frontend. Owner written ratification: [`RATIFY-P5-F1-BOUNDED-RUN-GATE-SCOPE`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/32#issuecomment-7065279772). CH-01/P5-F0 does not imply full P4/P5 phase acceptance.

## Scope delivered for review

- `backend/app/db/models.py`: P5-F1-only `RunGateEvaluation` and `RunGateBlocker` schemas with strict FKs, closed gate/VI vocabularies, unique run+snapshot+gate version.
- `backend/migrations/versions/0007_p5_run_gate.py`: additive gate evidence tables with UPDATE/DELETE immutability triggers and fail-closed downgrade when evidence exists.
- `backend/app/services/p5_run_gate.py`: internal-only synthetic, server-owned `run_id` entry point. Fresh clean SQLite session, write lock (`BEGIN IMMEDIATE`), stored active doctor/session/assignment, immutable F0 selected documents/observations/omissions, selected actual file bytes SHA, P3 verification events, VI-001..006/recovery checks, deterministic fingerprint + idempotent gate/audit. Frozen receipt `runtime_evaluable=False` on *all* paths; no graph or P4 DR activation even on F1 PROCEED.
- `backend/tests/p5/test_p5_run_gate.py`: initial synthetic SQLite checks for source integrity, proceed vs missing-source, stale source, VI-002 blocker, recovery original open VI, selected self-report label, revoked session, persisted gate immutability, empty 0007 migration roundtrip. Matrix must expand after CI and independent review.
- `docs/contracts/DATA_DICTIONARY.md` / `STATE_AND_GRAPH_CONTRACT.md`: append-only F1 schema/typed boundary clarification, no rewrites of P3 contracts.
- `docs/roadmap/PHASE_PROGRESS.md`: append-only P5-F1 implementation checkpoint. This report is not approval.

## Explicit non-goals / safety

No P3 historical `verification_issue` mutation, no source glyph OCR correctness claim (original real `GOLD-EX-11 = FAIL / NOT PROVEN`), no `review_item`/`evidence_link`, no DR rule output, no LangGraph/N2/checkpoint/LLM, no agent drafts, no API/UI, no medication or patient advice, no task, notification or external message, no real medical records. F0 `run_gate_status=unavailable`, `run_gate_completed=False` stays unchanged. F1 `proceed` is *not* `runtime_evaluable` and needs F2 recheck of the same-source state before use.

## Mandatory before merge

- Independently inspect the SQL lock + filesystem TOCTOU boundary and concurrent replay; SQLite excludes simultaneous DB writes while F1 evaluates but cannot make disk bytes transactional.
- Audit exact F1 issue predicates, document correction/verification lineage, dated candidate and selected observation trust; add negative tests including all VI types and races before claiming coverage.
- **Known likely historical CI version boundary:** new `0007` becomes `head`, so historical P2/P3 schema tests and `scripts/python/check_alembic_smoke.py` which pin `0006` may fail. These are **not** included in owner-ratified P5-F1 code allowlist. Do **not** edit any legacy P2/P3/smoke script without a separate explicit owner exact-file exception recorded first. Do not waive a failed check.
- Full Pytest/ruff and 0007 migration smoke/openapi/Frontend on exact PR-head CI. Owner independent Windows 5.1 `setup.ps1` + `test_all.ps1` on exact final SHA (optional Playwright SKIP reported as SKIP, not PASS). This GitHub connector session cannot run owner Windows, real OCR, browser, Ollama, or Tesseract.
- Owner review and merge only. P4 remains **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN. **SYNTHETIC EDUCATIONAL / NOT FOR CLINICAL USE.**

## Execution evidence classification

**Reviewed:** PR #32, F1 design, F0 source and migration, P3 VI helpers and state/contracts, F1 code diff. **Executed:** GitHub file creation/branch commits; independent pre-code merged-main CI read. **Not yet executed:** local F1 Python tests, SQLite migration, owner Windows; exact-head CI awaits PR. These are not PASS claims.

**Rollback:** while PR unmerged close it; no main changes. When F1 gate evidence exists, `0007` refuses destructive downgrade, and archived rows require owner-operated handling. No destructive cleanup or migration of real data is authorized.
