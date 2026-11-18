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


---

## F. Owner workflow correction — continue in the EXISTING Arena session (2026-11-18)

**This addendum supersedes ONLY sections A/E's instruction to implement on the freshly created `feat/p3-g11-a1-anchored-w2` branch and to open a third implementation PR. The owner objected to unnecessary extra branches/PRs and explicitly identified the ALREADY ACTIVE Arena session on `arena/752cca1f-ai-doctor-followup-agent`. The technical A1-Anchored + W2 scope, SIX allowed code/test paths, strict P1 policy, no real Windows OCR, no merge/auto-approval, untouched fixtures/holdout and STOP conditions in sections B–E stay unchanged.**

### Evidence from Arena's STRICTLY READ-ONLY workspace audit

- Arena session working directory `/home/user/AI-Doctor-FollowUp-Agent`, locally named branch `arena/752cca1f-ai-doctor-followup-agent`, **local shallow HEAD `5d30960c045de5eb6527de6aab64669d34fafb7a`**, **43 dirty paths** (39 tracked modified + 4 untracked), 0 staged.
- Arena reports byte-for-byte Git blob equality of **all 204 local file paths** to remote `af2bfd226cc53b5c4665c160a6d8310abcce8b53` (`mismatched_count=0`, no extra files). The displayed UI `+7101/-290` is the 6 already pushed commits `e3a4698`, `4f0862f`, `8f7c007`, `e5d6dbb`, `46ee188`, `af2bfd2` rehydrated as a dirty working tree on older shallow local HEAD. Arena ran only read-only inspection and made no changes.
- GitHub compare independently confirms `5d30960..af2bfd2 = ahead 6, behind 0`; `PR #10 HEAD 18a53b2..af2bfd2 = ahead 14, behind 0`, linear ancestry. The inadvertently created `feat/p3-g11-a1-anchored-w2` is **identical to `af2bfd2`, zero additional commits**, must **not** be used for development and should remain untouched unless owner separately approves removal.

### Corrected next steps in the SAME session (no new branch or PR)

1. **Metadata alignment only after full safety guards:** from existing Arena session branch, recheck `git ls-remote` pinned `origin/arena/752...` SHA unchanged, branch name, local HEAD, and **all 204** local paths and blob hashes equal to fetched remote target, including **all 4 previously untracked** files. A `git fetch` is allowed to populate `.git` only; it must not rewrite the working tree. If any mismatch or unaccounted file, STOP without reset. Once equality is **independently confirmed against fetched Git tree**, allow `git reset --mixed FETCH_HEAD` (explicitly **NEVER `--hard`**, no `clean`/stash). This changes only local `HEAD`/index metadata; existing bytes must remain identical; require clean `git status --porcelain`, `HEAD=af2bfd2`, no lost history, and report.
2. Once correctly aligned and clean, implement authorized **A1-Anchored + nonvacuous W2** in **this same Arena session and branch**, with RED first, minimal changes limited to the **same six authorized paths**, isolated local GREEN checks, and evidence reporting. **Do not open a new PR.** Stop if dirty/mismatched state, failed isolation, new required paths or unexpected results.
3. Continue review through **existing PR #10**. Only after the new code is committed/pushed to `origin/arena/752cca1f-ai-doctor-followup-agent` and independently audited, the owner or explicitly authorized maintainer may **strict fast-forward** PR #10's head ref `arena/ce85d4e6-ai-doctor-followup-agent` to the reviewed final P3 SHA after verifying true ancestry and unchanged expected old ref. **Do not force-push, rebase or merge into main.** This eventual PR-head fast-forward is a **separate action**, not authorized merely by this addendum; PR #10 stays DRAFT/unmerged for Windows gates and owner final review.
4. PR #11 remains independent Draft documentation; no merges. No change to protected Windows acceptance checkout/database or existing evidence.

**No action in this addendum is an OCR/P3 acceptance, P2 waiver, merge approval, or permission for a seventh changed implementation file.** This is a workflow correction in response to the owner's expressed preference to keep the already active Arena session and existing P3 PR, not a redefinition of scientific findings.

---

## G. Owner-delegated blocker resolution — seventh file and SQLite audit transaction (2026-11-18)

**Latest owner instruction:** “شوف الي انت شايفه صح واعمله”. This ChatGPT-authored section records the user's instruction to select the safest bounded unblock path; it is NOT an owner-authored GitHub signature. Section G adds one narrowly allowed file and one conditional design-proving activity, superseding only the prior six-file limit. Section F (SAME existing Arena session/branch) and all P1 scientific/merge/holdout restrictions still apply.

### G1. Arena-reported clean starting point

