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
| backend/app/services/monitoring.py | **New.** Immutable ObservationSnapshot, admissibility check, deterministic ComparisonResult, patient-scope failure, excluded-data reason codes, explicit fixed-time input and Decimal deltas |
| backend/tests/p4/test_p4_monitoring.py | **New.** Focused P4-1 tests for current/latest prior, lookback, missing baseline, rejected/unit/future/missing rows, trust provenance, deterministic order, 100-row cap, cross-patient refusal, invalid numeric values |
| docs/phase-reports/PHASE_4_REPORT.md | **New.** This staged scope and honest test/remaining-work record |

No new API endpoints, DB tables, policies/threshold activation, agent graph, LLM, task, notification, external communication, P3 OCR, or existing code changes in this first PR.

**Important implementation boundary:** The functions operate on explicitly supplied immutable snapshots. A future P4 change must provide authorized patient-scoped DB adapters; do not claim that standalone pure logic already constitutes an end-to-end P4 service.

## 3. Verification — label evidence correctly

- **Executed locally in an isolated Python 3.13 workspace**: focused pytest on the new module, with temporary small *local parity stubs* of existing enums/UTC clock helpers (not committed): **21 passed in 0.10 s**, command equivalent to PYTHONPATH=<isolated test root> python -m pytest backend/tests/p4/test_p4_monitoring.py -q. This proves the newly authored comparison logic against matching interface shapes, **not** that the integrated repository suite has passed.
- **Executed locally**: Python compileall on the two new Python files, completed without error.
- **Not executed locally**: full existing private repository test suite; exact pinned Python 3.12 runtime, Ruff and Windows PowerShell (unavailable in the isolated authoring environment). **GitHub Actions must be used for authoritative integrated Python 3.12 and frontend regression checks on this new PR head.** Capture actual CI run URL, exit/outcome and any failures before owner review.
- **Not run**: Tesseract Windows, LLM, Playwright, new DB migrations and full P4 gold cases; not part of this pure slice. Prior P3 Windows evidence remains authoritative but does not prove new P4 functionality.

## 4. Safety, correctness and residual risks

- Mixed patient_id values fail with E_SCOPE_VIOLATION rather than partial output; invalid trust/value/type fails closed with E_VALIDATION.
- Rejected rows, invalid unit, missing timestamp and beyond+5min values have explicit skip reasons; they cannot displace a usable baseline.
- Both doctor_verified and self_reported_validated can be compared; trust_basis explicitly records self_reported/doctor_verified/mixed and never upgrades self-reported status.
- Baseline is the closest strictly earlier admissible row within the explicit lookback, never the oldest or a same-timestamp duplicate. Delta is exact signed Decimal, **not** an assessment, direction label or clinical trigger.
- No thresholds are hard-coded or inferred from clinical sources in this slice; each call must supply baseline_lookback_days. No database writes, task/notification, graph or LLM operations.
- Existing real Windows OCR GOLD-EX-11=FAIL / NOT PROVEN, source 1O5→105, exit 2 and residual false-attestation risk are **not repaired or retested by this PR**. No interpretation of OCR misreads as clinically validated.
- **Remaining integration risks:** need tested projection from database Observation rows to snapshots, durable evidence/DR items, review/approval of arbitrary policy numbers, reconciliation of schema dependencies before migrations, gold-case replay and end-to-end security tests.

## 5. Owner review checklist and rollback

- Confirm this is limited to these three new P4 paths; no preexisting P3 artifact changed and main remains unchanged.
- Confirm unit/timestamp/trust/scope and latest-prior semantics match the approved contract, including data-quality-only wording.
- Confirm Python 3.12 backend + Node 22 frontend CI SUCCESS on the exact PR head, then request independent review if necessary; failures remain OPEN, never described as PASS.
- Do not merge or mark P4 accepted by this slice. Owner decides whether to merge a green interim P4-1 PR; Issue #14 remains OPEN until full P4 owner acceptance.
- Rollback: close PR unmerged, or owner revert this isolated additive P4-1 commit later. No stored data or migrations are touched.

**NOT FOR CLINICAL USE — synthetic demonstration only.**
