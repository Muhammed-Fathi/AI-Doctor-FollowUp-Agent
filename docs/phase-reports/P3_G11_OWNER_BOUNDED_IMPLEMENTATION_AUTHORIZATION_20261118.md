# P3-G11 — Owner's Bounded Implementation Authorization (2026-11-18)

**Decision recorded by ChatGPT following the owner's explicit agreement in this conversation (“ماشي يلا”) to the immediately preceding proposed plan.** This is a record of the owner's instruction as conveyed in chat, **not an owner-authored GitHub ratification comment**, and does not transfer final acceptance/merge authority to an assistant or Arena.

**Status: BOUNDED IMPLEMENTATION / TEST DEVELOPMENT AUTHORIZED on a NEW ISOLATED BRANCH only; NO MERGE, PHASE ACCEPTANCE OR WINDOWS OCR EXECUTION AUTHORIZED.**

## A. Exact baseline and implementation branch

- Repository: `Muhammed-Fathi/AI-Doctor-FollowUp-Agent`.
- Authoritative **already implemented** Stage 3/R21 baseline commit: `af2bfd226cc53b5c4665c160a6d8310abcce8b53`.
- Fresh review branch **created at that exact commit**: `feat/p3-g11-a1-anchored-w2` (GitHub create-branch success on 2026-11-18). This is **not** the older P3 PR #10 code head (`18a53b2de5ee9a7cd44d473b78f8ecbaa28fb1f5`).
- Arena must inspect the fresh branch SHA and clean state before any edits; if head changed or unreviewed files are present, **STOP**. Do not base changes on Arena's unrelated dirty local workspace, or overwrite `E:\DEPI\P3-Acceptance-af2bfd226cc5` on the owner's Windows machine.
- Open a new **DRAFT implementation PR** into `arena/752cca1f-ai-doctor-followup-agent` **only if the target base is still the intended pinned Stage 3 branch and diff is limited to approved scope**. If not, STOP and report base/graph mismatch, do not target `main` automatically. No approval, merge, auto-merge, or PR #10/11 modification by Arena.

## B. Owner decisions — precisely scoped

| Decision | Authorized / retained state |
|---|---|
| OD-1 — GOLD release policy | **P1 RETAINED.** The literal G1 `GOLD-EX-11` release blocker still applies; `FAIL / NOT PROVEN` until genuine unchanged-fixture Tesseract output meets original acceptance. P2 governance amendment **DEFERRED**, not silently adopted. |
| OD-2 — code scope | **APPROVED**: minimal A1 source-file-integrity hardening + non-vacuous real-HTTP `W2/FC-3` acceptance code and focused regression tests only. |
| OD-2a — integrity boundary | **A1-ANCHORED APPROVED**, not A1-Narrow: integrity at `GET /file` + stale-read audit-anchor invalidation + current source hash verification at OCR fact verification and before Observation promotion.|
| OD-3 — optional `ExtractionResponse.source_truth_notice` contract addition | **DEFERRED.** |
| OD-4 — new `confusable_digits_present` field and unrelated cleanup | **DEFERRED.** |
| OD-5 — file-scope exception | **APPROVED ONLY for the six implementation/test paths in section C and for this authorization report / `PHASE_PROGRESS.md` update**; not a blanket docs or scripts exception. The existing draft docs PR #11's other file-scope exceptions and its merge remain separately pending owner review. |
| OD-6 — PS5.1 wrapper change | **SEPARATE / DEFERRED.** Current authorization does not allow writing a new PS wrapper or executing any OCR/Windows diagnostics; produce its follow-up proposal separately. |

This decision allows **code implementation in a branch and isolated local non-Windows regression testing**. It does NOT authorize use of real patient data or protected databases, an environment change, any canonical/exploratory/holdout rerun, `freeze_rules_only`, or passing P3.

## C. Exact allowlist for implementation

Only the following **six** implementation/test repository paths are authorized:

