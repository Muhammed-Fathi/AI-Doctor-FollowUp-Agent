# Phase 0 Report — Governance and Architecture Baseline

| Field | Value |
|---|---|
| Report ID | `REPORT-P0-001` |
| Phase | **P0 only** — documentation and governance |
| Status | **IN_REVIEW — not accepted, not merged, P1 not started** |
| Branch | `arena/ee7d211b-ai-doctor-followup-agent` |
| Base commit | `7d2ef73dae50c7404b46f653942eb99351053059` |
| Head commit | recorded in the PR body (this report is updated by a follow-up commit when the PR is opened) |
| Pull request | linked in `docs/roadmap/PHASE_PROGRESS.md` and the PR itself; targeting `main`, **not merged** |
| Tracking issue | GitHub issue #1 (referenced by number only — see §8 for an access limitation) |
| Author | Arena agent (implementer) |
| Reviewer | Project owner (pending) |

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.** This report describes documentation work. No
> application exists yet, and nothing in this phase was clinically or procedurally validated.

---

## 1. Executive summary

Phase 0 delivered a documentation-only baseline: an MVP specification with 47 traceable requirements,
six architecture decision records, a finalized architecture with a role/permission matrix, typed shared-state
and graph contracts (checkpoint, interrupt/resume, retry, idempotency), tool allowlists, an API/OpenAPI
proposal validated structurally, a data dictionary, an extraction/provenance contract, a local-LLM adapter
design with an honest fallback, a deterministic DEMO-only review policy, a threat model, an evaluation matrix
with gold fixtures, three demo scenarios, agent governance rules, and this report.

**Status is intentionally `IN_REVIEW`.** The implementing agent cannot mark P0 `PASS`, cannot sign the
specification, and did not merge. Phase 1 has not started.

## 2. Deliverables (12 required)

