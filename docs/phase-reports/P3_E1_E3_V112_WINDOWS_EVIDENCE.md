# P3 E1–E3 v1.1.2 — Owner Windows evidence register (2026-11-18)

> **Phase state: IN_REVIEW / NOT ACCEPTED.** This is a record of the owner's reported Windows execution and an independent inspection of owner-supplied evidence, not a P3 sign-off. **GOLD-EX-11: FAIL / NOT PROVEN.** Do not merge P3 or begin P4/P5. EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.

## 1. Baseline and evidence provenance

| Field | Recorded value |
|---|---|
| Repository / P3 PR | `Muhammed-Fathi/AI-Doctor-FollowUp-Agent`, [draft PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) |
| P3 owner Windows acceptance commit | `af2bfd226cc53b5c4665c160a6d8310abcce8b53` |
| Approved baseline `main` | `867ab122394ffcc14df099bc2c7a11bce3143d8f` (P0–P2 accepted) |
| Harness version | `1.1.2` |
| Authenticated Draft Release | `449417459`, review-only; not merged into the application |
| Bundle ZIP | 91,290 bytes; SHA-256 `baa0ce745a2f582433b0fe37061c8f0f41ca05ce2da1c12b50f39b1fb0446437` |
| Source test case | `data/synthetic/documents/sources/report_ocr_o_confusion.txt` |
| Protected DB baseline SHA-256 | `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b` |
| Probe image | 1349×400; SHA-256 `80e6afbaa30c49beaef8dc41373e23a72603780d19fa5d660dfdd1593a988660` |
| Raw hOCR file | `hocr_probe.stdout(1).txt`; SHA-256 `d6104275a4583addd0ac1d7f8b9d4f01e1a2476b6b256cd2da52b4cd84a2b1f2` |
| Plan identity | SHA-256 `d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793` |

The owner-supplied evidence included local Windows launcher transcripts, `plan_only_output.txt`, `probe_only_output.txt`, `manifest.json`, `metrics_summary.json`, `probe_input.png`, and `hocr_probe.stdout.txt`. These **run-time outputs, ZIP, rendered image and OCR temp results are not committed** to the repository under `AGENTS.md` §3.1. Their digests and minimal non-sensitive excerpts are captured here to support verification.

## 2. Windows gate results (owner-executed, separately inspected)

| Gate | Status | Observed result |
|---|---|---|
| Authenticated v1.1.2 ZIP recovery | **PASS** | Correct ZIP + five embedded member hashes, protected DB and golden source unchanged; no diagnostic modes run during recovery |
| `plan_only` on Windows PowerShell 5.1 | **PASS** | Exit `0`; `plan_valid=true`, `execution_ready=true`, `required_coverage_ready=true`, `READY_FULL_COVERAGE`; `[POSTFLIGHT OK]` |
| Canonical plan coverage | **READY / NOT EXECUTED** | 3 canonical (1 corrupted / 2 clean), 80 exploratory (16 / 64), 160 holdout (80 / 80); zero missing font exclusions |
| `probe_only` on owner Windows | **INCOMPLETE** | Exit `13`; `probe_measurement_complete=false`, `probe_subprocess_failures=["probe_hocr_char_boxes"]` |
| Probe preflight/postflight | **PASS** | Pinned HEAD, clean worktree, protected/worktree DB and pinned source hashes unchanged |
| Real Tesseract | **EXECUTED** | Tesseract `5.4.0.20240606`, `eng` listed; `probe_hocr_char_boxes` returned OS exit `0`, 451.317 ms, no timeout |
| Canonical probe image parity | **PASS** | Byte-, pixel- and geometry-identical to committed canonical image |
| OEM 0 legacy engine | **UNSUPPORTED** | Installed `eng.traineddata` lacks legacy components; separately recorded unsupported capability, not source of exit 13 |
| `canonical_baseline`, exploratory, holdout | **NOT AUTHORIZED / NOT RUN** | Stop before any subsequent OCR experiment |
| GOLD-EX-11 OCR fidelity/safety acceptance | **FAIL / NOT PROVEN** | Not proven safe by this incomplete capability probe |
| P3 phase acceptance | **IN_REVIEW** | No owner PASS, no PR #10 merge |

