# P3-R17 — Test matrix (traceable)

**Implemented by:** `backend/tests/p3/test_p3_r17_safety.py` — 24 tests.
**Baseline:** `1b17a9a` (597 passed). **After:** 621 passed, P3 238.
**Honest labelling:** every OCR text in this matrix is **injected** by monkeypatching
`intake.run_ocr`. None of it is real-engine evidence. Real recognition stays with the
owner's Windows run.

"Pre-fix" is the result measured against `1b17a9a` before any production change, with the
tests written first.

## A. Exact owner OCR text

Input: the owner's real Windows output at `1b17a9a` —

```
SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD

Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20
Test: Glucose Value: 105 mg/dL

Reference range: 70 - 110 mg/dL
```

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| A1 | The printed measurement is retained as evidence, `normalized_value=None`, flag `page_missing`, extractor `tesseract` | `test_r17_owner_ocr_text_surfaces_the_missing_measurement` | **FAIL** (no fact at all) |
| A2 | `VI-005` open with reason `value_unreadable`, `blocking=1` | same | **FAIL** (only `VI-002`) |

## B. Missing measurement / fail-closed status

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| B1 | `verified` unreachable without a measurement value fact | `test_r17_missing_measurement_never_reaches_verified` | **FAIL** (reached `verified`) |
| B2 | Document stays `needs_verification` with `VI-005` open | `test_r17_missing_measurement_blocks_document` | **FAIL** |
| B3 | Zero automatically created Observations | B1 asserts `_document_observations(db, id) == []` | pass (guard) |
| B4 | A genuinely document-only report is **not** labelled a failed read | `test_r17_document_only_report_is_not_a_failed_measurement` | pass (control) |
| B5 | A destroyed `Value:` label is undetectable, but still cannot manufacture an observation | `test_r17_lost_label_line_cannot_reach_verified` | pass; documents the limit |

## C. Parseable substituted `105`

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| C1 | One pending value fact, `normalized_value='105'`, **zero** observations before any decision | `test_r17_substituted_value_creates_no_observation_without_a_decision` | pass (guard) |
| C2 | Rejecting it creates no observation | `test_r17_rejecting_a_substituted_value_creates_no_observation` | pass (guard) |
| C3 | Preserved `1O5` is flagged `unparseable_value`, never repaired, `VI-005` | `test_r17_preserved_token_is_flagged_never_repaired` | pass (guard) |

## D. Correction and rejection

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| D1 | Correction value must be a number: `'   '`, `'abc'`, `'10x5'`, `'nan'`, `'inf'`, `'10\n5'` → `400` | `test_r17_measurement_correction_rejects_inadmissible_values` (6 params) | **FAIL** (all `200`) |
| D2 | A valid number is accepted | `test_r17_measurement_correction_accepts_a_valid_number` | pass (control) |
| D3 | Lineage kept: original `rejected`, `raw_text='1O5'` on both rows, `corrected_from_fact_id` set, `fact_verification` row with previous/new/reason | `test_r17_correction_keeps_the_original_ocr_evidence` | pass (guard) |
| D4 | Unsupported corrected unit `mmol/L` → `400` | `test_r17_correction_rejects_an_unsupported_unit` | **FAIL** |
| D5 | Allowlisted unit `mg/dL` accepted | `test_r17_correction_accepts_a_supported_unit` | pass (control) |
| D6 | A date correction is not held to the numeric rule | `test_r17_date_correction_is_not_held_to_the_numeric_rule` | pass (control) |
| D7 | Malformed date refused | `test_r17_date_correction_rejects_a_malformed_date` | **FAIL** |

## E. Issue lifecycle

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| E1 | A valid correction resolves `VI-005` (state `resolved`) | `test_r17_valid_correction_resolves_vi_005` | **FAIL** (stuck open) |
| E2 | Resolving `VI-005` does not clear `VI-002` while facts remain pending | `test_r17_correction_does_not_clear_unrelated_blockers` | pass (control) |
| E3 | Rejecting the value leaves `VI-005` open | `test_r17_rejection_leaves_vi_005_open` | pass (guard) |

## F. Acceptance evidence

| # | Property asserted | Test | Pre-fix |
|---|---|---|---|
| F1 | `human_review_required` is derived from blocker logic, not a literal | `test_r17_gate_human_review_flag_is_derived_not_hardcoded` | **FAIL** |

Verified end-to-end with the scripted engine, owner's exact bytes:
`human_review_required=True`, `basis=persisted-blocker-logic:collect_flag_issues`,
`blocking_issues=['VI-005']`, gate **FAIL** / `diagnosis=substituted`.
Preserved-token variant: gate **PASS** / `preserved_and_refused`.

## G. Contract-preservation checks (regressions that had to stay green)

| # | Property | Test | Result |
|---|---|---|---|
| G1 | Wrong-patient document + correction still answers `409 E_VI_004_UNRESOLVED`, not a `400` | `test_p3_r02_corrected_fact_cannot_bypass_the_identity_blocker` | green — caught a precedence bug in my first attempt |
| G2 | All 12 golden fixtures parse unchanged | `test_p3_fixtures.py` (12) | green |
| G3 | `GOLD-EX-11` preserved-token case still PASSes; substituted case still FAILs | probe, scripted engine | green |
| G4 | No fixture hash or manifest change this round | git diff | zero changes |
| G5 | OpenAPI still 16 paths / 17 operations | `check_openapi.py` | green — no endpoint added |

## Not covered, and not claimed

* Real Tesseract, on any variant. **NOT RUN.**
* Whether `preserve_interword_spaces=1` fixes recognition. **UNMEASURED.**
* A document with zero extracted facts (no `Value:` label at all) reporting an empty
  issue list — still open, needs a governance decision (analysis §8.2).
* `extractor: 'pypdf'` on document-level issues with no linked fact — still open, needs a
  wire-contract approval (P2 design §4).
* Durable OCR page text — design only, needs approval (P2 design §5).
