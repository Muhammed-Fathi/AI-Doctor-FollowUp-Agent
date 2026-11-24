# Phase Progress Tracker

> **LATEST POST-MERGE P3 OWNER STATUS (2026-11-19):** [PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) was **owner-merged** to `main` at `006ecf417f023428ab90c35cbb0638995c246774`; reviewed head `1b24d09d7630ff67ec282c9ee166440624d19fa5` has an identical tree, and [post-merge CI 44430671695](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44430671695) completed **SUCCESS**. Owner [conditionally accepted the P3 educational application](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995753177) and [ratified the independent-review substitution](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995977559). **P3 = CONDITIONALLY_ACCEPTED — LOCAL SYNTHETIC EDUCATIONAL USE ONLY**; this is not strict P1 technical PASS or clinical approval. Real `GOLD-EX-11 = FAIL / NOT PROVEN` (source `1O5` → OCR `105`; 27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED; exit 2) and possible false human attestation remain. See [final owner evidence/closure record](../phase-reports/P3_FINAL_CONDITIONAL_ACCEPTANCE_20261119.md). Earlier `IN_REVIEW`, `DRAFT`, `PROPOSED`, and not-yet-effective statements below are *historical checkpoints*, not today's phase status. No P4/P5 execution authorization. **NOT FOR CLINICAL USE.**

> **Historical 2026-11-18 OCR investigation snapshot (superseded for PR/CI status): P0 PASS; P1 PASS (owner-approved and merged 2026-11-14); P2 PASS (owner-approved and merged 2026-11-14 at `777f6618c62560be41cce394218c87b0c683981f`). P3 `IN_REVIEW` — Stages 1–5 implementation exists on a separate P3 acceptance branch; owner Windows v1.1.2 `plan_only` PASS and `probe_only` INCOMPLETE (exit 13); v1.1.3 ZIP/source independently audited; actual owner Windows `plan_only` **PASS (exit 0)** and `probe_only` **PASS (exit 0; measurement complete)**, both with protected postflight PASS; **`canonical_baseline` independently audited COMPLETE (inner exit 0, 3/3, postflight PASS)**; however **GOLD-EX-11 source `1O5` OCR→`105` was missed by every ambiguity-specific detector**, while D4/D6 only raised non-specific operational review and also falsely routed clean `13.4`. **STOP before exploratory/holdout; GOLD-EX-11 FAIL / NOT PROVEN.** Outer PowerShell warning/log incident remains documented. No P3 PASS, no PR #10 merge, no P4/P5.**
>
> Phase 0 (Governance and Specifications) completed its documentation review process and was merged into `main` through [PR #2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2).
>
> **Verified merge commit:** `442256606fd2465439409cc9b4d42f1bec09a723`
>
> **Final PR head:** `2eace34801d4140cba7b698d9be6d8632a6d9ad6`
>
> **Original base:** `7d2ef73dae50c7404b46f653942eb99351053059`
>
> **Owner approval:** Approved on 2026-11-14, following the final technical review.
>
> **Final technical review:** `5904590155` — P0 architecture and governance documentation ready for owner sign-off, with no remaining blocking documentation findings.
>
> **P1 acceptance record:** P1 — Foundation and Reproducible Startup, PR [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4), status `PASS`. Windows verification at `eec6642`, final docs-only PR head `58a0652`; merge commit `2c85db4d9fe9f17080146d12adfbd030a05cc75d`. Owner approved on 2026-11-14.
>
> **In review:** P3 — Synthetic document ingestion, extraction, provenance and doctor verification. Status `IN_REVIEW`. Nine independent-review findings (`P3-R01..R05` at `9704fca`, `P3-R06..R08` at `b4f761f`, `P3-R09` at `af7d59d`) plus the issue-uniqueness point were reproduced with regression tests and corrected; see `docs/phase-reports/PHASE_3_REPORT.md` Parts III, IV and V. Full evidence, deliberate deviations, honest limitations and the Windows verification checklist are in Part II (§I–§P) and Part III (§III.1–§III.8). The implementing agent makes no PASS claim and has not merged anything (`AGENTS.md` §2).
>
> **Last accepted phase:** P2 — Patient data and role-based API, PR [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7), status `PASS`. Live owner Windows verification at `9fddb51` (`6882774686`), final owner Windows regression at `b2bb1594fd89b26fed1ea5201302d6aac4c04698` (**12 PASS / 0 FAIL / 1 optional SKIP**), final CI run [`43632732091`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43632732091) (**SUCCESS**); merge commit `777f6618c62560be41cce394218c87b0c683981f` ([comment `6883243529`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883243529)). Owner approved on 2026-11-14 ([comment `6883198256`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256)). P2 remains the **last accepted phase**; P3 is active only in `IN_REVIEW` on its own branch.
>
> **Important:** P0 approval applies to the architecture, requirements, contracts, documentation and synthetic-demo scope. It does not represent completed application implementation, clinical validation or successful runtime testing.

A phase becomes `PASS` only after PR review, evidence verification, the local PowerShell gate when applicable, explicit owner approval and merge.

The implementing agent never self-approves, marks phases `PASS` or merges pull requests (`AGENTS.md` §2).

---

## Phase Status Overview

| Phase | Topic | Status | PR | Merge SHA | Test Evidence | Owner Approval |
|---|---|---|---|---|---|---|
| P0 | Governance / specifications | **PASS** | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) | `442256606fd2465439409cc9b4d42f1bec09a723` | Documentation consistency, traceability, OpenAPI validation and targeted contract checks completed. No runtime implementation tests applicable to P0. | **Approved — 2026-11-14** |
| P1 | Foundation / reproducible startup | **PASS** | [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4) | `2c85db4d9fe9f17080146d12adfbd030a05cc75d` | **Owner Windows gate PASSED at `eec6642`:** `test_all.ps1` 12 PASS / 0 FAIL / 1 optional SKIP; `invoke_native.tests.ps1` 14 checks; `stop_identity.tests.ps1` 38 checks; live setup/start/stop PASS on both the normal path and the space-containing path (`E:\DEPI\AI Doctor FollowUp Agent Space Test`); ports 8000/5173 free and all three tracking files removed. GitHub Actions run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) SUCCESS. Backend 121 tests, frontend 13, Ruff, Alembic, OpenAPI, scan, Vite build also pass locally. Optional Playwright smoke NOT EXECUTED. | **Approved — 2026-11-14; license and DEPENDENCIES sync deferred; Playwright SKIP acknowledged** |
| P2 | Patient data + role-based API | **PASS** | [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) | `777f6618c62560be41cce394218c87b0c683981f` | Sandbox Python 3.11: `356 passed` (125 P1 + 231 P2), `ruff check`/`format` clean, OpenAPI gate `PASS (11 paths / 12 operations, 22 schemas)`, `check_alembic_smoke` PASS in states `head`/`p1`/`base`, secret scan PASS. **CI independently verified across PR heads:** runs [`43625331149`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625331149) (`dbaf938`), [`43625989736`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625989736) (`6d54ede`), [`43626628577`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43626628577) (`9fddb51`), [`43631967775`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43631967775) (`7a5a047`), and **final merged head run [`43632732091`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43632732091) (`b2bb1594fd89b26fed1ea5201302d6aac4c04698`)** — Backend Python 3.12 SUCCESS and Frontend Node 22 SUCCESS in all five (the Arena agent's own Actions/Checks read returned 403 *Resource not accessible by integration*, retained as an observer limitation, **not** a CI failure). **Owner live Windows verification: PASS (2026-11-14)** at unchanged implementation snapshot `9fddb51ba7672efd992c47325ab4883734da3c9a` — isolated worktree, PowerShell 5.1, Python 3.12.9: `test_all.ps1` 12 PASS / 0 FAIL / 1 optional SKIP (exit 0), Alembic P2→P1→P2, 11 paths / 12 operations / 22 schemas, synthetic bootstrap 6 users / 3 patients / 3 encounters / 17 observations, 9 RBAC checks, 8 idempotency checks, 7 demo-reset checks, identity-safe shutdown, `main` HEAD unchanged and DB SHA-256 byte-identical; PBKDF2 600 000 iterations measured hash 550.49 ms / verify 537.67 ms ([owner comment 6882774686](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6882774686)). **Owner final Windows regression at final head `b2bb1594fd89b26fed1ea5201302d6aac4c04698`: PASS** — `test_all.ps1` 12 PASS / 0 FAIL / 1 optional SKIP, 14 command-wrapper checks PASS, 38 stop-identity checks PASS, `P2 FINAL WINDOWS REGRESSION: PASS`, `MAIN ISOLATION: PASS`; post-merge owner local `main` fast-forwarded to `777f6618c62560be41cce394218c87b0c683981f` and original `main` SQLite database remains byte-identical ([comment 6883198256](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256), [comment 6883243529](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883243529)). Optional Playwright: **SKIPPED, not passed**. | **Approved — 2026-11-14 ([comment 6883198256](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256)); bounded MVP limitations and Playwright SKIP acknowledged** |
| P3 | Synthetic documents, OCR/provenance, doctor verification | **CONDITIONALLY ACCEPTED — SYNTHETIC EDUCATIONAL ONLY** (strict GOLD technical FAIL retained) | [merged #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) | `006ecf417f023428ab90c35cbb0638995c246774` | [Owner closure record](../phase-reports/P3_FINAL_CONDITIONAL_ACCEPTANCE_20261119.md): Windows Pytest **833 passed / 4 skipped**; full gate **12 PASS / 0 FAIL / 1 optional E2E SKIP**; deterministic fixtures **7/7 PASS**; Alembic **8/8 PASS**; SQLite invariants PASS; W1/W2 real-engine application controls PASS; pre-merge and post-merge Backend/Frontend CI SUCCESS. **GOLD-EX-11=FAIL / NOT PROVEN**; exit 2, `1O5`→`105`; 27/1/0/1 preserved. | **Owner conditional educational acceptance — 2026-11-19** ([decision](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995753177), [review amendment](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6995977559)); NOT FOR CLINICAL USE |
| P4 | Monitoring + demo review rules | TODO | — | — | Not run | Pending |
| P5 | LangGraph agents + Ollama + approval | TODO | — | — | Not run | Pending |
| P6 | Doctor/patient UI + follow-up tasks | TODO | — | — | Not run | Pending |
| P7 | Robustness, safety and evaluation | TODO | — | — | Not run | Pending |
| P8 | Demo + final handoff | TODO | — | — | Not run | Pending |

---

## P0 Owner Approval and Architectural Decisions

**Decision date:** 2026-11-14

**Decision:** The project owner approved the Phase 0 architectural direction and authorized completion of the Phase 0 governance milestone.

The following decisions are approved as the implementation baseline:

1. **ADR-0001 — Monorepo / Single-Service Architecture:** Approved for the local MVP.
2. **ADR-0002 — Local Ollama with Labelled Fallback:** Approved, with no paid API dependency.
3. **ADR-0003 — SQLite Application Database and Checkpoints:** Approved, subject to the documented recovery and reconciliation contracts.
4. **ADR-0004 — Evidence-Verified Review Queue:** Approved, requiring human verification of extracted document facts.
5. **ADR-0005 — Deferred External Communications and EHR Integration:** Approved. No real SMS, email, WhatsApp, external patient messaging or EHR integration in the MVP.
6. **ADR-0006 — Five Bounded Agents in a Single LangGraph:** Approved as the implementation direction. The bounded-agent interpretation remains subject to compatibility with the actual DEPI evaluation rubric.

Additional owner-approved implementation boundaries:

- **Synthetic-first:** Build and validate the MVP using fictional, clearly labelled synthetic medical data.
- **Future real-data evaluation:** May be considered separately after the end-to-end system is completed, using appropriately licensed and de-identified datasets. This is not an approved expansion of the current MVP.
- **Doctor-in-the-loop:** Human verification and doctor approval remain mandatory at the documented workflow gates.
- **No autonomous medical decisions:** The system must not independently diagnose, prescribe, assign clinical risk or provide treatment recommendations.
- **Demo-only review parameters:** Numeric demo triggers and the injected clock are synthetic evaluation settings, not clinical thresholds.
- **Observation trust labels:** `self_reported_validated` observations may be used when admissible but must never be described as doctor-verified.
- **Closed measurement mapping:** Version `map-1.0.0` is the approved baseline. The MVP maps at most one measurement tuple per document and must not guess associations in multi-test reports.
- **Evidence and traceability:** Agent outputs must remain source-grounded, auditable and subject to the documented constraints.

This owner approval records the decision to implement the above architecture. Individual ADR documents may retain their original `Proposed` metadata until a separate documentation synchronization updates those headers.

**P0 exit decision: PASS.**

---

## P0 Evidence — Final Accepted Baseline

| Item | Value |
|---|---|
| Scope | Documentation and governance only — no application, dependency installation, database migration, or model implementation |
| Deliverables | 12/12 addressed; see `docs/phase-reports/PHASE_0_REPORT.md` §2 |
| PR | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) — **MERGED** |
| Original base | `7d2ef73dae50c7404b46f653942eb99351053059` |
| Final PR head | `2eace34801d4140cba7b698d9be6d8632a6d9ad6` |
| Merge commit | `442256606fd2465439409cc9b4d42f1bec09a723` |
| Merge date | 2026-11-14 |
| Changed files | 30 files in the merged P0 PR |
| Documentation checker | 29 Markdown files checked; 41 relative links; 0 broken links; 0 bad anchors, as reported in P0 evidence |
| Requirements traceability | 50 defined, 50 traced, 50 used; no reported gaps |
| Evaluation inventory | 96 declared test IDs; 60 referenced; no referenced-but-undeclared IDs |
| OpenAPI | OpenAPI 3.1.0 structurally validated; 30 paths, 56 schemas |
| Targeted contract checks | Document-level Pydantic `MappingVersion` validation and OpenAPI extraction-attempt projection consistency checks executed and reported |
| Security/document checks | Prohibited-claim scanning, secret/runtime-artifact scanning and cross-document consistency checks reported |
| Final technical review | `5904590155` — documentation ready for owner sign-off |
| Owner decision | **Approved — 2026-11-14** |
| Local Git verification | `main` synchronized with `origin/main`, clean working tree, exact merge SHA confirmed using PowerShell |
| Application runtime tests | **NOT RUN — application code does not exist in P0** |
| Clinical validation | **NOT PERFORMED — not a clinical validation milestone** |

### P0 Local Git Verification

Executed on the owner's Windows laptop:

**Repository path:**

`E:\DEPI\AI-Doctor-FollowUp-Agent`

**Commands:**

```powershell
git switch main
git pull --ff-only origin main
git status
git log -1 --format="%H"
```

**Observed results:**

- Fast-forward from `7d2ef73` to `4422566`.
- `main` up to date with `origin/main`.
- `nothing to commit, working tree clean`.
- Final commit:

```text
442256606fd2465439409cc9b4d42f1bec09a723
```

These checks confirm repository synchronization, not application functionality.

### P0 Checks Not Executed

The following checks were **not executed** during P0 because application runtime components were not implemented:

- Backend and frontend runtime tests.
- Ruff against implemented application code.
- Database migrations.
- OCR and live Tesseract evaluations.
- Ollama inference and model benchmarks.
- LangGraph runtime and checkpoint recovery tests.
- Playwright browser end-to-end tests.
- Windows application quality-gate scripts.
- GitHub Actions application CI.
- Live application performance measurements.

All future tests remain `NOT RUN` until their respective implementation phases provide executable evidence.

---

## P0 Review History

### Review Round 1 — `5904454222`

**Findings:** `P0-R01` through `P0-R07`, plus the ADR-0006 agentic-depth concern.

**Resolution:** All findings addressed in the Phase 0 documentation.

Major corrections included:

- Case B comparison arithmetic and Case C chronology.
- Separation of pre-verification `VI-*` issues from post-verification `DR-*` review prompts.
- Deterministic task identity and idempotency.
- Observation trust-level distinctions.
- Document-only measurement handling.
- Injected and reproducible demo clock.
- Bounded agentic decision loops.

**Content commit:** `81df966b2fe80ab842f3405b32cfabc2f1b3a5e7`

**Final disposition:** Resolved.

### Review Round 2 — `5904505998`

**Findings:** `P0-R08` through `P0-R11` and three test-realism recommendations.

**Resolutions:**

- `P0-R08`: Typed graph-trace detail payloads and extraction-attempt metadata.
- `P0-R09`: Application database as the source of truth, two-phase finalization and restart reconciliation.
- `P0-R10`: Closed verified-fact-to-observation mapping, `REQ-DATA-05` and `MAP-01`.
- `P0-R11`: Shared observation-admissibility predicate and `TRUST-02`.
- Deterministic `AD-01` test design using a mocked extractor.
- Separate `OCR-LIVE-01` measurement plan for real Tesseract behavior.
- Explicit Case C candidate-fact count and computed `VI-002` message.

**Content commit:** `b3605ec484a38b15aec5bb153586fecda187ea1d`

**Final disposition:** Resolved.

### Review Round 3 — `5904552354`

**Findings:** `P0-R12` through `P0-R14`.

**Resolutions:**

- `P0-R12`: Distinct `MappingVersion` type and documented validation rules.
- `P0-R13`: `ExtractionAttemptSummary` as an intentional redacted public API projection.
- `P0-R14`: One-measurement-tuple-per-document limitation, negative fixture `GOLD-NEG-10` and corrected `REPORT-B-01` identifier.
- No new requirement IDs, endpoints or ADRs were introduced.

**Content commit:** `c110aa68c2ae60df4594dd62c196cc45919b9cb8`

**Final disposition:** Resolved.

### Final Technical Review — `5904590155`

**Reviewed HEAD:**

`2eace34801d4140cba7b698d9be6d8632a6d9ad6`

**Outcome:** Architecture and governance documentation ready for owner sign-off.

**Remaining blocking P0 findings:** None identified.

**Non-blocking implementation safeguard for P3:**

`MAP-01` must confirm that a multi-test document never creates an observation while measurement associations remain ambiguous, including partially verified and fully verified multi-test states.

A human verification action must not implicitly choose a measurement tuple.

This safeguard must be checked during P3 implementation before the document-ingestion phase is accepted.

**Final disposition:** Owner-approved and merged.

---

## P1 Entry Readiness

**Phase:** P1 — Foundation and Reproducible Startup

**Current status:** `PASS` — PR [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4) **merged** on 2026-11-14 at `2c85db4d9fe9f17080146d12adfbd030a05cc75d`. Owner verified Windows tests and both normal/spaced-path lifecycles, reviewed CI, approved the documented limitations and authorized the merge. Evidence: `docs/phase-reports/PHASE_1_REPORT.md` §13 (Windows), §14 (post-merge record).

**Prerequisite:** P0 accepted and merged — satisfied.
**Base commit of the P1 branch:** `a33e693ba16560836312351787769ec5ee18b469`.

### Owner Laptop Environment

Read-only environment inspection performed on 2026-11-14:

| Component | Observed Value | Note |
|---|---|---|
| Operating system | Windows | PowerShell-based local workflow |
| Python | `3.12.9` | Selected implementation target; Python 3.14 is also installed but must not be selected accidentally |
| pip | `25.3` | Available for Python 3.12 |
| Node.js | `24.15.0` | Installed |
| npm | `11.17.0` | Working through `npm.cmd` |
| Git | `2.50.0.windows.2` | Installed and working |
| Local repository | `E:\DEPI\AI-Doctor-FollowUp-Agent` | Synchronized with merged P0 |
| E: free space | Approximately `71.21 GB` | Observed before P1 installation |

**PowerShell compatibility note:**

Calling `npm` invokes `npm.ps1`, which was blocked by the current PowerShell execution policy.

Calling `npm.cmd` succeeded without changing execution-policy settings.

P1 PowerShell scripts should use `npm.cmd` where appropriate and must not require weakening system security settings.

**Storage note:**

Project virtual environments, local runtime files, dependencies and test artifacts should be placed on the E: workspace wherever configurable, with generated artifacts excluded from Git.

### P1 Required Deliverables (delivery status)

| # | Deliverable | Status in the submitted P1 PR |
|---|---|---|
| 1 | Python 3.12-based reproducible backend environment | Implemented. **Executed on the owner's Windows laptop with Python 3.12.9** (`.venv`, hash-locked install, editable backend import) and on Linux with 3.11.2; CI also runs it on 3.12 |
| 2 | FastAPI scaffold with `/health` and `/version` | Implemented and executed (HTTP 200, `status=ok db=ok`, `api_version=v1`) — locally and on the owner's laptop |
| 3 | React, TypeScript and Vite frontend scaffold | Implemented; dev server, preview server and production build executed; page verified rendering on the owner's laptop |
| 4 | SQLite application database initialization | Implemented and executed |
| 5 | Alembic baseline migration (reversible) | Implemented and executed (up/down/up) |
| 6 | Dependency declarations, lockfiles, `.env.example` | Implemented (hash-pinned locks + `package-lock.json`) |
| 7 | Strict `.gitignore` | Implemented; repository scan passes |
| 8 | PowerShell `preflight` / `setup` / `start` / `stop` / `test_all` | Implemented and **executed on the owner's Windows laptop**: `preflight` PASS, `setup` PASS (86.4 s from the space-containing path), `start`/`stop` PASS on both paths, `test_all` 12 PASS / 0 FAIL / 1 optional SKIP |
| 9 | Backend unit and smoke tests | Implemented and executed (**121 passing** on Linux; also green in CI on Python 3.12) |
| 10 | Frontend build and test verification | Implemented and executed (**13 passing**, build OK) |
| 11 | Ruff and applicable source checks | Implemented and executed (clean) |
| 12 | GitHub Actions CI foundation | **Delivered and run green.** Workflow committed by the owner at `6d09b66`; run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) SUCCESS (backend Python 3.12 + frontend Node 22). The agent could not push workflow files (its token lacks the `workflows` permission); the owner added the file |
| 13 | Phase 1 implementation report with actual evidence | `docs/phase-reports/PHASE_1_REPORT.md` — including the owner Windows verification appendix (§8) |

### P1 Acceptance Gate

P1 is now **PASS**. The checks below were satisfied on the owner-verified code head `eec6642`, followed by the final docs-only head `58a0652` and owner-approved merge `2c85db4d9fe9f17080146d12adfbd030a05cc75d`.

- A clean installation can reproduce the documented environment. — **Met:** clean clone
  reproducibility on Linux, plus `setup.ps1` PASS from a clean space-containing path on
  the owner's Windows laptop (Python 3.12.9).
- The FastAPI health endpoint responds successfully. — **Met:** HTTP 200, `status=ok db=ok`
  (locally and on Windows).
- The frontend starts and loads locally. — **Met:** GET / HTTP 200 and the status page
  rendered with the correct dependency states, versions and notice.
- Database initialization and Alembic migration succeed. — **Met** (up/down/up, baseline
  `0001_p1_baseline`).
- Required backend tests pass. — **Met:** 121 passing locally and in CI on Python 3.12.
- Required frontend checks pass. — **Met:** 13 passing, lint and typecheck clean, build OK.
- GitHub Actions CI passes. — **Met:** run `43615782079` SUCCESS.
- Required PowerShell quality-gate scripts execute successfully on the owner's laptop. —
  **Met:** `test_all.ps1` 12 PASS / 0 FAIL / 1 optional SKIP, plus 14/14 and 38/38
  regression checks.
- No secrets, real patient data or disallowed runtime artifacts are committed. — **Met:**
  repository scan PASS.
- The P1 pull request passes independent review. — **Met on functionality:** P1-R01–R09
  addressed; no open functional blockers identified.
