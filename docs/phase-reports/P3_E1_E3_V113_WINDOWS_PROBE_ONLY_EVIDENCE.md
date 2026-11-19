# P3 E1–E3 v1.1.3 — Owner Windows `probe_only` acceptance evidence (2026-11-18)

> **Disposition:** **`probe_only = PASS / COMPLETE` (exit 0) for the owner Windows capability measurement only**. This establishes that the v1.1.2 *diagnostic harness* blockers (source-token localization and sibling LSTM hOCR choice parsing) have been repaired and verified by the actual Windows Tesseract 5.4 run. **This does not establish recognition fidelity or an application's safe rejection of false-clean OCR.** P3 remains **IN_REVIEW**, `GOLD-EX-11 = FAIL / NOT PROVEN`. No P3 phase acceptance, PR merge, exploratory, holdout, or freeze-rules authorization.

## Evidence provenance and direct independent inspection

Four owner-uploaded files (independently opened and parsed, not generated from Arena statements):

| Supplied file | Size (bytes) | SHA-256 |
|---|---:|---|
| `Pasted text(20261118-120512).txt` (PowerShell transcript) | 25,250 | `9d9e0336d86e0e950ce69fe8dd96769ad24b2a6a29925557e4e4ee8e3eee3424` |
| `probe_only_output(1).txt` (UTF-16LE with BOM) | 48,684 | `92a76c233d956f7964008c538d65a64153665e3400ac01c2f8247bf03d1e301e` |
| `manifest(1).json` | 17,440 | `387fa4c35c515dab5259d41cadb7f95475693a407954b5d78e114e0d6028a5e9` |
| `metrics_summary(1).json` | 21,882 | `87623ca69f202c2304d66daf4677b30c4dfb19565b9f93b9018d1059f51d8b70` |

The JSON embedded in **both** the transcript and saved UTF-16LE output parses to **identical objects**. The embedded `summary` equals the uploaded `metrics_summary(1).json` **exactly** (all fields and values). Manifest and summary share the exact same run ID, split, pinned SHA and plan SHA. Console and saved output end in `[POSTFLIGHT OK]` and `PROBE_ONLY_EXIT_CODE: 0`; external wrapper reports another `PROTECTED BASELINE POSTFLIGHT: PASS`. These files are owner Windows evidence; this reviewer did not execute Windows or Tesseract.

## Pinned identity and gate result

| Item | Verified owner-machine result |
|---|---|
| Run ID | `20261118T120322_080547Z_probe_only_7d18ad0f` |
| Run directory | `E:\DEPI\P3-Diagnostics\run_20261118T120322_080547Z_probe_only_7d18ad0f` |
| Transcript log directory | `E:\DEPI\P3-Diagnostics\probe_only_v113_review_20261118_140320692_3e1bd319` |
| Mode / harness / exit | `probe_only` / `1.1.3` / **0** |
| Pinned acceptance HEAD | `af2bfd226cc53b5c4665c160a6d8310abcce8b53` (pre/postflight unchanged) |
| Specimen plan SHA-256 | `d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793` (unchanged vs v1.1.2 and v1.1.3 `plan_only`) |
| Runtime | Python `3.12.9`, Pillow `13.0.0`, pinned acceptance `.venv`, compatible |
| Tesseract | `5.4.0.20240606`, `eng` and `osd` available; hOCR parameters detected |
| `capability_probes.probe_measurement_complete` | **true** |
| Subprocess failures / measurement failures / timeouts | `[]` / `[]` / `[]` |
| `experiment_completeness.complete` | **true** |
| `experiment_completeness.split_coverage_status` | `PROBE_ONLY_COMPLETE` |
| Actual specimen executions | **0** (correct for capability-only mode); `full_planned_coverage_achieved = false`, scientific metrics `{}` |
| Canonical **probe-image** parity | **PASS**, bytes/pixels/geometry matched SHA-256 `80e6afbaa30c49beaef8dc41373e23a72603780d19fa5d660dfdd1593a988660` |
| Persisted probe image verified | **true** |
| Preflight / postflight | **PASS** / **PASS** in manifest, Python summary, launcher and external wrapper |
| Protected main DB SHA-256 | `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`, unchanged |
| Worktree DB and directory | absent before and after |
| Source fixtures and Git worktree | unchanged; pinned raw hashes and permitted CRLF normalized Git blob hashes verified |
| `OEM 0` legacy engine | `unsupported` by installed `eng.traineddata` as expected; not a probe failure |
| Frozen rules | not requested, not written, not eligible |

