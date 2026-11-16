# P3 Windows acceptance — executable handoff

**Status of this document: a procedure, not a result.** Nothing in it has been
executed by the implementing agent. The sandbox has no Windows, no Tesseract
engine and a Python 3.11 interpreter, so every gate below is **NOT RUN** until the
owner executes it and records the output.

| Item | Value |
|---|---|
| Main checkout (**never** mutated by this procedure) | `E:\DEPI\AI-Doctor-FollowUp-Agent` |
| Disposable acceptance worktree | `E:\DEPI\P3-Acceptance` (or `P3-Acceptance-<short-sha>` if taken — §2.1) |
| Branch (remote-only) | `arena/818751e0-ai-doctor-followup-agent` — the **R21 implementation**, not PR #10 |
| Pinned commit | the SHA the reviewer names for this Stage 5.1 correction (§2.0) |
| PR | [#10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) — draft, open, **not** this branch |
| Phase | **`IN_REVIEW`** — no PASS, no merge, no P4/P5 |

> **This procedure now targets the R21 implementation branch.** Earlier revisions
> of this document fetched `refs/heads/arena/ce85d4e6-ai-doctor-followup-agent`,
> which is PR #10's branch and still points at `18a53b2`. That commit does **not**
> contain the R21 rejection/recovery work, so following those commands failed the
> SHA check before any Windows gate ran. Do not substitute PR #10's branch here.

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

The R21 branch exists **only on the remote**, so the worktree is created **detached**
from the verified remote SHA. No local branch is created, `main` is never checked
out, and the main checkout is never touched.

### 2.0 The exact SHA you must paste

`$ApprovedSha` below is a placeholder on purpose. **Fill it with the SHA the
reviewer names when approving this Stage 5.1 correction** — that is the only
correct source. Two rules make it safe:

1. **It is the reviewer's SHA, never the branch tip.** The branch may have moved
   since review. Binding the evidence to a commit a human actually reviewed is the
   entire point of the check.
2. **It must be a commit that carries this document.** The expected figures in §6
   and the populated-graph regression only exist from the Stage 5.1 commit onward.
   A commit cannot name its own hash, so this file cannot quote it — but the
   checkout can tell you whether you are holding the right pairing (below).

Do **not** paste `18a53b2` (PR #10) or `867ab12` (`main`); neither contains R21.

#### Verify the document and the code are the same commit

The expected test count travels with the commit. The count has moved twice:
`e7d73b5` (Stages 3-5) expects **663** (P3: 275); the Stage 5.1 revision expects
**666** (P3: 275); and Stage 5.2 expected **688** (P3: **297**); Stage 5.2a expects **696** (P3: **305**) after eight probe regressions. Pinning an older SHA while reading a newer table —
or the reverse — reports a false FAIL on a run that actually succeeded, which is
why the check below reads the figure from the pinned checkout rather than from
whatever copy of this file you happen to be holding.

Let the checkout settle it, before recording any number:

```powershell
# Which document did the pinned commit actually check out?
Select-String -Path (Join-Path $env:P3_ACCEPT 'docs\phase-reports\PHASE_3_WINDOWS_ACCEPTANCE.md') `
               -Pattern 'passed\*\*, of which'

# And what does that checkout actually collect?
# NOTE: this needs the 3.12 runtime built in §3/§4, so it runs *after* those steps.
# $Py is defined here explicitly rather than assumed, because this block appears
# before §3 and would otherwise fail with "Cannot bind argument to parameter 'Path'".
Set-Location $env:P3_ACCEPT
$Py = Join-Path $env:APP_VENV_DIR "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
    throw "Run §3/§4 first: no interpreter at $Py. The count check below needs it."
}
& $Py -m pytest backend/tests --collect-only -q 2>&1 | Select-Object -Last 2
```

If the figure the document states and the figure pytest collects disagree, **stop**.
You are holding one commit's procedure against another commit's code, and no
Windows result from that combination is usable. Re-pin and start §2 again.

### 2.1 Handle an existing acceptance worktree without destroying it

A previous run may have left `E:\DEPI\P3-Acceptance` behind. This procedure
**never deletes or overwrites it**. It detects the situation, tells you what is
there, and moves to a new destination instead.

```powershell
$Main        = 'E:\DEPI\AI-Doctor-FollowUp-Agent'
$Branch      = 'refs/heads/arena/818751e0-ai-doctor-followup-agent'
$ApprovedSha = '<PASTE THE REVIEWED STAGE 5.1 SHA HERE>'   # see §2.0
$Base        = 'E:\DEPI\P3-Acceptance'
$Accept      = $Base

# 2.1.1 If the usual path is occupied, do NOT remove it: report and relocate.
if (Test-Path -LiteralPath $Base) {
    Write-Host "NOTE: '$Base' already exists. Leaving it untouched."
    foreach ($w in (git -C $Main worktree list --porcelain)) {
        if ($w -like "worktree $Base*") { Write-Host "  registered worktree: $w" }
    }
    $short   = $ApprovedSha.Substring(0, 12)
    $Accept  = "$Base-$short"
    Write-Host "  using a fresh isolated destination instead: '$Accept'"
}

# 2.1.2 The relocated path must itself be free; never reuse it silently.
if (Test-Path -LiteralPath $Accept) {
    throw ("Refusing to proceed: '$Accept' already exists too. " +
           "Inspect or remove it deliberately, then re-run with a new `$Accept`.")
}
Write-Host "acceptance worktree will be created at: $Accept"
```

If you *want* to reclaim a stale worktree, do it as an explicit, separate decision
— never as a side effect of this procedure:

```powershell
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' worktree list
# Only after confirming nothing there is needed:
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' worktree remove 'E:\DEPI\P3-Acceptance'
```

### 2.2 Fetch, and prove the remote really is the reviewed commit

```powershell
# 2.2.1 Ask the remote what the branch is, without trusting any local ref.
$RemoteSha = (git -C $Main ls-remote origin $Branch).Split("`t")[0].Trim().ToLower()
Write-Host "origin $Branch = $RemoteSha"

# 2.2.2 The branch tip must carry the reviewed commit. If the branch has moved
#       ahead of the reviewed SHA, that is expected during a review cycle — but the
#       reviewed commit must still be an ancestor of it, and it must exist.
if ($RemoteSha -ne $ApprovedSha) {
    git -C $Main fetch origin $Branch
    git -C $Main cat-file -e "$ApprovedSha^{commit}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Reviewed SHA $ApprovedSha does not exist on the remote. Stop."
    }
    git -C $Main merge-base --is-ancestor $ApprovedSha $RemoteSha
    if ($LASTEXITCODE -ne 0) {
        throw ("Reviewed SHA $ApprovedSha is not an ancestor of $Branch ($RemoteSha). " +
               "The reviewed work may have been rewritten. Stop and ask the reviewer.")
    }
    Write-Host "NOTE: branch tip $RemoteSha is ahead of the reviewed SHA; building $ApprovedSha."
} else {
    git -C $Main fetch origin $Branch
}

