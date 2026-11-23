# P4-RB3 Durable Review Persistence Implementation — Review Candidate (2026-11-23)

**Status: IN_REVIEW / NOT ACCEPTED / DRAFT PR PENDING.** Repository: `Muhammed-Fathi/AI-Doctor-FollowUp-Agent`. Base `main@6d121228a9e4a1c0571c513d158c2cb887b1486` (post-PR #42 merge; CI `#45141004060` `success`). Ratified Revision-6 design: `docs/phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md` (git blob `9b9160b329afa7b41baa971eb9c2558f2c6e073e`, SHA-256 `3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`, owner marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` at [PR #42 comment #7095039109](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/42#issuecomment-7095039109)). P4 issue #14 remains OPEN.

## 1. Authorized N1–N13 paths delivered

Only the 13 paths specified in the ratified design allowlist (`N1`–`N13`) were created or updated:

1. **N1** `backend/app/services/p4_rb3_review_persistence.py` — server-only `persist_run_review_items(db, *, principal, run_id, validation_clock, upload_root) -> ReviewPersistenceReceiptV1` implementing Phase 1 (`P1`–`P6`) and Phase 2 (`T1`–`T18`) inside `BEGIN IMMEDIATE`, F2/RB1 re-verification, independent stored-lineage proof (`proved_by_obs`), Alt A2 transport boundary over the unchanged RB2 evaluator, conservative DR-006 whole-invocation `409 E_VALIDATION` denial, `OverflowError`/pre-year-2 timestamp guard, 9-key bounded audit contract (`<= 500` chars), exact zero-write replay, and 8-reason deterministic conflict precedence.
2. **N2** `backend/app/schemas/p4_rb3_review_persistence.py` — frozen DTOs (`RB3DenialReason`, `PersistedEvidenceExclusionV1`, `LayeredEvidenceExclusionsV1`, `ReviewPersistenceReceiptV1`).
3. **N3** `backend/app/db/models.py` — additive `WITHOUT ROWID` (`{"sqlite_with_rowid": False}`) ORM models `ReviewItem`, `EvidenceLink`, `ReviewEvaluation` and `__all__` exports, preserving all pre-existing models unchanged.
4. **N4** `backend/migrations/versions/0008_p4_rb3_review_persistence.py` — Alembic revision `0008_p4_rb3_review_persistence` (`down_revision = "0007_p5_run_gate"`), creating the three `WITHOUT ROWID` tables, 9 indexes (`ux_review_dedupe`, `ux_review_order`, `ix_review_patient_state`, `ix_review_run`, `ix_evidence_owner`, `ux_evidence_link_observation`, `ux_evidence_link_span` inert, `ux_review_evaluation_run`, `ix_review_evaluation_patient`), 25 triggers (`G1`–`G25`) in `TRIGGER_CREATION_ORDER`, and non-empty downgrade refusal.
5. **N5** `backend/tests/p4/test_p4_rb3_review_persistence.py` — Round 1 (`414284de40f0cee23be85deebf1e5310aa0ff043`): 13 test functions; Round 2: expanded to **18** test functions (`13` core + `5` Round-2 `RB3-I01..I04` regression tests) covering `RB3-01..28`, `32..52`, `59..66`, `70..77`, `79`, `82..88`, `92..99`, `111..114`, `128` (with explicit boundary notes for unit-level `DR-006` in `RB3-66`/`RB3-99` and DB-CHECK + source-guard coverage for `RB3-12`).
6. **N6** `backend/tests/p4/test_p4_rb3_migration_guards.py` — 7 comprehensive migration/SQLite guard test functions covering `RB3-29..31`, `54..58`, `67..69`, `78..81`, `89..91`, `100..110`, `115..127` (populated downgrade refusal & empty roundtrip, ORM/migration parity & Alembic autogenerate blindness to `WITHOUT ROWID`, per-RB3-table 25 triggers + 11 historical triggers intact + `recursive_triggers=0`, CHECK constraints & vocabulary, all replacement paths including `rowid`/`_rowid_`/`oid` across `INSERT OR REPLACE`/`REPLACE INTO`/`INSERT OR IGNORE`/upsert, G14 8-field audit completeness, isolated Revision-5 rowid regression proof).
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

## 2. Historical Round-1 verification results (`414284de40f0cee23be85deebf1e5310aa0ff043`, superseded by Round 2 in §§5–8)

Executed in the sandbox on Linux Python `3.11.2` using an isolated virtual environment (`/tmp/rb3-venv`) installed from `requirements/requirements-dev.lock` and Node `v22.22.3` (`frontend/node_modules`). **Local Linux Python 3.11.2 results are implementation evidence only and do not substitute for GitHub Actions Python 3.12 CI or owner Windows PowerShell 5.1 verification.**

| Check | Command | Observed Result (Round 1) |
|---|---|---|
| RB3 targeted pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -vv backend/tests/p4/test_p4_rb3_review_persistence.py backend/tests/p4/test_p4_rb3_migration_guards.py` | **20 passed** (`13` service + `7` migration guards) |
| Safety guards | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -vv backend/tests/test_safety_guards.py` | **9 passed** (no forbidden imports, no clinical/notification vocabulary, allowlisted routes only) |
| Ruff lint & format | `/tmp/rb3-venv/bin/ruff check . && /tmp/rb3-venv/bin/ruff format --check .` | **PASS** (`145 files already formatted`) |
| OpenAPI contract check | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/check_openapi.py` | **PASS** (`17 paths / 18 operations, 43 schemas`) |
| Secret/artefact/claim scan | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/scan_repository.py` | **PASS** (tracked files scanned; 0 findings) |
| Frontend suite | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` | **PASS** (ESLint, `tsc --noEmit`, `13` Vitest tests, Vite production build) |
| Collection counts | `pytest --collect-only backend/tests` & `backend/tests/p3` | **1277 collected**, of which **443** are the P3 suite |
| Full backend pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -q` | **1270 passed, 7 failed** (every failure is an untouched E1–E5 legacy guard — see §3) |

## 3. Historical Round-1 E1–E5 legacy guard failures and E6 status (superseded for E5 collection count by §8)

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

---

## 5. Round-2 Implementation Review Remediation (`RB3-I01` through `RB3-I05`)

All five Round-2 blockers (`RB3-I01`–`RB3-I05`) identified against Round-1 commit `414284de40f0cee23be85deebf1e5310aa0ff043` on draft PR #43 (base `main@6d121228a9e4a1c0571c513d158c2cb887b1486`) were resolved inside the ratified Revision-6 architecture and the same 13 **N1–N13** paths with zero edits to F2, RB1, RB2, `monitoring.py`, `session.py`, or any E1–E6 path:

1. **`RB3-I01` — Transaction lifecycle, post-termination ORM access, and replay final freshness (`N1`, `N5`):**
   - `persist_run_review_items` (`backend/app/services/p4_rb3_review_persistence.py`) constructs and validates the frozen `ReviewPersistenceReceiptV1` **before** `db.rollback()` (exact zero-write replay) and **before** `db.commit()` (T18 first-completion commit). Zero ORM attributes are accessed after transaction termination.
   - Replay performs final in-transaction freshness verification (`inspect_current_run_gate_locked` + `_rehash_document_bytes`) immediately prior to `db.rollback()`.
   - Commit failures propagate directly (never swallowed into a success receipt), and dirty/active caller transactions (`db.in_transaction()` / pending `new`/`dirty`/`deleted` state) are rejected before `BEGIN IMMEDIATE`.
   - Verified in `test_rb3_i01_transaction_lifecycle_expire_on_commit_and_dirty_caller` using `get_session_factory(engine)` and `sessionmaker(expire_on_commit=True)` with SQLAlchemy `before_cursor_execute` event counting: zero SQL statements after transaction termination, `not db.in_transaction()`, every receipt field accessible post-termination, dirty-caller denial with zero writes, and commit-failure propagation with zero persisted rows.
2. **`RB3-I02` — Atomic rollback & genuine retry regression coverage (`N5`):**
   - `test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry` injects real failures at every flush stage (post-`ReviewItem` flush, post-`EvidenceLink` flush, post-`AuditEvent` flush, post-`ReviewEvaluation` flush, real `IntegrityError` via G10 cross-patient trigger, service-level cross-patient/run scope denial, `T17` source file byte change between Phase 1 and final freshness check, and `commit()` failure), compares complete table snapshots before/after each failure (proving zero partial rows across all 6 tables), and then executes a clean genuine retry (`RB3-64`) on the same `run_id` that succeeds cleanly.
3. **`RB3-I03` — Phase 1 + Phase 2 Decimal context isolation (`N1`, `N5`):**
   - `persist_run_review_items` wraps **both** Phase 1 (F2 `p5_evidence_bridge` + RB1 `p4_run_bound_preview`) and Phase 2 (`T1`–`T18`) inside `localcontext(_RB3_ARITHMETIC_CONTEXT)` via `_persist_run_review_items_pinned(...)` without modifying `p5_evidence_bridge.py`, `p4_run_bound_preview.py`, `p4_rb2_offline_rules.py`, or `monitoring.py`.
   - Verified in `test_rb3_i03_precision_dependent_decimal_context_phase1_and_phase2` with precision-sensitive fractional values (`100.1234` vs `100.1000` mg/dL) under hostile caller contexts (`prec=2`, `ROUND_DOWN`, and enabled traps) vs standard context: `bridge_input_fingerprint_sha256`, `input_fingerprint_sha256`, `output_identity_sha256`, and persisted items remain identical across caller contexts, and the caller's original `decimal.getcontext()` is restored identically on both success and denial.
4. **`RB3-I04` — All 8 replay conflicts, edge cases, §8.2 discrepancy documentation, and RB3-01..128 mapping (`N5`, `N10`):**
   - `test_rb3_i04_all_8_replay_conflicts_multi_conflict_precedence_and_nonempty_to_zero` proves all 8 replay conflict branches with zero writes (using isolated trigger-free SQLite copies for logically impossible sealed-table corruption without weakening production `G1`–`G25` triggers):
     1. `completion_evidence_missing` (case 12)
     2. `orphan_review_audit` (cases 11, 16)
     3. `extra_persisted_items` (case 13)
     4. `missing_persisted_evidence` (case 14)
     5. `input_fingerprint_changed` (case 4)
     6. `output_identity_changed` (cases 5, 8 zero->nonempty, 9 nonempty->zero, 10)
     7. `audit_business_inconsistent` (cases 15, 16)
     8. `audit_key_collision` (case 7)
   - Multi-conflict precedence tests verify `1 > 2`, `2 > 5`, `3 > 4`, `5 > 6`, `6 > 7`, `7 > 8`.
   - **Documented §8.2 design discrepancy (preserved without silent resolution):** in the ratified design's §8.2 prose, precedence 3 (`extra_persisted_items`) and precedence 4 (`missing_persisted_evidence`) describe item/link set mismatches without narrowing to matching `output_identity_sha256`, whereas §8.2 cases 5, 8 (zero-to-nonempty), and 9 (nonempty-to-zero) explicitly specify `output_identity_changed` (precedence 6) when persisted rows match the sealed `review_evaluation` counts (`item_count`, `evidence_link_count`) while recomputation under a changed rule/identity yields a different item set. Accordingly, `p4_rb3_review_persistence.py` evaluates precedence 3 (`extra_persisted_items`) and precedence 4 (`missing_persisted_evidence`) when persisted row/link sets diverge from the sealed `existing_eval` expectations (or when `existing_eval.output_identity_sha256 == output_identity_sha256`), preserving both sealed-corruption detection (cases 13–14) and cases 5, 8, 9 -> `output_identity_changed` (precedence 6) with fail-closed `409 E_IDEMPOTENCY_CONFLICT` and zero writes across every conflict branch.
   - `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` proves `RB3-12` (`patient.data_source` DB CHECK enforcement + T2 source-guard verification), `RB3-22` (prior terminal run isolation), `RB3-32` (`evidence_link` unique-per-observation & `review_item` unique dedupe), `RB3-47` (`Observation.created_at` mutation sensitivity), `RB3-49` (historical eligibility change via `validation` with zero column deletion), and `RB3-74` (missing `report_date` F1 vs F2 divergence asserted from actual accepted gate logic without assuming outcome).
5. **`RB3-I05` — Exact 9-index inventory, base SHA affirmation, and §2.22 corrections (`N7`, `N10`, `N11`, `N12`):**
   - Exact base reaffirmed: `main@6d121228a9e4a1c0571c513d158c2cb887b1486` (design SHA-256 `3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`).
   - Exact 9 migration-created indexes (`4 + 3 + 2 = 9`) verified in `0008_p4_rb3_review_persistence.py` and `models.py`, and corrected in `DATA_DICTIONARY.md` §2.22 and N10:
     - `review_item` (4): `ux_review_dedupe(workflow_run_id, dedupe_key)` UNIQUE, `ux_review_order(workflow_run_id, display_order)` UNIQUE, `ix_review_patient_state(patient_id, state)`, `ix_review_run(workflow_run_id)`.
     - `evidence_link` (3): `ix_evidence_owner(owner_type, owner_id)`, `ux_evidence_link_observation(owner_id, observation_id)` partial UNIQUE `WHERE kind = 'observation'`, `ux_evidence_link_span(owner_id, document_id, page_index, char_start, char_end)` partial UNIQUE `WHERE kind = 'document_span'` (inert).
     - `review_evaluation` (2): `ux_review_evaluation_run(workflow_run_id)` UNIQUE, `ix_review_evaluation_patient(patient_id, created_at)`.

## 6. Round-2 Observed Local Verification Results (Linux Python 3.11.2 sandbox)

| Check | Command | Observed Result (Round 2) |
|---|---|---|
| RB3 + safety targeted pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -q backend/tests/p4/test_p4_rb3_review_persistence.py backend/tests/p4/test_p4_rb3_migration_guards.py backend/tests/test_safety_guards.py` | **34 passed** (`18` RB3 service + `7` RB3 migration guards + `9` safety guards) |
| RB3 targeted pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -vv backend/tests/p4/test_p4_rb3_review_persistence.py backend/tests/p4/test_p4_rb3_migration_guards.py` | **25 passed** (`18` service + `7` migration guards) |
| Ruff lint & format | `/tmp/rb3-venv/bin/ruff check . && /tmp/rb3-venv/bin/ruff format --check .` | **PASS** (`145 files already formatted`) |
| OpenAPI contract check | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/check_openapi.py` | **PASS** (`17 paths / 18 operations, 43 schemas`) |
| Secret/artefact/claim scan | `PYTHONPATH=backend /tmp/rb3-venv/bin/python scripts/python/scan_repository.py` | **PASS** (`294` tracked files scanned; 0 findings) |
| Collection counts | `pytest --collect-only` & `pytest --collect-only backend/tests/p3` | **1282 collected**, of which **443** are the P3 suite |
| Full backend pytest | `PYTHONPATH=backend /tmp/rb3-venv/bin/python -m pytest -q --tb=no` | **1275 passed, 7 failed** out of **1282 collected** (all 7 failures are strictly the untouched E1–E5 legacy expectations; see §8) |

## 7. Requirement-to-Test Evidence Mapping (`RB3-01`..`RB3-128`)

Every case of the design §11 matrix (`RB3-01`..`RB3-128`) is mapped below with its exact verification class: **Executed / Passing** (runtime test in `test_p4_rb3_review_persistence.py` or `test_p4_rb3_migration_guards.py`), **Executed Unit Boundary Only** (no end-to-end DR-006 reachability claimed), **DB CHECK + Source Guard** (`RB3-12`), or **Structural / Diff-Verified** (`RB3-41`, `RB3-42`, `RB3-65`, `RB3-126`).

| Requirement IDs | Verification Class | Exact Evidence (`test_p4_rb3_review_persistence.py` / `test_p4_rb3_migration_guards.py`) |
|---|---|---|
| `RB3-01`, `RB3-23`, `RB3-44` | Executed / Passing | `test_rb3_01_23_44_happy_path_replay_and_honesty_receipt`, `test_rb3_i01_transaction_lifecycle_expire_on_commit_and_dirty_caller` |
| `RB3-02`..`RB3-06` | Executed / Passing | `test_rb3_02_to_06_gate_and_lock_failures_write_nothing`, `test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry` |
| `RB3-07`..`RB3-11`, `RB3-13`..`RB3-18` | Executed / Passing | `test_rb3_07_to_18_authority_session_scope_run_and_byte_tampering`, `test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry` (`T17` byte tampering + `403` scope) |
| `RB3-12` | DB CHECK + Source Guard | `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` (runtime `ck_patient_synthetic_data_only` `IntegrityError` + T2 `patient.data_source != "synthetic_fixture"` guard assertion) |
| `RB3-19`, `RB3-71`, `RB3-96` | Executed / Passing | `test_rb3_19_71_96_empty_selection_complete_t8a_path` |
| `RB3-20` | Executed / Passing | `test_rb3_20_input_caps_fail_closed` |
| `RB3-21`, `RB3-72`, `RB3-73`, `RB3-83`..`RB3-88` | Executed / Passing | `test_rb3_21_72_73_83_to_88_layered_exclusions_and_precedence` |
| `RB3-22` | Executed / Passing | `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` (prior `completed`/`failed`/`halted` run isolation) |
| `RB3-24` | Executed / Passing | `test_rb3_24_concurrent_invocation_single_winner_no_partial` |
| `RB3-25`..`RB3-28`, `RB3-64` | Executed / Passing | `test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry` (all flush stages, real `IntegrityError`, G10 trigger + scope denial, genuine retry) |
| `RB3-29`..`RB3-31`, `RB3-127` | Executed / Passing | `test_rb3_29_30_31_127_migration_populated_refusal_and_empty_roundtrip` |
| `RB3-32` | Executed / Passing | `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` (`ux_evidence_link_observation` + `ux_review_dedupe` duplicate rejection) |
| `RB3-33`..`RB3-40`, `RB3-94`, `RB3-95` | Executed / Passing | `test_rb3_33_to_40_r01_to_r08_and_rb3_94_95_decimal_and_range`, `test_rb3_i03_precision_dependent_decimal_context_phase1_and_phase2` |
| `RB3-41`..`RB3-43`, `RB3-82` | Executed / Passing + Structural | `test_rb3_41_to_43_82_no_http_surface_no_caller_authority_and_model_fields` + `test_safety_guards.py` + `check_openapi.py` |
| `RB3-45`..`RB3-53`, `RB3-93` | Executed / Passing | `test_rb3_45_to_52_93_input_identity_sensitivity_note_isolation_and_order`, `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` (`RB3-47`, `RB3-49`) |
| `RB3-54`..`RB3-57`, `RB3-67`, `RB3-68`, `RB3-78`..`RB3-81` | Executed / Passing | `test_rb3_54_to_57_67_68_78_79_80_81_checks_and_vocabulary`, `test_rb3_79_97_98_provenance_stored_lineage_proved_superseded_facts_and_exclusion_bounds` |
| `RB3-58`, `RB3-126` | Executed / Passing | `test_rb3_58_126_orm_migration_parity_and_autogenerate_blind_spot` |
| `RB3-59`..`RB3-63`, `RB3-65`, `RB3-70`, `RB3-92`, `RB3-111`..`RB3-114`, `RB3-128` | Executed / Passing | `test_rb3_59_to_65_70_92_111_to_114_128_replay_conflicts_and_audit_contract`, `test_rb3_i04_all_8_replay_conflicts_multi_conflict_precedence_and_nonempty_to_zero` (`RB3-65` source diff verifies untouched `p4_rb2_offline_rules.py` & `monitoring.py`) |
| `RB3-66`, `RB3-99` | Executed Unit Boundary Only | `test_rb3_66_99_dr006_unit_level_boundary_denies_whole_invocation` (explicitly tests unit-level evaluator boundary under conservative `T12` denial; **no** end-to-end DR-006 reachability claimed) |
| `RB3-69`, `RB3-89`, `RB3-90`, `RB3-100`..`RB3-108`, `RB3-118`, `RB3-121` | Executed / Passing | `test_rb3_69_89_90_100_to_108_118_121_replacement_and_rowid_closure` |
| `RB3-74` | Executed / Passing | `test_rb3_i04_remaining_matrix_items_12_22_32_47_49_74` (`report_date` missing F1/F2 divergence asserted from actual accepted gate decision) |
| `RB3-75`..`RB3-77`, `RB3-97`, `RB3-98` | Executed / Passing | `test_rb3_79_97_98_provenance_stored_lineage_proved_superseded_facts_and_exclusion_bounds` |
| `RB3-91`, `RB3-115`..`RB3-117` | Executed / Passing | `test_rb3_91_115_116_117_g14_audit_completeness` |
| `RB3-109`, `RB3-120` | Executed / Passing | `test_rb3_109_120_isolated_guard_regression_proves` |
| `RB3-110`, `RB3-119`, `RB3-122`..`RB3-125` | Executed / Passing | `test_rb3_110_119_122_123_124_125_without_rowid_inventory_and_pragmas` |

## 8. Updated Standalone Owner Exception Requests (E1–E6, current exact counts)

All six E1–E6 targets remain **untouched** on this branch. Exact failing count in full pytest remains **7**, exclusively across E1–E5, with the updated collection count **1282 collected** (**443** P3) for E5:

1. **E1 (`backend/tests/test_database.py` — 2 failures):** `APPROVE-P4-RB3-E1-TEST-DATABASE-UPDATE` — update `HEAD_REVISION` to `"0008_p4_rb3_review_persistence"`, add `P4_RB3_TABLES = {"review_item", "evidence_link", "review_evaluation"}`, remove `review_item` from `FUTURE_TABLES`.
2. **E2 (`backend/tests/p2/test_p2_migration.py` — 2 failures):** `APPROVE-P4-RB3-E2-P2-MIGRATION-UPDATE` — include `P4_RB3_TABLES` in expected head tables while keeping `0001`–`0007` assertions unchanged.
3. **E3 (`backend/tests/p2/test_p2_scope_guards.py` — 1 failure):** `APPROVE-P4-RB3-E3-P2-SCOPE-GUARDS-UPDATE` — include `P4_RB3_TABLES` in allowed head tables and remove `review_item`/`evidence_link` from `P4_PLUS_TABLES` (leaving future `task`/`notification`/`summary_draft`/etc. forbidden).
4. **E4 (`scripts/python/check_alembic_smoke.py` — 1 failure via `test_alembic_smoke_retains_all_historical_states`):** `APPROVE-P4-RB3-E4-ALEMBIC-SMOKE-UPDATE` — update `HEAD_REVISION` to `"0008_p4_rb3_review_persistence"`, keep `--state p5_f1` and earlier states unchanged, assert `P4_RB3_TABLES`, `WITHOUT ROWID`, 25 RB3 triggers, and 11 historical triggers.
5. **E5 (`docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — 1 failure via `test_handoff_test_count_matches_the_suite_it_describes`):** `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY` — append collection-only line recording **`**1282 collected**, of which **443** are the P3 suite`** with explicit non-pass wording, keeping historical 1255/443 and real-OCR evidence untouched.
6. **E6 (`backend/app/services/p5_run_gate.py` — optional docstring-only, currently passing):** `APPROVE-P4-RB3-E6-GATE-DOCSTRING-ONLY` — optional docstring update on `inspect_current_run_gate_locked` noting read-only RB3 caller alongside `build_run_evaluable_review_evidence` (zero logic change; N8 contract note already covers this if omitted).

- **P4 remains `IN_REVIEW`**, issue #14 remains **OPEN**, full P5 remains **NOT ACCEPTED**, original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**, and PR #43 remains **OPEN / DRAFT / NOT MERGED**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**
