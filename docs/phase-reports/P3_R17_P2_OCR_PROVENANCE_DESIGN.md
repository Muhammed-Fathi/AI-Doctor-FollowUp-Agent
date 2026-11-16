# P3-R17 (P2) — Durable OCR provenance and reviewability: design proposal

**Status: PROPOSAL ONLY. Not implemented. Requires owner approval before any code,
migration, endpoint or UI work.** Written in response to ruling `5915830616` P2, which
also forbids adding new API endpoints, migrations or UI features without identifying
the required governance approval. This document identifies it.

## 1. The gap, precisely

`EXTRACTION_PROVENANCE.md` §5 states the rule:

> `char_end > char_start`; spans are bounded by **the stored page text** length.

and §5 rule 4 requires:

> The UI must be able to render the source page/snippet for any cited claim
> (read-only viewer), so the doctor can audit the extraction (`US-09`).

`field_parser.py`'s module docstring repeats it: a span "can always be re-resolved
against the stored page text".

**There is no stored page text.** `span_is_resolvable()` is evaluated in memory during
`intake.run_extraction()` against `PageText` objects that are discarded when the request
ends. `grep __tablename__` over `app/db/models.py` yields 12 tables, none of which holds
page or OCR text.

Consequences, measured in §2-Q4 of the analysis:

| Question | Can it be answered today? |
|---|---|
| Is the original image retrievable? | **Yes** — `GET /{id}/file`, byte-identical. |
| Is `raw_text` for each fact retrievable? | **Yes** — bounded to 300 chars at persist time. |
| Is the **full OCR page text** retrievable? | **No.** |
| Can a doctor see that the engine collapsed a column gap? | **No.** |
| Can a span be re-resolved after the request? | **No.** |

So the doctor can compare *a 300-character excerpt* against the image, but cannot
compare *what the engine actually read*. For the R17 case specifically, the substitution
`1O5`→`105` is visible in the image and invisible in the excerpt, because the excerpt is
the already-substituted `105`.

## 2. Why this cannot be fixed inside the current contracts

Four constraints collide:

1. **No text in the audit trail.** `API_CONTRACT.md` §1.1 rule 1 and `REQ-AUDIT-02`
   forbid document text in audit detail and error bodies. A provenance store must
   therefore be a *scoped read*, not an audit export.
2. **No new endpoint without approval.** The contract declares 16 paths / 17 operations
   (`check_openapi.py` asserts exactly this). Any read surface changes the OpenAPI
   contract artifact.
3. **No migration without approval.** A new table or column is a `DATA_DICTIONARY.md`
   change, and the dictionary is a locked P0 contract.
4. **Retention is explicitly post-MVP.** `DATA_DICTIONARY.md` §531 defers "retention
   jobs, encryption at rest" to P7. Persisting clinical page text without a retention
   rule is therefore a regression against a documented deferral.

## 3. Options considered

| # | Option | Persists text? | Migration | New endpoint | Verdict |
|---|---|---|---|---|---|
| A | Nothing (status quo) | no | no | no | Keeps a documented contract untrue. Not acceptable long-term. |
| B | Put OCR text in `document.failure_code` | yes | no | no | **Rejected.** §112 documents that column as "Mirrors tool error codes"; it is bounded to 48 chars and is surfaced to clients. Silently repurposing a locked column is exactly the semantic change the ruling forbids. |
| C | Widen `ExtractionAttemptSummary` to carry `text_char_count`/`engine_confidence`/`preprocessing` (already stored in `extraction_attempt`) | no | no | no (field addition to an existing response) | **Cheap, partial, still a wire change.** Gives a doctor *whether* text was read and how much, not *what*. Does not satisfy §5 rule 4. |
| D | New `document_page_text` table + scoped read endpoint | yes | yes | yes | **Recommended**, needs approval. |
| E | Recompute text on demand from the stored image | no | no | yes | Tempting but **rejected**: re-OCRing produces *different* text (a different engine version or dpi yields a different reading), so it cannot re-resolve the span that was actually cited. It would fabricate evidence rather than preserve it. |

Option E matters: "just OCR it again when the doctor looks" is the obvious cheap answer
and it is wrong for the same reason `_normalize_number` refuses to repair `1O5`.

## 4. Recommended design (Option D)

### 4.1 Storage

