# API Contract Proposal

| Field | Value |
|---|---|
| Document ID | `CTR-API-001` |
| Version | `0.4.0-p0` |
| Status | **IN REVIEW — proposal only; no server exists in P0** |
| Phase | `P0` (design). Implementation: P2 (auth/data), P3 (documents), P5 (workflows), P6 (UI) |
| Machine-readable companion | [`openapi.phase0.yaml`](openapi.phase0.yaml) |
| Related | `REQ-AUTH-01..03`, `REQ-ING-01`, `REQ-VERIFY-03`, `REQ-GRAPH-03`, `REQ-TASK-01/02`, `REQ-AUDIT-02`, `REQ-DATA-04`, `REQ-OPS-04` |
| Revision | 0.2.0: exposes observation `trust_level`, `verification_issues[]` (pre-verification), review `trust_basis`, run `as_of_utc`, and the deterministic `finalizing` state (`P0-R03`, `P0-R04`, `P0-R05`, `P0-R07`) |

> All endpoints below are proposals. Nothing is binding until the OpenAPI file is validated at P1 and
> contract tests exist (P2+). No endpoint is implemented in Phase 0.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `http://127.0.0.1:8000` (local only; no public deployment) |
| Versioning | URL prefix `/api/v1`; breaking changes bump the prefix |
| Auth | Opaque session token in `Authorization: Bearer <token>` (cookie mode optional at P2). Roles `doctor`, `patient`, `demo_admin` |
| Content type | `application/json` except uploads (`multipart/form-data`) |
| Timestamps | UTC ISO-8601 (`2026-11-03T09:15:00Z`); display time zone is a client concern |
| IDs | UUIDv4 strings |
| Idempotency | Mutating endpoints accept `Idempotency-Key` (client-generated UUID). Server derives the stored key; repeats return the original result |
| Pagination | `?limit=` (default 20, max 100) and `?cursor=`; responses include `next_cursor` |
| Errors | RFC-9457-style problem object (below), stable machine-readable `code` |
| Rate/size limits | Upload ≤ 10 MiB, ≤ 20 pages; JSON body ≤ 256 KiB |
| Traceability | Every response that depends on a run includes `run_id` and `as_of_utc`; every clinical fact carries evidence references |
| Provenance labels | Observations expose `trust_level`; review items expose `trust_basis`; the API never calls a self-reported value doctor-verified |
| Prohibited | No endpoint sends messages, prescribes, exports datasets, or returns model-only clinical conclusions |

### 1.1 Error envelope

```json
{
  "type": "https://demo.local/errors/E_UNVERIFIED_FACT",
  "title": "Unverified fact",
  "status": 409,
  "code": "E_UNVERIFIED_FACT",
  "detail": "1 fact is still pending verification; the workflow cannot continue.",
  "instance": "/api/v1/workflows/follow-up",
  "request_id": "b0d1…",
  "details": [{"field": "fact_id", "reason": "verification_status=pending"}]
}
```

Rules:

1. `code` is stable and documented in §4; `detail` never contains document body text, secrets, stack traces, or another patient's data.
1a. **DTO redaction is explicit (`P0-R13`).** Document detail exposes `attempts[]` as `ExtractionAttemptSummary` —
   route, outcome, duration, tool version, timestamp only. Typed attempt metadata (`preprocessing`,
   `engine_confidence`, `text_char_count`, `page_from/to`, `attempt_id`) stays in the state/DB contract and is
   surfaced to a doctor solely through `TraceEvent.detail` (`TriageEventDetail`), where
   `engine_confidence` is nullable and engine-reported (`null` = not reported, never invented). A client must not
   expect extraction metrics on the document endpoint.
1b. `mapping_version` is internal in the MVP: it is persisted on the run for replay/explanation but is **not**
   exposed by any endpoint, so no client contract depends on it.