| # | Required deliverable | Artefact(s) | Status |
|---|---|---|---|
| 1 | Signed-off technical spec: one routine outpatient follow-up, actors, MVP user stories, non-goals | `docs/contracts/MVP_SPEC.md` (13 user stories, 10 non-goals, 47 requirements, sign-off block) | **Complete for review** — signature pending owner |
| 2 | Finalized architecture diagram and role/permission matrix | `docs/architecture/ARCHITECTURE.md` §2, §6 (+ §5 sequence) | Complete for review |
| 3 | Five bounded agents + typed shared-state contract + tool contracts + graph transitions incl. checkpoint/interrupt/resume/retry/idempotency | `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, `docs/contracts/TOOL_CONTRACTS.md`, ADR-0006 | Complete for review |
| 4 | Data dictionary + API/OpenAPI endpoint proposal + error cases | `docs/contracts/DATA_DICTIONARY.md`, `docs/contracts/API_CONTRACT.md`, `docs/contracts/openapi.phase0.yaml` | Complete for review; OpenAPI structurally validated |
| 5 | Ingestion/OCR pipeline + provenance + verification-status contract | `docs/contracts/EXTRACTION_PROVENANCE.md` | Complete for review |
| 6 | Deterministic synthetic demo-only review rules, no unsupported clinical thresholds | `docs/clinical-safety/DEMO_REVIEW_RULES.md` (DR-001…DR-010, arbitrary parameters, explicit non-claims) | Complete for review — parameter sign-off pending |
| 7 | LLM/Ollama adapter design, fallback honesty, local benchmark plan | `docs/contracts/LLM_ADAPTER.md`, `docs/evaluation/LOCAL_BENCHMARK_PLAN.md` | Complete for review; nothing measured |
| 8 | Evaluation matrix: gold fixtures, negative/security tests, traceability, evidence, acceptance criteria | `docs/evaluation/EVALUATION_MATRIX.md`, `docs/evaluation/GOLD_FIXTURES.md`, `docs/evaluation/TRACEABILITY_MATRIX.md` | Complete for review; nothing executed |
| 9 | Three precise demo scenarios: stable, changed, ambiguous OCR; no real data | `docs/demo/DEMO_SCENARIOS.md` (+ exact values in `GOLD_FIXTURES.md`) | Complete for review |
| 10 | `PHASE_PROGRESS.md` with P0–P8 statuses; P0 `IN_REVIEW`, others `TODO` | `docs/roadmap/PHASE_PROGRESS.md` | Complete |
| 11 | `AGENTS.md` governance: one phase per PR, no autonomous diagnosis/prescribing/real messages, no direct `main`, no fabricated verification, no agent merge | `AGENTS.md` | Complete |
| 12 | Phase 0 review report: files, checks, assumptions, risks, P1 entry criteria | this file | Complete |

Additionally delivered (supporting infrastructure for reviewability): six ADRs, a threat model,
a dependency/version verification record, and a minimal `.gitignore` safety net.

## 3. File-level changes

**Modified (4):**

| File | Change |
|---|---|
| `README.md` | Rewritten as a review-oriented project home: P0 status table, review path, scope, non-goals, stack with unverified-version caveat, verification-honesty section |
| `docs/roadmap/MASTER_PLAN.md` | Plan version → v0.2; Phase 0 status → `IN_REVIEW` + artefact list; normative-contract pointers; ADR/docs layout updated; §11 next actions updated to "owner review, agent must not merge/advance"; §12 points to the verification record |
| `docs/roadmap/PHASE_PROGRESS.md` | P0 → `IN_REVIEW` with evidence table; P1–P8 → `TODO`; required-evidence rules retained |
| `docs/architecture/ARCHITECTURE.md` | Rewritten v0.1 → v0.2: finalized diagram, layer contracts, five-agent table, role/permission matrix, trust boundaries, checkpoint/interrupt summary, ADR index, deferred design |

**Added (26):**

| Area | Files |
|---|---|
| Governance | `AGENTS.md`, `.gitignore` |
| Architecture | `ADR-0001-monorepo-single-service.md`, `ADR-0002-local-ollama-with-labelled-fallback.md`, `ADR-0003-sqlite-app-and-checkpoints.md`, `ADR-0004-evidence-verified-review-queue.md`, `ADR-0005-defer-external-comms-and-ehr.md`, `ADR-0006-five-bounded-agents-single-graph.md` |
| Contracts | `MVP_SPEC.md`, `STATE_AND_GRAPH_CONTRACT.md`, `TOOL_CONTRACTS.md`, `API_CONTRACT.md`, `openapi.phase0.yaml`, `DATA_DICTIONARY.md`, `EXTRACTION_PROVENANCE.md`, `LLM_ADAPTER.md`, `DEPENDENCIES.md` |
| Clinical safety | `CLINICAL_SAFETY.md`, `DEMO_REVIEW_RULES.md`, `THREAT_MODEL.md` |
| Evaluation | `EVALUATION_MATRIX.md`, `GOLD_FIXTURES.md`, `TRACEABILITY_MATRIX.md`, `LOCAL_BENCHMARK_PLAN.md` |
| Demo | `DEMO_SCENARIOS.md` |
| Report | `docs/phase-reports/PHASE_0_REPORT.md` |

**Totals:** 30 files changed (4 modified, 26 added), ~6,170 insertions, 84 deletions; documentation-only.

**Not touched:** no backend, frontend, database, migration, dependency manifest, lockfile, script, workflow,
fixture, or model file was created or modified. `docs/arena/ARENA_PHASE_0_PROMPT.md` was read, not edited.

## 4. Commands executed and actual results

Environment: Linux authoring sandbox, Python 3.11.2, Node 22.22.3 / npm 10.9.8. Tesseract, Poppler and
Ollama are **not installed** there, and there is no Windows PowerShell.

### 4.1 Environment probe

```console
$ python3 -V          → Python 3.11.2
$ node -v             → v22.22.3
$ npm -v              → 10.9.8
$ which tesseract     → not found
$ which ollama        → not found
$ which pdftoppm      → not found
```

### 4.2 Dependency metadata (registry-verified, not installed)

```console
$ curl -s https://pypi.org/pypi/<pkg>/json | python3 -c "..."
fastapi 0.162.7 MIT; pydantic 2.14.3 MIT; sqlalchemy 2.1.8 MIT; alembic 1.20.1 MIT;
langgraph 1.2.22 MIT; langgraph-checkpoint-sqlite 3.1.3 MIT; pypdf 7.1.0 BSD-3-Clause;
pytesseract 0.3.13 Apache-2.0; pillow 13.0.0 MIT-CMU; pytest 9.2.0 MIT; httpx 0.28.1 BSD-3-Clause;
uvicorn 0.54.0 BSD-3-Clause; ruff 0.17.5 MIT; python-multipart 0.0.33 Apache-2.0; pdf2image 1.17.0 MIT

