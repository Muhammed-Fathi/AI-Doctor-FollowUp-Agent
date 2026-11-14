# Requirements Traceability Matrix

| Field | Value |
|---|---|
| Document ID | `EVAL-TRACE-001` |
| Version | `0.2.0-p0` |
| Status | **IN REVIEW** |
| Phase | `P0` (baseline). Updated every phase with real evidence |
| Purpose | Answer "where is this requirement designed, where is it built, and what proves it?" |
| Revision | 0.2.0: adds `REQ-DATA-04` (trust levels) and `REQ-OPS-04` (injected clock); 49 requirements total |

**Status legend:** `DESIGNED` = specified in P0 docs, nothing built · `PLANNED Pn` = build phase ·
`EXECUTED` = a real command produced real evidence (none yet outside documentation checks).

No requirement in this table is implemented or proven in Phase 0.

## 1. Authentication and authorization

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-AUTH-01` | `US-01` | `MVP_SPEC.md` §7.1 | `core/security.py`, seed script | `AUTH-01` | P2 | DESIGNED |
| `REQ-AUTH-02` | `US-01` | `ARCHITECTURE.md` §6 | `core/policies.py`, all routers | `NEG-02`, `NEG-16` | P2 | DESIGNED |
| `REQ-AUTH-03` | `US-01` | `API_CONTRACT.md` §2.2 | session/token layer | `AUTH-02`, `NEG-10` | P2 | DESIGNED |

## 2. Data domain

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-DATA-01` | `US-02`, `US-07` | `DATA_DICTIONARY.md` §2.8 | `db/models.py`, observations service | `GOLD-A`, `VERIFY-01` | P2 | DESIGNED |
| `REQ-DATA-02` | `US-02` | `DATA_DICTIONARY.md` §3 | check-in validation | `NEG-13` | P2 | DESIGNED |
| `REQ-DATA-03` | `US-02`, `US-12` | `DATA_DICTIONARY.md` §1 | models + seed | `DEMO-R` | P2 | DESIGNED |
| `REQ-DATA-04` | `US-07`, `US-08` | `DATA_DICTIONARY.md` §2.8/§3.2 | trust column + label rendering | `TRUST-01`, `NEG-19`, `NEG-21` | P2 | DESIGNED |

## 3. Ingestion and OCR

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-ING-01` | `US-03` | `EXTRACTION_PROVENANCE.md` §1 | `services/intake.py` | `NEG-03`, `NEG-04` | P3 | DESIGNED |
| `REQ-ING-02` | `US-04` | `EXTRACTION_PROVENANCE.md` §2 | `services/extraction.py` | `GOLD-EX-01..08` | P3 | DESIGNED |
| `REQ-ING-03` | `US-04` | `EXTRACTION_PROVENANCE.md` §2/§3 | extraction field set | `GOLD-EX-01..04` | P3 | DESIGNED |
| `REQ-ING-04` | `US-03` | `EXTRACTION_PROVENANCE.md` §1 | document hash + attempts | `GOLD-EX-01`, `NEG-18` | P3 | DESIGNED |
| `REQ-ING-05` | `US-03` | `EXTRACTION_PROVENANCE.md` §2 | parser bounds | `NEG-05` | P3/P7 | DESIGNED |

## 4. Verification and provenance

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-VERIFY-01` | `US-04` | `EXTRACTION_PROVENANCE.md` §5 | provenance model + UI viewer | `VERIFY-03`, `GOLD-EX-01` | P3 | DESIGNED |
| `REQ-VERIFY-02` | `US-05` | `EXTRACTION_PROVENANCE.md` §4 | quality-flag router | `GOLD-EX-09..11` | P3 | DESIGNED |
| `REQ-VERIFY-03` | `US-06` | `EXTRACTION_PROVENANCE.md` §6 | verify endpoint + append-only log | `VERIFY-01/02` | P3 | DESIGNED |