# 2.2.3 Fetch the exact object and re-verify it locally.
$FetchedSha = (git -C $Main rev-parse "$ApprovedSha^{commit}").Trim().ToLower()
Write-Host "resolved approved commit = $FetchedSha"
if ($FetchedSha -ne $ApprovedSha) {
    throw "Refusing to proceed: resolved $FetchedSha but the reviewed SHA is $ApprovedSha."
}
```

### 2.3 Detached worktree at that exact commit

```powershell
git -C $Main worktree add --detach $Accept $ApprovedSha

# 2.3.1 Assert the worktree really sits on the approved commit and is clean.
$Head = (git -C $Accept rev-parse HEAD).Trim().ToLower()
if ($Head -ne $ApprovedSha) { throw "worktree HEAD $Head != $ApprovedSha" }
$Dirty = (git -C $Accept status --porcelain)
if ($Dirty) { throw "worktree is not clean:`n$Dirty" }
Write-Host "OK: detached at $Head, working tree clean."

# 2.3.2 Bind the rest of the session to this path (it may be the relocated one).
$env:P3_ACCEPT = $Accept
$env:P3_APPROVED_SHA = $ApprovedSha
Write-Host "P3_ACCEPT=$env:P3_ACCEPT  P3_APPROVED_SHA=$env:P3_APPROVED_SHA"
```

Every later step uses `$env:P3_ACCEPT`, not a literal path, so a relocated
worktree does not silently send the run back to the stale one.

### 2.4 Prove the main checkout and its database were not modified

```powershell
git -C $Main rev-parse HEAD
Get-Item "$Main\data\runtime\app.db" | Select-Object FullName, Length, LastWriteTime
```

Re-run this at the end (§10) and compare: `HEAD` must be unchanged and `app.db`
must have the same length and timestamp. `data\runtime\` inside the acceptance
worktree starts empty, so the worktree cannot even see the demo database.

To remove the worktree afterwards — **your** decision, never this procedure's, and
only after the evidence is captured and the path is confirmed:

```powershell
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' worktree remove $env:P3_ACCEPT
```

---

## 3. Python 3.12 hash-locked runtime (repo-native setup)

Use the repository's own script, **without** `-SkipFrontend` (the full
`test_all.ps1` gate runs frontend typecheck, lint, Vitest and a production build, so
`node_modules` must exist in this worktree) and **with** `-SkipDatabase` (no
migration against a shared database here — that is step 5 on a disposable file).

```powershell
Set-Location $env:P3_ACCEPT
$env:APP_VENV_DIR = Join-Path $env:P3_ACCEPT ".venv"

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
Set-Location $env:P3_ACCEPT
$Py = "$env:APP_VENV_DIR\Scripts\python.exe"
$Evidence = Join-Path $env:P3_ACCEPT "artifacts"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null

