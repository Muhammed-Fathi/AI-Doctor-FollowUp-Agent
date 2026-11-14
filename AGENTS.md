# AGENTS.md — Operating Rules for AI Agents

Binding rules for any AI agent (Arena, ChatGPT, IDE assistants, autonomous scripts) contributing to
**AI-Doctor-FollowUp-Agent**. Humans may override a rule only by an explicit written decision in the
PR thread and in `docs/roadmap/PHASE_PROGRESS.md`. Agents may never override them.

> **Project nature:** academic, local-only, synthetic-data graduation project.
> **NOT FOR CLINICAL USE.** No diagnosis, no prescribing, no real patient messaging.

---

## 1. One phase per pull request

1. An agent works on **exactly one phase** (`P0`…`P8`) per branch and per PR, matching the phase named in its task prompt.
2. Do **not** start phase *n+1* in the same PR, in a follow-up comment, or in the background — not even "preparatory" files.
3. Do not implement future-phase code early. Empty placeholder modules and speculative APIs are forbidden.
4. If work for the next phase seems necessary, write it as an **open question** in the phase report instead.

## 2. No direct `main` edits, no merging, no self-approval

1. Never commit, force-push, or push directly to `main`. All work goes to a phase branch
   (`feat/pN-short-scope`) or the assigned Arena session branch, then into a PR targeting `main`.
2. An agent must **never merge** a PR, enable auto-merge, or push a merge commit to `main`.
3. An agent must **never** mark a phase `PASS`, tick owner-approval checkboxes, sign a specification, or edit another reviewer's verdict.
4. Only the project owner decides merge and phase acceptance. `P0` stays `IN_REVIEW` until then.
5. Never rewrite history on a branch that the owner may be reviewing; add commits instead of amending/rebasing pushed work.

## 3. Medical and safety boundaries (non-negotiable)

An agent must not implement, describe, or demo any of the following, in code, fixtures, documents, or UI copy:

1. Autonomous diagnosis, differential diagnosis, risk scores, triage, severity classification, or prognosis.
2. Prescriptions, dosing, drug interactions, treatment plans, or medication changes.
3. Patient-facing medical advice or result interpretation.
4. Any external communication to a real person: SMS, email, WhatsApp, push, phone, webhooks to third parties.
5. Automatic escalation or emergency response of any kind.
6. Invented clinical thresholds, guideline claims, or citations to medical literature that were not provided by the owner.
7. "Clinically safe", "medically accurate", "HIPAA/GDPR compliant", "production-ready", or "validated" claims based on synthetic tests.

The only permitted numeric trigger values are the **explicitly labelled, arbitrary demo parameters** in
`docs/clinical-safety/DEMO_REVIEW_RULES.md`. They must never be presented as medical guidance.

### 3.1 Data rules
- Synthetic, fictitious, clearly labelled demo data only. No real patient data, real names, real record numbers, or scraped medical documents.
- Never request, accept, or store real credentials, tokens, or PHI in the repo, PR bodies, logs, or chat.
- Never commit `.env`, databases, uploads, model weights, OCR temp output, or screenshots containing real data.

### 3.2 Provenance, idempotency and clock invariants
- Every observation carries a `trust_level` (`self_reported_validated` | `doctor_verified`). Never describe a
  self-reported check-in as "verified", "confirmed", or doctor-reviewed.
- Self-reported values must be labelled as such in review messages and draft claims (`(self-reported)`).
- Pre-verification blockers are `VI-*` verification issues; post-verification prompts are `DR-*` review items.
  Never mix the two types, and never emit a retired ID (`DR-002/004/007/010`).
- Mutating actions derive their idempotency key **only** from immutable, already-persisted identifiers
  (e.g. the approval decision ID) plus a fixed slot — never from a newly generated row ID.
- Time-dependent demo behaviour uses the injected `as_of_utc`; do not introduce `now()` in rules, fixtures,
  or tests.
- **Admissibility is not verification.** `is_admissible_observation` (`TOOL_CONTRACTS.md` §3.4) admits
  `self_reported_validated`; it excludes `validation='rejected'`, cross-patient rows, unit mismatches and
  unparseable timestamps. Never re-introduce an "unverified observation" error for observations —
  `E_UNVERIFIED_FACT` is for extracted facts only.
- **Mapping is closed.** A verified document fact becomes an observation only via the versioned alias/unit table
  (`DATA_DICTIONARY.md` §3.3). Unmapped values (`g/dL`, `%`, unknown names) stay document-only; never coerce them
  onto a nearby measure type.
- **The app DB is the source of truth for run status.** The LangGraph checkpoint file is replay state and cannot
  join an app-DB transaction; reconcile on restart (`STATE_AND_GRAPH_CONTRACT.md` §7.3) instead of trusting a
  checkpoint's status.
