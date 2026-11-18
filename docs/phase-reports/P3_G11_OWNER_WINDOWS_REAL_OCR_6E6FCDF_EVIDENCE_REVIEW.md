# P3-G11 — Owner Windows real Tesseract evidence review: GOLD-EX-11 remains a release blocker

**Evidence date:** 2026-11-18  
**Status:** `P3 = IN_REVIEW`; `GOLD-EX-11 = FAIL / NOT PROVEN`; **NO P3 ACCEPTANCE**.  
**Reviewed detached source SHA:** `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821` (same existing active Arena P3 implementation branch; original PR #10 head not changed).  
**Operating system/runtime:** Windows 11 (10.0.22621), Python 3.12.9, Tesseract 5.4.0.20240606, Pillow 13.0.0, pytesseract 0.3.13, pypdfium2 5.15.2.

This report summarizes the **actual owner's supplied output files** from `scripts/python/windows_ocr_acceptance.py` on a newly created detached acceptance worktree `E:\DEPI\P3-Acceptance-6e6fcdf02d39`, not an agent-generated or a mock run. A separate reviewer examined the uploaded JSON, stdout, stderr and runner locally, but did **not** rerun the probe on the owner laptop. Original evidence remains in the owner's isolated `logs/` folder and user-provided attachments. This report is a findings memo, not owner-authored GitHub ratification or new authorization.

## 1. Authenticity and top-level evidence

- JSON `repository_head`: **`6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`**, matches the pinned reviewed source.
- Probe exit: **`2`**, correctly nonzero for a blocking gate.
- Gate summary: **27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED** (29 rows total).
- Reviewer-computed SHA-256 of the uploaded original JSON bytes: `9ac465722f011d538fd8045e393328fa8aff961f08e3488aff961f08cb`.
- Ancillary uploaded artifacts: `p3_g11_real_ocr.cmd`, `p3_g11_real_ocr_stdout.txt`, `p3_g11_real_ocr_stderr.txt`, and `p3_g11_windows_quality.log`. The runner uses an isolated child CMD process and output paths under the detached worktree. No source or fixture changes reported.
- Owner's prior Python 3.12 `test_all.ps1` had **12 PASS / 0 FAIL / 1 SKIPPED** optional Playwright; earlier native `finally` shell wrapper issue was separately cleaned up and source/protected checks repeated. These facts do not convert the OCR FAIL to PASS.

## 2. Confirmed GOLD-EX-11 failure mode

The synthetic source visibly contains **`1O5`** (letter O), but the **real Tesseract engine itself** transcribed **`Value: 105 mg/dL`** (digit zero). The application parser then received `raw_text='105'`, normalized `105`, and quality flag `clean`. The uploaded JSON explicitly records:

```text
source_token=1O5
diagnosis=substituted
engine_substituted_plausible_value=true
engine_preserved_ambiguous_token=false
application_substituted_value=false
parser_refused_token=false
raw_tokens=['105']
normalized_values=['105']
flags=['clean']
```

The JSON additionally reports `human_review_required=false` **under the specific `collect_flag_issues` blocking-issue derivation**, with `human_review_blocking_issues=[]`. This **does not** assert that the separate HTTP source-confirmation requirement is bypassable. The OCR text output alone contains no surviving `O` glyph from which a text parser could infer the visual source's `1O5`. The strict P1 gate (OCR-preserved ambiguous token must be refused, not silently corrected) was therefore **not proven**, and the immutable gate correctly reports FAIL. Low-confidence warnings or a policy reinterpretation do not prove this case.

## 3. Real-engine PASS outcomes that must not be understated or overstated

- `GOLD-EX-05 PNG`, `GOLD-EX-06 JPEG`, OCR engine/language availability, `PDFIUM-01`, and `ING-02 OCR upload end-to-end` succeeded with stored `tesseract` provenance. `OCR-LIVE-01` produced recorded measurements (not accuracy guarantees).
- **W1 R21 rejection**: a real OCR-derived, otherwise mappable **104 mg/dL** candidate was rejected by the assigned doctor; the document stored terminal `failed/measurement_rejected`, no Observation from its facts, the rejected fact was immutable, `VI-002` remained open, and re-decision returned `409 E_FACT_ALREADY_DECIDED`.
- **W1 source confirmation**: bare verify was blocked `400 E_VALIDATION`; after doctor source `GET /file`/`GET /text` and explicit `source_image_compared=true` plus confirmations, the clean 104 value created exactly **one** source-linked `doctor_verified` Observation, with intact provenance/audit safety.
- **W2 FC-3**: all five cases PASS under the actual false-clean OCR counterexample (rendered `1O5` transcribed as candidate **105 mg/dL**, with mappable siblings, `pending`, Tesseract provenance, source confirmation requirement). There were **zero pre-verify Observations**; bare and fake unreviewed comparison both answered `400 E_VALIDATION`; after doctor rejection there was no Observation, a repeated decision was refused and audit details passed leakage checks.
- `GOLD-EX-07/08 coverage` is **DERIVED** from other separately tested gates; it is not an independent PASS.

**Interpretation:** The mandatory doctor-mediated workflow prevents promotion without review, and R21 terminal rejection worked on a real OCR candidate. These are valuable compensating protections, **not proof that the OCR output preserved/flagged the ambiguous source character or that the strict `GOLD-EX-11` criterion is met**.

## 4. Engineering decision boundary

**Do not** change original synthetic `1O5` source/manifest, fake an OCR `1O5` result, reduce the gate's threshold, relabel a W2 PASS as GOLD PASS, rerun unchanged canonical OCR hoping for a different outcome, or merge PR #10 / mark P3 complete.

**Recommended next task: a read-only, bounded root-cause and safety-design review in the existing Arena session/branch**, comparing real source/pixel-level evidence with Tesseract output and the parser; evaluate whether a genuinely source-aware ambiguity/double-read check or conservative nonpromotion review gate can detect this exact false-clean substitution **without also denying normal clean `104` and genuinely numeric `105`**, changing raw OCR text, or producing spurious clinical assertions. Keep the P1 literal GOLD requirement as-is; a P2 policy reinterpretation is a **separate owner decision, not authorized**. Any implementing file expansion/design must be explicitly reauthorized; no new PR or branch.

An engineering report should distinguish what can be guaranteed from OCR text-only input (not source character identity after substitution) versus additional image-derived evidence, provide minimal alternatives with failure modes, and propose new RED tests/holdout-free offline controls; no code changes or repeat real-engine test without approval.

### Pending evidence
- Independent review of the scope/design decision above; **no new implementation or OCR rerun authorized**.
- Protected main HEAD/DB SHA postflight of this specific OCR run was not included in the supplied excerpt; verify safely/read-only before new host actions. Previously checked main and database remained intact.
- Existing CI/head PR review and optional frontend E2E remain separate from the scientific `GOLD-EX-11` blocker.

**Release ledger: P3 IN_REVIEW / GOLD-EX-11 FAIL NOT PROVEN / 27 PASS, 1 FAIL, 0 NOT RUN, 1 DERIVED / probe exit 2 / no merge or P4/P5.**

Educational synthetic demonstration only — NOT FOR CLINICAL USE.
