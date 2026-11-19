# Phase 4 — Monitoring & Deterministic Demo Review Rules

**Status:** IN_REVIEW — implementation in progress, NOT ACCEPTED  
**Owner kickoff:** [Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14)  
**Start date:** 2026-11-19  
**Baseline:** main at 2e99fcf59e05f4076754ce70e2a3ac9657810183; P3 educational conditional closure merged and CI SUCCESS  
**Safety:** LOCAL SYNTHETIC EDUCATIONAL DEMO ONLY; NOT FOR CLINICAL USE.

## 1. Phase contract and planned stages

This is P4 only. Primary sources: MASTER_PLAN.md §5 P4, MVP_SPEC.md REQ-MON-01/02/03 and REQ-RULE-01/02/03, TOOL_CONTRACTS.md §3.4/3.5/3.7, DEMO_REVIEW_RULES.md §3-12, DATA_DICTIONARY.md §2.9/2.10. The owner authorized starting P4 after P3 had been conditionally accepted/merged. No agent-authorized phase PASS, main merge, clinical use or P5/P6 implementation.

- **P4-1 (this PR):** pure deterministic comparison of patient-scoped, admissible observations with the most recent prior eligible baseline. Explicit as_of_utc; no imputation, unit conversion, hidden excluded inputs, out-of-scope patient reads, or invented medical interpretation.
- **P4-2 (later):** strict versioned candidate demo policy; DR-001/003/005/006/008/009; exact nonclinical messages, evidence references, trust basis, stable ordering and dedupe; reject retired IDs. Pending explicit owner parameter approval.
- **P4-3 (later):** reversible review-item/evidence persistence, audit, safe read API and idempotency; resolve workflow_run reference currently assigned to P5 first. Never implement P5 prematurely.
- **P4-4 (later):** full A/B/C synthetic gold-fixture and negative acceptance matrix, cross-patient isolation, duplicate suppression, test_all.ps1/Windows owner run and independent review. P4 remains IN_REVIEW until separately approved.

## 2. This PR exact scope

| File | Change |
|---|---|
| backend/app/services/monitoring.py | **New.** Internal pure `compare_observation_history` over immutable ObservationSnapshot, shared admissibility predicate, deterministic ComparisonResult, patient-scope/duplicate-ID failure, excluded-data reasons, explicit clock and Decimal deltas; **not** an agent tool implementation |
| backend/tests/p4/test_p4_monitoring.py | **New.** Focused P4-1 tests for current/latest prior, lookback, missing baseline, rejected/unit/future/missing rows, trust provenance, deterministic order, 100-row cap, cross-patient refusal, invalid numeric values |
| docs/phase-reports/PHASE_4_REPORT.md | **New.** This staged scope and honest test/remaining-work record |
| docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md | **Existing documentation only.** Preserve the historical 837/443 P3 baseline and append an explicitly conditional 859/443 collection expectation after adding P4 tests; no P3 code or tests altered |

No new API endpoints, DB tables, policies/threshold activation, agent graph, LLM, task, notification, external communication, P3 OCR, or modifications to existing executable code or tests in this first PR. The P3 handoff has a documentation-only collection-count addendum.

**Important implementation boundary (P4-1 contract review):** This code operates on explicitly supplied immutable snapshots (up to 100 historical rows). The pure function is deliberately named `compare_observation_history` rather than claiming to implement the `compare_observations` **agent tool** from `TOOL_CONTRACTS.md` §3.5. That proposed tool accepts `current: list[ObservationView] ≤ 6` and `baseline_lookback_days ≤ 365`, and does not yet define a self-contained baseline-history source despite being designated pure. An authorized, patient-scoped history read/adapter and precise incomparable-current output are still required. **Do not expose this internal function to agents, call P4 complete, or silently rewrite the tool's signature.**

## 3. Verification — label evidence correctly

- **Executed locally in an isolated Python 3.13 workspace**: focused pytest on the new module, with temporary small *local parity stubs* of existing enums/UTC clock helpers (not committed): **21 passed in 0.10 s**, command equivalent to PYTHONPATH=<isolated test root> python -m pytest backend/tests/p4/test_p4_monitoring.py -q. This proves the newly authored comparison logic against matching interface shapes, **not** that the integrated repository suite has passed.
- **Executed locally**: Python compileall on the two new Python files, completed without error.
- **Not executed locally**: full existing private repository test suite; exact pinned Python 3.12 runtime, Ruff and Windows PowerShell (unavailable in the isolated authoring environment). **GitHub Actions is the authoritative integrated Python 3.12 and frontend regression check.** Extra hardening assertions were added inside existing tests, so the collected test count is expected to remain unchanged, subject to CI verification.
- **Observed GitHub Actions results at pre-fix head `5a9f5748d7dc202f21b5670e61be96a6bf0435da`:** [PR run 44464674678](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44464674678) and [push run 44464666580](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44464666580) returned **FAIL** even though backend pytest, Ruff, OpenAPI, Alembic smoke and frontend jobs passed; the actual blocker was repository scanner rejection of an inadvertently prohibited clinical claim phrase in this report. This correction changes the wording, not scanner policy. **New exact-head CI must complete SUCCESS before merge; no earlier failed run counts as approval.**
- **Not run**: Tesseract Windows, LLM, Playwright, new DB migrations and full P4 gold cases; not part of this pure slice. Prior P3 Windows evidence remains authoritative but does not prove new P4 functionality.

## 4. Safety, correctness and residual risks

