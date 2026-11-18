# P3 / GOLD-EX-11 — P2 alternative acceptance-policy decision (owner selection)

**Decision ID:** `P3-GOLD-P2-2026-11-18`  
**Date:** 2026-11-18  
**Project:** AI Doctor Follow-Up Agent — local educational synthetic-data demonstration, **NOT FOR CLINICAL USE**.  
**Decision source:** The project owner replied **“طب يلا اعتمد”** in the ChatGPT conversation directly following a proposal to **adopt the P2 alternative policy path**, record the known OCR limitation, keep GOLD's FAIL visible, and subject any phase closure to review and explicit approval. This document and the accompanying PR conversation comment are **assistant-authored transcriptions of that user instruction**, **not a GitHub-authenticated owner-authored ratification or final phase approval**.

## 1. Owner-selected decision and effective boundary

**OWNER SELECTED: P2 alternative policy direction, as a *conditional, synthetic-only, application-layer acceptance path*.** This selection supersedes the **policy-choice/deferred-intent** part of historical P3-G11 OD-1 ("P1 retained, P2 deferred") **for drafting and reviewing a controlled policy amendment**. It does **NOT** automatically amend the currently checked-in P1/GOLD acceptance contract, mark `P3=PASS`, remove a release blocker from code/evidence, or authorize PR merge. The P2 exception can become operationally effective **only after** all items in §5 are satisfied, including explicit owner-authored confirmation on the PR and formal approved/merged contract/handoff amendment.

**The technical finding is permanent unless new evidence changes it:** `GOLD-EX-11=FAIL / NOT PROVEN` on the measured Windows run. The original `gate_ocr_corruption` retains its strict literal result and remains part of every evidence package. **The alternate P2 *policy* would accept a *bounded known deviation* for an academic demo; it does not transform FAIL into PASS or establish OCR glyph accuracy.**

**Until the effective boundary:** existing P1 strict gate remains authoritative; P3 is **IN_REVIEW / BLOCKED for final acceptance**. P2 here means *policy option P2*, **not project Phase P2** (the previously accepted patient API phase).

## 2. Immutable owner Windows evidence and risk

**Exact implementation / acceptance SHA:** `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821` (remote existing Arena branch `arena/752cca1f-ai-doctor-followup-agent`; detached host acceptance checkout at `E:\DEPI\P3-Acceptance-6e6fcdf02d39`).  
**Evidence:** owner-uploaded `p3_g11_real_ocr.json`, 15,283 bytes, actual SHA-256 `9ac465722f011d538fd8045e393328fa4a0e2b1f10afd1b8e3488aff961f08cb`. JSON `repository_head` equals implementation SHA; Windows 11 / Python 3.12.9 / Tesseract 5.4.0.20240606. OCR child exit **2**, **27 PASS, 1 FAIL, 0 NOT RUN, 1 DERIVED**. Earlier owner Windows `test_all.ps1`: **12 PASS, 0 FAIL, 1 optional Playwright SKIP**; backend pytest output includes four skipped tests and lacks a distinct count summary in the captured text. It is a passing quality gate, **not 837 individually passed tests on Windows**.

**Single blocking result under original P1:** synthetic source contains **`1O5`** (letter O) while real Tesseract emitted **`105 mg/dL`** (digit zero); parser received/stored `raw_text='105'`, `normalized_value='105'`, flags `['clean']`. The application **did not itself replace** the glyph. `GOLD-EX-11` correctly FAILS and `collect_flag_issues` alone did not emit a corruption-specific blocking signal. Neither scalar OCR confidence nor text-only parsing can reconstruct the missing O. `human_review_required=false` in the GOLD probe refers to this specific flag-derived calculation; it does not mean the HTTP verification route permits unattended promotion.

**Proven real-engine controls, not a detection claim:**
- All **W1** rejection and positive source-confirmation gates passed, including genuine 104 mg/dL, doctor review, source read/audit, linked `doctor_verified` Observation only after explicit confirmation, terminal rejection, VI-002 open and second decision rejected.
- All **five W2 / FC-3** cases passed on the *actual* false-clean 105 counterexample: zero pre-verification Observations; bare/unreviewed verification refused `400 E_VALIDATION`; doctor rejection prevented promotion and repeat decision; source/provenance/audit checks passed.
- `ING-02` real HTTP persisted Tesseract provenance, `GOLD-EX-05/06` PNG/JPEG and `PDFIUM-01` succeeded. `GOLD-EX-07/08 coverage=DERIVED`, not independent PASS.

**Residual risk explicitly accepted for consideration but NOT eliminated:** A doctor may mistakenly attest `105` without identifying the visual `1O5`, even after fetching the correct original image. The system currently verifies source-file retrieval, hash integrity, typed confirmation and reason, **not the correctness of the clinician's visual comparison**. A falsely attested value may still become a doctor-verified Observation. This is a material false-attestation / confirmation-bias limitation, not evidence of clinical safety.

## 3. Candidate bounded P2 acceptance rule — proposed contract amendment, NOT active yet

At the **application-boundary**, for **this synthetic-only P3 implementation and reviewed SHA**, owner may consider a **conditional acceptance despite `GOLD-EX-11` remaining technical FAIL**, **if and only if** all of the following are independently confirmed on the exact accepted review head:

