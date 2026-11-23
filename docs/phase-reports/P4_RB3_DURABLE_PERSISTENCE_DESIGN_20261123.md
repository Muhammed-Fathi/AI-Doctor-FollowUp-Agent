# P4-RB3 — durable run-bound review persistence: independent design discovery and specification (owner decision requested)

**Status: DESIGN ONLY — PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED.**
**Revision 3 (2026-11-22): corrected in response to the independent reviewer findings RB3-R3-01…RB3-R3-10 plus the additional schema-precision questions. Revision 2 is superseded in full; the Revision 3 correction log is §0.2 (the Revision 2 log is retained at §0.1). No implementation exists and nothing here authorizes any.**

- Tracking: [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) (**OPEN**). P4 remains **IN_REVIEW**. Full P5 remains **NOT ACCEPTED**. Original real-OCR `GOLD-EX-11` (`1O5`→`105`) remains **FAIL / NOT PROVEN**.
- Scope of this PR: three documentation files only. No contract, application source, test, fixture, model, migration, dependency, policy, CI or scanner file is modified. Contracts are **reconciled by proposal**, never edited here.
- Base: the exact verified merged main `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`.
- **Branch-name deviation (honest):** the task proposes `docs/p4-rb3-durable-persistence-design`; the Arena session pins this work to `arena/91facff6-ai-doctor-followup-agent`, created from that exact verified main and carrying only the three documentation paths.
- **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

---

## 0. Independently verified merged-P4-RB2 checkpoint (executed in this session)

