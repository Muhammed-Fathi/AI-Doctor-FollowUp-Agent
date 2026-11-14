# Phase 1 Report — Foundation and Reproducible Startup

| Field | Value |
|---|---|
| Report ID | `REPORT-P1-001` |
| Phase | **P1 only** — repository foundation, reproducible startup, `/health` + `/version`, frontend status page, SQLite + Alembic baseline, Windows scripts, CI |
| Status | **IN_REVIEW — submitted for owner review; not accepted, not merged, not `PASS`** |
| Branch | `arena/d86c4f98-ai-doctor-followup-agent` |
| Base commit | `a33e693ba16560836312351787769ec5ee18b469` (verified `main` HEAD before any change) |
| Head commit | recorded in the PR description (this file is committed with it) |
| Pull request | open against `main`, title `P1: Foundation and reproducible local startup` |
| Author | Arena agent (implementer) |
| Reviewer | Project owner (pending) |

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
| 6 | Five Windows PowerShell scripts | **Implemented — not executed** | `scripts/powershell/` (see §7) |
| 7 | `.env.example`, strict `.gitignore`, no committed secrets/artifacts | **Complete and scanned** | `.env.example`, `.gitignore`, `scripts/python/scan_repository.py` |
| 8 | Deterministic tests, Ruff, build validation, Alembic smoke | **Complete and executed** | `backend/tests/`, `frontend/tests/`, `test_all.ps1` gates |
| 9 | Minimal GitHub Actions CI, no model/GPU/paid API | **INCOMPLETE — workflow prepared but could not be pushed** (GitHub App token lacks the `workflows` permission). Full file included in the PR description for the owner to add. | workflow content in the PR body; not present on the branch |
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

Environment: Linux sandbox, Debian 12, Python **3.11.2**, Node **22.22.3**, npm 10.9.8, git 2.39.5.
The repository virtual environment lives at `.venv/` (gitignored).

### 7.1 Executed and passed

| # | Command | Exit | Observed result |
|---|---|---|---|
| 1 | `git log --oneline -1` | 0 | `a33e693 Merge pull request #3 …` — base commit verified before any change |
| 2 | `.venv/bin/python -V` | 0 | `Python 3.11.2` (see §5.4: not the 3.12 target) |
| 3 | `.venv/bin/pip install --require-hashes -r requirements/requirements.lock` (fresh venv, other venv) | 0 | resolved and installed all 20 hashed pins |
| 4 | `.venv/bin/pip install --require-hashes -r requirements/requirements-dev.lock` (fresh venv) | 0 | all 35 hashed pins installed |
| 5 | `pip install -e . --no-build-isolation --no-deps` (throwaway copy with `requires-python >=3.11`) | 0 | `import app` succeeded from an unrelated CWD (the real repo correctly refuses to install on 3.11 due to `requires-python`) |
| 6 | `python -m pytest -q` | 0 | `103 passed` (94 at the first submission + 9 review-fix tests) |
| 7 | `python -m pytest <file> -q` per suite | 0 | health 9, version 7, openapi 6, database 9, safety 7, powershell 49 (parametrised), CI 16 |
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
| 24 | `npm test` (vitest + jsdom) | 0 | `2 passed (2)` files, `12 passed (12)` tests |
| 25 | `npm run build` (`tsc --noEmit && vite build`) | 0 | `34 modules transformed`; `dist/index.html 0.75 kB`, `index-*.css 4.25 kB`, `index-*.js 228.22 kB (gzip 71.43 kB)` |
| 26 | `npm run dev -- --host 127.0.0.1 --port 5173` then `curl http://127.0.0.1:5173/` | 0 | dev server ready in 168 ms; HTML served |
| 27 | `curl http://127.0.0.1:5173/health` and `/version` (Vite dev proxy) | 0 | both HTTP 200 with the same JSON as the backend — the page's data path is proven, not just the API |
| 27a | `npm run preview -- --port 4173` then `curl http://127.0.0.1:4173/`, `/health`, `/version` | 0 | production build served (HTTP 200) and both endpoints proxied — this is the exact server the Playwright smoke test drives |
| 28 | `python -c "yaml.safe_load(ci.yml)"` | 0 | `jobs: ['backend', 'frontend']` |
| 29 | **Clean-clone reproducibility**: `git clone <branch>` into a fresh directory, then a fresh `python3.11 -m venv` + `pip install --require-hashes -r requirements/requirements-dev.lock` | 0 | lock installed from scratch; `pytest -q` -> `103 passed`; `ruff check .` + `ruff format --check .` clean; `check_openapi.py` PASS; `scan_repository.py` PASS (94 files); `alembic upgrade head` + `check_alembic_smoke.py` PASS |
| 30 | Same clean clone: `npm ci --no-audit --no-fund` | 0 | `added 235 packages`; `npm run lint` clean; `npm test` -> 12 passed; `npm run build` -> built in 1.48 s |

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