$ curl -s https://registry.npmjs.org/<pkg> | python3 -c "..."
react 19.3.1 MIT; react-dom 19.3.1 MIT; vite 8.3.8 MIT (node ^20.19||>=22.12);
@vitejs/plugin-react 6.3.0 MIT; typescript 7.0.2 Apache-2.0; vitest 5.1.0 MIT;
@playwright/test 1.65.1 Apache-2.0; eslint 10.15.0 MIT
```

Recorded in `docs/contracts/DEPENDENCIES.md`; all values flagged as *not pinned, not installed, not tested*.

### 4.3 OpenAPI structural validation

```console
$ python3 - <<'PY' (yaml.safe_load + openapi_spec_validator.validate)
parsed ok; openapi: 3.1.0 paths: 30
VALID: spec passes openapi-spec-validator

# after converting OpenAPI-3.0-style `nullable: true` to 3.1 union types:
VALID after nullable conversion; paths: 30 schemas: 50

# custom structural check (required ⊆ properties, all $refs resolve)
no structural issues found
```

### 4.4 Documentation consistency checks

```console
$ python3 /tmp/check_docs.py
[links] markdown files: 29 | relative links checked: 41 | broken: 0 | bad anchors: 0
[req] defined: 47 | traceability rows: 47 | used repo-wide: 47
  defined-not-traced: []
  traced-not-defined: []
  used-undefined: []
[tests] declared (range-expanded): 80 | referenced by trace/spec: 46 | referenced-not-declared: []
[md] files missing H1: 0 []
[mermaid] diagrams present: 5 (syntax NOT validated)
```

Exit code `0`. Note: the checker is a throwaway script in `/tmp` (not committed, because `scripts/` is outside
the Phase 0 file scope); its logic is reproduced below so a reviewer can re-run it.

What it checks: every relative Markdown link resolves to an existing file; every `#anchor` resolves to a
heading in the target; every `REQ-*` ID used anywhere is defined in `MVP_SPEC.md`; every requirement defined
is present in `TRACEABILITY_MATRIX.md`; every referenced test ID exists in `EVALUATION_MATRIX.md` or
`API_CONTRACT.md`; every Markdown file has an H1.

### 4.5 Prohibited-claim scan

```console
$ grep -rniE "clinically safe|medically accurate|HIPAA[- ]compliant|GDPR[- ]compliant|production[- ]ready|clinically validated|medical device" --include="*.md" .
```

Match count: `6` files/lines (plus 2 lines containing only "medical device" in a negated sense). Every match
was read and is a **prohibition or an explicit negation**, e.g.:

- `MASTER_PLAN.md`: "**The system is not** a … medical device … or clinically validated application."
- `CLINICAL_SAFETY.md`: table saying **do not say** "clinically safe"/"medically accurate"; and "is not a medical device, has not been clinically evaluated".
- `AGENTS.md`, `EVALUATION_MATRIX.md`: assertions forbidden / never justified.
- `MVP_SPEC.md`: "It is not a medical device…".

No affirmative claim was found, and none was added.

### 4.6 Secret / runtime-artefact scan

```console
$ git ls-files | grep -niE "\.env$|\.sqlite|\.db$|\.gguf|\.safetensors|\.key$|\.pem$|secret|credential|node_modules|__pycache__|/uploads/"
(no output)
```

No secret, database, upload, or model artefact is staged/tracked. `.gitignore` covers these for later phases.

### 4.7 Issue access (limitation, reported honestly)

```console
$ gh issue view 1 --json number,title,body,labels,state
GraphQL: Resource not accessible by integration (repository.issue)
$ gh api repos/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/issues/1
{"message":"Resource not accessible by integration", ... "status":403}
```

The GitHub integration token available in this session cannot read issues. Issue **#1** is therefore
referenced as the tracking issue by number in the PR body, and **its content was not read or assumed**.
If #1 is not the Phase 0 tracking issue, the owner should say so in the PR.

## 5. What was **not** executed (and why)

| Check | Status | Reason |
|---|---|---|
| Backend unit/integration/contract tests | **Not run** | No backend code exists in P0 (by design) |
| Frontend build, Vitest, Playwright | **Not run** | No frontend exists in P0 |
| Ruff / type checks | **Not run** | No Python/TypeScript source exists |
| Database creation or Alembic migration | **Not run** | Schema is a proposal in P0 |
| OCR extraction on any fixture | **Not run** | Fixtures are specified, not authored; Tesseract absent here |
| Any Ollama model call, download, or benchmark | **Not run** | No model installed; no model may be downloaded in P0 |
| Windows PowerShell scripts (`preflight/setup/start/stop/test_all`) | **Not run** | Do not exist yet (P1); no Windows host |
| Playwright browser E2E | **Not run** | No UI; no browsers installed |
| Mermaid diagram rendering/validation | **Not run** | No renderer available; 5 diagrams are hand-written and only reviewed for syntax by inspection |
| Automatic Markdown lint (e.g. markdownlint) | **Not run** | Not installed; a custom link/ID checker was used instead |
| GitHub Actions CI | **Not run** | No workflow file exists yet (P1) |

