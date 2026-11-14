# Threat Model

| Field | Value |
|---|---|
| Document ID | `SAFE-TM-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — mitigations are design commitments; only documentation checks were executed in P0** |
| Phase | `P0` (design). Mitigations implemented P2–P6; verified P7 |
| Related | `REQ-SEC-01..06`, `REQ-AUDIT-02`, ADR-0005 |

Scope: a single-machine, localhost, synthetic-data educational prototype. Threats are scoped to what this
system *could* plausibly do, including during a live defense demo. Enterprise/hosted threats (multi-tenant
isolation, DDoS, cloud IAM) are out of scope and listed as such.

## 1. Assets

| Asset | Why it matters here |
|---|---|
| The claim "the doctor decides" | The project's entire safety narrative depends on it |
| Evidence integrity (facts ↔ sources) | A silent mismatch makes every downstream statement unreliable |
| Patient-scope isolation | Cross-patient leakage is a critical failure even with synthetic data (`REQ-SEC-01`) |
| Approval and task records | The only proof that no autonomous action occurred |
| Audit trail | Demo credibility and defect investigation |
| Local machine and repo | No secrets, no real data, no model weights committed (`REQ-SEC-06`) |
| Demo availability | A broken demo undermines the presented evidence |

## 2. Actors and adversaries

| Actor | Trust | Notes |
|---|---|---|
| Doctor (demo user) | Trusted but fallible | May approve carelessly; UI must make uncertainty obvious |
| Patient (demo user) | Untrusted input source | Can submit odd units, timestamps, and text |
| Uploaded document content | Untrusted data | May be malformed or contain adversarial instructions |
| Local model | Untrusted output generator | Can hallucinate, time out, or produce invalid JSON |
| Demo admin | Trusted local operator | Can reset data; cannot bypass approvals |
| Local attacker with machine access | Out of scope to defend | SQLite files are plaintext; documented limitation |
| Remote attacker | Out of scope | No network exposure beyond loopback |

## 3. Threat table

| ID | Threat | Likelihood | Impact | Mitigation | Verification (phase) |
|---|---|---|---|---|---|
| `T-01` | Patient A reads patient B's documents, observations, or drafts | Medium (IDOR) | Critical | Server-side scope check on every patient-data route; IDs never trusted from the body; `403`/`404` without existence leak | `NEG-01`, `NEG-02`, `NEG-10` (P2/P7) |
| `T-02` | Unverified/OCR-garbled value reaches a draft or rule as if trusted | Medium | Critical | `verification_status` gate; tools return verified-only; blocking gate halts the graph | `NEG-06`, `SAFE-02` (P5/P7) |
| `T-03` | A follow-up task or notification exists without doctor approval | Low (design defect) | Critical | Task FK to `approval_decision`; unique constraint; decision-only creation path | `SAFE-01`, `NEG-08` (P5/P7) |
| `T-04` | Prompt injection in an uploaded document changes instructions, tools, scope, or approval state | Medium | High | Text treated strictly as data; deterministic extraction; single no-side-effect model tool; delimited untrusted block; injection fixture | `NEG-11` (P3/P5/P7) |
| `T-05` | LLM fabricates a clinical claim not present in evidence | Medium | High | Claim-level citations; validator drops unsupported claims; number check; prohibited-content filter; fallback on failure | `SAFE-05`, `EVAL-03` (P5/P7) |
| `T-06` | Duplicate approval or replay creates two tasks / two notifications | Medium | Medium | Idempotency keys + unique indexes; identical replay returns stored result | `NEG-07`, `NEG-09` (P7) |
| `T-07` | Restart mid-approval loses the gate or resumes with stale state | Medium | High | Checkpoint before interrupt; resume validates status and version; kill/restart test | `RESUME-01` (P7) |
| `T-08` | Malicious or oversized upload exhausts resources or crashes the parser | Medium | Medium | Magic-byte check, 10 MiB cap, 20-page cap, 20 s parse timeout, per-page OCR cap, fail-closed errors | `NEG-03..05` (P3/P7) |
| `T-09` | Silent unit/date misinterpretation (e.g. `03/04`, `mmol/L`, OCR `1O5`) | High | High | Unit allowlist, ambiguity flags, blocking verification, no conversion | `GOLD-EX-09..12`, `SAFE-02` (P3/P7) |
| `T-10` | Wrong-patient document filed under the current patient | Medium | Critical | Document↔patient reference check (`DR-010`), mismatch blocks, explicit confirmation | `SAFE-06` (P3/P4) |
| `T-11` | Audit trail contains sensitive text or is tampered with | Medium | Medium | `safe_detail` only; no body text; append-only; unique idempotency key; reviewer grep test | `NEG-14` (P7) |
| `T-12` | Secrets, runtime DBs, uploads, or model weights committed | Medium | High | `.gitignore`, synthetic-only fixtures, PR review, repo scan | `SEC-06` (P1/P7) |
| `T-13` | External messaging added accidentally or via a dependency | Low | Critical | No transport code; dependency allowlist review; repository scan for SMTP/Twilio/etc. | `NEG-15` (P6/P7) |
| `T-14` | Local model outage mid-demo | High | Low | Labelled fallback; preflight check; offline demo path | `LLM-04` (P5/P7) |
| `T-15` | Demo data reset while a run is active, producing inconsistent state | Low | Medium | Reset refused when a run is active; full rebuild of DB/checkpoints/uploads | `NEG-12` (P6) |
| `T-16` | Credential stuffing / brute force on local demo login | Low | Low | Seeded accounts, rate limit, no public exposure | `NEG-10` (P2/P7) |
| `T-17` | Reviewer misreads demo output as clinical advice | Medium | High | Persistent disclaimer in UI/drafts/fixtures; neutral wording rules; demo script wording lock | Wording audit (P0/P8) |
| `T-18` | Agent silently expands scope or auto-approves during a later phase | Low | Critical | `AGENTS.md` phase/scope rules, PR review, no auto-merge, phase gate statuses | Process (every PR) |

## 4. Threat-to-requirement mapping

| Requirement | Threats covered |
|---|---|
| `REQ-AUTH-01..03` | `T-01`, `T-16` |
| `REQ-ING-01..05` | `T-08`, `T-09` |
| `REQ-VERIFY-01..03` | `T-02`, `T-09`, `T-10` |
| `REQ-RULE-01..03` | `T-02`, `T-05` |
| `REQ-GRAPH-01..05` | `T-06`, `T-07`, `T-18` |
| `REQ-LLM-01..04` | `T-04`, `T-05`, `T-14` |
| `REQ-TASK-01/02`, `REQ-AUDIT-01/02` | `T-03`, `T-11` |
| `REQ-SEC-01..06` | `T-01`, `T-04`, `T-12`, `T-13`, `T-17` |

## 5. Out of scope

- Protecting a machine from a user who already has local admin access (plaintext SQLite, no encryption at rest).
- Multi-user concurrency, horizontal scaling, network exposure, cloud IAM, DDoS, supply-chain attestation, or SBOM signing.
- Regulatory regimes (HIPAA/GDPR/medical-device) — the project makes no compliance claim and would need a separate assessment.
- Model provenance/licensing assurance beyond "owner verified the model terms".

## 6. Verification status

| Item | Status |
|---|---|
| Threat table and mitigations documented | Done in P0 |
| Repository wording/dependency audit | Documentation-level checks only (see phase report) |
| Negative tests `NEG-01..15` | **Not executed** — defined for P2–P7 |
| Restart/resume test | **Not executed** — P7 |
| Injection fixture | **Not executed** — P3/P5 |

## 7. Residual risks accepted for the MVP

| Risk | Why accepted | Owner-visible consequence |
|---|---|---|
| No encryption at rest | Local synthetic demo only | Anyone with the machine can read the demo DB |
| Best-effort content filter | Cannot be exhaustive | Human approval remains the true control |
| Single OCR language / limited layouts | Scope control | Case C demonstrates manual correction as a feature |
| Small model quality | Hardware constraint | Fallback and honest provenance |
| Plaintext session storage choice | Simplicity | Documented as demo-only limitation |
