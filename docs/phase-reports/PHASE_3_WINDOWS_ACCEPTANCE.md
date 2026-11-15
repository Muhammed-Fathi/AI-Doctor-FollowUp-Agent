# P3 Windows acceptance — executable handoff

**Status of this document: a procedure, not a result.** Nothing in it has been
executed by the implementing agent. The sandbox has no Windows, no Tesseract
engine and a Python 3.11 interpreter, so every gate below is **NOT RUN** until the
owner executes it and records the output.

- Branch: `arena/ce85d4e6-ai-doctor-followup-agent`
- PR: [#10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) — **draft, open**
- Phase: **`IN_REVIEW`** — no PASS, no merge, no P4/P5
- Reference head when this was written: see the commit this file landed in. Confirm
  with `git rev-parse HEAD` before recording evidence.

**Never run these steps against your existing `main` checkout or its
`data/runtime/app.db`.** Every step below works in a separate worktree with its own
database, upload directory and virtual environment.

---

## 0. What "PASS" means here

| Mark | Meaning |
|---|---|
| `PASS` | The command ran and its output matched the stated expectation. Paste the output. |
| `FAIL` | It ran and did not match. Paste the output; that is a release blocker. |
| `NOT RUN` | It did not run, or a prerequisite was missing. **Not** a pass, **not** a failure of the code. |

The acceptance script in step 7 emits exactly these three words and exits `2` if
any gate is not `PASS`, so a truncated log cannot be mistaken for acceptance.

---

## 1. Prerequisites (verify, do not install silently)

```powershell
# From any shell. Read-only.
py -3.12 --version                          # must print Python 3.12.x
git --version
node --version                              # Node 22, only needed for the full gate
```

Tesseract for Windows (UB Mannheim build is the usual choice):

```powershell
# After installing, confirm BOTH the executable and the language data.
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
# Expect: eng
Get-ChildItem "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" | Select-Object FullName, Length
```

Record: engine version, `--list-langs` output, and the `eng.traineddata` size. If
`--list-langs` does not list `eng`, the OCR gates below cannot pass and that is a
**release blocker**, not something to work around by lowering a threshold.

---

## 2. Isolated worktree (your `main` checkout is not touched)

```powershell
$Repo    = 'C:\src\AI-Doctor-FollowUp-Agent'          # your existing clone
$Branch  = 'arena/ce85d4e6-ai-doctor-followup-agent'
$Accept  = 'C:\src\p3-acceptance'                     # new, disposable

git -C $Repo fetch origin
git -C $Repo worktree add $Accept $Branch
git -C $Accept rev-parse HEAD                          # record this SHA as the tested head
git -C $Accept status --porcelain                      # expect: empty
```

The worktree shares the Git object store but has its **own** working files, so:

- `data/runtime/` inside `$Accept` is new and empty — your demo database is not
  visible from it and cannot be mutated by these steps.
- `.git` is a file pointing back at the main checkout; do not delete it manually.
- To remove it afterwards: `git -C $Repo worktree remove $Accept`.

---

## 3. Python 3.12 hash-locked runtime

The lock files are hash-pinned; a hash mismatch fails the install loudly, which is
the point.

```powershell
Set-Location $Accept

# Keep the venv inside the worktree so removing the worktree removes it too.
$env:APP_VENV_DIR = "$Accept\.venv"
py -3.12 -m venv $env:APP_VENV_DIR

# Upgrade pip first: old pip versions reject hash-pinned requirement sets.
& "$env:APP_VENV_DIR\Scripts\python.exe" -m pip install --upgrade pip

# Runtime, then development, both with --require-hashes.
& "$env:APP_VENV_DIR\Scripts\python.exe" -m pip install `
    --require-hashes --no-deps -r requirements\requirements.lock
& "$env:APP_VENV_DIR\Scripts\python.exe" -m pip install `
    --require-hashes -r requirements\requirements-dev.lock

# The backend imports `app.*`, so install it editable in the same interpreter.
& "$env:APP_VENV_DIR\Scripts\python.exe" -m pip install --no-deps -e .

& "$env:APP_VENV_DIR\Scripts\python.exe" --version      # must be 3.12.x
```

Expected: every line `Successfully installed …`, then Python 3.12.
If pip reports a hash mismatch: **stop**. Do not pass `--no-verify`. Record the
package name and file; that is a blocker for the lockfiles, not for this branch.

> The project's own `scripts\powershell\setup.ps1` performs the same install and is
> the supported path. Use it if you prefer:
> `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1 -SkipFrontend -SkipDatabase`
> The explicit commands above are listed so a failure can be attributed to one step.

---

## 4. Deterministic fixtures

Binaries are **not** committed (owner decision D-04); they are generated from the
committed text sources and must be byte-identical on every run.

```powershell
& "$env:APP_VENV_DIR\Scripts\python.exe" scripts\python\generate_p3_fixtures.py
# Expect one line per generator: "… deterministic=True"

& "$env:APP_VENV_DIR\Scripts\python.exe" scripts\python\generate_p3_fixtures.py --out .\artifacts\fixtures
Get-ChildItem .\artifacts\fixtures | Select-Object Name, Length
```

Record the summary lines. A `deterministic=False` line is a FAIL.

---

## 5. Alembic round trip on a disposable database

```powershell
Set-Location $Accept\backend\migrations
$Db = 'sqlite:///C:/src/p3-acceptance/artifacts/roundtrip.db'

New-Item -ItemType Directory -Force -Path "$Accept\artifacts" | Out-Null

& "$env:APP_VENV_DIR\Scripts\python.exe" -m alembic -x database_url=$Db upgrade head
& "$env:APP_VENV_DIR\Scripts\python.exe" -m alembic -x database_url=$Db downgrade 0002_p2_patient_domain
& "$env:APP_VENV_DIR\Scripts\python.exe" -m alembic -x database_url=$Db upgrade head
& "$env:APP_VENV_DIR\Scripts\python.exe" -m alembic -x database_url=$Db downgrade base
& "$env:APP_VENV_DIR\Scripts\python.exe" -m alembic -x database_url=$Db upgrade head

# Assert the exact expected schema at head.
Set-Location $Accept
& "$env:APP_VENV_DIR\Scripts\python.exe" scripts\python\check_alembic_smoke.py `
    C:\src\p3-acceptance\artifacts\roundtrip.db --state head
# Expect: "Alembic smoke check: PASS (state head, revision ['0003_p3_documents'], …)"
```

This database is disposable and lives under `artifacts\`; delete it afterwards.
The `data\runtime\app.db` of your main checkout is never referenced.

---

## 6. Full local gate

```powershell
Set-Location $Accept
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1
```

Backend-only variant if the frontend is not installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1 -BackendOnly
```

Record the per-gate summary block and the exit code. `SKIPPED` is never a pass —
note which gate skipped and why.

Expected backend figure at this head: **519 passed** (P3: 136). Frontend gates were
not exercised in the sandbox at all, so treat their result as new evidence.

---

## 7. Real OCR, provenance and rasterization

This is the executable half of the handoff. It is **read-only** with respect to your
data: it creates its own temporary SQLite database and upload directory, and never
touches `data\runtime`.

```powershell
Set-Location $Accept
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'

& "$env:APP_VENV_DIR\Scripts\python.exe" scripts\python\windows_ocr_acceptance.py `
    --json .\artifacts\ocr-acceptance.json

"exit code: $LASTEXITCODE"
```

Exit `0` = every gate `PASS`. Exit `2` = at least one `NOT RUN`/`FAIL` — read the
summary table and record which.

| Gate printed by the script | What it proves | Contract case |
|---|---|---|
| `ENV-01 runtime` | Python 3.12, library versions actually installed | environment evidence |
| `OCR-ENGINE` | Tesseract executable resolves and reports a version | ASM-01 |
| `OCR-ENGINE eng.traineddata` | `eng` language data is present next to the exe | ASM-01 |
| `GOLD-EX-05 PNG` | real engine reads a clean PNG; records chars, confidence, version, wall time | `GOLD-EX-05`, `REQ-ING-02` |
| `GOLD-EX-06 JPEG` | same for JPEG | `GOLD-EX-06` |
| `OCR-LIVE-01 measured` | confidence/chars/wall time for both preprocessings, twice — **recorded, not asserted** | `OCR-LIVE-01` |
| `GOLD-EX-11 OCR-produced 1O5` | an OCR'd `1O5` is flagged, never repaired to `105` | `GOLD-EX-11` |
| `PDFIUM-01 rasterize` | `pypdfium2` renders page 0 on Windows (D-01) | D-01 |
| `ING-02 OCR upload end-to-end` | a PNG uploaded over HTTP yields `extractor='tesseract'` in the **response**, the **stored fact**, and the attempt log | `REQ-ING-02`, `REQ-VERIFY-01` |

`OCR-LIVE-01` is deliberately not a threshold: `GOLD_FIXTURES.md` §6.2 says the
numbers are **measured observations**. Write them into
`docs/evaluation/LOCAL_BENCHMARK_PLAN.md`; do not invent a pass mark for them.

**What the sandbox could prove instead (already done):** the provenance *storage and
read path* with a mocked engine (`test_p3_r01_ocr_facts_report_tesseract`). That
proves plumbing only — it is why this step exists.

---

## 8. Record the evidence

Copy this table into the PR (or attach the JSON) and fill it in from the run above.

| # | Gate | Command | Result | Evidence |
|---|---|---|---|---|
| 1 | Python 3.12 + hash-locked install | step 3 | PASS / FAIL / NOT RUN | pip tail |
| 2 | Fixture determinism | step 4 | | generator lines |
| 3 | Alembic head→0002→head→base→head | step 5 | | `check_alembic_smoke` line |
| 4 | Exact schema at head | step 5 | | PASS line incl. table list |
| 5 | `test_all.ps1` | step 6 | | summary block + exit code |
| 6 | Tesseract + `eng.traineddata` | step 1 / 7 | | `--version`, `--list-langs` |
| 7 | `GOLD-EX-05` PNG | step 7 | | JSON gate entry |
| 8 | `GOLD-EX-06` JPEG | step 7 | | JSON gate entry |
| 9 | `OCR-LIVE-01` measurements | step 7 | recorded | JSON gate entry |
| 10 | `GOLD-EX-11` OCR `1O5` | step 7 | | JSON gate entry |
| 11 | `pypdfium2` rasterization | step 7 | | JSON gate entry |
| 12 | OCR upload end-to-end provenance | step 7 | | JSON gate entry |
| 13 | CI on the tested head | GitHub Actions | | run URL |

---

## 9. Release blockers (any single one blocks P3 acceptance)

1. A hash mismatch or a package that cannot be installed from the lockfiles on 3.12.
2. `Alembic smoke check` not `PASS` at `--state head`, or a downgrade that leaves
   the P2 schema changed.
3. Any `test_all.ps1` gate `FAIL`.
4. `OCR-ENGINE` or `OCR-ENGINE eng.traineddata` not `PASS`.
5. `GOLD-EX-05`/`06` not `PASS`, or OCR-derived facts reporting an extractor other
   than `tesseract` in `ING-02`.
6. `PDFIUM-01` not `PASS` (D-01 would be unproven on the target OS).
7. CI not green on the exact tested head.

`OCR-LIVE-01` is a blocker only in the sense that it must be **recorded** — a low
confidence number is data, not a defect.

---

## 10. What is still open after a green run

- One **contract clarification** is requested, not applied: §4/§6.1 of
  `DEMO_REVIEW_RULES.md` should state that `VI-002` counts facts that are not
  `verified` **and not superseded by a correction** (see `PHASE_3_REPORT.md` §V.3).
  Until then the shipped behaviour is an interpretation recorded in the phase
  report, not a silently edited contract.
- P3 remains `IN_REVIEW` until the owner's independent review of this evidence.
  The implementing agent does not mark PASS and does not merge.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
