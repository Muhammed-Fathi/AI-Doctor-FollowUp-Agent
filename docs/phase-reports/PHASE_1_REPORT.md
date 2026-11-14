# Phase 1 Report — Foundation and Reproducible Startup

| Field | Value |
|---|---|
| Report ID | `REPORT-P1-001` |
| Phase | **P1 only** — repository foundation, reproducible startup, `/health` + `/version`, frontend status page, SQLite + Alembic baseline, Windows scripts, CI |
| Status | **IN_REVIEW — owner Windows verification complete; owner approval and merge still pending. Not `PASS`, not merged.** |
| Branch | `arena/d86c4f98-ai-doctor-followup-agent` |
| Base commit | `a33e693ba16560836312351787769ec5ee18b469` (verified `main` HEAD before any change) |
| Head commit | `eec6642ba700be25f8be1d645bb099f51a665441` — the commit the owner verified on Windows |
| Merge SHA | **unset — the phase is not merged** |
| Pull request | [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4) against `main`, title `P1: Foundation and reproducible local startup` |
| GitHub Actions | run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) — **SUCCESS** |
| Author | Arena agent (implementer) |
| Reviewer | Project owner — Windows verification complete; **sign-off pending** |

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.** This report describes infrastructure
> work. No clinical feature, no patient data and no model integration exists. Nothing here was
> clinically or procedurally validated.

---

## 1. Scope and non-goals

**In scope (P1):** monorepo skeleton, Python 3.12 FastAPI backend with typed `/health` and
`/version`, React + TypeScript + Vite status page, SQLite + SQLAlchemy + Alembic baseline,
hash-pinned Python locks and `package-lock.json`, strict `.gitignore` and `.env.example`,
five Windows PowerShell scripts, deterministic automated checks, minimal GitHub Actions CI,
a Windows runbook and this report.

**Explicit non-goals (deferred, not stubbed):** authentication/roles (P2), patient/observation
domain and seeded users (P2), document upload, PDF/OCR extraction and verification (P3),
monitoring comparison and demo review rules (P4), LangGraph agents, Ollama adapter and
checkpointing (P5), doctor/patient UI and follow-up tasks (P6). No placeholder module, empty
router or speculative schema was created for any of them.

---

## 2. Changed files (exact)

Renamed/added at the repository root and in these paths — 58 files added or replaced on the branch
(plus `ci.yml`, which is supplied separately for the reason in §7.5):

```text
(CI workflow: prepared and validated but NOT included on the branch - see §7.5)
.env.example
.gitignore                              (replaced: Phase-0 net -> full project ignore set)
README.md                               (Status, Start here, Stack, Layout, Verification honesty)
pyproject.toml
requirements/requirements.lock
requirements/requirements-dev.lock
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/api/system.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/core/logging.py
backend/app/core/paths.py
backend/app/core/version.py
backend/app/db/__init__.py
backend/app/db/base.py
backend/app/db/models.py
backend/app/db/session.py
backend/app/schemas/__init__.py
backend/app/schemas/system.py
backend/migrations/alembic.ini
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_p1_baseline.py
backend/tests/conftest.py
backend/tests/test_health.py
backend/tests/test_version.py
backend/tests/test_openapi.py
backend/tests/test_database.py
backend/tests/test_safety_guards.py
backend/tests/test_powershell_scripts.py
backend/tests/test_ci_workflow.py
frontend/package.json
frontend/package-lock.json
frontend/tsconfig.json
frontend/vite.config.ts
frontend/eslint.config.js
frontend/playwright.config.ts
frontend/index.html
frontend/src/main.tsx
frontend/src/styles.css
frontend/src/app/App.tsx
frontend/src/app/constants.ts
frontend/src/components/ErrorNotice.tsx
frontend/src/components/StatusBadge.tsx
frontend/src/pages/HealthPage.tsx
frontend/src/services/systemApi.ts
frontend/tests/setup.ts
frontend/tests/HealthPage.test.tsx
frontend/tests/config.test.ts
frontend/tests/e2e/health.spec.ts
scripts/powershell/_common.ps1
scripts/powershell/preflight.ps1
scripts/powershell/setup.ps1
scripts/powershell/start.ps1
scripts/powershell/stop.ps1
scripts/powershell/test_all.ps1
scripts/python/check_openapi.py
scripts/python/check_alembic_smoke.py
scripts/python/scan_repository.py
docs/runbooks/WINDOWS_SETUP.md
docs/phase-reports/PHASE_1_REPORT.md        (this file)
docs/roadmap/PHASE_PROGRESS.md              (P1 status row + P1 evidence section)
```

No file outside the P1 allowed-path set (`AGENTS.md` §5) was modified. Two documentation files
were added under `docs/**` — see §11 for the scope note the owner should acknowledge.

---

## 3. Deliverables

| # | P1 requirement | Status | Where |
|---|---|---|---|
| 1 | Minimal monorepo layout | **Complete** | `backend/`, `frontend/`, `scripts/`, `requirements/`, `data/runtime/` (gitignored) |
| 2 | Python 3.12 + FastAPI + Pydantic, typed `/health` + `/version` | **Complete** | `backend/app/**`; contract-matched schemas |
| 3 | React + TypeScript + Vite minimal professional page | **Complete** | `frontend/` — one health/status route, no clinical screen |
| 4 | SQLite + SQLAlchemy + Alembic minimal reversible baseline | **Complete** | `backend/app/db/**`, `backend/migrations/**` (one table, `schema_meta`) |
| 5 | Dependency declarations + locks + `package-lock.json` | **Complete** | `pyproject.toml`, `requirements/*.lock` (uv, universal, hashed), `frontend/package-lock.json` |
| 6 | Five Windows PowerShell scripts | **Implemented and executed on the owner's Windows laptop** (PASS; see §13) | `scripts/powershell/` |
| 7 | `.env.example`, strict `.gitignore`, no committed secrets/artifacts | **Complete and scanned** | `.env.example`, `.gitignore`, `scripts/python/scan_repository.py` |
| 8 | Deterministic tests, Ruff, build validation, Alembic smoke | **Complete and executed** | `backend/tests/`, `frontend/tests/`, `test_all.ps1` gates |
| 9 | Minimal GitHub Actions CI, no model/GPU/paid API | **Complete and green** — the agent could not push workflow files, so the owner committed it at `6d09b66`; run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) SUCCESS | `.github/workflows/ci.yml` |
| 10 | Reproducible Windows guide + truthful P1 report | **Complete** | `docs/runbooks/WINDOWS_SETUP.md`, this report |

### 3.1 `/health` — a live response (not an expectation)

```json
{"status":"ok","version":"0.1.0","db":"ok","ollama":"not_configured",
 "tesseract":"not_configured","disclaimer":"EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"}
```

### 3.2 `/version` — a live response

```json
{"app_version":"0.1.0","api_version":"v1","workflow_version":"1.0.0",
 "policy_version":"demo-policy-1.1.0","git_sha":"a33e693ba16560836312351787769ec5ee18b469"}
```

