# P4-RB3 — durable run-bound review persistence: independent design discovery and specification (owner decision requested)

**Status: DESIGN ONLY — PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED.**
**Revision 2 (2026-11-22): corrected in response to the independent design review findings RB3-D01…RB3-D06. This document supersedes Revision 1 in full; the correction log is §0.1. No implementation exists, and nothing here authorizes any.**

- Tracking: [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) (**OPEN**). P4 remains **IN_REVIEW**. Full P5 remains **NOT ACCEPTED**. Original real-OCR `GOLD-EX-11` (`1O5`→`105`) remains **FAIL / NOT PROVEN**.
- Scope of this PR: three documentation files only (this design, an append-only `PHASE_4_REPORT.md` checkpoint, an append-only `PHASE_PROGRESS.md` checkpoint). No contract, application source, test, fixture, model, migration, dependency, CI or scanner file is modified.
- Base: the exact verified merged main `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`.
- **Branch-name deviation (honest):** the task proposes `docs/p4-rb3-durable-persistence-design`; the Arena session model pins this work to the session branch `arena/91facff6-ai-doctor-followup-agent`, created from that exact verified main and carrying only the three documentation paths. No other branch is used.
- **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

---

## 0. Independently verified merged-P4-RB2 checkpoint (executed in this session)

