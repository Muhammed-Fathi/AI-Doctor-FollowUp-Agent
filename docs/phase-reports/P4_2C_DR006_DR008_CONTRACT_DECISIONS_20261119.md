# P4-2c — DR-006 / DR-008 source, timestamp and interface decision proposal

**Status: OWNER-AGREED SCOPED SEMANTICS IN CHAT / ENGINEERING CONTRACT REVIEW STILL PENDING — no implementation, no policy activation, no phase acceptance.**
**Tracking:** P4 issue #14. **Baseline:** `main@3ccee32ec3aef0c11612d690cea42fbe203d955e` (owner-merged PR #18). Its post-merge GitHub Actions run #44483743708 completed SUCCESS on Python 3.12 backend and Node 22 frontend.
**Boundary:** local, fictitious educational records only; NOT FOR CLINICAL USE. The historical P3 `GOLD-EX-11=FAIL / NOT PROVEN` remains unchanged.

## 1. Why P4 needs a contract decision before implementing these rules

The approved planning texts identify six post-verification `DR-*` IDs. The already-merged *offline candidate* evaluator implements `DR-001/003/005/009`, but neither its policy nor the separately validated `demo-policy-*` policy is wired to a real run. The two remaining catalogue entries are:

- `DR-006`: two independent doctor-verified sources, same measurement type, compatible timestamps and different values beyond a `conflict_tolerance`; exact message: "Two verified sources disagree for {measure_type} at {timestamp}."
- `DR-008`: duplicate measurement (same type/value/timestamp) **or** a later-recorded entry whose measurement timestamp precedes an existing entry; exact message: "A repeated or out-of-order entry was detected for {measure_type}."

Neither *compatible timestamps* nor *recorded later* currently has a complete, testable definition at the candidate-evaluator interface. Silent assumptions could generate false prompts or double-count the same document-derived value.

### Existing implemented facts, not proposed assumptions

| Evidence in `main` | What actually exists | Missing from the current P4 candidate boundary |
|---|---|---|
| `DATA_DICTIONARY.md` §2.8 and `backend/app/db/models.py` | `observation.measured_at`, `created_at`, `source`, `source_fact_id`, `trust_level`, `validation`, `verified_at` are persisted | `ObservationSnapshot` carries `measured_at` and `trust_level` but not `created_at`, `source` or `source_fact_id` |
| `monitoring.py` | Explicit patient scoping, admissibility exclusions, UTC clock, deterministic comparisons; rejects duplicate observation IDs | No source-independence proof, creation-order projection or direct verified-fact projection |
| `TOOL_CONTRACTS.md` §3.5 | Proposed agent tool accepts up to 6 current values | Does not supply the historical rows needed to choose a prior baseline; the implemented pure helper uses up to 100 rows instead |
| `TOOL_CONTRACTS.md` §3.7 vs `DEMO_REVIEW_RULES.md` §10 | First names `verified_facts`, `comparisons` and `policy_version`; second additionally needs observations, clock and policy | No versioned, trusted, complete evaluation interface or actual server-side fact gate |
| `EXTRACTION_PROVENANCE.md` and `DATA_DICTIONARY.md` §3.3 | A verified document fact maps to an observation only through `map-1.0.0`; at most one measurement tuple per document | A fact and its mapped observation are **one source**, not two independent readings |
| `GOLD_FIXTURES.md` §5 | `GOLD-D` includes a positive same-type/value/time duplicate for `DR-008` | Does not establish creation-order or `DR-006` compatibility-window semantics |

These distinctions mean a test-only function receiving arbitrary `blocking_fact_count` or client-provided `patient_id` cannot be described as the actual doctor-verification or role-scope gate.

## 2. Decision A — DR-006: independent doctor-verified sources

**Owner-agreed conservative semantics for a synthetic, offline first candidate (not runtime activation):**

1. An eligible candidate must be an admissible, mapped, doctor-verified observation whose stored provenance proves that it was derived from a verified document. Resolve `source_fact_id`, its source document and verification state from the application DB under the trusted patient/run scope. Do not treat a raw `ExtractedFact`, a mere OCR transcription, a self-reported observation, or a declared source label on its own as proof.
2. Require **two distinct persisted source facts from independent source documents** for a positive pair. The `ExtractedFact` and the `Observation` mapped from that *same* fact count as one source, not two. Whether separately verified values in the same document or other doctor-verified observation sources qualify is an **owner decision**; the conservative subset excludes them for now.
3. Recommend strict equality of canonical UTC measurement instants for "compatible timestamps" in the first candidate. The policy's proposed `conflict_tolerance=0` would compare exact Decimal values in the same allowlisted unit. A ±time window or date-only equivalence **cannot be guessed** from the current contract; either must be separately selected and versioned by the owner.
4. Check distinct sources, approved trust, verification gate, patient scope, measurement type, allowed unit, finite value and usable timestamps **before** value comparison. For unsupported or ambiguous provenance, produce **no `DR-006` prompt** and expose a typed exclusion/verification outcome to the internal caller; never silently promote it.
5. Prefer evidence links to distinct, patient-scoped observation IDs with their existing immutable source lineage; a future reviewed adapter must ensure `evidence_link` can resolve the sources. Maintain deterministic ordering, deduplication and the exact neutral message. No medical interpretation or action.

