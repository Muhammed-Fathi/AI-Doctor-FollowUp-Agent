# P3-G11 — Independent Audit of Arena Design v2 (2026-11-18)

**Verdict: SUBSTANTIALLY IMPROVED / CORRIGENDUM REQUIRED BEFORE IMPLEMENTATION APPROVAL.** The owner supplied the full Arena Design v2, and Arena posted [design v2 summary on PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6979426944). Independently re-read critical pinned source code `af2bfd226cc53b5c4665c160a6d8310abcce8b53` using the private GitHub connection, along with original Windows v1.1.3 scientific evidence and the design. **No code/test/OCR execution was performed in this review. No implementation, merge, diagnostic run or owner policy change is approved by this report.**

**Gates unchanged:** P3 `IN_REVIEW`, `GOLD-EX-11=FAIL/NOT PROVEN`; actual Windows `plan_only` PASS, `probe_only` PASS, `canonical_baseline` execution 3/3 COMPLETE but specific `1O5`→`105` detection 0/1. Docs-only PR #11 and P3 PR #10 DRAFT/OPEN/UNMERGED; protected baseline and holdout untouched.

## Strong v2 corrections independently supported

1. **Owner policy alternatives P1/P2** explicitly keep literal G1 `GOLD-EX-11` separate from procedural G3/G4 source-attested `W2/FC-3`. Existing Windows acceptance §9 still blocks release on literal GOLD FAIL; R20 treats G1 as a measured limitation. **Only owner may approve any amended policy**, and new W2 evidence cannot be called a G1 PASS.
2. **Non-vacuous W2:** requires actual synthetic OCR `tesseract` extraction, original source/upload hash, persisted page text, an actual numeric `105 mg/dL` value, supported glucose alias, usable report date/unit and mapping eligibility before any “zero Observation” assertion. If the real production OCR path loses layout/sibling facts, the false-clean case is **NOT RUN/FAIL**, never PASS. No fixture substitution or OCR config changes to force it.
3. **False doctor attestation** is now explicitly admitted as residual: `GET /file` plus a checked `source_image_compared` flag is attribution, not evidence of human visual correctness. No claim of a perfectly safe or fully detected OCR result.
4. **Patch narrowed** to `read.py:read_file`, `windows_ocr_acceptance.py`, and P3 tests; unrelated response schema, speculative confusable flags, frontend work and dead-branch cleanup deferred.
5. **PowerShell proposed architecture improved**: separate stdout/stderr, real child OS exit code, no merged chronology claim, collision-protected diagnostics-only folder, preflight/postflight, synthetic mock-child validation; no rewrite of immutable ZIP or historic data.
6. **Honest provenance:** test totals from prior implementer sessions are correctly attributed, not described as independently run during this design-only review.

## Remaining required technical corrigendum (small and focused; no full redesign)

### V2-C1 — BLOCKER: Clean `13.4 g/dL` is UNMAPPED; M2 expected Observation contradicts actual closed mapping

Arena Design v2 **acceptance matrix M2** says the clean `report_a_clean.txt` `Hemoglobin 13.4` produces `Observation(13.4)` after verification. This is **false in pinned source**. `backend/app/core/enums.py:MAPPING_TABLE` has no `hemoglobin` alias; `backend/app/core/enums.py:DocumentUnit.G_DL` is document-only, not an allowed Observation `Unit`; and `backend/app/services/documents/mapping.py:decide_mapping` explicitly returns `reason=unmapped_test_name` for hemoglobin. It is correct for a document to be reviewed/verified **with ZERO Observation**, without treating that as a false-clean detection or a failed workflow. Update M2 to: clean OCR `13.4` remains free of spurious corruption/VI-005, all facts may be confirmed, **document verified (if no other blockers), mapping UNMAPPED, Observation count = 0**. If the actual OCR loses fields, classify that as a separate extraction outcome rather than fabricating mapping. Explicitly keep clean `104 mg/dL` as the mapped positive control.

### V2-C2 — BLOCKER: File-integrity check at GET alone DOES NOT invalidate an earlier successful source-read anchor

Arena v2 M5 states that stored-file tampering or missing bytes causes `GET /file` 404/error and then `POST /verify` is blocked. That holds when **no prior successful read** exists. But `verification.py:_doctor_accessed_source_file` looks for the **latest successful** `EVENT_DOCUMENT_FILE_READ` for that doctor/doc after extraction; it does not consult later `outcome=ERROR` events or recheck current disk bytes. Therefore sequence **successful GET /file (OK anchor) → stored file tampered → GET /file fails (ERROR event) → POST /verify** could still satisfy the prior success anchor. Even without the second failed GET, tampering after a successful read is not stopped by a new GET-only hash check.

**Required explicit owner-visible choice:** Either (a) limit A1's stated guarantee to **integrity of the current GET response before an OK audit**, and disclose/reproduce the stale-prior-anchor residual; or (b) broaden the minimally scoped fix to invalidate any prior OK anchor on later failed file access and/or check current stored content hash again during OCR verification/promotion (with bounded tests and transaction/persistence considerations). Do not assert that M5 proves no tampered content can ever be verified if prior OK reads remain valid. If audit-error is committed inside a 404 handler, verify the commit does not unintentionally commit unrelated ORM changes and respects neutral detail, authorization and append-only audit rules.

