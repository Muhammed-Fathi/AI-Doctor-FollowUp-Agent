# Deterministic DEMO Review Rules and Verification Issues

| Field | Value |
|---|---|
| Document ID | `SAFE-RULES-001` |
| Version | `0.3.0-p0` (policy id `demo-policy-1.1.0`) |
| Status | **IN REVIEW — parameters are arbitrary demo values and require owner sign-off** |
| Phase | `P0` (design). Implementation P3 (issues) / P4 (rules); fixture replay P4/P7 |
| Related | `REQ-RULE-01/02/03`, `REQ-SEC-04`, `REQ-DATA-04`, `REQ-OPS-04`, ADR-0004 |
| Revision | 0.2.0 separates **pre-verification issues** from **post-verification review rules** (review finding `P0-R03`), pins an injected demo clock (`P0-R07`), and labels self-reported data (`P0-R05`) |

> **These are not clinical rules.** They are deterministic workflow prompts that say, in effect,
> "this value is not usable yet", "the data changed", "the data is incomplete", or "please confirm".
> They are labelled `DEMO_ONLY` in the UI, they never carry a diagnosis, risk level, or recommendation,
> and no value below is derived from a medical guideline or asserted to be medically meaningful.

---

## 1. Purpose and non-purpose

| This engine **does** | This engine **does not** |
|---|---|
| Evaluate a small, versioned, deterministic rule set over **admissible** data | Predict, score, or classify clinical risk |
| Emit items with a rule/issue ID, a reason code, and evidence references | Diagnose, triage, or recommend any action |
| Make missing/ambiguous/conflicting/unverified data visible to the doctor | Impute or repair data silently |
| Guarantee identical output for identical input, policy version and as-of clock | Use the LLM in any way |
| Distinguish *pre-verification blockers* from *post-verification review prompts* | Treat pending or rejected facts as verified |

**The doctor decides what matters.** A missing item is not reassurance; a present item is not a finding.

## 2. Why deterministic instead of model-generated

1. Repeatability: the same fixture and as-of clock always produce the same items (testable, demonstrable).
2. Auditability: every item maps to an ID, a policy version, and evidence.
3. Safety: a model cannot invent a threshold, upgrade its own priority, or hide a data-quality problem.
4. Defensibility: no clinical validity is claimed, so the rules must be transparently mechanical.

## 3. Two separate output types (resolves `P0-R03`)

The graph has a **hard gate** between extraction and everything downstream. Earlier revisions declared
"unverified fact" / "missing unit" / "ambiguous date" / "wrong patient" as review rules (`DR-002`,
`DR-004`, `DR-007`, `DR-010`), but those conditions occur *before* verification and their inputs are
`ExtractedFact` records that the rule tool is forbidden to read. That path was unreachable and is now
split explicitly:

| | **Verification issues** (`VI-*`) | **Demo review rules** (`DR-*`) |
|---|---|---|
| Produced by | `fact_verify_gate` (deterministic, orchestrator node) | `review_rules` node (`review_priority` agent) |
| Runs | **before** human verification | **after** all blocking facts are verified |
| Input | `ExtractedFact` (candidate), document metadata, existing observations | `VerifiedFact`, admissible `ObservationView`, `ComparisonResult` |
| Output type | `VerificationIssue` (blocking, no rule ID) | `ReviewFlag` (`DR-*`, carries `trust_basis`) |
| Trust | Never trusted: never enters the draft, rules, comparisons, or tasks | Derived only from verified evidence |
| Doctor action | verify / correct / reject the fact, then resume | acknowledge / dismiss (informational) |
| UI section | **"Verification required"** | **"DEMO review prompts — not clinical risk assessment"** |

Invariant: a `VerificationIssue` never becomes a `ReviewFlag`, and a pending/rejected fact never appears in
`VerifiedFact`. The gate halts the run (`needs_verification`) instead of continuing, so no downstream node
can observe unverified data.

### 3.1 Retired rule IDs

| Retired | Replaced by | Reason |
|---|---|---|
| `DR-002` | `VI-001` | Missing/unsupported unit is a pre-verification blocker |
| `DR-004` | `VI-002` | Unverified fact is a gate condition, not a post-hoc rule |
| `DR-007` | `VI-003` | Ambiguous date must be resolved before any use |
| `DR-010` | `VI-004` | Wrong-patient document must block intake, not be "reviewed" later |

These IDs are **not reused**. `DR-002/004/007/010` must not appear in future code or fixtures (a P4 lint
test asserts their absence outside this mapping table).

## 4. Verification issue catalogue (`VI-*`)