| Check | Verified result |
|---|---|
| PR #41 state | `MERGED`, `mergedBy = Muhammed-Fathi`, `mergedAt = 2026-11-22T23:20:55Z` |
| Accepted candidate SHA | `headRefOid = 8dd79ac0aa8fc626dcc9b4b7ecf3de3a8aedc888` |
| Merged main SHA | `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`, parents `eaab808b81986077c94eec8f4858c9f746c92ca8` + `8dd79ac0…` |
| Tree equality | merged-main tree `2b083757d04cc202ca64523d25c8e87dcc4cd3fd` == candidate tree; `git diff 8dd79ac0 7190b25e` empty |
| Owner acceptance marker | `OWNER-ACCEPT-P4-RB2`, [PR #41 comment #7087501521](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087501521), `2026-11-22T23:20:34Z`; explicitly **not** runtime rule activation, persistence, RB3/RB4 implementation, or P4/P5 acceptance |
| Permanent evidence report | [comment #7087467476](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087467476), `2026-11-22T23:17:52Z`; self-described "not an approval marker" |
| Post-merge main CI | [run #45082770648](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45082770648), `event=push`, `headBranch=main`, `headSha=7190b25e…`, COMPLETED **SUCCESS**; every Backend Python 3.12 step SUCCESS (Ruff lint, Ruff format, pytest, Alembic upgrade/downgrade/upgrade smoke, OpenAPI check, secret/artefact scan) and every Frontend Node 22 step SUCCESS (ESLint, typecheck, Vitest, production build) |
| Design-PR CI (Revision 1 head `684cf5e0…`) | [#45084736523](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45084736523) (`pull_request`) and [#45084687547](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45084687547) (`push`) both COMPLETED **SUCCESS**, zero non-success steps |

CI is green, so the RB3 design precondition is satisfied. **RB2's acceptance is offline-only**: the accepted evaluator is not a runtime clearance and conveys no RB3 authority.

### 0.1 Revision 2 correction log (independent review findings → actual source evidence → correction)

| Finding | Actual source evidence read in this session | Correction made in Revision 2 |
|---|---|---|
| **RB3-D01** complete locked historical-evidence reconstruction | F2's fingerprint serializes **only projected current** observations (`p5_evidence_bridge.py:378-389`, eight fields, **no `created_at`**); history enters only through `comparisons` (`:390-399`) and `history_exclusions` (`:401`). RB1 subtracts **F2's cached exclusion IDs** (`p4_run_bound_preview.py:152`, `:190-194`). F1's snapshot *does* serialize every column of every patient observation (`p5_run_gate.py:531-562`, ≤100 rows, `:736` digest) | New §5: fresh full stored-history reconstruction under the committing lock; fresh exclusion derivation with cached IDs used **only** as drift cross-checks; a new complete canonical `rb3-full-input-1.0.0` fingerprint; an explicit fingerprint-authority scope table; the fresh locked snapshot declared the **sole** authoritative history source (no separate pre-write pin). Old T5 defect removed |
| **RB3-D02** invocation-level replay identity | `derive_audit_key` includes `request_id` (`audit.py:65-74`), so replays under different request ids append **different** keys; `append_audit_event` returns an existing row **without comparing any other content** (`audit.py:124-128`) | New §6.3 proposes an additive immutable `review_evaluation` completion record (one row per run, UNIQUE) carrying the complete input and output identities plus `audit_event_id`; §8.2 specifies all thirteen replay cases; audit retained as **corroborating**, never authoritative |
| **RB3-D03** DTO/helper compatibility | `RunBoundReviewInputPreviewV1` exposes **no** `gate_version`, `workflow_version`, `state_schema_version` or `mapping_version` (`schemas/p4_run_bound_preview.py:33-57`); `p4_run_bound_preview.py:110` uses `evidence.gate_version` (the **F2** DTO, which does expose it, `p5_evidence_bridge.py:410-414`) | New §2.4 field-to-source mapping; the invalid `preview.gate_version` T3 expression replaced; every proposed call re-verified against actual signatures and `__all__` exports (§1.3); T1 precondition reworded (clean Session **before** `BEGIN IMMEDIATE`, active transaction **after**) |
| **RB3-D04** structural integrity and immutability | House precedents: unconditional immutability triggers `trg_<table>_<op>_immutable` (`0006_p5_run_foundation.py:156-162`, `IMMUTABLE_EVENTS = ("UPDATE","DELETE")` `:31`); conditional cross-table `WHEN (SELECT …) IS NOT …` + `RAISE(ABORT,…)` (`0003_p3_documents.py:267-277`); `length()` CHECK because SQLite does not enforce `TEXT(n)` (`0006…:136`); partial UNIQUE index declared in **both** ORM and migration (`models.py:278-287`, `0002…:289`); ORM/migration parity asserted by name (`tests/p2/test_p2_migration.py:314-331`); downgrade-refusal pattern (`0006…:165-184`) | §6 rewritten: full UPDATE/DELETE immutability for all three tables; an exact numbered inventory of **14 triggers** (replacing the inconsistent "four/five" prose); state/owner/kind **vocabulary reserved but not writable**; cross-table guards implemented as triggers because SQLite CHECK expressions cannot reference other tables; `length()` CHECKs for every bounded TEXT; NULL-distinctness gap closed by a NULL-safe duplicate-identity trigger; downgrade refusal extended to every new object |
| **RB3-D05** audit identity | `ActorType = {user, system, demo_admin}` (`core/enums.py`) — **no** doctor member; doctor is a `Role`. `AuditOutcome = {ok, denied, error}`. `event_type TEXT(48)` has **no** CHECK (`models.py` AuditEvent; `DATA_DICTIONARY.md` §2.17) so an additive event type needs no constraint change. `record_denial` **commits immediately** (`audit.py:170-190`) | §6.3/§8.4: `ActorType.USER` for an authenticated doctor; exact `append_audit_event` argument list; canonical bounded `safe_detail` fragments; explicit re-read and content validation of the audit row via `review_evaluation.audit_event_id`; **no** committed denial-audit mechanism in this slice (`record_denial` prohibited) |
| **RB3-D06** remaining semantics | `created_at` malformed → RB2's ratified **R03** typed exclusion `missing_created_at` (`p4_rb2_offline_rules.py:313-315`, `_clock` returns `None` on `TypeError/ValueError/OverflowError/AttributeError` `:…`), not a hard denial. F1's VI-006 loop runs over **selected documents only** (`p5_run_gate.py:608` `for doc_id in doc_ids`) and `continue`s on non-conforming fact shape (`:622-628`); DR-006 iterates **all** eligible rows of a type (`p4_rb2_offline_rules.py:425`) | §4.5 corrected (R03/R04/R07/R08); §2.2 states `session.user_id == principal.user_id` explicitly; §3.1 states the injected clock defines the evaluation instant with **no** wall-clock expiry detection and that re-hashing reduces but cannot eliminate the check-to-commit race; §7.4 **withdraws** Revision 1's "DR-006 structurally unreachable" claim and replaces it with a proved reachable path plus an explicit owner decision; §8.3 distinguishes durable completion from row persistence |

---

## 1. Actual repository findings (read in this session, resolved from the merged tree)

### 1.1 Governing documents read

`AGENTS.md`; `docs/contracts/DATA_DICTIONARY.md` (§§2.7–2.10, 2.16–2.18, 2.21, 3.1–3.3, 5.1); `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`; `docs/contracts/TOOL_CONTRACTS.md` (incl. `:270`, `:279`); `docs/contracts/EXTRACTION_PROVENANCE.md` (§§5–6); `docs/clinical-safety/DEMO_REVIEW_RULES.md` (§§3–10, `:81`, `:123`, `:125`, `:135`, `:161`); `docs/evaluation/GOLD_FIXTURES.md`; `docs/phase-reports/P4_RUN_BOUND_INTEGRATION_DESIGN_20261122.md`, `P4_RB1_READONLY_ADAPTER_REVIEW_20261122.md`, `P4_RB2_OFFLINE_SIX_RULE_DESIGN_20261122.md`, `P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md`, `P5_F1_…_20261121.md`, `P5_F2_…_20261122.md`, `PHASE_3_WINDOWS_ACCEPTANCE.md`, `PHASE_4_REPORT.md`; `docs/roadmap/PHASE_PROGRESS.md`; `data/synthetic/golden_cases/GOLD-D.expected.json`; `data/synthetic/policy/demo_review_policy.yaml`.

### 1.2 Merged source actually inspected (with the facts that shape this design)

| Area | Path | Facts relied on |
|---|---|---|
| F0 run foundation | `backend/app/services/p5_run_foundation.py` | `WORKFLOW_VERSION = "1.0.0"` (`:40`), `STATE_SCHEMA_VERSION = "1.0.0"` (`:41`), `POLICY_REFERENCE_VERSION`; persisted onto `workflow_run` (`:279-285`); prior-manifest version equality check (`:257`) |
| F1 gate | `backend/app/services/p5_run_gate.py` | `GATE_VERSION = "1.0.0"` (`:71`, exported `:929`); `MAX_GATE_FACTS = 40`, `MAX_GATE_OBSERVATIONS = 100` (`:72-73`); `RunGateReceipt` fields (`:87-101`) incl. `gate_version`, `input_fingerprint_sha256`, `decision`, `historical_excluded_vi002_ids`, `blocking_fact_count`, `replayed`, `runtime_evaluable=False`; `_authorize` (`:141-168`) proves stored session **ownership** (`UserSession.user_id == principal.user_id`), `revoked_at IS NULL`, `created_at <= at < expires_at`, `User.role == doctor`, `is_active == 1`, `Patient.data_source == 'synthetic_fixture'`, `require_assigned_patient`; run-version denial `unsupported_run_version` (`:276-282`); manifest bounds 1..5 docs / ≤20 obs / ≤20 omissions (`:234`); snapshot payload (`:242-273`) covering the run row, documents (`:305`), facts (`:361`), decisions (`:384`), issues (`:485`), **the complete patient observation history with every column** (`:531-562`, `order_by(Observation.id)`, `limit(101)`, `>100 → unavailable="too_many_patient_observations"`), omissions (`:683`), and policy settings (`ocr_confidence_floor`, `conflict_tolerance`); selected-observation revalidation incl. `observation_created_at`, `trust_level`, `source_fact_id` (`:564-604`); VI-006 detection over **selected documents only** (`:608`) with a strict shape gate that `continue`s (`:622-628`) and same-UTC-day comparison at `conflict_tolerance` (`documents/issues.py:217-258`); source-byte re-hash before digest (`:733`) and `fingerprint = _sha(snapshot)` (`:736`); idempotency key `_sha([run.id, fingerprint, GATE_VERSION])` (`:744`); `inspect_current_run_gate_locked` (`:857-884`) requires `db.in_transaction()` and raises `409 E_VALIDATION` unless `decision == 'proceed'` with no issues, and its docstring states **"Only the F2 bridge may call this"**; `evaluate_run_verification_gate` (`:887-925`) requires a fresh clean Session (`:905`), maps `OperationalError` on `BEGIN IMMEDIATE` to `503 E_VALIDATION` "Verification database is unavailable." (`:913-917`) |
| F2 evidence bridge | `backend/app/services/p5_evidence_bridge.py` | `CONTRACT_VERSION = "2.0.0"` (`:46`, the only service export besides the builder, `:475`); `COMPARISON_HISTORY_VERSION = "f2-history-365d-v1"`, `HISTORY_LOOKBACK_DAYS = 365`, `MAX_CURRENT_OBSERVATIONS = 6`, `MAX_FACTS = 40`, `MAX_HISTORY_OBSERVATIONS = 100` (`:47-52`, **not** in `__all__`); `_projection` requires a stored PROCEED row matched on `gate_version` **and** `input_fingerprint_sha256` (`:96-105`); selected-manifest equality incl. `observation_created_at` (`:246-251`); admissibility via public `admissibility_reason` (`:255`, `:288`); fresh history/exclusion derivation (`:278-295`); 365-day comparison (`:301-308`) with `compared.excluded_history` refusal (`:310-311`); final locked gate re-check and byte re-hash with the explicit comment that **"Filesystem and DB are not jointly transactional"** (`:330-344`); fingerprint payload (`:348-403`) whose `observations` member is **`projected_current_rows` only** (`:378-389`, no `created_at`), history appearing only via `comparisons` (`:390-399`), `history_exclusions` (`:401`) and `historical_issues` (`:402`); returned DTO exposes `workflow_version`, `state_schema_version`, `mapping_version`, `policy_version`, `gate_version`, both fingerprints (`:405-428`) |
| P4-2e read-only provenance | `backend/app/services/p4_readonly_provenance.py` | `MAX_OFFLINE_ROWS = 100` (`:31`); `ReadonlyProvenanceEvidence(records, lineage_exclusions, patient_id, as_of_utc)` (`:34-41`); `load_readonly_provenance_evidence(db, *, principal, patient_id, as_of_utc)` (`:143-215`) re-proves doctor/assignment/synthetic scope, reads observations `order_by(measured_at DESC, id)` `limit(101)` and refuses `>100` (`:178-186`), and per row returns `CandidateRecordedObservation(observation=ObservationSnapshot(...), created_at, source, source_fact_id, source_document_id, source_fact_verification_status)` with `verified_lineage_unavailable` exclusions when a `verified_document` row has no stored lineage (`:188-208`); all three names are public (`:221`) |
| RB1 preview | `backend/app/services/p4_run_bound_preview.py`, `backend/app/schemas/p4_run_bound_preview.py` | Pinned literals `POLICY_CANONICAL_SHA256 = f3bdad3f…bd36`, `POLICY_VERSION = "demo-policy-1.1.0"`, `POLICY_LOOKBACK_DAYS = 90` (`:37-39`); `_pinned_policy()` recompiles the sealed R3-A values and refuses alteration (`:48-87`); `_policy_projection_locked` re-checks the gate fingerprint **and** `evidence.gate_version` (`:108-112`), pins run identity/policy/injected clock (`:114-125`), re-reads the immutable selection with a ≤6 bound (`:127-140`), loads provenance (`:142-150`), **uses F2's cached `history_exclusions` as `excluded_ids`** (`:152-158`), proves every selected stored value and provenance field (`:160-183`), returns early on zero selected (`:185-188`), builds `history_rows` by **subtracting cached exclusion ids** (`:190-194`), recomputes 90-day comparisons and refuses unreported exclusions/incomplete comparisons (`:195-206`); `__all__ = ["POLICY_VERSION", "build_p4_run_bound_review_input_preview"]` (`:…`) — the pinned-sha/lookback/rule-id constants are **not** exported; the preview DTO has **no** version fields and hard-codes `runtime_evaluable=False`, `rules_executed=False`, `policy_status='unapproved'`, `review_items_persisted=False` (schema `:54-57`) |
| RB2 offline evaluator | `backend/app/services/p4_rb2_offline_rules.py`, `backend/app/schemas/p4_rb2_offline_rules.py` | Single export `evaluate_p4_rb2_offline_fixture` (`:503`); `_RULES` = the six DR ids (`:53`); decimal context `prec=28` (**R08**, `:59`); `max_items_per_type` must be exactly `3` (`:112-113`); per-measure deltas (`:120`); `_flag` builds `refs = sorted({observation:<id>…} ∪ extra_evidence)`, refuses empty evidence, and sets `dedupe_key = sha256("|".join((patient_id, rule, *refs, trust)))` (`:150-174`); `_valid_id` refuses `|`, control chars and non-stripped values, protecting that serialization (`:176-188`); `_validate_row` denies foreign patients with `E_SCOPE_VIOLATION` (`:190-199`); `lineage_status` admits **only** `{unavailable, fixture_asserted}` and rejects anything else as "Unsupported or forged provenance authority" (`:221-225`), with `stored_independently_verified` documented in the schema as "a FUTURE RB3 server-side state; never a valid caller claim on the RB2 pure fixture interface" (schema `:67-69`) and asserted rejected in `tests/p4/test_p4_rb2_offline_rules.py:275`; provenance claims on non-document rows refused (`:226-229`); `pending`/`rejected` fact assertions fail closed with `E_UNVERIFIED_FACT` (**R05**, `:236-243`); `_independent_fixture_source` requires `verified_document` + `doctor_verified` + `lineage_status == 'fixture_asserted'` + `source_fact_verification_status == 'verified'` + non-empty document and fact ids (`:247-257`); a `verified_document`/`doctor_verified` row that is **not** independently sourced emits the typed exclusion `verified_lineage_unavailable` (**R02**, `:316-321`); unparseable/missing `created_at` emits `missing_created_at` (**R03**, `:313-315`); input caps `selected_current > 6` / `history > 100` refused (`:272-274`); DR-003 uses the newest admissible same-unit row for explicitly selected types (owner clarification, `TOOL_CONTRACTS.md:279`); DR-006 iterates `combinations(ordered, 2)` over **all** eligible rows of a measure type and requires identical `measured_at`, differing values, `_independent_fixture_source` on both rows, and distinct document **and** fact ids (`:423-451`); DR-008 combines duplicate-value and `created_at`-order evidence (`:452-479`); per-measure dedupe then a cap check raising `E_RULE_POLICY_INVALID "Rule item cap exceeded."` (`:482-489`); final ordering `(_HINT_ORDER[hint], rule_id, evidence, dedupe_key)` and exclusions sorted by `(observation_id, reason)` (`:490-499`); `OfflineRuleResult` carries frozen honesty literals `runtime_evaluable=False`, `rules_executed=False`, `review_items_persisted=False`, `policy_status='unapproved'` (schema) |
| Audit | `backend/app/services/audit.py`, `backend/app/db/models.py`, `backend/app/core/enums.py` | `SAFE_DETAIL_MAX = 500` (`:31`); event vocabulary "Namespaced so P3+ can extend it additively" (`:33-40`); `derive_audit_key(event_type, actor_type, actor_id, outcome, subject_type, subject_id, request_id)` (`:49-74`) — **`request_id` is part of the key**; `safe_detail()` whitespace-collapses and truncates to 500 (`:77-87`); `append_audit_event(db, *, event_type, actor_type, actor_id, outcome, request_id, now, patient_id=None, workflow_run_id=None, subject_type=None, subject_id=None, detail_fragments=())` returns an existing row **by key alone, without comparing any other content** (`:124-128`), otherwise inserts and flushes (`:130-146`); `record_denial` **commits immediately** (`:170-190`); `ActorType = {USER='user', SYSTEM='system', DEMO_ADMIN='demo_admin'}` — no doctor member; `AuditOutcome = {OK, DENIED, ERROR}`; `AuditEvent.event_type` is `String(48)` NOT NULL with **no** CHECK, `actor_type`/`outcome` are closed CHECKs, `idempotency_key` is `String(64)` UNIQUE, `safe_detail` is `String(500)`, `workflow_run_id` FK `ondelete='RESTRICT'`; `DATA_DICTIONARY.md` §2.17 lists `event_type` values as examples ("e.g.") and states no UPDATE/DELETE in the application layer |
| Errors | `backend/app/core/errors.py` | `ErrorCode.IDEMPOTENCY_CONFLICT = "E_IDEMPOTENCY_CONFLICT"` **exists** in the P2 surface, alongside `FORBIDDEN`, `SCOPE_VIOLATION`, `NOT_FOUND`, `VALIDATION`; the docstring states that later-phase codes such as `E_UNVERIFIED_FACT` are **deliberately absent** — so RB3 must map RB2's string codes onto existing enum members and must **not** add an `ErrorCode` member |
| Migrations | `backend/migrations/versions/0001…0007*.py` | Verified head `0007_p5_run_gate` (`:15-16`, `down_revision = "0006_p5_run_foundation"`); `0006` immutability-trigger pattern `trg_<table>_<op>_immutable` with `RAISE(ABORT, …)` over `IMMUTABLE_EVENTS = ("UPDATE","DELETE")` (`:31`, `:156-162`); `length(source_sha256) = 64` CHECK (`:136`) and a literal-pinning CHECK (`:133-135`); downgrade refusal via `_persisted_run_evidence()` + `RuntimeError(DOWNGRADE_REFUSED_MESSAGE)` (`:21-24`, `:165-184`); batch-mode FK addition to existing nullable columns (`:143-152`); `0003` conditional cross-table trigger `WHEN (SELECT role FROM user WHERE id = NEW.verified_by_user_id) IS NOT 'doctor'` (`:267-277`), plain UNIQUE index on a nullable column `ux_obs_source_fact` (`:263`) and index-before-column drop ordering (`:281-283`); `0002` partial UNIQUE index `uq_observation_checkin_identity` with `sqlite_where` (`:289`), mirrored in the ORM (`models.py:278-287`) and reflected by name in `scripts/python/check_alembic_smoke.py:513-520` |

### 1.3 Verified public interfaces RB3 may call (no invented APIs, no private imports)

RB3's implementation may import **only** these public names, each verified in this session:

- `app.services.p5_run_gate`: `GATE_VERSION`, `RunGateIssue`, `RunGateReceipt`, `evaluate_run_verification_gate`, `inspect_current_run_gate_locked` (`__all__` `:927-933`). RB3 calls `inspect_current_run_gate_locked` (read-only, caller-owned lock). RB3 **never** calls `evaluate_run_verification_gate` from a read-only path, and never imports the private `_authorize`, `_evaluate_locked`, `_file_sha`, `_sha` or `_receipt`.
- `app.services.p5_evidence_bridge`: `CONTRACT_VERSION`, `build_run_evaluable_review_evidence` (`__all__` `:475`). `COMPARISON_HISTORY_VERSION`, `HISTORY_LOOKBACK_DAYS` and the `MAX_*` bounds are **not** exported, so RB3 must not import them; it pins F2's identity through the returned DTO's `bridge_input_fingerprint_sha256` instead.
- `app.services.p4_readonly_provenance`: `MAX_OFFLINE_ROWS`, `ReadonlyProvenanceEvidence`, `load_readonly_provenance_evidence` (`__all__` `:221`).
- `app.services.p4_run_bound_preview`: `POLICY_VERSION`, `build_p4_run_bound_review_input_preview` (`__all__`). `POLICY_CANONICAL_SHA256`, `POLICY_LOOKBACK_DAYS`, `EXPECTED_RULE_IDS`, `EXPECTED_VI_IDS` are **not** exported: RB3 re-validates its own pinned policy literal through `validate_demo_policy` and asserts equality against the preview DTO's exposed `policy_version` and `policy_reference_sha256` rather than importing RB1's constants.
- `app.services.monitoring`: `MonitoringInputError`, `ObservationSnapshot`, `admissibility_reason` (`__all__` `:219-225`+); signature `admissibility_reason(row: ObservationSnapshot, *, patient_id: str, as_of_utc: datetime) -> str | None` (`:109-111`).
- `app.services.p4_explicit_history`: `compare_explicit_current_with_history`.
- `app.services.p4_rb2_offline_rules`: `evaluate_p4_rb2_offline_fixture` (sole export).
- `app.schemas.p4_rb2_offline_rules`: `OfflineEvidenceExclusion`, `OfflineObservation`, `OfflineRuleError`, `OfflineRuleFlag`, `OfflineRuleInput`, `OfflineRulePolicy`, `OfflineRuleResult` (`__all__` `:113-121`). `OfflineRuleError` is imported from the **schema** module, not the service.
- `app.services.demo_policy`: `DemoPolicyCandidate`, `DemoPolicyError`, `validate_demo_policy`.
- `app.services.audit`: `SAFE_DETAIL_MAX`, `append_audit_event`, `derive_audit_key`, `safe_detail` and the `EVENT_*` constants (`__all__`). `record_denial` is **prohibited** in RB3 because it commits (`:189`).
- `app.core.enums`: `ActorType`, `AuditOutcome`, `MAPPING_VERSION`, `MAPPING_VERSION_PATTERN`, `MeasureType`, `Role`, `Unit`. `app.core.errors`: `ApiError`, `ErrorCode`. `app.core.clock`: `format_utc`, `parse_utc`, `to_utc`. `app.core.policies`: `Principal`, `require_assigned_patient`, `require_doctor`.
- `app.db.models`: existing ORM classes only, plus the additive RB3 classes proposed in §6.

No other helper is assumed to exist. Nothing in this list grants execution authority: `load_readonly_provenance_evidence`'s own docstring forbids passing its rows to a live rule executor, and RB3 honours that by treating the evaluator as a bounded offline computation whose output is persisted as demo review data, never as runtime clearance.

---

## 2. (A) Authority and authorization design

### 2.1 Proposed internal authenticated service boundary

```python
# backend/app/services/p4_rb3_review_persistence.py  (PROPOSED — does not exist)
def persist_run_review_items(
    db: Session,
    *,
    principal: Principal,
    run_id: str,
    validation_clock: datetime,
    upload_root: str,
) -> ReviewPersistenceReceiptV1: ...
```

Exactly five server-owned parameters. There is **no** parameter through which a caller can supply a clearance flag, a gate decision, a trusted-fact count, an evidence id list, a policy override, a lookback window, a cached V2/RB1/RB2 object, an idempotency token or a lineage claim. Such inputs are structurally impossible, not merely ignored (**D-RB3-01**: internal authenticated service only; no HTTP router, no agent tool, no graph node, no task, no notification).

The receipt type `ReviewPersistenceReceiptV1` is a new frozen dataclass in `backend/app/schemas/p4_rb3_review_persistence.py` (§8.3). It is a report about a completed write, never an execution token: it carries `runtime_evaluable=False`, `policy_status='unapproved'`, `demo_only=True` and `not_for_clinical_use=True`.

### 2.2 Authorization conditions (all re-proved from stored rows inside the write transaction)

RB3 re-proves, in this order, from persisted rows only — semantically mirroring `p5_run_gate._authorize` (`:141-168`) without importing it:

1. `isinstance(principal, Principal)` and `require_doctor(principal)` → else `403 E_FORBIDDEN`.
2. `run = db.get(WorkflowRun, run_id)`; missing → `404 E_NOT_FOUND` "Run is unavailable."
3. `run.doctor_id == principal.user_id` → else `403 E_FORBIDDEN`.
4. **Stored session, including ownership:** a `UserSession` row with `id == principal.session_id` **and `user_id == principal.user_id`** (both conditions, explicitly), `revoked_at IS NULL`, `parse_utc(created_at) <= validation_clock < parse_utc(expires_at)`; any `TypeError/AttributeError/ValueError` while parsing means **inactive**, never "assume valid" → else `403 E_FORBIDDEN`.
5. `User.role == Role.DOCTOR.value` and `User.is_active == 1` → else `403 E_FORBIDDEN`.
6. `Patient` exists, `patient.data_source == 'synthetic_fixture'`, `patient.id == run.patient_id` → else `403 E_FORBIDDEN`.
7. `require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)` → `403 E_SCOPE_VIOLATION` on reassignment; a patient reassigned after the run was created is denied here.
8. `run.status == 'queued'` (the F0/F1/F2-eligible state) → else `409 E_VALIDATION`.
9. Run version identity: `run.mapping_version == MAPPING_VERSION`, `run.workflow_version == WORKFLOW_VERSION`, `run.state_schema_version == STATE_SCHEMA_VERSION`, `run.policy_version == POLICY_REFERENCE_VERSION`, and `run.current_node`, `run.halt_reason`, `run.checkpoint_ref` all `NULL` → else `409 E_VALIDATION` (F1 already denies these as `unsupported_run_version` / `run_execution_state_unexpected`, `:270-282`; RB3 denies independently rather than trusting that it ran).
10. Immutable demo clock: `run.as_of_utc == '2026-11-14T12:00:00Z'` and `parse_utc(run.as_of_utc) == to_utc(validation_clock)` → else `409 E_VALIDATION`.

**Clock semantics (corrected, RB3-D06).** `validation_clock` is a fixed injected UTC instant that **defines** the evaluation instant; it is compared against stored session validity windows. RB3 makes **no** claim to detect wall-clock expiry during execution: there is no defined revalidation clock mechanism other than re-testing the same injected instant against stored rows at T2 and again at T16. If the owner later wants elapsed-time expiry inside a long transaction, that requires a separately defined clock source and its own decision; nothing here provides it.

### 2.3 Denial and stale-evidence conditions (typed, fail-closed, zero writes)

| Condition | Denial |
|---|---|
| Missing/stale/HALT/UNAVAILABLE F1 gate, or `inspect_current_run_gate_locked` raising | Propagate its `409 E_VALIDATION` ("Current F1 gate is not eligible.") — zero writes |
| No stored PROCEED `RunGateEvaluation` matching `gate_version` + `input_fingerprint_sha256` | `409 E_VALIDATION` "A matching stored F1 PROCEED is required." |
| F1 fingerprint at T16 differs from T3 | `409 E_VALIDATION` "Source evidence changed during review persistence." |
| Re-hashed source bytes differ from stored `Document.sha256`/`size_bytes` | `409 E_VALIDATION` (F1's `source_bytes_unavailable` / `selected_document_changed` surface through the locked gate re-check) |
| Session revoked, expired, or owned by another user; patient reassigned | `403 E_FORBIDDEN` / `403 E_SCOPE_VIOLATION` |
| Foreign patient/run/document/observation/fact reference anywhere in the projection | `403 E_SCOPE_VIOLATION` |
| Immutable selection, run identity, policy pin or injected clock mismatch | `409 E_VALIDATION` |
| Freshly derived exclusions differ from the cached F2/RB1 exclusion sets | `409 E_VALIDATION` "Historical exclusion evidence changed." |
| Malformed stored timestamps (`measured_at`, `created_at`, `as_of_utc`, session windows) | Typed denial for **scope-bearing** fields (run clock, session windows, selected `measured_at`); for historical `created_at`, the ratified **R03** behaviour applies — the frozen evaluator emits a `missing_created_at` typed exclusion while preserving proven duplicates, and RB3 surfaces that exclusion in the receipt instead of inventing a stricter denial (§4.5) |
| Caps exceeded (>6 selected current, >100 history, >40 facts, >5 or <1 documents, per-measure item cap) | Fail closed: `409 E_VALIDATION` for RB3-side bounds; RB2's own typed `OfflineRuleError` is mapped per §4.4 |
| Unresolvable evidence key (no stored row, no resolvable span) | `409 E_VALIDATION` "Evidence is not resolvable to stored sources." — never invent a span, fact or free-text link |
| Any `OfflineRuleError` from the frozen evaluator | Map to an existing `ErrorCode` (§4.4), roll back, zero writes |
| Replay ambiguity or mismatch (§8.2) | `409 E_IDEMPOTENCY_CONFLICT` with a bounded reason string |
| DR-006 present while the owner has ratified the conservative prohibition | `409 E_VALIDATION` reason `dr006_persistence_not_authorized` — the **entire** invocation fails closed (§7.4, **D-RB3-08**) |

**No committed denial audit in this slice.** `record_denial` commits immediately (`audit.py:189`), which would survive a rollback and create a second write path; RB3 must not call it. Denials raise inside the write transaction and roll back; the caller receives the typed error. A future committed-denial audit trail is a separate owner decision, not part of RB3.

**No new `ErrorCode` member.** `core/errors.py` deliberately omits later-phase codes; RB3 maps RB2's string codes onto existing members and preserves the original string as a bounded reason in the denial detail and receipt.

### 2.4 Field-to-source mapping (corrects the invalid `preview.gate_version` expression, RB3-D03)

`RunBoundReviewInputPreviewV1` (`schemas/p4_run_bound_preview.py:33-57`) exposes: `contract_version`, `run_id`, `patient_id`, `doctor_id`, `as_of_utc`, `policy_version`, `policy_reference_sha256`, `policy_baseline_lookback_days`, `gate_evaluation_id`, `gate_input_fingerprint_sha256`, `bridge_input_fingerprint_sha256`, `selected_document_ids`, `selected_observation_ids`, `verified_facts`, `selected_observations`, `policy_comparisons`, `history_exclusions`, `no_current_reason`, and the four frozen `False`/`'unapproved'` literals. It has **no** version fields. The authoritative source of every field RB3 needs is therefore:

| Field | Authoritative source (actual) | Not from |
|---|---|---|
| `gate_version` | `RunGateReceipt.gate_version` returned by `inspect_current_run_gate_locked`, equal to the public constant `p5_run_gate.GATE_VERSION`; corroborated by the persisted `RunGateEvaluation.gate_version` and by `EvaluableReviewEvidenceV2.gate_version` (`p5_evidence_bridge.py:411`) | ~~`preview.gate_version`~~ (does not exist) |
| `workflow_version` | Persisted `WorkflowRun.workflow_version`, re-read under the lock; F1 validates it against `p5_run_foundation.WORKFLOW_VERSION` (`p5_run_gate.py:279`); corroborated by `EvaluableReviewEvidenceV2.workflow_version` (`:409`) | ~~`preview.workflow_version`~~ |
| `state_schema_version` | Persisted `WorkflowRun.state_schema_version`; F1 validates against `p5_run_foundation.STATE_SCHEMA_VERSION` (`:280`); corroborated by the F2 DTO (`:410`) | ~~`preview.state_schema_version`~~ |
| `mapping_version` | Persisted `WorkflowRun.mapping_version`; F1 validates against `core.enums.MAPPING_VERSION` (`:277`) | ~~`preview.mapping_version`~~ |
| `policy_version` | Persisted `WorkflowRun.policy_version` (must equal `POLICY_REFERENCE_VERSION`), cross-checked against `preview.policy_version` and `EvaluableReviewEvidenceV2.policy_version`, and against the pinned demo policy `demo-policy-1.1.0` | caller input |
| `policy_reference_sha256` | `preview.policy_reference_sha256` (exposed) — asserted equal to RB3's own re-validated pinned-policy digest | caller input |
| `gate_evaluation_id` | `preview.gate_evaluation_id`, re-proved by querying the stored PROCEED `RunGateEvaluation` row at T3 | caller input |
| `gate_input_fingerprint_sha256` | `RunGateReceipt.input_fingerprint_sha256` from the locked re-check, asserted equal to the persisted PROCEED row and to `preview.gate_input_fingerprint_sha256` | caller input |
| `bridge_input_fingerprint_sha256` | `EvaluableReviewEvidenceV2.bridge_input_fingerprint_sha256`, asserted equal to `preview.bridge_input_fingerprint_sha256` | caller input |
| F2 contract version | Public `p5_evidence_bridge.CONTRACT_VERSION` (`"2.0.0"`) | non-exported module constants |
| History policy identity | Opaque: it is already inside `bridge_input_fingerprint_sha256` (`"history_policy": COMPARISON_HISTORY_VERSION`, `:351`). RB3 pins the digest, never the non-exported constant | importing `COMPARISON_HISTORY_VERSION` |
| 90-day lookback | RB3's own re-validated pinned policy (`baseline_lookback_days = 90`), asserted equal to `preview.policy_baseline_lookback_days` (a `Literal[90]`) | caller input |
| `as_of_utc` | Persisted `WorkflowRun.as_of_utc`, asserted equal to `preview.as_of_utc` and to `to_utc(validation_clock)` | caller input |

Consequence: the T3 assertion is expressed against `RunGateReceipt` and persisted `WorkflowRun`/`RunGateEvaluation` columns, never against preview attributes that do not exist. Frozen RB1/F2 schemas are **not** changed, implicitly or otherwise.

---

## 3. (B) Fresh transactional verification — exact SQLite transaction ownership and lock boundary

### 3.1 Honest non-atomicity acknowledgements (normative)

1. **SQLite cannot transact with filesystem bytes.** The uploaded source files live outside the database. `BEGIN IMMEDIATE` gives a write lock over the database only.
2. **Re-hashing narrows but does not close the race.** RB3 re-hashes every selected source byte twice (at T3 through the locked F1 re-check, and again at T16 immediately before COMMIT), exactly as F2 does (`p5_evidence_bridge.py:330-344`, whose own comment states filesystem and DB are not jointly transactional). A byte change landing between the T16 re-hash and the operating-system-level durability of the commit cannot be excluded by any SQLite transaction. RB3 therefore claims *reduction*, never elimination, of the check-to-commit race.
3. **The F1, F2 and RB1 sessions are separate transactions.** Phase 1 performs up to three independently locked read/projection passes, each with its own `BEGIN IMMEDIATE` and its own commit/rollback. They are **not** one snapshot and are never described as one. Only Phase 2 writes RB3 rows, and it is the only committing transaction RB3 owns.
4. **RB3 owns exactly one committing transaction.** It begins at T1 with `db.connection().exec_driver_sql("BEGIN IMMEDIATE")` on a Session verified clean beforehand, and ends at T16 with a single `db.commit()` or an unconditional `db.rollback()`.
5. **No partial persistence.** Every insert (items, links, completion record, audit row) happens inside that one transaction; any exception rolls all of it back.

### 3.2 Revised transaction sequence

**Phase 1 — read-only pins (no RB3 writes; each helper owns and closes its own lock).**

| Step | Action | Failure |
|---|---|---|
| P1 | Assert a fresh clean Session: `not db.in_transaction() and not db.new and not db.dirty and not db.deleted` (mirrors `p5_run_gate.py:905`, `p4_run_bound_preview.py:241`) | `400 E_VALIDATION` "A fresh clean Session is required." |
| P2 | `build_run_evaluable_review_evidence(db, principal=…, run_id=…, validation_clock=…, upload_root=…)` → F2 DTO (its own lock; commits only typed F2 evidence) | propagate |
| P3 | `build_p4_run_bound_review_input_preview(db, principal=…, run_id=…, validation_clock=…, upload_root=…)` → RB1 preview (its own separate locks; always rolled back) | propagate |
| P4 | Assert the preview's frozen literals: `contract_version == 'p4-rb1-preview-1.0.0'`, `policy_version == 'demo-policy-1.1.0'`, `policy_reference_sha256 == <R3-A LF seal>`, `policy_baseline_lookback_days == 90`, `as_of_utc == '2026-11-14T12:00:00Z'`, `runtime_evaluable is False`, `rules_executed is False`, `review_items_persisted is False`, `policy_status == 'unapproved'` | `409 E_VALIDATION` |
| P5 | Assert `to_utc(validation_clock) == parse_utc(preview.as_of_utc)` | `409 E_VALIDATION` |
| P6 | Assert cross-DTO agreement: `preview.gate_input_fingerprint_sha256 == evidence.gate_input_fingerprint_sha256`, `preview.bridge_input_fingerprint_sha256 == evidence.bridge_input_fingerprint_sha256`, `preview.gate_evaluation_id == evidence.gate_evaluation_id`, selections equal | `409 E_VALIDATION` |

Phase 1 output is a **cross-check pin only**. Its `history_exclusions` are never carried into Phase 2 as authority (RB3-D01).

**Phase 2 — the single committing write transaction.**

| Step | Action (all inside one `BEGIN IMMEDIATE`) | Failure |
|---|---|---|
| **T1** | Re-assert a clean Session, then acquire the write lock: `db.connection().exec_driver_sql("BEGIN IMMEDIATE")`. **Precondition wording (corrected):** the clean-Session check happens *before* `BEGIN IMMEDIATE`; *after* successful lock acquisition the transaction must be **active** — assert `db.in_transaction() is True`. `OperationalError` during acquisition → `503 E_VALIDATION` "Verification database is unavailable." (mirrors `p5_run_gate.py:913-917`); lock-acquisition failure never yields a success receipt | `400`/`503` |
| **T2** | Re-prove the full authorization chain of §2.2 from stored rows (session ownership, expiry, revocation, role, active flag, synthetic patient, assignment, run status, run versions, execution-state NULLs, immutable clock) | `403`/`409` |
| **T3** | Locked F1 revalidation: `inspect_current_run_gate_locked(db, principal=…, run_id=…, at=validation_clock, upload_root=…)`; then query the stored `RunGateEvaluation` with `workflow_run_id == run.id AND gate_version == GATE_VERSION AND input_fingerprint_sha256 == receipt.input_fingerprint_sha256` and require `decision == 'proceed'`; assert the receipt's fingerprint equals the Phase-1 pin (field sources per §2.4) | `409 E_VALIDATION` |
| **T4** | Re-pin the run and manifest: re-read `RunSelectedDocument` / `RunSelectedObservation` / `RunSourceOmission` for the run in F0's ordering; assert set equality with both DTOs; assert bounds 1..5 documents, ≤20 manifest observations, ≤20 omissions, ≤6 selected current, ≤40 facts, ≤100 history | `409 E_VALIDATION` |
| **T5** | **Fresh full stored-history reconstruction:** `load_readonly_provenance_evidence(db, principal=…, patient_id=run.patient_id, as_of_utc=parse_utc(run.as_of_utc))` → `records` (≤`MAX_OFFLINE_ROWS`) + `lineage_exclusions`. This locked snapshot is the **sole authoritative history source** for the write (§5.6). No separate pre-write history pin object is created | propagate (`400` on >100 rows) |
| **T6** | **Fresh exclusion derivation:** for each record apply public `admissibility_reason(entry.observation, patient_id=…, as_of_utc=…)` and combine with `lineage_exclusions` (`verified_lineage_unavailable`) to derive RB3's own eligible/excluded partition. Then **cross-check** the derived non-selected exclusion set (ids and reason codes) against `evidence.history_exclusions` and `preview.history_exclusions` as drift detectors only; assert selected-current ids are never excluded. Cached exclusion ids are **never** subtracted as authority | `409 E_VALIDATION` "Historical exclusion evidence changed." |
| **T7** | Selected-current stored-value proof: re-read each selected `Observation` and assert patient/measure/unit/exact `Decimal(str(value))`/`format_utc(parse_utc(measured_at))`/trust/source/`source_fact_id`/`source_document_id` equality against the F2 projection and the manifest row's `observation_created_at` (mirrors `p4_run_bound_preview.py:160-183`, `p5_evidence_bridge.py:246-251`) | `409 E_VALIDATION` |
| **T8** | 90-day comparison recomputation: `compare_explicit_current_with_history(current=…, history=<fresh eligible rows>, patient_id=…, as_of_utc=…, baseline_lookback_days=90)`; require `compared.excluded_history == ()` and `len(comparisons) == len(selected_rows)`; assert field-by-field equality with `preview.policy_comparisons`. F2's 365-day comparisons are used **only** as identity inside the pinned bridge fingerprint, never as RB3's comparison source | `409 E_VALIDATION` |
| **T9** | Compute the **complete canonical full-input fingerprint** `rb3-full-input-1.0.0` (§5.4) over everything re-read and re-derived in T2–T8 plus the re-hashed source-byte digests | — |
| **T10** | Project the rule input: build `OfflineRuleInput(patient_id, selected_current, history, as_of_utc, policy, active_fact_verification_statuses)` from stored rows only; `OfflineRulePolicy` values re-validated through `validate_demo_policy` and asserted equal to the preview's pinned `policy_version`/`policy_reference_sha256`; `lineage_status` assigned per §4.3 | `409 E_VALIDATION` |
| **T11** | Call the frozen evaluator `evaluate_p4_rb2_offline_fixture(input)`; catch `OfflineRuleError` → mapped typed denial (§4.4); assert the result's frozen honesty literals are unchanged (`runtime_evaluable=False`, `rules_executed=False`, `review_items_persisted=False`, `policy_status='unapproved'`) | mapped denial |
| **T12** | DR-006 owner-decision gate (§7.4): if a DR-006 flag exists and the conservative prohibition is ratified, deny the **whole** invocation; never persist a subset | `409 E_VALIDATION` |
| **T13** | Stored-evidence proof for every emitted evidence key (§7.2): resolve each `observation:`/`document:`/`fact:` reference to a real stored row of the same patient; a `document_span` link may be written only when the fact's span is resolvable from stored provenance; unresolvable → denial, zero writes | `409 E_VALIDATION` |
| **T14** | Completion-record read (§8.2): select the single `review_evaluation` row for `workflow_run_id`; branch to first-evaluation, exact-replay no-op, or typed `E_IDEMPOTENCY_CONFLICT`; re-read the linked `audit_event` by `audit_event_id` and validate its identity **and** required content | `409 E_IDEMPOTENCY_CONFLICT` |
| **T15** | Inserts, in this order, all inside the transaction: `review_item` rows (`state='open'` only) → `evidence_link` rows → the single `review_evaluation` completion row → one `append_audit_event(...)` row (§8.4). No UPDATE, no DELETE, no supersession, no second audit mechanism. On exact replay: **zero writes of any kind** | `IntegrityError` → rollback → typed conflict |
| **T16** | Pre-commit revalidation: re-call `inspect_current_run_gate_locked`, re-hash every selected source byte, recompute the full-input fingerprint, and require all three to be unchanged from T3/T9; then the single `db.commit()`. Any exception anywhere in T1–T16 → `db.rollback()` and re-raise | `409 E_VALIDATION` + rollback |

### 3.3 Concurrency, replay and denial handling

- **Concurrency.** `BEGIN IMMEDIATE` serializes writers. A second invocation blocks until the first commits or rolls back, then resolves through T14 as exact replay or typed conflict. `UNIQUE ux_review_evaluation_run` is the final structural backstop: a racing insert raises `IntegrityError`, which RB3 converts to a rollback plus `409 E_IDEMPOTENCY_CONFLICT`, never a partial write.
- **Denials.** Raise inside the transaction; the rollback removes every pending row. No denial is audited in a separate committed transaction in this slice (§2.3).
- **Retries.** A rolled-back attempt persisted nothing — no rows, no completion record, no audit row, and its generated UUIDs never existed in the database. A retry is therefore a first evaluation. Retry equivalence means **identical semantic output and identical evidence identity**; newly generated `review_item.id` / `evidence_link.id` / `review_evaluation.id` values need not match a previous rolled-back attempt (§8.2 case 13).

### 3.4 P5 source impact assessment

Exact correctness of RB3 does **not** require changing any accepted F0/F1/F2/RB1 path: every interface RB3 needs is already public (§1.3), and the complete-history gap is closed by RB3's own fresh reconstruction and fingerprint (§5) rather than by editing F2.

One documentation-only inconsistency is identified, not made:

- **E6 (conditional, docstring-only).** `inspect_current_run_gate_locked`'s docstring states "Only the F2 bridge may call this with an already open BEGIN IMMEDIATE transaction" (`p5_run_gate.py:862-868`). RB3's T3/T16 call it under the same contract (caller-owned lock, no writes). Leaving the docstring unchanged would make the merged source contradict its own approved usage. The proposed exception is a **docstring-only** clarification naming RB3 as an additional locked-read caller, with **zero** logic, signature, behaviour or test-semantics change in `backend/app/services/p5_run_gate.py`. **D-RB3-02b** prefers this separately authorized clarification over knowingly contradictory source documentation. No other P5 path is proposed for change; if the owner rejects E6, RB3 must instead record the deviation in an append-only `TOOL_CONTRACTS.md` note and leave the P5 docstring untouched (the fallback in **D-RB3-02b**).

---

## 4. (C) RB2-to-RB3 evaluator boundary

### 4.1 Pinned R3-A fixture clock vs the immutable persisted run clock

RB2 enforces one pinned clock (`_PINNED_CLOCK = 2026-11-14T12:00:00Z`) on both the injected clock and `policy.demo_as_of_utc`. A persisted run carries an immutable `WorkflowRun.as_of_utc`. RB3 does not reconcile these by relaxing either: it **requires equality**. A run is persistable only if `run.as_of_utc == '2026-11-14T12:00:00Z'` and `to_utc(validation_clock) == parse_utc(run.as_of_utc)` (§2.2 items 9–10, P5). Runs with any other clock are denied, not converted, and no wall clock is ever substituted. This inherits RB1's existing binding (`p4_run_bound_preview.py:114-125`) and weakens nothing (**D-RB3-04**).

### 4.2 Offline policy reference vs separately approved execution authority

The pinned R3-A policy is a **reference** for bounded demo comparison. RB1 hard-codes `policy_status='unapproved'` and `runtime_evaluable=False`; RB2's result repeats those literals. Persisting review rows does not approve the policy, activate runtime rules, or create execution authority. RB3's receipt therefore states `policy_status='unapproved'` and `runtime_evaluable=False` even though rows were written, and the completion record stores the immutable `policy_version` and `policy_reference_sha256` so every persisted item is bound to exactly one sealed policy revision.

### 4.3 Fixture-asserted lineage vs actually persisted provenance — decisive constraint and recommendation

Three facts, all verified in this session, decide this boundary:

1. RB2 admits **only** `lineage_status ∈ {unavailable, fixture_asserted}` and rejects anything else as "Unsupported or forged provenance authority" (`p4_rb2_offline_rules.py:221-225`); `stored_independently_verified` is asserted rejected in `tests/p4/test_p4_rb2_offline_rules.py:275`, while the schema documents it as "a FUTURE RB3 server-side state; never a valid caller claim on the RB2 pure fixture interface" (`schemas/p4_rb2_offline_rules.py:67-69`).
2. `TOOL_CONTRACTS.md:270` states that `lineage_status=fixture_asserted` labels ***fictional*** lineage, that `stored_independently_verified` is rejected as forged RB2 caller authority, and that "a future RB3 verifier must instead query and prove the actual selected stored sources".
3. Choosing `unavailable` for stored-proved rows is **not** a neutral option: RB2 emits a typed `verified_lineage_unavailable` exclusion for every `verified_document` + `doctor_verified` row that is not independently fixture-sourced (`:316-321`, R02). Passing `unavailable` for rows whose lineage RB3 just proved would persist **false exclusion claims** and understate provenance — a silent weakening.

Therefore, under an unchanged RB2 evaluator, the only admissible label for a stored-proved row is `fixture_asserted`, and it must be treated as a **transport label**, not a provenance claim. Alternatives:

- **Alt A2 (recommended, retained per review, with corrected conditions).** Use the unchanged RB2 evaluator as a pure computation core. RB3 proves stored lineage itself in-transaction (T5/T7/T13) and passes `lineage_status='fixture_asserted'` **only** for rows whose stored lineage it proved, documenting that value as a transport label required by RB2's closed vocabulary. Every **persisted** artifact tells the truth: `evidence_link` rows point at real stored documents/observations with resolvable spans; `review_evaluation` records the RB3-side lineage state `stored_independently_verified` as an internal completion fact (never passed to RB2); the receipt reports which rows were stored-proved. Conditions: (i) RB2 source, schema and tests remain frozen (zero diffs); (ii) RB3 must not label any DR-006 output as an authenticated doctor verification — the frozen flag already carries `provenance_status='fixture_asserted'` and the rule's own comment states that even qualifying records "do not constitute a real doctor's attestation"; (iii) no trust promotion anywhere (`self_reported_validated` never becomes `doctor_verified`); (iv) mandatory RB3↔RB2 output-equivalence tests on identical inputs; (v) an append-only `TOOL_CONTRACTS.md` note recording the transport-label semantics so the boundary is honest in the contracts, not only in code comments.
- **Alt B (fallback).** RB3-owned derivation of the six rules inside the new persistence module, using `stored_independently_verified` as an RB3-internal typed state that is never passed to RB2. Clean labels and no transport-label fiction, at the cost of duplicating roughly five hundred lines of recently remediated, subtly bounded rule logic (R01–R08), with divergence risk even under equivalence tests and a materially larger review surface. Note that Alt B cannot be implemented *by calling RB2 with a different label* — RB2 rejects that value — so Alt B necessarily means re-derivation, not re-labelling.
- **Alt C (rejected).** Modify RB2 to accept `stored_independently_verified`. It reopens the owner-accepted RB2 candidate `8dd79ac0…`, edits frozen reviewed source and tests, and yields no safety gain over A2's independent in-transaction proof.

Under no alternative is the offline evaluator reused as a runtime clearance token, and under none are the pinned clock, policy constraints or validation weakened. The chosen option is recorded as **C-RB3-01** in §13 because the transport label is a genuine contract-text tension that only the owner can ratify.

### 4.4 Conservative R05 handling of pending/rejected facts

RB2 fails closed with `OfflineRuleError("E_UNVERIFIED_FACT", …)` when a row asserts `source_fact_verification_status ∈ {pending, rejected}` (`:236-243`). RB3 preserves this exactly and adds nothing permissive. Because `E_UNVERIFIED_FACT` is deliberately **absent** from `ErrorCode` (`core/errors.py` docstring), RB3 maps it to `409 E_VALIDATION` and carries the original string `E_UNVERIFIED_FACT` as a bounded reason in the denial detail and receipt — it does not add an enum member. `active_fact_verification_statuses` is populated only from stored `FactVerification`/`ExtractedFact` rows re-read under the lock, never from a caller count.

### 4.5 R01–R08 protections, measurement types, 90-vs-365, bounds, trust, ordering (corrected)

| Protection | Actual ratified behaviour | RB3 obligation (corrected) |
|---|---|---|
| **R01** | Independently pin both normalized clocks | RB3 pins the run clock and the injected clock and requires equality (§4.1); no wall clock |
| **R02** | Per-observation lineage exclusion, including singleton document observations (`:316-321`) | RB3 surfaces every `verified_lineage_unavailable` exclusion in the receipt; never drops one; never fabricates lineage to avoid one |
| **R03** | "Exclude each missing or unparseable created time while preserving proven duplicates" (`P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md:59`); `_clock` returns `None` on `TypeError/ValueError/OverflowError/AttributeError` | **Corrected:** a non-NULL stored `created_at` does **not** prove it is parseable or valid UTC. RB3 does **not** add a hard denial for malformed historical `created_at`; it passes the stored value through unchanged and lets the frozen evaluator emit the ratified `missing_created_at` typed exclusion while preserving proven duplicates (DR-008). Scope-bearing clocks (run `as_of_utc`, session windows, selected `measured_at`) still deny typed, because a malformed value there makes authorization or selection unprovable |
| **R04** | **Corrected:** R04 is the owner-approved **DR-003 newest-admissible-selected-type clarification** — marker `APPROVE-P4-RB2-DR003-NEWEST-ADMISSIBLE-SELECTED-TYPE`, [PR #41 comment #7080736185](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7080736185), `2026-11-22T14:41:49Z`; contract text at `TOOL_CONTRACTS.md:279`: evaluated types come from selected admissible current observations, staleness uses the newest admissible same-patient/same-type/same-unit observation across bounded selected **and** historical inputs, history alone never selects a type | R04 is **not** policy pinning. RB3 must feed both selected and freshly reconstructed historical rows so DR-003 can find the newest admissible same-unit row, and must not restrict DR-003's staleness evidence to selected rows |
| **R05** | `pending`/`rejected` source-fact assertions fail closed even when the top-level status tuple is empty | preserved exactly (§4.4) |
| **R06** | Malformed types produce typed failures | RB3 maps every `OfflineRuleError` to an existing `ErrorCode` and rolls back with zero writes |
| **R07** | Overflow-safe 90-day window by comparing timestamp differences; a UTC year-one selected timestamp previously raised `OverflowError` | **Corrected test expectation:** an RB3 regression case with a year-one timestamp must expect the window comparison to succeed without overflow (and any `created_at`-driven exclusion to be reported), **not** a crash and **not** a typed arithmetic denial |
| **R08** | Explicit local 28-digit decimal context with rounding, exponents and traps specified; `121.1 - 100` emits DR-005 at precision 28 but raised `E_VALIDATION` at precision 2; the caller's context is not altered | **Corrected test expectation:** an RB3 regression case for that shape must expect a persisted DR-005 item with the exact decimal delta, **not** `E_VALIDATION`; RB3 must not change the ambient decimal context before or after the call |

Explicit selected-current measurement types: RB3 persists `review_item` rows only for the measure types the frozen evaluator returns, derived from selected admissible current observations (`_LABELS`: systolic, diastolic, heart-rate, glucose). RB3 never adds, renames or infers a type.

90-day policy vs F2's 365-day window: RB3 recomputes comparisons at **90** days (T8) for review semantics, while F2's **365**-day comparisons (`HISTORY_LOOKBACK_DAYS = 365`, `COMPARISON_HISTORY_VERSION = 'f2-history-365d-v1'`) remain the accepted identity for the bridge fingerprint. The two are never substituted for one another; the 365-day digest is pinned opaquely inside `bridge_input_fingerprint_sha256` (§2.4).

Bounds, trust and ordering: caps ≤6 selected current / ≤100 history / ≤40 facts / 1..5 documents are re-asserted at T4; `max_items_per_type` must be exactly `3` and the per-measure cap is enforced by the frozen evaluator (`:482-489`), so the structural maximum persisted item count is **12** (4 measure types × 3); trust labels are stored exactly as emitted with no promotion; persisted order is the evaluator's `(hint, rule_id, evidence, dedupe_key)` (`:490-495`), and RB3 preserves it via an explicit `display_order` column (§6.1) so retrieval cannot silently reorder.

### 4.6 Contract conflicts requiring explicit owner decisions

Recorded in §13 as **C-RB3-01** (transport lineage label), **C-RB3-02** (DR-006 reachability and persistence), **C-RB3-03** (new `review_evaluation` object versus the dictionary's two-table scope), **C-RB3-04** (evidence-identity uniqueness mechanism). None is resolved by guessing; each has a recommendation and an exact authorization scope.

---

## 5. (RB3-D01) Complete locked historical-evidence reconstruction and the full-input fingerprint

### 5.1 What each existing fingerprint actually covers — authoritative scope

| Fingerprint | Actual coverage (verified) | Authoritative for | **Not** authoritative for |
|---|---|---|---|
| F1 `gate_input_fingerprint_sha256` (`p5_run_gate.py:736`) | Run row (id, patient, doctor, status, `as_of_utc`, all four version fields, idempotency key, `started_at`, `updated_at`, execution-state columns, `patient.assigned_doctor_id`); selected documents' stored columns; facts; verification decisions; open issues; **every column of every patient observation** (`:544-562`, including `created_at`, `note`, `validation`, `trust_level`, `source`, `source_fact_id`, `verified_by_user_id`, `verified_at`, `encounter_id`, `created_by_user_id`), bounded at 100 rows with `too_many_patient_observations` beyond; selected id tuples; `ocr_confidence_floor` and `conflict_tolerance`; omissions; re-hashed source bytes (`:733`) | Integrity of **stored rows** across the whole patient scope: any inserted, removed or mutated observation/document/fact/decision anywhere in that scope changes this digest | Derived rule inputs: eligibility decisions, exclusions, comparisons, measure-type mapping, projection shape, RB2 policy semantics, or which rows RB3 actually fed the evaluator |
| F2 `bridge_input_fingerprint_sha256` (`p5_evidence_bridge.py:348-403`) | `contract`, `history_policy`, stored gate identity, run identity + versions, document ids, selected observation ids, six fact fields, **projected current observations only** (eight fields, **no `created_at`**), comparisons, `history_exclusions` (id + reason), `historical_issues` | Integrity of the V2 projection: current selection, comparisons, reported exclusions | **Complete eligible history.** A non-baseline eligible historical row can change — or a new row appear — without altering the closest-prior baseline comparison, leaving this digest unchanged |
| RB1 preview (`contract_version`, `gate_evaluation_id`, both fingerprints, comparisons, exclusions) | A re-checked *shape* summary; no version fields; `runtime_evaluable=False`, `rules_executed=False`, `policy_status='unapproved'`, `review_items_persisted=False` | Nothing at write time | Any authority. It is a non-executable drift cross-check only, and its `history_exclusions` are **not** an authorization input |
| **RB3 `input_fingerprint_sha256` (new, §5.4)** | The complete canonical rule-input set actually used in the committing transaction | **The durable evaluation identity** for invocation-level replay (§8.2) and the authoritative statement of "these exact inputs produced these exact rows" | Anything beyond that invocation: it is not a gate decision, not a policy approval, not a runtime clearance |
| **RB3 `output_identity_sha256` (new, §8.1)** | The complete persisted semantic item + evidence-link identity | Proof of what was persisted, for replay comparison | Per-row surrogate ids and timestamps, deliberately excluded (§8.1) |

**Explicit statement required by the review:** equality of 90-day comparisons does **not** establish equality of all DR-003/DR-006/DR-008 inputs, and equality of the F2 bridge fingerprint does **not** establish complete pre-read history equality. F1 fingerprint equality *does* detect stored-row mutation, insertion or removal across the patient scope, but it does not detect changes in derived eligibility or projection, and it is not RB3's evaluation identity. No claim of complete pre-read history equality is made from comparison equality.

### 5.2 Fresh full stored-history eligibility and provenance reconstruction under the committing lock

At T5, inside the committing transaction, RB3 calls the public `load_readonly_provenance_evidence(db, principal=…, patient_id=run.patient_id, as_of_utc=parse_utc(run.as_of_utc))`. That helper re-proves doctor/assignment/synthetic scope itself, reads up to `MAX_OFFLINE_ROWS = 100` observations (`limit(101)`, refusing more), and returns per row: an `ObservationSnapshot` (`id`, `patient_id`, `measure_type`, `value`, `unit`, `measured_at`, `validation`, `trust_level`), plus `created_at`, `source`, `source_fact_id`, `source_document_id` and `source_fact_verification_status` derived from **stored** human-decision lineage (`_stored_verified_lineage`), and `lineage_exclusions` carrying `verified_lineage_unavailable` for `verified_document` rows without stored lineage.

RB3 then, still under the lock and still without writes:

1. Applies public `admissibility_reason(entry.observation, patient_id=…, as_of_utc=…)` to every record, capturing `validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp` and any other documented reason.
2. Unions those reasons with the loader's `lineage_exclusions`.
3. Partitions records into `selected_current` (ids equal to the re-pinned immutable selection), `eligible_history` and `excluded` (with reason codes).
4. Re-reads the underlying `Observation` rows for every field the fingerprint needs but the snapshot does not carry (`created_at` is carried by the record; `verified_by_user_id`, `verified_at`, `encounter_id`, `created_by_user_id` are read from the stored row) so the fingerprint covers complete stored identity, not merely the projection.
5. Asserts the partition bounds: `len(selected_current) <= 6`, `len(eligible_history) + len(excluded) <= 100`, `selected_current ∩ excluded == ∅`.

Ordering: the loader returns rows `measured_at DESC, id`; F1 uses `id ASC`; F2 uses `sorted(by_id)`. RB3 therefore defines **one** canonical order for its own artifacts — ascending observation id — and applies it everywhere (fingerprint payload, projection, persisted `display_order` derivation is the evaluator's own ordering, preserved separately). This makes the fingerprint independent of loader ordering.

### 5.3 Fresh exclusion derivation — cached ids are never authority

Revision 1's T5 subtracted the previous preview's history-exclusion ids. That is removed. RB3 derives exclusions fresh (T6) and uses the cached F2/RB1 exclusion sets **only** as equality cross-checks:

- derived non-selected exclusion ids and reason codes must equal `evidence.history_exclusions` and `preview.history_exclusions`; any difference → `409 E_VALIDATION` "Historical exclusion evidence changed."
- a derived exclusion that is also a selected current id → `409 E_VALIDATION` "Selected current evidence may not be excluded." (mirrors `p4_run_bound_preview.py:157-158`)
- if the cross-check passes, the **derived** set is what RB3 uses; the cached set is discarded. If the owner prefers RB3 to trust the cached set instead, that is a different (weaker) design and is not proposed.

Rationale: a cached exclusion list is an output of an earlier transaction. Treating it as authorization would let a stale or forged list suppress evidence from the new evaluation, which is precisely the "caller-supplied evidence ids" prohibition in §2.1.

### 5.4 Complete canonical input fingerprint `rb3-full-input-1.0.0`

Computed at T9 with the same canonicalization discipline the repository already uses (`json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` then SHA-256, as in `p5_run_gate._sha:103-106`), over explicit **lists in canonical order** (never sets, never dict iteration order), with every numeric measurement rendered as an exact `Decimal` string (never float) and every timestamp rendered via `format_utc`:

```text
{
  "fingerprint_version": "rb3-full-input-1.0.0",
  "contracts": {
     "f1_gate": GATE_VERSION,                       # public constant
     "f2_bridge": CONTRACT_VERSION,                 # public constant ("2.0.0")
     "rb1_preview": preview.contract_version,       # "p4-rb1-preview-1.0.0"
     "mapping": MAPPING_VERSION,                    # "map-1.0.0"
     "workflow": run.workflow_version,
     "state_schema": run.state_schema_version
  },
  "run": [run.id, run.patient_id, run.doctor_id, run.status, run.as_of_utc,
          run.mapping_version, run.policy_version, run.workflow_version,
          run.state_schema_version, run.idempotency_key, run.started_at,
          patient.assigned_doctor_id],
  "gate": [stored_gate.id, receipt.gate_version, receipt.input_fingerprint_sha256,
           receipt.decision, receipt.blocking_fact_count,
           sorted(receipt.historical_excluded_vi002_ids)],
  "bridge": [evidence.bridge_input_fingerprint_sha256],
  "policy": [policy.policy_version, policy_reference_sha256,
             policy.baseline_lookback_days, policy.stale_measurement_days,
             str(deltas...), str(policy.ocr_confidence_floor),
             str(policy.conflict_tolerance), policy.max_items_per_type,
             list(policy.enabled_rules), list(policy.enabled_verification_issues),
             str(settings.ocr_confidence_floor), str(settings.conflict_tolerance)],
  "clock": [format_utc(validation_clock), run.as_of_utc],
  "selected_documents": [[d.id, d.patient_id, d.sha256, d.size_bytes, d.mime_type,
                          d.extraction_status, d.stored_path, d.page_count,
                          d.uploaded_at, d.created_at, d.recovered_from_document_id]
                         for d in sorted-by-id selected documents],
  "source_byte_digests": [[document_id, recomputed_sha256] for each selected document],
  "selected_observations": [[complete stored column set incl. created_at,
                             measured_at, value (exact decimal string), unit,
                             validation, trust_level, source, source_fact_id,
                             verified_by_user_id, verified_at, encounter_id,
                             created_by_user_id, manifest.observation_created_at,
                             manifest.trust_level, manifest.source_fact_id]
                            sorted by observation id],
  "history_observations": [[the same complete column set] sorted by observation id],
  "derived_exclusions": [[observation_id, reason_code] sorted by (id, reason)],
  "lineage_proofs": [[observation_id, rb3_lineage_state, source_document_id,
                      source_fact_id, source_fact_verification_status]
                     sorted by observation id],
  "verified_facts": [[f.id, f.document_id, f.field_name, f.normalized_value, f.unit,
                      f.verification_status, f.corrected_from_fact_id, f.created_at]
                     sorted by fact id],
  "verification_decisions": [[v.id, v.fact_id, v.verified_by_user_id, v.verified_at,
                              v.status, v.created_at] sorted by decision id],
  "comparisons_90d": [[current_id, baseline_id, measure_type, unit, comparable,
                       exact decimal delta or null, incomparable_reason, trust_basis]
                      in evaluator order],
  "active_fact_verification_statuses": [stored statuses in canonical order]
}
```

Deliberate exclusions, each justified:

- **Document bytes** are not embedded; their recomputed SHA-256 digests are (`source_byte_digests`), which is what actually proves byte identity.
- **Free-text `note` / document text** is excluded from the RB3 payload. It is not rule-relevant (the frozen evaluator never reads it), and it is already covered by the F1 fingerprint, which serializes `obs.note` (`p5_run_gate.py:560`). Excluding it keeps clinical prose and document text out of every RB3-persisted artifact while losing no detection capability: a note change alters the F1 digest, which T3/T16 compare against the persisted PROCEED row.
- **RB3-generated surrogate ids and `created_at` values** are excluded (they do not exist yet at T9 and are not inputs).

### 5.5 How added, removed or modified eligible history is detected

| Change | Detected by | Mechanism |
|---|---|---|
| New eligible historical row inserted | F1 digest **and** RB3 digest | F1's snapshot lists every patient observation (`:531-562`), so the row changes `gate_input_fingerprint_sha256`; T3 compares it to the persisted PROCEED row → denial. Independently, the new row appears in `history_observations` → RB3 digest changes → T14 conflict |
| Eligible row deleted | F1 digest **and** RB3 digest | Same two mechanisms; a deleted row also breaks the T6 exclusion cross-check if it had been excluded |
| Non-baseline eligible row's `value`, `unit`, `trust_level`, `validation`, `source`, `measured_at` changed | F1 digest **and** RB3 digest | All are serialized in both. **This is the exact case the F2 bridge fingerprint misses**, because F2 serializes projected *current* rows only |
| Non-baseline eligible row's `created_at` changed | F1 digest **and** RB3 digest | F1 serializes `obs.created_at` (`:561`); F2 does **not**. RB3's payload does, so DR-008's `created_at`-ordering evidence is protected |
| Eligibility of a row changed (admissible ↔ excluded) without any column change | RB3 digest (and T6 cross-check) | Eligibility is derived from the pinned clock, policy and admissibility logic; a change in the derived reason set changes `derived_exclusions` and fails the T6 equality cross-check against the cached F2/RB1 sets |
| Lineage proof changed (fact/document id, verification status) | RB3 digest | `lineage_proofs` + `verified_facts` + `verification_decisions` |
| Baseline comparison unchanged but rule output changed | RB3 digest via T14 output comparison | The complete input identity plus the persisted output identity are compared together, so a changed DR-003/006/008 result with an unchanged closest-prior baseline is still detected (§8.2 cases 4–5) |
| Source bytes changed on disk | T3 and T16 re-hash | `_file_sha` semantics inside the locked gate re-check, plus RB3's own re-hash at T16; both compared before COMMIT (race reduced, not eliminated — §3.1) |
| More than 100 patient observations | F1 and the provenance loader | F1 sets `unavailable="too_many_patient_observations"`; the loader raises `400` "Too many scoped observations." Both deny |

### 5.6 Sole authoritative history source — no separate pre-write history pin

**Decision: the fresh locked snapshot reconstructed at T5–T6 is explicitly the sole authoritative history source for the write transaction.** RB3 does **not** create a separate pre-write history pin table, and does not persist a pre-write history snapshot. Reasons: (a) a second persisted history copy would itself need immutability guards, a downgrade-refusal rule and a reconciliation story, enlarging the schema and the exception inventory for no detection gain; (b) the F1 digest already covers stored-row integrity across the whole patient scope; (c) the RB3 digest covers the derived rule-input identity; (d) Phase 1's preview remains available as a cheap drift cross-check. The Phase-1 preview pin is therefore **corroborating**, never authoritative, and its exclusion list is never subtracted (T6, §5.3).

### 5.7 Pre-commit revalidation requirements and filesystem limitation

T16 repeats, immediately before the single COMMIT: the locked F1 re-check (`inspect_current_run_gate_locked`), the stored-PROCEED fingerprint equality, a re-hash of every selected source byte, and a recomputation of the RB3 full-input fingerprint. Any difference → `db.rollback()` and a typed `409 E_VALIDATION`. This mirrors F2's own final re-check (`p5_evidence_bridge.py:330-344`). The filesystem limitation in §3.1 is restated in the module docstring of the proposed RB3 service so no future reader mistakes the re-hash for atomicity.

### 5.8 Would exact correctness require changing accepted F1/F2/RB1 paths?

**No.** Every interface RB3 needs is public (§1.3), and the complete-history gap is closed inside RB3 by fresh reconstruction plus a new fingerprint. The only proposed touch to an accepted path is the **docstring-only** E6 clarification in `backend/app/services/p5_run_gate.py` (§3.4), which changes no logic. Two further changes are explicitly **not** proposed and would each need their own owner exception if the owner later wants them: exporting `COMPARISON_HISTORY_VERSION`/`HISTORY_LOOKBACK_DAYS` from `p5_evidence_bridge` (RB3 does not need them), and exporting `POLICY_CANONICAL_SHA256`/`POLICY_LOOKBACK_DAYS` from `p4_run_bound_preview` (RB3 re-derives and asserts against the DTO instead).

---

## 6. (D) Durable schema design — proposed additive migration `0008_p4_rb3_review_persistence`

`down_revision = "0007_p5_run_gate"` (the verified actual head). Three tables: the two dictionary tables `review_item` (§6.1) and `evidence_link` (§6.2), plus the proposed new completion record `review_evaluation` (§6.3, **C-RB3-03** / **D-RB3-09**). All are additive; no existing table, column, constraint, index or trigger is altered or dropped.

### 6.1 `review_item` (DATA_DICTIONARY §2.9 — exact fidelity, plus length CHECKs)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36` |
| `patient_id` | TEXT(36) | NOT NULL, FK `patient.id` ON DELETE RESTRICT; CHECK `length(patient_id) = 36` |
| `workflow_run_id` | TEXT(36) | **NOT NULL**, FK `workflow_run.id` ON DELETE RESTRICT; CHECK `length(workflow_run_id) = 36` — the genuine persisted run is the parent; no synthetic or placeholder run parent is ever created |
| `rule_id` | TEXT(8) | NOT NULL; CHECK `rule_id IN ('DR-001','DR-003','DR-005','DR-006','DR-008','DR-009')`; CHECK `length(rule_id) = 7`. The dictionary's `^DR-\d{3}$` intent is expressed as the closed IN list plus a length check, because SQLite CHECK expressions have no regex operator; retired ids `DR-002/004/007/010` are structurally rejected |
| `reason_code` | TEXT(64) | NOT NULL; CHECK `length(reason_code) BETWEEN 1 AND 64`; closed IN list of the six rules' actual reason codes emitted by the frozen evaluator (`no_current_measurement`-family, `measurement_stale`, `bp_delta_above_demo_parameter`-family, `verified_source_conflict`, `duplicate_or_out_of_order_evidence`-family, `implausible_value`) — exact literals to be transcribed from RB2's `_flag` call sites in the implementation PR and asserted by tests, not paraphrased here |
| `workflow_hint` | TEXT(24) | NOT NULL; CHECK IN (`data_quality`,`verification_needed`,`change_to_review`) |
| `trust_basis` | TEXT(16) | NOT NULL; CHECK IN (`self_reported`,`doctor_verified`,`mixed`) |
| `message` | TEXT(240) | NOT NULL; CHECK `length(message) BETWEEN 1 AND 240`; stored **verbatim** from the frozen evaluator's neutral template — RB3 writes no new prose and no clinical interpretation |
| `policy_version` | TEXT(24) | NOT NULL; CHECK `policy_version = 'demo-policy-1.1.0'`; CHECK `length(policy_version) <= 24` — immutable policy-version binding |
| `demo_only` | INTEGER | NOT NULL DEFAULT 1; CHECK `demo_only = 1` |
| `dedupe_key` | TEXT(64) | NOT NULL; CHECK `length(dedupe_key) = 64`; UNIQUE with `workflow_run_id` |
| `state` | TEXT(16) | NOT NULL DEFAULT `'open'`; CHECK IN (`open`,`decided`,`superseded`) — **vocabulary reserved**; write permission restricted to `open` by trigger G3 and by the UPDATE/DELETE immutability triggers G1/G2 |
| `display_order` | INTEGER | NOT NULL; CHECK `display_order >= 0`; UNIQUE with `workflow_run_id` — preserves the evaluator's `(hint, rule_id, evidence, dedupe_key)` ordering durably so retrieval cannot silently reorder. **Additive beyond §2.9** → part of **C-RB3-05** |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Indexes: `ux_review_dedupe UNIQUE (workflow_run_id, dedupe_key)`; `ux_review_order UNIQUE (workflow_run_id, display_order)`; `ix_review_patient_state (patient_id, state)`; `ix_review_run (workflow_run_id)`.

**Vocabulary reservation vs write permission (explicit).** The dictionary mandates the three-value `state` vocabulary, so the CHECK keeps all three values. This slice has **no** permission to write `decided` or `superseded`: G3 admits only `state='open'` inserts, and G1/G2 make every row immutable, so no transition is expressible in SQL at all — not merely unimplemented in Python. A future decision-writing slice must obtain its own owner authorization and its own trigger revision; nothing here pre-approves it. The same distinction applies to `evidence_link.owner_type` (§6.2) and `kind`.

### 6.2 `evidence_link` (DATA_DICTIONARY §2.10 — exact fidelity)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36` |
| `owner_type` | TEXT(24) | NOT NULL; CHECK IN (`review_item`,`verification_issue`,`summary_claim`) — vocabulary reserved; only `review_item` writable (G7) |
| `owner_id` | TEXT(36) | NOT NULL; CHECK `length(owner_id) = 36`; must reference an existing `review_item` (G9) |
| `kind` | TEXT(24) | NOT NULL; CHECK IN (`document_span`,`observation`,`checkin_note`) — `checkin_note` reserved, never writable by RB3 (G8) |
| `document_id` | TEXT(36) | NULL; FK `document.id` ON DELETE RESTRICT; required for `document_span` |
| `observation_id` | TEXT(36) | NULL; FK `observation.id` ON DELETE RESTRICT; required for `observation` |
| `page_index` | INTEGER | NULL; CHECK `page_index IS NULL OR page_index >= 0` |
| `char_start` / `char_end` | INTEGER | NULL; CHECK both NULL, or both NOT NULL with `char_start >= 0 AND char_end > char_start` |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Exactly-one-typed-reference CHECK (dictionary §2.10), expressed without subqueries:

```sql
CHECK (
  (kind = 'document_span' AND document_id IS NOT NULL AND observation_id IS NULL)
  OR (kind = 'observation' AND observation_id IS NOT NULL AND document_id IS NULL)
  OR (kind = 'checkin_note' AND document_id IS NULL AND observation_id IS NULL)
)
```

`checkin_note` is structurally unreachable for RB3 (G8) while its vocabulary and its NULL-reference shape are preserved for the future check-in slice.

Index: `ix_evidence_owner (owner_type, owner_id)`.

**No `fact_id` column exists in §2.10**, so RB2's `fact:<id>` evidence keys cannot be stored as a first-class typed link. §7.2 defines the mapping (span-verified `document_span`), and the fact identity is preserved inside the completion record's output identity rather than by inventing a column.

### 6.3 `review_evaluation` — proposed additive immutable completion record (**C-RB3-03**, **D-RB3-09**)

Purpose: prove, durably and atomically with the rows it describes, the complete input identity and complete output identity of the one evaluation that produced a run's persisted review items — including the zero-item case, which leaves no other trace.

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT(36) | PK; CHECK `length(id) = 36` |
| `workflow_run_id` | TEXT(36) | NOT NULL; FK `workflow_run.id` ON DELETE RESTRICT; **UNIQUE** (`ux_review_evaluation_run`) — exactly one immutable completed evaluation per persisted run; CHECK `length(...) = 36` |
| `patient_id` | TEXT(36) | NOT NULL; FK `patient.id` ON DELETE RESTRICT; must equal the run's patient (G14) |
| `doctor_id` | TEXT(36) | NOT NULL; FK `user.id` ON DELETE RESTRICT; must equal the run's doctor (G14) |
| `as_of_utc` | TEXT(20) | NOT NULL; CHECK `as_of_utc = '2026-11-14T12:00:00Z'`; CHECK `length(...) = 20` |
| `policy_version` | TEXT(24) | NOT NULL; CHECK `policy_version = 'demo-policy-1.1.0'`; must equal `workflow_run.policy_version` (G14) |
| `policy_reference_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` — the sealed R3-A LF digest |
| `fingerprint_version` | TEXT(32) | NOT NULL; CHECK `fingerprint_version = 'rb3-full-input-1.0.0'` — makes the identity self-describing |
| `input_fingerprint_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` — the complete RB3 rule-input identity (§5.4) |
| `output_identity_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` — the complete persisted semantic output identity (§8.1) |
| `gate_evaluation_id` | TEXT(36) | NOT NULL; FK `run_gate_evaluation.id` ON DELETE RESTRICT — the stored PROCEED row actually used |
| `gate_input_fingerprint_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` |
| `bridge_input_fingerprint_sha256` | TEXT(64) | NOT NULL; CHECK `length(...) = 64` |
| `f2_contract_version` | TEXT(8) | NOT NULL; CHECK `f2_contract_version = '2.0.0'` (the public `CONTRACT_VERSION`) |
| `gate_version` | TEXT(8) | NOT NULL; CHECK `gate_version = '1.0.0'` (the public `GATE_VERSION`) |
| `rb2_policy_version` | TEXT(24) | NOT NULL; CHECK `rb2_policy_version = 'demo-policy-1.1.0'` — `OfflineRuleResult.policy_version` |
| `item_count` | INTEGER | NOT NULL; CHECK `item_count BETWEEN 0 AND 12` (4 measure types × `max_items_per_type` 3, enforced by the frozen evaluator at `:482-489`); must equal the actual `review_item` row count (G14) |
| `evidence_link_count` | INTEGER | NOT NULL; CHECK `evidence_link_count BETWEEN 0 AND 96` and `evidence_link_count >= item_count` (every flag carries ≥1 typed evidence ref, `_flag:161-162`); must equal the actual `evidence_link` row count (G14) |
| `exclusion_count` | INTEGER | NOT NULL; CHECK `exclusion_count BETWEEN 0 AND 100` — derived + lineage exclusions surfaced, never dropped |
| `audit_event_id` | TEXT(36) | NOT NULL; FK `audit_event.id` ON DELETE RESTRICT — the single corroborating audit row, so it can be re-read and its content validated (§8.4) |
| `lineage_state` | TEXT(32) | NOT NULL; CHECK `lineage_state = 'stored_independently_verified'` — the RB3-side state documented as reserved for RB3 by `schemas/p4_rb2_offline_rules.py:67-69`; never passed to RB2 |
| `demo_only` | INTEGER | NOT NULL DEFAULT 1; CHECK `demo_only = 1` |
| `created_at` | TEXT(20) | NOT NULL; CHECK `length(created_at) = 20` |

Indexes: `ux_review_evaluation_run UNIQUE (workflow_run_id)`; `ix_review_evaluation_patient (patient_id, created_at)`.

Why the existing immutable audit record is **not** sufficient alone (alternatives evaluated, per the review):

- **Option 1 — dedicated additive `review_evaluation` table (recommended).** Proves the original evaluation fingerprint exactly; UNIQUE per run makes "one immutable completed evaluation" structural; covers the zero-item case; atomic with the rows; self-describing via `fingerprint_version`; supports every case in §8.2 without inference. Cost: a third new table, so the dictionary gains an append-only note and the table-set guards (§9.2) gain one more entry.
- **Option 2 — use the existing immutable `audit_event` row as the completion record (rejected).** `derive_audit_key` includes `request_id` (`audit.py:65-74`), so a replay under a different request id derives a **different** key and appends a **second** row: the audit table cannot express "one completion per run". `append_audit_event` returns an existing row **by key alone without comparing any other content** (`:124-128`), so a returned row is not evidence of exact replay. `safe_detail` is whitespace-collapsed and truncated to 500 characters (`:77-87`), which can carry digests but cannot be relied on to carry a complete identity, and `event_type` has no per-run uniqueness. Assuming an opaque audit idempotency key stores the complete evaluation identity would be unsound. Audit is therefore retained as a **corroborating** record referenced by `audit_event_id`, never as the authoritative completion proof.
- **Option 3 — derive completion from `review_item`/`evidence_link` rows alone (rejected).** A zero-item evaluation leaves no rows, so it is indistinguishable from "never evaluated"; "extra rows" and "missing rows" cases have no authoritative expected-output identity to compare against. Structurally insufficient.

### 6.4 Exact trigger inventory — **14 triggers** (authoritative; supersedes all earlier counts)

House patterns used: unconditional immutability triggers `trg_<table>_<op>_immutable` with `RAISE(ABORT, …)` (`0006…:156-162`), and conditional cross-table guards `BEFORE INSERT … FOR EACH ROW WHEN (SELECT …) IS NOT … BEGIN SELECT RAISE(ABORT, '…'); END` (`0003…:267-277`). Cross-table comparisons **must** be triggers: a SQLite CHECK expression cannot reference another table.

| # | Name | Table | Event | Condition | Effect |
|---|---|---|---|---|---|
| G1 | `trg_review_item_update_immutable` | `review_item` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'review_item is immutable in P4-RB3')` |
| G2 | `trg_review_item_delete_immutable` | `review_item` | BEFORE DELETE | unconditional | `RAISE(ABORT,'review_item is immutable in P4-RB3')` |
| G3 | `trg_review_item_insert_open_only` | `review_item` | BEFORE INSERT | `NEW.state <> 'open'` | `RAISE(ABORT,'only open review items may be written in P4-RB3')` |
| G4 | `trg_review_item_run_scope_consistent` | `review_item` | BEFORE INSERT | run row missing, **or** `NEW.patient_id <>` run's `patient_id`, **or** `NEW.policy_version <>` run's `policy_version` | `RAISE(ABORT,'review item must match its run scope')` |
| G5 | `trg_evidence_link_update_immutable` | `evidence_link` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'evidence_link is immutable in P4-RB3')` |
| G6 | `trg_evidence_link_delete_immutable` | `evidence_link` | BEFORE DELETE | unconditional | `RAISE(ABORT,'evidence_link is immutable in P4-RB3')` |
| G7 | `trg_evidence_link_owner_review_item_only` | `evidence_link` | BEFORE INSERT | `NEW.owner_type <> 'review_item'` | `RAISE(ABORT,'only review_item owners are supported in P4-RB3')` |
| G8 | `trg_evidence_link_kind_not_checkin_note` | `evidence_link` | BEFORE INSERT | `NEW.kind = 'checkin_note'` | `RAISE(ABORT,'checkin_note evidence is reserved and never written by P4-RB3')` |
| G9 | `trg_evidence_link_owner_exists` | `evidence_link` | BEFORE INSERT | `(SELECT id FROM review_item WHERE id = NEW.owner_id) IS NULL` | `RAISE(ABORT,'evidence link owner must be an existing review item')` |
| G10 | `trg_evidence_link_reference_same_patient` | `evidence_link` | BEFORE INSERT | referenced `observation`/`document` row missing, **or** its `patient_id` differs from the owner item's `patient_id` | `RAISE(ABORT,'evidence must belong to the review item patient')` |
| G11 | `trg_evidence_link_duplicate_identity` | `evidence_link` | BEFORE INSERT | NULL-safe `EXISTS` match on `(owner_type, owner_id, kind, document_id, observation_id, page_index, char_start, char_end)` using `IS` | `RAISE(ABORT,'duplicate typed evidence identity')` |
| G12 | `trg_review_evaluation_update_immutable` | `review_evaluation` | BEFORE UPDATE | unconditional | `RAISE(ABORT,'review_evaluation is immutable in P4-RB3')` |
| G13 | `trg_review_evaluation_delete_immutable` | `review_evaluation` | BEFORE DELETE | unconditional | `RAISE(ABORT,'review_evaluation is immutable in P4-RB3')` |
| G14 | `trg_review_evaluation_run_scope_consistent` | `review_evaluation` | BEFORE INSERT | run/patient/doctor/policy/`as_of_utc` mismatch against `workflow_run`, **or** the referenced `run_gate_evaluation` is not a stored `proceed` row of that run, **or** `item_count` / `evidence_link_count` differ from the actual row counts for that run | `RAISE(ABORT,'review evaluation must match its run scope and rows')` |

Review-requested INSERT restrictions → guard mapping: `state='open'` → **G3**; real run ownership → NOT NULL FK + **G4**/**G14**; equal run/item patient identity → **G4**; equal run/item policy version → **G4**; observation/document evidence belonging to the same patient → **G10**; existing review-item owner → **G9**; unsupported `verification_issue`/`summary_claim` owners → **G7**; reserved `checkin_note` kind → **G8**; duplicate typed evidence identity → UNIQUE indexes + **G11**.

Consolidation considered and rejected: merging G7 and G8 into one vocabulary guard, or G9 and G10 into one ownership guard, would reduce the count but couple unrelated denials into one message and make each restriction harder to test independently. The 14-trigger inventory is exact and is the only count this design asserts.

### 6.5 Exact index and uniqueness inventory, including SQLite NULL semantics

SQLite treats NULLs as **distinct** in UNIQUE indexes. This repository already relies on that deliberately: `ux_obs_source_fact` is a plain UNIQUE index on the nullable `observation.source_fact_id` (`0003…:263`), which permits many rows with no source fact. Consequently a plain UNIQUE constraint over `evidence_link`'s nullable reference columns would **not** prevent duplicate `document_span` links whose span coordinates are NULL, nor duplicate links differing only by a NULL column.

Two-layer design (fail-closed, both layers structural):

1. **Partial UNIQUE indexes**, using the in-repo `sqlite_where` precedent (`uq_observation_checkin_identity`, declared in the ORM at `models.py:278-287` and in the migration at `0002…:289`, and reflected by name in `check_alembic_smoke.py:513-520`):
   - `ux_evidence_link_observation UNIQUE (owner_id, observation_id) WHERE kind = 'observation'` — all indexed columns are NOT NULL for that kind, so the partial index is fully effective.
   - `ux_evidence_link_span UNIQUE (owner_id, document_id, page_index, char_start, char_end) WHERE kind = 'document_span'` — effective whenever the span coordinates are populated; NULL coordinates remain a gap.
2. **NULL-safe duplicate-identity trigger G11** closes the remaining gap for every kind, comparing with `IS` so NULL equals NULL.

Rejected alternative (**C-RB3-04**): a single UNIQUE **expression** index over `COALESCE(...)` normalizations. It would need `Index(..., text(...))` in the ORM, and `test_migration_matches_the_orm_metadata` (`tests/p2/test_p2_migration.py:314-331`) compares **reflected index names to ORM-declared names** for every table; the repository contains no expression-index precedent (only partial indexes), so its reflection parity is unproven here. Partial indexes plus G11 use only patterns already accepted in this codebase. If the owner prefers the expression index, the implementation PR must first prove name-level reflection parity with a dedicated test.

Also unique: `ux_review_dedupe (workflow_run_id, dedupe_key)` (dictionary-mandated), `ux_review_order (workflow_run_id, display_order)`, `ux_review_evaluation_run (workflow_run_id)`.

### 6.6 SQLite constraint behaviour accuracy (normative notes for the implementation PR)

- **`TEXT(n)` length is not enforced by SQLite.** Every length bound in §6.1–§6.3 is therefore expressed as an explicit `length(...) = n` or `BETWEEN` CHECK, following the accepted `length(source_sha256) = 64` precedent (`0006…:136`). Tests must assert the CHECK, never assume the type declaration enforces anything.
- **CHECK expressions cannot reference other tables.** All cross-table integrity (run scope, patient equality, owner existence, same-patient evidence, stored-PROCEED verification, count agreement) is implemented as BEFORE INSERT triggers (G4, G9, G10, G14), following `0003…:267-277`.
- **No regex in CHECK.** `rule_id`'s `^DR-\d{3}$` intent is expressed as a closed IN list plus `length(rule_id) = 7`.
- **Foreign keys require `PRAGMA foreign_keys = ON`** at connection time; the repository already asserts this (`tests/test_database.py:160` `test_foreign_keys_are_enabled`). RB3's RESTRICT FKs are only meaningful under that pragma, and its tests must run through the same engine factory.
- **Triggers are not covered by ORM metadata.** They exist only in the migration; the parity test compares tables and index **names**, so triggers must be asserted separately by querying `sqlite_master WHERE type='trigger'`, as `check_alembic_smoke.py` already does for the doctor-only trigger (`:498-501`).
- **Batch mode recreates tables on SQLite.** RB3 creates new tables only and alters none, so no batch rebuild is needed and no existing CHECK/index/row can be silently dropped. If any future revision needs an alter, the `0004` rebuild-preservation tests are the model to follow.

### 6.7 ORM / migration parity obligations

`tests/p2/test_p2_migration.py:314-331` asserts `migrated_tables == set(Base.metadata.tables)` and, for every table, `migrated_indexes == declared_indexes` **by name**. Therefore the implementation PR must declare all three tables and every index (including both partial unique indexes, with matching `sqlite_where` text) in `backend/app/db/models.py` **and** create exactly the same names in `0008`. Triggers are migration-only and asserted via `sqlite_master`. Any name mismatch fails an existing accepted test — this is a hard parity obligation, not a style preference.

### 6.8 Referential integrity and deletion restrictions

All RB3 foreign keys are `ON DELETE RESTRICT`, preserving the dictionary's deletion restrictions and the existing `audit_event`/`verification_issue` → `workflow_run` RESTRICT pattern (`0006…:143-152`). `review_item.workflow_run_id` stays **NOT NULL** with a genuine persisted run parent; no placeholder, synthetic or shadow run row is ever created to satisfy it. Deletion of a run, patient, user, document, observation, gate evaluation or audit row that RB3 evidence references is structurally refused. The only removal path in this repository remains the demo reset (whole-database rebuild), which the dictionary already documents for `audit_event`.

---

## 7. (E) Evidence-link mapping for all six rule outputs

### 7.1 RB2 evidence keys → typed persisted links

RB2 emits typed keys `observation:<id>`, `document:<id>`, `fact:<id>` (`_flag:160`, dedupe `:164`). §2.10 offers kinds `document_span`, `observation`, `checkin_note` and reference columns `document_id` (+ span) and `observation_id` only. Mapping:

| RB2 key | Persisted link | Proof required at T13 |
|---|---|---|
| `observation:<id>` | `kind='observation'`, `observation_id=<id>` | Stored `Observation` exists, `patient_id` equals the run's patient (also enforced structurally by G10), and the row is in the freshly reconstructed eligible set or the re-pinned selection |
| `document:<id>` | `kind='document_span'`, `document_id=<id>`, span coordinates when stored provenance resolves them, otherwise NULL coordinates | Stored `Document` exists, same patient, `sha256`/`size_bytes` match the re-hashed bytes, and the document is in the re-pinned selection or is the stored source of an eligible observation |
| `fact:<id>` | `kind='document_span'` on the fact's stored `document_id`, with `page_index`/`char_start`/`char_end` taken **only** from stored extraction provenance | Stored `ExtractedFact` exists, same patient, `verification_status='verified'`, its `document_id` resolves, and its span is resolvable per `EXTRACTION_PROVENANCE.md` §5. If the span is not resolvable, RB3 denies (`409 E_VALIDATION`) — it never invents coordinates and never falls back to a free-text or untyped link |
| `checkin_note` | **never written by RB3** (G8) | Reserved for the future check-in slice; the kind and its NULL-reference shape stay in the schema |

Fixture-declared references are **not** automatically authorized evidence: every key must resolve to a stored row of the same patient under the lock (T13). A reference that resolves only in a fixture, or not at all, denies the whole invocation.

### 7.2 Per-rule mapping

| Rule | RB2 evidence (actual call sites) | Persisted links |
|---|---|---|
| `DR-001` no current measurement | the selected current row(s) for the type | 1 `observation` link (or the type's selected row when present) |
| `DR-003` stale measurement | the newest admissible same-type/same-unit row (selected **or** historical, per the owner clarification) | 1 `observation` link to that actual row |
| `DR-005` delta above demo parameter | current row + baseline row | 2 `observation` links |
| `DR-006` verified source conflict | `document:<first>`, `document:<second>`, `fact:<first>`, `fact:<second>` (`:434-439`) | 2 `document_span` links for the documents + 2 `document_span` links for the facts' spans (4 total), each span-resolved or denied |
| `DR-008` duplicate / out-of-order evidence | the two compared rows | 2 `observation` links |
| `DR-009` implausible value | the current row | 1 `observation` link |

Every link count is within the per-flag typed evidence bound, and `evidence_link_count >= item_count` holds structurally because `_flag` refuses empty evidence (`:161-162`).

### 7.3 `document_span` / `observation` / `checkin_note` semantics

- `document_span` means "this persisted document, at this stored span when provenance provides one". It is the only kind able to carry a `fact:` reference, because §2.10 has no `fact_id` column. NULL span coordinates are permitted by the dictionary and are used only when stored provenance genuinely lacks a span **and** the rule's evidence is the document itself rather than a specific fact; a `fact:` key with no resolvable span denies instead.
- `observation` means "this stored observation row", same patient, proven by G10.
- `checkin_note` is reserved vocabulary for a future patient-check-in evidence slice. RB3 never writes it (G8) and never maps a rule output to it, because none of the six rules emits a check-in note reference.
- No free-text evidence link exists in the schema and none is invented. No verification decision is fabricated: `verified_by_user_id`/`verified_at`/`FactVerification` rows are read as stored, and their identity is captured in the fingerprint (§5.4) rather than re-decided.

### 7.4 DR-006: corrected reachability finding and the owner decision it creates (**C-RB3-02**, **D-RB3-08**)

**Revision 1 claimed run-bound DR-006 is structurally unreachable on an F1-PROCEED run. That claim is withdrawn: it is not proved, and a concrete reachable path exists.**

Verified mechanics: DR-006 requires two rows of the same measure type with **identical** `measured_at`, **different** values, `_independent_fixture_source` true for both (`verified_document` + `doctor_verified` + `lineage_status='fixture_asserted'` + `source_fact_verification_status='verified'` + non-empty document and fact ids), and **distinct** `source_document_id` and `source_fact_id` (`:423-451`). It iterates `combinations(ordered, 2)` over **all eligible rows of that measure type** (`:425`, with `ordered` built from `by_type[measure]` at `:330-331`), not only selected current rows.

F1's VI-006 detection is narrower in three independent ways:

1. Its loop runs over `doc_ids` — the run's **selected** documents only (`p5_run_gate.py:608`, where `doc_ids` comes from `RunSelectedDocument`).
2. It `continue`s, performing no comparison at all, unless the document has exactly one `test_name`, one `report_date` and one verified `value` fact, its alias is in `MAPPING_TABLE`, and the value's unit equals the mapped required unit (`:617-628`).
3. Its comparability test is **same UTC calendar day** at `conflict_tolerance` (`documents/issues.py:243-256`), using `report_date T00:00:00Z` as the candidate stamp — not exact `measured_at` equality, and not observation-versus-observation.

Reachable path: two eligible `doctor_verified` / `verified_document` observations of the same measure type, identical `measured_at`, different values, whose source documents are **both outside** the run's selected set (or whose selected document fails the shape gate at `:622-628`). F1's VI-006 loop never constructs a candidate for them, so PROCEED is possible; DR-006 then compares them because `ordered` includes historical rows. A second, narrower divergence: a pair whose stamps share a calendar day but are not exactly equal is caught by VI-006 when a selected document drives it, while an exactly-equal pair driven only by non-selected documents is not.

What **is** true and remains stated: the currently approved synthetic fixtures do not exercise this path — `GOLD-D.expected.json` records `expected_source_conflicts: 0`. That is a property of the fixtures, **not** a proof of universal unreachability, and Revision 1's inference from it was invalid.

Consequences for the design:

- RB3 must **not** deny DR-006 candidates as `evidence_gate_inconsistency`. Revision 1's fail-closed denial on any DR-006 candidate is **withdrawn**: it rested on the false invariant and would suppress a genuine stored-evidence safety signal exactly when review is most needed.
- Under Alt A2 (§4.3) DR-006 is live, because stored-proved rows carry the `fixture_asserted` transport label that `_independent_fixture_source` requires. Persisted DR-006 items must carry their four span-resolved `document_span` links, the evaluator's own `provenance_status='fixture_asserted'`, and no trust promotion; the item must never be presented as an authenticated doctor attestation.
- Because this is the one rule whose activation depends on a contested label, **D-RB3-08** asks the owner to choose explicitly: **(i) persist DR-006 normally** (recommended — it is real stored-evidence evidence of two verified sources disagreeing, and suppressing it weakens review), or **(ii) retain a conservative prohibition**, in which case T12 denies the **entire invocation** fail-closed with reason `dr006_persistence_not_authorized` — never a partial persist, never a silently dropped item. Option (ii) is a deliberate reduction of persisted output and must be recorded as such.
- Under Alt B (§4.3) DR-006 would be inert by construction, because RB3's honest `stored_independently_verified` state is not the literal `fixture_asserted` that `_independent_fixture_source` tests. That inertness would have to be disclosed in the receipt and the implementation review, and it is a material argument for option (i) under Alt A2 rather than Alt B.

---

## 8. (F) Idempotency, replay and atomicity — invocation level

### 8.1 Identities

- **Dedupe key (unchanged, per-row).** `sha256("|".join((patient_id, rule_id, *sorted_refs, trust_basis)))` computed by the frozen evaluator (`:164`), with `_valid_id` refusing `|` and control characters so the serialization stays unambiguous (`:176-188`). Persisted with `UNIQUE (workflow_run_id, dedupe_key)`.
- **Complete input identity (new).** `review_evaluation.input_fingerprint_sha256` (§5.4) — the whole rule-input set, including complete eligible history, `created_at` values, units, exact decimal values, trust, source identity, lineage proofs, verification decisions, derived exclusions, comparisons, policy identity, contract versions, run identity and re-hashed source-byte digests.
- **Complete output identity (new).** `review_evaluation.output_identity_sha256` = the same canonical JSON+SHA-256 discipline over the persisted **semantic** output: for each item, in evaluator order, `(rule_id, reason_code, workflow_hint, trust_basis, message, policy_version, dedupe_key, display_order, state)` together with its ordered evidence-link tuples `(kind, document_id, observation_id, page_index, char_start, char_end)`; plus `item_count`, `evidence_link_count` and the sorted derived-exclusion list `(observation_id, reason)`.
  **Deliberately excluded:** `review_item.id`, `evidence_link.id`, `review_evaluation.id` and every `created_at`. These are per-invocation surrogate values; including them would make an exact semantic replay compare unequal. Their exclusion cannot mask a content difference, because every semantic field the evaluator emitted is included. This is the precise sense in which "retry equivalence means identical semantic output and evidence identity; newly generated UUIDs need not match an earlier rolled-back attempt".

### 8.2 All thirteen replay cases (each fail-closed on ambiguity, `409 E_IDEMPOTENCY_CONFLICT`)

| # | Case | Behaviour |
|---|---|---|
| 1 | **Exact same-run replay** (complete input identity equal, recomputed semantic output identity equal, persisted item/link set re-derived from the rows equal) | **Zero writes of any kind** — no item, link, completion row or audit row. Receipt: `replayed=True`, `evaluation_completed=True`, `review_items_persisted=0`, `review_items_total=item_count`, identities echoed from the stored completion record. The transaction ends in rollback-with-nothing-pending or a no-op commit; neither appends |
| 2 | **Existing extra review items** not in the recomputed set | `409 E_IDEMPOTENCY_CONFLICT`, reason `extra_persisted_items`; zero writes; no DELETE, no supersession |
| 3 | **Missing previously persisted items or evidence links** | `409 E_IDEMPOTENCY_CONFLICT`, reason `missing_persisted_evidence`; zero writes; no repair, no append-to-old-result |
| 4 | **Changed complete-history fingerprint with unchanged candidate dedupe keys** | `409 E_IDEMPOTENCY_CONFLICT`, reason `input_identity_changed`. Per-row dedupe equality is explicitly **not** sufficient; the complete input identity governs. This is the RB3-D01 case |
| 5 | **Changed candidate set with unchanged F1 fingerprint** | `409 E_IDEMPOTENCY_CONFLICT`, reason `output_identity_changed` — detected by comparing the recomputed semantic output identity with the stored one, independently of the F1 digest |
| 6 | **Original zero-item evaluation** | Insert the completion row with `item_count=0`, `evidence_link_count=0`, `exclusion_count=<derived>`, plus the single audit row; commit. Receipt: `evaluation_completed=True`, `review_items_persisted=0`, `review_items_total=0`, `replayed=False` — a durable completed evaluation with no items, structurally distinguishable from "never evaluated" |
| 7 | **Repeated zero-item evaluation** | Case 1 semantics: exact replay, zero writes, `replayed=True`, `review_items_total=0` |
| 8 | **Zero-item evaluation followed by new nonempty output** | `409 E_IDEMPOTENCY_CONFLICT`, reason `output_identity_changed`; zero writes. No UPDATE of the completion row, no second completion row (UNIQUE per run), no append-to-old-result |
| 9 | **Nonempty evaluation followed by zero output** | `409 E_IDEMPOTENCY_CONFLICT`, reason `output_identity_changed`; zero writes |
| 10 | **Existing audit row without a matching item/link set** | `409 E_IDEMPOTENCY_CONFLICT`, reason `audit_business_inconsistent`. RB3 re-reads the audit row via `review_evaluation.audit_event_id` and validates its `event_type`, `actor_type`, `actor_id`, `workflow_run_id`, `outcome` and that its `safe_detail` carries the recorded input/output identities and counts; any inconsistency denies |
| 11 | **Existing item/link set without the required completion evidence** | `409 E_IDEMPOTENCY_CONFLICT`, reason `completion_evidence_missing`. Rows whose originating evaluation cannot be proved are never adopted, extended or repaired |
| 12 | **Concurrent invocation** | The second writer blocks on `BEGIN IMMEDIATE`; after acquiring, it resolves through T14 as case 1 (exact) or cases 4/5/8/9 (conflict). `ux_review_evaluation_run` is the structural backstop: a racing insert raises `IntegrityError` → rollback → `409 E_IDEMPOTENCY_CONFLICT`, never a partial write |
| 13 | **Rollback and retry** | A rolled-back attempt persisted nothing; the retry is a first evaluation (case 6 or a normal first persist). Equivalence is semantic (§8.1); newly generated UUIDs need not match the abandoned attempt |

Prohibited in every case: silent repair, append-to-old-result, duplicate audit rows, `UPDATE`, `DELETE`, supersession, and any second committed write path. Uniqueness conflicts on `ux_review_dedupe`, `ux_review_order`, `ux_review_evaluation_run`, `ux_evidence_link_observation` or `ux_evidence_link_span` are caught as `IntegrityError`, rolled back, and reported as typed conflicts — never retried blindly.

### 8.3 Receipt semantics (`ReviewPersistenceReceiptV1`, proposed)

`contract_version='p4-rb3-receipt-1.0.0'`; `run_id`, `patient_id`, `doctor_id`; `as_of_utc`, `policy_version`, `policy_reference_sha256`; `gate_evaluation_id`, `gate_version`, `gate_input_fingerprint_sha256`, `bridge_input_fingerprint_sha256`; `rb3_fingerprint_version`, `input_fingerprint_sha256`, `output_identity_sha256`; `evaluation_id`; `audit_event_id`; and the honesty fields:

- `evaluation_completed: Literal[True]` — a durable completed evaluation exists for this run.
- `replayed: bool` — `True` only for case 1/7 (zero-write exact replay).
- `review_items_persisted: int` — rows written **by this invocation** (`0` on replay).
- `review_items_total: int` — rows that exist for the run (`== item_count`).
- `evidence_links_persisted: int`, `evidence_links_total: int` — same distinction.
- `excluded_evidence: tuple[(observation_id, reason), ...]` — every derived, lineage and R03 `missing_created_at` exclusion surfaced; never silently dropped.
- `dr006_policy: Literal['persisted','prohibited_denied']` — which side of **D-RB3-08** applied.
- `offline_evaluator_invoked: Literal[True]`, `runtime_evaluable: Literal[False]`, `policy_status: Literal['unapproved']`, `demo_only: Literal[True]`, `not_for_clinical_use: Literal[True]`.

**Zero-item receipts must clearly distinguish a completed durable evaluation from review-item rows being persisted:** `evaluation_completed=True` with `review_items_persisted=0` and `review_items_total=0` means "the evaluation ran, was proved and was recorded, and it produced no items" — not "nothing happened" and not "the evaluator was skipped". RB3 uses its **own** field names for these facts and never reinterprets RB2's frozen result literals (`review_items_persisted=False` on `OfflineRuleResult` stays exactly that: a statement about the offline evaluator, not about RB3's write).

### 8.4 Audit identity and verification (**RB3-D05**)

One audit row per **first** completed evaluation, written inside the same transaction by the existing public helper:

```python
append_audit_event(
    db,
    event_type="workflow.review.persisted",       # additive; event_type has no CHECK (models.py; DD §2.17)
    actor_type=ActorType.USER,                    # a doctor is a Role, not an ActorType
    actor_id=principal.user_id,
    outcome=AuditOutcome.OK,
    request_id=request_id,                        # server-owned request identity
    now=validation_clock,
    patient_id=run.patient_id,
    workflow_run_id=run.id,
    subject_type="review_evaluation",
    subject_id=evaluation_id,
    detail_fragments=(
        "fingerprint_version=rb3-full-input-1.0.0",
        f"input={input_fingerprint_sha256}",
        f"output={output_identity_sha256}",
        f"gate={gate_input_fingerprint_sha256}",
        f"bridge={bridge_input_fingerprint_sha256}",
        f"policy={policy_version}",
        f"items={item_count}",
        f"links={evidence_link_count}",
        f"exclusions={exclusion_count}",
        "demo_only=1",
    ),
)
```

`safe_detail()` whitespace-collapses and truncates to `SAFE_DETAIL_MAX = 500`; the fragments above are literals, enum values, hex digests and small integers, and fit inside the bound. The implementation PR must assert the composed length in a test rather than rely on truncation, because silent truncation would weaken the corroboration. **No clinical prose, document text, credential, token or free-text note** appears in any fragment (`REQ-AUDIT-02`).

`ActorType.USER` is used because `ActorType = {user, system, demo_admin}` has no doctor member; doctor is a `Role`. `AuditOutcome.OK` is used for a completed evaluation. No denial audit is committed in this slice (§2.3), so `DENIED`/`ERROR` are not used by RB3.

**Why an existing audit row is not automatically proof of exact replay, and what RB3 does instead.** `append_audit_event` looks a row up **by `idempotency_key` alone and returns it without comparing any other content** (`audit.py:124-128`), and `derive_audit_key` includes `request_id` (`:65-74`), so the key is request-scoped rather than evaluation-scoped. RB3 therefore (a) never treats a returned existing row as replay proof, (b) stores `audit_event_id` on the completion record, (c) on any later invocation re-reads that row by id and **explicitly validates** its `event_type`, `actor_type`, `actor_id`, `patient_id`, `workflow_run_id`, `subject_type`, `subject_id`, `outcome` and that its `safe_detail` still carries the recorded input/output identities and counts (case 10), and (d) performs **zero writes** on exact replay so no duplicate audit row can be appended. The authoritative completion proof is `review_evaluation`; the audit row corroborates it.

Audit/business-row consistency is structural as well as procedural: G14 requires `item_count` and `evidence_link_count` to equal the actual row counts for the run at insert time, `ux_review_evaluation_run` forbids a second completion row, and G12/G13 make the completion row immutable — so the audit row, the completion row and the business rows are written together or not at all.

---

## 9. (G) Migration safety

### 9.1 Actual current head and the proposed additive migration

Verified actual head: `0007_p5_run_gate` (`backend/migrations/versions/0007_p5_run_gate.py:15`, `down_revision = "0006_p5_run_foundation"` `:16`), corroborated by the pinned constants `HEAD_REVISION = "0007_p5_run_gate"` in `backend/tests/test_database.py:22`, `backend/tests/p2/test_p2_migration.py:46` and `scripts/python/check_alembic_smoke.py:70`.

Proposed (not implemented): `0008_p4_rb3_review_persistence`, `revision = "0008_p4_rb3_review_persistence"`, `down_revision = "0007_p5_run_gate"`. Upgrade creates `review_item`, `evidence_link`, `review_evaluation`, their indexes (including both partial unique indexes) and the 14 triggers of §6.4, in FK-safe order (`review_item` before `evidence_link` before `review_evaluation`, since G9/G14 read the earlier tables). No existing table, column, constraint, index or trigger is altered, rebuilt or dropped, so no batch-mode rebuild and no risk of silently losing an accepted CHECK, index or row.

**Upgrade on nonempty databases:** purely additive DDL; existing rows in `patient`, `user`, `document`, `observation`, `extracted_fact`, `fact_verification`, `verification_issue`, `workflow_run`, the three manifest tables, `run_gate_evaluation`, `run_gate_blocker` and `audit_event` are untouched and remain valid. New FKs point at existing parents only, and no new column is added to an existing table, so no backfill is required or possible.

**Downgrade:** refuses when any RB3 persistence object holds data, following the accepted `0006` pattern (`_persisted_run_evidence()` + `RuntimeError(DOWNGRADE_REFUSED_MESSAGE)`, `:165-184`). The refusal predicate covers **every** newly introduced object:

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
    # triggers first, then indexes (index-before-column/drop ordering per 0003:281-283), then tables
    # in reverse dependency order: review_evaluation, evidence_link, review_item
```

`DOWNGRADE_REFUSED_MESSAGE` follows the `0006` wording shape and names revision `0008_p4_rb3_review_persistence`. Downgrade on an empty database drops all 14 triggers, all RB3 indexes and all three tables, restoring the exact `0007` schema — so the accepted empty-database reversibility tests (`tests/test_database.py:110` `test_migration_is_reversible`; `tests/p2/test_p2_migration.py:224`, `:251`) continue to pass **unchanged**, because the refusal predicate is false on an empty database. This is a deliberate, verified narrowing of the E1/E2 deltas.

**Legacy historical migration states:** the staged expectations in `check_alembic_smoke.py` (`_expected_tables(state)` `:199-211`, `_expected_revisions(state)` `:214-220`) pin earlier states (`p1`, `p2`, `p3`, `p3_recovery`, `p3_stage1`, `p5_f0`) to their historical table sets and revisions. RB3 adds a new pinned historical state for `0007` (proposed key `p5_f1`, tables `… | P5_F0_TABLES | P5_F1_TABLES`, revision `0007_p5_run_gate`) so that the pre-RB3 schema stays asserted after `head` advances, and extends only the `head` state. No historical state's expected table set or revision is rewritten.

### 9.2 Existing guards a new head provably trips (exact paths, minimal deltas, none weakened/skipped/replaced, none modified in this design PR)

| ID | Path | Exact assertion that trips | Minimal future delta (each needs its own fresh owner marker) |
|---|---|---|---|
| **E1** | `backend/tests/test_database.py` | `HEAD_REVISION = "0007_p5_run_gate"` (`:22`, asserted `:85`); `FUTURE_TABLES` contains `review_item` (`:59-65`) with `assert tables.isdisjoint(FUTURE_TABLES)` (`:99`); exact table-set equality `tables == {schema_meta, alembic_version} | P2 | P3 | P5_F0 | P5_F1` (`:88-97`) | Advance `HEAD_REVISION` to `0008…`; remove **only** `review_item` from `FUTURE_TABLES` (keeping `summary_draft`, `approval_decision`, `follow_up_task`, `in_app_notification` forbidden); add a `P4_RB3_TABLES = {"review_item","evidence_link","review_evaluation"}` term to the exact-equality set. `test_migration_is_reversible` (`:110`) needs **no** change (empty-database downgrade is permitted) |
| **E2** | `backend/tests/p2/test_p2_migration.py` | `HEAD_REVISION = "0007_p5_run_gate"` (`:46`, asserted `:241`, `:263`); `test_migration_matches_the_orm_metadata` (`:314-331`) compares migrated tables **and index names** to `Base.metadata` | Advance `HEAD_REVISION`; ensure ORM/migration parity per §6.7 (no assertion weakened — the parity test is kept exactly as accepted and must pass with the new tables and both partial indexes) |
| **E3** | `backend/tests/p2/test_p2_scope_guards.py` | `P4_PLUS_TABLES = {review_item, evidence_link, summary_draft, summary_claim, approval_decision, follow_up_task, in_app_notification, node_event}` (`:62-71`) with `assert tables.isdisjoint(P4_PLUS_TABLES)` (`:123`), plus its own exact table-set assertion | Remove **only** `review_item` and `evidence_link` from the disjointness set, **add** `review_evaluation` to it (so the new object stays forbidden below `0008`), and extend the exact head table set with `P4_RB3_TABLES`. All other later-phase tables stay forbidden |
| **E4** | `scripts/python/check_alembic_smoke.py` | `HEAD_REVISION` (`:70`); `_expected_tables("head")` (`:199-201`); `_expected_revisions("head")` → `[HEAD_REVISION]` (`:217`); the early-table gate `early = P4_PLUS_TABLES & tables` → "later-phase tables must not exist" (`:131`, `:336-338`); F1-stage index/trigger expectations (`:434+`) | Advance `HEAD_REVISION`; add `P4_RB3_TABLES` to the `head` expectation only; add `review_evaluation` to `P4_PLUS_TABLES`; add a pinned historical `p5_f1` state for `0007`; add RB3-stage expectations (three tables, the named indexes including both partial unique indexes, and all 14 trigger names via `sqlite_master`). No existing stage expectation is relaxed |
| **E5** | `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (+ its enforcer `backend/tests/p3/test_windows_ocr_acceptance.py`) | The literal collection pairing `**1255 collected**, of which **443** are the P3 suite` is enforced by an existing test; any new backend test file changes the collected total and fails that guard | An **append-only** note recording the **actual future measured** backend/P3 pairing after the RB3 test files exist, authorized by a **fresh standalone collection-only marker** (proposed form `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`, following the RB1/RB2 precedents `APPROVE-P4-RB1-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION`, `APPROVE-P4-RB2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION`, `APPROVE-P4-RB2-P3-HANDOFF-1255-COLLECTION-ONLY`). The measured numbers must be the real future ones; this is **not** requested as a reusable generic permission, and the historical 1255/443 evidence is preserved untouched |
| **E6** | `backend/app/services/p5_run_gate.py` | `inspect_current_run_gate_locked` docstring: "Only the F2 bridge may call this…" (`:862-868`) contradicts the approved RB3 usage | **Conditional, docstring-only** clarification naming RB3 as an additional locked-read caller; zero logic/signature/behaviour change (**D-RB3-02b**). Fallback if refused: leave the source untouched and record the deviation in an append-only `TOOL_CONTRACTS.md` note |

Guards verified **not** tripped: `.github/workflows/ci.yml` and `backend/tests/test_ci_workflow.py` (no gate order or command change); `scripts/python/check_openapi.py` (no router, path, operation or schema change — RB3 exposes no HTTP surface); `scripts/python/scan_repository.py` (no new claim pattern, secret or artefact); the P2 API tests that hard-code `review_items=[]` (RB3 adds no endpoint); RB1/RB2 sources, schemas and tests (frozen); `data/synthetic/policy/demo_review_policy.yaml` and the GOLD JSON fixtures (untouched); `backend/tests/p4/*` (extended only by new files, never edited).

Required legacy compatibility changes: none beyond E1–E6. No historical migration is rewritten, no accepted assertion is weakened, and no check is skipped or replaced.

---

## 10. Exact future RB3 implementation allowlist (proposal — nothing here is authorized yet)

### 10.1 Normal proposed RB3 paths

| ID | Path | Why required | Authorizing contract | Prohibited from changing |
|---|---|---|---|---|
| N1 | `backend/app/services/p4_rb3_review_persistence.py` (new) | The internal service boundary, transaction sequence T1–T16, fresh history reconstruction, full-input fingerprint, replay resolution | `TOOL_CONTRACTS.md` F2/RB1/RB2 boundary sections; `STATE_AND_GRAPH_CONTRACT.md` §7 idempotency/finalize; `AGENTS.md` §3 provenance/idempotency/clock invariants | Must not add an HTTP router, agent tool, graph node, task or notification; must not import private helpers; must not call `evaluate_run_verification_gate` or `record_denial`; must not weaken the pinned clock/policy |
| N2 | `backend/app/schemas/p4_rb3_review_persistence.py` (new) | `ReviewPersistenceReceiptV1` and its typed denial reasons | `DATA_DICTIONARY.md` §§2.9–2.10; `TOOL_CONTRACTS.md` | Must not reinterpret RB2's frozen result literals; must not expose a clearance/authority field |
| N3 | `backend/app/db/models.py` (additive ORM only) | Declare `ReviewItem`, `EvidenceLink`, `ReviewEvaluation` and every index, for ORM/migration parity | `DATA_DICTIONARY.md` §§2.9–2.10 (+ the proposed §2.10a note for `review_evaluation`) | Additive only: no change to any existing model, column, constraint, relationship or index |
| N4 | `backend/migrations/versions/0008_p4_rb3_review_persistence.py` (new) | Create the three tables, indexes and 14 triggers; refuse destructive downgrade | `DATA_DICTIONARY.md` §5.1 retention/downgrade refusal; the `0006` precedent | Must not alter or drop any existing object; must not rewrite a historical migration; must not relax the refusal predicate |
| N5 | `backend/tests/p4/test_p4_rb3_review_persistence.py` (new) | The §11 matrix: authority, transactions, fingerprint, replay, schema guards | `AGENTS.md` §4 (no fabricated verification) | Must not edit an existing test, fixture or golden file |
| N6 | `backend/tests/p4/test_p4_rb3_migration_guards.py` (new) | Migration/trigger/parity/downgrade-refusal adversarial cases | `DATA_DICTIONARY.md` §5.1 | Same |
| N7 | `docs/contracts/DATA_DICTIONARY.md` (append-only note) | Record the RB3 realization of §§2.9–2.10, the additive `display_order` column (**C-RB3-05**) and the proposed §2.10a `review_evaluation` | `DATA_DICTIONARY.md` | Append-only; no existing row, type or constraint rewritten |
| N8 | `docs/contracts/TOOL_CONTRACTS.md` (append-only note) | Record the RB3 service boundary, the transport-label semantics of `lineage_status='fixture_asserted'` (**C-RB3-01**), the DR-006 decision (**C-RB3-02**) and, if E6 is refused, the docstring deviation | `TOOL_CONTRACTS.md:270`, `:279` | Append-only |
| N9 | `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (append-only note) | Record the RB3 full-input/output identities and invocation-level replay semantics alongside §7 | `STATE_AND_GRAPH_CONTRACT.md` §7 | Append-only |
| N10 | `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_<date>.md` (new) | The future implementation review with real commands, exit codes and CI evidence | `AGENTS.md` §4 | Must not claim an unexecuted check |
| N11 | `docs/phase-reports/PHASE_4_REPORT.md` (append-only) | Phase checkpoint | `AGENTS.md` §1 | Append-only; historical evidence preserved |
| N12 | `docs/roadmap/PHASE_PROGRESS.md` (append-only) | Owner-decision and execution checkpoint | `AGENTS.md` §1 | Append-only; the literal P3-handoff phrase elsewhere stays untouched |
| N13 | `docs/clinical-safety/DEMO_REVIEW_RULES.md` (append-only note, **only if** D-RB3-08 option (ii) is ratified) | Record the conservative DR-006 prohibition and its whole-invocation fail-closed behaviour | `DEMO_REVIEW_RULES.md` §10 | Append-only; no rule definition, message template or parameter altered |

No blanket directory authorization is granted or requested: each path is listed individually with its justification. Module naming avoids every name forbidden by `backend/tests/p2/test_p2_scope_guards.py` (`reviews.py`, `review_rules.py`, `comparisons.py`, `summary.py`, `workflows.py`, `tasks.py`, `orchestrator.py`, `notifications.py`) and creates no `app/agents` or `app/llm` package.

### 10.2 Exceptional cross-phase paths (each requires its own explicit owner authorization recorded in the roadmap **before** any edit)

E1 `backend/tests/test_database.py` · E2 `backend/tests/p2/test_p2_migration.py` · E3 `backend/tests/p2/test_p2_scope_guards.py` · E4 `scripts/python/check_alembic_smoke.py` · E5 `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (with `backend/tests/p3/test_windows_ocr_acceptance.py` as its enforcer, itself unchanged) · E6 `backend/app/services/p5_run_gate.py` (conditional, docstring-only). Deltas are exactly those in §9.2 — no broader edit is proposed, and E1–E4/E6 remain subject to separate explicit owner authorization before any edit. E5's authorization must state the **actual future measured** backend/P3 pairing and must not be requested as a reusable generic permission.

---

## 11. Acceptance test matrix for the future RB3 implementation PR (requirements — none executed by this design)

RB3-01..RB3-44 are carried forward from Revision 1 with the corrections noted; RB3-45..RB3-66 are new, driven by RB3-D01…RB3-D06. Every case states its expected outcome and failure code. **None has been executed.**

| ID | Requirement case | Expected outcome / failure code |
|---|---|---|
| RB3-01 | Happy path: synthetic assigned-doctor run, stored PROCEED, pinned clock/policy, fresh evidence | Items + links + completion row + one audit row committed; receipt `evaluation_completed=True`, `replayed=False`, `review_items_persisted=item_count` |
| RB3-02 | Missing F1 gate row | `409 E_VALIDATION` "A matching stored F1 PROCEED is required."; zero writes |
| RB3-03 | Stale F1 gate (fingerprint differs from stored PROCEED) | `409 E_VALIDATION`; zero writes |
| RB3-04 | F1 decision HALT | Locked gate re-check raises `409 E_VALIDATION` "Current F1 gate is not eligible."; zero writes |
| RB3-05 | F1 decision UNAVAILABLE (any `unavailable_reason`) | `409 E_VALIDATION`; zero writes |
| RB3-06 | `BEGIN IMMEDIATE` raises `OperationalError` | `503 E_VALIDATION` "Verification database is unavailable."; never a success receipt |
| RB3-07 | Foreign patient / run / document / observation / fact reference | `403 E_SCOPE_VIOLATION`; zero writes |
| RB3-08 | Revoked session | `403 E_FORBIDDEN` |
| RB3-09 | Expired session, or session `created_at` after the injected clock | `403 E_FORBIDDEN` |
| RB3-10 | **Session owned by a different user** (`session.user_id != principal.user_id`) | `403 E_FORBIDDEN` (explicit ownership check, §2.2 item 4) |
| RB3-11 | Patient reassigned to another doctor | `403 E_SCOPE_VIOLATION` |
| RB3-12 | Non-synthetic patient (`data_source != 'synthetic_fixture'`) | `403 E_FORBIDDEN` |
| RB3-13 | Run not `queued`, or execution-state columns non-NULL | `409 E_VALIDATION` |
| RB3-14 | Run version fields differ from the pinned constants | `409 E_VALIDATION` (`unsupported_run_version` semantics) |
| RB3-15 | Tampered source bytes on disk | `409 E_VALIDATION` via the locked re-hash at T3 and again at T16 |
| RB3-16 | Tampered verification decision (`FactVerification` status/actor/timestamp changed) | `409 E_VALIDATION`; the change also alters the full-input fingerprint |
| RB3-17 | Policy tampering (pinned policy digest mismatch) | `409 E_VALIDATION` "The fixed synthetic comparison reference was altered." |
| RB3-18 | Clock mismatch (`validation_clock != run.as_of_utc`, or run clock not the pinned instant) | `409 E_VALIDATION` |
| RB3-19 | Zero selected current observations | Persisted evaluation with `item_count=0` where the evaluator emits none; receipt distinguishes completion from row persistence; `no_current_reason` preserved |
| RB3-20 | Input caps: >6 selected current, >100 history, >40 facts, >5 or <1 documents | Fail closed (`409 E_VALIDATION` RB3-side; RB2 typed error mapped per §4.4); zero writes |
| RB3-21 | Typed exclusions surfaced (`validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp`, `verified_lineage_unavailable`) | Present in `receipt.excluded_evidence`; never dropped; never fabricated |
| RB3-22 | No trust promotion (`self_reported_validated` never becomes `doctor_verified`) | `trust_basis` exactly as emitted; denial if a promotion would be required |
| RB3-23 | Duplicate replay (case 1) | Zero writes; `replayed=True`; no second audit row |
| RB3-24 | Concurrent invocation (case 12) | One writer persists; the other resolves as replay or `409 E_IDEMPOTENCY_CONFLICT`; `ux_review_evaluation_run` backstop exercised; no partial write |
| RB3-25 | Partial write failure (link insert raises) then rollback | Nothing persisted: no item, link, completion or audit row survives |
| RB3-26 | Unique-constraint conflict on `ux_review_dedupe` | `IntegrityError` → rollback → `409 E_IDEMPOTENCY_CONFLICT` |
| RB3-27 | Evidence-link integrity: unresolvable span for a `fact:` key | `409 E_VALIDATION`; no invented coordinates |
| RB3-28 | Evidence-link integrity: link to another patient's observation/document | Structural refusal by G10; `409 E_SCOPE_VIOLATION` at T13 |
| RB3-29 | Migration from the genuine existing head `0007` on a populated database | `0008` upgrade succeeds; all pre-existing rows intact; `alembic_version == 0008…` |
| RB3-30 | Nonempty-data downgrade safeguard | `RuntimeError(DOWNGRADE_REFUSED_MESSAGE)`; schema and rows unchanged |
| RB3-31 | Empty-database downgrade/upgrade round trip | Succeeds; exact `0007` schema restored; accepted reversibility tests still pass |
| RB3-32 | Historical P3 issues preserved (P3 collections and the pinned pairing) | Unchanged except by an E5-authorized append-only note with real measured numbers |
| RB3-33..RB3-40 | R01–R08 regression protection, one case each, with the **corrected** expectations: R03 expects a `missing_created_at` exclusion preserving proven duplicates (not a hard denial); R04 expects DR-003 staleness from the newest admissible same-unit row across selected **and** historical inputs; R07 expects a year-one timestamp to be handled without overflow (not a crash, not a typed arithmetic denial); R08 expects `121.1 - 100` to persist a DR-005 item with the exact decimal delta (not `E_VALIDATION`) | Frozen evaluator behaviour preserved end-to-end through persistence |
| RB3-41 | No graph/LLM/API/task/notification activation | No router, node, agent, task or notification object exists; scope-guard and OpenAPI checks unchanged |
| RB3-42 | No caller-supplied authority accepted (clearance flag, fact count, evidence ids, policy override, cached V2/RB1/RB2 object) | Structurally impossible: no such parameter exists; a test asserts the signature |
| RB3-43 | RB2 source/schema/tests frozen | Zero diffs asserted |
| RB3-44 | RB3↔RB2 output equivalence on identical inputs | Persisted items equal the evaluator's flags exactly (order, message, trust, dedupe key) |
| **RB3-45** | **Newly added eligible historical row after the Phase-1 pin, before T16** | `409 E_VALIDATION` at T3/T16 (F1 digest changed) or `409 E_IDEMPOTENCY_CONFLICT` on a later invocation; never persisted |
| **RB3-46** | **Changed non-baseline historical value with the closest-prior baseline comparison unchanged** | Detected: F1 digest **and** RB3 full-input digest change; `409` denial. Asserts explicitly that F2 bridge-fingerprint equality would **not** have caught it |
| **RB3-47** | **Changed historical `created_at` only** | Detected via F1 digest and RB3 digest (`created_at` serialized); DR-008 ordering evidence protected |
| **RB3-48** | **Changed eligibility of a historical row with no column change** (derived exclusion set differs) | `409 E_VALIDATION` "Historical exclusion evidence changed." at T6 |
| **RB3-49** | **Unchanged baseline comparison but changed rule output** | `409 E_IDEMPOTENCY_CONFLICT` reason `output_identity_changed` (case 5) |
| **RB3-50** | **Cached exclusion ids offered as authority** (F2/RB1 exclusion set differs from the freshly derived set) | Fresh derivation governs; inequality denies; a test asserts RB3 never subtracts cached ids |
| **RB3-51** | **Full-input fingerprint stability**: same stored state, two invocations, different loader orderings | Identical `input_fingerprint_sha256` (canonical id-ascending order, exact decimals, `format_utc` timestamps) |
| **RB3-52** | **Fingerprint excludes free text**: a changed `Observation.note` with nothing else changed | RB3 digest unchanged; F1 digest changed → denial still occurs; asserts no clinical prose or document text enters any RB3-persisted artifact |
| **RB3-53** | **Invalid `preview.gate_version`-style access**: a test asserts the receipt/completion record sources every version field per §2.4 | No attribute error; no reliance on a nonexistent preview field |
| **RB3-54** | **All 14 triggers exist and fire**, one case each (G1–G14), asserted via `sqlite_master` and direct SQL attempts bypassing the ORM | Each raises the documented `RAISE(ABORT, …)` message; no UPDATE/DELETE succeeds on any RB3 table |
| **RB3-55** | **State/owner/kind vocabulary reserved but not writable**: direct SQL inserts of `state='decided'`, `state='superseded'`, `owner_type='verification_issue'`, `owner_type='summary_claim'`, `kind='checkin_note'` | Refused by G3/G7/G8 while the CHECK vocabulary still contains all contract values |
| **RB3-56** | **SQLite length semantics**: over-length `message`, `reason_code`, `dedupe_key`, `id`, `created_at` | Refused by the explicit `length()` CHECKs, proving the design does not rely on `TEXT(n)` |
| **RB3-57** | **Duplicate typed evidence identity with NULL span coordinates** | Refused by G11 (NULL-safe) even though the partial unique index treats NULLs as distinct |
| **RB3-58** | **ORM/migration parity** with three tables and both partial indexes | `test_migration_matches_the_orm_metadata` semantics satisfied by name for every table and index |
| **RB3-59** | **Zero-item evaluation then nonempty output** (case 8) and **nonempty then zero** (case 9) | `409 E_IDEMPOTENCY_CONFLICT` reason `output_identity_changed`; completion row immutable; no UPDATE/supersession |
| **RB3-60** | **Repeated zero-item evaluation** (case 7) | Zero writes; `replayed=True`; `review_items_total=0` |
| **RB3-61** | **Extra persisted items** (case 2) and **missing persisted items/links** (case 3) | `409 E_IDEMPOTENCY_CONFLICT` reasons `extra_persisted_items` / `missing_persisted_evidence`; no repair |
| **RB3-62** | **Audit row present but item/link set inconsistent** (case 10) | `409 E_IDEMPOTENCY_CONFLICT` reason `audit_business_inconsistent`; explicit content validation of `event_type`, actor, run, outcome and `safe_detail` identities/counts |
| **RB3-63** | **Items/links present without a completion row** (case 11) | `409 E_IDEMPOTENCY_CONFLICT` reason `completion_evidence_missing`; rows never adopted |
| **RB3-64** | **Rollback then retry** (case 13) | Retry persists successfully as a first evaluation; semantic output identical; new UUIDs differ from the abandoned attempt and that is accepted |
| **RB3-65** | **Audit semantics**: `actor_type='user'` for a doctor; `safe_detail` length asserted ≤500 and containing no clinical prose, document text, credential or free-text note; exactly one audit row per first evaluation and none on replay | Enforced; `record_denial` never called (asserted by test) |
| **RB3-66** | **DR-006 reachable path** (two eligible `doctor_verified` rows, identical `measured_at`, different values, both source documents non-selected): under D-RB3-08 option (i) → persisted with four span-resolved links, `provenance_status='fixture_asserted'`, no trust promotion; under option (ii) → the **entire invocation** denies with reason `dr006_persistence_not_authorized` and zero writes | Never a partial persist; never a silently dropped item |

**RB4 separation (unchanged).** Run-backed GOLD A/B/C/D final acceptance is a separate future activity. GOLD-D-shaped cases used here as implementation regression tests (for example asserting the expected rule set `[DR-001, DR-003, DR-005, DR-008, DR-009]`, five items, a diastolic delta of 168, or a duplicate systolic 130 at `2026-10-20T09:00:00Z`) are **not** an RB4 acceptance claim and must not be reported as one. No matrix outcome above is claimed as executed.

---

## 12. Explicit owner decisions requested (no approval assumed)

| ID | Exact question | Relevant existing contract | Alternatives | Recommendation | Safety / engineering trade-offs | Exact scope of the proposed authorization |
|---|---|---|---|---|---|---|
| **D-RB3-01** | Approve an internal authenticated service boundary only (no HTTP endpoint, agent tool, graph node, task or notification) for RB3 persistence? | `TOOL_CONTRACTS.md` F2/RB1/RB2 boundary sections; `AGENTS.md` §3 | (a) internal service; (b) internal doctor endpoint; (c) graph node | **(a)** | (a) smallest attack surface, no OpenAPI change, no new authorization path; (b)/(c) would create a runtime surface the phase has not accepted | Binds N1/N2 shape only |
| **D-RB3-02** | Approve the two-phase architecture: verified read-only pins, then one independently controlled committing `BEGIN IMMEDIATE` transaction with the corrected T1–T16 sequence (fresh full-history reconstruction at T5–T6)? | `p5_run_gate.py:887-925`, `p5_evidence_bridge.py:330-344`; `STATE_AND_GRAPH_CONTRACT.md` §7 | (a) as designed; (b) single transaction doing everything incl. F2 projection; (c) no transaction, best-effort writes | **(a)** | (a) honest about non-atomicity and keeps accepted helpers unchanged; (b) would require re-owning F2's committed evidence write; (c) permits partial persistence and is rejected | Binds §3 and N1 |
| **D-RB3-02b** | Prefer the separately authorized **docstring-only** E6 clarification in `p5_run_gate.py` over knowingly contradictory source documentation? | `p5_run_gate.py:862-868` | (a) docstring-only E6; (b) leave the docstring and record an append-only contract note | **(a)**, with (b) as the fallback if E6 is refused | (a) removes a real contradiction with zero logic risk; (b) keeps P5 bytes untouched but leaves misleading source text | Authorizes at most a docstring edit in one file; no logic, signature or test change |
| **D-RB3-03** | Approve evaluator boundary **Alt A2** (unchanged RB2 as pure computation core; `fixture_asserted` used strictly as a transport label for stored-proved rows; truthful `stored_independently_verified` recorded in RB3's own completion record; mandatory independent in-transaction stored-lineage proof; equivalence tests; append-only contract note) — or **Alt B** (RB3-owned re-derivation)? | `TOOL_CONTRACTS.md:270`; `schemas/p4_rb2_offline_rules.py:67-69`; `p4_rb2_offline_rules.py:221-225`, `:247-257`, `:316-321` | A2 / B / C (modify RB2) | **A2**, with the corrected conditions of §4.3; **C rejected** | A2: one reviewed core, R01–R08 inherited, zero RB2 diffs; cost: a transport label whose meaning must be documented honestly, and DR-006 stays live. B: honest labels but duplicated rule logic, divergence risk, and DR-006 becomes inert by construction. Neither weakens the pinned clock/policy/validation; neither makes RB2 output a clearance token | Binds N1/N5/N8 and the RB2 freeze |
| **D-RB3-04** | Retain exact pinned demo clock and policy binding (persistable runs must have immutable `as_of_utc == 2026-11-14T12:00:00Z` and `policy_version == demo-policy-1.1.0`; no wall clock; no conversion)? | `p4_run_bound_preview.py:37-39`, `:114-125`; `DEMO_REVIEW_RULES.md` §7 | (a) exact equality; (b) allow any run clock with a policy-relative window | **(a)** | (a) no weakening, deterministic, testable; (b) would silently generalize the demo beyond its accepted scope | Binds §2.2, §4.1, N1 |
| **D-RB3-05** | Approve the stricter structural integrity package: full UPDATE/DELETE immutability on all three tables; the exact 14-trigger inventory; `length()` CHECKs; NULL-safe duplicate-identity guard; partial unique indexes; vocabulary reserved but not writable? | `0006…:31`, `:136`, `:156-162`; `0003…:263`, `:267-277`; `0002…:289` + `models.py:278-287`; `tests/p2/test_p2_migration.py:314-331` | (a) full package; (b) immutability for `review_item` only; (c) application-layer checks only | **(a)** | (a) integrity survives SQL that bypasses the service layer; cost: 14 triggers and more migration tests. (b)/(c) leave bypass paths open | Binds N3/N4/N6 |
| **D-RB3-05a** | Approve pinning `policy_version` and `as_of_utc` to literal values by structural CHECK on `review_item` and `review_evaluation`? | `0006…:133-135` literal-pinning CHECK precedent; `DATA_DICTIONARY.md` §§2.9, 5.1 | (a) literal CHECK; (b) application-layer assertion only | **(a)** | (a) makes the demo-only scope structural; cost: a future policy version needs a migration | Binds N4 |
| **D-RB3-05b** | Approve the additive `review_item.display_order` column (beyond DATA_DICTIONARY §2.9) to preserve the evaluator's stable ordering durably? (**C-RB3-05**) | `DATA_DICTIONARY.md` §2.9; `p4_rb2_offline_rules.py:490-495` | (a) additive column + `ux_review_order`; (b) re-derive order at read time from the evaluator's rule | **(a)** | (a) ordering cannot silently change if the evaluator evolves; cost: one column beyond the dictionary, needing an append-only note. (b) keeps the dictionary byte-identical but makes persisted order a read-time computation | Binds N3/N4/N7 |
| **D-RB3-05c** | Approve `checkin_note` being reserved but structurally unwritable by RB3 (G8), and `verification_issue`/`summary_claim` owner types likewise (G7)? | `DATA_DICTIONARY.md` §2.10 | (a) reserve + trigger-block; (b) drop the values from the CHECK | **(a)** | (a) preserves the dictionary's future vocabulary while forbidding unsupported orphan ownership; (b) would contradict the contract | Binds N4 |
| **D-RB3-05d** | Approve the two-layer evidence-identity uniqueness (partial unique indexes **plus** NULL-safe trigger G11) rather than a COALESCE expression index? (**C-RB3-04**) | `0002…:289`; `models.py:278-287`; `0003…:263`; `tests/p2/test_p2_migration.py:314-331` | (a) partial indexes + trigger; (b) expression index | **(a)** | (a) uses only accepted in-repo patterns and is parity-safe by name; (b) is more compact but its ORM reflection parity is unproven here | Binds N3/N4/N6 |
| **D-RB3-06** | Approve the pre-planned exceptional paths E1–E5 plus conditional E6, **each** still requiring its own fresh standalone marker before any edit? | `AGENTS.md` §5; the RB1/RB2 exception precedents | (a) per-path fresh markers; (b) one blanket marker | **(a)** | (a) each guard change stays individually reviewable; (b) would grant unrestricted cross-phase editing and is rejected | Authorizes nothing now; defines the future request shape |
| **D-RB3-07** | Approve the revised invocation-level receipt, replay and audit semantics: one immutable completion record per run; **zero writes** on exact replay (hence no duplicate audit row); `audit_event_id` stored so the audit row's identity **and** content are explicitly validated; no committed denial-audit mechanism; receipt fields distinguishing durable completion from row persistence? | `audit.py:49-74`, `:124-128`, `:170-190`; `DATA_DICTIONARY.md` §2.17; `STATE_AND_GRAPH_CONTRACT.md` §7 | (a) as designed; (b) append an audit row per invocation; (c) rely on the audit key alone | **(a)** | (a) no duplicate audit, no unsound replay proof; (b) duplicates the trail on every replay; (c) is unsound because the key is request-scoped and content is never compared | Binds N1/N2/N3/N4 |
| **D-RB3-08** | DR-006: **(i)** persist DR-006 normally when its stored-evidence conditions are met (recommended), or **(ii)** retain a conservative prohibition that denies the **entire** invocation fail-closed with reason `dr006_persistence_not_authorized`? (**C-RB3-02**) | `DEMO_REVIEW_RULES.md:125`, `:135`, `:161`; `p4_rb2_offline_rules.py:423-451`; `p5_run_gate.py:608`, `:617-628`; `documents/issues.py:217-258` | (i) persist; (ii) prohibit whole-invocation | **(i)** | (i) preserves a genuine stored-evidence safety signal, at the cost of persisting a rule whose independence label is a transport label; (ii) is maximally conservative but **reduces** persisted output and must be recorded as a deliberate reduction, and it must never silently drop the item while persisting others | Binds N1, N13 (only under (ii)), and RB3-66 |
| **D-RB3-09** | Approve the additive immutable `review_evaluation` completion table (a third new object beyond DATA_DICTIONARY §§2.9–2.10), with the exact schema of §6.3? (**C-RB3-03**) | `DATA_DICTIONARY.md` §§2.9–2.10, 2.17, 5.1; `audit.py:65-74`, `:124-128` | (a) dedicated table; (b) audit-only; (c) rows-only inference | **(a)** | (a) proves the original evaluation fingerprint including the zero-item case, atomically; cost: a third table, an append-only dictionary note, and one more entry in the E1/E3/E4 table sets. (b) is unsound (request-scoped key, no content comparison, 500-char bound). (c) cannot represent a zero-item evaluation at all | Binds N3/N4/N6/N7 and the E1/E3/E4 deltas |

### 12.1 Proposed exact owner ratification marker

If — and only if — the owner accepts D-RB3-01..D-RB3-09 (including the C-RB3-01..C-RB3-05 conflict resolutions) and the N1–N13 / E1–E6 allowlist split exactly as written, the proposed marker for the final reviewed RB3 design and implementation allowlist is:

```
RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE
```

Semantics (bounded): the marker would authorize **one** future separate RB3 implementation PR, confined to the N1–N13 paths, issued only after (a) this documentation-only PR is owner-reviewed and owner-merged and (b) exact merged-main CI SUCCESS is independently verified on the merge SHA. Each of E1–E6 would still require its **own** fresh standalone marker before any edit, and E5's marker must state the actual future measured backend/P3 collection pairing.

The marker would **not** authorize: full P4 acceptance or a P4 PASS; RB4 run-backed GOLD A/B/C/D acceptance; runtime policy activation beyond the bounded demo persistence service; graph, LLM, API, UI, task, notification, approval-decision, summary or state-transition-writer activity; any change to accepted F0/F1/F2/RB1/RB2 behaviour beyond the docstring-only E6; closure of issue #14; clinical use of any kind; or any merge, readiness change or self-approval by an agent (`AGENTS.md` §2).

---

## 13. Unresolved design conflicts (explicitly identified, not guessed)

| ID | Conflict | Why it is unresolved | Recommendation | What would resolve it |
|---|---|---|---|---|
| **C-RB3-01** | `TOOL_CONTRACTS.md:270` says `lineage_status='fixture_asserted'` labels ***fictional*** lineage and that a future RB3 verifier must query and prove the actual stored sources; but RB2 rejects `stored_independently_verified` (`:221-225`, test `:275`) and emits a **false** `verified_lineage_unavailable` exclusion for stored-proved rows labelled `unavailable` (`:316-321`). So an unchanged RB2 has **no** honest label for stored-proved lineage | Both admissible labels misstate something: `fixture_asserted` understates the proof mechanism, `unavailable` fabricates an exclusion. Only the owner can accept a documented transport label or authorize re-derivation | **A2 with `fixture_asserted` as an explicitly documented transport label**, all persisted artifacts truthful, `stored_independently_verified` recorded only in RB3's completion record, DR-006 never presented as a doctor attestation, append-only contract note (N8) | Owner ratification of D-RB3-03, or an owner-authorized RB2 change (Alt C, not proposed) |
| **C-RB3-02** | DR-006's activation depends entirely on the C-RB3-01 label choice, and its reachability on a PROCEED run is real but not exercised by any approved fixture | Whether to persist a rule whose independence label is contested is a safety/scope judgement, not an engineering one | **Persist** (D-RB3-08 option (i)) with four span-resolved links, no trust promotion, and the frozen `provenance_status`; otherwise deny the whole invocation | Owner decision D-RB3-08 |
| **C-RB3-03** | Invocation-level replay needs a durable completion identity; `DATA_DICTIONARY.md` §§2.9–2.10 define only `review_item` and `evidence_link`, and the audit table cannot serve (§6.3 Option 2) | Adding a third table extends the dictionary's P4 persistence scope | **Add `review_evaluation`** as proposed, with an append-only §2.10a note | Owner decision D-RB3-09 |
| **C-RB3-04** | SQLite's NULL-distinct UNIQUE semantics leave a duplicate-identity gap for `evidence_link`; the compact fix (COALESCE expression index) has no in-repo precedent and unproven ORM reflection parity under `test_migration_matches_the_orm_metadata` | Both mechanisms are viable; the choice trades compactness against parity certainty | **Partial unique indexes + NULL-safe trigger G11** | Owner decision D-RB3-05d, plus a parity test in the implementation PR |
| **C-RB3-05** | Preserving the evaluator's stable ordering durably needs `display_order`, which is not in `DATA_DICTIONARY.md` §2.9 | Additive column versus read-time re-derivation | **Additive `display_order`** + `ux_review_order`, with an append-only dictionary note | Owner decision D-RB3-05b |
| **C-RB3-06** | The exact closed list of `reason_code` literals and the exact per-flag evidence-reference bound must be transcribed from the accepted RB2 call sites rather than paraphrased in a design document | Transcription is an implementation-PR task; guessing here would risk a wrong CHECK constraint | Defer to N4/N5 with a test asserting the transcription against RB2's emitted values; the structural bounds used here (`item_count ≤ 12`, `evidence_link_count ≤ 96`, `evidence_link_count ≥ item_count`) are derived from `max_items_per_type = 3` × 4 measure types and `_flag`'s refusal of empty evidence | Implementation-PR tests plus owner review of the migration |

---

## 14. This PR's scope, procedure and rollback

- **Files (exactly three):** this design document (corrected in place — it is new and unratified), an append-only `docs/phase-reports/PHASE_4_REPORT.md` checkpoint, and an append-only `docs/roadmap/PHASE_PROGRESS.md` checkpoint. Both appends were verified to remove zero lines. If any fourth path were required, this task would stop and explain rather than proceed; none is.
- **Not modified:** contracts, application source, tests, fixtures, models, migrations, dependencies, CI configuration, scanner, policy YAML, GOLD fixtures. No P5 source file is modified; E6 is identified and justified only.
- **Procedure:** one DRAFT PR (#42) targeting `main` from the session branch based on the exact verified main `7190b25e…`. The agent never merges, never marks the PR ready for review, and never self-approves (`AGENTS.md` §2). Corrections are committed normally to the same branch; history is not rewritten and no second PR is created.
- **Checks actually executed for Revision 2:** the git/`gh` state verifications in §0 and §14; read-inspection of every source path cited in §1.2 with line-level evidence; `git diff` proof that both report appends remove zero lines; and `python scripts/python/scan_repository.py` on the staged tree. Exact-head CI results are reported in §0 and in the PR conversation. **Not executed:** any `pytest`, `ruff`, `alembic` or frontend command in this session; no RB3 code, migration, model, contract or fixture exists; no case in §11 has been run; no Windows or real-OCR gate; no coverage or pass-count claim.
- **Rollback:** close PR #42 unmerged. Zero database, source, fixture or policy impact.

**Standing status:** P4 **IN_REVIEW** · issue #14 **OPEN** · full P5 **NOT ACCEPTED** · original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN** · no RB4, graph, LLM, API, UI, task, notification, summary, approval-decision writer or clinical capability is authorized or claimed · **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**
