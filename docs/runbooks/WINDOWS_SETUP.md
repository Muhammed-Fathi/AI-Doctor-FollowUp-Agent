# Windows Setup, Run and Test Guide (Phase 1)

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**
> This guide covers the Phase 1 *foundation* only: environment setup, the FastAPI
> service with `/health` and `/version`, the React status page, SQLite + Alembic
> and the quality-gate scripts. No patient data, no OCR, no model, no workflow.
>
> **Verification status of this document.** Every command below was *designed*
> against the merged P0 contracts and the implemented P1 code. The Python,
> frontend and database commands were executed in the authoring Linux sandbox
> (Python 3.11.2, Node 22.22.3 — see `docs/phase-reports/PHASE_1_REPORT.md` §6).
> The PowerShell commands were **not executed anywhere**: the sandbox has no
> PowerShell and no Windows. They must be verified on the owner's laptop
> (`E:\DEPI\AI-Doctor-FollowUp-Agent`) before P1 acceptance.

---

## 1. Prerequisites (owner machine, verified 2026-11-14)

| Component | Required | Owner's observed value | Notes |
|---|---|---|---|
| Windows | 10/11 | Windows (verified) | PowerShell 5.1 or 7.x |
| Python | **3.12.x** | `3.12.9` via `py -3.12` | Python 3.14 is the machine default — never use bare `python` |
| pip | any recent | `25.3` | upgraded by `setup.ps1` |
| Node.js | `^20.19.0` or `>=22.12.0` | `24.15.0` | Vite 7 engine constraint |
| npm | ships with Node | `11.17.0` | **call `npm.cmd`**, never `npm` |
| Git | any recent | `2.50.0.windows.2` | used for `/version` SHA detection |
| Free disk | ≥ 2 GB (5 GB+ recommended) | ≈ 71 GB on `E:` | venv + node_modules ≈ 400 MB |

**PowerShell execution policy.** `npm` resolves to `npm.ps1`, which the machine
policy blocks. Every script in this repository calls `npm.cmd` directly and uses
`-NoProfile -ExecutionPolicy Bypass -File` at the *invocation* boundary only.
Nothing weakens the machine-wide policy and no `Set-ExecutionPolicy` is issued.

**Keeping dependencies off `C:`.** Point the virtual environment at `E:` before
running setup:

```powershell
$env:APP_VENV_DIR = 'E:\AI-Doctor-FollowUp-Agent\.venv'
```

`node_modules` always stays inside `frontend\` (npm has no external option);
both `frontend\node_modules` and any `.venv` are gitignored.

---

## 2. First-time setup

```powershell
cd E:\DEPI\AI-Doctor-FollowUp-Agent

# 1. Read-only readiness check (changes nothing)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\preflight.ps1

# 2. Install (idempotent; safe to re-run)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1
```

`setup.ps1` performs, in order:

1. verifies `py -3.12` really is 3.12.x;
2. creates `.env` from `.env.example` **only if missing**;
3. creates the virtual environment (`<repo>\.venv` or `$env:APP_VENV_DIR`);
4. installs `requirements\requirements.lock` and `requirements\requirements-dev.lock`
   with `--require-hashes` (tampered or substituted artifacts fail the install);
5. installs the backend package in editable mode;
6. creates `data\runtime\` and applies the Alembic baseline (`upgrade head`);
7. installs frontend dependencies with `npm.cmd ci` (or `npm.cmd install` when the
   lock file is absent).

Exit code `0` = success, `1` = failure with the failing step printed. Nothing is
installed outside the repository except the tooling already on the machine.

Useful flags: `-SkipFrontend`, `-SkipDatabase`, `-Clean` (recreate venv and
`node_modules`; `data\runtime` is never deleted).

---

## 3. Start and stop

```powershell
# Start backend (8000) + frontend dev server (5173)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1

# Backend only, without opening a browser
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1 -BackendOnly -NoBrowser
```

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8000/health` | Liveness + dependency state (JSON) |
| `http://127.0.0.1:8000/version` | Build/contract versions (JSON) |
| `http://127.0.0.1:8000/docs` | Generated OpenAPI UI |
| `http://127.0.0.1:5173/` | React status page (proxies `/health`, `/version`) |

`start.ps1` writes `data\runtime\run-state.json` (PIDs + verified command lines)
and refuses to start when the application is already running or when port 8000 /
5173 belongs to another process. It never terminates a process it did not start.

```powershell
# Stop only the processes start.ps1 recorded
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1
```

`stop.ps1` re-reads each PID's command line and stops it only when it still
belongs to this repository's uvicorn/vite process. Without
`data\runtime\run-state.json` it stops **nothing** and says so.

