# P4-2a — Strict Candidate DEMO Policy Validation

**Status:** IN_REVIEW / NOT MERGED. **Base:** main at 0e8002acffcfbeebcb45b64d78aac6266679495d (merged P4-1 PR #15). **Tracking:** [Issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).

**EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**

## Implemented bounded scope

This PR creates a **pure, strict validator** for already-parsed untrusted demo-policy candidate dictionaries. It returns an immutable DemoPolicyCandidate or fails with DemoPolicyError / E_RULE_POLICY_INVALID. It DOES NOT create/activate a runtime YAML policy, perform rule evaluation, persist review items, read files/databases, or touch LangGraph/LLM, APIs, medical workflows, notifications, tasks or doctor decisions. Section 8/9 parameters of [DEMO_REVIEW_RULES.md](../clinical-safety/DEMO_REVIEW_RULES.md) are still **unapproved synthetic values** requiring an explicit owner decision.

| Path | Change |
|---|---|
| backend/app/services/demo_policy.py | New candidate schema validator, closed IDs, bounded parameters, canonical UTC clock |
| backend/tests/p4/test_p4_demo_policy.py | New 22 focused synthetic tests for valid candidate, unavailable fields, duplicate/retired IDs, bad parameter types/values, version, clock, notice, immutability |
| docs/phase-reports/P4_2A_POLICY_VALIDATION.md | This evidence and open decisions |
| docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md | Append-only downstream collection checkpoint, preserving historical P3 evidence |

No P3 code/tests/fixtures, scanner rules, runtime DB, front-end, or existing API was changed.

## Strict validator behavior

Top-level keys must be exactly policy_version, demo_only, demo_as_of_utc, notice, parameters, verification_issues, rules. Version must follow demo-policy-X.Y.Z. Demo-only must be true. Notice must equal the exact neutral synthetic disclaimer. Clock must be a canonical Z-suffixed UTC instant, not a wall-clock calculation.

The nine declared parameter names must all be present, typed and bounded. Non-finite numbers, booleans in place of integers, negatives, extra/missing keys fail closed. Engineering resource ceilings are not endorsed medical thresholds. The closed rule catalogue is DR-001/003/005/006/008/009, and verification issue catalogue VI-001..006. Missing, extra, retired or repeated IDs and non-boolean enabled switches are rejected. Disabled entries are preserved separately in a stable canonical order. The validator produces **no ReviewFlags** and has no partial-success fallback.

## Verification record and required CI

The authored candidate test file contains **22 tests**. Historical P3 reviewed figures are 837 backend / 443 P3; P4-1 collected 859 / 443; expected candidate collection after P4-2a is **881 / 443**, subject to official pytest collection and full workflow execution. **881 passed is NOT an observed result before CI succeeds.** The P3 handoff receives an append-only, clearly conditional P4-2a count note rather than having its prior evidence overwritten.

Before an interim owner merge, verify exact-head Python 3.12 Ruff lint/format, all backend tests, Alembic smoke, OpenAPI check, repository artefact/secret scan and frontend CI. A later independent review must inspect claims, pure side-effect boundary and policies. Local Windows/OCR runs and the full P4 gold rule matrix have not been executed by this work.

## Unresolved contract decisions — do not silently assume approval

1. **Comparison tool history dependency:** TOOL_CONTRACTS.md §3.4 allows read_observations to return up to 100 patient-scoped historical rows. Its §3.5 compare_observations tool takes only up to six current observations plus lookback and is pure; that is insufficient to select the most recent historical prior baseline required by MVP_SPEC REQ-MON-01. **Proposed, not yet approved:** preserve the P4-1 internal history helper; create a later, explicitly typed adapter receiving scope-checked history, current inputs, UTC clock, and evidence IDs, while emitting per-current not_admissible and skip_reason states. Do not expose P4-1 as the P5 agent tool yet.
2. **Synthetic policy activation:** The suggested demo-policy-1.1.0 numbers (lookback 90d, stale 30d, arbitrary demo deltas 10/8/15/40, OCR 0.70, tolerance 0, cap 3, clock 2026-11-14) remain candidate values. This validator does not install, endorse, or activate them. Rule evaluation must wait for owner signoff and an explicitly versioned policy artifact.
3. **Later rule implementation:** P4-2b needs all six DR evaluators, exact neutral templates, evidence and ordering/dedup checks, verification gate, A/B/C tests. DR-006 requires independent doctor-confirmed source provenance; DR-008 requires recorded-at lineage not present in the current P4-1 snapshot. Those cannot be fabricated.
4. **P4-3 schema dependency:** review_item.workflow_run_id references workflow_run currently scoped to P5; resolve it before any additive migration. No premature LangGraph, LLM or external actions.

**P3 OCR limitation is untouched:** GOLD-EX-11 = FAIL / NOT PROVEN, real 1O5 → 105, original exit 2. This P4-2a PR must never be described as solving it.

## Decision boundary

If CI and review pass, the owner may merge the bounded policy-validation increment. That is **not** acceptance of P4 or approval of policy thresholds, an AI agent graph, clinical use, or phase advancement. **No agent merge. NOT FOR CLINICAL USE.**