Windows runtime: `E:\DEPI\P3-Acceptance-af2bfd226cc5\.venv\Scripts\python.exe`, Python `3.12.9`, Pillow `13.0.0`, acceptance HEAD `af2bfd2`; `C:\Program Files\Tesseract-OCR\tesseract.exe`. The records are owner-machine evidence; no claim is made that the ChatGPT sandbox ran Windows/Tesseract.

## 3. Reproduced defect and evidence snippet

The synthetic source ambiguity under test is **`1O5`** (letter uppercase O). The OCR engine returned **`105`** (digit zero) inside real hOCR word `word_1_20`, bounding box `543 187 613 216`, word confidence `95`.

Minimal reproducible structural excerpt from the real, synthetic-only hOCR (not the full OCR output):

```xml
<span class="ocrx_word" id="word_1_20" title="bbox 543 187 613 216; x_wconf 95">
  <!-- top recognized characters are siblings of the LSTM choice group -->
  <span class="ocrx_cinfo" title="x_bboxes ...; x_conf ...">0</span>
  <span class="ocrx_cinfo" id="lstm_choices_1_20_2">
    <span class="ocrx_cinfo" id="choice_1_20_3" title="x_confs 88.836983">0</span>
    <span class="ocrx_cinfo" id="choice_1_20_6" title="x_confs 0">O</span>
  </span>
</span>
```

Snippet omits unrelated surrounding elements and does **not** represent a literal complete hOCR document. Actual raw hOCR had **138** `lstm_choices_*` groups, of which **123** had multiple candidates.

**Defect A — target localization:** v1.1.2 probe invoked the parser with `target_bbox=None, target_token="1O5"`; it searched for the recognized OCR text to equal the expected source text, yielding `no_target_word` when OCR substituted O→0.

**Defect B — choice group decoding:** the real Tesseract output uses sibling `ocrx_cinfo` followed by `ocrx_cinfo id="lstm_choices_*"` containing `choice_*` children; the parser failed to count these alternative groups. Exact-token workaround `105` or explicit bbox still reported `genuine_no_o_zero_alternative` with **zero** parsed choices. The observed `O` alternative has `x_confs 0`, i.e. **below** `d3_min_alt_conf_pct=1.0`; it must **not** be treated as sufficient evidence for correction or as a repaired clinical value.

There are **two** independent harness bugs. A process `returncode=0` means Tesseract ran; the measurement can nevertheless be incomplete. Both must be fixed with regression tests without weakening fail-closed decisions.

## 4. Bounded engineering handoff and next gate

1. Arena may use the linked [independent bundle review](P3_E1_E3_V112_INDEPENDENT_BUNDLE_REVIEW.md) and [root-cause report](P3_E1_E3_V112_PROBE_ROOT_CAUSE.md). Fix **the diagnostic harness only**, on a new review branch / new authenticated Draft Release **v1.1.3**, with a pinned SHA manifest, exact diff, tests, and rollback. No application source, fixture, DB, OCR thresholds, or accepted baseline edits.
2. Locate the intended OCR target from independently grounded source/render geometry (unique bbox/IoU), **then** compare observed OCR text to expected source; preserve uncertainty, and fail closed on ambiguity.
3. Parse sibling and nested hOCR choice structures correctly, attach alternatives to their own top character, preserve confidence semantics and rejection of malformed/ambiguous alternatives. Regression-test real-syntax `105` with intended `1O5` and an `O` candidate at `x_confs 0`.
4. Independently audit the revised ZIP and test source; owner then executes new `plan_only` and only after separate authorization a new `probe_only` in fresh evidence directories. Do **not** rerun or overwrite v1.1.2 evidence. `canonical_baseline` requires its own later authorization.
5. After actual Windows evidence is complete, update this phase ledger and the P3 report; **only the owner** can approve P3 and merge. P4/P5 remain `TODO`.

**Source-of-truth order:** `docs/roadmap/MASTER_PLAN.md` for planned scope, `docs/roadmap/PHASE_PROGRESS.md` for phase status, P3 phase reports + immutable hashes for executed evidence, GitHub PR review/owner decision for acceptance.

This addendum does not assert that real OCR fidelity is proven, nor that any synthetic medical value is clinically correct.