## 5. Monitoring and comparison

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-MON-01` | `US-07` | `TOOL_CONTRACTS.md` §3.5 | `services/comparisons.py` | `MON-01`, `RULE-01` | P4 | DESIGNED |
| `REQ-MON-02` | `US-07` | `DATA_DICTIONARY.md` §3 | comparison guards | `RULE-06` | P4 | DESIGNED |
| `REQ-MON-03` | `US-07` | `DEMO_REVIEW_RULES.md` §4 | duplicate/conflict rules | `MON-02`, `MON-03` | P4 | DESIGNED |

## 6. Deterministic review rules

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-RULE-01` | `US-08` | `DEMO_REVIEW_RULES.md` §3/§5 | `services/review_rules.py`, `services/verification_issues.py` | `RULE-01`, `RULE-05`, `VI-01`, `VI-02` | P3/P4 | DESIGNED |
| `REQ-RULE-02` | `US-08` | `DEMO_REVIEW_RULES.md` §6 | message templates + UI labels | `RULE-04`, `TRUST-01` | P4 | DESIGNED |
| `REQ-RULE-03` | `US-08` | `DEMO_REVIEW_RULES.md` §7 | dedupe + idempotent persistence | `RULE-02`, `RULE-03` | P4 | DESIGNED |

## 7. Local LLM drafting

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-LLM-01` | `US-09` | `LLM_ADAPTER.md` §1/§2 | `llm/base.py`, `ollama_provider.py` | `LLM-04` | P5 | DESIGNED |
| `REQ-LLM-02` | `US-09` | `LLM_ADAPTER.md` §3 | draft validator + citations | `LLM-01/02/03`, `EVAL-03` | P5/P7 | DESIGNED |
| `REQ-LLM-03` | `US-09` | `LLM_ADAPTER.md` §4 | provenance fields + UI badge | `LLM-04`, `E2E-03` | P5/P6 | DESIGNED |
| `REQ-LLM-04` | `US-09` | `LLM_ADAPTER.md` §5 | failure/degradation matrix | `LLM-05` | P5 | DESIGNED |

## 8. Orchestration

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-GRAPH-01` | `US-10` | `STATE_AND_GRAPH_CONTRACT.md` §4 | `agents/orchestrator.py` | `NEG-06`, `AD-01` | P5 | DESIGNED |
| `REQ-GRAPH-02` | `US-10` | `STATE_AND_GRAPH_CONTRACT.md` §5 | checkpointer wiring | `RESUME-01/02` | P5/P7 | DESIGNED |
| `REQ-GRAPH-03` | `US-10` | `STATE_AND_GRAPH_CONTRACT.md` §5.2 | interrupt + decisions endpoint | `SAFE-01/03`, `NEG-08/09` | P5 | DESIGNED |
| `REQ-GRAPH-04` | `US-10` | `STATE_AND_GRAPH_CONTRACT.md` §6/§7 | retry + idempotency guards | `NEG-07`, `RESUME-03` | P5 | DESIGNED |
| `REQ-GRAPH-05` | `US-10` | `TOOL_CONTRACTS.md` §5 | tool allowlist dispatcher | `SAFE-04` | P5 | DESIGNED |