**Owner-scoped decision:** exact UTC measurement instants and independent, mapped, doctor-verified observations from **different persisted source documents** are the first-candidate interpretation. Other independently verified source categories and wider time windows remain intentionally out of scope, not silently treated as validated. Keep `DR-006` rejected by the existing offline evaluator until a separate reviewed implementation PR passes.

## 3. Decision B — DR-008: duplicates and recording chronology

**Owner-agreed semantics for a synthetic, offline first candidate (not runtime activation):**

1. An **exact duplicate** means two distinct eligible observation IDs from the same patient have identical measure type, allowed unit, canonical `measured_at` and Decimal value. Do not compare an observation with itself, count `source_fact_id` replay as a second entry, or confuse duplicate *request* idempotency with two already-stored measurements.
2. An **out-of-order entry** means a second eligible observation has a strictly **later persisted `created_at`** but a strictly **earlier `measured_at`** than another eligible observation of the same type/unit. A late document upload can meet this condition; wording must remain "entry" / data-quality only, not an adverse finding.
3. Use server-read persisted `created_at` as the recording chronology; **never** substitute `measured_at`, `verified_at`, upload timestamp or the injected `as_of_utc` for creation time. Equal creation instants do not prove "later"; do not invent order using IDs. The injected UTC clock still controls admissibility.
4. Exclude rejected, wrong-unit, missing/future-measurement-time rows before evaluating either branch. Missing/invalid creation time means the ordering branch is not evaluable, rather than treating the missing time as early/late. Missing data may be a data-quality exclusion, not a fabricated `DR-008` output.
5. Candidate tests must cover `GOLD-D` duplicate, out-of-order, ordinary in-order history, idempotent replay, same ID, same timestamp/different value, equal `created_at`, mixed provenance, mismatched patient, wrong unit, invalid clock, and permutation-invariant ordered outputs.

**Owner-scoped decision:** persisted `created_at` is the sole creation-order signal; strictly greater creation time plus strictly earlier measurement time is required to call an entry out of order. Missing/invalid or equal creation instants **must not** produce an inferred ordering flag; they require a bounded internal exclusion/indeterminate outcome. A future reviewed internal projection must supply this metadata before enabling the full rule.

## 4. Decision C — P4 service boundaries required for both rules

**Recommended architecture, proposed only:**

- A read-only, authentication-scoped P4 service resolves the current patient's observations (max 100), verified-fact/document lineage, admissibility exclusions and persisted creation times. The patient scope and actual verification gate must come from server-side authorization and database state, not from a caller-supplied flag count.
- Keep an immutable internal `ReviewEvidenceBundle` **concept** containing the trusted scope, explicit UTC clock, admissible observation projections, recomputed comparisons, approved verified-source lineage and versioned candidate policy. This is a proposed shape, **not** an existing API/schema or a request to create `backend/app/agents` prematurely.
- `TOOL_CONTRACTS.md` §3.5 must explicitly reconcile its six-current input with the history source that the existing internal comparison helper requires. §3.7 must include the server-owned evidence/clock requirements and a reliable pre-verification block. Preserve `E_UNVERIFIED_FACT` for extracted facts only; never apply it to a merely self-reported, otherwise admissible observation.
- The independent `DemoPolicyCandidate` validator and `CandidateDemoPolicy` evaluator have different, deliberately isolated version families and input sets. Decide on a single **reviewed adapter/contract revision** before any runtime wiring; passing structural validation never constitutes parameter approval.
- P4-3 persistence requires a separate owner architectural decision: `review_item.workflow_run_id` is a mandatory FK to a `workflow_run` currently assigned to P5. Do not invent a fictitious run, silently loosen the FK, or implement P5 graph code in P4. Record which minimal P4-compatible run identity or deferred persistence strategy is approved.
- `OQ-R01`: arbitrary `demo-policy-1.1.0` numbers remain **unapproved** until expressly signed off for synthetic educational mode. The two proposed candidate rules can be independently tested offline without activating this policy.

## 5. Required synthetic acceptance matrix before a rule-implementation PR can be merged

