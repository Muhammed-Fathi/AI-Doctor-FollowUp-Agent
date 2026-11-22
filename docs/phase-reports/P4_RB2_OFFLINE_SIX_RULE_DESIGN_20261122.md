# P4-RB2 — complete six-rule offline synthetic evaluation design (owner decision requested)

**State: PROPOSAL / DOCS ONLY / NOT RATIFIED / NO RB2 CODE AUTHORIZED.** Date: 2026-11-22. P4 [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN** and P4 remains **IN_REVIEW**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

**Independently verified base:** Owner merged [P4-RB1 PR #37](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/37) at `main@fb859ba254c24f63e4cad0036277044549cc3f27` (2026-11-22T08:37:08Z). Its reviewed code HEAD `0563f53ae59caebe45c5a49c5cb0850c30925030` received owner Windows `setup.ps1` PASS and `test_all.ps1` **12 PASS, 0 FAIL, 1 optional Playwright SKIP**, plus [push CI #45001120724](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45001120724) and [PR CI #45001124861](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45001124861) SUCCESS. The **actual newly merged-main** [CI #45003663828](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45003663828) independently completed **SUCCESS** on this exact merge SHA, both Backend Python 3.12 and Frontend Node 22. None of this is RB2 test execution or P4 phase acceptance.

## 1. What exists and what RB2 is allowed to prove

- P5-F0 real stored `workflow_run` plus immutable selected source manifest, P5-F1 scoped persisted VI gate, P5-F2 read-only V2 checked evidence, P4-RB1 read-only `RunBoundReviewInputPreviewV1` are now in `main`. **RB1 output is explicitly non-executable**: `runtime_evaluable=False`, `rules_executed=False`, `policy_status=unapproved`, `review_items_persisted=False`. Its 90-day current comparison inputs are distinct from F2's 365-day history.
- `backend/app/services/demo_rules_candidate.py` already implements **only** offline synthetic DR-001/003/005/009 and accepts a **caller-supplied test-only** `blocking_fact_count`. `backend/app/services/provenance_review_candidate.py` separately implements offline DR-006/008 on **fixture-asserted** provenance; its `source_fact_verification_status` is NOT proof that the server independently verified a doctor source. Do NOT expose either old candidate as an authorized live runtime rule tool.
- The owner-pinned R3-A synthetic **offline reference** `demo-policy-1.1.0` has 90-day baseline, 30-day stale limit, arbitrary demo deltas 10/8/15/40, zero source-conflict tolerance, max three items per measure type, injected `2026-11-14T12:00:00Z` clock, all six `VI-001..006` and exactly six `DR-001/003/005/006/008/009`. Canonical LF reference SHA `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36` is an **offline test seal, not a runtime policy toggle**. Existing `backend/tests/p4/test_p4_demo_policy_reference.py::test_reference_artifact_is_not_imported_by_app_runtime` forbids app code from referring to the test-only YAML file; leave it intact.
- CH-01 and D-RB-01..04 deliberately separate offline deterministic evaluation (**RB2**) from durable run-scoped `review_item`/`evidence_link` table writes (**RB3**), and actual run-backed GOLD replay/independent P4 phase acceptance (**RB4**). The original real P3 OCR `GOLD-EX-11: 1O5→105` is **FAIL / NOT PROVEN** and remains so.

## 2. Exactly four RB2 design decisions needing explicit owner ratification

### D-RB2-01 — isolated pure six-rule OFFLINE evaluator only (recommended)

Create a **new** pure synthetic-only deterministic evaluator with a frozen result object. It is **NOT** `evaluate_demo_review_rules` callable from any agent/API, and it does not consume a stored `workflow_run`, query SQLite, accept session credentials, mutate data or invoke a graph/LLM. Tests drive synthetic typed snapshots; historical older candidate modules remain unmodified/unused as trusted runtime gates.

Every result contains only neutral candidate DR items with closed rule ID, reason code, workflow hint, explicit evidence keys, trust basis, deterministic dedupe key, fixed policy identity and `demo_only=True`. The result **must also explicitly be non-authoritative**: `runtime_evaluable=False`, `rules_executed=False` in the *run/runtime sense*, `review_items_persisted=False`, `policy_status=unapproved`; describe any internal result as `offline_candidate_rules_evaluated=True` or equivalent to avoid falsely asserting that no pure test function ran. No row or `ReviewFlag` is persisted.

**Important distinction:** A successful RB1 typed preview may be **used as one test-data source**, but is **not an executable authorization**, cannot be a signed permit, cannot be accepted merely because it is a frozen DTO, and cannot supply DR-006/008 provenance that it does not contain. RB2 tests are pure offline assertions only; any future run-bound RB3 consumer must independently recheck F0/F1/F2/RB1, selected document bytes, doctor assignment, clock and policy in its own write-controlled boundary. Existing RB1 source must not be edited.

### D-RB2-02 — refuse counterfeit or incomplete six-rule evidence (recommended)

The pure evaluator accepts typed synthetic evidence only: an explicitly declared same-patient scoped set of current readings (at most six), bounded admissible/explicitly-excluded history (at most 100), measured and recorded timestamps, underlying verified-fact/source-lineage references (only if supplied by the independently checked *offline test fixture*), and a candidate policy that structurally and **exactly** matches the owner-sealed R3-A reference values. Do NOT load the offline YAML file in application source (only test code may read/verify the seal). Include a typed provenance-status field distinguishing **fixture_asserted** from **stored_independently_verified**; RB2 may show fixture-labelled outputs but MUST NOT label an asserted-only DR-006 as persisted-doctor verified. When independent source lineage is absent, suppress DR-006 and emit a typed `verified_lineage_unavailable` exclusion; never upgrade `self_reported_validated`. The strict evidence boundary must forbid caller-provided `blocking_fact_count=0`, `run_gate_completed=True`, pretend `policy_status=approved`, cross-patient IDs, unknown units/measure IDs, forged trust/source or unsupported timestamps; invalid input returns a typed fail-closed error **with no partial DR items**.

**Safest first RB2 implementation choice:** full six-rule evaluation over explicit **synthetic offline fixture provenance**; do NOT try to claim it is the authenticated production stored F1 decision. When future true provenance is needed, RB3 requires fresh DB- and selected-source-based verification and a separate owner approval.

### D-RB2-03 — pin six-rule triggers, deterministic scope and neutral wording (recommended)

Follow the normative `docs/clinical-safety/DEMO_REVIEW_RULES.md` §§5–10, not an invented medical heuristic:

| Rule | Offline trigger and mandatory restriction |
|---|---|
| DR-001 | No same-measure/unit admissible earlier baseline within the pinned **90 days**, using the newest prior candidate; one per declared evaluated measure type, not per arbitrary unselected history row |
| DR-003 | Newest admissible measurement of a declared evaluated measure type older than 30 **whole days** relative to injected fixture clock; no output when the evaluated type was not explicitly selected |
| DR-005 | Strict `abs(current − latest prior) >` synthetic demo delta for that type, not `>=`; no direction-based or clinical wording; evidence current and exact prior, and preserve self-report/mixed suffix |
| DR-006 | Two **distinct**, doctor-verified **independently supported** document sources of same type/unit and **equal normalized measurement timestamp**, differing by more than zero; same fact/doc replay is NOT two sources; fixture-only assertions are not real doctor verification |
| DR-008 | Same type/value/timestamp duplicate, OR later-created entry measured earlier than an existing admissible entry, using stable created/measured timestamps; missing `created_at` yields typed exclusion rather than made-up ordering |
| DR-009 | Admissible numeric value outside the **existing** engineering typo/plausibility band from the closed measure-type dictionary; not clinical normality, no new bands |

Apply `max_items_per_type=3` deterministically and **fail closed** rather than silently truncate if over cap, fixed sort order `verification_needed → data_quality → change_to_review`, then `rule_id` and stable evidence keys. Dedup by `sha256(patient_id | rule_id | sorted typed evidence keys | trust_basis)`, never a newly created row ID. Reject retired DR-002/004/007/010 and unknown/disabled VI. Use the exact neutral text templates and trust suffixes from the safety contract; block words suggesting normal/abnormal, danger, risk, urgency, diagnosis, treatment, medication or medical advice.

**Scope nuance requiring tests:** an F0/RB1 run can select **zero** current observations; this yields **zero RB2 candidates**, not DR-001 or DR-003 from unselected historical records. A same-patient GOLD-D offline dataset may evaluate a declared HR record for DR-001/003 even when it is old; do not infer selection from all historical rows. RB2 must represent the *explicit selected/evaluated set* and test this difference. If the existing GOLD input selection cannot be represented without changing a frozen GOLD fixture, STOP and submit a documented design conflict; do not rewrite GOLD expected JSON.

### D-RB2-04 — strict fixture/seal/edge-case coverage, separate persistence and runtime (recommended)

Prove **all six rules** under synthetic pure tests, not by dispatching two partial candidate engines with forged `blocking_fact_count=0`. Tests must separately cover message labels/order/evidence/dedupe/replay; exact 90-vs-365 baseline; threshold equality vs strict greater-than; latest prior tie-breaking; explicit no-current selected; newest stale type; two *different independently supported* verified sources vs one replayed source; DR-008 repeat vs created/measured disorder; DR-009 value just inside/outside closed demo band; mixed/self_reported trust; invalid/partial policy, version, YAML SHA; blocked facts; foreign patient and falsely verified source; over-cap failure with no partial outputs; zero writes and immutable existing P3/F1 provenance; future timestamp/rejected/wrong unit exclusions. Use the published GOLD-A/B/C/D **offline** expectation pack, but distinguish pure fixture replay from any *later* genuine run-bound end-to-end RB4.

Do not change legacy candidate engines, pinned R3-A policy YAML, original GOLD expected JSON, old P3 gate/test, scanner, CI, or P5-F1/F2/RB1 sources. Adding RB2 tests may alter strict P3 handoff **collection count**. The previous [PR #37 specific extra-path exception](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/37#issuecomment-7076184528) is **not reusable**. If a separate RB2 implementation CI fails the handoff pairing, obtain **fresh authenticated owner PR-thread permission** for exactly `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`, append-only current measured `N collected / 443 P3` and never call collected tests passed.

## 3. Proposed FIRST FUTURE RB2 code PR allowlist (not yet authorized)

If the owner ratifies this design, then **after owner merge of THIS docs-only PR and exact merged-main CI SUCCESS**, one separately reviewed P4-RB2 *offline-only* code PR may change only these eight files:

1. `backend/app/services/p4_rb2_offline_rules.py` — **new** pure evaluator over typed synthetic evidence, no DB/file/network/run runtime access.
2. `backend/app/schemas/p4_rb2_offline_rules.py` — **new** sealed, non-authoritative candidate types/typed errors with explicit fixture lineage.
3. `backend/tests/p4/test_p4_rb2_offline_rules.py` — **new** all-six positive and fail-closed negative rule tests, trust/dedupe/clock/boundary cases.
4. `backend/tests/p4/test_p4_rb2_gold_offline.py` — **new** A/B/C/D test-only synthetic adapter/replay; no real OCR or run-backed storage claims.
5. `docs/contracts/TOOL_CONTRACTS.md` — append-only offline-only RB2 interface with no `evaluate_demo_review_rules` tool activation.
6. `docs/phase-reports/P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md` — new truthful evidence/test/security report.
7. `docs/phase-reports/PHASE_4_REPORT.md` — append-only RB2 checkpoint.
8. `docs/roadmap/PHASE_PROGRESS.md` — append-only owner ratification and implementation evidence.

**No other path, even to fix tests, without a separate explicit owner approval recorded in the RB2 PR before change.** No modifying already merged P5/F1/F2/RB1 or older P4 candidate source, `STATE_AND_GRAPH_CONTRACT.md`, no `backend/app/db/models.py`, migration, API, graph, LLM, task, notification, frontend, scanner, CI, P3 handoff/test or policy reference. Any new dependency or migration need is a STOP/review item, not implicit authorization.

**Future RB3** is independently scoped *strict durable* run-owned review/persistence with fresh authenticated gate and filesystem check; **future RB4** is independently scoped run-backed GOLD/acceptance. No RB3/RB4 code permission is conveyed here.

## 4. Non-negotiable review gates and test matrix

| ID | Pure synthetic acceptance condition | Required outcome |
|---|---|---|
| RB2-01 | All 6 DR identifiers enabled in exact R3-A fixture | Each emits the correct neutral typed candidate in its own test; no retired IDs |
| RB2-02 | Zero selected current vs historical-only | Zero DR candidates; no inferred selected/current data |
| RB2-03 | Day 180 baseline in F2, not RB1's 90-day window | DR-001 eligible only under 90-day semantics, no DR-005 invalid delta |
| RB2-04 | Two baselines within window and equal-timestamp tie | Latest prior and stable ID deterministically; same result on replay |
| RB2-05 | Value delta exactly threshold vs threshold plus epsilon | Strict greater-than emits only the latter |
| RB2-06 | 29/30/31-day stale boundaries, clock injected | Whole UTC-day floor and correct newest selected type only |
| RB2-07 | Real distinct independently verified source vs duplicated fact/doc fixture assertion | DR-006 only with truly independently supported compatible provenance; otherwise excluded |
| RB2-08 | Equal-value/timestamp repeat, created/measured disorder, missing created_at | DR-008 only with admissible proof; typed missing-source exclusion |
| RB2-09 | Existing engineering-band boundary, just beyond it | DR-009 exactly as data-quality hint; never clinical threshold |
| RB2-10 | Self-reported, doctor-verified and mixed observations | Correct trust suffix, no self-report upgrade |
| RB2-11 | Unapproved/missing/modified policy, unknown/retired DR or disabled VI | `E_RULE_POLICY_INVALID`, ZERO emitted candidates |
| RB2-12 | Forged caller blocker/gate/policy approval or old candidate count flag | Interface disallows or rejects; no runtime authority |
| RB2-13 | Cross-patient, invalid source/units/clock, rejected/future rows | Fail closed or typed exclusion per contract, no fabricated evidence |
| RB2-14 | Dedup, max 3 items per type, stable hint/evidence sorting | Stable replay; over-cap fail-closed with no partial results |
| RB2-15 | GOLD-A/B/C/D offline fixture matrix, including C pre/post | Correct *offline-only* expected DR IDs and VI-blocked C; no new run/OCR claim |
| RB2-16 | Exact head Linux full CI + independent owner Windows 5.1 gate | Real PASS/FAIL/SKIP evidence; optional Playwright skip NOT PASS |
| RB2-17 | Attempts to call DB/API/graph/LLM/notification or persist result | No entry point or side effects; read-only by construction |
| RB2-18 | Original P3 OCR truth `1O5`→`105` | `GOLD-EX-11 FAIL / NOT PROVEN` preserved; no clinical claim |

**These are REQUIREMENTS, NOT tests executed by this docs-only design.** Published past RB1 CI and Windows results are prior-entry evidence only. An RB2 code PR still requires Ruff, all pytest, Alembic smoke, OpenAPI, scanner, Node 22 checks, exact-head owner Windows `setup.ps1`+`test_all.ps1`, independent static/security review, then owner-only merge. Cannot claim synthetic tests establish clinical validity.

## 5. Decision procedure, owner-only signoff and rollback

**Exact owner marker for this design PR**, if all four decisions and the first-code eight-path scope are accepted:

`RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE`

**Marker means:** ratify D-RB2-01..04 *as offline design* and authorize **only** a future separate P4-RB2 **pure offline synthetic** evaluator PR with the exact eight paths above, **conditional on** owner merging this design PR and exact merged-main CI SUCCESS. It does **NOT** authorize production or real-run `evaluate_demo_review_rules`, P4 `review_item`/`evidence_link` writes, genuine RB3/RB4, P5 graph/LLM, API/frontend/task/message, doctor approvals, P4 PASS, clinical use, or agent merge.

After owner posts the exact marker **in this PR's Conversation**, independently verify actual author/body/time/link; record the owner decision and boundaries *append-only* in `docs/roadmap/PHASE_PROGRESS.md` on this docs-only branch. Re-run CI on the **final** docs HEAD, then only owner reviews, marks Ready for review and merges; verify **postmerge main CI** before starting future RB2 code branch. If any design decision is disputed, revise this docs PR only, then obtain a fresh exact owner marker. **Do not self-ratify or merge.**

This docs-only PR changes exactly **three** files: this new design, an append-only `docs/phase-reports/PHASE_4_REPORT.md` checkpoint, and an append-only `docs/roadmap/PHASE_PROGRESS.md` checkpoint. No runtime, tests, policies, fixtures, migrations, or P3 OCR changes. Rollback = close Draft design PR unmerged, with zero source/db effects. P4 **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, full P5 NOT ACCEPTED, real `GOLD-EX-11 FAIL / NOT PROVEN` unchanged. **NOT FOR CLINICAL USE.**
