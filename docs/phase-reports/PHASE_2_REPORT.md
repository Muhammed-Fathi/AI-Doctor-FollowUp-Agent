# Phase 2 Report — Patient Data Domain & Role-Based API

**Status: IN REVIEW.** Not accepted, not merged, **not PASS**. No owner checkbox is
ticked by the implementer. Acceptance, merge and any PASS marking are the owner's.

| Item | Value |
|---|---|
| Phase | P2 — patient data domain & role-based API |
| Approved baseline | `main` @ `d1ec0b9b481dca313c8ea2f21f97872582fc5a86` (P0 PASS, P1 PASS) |
| Branch | `arena/a8844cc2-ai-doctor-followup-agent` |
| Pull request | [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) — **draft**, base `main` |
| Commits | implementation `4f661de`, `58b60f8`, `69f12ae`; documentation `b079090`, `7b0b822`, `dbaf938` and the 2026-11-14 documentation-synchronization commit (§14). The exact branch head is the PR #7 head |
| Scope authorization | [owner comment 6881832444](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6881832444) — recorded verbatim in `docs/roadmap/PHASE_PROGRESS.md` |
| Authorized exceptions | A1–A3, B1–B2, C1–C2, D1–D2, E1–E2, F1–F2, G1–G3, H1–H3 (19 physical paths) |
| Executed here | Debian 12 sandbox, **Python 3.11.2** |
| CI | run [`43625331149`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625331149) at `dbaf938` and run [`43625989736`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625989736) at `6d54ede` — 3.12 **SUCCESS**, Node 22 **SUCCESS** in both (reviewer-verified, §9.2) |
| Owner Windows gate | **PASS — executed 2026-11-14** on an isolated worktree (PowerShell 5.1, Python 3.12.9); PBKDF2 measured on Windows (§10.11) |

