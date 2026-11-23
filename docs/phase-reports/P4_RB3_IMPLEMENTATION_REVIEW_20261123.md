# P4-RB3 Durable Review Persistence Implementation — Review Candidate (2026-11-23)

**Status: IN_REVIEW / NOT ACCEPTED / DRAFT PR PENDING.** Repository: `Muhammed-Fathi/AI-Doctor-FollowUp-Agent`. Base `main@6d121228a9e4a1c0571c513d158c2cb887b1486` (post-PR #42 merge; CI `#45141004060` `success`). Ratified Revision-6 design: `docs/phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md` (git blob `9b9160b329afa7b41baa971eb9c2558f2c6e073e`, SHA-256 `3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`, owner marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` at [PR #42 comment #7095039109](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/42#issuecomment-7095039109)). P4 issue #14 remains OPEN.

## 1. Authorized N1–N13 paths delivered

Only the 13 paths specified in the ratified design allowlist (`N1`–`N13`) were created or updated:

1. **N1** `backend/app/services/p4_rb3_review_persistence.py` — server-only `persist_run_review_items(db, *, principal, run_id, validation_clock, upload_root) -> ReviewPersistenceReceiptV1` implementing Phase 1 (`P1`–`P6`) and Phase 2 (`T1`–`T18`) inside `BEGIN IMMEDIATE`, F2/RB1 re-verification, independent stored-lineage proof (`proved_by_obs`), Alt A2 transport boundary over the unchanged RB2 evaluator, conservative DR-006 whole-invocation `409 E_VALIDATION` denial, `OverflowError`/pre-year-2 timestamp guard, 9-key bounded audit contract (`<= 500` chars), exact zero-write replay, and 8-reason deterministic conflict precedence.
2. **N2** `backend/app/schemas/p4_rb3_review_persistence.py` — frozen DTOs (`RB3DenialReason`, `PersistedEvidenceExclusionV1`, `LayeredEvidenceExclusionsV1`, `ReviewPersistenceReceiptV1`).
3. **N3** `backend/app/db/models.py` — additive `WITHOUT ROWID` (`{"sqlite_with_rowid": False}`) ORM models `ReviewItem`, `EvidenceLink`, `ReviewEvaluation` and `__all__` exports, preserving all pre-existing models unchanged.
4. **N4** `backend/migrations/versions/0008_p4_rb3_review_persistence.py` — Alembic revision `0008_p4_rb3_review_persistence` (`down_revision = "0007_p5_run_gate"`), creating the three `WITHOUT ROWID` tables, 9 indexes (`ux_review_dedupe`, `ux_review_order`, `ix_review_patient_state`, `ix_review_run`, `ux_evidence_link_observation`, `ux_evidence_link_span` inert, `ix_evidence_link_owner`, `ix_evidence_link_obs`, `ux_review_evaluation_run`, `ix_review_evaluation_patient`), 25 triggers (`G1`–`G25`) in `TRIGGER_CREATION_ORDER`, and non-empty downgrade refusal.
5. **N5** `backend/tests/p4/test_p4_rb3_review_persistence.py` — 13 comprehensive test functions covering RB3-01..24, 33..52, 59..66, 70..73, 79, 82..88, 92..99, 111..114, 128 (auth/session/scope/gate/tamper, empty selection, input caps, layered exclusions & precedence, single-winner concurrency, R01–R08 edge behavior, no HTTP route / caller authority, input identity sensitivity, 8-reason replay conflicts, DR-006 unit boundary denial, provenance/superseded-fact lineage, 9-key audit domain).
6. **N6** `backend/tests/p4/test_p4_rb3_migration_guards.py` — 7 comprehensive migration/SQLite guard test functions covering RB3-29..31, 54..58, 67..69, 78..81, 89..91, 100..110, 115..127 (populated downgrade refusal & empty roundtrip, ORM/migration parity & Alembic autogenerate blindness to `WITHOUT ROWID`, per-RB3-table 25 triggers + 11 historical triggers intact + `recursive_triggers=0`, CHECK constraints & vocabulary, all replacement paths including `rowid`/`_rowid_`/`oid` across `INSERT OR REPLACE`/`REPLACE INTO`/`INSERT OR IGNORE`/upsert, G14 8-field audit completeness, isolated Revision-5 rowid regression proof).
7. **N7** `docs/contracts/DATA_DICTIONARY.md` — append-only §2.22 schema/index/trigger/downgrade documentation.
8. **N8** `docs/contracts/TOOL_CONTRACTS.md` — append-only P4-RB3 internal durable persistence boundary documentation.
9. **N9** `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` — append-only P4-RB3 non-graph persistence & sealing documentation.
10. **N10** `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md` — this implementation review report.
11. **N11** `docs/phase-reports/PHASE_4_REPORT.md` — append-only §35 implementation checkpoint.
12. **N12** `docs/roadmap/PHASE_PROGRESS.md` — append-only P4-RB3 implementation checkpoint.
13. **N13** `docs/clinical-safety/DEMO_REVIEW_RULES.md` — append-only §14 conservative DR-006 denial & A2 transport-label disclosure.

### Untouched boundaries

- `backend/app/db/session.py`, `backend/app/services/p4_rb2_offline_rules.py`, `backend/app/services/p5_run_gate.py` (E6), and `docs/phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md` were **not modified**.
- Zero new HTTP routes, zero LangGraph/agent/LLM/task/notification surfaces, zero frontend source edits.
- All six E1–E6 legacy-guard/docstring targets remain **untouched** pending separate owner authorization markers.

## 2. Observed local verification results

Executed in the sandbox on Linux Python `3.11.2` using an isolated virtual environment (`/tmp/rb3-venv`) installed from `requirements/requirements-dev.lock` and Node `v22.22.3` (`frontend/node_modules`). **Local Linux Python 3.11.2 results are implementation evidence only and do not substitute for GitHub Actions Python 3.12 CI or owner Windows PowerShell 5.1 verification.**

| Check | Command | Observed Result |
|---|---|---|
| RB3 targeted pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -vv backend/tests/p4/test_p4_rb3_review_persistence.py backend/tests/p4/test_p4_rb3_migration_guards.py` | **20 passed** (`13` service + `7` migration guards) |
| Safety guards | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -vv backend/tests/test_safety_guards.py` | **9 passed** (no forbidden imports, no clinical/notification vocabulary, allowlisted routes only) |
| Ruff lint & format | `/tmp/rb3-venv/bin/ruff check . && /tmp/rb3-venv/bin/ruff format --check .` | **PASS** (`145 files already formatted`) |
| OpenAPI contract check | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/check_openapi.py` | **PASS** (`17 paths / 18 operations, 43 schemas`) |
| Secret/artefact/claim scan | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/scan_repository.py` | **PASS** (tracked files scanned; 0 findings) |
| Frontend suite | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` | **PASS** (ESLint, `tsc --noEmit`, `13` Vitest tests, Vite production build) |
| Collection counts | `pytest --collect-only backend/tests` & `backend/tests/p3` | **1277 collected**, of which **443** are the P3 suite |
| Full backend pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -q` | **1270 passed, 7 failed** (every failure is an untouched E1–E5 legacy guard — see §3) |

## 3. Exact E1–E5 legacy guard failures and E6 status (untouched pending owner markers)

No E1–E6 file was modified in this branch because the ratified Revision-6 scope requires a separate standalone owner exception marker for each before editing:

1. **E1 — `backend/tests/test_database.py` (2 failures):**
   - `test_migration_creates_baseline_table`: expected `HEAD_REVISION == '0007_p5_run_gate'`, observed `'0008_p4_rb3_review_persistence'`.
   - `test_migrated_schema_is_exactly_p1_plus_p2_plus_p3`: observed extra tables `{'review_item', 'evidence_link', 'review_evaluation'}` in migrated head.
   - *Required delta:* update `HEAD_REVISION` to `"0008_p4_rb3_review_persistence"`, add `P4_RB3_TABLES = {"review_item", "evidence_link", "review_evaluation"}` to the head set, and remove `review_item` from `FUTURE_TABLES` (keeping non-authorized future P4/P5 tables forbidden).
   - *Proposed standalone marker:* `APPROVE-P4-RB3-E1-TEST-DATABASE-UPDATE`
2. **E2 — `backend/tests/p2/test_p2_migration.py` (2 failures):**
   - `test_full_round_trip_to_base_and_back` and `test_p1_to_head_to_p1_to_head_is_stable`: observed extra tables `{'review_item', 'evidence_link', 'review_evaluation'}` at head (`test_migration_matches_the_orm_metadata` already passes).
   - *Required delta:* add `P4_RB3_TABLES` to expected head tables while keeping `0001`–`0007` historical assertions intact.
   - *Proposed standalone marker:* `APPROVE-P4-RB3-E2-P2-MIGRATION-UPDATE`
3. **E3 — `backend/tests/p2/test_p2_scope_guards.py` (1 failure):**
   - `test_p2_tables_still_exist_and_no_later_phase_table_appears`: observed `review_item`, `evidence_link`, `review_evaluation` in `Base.metadata.tables`.
   - *Required delta:* update allowed head table set to include `P4_RB3_TABLES` and remove `review_item`/`evidence_link` from `P4_PLUS_TABLES` (while keeping `task`, `notification`, `summary_draft`, etc. forbidden).
   - *Proposed standalone marker:* `APPROVE-P4-RB3-E3-P2-SCOPE-GUARDS-UPDATE`
4. **E4 — `scripts/python/check_alembic_smoke.py` (1 failure via `backend/tests/p5/test_p5_run_gate.py::test_alembic_smoke_retains_all_historical_states`):**
   - Observed `unexpected tables for state 'head': ['evidence_link', 'review_evaluation', 'review_item']` and `expected alembic_version ['0007_p5_run_gate'], found ['0008_p4_rb3_review_persistence']`.
   - *Required delta:* update `HEAD_REVISION` to `"0008_p4_rb3_review_persistence"`, retain `--state p5_f1` for `0007` and prior states unchanged, and add RB3 `head` structural assertions (`P4_RB3_TABLES`, `WITHOUT ROWID` in `sqlite_master.sql`, all 25 RB3 trigger names scoped to the 3 RB3 tables, and all 11 historical triggers intact).
   - *Proposed standalone marker:* `APPROVE-P4-RB3-E4-ALEMBIC-SMOKE-UPDATE`
5. **E5 — `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (1 failure via `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes`):**
   - Observed `AssertionError` requiring exact measured pairing `**1277 collected**, of which **443** are the P3 suite` (collection count only, never tests passed; historical 1255/443 and OCR/Windows entries preserved).
   - *Required delta:* append-only collection pairing line recording `**1277 collected**, of which **443** are the P3 suite` with explicit non-pass wording.
   - *Proposed standalone marker:* `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`
6. **E6 — `backend/app/services/p5_run_gate.py` (docstring-only, currently passing):**
   - `inspect_current_run_gate_locked` docstring currently names `build_run_evaluable_review_evidence` as sole caller; RB3 calls it read-only under `BEGIN IMMEDIATE` in T5/T17. Zero logic change required; append-only contract note in N8 already documents the RB3 caller boundary, and a docstring note in `p5_run_gate.py` can be added if authorized.
   - *Proposed standalone marker (optional docstring-only):* `APPROVE-P4-RB3-E6-GATE-DOCSTRING-ONLY`

## 4. Non-claims and acceptance gates

- **Synthetic / educational scope only — NOT FOR CLINICAL USE.**
- **P4 remains `IN_REVIEW`**, issue #14 remains **OPEN**, full P5 remains **NOT ACCEPTED**, and original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**.
- Acceptance of RB3 implementation additionally requires owner authorization markers for E1–E5 (and optional E6), green Python 3.12 GitHub Actions CI on the final PR head, and independent owner Windows PowerShell 5.1 verification (`setup.ps1` + `test_all.ps1`).