`workflow_version` and `policy_version` are the P0 contract values
(`STATE_AND_GRAPH_CONTRACT.md` §2, `DEMO_REVIEW_RULES.md`). They are metadata only: no graph and
no rule engine exists in P1. `ollama` and `tesseract` are reported as `not_configured` — the
honest state, since neither is integrated.

---

## 4. Design decisions worth review

| Decision | Rationale | Risk accepted |
|---|---|---|
| `DependencyState` is a `StrEnum` component | Generated OpenAPI references one shared `#/components/schemas/DependencyState`, matching the P0 contract instead of three inline enums | none material |
| Public endpoints declare `security: []` explicitly | The generated schema states publicly what the contract states in prose | none |
| `schema_meta` is the only P1 table | P1 must prove migration mechanics without pre-empting `DATA_DICTIONARY.md` §2 | a P2 migration will add the domain tables |
| Alembic URL precedence `-x` → `ALEMBIC_DATABASE_URL` → config → settings | One source of truth for the SQLite path across `setup.ps1`, pytest, CI, and any working directory | none |
| `prepend_sys_path = %(here)s/..` in `alembic.ini` | `alembic -c <path>` works from any CWD, including Windows paths with spaces | none |
| uv-compiled **universal** (`--universal`) hashed locks | Pip on Windows resolves the same graph; `--require-hashes` blocks substitution; produced without a 3.12 interpreter locally | regenerating requires uv; documented in the lock header |
| `httpx2` (not `httpx`) in the dev lock | Starlette 1.10 deprecates `httpx` for `TestClient` and would emit a `DeprecationWarning` (tests run with `-W error`) | new-ish package; pinned and hash-verified |
| TypeScript 5.9.3 rather than 7.0.2 | `typescript-eslint` 8.72 supports `>=4.8.4 <6.1.0`; TS 7 would break linting | not on the newest major |
| Vite 7.3.8 rather than 8.3.8 | Vite 8 pulls a rolldown toolchain; Vite 7 is the conservative, widely used generation for a defense build. Both satisfy Node 24.15.0 | not on the newest major |
| State-based shutdown (`run-state.json`) instead of port-based | Prevents `stop.ps1` from ever terminating an unrelated process | if the state file is deleted, `stop.ps1` stops nothing (by design) and says so |

---

## 5. Dependencies, versions and licenses

All versions were read from the authoritative registries on **2026-11-14** before pinning, and
each is an exact pin in `pyproject.toml` / `frontend/package.json`, locked with hashes / a
`package-lock.json`.

### 5.1 Python (runtime)

| Package | Pin | License | `requires_python` |
|---|---|---|---|
| fastapi | 0.162.7 | MIT | `>=3.11` |
| pydantic | 2.14.3 | MIT | `>=3.10` |
| pydantic-settings | 2.16.3 | MIT | `>=3.11` |
| uvicorn | 0.54.0 | BSD-3-Clause | `>=3.10` |
| sqlalchemy | 2.1.8 | MIT | `>=3.11` |
| alembic | 1.20.1 | MIT | `>=3.10` |

Transitive runtime set (`requirements/requirements.lock`, 20 pins with hashes): annotated-doc,
annotated-types, anyio, click, h11, idna, mako, markupsafe, opentelemetry-api, pydantic-core,
python-dotenv, starlette, typing-extensions, typing-inspection.

### 5.2 Python (development only)

| Package | Pin | License |
|---|---|---|
| pytest | 9.2.0 | MIT |
| httpx2 | 2.16.0 | BSD-3-Clause |
| ruff | 0.17.5 | MIT |
| pyyaml | 6.0.3 | MIT |
| wheel | 0.48.0 | MIT |
| setuptools | 84.2.1 | MIT |

`requirements/requirements-dev.lock` contains 35 pins with hashes.

### 5.3 Frontend

| Package | Pin | License | Notes |
|---|---|---|---|
| react / react-dom | 19.3.1 | MIT | |
| vite | 7.3.8 | MIT | engines `^20.19.0 \|\| >=22.12.0` |
| @vitejs/plugin-react | 5.2.0 | MIT | peer `vite ^4.2 \|\| ^5 \|\| ^6 \|\| ^7` |
| typescript | 5.9.3 | Apache-2.0 | |
| vitest | 5.1.0 | MIT | |
| jsdom | 31.0.1 | MIT | |
| @testing-library/react | 16.3.3 | MIT | |
| @testing-library/dom | 10.4.2 | MIT | |
| @testing-library/jest-dom | 7.0.1 | MIT | |
| @testing-library/user-event | 14.6.10 | MIT | |
| eslint | 10.15.0 | MIT | |
| @eslint/js | 10.0.1 | MIT | |
| typescript-eslint | 8.72.2 | MIT | supports TypeScript `<6.1.0` |
| eslint-plugin-react-hooks | 7.1.1 | MIT | |
| globals | 17.14.0 | MIT | |
| @types/node | 26.6.6 | MIT | |
| @types/react / @types/react-dom | 19.3.0 | MIT | |
| @playwright/test | 1.65.1 | Apache-2.0 | installed; browsers not downloaded |

`frontend/package-lock.json` (lockfileVersion 3) contains 286 locked packages. Resolution was
verified by a clean `npm install` from an empty `node_modules` — **no** `--legacy-peer-deps` and
no `--force` was required with this exact set (an earlier experimental combination failed with an
`npm` arborist peer-resolution crash; the pinned set was adjusted rather than working around it
with a flag).

### 5.4 Reproducibility limits (honest statement)

* The Python locks are **universal** resolutions for CPython 3.12 on Windows/Linux/macOS. Wheel
  selection at install time is platform-specific; hashes cover every published artifact, so a
  substitution fails loudly, but the *installed wheel set* differs by platform.
* `npm ci` reproduces the exact tree from `package-lock.json`; it still downloads from
  registry.npmjs.org, so a registry outage blocks setup. There is no offline mirror.
* Playwright browser binaries are **not** locked or committed; the browser smoke gate is optional
  and reported as `SKIP` when the binaries are absent.
* The authoring sandbox ran **Python 3.11.2**, not 3.12. CI is configured for 3.12 and will be the
  first 3.12 execution of the suite (see §7.3).

---

## 6. Update to `DEPENDENCIES.md` status

`docs/contracts/DEPENDENCIES.md` still records `0.1.0-p0` / "nothing pinned" because it is a P0
document. This report supersedes that status for the P1 set: the versions above are installed,
locked and (except where explicitly noted as not executed) exercised. The owner may want
`DEPENDENCIES.md` synchronised in a follow-up documentation change; the agent did not rewrite a P0
contract silently.

---

## 7. Commands executed — actual results

