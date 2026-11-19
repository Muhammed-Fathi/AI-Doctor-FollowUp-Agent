> **Current evidence status (2026-11-18):** Root-cause report; fixes are not yet implemented or Windows-verified. `P3=IN_REVIEW`, `GOLD-EX-11=FAIL/NOT PROVEN`. Do not present this analysis as production OCR correction.

# AI-Doctor-FollowUp-Agent — P3 Windows E1–E3 `probe_only` v1.1.2
## Independent Root-Cause Analysis & Engineering Handoff

**Observed Windows run:** `20261118T102522_689007Z_probe_only_6f800149`  
**Pinned P3 acceptance commit:** `af2bfd226cc53b5c4665c160a6d8310abcce8b53`  
**Original harness ZIP:** v1.1.2, SHA-256 `baa0ce745a2f582433b0fe37061c8f0f41ca05ce2da1c12b50f39b1fb0446437`  
**Status:** `probe_only` **INCOMPLETE**, exit code **13**; do **not** execute `canonical_baseline` / exploratory / holdout or merge P3.

### 1. Grounded observations

- Windows `plan_only` v1.1.2 passed earlier, with complete planned 3/80/160 split coverage.
- Windows `probe_only`: preflight **PASS**, postflight **PASS**, protected DB / clean git worktree / pinned source hashes **UNCHANGED**. Python 3.12.9, Pillow 13.0.0, Tesseract 5.4.0.20240606, English traineddata available.
- `probe_hocr_char_boxes` *subprocess* returned **0**, no timeout, elapsed ~451.317 ms. Its stdout is valid XHTML/XML with Tesseract character and choice data, not missing output.
- Probe input `probe_input.png` uploaded independently has SHA-256 `80e6afbaa30c49beaef8dc41373e23a72603780d19fa5d660dfdd1593a988660`, identical to the run's recorded canonical image hash. Dimension 1349×400 in prior run report. Canonical image parity = **PASS**.
- Real target `ocrx_word` is `id="word_1_20"`, `bbox 543 187 613 216`, `x_wconf 95`, OCR text `105`, while the source target of the ambiguity test is `1O5` (letter `O`). **Do not infer that 105 is medically/source correct from the high OCR confidence.**
- Real hOCR contains 138 `lstm_choices_*` groups (123 groups with at least two alternatives). In `lstm_choices_1_20_2` the primary recognized character is `0` (`x_confs 88.836983`), with `O` listed as a candidate at `x_confs 0`. The `O` alternative does not meet the existing `d3_min_alt_conf_pct=1.0` threshold.
- The v1.1.2 summary nonetheless records `hocr_any_multi_choice_observed=false`, `hocr_probe_status=no_target_word`, `probe_subprocess_failures=["probe_hocr_char_boxes"]`, `probe_measurement_complete=false`, and overall exit **13**.
- Legacy `OEM 0` is explicitly unsupported by the installed `eng.traineddata`; this is reported as an unsupported capability and is **not** the primary cause of exit 13.

### 2. Independently replayed parser results

Read-only dynamic import of the original v1.1.2 `e1_e3_windows_diagnostic.py`, using the uploaded real hOCR as input to `parse_hocr_assessment(...)`:

| Target token | Target bbox | Status | Selected word | Parsed choice slots | Page multi-choice slots |
|---|---|---|---|---|---|
| `1O5` | `None` (actual probe invocation) | `no_target_word` | — | 0 | 0 |
| `105` | `None` | `genuine_no_o_zero_alternative` | `word_1_20` | 0 | 0 |
| `1O5` | `(543,187,613,216)` | `genuine_no_o_zero_alternative` | `word_1_20` | 0 | 0 |

**Two independent defects must be fixed together:**

