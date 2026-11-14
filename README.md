# AI Doctor Follow-Up Agent

**Multi-Agent Clinical Workflow Assistant — DEPI Graduation Project**

Doctor-centered educational demonstration. The application will take **synthetic** periodic patient measurements and mock PDF reports, extract grounded facts, compare them with history, draft source-cited summaries for the doctor, and organize doctor-approved in-app follow-up tasks. Self-reported check-ins are labelled as such and are never presented as doctor-verified.

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**
> Academic prototype with fictitious data only. No autonomous diagnosis, treatment, prescribing, emergency
> triage, or patient messaging. A human doctor approves every follow-up action. No real patient data may
> ever be used with this project.

## Status

| Phase | Status | Notes |
|---|---|---|
| **P0 — Governance and specification baseline** | **PASS** | Merged via PR #2, merge commit `442256606fd2465439409cc9b4d42f1bec09a723`, owner-approved 2026-11-14. |
| **P1 — Foundation and reproducible startup** | **IN_REVIEW** | Implementation PR open against `main`. Adds the FastAPI `/health` + `/version` service, the React + TypeScript + Vite status page, SQLite + Alembic baseline, hash-pinned Python locks, five Windows PowerShell scripts, and CI. Evidence and non-executed checks: [Phase 1 report](docs/phase-reports/PHASE_1_REPORT.md). |
| P2–P8 | TODO | Must not start before P1 is accepted. |

Phase 1 delivers the runnable foundation only. There is **no** patient record, authentication, document
upload, OCR, monitoring, review rule, agent workflow or follow-up task yet, and `/health` reports the OCR and
model dependencies as `not_configured` rather than pretending they exist.

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

Planned for later phases and **not installed**: LangGraph + a local Ollama model with a labelled
fallback (P5), `pypdf` + Tesseract OCR (P3), Playwright browser E2E (P6/P7).

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

`data/synthetic/` and the P2+ application modules do not exist yet.

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