& $Py scripts\python\generate_p3_fixtures.py
# expect every line to end with deterministic=True

& $Py scripts\python\generate_p3_fixtures.py --out "$Evidence\fixtures"
Get-ChildItem "$Evidence\fixtures" | Select-Object Name, Length
```

A `deterministic=False` line is a FAIL.

---

## 5. Alembic round trip on a disposable database

The head revision below is **`0004_p3_rejection_recovery`**. R21 added it after
`0003_p3_documents`, and `check_alembic_smoke.py` now knows a real `p3` state, so
the sequence visits every state the checker can assert rather than only `head` and
`p2`.

The database URL is derived from `$env:P3_ACCEPT`; nothing points at
`data\runtime`.

```powershell
$Py = Join-Path $env:APP_VENV_DIR "Scripts\python.exe"
$Evidence = Join-Path $env:P3_ACCEPT "artifacts"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$DbFile = Join-Path $Evidence 'roundtrip.db'
$Db = 'sqlite:///' + ((Resolve-Path $Evidence).Path -replace '\\', '/') + '/roundtrip.db'

# Two positional parameters rather than array splatting: splatting a param-typed
# array into a native executable behaves differently between PowerShell 5.1 and 7,
# and this procedure must be reproducible on the Windows PowerShell 5.1 that ships
# with Windows 11. The URL is quoted because it contains ':' and '/'.
function Invoke-Alembic {
    param([string]$Action, [string]$Revision = '')
    Set-Location (Join-Path $env:P3_ACCEPT "backend\migrations")
    if ($Revision) {
        & $Py -m alembic -x "database_url=$Db" $Action $Revision
    } else {
        & $Py -m alembic -x "database_url=$Db" $Action
    }
    if ($LASTEXITCODE -ne 0) {
        throw "alembic $Action $Revision failed (exit $LASTEXITCODE)"
    }
    Set-Location $env:P3_ACCEPT
}
function Assert-Smoke { param([string]$State)
    & $Py scripts\python\check_alembic_smoke.py $DbFile --state $State
    if ($LASTEXITCODE -ne 0) { throw "check_alembic_smoke --state $State failed" }
}
```

Run the sequence, asserting each state **immediately** after reaching it — a single
final check at `head` would not prove the intermediate downgrades left anything
correct:

```powershell
Invoke-Alembic 'upgrade' 'head'                           # -> 0004
Assert-Smoke 'head'
# expect: PASS (state head, revision ['0004_p3_rejection_recovery'], …)

