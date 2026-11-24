# P3 Windows acceptance — executable handoff

> **LATEST POST-MERGE P3 OWNER STATUS (2026-11-19):** [PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) was **owner-merged** to `main` at `006ecf417f023428ab90c35cbb0638995c246774`; reviewed head `1b24d09d7630ff67ec282c9ee166440624d19fa5` has an identical tree, and [post-merge CI 44430671695](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44430671695) completed **SUCCESS**. Owner [conditionally accepted the P3 educational application](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995753177) and [ratified the independent-review substitution](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995977559). **P3 = CONDITIONALLY_ACCEPTED — LOCAL SYNTHETIC EDUCATIONAL USE ONLY**; this is not strict P1 technical PASS or clinical approval. Real `GOLD-EX-11 = FAIL / NOT PROVEN` (source `1O5` → OCR `105`; 27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED; exit 2) and possible false human attestation remain. See [final owner evidence/closure record](P3_FINAL_CONDITIONAL_ACCEPTANCE_20261119.md). Earlier `IN_REVIEW`, `DRAFT`, `PROPOSED`, and not-yet-effective statements below are *historical checkpoints*, not today's phase status. No P4/P5 execution authorization. **NOT FOR CLINICAL USE.**

> **Evidence/status addendum (2026-11-18; NOT a replacement for this historical procedure):** The owner has now executed the real Windows 11/Python 3.12.9/Tesseract 5.4 acceptance probe on detached implementation commit `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`. Actual result: **27 PASS / 1 FAIL (`GOLD-EX-11`) / 0 NOT RUN / 1 DERIVED; exit 2**. This document's early statements that owner Windows tests are "NOT RUN" describe its original drafting state, not the later owner-executed evidence. **Strict §9 is still binding.** The alternative P2 policy in §12 is **only proposed** and cannot overrule §9 without separate final owner ratification. See [owner Windows evidence report](P3_G11_OWNER_WINDOWS_REAL_OCR_6E6FCDF_EVIDENCE_REVIEW.md) and [decision memo](P3_GOLD_EX11_P2_OWNER_POLICY_DECISION_20261118.md).

**Status of this document: a procedure, not a result.** Nothing in it has been
executed by the implementing agent. The sandbox has no Windows, no Tesseract
engine and a Python 3.11 interpreter, so every gate below is **NOT RUN** until the
owner executes it and records the output.

| Item | Value |
|---|---|
| Main checkout (**never** mutated by this procedure) | `E:\DEPI\AI-Doctor-FollowUp-Agent` |
| Disposable acceptance worktree | `E:\DEPI\P3-Acceptance` (or `P3-Acceptance-<short-sha>` if taken — §2.1) |
| Branch (remote-only) | `arena/752cca1f-ai-doctor-followup-agent` — the **R21 + Stage 5.2a / 6a implementation**, not PR #10 |
| Pinned commit | the SHA the reviewer names for this Stage 6a correction (§2.0) |
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

The expected test count travels with the commit. The count has moved across
revisions: `e7d73b5` (Stages 3-5) expects **663** (P3: 275); Stage 5.1 expects
**666** (P3: 275); Stage 5.2 expects **688** (P3: 297); Stage 5.2a
(`e3a4698`) expects **702** (P3: 311); Stage 6a (`4f0862f`) expects **708** (P3: 314); Stage 6b.2 Stage 1 (`e5d6dbb`) expects **739** (P3: 345);
Stage 6b.2 Stage 2 (`46ee188`) expects **767** (P3: 373); Stage 3 (`af2bfd2`) expects
**789** (P3: 395); and this P3-G11 Step 2 revision expects **837** (P3: **443**),
adding 9 `OD-2b` / `A1-Anchored` / control regressions in Stage 3 verification
hardening and 39 non-vacuous `W2 / FC-3` (`W2-R1` / `W2-R2` / `W2-R3`) acceptance
harness regressions.
Pinning an older SHA while reading a newer table — or the reverse — reports a
false FAIL on a run that actually succeeded, which is why the check below reads
the figure from the pinned checkout rather than from whatever copy of this file
you happen to be holding.

Let the checkout settle it, before recording any number:

```powershell
# Which document did the pinned commit actually check out?
Select-String -Path (Join-Path $env:P3_ACCEPT 'docs\phase-reports\PHASE_3_WINDOWS_ACCEPTANCE.md') `
               -Pattern 'passed\*\*, of which'

# And what does that checkout actually collect?
# NOTE: this needs the 3.12 runtime built in §3/§4, so it runs *after* those steps.
# $Py is defined here explicitly rather than assumed, because this block appears
# before §3 and would otherwise fail with "Cannot bind argument to parameter 'Path'".
# Scoped ErrorActionPreference='Continue' prevents PowerShell 5.1 from treating
# benign native stderr lines as terminating errors if $ErrorActionPreference='Stop'.
Set-Location $env:P3_ACCEPT
$Py = Join-Path $env:APP_VENV_DIR "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
    throw "Run §3/§4 first: no interpreter at $Py. The count check below needs it."
}
& {
    $ErrorActionPreference = 'Continue'
    & $Py -m pytest backend/tests --collect-only -q 2>&1 |
        ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                if ($_.Exception) { $_.Exception.Message } else { $_.ToString() }
            } else {
                $_
            }
        } |
        Select-Object -Last 2
}
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
$Branch      = 'refs/heads/arena/752cca1f-ai-doctor-followup-agent'
$ApprovedSha = '<PASTE THE REVIEWED STAGE 6A SHA HERE>'   # see §2.0
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

## 5. Alembic round trip on a disposable database (`IMP-07`)

The head revision below is **`0005_p3_ocr_provenance`** (Stage 1 OCR provenance:
`document_page_text` + `fact_verification` confirmation columns, added without
rebuilding `fact_verification` so `trg_fact_verification_doctor_only` remains
intact across both upgrade and downgrade). `check_alembic_smoke.py` verifies
`head` (`0005`), `p3_recovery` (`0004`), `p3` (`0003`), `p2` (`0002`), `p1`,
and `base` cleanly on a disposable database.

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
Invoke-Alembic 'upgrade' 'head'                           # -> 0005
Assert-Smoke 'head'
# expect: PASS (state head, revision ['0005_p3_ocr_provenance'], …)

Invoke-Alembic 'downgrade' '0004_p3_rejection_recovery'   # -> 0004 (empty provenance)
Assert-Smoke 'p3_recovery'
# expect: PASS (state p3_recovery, revision ['0004_p3_rejection_recovery'], …)

Invoke-Alembic 'downgrade' '0003_p3_documents'            # -> 0003
Assert-Smoke 'p3'
# expect: PASS (state p3, revision ['0003_p3_documents'], …)
# At 0003 the recovery and Stage 1 columns/tables must be ABSENT; the trigger must survive.

Invoke-Alembic 'upgrade' 'head'                           # -> 0005 again
Assert-Smoke 'head'

Invoke-Alembic 'downgrade' '0002_p2_patient_domain'       # D-05: P2 schema intact
Assert-Smoke 'p2'

Invoke-Alembic 'downgrade' 'base'
Assert-Smoke 'base'

