# P3 E1–E3 v1.1.3 — Canonical Baseline Wrapper Warning Incident (2026-11-18)

> **Status: ATTEMPTED / OUTCOME UNKNOWN — evidence collection required, NOT a canonical PASS or FAIL determination.** The owner Windows `canonical_baseline` launch reached pinned `[PREFLIGHT OK]`, and independent protected-baseline postflight returned PASS, but the outer PowerShell 5.1 wrapper aborted on a Python deprecation warning redirected from stderr. No `CANONICAL_BASELINE_EXIT_CODE` was recorded in the supplied transcript. Do not rerun before inspecting the already-created evidence folder.

## Observed exact owner-machine evidence

Owner executed the separately reviewed `Run-AI-Doctor-E1E3-v113-CANONICAL-BASELINE.ps1` on Windows PowerShell 5.1. The supplied console excerpt showed:

- `[1/6]` ZIP + all five members verified; pinned acceptance checkout HEAD `af2bfd226cc53b5c4665c160a6d8310abcce8b53`, clean.
- `READ-ONLY BASELINE PREFLIGHT: PASS`.
- `V1.1.3 PROBE-ONLY EVIDENCE: VERIFIED / PASS`.
- `[4/6] Execute ONLY canonical_baseline, with DEFAULT rules and NO frozen-rule writes`.
- `[RUNTIME]` Python 3.12.9 / Pillow 13.0.0, `[PREFLIGHT OK] Mode=canonical_baseline`, protected DB SHA `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`.
- Then owner console reported `DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 ...` from the original v1.1.3 diagnostic Python file at line **2665**, converted by outer PowerShell to `NativeCommandError` pointing at wrapper line **88**.
- The outer wrapper executed its `finally` and returned `PROTECTED BASELINE POSTFLIGHT: PASS`, with log path:
  `E:\DEPI\P3-Diagnostics\canonical_baseline_v113_review_20261118_141738271_e98816ac\canonical_baseline_output.txt`.
- **Not observed:** the Python run directory, `records.jsonl`, `metrics_summary.json`, `manifest.json`, completion count and final exit code. These are **unknown**, not inferred from the clean postflight.

## Independently inspected source cause

In the submitted outer PowerShell script:
```powershell
$ErrorActionPreference = 'Stop'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -Mode canonical_baseline 2>&1 |
    Tee-Object -FilePath $Log
$ExitCode = $LASTEXITCODE
```

The parent PowerShell 5.1 pipeline receives Python's **stderr** warning from the nested PowerShell subprocess via `2>&1`. With `$ErrorActionPreference='Stop'`, an emitted native stderr record can cause an outer `NativeCommandError` terminating condition before the code storing `$LASTEXITCODE` executes. The original `run_e1_e3_diagnostic.ps1` launcher and guarded Python source were **not modified**. Inspection of pinned v1.1.3 Python source confirms `list(sub.getdata())` at line 2665 (and other `getdata()` usage), which Pillow 13 emits a deprecation warning about; this alone does not establish an OCR-engine failure.

**Important distinction:** `PROTECTED BASELINE POSTFLIGHT: PASS` verifies integrity of protected resources; it does **not** verify the Python experiment completed, recorded all three specimens or exited 0.

## Required next gate: evidence-only forensics (NO rerun)

Inspect **existing** `E:\DEPI\P3-Diagnostics\run_*_canonical_baseline_*` folders and the original log; identify whether `manifest.json`, `metrics_summary.json`, `records.jsonl` and `records.csv` exist. If all are present, compare their data, hashes, completeness and three specimen records against protected pre/postflight. If absent/partial, label run INCOMPLETE and independently review any revised wrapper before considering a separately authorized rerun. Never overwrite any earlier evidence.

Read-only inspection script prepared separately for the owner:
`Inspect-AI-Doctor-v113-CANONICAL-EVIDENCE-READONLY.ps1` — this script invokes **no diagnostic mode and performs no writes**, only checks clean pinned HEAD and protected DB SHA, lists run folders and summarizes available evidence paths/fields.

**Governance:** P3 remains `IN_REVIEW`, GOLD-EX-11 `FAIL / NOT PROVEN`. `exploratory`, `holdout`, frozen rules, phase acceptance/merge and P4/P5 remain NOT AUTHORIZED. Docs-only PR #11 is still a draft; no file-scope exception or merge is implied.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.


---

## Follow-up — owner read-only disk inspection (2026-11-18)

**Evidence status upgraded from “no files inspected” to “all four evidence files present; summary claims complete”; full specimen scientific assessment remains PENDING.** This follow-up supersedes the earlier *unknown file-presence* statement only; it does not replace an independent review of actual file contents.

Owner ran `Inspect-AI-Doctor-v113-CANONICAL-EVIDENCE-READONLY.ps1`, explicitly reporting **`DIAGNOSTIC MODES: NONE`**, `PROTECTED READ-ONLY CHECK: PASS`, pinned clean worktree HEAD `af2bfd226cc53b5c4665c160a6d8310abcce8b53`, and unchanged protected DB SHA `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`.

Owner discovered **one** canonical run folder:

`E:\DEPI\P3-Diagnostics\run_20261118T121739_753329Z_canonical_baseline_0e5a8b3d`

| Existing evidence file | Reported file size | Interpretation |
|---|---:|---|
| `manifest.json` | 17,456 bytes | Present, contents not yet uploaded |
| `metrics_summary.json` | 54,330 bytes | Present, contents not yet uploaded |
| `records.jsonl` | 46,463 bytes | Present, **3 nonblank lines** (record contents not yet uploaded) |
| `records.csv` | 1,625 bytes | Present, contents not yet uploaded |
| Original outer `canonical_baseline_output.txt` | 1,096 bytes | Only runtime and `[PREFLIGHT OK]` present; warning stopped parent logging |

**Read-only inspector-reported fields:** `HARNESS_VERSION=1.1.3`, `SPLIT=canonical_baseline`, `SUMMARY_EXIT_CODE=0`, `COMPLETE=True`, `COVERAGE_STATUS=COMPLETE`, `POSTFLIGHT_PASSED=True`, `PROTECTED_DB_UNCHANGED=True`, and `RECORDS_JSONL_NONBLANK_LINES=3`.

**Narrow conclusion:** the harness apparently completed and wrote the expected three specimen records **despite** the parent PowerShell `NativeCommandError`. The saved summary's internal exit code is 0, **but that is not the missing outer wrapper exit code**. No independent validation of specimen outcomes, classification confusion matrix, guardrails or per-record provenance is possible without the existing four files.

**Required next action:** Upload those exact four existing files **plus the original 1,096-byte outer log** for independent in-depth content consistency and scientific assessment. No rerun, no retuning, no overwrites, no new diagnostic modes. `GOLD-EX-11` remains `FAIL / NOT PROVEN` until acceptance-specific evidence is evaluated; P3 stays `IN_REVIEW`.

No code/fixtures, database, or executable source was changed by this documentation-only follow-up.
