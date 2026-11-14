# ADR-0004 — Evidence-verified facts and a deterministic review queue (no risk prediction)

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Related | `REQ-VERIFY-01/02/03`, `REQ-RULE-01/02/03`, `REQ-SEC-04`, `REQ-LLM-02` |

## Context

The originally proposed "Risk Agent" implies clinical risk scoring, which this project cannot support: it has synthetic data, no validated model, no clinician oversight of an algorithm, and no regulatory basis. At the same time, the doctor needs help noticing *things that changed or need attention*, and the project needs a defensible "agentic" decision point that is not an LLM guess.

## Decision

1. **Facts are evidence-verified before use.** Every extracted value carries a document/page/span (or observation ID), raw text, quality flag and `verification_status`. Only `verified` facts may enter comparisons, rule evaluation, drafting, or tasks.
2. **Review items come from a deterministic rule engine**, not from the LLM and not from a clinical risk score. Rules are versioned, declared in a policy file, labelled `DEMO_ONLY`, and emit rule ID + reason code + evidence references.
3. The reviewing component is named `review_priority` but defines priority as **workflow ordering** (e.g. data-quality items first) — never clinical severity.
4. The LLM may only phrase a draft over verified evidence; it cannot create, remove, downgrade, or upgrade a review item.
5. Numeric parameters in the demo policy are arbitrary, configurable demo values. They are not derived from guidelines and must never be described as clinical thresholds.

Rule catalogue and wording: `docs/clinical-safety/DEMO_REVIEW_RULES.md`.

## Consequences

Positive:
- A reviewer can audit exactly why an item appeared (rule + evidence), and can change the policy in one file.
- No claim of clinical validity is needed or made; the system's contribution is workflow + evidence traceability.
- LLM failure cannot change what the doctor is asked to look at.

Negative / accepted costs:
- Less impressive-sounding than "AI risk prediction" — accepted deliberately; the project's honesty is a defense strength.
- Deterministic rules can produce false positives; they are a *prompt to look*, not an assertion about the patient.
- Requires fixture-based regression tests to keep rule behaviour stable (`REQ-EVAL-01`).

## Alternatives rejected

| Alternative | Reason |
|---|---|
| LLM-generated alerts or priorities | Unverifiable, non-deterministic, clinically unsupportable |
| Named clinical risk score (e.g. NEWS2/ASCVD) | Would be a medical claim requiring validation we cannot perform |
| No review queue at all | Loses the human-in-the-loop demonstration the project must show |
| Hard-coded single threshold in code | Unreviewable; policy must be visible and versioned |

## Verification (P0, docs-only)

- Rule catalogue, parameters, dedupe keys and prohibitions are specified in `docs/clinical-safety/DEMO_REVIEW_RULES.md`, and evaluated in `docs/evaluation/GOLD_FIXTURES.md`.
- `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §3 forbids `review_priority` from reading unverified facts.
- **Not executed:** no rule engine, no fixture replay, no false-positive measurement. Scheduled P4, measurement P7.

## Review notes for owner

Confirm the "review queue, not risk score" framing is acceptable for the defense narrative, and approve the arbitrary demo parameter values (or supply your own).