### 7.3 Not executed — and why

| Check | Reason |
|---|---|
| **All five PowerShell scripts** (`preflight`, `setup`, `start`, `stop`, `test_all`) | No PowerShell and no Windows in this environment. Only static properties are tested (`test_powershell_scripts.py`). **Linux results are not evidence that these scripts work.** |
| **The Python suite on Python 3.12** | The sandbox has Python 3.11.2; obtaining 3.12 was impossible (the python-build-standalone release host is not in the allowed egress set). CI runs the same suite on 3.12 and is the first 3.12 execution. |
| **GitHub Actions run** | The workflow file could not be pushed at all (§7.5). No run exists yet; the owner must add the file (copy from the PR body) and then the run is observable. |
| **Playwright browser smoke** | `npx playwright install chromium` fails (`Download failure, code=1`) because the browser CDN is outside the allowed egress set. The spec now self-guards both preconditions and the run reports `1 skipped` (verified: `npx playwright test` -> `1 skipped`), so it never fakes a pass or a failure. `test_all.ps1` reports the gate as `SKIP` with the reason. |
| **`test_all.ps1` end-to-end** | Same reason as the PowerShell row; each underlying command it calls was executed individually here. |

### 7.4b Re-verification at the submitted head

Re-run after the review fixes, at head `a20c536` on a clean working tree:

| Command | Exit | Observed |
|---|---|---|
| `python -m pytest` | 0 | `103 passed` |
| `ruff check .` | 0 | `All checks passed!` |
| `ruff format --check .` | 0 | `27 files already formatted` |
| `python scripts/python/check_openapi.py` | 0 | `PASS (2 paths, 3 schemas)` |
| `python scripts/python/scan_repository.py` | 0 | `PASS (94 tracked files)` |
| `alembic upgrade head` / `downgrade base` / `upgrade head` | 0 | all three steps exit 0; `check_alembic_smoke.py` PASS |
| `alembic -c <abs path>` from `/tmp` | 0 | migration applied (CWD independence) |
| `uvicorn … --port 8000` then `curl /health` | 0 | **200**, `status=ok`, `db=ok` |
| `curl /version` | 0 | `api_version=v1`, `git_sha=a20c536…` (the real head) |
| `curl /openapi.json`, `/docs` | 0 | only `/health` + `/version`; notice present; docs UI 200 |
| `npm run lint` / `npx tsc --noEmit` | 0 | clean |
| `npm test` | 0 | `12 passed` (2 files) |
| `npm run build` | 0 | built in 1.31 s |
| dev server `:5173` -> `/`, `/health`, `/version` | 0 | 200, 200, 200 (proxy proven) |
| preview server `:4173` -> `/`, `/health`, `/version` | 0 | 200, 200, 200 (production build + proxy) |
| `npx playwright test` | skipped | `1 skipped` — chromium not installed (honest, not a failure) |

Repository audit at the same head: `git ls-files` contains no `.env`, database, log, PID file,
`node_modules`, `.venv` or `dist`; the secret/artefact scan reports 0 findings; the backend contains
none of `langgraph`, `ollama`, `pytesseract`, `pypdf`, `smtplib`, `sendgrid`, `twilio`, `requests`,
`httpx`, `aiohttp`.

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

### 7.5 CI workflow delivery — RESOLVED by the owner (commit `6d09b66`)

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

**Resolution for the owner (one minute):** the complete workflow file is included verbatim
in the PR description. Add it at `.github/workflows/ci.yml` on the branch (GitHub's web
editor is enough) or grant the session app the `workflows` permission and re-run the agent.
Until then:

* **no GitHub Actions run exists** — the CI acceptance criterion is *not* met,
* every command the workflow would run was executed manually (§7.1 items 3–10, 20–25),
* `test_all.ps1` is the local equivalent gate for the owner's laptop.

