# P4-2e — Read-only SQLite projection of synthetic provenance

**Status:** DRAFT / IN_REVIEW. No P4 acceptance, no live rule/tool activation.
**Scope:** Internal P4 source-read proof only. Fictitious synthetic data — NOT FOR CLINICAL USE.
**Baseline:** owner-merged PR #20, `main@2739c90229f754bb0822d309600bab8f8f617b85`.
**Baseline postmerge CI:** [#44493844402](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44493844402) completed SUCCESS (Python 3.12 + Node 22).

## Goal and verified implementation boundary

The P4-2d `DR-006/008` evaluator accepts *fixture claims* about source documents, verification decisions and `created_at`. That alone is not trusted evidence of provenance. This slice adds one **internal read-only SQLite service**, `load_readonly_provenance_evidence`, which:

- Requires a server-provided `Principal`, doctor-only role, **persisted active doctor** account, and current `patient.assigned_doctor_id`. It rejects out-of-scope users and explicitly requires `patient.data_source='synthetic_fixture'`.
- Reads at most **100** patient-scoped `observation` rows; fails closed above the cap instead of silently omitting potential duplicates or contradictions.
- Preserves the stored measurement type, value, unit, trust level, measured timestamp and persisted `created_at` without converting/imputing/reordering trust.
- For `source='verified_document'`: resolves a value `ExtractedFact`, same-patient verified `Document` with matching patient reference, unit/value consistency, stored doctor account, and exactly one matching doctor decision. It understands both `verified` and `corrected` via the original source fact's decision and original rejected status. Missing/inconsistent lineage is **withheld**, with `verified_lineage_unavailable` exclusion; a record is never promoted to doctor-verified from a client claim.
- Returns `CandidateRecordedObservation` projections used by the **existing offline candidate evaluator**; tests may manually select the synthetic rows and pass a **test-only** blocking count, but the service itself neither executes a review rule nor publishes any endpoint.

### Critical limits

This is **not proof of physical OCR/PDF integrity**, clinician examination, or a complete run-scoped `VI-002` gate. It checks the DB's recorded doctor decisions and source links, not actual original document bytes. The incoming `Principal` must be derived from a server-authenticated session by any future caller; the internal service is not an authentication endpoint and cannot turn an arbitrary caller-created object into an authenticated session. No P5 LangGraph or trusted policy default is added.

There is **no genuine P4-4 run** to associate a document's active or superseded facts with in this slice. It would be unsafe to treat a manually supplied `blocking_fact_count=0` or a document-level `verified` status as authorization to produce a live `DR-*` item. Any future P4 integration needs separate bounded owner review of `TOOL_CONTRACTS.md` `3.5/`3.7, owner policy `OQ-R01`, and run-scoped gating, plus P4-3 `workflow_run` identity strategy.

## Exact changed files

1. `backend/app/services/p4_readonly_provenance.py` — new internal read-only DB projection.
2. `backend/tests/p4/test_p4_readonly_provenance.py` — migrated SQLite tests of real stored lineages, fake source decisions, corrected-fact lineage, doctor scoping, no cross-patient leakage, no mutation and row-cap.
3. `docs/phase-reports/P4_2E_READONLY_SQLITE_PROVENANCE.md` — this stage report.
4. `docs/phase-reports/PHASE_4_REPORT.md` — append-only P4 checkpoint.
5. `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — append-only provisional **976 whole-backend / 443 P3** collection assertion so the existing P3 handoff-integrity test cannot silently drift; it preserves P3 historical evidence.

## Tests, rollback and owner review

- **At PR authoring:** no local Python/Ruff/Windows tests executed in this tool environment. New P4-2e tests are expected to add 9 backend cases; **976 is a provisional collection count**, not pass evidence.
- Require **exact-head GitHub CI**: Ruff lint/format; full pytest and existing P3 count guard; reversible Alembic; OpenAPI; repository scanner; Node 22 typecheck/lint/Vitest/build. Fix any failures on the same branch, without weakening test or scan policies.
- Require **owner Windows isolated-worktree** `setup.ps1` and `test_all.ps1` on the reviewed exact HEAD before considering owner merge. Optional Playwright skipped unless deliberately configured, never described as passing.
- No `main` mutation/merge/agent approvals. Rollback: close the isolated branch unmerged. No persisted schema or production DB changes.

**P4 = IN_REVIEW. P3 GOLD-EX-11 remains FAIL / NOT PROVEN.**


## Initial CI result and collection count correction

- [PR CI 44495402318](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44495402318) at `711d1e0c34268c60c29bdb01c7b7485ca30c274f` completed **FAIL** at the already-existing handoff-count integrity test. It reported exactly `handoff should quote the whole-backend total 977`, not our earlier provisional `976`. The progress of the other backend tests showed no additional failure; the frontend job succeeded.
- The P4-2e Windows handoff now **appends** the corrected **977 total / 443 P3** collected-count token; a subsequent exact-head CI **must still pass**. Neither historical P3 tests/fixtures nor scanner checks have been weakened. This note distinguishes collected tests from an observed PASS count.
