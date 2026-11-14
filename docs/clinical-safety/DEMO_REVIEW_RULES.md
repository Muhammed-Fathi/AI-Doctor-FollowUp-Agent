# Deterministic DEMO Review Rules

| Field | Value |
|---|---|
| Document ID | `SAFE-RULES-001` |
| Version | `0.1.0-p0` (policy id `demo-policy-1.0.0`) |
| Status | **IN REVIEW — parameters are arbitrary demo values and require owner sign-off** |
| Phase | `P0` (design). Implementation P4; fixture replay P4/P7 |
| Related | `REQ-RULE-01/02/03`, `REQ-SEC-04`, ADR-0004 |

> **These are not clinical rules.** They are deterministic workflow prompts that say, in effect,
> "the data changed / the data is incomplete / this value is unverified — please look".
> They are labelled `DEMO_ONLY` in the UI, they never carry a diagnosis, risk level, or recommendation,
> and no value below is derived from a medical guideline or asserted to be medically meaningful.

---

## 1. Purpose and non-purpose

| This engine **does** | This engine **does not** |
|---|---|
| Evaluate a small, versioned, deterministic rule set over **verified** facts and observations | Predict, score, or classify clinical risk |
| Emit review items with a rule ID, a reason code, and evidence references | Diagnose, triage, or recommend any action |
| Make missing/ambiguous/conflicting data visible to the doctor | Impute or repair data silently |
| Guarantee identical output for identical input and policy version | Use the LLM in any way |
| Order items by data-quality class for review convenience | Claim that a flagged change is clinically significant |

**The doctor decides what matters.** A missing review item is not reassurance; a present review item is not
a finding. This is stated in the UI header and in the demo script.

## 2. Why deterministic instead of model-generated

1. Repeatability: the same fixture always produces the same items (testable, demonstrable).
2. Auditability: every item maps to a rule ID, a policy version, and evidence.
3. Safety: a model cannot invent a threshold, upgrade its own priority, or hide a data-quality problem.
4. Defensibility: the project makes no clinical validity claim, so the rules must be transparently mechanical.

## 3. Policy file (proposed shape)

```yaml
# data/synthetic/policy/demo_review_policy.yaml    (PROPOSAL — not created in P0)
policy_version: demo-policy-1.0.0
demo_only: true
notice: "DEMO review prompts only — not clinical risk assessment. Not for clinical use."
parameters:
  baseline_lookback_days: 90
  stale_measurement_days: 30
  demo_delta_systolic_mmHg: 10
  demo_delta_diastolic_mmHg: 8
  demo_delta_heart_rate_bpm: 15
  demo_delta_glucose_mgdl: 40
  ocr_confidence_floor: 0.70
  conflict_tolerance: 0
  max_items_per_type: 3
rules:
  - id: DR-001
    enabled: true
    reason_code: missing_baseline
    workflow_hint: data_quality
  - id: DR-005
    enabled: true
    reason_code: change_exceeds_demo_parameter
    workflow_hint: change_to_review
  # ... one entry per rule in §4
```

Rules for the file:

- It is data, reviewed like code, and versioned by `policy_version`.
- Changing any parameter or rule **requires** a `policy_version` bump, updated gold fixtures, and a note in the phase report.
- An unknown rule ID, a missing parameter, or a malformed file is `E_RULE_POLICY_INVALID` — the engine fails closed (no items) rather than guessing.
- Disabled rules are recorded as disabled in the run trace.

## 4. Rule catalogue

Common terms: *current* = the observation/fact under review; *baseline* = the most recent **verified** prior value of the same type and unit within `baseline_lookback_days`; *evidence* = `ProvenanceRef` list.