**Requires owner Windows laptop:** dependency installation, Tesseract/Poppler setup, Ollama install and model
benchmark, offline end-to-end run, PowerShell gate, and the machine record sheet in
`docs/evaluation/LOCAL_BENCHMARK_PLAN.md`.

## 6. Design review performed (and its limits)

Performed by inspection in this phase:

1. **Cross-document consistency** — requirement IDs (47), agent names, tool names, node names, error codes, and rule IDs are used identically across `MVP_SPEC`, `ARCHITECTURE`, `STATE_AND_GRAPH_CONTRACT`, `TOOL_CONTRACTS`, `API_CONTRACT`, `openapi.phase0.yaml`, `DATA_DICTIONARY`, `DEMO_REVIEW_RULES`, `EVALUATION_MATRIX`, and `TRACEABILITY_MATRIX` (machine-checked where possible, see §4.4).
2. **Forbidden autonomy** — no path exists where an agent approves, diagnoses, prescribes, sends a message, or creates a task without a doctor decision; the forbidden tool list is explicit in `TOOL_CONTRACTS.md` §4 and mirrored in ADR-0005 and the threat model.
3. **No unsupported clinical thresholds** — the only numeric triggers are the arbitrary demo parameters in `DEMO_REVIEW_RULES.md` §6, with explicit non-claims and mechanically checkable message wording.
4. **Honest verification** — every status in this repository distinguishes design, execution, and not-run; no PASS is claimed.
5. **Scope discipline** — no future-phase code or empty scaffolding was created (`AGENTS.md` §1).

Limits of that review: it is a documentation review, not a code review, not a clinical review, and not a
security assessment. It cannot establish correctness of the future implementation.

## 7. Unresolved assumptions requiring owner input

