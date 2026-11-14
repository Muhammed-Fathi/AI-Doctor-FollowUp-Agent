# Arena Agent Task — Phase 0 ONLY

You are implementing a **documentation and governance foundation**, not the product code. Read `docs/roadmap/MASTER_PLAN.md` and `docs/architecture/ARCHITECTURE.md` end-to-end before changing files.

## Mission
Prepare a rigorous, internally consistent, executable Phase 0 specification for the `AI-Doctor-FollowUp-Agent` DEPI graduation project. This is a local, zero-paid-API, doctor-centered workflow assistant with synthetic data. All medical decisions remain with the doctor.

## Allowed changes
- `README.md`, `AGENTS.md`
- `docs/roadmap/{MASTER_PLAN,PHASE_PROGRESS}.md`
- `docs/architecture/{ARCHITECTURE,ADR-*.md}`
- `docs/contracts/*`
- `docs/clinical-safety/*`
- `docs/evaluation/*`
- `docs/demo/*`
- `docs/phase-reports/PHASE_0_REPORT.md`
- `.gitignore` (only if necessary to prevent accidental commits)

## Required deliverables
1. Signed-off technical spec for one routine outpatient follow-up, actors, exact MVP user stories and clear non-goals.
2. Finalized architecture diagram and role/permission matrix.
3. Five bounded agent responsibilities + typed shared-state JSON/Pydantic contract proposal + allowed tool contracts + graph transitions, including checkpoint, interrupt/resume and retry/idempotency policy.
4. Database/data-dictionary draft + API/OpenAPI endpoint proposal and error cases.
5. Document ingestion/OCR pipeline and provenance + verification status contract.
6. Deterministic **synthetic demo-only** review rule design with no unsupported clinical threshold claims.
7. LLM/Ollama adapter design; mock/fallback honesty and local GPU/CPU benchmark plan (do not claim tests without execution).
8. Evaluation matrix: exact synthetic gold fixtures, negative/security tests, traceability to requirements, evidence, acceptance criteria.
9. 3 precise demo scenarios: stable, changed, uncertain OCR; no real patient data.
10. `docs/roadmap/PHASE_PROGRESS.md` with statuses P0-P8. Leave P0 `IN_REVIEW`, not `PASS`, until owner reviews and approves. All other phases `TODO`.
11. `AGENTS.md` enforcing one-phase-per-PR, no autonomous diagnosis/prescribing/real messages, no direct `main` edits, no fabricated verification and no merge by the agent.
12. Phase 0 review report: changed files, exact review checks performed, unresolved assumptions, known risks and P1 entry criteria.

## Constraints
- **DO NOT** implement backend/frontend/agents/database code, train or download models, upload real patient files, invent medical guidance, use paid services, spend quota, merge PRs, mark P0 accepted, or auto-start Phase 1.
- The included plan/architecture are *drafts*, and factual claims should be checked against up-to-date official documentation. Record dependency/platform versions only when verified.
- Do not treat "five agents" as five costly independent LLMs; design bounded components inside a single orchestrated graph.
- In the Phase 0 report, distinguish **design verified**, **tests executed**, **not executed**, **requires owner Windows laptop**.
- Keep the scope lean and buildable. If requirements conflict, document the decision in an ADR and surface it for review.

## Git process
1. Start from latest `main` on a dedicated `feat/p0-governance-baseline` or the assigned Arena branch (do not overwrite a shared branch).
2. Make docs-only changes; create a single PR into `main` with title `P0: Doctor Follow-Up governance and architecture baseline`.
3. Run docs consistency/lint checks actually available; clearly flag anything not run.
4. In PR body include concise implementation summary, safety boundary review, exact changed filenames, commands+results, unanswered issues, and owner review checklist.
5. Stop. Do **not** merge or start P1.

## Final reporting template
- Branch / PR URL / base commit / head commit
- Deliverables complete / incomplete
- File-level changes
- Commands executed + actual results
- Risk/safety concerns, assumptions requiring owner input
- Definition-of-Done gate evidence
- Next action explicitly **P0 owner review**, not P1 implementation