| ID | Name | Deterministic trigger | Reason code | Blocking |
|---|---|---|---|---|
| `VI-001` | Missing or unsupported unit | A candidate fact whose field is a measurement value has `unit = null`, or a unit outside the per-field document unit list (`EXTRACTION_PROVENANCE.md` §3) | `unit_missing_or_unsupported` | Yes |
| `VI-002` | Unverified fact present | Any **active** candidate fact for the run's documents has `verification_status != verified`. *Active* excludes only an original fact that was rejected because a successfully recorded doctor correction superseded it with valid `corrected_from_fact_id` lineage — it is retained for immutable provenance but is not an active candidate (owner decision D-14) | `fact_unverified` | Yes |
| `VI-003` | Ambiguous date | `report_date` has more than one plausible interpretation, or is absent | `date_ambiguous` | Yes |
| `VI-004` | Wrong-patient document | The document's patient reference does not match the run's patient scope | `wrong_patient_document` | Yes |
| `VI-005` | Unreadable value | Value token is unparseable/OCR-corrupted, or OCR confidence `< ocr_confidence_floor` | `value_unreadable` | Yes |
| `VI-006` | Source conflict at intake | A candidate document value conflicts with an existing admissible observation for the same type and compatible timestamp, beyond `conflict_tolerance` | `source_conflict_at_intake` | Yes |

`VerificationIssue` fields: `issue_id`, `issue_type`, `reason_code`, `blocking=true`, `message` (neutral,
≤240 chars), `document_id`, `fact_ids`, `evidence[]`, `created_at`. No `rule_id`, no severity, no advice.

**`VI-002` counting scope (owner decision D-14, P3).** `EXTRACTION_PROVENANCE.md` §6 requires a
corrected original to remain `rejected`, while this catalogue triggers `VI-002` on any fact that is
not `verified`. Read literally together those two rules make every corrected document carry a
permanent blocker that no doctor action can clear, so the trigger and the count range over the
**active** candidate set:

- **excluded** — an original fact rejected *specifically because* a recorded doctor correction
  superseded it, i.e. another fact of the same document carries `corrected_from_fact_id` pointing at
  it. Such a row is immutable provenance, not a candidate.
- **still counted** — plain rejected facts, pending facts, and every fact of a genuine
  multi-measurement document.

**`VI-002` on a terminal rejected document (R21 §4.4).** Because a plain rejection is still counted
(D-14), a document whose facts were rejected ends `failed` while `VI-002` remains **open**. That is
deliberate and is *not* a stale-issue bug: the open row is the immutable record that a doctor refused
a reading, and `sync_issues` re-derives it on every read, so resolving it would only re-open it.

The terminal signal is therefore `extraction_status='failed'` plus `failure_code`
(`all_facts_rejected`, `measurement_rejected` or `fact_rejected`), **not** the absence of open issues.
No issue row is deleted, re-typed or auto-resolved, and a recovery upload elsewhere does not resolve,
supersede or clear the source document's `VI-002`. Whether any downstream consumer may treat a
recovered document as closing the old blocker is a **deferred** governance decision (P4/P5 or later);
nothing in P3 performs or implies it.

The decision authorizes nothing else: no automatic verification, no removal of historical facts, no
weakening of source evidence, no change to the closed mapping (see `PHASE_3_REPORT.md` §V.3).

## 5. Post-verification review rule catalogue (`DR-*`)

Inputs are only `VerifiedFact`, admissible `ObservationView`, and `ComparisonResult`. Admissible means
`is_admissible_observation` (`TOOL_CONTRACTS.md` §3.4): `validation != rejected`, patient-scoped, unit matches
the measure, parseable `measured_at`. **`self_reported_validated` is admissible and stays labelled** — it is
carried into `trust_basis` and never promoted to `doctor_verified` (`P0-R11`).

| ID | Name | Deterministic trigger | Reason code | Hint | Blocking |
|---|---|---|---|---|---|
| `DR-001` | Missing baseline | No admissible prior value of the same type/unit within `baseline_lookback_days` of the current value | `missing_baseline` | `data_quality` | No |
| `DR-003` | Stale measurement | As of `as_of_utc`, the newest admissible value of a type is older than `stale_measurement_days` | `measurement_stale` | `data_quality` | No |
| `DR-005` | Change above demo parameter | `abs(current − baseline) > demo_delta_<type>`, same unit, `comparable=true`, baseline = **most recent prior** value | `change_exceeds_demo_parameter` | `change_to_review` | No |
| `DR-006` | Two doctor-verified sources disagree | Two `doctor_verified` facts/observations for the same type at compatible timestamps differ beyond `conflict_tolerance` | `verified_source_conflict` | `verification_needed` | No (post-gate) |
| `DR-008` | Duplicate or out-of-order entry | Same type/value/timestamp repeated, or a value recorded later but measured earlier than an existing admissible value | `duplicate_or_out_of_order` | `data_quality` | No |
| `DR-009` | Implausible value (data quality) | Value outside the intake plausibility band (`DATA_DICTIONARY.md` §3), e.g. `1200 mmHg` | `implausible_value` | `data_quality` | No |

