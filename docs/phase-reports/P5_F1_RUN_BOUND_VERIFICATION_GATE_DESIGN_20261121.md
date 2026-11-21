# P5-F1 — Run-bound verification gate: bounded design for owner decision

**Status: PROPOSAL / DESIGN ONLY / NOT APPROVED / NO P5-F1 CODE.** Date: 2026-11-21.
**Repo base:** `main@6f90c8d1308424a9c0d8efcc84a5fc5389e5d937` after owner-merged [PR #31](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31); exact-main [Actions #44920665782](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44920665782) Backend+Frontend COMPLETED SUCCESS. The owner Windows PR-head gate reported 12 PASS / 0 FAIL / 1 optional Playwright SKIP. Those are **F0** results, **not evidence of F1**.
**Safety:** EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE. Historic real P3 `GOLD-EX-11 = FAIL / NOT PROVEN` (source glyph `1O5` read as `105`) remains unwaived.

## 1. Decision sought; sequencing

[CH-01](P4_P5_CONDITIONAL_HANDOFF_20261121.md) ratified an exception **only for F0**, not F1. Owner's instruction to *prepare* F1 permits this docs-only proposal, not code, phase acceptance, a new runtime verification permission, or a merge by the agent. P4 remains `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN. This PR has **no application, migration, test, CI workflow, or policy change**.

**Proposed next code slice, only after separately recorded explicit owner approval and a merged/green docs decision:** an internal-only `P5-F1` deterministic gate evaluating persisted F0 run selection against current stored patient/doctor evidence, emitting a durable typed run-specific decision and honest provenance. **No graph execution, LLM, DR rule evaluation, P4 review-item persistence, approval, task, notification, patient messaging, P6 UI, public endpoint, or source glyph validation claim.**

## 2. Current source-grounded inventory / problems to solve

- F0 `backend/app/services/p5_run_foundation.py` persists `workflow_run` (initially `queued`), immutable `run_selected_document`, `run_selected_observation`, `run_source_omission`, and a run audit event. Initial receipt always reports `run_gate_status=unavailable`, `run_gate_completed=False`, `runtime_evaluable=False`. Selection SHA comes from stored metadata only; no source-file bytes verified at run start.
- F0's replay key uses stable patient, workflow version, sorted selected IDs and request ID; F1 must not use a newly generated gate row ID as an idempotency input. Duplicate simultaneous F0 start and read-to-write TOCTOU have not been independently proven safe; do not pretend F1 fixes F0 concurrency.
- R21 `inspect_offline_recovery_selection` validates scope/lineage/omission shape and intentionally returns `empty_selected_source_set` when no document is chosen. **Observation-only runs are not currently startable through F0** even if observations are present; F1 must not silently broaden F0. Record an independent future decision if observation-only is desired.
- Existing `p4_document_preflight` validates selected document, active/corrected fact status, actual doctor decision, patient reference, open P3 issues, but explicitly is **not** a run eligibility gate or source file attestation.
- P3 `documents/issues.py` implements pure VI-001..006 intake helpers; `verification_issue` has document-level `ux_vi_document_type` and nullable run FK. A naive per-run issue insert keyed by selected document collides with / repurposes historical P3 entries. F1 must keep original document issues and historical terminal `VI-002` untouched.
- `TOOL_CONTRACTS.md` section 4 specifies the future pure `collect_verification_issues` deterministic service, not an agent tool, using candidate facts, patient/document reference and admissible observations. `STATE_AND_GRAPH_CONTRACT.md` N2 describes `fact_verify_gate`, but **F1 must not implement N2 graph transitions** before separate authorization.
- A source SHA/hash match confirms bytes match a file identity; it **never** proves the OCR's original glyph or doctor's understanding. P3 real `GOLD-EX-11` remains FAIL / NOT PROVEN regardless of an F1 unit test.

## 3. Proposed internal F1 interface (contract sketch, not implemented)

`evaluate_run_verification_gate(db, *, principal: Principal, run_id: str, validation_clock: aware UTC, upload_root: configured trusted root) -> RunGateReceipt`.

- **Server-owned inputs:** `run_id` selects the stored run and its immutable manifest. The caller cannot supply `document_ids`, `observation_ids`, `blocking_fact_count`, historical omission flags, `gate_proceed`, `verified_fact_count`, `policy_version`, `patient_id`, or claimed doctor identity. Stored F0 `as_of_utc` remains the immutable evaluation time for facts/rules; request-time injected clock only validates active session and guards freshness, never silently changes the run clock.
- **Active identity/scope:** load persisted, unrevoked doctor `UserSession`; require active doctor account, current assigned synthetic patient, and `WorkflowRun.doctor_id == principal.user_id`. Validate stored run's policy, mapping, workflow, schema versions (no runtime policy activation).
- **Output (proposed strict frozen type):** `run_id`, `patient_id`, `doctor_id`, `gate_version`, `input_fingerprint_sha256`, `decision ∈ {proceed, halt, unavailable}`, sorted `VI-001..006` issues + reason codes + ID refs/counts, `historical_excluded_vi002_ids`, `gate_evaluated` and `runtime_evaluable=False` always in F1. Typed neutral messages ONLY from approved VI templates. No raw OCR/page text, free-text trace or severity/clinical score.
- **Decision:** `PROCEED` only if *all* selected inputs independently pass the complete run-bound verification in a stable snapshot with no unresolved selected blockers; `HALT` on an identified blocker; `UNAVAILABLE` on inability to prove completeness/integrity (missing upload/DB inconsistency/lock conflict/unsupported version). Both non-PROCEED outcomes fail closed. Empty selections are ineligible. No downstream DR or graph invocation even on PROCEED; later F2 must re-check fingerprint and independently authorize runtime consumption.
- **Lifecycle:** propose a separate gate receipt instead of mutating F0's immutable receipt. `PROCEED` may leave the app-DB run `queued` for the later F2 transition; a determinate `HALT` can record `needs_verification` only after a separately approved state-machine rule. The app DB, never checkpoint/client, is authoritative.

## 4. Verification order and strict eligibility

1. Refuse dirty SQLAlchemy sessions and arbitrary caller-supplied "already verified" values. Authenticate actual stored session/doctor/assigned synthetic patient; load exact run and immutable manifest with scoped joins; ensure no unexpected extra/duplicate rows or missing referenced records. Retain one explicit injected clock and immutable run clock.
2. Start a deterministic fenced SQLite read/write transaction (design candidate: `BEGIN IMMEDIATE` or equivalent documented lock policy). Serialize canonical row selections and validate `workflow_run` version/status. Re-evaluate scope and doctor assignment within that transaction; a concurrent change must not grant clearance.
3. For each selected doc: check `Document.patient_id`, identity reference, extraction status and failure, selected stored SHA vs current document metadata, the stored file's actual safe-path size and SHA-256 where available. Missing, replaced, unsupported or unreadable file -> **no PROCEED**. File inspection is NOT a clinical glyph/OCR validity proof. Recheck byte integrity near gate commit; note filesystem bytes cannot participate atomically in SQLite and F2 MUST validate fingerprint again.
4. Reconstruct every selected document's *active* fact set; retain rejected superseded originals for provenance but exclude them only if valid doctor-recorded correction lineage exists (D-14). Validate exact doctor verification decision, mapping, admissible source provenance, selected open P3 issues, and absence of unaccounted/multiple measurement tuples. Never treat a successful OCR parser output as doctor verification.
5. Recompute each VI from authoritative selected evidence, not merely count stored issues:
   - **VI-001:** missing/unsupported measurement unit;
   - **VI-002:** pending/rejected *active* fact or multiple measurement candidates (`multi_measurement_document`);
   - **VI-003:** missing or ambiguous report date;
   - **VI-004:** wrong/missing patient reference;
   - **VI-005:** unreadable/OCR-corrupted or flagged low-confidence value;
   - **VI-006:** conflict with current eligible, same-patient same-day mapped observation under *existing approved synthetic intake predicate*, never made-up tolerance, conversion or medical inference.
   Existing P3 `collect_*` helpers can be reused as pure functions, but no P3 status/issue writers or new policy values are authorized by this design.
6. Validate every selected observation: same patient, same stored ID and F0 manifest trust/created-at/source-fact reference, acceptable `validation`, fixed measure/unit, parseable timestamp (≤ stored run `as_of_utc + 5 min`), `trust_level` coherent with source/verification lineage. **`self_reported_validated` is admissible and remains visibly self-reported; it must never become `doctor_verified`.** Reject silently changed trusted source or selected observation; do not quietly drop one to make PROCEED.
7. R21-S1 recovery: a terminal rejected original selected directly or alongside replacement -> HALT. Separately selected recovery may qualify only if independently verified and each excluded terminal ancestor has its persisted doctor-authored F0 omission bound to the exact open blocking original `VI-002`, with same patient/doctor/lineage and no hidden chain/cycle/duplicate. Its historical original `VI-002` **stays OPEN**; omission is not a clearance or evidence of equivalence.
8. Build bounded typed outcome with exact selected fingerprint and server-derived count. Serialize audit/immutable decision in the same DB transaction. If any source/assignment/issue/trust/version changed between checks, abort to HALT/UNAVAILABLE, no PROCEED. On replay, return original decision only if the same fingerprint is still fresh; otherwise fail closed without falsely reusing an old clearance.

## 5. Durable gate provenance — schema decision needed BEFORE coding

**Recommended proposal, not ratified:** an additive `0007_p5_run_gate` migration with append-only `run_gate_evaluation` (FK to `workflow_run`, bounded contract version, fingerprint SHA-256, decision, run versions, injected clock, deterministic idempotency key) plus `run_gate_blocker` (FK gate receipt, VI enum, reason code, bounded source IDs, P3 issue reference where relevant). Exactly one committed matching decision per `(run_id, fingerprint, gate_version)`; enforce unique constraints, ON DELETE RESTRICT and update/delete immutability guards, reversible only on empty/downward-safe state. The full typed source digest/snapshot definition, time semantics and proof of no untracked source rows must be specified in approved design before implementation.

**Why a separate record is recommended:** pre-run `verification_issue` already owns historic document issues and unique `(document_id, issue_type)`, and P5-F0's `workflow_run` has no durable gate-outcome or input-fingerprint columns. F1 must not repurpose/resolve existing P3 issues or infer latest gate eligibility from `run.status` alone. Contract/schema additions to `DATA_DICTIONARY.md` and `STATE_AND_GRAPH_CONTRACT.md` require explicit owner-reviewed amendment (not silent implementation).

**Open D-F1-01:** owner to ratify whether dedicated append-only gate tables are acceptable, or require a bounded alternative compatible with the existing `verification_issue` lifecycle. No code until this is settled.
**Open D-F1-02:** owner to ratify precise `queued`/`needs_verification` state transition / replay semantics for F1-only (no N2 graph yet).
**Open D-F1-03:** owner to decide observation-only path separately; default is **out of scope**, retain F0 no-document prohibition.

## 6. Synthetic acceptance matrix (all *planned*, none executed for F1)

| Case | Expected |
|---|---|
| F1-01: stored assigned doctor, verified selected doc, sound actual bytes, no VI | PROCEED *for synthetic internal gate only*, `runtime_evaluable=False` |
| F1-02: selected pending/plain rejected fact | HALT VI-002; no DR |
| F1-03: corrected original with documented valid replacement | superseded original excluded from *active* VI-002 count only |
| F1-04: missing/unsupported unit; ambiguous date; OCR flag/low confidence; wrong patient ref; conflicting same-day reading | respective VI-001/003/005/004/006, HALT; all six VI categories independently exercised |
| F1-05: selected terminal original, both original and recovery, or missing doctor omission | HALT; original OPEN VI-002 preserved |
| F1-06: selected *verified* recovery with audited omission and original OPEN VI-002 | eligible if ALL other checks pass; historical VI-002 remains OPEN |
| F1-07: missing/replaced file, SHA mismatch, changed document metadata, stale fact/verification/issue/assignment/version | HALT/UNAVAILABLE; never old PROCEED replay |
| F1-08: wrong role, expired/revoked session, cross-patient document/observation/ancestor | deny, no persisted authorization or P3 issue mutation |
| F1-09: rejected observation, wrong unit, unparseable/future time, trust/source mismatch | HALT/UNAVAILABLE, not silently excluded |
| F1-10: valid selected patient check-in | admissible with `self_reported_validated` label, never impersonates doctor |
| F1-11: duplicate request, concurrent gate attempts, lock/rollback failure | one durable decision/audit; no duplicate or partial PROCEED |
| F1-12: empty source set, excessive facts/docs/issues, invalid source file, malformed provenance | fail closed without truncation |
| F1-13: GOLD-A/B/C/D and negatives rechecked at F1 boundary | exact expected synthetic gate outcomes; no P4 review persistence |
| F1-14: original real OCR GOLD-EX-11 1O5→105 | report as historic FAIL/NOT PROVEN, never marked detected/validated by F1 |
| F1-15: migration 0007 up/down/up, FK/check/index/immutability/old-state parity | strict assertions; original P3/F0 data preserved |
| F1-16: no graph/LLM/API/P6/task/notification/DR output, no external egress | static and runtime absence assertions |

Exact-head GitHub Backend+Frontend CI and isolated owner Windows PowerShell 5.1 `setup.ps1` + `test_all.ps1` are mandatory for the *future* code PR. Optional Playwright SKIP is not PASS; actual OCR/GOLD-EX-11 remains a separate unresolved real-world deviation.

## 7. Proposed future **code** PR allowlist — NOT AUTHORIZED YET

After design decisions and written owner approval, create a **new branch from the then-current green `main`**; never add code to this docs PR.

- `backend/app/services/p5_run_gate.py` — new internal deterministic run-bound gate only.
- `backend/app/db/models.py` and `backend/migrations/versions/0007_p5_run_gate.py` — **only if D-F1-01 is ratified** for the exact schema.
- `backend/tests/p5/test_p5_run_gate.py` and `backend/tests/p5/test_p5_run_gate_races.py` — proof matrix above.
- `docs/contracts/DATA_DICTIONARY.md`, `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` — **only for owner-reviewed contract amendments**, with precise migration/typed-output design; possible ADR in `docs/decisions/**` if accepted.
- `docs/phase-reports/P5_F1_IMPLEMENTATION_REVIEW.md`, `docs/roadmap/PHASE_PROGRESS.md` — traceability/observed gates.

**Explicitly excluded:** editing existing P3 issue/verification/OCR logic, changing P4 rule policy, adding endpoints, touching frontend or LangGraph/LLM, enabling review items/DR, closing P4, marking P5 PASS. Scope changes require a separate exact-path owner decision.

## 8. Owner decision workflow (no self-ratification)

1. Review this **docs-only** draft and D-F1-01/02/03 against immutable F0, P3 historical VI, `AGENTS.md`, `DATA_DICTIONARY.md`, `DEMO_REVIEW_RULES.md`, `TOOL_CONTRACTS.md` and `STATE_AND_GRAPH_CONTRACT.md`.
2. If adopting the bounded F1 scope **including the recommended separate gate-evaluation store, conservative status semantics, and observation-only exclusion**, owner posts the exact marker **`RATIFY-P5-F1-BOUNDED-RUN-GATE-SCOPE`** in this PR *Conversation*. This approves only preparation of a separately reviewed F1 code PR after docs merge and main CI; it is NOT code acceptance or permission for F2/agent runtime.
3. Record the owner decision **append-only** in `docs/roadmap/PHASE_PROGRESS.md` before or with docs merge, not by agent inference; if any D-F1 item is rejected, revise the design and request a more precise marker. The owner alone moves docs PR out of Draft and merges.
4. Reconfirm exact-main CI SUCCESS; then implement F1 in its own one-phase PR, execute all synthetic tests and owner Windows, and request independent review. **P4 IN_REVIEW, P5 not accepted, NOT FOR CLINICAL USE** throughout.

### Evidence classification
- **Read/inspected in this design session:** merged PR #31, exact merge SHA/postmerge CI, CH-01, existing F0 service/models/migration/tests, R21 selection inspector, P4 preflight/evidence inspection, P3 pure issue helpers, demo VI catalogue, source integrity helper and state/tool/data contracts.
- **Executed in this design session:** GitHub reads and this documentation-only branch/PR, if opened. **NOT executed:** F1 code, migration, F1 test, Windows or real OCR; no claimed F1 implementation or F1 PASS.