2. `401` responses do not reveal whether a patient exists (`REQ-AUTH-03`, `REQ-SEC-01`).
3. `403` and `404` are used deliberately: `403` when the actor is authenticated but out of scope; `404` when the resource must not be acknowledged at all.
4. Every denial appends an `access.denied` audit event with a `request_id`, never with the requested payload.

### 1.2 Security scheme

Bearer token, roles enforced server-side. Token TTL and refresh are P2 decisions; the MVP may use a signed opaque token stored in the local DB with an expiry column. There is **no** public signup, password reset email, or OAuth provider.

## 2. Endpoint catalogue

Legend for "Auth": `public` (health only) · `any` (any authenticated role) · `doctor` · `patient` · `demo_admin` (and `DEMO_MODE=true`).

### 2.1 System

| Method | Path | Auth | Purpose | Success | Notes |
|---|---|---|---|---|---|
| GET | `/health` | public | Liveness + dependency status | `200 {status, version, db, ollama, tesseract}` | Dependency fields are `ok`/`unavailable`/`not_configured`; a missing local model must not fail liveness |
| GET | `/version` | public | Build/version metadata | `200 {app_version, git_sha, workflow_version, policy_version, api_version}` | No secrets |
| GET | `/openapi.json` | public | Generated schema | `200` | Served by FastAPI, not hand-maintained in code |

`/health` must never report a clinical or demo-success state; it reports process and dependency facts only.

### 2.2 Authentication

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | public | `{username, password}` | `200 {access_token, token_type, expires_at, user}` | `401 E_INVALID_CREDENTIALS`, `429 E_RATE_LIMITED` |
| GET | `/api/v1/auth/me` | any | – | `200 User` | `401 E_UNAUTHENTICATED` |
| POST | `/api/v1/auth/logout` | any | – | `204` | `401` |

Login is rate-limited and constant-time-ish in failure messaging (details at P2). No password appears in any response or log.

### 2.3 Doctor — patients and timeline

| Method | Path | Auth | Purpose | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/v1/doctor/patients` | doctor | Assigned synthetic patients only | `200 {items[], next_cursor}` | `401`, `403 E_SCOPE_VIOLATION` |
| GET | `/api/v1/doctor/patients/{patient_id}` | doctor | Patient header + counts | `200 Patient` | `403`, `404 E_NOT_FOUND` |
| GET | `/api/v1/doctor/patients/{patient_id}/timeline` | doctor | Observations, documents, review items, tasks in time order | `200 {observations[], documents[], review_items[], tasks[]}` | `403`, `404` |
| GET | `/api/v1/doctor/patients/{patient_id}/observations` | doctor | Filtered series (`?measure_type=&from=&to=`) | `200 {items[]}` | `403`, `404`, `400 E_VALIDATION` |

`patient_id` is validated against `patient.assigned_doctor_id`; there is no "all patients" variant for non-admins.

### 2.4 Patient — check-ins and uploads

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/v1/patient/check-ins` | patient (self scope) | `{measured_at, measure_type, value, unit, note?}` | `201 Observation` | `400 E_VALIDATION`, `400 E_UNIT_NOT_ALLOWED`, `403`, `409 E_DUPLICATE_CHECKIN` |
| GET | `/api/v1/patient/check-ins` | patient (self) | – | `200 {items[]}` | `401` |
| POST | `/api/v1/documents/upload` | patient (self) | `multipart/form-data`: `file`, `declared_type?` | `202 {document_id, status:"pending_extraction", sha256, page_count}` | `400 E_VALIDATION`, `413 E_FILE_TOO_LARGE`, `415 E_UNSUPPORTED_MEDIA`, `422 E_PAGE_LIMIT_EXCEEDED`, `409 E_DUPLICATE_DOCUMENT` |
| GET | `/api/v1/documents/{document_id}` | patient (self) / doctor (assigned) | – | `200 {document metadata, extraction_status}` | `403`, `404` |
| GET | `/api/v1/documents/{document_id}/extraction` | doctor (assigned) | – | `200 {facts[], attempts[], verification_issues[], document_status}` | `403`, `404`, `409 E_EXTRACTION_PENDING` |
| POST | `/api/v1/documents/{document_id}/verify` | doctor (assigned) | `{fact_id, decision:"verified"\|"rejected"\|"corrected", corrected_value?, corrected_unit?, reason?}` | `200 {fact, verification, document_status}` | `400 E_VALIDATION`, `403`, `404`, `409 E_FACT_ALREADY_DECIDED` |
| GET | `/api/v1/documents/{document_id}/file` | doctor (assigned) / patient (self) | – | `200` binary | `403`, `404` |