1. **Target localization defect:** `run_capability_probes(...)` calls `parse_hocr_assessment` with `target_bbox=None, target_token="1O5"`. In this mode the parser uses an exact equality of the *recognized* OCR token against the *source* token, so an O→0 substitution itself makes the target disappear and reports `no_target_word` despite a real matched word in the expected image region. The diagnostic must locate the intended target from source/render geometry or a similarly independently grounded unique anchor, then compare OCR text as evidence. Do not change the canonical source or simply hardcode `target_token="105"`; do not select arbitrary matching numbers elsewhere in the page.
2. **Real-Tesseract hOCR structural parsing defect:** The actual Tesseract 5.4 output places the top `ocrx_cinfo` character and its adjacent `ocrx_cinfo id="lstm_choices_*"` *as siblings*, with candidate children `ocrx_cinfo id="choice_*" title="x_confs ..."`. The current `_parse_cinfo_slot_raw` only recognizes nested `ocr_cinfo` as a choice group or a single `x_conf` and does not bind these sibling `lstm_choices_*` to the preceding character slot. Hence it silently drops the observed alternative mechanism (reporting zero multi-choice slots although 138 groups exist).

This is a **diagnostic measurement/evidence defect**, not proof of a clinical OCR correction failure or success. Until corrected, `genuine_no_o_zero_alternative` from this parser is unsafe to rely on for the real Tesseract output, because the choices have not been counted.

### 3. Requirements for a new independently reviewed harness revision

- Deliver a new **v1.1.3** (or new unambiguous revision) review-only bundle in an authenticated **Draft Release**; preserve the original v1.1.2 ZIP and all Windows run artifacts byte-for-byte. No changes to the P3 acceptance worktree / protected DB / golden source / production repo to make tests pass.
- Fix target localization with deterministically grounded canonical target location, bounded IoU / uniqueness constraints, and explicit `target_word_id`, `target_word_text`, recognized-vs-intended comparison, and an explainable failure state if localization is ambiguous. Do **not** treat OCR confidence as source truth.
- Support actual sibling `ocrx_cinfo` + `lstm_choices_*` / `choice_*` hOCR structure while preserving support for legacy nested `ocr_cinfo` and `x_confs` formats. Bind exactly one alternative group to its intended top character slot, account for duplicate groups, malformed titles, missing data, confidence scales, and escaped XML correctly. Evidence status must be fail-closed on malformed/ambiguous attachment.
- Decouple Tesseract process execution success from OCR/measurement status: a return code 0 with valid hOCR plus a source/OCR mismatch should not be mislabeled a subprocess failure. Introduce accurate measurement categories, while preserving a nonzero terminal exit for genuine incomplete/unverified experiments.
- **Regression tests**: a minimized, non-sensitive snippet modeled on the real `word_1_20` with OCR text `105`, expected source token `1O5`, `bbox 543 187 613 216`, sibling choice group including `O` at `x_confs 0`, and proof that the group is detected, the target is uniquely anchored and the O alternative is **below** the 1.0% threshold. Also test genuine positive O alternative >=1%, no group, malformed group, ambiguous/multiple matching words, legacy parser formats, and unchanged fail-closed rules. Include an end-to-end mock probe expecting an accurate capability classification and controlled exit conditions.
- Run full harness unit tests and integrity checks; report exact tests, hashes, release ID, safety checks, Python/Pillow compatibility. Provide an independent verification path and owner Windows instructions only *after* the revised ZIP has been audited.
- Preserve the real observed evidence as scientific evidence; never rewrite or cherry-pick OCR output, change the original specimen, relax the threshold to force a green result, treat `x_confs 0` as meaningful positive evidence, or claim GOLD-EX-11 is resolved.

### 4. Acceptance gating

After independent ZIP audit, owner performs a new Windows `plan_only`, then `probe_only` in fresh diagnostics-only directories, verifying exact runtime and postflight hashes. Only if those pass should `canonical_baseline` be separately reviewed/authorized. P3 remains **IN_REVIEW**; `GOLD-EX-11` remains **FAIL / NOT PROVEN**. No merge of PR #10, no production or patient use, no real PHI.

**Evidence supplied:** Original v1.1.2 bundle + uploaded real `hocr_probe.stdout(1).txt`, `probe_input(1).png`, `probe_only_output.txt`, `manifest.json`, `metrics_summary.json`; upload the required source excerpts or minimized synthetic fixture to Arena as needed without changing protected repository files.