Logs (gitignored): `data\runtime\backend.out.log`, `backend.err.log`,
`frontend.out.log`, `frontend.err.log`.

---

## 4. Quality gate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1
```

Gates, in order — each prints `PASS`, `FAIL` or `SKIP` and the script exits
non-zero if anything fails:

| # | Gate | Command it runs |
|---|---|---|
| 1 | Ruff lint | `ruff check .` |
| 2 | Ruff format | `ruff format --check .` |
| 3 | Backend tests | `python -m pytest -q` |
| 4 | Alembic smoke | `upgrade head` → `downgrade base` → `upgrade head` on a temp DB |
| 5 | OpenAPI surface | `python scripts\python\check_openapi.py` |
| 6–9 | Frontend | `npm.cmd run typecheck`, `lint`, `test`, `build` |
| 10 | Browser smoke (optional) | `npm.cmd run test:e2e` with `-IncludeE2E` |
| 11 | Secret/artifact scan | `python scripts\python\scan_repository.py` |

Skipped gates are never counted as passes. `-BackendOnly` restricts the run to
the Python gates.

### Optional browser smoke test

Playwright browser binaries are **not** installed by `setup.ps1` and are not
committed (≈ 150 MB download):

```powershell
cd frontend
npx playwright install chromium      # one-off, needs network
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1 -IncludeE2E
```

Without the binaries, or without the backend running, `test_all.ps1` reports the
browser gate as `SKIP` with the reason — it never reports a false pass.

---

## 5. Manual verification checklist (owner laptop)

Run each command, record the real output, and attach it to the P1 PR review.

```powershell
# 1. Interpreter selection
py -3.12 -V                                  # expect: Python 3.12.x

# 2. Clean install from a fresh clone
git clone https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent.git E:\DEPI\AI-Doctor-FollowUp-Agent
cd E:\DEPI\AI-Doctor-FollowUp-Agent
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\preflight.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1

# 3. Database + migration
.\.venv\Scripts\python.exe -m alembic -c backend\migrations\alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend\migrations\alembic.ini history

# 4. Start, then in a second terminal:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1
Invoke-RestMethod http://127.0.0.1:8000/health       # expect db=ok, status=ok
Invoke-RestMethod http://127.0.0.1:8000/version      # expect api_version=v1
(Invoke-WebRequest http://127.0.0.1:8000/health).StatusCode   # expect 200

# 5. Browser: http://127.0.0.1:5173/ shows "Foundation status",
#    a green Database badge, "Not configured in Phase 1" for ollama/tesseract,
#    the version block, and the educational notice banner.

# 6. Quality gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1

# 7. Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue
```

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `py -3.12` not found | Python 3.12 or the Python Launcher not installed | Install Python 3.12 with the launcher; do not rely on `python` (3.14) |
| `npm.ps1 cannot be loaded because running scripts is disabled` | You typed `npm` instead of `npm.cmd` | Use `npm.cmd`, or run `powershell -NoProfile -ExecutionPolicy Bypass -File <script>` |
| `setup.ps1` fails with `--require-hashes` | Lock file and a dependency drifted | Do not edit the lock by hand; report it in the PR |
| Port 8000 in use | A previous run is still alive | `stop.ps1`; if it is not our process, the script tells you and refuses |
| `/health` returns `db: "unavailable"` | Migration was never applied | `setup.ps1` or `python -m alembic upgrade head` |
| Frontend shows "Backend unreachable" | Backend not running | `start.ps1 -BackendOnly`, then reload |
| `ruff format --check .` fails | Formatting drift | `ruff format .` and commit |
| `npm ci` fails after dependency changes | `package-lock.json` out of date | `npm install` in `frontend\`, commit the lock |

---

## 7. What this guide intentionally does not cover

Not available in Phase 1, because the code does not exist yet: authentication,
patient records, document upload/OCR, monitoring comparisons, review rules,
LangGraph agents, local model drafting, follow-up tasks, external messaging and
any clinical feature. Those arrive in P2–P8 and each brings its own setup steps.

## 8. Rollback

```powershell
# Stop the application
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1

# Remove generated state (keeps source and docs)
Remove-Item -Recurse -Force .\data\runtime
Remove-Item -Recurse -Force .\.venv           # or $env:APP_VENV_DIR
Remove-Item -Recurse -Force .\frontend\node_modules
Remove-Item -Force .\.env

# Revert the phase on the branch
git checkout main
git branch -D arena/d86c4f98-ai-doctor-followup-agent
```
