# P3-G11 — Independent Review of Arena Design v2.1 Corrigendum

**Date:** 2026-11-18  
**Disposition:** **DESIGN REVIEW COMPLETE — CONDITIONAL DESIGN ACCEPTANCE; AWAIT EXPLICIT OWNER SCOPE/POLICY DECISIONS.** No permission to implement, execute an OCR diagnostic, rerun canonical, touch holdout, alter acceptance semantics, merge or promote P3.  
**Source:** owner-uploaded complete **Design v2.1 Corrigendum** (96 source lines) and authenticated Arena PR #10 [comment 6979769036](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6979769036), cross-checked against pinned implementation commit `af2bfd226cc53b5c4665c160a6d8310abcce8b53` using read-only GitHub fetches. **No tests or Windows executions during this review.**

## 1. Verification of corrections C1–C5

| Requirement | Independent verdict | Basis |
|---|---|---|
| **C1 — clean Hemoglobin 13.4** | **SATISFIED at design level.** A doctor can confirm the clean report while `decide_mapping` returns `unmapped_test_name` and creates **zero Observations**, as the mapping is closed. | `backend/app/core/enums.py:MAPPING_TABLE`, `DocumentUnit.G_DL`; `backend/app/services/documents/mapping.py:decide_mapping`. |
| **C2 — stale successful source-read anchor** | **SATISFIED at design level, with an owner boundary choice.** Now identifies S1 (valid read → tamper → failed read → verify) and S2 (valid read → silent tamper → verify) and distinguishes `A1-Narrow` from stronger `A1-Anchored`. | `backend/app/services/documents/verification.py:_doctor_accessed_source_file` checks only successful `document.file_read` events and lacks current-byte validation; `read.py:read_file` lacks SHA check. |
| **C3 — false attestation M6** | **SATISFIED at design level.** Zero Observations after value-only decision; a mapped `105 mg/dL` Observation can only appear after all necessary date/name/unit/value OCR decisions and verification guards pass. | `record_decision`→`_recompute_document_status`→`_maybe_promote_document`→`_create_observation_from_mapping` and closed `decide_mapping`. |
| **C4 — source precision** | **SATISFIED.** Correct `document.mime_type`, exact detector keys D1–D6, and outer wrapper—not the immutable bundled launcher—is responsible for the observed PS5.1 `NativeCommandError`. | Pinned `read.py` and prior actual Windows metrics/incident. |
| **C5 — preserve invariants** | **SATISFIED as proposed restrictions, NOT YET TESTED.** Actual real-HTTP `105` mappability is required for `W2` (or explicit NOT RUN/FAIL), literal `GOLD-EX-11` remains untouched and separate, R21 and original bundle/fixtures untouched, and the holdout remains unrun. | Current `windows_ocr_acceptance.py:gate_ocr_corruption` and original owner Windows 3-case evidence; new code not written. |

**Verdict on the design itself:** Focused v2.1 corrigendum addresses the substantive v2 reviewer objections. **No Design v2.2 is required merely to reword these findings.** Any follow-on proposal must be limited to explicit owner decisions and a code-level safety/test review.

## 2. Conditions to enforce in any subsequently AUTHORIZED implementation