### V2-C3 — BLOCKER: False-attestation M6 cannot create an Observation after deciding only the value

Arena M6 predicts `Observation(105 mg/dL, doctor_verified)` after a single `POST /verify` for OCR value `105`. `mapping.py:decide_mapping` requires verified test name, value, unit, report date and complete mapping; `_create_observation_from_mapping` rechecks active OCR siblings. The correct test must **first** verify all required sibling OCR facts under the same assigned doctor with fresh file access and valid confirmations; only **after** the final required decision can it expect one mapped `105 mg/dL` Observation. The residual is genuine but the fixture and test sequence must not invent “immediate promotion after a value-only decision.” Keep an assertion of **0 Observations before all siblings complete**, **at most 1 after** due to uniqueness, and an independent test that a false human attestation can still pass the procedural gate.

### V2-C4 — SOURCE ACCURACY: Fix exact code identifiers and causal attribution before code generation

- **Wrong property:** Arena Design v2 §6.1 uses `media_type=document.content_type`; actual `Document` model/route uses `document.mime_type`. Keep the existing MIME attribute unchanged.
- **Wrong detector taxonomy in §1.1:** actual JSON metrics keys are `D1_crop_c1_only`, `D1b_crop_c2_nodawg`, `D2_word_conf`, `D3_hocr_char_alts`, `D4_crop_ensemble`, `D5_oem0_compare`, `D6_combined_signal`. v2 labels D1 word confidence, D2 choice iterator, D3 hOCR delta, D4 rotation, D6 unsharp; these are not the detector *names* supported by the original owner metrics. Preserve exact labels and separate individual image transforms from detector group identity.
- **Warning attribution:** the observed `NativeCommandError` at `C:\Users\wifi\Downloads\Run-AI-Doctor-E1E3-v113-CANONICAL-BASELINE.ps1:88` occurred in the **outer calling wrapper's** `2>&1 | Tee-Object` with `$ErrorActionPreference='Stop'`. Do not imply it was an independently observed failure of the unchanged bundled `run_e1_e3_diagnostic.ps1`; the inner Python run completed exit 0 and postflight passed.

### V2-C5 — REQUIRED REGRESSION/POLICY CLARITY: Do not invent future PASS

- W2 needs **before/after persisted DB facts/verification/audit/Observation** assertions with actual mappable extractor path and `NOT RUN/FAIL` state for unparseable or layout-lost OCR, not an empty upload. If `W2` can't get a candidate, don't tune source fixture/spacing to force it.
- A1 must preserve correct `GET /file` response content type, confidentiality of error reasons, no successful read audit on mismatch, and transactional durability of optional ERROR audit. Test immediate mismatch and **prior-success/tamper** sequencing explicitly.
- PS mock tests must not be conflated with *real Windows diagnostic* tests and must preserve pre/postflight on all attempted child paths.
- P1/P2 is an **OWNER GOVERNANCE POLICY decision**, not a code review decision; no accepted P3 release solely from test reclassification. Keep protected real Windows evidence and untouched holdout.

## Next required deliverable and decisions

**Request a small Design v2.1 CORRIGENDUM ONLY** addressing C1–C5 with corrected M2/M5/M6 tests, exact paths/labels, clarified A1 guarantee or extra hash checks if proposed, and an owner decision ledger clearly identifying the **new integrity-anchor policy choice**. Do not repeat a 200-line architecture review.

**Owner decision recommendation (not automatic approval):**
- `OD-1` P1/P2: **hold pending deliberate, written owner acceptance decision**. P2 can be a truthful *different* release contract if deliberately approved and if future W2 G3/G4 evidence passes, but it cannot be counted as a retroactive G1 PASS. P1 retains existing strict blocker.
- `OD-2` A1+W2: **reasonable direction, pending corrected v2.1 and explicit scope authorization**.
- `OD-3` optional `ExtractionResponse.source_truth_notice`: DEFER.
- `OD-4` confusable heuristics/dead branch: DEFER.
- `OD-5` docs/scripts scope: pending owner written exception.
- `OD-6` external PowerShell wrapper: acceptable DESIGN direction only; authorize only after corrected mock guard tests, without touching original ZIP/historic runs.

**Status:** `DESIGN v2 REVIEWED / TARGETED CORRIGENDUM REQUIRED / NO IMPLEMENTATION AUTHORIZED`. P3 `IN_REVIEW` and `GOLD-EX-11 FAIL/NOT PROVEN`. No new diagnostics, exploratory/holdout, freeze, branch merge or P4–P8 work.

**Reviewer execution:** private GitHub `fetch_file` of pinned code and direct reading of user-supplied Design v2 / previously provided original owner metrics. No pytest/Windows/Tesseract execution this turn. No production source edited.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