Invoke-Alembic 'downgrade' '0003_p3_documents'            # -> 0003
Assert-Smoke 'p3'
# expect: PASS (state p3, revision ['0003_p3_documents'], …)
# At 0003 the recovery column/index/self-FK must be ABSENT; the checker asserts it.

Invoke-Alembic 'upgrade' 'head'                           # -> 0004 again
Assert-Smoke 'head'

Invoke-Alembic 'downgrade' '0002_p2_patient_domain'       # D-05: P2 schema intact
Assert-Smoke 'p2'

Invoke-Alembic 'downgrade' 'base'
Assert-Smoke 'base'

Invoke-Alembic 'upgrade' 'head'                           # -> 0004 from scratch
Assert-Smoke 'head'
```

Then assert foreign-key integrity on a **runtime-equivalent** connection, i.e. with
`PRAGMA foreign_keys=ON`. The migration engine intentionally runs DDL with foreign
keys off, so a plain `sqlite3.connect` would not reproduce the runtime setting:

```powershell
& $Py -c @"
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('PRAGMA foreign_keys=ON')
print('foreign_keys =', c.execute('PRAGMA foreign_keys').fetchone()[0])
print('foreign_key_check =', c.execute('PRAGMA foreign_key_check').fetchall())
print('document.recovered_from_document_id present =',
      any(r[1] == 'recovered_from_document_id' for r in c.execute('PRAGMA table_info(document)')))
print('self-FK =', [r for r in c.execute('PRAGMA foreign_key_list(document)')
                    if r[3] == 'recovered_from_document_id'])
