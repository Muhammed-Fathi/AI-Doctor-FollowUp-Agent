# P4 — Comprehensive Phase Closure Assessment and P5 Readiness Review

**Date:** 2026-11-23  
**Document class:** ASSESSMENT + DOCUMENTATION ONLY. **This document does not mark P4 PASS, does not accept P4, does not authorize P5, and does not activate anything.**  
**Branch:** `arena/a61b8893-p4-final-closure-assessment`, created from the exact owner-merged `main@96cb275136f9f80608709ce8c7d83693bffa36c3` (merge of PR #45).  
**Tracking:** [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**. P4 remains **IN_REVIEW** until the owner posts a consolidated decision.  
**Scope limit:** local, synthetic, academic application only. **NOT FOR CLINICAL USE.**  
**Preserved adverse statuses:** real P3 OCR `GOLD-EX-11 = FAIL / NOT PROVEN`; RB3-75..77 **deferred / never executed**; DR-006 persistence **prohibited**; DR-006 genuine end-to-end reachability **unproven in both directions**; full P5 **NOT ACCEPTED**.

---

## 0. Verdict summary

**Recommendation: B — bounded conditional academic acceptance.** Not A, because several *literal* P4 exit-gate expectations are either not executed in their literal form or were re-scoped by explicit owner decisions. Not C, because every gap is either (i) an owner-ratified conservative scope reduction that is fail-closed, or (ii) a documentation/verification-form gap with an equivalent-or-stronger safety outcome — not an unresolved engineering defect, weakened assertion, fabricated evidence or reproducible correctness failure.

| Question | Answer |
|---|---|
| Is the P4 engineering corpus complete for the *authorized* scope? | **Yes** — P4-1, P4-2 (offline six-rule evaluator), P4-3 (authorized durable `observation`-link persistence) and P4-4 (service-level run-backed GOLD A/B/C/D + negatives) are implemented, independently reviewed, CI-green and owner-accepted slice by slice. |
| Are all *original* P4 exit requirements satisfied in their literal form? | **No.** Six literal expectations are deferred or not literally executed (§5.1, §5.4). |
| Are there genuine mandatory blockers? | **None** for a bounded acceptance. There *are* six would-be blockers for option A (§5.4). |
| Is any accepted evidence fabricated, weakened or inferred? | **No.** Every executed claim in this document is traceable to a named test function, a named CI run, or a named owner Windows record. Where a claim was not executed, it is marked NOT RUN / NOT PROVEN. |
| Does P4 closure authorize P5? | **No.** P5 requires its own explicit owner authorization after the P4 decision (§6.4). |

**Status roll-up across the 50 requirement rows of §2 (Matrices A–E):** 27 satisfied · 11 partially satisfied · 6 rows outside P4 scope (3 unique requirements plus 3 re-listings/sub-parts in the decision register) · 2 superseded by explicit owner decision · 4 deferred · 0 rows whose only evidence is a source-presence check.

---

## 1. Verified baseline, evidence classes and provenance

### 1.1 Repository identity (independently verified this session)

| Item | Value | How verified |
|---|---|---|
| Repository | `Muhammed-Fathi/AI-Doctor-FollowUp-Agent` | `git remote -v`, `gh api repos/...` |
| `origin/main` | `96cb275136f9f80608709ce8c7d83693bffa36c3` | `git fetch origin --prune`, `git rev-parse origin/main` |
| Merge identity | PR #45, `merged=true`, `merged_at=2026-11-23T20:42:08Z`, `merged_by=Muhammed-Fathi`, `merge_commit_sha=96cb275…`, head `679ccb554e3e5c147c734bd0d2e6ca4dc9dec7a3` | `gh api pulls/45` |
| Design integrity | merged main tree `86b8645a4e7d5f3f6be514586a155448ad17046e` **identical** to recording head `679ccb5` tree; `git diff 679ccb5 96cb275` empty | `git rev-parse <sha>^{tree}`, `git diff --stat` |
| Post-merge main CI | [#45262091228](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45262091228), event `push`, branch `main`, head `96cb275`, **COMPLETED / SUCCESS** — Backend (Python 3.12) 14/14 steps, Frontend (Node 22) 11/11 steps, all `success` | `gh api actions/runs/45262091228` + jobs |
| RB4 owner acceptance | comment [`7113168956`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/45#issuecomment-7113168956), `OWNER-ACCEPT-P4-RB4`, author `Muhammed-Fathi`, `author_association: OWNER`, created `2026-11-23T20:30:40Z`, never updated, accepted SHA `935283577e55f9ed92821393eec088e02017d6d0` | `gh api issues/comments/7113168956` |
| Issue #14 | `state=open`, 19 comments, full dump read | `gh api repos/.../issues/14` + comments |
| Working tree | clean at `96cb275` before this document; only the three authorized paths changed after | `git status --porcelain` |

### 1.2 Evidence classes used throughout

| Code | Meaning | Authority |
|---|---|---|
| **CI** | GitHub Actions at a named run id / exact SHA — Backend Python 3.12, Frontend Node 22 | Authoritative for pass/fail and environment |
| **LNX** | Local Linux execution, **Python 3.11.2** (disclosed deviation; CI 3.12 is authoritative) | Supporting only; never a Windows or 3.12 claim |
| **WIN** | Owner-executed isolated Windows PowerShell 5.1 `setup.ps1` + `test_all.ps1` at a named SHA | Authoritative for the owner gate; exact Windows passed count not printed where noted |
| **DOC** | Documentation/design review only — no execution | Never a pass |
| **NR** | Not run | Never a pass |
| **NP** | Not proven (no executed evidence either way) | Never a pass |

### 1.3 Local environment disclosure

The only interpreter available in this sandbox is system **Python 3.11.2**. No Python 3.12 was obtainable and none was retried. No `pytest`/`ruff`/Alembic virtual environment exists in this sandbox, so **no test suite was executed locally for this document**. All executed test evidence cited here is either (a) the authoritative CI runs at named SHAs, or (b) the owner's Windows records at named SHAs, or (c) previously recorded local Linux 3.11.2 results at named SHAs from the accepted slice reports. The only command executed for this document is the repository scanner (§7).

---

## 2. Requirement-to-evidence matrix

### 2.1 Status vocabulary (exhaustive)

`satisfied` · `partially satisfied` · `not proven` · `deferred` · `superseded by explicit owner decision` · `outside P4 scope`.

A row is `satisfied` only when the *behaviour* is asserted by a named executed test at a named SHA — never because a module exists, a design was ratified, or a reviewer approved a slice. A row is `partially satisfied` when part of the requirement is proven and another part is deferred, outside scope, or not literally executed; the unproven part is named in the row.

### 2.2 Matrix A — MVP requirements applicable to P4

| Req. | Original expectation (source) | Implemented behaviour | Exact path + symbol | Exact tests (file :: function) | Executed evidence + source | Owner decision + merge identity | Status | Remaining action |
|---|---|---|---|---|---|---|---|---|
| **REQ-MON-01** | Compare current verified measurement vs **most recent prior** comparable measurement in lookback; explicit `as_of_utc`; patient-scoped; no conversion/imputation (`MVP_SPEC`, `TRACEABILITY_MATRIX` row 57) | Latest usable prior within an explicit window; typed `missing_baseline`; exact `Decimal`; order-independent; clock-injected | `backend/app/services/monitoring.py::compare_observation_history` (`:143`), `::admissibility_reason` (`:109`); `backend/app/services/p4_explicit_history.py::compare_explicit_current_with_history`; 90-day run-bound projection `backend/app/services/p4_run_bound_preview.py::build_p4_run_bound_review_input_preview` (`:227`) | `test_p4_monitoring.py` :: `test_req_mon_01_case_b_uses_most_recent_prior_not_oldest`, `…lookback_uses_current_measurement_not_as_of`, `…exact_boundary_is_included`, `…decimal_arithmetic_is_exact`, `…result_is_order_independent_and_clock_injected`, `…max_input_and_lookback_bounds`; `test_p4_explicit_history.py` :: `test_explicit_history_uses_latest_prior_not_nearest_future`, `…same_time_does_not_become_prior_and_tied_prior_is_deterministic`; `test_p4_run_bound_preview.py` :: `test_rb1_90_day_baseline_is_latest_prior_and_trust_retained`, `test_rb1_365_day_f2_baseline_is_not_a_90_day_policy_baseline` | CI #45262091228 (`main@96cb275`) full backend SUCCESS; LNX 3.11.2 1294/0 at `9352835`/`679ccb5`; WIN 12 PASS / 0 FAIL / 1 SKIP at `9352835` | R2-A / C-35A / C-37A (issue #14 comment 7009363266) kept the comparison **internal**, not an agent tool; RB1 ratification PR #36 comment 7075542080; RB1 merged PR #37 → `main@fb859ba2` 2026-11-22T08:37:08Z | **satisfied** (service semantics) | Bind to the §3.5 `compare_observations` agent tool in P5; no P4 action |
| **REQ-MON-02** | Comparison guards + `skip_reason` reporting for missing/future time, rejected validation, unit mismatch (`TRACEABILITY_MATRIX` row 58) | Typed `incomparable_reason` + `skip_reason`; excluded rows returned, never silently dropped; F2/RB1/RB2/RB3 all preserve exclusions verbatim | `monitoring.py:45–55` (`skip_reason`, `incomparable_reason`); `p4_explicit_history.py:119–158`; `p5_evidence_bridge.py` exclusions; `p4_rb3_review_persistence.py` L2 exclusions in the output identity | `test_p4_monitoring.py` :: `test_req_mon_02_missing_baseline_is_incomparable_without_imputation`, `…missing_and_future_time_are_reported_not_hidden`, `…invalid_value_fails_closed`; `test_p4_explicit_history.py` :: `test_current_future_and_wrong_unit_have_typed_exclusions`, `…history_rejected_unit_and_future_are_excluded_never_baselines`; `test_p4_run_bound_preview.py` :: `test_rb1_history_exclusions_remain_explicit`; `test_p4_rb3_review_persistence.py` :: `test_rb3_21_72_73_83_to_88_layered_exclusions_and_precedence` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | same as above; RB3 acceptance PR #43 comment 7105580779 | **satisfied** | Expose `skip_reason` through the P6 review/timeline UI |
| **REQ-MON-03** | Duplicate/conflict rules: `DR-008` for duplicate/out-of-order; `DR-006` for two conflicting sources at the same time (`DEMO_REVIEW_RULES` §4, `TRACEABILITY_MATRIX` row 59) | `DR-008` fully implemented (exact duplicate, created-vs-measured ordering, no creation-order inference). `DR-006` implemented **in the pure evaluator only**; persistence denied whole-invocation; genuine F1-PROCEED reachability unproven | `p4_rb2_offline_rules.py` DR-006 `:423–454`, DR-008 `:452–479`; `p4_rb3_review_persistence.py` T12 `:1363–1364` `_deny(RB3DenialReason.DR006_PERSISTENCE_NOT_AUTHORIZED)` → `409 E_VALIDATION dr006_persistence_not_authorized` | `test_p4_provenance_review_candidate.py` :: `test_dr006_two_independent_verified_documents_same_instant_flag_once`, `…does_not_infer_independent_compatible_sources`, `…tolerance_must_be_explicit_and_strictly_exceeded`, `…one_source_fact_two_claimed_documents_rejected`, `…utc_instant_equality_handles_timezone_offset`; `…::test_dr008_*` (6 functions); `test_p4_rb3_review_persistence.py` :: `test_rb3_66_99_dr006_unit_level_boundary_denies_whole_invocation` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | **D-RB3-08(ii)** conservative prohibition ratified by `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` (PR #42 comment 7095039109, `2026-11-23T08:06:02Z`, design SHA `dabcebc7…`) and accepted by `OWNER-ACCEPT-P4-RB3` (PR #43 comment 7105580779) | **partially satisfied** (DR-008 satisfied; DR-006 pure-evaluator only — run-backed/persisted form **not proven**) | Owner records MON-03 as pure-evaluator-only for P4; C-RB3-08 stays open for any future extension (§4 C01) |
| **REQ-RULE-01** | Six active IDs `DR-001/003/005/006/008/009`; retired `DR-002/004/007/010` prohibited; exact deterministic semantics; no LLM (`TRACEABILITY_MATRIX` row 65, issue #14 scope item 2) | All six implemented in one pure evaluator; retired/unknown/duplicate IDs fail closed; no I/O, DB, API, agent, graph or LLM import | `backend/app/services/p4_rb2_offline_rules.py::evaluate_p4_rb2_offline_fixture` (`:260`); candidate subset `demo_rules_candidate.py`, `provenance_review_candidate.py` | `test_p4_rb2_offline_rules.py` (39 functions, incl. `test_rb2_r04_*`, `test_rb2_r07_*`, `test_rb2_r08_*`); `test_p4_demo_rules_candidate.py` :: `test_retired_unknown_and_unimplemented_rules_are_rejected`; `test_p4_rb2_gold_offline.py` (7); `test_p4_gold_abcd_offline_replay.py` (9); `test_p4_rb4_run_backed_gold.py` :: `test_rb4_06_gold_d_exact_ordered_outputs_and_replay` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | RB2 design `RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE` (PR #38 comment 7076744806, `2026-11-22T08:48:05Z`); `OWNER-ACCEPT-P4-RB2` (PR #41 comment 7087501521, `2026-11-22T23:20:34Z`) → `main@7190b25e` | **satisfied** (offline deterministic evaluator) | Runtime activation is **not** authorized by any P4 decision — deferred (§4 C02) |
| **REQ-RULE-02** | Exact neutral message templates, UI labels, `DEMO_ONLY`, trust suffix, no clinical interpretation (`TRACEABILITY_MATRIX` row 66) | Templates are exact and asserted byte-for-byte for DR-005/006/008/009/003; `trust_basis` and `(self-reported)`/`(includes self-reported values).` suffixes asserted; no diagnosis/urgency/treatment wording in any template | `p4_rb2_offline_rules.py` message construction; `demo_rules_candidate.py`; `provenance_review_candidate.py` | `test_p4_demo_rules_candidate.py` :: `test_case_b_emits_exactly_one_dr005` (asserts `"12 mmHg"` present and `"worsen"` absent), `…mixed_provenance_and_order_independence`, `…verified_provenance_has_no_self_reported_suffix`; `test_p4_provenance_review_candidate.py` :: exact DR-006 string, DR-008 strings, `…mixed_trust_is_never_promoted_to_verified`; `test_p4_rb2_offline_rules.py` :: `test_rb2_r04_newer_history_dr003_only…`, `…stale_newest_history_evidence_trust_template_and_replay`; `test_p4_dr009_candidate.py` :: `test_dr009_synthetic_typo_uses_exact_message_and_source_label` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | same RB2/RB3 decisions | **partially satisfied** (templates + spot wording assertions satisfied; the literal RULE-04 *exhaustive* scan is not executed — §4 C07) | Optional improvement: table-driven prohibited-term scan over all six templates (§5.5) |
| **REQ-RULE-03** | Dedupe + idempotent persistence (`TRACEABILITY_MATRIX` row 67) | Deterministic `dedupe_key = sha256(patient_id \| rule_id \| sorted refs \| trust_basis)`; `UNIQUE (workflow_run_id, dedupe_key)`; one evaluation per run; 8 exact replay-conflict reasons; zero partial writes | `p4_rb2_offline_rules.py` dedupe; `p4_rb3_review_persistence.py::persist_run_review_items` (`:691`), constants `:116–123`, triggers G1–G25 | `test_p4_rb2_offline_rules.py` :: `test_dedupe_replay_order_trust_and_no_retired_ids`; `test_p4_rb3_review_persistence.py` :: `test_rb3_01_23_44_happy_path_replay_and_honesty_receipt`, `…59_to_65_70_92_111_to_114_128_replay_conflicts_and_audit_contract`, `…i04_all_8_replay_conflicts…`, `…i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry`; `test_p4_rb4_run_backed_gold.py` :: `test_rb4_06_gold_d_exact_ordered_outputs_and_replay` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835`; RB3 CI #45191070030 / #45191082779 at `c929dee4` | RB3 acceptance PR #43 comment 7105580779; merged → `main@0738a32a` 2026-11-23T16:14:22Z | **satisfied** | — |
| **REQ-DATA-04** | Trust levels never mislabelled; `self_reported_validated` admissible and labelled; rejected rows excluded (`TRACEABILITY_MATRIX` row 32) | Admissibility predicate returns typed reasons; `self_reported_validated` accepted and carried into `trust_basis`; `doctor_verified` never produced for a self-reported input | `monitoring.py::admissibility_reason`; `p4_explicit_history.py`; `p5_evidence_bridge.py` `source_reason` | `test_p4_monitoring.py` :: `test_req_data_04_rejected_and_incompatible_unit_do_not_shift_baseline`, `…self_reported_and_mixed_are_never_mislabelled`, `…invalid_trust_fails_closed`; `test_p5_evidence_bridge.py` :: `test_f2_selected_self_reported_current_and_history_preserve_trust` | CI #45262091228; LNX 1294/0; WIN 12/0/1 | R2-A / C-35A / C-37A | **satisfied** | — |
| **REQ-DATA-05** | Closed fact → observation mapping `map-1.0.0`; unmapped document facts never become observations (`TRACEABILITY_MATRIX` row 33) | Mapping re-verified at the run boundary: document-only verified unit never becomes an observation; `mapping_version` immutable per run | `p5_evidence_bridge.py`; `p5_run_foundation.py` (`mapping_version`) | `test_p5_evidence_bridge.py` :: `test_f2_document_only_verified_unit_never_becomes_observation`; `test_p5_run_gate.py` :: `test_verified_multimeasurement_document_is_not_promoted`; `test_p4_rb4_run_backed_gold.py` :: `test_rb4_08_semantic_bridge_equivalence_for_b_and_d` | CI #45262091228; LNX 1294/0 | P3 acceptance (PR #10 comment 6995753177); F2 acceptance PR #35 | **satisfied** (P3-owned, re-verified at the P4 run boundary) | — |
| **REQ-SEC-04** | Verified-only gate + `VI-*` issues; no `DR-*` item while a fact is pending (`TRACEABILITY_MATRIX` row 112) | F1 gate recomputes VI-001..006 from the selected source; `HALT` blocks RB2 entirely; zero RB3 writes on a blocked run; F0 refuses a pending initial document before run creation | `p5_run_gate.py::evaluate_run_verification_gate` (`:887`), `::inspect_current_run_gate_locked` (`:857`), `_evaluate_locked` (`:198`), VI-006 `:608–660`; `p5_run_foundation.py::create_run_foundation` (`:121`) | `test_p5_run_gate.py` (21 functions, incl. `test_selected_unverified_fact_blocks_even_if_original_run_queued`, `test_vi_001_003_004_005_recomputed_from_selected_source`); `test_p4_rb4_run_backed_gold.py` :: `test_rb4_03_gold_c_initial_pending_document_is_refused_before_run`, `test_rb4_11_blocked_run_has_no_rb2_call_or_review_persistence` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | F1 design PR #32; F0/F1/F2 accepted as bounded slices under CH-01 (issue #14 comment 7063634619) | **partially satisfied** (VI gate/blocking satisfied; the *draft* verified-only gate is P5) | P5: enforce the verified-only gate on draft generation (SAFE-02) |
| **REQ-OPS-04** | Injected `as_of_utc` on run + policy; the only clock for time-dependent rules (`TRACEABILITY_MATRIX` row 122) | Run clock persisted and immutable; RB1 rejects an unpinned run clock; RB2 pins `2026-11-14T12:00:00Z`; RB3 CHECK-pins `as_of_utc`; coordinated clock override fails | `p5_run_foundation.py`; `p4_run_bound_preview.py` (clock recheck); `p4_rb2_offline_rules.py::_PINNED_CLOCK` (`:56`); `p4_rb3_review_persistence.py` | `test_p4_rb2_offline_rules.py` :: `test_rb2_r01_coordinated_clock_override_fails_and_equal_offsets_normalize`; `test_p4_run_bound_preview.py` :: `test_rb1_rejects_unpinned_run_clock`; `test_p4_demo_rules_candidate.py` :: `test_dr003_stale_depends_on_explicit_clock`, `test_unapproved_clock_change_is_blocked`; `test_p4_demo_policy_reference.py` :: `test_reference_has_all_exact_synthetic_numbers_and_fixed_clock` | CI #45262091228; LNX 1294/0; WIN 12/0/1 | R3-A (issue #14 comment 7062063539) pins the reference clock | **satisfied** (clock injection/immutability); literal advanced-clock replay **not executed** (§4 C07) | Optional improvement: pinned +400-day DR-003 test (§5.5) |
| **REQ-EVAL-01** | Golden JSON fixtures + deterministic replay tests (`TRACEABILITY_MATRIX` row 123) | Four frozen GOLD JSONs with pinned byte hashes; offline replay; genuine run-backed replay with exact ordered outputs and semantic equivalence | `data/synthetic/golden_cases/*.json`; `test_p4_demo_policy_reference.py` hash seals | `test_p4_rb2_gold_offline.py` (7); `test_p4_gold_abcd_offline_replay.py` (9); `test_p4_rb4_run_backed_gold.py` :: `test_rb4_01…06`, `test_rb4_08_semantic_bridge_equivalence_for_b_and_d` | CI #45262091228; LNX 1294/0; WIN 12/0/1 at `9352835` | R4 (issue #14 comment 7007626056); RB4 design PR #44 comment 7108431644; `OWNER-ACCEPT-P4-RB4` PR #45 comment 7113168956 | **satisfied** | — |
| **REQ-EVAL-02** | Extraction metrics (`TRACEABILITY_MATRIX` row 124) | — | — | — | — | — | **outside P4 scope** (P7) | P7 |
| **REQ-EVAL-03** | Runtime measurement (`TRACEABILITY_MATRIX` row 125) | — | — | — | — | — | **outside P4 scope** (P5/P7) | P5/P7 |
| **REQ-SEC-06** | No secrets/artefacts committed (`TRACEABILITY_MATRIX`, scanner; P1-owned, re-verified in every CI run) | Tracked-file scanner for secret shapes, forbidden artefacts and unsafe claims; runs in CI | `scripts/python/scan_repository.py` | CI step "tracked scanner"; local run for this document (§7) | CI #45262091228 scanner step `success`; WIN scanner PASS (297 files / 7 secret / 4 claim patterns) | P1 acceptance | **satisfied** (P1-owned, re-verified) | — |

### 2.3 Matrix B — P4 sub-deliverables (issue #14 scope items 1–4 + acceptance item 5)

| Sub-deliverable | Original expectation | Implemented | Owner decision + merge | Status | Remaining action |
|---|---|---|---|---|---|
| **P4-1** — pure monitoring comparisons + shared admissibility | Explicit `as_of_utc`, patient-scoped, unit mismatch rejected, rejected validation and missing/future timestamps handled, `self_reported_validated` accepted without relabelling, latest prior not oldest, no conversion/imputation, deterministic skip reasons | `monitoring.py`, `p4_explicit_history.py`; 15 + 9 test functions | R2-A / C-35A / C-37A (issue #14 7009363266); P4-1 slice PRs owner-merged 2026-11-19; RB1 PR #37 merged `main@fb859ba2` | **satisfied** | — |
| **P4-2** — versioned deterministic demo policy + six-rule evaluator | Six active IDs, retired prohibited, strict validation, exact neutral templates, order, evidence refs, trust basis, `DEMO_ONLY`, no LLM, injected clock, invalid policy → no items + `E_RULE_POLICY_INVALID` | `demo_policy.py::validate_demo_policy` (`:128`), `p4_rb2_offline_rules.py`, `demo_rules_candidate.py`, `provenance_review_candidate.py`; 22 + 39 + 17 + 22 test functions | RB2 design PR #38 comment 7076744806; `OWNER-ACCEPT-P4-RB2` PR #41 comment 7087501521; merged `main@7190b25e` | **satisfied** (offline evaluator) | Runtime activation **deferred** — no P4 decision authorizes it (§4 C02) |
| **P4-3** — durable review items + evidence | Additive/reversible migrations for `review_item` + `evidence_link` per `DATA_DICTIONARY` §2.9/§2.10; `UNIQUE (workflow_run_id, dedupe_key)`; scoped persistence + audit; no task/notification/approval | Migration `0008_p4_rb3_review_persistence` (head); 3 `WITHOUT ROWID` tables, 9 indexes, 25 triggers G1–G25; `persist_run_review_items` (`:691`); audit `workflow.review.persisted` with 9-key `safe_detail`; 18 + 7 test functions | `RATIFY-P4-RB3-…` PR #42 comment 7095039109; `OWNER-ACCEPT-P4-RB3` PR #43 comment 7105580779; merged `main@0738a32a` 2026-11-23T16:14:22Z | **partially satisfied** — durable `observation`-link persistence satisfied; `document_span`/`fact` links and DR-006 persistence **deferred/prohibited** | Future extension: RB3-75..77 require their own owner decision + migration (§4 C03) |
| **P4-4** — end-to-end service/API + golden fixtures | Patient/doctor scope; deterministic A/B/C + negatives; idempotency; cross-patient denial; replay; zero unapproved side effects | Service-level run-backed A/B/C/D + negatives: 12 RB4 tests; cross-patient/session/scope denials; exact replay; zero side effects | RB4 design PR #44 comment 7108431644; `OWNER-ACCEPT-P4-RB4` PR #45 comment 7113168956; merged `main@96cb275` | **partially satisfied** — service level satisfied; **public read/decision API and agent tools unimplemented** | Owner decision required: defer to P5 (tools) and P6 (API/UI) or complete in P4 (§4 C06) |
| **P4-5** — acceptance evidence | Full Python 3.12 tests + CI, Windows owner gate, exact changed-file inventory, independent security/scientific-language review, signed owner phase decision | Per-slice: CI green at every accepted SHA; owner Windows gates recorded per slice (RB2 historical starting SHA `21751e64`; RB3 reported 12 mandatory PASS / 0 FAIL / 1 optional SKIP at its accepted head; RB4 `9352835`); independent reviews R01–R05 and RB3-I01–I05; exact inventories recorded | Each slice's acceptance comment | **partially satisfied** — no single consolidated owner phase decision exists yet | This document is the input to that decision (§5.8) |

### 2.4 Matrix C — P4 exit-gate evaluation IDs (`EVALUATION_MATRIX` §5/§11)

| ID | Literal expectation | Evidence | Status | Note |
|---|---|---|---|---|
| **RULE-01** | Replay every gold fixture → exact expected rule ID set and order | `test_p4_rb2_gold_offline.py` (A/B/C/D), `test_p4_gold_abcd_offline_replay.py`, `test_p4_rb4_run_backed_gold.py::test_rb4_06_gold_d_exact_ordered_outputs_and_replay` (D order DR-001, DR-003, DR-008, DR-009, DR-005; 7 links) | **satisfied** | Offline + genuine run-backed |
| **RULE-02** | Evaluate twice for the same run → identical items, no duplicates persisted | `test_rb3_01_23_44_happy_path_replay_and_honesty_receipt`, `test_rb3_i04_*`, RB4 `_assert_exact_replay` at six sites | **satisfied** | Durable, run-backed |
| **RULE-03** | Pass a pending fact to the engine → `E_UNVERIFIED_FACT`, zero items | `test_p4_rb2_offline_rules.py::test_rb2_r05_unverified_fact_assertion_fails_closed` asserts `error.value.code == "E_UNVERIFIED_FACT"`; `test_blocked_unverified_facts_stop_offline_candidate_evaluation`; `test_dr009_verification_blocker_prevents_any_review_output` | **satisfied** | Typed service error; the HTTP `409` form does not exist because there is no API (§4 C07) |
| **RULE-04** | Scan **all** messages for prohibited wording → zero prohibited terms | Exact template assertions + spot checks (`"worsen"` absent, suffix present, exact DR-006/008/009 strings); **no exhaustive table-driven scan of every template** | **partially satisfied** | §4 C07; optional improvement §5.5 |
| **RULE-05** | Malformed policy / unknown rule ID → `E_RULE_POLICY_INVALID`, zero items | `test_p4_demo_policy.py` (22 negative cases), `test_rb2_r06_malformed_policy_is_typed_failure`, `test_invalid_candidate_policy_fails_closed`, `test_retired_unknown_and_unimplemented_rules_are_rejected` | **satisfied** | Fail-closed, no partial output |
| **RULE-06** | Unit mismatch baseline (`mg/dL` vs `mmol/L`) → `comparable=false`, no `DR-005` | `test_req_data_04_rejected_and_incompatible_unit_do_not_shift_baseline`, `test_mismatched_unit_never_shifts_baseline`, `test_rb2_r04_inadmissible_newer_history_cannot_determine_age` | **satisfied** | No conversion, no imputation |
| **RULE-07** | Static check: rule engine imports no task/approval/messaging module | — | **outside P4 scope** (P7) | `test_no_io_run_api_or_agent_imports_in_pure_service` already provides a stronger P4-local import assertion |
| **RULE-08** | Evaluate with `as_of_utc=2026-11-14T12:00:00Z` and again **400 days later** → stable first run, `DR-003` on the second, both record the as-of used | Pinned-clock stability proven (`test_rb2_r01_…`, `test_reference_has_all_exact_synthetic_numbers_and_fixed_clock`, `test_unapproved_clock_change_is_blocked`); **the +400-day replay is not executed** — the design deliberately blocks unapproved clock changes | **partially satisfied** | §4 C07: fail-closed clock immutability vs literal advanced-clock test |
| **MON-01** | Missing baseline → `DR-001` once per type, no delta claimed | `test_dr001_single_missing_baseline`, `test_gold_a_stable_three_current_measurements_zero_flags`, `test_rb4_10_zero_selected_current_history_admissibility_and_exclusions` | **satisfied** | — |
| **MON-02** | Duplicate / out-of-order entries → `DR-008`, no silent correction | 6 `test_dr008_*` functions; `test_gold_d_five_rules_without_doctor_verified_source_conflict` | **satisfied** | — |
| **MON-03** | Two conflicting sources at the same time → `DR-006`, **both evidence refs shown** | Pure evaluator: `test_dr006_two_independent_verified_documents_same_instant_flag_once` (both refs). Run-backed/persisted: **not proven** — RB3 denies the whole invocation; genuine F1-PROCEED reachability unproven (C-RB3-08) | **partially satisfied** | §4 C01 |
| **TRUST-01** | Self-reported vs doctor-verified flowing into a review item **and a draft** → `trust_basis` correct, suffix present, never described as verified | Review item: satisfied (RB2/RB3/RB4 assertions). Draft: **not executed** — P5 | **partially satisfied** | Draft half outside P4 scope |
| **TRUST-02** | `is_admissible_observation`: rejected row skipped with `skip_reason=validation_rejected`; `self_reported_validated` accepted and carried; cross-patient → `E_SCOPE_VIOLATION`; never `doctor_verified` for self-reported; `E_UNVERIFIED_FACT` never raised for observations | `test_req_data_04_rejected_and_incompatible_unit_do_not_shift_baseline`, `test_req_data_04_self_reported_and_mixed_are_never_mislabelled`, `test_req_sec_01_cross_patient_fails_before_returning_any_data` (asserts `E_SCOPE_VIOLATION`), `test_history_rejected_unit_and_future_are_excluded_never_baselines` | **satisfied** | Implementation symbol is `admissibility_reason`, contract name is `is_admissible_observation` — same behaviour, naming difference only (§4 C07) |
| **NEG-19** | Rejected observation used as a baseline → excluded, no comparison, no `DR-*` item | `test_history_rejected_unit_and_future_are_excluded_never_baselines`, `test_rb1_history_exclusions_remain_explicit`, RB2 R02, RB3 layered exclusions | **satisfied** | — |
| **SAFE-06** | Document patient mismatch → `VI-004` before any rule evaluation; cannot be verified away without explicit re-attribution + audit | P3: `test_p3_r02_*` (3 functions), `test_p3_edge_cases.py` VI-004 cases. P4 boundary: `test_p4_evidence_inspection.py::test_missing_and_foreign_current_never_leak`, `test_p5_run_gate.py::test_reassigned_patient_denied_before_any_gate_evidence` | **satisfied** | P3-owned evidence, re-verified at the P4 run gate |

### 2.5 Matrix D — `MASTER_PLAN.md` §5 P4 exit gate clauses

| Clause | Evidence | Status |
|---|---|---|
| Gold fixture rules have 100% expected pass/fail outcomes | A=0, B=exactly one DR-005 (self-reported, 12 mmHg), C=blocked pre-correction / clean after scripted correction, D=exact five ordered flags + 7 links; offline and run-backed | **satisfied** (as scoped by C-F0-C for C) |
| Zero unapproved external side effects | No HTTP route, no task, no notification, no approval, no graph, no LLM, no external messaging; RB3 writes only the three review tables; OpenAPI unchanged at 17 paths / 18 operations / 43 schemas | **satisfied** |
| Idempotency | `UNIQUE (workflow_run_id, dedupe_key)`, one evaluation per run, 8 replay-conflict reasons, atomic rollback, genuine-retry test | **satisfied** |
| Cross-patient isolation | `E_SCOPE_VIOLATION` before any data return; F0/F1/F2/RB1/RB3 cross-patient denials with zero writes | **satisfied** |
| Documented non-clinical limitation | `DEMO_REVIEW_RULES.md` §14 RB3 disclosure; every report carries the notice; `demo_only=1` structural | **satisfied** |
| Compare current vs baseline; handle repeated values, missing timestamps, changed units, outliers, contradictory inputs | Repeated → DR-008; missing timestamps → typed exclusion; changed units → non-comparable; outliers → DR-009; contradictory → DR-006 (pure evaluator) | **satisfied** |
| Generate de-duplicated review items with evidence and rule IDs; maintain reason codes and audit | Satisfied for DR-001/003/005/008/009; **DR-006 conflicts persist nothing** by owner-ratified prohibition; `document_span` evidence deferred | **partially satisfied** |

### 2.6 Matrix E — original expectations explicitly re-scoped by owner decision

| # | Original expectation | Re-scoping decision | Status |
|---|---|---|---|
| E1 | GOLD-C run halts `needs_verification` then resumes through the graph with a draft | **C-F0-C** ratified by `RATIFY-P4-RB4-…` (PR #44 comment 7108431644): F0 refusal + genuine post-selection F1 HALT + corrected **new** run | **superseded by explicit owner decision** (P4); the literal workflow remains a P5/P8 obligation |
| E2 | DR-006 review items persisted with both evidence refs | **D-RB3-08(ii)** conservative prohibition (PR #42 comment 7095039109; accepted PR #43 comment 7105580779) | **superseded by explicit owner decision** |
| E3 | `document_span` / `fact` evidence links per `DATA_DICTIONARY` §2.10 | RB3-75..77 declared future-extension; requires its own decision + migration | **deferred** |
| E4 | `GET /api/v1/doctor/review-items`, `GET …/{id}`, `POST …/decision` | Never implemented; `check_openapi.py` enforces 17 paths; API_CONTRACT §2.6 assigns dismissal UX to P6 (`OQ-A02`) | **deferred** — owner decision required (§4 C06) |
| E5 | Agent tools `compare_observations` (§3.5) and `evaluate_demo_review_rules` (§3.7) | C-35A / C-37A: internal-only; normative tool contracts unchanged | **deferred** (P5) |
| E6 | Runtime activation of `demo-policy-1.1.0` | R3-A: reference values only, **not** activation | **deferred** (§4 C02) |
| E7 | TRUST-01 draft half | Drafting is P5 | **outside P4 scope** |
| E8 | RULE-07 static import check | P7 | **outside P4 scope** |
| E9 | REQ-EVAL-02 / REQ-EVAL-03 | P7 / P5-P7 | **outside P4 scope** |

---

## 3. Accepted architecture trace F0 → F1 → F2 → RB1 → RB2 → RB3 → RB4

### 3.1 Layer-by-layer

| Layer | Responsibility | Key symbol | Trust boundary it establishes | Proves | Does **not** prove |
|---|---|---|---|---|---|
| **F0** run foundation | Server-generated `workflow_run`, patient/doctor scope, immutable `workflow_version` / `state_schema_version` / `policy_version` / `mapping_version`, stored `as_of_utc`, idempotency key, durable doctor-selected source manifest + omission records, scoped audit | `p5_run_foundation.py::create_run_foundation` (`:121`); `WORKFLOW_VERSION`/`STATE_SCHEMA_VERSION` `1.0.0`, `POLICY_REFERENCE_VERSION` `demo-policy-1.1.0`, `MAX_SELECTED_OBSERVATIONS` 20 | Authenticated assigned doctor ↔ synthetic patient; selection IDs are **not** permissions | Real run identity exists; replay returns the same run; wrong role/patient/dirty session denied with zero writes; manifest DB-immutable | That a graph ran; that the doctor's selection is clinically correct; any clearance |
| **F1** run-scoped verification gate | Recompute VI-001..006 from the persisted selection; persist immutable `run_gate_evaluation` + `run_gate_blocker`; `PROCEED`/`HALT`/`UNAVAILABLE`; VI-006 same-day constrained comparison | `p5_run_gate.py::evaluate_run_verification_gate` (`:887`), `::inspect_current_run_gate_locked` (`:857`), `_evaluate_locked` (`:198`), VI-006 `:608–660` | Selected-document set ↔ patient history; calendar-day UTC comparison; no caller-supplied blocker count | Genuine HALT with exact blockers; source drift invalidates an old PROCEED; concurrent attempts → one evaluation; tables/trigger-enforced immutability | That VI-006 equals DR-006 semantics (mechanism divergence is verified, §4 C01); that `PROCEED` is a runtime execution token |
| **F2** evidence bridge | Build frozen `EvaluableReviewEvidenceV2`: labelled facts, current observations, comparisons, exclusions, provenance; fresh read-only F1 recheck; always rolls back | `p5_evidence_bridge.py::build_run_evaluable_review_evidence` (`:430`); `CONTRACT_VERSION` `2.0.0`, `f2-history-365d-v1`, `HISTORY_LOOKBACK_DAYS` 365, `MAX_CURRENT_OBSERVATIONS` 6, `MAX_HISTORY_OBSERVATIONS` 100 | Server-owned evidence object; no caller gate/role/count flags; `runtime_evaluable=False`, `rules_executed=False`, `policy_status="unapproved"` | Deterministic labelled evidence; forged extra blocker rejected; stale/corrupt provenance never uses a cached PROCEED; frozen evidence cannot become a graph token | That rules ran; that anything is authorized; atomicity with the filesystem |
| **RB1** read-only run-bound preview | Reconstruct F1/F2 gates, derive 90-day policy-window comparison inputs from the manifest under the pinned clock; returns no DR flags, writes nothing | `p4_run_bound_preview.py::build_p4_run_bound_review_input_preview` (`:227`); `POLICY_LOOKBACK_DAYS` 90, `POLICY_CANONICAL_SHA256` `f3bdad3f…`, `POLICY_VERSION` `demo-policy-1.1.0` | Run identity + policy revision/hash; 90-day policy window vs F2's 365-day search — never conflated | Zero-selected → `no_current_selected`; >6 selected → deny, never truncate; source-file change denied, not cached; revoked doctor denied | A DR result; an execution token; atomicity across two sessions |
| **RB2** pure offline six-rule evaluator | Deterministic DR-001/003/005/006/008/009 over frozen fixture input; exact templates, ordering, dedupe, caps, typed failures | `p4_rb2_offline_rules.py::evaluate_p4_rb2_offline_fixture` (`:260`); `_PINNED_CLOCK` `2026-11-14T12:00:00Z`, `_ARITHMETIC_CONTEXT` | Pure function: no DB, disk, API, agent, graph, LLM, YAML, session | Exact rule semantics; fail-closed on malformed policy/data/clock; decimal-context independence; delimiter-collision rejection | Runtime authority; persistence; genuine provenance; that a fixture assertion equals a doctor verification |
| **RB3** durable run-bound persistence | One locked, revalidated transaction: reconstruct F2, run RB2, persist items + links + completion + audit; 25 triggers; immutable completion; exact replay | `p4_rb3_review_persistence.py::persist_run_review_items` (`:691`); constants `:116–123`; T12 `:1363–1364` | Fresh source/policy/session recheck immediately before write; `UNIQUE (workflow_run_id, dedupe_key)`; one evaluation per run; `dr006_policy='prohibited_denied'` | Atomic no-duplicate persistence; replay conflicts; `WITHOUT ROWID` closes hidden-identity replacement; audit completeness; empty-downgrade refusal | DR-006 persistence; `document_span` links; API/agent-tool exposure; clinical correctness |
| **RB4** genuine run-backed GOLD acceptance | Drive F0→F1→F2→RB1→RB2→RB3 on real migrated SQLite for A/B/C/D + negatives | `backend/tests/p4/test_p4_rb4_run_backed_gold.py` (12 tests) | Test-only; no production change | RB4-01 A zero candidates; 02 B exact DR-005 self-reported; 03 C F0 refusal; 04 C post-selection HALT; 05 C corrected new run PROCEED; 06 D exact ordered outputs + replay; 07 identity/scope/session; 08 semantic bridge equivalence; 09 drift denied without writes; 10 zero-selected/history admissibility; 11 blocked run zero RB2 calls; 12 migrated head + guards | Real OCR; real human verification; clinical validity; Windows execution of RB4-12 (Linux schema guard only) |

### 3.2 Boundary inventory — internal service vs public API vs agent tool

| Surface | Exists? | Enforcement | Consequence |
|---|---|---|---|
| Internal services (F0/F1/F2/RB1/RB2/RB3) | **Yes** — accepted, tested, merged | No HTTP route imports them; `check_openapi.py` enforces the exact path set | Behaviour is provable only at service level |
| Public HTTP API for review items | **No** | `check_openapi.py` `EXPECTED_PATHS` = 17 paths / 18 operations / 43 schemas; `openapi.phase0.yaml` lists 30 *proposed* paths including `/api/v1/doctor/review-items*` and `/api/v1/workflows*` | No external caller can read or decide a review item; NEG-16 unexecuted |
| Agent tools §3.4/§3.5/§3.7 | **No** | `TOOL_CONTRACTS.md` normative text unchanged; RB2 source asserts no agent import | The five-agent graph has no tool bindings yet (P5) |
| Graph / checkpoints / interrupt | **No** | No `backend/app/agents/**`, no LangGraph dependency in the P4 path | Halt/resume is not implemented (P5) |
| LLM / Ollama | **No** | No `backend/app/llm/**` | No draft, no model claim (P5) |

### 3.3 Cross-cutting invariants (verified, with the test that pins each)

1. **Auth/scope before data.** `test_req_sec_01_cross_patient_fails_before_returning_any_data`; `test_rb3_07_to_18_authority_session_scope_run_and_byte_tampering`; `test_rb4_07_identity_scope_and_session_boundaries`.
2. **Provenance/trust separation.** `test_f2_selected_self_reported_current_and_history_preserve_trust`; `test_rb3_79_97_98_provenance_stored_lineage_proved_superseded_facts_and_exclusion_bounds`; per-item `provenance_status='fixture_asserted'`, `stored_lineage_proved` 0/1.
3. **History eligibility.** `test_rb2_r02_single_document_lineage_excluded`; `test_rb2_r03_*`; `test_rb2_r05_unverified_fact_assertion_fails_closed`.
4. **Deterministic baseline.** `test_req_mon_01_case_b_uses_most_recent_prior_not_oldest`; `test_rb1_90_day_baseline_is_latest_prior_and_trust_retained`.
5. **Explicit clocks/policy versions.** `test_rb2_r01_coordinated_clock_override_fails_and_equal_offsets_normalize`; `test_rb1_fixed_reference_rejects_mutated_version_not_a_fallback`; `test_reference_has_exact_owner_pinned_sha256`.
6. **Exact rule semantics.** 39 RB2 rule functions + 17 candidate functions + 22 provenance functions.
7. **Immutable completion/replay.** `test_rb3_01_23_44…`, `test_rb3_i04_all_8_replay_conflicts…`, `test_rb3_i01_transaction_lifecycle…`.
8. **Audit integrity.** `test_rb3_91_115_116_117_g14_audit_completeness`; `test_rb3_59_to_65_70_92_111_to_114_128_replay_conflicts_and_audit_contract`.
9. **Transactions/migration safety.** `test_rb3_i02_atomic_rollback_flush_stages_commit_failure_t17_and_genuine_retry`; `test_rb3_29_30_31_127_migration_populated_refusal_and_empty_roundtrip`; `test_rb3_58_126_orm_migration_parity_and_autogenerate_blind_spot`.
10. **Stale-source / historical-evidence denial.** `test_rb4_09_selected_and_history_drift_denied_without_writes`; `test_f2_stale_or_corrupt_provenance_never_uses_cached_proceed`; `test_source_byte_drift_invalidates_old_proceed_receipt`.
11. **No unapproved side effects.** `test_no_io_run_api_or_agent_imports_in_pure_service`; `test_rb3_41_to_43_82_no_http_surface_no_caller_authority_and_model_fields`; OpenAPI 17/18/43.
12. **Internal-service vs public boundary.** §3.2 above; `check_openapi.py` equality assertion.

---

## 4. Unresolved points C01–C07

### C01 — DR-006: mandatory blocker or owner-ratified bounded deferral?

**Question.** Does the unresolved DR-006 situation block P4 closure?

**Verified facts.**
- RB2 implements DR-006 detection: `combinations(ordered, 2)` over all eligible rows of a measure type on **exact** `measured_at` equality, with distinct document **and** fact ids and an explicit strict `conflict_tolerance` (`p4_rb2_offline_rules.py:423–454`).
- F1's VI-006 is a **different mechanism**: it iterates **selected documents only** (`p5_run_gate.py:608`), constructs no candidate unless the document has exactly one `test_name`, one `report_date` and one verified `value` fact with a mapped alias and matching unit (`:617–628`), and compares on a **UTC calendar day** (`documents/issues.py:243–256`). F2's `source_reason` restricts `verified_document` rows to the selected document set (`p5_evidence_bridge.py:187–193`) and has **no** `report_date` requirement.
- Therefore genuine F1-PROCEED → DR-006 reachability is **unproven in both directions** (C-RB3-08). It also depends on extraction-time issue generation (VI-001..VI-005) and F1's selected-document preflight, which has not been fully traced.
- RB3 T12 denies the **entire** invocation: `409 E_VALIDATION`, reason `dr006_persistence_not_authorized`; `dr006_policy` is CHECK-pinned to `'prohibited_denied'`; never a subset, never a silently dropped item (`p4_rb3_review_persistence.py:1363–1364`).
- `GOLD-D.expected.json` records `expected_source_conflicts: 0` — a fixture property, **not** an invariant.
- The prohibition was **explicitly ratified**: `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` (PR #42 comment 7095039109, `2026-11-23T08:06:02Z`, design SHA `dabcebc7…`) selected option (ii); `OWNER-ACCEPT-P4-RB3` (PR #43 comment 7105580779) accepted the implementation.

**Assessment.** **Not a mandatory P4 blocker.** It is an owner-ratified, fail-closed scope reduction. The safety property holds regardless of reachability: whatever the evaluator emits, RB3 denies and writes nothing. The residual cost is a **loss of signal**, not a safety violation: a run whose evidence genuinely contains a verified-source conflict persists **no** review items at all. That is a real functional limitation and must be disclosed as such — it is not neutral, and it is not a pass.

**Mandatory vs deferred.** Deferred, with an open obligation: any future DR-006 persistence extension must first either construct a genuine PROCEED run reaching DR-006 through the accepted F1/F2 contracts, or prove from the accepted extraction/issue logic that none exists, and must supply genuine provenance evidence. **C-RB3-08 remains open.**

**Remaining owner decision.** Record in the acceptance marker that **MON-03 is accepted as pure-evaluator-only for P4**, that DR-006 persistence stays prohibited, and that C-RB3-08 stays open. No further engineering is required for P4 closure.

---

### C02 — Demo policy authority: test-only pinned reference vs runtime approval

**Question.** Is the demo policy an approved runtime authority, or only a pinned offline reference?

**Verified facts.**
- R3-A pins `demo-policy-1.1.0` with canonical-LF SHA-256 `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`, `demo_as_of_utc=2026-11-14T12:00:00Z`, `baseline_lookback_days=90`, `stale_measurement_days=30`, deltas systolic 10 / diastolic 8 / heart rate 15 / glucose 40, `ocr_confidence_floor=0.70`, `conflict_tolerance=0`, `max_items_per_type=3`; all six VI and all six DR switches true **in the offline reference catalogue** (issue #14 comment 7062063539).
- `validate_demo_policy` (`demo_policy.py:128`) is a strict **candidate** validator; it deliberately does not authorize a runtime policy and may structurally accept a disabled `VI-*` switch for testable invalid candidates.
- The YAML is **not imported by app runtime**: `test_p4_demo_policy_reference.py::test_reference_artifact_is_not_imported_by_app_runtime`; RB2 source contains no `demo_review_policy.yaml` reference (`test_no_io_run_api_or_agent_imports_in_pure_service`).
- RB1 pins `POLICY_VERSION` + `POLICY_CANONICAL_SHA256` and rejects a mutated version rather than falling back (`test_rb1_fixed_reference_rejects_mutated_version_not_a_fallback`, `test_rb1_fixed_comparison_reference_matches_offline_owner_seal`).
- OQ-R01 numeric approval is **reference-only**, explicitly not runtime activation.

**Assessment.** P4 closure does **not** require runtime activation, and no P4 decision grants it. The authority question is therefore **resolved for P4** (reference values ratified and byte-sealed) and **open for P5/P7** (whether and when a genuine run may use these thresholds).

**Mandatory vs deferred.** Deferred to P5/P7. **Do not activate.**

**Remaining owner decision.** None for P4 closure. For P5: a separate decision on whether `demo-policy-1.1.0` becomes the runtime policy of a genuine run, with its own version bump and fixture-impact review.

---

### C03 — RB3-75, RB3-76, RB3-77 individually

| Case | Definition | P4 blocker? | Why | What ratifying it would require |
|---|---|---|---|---|
| **RB3-75** | All six DR-006 evidence keys (`observation:first/second`, `document:first/second`, `fact:first/second`) map to six persisted links | **No — future-scoped** | It presupposes DR-006 persistence, which is prohibited by D-RB3-08(ii). Enabling 75 without that decision is meaningless and would widen a prohibited path | The DR-006 decision **plus** a migration relaxing G8, raising `evidence_link_count` to `0..72`, making `ux_evidence_link_span` effective, adding `dr006_policy='persisted'` |
| **RB3-76** | Exact stored document spans for `document:` / `fact:` references | **No — future-scoped** | `document_span` is reserved-but-unwritable (G8); `page_index`/`char_start`/`char_end` are reserved/NULL; only `observation` links are writable, so no span can be stored or resolved | A migration relaxing G8, span-resolution machinery, `EXTRACTION_PROVENANCE.md` §5 rule-1 assertion (`0 <= char_start < char_end <= len(page_text)` and exact text match), and the 72-link bound |
| **RB3-77** | Missing or unresolvable document span denies the whole invocation | **No — future-scoped** | Unreachable while `document_span` is unwritable; there is nothing to fail on | Must be implemented and tested **before** any span-writing extension ships; it is the safety gate for 76 |

**Assessment.** All three are recorded in the RB3 design (§7.2a, §11) and implementation review as **future-extension cases — never executed, never passed**. They must not be relabelled. The authorized structural maximum in this slice is **12 items × 2 observation links = 24 links**, asserted by RB3-99.

**Mandatory vs deferred.** Deferred, each requiring its own owner decision and migration.

**Remaining owner decision.** None for P4 closure. For the future: one combined decision covering 75+76+77, or an explicit decision never to implement them.

---

### C04 — P3 OCR limitation: four distinct things that must never be conflated

| Layer | What it is | Evidence | What it proves | What it does **not** prove |
|---|---|---|---|---|
| **(a) Recorded bytes** | Stored file SHA-256 / stored page text | F1 source fingerprint; `document_page_text` CHECKs; RB4-09 drift denial | Which bytes are stored, and that drift is detected | That the stored bytes match the physical source, or that a glyph was read correctly |
| **(b) Scripted correction** | Test-staged fixture state (a verification decision inserted by the test) | RB4-03/04/05 staged lineage | That the *logic* handles a corrected lineage deterministically | That a human corrected anything; that OCR succeeded |
| **(c) Actual OCR** | Real Tesseract execution | `GOLD-EX-11`: source glyph `1O5` read as `105`; exit 2; **27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED** | That a real false-clean recognition occurred and is reproducible | That the pipeline detects it (it does not) |
| **(d) Human interpretation** | A clinician reading the source | **Not performed, not recorded** | — | Anything |

**Effect on P4 closure.** P4's gold fixtures are **text-staged synthetic**, so the rule semantics are not invalidated by the OCR defect. But no claim may be made that an uploaded scanned report produces correct review items end-to-end. P4 acceptance is therefore **synthetic-educational only**, and `GOLD-EX-11 = FAIL / NOT PROVEN` must remain recorded verbatim. P4 does not reopen P3, does not waive the failure, and does not retest it.

**Mandatory vs deferred.** Not a P4 blocker; a permanent disclosed limitation until a real-OCR remediation phase is authorized.

**Remaining owner decision.** Confirm in the acceptance marker that P4 acceptance is synthetic-educational only and that GOLD-EX-11 remains FAIL / NOT PROVEN.

---

### C05 — GOLD-C reconciliation (C-F0-C)

**Ratified three-part reconciliation** (`RATIFY-P4-RB4-…`, PR #44 comment 7108431644; accepted PR #45 comment 7113168956):

| Part | Implemented | Test | Outcome |
|---|---|---|---|
| 1. Initial pending document | F0 refuses **before** run creation with `409 E_VALIDATION`; exactly three pending facts, P3 issue types, derived VI-002 count/message asserted | `test_rb4_03_gold_c_initial_pending_document_is_refused_before_run` | **satisfied** |
| 2. Post-selection deterioration on a genuine previously created run | Actual F1 HALT with **6 exact blockers** (VI-001×2, VI-002, VI-003×2, VI-005); RB3 denied; **zero RB2 calls**; zero review writes | `test_rb4_04_gold_c_controlled_post_selection_deterioration_halts`, `test_rb4_11_blocked_run_has_no_rb2_call_or_review_persistence` | **satisfied** |
| 3. Corrected source, **new** run | PROCEED; mixed delta 9 ≤ 40; 0 items; corrected-source lineage preserved | `test_rb4_05_gold_c_corrected_new_run_proceeds_zero_candidates` | **satisfied** |

**Original expectation vs implemented.** The original GOLD-C expectation — the run halts `needs_verification` and then **resumes** through the graph, producing a draft — is **unexecuted**. Graph-level halt/resume is P5 (`STATE_AND_GRAPH_CONTRACT.md` §5.2). P4 implemented the ratified decomposition instead. **Scripted correction ≠ OCR success**, and the new-run distinction is preserved (a correction creates a new run; the old run is not resumed).

**Status.** **superseded by explicit owner decision** for P4; the literal workflow remains a **P5/P8 obligation**.

---

### C06 — Service / API / agent-tool boundary

**Original P4-4 text (issue #14):** "*End-to-end service/API and golden fixtures*: patient/doctor scope; deterministic A/B/C and negative fixtures; idempotency, cross-patient denial, replay, zero unapproved side effects."

| Surface | Contract status | Implementation status | Assessment |
|---|---|---|---|
| Service-level end-to-end | Implied by P4-4 | **Implemented and accepted** (RB4, 12 tests, run-backed A/B/C/D + negatives) | Satisfied |
| `GET /api/v1/doctor/review-items` | `API_CONTRACT.md` §2.6; `openapi.phase0.yaml` (proposed) | **Not implemented**; no router; `check_openapi.py` enforces 17 paths | Unresolved |
| `GET /api/v1/doctor/review-items/{id}` | §2.6 | **Not implemented** | Unresolved |
| `POST /api/v1/doctor/review-items/{id}/decision` | §2.6 (dismissal reason deferred to P6 per `OQ-A02`) | **Not implemented** | Unresolved |
| `compare_observations` (§3.5) | Normative tool contract, unchanged | **Not implemented as a tool**; internal `compare_observation_history` / `compare_explicit_current_with_history` instead (C-35A) | Deferred to P5 |
| `evaluate_demo_review_rules` (§3.7) | Normative tool contract, unchanged | **Not implemented as a tool**; internal `evaluate_p4_rb2_offline_fixture` instead (C-37A) | Deferred to P5 |

**Assessment.** The owner ratified the **internal-service** route explicitly (R2-A / C-35A / C-37A, then RB1–RB4). The service half of P4-4 is therefore satisfied by decision. The **public read/decision API and the agent tools** are genuine unresolved P4 deliverables *or* deferred P5/P6 items — this is the one place where an owner could reasonably insist on completing P4 rather than deferring.

**Recommendation.** Defer: agent tools to **P5** (they are meaningless without the graph), and the review-item read/decision API to **P6** (API_CONTRACT itself assigns the dismissal-reason UX to P6 via `OQ-A02`, and MASTER_PLAN assigns the review-queue UI to P6). Exposing a read API now would require a new OpenAPI contract revision, NEG-16 negative tests, and a UI consumer — all P6 work. **But this must be an explicit owner decision, not an inference.**

**Remaining owner decision.** Choose one: (i) defer both to P5/P6 and record it in the acceptance marker; or (ii) require a bounded P4-4b read-only API slice before closure. Option (i) is recommended.

---

### C07 — Remaining evaluation requirements: literal contract vs equivalent safety outcome

| Item | Literal expectation | What is proven | Gap | Equivalent safety outcome? | Disposition needed |
|---|---|---|---|---|---|
| **RULE-03** denial semantics | `E_UNVERIFIED_FACT`, zero items | Typed `E_UNVERIFIED_FACT` from the pure evaluator; zero items; RB3 writes nothing on a blocked run | No HTTP `409` form exists (no API) | **Yes** — identical semantics, missing transport | Accept as-is; the HTTP form arrives with the P6 API |
| **RULE-05** malformed policy | `E_RULE_POLICY_INVALID`, zero items | 22 policy negative cases + RB2 typed failures; no partial output | None | **Yes** | Accept |
| **RULE-08** advanced clock | Same fixture at `+400 days` → `DR-003`; both runs record the as-of used | Pinned-clock stability; coordinated override rejected; unpinned run clock rejected; `DR-003` proven to depend on the explicit clock | The `+400 days` replay is **not executed** | **Stronger, not weaker** — an unapproved clock change is blocked outright, so a stale-clock evaluation cannot occur | Owner chooses: accept the substitution **or** authorize a pinned advanced-clock fixture test (small, test-only) |
| **RULE-04** prohibited wording | Scan **all** messages → zero prohibited terms | Exact templates for DR-003/005/006/008/009; `"worsen"` absent; trust suffixes asserted | No exhaustive table-driven scan across every template | **Partial** — coverage is spot-based, not total | Optional improvement §5.5 (test-only, no production change) |
| **TRUST-01** draft half | Draft renders `(self-reported)` and never "verified" | Review-item half proven | Draft does not exist | **Outside P4** | P5 |
| **TRUST-02** predicate naming | `is_admissible_observation` | Behaviour proven; symbol is `admissibility_reason` | Name only | **Yes** | Document the mapping; a contract edit needs owner authorization |
| **MON-03** run-backed | `DR-006` with both refs, persisted | Pure evaluator only | Persistence prohibited; reachability unproven | **Fail-closed, not equivalent** (signal loss) | §4 C01 |
| **RULE-07** | Static import check | A stronger P4-local import assertion exists | P7 scope | — | P7 |
| **REQ-EVAL-02/03** | Extraction metrics / runtime measurement | — | P7 / P5-P7 | — | P7 |

**Assessment.** No item in this table is an unresolved engineering defect. Two are genuine *literal* gaps (RULE-08 advanced clock, RULE-04 exhaustive scan) with equivalent-or-stronger safety outcomes; one is a real functional limitation (MON-03) that is fail-closed and owner-ratified; the rest are transport, naming or phase-scope differences.

---

## 5. Consolidated closure decision

### 5.1 Disposition lists

**Satisfied (behaviour asserted by an executed test at a named SHA):**
REQ-MON-01, REQ-MON-02, REQ-RULE-01, REQ-RULE-03, REQ-DATA-04, REQ-DATA-05, REQ-OPS-04 (clock injection/immutability), REQ-EVAL-01, REQ-SEC-06; P4-1, P4-2; RULE-01, RULE-02, RULE-03, RULE-05, RULE-06, MON-01, MON-02, TRUST-02, NEG-19, SAFE-06; MASTER_PLAN clauses: gold fixtures, zero unapproved side effects, idempotency, cross-patient isolation, non-clinical limitation, comparison robustness.

**Partially satisfied:**
REQ-MON-03 (DR-006 pure-evaluator only), REQ-RULE-02 (no exhaustive wording scan), REQ-SEC-04 (draft gate is P5); P4-3 (`document_span`/`fact` links + DR-006 persistence deferred), P4-4 (public API/agent tools unimplemented), P4-5 (no consolidated owner decision yet); RULE-04, RULE-08, MON-03, TRUST-01; MASTER_PLAN "de-duplicated review items with evidence" (DR-006 persists nothing; span evidence deferred).

**Not proven (no executed evidence either way):**
1. Genuine F1-PROCEED → DR-006 reachability (C-RB3-08, both directions).
2. Real OCR source-glyph fidelity (`GOLD-EX-11`).
3. Literal RULE-08 `+400 days` replay.
4. Exhaustive RULE-04 prohibited-term scan.
5. Actual human verification and the halt→resume→draft workflow.
6. Public API and agent-tool behaviour (no surface exists).
7. RB4-12 on Windows (Linux schema guard only).

**Deferred:**
RB3-75, RB3-76, RB3-77; runtime demo-policy activation; agent tools §3.5/§3.7; review-item read/decision API.

**Superseded by explicit owner decision:**
GOLD-C literal halt→resume workflow (C-F0-C); DR-006 persistence (D-RB3-08(ii)).

**Outside P4 scope:**
REQ-EVAL-02, REQ-EVAL-03, RULE-07, TRUST-01 draft half.

### 5.2 Approved scope changes (register)

| Change | Decision | Evidence | Effect |
|---|---|---|---|
| P4-3 persistence deferred until a genuine P5 run identity | **R1-A** | issue #14 comment 7007626056 | Broke the P4↔P5 FK cycle without a fake run or a weakened FK |
| Offline GOLD A/B/C/D component verification authorized while P4 stays IN_REVIEW | **R4** | issue #14 comment 7007626056 | Enabled P4-4 before run identity existed |
| Internal-only evidence inspection; §3.5/§3.7 not changed | **R2-A, C-35A, C-37A** | issue #14 comment 7009363266 | Kept the agent-tool boundary intact |
| DR-006/DR-008 conservative semantics | owner consent | issue #14 comment 7003513659 | Fixed source-independence and ordering semantics |
| `demo-policy-1.1.0` pinned as **reference only** | **R3-A** | issue #14 comment 7062063539 | Values ratified; activation withheld |
| Future doctor-authored source selection, offline inspector only | **R21-S1** | issue #14 comment 7062063539 | `doctor_selection_audited=False`; no run clearance |
| P4→P5 conditional sequencing exception | **CH-01** | issue #14 comment 7063634619 | Allowed P5-F0/F1/F2 as bounded slices before full P4 acceptance |
| RB1 read-only adapter scope | `RATIFY-P4-RB1-READONLY-INTEGRATION-SCOPE` | PR #36 comment 7075542080, `2026-11-22T06:48:34Z` | Eight-path allowlist; no DR result, no writes |
| RB2 offline six-rule scope | `RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE` | PR #38 comment 7076744806, `2026-11-22T08:48:05Z` | Pure evaluator only |
| RB3 durable persistence scope, incl. **D-RB3-08(ii)** | `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` | PR #42 comment 7095039109, `2026-11-23T08:06:02Z` | DR-006 prohibited; `observation` links only |
| RB4 run-backed GOLD scope, incl. **C-F0-C** | `RATIFY-P4-RB4-RUN-BACKED-GOLD-ACCEPTANCE-DESIGN-SCOPE` | PR #44 comment 7108431644, `2026-11-23T17:17:11Z` | C decomposition ratified |
| RB3 E1–E5 compatibility edits | five separate markers | PR #43 comments 7102514514, 7102522320, 7102527486, 7102533877, 7102539192 | Test/smoke/handoff compatibility only |
| RB4 P3 handoff collection-only note | `APPROVE-P4-RB4-P3-HANDOFF-COLLECTION-ONLY` | PR #45 comment 7111663704, `2026-11-23T19:28:46Z` | `1294 collected` / `443` pairing; not a pass claim |

### 5.3 Residual risks (ranked)

| # | Risk | Severity | Mitigation in place | Owner visibility |
|---|---|---|---|---|
| R1 | A genuine verified-source conflict persists **no** review items (DR-006 prohibition) | Medium — loss of signal, fail-closed | Whole-invocation denial; `dr006_policy='prohibited_denied'` in the receipt; DEMO_REVIEW_RULES §14 disclosure | **Must be named in the acceptance marker** |
| R2 | Review items cite observations only, not page spans (`document_span` deferred) | Medium — weaker doctor verifiability | RB3-75..77 recorded as future-extension; 24-link bound asserted | Must be named in the marker |
| R3 | No public API and no agent tools → no external end-to-end behaviour | Medium — the demo cannot be driven outside tests | Explicit deferral decision required (C06) | Must be named in the marker |
| R4 | Real OCR false-clean (`1O5`→`105`) remains undetected | High for any real-document use; **out of scope** for synthetic P4 | `GOLD-EX-11 FAIL / NOT PROVEN` preserved; P3 conditional acceptance is synthetic-educational only | Permanent disclosure |
| R5 | One evaluation per run: a correction requires a **new** run | Low — by design, preserves audit | New-run distinction tested (RB4-05) | Informational |
| R6 | `demo-policy-1.1.0` has no runtime authority | Low — no runtime exists | Reference-only; no runtime import | P5 decision |
| R7 | Evidence is Linux 3.11.2 + CI 3.12 + per-slice owner Windows, not one consolidated Windows run at a single head | Low — docs-only change | CI #45262091228 at the exact base is authoritative for the whole corpus | Disclosed in §1.3 |

### 5.4 Genuine mandatory blockers

**For a bounded conditional acceptance (B): none.**

**Would-be blockers for option A (all original exit requirements satisfied literally):**
1. MON-03 run-backed/persisted `DR-006` with both refs — prohibited and unproven.
2. RULE-08 literal `+400 days` replay — not executed.
3. RULE-04 exhaustive prohibited-wording scan — not executed.
4. Public review-item read/decision API + agent tools — not implemented.
5. `document_span`/`fact` evidence links — deferred (RB3-75..77).
6. TRUST-01 draft half — P5.

These are exactly why **A is not recommended**. None of them is an engineering defect: 1, 5 and 6 are owner-ratified or phase-scoped; 2 and 3 are verification-form gaps with equivalent-or-stronger outcomes; 4 needs a decision.

### 5.5 Optional improvements (none required for closure; all test-only unless stated)

| # | Improvement | Size | Risk | Recommended? |
|---|---|---|---|---|
| O1 | Table-driven prohibited-term scan over all six message templates (closes the RULE-04 literal gap) | Small, test-only | None | **Yes** — can be done in a P5/P7 test slice |
| O2 | Pinned `+400 days` DR-003 fixture test using a second fixed clock constant (closes the RULE-08 literal gap) | Small, test-only | None | **Yes** |
| O3 | Documentation-only trace of VI-001..VI-005 issue generation to settle C-RB3-08 reachability | Medium, docs-only | None | Yes, before any DR-006 extension |
| O4 | Document the `is_admissible_observation` ↔ `admissibility_reason` mapping in `TOOL_CONTRACTS.md` | Tiny, **contract edit — needs owner authorization** | Low | Yes, with authorization |
| O5 | Reconcile the stale status tables in `MASTER_PLAN.md` §5 and `PHASE_PROGRESS.md` (P4/P5 still "TODO") | Small, docs-only | None | Yes, append-only; do not rewrite history |

### 5.6 Recommendation

**B — bounded conditional academic acceptance.**

**Rationale.**
- **Not A:** six literal expectations are unmet (§5.4). Declaring A would require either fabricating evidence or silently re-scoping requirements — both prohibited.
- **Not C:** every gap is (i) an explicit owner-ratified conservative reduction that is fail-closed (DR-006, GOLD-C decomposition), (ii) a phase-scope assignment (draft, agent tools, API, RULE-07, EVAL-02/03), or (iii) a verification-form gap with an equivalent-or-stronger safety outcome (RULE-08, RULE-04). There is no reproducible correctness failure, no weakened assertion, no fabricated run id, gate decision, evidence receipt or evaluator output, and no unreviewed production change. Blocking would discard a complete, independently reviewed, CI-green, owner-accepted engineering corpus over documentation-form differences.
- **B is honest:** it accepts exactly what is proven, names every deferral, keeps the adverse statuses verbatim, and makes the residual obligations explicit conditions rather than footnotes.

### 5.7 Objective acceptance conditions for B

All seven must hold; the owner's marker is the evidence that they do.

1. **Scope confirmation.** The owner confirms P4-1, P4-2 (offline six-rule evaluator), P4-3 (authorized durable `observation`-link persistence) and P4-4 (service-level run-backed GOLD A/B/C/D + negatives) as implemented and merged through PR #45, with `main@96cb275` as the accepted base.
2. **Deferral register ratified.** The owner explicitly ratifies the deferral of: DR-006 persistence (D-RB3-08(ii)); RB3-75..77; agent tools §3.5/§3.7 (P5); review-item read/decision API (P6); TRUST-01 draft half (P5); runtime demo-policy activation (P5/P7).
3. **Equivalent-outcome substitutions ratified.** The owner accepts fail-closed clock immutability in place of the literal RULE-08 `+400 days` replay, and exact-template + spot wording assertions in place of the literal RULE-04 exhaustive scan — **or** authorizes O1/O2 as a follow-up test slice (recommended).
4. **MON-03 disposition.** The owner records MON-03 as pure-evaluator-only for P4 and C-RB3-08 as open for any future extension.
5. **OCR status.** The owner confirms `GOLD-EX-11 = FAIL / NOT PROVEN` remains recorded verbatim and that P4 acceptance is **synthetic-educational only**.
6. **Non-authorization.** The owner confirms the acceptance grants no runtime policy activation, no DR-006 persistence, no graph/LLM/API/UI/task/notification change, no P5 implementation, and no clinical use.
7. **Residual obligations assigned.** The owner assigns each deferred item to a named future phase or explicitly declines it.

### 5.8 Proposed owner acceptance marker and scope text — **PROPOSAL ONLY, NOT AUTHORIZATION**

The agent posts **no** marker. The following is a proposal for the owner to use, edit or reject.

**Marker:**

```
OWNER-ACCEPT-P4-BOUNDED-CLOSURE-B
```

**Proposed scope text:**

> Accepting Phase 4 as a **bounded conditional academic acceptance** at documentation head `<EXACT-PR-HEAD-SHA>` (base `main@96cb275136f9f80608709ce8c7d83693bffa36c3`), per `docs/phase-reports/P4_FINAL_CLOSURE_ASSESSMENT_20261123.md` §5.7 conditions 1–7.
>
> **Accepted as implemented:** P4-1 pure monitoring comparisons and shared admissibility; P4-2 offline deterministic six-rule evaluator with retired-ID prohibition and strict policy validation; P4-3 durable run-bound review persistence within the authorized `observation`-link slice (migration `0008`, 25 triggers, immutable completion, exact replay, complete audit); P4-4 service-level genuine run-backed GOLD A/B/C/D and negative acceptance.
>
> **Recorded as owner-ratified bounded deferrals, not passes:** DR-006 persistence prohibited (D-RB3-08(ii)) with genuine end-to-end reachability still unproven (C-RB3-08 open); RB3-75, RB3-76 and RB3-77 as future-extension cases, never executed; agent tools `compare_observations` and `evaluate_demo_review_rules` deferred to P5; review-item read/decision API deferred to P6; TRUST-01 draft half deferred to P5; runtime activation of `demo-policy-1.1.0` not authorized.
>
> **Recorded as equivalent-outcome substitutions:** fail-closed clock immutability in place of the literal RULE-08 advanced-clock replay; exact-template and spot wording assertions in place of the literal RULE-04 exhaustive scan.
>
> **Status:** P4 = `CONDITIONALLY_ACCEPTED_SYNTHETIC` — **not PASS**, not clinical, not OCR-proven. `GOLD-EX-11` remains **FAIL / NOT PROVEN**. Full P5 remains **NOT ACCEPTED**. No graph, LLM, API, UI, task, notification, migration, policy activation or DR-006 persistence is authorized. Issue #14 remains open at the owner's discretion for the residual obligations. No agent merge, auto-merge, direct main edit or self-approval.

---

## 6. P5 readiness review — **PLANNING ONLY**

Nothing in this section is a design, an implementation, a graph, an LLM integration or a runtime activation. It is a readiness inventory and a proposed slicing order, to be used **only after** an explicit P4 closure decision **and** a separate P5 authorization.

### 6.1 Reusable accepted components

| Component | Reuse in P5 | Caveat |
|---|---|---|
| F0 `create_run_foundation` | Run identity, immutable versions/clock, durable selection manifest, idempotency | `run_id` must equal the LangGraph `thread_id`; F0 already stores it |
| F1 `evaluate_run_verification_gate` | The N2 verification node's gate; `HALT`/`PROCEED` with exact blockers | A cached `PROCEED` is never permanently fresh — F2 rechecks |
| F2 `build_run_evaluable_review_evidence` | The server-owned evidence object every downstream node consumes | Always rolls back; `runtime_evaluable=False`; not a token |
| RB1 preview | Debug/inspection view of 90-day policy inputs | No DR result; not a graph transition |
| RB2 evaluator | The `evaluate_demo_review_rules` tool's implementation core | Must be wrapped, not called directly by an agent |
| RB3 persistence | Durable review items + evidence + audit | One evaluation per run; DR-006 prohibited |
| `monitoring.py`, `p4_explicit_history.py` | The `compare_observations` tool's implementation core | Must be wrapped with server-derived scope |
| `p4_readonly_provenance.py`, `p4_document_preflight.py`, `p4_evidence_inspection.py`, `p4_recovery_selection_candidate.py` | Source/lineage inspection inside the document node | `doctor_selection_audited=False` — P5 must persist the doctor's authored selection |
| `demo_policy.py` + pinned reference | Policy loading/validation for a genuine run | **Reference only** — activation needs its own decision |
| GOLD A/B/C/D + RB4 harness | P5/P7 end-to-end evaluation fixtures | Text-staged; not OCR |
| Migrations `0001..0008`, audit discipline, trigger-based immutability | Pattern for P5 checkpoint/finalize tables | New tables need their own decision and parity assertions |

### 6.2 Remaining P5 scope, mapped to contracts

| P5 scope item | Contract source | Current state | P5 work |
|---|---|---|---|
| LangGraph typed state | `STATE_AND_GRAPH_CONTRACT.md` §3 | **Not implemented** — no `backend/app/agents/**` | Typed state models, caps, schema unit tests |
| Authorized tool adapters | `TOOL_CONTRACTS.md` §3.4–§3.10 | **Not implemented** — §3.5/§3.7 unchanged | Thin wrappers over accepted services; server-derived scope; no caller gate flags |
| Verification halt/resume | §5.2 (interrupt at N2/N6) | **Not implemented** — F1 can HALT, but no graph interrupt exists | N2 interrupt wiring; resume validation; re-interrupt on unchanged blockers |
| Durable checkpoints / restart | §5.1, §7.3 | **Not implemented** — no checkpointer | `langgraph-checkpoint-sqlite`, app-DB-first ordering, restart reconciliation |
| Local model interface + fallback | `LLM_ADAPTER.md` §2 | **Not implemented** — no `backend/app/llm/**` | `OllamaProvider` + `DeterministicFallbackProvider`, provenance metadata |
| Evidence-grounded drafts | `LLM_ADAPTER.md` §3, `TOOL_CONTRACTS.md` §3.8 | **Not implemented** | Citation-only grounding, abstention on unverified facts |
| Structured output validation | `LLM_ADAPTER.md` §3 rule 8 (deterministic validation), §5 (failure/degradation matrix); `STATE_AND_GRAPH_CONTRACT.md` §6 (retry matrix) | **Not implemented** | JSON-schema validation, one repair attempt, labelled fallback |
| Human approval boundary | §5.2, §5.3 | **Not implemented** | N6 interrupt; only `POST /decisions` creates tasks; no client-supplied facts |
| Orchestration / five bounded agents | `ADR-0006`, `MASTER_PLAN` §2.2 | **Not implemented** | Single graph, bounded tools, no agent-to-agent chat |
| Benchmark measurement | `LOCAL_BENCHMARK_PLAN.md` | **Not measured** | `EVAL-03`, `BENCH-01..04`, `OCR-LIVE-01` — owner laptop only |

### 6.3 P5 / P6 / P7 / P8 separation

| Phase | Owns | Must **not** absorb from P5 |
|---|---|---|
| **P5** | Graph, typed state, tool adapters, checkpoints/interrupt/resume, LLM adapter + fallback, grounding, output validation, approval boundary | No review-queue UI, no timeline UI, no browser E2E, no extraction-accuracy metrics, no demo packaging |
| **P6** | Doctor dashboard (patient list, timeline, extraction review, review queue, run timeline, grounded summary, edit/approve/reject, task scheduler), patient check-in/upload, RBAC routes, notifications/tasks from approved actions | No rule logic, no LLM calls, no new persistence semantics |
| **P7** | Integrated robustness/safety evaluation: extraction accuracy, provenance completeness, false review flags, grounding, approval enforcement, latency, offline recovery, attack cases, threat-model evidence, honest limits | No new features; evaluation only |
| **P8** | Three demo stories, one-command startup, deterministic reset, architecture/API docs, screenshots, script, troubleshooting, handover | No new behaviour |

### 6.4 Proposed slice sequence (each slice: separate branch/PR, own tests, exact-head CI, owner Windows, owner merge)

**Entry condition for every slice:** an explicit P4 closure decision **and** a separate P5 authorization naming the slice's exact file allowlist. No slice may start on the strength of this document.

| Slice | Scope | Exit evidence | Explicitly excluded |
|---|---|---|---|
| **P5-S0** | Contract reconciliation + typed state models + schema unit tests; **no graph** | State schema tests pass; no runtime path | Any node, edge, checkpoint or tool |
| **P5-S1** | Tool adapters `compare_observations`, `evaluate_demo_review_rules` as thin wrappers over accepted services | Deterministic outputs equal the service outputs; server-derived scope; no caller flags | Graph wiring |
| **P5-S2** | Orchestrator skeleton + N1/N2 gate wiring to F1 + checkpoint persistence; **no LLM** | A run reaches `needs_verification` with exact blockers and survives a hard kill | Draft node, approval |
| **P5-S3** | LLM adapter interface + deterministic fallback + structured output validation + grounding | Labelled fallback; schema-invalid output repaired once then fallback; citations resolve | Approval, tasks |
| **P5-S4** | N6 interrupt/resume + restart reconciliation + two-phase finalize | Resume from restart; idempotent finalize; no duplicate task | UI |
| **P5-S5** | End-to-end gold summaries + benchmark measurement | `EVAL-04`, `AD-01`, `BENCH-01..04` measured or explicitly marked not measured | P6 UI |

**Recommended first slice after authorization: P5-S0**, because every later slice depends on the typed state and because it carries zero runtime risk.

### 6.5 P5 non-goals / prohibitions (carry forward verbatim)

- No diagnosis, risk score, triage, urgency, treatment, prescription or personal medical guidance.
- No external messaging (SMS/WhatsApp/email); in-app records only.
- No client-supplied clinical facts, observation values, evidence, `force=true`, `approved=true`, role or gate flags.
- No task creation except through `POST /decisions`.
- No phase PASS, no agent merge, no self-approval, no direct `main` edit.
- No model weights or large artefacts committed.
- `GOLD-EX-11 = FAIL / NOT PROVEN` stays recorded; P5 must not claim OCR fidelity.

---

## 7. Verification performed for this document

| Check | Command / method | Result |
|---|---|---|
| Repo identity | `git remote -v`, `git rev-parse origin/main` | `96cb275136f9f80608709ce8c7d83693bffa36c3` |
| Merge identity | `gh api pulls/45` | merged, `2026-11-23T20:42:08Z`, `merge_commit_sha=96cb275…` |
| Tree equality | `git rev-parse <sha>^{tree}`; `git diff 679ccb5 96cb275` | identical trees; empty diff |
| Post-merge CI | `gh api actions/runs/45262091228` + jobs | COMPLETED / SUCCESS; Backend 14/14, Frontend 11/11 |
| Owner acceptance | `gh api issues/comments/7113168956` | `OWNER-ACCEPT-P4-RB4`, OWNER, never updated |
| Issue state | `gh api repos/.../issues/14` + comments | `open`, 19 comments |
| Branch creation | `git checkout -b arena/a61b8893-p4-final-closure-assessment 96cb275…` | exit 0, clean |
| Scanner | `python3 scripts/python/scan_repository.py` (system Python 3.11.2) | **PASS** — `Secret/artefact scan: PASS (298 tracked files; 7 secret patterns, 4 claim patterns)`, **exit code 0** (297 tracked files before this document) |
| Test suites | **not executed** for this docs-only change | NOT RUN — no claim |
| Python 3.12 | not available; not retried | disclosed deviation (§1.3) |
| Alembic / OpenAPI / ruff / pytest locally | no virtual environment in this sandbox | NOT RUN — CI #45262091228 is authoritative |

---

## 8. Exact changed paths

1. `docs/phase-reports/P4_FINAL_CLOSURE_ASSESSMENT_20261123.md` — **new** (this document).
2. `docs/phase-reports/PHASE_4_REPORT.md` — **append-only**.
3. `docs/roadmap/PHASE_PROGRESS.md` — **append-only**.

No source, test, migration, model, policy, fixture, dependency, scanner, script, CI, contract, traceability, evaluation or historical-report file is changed. No production implementation. No P3 handoff edit.

---

## 9. Status preservation statement

P4 **IN_REVIEW** · issue #14 **OPEN** · full P5 **NOT ACCEPTED** · GOLD-EX-11 **FAIL / NOT PROVEN** · RB3-75..77 **deferred, never executed** · DR-006 persistence **prohibited** · DR-006 genuine end-to-end reachability **unproven in both directions** · runtime demo policy **not activated** · no graph, LLM, API, UI, task or notification implementation · no agent merge, auto-merge, direct main edit or self-approval.

**ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

---

## Appendix A — Test inventory relied on (function counts, not pass counts)

| File | Test functions | Primary requirements |
|---|---|---|
| `backend/tests/p4/test_p4_monitoring.py` | 15 | REQ-MON-01/02, REQ-DATA-04, TRUST-02 |
| `backend/tests/p4/test_p4_explicit_history.py` | 9 | REQ-MON-01/02, NEG-19 |
| `backend/tests/p4/test_p4_demo_policy.py` | 22 | RULE-05, REQ-RULE-01 |
| `backend/tests/p4/test_p4_demo_policy_reference.py` | 11 | REQ-OPS-04, REQ-EVAL-01 |
| `backend/tests/p4/test_p4_demo_rules_candidate.py` | 17 | REQ-RULE-01/02 |
| `backend/tests/p4/test_p4_dr009_candidate.py` | 18 | REQ-RULE-01/02 |
| `backend/tests/p4/test_p4_provenance_review_candidate.py` | 22 | REQ-MON-03 (DR-006/008) |
| `backend/tests/p4/test_p4_document_preflight.py` | 10 | REQ-SEC-04 |
| `backend/tests/p4/test_p4_evidence_inspection.py` | 9 | REQ-SEC-04, cross-patient |
| `backend/tests/p4/test_p4_readonly_provenance.py` | 7 | REQ-DATA-04 |
| `backend/tests/p4/test_p4_recovery_selection_candidate.py` | 19 | R21-S1 |
| `backend/tests/p4/test_p4_gold_abcd_offline_replay.py` | 9 | REQ-EVAL-01 |
| `backend/tests/p4/test_p4_run_bound_preview.py` | 13 | REQ-MON-01, REQ-OPS-04 |
| `backend/tests/p4/test_p4_rb2_offline_rules.py` | 39 | RULE-01..06, RULE-08, MON-01..03 |
| `backend/tests/p4/test_p4_rb2_gold_offline.py` | 7 | RULE-01, REQ-EVAL-01 |
| `backend/tests/p4/test_p4_rb3_review_persistence.py` | 18 | REQ-RULE-03, idempotency, audit |
| `backend/tests/p4/test_p4_rb3_migration_guards.py` | 7 | migration safety |
| `backend/tests/p4/test_p4_rb4_run_backed_gold.py` | 12 | run-backed A/B/C/D |
| `backend/tests/p5/test_p5_run_foundation.py` | 12 | F0 |
| `backend/tests/p5/test_p5_run_gate.py` | 21 | F1 |
| `backend/tests/p5/test_p5_evidence_bridge.py` | 14 | F2 |
| **Total P4** | **264** | — |
| **Total P5** | **47** | — |

Function counts are **not** pass counts. The authoritative executed statement is: full backend suite **passed** in CI #45262091228 at `main@96cb275` (count not printed by CI), and **1294 passed / 0 failed** on local Linux Python 3.11.2 at `9352835`/`679ccb5` (a Linux count, never a Windows count).