> **How to read §7.** Everything in §7.1–§7.4 was executed by the *implementing agent*
> in a **Linux authoring sandbox** (Python 3.11.2, Node 22.22.3). Those numbers are kept
> as the **historical record of the authoring environment** and have not been rewritten.
> The **current** cross-platform state — the owner's Windows verification, the passing
> GitHub Actions run, and what remains genuinely unexecuted — is in **§8**.
> Where §7.3 says a check was "not executed", read it as *not executed in the authoring
> sandbox*; §8 records whether the owner has since executed it.


Environment: Linux sandbox, Debian 12, Python **3.11.2**, Node **22.22.3**, npm 10.9.8, git 2.39.5.
The repository virtual environment lives at `.venv/` (gitignored).

### 7.1 Executed and passed (Linux authoring sandbox — historical)

| # | Command | Exit | Observed result |
|---|---|---|---|
| 1 | `git log --oneline -1` | 0 | `a33e693 Merge pull request #3 …` — base commit verified before any change |
| 2 | `.venv/bin/python -V` | 0 | `Python 3.11.2` (see §5.4: not the 3.12 target) |
| 3 | `.venv/bin/pip install --require-hashes -r requirements/requirements.lock` (fresh venv, other venv) | 0 | resolved and installed all 20 hashed pins |
| 4 | `.venv/bin/pip install --require-hashes -r requirements/requirements-dev.lock` (fresh venv) | 0 | all 35 hashed pins installed |
| 5 | `pip install -e . --no-build-isolation --no-deps` (throwaway copy with `requires-python >=3.11`) | 0 | `import app` succeeded from an unrelated CWD (the real repo correctly refuses to install on 3.11 due to `requires-python`) |
| 6 | `python -m pytest -q` | 0 | `121 passed` (94 at the first submission + 27 review-fix tests) |
| 7 | `python -m pytest <file> -q` per suite | 0 | health 9, version 7, openapi 6, database 9, safety 7, powershell 67 (parametrised), CI 16 |
| 8 | `ruff check .` | 0 | `All checks passed!` |
| 9 | `ruff format --check .` | 0 | `27 files already formatted` (Python only; Markdown/docs are excluded from formatting) |
| 10 | `python -m alembic -c backend/migrations/alembic.ini upgrade head` | 0 | `Running upgrade -> 0001_p1_baseline`; created `data/runtime/app.db` |
| 11 | `alembic upgrade head → downgrade base → upgrade head` (temp DB, in tests and script) | 0 | table created, dropped, recreated; `alembic_version = 0001_p1_baseline` |
| 12 | `alembic -c backend/migrations/alembic.ini` from a *different* CWD (`/tmp`) | 0 | migration applied — `prepend_sys_path` fix confirmed |
| 13 | `python scripts/python/check_alembic_smoke.py <temp.db>` | 0 | `PASS (revision 0001_p1_baseline, tables ['alembic_version', 'schema_meta'])` |
| 14 | `python scripts/python/check_openapi.py` | 0 | `OpenAPI contract check: PASS (2 paths, 3 schemas)` |
| 15 | `python scripts/python/scan_repository.py` | 0 | `Secret/artefact scan: PASS (88 tracked/dirty files; 7 secret patterns, 4 claim patterns)` |
| 16 | `uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend` | running | `Application startup complete` |
| 17 | `curl -s -w '%{http_code}' http://127.0.0.1:8000/health` | 0 | HTTP **200**, `db=ok`, `status=ok` (body in §3.1) |
| 18 | `curl -s http://127.0.0.1:8000/version` | 0 | `api_version=v1`, `git_sha` = the real base SHA (body in §3.2) |
| 19 | `curl -s http://127.0.0.1:8000/openapi.json` | 0 | `paths = ['/health', '/version']`, `info.x-demo-notice` present |
| 20 | `npm install` (clean `node_modules`, no peer flags) | 0 | `added 234 packages`; `package-lock.json` lockfileVersion 3 |
| 21 | `npm ci --no-audit --no-fund` (equivalent clean install in CI config) | 0 | see #20 procedure |
| 22 | `npm run lint` (eslint 10 + typescript-eslint) | 0 | no errors |
| 23 | `npx tsc --noEmit` | 0 | typecheck clean under `strict` + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes` |
| 24 | `npm test` (vitest + jsdom) | 0 | `2 passed (2)` files, `12 passed (12)` tests (12 at that time; now 13) |
| 25 | `npm run build` (`tsc --noEmit && vite build`) | 0 | `34 modules transformed`; `dist/index.html 0.75 kB`, `index-*.css 4.25 kB`, `index-*.js 228.22 kB (gzip 71.43 kB)` |
| 26 | `npm run dev -- --host 127.0.0.1 --port 5173` then `curl http://127.0.0.1:5173/` | 0 | dev server ready in 168 ms; HTML served |
| 27 | `curl http://127.0.0.1:5173/health` and `/version` (Vite dev proxy) | 0 | both HTTP 200 with the same JSON as the backend — the page's data path is proven, not just the API |
| 27a | `npm run preview -- --port 4173` then `curl http://127.0.0.1:4173/`, `/health`, `/version` | 0 | production build served (HTTP 200) and both endpoints proxied — this is the exact server the Playwright smoke test drives |
| 28 | `python -c "yaml.safe_load(ci.yml)"` | 0 | `jobs: ['backend', 'frontend']` |
| 29 | **Clean-clone reproducibility**: `git clone <branch>` into a fresh directory, then a fresh `python3.11 -m venv` + `pip install --require-hashes -r requirements/requirements-dev.lock` | 0 | lock installed from scratch; `pytest -q` -> `121 passed`; `ruff check .` + `ruff format --check .` clean; `check_openapi.py` PASS; `scan_repository.py` PASS (94 files at the time of that run); `alembic upgrade head` + `check_alembic_smoke.py` PASS |
| 30 | Same clean clone: `npm ci --no-audit --no-fund` | 0 | `added 235 packages`; `npm run lint` clean; `npm test` -> 12 passed (12 at that time; now 13); `npm run build` -> built in 1.48 s |

### 7.2 Executed and failed (then fixed in this branch)

| Attempt | Failure | Resolution |
|---|---|---|
| `alembic upgrade head` in tests | `CommandError: 'connection' argument to configure() is expected to be a sqlalchemy.engine.Connection instance, got Engine(...)` | `env.py` rewritten to open its own `Connection` and to honour a programmatically-set `sqlalchemy.url` |
| `alembic -c backend/migrations/alembic.ini` from `/tmp` | `ModuleNotFoundError: No module named 'app'` | `prepend_sys_path = %(here)s/..` |
| `npm install` with the first pinned set | `npm error Cannot read properties of null (reading 'edgesOut')` (npm 10.9.8 arborist crash) | installed with `--legacy-peer-deps` to prove the tree, then bisected the offender and adjusted the pinned versions; final set installs cleanly **without** flags |
| `npx playwright install chromium` | `Download failure, code=1` (release-assets host unreachable) | browser smoke reported as **not executed**; not simulated (§7.3) |
| `npx playwright test` on the first spec revision | `browserType.launch: Executable doesn't exist …` — reported as **1 failed** instead of a skip, because the spec only guarded the backend precondition | added a browser-executable presence guard: `chromium.executablePath()` + `existsSync` before the test body. Re-run now reports `1 skipped` with the prerequisite named, which is the documented behaviour |
| ESLint `react-hooks/set-state-in-effect` | `Calling setState synchronously within an effect` | loading state moved out of the effect body |
| `pip install -e .` in the sandbox | `invalid command 'bdist_wheel'` | `wheel` + `setuptools` added to the dev lock with hashes; verified in a throwaway copy (real repo correctly refuses 3.11) |
| Real `.venv` editable install | `requires a different Python: 3.11.2 not in '<3.13,>=3.12'` | **not a defect** — the guard works; the sandbox simply is not 3.12 |

