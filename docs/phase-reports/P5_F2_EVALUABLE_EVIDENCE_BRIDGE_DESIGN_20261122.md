# P5-F2 — server-owned EvaluableReviewEvidenceV2 and deterministic P4 bridge: bounded design for owner ratification

**Status: DESIGN PROPOSAL ONLY / NOT CODE / NOT OWNER RATIFIED.** Authored 2026-11-22 from `main@3b236bfb29e7235b09b433ff92e271dc0900a2c5` (owner-merged [P5-F1 PR #33](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33)); exact-main [postmerge GitHub CI #44959531076](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44959531076) **COMPLETED / SUCCESS** for Backend Python 3.12 and Frontend Node 22. F1's final PR head `1f95d4db473e83a122304916df5c12304801e711` had both exact-head GitHub checks SUCCESS and independently supplied owner Windows `test_all.ps1` **12 PASS / 0 FAIL / 1 optional Playwright SKIP**, at matching tested SHA; see [PR #33 owner Windows receipt](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33#issuecomment-7070509224). None of this is F2 testing or authority to execute post-verification DR rules.

**Governing authority:** [CH-01](P4_P5_CONDITIONAL_HANDOFF_20261121.md) sequences F0 → F1 → a separately reviewed F2 → P4 run-bound integration. Owner approved only exact previous scopes and [PR #33 legacy 0007 compatibility exception](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33#issuecomment-7070068019). F2 requires a fresh, explicit design scope ratification in this PR Conversation; do not infer it from a successful F1 merge. `AGENTS.md` §§1–5/8–9 (phase, paths, no agent merge/self-approval), `TOOL_CONTRACTS.md` §§3.4–3.7 and `STATE_AND_GRAPH_CONTRACT.md` apply without waivers.

**Safety:** local synthetic academic program, **NOT FOR CLINICAL USE**. P4 remains `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN; P5 as a whole not accepted. P3 real OCR `GOLD-EX-11` original source `1O5` incorrectly parsed as `105`: **FAIL / NOT PROVEN**, never waived. Matching a file SHA to stored bytes and a doctor's audit row does **not** independently verify the original glyph.

---

## 1. What exists, what is absent

- **P5-F0** `backend/app/services/p5_run_foundation.py` creates server-owned `workflow_run` and immutable doctor-selected document/observation/omission manifest, sets `queued`, **not** `runtime_evaluable`; observations are allowed to be empty, but at least one document is required because R21 rejects `empty_selected_source_set`.
- **P5-F1** `backend/app/services/p5_run_gate.py` independently authorizes an active stored doctor session and assigned synthetic patient, inspects current persisted F0 selected evidence and actual bytes against stored source SHA, and records immutable `run_gate_evaluation` / `run_gate_blocker`. F1 decision `proceed` can be stale after later DB/filesystem changes; F1 receipt still `runtime_evaluable=False`. Its idempotency is a **run+source snapshot+gate version**, not generic forever approval. Its SQLite `BEGIN IMMEDIATE` transaction cannot atomically lock files.
- **P4** `backend/app/services/p4_evidence_inspection.py` returns `SelectedEvidenceInspection`, deliberately `run_gate_status=unavailable`, `run_gate_completed=False`, `runtime_evaluable=False`, `policy_status=unapproved`; its caller-supplied explicit selections and as-of clock are **not** an F0-backed authorization. `backend/app/services/p4_explicit_history.py` compares explicitly selected current ≤6 with historical ≤100, oldest? No: latest previous by (measured_at, ID), with lookback 0..365 days, and emits missing baseline honestly. `backend/app/services/p4_readonly_provenance.py` validates persisted fact/doctor lineage but does not attest original OCR glyphs.
- `TOOL_CONTRACTS.md` §3.5 presents a proposed `compare_observations(current,baseline_lookback_days)`, §3.7 a pure versioned `evaluate_demo_review_rules(verified_facts, comparisons, policy_version)`; neither currently accepts an authenticated F1/F0 run-bound V2 envelope. The proposed graph contract has `ObservationView`, `ComparisonResult`, `VerifiedFact`, `ProvenanceRef`, and `ReviewFlag` as **proposed** typed shapes, not all runtime classes.

**Gap:** a deterministic, provenance-backed, versioned, bounded *read-only* adapter from F0/F1 to P4-compatible types, with no caller-created `blocking_fact_count=0` / `proceed` / `doctor_verified` or unverified facts.

## 2. Proposed decisions (must ALL be ratified before code)

### D-F2-01 — sealed, server-derived V2 envelope, not a permission to execute graph/DR

Recommend a **strict immutable** (`frozen` dataclass or Pydantic v2 `extra=forbid`) internal-only `EvaluableReviewEvidenceV2` built *exclusively* from persisted `run_id` via a server-authenticated Principal. Suggested internal entry point:

`build_run_evaluable_review_evidence(db, *, principal, run_id: str, validation_clock: datetime, upload_root: str) -> EvaluableReviewEvidenceV2`

No caller parameters `patient_id`, document/observation IDs, `blocking_fact_count`, `gate_status`, `policy_version` override, history/current IDs, or `already_verified`. No HTTP endpoint, graph execution token or generic deserializer accepting a client-supplied envelope. Every result includes:
- stable `contract_version="2.0.0"`, `run_id`, `patient_id`, `doctor_id`, `as_of_utc` **copied from the run**, `workflow_version`, `state_schema_version`, `mapping_version`, `policy_version`;
- `gate_evaluation_id`, `gate_version`, `gate_input_fingerprint_sha256`, new `bridge_input_fingerprint_sha256` and fixed ordering of source IDs; each identifier resolves to one current scoped DB record;
- bounded typed `verified_facts` (≤40, active and valid doctor decisions only; no raw untrusted OCR text promoted), typed `selected_observations` (≤20 with unchanged `trust_level`), selected/excluded document provenance, optional typed `comparisons` (current ≤6, history ≤100) and explicit `exclusions` /`incomparables` with reason codes;
- `bridge_validated=True` means **F2 evidence-contract checks passed in this bounded invocation only**. `runtime_evaluable=False`, `policy_status="unapproved"`, `rules_executed=False` remain fixed: F2 **does not authorize a DR rule execution, LangGraph N2, P4 review persistence or any user-facing claim**. The name `EvaluableReviewEvidenceV2` identifies a typed *future P4 input*, not an agent-ready permission.

If any authoritative input violates a bound, closed vocabulary, doctor scope, provenance lineage or freshness, **fail closed with a typed error and no V2 envelope**. Do not emit an empty "clean" envelope or silently drop selected bad evidence.

### D-F2-02 — fresh F1 decision and same-snapshot revalidation, never a cached PROCEED

The bridge must re-authenticate the **stored** unrevoked time-valid doctor session and assigned synthetic patient at the injected `validation_clock`, require existing F0 run `status=queued`, require **current** F1 `decision=proceed` with no blockers, no error and expected version, and reproduce **the current authoritative F1 fingerprint** (including changed raw/provenance fields, verified decisions, selected/omitted rows, patient observations, versioned OCR/conflict parameters and file SHA/path data).

**A stored F1 receipt alone is never sufficient.** Recompute in a consistent SQLite snapshot under an explicit lock / isolation guarantee; validate actual selected file bytes and metadata, including a second file byte/hash check as close as feasible to completion. Locking SQLite does not lock files: record this non-atomic boundary and make a future consumer **recheck** before any later execution. A generic `read receipt row and trust its decision` implementation is forbidden.

**Design constraint:** F1's current exported `evaluate_run_verification_gate` is **mutating** (inserts an immutable evaluation/audit when source state changes). F2 must **not call this function as if it were pure**. A later F2 code PR may either (a) factor a reviewed read-only, snapshot-equivalent evaluator from F1, then compare the result to an existing persisted F1 PROCEED under one consistent DB transaction, or (b) introduce a documented equivalent exact read-only algorithm with explicit equivalence tests. Whichever chosen, no F2 success if there is no *matching, current, immutable* F1 PROCEED. No new F1 decision rows, audit pretending that F1 ran or P3 VI mutation on the bridge's read-only path. Test concurrent writers, altered files, blocker injection, changed F1 policy settings and stale replay.

### D-F2-03 — exact observation trust + comparison selection; no implicit upgrades

Run-selected current observation IDs must come from **F0's immutable selected observation manifest**. F0 allows 0..20 selected IDs; do **not** turn 0 into an invented current reading or implicitly select the most recent patient reading. Recommend **0 selected** → empty comparisons, preserved verified document facts, typed `no_current_selected` reason (not "normal"). For >6 eligible selected current IDs, recommend fail closed as `current_selection_over_cap` rather than silently picking the first six; document the contrast with F0's upper bound of 20.

The historical baseline *may* be server-derived from the same synthetic patient, but ONLY after separate owner choice between these alternatives:
- **Recommended:** allow a bounded, read-only, deterministic same-patient history (≤100) with **explicitly versioned** fixed lookback `0..365` days and exact ordering/tie-break; exclude invalid or future historical rows with typed reasons, never auto-convert units or impute a baseline. No user-supplied baseline IDs.
- **Alternative:** F0-selected-only readings serve as the complete comparison universe, and any absent earlier reading yields `missing_baseline`. Smaller reach but no additional historical read.

Either choice must preserve `self_reported_validated` as `self_reported`, `doctor_verified` only when the actual persisted source fact/doctor/correction lineage matches, and `mixed` for mixed-trust comparison. `validation='rejected'` is **not** an unverified fact; failures for a selected row stop the whole V2 projection and historical exclusions are explicit. Maintain **one measurement tuple per document**, closed `map-1.0.0` alias + exact unit mapping, and document-only unmatched verified facts (no converted Observation).

### D-F2-04 — reconcile TOOL_CONTRACTS §§3.5/3.7 without activating policy

Propose **additive, versioned, internal adapter contracts** (no rewrite to falsely claim prior tools implemented):
- `compare_run_observations_v2(evidence: EvaluableReviewEvidenceV2)` accepts only the sealed server-produced envelope; it returns deterministic ordered P4 comparison *inputs/results* with required comparable, delta, trust_basis and typed no-baseline/inadmissible reasons. Delegate only to existing reviewed pure P4 comparison logic when its expectations match exactly. No threshold/risk/clinical judgement.
- `prepare_run_review_inputs_v2(evidence: EvaluableReviewEvidenceV2)` shapes bounded `VerifiedFact`, admissible labelled `ObservationView`, `ComparisonResult` and provenance references for a **future**, separately authorized pure rule executor. It is not `evaluate_demo_review_rules` and emits **no `ReviewFlag` / DR-`*`**. `policy_version` stays the persisted run policy and cannot be swapped by caller.
- Preserve `TOOL_CONTRACTS.md` §3.4 observation admissibility and §3.7's statement that `E_UNVERIFIED_FACT` applies only to extracted facts, not observations. Explicitly document any `missing_baseline` vs `no_baseline` vocabulary reconciliation; never silently change a tested output.

**Deferred to a separately approved P4 integration PR:** actual `evaluate_demo_review_rules` execution, enabled/disabled DR policy promotion, `review_item` and `evidence_link` tables, graph transitions, tasks and notifications. F2 evidence production must not set the existing F0/P4 "unavailable" receipt flags to imply those parts ran.

## 3. Proposed F2 code allowlist — not permission now

After owner ratification, merging this design-only PR and obtaining **SUCCESS on exact merged-main SHA**, propose one *separate* P5-F2 code branch / PR with only the following **exact proposed paths**:

1. `backend/app/services/p5_evidence_bridge.py` (new — internal server-owned F2 recheck and read-only projection).
2. `backend/app/schemas/p5_review_evidence.py` (new — strict immutable typed V2 envelope and reason codes).
3. `backend/app/services/p5_run_gate.py` (**only** if essential to factor a read-only equivalent snapshot check; no change to existing gate behavior or persisted F1 receipts).
4. `backend/tests/p5/test_p5_evidence_bridge.py` (new; security, negative/replay/compare cases).
5. `docs/contracts/TOOL_CONTRACTS.md` (additive versioned contract amendment, owner-reviewed).
6. `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (additive non-graph V2 boundary).
7. `docs/phase-reports/P5_F2_IMPLEMENTATION_REVIEW_20261122.md` (new report).
8. `docs/roadmap/PHASE_PROGRESS.md` (append-only decision/progress).

**Not in this exception:** `backend/app/services/p4_*.py`, monitoring/rule engines, F0 foundation, P3 OCR/verification, `backend/app/db/models.py`, migrations, `backend/tests/p2/**`, legacy smoke scripts, API/Graph/LLM/UI/notification code, policy YAML or any real OCR artifacts. If F2 cannot be implemented faithfully within this allowlist, STOP and request a specific owner reviewed path exception; do not weaken prior tests. **No migration is proposed for this read-only bridge.** Contract changes require review before code merge. No owner auto-merge.

## 4. Proposed synthetic acceptance matrix — not yet executed

| ID | Synthetic condition | Required F2 outcome |
|---|---|---|
| F2-01 | Current F1 PROCEED, identical selected source/facts/observations and session | Read-only bounded V2 envelope; runtime_evaluable=false |
| F2-02 | Missing F1 receipt or F1 HALT/UNAVAILABLE | No envelope; typed denial; no DR |
| F2-03 | Previously PROCEED now changed file SHA/size/path or lost file | No stale V2 success; no historical rewrite |
| F2-04 | Source metadata unchanged but raw fact text/quality flag/doctor decision changed | Fingerprint mismatch; deny; no stale PROCEED reuse |
| F2-05 | Gate persisted blocker list forged/extra, decision mismatch or multiple conflicting PROCEED rows | Fail-closed; no candidate |
| F2-06 | Doctor session revoked/expired; reassigned patient; cross-patient run/source | 403/typed denial, no evidence leak |
| F2-07 | Run status/version or mapping/policy/clock changed | Deny with version/freshness mismatch |
| F2-08 | F0 manifest tampering, source omission changed, original and recovery both selected | Deny; historical OPEN VI-002 preserved |
| F2-09 | Audited omitted original OPEN VI-002; separately verified selected recovery eligible | Preserve historical exclusion as typed metadata, never resolve original |
| F2-10 | Valid selected self_reported check-in | Remains self_reported_validated and labelled; never doctor verified |
| F2-11 | Verified-document observation with missing/mismatched source fact, wrong unit or false doctor lineage | Fail-closed; no promotion |
| F2-12 | Pending/rejected/corrected-without-real-decision fact or multi-measurement report | No trusted fact / no V2 PROCEED |
| F2-13 | Unmapped or document-only verified unit (e.g. g/dL) | Keep verified document-only fact; no observation/unit coercion |
| F2-14 | 0 selected observations | Empty comparisons + typed no_current_selected, not fake baseline |
| F2-15 | More than 6 current selections, invalid current, future or wrong-patient | Fail-closed (never truncate/silent drop) |
| F2-16 | Same patient, earlier valid bounded baseline | Deterministic Decimal delta, fixed tie-break, typed trust_basis |
| F2-17 | No baseline, out-of-window, bad baseline unit or rejected history | Non-comparable + explicit typed exclusion, not "normal" |
| F2-18 | Observations cross trust levels | mixed; never doctor_verified if either self-reported |
| F2-19 | Concurrent changes during read, same-run replays and code-version mismatch | Fail closed or deterministic identical projection, no partial result |
| F2-20 | Attempt to pass caller-crafted V2 / manipulate role/gate/count or invoke DR | Not exposed/denied; no review_item, task or graph event |
| F2-21 | Source original OCR glyph discrepancy GOLD-EX-11 | No claims of OCR fidelity; existing FAIL/NOT PROVEN remains |
| F2-22 | Full repository Windows and CI regression, original P3/F0/F1 tests, no migrations | Existing tests continue PASS; Playwright SKIP stays accurately labelled |

All test counts, timings and PASS/FAIL figures above are **requirements, not executed evidence**. Owner isolated Windows PowerShell 5.1 acceptance at exact final commit is still required in the later implementation PR. Full GitHub Python Ruff/Pytest/Alembic + frontend and secret/artefact scans are mandatory. Explicit reproducible tests must demonstrate that the bridge writes no F1/F0/P3/P4 or graph/DR rows.

## 5. Open design risks / decisions the owner must understand

1. The term `EvaluableReviewEvidenceV2` is easy to confuse with permission to run rules: **separate "evidence shape validated" from "runtime execution authorized".** Runtime stays false; a future P4 owner decision is still required.
2. A SQLite snapshot is not a filesystem snapshot. A matching source byte check only supports the inspected instant; any later consumer requires another freshness recheck.
3. The current F1 implementation is a mutating transaction; factoring the evaluator for F2 must preserve F1 replay/receipt semantics and existing tests. A silent `evaluate_run_verification_gate` call from supposedly read-only F2 is forbidden.
4. P4 C-35A's `missing_baseline` differs from the proposed `STATE_AND_GRAPH_CONTRACT`'s `no_baseline`. Formalize versioning and mapping; never rewrite old test output without explicit owner contract decision.
5. Existing F0 allows ≤20 selected observations while §3.5 compares ≤6: no unnoticed truncation. The owner must endorse the cap behavior, baseline provenance and no-observation semantics.
6. The P3 original OCR `GOLD-EX-11` miss remains an explicitly unresolved real source-check failure. F2 is **not** clinical safety validation or repair.

## 6. Required governance / owner approval sequence

1. **Design-only PR:** exact diff must be **two Markdown files only**: this design and an append-only `docs/roadmap/PHASE_PROGRESS.md` proposal checkpoint. Do not touch source/migrations/tests. Hosted CI on design branch demonstrates only existing tests, not F2 tests.
2. If all **D-F2-01..04** decisions and narrow proposed later code allowlist are acceptable, owner posts **exactly** in this PR Conversation:

   `RATIFY-P5-F2-BOUNDED-EVIDENCE-BRIDGE-SCOPE`

   This ratifies only the bounded F2 **design/code-scope proposal**, not code acceptance, P4 policy activation or phase PASS. If any decision is not acceptable, revise this docs PR instead; do not ratify a partial/ambiguous scope.
3. On verified owner comment, record exact comment URL, author/time, decision list and exclusions **append-only** in `PHASE_PROGRESS.md` on this design branch. Obtain CI **SUCCESS on the updated exact head**, independent owner review and owner merge; then confirm exact-main postmerge CI **SUCCESS**.
4. Only then create a separately scoped **P5-F2 code PR**, no agent merge; independent negative/positive tests, exact-head GitHub CI, owner isolated Windows, then a separate owner acceptance decision. Return to P4 run-bound review persistence **only after F2 prerequisites**, not in this docs or F2 code PR.

**Do not mark F2, P4 or P5 overall PASS.** No UI, graph, DR execution, real patient advice or clinical deployment. **NOT FOR CLINICAL USE.**

## 7. Evidence and rollback

**Reviewed:** the actual merged PR #33 status, exact-main postmerge CI, `AGENTS.md`, CH-01, F0 and F1 current implementations, typed P3/F1 schema, P4 read-only projection and C-35A comparator, `TOOL_CONTRACTS.md` §§3.4–3.7, graph contract proposed types, closed mapping and demo-only DR catalogue. **Executed:** GitHub read operations, creation of documentation-only design branch and docs commits. **Not executed:** F2 source code, new F2 tests, owner Windows, live OCR, model/LLM, browser E2E. Design PR rollback is close the draft; no application code or DB impact.
