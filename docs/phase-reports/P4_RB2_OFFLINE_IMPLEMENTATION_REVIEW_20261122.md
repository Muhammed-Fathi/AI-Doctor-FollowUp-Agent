# P4-RB2 Offline Six-Rule Implementation — Review Candidate (2026-11-22)

**Status: IN_REVIEW / tests pending at initial draft / NOT ACCEPTED.** Repository: `Muhammed-Fathi/AI-Doctor-FollowUp-Agent`. Base `main@eaab808b81986077c94eec8f4858c9f746c92ca8` ([PR #38](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/38)); exact merged-main [CI #45005337550](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45005337550) COMPLETED SUCCESS Backend Python 3.12 and Frontend Node 22, before branch creation. Owner scope marker: [RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/38#issuecomment-7076744806). P4 issue #14 remains OPEN.

## Exactly eight authorized paths

1. `backend/app/services/p4_rb2_offline_rules.py` — new pure engine.
2. `backend/app/schemas/p4_rb2_offline_rules.py` — new frozen fixture inputs/non-authoritative outputs.
3. `backend/tests/p4/test_p4_rb2_offline_rules.py` — rule/negative/edge coverage.
4. `backend/tests/p4/test_p4_rb2_gold_offline.py` — fixture-only GOLD A/B/C/D replay.
5. `docs/contracts/TOOL_CONTRACTS.md` — append-only boundary.
6. `docs/phase-reports/P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md` — this report.
7. `docs/phase-reports/PHASE_4_REPORT.md` — append-only progress.
8. `docs/roadmap/PHASE_PROGRESS.md` — append-only checkpoint.

## Scope and safety

- Pure deterministic candidates `DR-001/003/005/006/008/009`: newest prior within 90 days, 30 whole-day stale, strict absolute threshold, independently distinct **fixture-asserted** document sources, duplicate/created-vs-measured ordering, engineering typo band. Stable evidence, trust suffix, sort, 3/type cap, and no-current selection semantics.
- **No DB, disk read, state mutation, framework endpoint, agent registration, graph, LLM, task or messages.** The schema can receive test fixture assertions but cannot accept caller gate status as run authority. A fixture asserting two sources does **not** prove two actual doctor verifications.
- Strict policy shape and exact numeric checks in pure source. The synthetic YAML SHA and frozen A/B/C/D expected JSON digests are checked *only by tests*. No alteration to existing offline engines, Gold fixtures, P3 OCR logic, P5/F1/F2/RB1, CI or migrations.
- **No clinical safety claims**: original P3 real OCR `GOLD-EX-11 1O5→105 = FAIL / NOT PROVEN`, P3 conditional synthetic acceptance, P4 IN_REVIEW and full P5 not accepted remain.

## Test status and gates

**Initial authoring status:** new tests and implementation files committed; full Python 3.12 CI, Ruff, Alembic smoke, OpenAPI, scan, Node 22 and isolated Windows 5.1 exact-head `setup.ps1`+`test_all.ps1` **NOT YET VERIFIED** at report creation. No PASS is claimed here.

Acceptance requires complete exact-head CI + independent Windows gate, negative/side-effect/source review and owner approval. `RB2-01..18` are acceptance criteria, not yet certified pass outcomes. Adding tests may trip P3's historical strict `N collected / 443 P3` reference; **if it does, STOP and request a new precise owner exception for only `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`**, append-only measured collection pairing, never manufactured test-pass or reused RB1 authority. No out-of-allowlist changes without an owner decision.

## Deferred to distinct phases

RB3 must independently verify F0/F1/F2/RB1, selected document bytes, patient+doctor scope, and actual policy/clock under a new owner-gated write boundary before `review_item` or `evidence_link` storage. RB4 must perform real run-backed GOLD acceptance. Neither is implemented here. P6/P7/P8 remain to be completed separately. Rollback: close this draft PR; main and stored rows remain untouched.


## CI review checkpoint: exact-head failure is historical P3 collection pairing (2026-11-22)

- [PR CI #45006265207](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45006265207) ran at branch HEAD `1a8405f666ca4211613cbfd0e42bbac1280b77ef`, reported **Backend Python 3.12 FAILURE** and **Frontend Node 22 SUCCESS**.
- Backend **Ruff lint SUCCESS; Ruff format SUCCESS (141 files already formatted)**. Full `python -m pytest -q` completed collection and reported **exactly one failure**: `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes`. The failure is the historical handoff's absence of the required exact string **`**1204 collected**`**. This is a **collected test count, never 1204 tests passed**. Historical P3 count remains **443**. New RB2 tests did not appear in the test failure summary, but this is not a separate independently certified all-pass RB2 run.
- Backend later Alembic, OpenAPI, secret/artifact scan were **SKIPPED by the CI job after failed Pytest**, so no green claim for them. Independent Windows PowerShell 5.1 `setup.ps1` and `test_all.ps1` **NOT RUN**.
- **MANDATORY STOP:** the original eight-path permit explicitly excludes `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`. **Do not edit that file without an entirely new owner PR #41 Conversation permission** limited to a ninth path, append-only `**1204 collected**` / `**443**` P3 pairing, preserving all historical Windows/OCR evidence and statuses. No P3 tests/code or fixtures may be changed. An eventual new CI run must verify the exact final head and all downstream gates before owner Windows testing or merge.


## Owner-approved ninth-path collection checkpoint (2026-11-22)

- **Permission verified:** owner `Muhammed-Fathi` posted the exact standalone `APPROVE-P4-RB2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION` at [PR #41 comment #7077204700](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7077204700), `2026-11-22T09:31:39Z`. The permission was recorded in the Roadmap before the out-of-allowlist write.
- **One path only, append-only, completed:** `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` now has a current pairing of **1204 collected** whole-backend / **443** P3 tests. The note links [CI #45006638723](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45006638723), accurately states it failed exactly the historical count-pairing assertion, and explicitly says collection is not tests passed. All previous historical entries were preserved. No P3 executable source, tests, fixtures, Windows evidence or OCR claims changed. Roadmap approval record is in commit `9cf69284b148b7506a102a89ea82eab0cee28b9d`; P3 handoff append is in commit `75b99ec125fb0cf9d95251416218bdf7aa8abc5c`.
- **Next gate:** full CI on the new final PR head is pending. Require Backend Ruff, Pytest, Alembic, OpenAPI, secret/artifact scan and Frontend Node all green. Only after exact-head CI succeeds should owner perform independent Windows PowerShell 5.1 `setup.ps1` + `test_all.ps1` and independent review. No test pass or phase acceptance is inferred from the collection-only note.
- PR #41 remains **DRAFT / NOT MERGE-READY**. P4 remains IN_REVIEW; issue #14 OPEN. RB3/RB4 remain deferred. Real P3 `GOLD-EX-11 FAIL / NOT PROVEN` remains unchanged. **SYNTHETIC ONLY / NOT FOR CLINICAL USE.**
