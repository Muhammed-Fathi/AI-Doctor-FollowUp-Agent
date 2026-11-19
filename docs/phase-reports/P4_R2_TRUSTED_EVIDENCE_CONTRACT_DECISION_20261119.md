# P4 R2 — trusted evidence and tool-interface reconciliation: owner decision request

**Status: PROPOSED ONLY / R2 OWNER DECISION OPEN / NO RUNTIME AUTHORIZATION.**  
**Date:** 2026-11-19 · **Phase:** P4 · **Tracking:** [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14)  
**Baseline:** Owner-merged [PR #24](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/24), `main@8cdd5cef318a73c0adcfcf86a953d6801494cb56`; [post-merge CI #44517849352](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44517849352) **COMPLETED / SUCCESS** on that exact SHA.  
**Governance:** Owner explicitly selected **R1-A** and **R4**. R1-A defers P4-3 review-item/evidence-link persistence until a genuine P5-owned workflow_run identity exists. R4 authorized synthetic **offline** GOLD-A/B/C/D tests, delivered and merged in PR #24. Neither choice approves R2 or R3/OQ-R01. P4 remains **IN_REVIEW**, not accepted. Local synthetic educational project; **NOT FOR CLINICAL USE**. Historical P3 real OCR `GOLD-EX-11=FAIL / NOT PROVEN` is unchanged.

## 1. Why a separate R2 decision is necessary

The normative draft `docs/contracts/TOOL_CONTRACTS.md` `3.5 defines a **pure** `compare_observations(current ≤6, baseline_lookback_days)` but does not specify how the pure tool acquires the historical baseline. The actual internal `backend/app/services/monitoring.py::compare_observation_history` takes up to 100 historical observations and returns the latest-comparable-per-measure result, not an exact implementation of the public tool’s current-list/`not_admissible` response semantics. Joining these silently would alter a reviewed interface.

`TOOL_CONTRACTS.md` `3.7 defines `evaluate_demo_review_rules(verified_facts, comparisons, policy_version)`. `DEMO_REVIEW_RULES.md` `10 and the candidate P4-2 evaluators also require admissible observations, injected clock, threshold contents, source lineage and an independently established fact-verification decision. Both offline evaluators still take a **caller-controlled test-only** `blocking_fact_count`; the fact that a fixture supplies 0 cannot prove a real gate. `demo_policy.py` validates candidate policy shape; it does not prove owner approval or activate the arbitrary numeric values.

The P4-2e read-only provenance projection and P4-2f selected-document preflight are implemented and tested, but neither binds an actual persisted run. `p4_document_preflight.SelectedDocumentPreflight.run_gate_completed` is **always False**. No `workflow_run`, `review_item` or `evidence_link` table exists; migrated head remains `0005_p3_ocr_provenance`. P4-4 GOLD tests **script** test-only doctor decisions and do not prove physical OCR/source accuracy or a genuine doctor review.

**No automatic bridge is permissible** from these components to an agent or live `DR-*` rule caller merely because PR #24 CI and Windows tests passed.

## 2. R2-A proposed: two-stage evidence contract, with a hard run-identity boundary

**Recommendation for OWNER REVIEW, NOT AUTHORIZED BY THIS DOC:**

**Stage A — P4 internal, read-only evidence inspection (possible before P5):**
1. Accept a **server-established, session-authenticated** doctor `Principal`, patient scope, an explicitly bounded selection of patient documents and observations and an injected aware `as_of_utc`. All selection identifiers are treated as untrusted selectors until matched to the currently assigned synthetic patient in the app DB. Neither request data nor fixtures may assert a role/doctor assignment.
2. Read from the **same consistent database snapshot / transaction**: stored doctor/assignment state; selected documents (including status, failure/recovery lineage and printed patient ref); active extracted facts, corrected-original provenance and immutable doctor `FactVerification` decisions; **all pertinent stored open and historical issues** without misrepresenting lifecycle; selected observations and mapped source-fact IDs; source timestamps and the policy-version binding. Fail closed on cap overflow, missing/foreign rows, mismatched versions, duplicate selection, missing decision, unsupported source evidence, or concurrent snapshot invalidation. Do not infer original image glyph accuracy from OCR output or a human attestation bit.
3. Separate three **different predicates**: (i) `observation_admissible` = unit, validation, patient scope and timestamp; self-reporting is admissible **as labelled**, (ii) `selected_document_preflight_clear` = only selected persisted rows meet declared checks, and (iii) `run_gate_completed` = the complete documented run's fact/VI gate has been independently evaluated against a real persisted run selection. Under **R1-A, (iii) MUST REMAIN FALSE / UNAVAILABLE IN P4**, even when (i) and (ii) hold. No caller-supplied boolean, count, fake token or offline flag may change this.
4. Return an **immutable, bounded internal inspection result**: canonical scope identifiers, selected IDs, `as_of_utc`, source/lineage exclusions, admissibility exclusions, verification issue *types/reasons*, active fact count and verified count, fact/document snapshot identity (to detect stale replay), and an explicit **UNAVAILABLE** run-gate outcome. Do not expose untrusted uploaded text, patient-identifying display names, PHI, task instructions or a write capability. A hash alone is not authorization and must not replace repeatable DB consistency checks.
5. Never invoke live `evaluate_demo_review_rules`, persist review items, create `workflow_run` placeholders, or return `run_gate_completed=True` in Stage A. An offline analysis caller may continue to exercise the quarantined candidate functions with **explicit test inputs** and a conspicuous synthetic-only label, but the public rule/tool route remains disabled.

**Stage B — real run-bound verification later, once P5 creates a valid run (NOT P4 under R1-A):**
1. Start from the **app DB as run-status source of truth**, not a client-supplied run_id nor a LangGraph checkpoint assertion. Resolve the immutable persisted `workflow_run` author/doctor/patient, pinned selected document IDs, observation IDs, injected clock, mapping, workflow and policy versions, status/idempotency identity and current access rules. The current contract does not yet provide a reliable persisted run-selected input-set snapshot: it needs a separate P5 design/approval before Stage B.
2. Evaluate **all run-selected documents** and their source/recovery relationships (including selected failed originals), and recompute **VI-001..VI-006** as specified from current stored evidence. Preserve corrected-history originals only when the saved doctor-correction and replacement lineage is valid; plain rejections and true multi-measurement rows still block. **R21 terminal rejected document `VI-002` stays open**. Linking a later recovery upload does not erase or validate the original; policy on whether a run can omit a terminal source requires a separate explicit owner decision. Do not infer 'resolved' from zero newly computed drafts if historical open issues remain relevant.
3. Produce a **typed and scoped gate result** (`PROCEED` or `HALT`), a bounded true blocker count, issue IDs/types and source-selection binding, under a reviewable **same-snapshot / replay freshness check**. Every route must reject stale, foreign or modified evidence. Crucially, no `DR-*` is evaluated on a halted/incomplete run. The report must preserve `VI-*` vs `DR-*` separation; `E_UNVERIFIED_FACT` pertains to extracted facts only, never a self-reported admissible observation.
4. Only after **separate owner-approved R2 interface revision and R3/OQ-R01 policy ratification**, consider a versioned runtime bridge from trusted gate evidence to pure rule evaluation and P4-3 review storage. Stage B does not itself authorize clinical validity, LLM, drafts, approval, notifications or external actions.

## 3. `compare_observations` `3.5: explicit options and owner choice

**C-35A (recommended): split scoped history acquisition from pure comparison.** The server-scope service first reads admissible and excluded observations (bounded, provenance-preserving) from the app DB with the injected clock. A separately typed internal *pure* comparison engine consumes explicit current ≤6 **and** explicit history ≤100, both constrained to one patient and consistent time window, with the rule “most recent prior comparable row.” For rejected/unit/timestamp-invalid *current* rows, emit a distinct `comparable=false, incomparable_reason=not_admissible, skip_reason` result as the draft tool requires. Historical rejected rows are **excluded**, never baselines. This is a **proposed tool interface revision**, not an edit to current `TOOL_CONTRACTS.md` or to `compare_observation_history` in this PR. It must define whether an absent current is omitted or a typed result; do not guess.

**C-35B: keep the public signature unchanged and make `current` come with server-attested baseline context.** Such context must be specified and verifiable, not hidden in an implicit global cache or independently re-querying inside a supposedly pure function. If selected, a separate ADR and version bump must define the context encoding and cache invalidation. This option is less transparent.

**Recommend C-35A**, subject to explicit owner approval. Whether the existing helper is reused or wrapped must be tested, with no change in self-reporting labels or a fabricated baseline.

## 4. `evaluate_demo_review_rules` `3.7: versioned, trusted input vs the test-only API

**C-37A (recommended):** define a *future* `EvaluableReviewEvidenceV2` value assembled **only by the approved, run-bound server gate**, including identity-bound run selection, verified-only facts and their source references, admissible observations including persisted creation/source metadata, recomputed comparisons, explicit `as_of_utc` and a pinned **owner-approved** policy revision/parameters. The engine remains **pure, deterministic and offline**: it validates that all supplied fact references and comparator IDs are consistent within that sealed input snapshot, rejects unapproved policy, and returns only bounded neutral `ReviewFlag` values and typed exclusions. It does **not** write them.

The live caller must use a **gate-produced opaque internal object**, not a serializable API body where a client sets `blocking_fact_count=0`, `doctor_verified=true` or `gate_completed=true`. Runtime readiness depends on the server rechecking the source against its durable run state before execution. A sealed object is a type/system contract, not independent cryptographic proof and not a substitute for transactional replay checks.

**C-37B:** add missing inputs as independently supplied arguments directly to the existing `3.7` signature. This is easier to forge or assemble inconsistently; if selected, all arguments need the same server-authoritative, same-snapshot proof and an explicit versioned interface. Do not interpret a structural schema as trust.

**Recommend C-37A**, but only as a design until actual P5 run identity, R2 ratification and R3 policy ratification. The current `CandidateDemoPolicy` / `CandidateProvenancePolicy` version families remain isolated. Do not promote `candidate-p4-*` inputs to approved `demo-policy-*` automatically.

## 5. Remaining owner decisions and normative conflicts

| Item | State | Decision needed |
|---|---|---|
| **R2-A scope staging** | Proposed | Allow a *separate* P4 internal read-only typed inspection design/test PR **without** a run-clearance boolean; run-bound gate remains deferred under R1-A |
| **C-35A vs C-35B** | Proposed | Select how pure `compare_observations` obtains patient history and reports non-admissible current values; do not change normative `3.5` silently |
| **C-37A vs C-37B** | Proposed | Select how `3.7` receives trusted fact, observation, comparison, clock, and policy evidence; do not change normative `3.7` silently |
| **Terminal-rejection/R21 recovery interpretation** | **OPEN** | Run scope that includes a failed original **must block** absent a separately ratified exclusion policy; a later recovery does not remove its open VI-002. Decide whether a future run may select only the recovered document and how this exclusion is auditable. No auto-clear |
| **Snapshot/freshness/replay** | **OPEN** | Specify app-DB transaction/isolation, source-file integrity checks and revision/policy binding across a future run; a timestamp/hash by itself does not prove same-snapshot semantics |
| **R3 / OQ-R01** | **OPEN** | Explicit owner approval of named, versioned, arbitrary *synthetic* demo policy numbers — not supplied by these tests |
| **R1-A P4-3 persistence** | **OWNER-SELECTED DEFER** | `review_item`/`evidence_link` and FK stay blocked until real run identity; P4 cannot be declared fully complete |

## 6. Separate post-decision implementation and tests (NOT executed by this PR)

If the owner selects the recommended R2-A/C-35A/C-37A options, start a **new, independently reviewed P4 component PR** limited to typed read-only consistent-snapshot selection, exclusions, conservative fake/foreign/stale refusal and *offline* comparison-contract tests. No real `run_gate_completed=true` or live rule pipeline. Tests required:

- Authenticated active doctor, assigned synthetic patient, full selected-doc scope, same-session/transaction reader; foreign doctor, wrong patient/document/fact/observation and stale selection all deny without leaking data.
- Valid correction/verified-decision lineage vs pending, ordinary rejection, terminal failed original, later recovery, duplicate/superseding entries, multi-measurement, forged zero blockers, stale VI reconciliation; preserve VI-001..006 identity without claiming run clearance.
- Admissibility and provenance: rejected, unsupported unit, unparseable/future times, self-reported never becomes doctor-verified; same mapped fact and derived observation count as **one** source.
- Strict chosen `DR-006` two independent verified documents at identical UTC measured time, and `DR-008` observed created-vs-measured chronology; no inference from missing/equal creation instants.
- Repeatable selected snapshot, deterministic ordering/dedup, bounded caps, no DB writes, no activated API, no P5/LLM, no patient/clinical messaging. Test-only GOLD-A/B/C/D expected output files from PR #24 stay unchanged unless an explicit expected-outcome revision is reviewed.

The exact-head CI must pass Ruff, pytest, Alembic smoke, OpenAPI, repo scanner and frontend; an owner Windows isolated-worktree test is required before merging any code PR. No CI may be cited as evidence of real OCR source-glyph verification. Real `GOLD-EX-11` remains **FAIL / NOT PROVEN**.

## 7. This PR's exact scope, evidence and reviewer checklist

**Design reviewed here:** `AGENTS.md`, `TOOL_CONTRACTS.md` ``3.4–3.7, `DEMO_REVIEW_RULES.md` `4 and `10, `STATE_AND_GRAPH_CONTRACT.md` `3/`4/`7, `DATA_DICTIONARY.md` ``2.8–2.16, merged `monitoring.py` / `demo_rules_candidate.py` / `provenance_review_candidate.py` / `p4_readonly_provenance.py` / `p4_document_preflight.py`, and owner-approved P4-4 GOLD tests and reports. Reviewed as source, **not executed** in the assistant environment.

**Executed:** verified on GitHub that [PR #24](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/24) was owner-merged at `main@8cdd5cef318a73c0adcfcf86a953d6801494cb56`; [postmerge main CI #44517849352](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44517849352) **COMPLETED / SUCCESS**. This PR introduces no executable changes. **Not executed:** local Python, PowerShell, Tesseract, Playwright, real run-gate, actual workflow, any policy activation. CI on this new docs-only PR must be checked independently.

**Changed files only:** new `docs/phase-reports/P4_R2_TRUSTED_EVIDENCE_CONTRACT_DECISION_20261119.md` and an **append-only** checkpoint in `docs/phase-reports/PHASE_4_REPORT.md`. No normative contract, production code, SQL migration, P5 module or policy file is edited.

**Owner review checklist:** inspect the proposed recommendations and non-goals; explicitly say whether you approve **R2-A + C-35A + C-37A** for a *separate internal-only* code/testing PR. Independently decide or defer terminal-recovery scope and R3/OQ-R01 later. **Merging this documentation alone is NOT ratification of R2**, approval of policy, a phase pass, or consent to P5 scope. If rejected, close this PR; no code/data rollback required.

**P4 stays IN_REVIEW; R1-A and R4 stand; R3 remains OPEN; P3 GOLD-EX-11 stays FAIL / NOT PROVEN; NOT FOR CLINICAL USE.**
