# AI Doctor Follow-Up Agent

**Multi-Agent Clinical Workflow Assistant — DEPI Graduation Project**

Doctor-centered educational demonstration. The application will take **synthetic** periodic patient measurements and mock PDF reports, extract grounded facts, compare them with history, draft source-cited summaries for the doctor, and organize doctor-approved in-app follow-up tasks. Self-reported check-ins are labelled as such and are never presented as doctor-verified.

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**
> Academic prototype with fictitious data only. No autonomous diagnosis, treatment, prescribing, emergency
> triage, or patient messaging. A human doctor approves every follow-up action. No real patient data may
> ever be used with this project.

## Status (2026-11-18)

| Phase | Status | Evidence |
|---|---|---|
| **P0 — Governance and specification baseline** | **PASS / merged** | [Phase 0 report](docs/phase-reports/PHASE_0_REPORT.md), PR #2 |
| **P1 — Foundation and reproducible startup** | **PASS / merged** | [Phase 1 report](docs/phase-reports/PHASE_1_REPORT.md), PR #4 |
| **P2 — Synthetic patient domain and role-scoped API** | **PASS / merged** | [Phase 2 report](docs/phase-reports/PHASE_2_REPORT.md), PR #7 |
| **P3 — Synthetic document ingestion, OCR and doctor verification** | **IN_REVIEW / BLOCKED** | Draft [PR #10](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10); [Windows E1–E3 evidence](docs/phase-reports/P3_E1_E3_V112_WINDOWS_EVIDENCE.md) and [root-cause handoff](docs/phase-reports/P3_E1_E3_V112_PROBE_ROOT_CAUSE.md) |
| **P4–P8** | **TODO / not started** | Do not begin until the prior phase is owner-accepted |

**Accepted implementation on `main`: P0–P2.** P3 implementation and R21 work exist on **unmerged branches**. Owner Windows v1.1.2 `plan_only` PASSED but `probe_only` returned exit **13** (historical v1.1.2 diagnostic bugs). The revised and independently audited v1.1.3 harness now passed **both** real Windows `plan_only` **and** `probe_only` (exit 0 each); see [v1.1.3 Windows probe evidence](docs/phase-reports/P3_E1_E3_V113_WINDOWS_PROBE_ONLY_EVIDENCE.md). **Only `canonical_baseline` (3 synthetic specimens) is authorized next and NOT YET RUN**. `GOLD-EX-11` remains **FAIL / NOT PROVEN**. No exploratory/holdout/rules freeze, P3 release/merge or P4 work is authorized.

For current status and exact owner decisions, use [PHASE_PROGRESS.md](docs/roadmap/PHASE_PROGRESS.md) and the [MASTER_PLAN.md](docs/roadmap/MASTER_PLAN.md) status index. Older P1-only setup examples and descriptions below are historical foundation documentation, not proof of P3 acceptance.

### What you can run today

```powershell
# Windows, from the repository root
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\preflight.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1
Invoke-RestMethod http://127.0.0.1:8000/health
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1
```

Full instructions, prerequisites and troubleshooting:
[Windows setup guide](docs/runbooks/WINDOWS_SETUP.md).

## Start here

1. [Windows setup guide](docs/runbooks/WINDOWS_SETUP.md) — install, run, test, rollback (P1).
2. [Phase 1 report](docs/phase-reports/PHASE_1_REPORT.md) — what was implemented and exactly what was executed.
3. [Phase 0 report](docs/phase-reports/PHASE_0_REPORT.md) — the governance baseline and its review history.
4. [MVP specification](docs/contracts/MVP_SPEC.md) — actors, user stories, requirements, non-goals.
5. [Architecture baseline](docs/architecture/ARCHITECTURE.md) — diagram, layers, role/permission matrix, ADR-0001..0006.
6. [Shared state + graph contract](docs/contracts/STATE_AND_GRAPH_CONTRACT.md) — agents, transitions, typed trace decisions, checkpoint vs app-DB reconciliation, interrupt/resume, idempotency.
7. [Tool contracts](docs/contracts/TOOL_CONTRACTS.md), [API contract](docs/contracts/API_CONTRACT.md) and [OpenAPI proposal](docs/contracts/openapi.phase0.yaml).
8. [Data dictionary](docs/contracts/DATA_DICTIONARY.md) and [extraction/provenance contract](docs/contracts/EXTRACTION_PROVENANCE.md).
9. [Clinical safety](docs/clinical-safety/CLINICAL_SAFETY.md), [demo review rules](docs/clinical-safety/DEMO_REVIEW_RULES.md), [threat model](docs/clinical-safety/THREAT_MODEL.md).
10. [Evaluation matrix](docs/evaluation/EVALUATION_MATRIX.md), [gold fixtures](docs/evaluation/GOLD_FIXTURES.md), [traceability](docs/evaluation/TRACEABILITY_MATRIX.md), [benchmark plan](docs/evaluation/LOCAL_BENCHMARK_PLAN.md).
11. [Demo scenarios](docs/demo/DEMO_SCENARIOS.md), [dependency verification](docs/contracts/DEPENDENCIES.md).

Governance: [AGENTS.md](AGENTS.md) (agent rules) · [MASTER_PLAN.md](docs/roadmap/MASTER_PLAN.md) (roadmap) ·
[PHASE_PROGRESS.md](docs/roadmap/PHASE_PROGRESS.md) (gate tracker).

## The one workflow in scope

Patient check-in + optional document upload → intake validation → text-first extraction with a bounded,
trace-recorded OCR-retry path → **verification issues (`VI-*`) and doctor correction of ambiguous facts** →
comparison against the most recent prior admissible value (with trust labels) → deterministic `DEMO_ONLY`
review prompts (`DR-*`, verified evidence only) → cited draft summary (local Ollama, or a clearly labelled
deterministic fallback) → **doctor approve / edit / reject** → in-app follow-up task + notification + audit
trail, committed exactly once. Rule evaluation uses an injected `as_of_utc`, so demo expectations do not
drift with the calendar.

Five bounded agent nodes (`medical_document`, `patient_monitoring`, `review_priority`,
`doctor_communication`, `follow_up`) run inside **one** LangGraph graph. Only the drafting node may call a
model. See [ADR-0006](docs/architecture/ADR-0006-five-bounded-agents-single-graph.md).

## What this project deliberately does not do

Diagnosis, risk scoring, triage, treatment or dosing advice, patient-facing interpretation, external
messaging (SMS/email/WhatsApp/push), EHR/FHIR integration, real patient data, cloud inference, paid APIs,
clinical/compliance claims, or autonomous approval. Full list: [MVP_SPEC §6](docs/contracts/MVP_SPEC.md#6-non-goals-mvp-binding).

## Stack

Implemented in P1 and pinned to exact versions: FastAPI, Pydantic, pydantic-settings, Uvicorn,
SQLAlchemy, Alembic, pytest, Ruff, PyYAML (backend); React, TypeScript, Vite, Vitest,
Testing Library, ESLint (frontend). Python 3.12 and Node 22+ (Vite 7 engine constraint).

**Phase-specific:** P3 uses local PDF/OCR components under review and has not passed its real-engine diagnostic gate; P5 LangGraph/Ollama remains planned, with deterministic fallback; optional Playwright E2E remains a later testing scope. Dependencies and execution claims are version-/branch-specific and must be checked against the relevant phase reports.

Registry metadata, licenses, hashes and lock strategy are recorded in
[docs/contracts/DEPENDENCIES.md](docs/contracts/DEPENDENCIES.md) and
[the Phase 1 report](docs/phase-reports/PHASE_1_REPORT.md) §5.

## Repository layout

```text
AI-Doctor-FollowUp-Agent/
|-- README.md / AGENTS.md / .gitignore / .env.example / pyproject.toml
|-- docs/                  roadmap, architecture, contracts, clinical-safety,
|                          evaluation, demo, runbooks, phase-reports, arena
|-- backend/
|   |-- app/               main.py, api/, core/, db/, schemas/
|   |-- migrations/        Alembic environment + baseline revision
|   `-- tests/             pytest suites (health, version, openapi, db, safety, scripts, CI)
|-- frontend/
|   |-- src/               app/, components/, pages/, services/, styles.css
|   `-- tests/             Vitest component tests + Playwright smoke spec
|-- requirements/          hash-pinned runtime and dev locks (generated by uv)
|-- scripts/
|   |-- powershell/        preflight, setup, start, stop, test_all
|   `-- python/            check_openapi, check_alembic_smoke, scan_repository
|-- data/runtime/          gitignored: SQLite DB, logs, PID/state files
`-- .github/workflows/     ci.yml (backend on 3.12, frontend on Node 22)
```

The tree above was documented during P1. P2 synthetic data and patient/auth modules are accepted; P3 document modules and acceptance diagnostics are under review on unmerged branches. See the phase tracker rather than inferring current implementation from the old schematic.

## Verification honesty

Phase 1 executed, in this session: the backend pytest suite, Ruff lint and format checks, the Alembic
upgrade/downgrade/upgrade cycle, the generated OpenAPI contract check, the repository secret/artefact scan,
Vitest, ESLint, the TypeScript typecheck and the production Vite build; plus live HTTP checks of `/health`
and `/version` against a running Uvicorn process and through the Vite dev-server proxy.

**Not executed anywhere:** the Windows PowerShell scripts (no PowerShell/Windows in the authoring
environment), a GitHub Actions run (only observable after the branch is pushed) and the Playwright browser
smoke test (browser download blocked). The Python checks ran on Python **3.11.2**, not the 3.12 target,
because the sandbox could not obtain a 3.12 interpreter — CI is configured to run the same suite on 3.12.

Exact commands, exit codes and trimmed output are in
[the Phase 1 report](docs/phase-reports/PHASE_1_REPORT.md). Nothing else was run, and no claim of clinical
safety, medical accuracy, regulatory compliance or production readiness is made anywhere in this repository.
