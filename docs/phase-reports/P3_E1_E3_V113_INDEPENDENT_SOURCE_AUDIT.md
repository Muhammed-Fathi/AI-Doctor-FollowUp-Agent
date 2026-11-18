# P3 E1–E3 v1.1.3 — Independent Source Audit and Conditional Windows Gate

**Review date:** 2026-11-18  
**Review scope:** authenticated owner-uploaded v1.1.3 ZIP, direct SHA verification, exact code diff against v1.1.2, targeted tests, actual saved Windows v1.1.2 synthetic hOCR replay, and read-only launcher/path audit.  
**Disposition:** **CONDITIONAL APPROVAL — `plan_only` ONLY.** No permission for `probe_only`, `canonical_baseline`, exploratory, holdout or frozen-rules actions. P3 remains `IN_REVIEW`; `GOLD-EX-11` remains `FAIL / NOT PROVEN`. No phase acceptance or merge.

## Authenticated artifact and integrity

- Owner independently recovered release **449889565**, confirmed `PROTECTED BASELINE POSTFLIGHT: PASS` without executing modes, and uploaded ZIP `e1_e3_windows_diagnostic_bundle_v113.zip`.
- Local independent ZIP SHA256 **`d620208ff0811b7ec6372bc96174cd302daed4dc37664acd104aba5d27cc3cb5`**, exactly **85,170 bytes**, matching authenticated Draft Release metadata. `zipfile.testzip()` yielded `None`, five members, LZMA method 14, five member hashes independently recomputed and matched.
- Member SHA-256:
  - `e1_e3_windows_diagnostic.py`: `b7bf92292be5755c5d04a5a4f2cee0f23f4b5e9610ef04a1a54dc33478beec59`, 263,804 bytes.
  - `run_e1_e3_diagnostic.ps1`: `a45193aa7a19d3681e9ef3a6b4faa3a8ca993b28e9ba9f97d8f5d30c8c3b90bb`, 21,086 bytes.
  - `test_e1_e3_diagnostic.py`: `22a576b967424cd2cc8527617f3ffa9ce9486af38db4fe7a344d520b9fd7af7f`, 223,579 bytes.
  - `SELFTEST_AND_PLAN_OUTPUT.txt`: `ea03220453c41db73a7d24c31a2ee6f18a68a1f3cd4302afc7fa5a802e780970`, 32,586 bytes.
  - `SHA256SUMS.txt`: `d8735cd55d99b6a1d3176f32610e0b0d50c9614660248bd0950e715a8f2fd660`, 371 bytes.
- Exact comparison against previous uploaded v1.1.2: **PowerShell launcher byte-for-byte unchanged**; harness Python and tests changed, no other source files in the ZIP.

## Source-change review and independently reproduced checks

**Defect A — OCR-token exact-match localization:** New `GroundedTargetGeometry` derives the intended source token span from synthetic source `Value:` and renders target geometry independent of OCR. `parse_hocr_assessment` requires a bbox; no recognized-token fallback; no match → `no_target_word`; multiple matches → `ambiguous_target_word`. The code differentiates `target_word_text` from `expected_source_token`.

**Defect B — Tesseract 5.4 sibling `lstm_choices_*` groups:** New parser binds sibling choice groups to preceding `ocrx_cinfo` character slots and reports malformed, duplicate, orphan, missing or ambiguous groups; normalizes confidence and preserves threshold `d3_min_alt_conf_pct=1.0`.

