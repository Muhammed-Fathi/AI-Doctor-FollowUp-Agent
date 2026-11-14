# Phase Progress Tracker

> **Current status: P0 PASS; P1 PASS (owner-approved and merged 2026-11-14). P2 IN REVIEW — implemented, scope-authorized, awaiting independent review and owner Windows verification.**
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
> **Last accepted phase:** P1 — Foundation and Reproducible Startup, PR [#4](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/4), status `PASS`. Windows verification at `eec6642`, final docs-only PR head `58a0652`; merge commit `2c85db4d9fe9f17080146d12adfbd030a05cc75d`. Owner approved on 2026-11-14.
>
> **Current phase:** P2 — Patient data and role-based API, PR [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) (draft), status **IN REVIEW**. File-scope authorization recorded verbatim below. P2 is **not** PASS and is **not** merged.
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
| P2 | Patient data + role-based API | **IN REVIEW** | [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7) (draft) | — | Sandbox Python 3.11: `355 passed` (125 P1 + 230 P2), `ruff check`/`format` clean, OpenAPI gate `PASS (11 paths / 12 operations, 22 schemas)`, `check_alembic_smoke` PASS in states `head`/`p1`/`base`, secret scan PASS. **CI independently verified by the reviewer on two heads:** run [`43625331149`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625331149) at `dbaf938` and run [`43625989736`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/actions/runs/43625989736) at docs-only head `6d54ede` — Backend Python 3.12 SUCCESS and Frontend Node 22 SUCCESS in both (the implementer's own Actions/Checks read returned 403 *Resource not accessible by integration*, retained as an observer limitation, **not** a CI failure). **Windows PowerShell gate: PENDING — owner.** | Pending |
| P3 | Document ingestion + OCR verification | TODO | — | — | Not run | Pending |
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

### P2 status

**IN REVIEW — not PASS, not merged, not approved.** Acceptance requires
independent technical review, the owner's Windows gate and a separate owner
decision after the PR is ready.

See `docs/phase-reports/PHASE_2_REPORT.md` for evidence, limitations and rollback.

---

## Next Authorized Workflow

1. P0 and P1 accepted; preserve the verified merge SHAs and owner decision records.
2. Synchronize the owner's local `main` from `origin/main` after checking for uncommitted changes.
3. Begin P2 planning against the merged foundation in a new scoped branch/PR; follow P0 governance and synthetic-data constraints.
4. Carry forward the deferred license/public-distribution decision, `DEPENDENCIES.md` sync, and optional Playwright smoke without claiming they passed.
5. Do not mark P2 `PASS` without its own evidence, owner approval, and merge.

**Current accepted baseline:** P0 governance plus **P1 foundation (PASS)**.

**Current implementation milestone (IN REVIEW):** P2 — Patient data domain and role-scoped API, PR [#7](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/7).

**Project classification:** Educational, synthetic-data, local-first multi-agent workflow assistant.

**NOT FOR CLINICAL USE.**