## Real Windows hOCR: fixed diagnostic defects demonstrated

The source synthetic fixture specifies `Test: Glucose             Value: 1O5 mg/dL` (uppercase letter **O**), while the **real** Tesseract recognition output is `105` (digit **0**). The v1.1.3 probe:

- Locates `word_1_20` from independent source/render target geometry `bbox=(543,186,613,216)`; matched OCR word `bbox=(543,187,613,216)`, IoU **0.966667**; `localization_candidate_count=1`, no OCR-token equality fallback.
- Records `target_word_text="105"`, `expected_source_token="1O5"`, and `target_matches_expected_source=false`, preserving the discrepancy rather than silently correcting it.
- Parses **138** page `lstm_choices_*` groups, **123** multi-choice groups, **0** malformed groups; target has **3** character slots and **3** multi-choice slots.
- Detects that a candidate `O` is present for the recognized `0`, but its `x_confs=0.0` is below `d3_min_alt_conf_pct=1.0`. Correct assessment: `hocr_probe_status="genuine_no_o_zero_alternative"`, `o_zero_or_l_one_hits=[]`.
- Real hOCR subprocess returned **exit 0**, no timeout, about **362.531 ms**. Its process success and the independently assessed capability status are recorded separately.

Unlike v1.1.2 `probe_only` exit 13 / `no_target_word`, this run is technically complete with the exact same original rendered canonical probe input. The negative alternative-confidence result is **scientific evidence**, not a reason to pretend an `O` correction is safe. High OCR confidence is not validation against the true source.

## Next gate and restrictions

**Only the next isolated `canonical_baseline` diagnostic split may be considered**, comprising **3 synthetic specimens** (1 corrupted-positive, 2 clean-negative), **with the unchanged pinned v1.1.3 ZIP, unchanged extracted launcher and Python, default untuned ruleset `e1_e3_rules_v1`, and a fresh evidence-only run directory**. No frozen-rule output argument. The source has been statically reviewed: each split uses the same guarded launcher, enforces the pinned checkout, writes evidence only beneath `E:\DEPI\P3-Diagnostics`, and performs independent pre/postflight. This is **not** an approval of the resulting recognition or detection metrics.

After owner execution, retain full `canonical_baseline_output.txt`, new `run_..._canonical_baseline\manifest.json`, `metrics_summary.json`, `records.jsonl` / `records.csv`, and any needed synthetic hOCR/image evidence for an independent evaluation. Stop if any nonzero exit, failed parity, incomplete coverage or baseline mutation occurs; do **not** retrain, change thresholds, rerun the holdout, or edit a golden fixture to force `GOLD-EX-11` to green.

**Current authorized progression is deliberately sequential:** `plan_only v1.1.3 = PASS` → `probe_only v1.1.3 = PASS` → *only* `canonical_baseline` (three items, not yet executed) → independent review and separate decision. `exploratory`, `holdout`, `freeze_rules_only`, P3 acceptance/merge and P4–P8 remain unauthorized.

**Governance:** This proposed evidence report is on docs-only draft PR #11, targeting a pinned P3 acceptance branch **not `main`**. Its file-scope exception still requires explicit owner review/authorization. Existing v1.1.2 original logs and v1.1.3 recovery evidence are preserved; no raw runtime output, databases, or PHI committed to GitHub.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