### 7.3 Not executed in the authoring sandbox — and why

| Check | Reason |
|---|---|
| **All five PowerShell scripts** (`preflight`, `setup`, `start`, `stop`, `test_all`) | No PowerShell and no Windows in the authoring sandbox. Only static properties were tested there (`test_powershell_scripts.py`). **Linux results are not evidence that these scripts work.** *Since executed by the owner on Windows — §13.1–§13.3.* |
| **The Python suite on Python 3.12** | The sandbox has Python 3.11.2; obtaining 3.12 was impossible (the python-build-standalone release host is not in the allowed egress set). *Since executed on 3.12 by CI run `43615782079` and by the owner on Python 3.12.9 — §13.* |
| **GitHub Actions run** | The workflow file could not be pushed by the agent at the time (§7.5). *Since resolved: the owner committed it at `6d09b66` and run `43615782079` completed SUCCESS.* |
| **Playwright browser smoke** | `npx playwright install chromium` fails (`Download failure, code=1`) because the browser CDN is outside the allowed egress set. The spec now self-guards both preconditions and the run reports `1 skipped` (verified: `npx playwright test` -> `1 skipped`), so it never fakes a pass or a failure. `test_all.ps1` reports the gate as `SKIP` with the reason. |
| **`test_all.ps1` end-to-end** | Same reason as the PowerShell row; each underlying command it calls was executed individually here. |

### 7.4 Requires the owner's Windows laptop — **now executed (§13)**

In the authoring sandbox none of the PowerShell scripts could run, so the whole
Windows gate was listed here as owner-only work. **The owner has since executed all of
it** at head `eec6642`; the full record is the appendix in **§13**. Summary:
`preflight.ps1` PASS, `setup.ps1` PASS (including from a path containing spaces),
`start.ps1` + `/health` HTTP 200, the status page rendered, `test_all.ps1` 12 PASS /
0 FAIL / 1 optional SKIP, and `stop.ps1` PASS leaving ports 8000 and 5173 free with all
three tracking files removed.

---

### 7.4a Re-verification at an earlier review head (historical)

> Historical record: this re-run was made at head `a20c536`, **before** the P1-R06/R07/R08
> fixes. Its numbers are kept as-is. The current head is `eec6642`; the current state is
> §13.

Re-run after the round-1 review fixes, at head `a20c536` on a clean working tree:

| Command | Exit | Observed |
|---|---|---|
| `python -m pytest` | 0 | `121 passed` |
| `ruff check .` | 0 | `All checks passed!` |
| `ruff format --check .` | 0 | `27 files already formatted` |
| `python scripts/python/check_openapi.py` | 0 | `PASS (2 paths, 3 schemas)` |
| `python scripts/python/scan_repository.py` | 0 | `PASS (94 tracked files at that head; 95 now)` |
| `alembic upgrade head` / `downgrade base` / `upgrade head` | 0 | all three steps exit 0; `check_alembic_smoke.py` PASS |
| `alembic -c <abs path>` from `/tmp` | 0 | migration applied (CWD independence) |
| `uvicorn … --port 8000` then `curl /health` | 0 | **200**, `status=ok`, `db=ok` |
| `curl /version` | 0 | `api_version=v1`, `git_sha=a20c536…` (the real head) |
| `curl /openapi.json`, `/docs` | 0 | only `/health` + `/version`; notice present; docs UI 200 |
| `npm run lint` / `npx tsc --noEmit` | 0 | clean |
| `npm test` | 0 | `12 passed` (2 files) — count at that earlier head |
| `npm run build` | 0 | built in 1.31 s |
| dev server `:5173` -> `/`, `/health`, `/version` | 0 | 200, 200, 200 (proxy proven) |
| preview server `:4173` -> `/`, `/health`, `/version` | 0 | 200, 200, 200 (production build + proxy) |
| `npx playwright test` | skipped | `1 skipped` — chromium not installed (honest, not a failure) |

Repository audit at the same head: `git ls-files` contains no `.env`, database, log, PID file,
`node_modules`, `.venv` or `dist`; the secret/artefact scan reports 0 findings; the backend contains
none of `langgraph`, `ollama`, `pytesseract`, `pypdf`, `smtplib`, `sendgrid`, `twilio`, `requests`,
`httpx`, `aiohttp`.

### 7.5 CI workflow delivery — resolved by the owner (commit `6d09b66`)

`.github/workflows/ci.yml` was written, YAML-parsed and covered by 16 static tests
(python 3.12, node 22, read-only permissions, no model/GPU/OCR/paid API/secrets, every
gate invoked, short timeouts). Pushing it failed:

```text
! [remote rejected] arena/d86c4f98-ai-doctor-followup-agent -> ... (refusing to allow a
  GitHub App to create or update workflow `.github/workflows/ci.yml` without `workflows`
  permission)
```

A direct API attempt to create a test workflow returned
`403 Resource not accessible by integration`. This is a permission boundary on the
agent's GitHub App token, not a code defect.

**Resolved.** The owner committed the workflow at `6d09b66` and both jobs now run on
every push. Current state:

* **GitHub Actions run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079)
  completed SUCCESS** (backend Python 3.12 + frontend Node 22) — the CI acceptance
  criterion is met;
* the 16 static workflow tests now execute instead of skipping when the file is absent;
* `test_all.ps1` remains the local equivalent gate for the owner's laptop.

The history above is kept because the permission boundary is a real constraint on what
this session could deliver, not a defect that was fixed in code.

### 7.6 Review round 1 — findings and resolutions

Reviews `5905323895` (P1-R01–R05) and `5905460892` (P1-R06) on head `7295d0c`.
The owner's first Windows run of `test_all.ps1` produced **PASS 1 / FAIL 9 /
SKIPPED 1** although the underlying tools succeeded — a reporting defect, not a
tool failure. All six findings are addressed below; **no finding is closed by
this document alone** — the owner re-runs on Windows.