Notes:

- `DR-001` fires once per measure type.
- `DR-003` compares `as_of_utc − measured_at`; see §7 for the injected clock.
- `DR-005` is an **absolute** difference only; no direction-based wording ("rising", "worsening") is permitted.
- `DR-005` uses the **most recent prior** value, per `REQ-MON-01`. It never compares against the oldest value.
- `DR-006` is distinct from `VI-006`: the intake conflict is about an *unverified* candidate vs existing data; `DR-006` is about two sources that a doctor has already verified.
- `DR-009` is a data-entry heuristic, explicitly not a normal/abnormal judgement.

Each `ReviewFlag` also carries `trust_basis ∈ {self_reported, doctor_verified, mixed}` so the doctor can see
whether the underlying values were self-reported by the patient or doctor-verified (`REQ-DATA-04`).

## 6. Message templates (neutral wording only)

### 6.1 Verification issues

| ID | Message (exact template) |
|---|---|
| `VI-001` | `A recorded value has no usable unit. Please confirm the unit.` |
| `VI-002` | `{count} extracted value(s) are not yet verified.` — `{count}` is the number of **active** candidate fact rows with `verification_status != verified` for the run's documents, computed at render time (never hard-coded; `GOLD-FIXTURES` Case C declares exactly 3). Superseded originals are excluded from the count only (owner decision D-14); plain rejected and pending facts are still counted |
| `VI-003` | `A date could not be read unambiguously.` |
| `VI-004` | `A document may not belong to this patient; please confirm.` |
| `VI-005` | `A value could not be read reliably and needs correction.` |
| `VI-006` | `A document value conflicts with an existing record for {measure_type}.` |

### 6.2 Review rules

| ID | Message (exact template) |
|---|---|
| `DR-001` | `No previous recorded {measure_type} to compare against.` |
| `DR-003` | `The most recent {measure_type} was recorded {days} days ago.` |
| `DR-005` | `{measure_type} differs from the previous recorded value by {delta} {unit}.` |
| `DR-006` | `Two verified sources disagree for {measure_type} at {timestamp}.` |
| `DR-008` | `A repeated or out-of-order entry was detected for {measure_type}.` |
| `DR-009` | `A recorded value is outside the demo plausibility range and may be a typo.` |

**Self-reported suffix rule (deterministic).** When `trust_basis = self_reported`, the message is rendered
with the suffix ` (self-reported)`. When `mixed`, the suffix is ` (includes self-reported values)`. When
`doctor_verified`, no suffix. Example: `Systolic BP differs from the previous recorded value by 12 mmHg (self-reported).`

Wording prohibitions (asserted by a P4 test): no "risk", "danger", "urgent", "abnormal", "normal",
"concerning", "high/low", "should", "recommend", "diagnosis", or directional trend language; and
self-reported values must never be described as "verified" or "confirmed by your doctor".

## 7. Injected demo clock (resolves `P0-R07`)

