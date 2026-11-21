# P4 → P5 Conditional Handoff — dependency-breaking decision for owner ratification

**Date:** 2026-11-21  
**Status:** OWNER REVIEW REQUIRED / DESIGN ONLY / NO P5 CODE AUTHORIZED BY THIS PR  
**Repository baseline:** [PR #29](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/29) owner-merged to `main@e01250dd393fdd639bed65cee298beb8ecc33b1b`; [postmerge CI #44912202066](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44912202066) completed SUCCESS (Backend and Frontend).  
**Tracking:** [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains OPEN.  
**Evidence of direction:** On 2026-11-21, after PR #29 owner merge, the owner agreed in chat to **prepare the P4-to-P5 Conditional Handoff design PR**. This authorizes **documenting and submitting the proposal**. Per [AGENTS.md](../../AGENTS.md) §§1–2, a **separate explicit owner ratification in this PR conversation and a merged roadmap decision** are still required before any sequencing/file-scope exception can take effect.

**SCOPE LIMIT:** Local, synthetic, academic application only; **NOT FOR CLINICAL USE**. P3 real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN** (source glyph `1O5` read as `105`); no acceptance, waiver, retest or alteration is claimed.

## 1. Decision problem and existing verified foundation

- [MASTER_PLAN.md](../roadmap/MASTER_PLAN.md) says P5 depends on an accepted P4, while [DATA_DICTIONARY.md](../contracts/DATA_DICTIONARY.md) §2.9 defines `review_item.workflow_run_id` as **NOT NULL FK** to the `workflow_run` object planned for P5 (§2.16). P4-3 cannot persist a valid review item while this parent identity is absent. This is a **real dependency cycle**, not a reason to declare P4 PASS.
- The previously owner-selected **R1-A** deliberately defers `review_item` / `evidence_link` persistence until a **genuine P5-owned** `workflow_run`. It explicitly prohibits fake run IDs, a nullable/weakened FK and prematurely fabricated P5 graph state. **R1-A is retained.**
- Owner-approved R2-A / C-35A / C-37A cover read-only internal evidence inspection, pure explicit comparison and a *future* typed run-bound evidence interface. R3-A pins an **offline-only synthetic** `demo-policy-1.1.0` reference. R4 covers GOLD A/B/C/D *component* replay; R21-S1 covers offline source-selection/omission **shape** checks, NOT an audited doctor selection.
- Already implemented P4 services/tests remain **non-evaluable at runtime**: `run_gate_completed=False`, `runtime_evaluable=False`, `run_gate_status=unavailable`, and R21-S1 `doctor_selection_audited=False`. None may be recast as a P5 clearance by adapter code. No actual `workflow_run`, durable run source-selection manifest, source-byte attestation or full run-scoped VI gate is proven by PR #29.
- Existing P3 conditional acceptance is **synthetic educational only**, not a claim of clinical/OCR correctness.

**Proposal CH-01:** Permit a *narrow phase-sequencing exception* to build the minimum honest P5 run-identity foundation **before full P4 acceptance**, then return to P4's run-bound integration/acceptance using that foundation. P4 remains **IN_REVIEW** throughout. This exception **does not permit arbitrary P5/P6 advancement**, authorize clinical use, approve actual DR runtime activation, or relax doctor-in-the-loop and fail-closed invariants.

## 2. Ratification and scope control (hard gates)

1. **This PR is documentation only**. The owner must review the exact changed files, explicit risks, and postmerge CI; then post the unambiguous decision `RATIFY-P4-P5-CONDITIONAL-HANDOFF-FOUNDATION-ONLY` in **this PR thread** and merge this documentation to `main`. Without both, CH-01 is **PENDING**; no P5 branch/code authorization is inferred from chat alone.
2. The narrowly proposed exception affects **only** [AGENTS.md](../../AGENTS.md) §1 phase ordering and §5 file-scope *for the specifically named P5 foundation PR*. It does **not** amend §2 (no agent merge/self-approval), §3 (medical/safety), §4 (no invented test claims), or existing R1-A / R2-A / C-35A / C-37A / R3-A / R4 / R21-S1 limitations. Future code must still be **one phase per branch/PR**.
3. The first authorized code slice after ratification is **P5-F0 (run foundation)** only, on its own `feat/p5-run-foundation` branch from a pinned passing `main`. The proposed P5-F0 path-family exception is narrowly limited to `backend/app/db/**`, `backend/alembic/**` (verify actual migration directory before editing), `backend/app/services/**` for run-specific persistence, `backend/app/schemas/**` for internal run types, `backend/tests/p5/**`, and P5-specific reports/roadmap; exact file allowlist must be declared in the P5 PR **before** implementation. No `backend/app/agents/**` or `backend/app/llm/**` in P5-F0. No P4 files or P6 UI changed in that PR.
4. Stop if a new migration contradicts [DATA_DICTIONARY.md](../contracts/DATA_DICTIONARY.md) §2.16 or [STATE_AND_GRAPH_CONTRACT.md](../contracts/STATE_AND_GRAPH_CONTRACT.md) §2/§7. Require a separately reviewed contract/ADR amendment rather than silently changing authoritative semantics.
5. Later P5 code slices and P4 re-integration each require separately scoped PRs, tests, owner Windows evidence where applicable and **owner merges**; no combined multi-phase code PR and no automatic phase PASS.

## 3. Concrete handoff order and deliverables

| Order | PR / owner | Deliverable | Hard exit condition |
|---|---|---|---|
| CH-01 (this PR; P4 docs) | Owner decision | Record the explicit sequencing and file-scope exception; preserve R1-A and honest statuses | Owner review + exact marker in PR conversation + merged docs + exact-main CI SUCCESS |
| P5-F0 (P5 code, separate PR) | Run identity and immutable selection | App-DB `workflow_run` real parent FK; authenticated doctor/assigned synthetic patient; server-generated ID equal to eventual LangGraph thread_id; stored UTC clock and versions; stable idempotency; durable doctor-selected document/observation IDs and explicit historical-source omission decisions; scoped audit | Reversible migration, stored source/selection tests, denial/no-write/idempotency, read-only preflight remains non-evaluable; owner code review / Windows + CI |
| P5-F1 (P5 code, separate PR) | Genuine run-bound VI preflight | From persisted run selection, reconstruct full evidence and recompute VI-001..006 with same-snapshot/freshness safeguards; selected rejected original always HALT; recovery must be separately selected, independently verified and explicitly doctor-omitted/audited; historic original OPEN VI-002 retained | Both HALT/eligible control cases evidenced; no DR evaluation before PROCEED; immutable gate provenance; owner review / Windows + CI |
| P5-F2 (P5 contract/bridge, separate PR) | Versioned server-owned `EvaluableReviewEvidenceV2` and deterministic P4 adapter | Reconcile `TOOL_CONTRACTS.md` §§3.5/3.7 through explicit approved versioning; no caller-supplied `blocking_fact_count=0`, role or gate flag; runtime demo policy activation remains separately owner-gated | Correct evidence/fact/observation provenance, scope/clock/mapping/policy validation, deterministic replay, no LLM rule decision |
| P4 completion PR(s), after P5 prerequisites | Run-bound `review_item` + `evidence_link` | Add authoritative FK-bound P4 persistence/review service; unique `workflow_run_id + dedupe_key`, scoped evidence, audited/no duplicate writes; full A/B/C/D + negative run-backed acceptance and truthful E2E scope | Independent P4 acceptance decision only after integrated gates, exact-head CI + owner Windows; `P4=IN_REVIEW` until then |
| Remaining P5, then P6–P8 | Graph/LLM/UI/demo | Continue according to architecture and gated phases | Separate scoped PRs and acceptance; no phase silently marked complete |

**Ordering note:** The table is a *proposed integration sequence*, not authorization to implement all rows. P5-F0 is the **only next code scope** that CH-01 may authorize after the explicit owner PR-thread ratification. Before F1/F2 or returning to P4, inspect the results and re-authorize each exact scope. The **full** five-agent LangGraph graph, Ollama drafts, approvals, tasks and UI stay out of F0.

## 4. Required P5-F0 run identity model (design, not a claimed implementation)

- The application SQLite DB, **not** a checkpoint or request body, is the source of truth for `workflow_run.status`. Persist `id` (server-authored UUIDv4), `patient_id`, `doctor_id`, immutable `workflow_version`, `state_schema_version`, `policy_version` (not an activation claim), `mapping_version`, explicit `as_of_utc`, `idempotency_key`, and controlled status/timestamps. `run_id == thread_id` must be the later P5 invariant. Never create a fake successful/completed run.
- Store an immutable **canonical selected-source manifest** of exact document/observation IDs with patient scope, ordering, selection revision and source/file SHA references or fingerprint, plus a **doctor-authored, authenticated, persisted/audited** explicit omission record for each excluded terminal recovery ancestor. Selection IDs are not permissions or guarantees; every selected row and lineage must be independently authorized and cross-checked. The `recovered_from_document_id` relationship is patient-declared, not proof that a document is equivalent.
- Use app-DB transaction boundaries and replay guards: a historical snapshot hash **alone** does not prove freshness or authorization. Define how the gate detects changed doctor assignment, verification decisions, VI states, source bytes, selected rows, and version mismatch. No `PROCEED` can be issued by P5-F0; its future gate remains `unavailable`.
- Migrations must be additive/reversible, preserve existing P3 documents/VI history, keep foreign keys strict and retain pre-existing protected owner data. No real user medical records, new clinical calculations, external messaging or unaudited writes.
- The genuine P5-F1 gate must distinguish **selected current source blocking** from **historical, open `VI-002` on excluded original**; a doctor-authored omission is NOT a historical VI auto-resolution. No live DR evaluation on an incomplete, stale or halted gate.
- `self_reported_validated` remains accurately labelled and admissible when the input meets the documented predicate; it must not become `doctor_verified`. `VI-*` verification blockers stay separate from `DR-*` demo review prompts; retired DR IDs forbidden.
- Source-byte attestation must be treated as a separate verifiable check: stored SHA/OCR text or a doctor click does not prove the original glyph was read correctly; `GOLD-EX-11` remains a known failed real OCR test.

## 5. Acceptance/test matrix and evidence classification

**Tests to implement in their own later code PRs (NOT RUN by this docs-only PR):**

1. Real DB migration `upgrade → downgrade → upgrade` (fresh + existing synthetic SQLite), FK integrity, duplicate/replay idempotency, immutable selected-source rows and audit/no-write on denied requests.
2. Authentic persisted active doctor session/role and assigned-patient scope; wrong-patient document/observation/lineage, missing IDs, duplicate/oversized selections, stale/expired/revoked identities fail closed.
3. Source-selection matrix: rejected original only/both => HALT; valid recovered only without audited omission => HALT; verified recovered with audited omission retains original failure and original OPEN `VI-002`; invalid chain/cycle, changed SHA, stale decisions and foreign ancestor fail closed.
4. Full VI-001..006 run selection recomputation and preservation of historical issue audit; no forged zero-blocker count, no `run_gate_completed=True` before true F1 verification, no DR/agent/LLM calls on HALT.
5. Deterministic `GOLD-A/B/C/D` and negatives with exact provenance/trust labels, policy version and clock; no unapproved task/notification, real message or clinical action.
6. Python 3.12 Ruff lint/format, full Pytest, reversible Alembic, generated OpenAPI, tracked secret/artifact scanner, Node frontend CI; isolated **owner Windows 5.1** `setup.ps1` / `test_all.ps1` at exact PR head; optional Playwright `SKIP ≠ PASS`. Model/Ollama checks separate if/when their phase exists.

**Evidence available now:** owner Windows at PR #29 final head `06bb56ff5d7e44c7d0c4028388ed5629d95093d5`: focused R21-S1 **25 PASS**, aggregate quality **12 PASS / 0 FAIL / 1 optional Playwright SKIP**; premerge [push CI #44907328104](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44907328104) / [PR CI #44907332161](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44907332161) SUCCESS, measured Linux backend 1077 PASS / 0 FAIL / 0 SKIP. Postmerge CI at `e01250dd...` SUCCESS. These results **do not test** any proposed future P5-F0/F1/F2 code.

**Executed in this docs-only PR:** GitHub-connected review of exact merge SHA, postmerge CI, [AGENTS.md](../../AGENTS.md), [MASTER_PLAN.md](../roadmap/MASTER_PLAN.md), [DATA_DICTIONARY.md](../contracts/DATA_DICTIONARY.md), [STATE_AND_GRAPH_CONTRACT.md](../contracts/STATE_AND_GRAPH_CONTRACT.md), [TOOL_CONTRACTS.md](../contracts/TOOL_CONTRACTS.md), prior P4 decisions, and source inventory. **No local Python/Windows/SQLite/Ollama/real-OCR/browser tests executed here.** Drafting documentation is not executable validation.

## 6. Owner ratification form, stop conditions and rollback

**Exact decision requested in this PR:**

> RATIFY-P4-P5-CONDITIONAL-HANDOFF-FOUNDATION-ONLY

Interpretation: the owner permits only the conditional **P5-F0** coding start after this docs PR merge and postmerge CI, with the explicit P5-F0 file-scope exception above; P4 stays `IN_REVIEW`, P5 as a whole stays unaccepted, existing R1-A and safety restrictions stay in force. All further F1/F2/P4 review code needs its own gated decision.

**If the owner does not ratify, leave CH-01 PENDING; do not create P5 code.** If the branch/docs prove inconsistent with existing contracts, revise them here before ratification, or close the PR. There is **no DB/data rollback** for this docs-only proposal. If a future code PR fails a gate, stop/revise that code PR; never bypass required tests, downgrade historical OCR failures or alter protected DBs.

**Owner review checklist:** exact three-file docs diff only; no deletion/rewrite of prior P3/P4 evidence; agreement on narrow P5-F0 sequencing/file-scope exception; source-selection and replay/freshness obligations; no fake FK/run clearance; `GOLD-EX-11` unchanged; CI and owner PR-thread decision; issue #14 remains OPEN until full P4 acceptance.