| ID | Severity | Finding | Resolution in this revision | Verified here |
|---|---|---|---|---|
| **P1-R06** | **Blocker** | `Invoke-Native` emitted native stdout into its caller's pipeline beside the exit code, so `$code = Invoke-Native …` was an array and `$code -eq 0` was false for successful commands. The owner saw `Ruff lint (exit All checks passed! 0)`. | `_common.ps1`: native output is piped to `Out-Host` (same console, out of the pipeline); `$code` initialised to `0` and cast `[int]`; stderr deliberately not merged (`2>&1` under `ErrorActionPreference='Stop'` is unsafe on 5.1). `test_all.ps1` gained `Get-ExitCodeValue`, which fails a gate loudly if the wrapper ever returns a non-`[int]`. `Get-NativeOutput` hardened the same way but still returns `{ExitCode, Output}`. | 9 new static tests + **executable** `scripts/powershell/tests/invoke_native.tests.ps1` (7 cases incl. numeric-looking output); the script is now gate 0 of `test_all.ps1` |
| **P1-R03** | High | `Start-Process -ArgumentList` joins the array into one command line, so an `--app-dir` path containing a space was split and the child got a truncated path. | New shared `ConvertTo-QuotedArgument` / `ConvertTo-CommandLine` in `_common.ps1` (quotes only when needed, escapes embedded quotes, doubles a trailing backslash). `start.ps1` uses them for both the uvicorn and the `npm.cmd` launches. | Algorithm ported to Python and checked against 9 cases including `E:\DEPI\AI Doctor FollowUp Agent\backend` and `C:\Program Files\…` — all correct |
| **P1-R05** | High | `stop.ps1` required the repository path in the frontend command line; the `cmd.exe` wrapper may not carry it, so Vite could survive. | Identity for `frontend` now needs the Vite signature **and** any of: repository path, `run dev`, `--port 5173`, or `strictPort` — all of which `start.ps1` always passes. Backend identity stays strict (repository path **and** `uvicorn` **and** `app.main:app`). The verified descendant tree is still what gets stopped. | Static tests assert the relaxed frontend rule and the unchanged strict backend rule |
| **P1-R04** | Medium | The runbook's §5 told the owner to `git clone` into `E:\DEPI\AI-Doctor-FollowUp-Agent`, which already exists. | New §2.1 "You already have a clone (the normal case)" with `git fetch` / `git switch` / `git pull --ff-only` and a detached-HEAD alternative; fresh clone moved to optional §2.2 with a new path. §5 rewritten to match. | Documentation reviewed against the actual owner paths |
| **P1-R02** | Open | Windows execution of the gate. | **Still open by design.** This revision is a fix for the defect the owner's run exposed; it must itself be re-run on Windows. | — (see §7.3) |
| **P1-R01** | Closed | CI workflow missing. | Resolved by the owner: `.github/workflows/ci.yml` is committed at `6d09b66`; both Actions jobs are reported green by the owner. The 8 workflow tests now execute instead of skipping. | Workflow present and unmodified in the diff |
| — | Medium | React `act(...)` warning in the loading-state test. | Cause: the test asserted, then the mocked `fetch` settled after the test ended. Fixed by modelling a request that never settles (deterministic) and by `await`ing the rejection in the sibling test. **Not suppressed.** `tests/setup.ts` now *fails* any test that emits an `act(...)` warning while still printing React's message verbatim. | Proven both ways: reintroducing the old test body fails with "React reported 1 unwrapped state update(s)"; the fixed suite is clean with empty stderr |

### 7.7 Review round 2 — P1-R07 shutdown blocker, and its resolution

The owner's live Windows run (head `6693108`) stopped the backend correctly
(port 8000 freed) but **left Vite running on port 5173**, reporting
`Stop result: 1 stopped, 1 not stopped`.

**Evidence from the owner's machine (`Get-CimInstance Win32_Process`):**

| PID | Image | Command line | Note |
|---|---|---|---|
| 4400 | `cmd.exe` | `cmd.exe /c ""C:\Program Files\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port 5173 --strictPort "` | the recorded root |
| 5744 | `node.exe` | `"node" "<repo>\frontend\node_modules\\.bin\\..\vite\\bin\\vite.js" --host 127.0.0.1 --port 5173 --strictPort` | the actual Vite server |

**Root cause.** Round 1 required the frontend command line to contain `vite`
**or** `node_modules`. The recorded PID is the `cmd.exe`/`npm.cmd` **wrapper**,
whose command line contains neither, so the ownership test rejected a process
that was genuinely ours. Two further defects made it worse: the state files were
deleted even after a refusal (destroying the identity information needed for a
retry), and the script exited `0` while an owned process was still running.

**The fix.**

1. **Records real identity at startup.** `start.ps1` stores PID, image name,
   **process creation time** and command line. Creation time is what defeats PID
   recycling; a reused PID fails the check and is left alone.