Patient responses intentionally exclude extracted values, review items, drafts, and tasks (`US-05`, `US-11`). The patient view shows status strings only.

Upload validation order (fixed): declared size → magic bytes → allowed MIME → page count (PDF) → image dimensions → store hash → reject on duplicate hash for the same patient.

### 2.5 Workflows

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/v1/workflows/follow-up` | doctor (assigned) | `{patient_id, observation_ids?, document_ids?, client_request_id}` + `Idempotency-Key` | `202 {run_id, status, current_node}` or `200` existing run on repeat | `400`, `403`, `409 E_IDEMPOTENCY_CONFLICT`, `409 E_UNVERIFIED_FACT`, `422 E_RUN_LIMIT_REACHED`, `503 E_MODEL_UNAVAILABLE` (only if fallback also disabled) |
| GET | `/api/v1/workflows/{run_id}` | doctor (assigned) | – | `200 {run, draft?, verification_issues[], review_items[], blocking_facts[], model_metadata, events[]}` | `403`, `404` |
| GET | `/api/v1/workflows/{run_id}/trace` | doctor (assigned) | – | `200 {run_id, events[]}` where each event has `node`, `attempt`, `started_at`, `ended_at`, `outcome`, `tools_called` and a **typed** `detail` (`null` for nodes without a bounded decision) | `403`, `404` |
| POST | `/api/v1/workflows/{run_id}/decisions` | doctor (assigned) | `{decision:"approve"\|"edit"\|"reject", edited_summary?, reason?}` | `200 {run, decision, task?, notification?}` | `400`, `403`, `404`, `409 E_APPROVAL_CONFLICT`, `409 E_RUN_NOT_PAUSED`, `409 E_WORKFLOW_VERSION_MISMATCH` |
| POST | `/api/v1/workflows/{run_id}/resume` | doctor (assigned) | `{resume_reason:"facts_verified"}` | `202 {run, status}` | `400`, `403`, `404`, `409 E_RUN_NOT_PAUSED`, `409 E_UNVERIFIED_FACT` |

Rules:

1. `POST /decisions` is the **only** path to task creation. `patient_id`, `doctor_id`, and facts are never taken from the request body.
1a. A decision is applied in **two ordered app-DB transactions**: (A) the decision row + `awaiting_decision →
   `finalizing`; (B) task + notification + audit finalization + `finalizing → completed`. They are separate
   because the LangGraph checkpoint file cannot join an app-DB transaction; phase B is idempotent through the
   derived task key, and a restart reconciles from the app DB (`STATE_AND_GRAPH_CONTRACT.md` §7.2–§7.3).
1b. `verification_issues[]` (pre-verification, blocking) and `review_items[]` (post-verification, `DR-*`) are
   separate arrays with separate UI sections; a client must not merge or relabel them.
1c. Trace `detail` payloads are enum/count/ID-only by contract. A client that receives any free text in a detail
   field should treat the response as malformed; the server never emits document content there (`REQ-AUDIT-02`).
1d. Observations appear with `trust_level`; a client must render `self_reported_validated` as "self-reported" and
   must not present it as verified. Comparison responses carry `trust_basis` for the same reason (`P0-R11`).
