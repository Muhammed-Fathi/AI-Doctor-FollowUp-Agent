# P4 — R3/OQ-R01 synthetic policy and R21 recovery-selection decisions

**State:** OWNER DECISIONS REQUESTED — NOT RATIFIED BY THIS DOCUMENT; P4 **IN_REVIEW**, NOT ACCEPTED.  
**As of:** 2026-11-21. [P4 issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14).  
**Baseline:** owner-merged [PR #26](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/26) at `main@1aed4595f8d9a90ece6af0659513e2bdbc98b448`. Exact-main [postmerge Actions run #44896431925, attempt 3](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44896431925) is **COMPLETED/SUCCESS**, Backend + Frontend SUCCESS after attempts 1/2 terminated without runner steps. Main Git tree matched previously reviewed PR #26 head. No application change was needed for the retry.

**Scope:** R3/OQ-R01 policy values and R21/P3 terminal-recovery **future source selection**, two **independent owner choices**. User asked to *review* them and prepare the next step, not to pre-approve either. Merging this documentation **does NOT count as** approval of R3, R21, any new API, a runtime policy, a source-exclusion rule, P5 or phase acceptance. Local, synthetic, educational only. **NOT FOR CLINICAL USE.**

## 1. Source inspection (design versus executable)

- `docs/clinical-safety/DEMO_REVIEW_RULES.md` ``4–5, 7–10, 11 and 13: policy `demo-policy-1.1.0` has a proposed fixed demo clock and nine *arbitrary* parameters, six active DR IDs and six blocking VI IDs. `OQ-R01` explicitly asks for owner approval. The candidate is deliberately nonclinical.
- `backend/app/services/demo_policy.py`: `validate_demo_policy` strictly checks the closed policy shape, values/engineering bounds, ID catalogue and date, returning a **DemoPolicyCandidate**, not an approved policy. `backend/tests/p4/test_p4_demo_policy.py` exercises candidate validation. Tests accepting values are **not a signature or activation**. The validator accepts enabled/disabled switches structurally, so the future approved release must not silently disable any blocking `VI-001..006`.
- `docs/phase-reports/P3_R21_REJECTION_RECOVERY_DESIGN.md` `4.1–4.4 and `7a, ``9–10, and `backend/app/services/documents/{intake,verification,quality}.py`: existing R21/P3 design and code treat a first **plain active rejection** as terminal `failed` (`measurement_rejected`, `fact_rejected`, or `all_facts_rejected`). The patient may separately upload different bytes with `recovery_of`, creating a **patient-declared link**, NOT verified equivalence. The rejected original and its `VI-002` stay open and immutable. Existing P3 rejection/recovery tests validate the P3 behavior; none authorizes downstream omission of the original from a *future run*.
- `backend/app/services/p4_document_preflight.py` rejects selected nonverified documents and reports `run_gate_completed=False`. `backend/app/services/p4_evidence_inspection.py` reports `run_gate_status="unavailable"` / `runtime_evaluable=False`; its current selection is **not** a durable or independently replay-verified run manifest. These helpers cannot be treated as a full VI-001..006 run gate.
- `docs/phase-reports/P4_R2_TRUSTED_EVIDENCE_CONTRACT_DECISION_20261119.md` and owner-selected R1-A, R2-A, C-35A, C-37A: only scoped internal inspection and explicit history are allowed now. P4-3 persistence is deferred until a genuine P5 `workflow_run` exists; no fake run IDs, relaxed FKs or P5 preimplementation.
- Real P3 Windows OCR `GOLD-EX-11` remains `FAIL / NOT PROVEN` (real engine read `1O5` as `105`); synthetic corrected-fact fixtures do not resolve OCR source-glyph accuracy.

## 2. Independent choice R3 / OQ-R01 — approve synthetic reference parameters?

**R3-A (recommended for explicit owner decision):** Approve exactly the `DEMO_REVIEW_RULES.md` ``8–9 **synthetic reference policy parameters** for `demo-policy-1.1.0`, **only to pin deterministic fixture outputs and a future, separately reviewed offline policy artifact**. Such approval is NOT installation, switching on a runtime policy, linking an agent to rules, a reviewed source-image verification, or permission to display a decision recommendation.

| Exact name | R3-A candidate | Invariant if owner approves |
|---|---|---|
| `policy_version` | `demo-policy-1.1.0` | Immutable artifact identifier; any different values/clock/switches require new version and independent fixture review |
| `demo_only` | `true` | Test-only/synthetic and fixed neutral notice |
| `demo_as_of_utc` | `2026-11-14T12:00:00Z` | Fixed injected clock for reproducible fixture replay; not current time |
| `baseline_lookback_days` | `90` | Only comparison-history horizon in the synthetic policy |
| `stale_measurement_days` | `30` | Mechanical data-age prompt, no urgency semantics |
| `demo_delta_systolic_mmHg` | `10` | Absolute demo delta; not a normal-range or severity cutoff |
| `demo_delta_diastolic_mmHg` | `8` | Same |
| `demo_delta_heart_rate_bpm` | `15` | Same |
| `demo_delta_glucose_mgdl` | `40` | Same |
| `ocr_confidence_floor` | `0.70` | Fixture/engine-reported uncertainty flag only; **not** evidence that OCR token agrees with original document |
| `conflict_tolerance` | `0` | Synthetic exact-numeric comparison with compatible unit/time and verified independent sources |
| `max_items_per_type` | `3` | Presentation/cap boundedness only; NEVER hides an active `VI-*` blocker |

**Closed enabled ID sets:** all `VI-001, VI-002, VI-003, VI-004, VI-005, VI-006` **enabled**, all six `DR-001, DR-003, DR-005, DR-006, DR-008, DR-009` **enabled for offline evaluation only**, retired `DR-002/004/007/010` prohibited. Enabled DR means included in a *test catalogue*, not runnable in the app. The exact notice is `DEMO review prompts only — not clinical risk assessment. Not for clinical use.`

**R3-B:** Modify one or more arbitrary parameters (supply exact alternatives); requires a *new version*, baseline + fixture impact analysis and fresh approval. **R3-C:** defer approval; current candidate evaluation remains test-only as it is now.

**Additional required guard for an eventual policy artifact:** unlike structurally valid candidate input, owner-approved artifact must be distinguishable from arbitrary candidate dictionaries by **trusted server/repository-pinned identity**, complete six blocking VI switches and a separately reviewed activation boundary. A version string or an asserted `approved=true` inside a request body cannot authorize anything. Missing/invalid versions or values fail closed with `E_RULE_POLICY_INVALID` and zero rule outputs; never silently substitute defaults. This recommendation **does not change** current `validate_demo_policy` or freeze a YAML file in this docs PR.

## 3. Independent choice R21 — how can a future run select a recovered document?

**Current P3 invariant is NON-NEGOTIABLE:** a terminal original `failed` with open `VI-002` must retain its facts, rejection decisions, open issue, failure code and audited recovery links. Re-uploading does **not** attest equivalence, close the original issue, auto-resolve the original document, or make the chain safe by itself.

**R21-S1 (recommended for a future run design only): explicit doctor-authored source-set selection, audited omission, no automatic clearance.** Define a *later* genuine persisted run's immutable manifest of selected doc IDs and observation IDs, with server-authenticated active assigned doctor + patient scope, source and recovery lineage, doctor selection reason for excluding a terminal original, recorded exact revision/hash/clock/policy reference and replay freshness. The patient-supplied `recovery_of` association is never sufficient evidence of equivalence or a doctor's choice.

- **Old terminal original selected in the run:** **HALT** on `failed` and its active `VI-002`, even when a linked recovery is selected and separately verified. No flag, score, read-only preflight, or patient upload can override this.
- **Recovered document selected, original explicitly NOT selected:** the original `VI-002` remains **OPEN** historically; the old rejection must be visible via relationship/audit but is **not falsely declared "resolved"**. The recovered document is independently evaluated for identity, extraction, verified human decisions, valid source bytes/lineage, all relevant `VI-001..006` and scope; any failure or a missing/ambiguous manifest/omission reason => **HALT**. Only a *future* owner-authorized, replay-safe run gate may decide `PROCEED` based on a complete selected set. A successful *P4 local selected-doc preflight* is never this decision.
- **Both selected / missing source decision / cross-patient chain / rejected recovery / changed evidence:** **HALT**; do not silently downselect or auto-clear. In particular, a mere `recovery_of` field and a non-empty `FactVerification` do not prove the uploaded source glyphs were accurately read.
- **Multiple recovered generations:** inspect/record the complete ancestry, enforce bounded acyclic same-patient linkage and the chosen scope; do not assume newest automatically wins. Include explicit tests for chained recovery, wrong-patient, cycles, stale decisions, duplicate evidence, and source-hash mismatch.
- **P4 before a real run identity:** support only an offline *typed selection-eligibility recommendation* with `run_gate_completed=False`; it cannot mutate `VerificationIssue`, emit live DRs, fabricate a workflow ID or guarantee freshness beyond its read scope. Actual immutable manifest/transactional/run authorization belongs to P5 under R1-A.

**R21-S2 (strict alternative):** any known terminal rejected ancestor keeps the entire linked chain blocked for a future run until a separately defined authoritative resolution process. This is more conservative but makes even independently verified recovery unusable. It must be an explicit product decision, not an accidental consequence of treating all historical open issues as selected blockers.

**R21-S3:** defer the downstream selection policy; today an incomplete gate always **HALTS / is UNAVAILABLE**, with no omission-based clearance. Existing P3 recovery remains intact.

**Recommendation:** R21-S1 for an explicitly reviewed *future run selection policy*, conditioned on an immutable signed/owner-authenticated selection record and a completed, recomputed run-gate implementation. **Do not** implement a permissive substitute in P4 that only checks selected documents while ignoring old lineage without an audited doctor choice.

## 4. Decision matrix — distinct approvals

| Decision | Recommended answer | Approval effect | Explicitly not approved |
|---|---|---|---|
| **R3/OQ-R01** | **R3-A** | Owner ratifies fixed artificial demo numbers/clock/catalogue for later **reference-only** artifact and synthetic tests | Runtime enabling, OCR accuracy, source attestation, agent tool, review persistence |
| **R21 source-selection** | **R21-S1** | Owner authorizes separate **offline P4 selection-policy tests/design** and future P5 run-bound manifest contract | Auto-resolving old VI-002, automatically trusting recovery, creating P5 run or clearing real gate |
| **R1-A** | Already selected | P4-3 schema/write deferred until genuine P5 run identity | Temporary run ledger / FK weakening |
| **R2-A/C-35A/C-37A** | Already selected; PR #26 merged | Explicit history + internal scope-bound inspection only | A durable same-transaction source manifest or full `VI-*` gate |

**Merging this documentation alone is NOT owner ratification of R3-A or R21-S1.** A future approval must name **both choices separately**; the owner may approve just one or reject either.

## 5. Planned work AFTER separate owner decisions (one bounded PR per implementation)

**PR A — R3 fixture-pinned policy artifact, offline only:** versioned file under `data/synthetic/policy/` plus explicit fixed serializable shape; strict decode with existing validator; policy/fixture hash and immutable comparison, disabled-blocking-VI rejection, invalid clock or future policy switch rejection, deterministic GOLD A/B/C/D offline reference tests. No API route, policy activation, OCR bypass, runtime selection or P5. If the candidate version/values are altered the fixture reference must be reviewed as a new owner decision. An owner Windows gate required before code merge.

**PR B — R21 synthetic recovery-selection matrix, offline only:** small P4 projection against migrated SQLite to model selected original/recovery/both/neither, chained links, new doctor decision/missing decision, source/identity mismatch, VI-002 preservation and no-write guarantee. This is **NOT** the final run gate, and must return unavailable as long as P5's genuine run identity and audited selection manifest do not exist. No P3 recovery workflow changes, no VI database writes/auto-resolution or policy activation. May be prepared only after the owner chooses the intended R21-S* semantics.

**Later P5 work (not authorized here):** durable run identity + explicit selected-source manifest, re-run scoped VI-001..006, snapshot/replay and app DB status binding, versioned `TOOL_CONTRACTS` ``3.5/3.7 runtime tool bridge, review persistence, agent orchestration. P4 acceptance remains conditional and must not be declared by fixture success.

## 6. Evidence, test status, owner review

**Design reviewed:** exact main source files and docs identified in `1, P4 Issue #14, PR #26 merge record, postmerge GitHub CI run attempt 3. **Executed here:** authenticated GitHub reads of committed Markdown/Python and workflow run metadata; no code or policy activation. **Not executed here:** local Python/Windows tests, Tesseract, Playwright, source-byte comparison, P5 run-gate or any patient interaction. This PR changes documentation only; exact-head CI must be independently checked before owner merges.

**Exact changed paths (proposed):**
1. `docs/phase-reports/P4_R3_OQR01_R21_RECOVERY_SELECTION_DECISION_20261121.md` — this report.
2. `docs/phase-reports/PHASE_4_REPORT.md` — append-only progress.
3. `docs/roadmap/PHASE_PROGRESS.md` — append-only status note; **not** an approval record.

**Risks:** a numeric demo parameter could be mistaken for an endorsed threshold; a patient-declared recovery link could be mistaken for source validation; relying only on the selected subset could hide an old terminal blocker; a session-bound ORM inspection is not run-scoped replay attestation; the real `GOLD-EX-11` failure remains. Controls are explicit disclaimer, approval split, fail-closed run gate, preserve original `VI-002` and source lineage, separate PR/testing/owner review.

**Owner checklist:** review this three-file documentation proposal; independently choose `R3-A/B/C` and `R21-S1/S2/S3`; record decisions in a later owner reply; merge documentation only after exact-head CI. P4 stays `IN_REVIEW` and Issue #14 remains OPEN. No agent self-merge; rollback = close docs PR. **NOT FOR CLINICAL USE.**
