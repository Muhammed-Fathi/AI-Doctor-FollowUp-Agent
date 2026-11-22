# P4-RB3 — durable run-bound review persistence: independent design discovery and specification (owner decision requested)

**State: DESIGN ONLY / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED / NO IMPLEMENTATION IN THIS PR.**
Authored 2026-11-22 (UTC); filename date `20261123` follows the task specification for P4-RB3. Tracking: [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; P4 remains **IN_REVIEW**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` (`1O5`→`105`) remains **FAIL / NOT PROVEN**.

**ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.** Nothing in this document diagnoses, treats, advises, activates a graph/LLM/API/task/notification, or authorizes any agent merge or phase acceptance.

**Branch note (honest deviation):** the task proposes branch `docs/p4-rb3-durable-persistence-design`. This Arena session is pinned to its single session branch `arena/91facff6-ai-doctor-followup-agent`, which is based on the **exact verified main** `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`; the session model forbids creating or pushing any other branch. The design-only branch requirement ("separate branch based on the exact verified main, docs-only content, one draft PR to main") is therefore satisfied by this session branch under a different name. No other deviation is intended.

---

## 0. Independently verified merged-P4-RB2 checkpoint (executed in this session)

All checks below were **actually executed here** via `git` and authenticated `gh api`/`gh run` reads on 2026-11-22; none is copied from a prior report.

| Check | Command evidence | Result |
|---|---|---|
| PR #41 merged by the repository owner | `gh pr view 41 --json mergedBy,mergedAt,state,headRefOid,mergeCommit` | `state=MERGED`, `mergedBy.login=Muhammed-Fathi` (owner), `mergedAt=2026-11-22T23:20:55Z` — **VERIFIED** |
| Exact reviewed candidate merged | same call: `headRefOid` | `8dd79ac0aa8fc626dcc9b4b7ecf3de3a8aedc888` — equals the accepted RB2 feature SHA — **VERIFIED** |
| Merged-main tree matches candidate tree | `git rev-parse 7190b25e…^{tree} 8dd79ac0…^{tree}`; `git diff --stat 8dd79ac0 7190b25e` | both trees `2b083757d04cc202ca64523d25c8e87dcc4cd3fd`; diff empty — **VERIFIED** |
| Merge-commit parentage | `git log --format='%H %P' -1 7190b25e…` (after `git fetch --unshallow`) | parents `eaab808b81986077c94eec8f4858c9f746c92ca8` (prior main) + `8dd79ac0…` — **VERIFIED** |
| Main remains at expected starting SHA | `git rev-parse origin/main` | `7190b25e2c62de3a56e369f12bf6d9fbecd8982e` — **VERIFIED** |
| Owner acceptance marker exists | `gh api …/issues/comments/7087501521` | author `Muhammed-Fathi`, 2026-11-22T23:20:34Z, body begins `OWNER-ACCEPT-P4-RB2`, accepts exactly SHA `8dd79ac0…`, explicitly does **not** authorize runtime activation, persistence, RB3/RB4 or P4/P5 acceptance — **VERIFIED** |
| Permanent evidence report exists | `gh api …/issues/comments/7087467476` | author `Muhammed-Fathi`, 2026-11-22T23:17:52Z, "P4-RB2 final validation evidence report — not an approval marker" for candidate `8dd79ac0…` — **VERIFIED** |
| Post-merge main CI SUCCESS incl. all mandatory gates | `gh run view 45082770648 --json …` + `gh api …/runs/45082770648/jobs` | run `45082770648`, event `push`, `headBranch=main`, `headSha=7190b25e…`, `status=completed`, `conclusion=success`. Backend (Python 3.12) SUCCESS with every step successful: Ruff lint, Ruff format check, Backend tests, Alembic migration smoke (upgrade/downgrade/upgrade), OpenAPI contract check, secret/artefact scan. Frontend (Node 22) SUCCESS: ESLint, typecheck, Vitest, production build — **VERIFIED** |
| Issue #14 state | `gh issue view 14 --json state` | `OPEN` — **VERIFIED** |

**Gate conclusion:** CI is neither pending, failed nor unavailable. The RB3 design branch precondition is met; this docs-only design work may proceed. RB2 acceptance conveys **no** RB3 authority.

## 1. Actual repository findings (read in this session, resolved from the merged tree)

### 1.1 Governing documents read

`AGENTS.md`; [P4 Run-Bound Integration design](P4_RUN_BOUND_INTEGRATION_DESIGN_20261122.md) (D-RB-01..04, RB-01..24 matrix); [RB1 implementation review](P4_RB1_READONLY_ADAPTER_REVIEW_20261122.md); [RB2 design](P4_RB2_OFFLINE_SIX_RULE_DESIGN_20261122.md) (D-RB2-01..04) and [RB2 implementation review](P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md) (R01–R08, owner DR-003 clarification, 1255/443 collection checkpoint); [F1 design](P5_F1_RUN_BOUND_VERIFICATION_GATE_DESIGN_20261121.md); [F2 design](P5_F2_EVALUABLE_EVIDENCE_BRIDGE_DESIGN_20261122.md); `docs/contracts/DATA_DICTIONARY.md` (§§2.4–2.10, 2.16–2.18, 2.21, 3.1–3.3, 5.1); `docs/contracts/TOOL_CONTRACTS.md` (§§3.4–3.7 + F2/RB1/RB2 appended boundaries); `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (§7 idempotency/two-phase finalize, §7.3 reconciliation, §8 bounds, `ReviewFlag`/`ProvenanceRef` shapes, RB1 non-clearance section); `docs/clinical-safety/DEMO_REVIEW_RULES.md` (§§3–10); `docs/contracts/EXTRACTION_PROVENANCE.md` (§5 provenance kinds, span resolvability); [PHASE_4_REPORT.md](PHASE_4_REPORT.md); [PHASE_PROGRESS.md](../roadmap/PHASE_PROGRESS.md).

### 1.2 Merged source actually inspected

| Component | Path | Verified facts this design relies on |
|---|---|---|
| F0 run foundation | `backend/app/services/p5_run_foundation.py` | `create_run_foundation` persists `workflow_run` (`status='queued'`), immutable `run_selected_document` / `run_selected_observation` / `run_source_omission`; 1..5 documents mandatory (R21 rejects empty source set), ≤20 selected observations; run clock `as_of_utc` is caller-injected at start and immutable afterwards; `POLICY_REFERENCE_VERSION='demo-policy-1.1.0'`, `WORKFLOW_VERSION=STATE_SCHEMA_VERSION='1.0.0'`, `MAPPING_VERSION='map-1.0.0'`; start idempotency key = sha256 over patient/version/sorted IDs/client request ID; audit `workflow.run.started` in the same transaction |
| F1 run gate | `backend/app/services/p5_run_gate.py` | `evaluate_run_verification_gate` owns `BEGIN IMMEDIATE`, commits gate rows + audit; `_authorize` re-reads the **stored** `UserSession` (unrevoked, `created_at ≤ at < expires_at`), active doctor user, synthetic patient, `patient.assigned_doctor_id == principal.user_id`, `run.doctor_id == principal.user_id`; `_file_sha` re-hashes selected bytes **twice** (mid-evaluation and pre-commit `source_bytes_changed_during_gate`); the canonical snapshot fingerprint covers run rows, documents, facts, decisions, issues, observations, selection, omissions and settings; replay compares full stored decision incl. blockers/historical list → `409 E_IDEMPOTENCY_CONFLICT` on any mismatch; `inspect_current_run_gate_locked(db, …)` is a **read-only** re-evaluation requiring a caller-held transaction and an existing matching persisted PROCEED (`require_existing=True`); its docstring currently states "Only the F2 bridge may call this" (see §9 E6); `runtime_evaluable=False` always |
| F2 evidence bridge | `backend/app/services/p5_evidence_bridge.py` | `build_run_evaluable_review_evidence` owns `BEGIN IMMEDIATE`, **always rolls back**; requires F1 locked PROCEED at entry and again at exit (fingerprint equality); `CONTRACT_VERSION='2.0.0'`; `f2-history-365d-v1`, 365-day comparison; caps: current ≤6, facts ≤40, history ≤100; history eligibility: a `verified_document` observation is excluded (`verified_lineage_unavailable`) unless its source document is **run-selected**; bridge fingerprint covers contract/gate/run/documents/selection/facts/observations/comparisons/exclusions; `missing_baseline`→`no_baseline` projection |
| RB1 preview | `backend/app/services/p4_run_bound_preview.py` | `build_p4_run_bound_review_input_preview` = F2 read → own `BEGIN IMMEDIATE` 90-day projection (rollback) → second F2 read, requiring `first == last`; binds the run to the pinned R3-A reference: `run.policy_version='demo-policy-1.1.0'` **and** `run.as_of_utc == 2026-11-14T12:00:00Z` (format-equal to `policy.demo_as_of_utc`); compiled pinned constants validated via `validate_demo_policy` (never loads the test-only YAML at runtime); canonical LF SHA `f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36`; 90-day comparisons via `compare_explicit_current_with_history(baseline_lookback_days=90)` over `load_readonly_provenance_evidence` rows minus F2 exclusions; output frozen with `runtime_evaluable=False`, `rules_executed=False`, `review_items_persisted=False`, `policy_status='unapproved'` |
| RB2 offline evaluator | `backend/app/services/p4_rb2_offline_rules.py`, `backend/app/schemas/p4_rb2_offline_rules.py` | Pure `evaluate_p4_rb2_offline_fixture(OfflineRuleInput)`; pinned clock `_PINNED_CLOCK=2026-11-14T12:00:00Z` enforced on both the injected clock and `policy.demo_as_of_utc`; exact R3-A numeric pinning (90/30/10/8/15/40/0.70/0/3, six VI + six DR); `_ARITHMETIC_CONTEXT` (prec 28, trapped) per R08; overflow-safe 90-day window per R07; `_valid_id` rejects `|`/control chars protecting the dedupe serialization; R05: `source_fact_verification_status ∈ {pending, rejected}` → `E_UNVERIFIED_FACT` fail-closed; `lineage_status ∈ {unavailable, fixture_asserted}` only — `stored_independently_verified` is rejected as forged caller authority and documented as "a FUTURE RB3 server-side state"; DR-006 requires `_independent_fixture_source` on **both** rows (distinct document and fact IDs); DR-003 per owner clarification `APPROVE-P4-RB2-DR003-NEWEST-ADMISSIBLE-SELECTED-TYPE`; cap overflow fails closed; dedupe `sha256("|".join(patient_id, rule_id, *sorted_refs, trust_basis))` with typed keys `observation:<id>` / `document:<id>` / `fact:<id>`; ordering `(hint, rule_id, evidence, dedupe_key)`; result flags frozen, `provenance_status='fixture_asserted'`, `review_items_persisted=False` |
| Sessions / auth / audit | `backend/app/db/session.py`, `backend/app/api/v1/auth/dependencies.py`, `backend/app/core/policies.py`, `backend/app/services/audit.py` | `Principal` built only from stored session+user rows; `require_doctor` / `require_assigned_patient`; SQLite per-connection `PRAGMA foreign_keys=ON`; `session_scope`/`get_db_session` commit-on-success helpers exist but F1/F2/RB1 deliberately manage explicit `BEGIN IMMEDIATE`; `append_audit_event` derives its idempotency key only from immutable request facts (never a new row ID) and is caller-transaction-scoped; event vocabulary is namespaced for additive extension |
| Migration state | `backend/migrations/versions/0001..0007` | **Actual current Alembic head: `0007_p5_run_gate`** (no revision lists it as `down_revision`; `HEAD_REVISION='0007_p5_run_gate'` pinned in `scripts/python/check_alembic_smoke.py`, `backend/tests/test_database.py`, `backend/tests/p2/test_p2_migration.py`). 0006/0007 pattern: additive tables, immutability triggers, downgrade refusal when rows exist |
| Schema guards that RB3 will trip (read, not modified) | `backend/tests/test_database.py`, `backend/tests/p2/test_p2_migration.py`, `backend/tests/p2/test_p2_scope_guards.py`, `scripts/python/check_alembic_smoke.py`, `backend/tests/p3/test_windows_ocr_acceptance.py` | `FUTURE_TABLES` (test_database) and `P4_PLUS_TABLES` (scope guards + smoke script) both list `review_item` and/or `evidence_link` as **forbidden**; exact head table-set equality assertions; forbidden module names include `reviews.py`, `review_rules.py` (the proposed `p4_rb3_review_persistence.py` matches none); the P3 handoff guard requires the literal adjacent phrase `**N collected**, of which **443** are the P3 suite` in `PHASE_3_WINDOWS_ACCEPTANCE.md` (current token **1255 collected / 443**, appended under owner marker `APPROVE-P4-RB2-P3-HANDOFF-1255-COLLECTION-ONLY`) |
| Absent by design | — | No `review_item`/`evidence_link` ORM models or tables exist; no DR persistence anywhere; P2 doctor API hard-codes `review_items=[]` / `open_review_item_count=0` and reads no such table; OpenAPI is 17 paths / 18 operations / 43 schemas |

**No API is invented below.** Every helper named in this design exists at the cited path in the merged tree. Nothing assumes an existing helper provides execution authority: F1 PROCEED, F2 V2, RB1 preview and RB2 results are all documented non-clearances, and RB3 treats them exactly so.

---

## 2. (A) Authority and authorization design

### 2.1 Proposed internal authenticated service boundary

One new internal service function (no HTTP route, no agent tool, no graph node):

```text
persist_run_review_items(
    db: Session, *,
    principal: Principal,          # server-built from a stored session row only
    run_id: str,                   # selects one genuine persisted workflow_run
    validation_clock: datetime,    # aware UTC, injected; validates session/freshness only
    upload_root: str,              # configured trusted local upload root
) -> ReviewPersistenceReceiptV1    # frozen, honest, non-executable receipt
```

The parameter list is deliberately identical in shape to F1/F2/RB1: **the caller supplies identity and environment, never evidence, decisions or policy.** There is no parameter through which any of the following could enter, so all are structurally impossible, not merely checked:

- caller-supplied clearance flags (`run_gate_completed`, `proceed`, `gate_status`, `blocking_fact_count=0`);
- trusted fact counts or "already verified" assertions;
- arbitrary evidence/observation/document/fact IDs, patient IDs, dedupe keys or review-item IDs;
- policy overrides (`policy_version`, `baseline_lookback_days`, thresholds, disabled VI/DR switches);
- cached V2 / RB1 preview / RB2 result objects as executable authority (the DTOs used for identity pinning are constructed **inside** the same call from live reads — §3; they are never accepted as arguments);
- a `review_item_id` or state-transition instruction (RB3 only creates `state='open'` rows).

### 2.2 Authorization conditions (all re-proved from stored rows inside the write transaction)

Mirrors F1 `_authorize` semantics, re-executed under the write lock (§3 T2):

1. `principal` is a genuine `Principal`; `require_doctor(principal)`.
2. The stored `UserSession` row for `principal.session_id` exists, has `revoked_at IS NULL`, and `created_at ≤ validation_clock < expires_at`.
3. The `User` row is `role='doctor'` and `is_active=1`.
4. The `workflow_run` exists (**404 `E_NOT_FOUND` "Run is unavailable."** otherwise, never acknowledging foreign runs), `run.doctor_id == principal.user_id` (**403 `E_FORBIDDEN`**), `run.status == 'queued'` (RB3 never transitions status).
5. The `Patient` row has `data_source='synthetic_fixture'` and `patient.assigned_doctor_id == principal.user_id` (**403 `E_SCOPE_VIOLATION`** via `require_assigned_patient`).

### 2.3 Denial and stale-evidence conditions (typed, fail-closed, zero writes)

| Class | Detected by | Outcome |
|---|---|---|
| Missing/absent gate | `inspect_current_run_gate_locked` requires an existing persisted matching F1 decision (`require_existing=True`) | 409 `E_VALIDATION` denial; no rows |
| HALT / UNAVAILABLE gate, any VI blocker | locked F1 re-evaluation `decision != 'proceed'` or issues/unavailable reason present | 409 denial; historical VI rows untouched |
| Stale source decision | recomputed F1 fingerprint ≠ persisted PROCEED fingerprint, or ≠ pinned RB1 `gate_input_fingerprint_sha256` | 409 stale-evidence denial; a cached PROCEED is **never** reused |
| Session revocation / expiry mid-flight | condition 2 re-read inside the write transaction | 403; rollback |
| Patient reassignment mid-flight | condition 5 re-read inside the write transaction | 403; rollback |
| Source byte tamper | F1 locked evaluation re-hashes bytes twice inside the write transaction (`source_bytes_unavailable` / `source_bytes_changed_during_gate`) | 409/503-class denial; rollback |
| Verification-decision / manifest / observation tamper | any change alters the F1 canonical fingerprint (facts, decisions, issues, observations, selection, omissions are all fingerprinted) | 409 denial |
| Policy tampering | `run.policy_version != 'demo-policy-1.1.0'`, pinned compiled reference mismatch (RB1 `_pinned_policy` semantics) | 409 denial; never a fallback default |
| Clock mismatch | `run.as_of_utc != '2026-11-14T12:00:00Z'` (RB1 binding, §4.1) | 409 denial |
| Evidence drift between pre-read and write transaction | pinned bridge fingerprint / comparison set / selection re-checked in-transaction | 409 stale-evidence denial |
| Evaluator typed error or cap overflow | `OfflineRuleError` (`E_RULE_POLICY_INVALID`, `E_VALIDATION`, `E_UNVERIFIED_FACT`, `E_SCOPE_VIOLATION`) | mapped 409 denial; **no partial items** |
| Any unresolvable / foreign / unproven evidence reference in a candidate flag | post-evaluation stored-evidence proof (§6.3) | 409 denial for the whole invocation |

**RB2 acceptance does not authorize runtime activation.** The owner marker `OWNER-ACCEPT-P4-RB2` ([comment #7087501521](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087501521)) explicitly excludes runtime rule activation, persistence and RB3. Authority for the future RB3 write service comes **only** from (a) a fresh owner ratification of this design, (b) an owner-merged design PR with green exact-main CI, and (c) a separately reviewed RB3 implementation PR — never from any RB2 artifact, frozen DTO or prior marker.

---

## 3. (B) Fresh transactional verification — exact SQLite transaction ownership and lock boundary

### 3.1 Honest non-atomicity acknowledgements (normative)

1. **SQLite cannot transact atomically with filesystem upload bytes.** The write transaction hashes selected files inside the transaction (via the F1 locked evaluation, which re-hashes near its end) and again immediately before commit; nevertheless a byte swap **after commit** is undetectable by that transaction. Every later consumer (RB4, any future read surface) must recheck freshness, exactly as the F2/RB1 contracts already require.
2. **The F1/F2/RB1 reads and the RB3 write are separate SQLite transactions.** The RB1 pre-read internally performs three separate lock acquisitions (F2 read #1 → RB1 locked 90-day read → F2 read #2), each rolling back. The RB3 write transaction is a **fourth, distinct** transaction and the **only committing one**. Fingerprint equality *pins* the sequence; it does **not** make it one atomic snapshot, and no report may describe it as such (preserves D-RB-02's snapshot caveat verbatim in spirit).
3. The design uses only public, reviewed entry points. If the owner ratifies D-RB3-02/03, one **docstring-only** clarification in `backend/app/services/p5_run_gate.py` is requested as an exceptional cross-phase path (§9 E6) because `inspect_current_run_gate_locked`'s docstring currently names the F2 bridge as its only caller. **No P5 logic changes. Nothing was modified in this design PR.**

### 3.2 Transaction sequence (where the transaction begins, what runs inside, where commit/rollback occur)

**Phase 0 — preconditions, no transaction.** Require a fresh clean `Session` (`db.in_transaction() or db.new or db.dirty or db.deleted` → **400 `E_VALIDATION`**, F1/F2 pattern). Validate argument types (`Principal`, non-empty `run_id`, aware `validation_clock` via `to_utc`, non-empty `upload_root`). The caller owns the Session; the service never opens `session_scope` itself.

**Phase 1 — read-only pinning (separate transactions, always rolled back, zero writes).**
Call `build_p4_run_bound_review_input_preview(db, principal=…, run_id=…, validation_clock=…, upload_root=…)`. This single public call performs: F2 build #1 (own `BEGIN IMMEDIATE`, F1 locked recheck ×2, byte re-hash, rollback), the RB1 locked 90-day projection (own `BEGIN IMMEDIATE`, rollback), F2 build #2 with `first == last` equality, and the pinned-policy/pinned-clock/run-identity binding. On success RB3 holds a frozen `RunBoundReviewInputPreviewV1` pinning: `gate_evaluation_id`, `gate_input_fingerprint_sha256`, `bridge_input_fingerprint_sha256`, run identity/versions, `as_of_utc`, selected document/observation IDs, verified facts, selected observations, 90-day `policy_comparisons`, `history_exclusions`, `no_current_reason`. **The preview is an input pin, not a clearance.** Any Phase-1 denial propagates as-is (§2.3) with zero writes.

**Phase 2 — the single write transaction.** The service executes `db.connection().exec_driver_sql("BEGIN IMMEDIATE")` on the same (now clean) Session — **this is where the RB3 transaction begins**. `OperationalError` on acquisition → rollback → **503 `E_VALIDATION` "Verification database is unavailable."** (F1 pattern; lock failure never claims success). `BEGIN IMMEDIATE` takes the SQLite write lock immediately, serializing all writers for the whole verify-and-persist span. Inside this one transaction, in order:

- **T1 clean-lock assertion.** Session must not already be in a transaction; the IMMEDIATE lock is held until commit/rollback.
- **T2 authorization re-check** (§2.2 conditions 1–5 re-read from stored rows under the lock): revocation, expiry, deactivation, reassignment and foreign-run states are detected **here**, not from Phase-1 memory.
- **T3 F0/F1 reconstruction and revalidation.** `gate = inspect_current_run_gate_locked(db, principal=…, run_id=…, at=clock, upload_root=…)`. This read-only locked call re-derives, **inside the write transaction**: the F0 manifest rows (selection, duplicates, caps), document metadata vs manifest `source_sha256`/`source_status`, **actual file bytes vs stored SHA-256 (re-hashed twice, including near the end)**, active-fact reconstruction with D-14 supersession semantics, every VI-001..006 recomputation, persisted P3 issue state (historical terminal OPEN `VI-002` preserved, never resolved), selected-observation admissibility and trust coherence, R21-S1 omission/recovery lineage, and the requirement of an existing persisted F1 PROCEED whose fingerprint matches the fresh recomputation. RB3 then asserts `gate.decision == 'proceed'`, zero issues, no unavailable reason, and **`gate.input_fingerprint_sha256 == preview.gate_input_fingerprint_sha256`** and `gate.gate_version == preview.gate_version`. Any mismatch → 409 stale-evidence denial → rollback.
- **T4 run/manifest identity re-pin.** Re-read `workflow_run` and both selection tables; assert equality with the preview (patient, doctor, `as_of_utc`, `workflow_version`, `state_schema_version`, `mapping_version`, `policy_version`, `status='queued'`, sorted selected document/observation ID tuples, no duplicates, caps 1..5 / ≤6-current). F1's fingerprint already covers these rows; the explicit re-pin provides a typed, testable denial surface.
- **T5 90-day comparison recomputation (never F2's 365-day result).** `load_readonly_provenance_evidence(db, principal=…, patient_id=run.patient_id, as_of_utc=run_clock)`; rebuild history rows = provenance records − preview `history_exclusions` − selected IDs (RB1 `_policy_projection_locked` semantics); re-verify each selected current row's stored values/provenance against the preview; run `compare_explicit_current_with_history(current, history, patient_id, as_of_utc=run_clock, baseline_lookback_days=90)`; assert the result **equals** `preview.policy_comparisons` item-for-item (and `no_current_selected` semantics for zero selection). Inequality ⇒ concurrent modification ⇒ 409 denial, rollback. The F2 365-day `comparisons` are used for **nothing** except identity pinning through the bridge fingerprint.
- **T6 rule-input projection** (§4.3): stored rows → RB2 typed inputs; bound assertions (≤6 current, ≤100 history, ≤40 active fact statuses, all `'verified'`); derived-only trust labels.
- **T7 rule computation:** `result = evaluate_p4_rb2_offline_fixture(input)` — pure in-process computation core (D-RB3-03). `OfflineRuleError` → typed 409 denial, rollback, **zero partial items**. Assert the evaluator's typed exclusions over the pre-filtered eligible set are empty of admissibility-class reasons (`validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp`); any such exclusion means the stored evidence diverged from the RB1-validated set ⇒ denial (this also fail-closes the known conservative edge where a row admissible under the `as_of+5min` skew guard is strictly future of the pinned clock for RB2 — denial, never silent divergence).
- **T8 stored-evidence proof of every candidate flag** (§6.3), including DR-006/DR-008 provenance re-derivation and the run-bound DR-006 unreachability rule (D-RB3-03/§6.4). Any failure ⇒ whole-invocation denial.
- **T9 replay/idempotency resolution** (§7): select existing `review_item` rows for the run; per candidate — absent → stage INSERT; present → full stored-content equality ⇒ replay no-op; mismatch ⇒ **409 `E_IDEMPOTENCY_CONFLICT`**, rollback.
- **T10 inserts** in the evaluator's deterministic flag order: `review_item` rows (`state='open'`, `created_at=format_utc(validation_clock)`, dedupe key from the evaluator, `policy_version` copied from the run after the pinned equality assert), then their `evidence_link` rows (§6), then the audit event (§7.4) via `append_audit_event` — all in this transaction. `IntegrityError` on `ux_review_dedupe` / FK / CHECK / trigger ⇒ rollback ⇒ typed 409 conflict (defensive; unreachable while the IMMEDIATE lock is held honestly).
- **T11 pre-commit freshness recheck.** Second `inspect_current_run_gate_locked` call (read-only, same transaction) asserting an unchanged fingerprint versus T3 — mirrors F2's final recheck and F1's pre-commit byte re-hash, catching in-transaction drift before commit.
- **T12 COMMIT** — the only commit in the whole service. 
- **T13 any exception anywhere ⇒ ROLLBACK ⇒ re-raise the typed error.** No partial persistence is reachable: review items, evidence links and the audit row commit together or not at all.

**Receipt (frozen):** run/patient/doctor IDs, `as_of_utc`, `policy_version`, pinned `gate_evaluation_id` + both fingerprints, a canonical RB3 `evaluation_fingerprint_sha256` (§7.1), sorted created/persisted review-item IDs, evidence-link count, `replayed: bool`, and honesty flags: `review_items_persisted=True`, `rule_evaluation_executed=True` (run-bound sense, distinct from RB2's offline `rules_executed=False`), `runtime_evaluable=False` (nothing downstream is unlocked), `graph_or_llm_invoked=False`, `run_status_changed=False`, `demo_only=True`, `policy_status='reference_pinned_demo_only'`. The receipt is not a token: no consumer may persist, execute or message anything on its basis.

### 3.3 Concurrency, replay and denial handling

- **Concurrent invocations:** `BEGIN IMMEDIATE` serializes writers; the loser blocks, then re-verifies inside its own transaction, sees the winner's committed rows in T9 and resolves to the exact-replay path (or a typed conflict if content differs — which cannot happen while the fingerprint is unchanged).
- **Concurrent source modification:** any change to fingerprinted rows/bytes between T3 and T11, or between Phase 1 and Phase 2, fails closed (T3/T5/T11 equality asserts); a change committed *before* T3 simply yields a different fingerprint than the pin ⇒ stale-evidence denial.
- **Denials** raise typed `ApiError`s; consistent with F1/F2/RB1 precedent, denials inside the rolled-back write transaction write **no** audit rows (a denial audit would require a separate committed session; recording denials is left to any future API layer that owns `record_denial`). This is stated honestly rather than pretending denials are audited.

### 3.4 P5 source impact assessment

With D-RB3-02/03 as recommended, **no P5 logic change is required**: F1's `inspect_current_run_gate_locked` and F2/RB1 public builders are consumed as-is. The only candidate P5 edit is the **docstring-only** caller-scope note in `backend/app/services/p5_run_gate.py` (§9 E6) so the source text does not contradict the ratified contract. If the owner prefers zero P5 file edits, the alternative is an append-only `TOOL_CONTRACTS.md`/`STATE_AND_GRAPH_CONTRACT.md` note documenting RB3 as a second authorized locked caller while the docstring stays stale-but-unmodified; the design flags this as owner decision D-RB3-02b. **This design PR modifies no P5 file.**

---

## 4. (C) RB2-to-RB3 evaluator boundary

### 4.1 Pinned R3-A fixture clock vs the immutable persisted run clock

RB2 hard-requires `as_of_utc == policy.demo_as_of_utc == 2026-11-14T12:00:00Z` (`_PINNED_CLOCK`); F0 persists `workflow_run.as_of_utc` immutably from the start-time injected clock; RB1 already refuses any run whose `as_of_utc` differs from the pinned reference instant. **Reconciliation (D-RB3-04, recommended): RB3 inherits the RB1 binding unchanged — a run is persistable only when its immutable persisted clock equals the pinned R3-A instant.** The evaluator receives `as_of_utc = run.as_of_utc` (validated equal to the pin); the RB2 pinned-clock check is thereby satisfied **without weakening it**: no second clock, no wall-clock `now()` anywhere (AGENTS §3.2), no caller clock reaching the rules. Runs started with any other clock fail closed with a typed denial. This is contract-consistent: `DEMO_REVIEW_RULES.md` §7 states demo-mode evaluation uses `demo_as_of_utc` "stored on the run", and changing it requires a `policy_version` bump and fixture updates — i.e., generalizing the clock is a future policy-version decision, **not** an RB3 relaxation.

### 4.2 Offline policy reference vs separately approved execution authority

The R3-A YAML remains an **offline test seal** (canonical LF SHA `f3bdad3f…bd36`); application code never reads it (the historical guard `test_reference_artifact_is_not_imported_by_app_runtime` stays intact). RB3 uses the same **compiled pinned constants** pattern as RB1 (`validate_demo_policy` over in-source literals) and additionally asserts `run.policy_version == 'demo-policy-1.1.0'`. Execution authority is **not** the policy artifact: it is the owner-ratified RB3 implementation operating inside the §3 boundary. `validate_demo_policy` passing, the SHA seal matching, or an RB2 result object existing are each explicitly **not** activation, exactly as R3-A/D-RB-03 already ruled.

### 4.3 Fixture-asserted lineage vs actually persisted provenance — alternatives and recommendation

RB2's typed boundary accepts `lineage_status ∈ {unavailable, fixture_asserted}` and rejects `stored_independently_verified` as forged caller authority, while its own schema documents that value as "a FUTURE RB3 server-side state". Three bounded alternatives were evaluated:

- **Alt A2 — reuse the unchanged RB2 evaluator as the pure computation core (RECOMMENDED).** RB3 projects stored rows into `OfflineObservation`s and calls `evaluate_p4_rb2_offline_fixture` inside the write transaction. Conditions: (i) **zero** changes to RB2 source/schema/tests; (ii) for `verified_document` rows whose lineage RB3 has *already independently proven from stored rows in-transaction* (fact `verification_status='verified'`, real doctor decision, document `extraction_status='verified'`, patient scope, mapping identity — F2 `source_reason` + preflight semantics), RB3 sets `lineage_status='fixture_asserted'` **solely as the documented label artifact of the unchanged RB2 boundary**; the persisted evidence links reference the real stored rows and the RB3 report/receipt never describes them as fixtures; (iii) before persisting any flag, RB3 re-resolves every evidence reference against stored rows (§6.3) — the evaluator output is candidate content, **never clearance**; (iv) equivalence/regression tests pin RB3 persisted outputs to RB2 offline outputs on shared synthetic fixtures (GOLD-D included); (v) an append-only `TOOL_CONTRACTS.md` note records that the pure function may be invoked by the RB3 write boundary as a computation core while remaining a non-tool, non-clearance. Benefits: one reviewed six-rule core inheriting R01–R08 protections (pinned clock, exact numeric pinning, trapped 28-digit decimal context, overflow-safe window, ambiguous-`|` ID refusal, cap fail-closed, conservative R05, DR-003 owner semantics) with zero divergence risk. Costs: the label bridge in (ii) is a genuine semantic artifact and is therefore surfaced as an explicit owner decision (D-RB3-03), not silently adopted.
- **Alt B — RB3-owned stored-input derivation** in the new persistence module, with `stored_independently_verified` as an RB3-internal typed state set only by server queries, plus mandatory output-equivalence tests against RB2. Clean labels, but it duplicates ~500 lines of subtle, recently remediated rule logic; divergence risk persists even with equivalence tests; larger review surface. Kept as the fallback if the owner rejects the label bridge.
- **Alt C — modify RB2** to accept `stored_independently_verified` inputs. **Not recommended:** it reopens the owner-accepted RB2 candidate (`8dd79ac0…`), touches frozen reviewed source and tests, and provides no safety gain over A2's independent in-transaction proof.

**Recommendation: Alt A2 with conditions (i)–(v).** Under no alternative is the RB2 result object an execution token: authority always comes from the §3 boundary, and RB2's pinned clock, policy constraints and validation are never weakened.

### 4.4 Conservative R05 handling of pending/rejected facts

RB3 keeps R05 strictly: the projected `active_fact_verification_statuses` tuple is derived from the **stored active fact set** of the selected documents (F1's D-14 supersession reconstruction); gate PROCEED guarantees all are `'verified'`, and RB2 independently fails closed (`E_UNVERIFIED_FACT`) on any pending/rejected assertion, including in history rows' `source_fact_verification_status`. No supersession or inactivity is inferred beyond the persisted `corrected_from_fact_id` lineage that F1 already reconstructs; relaxing R05 remains a separate future owner decision (unchanged from the RB2 review).

### 4.5 R01–R08 protections, measurement types, 90-vs-365, bounds, trust, ordering

All R01–R08 remediations are inherited by construction under Alt A2 (they live inside the unchanged evaluator): dual clock pinning (R01), per-observation lineage exclusion incl. singleton-document observations (R02), missing/unparseable `created_at` typed exclusion with proven duplicates preserved (R03), policy pinning (R04 via `_policy`), conservative pending/rejected fail-closed (R05), malformed-type typed failures (R06), year-one-safe window comparison (R07), explicit local decimal context (R08). Additionally:

- **Explicit selected-current measurement types:** evaluated types derive **only** from F0-selected current observations (≤6); history never introduces a type; zero selected ⇒ zero candidates with the typed `no_current_selected` pin from RB1 — never DR-001/DR-003 inferred from unselected history (D-RB2-03 scope nuance preserved).
- **90-day policy baseline vs F2's 365-day comparison:** persisted items derive exclusively from the 90-day recomputation (T5/T6); F2's 365-day `comparisons` are identity-pin material only. A 180-day F2-valid baseline remains a 90-day `no_baseline` (D-RB-02 preserved).
- **Bounded input counts:** current ≤6, history ≤100 (provenance loader bound), active fact statuses ≤40, ≤5 selected documents; overflow fails closed, never truncates.
- **Trust labels:** `self_reported_validated` passes through unmodified; `trust_basis ∈ {self_reported, doctor_verified, mixed}` is derived by the evaluator from stored labels; message suffixes ` (self-reported)` / ` (includes self-reported values)` persist verbatim; **no trust promotion anywhere** (P0-R05/R11).
- **Stable ordering:** rows are projected in sorted-ID order; the evaluator's deterministic `(hint, rule_id, evidence, dedupe_key)` ordering fixes insert order and receipt ordering; replay is byte-stable.

### 4.6 Contract conflicts requiring explicit owner decisions

1. The `fixture_asserted` label bridge for stored-verified rows (D-RB3-03; genuine ambiguity between RB2's "test-invoked pure function" characterization and RB3's need for a six-rule core).
2. `inspect_current_run_gate_locked` docstring caller restriction vs RB3's locked revalidation need (D-RB3-02b / §9 E6).
3. Run-bound DR-006 unreachability under current F1/F2 contracts (§6.4) — recorded, not silently worked around.

---

## 5. (D) Durable schema design — `review_item` and `evidence_link` (proposed `0008`, additive)

Both tables are specified **against the existing data dictionary §§2.9–2.10**, keeping every dictionary column, type and constraint, plus explicitly flagged hardening proposals (owner decision D-RB3-05). UUIDv4 36-char text PKs, UTC ISO-8601 text timestamps, INTEGER 0/1 booleans, TEXT enums with CHECKs (dictionary conventions). **No fake run parent: `review_item.workflow_run_id` is the required NOT NULL FK to the genuine P5-F0 `workflow_run.id` with ON DELETE RESTRICT (R1-A preserved).**

### 5.1 `review_item`

| Column | Type | Null | Constraints |
|---|---|---|---|
| `id` | TEXT(36) | NOT NULL | PK, UUIDv4 (`new_uuid()`); never an idempotency input |
| `patient_id` | TEXT(36) | NOT NULL | FK `patient.id` ON DELETE RESTRICT; must equal `run.patient_id` (service-asserted) |
| `workflow_run_id` | TEXT(36) | NOT NULL | FK `workflow_run.id` ON DELETE RESTRICT — genuine run ownership |
| `rule_id` | TEXT(8) | NOT NULL | CHECK IN (`DR-001`,`DR-003`,`DR-005`,`DR-006`,`DR-008`,`DR-009`) — closed catalogue; retired `DR-002/004/007/010` structurally rejected |
| `reason_code` | TEXT(64) | NOT NULL | CHECK `length(reason_code) > 0`; evaluator vocabulary (`missing_baseline`, `measurement_stale`, `change_exceeds_demo_parameter`, `verified_source_conflict`, `duplicate_or_out_of_order`, `implausible_value`) |
| `workflow_hint` | TEXT(24) | NOT NULL | CHECK IN (`data_quality`,`verification_needed`,`change_to_review`) — ordering metadata, not severity |
| `trust_basis` | TEXT(16) | NOT NULL | CHECK IN (`self_reported`,`doctor_verified`,`mixed`) |
| `message` | TEXT(240) | NOT NULL | CHECK `length(message) > 0 AND length(message) <= 240`; neutral template + trust suffix, copied verbatim from the evaluator; prohibited-wording rules enforced by tests, not columns |
| `policy_version` | TEXT(24) | NOT NULL | immutable policy-version binding; service copies `run.policy_version` after asserting equality with the pinned reference. **Proposed hardening (D-RB3-05a): CHECK `policy_version = 'demo-policy-1.1.0'`** — a future policy bump then requires a deliberate owner-approved migration, making drift structurally impossible |
| `demo_only` | INTEGER | NOT NULL DEFAULT 1 | CHECK `demo_only = 1` (structural honesty) |
| `dedupe_key` | TEXT(64) | NOT NULL | CHECK `length(dedupe_key) = 64`; `sha256(patient_id \| rule_id \| sorted evidence keys \| trust_basis)` — exactly RB2's serialization; UNIQUE with `workflow_run_id` |
| `state` | TEXT(16) | NOT NULL DEFAULT `'open'` | CHECK IN (`open`,`decided`,`superseded`) |
| `created_at` | TEXT(20) | NOT NULL | `format_utc(validation_clock)` (injected clock; deterministic; never `now()`) |

Indexes (dictionary names preserved): `ux_review_dedupe (workflow_run_id, dedupe_key)` **UNIQUE**; `ix_review_patient_state (patient_id, state)`. The unique index's `workflow_run_id` prefix also serves run-scoped lookups; no extra index is proposed.

**State lifecycle and permitted transitions.** RB3 creates `open` rows only. `open → decided` and `open → superseded` are the only permitted transitions, and **RB3 implements no writer for either** (a doctor-decision surface is a future separately approved slice; P6-era). Proposed hardening (D-RB3-05b): a `BEFORE UPDATE` trigger that ABORTs unless the update changes **only** `state`, from `open` to `decided`/`superseded`, with every other column byte-equal; plus a `BEFORE DELETE` trigger that always ABORTs (deletion restriction; run/patient FKs are RESTRICT anyway). The conservative alternative is full UPDATE/DELETE immutability like F1, at the cost of a future trigger-relaxing migration when a decision surface is approved.

### 5.2 `evidence_link`

| Column | Type | Null | Constraints |
|---|---|---|---|
| `id` | TEXT(36) | NOT NULL | PK, UUIDv4 |
| `owner_type` | TEXT(24) | NOT NULL | CHECK IN (`review_item`,`verification_issue`,`summary_claim`) — dictionary enum kept whole; **RB3 writes only `review_item`** |
| `owner_id` | TEXT(36) | NOT NULL | **not an FK** (polymorphic). Integrity: a `BEFORE INSERT` trigger ABORTs when `owner_type='review_item'` and no `review_item` row with that id exists (owner-resolution is checked structurally *and* by the service, which inserts links only for items created/confirmed in the same transaction); referential integrity for the other owner types is left to their future phases (a trigger cannot reference the not-yet-existing `summary_claim` table) |
| `kind` | TEXT(24) | NOT NULL | CHECK IN (`document_span`,`observation`,`checkin_note`) |
| `document_id` | TEXT(36) | NULL | FK `document.id` ON DELETE RESTRICT (proposed; dictionary omits ON DELETE — RESTRICT chosen so evidence can never dangle; F0/F1 precedent) |
| `observation_id` | TEXT(36) | NULL | FK `observation.id` ON DELETE RESTRICT (as above) |
| `page_index` | INTEGER | NULL | CHECK `page_index IS NULL OR page_index >= 0` |
| `char_start` / `char_end` | INTEGER | NULL | CHECK `char_start IS NULL OR char_start >= 0`; `char_end IS NULL OR (char_start IS NOT NULL AND char_end >= char_start)` |
| `created_at` | TEXT(20) | NOT NULL | same injected clock value as its review item |

**Exactly-one-typed-reference CHECKs (dictionary §2.10 made explicit):**

- `kind='observation'` ⇒ `observation_id IS NOT NULL AND document_id IS NULL AND page_index IS NULL AND char_start IS NULL AND char_end IS NULL`.
- `kind='document_span'` ⇒ `document_id IS NOT NULL AND observation_id IS NULL AND page_index IS NOT NULL AND char_start IS NOT NULL AND char_end IS NOT NULL` (span mandatory per `EXTRACTION_PROVENANCE.md` §5).
- `kind='checkin_note'` ⇒ **proposed resolution (D-RB3-05d):** mirror the `observation` shape (`observation_id IS NOT NULL`, document/span columns NULL), matching `EXTRACTION_PROVENANCE.md` §5 ("`observation_id` (the note-bearing record)"). The kind stays in the enum for contract fidelity, but **RB3 never inserts a `checkin_note` link** (no rule in the closed six emits note evidence); it is reserved for future summary/claim consumers under their own approvals. No free-text link, no note copy, no invented payload.

Indexes: `ix_evidence_owner (owner_type, owner_id)` (dictionary). **Proposed hardening (D-RB3-05c):** a UNIQUE **expression** index `ux_evidence_identity` over `(owner_type, owner_id, kind, COALESCE(document_id,''), COALESCE(observation_id,''), COALESCE(page_index,-1), COALESCE(char_start,-1), COALESCE(char_end,-1))` — needed because plain-column UNIQUE cannot deduplicate rows containing NULLs (SQLite treats NULLs as distinct), which would otherwise allow identical duplicate span/observation links per owner. This is an addition beyond the dictionary's index list and is flagged for explicit owner ratification; the fallback is service-level dedupe only (weaker against manual DB surgery).

Immutability: `BEFORE UPDATE` and `BEFORE DELETE` triggers ABORT unconditionally on `evidence_link` (evidence is append-only like F1 blockers).

### 5.3 Referential integrity summary

Patient ownership: `review_item.patient_id` FK RESTRICT + service assertion that item patient == run patient == every referenced observation/document patient (checked in-transaction; cross-patient references are denials, §6.3). Run ownership: NOT NULL FK RESTRICT to a genuine `workflow_run`. Owner resolution: polymorphic `owner_id` guarded by trigger + same-transaction service discipline (no orphan links: links are inserted after and only for their item; items and links commit atomically). Deletion restrictions: RESTRICT on every RB3 FK plus delete-blocking triggers mean neither table can be silently emptied; demo reset remains the only whole-DB rebuild path (dictionary §4/§5.1 semantics unchanged).

---

## 6. (E) Evidence-link mapping for all six rule outputs

### 6.1 RB2 evidence keys → typed persisted links

RB2 flags carry sorted typed keys (`observation:<uuid>`, `document:<uuid>`, `fact:<uuid>`). RB2 fixture references are **not** automatically authorized stored evidence: every key is re-resolved against stored rows in T8 before any link is staged.

| Rule | RB2 evidence keys | Persisted `evidence_link` rows |
|---|---|---|
| DR-001 | `observation:<current>` | 1 × `kind='observation'` |
| DR-003 | `observation:<newest>` | 1 × `kind='observation'` |
| DR-005 | `observation:<baseline>`, `observation:<current>` | 2 × `kind='observation'` |
| DR-006 | `observation:<a>`, `observation:<b>`, `document:<d_a>`, `document:<d_b>`, `fact:<f_a>`, `fact:<f_b>` | 2 × `observation` + 2 × `document_span` (see §6.2) |
| DR-008 | `observation:<first>`, `observation:<second>` | 2 × `kind='observation'` |
| DR-009 | `observation:<current>` | 1 × `kind='observation'` |

All counts stay inside the `ReviewFlag.evidence` 1..8 bound (STATE_AND_GRAPH_CONTRACT). The persisted `dedupe_key` remains RB2's digest over **all** evidence keys verbatim (dedupe identity ≠ link-row projection); replay compares both the key and the exact link set.

### 6.2 `document_span` / `observation` / `checkin_note` semantics resolved

- **`observation`:** a direct reference to one stored, patient-scoped, admissible `Observation` row re-read in T8 (identity, `measure_type`, unit, value, `measured_at`, `trust_level`, `source`, lineage columns all re-verified against the projection used by the evaluator).
- **`document_span`:** the dictionary/EXTRACTION_PROVENANCE representation of a **fact** reference: `(document_id, page_index, char_start, char_end)` copied from the stored `extracted_fact` row — never invented. RB3 additionally re-verifies span resolvability at write time: the persisted `document_page_text` row for `(document_id, page_index)` exists and `text[char_start:char_end] == fact.raw_text` (EXTRACTION_PROVENANCE §5 rule 1). Unresolvable span ⇒ denial. This realizes DATA_DICTIONARY §3.3 rule 6's "evidence_link to the fact + document span" for the RB3 consumer. **Gap flagged for owner ratification (D-RB3-05e):** §2.10 has no `fact` kind; the paired `{document:D, fact:F}` keys therefore consolidate into **one** span link per fact (the bare `document:<id>` key has no span and cannot become a link without fabricating one). The alternative — a new `fact_reference` kind — would deviate from the dictionary and is **not** proposed.
- **`checkin_note`:** resolved in §5.2 — enum retained, constrained to the note-bearing observation shape, **never written by RB3**.
- **Never invented:** no document span without a stored fact row; no source fact without stored `verified` status and a real doctor `fact_verification` decision; no free-text link; no verification decision of any kind is created by RB3.

### 6.3 Post-evaluation stored-evidence proof (T8), including DR-006/DR-008 distinctions

For **every** candidate flag, before staging:

1. Parse each evidence key; malformed/ambiguous keys (RB2 already refuses `|`-containing IDs) ⇒ denial.
2. `observation:` keys ⇒ row exists, `patient_id == run.patient_id`, and the row's stored fields equal the projected input used by the evaluator (no drift between projection and proof).
3. `document:` keys ⇒ row exists, patient-scoped, `extraction_status='verified'`, `sha256` equal to the in-transaction hash, and the document is run-selected (F2 eligibility invariant).
4. `fact:` keys ⇒ row exists, `patient_id == run.patient_id`, `field_name='value'`, `verification_status='verified'`, `document_id` equals the paired `document:` key, and a genuine stored doctor decision exists (`fact_verification` rows by an active doctor, per the read-only provenance lineage checks).
5. **DR-006 — actual source independence vs duplicate evidence:** re-derive from stored rows that the two observations have **distinct** `source_document_id` and **distinct** `source_fact_id`, both `trust_level='doctor_verified'`, both source documents verified and run-selected, equal normalized `measured_at`, values differing beyond the zero tolerance. Same fact/document replayed under two observation IDs is *duplicate evidence*, not independence ⇒ no DR-006; if the evaluator emitted one anyway, proof fails ⇒ denial.
6. **DR-008 — duplicate vs creation-order provenance:** duplicates require two **distinct** stored observation IDs with equal type/value/normalized timestamp (reachable e.g. seed+check-in mixes; two `patient_checkin` duplicates are structurally impossible under `uq_observation_checkin_identity`); out-of-order requires stored `created_at` vs `measured_at` inversion on both rows. Missing/unparseable `created_at` is impossible for stored rows (NOT NULL) — if encountered ⇒ denial, never made-up ordering (R03 semantics preserved).
7. Any proof failure denies the **whole invocation** (fail-closed; no partial persistence).

### 6.4 Run-bound DR-006 reachability finding (explicit, for owner awareness)

Under the **current merged contracts**, a run-bound DR-006 appears structurally unreachable on an F1-PROCEED run: two conflicting doctor-verified document observations at equal measurement timestamps require both source documents in the eligible set (F2 excludes document-derived history whose document is not run-selected), but two run-selected mapped verified documents with differing same-day values re-trigger the recomputed VI-006 (`conflict_tolerance=0`) ⇒ HALT; and the second document's intake/verification would already have been blocked by VI-006 against the first's observation. Consequences for this design: (i) the RB3 DR-006 path is retained **defense-in-depth** — a DR-006 candidate on a PROCEED run indicates gate/eligibility inconsistency and is denied fail-closed (typed `evidence_gate_inconsistency`), never persisted; (ii) this matches RB-18's "DR-006 absent without two real verified sources" and GOLD-D's `expected_source_conflicts: 0`; (iii) making run-bound DR-006 genuinely reachable would require evolving VI-006 semantics or F2 history eligibility — **out of RB3 scope**, recorded as an owner-visible finding, not silently changed. Equal-value duplicates across two selected documents remain reachable and surface as DR-008, not DR-006.

---

## 7. (F) Idempotency, replay and atomicity

### 7.1 Deterministic dedupe from immutable evidence identity

- Item identity: `dedupe_key = sha256(patient_id | rule_id | sorted typed evidence keys | trust_basis)` — computed by the unchanged evaluator over **immutable, already-persisted** identifiers only (stored observation/document/fact UUIDs, patient id), never a newly generated row ID (AGENTS §3.2). The reviewed serialization safeguards are preserved: `_valid_id`'s refusal of `|` and control characters makes distinct evidence sets unable to collide, and RB3 adds no new identifier format.
- Structural guard: `ux_review_dedupe (workflow_run_id, dedupe_key)` UNIQUE — "persisting twice is a no-op" (DEMO_REVIEW_RULES §10.4) is enforced by the database, not by discipline.
- Invocation-level identity: `evaluation_fingerprint_sha256 = sha256(canonical JSON of {contract version, run identity tuple, gate_evaluation_id, gate_input_fingerprint_sha256, bridge_input_fingerprint_sha256, pinned policy identity (version + canonical SHA + lookback), sorted projected rule inputs, sorted result flags (rule_id, reason_code, hint, message, evidence, trust_basis, dedupe_key)})` — deterministic from persisted state; used for audit idempotency and replay bookkeeping.

### 7.2 Scenario semantics

| Scenario | Behavior |
|---|---|
| **Same-run repeated invocation, unchanged state** | Phase 1/2 recompute identically; T9 finds every `(run, dedupe_key)` row with **exact stored-content equality** on (`patient_id`, `rule_id`, `reason_code`, `workflow_hint`, `trust_basis`, `message`, `policy_version`, `dedupe_key`, `state`) ⇒ no INSERTs; evidence-link set re-verified equal (count + identity, incl. spans) ⇒ no INSERTs; audit key recomputes to the existing row (`append_audit_event` returns it, no duplicate); receipt `replayed=True`, created-list empty. `created_at`/row IDs are persistence metadata of the original commit and are excluded from the equality set (documented, mirrors F1 excluding `evaluated_at`) |
| **Concurrent invocation** | Serialized by `BEGIN IMMEDIATE`; the second transaction resolves to the replay path above; a raced INSERT is impossible, and a defensive `IntegrityError` on `ux_review_dedupe` ⇒ rollback ⇒ typed 409, zero partial state |
| **Unique-constraint conflict (manual surgery / forged row)** | Pre-existing row with same `(run, dedupe_key)` but differing content ⇒ **409 `E_IDEMPOTENCY_CONFLICT` "Persisted review evidence changed."**, rollback, existing rows untouched (never UPDATE, never DELETE) |
| **Exact replay vs mismatched persisted content** | Distinguished per-row as above: exact ⇒ no-op; mismatch ⇒ whole-invocation conflict denial; no merge, no supersede, no silent repair |
| **Retry after rollback** | Nothing was committed; a fresh invocation recomputes from persisted state and produces byte-identical rows; deterministic `created_at` from the injected clock keeps even the timestamps stable for a fixed `validation_clock` |
| **Source fingerprint change** (bytes, facts, decisions, manifest, observations) | F1 fingerprint differs from the persisted PROCEED and/or the Phase-1 pin ⇒ stale-evidence denial **before** T9; already-persisted items from an earlier valid evaluation remain immutable (RB3 never rewrites or supersedes them; whether a later legitimate re-evaluation should mark old items `superseded` is a **future** decision-surface question, out of RB3 scope) |
| **Policy-version change** | `run.policy_version` is immutable and pinned; a mismatch denies at Phase 1 (RB1 binding) and again at T4; the proposed structural CHECK (§5.1, D-RB3-05a) makes a divergent row uninsertable |
| **Evidence-link duplication prevention** | Sorted deduplicated link projection per item + same-transaction single insert pass + proposed `ux_evidence_identity` expression index (D-RB3-05c) + replay equality check on the link set |
| **Audit consistency** | One `workflow.review.persisted` audit row (additive namespaced event type) per distinct evaluation fingerprint: `actor=doctor`, `patient_id`, `workflow_run_id`, `subject_type='workflow_run'`, `subject_id=run_id`, `outcome=ok`, `safe_detail` fragments only (`phase=p4-rb3`, `items=N`, `created=M`, `replayed=bool`, `demo_only=true`) — IDs/enums/counts, never message text or clinical content; committed **atomically with** the items and links; replay returns the existing audit row via the derived key |
| **No partial persistence / no orphans** | Single committing transaction (T12) covering items + links + audit; every failure path rolls back (T13); links require their owner row (trigger + ordering); RESTRICT FKs and delete-blocking triggers prevent later orphaning; zero-item evaluations commit only the audit row (deterministic key) and no items |

---

## 8. (G) Migration safety

### 8.1 Actual current head and proposed additive migration

**Verified actual Alembic head: `0007_p5_run_gate`** (inspected: no revision depends on it; `HEAD_REVISION` pins in the smoke script and two test modules agree; post-merge CI ran the upgrade→downgrade→upgrade + smoke gate successfully at this head). Proposed next revision: **`0008_p4_rb3_review_persistence`**, `down_revision='0007_p5_run_gate'`, containing exactly: CREATE `review_item` (§5.1) → CREATE `evidence_link` (§5.2) → indexes (`ix_review_patient_state`, `ix_evidence_owner`, proposed `ux_evidence_identity`; `ux_review_dedupe` inline UNIQUE) → triggers (item update-guard + delete-block; link update/delete-block; link owner-exists insert guard). **No ALTER of any existing table, no data migration, no trigger/FK change to P3/F0/F1 objects.**

- **Upgrade on existing nonempty databases:** pure additive CREATEs; safe over populated P2/P3/F0/F1 rows; verified by a dedicated test that upgrades a seeded nonempty `0007` database (protected F0/F1/P3 rows incl. a historical terminal OPEN VI-002) and asserts full pre-existing-state parity plus the new empty tables.
- **Downgrade/upgrade checks:** `upgrade head → downgrade base → upgrade head` (existing global pattern) plus `0007 → 0008 → 0007 → 0008` targeted cycling on empty new tables.
- **Protection against silent destructive downgrade:** `downgrade()` refuses with a `RuntimeError` when **either** new table contains rows (0006/0007 refusal pattern, message naming both tables and the archive-by-operator-procedure requirement); drops otherwise in FK-safe order (triggers → indexes → `evidence_link` → `review_item`).
- **FK / UNIQUE / CHECK assertions:** new migration tests assert, via `PRAGMA` introspection: `review_item.workflow_run_id` FK → `workflow_run` with ON DELETE RESTRICT and NOT NULL; `patient_id` FK RESTRICT; `ux_review_dedupe` uniqueness (duplicate `(run, dedupe_key)` INSERT aborts); every CHECK of §§5.1–5.2 (retired DR IDs rejected, `demo_only=0` rejected, message bounds, state/hint/trust/kind vocabularies, exactly-one-reference exclusivity per kind, span shape); all four triggers fire (foreign-owner link abort; content-rewrite abort; delete abort; state-only transition accepted iff D-RB3-05b ratified); `PRAGMA foreign_key_check` clean.
- **Required legacy compatibility changes:** none to migration semantics; the compatibility surface is the pinned guard inventory below.

### 8.2 Existing guards that a new head provably trips (exact paths; future owner exceptions required; none weakened, skipped or replaced; none modified in this design PR)

| # | Path | Exact assertion that fails at `0008` | Permitted future change (append/constant-level only) |
|---|---|---|---|
| E1 | `backend/tests/test_database.py` | `HEAD_REVISION='0007_p5_run_gate'` (rev equality assert); `test_migrated_schema_is_exactly_p1_plus_p2_plus_p3` exact head table-set equality; `FUTURE_TABLES` disjointness lists `review_item` | Update the head constant; add the two owner-ratified RB3 tables to the expected union; move `review_item` (only) out of the forbidden set — `summary_draft`/`approval_decision`/`follow_up_task`/`in_app_notification` **stay forbidden**; all historical P1/P2/P3 assertions untouched |
| E2 | `backend/tests/p2/test_p2_migration.py` | `HEAD_REVISION='0007_p5_run_gate'` used at the two head-revision assertions | Update the constant only; every pinned historical-revision assertion (0001/0002/0003/0004/0005/0006 exactness) untouched |
| E3 | `backend/tests/p2/test_p2_scope_guards.py` | `test_p2_tables_still_exist_and_no_later_phase_table_appears`: `Base.metadata.tables` disjoint from `P4_PLUS_TABLES` (lists `review_item`, `evidence_link`) and exact equality with P2∪P3∪F0∪F1 | Move exactly `review_item`/`evidence_link` into a new "owner-ratified P4-RB3 tables" set included in the equality; the remaining later-phase tables (`summary_*`, `approval_decision`, `follow_up_task`, `in_app_notification`, `node_event`) stay forbidden; forbidden-module and forbidden-import guards untouched (`p4_rb3_review_persistence.py` matches no forbidden module name) |
| E4 | `scripts/python/check_alembic_smoke.py` | `HEAD_REVISION` pin; `_expected_tables('head')`; the all-states `P4_PLUS_TABLES` early-table gate | Advance `head` to `0008` with the two new tables + their index/FK/unique/trigger assertions; **add a pinned historical state `p5_f1` = `0007_p5_run_gate`** preserving today's head assertions verbatim (mirrors how `p5_f0` pinned `0006`); `P4_PLUS_TABLES` keeps every non-ratified table; no historical state weakened |
| E5 | `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` | `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` requires the literal adjacent phrase `**N collected**, of which **443** are the P3 suite` with N = live whole-backend collection (current token **1255 collected / 443**); new RB3 tests necessarily raise N | **Only** an append-only, dated, linked note with the newly measured pairing and explicit "collection, NOT passed" wording, and **only after** a fresh standalone owner marker (proposed: `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`); the guard test itself is never edited; historical entries (837/…/1140/1155/1204/1249/1255) never rewritten; prior RB1/RB2 exceptions are **not reusable** |
| E6 | `backend/app/services/p5_run_gate.py` *(conditional, P5 cross-phase)* | Not a test failure: the `inspect_current_run_gate_locked` docstring names the F2 bridge as sole caller, contradicting §3 T3/T11 | **Docstring-only** clarification naming the ratified RB3 write boundary as a second locked caller; zero logic/signature/behavior change; if the owner prefers, D-RB3-02b keeps the file untouched and records the caller extension in append-only contract notes instead |

Also inventoried and **not** tripped (no change requested): `.github/workflows/ci.yml` (steps are head-agnostic; `backend/tests/test_ci_workflow.py` untouched), `scripts/python/check_openapi.py` (no endpoint change ⇒ 17/18/43 stable), `scripts/python/scan_repository.py` (new docs/code avoid claim patterns), P2 API tests asserting `review_items == []` (the P2 service hard-codes the empty list and reads no new table — RB3 adds no API surface), P3 tests/fixtures, RB1/RB2 sources/tests, policy YAML, GOLD expected JSONs.

---

## 9. Exact future RB3 implementation allowlist (proposal — nothing here is authorized yet)

No blanket directory authorization. Each path is listed individually with its requirement, authorizing contract, and frozen prohibitions. **This design PR itself changes only the three docs paths of §12.**

### 9.1 Normal proposed RB3 paths

| # | Path (new unless stated) | Why required | Authorizing contract/requirement | Explicitly prohibited from changing |
|---|---|---|---|---|
| N1 | `backend/app/services/p4_rb3_review_persistence.py` | The §2–§3 write boundary: authorization, pinning, locked revalidation, projection, evaluator call, stored-evidence proof, idempotent persistence, receipt | D-RB-04 (RB3 slice), DEMO_REVIEW_RULES §10.4, DATA_DICTIONARY §§2.9–2.10, TOOL_CONTRACTS §3.7 deferral note | Must not add API/graph/LLM/task/notification imports, run-status transitions, `approval_decision`/summary writes, caller-tunable inputs, or any edit to F0/F1/F2/RB1/RB2 modules |
| N2 | `backend/app/schemas/p4_rb3_review_persistence.py` | Frozen receipt + typed projection/error DTOs with the §3.2 honesty flags | D-RB-04; AGENTS §4 (honest reporting) | No mutable/serializable "clearance" shape; no field implying runtime/graph/clinical authority |
| N3 | `backend/app/db/models.py` (**modified**) | ORM `ReviewItem`/`EvidenceLink` classes exactly mirroring `0008` (required for ORM inserts and head-parity metadata tests) | DATA_DICTIONARY §§2.9–2.10 as hardened by D-RB3-05 | Additive classes + `__all__` only; **no change** to any existing model, column, constraint, index or docstring |
| N4 | `backend/migrations/versions/0008_p4_rb3_review_persistence.py` | §8.1 additive migration with triggers and downgrade refusal | D-RB-04; dictionary §4 ("every later phase adds migrations"); 0006/0007 precedent | No ALTER/DROP of existing objects; no destructive downgrade; no data backfill |
| N5 | `backend/tests/p4/test_p4_rb3_review_persistence.py` | The §10 acceptance matrix (service-level, synthetic SQLite fixtures) | Task §5; DEMO_REVIEW_RULES §12 (RULE-01..08 analogues) | Must not weaken/skip any existing test; no fixture edits outside new files; no network/model/OCR |
| N6 | `backend/tests/p4/test_p4_rb3_migration.py` | §8.1–8.2 migration assertions incl. nonempty-upgrade, refusal-on-nonempty-downgrade, cycle, PRAGMA introspection | AGENTS §7 reversibility; 0006/0007 test precedent | Same as N5; historical migration assertions untouched |
| N7 | `docs/contracts/DATA_DICTIONARY.md` (**append-only**) | An as-built `§2.19 P4-RB3 review persistence (0008)`-style note recording ratified hardenings (CHECK pin, triggers, expression index, checkin_note resolution, DR-006 finding), mirroring the §2.21 F1 precedent | D-RB-04 requires dictionary-anchored schema; owner-reviewed contract amendment rule (F1 design §5) | §§2.9/2.10 original text and every other section verbatim; no retroactive edits |
| N8 | `docs/contracts/TOOL_CONTRACTS.md` (**append-only**) | RB3 internal persistence-interface boundary: not an agent tool, not `evaluate_demo_review_rules` activation, evaluator-core usage note per D-RB3-03, receipt-is-not-a-token | RB1/RB2 append precedent; D-RB-03 | §§3.1–3.10 and prior appended sections verbatim |
| N9 | `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` (**append-only**) | RB3 writes no graph transition; review persistence is not a state-machine event; §7 idempotency table gains a review-persistence row conceptually; two-transaction honesty note | RB1 append precedent; §7.2/§7.3 analogies | §7 tables/rows and all prior content verbatim; no node/edge/status changes |
| N10 | `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_2026MMDD.md` (future date at authoring) | Truthful implementation/test/security report for the RB3 code PR | AGENTS §4 | No fabricated results; explicit executed/not-executed/owner-Windows classification |
| N11 | `docs/phase-reports/PHASE_4_REPORT.md` (**append-only**) | RB3 checkpoint | phase-report convention | Historical sections verbatim |
| N12 | `docs/roadmap/PHASE_PROGRESS.md` (**append-only**) | Owner-decision and execution checkpoints | AGENTS §2 (owner decisions recorded in roadmap) | Historical entries verbatim |

### 9.2 Exceptional cross-phase paths (each requires its own explicit owner authorization, recorded in the roadmap **before** any edit)

E1 `backend/tests/test_database.py`, E2 `backend/tests/p2/test_p2_migration.py`, E3 `backend/tests/p2/test_p2_scope_guards.py`, E4 `scripts/python/check_alembic_smoke.py`, E5 `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`, E6 `backend/app/services/p5_run_gate.py` (conditional docstring-only) — each with the exact permitted delta and frozen prohibitions of §8.2/§3.4. **No other path, for any reason, without a fresh standalone owner PR-thread marker; RB1/RB2/F1/F2 exceptions do not carry over.** If the implementation discovers any further required path: STOP, report, request a new exact-path decision — never edit first.

---

## 10. Acceptance test matrix for the future RB3 implementation PR (requirements — none executed by this design)

All tests run against synthetic migrated SQLite fixtures with an injected clock; no network, model, real OCR, Windows or browser dependency. Failure codes use the existing `ErrorCode` vocabulary (`E_FORBIDDEN`, `E_SCOPE_VIOLATION`, `E_NOT_FOUND`, `E_VALIDATION`, `E_IDEMPOTENCY_CONFLICT`). "Zero writes" always means: no `review_item`, no `evidence_link`, no audit row, no change to any pre-existing row, verified by table dumps.

| ID | Requirement-linked adversarial condition | Expected outcome / failure code |
|---|---|---|
| RB3-01 | Happy path: genuine F0 run (pinned clock), persisted F1 PROCEED, F2/RB1 valid, active assigned-doctor principal, GOLD-D-shaped stored fixture | Items persisted exactly matching the RB2 offline expectation (DR-001/003/005/008/009 set, neutral messages, suffixes, ordering), links per §6.1, one audit row, receipt `replayed=False`, run still `queued`, `runtime_evaluable=False` |
| RB3-02 | No persisted F1 gate evaluation | 409 `E_VALIDATION` denial; zero writes |
| RB3-03 | Persisted F1 HALT (e.g. VI-002) | 409 denial; zero writes; historical VI rows untouched |
| RB3-04 | Persisted F1 UNAVAILABLE | 409 denial; zero writes |
| RB3-05 | Stale F1 PROCEED: source rows changed after the decision | 409 stale-evidence denial (fingerprint mismatch); cached PROCEED never reused |
| RB3-06 | Foreign run (`run.doctor_id != principal.user_id`) | 403 `E_FORBIDDEN`; zero writes; no existence leak beyond the F1 precedent |
| RB3-07 | Foreign patient: patient reassigned (`assigned_doctor_id` changed) after Phase 1 | 403 `E_SCOPE_VIOLATION` inside the write transaction; rollback; zero writes |
| RB3-08 | Revoked session; expired session at `validation_clock` | 403 `E_FORBIDDEN`; zero writes |
| RB3-09 | Foreign/tampered selected document (patient mismatch, SHA/status drift vs manifest) | 409 denial via locked F1 (`Selected document scope changed` / `selected_document_changed`); zero writes |
| RB3-10 | Foreign observation injected into the selection or referenced by a candidate | 409 denial (scope/inadmissible); zero writes |
| RB3-11 | Foreign evidence reference: candidate key naming another patient's document/fact/observation | T8 proof failure ⇒ 409 denial; no link rows |
| RB3-12 | Tampered source bytes between Phase 1 and commit (file swapped on disk) | 409 denial (`source_bytes_changed_during_gate` / fingerprint mismatch); zero writes; post-commit swap documented as undetectable (§3.1) and covered by a consumer-recheck note test |
| RB3-13 | Tampered verification decision (fact un-verified / decision row appended after preview) | Fingerprint mismatch ⇒ 409 denial; append-only `fact_verification` never modified by RB3 |
| RB3-14 | Policy tampering: `run.policy_version` altered; pinned compiled reference mismatch; disabled VI/DR switch attempted | 409 denial at Phase 1/T4; never a fallback default; YAML never loaded by app code (existing guard test stays green) |
| RB3-15 | Clock mismatch: run persisted with `as_of_utc` ≠ `2026-11-14T12:00:00Z` | 409 denial (RB1 pinned-clock binding); zero writes |
| RB3-16 | Zero selected current observations | `no_current_selected` pin; zero review items; audit row with `items=0`; no fabricated DR-001/003 |
| RB3-17 | 7..20 F0-selected current observations | 409 denial (F2 cap); never truncated to 6 |
| RB3-18 | 101 same-patient history rows | 409 denial (provenance/F2 bound); never truncated |
| RB3-19 | Rejected / wrong-unit / future / unparsable-timestamp history rows | Typed exclusions preserved exactly as RB1/F2 recorded; excluded rows never baselines; result equals RB2 offline expectation on the same data |
| RB3-20 | Mixed self-reported and doctor-verified series | `trust_basis` `self_reported`/`mixed` with exact suffixes; **no trust promotion** anywhere in rows, links, audit or receipt |
| RB3-21 | DR-006 fixture-shaped candidate on inconsistent stored state (evaluator emits despite PROCEED) | Denied fail-closed (`evidence_gate_inconsistency`, §6.4); zero writes |
| RB3-22 | DR-006 duplicate-evidence disguise: same fact/document behind two observation IDs | Proof failure ⇒ 409 denial; never persisted as independence |
| RB3-23 | DR-006 with one fixture-asserted-only source (no stored doctor decision) | Stored-lineage proof failure ⇒ denial; no `verified` label invented |
| RB3-24 | DR-008 duplicate: two distinct stored observation IDs, equal type/value/timestamp (seed+check-in mix) | One item, two `observation` links; message/hint exact |
| RB3-25 | DR-008 creation-order inversion (later `created_at`, earlier `measured_at`) | One item persisted; missing `created_at` path asserts denial-by-impossibility (NOT NULL stored rows) |
| RB3-26 | `checkin_note` links | Zero rows of that kind ever written by RB3 (dump assertion) |
| RB3-27 | Exact same-run repeated invocation | Byte-identical rows; no new item/link/audit; receipt `replayed=True`; zero side effects |
| RB3-28 | Concurrent double invocation (two sessions/threads) | Exactly one persisted set; loser replays or gets typed 409; `ux_review_dedupe` never violated; no orphan links |
| RB3-29 | Replay against mismatched persisted content (row surgically altered — triggers bypassed only in a raw-SQL fixture) | 409 `E_IDEMPOTENCY_CONFLICT`; zero writes; existing rows untouched |
| RB3-30 | Partial write failure injection (link INSERT forced to fail mid-transaction) | Full rollback: zero items, zero links, zero audit; deterministic retry then succeeds whole |
| RB3-31 | Forced unique-constraint conflict on `(run, dedupe_key)` | IntegrityError handled ⇒ rollback + 409; no partial state |
| RB3-32 | Retry after rollback | Identical recomputation; final state exactly one copy |
| RB3-33 | Source fingerprint change after first successful persistence | New invocation denied (stale); previously persisted items remain immutable; no silent supersede |
| RB3-34 | Evaluator cap overflow (>3 items per type constructed) | `E_RULE_POLICY_INVALID` typed denial; zero rows; never truncated |
| RB3-35 | Malformed projection input (ambiguous `|` IDs, bad decimals, year-one timestamps) | RB2 R06/R07/R08 protections fire through the persistence path: typed failure, zero rows |
| RB3-36 | Fresh-DB migration: `upgrade head` | Head = `0008_p4_rb3_review_persistence`; all §5 objects/triggers/indexes exist per PRAGMA; `foreign_key_check` clean |
| RB3-37 | Migration from the **genuine existing head**: seeded nonempty `0007` DB (F0/F1/P3 rows incl. historical terminal OPEN VI-002) upgraded to `0008` | Additive only; every historical row/table/index/trigger byte-identical; new tables empty; downgrade→upgrade cycle clean on empty new tables |
| RB3-38 | Nonempty-data downgrade safeguard | `downgrade 0007` with review/evidence rows present raises; rows preserved; after operator-style clearing (test-only deletion via raw SQL with triggers dropped in a scratch copy), downgrade succeeds and re-upgrade restores |
| RB3-39 | FK integrity: fake `workflow_run_id`; delete run/patient/document/observation under items/links | FK/NOT NULL/RESTRICT aborts; no orphans constructible through the ORM |
| RB3-40 | CHECK battery: retired `DR-002/004/007/010`, `demo_only=0`, >240-char message, bad state/hint/trust/kind, dual-reference link, span-less `document_span` | Each rejected structurally |
| RB3-41 | Historical preservation: P3 `verification_issue` rows (incl. OPEN VI-002 with R21-S1 omission), F1 gate rows/triggers, F0 manifest, run status | All unchanged after every RB3 scenario (dump equality); no auto-resolution anywhere |
| RB3-42 | R01–R08 regression protection: existing RB2 offline suite green **unmodified**; RB3-vs-RB2 output-equivalence tests on shared synthetic fixtures (incl. GOLD-D replay through the DB path) | Identical rule IDs, evidence keys, dedupe keys, messages, ordering; zero RB2 source diffs |
| RB3-43 | No activation: static + runtime assertions — no new API route/OpenAPI delta (17/18/43 stable), no graph/LLM/agent imports (scope guards green), no task/notification/approval/summary/node_event rows, run status `queued` throughout, scanner green | All hold in every scenario |
| RB3-44 | GOLD-EX-11 truth preservation | No test, fixture or doc in the RB3 PR claims OCR glyph fidelity or reclassifies `GOLD-EX-11`; byte-SHA equality language only |

**RB4 separation (explicit):** run-backed GOLD A/B/C/D **final acceptance** — real end-to-end F0→F1→F2→RB1→RB3 replays as phase-level evidence, owner Windows gates and the P4 acceptance decision — is **RB4**, separately scoped and separately ratified. Nothing in this matrix executes or claims RB4; RB3-01/42 are implementation-PR regression tests, not phase acceptance.

---

## 11. Explicit owner decisions requested (no approval assumed)

| ID | Exact question | Relevant existing contract | Alternatives | Recommended | Safety / engineering trade-offs | Exact scope of the proposed authorization |
|---|---|---|---|---|---|---|
| **D-RB3-01** | Approve the internal service boundary of §2.1 (five server-owned parameters; no API/agent/graph surface; structurally impossible caller evidence/policy/clearance inputs)? | D-RB-04; TOOL_CONTRACTS §3.7 deferral; THREAT_MODEL T-01 | (a) as specified; (b) additionally expose a doctor HTTP endpoint now | **(a)** | (b) would pull P6 UI/API scope into P4 and enlarge the attack surface before RB4 evidence | RB3 internal write service only; no endpoint, no tool registration |
| **D-RB3-02** | Approve the four-transaction sequence of §3 (RB1 pin → single committing `BEGIN IMMEDIATE` write transaction with locked F1 revalidation, comparison re-derivation, pre-commit recheck) and the honest non-atomicity statements? Sub-decision **D-RB3-02b**: permit the docstring-only E6 note, or keep `p5_run_gate.py` untouched with a contract-note-only caller extension? | D-RB-02 snapshot caveat; F1/F2/RB1 patterns; STATE_AND_GRAPH §7.2 | (a) as specified; (b) single-transaction design skipping the RB1 pre-read (loses `first==last` drift detection and the reviewed 90-day pin); (c) refactor a shared locked projection out of F2 (P5 logic change — larger exception) | **(a)**; E6 docstring-only note preferred over a stale docstring | (a) maximizes reuse of reviewed read-only checks at the cost of one extra pre-read; (b) is leaner but weakens drift detection; (c) touches accepted P5 logic | One future RB3 code PR per §9; E6 limited to one docstring paragraph, zero logic |
| **D-RB3-03** | Approve evaluator boundary **Alt A2** (unchanged RB2 evaluator as pure computation core; documented `fixture_asserted` label bridge for stored-verified rows; mandatory independent in-transaction stored-lineage proof; equivalence tests; append-only tool-contract note)? Or **Alt B** (RB3-owned stored-input derivation with `stored_independently_verified` internal state + equivalence tests)? | TOOL_CONTRACTS RB2 sections ("test-invoked pure function"; `stored_independently_verified` = future RB3 server-side state); D-RB2-01/02; RB2 review R05 | A2 / B / C (modify RB2) | **A2** with conditions (i)–(v) of §4.3; **C rejected** | A2: single reviewed core, R01–R08 inherited, zero RB2 diffs; cost: the label bridge must be documented honestly (a fixture label on proven-stored rows) — mitigated because persisted links and proofs reference only real stored evidence. B: clean labels; cost: duplicated rule logic and divergence risk. Neither weakens the pinned clock/policy/validation; neither treats RB2 output as clearance | RB2 source/schema/tests remain frozen under both; the chosen option binds the RB3 implementation PR's evaluator boundary and its equivalence-test obligation |
| **D-RB3-04** | Approve the clock/policy binding: persistable runs are exactly those with immutable `as_of_utc = 2026-11-14T12:00:00Z` and `policy_version = demo-policy-1.1.0`; all other runs deny typed? | DEMO_REVIEW_RULES §7; RB1 binding; R3-A | (a) as specified; (b) accept any run clock by generalizing RB2 (weakens the pinned clock — prohibited here); (c) reject clock binding and persist with the run clock while RB2 stays pinned (incoherent) | **(a)** | (a) keeps demo determinism and RB2 pinning intact; cost: only pinned-clock synthetic runs are persistable — exactly the academic scope. Generalization = future `policy_version` bump + fresh owner decision, never an RB3 side effect | No change to RB2 pinning; no wall-clock introduction; future clock policy deferred |
| **D-RB3-05** | Ratify schema hardenings: (a) structural CHECK `policy_version='demo-policy-1.1.0'`; (b) column-guarded state-transition trigger (state-only `open→decided/superseded`) vs full immutability; (c) `ux_evidence_identity` UNIQUE expression index; (d) `checkin_note` constraint resolution + RB3 never writes it; (e) fact references consolidated into span-verified `document_span` links (no new kind, no fabricated spans)? | DATA_DICTIONARY §§2.9–2.10, §3.3 rule 6; EXTRACTION_PROVENANCE §5; D-RB-04 | Per sub-item as listed in §5 | **(a) yes, (b) column-guarded trigger, (c) yes, (d) yes, (e) yes** | (a) makes policy drift a deliberate migration; (b) preserves a future decision surface without a trigger-rewrite migration while blocking content edits; full immutability is stricter but costs a later migration; (c) closes NULL-distinctness duplication at the cost of one non-dictionary index; (d)/(e) keep the dictionary whole without inventing payloads | Additive `0008` content only; dictionary amended append-only (N7) to record the as-built ratification |
| **D-RB3-06** | Pre-plan the exact exceptional paths E1–E5 (+conditional E6) with the deltas of §8.2, each still requiring its own fresh standalone marker in the RB3 PR thread before editing (proposed collection marker: `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`)? | D-RB-04 ("pre-plan a later exact owner path exception"); RB1/RB2 exception precedents | (a) pre-plan as specified; (b) leave entirely unplanned (guaranteed mid-PR STOP cycles) | **(a)** | Pre-planning removes ambiguity but authorizes nothing by itself; every edit still needs its own verified marker; no guard weakened | Roadmap-recorded list of candidate exception paths and their frozen prohibitions; **not** permission to edit any of them yet |
| **D-RB3-07** | Approve receipt honesty flags, the additive audit event type `workflow.review.persisted` (fingerprint-keyed, committed atomically, `items=0` audited, denials not audited inside the rolled-back transaction per F1/F2/RB1 precedent)? | AGENTS §3.2/§4; audit module conventions; DATA_DICTIONARY §2.17 | (a) as specified; (b) also commit denial audits via separate sessions (new machinery, scope growth); (c) skip zero-item audits | **(a)** | (a) is consistent with every accepted predecessor; (b) adds a committed-denial path none of F1/F2/RB1 has; (c) loses evidence of completed zero-item evaluations | Audit vocabulary extended additively; no existing event semantics changed |

**Recorded finding requiring no decision but owner awareness:** §6.4 run-bound DR-006 unreachability under current F1/F2/VI-006 contracts (RB3 denies any DR-006 candidate fail-closed; reaching it genuinely would be a future contract evolution outside RB3).

### 11.1 Proposed exact owner ratification marker

If and only if D-RB3-01..07 (with the recommended options, or revised options after a design amendment) **and** the §9 allowlist split (N1–N12 normal paths; E1–E6 exceptional paths) are accepted, the owner posts **exactly** in this design PR's Conversation:

`RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE`

**Marker meaning (bounded):** ratifies this design as the RB3 roadmap and authorizes **only one** future separate P4-RB3 implementation PR confined to §9.1 paths (plus individually marker-approved §9.2 exceptions), **conditional on** the owner reviewing/merging this docs-only PR and exact merged-main CI SUCCESS being independently verified first. The marker does **NOT** authorize: full P4 acceptance or PASS; RB4 run-backed GOLD acceptance; runtime policy activation beyond the bounded demo persistence service; any graph, LLM, API, UI, task, notification, approval-decision or summary activity; `review_item` state-transition writers; clinical use; issue #14 closure; or any agent merge. Any disputed decision requires revising this docs PR and a fresh marker. The marker's comment URL, author, timestamp and boundaries must be recorded append-only in `docs/roadmap/PHASE_PROGRESS.md` before the implementation branch starts.

## 12. This PR's scope, procedure and rollback

**Exactly three files (docs-only):** this new design; append-only `docs/phase-reports/PHASE_4_REPORT.md` checkpoint (RB2 owner acceptance + merged-main evidence as a historical checkpoint, and this proposal); append-only `docs/roadmap/PHASE_PROGRESS.md` checkpoint. **No** contract, application source, test, fixture, model, migration, dependency, CI or scanner change — if implementation later shows another path is required, that PR must STOP and request it explicitly (§9.2 rule).

**Procedure:** owner reviews this draft; posts D-RB3 decisions and (if accepted) the exact marker **in this PR's Conversation**; the marker is independently verified (author/body/timestamp) and recorded append-only in the roadmap **on this branch before merge**; CI is re-checked on the final docs head; owner alone marks Ready for review and merges; exact merged-main CI SUCCESS is independently verified before any RB3 implementation branch. **Rollback:** close this draft PR unmerged — zero database, source, fixture or policy impact.

**Evidence classification for this session.** *Executed here:* the §0 GitHub/git verifications (exact commands and outputs reproducible from the PR thread) and full read-inspection of the merged contracts and sources listed in §1. *Not executed here:* no Python/pytest/Ruff/Alembic/frontend run (this is a design PR; the merged-main CI SUCCESS of §0 is the operative gate evidence), no RB3 code, no migration, no Windows gate, no real OCR. *Design reviewed ≠ executed.* No test outcome in §10 is claimed as run.

**Unchanged invariants:** R1-A (no fake run parent, no weakened FK); R2-A/C-35A/C-37A; R3-A reference-only policy; R4 offline GOLD; R21-S1; F1/F2 freshness and non-clearance semantics; RB2 offline-only acceptance; P4 **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**
