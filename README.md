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
| **P0 — Governance and specification baseline** | **IN_REVIEW** | Documentation-only PR submitted; review rounds 1–3 addressed in follow-up commits (R01–R07 + ADR-0006 depth; R08–R11 contract reconciliations and test-realism fixes; R12–R14 mapping-version type, attempt-DTO projection and the one-measurement-per-document association rule). Owner re-review pending. Not accepted, not merged. |
| P1–P8 | TODO | Must not start before P0 is approved |

No application code exists yet, and no test, benchmark, or demo has been executed. What exists is a
reviewable specification set: scope, architecture, ADRs, state/tool/API/data contracts, clinical-safety
boundaries, a deterministic demo rule policy, gold fixtures, an evaluation matrix, and three demo stories.
See [Phase 0 report](docs/phase-reports/PHASE_0_REPORT.md) for exactly what was and was not executed.

## Start here (review path for P0, ~25 minutes)

1. [Phase 0 report](docs/phase-reports/PHASE_0_REPORT.md) — changed files, commands, gaps, open questions.
2. [MVP specification](docs/contracts/MVP_SPEC.md) — actors, user stories, requirements, non-goals.
3. [Architecture baseline](docs/architecture/ARCHITECTURE.md) — diagram, layers, role/permission matrix.
4. [Decision records](docs/architecture/ARCHITECTURE.md#10-architecture-decisions) — six ADRs.
5. [Shared state + graph contract](docs/contracts/STATE_AND_GRAPH_CONTRACT.md) — agents, transitions, typed trace decisions, checkpoint vs app-DB reconciliation, interrupt/resume, idempotency; `VI-*` (pre-verification) vs `DR-*` (post-verification) outputs.
6. [Tool contracts](docs/contracts/TOOL_CONTRACTS.md) and [API contract](docs/contracts/API_CONTRACT.md) + [OpenAPI proposal](docs/contracts/openapi.phase0.yaml).
7. [Data dictionary](docs/contracts/DATA_DICTIONARY.md) and [extraction/provenance contract](docs/contracts/EXTRACTION_PROVENANCE.md).
8. [Clinical safety](docs/clinical-safety/CLINICAL_SAFETY.md), [demo review rules](docs/clinical-safety/DEMO_REVIEW_RULES.md), [threat model](docs/clinical-safety/THREAT_MODEL.md).
9. [Evaluation matrix](docs/evaluation/EVALUATION_MATRIX.md), [gold fixtures](docs/evaluation/GOLD_FIXTURES.md), [traceability](docs/evaluation/TRACEABILITY_MATRIX.md), [benchmark plan](docs/evaluation/LOCAL_BENCHMARK_PLAN.md).
10. [Demo scenarios](docs/demo/DEMO_SCENARIOS.md) and [dependency verification](docs/contracts/DEPENDENCIES.md).

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

## Proposed stack (versions pending verification on the owner machine)

LangGraph + local Ollama (with labelled fallback), FastAPI + Pydantic + SQLAlchemy/Alembic, SQLite,
`pypdf` + Tesseract OCR, React + TypeScript + Vite, pytest/Vitest/Playwright, GitHub Actions (short jobs).
Local Windows development; no paid APIs or hosting required for the demo.

Registry metadata for every planned dependency, its license, and every item still unverified is recorded in
[docs/contracts/DEPENDENCIES.md](docs/contracts/DEPENDENCIES.md). Nothing is pinned yet — pinning happens
in P1 with lockfiles after a real install.

## Repository layout (target)

```text
AI-Doctor-FollowUp-Agent/
├── README.md · AGENTS.md · .gitignore
├── docs/            roadmap/ · architecture/ · contracts/ · clinical-safety/ · evaluation/ · demo/ · phase-reports/ · arena/
├── backend/         (P1+) FastAPI app, services, agents, llm, tests
├── frontend/        (P1+) React app + tests
├── data/synthetic/  (P3+) synthetic fixtures + gold cases   |  data/runtime/ gitignored
├── scripts/         (P1+) PowerShell + python helpers
└── .github/workflows/ (P1+) CI
```

Only `docs/` exists today. Phase 0 is documentation-only by design.

## Verification honesty

Phase 0 executed **documentation-level checks only**: cross-file link/reference resolution, requirement-ID
coverage, OpenAPI structural validation, and a prohibited-claim wording scan. Their exact commands and
results are in the [Phase 0 report](docs/phase-reports/PHASE_0_REPORT.md).

Nothing else was run: there is no backend, no frontend, no database, no OCR, no model, no benchmark, no
browser test, and no Windows PowerShell run. Windows/Ollama/Tesseract checks are listed as **not executed —
requires owner Windows laptop**. Passing synthetic tests could never establish clinical safety, and no such
claim is made anywhere in this repository.