| Check | Verified result |
|---|---|
| PR #41 state | `MERGED`, `mergedBy = Muhammed-Fathi`, `mergedAt = 2026-11-22T23:20:55Z` |
| Accepted candidate SHA | `headRefOid = 8dd79ac0aa8fc626dcc9b4b7ecf3de3a8aedc888` |
| Merged main SHA | `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`, parents `eaab808b…` + `8dd79ac0…` |
| Tree equality | merged-main tree `2b083757d04cc202ca64523d25c8e87dcc4cd3fd` == candidate tree; empty diff |
| Owner acceptance marker | `OWNER-ACCEPT-P4-RB2`, [comment #7087501521](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087501521), `23:20:34Z`; **not** runtime activation, persistence, RB3/RB4 or P4/P5 acceptance |
| Permanent evidence report | [comment #7087467476](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087467476), `23:17:52Z`; "not an approval marker" |
| Post-merge main CI | [#45082770648](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45082770648) COMPLETED **SUCCESS**; every backend and frontend step SUCCESS |
| Rev-1 design CI (`684cf5e0…`) | [#45084736523](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45084736523) + [#45084687547](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45084687547) **SUCCESS** |
| Rev-2 design CI (`3d749648…`) | [#45087482596](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45087482596) + [#45087476153](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45087476153) **SUCCESS**, zero non-success steps |

RB2's acceptance is offline-only: the accepted evaluator is not a runtime clearance and conveys no RB3 authority.

### 0.1 Revision 2 correction log (retained; findings RB3-D01…RB3-D06)

RB3-D01 complete locked historical-evidence reconstruction → new §5 (fresh reconstruction T5, fresh exclusion derivation T6, `rb3-full-input-1.0.0` fingerprint, authority-scope table, sole-authoritative-snapshot decision). RB3-D02 invocation-level replay → new `review_evaluation` completion record (§6.3) and all thirteen replay cases (§8.2). RB3-D03 DTO/helper compatibility → field-to-source mapping (§2.4), corrected T1 precondition. RB3-D04 structural integrity → full immutability, exact trigger inventory, `length()` CHECKs, NULL-safe duplicate guard, ORM/migration parity, downgrade refusal. RB3-D05 audit identity → `ActorType.USER`, exact arguments, explicit content validation, no committed denial audit. RB3-D06 semantics → R03/R04/R07/R08 corrected, session ownership explicit, no wall-clock claim, race acknowledged, semantic retry equivalence, zero-item receipt distinction. Revision 1's "DR-006 structurally unreachable" claim was withdrawn.

### 0.2 Revision 3 correction log (findings RB3-R3-01…RB3-R3-10 and the §11 precision questions)

| Finding | Actual source evidence read in this session | Correction in Revision 3 |
|---|---|---|
| **RB3-R3-01** `rule_id` length | Every valid id (`DR-001`…`DR-009`) is **six** characters; the Revision-2 `length(rule_id) = 7` CHECK would reject every legitimate insert | §6.1 now specifies `length(rule_id) = 6`, enumerates all six valid ids in the closed CHECK, and §11 adds RB3-67 (all six accepted) and RB3-68 (retired `DR-002/004/007/010` and the seven-character assumption rejected) |
| **RB3-R3-02** audit FK insertion order | `review_evaluation.audit_event_id` is a NOT NULL FK; SQLite foreign keys are immediate by default and no deferred constraint is specified; `append_audit_event` adds **and flushes** its row internally, returning the actual event (`audit.py:130-146`) — so Revision 2's T15 order (completion row before audit row) was **impossible** | §3.2 T15 rewritten to the seven-step order (pre-generate `evaluation_id` → items → links → `append_audit_event(subject_id=evaluation_id)` → validate the returned row → insert `review_evaluation` with the returned `audit_event.id` → single commit). `audit_event.subject_id` has **no** FK (`models.py` AuditEvent; DD §2.17), which is why a pre-generated id is safe. Deferred-FK alternative evaluated and rejected (§8.4). New cases RB3-69/RB3-70 |
| **RB3-R3-03** zero selected current observations | `compare_explicit_current_with_history` requires `1 <= len(current) <= MAX_CURRENT` and raises `MonitoringInputError("E_VALIDATION", "Invalid current/history selection or window.")` otherwise (`p4_explicit_history.py:22-23`, `:…` bound check); RB1 returns early on an empty selection (`p4_run_bound_preview.py:185-188`) | §3.2 T8 split into T8a (empty selection: **do not call** the comparison helper; assert RB1's `no_current_selected` semantics and empty comparisons) and T8b (non-empty: call it). The unchanged RB2 evaluator still receives the empty `selected_current` tuple; durable zero-item completion and the receipt distinction are preserved. New case RB3-71 exercises the **complete** path, not the evaluator alone |
| **RB3-R3-04** complete fresh exclusion equivalence | The actual F2 `source_reason` (`p5_evidence_bridge.py:183-233`) does far more than `admissibility_reason` + loader lineage exclusions: verified-document lineage identity, `source_document_id ∈ doc_set` (**selected** documents), stored verified `value`-fact identity (patient/document/field/status), exactly one verified `test_name` fact with a normalized value, `MAPPING_TABLE` alias validity with measure-type and unit equality on **both** the observation and the fact, and stored trust/source consistency for `seed_fixture`/`patient_checkin` | §5.3 now specifies the complete T6 derivation reproducing that contract from stored evidence through public interfaces only, enumerates **every** resulting exclusion code (`verified_lineage_unavailable`, `verified_mapping_unproven`, `stored_trust_source_mismatch`, plus the `admissibility_reason` codes and the loader's `verified_lineage_unavailable`), and keeps cached sets as cross-checks only. New cases RB3-72/RB3-73/RB3-74 |
| **RB3-R3-05** DR-006 reachability fixture | `source_reason` excludes any `verified_document` row whose `source_document_id` is **not** in the selected document set (`:187-193` → `verified_lineage_unavailable`), so Revision 2's "two non-selected source documents" fixture **cannot reach the evaluator** | §7.4 withdraws that fixture. The narrowed mechanism is stated (both documents selected, both passing F2's mapping checks, both failing F1's VI-006 shape gate at `p5_run_gate.py:622-628` — which requires exactly one `test_name`, one `report_date` and one verified `value` fact — while F2's `source_reason` has **no** `report_date` requirement). Because constructibility also depends on extraction-time issue generation that this design has not fully traced, reachability is declared **UNPROVEN in both directions** and no fixture is invented; RB3-66 becomes a proof obligation plus a unit-level case |
| **RB3-R3-06** DR-006 evidence mapping and the structural maximum | `_flag` builds `refs = tuple(sorted({*(f"observation:{row.id}" for row in rows), *extra_evidence}))` (`:160`); DR-006 passes `rows=(first, second)` **and** four extra document/fact refs (`:434-445`) → **six** keys. Per-call-site ref counts: DR-001 `(current,)`=1 (`:349-353`), DR-003 `(newest,)`=1 (`:366-370`), DR-005 `(baseline, current)`=2 (`:396-401`), DR-006=6, DR-008 `(first, second)`=2 (`:473-477`), DR-009 `(current,)`=1 (`:413-417`) | §7.2 corrected to **six** links for DR-006 (two `observation` + two document-source spans + two fact-value spans); the structural maximum is corrected from 96 to **72** (12 items × 6 refs, derived from all six call sites), applied to `evidence_link_count` in §6.3 and to RB3-80 |
| **RB3-R3-07** extraction span contract | `EXTRACTION_PROVENANCE.md` §5 requires `document_span` to carry `document_id`, `page_index`, `char_start`, `char_end`, and rule 1 requires `char_end > char_start`, a bound of `max_page_text_chars` (default 20,000) and `span_is_resolvable`'s exact substring equality `page_text[char_start:char_end] == raw_text[:300]`; the public helper is `span_is_resolvable(pages, fact)` (`documents/field_parser.py:555-566`, exported `:575`). The stored `ExtractedFact` CHECK `span_ordered` is **weaker** (`char_end >= char_start`, `models.py`) | §7.1 removes NULL spans for `document_span` entirely: `document:<id>` → the stored verified **`test_name`** fact's exact resolvable span; `fact:<id>` → the stored verified **`value`** fact's exact resolvable span; missing or unresolvable span denies the **whole** invocation; no coordinate is ever fabricated. §6.2 adds a kind-conditional CHECK making all three span columns NOT NULL for `document_span` with strict `char_end > char_start`, and reconciles DD §2.10 with §5 explicitly (**no contract amendment needed** — §2.10's NULL-ability serves the non-span kinds and its own CHECK text already says "`document_id`+span"). A first-class `fact_id` column is raised as amendment decision **C-RB3-07** |
| **RB3-R3-08** per-item provenance honesty | `OfflineRuleFlag.provenance_status = "fixture_asserted"` is emitted per flag; the Revision-2 `review_item` schema did not store it, `review_evaluation.lineage_state` was a single global value, and `output_identity_sha256` omitted it — contradicting the claim that persisted DR-006 items carry the evaluator's `provenance_status` | §6.1 adds an additive per-item `provenance_status` column (evaluator literal stored verbatim, closed CHECK) — **Option A**, recommended; §8.1 includes it in the output identity; the over-claiming global `lineage_state` is **replaced** by `lineage_label_policy` (§6.3), a truthful statement of which ratified boundary option applied, never a claim that every observation has verified document lineage. Option B is specified and rejected with reasons. New owner decision **D-RB3-10**; C-RB3-01 stays explicitly unratified |
| **RB3-R3-09** actual reason codes | The six literals at the `_flag` call sites are `missing_baseline` (`:350`), `measurement_stale` (`:367`), `change_exceeds_demo_parameter` (`:397`), `verified_source_conflict` (`:447`), `duplicate_or_out_of_order` (`:474`), `implausible_value` (`:414`) | §6.1's closed CHECK now lists exactly these six (no deferral); DR-001 is corrected to mean **missing baseline**, not "no current measurement"; the per-flag evidence bound is derived from all six call sites (max 6) and C-RB3-06 is closed. New cases RB3-78/RB3-79 |
| **RB3-R3-10** Phase 1 transaction claims and E6 | `build_run_evaluable_review_evidence` executes `db.rollback()` in a `finally` block with the comment "Even a successful F2 read is never an implicit SQLite commit" (`p5_evidence_bridge.py:470-473`); its docstring says "Always ROLLBACK". `inspect_current_run_gate_locked` already has **two** callers: F2's `_projection` (`:88`) and RB1's `_policy_projection_locked` (`p4_run_bound_preview.py:101`) | §3.2 P2 corrected: F2 performs a **locked, read-only projection that always rolls back** and writes nothing. §3.4 E6 corrected: RB3 would be an **additional (third)** caller, not the second; E6 remains separately authorized and docstring-only |
| **§11 precision** | `0006…:133-136` literal-pinning and `length()` CHECK precedents; `audit_event.subject_id` has no FK; partial unique indexes on all-NOT-NULL columns are fully effective | `review_evaluation.policy_reference_sha256` is now **structurally pinned** to the exact R3-A digest (sub-decision **D-RB3-05e**); G14 and the audit verification sequence are confirmed still valid under the corrected T15 (§6.4, §8.4); the output identity now includes every persisted semantic field including `provenance_status` (§8.1); the corrected span mapping is shown compatible with G11 — and, because spans become mandatory, the NULL-distinctness gap **closes** for every RB3-writable kind, so the partial unique indexes alone suffice and G11 is retained as defence-in-depth (§6.5); the one-evaluation-per-run invariant is re-confirmed for zero-item and changed-input cases (§8.2) |

---

## 1. Actual repository findings (read in this session, resolved from the merged tree)

### 1.1 Governing documents read

`AGENTS.md`; `docs/contracts/DATA_DICTIONARY.md` (§§2.7–2.10, 2.16–2.18, 2.21, 3.1–3.3, 5.1); `STATE_AND_GRAPH_CONTRACT.md`; `TOOL_CONTRACTS.md` (`:270`, `:279`); `EXTRACTION_PROVENANCE.md` (§5 provenance-record table and rules 1–5, §6 verification workflow); `docs/clinical-safety/DEMO_REVIEW_RULES.md` (`:81`, `:123`, `:125`, `:135`, `:161`); `docs/evaluation/GOLD_FIXTURES.md`; the P4 integration/RB1/RB2 design and implementation reviews; the P5 F1/F2 designs; `PHASE_3_WINDOWS_ACCEPTANCE.md`; `PHASE_4_REPORT.md`; `PHASE_PROGRESS.md`; `data/synthetic/golden_cases/GOLD-D.expected.json`; `data/synthetic/policy/demo_review_policy.yaml`.

### 1.2 Merged source actually inspected (facts that shape this design)

| Area | Path | Facts relied on |
|---|---|---|
| F0 run foundation | `p5_run_foundation.py` | `WORKFLOW_VERSION = "1.0.0"` (`:40`), `STATE_SCHEMA_VERSION = "1.0.0"` (`:41`), `POLICY_REFERENCE_VERSION`; persisted on `workflow_run` (`:279-285`) |
| F1 gate | `p5_run_gate.py` | `GATE_VERSION = "1.0.0"` (`:71`, exported `:929`); `MAX_GATE_FACTS = 40`, `MAX_GATE_OBSERVATIONS = 100` (`:72-73`); `RunGateReceipt` fields (`:87-101`); `_authorize` (`:141-168`) proves stored session **ownership** (`UserSession.user_id == principal.user_id`), `revoked_at IS NULL`, `created_at <= at < expires_at`, doctor role, `is_active == 1`, `data_source == 'synthetic_fixture'`, `require_assigned_patient`; run-version denial (`:276-282`); manifest bounds (`:234`); snapshot covering the run row, documents (`:305`), facts (`:361`), decisions (`:384`), issues (`:485`), **every column of every patient observation** (`:531-562`, `order_by(id)`, `limit(101)`, `>100 → too_many_patient_observations`), omissions (`:683`) and policy settings; byte re-hash (`:733`) then `fingerprint = _sha(snapshot)` (`:736`); **VI-006 loop over selected documents only** (`:608` `for doc_id in doc_ids`) with a shape gate that `continue`s unless exactly one `test_name`, one `report_date` and one verified `value` fact exist and the alias maps with a matching unit (`:617-628`), then same-UTC-day comparison at `conflict_tolerance` (`documents/issues.py:217-258`); `inspect_current_run_gate_locked` (`:857-884`) requires `db.in_transaction()`, raises unless PROCEED with no issues, and its docstring says "Only the F2 bridge may call this"; `evaluate_run_verification_gate` (`:887-925`) requires a fresh clean Session (`:905`) and maps `OperationalError` on `BEGIN IMMEDIATE` to `503 E_VALIDATION` (`:913-917`) |
| F2 evidence bridge | `p5_evidence_bridge.py` | `CONTRACT_VERSION = "2.0.0"` (`:46`, exported `:475`); `COMPARISON_HISTORY_VERSION = "f2-history-365d-v1"`, `HISTORY_LOOKBACK_DAYS = 365`, `MAX_CURRENT_OBSERVATIONS = 6`, `MAX_FACTS = 40`, `MAX_HISTORY_OBSERVATIONS = 100` (`:47-52`, **not** exported); `_projection` calls `inspect_current_run_gate_locked` (`:88`) and requires a stored PROCEED row matched on `gate_version` **and** `input_fingerprint_sha256` (`:96-105`); verified-fact projection with patient-scope and bound checks (`:150-171`); provenance load (`:173-181`); **`source_reason` (`:183-233`)** — for `verified_document`: `source_fact_verification_status == 'verified'`, non-empty `source_fact_id`, **`source_document_id ∈ doc_set` (the selected documents)**, `trust_level == 'doctor_verified'`, else `verified_lineage_unavailable`; then the stored `value` fact must exist with matching patient, matching `document_id`, `field_name == 'value'`, `verification_status == 'verified'`, else `verified_lineage_unavailable`; then **exactly one** verified `test_name` fact with a normalized value (`.limit(2)`), else `verified_mapping_unproven`; then the normalized alias must be in `MAPPING_TABLE` with `mapped[0].value == observation.measure_type` **and** `mapped[1].value == observation.unit` **and** `mapped[1].value == source_fact.unit`, else `verified_mapping_unproven`; for `patient_checkin`/`seed_fixture`: `trust_level == 'self_reported_validated'` and `source_fact_id is None`, else `stored_trust_source_mismatch`; any other source → `stored_trust_source_mismatch`. **No `report_date` requirement exists in `source_reason`.** Selected-current proof (`:236-276`), fresh history/exclusion derivation (`:278-295`), 365-day comparison (`:301-308`) with `compared.excluded_history` refusal (`:310-311`), final locked gate re-check and byte re-hash with the comment "Filesystem and DB are not jointly transactional" (`:330-344`), fingerprint payload (`:348-403`) whose `observations` member is **projected current only** (`:378-389`, no `created_at`) with history present only via `comparisons` (`:390-399`), `history_exclusions` (`:401`) and `historical_issues` (`:402`); returned DTO exposes the four run version fields, `gate_version` and both fingerprints (`:405-428`); **`build_run_evaluable_review_evidence` always rolls back** in `finally` (`:470-473`) — it writes nothing |
| P4-2e read-only provenance | `p4_readonly_provenance.py` | `MAX_OFFLINE_ROWS = 100` (`:31`); `ReadonlyProvenanceEvidence(records, lineage_exclusions, patient_id, as_of_utc)` (`:34-41`); `load_readonly_provenance_evidence` (`:143-215`) re-proves doctor/assignment/synthetic scope, reads `order_by(measured_at DESC, id)` `limit(101)` refusing `>100`, and per row returns `CandidateRecordedObservation(observation=ObservationSnapshot(id, patient_id, measure_type, value, unit, measured_at, validation, trust_level), created_at, source, source_fact_id, source_document_id, source_fact_verification_status)`, adding `verified_lineage_unavailable` exclusions for `verified_document` rows lacking stored lineage (`:188-208`); all three names public (`:221`) |
| RB1 preview | `p4_run_bound_preview.py`, `schemas/p4_run_bound_preview.py` | `POLICY_CANONICAL_SHA256 = f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`, `POLICY_VERSION = "demo-policy-1.1.0"`, `POLICY_LOOKBACK_DAYS = 90` (`:37-39`); `_pinned_policy()` (`:48-87`); `_policy_projection_locked` calls `inspect_current_run_gate_locked` (`:101`), re-checks the gate fingerprint and `evidence.gate_version` (`:108-112`), pins run identity/policy/clock (`:114-125`), re-reads the immutable selection with a ≤6 bound (`:127-140`), loads provenance (`:142-150`), **uses F2's cached `history_exclusions` as `excluded_ids`** (`:152-158`), proves selected stored values (`:160-183`), **returns early on an empty selection after asserting `no_current_reason == 'no_current_selected'` and empty comparisons** (`:185-188`), builds `history_rows` by subtracting cached ids (`:190-194`), recomputes 90-day comparisons and refuses unreported exclusions/incomplete comparisons (`:195-206`); `__all__ = ["POLICY_VERSION", "build_p4_run_bound_review_input_preview"]`; the preview DTO exposes no version fields and hard-codes `runtime_evaluable=False`, `rules_executed=False`, `policy_status='unapproved'`, `review_items_persisted=False` (schema `:54-57`) |
| Comparison helper | `p4_explicit_history.py` | `MAX_CURRENT = 6`, `MAX_HISTORY = 100` (`:22-23`); `compare_explicit_current_with_history(*, current, history, patient_id, as_of_utc, baseline_lookback_days)` requires **`1 <= len(current) <= MAX_CURRENT`**, `len(history) <= MAX_HISTORY` and `0 <= baseline_lookback_days <= 365`, else `MonitoringInputError("E_VALIDATION", "Invalid current/history selection or window.")`; rejected/malformed current readings return a typed not-admissible response, malformed history is excluded and never becomes a baseline, duplicate ids (including cross-set) fail closed |
| RB2 offline evaluator | `p4_rb2_offline_rules.py`, `schemas/p4_rb2_offline_rules.py` | Sole export `evaluate_p4_rb2_offline_fixture` (`:503`); `_RULES` = the six DR ids (`:53`); decimal context `prec=28` (R08, `:59`); `max_items_per_type` must be exactly `3` (`:112-113`); **`_flag` (`:150-174`)** builds `refs = tuple(sorted({*(f"observation:{row.id}" for row in rows), *extra_evidence}))`, refuses empty evidence (`:161-162`), and sets `dedupe_key = sha256("|".join((patient_id, rule, *refs, trust)))` (`:164`); `_valid_id` refuses `|`/control chars (`:176-188`); `_validate_row` denies foreign patients with `E_SCOPE_VIOLATION` (`:190-199`); `lineage_status` admits **only** `{unavailable, fixture_asserted}` (`:221-225`), `stored_independently_verified` documented as "a FUTURE RB3 server-side state" (schema `:67-69`) and asserted rejected in `tests/p4/test_p4_rb2_offline_rules.py:275`; provenance claims on non-document rows refused (`:226-229`); `pending`/`rejected` → `E_UNVERIFIED_FACT` (R05, `:236-243`); `_independent_fixture_source` requires `verified_document` + `doctor_verified` + `lineage_status == 'fixture_asserted'` + `source_fact_verification_status == 'verified'` + non-empty document and fact ids (`:247-257`); **exclusion emissions** — `missing_created_at` (R03, `:313-315`) and `verified_lineage_unavailable` for a `verified_document`/`doctor_verified` row that is not independently fixture-sourced (R02, `:316-321`); caps `selected_current > 6` / `history > 100` refused (`:272-274`); `ordered`/`selected`/`past`/`baseline` construction (`:330-345`); **six call sites with exact reason codes and evidence** — DR-001 `missing_baseline`/`data_quality`/`(current,)` (`:344-353`), DR-003 `measurement_stale`/`data_quality`/`(newest,)` (`:361-370`), DR-005 `change_exceeds_demo_parameter`/`change_to_review`/`(baseline, current)` (`:390-401`), DR-009 `implausible_value`/`data_quality`/`(current,)` (`:408-417`), DR-006 `verified_source_conflict`/`verification_needed`/`(first, second)` **plus** `document:first`, `document:second`, `fact:first`, `fact:second` (`:423-451`), DR-008 `duplicate_or_out_of_order`/`data_quality`/`(first, second)` (`:452-479`); DR-006 iterates `combinations(ordered, 2)` over **all** eligible rows of a measure type and requires identical `measured_at`, differing values, `_independent_fixture_source` on both, and distinct document **and** fact ids; per-measure dedupe then the cap check `E_RULE_POLICY_INVALID "Rule item cap exceeded."` (`:482-489`); ordering `(_HINT_ORDER[hint], rule_id, evidence, dedupe_key)` and exclusions sorted by `(observation_id, reason)` (`:490-499`); `OfflineRuleResult` frozen literals `runtime_evaluable=False`, `rules_executed=False`, `review_items_persisted=False`, `policy_status='unapproved'`; `OfflineRuleFlag.provenance_status = "fixture_asserted"` per flag |
| Span contract | `EXTRACTION_PROVENANCE.md` §5; `documents/field_parser.py`; `db/models.py` | §5 requires `document_span` → `document_id`, `page_index`, `char_start`, `char_end`; rule 1 requires `char_end > char_start`, a bound of `max_page_text_chars` (default 20,000) and `span_is_resolvable`'s exact equality `page_text[char_start:char_end] == raw_text[:300]` against the persisted `document_page_text` row; rule 2 states persisted OCR text is untrusted engine output; rule 4 states evidence references are immutable. Public helpers `span_is_resolvable(pages, fact)` (`:555-566`) and `page_text_for_span` with `CandidateFact` exported (`:568-576`). `ExtractedFact` stores `page_index`, `char_start`, `char_end`, `raw_text` with CHECKs `page_index >= 0`, `char_start >= 0 AND char_end >= char_start` (**weaker than §5's strict inequality**), `raw_text <> ''`, `length(raw_text) <= 300` |
| Audit | `audit.py`, `db/models.py`, `core/enums.py`, DD §2.17 | `SAFE_DETAIL_MAX = 500` (`:31`); vocabulary "Namespaced so P3+ can extend it additively" (`:33-40`); `derive_audit_key(event_type, actor_type, actor_id, outcome, subject_type, subject_id, request_id)` (`:49-74`) — **`request_id` is part of the key**; `safe_detail()` collapses and truncates (`:77-87`); `append_audit_event(...)` returns an existing row **by key alone without comparing content** (`:124-128`), otherwise constructs, `db.add`s **and `db.flush()`es** the row and returns it with its id populated (`:130-146`); `record_denial` **commits immediately** (`:170-190`); `ActorType = {USER, SYSTEM, DEMO_ADMIN}` — no doctor member; `AuditOutcome = {OK, DENIED, ERROR}`; `AuditEvent.event_type` is `String(48)` NOT NULL with **no** CHECK, `actor_type`/`outcome` are closed CHECKs, `idempotency_key` is `String(64)` UNIQUE, `safe_detail` is `String(500)`, `workflow_run_id` is FK RESTRICT, and **`subject_type`/`subject_id` carry no foreign key** |
| Errors | `core/errors.py` | `ErrorCode.IDEMPOTENCY_CONFLICT = "E_IDEMPOTENCY_CONFLICT"` exists, alongside `FORBIDDEN`, `SCOPE_VIOLATION`, `NOT_FOUND`, `VALIDATION`; later-phase codes such as `E_UNVERIFIED_FACT` are **deliberately absent**, so RB3 maps RB2's string codes onto existing members and must add no enum member |
| Migrations | `0001…0007*.py` | Verified head `0007_p5_run_gate` (`:15-16`); `0006` immutability triggers `trg_<table>_<op>_immutable` with `RAISE(ABORT,…)` over `IMMUTABLE_EVENTS = ("UPDATE","DELETE")` (`:31`, `:156-162`); literal-pinning CHECK (`:133-135`) and `length(source_sha256) = 64` (`:136`); downgrade refusal `_persisted_run_evidence()` + `RuntimeError(DOWNGRADE_REFUSED_MESSAGE)` (`:21-24`, `:165-184`); batch-mode FK addition (`:143-152`); `0003` conditional cross-table trigger (`:267-277`), plain UNIQUE index on a nullable column (`:263`), index-before-column drop ordering (`:281-283`); `0002` partial UNIQUE index with `sqlite_where` (`:289`) mirrored in the ORM (`models.py:278-287`) and reflected by name (`check_alembic_smoke.py:513-520`) |

### 1.3 Verified public interfaces RB3 may call (no invented APIs, no private imports)

- `p5_run_gate`: `GATE_VERSION`, `RunGateIssue`, `RunGateReceipt`, `evaluate_run_verification_gate`, `inspect_current_run_gate_locked`. RB3 calls only `inspect_current_run_gate_locked`; it never calls `evaluate_run_verification_gate` from a read-only path and never imports `_authorize`, `_evaluate_locked`, `_file_sha`, `_sha` or `_receipt`.
- `p5_evidence_bridge`: `CONTRACT_VERSION`, `build_run_evaluable_review_evidence`. `COMPARISON_HISTORY_VERSION`, `HISTORY_LOOKBACK_DAYS` and the `MAX_*` bounds are **not** exported and must not be imported; the private `source_reason` closure must not be imported either — §5.3 reproduces its contract through public interfaces.
- `p4_readonly_provenance`: `MAX_OFFLINE_ROWS`, `ReadonlyProvenanceEvidence`, `load_readonly_provenance_evidence`.
- `p4_run_bound_preview`: `POLICY_VERSION`, `build_p4_run_bound_review_input_preview` only; the pinned-sha/lookback/rule-id constants are not exported, so RB3 re-validates its own pinned policy through `validate_demo_policy` and asserts equality against the preview DTO's exposed `policy_version`/`policy_reference_sha256`.
- `monitoring`: `MonitoringInputError`, `ObservationSnapshot`, `admissibility_reason(row: ObservationSnapshot, *, patient_id, as_of_utc) -> str | None`.
- `p4_explicit_history`: `compare_explicit_current_with_history` (with its `1 <= len(current) <= 6` precondition honoured by T8a/T8b).
- `p4_rb2_offline_rules`: `evaluate_p4_rb2_offline_fixture`. `schemas.p4_rb2_offline_rules`: `OfflineEvidenceExclusion`, `OfflineObservation`, `OfflineRuleError`, `OfflineRuleFlag`, `OfflineRuleInput`, `OfflineRulePolicy`, `OfflineRuleResult`.
- `documents/field_parser`: `span_is_resolvable`, `page_text_for_span`, `CandidateFact` (all exported) — used for §7.1 span resolution against persisted `document_page_text` rows.
- `demo_policy`: `DemoPolicyCandidate`, `DemoPolicyError`, `validate_demo_policy`. `audit`: `SAFE_DETAIL_MAX`, `append_audit_event`, `derive_audit_key`, `safe_detail`, the `EVENT_*` constants. **`record_denial` is prohibited** (it commits).
- `core.enums`: `ActorType`, `AuditOutcome`, `MAPPING_VERSION`, `MAPPING_TABLE`, `MAPPING_VERSION_PATTERN`, `MeasureType`, `Role`, `Unit`. `core.errors`: `ApiError`, `ErrorCode`. `core.clock`: `format_utc`, `parse_utc`, `to_utc`. `core.policies`: `Principal`, `require_assigned_patient`, `require_doctor`. `db.models`: existing ORM classes (incl. `DocumentPageText`, `ExtractedFact`) plus the additive RB3 classes of §6.

`MAPPING_TABLE` is imported from `core.enums` (the same public source F1 and F2 use, `p5_run_gate.py:25`-area and `p5_evidence_bridge.py:22`) so that §5.3's alias/mapping reproduction uses the identical table rather than a copy.

---

## 2. (A) Authority and authorization design

### 2.1 Proposed internal authenticated service boundary

```python
# backend/app/services/p4_rb3_review_persistence.py  (PROPOSED — does not exist)
def persist_run_review_items(
    db: Session, *, principal: Principal, run_id: str,
    validation_clock: datetime, upload_root: str,
) -> ReviewPersistenceReceiptV1: ...
```

Exactly five server-owned parameters. No parameter admits a clearance flag, gate decision, trusted-fact count, evidence-id list, policy override, lookback window, cached V2/RB1/RB2 object, idempotency token or lineage claim: such inputs are structurally impossible, not merely ignored (**D-RB3-01**: internal authenticated service only; no HTTP router, agent tool, graph node, task or notification).

`ReviewPersistenceReceiptV1` (new frozen dataclass, `backend/app/schemas/p4_rb3_review_persistence.py`, §8.3) reports a completed write; it is never an execution token and carries `runtime_evaluable=False`, `policy_status='unapproved'`, `demo_only=True`, `not_for_clinical_use=True`.

### 2.2 Authorization conditions (re-proved from stored rows inside the write transaction)

1. `isinstance(principal, Principal)` and `require_doctor(principal)` → else `403 E_FORBIDDEN`.
2. `run = db.get(WorkflowRun, run_id)`; missing → `404 E_NOT_FOUND`.
3. `run.doctor_id == principal.user_id` → else `403 E_FORBIDDEN`.
4. **Stored session including ownership:** a `UserSession` with `id == principal.session_id` **and `user_id == principal.user_id`**, `revoked_at IS NULL`, `parse_utc(created_at) <= validation_clock < parse_utc(expires_at)`; any parse error means **inactive** → else `403 E_FORBIDDEN`.
5. `User.role == Role.DOCTOR.value` and `User.is_active == 1` → else `403 E_FORBIDDEN`.
6. `Patient` exists, `data_source == 'synthetic_fixture'`, `patient.id == run.patient_id` → else `403 E_FORBIDDEN`.
7. `require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)` → `403 E_SCOPE_VIOLATION` on reassignment.
8. `run.status == 'queued'` → else `409 E_VALIDATION`.
9. Run version identity against `MAPPING_VERSION`, `WORKFLOW_VERSION`, `STATE_SCHEMA_VERSION`, `POLICY_REFERENCE_VERSION`, and `current_node`/`halt_reason`/`checkpoint_ref` all NULL → else `409 E_VALIDATION`.
10. Immutable demo clock: `run.as_of_utc == '2026-11-14T12:00:00Z'` and `parse_utc(run.as_of_utc) == to_utc(validation_clock)` → else `409 E_VALIDATION`.

**Clock semantics.** `validation_clock` is a fixed injected instant that **defines** the evaluation instant. RB3 claims no wall-clock expiry detection: the only revalidation is re-testing that same instant against stored rows at T2 and T16. Elapsed-time expiry inside a long transaction would need a separately defined clock source and its own owner decision.

### 2.3 Denial and stale-evidence conditions (typed, fail-closed, zero writes)

| Condition | Denial |
|---|---|
| Missing/stale/HALT/UNAVAILABLE F1 gate; locked re-check raising | propagate `409 E_VALIDATION` |
| No stored PROCEED `RunGateEvaluation` matching `gate_version` + fingerprint | `409 E_VALIDATION` |
| F1 fingerprint or RB3 full-input fingerprint differs at T16 | `409 E_VALIDATION` |
| Re-hashed source bytes differ from stored `sha256`/`size_bytes` | `409 E_VALIDATION` |
| Session revoked/expired/foreign-owned; patient reassigned; non-synthetic patient | `403 E_FORBIDDEN` / `403 E_SCOPE_VIOLATION` |
| Foreign patient/run/document/observation/fact reference | `403 E_SCOPE_VIOLATION` |
| Selection, run identity, policy pin or injected clock mismatch | `409 E_VALIDATION` |
| Freshly derived exclusions differ from the cached F2/RB1 sets | `409 E_VALIDATION` "Historical exclusion evidence changed." |
| Malformed **scope-bearing** timestamps (run clock, session windows, selected `measured_at`) | typed `409 E_VALIDATION` |
| Malformed historical `created_at` | **R03** behaviour: the frozen evaluator emits `missing_created_at` while preserving proven duplicates; RB3 surfaces it in the receipt and invents no stricter denial (§4.5) |
| Caps exceeded (>6 selected current, >100 history, >40 facts, >5/<1 documents, per-measure item cap) | fail closed (`409 E_VALIDATION`, or RB2's typed error mapped per §4.4) |
| Unresolvable evidence key, or a `document_span` whose stored span is missing/unresolvable | `409 E_VALIDATION` "Evidence is not resolvable to stored sources." — the **whole** invocation; no fabricated coordinates, no NULL-span substitute |
| Any `OfflineRuleError` | mapped to an existing `ErrorCode` (§4.4), rollback, zero writes |
| Replay ambiguity or mismatch (§8.2) | `409 E_IDEMPOTENCY_CONFLICT` with a bounded reason |
| Audit key collision at T15 (helper returned a pre-existing row) | `409 E_IDEMPOTENCY_CONFLICT` reason `audit_key_collision` (§8.4) |
| DR-006 present while the conservative prohibition is ratified | `409 E_VALIDATION` reason `dr006_persistence_not_authorized` — the **entire** invocation (§7.4, **D-RB3-08**) |

**No committed denial audit:** `record_denial` commits (`audit.py:189`) and is prohibited; denials raise inside the transaction and roll back. **No new `ErrorCode` member:** RB2's string codes map onto existing members with the original string preserved as a bounded reason.

### 2.4 Field-to-source mapping (RB1's preview DTO exposes no version fields)

`RunBoundReviewInputPreviewV1` exposes `contract_version`, `run_id`, `patient_id`, `doctor_id`, `as_of_utc`, `policy_version`, `policy_reference_sha256`, `policy_baseline_lookback_days`, `gate_evaluation_id`, both fingerprints, the two selected-id tuples, `verified_facts`, `selected_observations`, `policy_comparisons`, `history_exclusions`, `no_current_reason` and the four frozen literals — and **no** `gate_version`, `workflow_version`, `state_schema_version` or `mapping_version`.

| Field | Authoritative source |
|---|---|
| `gate_version` | `RunGateReceipt.gate_version` from `inspect_current_run_gate_locked` == public `GATE_VERSION`; corroborated by stored `RunGateEvaluation.gate_version` and `EvaluableReviewEvidenceV2.gate_version` (`:411`) |
| `workflow_version` / `state_schema_version` / `mapping_version` | Persisted `WorkflowRun` columns re-read under the lock (F1 validates them at `:276-282`); corroborated by the F2 DTO (`:409-410`) |
| `policy_version` | Persisted `WorkflowRun.policy_version`, cross-checked against both DTOs and the pinned `demo-policy-1.1.0` |
| `policy_reference_sha256` | `preview.policy_reference_sha256`, asserted equal to RB3's re-validated pinned-policy digest and to the structurally pinned value in §6.3 |
| `gate_evaluation_id` | `preview.gate_evaluation_id`, re-proved by querying the stored PROCEED row at T3 |
| `gate_input_fingerprint_sha256` | `RunGateReceipt.input_fingerprint_sha256`, asserted equal to the stored PROCEED row and the Phase-1 pin |
| `bridge_input_fingerprint_sha256` | `EvaluableReviewEvidenceV2.bridge_input_fingerprint_sha256`, asserted equal to the preview's |
| F2 contract version | public `CONTRACT_VERSION` |
| History-policy identity | opaque: already inside `bridge_input_fingerprint_sha256` (`:351`); never imported |
| 90-day lookback | RB3's re-validated pinned policy, asserted equal to `preview.policy_baseline_lookback_days` (`Literal[90]`) |
| `as_of_utc` | persisted `WorkflowRun.as_of_utc`, equal to `preview.as_of_utc` and `to_utc(validation_clock)` |

Frozen RB1/F2 schemas are not changed, implicitly or otherwise.

---

## 3. (B) Fresh transactional verification — exact SQLite transaction ownership and lock boundary

### 3.1 Honest non-atomicity acknowledgements (normative)

1. **SQLite cannot transact with filesystem bytes**; `BEGIN IMMEDIATE` locks the database only.
2. **Re-hashing narrows but does not close the race.** RB3 re-hashes selected bytes at T3 (through the locked F1 re-check) and again at T16, as F2 does (`:330-344`, whose comment states filesystem and DB are not jointly transactional). A change landing between the T16 re-hash and durable commit cannot be excluded by any SQLite transaction.
3. **Phase 1 performs no writes at all.** F2's `build_run_evaluable_review_evidence` takes its own `BEGIN IMMEDIATE`, projects read-only and **always rolls back** (`:470-473`); RB1's preview owns separate locks and also rolls back. Neither is a snapshot shared with Phase 2, and the three passes are never described as one transaction.
4. **RB3 owns exactly one committing transaction**, from T1's `BEGIN IMMEDIATE` to T16's single `db.commit()` or unconditional `db.rollback()`.
5. **No partial persistence:** items, links, the completion record and the audit row are written in that one transaction or not at all.

### 3.2 Revised transaction sequence T1–T16

**Phase 1 — read-only pins (no writes anywhere; each helper owns and rolls back its own lock).**

| Step | Action | Failure |
|---|---|---|
| P1 | Assert a fresh clean Session: `not db.in_transaction() and not db.new/dirty/deleted` | `400 E_VALIDATION` |
| P2 | `build_run_evaluable_review_evidence(...)` → F2 DTO. **Corrected:** this is a **locked, read-only projection that always rolls back** (`:470-473`); it writes no F2 evidence, no audit row and no gate row | propagate |
| P3 | `build_p4_run_bound_review_input_preview(...)` → RB1 preview (its own separate locks, always rolled back) | propagate |
| P4 | Assert the preview's frozen literals: `contract_version == 'p4-rb1-preview-1.0.0'`, `policy_version == 'demo-policy-1.1.0'`, `policy_reference_sha256 == <R3-A LF seal>`, `policy_baseline_lookback_days == 90`, `as_of_utc == '2026-11-14T12:00:00Z'`, and all four `False`/`'unapproved'` literals | `409 E_VALIDATION` |
| P5 | Assert `to_utc(validation_clock) == parse_utc(preview.as_of_utc)` | `409 E_VALIDATION` |
| P6 | Assert cross-DTO agreement: both fingerprints, `gate_evaluation_id`, and the two selected-id tuples | `409 E_VALIDATION` |

Phase 1 output is a **cross-check pin only**; its `history_exclusions` are never carried into Phase 2 as authority.

**Phase 2 — the single committing write transaction.**

| Step | Action | Failure |
|---|---|---|
| **T1** | Re-assert a clean Session, then `db.connection().exec_driver_sql("BEGIN IMMEDIATE")`. The clean-Session check happens **before** the lock; **after** successful acquisition assert `db.in_transaction() is True`. `OperationalError` during acquisition → `503 E_VALIDATION` "Verification database is unavailable."; lock failure never yields a success receipt | `400`/`503` |
| **T2** | Re-prove the full §2.2 chain from stored rows | `403`/`409` |
| **T3** | Locked F1 revalidation via `inspect_current_run_gate_locked`; then require a stored `RunGateEvaluation` with `workflow_run_id == run.id AND gate_version == GATE_VERSION AND input_fingerprint_sha256 == receipt.input_fingerprint_sha256 AND decision == 'proceed'`; assert equality with the Phase-1 pin (sources per §2.4) | `409 E_VALIDATION` |
| **T4** | Re-pin run and manifest: re-read the three `run_selected_*`/`run_source_omission` tables in F0 order; assert set equality with both DTOs; assert bounds 1..5 documents, ≤20 manifest observations, ≤20 omissions, ≤6 selected current, ≤40 facts, ≤100 history | `409 E_VALIDATION` |
| **T5** | **Fresh full stored-history reconstruction:** `load_readonly_provenance_evidence(db, principal=…, patient_id=run.patient_id, as_of_utc=parse_utc(run.as_of_utc))` → `records` + `lineage_exclusions`. This locked snapshot is the **sole authoritative history source**; no separate pre-write pin object exists | propagate |
| **T6** | **Fresh, complete eligibility/exclusion derivation** reproducing the entire F2 `source_reason` contract from stored evidence (§5.3), then a drift cross-check against the cached F2/RB1 exclusion sets; cached ids are never authority and never subtracted | `409 E_VALIDATION` |
| **T7** | Selected-current stored-value proof: patient/measure/unit/exact `Decimal(str(value))`/`format_utc(parse_utc(measured_at))`/trust/source/`source_fact_id`/`source_document_id` against the F2 projection, plus manifest `observation_created_at`/`trust_level`/`source_fact_id` equality | `409 E_VALIDATION` |
| **T8a** | **If the re-pinned selection is empty:** do **not** call `compare_explicit_current_with_history` (it requires `1 <= len(current) <= 6`). Assert RB1's `no_current_selected` semantics — `preview.no_current_reason == 'no_current_selected'`, `preview.policy_comparisons == ()`, `evidence.comparisons == ()`, `evidence.no_current_reason == 'no_current_selected'` — set `comparisons = ()`, and continue to T9 with an empty `selected_current` tuple for the unchanged RB2 evaluator | `409 E_VALIDATION` on any mismatch |
| **T8b** | **If the selection is non-empty:** `compare_explicit_current_with_history(current=…, history=<fresh eligible rows>, patient_id=…, as_of_utc=…, baseline_lookback_days=90)`; require `compared.excluded_history == ()` and `len(comparisons) == len(selected_rows)`; assert field-by-field equality with `preview.policy_comparisons`. F2's 365-day comparisons serve only as identity inside the pinned bridge fingerprint | `409 E_VALIDATION` |
| **T9** | Compute the complete canonical `rb3-full-input-1.0.0` fingerprint (§5.4) over everything re-read/re-derived in T2–T8 plus the re-hashed source-byte digests | — |
| **T10** | Project the rule input: `OfflineRuleInput(patient_id, selected_current, history, as_of_utc, policy, active_fact_verification_statuses)` from stored rows only; `OfflineRulePolicy` re-validated via `validate_demo_policy` and asserted equal to the preview's pinned `policy_version`/`policy_reference_sha256`; `lineage_status` per §4.3. An empty `selected_current` tuple is passed through unchanged | `409 E_VALIDATION` |
| **T11** | `evaluate_p4_rb2_offline_fixture(input)`; catch `OfflineRuleError` → mapped denial; assert the result's frozen honesty literals are unchanged | mapped denial |
| **T12** | DR-006 owner-decision gate (§7.4): if a DR-006 flag exists and the conservative prohibition is ratified, deny the **whole** invocation; never persist a subset | `409 E_VALIDATION` |
| **T13** | Stored-evidence proof and **span resolution** for every emitted key (§7.1): resolve each `observation:`/`document:`/`fact:` reference to a real stored row of the same patient, and resolve every `document_span` to the stored fact's exact span verified against the persisted `document_page_text` row; missing or unresolvable → deny the whole invocation | `409 E_VALIDATION` |
| **T14** | Completion-record read (§8.2): select the single `review_evaluation` row for `workflow_run_id`; branch to first evaluation, exact-replay no-op, or typed conflict; when a completion row exists, re-read its `audit_event_id` row and validate identity **and** content | `409 E_IDEMPOTENCY_CONFLICT` |
| **T15** | **Corrected insertion order (immediate FKs, no deferred constraint):** (1) pre-generate `evaluation_id`; (2) insert `review_item` rows (`state='open'` only); (3) insert `evidence_link` rows; (4) call `append_audit_event(..., subject_type='review_evaluation', subject_id=evaluation_id)` — `audit_event.subject_id` has **no** FK, so the forward reference is safe, and the helper flushes and returns the row; (5) validate the returned audit row, including detecting that the helper returned a **pre-existing** row → typed conflict `audit_key_collision`; (6) insert `review_evaluation` using the returned `audit_event.id`, so the NOT NULL FK is satisfied at insert time; (7) proceed to T16's single commit. No UPDATE, DELETE, supersession or second audit mechanism | `IntegrityError`/conflict → rollback |
| **T16** | Pre-commit revalidation: re-call `inspect_current_run_gate_locked`, re-hash every selected source byte, recompute the full-input fingerprint, and require all three unchanged from T3/T9; then the single `db.commit()`. Any exception in T1–T16 → `db.rollback()` and re-raise | `409 E_VALIDATION` + rollback |

### 3.3 Concurrency, replay and denial handling

`BEGIN IMMEDIATE` serializes writers; a second invocation resolves through T14 as exact replay or typed conflict, with `ux_review_evaluation_run` as the structural backstop (`IntegrityError` → rollback → conflict, never a partial write). Denials raise inside the transaction and roll back. A rolled-back attempt persisted nothing — no rows, no completion record, no audit row, and its UUIDs never existed — so a retry is a first evaluation; retry equivalence is **semantic** (§8.1).

### 3.4 P5 source impact assessment

Exact correctness requires **no** change to any accepted F0/F1/F2/RB1 path: every needed interface is public (§1.3), the complete-history gap is closed by RB3's own reconstruction and fingerprint (§5), the empty-selection gap by T8a, and the F2 eligibility gap by reproducing its contract through public interfaces (§5.3).

One documentation-only inconsistency is identified, not made:

- **E6 (conditional, docstring-only).** `inspect_current_run_gate_locked`'s docstring states "Only the F2 bridge may call this with an already open BEGIN IMMEDIATE transaction" (`:862-868`). **Corrected:** it already has **two** callers — F2's `_projection` (`:88`) and RB1's `_policy_projection_locked` (`p4_run_bound_preview.py:101`) — so the docstring is already inaccurate today, and RB3 would be an **additional (third)** caller under the same contract (caller-owned lock, no writes). The proposed exception is a docstring-only clarification naming the actual callers, with **zero** logic, signature, behaviour or test-semantics change. **D-RB3-02b** prefers this separately authorized clarification over knowingly contradictory source documentation; the fallback if refused is an append-only `TOOL_CONTRACTS.md` note leaving P5 bytes untouched.

---

## 4. (C) RB2-to-RB3 evaluator boundary

### 4.1 Pinned R3-A fixture clock vs the immutable persisted run clock

RB3 requires equality rather than reconciling by relaxation: a run is persistable only if `run.as_of_utc == '2026-11-14T12:00:00Z'` and `to_utc(validation_clock) == parse_utc(run.as_of_utc)`. Other clocks are denied, never converted; no wall clock is substituted. This inherits RB1's binding (`:114-125`) and weakens nothing (**D-RB3-04**).

### 4.2 Offline policy reference vs execution authority

The pinned R3-A policy is a bounded demo comparison reference. RB1 and RB2 both hard-code `policy_status='unapproved'` and `runtime_evaluable=False`. Persisting rows approves nothing and activates nothing; every item is bound to exactly one sealed policy revision through `review_item.policy_version` and `review_evaluation.policy_reference_sha256`.

### 4.3 Fixture-asserted lineage vs persisted provenance — decisive constraint and recommendation

Three verified facts decide this boundary: (1) RB2 admits only `{unavailable, fixture_asserted}` and rejects `stored_independently_verified` as "Unsupported or forged provenance authority" (`:221-225`; test `:275`), while its schema documents that value as "a FUTURE RB3 server-side state" (schema `:67-69`); (2) `TOOL_CONTRACTS.md:270` says `fixture_asserted` labels ***fictional*** lineage and that "a future RB3 verifier must instead query and prove the actual selected stored sources"; (3) labelling stored-proved rows `unavailable` is **not** neutral — RB2 then emits a `verified_lineage_unavailable` exclusion for every `verified_document`/`doctor_verified` row (`:316-321`), persisting **false exclusion claims**.

- **Alt A2 (recommended, retained):** unchanged RB2 as pure computation core; `lineage_status='fixture_asserted'` passed **only** for rows whose stored lineage RB3 proved in-transaction, documented explicitly as a **transport label** forced by RB2's closed vocabulary. Every persisted artifact tells the truth: per-item `provenance_status` stores the evaluator's literal verbatim (§6.1), `evidence_link` rows point at real stored rows with §5-resolvable spans, and `review_evaluation.lineage_label_policy` records which boundary option was ratified. Conditions: RB2 source/schema/tests frozen (zero diffs); no DR-006 item ever presented as an authenticated doctor attestation; no trust promotion; mandatory RB3↔RB2 equivalence tests; append-only `TOOL_CONTRACTS.md` note (N8).
- **Alt B (fallback):** RB3-owned re-derivation of the six rules with `stored_independently_verified` as an RB3-internal state never passed to RB2. Honest labels, but ~500 lines of recently remediated bounded logic duplicated, divergence risk even with equivalence tests, a much larger review surface — and DR-006 becomes **inert by construction**, which would have to be disclosed. Alt B cannot be implemented by re-labelling, because RB2 rejects that value.
- **Alt C (rejected):** modify RB2 to accept `stored_independently_verified`; it reopens the owner-accepted candidate `8dd79ac0…` and edits frozen reviewed source and tests for no safety gain.

Under no alternative is the evaluator a runtime clearance token, and under none are the pinned clock, policy constraints or validation weakened. The transport-label tension remains **C-RB3-01, explicitly unratified** (§13).

### 4.4 Conservative R05 handling

RB2 fails closed with `OfflineRuleError("E_UNVERIFIED_FACT", …)` on `pending`/`rejected` fact assertions (`:236-243`). RB3 preserves this and, because `E_UNVERIFIED_FACT` is deliberately absent from `ErrorCode`, maps it to `409 E_VALIDATION` while carrying the original string as a bounded reason. `active_fact_verification_statuses` comes only from stored rows re-read under the lock.

### 4.5 R01–R08 protections, measurement types, 90-vs-365, bounds, trust, ordering

| Protection | Ratified behaviour | RB3 obligation |
|---|---|---|
| **R01** | Pin both normalized clocks | Pin run and injected clocks, require equality; no wall clock |
| **R02** | Per-observation lineage exclusion, incl. singleton document observations (`:316-321`) | Surface every `verified_lineage_unavailable` exclusion in the receipt; never drop or fabricate one |
| **R03** | "Exclude each missing or unparseable created time while preserving proven duplicates"; `_clock` returns `None` on `TypeError/ValueError/OverflowError/AttributeError` | Non-NULL `created_at` does **not** prove parseability. Pass stored values through unchanged; let the frozen evaluator emit `missing_created_at`; surface it. Scope-bearing clocks still deny typed |
| **R04** | The owner-approved **DR-003 newest-admissible-selected-type clarification** (`APPROVE-P4-RB2-DR003-NEWEST-ADMISSIBLE-SELECTED-TYPE`, [comment #7080736185](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7080736185), `2026-11-22T14:41:49Z`; `TOOL_CONTRACTS.md:279`) — **not** policy pinning | Feed both selected and freshly reconstructed historical rows so DR-003 can find the newest admissible same-unit row; never restrict its staleness evidence to selected rows |
| **R05** | `pending`/`rejected` fail closed even with an empty top-level status tuple | preserved exactly (§4.4) |
| **R06** | Malformed types produce typed failures | Map every `OfflineRuleError` to an existing `ErrorCode`; rollback; zero writes |
| **R07** | Overflow-safe 90-day window by comparing timestamp differences | A year-one timestamp must be handled **without** overflow: expect the window comparison to succeed and any `created_at` exclusion to be reported — not a crash, not a typed arithmetic denial |
| **R08** | Explicit local 28-digit decimal context; `121.1 - 100` emits DR-005 at precision 28 | Expect a persisted DR-005 item with the exact decimal delta — **not** `E_VALIDATION`; never alter the ambient context |

Measurement types: only those the frozen evaluator returns for selected admissible current observations (systolic, diastolic, heart-rate, glucose). 90-day policy vs F2's 365-day window: RB3 recomputes at **90** (T8b) for review semantics; the 365-day identity is pinned opaquely inside `bridge_input_fingerprint_sha256`. Bounds: ≤6 current / ≤100 history / ≤40 facts / 1..5 documents (T4); `max_items_per_type == 3` enforced by the evaluator (`:482-489`) giving a structural maximum of **12** items. Trust labels are stored exactly as emitted, never promoted. Persisted order is the evaluator's `(hint, rule_id, evidence, dedupe_key)`, preserved durably by `display_order` (§6.1).

### 4.6 Contract conflicts requiring explicit owner decisions

**C-RB3-01** (transport lineage label), **C-RB3-02** (DR-006 reachability and persistence), **C-RB3-03** (third schema object), **C-RB3-04** (evidence-identity uniqueness mechanism), **C-RB3-05** (`display_order` beyond §2.9), **C-RB3-07** (per-item `provenance_status` beyond §2.9, and whether a first-class `fact_id` column should be added to §2.10), **C-RB3-08** (DR-006 reachability proof obligation). Each has a recommendation and an exact authorization scope (§12, §13); none is resolved by guessing.

---

## 5. (RB3-D01) Complete locked historical-evidence reconstruction and the full-input fingerprint

### 5.1 Fingerprint authority scope

| Fingerprint | Actual coverage | Authoritative for | **Not** authoritative for |
|---|---|---|---|
| F1 `gate_input_fingerprint_sha256` (`:736`) | Run row incl. all four version fields; documents; facts; decisions; issues; **every column of every patient observation** (`:544-562`, incl. `created_at`, `note`), ≤100 rows; selected ids; `ocr_confidence_floor`/`conflict_tolerance`; omissions; re-hashed bytes (`:733`) | Integrity of **stored rows** across the whole patient scope: any inserted, removed or mutated row changes it | Derived rule inputs: eligibility, exclusions, comparisons, mapping, projection shape, RB2 policy semantics, or which rows RB3 fed the evaluator |
| F2 `bridge_input_fingerprint_sha256` (`:348-403`) | `contract`, `history_policy`, stored gate identity, run identity + versions, document ids, selected ids, six fact fields, **projected current only** (`:378-389`, no `created_at`), comparisons, `history_exclusions`, `historical_issues` | Integrity of the V2 projection | **Complete eligible history**: a non-baseline eligible row can change, or a new row appear, without altering the closest-prior baseline comparison |
| RB1 preview | Re-checked shape summary; no version fields; four frozen literals | Nothing at write time | Any authority; its `history_exclusions` are not an authorization input |
| **RB3 `input_fingerprint_sha256`** (§5.4) | The complete canonical rule-input set actually used in the committing transaction | **The durable evaluation identity** for replay, and "these exact inputs produced these exact rows" | Anything beyond that invocation |
| **RB3 `output_identity_sha256`** (§8.1) | The complete persisted semantic item + link identity, **including per-item `provenance_status`** | Proof of what was persisted | Surrogate ids and timestamps, deliberately excluded |

Equality of 90-day comparisons does **not** establish equality of all DR-003/006/008 inputs; F2 fingerprint equality does **not** establish complete pre-read history equality. F1 equality detects stored-row change across the patient scope but not derived-eligibility change. No complete-pre-read-history-equality claim is made from comparison equality.

### 5.2 Fresh reconstruction under the committing lock

At T5 RB3 calls public `load_readonly_provenance_evidence`, which re-proves scope itself and returns per row an `ObservationSnapshot` plus `created_at`, `source`, `source_fact_id`, `source_document_id`, `source_fact_verification_status`, and `lineage_exclusions`. Under the same lock RB3 then: (1) applies public `admissibility_reason(entry.observation, patient_id=…, as_of_utc=…)` to every record; (2) applies the complete `source_reason` reproduction of §5.3; (3) partitions into `selected_current` / `eligible_history` / `excluded` with reason codes; (4) re-reads the underlying `Observation` rows for fingerprint fields the snapshot lacks (`verified_by_user_id`, `verified_at`, `encounter_id`, `created_by_user_id`); (5) asserts bounds `len(selected_current) <= 6`, `eligible + excluded <= 100`, `selected ∩ excluded == ∅`.

Canonical ordering: the loader returns `measured_at DESC, id`; F1 uses `id ASC`; F2 uses `sorted(by_id)`. RB3 defines **one** canonical order — ascending observation id — for its fingerprint and projection, making both independent of loader ordering. Persisted display order is the evaluator's own ordering, preserved separately via `display_order`.

### 5.3 Complete fresh eligibility derivation reproducing the actual F2 `source_reason` contract

Revision 2 specified only `admissibility_reason` + loader lineage exclusions and then demanded exact equality with F2's cached sets — which would fail valid paths, because F2's `source_reason` (`:183-233`) applies substantially more conditions. T6 therefore reproduces the **complete** contract from stored evidence, using only public interfaces (`load_readonly_provenance_evidence` records, `db.get(ExtractedFact, …)`, a `select(ExtractedFact)` on the stored document, `MAPPING_TABLE` from `core.enums`, `admissibility_reason`) and never importing the private closure.

For each record, in this order:

**A. Source-class eligibility (`source_reason` reproduction).**
1. `source == 'verified_document'`:
   a. require `source_fact_verification_status == 'verified'`, non-empty `source_fact_id`, **`source_document_id ∈` the re-pinned selected document set**, and `trust_level == 'doctor_verified'`; else exclude `verified_lineage_unavailable`.
   b. load the stored `ExtractedFact` by `source_fact_id`; require it exists with `patient_id == run.patient_id`, `document_id == source_document_id`, `field_name == 'value'`, `verification_status == 'verified'`; else exclude `verified_lineage_unavailable`.
   c. select verified `test_name` facts on that document with `.limit(2)`; require **exactly one** with a non-empty `normalized_value`; else exclude `verified_mapping_unproven`.
   d. normalize the alias (`" ".join(value.lower().strip().rstrip(":").split())`), look it up in `MAPPING_TABLE`; require a mapping whose measure type equals `observation.measure_type` **and** whose required unit equals both `observation.unit` and the stored value fact's `unit`; else exclude `verified_mapping_unproven`.
2. `source ∈ {'patient_checkin', 'seed_fixture'}`: require `trust_level == 'self_reported_validated'` and `source_fact_id is None`; else exclude `stored_trust_source_mismatch`.
3. any other `source` value: exclude `stored_trust_source_mismatch`.

**B. Admissibility (`admissibility_reason`).** Apply to the `ObservationSnapshot`; any returned reason excludes with that reason.

**C. Loader lineage exclusions.** Union `provenance.lineage_exclusions` (`verified_lineage_unavailable`).

**D. RB2-side exclusions (emitted by the frozen evaluator, surfaced not pre-filtered).** `missing_created_at` (R03) and `verified_lineage_unavailable` for a `verified_document`/`doctor_verified` row that is not independently sourced (R02) — these arise inside T11 and are reported through `result.excluded` into the receipt.

**Complete exclusion-code inventory for RB3:** `verified_lineage_unavailable`, `verified_mapping_unproven`, `stored_trust_source_mismatch`, `validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp` (and any other documented `admissibility_reason` return), `missing_created_at`. Every code is either an actual F2/loader/admissibility literal or an actual RB2 literal; none is invented.

**Cross-check, never authority.** The derived non-selected exclusion set (ids **and** reason codes) must equal `evidence.history_exclusions` and `preview.history_exclusions`; any difference → `409 E_VALIDATION` "Historical exclusion evidence changed." A derived exclusion that is also a selected current id → `409 E_VALIDATION` "Selected current evidence may not be excluded." Because T6 now reproduces F2's complete contract, this equality is expected to hold on valid paths rather than spuriously failing. If it passes, the **derived** set is used and the cached set discarded. Should a residual divergence be found during implementation (for example an ordering-dependent reason code where F2 and RB3 both exclude a row but report different codes), that is a **stop-and-escalate** condition for a new owner decision — not a licence to weaken the cross-check or to prefer the cached set.

### 5.4 Complete canonical input fingerprint `rb3-full-input-1.0.0`

Computed at T9 using the repository's canonicalization discipline (`json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=True)` then SHA-256, as in `_sha:103-106`), over explicit **lists in canonical order** (never sets), every measurement as an exact `Decimal` string (never float), every timestamp via `format_utc`:

```text
{ "fingerprint_version": "rb3-full-input-1.0.0",
  "contracts": {f1_gate: GATE_VERSION, f2_bridge: CONTRACT_VERSION,
                rb1_preview: preview.contract_version, mapping: MAPPING_VERSION,
                workflow: run.workflow_version, state_schema: run.state_schema_version},
  "run": [id, patient_id, doctor_id, status, as_of_utc, mapping_version, policy_version,
          workflow_version, state_schema_version, idempotency_key, started_at,
          patient.assigned_doctor_id],
  "gate": [stored_gate.id, receipt.gate_version, receipt.input_fingerprint_sha256,
           receipt.decision, receipt.blocking_fact_count,
           sorted(receipt.historical_excluded_vi002_ids)],
  "bridge": [evidence.bridge_input_fingerprint_sha256],
  "policy": [policy_version, policy_reference_sha256, baseline_lookback_days,
             stale_measurement_days, exact decimal deltas, ocr_confidence_floor,
             conflict_tolerance, max_items_per_type, enabled_rules,
             enabled_verification_issues, settings.ocr_confidence_floor,
             settings.conflict_tolerance],
  "clock": [format_utc(validation_clock), run.as_of_utc],
  "selected_documents": [[id, patient_id, sha256, size_bytes, mime_type, extraction_status,
                          stored_path, page_count, uploaded_at, created_at,
                          recovered_from_document_id] sorted by id],
  "source_byte_digests": [[document_id, recomputed_sha256]],
  "selected_observations": [[complete stored column set incl. created_at, measured_at,
                             exact decimal value, unit, validation, trust_level, source,
                             source_fact_id, verified_by_user_id, verified_at, encounter_id,
                             created_by_user_id, manifest.observation_created_at,
                             manifest.trust_level, manifest.source_fact_id] sorted by id],
  "history_observations": [[the same complete column set] sorted by id],
  "derived_exclusions": [[observation_id, reason_code] sorted by (id, reason)],
  "lineage_proofs": [[observation_id, rb3_lineage_state, source_document_id, source_fact_id,
                      source_fact_verification_status] sorted by observation_id],
  "resolved_spans": [[document_id, fact_id, field_name, page_index, char_start, char_end,
                      span_resolvable] sorted by (document_id, field_name, fact_id)],
  "verified_facts": [[id, document_id, field_name, normalized_value, unit,
                      verification_status, corrected_from_fact_id, created_at] sorted by id],
  "verification_decisions": [[id, fact_id, verified_by_user_id, verified_at, status,
                              created_at] sorted by id],
  "comparisons_90d": [[current_id, baseline_id, measure_type, unit, comparable,
                       exact decimal delta or null, incomparable_reason, trust_basis]
                      in evaluator order, or [] under T8a],
  "active_fact_verification_statuses": [stored statuses in canonical order] }
```

Deliberate exclusions: **document bytes** (their recomputed digests are included instead); **free-text `note` and document text** (not rule-relevant, and already covered by the F1 digest which serializes `obs.note` at `:560` — so a note change is still detected at T3/T16 while no clinical prose or document text enters any RB3-persisted artifact); **RB3-generated surrogate ids and `created_at`** (not inputs). `resolved_spans` is included so that span resolvability is part of the durable input identity, and it stores only coordinates and a boolean — never `raw_text`.

### 5.5 Detection of added, removed or modified eligible history

| Change | Detected by | Mechanism |
|---|---|---|
| New eligible historical row | F1 digest **and** RB3 digest | F1 lists every patient observation; T3 compares to the persisted PROCEED row. Independently the row appears in `history_observations` |
| Eligible row deleted | F1 digest **and** RB3 digest | Both; also breaks the T6 cross-check if it had been excluded |
| Non-baseline row's value/unit/trust/validation/source/`measured_at` changed | F1 digest **and** RB3 digest | **The exact case the F2 bridge fingerprint misses** (projected current only) |
| Non-baseline row's `created_at` changed | F1 digest **and** RB3 digest | F1 serializes `obs.created_at` (`:561`); F2 does not; DR-008's ordering evidence is protected |
| Eligibility changed with no column change | RB3 digest + T6 cross-check | `derived_exclusions` changes; equality with the cached sets fails |
| A row's source document leaves the selected set | T6 (`source_reason` step 1a) | Excluded `verified_lineage_unavailable`; T4 selection equality also fails |
| Lineage proof or verification decision changed | RB3 digest | `lineage_proofs`, `verified_facts`, `verification_decisions` |
| Resolved span changed or became unresolvable | RB3 digest + T13 | `resolved_spans`; unresolvable denies the whole invocation |
| Baseline comparison unchanged but rule output changed | T14 output comparison | Complete input **and** output identities are compared together (§8.2 cases 4–5) |
| Source bytes changed on disk | T3 and T16 re-hash | Race reduced, not eliminated (§3.1) |
| More than 100 patient observations | F1 and the loader | `too_many_patient_observations` / `400` "Too many scoped observations." |

### 5.6 Sole authoritative history source — no separate pre-write pin

The fresh locked snapshot (T5–T6) is **explicitly the sole authoritative history source**. No pre-write history pin table is created: a second persisted history copy would need its own immutability guards, downgrade refusal and reconciliation story for no detection gain, since the F1 digest covers stored-row integrity and the RB3 digest covers derived rule-input identity. Phase 1's preview remains a corroborating drift cross-check only.

### 5.7 Pre-commit revalidation and filesystem limitation

T16 repeats the locked F1 re-check, the stored-PROCEED fingerprint equality, the byte re-hash and the full-input fingerprint recomputation immediately before the single COMMIT; any difference rolls back with a typed denial. The module docstring of the proposed RB3 service restates §3.1 so no future reader mistakes re-hashing for atomicity.

### 5.8 Does exact correctness require changing accepted F1/F2/RB1 paths?

**No.** All interfaces are public (§1.3); the history, empty-selection and eligibility gaps are closed inside RB3 (§5.2, T8a, §5.3). The only proposed touch is the docstring-only E6 clarification. Explicitly **not** proposed (each would need its own owner exception if ever wanted): exporting `COMPARISON_HISTORY_VERSION`/`HISTORY_LOOKBACK_DAYS` from `p5_evidence_bridge`; exporting `POLICY_CANONICAL_SHA256`/`POLICY_LOOKBACK_DAYS` from `p4_run_bound_preview`; making `source_reason` a public helper (RB3 reproduces its contract instead, and the T6 cross-check is the equivalence proof).

---

## 6. (D) Durable schema — proposed additive migration `0008_p4_rb3_review_persistence`

`down_revision = "0007_p5_run_gate"` (verified actual head). Three tables: the two dictionary tables plus the proposed completion record. All additive; no existing object altered or dropped.

### 6.1 `review_item` (DATA_DICTIONARY §2.9 fidelity, plus length CHECKs and two additive columns)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36` |
| `patient_id` | TEXT(36) | NOT NULL, FK `patient.id` RESTRICT; CHECK `length(patient_id) = 36` |
| `workflow_run_id` | TEXT(36) | **NOT NULL**, FK `workflow_run.id` RESTRICT; CHECK `length(workflow_run_id) = 36` — the genuine persisted run is the parent; no synthetic or placeholder run parent is ever created |
| `rule_id` | TEXT(8) | NOT NULL; CHECK `rule_id IN ('DR-001','DR-003','DR-005','DR-006','DR-008','DR-009')`; **CHECK `length(rule_id) = 6`** (corrected from Revision 2's `= 7`, which would have rejected every legitimate insert — `DR-001` is six characters). The dictionary's `^DR-\d{3}$` intent is expressed as the closed IN list plus this length check because SQLite CHECK has no regex operator; retired `DR-002/004/007/010` are structurally rejected |
| `reason_code` | TEXT(64) | NOT NULL; **CHECK `reason_code IN ('missing_baseline','measurement_stale','change_exceeds_demo_parameter','verified_source_conflict','duplicate_or_out_of_order','implausible_value')`** — transcribed now from the six actual `_flag` call sites (`:350`, `:367`, `:397`, `:447`, `:474`, `:414`), not deferred; CHECK `length(reason_code) BETWEEN 1 AND 64` |
| `workflow_hint` | TEXT(24) | NOT NULL; CHECK IN (`data_quality`,`verification_needed`,`change_to_review`) |
| `trust_basis` | TEXT(16) | NOT NULL; CHECK IN (`self_reported`,`doctor_verified`,`mixed`) |
| `message` | TEXT(240) | NOT NULL; CHECK `length(message) BETWEEN 1 AND 240`; stored **verbatim** from the frozen evaluator's neutral template — no new prose, no clinical interpretation |
| `policy_version` | TEXT(24) | NOT NULL; CHECK `policy_version = 'demo-policy-1.1.0'`; CHECK `length(policy_version) <= 24` |
| `demo_only` | INTEGER | NOT NULL DEFAULT 1; CHECK `demo_only = 1` |
| `dedupe_key` | TEXT(64) | NOT NULL; CHECK `length(dedupe_key) = 64`; UNIQUE with `workflow_run_id` |
| `state` | TEXT(16) | NOT NULL DEFAULT `'open'`; CHECK IN (`open`,`decided`,`superseded`) — vocabulary **reserved**; only `open` writable (G3), and G1/G2 make rows immutable so no transition is expressible in SQL |
| `provenance_status` | TEXT(24) | **Additive (RB3-R3-08, Option A, C-RB3-07).** NOT NULL; CHECK `provenance_status IN ('fixture_asserted','stored_independently_verified')`; stores the evaluator's emitted `OfflineRuleFlag.provenance_status` **verbatim** (under Alt A2 always `fixture_asserted`), so no persisted item can over-claim. Included in `output_identity_sha256` |
| `display_order` | INTEGER | **Additive (C-RB3-05).** NOT NULL; CHECK `display_order >= 0`; UNIQUE with `workflow_run_id` — preserves the evaluator's `(hint, rule_id, evidence, dedupe_key)` ordering durably |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Indexes: `ux_review_dedupe UNIQUE (workflow_run_id, dedupe_key)`; `ux_review_order UNIQUE (workflow_run_id, display_order)`; `ix_review_patient_state (patient_id, state)`; `ix_review_run (workflow_run_id)`.

**Rule semantics correction (RB3-R3-09):** `DR-001` means **missing baseline** for an explicitly selected current measurement (`reason_code='missing_baseline'`, `:349-353`) — not "no current measurement". The zero-selected-current situation is handled by T8a and produces a durable zero-item (or DR-003/DR-009-only) evaluation, never a DR-001.

**Vocabulary reservation vs write permission.** The dictionary mandates the three-value `state`, so the CHECK keeps all three; this slice has **no** permission to write `decided`/`superseded` (G3 + G1/G2). A future decision-writing slice needs its own owner authorization and trigger revision; nothing here pre-approves it. The same distinction applies to `evidence_link.owner_type` and `kind`.

### 6.2 `evidence_link` (DATA_DICTIONARY §2.10 fidelity, span contract enforced)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36` |
| `owner_type` | TEXT(24) | NOT NULL; CHECK IN (`review_item`,`verification_issue`,`summary_claim`) — reserved; only `review_item` writable (G7) |
| `owner_id` | TEXT(36) | NOT NULL; CHECK `length(owner_id) = 36`; must reference an existing `review_item` (G9) |
| `kind` | TEXT(24) | NOT NULL; CHECK IN (`document_span`,`observation`,`checkin_note`) — `checkin_note` reserved, never writable (G8) |
| `document_id` | TEXT(36) | NULL; FK `document.id` RESTRICT; required for `document_span` |
| `observation_id` | TEXT(36) | NULL; FK `observation.id` RESTRICT; required for `observation` |
| `page_index` | INTEGER | NULL; CHECK `page_index IS NULL OR page_index >= 0` |
| `char_start` / `char_end` | INTEGER | NULL; CHECK both NULL or both NOT NULL with `char_start >= 0 AND char_end > char_start` (**strict**, per `EXTRACTION_PROVENANCE.md` §5 rule 1 — the stored `ExtractedFact` CHECK `span_ordered` is weaker, allowing equality, so RB3 must not rely on it) |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Kind-conditional integrity CHECKs (no subqueries, so all are expressible):

```sql
CHECK ( (kind = 'document_span' AND document_id IS NOT NULL AND observation_id IS NULL
                         AND page_index IS NOT NULL AND char_start IS NOT NULL
                         AND char_end IS NOT NULL)
     OR (kind = 'observation'  AND observation_id IS NOT NULL AND document_id IS NULL
                         AND page_index IS NULL AND char_start IS NULL AND char_end IS NULL)
     OR (kind = 'checkin_note' AND document_id IS NULL AND observation_id IS NULL) )
```

**Contract reconciliation (RB3-R3-07), explicitly:** `DATA_DICTIONARY.md` §2.10 declares `page_index`/`char_start`/`char_end` NULL-able **per column across kinds** and its own CHECK note already says "exactly one of (`document_id`**+span**, `observation_id`) populated per `kind`"; `EXTRACTION_PROVENANCE.md` §5 requires all three for `document_span`. These are **not in conflict**: NULL-ability serves `observation` and `checkin_note`, while the kind-conditional CHECK above enforces §5 for `document_span`. **No contract amendment is needed** for this, and none is proposed. A NULL span is therefore never a substitute for provenance in RB3: every `document_span` row carries a stored, §5-resolvable span, or the invocation is denied.

The one genuine §2.10 gap is the absence of a `fact_id` column, so a `fact:` reference can only be represented by its value-fact span. The fact's identity **is** preserved inside `input_fingerprint_sha256` (`resolved_spans`, `verified_facts`) and `output_identity_sha256`. Adding a first-class `fact_id` column would be a contract amendment → **C-RB3-07** / **D-RB3-05f**, not proposed as an edit here.

Index: `ix_evidence_owner (owner_type, owner_id)`.

### 6.3 `review_evaluation` — proposed additive immutable completion record (**C-RB3-03**, **D-RB3-09**)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36`; **pre-generated at T15 step 1** so the audit row can reference it |
| `workflow_run_id` | TEXT(36) | NOT NULL; FK `workflow_run.id` RESTRICT; **UNIQUE** (`ux_review_evaluation_run`) — exactly one immutable completed evaluation per persisted run |
| `patient_id` / `doctor_id` | TEXT(36) | NOT NULL; FK `patient.id` / `user.id` RESTRICT; must equal the run's (G14) |
| `as_of_utc` | TEXT(20) | NOT NULL; CHECK `as_of_utc = '2026-11-14T12:00:00Z'`; CHECK `length(...) = 20` |
| `policy_version` | TEXT(24) | NOT NULL; CHECK `policy_version = 'demo-policy-1.1.0'`; must equal `workflow_run.policy_version` (G14) |
| `policy_reference_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64`; **CHECK `policy_reference_sha256 = 'f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36'`** — structurally pinned to the exact R3-A digest (the value already public in `p4_run_bound_preview.py:37`), following the `0006:133-136` literal-pinning precedent. Sub-decision **D-RB3-05e**; trade-off: re-sealing the policy later requires a migration |
| `fingerprint_version` | TEXT(32) | NOT NULL; CHECK `= 'rb3-full-input-1.0.0'` |
| `input_fingerprint_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` — complete RB3 rule-input identity |
| `output_identity_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` — complete persisted semantic output identity, **including per-item `provenance_status`** |
| `gate_evaluation_id` | TEXT(36) | NOT NULL; FK `run_gate_evaluation.id` RESTRICT — the stored PROCEED row used |
| `gate_input_fingerprint_sha256` / `bridge_input_fingerprint_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` each |
| `f2_contract_version` | TEXT(8) | NOT NULL; CHECK `= '2.0.0'` (public `CONTRACT_VERSION`) |
| `gate_version` | TEXT(8) | NOT NULL; CHECK `= '1.0.0'` (public `GATE_VERSION`) |
| `rb2_policy_version` | TEXT(24) | NOT NULL; CHECK `= 'demo-policy-1.1.0'` (`OfflineRuleResult.policy_version`) |
| `lineage_label_policy` | TEXT(32) | NOT NULL; CHECK IN (`a2_transport_label`,`b_rb3_derived`) — **replaces** Revision 2's global `lineage_state`. Truthful semantics: it records **which ratified evaluator-boundary option governed the labels passed to the evaluator** for this invocation. It is **not** a claim that every observation in a mixed input has independently verified document lineage; per-item truth lives in `review_item.provenance_status` and `trust_basis`, and rows without document lineage are `self_reported`/`mixed` with no document-link claim at all |
| `item_count` | INTEGER | NOT NULL; CHECK `item_count BETWEEN 0 AND 12` (4 measure types × `max_items_per_type` 3, enforced at `:482-489`); must equal the actual `review_item` row count (G14) |
| `evidence_link_count` | INTEGER | NOT NULL; **CHECK `evidence_link_count BETWEEN 0 AND 72`** (corrected from 96: 12 items × the maximum **6** references per flag, derived from all six call sites — DR-001/003/009 = 1, DR-005/008 = 2, DR-006 = 6) and CHECK `evidence_link_count >= item_count` (`_flag` refuses empty evidence, `:161-162`); must equal the actual `evidence_link` row count (G14) |
| `exclusion_count` | INTEGER | NOT NULL; CHECK `BETWEEN 0 AND 100` — derived + lineage + R02/R03 exclusions surfaced, never dropped |
| `audit_event_id` | TEXT(36) | NOT NULL; FK `audit_event.id` RESTRICT — inserted **after** the audit row exists (T15 step 6) so the immediate FK is satisfiable |
| `demo_only` | INTEGER | NOT NULL DEFAULT 1; CHECK `demo_only = 1` |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Indexes: `ux_review_evaluation_run UNIQUE (workflow_run_id)`; `ix_review_evaluation_patient (patient_id, created_at)`.

Alternatives evaluated: **Option 1 dedicated table (recommended)** — proves the original evaluation fingerprint exactly, makes one-completion-per-run structural, covers the zero-item case, atomic with the rows, self-describing via `fingerprint_version`. **Option 2 audit-only (rejected)** — `derive_audit_key` includes `request_id` (`audit.py:65-74`) so replays derive different keys and append second rows; `append_audit_event` returns an existing row **without comparing content** (`:124-128`); `safe_detail` is collapsed and truncated to 500 (`:77-87`); `event_type` has no per-run uniqueness. **Option 3 rows-only inference (rejected)** — a zero-item evaluation leaves no rows and is indistinguishable from "never evaluated", and extra/missing-row cases have no authoritative expected-output identity.

### 6.4 Exact trigger inventory — **14 triggers** (authoritative)

House patterns: unconditional immutability triggers (`0006:156-162`) and conditional cross-table `BEFORE INSERT … WHEN (SELECT …) … BEGIN SELECT RAISE(ABORT, '…'); END` (`0003:267-277`). Cross-table comparisons must be triggers: a SQLite CHECK cannot reference another table.

| # | Name | Table | Event | Condition | Effect |
|---|---|---|---|---|---|
| G1 | `trg_review_item_update_immutable` | `review_item` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'review_item is immutable in P4-RB3')` |
| G2 | `trg_review_item_delete_immutable` | `review_item` | BEFORE DELETE | unconditional | same |
| G3 | `trg_review_item_insert_open_only` | `review_item` | BEFORE INSERT | `NEW.state <> 'open'` | `RAISE(ABORT,'only open review items may be written in P4-RB3')` |
| G4 | `trg_review_item_run_scope_consistent` | `review_item` | BEFORE INSERT | run row missing, or `NEW.patient_id` ≠ run's `patient_id`, or `NEW.policy_version` ≠ run's `policy_version` | `RAISE(ABORT,'review item must match its run scope')` |
| G5 | `trg_evidence_link_update_immutable` | `evidence_link` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'evidence_link is immutable in P4-RB3')` |
| G6 | `trg_evidence_link_delete_immutable` | `evidence_link` | BEFORE DELETE | unconditional | same |
| G7 | `trg_evidence_link_owner_review_item_only` | `evidence_link` | BEFORE INSERT | `NEW.owner_type <> 'review_item'` | `RAISE(ABORT,'only review_item owners are supported in P4-RB3')` |
| G8 | `trg_evidence_link_kind_not_checkin_note` | `evidence_link` | BEFORE INSERT | `NEW.kind = 'checkin_note'` | `RAISE(ABORT,'checkin_note evidence is reserved and never written by P4-RB3')` |
| G9 | `trg_evidence_link_owner_exists` | `evidence_link` | BEFORE INSERT | `(SELECT id FROM review_item WHERE id = NEW.owner_id) IS NULL` | `RAISE(ABORT,'evidence link owner must be an existing review item')` |
| G10 | `trg_evidence_link_reference_same_patient` | `evidence_link` | BEFORE INSERT | referenced `observation`/`document` missing, or its `patient_id` ≠ the owner item's `patient_id` | `RAISE(ABORT,'evidence must belong to the review item patient')` |
| G11 | `trg_evidence_link_duplicate_identity` | `evidence_link` | BEFORE INSERT | NULL-safe `EXISTS` match on `(owner_type, owner_id, kind, document_id, observation_id, page_index, char_start, char_end)` using `IS` | `RAISE(ABORT,'duplicate typed evidence identity')` |
| G12 | `trg_review_evaluation_update_immutable` | `review_evaluation` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'review_evaluation is immutable in P4-RB3')` |
| G13 | `trg_review_evaluation_delete_immutable` | `review_evaluation` | BEFORE DELETE | unconditional | same |
| G14 | `trg_review_evaluation_run_scope_consistent` | `review_evaluation` | BEFORE INSERT | run/patient/doctor/policy/`as_of_utc` mismatch against `workflow_run`, or the referenced `run_gate_evaluation` is not a stored `proceed` row of that run, or the referenced `audit_event` row is missing, or `item_count`/`evidence_link_count` differ from the actual row counts for that run | `RAISE(ABORT,'review evaluation must match its run scope and rows')` |

Requested INSERT restrictions → guards: `state='open'` → G3; real run ownership → NOT NULL FK + G4/G14; equal run/item patient → G4; equal run/item policy version → G4; same-patient evidence → G10; existing review-item owner → G9; unsupported `verification_issue`/`summary_claim` owners → G7; reserved `checkin_note` → G8; duplicate typed evidence identity → UNIQUE indexes + G11.

**Validity after the T15 correction (RB3-R3-02, §11 question):** G14 remains valid and in fact becomes *stronger* — because items and links are inserted **before** the completion row, G14's count-agreement condition can be evaluated against real rows at insert time; and because the audit row is inserted before the completion row, G14 can also require the referenced `audit_event` row to exist (added above). The audit verification sequence in §8.4 is likewise still valid: T14's re-read path uses `audit_event_id`, and T15 step 5's fresh-insert path validates the returned row before the completion row exists. Consolidation of G7+G8 or G9+G10 was considered and rejected: separate triggers give distinct denial messages and independent testability. **14** is the only trigger count this design asserts.

### 6.5 Index and uniqueness inventory, including SQLite NULL semantics

SQLite treats NULLs as **distinct** in UNIQUE indexes — a behaviour this repository already relies on deliberately (`ux_obs_source_fact` on the nullable `observation.source_fact_id`, `0003:263`).

Two-layer design:

1. **Partial UNIQUE indexes** on the accepted `sqlite_where` pattern (`0002:289`; ORM mirror `models.py:278-287`; reflected by name in `check_alembic_smoke.py:513-520`):
   - `ux_evidence_link_observation UNIQUE (owner_id, observation_id) WHERE kind = 'observation'` — all indexed columns NOT NULL for that kind → fully effective.
   - `ux_evidence_link_span UNIQUE (owner_id, document_id, page_index, char_start, char_end) WHERE kind = 'document_span'` — **now fully effective as well**, because §6.2's kind-conditional CHECK makes `page_index`/`char_start`/`char_end` NOT NULL for every `document_span` row. This is a direct consequence of the RB3-R3-07 correction: with NULL spans prohibited and `checkin_note` unwritable (G8), **no RB3-writable `evidence_link` row has any NULL column participating in identity**, so the NULL-distinctness gap **closes entirely**.
2. **G11** is retained as defence-in-depth (belt-and-braces against a future kind or a relaxed CHECK), not as the primary mechanism. Its necessity is therefore downgraded from "mandatory gap closure" (Revision 2) to "structural redundancy", stated honestly.

Rejected (**C-RB3-04**): a single COALESCE **expression** UNIQUE index — it would need `Index(..., text(...))` in the ORM, and `test_migration_matches_the_orm_metadata` (`tests/p2/test_p2_migration.py:314-331`) compares reflected index **names** to ORM-declared names for every table; the repository has no expression-index precedent, so its reflection parity is unproven. If the owner prefers it, the implementation PR must first prove name-level parity with a dedicated test.

Also unique: `ux_review_dedupe`, `ux_review_order`, `ux_review_evaluation_run`.

### 6.6 SQLite constraint behaviour accuracy (normative for the implementation PR)

`TEXT(n)` length is **not** enforced → every bound is an explicit `length()` CHECK (`0006:136` precedent); tests must assert the CHECK, never the type declaration. CHECK cannot reference other tables → cross-table integrity is triggers (G4, G9, G10, G14). No regex in CHECK → closed IN lists plus length checks. FKs need `PRAGMA foreign_keys = ON`, already asserted by `tests/test_database.py:160`; **FKs are immediate by default and no deferred constraint is used anywhere in this design** (RB3-R3-02). Triggers are invisible to ORM metadata → assert them via `sqlite_master WHERE type='trigger'`, as `check_alembic_smoke.py:498-501` already does. Batch mode recreates tables → RB3 creates new tables only and alters none, so no accepted CHECK, index or row can be silently dropped.

### 6.7 ORM / migration parity obligations

`test_migration_matches_the_orm_metadata` (`:314-331`) asserts migrated tables equal `Base.metadata.tables` and, per table, migrated index **names** equal declared index names. The implementation PR must therefore declare all three tables and every index (including both partial unique indexes with matching `sqlite_where` text) in `backend/app/db/models.py` **and** create identical names in `0008`. Triggers are migration-only and asserted separately. Any name mismatch fails an accepted test — a hard obligation, not a style preference.

### 6.8 Referential integrity and deletion restrictions

All RB3 FKs are `ON DELETE RESTRICT`, preserving the dictionary's deletion restrictions and the accepted `audit_event`/`verification_issue` → `workflow_run` pattern (`0006:143-152`). `review_item.workflow_run_id` stays NOT NULL with a genuine run parent; no placeholder, synthetic or shadow run row is ever created. Deletion of any referenced run, patient, user, document, observation, gate evaluation or audit row is structurally refused. The only removal path remains the demo reset (whole-database rebuild).

---

## 7. (E) Evidence-link mapping for all six rule outputs

### 7.1 RB2 evidence keys → typed persisted links (span contract enforced)

RB2 emits `observation:<id>`, `document:<id>`, `fact:<id>` (`_flag:160`). §2.10 provides kinds `document_span`, `observation`, `checkin_note` with reference columns `document_id`(+span) and `observation_id` only. Mapping, with **no NULL spans**:

| RB2 key | Persisted link | Proof required at T13 |
|---|---|---|
| `observation:<id>` | `kind='observation'`, `observation_id=<id>`, span columns NULL | Stored `Observation` exists, same patient (also G10), and is in the re-pinned selection or the freshly reconstructed eligible set |
| `document:<id>` | `kind='document_span'` on that document, span = the stored **verified `test_name` fact's** exact `page_index`/`char_start`/`char_end` | Exactly one verified `test_name` fact exists on that document with a non-empty `normalized_value` (the same condition F2's `source_reason` step 1c proves); its span satisfies §5 rule 1 — `0 <= char_start < char_end <= len(page_text)`, bounded by `max_page_text_chars`, and `page_text[char_start:char_end] == raw_text[:300]` against the persisted `document_page_text` row, asserted with the public `span_is_resolvable` (or, if its typed input cannot be constructed without inventing fields, by asserting the identical condition directly — the same contract, never a weaker one) |
| `fact:<id>` | `kind='document_span'` on the fact's stored `document_id`, span = that stored **verified `value` fact's** exact span | The stored `ExtractedFact` exists with `patient_id == run.patient_id`, `document_id` equal to the link's document, `field_name == 'value'`, `verification_status == 'verified'`, and a §5-resolvable span as above |
| `checkin_note` | **never written by RB3** (G8) | Reserved vocabulary for a future check-in slice; no rule emits one |

**Deny, never fabricate.** If a required span is missing, unresolvable, or the underlying fact identity is not exactly as stored, the **entire invocation** is denied (`409 E_VALIDATION`); RB3 never fabricates coordinates, never substitutes a NULL span for provenance, never falls back to a free-text or untyped link, and never invents a fact or verification decision. Fixture-declared references are not automatically authorized evidence: every key must resolve to a stored row of the same patient under the lock.

Because `evidence_link` has no `fact_id` column, the fact identity is preserved in `input_fingerprint_sha256` (`resolved_spans`, `verified_facts`) and `output_identity_sha256`, not in the link row. A first-class `fact_id` column would be a §2.10 amendment → **C-RB3-07** / **D-RB3-05f** (not proposed as an edit here).

### 7.2 Per-rule mapping (corrected reference counts)

| Rule | Reason code (actual) | RB2 evidence (actual call site) | Refs | Persisted links |
|---|---|---|---|---|
| `DR-001` missing **baseline** | `missing_baseline` | `(current,)` (`:349-353`) | 1 | 1 `observation` |
| `DR-003` stale measurement | `measurement_stale` | `(newest,)` (`:366-370`) — may be a historical row per the owner clarification | 1 | 1 `observation` |
| `DR-005` change exceeds demo parameter | `change_exceeds_demo_parameter` | `(baseline, current)` (`:396-401`) | 2 | 2 `observation` |
| `DR-006` verified source conflict | `verified_source_conflict` | `(first, second)` **plus** `document:first`, `document:second`, `fact:first`, `fact:second` (`:434-451`) | **6** | **2 `observation`** (both rows — neither may be dropped) **+ 2 `document_span`** (each document's verified `test_name` span) **+ 2 `document_span`** (each fact's verified `value` span) |
| `DR-008` duplicate / out-of-order | `duplicate_or_out_of_order` | `(first, second)` (`:473-477`) | 2 | 2 `observation` |
| `DR-009` implausible value | `implausible_value` | `(current,)` (`:413-417`) | 1 | 1 `observation` |

Maximum references per flag = **6** (DR-006); minimum = 1 (`_flag` refuses empty evidence, `:161-162`). With at most **12** items (4 measure types × `max_items_per_type` 3), the structural maximum persisted link count is **12 × 6 = 72** — the bound now encoded in §6.3. For DR-006 the six links are pairwise distinct: two distinct observation ids, and four spans across two distinct documents (two `test_name` spans and two `value` spans with different coordinate ranges), so G11 and both partial unique indexes are satisfied without collision.

### 7.3 Kind semantics

`document_span` = this persisted document at this **stored, resolvable** span; it is the only kind able to carry a `document:` or `fact:` reference. `observation` = this stored observation row, same patient, enforced by G10. `checkin_note` = reserved vocabulary for a future patient-check-in slice (§5 requires the note-bearing `observation_id`), never written by RB3 because none of the six rules emits a check-in reference. No free-text evidence link exists and none is invented; no verification decision is fabricated — `verified_by_user_id`, `verified_at` and `FactVerification` rows are read as stored and captured in the fingerprint rather than re-decided.

### 7.4 DR-006: reachability re-examined (**C-RB3-02**, **C-RB3-08**, **D-RB3-08**)

**Revision 1 claimed DR-006 is structurally unreachable. Revision 2 claimed a reachable fixture using two non-selected source documents. Both are withdrawn.**

Revision 2's fixture is **provably impossible**: F2's `source_reason` excludes any `verified_document` row whose `source_document_id` is not in the selected document set (`:187-193` → `verified_lineage_unavailable`), so such rows never reach the evaluator as eligible history.

The **narrowed mechanism** that remains source-grounded: DR-006 iterates `combinations(ordered, 2)` over all eligible rows of a measure type (`:425`, `ordered` from `:330-331`), requiring identical `measured_at`, differing values, `_independent_fixture_source` on both rows and distinct document **and** fact ids. F1's VI-006 detection is narrower in three verified ways: its loop covers **selected documents only** (`p5_run_gate.py:608`); it `continue`s — constructing no candidate at all — unless the document has exactly one `test_name`, exactly one `report_date` and exactly one verified `value` fact, with a `MAPPING_TABLE` alias and matching unit (`:617-628`); and its comparison is same-UTC-calendar-day at `conflict_tolerance` using `report_date T00:00:00Z` (`documents/issues.py:243-256`), not exact `measured_at` equality. F2's `source_reason`, by contrast, has **no `report_date` requirement**. So a pair of selected documents that both satisfy F2's mapping conditions but both fail F1's shape gate (for example by lacking a `report_date` fact, or carrying a second non-verified `test_name` fact so F1's unfiltered `tests` list has length 2 while F2's verified-only query returns 1) would produce no VI-006 candidate from either document — and if either document *did* conform, its candidate would catch the pair, so **both** must fail.

**Whether such a run is actually constructible is NOT PROVEN here.** It also depends on extraction-time issue generation (VI-001…VI-005) and F1's selected-document preflight (`inspect_selected_document_verification`, `:515-528`), which this design has not fully traced; a document missing `report_date` may itself carry an open blocking issue that forces HALT. Consistent with the review instruction, **no fixture is invented**: DR-006 reachability on an F1-PROCEED run is declared **UNPROVEN in both directions**, and the only asserted facts are (a) the mechanism divergence above, verified at line level, and (b) that the currently approved fixtures do not exercise it (`GOLD-D.expected.json` records `expected_source_conflicts: 0`) — a fixture property, not an invariant.

Design consequences:

- Revision 1's fail-closed denial of any DR-006 candidate stays **withdrawn**: it rested on a false invariant and would suppress a genuine stored-evidence signal.
- RB3 must therefore **handle** a DR-006 flag if one ever occurs, without asserting that it can. **D-RB3-08** asks the owner to choose: **(i)** persist DR-006 normally (recommended) with all six links, the evaluator's `provenance_status` stored verbatim, and no trust promotion; or **(ii)** retain a conservative prohibition, in which case T12 denies the **entire** invocation with reason `dr006_persistence_not_authorized` — never a partial persist, never a silently dropped item.
- **C-RB3-08** records the implementation-PR proof obligation: either construct a genuine PROCEED run that reaches DR-006 through the accepted F1/F2 contracts and test the ratified behaviour end-to-end, or demonstrate from the accepted extraction/issue logic that no such run exists and record DR-006 as a provably inert rule with that proof in the implementation review. In neither case may a fixture be invented or the reachability question left implicit.

---

## 8. (F) Idempotency, replay and atomicity — invocation level

### 8.1 Identities

- **Dedupe key (unchanged, per row):** `sha256("|".join((patient_id, rule_id, *sorted_refs, trust_basis)))` from the frozen evaluator (`:164`), with `_valid_id` refusing `|`/control chars (`:176-188`); persisted with `UNIQUE (workflow_run_id, dedupe_key)`.
- **Complete input identity:** `review_evaluation.input_fingerprint_sha256` (§5.4).
- **Complete output identity:** `review_evaluation.output_identity_sha256` = the same canonical JSON+SHA-256 discipline over the persisted **semantic** output: for each item in evaluator order, `(display_order, rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, dedupe_key, state, provenance_status)` together with its ordered evidence-link tuples `(kind, document_id, observation_id, page_index, char_start, char_end)`; plus `item_count`, `evidence_link_count`, `lineage_label_policy` and the sorted derived-exclusion list `(observation_id, reason)`. **`provenance_status` is included** (RB3-R3-08), so the identity cannot be preserved while the per-item provenance representation changes.
  **Deliberately excluded:** `review_item.id`, `evidence_link.id`, `review_evaluation.id`, `audit_event_id` and every `created_at` — per-invocation surrogate values whose inclusion would make an exact semantic replay compare unequal. Their exclusion cannot mask a content difference because every semantic field the evaluator emitted, including `provenance_status`, is included. This is the precise sense in which retry equivalence is semantic and newly generated UUIDs need not match a rolled-back attempt.

### 8.2 All thirteen replay cases (fail closed on ambiguity, `409 E_IDEMPOTENCY_CONFLICT`)

| # | Case | Behaviour |
|---|---|---|
| 1 | Exact same-run replay (input identity equal, recomputed semantic output identity equal, persisted item/link set re-derived from the rows equal) | **Zero writes of any kind** — no item, link, completion or audit row. Receipt: `replayed=True`, `evaluation_completed=True`, `review_items_persisted=0`, `review_items_total=item_count`, identities echoed from the stored completion record |
| 2 | Existing **extra** review items not in the recomputed set | reason `extra_persisted_items`; zero writes; no DELETE, no supersession |
| 3 | **Missing** previously persisted items or evidence links | reason `missing_persisted_evidence`; zero writes; no repair, no append-to-old-result |
| 4 | Changed complete-history fingerprint with **unchanged** candidate dedupe keys | reason `input_identity_changed` — per-row dedupe equality is explicitly **not** sufficient (RB3-D01) |
| 5 | Changed candidate set with **unchanged** F1 fingerprint | reason `output_identity_changed` |
| 6 | Original **zero-item** evaluation (including the T8a empty-selection path) | Completion row with `item_count=0`, `evidence_link_count=0`, `exclusion_count=<derived>`, plus the single audit row; commit. Receipt: `evaluation_completed=True`, `review_items_persisted=0`, `review_items_total=0`, `replayed=False` |
| 7 | Repeated zero-item evaluation | case 1 semantics; `review_items_total=0` |
| 8 | Zero-item evaluation followed by new nonempty output | reason `output_identity_changed`; zero writes; no UPDATE, no second completion row (UNIQUE per run), no append-to-old-result |
| 9 | Nonempty evaluation followed by zero output | reason `output_identity_changed`; zero writes |
| 10 | Existing audit row without a matching item/link set | reason `audit_business_inconsistent`: RB3 re-reads the row via `audit_event_id` and validates `event_type`, `actor_type`, `actor_id`, `patient_id`, `workflow_run_id`, `subject_type`, `subject_id`, `outcome` and that `safe_detail` still carries the recorded identities and counts |
| 11 | Existing item/link set without the required completion evidence | reason `completion_evidence_missing`; rows whose originating evaluation cannot be proved are never adopted, extended or repaired |
| 12 | Concurrent invocation | The second writer blocks on `BEGIN IMMEDIATE`, then resolves as case 1 or 4/5/8/9; `ux_review_evaluation_run` is the structural backstop → `IntegrityError` → rollback → conflict, never a partial write |
| 13 | Rollback and retry | A rolled-back attempt persisted nothing; the retry is a first evaluation. Equivalence is semantic; new UUIDs are expected and accepted |

**One-evaluation-per-run invariant re-confirmed (§11 question):** `UNIQUE (workflow_run_id)` plus G12/G13 immutability means a zero-item evaluation occupies the single slot exactly as a nonempty one does (cases 6–7), and any later differing evaluation — whether from changed inputs (case 4) or changed output (cases 5, 8, 9) — is a typed conflict rather than a second record, an UPDATE or a supersession. Supersession remains reserved vocabulary requiring its own future owner authorization.

Prohibited in every case: silent repair, append-to-old-result, duplicate audit rows, UPDATE, DELETE, supersession, and any second committed write path. Uniqueness conflicts on `ux_review_dedupe`, `ux_review_order`, `ux_review_evaluation_run`, `ux_evidence_link_observation` or `ux_evidence_link_span` are caught as `IntegrityError`, rolled back and reported as typed conflicts — never retried blindly.

### 8.3 Receipt semantics (`ReviewPersistenceReceiptV1`, proposed)

`contract_version='p4-rb3-receipt-1.0.0'`; run/patient/doctor ids; `as_of_utc`, `policy_version`, `policy_reference_sha256`; `gate_evaluation_id`, `gate_version`, both upstream fingerprints; `rb3_fingerprint_version`, `input_fingerprint_sha256`, `output_identity_sha256`; `evaluation_id`; `audit_event_id`; `lineage_label_policy`; `dr006_policy: Literal['persisted','prohibited_denied','not_present']`; and the honesty fields `evaluation_completed: Literal[True]`, `replayed: bool`, `review_items_persisted: int` (this invocation), `review_items_total: int`, `evidence_links_persisted: int`, `evidence_links_total: int`, `excluded_evidence: tuple[(observation_id, reason), ...]`, `offline_evaluator_invoked: Literal[True]`, `runtime_evaluable: Literal[False]`, `policy_status: Literal['unapproved']`, `demo_only: Literal[True]`, `not_for_clinical_use: Literal[True]`.

**Zero-item receipts distinguish a completed durable evaluation from persisted review items:** `evaluation_completed=True` with `review_items_persisted=0` and `review_items_total=0` means "the evaluation ran, was proved and was recorded, and produced no items" — not "nothing happened" and not "the evaluator was skipped". RB3 uses its **own** field names and never reinterprets RB2's frozen result literals (`OfflineRuleResult.review_items_persisted=False` remains a statement about the offline evaluator, not about RB3's write).

### 8.4 Audit identity, insertion order and verification (**RB3-D05**, **RB3-R3-02**)

One audit row per **first** completed evaluation, written inside the same transaction at T15 step 4 — **after** the item and link inserts and **before** the completion-row insert, because `review_evaluation.audit_event_id` is a NOT NULL FK and SQLite FKs are immediate:

```python
event = append_audit_event(
    db,
    event_type="workflow.review.persisted",   # additive; event_type has no CHECK (models.py; DD §2.17)
    actor_type=ActorType.USER,                # a doctor is a Role; ActorType has no doctor member
    actor_id=principal.user_id,
    outcome=AuditOutcome.OK,
    request_id=request_id,                    # server-owned request identity
    now=validation_clock,
    patient_id=run.patient_id,
    workflow_run_id=run.id,
    subject_type="review_evaluation",
    subject_id=evaluation_id,                 # pre-generated; subject_id has NO foreign key
    detail_fragments=(
        "fingerprint_version=rb3-full-input-1.0.0",
        f"input={input_fingerprint_sha256}", f"output={output_identity_sha256}",
        f"gate={gate_input_fingerprint_sha256}", f"bridge={bridge_input_fingerprint_sha256}",
        f"policy={policy_version}", f"lineage_label_policy={lineage_label_policy}",
        f"items={item_count}", f"links={evidence_link_count}", f"exclusions={exclusion_count}",
        "demo_only=1",
    ),
)
```

`safe_detail()` collapses whitespace and truncates to `SAFE_DETAIL_MAX = 500`; the fragments are literals, enum values, hex digests and small integers. The implementation PR must assert the composed length in a test rather than rely on truncation, since silent truncation would weaken corroboration. **No clinical prose, document text, `raw_text`, credential, token or free-text note** appears in any fragment (`REQ-AUDIT-02`).

**Validating the returned row (T15 step 5).** `append_audit_event` may return a **pre-existing** row matched by key alone, without comparing content (`:124-128`). RB3 reaching T15 means T14 found **no** completion record, i.e. this is a first evaluation; and `evaluation_id` was freshly generated at T15 step 1. Therefore a returned row whose `id`/`subject_id`/`workflow_run_id`/`safe_detail` identities do not match this invocation cannot be a legitimate prior record of *this* evaluation — it indicates a duplicated `request_id` or a key collision. RB3 fails closed: `409 E_IDEMPOTENCY_CONFLICT`, reason `audit_key_collision`, rollback, zero writes. RB3 never adopts an unmatched pre-existing audit row as its completion evidence.

**Deferred-FK alternative, evaluated and rejected.** Deferring `review_evaluation.audit_event_id` (`PRAGMA defer_foreign_keys` / `DEFERRABLE INITIALLY DEFERRED`) would permit inserting the completion row first. Rejected because: it changes connection-level pragma behaviour for the whole transaction rather than one insert; no existing migration in this repository declares a deferred constraint, so it would be a new, less-reviewed pattern; it makes the intermediate state transiently FK-invalid, which any concurrent reader or a crash between statements could observe; and it is unnecessary — reordering two inserts achieves the same result with immediate constraints. The chosen order also lets G14 assert that the referenced audit row exists.

**No committed denial audit:** `record_denial` commits (`:170-190`) and is prohibited. Audit/business-row consistency is structural as well as procedural: G14 requires `item_count`/`evidence_link_count` to equal the actual row counts and the audit row to exist; `ux_review_evaluation_run` forbids a second completion row; G12/G13 make it immutable — so the audit row, completion row and business rows are written together or not at all.

---

## 9. (G) Migration safety

### 9.1 Actual head and the proposed additive migration

Verified head `0007_p5_run_gate` (`:15-16`), corroborated by `HEAD_REVISION` pins in `tests/test_database.py:22`, `tests/p2/test_p2_migration.py:46` and `scripts/python/check_alembic_smoke.py:70`.

Proposed (not implemented): `0008_p4_rb3_review_persistence`, `down_revision = "0007_p5_run_gate"`. Upgrade creates `review_item`, `evidence_link`, `review_evaluation`, their indexes (including both partial unique indexes) and the 14 triggers of §6.4, in FK-safe order (`review_item` → `evidence_link` → `review_evaluation`, since G9/G10/G14 read the earlier tables and `audit_event` already exists from `0002`). No existing table, column, constraint, index or trigger is altered, rebuilt or dropped, so no batch rebuild and no risk of silently losing an accepted CHECK, index or row.

**Nonempty databases:** purely additive DDL; all existing rows in `patient`, `user`, `document`, `document_page_text`, `observation`, `extracted_fact`, `fact_verification`, `verification_issue`, `workflow_run`, the three manifest tables, `run_gate_evaluation`, `run_gate_blocker` and `audit_event` remain untouched and valid. New FKs reference existing parents only; no column is added to an existing table, so no backfill is required or possible.

**Downgrade** refuses when any RB3 object holds data, following the accepted `0006` pattern (`:165-184`):

```python
def _rb3_persisted_evidence() -> bool:
    conn = op.get_bind()
    for table in ("review_item", "evidence_link", "review_evaluation"):
        if conn.execute(sa.text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar_one():
            return True
    return False

def downgrade() -> None:
    if _rb3_persisted_evidence():
        raise RuntimeError(DOWNGRADE_REFUSED_MESSAGE)   # archive via an approved operator process; no data removed
    # triggers first, then indexes (index-before-drop ordering per 0003:281-283),
    # then tables in reverse dependency order: review_evaluation, evidence_link, review_item
```

`DOWNGRADE_REFUSED_MESSAGE` follows the `0006` wording shape and names `0008_p4_rb3_review_persistence`. On an empty database the predicate is false, so downgrade drops all 14 triggers, all RB3 indexes and all three tables and restores the exact `0007` schema — the accepted empty-database reversibility tests (`tests/test_database.py:110`; `tests/p2/test_p2_migration.py:224`, `:251`) therefore pass **unchanged**, a deliberate narrowing of the E1/E2 deltas.

**Legacy historical states:** the staged expectations in `check_alembic_smoke.py` (`_expected_tables` `:199-211`, `_expected_revisions` `:214-220`) pin `p1`, `p2`, `p3`, `p3_recovery`, `p3_stage1`, `p5_f0` to their historical sets. RB3 adds a new pinned historical state for `0007` (proposed key `p5_f1`) so the pre-RB3 schema stays asserted after `head` advances, and extends only the `head` state. No historical expectation is rewritten.

### 9.2 Existing guards a new head provably trips (exact paths, minimal deltas, none weakened/skipped/replaced, none modified in this PR)

| ID | Path | Assertion that trips | Minimal future delta (each needs its own fresh owner marker) |
|---|---|---|---|
| **E1** | `backend/tests/test_database.py` | `HEAD_REVISION = "0007_p5_run_gate"` (`:22`, asserted `:85`); `FUTURE_TABLES` contains `review_item` (`:59-65`) with `assert tables.isdisjoint(FUTURE_TABLES)` (`:99`); exact set equality (`:88-97`) | Advance `HEAD_REVISION`; remove **only** `review_item` from `FUTURE_TABLES` (keeping `summary_draft`, `approval_decision`, `follow_up_task`, `in_app_notification` forbidden); add `P4_RB3_TABLES = {"review_item","evidence_link","review_evaluation"}` to the exact-equality set. `test_migration_is_reversible` (`:110`) needs **no** change |
| **E2** | `backend/tests/p2/test_p2_migration.py` | `HEAD_REVISION` (`:46`, asserted `:241`, `:263`); `test_migration_matches_the_orm_metadata` (`:314-331`) compares tables **and index names** to `Base.metadata` | Advance `HEAD_REVISION`; satisfy parity per §6.7. The parity assertion itself is kept exactly as accepted |
| **E3** | `backend/tests/p2/test_p2_scope_guards.py` | `P4_PLUS_TABLES` (`:62-71`) with `assert tables.isdisjoint(P4_PLUS_TABLES)` (`:123`) and its exact table-set assertion | Remove **only** `review_item`/`evidence_link` from the disjointness set, **add** `review_evaluation` to it (so the new object stays forbidden below `0008`), and extend the exact head set with `P4_RB3_TABLES`. All other later-phase tables stay forbidden |
| **E4** | `scripts/python/check_alembic_smoke.py` | `HEAD_REVISION` (`:70`); `_expected_tables("head")` (`:199-201`); `_expected_revisions("head")` (`:217`); early-table gate `P4_PLUS_TABLES & tables` (`:131`, `:336-338`); F1-stage index/trigger expectations (`:434+`) | Advance `HEAD_REVISION`; add `P4_RB3_TABLES` to the `head` expectation only; add `review_evaluation` to `P4_PLUS_TABLES`; add the pinned historical `p5_f1` state; add RB3-stage expectations (three tables, named indexes including both partial unique indexes, and all 14 trigger names via `sqlite_master`). No existing stage is relaxed |
| **E5** | `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (enforcer `backend/tests/p3/test_windows_ocr_acceptance.py`, itself unchanged) | The literal pairing `**1255 collected**, of which **443** are the P3 suite`; any new backend test file changes the collected total | An **append-only** note recording the **actual future measured** backend/P3 pairing once the RB3 test files exist, authorized by a **fresh standalone collection-only marker** (proposed form `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`, following `APPROVE-P4-RB1-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION`, `APPROVE-P4-RB2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION`, `APPROVE-P4-RB2-P3-HANDOFF-1255-COLLECTION-ONLY`). The numbers must be the real future measurements; this is **not** a reusable generic permission, and the historical 1255/443 evidence is preserved untouched |
| **E6** | `backend/app/services/p5_run_gate.py` | `inspect_current_run_gate_locked` docstring "Only the F2 bridge may call this…" (`:862-868`) — already inaccurate, since RB1 also calls it (`p4_run_bound_preview.py:101`) | **Conditional, docstring-only** clarification naming the actual callers (F2, RB1, and RB3 as an additional locked-read caller); zero logic/signature/behaviour change (**D-RB3-02b**). Fallback if refused: leave the source untouched and record the deviation in an append-only `TOOL_CONTRACTS.md` note |

Guards verified **not** tripped: `.github/workflows/ci.yml` and `tests/test_ci_workflow.py`; `scripts/python/check_openapi.py` (no router/path/operation/schema change — RB3 exposes no HTTP surface); `scripts/python/scan_repository.py`; the P2 API tests hard-coding `review_items=[]`; RB1/RB2 sources, schemas and tests (frozen); `data/synthetic/policy/demo_review_policy.yaml` and the GOLD JSON fixtures; existing `backend/tests/p4/*` (extended only by new files). Required legacy compatibility changes: none beyond E1–E6.

---

## 10. Exact future RB3 implementation allowlist (proposal — nothing authorized yet)

### 10.1 Normal proposed RB3 paths

| ID | Path | Why required | Authorizing contract | Prohibited from changing |
|---|---|---|---|---|
| N1 | `backend/app/services/p4_rb3_review_persistence.py` (new) | Service boundary, T1–T16, fresh reconstruction and complete T6 eligibility derivation, full-input fingerprint, span resolution, replay resolution, corrected insertion order | `TOOL_CONTRACTS.md` F2/RB1/RB2 sections; `STATE_AND_GRAPH_CONTRACT.md` §7; `EXTRACTION_PROVENANCE.md` §5; `AGENTS.md` §3 | No HTTP router, agent tool, graph node, task or notification; no private-helper import; no call to `evaluate_run_verification_gate` or `record_denial`; no weakening of the pinned clock/policy |
| N2 | `backend/app/schemas/p4_rb3_review_persistence.py` (new) | `ReviewPersistenceReceiptV1` and typed denial reasons | `DATA_DICTIONARY.md` §§2.9–2.10; `TOOL_CONTRACTS.md` | Must not reinterpret RB2's frozen literals; must not expose a clearance/authority field |
| N3 | `backend/app/db/models.py` (additive ORM only) | Declare `ReviewItem`, `EvidenceLink`, `ReviewEvaluation` and every index for parity | `DATA_DICTIONARY.md` §§2.9–2.10 (+ proposed §2.10a note) | Additive only: no change to any existing model, column, constraint, relationship or index |
| N4 | `backend/migrations/versions/0008_p4_rb3_review_persistence.py` (new) | Create three tables, indexes and 14 triggers; refuse destructive downgrade | `DATA_DICTIONARY.md` §5.1; the `0006` precedent | No alteration or drop of any existing object; no rewriting a historical migration; no relaxing the refusal predicate |
| N5 | `backend/tests/p4/test_p4_rb3_review_persistence.py` (new) | The §11 matrix: authority, transactions, fingerprint, eligibility equivalence, span resolution, replay, provenance | `AGENTS.md` §4 | Must not edit an existing test, fixture or golden file |
| N6 | `backend/tests/p4/test_p4_rb3_migration_guards.py` (new) | Migration, trigger, parity, FK-order, downgrade-refusal and bound adversarial cases | `DATA_DICTIONARY.md` §5.1 | Same |
| N7 | `docs/contracts/DATA_DICTIONARY.md` (append-only note) | Record the RB3 realization of §§2.9–2.10, the additive `display_order` and `provenance_status` columns (**C-RB3-05**, **C-RB3-07**), the §2.10-vs-§5 span reconciliation, and the proposed §2.10a `review_evaluation` | `DATA_DICTIONARY.md` | Append-only; no existing row, type or constraint rewritten |
| N8 | `docs/contracts/TOOL_CONTRACTS.md` (append-only note) | Record the RB3 service boundary, the transport-label semantics (**C-RB3-01**), the DR-006 decision (**C-RB3-02**) and, if E6 is refused, the docstring deviation | `TOOL_CONTRACTS.md:270`, `:279` | Append-only |
| N9 | `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (append-only note) | Record the RB3 input/output identities and invocation-level replay semantics alongside §7 | §7 | Append-only |
| N10 | `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_<date>.md` (new) | The future implementation review with real commands, exit codes, CI evidence and the **C-RB3-08** DR-006 reachability proof outcome | `AGENTS.md` §4 | Must not claim an unexecuted check |
| N11 | `docs/phase-reports/PHASE_4_REPORT.md` (append-only) | Phase checkpoint | `AGENTS.md` §1 | Append-only; historical evidence preserved |
| N12 | `docs/roadmap/PHASE_PROGRESS.md` (append-only) | Owner-decision and execution checkpoint | `AGENTS.md` §1 | Append-only; the literal P3-handoff phrase elsewhere untouched |
| N13 | `docs/clinical-safety/DEMO_REVIEW_RULES.md` (append-only note, **only if** D-RB3-08 option (ii) is ratified) | Record the conservative DR-006 prohibition and its whole-invocation fail-closed behaviour | `DEMO_REVIEW_RULES.md` §10 | Append-only; no rule definition, message template or parameter altered |

No blanket directory authorization is granted or requested. Module naming avoids every name forbidden by `tests/p2/test_p2_scope_guards.py` (`reviews.py`, `review_rules.py`, `comparisons.py`, `summary.py`, `workflows.py`, `tasks.py`, `orchestrator.py`, `notifications.py`) and creates no `app/agents` or `app/llm` package.

### 10.2 Exceptional cross-phase paths (each requires its own explicit owner authorization recorded in the roadmap **before** any edit)

E1 `backend/tests/test_database.py` · E2 `backend/tests/p2/test_p2_migration.py` · E3 `backend/tests/p2/test_p2_scope_guards.py` · E4 `scripts/python/check_alembic_smoke.py` · E5 `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (enforcer unchanged) · E6 `backend/app/services/p5_run_gate.py` (conditional, docstring-only). Deltas are exactly those in §9.2. E5's authorization must state the actual future measured backend/P3 pairing and must not be a reusable generic permission.

---

## 11. Acceptance test matrix for the future RB3 implementation PR (requirements — none executed)

RB3-01..RB3-66 carry forward from Revision 2 with the corrections noted; RB3-67..RB3-81 are new for Revision 3. Every case states its expected outcome and failure code. **No matrix result is claimed as executed.**

| ID | Case | Expected outcome / failure code |
|---|---|---|
| RB3-01 | Happy path: synthetic assigned-doctor run, stored PROCEED, pinned clock/policy, fresh evidence | Items + links + audit + completion row committed in the T15 order; receipt `evaluation_completed=True`, `replayed=False`, `review_items_persisted=item_count` |
| RB3-02..05 | Missing / stale / HALT / UNAVAILABLE F1 gate | `409 E_VALIDATION`; zero writes |
| RB3-06 | `BEGIN IMMEDIATE` raises `OperationalError` | `503 E_VALIDATION`; never a success receipt |
| RB3-07 | Foreign patient/run/document/observation/fact reference | `403 E_SCOPE_VIOLATION`; zero writes |
| RB3-08..12 | Revoked session; expired session; **session owned by another user**; reassigned patient; non-synthetic patient | `403 E_FORBIDDEN` / `403 E_SCOPE_VIOLATION` |
| RB3-13..14 | Run not `queued` or execution-state columns non-NULL; run version mismatch | `409 E_VALIDATION` |
| RB3-15..16 | Tampered source bytes; tampered verification decision | `409 E_VALIDATION` (T3 and T16 re-hash; fingerprint change) |
| RB3-17..18 | Policy tampering; clock mismatch | `409 E_VALIDATION` |
| RB3-19 | **Corrected:** zero selected current observations, exercised through the **complete** T8a path (see RB3-71) | Durable completed evaluation; `no_current_selected` asserted; empty comparisons; receipt distinguishes completion from row persistence |
| RB3-20 | Input caps: >6 current, >100 history, >40 facts, >5/<1 documents | fail closed (`409 E_VALIDATION`; RB2 typed error mapped per §4.4); zero writes |
| RB3-21 | Typed exclusions surfaced (`validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp`, `verified_lineage_unavailable`, `verified_mapping_unproven`, `stored_trust_source_mismatch`, `missing_created_at`) | All present in `receipt.excluded_evidence`; never dropped or fabricated |
| RB3-22 | No trust promotion | `trust_basis` exactly as emitted; denial if promotion would be required |
| RB3-23..24 | Duplicate replay; concurrent invocation | Zero writes / `replayed=True`; one writer persists, the other replays or conflicts; no partial write |
| RB3-25..26 | Partial write failure then rollback; `ux_review_dedupe` conflict | Nothing persisted; `IntegrityError` → rollback → `409 E_IDEMPOTENCY_CONFLICT` |
| RB3-27..28 | Unresolvable span for a `fact:` key; link to another patient's row | `409 E_VALIDATION` (whole invocation); structural refusal by G10 / `403 E_SCOPE_VIOLATION` at T13 |
| RB3-29..31 | Migration from the genuine head on a populated DB; nonempty downgrade refusal; empty-DB round trip | Upgrade succeeds with all rows intact; `RuntimeError(DOWNGRADE_REFUSED_MESSAGE)` with schema unchanged; exact `0007` schema restored |
| RB3-32 | Historical P3 issues preserved | Unchanged except by an E5-authorized append-only note with real measured numbers |
| RB3-33..40 | R01–R08 regression, one case each, with the corrected expectations (R03 exclusion not denial; R04 DR-003 newest-admissible across selected **and** historical; R07 year-one timestamp handled without overflow; R08 `121.1 - 100` persists DR-005 with the exact decimal delta) | Frozen evaluator behaviour preserved end-to-end through persistence |
| RB3-41..44 | No graph/LLM/API/task/notification activation; no caller-supplied authority accepted (signature assertion); RB2 frozen (zero diffs); RB3↔RB2 output equivalence | Enforced |
| RB3-45..49 | Newly added eligible history; changed non-baseline value with unchanged baseline comparison; changed historical `created_at`; changed eligibility with no column change; unchanged baseline with changed rule output | Detected and denied (`409 E_VALIDATION` or `409 E_IDEMPOTENCY_CONFLICT` reasons `input_identity_changed` / `output_identity_changed`); asserts explicitly that F2 bridge-fingerprint equality would **not** have caught the value/`created_at` cases |
| RB3-50..52 | Cached exclusion ids offered as authority; fingerprint stability across loader orderings; changed `Observation.note` only | Fresh derivation governs; identical `input_fingerprint_sha256`; RB3 digest unchanged while the F1 digest changes → denial, proving no free text enters RB3 artifacts |
| RB3-53 | Field-to-source mapping: no reliance on a nonexistent preview attribute | No `AttributeError`; every version field sourced per §2.4 |
| RB3-54..57 | All 14 triggers exist and fire (via `sqlite_master` and direct SQL bypassing the ORM); state/owner/kind vocabulary reserved but not writable; over-length `message`/`reason_code`/`dedupe_key`/`id`/`created_at` refused by `length()` CHECKs; duplicate identity refused | Each raises its documented `RAISE(ABORT,…)`; no UPDATE/DELETE succeeds on any RB3 table |
| RB3-58 | ORM/migration parity with three tables and both partial indexes | Name-level equality for every table and index |
| RB3-59..61 | Zero-item → nonempty and nonempty → zero; repeated zero-item; extra/missing persisted rows | `409 E_IDEMPOTENCY_CONFLICT` reasons `output_identity_changed`, `extra_persisted_items`, `missing_persisted_evidence`; completion row immutable |
| RB3-62..63 | Audit row present but item/link set inconsistent; items/links without a completion row | reasons `audit_business_inconsistent` / `completion_evidence_missing`; explicit content validation |
| RB3-64 | Rollback then retry | Retry persists as a first evaluation; semantic output identical; new UUIDs differ and are accepted |
| RB3-65 | Audit semantics: `actor_type='user'` for a doctor; `safe_detail` ≤500 with no clinical prose, document text, `raw_text`, credential or free-text note; exactly one audit row per first evaluation and none on replay; `record_denial` never called | Enforced |
| RB3-66 | **Corrected DR-006 case (see §7.4 and C-RB3-08).** Unit level: feed the evaluator two qualifying stored-proved rows (same measure type, identical `measured_at`, differing values, distinct documents and facts) and assert the ratified behaviour — under D-RB3-08(i) persist with **six** links and `provenance_status` stored verbatim and no trust promotion; under (ii) deny the **whole** invocation with reason `dr006_persistence_not_authorized` and zero writes. Integration level: the implementation PR must either construct a genuine PROCEED run reaching DR-006 through the accepted F1/F2 contracts, or prove from the accepted extraction/issue logic that none exists and record that proof. **No fixture may be invented**; Revision 2's non-selected-document fixture is withdrawn as provably impossible | Never a partial persist; never a silently dropped item; no unproven reachability assertion |
| **RB3-67** | All six valid `rule_id` values (`DR-001`, `DR-003`, `DR-005`, `DR-006`, `DR-008`, `DR-009`) insert successfully | Each accepted; `length(rule_id) = 6` satisfied |
| **RB3-68** | Retired ids `DR-002`, `DR-004`, `DR-007`, `DR-010`, a seven-character variant such as `DR-0001`, and an empty/whitespace id | All rejected by the closed CHECK / length CHECK; asserts the Revision-2 `length = 7` assumption would have rejected every legitimate insert |
| **RB3-69** | **Audit FK insertion order:** assert the persisted row order (items → links → audit → completion) and that `review_evaluation.audit_event_id` equals the audit row's actual id, with immediate FKs enabled and no deferred constraint | Insert succeeds; reversing the order (completion before audit) raises an FK violation, proving the corrected order is necessary |
| **RB3-70** | **Audit helper returns a pre-existing row** at T15 step 5 (duplicated `request_id` / key collision) | `409 E_IDEMPOTENCY_CONFLICT` reason `audit_key_collision`; rollback; zero writes; the unmatched row is never adopted |
| **RB3-71** | **Empty selected-current path end-to-end** through T4→T5→T6→T7→**T8a**→T9→T10→T11→T13→T14→T15→T16 (not the evaluator in isolation): assert `compare_explicit_current_with_history` is **never called**, RB1's `no_current_selected` semantics hold, comparisons are empty, RB2 receives an empty `selected_current` tuple, and a durable zero-item completion record plus audit row are committed | Completed evaluation with `item_count=0`; receipt `evaluation_completed=True`, `review_items_persisted=0`, `review_items_total=0` |
| **RB3-72** | **F2 `source_reason` equivalence:** for every branch (verified-document lineage identity; `source_document_id ∉` selected set; stored value-fact patient/document/field/status; zero or two verified `test_name` facts; unmapped alias; measure-type mismatch; unit mismatch against either the observation or the fact; `patient_checkin`/`seed_fixture` trust or non-null `source_fact_id`; unknown source), RB3's T6 derivation produces the same exclusion code as F2 | Exact set-and-reason equality with `evidence.history_exclusions`; no spurious `409` on valid paths |
| **RB3-73** | **Non-selected verified-document history row** (source document outside the selected set) | Excluded `verified_lineage_unavailable` at T6; never reaches the evaluator; equality with F2's cached exclusion holds |
| **RB3-74** | **Selected documents failing only F1's `report_date` shape gate while passing F2's mapping checks** | F1 constructs no VI-006 candidate (documented divergence); F2 accepts the provenance; the run's gate outcome is asserted from the actual accepted logic, and the case records whether DR-006 became reachable — feeding the **C-RB3-08** proof obligation rather than assuming an outcome |
| **RB3-75** | **All six DR-006 evidence keys** (`observation:first`, `observation:second`, `document:first`, `document:second`, `fact:first`, `fact:second`) | Six persisted links: two `observation`, two `document_span` from the verified `test_name` facts, two `document_span` from the verified `value` facts; neither observation reference dropped |
| **RB3-76** | **Exact stored document spans** for both `document:` and `fact:` references | Each link's `page_index`/`char_start`/`char_end` equals the stored fact's span and satisfies §5 rule 1 (`char_end > char_start`, within `max_page_text_chars`, `page_text[char_start:char_end] == raw_text[:300]`) |
| **RB3-77** | **Missing or unresolvable document span** (absent `document_page_text` row, coordinates out of range, substring mismatch, or `char_end == char_start`) | `409 E_VALIDATION`; the **whole** invocation fails; no fabricated coordinates; no NULL-span substitute |
| **RB3-78** | **Exact six `reason_code` literals** persisted per rule | `missing_baseline`, `measurement_stale`, `change_exceeds_demo_parameter`, `verified_source_conflict`, `duplicate_or_out_of_order`, `implausible_value`; any other value rejected by the closed CHECK |
| **RB3-79** | **`provenance_status` persistence** under the ratified D-RB3-10 option: Option A → each item stores the evaluator's literal verbatim and the value appears in `output_identity_sha256` (changing it changes the identity); Option B → the documented non-persistence consumer contract is asserted instead | No persisted item can appear to be a real doctor attestation |
| **RB3-80** | **Structural bounds:** `item_count ≤ 12` and `evidence_link_count ≤ 72` (and `≥ item_count`) | CHECKs enforced; a 13th item or 73rd link is rejected; the 72 derivation is asserted from the six call-site reference counts |
| **RB3-81** | **`policy_reference_sha256` structural pin** (if D-RB3-05e is ratified) | Any value other than the exact R3-A digest is rejected by CHECK |

**RB4 separation (unchanged).** Run-backed GOLD A/B/C/D final acceptance is a separate future activity. GOLD-D-shaped cases used here as implementation regressions (for example the expected rule set `[DR-001, DR-003, DR-005, DR-008, DR-009]`, five items, a diastolic delta of 168, or a duplicate systolic 130 at `2026-10-20T09:00:00Z`) are **not** an RB4 acceptance claim and must never be reported as one.

---

## 12. Explicit owner decisions requested (no approval assumed)

| ID | Exact question | Relevant contract | Alternatives | Recommendation | Trade-offs | Exact authorization scope |
|---|---|---|---|---|---|---|
| **D-RB3-01** | Internal authenticated service only (no endpoint, agent tool, graph node, task, notification)? | `TOOL_CONTRACTS.md` boundary sections; `AGENTS.md` §3 | (a) internal service; (b) doctor endpoint; (c) graph node | **(a)** | (a) smallest surface, no OpenAPI change; (b)/(c) create runtime surface the phase has not accepted | Binds N1/N2 shape |
| **D-RB3-02** | Two-phase architecture: verified read-only pins (all of which roll back), then one independently controlled committing `BEGIN IMMEDIATE` with the corrected T1–T16 sequence? | `p5_run_gate.py:887-925`; `p5_evidence_bridge.py:330-344`, `:470-473`; `STATE_AND_GRAPH_CONTRACT.md` §7 | (a) as designed; (b) one transaction incl. F2 projection; (c) best-effort writes | **(a)** | (a) honest about non-atomicity, accepted helpers unchanged; (b) would require re-owning F2's read path; (c) permits partial persistence — rejected | Binds §3, N1 |
| **D-RB3-02b** | Prefer the separately authorized **docstring-only** E6 clarification (naming F2, RB1 and RB3 as the actual callers) over knowingly contradictory source documentation? | `p5_run_gate.py:862-868`; `p4_run_bound_preview.py:101` | (a) docstring-only E6; (b) leave source, add an append-only contract note | **(a)**, with (b) as fallback | (a) removes a real contradiction with zero logic risk; (b) keeps P5 bytes untouched but leaves misleading text | At most a docstring edit in one file |
| **D-RB3-03** | Approve **Alt A2** (unchanged RB2 as pure computation core; `fixture_asserted` strictly as a documented transport label; mandatory independent in-transaction stored-lineage proof; per-item `provenance_status` persisted verbatim; equivalence tests; append-only contract note) — or **Alt B** (RB3-owned re-derivation)? | `TOOL_CONTRACTS.md:270`; schema `:67-69`; `p4_rb2_offline_rules.py:221-225`, `:247-257`, `:316-321` | A2 / B / C (modify RB2) | **A2** with §4.3's conditions; **C rejected** | A2: one reviewed core, R01–R08 inherited, zero RB2 diffs; cost: a transport label that must be documented honestly, and DR-006 stays live. B: honest labels, duplicated logic, divergence risk, DR-006 inert by construction. Neither weakens the pinned clock/policy/validation | Binds N1/N5/N8 and the RB2 freeze |
| **D-RB3-04** | Retain exact pinned demo clock and policy binding (no wall clock, no conversion)? | `p4_run_bound_preview.py:37-39`, `:114-125`; `DEMO_REVIEW_RULES.md` §7 | (a) exact equality; (b) any run clock with a relative window | **(a)** | (a) deterministic, no weakening; (b) would generalize the demo beyond its accepted scope | Binds §2.2, §4.1, N1 |
| **D-RB3-05** | Approve the stricter structural package: full UPDATE/DELETE immutability on all three tables; the exact 14-trigger inventory; `length()` CHECKs; kind-conditional span NOT NULL with strict `char_end > char_start`; partial unique indexes plus G11 as defence-in-depth? | `0006:31,136,156-162`; `0003:263,267-277`; `0002:289` + `models.py:278-287`; `EXTRACTION_PROVENANCE.md` §5; `test_p2_migration.py:314-331` | (a) full package; (b) immutability for `review_item` only; (c) application-layer only | **(a)** | (a) integrity survives SQL bypassing the service layer; cost: 14 triggers and more migration tests. (b)/(c) leave bypass paths open | Binds N3/N4/N6 |
| **D-RB3-05a** | Pin `policy_version` and `as_of_utc` to literal values by structural CHECK on `review_item` and `review_evaluation`? | `0006:133-135`; DD §§2.9, 5.1 | (a) literal CHECK; (b) application-layer only | **(a)** | (a) makes the demo scope structural; cost: a future policy version needs a migration | Binds N4 |
| **D-RB3-05b** | Approve additive `review_item.display_order` (beyond §2.9) to preserve the evaluator's stable ordering durably? (**C-RB3-05**) | DD §2.9; `p4_rb2_offline_rules.py:490-495` | (a) additive column + `ux_review_order`; (b) re-derive order at read time | **(a)** | (a) order cannot silently drift; cost: one column beyond the dictionary plus an append-only note | Binds N3/N4/N7 |
| **D-RB3-05c** | Reserve `checkin_note`, `verification_issue` and `summary_claim` vocabulary while making them structurally unwritable (G7/G8)? | DD §2.10 | (a) reserve + trigger-block; (b) drop the values from the CHECK | **(a)** | (a) preserves the dictionary's future vocabulary while forbidding unsupported orphan ownership; (b) would contradict the contract | Binds N4 |
| **D-RB3-05d** | Two-layer evidence-identity uniqueness (partial unique indexes + NULL-safe G11) rather than a COALESCE expression index? (**C-RB3-04**) | `0002:289`; `models.py:278-287`; `0003:263`; `test_p2_migration.py:314-331` | (a) partial indexes + trigger; (b) expression index | **(a)** | (a) accepted in-repo patterns, parity-safe by name, and — after the span correction — sufficient on its own; (b) compact but parity unproven | Binds N3/N4/N6 |
| **D-RB3-05e** | Structurally pin `review_evaluation.policy_reference_sha256` to the exact R3-A digest `f3bdad3f…bd36` by CHECK, rather than only `length() = 64`? | `p4_run_bound_preview.py:37`; `0006:133-136` literal-pinning precedent | (a) exact-digest CHECK; (b) length-only CHECK plus service assertion | **(a)** | (a) a wrong or re-sealed policy digest becomes structurally impossible; cost: re-sealing requires a migration and a fresh owner decision | Binds N4, RB3-81 |
| **D-RB3-05f** | Add a first-class `fact_id` column to `evidence_link` (a §2.10 amendment), or keep representing `fact:` references by their verified value-fact span with the fact identity preserved in the input/output identities? (**C-RB3-07**) | DD §2.10; `EXTRACTION_PROVENANCE.md` §5 | (a) span representation, no amendment; (b) amend §2.10 with a NULL-able `fact_id` FK | **(a)** for this slice | (a) needs no contract change and is span-resolvable per §5; cost: the fact id is not directly queryable from the link row. (b) is more queryable but amends an accepted contract and enlarges the migration | Binds N4/N7 if (b) |
| **D-RB3-06** | Approve the pre-planned exceptional paths E1–E5 plus conditional E6, **each** still requiring its own fresh standalone marker before any edit? | `AGENTS.md` §5; the RB1/RB2 precedents | (a) per-path fresh markers; (b) one blanket marker | **(a)** | (a) keeps each guard change individually reviewable; (b) would grant unrestricted cross-phase editing — rejected | Authorizes nothing now; defines the future request shape |
| **D-RB3-07** | Approve the revised invocation-level receipt, replay and audit semantics: one immutable completion record per run; **zero writes** on exact replay; `audit_event_id` stored so the audit row's identity **and** content are validated; the corrected T15 insertion order with `audit_key_collision` fail-closed; no committed denial audit; receipt fields distinguishing durable completion from row persistence? | `audit.py:49-74`, `:124-146`, `:170-190`; DD §2.17; `STATE_AND_GRAPH_CONTRACT.md` §7 | (a) as designed; (b) audit row per invocation; (c) rely on the audit key alone; (d) deferred FK | **(a)** | (a) no duplicate audit, no unsound replay proof, immediate FKs only; (b) duplicates the trail; (c) unsound (request-scoped key, no content comparison); (d) changes connection-level pragma behaviour with no existing precedent and a transiently invalid state | Binds N1/N2/N3/N4 |
| **D-RB3-08** | DR-006: **(i)** persist normally when its stored-evidence conditions are met (recommended), or **(ii)** retain a conservative prohibition denying the **entire** invocation with reason `dr006_persistence_not_authorized`? Reachability on a PROCEED run is **UNPROVEN in both directions** (§7.4, **C-RB3-08**) | `DEMO_REVIEW_RULES.md:125`, `:135`, `:161`; `p4_rb2_offline_rules.py:423-451`; `p5_run_gate.py:608`, `:617-628`; `p5_evidence_bridge.py:183-233`; `documents/issues.py:217-258` | (i) persist; (ii) prohibit whole-invocation | **(i)**, conditional on the C-RB3-08 proof obligation being discharged in the implementation review | (i) preserves a genuine stored-evidence signal, at the cost of persisting a rule whose independence label is a transport label; (ii) is maximally conservative but **reduces** persisted output and must be recorded as a deliberate reduction — and must never silently drop the item while persisting others | Binds N1, N13 (only under (ii)), RB3-66 |
| **D-RB3-09** | Approve the additive immutable `review_evaluation` completion table with the §6.3 schema, including `lineage_label_policy` in place of Revision 2's global `lineage_state`? (**C-RB3-03**) | DD §§2.9–2.10, 2.17, 5.1; `audit.py:65-74`, `:124-128` | (a) dedicated table; (b) audit-only; (c) rows-only inference | **(a)** | (a) proves the original evaluation fingerprint including the zero-item case, atomically; cost: a third table, an append-only dictionary note, one more entry in the E1/E3/E4 table sets. (b) unsound; (c) cannot represent a zero-item evaluation | Binds N3/N4/N6/N7 and the E1/E3/E4 deltas |
| **D-RB3-10** | Per-item provenance honesty (**RB3-R3-08**): **Option A** — additive `review_item.provenance_status` storing the evaluator's literal verbatim, included in `output_identity_sha256`, with an append-only dictionary note; or **Option B** — explicitly documented non-persistence plus a truthful per-item RB3 stored-lineage representation and a consumer contract preventing a persisted item from appearing to be a real doctor attestation? | `schemas/p4_rb2_offline_rules.py` (`OfflineRuleFlag.provenance_status`); DD §2.9; `TOOL_CONTRACTS.md:270`; `DEMO_REVIEW_RULES.md:135` | A / B | **A** | A: the provenance qualifier travels with the row, is structurally CHECK-pinned and is part of the durable output identity, so no consumer can see a DR-006 item without it; cost: one additive column beyond §2.9 needing an append-only note. B: keeps §2.9 byte-identical; cost: the honesty guarantee lives only in out-of-band documentation and consumer discipline, which is weaker for a persisted clinical-adjacent artifact. Under **both**, `review_evaluation.lineage_label_policy` states only which boundary option governed the labels — it must never imply that every observation in a mixed input has independently verified document lineage | Binds N3/N4/N7 and RB3-79 |

### 12.1 Proposed exact owner ratification marker

If — and only if — the owner accepts D-RB3-01..D-RB3-10 (including sub-decisions 05a–05f) and the conflict resolutions C-RB3-01..C-RB3-05, C-RB3-07, C-RB3-08, plus the N1–N13 / E1–E6 allowlist split exactly as written, the proposed marker is:

```
RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE
```

Bounded semantics: it would authorize **one** future separate RB3 implementation PR confined to the N1–N13 paths, issued only after (a) this documentation-only PR is owner-reviewed and owner-merged and (b) exact merged-main CI SUCCESS is independently verified on the merge SHA. Each of E1–E6 would still require its **own** fresh standalone marker before any edit, and E5's marker must state the actual future measured backend/P3 collection pairing.

It would **not** authorize: full P4 acceptance or a P4 PASS; RB4 run-backed GOLD A/B/C/D acceptance; runtime policy activation beyond the bounded demo persistence service; graph, LLM, API, UI, task, notification, approval-decision, summary or state-transition-writer activity; any change to accepted F0/F1/F2/RB1/RB2 behaviour beyond the docstring-only E6; closure of issue #14; clinical use of any kind; or any merge, readiness change or self-approval by an agent (`AGENTS.md` §2).

---

## 13. Unresolved design conflicts (explicitly identified, not guessed)

| ID | Conflict | Why unresolved | Recommendation | Resolution path |
|---|---|---|---|---|
| **C-RB3-01** | An unchanged RB2 has **no honest** `lineage_status` for stored-proved rows: `fixture_asserted` labels *fictional* lineage per `TOOL_CONTRACTS.md:270`; `unavailable` makes RB2 emit **false** `verified_lineage_unavailable` exclusions (`:316-321`); `stored_independently_verified` is rejected (`:221-225`, test `:275`) | Only the owner can accept a documented transport label or authorize re-derivation | **A2 with `fixture_asserted` as an explicitly documented transport label**, per-item `provenance_status` persisted verbatim (D-RB3-10 Option A), `lineage_label_policy` recorded, DR-006 never presented as a doctor attestation, append-only contract note | Owner ratification of D-RB3-03 + D-RB3-10; **stays unratified until then** |
| **C-RB3-02** | Whether to persist DR-006 at all, given its activation depends on the contested label | A safety/scope judgement, not an engineering one | **Persist** (D-RB3-08 (i)) with six span-resolved links and no trust promotion; otherwise deny the whole invocation | Owner decision D-RB3-08 |
| **C-RB3-03** | Invocation-level replay needs a durable completion identity; DD §§2.9–2.10 define only two tables and the audit table cannot serve | A third table extends the dictionary's P4 persistence scope | **Add `review_evaluation`** with an append-only §2.10a note | Owner decision D-RB3-09 |
| **C-RB3-04** | SQLite NULL-distinct UNIQUE semantics; the compact COALESCE expression index has no in-repo precedent and unproven ORM reflection parity | Both mechanisms viable; the choice trades compactness against parity certainty | **Partial unique indexes + G11**; after the span correction the partial indexes alone suffice for every RB3-writable kind, and G11 is defence-in-depth | Owner decision D-RB3-05d + a parity test in the implementation PR |
| **C-RB3-05** | Preserving the evaluator's stable ordering durably needs `display_order`, absent from DD §2.9 | Additive column vs read-time re-derivation | **Additive `display_order`** + `ux_review_order` with an append-only note | Owner decision D-RB3-05b |
| **C-RB3-06** | *(closed in Revision 3)* The exact `reason_code` literals and per-flag evidence bound | — | **Resolved by transcription:** the six literals are `missing_baseline`, `measurement_stale`, `change_exceeds_demo_parameter`, `verified_source_conflict`, `duplicate_or_out_of_order`, `implausible_value`; the per-flag maximum is **6** references (DR-006), giving `item_count ≤ 12` and `evidence_link_count ≤ 72` | Encoded in §6.1/§6.3/§7.2 and tested by RB3-78/RB3-80 |
| **C-RB3-07** | Per-item `provenance_status` is absent from DD §2.9, and §2.10 has no `fact_id` column for `fact:` references | Both are additive contract deviations | **Add `provenance_status`** (D-RB3-10 Option A); **do not** add `fact_id` in this slice — represent `fact:` by its verified value-fact span and preserve the fact identity in the input/output identities | Owner decisions D-RB3-10 and D-RB3-05f |
| **C-RB3-08** | Whether a genuine F1-PROCEED run can reach DR-006 through the accepted F1/F2 contracts is **UNPROVEN in both directions**: the mechanism divergence is verified at line level, but constructibility also depends on extraction-time issue generation and F1's selected-document preflight, which this design has not fully traced | Proving it requires either building a real fixture run or tracing the full VI-001…VI-005 issue-generation logic — implementation work, not design work, and inventing a fixture is prohibited | Discharge it in the implementation PR: either construct a genuine PROCEED run reaching DR-006 and test the ratified behaviour end-to-end, or prove none exists from the accepted logic and record DR-006 as provably inert with that proof in the implementation review (N10) | Owner decision D-RB3-08 plus the RB3-66/RB3-74 obligations |

---

## 14. This PR's scope, procedure and rollback

- **Files (exactly three):** this design document (corrected in place — it is new and unratified), an append-only `docs/phase-reports/PHASE_4_REPORT.md` checkpoint, and an append-only `docs/roadmap/PHASE_PROGRESS.md` checkpoint. Both appends are verified to remove zero lines. If a fourth path were required, this task would stop and explain; none is.
- **Not modified:** contracts, application source, tests, fixtures, models, migrations, dependencies, policy YAML, GOLD fixtures, CI configuration, scanner. No P5 source file is modified; E6 is identified and justified only. Where a contract amendment might be wanted (§2.10 `fact_id`), it is proposed as an owner decision, not made.
- **Procedure:** one DRAFT PR (#42) targeting `main` from the session branch based on the exact verified main `7190b25e…`. The agent never merges, never marks the PR ready for review, never self-approves and posts no ratification marker (`AGENTS.md` §2). Corrections are committed normally to the same branch; history is not rewritten and no second PR is created.
- **Checks actually executed for Revision 3:** the git/`gh` state verifications (branch, HEAD `3d749648…`, base, clean tree, PR draft/state/head); line-level read-inspection of every path cited in §1.2, including the complete F2 `source_reason`, the F2 always-rollback `finally` block, `compare_explicit_current_with_history`'s `1 <= len(current) <= 6` bound, all six `_flag` call sites with their reason codes and evidence tuples, `EXTRACTION_PROVENANCE.md` §5, `span_is_resolvable`, the `ExtractedFact` span CHECKs, the `AuditEvent` model and `append_audit_event`'s add-and-flush return; the append-only removed-line proofs; and `python scripts/python/scan_repository.py` on the staged tree. Exact-head CI results are reported in §0 and the PR conversation. **Not executed:** any `pytest`, `ruff`, `alembic` or frontend command in this session; no RB3 code, migration, model, contract or fixture exists; no case in §11 has been run; no Windows or real-OCR gate; no coverage or pass-count claim.
- **Rollback:** close PR #42 unmerged. Zero database, source, fixture or policy impact.

**Standing status:** P4 **IN_REVIEW** · issue #14 **OPEN** · full P5 **NOT ACCEPTED** · original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN** · no RB4, graph, LLM, API, UI, task, notification, summary, approval-decision writer or clinical capability is authorized or claimed · **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**