1. `backend/app/api/v1/documents/read.py` — single-buffer SHA-256 match before successful `GET /file` response/audit, preserve `document.mime_type`, neutral 404 on unavailable/corrupted source, accurate and durable confidentially safe `AuditOutcome.ERROR` evidence; optional `ETag` and `X-Content-Type-Options: nosniff` for the intact response only.
2. `backend/app/api/v1/documents/verify.py` — pass actual `settings.upload_dir` to verification service, and nothing unrelated.
3. `backend/app/services/documents/verification.py` — anchored checks at `record_decision`/`_validate_ocr_confirmation` and `_create_observation_from_mapping`, invalidation of stale `GET /file` OK anchors after integrity ERROR; preserve R21 `REJECTED`, same-doctor/patient/document boundaries, append-only decisions and Observation uniqueness.
4. `scripts/python/windows_ocr_acceptance.py` — add the new **non-vacuous W2/FC-3** code but do NOT change original `gate_ocr_corruption`, thresholds, fixture code, or existing acceptance semantics. This is a narrow `AGENTS.md §5` file-scope exception, not permission to run real OCR.
5. `backend/tests/p3/test_p3_stage3_verification_hardening.py` — tests of A1-Anchored, S1/S2 stale anchor, audit transaction isolation, cross-patient/doctor/document, clean controls, R21, false doctor attestation residual.
6. `backend/tests/p3/test_windows_ocr_acceptance.py` — offline/mocked helper logic and W2 non-vacuity tests, without executing owner Windows OCR or touching protected data.

**No additional file may be changed** without a new owner decision in the PR conversation and phase tracker. Existing tests may be run read-only from the new branch but not rewritten outside the allowlist; report any required wider scope. The required implementation report should be posted in the draft PR body/comment, not committed to an unauthorized new docs path.

## D. Non-negotiable RED / GREEN implementation gates

1. **RED first:** Add tests showing current absent guards actually fail on pinned baseline (tamper detection, stale OK anchors S1/S2, W2 vacuous false pass). Keep test output, command and exit code; avoid changing fixtures to force a failure.
2. **Fix minimally:** `read_file` must hash the **same** bytes it returns, check hash before `AuditOutcome.OK`, never commit unrelated uncommitted ORM changes when persisting `AuditOutcome.ERROR`. An isolated `Session(bind=db.get_bind())` alone is NOT proof of transaction isolation with SQLite in-memory/single-connection tests. Validate both supported file-backed and isolated test DB modes; STOP if safe durable audit semantics cannot be proven.
3. **Anchored security:** `settings.upload_dir` propagated from request through all check points; `(created_at, SQLite rowid)` ordering for success/error, with strict matching of doctor/doc and current extraction; do not erroneously allow another patient's read to validate, or wrongly invalidate unrelated documents. Verify success recovery after a *new valid intact* `GET /file`. Reject/scope behavior must be preserved even with tampered or missing bytes.
4. **Verification boundary:** For OCR `VERIFIED` or `CORRECTED`, an intact source is required at decision time, and again before mapped Observation creation. A rejected fact must still follow R21 with zero Observations; recording a rejection does not require opening a corrupted/unreadable file. The check is a snapshot, NOT proof a human saw the pixels, and not proof bytes cannot change later.
5. **W2 non-vacuity:** Require real unmodified synthetic fixture `1O5`, actual HTTP/persisted `tesseract` OCR, a mappable `105 mg/dL` glucose candidate with date/name/unit siblings, pending verification and zero Observations **before** invoking invalid verification/rejection tests. If layout/facts are missing or the OCR engine preserved `1O5`, report **NOT RUN/FAIL with explicit reason**, never PASS by vacuity; keep the G1 `gate_ocr_corruption` unchanged. Isolated unit tests may simulate W2 state transitions but MUST NOT be reported as real-engine Windows proof.
6. **Controls:** `Hemoglobin 13.4 g/dL` is clean **UNMAPPED** (verified doc, zero Observation); `Glucose 104 mg/dL` is mapped positive (Observation only after complete valid source-confirmed verification). False `105` doctor attestation remains an explicit documented residual; zero Observation after value-only verification, potential single Observation after verifying every sibling and falsely attesting the source.
7. **Evidence/provenance:** Record tests run vs not run, changed files and exact SHAs, `pytest` subset/full suite and lint if possible; stop on unexpected test failures; no output interpreted as clinical safety validation.

## E. Stop / handoff boundary

- **STOP** for nonapproved files, unexpected HEAD/worktree status, SQL transaction isolation issues, broken R21 contracts, mismatching tests, any desire to alter `GOLD-EX-11`/fixture/OCR params, or any real Windows OCR requirement.
- Allow **a draft PR and its review**, not a merge. The owner will inspect the full diff and independent test evidence before any separate approval to run Windows real-engine checks. **Do not start P4/P5.**
- Keep `GOLD-EX-11 = FAIL / NOT PROVEN`; `P3 = IN_REVIEW`; no claims of accepted P3 until governed separately.

**Report origin:** owner’s explicit conversational approval, transcribed into this GitHub docs artifact by ChatGPT; no generated PR comment can be construed as the owner personally authenticating into GitHub to sign a separate policy amendment.

*Academic synthetic demo, NOT FOR CLINICAL USE.*