Invoke-Alembic 'upgrade' 'head'                           # -> 0005 from scratch
Assert-Smoke 'head'
```

Then assert foreign-key integrity, trigger survival, and Stage 1 provenance
objects on a **runtime-equivalent** connection (`PRAGMA foreign_keys=ON`):

```powershell
& $Py -c @"
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('PRAGMA foreign_keys=ON')
print('foreign_keys =', c.execute('PRAGMA foreign_keys').fetchone()[0])
print('foreign_key_check =', c.execute('PRAGMA foreign_key_check').fetchall())
print('document.recovered_from_document_id present =',
      any(r[1] == 'recovered_from_document_id' for r in c.execute('PRAGMA table_info(document)')))
print('document_page_text present =',
      any(r[0] == 'document_page_text' for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")))
print('fact_verification stage1 cols =',
      sorted({r[1] for r in c.execute('PRAGMA table_info(fact_verification)')}
             & {'source_image_compared', 'confirmed_value', 'confirmed_unit'}))
print('trigger present =',
      any(r[0] == 'trg_fact_verification_doctor_only'
          for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")))
print('self-FK =', [r for r in c.execute('PRAGMA foreign_key_list(document)')
                    if r[3] == 'recovered_from_document_id'])
"@ $DbFile
```

Expect `foreign_keys = 1`, `foreign_key_check = []`, `document.recovered_from_document_id present = True`, `document_page_text present = True`, `fact_verification stage1 cols = ['confirmed_unit', 'confirmed_value', 'source_image_compared']`, `trigger present = True`, and exactly one self-FK row whose delete action is `RESTRICT`.

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

If you capture logs from an outer Windows PowerShell 5.1 script where
`$ErrorActionPreference = 'Stop'`, **do not** run bare `& ... 2>&1`: PowerShell 5.1
wraps native stderr lines (such as Alembic `INFO [alembic.runtime.migration] ...`
diagnostics during `pytest`) as `ErrorRecord` objects and aborts on the first
one. Use a wrapper that scopes `Continue`, unwraps `ErrorRecord` entries to text,
streams live via `Out-Host`, and returns the exact scalar child exit code:

```powershell
function Invoke-Logged {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][string]$LogPath
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $global:LASTEXITCODE = 0
    try {
        & $FilePath @Arguments 2>&1 |
            ForEach-Object {
                if ($_ -is [System.Management.Automation.ErrorRecord]) {
                    if ($_.Exception) { $_.Exception.Message } else { $_.ToString() }
                } else {
                    $_
                }
            } |
            Tee-Object -FilePath $LogPath |
            Out-Host
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        if (-not $? -and $code -eq 0) { $code = 1 }
    }
    finally {
        $ErrorActionPreference = $prev
    }
    return $code
}

# Example — log full output, keep failures visible, and fail only on real non-zero exit:
$Evidence = Join-Path $env:P3_ACCEPT "artifacts"
New-Item -ItemType Directory -Force -Path $Evidence | Out-Null
$GateExit = Invoke-Logged -FilePath 'powershell.exe' `
    -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', '.\scripts\powershell\test_all.ps1') `
    -LogPath (Join-Path $Evidence 'test_all.log')
Write-Host "test_all exit code: $GateExit"
if ($GateExit -ne 0) { throw "test_all.ps1 failed (exit $GateExit); see test_all.log" }
```

> **Note on temporary scripts under `$env:P3_ACCEPT`:** Ruff checks all `.py`
> files in the worktree (including `artifacts\*.py`), so keep any ad-hoc
> helper scripts outside `$env:P3_ACCEPT` or delete them before running
> `test_all.ps1`.

Record the per-gate summary block **and** the exit code. `SKIPPED` is never a pass —
note which gate skipped and why (the Playwright smoke legitimately skips unless
`-IncludeE2E` is given and browser binaries are installed).

> **P4-1 additive test-collection note (2026-11-19, unmerged PR #15).**
> The immutable P3 handoff table below is the **historical P3-only reviewed
> baseline** (837 backend cases, 443 P3 cases). A new P4 test file adds test
> cases outside P3: at the P4-1 candidate head, pytest collection reports a
> **whole-backend expected green-run total of 859 cases**, without changing
> the 443 P3 cases. The protected P3 collection-integrity test requires the
> updated, paired expectation: **859 passed**, of which **443** are the P3 suite
> **if and only if** the candidate's complete backend test run succeeds. These
> are target/collection figures, **not** a claim that the failed pre-fix CI run
> passed. Do not revise the P3 837 historical run to 859, weaken its assertions,
> or claim the separate Windows P3 result (833 passed, four skips) changed.

> **P4-2a combined collection checkpoint (2026-11-19; after PR #16 owner merge, PR #17 still under review).**
> The accepted P3 history remains 837 backend / 443 P3. P4-1 collected 859/443;
> merged offline P4-2A PR #16 recorded 886/443. Standalone validator PR #17
> independently recorded 882/443 on the old P4-1 base. Expected combined
> collection on this reconciled branch is **909** backend / **443** P3,
> calculated as 886 + (882 - 859), **subject to exact-head pytest verification**.
> Only if complete backend tests pass is the paired candidate statement valid:
> **909 passed**, of which **443** are the P3 suite
> This sentence is a conditional expected test-gate token, not a claim that
> the combined CI has succeeded. Never rewrite the historical 837/443, P3
> Windows 833 passed / 4 skipped, or GOLD-EX-11 scientific FAIL.

> **P4-2A candidate-only test-collection note (2026-11-19, unmerged feature PR).**
> After the owner merged P4-1 (PR #15, reviewed head 6c254457a62826656382945898ac790dacc4ffc7), the repository collected **859** backend cases, including the same **443** P3 cases; the historical P3-only baseline below remains **837**. This P4-2A candidate has **26 focused test cases in the isolated local probe** and does not change P3 tests or fixtures. At new GitHub CI head a5d7f27bc, the **actual full backend collection check measured 886**, not the earlier arithmetic estimate of 885; no previous PASS is claimed. The next candidate's expected successful full-suite result is **886 passed**, of which **443** are the P3 suite **IF AND ONLY IF** its full backend CI succeeds. This is not a representation of already-executed results; historical P3 Windows **833 passed / 4 skipped** stays unchanged. The collection-integrity test checks that candidate expected total and must not be weakened.

Expected backend figure at this commit: **837 passed**, of which **443** are the P3
suite (`backend/tests/p3`). Verified by collection and by a full run on the
reviewed commit, not estimated:

| Suite | Tests |
|---|---|
| `backend/tests` (whole backend) | **837 passed** |
| `backend/tests/p3` (P3 suite) | **443** |
| ├ `test_p3_verification.py` | 29 |
| ├ `test_p3_extraction.py` | 26 |
| ├ `test_p3_edge_cases.py` (R06–R09) | 24 |
| ├ `test_p3_review_corrections.py` (R01–R05) | 21 |
| ├ `test_p3_rejection_recovery.py` (R21 rejection/recovery) | 21 |
| ├ `test_p3_ocr_integration.py` (R11/R12 pytesseract + Stage 2 TSV layout) | 23 |
| ├ `test_p3_ocr_provenance.py` (Stage 1/2 OCR confirmation, anti-FC-3, `/text`, `0005`) | 33 |
| ├ `test_p3_r17_safety.py` (R17 OCR substitution + fail-closed) | 24 |
| ├ `test_p3_r18_provenance.py` (R18 span exactness + bare label) | 14 |
| ├ `test_p3_stage3_verification_hardening.py` (Stage 3 `G11-D1`..`G11-D6`, `OD-2b` & `A1-Anchored`) | 31 |
| ├ `test_p3_windows_findings.py` (R13–R16) | 49 |
| ├ `test_windows_ocr_acceptance.py` (probe, W1 R21/source-confirmation, W2 FC-3 + handoff) | 111 |
| ├ `test_p3_upload.py` | 12 |
| ├ `test_p3_authorization.py` | 12 |
| └ `test_p3_fixtures.py` (incl. CRLF portability + PNG/JPEG legible bytes) | 13 |

> **R21 note (current figures).** This table previously read **635 passed** for
> the backend and **252** for P3. The R21 rejection/recovery work added 21 cases
> to `test_p3_rejection_recovery.py` (Stage 1), 2 authorization cases for the new
> patient-safe metadata, and 8 `0004` migration tests in
> `backend/tests/p2/test_p2_migration.py` (rebuild integrity, row preservation,
> CHECK-constraint survival, downgrade refusal, downgrade round trip, plus the
> populated P3 dependency graph and its downgrade/link cases), for +31 in
> total as of Stage 5.1; no pre-existing test was removed, renamed or skipped, and
> the pre-existing 635 remain among the 666 measured then. Stage 5.2 adds the 22
> W1 cases above on top of that, Stage 5.2a adds 14 W1 plumbing, validity and
> teardown regressions, and Stage 6a adds 6 Windows portability and test-isolation
> regressions (see the Stage 5.2 / 5.2a / 6a notes below).
>
> **Stage 5.2 (current figures).** The R21 W1 gate added 22 cases to
> `test_windows_ocr_acceptance.py` (17 -> 39), so the backend total moved
> 666 -> **688** and the P3 suite 275 -> **297**. No pre-existing test was removed,
> renamed or skipped, and the pre-existing 666 remain among the 688. Stage 5.1's
> populated-graph cases stay in `backend/tests/p2/`, beside the migration tests
> they extend.
>
> **Stage 5.2a (current figures).** Review follow-up on the W1 probe added 14
> cases to `test_windows_ocr_acceptance.py` (39 -> 53), moving the backend total
> 688 -> **702** and the P3 suite 297 -> **311**: end-to-end `_w1_run`
> plumbing with simulated OCR, a positive mapping control proving the same
> `report_a_glucose.txt` fixture promotes a `verified_document` glucose
> `Observation` when verified, unmappable/damaged OCR negative cases (`NOT RUN`,
> never vacuous `PASS`), mid-setup engine disposal and `main()` duplicate-row
> protection. These simulated-OCR tests prove W1's wiring only and are never
> Windows or real-Tesseract evidence.
>
> **Stage 6a (current figures).** Windows acceptance fixes added 6 regressions
> (`702 -> 708`, P3 `311 -> 314`): platform-semantic Windows `PATHEXT` executable
> identity check in `test_p3_ocr_integration.py` (16 -> 17), isolated Windows
> subprocess environment (`SYSTEMROOT`/`WINDIR`/`System32` preserved without host
> leaks, fixing `WinError 10106`) and `.gitattributes` LF policy verification in
> `test_p3_windows_findings.py` (47 -> 49), plus full `/health` dependency state
> (`not_configured`, `ok`, `unavailable`) and host-`TESSERACT_CMD` fixture
> isolation tests in `backend/tests/test_health.py` (+3).
>
> **Stage 6b.2 Stage 1, Stage 2 & Stage 3 (current figures).** Stage 1 (`8f7c007`/`e5d6dbb`)
> added 31 regressions (`708 -> 739`, P3 `314 -> 345`) in `test_p3_ocr_provenance.py`
> covering OCR confirmation, `/text`, migration `0005` safety, `max_page_text_chars`
> alignment (`20,000`), and synthetic retention. Stage 2 (`46ee188`) added 28 regressions
> (`739 -> 767`, P3 `345 -> 373`): `build_legible_scan_image` JPEG bytes + determinism
> in `test_p3_fixtures.py` (12 -> 13), TSV bounding-box layout reconstruction and
> real-subprocess TSV fallback checks in `test_p3_ocr_integration.py` (17 -> 23),
> anti-`FC-3` `1O5`->`105` confirmation and dual-path observation rules in
> `test_p3_ocr_provenance.py` (31 -> 33), and W1 negative provenance + W1 positive
> source-confirmation gates in `test_windows_ocr_acceptance.py` (53 -> 72).
> Stage 3 added 22 regressions (`767 -> 789`, P3 `373 -> 395`) in
> `test_p3_stage3_verification_hardening.py` enforcing `G11-D1`..`G11-D6` (fresh
> post-extraction `GET /file` audit ordering, `requires_source_confirmation` across
> all 5 OCR `FactField`s + `ambiguous_date` refusal, pending-sibling unit consistency,
> `_create_observation_from_mapping` defense-in-depth, and mandatory `reason` on OCR
> corrections and confusable digits `0`/`1`/`5`/`8`).
>
> **P3-G11 Step 2 (`A1-Anchored`, `OD-2b`, and non-vacuous `W2 / FC-3` — current
> figures).** Added 48 offline regressions (`789 -> 837`, P3 `395 -> 443`): +9 in
> `test_p3_stage3_verification_hardening.py` (22 -> 31) proving route-local
> post-rollback `AuditOutcome.ERROR` persistence (`OD-2b`), `A1-Anchored` source
> integrity checks (`ETag` + `X-Content-Type-Options: nosniff`, `(created_at, rowid)`
> `ERROR` invalidation with good re-read recovery, live SHA-256 rechecks in `verify.py`/
> `verification.py` preserving `R21` `rejected`, and `upload_dir` propagation), plus
> unmapped `13.4 g/dL` vs mapped `104 mg/dL` vs `M6` sibling attestation controls; and
> +39 in `test_windows_ocr_acceptance.py` (72 -> 111) covering non-vacuous `W2 / FC-3`
> acceptance on `report_ocr_o_confusion.txt` (`W2-R2` pinned canonical LF SHA-256
> `0f8cae89...` / 200-byte source check even when tampered text still retains `1O5`,
> `W2-R1` bounded `DERIVED` status strictly when unchanged `GOLD-EX-11` passes
> and W2 preserves/refuses `1O5` with zero Observations, and `W2-R3` requiring intact
> fact provenance `all_facts_pending`/`all_facts_tesseract`/`all_facts_require_source`
> plus `non_value_fact_count > 0` and required sibling fields `report_date`/
> `test_name`/`unit` before permitting `DERIVED`, while missing/unmappable/
> substituted-unmappable OCR stays `NOT RUN` or `FAIL`). Sandbox runs execute under
> Linux Python 3.11.2 (off-target compatibility evidence only; supported Windows
> Python 3.12 remains unexecuted). No real Windows Tesseract run occurred; `P3`
> remains **`IN_REVIEW`** and `GOLD-EX-11` remains **`FAIL / NOT PROVEN`**.
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


> **Windows CRLF note (P3-R10).** The repository `.gitattributes` pins
> `data/synthetic/documents/sources/*.txt` and `data/synthetic/documents/manifest.json`
> to `text eol=lf` so a fresh Windows checkout preserves the exact committed LF
> bytes even when `core.autocrlf=true` (keeping both `test_p3_fixtures.py` and
> `test_the_new_fixture_is_registered_with_a_correct_digest` exact against
> `manifest.json`). Do not add `core.autocrlf=false` locally; if you *do* see a
> hash mismatch on a fresh checkout, report the file and both digests.

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
| `W1 R21 rejection: OCR value fact` | a real Tesseract scan of `report_a_glucose.txt` produces a mappable numeric `value` fact (supported unit, `extractor='tesseract'`) and a mapping-eligible document | R21 W1 |
| `W1 R21 rejection: doctor rejection` | the **assigned doctor** rejects that exact fact; one decision row is stored | R21 W1 |
| `W1 R21 rejection: terminal failure` | stored `extraction_status='failed'` **and** `failure_code='measurement_rejected'` | R21 W1 |
| `W1 R21 rejection: no Observation` | **no** Observation references the rejected document's facts — a real assertion here, because this fixture's 104 mg/dL glucose would otherwise map | R21 W1 |
| `W1 R21 rejection: fact immutable` | the rejected fact keeps its `raw_text`, `normalized_value`, `quality_flags` and exactly **one** decision row | R21 W1 |
| `W1 R21 rejection: VI-002 stays open` | `VI-002` is still `state='open'` after the rejection (D-14) | R21 W1 |
| `W1 R21 rejection: re-decision refused` | a second decision answers `409 E_FACT_ALREADY_DECIDED` and appends **no** row | R21 W1 |
| `W1 source confirmation: OCR mappable candidate` | 40px legible `report_a_glucose.txt` scan yields mappable `104 mg/dL` `value` fact (`extractor='tesseract'`, `requires_source_confirmation=True`) | Stage 2 W1 |
| `W1 source confirmation: bare verify refused` | bare `POST /verify` (`decision='verified'`) without `GET /file` or confirmations answers `400 E_VALIDATION` | Stage 2 W1 |
| `W1 source confirmation: source retrieved and audited` | doctor calls `GET /file` (`200`) and `GET /text` (`200`), recording `document.file_read` / `document.text_read` audits | Stage 2 W1 |
| `W1 source confirmation: source-confirmed verification` | explicit `source_image_compared=True`, `confirmed_value='104'`, `confirmed_unit='mg/dL'` verify all facts to `document_status='verified'` | Stage 2 W1 |
| `W1 source confirmation: verified Observation created` | exactly **one** `verified_document` / `doctor_verified` glucose `104.0 mg/dL` Observation linked to `source_fact_id` | Stage 2 W1 |
| `W1 source confirmation: persisted provenance and audit safety` | `document_page_text` (`extractor='tesseract'`, matching SHA-256), exact span equality on all facts, `source_truth_notice`, zero leaked clinical text in `audit_event` | Stage 2 W1 |
| `W2 FC-3 source-aware` (`source fixture intact`, `OCR mappable 105 candidate`, `no autonomous promotion`, `unreviewed verify refused`, `R21 rejection blocks promotion`) | non-vacuous check on pinned `report_ocr_o_confusion.txt` (`sha256=0f8cae89…`, 200 canonical LF bytes, literal `1O5`): requires mappable `105 mg/dL` + siblings; reports nonblocking `DERIVED` **only** if unchanged `GOLD-EX-11` independently `PASS`es and W2 preserves/refuses `1O5` with 0 Observations, intact fact provenance (`pending`, `tesseract`, `requires_source_confirmation`), and complete required siblings (`report_date`, `test_name`, `unit`, `non_value_fact_count > 0`) (missing/unmappable/substituted-unmappable OCR or broken provenance stays `NOT RUN`/`FAIL`); confirms 0 pre-verify Observations, refuses bare/`source_image_compared` verify before `GET /file`, and proves R21 rejection blocks promotion without weakening `GOLD-EX-11` | P3-G11 W2/FC-3 |

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
| 23 | **W1 source confirmation** (6 rows: mappable candidate, bare verify refused, source retrieved/audited, confirmed verify, 1 linked Observation, persisted provenance + audit safety) | step 7 | | JSON gate entries |
| 24 | **`GOLD-EX-11`** | step 7 | **`FAIL` / NOT PROVEN — see §9** | JSON gate entry + raw OCR text |
| 25 | CI on the tested head | GitHub Actions | | run URL |

Row 24 is filled in **as a failure** unless the real engine genuinely stops
producing the `1O5` reading. See §9: a preserved `GOLD-EX-11` failure is a
**release blocker**, not a successful acceptance result.

---

## 9. Release blockers (any one blocks P3 acceptance)

> **Current interpretation:** These are the original **strict P1 technical requirements**. `GOLD-EX-11` still fails that technical requirement. The owner-ratified conditional P2 policy may allow a *separately approved, bounded synthetic educational application acceptance despite this known deviation*, only after all §12.2 evidence gates and final owner authorization/merge. Until then P3 is IN_REVIEW, and no other requirement is waived.

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
11. **`GOLD-EX-11` is not `PASS`.** Under strict P1 this remains an unresolved **technical release blocker**. Owner-ratified P2 allows a future *separate owner acceptance decision* to consider this disclosed technical deviation for synthetic-only education (§12); neither the executable GOLD test nor the recorded FAIL becomes PASS.

### On `GOLD-EX-11` specifically

`GOLD-EX-11` currently stands at **`FAIL / NOT PROVEN`**. The OCR reading of the
committed `report_ocr_o_confusion.txt` source still yields `1O5`, and P3's
acceptance criterion is that the pipeline flags it rather than repairing it to
`105`. Until a real-engine run shows the flagged behaviour, this gate **blocks strict P1 technical acceptance**. Under P2 a separate owner may conditionally accept the disclosed deviation for synthetic-only application use after all §12.2 checks, final review and main merge; no such final P3 approval is recorded yet.

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
**one strict P1 technical release blocker**. Conditional P2 acceptance, if later granted, must still report this deviation as a genuine OCR test FAIL.

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

- **`GOLD-EX-11` remains a strict P1 technical blocker** unless it genuinely turns `PASS` (see §9). A green CI or W1/W2 run does not prove OCR fidelity. Under the independently owner-ratified P2 text (§12), a separate final owner decision may instead conditionally accept that **disclosed technical deviation** for an educational application; that would never be a GOLD test PASS.
- Owner decision **D-14** (recorded in `docs/roadmap/PHASE_PROGRESS.md`) is applied
  to `DEMO_REVIEW_RULES.md` §4/§6.1: `VI-002` counts **active** candidates only,
  excluding a superseded original with valid `corrected_from_fact_id` lineage.
  It authorizes nothing else — no automatic verification, no deletion of history,
  no change to `map-1.0.0`.
- P3 remains `IN_REVIEW` until the owner reviews this evidence. The implementing
  agent does not mark PASS and does not merge.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

---

## 12. PROPOSED P2 conditional acceptance annex — NOT EFFECTIVE (2026-11-18)

> **Historical draft heading retained for links.** Current policy text is owner-re-ratified for integration review ([owner P2 policy re-ratification #6991001412](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6991001412)); this revised documentation still needs independent review and new-head CI, and final P3 acceptance is not yet approved or merged into `main`.

**CURRENT POLICY STATUS: OWNER-RATIFIED TEXT, NOT YET OPERATIONALLY IN FORCE.** Draft-only approval [#6986820279](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6986820279) was followed by ratification ([owner P2 policy re-ratification #6991001412](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6991001412)) and docs reconciliation authorization ([owner docs-only reconciliation authorization #6993612930](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6993612930)). Strict GOLD executable and Windows result remain unchanged; this bounded conditional educational policy still requires final owner P3 acceptance, main merge, independent review and new exact-head CI.

| Decision layer | Current P1 strict policy (EFFECTIVE) | P2 conditional academic policy (OWNER-RATIFIED; NOT YET EFFECTIVE) |
|---|---|---|
| `GOLD-EX-11` executable/JSON result | **FAIL / NOT PROVEN**, hence P3 acceptance blocked | **Same literal FAIL / NOT PROVEN**, reported as an explicit bounded technical deviation, *not* changed into PASS |
| Windows probe exit | **2**, preserve as nonzero | **2 remains 2**; never mask, override or modify exit status; document separate conditional **policy** decision |
| W1/W2 real-engine gates | Independently required to PASS | Independently required to PASS, including no autonomous promotion, authenticated source access, rejection and audit invariants |
| Supported platform/security | Windows Python 3.12, Tesseract, original fixture, source hash and immutable OCR provenance required | Unchanged; source SHA/access checks, correct role/document boundaries and `GET /file` anchor checks must remain effective |
| Human verification | Doctor reads original source, explicitly confirms values/siblings and reason before possible `doctor_verified` Observation | Unchanged **with explicit admission that source-read audit and attestation do not guarantee correct human visual comparison** |
| Approval | Final owner acceptance/merge not granted | Policy text re-ratified; this reconciliation needs new-head review/CI, and a separate final owner P3 phase/merge decision |

### 12.1 Measured counterexample and why P2 is not a technical repair

- **Frozen implementation:** `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`; Windows Python `3.12.9`; Tesseract `5.4.0.20240606`; attached original JSON 15,283 bytes with SHA-256 `9ac465722f011d538fd8045e393328fa4a0e2b1f10afd1b8e3488aff961f08cb`.
- **Actual OCR:** rendered source `1O5` (letter O) → engine text `105` (zero) → parser `raw_text='105'`, `normalized_value='105'`, `quality_flags=['clean']`. The parser had no preserved O to reject, so `GOLD-EX-11=FAIL` remains evidence of an unresolved upstream fidelity limitation.
- **Actual application controls:** all **13 W1** entries (7 terminal rejection and 6 source-confirmation) and all **five W2/FC-3** entries PASS. W2 prevents automatic Observation on a false-clean 105, refuses bare/unreviewed `POST /verify` (400), and enforces doctor decision/rejection. It does **not** detect or repair `1O5→105`; a doctor may falsely attest despite a valid `GET /file`.
- **Top-level accounting:** `PASS=27 / FAIL=1 / NOT RUN=0 / DERIVED=1`, process exit `2`; `GOLD-EX-07/08` coverage was DERIVED, not independently proven. Do not show the full run as all-green.

### 12.2 Proposed P2 eligibility checklist (ALL required; no auto-accept)

1. Verify exact reviewed PR #10 implementation head, complete source ancestry, file scope and clean evidence identity; check **authoritative CI PASS on the same PR head** and record supported Windows quality gate (12 PASS / 0 FAIL / 1 optional Playwright SKIP, with backend skip details disclosed). PR #10 was later moved with separate owner authorization to `4ec7d469d76ad89ffb7e27fbe18864bdc216ba46`, where Backend/Frontend CI passed. A new docs reconciliation commit requires its own fresh exact-head CI.
2. Preserve and attach **the original FAIL row and full 27/1/0/1 OCR JSON**, engine/version and rendered visual source hash. No mutation of fixture/source, parser, renderer, engine settings, OCR confidence threshold, or `GOLD-EX-11` function. Tests and executable gate must continue to fail on this captured false-clean reading.
3. Verify every **real-engine W1 and W2** acceptance row independently; require `ING-02`, `PDFIUM-01`, `GOLD-EX-05/06`, OCR provenance and verified original source bytes. A missing/failed row (including `NOT RUN`) remains a blocker, never a derived PASS.
4. Preserve **A1-Anchored** SHA/access/audit invalidation and R21 guarantees, per-fact review (not blind batch acceptance), no Observation before all required doctor confirmations, explicit confusable-digit reason and source linkage. Record that doctor **false attestation remains possible**; no safety assertion from source-read events alone.
5. Keep the deviation **limited to local synthetic teaching/demo**; prohibit real patient reports, diagnosis/triage, care instructions and autonomous clinical decisions or communications.
6. The exact P2 policy text was owner re-ratified ([owner P2 policy re-ratification #6991001412](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6991001412)). This reconciliation still requires independent diff/evidence review and new-head CI, then a **separate owner-authored final conditional P3 acceptance and main-merge decision** before any bounded educational policy can be operationally effective. Original strict §9 technical FAIL stays visible. No agent auto-acceptance or implied P4/P5 authorization.

**STOP** if any requirement is unverified, scope expands, baseline hashes change, or someone attempts to mark `GOLD-EX-11` technical PASS. A P2 policy *exception*, if eventually adopted, cannot be reused as evidence that OCR detects confusable glyphs.

**Present disposition (2026-11-19):** `P2 TEXT OWNER-RATIFIED / NOT YET OPERATIONALLY EFFECTIVE`; `P3=IN_REVIEW`; `GOLD-EX-11=FAIL / NOT PROVEN`, OCR exit 2; PR #11 MERGED into implementation branch, PR #10 DRAFT/UNMERGED to main. Independent reconciliation review, exact-head CI and separate final owner P3 acceptance remain pending.

*Educational and synthetic only; NOT FOR CLINICAL USE.*


> **P4-2b downstream collection checkpoint (2026-11-19; candidate only, NOT new P3 acceptance).**
> Owner-merged PR #17 has post-main CI SUCCESS at 154300096b33f2a03b4b0e74811eaf9ce40be30e.
> The combined P4-2a backend collection was 909 with P3 subset 443.
> This isolated DR-009 candidate now adds 19 collected test cases (18 authored
> functions, including two timestamp parameter variants), giving a provisional
> **928 backend / 443 P3** collection expectation, not an observed PASS.
> Conditional paired integrity token **928 passed**, of which **443** are the P3 suite
> applies ONLY if exact-head full GitHub CI demonstrates success. On mismatch
> update this P4 checkpoint after measurement, never edit prior P3 tests,
> provenance or scanner. Preserve historical P3 837/443, Windows 833 pass /
> 4 skip and real GOLD-EX-11 FAIL / NOT PROVEN.


> **P4-2d downstream collection checkpoint (2026-11-19; new offline candidate tests only, NOT new P3 acceptance).**
> The merged P4-2b baseline collected 928 backend / 443 P3 tests; the P4-2d
> candidate adds 39 collected tests in `test_p4_provenance_review_candidate.py`,
> so the **measured whole-backend collection** is now **967**, with **443** P3.
> Conditional paired handoff integrity token: **967 passed**, of which **443** are the P3 suite
> (this is a **collection expectation only**, **not** an assertion that 967 tests
> have passed). The initial P4-2d CI at 7f64295 failed solely because this
> existing count-integrity assertion still expected the outdated total.
> Keep original 837/443 historical P3, owner Windows 833 passed / 4 skipped,
> and real GOLD-EX-11 FAIL / NOT PROVEN untouched. No P3 executable, scanner,
> fixture or strict OCR policy changes are introduced by this addendum.


> **P4-2e downstream collection checkpoint (2026-11-19; internal read-only SQLite projection ONLY).**
> P4-2d collected 967 backend / 443 P3 tests. The proposed new P4-2e
> `test_p4_readonly_provenance.py` adds **9 expected collected** tests:
> **976 backend / 443 P3**, subject to exact-head CI collection verification.
> Conditional integrity-pair token: **976 passed**, of which **443** are the P3 suite
> (test-checking *syntax only*: this is **NOT** a claim of 976 successful
> tests until exact-head CI confirms them). No historic P3 source, fixture,
> scanner or Windows OCR outcome is modified; preserve real GOLD-EX-11
> FAIL / NOT PROVEN and original owner-accepted scope.


> **P4-2e actual exact-head collection correction (2026-11-19; appending, no historic overwrite).**
> GitHub Actions [PR run #44495402318](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44495402318)
> reached full Python pytest and the existing handoff integrity assertion
> **measured 977 collected backend cases** (P3 remains **443**). Our earlier
> **976** was a provisional, inaccurate estimate; it was never a green test
> claim. Correct conditional integrity token: **977 passed**, of which **443** are the P3 suite
> (**collection-check text only** until an exact-head successful CI run).
> The single CI failure was the outdated handoff count assertion, not a
> failure in the new source-projection behavioral tests. No P3 executable,
> acceptance policy, historical counts or OCR test outcome was changed.


> **P4-2f downstream test collection checkpoint (2026-11-19; selected-document preflight only).**
> PR #21 established **977 backend / 443 P3** collection. The new P4-2f
> `test_p4_document_preflight.py` adds **10 expected** synthetic migrated-SQLite
> tests; provisional whole-backend collection **987**, P3 unchanged at **443**.
> Conditional handoff integrity token: **987 passed**, of which **443** are the P3 suite
> (a **collection expectation**, **NOT** a claim that 987 tests passed; exact-head
> CI must verify it before owner merge). This appendix does not change historical
> P3 counts, Windows decisions, the OCR executable, scanner or GOLD-EX-11
> FAIL / NOT PROVEN.


> **P4-2f measured collection correction (2026-11-19; append-only).**
> [Push CI #44501826966](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44501826966)
> measured **988 backend collected tests**, including **443 P3** tests, at
> P4-2f head `a782ea885262a07cd78c6b938a36a917143f2a0d`. The previous
> 987 count was an estimate, not a verified pass. Corrected conditional
> integrity token: **988 passed**, of which **443** are the P3 suite
> (this sentence is only the **collection-pairing expectation** required by
> the existing handoff-integrity test; no 988 passing test claim until
> independent exact-head CI completes SUCCESS). The only reported pytest
> failure in this CI was the outdated handoff-count assertion; the new P4
> behavioral tests showed no failures. No P3 executable, scanner, past owner
> acceptance or GOLD-EX-11 OCR result is modified here.


> **P4-4/R4 provisional offline GOLD-A/B/C/D collection checkpoint (2026-11-19).**
> Owner approved R1-A (defer P4-3 persistence until genuine P5 workflow_run
> identity) and R4 (isolated synthetic offline golden component tests).
> Previously CI-measured whole-backend collection: **988 backend / 443 P3**.
> The new `test_p4_gold_abcd_offline_replay.py` declares nine tests, so provisional
> collected count **997 backend / 443 P3**; conditional integrity token
> **997 passed**, of which **443** are the P3 suite. This is a *collection
> expectation only*, NOT a claim of 997 passing tests. Exact-head CI must
> independently measure and pass; correct here append-only if wrong. The
> historical P3 Windows/OCR results, P3 test code, baseline and
> GOLD-EX-11=FAIL / NOT PROVEN remain completely unchanged.


> **P4 R2-A / C-35A / C-37A provisional test collection checkpoint (2026-11-19).**
> The owner approved **internal-only** scoped evidence inspection and explicit
> current/history comparison after merging PR #25. Base suite had **997 backend
> / 443 P3** cases. Two new P4 test modules define 18 test functions including
> parametrization for an expected **26** new collected cases: provisional
> **1023 backend / 443 P3**. Conditional handoff test-count token:
> **1023 passed**, of which **443** are the P3 suite. This is an **unverified
> collection estimate, not an assertion that 1023 tests passed**. Exact-head
> CI must measure the actual count and correct this append-only if wrong.
> No P3 test/executable/scanner/historical Windows decision changed.
> Real OCR GOLD-EX-11 remains **FAIL / NOT PROVEN**.


> **P4 R2-A measured backend collection correction (2026-11-19; append-only).**
> Exact-head [CI #44522832450](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44522832450)
> at `5f812857c2c6490292d747efbe56e98c964c5e24` measured
> **1025 backend collected cases / 443 P3**, not the provisional
> 1023. Updated conditional collection integrity token **1025 passed**,
> of which **443** are P3 (token is **NOT** evidence that 1025 tests passed;
> it is a pairing assertion for the existing handoff check).
> Three *actual* reported failures were: this outdated estimate,
> an incorrect exclusion-reason expectation, and a test helper query that
> autoflushed a dirty row before the preflight was called. The test helper
> now pins patient ID before editing, preserving the dirty-session guard.
> The real expected exclusion reason for a pending-source document is
> `verified_lineage_unavailable`; it must not be relabeled as a cleared source.
> All tests must be rerun on a new exact head. No P3 executable, scanner,
> historic owner result or real OCR GOLD-EX-11 outcome was changed.


> **P4 R2-A suite-count pairing clarification (2026-11-19, append-only).**
> [Exact-head CI #44523738265](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44523738265)
> collected **1025** backend tests, including **443** tests from the P3 suite.
> The existing P3 handoff integrity assertion requires this exact *conditional*
> collection-pairing string: **1025 passed**, of which **443** are the P3 suite.
> **This is a collection-count token ONLY, not a statement that 1025 tests
> actually passed.** On the cited run, backend test execution had a single
> failure: the historical handoff pairing guard was expecting this sentence.
> The new P4 behavior tests reported no failures. All checks must rerun on the
> following exact head and pass before any owner merge. No test was disabled,
> no old P3 claim was overwritten, and real OCR GOLD-EX-11 stays FAIL / NOT PROVEN.


> **P4 R3-A owner-pinned synthetic reference provisional count (2026-11-21, append-only).**
> After the owner merged PR #27 and explicitly approved R3-A and R21-S1,
> a new fixture-only policy YAML and a reference test module add **26 expected
> collected test cases** to the previously CI-measured **1025** backend cases,
> unchanged **443** P3 cases. Exact conditional collection pairing token
> for the existing P3 handoff integrity test:
> **1051 passed**, of which **443** are the P3 suite.
> This **1051 is a provisional collection-count token, NOT evidence of actual
> tests passing**. Confirm/reconcile from exact-head GitHub Actions; no historical
> P3 test count, P3 executable, scanner control or real Windows/OCR result is edited.
> Owner Windows gate is still required before merging the code PR.


> **P4 R21-S1 offline matrix provisional suite count (2026-11-21, append-only).**
> Owner-merged PR #28 established backend **1051** collected cases with
> unchanged **443** P3 cases. The new R21-S1 offline migrated-SQLite test module
> contains 19 test functions, with **25** expected parametrized cases,
> so the new expected collection is **1076** backend / **443** P3.
> The existing P3 handoff guard requires an exact conditional *collection token*:
> **1076 passed**, of which **443** are the P3 suite.
> **This is NOT evidence that 1076 tests passed**; exact-head CI must independently
> measure collected/executed results, and any mismatch must be corrected by
> append-only note. No P3 executable, prior owner decision, historical OCR
> failure, or quality gate was changed. Isolated Windows gate still required.


> **P4 R21-S1 measured backend collection correction (2026-11-21; append-only).**
> Exact-head [GitHub CI #44906944016](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44906944016)
> measured **1077 total backend collected cases**, not provisional 1076,
> and unchanged **443** P3 tests. The conditional *collection-pairing marker*
> required by the existing P3 acceptance guard is:
> **1077 passed**, of which **443** are the P3 suite.
> This sentence is **not a claim of 1077 passing tests**; cited CI had two
> failures: the outdated handoff collection token and the new R21 test's
> ORM autoflush in its own helper before the production dirty-session guard.
> The test now captures patient/document IDs *before* mutation and directly
> calls the inspector with a dirty Session, preserving the fail-closed guard.
> **No historical P3 test/code/scanner or real OCR result has changed.**
> Re-run full exact-head CI and require owner Windows gate before merge.

> **P5-F0 owner-approved historical-count compatibility note (2026-11-21; append-only, not an OCR acceptance result).**
> Under the explicit owner [PR #31 legacy-test exception](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31#issuecomment-7064518944), the original historical P1/P2/P3 counts and every earlier conditional `N passed` marker above are retained as historical records. [Exact-head red backend CI #44914856359](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44914856359) measured **1096 collected**, of which **443** are the P3 suite. **This is the recorded collected test count, NOT a claim of 1096 tests passing.** Six historical compatibility assertions failed at that head, while all P5-F0 tests were absent from its failure summary. This is a measured collection-pairing token for the updated integrity guard, which now distinguishes `collected` from `passed`. A green exact-head CI and isolated owner Windows gate remain required before P5-F0 merge. No P3 source/executable/scanner change, no reclassification of real Windows `GOLD-EX-11 = FAIL / NOT PROVEN`, no new proof of glyph or OCR validity; **NOT FOR CLINICAL USE**.

> **P5-F1 0007 exact compatibility checkpoint (PR #33, 2026-11-21; not a test PASS).**
> Under owner [explicit six-path legacy compatibility authorization](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33#issuecomment-7070068019), historical P3 run figures and the original P3-only **443** test cases remain unchanged. The last pre-exception [CI #44924018806](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44924018806) measured **1116 backend collected** and **six unrelated historical 0006/count-assumption failures**; it did **not** establish 1116 passing tests. The P5-F1 candidate then added **one** new parametrically unexpanded test that executes the smoke checker across 0007, historical 0006, 0005, 0004, 0003, 0002, 0001 and base, giving a **provisional** `1116 + 1 = 1117` case collection expectation pending exact-head CI. For the *current* candidate's integrity-check pairing only, the required **collection** token is **1117 collected**, of which **443** are the P3 suite. This paired token is **NOT** a claim that 1117 cases have passed. If exact-head pytest collection differs, correct this current-only pairing and investigate; never rewrite the historical 837 P3 handoff result or a past conditional test run.
>
> The new migration adds only `run_gate_evaluation` and `run_gate_blocker` at `0007_p5_run_gate`. The separate `p5_f0` smoke state preserves `0006_p5_run_foundation` exact F0 shape, and every older state retains strict P3/P2/P1 checks. This change does not alter ingestion, OCR, historical `VI-002`, Windows acceptance evidence or real `GOLD-EX-11=FAIL / NOT PROVEN`. F1 remains `IN_REVIEW`; exact-head CI and owner isolated Windows tests are required before merge. **SYNTHETIC / NOT FOR CLINICAL USE.**

> **P5-F1 last-minute provenance hardening collection checkpoint (PR #33, synthetic test suite; provisional).**
> Following the first F1 compatibility checkpoint's **1117 expected collected** tests,
> four further *new* synthetic P5-F1 tests were authored for (1) raw extracted-text
> fingerprint changes, (2) unknown quality flags, (3) replay rejection of an
> inserted forged gate blocker and (4) two simultaneous run-gate attempts. There
> were no removals, skips or parametrization changes to the original 443 P3
> cases. Accordingly this updated **provisional collection-pair token** is
> **1121 collected**, of which **443** are the P3 suite; this is arithmetic
> on the prior pending candidate, **NOT evidence that 1121 tests passed**.
> Correct it if the exact final head's pytest collection differs. The accepted
> P3 historical results and real `GOLD-EX-11 FAIL / NOT PROVEN` remain unmodified.
> The new F1 cases concern synthetic software consistency, not clinical validity.

> **P5-F2 PR #35 owner-approved collection-pairing compatibility note (2026-11-22; collection, NOT test PASS).**
> Repository owner `Muhammed-Fathi` explicitly approved the **one-document, append-only**
> [collection-only exception](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/35#issuecomment-7075105100).
> The exact-head [GitHub CI #44979500529](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44979500529)
> at `f09d4d97a39fc40a3fb34bd625523e94a76e293e` measured the **current**
> backend test suite as **1140 collected**, of which **443** are the P3 suite.
> The added synthetic P5-F2 tests increased the backend collection while the
> historical P3 test suite remained unchanged. **1140 collected does NOT mean
> 1140 passed**: that prior CI run actually **FAILED** the strict paired-count
> documentation guard because the prior handoff recorded 1121 collected.
> All historical P3 handoff results, earlier provisional/current-at-that-time
> collection tokens, real source OCR `GOLD-EX-11 = FAIL / NOT PROVEN`, and
> original P3 safety evidence are preserved verbatim. No P3 test, tolerance,
> gate criterion, code, source fixture, or CI job has been altered under this
> exception. A new exact-head full CI SUCCESS and independent owner Windows
> acceptance remain mandatory before any PR #35 merge. F2/P4/P5 are not
> declared accepted; SYNTHETIC EDUCATIONAL / NOT FOR CLINICAL USE.

> **P4-RB1 PR #37 owner-approved current collection pairing (2026-11-22; NOT a PASS)**
> Under the owner-only [PR #37 exact one-path exception](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/37#issuecomment-7076184528), after recording its exact authorization in the append-only roadmap, the new RB1 synthetic-only tests cause the current backend suite to comprise **1155 collected**, of which **443** are the P3 suite. This pairing was measured in [Push CI #44998192004](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44998192004) and [PR CI #44998195330](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44998195330) on exact RB1 head `863731f01e5e74c2cac74bb4ca8710acee397591`, where Ruff lint/format and Frontend succeeded but Backend Pytest **FAILED the collection-handoff assertion** because this current token did not yet exist. **1155 collected is NOT a claim that 1155 tests passed**, and the previous red jobs do NOT establish Alembic/OpenAPI/secret-scan success.
> This new RB1 collection count does **not** change the previously valid F2 **1140 collected** checkpoint, any original P3 **443** collection, past Windows acceptance results, the historical `GOLD-EX-11 FAIL / NOT PROVEN` real OCR outcome, or any P3 test, OCR source, fixture, tolerance, gate, workflow, scanner, migration or clinical claim. A newly executed full CI on the final PR #37 head and independently checked owner Windows acceptance are still mandatory before any merge. P4 remains **IN_REVIEW**, overall P5 unaccepted; SYNTHETIC EDUCATIONAL — **NOT FOR CLINICAL USE**.


> **P4-RB2 PR #41 owner-approved collection-only checkpoint (2026-11-22; collection, NOT test PASS).**
> Repository owner `Muhammed-Fathi` explicitly authorized this one-document, append-only update via the exact standalone marker in [PR #41 Conversation comment #7077204700](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7077204700), verified before this edit. The exact candidate-head [PR CI #45006638723](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45006638723) at `8c5a171214264a4763e12e00c9b552ab29662c5e` measured **1204 collected** across the current whole backend suite, of which **443** are the unchanged P3 suite. **1204 collected does NOT mean 1204 passed.** That CI run's Backend Ruff lint and Ruff format succeeded and Frontend Node 22 succeeded, but Pytest **FAILED exactly one** historical collection-pairing assertion, `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes`, because this exact `**1204 collected**` token had not yet been appended. The failure summary did not report an RB2 evaluator test failure; this does not independently certify RB2 acceptance. Backend Alembic, OpenAPI and secret/artifact scan steps were not reached after Pytest failed. Independent owner Windows PowerShell 5.1 exact-head `setup.ps1` and `test_all.ps1` have **NOT RUN**.
>
> This is only a current collection-pairing note. All prior 1096/1116/1121/1140/1155 checkpoints, the original P3 **443** suite count, every historical Windows result and every OCR status are preserved verbatim. No P3 source, executable code, test, fixture, scanner, tolerance, workflow, gate or prior result was changed. Real `GOLD-EX-11 = FAIL / NOT PROVEN` remains unchanged. A new full exact-final-head CI SUCCESS and independent owner Windows acceptance are mandatory before PR #41 can be considered for merge. P4 remains **IN_REVIEW**, P5 is not accepted, and this synthetic offline work is **NOT FOR CLINICAL USE**.


> **P4-RB2 exact collection guard token (2026-11-22; formatting-only supplement to the owner-approved append):** **1204 collected**, of which **443** are the P3 suite. This exact adjacent phrase satisfies the historical collection-pairing assertion. It remains a **collection count, NOT 1204 tests passed**. The preceding CI [#45008087818](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45008087818) still failed exactly that one assertion because the earlier append inserted descriptive words between the two tokens. No count or historical result changed; no P3 source/test/fixture/Windows/OCR content was modified. A fresh exact-head full CI is required.

## P4-RB2 owner-authorized collection-only pairing (2026-11-22)

On the unchanged P4-RB2 Arena test tree `58eb9992fd0a9e33876b462c0c76eaa3d5c84908`, local Linux Python 3.11.2 with hash-locked development dependencies measured **1255 collected**, of which **443** are the P3 suite. Relative to the historical 1204 whole-backend pairing, the additional 51 collected cases are RB2 regression coverage; this is **collection, not 1255 tests passed**. The previous historical handoff collection guard failed when the 1255 token was absent; the user-supplied independent reviewer identified that assertion in [CI #45038253453](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45038253453). That log finding is attributed to the reviewer, not independently retrieved by this session.

This append is authorized solely by owner `Muhammed-Fathi`'s exact standalone [1255 collection-only decision](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7083447073), as scoped by [request #7081201222](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7081201222). All earlier P3 evidence is preserved. No fresh Windows acceptance or overall CI success is claimed. The original real `GOLD-EX-11 FAIL / NOT PROVEN` remains unchanged. ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

## P4-RB3 PR #43 owner-authorized collection-only pairing (2026-11-23; NOT test PASS)

Under repository owner `Muhammed-Fathi`'s explicit standalone authorization `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY` ([PR #43 Conversation comment #7102539192](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102539192), `2026-11-23T13:26:34Z`), verified and recorded in `docs/roadmap/PHASE_PROGRESS.md` prior to editing this file, local Linux Python 3.11.2 pytest collection on the finalized P4-RB3 Round-3 branch measured **1282 collected**, of which **443** are the P3 suite. Relative to `main@6d121228a9e742849337366c6880a2cb887b1486` (`1257` collected), the added `25` P4-RB3 tests (`18` service tests in `backend/tests/p4/test_p4_rb3_review_persistence.py` plus `7` migration guards in `backend/tests/p4/test_p4_rb3_migration_guards.py`) bring the whole-backend suite to `1282` collected while the historical P3 test suite remains untouched at `443`. This is strictly a **collection count, NOT a claim that 1282 tests passed**.

All historical P3 results, prior collection checkpoints (`1096`/`1116`/`1121`/`1140`/`1155`/`1204`/`1255`), original Windows PowerShell 5.1 acceptance records, and real source OCR `GOLD-EX-11 FAIL / NOT PROVEN` remain preserved verbatim without modification. No P3 test, source fixture, OCR tolerance, gate, scanner, or clinical claim was changed. Exact-head CI and independent owner Windows acceptance remain mandatory before any merge. P4 remains **IN_REVIEW**; overall P5 remains **NOT ACCEPTED**; **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**


## P4-RB4 PR #45 owner-authorized collection-only pairing (2026-11-23; NOT test PASS)

Under repository owner `Muhammed-Fathi`'s explicit standalone authorization `APPROVE-P4-RB4-P3-HANDOFF-COLLECTION-ONLY` ([PR #45 comment #7111663704](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/45#issuecomment-7111663704), `2026-11-23T19:28:46Z`), verified and recorded in `docs/roadmap/PHASE_PROGRESS.md` prior to editing this file, local Linux Python 3.11.2 pytest collection on the P4-RB4 implementation tree `baff43e08e7549d0776829cc134f6be539439dbd` measured **1294 collected**, of which **443** are the P3 suite. Relative to the prior **1282** whole-backend pairing, the 12 additional collected cases are the authorized RB4 genuine run-backed GOLD A/B/C/D integration tests in `backend/tests/p4/test_p4_rb4_run_backed_gold.py`; the P3 suite is unchanged at 443. **This is the recorded collected test count, NOT a claim that 1294 tests passed.** The exact-head [push CI #45245954024](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45245954024) and [PR CI #45246015431](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45246015431) at that head failed the Backend tests step on this very collection-pairing guard before this append.

All historical P3 results, prior collection checkpoints (`1096`/`1116`/`1121`/`1140`/`1155`/`1204`/`1255`/`1282`), original Windows PowerShell 5.1 acceptance records, and real source OCR `GOLD-EX-11 FAIL / NOT PROVEN` remain preserved verbatim without modification. No P3 test, source fixture, OCR tolerance, gate, scanner, migration, production path or clinical claim is changed by this append. A new exact-head CI run and independent owner Windows acceptance remain mandatory before any merge. P4 remains **IN_REVIEW**; overall P5 remains **NOT ACCEPTED**; **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P5-S0 Round 2 collection re-measurement (2026-11-24)

Current collection, measured on the P5-S0 Round-2 tree before this note was written: **1447 collected**, of which **443** are the P3 suite. The P3 suite is unchanged at 443 and no test was deleted; the whole-backend total moved from 1420 to 1447 through the P5-S0 typed-state test rewrite (124 -> 150 collected) plus the owner-authorized D-14 rejection test and the parametrized typing cases that now cover the two authorized `backend/app/agents` modules. This is **collection evidence only**: it is not a passed-test count, not a new Windows acceptance and not a test result. Executed locally on Linux CPython 3.11.2 (CI uses 3.12); Windows `test_all.ps1` was not run by the agent.

## P5-S0 Round 3 collection re-measurement (2026-11-24)

Current collection, measured on the P5-S0 Round-3 tree before this note was written: **1466 collected**, of which **443** are the P3 suite. The P3 suite is unchanged at 443 and no test was deleted; the whole-backend total moved from 1447 to 1466 through 19 added P5-S0 typed-state tests (150 -> 169 collected). This is **collection evidence only**: it is not a passed-test count, not a new Windows acceptance and not a test result. Executed locally on Linux CPython 3.11.2 (CI uses 3.12); Windows `test_all.ps1` was not run by the agent.