- **Trace decisions are typed.** Graph trace entries carry a discriminated `detail` payload of enums, IDs, counts
  and probabilities. Never add a free-text field, a document snippet, or a model output to the trace.

### 3.3 Human-in-the-loop invariants
- A doctor decision is required before any follow-up task, notification, or final summary is finalized.
- Extracted/OCR values are never silently promoted to trusted facts.
- The LLM drafts prose only: it cannot set thresholds, decide review flags, approve, select a patient, write SQL, or call arbitrary URLs.

## 4. No fabricated verification

1. **Never claim a test, lint, build, benchmark, or browser check was run unless it was actually executed in this session.**
2. Report commands exactly as executed, with the real exit status and a trimmed output excerpt.
3. Distinguish, in every report: **design reviewed** / **executed here** / **not executed** / **requires owner Windows laptop**.
4. No invented screenshots, metrics, latency figures, pass counts, coverage numbers, model outputs, or trace logs.
5. If a check cannot run in the sandbox (Windows PowerShell, Ollama, Tesseract install, GPU, Playwright browsers), say so and mark it blocked for owner verification. Do not simulate it.
6. Quotes from logs must be reproducible by the reviewer. Long logs belong in the PR body as trimmed excerpts, not as binary blobs.

## 5. Phase file scope

Default allowed paths per phase (PRs touching others need owner approval first):

| Phase | Allowed paths |
|---|---|
| `P0` | `README.md`, `AGENTS.md`, `.gitignore`, `docs/**` (governance, contracts, safety, evaluation, demo, phase reports) |
| `P1` | repo skeleton, `pyproject.toml`, frontend scaffold, `.github/workflows/**`, `scripts/powershell/**`, `.env.example`, backend `/health` + `/version`, Alembic baseline, `.gitignore` |
| `P2` | `backend/app/{api/v1/auth,core,db,schemas,services}`, `data/synthetic/**`, backend tests for P2 |
| `P3` | ingestion/extraction modules, document fixtures, extraction tests |
| `P4` | comparisons, rule engine, `data/synthetic/golden_cases/**`, rule tests |
| `P5` | `backend/app/{agents,llm}/**`, checkpointer wiring, workflow endpoints, agent/LLM tests |
| `P6` | `frontend/**`, UI tests, in-app task/notification surfaces |
| `P7` | tests across suites, CI hardening, evaluation reports |
| `P8` | demo scripts, final docs, packaging and handover |

`P0` is **docs-only**: no application, dependency, database, migration, or model code.

## 6. Dependency and platform claims

1. Record a version only after checking an authoritative source (PyPI/npm metadata, official docs, or the owner's machine). Store the source and retrieval date.
2. Do not pin or claim compatibility for an unverified version. Unverified items are listed as *unverified* in `docs/contracts/DEPENDENCIES.md`.
3. Do not download models, datasets, or large binaries. Do not add paid services or anything requiring an API key/billing.
4. No LLM/GPU test in hosted CI; those are local-owner checks.

## 7. Code quality expectations (from P1 onward)

- Typed Python (Pydantic/FastAPI), typed TypeScript; no untyped public boundary.
- Every security- or safety-critical assertion has a test; every test maps to a requirement ID.
- No secret literals; configuration via environment with safe local defaults.
- Tests must be deterministic and offline; the model-dependent path is separately marked.
- Migrations are additive and reversible; seeded data is reproducible.

## 8. Required PR and report contents

Every agent PR includes:

1. Phase, scope, and explicit non-goals of the change.
2. **Exact** changed-file list.
3. Commands executed with real results (and what was not executed, and why).
4. Safety-boundary review: what the change could make the system do, and the evidence it still cannot diagnose, prescribe, message, or self-approve.
5. Tests: passed / failed / skipped / not run, with context.
6. Unresolved assumptions, open questions, known risks, and rollback.
7. Owner review checklist.
8. The tracking issue reference and whether it should stay open.

## 9. Stop conditions

Stop and report instead of proceeding when:

- A requirement conflicts with docs, the plan, or the safety contract (log it, propose an ADR, do not silently pick).
- A requested action would require real data, secrets, paid quota, merging, or phase advancement.
- A test environment is unavailable (state it plainly).
- The change would exceed the phase's allowed file scope.

## 10. Reporting template

```text
Branch: <name>   Base: <sha>   Head: <sha>   PR: <url>
Deliverables: complete / incomplete (list)
Files: <exact paths>
Commands + results: <command> -> <exit code / observed result>
Executed: <checks>   Not executed: <checks + reason>   Owner-laptop required: <checks>
Safety review: <boundary assertions and evidence>
Open questions / risks: <items>
Phase status: IN_REVIEW (never PASS)   Next action: owner review of P0
```