2. `approve` and `edit` return the created task + notification; `reject` returns neither (`US-10`). The task ID is
   derived deterministically from the stored decision, so a retried or restarted request cannot create a second task.
3. A duplicate identical decision returns `200` with the stored result (idempotent); a conflicting decision returns `409 E_APPROVAL_CONFLICT`.
4. `503 E_MODEL_UNAVAILABLE` is returned only when the fallback is explicitly disabled by configuration; the default demo returns a labelled fallback draft instead (`REQ-LLM-04`).

### 2.6 Review items, tasks, notifications, audit

| Method | Path | Auth | Purpose | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/v1/doctor/review-items` | doctor | Open review items (assigned patients), filter `?state=&patient_id=` | `200 {items[]}` | `403` |
| GET | `/api/v1/doctor/review-items/{review_item_id}` | doctor | Item + evidence | `200 ReviewItem` | `403`, `404` |
| POST | `/api/v1/doctor/review-items/{review_item_id}/decision` | doctor | `{action:"acknowledge"\|"dismiss", reason?}` | `200 ReviewItem` | `400`, `403`, `404`, `409 E_REVIEW_ALREADY_DECIDED` |
| GET | `/api/v1/doctor/tasks` | doctor | Tasks for assigned patients (`?status=&due_before=`) | `200 {items[]}` | `403` |
| POST | `/api/v1/doctor/tasks/{task_id}/complete` | doctor | Marks complete | `200 FollowUpTask` | `403`, `404`, `409 E_TASK_ALREADY_COMPLETED` |
| GET | `/api/v1/notifications` | any | In-app notifications for the caller | `200 {items[], unread_count}` | `401` |
| POST | `/api/v1/notifications/{notification_id}/read` | any | Marks read | `200` | `403`, `404` |
| GET | `/api/v1/doctor/audit-events` | doctor | Scoped audit trail (`?patient_id=&run_id=`) | `200 {items[]}` | `403` |

Review-item decisions do **not** change clinical data; they record that the doctor looked at a workflow prompt. Dismissal requires a reason at P6 (open question `OQ-A02`).

### 2.7 Demo administration

| Method | Path | Auth | Purpose | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/v1/demo/reset` | demo_admin **and** `DEMO_MODE=true` | Rebuild synthetic fixtures; deletes runtime DB/checkpoints/uploads | `200 {reset_at, cases_loaded[]}` | `403 E_DEMO_MODE_REQUIRED`, `409 E_RUN_IN_PROGRESS` |
| GET | `/api/v1/demo/status` | any authenticated | Which synthetic cases are seeded, provider status | `200` | `401` |

Reset is refused while any run is `running`, `awaiting_decision`, or `needs_verification`.

## 3. Schemas (summary)

Full JSON Schemas live in `openapi.phase0.yaml`. Field-level meaning lives in `DATA_DICTIONARY.md`.

| Schema | Key fields |
|---|---|
| `User` | `id, username, display_name, role, patient_id?, timezone` |
| `Observation` | `id, patient_id, measure_type, value, unit, measured_at, source, validation, trust_level, verification (nullable object: `verified_by`, `verified_at`)` |
| `DocumentMeta` | `id, patient_id, filename, mime_type, sha256, size_bytes, page_count, extraction_status, uploaded_at` |
| `ExtractedFact` | `fact_id, document_id, field_name, raw_text, normalized_value, unit, page_index, char_start, char_end, quality_flags, confidence, verification_status, evidence` |
| `VerificationIssue` | `issue_id, issue_type (VI-001…VI-006), reason_code, blocking:true, message, document_id, fact_ids[], evidence[]` — never has a `rule_id` |
| `ReviewItem` | `review_item_id, rule_id (DR-001/003/005/006/008/009), reason_code, workflow_hint, message, trust_basis, evidence[], policy_version, demo_only:true, state` |
| `DraftSummary` | `draft_id, provider, model, execution_status, prompt_version, latency_ms, body, claims[], uncertainties[], not_asserted[], disclaimer` |
| `WorkflowRun` | `run_id, status, current_node, workflow_version, policy_version, as_of_utc, halt_reason, started_at, updated_at` |
| `ApprovalDecision` | `decision_id, decision, edited_summary?, reason?, doctor_id, decided_at` |
| `FollowUpTask` | `id, patient_id, approval_decision_id, title, note?, due_date?, status` |
| `Notification` | `id, text, task_id?, read_at?, created_at` |
| `Problem` | `type, title, status, code, detail, instance, request_id, details[]` |