Arena reports the active `arena/752cca1f-ai-doctor-followup-agent` aligned and clean at `af2bfd226cc53b5c4665c160a6d8310abcce8b53`; 204/204 file bytes preserved. Tests ACTUALLY run by Arena on that baseline: 94 targeted PASS, full 789 PASS (395 P3), Ruff PASS and OpenAPI PASS. No code modifications on Step 2. These results are reported by Arena, not independently rerun by ChatGPT.

### G2. Explicit narrowly expanded scope: exactly SEVEN files

**OD-5b: APPROVED.** The previous six authorized code/test paths in Section C remain unchanged. Add ONLY a seventh path:

`docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`

Authorized changes to this document: update the genuine post-change backend/P3 collected and executed counts, paired headline text and exact two changed P3 test-file table rows, plus a short accurately labeled A1/W2 status note if necessary. Do not weaken, skip or remove `test_handoff_test_count_matches_the_suite_it_describes`. Historical 789/395 baseline counts remain correctly identified as historical; only claim new PASS counts after executing the corresponding tests. RED can temporarily fail the documentation count check; final GREEN must not. **No eighth path, no blanket docs permission, no PR #11 merge authority.**

### G3. SQLite lock: conditional proof of deferred ERROR audit, not a blanket redesign

Arena's empirical probe found a real `sqlite3.OperationalError: database is locked`: `resolve_session` flushes `UserSession.last_used_at` before the authenticated file route, so a concurrent `Session(bind=db.get_bind())` ERROR-audit commit cannot acquire a second SQLite writer lock. Do **NOT** implement this known-failing pattern, retry it, sleep around it, weaken audit guarantees, or commit/rollback the original request session's unrelated state.

**OD-2b: APPROVED — tightly scoped PROOF-OF-CONCEPT ONLY within previously allowed `backend/app/api/v1/documents/read.py` and the two authorized P3 test modules.** Evaluate an *outer, route-local FastAPI yield dependency* that records an enum-only error-audit intent during authenticated missing/mismatched `GET /file`, then durably writes the ERROR event using a fresh DB transaction **only after the existing `get_db_session` dependency has rolled back/closed and released the SQLite writer lock**. A dependency registered earlier is NOT proof of teardown order; demonstrate execution order on the repository's pinned FastAPI version with actual HTTP TestClient and instrumented offline tests before implementing the final A1 code.

**Mandatory empirical acceptance checks:**
1. `404 E_NOT_FOUND` response remains neutral; the error-audit intent occurs **only after authorized, scoped file lookup**. No `document.file_read OK` event for missing or corrupt source.
2. Prove complete request-session rollback and lock release **before** separate `AuditOutcome.ERROR` commit; no unrelated `last_used_at` or pending ORM state gets committed, no SQLite deadlock; persisted event is durable, append-only, idempotent per request, without document text/paths in detail.
3. Test both real file-backed SQLite and the supported in-memory/StaticPool database setup (if used), including exact request correlation/actor/doc scope, and reliable response/error behavior when the deferred audit itself fails.
4. Test the real HTTP dependency lifecycle, and explicitly distinguish direct Python calls of `read_file` (where FastAPI dependency cleanup does not execute). Do not claim they are operationally identical or break existing direct-call expectations silently.
5. Once proof tests PASS, proceed within the same seven allowed files to A1-Anchored (current `GET /file` response SHA, S1 stale anchor invalidation, S2 live SHA recheck at OCR verify/promotion, good re-read recovery, actual `settings.upload_dir`), plus non-vacuous real-HTTP design `W2/FC-3` and its **offline tests only**. Preserve R21 `rejected`, no spurious `13.4 g/dL` mapping, and full sibling verification for M6.

**STOP:** If correct FastAPI teardown order, durable ERROR audit without collateral commits, safe SQLite handling, or direct-call compatibility cannot be proven inside the SEVEN approved paths, stop with exact test evidence. **Do not** independently edit `accounts.py`, `db/session.py`, `services/audit.py`, schema/migrations, helpers, auth or an eighth file. Request a separate owner decision before any expansion or alternate design.

### G4. All previous governance boundaries remain

Continue in the SAME Arena session and original branch `arena/752cca1f-ai-doctor-followup-agent`; no new branch or PR. After RED/green offline changes, push only to this active branch and stop for independent review. Later FF-only advancement of original PR #10 head requires a separate owner decision. P1 strict `GOLD-EX-11=FAIL / NOT PROVEN`, P3 `IN_REVIEW`. No P2 amendment, original fixture/threshold edits, protected DB, real Windows OCR, canonical/exploratory/holdout/freeze, PS wrapper, merge to main or P4/P5. **This is bounded implementation scope approval, not acceptance.**

**Status:** `OWNER-DELEGATED SEVEN-PATH SCOPE + EXPERIMENTAL DEFERRED-AUDIT PROOF AUTHORIZED; NO STEP 2 IMPLEMENTATION COMPLETION CLAIMED`.