1. **Transparency:** show literal `GOLD-EX-11=FAIL / NOT PROVEN`, OCR `1O5→105` counterexample and residual false-attestation risk in the phase report, handoff, demo limitations and PR approval statement. **Never** describe this gate as `PASS`, OCR fidelity as validated, or the product as clinically safe.
2. **Non-autonomy:** no OCR-extracted value creates an `Observation` before authorized doctor verification. Retain `verification_status=pending`, `requires_source_confirmation`, source-linked immutable facts and `VI-002`.
3. **Source integrity and access:** original immutable source bytes + SHA checked at `GET /file`, verify and promotion; fresh same-doctor, same-document read/audit anchor after extraction; later integrity ERROR invalidates stale successes; scoped neutral errors and confidential audit details. Do not replace the original with a re-render, sanitized OCR text or an AI guess.
4. **Doctor decision integrity:** require correct source scope, source comparison attestation, explicit matching value/unit/sibling confirmation and written confusable-digit rationale; preserve R21 terminal rejection and recovery, no re-decision and no automatic promotion. The acceptance documentation must explicitly say a typed attestation does **not** prove visual correctness.
5. **Real supported-platform evidence:** Windows Python 3.12 full local quality gate, genuine Tesseract W1/W2/ING/PDFIUM and unchanged strict GOLD measurement, fixture hashes, targeted security regressions, test counts and skip reasons all verified at a final pinned head; genuine CI PASS on the **same final reviewed implementation head** (not merely a prior head).
6. **Bounded scope:** all patients, reports and tests remain fictional/synthetic and local; no real patient documents, autonomous medical interpretation, risk/triage, treatment or external notifications. Do not silently broaden the policy to P4–P8, new OCR engines, a different SHA or other unsupported use.
7. **Governance & exit:** reconcile the P1/P2 policy text in `docs/evaluation/GOLD_FIXTURES.md`, `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` and related phase/contract reports via **separately authorized** minimal documentation-only change, without modifying the executable `GOLD-EX-11` function, tests or fixtures; obtain an explicit **owner-authored PR comment ratifying the exact deviation**, independent review, and only thereafter make any final phase-acceptance / PR merge decision. Preserve historical P1 results as history, not retroactively rewritten.

P2 policy is **one approved direction for drafting**, not blanket permission to treat the present suite's exit `2` as `0`, hide the one failure or skip separate PR-head review.

## 4. Alternatives rejected / deferred

- **Do not** modify the test image/source literal `1O5`, manifest, fonts, OCR engine output, renderer, `ocr_confidence_floor`, parser grammar, test verdicts or strict `gate_ocr_corruption` to manufacture a green result.
- Do not treat W2 PASS as scientific detection of the letter O; it shows human-gated nonautonomy.
- Disclosure-only API change (`ExtractionResponse.source_truth_notice`, `requires_confusable_digit_reason`) or later P6 visual comparison interface may reduce cognitive bias but **does not make GOLD PASS**. Both remain separate proposals with future authorization, not prerequisites or included code edits in this decision.
- Multi-pass Tesseract and confidence-only heuristics do not guarantee detection; trials showed collateral false positives for a clean 13.4 g/dL case. An alternative OCR engine or independently validated image-aware recognizer could be researched later under a separate plan, not inferred here.

## 5. Required implementation/governance checklist **before** P2 can take effect

- [x] Owner selected **P2 policy path in ChatGPT conversation** on 2026-11-18. *(Assistant-recorded instruction; not owner-authored GitHub ratification.)*
- [x] Independent Windows OCR evidence and exact SHA recorded; `GOLD-EX-11` technical **FAIL** preserved.
- [x] W1/W2/ING/PDFIUM real-engine successes and residual risk documented.
- [ ] **Owner personally posts/approves the exact P2 policy exception in PR #10** after reading this decision. A ChatGPT connector comment **cannot substitute** for this signature.
- [ ] Explicit owner approval of a minimal documentation-only contract/handoff alignment with scope declared in advance; keep old technical gates untouched.
- [ ] Source/evidence audit of the **final PR #10 candidate**; if needed update its old head `18a53b2...` to a reviewed implementation SHA **FF-only and separately authorized**, no force push; original draft state preserved until owner decision.
- [ ] Green CI on the **exact final PR #10 implementation head**, verified by authoritative Actions checks.
- [ ] Any required supported-Windows P3 acceptance supplementary fixture/Alembic checks (distinct from successful `test_all.ps1`) recorded; optional Playwright and four pytest skips declared, not silently passed.
- [ ] Reviewers approve a final amended acceptance decision; **only owner** authorizes `P3=PASS` and merge. No agent self-approval, no automatic phase transition.

If a required item is not satisfied, **STOP** at `P3=IN_REVIEW` and keep the technical GOLD finding visible. If future real OCR contradicts current controls, reopen the decision rather than grandfathering it.

## 6. PR workflow / no-code boundary

This **docs-only** decision record belongs to existing Draft PR #11 (`docs/p3-e1e3-windows-evidence-20261118`), not the implementation branch or `main`. Do not open a new branch or PR. **No source, tests, OCR or fixture edits**, no Windows rerun, no holdout/canonical rerun, no PR #10 pointer manipulation, no merges or phase P4/P5 commencement were authorized by this owner instruction.

**Decision ledger now:** `P2 POLICY PATH = OWNER SELECTED IN CHAT / FORMAL RATIFICATION PENDING`; `GOLD-EX-11 = FAIL / NOT PROVEN`; `P3 = IN_REVIEW`; `PR #10 = DRAFT, OLD HEAD`; `PR #11 = DRAFT DOCS`; no final acceptance.

---
*Educational synthetic demo. NOT FOR CLINICAL USE.*