| Scenario | Expected deterministic behavior |
|---|---|
| Two independent mapped doctor-verified document observations, same type/unit/time, different values beyond approved tolerance | Exactly one `DR-006` candidate, with two distinct source-backed evidence references |
| Fact plus its derived observation; only one source | No `DR-006` |
| Self-reported plus doctor-verified value, or document-only unmapped test | No `DR-006` under conservative first-slice semantics |
| Two compatible verified sources with equal value | No `DR-006` |
| Two stored admissible observations with same type/unit/value/measured_at and distinct IDs | `DR-008` duplicate candidate, once |
| Later-created record with earlier measurement time | `DR-008` out-of-order candidate, once |
| Equal creation instants or missing creation-order information | No inferred out-of-order prompt |
| Excluded timestamp/unit/rejected row + clean admissible row | No false flag; preserve exclusion reasons |
| Wrong patient, stale/forged verification gate, mismatched recomputed comparison, retired/unknown IDs | Typed fail-closed response, no partial output |
| Same evidence in reversed order, replay, repeated evaluation | Exactly identical output/dedupe keys, no duplicate items |
| Pre-verification `VI-002` active, including existing R21 lineage rules | No post-verification `DR-*` output until actual gate resolves |
| `GOLD-A` / `GOLD-B` / `GOLD-C` / `GOLD-D` | Exact expected synthetic IDs; never present `GOLD-EX-11` as a successful real OCR detection |

All future test data are fictitious, fixed-clock fixtures. No real records, diagnosis, risk scoring, treatment, autonomous agent, database mutation, notification or external communication are authorized by this document.

## 6. Review decision checklist

1. **A1 — AGREED IN CHAT, SCOPED:** exact UTC measurement-instant equality for the first offline `DR-006` candidate.
2. **A2 — AGREED IN CHAT, SCOPED:** only independent, persisted, doctor-verified mapped observations from two distinct source documents; fact-plus-derived-observation counts as one source.
3. **B1 — AGREED IN CHAT, SCOPED:** persisted `created_at`, not upload/verification/measured time, establishes the strictly later recorded entry for `DR-008`.
4. **B2 — AGREED IN CHAT, SCOPED:** missing, invalid or equal creation timestamps do not prove a later-entry chronology; do not infer an out-of-order prompt.
5. **C1 — STILL OPEN:** review/version a server-scoped P4 evidence adapter for §3.5/3.7 and a real verification gate; no P5 agent calls.
6. **C2 — STILL OPEN:** explicitly decide P4-3 run identity/persistence strategy and separately approve or reject `OQ-R01` demo-policy parameters.

The owner consented to A1/A2/B1/B2 in the current chat on 2026-11-19, after being presented with the exact-source, strict-UTC and persisted-`created_at` conservative interpretations. This document records the *scoped* instruction rather than claiming a GitHub approval, phase PASS, policy activation, or resolution of C1/C2. A separate implementation PR must carry the actual typed evidence adapter and tests; normative runtime contracts must not be changed or activated silently. GitHub owner review/merge of this docs-only record remains required.

## 7. Verification and non-goals for this PR

- **Authoring:** evidence reviewed directly from private `main` files and merged PR #18; this document itself introduces no executable behavior.
- **Executed here:** GitHub read-only merged-state and CI checks. Post-merge CI run #44483743708: completed SUCCESS, both Backend Python 3.12 and Frontend Node 22.
- **Not executed here:** local pytest, Windows PowerShell, Ruff, migration smoke, production endpoints, any source/time rule tests. CI for this *new docs-only PR* must be checked at its exact head if opened.
- **Changed paths intended:** this new P4 proposal and an append-only link/status note in `PHASE_4_REPORT.md`. No contracts, P3 executable/fixtures, scanner rules or active policy are modified.
- **Rollback:** close this PR without merge. It has no runtime or database effects.
- **Status remains:** P4 `IN_REVIEW`, P5 not started, P3 educational conditional acceptance and `GOLD-EX-11` technical failure retained.

## 8. Owner authorization boundary — 2026-11-19

The owner replied in chat **«موافق لو انت شايف ده في مصلحه الشغل والبروجيكت»** to the two *specified* candidate interpretations. Recorded here as a bounded semantic decision only:

- **DR-006:** two independently verified document-backed observations; each from a distinct source document and fact, same patient/type/allowed unit, with **exactly equal canonical UTC measured times**. Same fact plus mapped observation is a single source. No broader ±time window, self-reported promotion or medical meaning.
- **DR-008:** exact duplicate requires distinct observation IDs and identical patient/type/unit/value/measured time. The out-of-order path uses **persisted `created_at`** for later recording and **persisted `measured_at`** for earlier measurement; a tie or missing/invalid `created_at` does not prove a later recording. Preserve separate exclusion state instead of guessing.

**Not authorized by this chat approval:** runtime activation; policies or any numeric `conflict_tolerance`/`demo_delta_*` values; tool/API contracts; creating `workflow_run` or review-item persistence; P5 graph; autonomous actions; P3 safety conclusions. C1/C2 and OQ-R01 remain open. PR owner review and exact-head CI remain separate gates. No source or current-user data was used; this is a synthetic educational policy-design decision.