> **This report distinguishes three evidence sources and never mixes them:**
> sandbox Python 3.11 execution by the implementer (this file's numbers), the
> GitHub Actions 3.12 + Node 22 run verified independently by the reviewer (§9.2;
> the implementer's own read was 403 / NOT OBSERVED, §9.1), and owner-side Windows
> verification, **executed by the owner on 2026-11-14 and PASS** (§10.11; the
> checklist that produced it is §10, and its earlier PENDING state is kept below as
> historical provenance).

---

## 1. Scope delivered

| Requirement (Issue #6) | Delivered |
|---|---|
| §3.1 synthetic users, assignments, encounter/observation models, reversible migration | `user`, `patient`, `encounter`, `observation`, `session`, `audit_event`, `checkin_idempotency`; revision `0002_p2_patient_domain` with working `downgrade()` |
| §3.2 server-side RBAC, no registration, never trust a client `patient_id` | `core/policies.py` + route-level role gate + service-level scope checks; the request models forbid extra fields, so `patient_id`/`trust_level`/`verification` in a body is a `400` |
| §3.3 login/me/logout, bearer, expiry, revocation, uniform failures, bounded attempts | `POST /api/v1/auth/login`, `GET /me`, `POST /logout` (204); SHA-256-hashed opaque tokens; `429 E_RATE_LIMITED` after 5 failures |
| §3.4 endpoint catalogue | 9 P2 paths / 10 operations (§3 below), asserted by an exact allowlist gate |
| §3.5 unit allowlist, UTC, positive finite, bounded note, `self_reported_validated`, no client `verified_by`, `Idempotency-Key` + conflict, injected clock | `services/checkins.py`; `E_UNIT_NOT_ALLOWED`, `E_IDEMPOTENCY_CONFLICT`, `E_DUPLICATE_CHECKIN` |
| §3.6 scoped timeline/observations, stable order, pagination, exclude `rejected` | `services/patients.py` + `services/pagination.py` (cursor, newest-first, `rejected` filtered) |
| §3.7 append-only `access.denied` | `services/audit.py` (single writer, deterministic idempotency key, idempotent append) |
| §3.8 deterministic seed/reset (`demo_admin` + `DEMO_MODE=true`, refuse when a run is active) | `services/seed.py`, `services/demo.py`, `POST /api/v1/demo/reset`, plus the `python -m app.services.seed` bootstrap |
| §3.9 preserve P1 | P1 routes, schemas, migrations, PowerShell scripts, CI untouched except the three gate files authorized as G1–G3 |

**Not delivered, by design:** `GET /api/v1/demo/status` (`OQ-P2-01`, deferred to P5),
`POST /api/v1/demo/seed` (does not exist in any phase), and any P3+ capability
(documents, OCR, facts, workflow, review items, tasks, notifications).

---

## 2. Changed files

28 files in `69f12ae` (all inside the authorized scope), on top of 40 files from
`4f661de`/`58b60f8` (all inside `AGENTS.md` §5):

**New routes / assembly (A, B, C, D)**
`backend/app/api/v1/__init__.py`, `backend/app/api/v1/router.py`,
`backend/app/api/v1/doctor/{__init__,patients}.py`,
`backend/app/api/v1/patient/{__init__,checkins}.py`,
`backend/app/api/v1/demo/{__init__,router}.py`

**Modified for mounting (A1)**
`backend/app/main.py` — problem handlers installed, v1 router included,
`bearerAuth` completed to the contract (`bearerFormat`, global `security`),
`x-design-status` → `P2_PATIENT_DOMAIN`

**Migration (E)**
`backend/migrations/versions/0002_p2_patient_domain.py` (new),
`backend/migrations/env.py`

**Gates (F)**
`scripts/python/check_openapi.py`, `scripts/python/check_alembic_smoke.py`

**P1 tests updated to the allowlist (G)**
`backend/tests/test_openapi.py`, `backend/tests/test_safety_guards.py`,
`backend/tests/test_database.py`

**Allowlisted application changes required by the review**
`backend/app/api/v1/auth/dependencies.py` (`bearer_scheme`),
`backend/app/api/v1/auth/router.py` (security declaration on `me`/`logout`),
`backend/app/db/models.py` (partial unique check-in identity index),
`backend/app/services/accounts.py` (`needs_rehash` wired into login),
`backend/app/services/checkins.py` (write-collision recovery)

**Tests (allowlisted)**
`backend/tests/p2/conftest.py`, `test_p2_accounts.py`, `test_p2_auth_http.py`,
`test_p2_checkins.py`, **new** `test_p2_http_routes.py`, **new**
`test_p2_migration.py`

**Config (H1)**
`.env.example`

---

## 3. API surface (exactly 11 paths / 12 operations)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | public | P1, unchanged |
| GET | `/version` | public | P1, unchanged |
| POST | `/api/v1/auth/login` | public | rate limited, uniform 401 |
| GET | `/api/v1/auth/me` | bearer | identity + own `patient_id` |
| POST | `/api/v1/auth/logout` | bearer | `204`, revokes the session |
| GET | `/api/v1/doctor/patients` | bearer (doctor) | assignment-scoped |
| GET | `/api/v1/doctor/patients/{patient_id}` | bearer (doctor) | header/counts only |
| GET | `/api/v1/doctor/patients/{patient_id}/timeline` | bearer (doctor) | `documents`/`review_items`/`tasks` empty |
| GET | `/api/v1/doctor/patients/{patient_id}/observations` | bearer (doctor) | `measure_type`, `from`, `to`, `limit`, `cursor` |
| POST | `/api/v1/patient/check-ins` | bearer (patient) | `Idempotency-Key`; `Idempotent-Replay: true` on replay |
| GET | `/api/v1/patient/check-ins` | bearer (patient) | self-scoped, newest-first |
| POST | `/api/v1/demo/reset` | bearer (demo_admin) + `DEMO_MODE` | keeps the audit trail |

Absent on purpose: `GET /api/v1/demo/status` (`OQ-P2-01`), `POST /api/v1/demo/seed`
(never existed), every P3+ route.

---

## 4. Requirement → test mapping (executed)

Counts are per file, from `pytest --collect-only`. "Service" = direct call with a
real SQLite database and a frozen clock; "HTTP" = through the production ASGI app.

| Matrix row / requirement | Expected | Tests |
|---|---|---|
| **AUTH-01** salted seeded hashing, no plaintext anywhere | hash prefix differs per user, no password in DB/response/log | `test_p2_security_primitives.py` (17, incl. work factor ≥ 600 000, legacy-hash compatibility, cost bound), `test_p2_accounts.py::{test_login_issues_a_hashed_session_and_audits_it,test_no_password_or_token_appears_in_stored_rows,test_audit_rows_never_contain_the_submitted_password}`, `test_p2_seed_reset.py::{test_every_account_has_a_distinct_salted_hash,test_no_stored_value_contains_the_demo_password,test_fixtures_contain_no_credentials}`, `test_p2_bootstrap.py::test_bootstrap_seeds_and_never_prints_the_password` |
| **AUTH-02** expiry/revocation | expired/revoked token unusable | `test_p2_accounts.py::{test_expired_session_is_rejected,test_revoked_session_is_rejected,test_revocation_is_idempotent}`, `test_p2_auth_http.py::test_logout_revokes_the_session` |
| **NEG-10** unauthenticated **and expired-token** requests → 401, uniform, no existence leak | 401 | `test_p2_auth_http.py::{test_missing_token_returns_the_problem_envelope,test_unknown_and_expired_tokens_are_indistinguishable,test_non_bearer_scheme_is_rejected}`, `test_p2_http_routes.py::test_protected_get_routes_require_a_token` (6 paths), `::test_protected_post_routes_require_a_token`, `test_p2_accounts.py::test_unknown_expired_and_unknown_username_share_one_failure_shape` |
| **NEG-02** doctor asks for an unassigned patient's timeline → 403/404, no partial data | service + HTTP | `test_p2_patients.py::{test_unassigned_doctor_is_denied_and_audited,test_unassigned_doctor_sees_no_patients,test_unknown_patient_is_not_found}`, `test_p2_policies.py::test_unassigned_doctor_is_a_scope_violation`, `test_p2_http_routes.py::{test_unassigned_doctor_is_denied_with_the_problem_envelope,test_unassigned_doctor_gets_an_empty_page_not_someone_elses_patients,test_unknown_and_malformed_patient_ids_are_distinguished}` |
| **REQ-SEC-01** cross-scope denial + audit | 403 `E_SCOPE_VIOLATION`, audit row, no content | `test_p2_patients.py::{test_a_doctor_assigned_elsewhere_cannot_read_this_patient,test_denial_audit_key_is_deterministic}`, `test_p2_policies.py::{test_patient_self_scope_accepts_only_its_own_patient_id,test_the_self_scope_comes_from_the_server_not_the_caller,test_doctor_cannot_use_a_patient_capability,test_patient_cannot_use_a_doctor_capability}`, `test_p2_http_routes.py::{test_patient_role_cannot_use_the_doctor_surface,test_doctor_cannot_post_a_check_in,test_check_ins_are_self_scoped}`, `test_p2_checkins.py::{test_patient_lists_only_own_check_ins,test_idempotency_rows_are_scoped_per_patient}` |
| **NEG-13** check-in with `mmol/L` glucose → `400 E_UNIT_NOT_ALLOWED` | service + HTTP | `test_p2_checkins.py::{test_glucose_in_mmol_per_litre_is_rejected,test_every_measurement_enforces_its_own_unit}`, `test_p2_http_routes.py::test_glucose_in_mmol_per_litre_is_refused_over_http` |
| **NEG-01** *another patient's document extraction* | **NOT APPLICABLE in P2** — documents are P3; the page says so, and this report does not claim it. The scope-denial mechanics are covered under `REQ-SEC-01`/`NEG-02` | — |
| **AUD-01** access events carry actor/time/context, never content or secrets | append-only, bounded `safe_detail` | `test_p2_patients.py::test_unassigned_doctor_is_denied_and_audited`, `test_p2_checkins.py::test_check_in_audit_row_is_recorded`, `test_p2_scope_guards.py::test_api_models_never_expose_credential_material` |
| **REQ-AUTH-01/03** bearer only, bounded attempts | 429 after budget | `test_p2_security_primitives.py` (limiter), `test_p2_accounts.py::test_repeated_failures_raise_rate_limited`, `test_p2_auth_http.py::test_rate_limited_login_returns_429` |
| **REQ-DATA-01/02/04** stored fields, unit allowlist, derived provenance | as specified | `test_p2_checkins.py` (validation), `test_p2_http_routes.py::{test_patient_creates_and_reads_back_a_check_in,test_client_cannot_forge_provenance}` |
| **§1 idempotency** replay / conflict / duplicate / concurrency | same observation, `409`, one row | `test_p2_checkins.py::{test_exact_replay_returns_the_original_observation,test_same_key_with_a_different_body_conflicts,test_a_new_key_does_not_unlock_a_duplicate,test_identical_check_in_without_a_key_is_a_duplicate,test_replay_survives_a_new_session,test_two_writers_with_the_same_key_persist_exactly_one_check_in,test_two_writers_with_different_keys_cannot_store_one_measurement_twice}`, `test_p2_http_routes.py::{test_idempotency_key_replay_returns_the_same_observation,test_same_key_different_body_conflicts,test_duplicate_measurement_without_a_key_is_a_conflict}` |
| **§3.6** scoped timeline, ordering, pagination, `rejected` excluded | stable order | `test_p2_patients.py` (16), `test_p2_http_routes.py::{test_doctor_reads_the_timeline_and_observation_series,test_observation_filters_are_applied_server_side,test_invalid_measure_type_is_a_validation_problem}` |
| **US-12 / REQ-OPS-01** deterministic seed & reset | identical rows, audit preserved | `test_p2_seed_reset.py` (16), `test_p2_bootstrap.py` (11), `test_p2_http_routes.py::{test_demo_reset_succeeds_for_the_admin_and_keeps_the_audit_trail,test_demo_reset_requires_the_admin_role,test_demo_reset_is_refused_when_demo_mode_is_off}` |
| **§2.1–§2.3 referential integrity** | FK enforced, unique, RESTRICT | `test_p2_schema_integrity.py` (11), `test_p2_migration.py` (7) |
| **Scope discipline** (no P3+, no demo seed/status, no secrets, UTC-only, typed) | guards | `test_p2_scope_guards.py` (51) |
| **P1 preservation** | P1 assertions retained | `test_openapi.py`, `test_safety_guards.py`, `test_database.py` (G1–G3) |

---

## 5. Gates, and why they are stricter than before

**`check_openapi.py` (F1)** — asserts an exact set, not "at least":
`P1_PATHS ∪ P2_ALLOWED` = **11 paths**, per-path **method sets** (so
`/patient/check-ins` must carry exactly `GET`+`POST`), the **22-schema allowlist**
(no extra, no missing), per-operation `security` (only `/health`, `/version`,
`login` are public; everything else `[{"bearerAuth": []}]`), the `bearerAuth`
scheme with `bearerFormat: opaque-session-token`, the educational notice, and the
unchanged P1 `Health`/`VersionInfo`/`DependencyState` assertions.

**`check_alembic_smoke.py` (F2)** — `--state head|p1|base`:
`head` = revision `0002_p2_patient_domain` and exactly P1+7 tables, FK present,
partial index present, `PRAGMA foreign_key_check` empty on a
`foreign_keys=ON` connection; `p1` = revision `0001_p1_baseline`, exactly
`schema_meta`+`alembic_version` (this is the *only* way to test P1 retention —
`downgrade base` also drops `schema_meta`); `base` = only `alembic_version`, the
documented empty state. Later-phase tables are rejected in every state.

**P1 tests (G1–G3)** keep their equality semantics with the explicit P2 allowlist
added; no assertion was relaxed to a superset.

---

## 6. Review corrections (mentor review 5906194976)

| # | Finding | Correction |
|---|---|---|
| 1 | Path count: 9 unique P2 paths / 10 operations; 11 paths total | Confirmed and implemented exactly; the gate asserts **methods per path** as well as paths, and the report says 11 paths / 12 operations |
| 2 | Alembic downgrade semantics | `--state p1` tests `0002->0001` (P1 retained) and `--state base` tests `0002->base` (documented empty state) as **separate** checks; `test_p2_migration.py` also runs `0001->0002->0001->0002` |
| 3 | Concurrency must be real, not a manual insert | Two threaded two-writer tests (same key → replay; different keys → `409`) driving `create_check_in` through separate connections. **They fail if the recovery path is removed** (verified by reverting it). The database also enforces check-in identity through the partial unique index, so service-level checks are not the only guarantee |
| 4 | `needs_rehash` claim | Now wired into `accounts.authenticate` *after* successful verification, with tests for both branches (upgrade on success, unchanged on failure) |
| 5 | Traceability | `NEG-01` is marked **NOT APPLICABLE in P2** (P3 documents); cross-scope tests are filed under `REQ-SEC-01`/`NEG-02`; `NEG-13` is the unit mismatch only, idempotency is labelled §1 |
| 6 | Migration FK safety | `env.py` disables `foreign_keys` **only on the migration engine**; a test asserts the runtime engine still reports `ON`, that orphans are rejected **on the migrated schema**, and that `PRAGMA foreign_key_check` is empty after every transition |
| 7 | Docs/scope | Owner authorization recorded verbatim in `docs/roadmap/PHASE_PROGRESS.md`; no `/demo/seed`, no `/demo/status`, no P3+, no new dependencies, no contract change; status stays IN REVIEW / draft |

### A real defect found while fixing finding 3

The first implementation wrapped the inserts in `Session.begin_nested()`. On
SQLite a `SAVEPOINT` issued outside a DBAPI transaction **starts** one and its
`RELEASE` **commits** it, so the observation was published before the request
committed, and the collision could never be observed (the second writer simply
saw the row). The savepoint was removed; the service now flushes plainly, catches
`IntegrityError`, rolls the transaction back and answers from the winner's rows.
The two-writer tests are what exposed this.

---

## 7. Commands executed here (real output, Python 3.11.2 sandbox)

```
$ PYTHONPATH=backend APP_ENV=test pytest backend/tests/p2
230 passed in 31.65s

$ PYTHONPATH=backend APP_ENV=test pytest backend/tests
355 passed in 33.09s          # 125 P1 + 230 P2

$ ruff check .                → All checks passed!
$ ruff format --check .       → 69 files already formatted

$ PYTHONPATH=backend python scripts/python/check_openapi.py
OpenAPI contract check: PASS (11 paths / 12 operations, 22 schemas)

$ PYTHONPATH=backend python scripts/python/scan_repository.py
Secret/artefact scan: PASS (143 tracked files; 7 secret patterns, 4 claim patterns)
```

Migration sequence (fresh SQLite each time, `-x database_url=...`):

```
$ alembic upgrade head           → 0001_p1_baseline → 0002_p2_patient_domain
$ check_alembic_smoke.py db            → PASS (state head, revision 0002_p2_patient_domain, 9 tables)
$ alembic downgrade 0001_p1_baseline
$ check_alembic_smoke.py db --state p1 → PASS (state p1, revision 0001_p1_baseline, schema_meta + alembic_version)
$ alembic downgrade base
$ check_alembic_smoke.py db --state base → PASS (state base, revision none, alembic_version)
$ alembic upgrade head
$ check_alembic_smoke.py db            → PASS (state head, ...)
```

Runtime schema evidence from the migrated database:

```
tables: ['alembic_version','audit_event','checkin_idempotency','encounter',
         'observation','patient','schema_meta','session','user']
user FKs: [(0,0,'patient','patient_id','id','NO ACTION','RESTRICT','NONE')]
index:    CREATE UNIQUE INDEX uq_observation_checkin_identity ON observation
          (patient_id, measure_type, measured_at, value, unit)
          WHERE source = 'patient_checkin'
PRAGMA foreign_key_check → []
```

Password hashing at the shipped work factor:

```
iterations=600000 hash=271ms verify=204ms (CPython 3.11.2, this sandbox)
```

---

## 8. PASS / FAIL / SKIP / NOT RUN ledger

| Check | Result |
|---|---|
| `pytest backend/tests` (356: 125 P1 + 231 P2) | **PASS** — the one intermittently flaky assertion was fixed and given a deterministic regression case (§11.15) |
| `ruff check` / `ruff format --check` | **PASS** |
| `check_openapi.py` (11 paths / 12 operations / 22 schemas) | **PASS** |
| `scan_repository.py` (secrets/artefacts) | **PASS** |
| `check_alembic_smoke.py` states `head`, `p1`, `base` | **PASS** |
| P2 HTTP lifecycle (auth, doctor, patient, demo) through the production app | **PASS** (29 tests) |
| Two-writer concurrency, both interleavings | **PASS** (and fail without the recovery path) |
| Migration round trip + ORM/metadata parity | **PASS** (7 tests) |
| GitHub Actions CI (Python 3.12 + frontend) | **VERIFIED SUCCESS by the independent reviewer** — run `43625331149` at `dbaf938` *and* run `43625989736` at docs-only HEAD `6d54ede`; both jobs SUCCESS in each (§9.2). The implementer's own read attempt was 403 / NOT OBSERVED (§9.1, historical) |
| Windows `scripts/powershell/test_all.ps1` | **PASS — executed by the owner 2026-11-14**: 12 PASS / 0 FAIL / 1 optional SKIP, exit 0 (§10.11). Historical state for this row was `NOT RUN` before owner execution |
| Windows PBKDF2 timing at 600 000 iterations | **MEASURED 2026-11-14 by the owner**: PBKDF2-HMAC-SHA256 600 000 iterations — hash **550.49 ms**, verify **537.67 ms**; wrong password rejected; `needs_rehash` passed (§10.11). The 3.11 sandbox figure in §7 is not a Windows measurement |
| Ollama / Tesseract / Playwright | **N/A** (P3+/optional) |
| `NEG-01` (document extraction) | **NOT APPLICABLE in P2** (P3) |
| `GET /api/v1/demo/status` | **DEFERRED to P5** (`OQ-P2-01`) |

---

## 9. Continuous integration

The 3.12 CI leg runs `ruff check`, `ruff format --check`, `pytest`,
`alembic upgrade → downgrade base → upgrade` + `check_alembic_smoke.py`, and
`check_openapi.py`.

CI evidence is recorded twice, from two different observers, and the two records
are never merged. The implementer could not read Actions/Checks; the independent
reviewer could and did.

### 9.1 Implementer observation at HEAD `dbaf938` — NOT OBSERVED (historical)

Kept as evidence of an **observer permission limitation**, not of a CI failure.

The automation credentials available to the implementing agent cannot read
Actions/Checks data, so no conclusion was claimed. Every attempt returned HTTP 403
`Resource not accessible by integration`:

```
$ gh run list --branch arena/a8844cc2-ai-doctor-followup-agent
failed to get runs: HTTP 403: Resource not accessible by integration
$ gh pr checks 7
GraphQL: Resource not accessible by integration (…statusCheckRollup…)
$ gh api repos/…/commits/<sha>/check-runs     → 403
$ gh api repos/…/commits/<sha>/status         → 403
$ gh api repos/…/actions/runs?per_page=2      → 403
```

The pushes themselves succeeded (`58b60f8..69f12ae..b079090`), but no CI result is
asserted from this side. **Resolved by §9.2.**

### 9.2 Reviewer verification addendum — 2026-11-14 — CI VERIFIED SUCCESS

Independently verified by the reviewer in mentor review
[5906286395](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#pullrequestreview-5906286395),
for the exact HEAD this report was handed back at
(`dbaf938ecb2e8abd39759f7856f083d2efe11cad`):

| Item | Result |
|---|---|
| Workflow run | [`43625331149`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625331149) — **COMPLETED / SUCCESS** |
| Backend — Python 3.12 | **SUCCESS** |
| Frontend — Node 22 | **SUCCESS** |
| Overall | **SUCCESS** |

Provenance, deliberately never collapsed into one line:

| Observer | CI evidence | Meaning |
|---|---|---|
| Implementer (agent) | `403 Resource not accessible by integration` — **NOT OBSERVED** | An observer permission restriction of the automation credentials, **not** a CI failure |
| Independent reviewer | run `43625331149` — **VERIFIED SUCCESS** | The 3.12 + Node 22 legs pass at `dbaf938` |
| Owner Windows gate | **PASS** — 2026-11-14, `test_all.ps1` 12 PASS / 0 FAIL / 1 optional SKIP, exit 0 (§10.11) | This row read `PENDING` when written; it is superseded by the owner run at `9fddb51` |

Because the reviewer resolved this matter, **no `OQ-P2-0x` was opened for it** — an
open question is not created for a resolved issue.

**Second verification, same reviewer, docs-only HEAD (supersedes the earlier caveat).**
Run [`43625989736`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625989736)
on HEAD `6d54edeb65b31c437537010329027f6ea33d0aa1` — the documentation commit whose
diff is exactly two Markdown files — is **COMPLETED / SUCCESS**, with Backend
Python 3.12 **SUCCESS** and Frontend Node 22 **SUCCESS**. That removes the earlier
caveat that post-`dbaf938` docs commits lacked CI confirmation. No CI question is
open.

| Run | HEAD | Backend 3.12 | Frontend Node 22 | Overall |
|---|---|---|---|---|
| [`43625331149`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625331149) | `dbaf938` (implementation) | SUCCESS | SUCCESS | SUCCESS |
| [`43625989736`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625989736) | `6d54ede` (docs-only) | SUCCESS | SUCCESS | SUCCESS |
| [`43626628577`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43626628577) | `9fddb51` (**owner-tested code snapshot**) | SUCCESS | SUCCESS | SUCCESS |
| [`43631967775`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43631967775) | `7a5a047` (docs-only ledger sync) | SUCCESS | SUCCESS | SUCCESS |

Any further documentation commit produced after this one is again docs-only; if
the owner wants CI confirmation for the final head, it is read on PR #7 → *Checks*
rather than assumed.

---

## 10. Windows verification checklist (owner) — PowerShell 5.1, Python 3.12, isolated worktree

Revision 2 (2026-11-14), correcting five checklist defects found in mentor review
`5906330237` **before** the owner ran anything. These were **checklist errors, not
application defects**; no code, migration, gate script or P1 file was changed to
fix them. **This checklist was subsequently executed by the owner and passed — the
results are in §10.11.** Changes from revision 1:

| # | Defect in revision 1 | Fix |
|---|---|---|
| 1 | `DEMO_SEED_PASSWORD` was cleared after bootstrap, so the running backend had `None` and `POST /demo/reset` would answer **500 E_INTERNAL** (`services/demo.py` refuses when the secret is absent) | §10.5 re-supplies the **same** password to the parent environment immediately before `start.ps1`, lets the backend inherit it at process start, then clears the parent shell |
| 2 | Admin reset ran before the doctor's denial check, but reset deletes every `session` row → the doctor token would answer **401**, not `403` | §10.8 tests the doctor's **403 E_FORBIDDEN first**, the admin's `200` last, then proves the old tokens are dead |
| 3 | `409 E_DUPLICATE_CHECKIN` was expected but never requested, and `201` was never asserted | §10.7 asserts the first `StatusCode = 201`, replays the same key, **then** submits the same measurement with a **new** key and asserts `409` + code |
| 4 | Absence of `/demo/seed` was probed with `GET`, while the forbidden route would be a `POST` | §10.8 probes **`POST /api/v1/demo/seed`** (and `GET /demo/status`) |
| 5 | `APP_VENV_DIR`, a pre-existing review folder, a dirty worktree and a missing `main` database were assumed rather than checked | §10.0 guards all four; §10.9 compares a captured hash **or** asserts continued non-existence; tokens/headers/password are cleared at the end |

**What must not be touched:** `main`, its `data/runtime/app.db` (existing **or**
absent), its `.env`, its `.venv`, and any path outside the authorized scope. The
checklist edits no repository file — only environment variables, the new worktree
and that worktree's own database are used.

### 10.0 Preparation and isolation guards (once per review)

```powershell
# PowerShell 5.1. Run from anywhere; nothing in the main checkout is modified.
$Main   = 'E:\DEPI\AI-Doctor-FollowUp-Agent'          # accepted main working copy
$Review = 'E:\DEPI\P2-Review'                          # must NOT exist yet
$Branch = 'arena/a8844cc2-ai-doctor-followup-agent'

# Guard 1: no inherited venv override, or setup.ps1 would install into main's venv.
if ($env:APP_VENV_DIR) {
    "APP_VENV_DIR was set to '$env:APP_VENV_DIR' - clearing it to keep the worktree isolated"
    Remove-Item Env:APP_VENV_DIR
}
if (Test-Path Env:APP_VENV_DIR) { throw 'APP_VENV_DIR still set - stop and report' }

# Guard 2: the review directory must not already exist.
if (Test-Path -LiteralPath $Review) { throw "$Review already exists - choose an empty path or remove it manually" }

# Guard 3: the main checkout must be clean and untouched.
git -C $Main status --porcelain        # must print nothing; otherwise stop and report
git -C $Main rev-parse HEAD            # record this: $MainHeadBefore
$MainHeadBefore = (git -C $Main rev-parse HEAD)

# Guard 4: main's database - handle BOTH states, remember which one applied.
$MainDb = Join-Path $Main 'data\runtime\app.db'
$MainDbExisted = Test-Path -LiteralPath $MainDb
if ($MainDbExisted) {
    $MainDbHashBefore = (Get-FileHash -LiteralPath $MainDb -Algorithm SHA256).Hash
    "main app.db EXISTS  hash=$MainDbHashBefore"
    Get-Item -LiteralPath $MainDb | Select-Object FullName, Length, LastWriteTime
} else {
    $MainDbHashBefore = $null
    'main app.db does NOT exist - it must still not exist at the end of 10.9'
}

# Create the isolated worktree at the exact reviewed commit.
git -C $Main fetch origin $Branch
$Head = (git -C $Main rev-parse "origin/$Branch")
$Head
git -C $Main worktree add $Review $Head
git -C $Review rev-parse HEAD          # must equal $Head
git -C $Review status --porcelain      # must print nothing
```

### 10.1 Install inside the worktree (own venv, own `.env`, own database)

```powershell
Set-Location $Review
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1

# The worktree must own its interpreter and its database.
$Python = Join-Path $Review '.venv\Scripts\python.exe'
& $Python -c "import sys; print(sys.version); print(sys.executable)"   # 3.12.x under $Review\.venv
Test-Path -LiteralPath (Join-Path $Review 'data\runtime\app.db')       # expected True (fresh)
```

If the reported interpreter is not `$Review\.venv\...`, stop: it means an
environment override leaked and the run is not isolated. If the Python version is
not 3.12, stop and report (the Windows gates are pinned to 3.12).

### 10.2 Full quality gate (backend + frontend + migration + OpenAPI + scan)

```powershell
Set-Location $Review
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1
"exit code: $LASTEXITCODE"
```

Expected: **PASS** for Ruff lint, Ruff format check, Backend pytest, Alembic
migration smoke (`upgrade head → downgrade base → upgrade head` on a throwaway
temporary database), OpenAPI surface check, Frontend typecheck/lint/tests/build,
Secret scan; exit code `0`. Playwright `SKIP` unless `-IncludeE2E`; a SKIP is not
a pass.

Two documented properties of this **unchanged** script (editing it was outside the
authorized scope):

- Its OpenAPI gate banner still reads `/health, /version only` from P1. That is a
  historical comment: the script invokes `check_openapi.py`, the P2 strict gate,
  whose own line reads `PASS (11 paths / 12 operations, 22 schemas)`. Judge the
  produced line, not the banner.
- It is where the `base` migration state is exercised, on a temporary database —
  which is why §10.3 keeps the worktree database at `head` (reviewer decision
  `5906330237`: no standalone owner `--state base` run is required).

### 10.3 Migration round trip on the worktree's own database (ends at `head`)

```powershell
Set-Location $Review
$Alembic = Join-Path $Review 'backend\migrations\alembic.ini'
$Python  = Join-Path $Review '.venv\Scripts\python.exe'
$DbPath  = Join-Path $Review 'data\runtime\app.db'
$Smoke   = Join-Path $Review 'scripts\python\check_alembic_smoke.py'

& $Python -m alembic -c $Alembic upgrade head
& $Python $Smoke $DbPath --state head

# P1 retention: 0002 -> 0001 must keep schema_meta, then return to head.
& $Python -m alembic -c $Alembic downgrade 0001_p1_baseline
& $Python $Smoke $DbPath --state p1
& $Python -m alembic -c $Alembic upgrade head
& $Python $Smoke $DbPath --state head
```

Expected: three `PASS` lines at revisions `0002_p2_patient_domain`,
`0001_p1_baseline`, `0002_p2_patient_domain`. **Do not** run `downgrade base`
against this database — it would drop the schema the smoke tests below need (and
it is already covered in §10.2 and by `test_p2_migration.py`).

### 10.4 Synthetic account bootstrap — the password is entered **once** here

The password is typed at the prompt (never in a command, never in `.env`, never in
a file, never printed). It is kept in the shell session as `$Plain` and re-used in
§10.5/§10.6 because `/demo/reset` and every login need the **same** secret that
`seed` hashed.

```powershell
Set-Location $Review
$env:PYTHONPATH = Join-Path $Review 'backend'
$env:DEMO_MODE  = 'true'

$secure = Read-Host -AsSecureString 'Local demo password (>= 12 chars, not reused anywhere)'
$bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$Plain  = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
Remove-Variable bstr, secure

$env:DEMO_SEED_PASSWORD = $Plain          # environment only; Settings prefers env over .env
& "$Review\.venv\Scripts\python.exe" -m app.services.seed
"seed exit code: $LASTEXITCODE"
Remove-Item Env:DEMO_SEED_PASSWORD        # the seed has finished with it
if (Test-Path Env:DEMO_SEED_PASSWORD) { 'FAIL: secret still in the environment' } else { 'OK: seed secret cleared' }
```

Expected: exit code `0`; counts of users/patients/encounters/observations; the
account list (`demo_admin`, `demo_doctor`, `demo_doctor_unassigned`,
`demo_patient_a|b|c`); the line `password: supplied via DEMO_SEED_PASSWORD (not
displayed)`. Re-running is idempotent; with `DEMO_MODE=false` it must exit `2` and
write nothing.

### 10.5 Start the demo **with the reset secret available to the backend process**

`POST /api/v1/demo/reset` re-seeds from the fixtures and therefore needs the seed
secret **inside the backend process**: `services/demo.py` answers `500 E_INTERNAL`
when `Settings.demo_seed_password` is empty. `Settings` is read **once per process**
(env takes precedence over `.env`) and `Start-Process` in PowerShell 5.1 inherits
the parent environment, so the variable must be present *at launch* — and can be
cleared in the parent immediately afterwards.

```powershell
Set-Location $Review
$env:DEMO_MODE           = 'true'   # inherited by the backend start.ps1 launches
$env:DEMO_SEED_PASSWORD  = $Plain   # inherited at process start, needed only for reset
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1 -NoBrowser
"start exit code: $LASTEXITCODE"

Remove-Item Env:DEMO_SEED_PASSWORD   # parent shell no longer carries it
if (Test-Path Env:DEMO_SEED_PASSWORD) { 'FAIL: secret still in the environment' } else { 'OK: reset secret cleared from the parent shell' }

$Api = 'http://127.0.0.1:8000'
Invoke-RestMethod -Uri "$Api/health"  | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri "$Api/version" | ConvertTo-Json -Depth 6
Invoke-WebRequest -Uri 'http://127.0.0.1:5173/' -UseBasicParsing | Select-Object StatusCode
Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

Documented limitation to be aware of: the secret now lives **only in the
already-running backend process's memory**. Restarting the backend (without
repeating the two lines above) would make `/demo/reset` answer `500 E_INTERNAL`.
It is never written to `.env`, a script, a log or git, and `$Plain` is cleared in
§10.9.

Expected: `/health` → `status = "ok"` with database/migrations `ok`; `/version` →
the P2 version string; the Vite page `200`; ports 8000/5173 listening on
`127.0.0.1` only, owned by the processes `start.ps1` recorded in `data/runtime/`.

### 10.6 Authentication and role-based API smoke

```powershell
$Api = 'http://127.0.0.1:8000'

function Get-Token([string]$User) {
    $body = @{ username = $User; password = $Plain } | ConvertTo-Json
    (Invoke-RestMethod -Method Post -Uri "$Api/api/v1/auth/login" `
        -ContentType 'application/json' -Body $body).access_token
}

$DocToken      = Get-Token 'demo_doctor'
$UnassignedTok = Get-Token 'demo_doctor_unassigned'
$PatToken      = Get-Token 'demo_patient_a'
$AdminToken    = Get-Token 'demo_admin'

$H  = @{ Authorization = "Bearer $DocToken" }
$HU = @{ Authorization = "Bearer $UnassignedTok" }
$HP = @{ Authorization = "Bearer $PatToken" }
$HA = @{ Authorization = "Bearer $AdminToken" }

Invoke-RestMethod -Uri "$Api/api/v1/auth/me" -Headers $H  | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$Api/api/v1/auth/me" -Headers $HP | ConvertTo-Json -Depth 5   # patient_id present

# no token -> 401 E_UNAUTHENTICATED (never 403, never HTML)
try { Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients" -ErrorAction Stop | Out-Null }
catch { "no token       -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }

# unassigned doctor -> 403 E_SCOPE_VIOLATION, no patient content
$Pid = '11111111-1111-4111-8111-111111111111'
try { Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients/$Pid/timeline" -Headers $HU -ErrorAction Stop | Out-Null }
catch { "unassigned     -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }

# assigned doctor reads
Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients?limit=5" -Headers $H | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients/$Pid" -Headers $H | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients/$Pid/timeline?limit=5" -Headers $H | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients/$Pid/observations?measure_type=glucose&limit=5" -Headers $H |
    ConvertTo-Json -Depth 5

# patient on the doctor surface -> 403 E_FORBIDDEN; unknown id -> 404 E_NOT_FOUND
try { Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients" -Headers $HP -ErrorAction Stop | Out-Null }
catch { "patient→doctor -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }
try { Invoke-RestMethod -Uri "$Api/api/v1/doctor/patients/not-a-uuid/timeline" -Headers $H -ErrorAction Stop | Out-Null }
catch { "malformed id   -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }
```

Expected: `401 E_UNAUTHENTICATED`; `403 E_SCOPE_VIOLATION` with no patient content;
populated reads for `demo_doctor`; `403 E_FORBIDDEN`; `400 E_VALIDATION` for the
malformed id. Every error body is the problem envelope (`type`, `title`, `status`,
`code`, `request_id`), never HTML.

### 10.7 Check-in lifecycle: `201`, replay, and `409`

```powershell
$Api  = 'http://127.0.0.1:8000'
$Now  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$Key  = [guid]::NewGuid().ToString()
$Body = @{ measured_at = $Now; measure_type = 'heart_rate'; value = 78; unit = 'bpm';
           note = 'owner Windows smoke' } | ConvertTo-Json

$Hdr = @{ Authorization = "Bearer $PatToken"; 'Idempotency-Key' = $Key;
          'Content-Type' = 'application/json' }

# 1. first write must be HTTP 201
$firstResp = Invoke-WebRequest -Method Post -Uri "$Api/api/v1/patient/check-ins" -Headers $Hdr -Body $Body
"first status   : " + [int]$firstResp.StatusCode
$first = $firstResp.Content | ConvertFrom-Json
"trust_level    : $($first.trust_level) / source: $($first.source) / id: $($first.id)"

# 2. same key + same payload -> replay of the SAME row, header Idempotent-Replay: true
$replayResp = Invoke-WebRequest -Method Post -Uri "$Api/api/v1/patient/check-ins" -Headers $Hdr -Body $Body
$replay     = $replayResp.Content | ConvertFrom-Json
"replay status  : " + [int]$replayResp.StatusCode
"replay header  : " + $replayResp.Headers['Idempotent-Replay']
"same id        : " + ($first.id -eq $replay.id)

# 3. NEW key + SAME measurement -> 409 E_DUPLICATE_CHECKIN (not 500, no second row)
$DupHdr = @{ Authorization = "Bearer $PatToken"; 'Idempotency-Key' = [guid]::NewGuid().ToString();
             'Content-Type' = 'application/json' }
try {
    Invoke-WebRequest -Method Post -Uri "$Api/api/v1/patient/check-ins" -Headers $DupHdr -Body $Body -ErrorAction Stop | Out-Null
    'FAIL: duplicate measurement was accepted'
} catch {
    "duplicate      -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message
}

# 4. exactly one row with this value exists
$mine = Invoke-RestMethod -Uri "$Api/api/v1/patient/check-ins?limit=20" -Headers $HP
"rows with 78   : " + (@($mine.items | Where-Object { $_.value -eq 78 }).Count)

# 5. engine-derived provenance cannot be forged, and mmol/L is never converted
$Forge = @{ measured_at = $Now; measure_type = 'heart_rate'; value = 79; unit = 'bpm';
            trust_level = 'doctor_verified' } | ConvertTo-Json
try {
    Invoke-RestMethod -Method Post -Uri "$Api/api/v1/patient/check-ins" `
        -Headers @{ Authorization = "Bearer $PatToken"; 'Content-Type' = 'application/json' } `
        -Body $Forge -ErrorAction Stop | Out-Null
} catch { "forged field   -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }

$Bad = @{ measured_at = $Now; measure_type = 'glucose'; value = 6.1; unit = 'mmol/L' } | ConvertTo-Json
try {
    Invoke-RestMethod -Method Post -Uri "$Api/api/v1/patient/check-ins" `
        -Headers @{ Authorization = "Bearer $PatToken"; 'Content-Type' = 'application/json' } `
        -Body $Bad -ErrorAction Stop | Out-Null
} catch { "mmol/L         -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }
```

Expected: `first status = 201`, `trust_level = self_reported_validated`,
`source = patient_checkin`; replay `201` with `Idempotent-Replay: true` and the
**same** id; the new-key duplicate → **`409` with `E_DUPLICATE_CHECKIN`** and
`rows with 78 = 1`; forged field → `400 E_VALIDATION`; `mmol/L` →
`400 E_UNIT_NOT_ALLOWED`.

### 10.8 Demo administration — denial **first**, successful reset **last**

`POST /demo/reset` deletes **every** row in `session`, so any token captured in
§10.6 is invalid afterwards. The denial therefore has to be proven **before** the
successful reset; the reset is the last authenticated call of the run.

```powershell
$Api = 'http://127.0.0.1:8000'

# 1. a doctor must be refused: 403 E_FORBIDDEN (checked while tokens are still valid)
try {
    Invoke-RestMethod -Method Post -Uri "$Api/api/v1/demo/reset" -Headers $H -ErrorAction Stop | Out-Null
    'FAIL: doctor was allowed to reset'
} catch { "doctor reset   -> " + [int]$_.Exception.Response.StatusCode + " " + $_.ErrorDetails.Message }

# 2. the forbidden / deferred surfaces must not exist, probed with the REAL method
try {
    Invoke-RestMethod -Method Post -Uri "$Api/api/v1/demo/seed" -Headers $HA -ErrorAction Stop | Out-Null
    'FAIL: POST /demo/seed answered'
} catch { "POST /demo/seed  -> " + [int]$_.Exception.Response.StatusCode }
try {
    Invoke-RestMethod -Method Get -Uri "$Api/api/v1/demo/status" -Headers $HA -ErrorAction Stop | Out-Null
    'FAIL: GET /demo/status answered'
} catch { "GET /demo/status -> " + [int]$_.Exception.Response.StatusCode }

# 3. the administrator's reset — LAST authenticated call of the run
$reset = Invoke-RestMethod -Method Post -Uri "$Api/api/v1/demo/reset" -Headers $HA
$reset | ConvertTo-Json -Depth 4
"cases_loaded   : " + ($reset.cases_loaded -join ', ')

# 4. every pre-reset token is now dead (sessions were deleted) -> 401
try { Invoke-RestMethod -Uri "$Api/api/v1/auth/me" -Headers $HA -ErrorAction Stop | Out-Null }
catch { "admin token    -> " + [int]$_.Exception.Response.StatusCode + " (expected 401: session deleted by reset)" }

# 5. the reseed used the SAME password: logging in again must work
$Relogin = Get-Token 'demo_admin'
"relogin ok     : " + [bool]$Relogin
```

Expected: doctor → `403 E_FORBIDDEN`; `POST /demo/seed` → `404`;
`GET /demo/status` → `404`; admin reset → `200` with
`cases_loaded = [A_stable, B_changed, C_ambiguous_ocr]` and the audit trail
retained; the old admin token → `401`; re-login succeeds with the same password
(proof that the reset re-hashed the same secret).

### 10.9 Clean shutdown, isolation proof, and secret/token cleanup

```powershell
Set-Location $Review
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1
"stop exit code: $LASTEXITCODE"
Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen -ErrorAction SilentlyContinue   # expected: nothing
Get-ChildItem -LiteralPath (Join-Path $Review 'data\runtime') -Filter *.json |
    Select-Object Name                                                                  # expected: no run-state/PID files

# main must be exactly as it was in 10.0
git -C $Main status --porcelain
$MainHeadAfter = (git -C $Main rev-parse HEAD)
"main HEAD unchanged: " + ($MainHeadAfter -eq $MainHeadBefore)
if ($MainDbExisted) {
    $after = (Get-FileHash -LiteralPath $MainDb -Algorithm SHA256).Hash
    "main app.db unchanged: " + ($after -eq $MainDbHashBefore) + " ($after)"
} else {
    "main app.db still absent: " + (-not (Test-Path -LiteralPath $MainDb))
}

# PBKDF2 timing at the shipped work factor, measured ON WINDOWS
& "$Review\.venv\Scripts\python.exe" -c "import sys,time; sys.path.insert(0,'backend'); from app.core.security import hash_password, verify_password; t=time.perf_counter(); h=hash_password('benchmark-only-not-a-credential'); t1=time.perf_counter(); ok=verify_password('benchmark-only-not-a-credential',h); print('python', sys.version.split()[0]); print('hash %.0f ms, verify %.0f ms, ok=%s' % ((t1-t)*1000,(time.perf_counter()-t1)*1000,ok))"

# clear secrets and tokens from the session
Remove-Item Env:DEMO_MODE, Env:DEMO_SEED_PASSWORD, Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Variable Plain, DocToken, UnassignedTok, PatToken, AdminToken, Relogin `
    -ErrorAction SilentlyContinue
Remove-Variable H, HU, HP, HA, Hdr, DupHdr, first, firstResp, replay, replayResp, reset, mine, Forge, Bad `
    -ErrorAction SilentlyContinue
if (Get-Variable -Name Plain -ErrorAction SilentlyContinue) { 'FAIL: password still in session' } else { 'OK: password cleared' }
if (Get-Variable -Name PatToken -ErrorAction SilentlyContinue) { 'FAIL: token still in session' } else { 'OK: tokens cleared' }
```

Expected: `stop` exit `0`, no listeners on 8000/5173, no tracking files; `main`
HEAD and `git status` unchanged; `main/data/runtime/app.db` byte-identical **or**
still absent; Windows-measured PBKDF2 timings recorded; `OK` for both cleanup
checks.

**Only after every output above has been captured** may the worktree be removed —
it holds the evidence database:

```powershell
git -C $Main worktree remove $Review --force
git -C $Main worktree list
```

### 10.10 What the owner must report back

| Evidence | Step |
|---|---|
| `test_all.ps1` PASS/FAIL/SKIP summary + exit code | 10.2 |
| Migration `head` → `p1` → `head` PASS lines | 10.3 |
| Seed counts, refusal paths, seed secret cleared | 10.4 |
| `/health`, `/version`, Vite `200`, ports, reset secret cleared after launch | 10.5 |
| Login, `me` (role + patient_id), `401`, `403 E_SCOPE_VIOLATION`, `403 E_FORBIDDEN`, `400` malformed id | 10.6 |
| Check-in `201`, replay `Idempotent-Replay: true` + same id, `409 E_DUPLICATE_CHECKIN`, single row, forged `400`, `mmol/L` `400` | 10.7 |
| Doctor reset `403` (before), `404` for `POST /demo/seed` and `GET /demo/status`, admin reset `200`, old token `401`, re-login ok | 10.8 |
| Clean shutdown, free ports, tracking files removed, `main` unchanged (hash or absence), Windows PBKDF2 timings, secrets/tokens cleared | 10.9 |

Any deviation is a **blocker to be reported**, not something to work around: the
checklist claims no result of its own.

### 10.11 Owner Windows verification — EXECUTED RESULTS, 2026-11-14 (PASS)

The checklist above was executed by the owner, not by the implementer. This is the
**only** section of this report that records a Windows result, and every number
below comes from the owner's evidence comment
[`6882774686`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6882774686).

| Item | Value |
|---|---|
| Date | 2026-11-14 |
| Verified commit (code snapshot) | `9fddb51ba7672efd992c47325ab4883734da3c9a` |
| Environment | Windows **PowerShell 5.1**, **Python 3.12.9** |
| Isolated review worktree | `E:\DEPI\P2-Review` (own `.venv`, own `.env`, own SQLite database) |
| Evidence | owner comment [`6882774686`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6882774686) |
| Decision | **Owner Windows verification: PASS** — *verification evidence only, not final P2 approval or merge authorization* |

| Verification (owner) | Result |
|---|---|
| Isolated Git worktree and installation | PASS |
| Full `test_all.ps1` quality gate | **12 PASS / 0 FAIL / 1 optional SKIP**, exit 0 |
| Backend pytest | PASS (exact Windows test count not captured in the console summary) |
| Frontend tests | 13 passed |
| Alembic P2 → P1 → P2 round trip | PASS |
| OpenAPI contract | **11 paths / 12 operations / 22 schemas** — PASS |
| Synthetic bootstrap | 6 users, 3 patients, 3 encounters, 17 observations — PASS |
| Backend / frontend startup and health | PASS |
| Authentication and token rejection | PASS |
| RBAC and patient isolation | 9 checks PASS |
| Check-ins and idempotency | 8 checks PASS |
| Demo reset and session revocation | 7 checks PASS |
| Identity-safe shutdown | PASS |
| `main` HEAD and clean working tree | Unchanged |
| `main` SQLite database SHA-256 | Byte-identical |
| P2 review working tree | Clean |
| PBKDF2 security checks | PASS |

**PBKDF2-HMAC-SHA256, 600 000 iterations, measured on Windows** — hash
**550.49 ms**, verify **537.67 ms**; wrong password rejected; `needs_rehash`
passed. (The 3.11 sandbox figure in §7 is a different machine and is not a Windows
measurement.)

**Optional Playwright browser smoke: SKIPPED — not run, not passed.** It stays a
recorded skip (`test_all.ps1` reports it as `SKIP`), exactly as in §8.

**Two owner-side PowerShell *test-command* errors** were corrected and the affected
validations rerun successfully: a reserved `$PID` variable name, a Python `-c`
quoting problem, and one PowerShell interpolation syntax correction. **No
application code change was required**, and the implementation under test did not
change.

**Independent CI at the same commit:** run
[`43626628577`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43626628577) —
**COMPLETED / SUCCESS**, Backend Python 3.12 **SUCCESS**, Frontend Node 22
**SUCCESS**.

**What this PASS does not mean.** It is owner-executed verification evidence on one
machine, with synthetic data, not final P2 approval: **P2 stays `IN_REVIEW`**, no
approval, no merge SHA and no `PASS` phase marking are recorded here, and P3 is not
authorized. The known limitations in §11 are unchanged by a successful gate.

**Provenance note.** Earlier revisions of this report said the Windows gate was
`PENDING` / `NOT RUN`, which was accurate at the time. Those statements were
superseded by this section rather than deleted; the historical CI and 403 observer
records in §9.1–§9.2 are untouched.

## 11. Known limitations and deferred items

1. **Login rate limiting is in-process** (`core/security.LoginRateLimiter`): a
   restart clears the counter and a multi-worker deployment would need a shared
   store. Honest MVP limitation for the single-machine demo (`ASM-06`).
2. **`GET /api/v1/demo/status` is deferred to P5** (`OQ-P2-01`). The accepted
   schema requires a drafting-provider status whose enum only admits components
   introduced in P5; returning one in P2 would assert a non-existent component.
   `POST /demo/reset` and `DemoResetResponse` are unaffected.
3. **`NEG-01` is not implementable in P2** — there are no documents until P3, so
   the row stays NOT APPLICABLE rather than being claimed as covered.
4. **Two internal tables are additions to the data dictionary** (`session`,
   `checkin_idempotency`), accepted by the owner and documented in
   `app/db/models.py`; the amendment belongs in the contract document, which P2
   does not modify.
5. **Argon2id remains the preferred hashing algorithm** long-term; P2 ships
   stdlib PBKDF2-HMAC-SHA256 at 600 000 iterations because adding a dependency
   would touch files outside the authorized scope. The stored hash is
   self-describing, so a future move is incremental (`needs_rehash`).
6. **SQLite only** (`ADR-0003`): the migration relies on SQLite's tolerance of
   forward foreign-key references for the `user ↔ patient` cycle. A different
   backend would need an `ALTER TABLE ADD CONSTRAINT` step.
7. **Migration-time foreign keys are off by design** on the Alembic connection;
   runtime enforcement is asserted separately (§6.6).
8. **P1 gate files changed** (G1–G3): the old assertions encoded "P1 only" and
   could not survive P2. They were replaced with equality assertions that include
   the explicit P2 allowlist, preserving their intent.
9. **No clinical claim** is made anywhere: synthetic data, deterministic rules,
   `self_reported_validated` provenance, and no recommendations or diagnoses.
10. **The two-writer tests are SQLite-specific evidence, not a Windows or
    multi-process guarantee.** They use two real connections plus an explicit
    hold event and prove that the second writer replays or receives `409` instead
    of a `500`; they do not prove every Windows scheduler interleaving, every
    `busy_timeout` configuration, or safety under multiple worker processes.
11. **A `database is locked` error is not explicitly converted into a replay.**
    The service catches `IntegrityError` (unique/constraint violation) and rolls
    back; a SQLite `OperationalError` under sustained lock contention would
    surface as an error rather than a guaranteed idempotent answer. Do not read
    this as blanket contention safety.
12. **`scripts/powershell/test_all.ps1` was not modified** (outside the authorized
    scope) and its OpenAPI gate *banner* still reads `/health, /version only`
    from P1. This is cosmetic: the script invokes `check_openapi.py`, which is the
    P2 strict gate and prints `PASS (11 paths / 12 operations, 22 schemas)`. The
    banner must not be read as evidence that the P1-only check still runs, and
    silently editing that unapproved file was deliberately avoided.
13. **`POST /api/v1/demo/reset` needs the seed secret inside the backend
    process.** It re-seeds from the fixtures, so `services/demo.py` answers
    `500 E_INTERNAL` when `DEMO_SEED_PASSWORD` is empty at process start
    (`Settings` is read once per process; the environment wins over `.env`). This
    is an operator configuration matter, not a client error: the owner checklist
    re-supplies the same password at launch and clears it from the parent shell
    afterwards (§10.5). Nothing is ever written to `.env`, a script, a log or git.
14. **A successful reset invalidates every session.** `clear_demo_data()` deletes
    the whole `session` table before reseeding, so all bearer tokens die with it —
    which is why the owner checklists prove the doctor's `403` *before* the admin
    reset and re-login afterwards (§10.8), and why the check-in idempotency
    evidence is collected earlier (§10.7).
15. **Resolved: the intermittently flaky validation-envelope assertion
    (`test_p2_auth_http.py::test_request_validation_uses_the_contract_envelope`).**
    The old test asserted `"ab" not in response.text` to prove the submitted
    username is never echoed, but `response.text` contains a random `request_id`
    UUID which can itself contain `ab` (`…-95e4-ab3b42cbc2d9`), so the test failed
    roughly one run in ten despite correct product behaviour. It is now fixed — with
    no change to application code:
    - the assertion reads the **user-facing validation text only** (`title`,
      `detail`, `details[].field`, `details[].reason`) and excludes the random
      correlation id, which may legitimately contain any short substring;
    - the submitted values are chosen so they cannot collide with a Pydantic *rule*
      name (`string_too_short` contains `short`, so `password="short"` is a poor
      probe; the test uses `secret7`);
    - a **deterministic regression test**
      (`test_validation_envelope_never_echoes_credentials_even_when_the_request_id_contains_them`)
      pins a client-supplied `X-Request-ID` of
      `00000000-ab00-4000-8000-000000000000`, asserts the response echoes exactly
      that id, and shows that a raw-body substring check is false for this input —
      so a regression to the old assertion now fails **every** time instead of one
      run in ten;
    - evidence: targeted pair of tests **25/25 runs PASS**; re-introducing
      `request_id` into the checked fragments (mutation) makes the regression test
      **FAIL** immediately; full suite **356 passed** (231 in `backend/tests/p2`).

    Nothing about the security requirement was weakened: the envelope, the status
    `400`, the `E_VALIDATION` code, the `{field, reason}` shape and the no-echo
    property are all still asserted.

---

## 12. Risks and rollback

**Risks**

- The `Idempotency-Key` durability guarantee now depends on the partial unique
  index `uq_observation_checkin_identity`; dropping that index in a later phase
  would silently reopen the semantic-duplicate race. It is asserted in
  `test_p2_migration.py` and the smoke gate.
- Concurrency behaviour is proven for SQLite serialized writers with two
  connections; it is **not** a claim about multi-process deployments, another
  database engine, or every Windows scheduling/busy-timeout case (§11.10–11.11).
- Rate limiting and the audit idempotency key are per-process concerns; see §11.1.
- The 3.12 CI leg is verified by the reviewer (§9.2) but **not by the
  implementer**, whose Actions/Checks read stays `403` (§9.1). Windows timings
  **are** measured: PBKDF2-HMAC-SHA256 at 600 000 iterations gives hash
  **550.49 ms** and verify **537.67 ms** on the owner's Windows machine (§10.11).
  They are one machine's numbers, not a performance budget.

**Rollback**

- Revert the P2 commits on the branch (`69f12ae`, `58b60f8`, `4f661de`); `main`
  was never modified.
- Schema: `alembic downgrade 0001_p1_baseline` removes the seven P2 tables and
  leaves P1's `schema_meta` untouched; `alembic downgrade base` returns the
  documented empty state. Both are asserted by tests and by the smoke gate.
- Data: the dataset is synthetic and rebuildable with
  `python -m app.services.seed`; nothing outside the database is written.

---

## 13. Handback

Implementation, sandbox verification, independent review and owner Windows
verification are complete. None of that is code approval, merge authorization or a
phase PASS.

| Gate | State at this revision |
|---|---|
| Implementer sandbox evidence (3.11) | **complete** (§7) |
| Independent reviewer technical reviews | `5906194976`, `5906286395`, `5906330237` addressed; final review `5906680401` **COMMENT** — asked for this ledger synchronization |
| CI (3.12 + Node 22), runs `43625331149` (`dbaf938`), `43625989736` (`6d54ede`), `43626628577` (`9fddb51`) | **SUCCESS** in all three (reviewer-verified, §9.2) |
| Owner Windows quality gate (`test_all.ps1`) at `9fddb51` | **PASS** — 12 PASS / 0 FAIL / 1 optional SKIP, exit 0; PBKDF2 550.49 ms hash / 537.67 ms verify (§10.11) |
| Optional Playwright smoke | **SKIPPED** — not run, not passed (§8, §10.11) |
| Owner approval / merge / P2 PASS | **NOT GIVEN** — PR #7 stays **draft**, P2 **IN_REVIEW** |
| P2 phase status | **IN REVIEW** — no approval, no merge SHA, no `PASS` |
| P3 | **NOT STARTED** |

No approval, merge, PASS marking or P3 work is performed by the implementer.

---

## 14. Document history

| Date | Revision |
|---|---|
| 2026-11-14 | Initial report at implementation handback `dbaf938`. |
| 2026-11-14 | Reviewer-driven documentation synchronization (mentor review `5906286395`), **docs-only**: §9.2 adds the independently verified CI run `43625331149` (3.12 SUCCESS, Node 22 SUCCESS) while §9.1 keeps the implementer's 403/NOT-OBSERVED evidence as a historical observer limitation; §8 ledger row updated accordingly, no `OQ` opened for the resolved CI question; §10 replaced with a PowerShell 5.1 / Python 3.12 checklist on an isolated review worktree with its own venv, `.env` and fresh SQLite database, covering full quality gates, migrations, bootstrap, auth, role-based access, idempotency, startup and clean shutdown; §11 adds the SQLite `database is locked` caveat and the unchanged `test_all.ps1` banner; no code, migration, gate script or P1 file changed. |
| 2026-11-14 | **§10 revision 2** (mentor review `5906330237`), **docs-only**: the reset secret is re-supplied to the backend at launch and cleared from the parent shell (the previous order would have ended in `500 E_INTERNAL`); reset denials are proven **before** the admin reset because reset deletes all sessions; §10.7 now actually issues the new-key duplicate request and asserts `409 E_DUPLICATE_CHECKIN` plus the first response's `201`; `POST /demo/seed` (not `GET`) is probed; `APP_VENV_DIR`, a pre-existing review directory, a dirty worktree and both states of `main/data/runtime/app.db` are guarded, with tokens/password cleared at the end. §9.2 records the second reviewer-verified CI run `43625989736` on docs-only HEAD `6d54ede`, which supersedes the earlier "docs commits lack CI" caveat. No code changed; P2 stays IN_REVIEW. |
| 2026-11-14 | **Final acceptance-ledger synchronization** (independent final review `5906680401`), **docs-only**: §10.11 records the owner's executed Windows verification at the verified code snapshot `9fddb51` — 12 PASS / 0 FAIL / 1 optional SKIP, Alembic P2→P1→P2, 11 paths / 12 operations / 22 schemas, 6 users / 3 patients / 3 encounters / 17 observations, 9 RBAC checks, 8 idempotency checks, 7 demo-reset checks, identity-safe shutdown, `main` HEAD unchanged and its database byte-identical, plus Windows-measured PBKDF2 550.49 ms hash / 537.67 ms verify — with the evidence comment `6882774686` linked. §8, §9.2, §13 and the header now show the gate as **PASS** at that commit and cite CI run `43626628577`; the former `PENDING` / `NOT RUN` wording is retained as historical provenance. Optional Playwright stays a recorded **SKIP**. No code, migration, gate, test or configuration change; no approval, merge SHA or P2 `PASS` recorded; P2 remains **IN_REVIEW**, P3 not started. |
| 2026-11-14 | **Final test-reliability fix** (independent review `5906711140`), test + docs only: `test_request_validation_uses_the_contract_envelope` no longer asserts on the raw response body (a random `request_id` could contain `ab`, causing a ~1-in-10 false failure). It now checks the user-facing validation text only, with submitted values that cannot collide with a Pydantic rule name, and a new deterministic regression test pins a client `X-Request-ID` containing `ab` — proven by 25/25 targeted runs and by a mutation that makes the regression test fail. §11.15 is re-labelled **Resolved** with that evidence; §12's stale "Windows timings are still unmeasured" sentence now records the measured 550.49 ms / 537.67 ms at 600 000 iterations (§10.11). Suite: **356 passed** (231 P2). No application, migration, gate, dependency or configuration change; P2 remains **IN_REVIEW** and the owner-tested implementation is still `9fddb51`. |

**NOT FOR CLINICAL USE — educational, synthetic-data demo only.**