`DraftSummary.disclaimer` is a constant string: `EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE`.

## 4. Error catalogue

| Code | HTTP | Meaning | Client action |
|---|---|---|---|
| `E_UNAUTHENTICATED` | 401 | Missing/expired session | Re-authenticate |
| `E_INVALID_CREDENTIALS` | 401 | Login failed | Retry carefully; rate-limited |
| `E_FORBIDDEN` | 403 | Role lacks capability | Do not retry |
| `E_SCOPE_VIOLATION` | 403 | Actor outside patient/run scope; audited | Do not retry |
| `E_DEMO_MODE_REQUIRED` | 403 | Admin action outside demo mode | Enable demo mode locally |
| `E_NOT_FOUND` | 404 | Resource absent or not acknowledged | Do not retry |
| `E_VALIDATION` | 400 | Schema/field error | Fix request |
| `E_UNIT_NOT_ALLOWED` | 400 | Unit not in allowlist | Use an allowed unit |
| `E_UNSUPPORTED_MEDIA` | 415 | MIME/magic-byte mismatch | Upload PDF/PNG/JPEG |
| `E_FILE_TOO_LARGE` | 413 | > 10 MiB | Resize |
| `E_PAGE_LIMIT_EXCEEDED` | 422 | > 20 pages | Split the document |
| `E_DUPLICATE_DOCUMENT` | 409 | Same sha256 for this patient | Reuse existing document |
| `E_DUPLICATE_CHECKIN` | 409 | Same type/value/timestamp for this patient | Treat as success |
| `E_EXTRACTION_PENDING` | 409 | Extraction not finished | Poll `GET /documents/{id}` |
| `E_FACT_ALREADY_DECIDED` | 409 | Verification is append-only | Fetch latest state |
| `E_UNVERIFIED_FACT` | 409 | Blocking **fact** still pending/rejected (facts only — never raised for an observation) | Verify the fact, then resume |
| `E_IDEMPOTENCY_CONFLICT` | 409 | Same key, different payload | Generate a new key |
| `E_APPROVAL_CONFLICT` | 409 | A different decision already exists for the run | Fetch the run |
| `E_RUN_NOT_PAUSED` | 409 | Resume/decision on a run that is not paused | Fetch status |
| `E_WORKFLOW_VERSION_MISMATCH` | 409 | Checkpoint created by another graph version | Start a new run |
| `E_REVIEW_ALREADY_DECIDED` | 409 | Review item already acknowledged/dismissed | Fetch item |
| `E_TASK_ALREADY_COMPLETED` | 409 | Task already complete | No-op |
| `E_RUN_LIMIT_REACHED` | 422 | Demo cap on concurrent runs | Finish/reset |
| `E_MODEL_UNAVAILABLE` | 503 | Ollama down and fallback disabled | Use fallback or start Ollama |
| `E_RATE_LIMITED` | 429 | Login or upload throttled | Back off |
| `E_INTERNAL` | 500 | Unexpected failure (no details leaked) | Report with `request_id` |
| `E_DEPENDENCY_MISSING` | 503 | Tesseract/PDF tooling missing | Install per P1 docs |

## 5. Negative and security test mapping