"@ $DbFile
```

Expect `foreign_keys = 1`, `foreign_key_check = []`, present `= True`, and exactly
one self-FK row whose delete action is `RESTRICT`.

> **This is the round trip, not the populated-graph test.** The row-preservation
> assertions here run on an *empty* schema. The populated P3 dependency graph
> (document → extraction_attempt → extracted_fact → fact_verification →
> verification_issue, plus `observation.source_fact_id`) is covered by
> `backend/tests/p2/test_p2_migration.py::test_0004_preserves_a_populated_p3_graph`,
> which runs inside `test_all.ps1` at step 6. No manual step is needed for it.

`$DbFile` is disposable and lives under `artifacts\`; delete it afterwards.

---

## 6. Full local gate

```powershell
Set-Location $env:P3_ACCEPT
powershell -NoProfile -ExecutionPolicy Bypass -File '.\scripts\powershell\test_all.ps1'
```

Record the per-gate summary block **and** the exit code. `SKIPPED` is never a pass —
note which gate skipped and why (the Playwright smoke legitimately skips unless
`-IncludeE2E` is given and browser binaries are installed).

Expected backend figure at this commit: **696 passed**, of which **305** are the P3
suite (`backend/tests/p3`). Verified by collection and a full run on this Stage 5.2a commit, not estimated:

| Suite | Tests |
|---|---|
| `backend/tests` (whole backend) | **696 passed** |
| `backend/tests/p3` (P3 suite) | **305** |
| ├ `test_p3_verification.py` | 29 |
| ├ `test_p3_extraction.py` | 26 |
| ├ `test_p3_edge_cases.py` (R06–R09) | 24 |
| ├ `test_p3_review_corrections.py` (R01–R05) | 21 |
| ├ `test_p3_rejection_recovery.py` (R21 rejection/recovery) | 21 |
| ├ `test_p3_ocr_integration.py` (R11/R12 pytesseract + lock) | 16 |
| ├ `test_p3_r17_safety.py` (R17 OCR substitution + fail-closed) | 24 |
| ├ `test_p3_r18_provenance.py` (R18 span exactness + bare label) | 14 |
| ├ `test_p3_windows_findings.py` (R13–R16) | 47 |
| ├ `test_windows_ocr_acceptance.py` (probe, W1 gate + handoff) | 47 |
| ├ `test_p3_upload.py` | 12 |
| ├ `test_p3_authorization.py` | 12 |
| └ `test_p3_fixtures.py` (incl. CRLF portability) | 12 |

> **R21 note (current figures).** This table previously read **635 passed** for
> the backend and **252** for P3. The R21 rejection/recovery work added 21 cases
> to `test_p3_rejection_recovery.py` (Stage 1), 2 authorization cases for the new
> patient-safe metadata, and 8 `0004` migration tests in
> `backend/tests/p2/test_p2_migration.py` (rebuild integrity, row preservation,
> CHECK-constraint survival, downgrade refusal, downgrade round trip, plus the
> populated P3 dependency graph and its downgrade/link cases), for +31 in
> total as of Stage 5.1; no pre-existing test was removed, renamed or skipped, and
> the pre-existing 635 remain among the 666 measured then. Stage 5.2 adds the 20
> W1 cases above on top of that (see the Stage 5.2 note below).
>
> **Stage 5.2 (current figures).** The R21 W1 gate added 22 cases to
> `test_windows_ocr_acceptance.py` (17 -> 39), so the backend total moved
> 666 -> **688** and the P3 suite 275 -> **297**. No pre-existing test was removed,
> renamed or skipped, and the pre-existing 666 remain among the 688. Stage 5.1's
> populated-graph cases stay in `backend/tests/p2/`, beside the migration tests
> they extend.
>
> The R1-R8 R21 cases were written **RED first** and stayed RED until the
> implementation landed. They are now all GREEN — R1/R1a/R1b/R2/R3 from the
> Stage 2 rejection-state rule, R4–R7 from the Stage 3 recovery route and
> metadata, and R8 from migration `0004_p3_rejection_recovery`. The suite is
> therefore quoted as **passed**, which it is; there are no expected failures.
>
> **The R21 acceptance run is local and synthetic.** W1 (real-engine rejection)
> and W2 (`GOLD-EX-11` preservation, expected **FAIL / NOT PROVEN**) remain
> **Windows-only and unexecuted** — see §7 of
> `docs/phase-reports/P3_R21_REJECTION_RECOVERY_DESIGN.md`. Nothing here is
> Windows evidence, and no OCR configuration changed as part of R21.


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
Set-Location $env:P3_ACCEPT
$Py = Join-Path $env:APP_VENV_DIR "Scripts\python.exe"
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'

& $Py scripts\python\windows_ocr_acceptance.py `
      --json (Join-Path $Evidence "ocr-acceptance.json")

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
| `W1 R21 rejection: OCR value fact` | a real Tesseract scan of `report_a_glucose.txt` produces a `value` fact whose evidence extractor is `tesseract` | R21 W1 |
| `W1 R21 rejection: doctor rejection` | the **assigned doctor** rejects that exact fact; one decision row is stored | R21 W1 |
| `W1 R21 rejection: terminal failure` | stored `extraction_status='failed'` **and** `failure_code='measurement_rejected'` | R21 W1 |
| `W1 R21 rejection: no Observation` | **no** Observation references the rejected document's facts — a real assertion here, because this fixture's 104 mg/dL glucose would otherwise map | R21 W1 |
| `W1 R21 rejection: fact immutable` | the rejected fact keeps its `raw_text`, `normalized_value`, `quality_flags` and exactly **one** decision row | R21 W1 |
| `W1 R21 rejection: VI-002 stays open` | `VI-002` is still `state='open'` after the rejection (D-14) | R21 W1 |
| `W1 R21 rejection: re-decision refused` | a second decision answers `409 E_FACT_ALREADY_DECIDED` and appends **no** row | R21 W1 |