```text
document_page_text
  id                TEXT(36)  PK
  document_id       TEXT(36)  NOT NULL FK document.id ON DELETE CASCADE
  page_index        INT       NOT NULL
  extractor         TEXT(16)  NOT NULL   -- pypdf | tesseract
  tool_version      TEXT(64)  NULL       -- from extraction_attempt, not invented
  text              TEXT      NOT NULL   -- bounded by the same page limit as intake
  char_count        INT       NOT NULL
  sha256            TEXT(64)  NOT NULL   -- of the stored text, for integrity + dedupe
  created_at        TEXT(20)  NOT NULL
  UNIQUE (document_id, page_index)
```

Written once, in the same transaction as the facts it describes, by
`intake.run_extraction()`. Immutable thereafter — a re-extraction would be a new
document row under the existing duplicate-hash rule, so no update path is needed.

Bounded by the existing `max_page_chars` setting so a hostile page cannot inflate the
database; a truncated page records `char_count` as the stored length and the span
validator treats anything beyond it as unresolvable (fail closed, same as today).

### 4.2 Access and isolation

Reuses the existing guard, no new authorization model:

* `require_document_read_access(db, principal, document)` — the same call
  `GET /{id}/file` already makes, so patient-owner and assigned-doctor scoping is
  inherited rather than re-implemented.
* Doctors additionally pass `require_doctor_document_scope` for the fact-level view.
* Cross-patient access yields the existing uniform `404`, never a `403` that would
  confirm existence.

### 4.3 Read surface

```text
GET /api/v1/documents/{document_id}/text        (doctor only, scope-checked)

200 {
  document_id, pages: [ { page_index, extractor, tool_version, char_count,
                          text, sha256 } ],
  notice: "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"
}
```

`text` is returned so the doctor can diff it against the image. It is **not** added to
`ExtractionResponse`, deliberately: that response is metadata-only today
(`read_document`'s description says "no clinical value and no extracted text are
returned") and overloading it would break the patient/doctor shape symmetry.

### 4.4 Security

| Risk | Control |
|---|---|
| Injection text in the page being rendered as HTML | The API returns JSON; rendering is the client's problem and must escape. `untrusted_content_detected` is already recorded at intake. |
| Text used as a prompt upstream | It is not — no LLM is in this path (P3 scope). |
| Unbounded response size | Page count and per-page chars are already bounded at intake. |
| PHI exposure | The project is synthetic-only by rule (`AGENTS.md`); this adds no real-PHI surface, but the retention decision below assumes that holds. |
| Text in logs/errors | Explicitly not logged; the endpoint is a read, and error paths keep the existing neutral details. |

### 4.5 Retention — the open governance question

`DATA_DICTIONARY.md` §531 defers retention to P7. Persisting text before a retention rule
exists is a policy decision, not an engineering one. Three coherent positions:

1. **Persist with the document, delete with it** (CASCADE). Simplest; inherits whatever
   retention the document itself has, which is currently "forever in the demo".
2. **Persist only while a document is not `verified`**, purge on verification. Keeps
   review evidence during review, drops it after. Defensible, needs a job and a
   documented exception to immutability.
3. **Do not persist; accept the limitation.** Amend §5 to say spans are resolvable *at
   intake only*, and drop the §5 rule-4 UI claim until P7.

**Recommendation: position 1 for the demo, with the retention gap stated in the report
rather than papered over.** It is the smallest change consistent with the contract as
written, and it preserves evidence instead of destroying it — errs toward auditability.
Position 3 is the honest alternative if you would rather not expand stored data at all;
it costs a contract amendment and an admitted gap in `US-09`.

## 5. Approval required

| Change | Artifact affected | Approval |
|---|---|---|
| `document_page_text` table + migration `0004` | `DATA_DICTIONARY.md` §2 (locked) | **Owner** |
| `GET /{id}/text` | `API_CONTRACT.md`, `openapi.phase0.yaml`, `check_openapi.py` baseline (16→17 paths) | **Owner** |
| Retention position 1/2/3 | `DATA_DICTIONARY.md` §531 deferral | **Owner** |
| Option C only (attempt metadata fields) | `ExtractionAttemptSummary` wire shape | **Owner** (smaller blast radius; does not satisfy §5 rule 4) |

Nothing in this section has been implemented. There is no migration, no endpoint and no
schema change in the current branch, and `check_openapi.py` still reports
`16 paths / 17 operations`.

## 6. Interim mitigation (already in place, no approval needed)

Until this is approved, the two things a reviewer can do today are:

1. `GET /{id}/file` for the original bytes.
2. Per-fact `evidence.raw_text` + `page_index`/`char_start`/`char_end`.

That is enough to prove *what was cited*, not *what the engine saw*. The acceptance
probe's `engine_ocr_text` field remains the only place the raw OCR text appears, and it
exists only for the probe's own single fixture — it is not a product capability and
must not be cited as one.