2. **Classifies by role, not by one keyword.** `_common.ps1` now exposes
   `Test-NpmWrapperCommandLine` (npm + `run dev` + our port), `Test-ViteCommandLine`
   (a vite entry point *under this repository's frontend*) and
   `Test-UvicornCommandLine`. The wrapper is matched by source 1 + 2; each
   descendant is matched by its own command line (source 3).
3. **Stops children before the wrapper**, so Vite cannot be re-parented
   mid-shutdown. If the wrapper is already gone, an orphaned Vite child is
   adopted **only** on the repository Vite command line — never because it holds
   the port.
4. **Preserves tracking state** on partial failure: `Save-StopState` rewrites
   `run-state.json` and the PID files with whatever is still running, and only
   deletes them after a fully clean stop.
5. **Honest exit status**: `0` clean, `1` an owned process survived, `2` a port is
   still occupied. A missing state file with a busy port is `2`, not a silent `0`.
6. **Same fix in startup rollback**: `Stop-StartedProcesses` now stops the whole
   verified child tree of a failed start, with the same PID-reuse guard.
7. **PS 5.1 trap closed**: `ConvertFrom-Json` adds a falsy `PSComputerName`
   property to every object, so a bare `if (-not $entry)` would have skipped
   **every** state entry and reported a clean stop without acting. The entry
   filter is now an explicit `$null -ne $_`.

**Executable regression coverage** — `scripts/powershell/tests/stop_identity.tests.ps1`
(11 checks, gate 0b of `test_all.ps1`), built from the owner's verbatim command
lines: the wrapper and the Vite process are each recognised, a foreign project's
Vite is rejected, plain `node.exe` is rejected, `npm run build` is rejected,
`app.main:app` is accepted while `other.app:app` is rejected, forward-slash paths
work, the descendant walk finds a real child, a wrong image name or creation time
is rejected, and a falsy JSON property does not hide a state entry.

The classifier was additionally ported to Python and checked against the
owner's exact command lines plus seven look-alikes — all 9 cases correct.

### 7.8 Review round 3 — P1-R08 tracking-state deletion ordering

Finding: `stop.ps1` deleted `run-state.json` and the PID files whenever no
*survivor* was identified, and only **then** checked the ports and exited `2`.
The counterexample is a process holding port 5173 that cannot be traced to this
application: `$survivors` is empty, so the provenance needed to diagnose or retry
was destroyed while the script still reported `INCOMPLETE`.

**Fix.**

1. `Get-ShutdownVerdict` in `_common.ps1` decides the outcome — and therefore the
   exit code — **before** any tracking file is touched:
   `0 PASS` / `1 FAILED` / `1 BLOCKED` / `2 INCOMPLETE`.
2. `Save-StopState` moved to `_common.ps1` with a mandatory `-Clean` parameter and
   injectable paths, so it is reachable from the executable regression script.
   It removes files **only** when `-Clean` is true, and only on the
   `$survivors.Count -eq 0` branch, immediately followed by `return`.
3. Incomplete-with-no-survivor now **keeps the original metadata**, annotated
   `partial: true` and `incompleteReason` (`port-still-occupied`,
   `process-stop-failed`, `process-unverified`). A parse failure leaves the file
   untouched rather than deleting it.
4. `BLOCKED` is a new status: a recorded PID that is still alive but unverifiable
   is no longer a silent `INCOMPLETE`; it exits `1`, because the advertised
   success condition requires it to be gone.
5. Survivors are now filtered by liveness — a `not-ours` entry whose recorded PID
   is already gone is dropped instead of being retained forever as noise.

**The same bug class in `start.ps1`.** The rollback handler called
`Stop-StartedProcesses` and then unconditionally deleted the tracking files while
printing "nothing is left running". It now verifies the rollback, lists any
survivor, keeps the tracking files, and exits `1` with
`rollback was INCOMPLETE`.

**Coverage.**

- Executable, `scripts/powershell/tests/stop_identity.tests.ps1` cases 12-15:
  verdict mapping, **the exact counterexample** (`0` survivors + busy port ⇒ all
  three files kept, `partial` set, both original processes and `startedAt` /
  `venvDir` preserved), clean-result deletion, and survivor rewriting.
- Seven new static tests, including the ordering assertion
  (`$busyPorts` → `$verdict` → `Save-StopState`) and a check that no
  `Remove-Item` of a tracking file appears before the verdict.
- The verdict and state logic were ported to Python and run against the
  counterexample plus four other outcomes — all 21 assertions correct.

---

### 7.9 Review round 4 — P1-R09 documentation synchronization (docs-only)

Finding: after the owner's successful Windows verification, `PHASE_PROGRESS.md` still
described the Windows gate as "NOT EXECUTED", CI as undelivered/never run, and older
frontend counts; `PHASE_1_REPORT.md` still carried "owner review pending / Windows not
executed" wording in several places.

**Fixed in this round — documentation only, no application or script change:**

| Was | Now |
|---|---|
| `PHASE_PROGRESS.md` P1 row: "PowerShell scripts, Windows gate, Playwright smoke **not executed**" | Owner Windows gate **PASSED** with the exact counts, both start/stop paths, CI run link, and the optional Playwright SKIP |
| P1 deliverables: "PowerShell … **not executed** — requires the owner laptop", "3.12 execution pending in CI", "93 passing"/"8 passing" | Executed on Windows and in CI; counts corrected to 121 backend / 13 frontend; CI **delivered and green** |
| Status block: "owner review and the local Windows quality gate are pending" | Windows verification complete; **owner approval and merge still pending** |
| Report header: "Head commit: recorded in the PR description / Reviewer: pending" | Head `eec6642`, merge SHA **unset**, CI run URL, reviewer "sign-off pending" |
| Report §7 read as current state | §7 explicitly labelled the **historical** authoring-sandbox record; current state moved to §13 |
| Report §7.4/§7.5 described the Windows gate as owner-only and CI as "not met" | §7.4 points to the executed evidence; §7.5 records CI as resolved and green |
| §7.5–7.8 physically out of order | Renumbered into document order |

**History is preserved, not rewritten.** §7.1–§7.3 and the round-by-round findings
(§7.5–§7.8) keep their original numbers, commands and outcomes — including the failures
that were fixed. They are now clearly labelled as what the *implementing agent* observed
in a Linux sandbox, so they cannot be mistaken for the current cross-platform state.

## 8. Safety and security review

| Boundary | Evidence in this change |
|---|---|
| No diagnosis, treatment, prescribing, risk scoring | `test_p1_implements_no_clinical_capability` scans all backend sources for that vocabulary; UI copy contains no clinical terms (`HealthPage` test asserts the rendered page has none) |
| No external communication | `test_p1_backend_has_no_forbidden_imports` forbids `smtplib`, `sendgrid`, `twilio`, `requests`, `httpx`, `aiohttp` in backend code; there is no outbound network call anywhere in P1 |
| No patient data / synthetic-only | `schema_meta` is the only table; no PII field exists; `.gitignore` and the repository scan block databases and uploads |
| No secrets committed | `scan_repository.py` (7 secret patterns) + `.env.example` value check + `.env` ignored; `.gitignore` covers `.env`, keys, certs, tokens |
| No premature agents/OCR/model | Forbidden imports include `langgraph`, `ollama`, `pytesseract`, `pypdf`; `/health` reports them `not_configured` |
| Loopback only | Server binds `127.0.0.1`; `.env.example` documents "do not bind 0.0.0.0"; Vite dev/preview bind `127.0.0.1` |
| No broad process termination | `stop.ps1` verifies PID **and** command line ownership; no `Stop-Process -Name`, no `taskkill /IM`, no port-based kill; static tests assert absence of these idioms |
| No weakened machine security | No `Set-ExecutionPolicy` / unrestricted / registry edits in any script; `npm.cmd` used instead (static test) |
| Honest health reporting | `/health` never fabricates `ok` for an unimplemented dependency; a DB failure yields `degraded` without leaking paths or exception text (tested) |
| No fabricated evidence | Every number in this report came from the commands in §7; nothing in §7.3 is presented as a pass |
| Educational notice | `REQ-SEC-05` string is fixed in `version.py`, `schemas`, generated OpenAPI (`info.x-demo-notice`) and the UI banner |

`/openapi.json` exposes only two public read-only endpoints; there is no write endpoint, no
authentication surface and therefore no privilege boundary to break in P1.

---

## 9. Test inventory (P1 suites)

| File | Tests | What it protects |
|---|---|---|
| `test_health.py` | 9 | HTTP 200, contract keys/enums, `db=ok` when migrated, `degraded` + no leak when not, honest `not_configured`, disclaimer, determinism, no clinical fields |
| `test_version.py` | 7 | Contract fields, real-or-`unknown` SHA, explicit `APP_GIT_SHA`, determinism, no secrets/paths, malformed SHA rejected |
| `test_openapi.py` | 6 | Only `/health` + `/version`; served schema; `Health`/`VersionInfo`/`DependencyState` parity with P0; notice; public ops |
| `test_database.py` | 9 | Baseline table + revision, no P2 tables, upgrade/downgrade/upgrade, `schema_meta` roundtrip, CHECK constraint, `PRAGMA foreign_keys`, directory creation, `:memory:` untouched, relative URL anchored to repo root |
| `test_safety_guards.py` | 7 | Forbidden imports and clinical vocabulary absent, route surface, notice constant, no tracked artifacts, `.env.example` has no secret values, honest dependencies |
| `test_powershell_scripts.py` | 67 (parametrised) | Script presence, helper dot-sourcing, root anchoring, no unsafe kill idioms, no policy weakening, `npm.cmd` only, ownership-checked stop with verified child-tree collection, state file, helper scripts exist, ASCII-only, no TODO markers; plus the P1-R06 exit-code pipeline, P1-R07 role classifiers, and P1-R08 verdict-before-deletion ordering |
| `test_ci_workflow.py` | 16 | YAML/jobs/triggers, Python 3.12 + Node 22, no model/GPU/secrets/services, read-only permissions, every gate invoked, timeouts, lock pins + hashes, no wildcards, runtime/dev separation, pyproject↔lock parity, no npm ranges, lockfile v3 |

Backend total: **121 passed**.

Frontend: `tests/HealthPage.test.tsx` — 9 tests (loading with a never-settling request,
loading→error transition, dependency render, versions, notice, degraded badge,
unreachable-backend error card, retry recovery, no clinical vocabulary);
`tests/config.test.ts` — 4 tests (dev + preview proxy entries, loopback binding/ports,
backend default). Frontend total: **13 passed**, zero `act(...)` warnings.

Browser: `tests/e2e/health.spec.ts` — 1 smoke test, **never executed anywhere** (§13.4);
it reports `1 skipped` with the missing prerequisite rather than a false result.

PowerShell regression scripts (executed by the owner on Windows, §13.1):
`invoke_native.tests.ps1` — **14 checks**; `stop_identity.tests.ps1` — **38 checks**.

---

## 10. Open questions, risks and limitations

| ID | Item | Proposed default |
|---|---|---|
| `P1-OPEN-01` | Project license still unset (`DEPENDENCIES.md` §7). `pyproject.toml` deliberately declares none. | Owner chooses before P2 (or explicitly defers to P8). |
| `P1-OPEN-02` | `docs/**` additions (this report, `docs/runbooks/WINDOWS_SETUP.md`) plus the `PHASE_PROGRESS.md` row are outside the literal P1 path list in `AGENTS.md` §5, but item 10 of the P1 brief requires them. | **Owner acknowledgement requested** in the PR. No other doc was edited. |
| `P1-OPEN-03` | `DEPENDENCIES.md` records "nothing pinned" (P0 text); this report supersedes it for P1. | Owner decides whether to synchronise the P0 document now or at P2. |
| `P1-OPEN-09` | **Closed** — the owner committed `.github/workflows/ci.yml` at `6d09b66`; both Actions jobs are green. | Resolved. |
| `P1-OPEN-10` | **Closed** — the owner executed every PowerShell fix on Windows at `eec6642`: 14/14 and 38/38 regression checks, `test_all.ps1` 12 PASS / 0 FAIL / 1 SKIP, and live start/stop on both the normal and space-containing paths (§13). | Resolved. |
| `P1-OPEN-11` | **Closed** — the shutdown fix was exercised against a live Windows process tree: backend PID 13516 plus frontend root PID 11860 and verified descendant PID 7156 stopped, both ports free, all three tracking files removed (§13.3). | Resolved. |
| `P1-OPEN-12` | The **incomplete**-shutdown path (`exit 2`, tracking kept) is verified by the executable script cases 12–15 and a Python port, but was not reproduced on Windows — the owner's runs all ended cleanly. | Optional: reproduce with the `http.server` squatter recipe in `WINDOWS_SETUP.md` §5. Non-blocking. |
| `P1-OPEN-04` | `pydantic-settings` reads `.env` from the repo root only. A second `.env` in a subdirectory is ignored. | Keep single-root configuration. |
| `P1-OPEN-05` | `git_sha` falls back to `unknown` outside a git checkout (e.g. a source zip). CI sets `APP_GIT_SHA` explicitly. | Accepted; document in `setup.ps1` output if it matters. |
| `P1-OPEN-06` | Vite 7 / TypeScript 5.9 chosen over the newest majors (8 / 7) for toolchain stability. | Revisit only with a re-run of the full gate. |
| `P1-OPEN-07` | `npm install` on npm 10.9.8 crashed for one experimental dependency set. The final pinned set is clean, but npm 11.17 (owner) may behave differently — `package-lock.json` pins the tree, so `npm ci` is the supported path. | Use `npm.cmd ci` (what `setup.ps1` does when a lock exists). |
| `P1-OPEN-08` | No `LICENSE` file, therefore no copyright header convention. | Owner decision with `P1-OPEN-01`. |

---

## 11. Rollback

1. `stop.ps1` (nothing keeps running).
2. `Remove-Item -Recurse -Force .\data\runtime, .\.venv, .\frontend\node_modules; Remove-Item .\.env`.
3. On `main`: `git revert --no-commit <merge-sha> && git commit` — the change is purely additive
   (one `.gitignore` replacement) so a revert restores the P0 tree exactly; no database migration
   touches existing data because P1 creates the first one.
4. No external system, paid service or cloud resource was provisioned, so nothing else needs
   cleanup.

---

## 12. Owner review checklist

Items marked **[x]** were verified by the owner on Windows at `eec6642` (§13);
the tick reflects the owner's own reported evidence, not an agent claim.

- [x] Base commit is `a33e693ba16560836312351787769ec5ee18b469` and the branch is `arena/d86c4f98-ai-doctor-followup-agent`.
- [x] Changed-file list (§2) matches the PR diff; no file outside the P1 scope (plus `P1-OPEN-02`).
- [x] `git diff main -- .gitignore .env.example` reviewed: no secret, no path outside the repo.
- [x] `preflight.ps1` → `setup.ps1` → `test_all.ps1` run on the laptop — `test_all.ps1` **12 PASS / 0 FAIL / 1 SKIP**.
- [x] `/health` returns 200 with `db=ok`; `/version` shows `api_version=v1` and a real SHA.
- [x] `http://127.0.0.1:5173/` loads the status page, shows the notice banner and no error card.
- [x] `alembic current` → `0001_p1_baseline`; `data\runtime\app.db` exists and is gitignored.
- [x] `stop.ps1` leaves ports 8000/5173 free and stops nothing else — on **both** the normal and the space-containing path.
- [x] CI workflow added by the owner (§7.5); run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) is green.
- [x] `git ls-files | Select-String -Pattern '\.env$|\.db$|node_modules'` returns nothing.
- [ ] **Open:** scope question `P1-OPEN-02` explicitly accepted or rejected.
- [ ] **Open:** decide `P1-OPEN-01` (license) before P2.
- [ ] **Open:** explicit owner approval of P1 and the merge itself.
- [ ] **Open (optional):** run the Playwright smoke with `-IncludeE2E` if you want that gate executed (§13.4).