`W1` is the only gate in this file that proves R21's rejection behaviour on the
**real engine**. It is deliberately the mappable glucose fixture: with a hemoglobin
source, "no Observation was promoted" would be true even if the gate were broken,
so the assertion would be vacuous. The gate therefore checks its own fixture first
and reports `FAIL` rather than a hollow `PASS` if it is swapped for an unsupported
measurement.

Every W1 requirement is its own row. One combined verdict would hide which of the
seven requirements failed, which is how a partial result can be mistaken for a
green one. If Tesseract produces no usable `value` fact, W1 reports **`NOT RUN`**
with the extracted field list as evidence — it never fabricates a candidate, and no
`NOT RUN` is ever recorded as a pass.

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
| 1 | Fetch + SHA match + detached worktree | steps 2.1-2.3 | | `origin` ref, resolved commit and `HEAD` lines |
| 2 | Main checkout + `app.db` unchanged | steps 2.4 / 10 | | before/after `app.db` line |
| 3 | Python 3.12 hash-locked install | step 3 | | `setup.ps1` Python line + `--require-hashes` lines |
| 4 | Fixture determinism | step 4 | | generator lines |
| 5 | Alembic head→p3→head→p2→base→head | step 5 | | one `check_alembic_smoke` PASS line per state (6 total) |
| 6 | Recovery objects at `head`, absent at `p3`; P2 schema intact | step 5 | | `head`/`p3` PASS lines + `foreign_key_check = []` |
| 7 | `test_all.ps1` | step 6 | | summary block + exit code |
| 8 | Tesseract + `eng.traineddata` | steps 1 / 7 | | `--version`, `--list-langs` |
| 9 | `GOLD-EX-05` PNG | step 7 | | JSON gate entry |
| 10 | `GOLD-EX-06` JPEG | step 7 | | JSON gate entry |
| 11 | `GOLD-EX-07/08` | step 7 | `DERIVED` | JSON gate entry |
| 12 | `OCR-LIVE-01` measurements | step 7 | recorded | JSON gate entry |
| 13 | `GOLD-EX-11` OCR `1O5` | step 7 | | JSON gate entry |
| 14 | `pypdfium2` rasterization | step 7 | | JSON gate entry |
| 15 | OCR upload end-to-end provenance | step 7 | | JSON gate entry |
| 16 | **W1** real-engine rejection: OCR `value` fact produced | step 7 | | JSON gate entry |
| 17 | **W1** doctor rejection recorded | step 7 | | JSON gate entry |
| 18 | **W1** terminal `failed` / `measurement_rejected` | step 7 | | JSON gate entry |
| 19 | **W1** no Observation promoted from the rejected document | step 7 | | JSON gate entry |
| 20 | **W1** rejected fact immutable, one decision row | step 7 | | JSON gate entry |
| 21 | **W1** `VI-002` remains `open` (D-14) | step 7 | | JSON gate entry |
| 22 | **W1** re-decision → `409 E_FACT_ALREADY_DECIDED`, no new row | step 7 | | JSON gate entry |
| 23 | **`GOLD-EX-11`** | step 7 | **`FAIL` / NOT PROVEN — see §9** | JSON gate entry + raw OCR text |
| 24 | CI on the tested head | GitHub Actions | | run URL |