| ID | Name | Deterministic trigger | Reason code | Hint | Blocking? |
|---|---|---|---|---|---|
| `DR-001` | Missing baseline | No verified prior value of the same type/unit within `baseline_lookback_days` | `missing_baseline` | `data_quality` | No |
| `DR-002` | Unit missing or not allowed | Verified fact has `unit = null` or a unit outside the allowlist | `unit_missing_or_unsupported` | `verification_needed` | Yes |
| `DR-003` | Stale measurement | `now - measured_at > stale_measurement_days` for the newest value of a type | `measurement_stale` | `data_quality` | No |
| `DR-004` | Unverified fact present | A fact exists with `verification_status != verified` for the patient/document in this run | `fact_unverified` | `verification_needed` | Yes |
| `DR-005` | Change above demo parameter | `abs(current - baseline) > demo_delta_<type>` with matching units and a comparable baseline | `change_exceeds_demo_parameter` | `change_to_review` | No |
| `DR-006` | Source conflict | Two verified sources for the same type and near-identical timestamp differ by more than `conflict_tolerance` | `source_conflict` | `verification_needed` | Yes |
| `DR-007` | Ambiguous date | A fact/observation has more than one plausible date interpretation or no date | `date_ambiguous` | `verification_needed` | Yes |
| `DR-008` | Duplicate or out-of-order entry | Same type/value/timestamp repeated, or `measured_at` earlier than an existing later entry that was recorded first | `duplicate_or_out_of_order` | `data_quality` | No |
| `DR-009` | Unsupported value range (data-quality) | Value outside the intake plausibility band in `DATA_DICTIONARY.md` §3 (e.g. `1200 mmHg`) | `implausible_value` | `data_quality` | No |
| `DR-010` | Patient-document mismatch | Document metadata/patient reference does not match the run's patient scope | `wrong_patient_risk` | `verification_needed` | Yes |

Notes per rule:

- `DR-001` fires **once per measure type**, not per observation.
- `DR-005` requires `comparable = true`; a unit mismatch produces `incomparable_reason` and never a delta.
- `DR-005` compares **absolute** difference only. No direction-based wording ("rising", "worsening") is permitted in the message.
- `DR-006` and `DR-010` are safety-relevant: they prevent silently wrong attribution.
- `DR-009` is a data-entry heuristic, explicitly not a normal/abnormal judgement.
- Blocking rules halt the graph at `fact_verify_gate` or prevent a pipeline stage; they never "auto-resolve".

## 5. Message templates (neutral wording only)

| Rule | Message (exact template) |
|---|---|
| `DR-001` | `No previous recorded {measure_type} to compare against.` |
| `DR-002` | `A recorded value has no usable unit. Please confirm the unit.` |
| `DR-003` | `The most recent {measure_type} was recorded {days} days ago.` |
| `DR-004` | `{count} extracted value(s) are not yet verified.` |
| `DR-005` | `{measure_type} differs from the previous recorded value by {delta} {unit}.` |
| `DR-006` | `Two sources disagree for {measure_type} at {timestamp}.` |
| `DR-007` | `A date could not be read unambiguously.` |
| `DR-008` | `A repeated or out-of-order entry was detected for {measure_type}.` |
| `DR-009` | `A recorded value is outside the demo plausibility range and may be a typo.` |
| `DR-010` | `A document may not belong to this patient; please confirm.` |

Wording prohibitions (enforced by a unit test at P4): no "risk", "danger", "urgent", "abnormal", "normal",
"concerning", "high/low", "should", "recommend", "diagnosis", or directional trend language.

## 6. Parameters are arbitrary demo values

| Parameter | Value | Justification |
|---|---|---|
| `demo_delta_systolic_mmHg` | 10 | Chosen only so demo Case B reliably produces one deterministic item with round numbers |
| `demo_delta_diastolic_mmHg` | 8 | Same |
| `demo_delta_heart_rate_bpm` | 15 | Same |
| `demo_delta_glucose_mgdl` | 40 | Same |
| `baseline_lookback_days` | 90 | Fits the synthetic timeline spacing |
| `stale_measurement_days` | 30 | Fits the demo narrative of a missed check-in |
| `ocr_confidence_floor` | 0.70 | Engine-reported confidence is noisy; this only decides "needs a human look" |
| `conflict_tolerance` | 0 | Exact equality required when comparing same-time sources |
| `max_items_per_type` | 3 | Keeps the queue readable in a demo |