**Phase status: `IN_REVIEW`. Owner approval is pending and the merge SHA is unset.**
The agent did not merge, did not self-approve and did not start P2. Merging and phase
acceptance are owner decisions (`AGENTS.md` §2).

---

## 13. Owner Windows verification — final appendix

This appendix records evidence **produced by the project owner on Windows**, reported in
PR #4 review `5905950006` and the accompanying owner notes. The agent did not execute any
of it and did not synthesize any figure below. Everything is at head
**`eec6642ba700be25f8be1d645bb099f51a665441`**.

**Environment:** Windows PowerShell **5.1.22621.4249**, Python **3.12.9**, Node
**24.15.0**, npm 11.17.0.

### 13.1 Quality gate and regression suites

| Check | Result |
|---|---|
| `scripts\powershell\test_all.ps1` | **12 PASS / 0 FAIL / 1 SKIP** — `test_all result: PASS` |
| `scripts\powershell\tests\invoke_native.tests.ps1` | **14 checks PASS** — `Invoke-Native tests: PASS (14 checks)` |
| `scripts\powershell\tests\stop_identity.tests.ps1` | **38 checks PASS** — `Stop identity tests: PASS (38 checks)` |
| `scripts\powershell\preflight.ps1` | **PASS** |
| `scripts\powershell\setup.ps1` | **PASS** (86.4 s from the space-containing path; clean Python 3.12.9 `.venv`, hash-locked dependencies, editable backend import, Alembic baseline, `npm ci`) |

