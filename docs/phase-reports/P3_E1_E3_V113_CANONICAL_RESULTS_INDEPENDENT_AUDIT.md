# P3 E1–E3 v1.1.3 — Independent canonical-baseline results audit

**Audit date:** 2026-11-18. **Source:** five owner-uploaded original artifacts from existing owner Windows run, not a fresh diagnostic invocation. **Disposition:** `CANONICAL_EXECUTION_COMPLETE / SCIENTIFIC_GOLD_EX_11_NOT_PROVEN`. The diagnostic run **completed** (3/3, harness exit 0, protected postflight PASS) despite the parent PowerShell 5.1 `NativeCommandError`; **none of the supported mechanisms specifically detected the positive `1O5`→`105` OCR confusion**. P3 stays **IN_REVIEW**, and the shipped application `GOLD-EX-11` remains **FAIL / NOT PROVEN**. Do **not** advance to exploratory, holdout, rule freeze, P3 release, merge or P4/P5.

## 1. Immutable run identity and uploaded source digests

One and only existing original Windows run was found during a separate read-only on-device check; the owner then uploaded its **actual contents**:

| Exact uploaded original | Bytes | SHA-256 |
|---|---:|---|
| `manifest(2).json` | 17,456 | `62533b01935a2fae5395ff1705ed5ae475f5c71061115b89c6e8d6b5d0261c4a` |
| `metrics_summary(2).json` | 54,330 | `e79d60d3ac905ddfdb9e345d58f859e98da0525d6f4a428099c5888b1804d8bd` |
| `records.jsonl` | 46,463 | `bb0f82906a60f0b8669eca9e83df737e478be9116a1cb09c780732b09bed1945` |
| `records.csv` | 1,625 | `6099598136eb0313d67cc51b03004d6168348bd0b561fc73dfa14a8e9badba78` |
| `canonical_baseline_output.txt` (UTF-16LE BOM) | 1,096 | `7770fb98170bef41a89613b76dcf1f28814f522be08516642d81e7f6f49bff4d` |

Run: `20261118T121739_753329Z_canonical_baseline_0e5a8b3d` from `E:\DEPI\P3-Diagnostics\run_20261118T121739_753329Z_canonical_baseline_0e5a8b3d`. Pinned acceptance HEAD `af2bfd226cc53b5c4665c160a6d8310abcce8b53`; immutable plan SHA `d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793`; default `e1_e3_rules_v1` SHA `e04f2701d7e973d30a9082330762ef50f4a759a83bf6de001b1405cc58bdd446`. Python 3.12.9, Pillow 13.0.0, real Tesseract 5.4.0.20240606, `eng`. No frozen rules were produced.

## 2. Independently verified completeness and integrity

- The manifest and metrics have identical `run_id`, `split=canonical_baseline`, `pinned_commit_sha` and `plan_sha256`. Metrics `exit_code=0`.
- `experiment_completeness.complete=true`, `split_coverage_status=COMPLETE`, `attempted_specimen_count=3`, `completed_specimen_count=3`, `planned_specimen_count=3`, `full_planned_coverage_achieved=true`; no specimen timeouts/subprocess failures. Exactly **3** parsed JSONL records and **3** CSV rows, correct specimen identities, with independently matched core fields and **all D1/D1b/D2/D3/D4/D5/D6 state/flag pairs** across JSONL and CSV.
- Canonical specimen image parity **3/3 PASS**, TSV-repo parity **3/3 PASS**, persisted images verified, crop isolation `clean_isolated` 3/3, no raw crop overlap.
- Manifest preflight and postflight `passed=true`, pinned HEAD and worktree clean/unchanged, pinned source files unchanged, worktree DB absent. Protected DB SHA-256 remained `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`.
- The parent log contains **only** runtime + `[PREFLIGHT OK]`: its stderr/Pillow `Image.getdata()` warning was surfaced as a terminating `NativeCommandError` in the **outer** Windows PowerShell 5.1 wrapper before the wrapper printed the final exit. The **inner** run nonetheless generated complete, postflight-checked evidence with exit 0. Thus **outer wrapper logging failed, experiment execution completed**. Preserve both facts.
- This audit did not re-execute OCR or modify any evidence.

## 3. Three observed specimens (exact owner JSONL evidence)

| Specimen | Expected source token | OCR numeric result | Ground truth ambiguity | Specific detection | Other operational outcome |
|---|---|---|---|---|---|
| `CANON_GOLD_EX_11` | `1O5` (**letter O**) | `105` (**digit 0**) | **POSITIVE** | **NOT DETECTED** by D1, D1b, D2, D3, D4, D6; D5 unsupported | D4 generic crop disagreement (`105°`), D6 **fail_closed_non_specific** |
| `CANON_W1_GLUCOSE_104` | `104` | `104` | NEGATIVE | correctly not flagged | D4 & D6 clean |
| `CANON_REPORT_A_CLEAN_13_4` | `13.4` | `13.4` | NEGATIVE | correctly not flagged as ambiguity | **D4 generic disagreement (`134`) + D6 fail_closed_non_specific**, operational false positive |

`CANON_GOLD_EX_11` baseline OCR parsed numerical `105` and set `baseline_looks_corrupted=false` despite source `1O5`. The **separate** diagnostic ground-truth comparison recorded `hocr_target_matches_expected_source=false`, recognized `105`, and real hOCR `genuine_no_o_zero_alternative`. This diagnostic mismatch is not evidence that the shipping application detects/rejects the false-clean value.

