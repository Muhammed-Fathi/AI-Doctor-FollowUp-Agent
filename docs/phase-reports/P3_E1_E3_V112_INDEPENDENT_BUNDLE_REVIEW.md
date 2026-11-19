> **Historical inspection record (2026-11-18):** This document was written before owner Windows `plan_only`/`probe_only`. Its next-step authorization was superseded by subsequent Windows evidence. Read `P3_E1_E3_V112_WINDOWS_EVIDENCE.md` for the current state: `plan_only=PASS`, `probe_only=INCOMPLETE (exit 13)`, and no authorization for further modes.

# AI-Doctor-FollowUp-Agent — E1–E3 Diagnostic Harness v1.1.2
## Independent bundle inspection — 2026-11-18

**Decision:** Conditional approval to run **only** the bundled `run_e1_e3_diagnostic.ps1 -Mode plan_only` on the pinned Windows acceptance checkout, after confirming the extracted files still match the hashes. **No authorization** for `probe_only`, `canonical_baseline`, `exploratory`, `freeze_rules_only` or `holdout`. P3 stays `IN_REVIEW`; GOLD-EX-11 stays `FAIL / NOT PROVEN`.

## Evidence inspected

User-provided `e1_e3_windows_diagnostic_bundle(5).zip` received and read in the sandbox.

- Size: **91,290 bytes**
- SHA-256: `baa0ce745a2f582433b0fe37061c8f0f41ca05ce2da1c12b50f39b1fb0446437`
- ZIP integrity: `zipfile.ZipFile.testzip() is None`
- Exactly the five expected regular files; no unexpected archive members.

| File | SHA-256 | Result |
|---|---|---|
| `e1_e3_windows_diagnostic.py` | `18654128634232808c0084116c70116d3d406278fd9fc152324faa5f9a5c1be5` | MATCH |
| `run_e1_e3_diagnostic.ps1` | `a45193aa7a19d3681e9ef3a6b4faa3a8ca993b28e9ba9f97d8f5d30c8c3b90bb` | MATCH |
| `test_e1_e3_diagnostic.py` | `2144690ce756dac56d37bcc06f106139e831297835d5982913f141c985a35f42` | MATCH |
| `SELFTEST_AND_PLAN_OUTPUT.txt` | `c5dd82936eb7aa8a24aacc5862ca68d766c24a329d4d02c2c7c15c3a87429e1c` | MATCH |
| `SHA256SUMS.txt` | `1eccb2391618c60c24e2594158f5e0246da702df2106b701451ca9d284d42e4f` | MATCH |

All entries in `SHA256SUMS.txt` agree with the independent file hashes.

## Static audit of `plan_only`

- PS1 `param` / default paths: lines 37–59; pinned commit `af2bfd226cc53b5c4665c160a6d8310abcce8b53`; protected DB expected SHA `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`.
- PS1 destination checks: lines 64–171; refuses forbidden diagnostic-root paths and reparse-point ancestors.
- PS1 Python resolution: lines 253–315; uses pinned checkout `.venv\\Scripts\\python.exe` or explicitly provided `-PythonExe`, rejects incompatible Python/Pillow and tests `ImageFont.load_default(size=40)`.
- PS1 protected preflight: lines 317–357; HEAD, clean worktree, protected DB SHA and presence; in `plan_only`, Tesseract presence is *not required* and diagnostics root is not automatically created.
- PS1 mode routing: lines 359–405; `plan_only` passes `--plan-only` (not `--split`).
- PS1 finally: lines 407–470; verifies HEAD, worktree, protected and worktree DB, restores environment variable.
- Python `run_plan_only`: lines 5699–5771; uses `run_preflight_checks` with `require_tesseract=False`, then `build_specimen_plan` and `compute_plan_readiness` and prints JSON. No OCR subprocess and no artifact writing within the examined `plan_only` path.
- Python `main`: lines 5802–5819; `--plan-only` returns before `execute_diagnostic_run`.
- Python preflight: lines 4112–4216; checks runtime, pinned HEAD, repo state, DB and pinned source files, strict (selectively 3-way CRLF) hash rules, fonts.
- Python plan readiness: lines 1353–1420; separates `plan_valid` from `execution_ready` and full font coverage. `plan_only` returns exit 10 if not execution-ready, even when structurally valid.

### Audit qualifications

1. `run_plan_only` does not run its own Python postflight; the bundled PS1 wrapper supplies the after-execution checks. The approval specifically requires **launching through this PS1**, not invoking the Python script directly.
2. The PS1 wrapper checks the protected/working DB and git state afterward, but does not duplicate Python's postflight per-file digest audit. In this `plan_only` path the source files are only read. This is a scope limitation, not evidence of file modification.
3. The 36/36 tests in `SELFTEST_AND_PLAN_OUTPUT.txt` are **reported historical self-tests** (the transcript itself matches the verified ZIP). Do not mistake them for live Windows evidence.
4. Existing `plan_only` could return exit 10 due to missing fonts or incompatible interpreter. Preserve and inspect the JSON errors; never modify golden fixtures or relax controls to force an exit 0.
5. No standalone Windows PowerShell runtime, actual Tesseract, `probe_only`, or canonical baseline was executed during this review. Approval is **not** a P3/GOLD-EX-11 acceptance verdict.

## Independent execution in this sandbox

- Parsed Python AST syntax for `e1_e3_windows_diagnostic.py` and `test_e1_e3_diagnostic.py`: **PASS**.
- Executed **six targeted** bundled `unittest` cases in the isolated Linux sandbox: **6 passed, 0 failed** (mock/stub and safety tests, not real OCR):
  - static PowerShell `finally`/StrictMode guard checks
  - Pillow Aileron BytesIO resolution/non-substitution with fake PIL
  - atomic collision-safe run directory creation in temp space
  - real CLI `plan_only` failure on non-pinned repo (fail-closed)
  - confusion matrix / Wilson interval calculations
  - hOCR seven-state classification with synthetic data
- The **entire 36-test suite** was **not rerun here**, because some tests depend on local pinned Git source fixtures not present in this isolated sandbox. This review must not be presented as independent 36/36 execution.
- Windows-specific acceptance: **NOT RUN**.

## Next authorized action

On owner's Windows PowerShell 5.1, in the verified recovery evidence directory, re-check the SHA-256 of at least the PS1 and Python launcher files, then execute **only**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'E:\DEPI\P3-Diagnostics\bundle_review_v1_1_2_20261118_114140934_93c33819\run_e1_e3_diagnostic.ps1' -Mode plan_only
```

Capture all output and the native process exit code. Check: `preflight_passed`, `plan_valid`, `execution_ready`, `runtime_provenance`, missing fonts, and `[POSTFLIGHT OK]`. If the run fails or returns exit 10, stop and inspect rather than proceeding. No further modes until separate authorization after review of the real Windows output.

**Safety label:** EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