The single `SKIP` is the **optional** Playwright browser smoke test — see §13.4.

The 14-check total is the sum of the executable assertions in `invoke_native.tests.ps1`
(10 direct `Assert-True` calls, 4 of them reached through the `Test-SingleInteger` helper).
The 38 are the direct assertions in `stop_identity.tests.ps1`. Both match the committed
sources.

### 13.2 Live lifecycle — normal repository path

| Step | Result |
|---|---|
| `start.ps1` | **Start result: PASS** |
| `GET /health` | HTTP **200**, `status=ok`, `db=ok`, `ollama=not_configured`, `tesseract=not_configured` |
| `GET /version` | `app_version=0.1.0`, `api_version=v1`, real git SHA |
| Frontend page | Rendered with Database OK, correct versions and the educational notice |
| `stop.ps1` | **PASS** — backend and frontend stopped, both ports free |
| Tracking files after stop | `run-state.json`, `backend.pid`, `frontend.pid` all **removed** |

### 13.3 Live lifecycle — path containing spaces

A separate detached worktree at `E:\DEPI\AI Doctor FollowUp Agent Space Test` was used,
so the primary checkout was not touched.

| Step | Result |
|---|---|
| `setup.ps1` from the spaced path | **PASS**, exit **0** (86.4 s). The npm `esbuild` allow-scripts warning was non-fatal |
| Ports before start | Free |
| `start.ps1 -NoBrowser` | **Start result: PASS**; backend PID **13516**, frontend PID **11860**; GET `/health` HTTP **200**; GET `/` HTTP **200**; the exact space-containing root appeared in the logs and there was **no `--app-dir` splitting or import error** |
| `stop.ps1` | **Stop result: PASS — 2 stopped, ports 8000 and 5173 are free**, exit **0**. Backend PID 13516 stopped; frontend root PID 11860 **and verified descendant PID 7156** stopped |
| `Get-NetTCPConnection -LocalPort 8000,5173 -State Listen` afterwards | **No listeners** |
| `run-state.json`, `backend.pid`, `frontend.pid` afterwards | Each verified **absent** |

This closes **P1-R03** (argument quoting for spaced paths), **P1-R06** (exit-code
pipeline), **P1-R07** (wrapper/descendant identity) and **P1-R08** (tracking preserved
until the outcome is decided) with real Windows runtime evidence rather than static
analysis.

> The owner's testing worktree should be removed only after confirming it holds no data
> worth retaining. This does not affect the primary checkout or any git ref.

### 13.4 Optional Playwright smoke test — **NOT EXECUTED**

The browser smoke test remains the **one** check in P1 that was never executed anywhere.

- Browsers are not installed by `setup.ps1` and are not committed (≈ 150 MB download).
- Installation failed in the authoring sandbox (`Download failure, code=1`; the browser
  CDN is outside the allowed egress set), and binaries were not installed for the owner's
  run, so `test_all.ps1` reported the gate as `SKIP`.
- The behaviour is honest by construction: `tests/e2e/health.spec.ts` checks the backend
  precondition and the presence of `chromium.executablePath()` before running, and reports
  **`1 skipped`** with the reason rather than a false pass or a confusing launch error.

**This is not a blocker.** The gate is explicitly optional (`-IncludeE2E`), and the page
it would verify was confirmed rendering on the owner's laptop by direct browser load
(§13.2). To execute it: `cd frontend; npx playwright install chromium; cd ..;
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1 -IncludeE2E`.

### 13.5 Remaining non-blocking limitations

| # | Limitation | Impact |
|---|---|---|
| 1 | Playwright browser smoke never executed (§13.4) | None for acceptance — optional gate; page verified manually |
| 2 | Python locks are **universal** resolutions; the installed wheel set is platform-specific and hash-verified, but there is no offline mirror | A future install needs network access |
| 3 | `pydantic-settings` reads `.env` from the repository root only | Documented; no multi-env requirement in P1 |
| 4 | `git_sha` reports `unknown` outside a git checkout; CI sets `APP_GIT_SHA` | Cosmetic in exported tarballs |
| 5 | Vite 7 / TypeScript 5.9 are deliberate choices over the newest majors (Vite 8 pulls the rolldown toolchain; `typescript-eslint` 8 does not support TypeScript 7) | None in P1; revisit in a later phase |
| 6 | Project licence still undecided (`P1-OPEN-01`) | Owner decision, does not block P1 acceptance |
| 7 | `docs/contracts/DEPENDENCIES.md` still says "nothing pinned" (`P1-OPEN-03`) | P0 document left untouched on purpose; this report supersedes it for the P1 set |
| 8 | Documentation additions outside the literal P1 path list in `AGENTS.md` §5 (`P1-OPEN-02`) | Requires explicit owner acknowledgement |
| 9 | Node 24.15.0 on the owner's machine vs Node 22 in CI | Both satisfy Vite 7's `^20.19.0 \|\| >=22.12.0`; the gate passed on 24.15.0 |

### 13.6 Phase disposition

**`IN_REVIEW`. Owner approval is PENDING. The merge SHA is deliberately unset.**

| Item | State |
|---|---|
| Implementation | Complete — 13/13 deliverables |
| Functional findings P1-R01…R09 | Addressed |
| Windows runtime validation | **Passed** (§13.1–§13.3) |
| GitHub Actions | **Green** — run `43615782079` |
| Owner approval | **Pending** |
| Merge | **Not merged**; `main` is unchanged at `a33e693` |
| P2 | **Not started** |

Nothing in this appendix may be read as an approval, and no future result has been
claimed: the merge SHA does not exist yet.