**Why the individual detectors did not flag the exact ambiguity:**
- **D1 / D1b:** all three specimens `identical_after_normalization`; no 1O5→105-specific signal.
- **D2:** word confidence 95.99176 on positive, above default 85.0 floor; no low-confidence flag. Clean controls 95.457184 and 96.307739.
- **D3:** hOCR character choices parsed successfully but the `O` candidate had **0.0%**, below 1.0% threshold, thus `genuine_no_o_zero_alternative`; no supported positive ambiguity hit. No threshold tampering is justified.
- **D4:** 2/3 specimens `generic_disagreement_only`, positive candidate `105°` (not O/0); *clean* 13.4 candidate `134` (punctuation removed). This provides a non-specific safety review trigger but **not specific ambiguity detection** and incurs false positives.
- **D5:** legacy OEM0 missing; `NOT_SUPPORTED_IN_THIS_ENVIRONMENT` across all three. Treat forced operational routing and suppressed rates as **unsupported**, never a scientific detection success.
- **D6:** 2/3 `fail_closed_non_specific` (positive GOLD and clean 13.4), 1/3 clean (104); no `flagged_ambiguity_specific=true` on GOLD. Operational routing isn't proof of the application-level `GOLD-EX-11` guard.

## 4. Correct scientific interpretation

| Detector family | Ambiguity-specific TP / FN / TN / FP | Ambiguity-specific sensitivity | Operational fail-closed TP / FN / TN / FP | Key limitation |
|---|---|---|---|---|
| D1, D1b, D2, D3 | `0 / 1 / 2 / 0` each | `0/1 = 0%` | `0 / 1 / 2 / 0` | Misses sole corrupted positive |
| D4 crop ensemble | `0 / 1 / 2 / 0` | `0/1 = 0%` | `1 / 0 / 1 / 1` | Non-specific operational review catches positive but falsely flags clean 13.4 |
| D5 OEM0 | **unsupported**; applicable n=0 | **undefined** | Routing recorded for 3/3; operational rates **SUPPRESSED** | Must not count missing engine as real accuracy |
| D6 combined | conditional applicable n=1 (negative only), so sensitivity **undefined**; 2 non-applicable | **undefined** | `1 / 0 / 1 / 1` | Same non-specific review false positive |

These rates are only on **three** canonical examples (one positive, two negative). They are neither generalized performance estimates nor approval thresholds. The scientific performance summary's `outcome_state_counts.true_negative_clean=3` for D1/D1b/D2/D3 is a **potentially misleading classification-state label**: it includes the known positive GOLD, which is a false negative by ground truth. The confusion matrices correctly report `fn=1, tn=2`; interpretation and future report naming should be audited. Do not change these historical results.

## 5. Acceptance distinction and engineering next step

Read-only repository acceptance requirements in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (§9) explicitly say **GOLD-EX-11 must PASS by showing that the real-engine OCR output is flagged instead of silently turned into a plausible numeric value**; a preserved failure is **not** acceptance. `P3_R20_OCR_CONFIGURATION_DECISION.md` (§2) previously demonstrated the shipping API's false-clean `105` could reach a `doctor_verified` Observation when approved without source comparison. This bounded diagnostic study does **not** prove that application-level risk is closed. Conversely the D4/D6 non-specific operational route is a useful research observation and should not be hidden.

**Recommendation now: HALT the next diagnostic progression.** No repeat canonical run, exploratory, holdout, frozen-rules, source fixture editing, OCR threshold lowering, stealth normalization, P3 merge or P4/P5. Preserve the holdout untouched.

**Arena handoff — design and evidence first (not authorization for source modification):**
1. Propose a bounded mitigation strategy for real-engine `1O5`→`105` *false-clean* risk which is deterministic, fail-closed, source-review capable and **does not use the synthetic fixture's expected token as a production input**. Explain how a doctor can compare the original image to recognized value and verify/correct/reject it; prevent `doctor_verified` promotion without genuine source-aware confirmation. Keep the approved rejection/recovery contract (R21) and audit provenance intact.
2. Compare a source-view/explicit confirmation gate vs non-specific multiple-pass crop review, including expected false positives on clean `13.4`. Add owner-controlled acceptance criteria for GOLD with both corrupted positive and clean negative. Do not invent an OCR-only guarantee; use explicit human review where ambiguity cannot be reliably resolved.
3. Audit the `true_negative_clean` outcome label vs actual GT FNs without rewriting historical evidence; design testable clearer scientific wording.
4. Fix **the external PowerShell 5.1 wrapper logging only** on a separate reviewable change, preserving stderr (including deprecation warnings) and exit status; don't suppress warnings globally or modify immutable v1.1.3 bundle/launcher as a shortcut.
5. Submit a **review-only** change design with exact files, API/UX contracts, regression tests, and migration requirements (if any) for owner approval. No P3 or GOLD success claim until independently verified real Windows end-to-end.

**Provenance/governance:** This is a report on **docs-only draft PR #11** targeting pinned P3 acceptance branch, not `main`. File-scope exception/merge remains an explicit owner decision. Run evidence, database and fixtures were not committed or overwritten.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