**Actual owner-supplied Windows hOCR independently replayed through the *new* v1.1.3 parser, outside Windows/Tesseract:**
- Input: original `hocr_probe.stdout(1).txt`, SHA-256 `d6104275a4583addd0ac1d7f8b9d4f01e1a2476b6b256cd2da52b4cd84a2b1f2`, `target_bbox=(543,187,613,216)`, synthetic source target `1O5`.
- Result: `target_word_id=word_1_20`, OCR `target_word_text=105`, `target_matches_expected_source=false`, IoU `1.0` (supplied bbox), `localization_candidate_count=1`; **138** sibling LSTM groups and **123** multi-choice groups parsed, **0** malformed groups; **3** target multi-choice character slots.
- Target character `0` has an `O` alternative with `x_confs 0`; outcome **`genuine_no_o_zero_alternative`**, **not** a proven correction. No medical value was promoted.
- Bbox omitted → `missing_target_geometry`; distant/non-overlapping bbox → `no_target_word`. No unsafe OCR-text fallback.
- The **exact three original pinned synthetic source texts** were fetched from private GitHub at acceptance commit `af2bfd226cc5`; their raw SHA-256 digests matched pinned manifest. Local Pillow **12.3.0** computed the probe target bbox `(543,186,613,216)`, IoU **0.966667** against the real v1.1.2 OCR target, successfully localized the same word. **Important limit:** local Pillow 12.3.0 PNG bytes do **not** reproduce the owner Pillow 13.0.0 canonical image SHA; correct Windows canonical parity remains to be checked by the next authorized owner run.

**Independent syntax check:** `python -B -m py_compile` on both Python members: exit 0 on Linux Python 3.13.5. Replayed existing new test class with three genuine pinned synthetic source files in an isolated temporary directory: **6 of the eight new tests PASS**; the two end-to-end tests requiring a complete pinned Git worktree returned `EXIT_PREFLIGHT_FAILED=10` instead of their test-expected 0, because the *review environment* lacks the exact `af2bfd2` checkout and pinned Git blobs. Running all 44 tests in this incomplete review environment likewise did not pass (14 failures, 15 errors, strongly dependent on missing pinned repository). **This is not an independent reproduction of Arena's reported 44/44 PASS; it is also not proof of a Windows failure.** Arena's `44/44` remains a separately attributed implementer-side claim, and Windows real-engine v1.1.3 is **NOT RUN**.

## Gate integrity, safety, and explicit limits

- Existing `run_e1_e3_diagnostic.ps1` is byte-identical to the previously audited launcher. It resolves only a pinned worktree Python 3.12 / Pillow 13.0.0, verifies pinned `af2bfd2`, clean Git status, protected DB before and after, and enforces diagnostics destination outside repo and DB.
- `run_plan_only` now adds a Python-level `try/finally` postflight integrity check. Its successful path checks the plan; it does **not** run Tesseract or write application data. The PowerShell launcher also retains a `finally` postflight.
- No full Windows `plan_only` test of **v1.1.3** was performed during this independent review. **A conditional read-only Windows `plan_only` is the next permitted activity** after re-verifying hashes and extracting into a new evidence-only folder.
- `ZIP_LZMA` may require Python `-m zipfile -e` or 7-Zip; **do not assume PowerShell `Expand-Archive` supports LZMA**. Use pinned Python on the detached acceptance checkout.
- No changes to application, pinned source fixtures, protected DB, thresholds, or original v1.1.2 evidence are authorized. No `probe_only` approval before a separately reviewed, successful v1.1.3 `plan_only` owner log.

## Next steps / Arena and owner handoff

1. Owner verifies the freshly recovered ZIP by fixed SHA-256 and all five individual member hashes; extracts using **pinned acceptance Python** into a new diagnostics-only folder; runs **only** `run_e1_e3_diagnostic.ps1 -Mode plan_only` using the unchanged verified launcher.
2. Record `PLAN_ONLY_EXIT_CODE`, runtime fingerprint, `plan_sha256`, split readiness, Python internal postflight, PowerShell `[POSTFLIGHT OK]`, and protected DB + pinned file hashes. Stop and attach full log even if any gate fails.
3. Independent reviewer inspects real Windows `plan_only` v1.1.3 evidence. Only then consider separate `probe_only` authorization; no batch runs or acceptance shortcuts.
4. Update `PHASE_PROGRESS.md` after each owner gate. New tests must never be represented as real OCR-engine evidence.

**Governance:** This is a docs-only draft PR #11 evidence record targeting the P3 acceptance branch, not `main`. It is still subject to explicit owner file-scope exception and review before any merge. P3 draft PR #10 remains unmerged. No P4/P5 work.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
