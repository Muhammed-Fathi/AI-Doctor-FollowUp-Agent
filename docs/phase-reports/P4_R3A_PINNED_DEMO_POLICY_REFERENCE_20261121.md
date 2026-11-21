# P4 R3-A — Owner-pinned synthetic demo policy reference (offline only)

**Status:** CODE PR OPEN / OWNER REVIEW REQUIRED / P4 IN_REVIEW.  
**Decision evidence:** After personally merging [PR #27](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/27), the owner wrote **"تم دمج PR #27، وموافق على R3-A وR21-S1"** on 2026-11-21. This explicitly ratifies R3-A *synthetic fixture-reference* parameters and separately R21-S1 *future doctor-authored run selection* semantics. It does not activate tools, run rules, alter OCR or authorize P5.  
**Base:** `main@35c680b59d7aa2e7fb951d1bdd6650af5d839f01` (owner-merged PR #27). [Postmerge main CI #44899015847](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44899015847) **COMPLETED/SUCCESS** for Backend + Frontend at this exact baseline. [Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains OPEN.

## 1. Exact bounded scope and immutable reference

**Source of truth for the selected arbitrary synthetic-only numbers:** `docs/clinical-safety/DEMO_REVIEW_RULES.md` ``8–9; the new immutable fixture-reference artifact is `data/synthetic/policy/demo_review_policy.yaml` with the exact owner-approved values. Its **raw SHA-256** is:

`f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`.

The pinned policy is `demo-policy-1.1.0`, `demo_only=true`, `demo_as_of_utc=2026-11-14T12:00:00Z`, and the existing fixed neutral notice. Parameters (exact): `baseline_lookback_days=90`; `stale_measurement_days=30`; absolute synthetic deltas systolic 10 mmHg, diastolic 8 mmHg, heart rate 15 bpm and glucose 40 mg/dL; `ocr_confidence_floor=0.70`; `conflict_tolerance=0`; `max_items_per_type=3`. All six `VI-001..006` and all six `DR-001/003/005/006/008/009` switches are true **in the offline reference catalogue**, not runtime. No clinical interpretation, danger threshold, diagnosis, treatment, score or urgency is inferred.

The raw SHA-256 and exact-value assertions require a *new reviewed policy_version and fixture impact decision* for any change. The fixture-only test uses PyYAML's safe loader with **duplicate mapping keys rejected**; the generic `validate_demo_policy` remains a strict *candidate* validator and deliberately does **not** authorize a runtime policy. In particular, it may structurally accept a disabled `VI-*` switch for testable invalid candidates, whereas the owner-pinned reference tests independently require **every blocking VI enabled**.

## 2. Exact six changed paths

1. `data/synthetic/policy/demo_review_policy.yaml` — a static synthetic reference file **never loaded by app production/runtime**.
2. `backend/tests/p4/test_p4_demo_policy_reference.py` — test-only SHA seal and strict YAML decode, frozen typed policy, exact approved parameters, blocking VI completeness, invalid mutation/version/clock/disabled switch cases, raw GOLD expected fixture SHA checks and synthetic A/B/C/D arithmetic/issue invariants.
3. `docs/phase-reports/P4_R3A_PINNED_DEMO_POLICY_REFERENCE_20261121.md` — this report and safety boundary.
4. `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — append-only expected whole-backend suite count pairing; no P3 tests/executable changes or historical result edits.
5. `docs/phase-reports/PHASE_4_REPORT.md` — append-only implementation/evidence checkpoint.
6. `docs/roadmap/PHASE_PROGRESS.md` — append-only verbatim owner approval and separate R21 scope record.

**No modifications** to any runtime Python module, YAML loader in the API, SQL schema/migration, agent tool contract, policy activation switch, P3 OCR logic, source facts/doctor decisions, P5 workflow/run, review persistence, task, notification, frontend or four existing GOLD expected files. GitHub scanner rules are unchanged.

## 3. Golden-fixture integrity and provenance

GOLD A/B/C/D expected JSONs are unchanged. Reference tests pin their raw byte hashes; existing `test_p4_gold_abcd_offline_replay.py` continues to exercise a **scripted synthetic SQLite** case matrix. The original GOLD fixture key `candidate_policy_status="test-only-unapproved"` is deliberately **unchanged**, because its test-only candidate rule engine and caller-controlled `blocking_fact_count=0` remain *unapproved for live use*, independently of approving the **reference parameter values**.

Fixture raw SHA256:
- GOLD-A `643c219ba15c77e2ddd1f7273931aafc40d3bf37725386c590dc2535ff5211be`
- GOLD-B `4019f1700fd7407e5df9f264dcd73b317d3b61d8e511e7ad8689a2de2d054cd3`
- GOLD-C `555d41d5d52187a154a2d3e258e94cc9f1e5dd3bee6ab67aa4ac1d359156f6f0`
- GOLD-D `d4aea8155f690c4420a194e317b7fc202a9d3a3e7671bb22d363c70092065940`

Reference checks keep the following distinct: Case B self-reported systolic abs delta 12 > demo 10; Case C **pre-correction VI-001/002/003/005 blocking**, followed by **test-scripted**, not real OCR, glucose delta 9 ≤ demo 40; Case D diastolic delta 168 > demo 8 plus data-quality entries; Case A no demo flags. These do not prove a run-gate, future review queue or real document OCR accuracy.

## 4. Executed vs pending verification

**Reviewed:** source catalogues and candidate validator from `main`, PR #27 owner decision and postmerge CI.  
**At authorship:** no local Linux or Windows repository Python suite, Tesseract, Playwright or E2E run was executed by this assistant. The new file and test have been committed via the GitHub connector; integrated results **require exact-head GitHub Actions**. New test module contains **11 test functions / 26 expected collected test cases**, for a **provisional 1051 whole-backend / unchanged 443 P3**; this is a collection estimate, not a pass count. Correct the append-only handoff token if authoritative CI differs. A failed gate cannot be declared approved.

**Mandatory before owner merge:** exact-head Python 3.12 Ruff lint + format, full Pytest, Alembic reversible smoke, OpenAPI, tracked scanner and Frontend Node 22 CI. Owner must run `scripts/powershell/setup.ps1` and `scripts/powershell/test_all.ps1` on an isolated pinned Windows worktree at the final SHA, then send log for independent review. Optional Playwright skip is not PASS. No agent self-merge.

## 5. Owner boundaries and R21 next step

**R3-A approved:** only the numbers/catalogue/clock for an offline synthetic *reference artifact*. This does NOT grant `run_gate_completed=True`, a verified runtime `EvaluableReviewEvidenceV2`, source byte/glyph authenticity or policy activation; the `backend/app/services/demo_policy.py` candidate API and P4 R2 internal inspector are not altered. R1-A still defers `review_item` storage until genuine P5 `workflow_run` identity.

**R21-S1 approved separately:** plan a **new, independent PR after R3-A owner merge**, limited to offline migrated-SQLite **future source-selection policy tests** with explicit doctor-authored exclusion intent, fail-closed original+recovery selection rules, and immutable preservation of terminal original's open `VI-002`. No change to P3's existing patient-declared `recovery_of` behavior, no VI-002 auto-clear, no fake run IDs, no actual P5 manifest/gate yet. If source original included => HALT. If only recovered selected, an audited assigned-doctor selection intent and **future full run gate** remain mandatory; under P4 result stays unavailable/false. R21-S1 is not permission to skip verification.

**Project status:** P4 **IN_REVIEW / NOT ACCEPTED**, P5 not started. P3 academic conditional acceptance unchanged. The real Windows OCR `GOLD-EX-11=FAIL / NOT PROVEN`, the `1O5`→`105` false-clean recognition and source-glyph limitation remain *unresolved*. NOT FOR CLINICAL USE.


## 6. Owner Windows R3-A review: CRLF-only SHA mismatch and canonical line-ending correction (2026-11-21)

**Exact owner evidence:** uploaded PowerShell log `Pasted text(20261121-115633).txt`, isolated worktree `E:\\DEPI\\P4-R3-Review-c6733aa`, `git rev-parse HEAD=c6733aa451c26f1b3d75d956e7f9f1734b56d955`, `setup.ps1=PASS`, `test_all.ps1=FAIL` (**11 top-level PASS / 1 FAIL / 1 optional Playwright SKIP**). Ruff lint/format, Alembic reversible migration, OpenAPI, frontend 13 tests/build and repository scanner PASS. Backend pytest had **9 FAILED** in the new reference module (all reference/GOLD SHA comparisons), **4 SKIPPED** unrelated tests, with no other failure.

**Root cause verified without guessing or changing fixture values:** Python test originally hashed the *raw checked-out bytes*. GitHub committed text is full **LF**, while owner Windows checkout uses **CRLF**. Exact Policy CRLF hash, independently calculated from GitHub source, is `eb635f5b320a5d87f146c1e8010834c02c03caee4721ebc9cc891ef8b7013c1e`, **identical** to the value in Windows failure output; canonical LF hash is still `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`. GOLD-A/B/C/D committed raw LF hashes continue to match the original approved reference values; platform CRLF newline conversion explains their four failures, not a changed GOLD fixture.

**Correction:** `backend/tests/p4/test_p4_demo_policy_reference.py` now canonicalizes **only uniform CRLF line endings to LF** before SHA comparisons and decoding, explicitly rejecting **mixed line endings** and **bare CR**. It checks both LF and simulated CRLF for the policy and every GOLD file within **existing test cases**; no reduced SHA comparisons, missing-file bypass, values changed, disabled VI, policy activation or P3 test edits. The constants remain the exact **canonical LF source/Git blob** SHA-256 hashes; wording “raw SHA” above is clarified to mean *raw LF Git version*, **not arbitrary platform checkout bytes**. Changes to content/spacing other than the entire file's newline representation must still fail. **Same 1051 total collected test cases / 443 P3** (no new tests added), pending rerun.

**Status:** previous Linux exact-head PR/push CI at `c6733aa` SUCCESS; owner Windows FAIL means **DO NOT MERGE** that head. This correction requires **new exact-head CI success** and **a fresh owner Windows quality gate** on the new SHA before merge. Do not rewrite old Windows evidence or claim a pass now. P4 remains IN_REVIEW and original real OCR GOLD-EX-11 remains FAIL / NOT PROVEN. NOT FOR CLINICAL USE.
