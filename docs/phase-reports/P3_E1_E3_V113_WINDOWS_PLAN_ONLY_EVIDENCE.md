# P3 E1–E3 v1.1.3 — Owner Windows `plan_only` verification

**Observed date:** 2026-11-18. **Evidence source:** owner-executed Windows PowerShell transcript `Pasted text(20261118-115327).txt` and saved `plan_only_output(1).txt` uploaded for independent review. Both decoded and parsed; the saved log was UTF-16LE, and the JSON objects matched exactly between saved output and full transcript. The reviewer did **not** execute Windows commands or Tesseract. **Gate decision: `plan_only` PASS; separate conditional permission for `probe_only` ONLY.**

**Governance state:** P3 **IN_REVIEW**, PR #10 and docs-only PR #11 still draft/unmerged. `GOLD-EX-11 = FAIL / NOT PROVEN`. `canonical_baseline`, exploratory, holdout and rules freezing remain **NOT AUTHORIZED**. Source is synthetic-only and not for clinical use.

## Owner Windows command and exact local provenance

- The owner ran an independently prepared, hash-verifying wrapper, `Run-AI-Doctor-E1E3-v113-PLAN-ONLY.ps1`, which verified the release ZIP and the five extracted member SHA-256 hashes and then invoked only `run_e1_e3_diagnostic.ps1 -Mode plan_only`.
- ZIP: Authenticated Draft Release 449889565, 85,170 bytes; SHA-256 `d620208ff0811b7ec6372bc96174cd302daed4dc37664acd104aba5d27cc3cb5`.
- Acceptance worktree: `E:\DEPI\P3-Acceptance-af2bfd226cc5`; HEAD exactly `af2bfd226cc53b5c4665c160a6d8310abcce8b53`, clean.
- Owner result evidence directory: `E:\DEPI\P3-Diagnostics\plan_only_v113_review_20261118_135250604_b5aefdc8`.
- Owner saved log: `E:\DEPI\P3-Diagnostics\plan_only_v113_review_20261118_135250604_b5aefdc8\plan_only_output.txt`.
- Interpreter: `E:\DEPI\P3-Acceptance-af2bfd226cc5\.venv\Scripts\python.exe`, Python **3.12.9**, Pillow **13.0.0**, scalable `ImageFont.load_default(size=40)`.
- Protected main database: `E:\DEPI\AI-Doctor-FollowUp-Agent\data\runtime\app.db`, SHA-256 `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`. Worktree DB absent both before and after; pinned files validated, two configured CRLF normalization exceptions match committed Git blobs.

## Independently inspected evidence

| Check | Owner Windows result |
|---|---|
| `[PREFLIGHT OK]` | PASS |
| `harness_version` | `1.1.3` |
| `mode` | `plan_only` |
| `preflight_passed` | `true` |
| `plan_valid` | `true` |
| `execution_ready` | `true` |
| `required_coverage_ready` | `true` |
| `execution_readiness_status` | `READY_FULL_COVERAGE` |
| `execution_blocking_reasons` | `[]` |
| `postflight_checked`, `postflight_passed` (v1.1.3 Python) | `true`, `true`; `postflight_errors=[]` |
| `[POSTFLIGHT OK]` (PowerShell) | PASS, repo clean/HEAD pinned/protected DB and worktree DB unchanged |
| `PLAN_ONLY_EXIT_CODE` | **0** (in the saved log and transcript) |
| `plan_sha256` | `d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793` — **identical to v1.1.2**, no plan drift |
| `duplicate_ids` | `[]` |
| `missing_font_exclusions` | none in any split |
| Font catalog | 6/6 available |

**Planned, not executed:** canonical baseline 3 = 1 corrupted-positive + 2 clean-negative; exploratory 80 = 16 + 64; holdout 160 = 80 + 80. **Total plan: 243**. No OCR is executed by `plan_only`; readiness is not an OCR accuracy result.

## Comparison to previous gates / next safe step

- v1.1.2 owner Windows `plan_only` already PASS, and its `plan_sha256` is identical. v1.1.2 `probe_only` was INCOMPLETE (exit 13) because target matching depended on OCR text and the parser missed real `lstm_choices_*` sibling groups.
- v1.1.3 was independently source-audited and its parser was replayed on actual saved owner Windows hOCR: `word_1_20` localized, 138 choice groups parsed, and the zero-confidence `O` alternative was **not** accepted as a corrected reading. See [independent source audit](P3_E1_E3_V113_INDEPENDENT_SOURCE_AUDIT.md).
- **Decision:** The code/path integrity review plus the **actual successful v1.1.3 Windows plan-only** gates justify permitting the **single next diagnostic mode, `probe_only`**, using the **same hash-verified immutable v1.1.3 launcher and Python**, an entirely new diagnostics-only run directory and an independent reviewer check of outputs before any more modes.
- Stop on any nonzero exit, failed preflight/postflight, insufficient/missing hOCR evidence, mismatch, unexpected write or `probe_measurement_failures`. `probe_only` exit 0 can establish *probe completeness*, but **never** automatically satisfy `GOLD-EX-11` or authorize `canonical_baseline` without independent review.
- Required evidence after run: full `probe_only_output.txt`, **new** `run_..._probe_only\manifest.json`, `metrics_summary.json`, and minimal synthetic `raw\_probes\hocr_probe.stdout.txt` and `probe_input.png` only when further provenance inspection is necessary. Do not upload secrets, protected DB, app runtime files or real PHI.

**No owner P3 phase acceptance or PR merge is requested or implied by this docs-only update.** Any filescope exception for documentation in draft PR #11 remains subject to explicit owner approval. P4–P8 remain TODO.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
