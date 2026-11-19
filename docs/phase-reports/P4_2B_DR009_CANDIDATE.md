# P4-2b — Offline DR-009 entry-quality candidate

**Status:** DRAFT / IN_REVIEW, not phase acceptance. Tracking: [Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).
**Base:** main 154300096b33f2a03b4b0e74811eaf9ce40be30e after owner-merged PR #17, postmerge CI 44475754026 SUCCESS.
**Boundary:** academic synthetic only, NOT FOR CLINICAL USE.

## Implemented
The isolated P4 candidate evaluator now optionally recognizes DR-009 using the existing MEASURE_PLAUSIBLE_BANDS in backend/app/core/enums.py. Those bands are arbitrary typo/unit-confusion checks, not medical cutoffs. A strictly out-of-band *admissible* record produces an informational data-quality prompt with reason_code=implausible_value, workflow_hint=data_quality, observation-ID evidence and a deterministic hash. The record's source label remains self_reported or doctor_verified and the matching message suffix stays intact. Rejected, unit-mismatched and invalid-time rows are excluded using the already-reviewed monitoring comparator before rule evaluation. Both current and prior admissible records are checked, inclusive band endpoints never fire and multiple flags obey the prior max-items-per-type fail-closed behavior.

The candidate DR-009 rule must be explicitly enabled under version candidate-p4-2a-0.2.0 or later, an offline version bump. Previous DR-001/003/005 behavior remains unchanged. Unknown, retired, or still unimplemented IDs continue to fail closed.

**NOT included:** DR-006, DR-008, database or agent tool adapter, real verification gate, policy activation, evidence persistence, run APIs, LangGraph/LLM, task, notification, or messaging. The separate P4-2a DEMO policy validator remains unconnected. P3 GOLD-EX-11 technical FAIL/NOT PROVEN remains unchanged.

## Exact proposed changed paths
- backend/app/services/demo_rules_candidate.py — opt-in offline DR-009 proof.
- backend/tests/p4/test_p4_demo_rules_candidate.py — fixture candidate-version bump only.
- backend/tests/p4/test_p4_dr009_candidate.py — 19 collected synthetic cases (18 test functions; two timestamp parameter variants).
- docs/phase-reports/P4_2B_DR009_CANDIDATE.md — this stage evidence.
- docs/phase-reports/PHASE_4_REPORT.md — append-only P4 stage entry.
- docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md — append-only conditional collection-count note, preserving historical acceptance.

## Test status and next gates
At initial authorship the first 16 new tests had not yet run in authoritative CI (historical checkpoint). The initial branch head subsequently passed CI. Independent review then requested explicit excluded-timestamp coverage and an oversized candidate-version fail-closed regression; this revision adds 3 collected cases, for 19 new cases total. The prior merged P4-2a baseline collected 909 backend tests, P3 subset 443. This revision's provisional backend count is **928 (909 + 19)**, subject to exact-head CI; this is **not** a claim of 928 passing. The candidate version pattern now bounds ASCII numeric components to 20 digits before int conversion, returning E_RULE_POLICY_INVALID on oversized strings. Missing and >5-minute future timestamps are tested alongside a clean record; no DR-009 flag is emitted and exclusions retain their explicit reasons. Review and record exact-head Python 3.12 Ruff lint/format, pytest, migrations smoke, OpenAPI, repository scan and Node 22 frontend outcome before any owner-controlled merge. If the collection differs, correct only the downstream P4 note, not historical P3 tests or controls.

## Deferred owner and engineering decisions
- DR-006 verified-source timestamp compatibility and DR-008 recorded-at chronology are not sufficiently specified for a live-safe evaluator; require separate signed semantics and fixtures.
- TOOL_CONTRACTS 3.5 still needs explicit server-scoped historical baseline input, and 3.7 needs verified-fact/observation/as-of boundary. Do not expose candidate evaluation as an agent tool.
- DEMO_REVIEW_RULES section 9 arbitrary policy values remain in review; a passed offline PR does not activate them.
- P4-3 durable review_item linkage to P5 workflow_run remains an architecture dependency, not solved here.

No agent self-approval or merge. Phase P4 remains IN_REVIEW. Synthetic educational scope only.