- Mixed patient_id values fail with E_SCOPE_VIOLATION rather than partial output; missing IDs, duplicate evidence IDs and invalid trust/value/type fail closed with E_VALIDATION. Rejected/invalid-unit rows are excluded even if their raw values are nonnumeric; they do not block the evaluation of eligible rows.
- Rejected rows, invalid unit, missing timestamp and beyond+5min values have explicit skip reasons; they cannot displace a usable baseline.
- Both doctor_verified and self_reported_validated can be compared; trust_basis explicitly records self_reported/doctor_verified/mixed and never upgrades self-reported status.
- Baseline is the closest strictly earlier admissible row within the explicit lookback, never the oldest or a same-timestamp duplicate. Delta is exact signed Decimal, **not** an assessment, direction label or clinical trigger.
- No thresholds are hard-coded or inferred from clinical sources in this slice; each call must supply baseline_lookback_days. No database writes, task/notification, graph or LLM operations.
- Existing real Windows OCR GOLD-EX-11=FAIL / NOT PROVEN, source 1O5→105, exit 2 and residual false-attestation risk are **not repaired or retested by this PR**. No interpretation of OCR misreads as proof of medical reliability or verified OCR accuracy.
- **Remaining integration risks:** need tested projection from database Observation rows to snapshots, durable evidence/DR items, review/approval of arbitrary policy numbers, reconciliation of schema dependencies before migrations, gold-case replay and end-to-end security tests.

## 5. Owner review checklist and rollback

- Confirm the four-path diff contains only three new P4 files plus the dated documentation-only P3 handoff count note, no changes to P3 executable/tests/fixtures, and `main` remains unchanged.
- Confirm unit/timestamp/trust/scope and latest-prior semantics match the history-comparison requirements; explicitly **do not** claim compatibility with the agent tool §3.5 until its current-list/baseline-history interface is resolved and tested.
- Confirm Python 3.12 backend + Node 22 frontend CI SUCCESS on the exact PR head, then request independent review if necessary; failures remain OPEN, never described as PASS.
- Do not merge or mark P4 accepted by this slice. Owner decides whether to merge a green interim P4-1 PR; Issue #14 remains OPEN until full P4 owner acceptance.
- Rollback: close PR unmerged, or owner revert this isolated additive P4-1 commit later. No stored data or migrations are touched.

**NOT FOR CLINICAL USE — synthetic demonstration only.**

## 6. Contract-alignment review checkpoint (2026-11-19)

Independent follow-up review found an interface ambiguity in proposed `compare_observations`: six current values alone do not provide the most-recent historical baseline without a separate authorized history lookup. This PR therefore provides only an **internal comparison helper**, not a LangGraph tool. A separately reviewed P4 adapter and typed `not_admissible` response with `skip_reason` remain necessary. This hardening defers value validation until after admissibility and rejects duplicate evidence IDs; new exact-head CI must prove the change. No policy thresholds, real diagnoses, new P3 changes or P5 implementation are authorized. **P4=IN_REVIEW; NOT FOR CLINICAL USE.**


## 7. P4-1 post-merge verification and P4-2A candidate-rule subset (2026-11-19)

- Owner merged PR #15 into main at 0e8002acffcfbeebcb45b64d78aac6266679495d. Its Git tree matches reviewed PR HEAD 6c254457a62826656382945898ac790dacc4ffc7, and post-merge CI 44468389417 completed SUCCESS for Python 3.12 backend and Node 22 frontend: https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44468389417
- **P4-2A implementation slice (THIS NEW PR, not yet accepted):** new internal, offline, test-only candidate policy and deterministic evaluator for DR-001 (missing baseline), DR-003 (staleness with injected UTC clock), and DR-005 (absolute demo delta). Explicit candidate-p4-2a version, no official demo-policy-1.1.0 activation, explicit policy parameters (no automatic defaults), demo_only=true, neutral review messages and self-reported suffixes, SHA-256 evidence dedupe, strict evidence/scope comparison recomputation. It rejects unknown/retired/unimplemented IDs and fails closed when the explicit blocking-fact count is nonzero.
- **Verification limit:** blocking_fact_count is a test-only input, NOT a trustworthy live doctor-verification gate. Nothing here exposes an API route or tool, persists review items, consumes unverified facts, sends notifications, or grants any agent access. The service must independently read actual verification state and authorized patient scope before future exposure.
- **Remaining P4-2 rules NOT implemented:** DR-006 doctor-verified source conflicts; DR-008 creation-order/duplicate detection; DR-009 plausibility-band review. Unsupported IDs cause a policy error, not silent omission. All three need dedicated fixtures and tests before acceptance.
- **Open contract gaps:** TOOL_CONTRACTS.md §3.5 has only six current observations though REQ-MON-01 needs the most recent historical baseline; §3.7 lacks explicit observations/as-of/gate inputs. This candidate is NOT the agent tool. Future approved adapter/contract revision must resolve both without trusting caller-provided patient or gate state.
- **Policy governance:** all parameters in DEMO_REVIEW_RULES.md §9 remain arbitrary proposed synthetic values pending the owner OQ-R01 decision. Candidate tests pass values explicitly without activation. A live policy must be separately reviewed and versioned.
- **Tests:** isolated local prototype using lightweight interface stubs passed 26/26 parametrized cases, but that is NOT proof of the exact new GitHub head or integrated Python 3.12. Authoritative CI Ruff, full pytest, repository scan, migrations and OpenAPI must pass at new PR head. The historical P3 document has a dated 885/443 expected green-run count note, preserving the 837/443 P3-only and 859/443 P4-1 historical baselines. No P3 code, tests or fixtures modified.
- **Status:** P4 stays IN_REVIEW; P4-2A does not constitute complete P4-2, final P4 acceptance or P5 implementation. P3 GOLD-EX-11 stays FAIL / NOT PROVEN under its synthetic educational conditional-acceptance decision. NOT FOR CLINICAL USE.