| ID | Item | Where | Default if unanswered |
|---|---|---|---|
| `OQ-01`/`ASM-01`/`ASM-02` | Demo laptop specification (Windows version, CPU, RAM, GPU/VRAM, disk) and whether a 3B-class local model is viable | `MVP_SPEC.md` §8/§9, `LOCAL_BENCHMARK_PLAN.md` | CPU-only target; benchmark marked "owner laptop required"; fallback path supported |
| `OQ-02` | Separate patient login vs a role switch in one app | `MVP_SPEC.md` §9 | Separate logins, one React app |
| `OQ-03` | Whether the 5-field extraction set is too ambitious for the demo (demo uses 2 fields) | `MVP_SPEC.md` §9 | Keep 5 declared, demo uses 2 |
| `OQ-04`/`OQ-A02` | Demo reset reachability and required dismissal reasons | `MVP_SPEC.md`, `API_CONTRACT.md` §6 | CLI/PowerShell reset; reason optional |
| `OQ-05` | Arabic/English balance in the UI | `MVP_SPEC.md` §9 | English UI |
| `OQ-06`/`OQ-R01..R04` | Approval of the arbitrary demo parameters and rule behaviour | `DEMO_REVIEW_RULES.md` §6/§10 | Keep listed values; absolute differences; optional reasons |
| `OQ-A01` | Bearer token vs httpOnly cookie session | `API_CONTRACT.md` §6 | Bearer for MVP |
| `OQ-L01..L05` | Model family/size, latency budget, warm-up, repair attempts, translation | `LLM_ADAPTER.md` §7 | Candidates from `MASTER_PLAN.md`; 45 s budget; one repair |
| `OQ-T01..T03` | Batch extraction, manual review note, task scheduling | `TOOL_CONTRACTS.md` §7 | One document per run; no manual note tool; manual due date |
| ADR-0001..0006 | Acceptance of all six architecture decisions (especially ADR-0006's "five bounded nodes, one model" interpretation) | `docs/architecture/` | All remain `Proposed` until owner approval |
| — | Project license choice | `DEPENDENCIES.md` §7, OpenAPI `license` | `NOASSERTION` until P1 |
| — | Whether GitHub issue #1 is the correct tracking issue | §4.7 | Referenced by number; content unread |

## 8. Known risks (Phase 0 specific)

| Risk | Impact | Mitigation in this phase |
|---|---|---|
| Reviewer reads "five agents" as five LLM peers | Scope/cost misunderstanding | ADR-0006 states the interpretation explicitly and flags it as the most important semantic decision |
| Demo rule numbers mistaken for clinical thresholds | Safety/credibility | `DEMO_REVIEW_RULES.md` §6 non-claims, neutral message templates, `demo_only=1` DB constraint, UI label requirement |
| Specification drift during implementation | Docs become fiction | Requirement IDs + traceability matrix + per-phase update rule in `PHASE_PROGRESS.md` |
| Over-specification delays P1 | Schedule risk | P1 is deliberately limited to skeleton/health/scripts/CI; contracts are proposals, not code commitments |
| Unverified dependency versions break setup | P1 failure | `DEPENDENCIES.md` marks everything unpinned; P1 pins after a real install on the owner machine |
| Docs-only PR creates a false sense of completion | Governance risk | Status is `IN_REVIEW`; README/report state nothing is implemented or tested |
| Issue #1 not readable by the integration token | Traceability gap | Disclosed in §4.7 and in the PR body; owner can confirm |

## 9. P1 entry criteria (do not start before these hold)

1. Owner has **reviewed and approved** this P0 PR (explicit approval recorded in `PHASE_PROGRESS.md`), and the PR is **merged by the owner** — not the agent.
2. All six ADRs are accepted (or amended with the owner's decision recorded).
3. The demo parameter values and neutral wording in `DEMO_REVIEW_RULES.md` are accepted.
4. Owner supplies the laptop specification and confirms Python 3.12 / Node LTS / Tesseract / Poppler / Ollama installability (`ASM-01`, `ASM-02`).
5. Owner confirms the tracking issue and the repository settings (private repo, no Actions secrets needed for P1).
6. Any changes requested to `MVP_SPEC.md` §7 requirements are applied and re-traced before coding.

P1 will then implement only: monorepo skeleton, Python/Node environments, `.env.example`, `.gitignore`
hardening, FastAPI `/health` + `/version`, Vite shell, Alembic baseline, Windows PowerShell
`preflight/setup/start/stop/test_all`, basic tests, and a minimal CI workflow.

## 10. Owner review checklist

- [ ] Read `README.md` → `MVP_SPEC.md` → `ARCHITECTURE.md`; confirm the scope is what you want to defend.
- [ ] Confirm actors, user stories `US-01..US-13`, and the 10 non-goals.
- [ ] Accept or amend ADR-0001…ADR-0006 (especially ADR-0006 and ADR-0004).
- [ ] Check the permission matrix (`ARCHITECTURE.md` §6) matches your expectations for doctor/patient/admin.
- [ ] Check `STATE_AND_GRAPH_CONTRACT.md` §4–§7: node set, halt conditions, interrupt/resume, retry and idempotency.
- [ ] Check `TOOL_CONTRACTS.md` §4 forbidden capabilities (no messaging, no shell/SQL, no prescribing).
- [ ] Review `openapi.phase0.yaml` endpoint set and `API_CONTRACT.md` error catalogue; note anything missing for P1.
- [ ] Review `DATA_DICTIONARY.md` for extra/missing fields.
- [ ] Approve or replace the arbitrary parameters in `DEMO_REVIEW_RULES.md` §6; confirm the wording non-claims.
- [ ] Review `CLINICAL_SAFETY.md` §3/§9 (allowed vs prohibited wording) and `THREAT_MODEL.md` residual risks.
- [ ] Review `GOLD_FIXTURES.md` values and the three scenes in `DEMO_SCENARIOS.md`.
- [ ] Confirm the versions/licenses in `DEPENDENCIES.md` and supply the laptop specification.
- [ ] Confirm `AGENTS.md` rules are what you want enforced on future PRs.
- [ ] Confirm GitHub issue #1 is the tracking issue; state any required changes in the PR.
- [ ] Approve the PR and merge it yourself; then update `PHASE_PROGRESS.md` to `PASS` with the merge SHA.

## 11. Compliance statement for this phase

- No backend, frontend, agent, database, migration, or model code was written.
- No model was trained, downloaded, or called; no paid service, quota, or credential was used.
- No real patient data, PII, or PHI was created, requested, or stored.
- No PR was merged, no phase was marked `PASS`, no owner approval was fabricated, and Phase 1 was not started.
- No test, benchmark, build, or browser run is claimed that did not happen; §4 lists what actually ran and §5 lists what did not.
- **Next action is P0 owner review — not Phase 1 implementation.**
