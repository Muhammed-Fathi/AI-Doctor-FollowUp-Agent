# Phase Progress Tracker

> Current status: **P0 IN_REVIEW** — review `5904454222` (round 1) returned CHANGES REQUIRED for findings
> P0-R01…P0-R07 plus the ADR-0006 agentic-depth concern; those were resolved in documentation. Review
> `5904505998` (round 2) then raised `P0-R08…P0-R11` and three test-realism points (typed trace, app-DB vs
> checkpoint recovery, verified-fact → observation mapping, self-reported admissibility, mocked-vs-live OCR,
> invented `VI-002` count, PR description). All are addressed in a further documentation-only commit on the
> same PR. Owner re-review pending. Updated: 2026-11-14.
>
> A phase becomes `PASS` only after PR review, evidence verification, the local PowerShell gate (when
> applicable), explicit owner approval, and merge. The implementing agent never sets `PASS` and never merges
> (`AGENTS.md` §2).

| Phase | Topic | Status | PR | Merge SHA | Test Evidence | Owner Approval |
|---|---|---|---|---|---|---|
| P0 | Governance / specifications | **IN_REVIEW** | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) | — | Documentation + OpenAPI checks only (rounds 2–3, see `docs/phase-reports/PHASE_0_REPORT.md` §10–§11); no application tests exist | Pending — rounds 1 and 2 changes requested; round 3 submitted |
| P1 | Foundation / reproducible startup | TODO | — | — | Not run | Pending |
| P2 | Patient data + role-based API | TODO | — | — | Not run | Pending |
| P3 | Document ingestion + OCR verification | TODO | — | — | Not run | Pending |
| P4 | Monitoring + demo review rules | TODO | — | — | Not run | Pending |
| P5 | LangGraph agents + Ollama + approval | TODO | — | — | Not run | Pending |
| P6 | Doctor/patient UI + follow-up tasks | TODO | — | — | Not run | Pending |
| P7 | Robustness, safety and evaluation | TODO | — | — | Not run | Pending |
| P8 | Demo + final handoff | TODO | — | — | Not run | Pending |

## P0 evidence (as submitted)

| Item | Value |
|---|---|
| Scope | Documentation and governance only — no application, dependency, database, migration, or model code |
| Deliverables | 12/12 addressed; see `docs/phase-reports/PHASE_0_REPORT.md` §2 |
| Executed checks | Cross-file reference resolution, requirement-ID coverage, OpenAPI structural validation, prohibited-claim scan, secret/runtime-artifact scan |
| Not executed | Any backend/frontend test, OCR, model call, benchmark, browser E2E, Windows PowerShell gate, migration |
| Owner-laptop required | Windows PowerShell scripts, Tesseract/Poppler install, Ollama model benchmark, offline demo |
| PR | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) — opened 2026-11-14, base `main` @ `7d2ef73`, not merged |
| Review round 1 (`5904454222`) | 7 findings + 1 ADR concern, all resolved in documentation; content commit `81df966b2fe80ab842f3405b32cfabc2f1b3a5e7` |
| Review round 2 (`5904505998`) | `P0-R08` typed trace payloads + typed extraction attempts (51 new OpenAPI properties), `P0-R09` app-DB source-of-truth and restart reconciliation (`RESUME-04/05`), `P0-R10` closed fact → observation mapping (`REQ-DATA-05`, `MAP-01`), `P0-R11` observation admissibility predicate (`TRUST-02`); test realism: mocked `AD-01` vs measured `OCR-LIVE-01`, `VI-002` `{count}` declared from 3 candidate facts, PR description rewritten; content commit `b3605ec484a38b15aec5bb153586fecda187ea1d` |
| Blocks P1 until | Owner re-reviews the resolutions, confirms the six ADRs (incl. amended ADR-0006), approves the demo rule parameters, and merges the PR |

Do not prefill future pass results, test counts, or metrics. When a phase completes, record the PR URL,
exact base/head commits, commands with real output, and the merge SHA.

## Required evidence for every phase

- Scope and acceptance criteria
- PR URL, exact base/head and changed-file list
- Tests: name/command/pass/fail/skipped/not-run and the real execution context
- Local PowerShell result (if applicable)
- Security and safety changes
- Known limitations
- Owner decision and merged commit SHA