`DR-003` (and `DR-001`'s lookback window) depend on "now". Using a wall clock would silently change the
expected items on the defence date. Therefore:

| Rule | Behaviour |
|---|---|
| Demo mode (`DEMO_MODE=true`) | Evaluation uses `as_of_utc` from the policy file (`demo_as_of_utc`), stored on the run and shown in the UI/API |
| Tests and fixtures | Always pass an explicit `as_of_utc`; no test may call the wall clock |
| Non-demo/production-like path | Uses the real clock but records the exact instant used on the run record |

Policy default: `demo_as_of_utc: 2026-11-14T12:00:00Z`. Changing it requires a `policy_version` bump and
fixture updates. The value actually used is persisted (`workflow_run.as_of_utc`) and returned by the API, so
a reviewer can recompute every expectation. `DR-003`'s `{days}` is `floor(as_of_utc − measured_at)`.

## 8. Policy file (proposed shape)

```yaml
# data/synthetic/policy/demo_review_policy.yaml    (PROPOSAL — not created in P0)
policy_version: demo-policy-1.1.0
demo_only: true
demo_as_of_utc: 2026-11-14T12:00:00Z
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
verification_issues:
  - id: VI-001
    enabled: true
  # ... VI-002 … VI-006
rules:
  - id: DR-001
    enabled: true
  # ... DR-003, DR-005, DR-006, DR-008, DR-009
```

Rules for the file: reviewed like code; any rule/parameter/as-of change bumps `policy_version` and updates
gold fixtures; unknown IDs or missing parameters produce `E_RULE_POLICY_INVALID` and **no** items (fail closed);
disabled rules are recorded in the trace.

## 9. Parameters are arbitrary demo values

| Parameter | Value | Justification |
|---|---|---|
| `demo_delta_systolic_mmHg` | 10 | Chosen only so demo Case B reliably produces one deterministic item |
| `demo_delta_diastolic_mmHg` | 8 | Same |
| `demo_delta_heart_rate_bpm` | 15 | Same |
| `demo_delta_glucose_mgdl` | 40 | Same |
| `baseline_lookback_days` | 90 | Fits the synthetic timeline spacing |
| `stale_measurement_days` | 30 | Fits the demo narrative of a missed check-in |
| `ocr_confidence_floor` | 0.70 | Engine-reported confidence is noisy; this only decides "needs a human look" |
| `conflict_tolerance` | 0 | Exact equality required when comparing same-time sources |
| `max_items_per_type` | 3 | Keeps the queue readable in a demo |
| `demo_as_of_utc` | `2026-11-14T12:00:00Z` | Makes fixtures date-independent; not a clinical value |

**Explicit non-claims.** These numbers are *not* derived from any guideline, paper, device threshold, or
clinical consensus; they are not endorsed for any real use; they must not be described as "normal ranges" or
"clinical cut-offs" in the UI, docs, slides, or demo narration. Any real-world use would require clinician
ownership of the policy and formal validation, which this project does not perform.

## 10. Evaluation semantics

```text
gate   : extraction_facts[], documents            -> verification_issues[], verdict(run|halt)
rules  : verified_facts[], admissible observations, comparisons[], as_of_utc, policy
         -> review_flags[], sorted by (hint order, rule_id, evidence key)
```

1. **Purity.** No database writes inside evaluation; nodes persist results.
2. **Ordering.** Deterministic sort so screenshots and tests are stable
   (`verification_needed` > `data_quality` > `change_to_review`, then ID, then evidence key).
3. **Dedup.** `dedupe_key = sha256(patient_id | rule_id | sorted(evidence keys) | trust_basis)`; duplicates collapse.
4. **Idempotency.** Re-running with the same run, evidence set, policy version and as-of produces an identical
   item set; persisting twice is a no-op (unique index in `DATA_DICTIONARY.md` §2.9).
5. **Admissible-only.** Requests containing a rejected or pending fact fail with `E_UNVERIFIED_FACT`
   (`REQ-SEC-04`); rejected observations are excluded from comparisons (`REQ-DATA-04`).
6. **No side effects.** No tasks, approvals, notifications, or messages (`ADR-0005`).
7. **Fail closed.** Policy errors produce no items plus an error, never a default threshold.

## 11. Worked examples

### 11.1 Case B — changed measurements (corrected, resolves `P0-R01`)

| Item | Value |
|---|---|
| Series (systolic) | 138 mmHg (2026-10-02) → 146 mmHg (2026-10-20) → 158 mmHg (2026-11-03) |
| Baseline per `REQ-MON-01` | **most recent prior** = 146 mmHg (2026-10-20) |
| Delta | \|158 − 146\| = **12 mmHg** |
| Parameter | `demo_delta_systolic_mmHg = 10` |
| Output | One `DR-005`, hint `change_to_review`, `trust_basis=self_reported` (values come from patient check-ins), message `Systolic BP differs from the previous recorded value by 12 mmHg (self-reported).`, evidence = the two systolic observation IDs |
| Diastolic | 88 → 92 → 96: delta 4 ≤ 8 → **no** item |
| Heart rate | 76 → 80 → 84: delta 4 ≤ 15 → **no** item |
| Glucose | 98 mg/dL (2026-10-02, self-reported) → 104 mg/dL (2026-11-02, doctor-verified document): delta 6 ≤ 40 → **no** item; baseline exists → no `DR-001` |
| Staleness | newest values are 11–12 days old at `as_of_utc=2026-11-14T12:00:00Z` → no `DR-003` |

### 11.2 Case C — ambiguous OCR (corrected, resolves `P0-R02`)

| Stage | Expectation |
|---|---|
| Before correction | `VI-001` (unit), `VI-002` (`{count}` = 3 candidate facts, §4.2a of `GOLD_FIXTURES.md`), `VI-003` (date `03/11/2026`), `VI-005` (`1O5` unreadable) — all blocking; run halts `needs_verification`; **no** `DR-*` items exist yet |
| Correction | value `105`, unit `mg/dL`, date `2026-11-03` (after the 2026-10-10 baseline) |
| After resume | Baseline 96 mg/dL (2026-10-10) → 105 mg/dL (2026-11-03): delta 9 ≤ 40 → no `DR-005`; baseline exists → no `DR-001`; 11 days old → no `DR-003`; **zero** `DR-*` items |

### 11.3 Case A — stable

Seed (2026-10-01, 2026-10-15) + live check-in (2026-11-01): systolic 122 → 120 → 121 (delta 1), diastolic
78 → 79 → 78 (delta 1), HR 72 → 74 → 71 (delta 3); document hemoglobin is not an `Observation` type, so it
produces no comparison and no `DR-*` item. Expected: **zero** verification issues after verification, **zero**
`DR-*` items.

## 12. Test plan

| Test ID | Assertion | Phase |
|---|---|---|
| `RULE-01` | Every gold fixture yields exactly the expected `DR-*` ID set and order | P4 |
| `RULE-02` | Same input twice → identical output, no duplicate rows | P4 |
| `RULE-03` | Non-verified/rejected input → `E_UNVERIFIED_FACT`, zero items | P4 |
| `RULE-04` | All templates pass the prohibited-wording scan; self-reported suffix applied when required | P4 |
| `RULE-05` | Invalid policy (unknown ID, missing parameter, retired `DR-002/004/007/010`) → `E_RULE_POLICY_INVALID`, zero items | P4 |
| `RULE-06` | Unit mismatch → `comparable=false`, no `DR-005` | P4 |
| `RULE-07` | Static check: rule engine imports no task/approval/messaging module | P7 |
| `RULE-08` | Two runs with different `as_of_utc` produce different `DR-003` outcomes; same as-of is stable | P4 |
| `VI-01` | Each `VI-*` fires exactly for its fixture and lists the blocking fact IDs | P3 |
| `VI-02` | Gate halts with `needs_verification`; no `DR-*` evaluated, no draft persisted | P3/P5 |
| `VI-03` | `VI-004` (wrong patient) cannot be "verified away": correction path requires explicit re-attribution and audit | P3/P4 |

None of these are executed in P0.

## 13. Open questions for the owner

| ID | Question | Default |
|---|---|---|
| `OQ-R01` | Approve the parameters in §9 (or supply your own)? | Keep as listed |
| `OQ-R02` | Should `DR-005` also fire for reductions? | Yes — absolute difference, no direction claims |
| `OQ-R03` | Should dismissals require a reason? | Optional in the MVP |
| `OQ-R04` | Should the demo include a deliberately noisy rule to show suppression? | Covered by internal fixture `GOLD-D`; not shown in the three demo stories |
| `OQ-R05` | Is the ` (self-reported)` suffix acceptable in doctor-facing messages? | Yes — honesty over brevity |

## 14. P4-RB3 conservative durable persistence disclosure (2026-11-23)

Owner-ratified Design PR #42 (`0008_p4_rb3_review_persistence`, `backend/app/services/p4_rb3_review_persistence.py`) persists run-bound outputs of the unchanged RB2 six-rule evaluator under the following conservative boundaries:

- **DR-006 whole-invocation denial (`dr006_policy = "prohibited_denied"`):** All six rules (`DR-001`, `DR-003`, `DR-005`, `DR-006`, `DR-008`, `DR-009`) remain implemented in the RB2 evaluator, and `DR-006` persistence is **not authorized** in this slice. Whenever the evaluator emits `DR-006`, RB3 T12 denies the **entire** persistence invocation (`409 E_VALIDATION`, `dr006_persistence_not_authorized`) with zero DB writes — never a silently dropped item or partial run subset. A run with a verified-source conflict therefore persists no `review_item` rows in this conservative slice; `document_span` / `checkin_note` links remain deferred and blocked (`0..24` observation links only).
- **A2 transport label vs. stored-lineage proof (`lineage_label_policy = "a2_transport_label"`):** When RB3 translates F2/RB1-verified observations into RB2 `OfflineObservation` inputs, `self_reported_validated` is passed as `trust_level="self_reported"` and every item stores `provenance_status="fixture_asserted"` as the boundary transport label. Independent per-item verified-source lineage truth is persisted separately in `review_item.stored_lineage_proved` (`0` or `1`), derived strictly inside RB3's SQLite lock from stored document/fact/decision provenance.

