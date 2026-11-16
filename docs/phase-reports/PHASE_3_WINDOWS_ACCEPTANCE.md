# P3 Windows acceptance — executable handoff

**Status of this document: a procedure, not a result.** Nothing in it has been
executed by the implementing agent. The sandbox has no Windows, no Tesseract
engine and a Python 3.11 interpreter, so every gate below is **NOT RUN** until the
owner executes it and records the output.

| Item | Value |
|---|---|
| Main checkout (**never** mutated by this procedure) | `E:\DEPI\AI-Doctor-FollowUp-Agent` |
| Disposable acceptance worktree | `E:\DEPI\P3-Acceptance` |
| Branch (remote-only) | `arena/ce85d4e6-ai-doctor-followup-agent` |
| PR | [#10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) — draft, open |
| Phase | **`IN_REVIEW`** — no PASS, no merge, no P4/P5 |

Every path below is derived from those two roots; there are **no** hard-coded
`C:\…` paths and nothing reads `E:\DEPI\AI-Doctor-FollowUp-Agent\data\runtime\app.db`.

---

## 0. What "PASS" means here

| Mark | Meaning |
|---|---|
| `PASS` | The command ran and its output matched the stated expectation. Paste the output. |
| `FAIL` | It ran and did not match. Paste the output; that is a release blocker. |
| `NOT RUN` | It did not run, or a prerequisite was missing. **Not** a pass, **not** a failure of the code. |
| `DERIVED` | A mapping row stating which other gates prove a contract case. Never counted as a pass. |

The probe emits exactly these words and exits `2` if any gate is not `PASS`, so a
truncated log cannot be mistaken for acceptance.

---

## 1. Prerequisites (read-only checks)

```powershell
py -3.12 --version          # expect Python 3.12.x
git --version
node --version              # expect v22.x  (needed for the full test_all.ps1 gate)
```

The same checks are available as a script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File 'E:\DEPI\AI-Doctor-FollowUp-Agent\scripts\powershell\preflight.ps1'
```

Tesseract for Windows:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs     # expect: eng
Get-Item 'C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata' |
    Select-Object FullName, Length
```

Record the version, the `--list-langs` output and the `eng.traineddata` size. An
engine without `eng` data is a **release blocker**, not something to route around
by lowering a threshold.

---

## 2. Isolated worktree at the exact reviewed commit

The P3 branch may exist only on the remote, so the worktree is created **detached**
from the verified remote SHA. `main` is never checked out and never touched.

```powershell
$Main       = 'E:\DEPI\AI-Doctor-FollowUp-Agent'
$Accept     = 'E:\DEPI\P3-Acceptance'
$Branch     = 'refs/heads/arena/ce85d4e6-ai-doctor-followup-agent'
$ApprovedSha = '<PASTE THE REVIEWED SHA HERE>'      # e.g. from the PR header

# 2.1 Refuse to run if the destination already exists.
if (Test-Path -LiteralPath $Accept) {
    throw "Refusing to proceed: '$Accept' already exists. Inspect or remove it deliberately."
}

# 2.2 Fetch, and verify the remote is really the branch we think it is.
git -C $Main fetch origin $Branch
$RemoteSha = (git -C $Main rev-parse FETCH_HEAD).Trim()
Write-Host "fetched FETCH_HEAD = $RemoteSha"
if ($RemoteSha -ne $ApprovedSha) {
    throw "Refusing to proceed: fetched $RemoteSha but the reviewed SHA is $ApprovedSha."
}

# 2.3 Detached worktree at that exact commit — no local branch is created.
git -C $Main worktree add --detach $Accept $ApprovedSha

# 2.4 Assert the worktree really sits on the approved commit and is clean.
$Head = (git -C $Accept rev-parse HEAD).Trim()
if ($Head -ne $ApprovedSha) { throw "worktree HEAD $Head != $ApprovedSha" }
$Dirty = (git -C $Accept status --porcelain)
if ($Dirty) { throw "worktree is not clean:`n$Dirty" }
Write-Host "OK: detached at $Head, working tree clean."

# 2.5 Prove the main checkout was not modified and its database is untouched.
git -C $Main rev-parse HEAD
Get-Item "$Main\data\runtime\app.db" | Select-Object FullName, Length, LastWriteTime
```

`data\runtime\` inside `$Accept` starts empty, so this worktree cannot even see the
demo database, let alone write to it. Re-run step 2.5 at the end of the session and
compare the `app.db` length/timestamp: they must be identical.

To remove the worktree afterwards:

```powershell
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' worktree remove 'E:\DEPI\P3-Acceptance'
```

---

## 3. Python 3.12 hash-locked runtime (repo-native setup)

Use the repository's own script, **without** `-SkipFrontend` (the full
`test_all.ps1` gate runs frontend typecheck, lint, Vitest and a production build, so
`node_modules` must exist in this worktree) and **with** `-SkipDatabase` (no
migration against a shared database here — that is step 5 on a disposable file).

```powershell
Set-Location 'E:\DEPI\P3-Acceptance'
$env:APP_VENV_DIR = 'E:\DEPI\P3-Acceptance\.venv'

powershell -NoProfile -ExecutionPolicy Bypass `
  -File '.\scripts\powershell\setup.ps1' -SkipDatabase
```

`setup.ps1` itself: creates `.env` from `.env.example` when missing (never
overwrites an existing one), creates the 3.12 venv at `$env:APP_VENV_DIR`, installs
both **hash-verified lock files** with `--require-hashes`, installs the backend
editable, and installs frontend dependencies with `npm.cmd ci`. It starts no
process and downloads only from the official registries.

Record from its output:

1. the `Python 3.12.x` line — proof the interpreter is 3.12, not 3.11;
2. the `pip install … --require-hashes` lines for **both** lock files, with no
   `--no-verify` anywhere;
3. the `npm.cmd ci` summary and the Node version.

Then confirm the runtime explicitly:

```powershell
& "$env:APP_VENV_DIR\Scripts\python.exe" --version                # 3.12.x
& "$env:APP_VENV_DIR\Scripts\python.exe" -m pip check             # no broken requirements
```

If pip reports a **hash mismatch**: stop. Do not re-run with `--no-verify`; record
the package and file — that is a lockfile blocker.

> The explicit `pip install --require-hashes -r requirements\…lock` commands are
> deliberately *not* duplicated here: `setup.ps1` is the supported path and the
> reviewer asked for it by name. If `setup.ps1` fails, its output names the step.

---

## 4. Deterministic synthetic fixtures

Binaries are **not** committed (owner decision D-04); they are generated from the
committed text sources and must be byte-identical on every run.

```powershell
Set-Location 'E:\DEPI\P3-Acceptance'
$Py = "$env:APP_VENV_DIR\Scripts\python.exe"
$Evidence = 'E:\DEPI\P3-Acceptance\artifacts'
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

& $Py scripts\python\generate_p3_fixtures.py
# expect every line to end with deterministic=True

& $Py scripts\python\generate_p3_fixtures.py --out "$Evidence\fixtures"
Get-ChildItem "$Evidence\fixtures" | Select-Object Name, Length
```

A `deterministic=False` line is a FAIL.

---

## 5. Alembic round trip on a disposable database

The URL is derived from `$Accept`; nothing points at `data\runtime`.

```powershell
Set-Location 'E:\DEPI\P3-Acceptance\backend\migrations'
$Py = 'E:\DEPI\P3-Acceptance\.venv\Scripts\python.exe'
$Evidence = 'E:\DEPI\P3-Acceptance\artifacts'
$DbFile = Join-Path $Evidence 'roundtrip.db'
$Db = 'sqlite:///' + ($DbFile -replace '\\', '/')

& $Py -m alembic -x database_url=$Db upgrade head
& $Py -m alembic -x database_url=$Db downgrade 0002_p2_patient_domain
& $Py -m alembic -x database_url=$Db upgrade head
& $Py -m alembic -x database_url=$Db downgrade base
& $Py -m alembic -x database_url=$Db upgrade head

Set-Location 'E:\DEPI\P3-Acceptance'
& $Py scripts\python\check_alembic_smoke.py $DbFile --state head
# expect: "Alembic smoke check: PASS (state head, revision ['0003_p3_documents'], …)"
```

Also assert the intermediate P2 schema survived (this is the D-05 check):

```powershell
Set-Location 'E:\DEPI\P3-Acceptance\backend\migrations'
& $Py -m alembic -x database_url=$Db downgrade 0002_p2_patient_domain
Set-Location 'E:\DEPI\P3-Acceptance'
& $Py scripts\python\check_alembic_smoke.py $DbFile --state p2
& $Py -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('PRAGMA foreign_key_check').fetchall())" $DbFile
```

`$DbFile` is disposable and lives under `artifacts\`; delete it afterwards.

---

## 6. Full local gate

```powershell
Set-Location 'E:\DEPI\P3-Acceptance'
powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\powershell\test_all.ps1'
```

Record the per-gate summary block **and** the exit code. `SKIPPED` is never a pass —
note which gate skipped and why (the Playwright smoke legitimately skips unless
`-IncludeE2E` is given and browser binaries are installed).

Expected backend figure at this commit: **635 passed**, of which **252** are the P3
suite (`backend/tests/p3`). Verified by collection on the reviewed commit, not
estimated:

| Suite | Tests |
|---|---|
| `backend/tests` (whole backend) | **635 passed** |
| `backend/tests/p3` (P3 suite) | **252** |
| ├ `test_p3_verification.py` | 29 |
| ├ `test_p3_extraction.py` | 26 |
| ├ `test_p3_edge_cases.py` (R06–R09) | 24 |
| ├ `test_p3_review_corrections.py` (R01–R05) | 21 |
| ├ `test_p3_ocr_integration.py` (R11/R12 pytesseract + lock) | 16 |
| ├ `test_p3_r17_safety.py` (R17 OCR substitution + fail-closed) | 24 |
| ├ `test_p3_r18_provenance.py` (R18 span exactness + bare label) | 14 |
| ├ `test_p3_windows_findings.py` (R13–R16) | 47 |
| ├ `test_windows_ocr_acceptance.py` (probe + handoff) | 17 |
| ├ `test_p3_upload.py` | 12 |
| ├ `test_p3_authorization.py` | 10 |
| └ `test_p3_fixtures.py` (incl. CRLF portability) | 12 |


> **Windows CRLF note (P3-R10).** `git` may check these `.txt` fixtures out with CRLF,
> which changes their byte length and SHA-256. That is expected: the integrity test
> canonicalizes CRLF to LF before hashing and compares against the committed
> `manifest.json` values, so a CRLF checkout is not a failure. If you *do* see a hash
> mismatch, it is a real content difference — report the file and both digests rather
> than re-cloning. Set nothing; do not add `core.autocrlf=false` to work around it.

Those figures come from a **Linux sandbox on Python 3.11**, so treat them as the
expected *count*, not as Windows evidence. A different count on your machine is a
finding worth reporting, not a failure to explain away — in particular the Playwright
smoke adds cases only with `-IncludeE2E`. The frontend gates were not exercised in
the sandbox at all, so their result is new evidence, not confirmation.

---

## 7. Real OCR, provenance and rasterization

The probe is read-only with respect to your data: it creates its own temporary
SQLite database and upload directory, and never references `data\runtime`.

```powershell
Set-Location 'E:\DEPI\P3-Acceptance'
$Py = 'E:\DEPI\P3-Acceptance\.venv\Scripts\python.exe'
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'

& $Py scripts\python\windows_ocr_acceptance.py `
      --json 'E:\DEPI\P3-Acceptance\artifacts\ocr-acceptance.json'

"exit code: $LASTEXITCODE"
```

Exit `0` = every gate `PASS`. Exit `2` = at least one `FAIL`/`NOT RUN` — read the
summary table and record which. The JSON always contains `repository_head`, so the
evidence is bound to the exact commit it was produced from.

| Gate | What it proves | Contract case |
|---|---|---|
| `ENV-01 python` | interpreter is 3.12 | environment evidence |
| `ENV-02 libraries` | `PIL`, `pytesseract`, `pypdfium2` actually import (a missing wheel is a FAIL, not a crash) | environment evidence |
| `OCR-ENGINE` | Tesseract resolves and reports a version | ASM-01 |
| `OCR-ENGINE eng.traineddata` | `eng` language data present | ASM-01 |
| `GOLD-EX-05 PNG` | real engine reads a clean PNG: chars, confidence, version, wall time | `GOLD-EX-05` |
| `GOLD-EX-06 JPEG` | same for JPEG | `GOLD-EX-06` |
| `GOLD-EX-07/08 coverage` | **`DERIVED`** row: 07 = fields via OCR (asserted by `ING-02`), 08 = JPEG readability (asserted by `GOLD-EX-06`). Documented, never claimed as an independent pass | `GOLD-EX-07/08` |
| `OCR-LIVE-01` | confidence/chars/wall time, both preprocessings, twice — **recorded, not asserted** | `OCR-LIVE-01` |
| `GOLD-EX-11 OCR-produced 1O5` | an OCR'd `1O5` is flagged, never repaired to `105` | `GOLD-EX-11` |
| `PDFIUM-01 rasterize` | `pypdfium2` renders page 0 (D-01) | D-01 |
| `ING-02 OCR upload end-to-end` | a PNG uploaded over HTTP yields `extractor='tesseract'` in the **response**, the **stored fact** and the attempt log | `REQ-ING-02`, `REQ-VERIFY-01` |

`OCR-LIVE-01` is deliberately not a threshold: `GOLD_FIXTURES.md` §6.2 makes those
numbers **measured observations**. Write them into
`docs/evaluation/LOCAL_BENCHMARK_PLAN.md`; do not invent a pass mark.

**What the sandbox could prove instead (already done):** the provenance *storage and
read path* against a mocked engine (`test_p3_r01_ocr_facts_report_tesseract`). That
proves plumbing only — which is exactly why this step exists.

**Secrets and real data:** the probe writes only synthetic fixture bytes,
plaintext-free gate results and library versions. It never prints tokens (the
session tokens it mints are discarded), never reads a real patient record, and the
JSON carries no paths outside `$Accept`. Review the JSON before attaching it if you
add environment variables of your own.

---

## 8. Record the evidence

Copy this table into PR #10 (or attach the JSON) and fill it from the run above.

| # | Gate | Command | Result | Evidence |
|---|---|---|---|---|
| 1 | Fetch + SHA match + detached worktree | step 2 | | `FETCH_HEAD`/`HEAD` lines |
| 2 | Main checkout + `app.db` unchanged | steps 2.5 / 10 | | before/after `app.db` line |
| 3 | Python 3.12 hash-locked install | step 3 | | `setup.ps1` Python line + `--require-hashes` lines |
| 4 | Fixture determinism | step 4 | | generator lines |
| 5 | Alembic head→0002→head→base→head | step 5 | | `check_alembic_smoke` line |
| 6 | Schema at `head` and at `p2` | step 5 | | two PASS lines + `foreign_key_check` |
| 7 | `test_all.ps1` | step 6 | | summary block + exit code |
| 8 | Tesseract + `eng.traineddata` | steps 1 / 7 | | `--version`, `--list-langs` |
| 9 | `GOLD-EX-05` PNG | step 7 | | JSON gate entry |
| 10 | `GOLD-EX-06` JPEG | step 7 | | JSON gate entry |
| 11 | `GOLD-EX-07/08` | step 7 | `DERIVED` | JSON gate entry |
| 12 | `OCR-LIVE-01` measurements | step 7 | recorded | JSON gate entry |
| 13 | `GOLD-EX-11` OCR `1O5` | step 7 | | JSON gate entry |
| 14 | `pypdfium2` rasterization | step 7 | | JSON gate entry |
| 15 | OCR upload end-to-end provenance | step 7 | | JSON gate entry |
| 16 | CI on the tested head | GitHub Actions | | run URL |

---

## 9. Release blockers (any one blocks P3 acceptance)

1. `FETCH_HEAD` ≠ the reviewed SHA, or the worktree is not clean/detached.
2. A hash mismatch or a package that cannot be installed from the lockfiles on 3.12.
3. `check_alembic_smoke` not `PASS` at `--state head` **or** at `--state p2`, or a
   downgrade that changes the P2 schema.
4. Any `test_all.ps1` gate `FAIL`.
5. `OCR-ENGINE` or `OCR-ENGINE eng.traineddata` not `PASS`.
6. `GOLD-EX-05`/`06` not `PASS`, or `ING-02` showing any extractor other than
   `tesseract`.
7. `PDFIUM-01` not `PASS` (D-01 unproven on the target OS).
8. `E:\DEPI\AI-Doctor-FollowUp-Agent\data\runtime\app.db` changed.
9. CI not green on the exact tested head.

`OCR-LIVE-01` is a blocker only in the sense that it must be **recorded** — a low
confidence number is data, not a defect.

---

## 10. Close the loop

```powershell
# Confirm the main checkout and its database were never touched.
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' rev-parse HEAD
Get-Item 'E:\DEPI\AI-Doctor-FollowUp-Agent\data\runtime\app.db' |
    Select-Object FullName, Length, LastWriteTime
# Compare with the values recorded in step 2.5 — they must be identical.
```

---

## 11. What is still open after a green run

- Owner decision **D-14** (recorded in `docs/roadmap/PHASE_PROGRESS.md`) is applied
  to `DEMO_REVIEW_RULES.md` §4/§6.1: `VI-002` counts **active** candidates only,
  excluding a superseded original with valid `corrected_from_fact_id` lineage.
  It authorizes nothing else — no automatic verification, no deletion of history,
  no change to `map-1.0.0`.
- P3 remains `IN_REVIEW` until the owner reviews this evidence. The implementing
  agent does not mark PASS and does not merge.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