## 9. UI

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-UI-01` | `US-07`–`US-11` | `ARCHITECTURE.md` §2 | `frontend/src/pages/doctor/*` | `E2E-02` | P6 | DESIGNED |
| `REQ-UI-02` | `US-02`, `US-03` | `ARCHITECTURE.md` §6 | `frontend/src/pages/patient/*` | `E2E-01` | P6 | DESIGNED |
| `REQ-UI-03` | `US-13` | `DEMO_SCENARIOS.md` §5 | state components + notices | `E2E-01/02/03` | P6 | DESIGNED |

## 10. Tasks, notifications, audit

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-TASK-01` | `US-10`, `US-11` | `TOOL_CONTRACTS.md` §3.9 | `services/tasks.py` | `SAFE-01`, `E2E-04` | P5/P6 | DESIGNED |
| `REQ-TASK-02` | `US-11` | `DATA_DICTIONARY.md` §2.15 | in-app notification table | `E2E-02`, `NEG-15` | P6 | DESIGNED |
| `REQ-AUDIT-01` | `US-06`, `US-12` | `DATA_DICTIONARY.md` §2.17 | `services/audit.py` | `AUD-01` | P2/P5 | DESIGNED |
| `REQ-AUDIT-02` | `US-12` | `CLINICAL_SAFETY.md` §8 | audit redaction | `AUD-02`, `NEG-14` | P7 | DESIGNED |

## 11. Security and safety

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-SEC-01` | `US-01` | `ARCHITECTURE.md` §6/§7 | scope guards on all routes | `NEG-01/02`, `SEC-08` | P2/P7 | DESIGNED |
| `REQ-SEC-02` | `US-13` | `EXTRACTION_PROVENANCE.md` §7 | untrusted-data handling | `NEG-11` | P3/P5 | DESIGNED |
| `REQ-SEC-03` | `US-11` | `ADR-0005`, `TOOL_CONTRACTS.md` §4 | absence of transport code | `NEG-15`, `SEC-07`, `RULE-07` | P6/P7 | DESIGNED |
| `REQ-SEC-04` | `US-05`, `US-09` | `STATE_AND_GRAPH_CONTRACT.md` §3/§8 | verified-only gate + `VI-*` issues | `SAFE-02/06`, `NEG-06`, `NEG-20`, `VI-01..03` | P3/P4/P5 | DESIGNED |
| `REQ-SEC-05` | `US-13` | `CLINICAL_SAFETY.md` §5 | disclaimer constants + UI | `E2E-01/03` | P6 | DESIGNED |
| `REQ-SEC-06` | `US-12` | `.gitignore`, `AGENTS.md` §3.1 | ignore rules + scan | `SEC-06` | P1/P7 | DESIGNED |

## 12. Operations and evaluation

| REQ | User story | Design doc | Planned component | Acceptance test | Build phase | Status |
|---|---|---|---|---|---|---|
| `REQ-OPS-01` | `US-12` | `GOLD_FIXTURES.md` §7 | deterministic seed | `DEMO-R` | P2/P8 | DESIGNED |
| `REQ-OPS-02` | `US-12` | `DEMO_SCENARIOS.md` §2 | PowerShell scripts | `NEG-12`, `BENCH-03` | P1/P8 | DESIGNED |
| `REQ-OPS-04` | `US-08` | `DEMO_REVIEW_RULES.md` §7 | injected `as_of_utc` on run + policy | `RULE-08` | P4 | DESIGNED |
| `REQ-EVAL-01` | `US-08` | `GOLD_FIXTURES.md` §6 | golden JSON + replay tests | `RULE-01` | P4/P7 | DESIGNED |
| `REQ-EVAL-02` | `US-04` | `EVALUATION_MATRIX.md` §4 | extraction metrics | `GOLD-EX-01..12`, `VERIFY-03` | P7 | DESIGNED |
| `REQ-EVAL-03` | `US-09` | `LOCAL_BENCHMARK_PLAN.md` §3 | runtime measurement | `BENCH-01..04`, `EVAL-03` | P5/P7 | DESIGNED |

## 13. Coverage summary (P0)

| Category | Requirements | Designed | Implemented | Executed evidence |
|---|---|---|---|---|
| Auth | 3 | 3 | 0 | 0 |
| Data | 4 | 4 | 0 | 0 |
| Ingestion/OCR | 5 | 5 | 0 | 0 |
| Verification | 3 | 3 | 0 | 0 |
| Monitoring | 3 | 3 | 0 | 0 |
| Rules | 3 | 3 | 0 | 0 |
| LLM | 4 | 4 | 0 | 0 |
| Graph | 5 | 5 | 0 | 0 |
| UI | 3 | 3 | 0 | 0 |
| Tasks/audit | 4 | 4 | 0 | 0 |
| Security | 6 | 6 | 0 | 0 |
| Ops/eval | 6 | 6 | 0 | 0 |
| **Total** | **49** | **49** | **0** | **0** |

The only executed checks in P0 are documentation-level: link/reference consistency, requirement-ID coverage,
OpenAPI structural validation, and prohibited-claim scanning. Their actual commands and results are quoted in
`docs/phase-reports/PHASE_0_REPORT.md` — nothing in this table is marked PASS on that basis.