- The project owner explicitly approves and merges the P1 pull request. — **Met:** owner approval recorded in the review and [PR #4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4) merged 2026-11-14.
- The exact merge SHA and execution evidence are recorded. — **Met:** `2c85db4d9fe9f17080146d12adfbd030a05cc75d`; Windows verification and CI are documented here and in the P1 report.

**Optional, not part of the gate:** the Playwright browser smoke test was **NOT
EXECUTED** — browser binaries were unavailable in the authoring environment. It is
reported as `SKIP` by both the spec and `test_all.ps1`, never as a pass.

The implementation agent must use a dedicated P1 branch and PR.

**No direct commits to `main`, no self-approval and no automatic merging.**

---

## P1 Evidence — Accepted and Merged

**Status:** `PASS`. Owner approval and merge were confirmed on 2026-11-14. Historical pre-merge execution evidence remains attributed to its actual code head.

| Item | Value |
|---|---|
| Scope | Foundation only: monorepo layout, FastAPI `/health` + `/version`, React/TS/Vite status page, SQLite + Alembic baseline, hash-pinned locks, Windows scripts, CI, guides |
| Branch | `arena/d86c4f98-ai-doctor-followup-agent` |
| Base commit | `a33e693ba16560836312351787769ec5ee18b469` |
| Owner-tested code head | `eec6642ba700be25f8be1d645bb099f51a665441` |
| Final PR head | `58a0652469fbea9f7ad3a13752993a908b5373ea` (docs-only delta from owner-tested head) |
| Merge SHA | `2c85db4d9fe9f17080146d12adfbd030a05cc75d` |
| Deliverables | 13/13 addressed; see `docs/phase-reports/PHASE_1_REPORT.md` §3 |
| Backend tests | `python -m pytest -q` -> 121 passed (exit 0); also green in CI on Python 3.12 |
| Frontend tests | `npm test` -> 13 passed (exit 0) |
| Lint / format | `ruff check .` and `ruff format --check .` -> clean (exit 0) |
| Frontend build | `npm run build` -> built successfully (exit 0) |
| Migration | `alembic upgrade head` / `downgrade base` / `upgrade head` -> `0001_p1_baseline` (exit 0) |
| Health endpoint | `GET /health` -> HTTP 200, `status=ok`, `db=ok` (live Uvicorn process; local and Windows) |
| Version endpoint | `GET /version` -> `api_version=v1`, real git SHA |
| Repository scan | `scan_repository.py` -> PASS, 0 secrets, 0 tracked artefacts, 0 forbidden claims |
| GitHub Actions | **PASS** — run [`43615782079`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43615782079) SUCCESS (backend Python 3.12 + frontend Node 22) |
| Windows PowerShell gate | **PASS on the owner's laptop** — `test_all.ps1`: 12 PASS / 0 FAIL / 1 optional SKIP |
| Windows regression suites | `invoke_native.tests.ps1` **14 checks PASS**; `stop_identity.tests.ps1` **38 checks PASS** |
| Windows live lifecycle | `setup` -> `start` -> `health` -> `stop` PASS on the normal path **and** on `E:\DEPI\AI Doctor FollowUp Agent Space Test`; ports 8000/5173 free afterwards; all three tracking files removed |
| Playwright browser smoke | **NOT EXECUTED** — optional gate; browser binaries unavailable in the authoring environment (and not installed on the owner's run). Reported `SKIP`, never as a pass |
| Python 3.12 execution | **Executed on Windows (3.12.9) and in CI**; the authoring sandbox used 3.11.2 |
| Application scope | No patient, auth, OCR, monitoring, agent, task or messaging code exists in P1 |
| Owner decision | **Approved 2026-11-14** — docs-scope exception accepted, private-repo license selection and historical dependency-doc sync deferred, optional Playwright SKIP acknowledged, PR #4 merged |

See `docs/phase-reports/PHASE_1_REPORT.md` §7 for exact commands, exit codes and the list of
checks that were *not* executed and why. No test count, timing or result in this table is
estimated; each came from a command actually run in the implementation session.

---

## P1 Owner Acceptance and Merge Record — 2026-11-14

- **Phase result:** `PASS`. Owner gave explicit approval after independent technical review and green Windows / GitHub CI checks.
- **Merged PR:** [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4), final PR head `58a0652469fbea9f7ad3a13752993a908b5373ea`, merge SHA `2c85db4d9fe9f17080146d12adfbd030a05cc75d`.
- **Owner Windows evidence:** regression suites 14/14 and 38/38; full `test_all.ps1` **12 PASS / 0 FAIL / 1 SKIP**; FastAPI and Vite normal-path and spaced-path setup/start/stop PASSED, ports free, state/PID files removed after clean shutdown.
- **CI:** final-head [run 43618740952](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43618740952) succeeded on backend Python 3.12 and frontend Node 22.
- **Owner governance decisions:** P1 documentation path exception (`P1-OPEN-02`) accepted; no license is granted at present and license/copyright convention (`P1-OPEN-01/08`) explicitly deferred while the repository remains private, to be decided before public distribution or a separately agreed gate; historical `DEPENDENCIES.md` sync (`P1-OPEN-03`) deferred to P2; optional Playwright browser smoke **NOT EXECUTED** and accepted as a non-blocking SKIP.
- **Safety boundary:** educational, synthetic-only, local-first foundation; no clinical validation or patient data handling claimed. P2 has **not started**.

---

## Required Evidence for Every Phase

Each future phase must record:

- Scope and acceptance criteria.
- PR URL and exact base/head commits.
- Changed-file list.
- Tests with actual commands, outcomes and execution environment.
- Pass/fail/skipped/not-run counts as genuinely observed.
- Local PowerShell results when applicable.
- Security and safety changes.
- Known limitations and unresolved issues.
- Owner approval decision.
- Exact merged commit SHA.

Do not prefill future pass results, test counts, benchmarks or model metrics.

---

## P2 Scope Authorization Record

### Owner authorization — file-scope exceptions only (2026-11-14)

Recorded **verbatim** from the owner's comment on PR #7:
<https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6881832444>

> **Owner Authorization — P2 File-Scope Exceptions**
>
> Approved: P2 scope exceptions A1–A3, B1–B2, C1–C2, D1–D2, E1–E2, F1–F2, G1–G3, H1–H3.
>
> I explicitly authorize modifications to the exact 19 physical file paths in the revised PR #7 scope matrix at head `58b60f83f50f77e6cd1c30b00019cf5c4f1de267`.
>
> This authorization is limited to completing P2 implementation and testing.
>
> I accept the following P2 design decisions:
> - PBKDF2-HMAC-SHA256 with 600,000 iterations and unique salts.
> - The bounded `session` and `checkin_idempotency` tables.
> - The restored database-enforced `user.patient_id` foreign key.
> - `DEMO_MODE=false` by default and operator-provided demo credentials.
> - Local CLI bootstrap without a new HTTP seed endpoint.
> - Deferral of `GET /api/v1/demo/status` to P5, without fabricating provider functionality.
>
> **Mandatory:** Address all findings in mentor review #5906194976 before requesting final P2 acceptance, including OpenAPI path counting, Alembic downgrade semantics, actual concurrent check-in handling, password rehash claims, requirement-to-test mapping and migration foreign-key safety.
>
> Record this authorization verbatim in `docs/roadmap/PHASE_PROGRESS.md`.
>
> Continue on the SAME P2 branch and draft PR #7. Preserve P1 behavior and all approved safety boundaries.
>
> **This is FILE-SCOPE AUTHORIZATION ONLY. It is NOT code approval, merge authorization, phase PASS acceptance or permission to begin P3.**
>
> Complete the implementation, run the full quality gates, report exact results and stop for independent review and owner Windows verification.

### The authorized 19 paths (8 groups)

| Group | Paths |
|---|---|
| A — assembly | `backend/app/main.py`; `backend/app/api/v1/__init__.py`; `backend/app/api/v1/router.py` |
| B — doctor routes | `backend/app/api/v1/doctor/__init__.py`; `backend/app/api/v1/doctor/patients.py` |
| C — patient routes | `backend/app/api/v1/patient/__init__.py`; `backend/app/api/v1/patient/checkins.py` |
| D — demo reset | `backend/app/api/v1/demo/__init__.py`; `backend/app/api/v1/demo/router.py` |
| E — migration | `backend/migrations/versions/0002_p2_patient_domain.py`; `backend/migrations/env.py` |
| F — gates | `scripts/python/check_openapi.py`; `scripts/python/check_alembic_smoke.py` |
| G — P1 gate tests | `backend/tests/test_openapi.py`; `backend/tests/test_safety_guards.py`; `backend/tests/test_database.py` |
| H — docs/config | `.env.example`; `docs/phase-reports/PHASE_2_REPORT.md`; `docs/roadmap/PHASE_PROGRESS.md` |

No path outside this list (plus the `AGENTS.md` §5 P2 allowlist:
`backend/app/{api/v1/auth,core,db,schemas,services}/**`, `data/synthetic/**`,
`backend/tests/p2/**`) was modified. `main` was never touched.

### P2 evidence — CI verification addendum (2026-11-14)

Recorded after mentor review `5906286395`. Provenance is kept explicit and the
two observations are not merged:

| Observer | CI evidence | Meaning |
|---|---|---|
| Implementer (agent) | `403 Resource not accessible by integration` on every Actions/Checks read — **NOT OBSERVED** | Permission limitation of the automation credentials; **not** a CI failure |
| Independent reviewer | workflow run `43625331149` at HEAD `dbaf938ecb2e8abd39759f7856f083d2efe11cad` — **COMPLETED / SUCCESS**; Backend Python 3.12 **SUCCESS**; Frontend Node 22 **SUCCESS** | The 3.12 and Node 22 legs pass at that head |
| Independent reviewer | workflow run `43625989736` at docs-only HEAD `6d54edeb65b31c437537010329027f6ea33d0aa1` — **COMPLETED / SUCCESS**; Backend Python 3.12 **SUCCESS**; Frontend Node 22 **SUCCESS** | The 3.12 and Node 22 legs also pass on the documentation-only commit (two Markdown files), which supersedes the earlier "docs commits lack CI" caveat |
| Owner Windows gate | **PENDING** | `test_all.ps1`, migrations, bootstrap, API smoke on an isolated worktree — see `PHASE_2_REPORT.md` §10 |

Because the reviewer resolved the CI question, **no Open Question was opened for
it**. P2 remains **IN REVIEW**: CI success is not code approval, not merge
authorization and not a phase PASS. The later documentation commits
(review-driven §10 corrections) are docs-only; their CI, if wanted, is read on
PR #7 → *Checks* and is not assumed here.

### P2 evidence — owner Windows verification addendum (2026-11-14, PASS)

Recorded after the owner executed `PHASE_2_REPORT.md` §10 on an isolated review
worktree. The class of evidence is owner-executed Windows, distinct from the
implementer's 3.11 sandbox numbers and from the reviewer-verified CI.

| Item | Value |
|---|---|
| Verified code snapshot | `9fddb51ba7672efd992c47325ab4883734da3c9a` |
| Environment | Windows **PowerShell 5.1**, **Python 3.12.9**, worktree `E:\DEPI\P2-Review` |
| Evidence | owner comment [`6882774686`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6882774686) |
| Decision | **Owner Windows verification: PASS** — verification evidence only, **not** P2 approval or merge authorization |

| Verification (owner) | Result |
|---|---|
| Isolated worktree + installation | PASS |
| `test_all.ps1` full gate | **12 PASS / 0 FAIL / 1 optional SKIP**, exit 0 |
| Backend pytest / frontend tests | PASS / 13 passed |
| Alembic P2 → P1 → P2 | PASS |
| OpenAPI contract | 11 paths / 12 operations / 22 schemas — PASS |
| Synthetic bootstrap | 6 users, 3 patients, 3 encounters, 17 observations — PASS |
| Startup, health, auth, token rejection | PASS |
| RBAC and patient isolation | 9 checks PASS |
| Check-ins and idempotency | 8 checks PASS |
| Demo reset and session revocation | 7 checks PASS |
| Identity-safe shutdown | PASS |
| `main` HEAD / clean tree / DB SHA-256 | Unchanged / clean / byte-identical |
| PBKDF2-HMAC-SHA256, 600 000 iterations | hash **550.49 ms**, verify **537.67 ms**; wrong password rejected; `needs_rehash` passed |
| Optional Playwright smoke | **SKIPPED — not run, not passed** |

Two owner-side PowerShell *test-command* errors (reserved `$PID`, Python `-c`
quoting, plus one interpolation fix) were corrected and rerun; **no application
code change was required**. The implementation at `9fddb51` did not change.

CI at the same commit: run [`43626628577`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43626628577) — **SUCCESS** (Backend Python 3.12 SUCCESS, Frontend Node 22 SUCCESS).

**Follow-up on top of the owner-tested snapshot (test-only).** Independent review
[`5906711140`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#pullrequestreview-5906711140)
identified an intermittently flaky assertion in
`backend/tests/p2/test_p2_auth_http.py` (the random `request_id` UUID can contain
the submitted substring `ab`). The test now asserts on the user-facing validation
text only, a deterministic regression test pins a client `X-Request-ID` containing
`ab`, and the pair passed **25/25** targeted runs; a mutation reintroducing the old
behaviour fails the regression test. **The implementation is unchanged** — the
owner-tested code snapshot is still `9fddb51ba7672efd992c47325ab4883734da3c9a`;
later commits are test and documentation only, so the live Windows API/bootstrap
lifecycle does not need repeating (the owner may re-run `test_all.ps1` on the new
checkout).

This PASS does **not** change the phase state: **P2 remains `IN_REVIEW`**, the
Owner Approval column stays **Pending**, no merge SHA exists and P3 is not started
*(historical pre-merge state at `9fddb51` / `b2bb159`; superseded post-merge by the
factual closure record below)*. Known limitations are unchanged by a passing gate
(see `PHASE_2_REPORT.md` §11).

### P2 status

**PASS — owner-approved on 2026-11-14 ([comment 6883198256](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256)) and merged into `main` at `777f6618c62560be41cce394218c87b0c683981f`.**

See `docs/phase-reports/PHASE_2_REPORT.md` (§10.11, §10.12, §15) for full evidence, limitations and rollback.

---

## P2 Post-Merge Factual Closure Record — PR #7 (Merged 2026-11-14)

Recorded after GitHub merged PR [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) into `main` following independent technical review and the owner's explicit acceptance and merge authorization ([comment `6883198256`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256)).

| Item | Verified Record |
|---|---|
| Scope | Patient data domain (`user`, `patient`, `encounter`, `observation`, `session`, `checkin_idempotency`, `audit_event`), reversible Alembic migration `0002_p2_patient_domain`, opaque bearer sessions, PBKDF2-HMAC-SHA256 (600,000 iterations, unique salts, `needs_rehash`), server-side RBAC, idempotent self-reported check-ins, deterministic synthetic bootstrap/reset, strict 11-path / 12-operation / 22-schema OpenAPI allowlist |
| Pull request | [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) (`arena/a8844cc2-ai-doctor-followup-agent` → `main`) — **MERGED** on 2026-11-14 |
| Accepted prior `main` base | `d1ec0b9b481dca313c8ea2f21f97872582fc5a86` |
| Owner live-Windows-tested implementation snapshot | `9fddb51ba7672efd992c47325ab4883734da3c9a` ([comment `6882774686`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6882774686)); subsequent commits on PR #7 modified only tests and Markdown documentation |
| Final merged PR head | `b2bb1594fd89b26fed1ea5201302d6aac4c04698` |
| Verified GitHub merge SHA | `777f6618c62560be41cce394218c87b0c683981f` ([post-merge comment `6883243529`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883243529)) |
| Changed files in PR #7 | 61 files total: 42 within the `AGENTS.md` §5 P2 default allowlist plus the exact 19 owner-authorized paths (`6881832444`) |
| Independent final technical review | [`5906757356`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#pullrequestreview-5906757356) (2026-11-14) — readiness recommendation at exact head `b2bb1594fd89b26fed1ea5201302d6aac4c04698`; zero unresolved review threads |
| Final-head GitHub Actions CI | Run [`43632732091`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43632732091) on `b2bb1594fd89b26fed1ea5201302d6aac4c04698` — **COMPLETED / SUCCESS** (Backend Python 3.12 **SUCCESS**, Frontend Node 22 **SUCCESS**, verified in review `5906757356` and comments `6883198256` / `6883243529`; direct Actions API reads from the Arena session return HTTP 403 *Resource not accessible by integration*, an observer credential limitation) |
| Owner final Windows regression (`b2bb159`) | Executed on Windows PowerShell 5.1 / Python 3.12.9 in an isolated worktree: `scripts/powershell/test_all.ps1` **12 PASS / 0 FAIL / 1 optional SKIP** (`test_all result: PASS`, `P2 FINAL WINDOWS REGRESSION: PASS`, `MAIN ISOLATION: PASS`; Backend pytest PASS [exact Windows test count not printed in console summary], Ruff lint/format PASS, Alembic upgrade/downgrade/upgrade PASS, OpenAPI `11 paths / 12 operations / 22 schemas` PASS, frontend typecheck/lint/build PASS, 13 frontend tests PASS, tracked secret scan PASS on 143 files, 14 command-wrapper checks PASS, 38 stop-identity checks PASS) |
| Optional Playwright browser smoke | **SKIPPED — not executed, not passed** (acknowledged optional skip in both `9fddb51` and `b2bb159` runs) |
| Post-merge local Git & SQLite verification | Owner local `main` (`E:\DEPI\AI-Doctor-FollowUp-Agent`) fast-forwarded cleanly to exact merge SHA `777f6618c62560be41cce394218c87b0c683981f`; original `main` SQLite database remains byte-identical |
| Posted owner decision record on GitHub | [Owner comment `6883198256`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256) (2026-11-14) recorded explicit owner P2 acceptance and merge authorization for exact PR #7 head `b2bb1594fd89b26fed1ea5201302d6aac4c04698` against `main` baseline `d1ec0b9b481dca313c8ea2f21f97872582fc5a86`, with bounded MVP limitations accepted |
| Official ledger Phase Status (`AGENTS.md` §2) | **PASS** |
| Official ledger Owner Approval (`AGENTS.md` §2) | **Approved — 2026-11-14** ([owner comment `6883198256`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7#issuecomment-6883198256); bounded MVP limitations and optional Playwright SKIP acknowledged) |
| P3 status | **TODO — not started, not authorized by this closure** |

### Accepted P2 Bounded Limitations (recorded in owner comment `6883198256`)

- **Optional Playwright smoke:** **SKIPPED (not passed)** — browser binaries were not installed; never counted as an executed pass.
- **In-process login rate limiting:** `LoginRateLimiter` is per-process memory (`ASM-06`), appropriate only for the single-worker local demo.
- **SQLite single-machine concurrency bounds:** Two-writer `IntegrityError` replay/`409` recovery and partial unique index `uq_observation_checkin_identity` are verified for SQLite serialized connections, without claiming multi-process worker safety or automatic conversion of sustained `OperationalError: database is locked` contention.
- **Demo reset operator secret and session invalidation:** `POST /api/v1/demo/reset` requires `DEMO_SEED_PASSWORD` in the running backend process environment at launch (`500 E_INTERNAL` if unset) and deletes all `session` rows, revoking active bearer tokens.
- **Bounded schema and hashing choices:** Internal tables `session` and `checkin_idempotency` (owner-accepted additions to the P0 data dictionary) and stdlib PBKDF2-HMAC-SHA256 at 600,000 iterations (`needs_rehash` wired; Argon2id deferred to avoid out-of-scope dependency changes).
- **Deferred and excluded surfaces:** `GET /api/v1/demo/status` (`OQ-P2-01`) deferred to P5; `NEG-01` document extraction not applicable until P3; `POST /api/v1/demo/seed` excluded by contract; private-repo license selection (`P1-OPEN-01/08`) and historical `DEPENDENCIES.md` sync (`P1-OPEN-03`) remain deferred as previously recorded.
- **Safety boundary:** Synthetic-data, local-first educational MVP stage only — **NOT FOR CLINICAL USE**; no clinical deployment, diagnosis, prescribing, external patient messaging, or clinical validation is claimed.

---

## P3-R21 Owner Authorizations — rejection recovery (2026-11-16)

Recorded because `AGENTS.md` §1/§2 require every owner decision and authorization to
reach this ledger, and because P3 remains `IN_REVIEW`.

**Authorization source:** owner review
[`5918885024`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5918885024)
(Stage 1), review
[`5920025835`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5920025835)
(Stage 2 acceptance), and the subsequent owner message authorizing Stages 3–5. The
design that these authorize is `docs/phase-reports/P3_R21_REJECTION_RECOVERY_DESIGN.md`
at `e1d76a6`.

**Approved engineering direction ("Approach A"), owner's wording:**

> Reuse `failed` with typed rejection failure codes. Apply the rejection-first
> terminal-state rule to any active rejected fact. Preserve D-11 append-only
> decisions and D-14 issue counting. Require a `verified` document status before
> Observation promotion. Use a new patient-uploaded document with `recovery_of`
> and durable lineage. Expose patient-safe recovery metadata. Preserve existing
> identity, authorization and duplicate-upload protections.

**What this authorizes, bounded:**

* **Stage 2 (landed, accepted at `0bd8e36`):** rejection-first document-state
  derivation; `measurement_rejected` / `fact_rejected`; preserved
  `all_facts_rejected` precedence; superseded originals excluded so a valid
  correction still reaches `verified`; and a promotion gate requiring
  `extraction_status == 'verified'`.
* **Stages 3–5 (this increment):** migration `0004_p3_rejection_recovery`
  (nullable `recovered_from_document_id`, index, self-FK `ON DELETE RESTRICT`,
  downgrade refusal when links exist); the optional `recovery_of` form field on
  the existing upload route with malformed/absent/cross-patient/wrong-state
  refusals; patient-safe `DocumentMeta` fields and doctor-only
  `ExtractionResponse` fields; the `document.recovered` audit event on success
  only; and contract/doc synchronization.
* **Explicitly deferred:** Stage 6 (owner Windows verification), any
  P4/P5 work, merging or approving PR #10, and any change to OCR configuration,
  parser grammar, `preserve_interword_spaces`, or the `GOLD-EX-11` expectations.

**New error-surface facts (no new codes invented):** `recovery_of` refusals reuse
`400 E_VALIDATION` and `404 E_NOT_FOUND`. The absent and cross-patient cases
return the *same* 404 wording as the document read route, so the endpoint cannot
be used to test whether another patient's document id exists.

**Clinical-safety boundary:** the recovery link is a **patient-declared
association**, never validated clinical equivalence. No schema object, message or
audit fragment describes it as corrected, clearer, equivalent or validated. The
recovered document is extracted, `VI-004`/`VI-006`-evaluated and doctor-verified
on its own, and the source document's open `VI-002` stays open and historical
(D-14 unchanged).

**Status:** P3 remains `IN_REVIEW`, PR #10 remains **DRAFT**, P4/P5 remain blocked,
and no PASS claim is made. W1 and W2 remain **Windows-only and unexecuted**; W2's
expected result is **FAIL / NOT PROVEN** and is a preservation check, not an
acceptance gate.

---

## P3 Owner Decisions and Scope Authorizations (2026-11-15)

Recorded because `AGENTS.md` §1/§2 require every owner decision and path exception
to be written into this ledger, and because P3 is `IN_REVIEW` rather than accepted.

### D-14 — `VI-002` counts active candidate facts only (`APPROVED`)

**Authorization source (the only one):** owner comment
[PR #10 issue comment `6900700171`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6900700171),
*"Owner Decision — P3 D-14 and Windows Handoff Scope"*, by `Muhammed-Fathi`, 2026-11-15T20:18:21Z.

Technical review `5912501268` is **not** an approval and is not cited as one: it is
an independent request that produced this decision, so it is referenced only as
prior context below.

**Owner comment, verbatim:**

> **Owner Decision — P3 D-14 and Windows Handoff Scope**
>
> I explicitly approve the narrow P3 interpretation that `VI-002` counts active candidate facts whose verification status is not `verified`.
>
> A rejected original fact superseded by a successfully recorded doctor correction with valid `corrected_from_fact_id` lineage is retained as immutable evidence but excluded from the active-candidate count.
>
> Plain rejected facts, pending facts, and genuinely multi-measurement documents must remain protected by the existing blocking rules.
>
> I also explicitly authorize these two P3-specific paths:
>
> - `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`
> - `scripts/python/windows_ocr_acceptance.py`
>
> I authorize the corresponding narrow `VI-002` clarification in `docs/clinical-safety/DEMO_REVIEW_RULES.md`.
>
> Please synchronize the phase ledger and report to reference **this owner comment**, not the independent technical review as owner approval. Reconcile the test-count wording in the Windows handoff.
>
> This is **not P3 acceptance or merge authorization**. P3 remains `IN_REVIEW`, pending successful owner-side Windows verification and final independent review.

**Prior context (technical, not an approval):** review
[`5912501268`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5912501268)
raised the `VI-002`/`EXTRACTION_PROVENANCE.md` §6 conflict and the Windows handoff
items; the owner then granted D-14 and the two path exceptions above.

**Applied to:** `docs/clinical-safety/DEMO_REVIEW_RULES.md` §4 (trigger) and §6.1
(message count), plus a scoping note in the same section. Only the `VI-002`
trigger/count wording changed; every threshold, policy and clinical-safety
boundary in that document is untouched.

**Implemented by:** `superseded_fact_ids` in
`backend/app/services/documents/quality.py`, which excludes only rows that are
`rejected` **and** referenced by another fact's `corrected_from_fact_id`. Pinned by
`test_p3_r09_plain_rejection_still_counts_for_vi_002` (plain rejections still
count), `test_p3_r09_genuine_two_measurement_document_still_blocks` (P0-R14
unchanged) and `test_p3_r09_corrected_single_measurement_has_no_false_multi_measurement_blocker`.

**Numbering note.** Before this decision the label `D-14` was used in
`PHASE_3_REPORT.md` §J for an unrelated audit retraction (`E_DEPENDENCY_MISSING`).
The owner's `D-14` is authoritative, so that audit row was renumbered to `D-16`
(cross-reference at §L / OQ-P3-10 updated too). No decision content changed.

**Not authorized by D-14:** no automatic verification, no deletion of historical
facts, no weakening of source evidence, no change to `map-1.0.0`.

### R10 — Windows CRLF fixture integrity (`CORRECTED`)

Source: [PR #10 review `5913143695`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913143695) together with the owner's Windows
`test_all.ps1` result at `37ff7ea`: **11 PASS / 1 FAIL / 1 SKIP, exit 1**, the single
failure being
`test_p3_fixtures.py::test_every_recorded_hash_matches_the_committed_source`.

**Root cause (confirmed, not inferred).** The committed source
`data/synthetic/documents/sources/report_a_clean.txt` is **202 bytes** with LF and
SHA-256 `c510153f…290d92`, which is what `manifest.json` records. A
`core.autocrlf=true` checkout on Windows rewrites its four LF endings to CRLF,
producing **206 bytes** and SHA-256 `bfaf9bbb…bebf38` — exactly the digest in the
owner's failure. The fixture content never changed; the *check* hashed checkout
transport instead of canonical content. No `.gitattributes` exists at the reviewed
head.

**Correction (test-only).** `test_every_recorded_hash_matches_the_committed_source`
now canonicalizes `\r\n` → `\n` before hashing and sizing, so the manifest digest
stays exactly as committed and remains the sole authority. Only `\r\n` is rewritten:
a lone `\r`, a `\x00`, an appended byte or any value edit still fails.

**Proof, both directions.** A simulated full CRLF checkout (106 converted files) passes
all 12 fixture tests; tampering `13.4` → `13.9` inside that same CRLF checkout still
fails with `eefef177…` ≠ `c510153f…`. Five regression tests pin LF, CRLF, the exact
owner-observed digest pair, and genuine corruption including a CRLF-file value edit.

**Not done, deliberately:** no fixture or manifest edit, no `.gitattributes`, no
production change, no contract change. Changing checkout attributes would alter every
Windows working tree and needs its own path-specific authorization.

### R11 — pytesseract 0.3.13 integration (`CORRECTED`)

Source: [PR #10 review `5913283150`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913283150) plus the owner's Windows probe run at
`9ee6b4a` (exit 2; `OCR-ENGINE` FAIL, six dependent gates NOT RUN).

**Not a probe defect.** `backend/app/services/documents/ocr.py` — an already-committed
P3 file from `ce96d73` — had two production faults:

1. `engine_version` passed `tesseract_cmd=` to `pytesseract.get_tesseract_version()`,
   which accepts **no arguments** in 0.3.13, so **every** version read raised
   `TypeError`. Callers: `run_ocr` (for `tool_version`), `/health`, and the probe.
2. `run_ocr` resolved the configured executable and then ignored it, because
   pytesseract invokes the module-global `pytesseract.pytesseract.tesseract_cmd`.
   Explicit `TESSERACT_CMD` without a `PATH` entry therefore could not run OCR.

**Fixed** with a `_engine_selected` context manager that installs the resolved path into
the global for the call and restores it afterwards (no cross-request leakage).
`run_ocr` now performs text, confidence and version all against the same binary, so
`tool_version` provenance is accurate by construction.

**Scope:** production code fix inside the existing P3 authorized tree — no new paths,
no dependency change, no contract or clinical-safety change. Confirms review item:
"identify scope/approval before editing if additional authorization is required" — no
additional authorization was needed because `ocr.py` is already a reviewed P3 path.

**Not claimed:** Windows live OCR (`GOLD-EX-05..08/11`, `OCR-LIVE-01`) remains
**NOT RUN** until the owner repeats acceptance on the corrected SHA.

### R12 — process-global OCR executable selection (`CORRECTED`)

Source: [PR #10 review `5913341864`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913341864).

**Confirmed by reproduction**, not assumed: two threads inside `_engine_selected` with
different executables cross-wired, and an out-of-order restore left the global at
`/engine/1` rather than its original value.

**Fixed** with a module-level `RLock` covering the whole save/select/call/restore span.
Re-entrant because `run_ocr` holds the lock while calling `engine_version`, which takes it
again. `tool_version`, exception behaviour and confidence semantics are unchanged.

**Honest limit:** the lock is process-local and cannot coordinate separate processes;
each has its own copy of the module global. That is not a defect of this fix, but it is
not a claim of multi-process safety either.

### R13 — GOLD-EX-11 `1O5` case (`DIAGNOSED; parser correct, gate improved`)

Source: [PR #10 review `5913389560`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913389560).

Owner result `value flags=[] normalized=[]` was **case (b)**: the engine lost the line,
so no value fact existed. The probe rendered the sample with PIL's default bitmap font
(~10 px), which Tesseract cannot reliably read.

Parser is correct and unchanged: a genuine `1O5` yields `normalized_value=None` with
`unparseable_value`, never `105`. Now pinned for six confusion tokens plus a clean control.

Gate improved to distinguish and *name* the three outcomes (`no_value_fact`, `flagged`,
`repaired`) and to record the raw engine text, instead of a bare FAIL. **The gate is
honest about its own limitation:** it can only demonstrate the corruption case when the
engine actually emits an ambiguous token.

### R14 — ING-02 `SecretStr` boundary (`CORRECTED`, plus two hidden probe bugs)

Source: [PR #10 review `5913389560`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913389560).

Probe passed `settings.demo_seed_password` (`SecretStr`) into `seed_demo_data`, so
`seed.py`'s `password.strip()` raised `AttributeError`. Fixed at the probe boundary with
`.get_secret_value()`; the secret is never logged or written to evidence, and the seed
service keeps its own empty-password guard.

Fixing that exposed two further probe defects that had never been reachable: a missing
keyword-only `now` on `issue_session()`, and sessions issued at a fixed midnight so every
token was already expired (`401`). Both fixed; the HTTP path now passes end-to-end with
`tesseract` provenance in both the response and the stored rows.

### R13 refined / R15 — engine substitution and evidence integrity (`CORRECTED`)

Source: [PR #10 review `5913471266`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913471266); owner evidence at `1cbc86a`.

**R13 refined.** The owner's raw OCR text shows Tesseract itself transcribed the rendered
`1O5` as `105` and damaged the `Test:`/unit labels, so the parser emitted no value fact.
This is **not** an application-side correction, and it does **not** demonstrate safe
handling of a plausible-but-wrong `105`. Both are now covered deterministically against
the verbatim OCR text: ambiguous-token preservation, engine substitution with damaged
labels, and a clean-looking `105` with low confidence that is recorded but not trusted.
The gate records the source/engine split and reports **NOT PROVEN** rather than claiming
the case.

**R15.** Two defects behind one symptom:

1. Duplicate verdicts — a gate could PASS and then also FAIL from its teardown path. Each
   gate now yields exactly one verdict; teardown failures get their own `ING-02 teardown`
   identifier so they are visible without corrupting the gate's result.
2. Windows file lock — the `@lru_cache`d engine in `app.db.session` kept a pooled
   connection to the throwaway SQLite file, and `TemporaryDirectory` deleted the directory
   before an outer `finally` could dispose it. Added `dispose_engines(url)` and restructured
   the gate to `mkdtemp` + `finally` (reset settings cache → dispose engines → remove
   directory), on every path.

**Scope note.** `backend/app/db/session.py` is an already-committed P3 file; the added
`dispose_engines` is additive and used only by the acceptance probe and tests. No
production request path changes.

### R16 — cleanup lifecycle completed (`CORRECTED`)

Source: [PR #10 review `5913517645`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913517645). CI at `f376157` was green, but the R15
cleanup was incomplete. Four defects, each reproduced first:

1. The gate's **standalone** engine (`create_db_engine`) was never disposed; a closed
   `Session` leaves its pool holding a SQLite handle (`pool.checkedin() == 1`).
2. `dispose_engines` used `cache_clear()`, which evicted every URL's engine **without
   disposing** any — other engines kept pooled handles and remained usable.
3. `unlink()` proved nothing: Unix unlinks open files, so the old test passed while the
   defect was live. Assertions now use `pool.checkedin() == 0`.
4. The gate never restored its `DATABASE_URL`/`APP_ENV`/`UPLOAD_DIR`/`DEMO_SEED_PASSWORD`
   overrides.

The engine cache is now an explicit URL-keyed dict with per-URL eviction, so `dispose_engines`
affects exactly one database; request-path behaviour (one lazily created engine per URL) is
unchanged. Teardown order in `finally`: dispose standalone engine → dispose cached engine →
restore environment → reset settings cache → remove directory, each step guarded and
reported through the separate `ING-02 teardown` row.

**Not claimed:** no Windows machine was available, so Windows deletion is **unverified**
here. The Windows re-run is the authority.

### R13 fixture — authorized addition (`IMPLEMENTED`)

Owner authorization: PR #10 review
[`5913621837`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913621837),
granting "the narrowly scoped addition of a new synthetic R13 fixture and its manifest
entry, including a legible TrueType rendering approach".

**Added:** `data/synthetic/documents/sources/report_ocr_o_confusion.txt` plus one `manifest.json` entry (`contract_case: GOLD-EX-11`). No
existing source, digest or clinical-safety contract was modified — verified: all eleven
prior sha256 values are unchanged.

**Rendering:** `ImageFont.load_default(size=40)`, i.e. Aileron Regular bundled inside
Pillow. This is why nothing is committed or newly depended on: the licence travels with
Pillow, and rendering is byte-deterministic across machines. `legible_font()` raises on
Pillow < 10.1 instead of silently reverting to the ~10 px bitmap face that failed on
Windows.

**Gate hardening (the part that matters for safety):** the predicate previously accepted
`low_confidence` alone, so a substituted `105` could be reported as a demonstrated
ambiguous-token case merely because the read was also uncertain. Now only *preserved token
+ parser refusal* passes; every substitution path reports **NOT PROVEN**. OCR output,
parser output and human-review status are recorded as three separate layers.

**Not claimed:** no Windows run was possible here. Whether real Tesseract preserves the `O`
at 40 px is the owner's to measure; if it substitutes, the gate says so honestly.

### File-scope exceptions for the P3 Windows handoff (`APPROVED`)

Two paths were added outside the previously approved 26 exceptions, authorized
explicitly by the owner in [issue comment `6900700171`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6900700171),
limited to Windows verification and handoff only:

| Path | Purpose |
|---|---|
| `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` | Executable owner acceptance procedure |
| `scripts/python/windows_ocr_acceptance.py` | Owner-laptop probe for the Windows-only gates |

Authorization is **limited to P3 Windows verification and handoff functionality**;
no other new paths or phase expansions are authorized by it.

### P3 owner environment (authoritative paths)

| Item | Value |
|---|---|
| Main checkout (never mutated by P3 acceptance) | `E:\DEPI\AI-Doctor-FollowUp-Agent` |
| Disposable acceptance worktree | `E:\DEPI\P3-Acceptance` |
| P3 branch (remote-only) | `arena/ce85d4e6-ai-doctor-followup-agent` |
| PR | [#10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) — draft, open |

P3 remains **`IN_REVIEW`**. D-14 is a contract interpretation, **not** a phase PASS or a
merge authorization (the owner comment says so explicitly),
and it does not authorize a merge or any P4/P5 work.

---

## Next Authorized Workflow

1. Preserve the verified merge SHAs and decision records for P0 (`442256606fd2465439409cc9b4d42f1bec09a723`), P1 (`2c85db4d9fe9f17080146d12adfbd030a05cc75d`), and merged PR #7 (`777f6618c62560be41cce394218c87b0c683981f`).
2. Confirm owner local `main` remains synchronized at `777f6618c62560be41cce394218c87b0c683981f` with the original `main` SQLite database byte-identical.
3. P2 administrative closure finalized (`PASS`); any P3 work requires separate owner initiation in a dedicated scoped branch and PR.
4. Carry forward the documented bounded limitations: private-repo license/public-distribution decision, historical `DEPENDENCIES.md` sync, P2 single-process/SQLite/reset-secret bounds, `OQ-P2-01` (`GET /api/v1/demo/status` in P5), and optional Playwright smoke (`SKIP`, never claimed as passed).
5. **Do not start or claim authorization for P3** until the P2 administrative ledger closure is finalized and the owner separately initiates P3 in its own scoped branch and PR.

**Current accepted baseline:** P0 governance (`PASS`), **P1 foundation (`PASS`)**, and **P2 patient data domain & role-scoped API (`PASS`, merged at `777f6618c62560be41cce394218c87b0c683981f`)**.

**Next implementation milestone (not started):** P3 — Document ingestion and OCR verification (**TODO — requires separate owner authorization and its own scoped branch/PR**).

**Project classification:** Educational, synthetic-data, local-first multi-agent workflow assistant.

**NOT FOR CLINICAL USE.**

### R17 — OCR substitution and fail-closed verification (P0 + P1 implemented, P2 design only)

Owner ruling [`5915830616`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5915830616)
ordered safety hardening before OCR tuning, and forbade redefining `GOLD-EX-11`, weakening
verification, or changing the public API contract to obtain green tests.

**Implemented (P0).** A document whose image printed a measurement could reach `verified`
after only its date and reference range were approved, because the `Value:` line was
dropped by the parser (one space where it required two) and `_recompute_document_status`
never required a measurement to exist. The parser now keeps an unattributable `Value:`
line as a `page_missing`-flagged candidate with `normalized_value=None`; `issues` maps
that flag to `VI-005`, and `verified` is refused while a declared measurement has never
been read. No new flag, column, migration or reason code: `page_missing` was already
documented in `EXTRACTION_PROVENANCE.md` §4 for exactly this situation and produced by
nothing. All 12 fixtures parse unchanged.

**Implemented (P1).** Correction values are validated per field (number / closed unit list
/ calendar-valid ISO date / non-blank text) instead of accepting any non-empty string;
`VI-005` closes when a valid correction resolves it; the probe's
`human_review_required` is derived from blocker logic rather than hard-coded. Validation
runs after the identity guard so a wrong-patient document still answers
`409 E_VI_004_UNRESOLVED` and not a cosmetic `400`.

**Not done.** P2 (durable OCR page text) is design-only — it needs a schema and an
endpoint, both forbidden without approval: `P3_R17_P2_OCR_PROVENANCE_DESIGN.md`. P3
recognition experiments are blocked: **no Tesseract binary here**, so
`preserve_interword_spaces` is unmeasured and unclaimed. A zero-fact document still
reports an empty issue list; a destroyed `Value:` label remains undetectable. All three
are stated in the report rather than papered over.

**Evidence.** `backend/tests/p3/test_p3_r17_safety.py` — 24 tests, 14 red against
`1b17a9a`. Full suite **621 passed**, P3 **238**. Gate re-run with a **scripted** engine
(not real Tesseract) on the owner's exact bytes: FAIL / `diagnosis=substituted`,
`human_review_required=True` from `['VI-005']`; preserved-token variant PASS /
`preserved_and_refused`. `GOLD-EX-11` unchanged and still FAIL/NOT PROVEN.

### R18 — corrections to R17's own fallback

Owner review [`5916114433`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916114433)
found two defects in the code R17 added, not in the code it replaced. Both reproduced
first; 12 of 14 new tests were red against `73639d0`.

1. **Span did not resolve to `raw_text`.** `_unattributed_value_facts` stripped the
   token but offset from `label.end()`, so the owner's line claimed
   `raw_text='105 mg/dL'` while its own span resolved to `' 105 mg/d'` — leading space
   kept, final character lost. A >120-char token diverged twice over. The trimmed range
   is now computed once and both fields derive from it, with the span bounded to the
   stored text length. `EXTRACTION_PROVENANCE.md` §3/§5 requires this; it went unnoticed
   because `span_is_resolvable()` checks bounds only.
2. **A bare `Value:` label was dropped.** `if not token: continue` meant a document
   declaring a measurement nobody read produced no evidence and no blocker, and
   approving only its date and reference range reached **`verified`** — the failure R17
   existed to prevent, one branch over. The label is now preserved as literal evidence
   (`'Value:'`, `normalized_value=None`, `page_missing`, blocking `VI-005`). No number is
   fabricated and a bare label is never treated as document-only.

**Not changed, flagged instead:** `span_is_resolvable()` still validates bounds only, so
it cannot catch a future `raw_text`/span mismatch. Equality inside it would change
validation semantics for every fact and was not authorized.

**Evidence.** `backend/tests/p3/test_p3_r18_provenance.py` — 14 tests, 12 red against
`73639d0`. Full suite **635 passed**, P3 **252**. ruff clean (103 files), OpenAPI PASS
(16 paths / 17 operations, unchanged), secret scan PASS (196 files), Alembic smoke PASS
in `head`/`p2`/`p1`/`base`. 12 fixture hashes verify, zero changed. No API, schema or
migration change. `GOLD-EX-11` unchanged and still FAIL/NOT PROVEN. Real-engine
behaviour at this SHA remains unverified — the last real Windows evidence is `1b17a9a`.

---

## P3 E1–E3 — Windows diagnostic evidence addendum (2026-11-18; owner runs, independently reviewed)

**Status update only: NOT an owner P3 acceptance.** No merge, no `main` edit, no work on P4/P5. The findings below supersede earlier *NOT RUN* statements **only for the specific Windows v1.1.2 diagnostic modes named**, not for the original full P3 acceptance script.

| Step | State | Evidence / stop condition |
|---|---|---|
| Authentic v1.1.2 bundle recovered | PASS | ZIP 91,290 bytes, SHA-256 `baa0ce745a2f582433b0fe37061c8f0f41ca05ce2da1c12b50f39b1fb0446437`; five members verified; owner baseline unchanged |
| Independent review | COMPLETED (conditional, historical) | [Bundle inspection](../phase-reports/P3_E1_E3_V112_INDEPENDENT_BUNDLE_REVIEW.md), includes strict launcher, hashes and limitations |
| Windows `plan_only` | **PASS** | Exit 0, runtime Python 3.12.9 / Pillow 13.0.0; `READY_FULL_COVERAGE` with canonical 3 / exploratory 80 / holdout 160; postflight OK |
| Windows `probe_only` | **INCOMPLETE** | Exit **13**, Tesseract 5.4.0.20240606 and `eng` confirmed, canonical image parity PASS, subprocess hOCR rc=0, no timeout, but `no_target_word` caused a rejected capability measurement; full details in [evidence register](../phase-reports/P3_E1_E3_V112_WINDOWS_EVIDENCE.md) |
| Root-cause diagnosis | CONFIRMED FOR HARNESS v1.1.2 | Exact-token target localization fails when intended `1O5` is read as `105`; parser ignores sibling `lstm_choices_*` groups. Real hOCR has 138 groups; target O alternative `x_confs 0` is **not** adequate evidence for correction. [Full engineering handoff](../phase-reports/P3_E1_E3_V112_PROBE_ROOT_CAUSE.md) |
| Protected baseline integrity | PASS | Owner-reported Windows pre/postflight: HEAD and worktree unchanged, protected/main DB digest unchanged, canonical source unchanged; independent raw file hashes matched supplied manifest |
| `canonical_baseline`, `exploratory`, `holdout` | **NOT AUTHORIZED / NOT RUN** | Stop until revised harness audited and new owner gates are complete |
| GOLD-EX-11 | **FAIL / NOT PROVEN** | Do not change golden fixture, infer source correctness from OCR confidence, or weaken thresholds |
| P3 owner PASS / PR merge | **PENDING / NOT AUTHORIZED** | Owner decision only, after accepted real-engine evidence and independent review |

**New engineering handoff:** Arena should prepare an isolated diagnostic harness v1.1.3 with two fixes, regression tests and a separately pinned authenticated Draft Release; preserve all v1.1.2 evidence. Start with [root-cause report](../phase-reports/P3_E1_E3_V112_PROBE_ROOT_CAUSE.md), then the [Windows evidence register](../phase-reports/P3_E1_E3_V112_WINDOWS_EVIDENCE.md). This addendum does **not** authorize direct source changes, acceptance, merge or execution of any subsequent mode.

**Governance / file-scope note:** This documentation-only proposal was requested by the owner to maintain GitHub reports and per-phase status. It is in a separate draft PR targeting the P3 acceptance branch for owner review; documents outside the default P3 implementation allowlist are **proposed scope exceptions pending an explicit owner decision in the PR**, not self-approved by the agent. The owner may authorize and merge documentation separately; only an owner can ratify the phase.

---

## P3 E1–E3 v1.1.3 — Independent source audit (2026-11-18; historical pre-Windows-plan review)

**Phase gate remains P3 IN_REVIEW; GOLD-EX-11 FAIL / NOT PROVEN; P3 draft PR #10 not merged.**

- Authenticated Draft Release ID `449889565` at pinned `af2bfd226cc5`; owner recovered ZIP into a **new** diagnostics-only evidence folder, reporting `AUTHENTICATED BUNDLE RECOVERY: PASS` and `PROTECTED BASELINE POSTFLIGHT: PASS` without running modes.
- Independent ZIP size, archive integrity and **all five member hashes MATCH**: 85,170-byte ZIP SHA-256 `d620208ff0811b7ec6372bc96174cd302daed4dc37664acd104aba5d27cc3cb5`. PowerShell launcher is **byte-identical** to v1.1.2. Source diff introduces grounded bbox localization, sibling `lstm_choices_*` parsing, split failure attribution and Python-level plan postflight.
- Independent replay against **real owner-supplied v1.1.2 Windows hOCR**: geometry localized `word_1_20`, expected synthetic `1O5` versus OCR `105`; 138 choice groups parsed (123 multi), no malformed groups, `O` alternative confidence `0.0` below threshold; output remains `genuine_no_o_zero_alternative` (NOT a corrected clinical value). Exact synthetic sources from accepted Git commit verified.
- Independent sandbox checks: Python syntax **PASS**, **6 of 8** new diagnostic tests reproduced with exact synthetic source texts; two higher-level tests **could not pass in this review sandbox because the complete pinned Git worktree/blobs are absent**, yielding preflight exit 10. The full 44-unit suite therefore **was NOT independently reproduced**. Arena reported 44/44 in its own environment, separately attributed.
- **Conditional approval for owner Windows v1.1.3 `plan_only` ONLY**, after exact hash checks and fresh diagnostics-only extraction. `probe_only`, `canonical_baseline`, exploratory, holdout, freeze-rules remain **NOT AUTHORIZED/NOT RUN**. Owner must upload v1.1.3 plan-only log for independent review before any next gate.
- Full report: [P3_E1_E3_V113_INDEPENDENT_SOURCE_AUDIT.md](../phase-reports/P3_E1_E3_V113_INDEPENDENT_SOURCE_AUDIT.md).

No owner P3 acceptance, scope exception or PR merge is implied by this documentation addendum. The docs-only PR #11 remains DRAFT and awaits explicit owner scope/merge decision.

---

## P3 E1–E3 v1.1.3 — Owner Windows `plan_only` gate CLOSED PASS (2026-11-18)

The owner ran the exact hash-verified v1.1.3 ZIP/launcher against the unchanged detached acceptance worktree at `af2bfd226cc53b5c4665c160a6d8310abcce8b53` and supplied both PowerShell transcript and the saved `plan_only_output.txt` (UTF-16LE). Independent reviewer parsed both: identical JSON, `PLAN_ONLY_EXIT_CODE: 0`, `[PREFLIGHT OK]`, `[POSTFLIGHT OK]`, and Python `postflight_checked=true`, `postflight_passed=true`, empty `postflight_errors`. Plan `READY_FULL_COVERAGE`, 3 canonical/80 exploratory/160 holdout *planned only*, 6 fonts, zero duplicate IDs/exclusions, `plan_sha256=d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793` identical to v1.1.2. Python 3.12.9, Pillow 13.0.0, protected main DB unchanged (SHA `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`). No Tesseract execution by this mode.

**Evidence & decision:** [P3_E1_E3_V113_WINDOWS_PLAN_ONLY_EVIDENCE.md](../phase-reports/P3_E1_E3_V113_WINDOWS_PLAN_ONLY_EVIDENCE.md). Following previously documented independent v1.1.3 source audit, **only `probe_only` is now conditionally authorized** on owner Windows in a fresh isolated evidence folder, with hash checks and immutable baseline; **`probe_only` has not yet run**. No `canonical_baseline`, exploratory, holdout, frozen-rules writes, P3 PASS, PR merge or P4–P8 work. `GOLD-EX-11=FAIL/NOT PROVEN`.

This owner Windows gate does not retroactively convert Arena's Linux 44 tests into an independently reproduced 44/44, and does not constitute a P3 phase acceptance. Docs-only PR #11 still awaits scope authorization and owner review.

---

## P3 E1–E3 v1.1.3 — Owner Windows `probe_only` gate CLOSED PASS (2026-11-18)

The owner executed the hash-verified v1.1.3 launcher **only** in `probe_only` mode. Independent inspection of the owner PowerShell transcript, saved UTF-16LE output, manifest and metrics (four uploaded files) confirmed: identical JSON from transcript and saved output, embedded summary equals `metrics_summary.json` exactly; **`PROBE_ONLY_EXIT_CODE: 0`**, `probe_measurement_complete=true`, `experiment_completeness.complete=true`, `split_coverage_status="PROBE_ONLY_COMPLETE"`, 0 subprocess failures, 0 measurement failures, 0 timeouts, image parity PASS. Preflight and both internal/external postflight checks PASS; protected main DB unchanged and worktree clean. Run ID `20261118T120322_080547Z_probe_only_7d18ad0f`, pinned `af2bfd2`, plan SHA `d94ca0aab6c961a2087962e2c75f76177062e59fdf6c5b3125e9d0fbcd4ff793`.

Real Windows Tesseract `5.4.0.20240606` recognized `105` against synthetic source `1O5`. v1.1.3 correctly localized the target `word_1_20` by source render geometry (IoU 0.966667) and parsed **138** sibling LSTM groups (**123** multi, 0 malformed); `O` alternative remains **0.0%**, below 1.0% threshold, yielding `genuine_no_o_zero_alternative` **without inventing a correction**. This **closes v1.1.2's diagnostic-harness measurement blockers** but **does not prove OCR recognition fidelity or `GOLD-EX-11`**. Zero canonical/exploratory/holdout specimens executed, `scientific_performance={}` and `full_planned_coverage_achieved=false` are expected for a probe-only run.

**Evidence/report:** [P3_E1_E3_V113_WINDOWS_PROBE_ONLY_EVIDENCE.md](../phase-reports/P3_E1_E3_V113_WINDOWS_PROBE_ONLY_EVIDENCE.md). Sequential next permission is **only v1.1.3 `canonical_baseline` (3 synthetic cases)**, with pinned immutable files, default rules, clean detached worktree and fresh evidence-only run directory. `exploratory`, `holdout`, `freeze_rules_only`, P3 phase acceptance, PR merge, P4–P8 remain unauthorized. Retain full canonical records for independent evaluation even if detection fidelity remains poor. `GOLD-EX-11 = FAIL / NOT PROVEN`.

This addendum is proposed on **draft PR #11**, not yet merged into `main`; proposed docs-path exceptions require owner authorization before PR #11 merge.

---

## P3 E1–E3 v1.1.3 — Canonical launch interrupted by PowerShell stderr handling (2026-11-18)

Owner executed the separately gated v1.1.3 `canonical_baseline` wrapper, verified immutable ZIP/five members, prior `probe_only` PASS and pinned preflight; Python/Tesseract diagnostic was launched with default rules. **Owner console ended on `NativeCommandError`** after `DeprecationWarning` from Python `e1_e3_windows_diagnostic.py:2665` (`Image.Image.getdata` in Pillow 13). Outer Windows PowerShell 5.1 script has `$ErrorActionPreference='Stop'` together with `2>&1 | Tee-Object`, so stderr can terminate the parent pipeline before `$LASTEXITCODE` capture. Parent `finally` checked protected main database, worktree and HEAD: **`PROTECTED BASELINE POSTFLIGHT: PASS`**.

**Unknown:** whether original Python produced complete `manifest.json`, `metrics_summary.json` and 3 records before the outer caller terminated. This is not a proven OCR failure, and definitely not a baseline PASS. **No automatic retry.** Read existing `run_*_canonical_baseline_*` evidence first and review it independently, then decide if a safe wrapper change is needed. See [incident and read-only inspection procedure](../phase-reports/P3_E1_E3_V113_CANONICAL_WRAPPER_INCIDENT.md).

**Current gate:** `canonical_baseline = ATTEMPTED / NOT VERIFIED`; `plan_only = PASS`; `probe_only = PASS`; `P3 = IN_REVIEW`; `GOLD-EX-11 = FAIL / NOT PROVEN`. Do not run exploratory, holdout, freeze, merge, or advance to P4–P8.

---

## P3 E1–E3 v1.1.3 — Read-only canonical evidence discovered (2026-11-18)

After the previously recorded outer PowerShell 5.1 `NativeCommandError`, owner ran **read-only evidence inspection only** (no diagnostic execution). Git checkout still clean at pinned `af2bfd2`, protected DB SHA unchanged `6728a3d4...`. It located **one** canonical run folder `run_20261118T121739_753329Z_canonical_baseline_0e5a8b3d` containing `manifest.json` (17,456 bytes), `metrics_summary.json` (54,330 bytes), `records.jsonl` (46,463 bytes / 3 nonblank lines) and `records.csv` (1,625 bytes). Inspector reports **`SUMMARY_EXIT_CODE=0`, `COMPLETE=True`, `COVERAGE_STATUS=COMPLETE`, `POSTFLIGHT_PASSED=True`, `PROTECTED_DB_UNCHANGED=True`**; original outer wrapper log contains only runtime and preflight and is not adequate on its own to establish results.

**Status:** `canonical_baseline = OWNER-REPORTED COMPLETE / FULL ARTIFACT AUDIT PENDING`. Distinguish this from both `canonical_baseline FAIL` and from acceptance-specific `GOLD-EX-11 PASS`. The latter remains `FAIL / NOT PROVEN`. Upload **existing** 4 canonical files and original truncated log for independent inspection; no reruns, tuning or new diagnostic mode. See [canonical incident and evidence update](../phase-reports/P3_E1_E3_V113_CANONICAL_WRAPPER_INCIDENT.md). P3 stays `IN_REVIEW`; docs-only PR #11 remains draft/unmerged.

---

## P3 E1–E3 v1.1.3 — Canonical original-artifact forensic audit CLOSED (2026-11-18)

Owner supplied original `manifest.json`, `metrics_summary.json`, `records.jsonl`, `records.csv` and the 1,096-byte PowerShell log for run `20261118T121739_753329Z_canonical_baseline_0e5a8b3d`. Independent reviewer decoded and parsed them, computed per-file SHA256 (recorded in [detailed report](../phase-reports/P3_E1_E3_V113_CANONICAL_RESULTS_INDEPENDENT_AUDIT.md)), verified cross-file run identity and all three CSV/JSONL record identities and D1–D6 outcomes, and confirmed **3/3 completed, inner exit 0, `COMPLETE`, 3/3 image/TSV parity PASS, pre/postflight PASS, protected DB unchanged**. Outer PowerShell 5.1 wrapper output was truncated by `Image.getdata()` deprecation stderr handling; **this is an external log-capture failure, not a failed inner specimen execution**. Historic original evidence remains intact; no rerun needed.

**Critical result:** On the one corrupted positive `CANON_GOLD_EX_11`, original `1O5` (letter O) was recognized and parsed as numeric `105`. `baseline_looks_corrupted=false` and **all supported ambiguity-specific detectors failed to identify O/0** (specific TP=0/FN=1). D4 `generic_disagreement_only` and D6 `fail_closed_non_specific` routed the positive operationally from non-confusable `105°`, **but also routed the clean `13.4` negative** due `134` crop disagreement (one operational false positive); D5 OEM0 unavailable. Thus D4/D6 operational sensitivity on only one positive is NOT sufficient to prove source-fidelity or application `GOLD-EX-11` gate, while D1/D2/D3 negative outcomes must not be presented as true negatives for the corrupted specimen. Do not conflate detector outcome-state labels with ground-truth confusion counts. `GOLD-EX-11 = FAIL / NOT PROVEN` remains the P3 blocker.

**Gate:** `plan_only=PASS`, `probe_only=PASS`, `canonical_baseline execution=COMPLETE` but `canonical scientific safety=NOT PROVEN`. **Hold exploratory, holdout, freeze_rules_only and P3 acceptance/merge.** Next task is a bounded Arena **design/review** for source-aware confirmation and robust false-clean prevention, not silent threshold tuning or altering the synthetic fixture. Owner must separately approve any source change or fresh experiment. Docs-only PR #11 remains DRAFT and its file-scope permission is pending.

---

## P3 G11 — False-clean remediation design request (2026-11-18)

**DESIGN REQUESTED — NOT DELIVERED / NOT IMPLEMENTED.** After the independent v1.1.3 canonical 3/3 audit demonstrated `CANON_GOLD_EX_11`'s `1O5`→`105` false-clean miss, a scoped, **design-only** Arena handoff was created: [P3_G11_FALSE_CLEAN_REMEDIATION_DESIGN_REQUEST.md](../phase-reports/P3_G11_FALSE_CLEAN_REMEDIATION_DESIGN_REQUEST.md). It explicitly requires auditing existing Stage 2/3 `GET /file`, `GET /text`, `source_image_compared`, `confirmed_value`, `G11-D1..D6`, and R21 source/verification controls **before proposing** any new code; avoid duplicating implemented protections. Keep G1 recognition accuracy separate from G3/G4 human-verification safety, and do not silently change the literal `GOLD-EX-11` contract. Design includes positive and clean-control acceptance matrix, minimal patch map, separate PowerShell 5.1 stderr/exit logging plan and owner decisions.

**Awaiting Arena's design response and independent owner review.** This is not an authorization to edit source, change acceptance rules, touch protected database or rerun canonical/exploratory/holdout/freeze. `GOLD-EX-11=FAIL/NOT PROVEN`, P3 `IN_REVIEW`, P4–P8 `TODO`. Proposed documentation additions are in unmerged Draft PR #11, subject to owner docs-file-scope permission.

---

## P3 G11 — Independent design review: REVISIONS REQUIRED (2026-11-18)

Arena posted its complete **design-only** P3-G11 response and [summary comment on PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6979138948). Independent reviewer checked claims against pinned `af2bfd226cc53b5c4665c160a6d8310abcce8b53` source code and accepted real Windows v1.1.3 canonical evidence. **Review verdict: direction Option A sensible, but DESIGN v2 REQUIRED / NO IMPLEMENTATION APPROVAL.** Full review and corrections: [P3_G11_ARENA_DESIGN_INDEPENDENT_REVIEW_V1.md](../phase-reports/P3_G11_ARENA_DESIGN_INDEPENDENT_REVIEW_V1.md).

**Blocking corrections:** (1) Explicit owner policy decision needed because literal `GOLD-EX-11` strict G1 acceptance is unmet by recommended source-review Option A, whereas R20 separates G1 as measured limitation; do not silently change the existing release blocker. (2) New real-engine `W2/FC-3` acceptance must prove real HTTP OCR produced a **mappable extracted value**, otherwise zero Observations could be a vacuous PASS. (3) Source-retrieval flags are doctor attestation, **not cryptographic proof of visually comparing pixels**; document incorrect-source-attestation residual. (4) Defer nonessential schema/cleanup changes; do not treat confusable-digit presence as OCR error detection. (5) PowerShell 5.1 wrapper design must preserve original hash/pre-postflight guards, exit status, stderr, existing logs, and label any post-exit `stdout+stderr` concatenation as **nonchronological**. (6) Separate historical test claims from tests actually run in the design session.

**Next allowed task:** Arena **design revision only** and then owner/reviewer decision. No app code edit, new diagnostic, exploratory/holdout/freeze, docs PR merge, P3 acceptance or P4/P5. `GOLD-EX-11=FAIL/NOT PROVEN` and `P3=IN_REVIEW`. Draft PR #11 docs file-scope exception remains pending explicit owner approval.

---

## P3 G11 — Independent Design v2 Review: TARGETED CORRIGENDUM REQUIRED (2026-11-18)

Arena submitted **Design v2** and posted its [PR #10 design-summary comment](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6979426944), with no executable changes or tests in that design session. Independent reviewer re-read pinned implementation `af2bfd226cc53b5c4665c160a6d8310abcce8b53` and original Windows canonical evidence. **v2 addresses the broad v1 objections, but four source-grounded corrections remain before approval:** (1) clean `Hemoglobin 13.4 g/dL` is **unmapped** by `MAPPING_TABLE`, so the M2 expectation of an Observation is wrong even after a verified document; (2) `GET /file` hash validation alone does **not** invalidate a **prior successful `document.file_read` audit anchor** if bytes are subsequently corrupted: new `ERROR` events are not checked by `_doctor_accessed_source_file`; (3) false source attestation cannot generate `doctor_verified` Observation after value-only approval; complete verified name/date/unit siblings must also be present; (4) wrong `document.content_type` property, detector-family labels and attribution of the outer PS5.1 wrapper warning must be corrected. Require explicit regression coverage of M2/M5/M6 and test the prior-read/tamper scenario.

**Full independent v2 review:** [P3_G11_ARENA_DESIGN_INDEPENDENT_REVIEW_V2.md](../phase-reports/P3_G11_ARENA_DESIGN_INDEPENDENT_REVIEW_V2.md). **Next:** Arena focused **Design v2.1 corrigendum only**, then owner sign-off on P1 vs P2 GOLD policy, core patch A1/W2, optional docs/PS scope. This is not an implementation authorization or contract amendment. PR #10/#11 remain drafts, `GOLD-EX-11=FAIL/NOT PROVEN`, P3 `IN_REVIEW`; no reruns, exploratory/holdout, frozen rules, merging or phase advancement.

---

## P3 G11 — Design v2.1 Independent Review: OWNER DECISIONS OPEN (2026-11-18)

Arena delivered focused **Design v2.1 Corrigendum** and [posted PR #10 summary](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6979769036). Independent reviewer compared its C1–C5 corrections against pinned `af2bfd226cc53b5c4665c160a6d8310abcce8b53` code. **All substantive v2 objections are resolved at the DESIGN level.** [Detailed review and safeguards](../phase-reports/P3_G11_ARENA_DESIGN_INDEPENDENT_REVIEW_V21.md).

**Decision:** `DESIGN v2.1 REVIEWED / ACCEPTABLE AS CONDITIONAL DESIGN BASIS`, **NOT implementation authorization**. Recommend `A1-Anchored` over `A1-Narrow` if source-file integrity is intended to cover stale success anchors; require verified `settings.upload_dir` propagation through `record_decision`/verification/promotion, isolated-session SQLite audit durability (no unrelated commit), correct per-doctor/per-document `(created_at,rowid)` ordering with recovery by a new intact successful read, and non-vacuous W2 + M2/M5/M6 testing. These are explicit code-review acceptance conditions, not claims of tests run. Avoid conflating a hash snapshot with actual doctor source comprehension or immutable lifetime integrity.

**Owner decisions OPEN**: `OD-1 P1 vs P2` (current P1 strict literal GOLD blocker remains in force until explicitly amended), `OD-2` minimal core code/tests scope, `OD-2a` anchored vs narrow, `OD-5` exact filescope exception and `OD-6` independent PS5.1 wrapper; optional schema/cleanup `OD-3/OD-4` recommended DEFER. Old PR #10 head `18a53b2` does not contain pinned R21/Stage3 code; any owner-approved implementation must be on an exact reviewed branch based on `af2bfd2`, not obsolete PR #10 head. No P3 acceptance/merge, OCR rerun, exploratory/holdout/freeze/P4/P5. `GOLD-EX-11=FAIL/NOT PROVEN`, `P3=IN_REVIEW`, docs-only PR #11 DRAFT and pending owner docs exception.

---

## P3 G11 — Owner bounded implementation authorization (2026-11-18)

**Owner explicitly agreed in ChatGPT to the immediately preceding proposed bounded plan**, recorded by ChatGPT on their behalf. [Exact authorization record](../phase-reports/P3_G11_OWNER_BOUNDED_IMPLEMENTATION_AUTHORIZATION_20261118.md) includes owner-policy, scope and gate limitations. The corresponding PR conversation comment is a ChatGPT transcription of the owner's instruction, **not an owner-authored GitHub ratification or P3 acceptance**.

- **Authorized:** `OD-2` minimal **A1-Anchored + non-vacuous W2/FC-3** branch implementation with offline RED→GREEN tests and limited exact file set, `OD-2a=A1-Anchored`, `OD-5` narrow exception for those six implementation/test files plus the owner authorization report and this tracker update. Owner **retains P1** literal `GOLD-EX-11` release blocker (`OD-1=P1` for now; **P2 DEFERRED**). `OD-3/OD-4` optional API fields/heuristics/cleanup deferred. `OD-6` PS5.1 wrapper is a **separate deferred task**.
- **New branch created from exactly pinned `af2bfd226cc53b5c4665c160a6d8310abcce8b53`: `feat/p3-g11-a1-anchored-w2`.** Do not reuse obsolete PR #10 code head (`18a53b2`), dirty Arena workspace or owner's clean protected Windows checkout.
- **Allowed paths ONLY:** `backend/app/api/v1/documents/read.py`, `backend/app/api/v1/documents/verify.py`, `backend/app/services/documents/verification.py`, `scripts/python/windows_ocr_acceptance.py`, `backend/tests/p3/test_p3_stage3_verification_hardening.py`, `backend/tests/p3/test_windows_ocr_acceptance.py`. If more are needed, STOP and seek an explicit revised owner exception; no automatic schema/migration/fixtures updates.
- **Implementation safety requirements:** assert configured `settings.upload_dir`, integrity of `GET /file` read-buffer and live source at `verify` / mapping boundary; isolate durable ERROR audit writes from SQLite request transaction; stale-anchor S1/S2 invalidation and recovery, same-doctor/doc authorization; R21 reject still available; W2 cannot PASS on missing/unmappable HTTP OCR. `Hemoglobin 13.4 g/dL` remains UNMAPPED with zero Observation; `Glucose 104` mapped positive; false doctor attestations are a known residual.
- **Explicitly NOT authorized:** real Windows OCR/diagnostic execution, any canonical/exploratory/holdout/frozen-rules run, changing `gate_ocr_corruption`, P2 contract amendment, PS wrapper writing, making P3 PASS, merging PR #10/#11/new PR, editing `main`, touching protected DB, or starting P4–P8. Draft code PR review only after offline RED→GREEN evidence.
- **Documentation caveat:** this small authorization record/tracker exception does **not** approve the broader prior docs-only PR #11 diff for merge; its remaining docs file-scope permission is independent and still requires owner review.

**Resulting phase status:** `P3=IN_REVIEW`; `GOLD-EX-11=FAIL/NOT PROVEN`; **implementation/testing authorized in a new, bounded branch only**. No implementation completion or test result is claimed here.

---

## P3 G11 — Arena shallow workspace restoration and existing-branch workflow correction (2026-11-18)

Following owner concern about unnecessary additional branches, Arena completed a **strictly read-only** audit of the **existing active session** `arena/752cca1f-ai-doctor-followup-agent` (no edits, commits, fetches, resets, pushes, PRs, or diagnostics). Sandbox is a shallow checkout whose local HEAD is `5d30960c045de5eb6527de6aab64669d34fafb7a`, with `39` tracked modified and `4` untracked restored files (Arena UI `+7101/-290`). Arena reports all **204** local blobs match GitHub-pinned `af2bfd226cc53b5c4665c160a6d8310abcce8b53` exactly, with **zero new work beyond the six remote commits** already committed and pushed. Independent GitHub compare confirms strictly linear `5d30960 -> af2bfd2` (ahead 6/behind 0) and original PR #10 code HEAD `18a53b2 -> af2bfd2` (ahead 14/behind 0). No source changes were lost.

**Owner-preferred workflow correction:** [authorization addendum](../phase-reports/P3_G11_OWNER_BOUNDED_IMPLEMENTATION_AUTHORIZATION_20261118.md#f-owner-workflow-correction--continue-in-the-existing-arena-session-2026-11-18) **supersedes ONLY the old “implement on new feat branch/open third PR” instruction.** Keep active Arena session/branch `arena/752cca1f-ai-doctor-followup-agent`, first **revalidate all path/blob parity against fetched target**, then permit guarded `git reset --mixed FETCH_HEAD` solely to align the local shallow HEAD/index (NEVER `reset --hard`, clean, stash, rebase or force-push). The local worktree must remain byte-identical; STOP for any mismatch. Continue owner-authorized **A1-Anchored + W2** RED→GREEN in same branch, only the six approved implementation/test paths, no new PR. The inadvertently created extra `feat/p3-g11-a1-anchored-w2` is identical to `af2bfd2`, **unused** and left untouched pending owner decision. Existing PR #10 may be updated by strictly guarded **fast-forward of its head ref only after independently reviewed code** and separate owner approval; **NO main merge**. PR #11 stays docs-only Draft.

**ALL other guardrails continue:** P1 literal GOLD remains active, P2 deferred, `GOLD-EX-11=FAIL/NOT PROVEN`, P3 `IN_REVIEW`. No owner Windows diagnostic, canonical/exploratory/holdout/freeze, PS wrapper, P3 acceptance, code beyond allowlist, or later phases.

---

## P3-G11 — Owner-delegated seventh-file / SQLite audit unblock (2026-11-18)

The owner explicitly delegated a safe bounded decision after Arena STOPPED on two pre-implementation blockers. **[Updated authorization / Section G](../phase-reports/P3_G11_OWNER_BOUNDED_IMPLEMENTATION_AUTHORIZATION_20261118.md)** records the owner's chat instruction, not a personally signed GitHub owner comment.

**Arena-reported actual clean baseline:** same active Arena branch `arena/752cca1f-ai-doctor-followup-agent` at `af2bfd2` (204/204 unchanged, clean); tests `789 passed` overall, `395` P3, targeted `94 passed`, Ruff/OpenAPI PASS. **Zero Step 2 source edits** when Arena stopped. **Blocker A**: handoff count-integrity test makes additional tests require editing `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`. **Decision OD-5b APPROVED:** authorize this **one seventh file only** for updated measured test totals/table and narrowly labeled A1/W2 status; preserve handoff-count integrity test and do not assert unrun GREEN. No eighth file.

**Blocker B**: empirically observed SQLite `database is locked` because `resolve_session` flushes the login-session update before `GET /file`, so a parallel `Session(bind=db.get_bind())` cannot commit an error event. **Decision OD-2b:** approve a **conditional, test-first route-level deferred `AuditOutcome.ERROR` proof** only in the existing `read.py` and approved P3 test paths. MUST verify actual FastAPI yield dependency cleanup **after request-db rollback/close**, no collateral ORM commit, persistent safe idempotent error audit and unchanged neutral 404 in file-backed and supported in-memory SQLite; direct Python-call semantics verified separately. If proof fails, STOP, no alternative auth/session/audit refactor or implicit eighth file allowed. Do NOT repeat the known failing simultaneous second-session commit.

**Next:** Arena in SAME session/branch performs this proof, then implements owner-authorized A1-Anchored + non-vacuous W2 with RED→GREEN and final count-doc sync, and stops for review. PR #10 remains original OPEN/DRAFT with head unchanged, PR #11 draft docs-only, no new branch/PR, no P3/main merge. **P1/GOLD-EX-11 FAIL/NOT PROVEN, P3 IN_REVIEW**; no owner Windows OCR or holdout/freeze/next phases.

---

## P3-G11 — W2-R1/R2 implementation and source-review follow-up (2026-11-18)

Arena continued in the **same existing session/branch** `arena/752cca1f-ai-doctor-followup-agent` and pushed commit `358f31df3b9d373566caa695b0cd930d138223da` (parent `3aec99b`). GitHub compare independently verifies **one linear commit changing only 3 of the seven allowed paths**: `scripts/python/windows_ocr_acceptance.py`, `backend/tests/p3/test_windows_ocr_acceptance.py`, and `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`. Cumulative diff from `af2bfd2` still exactly seven approved paths. Original PR #10 head still `18a53b2`, Draft/unmerged. Arena-reported Linux Python 3.11.2 regression results: **829 backend passed; 435 P3 passed; W2 103 passed; Ruff/OpenAPI passed**. Python 3.12 and real owner Windows Tesseract **NOT RUN**.

**W2-R2:** checked the real `1O5` fixture source canonical LF SHA-256 `0f8cae895dff04f3017b32d3e2d9b5e50e75c60f2498cb188991c749732c2492` and size 200; supports detection of tamper that retains the token. **W2-R1:** under actual independent GOLD PASS and W2 preserving/refusing `1O5`, an inapplicable false-clean test is labeled non-PASS `DERIVED`, while missing/unmappable OCR remains blocking.

**Independent reviewer source-level finding W2-R3:** `assess_w2`'s early `DERIVED` return does not check W2 sibling-field presence, `all_facts_tesseract`, `all_facts_require_source`, `all_facts_pending` or non-value fact count, so a structurally incomplete/non-Tesseract W2 record may be classified nonblocking when GOLD independently passes. This is a **logic/coverage risk**, not observed runtime evidence. Requested one narrowly bounded RED→GREEN case and minimal predicate hardening via [review PR #10 comment](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6984150816), in the SAME branch with the SAME allowed paths; no design loop or new PR. Keep intentional unparseable `1O5` mapping ineligible and avoid vacuous `PASS`.

**Gate:** pending W2-R3 patch and review, then separately approved supported Python 3.12 / Windows real-OCR evidence on an isolated detached acceptance checkout. **P1 strict literal GOLD remains FAIL / NOT PROVEN; P3 IN_REVIEW.** No protected DB change, canonical rerun, exploratory/holdout/freeze, new branch/PR, main merge or PR #10 head update authorized by this review.

---

## P3-G11 — W2-R3 source review accepted; Windows read-only preflight next (2026-11-18)

Arena pushed the focused W2-R3 correction on the existing P3 session branch at `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821` (parent `358f31d`). Authenticated GitHub compare confirms one commit / **3 authorized changed paths**; cumulative `af2bfd2..6e6fcdf` is 3 linear commits / **7 approved paths only**; no PR #10 head update or new implementation PR. [Detailed independent review and preflight boundary](../phase-reports/P3_G11_W2_R3_INDEPENDENT_REVIEW_AND_WINDOWS_PREFLIGHT.md).

**W2-R3 code-level review ACCEPTED**: a `DERIVED` result for independently GOLD-PASS preserved/refused `1O5` now additionally enforces all extracted facts pending, Tesseract provenance, source review requirement, non-value siblings, and `report_date`/`test_name`/`unit` presence. Violations return blocking `FAIL` or `NOT RUN`, never W2 PASS. The previous exact fixture SHA/size guard is preserved. `gate_ocr_corruption` literal requirement unchanged. Arena-reported Linux Python 3.11.2 checks: **837 backend passed**, **443 P3 passed**, **111 in W2 test file**, Ruff/format/OpenAPI PASS; these checks were **not independently rerun** and are on an **unsupported** Python version compared to `pyproject.toml` 3.12.

**Next step:** **read-only owner Windows preflight ONLY** (Python 3.12, Node/Tesseract, remote exact SHA, main HEAD/worktrees, protected DB read-only checksum) before authorizing fresh detached worktree/setup/real OCR. Existing Windows handoff has stale stage labels and explanatory prose, not a reason to change the acceptance gate. **No Windows diagnostic/test has been authorized or run by reviewer.** `GOLD-EX-11=FAIL/NOT PROVEN`, P1 literal release blocker retained, P3 `IN_REVIEW`. PR #10 remains DRAFT at old head; PR #11 docs-only DRAFT. No main merge, FF, P2 policy change or P4/P5.

---

## P3-G11 — Owner real Windows Tesseract: GOLD-EX-11 strict FAIL; W1/W2 PASS (2026-11-18)

Owner ran the **actual** Windows 11 / Python 3.12.9 / Tesseract 5.4.0.20240606 OCR acceptance probe on clean isolated detached P3 implementation SHA `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`; uploaded the JSON and exact stdout/stderr/runner. Reviewer inspected these artifacts. **Actual exit code `2`; 27 PASS, 1 FAIL, 0 NOT RUN, 1 DERIVED**; repo SHA bound in JSON, checksum documented. [Detailed real-engine evidence review](../phase-reports/P3_G11_OWNER_WINDOWS_REAL_OCR_6E6FCDF_EVIDENCE_REVIEW.md) and PR #10 evidence thread.

**One strict release blocker:** `GOLD-EX-11 OCR-produced 1O5=FAIL / NOT PROVEN`. Real Tesseract transformed original visual **`1O5`** (letter O) to plausible numeric **`105`** before the parser. Text parser stored clean `105`; no `unparseable_value` flag or blocking flag issue was raised by `collect_flag_issues`. The app **did not** make the original text substitution. Do not weaken the literal P1 condition, falsify rendering/engine output, change fixture or substitute W2 results.

**Genuine positive evidence:** All W1 real-engine R21 rejection and positive source-confirmation gates succeeded, including refusal of unreviewed verify, one explicitly doctor-verified `104 mg/dL` Observation from clean source, and terminal rejection with no Observation. All **five W2 FC-3** real-engine gates succeeded on the false-clean `105` counterexample, showing 0 pre-verify Observations, two 400 unreviewed refusals, doctor rejection and immutable follow-up, and audit safety. These are important compensating controls, **not evidence that `GOLD-EX-11` passed**. `GOLD-EX-07/08` was DERIVED, not independent PASS.

**Status decision:** `P3 IN_REVIEW`; strict `GOLD-EX-11 FAIL / NOT PROVEN`; **NO P3 acceptance or PR #10 FF/main merge**. Proceed with read-only source/image-aware RCA design review in SAME Arena session; no new branches, PRs, real-OCR reruns, P2 waiver, holdout or unauthorized code changes. Future implementation/design needs separate bounded owner authorization. Previously owner Windows `test_all.ps1` 12 PASS / 0 FAIL / 1 optional Playwright SKIP, with 4 backend test skips noted; this quality PASS does not override the actual OCR FAIL.

---

## P3-GOLD-P2 — Owner selects bounded alternative acceptance policy path (2026-11-18)

**Decision source:** In the project chat after reviewing the real Windows OCR `GOLD-EX-11` failure, the owner expressly replied **“طب يلا اعتمد”** to the proposal to select **P2 policy** (application-layer *conditional* acceptance) instead of iterating on unrelated OCR warning patches. This is an assistant-transcribed chat instruction, **not an owner-authored GitHub ratification or final P3 PASS**.

**Selected direction, NOT YET EFFECTIVE:** Adopt `P2 POLICY PATH = OWNER SELECTED / FORMAL CONTRACT AMENDMENT AND RATIFICATION PENDING`. See [complete decision memo with bounded conditions and owner-signature checklist](../phase-reports/P3_GOLD_EX11_P2_OWNER_POLICY_DECISION_20261118.md). This **supersedes the prior P2-DEFERRED decision as an owner-selected *future amendment***, not the currently binding P1 strict technical acceptance contract; do not silently rewrite any historical measurement.

The definitive owner Windows evidence at implementation SHA `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`: **27 PASS, 1 FAIL, 0 NOT RUN, 1 DERIVED, exit 2** on Tesseract 5.4 / Python 3.12.9. The synthetic visual source `1O5` was emitted as numeric `105` by the OCR engine and parsed `clean`; `GOLD-EX-11 = FAIL / NOT PROVEN`. Actual W1 rejection/source confirmation and W2 FC-3 nonautonomous/doctor-gated controls all PASS but **do not detect the original OCR substitution**. Uploaded JSON SHA-256 `9ac465722f011d538fd8045e393328fa4a0e2b1f10afd1b8e3488aff961f08cb`, 15,283 bytes.

**Scope and next gates:** preserve original GOLD fixture/strict executable verdict, immutable OCR evidence, SHA-anchored source, R21, W1/W2 and patient-free synthetic scope. P2 **would** allow a formal owner-approved *known technical deviation* for the academic application boundary while documenting residual doctor false-attestation risk; **it cannot be treated as blanket clinical safety or a successful OCR detection test**. The owner must personally ratify the exact policy amendment in PR #10, separately authorize and review coherent contract/handoff changes, align the old PR #10 candidate via separately approved FF-only operation after verified ancestry, obtain authoritative CI on that head, and then make a distinct final P3 phase approval and merge decision. Until then `P3=IN_REVIEW`, existing P1 blocker active, `GOLD-EX-11=FAIL / NOT PROVEN`, PR #10/#11 both DRAFT, no merge/P4/P5/holdout.

**Clarification:** P2 in this heading means **alternative GOLD acceptance policy option**, not the already merged **Phase P2 (patient domain)**.

### P2 policy process approval — GitHub owner comment verified (2026-11-18)

The owner confirmed in chat that they posted the agreed direction approval on [PR #10 issue comment `6986661566`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6986661566), and the GitHub issue-comment API independently returned the **exact requested text** displayed under `Muhammed-Fathi`. The comment explicitly authorizes **formal policy-amendment review only**, acknowledges that `GOLD-EX-11` technical `FAIL / NOT PROVEN` and the doctor false-attestation risk remain, and **does not** authorize a P3 PASS, a code/test/fixture change, PR #10 head fast-forward, or merge. The [P2 decision checklist](../phase-reports/P3_GOLD_EX11_P2_OWNER_POLICY_DECISION_20261118.md) now separately records this completed approval-of-process and the **still pending final owner ratification** of an exact revised acceptance contract.

A read-only GitHub comparison verified the frozen implementation `6e6fcdf...` is **17 commits ahead / zero behind** original PR #10 head `18a53b2...`, so a strictly guarded fast-forward of the PR head is technically plausible **but is not authorized by the comment**. PR #10 remains original DRAFT old head; PR #11 remains DRAFT docs. No PR/phase state changed; original P1 strict release blocker remains effective until separately approved contract/handoff amendment. P3 stays `IN_REVIEW`.


### P2 policy five-document drafting scope — owner-authorized and implemented as proposed text (2026-11-18)

**Scope authorization VERIFIED:** [PR #10 comment `6986820279`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6986820279) was authored under `Muhammed-Fathi`, approving exactly the five docs-only paths listed in [scope request `6986774509`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6986774509). That approval **does not authorize** changing executable GOLD, synthetic fixtures, production code, PR #10 head or status, merge, phase PASS, or next-phase activities.

**Amendment drafted on EXISTING docs-only Draft PR #11 ONLY**; all new policy wording is **PROPOSED / NOT EFFECTIVE**:

1. `docs/evaluation/GOLD_FIXTURES.md` — proposed P2 policy annex, preserving historical Case C declarations and actual `GOLD-EX-11` failure.
2. `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` — proposed conditional-acceptance annex; currently effective strict §9 remains unchanged and `exit 2` remains nonzero.
3. `docs/phase-reports/PHASE_3_REPORT.md` — appended real owner Windows OCR results, W1/W2 compensating guarantees and doctor false-attestation limitation.
4. `docs/roadmap/PHASE_PROGRESS.md` — this owner-authorization evidence and prospective/final policy gate separation.
5. `docs/phase-reports/P3_GOLD_EX11_P2_OWNER_POLICY_DECISION_20261118.md` — checklist records docs scope authorization while keeping the final policy and P3 acceptance approval pending.

**Immutable evidence:** implementation `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`, actual Windows OCR 27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED, exit 2; `GOLD-EX-11=FAIL / NOT PROVEN` because source `1O5` became `105`. W1 and W2 controls PASS, but do not prevent a doctor falsely attesting a misread source. Source JSON 15,283 bytes SHA-256 `9ac465722f011d538fd8045e393328fa4a0e2b1f10afd1b8e3488aff961f08cb`. Synthetic academic use only; no clinical claims.

**Remaining gates (UNFULFILLED):** independent review of the exact five-file docs diff; owner **final**, explicit GitHub policy ratification; owner decision to authorize a verified **fast-forward-only** update of old Draft PR #10 head `18a53b2...` to `6e6fcdf...` (or stop if branch/ref changed); successful authoritative CI on the final PR #10 head; final source/Windows/evidence and test-skip inspection; separate owner P3 acceptance/merge decision. No implicit authorization by this docs amendment. **Until all required gates are satisfied, existing strict P1 blocks final P3 acceptance, `P3=IN_REVIEW`, `GOLD-EX-11=FAIL / NOT PROVEN`**; PR #10/#11 remain DRAFT/unmerged. P4/P5 not started.

*Educational synthetic project — NOT FOR CLINICAL USE.*


---

## P3-GOLD-P2 final documentation reconciliation checkpoint (2026-11-19)

**Owner authority:** [owner P2 policy re-ratification #6991001412](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6991001412); five-file scope [owner docs-only reconciliation authorization #6993612930](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6993612930). Original updated docs SHA `95797e7da5a5bec6fdc1deadbdc765e3ee5ca814` was merged by owner via PR #11 to implementation commit `4ec7d469d76ad89ffb7e27fbe18864bdc216ba46`. The existing Draft PR #10 was separately guarded-fast-forwarded to `4ec7d469d76ad89ffb7e27fbe18864bdc216ba46`, and both push/PR CI runs there succeeded. This newer five-document reconciliation still requires independent review and fresh CI on its exact resulting head.

**Scientific truth:** Real Windows Tesseract misread synthetic visual `1O5` as numeric `105`; `GOLD-EX-11=FAIL / NOT PROVEN` (27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED; OCR exit 2; evidence SHA-256 `9ac465722f011d538fd8045e393328fa4a0e2b1f10afd1b8e3488aff961f08cb` (15,283 bytes)). The supported Windows `test_all.ps1` reported **12 PASS / 0 FAIL / 1 optional Playwright SKIP**, with four backend pytest skips requiring explicit reasons review. All 13 W1 and five W2/FC-3 real-engine rows were reported PASS, demonstrating bounded human approval and nonautonomy controls but not correct source O/zero recognition. Doctor false-attestation risk remains.

**Unfinished gates:** independent reconciliation diff review; new-head authoritative CI; Windows skip/supplementary evidence review; separate owner-authored final P3 conditional application acceptance and owner-controlled `main` merge. Until then the owner-ratified P2 policy is **not operationally effective**, `P3=IN_REVIEW`, and the technical GOLD FAIL persists. No P4/P5, real patient data, autonomous interpretation or clinical use. **NOT FOR CLINICAL USE.**


---

## P3 owner-approved conditional educational closure — 2026-11-19

**Current owner decision:** **CONDITIONALLY ACCEPTED — SYNTHETIC EDUCATIONAL ONLY**, after [PR #10 merge](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10) (`006ecf417f023428ab90c35cbb0638995c246774`) and [post-merge CI SUCCESS](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44430671695). The [final closure and acceptance evidence record](../phase-reports/P3_FINAL_CONDITIONAL_ACCEPTANCE_20261119.md) is authoritative for this status. All earlier open-PR/in-review progress notes above are retained as **historical** states and are superseded as current status.

**Scientific exception stays open:** Real Tesseract `1O5`→`105`, `GOLD-EX-11=FAIL / NOT PROVEN`, OCR exit 2; original 27 PASS / 1 FAIL / 0 NOT RUN / 1 DERIVED. This decision accepts a bounded synthetic academic application despite that disclosed deviation; it is **not** P1 strict technical PASS, source-glyph validation, clinical use, or permission to start P4/P5. Playwright E2E remains owner-deferred to P6.


## P4 owner decision — R1-A and R4 scoped authorization (2026-11-19)

Following owner-merged [PR #23](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/23) at `main@d100df80ebaf8a0dd8b98128ea936e495fbb320a`, the owner stated in chat: **"تم دمج PR #23، وموافق على R1-A وR4"**.

- **R1-A = OWNER-SELECTED:** defer P4-3 `review_item` / `evidence_link` durable storage, audit, and review API until the P5-owned real `workflow_run` identity exists; leave `review_item.workflow_run_id NOT NULL FK` unchanged, no fake runs or phase crossover. This prevents claiming P4 full acceptance at present.
- **R4 = OWNER-AUTHORIZED FOR OFFLINE TESTING ONLY:** synthetic GOLD-A/B/C/D expected fixtures and migrated SQLite candidate-rule tests, no runtime gate, API, agent, source-image/OCR validation, treatment, notifications, or live policy.
- **R2 & R3 remain OPEN:** trusted full-run evidence/VI tool interface and numerical demo-policy `OQ-R01` require independent future owner review; green test results cannot silently ratify them.
- **Status:** P4 **IN_REVIEW**, P5 NOT STARTED, P3 real `GOLD-EX-11 = FAIL / NOT PROVEN` stays disclosed. NOT FOR CLINICAL USE.


## P4 R2-A / C-35A / C-37A owner-scoped implementation approval (2026-11-19)

After owner-merged PR #25 at `main@71bf8bab7bcd55b570e7a13a46df6d2efad905f9`, the owner wrote **"تم دمج PR #25، وموافق على R2-A وC-35A وC-37A"** in chat.

- **R2-A:** approved only a subsequent P4 **internal, read-only, scoped synthetic evidence inspection**, not any full run VI gate or source-byte attestation. It must unconditionally refuse/withhold live rule clearance.
- **C-35A:** approved separate bounded server-side history acquisition and pure explicit current-plus-history comparison for P4 component testing; no silent normative tool contract change or P5 invocation.
- **C-37A:** approved the future **server-produced run-bound evidence** architecture, **not** creation of an evaluable run token before P5. Current internal P4 result is **non-evaluable**, with an explicit unavailable gate.
- **Previously approved R1-A** remains binding: no P4 review-item/evidence-link persistence before legitimate P5 workflow_run, and no P5 early code. R3/OQ-R01 demo numeric policy and R21 terminal-source recovery selection remain **OPEN**. P4 **IN_REVIEW**, P3 real OCR `GOLD-EX-11=FAIL / NOT PROVEN`; **NOT FOR CLINICAL USE**.


## P4 R3/OQ-R01 and R21 recovery scope — owner decision request (2026-11-21)

At owner-merged PR #26 `main@1aed4595f8d9a90ece6af0659513e2bdbc98b448`, postmerge Actions #44896431925 retry attempt 3 completed SUCCESS, clearing the temporary CI-only blocker. R1-A / R2-A / C-35A / C-37A / R4 remain the only approved P4 architecture and offline-testing choices.

A *new documentation-only proposal* in `docs/phase-reports/P4_R3_OQR01_R21_RECOVERY_SELECTION_DECISION_20261121.md` presents two **independent pending** owner decisions: **R3-A** pins the exact arbitrary synthetic `demo-policy-1.1.0` parameters for later offline reference without runtime activation; **R21-S1** proposes a doctor-authored, auditable future run-selected document set that does not erase a failed original's open `VI-002` or trust a patient-declared recovery link. Alternative R3-B/C and R21-S2/S3 are documented. **Neither proposal is approved by merging a report.**

Next code PRs, if separately authorized, must be independently bounded: (A) fixture-only versioned demo-policy artifact and strict validation; (B) offline recovery-selection fail-closed matrix. No present run-gate, P5 implementation, workflow_run/review-item persistence, VI auto-clear or rule activation. P4 **IN_REVIEW**, P3 real OCR `GOLD-EX-11=FAIL / NOT PROVEN`. NOT FOR CLINICAL USE.


## P4 owner decision R3-A + R21-S1 (2026-11-21)

After owner-merged [PR #27](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/27) at `main@35c680b59d7aa2e7fb951d1bdd6650af5d839f01`, the owner explicitly said: **"تم دمج PR #27، وموافق على R3-A وR21-S1"**.

**R3-A APPROVED WITH STRICT SCOPE:** exact synthetic demo-only `demo-policy-1.1.0` reference numbers, clock, enabled VI catalogue and offline DR IDs; see `docs/phase-reports/P4_R3A_PINNED_DEMO_POLICY_REFERENCE_20261121.md`. No runtime policy installation, rule-tool exposure, medical claim or run clearance. New YAML/test-only fixture remains a code PR until owner acceptance.

**R21-S1 APPROVED AS FUTURE SOURCE-SELECTION SEMANTICS:** original terminal rejected source `VI-002` remains open, inclusion in selected run set must HALT, separate recovered selection needs explicit doctor-authored/audited omission and full run re-verification later. The patient-created recovery link does not prove equivalence. A subsequent offline P4 testing PR may model these rules but **cannot** implement P5 run identity or return `run_gate_completed=True`. R1-A deferred persistence is unchanged. P4 **IN_REVIEW**, original P3 GOLD-EX-11 real OCR **FAIL / NOT PROVEN**.


## P4 R21-S1 recovery selection offline matrix after PR #28 merge (2026-11-21)

- Owner merged PR #28 into `main@77538678a108bc0896b04713c2072e47b63a7550`; exact-main CI #44905949746 completed SUCCESS. Owner had already approved **R21-S1** separately from synthetic-only **R3-A** after PR #27. R21-S1 is a future *doctor-authored/auditable selected source* policy, **not** approval to ignore old blockers or to fabricate run identity.
- A new P4 offline-only component `backend/app/services/p4_recovery_selection_candidate.py` + synthetic SQLite matrix `backend/tests/p4/test_p4_recovery_selection_candidate.py` models selected original/recovery/both/neither, multi-generation ancestry, missing/duplicate doctor omission **proposals**, persisted terminal `VI-002`, independent recovery preflight, assignment/session scope and fail-closed errors. [New report](../phase-reports/P4_R21S1_OFFLINE_RECOVERY_SOURCE_SELECTION_20261121.md).
- This is only an **unpersisted proposal inspection**: `doctor_selection_audited=False`, `run_gate_completed=False`, `runtime_evaluable=False`, `run_gate_status=unavailable` **always**. No source-byte/OCR proof, no run-selected manifest, no P5 code/persistence, no issue mutation. Provisional new test collection 1076 backend/443 P3 pending CI and Windows acceptance before owner merge.
- **R1-A**, P4 IN_REVIEW, and original P3 real GOLD-EX-11 FAIL / NOT PROVEN remain unchanged. NOT FOR CLINICAL USE.


## P4 R21-S1 first CI correction checkpoint (2026-11-21)

- Backend CI #44906944016 collected **1077** cases, not the provisional 1076. P3 remains **443**; full count-token corrected append-only in `PHASE_3_WINDOWS_ACCEPTANCE.md` (token is *collection*, not PASS evidence).
- New dirty-session test setup caused an ORM autoflush; test now pins IDs before mutation and asserts the **unchanged** read-only inspector refuses a dirty Session. Full suite must pass exact-head CI and owner Windows gate before merge. No P5, VI auto-clear, real run gate or OCR claim. P4 IN_REVIEW.

## P4→P5 CH-01 conditional handoff design proposal after PR #29 (2026-11-21)

- Owner-merged [PR #29](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/29) to `main@e01250dd393fdd639bed65cee298beb8ecc33b1b` (head `06bb56ff5d7e44c7d0c4028388ed5629d95093d5`); exact-main [CI #44912202066](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44912202066) **COMPLETED / SUCCESS**, Backend and Frontend. Prior owner Windows R21-S1 gate at the PR head: targeted 25 PASS, full 12 PASS / 0 FAIL / 1 optional Playwright SKIP. P4 remains **IN_REVIEW** and issue #14 stays OPEN.
- The owner then approved **preparing a documentation-only P4-to-P5 Conditional Handoff PR**. [CH-01 proposal](../phase-reports/P4_P5_CONDITIONAL_HANDOFF_20261121.md) reconciles the P4-3 `review_item.workflow_run_id NOT NULL FK` dependency with the genuine P5-owned run identity under existing **R1-A**. Proposed narrow exception: after separate explicit **owner PR-thread ratification** and merge/green exact-main CI, allow only a **P5-F0** run-identity-and-audited-selection foundation PR to begin before complete P4 acceptance; return to P4 integration/acceptance after the run/evidence prerequisites. No P5 code is authorized by this proposal alone.
- **CH-01 decision = PENDING OWNER PR-THREAD RATIFICATION.** Required exact marker: `RATIFY-P4-P5-CONDITIONAL-HANDOFF-FOUNDATION-ONLY`. An explicit owner decision in the CH-01 PR thread **and** a merged tracker decision are prerequisites under `AGENTS.md` §§1–2. This append-only checkpoint is a **proposal**, not a self-awarded phase/file-scope exception. P4 `IN_REVIEW`, P5 `TODO` until ratification; do not set `run_gate_completed=True`, activate DR policy, fabricate `workflow_run`, persist review items, claim verified OCR source glyphs, or touch P6. Historical P3 `GOLD-EX-11 = FAIL / NOT PROVEN` unchanged; NOT FOR CLINICAL USE.

## P5-F0 run identity and audited selection code PR opened under CH-01 (2026-11-21)

- Owner ratified CH-01 in the PR #30 conversation with exact marker `RATIFY-P4-P5-CONDITIONAL-HANDOFF-FOUNDATION-ONLY`, owner-merged PR #30 at `main@12c1920d2923e627621b16ac800d07a7054bad87`, and postmerge CI #44913434002 completed SUCCESS. This permits **only P5-F0**, a narrowly scoped foundation; P4 remains IN_REVIEW, P5 itself is NOT accepted.
- The proposed [P5-F0 foundation report](../phase-reports/P5_F0_RUN_FOUNDATION_REVIEW_20261121.md) describes a real `workflow_run` parent, immutable persisted doctor-context selected-source manifest and omission audit, migration and synthetic tests, while keeping every gate `unavailable` and no P4 DR activation, P5 agents, LLM, notification, or P6 UI. No execution PASS is claimed by submitting code.
- **Known scope-valid regression blocker:** historical `backend/tests/p2/test_p2_migration.py` hardcodes the old `head` revision `0005` and exact P3 table set. Updating that P2 test is **outside the ratified P5-F0 path allowlist**. Do not misrepresent this as a P5 application correctness failure or silently modify P2 tests; request a separately reviewed narrow test-maintenance authorization/PR before accepting P5-F0. Owner Windows and exact-head CI remain mandatory, and no auto-merge is authorized. Original P3 real OCR `GOLD-EX-11 FAIL / NOT PROVEN` unchanged; NOT FOR CLINICAL USE.

## P5-F0 legacy-migration test compatibility exception — owner authorization (2026-11-21)

- **Owner explicitly approved** the exact marker `APPROVE-P5-F0-LEGACY-MIGRATION-TEST-ONLY-EXCEPTION` in [PR #31's conversation](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31#issuecomment-7064518944) (2026-11-21 14:59:09 UTC). This append-only tracker entry records the written owner decision under `AGENTS.md` §§1/5/9 **before editing any legacy test or P3 handoff document**. It authorizes **test/documentation-only compatibility edits** to exactly these five paths within P5-F0 PR #31: `backend/tests/p2/test_p2_migration.py`, `backend/tests/p2/test_p2_scope_guards.py`, `backend/tests/p3/test_windows_ocr_acceptance.py`, `backend/tests/test_database.py`, and `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`.
- **Purpose/boundaries:** P1/P2/P3 tests must retain strict historical-revision assertions at `0005_p3_ocr_provenance` (or relevant earlier revision); the live migrated `head = 0006_p5_run_foundation` must additionally require exactly the four owner-authorized P5-F0 tables and strict foreign keys. The P3 Windows acceptance handoff may add a *clearly labeled future/test-collection count* `1096` measured by CI; it **must never replace historical passed counts or claim `1096 passed`**, because the last exact-head Backend run had failures. Any test adjustment may only reconcile version-bound expectations and historical collection tokens, not relax OCR/VI, security, schema integrity or phase-acceptance gates.
- **Evidence before compatibility edits:** [PR #31 push CI #44914856359](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44914856359) at `13f221e8fccf7459867b33a77c46eda5babfc36c`: Frontend SUCCESS; Backend six failing **legacy version/count assertions**, all new P5-F0 tests including the corrected dirty-session test no longer in failed summary. These are actual failed CI results, not P5-F0 acceptance. Maintain `P4=IN_REVIEW`, `P5-F0=IN_REVIEW`, P3 real `GOLD-EX-11=FAIL / NOT PROVEN`, **NOT FOR CLINICAL USE**; independent review, exact-head CI and owner Windows checks still required, no agent merge.

## P5-F0 Alembic smoke-only compatibility exception — owner authorization (2026-11-21)

- Owner [explicitly approved](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31#issuecomment-7064645259) exactly `APPROVE-P5-F0-ALEMBIC-SMOKE-ONLY-EXCEPTION` at 2026-11-21 15:08:59 UTC on PR #31. Under `AGENTS.md` §§1/5/9, this append-only record **precedes any write** to the one additionally permitted file, `scripts/python/check_alembic_smoke.py`.
- **Strict scope:** change only the revision-aware SQLite Alembic checker: `head` now means real revision `0006_p5_run_foundation`, with exactly four extra P5-F0 tables (`workflow_run`, `run_selected_document`, `run_selected_observation`, `run_source_omission`), all run FKs/required indexes/immutability triggers checked; preserve a separate `p3_stage1` state that demands the exact original `0005_p3_ocr_provenance` schema and the unchanged `p3_recovery`/`p3`/`p2`/`p1`/`base` gates. Do not waive foreign-key integrity, weaken P3 extraction/verification safety, enable review/agent/task tables, claim `GOLD-EX-11` OCR glyph integrity, or touch any other application/test/script file for this exception.
- Before this owner decision, [PR #31 head `7b1fe37505851c89ebae618b57a438163db04112`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31) passed Ruff lint/format, **completed the entire backend Pytest step with no failures**, passed Frontend, and completed Alembic upgrade-head/downgrade-base/upgrade-head, but [CI #44917004840](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44917004840) was **FAIL** solely at the old `check_alembic_smoke.py` expectation for 0005/no run tables. This is **not** a full CI PASS or owner Windows acceptance. Next: modify only the authorized checker, rerun exact-head CI and owner Windows, maintain PR #31 DRAFT / P4 IN_REVIEW / P5-F0 IN_REVIEW; NOT FOR CLINICAL USE.

## P5-F1 bounded run-bound verification gate — design proposal ONLY (2026-11-21)

- Owner-merged [PR #31](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/31) at `main@6f90c8d1308424a9c0d8efcc84a5fc5389e5d937`; exact-main [CI #44920665782](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44920665782) **COMPLETED SUCCESS** with both Backend and Frontend. Owner-submitted exact PR-head Windows acceptance was 12 PASS / 0 FAIL / 1 optional Playwright SKIP. This verifies **P5-F0 only**, not a genuine F1 run gate or full P5.
- At the owner's explicit request **“ابدأ تحضير P5-F1”**, a **docs-only** proposal was prepared in [P5-F1 run-gate design](../phase-reports/P5_F1_RUN_BOUND_VERIFICATION_GATE_DESIGN_20261121.md). It proposes a run-bound deterministic VI-001..006 preflight over persisted F0 selections, fail-closed source/snapshot checks, preserved historical OPEN terminal VI-002, typed immutable gate evidence and separate F1 synthetic test matrix. No code, migration, endpoint, LLM, DR, graph, task, notification or P4 persistence was changed by this proposal.
- **Decision PENDING, NO F1 IMPLEMENTATION AUTHORIZED BY CH-01.** Proposed exact owner PR-thread scope-ratification marker: `RATIFY-P5-F1-BOUNDED-RUN-GATE-SCOPE`. Design choices D-F1-01 (separate durable run gate receipt, P3 VI preserved), D-F1-02 (conservative status/replay handling), D-F1-03 (observation-only remains out-of-scope) need owner review. Only after explicit owner ratification in the design PR, merged tracker decision, green exact-main CI and a *new separately scoped code PR* may F1 implementation begin. No self-merge or self-acceptance.
- **Boundaries unchanged:** F0 returns `run_gate_status=unavailable`, `run_gate_completed=False`, `runtime_evaluable=False`; P4 **IN_REVIEW**, issue #14 OPEN; real P3 `GOLD-EX-11 FAIL / NOT PROVEN`; synthetic educational only / **NOT FOR CLINICAL USE**.

## P5-F1 bounded gate design — explicit owner ratification (2026-11-21)

- **Owner's exact written decision:** `RATIFY-P5-F1-BOUNDED-RUN-GATE-SCOPE`, posted by `Muhammed-Fathi` in [PR #32 Conversation](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/32#issuecomment-7065279772) on **2026-11-21 15:58:25 UTC**. This is a scoped **design and future-implementation-sequencing ratification** following the docs-only proposal; it is not independent F1 technical acceptance, F1 source-code permission effective before design merge, P4 phase approval, or authority for agents to merge.
- **Ratified design choices:** **D-F1-01:** recommend separate append-only run-gate evaluation/blocker evidence instead of modifying/clearing historical P3 `verification_issue` rows; migration and exact contract changes require independent review in the later F1 code PR. **D-F1-02:** conservative fail-closed HALT/UNAVAILABLE decisions, persistent fingerprint/replay evidence; no graph/N2 execution, DR runtime activation, or unapproved status transition. **D-F1-03:** observation-only starts stay out of F1 scope; the F0 document-selected precondition remains unchanged. Source SHA metadata is *not* OCR glyph verification.
- **Boundaries of authorization:** after **owner review + merge of PR #32** and **SUCCESS on the exact merged `main` SHA**, a *separate* one-phase **P5-F1 code PR** may implement only the bounded deterministic run-bound VI-001..006 gate from [the design](../phase-reports/P5_F1_RUN_BOUND_VERIFICATION_GATE_DESIGN_20261121.md), including source freshness, patient/doctor/session scope, unchanged historical terminal OPEN VI-002, deterministic typed evidence and synthetic safety/negative tests. Include contract/schema changes only with documented review in that PR; stop for a new owner decision if an unresolved incompatible requirement or path outside the declared allowlist appears. Agent may never self-approve/merge.
- **Not authorized:** P5-F2 evidence adapter, full LangGraph nodes, LLM, DR evaluation, P4 review-item persistence, P6 UI/API, tasks/notifications, clinical use, P3 OCR false-clean waiver, or P4/P5 phase PASS. **P4 stays `IN_REVIEW` and issue #14 OPEN**, F0 gate fields remain `unavailable/False` until implemented F1 contract, P3 real `GOLD-EX-11 = FAIL / NOT PROVEN`. **SYNTHETIC EDUCATIONAL / NOT FOR CLINICAL USE.**

## P5-F1 bounded run-bound VI gate implementation branch — IN_REVIEW (2026-11-21)

- Owner [PR #32](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/32) ratification `RATIFY-P5-F1-BOUNDED-RUN-GATE-SCOPE` was recorded and merged to `main@55e86083dec15334344917fdeac38516f6413957`; exact-main CI [#44922487176](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44922487176) **COMPLETED SUCCESS**. This authorizes only a separately reviewed F1 code slice, not F1 acceptance, F2 or phase advancement.
- New separate `feat/p5-f1-run-bound-vi-gate` branch proposes the internal-only deterministic run-specific VI-001..006 checker, additive `0007_p5_run_gate` immutable evidence schema, source-file hash/replay and doctor-scope validation, synthetic tests, and append-only contracts/report; see [P5-F1 implementation review](../phase-reports/P5_F1_IMPLEMENTATION_REVIEW_20261121.md). All gate outputs retain `runtime_evaluable=False`. No P3 historical issue rewrite, DR, graph, LLM, public endpoints, UI, tasks or notifications.
- **Tests not yet verified at this checkpoint:** F1 full PR-head CI and owner isolated Windows are mandatory; do not claim gate PASS before inspecting logs. Migration `0007` likely invalidates old `head=0006` historical P2 test and smoke-script assertions; changes outside ratified F1 allowlist require a new precise owner PR-thread exception before any edit.
- **Boundaries persist:** P4 `IN_REVIEW`, issue #14 OPEN, F0 receipt `run_gate_status=unavailable`, original P3 real `GOLD-EX-11 FAIL / NOT PROVEN`, **NOT FOR CLINICAL USE**. Owner alone may merge or accept the phase.
 
## PR #33 exact-path 0007 legacy compatibility exception — owner decision (2026-11-21)

- The owner `Muhammed-Fathi` posted the exact marker `APPROVE-P5-F1-0007-LEGACY-COMPAT-ONLY-EXCEPTION` in [PR #33 Conversation](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33#issuecomment-7070068019) at **2026-11-21 22:16:50 UTC**. This is explicit limited authorization to correct the old migration-version/collection-compatibility checks for the new owner-ratified P5-F1 `0007_p5_run_gate` schema, **not** an acceptance or authorization to dilute any assertions.
- **Before any exception edits**, at the pinned [PR #33 head `b802a3cf6e4725997042f542ecbaeb98ca5f52c2`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33), [push CI #44924018806](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44924018806) was **Backend FAILURE**, **Frontend SUCCESS**. Pytest had six *legacy head/count* failures: P2 migration 2, P2 scope guards 1, P3 Windows handoff collection guard 1, generic database migration 2. That run measured **1116 backend collected** tests and original P3 **443** collection; those are *collected*, NOT all passed. Newly authored F1 tests were not listed among this run's failed cases. The prior `scripts/python/check_alembic_smoke.py` still expects exact 0006 at `head` and must be version-updated while retaining strict historic-state checks.
- **Exactly six extra paths authorized** by this owner marker (and no other legacy source): `backend/tests/p2/test_p2_migration.py`, `backend/tests/p2/test_p2_scope_guards.py`, `backend/tests/p3/test_windows_ocr_acceptance.py`, `backend/tests/test_database.py`, `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`, `scripts/python/check_alembic_smoke.py`. Change only new-`0007` compatibility; keep all original P1/P2/P3/0005 and F0/0006 targeted checks, forbiddance of later-phase P4/DR/agent tables, real FK/unique/index/immutability checks, and credible `collected` vs `passed` labeling. No skips or test threshold relaxations.
- **No phase acceptance or merge approval**: PR #33 must stay Draft/IN_REVIEW pending exact-head full GitHub Backend+Frontend SUCCESS, independent owner Windows acceptance and code/security review. P4 IN_REVIEW, issue #14 OPEN, P3 real `GOLD-EX-11=FAIL / NOT PROVEN`; synthetic educational / NOT FOR CLINICAL USE.

## P5-F2 design proposal — owner decision pending (2026-11-22)

- **Entry point independently verified:** owner-merged [PR #33](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/33), `main@3b236bfb29e7235b09b433ff92e271dc0900a2c5`; exact-main [postmerge CI #44959531076](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44959531076) **COMPLETED SUCCESS** (Backend Python 3.12 + Frontend Node 22). Previous owner isolated Windows on exact PR head: **12 PASS / 0 FAIL / 1 optional Playwright SKIP**; this is F1 evidence only, not F2 code validation.
- **Proposal only, not ratified:** [P5-F2 bounded run-evidence/bridge design](../phase-reports/P5_F2_EVALUABLE_EVIDENCE_BRIDGE_DESIGN_20261122.md) documents four owner decisions **D-F2-01** server-owned sealed V2 evidence envelope with no runtime authorizer; **D-F2-02** exact F1 PROCEED/identity/fingerprint and file-byte freshness revalidation using a read-only consistent snapshot, never a mutating F1 shortcut; **D-F2-03** fixed F0 selected current IDs, explicit 0/6/20 cardinality behavior, trusted document lineage and versioned same-patient history policy; **D-F2-04** additive versioned TOOL_CONTRACTS §3.5/3.7 adapter shapes, **without** executing DR rules or persisting P4 review items. Suggested later one-phase P5-F2 code allowlist and 22-case negative/positive matrix in the design.
- **No implementation permission until owner ratifies exact marker** `RATIFY-P5-F2-BOUNDED-EVIDENCE-BRIDGE-SCOPE` in the future F2 design PR Conversation, design merge is owner-reviewed, and exact merged-main CI succeeds. Marker approves only the bounded design/code scope, not source code, P4 acceptance, rule activation, graph/LLM/UI, or P5 PASS. Any later out-of-allowlist F1/P4/P3/test/migration touch needs new explicit owner exception.
- **Status unchanged:** F1 code exists merged (not overall P5 accepted), P4 `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, real P3 `GOLD-EX-11 FAIL / NOT PROVEN`; no clinical interpretation or real-data use. **SYNTHETIC EDUCATIONAL / NOT FOR CLINICAL USE.**

## P5-F2 design owner ratification — PR #34 (2026-11-22 Cairo)

- **Owner identity, exact decision and verifiable comment:** repository owner `Muhammed-Fathi` posted precisely `RATIFY-P5-F2-BOUNDED-EVIDENCE-BRIDGE-SCOPE` in [PR #34 Conversation](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/34#issuecomment-7070783010) on **2026-11-21 23:18:13 UTC** (2026-11-22 01:18:13 Cairo). This was independently read using the connected authenticated GitHub source. Before this documentation update, design head `5b93dd293449276633046dcf33e80ea092b7d2ec` had [PR CI #44960316685](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44960316685) **COMPLETED SUCCESS**. This is an owner **design/scope ratification**, **not** code acceptance or a mandate to begin F2 code immediately.
- **D-F2-01 RATIFIED:** internal immutable versioned `EvaluableReviewEvidenceV2` derived solely from a persisted F0 run and authenticated stored doctor scope; carries typed bounded verified facts, observation trust, source IDs/provenance and explicit exclusions. `runtime_evaluable=False`, `policy_status=unapproved` and `rules_executed=False` stay fixed; no runtime/agent/DR authority is inferred from an F1/F2 receipt.
- **D-F2-02 RATIFIED:** read-only exact-F1-`PROCEED` fingerprint, immutable gate/blocker evidence, user/session/assignment, manifest, verified corrections, versions/clock and current file-byte integrity recheck within a consistent SQLite snapshot; never treat cached F1 as permanently fresh and never call F1's *mutating* evaluation function as an F2 read-only shortcut. Non-atomic filesystem-vs-database boundary remains a future-consumer recheck obligation.
- **D-F2-03 RATIFIED:** only F0 server-persisted current observation IDs (0 means typed no-current/empty comparisons; >6 denies rather than truncates although F0 allows 20). **Chosen recommended history policy:** fixed versioned **365-day** same-synthetic-patient deterministic history, ≤100 records with explicit overflow denial, prior-time tie-break and typed exclusions; no user-supplied current/baseline selectors or lookback override. Keep `self_reported_validated` labelled and never promote it; use closed `map-1.0.0` aliases and units with no imputation/unit conversion.
- **D-F2-04 RATIFIED:** additive versioned internal-only interfaces reconciling `TOOL_CONTRACTS.md` §§3.5/3.7 to produce P4-compatible comparison inputs and evidence references, **without executing `evaluate_demo_review_rules`**, creating `DR-*` outputs, `review_item` or `evidence_link` records, or starting a graph/LLM/API/UI/task/notification.
- **Exact later F2 code scope ratified but NOT yet effective:** proposed one-phase follow-up PR may modify only `backend/app/services/p5_evidence_bridge.py`, `backend/app/schemas/p5_review_evidence.py`, `backend/app/services/p5_run_gate.py` (only if independently reviewed read-only F1 snapshot extraction is indispensable), `backend/tests/p5/test_p5_evidence_bridge.py`, `docs/contracts/TOOL_CONTRACTS.md`, `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, `docs/phase-reports/P5_F2_IMPLEMENTATION_REVIEW_20261122.md`, and this append-only `docs/roadmap/PHASE_PROGRESS.md`. The full 22-case F2 synthetic matrix remains an **untested requirement**. **Separate activation gates:** owner reviews and merges this documentation PR *after* CI SUCCESS on its final ratified head; verify exact merged-main CI SUCCESS; only then create a separate F2 code branch/PR. Any other path needs a separately recorded exact-path exception, with no P3/P4 contract weakening or legacy test waiver.
- **No phase approval:** P5-F2 design ratification does not mean F2 code exists or passes tests. P4 remains **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, full P5 unaccepted; original P3 real `GOLD-EX-11 = FAIL / NOT PROVEN` unchanged. Synthetic local educational only, **NOT FOR CLINICAL USE**. No agent self-approval or auto-merge.

## P5-F2 isolated code candidate — IN_REVIEW, not owner accepted (2026-11-22)

- **Gate independently verified before branch:** owner-merged [P5-F2 design PR #34](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/34), merge `26aabd8a8d5d0987430e64e97cbd9ae110cb1a52`; [exact-main postmerge CI #44978669932](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44978669932) **COMPLETED SUCCESS** (Backend Python 3.12, Frontend Node 22). Owner's exact `RATIFY-P5-F2-BOUNDED-EVIDENCE-BRIDGE-SCOPE` decision was recorded before that design merge. This grants the narrowly proposed implementation files only and **does not** preapprove code.
- **Code branch:** `feat/p5-f2-run-evidence-bridge`, based on exact green merged-main commit, implementing the bounded internal-only V2 object, F1 read-only gate-inspection adapter and synthetic tests. This checkpoint is **IN_REVIEW** until exact-head complete CI plus independent owner Windows and final technical/scope review; do not merge or call phase PASS on a test claim alone.
- **Required security invariants:** recompute existing F1 PROCEED/immutable blockers/doctor scope/selected bytes and source fingerprint inside fresh SQLite lock; no F1 write/audit from F2, no caller-derived role/flags/source selection; selected current count >6 fails, 0 yields `no_current_selected`, 365-day/≤100 same-patient history is bounded and deterministic, never upgrades self-report trust; all internal outcomes `runtime_evaluable=False`. A future consumer must recheck external bytes (database/filesystem non-atomic).
- **Still excluded:** P4 DR policy activation/evaluation, `review_item`/`evidence_link` persistence, graph/LLM/endpoint/frontend/task/notification, P3 extraction code or reclassification of real OCR `GOLD-EX-11 = FAIL / NOT PROVEN`. P4 `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN. **SYNTHETIC / NOT FOR CLINICAL USE.**

## P5-F2 exact one-path P3 handoff collection exception — owner approval (2026-11-22)

- **Authenticated owner approval:** `Muhammed-Fathi` posted the exact `APPROVE-P5-F2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION` marker in [PR #35 Conversation](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/35#issuecomment-7075105100) at **2026-11-22T06:03:52Z** (08:03:52 Cairo). Verified independently against current GitHub comments before making any changes outside the original eight-path F2 design allowlist.
- **Exact extra path and allowed operation:** append-only **current collection** checkpoint to `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` ONLY. No other out-of-allowlist path, no modifications to original P3 tests or OCR sources/fixtures, old P3 outcome metrics, historical records, stored issue/gate decisions, or CI test thresholds. The approved handoff note must state the CI-observed current total **1140 collected**, of which **443** are the P3 suite; collection is **NOT** a claim that 1140 tests passed.
- **Motivation and evidence:** exact-head [PR #35 push CI #44979500529](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44979500529) at `f09d4d97a39fc40a3fb34bd625523e94a76e293e` showed Ruff lint/format PASS, Frontend SUCCESS, and **Backend Pytest FAIL** at the strict historic `test_handoff_test_count_matches_the_suite_it_describes` assertion because new synthetic F2 tests increased collected backend cases from the prior 1121 to 1140. Original P3 collection remained **443**. This checkpoint MUST NOT be called a successful backend run; Alembic/OpenAPI/secret scanner did not execute after the failure.
- **Conditional next gate:** record this ratification in the roadmap before changing the permitted handoff document; add the above exact-current paired collection token (append-only); execute full exact-head Python/Frontend Actions again and obtain independent owner Windows acceptance at final reviewed SHA before any owner merge. **PR #35 remains DRAFT / IN_REVIEW**, F2 NOT accepted, P4 `IN_REVIEW` [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, original real OCR `GOLD-EX-11 = FAIL / NOT PROVEN` unchanged. **SYNTHETIC ACADEMIC / NOT FOR CLINICAL USE.**

## P4 Run-Bound Integration proposal after P5-F2 PR #35 — NO CODE APPROVAL (2026-11-22)

- **Verified dependency clearance (not phase acceptance):** owner-merged [P5-F2 PR #35](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/35) with `main@deb6b15f19e4a1c0571c513d158c2b9e7128eb61`. Exact merged-main [GitHub Actions #44994402273](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44994402273) **COMPLETED SUCCESS**, Backend Python 3.12 and Frontend Node 22. Prior isolated Windows review was 12 PASS / 0 FAIL / 1 optional Playwright SKIP at the **premerge PR #35 head** `6d015bc0c2749dec7ce62de609f801ade5da4fe3`, not a fresh postmerge Windows run.
- **New documentation-only design:** `docs/phase-reports/P4_RUN_BOUND_INTEGRATION_DESIGN_20261122.md` proposes **D-RB-01** one safe read-only P4-RB1 run-bound preview slice (no rules executed), **D-RB-02** explicit split F2 365-day history versus R3-A 90-day demo baseline, **D-RB-03** separate later ratification for complete six-rule deterministic evaluator/runtime policy and **D-RB-04** separate later ratification for strict P4 `review_item`/`evidence_link` SQLite persistence with genuine run FK, replay and atomicity. It also specifies a 24-case future test matrix and exactly eight future **P4-RB1-only** code paths.
- **DECISION PENDING:** owner must post exact `RATIFY-P4-RB1-READONLY-INTEGRATION-SCOPE` in this design PR's Conversation, review/merge docs, and verify exact merged-main CI before a separate **P4-RB1 code PR** may begin. This marker, if given, **does NOT authorize** any P4-RB2/RB3/RB4 code, DR evaluation or persistence, P5 graph/LLM, P6 UI, notification or task. No approval may be inferred from an assistant's PR text. AGENTS.md no agent self-merge/phase PASS unchanged.
- **Source/clinical limitations:** never reuse a 365-day delta for the 90-day policy without a scoped recomputation; keep F1 fresh PROCEED and P5-F2 `runtime_evaluable=False`, maintain original terminal OPEN VI-002, strict trust labels and selected current cap, and preserve real P3 `GOLD-EX-11 FAIL / NOT PROVEN`. P4 **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, full P5 not accepted, **NOT FOR CLINICAL USE**.

## P4-RB1 design scope: owner PR #36 ratification (2026-11-22)

- **Explicit authenticated owner action:** GitHub repository owner `Muhammed-Fathi` posted the exact standalone `RATIFY-P4-RB1-READONLY-INTEGRATION-SCOPE` marker at [PR #36 Conversation comment #7075542080](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/36#issuecomment-7075542080), **2026-11-22T06:48:34Z** (Cairo 08:48:34). Independently checked against the actual API comment author and body before recording this decision. Owner ratification of this design is **not** self-approval of the future implementation or permission to merge by an agent.
- **Ratified D-RB-01:** the first later implementation slice is **P4-RB1 internal read-only run-bound input preview** only. It uses the real persisted F0 run and fresh authenticated F1/F2 evidence; absolutely no rule execution/`ReviewFlag`/`DR-*`, migration, `review_item`/`evidence_link`, workflow status transition, graph/LLM/API/UI/task/notification or clinical action. Preserve `runtime_evaluable=False`, `rules_executed=False`, `policy_status=unapproved`.
- **Ratified D-RB-02:** independently recompute eligible same-synthetic-patient comparisons within the **R3-A pinned 90-day demo policy**; never reuse the fixed **F2 365-day** baseline/delta as if it were a 90-day decision. Server-owned F0 selected current 0..6 only (zero gives typed no-current; 7..20 fail), capped server-derived history and exact trusted policy identity/clock, patient/doctor/session scope and verification-source freshness. A read-only preview spanning SQLite sessions/filesystem is never an atomic, reusable write clearance.
- **Ratified D-RB-03:** the six-rule offline synthetic DR catalogue and strict R3-A policy are a **future design only**. Existing candidate rules and caller-supplied test-only `blocking_fact_count` cannot be activated by this marker. A full pure rule evaluator would require a **separate owner-ratified P4-RB2** PR, and runtime/persistent use further P4-RB3 authorization.
- **Ratified D-RB-04:** strict run-owned `review_item.workflow_run_id NOT NULL FK`, `evidence_link` provenance, no duplicate `(workflow_run_id, dedupe_key)`, atomic fail-closed persistence and future migration/compatibility rules are design goals requiring **separate P4-RB3 owner review**. No schema or historical P3/F1/P5 change is approved now. Remaining run-backed GOLD A/B/C/D and P4 phase signoff stay separate.
- **Exactly eight future P4-RB1 code paths (only after owner merges PR #36 and exact merged-main CI succeeds):** `backend/app/services/p4_run_bound_preview.py`, `backend/app/schemas/p4_run_bound_preview.py`, `backend/tests/p4/test_p4_run_bound_preview.py`, `docs/contracts/TOOL_CONTRACTS.md`, `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, `docs/phase-reports/P4_RB1_READONLY_ADAPTER_REVIEW_20261122.md`, `docs/phase-reports/PHASE_4_REPORT.md`, `docs/roadmap/PHASE_PROGRESS.md`. Any additional path requires a fresh exact owner PR-thread scope exception before change (including P3 handoff count compatibility). No other phase authorization inferred.
- **Gating sequence and evidence honesty:** this is a **documentation-only PR** at a reviewed `main@deb6b15f19e4a1c0571c513d158c2b9e7128eb61` baseline (postmerge CI #44994402273 SUCCESS). Record exact-head CI after this ratification append; owner personally reviews then marks Ready for review and merges PR #36; independently verify **new** main postmerge Backend + Frontend SUCCESS before starting a distinct P4-RB1 code PR. Neither owner approval comment nor green design CI is executable P4 acceptance. **P4 IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, overall P5 unaccepted, historic real P3 `GOLD-EX-11 FAIL / NOT PROVEN` unchanged; **SYNTHETIC EDUCATIONAL / NOT FOR CLINICAL USE**.

## P4-RB1 isolated read-only implementation proposal — tests pending (2026-11-22)

- **Prerequisite independently verified:** repository owner merged [P4 Run-Bound design PR #36](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/36), merge SHA `3995584df45cfe0d3c8709f287eb405257a7540d`; exact-main [CI #44996564923](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44996564923) COMPLETED **SUCCESS** (Backend Python 3.12 + Frontend Node 22). The owner previously posted exact `RATIFY-P4-RB1-READONLY-INTEGRATION-SCOPE` [comment #7075542080](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/36#issuecomment-7075542080), recorded inside that owner-merged design. **Only the first eight P4-RB1 read-only implementation paths are now permitted.**
- Separate `feat/p4-rb1-readonly-run-preview` code branch (P4 ONLY): `backend/app/services/p4_run_bound_preview.py`, `backend/app/schemas/p4_run_bound_preview.py`, `backend/tests/p4/test_p4_run_bound_preview.py`, append-only `docs/contracts/TOOL_CONTRACTS.md` and `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, new `docs/phase-reports/P4_RB1_READONLY_ADAPTER_REVIEW_20261122.md`, append-only `docs/phase-reports/PHASE_4_REPORT.md` and this ledger. No other path, migration, existing P4/P5 code, test compat script, policy YAML, GOLD fixture, P3 source/test, API, graph/LLM/UI/task/notification allowed.
- **Implementation candidate, NOT a tested PASS:** internal authenticated server-owned F2 read-only recheck, fresh SQLite locked F1/current-history inspection, strictly pinned R3-A `demo-policy-1.1.0` canonical SHA and policy fixture clock, **90-day** policy comparison independent of F2's **365-day** result, final F2 freshness check and rollback. Typed DTO cannot authorize DR/runtime (`runtime_evaluable=False`, `rules_executed=False`, `policy_status=unapproved`, `review_items_persisted=False`). Selected 0 means no current, >6 denies, history cap and trust labels preserved. SQLite and filesystem separate transactions are not an atomic execution clearance.
- **Mandatory later gates:** exact-final-head GitHub Python Ruff/Pytest/Alembic/OpenAPI/scanner and Node CI, original P3/F0/F1/F2 regression, independent owner Windows PowerShell 5.1 `setup.ps1` + `test_all.ps1`, independent code/security review and explicit owner merge. New P4 tests may increase the strict historical P3 handoff *collection* count: report CI failure and request a **fresh exact owner approval for append-only single P3 handoff file** before changing it; never modify P3 tests or historical passed outcomes without permission.
- **Unchanged non-acceptance:** P4 `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, P5 overall not accepted, R3-A policy pinned offline reference only, full P4 six-rule evaluation and run-owned review persistence NOT authorized, original real P3 OCR `GOLD-EX-11 = FAIL / NOT PROVEN`; SYNTHETIC / **NOT FOR CLINICAL USE**.

## P4-RB1 PR #37 owner-approved P3 handoff collection-only exception (2026-11-22)

- **Authenticated explicit exception:** repository owner `Muhammed-Fathi` posted exact standalone `APPROVE-P4-RB1-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION` at [PR #37 Conversation comment #7076184528](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/37#issuecomment-7076184528) at **2026-11-22T07:53:41Z** (09:53:41 Cairo). Independently verified the exact comment author/body/time via GitHub issue comments **before any out-of-allowlist file modification**. This exception applies to **PR #37 only**, not P4 phase approval or RB2/RB3.
- **One additional path authorized:** `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` ONLY, **append-only current collection pairing**, in addition to the original eight RB1 paths. The current exact-head [red Push CI #44998192004](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44998192004) and [red PR CI #44998195330](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/44998195330) at `863731f01e5e74c2cac74bb4ca8710acee397591` measured **1155 collected**, of which **443** are P3. This is a **collection count, NOT 1155 tests passed**; Backend Pytest **FAILED exactly one documented historical collection-pairing test**. New RB1 and other tests do **not appear in the failure summary**; Ruff lint/format and Frontend SUCCESS. No Alembic/OpenAPI/scanner downstream PASS can be claimed for that red Backend run.
- **Permitted exact operation:** append the current **`**1155 collected**`** / **`**443**`** P3 paired token to that single handoff document while preserving the previous 1140-collected F2 checkpoint and **all** historical P3/Windows/OCR status claims. Absolutely no P3 source/test/fixture/threshold changes, no alteration to the former P4 offline-only policy guard, no CI bypass, no revision of actual original real OCR `GOLD-EX-11 FAIL / NOT PROVEN`. If a new suite change alters collection, pause for a fresh measured number before writing it; do not invent PASS.
- **Required remaining gates:** amend handoff ONLY after this permission record, independently review **nine-path diff**, run full exact-final-head Backend and Frontend CI, obtain owner **Windows exact SHA** `setup.ps1` + `test_all.ps1` evidence and independent security review. **No agent merge, no RB1 owner acceptance, no P4 phase PASS** from this narrow exception. P4 remains `IN_REVIEW`, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, overall P5 unaccepted; **SYNTHETIC / NOT FOR CLINICAL USE**.

## P4-RB2 design-only proposal after RB1 owner merge — DECISION PENDING (2026-11-22)

- **Independent merge and green-main gate:** [P4-RB1 PR #37](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/37) was merged by owner on 2026-11-22T08:37:08Z; current `main@fb859ba254c24f63e4cad0036277044549cc3f27` independently matches the merge SHA; exact-main [GitHub CI #45003663828](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45003663828) COMPLETED SUCCESS for Backend and Frontend. Owner Windows evidence at the **prior PR head**, not the merge SHA, was `setup.ps1` PASS and `test_all.ps1` 12 PASS / 0 FAIL / 1 Playwright SKIP. These are RB1 facts only, **not RB2 tests**.
- **Unratified three-document proposal:** `docs/phase-reports/P4_RB2_OFFLINE_SIX_RULE_DESIGN_20261122.md` requests approval for **D-RB2-01** pure offline six-rule evaluation only; **D-RB2-02** sealed typed synthetic fixture provenance with no counterfeit doctor/source verification or client blocker/gate flags; **D-RB2-03** exact deterministic DR-001/003/005/006/008/009 semantics under R3-A's arbitrary 90-day/30-day demo values, trust and per-type caps; and **D-RB2-04** 18-case test gate including GOLD-A/B/C/D *offline* only, full CI, independently witnessed Windows and no writes. Existing RB1 preview `runtime_evaluable=False` remains **non-authoritative**; no API/agent/tool wiring.
- **Exact proposed future RB2-only eight-file code allowlist, NOT YET APPROVED:** `backend/app/services/p4_rb2_offline_rules.py`; `backend/app/schemas/p4_rb2_offline_rules.py`; `backend/tests/p4/test_p4_rb2_offline_rules.py`; `backend/tests/p4/test_p4_rb2_gold_offline.py`; append-only `docs/contracts/TOOL_CONTRACTS.md`; new `docs/phase-reports/P4_RB2_OFFLINE_IMPLEMENTATION_REVIEW_20261122.md`; append-only `docs/phase-reports/PHASE_4_REPORT.md`; append-only this `docs/roadmap/PHASE_PROGRESS.md`. No extra file is authorized by prior RB1/R3-A comments. Especially no P3 handoff, existing candidate/P5/RB1 source, policy YAML, GOLD expected fixture, scanner, migrations or API changes. If strict P3 suite collection changes under future RB2 tests, seek a **new separately verified owner exact-path exception** before appending a current collection note. No past PASS/OCR rewrite.
- **Owner action required:** post exact `RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE` in this design PR's Conversation *only if all four decisions and future first-code allowlist are accepted*. Then independently confirm marker author/body/time, record approval append-only here, verify CI on amended docs HEAD, owner-only review/merge, check exact newly merged-main CI, and **only then** start a separate RB2 code PR. No agent self-approval/merge or next-phase code.
- **Unchanged:** P4 remains **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN; overall P5 not accepted; RB2/RB3/RB4 not implemented or approved by this design PR; real P3 `GOLD-EX-11 = FAIL / NOT PROVEN` unchanged; **SYNTHETIC ACADEMIC / NOT FOR CLINICAL USE**.


## P4-RB2 owner ratification recorded — OFFLINE DESIGN ONLY (2026-11-22)

- **Exact owner decision verified:** [PR #38 Conversation marker](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/38#issuecomment-7076744806) from repository owner `Muhammed-Fathi` on `2026-11-22T08:48:05Z`: `RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE`. This records D-RB2-01..04 and the **eight-path first RB2 implementation allowlist** as an offline synthetic-design scope decision; it is **not** phase acceptance, code execution permission on main, or consent for agent merging.
- **Design gate before this append:** PR #38 initial docs-only HEAD `54891bad219c2716731315c4c01ca92af797106a`, exactly three Markdown paths, [PR CI #45004288749](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45004288749) completed SUCCESS for Backend Python 3.12 and Frontend Node 22. This CI is **prior-head design CI only** and **must be rerun/rechecked on the final head containing this record**.
- **Strict next gate:** repository owner alone reviews, marks PR #38 ready and merges the *docs-only* PR after green CI on exact final docs head; independently verify CI SUCCESS on exact new `main` merge SHA before creating a **separate** RB2 pure OFFLINE code PR confined to the eight paths approved in [RB2 design](../phase-reports/P4_RB2_OFFLINE_SIX_RULE_DESIGN_20261122.md). Any extra path, including historical P3 collection pairing, requires a **fresh exact owner PR-thread exception**; RB1 exceptions do not carry over.
- **Not authorized:** no runtime agent/API/Graph/LLM/tool activation, no `review_item`/`evidence_link` DB writes, migrations, tasks, notifications, clinical use, or RB3/RB4 implementation/acceptance. P4 remains **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN, full P5 not accepted. The original real P3 OCR `GOLD-EX-11 FAIL / NOT PROVEN` remains unchanged. **SYNTHETIC EDUCATIONAL DEMO ONLY — NOT FOR CLINICAL USE.**


## P4-RB2 pure offline six-rule implementation — IN_REVIEW (2026-11-22)

- **Entry gate independently passed:** owner-merged design [PR #38](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/38) at `main@eaab808b81986077c94eec8f4858c9f746c92ca8` and exact-merge [CI #45005337550](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45005337550) COMPLETED SUCCESS, both Backend Python 3.12 and Frontend Node 22. Exact authenticated owner marker `RATIFY-P4-RB2-OFFLINE-SIX-RULE-SCOPE` had been recorded in PR #38 before the docs merge.
- New independent `feat/p4-rb2-offline-six-rules` implements the **eight named authorized files only**, including a pure typed non-authoritative six-rule fixture evaluator, tests, GOLD-A/B/C/D offline replay, append-only contract and reports. `runtime_evaluable=false`, `rules_executed=false` (in run sense), `review_items_persisted=false`, `policy_status=unapproved`. Distinct document source lineage is **fixture-asserted only**; no source can be promoted to genuine doctor verification by the pure evaluator.
- **No initial implementation gate outcome claimed:** final exact-head CI/owner isolated Windows validation/review PENDING. If newly collected RB2 tests change P3 collection pairing, STOP and get a **new** owner PR-thread exact-path exception, never reuse a prior RB1/F2 authorization or alter any old test, fixture, scanner or P3 OCR claim.
- P4 issue [#14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains OPEN and P4 IN_REVIEW. RB3 persistence, RB4 genuine run-backed acceptance, full P5 graph/LLM/UI, tasks and notices NOT authorized by this code PR. Real `GOLD-EX-11 FAIL / NOT PROVEN` unchanged. **SYNTHETIC ONLY / NOT FOR CLINICAL USE.**


## P4-RB2 measured CI pairing blocker — owner one-path exception REQUESTED (2026-11-22)

- [PR #41](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41), tested code HEAD `1a8405f666ca4211613cbfd0e42bbac1280b77ef`, [CI #45006265207](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45006265207): Frontend Node 22 SUCCESS; Backend Ruff lint and Ruff format SUCCESS; full Pytest reached 100% and **FAILED one** historical `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` check. Measured whole-backend **1204 collected**, historical P3 **443**. Collection ≠ all tests passed; no RB2 rule test appears in the failure summary. Alembic/OpenAPI/scanner downstream SKIPPED and independent Windows NOT RUN.
- **STOP, not a code or medical finding closure:** original eight-path scope forbids touching `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` without a fresh owner PR #41 Conversation marker `APPROVE-P4-RB2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION`. This is merely a **request**; NO ninth-path permission has yet been verified. The requested exception permits only an append-only honest **`**1204 collected**`** / **`**443**`** pairing with historical P3/Windows and `GOLD-EX-11 FAIL / NOT PROVEN` unmodified. The earlier #37 exception does not transfer.
- P4 remains **IN_REVIEW**, [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) OPEN. PR #41 remains DRAFT, NOT MERGE-READY. No RB3/RB4 activation, patient actions, production or clinical use.


## P4-RB2 owner-approved P3 collection-only handoff exception (2026-11-22)

- **Exact owner approval independently verified before any out-of-allowlist write:** repository owner `Muhammed-Fathi` posted standalone marker `APPROVE-P4-RB2-P3-HANDOFF-COLLECTION-ONLY-EXCEPTION` at [PR #41 Conversation comment #7077204700](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7077204700), timestamp `2026-11-22T09:31:39Z`. The comment author and exact body were fetched directly from GitHub; it is not inferred from chat confirmation.
- **One ninth path authorized, append-only:** `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` solely to record the current measured whole-backend `**1204 collected**` paired with the unchanged P3 suite `**443**`. No historical count or passed outcome may be rewritten; collection is not a pass count. This does not transfer RB1/#37, F2/#35, or any other exception to a different path or purpose.
- Exact candidate-head [PR CI #45006638723](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45006638723), SHA `8c5a171214264a4763e12e00c9b552ab29662c5e`: Frontend Node 22 SUCCESS; Backend Ruff lint and Ruff format SUCCESS; pytest measured **1204 collected**, with **one** failure solely in `backend/tests/p3/test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes`, because the handoff lacked `**1204 collected**`. The P3 suite count remains `443`. No evidence of a rule-engine failure in the pytest failure summary, but RB2 is not accepted. Backend Alembic/OpenAPI/secret-scan stages were not reached after pytest failed; owner Windows exact-head tests not run.
- **Exact permitted operation:** append a clearly dated, linked, collection-only note to the one P3 handoff document stating `1204 collected` / `443 P3`, CI's one collection-pairing failure, and explicitly **NOT 1204 passed**. Preserve every previous note verbatim and do not alter P3 source/tests/fixtures, Windows results, OCR outcomes, scanner, thresholds, workflows or CI logic. This approval is not permission to change any other path.
- After this append, rerun full exact-head CI and verify Ruff, Pytest, Alembic, OpenAPI and secret scan plus Node; then independent owner Windows PowerShell 5.1 exact-head `setup.ps1` + `test_all.ps1`, and independent review. PR #41 remains DRAFT and must not merge until the owner decides. P4 remains IN_REVIEW; issue #14 OPEN; `GOLD-EX-11 FAIL / NOT PROVEN` unchanged; SYNTHETIC / NOT FOR CLINICAL USE.


## P4-RB2 exact handoff-pair token follow-up (2026-11-22)

- After the owner-approved P3 collection-only note was appended, exact-final-head [PR CI #45008087818](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45008087818) on `a4919572ede141ed8f73efd094c9cdb649312982` again reported Frontend Node 22 SUCCESS and Backend Ruff lint/format SUCCESS. Pytest measured the same **1204 collected / 443 P3** and FAILED exactly one historical assertion: `test_handoff_test_count_matches_the_suite_it_describes` now requires the literal adjacent phrase `**1204 collected**, of which **443** are the P3 suite`; the current note expressed the same facts but inserted words between the tokens. No RB2 evaluator test failure appears in the failure summary. Backend Alembic/OpenAPI/secret scan skipped; independent Windows NOT RUN.
- This is a **format-only correction** to the same already owner-authorized ninth path and same collection-pairing purpose. Append one exact guard-token sentence to `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`; do not edit or delete any prior append, history, source, tests, fixtures or OCR/Windows result. No new collection count is introduced.
- Rerun full CI on the resulting exact head; require all Backend downstream stages and Frontend success, then independent owner Windows PowerShell 5.1 gate and review. PR #41 stays DRAFT / no merge; P4 IN_REVIEW, issue #14 OPEN; original `GOLD-EX-11 FAIL / NOT PROVEN` unchanged.

## P4-RB2 DR-003 owner clarification (2026-11-22)

- Repository owner `Muhammed-Fathi` posted `APPROVE-P4-RB2-DR003-NEWEST-ADMISSIBLE-SELECTED-TYPE` in [PR #41 Conversation comment #7080736185](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7080736185), `2026-11-22T14:41:49Z` (author, full body and time verified via GitHub).
- **DR-003 only:** derive evaluated types from selected admissible current observations; use the newest admissible same-patient, same-type, same-unit observation across bounded selected and historical inputs. History alone neither introduces types nor becomes selected current. Zero selected means zero candidates. Evidence and trust refer to the actual newest observation; retain the neutral template, stable ordering, pinned clock and whole-day age. Rejected, future, invalid, foreign-patient, wrong-unit and otherwise inadmissible evidence cannot determine staleness. DR-001/005 selection semantics do not change.
- This does not expand the file allowlist or authorize changes to frozen policy/GOLD, P3 source, runtime activation, persistence, RB3, RB4, phase acceptance or merge. PR #41 stays DRAFT and NOT MERGED; P4 remains IN_REVIEW; synthetic only, NOT FOR CLINICAL USE.

## P4-RB2 independent-review remediation checkpoint (2026-11-22)

- RB2-R01–R06 fixes are offline-only and require independent review. Source-fact assertions explicitly marked pending/rejected fail closed; determining whether an unverified historical fact is a superseded inactive original cannot be inferred from this DTO and any relaxation needs a separate owner decision.
- Necessary regressions measured **1249 collected** backend / **443** P3 on Linux Python 3.11.2 with hash-locked dependencies, not 1249 passed. The historical pairing guard failed; a new one-path [owner exception is requested](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7080832832), not granted. No new P3 handoff edit. Fresh exact-head Python 3.12 CI and independent Windows validation remain required.
- Historical owner Windows and remote CI evidence belongs only to starting SHA `21751e6493df938e6276335702200563adab422a`, not the modified candidate. Details are in the RB2 implementation review. PR #41 remains DRAFT, NOT MERGED; P4 IN_REVIEW, issue #14 OPEN, full P5 NOT ACCEPTED, real GOLD-EX-11 FAIL / NOT PROVEN; no RB3/RB4 or clinical use.

## P4-RB2 R07/R08 and superseding collection request (2026-11-22)

- Offline R07 fixes year-one timestamp-window overflow without changing the 90-day rule. R08 uses an explicitly controlled local Decimal context and preserves exact arithmetic or returns a typed failure, independent of caller context. R05 remains conservative and does not authorize inactive-fact inference; see the RB2 review report.
- Final local collection measured **1255 collected**, of which **443** are P3, on Python 3.11.2 with hash-locked dependencies; collection is not passed. A [superseding owner request](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7081201222) replaces the prior 1249 request. No P3 handoff edit is authorized without verifying an exact new owner decision.
- [CI #45035675614](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45035675614) failed at backend tests on Arena SHA `48f1bb58697e8e68eed609f8913d2fc8718a204b`; Ruff passed, downstream backend checks skipped, frontend passed. The user-supplied independent reviewer identified the historical 1249 pairing assertion in the actual backend log; this session could not independently retrieve the log. Fresh exact-head Python 3.12 CI, independent Windows validation and review remain required. PR #41 remains DRAFT and NOT MERGED; P4 IN_REVIEW, issue #14 OPEN, full P5 NOT ACCEPTED, GOLD-EX-11 FAIL / NOT PROVEN.

## P4-RB2 owner-authorized 1255 collection-only handoff (2026-11-22)

- Repository owner `Muhammed-Fathi` posted the exact standalone `APPROVE-P4-RB2-P3-HANDOFF-1255-COLLECTION-ONLY` at [PR #41 comment #7083447073](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7083447073), `2026-11-22T18:14:09Z`; author, body and timestamp were independently fetched from GitHub. The [superseding request #7081201222](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7081201222) limits this exception to an append-only collection-only note in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`; it does not authorize P3 source/tests/fixtures, scanner, CI, historical evidence, runtime, merge or phase acceptance changes.
- Before the append, on unchanged Arena test tree `58eb9992fd0a9e33876b462c0c76eaa3d5c84908`, Linux Python 3.11.2 with hash-locked development dependencies measured **1255 collected**, of which **443** are the P3 suite. Collection is not a pass count. Actual commands and exit codes are in the RB2 implementation review; Python 3.12 and Windows acceptance remain separate gates.
- The independent reviewer supplied the actual [CI #45038253453](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45038253453) backend log result: the historical handoff guard failed because `**1255 collected**` was absent. This session confirmed job metadata but could not fetch the log itself. P4 remains IN_REVIEW, issue #14 OPEN, full P5 NOT ACCEPTED, original GOLD-EX-11 FAIL / NOT PROVEN. PR #41 remains DRAFT / NOT MERGED.

## P4-RB2 owner-acceptance historical checkpoint and P4-RB3 design-only branch (2026-11-22)

- **RB2 accepted and owner-merged (independently verified on 2026-11-22 via authenticated GitHub reads):** owner `Muhammed-Fathi` posted `OWNER-ACCEPT-P4-RB2` at [PR #41 comment #7087501521](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087501521), `2026-11-22T23:20:34Z`, at the exact reviewed SHA `8dd79ac0aa8fc626dcc9b4b7ecf3de3a8aedc888`; permanent independent validation evidence is [comment #7087467476](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/41#issuecomment-7087467476), `2026-11-22T23:17:52Z`. PR #41 was owner-merged at `2026-11-22T23:20:55Z` to `main@7190b25e2c62de3a56e369f12bf6d9fbecd8982e`; the merged-main tree `2b083757d04cc202ca64523d25c8e87dcc4cd3fd` is byte-identical to the accepted candidate tree (verified empty diff; merge parents `eaab808b…` + `8dd79ac0…`). Post-merge main [CI #45082770648](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45082770648) COMPLETED **SUCCESS** on the exact merge SHA with all mandatory gates green (Backend Python 3.12: Ruff lint/format, full pytest, Alembic smoke lifecycle, OpenAPI check, secret/artefact scan; Frontend Node 22: ESLint, typecheck, Vitest, production build). `origin/main` remains at `7190b25e…`. The acceptance explicitly does **not** authorize runtime rule activation, persistence, clinical use, RB3/RB4 implementation or P4/P5 acceptance; RB2 stays an offline-only accepted evaluator.
- **P4-RB3 design-only branch opened from the exact verified main (THIS checkpoint's PR):** new [P4-RB3 durable run-bound persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) — **PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED**. It covers the internal authenticated write boundary, the exact `BEGIN IMMEDIATE` write-transaction architecture with locked F1/F2/RB1 revalidation and honest DB-vs-filesystem non-atomicity, the RB2→RB3 evaluator-boundary alternatives (recommended: unchanged RB2 pure evaluator as computation core with an explicitly documented label bridge plus mandatory independent stored-lineage proof), the additive `0008` `review_item`/`evidence_link` schema against DATA_DICTIONARY §§2.9–2.10 (NOT NULL `workflow_run` FK, ON DELETE RESTRICT, closed rule/trust enums, `demo_only=1`, UNIQUE `(workflow_run_id, dedupe_key)`), six-rule evidence-link mapping with the run-bound DR-006 unreachability finding, idempotency/replay/atomicity rules, migration safety from the actual head `0007_p5_run_gate` with the exact legacy guard paths (E1–E6) requiring fresh standalone owner exceptions, the exact future implementation allowlist (N1–N12 normal; E1–E6 exceptional; no blanket directory authorization), and a 44-case adversarial acceptance matrix. RB4 run-backed GOLD acceptance remains separate and unexecuted.
- **Owner decisions requested (no approval assumed):** D-RB3-01..07 as tabulated in the design, with the exact proposed ratification marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` to be posted **in the design PR's Conversation** only if all decisions and the allowlist split are accepted. The marker would authorize only one future separate RB3 implementation PR after this docs-only PR is owner-reviewed/merged and exact merged-main CI SUCCESS is independently verified; it would not authorize full P4 acceptance, RB4, graph/LLM/API/task/notification activation, review-item state-transition writers, clinical use or any agent merge.
- **Branch-name note (honest deviation):** the task proposes `docs/p4-rb3-durable-persistence-design`; the Arena session model pins this work to the session branch `arena/91facff6-ai-doctor-followup-agent`, which is based on the exact verified main `7190b25e…` and carries only the three docs-only paths (new design + append-only PHASE_4_REPORT + append-only this roadmap). No contract, application source, test, fixture, model, migration, dependency, CI or scanner file is modified. Rollback = close the draft PR unmerged; zero database/source impact.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design Revision 2 — independent review corrections checkpoint (2026-11-22)

- **Status unchanged: DESIGN ONLY / DRAFT PR #42 / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED.** The independent reviewer verified the successful RB2 merged-main CI, both successful Revision-1 design CI runs on head `684cf5e05695c2029ccd1c78d60076f6878ed18e`, the exact base/head relationship and the three-file documentation-only scope, then returned six blocking findings (RB3-D01..RB3-D06) plus reviewer-preferred positions on D-RB3-01..07. Reviewer recommendations are **not** owner authorization; no implementation path is authorized and none was begun. The corrected design stays in [P4-RB3 durable persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) (Revision 2, with a correction log at §0.1).
- **All six findings were resolved from actual merged source, read at line level in this session:** F2's fingerprint covers projected current observations only (`backend/app/services/p5_evidence_bridge.py:378-389`, no `created_at`) while F1's covers every column of every patient observation (`backend/app/services/p5_run_gate.py:531-562`, `:736`); RB1 reuses F2's cached exclusion ids (`backend/app/services/p4_run_bound_preview.py:152`, `:190-194`); the RB1 preview DTO exposes no version fields (`backend/app/schemas/p4_run_bound_preview.py:33-57`); `derive_audit_key` includes `request_id` and `append_audit_event` returns an existing row without comparing content (`backend/app/services/audit.py:65-74`, `:124-128`), while `record_denial` commits (`:170-190`); `ActorType` has no doctor member; RB2 admits only `lineage_status ∈ {unavailable, fixture_asserted}` and emits a `verified_lineage_unavailable` exclusion for stored-proved rows labelled `unavailable` (`backend/app/services/p4_rb2_offline_rules.py:221-225`, `:316-321`); house precedents for immutability triggers, conditional cross-table triggers, `length()` CHECKs, partial unique indexes, ORM/migration parity and downgrade refusal (`0006_p5_run_foundation.py:31`, `:136`, `:156-184`; `0003_p3_documents.py:263`, `:267-277`; `0002_p2_patient_domain.py:289`; `backend/app/db/models.py:278-287`; `backend/tests/p2/test_p2_migration.py:314-331`).
- **Material design changes:** fresh full stored-history reconstruction and fresh exclusion derivation under the committing lock, with cached exclusion ids demoted to drift cross-checks; a new complete canonical `rb3-full-input-1.0.0` input fingerprint plus an output identity, and an explicit fingerprint-authority scope table; a proposed additive immutable `review_evaluation` completion record (one row per run) with all thirteen replay cases failing closed on typed `E_IDEMPOTENCY_CONFLICT` and exact replay performing zero writes; a corrected field-to-source mapping replacing the invalid `preview.gate_version` expression; a corrected T1 transaction precondition; full UPDATE/DELETE immutability with an exact 14-trigger inventory and vocabulary reserved but not writable; `ActorType.USER` audit with explicit audit-row content validation and no committed denial audit; and corrected R03/R04/R07/R08 semantics.
- **A Revision-1 claim is withdrawn:** run-bound DR-006 is **not** proved structurally unreachable. F1's VI-006 loop covers selected documents only (`backend/app/services/p5_run_gate.py:608`) and skips non-conforming fact shapes (`:617-628`), comparing on UTC calendar day (`backend/app/services/documents/issues.py:243-256`), while DR-006 compares all eligible rows of a type on exact `measured_at` (`backend/app/services/p4_rb2_offline_rules.py:425`). `GOLD-D.expected.json`'s zero conflicts is a fixture property, not an invariant. DR-006 handling becomes explicit owner decision D-RB3-08.
- **Owner decisions requested (no approval assumed):** D-RB3-01..09 plus sub-decisions 05a–05d, and unresolved conflicts C-RB3-01..C-RB3-06 stated rather than guessed. The bounded marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` is proposed unchanged in form: it would authorize only one future separate RB3 implementation PR confined to N1–N13 after this docs-only PR is owner-merged with independently verified exact merged-main CI SUCCESS, with E1–E6 each still needing its own fresh marker (E5 stating the actual future measured backend/P3 pairing, never a reusable generic permission). It would not authorize full P4 acceptance, RB4 GOLD acceptance, runtime activation beyond the bounded demo persistence service, graph/LLM/API/UI/task/notification/approval/summary activity, review-item state-transition writers, clinical use, issue #14 closure or any agent merge. **The agent posts no ratification marker and claims no acceptance.**
- **Scope of this remediation:** the same three documentation paths only — the unratified design corrected in place, plus append-only checkpoints in `docs/phase-reports/PHASE_4_REPORT.md` and this roadmap (both verified to remove zero lines, all historical evidence preserved). No source, model, migration, test, contract, fixture, policy, dependency, CI or scanner file is edited. Committed normally to the existing PR #42 branch; no second PR; no history rewrite. PR #42 stays **DRAFT / NOT MERGED**.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design Revision 3 — reviewer corrections checkpoint (2026-11-22)

- **Status unchanged: DESIGN ONLY / DRAFT PR #42 / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED / NO IMPLEMENTATION STARTED.** Revision 2 passed both exact-head CI workflows on `3d749648c223eaccf1f42f4c57221df5dd05700d`, and an independent reviewer then found ten further concrete design defects (RB3-R3-01..RB3-R3-10) plus additional schema-precision questions. Reviewer findings are **not** owner authorization. The corrected design stays in [P4-RB3 durable persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) (Revision 3; correction log §0.2, Revision 2 log retained at §0.1).
- **Two Revision-2 proposals were provably defective and are corrected at source level:** the `length(rule_id) = 7` CHECK (every valid `DR-00n` id is **six** characters, so it would have blocked every legitimate insert) and the T15 insertion order (`review_evaluation.audit_event_id` is a NOT NULL immediate FK, and `append_audit_event` adds and flushes its row internally at `backend/app/services/audit.py:130-146`, so the completion row cannot precede the audit row). T15 is now pre-generate `evaluation_id` → items → links → audit (`subject_id=evaluation_id`, safe because `audit_event.subject_id` has no FK) → validate the returned row → completion row → single commit; a deferred-FK alternative is evaluated and rejected.
- **Two Revision-2 claims are withdrawn as unsupported:** (1) T8's unconditional call to `compare_explicit_current_with_history`, which requires `1 <= len(current) <= 6` (`backend/app/services/p4_explicit_history.py:22-23`) — now split into T8a (empty selection: helper not called, RB1's `no_current_selected` semantics asserted) and T8b; (2) the DR-006 reachability fixture using two **non-selected** source documents, which `source_reason` provably excludes (`backend/app/services/p5_evidence_bridge.py:187-193`). DR-006 reachability on an F1-PROCEED run is now declared **UNPROVEN in both directions** — the mechanism divergence is verified at line level (F1's VI-006 covers selected documents only at `backend/app/services/p5_run_gate.py:608` and skips non-conforming shapes at `:617-628` on calendar-day comparison, while F2's `source_reason` has no `report_date` requirement), but constructibility depends on extraction-time issue generation and F1 preflight that this design has not fully traced. **No fixture is invented**; conflict C-RB3-08 records the implementation-PR proof obligation.
- **Three specifications were incomplete and are now complete:** T6 reproduces the **entire** F2 `source_reason` eligibility contract from stored evidence via public interfaces only, enumerating every exclusion code (`verified_lineage_unavailable`, `verified_mapping_unproven`, `stored_trust_source_mismatch`, `validation_rejected`, `unit_mismatch`, `missing_timestamp`, `future_timestamp`, `missing_created_at`), with cached exclusions as cross-checks only; `document_span` links now require the stored fact's exact §5-resolvable span (`document:<id>` → verified `test_name` span, `fact:<id>` → verified `value` span) with a missing or unresolvable span denying the whole invocation and no NULL-span substitute, reconciling `DATA_DICTIONARY.md` §2.10 with `EXTRACTION_PROVENANCE.md` §5 **without any contract amendment**; and DR-006's evidence mapping is corrected to all **six** references (two observations plus two `test_name` and two `value` document spans), which also corrects the structural maximum from 96 to **72** links (12 items × 6, derived from all six `_flag` call sites).
- **Provenance honesty is now per item:** an additive `review_item.provenance_status` column stores the evaluator's literal verbatim and is included in `output_identity_sha256` (recommended Option A, new owner decision D-RB3-10), and Revision 2's over-claiming global `lineage_state` is replaced by `lineage_label_policy`, which records only which ratified boundary option governed the labels and must never imply that every observation in a mixed input has verified document lineage. The six actual `reason_code` literals are transcribed now (`missing_baseline`, `measurement_stale`, `change_exceeds_demo_parameter`, `verified_source_conflict`, `duplicate_or_out_of_order`, `implausible_value`) and **DR-001 is corrected to mean a missing baseline**, not "no current measurement". Phase 1's P2 is corrected to state that F2 always rolls back (`backend/app/services/p5_evidence_bridge.py:470-473`), and E6 is corrected to note that `inspect_current_run_gate_locked` already has two callers (F2 and RB1 at `backend/app/services/p4_run_bound_preview.py:101`), making RB3 an additional third caller; E6 remains separately authorized and docstring-only.
- **Precision additions:** `review_evaluation.policy_reference_sha256` structurally pinned to the exact R3-A digest (sub-decision D-RB3-05e); G14 strengthened to require the referenced audit row to exist and counts to match real rows; the NULL-distinctness gap shown to **close** once spans are mandatory, so the partial unique indexes suffice and G11 is honestly downgraded to defence-in-depth; the one-evaluation-per-run invariant re-confirmed for zero-item and changed-input cases.
- **Owner decisions requested (no approval assumed):** D-RB3-01..D-RB3-10 including sub-decisions 05a–05f, with unresolved conflicts C-RB3-01..C-RB3-05, C-RB3-07 and C-RB3-08 stated rather than guessed. C-RB3-06 is closed by transcription. The A2 transport-label conflict **C-RB3-01 remains explicitly unratified**. The bounded marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` is unchanged in form and would still authorize only one future separate RB3 implementation PR confined to N1–N13 after this docs-only PR is owner-merged with independently verified exact merged-main CI SUCCESS, with E1–E6 each needing its own fresh marker (E5 stating the actual future measured backend/P3 pairing, never a reusable generic permission). It would not authorize full P4 acceptance, RB4 GOLD acceptance, runtime activation beyond the bounded demo persistence service, graph/LLM/API/UI/task/notification/approval/summary activity, review-item state-transition writers, clinical use, issue #14 closure or any agent merge. **The agent posts no ratification marker and claims no acceptance.**
- **Revised acceptance matrix RB3-01..RB3-81**, with RB3-19/21/66 rewritten and RB3-67..RB3-81 added for the six valid rule ids, the invalid seven-character assumption, the audit FK order, the audit helper returning an existing event, the empty selected-current path end-to-end, `source_reason` equivalence branch by branch, non-selected verified-document exclusion, selected documents failing only F1's `report_date` shape gate, all six DR-006 evidence keys, exact stored spans, missing/unresolvable spans, per-item provenance persistence, the six exact reason codes and the corrected 72-link maximum. **No matrix result is claimed as executed.**
- **Scope of this remediation:** the same three documentation paths only — the unratified design corrected in place plus append-only checkpoints in `docs/phase-reports/PHASE_4_REPORT.md` and this roadmap (both verified to remove zero lines, all historical evidence preserved). No application source, model, migration, test, fixture, contract, policy, dependency, CI or scanner change; no contract edited, and the one possible §2.10 amendment (`fact_id`) is proposed as an owner decision instead. Committed normally to the existing PR #42 branch; no second PR; no history rewrite. PR #42 stays **DRAFT / OPEN / NOT MERGED**.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design Revision 4 — bounded design closure checkpoint (2026-11-22)

- **Status unchanged: DESIGN ONLY / DRAFT PR #42 / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED / NO IMPLEMENTATION STARTED.** The independent reviewer verified Revision 3 (exact three-file documentation scope, unchanged main `7190b25e2c62de3a56e369f12bf6d9fbecd8982e`, both successful exact-head CI runs on `e717e9c31c17e3dda04b0f90a052343890ab96fe`) and then issued a **bounded design-closure** correction task — not another unrestricted redesign. Reviewer findings RB3-R4-01..RB3-R4-06 and a reviewer-preferred decision package were resolved from line-level re-inspection; **three further defects were found while verifying them** (R4-S1 audit key derived from a freshly generated row id, R4-S2 the loader's `lineage_exclusions` are consumed by neither F2 nor RB1, R4-S3 no writable `document_span` path remains once DR-006 is prohibited). **Reviewer preferences are not owner authorization.** Corrected design: [P4-RB3 durable persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) (Revision 4; correction log §0.3, earlier logs retained at §0.1/§0.2).
- **Actual ORM field compatibility (RB3-R4-01):** `Document` has **`uploaded_at`** and no `created_at`; `FactVerification` has `decision`, `decided_at`, `source_image_compared`, `confirmed_value/unit`, `previous_value`, `new_value/unit`, `verified_by_user_id` and `reason` — **no `status`, `verified_at` or `created_at`**. The canonical payload was rebuilt against the real models, mirroring F1's exact field lists for the run, document, fact, decision and observation snapshots plus a new manifest member, with a field-to-source table classifying each member as persisted or derived. No attribute is invented and no ORM class is modified; free text, document text, bytes, user identity/credential columns and process settings are excluded with reasons and remain bound through the pinned F1 digest.
- **Exact F2 exclusion precedence and layered exclusions (RB3-R4-02, R4-S2):** F2 computes `source_reason` **first**, calls `admissibility_reason` only when it returned `None`, maps `MonitoringInputError` to **`malformed_history`**, and emits **at most one** reason per historical observation; its selected-current loop never excludes but raises instead. T6 now reproduces that precedence exactly and keeps **three separate layers** — L1 F2-compatible reconstruction, L2 the evaluator's own exclusions verbatim, L3 the merged receipt view with canonical deduplication on `(observation_id, reason_code)`. **L2 is never compared against F2's cached `history_exclusions`.** The loader's `lineage_exclusions` are an **L0 diagnostic layer** only (never merged, never compared), since no accepted consumer reads them. The upstream 5-minute future-skew allowance (`MAX_FUTURE_SKEW_MINUTES = 5`) versus RB2's strict pinned-clock exclusion is handled conservatively: such rows are **not** pre-filtered, are fed to the evaluator as F2/RB1 would, and surface as an L2 `future_timestamp` exclusion — neither accepted contract is loosened.
- **Completed evaluations are now structurally sealed (RB3-R4-03, C-RB3-09):** an isolated temporary in-memory SQLite probe (run in `/tmp`, editing no repository file and creating no implementation artifact, and **not** an implementation test) showed that under the repository's actual configuration — `backend/app/db/session.py:31` sets only `PRAGMA foreign_keys=ON`, so `recursive_triggers` stays **0** — `INSERT OR REPLACE`/`REPLACE INTO` **silently replaced** a row while the `BEFORE DELETE` immutability trigger never fired. Three `BEFORE INSERT` seals are added (**G15** review_item, **G16** evidence_link, **G17** review_evaluation), taking the inventory to **17 triggers**; probes confirmed they block every late insert and replacement path (including upsert `DO NOTHING`) while leaving the initial items → links → audit → completion sequence and other runs unaffected. `PRAGMA recursive_triggers=ON` is **rejected** (it would edit accepted P2 source outside the allowlist and change global trigger semantics). G14 is rewritten with its complete scope — run/patient/doctor/policy match, stored PROCEED gate identity and fingerprint match, audit subject/run/actor match, actual item/link count match, no orphan or duplicate completion — and the design now states explicitly which invariants are structural and which remain application-layer only.
- **Canonical identities in a consistent sequence (RB3-R4-04):** the transaction is renumbered **T1–T18** so the input identity is computed **after** the typed evaluator input is constructed and the output identity **after** evidence resolution, eliminating Revision 3's hashing of not-yet-existing `resolved_spans` (moved to the output identity as `span_proofs`). Every timestamp column is hashed as its **raw stored string** or `null`, never through `parse_utc`/`format_utc`, so malformed or absent historical `created_at` cannot raise during canonicalization and R03 behaviour is preserved. Fingerprint authority is corrected: F2 does not directly serialize every historical observation field, but it **embeds the F1 digest** in its own payload, so F1-captured changes propagate indirectly into F2 — no claim is made that F2's digest is unchanged when the embedded F1 digest changes. RB3's own full-input identity remains necessary to bind derived eligibility, exact evaluator inputs and completed output semantics.
- **R07/R08 across upstream comparisons (RB3-R4-05, C-RB3-10):** the frozen comparator subtracts a `timedelta` from a measurement stamp (`backend/app/services/p4_explicit_history.py:132`) with **no `OverflowError` handler**, and both F2 (365-day) and RB1 (90-day) call it catching only `MonitoringInputError`, so an `OverflowError` escapes F2's public wrapper too; probes confirmed year-one stamps overflow and that the earliest safe stamp for a 365-day lookback is `0002-01-01T00:00:00Z`. RB2 is overflow-safe because it compares datetime **differences**, so **R07 is an RB2 pure-function guarantee that does not reach earlier code**, and no claim is made that a year-one measurement necessarily reaches RB2. The design now separates RB2 guarantees, RB3's end-to-end supported domain (new §4.7) and upstream adapter limitations; pins an RB3-owned `decimal.localcontext` **equal to the CPython default** (`prec=28`, half-even, default traps) around T5–T16 — explicitly **not** RB2's `Inexact`-trapping context, which a probe showed would raise upstream — with automatic restoration on success and failure; and enforces a conservative supported domain with a typed `409 E_VALIDATION` reason `measurement_timestamp_out_of_supported_range` and zero writes, plus an `OverflowError` → typed-denial mapping at P2/P3. The narrowly scoped future owner exception (widening the upstream helper's arithmetic) is identified and **not** taken. No accepted source or test is changed and no RB2 regression test is weakened.
- **Audit, zero-selection and exclusion semantics (RB3-R4-06, R4-S1, R4-S3):** `append_audit_event` requires a `request_id` with no default and `Principal` has none, so §8.4 specifies a **server-derived bounded** audit request identity from immutable persisted identifiers only (64 hex characters, within `MAX_REQUEST_ID_LENGTH`), uses the existing `principal.actor_type` property, invents no `Principal` attribute and accepts no client token; **R4-S1** additionally corrects the audit subject from a freshly generated `evaluation_id` to `subject_type='workflow_run'`/`subject_id=run.id`, as both `derive_audit_key`'s documented contract and `AGENTS.md` §3.2 require, which also makes orphan-audit detection deterministic — an existing review-persistence audit with no completion record is now detected **even with zero items** and never silently adopted. All six rules sit behind `if not selected: continue`, so Revision 3's residual "DR-003/DR-009-only" wording is removed: a successful zero-selection evaluation has **exactly zero items and zero links**. `active_fact_verification_statuses` is derived exactly from F1's `active`-fact computation, so an unsuperseded `pending`/`rejected` original stays in the tuple and R05 is never bypassed. `exclusion_count` is **derived** as `CHECK BETWEEN 0 AND 200` (100 bounded patient rows × at most 2 distinct reasons per observation across the disjoint layers), counted after canonical deduplication, with no truncation. Because Alt A2 is the only proposed option, `provenance_status` and `lineage_label_policy` become **single-value** CHECKs and RB3's own stored-lineage proof is preserved separately in a second additive column `review_item.stored_lineage_proved`, both included in the output identity. Replay validation now covers completion metadata, semantic rows, links and audit identity **and** content, with a deterministic eight-step conflict precedence; a matching audit FK or dedupe key is explicitly insufficient.
- **Conservative DR-006 scope (D-RB3-08 option (ii), reviewer-preferred):** all six RB2 rules unchanged; if DR-006 is emitted the **entire** invocation is denied with `409 E_VALIDATION` reason `dr006_persistence_not_authorized` — never a silently dropped item, never a persisted subset. DR-006 is **not** described as structurally unreachable and its reachability through genuine F1/F2 evidence remains **unproven in both directions**. The prohibition is recorded as a **deliberate proposed scope reduction** (a genuine verified-source conflict persists no items at all) with **N13 included** in the proposed allowlist. The six-key evidence mapping and span machinery are **preserved as a future extension design** (§7.2a), not an authorized writable path — which also means no `document_span` link is writable now (R4-S3), so the authorized structural maximum is **12 × 2 = 24** links rather than 72, with G8 widened accordingly and `ux_evidence_link_span` honestly labelled inert. A unit-level boundary test may prove the whole-invocation denial but **does not** prove end-to-end reachability, and **no invented F1-PROCEED fixture is required** to close this conservative slice.
- **Final package, allowlist and marker semantics:** §12 separates decisions requiring owner ratification (D-RB3-01..D-RB3-10 with sub-decisions 05a–05f) from pure transcription/consistency corrections and from explicitly deferred future capabilities; no conditional DR-006 persistence authorization remains in the planned implementation scope. The N1–N13 / E1–E6 split is retained with only genuinely required destination updates, and **N10 is resolved to the exact filename `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md`**. E1–E4 and E6 each require a separately verified owner marker before editing; E5 requires a fresh exact measured backend/P3 collection-pair authorization; there is no generic permission to change historical tests, scanner policy, fixtures or contracts, and `backend/app/db/session.py` is explicitly outside the allowlist. §12.3 binds `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` to **one exact reviewed design SHA** and **one bounded future implementation PR**, posted as in the accepted RB2 precedent (marker on the PR conversation at the exact reviewed head, SHA stated), since a document cannot embed its own commit SHA. **The agent posts no marker and claims no acceptance.**
- **Matrix RB3-01..RB3-99**, preserving existing cases, correcting contradictory expectations and relabelling RB3-75..77 as future-extension requirements, with RB3-82..RB3-99 added for ORM field compatibility, exclusion precedence and `malformed_history`, future-skew boundaries, L0 diagnostics, no post-completion insertion, SQL replacement-path protection, complete G14 scope and audit consistency, input-identity construction order, malformed `created_at` canonicalization, upstream Decimal/timestamp boundaries, orphan audit with zero items, exact zero-selection results, active versus superseded facts, exclusion-count bounds and whole-invocation DR-006 denial. **No matrix result is claimed as executed; no unexecuted test is reported as PASS.** The `/tmp` probes are disclosed as design-level feasibility evidence, clearly distinguished from implementation tests.
- **Remaining genuine blockers: none for this conservative slice.** The design is internally consistent, every cited field and helper is verified to exist, and DR-006 reachability no longer blocks it. Outstanding items are **owner ratification only** (D-RB3-01..D-RB3-10; C-RB3-01..C-RB3-05, C-RB3-07..C-RB3-11, with C-RB3-01 still explicitly unratified and C-RB3-06 closed) plus the separately authorized E1–E6 markers before any guard or docstring edit.
- **Scope of this remediation:** the same three documentation paths only — the unratified design corrected in place plus append-only checkpoints in `docs/phase-reports/PHASE_4_REPORT.md` and this roadmap (both verified to remove zero lines, all historical evidence preserved). No source, model, migration, test, fixture, contract, policy, dependency, CI or scanner edit; no contract amended. Committed normally to the existing PR #42 branch; no second PR; no history rewrite. PR #42 stays **DRAFT / OPEN / NOT MERGED**.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design Revision 5 — final integrity and audit closure checkpoint (2026-11-22)

- **Status unchanged: DESIGN ONLY / DRAFT PR #42 / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED / NO IMPLEMENTATION STARTED.** Revision 4 was independently reviewed as materially improved; the reviewer issued three bounded findings (**RB3-R5-01…RB3-R5-03**) to close before recommending owner ratification. The design was **not** restarted and **every accepted Revision-4 decision is preserved**: Alt A2, the single committing transaction, the exact pinned synthetic clock and policy, the T1–T18 sequence, the L0/L1/L2/L3 exclusion separation, RB2 unchanged, bounded R07/R08 upstream limitations, zero selection meaning zero items and zero links, the conservative DR-006 whole-invocation denial, the authorized maximum of 24 evidence links with no `document_span` writes, the exact N1–N13 / E1–E6 authorization separation, one immutable completion per run, and exact replay meaning zero writes. Corrected design: [P4-RB3 durable persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) (Revision 5; new log §0.5, earlier logs retained at §0.1–§0.4).
- **RB3-R5-01 — complete replacement protection (trigger inventory 17 → 25).** Revision 4's G15/G16/G17 keyed only on `NEW.workflow_run_id`, so they could not see an attempt to overwrite an **existing** row. Measured with an isolated in-memory probe under the repository's real configuration (`backend/app/db/session.py:23-33` sets only `PRAGMA foreign_keys=ON`; `recursive_triggers` asserted **0**): with G1–G17 alone, `INSERT OR REPLACE`/`REPLACE INTO` **silently succeeded** for a same-run primary-key replacement **before** completion, a same-run `(workflow_run_id, dedupe_key)` replacement before completion, a same-run `(workflow_run_id, display_order)` replacement before completion, and a **cross-run** replacement of a completed `review_item`, `evidence_link` and `review_evaluation`. The cross-run item case was measurably destructive — the sealed completion row still recorded `item_count = 1` while its run held **0** items, making the durable record **false**. **Eight new `BEFORE INSERT` identity guards G18–G25** now protect every unique identity of every RB3 table independently of run completion (item PK / dedupe / display order; link PK / effective observation identity / prospective span identity; evaluation PK / unique run), with exact migration-ready SQL in the new §6.4b, while G15–G17 are retained verbatim as the run seals. The count was **updated rather than preserved artificially**; a combined single guard per table was evaluated and rejected because it cannot report which identity conflicted. Probe-verified as preserved: the valid initial T16 sequence, a second independent run's own full persistence with the sealed run's rows byte-identical and its counts unchanged, `recursive_triggers = 0`, no `session.py` edit, no accepted P2 behaviour change, and post-rollback retry. `PRAGMA recursive_triggers=ON` remains rejected and is now shown to be insufficient alone for cross-run replacement.
- **Three further SQLite behaviours measured and made normative (§6.6 items 1–6, §6.6a).** A UNIQUE index is satisfied by deleting the conflicting row, so it is not immutability protection. **FKs give only partial, incidental protection and are never relied on**: a replacement that changed a parent's primary key while a child link referenced it failed with `FOREIGN KEY constraint failed`, but a **primary-key-preserving** overwrite of that same parent **succeeded silently** (the child's reference is satisfied again at statement end), and linkless items, links and completion rows have no child references at all. A trigger's `RAISE(ABORT, …)` is **not** suppressed by an outer `INSERT OR IGNORE`. With several matching `BEFORE INSERT` triggers SQLite reports from the **most-recently-created** one, so tests must assert rejection and unchanged rows — never a specific message — for multi-conflict statements. Partial-index guards mirror their index `WHERE` predicate and use `=` rather than `IS`, so they neither over-block other kinds nor tighten SQLite's NULL-distinct UNIQUE semantics. §6.6a fixes migration trigger creation order (tables and indexes first, then all 25 triggers).
- **RB3-R5-02 — the 500-character audit detail contract.** `SAFE_DETAIL_MAX: int = 500` (`backend/app/services/audit.py:31`), `safe_detail()` joins with `"; "`, collapses whitespace and **truncates** (`:77-87`), column `String(500)` (`backend/app/db/models.py:412`). The Revision-4 thirteen-fragment set measured **529** characters at the permitted maximum counts and **525** with single-digit counts, so the stored value was truncated and **`exclusions` and `demo_only` were lost**, making §8.2's own audit-content validation unsatisfiable. Corrected to an exact **nine-key** set in fixed order with unique whitespace-free keys — `fingerprint_version`, `evaluation_id`, `input`, `output`, `lineage_label_policy`, `dr006_policy`, `items`, `links`, `exclusions` — measuring **346** at the domain maximum, **342** at the minimum and **346** worst case over the entire permitted domain (`items 0..12 × links 0..24 × exclusions 0..200`), leaving **154** characters of headroom so **no invocation depends on truncation**, including zero-item and maximum-exclusion evaluations. The four removed fragments are redundant with the sealed immutable `review_evaluation` row that G14 cross-checks and §8.2 (1) validates field by field. Everything §8.2 requires from the audit row is preserved — `evaluation_id`, both semantic identity digests, the fingerprint version, the lineage-label policy, the DR-006 policy and all three counts — so **audit validation is not weakened**; it is strengthened, because the removed values now come from a sealed structural row rather than a truncated string. **The existing helper and its 500-character contract are unchanged.** The design adds the exact deterministic assertions `len(composed_safe_detail) <= SAFE_DETAIL_MAX`, `composed == pre-truncation collapsed value` and parsed-key-sequence equality, plus a required round-trip validation after persistence and during replay.
- **RB3-R5-03 — G14 audit completeness.** Revision 4's G14 compared six audit fields but **not** `event_type` or `patient_id`, although §8.2 (5) expects both; measured, it **accepted** a completion row referencing an audit row with a wrong `event_type` and, separately, a wrong `patient_id`. G14 condition 3 now makes **eight** structural comparisons, adding `event_type = 'workflow.review.persisted'` and `patient_id = NEW.patient_id`; each mismatch was measured to be rejected independently with nothing persisted, a fully consistent row is still accepted (no over-blocking), and all six earlier comparisons still reject independently. §6.4a's structural-versus-application-layer split moves the audit `event_type`/`patient_id` to **structural** and keeps `safe_detail` content verification as a separate additional safeguard whose length bound is now guaranteed by construction. RB3-91 and RB3-92 updated as required.
- **Document-integrity self-audit.** A structural audit of the design itself (heading sequence §0–§14, subsection continuity, GFM-accurate cell counts for every table, defined-versus-referenced inventories for `D-RB3-*`, `C-RB3-*`, G1–G25, N1–N13, E1–E6, T1–T18 and RB3-01…RB3-117) found and fixed four GFM table-cell defects caused by literal `|` characters inside inline code spans, one stale trigger count, and **one decision row (D-RB3-07) silently lost during the Revision-4 in-place rewrite** — restored verbatim with the bounded audit-detail set folded into its question and alternatives. Disclosed rather than quietly repaired: Revision 4's completeness claim was wrong on that row.
- **Matrix RB3-01…RB3-117**, preserving every existing case, updating RB3-65/90/91/92 and adding RB3-100…RB3-117 for the eight specified adversarial replacement cases, firing-order independence, partial-index predicate mirroring, the exact 25-name trigger inventory with `recursive_triggers = 0` asserted, the exact length assertion across the whole count domain, round-trip audit validation, zero-item and maximum-exclusion invocations, a regression guard against reintroducing the thirteen-fragment set, and the two G14 field mismatches tested independently plus the no-over-blocking acceptance case. **No matrix case is claimed as executed; no unexecuted test is reported as PASS.** §11 now states the required three-way distinction explicitly: verified source facts, design-level feasibility probes (five throwaway in-memory probes across Revisions 4–5, which edited no repository file and produced no implementation artifact), and unexecuted future implementation tests.
- **Derived counts updated where the guard set changed them:** N4 and N6 name **25** triggers, §9.1 creates and drops **25**, §9.2's E4 delta asserts **all 25 trigger names**, RB3-54…57 assert **25**, C-RB3-09's recommendation now names both guard layers, and §12.1(b) records the Revision-5 items as transcription/consistency corrections required by real source constraints. **No decision recommendation changed and no marker was posted.**
- **Remaining genuine blockers: none for this conservative slice** — outstanding items are **owner ratification only** (D-RB3-01…D-RB3-10 with sub-decisions 05a–05f; C-RB3-01…C-RB3-05 and C-RB3-07…C-RB3-11, C-RB3-01 still explicitly unratified, C-RB3-06 closed), plus the separately authorized E1–E6 markers before any guard or docstring edit.
- **Scope of this remediation:** the same three documentation paths only — the unratified design corrected in place plus append-only checkpoints in `docs/phase-reports/PHASE_4_REPORT.md` (new §33) and this roadmap, both verified to remove zero lines with all historical evidence preserved. No source, model, migration, test, fixture, contract, policy, dependency, CI or scanner edit; no contract amended; no pragma changed. Committed normally to the existing PR #42 branch; no second PR; no history rewrite; no force push. PR #42 stays **DRAFT / OPEN / NOT MERGED**.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design Revision 6 — hidden-`rowid` closure and two precision corrections checkpoint (2026-11-22)

- **Status unchanged: DESIGN ONLY / DRAFT PR #42 / PROPOSAL / NOT RATIFIED / NO RB3 CODE AUTHORIZED / NO IMPLEMENTATION STARTED.** The independent reviewer verified all three Revision-5 corrections against the actual design and **independently reproduced the nine-key 346-character audit-detail length**; those three corrections are **preserved unchanged**. Three new bounded findings (**RB3-R6-01…RB3-R6-03**) were issued and resolved inside the existing design; the architecture was neither restarted nor expanded. Starting HEAD `2ce8710d…`, base `7190b25e…`.
- **RB3-R6-01 — the hidden SQLite `rowid` replacement gap is real, and wider than reported.** Measured with the complete Revision-5 guard set (G1–G25) under the repository's real configuration (`db/session.py:23-33` sets only `PRAGMA foreign_keys=ON`; `recursive_triggers` **0**): an explicit `INSERT OR REPLACE` targeting the hidden `rowid` with different declared identities **succeeds** — run A left with **0** items, run B with **1**, run A's sealed completion row still recording `item_count=1`, i.e. a **false** durable record; the identity is reachable as `rowid`, `_rowid_` **and** `oid`; a completed run's `evidence_link` can be moved to another run (recorded 1, actual **0**); and a sealed `review_evaluation` can be replaced wholesale, orphaning its items. FK protection was again measured to be **incidental only**.
- **Correction: all three new RB3 tables are declared `WITHOUT ROWID`** — `review_item`, `evidence_link`, `review_evaluation` (new §6.4c, owner decision **D-RB3-05g**, conflict **C-RB3-12**) — declared on **both** sides as `CREATE TABLE … WITHOUT ROWID` in `0008` and `{"sqlite_with_rowid": False}` in `backend/app/db/models.py`. The hidden identity is **removed rather than guarded**, so **no trigger is added or changed and the inventory stays exactly 25**, with all previously reviewed protections (G1–G25, both partial unique indexes, every CHECK, every `RESTRICT` FK) intact.
- **Feasibility proven against the actual schema and the exact pinned stack, not assumed.** Raw SQLite (`/tmp/probe_r6.py`, exit 0): all three aliases rejected, tables create with their real PKs/FKs/indexes and all 25 triggers, guards still fire, normal persistence and independent runs still succeed, PKs NOT NULL, FKs enforced to both rowid and `WITHOUT ROWID` parents, `PRAGMA index_list`/`index_info`/`foreign_key_list` unchanged in behaviour. Pinned ORM/migration (`/tmp/probe_r6_orm.py` in a throwaway venv with `sqlalchemy==2.1.8` + `alembic==1.20.1` from `requirements/requirements.lock`, exit 0): the dialect exposes `with_rowid`, both `create_all` and `op.create_table(..., sqlite_with_rowid=False)` emit the option, reflection round-trips it, index-name parity holds exactly per table, and an **empty downgrade restores the `0007` schema exactly**. **No existing table and no global pragma changes** — historical tables keep their rowids because accepted code orders by `literal_column("rowid")` (`backend/app/services/documents/verification.py:612-663`).
- **Measured limit made normative:** Alembic autogenerate is **blind** to `sqlite_with_rowid` (identical columns/indexes → **empty diff**), so §6.7, N6 and the E4 delta require an **explicit `sqlite_master.sql` assertion** — option present on the three RB3 tables, **absent on every pre-existing table** — and never an autogenerate/`alembic check` argument. The `WITHOUT ROWID` row-size figure is recorded as an **unverified recalled guideline**; the measured behaviour is what the design relies on (no payload failure up to 4,000,000 bytes at `page_size=4096`; worst-case declared rows 550/236/691 bytes all insert).
- **Bounded alternative measured, documented and not recommended:** three `NEW.rowid` `BEFORE INSERT` guards (inventory **25 → 28**, the count updated rather than preserved) close the same gap on rowid tables, but need the predicate `NEW.rowid >= 0` (measured: `NEW.rowid` is **`-1`**, not NULL, for an ordinary insert), leave "never emit `rowid`" as an application-layer obligation, and are **mutually exclusive** with `WITHOUT ROWID` (measured: such a trigger creates on a `WITHOUT ROWID` table and then fails every ordinary insert with `no such column: NEW.rowid`).
- **RB3-R6-02 — RB3-110 corrected in place to per-RB3-table scope:** the 25 names are asserted via `sqlite_master … WHERE type='trigger' AND tbl_name IN ('review_item','evidence_link','review_evaluation')`, **plus** an explicit assertion that all **11** historical triggers (`0003:67`; `0006:26-31`, `:156-162`; `0007:20`, `:89-95`) still exist unchanged — never a database-wide exact set, matching the repository's own membership-style guard. The DB-wide total 36 is a derived consequence only.
- **RB3-R6-03 — G14's scope stated precisely:** G14 validates audit identity **at completion insertion only** and confers **no** immutability on upstream `audit_event` rows; **no global audit-immutability claim is made**. Later audit inconsistency is detected **independently at replay** (§8.2 (5) → precedence 7 `audit_business_inconsistent`, or precedence 2 `orphan_review_audit`), recorded as new replay **case 16**.
- **Matrix RB3-01…RB3-128**, preserving every existing case, correcting RB3-110 in place and adding **RB3-118…RB3-128** (alias rejection across all five replacement spellings, the option declared and absent elsewhere, a Revision-5-schema regression guard proving the gap, no over-blocking, PK NOT NULL, index/FK validity, all prior protections still firing at count 25, row-size headroom, ORM/migration parity plus the autogenerate blind spot, empty-downgrade restoration, and G14's replay-time scope).
- **No implementation, no repository code change.** The two probes ran entirely in `/tmp` (throwaway scripts, in-memory and temporary-file databases, a throwaway venv), **both exit 0**, and **created, edited or deleted no repository file**; no `pytest`, `ruff` or `alembic` command was run against this repository; no source, model, migration, test, fixture, contract, policy, dependency, CI or scanner file is modified; `backend/app/db/session.py` is untouched.
- **Remaining genuine blockers: none for this conservative slice** — outstanding items are **owner ratification only** (D-RB3-01…D-RB3-10 with sub-decisions 05a–**05g**; C-RB3-01…C-RB3-05 and C-RB3-07…C-RB3-**12**, C-RB3-01 still explicitly unratified), each of E1–E6 still needing its own fresh standalone marker. No ratification marker was posted by the agent; PR #42 stays **DRAFT** and **NOT MERGED**; no P4 acceptance is claimed.
- **Scope of this remediation:** the same three documentation paths only — the unratified design corrected in place (Revision 6) plus append-only checkpoints in `docs/phase-reports/PHASE_4_REPORT.md` (new §34) and this roadmap, both verified to remove **zero** lines with all historical evidence preserved.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 design owner ratification recorded — DESIGN ONLY, NO IMPLEMENTATION AUTHORIZED (2026-11-23)

- **Exact owner decision verified independently in this session (authenticated GitHub API read, not taken on report):** repository owner `Muhammed-Fathi` (`author_association = OWNER`) posted the marker **`RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE`** as [PR #42 issue comment #7095039109](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/42#issuecomment-7095039109) at **`2026-11-23T08:06:02Z`** (`created_at` = `updated_at`, unedited), naming the exact ratified commit **`dabcebc74fcd1ed29626b3ada9aaff2ac65053c1`** and PR **#42**. The comment's first line is the marker verbatim, and the SHA it states equals the PR head, the local branch head and `origin/arena/91facff6-ai-doctor-followup-agent` at the time of this append. This records a **design-scope** decision only: it is **not** phase acceptance, not runtime activation, not persistence activation, not clinical use, not merge permission and not agent self-approval.
- **Ratified artifact, preserved byte-for-byte:** [P4-RB3 durable persistence design](../phase-reports/P4_RB3_DURABLE_PERSISTENCE_DESIGN_20261123.md) **Revision 6** at `dabcebc74fcd1ed29626b3ada9aaff2ac65053c1` — git blob **`9b9160b329afa7b41baa971eb9c2558f2c6e073e`**, file `sha256 3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`, **1387** lines. This append touched **no other file**: the design document and `docs/phase-reports/PHASE_4_REPORT.md` (blob `83c0de515dc9871332d4e38c236682246b8b064f`) are unchanged, **no Revision 7 exists and no ratified design decision is reopened, amended or re-argued anywhere in this record.**
- **CI at the exact ratified SHA (verified, both events):** `push` [#45133810215](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45133810215) and `pull_request` [#45133818931](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45133818931), both `completed` **SUCCESS** on head `dabcebc74fcd…`, 2 jobs each (Backend Python 3.12: Ruff lint, Ruff format, backend tests, Alembic migration smoke, OpenAPI contract check, secret/artefact scan; Frontend Node 22: ESLint, typecheck, Vitest, production build) with **zero non-success steps**; exactly two runs exist at that head. Following the accepted RB2 precedent, that is **prior-head design CI only** and **must be re-checked on the final head containing this record** (done: see the recording commit's own CI below and the PR conversation).
- **Accepted decision package (owner's own enumeration).** **D-RB3-01 … D-RB3-10**, explicitly including **D-RB3-02b** (docstring-only E6 clarification, with the append-only contract-note fallback) and **D-RB3-05a … D-RB3-05g**, together with the bounded conflict resolutions documented in Revision 6 (**C-RB3-01…C-RB3-05** and **C-RB3-07…C-RB3-12**; C-RB3-06 closed by transcription). Concretely ratified: an **authenticated internal service** with no API, agent tool, graph node, LLM, task or notification surface; **one controlled committing SQLite transaction** with fresh in-transaction authorization and source re-verification (read-only F2/RB1 pins first, T1–T18); the **exact sealed synthetic policy and pinned demo clock** (`demo-policy-1.1.0`, `2026-11-14T12:00:00Z`, policy digest `f3bdad3f…bd36`) with no wall clock and no conversion; and **three additive tables** — `review_item`, `evidence_link`, `review_evaluation` — with no alteration of any existing object.
- **A2 transport-label semantics and the separate stored-lineage proof (D-RB3-03 Alt A2, D-RB3-10 Option A).** The **unchanged** RB2 evaluator remains the computation core with R01–R08 inherited and zero RB2 diffs. `review_evaluation.lineage_label_policy = 'a2_transport_label'` is a **single-value CHECK** recording only *which ratified evaluator-boundary option governed the labels passed to the evaluator*; it is **never** a claim that every observation in a mixed input has independently verified document lineage. Per-item truth travels with the row in `review_item.provenance_status` (single-value CHECK `'fixture_asserted'`, the evaluator's literal verbatim — a deliberately documented **transport label**) and `review_item.stored_lineage_proved` (RB3's **own** in-transaction stored-lineage proof: loader lineage non-null, L1 source-class step passed, stored verified value and single verified test-name fact, matching measure type and unit), and both are members of `output_identity_sha256`. **C-RB3-01 is thereby owner-accepted as documented, not resolved away**: the honest limitation stays recorded in `TOOL_CONTRACTS.md` (N8) and in the receipt.
- **`WITHOUT ROWID` on all three new RB3 tables, with explicit schema verification (D-RB3-05g, C-RB3-12).** The hidden SQLite `rowid`/`_rowid_`/`oid` replacement path measured in Revision 6 is **removed** rather than guarded: declared as `CREATE TABLE … WITHOUT ROWID` in the proposed `0008` **and** `{"sqlite_with_rowid": False}` in `backend/app/db/models.py`. Because Alembic autogenerate is measured **blind** to the option, the implementation must assert it explicitly from `sqlite_master.sql` — present on the three RB3 tables and **absent on every pre-existing table**. **No existing table, column, index, trigger or global pragma changes**: historical tables keep their rowids (accepted code orders by `literal_column("rowid")`, `backend/app/services/documents/verification.py:612-663`) and `backend/app/db/session.py` stays untouched (`foreign_keys=ON` only, `recursive_triggers` **0**).
- **Complete G1–G25 protection, and preservation of every historical trigger.** The ratified inventory is exactly **25** RB3 triggers — G1–G13 immutability, vocabulary and scope guards; **G14** with its **eight** structural audit comparisons (including `event_type` and `patient_id`), which validate audit identity **at completion-insertion time only** and confer **no** immutability on upstream `audit_event`; **G15–G17** run seals; **G18–G25** per-declared-identity replacement guards — plus both partial unique indexes with their guards mirroring the index predicates, `length()`/range/literal CHECKs and `ON DELETE RESTRICT` foreign keys. RB3-110 asserts the 25 names **scoped to `tbl_name IN ('review_item','evidence_link','review_evaluation')`**, and the **11** accepted historical triggers at head `0007` — `trg_fact_verification_doctor_only` (`0003:67`, `:267-277`), six over `MANIFEST_TABLES` (`0006:26-31`, `:156-162`) and four over `run_gate_evaluation`/`run_gate_blocker` (`0007:20`, `:89-95`) — are asserted **preserved with their original definitions**, never counted as RB3 triggers.
- **Conservative DR-006 handling (D-RB3-08 option (ii)).** Whenever the unchanged evaluator emits DR-006, the **entire** persistence invocation is denied at T12 **before** any replay comparison or write: `409 E_VALIDATION`, reason `dr006_persistence_not_authorized`, **zero writes, no partial persistence, no silently dropped item**. All six RB2 rules stay unchanged and `dr006_policy` is a single-value CHECK `'prohibited_denied'`. This remains a **deliberate proposed scope reduction** — a run with a genuine verified-source conflict persists **no** items at all — recorded in `DEMO_REVIEW_RULES.md` (N13), in the receipt and in §7.4, never presented as neutral. **DR-006 persistence and its six-key span mapping stay deferred and unauthorized**, as do the reserved `document_span`/`checkin_note` kinds and `verification_issue`/`summary_claim` owners.
- **Bounded nine-key audit contract and exact replay semantics (D-RB3-07).** The audit detail is exactly the nine keys `fingerprint_version`, `evaluation_id`, `input`, `output`, `lineage_label_policy`, `dr006_policy`, `items`, `links`, `exclusions` — measured **346** characters worst case over the entire permitted domain against `SAFE_DETAIL_MAX = 500` (**342** minimum, **154** headroom), so it is **never truncation-dependent** and every count §8.2 requires survives storage. The audit request identity is **server-derived** from immutable persisted identifiers only (`subject_type='workflow_run'`, `subject_id=run.id`, never a freshly generated row id, no client-supplied header), making orphan-audit detection deterministic. Replay is **exact**: one immutable sealed completion row per run (`ux_review_evaluation_run` + G17/G24/G25), an exact replay performs **zero writes of any kind**, and every divergence resolves to the first matching typed conflict in the fixed precedence order 1–8 (`completion_evidence_missing` … `audit_key_collision`, all `409 E_IDEMPOTENCY_CONFLICT`, zero writes). A later upstream audit inconsistency is detected **independently at replay** (precedence 7 `audit_business_inconsistent`, or precedence 2 `orphan_review_audit`) — **not** by any claim of global `audit_event` immutability.
- **N1–N13 bounded implementation scope (the only authorized future paths).** N1 service, N2 schemas, N3 additive ORM, N4 migration `0008_p4_rb3_review_persistence`, N5 service tests, N6 migration-guard tests, N7–N9 append-only contract notes (`DATA_DICTIONARY.md`, `TOOL_CONTRACTS.md`, `STATE_AND_GRAPH_CONTRACT.md`), **N10 the implementation review at the exact filename `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md`**, N11–N12 append-only phase checkpoints, N13 the append-only `DEMO_REVIEW_RULES.md` note. **No blanket directory authorization** exists or is implied; module naming avoids every name forbidden by `tests/p2/test_p2_scope_guards.py` and creates no `app/agents` or `app/llm` package.
- **E1–E6 remain separately authorized, each by its own fresh standalone owner marker before any edit.** E1 `backend/tests/test_database.py`, E2 `backend/tests/p2/test_p2_migration.py`, E3 `backend/tests/p2/test_p2_scope_guards.py`, E4 `scripts/python/check_alembic_smoke.py`, E6 `backend/app/services/p5_run_gate.py` (**conditional, docstring-only**, zero logic change, with the append-only contract-note fallback if refused) — deltas exactly as specified in §9.2, none weakened, skipped or replaced. **E5 `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` requires the ACTUAL future measured backend/P3 collection pairing** (proposed marker form `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY`, following the RB1/RB2 precedents): the numbers must be real future measurements, it is **not** a reusable generic permission, and the historical 1255/443 evidence stays untouched. RB1/RB2 exceptions do **not** carry over, and there is no generic permission to change historical tests, scanner policy, fixtures or contracts.
- **Strict next gate — this owner decision permits PLANNING one separate bounded RB3 implementation PR, and only after both conditions hold:** **(a)** the owner reviews and merges the documentation-only PR #42 (the agent never merges, never enables auto-merge, never marks the PR ready, never self-approves and never modifies `main` directly), and **(b)** CI SUCCESS is **independently verified on the exact post-merge `main` merge SHA**. Until both are satisfied: no RB3 implementation, no N-path edit, no E-path edit, no migration, no model, no test. After them, the ratified marker authorizes **one** bounded implementation PR confined to N1–N13, with each of E1–E6 still needing its own marker; the marker's SHA binding means it ratifies **this exact design SHA** and nothing else.
- **Explicitly NOT authorized by this ratification (the owner's own exclusions).** RB3 implementation outside the ratified allowlist; DR-006 persistence or any future evidence-link kind/owner; `review_item.state` transitions to `decided`/`superseded`; an `evidence_link.fact_id` column; widening the upstream comparator's window arithmetic; any pragma change or any existing table's storage option; runtime clinical policy activation; RB4 or run-backed GOLD A/B/C/D acceptance; P4 or P5 final acceptance; real patient use, diagnosis, treatment or messaging; agent self-approval, automatic merging or direct `main` changes. **No RB3 implementation test has been run or passed; no case of the §11 matrix (RB3-01…RB3-128) has been executed, and none may be reported as passing.**
- **Scope of this recording append:** exactly one file — `docs/roadmap/PHASE_PROGRESS.md` — appended **append-only** with **zero removed lines** (verified against the pre-append copy), all historical checkpoints preserved. No application source, model, migration, test, contract, policy, fixture, dependency, CI or scanner file is created, edited or deleted; no additional owner approval marker is posted by the agent; the repository scanner is run on the staged tree and its result reported with the recording commit. **The ratified design SHA `dabcebc74fcd1ed29626b3ada9aaff2ac65053c1` and this new append-only recording SHA are different commits**: the recording commit adds only this roadmap checkpoint and changes no design content, so the ratification remains bound to the design SHA alone.
- P4 remains **IN_REVIEW**; [issue #14](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/14) remains **OPEN**; full P5 remains **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` remains **FAIL / NOT PROVEN**; PR #42 remains **OPEN / DRAFT / NOT MERGED**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.** Stopping for independent reviewer verification and the owner's merge decision.

## P4-RB3 implementation candidate delivered (N1–N13; E1–E6 untouched) (2026-11-23)

- **Baseline & scope:** Implemented on branch `arena/1123ae67-ai-doctor-followup-agent` from `main@6d121228a9e742849337366c6880a2cb887b1486` under ratified PR #42 marker `RATIFY-P4-RB3-DURABLE-PERSISTENCE-DESIGN-SCOPE` (design SHA-256 `3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`, PR #42 merged with CI `#45141004060` `success`). Strictly confined to the 13 authorized N1–N13 paths; zero edits to `backend/app/db/session.py`, `backend/app/services/p4_rb2_offline_rules.py`, or untouched E1–E6 targets.
- **Measured verification (Linux Python 3.11.2 `/tmp/rb3-venv` from `requirements/requirements-dev.lock`, Node `v22.22.3`):**
  - Targeted RB3 suite (`test_p4_rb3_review_persistence.py` + `test_p4_rb3_migration_guards.py`): **20 passed** (`13` service + `7` migration guards).
  - Safety guards (`test_safety_guards.py`): **9 passed**.
  - `ruff check .` & `ruff format --check .`: **PASS** (`145 files`).
  - `check_openapi.py`: **PASS** (`17 paths / 18 operations, 43 schemas`).
  - `scan_repository.py`: **PASS**.
  - Frontend (`npm run lint`, `npm run typecheck`, `npm test`, `npm run build`): **PASS** (`13` Vitest tests).
  - Full `pytest`: **1270 passed, 7 failed** out of **1277 collected** (**443** P3 collected). All **7** failures are exclusively the untouched E1–E5 legacy guards (`test_database.py` ×2, `test_p2_migration.py` ×2, `test_p2_scope_guards.py` ×1, `check_alembic_smoke.py` via `test_p5_run_gate.py` ×1, `test_windows_ocr_acceptance.py` ×1 expecting literal `**1277 collected**, of which **443** are the P3 suite` in `PHASE_3_WINDOWS_ACCEPTANCE.md`).
- **Next gate:** Owner review of `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md` (N10) and standalone owner exception markers for E1–E5 (plus optional E6 docstring note) before Python 3.12 CI and Windows verification. P4 remains **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 Round-2 implementation review blockers resolved (`RB3-I01`–`RB3-I05`; E1–E6 untouched) (2026-11-23)

- **Baseline & scope:** Resolved all five Round-2 implementation review blockers (`RB3-I01`–`RB3-I05`) atop Round-1 commit `414284de40f0cee23be85deebf1e5310aa0ff043` on draft PR #43 (base `main@6d121228a9e742849337366c6880a2cb887b1486`), strictly inside the ratified Revision-6 architecture and the same 13 authorized **N1–N13** paths. Zero edits to F2, RB1, RB2, `monitoring.py`, `session.py`, or any E1–E6 path.
- **Measured Round-2 verification (Linux Python 3.11.2 `/tmp/rb3-venv` from `requirements/requirements-dev.lock`):**
  - Targeted RB3 suite (`test_p4_rb3_review_persistence.py` + `test_p4_rb3_migration_guards.py`): **25 passed** (`18` service + `7` migration guards).
  - RB3 + safety guards (`test_safety_guards.py`): **34 passed**.
  - `ruff check .` & `ruff format --check .`: **PASS** (`145 files`).
  - `check_openapi.py`: **PASS** (`17 paths / 18 operations, 43 schemas`).
  - `scan_repository.py`: **PASS** (`294` tracked files).
  - Full `pytest`: **1275 passed, 7 failed** out of **1282 collected** (**443** P3 collected). All **7** failures remain exclusively the untouched E1–E5 legacy expectations (`test_windows_ocr_acceptance.py` now expects literal `**1282 collected**, of which **443** are the P3 suite` in `PHASE_3_WINDOWS_ACCEPTANCE.md`).
- **Next gate:** Owner review of `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md` (N10, including §5–§8 and the complete `RB3-01..128` matrix) and standalone owner markers for E1–E4, updated-count E5 (`1282` / `443`), and optional docstring-only E6 before Python 3.12 CI and Windows verification. PR #43 stays **OPEN / DRAFT / NOT MERGED**; P4 remains **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 E1–E5 standalone owner authorizations verified on PR #43 (2026-11-23)

- **Independently verified on GitHub API (`Muhammed-Fathi/AI-Doctor-FollowUp-Agent` PR #43 Conversation comments, `author_association = OWNER`, login `Muhammed-Fathi`), recorded here prior to editing any exceptional E1–E5 path:**
  1. **E1 (`backend/tests/test_database.py`):** marker `APPROVE-P4-RB3-E1-TEST-DATABASE-UPDATE` at [PR #43 comment #7102514514](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102514514) (`2026-11-23T13:25:32Z`) — compatibility-only changes per Revision 6 §9.2 (`HEAD_REVISION = "0008_p4_rb3_review_persistence"`, exact 3 RB3 tables at head, preserve historical checks, reversibility, and remaining future-table prohibitions).
  2. **E2 (`backend/tests/p2/test_p2_migration.py`):** marker `APPROVE-P4-RB3-E2-P2-MIGRATION-UPDATE` at [PR #43 comment #7102522320](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102522320) (`2026-11-23T13:25:52Z`) — advance expected head and exact head table set for `0008`; preserve historical migration assertions and existing ORM/migration parity assertion unchanged.
  3. **E3 (`backend/tests/p2/test_p2_scope_guards.py`):** marker `APPROVE-P4-RB3-E3-P2-SCOPE-GUARDS-UPDATE` at [PR #43 comment #7102527486](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102527486) (`2026-11-23T13:26:06Z`) — allow exactly the three authorized RB3 tables at head `0008` while preserving their prohibition at earlier historical revisions wherever applicable and keeping all other future-phase tables/surfaces forbidden.
  4. **E4 (`scripts/python/check_alembic_smoke.py`):** marker `APPROVE-P4-RB3-E4-ALEMBIC-SMOKE-UPDATE` at [PR #43 comment #7102533877](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102533877) (`2026-11-23T13:26:21Z`) — advance head to `0008`, add pinned historical `p5_f1` (`0007`) state, preserve all earlier schema expectations, and assert the 3 RB3 tables, 9 named indexes, partial unique predicates, 25 RB3 triggers scoped to their tables, preservation of the 11 historical triggers, and explicit `WITHOUT ROWID` assertions from `sqlite_master.sql` (present on the 3 RB3 tables, absent on every pre-existing table).
  5. **E5 (`docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`):** marker `APPROVE-P4-RB3-P3-HANDOFF-COLLECTION-ONLY` at [PR #43 comment #7102539192](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7102539192) (`2026-11-23T13:26:34Z`) — append-only collection-count compatibility note recording `**1282 collected**, of which **443** are the P3 suite` ONLY if re-measurement after test changes still equals `1282` backend / `443` P3 (collection evidence only, not passed count).
- **E6 (`backend/app/services/p5_run_gate.py`):** **NOT authorized** — kept completely untouched; N8 (`docs/contracts/TOOL_CONTRACTS.md`) contract note fallback preserved.
- No merge, no phase acceptance, no test weakening, no pragma change authorized. PR #43 stays **OPEN / DRAFT / NOT MERGED**; P4 remains **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 Round-3 final corrections & authorized E1–E5 closure completed (2026-11-23)

- **Baseline & scope:** Completed atop Round-2 commit `98cfefda10f162a8c261d275e1b0147979036016` on draft PR #43 (exact base `main@6d121228a9e742849337366c6880a2cb887b1486`, design SHA-256 `3c73f790e70a25301b17ac06566a719b3976629e48ed189bcb4f25c8738d8da4`) within N1–N13 plus verified owner-authorized E1–E5 only; E6 (`backend/app/services/p5_run_gate.py`) remains untouched.
- **Completed items:** `RB3-I06` T13 minimal foreign-patient `403 E_SCOPE_VIOLATION` classification (`p4_rb3_review_persistence.py`); `RB3-I07` test closures (`RB3-26`, `RB3-28`, `RB3-44`, `RB3-49`, `RB3-97`, `RB3-98`) and truthful `N10` matrix/factual corrections (`RB3-75..77` `DEFERRED FUTURE EXTENSION / NOT EXECUTED`, `RB3-22`/`RB3-32` exact descriptions, `RB3-I03` exact Decimal test values, injected `commit()` failure note, `6d121228a9e742849337366c6880a2cb887b1486` SHA corrections); Revision 6 §9.2 updates in E1–E4; re-measured collection (`1282` backend / `443` P3) and append-only collection note in E5 (`PHASE_3_WINDOWS_ACCEPTANCE.md`).
- **Final local verification (Linux Python 3.11.2, Node `v22.22.3`):** `25 passed` RB3 tests (`18` service + `7` migration guards); `111 passed` `test_windows_ocr_acceptance.py`; full backend `pytest` **1282 passed, 0 failed** (`1282` collected, `443` P3 collected); `ruff check` & `ruff format --check` PASS (`145 files`); full Alembic upgrade -> downgrade -> upgrade + `check_alembic_smoke.py` PASS across all 9 states (`head`, `p5_f1`, `p5_f0`, `p3_stage1`, `p3_recovery`, `p3`, `p2`, `p1`, `base`); `check_openapi.py` PASS (`17 paths / 18 operations, 43 schemas`); `scan_repository.py` PASS (`294` files); frontend `lint`/`typecheck`/`vitest 13`/`build` PASS.
- **Next gate:** Push incremental Round-3 commit to PR #43, verify exact-head GitHub Actions Python 3.12 Backend + Node 22 Frontend CI runs, and await independent review + owner Windows PowerShell 5.1 acceptance. PR #43 remains **OPEN / DRAFT / NOT MERGED**; P4 remains **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 Final Bounded Acceptance Evidence Closure (Round 4 — 2026-11-23)

- **Baseline & scope:** Closed atop Round-3 commit `7936bb535fb24ac4a4d9278921cdcbcd400bdf77` on draft PR #43 (base `main@6d121228a9e742849337366c6880a2cb887b1486`) inside `N5`, `N6`, `N10`–`N12`, and owner-authorized `E4` (`scripts/python/check_alembic_smoke.py`); `E5` (`PHASE_3_WINDOWS_ACCEPTANCE.md`) and `E6` (`p5_run_gate.py`) remain untouched.
- **Evidence closures:**
  - **`RB3-110/127` (`N6` + `E4`):** `test_rb3_29_30_31_127_...` proves exact `sqlite_master` (`62` non-autoindex objects + `sqlite_autoindex_*` counts + all `11` historical trigger SQL definitions verbatim) and `12`-table historical data preservation across `0007 -> 0008 -> 0007` plus populated downgrade refusal, `WITHOUT ROWID`, and `25` RB3 triggers; `check_alembic_smoke.py` verifies exact normalized SQL (`HISTORICAL_11_TRIGGER_SQL`) for all `11` historical triggers at `head`.
  - **`RB3-98` (`N5` + `N6`):** Distinguished the **`100`** end-to-end legitimately reachable exclusion cap (`MAX_HISTORY_OBSERVATIONS = 100`, proved end-to-end on fresh `patient_98` with `99` L1 + `1` L2 = `100`, no truncation) from the **`200`** design/storage bound (`ck_review_evaluation_review_eval_excl_count_range` `200` accept vs `201`/`-1` CHECK refusal in valid `G14` migration fixture, and unmodified `MAX_EXCLUSIONS == 200` service boundary `200` deduped accept vs `201` `409 E_VALIDATION` zero-write denial); retained `MAX_EXCLUSIONS = 4` test as supplemental coverage.
  - **Baseline collection accounting:** Verified `main@6d121228a9e742849337366c6880a2cb887b1486` collects **`1255`** backend tests (**`443`** P3, **`87`** in `test_p2_scope_guards.py`), not `1257`; PR #43 collects **`1282`** (`+2` `app_sources()` checks in `test_p2_scope_guards.py` for `N1`/`N2` + `+25` RB3 tests in `N5`/`N6`), preserving `E5` (`1282 / 443`) untouched.
- **Final local verification:** `49 passed` focused (`18` N5 + `7` N6 + `24` P5); full backend `pytest` **1282 passed, 0 failed** (`1282` collected, `443` P3); Ruff PASS (`145` files); all `9` Alembic smoke states PASS; `check_openapi.py` PASS (`17/18/43`); `scan_repository.py` PASS (`294` files); frontend `lint`/`typecheck`/`vitest 13`/`build` PASS.
- **Next gate:** Push incremental Round-4 commit to PR #43, verify exact-head GitHub Actions `push` and `pull_request` CI runs, and pause for owner Windows PowerShell 5.1 verification (`scripts/powershell/setup.ps1`, `scripts/powershell/test_all.ps1`) and independent review. PR #43 remains **OPEN / DRAFT / NOT MERGED**; P4 remains **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; original real-OCR `GOLD-EX-11` **FAIL / NOT PROVEN**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB3 Final Owner Acceptance & Windows Verification Recorded (2026-11-23)

- **Accepted implementation SHA vs recording commit:** Bounded `P4-RB3` implementation accepted by owner at exact reviewed commit **`c929dee4dbc72028fe18d047766553e5909faa35`** on draft PR #43 (base `main@6d121228a9e742849337366c6880a2cb887b1486`); recorded in a subsequent **documentation-only commit** touching only `docs/phase-reports/P4_RB3_IMPLEMENTATION_REVIEW_20261123.md`, `docs/phase-reports/PHASE_4_REPORT.md`, and `docs/roadmap/PHASE_PROGRESS.md`.
- **Owner decision record:** `OWNER-ACCEPT-P4-RB3` posted by `Muhammed-Fathi` (`OWNER`) at `2026-11-23T15:26:52Z` ([`#issuecomment-7105580779`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7105580779)), citing independent engineering review acceptance recommendation, exact-head CI **#45191070030** (push, `success`) and **#45191082779** (pull request, `success`) on `c929dee4dbc72028fe18d047766553e5909faa35`, and local Windows verification.
- **Observed Windows verification (`c929dee4dbc72028fe18d047766553e5909faa35`, isolated worktree):**
  - Windows PowerShell `5.1.22621.4249`, Python `3.12.9`, Node `v24.15.0`, npm `11.17.0`, Git `2.50.0.windows.2`; exact `HEAD` matched before/after with no tracked working-tree changes.
  - `setup.ps1` **PASS** (`114.7s`, exit `0`); `test_all.ps1` **PASS** (`669.9s`, exit `0`; **12 mandatory gates PASS**, **0 FAIL**, **1 optional Playwright SKIP**); Backend pytest **PASS** with four visible skipped markers (exact backend passed count not printed — `1282 passed` belongs strictly to the observed Linux result); Frontend Vitest **13 passed**; Alembic upgrade/downgrade/upgrade through revision `0008` **PASS**; OpenAPI **PASS** (`17` paths, `18` operations, `43` schemas); Repository scanner **PASS** (`294` tracked files, `7` secret patterns, `4` claim patterns).
- **Next gate:** Stop after pushing the documentation-only recording commit and verifying exact recording-head CI runs, awaiting independent verification of the recording commit and the owner's merge decision. **P4-RB3 owner-accepted implementation only**; **P4 remains `IN_REVIEW`**; **Issue #14 remains `OPEN`**; **Full P5 remains `NOT ACCEPTED`**; **`GOLD-EX-11` remains `FAIL / NOT PROVEN`**; **`RB3-75..77` remain deferred**; **DR-006 end-to-end reachability remains `NOT PROVEN`**; **RB4 has not started**; **PR #43 remains `OPEN`, `DRAFT`, and `NOT MERGED`**. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**







## P4-RB3 owner merge and post-merge main CI (2026-11-23)

Independently checked [PR #43](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43) MERGED by owner at 2026-11-23T16:14:22Z, merge `0738a32acfd3b9512f85d82062108d9adf14d9c9`; [owner acceptance #7105580779](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/43#issuecomment-7105580779) applies to implementation `c929dee4dbc72028fe18d047766553e5909faa35`, followed by docs-only recording `bc0ae73907cfa6d8f1515881c15bcd05cb83644e`. Owner-reported Windows: 12 mandatory PASS, 0 FAIL, 1 optional Playwright SKIP. Post-merge [main CI #45214231214](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45214231214) COMPLETED/SUCCESS at the merge SHA, Backend Python 3.12 and Frontend Node 22, all 25 job steps successful. Historical pre-merge statuses above are superseded, not rewritten.

## P4-RB4 design-only checkpoint (2026-11-23)

New [GOLD run-backed acceptance design](../phase-reports/P4_RB4_RUN_BACKED_GOLD_ACCEPTANCE_DESIGN_20261123.md) is a proposal only. C's blocked initial document cannot enter an F0 manifest; request the owner's explicit decision on the disclosed F0 refusal / post-selection F1 HALT / corrected new-run reconciliation. A/B/D expectations and test-only future allowlist are not execution or ratification. Proposed marker `RATIFY-P4-RB4-RUN-BACKED-GOLD-ACCEPTANCE-DESIGN-SCOPE` grants no permission unless posted by the owner with the stated C decision. P4 IN_REVIEW; issue #14 OPEN; full P5 NOT ACCEPTED; real GOLD-EX-11 FAIL / NOT PROVEN; RB3-75..77 deferred; DR-006 persistence prohibited. ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

## P4-RB4 owner design ratification recorded (2026-11-23)

- **Owner decision:** `RATIFY-P4-RB4-RUN-BACKED-GOLD-ACCEPTANCE-DESIGN-SCOPE` was posted by `Muhammed-Fathi` (`OWNER`) at **2026-11-23T17:17:11Z** in [PR #44 comment #7108431644](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/44#issuecomment-7108431644), explicitly ratifying reviewed design HEAD **`5ec047815a6967161a54af41f53d011423d83a89`**, based on `main@0738a32acfd3b9512f85d82062108d9adf14d9c9`. Independently checked reviewed-head CI: [push #45219008531](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45219008531) and [pull request #45219052487](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45219052487) both COMPLETED / SUCCESS at that exact SHA, Backend Python 3.12 and Frontend Node 22. This supersedes the historical proposal-only checkpoint above; the design document remains byte-identical.
- **Explicit C-F0-C decision:** The owner accepts (1) genuine F0 refusal of the original pending GOLD-C document before run creation, (2) a separately labelled genuine-run post-selection deterioration test with actual F1 HALT and zero downstream review persistence, and (3) a **new** genuine corrected-source run after explicitly staged synthetic verification and correction. The original pending state did not produce a genuine F1 HALT; scripted correction does not establish real OCR success. Original GOLD-EX-11 remains **FAIL / NOT PROVEN**.
- **Future implementation authorization, conditional:** One separate bounded RB4 integration-test PR, **only after owner merge of this design PR and successful exact merged-main CI**, limited to `backend/tests/p4/test_p4_rb4_run_backed_gold.py`, `docs/phase-reports/P4_RB4_RUN_BACKED_GOLD_IMPLEMENTATION_REVIEW_20261123.md`, and append-only `docs/phase-reports/PHASE_4_REPORT.md` and `docs/roadmap/PHASE_PROGRESS.md`. Any P3 collection-count compatibility note requires a separate fresh owner authorization for the actually measured backend/P3 collection pairing; prior authorizations are not reusable. No generic legacy test exception.
- **Future implementation verification clarifications:** Load and assert the frozen GOLD JSON expectations, not convenient surrogate values. Exercise accepted mapping logic for A/B/C, distinguishing scripted stored fixture construction from real ingestion, OCR and human verification. For initial C refusal assert exactly three pending facts, P3 issue types and derived VI-002 count/message. For controlled C deterioration use a genuine previously created run, actual F1 blocker derivation, zero RB2 invocation and zero RB3 writes. Preserve corrected-source lineage and the new-run distinction. For D assert the exact five ordered flags, seven observation links and correct semantic dedupe keys. Report discrepancies rather than modifying sources, fabricating evidence or weakening tests. These are verification clarifications, not additional production scope; none has been executed here.
- **Exclusions and status:** No production source, existing tests, migrations, models, frozen GOLD fixtures, policies, dependencies, CI, scanners or safety contracts are authorized to change by this decision; no DR-006 persistence, runtime activation, graph, LLM, API, UI, task or notification implementation. Design ratification is **not** RB4 or P4 acceptance. P4 remains **IN_REVIEW**, issue #14 **OPEN**, full P5 **NOT ACCEPTED**, RB4 **unexecuted and unaccepted**, RB3-75..77 deferred, DR-006 end-to-end reachability unproven and persistence prohibited. No agent merge, auto-merge, direct main edits or self-approval. PR #44 remains OPEN / DRAFT / NOT MERGED pending independent recording review, exact recording-head CI and the owner merge decision. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB4 run-backed GOLD integration-test implementation candidate delivered (2026-11-23)

- **Authorization & baseline:** Implemented under the owner's `RATIFY-P4-RB4-RUN-BACKED-GOLD-ACCEPTANCE-DESIGN-SCOPE` decision ([PR #44 #7108431644](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/44#issuecomment-7108431644), `2026-11-23T17:17:11Z`) only after PR #44 was owner-merged (`8f341b0822d9e76b905e2b4fda09726e6a3ea4e6`, `18:09:49Z`) and main CI [#45235418200](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45235418200) was verified SUCCESS. New branch `arena/a61b8893-p4-rb4-run-backed-gold` from that exact main; the merged design branch was not reused.
- **Exact changed paths (allowlist only):** NEW `backend/tests/p4/test_p4_rb4_run_backed_gold.py` (12 tests, 2635 lines); NEW `docs/phase-reports/P4_RB4_RUN_BACKED_GOLD_IMPLEMENTATION_REVIEW_20261123.md`; append-only `docs/phase-reports/PHASE_4_REPORT.md`; append-only `docs/roadmap/PHASE_PROGRESS.md`. No production, migration, model, legacy test, fixture, policy, CI, scanner or dependency change.
- **Executed results (Linux Python 3.11.2, disclosed deviation from CI 3.12):** RB4 file **12 passed / 0 failed / 0 skipped** covering RB4-01…RB4-12 (RB4-12 Linux guard only; owner Windows NOT RUN). Focused suites 216 passed; full backend **1 failed, 1293 passed**; P3 **1 failed, 442 passed** — the only failure in both is `test_handoff_test_count_matches_the_suite_it_describes`, which requires `PHASE_3_WINDOWS_ACCEPTANCE.md` to quote the new whole-backend collection. Ruff lint/format PASS; Alembic smoke PASS; OpenAPI PASS; scanner PASS. Measured collection on the final tree: **backend 1294 / P3 443** (collected, not passed; baseline 1282/443).
- **Owner authorization requested (single consolidated item):** append-only collection note `**1294 collected**` / `**443**` in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` (not in the RB4 allowlist; untouched; no test weakened). If the counts move before that note lands, re-measure and request a new exact authorization.
- **Status:** RB4 is an **implementation candidate, not accepted** — independent review, exact-head CI and the owner's isolated Windows gate are outstanding. P4 **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; real GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 deferred; DR-006 persistence prohibited, end-to-end reachability unproven; no agent merge or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB4 owner collection-only authorization verified (2026-11-23) — recorded before editing the exceptional path

- **Owner decision:** `APPROVE-P4-RB4-P3-HANDOFF-COLLECTION-ONLY` posted by `Muhammed-Fathi` (`OWNER`; verified repository owner) at **2026-11-23T19:28:46Z** in [PR #45 comment #7111663704](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/45#issuecomment-7111663704), authorizing the collection-only compatibility update for implementation HEAD **`baff43e08e7549d0776829cc134f6be539439dbd`** on the single exceptional path `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`, with the exact append literal `**1294 collected**, of which **443** are the P3 suite`. The comment states the previous whole-backend collection was 1282, the 12 additional collected tests belong to the authorized RB4 integration suite, P3 remains 443, and that this is collection evidence only — not passed tests, not Windows acceptance, not a broader exception.
- **Remeasured before editing:** on the clean tree at `baff43e08e7549d0776829cc134f6be539439dbd` (Linux Python 3.11.2), `pytest backend/tests --collect-only` = **1294** and `pytest backend/tests/p3 --collect-only` = **443**; `test_handoff_test_count_matches_the_suite_it_describes` fails only on the missing `**1294 collected**` token. The measured pairing equals the authorized pairing, so the append proceeds; `PHASE_3_WINDOWS_ACCEPTANCE.md` was untouched until this record existed. No legacy test, assertion, fixture, migration or production path is changed by this authorization.
- **Status:** collection-only evidence; RB4 remains pending independent review and actual owner Windows acceptance. P4 **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; GOLD-EX-11 **FAIL / NOT PROVEN**; DR-006 persistence prohibited. No agent merge or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB4 Round 2 evidence closure delivered (2026-11-23)

- **Collection compatibility executed under the verified owner authorization:** after remeasuring backend **1294** / P3 **443** on `baff43e08e7549d0776829cc134f6be539439dbd` and recording the authorization above, the exact literal `**1294 collected**, of which **443** are the P3 suite` was appended (append-only, 6 insertions / 0 deletions) to `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`; historical P3/Windows/OCR evidence preserved verbatim; the legacy guard test untouched and now passing (`1 passed`). No passed-test or Windows-acceptance claim is made by that note.
- **Independent-review findings closed inside the authorized RB4 test file (collection unchanged at 12):** R01 scalar per-column snapshots replacing ORM-instance snapshots (defect admitted and corrected), WorkflowRun/manifests/gate/completion/items/links/audits covered, audit filtering fixed, snapshot sensitivity demonstrated via the permitted mutable `workflow_run.status`; R02 stored-vs-receipt-vs-independent-F2 evidence and `_assert_exact_replay` at all six replay sites; R03 truthful pending → issues → scripted correction (unchanged test name kept via `verified`) → resolved same issue rows → accepted mapping → new run, plus RB4-04 denial snapshots separated from legitimate F1 writes and post-HALT denial, with an attempt-recording RB2 spy; R04 complete field-by-field D equivalence; R05 report fidelity separating executed / supporting-executed / source-presence-only / Linux-vs-Windows.
- **Executed (Linux Python 3.11.2, disclosed deviation from CI 3.12):** RB4 **12 passed / 0 failed / 0 skipped**; focused **216 passed**; full backend **1294 passed / 0 failed**; P3 **443 passed**; legacy guard **1 passed**; collection **1294 / 443**; Ruff lint/format PASS; Alembic smoke PASS; OpenAPI PASS; scanner PASS. Frontend and exact-head results are read from CI only; Windows NOT RUN (owner-only).
- **Status:** RB4 implementation candidate, **not accepted** — independent review, exact-head CI and owner Windows acceptance outstanding. P4 **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 deferred; DR-006 persistence prohibited, reachability unproven; PR #45 OPEN / DRAFT / NOT MERGED; no agent merge or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4-RB4 Final Owner Acceptance & Windows Verification Recorded (2026-11-23)

- **Owner acceptance verified:** `OWNER-ACCEPT-P4-RB4` by `Muhammed-Fathi` (`OWNER`; repository owner) at **2026-11-23T20:30:40Z**, [PR #45 comment #7113168956](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/45#issuecomment-7113168956), accepting the bounded P4-RB4 genuine run-backed GOLD A/B/C/D integration implementation at exactly **`935283577e55f9ed92821393eec088e02017d6d0`**, based on independent engineering review (R01–R05 closed), exact-head Actions #45253520543 / #45253532699, reported Linux results and the owner's own Windows verification; the ratified C-F0-C reconciliation is accepted as implemented and tested. The comment authorizes ONE documentation-only, append-only commit limited to the RB4 implementation review, `PHASE_4_REPORT.md` and this roadmap; no production, test, model, migration, policy, fixture, scanner, dependency, CI or P3 handoff change; no agent merge, auto-merge, direct main edit, self-approval or next-phase implementation.
- **Exact-head CI reconfirmed (`9352835…`):** push #45253520543 and PR #45253532699 both COMPLETED / SUCCESS; Backend Python 3.12 and Frontend Node 22 successful; all 50 reported steps successful.
- **Owner-executed Windows evidence (isolated worktree `E:\DEPI\AI-Doctor-RB4-verify`, exact HEAD before/after, no tracked changes):** PowerShell 5.1.22621.4249, Python 3.12.9, Node v24.15.0, npm 11.17.0, Git 2.50.0.windows.2; fresh `.env` + isolated venv; hash-pinned deps installed; `npm ci` 235 packages (non-fatal esbuild allow-scripts warning; setup/tests/build succeeded). Setup PASS 128.6 s (`SETUP_EXIT_CODE=0`); wrapper self-test 14 PASS; shutdown-identity self-test 38 PASS; Ruff lint/format PASS (146 files); backend pytest PASS with four visible skipped markers (**exact Windows passed count not printed — `1294 passed` is the Linux result only**); Alembic through `0008` PASS; OpenAPI PASS (17/18/43); frontend typecheck + lint PASS; Vitest 13 passed; build PASS; scanner PASS (297 files / 7 secret / 4 claim patterns); full quality gate PASS 602.1 s — **12 mandatory PASS / 0 FAIL / 1 optional Playwright SKIP**, `TEST_ALL_EXIT_CODE=0`, `RB4 WINDOWS VERIFICATION PASSED`. Finer details (worktree path, self-test counts, npm/Ruff counts, typecheck/lint, esbuild warning, final line) are as reported by the independent reviewer from the owner-supplied full PowerShell output.
- **Recorded closures and matrix:** R01 scalar snapshots + sensitivity proof; R02 stored fingerprints/audit/replay evidence; R03 GOLD-C refusal / HALT / corrected-new-run; R04 complete RB2→RB3 equivalence; R05 truthful attribution. Linux: RB4-01…RB4-11 PASS, RB4-12 PASS (Linux schema guard only); focused 216, full backend 1294 passed / 0 failed (Py 3.11.2). Historical Round-1 CI failures (#45245954024 / #45246015431 at `baff43e…`) were directly verified at the Backend tests step; the failing-test identity was inferred from the identical local run and the real collection guard, not read from CI logs; the owner-authorized collection note and Round-2 strengthening were followed by green exact-head CI. P3 handoff not edited by this recording.
- **Status:** P4-RB4 **owner-accepted bounded integration only** — not overall P4 acceptance, full P5 execution, actual human verification, real OCR success or clinical clearance. P4 **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 deferred; DR-006 persistence prohibited, genuine end-to-end reachability unproven. No P4 overall closure or P5 implementation started. PR #45 **OPEN / DRAFT / NOT MERGED** pending independent recording verification and the owner's merge decision; no agent merge, auto-merge or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4 comprehensive closure assessment and P5 readiness review — documentation-only (2026-11-23)

- **Owner request and scope:** comprehensive P4 phase closure assessment plus P5 readiness review, **assessment + documentation only**. No P4 PASS, no P4 acceptance, no P5 authorization, no next-phase implementation. New branch `arena/a61b8893-p4-final-closure-assessment` from the exact owner-merged `main@96cb275136f9f80608709ce8c7d83693bffa36c3`; the merged PR #45 branch was not reused.
- **Baseline independently re-verified before editing:** PR #45 merged by `Muhammed-Fathi` at `2026-11-23T20:42:08Z`, `merge_commit_sha=96cb275136f9f80608709ce8c7d83693bffa36c3`, head `679ccb554e3e5c147c734bd0d2e6ca4dc9dec7a3`; merged main tree `86b8645a4e7d5f3f6be514586a155448ad17046e` identical to the recording head tree (empty diff); post-merge main CI [#45262091228](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45262091228) COMPLETED / SUCCESS (Backend Python 3.12 14/14, Frontend Node 22 11/11); `OWNER-ACCEPT-P4-RB4` [`7113168956`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/45#issuecomment-7113168956) re-read as OWNER, `2026-11-23T20:30:40Z`, never updated, accepting `935283577e55f9ed92821393eec088e02017d6d0`; issue #14 `open`, 19 comments read.
- **New assessment delivered:** [`P4_FINAL_CLOSURE_ASSESSMENT_20261123.md`](../phase-reports/P4_FINAL_CLOSURE_ASSESSMENT_20261123.md) — full requirement-to-evidence matrix with original expectation, implemented behaviour, exact path + symbol, exact test file + function, executed evidence + source, owner decision + merge identity, status and remaining action for every applicable `REQ-*`, `P4-1..P4-5`, `RULE-01..08`, `MON-01..03`, `TRUST-01/02`, `NEG-19`, `SAFE-06` and every `MASTER_PLAN` P4 exit clause; the accepted F0→F1→F2→RB1→RB2→RB3→RB4 trace; the C01–C07 unresolved-point analysis (DR-006, demo-policy authority, RB3-75..77 individually, P3 OCR four-layer distinction, GOLD-C reconciliation, service/API/agent-tool boundary, literal-vs-equivalent evaluation requirements); the consolidated decision; and a P5 readiness plan.
- **Recommendation: B — bounded conditional academic acceptance** (not A, not C). Roll-up across the 50 requirement rows: 27 satisfied · 11 partially satisfied · 6 rows outside P4 scope (3 unique) · 2 superseded by explicit owner decision · 4 deferred. **Genuine mandatory blockers for B: none.** Six would-be blockers for A are enumerated: MON-03 run-backed DR-006, literal RULE-08 `+400 days` replay, exhaustive RULE-04 wording scan, public review-item API + agent tools, `document_span`/`fact` links, plus the TRUST-01 draft half.
- **Proposed owner acceptance marker — PROPOSAL ONLY, NOT AUTHORIZATION:** `OWNER-ACCEPT-P4-BOUNDED-CLOSURE-B`, with the scope text and seven objective conditions in §5.7/§5.8 of the assessment. The agent posts no marker and claims no acceptance.
- **P5 readiness (planning only):** reusable accepted components inventoried; remaining scope mapped to `STATE_AND_GRAPH_CONTRACT.md`, `TOOL_CONTRACTS.md`, `LLM_ADAPTER.md`; P5/P6/P7/P8 separation table; slices P5-S0 typed state (no graph) → S1 tool adapters → S2 orchestrator + N2 gate + checkpoints (no LLM) → S3 LLM adapter + fallback + validation + grounding → S4 N6 interrupt/resume + restart reconciliation → S5 gold summaries + benchmark. Each requires its own branch/PR, exact allowlist, exact-head CI, owner Windows gate and owner merge, and may begin **only after** an explicit P4 closure decision **and** a separate P5 authorization.
- **Verification honesty:** only `python3 scripts/python/scan_repository.py` executed locally on system Python 3.11.2 (disclosed deviation; CI 3.12 authoritative). No test suite, Alembic, OpenAPI or ruff executed locally for this docs-only change; all executed test evidence is CI at a named SHA, owner Windows at a named SHA, or previously recorded local Linux 3.11.2 results at a named SHA. `1294 passed` is a Linux count only.
- **Exact changed paths:** `docs/phase-reports/P4_FINAL_CLOSURE_ASSESSMENT_20261123.md` (new), `docs/phase-reports/PHASE_4_REPORT.md` (append-only), `docs/roadmap/PHASE_PROGRESS.md` (append-only). No source, test, migration, model, policy, fixture, dependency, scanner, script, CI, contract, traceability, evaluation or historical-report change; no P3 handoff edit; no production implementation.
- **Status preserved:** P4 **IN_REVIEW**; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred, never executed**; DR-006 persistence **prohibited**, genuine end-to-end reachability **unproven in both directions**; runtime demo policy **not activated**; no agent merge, auto-merge, direct main edit or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P4 bounded conditional acceptance recorded — documentation-only (2026-11-23)

- **Owner decision verified (authenticated read, not taken on report):** repository owner `Muhammed-Fathi` (`author_association: OWNER`) posted the standalone marker **`OWNER-ACCEPT-P4-BOUNDED-CLOSURE-B`** at [PR #46 comment #7114121198](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/46#issuecomment-7114121198), created **`2026-11-23T21:11:11Z`**, `updated_at` identical (never edited). It names the reviewed assessment HEAD **`c9b80e77f17852174488d7aa4995ac94f48c4f92`**, PR **#46**, and the accepted implementation baseline **`main@96cb275136f9f80608709ce8c7d83693bffa36c3`**.
- **Decision:** **Outcome B approved — bounded conditional academic acceptance of Phase 4**, accepting P4-1 through P4-4 including the accepted F0/F1/F2 foundations and RB1/RB2/RB3/RB4 integration evidence, subject to existing bounded authorizations. Eight dispositions ratified: DR-006 pure-evaluator-only with persistence prohibited, MON-03 only partially satisfied in the run-backed context, C-RB3-08 open and reachability unproven in both directions; RB3-75..77 deferred and unexecuted (separately authorized future evidence-persistence extension, considered in P5/P7 planning if required); agent-tool adapters to **P5**; public review-item read/decision APIs to **P6**; TRUST-01 draft-related acceptance to **P5**; runtime demo-policy activation requiring **separate explicit authorization before P5 use**; RULE-04 exhaustive coverage to **P7**; RULE-08 literal advanced-clock replay unexecuted, to **P7** for contract reconciliation and testing. Pinned-clock and exact-template safeguards accepted **without claiming they prove the unexecuted literal RULE-04 or RULE-08 requirements**. GOLD-C reconciliation accepted within P4; full graph halt/resume and draft behaviour remain **P5**. **GOLD-EX-11 remains FAIL / NOT PROVEN.**
- **Effective status boundary:** P4 becomes **`CONDITIONALLY_ACCEPTED_SYNTHETIC` only after** this recording is independently verified, the owner merges PR #46, and exact merged-main CI succeeds. Until then P4 remains **IN_REVIEW**. This is not unconditional PASS, not clinical acceptance, not real-OCR validation and not full P5 acceptance.
- **Recording authorization:** exactly **ONE** documentation-only, append-only commit on the three authorized documentation paths; no production, test, migration, model, policy, contract, fixture, dependency, CI, scanner or P3-handoff modification; no runtime activation, DR-006 persistence, graph, LLM, API, UI, task, notification or P5 implementation; no agent merge, auto-merge, direct main edit or self-approval; **issue #14 remains OPEN** for residual-obligation tracking until a separate owner disposition.
- **Re-verified before recording:** PR #45 merged `2026-11-23T20:42:08Z` by `Muhammed-Fathi` (`merge_commit_sha=96cb275…`, head `679ccb5…`); merged main tree **identical** to `679ccb5` (empty diff); `origin/main` still `96cb275…`; main CI [#45262091228](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45262091228) **SUCCESS**; assessment push CI [#45265811703](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45265811703) **SUCCESS**; assessment PR CI [#45265861635](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45265861635) **SUCCESS**; **50/50 reported CI steps successful across both assessment-head runs**; issue #14 `open` with 19 comments.
- **Precision preserved (appended independent-review clarifications):** fixed-clock fail-closed enforcement does not prove the literal +400-day DR-003 requirement; exact-template and spot-wording assertions are not exhaustive RULE-04 execution; the future assigned tests remain outstanding, not passed; DR-006 denial can produce missing review output and signal loss is not equivalent full functionality; the RB4 owner Windows gate did pass (12 mandatory PASS / 0 FAIL / 1 optional Playwright SKIP, four visible backend skipped markers) and is not unexecuted merely because RB4-12 is a Linux schema guard; recorded CI outcomes are authoritative with direct-log / reported-execution / inferred-attribution distinctions preserved; no clinical, real-OCR, complete public-API or full-agent-runtime acceptance is implied.
- **P5 handoff recorded as planning only:** P5-S0 must first reconcile the merged state and graph contracts — typed state and strict server-derived evidence; immutable run identity and selections; existing F0/F1/F2 and sealed RB3 completion semantics; resuming an unchanged run vs creating a new run after corrected source identity; explicit runtime policy authority before connecting rule execution to a graph; fail-closed handling of DR-006 and other denied persistence outcomes. Graph resume must not be assumed to overwrite or reuse a sealed evaluation after source correction. No P5 branch or implementation.
- **Exact recording inventory:** three append-only paths, **zero deletions** — `docs/phase-reports/P4_FINAL_CLOSURE_ASSESSMENT_20261123.md` (§10), `docs/phase-reports/PHASE_4_REPORT.md` (§41) and this file. No other path changes; cumulative PR #46 inventory unchanged at the same three paths. Recording-head CI is verified after pushing and reported in the PR/final report, not embedded, to preserve the authorized single commit.
- **Status preserved:** P4 **IN_REVIEW** pending verification, owner merge and merged-main CI; issue #14 **OPEN**; full P5 **NOT ACCEPTED**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred / NOT EXECUTED**; DR-006 persistence **prohibited**, genuine end-to-end reachability **unproven in both directions**; runtime demo policy **not activated**; no agent merge, auto-merge, direct main edit or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P5-S0 typed shared state and contract reconciliation delivered (2026-11-23)

- **Owner request and scope:** P5 kickoff, **S0 only** — contract reconciliation plus executable typed shared-state models with schema tests, in **one PR**, as a useful tested foundation for the actual LangGraph workflow rather than an empty module. New branch `arena/a61b8893-p5-s0-typed-state` from the exact owner-merged `main@121e1dbe8580d3d3da19c4c66d2391096d59bc52`. Authorized paths: `backend/app/agents/__init__.py`, `backend/app/agents/state.py`, `backend/tests/p5/test_p5_state.py`, `docs/phase-reports/P5_S0_TYPED_STATE_IMPLEMENTATION_REVIEW_20261123.md`, `docs/phase-reports/PHASE_5_REPORT.md` and this file (append-only). **S1 was not started.**
- **Contract reconciliation (§4 A–F) delivered:** 42-row matrix across identity/versions (real UUIDv4/v5 validation, exact UTC format, `thread_id == run_id` by construction, patient/doctor scope, pinned evaluation clock vs separate authorization/validation clock, immutable selected-source identities with a recomputed fingerprint, and serialized state that authorizes nothing), typed evidence/provenance (F2 DTOs, exact `Decimal` values, self-reported vs doctor-verified trust bound to `verified_by`/`verified_at` and to source refs, corrected-fact lineage, exclusions and incomparable reasons, VI vs DR separation), verification/completion (F1 `proceed`/`halt`/`unavailable` all representable, no stale receipt/state-bool/checkpoint/caller-blocker-count bypass, RB3 sealed completion independent of graph completion, one immutable review evaluation per run, exact replay only, DR-006 whole-invocation denial, runtime policy unapproved), halt/resume (schema-level `resume_unchanged` / `changed_source_identity` / `corrected_source_new_run`; app DB authoritative; checkpoint is replay material only; S2/S4 requirements recorded; **no checkpoint or resume implementation**), typed node trace (four discriminated detail shapes, no raw text/model output/secrets, per-node tool allowlist, finite confidence, bounded attempts) and structural draft/approval shapes (shape validation is not authentication, grounding, execution or authorization).
- **Implementation:** `state.py` (~1750 lines, pydantic 2.14.3) — `extra="forbid"`, `strict=True`, `frozen=True`; real UUID parsing; exact `YYYY-MM-DDTHH:MM:SSZ`; `Decimal(max_digits=10, decimal_places=4)`; 26 closed `StrEnum` vocabularies; 32 models; pure helpers `derived_trust_basis`, `selection_fingerprint`, `derive_task_id`; `SelectedSourceManifest.build()` validates every member through its own `TypeAdapter` **before** digesting (no `model_construct` escape hatch) and re-validates the whole; `SharedGraphState` cross-field validators `_scope_and_uniqueness`, `_evidence_binding`, `_references`, `_lifecycle`, `_gate_binding`; read-only projections `workflow_completed`, `review_evaluation_sealed`, `checkpoint_diverges` that are never serialized and never authoritative. No graph/checkpoint/LLM/API/task/notification import, no I/O, no side effects, no dependency change, no change to any F0/F1/F2/P4 service, schema, migration, route or test.
- **Tests:** `backend/tests/p5/test_p5_state.py` — **124 collected tests** across matrix M01–M20, one-to-one with the owner's twenty required areas, including a subprocess import-side-effect check, a source import/vocabulary scan, OpenAPI and F1 single-source vocabulary equality scans, and a full-population round-trip. Two genuine validator gaps found by the matrix and fixed: a `halt` gate with no blocking issues was accepted, and `model_metadata` accepted an uppercase key and a 200-character value.
- **Executed locally (Linux CPython 3.11.2 — disclosed deviation from CI 3.12; no 3.12 retry attempted):** focused P5-S0 **124 passed / 0 failed / 0 skipped** (0.77 s); P5 + safety + OpenAPI **206 passed**; P5 + P4 + API regression **604 passed**; full backend **2 failed / 1418 passed** in 268.65 s; Ruff lint PASS, Ruff format PASS (149 files); Alembic smoke PASS (head `0008_p4_rb3_review_persistence`); OpenAPI PASS (17 paths / 18 operations / 43 schemas). **Collection measured:** current **1420** / P3 **443** / P5 **183**; base re-measured in a detached worktree at `121e1dbe…` **1294** / **443** / **59**; delta **+126** = 124 new P5-S0 tests + 2 new parametrized P2 scope-guard cases that pass.
- **Both full-suite failures are guards colliding with the authorized scope; neither was weakened.** (1) `test_p2_scope_guards.py::test_no_later_phase_module_exists` asserts `backend/app/agents/` must not exist, contradicting the authorized P5-S0 paths — **new blocking owner decision D-14**. (2) `test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` — the collection guard moved 1294 → 1420 while P3 stayed 443; `PHASE_3_WINDOWS_ACCEPTANCE.md` is **not** an authorized path, so the append-only collection note needs separate owner authorization (**D-09**).
- **Not executed:** Windows PowerShell / `test_all.ps1` (owner laptop only — **no Windows claim**); LangGraph/Ollama/LLM/GPU/browser checks (not applicable to this slice); exact-head GitHub Actions and frontend build (read from CI after push, reported in the PR, not asserted here).
- **Owner decisions consolidated (14):** D-01 `GateDetail.decision` two-valued vs F1 `unavailable`; D-02 `ProvenanceRef.raw_text`; D-03 `incomparable_reason` union incl. `stale_baseline`; D-04 F2 365-day vs RB1 90-day window; D-05 `TASK_NAMESPACE` for uuid5 task ids; D-06 `prompt_version` format; D-07 JSON-number acceptance for exact decimals; D-08 `model_copy` bypass / re-validation at trust boundaries; D-09 collection-guard pairing; D-10 `CheckpointRef.claimed_status` non-authoritative for S4; D-11 schema-enforced `trust_basis` derivation; D-12 `verification_issues` must mirror the gate; D-13 `doctor_verified` + `validation=rejected` representable but labelled; **D-14 P2 scope guard vs authorized `backend/app/agents/` package (blocking)**.
- **Status preserved:** P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; P4 **`CONDITIONALLY_ACCEPTED_SYNTHETIC`**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred / NOT EXECUTED**; DR-006 persistence **prohibited**; runtime demo policy **not activated / unapproved**. No LangGraph graph, tool adapter, checkpoint, interrupt, resume, LLM, API, UI, approval execution, task or notification. One draft PR; **no agent merge, no auto-merge, no direct main edit, no self-approval**; stopped for independent engineering review. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P5-S0 exact-head CI recorded (2026-11-23)

- **Implementation head `e70d2ea9b5cc6446e06f336b40e83bdc3df73052` (PR #47, DRAFT, OPEN).** Push run [#45277330559](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277330559) and pull_request run [#45277408623](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/45277408623) both COMPLETED / **FAILURE**, and both failures are confined to the same single step.
- **Frontend (Node 22): SUCCESS** in both runs.
- **Backend (Python 3.12) step-level truth:** `Set up job`, `Check out the repository`, `Set up Python 3.12`, `Install hash-locked development dependencies`, `Show resolved versions`, **`Ruff lint` SUCCESS**, **`Ruff format check` SUCCESS**, **`Backend tests` FAILURE**; `Alembic migration smoke test`, `Generated OpenAPI contract check` and `Repository secret and artefact scan` **SKIPPED — not reached**, so no CI claim is made for them. Those three checks are covered by the local executions recorded above instead.
- **Failing-test attribution:** the CI job log could not be downloaded in this sandbox (the logs endpoint redirects to a blob host outside the permitted egress allowlist), so the failing test identity was **not read from CI**. It is **inferred** from the byte-identical local run at the same clean tree, where exactly `test_p2_scope_guards.py::test_no_later_phase_module_exists` and `test_windows_ocr_acceptance.py::test_handoff_test_count_matches_the_suite_it_describes` fail and nothing else does. Re-verified at the committed HEAD with a clean `git status`: **2 failed in 3.90 s**, same two tests.
- **Not a green run and not presented as one.** Both failures are the documented guard collisions (**D-14** P2 `agents`-package guard; **D-09** collection-count guard), neither of which was weakened. A green exact-head run requires an owner decision on D-14 and D-09 first.
- **Status preserved:** P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; P4 **`CONDITIONALLY_ACCEPTED_SYNTHETIC`**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred / NOT EXECUTED**; DR-006 persistence **prohibited**; runtime demo policy **not activated / unapproved**. No P5-S1 work started. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P5-S0 Round 2 — owner authorization recorded before the exceptional edits (2026-11-24)

- **Authorization verified, not assumed:** repository comment [`7122838674`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/47#issuecomment-7122838674), author `Muhammed-Fathi`, `author_association=OWNER`, created `2026-11-24T05:19:23Z`, marker `APPROVE-P5-S0-D09-D14-BOUNDED-COMPATIBILITY`, issued at reviewed HEAD `f6394f1c6e670562dae74bafef5190c396c629d2`. It authorizes **two narrowly scoped compatibility exceptions only** — D-14 (P2 scope guard, exact-path allowlist for `backend/app/agents/__init__.py` and `backend/app/agents/state.py`) and D-09 (append-only collection pairing `**1420 collected**, of which **443** are the P3 suite` in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`) — and states verbatim: *"Remeasure the final test collection and record both owner authorizations in `PHASE_PROGRESS.md` before editing the exceptional paths"* and *"If the measured collection pairing changes, obtain fresh explicit authorization before editing the P3 handoff."* No earlier P3/P4 authorization was reused; P3/P4 authorizations do not cover these paths.
- **Collection remeasured on the current tree (before any exceptional-path edit):** whole backend **1446**, P3 **443**, P5 **209** (previous round: 1420 / 443 / 183; base at `121e1dbe…`: 1294 / 443 / 59). The **D-09 pairing therefore changed**: 1446 ≠ the authorized 1420, because the Round-2 rewrite of `backend/tests/p5/test_p5_state.py` carries **150** collected tests instead of 124 (the P3 suite itself is unchanged at 443 and no test was deleted anywhere). Per the owner's own condition above, the P3 handoff is **NOT edited in this round**; the stale authorized literal would also be false against the live collection and would fail the very guard it is meant to satisfy. **Fresh explicit owner authorization for the 1446 / 443 pairing is required before D-09 can be executed.** D-09 is recorded here as *authorized-but-not-executed*, not as closed.
- **D-14 is executed under the verified authorization** (the pairing condition attaches only to D-09). The edit replaces the obsolete blanket `assert not (BACKEND_APP / "agents").exists()` with a strict exact-path allowlist of the two authorized S0 modules; `backend/app/llm`, graph, orchestrator, tool adapters, checkpoint and every other module or sub-package under `agents` remain forbidden, and all other guards in the file are untouched. Rejection of any non-allowlisted `agents` path is demonstrated by a test in the same authorized file.
- **Round-2 consolidated revision content (uncommitted at the time of this record):** `backend/app/agents/state.py` and `backend/tests/p5/test_p5_state.py` rewritten to close review findings R01–R07 and owner decisions D-01…D-14. Focused P5-S0 suite at this point: **150 passed / 0 failed** (Linux CPython 3.11.2, disclosed deviation from CI 3.12). Full battery, exact-head CI and the consolidated commit are recorded in the entries that follow.
- **Status preserved:** P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; P4 **`CONDITIONALLY_ACCEPTED_SYNTHETIC`**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred / NOT EXECUTED**; DR-006 persistence **prohibited**; runtime demo policy **not activated / unapproved**. No P5-S1 work. No agent merge, auto-merge, direct main edit or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

## P5-S0 Round 2 — fresh D-09 authorization for the changed pairing (2026-11-24)

- **Why fresh authorization was needed:** the verified comment [`7122838674`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/47#issuecomment-7122838674) authorizes the literal `**1420 collected**, of which **443** are the P3 suite` and states verbatim *"If the measured collection pairing changes, obtain fresh explicit authorization before editing the P3 handoff."* The pairing did change: whole backend **1447** (1420 + 23 net new collected P5-S0 tests from the Round-2 rewrite of `backend/tests/p5/test_p5_state.py`, 124 → 150, + 1 new D-14 rejection test in `backend/tests/p2/test_p2_scope_guards.py`, + 3 parametrized `test_application_modules_are_typed` cases that now cover `backend/app/agents/__init__.py` and `backend/app/agents/state.py`), P3 unchanged at **443**, P5 **209**. No test was deleted and no P3 test was added or removed.
- **Fresh authorization obtained before the edit:** the repository owner, in this session, selected the explicit option *Authorize the append-only edit* for exactly `**1447 collected**, of which **443** are the P3 suite` in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`, append-only with historical P3/Windows/OCR evidence preserved verbatim, **collection evidence only**. Channel disclosed honestly: this fresh D-09 authorization was given in the working session in reply to a direct question, **not** as a new signed GitHub comment; comment `7122838674` remains the authority for D-14 and for the original 1420/443 pairing.
- **Scope of the edit executed under it:** one append-only insertion of the paired literal above. No other line of the handoff changes; no passed-test count, no Windows-acceptance statement and no new acceptance claim is made by that note. The legacy guard `test_handoff_test_count_matches_the_suite_it_describes` is untouched and is re-run after the edit.
- **Status preserved:** P5 **IN_REVIEW / NOT ACCEPTED**; issue #14 **OPEN**; P4 **`CONDITIONALLY_ACCEPTED_SYNTHETIC`**; GOLD-EX-11 **FAIL / NOT PROVEN**; RB3-75..77 **deferred / NOT EXECUTED**; DR-006 persistence **prohibited**; runtime demo policy **not activated / unapproved**. No P5-S1 work. No agent merge, auto-merge, direct main edit or self-approval. **ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**