| Test ID | Scenario | Expected | Requirement |
|---|---|---|---|
| `NEG-01` | Patient A calls `GET /documents/{doc_of_B}/extraction` | `403 E_SCOPE_VIOLATION` + audit | `REQ-SEC-01` |
| `NEG-02` | Doctor requests an unassigned patient's timeline | `403`/`404`, no data | `REQ-SEC-01` |
| `NEG-03` | Upload with `.pdf` extension but PNG bytes | `415 E_UNSUPPORTED_MEDIA` | `REQ-ING-01` |
| `NEG-04` | 12 MiB PDF | `413 E_FILE_TOO_LARGE` | `REQ-ING-01` |
| `NEG-05` | 25-page PDF | `422 E_PAGE_LIMIT_EXCEEDED` | `REQ-ING-05` |
| `NEG-06` | Start workflow with one pending fact | `409 E_UNVERIFIED_FACT` | `REQ-SEC-04` |
| `NEG-07` | Approve twice with identical body | Second returns `200`, one task | `REQ-GRAPH-04` |
| `NEG-08` | Approve, then reject same run | `409 E_APPROVAL_CONFLICT` | `REQ-GRAPH-03` |
| `NEG-09` | Resume a `completed` run | `200` stored result, no new task | `REQ-GRAPH-03` |
| `NEG-10` | Unauthenticated `GET /doctor/patients` | `401`, no existence leak | `REQ-AUTH-03` |
| `NEG-11` | Document body containing "ignore previous instructions…" | No tool/state change; content quoted only as data | `REQ-SEC-02` |
| `NEG-12` | `POST /demo/reset` with `DEMO_MODE=false` | `403 E_DEMO_MODE_REQUIRED` | `REQ-OPS-02` |
| `NEG-13` | Check-in with unit `mmol/L` for glucose | `400 E_UNIT_NOT_ALLOWED` | `REQ-DATA-02` |
| `NEG-14` | Response/log inspector over a seeded demo run for document text | No document body in audit `safe_detail` | `REQ-AUDIT-02` |
| `NEG-15` | Search repository for `smtp`, `sendgrid`, `twilio`, `requests.post` to external hosts | None found | `REQ-SEC-03` |
| `NEG-16` | Patient calls `GET /doctor/review-items` | `403`, no review or verification content | `REQ-AUTH-02` |
| `NEG-17` | Patient calls `POST /workflows/follow-up` | `403` | `REQ-AUTH-02` |
| `NEG-18` | Re-upload identical bytes for the same patient | `409 E_DUPLICATE_DOCUMENT`, existing document reused | `REQ-ING-04` |
| `NEG-19` | Use an observation with `validation=rejected` as a comparison baseline | Excluded from `read_observations`; no comparison, no `DR-*` item | `REQ-DATA-04` |
| `NEG-20` | Request a document extraction where a fact is pending | Blocking `VI-002`; no `review_items[]` entries and no draft | `REQ-SEC-04` |
| `NEG-21` | Self-reported observation in a review message or draft claim | Rendered with `(self-reported)`; never described as verified | `REQ-DATA-04` |

None of these are executed in P0. They become executable at the phase listed in
[`../evaluation/EVALUATION_MATRIX.md`](../evaluation/EVALUATION_MATRIX.md).

## 6. Open questions

| ID | Question | Default |
|---|---|---|
| `OQ-A01` | Bearer header vs httpOnly cookie session? | Bearer header for the MVP; cookie hardening at P7 |
| `OQ-A02` | Is a required dismissal reason for review items useful or noisy? | Optional in MVP, revisit at P6 |
| `OQ-A03` | Should `GET /documents/{id}/file` stream originals to patients? | Only the patient's own upload; doctors see originals for assigned patients |
| `OQ-A04` | Do we need a polling `GET /workflows/{run_id}/events?after=` cursor for a live trace? | Simple polling of `GET /workflows/{run_id}` in the MVP |