Row 23 is filled in **as a failure** unless the real engine genuinely stops
producing the `1O5` reading. See §9: a preserved `GOLD-EX-11` failure is a
**release blocker**, not a successful acceptance result.

---

## 9. Release blockers (any one blocks P3 acceptance)

1. The `origin` ref reported by `ls-remote` does not resolve to the reviewed SHA
   (or that SHA is not an ancestor of the branch tip), the detached `HEAD` in the
   acceptance worktree is not exactly the reviewed SHA, or the worktree is not
   clean. §2.2 and §2.3 verify this as `ls-remote` → ancestry → `rev-parse`, then
   a detached `HEAD` assertion; `FETCH_HEAD` is deliberately not trusted, because
   it records whatever was fetched last rather than what was reviewed.
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
10. Any **W1** row not `PASS` — including `NOT RUN`. R21's Windows requirement is
    that the real engine's OCR `value` fact is rejected end to end; a `NOT RUN`
    means that was not demonstrated, which blocks acceptance exactly like a `FAIL`
    (only its cause differs: no usable candidate versus a wrong result).
11. **`GOLD-EX-11` is not `PASS`.** This is a **release blocker**, not a known
    deviation to be noted and accepted.

### On `GOLD-EX-11` specifically

`GOLD-EX-11` currently stands at **`FAIL / NOT PROVEN`**. The OCR reading of the
committed `report_ocr_o_confusion.txt` source still yields `1O5`, and P3's
acceptance criterion is that the pipeline flags it rather than repairing it to
`105`. Until a real-engine run shows the flagged behaviour, this gate **blocks
final P3 acceptance**.

Three things this document deliberately does *not* do:

- It does not treat "the failure is unchanged" as success. Preserving a known
  failure across a release is evidence of **no regression**, not evidence of
  acceptance. Those are different claims, and reporting the second from the first
  would overstate the result.
- It does not weaken the expectation, the source fixture, the OCR settings
  (`preserve_interword_spaces` stays as configured) or the parser grammar to make
  the gate green. A green result reached that way would not describe the pipeline
  that ships.
- It does not substitute the `GOLD-EX-05/06` passes, `ING-02` or `W1` for it. They
  prove different properties: those show the engine reads a page and that a
  rejection is terminal; `GOLD-EX-11` shows a corrupted reading is never silently
  repaired into a plausible one.

So a run where every other gate is green and `GOLD-EX-11` is `FAIL` is a run with
**one release blocker**, and it must be reported that way.

`OCR-LIVE-01` is a blocker only in the sense that it must be **recorded** — a low
confidence number is data, not a defect.

---

## 10. Close the loop

```powershell
# Confirm the main checkout and its database were never touched.
git -C 'E:\DEPI\AI-Doctor-FollowUp-Agent' rev-parse HEAD
Get-Item 'E:\DEPI\AI-Doctor-FollowUp-Agent\data\runtime\app.db' |
    Select-Object FullName, Length, LastWriteTime
# Compare with the values recorded in step 2.4 — they must be identical.
```

---

## 11. What is still open after a green run

A run in which every gate is green still leaves these open — a green run is
evidence, not acceptance:

- **`GOLD-EX-11` remains a P3 acceptance blocker** unless it genuinely turns
  `PASS` (see §9). If it is still `FAIL / NOT PROVEN` after your run, the run has
  not established P3 acceptance, however many other rows are green. Report it as a
  blocker; do not carry it forward as a known deviation.
- Owner decision **D-14** (recorded in `docs/roadmap/PHASE_PROGRESS.md`) is applied
  to `DEMO_REVIEW_RULES.md` §4/§6.1: `VI-002` counts **active** candidates only,
  excluding a superseded original with valid `corrected_from_fact_id` lineage.
  It authorizes nothing else — no automatic verification, no deletion of history,
  no change to `map-1.0.0`.
- P3 remains `IN_REVIEW` until the owner reviews this evidence. The implementing
  agent does not mark PASS and does not merge.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
