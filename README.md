# AI Doctor Follow-Up Agent

**Multi-Agent Clinical Workflow Assistant — DEPI Graduation Project**

Doctor-centered educational demonstration. The application will take **synthetic** periodic patient measurements and mock PDF reports, extract grounded facts, compare history, draft source-cited doctor summaries, and organize doctor-reviewed follow-up tasks.

> **Important:** Academic prototype, synthetic records only. **NOT FOR CLINICAL USE.** No autonomous medical diagnosis, treatment or emergency triage. Human clinician approval is mandatory for follow-up actions.

## Start here
- [Master execution plan](docs/roadmap/MASTER_PLAN.md)
- [Architecture baseline](docs/architecture/ARCHITECTURE.md)
- [Arena Phase 0 prompt](docs/arena/ARENA_PHASE_0_PROMPT.md)

## Progress
**Planning draft v0.1. No implementation phase is accepted or completed.** Arena will start with Phase 0 documentation and governance; subsequent PRs follow the plan after owner approval.

## Proposed stack
LangGraph + local Ollama, FastAPI, SQLite, pypdf/Tesseract, React/TypeScript/Vite, pytest/Vitest/Playwright. Local Windows development; no paid APIs or hosting required for the demo.