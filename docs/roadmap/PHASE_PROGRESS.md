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
