# P4-2d — Offline DR-006 / DR-008 synthetic candidates

**Status:** IMPLEMENTATION PROPOSAL / IN_REVIEW — NOT MERGED OR ACTIVATED.
**Tracking:** [P4 Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).
**Base:** owner-merged [PR #19](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/19), main `85ccf8202667af0326868e954c4e530c0dc3217f`. Postmerge GitHub Actions run `44485844421` completed SUCCESS.
**Scope:** local fictitious academic data ONLY; NOT FOR CLINICAL USE. P3 GOLD-EX-11 real OCR failure stays FAIL / NOT PROVEN.

## Implemented as offline-only proof
- New `provenance_review_candidate.py` module, no imports in app routers, DB, live policy validator or agents. Standalone version namespace `candidate-p4-2d-0.1.0` and explicit test-only tolerance; never activates `demo-policy-1.1.0` or chooses its numeric `conflict_tolerance`.
- `DR-006` candidate: two eligible observations, same measure, unit and exact UTC measurement instant, different values exceeding the **explicit fixture** tolerance, each *claimed* to originate from a verified fact from a different document. A fact and its mapped observation are **one source**. Actual database source authentication is deliberately NOT provided. This is a shape-checked proof, NOT independent evidence of doctor verification.
- `DR-008` candidate: exact duplicate only for two distinct observation IDs with the same measure/unit/value and measurement instant, excluding same-source-fact replay; out-of-order requires strictly later `created_at` and strictly earlier `measured_at`. Missing/equal creation time does not imply a later record, and the evidence exclusion is explicit.
- Reuses the already-merged monitoring admissibility projection (patient scope, rejected/wrong unit/missing/future timestamps) before any matching; stable evidence IDs, SHA-256 dedupe, neutral messages, explicit provenance labels, per-type cap failures and a supplied UTC clock.
- `CandidateProvenancePolicy` and `blocking_fact_count` are **test inputs**, not approved policy or a true server-side verification gate. No database read proves source claims here; those claims must be loaded and checked from the real application DB in a later separately approved P4 adapter.

## Exact paths
1. `backend/app/services/provenance_review_candidate.py` — new pure offline candidate evaluator.
2. `backend/tests/p4/test_p4_provenance_review_candidate.py` — new deterministic/negative regression tests.
3. `docs/phase-reports/P4_2D_DR006_DR008_OFFLINE_CANDIDATES.md` — this implementation/safety report.

## Required review and test evidence
GitHub Actions Python 3.12 Ruff lint/format, pytest, OpenAPI, Alembic smoke, secret scan and Node 22 frontend checks must pass on the exact new PR head before any owner-reviewed merge. A successful parent `main` run is NOT proof of new tests. Local Windows PowerShell/Playwright/OCR/LLM tests are **NOT RUN** here. Record measured counts only after CI; do not rewrite P3 test history.

## Open integration and governance gates
1. Source lineage is only fixture-provided; need **server-authorized** patient scope, persisted `created_at`, fact-to-document lineage and verified-fact state from app DB, plus existing `VI-002` gate (including R21 corrected-fact lineage).
2. `TOOL_CONTRACTS.md` `3.5/`3.7 interface differences are unresolved. This is **not** the `evaluate_demo_review_rules` agent tool, and no tool contract has been silently changed.
3. Separate `DemoPolicyCandidate` structural validator and this new `CandidateProvenancePolicy` are not yet reconciled; OQ-R01 arbitrary synthetic policy parameters still require **explicit owner decision** before activation.
4. P4-3 review-item/evidence persistence depends on the deferred `workflow_run` FK decision; no P5 modules or artificial run IDs created here.
5. Full `GOLD-A/B/C/D` integration, cross-patient API tests, Windows acceptance and separate owner P4 sign-off remain future requirements.

**Do not deploy/activate, self-approve, or merge automatically.** This code has no browser/task/notification/LLM action, no clinical interpretation, no real patient data. Owner reviews all changes and chooses merge after successful exact-head CI.