### 7.4 Requires owner Windows laptop

See `docs/runbooks/WINDOWS_SETUP.md` §5 for the exact command list. Summary: `preflight.ps1`,
`setup.ps1` (clean install reproduciblity), `start.ps1` + `/health` HTTP 200, browser load of
`http://127.0.0.1:5173/`, Alembic `current`/`history`, `test_all.ps1`, and `stop.ps1` leaving
ports 8000/5173 free.

---

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
| `test_powershell_scripts.py` | 40 (parametrised) | Script presence, helper dot-sourcing, root anchoring, no unsafe kill idioms, no policy weakening, `npm.cmd` only, ownership-checked stop with verified child-tree collection, state file, helper scripts exist, ASCII-only, no TODO markers |
| `test_ci_workflow.py` | 16 | YAML/jobs/triggers, Python 3.12 + Node 22, no model/GPU/secrets/services, read-only permissions, every gate invoked, timeouts, lock pins + hashes, no wildcards, runtime/dev separation, pyproject↔lock parity, no npm ranges, lockfile v3 |

Frontend: `tests/HealthPage.test.tsx` — 8 tests (loading, dependency render, versions, notice,
degraded badge, unreachable-backend error card, retry recovery, no clinical vocabulary);
`tests/config.test.ts` — 4 tests (dev + preview proxy entries, loopback binding/ports, backend
default).
Browser: `tests/e2e/health.spec.ts` — 1 smoke test, **not executed here**.

---

## 10. Open questions, risks and limitations

| ID | Item | Proposed default |
|---|---|---|
| `P1-OPEN-01` | Project license still unset (`DEPENDENCIES.md` §7). `pyproject.toml` deliberately declares none. | Owner chooses before P2 (or explicitly defers to P8). |
| `P1-OPEN-02` | `docs/**` additions (this report, `docs/runbooks/WINDOWS_SETUP.md`) plus the `PHASE_PROGRESS.md` row are outside the literal P1 path list in `AGENTS.md` §5, but item 10 of the P1 brief requires them. | **Owner acknowledgement requested** in the PR. No other doc was edited. |
| `P1-OPEN-03` | `DEPENDENCIES.md` records "nothing pinned" (P0 text); this report supersedes it for P1. | Owner decides whether to synchronise the P0 document now or at P2. |
| `P1-OPEN-09` | **Closed** — the owner committed `.github/workflows/ci.yml` at `6d09b66`; both Actions jobs are green. | Resolved. |
| `P1-OPEN-10` | The PowerShell **fix** in this revision (R03/R05/R06) has not itself been executed on Windows; PowerShell is unavailable in this sandbox and the `pwsh` release asset host is outside the allowed egress set. | Owner re-runs `invoke_native.tests.ps1` and `test_all.ps1` on Windows before acceptance. |
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

- [ ] Base commit is `a33e693ba16560836312351787769ec5ee18b469` and the branch is `arena/d86c4f98-ai-doctor-followup-agent`.
- [ ] Changed-file list (§2) matches the PR diff; no file outside the P1 scope (plus `P1-OPEN-02`).
- [ ] `git diff main -- .gitignore .env.example` reviewed: no secret, no path outside the repo.
- [ ] `preflight.ps1` → `setup.ps1` → `test_all.ps1` run on the laptop; paste real output into the PR.
- [ ] `/health` returns 200 with `db=ok`; `/version` shows `api_version=v1` and a real SHA.
- [ ] `http://127.0.0.1:5173/` loads the status page, shows the notice banner and no error card.
- [ ] `alembic current` → `0001_p1_baseline`; `data\runtime\app.db` exists and is gitignored.
- [ ] `stop.ps1` leaves ports 8000/5173 free and stops nothing else.
- [ ] CI workflow added by the owner (§7.5) and the resulting run is green (paste the run URL).
- [ ] `git ls-files | Select-String -Pattern '\.env$|\.db$|node_modules'` returns nothing.
- [ ] Scope question `P1-OPEN-02` explicitly accepted or rejected.
- [ ] Decide `P1-OPEN-01` (license) before P2.

**Phase status: `IN_REVIEW`.** The agent did not merge, did not self-approve and did not start P2.
Merging and phase acceptance are owner decisions (`AGENTS.md` §2).
