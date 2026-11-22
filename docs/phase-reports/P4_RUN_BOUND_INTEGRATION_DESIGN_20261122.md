# P4 Run-Bound Integration — owner decision and gated implementation design

**State:** DESIGN PROPOSAL / DRAFT / OWNER DECISION PENDING / NO P4-RB CODE AUTHORIZED BY THIS DOCUMENT.  
**Date:** 2026-11-22. **Tracking:** [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains OPEN; P4 **IN_REVIEW**; overall P5 NOT ACCEPTED.  
**Exact verified starting point:** Owner-merged [P5-F2 PR #35](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/35), `main@deb6b15f19e4a1c0571c513d158c2b9e7128eb61`. [Exact merged-main CI #44994402273](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44994402273) **COMPLETED SUCCESS** for Backend Python 3.12 and Frontend Node 22. Owner's last independent **premerge** Windows gate at F2 code head `6d015bc0c2749dec7ce62de609f801ade5da4fe3`: 12 PASS / 0 FAIL / 1 optional Playwright SKIP. This is F2 evidence, **not** P4 integration evidence.

**Academic synthetic/local only; NOT FOR CLINICAL USE.** The original P3 real-document `GOLD-EX-11` failure (source glyph `1O5` was read as `105`) remains **FAIL / NOT PROVEN**. Document SHA, a recorded doctor action, or scripted synthetic correction does not prove physical OCR glyph fidelity.

## 1. Why return to P4 now; evidence actually implemented

Owner-ratified [CH-01 P4→P5 handoff](P4_P5_CONDITIONAL_HANDOFF_20261121.md) deliberately sequenced genuine P5 run identity and run-scoped evidence before P4 `review_item.workflow_run_id NOT NULL FK` persistence. That missing parent **now exists**, but CH-01 explicitly requires another independent P4 authorization, not automatic policy activation.

| Existing implementation | Verified useful capability | Still missing / prohibited assumption |
|---|---|---|
| P5-F0, `workflow_run` / selected document, observation and omission tables | Real server-generated run, persisted doctor-selected source manifest, run clock/version, audited omission | No graph run/doctor sign-off on clinical outcomes; no DR review persistence |
| P5-F1 `run_gate_evaluation` / `run_gate_blocker` | Persisted replay-checked VI-001..006 PROCEED/HALT/UNAVAILABLE, selected bytes + source fingerprint; preserves historical original OPEN VI-002 | Never treat a cached PROCEED as permanently fresh; never auto-clear old P3 issue |
| P5-F2 `build_run_evaluable_review_evidence` / frozen V2 | Fresh read-only F1 recheck and typed labelled facts/current observations/comparisons; no caller-provided gate/count flags | Always `runtime_evaluable=False`, `rules_executed=False`, `policy_status=unapproved`; a V2 object is NOT a write/graph/DR token; filesystem and SQLite are not atomic |
| P4 pure `monitoring`, `p4_explicit_history`, `p4_readonly_provenance` | Deterministic patient-scoped comparison, trust-labelled observations, typed exclusions | No run-backed DR orchestration or review rows |
| P4 `demo_rules_candidate` and `provenance_review_candidate` | Offline synthetic DR-001/003/005/009 candidate subset and distinct DR-006/008 provenance candidates | **No unified, full six-rule, approved runtime evaluator**, no production integration; the candidate subset still accepts a test-only caller blocking count |
| Owner-approved R3-A `data/synthetic/policy/demo_review_policy.yaml` | Canonical LF SHA-256 `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`; exact offline fixture reference, `demo-policy-1.1.0` | **Reference values only**: neither that hash nor `validate_demo_policy` is a runtime activation or a free choice of disabled VI switches |
| GOLD-A/B/C/D component tests | Source-controlled expected offline synthetic outputs and pure-service tests | Not a real F0→F1→F2→P4 run-backed end-to-end replay, real OCR test or clinical validation |

**Previously decided and preserved:** R1-A (no fake run parent or weakened FK), R2-A/C-35A/C-37A (bounded source/explicit history), R3-A (synthetic *reference* policy), R4 (offline GOLD), R21-S1 (audited doctor choice of separately verified recovery). No design decisions here may retroactively broaden those approvals.

## 2. Four separately reviewable P4-RB design decisions

### D-RB-01 — strictly separate the first read-only integration slice from any execution (recommended)

**Recommended:** First code PR is **P4-RB1**, an internal *read-only* run-bound **review-input preview**. It accepts one persisted run ID and authenticated server Principal, reconstructs F2's exact current F1 source/identity gates without using user-provided `PROCEED`, and derives typed synthetic policy-window comparison inputs (see D-RB-02). It **returns no `ReviewFlag`/DR result**, writes no `review_item`/`evidence_link`, adds no schema/migration, changes no run status, and creates no graph/API/LLM/task/UI/notification. The preview is an intermediate input-checker only: `runtime_evaluable=False`, `rules_executed=False`, `policy_status=unapproved` even on success.

Later **P4-RB2** may implement a separately approved full six-rule *pure offline* deterministic evaluator on those verified inputs; **P4-RB3** may implement separately approved schema and durable run-bound persistence with one fresh lock-and-revalidation boundary; **P4-RB4** may add end-to-end GOLD acceptance and owner phase review. Each later PR requires its own explicit owner decision, exact file allowlist, CI and owner Windows evidence. No combined multi-phase/graph coding.

**Alternative requiring a revised design before ratification:** build P4 migrations and rule persistence immediately in the first code PR. This is NOT the recommended option because it would activate too many security, policy, and transaction assumptions before a witnessed read-only run-to-policy evidence adapter exists.

### D-RB-02 — reconcile two different lookback periods without falsifying either (recommended)

F2's V2 projection deliberately uses the versioned `f2-history-365d-v1` **365-day** maximum historical search; the R3-A synthetic reference `demo-policy-1.1.0` has `baseline_lookback_days=90`. A valid baseline at day 180 in V2 is **not** a valid DR-001/DR-005 baseline for the 90-day demo policy. **Never reuse V2 `delta`/baseline as a 90-day rule comparison without rechecking the full same-patient prior time and admissibility.**

**Recommended P4-RB1 policy projection:** obtain only server-scoped current observation IDs from the immutable F0 manifest; derive same-patient bounded historical rows through trusted DB provenance under an explicit injected run clock, compute *fresh policy-window* 90-day comparable inputs using existing pure comparison functions, with stable closest-prior tie-break, no unit conversion/imputation and no cross-patient source. The 90-day policy comes only from a trusted exact-revision/hash-pinned R3-A **offline** reference (canonical CRLF→LF handling only as previously reviewed), not a caller-supplied lookback/policy, and all VI-001..006 remain enabled in that reference. A version mismatch, tampered artifact, over-100 historical rows, >6 selected current observations, unverified document source, or stale F1 fingerprint fails closed. If F0 selected 0 current records, output empty comparison inputs with `no_current_selected`; do not invent observations or generate DR-001/DR-003 by assuming an unselected current record. `self_reported_validated` must remain labelled.

**Snapshot caveat:** today's F2 builder owns a separate SQLite `BEGIN IMMEDIATE` transaction and rolls it back; P4-RB1 may safely produce a **non-authoritative read-only preview** with a second scoped read plus fresh recheck, but **must not** claim those two sessions constitute one atomic authorization. A future P4-RB3 write service must re-evaluate source identity/fingerprint/doctor session, raw upload bytes and policy within its **own** controlled transaction immediately before persistence; it cannot consume a cached V2/preview/DR set as an execution token. If making this atomic requires changing any P5-F2 or F1 source path, STOP and request a fresh **exact-path** owner exception in the future implementation PR. SQLite does not transact with upload files, so later consumers also recheck freshness.

### D-RB-03 — preserve separation between six-rule policy approval and executing review items (recommended)

The R3-A values `demo_delta_systolic_mmHg=10`, diastolic 8, heart rate 15, glucose 40, stale 30 days, 90-day baseline and other switches are **synthetic fixture constants**, NOT clinical thresholds or runtime approval. The complete valid catalogue is exactly `DR-001,003,005,006,008,009`, all six `VI-001..006` enabled, retired `DR-002,004,007,010` forbidden.

Do not wire the partial candidate evaluator's caller-controlled `blocking_fact_count` into run execution, and do not mistake the DR-006/008 **fixture-only lineage assertions** for persisted doctor-verified evidence. For any later pure rule engine, require verified fact/source decisions, actual provenance, exact trusted policy, owner-controlled version, `as_of_utc`, deterministic neutral templates/trust suffixes, `E_RULE_POLICY_INVALID` on unapproved policy and **no outputs** on invalid/blocked input. The six-rule engine must not assert "normal", abnormal, diagnosis, urgency, treatment, prescriptions or personal medical guidance.

This design/PR marker **does not authorize either pure DR evaluation or durable DR activation**. A later P4-RB2 code-scope ratification may authorize **offline synthetic** evaluation only. Even after that, a **distinct P4-RB3 owner decision** is required to create durable run-bound review items. There is no graph/LLM/doctor messaging authority here.

### D-RB-04 — keep run-linked review persistence strict and separately gated (recommended)

When P4-RB3 is independently authorized, implement additive and reversible schema for `review_item` and `evidence_link` from [DATA_DICTIONARY.md §§2.9–2.10](../contracts/DATA_DICTIONARY.md), *not* placeholders:

- `review_item.workflow_run_id` **NOT NULL FK** to genuine `workflow_run.id` ON DELETE RESTRICT, plus patient FK, closed six-rule ID and trust enums, `demo_only=1`, bounded neutral message, state `open/decided/superseded`, and UNIQUE `(workflow_run_id, dedupe_key)`; derive dedupe solely from `sha256(patient_id | rule_id | sorted evidence keys | trust_basis)`, never from a new row ID. Match `policy_version` to the persisted immutable run.
- `evidence_link`: enforce exactly one typed `document_span` or `observation` reference with patient/run/owner integrity; polymorphic `owner_id` is **not** an FK, so the write service must check that `owner_type='review_item'` resolves to its real run-owned review item before insert. Do not fabricate unsupported generic links. `checkin_note` payload semantics in §2.10 need an explicit documented resolution before implementation; do not invent a free-text link.
- Persist flags and evidence **atomically under one authenticated assigned-doctor/run-and-policy-checked transaction**, with repeatable replay and zero partial writes/duplicates on denial or retry. No caller-supplied `review_item_id`, `run_gate_completed`, fact count, policy override, arbitrary text, or stale V2 receipt.
- Protect prior F1 immutability and P3 `verification_issue` history. A historic original terminal OPEN VI-002 is preserved when a separate selected recovery is properly accepted; never silently resolve the original.
- New Alembic head after current `0007_p5_run_gate` will change global historical `head` assertions and smoke counts. **Pre-plan a later exact owner path exception** for any legacy P2/P3 test or `scripts/python/check_alembic_smoke.py` compatibility edit. Do not weaken historical migration checks, invent PASS, skip tests or pre-approve exceptions with this document. Downgrade/upgrade and nonempty-data downgrade safeguards need independent tests.
- No LLM, graph, workflow status transition, approval_decision, summary, follow_up_task, notification, UI/API or clinical action in P4-RB3.

## 3. First future code PR allowlist — P4-RB1 only (owner must ratify)

**Scope is PROPOSED, not yet authorized:** after owner posts the exact marker below *in this design PR*, reviews/merges this **docs-only PR**, and verifies **SUCCESS on the exact merged-main SHA**, one separate P4-RB1 **read-only adapter** PR may touch **only**:

1. `backend/app/services/p4_run_bound_preview.py` (new; source/gate identity recheck + 90-day derived *comparison inputs only*, no DR flags).
2. `backend/app/schemas/p4_run_bound_preview.py` (new; frozen non-executable typed preview/skip reasons).
3. `backend/tests/p4/test_p4_run_bound_preview.py` (new; synthetic positive/negative input/provenance/clock/90-vs-365 boundary/no-write).
4. `docs/contracts/TOOL_CONTRACTS.md` (append-only versioned mapping that distinguishes F2 V2 365 from P4 90 policy inputs and preserves §3.4).
5. `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (append-only non-authoritative preview and no-graph scope).
6. `docs/phase-reports/P4_RB1_READONLY_ADAPTER_REVIEW_20261122.md` (new; truthful test and security report).
7. `docs/phase-reports/PHASE_4_REPORT.md` (append-only scope/evidence checkpoint).
8. `docs/roadmap/PHASE_PROGRESS.md` (append-only scoped owner approval and execution checkpoint).

**Nothing else:** no `backend/app/services/p5_*.py`, existing P4 rule candidate/monitoring modules, models, migration, legacy tests, P3 OCR, test fixtures, policy YAML, APIs, graph/LLM/UI/task code, scanner or CI. A new dependency or exact path need triggers STOP and explicit separately recorded PR-thread owner exception **before modification**. Never silently change a global test-count handoff if F2/RB1 tests increase the collected count; obtain a *new* exact one-file documentation exception if strict legacy tests require it.

Future P4-RB2 (six-rule offline engine), P4-RB3 (durable run-owned tables/service) and P4-RB4 (end-to-end A/B/C/D verification and independent owner P4 acceptance decision) **have NO code authorization from this PR**. Each needs its own exact-design/PR-thread scope and tests.

## 4. Synthetic acceptance gates for subsequent phase PRs (NOT executed by this document)

| Test ID | Synthetic input / adversarial condition | Mandatory outcome |
|---|---|---|
| RB-01 | Existing F0 persisted run, fresh F1 PROCEED and valid F2 V2 under assigned active doctor | Scoped read-only typed preview only; runtime_evaluable=false |
| RB-02 | Missing/stale F1, HALT/UNAVAILABLE, forged blocker, revoked session, reassigned patient | No preview; fail closed |
| RB-03 | Change source bytes, raw OCR fact, verification decision, run versions or selection | Deny; never reuse cached PROCEED |
| RB-04 | F2 valid 180-day baseline but no baseline in policy's 90-day lookback | 90-day noncomparable/no_baseline, not reused 365-day delta |
| RB-05 | Two eligible policy-window baselines, later timestamp and same-time ID tie | Deterministically select latest prior and stable ID tie-break |
| RB-06 | Zero run-selected current observations | Empty comparison inputs, typed no_current_selected, no fabricated review |
| RB-07 | Seven through twenty F0-selected current observations | Deny, do not truncate to six |
| RB-08 | 101 same-patient history entries, cross-patient source, future/rejected/invalid time/unit | Bound or typed exclusion per contract; no hidden baseline |
| RB-09 | Unmapped document fact `g/dL`, multiple measurement tuples or unproven corrected lineage | No observation coercion; unverified selection denied |
| RB-10 | Self-reported and doctor-verified mixed series | Preserve trust_basis self_reported/mixed, no promotion |
| RB-11 | Forged caller policy/horizon/gate flag, disabled VI switch, modified YAML or version | Deny; never use fallback defaults |
| RB-12 | Repeated read-only preview, no current, invalid request, concurrent source alteration | Deterministic/no-write; stale state cannot authorize follow-up |
| RB-13 | Full six DR rules in a *later separately ratified* pure offline engine | Closed IDs/templates and versioning; no retired ID, real doctor/synthetic-only |
| RB-14 | GOLD-A run-backed A setup | Expected 0 *demo review* items, not a statement of clinical normality |
| RB-15 | GOLD-B run-backed doctor-scoped source selections | One DR-005 (systolic 12 mmHg, self_reported) only if fresh/full rule gate permits |
| RB-16 | GOLD-C pre-correction/source mismatch | Existing VI-001/002/003/005 HALT; **zero DR items** |
| RB-17 | GOLD-C scripted corrected synthetic lineage | Recomputed eligible source; glucose delta 9 under 40; no DR item; original real OCR failure unaffected |
| RB-18 | GOLD-D run-backed demo fixture | DR-001/003/005/008/009 expected; DR-006 absent without two real verified sources; reconcile F0 mandatory selected doc and selected-current cap explicitly, never modify pinned GOLD expected JSON to force a pass |
| RB-19 | Reviewer hits same run twice / concurrent duplicate event / retry after error | Atomic no-duplicate `(run_id,dedupe_key)`, zero orphan evidence or partial audit |
| RB-20 | Foreign run/document/observation/evidence refs, forged owner ID or trust label | No writes; denied/typed scope error |
| RB-21 | Attempt to use current V2 object as signed execution clearance or call graph/LLM/task | No executable authority; no downstream work |
| RB-22 | Reversible later migration from strict `0007` baseline with existing protected data | Upgrade→downgrade→upgrade, FK/unique/check/immutability conditions, no weakened historic migration state |
| RB-23 | Current real P3 OCR glyph discrepancy `1O5` vs `105` | Original `GOLD-EX-11 FAIL / NOT PROVEN` retained, no false-clean claim |
| RB-24 | Exact final head full Windows PowerShell and Linux CI, frontend checks and scanner | Explicit PASS/FAIL/SKIP evidence; optional Playwright SKIP never counted as PASS |

**No RB tests executed here.** The source inspection and passing F2 postmerge CI above are already-existing evidence for the **starting point only**. Later code PRs need Ruff, full Pytest, Alembic state matrix, OpenAPI, secrets scan, Node frontend, independent owner Windows at exact PR SHA, and review of all failed/skipped tests. Separate model/browser/real OCR execution must not be invented.

## 5. Explicit approval marker, review procedure and rollback

**Exact owner marker to post in this design PR's Conversation if and only if all D-RB-01..04 and the P4-RB1 eight-path first-code allowlist are accepted:**

`RATIFY-P4-RB1-READONLY-INTEGRATION-SCOPE`

**Effect of this marker:** owner agrees to the four design decisions as a roadmap and **authorizes only the first future P4-RB1 read-only comparator/preview code PR** after the design PR is owner-reviewed/merged and exact merged-main CI is SUCCESS. It **does not authorize** P4-RB2 rule invocation, P4-RB3 migration/persistence or P4-RB4 GOLD activation, P5 graph/LLM/UI, P4 phase PASS or an agent merge. Record the marker's exact comment URL, owner identity, timestamp and boundaries append-only to the roadmap in this documentation branch **before merging**. Recheck CI on the final amended docs SHA; owner alone marks Ready for review and merges. Any alternative to D-RB-01..04 requires revising this design and obtaining fresh owner ratification.

**PR scope:** exactly this new Markdown design + append-only `docs/phase-reports/PHASE_4_REPORT.md` + append-only `docs/roadmap/PHASE_PROGRESS.md`. No other file changes. **Rollback:** close this draft PR unmerged, no database, app, fixture or active policy impact. Later code rollback is phase-specific and needs audit-safe migration semantics, never deletion of P3/F1 historical evidence.

**Unchanged invariants:** R1-A/R21-S1, strict F1 F2 freshness, P4 **IN_REVIEW** with [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, P5 overall NOT ACCEPTED, local synthetic educational only, original P3 real `GOLD-EX-11 FAIL / NOT PROVEN`. **NOT FOR CLINICAL USE.**
