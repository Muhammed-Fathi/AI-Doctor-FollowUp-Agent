# Phase Progress Tracker

> Current status: **P0 IN_REVIEW** — a documentation-only baseline has been submitted for owner review.
> Updated: 2026-11-14.
>
> A phase becomes `PASS` only after PR review, evidence verification, the local PowerShell gate (when
> applicable), explicit owner approval, and merge. The implementing agent never sets `PASS` and never merges
> (`AGENTS.md` §2).

| Phase | Topic | Status | PR | Merge SHA | Test Evidence | Owner Approval |
|---|---|---|---|---|---|---|
| P0 | Governance / specifications | **IN_REVIEW** | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) | — | Documentation checks only (see `docs/phase-reports/PHASE_0_REPORT.md`); no application tests exist | Pending |
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
| Blocks P1 until | Owner reviews wording/safety, confirms the six ADRs, approves the demo rule parameters, and merges the PR |

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
