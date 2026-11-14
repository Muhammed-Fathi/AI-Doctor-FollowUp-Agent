# Phase 0 Report — Governance and Architecture Baseline

| Field | Value |
|---|---|
| Report ID | `REPORT-P0-001` |
| Phase | **P0 only** — documentation and governance |
| Status | **IN_REVIEW — round 3 submitted after a second review; not accepted, not merged, P1 not started** |
| Review round | 1 — PR #2 review `5904454222` (P0-R01…P0-R07 + ADR-0006 depth) → resolved; 2 — PR #2 review `5904505998` (P0-R08…P0-R11 + 3 test-realism points) → resolved; both matrices in §10 |
| Branch | `arena/ee7d211b-ai-doctor-followup-agent` |
| Base commit | `7d2ef73dae50c7404b46f653942eb99351053059` |
| Head commit | round 1: `8e342546ec26acc1382e2916b25affed7c660dc2`; round 2 content: `81df966b2fe80ab842f3405b32cfabc2f1b3a5e7`; round 3 content: `b3605ec484a38b15aec5bb153586fecda187ea1d`, plus a documentation-linkage commit (the exact PR head is listed at the top of PR #2) |
| Pull request | [#2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2) — targeting `main`, **not merged** |
| Tracking issue | GitHub issue #1 (referenced by number only — see §4.7 for an access limitation) |
| Author | Arena agent (implementer) |
| Reviewer | Project owner (pending) |

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.** This report describes documentation work. No
> application exists yet, and nothing in this phase was clinically or procedurally validated.

---

## 1. Executive summary

Phase 0 delivered a documentation-only baseline: an MVP specification with **50 traceable requirements**,
six architecture decision records, a finalized architecture with a role/permission matrix, typed shared-state
and graph contracts (checkpoint, interrupt/resume, retry, idempotency), tool allowlists, an API/OpenAPI
proposal validated structurally, a data dictionary, an extraction/provenance contract, a local-LLM adapter
design with an honest fallback, a deterministic DEMO-only review policy, a threat model, an evaluation matrix
with gold fixtures, three demo scenarios, agent governance rules, and this report.

**Round 2 (after review `5904454222`)** closes seven cross-document defects and the ADR-0006 agentic-depth gap:
the pre-verification and post-verification outputs are now distinct types (`VI-*` vs `DR-*`), observations carry
an explicit trust level, the demo clock is injected, task identity is deterministic and finalized in two
ordered app-DB transactions with restart reconciliation,
Case B's arithmetic and Case C's chronology are corrected, and the document-vs-observation unit split plus the
seed-vs-live fixture responsibilities are explicit. Finding-by-finding evidence: §10.

**Round 3 (after review `5904505998`)** reconciles four remaining contract conflicts and three test-realism
points: graph-trace decisions are now a **typed discriminated payload** (with typed extraction attempts as the
triage router's only input), run status/finalize is governed by an **app-DB source of truth with an explicit
restart-reconciliation algorithm** (the checkpoint file cannot join an app-DB transaction), a verified document
fact becomes an observation **only through a closed, versioned mapping table** (`map-1.0.0`, new
`REQ-DATA-05`), and the comparator's "non-verified observation" error is replaced by an **admissibility
predicate** that admits labelled self-reported data. `AD-01` now runs against a **mocked extractor** while a
separate `OCR-LIVE-01` run records measured OCR behaviour, and Case C's `VI-002` count is derived from three
explicitly declared candidate facts. Evidence: §10.2 and §11.

**Status is intentionally `IN_REVIEW`.** The implementing agent cannot mark P0 `PASS`, cannot sign the
specification, and did not merge. Phase 1 has not started.

## 2. Deliverables (12 required)

| # | Required deliverable | Artefact(s) | Status |
|---|---|---|---|
| 1 | Signed-off technical spec: one routine outpatient follow-up, actors, MVP user stories, non-goals | `docs/contracts/MVP_SPEC.md` (13 user stories, 10 non-goals, **50 requirements**, sign-off block) | **Complete for review** — signature pending owner |
| 2 | Finalized architecture diagram and role/permission matrix | `docs/architecture/ARCHITECTURE.md` §2, §6 (+ §5 sequence) | Complete for review |
| 3 | Five bounded agents + typed shared-state contract + tool contracts + graph transitions incl. checkpoint/interrupt/resume/retry/idempotency | `docs/contracts/STATE_AND_GRAPH_CONTRACT.md`, `docs/contracts/TOOL_CONTRACTS.md`, ADR-0006 (amended: bounded path selection + acceptance test `AD-01`) | Complete for review |
| 4 | Data dictionary + API/OpenAPI endpoint proposal + error cases | `docs/contracts/DATA_DICTIONARY.md`, `docs/contracts/API_CONTRACT.md`, `docs/contracts/openapi.phase0.yaml` | Complete for review; OpenAPI structurally validated |
| 5 | Ingestion/OCR pipeline + provenance + verification-status contract | `docs/contracts/EXTRACTION_PROVENANCE.md` | Complete for review |
| 6 | Deterministic synthetic demo-only review rules, no unsupported clinical thresholds | `docs/clinical-safety/DEMO_REVIEW_RULES.md` (**VI-001…VI-006** pre-verification issues + **DR-001/003/005/006/008/009** post-verification rules, injected demo clock, arbitrary parameters, explicit non-claims) | Complete for review — parameter sign-off pending |
| 7 | LLM/Ollama adapter design, fallback honesty, local benchmark plan | `docs/contracts/LLM_ADAPTER.md`, `docs/evaluation/LOCAL_BENCHMARK_PLAN.md` | Complete for review; nothing measured |
| 8 | Evaluation matrix: gold fixtures, negative/security tests, traceability, evidence, acceptance criteria | `docs/evaluation/EVALUATION_MATRIX.md` (+ `AD-01`, `VI-01..03`, `RULE-08`, `TRUST-01`, `NEG-19..21`), `docs/evaluation/GOLD_FIXTURES.md` (+ case D, `GOLD-EX-13`), `docs/evaluation/TRACEABILITY_MATRIX.md` | Complete for review; nothing executed |
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

**Round 2 modified 22 existing files (no files added or deleted):**
`AGENTS.md`, `README.md`, `docs/architecture/ADR-0006-five-bounded-agents-single-graph.md`,
`docs/architecture/ARCHITECTURE.md`, `docs/clinical-safety/{CLINICAL_SAFETY,DEMO_REVIEW_RULES,THREAT_MODEL}.md`,
`docs/contracts/{API_CONTRACT,DATA_DICTIONARY,EXTRACTION_PROVENANCE,LLM_ADAPTER,MVP_SPEC,STATE_AND_GRAPH_CONTRACT,TOOL_CONTRACTS}.md`,
`docs/contracts/openapi.phase0.yaml`, `docs/demo/DEMO_SCENARIOS.md`,
`docs/evaluation/{EVALUATION_MATRIX,GOLD_FIXTURES,LOCAL_BENCHMARK_PLAN,TRACEABILITY_MATRIX}.md`,
`docs/roadmap/PHASE_PROGRESS.md`, `docs/phase-reports/PHASE_0_REPORT.md`.

**Round 3 modified the same 22 existing files (no files added or deleted)** — the round-3 work is a change to
the same contract set, so the file list is identical to round 2's. The substantive round-3 edits are:

| File | Round-3 change |
|---|---|
| `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` | `ExtractionAttempt`, `TriageDetail`/`ValidationDetail`/`GateDetail`/`FinalizeDetail`, `NodeEvent.detail`/`attempt`, `extraction_attempts[]`/`mapping_version` in state; §5.1 app-DB authority; §7.1–§7.3 two-phase finalize + reconciliation + crash windows; §8 invariants 10–14; §9 rows |
| `docs/contracts/openapi.phase0.yaml` | `TraceEvent.attempt` + required `detail`, four detail schemas (52 → 56 schemas) |
| `docs/contracts/DATA_DICTIONARY.md` | `node_event` table (§2.18), typed `extraction_attempt` columns, unique `source_fact_id`, `mapping_version`, §3.3 closed mapping table |
| `docs/contracts/TOOL_CONTRACTS.md` | `is_admissible_observation` predicate, comparator/rule-engine wording, two-phase atomicity, facts-only `E_UNVERIFIED_FACT` |
| `docs/contracts/EXTRACTION_PROVENANCE.md` | §6 mapping qualification and document-only rule |
| `docs/contracts/MVP_SPEC.md` | `REQ-DATA-05` (50 requirements) |
| `docs/contracts/API_CONTRACT.md` | trace `detail` contract, two-phase decision rule, admissibility rendering rule, facts-only error note |
| `docs/contracts/LLM_ADAPTER.md` | unmapped document values may be cited but not implied as compared |
| `docs/clinical-safety/DEMO_REVIEW_RULES.md` | admissibly labelled inputs, `{count}` template note, Case C count |
| `docs/clinical-safety/CLINICAL_SAFETY.md` | four new invariants (admissibility, mapping, trace redaction, restart safety) |
| `docs/clinical-safety/THREAT_MODEL.md` | `T-22` checkpoint divergence, `T-23` trace leakage, `T-24` wrong mapping |
| `docs/architecture/ARCHITECTURE.md` | app-DB authority invariant, typed trace in the agent paragraph, two-phase commit row |
| `docs/architecture/ADR-0006-…md` | §3.3 typed trace payloads, §3.4 determinism boundary (mocked vs live) |
| `docs/evaluation/EVALUATION_MATRIX.md` | `MAP-01`, `TRUST-02`, `RESUME-04/05`, `OCR-LIVE-01`, sharpened `AD-01`, gates |
| `docs/evaluation/GOLD_FIXTURES.md` | §4.2a candidate-fact declaration, per-case mapping counts, §6 mocked-vs-live split |
| `docs/evaluation/TRACEABILITY_MATRIX.md` | `REQ-DATA-05`, 50 totals, test columns |
| `docs/evaluation/LOCAL_BENCHMARK_PLAN.md` | `OCR-LIVE-01` measured-run row |
| `docs/demo/DEMO_SCENARIOS.md` | C2a typed trace, C3 derived `{count}` |
| `docs/roadmap/PHASE_PROGRESS.md` | round-2 review row and evidence note |
| `AGENTS.md` | four new standing invariants (admissibility, mapping, app-DB truth, typed trace) |
| `README.md` | round-3 status and review path wording |

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
# round 2 re-run after adding ObservationVerification, VerificationIssue, trust_basis, as_of_utc:
VALID | openapi 3.1.0 | paths 30 | schemas 52 | structural issues: none

# custom structural check (required ⊆ properties, all $refs resolve)
no structural issues found
```

### 4.4 Documentation consistency checks

```console
$ python3 /tmp/check_docs.py            # round 2 re-run, after all review fixes
[links] markdown files: 29 | relative links checked: 41 | broken: 0 | bad anchors: 0
[req] defined: 49 | traceability rows: 49 | used repo-wide: 49
  defined-not-traced: []
  traced-not-defined: []
  used-undefined: []
[tests] declared (range-expanded): 86 | referenced by trace/spec: 50 | referenced-not-declared: []
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

Match count in round 2: `6` substantive files/lines (plus 2 lines containing only "medical device" in a negated
sense); the current count is in §11 item 12. Every match
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

The GitHub integration token available in this session cannot read issues, so the issue body was not read.
**Resolved by the review:** the project owner confirmed in review `5904454222` that issue #1 is
`P0: Doctor Follow-Up governance and architecture baseline`. It remains referenced by number in
[PR #2](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2).

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

1. **Cross-document consistency** — requirement IDs (50), agent names, tool names, node names, error codes, issue/rule IDs (`VI-*` vs `DR-*`), and trust/clock field names are used identically across `MVP_SPEC`, `ARCHITECTURE`, `STATE_AND_GRAPH_CONTRACT`, `TOOL_CONTRACTS`, `API_CONTRACT`, `openapi.phase0.yaml`, `DATA_DICTIONARY`, `DEMO_REVIEW_RULES`, `EVALUATION_MATRIX`, and `TRACEABILITY_MATRIX` (machine-checked where possible, see §4.4).
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
| `OQ-07`/`OQ-R05` | Whether validated **self-reported** check-ins may serve as comparison baselines (labelled), and whether the ` (self-reported)` suffix is acceptable in doctor-facing messages | `MVP_SPEC.md` §9, `DEMO_REVIEW_RULES.md` §13 | Self-reported values admissible but always labelled; suffix kept. **Round-2 reviewer position (recorded):** accepted as the proposed engineering default — may be compared, clearly labelled, never called doctor-verified |
| ADR-0006 §2/§5 | Whether "five bounded components, one model" plus the two bounded decision loops satisfies the evaluator's agentic-depth expectation. **Round-2 reviewer position (recorded):** a defensible *orchestrated multi-component system*, but not five independently reasoning LLM agents, and no guarantee can be given about a separate multi-LLM rubric without seeing it | `ADR-0006` §2, §5 | Current interpretation stands; changing it is a scope change |
| `OQ-A01` | Bearer token vs httpOnly cookie session | `API_CONTRACT.md` §6 | Bearer for MVP |
| `OQ-L01..L05` | Model family/size, latency budget, warm-up, repair attempts, translation | `LLM_ADAPTER.md` §7 | Candidates from `MASTER_PLAN.md`; 45 s budget; one repair |
| `OQ-T01..T03` | Batch extraction, manual review note, task scheduling | `TOOL_CONTRACTS.md` §7 | One document per run; no manual note tool; manual due date |
| ADR-0001..0006 | Acceptance of all six architecture decisions (especially ADR-0006's "five bounded nodes, one model" interpretation) | `docs/architecture/` | All remain `Proposed` until owner approval |
| — | Project license choice | `DEPENDENCIES.md` §7, OpenAPI `license` | `NOASSERTION` until P1 |
| — | Whether GitHub issue #1 is the correct tracking issue | §4.7 | **Resolved:** owner confirmed it is the P0 tracking issue |
| `OQ-08` | Which `test_name` aliases your synthetic reports will actually print (the `map-1.0.0` table is closed by design) | `DATA_DICTIONARY.md` §3.3 | Current alias set; any new alias is a mapping-version bump, not a runtime guess |
| `OQ-09` | Whether a checkpoint found ahead of the app DB should always be rewound (current rule) or surfaced to the doctor as an incident | `STATE_AND_GRAPH_CONTRACT.md` §7.3 row 5 | Rewind + audit `workflow.checkpoint.diverged`, create nothing |

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

## 10. Review round 1 — finding-by-finding resolution matrix

Review: [PR #2, review `5904454222`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2#pullrequestreview-5904454222),
state `CHANGES REQUIRED` at head `8e342546ec26acc1382e2916b25affed7c660dc2`.

All findings are resolved **in documentation** in this round. No finding is closed by a runtime fix, because no
runtime exists yet; each row states what a P3–P7 test will prove later.

| ID | Finding (abbreviated) | Resolution | Paths changed | Evidence in this round | Status |
|---|---|---|---|---|---|
| **P0-R01** | GOLD-B baseline arithmetic: with 138→146→152 the most-recent-prior delta is 6, not 14, so `DR-005` could not fire | Corrected the synthetic series to **138 (10-02) → 146 (10-20) → 158 (11-03)**; baseline is explicitly the most recent prior (146); delta is **12 mmHg**; same delta propagated to the rule worked example, golden JSON (`baseline_rule: most_recent_prior_comparable`, `baseline_observation`, `delta: 12`), demo narration, and `DEMO-B` | `GOLD_FIXTURES.md` §3, `DEMO_REVIEW_RULES.md` §11.1, `DEMO_SCENARIOS.md` §4, `EVALUATION_MATRIX.md` `DEMO-B` | Stale-content scan finds no `14 mmHg`, no `152`, no `by 14`: `grep -rn "14 mmHg\|by 14\|152" docs` → **0 matches** | **Fixed** |
| **P0-R02** | GOLD-C chronology: corrected date `2026-04-03` predates the `2026-10-10` baseline, so `96 → 105` was not a valid current-vs-prior comparison | Changed the ambiguous printed date to **`03/11/2026`** (3 Nov vs 11 Mar) and the corrected value to **`2026-11-03`**, which is after the baseline; baseline stays 96 mg/dL (10-10); delta 9 ≤ 40 so no `DR-005`. Encounter moved to 2026-11-03 to match | `GOLD_FIXTURES.md` §4, `EXTRACTION_PROVENANCE.md` flag table, `DEMO_SCENARIOS.md` §5, `EVALUATION_MATRIX.md` `GOLD-EX-09`/`DEMO-C` | Stale-content scan finds no `03/04/2026`, no `2026-04-03`: **0 matches**; fixture states baseline and corrected dates explicitly | **Fixed** |
| **P0-R03** | Pre-verification review-item path unreachable: `DR-002/004/007/010` claimed `ExtractedFact` inputs the rule tool cannot read, and the gate halts before `review_rules` | Split the outputs into two typed families: **`VI-001…VI-006` verification issues** (pre-verification, blocking, produced by `fact_verify_gate`, never carry a `rule_id`) and **`DR-001/003/005/006/008/009` review rules** (post-verification, verified evidence only). Retired `DR-002/004/007/010` with an explicit mapping table and a "not reused" rule. Added `VerificationIssue` to the state model, `verification_issue` table (no `rule_id` column), API `verification_issues[]`, OpenAPI schema/enum, extraction response, UI section split, and tests `VI-01..03` | `DEMO_REVIEW_RULES.md` §3–§6, `STATE_AND_GRAPH_CONTRACT.md` §3–§4, `DATA_DICTIONARY.md` §2.8a, `API_CONTRACT.md`, `openapi.phase0.yaml`, `TOOL_CONTRACTS.md` §4, `EVALUATION_MATRIX.md`, `GOLD_FIXTURES.md` §4.3, `DEMO_SCENARIOS.md` §5, `ARCHITECTURE.md` | OpenAPI validator confirms `ReviewItem.rule_id` enum is exactly `[DR-001, DR-003, DR-005, DR-006, DR-008, DR-009]` and `VerificationIssue.issue_type` is `VI-001…VI-006`; `WorkflowDetail.required` contains `verification_issues`; retired IDs occur only in retirement/constraint text | **Fixed** |
| **P0-R04** | Task idempotency key could change on retry because it contained the optional, newly generated `task_id`; tool precondition also contradicted the post-resume `finalizing` state | Key is now `action_key = sha256(workflow_version \| patient_id \| approval_decision_id \| "followup_task" \| "slot:1")` — immutable, persisted inputs only — and `task_id = uuid5(TASK_NAMESPACE, action_key)` is **derived**. `TaskDraft.action_key`/`task_id` are required. Added the explicit `awaiting_decision → finalizing → completed` sequence, unique indexes and crash-before/after-commit recovery rules. (Round 2 refined this into **two ordered app-DB transactions** plus restart reconciliation, because the checkpoint file cannot join them — see `P0-R09`.) Tool precondition is now `status == finalizing`. Test `NEG-07` and `RESUME-01` updated; threat `T-21` added | `STATE_AND_GRAPH_CONTRACT.md` §7/§7.1/§7.2, `TOOL_CONTRACTS.md` §3.9, `DATA_DICTIONARY.md` §2.14, `API_CONTRACT.md` §2.5, `EVALUATION_MATRIX.md`, `THREAT_MODEL.md` | Grep of the idempotency table shows `slot:1` and `uuid5`; no key formula still contains `task_id`; `run finalizing` precondition documented in both contracts | **Fixed** |
| **P0-R05** | Observation verification undefined: rules/`read_observations` demanded "verified" observations, but the data model only had `validation` and no verifying actor; GOLD-C claimed a verified check-in | Decided and documented: **validated self-reported check-ins are admissible but always labelled**. Added `trust_level ∈ {self_reported_validated, doctor_verified}`, `verified_by_user_id`/`verified_at` with CHECK constraints (a check-in with a verifier is invalid; `verified_document` implies `doctor_verified`). Propagated to state (`ObservationView.trust_level`), DB, API (`trust_level` + nullable `verification`), OpenAPI, comparison `trust_basis`, review message `(self-reported)` suffix, draft validator, requirement `REQ-DATA-04`, threats `T-19`, and tests `TRUST-01`, `NEG-19`, `NEG-21`, `LLM-06` | `DATA_DICTIONARY.md` §2.8/§3, `STATE_AND_GRAPH_CONTRACT.md` §3, `API_CONTRACT.md`, `openapi.phase0.yaml`, `TOOL_CONTRACTS.md` §3.4, `DEMO_REVIEW_RULES.md` §5–§6, `CLINICAL_SAFETY.md`, `LLM_ADAPTER.md` §3, `MVP_SPEC.md` `REQ-DATA-04`/`US-07`, `GOLD_FIXTURES.md`, `EVALUATION_MATRIX.md` | OpenAPI validator confirms `Observation.required` contains `trust_level` and the `ObservationVerification` schema; DB CHECK constraints documented as bidirectional; owner decision recorded as `OQ-07` | **Fixed (decision documented; implementation P2/P4)** |
| **P0-R06** | Case A fixture/units/field completeness: `g/dL` outside the stated unit list; seed duplicated the live Nov 1 check-in; `reference_text` ambiguous | Split **observation units** (`mmHg`, `bpm`, `mg/dL`) from **document units** (`+ g/dL`, `%`, text-only, never converted); declared `reference_text` **optional** and added a printed reference range to `REPORT-A-01` so all five fields appear; seed now holds only Oct 1 + Oct 15 and the Nov 1 check-in is a live step; noted the pre-check-in staleness consequence explicitly | `GOLD_FIXTURES.md` §1/§2/§3.2, `DATA_DICTIONARY.md` §2.6/§3.2, `EXTRACTION_PROVENANCE.md` §2/§3, `DEMO_SCENARIOS.md` §3, `openapi.phase0.yaml` (`ExtractedFact.unit` docs) | Fixture table shows two seeded rows plus one live row; `g/dL` appears only in document-unit contexts; `reference_text` documented as optional | **Fixed** |
| **P0-R07** | Wall-clock dependence in `DR-003`/`DR-001` would change expected items on the defence date | Added an injected `demo_as_of_utc = 2026-11-14T12:00:00Z` to the policy, persisted per run (`workflow_run.as_of_utc`, state `as_of_utc`), returned by the API (`WorkflowRun`, `DemoStatus`), shown in the demo header, required in the benchmark protocol, and asserted by test `RULE-08`; non-demo path records the real instant used. `{days}` is defined against the injected clock | `DEMO_REVIEW_RULES.md` §7/§8, `STATE_AND_GRAPH_CONTRACT.md` §2/§3, `DATA_DICTIONARY.md` §2.16, `API_CONTRACT.md`, `openapi.phase0.yaml`, `EVALUATION_MATRIX.md`, `GOLD_FIXTURES.md` §1, `DEMO_SCENARIOS.md` §1, `LOCAL_BENCHMARK_PLAN.md` §3, `MVP_SPEC.md` `REQ-OPS-04` | OpenAPI validator confirms `WorkflowRun.required` contains `as_of_utc`; every fixture declares the same as-of value; no rule text still says "now" | **Fixed** |
| **ADR-0006** | Agentic depth: five named nodes with one LLM may read as a fixed chain; document bounded conditional tool-selection/recovery, executable trace and a P5/P8 acceptance scenario | ADR-0006 extended with (a) an explicit definition of "agent" here, (b) **`extraction_triage`** — bounded path selection (text layer / OCR / OCR-with-preprocessing / flag-for-human) with a hard retry budget of 2 and `path_selected`/`path_reason` in the trace, (c) **`draft_validation`** — accept/repair-once/fallback loop, (d) acceptance test **`AD-01`** with fixture `GOLD-EX-13`, (e) the trade-off stated plainly (auditable determinism instead of emergent planning) and the anti-goal (no five free-roaming LLM peers). Wired into the state/graph contract (§4, §10), architecture, evaluation matrix, demo step C2a, and the benchmark plan | `ADR-0006`, `STATE_AND_GRAPH_CONTRACT.md` §4/§6/§10, `ARCHITECTURE.md`, `EVALUATION_MATRIX.md` `AD-01`, `GOLD_FIXTURES.md` §6, `DEMO_SCENARIOS.md` §5.1, `LOCAL_BENCHMARK_PLAN.md`, `TOOL_CONTRACTS.md` §3.2/§3.8 | Triage and validation nodes appear in the node table, the transition diagram, the routing rules and the trace fields; `AD-01` is a named row in the evaluation matrix with explicit assertions | **Fixed (design; `AD-01` execution is P5)** |
| Review note | Synthetic demo parameters are acceptable as demo values, not clinical thresholds | Unchanged non-claims; parameters now also include the as-of value; exact wording retained and re-flagged for owner ratification | `DEMO_REVIEW_RULES.md` §9/§13 | Non-claim paragraph intact and expanded | Acknowledged — ratification still required |
| Review note | Update `PHASE_0_REPORT.md` with findings and a reviewer-resolution table; P0 stays `IN_REVIEW`; P1 `TODO`; no merge | This section; statuses unchanged | this file, `PHASE_PROGRESS.md` | §7 status table and `PHASE_PROGRESS.md` still show P0 `IN_REVIEW`, P1–P8 `TODO` | Done |

### 10.1 Additional consistency fixes made while resolving the findings

Cross-document defects found during the same pass (not raised explicitly in the review) and corrected:

| Item | Fix |
|---|---|
| `MVP_SPEC.md` §7 requirement count vs traceability | Added `REQ-DATA-04` and `REQ-OPS-04`; traceability, summary table and this report said **49** (was 47) — round 3 adds `REQ-DATA-05`, so the current figure is **50** |
| `TOOL_CONTRACTS.md` tool count sentence | Said "eight of nine" for ten tools; rewritten as a precise breakdown |
| Orchestrator nodes listed agent tools | `intake_validate`, `fact_verify_gate`, `clinician_approval` now explicitly hold no agent tools; a `collect_verification_issues` domain service is documented instead |
| `DATA_DICTIONARY.md` ER diagram | `CLAIM_EVIDENCE`/direct observation link replaced by a single `EVIDENCE_LINK` entity used by review items, verification issues and claims |
| Demo admin audit capability | Matrix now says "local DB/CLI only; no API endpoint in MVP" instead of implying an endpoint |
| Task/notification id | Both are now derived from the decision, so the notification also cannot duplicate |
| `GOLD-D` rule coverage | Added an internal fixture so every surviving `DR-*` rule has a deterministic positive case (staleness, missing baseline, duplicate, implausible value) |
| Case C encounter date | Moved to 2026-11-03 so it does not precede the corrected report date |

## 10.2 Review round 2 — finding-by-finding resolution matrix (`P0-R08`…`P0-R11` + test realism)

Review: [PR #2, review `5904505998`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/2#pullrequestreview-5904505998),
state `COMMENTED` ("substantive corrections confirmed; 4 contract reconciliations remain") at head
`2724fa4de8e4da11c30d41d6cff77de9e5d02373`.

| ID | Finding (abbreviated) | Resolution | Paths changed | Evidence in this round | Status |
|---|---|---|---|---|---|
| **P0-R08** | Agentic trace has no typed fields for the decisions it promises; `NodeEvent`/`TraceEvent` carry only `node/started_at/ended_at/outcome/tools_called`, so `path_selected`, `path_reason`, attempt count and `validation_outcome` had nowhere to live; also unexplained how `extraction_triage` reads attempt metadata that is not in `SharedGraphState` | (a) `NodeEvent` now carries `attempt` and a **discriminated `detail`** union — `TriageDetail{path_selected, path_reason, document_id, attempt_index, engine_confidence, preprocessing_applied}`, `ValidationDetail{validation_outcome, attempt_index, violation_codes[]}`, `GateDetail{decision, blocking_fact_count, issue_types[]}`, `FinalizeDetail{approval_decision, task_created, notification_created}`; (b) new typed `ExtractionAttempt` model and `extraction_attempts[]` state field written by N1 — this is the router's **only** input; (c) OpenAPI `TraceEvent.detail` (`oneOf` + `null`) plus four detail schemas, `detail` and `attempt` now **required**; (d) new `node_event` table with one column per typed field and CHECKs that bind `detail_kind` to the node; (e) `detail` is `null` for nodes with no bounded decision, so ad-hoc keys are schema errors; (f) `AD-01` asserts the payloads field-by-field | `STATE_AND_GRAPH_CONTRACT.md` §3/§4.1/§4.2/§8/§9/§10, `openapi.phase0.yaml`, `DATA_DICTIONARY.md` §2.5/§2.18, `ADR-0006` §3.3/§4, `ARCHITECTURE.md`, `EVALUATION_MATRIX.md`, `GOLD_FIXTURES.md` §6, `AGENTS.md` | OpenAPI validator: `schemas 56` (was 52), `TraceEvent.required = [node, attempt, started_at, detail]`, `detail` alternatives = `null + Triage/Validation/Gate/Finalize`. Grep confirms no free-text field exists in `node_event` or any detail schema | **Fixed** |
| **P0-R09** | "Atomic" approval transaction contradicted by the separate LangGraph checkpoint DB: §7.1 assumed a persisted decision before `finalizing`, while §7.2 claimed one transaction writes decision + task + notification + audit + status; a crash therefore could not be reasoned about | Replaced with a **two-phase app-DB finalize** and an explicit **restart-reconciliation algorithm**: phase A commits the decision row + `finalizing` (decision UUID created inside it); phase B commits task + notification + audit + `completed`, keyed by the already-committed decision. §7.3 defines seven ordered reconciliation rows (including checkpoint-lagging and checkpoint-ahead divergence) and a six-window crash table. §5.1 now states the app DB is the single source of truth and the checkpoint is replay state that cannot join an app-DB transaction. Divergence writes `workflow.checkpoint.diverged` and creates nothing. Tests `RESUME-04`, `RESUME-05`; threat `T-22` | `STATE_AND_GRAPH_CONTRACT.md` §5.1/§5.2/§7.1–§7.3/§8/§9, `TOOL_CONTRACTS.md` §3.9, `API_CONTRACT.md` §2.5 rule 1a, `DATA_DICTIONARY.md` §2.16, `THREAT_MODEL.md`, `EVALUATION_MATRIX.md`, `TRACEABILITY_MATRIX.md`, `ARCHITECTURE.md`, `AGENTS.md` | Grep: no document still claims a single cross-store transaction; §7.2 table has exactly two app-DB transactions; `RESUME-04/05` declared in the matrix with explicit expectations; `run finalizing` precondition retained | **Fixed** |
| **P0-R10** | "A verified document fact becomes an observation" was universal, contradicting Case A / the data dictionary where a hemoglobin `g/dL` fact stays document-only; alias mapping, report-date semantics and duplicate handling undefined | Added `DATA_DICTIONARY.md` **§3.3 closed mapping table `map-1.0.0`** (alias set + required unit per measure type, including `Fasting glucose` → `glucose`), nine rules (nothing else converts; unit gates separately; literal alias match, no fuzzy/substring; test name drives mapping; `measured_at` = verified report date at `00:00Z`, never upload time nor `as_of_utc`; atomic with the verification row; unique `source_fact_id`; patient scope inherited; check-ins never take this path), a per-fixture expectation table (A = 0, B = 1, C = 0 halted / 1 after correction), `mapping_version` on the run, new `REQ-DATA-05`, and test `MAP-01`. `EXTRACTION_PROVENANCE.md` §6 now qualifies the claim and keeps unmapped facts document-only | `DATA_DICTIONARY.md` §2.8/§3.2/§3.3, `EXTRACTION_PROVENANCE.md` §6, `MVP_SPEC.md` §7.2 (50 requirements), `TRACEABILITY_MATRIX.md`, `STATE_AND_GRAPH_CONTRACT.md` §2/§3/§8, `GOLD_FIXTURES.md` §1/§2.4/§3.2/§3.3/§4.4, `EVALUATION_MATRIX.md`, `THREAT_MODEL.md` (`T-24`), `LLM_ADAPTER.md`, `CLINICAL_SAFETY.md`, `AGENTS.md` | Layout check: the old universal sentence is gone (`grep "becomes an observation with"` → 0); §3.3 exists with 4 mapped rows and 9 rules; `REQ-DATA-05` traced in the matrix; checker now reports `defined 50 / traced 50 / used 50` | **Fixed** |
| **P0-R11** | `compare_observations` still returned `E_UNVERIFIED_FACT` for a "non-verified observation", contradicting the new `self_reported_validated` admissibility | Introduced one shared **`is_admissible_observation` predicate** (5 conjuncts: `validation != rejected`; patient scope; unit equals the measure's unit; parseable `measured_at` ≤ as-of + 5 min; trust level in the known set). Adopting it: `read_observations` (`trust_levels` defaults to both), `compare_observations` (retired `E_UNVERIFIED_FACT`; inadmissible input → `comparable=false` + `skip_reason`), `evaluate_demo_review_rules` (notes), the review-rule inputs line, and the UI/draft rules. `E_UNVERIFIED_FACT` is now explicitly **facts-only**. Tests `TRUST-02`; `NEG-19` retained | `TOOL_CONTRACTS.md` §3.4/§3.5/§3.7/§3.8/revision, `DEMO_REVIEW_RULES.md` §5/§6, `CLINICAL_SAFETY.md` §6, `STATE_AND_GRAPH_CONTRACT.md` §8, `AGENTS.md`, `EVALUATION_MATRIX.md`, `TRACEABILITY_MATRIX.md` | Scoped grep (excluding this report's own quotations): `"non-verified observation"` → **1** match, the revision note in `TOOL_CONTRACTS.md` that describes the removal; observation-scoped `E_UNVERIFIED_FACT` → only the explicit "never for observations" statements; predicate text identical in the two contracts and the safety doc; `TRUST-02` declares the rejected-row, self-reported-row, cross-patient and no-promotion assertions | **Fixed** |
| Test realism 1 | `GOLD-EX-13` promised OCR confidences 0.55 → 0.86 that real Tesseract is not guaranteed to produce | `AD-01` now runs against a **mocked extractor** (`FakeExtractor`) returning scripted attempt metadata — deterministic, offline, no OCR binary; a separate `OCR-LIVE-01` run on the owner laptop **records measured** confidence/text/time/version and is explicitly *not* asserted in advance. Both are named in the evaluation matrix, the ADR, the benchmark plan and the fixture doc | `GOLD_FIXTURES.md` §6.1/§6.2, `EVALUATION_MATRIX.md` (`AD-01`, `OCR-LIVE-01`), `ADR-0006` §4, `LOCAL_BENCHMARK_PLAN.md` §3, `DEMO_SCENARIOS.md` C2a, `TRACEABILITY_MATRIX.md` | Fixture §6 is split into "contract test (mocked)" and "live measurement (recorded)"; `AD-01` row lists the exact assertions; `OCR-LIVE-01` says "no expected value is asserted in advance" | **Fixed** |
| Test realism 2 | Case C's `VI-002` said "3 pending facts", an invented count, while the field contract permits up to five candidates | Declared the **exact candidate-fact set** for the fixture (three: `report_date`, `test_name`, `value`; absent fields produce no candidate, and `unit` is carried as `null` on the value fact) in `GOLD_FIXTURES.md` §4.2a, and made the message a rendered template `{count} extracted value(s) are not yet verified.` computed from the fact rows — never hard-coded | `GOLD_FIXTURES.md` §4.2a/§4.3, `DEMO_REVIEW_RULES.md` §6.1/§11.2, `DEMO_SCENARIOS.md` C3 | §4.2a table has exactly 3 rows with `raw_text`/`normalized_value`/flags; the message section shows `{count}` interpolation; the demo step references the derived count | **Fixed** |
| Test realism 3 | PR description appeared to describe the original 50-schema revision; owner could not see the revised evidence | PR body rewritten with a round-3 banner carrying the current figures (50 requirements, 56 schemas, 96 declared test IDs), the reconciliation list, and pointers to §10.2/§11 and the round-3 review comment | PR #2 body (not a repo file) | `gh pr view 2 --json body` contains the round-3 banner and the current numbers | **Fixed** |

### 10.2a Governance guidance from the review (recorded, not acted on beyond documentation)

| Guidance | How it is reflected |
|---|---|
| Provisional acceptance of ADR-0001…0005; local-only, no paid API, synthetic data | Unchanged; no ADR status was altered to "Accepted" — owner ratification is still required (§13) |
| Demo policy parameters stay explicitly `DEMO_ONLY`, as-of timestamp frozen | Every rule carries `demo_only`; `as_of_utc` remains injected and persisted (`REQ-OPS-04`, `RULE-08`); no parameter was given clinical meaning |
| `OQ-07` accepted as an engineering default (self-reported may be compared, labelled, never "doctor verified") | Now encoded as the admissibility predicate (`P0-R11`) plus `trust_basis`; the "never doctor verified" wording is retained in 4 places and asserted by `TRUST-01`, `TRUST-02`, `NEG-21` |
| ADR-0006 is an orchestrated multi-component system, not five independently reasoning LLM agents | ADR-0006 §2/§3.3 keeps that wording verbatim and states the limitation; the reviewer's "cannot guarantee an evaluator's separate multi-LLM rubric" is recorded in §7 open questions |
| Owner ratification required; do not mark P0 PASS | P0 remains `IN_REVIEW`, P1 `TODO`, no merge, no approval |

## 11. Verification evidence for round 3 (executed in this session)

Environment unchanged: Linux sandbox, Python 3.11.2, Node 22.22.3, no Tesseract/Poppler/Ollama/PowerShell.

Round-2 figures are kept for comparison: 49 requirements, 86 declared test IDs, 52 OpenAPI schemas. Round 3 adds
`REQ-DATA-05`, five test IDs (`MAP-01`, `TRUST-02`, `RESUME-04`, `RESUME-05`, `OCR-LIVE-01`) and four trace-detail
schemas, so the numbers below differ **because the documents changed**, not because a different checker was used
for the same inputs. The checker's test-ID pattern was extended in round 3 to include the `MAP`/`TRUST`/`AD`/`VI`/
`OCR-LIVE` families and to stop counting `VI-001…VI-006` (issue types, not tests) as tests.

| # | Command | Observed result (round 3) |
|---|---|---|
| 1 | `/tmp/docsenv/bin/python /tmp/check_docs.py` | `[links] markdown files: 29 \| relative links checked: 41 \| broken: 0 \| bad anchors: 0`; `[req] defined: 50 \| traceability rows: 50 \| used repo-wide: 50`, all three gap lists empty; `[tests] declared (range-expanded): 96 \| referenced by trace/spec: 60 \| referenced-not-declared: []`; `0 files missing H1`; `5 mermaid diagrams` (syntax NOT validated) |
| 2 | `yaml.safe_load` + `openapi_spec_validator.validate` | `VALID \| openapi 3.1.0 \| paths 30 \| schemas 56` |
| 3 | Custom structural check (every `required` ⊆ properties, all `$ref` resolve) | `structural issues: none` |
| 4 | Schema assertions on the new trace contract | `TraceEvent.required = ['node','attempt','started_at','detail']`; `detail` alternatives = `null, TriageEventDetail, ValidationEventDetail, GateEventDetail, FinalizeEventDetail`; `TriageEventDetail.required = [kind, path_selected, path_reason, document_id, attempt_index, preprocessing_applied]`; `path_selected` enum = `[text_layer, ocr_direct, ocr_preprocess_retry, flag_for_human]`; `path_reason` enum = `[text_layer_available, confidence_ok, low_confidence, ocr_transient_error, retry_exhausted]`; `ValidationEventDetail.validation_outcome` enum = `[accept, repair_requested, fallback_selected]` |
| 5 | Round-2 schema facts re-checked (regression) | `ReviewItem.rule_id` enum = `[DR-001, DR-003, DR-005, DR-006, DR-008, DR-009]`; `VerificationIssue.issue_type` enum = `VI-001…VI-006`; `Observation` requires `trust_level`; `WorkflowRun` requires `as_of_utc`; `WorkflowDetail` requires `verification_issues` — all still true |
| 6 | `grep -rn "non-verified observation" docs README.md AGENTS.md --include="*.md" \| grep -v PHASE_0_REPORT.md` | **1 match** — the `TOOL_CONTRACTS.md` revision note saying the error was *replaced* by the admissibility predicate. No tool still returns it for an observation (P0-R11) |
| 7 | `grep -rn "becomes an observation with \`trust_level='doctor_verified'\`"` | **0 matches** — replaced by the qualified, table-gated §3.3 rules (P0-R10) |
| 8 | `grep -rn "one transaction writes: approval decision row\|atomic-finalize transaction" docs --include="*.md" \| grep -v PHASE_0_REPORT.md` | **0 matches**; §7.2 now specifies exactly two ordered app-DB transactions and §7.3 the seven-row reconciliation (P0-R09) |
| 9 | `grep -rn "path_selected=proceed\|path_reason=text_sufficient" docs --include="*.md" \| grep -v PHASE_0_REPORT.md` | **0 matches** — one enum is used identically in the state contract, ADR-0006, the fixture, the matrix and the demo (P0-R08) |
| 10 | `grep -rn "14 mmHg\|by 14\|152\|03/04/2026\|2026-04-03" docs README.md AGENTS.md --include="*.md" \| grep -v PHASE_0_REPORT.md` | **0 matches** outside this report's own quotations of the retired values (round-2 corrections intact) |
| 11 | `grep -rn "DR-002\|DR-004\|DR-007\|DR-010" docs --include="*.md"` | 13 lines (`DEMO_REVIEW_RULES.md` 8, this report 3, `DATA_DICTIONARY.md` 1, `STATE_AND_GRAPH_CONTRACT.md` 1), all in retirement mappings, schema CHECK constraints, the OpenAPI description, the agent rule and this report — no fixture, demo step or expectation uses a retired ID |
| 12 | `grep -rniE "clinically safe\|medically accurate\|HIPAA[- ]compliant\|GDPR[- ]compliant\|production[- ]ready\|clinically validated\|medical device" --include="*.md" .` | **14** matching lines: 8 in the documents under review, each a prohibition or negation (`CLINICAL_SAFETY.md` §4/§9, `MASTER_PLAN.md` §1/§10, `MVP_SPEC.md` scope notice, `EVALUATION_MATRIX.md` honesty rule, `AGENTS.md` §2), and 6 inside this report (command echo, count line and quoted examples). **No affirmative claim** exists or was added in round 3 |
| 13 | `git ls-files \| grep -niE "\.env$\|\.sqlite\|\.db$\|\.gguf\|\.safetensors\|\.key$\|\.pem$\|secret\|credential\|node_modules\|__pycache__\|/uploads/"` | no matches |
| 14 | `git status --porcelain` before commit | modified Markdown/YAML only — 0 files added, 0 deleted (count stated in the commit/PR) |

**How `extraction_triage` gets its input (explicit answer to `P0-R08`).** N1 `document_extract` writes one
`ExtractionAttempt` per pass into `SharedGraphState.extraction_attempts[]` (`path`, `preprocessing`,
`engine_confidence` or `null`, `text_char_count`, `succeeded`, `error_code`, `duration_ms`) and the same rows into
`extraction_attempt` (app DB). N1a reads **only** that list plus `retry_counts`; it never re-reads the document and
never invents a confidence. The decision is emitted as a `TriageDetail` on the event and persisted to `node_event`.

## 12. What remains NOT RUN after round 3

Unchanged: no backend/frontend test, Ruff/type check, database or migration, OCR run, model call, benchmark,
browser E2E, PowerShell gate, CI job, or Mermaid rendering was executed. Round 3 changes documentation only, so
none of the newly declared tests (`MAP-01`, `TRUST-02`, `RESUME-04`, `RESUME-05`, `OCR-LIVE-01`, and the sharpened
`AD-01`) can run yet — they are specifications for P3–P7.

Specifically **not run and not claimed**: `AD-01` (needs the graph + mocked extractor from P5), `OCR-LIVE-01` (needs
the owner's Tesseract install), `RESUME-04/05` (need the real checkpoint + process-kill harness), and every
runtime measurement. The mocked/live split exists precisely so that a future `AD-01` pass is not mistaken for
evidence about real OCR quality.

**Requires the owner Windows laptop:** dependency installation, Tesseract/Poppler, Ollama/model benchmark,
offline run, PowerShell gate, live-OCR measurement, and the machine record sheet.

## 13. Owner review checklist (round 3)

- [ ] Re-read `DEMO_REVIEW_RULES.md` §3–§6: confirm the `VI-*` (pre-verification) vs `DR-*` (post-verification) split and the retirement of `DR-002/004/007/010`.
- [ ] Confirm the corrected Case B arithmetic (146 → 158 = 12 mmHg) and Case C chronology (`03/11/2026` → 2026-11-03, baseline 2026-10-10).
- [ ] Decide `OQ-07`: are validated **self-reported** check-ins acceptable as comparison baselines when always labelled? If not, a doctor-verification workflow for every observation must be added and this baseline re-planned.
- [ ] Accept the `trust_level`/`trust_basis` model and the ` (self-reported)` suffix (or amend the wording).
- [ ] Accept the injected `demo_as_of_utc` policy value and the requirement that tests never use the wall clock.
- [ ] Confirm the deterministic task identity + atomic finalize rules (`STATE_AND_GRAPH_CONTRACT.md` §7.1–§7.2).
- [ ] Review amended **ADR-0006**: is the bounded path selection + repair loop, with `AD-01`, sufficient agentic depth for your evaluator? State any additional mechanism required (without adding free-roaming LLM peers).
- [ ] Confirm the **typed trace contract** (`P0-R08`): four detail payloads, `detail` required-nullable, no free-text field, and `node_event` as the persisted form.
- [ ] Confirm the **two-phase finalize + reconciliation** rules (`P0-R09`) match how you expect restarts to behave, including the "checkpoint ahead of app DB" case (`RESUME-05`), which deliberately rewinds rather than creating a task.
- [ ] Confirm the closed **`map-1.0.0` alias table** (`P0-R10`) — especially that `Fasting glucose` maps to `glucose` while `hemoglobin g/dL`, `%` and unknown names stay document-only — and add any alias you know your synthetic reports will print.
- [ ] Confirm the **admissibility predicate** (`P0-R11`) and the retirement of the observation-scoped `E_UNVERIFIED_FACT`; `E_UNVERIFIED_FACT` now means *extracted fact*, nothing else.
- [ ] Confirm the **mocked `AD-01` vs measured `OCR-LIVE-01`** split, and that nothing in the evaluation matrix asserts a real Tesseract score.
- [ ] Confirm the document-vs-observation unit split (`g/dL` is document-only) and the seed-vs-live Case A split.
- [ ] Re-check the permission matrix, tool contracts and API/OpenAPI deltas introduced in round 2.
- [ ] Ratify the demo parameters in `DEMO_REVIEW_RULES.md` §9 (or supply your own).
- [ ] Approve and merge **yourself**, then record the merge SHA and set P0 `PASS` in `PHASE_PROGRESS.md`.
- [ ] Do not start P1 until that approval is recorded.

## 14. Compliance statement for this phase

- Rounds 2 and 3 changed documentation only: no file was added or deleted, and no code, dependency, migration, fixture, script or workflow was introduced (file counts are in the commit list and §11 item 14).
- No model was trained, downloaded, or called; no paid service, quota, or credential was used; no real patient data was created, requested, or stored.
- The clinical-safety constraints were preserved and strengthened: verified-only gating, doctor approval, no external messaging, no clinical thresholds, explicit non-claims, an explicit trust/provenance distinction for self-reported data, a closed document-value mapping, and a trace that structurally cannot carry patient text.
- No PR was merged, no phase was marked `PASS`, no approval was fabricated, and Phase 1 was not started.
- P0 remains `IN_REVIEW`; P1–P8 remain `TODO`.
- **Next action is P0 owner re-review of this round — not Phase 1 implementation.**