1. **Recommendation OD-2a = `A1-Anchored`**, not `A1-Narrow`, if owner wants the stronger claim “stored source intact at OCR verify/promotion boundary.” S1 and S2 regressions are mandatory. `A1-Narrow` leaves both known scenarios exposed and cannot be described as protecting all later verification.
2. **Do not overstate even anchored semantics.** The rehash is an integrity **snapshot at the decision/promotion check**; it cannot prove the doctor accurately interpreted image pixels or guarantee that bytes never change after a completed `doctor_verified` Observation. Distinguish procedural, time-of-check and cognitive limitations.
3. **Verify all function arguments/scope at the implementation diff.** `verify.py:verify_fact` receives `settings: AppSettings`, but currently passes only `conflict_tolerance` to `verification.record_decision`. A future `_stored_source_intact` check needs the **actual configured `settings.upload_dir`** threaded explicitly through `record_decision` / `_validate_ocr_confirmation` / `_maybe_promote_document` / `_create_observation_from_mapping`. Do not silently fall back to default runtime upload dir, especially in isolated tests. Preserve the zero-migration and R21 rejection path. Existing direct helper test callers must be migrated safely or intentionally defaulted with tests.
4. **Review independent ERROR-audit transaction carefully.** `get_db_session` rolls back when `ApiError` is raised; a separate `Session(bind=db.get_bind())` committed inside a request may behave unexpectedly with SQLite single-connection/in-memory test configurations or concurrent locks. Prove that the `AuditOutcome.ERROR` is durable without committing unrelated pending ORM state or leaking private details; test SQLite file and in-memory configurations if the repo supports them. An alternative bounded route-specific commit is possible only if proven safe and consistent with current read-only path; do not assume that `Session(bind=...)` alone is an isolation guarantee. No successful `document.file_read` audit may be emitted on missing/tampered source.
5. **Anchor invalidation must be time/actor/document precise.** Use a stable chronological key `(created_at, SQLite rowid)` for successful and failed file access; preserve fresh post-extraction `GET /file` and same-doctor scope, and test correct subsequent recovery after a new successful **intact** read. Events for other documents must never validate or invalidate an unrelated doctor's source confirmation. Decide and document the intended scope for a document-level corruption event even when triggered by a permitted patient GET.
6. **Make positive controls genuinely non-vacuous.** New W2 must prove persisted, real unmodified HTTP OCR yielded a **mappable 105 mg/dL glucose fact**, plus necessary date/name/unit siblings and provenance. It must show zero Observations BEFORE review and valid R21 rejection. The false-attestation residual M6 test must not claim an Observation after value-only verification, and no W2 PASS is permitted when OCR/layout is absent or unmappable. `13.4 g/dL` is a valid **unmapped** clean control, not a 13.4 Observation.
7. **Keep wrapper independent.** The proposed PS5.1 raw stdout/stderr + true exit wrapper is separately owner-gated; synthetic mock-child tests first, collision-proof fresh diagnostics directory and unconditional pre/postflight. Existing authenticated v1.1.3 ZIP, five files and historic Windows runs remain immutable.
8. **Do not implement on obsolete PR #10 head.** Its actual `head` remains older `18a53b2...`; use a fresh bounded review branch from the explicitly approved **pinned R21+Stage3 SHA `af2bfd2...`**, with a separately reviewed draft implementation PR and exact changed-file list, only after owner explicit scope approval. Keep docs-only PR #11 draft/unmerged until owner permission; no direct `main` writes.

## 3. Policy choice / owner ledger

**Current legal project policy: P1 (strict)**: `GOLD-EX-11` must be a genuine G1 OCR detection of literal `1O5` and **remains FAIL / NOT PROVEN** while Windows Tesseract returns `105`. Consequently P3 must not be marked PASS or merged on the current literal policy, **even if** A1 and W2 future tests pass.

**P2 possible only on explicit written OWNER approval:** amend the Windows acceptance *contract*, not the OCR result, to report G1 as an independently preserved **FAIL/NOT PROVEN engine limitation** while using real-engine, independently reviewed G3/G4/W2 source-aware safety as the separate application acceptance criteria. P2 cannot be accepted now just from Design v2.1 and cannot claim that false human attestation becomes impossible; it still requires actual Windows evidence, full acceptance checks and owner review.

**Recommended order, not authorization:**
- `OD-1`: **DEFER P2 amendment**, keep P1 in force during initial implementation/testing; decide after actual W2 evidence and explicit discussion of the remaining human false-attestation risk. Alternatively owner may consciously choose P1 permanently.
- `OD-2`: CONDITIONAL RECOMMEND approval of **core minimal A1 + W2 tests** only with owner-signoff on exact code/test file scope, no production OCR config change or API contract rewrite.
- `OD-2a`: CONDITIONAL RECOMMEND `A1-Anchored` with strict SQLite/audit tests above.
- `OD-3` and `OD-4`: DEFER optional `ExtractionResponse` fields, heuristics and dead-branch cleanup.
- `OD-5`: Owner scope exception is required for changes outside default P3 path allowlist (especially `scripts/python/windows_ocr_acceptance.py`, shared docs `docs/**`, and any `scripts/powershell/**` change). No implicit blanket permission.
- `OD-6`: Separate approval of wrapper-only synthetic mock tests; defer running any OCR diagnostic until an independent reviewer authorizes the exact revised binary/commit and evidence plan.

**ALL owner selections currently PENDING** — no reviewer has approved them on the user's behalf.

## 4. Required next step

**Owner decision checkpoint, then bounded implementation only if explicitly approved.** Have Arena submit a **precise implementation authorization request** enumerating (i) exact new base branch and file-scope, (ii) decision `P1 vs P2`, (iii) `A1-Anchored vs Narrow`, (iv) test-only first RED/then GREEN, (v) SQLite audit/transaction and same-doctor/stale-anchor validations, (vi) STOP/rollback and Windows evidence handoff. The existing 96-line Design v2.1 is technically sufficient as the design basis with conditions above; no need to rerun design iterations, but do not execute any implementation without the owner’s affirmative authorization.

**Current end state:** `DESIGN v2.1 REVIEWED / DESIGN BASIS ACCEPTABLE WITH CONDITIONS / OWNER DECISIONS OPEN`. P3 = `IN_REVIEW`; GOLD-EX-11 = `FAIL / NOT PROVEN`; exploratory/holdout/freeze/P4/P5, code edit, acceptance, merge NOT AUTHORIZED.

*Educational synthetic demo only — NOT FOR CLINICAL USE.*