**Explicit non-claims.** These numbers are *not* derived from any guideline, paper, device threshold, or
clinical consensus; they are not endorsed for any real use; they must not be described as "normal ranges" or
"clinical cut-offs" in the UI, docs, slides, or demo narration. Any real-world use would require clinician
ownership of the policy and formal validation, which this project does not perform.

The owner may replace all values with their own arbitrary demo values; the fixtures and expected rule IDs
must then be updated together (see `docs/evaluation/GOLD_FIXTURES.md`).

## 7. Evaluation semantics

```text
inputs : verified_facts[], comparisons[], observations[], policy(version, parameters)
output : review_items[], sorted by (workflow_hint order: verification_needed > data_quality > change_to_review,
                                    then rule_id, then evidence key)
```

1. **Purity.** No database writes inside evaluation; the node persists results.
2. **Ordering.** Deterministic sort so screenshots and tests are stable.
3. **Dedup.** `dedupe_key = sha256(patient_id | rule_id | sorted(evidence keys))`; duplicates collapse to one item (`REQ-RULE-03`).
4. **Idempotency.** Re-running for the same run and evidence set produces an identical item set; persisting twice is a no-op (unique index in `DATA_DICTIONARY.md` §2.9).
5. **Verified-only.** The engine rejects input containing non-verified facts with `E_UNVERIFIED_FACT` (`REQ-SEC-04`).
6. **No side effects.** The engine cannot create tasks, approvals, notifications, or messages (`ADR-0005`).
7. **Fail closed.** Policy errors produce no items plus an error, never a default threshold.

## 8. Worked example — demo Case B

| Item | Value |
|---|---|
| Prior verified systolic BP | 138 mmHg on 2026-10-02 |
| Current verified systolic BP | 152 mmHg on 2026-11-03 |
| Delta | 14 mmHg (absolute) |
| Parameter | `demo_delta_systolic_mmHg = 10` |
| Output | One `DR-005` item, hint `change_to_review`, message `Systolic BP differs from the previous recorded value by 14 mmHg.`, evidence = both observations |
| Also expected | `DR-005` for diastolic (88 → 94, delta 6 ≤ 8, so **no** item); no `DR-006`/`DR-007` (data is clean); no `DR-001` (baseline exists) |

What the doctor sees is a neutral difference and the two sources. What the doctor is **not** told is that
anything is wrong — that judgement, if any, is theirs.

## 9. Test plan for this policy

| Test ID | Assertion | Phase |
|---|---|---|
| `RULE-01` | Each gold fixture yields exactly the expected rule IDs in the expected order | P4 |
| `RULE-02` | Same input twice → identical output, no duplicate rows | P4 |
| `RULE-03` | Non-verified fact input → `E_UNVERIFIED_FACT`, no items | P4 |
| `RULE-04` | Message templates contain no prohibited words | P4 |
| `RULE-05` | Invalid policy (unknown rule/missing parameter) → `E_RULE_POLICY_INVALID`, no items | P4 |
| `RULE-06` | Unit mismatch → `comparable=false`, no `DR-005` | P4 |
| `RULE-07` | Rule engine has no import of task/approval/messaging modules | P7 |

**Not executed in P0.** No rule engine exists yet; these are requirements for P4.

## 10. Open questions for the owner

| ID | Question | Default |
|---|---|---|
| `OQ-R01` | Approve the parameter values in §6 (or supply your own)? | Keep as listed |
| `OQ-R02` | Should `DR-005` also fire for reductions, not just increases? | Yes, absolute difference (no direction claims) |
| `OQ-R03` | Should dismissals require a reason? | Optional in the MVP |
| `OQ-R04` | Should the demo include one intentionally "noisy" rule to show suppressibility? | Not in the MVP; keep the queue small |
