# P3-R21 — Document rejection / recovery design (owner direction: Option 2)

**Status: DESIGN AND SPECIFICATION ONLY.** No production code, API, schema,
migration, OCR configuration, fixture or UI change is proposed for implementation
without the explicit owner authorization in §9. PR #10 stays **DRAFT**; P3 stays
**IN_REVIEW**; `GOLD-EX-11` stays **FAIL / NOT PROVEN**; no merge; P4/P5 not
started.

Base: `18a53b2de5ee9a7cd44d473b78f8ecbaa28fb1f5` (PR #10 head, the last
independently reviewed commit). All code reading, probing and test execution for
this design were done at that commit. **No implementation was started**, because
the owner has not authorized changes. For this documentation-publication step the
Arena session branch `arena/f80e1923-ai-doctor-followup-agent` was fast-forwarded
from `867ab12` (`main`) to `18a53b2`, so this document is committed directly on
the reviewed PR head; `main` and the PR #10 branch were not modified. If
implementation is later authorized, it must begin on a fresh branch based on the
reviewed PR head.

This document is the next increment after
`P3_R20_OCR_CONFIGURATION_DECISION.md` §8.1.6a. The owner selected **Option 2**
("authorize a terminal/recovery design first") as the preferred engineering
direction. This round turns that direction into a concrete, minimal, testable
design. **Nothing here is authorized.**

**Corrigendum R21-B1…B4** (independent review
[`5918165016`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5918165016),
against `a46a7fd`). This revision resolves four targeted findings **without
changing the recommended approach**: B1 terminal timing is now explicitly
**rejection-first** (§4.1); B2 adds patient-safe recovery metadata (§4.9); B3
specifies a tested additive self-FK migration with a safe downgrade refusal
(§4.10); B4 restates the recovery link as a **patient-declared association** and
expands the negative tests (§4.3, §4.4, §4.7, §7). The acceptance matrix is
revised in §7. Nothing in this corrigendum is implementation authorization.

---

## 0. Verified baseline (executed in this session)

| Item | Result | How verified |
|---|---|---|
| PR #10 | **OPEN / DRAFT / UNMERGED**, base `main`, head `18a53b2`, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN` | `gh pr view 10` |
| Reviewed commit | `18a53b2de5ee9a7cd44d473b78f8ecbaa28fb1f5` exists as `refs/pull/10/head` and `refs/heads/arena/ce85d4e6-…` | `git ls-remote`, `git fetch origin pull/10/head` |
| Working tree at base | clean at `18a53b2` | `git status` |
| Local backend suite | **635 passed** in 99.31 s | `pytest backend/tests` (see §0.1) |
| P3 status | **IN_REVIEW** | `docs/roadmap/PHASE_PROGRESS.md` §P3 |

### 0.1 Test-suite environment note

The sandbox has only CPython 3.11 and no project dependencies. A throwaway
virtualenv was built with the pinned runtime/dev packages and the suite was run
there (`635 passed`). The project targets CPython 3.12 (`pyproject.toml`
`requires-python = ">=3.12,<3.13"`); the owner's Windows 3.12 run remains the
authoritative execution. No Windows/Tesseract behaviour was executed here.

### 0.2 First-hand reproduction of the defect (temporary probe, deleted)

A throwaway test module was written, executed against `18a53b2`, and deleted. It
used the existing P3 helpers (`fixtures.build_pdf`, upload, extraction, verify).
Measured results:

| Scenario | `document_status` | persisted issues | Observations |
|---|---|---|---|
| reject `reference_text`, verify the other four | **`verified`** | `VI-002` **open** (`fact_unverified`) | **1** `('glucose', 104.0, 'doctor_verified')` |
| reject `value`, verify the other four | **`verified`** | `VI-002` **open** (`fact_unverified`) | 0 |
| `corrected` on the already-rejected `value` | `409` | — | — |
| `verified` on the already-rejected `value` | `409` | — | — |
| re-upload identical bytes | `409 E_DUPLICATE_DOCUMENT` | — | — |

This confirms the R20 report's §1.1/§1.3 findings and adds one measured fact it
did not state: **a rejected non-measurement fact can currently coexist with a
`doctor_verified` Observation** (the `reference_text` row). The probe file was
deleted; no probe artefact remains in the tree.

---

## 1. Current-state architecture and root cause

### 1.1 The two derivations that disagree

**Document status** — `backend/app/services/documents/verification.py:180`
`_recompute_document_status()`:

```
no facts                 -> failed   (failure_code "no_facts_extracted" is set by intake)
any fact pending         -> needs_verification
all facts rejected       -> failed   (failure_code "all_facts_rejected")
unread measurement       -> needs_verification
otherwise                -> verified
```

It reads **fact statuses only**. It never consults `verification_issue` rows.

**Issue derivation** — `backend/app/services/documents/quality.py:357`
`compute_drafts()` → `issues.py:160` `collect_unverified_issue()`: `VI-002` is
open while any **active** (non-superseded) fact is not `verified`
(`quality.py:139` `superseded_fact_ids()`). A plain rejection is **not**
superseded, so it is counted (owner decision D-14).

**Promotion** — `verification.py:255` `_maybe_promote_document()` reads the
single active verified `value` fact and inserts the Observation. It checks
`VI-006`/`VI-004` but **never checks `document.extraction_status`**. So a
document whose status is `verified` *or* `failed` can still promote.

**Decision** — `verification.py:362` `record_decision()`: append-only. Any
second decision on the same fact returns `409 E_FACT_ALREADY_DECIDED`
(D-11), including `corrected` and `verified`. A `corrected` **first** decision
on a `pending` fact creates a new verified row with
`corrected_from_fact_id=<original>`; the original becomes `rejected` and is
superseded.

### 1.2 Root cause

A plain rejection is a **final** verdict on a fact, but the document state model
treats "every fact decided" as "verified" and the issue model treats the rejected
fact as a permanently open `VI-002`. The two rules are individually correct
(D-11 and D-14) and mutually inconsistent at the document level:

* `verified` is reachable while a blocking `VI-002` is open;
* no doctor action can clear that `VI-002` (every further decision is `409`);
* a `doctor_verified` Observation can be promoted from a document with a
  rejected non-measurement fact (measured in §0.2);
* re-uploading the same bytes is `409 E_DUPLICATE_DOCUMENT`, and re-uploading
  different bytes creates a **new, unlinked** document.

S1 (`P3_R20` §6.2) fixes the first bullet by keeping the document
`needs_verification`, but produces a **non-recoverable hold** with an unclearable
`VI-002`. That is the trade the owner declined to accept as the final answer.

### 1.3 What the design must not touch

* D-11 append-only decisions and the `409` on re-decision.
* D-14 `VI-002` counting (plain rejections still counted; superseded originals
  still excluded).
* Identity protection: `VI-004` is checked **before** the append-only guard and
  can never be cleared by a fact decision (`verification.py:386`).
* Provenance: `raw_text`/span/`extractor`/`corrected_from_fact_id` lineage.
* Duplicate-hash protection: `ux_document_sha_patient (patient_id, sha256)` and
  the `409 E_DUPLICATE_DOCUMENT` contract.
* The closed mapping `map-1.0.0` and the "at most one Observation per document"
  rule.
* OCR configuration (`preserve_interword_spaces` stays off), `GOLD-EX-11`
  expectations, and the synthetic golden fixtures.

---

## 2. Design goals and non-goals

**Goals**

1. A rejected fact must never leave a document `verified` with an open blocking
   issue.
2. A rejected document must have an **honest terminal** state.
3. There must be a **legitimate recovery route** that is linked to the original
   source and preserves the rejection history.
4. Minimal scope: no new endpoint if an existing one can carry the change; no
   migration unless it is genuinely required.

**Non-goals**

* Detecting a wrong-but-approved value (requirement B / `P3_R20` §3). Out of
  scope and unchanged.
* Changing OCR configuration or the parser grammar.
* Reclassifying `GOLD-EX-11`.
* P4/P5 workflow/task/notification surfaces.

---

## 3. Three technically viable approaches

All three share the same **status predicate** change (a rejected active fact
makes the document non-`verified`) and the same **promotion gate** (no Observation
unless the document is `verified`). They differ in *where the terminal state
lives* and *how recovery is modelled*.

### Approach A — terminal `failed` + explicit failure code, recovery = linked re-upload (new document)

* **Status transition model.** Reuse the existing `failed` status. The document
  becomes `failed` when any **active** (non-superseded) fact is `rejected`.
  Add two `failure_code` values: `measurement_rejected` (the rejected set
  contains a `value` fact) and `fact_rejected` (any other active rejected
  fact). `all_facts_rejected` is unchanged. `failed` is already terminal
  (nothing transitions out of it) and is already used for a doctor-decision
  outcome (`all_facts_rejected`).
* **After a doctor rejects a measurement.** The document becomes `failed` /
  `measurement_rejected`; no Observation is promoted; `VI-002` (and `VI-005`
  where the flag survives) stay open as immutable records.
* **Terminal or recoverable.** Terminal in place; recoverable only by a **new**
  document.
* **Recovery attempt.** `POST /documents/upload` gains an optional `recovery_of`
  form field (patient self-scope). The referenced document must belong to the
  same patient and be in a recoverable terminal state. The new document row
  carries `recovered_from_document_id=<old>`; a `document.recovered` audit event
  records the link. The old row is never mutated.
* **Append-only.** The rejection row and its `fact_verification` row are
  untouched; the recovery is a new row, not a revision.
* **Open `VI-002`.** Stays open (D-14). The document status `failed` is the
  terminal signal; the issue is an immutable record, not an actionable blocker.
* **Rejected non-measurement facts.** Same terminal rule (`fact_rejected`), so
  the §0.2 `reference_text` contradiction is fixed. This **subsumes R20-D2** and
  is an explicit owner decision (§9, A2).
* **Duplicate hash.** Unchanged. Same bytes → `409`; different bytes with
  `recovery_of` → a new linked document.
* **New endpoint / migration.** No new endpoint. **One additive column**
  (`document.recovered_from_document_id`, nullable, self-FK, indexed) and one
  migration. No new status value, so no `CHECK` rebuild and no `DocumentStatus`
  enum / OpenAPI enum change.
* **Risks.** `failed` is overloaded (extraction failure vs doctor rejection);
  `failure_code` is semantically extended beyond "tool error codes" (the
  `all_facts_rejected` precedent exists). Both are documented contract changes.
* **Backward compatibility.** Existing documents and `failed` documents are
  unaffected; the new field is nullable. The predicate change alters the status
  of a partial-rejection document from `verified` to `failed` — the intended
  fix.

### Approach B — dedicated terminal `rejected` status, recovery = linked re-upload

* Same as A, but adds `DocumentStatus.REJECTED = "rejected"`.
* **Status transition model.** `rejected` is set by the same predicate; the
  recovery link is the same.
* **Terminal or recoverable.** Terminal `rejected`; recoverable by a new document.
* **Recovery attempt.** Identical to A.
* **Append-only / VI-002 / duplicate hash.** Identical to A.
* **New endpoint / migration.** No new endpoint. **One migration that adds the
  column *and* rebuilds the `status_allowed` CHECK**; `DocumentStatus`,
  `openapi.phase0.yaml`, `DATA_DICTIONARY.md` and the API contract all change.
* **Risks.** Larger contract surface; a client must understand a new status.
  More legible and self-describing than `failed`.
* **Backward compatibility.** Existing rows keep their status; the `CHECK`
  rebuild is additive (old values remain valid).

### Approach C — same-document recovery via a doctor-created replacement fact

* **Status transition model.** Unchanged status derivation, but a new
  `POST /documents/{id}/recover` (doctor-assigned) creates a **new** candidate
  fact for the rejected field with `extractor='manual'`,
  `corrected_from_fact_id=<rejected fact>`, `raw_text` copied from the rejected
  fact, `verification_status='pending'`. The doctor then verifies it; the
  original becomes superseded, `VI-002` resolves, the document returns to
  `verified`.
* **After a doctor rejects a measurement.** The document is non-`verified` until
  a replacement fact is created and verified.
* **Terminal or recoverable.** Recoverable in place (same document id).
* **Recovery attempt.** The new fact row is the attempt; lineage is
  `corrected_from_fact_id`.
* **Append-only.** The rejection row is untouched, but the recovery **bypasses
  the `409` on a second decision** by creating a new fact. This is a
  reinterpretation of D-11's finality, not a violation of its letter.
* **Open `VI-002`.** Resolves via `superseded_fact_ids` (the new fact points at
  the rejected one) — the same mechanism a correction uses.
* **Rejected non-measurement facts.** Same path.
* **Duplicate hash.** Unchanged (no new upload).
* **New endpoint / migration.** **One new endpoint** (which breaks the
  `check_openapi.py` / `test_openapi.py` P3 path allowlist until updated) and
  **no migration**.
* **Risks.** New fact-creation path with its own provenance rules; the
  `raw_text` of a manual fact is not a source slice; it weakens the "a rejection
  is final" position the owner has held since R20 §8.1.4. Larger review surface.

### Comparison

| Requirement | A (recommended) | B | C |
|---|---|---|---|
| Fixes `verified` + open `VI-002` | yes | yes | yes |
| Terminal honest state | `failed` + code | `rejected` | non-`verified` until replaced |
| Recovery route | new linked document | new linked document | same document, new fact |
| New endpoint | no | no | **yes** |
| Migration | 1 additive column | 1 column + `CHECK` rebuild | none |
| Contract/enum change | `failure_code` values + 1 field | new status + 1 field | new endpoint + request/response |
| D-11 finality | preserved | preserved | **reinterpreted** |
| Non-measurement rejection | terminal (`fact_rejected`) | terminal | recoverable |
| Scope | **smallest** | small | largest |

---

## 4. Recommended design — Approach A

### 4.1 Exact status transition model and terminal timing

`_recompute_document_status()` becomes:

```
facts = all facts of the document
if not facts:                                -> failed (intake has already set failure_code = "no_facts_extracted")
if all facts rejected:                       -> failed, failure_code = "all_facts_rejected"
superseded = superseded_fact_ids(facts)
active_rejected = [f for f in facts
                   if f.verification_status == "rejected" and f.id not in superseded]
if active_rejected:
    failure_code = "measurement_rejected" if any(f.field_name == "value" for f in active_rejected)
                   else "fact_rejected"
                                             -> failed
if any fact.pending:                         -> needs_verification
if _unread_measurement_blocks_verification(...): -> needs_verification
                                             -> verified
```

**Terminal timing policy (resolves R21-B1).** The rejection check is
**rejection-first**: it runs before the `pending` check, so the document becomes
terminal `failed` on the **first** plain rejection, even while sibling facts are
still `pending`. The previous revision ordered `pending` first, which meant the
first rejection did not produce a terminal document and `recovery_of` could not
be used until every sibling was decided; that contradiction is removed.

* **Remaining pending siblings stay decidable.** `record_decision` keeps its
  existing guards (identity, append-only) and gains **no** new terminal guard.
  A decision on a still-pending sibling is accepted, recorded and audited
  exactly as before; it cannot resurrect the document, because the active
  rejected fact persists and `_recompute_document_status` returns `failed`
  again. Rationale: refusing those decisions would need a new
  `E_DOCUMENT_TERMINAL` error code and would discard the doctor's verdicts on
  the other facts; the fail-closed property already holds because promotion is
  gated on `verified` (§4.2) and the rejected fact can never be superseded by a
  sibling decision.
* **`failed` means "terminal for verification", not "frozen".** Fact rows may
  still receive decisions; the document can never return to `verified` and can
  never promote an Observation. A strict-freeze variant that refuses sibling
  decisions is a documented, separately approvable alternative; it is **not**
  part of this design.
* **Recovery eligibility begins immediately** on the first rejection, because
  the document is already `failed` with a rejection `failure_code`. A recovery
  upload does not depend on the old document's pending siblings being decided.
* **Reject-first and reject-last are both terminal** and both tested (§7
  R1a/R1b): rejecting the `value` first while siblings are pending yields
  `failed` immediately; verifying the siblings first and rejecting the `value`
  last yields `failed` at the last decision. The end state is identical.

Notes:

* `superseded_fact_ids` is reused exactly as `_unread_measurement_blocks_verification`
  already uses it, so a **valid first-decision correction** (original rejected +
  superseded, new fact verified) leaves `active_rejected` empty and the document
  `verified`. This is the C6 path and must stay green.
* A `page_missing` value that is `rejected` is an active rejection → `failed` /
  `measurement_rejected`. This is the R17 case A, now terminal instead of a
  `needs_verification` hold.
* The `all facts rejected` branch is kept ahead of the new branch so the existing
  `all_facts_rejected` code and its test are unchanged.

### 4.2 Promotion gate

`_maybe_promote_document()` returns `(False, "document_not_verified")` when
`document.extraction_status != "verified"`. The status has already been
recomputed by the caller, so this is a pure read. Consequence: a document with a
rejected fact can never promote an Observation, even if a verified `value` fact
exists beside it (the §0.2 `reference_text` case).

### 4.3 Recovery attempt creation and linkage

* `POST /api/v1/documents/upload` accepts an optional `recovery_of` form field
  (UUID). It is patient-self-scoped like the upload itself.
* Validation (in `intake.accept_upload` or a small helper it calls):
  * the referenced document exists and `patient_id == self_patient_id`;
  * `extraction_status == "failed"` **and**
    `failure_code ∈ {all_facts_rejected, measurement_rejected, fact_rejected}`.
  * Absent / other-patient → `404 E_NOT_FOUND` (neutral, consistent with the
    document access rule). Present but not recoverable → `400 E_VALIDATION`.
* The new `document` row is written with
  `recovered_from_document_id = recovery_of`.
* A `document.recovered` audit event is appended with
  `subject_type="document"`, `subject_id=<new document>`, and a typed detail
  fragment `recovered_from=<old document>`. No document text is recorded
  (`REQ-AUDIT-02`).
* The new document is extracted and verified through the **existing** endpoints;
  its Observation carries `source_fact_id` → its own verified fact. Lineage is
  therefore two explicit hops: `observation.source_fact_id -> new fact ->
  new document.recovered_from_document_id -> old document`.
* **The link is patient-declared, not validated equivalence (resolves R21-B4).**
  `recovery_of` asserts only "the uploader says this new report replaces that
  terminal document". The application does **not** assert that the new bytes are
  clearer, related or clinically equivalent, and the audit detail must not use
  words such as "corrected" or "validated". The new document is independently
  scope-checked, identity-checked (`VI-004`), conflict-checked (`VI-006`),
  extracted and doctor-verified; a link never substitutes for any of those.
* The `document.recovered` audit event is written **only after** the upload is
  accepted and the document row is created. A refused `recovery_of` writes no
  link and no audit event.

### 4.4 What happens to open `VI-002` issues

They **remain open**. D-14 requires a plain rejection to be counted, and
`sync_issues` re-derives `VI-002` on every read, so resolving it would only make
it re-open. The design treats an open `VI-002` on a `failed` document as an
**immutable record of the rejection**, not an actionable blocker. The terminal
signal is `document_status == "failed"` plus `failure_code`. No issue row is
deleted, re-typed or auto-resolved. (A terminal-specific message/reason is a
possible follow-up; it is not required and would be a separate `DEMO_REVIEW_RULES`
change.)

A recovery upload does **not** resolve, supersede or clear the old document's
open `VI-002`; the old row stays `open` and historical. Whether any downstream
consumer may treat a recovered document as closing the old blocker is a
separate, explicitly **deferred** governance decision (P4/P5 or later); this
design neither performs nor implies it.

### 4.5 Rejected non-measurement facts

Handled by the same predicate: any active rejected fact → `failed` /
`fact_rejected` (or `measurement_rejected` if a `value` is among them), and the
promotion gate suppresses the Observation. This fixes the measured
`reference_text` contradiction and **subsumes R20-D2**. It is called out as an
explicit owner decision (§9, A2) because it changes current behaviour for
non-measurement rejections. A narrow variant (measurements only) is available
if the owner prefers to defer R20-D2; the acceptance matrix flags which variant
each test pins.

### 4.6 Duplicate-hash protection

Untouched. `ux_document_sha_patient` and the `409 E_DUPLICATE_DOCUMENT` path run
**before** the recovery link is considered. A recovery therefore requires a
**different** source (different `sha256`); re-uploading the identical rejected
bytes is refused. This is correct: identical bytes cannot be a clearer source.

### 4.7 Identity and scope precedence

`record_decision` still evaluates `VI-004` before the append-only guard. The
recovery link is patient-scoped, and a `VI-004`-blocked document is never in a
recoverable terminal state (it cannot reach `failed` through decisions), so it
cannot be a recovery source. The new document is subject to the normal
`VI-004` / `VI-006` checks at read and verify time.

The recovery link is **not** a trust boundary: the new document must clear its
own `VI-004` / `VI-006` and its own doctor verification. A patient-declared link
to an unrelated failed document is stored as a declared association only and is
never described as a clinically validated recovery.

### 4.8 Append-only decision history

No `fact_verification` row is ever updated or deleted. The rejected fact keeps
its status, `raw_text`, span and flags. `corrected` / `verified` on it still
return `409 E_FACT_ALREADY_DECIDED`. The recovery creates **new** rows only.

### 4.9 Patient-safe recovery metadata (resolves R21-B2)

The patient is the actor who performs the recovery upload, so the patient's own
`GET /api/v1/documents/{document_id}` must expose the three non-clinical facts
it needs: the terminal reason, whether recovery is allowed, and the source
document id. `DocumentMeta` gains exactly three optional fields and nothing
else:

| Field | Type | Meaning |
|---|---|---|
| `failure_code` | `str \| None` | The terminal reason; one of the §4.1 codes or an extraction code. Never document text. |
| `recovery_eligible` | `bool` | Derived: `extraction_status == "failed"` **and** `failure_code ∈ {all_facts_rejected, measurement_rejected, fact_rejected}`. |
| `recovered_from_document_id` | `str \| None` | The source document this row was recovered from, if any. |

Redaction rules (all tested):

* No `facts`, `raw_text`, `normalized_value`, `unit`, span, `quality_flags`,
  `confidence` or Observation value may appear. `failure_code` is an
  enum-like token; `recovered_from_document_id` is a UUID.
* `recovery_eligible` is `false` for a document that is not terminal, and for
  every extraction failure code that is not a rejection.
* The exact-key assertion in `test_p3_authorization.py` is **updated** to the
  new field set; preserving that old test is not a reason to omit the fields.
* The doctor-only `ExtractionResponse` also carries `failure_code` and
  `recovered_from_document_id` (§5).
* The patient obtains the document id from the existing upload response /
  `GET /documents/{id}`; **no new list endpoint** is added in this increment.

### 4.10 SQLite migration integrity (resolves R21-B3)

Migration `0004_p3_rejection_recovery` is additive and uses Alembic batch mode:

```
upgrade:
  ALTER TABLE document ADD COLUMN recovered_from_document_id VARCHAR(36) NULL
  CREATE INDEX ix_document_recovered_from ON document (recovered_from_document_id)
  ALTER TABLE document ADD CONSTRAINT fk_document_recovered_from
      FOREIGN KEY (recovered_from_document_id) REFERENCES document (id)
      ON DELETE RESTRICT
downgrade:
  if EXISTS (SELECT 1 FROM document WHERE recovered_from_document_id IS NOT NULL):
      raise DowngradeRefused          # safe refusal; schema and rows untouched
  DROP CONSTRAINT fk_document_recovered_from
  DROP INDEX ix_document_recovered_from
  ALTER TABLE document DROP COLUMN recovered_from_document_id
```

* **Existing rows are untouched.** The column is nullable with no server
  default, so every P2/P3 row keeps its values and `recovered_from_document_id`
  is `NULL`. No table rebuild and no `CHECK` change.
* **The self-FK is a normal inline FK.** Verified: SQLAlchemy emits
  `FOREIGN KEY(recovered_from_document_id) REFERENCES document (id)` with no
  cycle warning, unlike the `user <-> patient` two-table cycle.
* **Downgrade refusal.** Dropping the column would silently destroy recovery
  provenance, so `downgrade` refuses when any link exists, raising a neutral
  error and leaving the schema and rows untouched. A rollback that must keep
  the data requires an explicit archive step first; this is documented in the
  migration docstring and tested. When no link exists, the downgrade drops the
  constraint, index and column and returns to the exact `0003` schema.
* **Enforcement is verified, not assumed.** The migration engine disables
  `PRAGMA foreign_keys` (the existing `env.py` pattern); the smoke runs on a
  runtime-equivalent connection with `PRAGMA foreign_keys=ON` and asserts:
  - `PRAGMA foreign_key_check` is empty;
  - inserting a `document` whose `recovered_from_document_id` does not exist
    fails;
  - deleting a parent `document` referenced by a child fails (`RESTRICT`);
  - `PRAGMA foreign_key_list('document')` contains the self-FK.
* **Head-revision constants must move.** `scripts/python/check_alembic_smoke.py`,
  `backend/tests/p2/test_p2_migration.py` and `backend/tests/test_database.py`
  hardcode `HEAD_REVISION = "0003_p3_documents"`; they become
  `"0004_p3_rejection_recovery"`, and the smoke gains a `p3` state asserting the
  column/index/FK are absent at `0003` and present at `head`.
* **Smoke sequence:** `0001 -> 0002 -> 0003 -> 0004(head)`, then
  `head -> 0003` on a database with no links, then `0003 -> head` again, with
  P2/P3 row counts preserved across every step and `PRAGMA foreign_key_check`
  empty at `head`.

---

## 5. Exact file-scope change proposal (Approach A)

Production code (all additive / localised):

| File | Change |
|---|---|
| `backend/app/services/documents/verification.py` | `_recompute_document_status`: rejection-first `active_rejected` branch and the two failure codes (§4.1). `_maybe_promote_document`: `document_not_verified` gate. `_active_rejected_facts` helper. |
| `backend/app/services/documents/intake.py` | `accept_upload(..., recovery_of: str | None = None)`: validate the source document, set `recovered_from_document_id`. |
| `backend/app/api/v1/documents/upload.py` | Accept `recovery_of: Annotated[str | None, Form()] = None`; pass it through; append `EVENT_DOCUMENT_RECOVERED` only on success. |
| `backend/app/db/models.py` | `Document.recovered_from_document_id` (String(36), nullable, self-FK `document.id` `ondelete="RESTRICT"`), `Index("ix_document_recovered_from", ...)`. |
| `backend/app/schemas/document.py` | `DocumentMeta`: optional `failure_code`, `recovery_eligible`, `recovered_from_document_id` (§4.9). `ExtractionResponse`: optional `failure_code`, `recovered_from_document_id`. |
| `backend/migrations/versions/0004_p3_rejection_recovery.py` | Add column, index, self-FK; downgrade refuses when links exist (§4.10). |
| `backend/app/services/documents/__init__.py` | `EVENT_DOCUMENT_RECOVERED = "document.recovered"`. |
| `scripts/python/check_alembic_smoke.py` | `HEAD_REVISION` → `0004_p3_rejection_recovery`; add a `p3` state asserting the new column/index/FK are absent at `0003` and present at `head`. |
| `backend/tests/test_database.py`, `backend/tests/p2/test_p2_migration.py` | `HEAD_REVISION` → `0004_p3_rejection_recovery`. |

No change to `enums.py`, `issues.py`, `quality.py`, `mapping.py`, `access.py`,
`audit.py`, `ocr.py`, `field_parser.py`, or any fixture.

Docs / contracts (must land in the same change):

| File | Change |
|---|---|
| `docs/contracts/DATA_DICTIONARY.md` §2.4 | New column; `failure_code` values and the terminal semantics; the self-FK and its `RESTRICT` rule. |
| `docs/contracts/API_CONTRACT.md` §2.4 | `recovery_of` request field; `DocumentMeta` / `ExtractionResponse` optional fields; `failure_code` catalogue; the patient-declared meaning of the link. |
| `docs/contracts/openapi.phase0.yaml` | Mirror the new optional `DocumentMeta` and `ExtractionResponse` fields. |
| `docs/clinical-safety/DEMO_REVIEW_RULES.md` | One note: `VI-002` remains open on a terminal rejected document (D-14 unchanged). |
| `docs/roadmap/PHASE_PROGRESS.md` | Record the owner decision verbatim once granted. |
| `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` | Update the collected test counts. |

Tests:

| File | Change |
|---|---|
| `backend/tests/p3/test_p3_rejection_recovery.py` | New: the §7 acceptance matrix. |
| `backend/tests/p3/test_p3_authorization.py` | Update the exact `DocumentMeta` key set; add patient/doctor authorization and redaction tests for the new fields (§4.9). |
| `backend/tests/p2/test_p2_migration.py` (or a new migration test) | Add the `head -> 0003 -> head` self-FK smoke, row preservation, real FK enforcement and downgrade-refusal tests (§4.10). |
| `backend/tests/p3/test_windows_ocr_acceptance.py` | Count table only (via the count-matching test). |

---

## 6. Required API / schema / migration decisions

| Decision | Recommended | Genuinely required? |
|---|---|---|
| New document status value | No — reuse `failed` | No |
| Terminal timing | Rejection-first: terminal on the first plain rejection, siblings still decidable (§4.1) | Yes, to remove the B1 contradiction |
| New `failure_code` values | Yes: `measurement_rejected`, `fact_rejected` | Yes, for a machine-readable terminal reason and recovery-source validation |
| New column | Yes: `document.recovered_from_document_id` (nullable, self-FK, indexed) | Yes, for durable lineage (an audit-only link is the fallback) |
| Migration | Yes: one additive migration; downgrade refuses when links exist (§4.10) | Yes, for the column |
| New endpoint | No | No |
| Request field | Yes: `recovery_of` on `POST /upload` | Yes, to create the link |
| Patient-safe exposure | Yes: `failure_code`, `recovery_eligible`, `recovered_from_document_id` on `DocumentMeta` (§4.9) | Yes — the patient is the recovery actor (B2) |
| Doctor exposure | Yes: `failure_code`, `recovered_from_document_id` on `ExtractionResponse` | Recommended for usability |
| Error codes | No new codes; `E_NOT_FOUND` / `E_VALIDATION` reused | No |

---

## 7. RED-first acceptance matrix

"RED" = fails on `18a53b2`, passes after the change. "GREEN" = passes today and
must stay green. All tests are local and deterministic except where marked
**Windows-only**. Scripted-OCR tests inject text through the existing
`monkeypatch` seam and need no Tesseract.

| ID | Test | Setup | Required assertion | Today | Class |
|---|---|---|---|---|---|
| **R1** | Rejected measurement (reject-last) | text PDF; verify the four siblings, then reject `value` | `document_status == "failed"`, `failure_code == "measurement_rejected"`, zero Observations | RED | local |
| **R1a** | Rejected measurement (reject-first) | text PDF; reject `value` **first**, siblings still `pending` | `failed` immediately (not `needs_verification`); `recovery_eligible == true`; a later sibling decision is still accepted and the status stays `failed` | RED | local |
| **R1b** | Reject-first vs reject-last equivalence | run R1 and R1a to the end | identical terminal state (`failed`, same code, zero Observations); recovery eligible in both | RED | local |
| **R2** | Rejected non-measurement fact | text PDF; reject `reference_text`, verify the other four | `document_status == "failed"`, `failure_code == "fact_rejected"`, zero Observations | RED | local |
| **R3** | No misleading `verified` | R1/R1a/R2 end states | `document_status != "verified"` whenever an active rejected fact exists; no `verified` + open `VI-002` pair | RED | local |
| **R4** | Recovery attempt is created and linked | after R1a, upload different bytes with `recovery_of=<old>` | `202`; new document `recovered_from_document_id == old`; old row unchanged (`failed`, rejected fact intact) | RED | local |
| **R5** | Observation lineage after recovery | R4, then verify the new document | new Observation's `source_fact_id` is a fact of the **new** document; old document still has zero Observations | RED | local |
| **R6** | Recovery-source correctness (B4) | each negative: missing `recovery_of` (baseline upload); malformed / non-UUID; non-existent id; other-patient id; `needs_verification`; `verified`; `pending_extraction`; extraction-failed `no_facts_extracted`; duplicate same bytes; repeated recovery of an already-recovered document | malformed → `400`; absent / other-patient / non-existent → indistinguishable `404`; wrong state → `400`; duplicate → `409 E_DUPLICATE_DOCUMENT`; missing → normal upload with no link; repeated recovery → a new chained link is allowed as designed; **no link row and no `document.recovered` audit event on any refusal** | RED | local |
| **R7** | Patient-safe recovery metadata (B2) | patient `GET /documents/{id}` on a terminal document and on a recovered document; other-patient, doctor and unauthenticated calls | `failure_code`, `recovery_eligible`, `recovered_from_document_id` present and correct; no `facts` / `raw_text` / `normalized_value` / `unit` / span / `quality_flags` / `confidence`; other patient → `403`/`404`; doctor assigned → `200`; unauthenticated → `401` | RED | local |
| **R8** | SQLite migration integrity (B3) | `0001..0004` upgrade; `head -> 0003 -> head`; non-empty P2/P3 data; a linked recovery row | row counts preserved; column/index/self-FK present at `head` and absent at `0003`; `PRAGMA foreign_key_check` empty; bad-parent insert fails; parent delete with a child fails (`RESTRICT`); `downgrade` with a link raises `DowngradeRefused` and changes nothing | RED | local |
| **G1** | Correction as the initial decision | `pending` fact → `corrected` → verify rest | `verified`; `corrected_from_fact_id` lineage; original retained `rejected`; `VI-002`/`VI-005` resolved; Observation where mappable | GREEN | local |
| **G2** | Immutable rejection history | after R1 | `fact_verification` row exists; `corrected` and `verified` on the rejected fact still `409`; fact still `rejected` | GREEN | local |
| **G3** | Identity-blocker precedence | document with open `VI-004` | `409 E_VI_004_UNRESOLVED` before any decision; `recovery_of` cannot name it; new linked document with a wrong ref gets its own `VI-004` | GREEN | local |
| **G4** | No Observation from a rejected fact | R1/R2 | no Observation whose `source_fact_id` references a rejected fact of the document | GREEN | local |
| **G5** | `VI-002` preserved (D-14) | R1/R2 | `VI-002` present, `state == open`, `reason_code == fact_unverified` | GREEN | local |
| **G6** | All-rejected unchanged | reject every fact | `failed`, `failure_code == "all_facts_rejected"` | GREEN | local |
| **G7** | Document-only report unaffected | no `value` fact; verify all | `verified`; `VI-002` resolved | GREEN | local |
| **G8** | Duplicate upload | same bytes after R1, with and without `recovery_of` | `409 E_DUPLICATE_DOCUMENT`; no new row | GREEN | local |
| **G9** | Existing P3 suite | full backend suite | 635 pre-existing tests still pass (new tests added on top) | GREEN | local |
| **W1** | Real-engine rejection | owner Windows/Tesseract, reject the OCR value | terminal `failed`, zero Observations | RED | **Windows-only** |
| **W2** | `GOLD-EX-11` regression preservation | owner Windows/Tesseract | still **FAIL / NOT PROVEN**; a *preservation* check, not a passing acceptance gate, and not by itself evidence of P3 acceptance | GREEN (preservation) | **Windows-only** |

R4–R8 are the tests that need the `recovery_of` field, the new column, the
patient-safe `DocumentMeta` fields and the migration; R1–R3 need only the
predicate + gate. W1 is the only new test that needs the real engine; its
application behaviour is otherwise identical to R1/R1a, which run locally with
scripted OCR. W2's expected result is **FAIL / NOT PROVEN**: it is a
regression-preservation check and must never be reinterpreted as a GREEN
acceptance gate.

---

## 8. Staged implementation plan

Each stage is independently reviewable and gated. **No stage starts before §9.**

| Stage | Work | Closes | Evidence |
|---|---|---|---|
| 0 | This design round; owner authorization | — | owner |
| 1 | Write `test_p3_rejection_recovery.py` (R1–R8, G1–G9); run against `18a53b2` and record the RED/GREEN table | baseline evidence | local |
| 2 | Rejection-first predicate + promotion gate + failure codes (no schema) | R1, R1a, R1b, R2, R3, G4, G5 | local |
| 3 | `recovery_of` + column + migration (with downgrade refusal) + audit event + `DocumentMeta`/`ExtractionResponse` fields | R4, R5, R6, R7 | local |
| 4 | Contract/doc sync (§5 docs table); update the handoff counts | auditability | local |
| 5 | Full suite + `ruff` + `check_openapi.py` + `check_alembic_smoke.py` (updated head + `p3` state) + migration smoke | G9, R8 | local |
| 6 | Owner Windows run at the new SHA with **unchanged** OCR configuration: W1, W2, and the existing acceptance set | W1, W2 | **Windows-only** |
| 7 | Independent review; PR #10 stays DRAFT; P3 stays IN_REVIEW | — | owner |

Stage 2 is the safety core and can land alone (it makes the state honest but
leaves the recovery route unspecified). Stage 3 is the usability core. Both are
needed for the owner's Option 2.

---

## 9. Explicit owner approval items

None of these is authorized by this document.

| # | Decision | Options |
|---|---|---|
| **A1** | Terminal state model | **A:** reuse `failed` + `failure_code` (recommended) / **B:** new `rejected` status / **C:** same-document replacement fact |
| **A2** | Scope of the terminal rule | **any active rejected fact** (recommended; subsumes R20-D2) / measurements only (narrow; R20-D2 stays open) |
| **A3** | Terminal timing | **rejection-first, siblings still decidable** (recommended, §4.1) / strict freeze (new `E_DOCUMENT_TERMINAL`) |
| **A4** | Additive `document.recovered_from_document_id` column + self-FK + migration with a **downgrade refusal when links exist** + `DATA_DICTIONARY.md` change | approve / reject (fallback: audit-only link) |
| **A5** | `recovery_of` upload field and its validation (self-owned, terminal, `failed` + rejection code; patient-declared link, not validated equivalence) | approve / adjust |
| **A6** | Promotion gate: no Observation unless `document_status == "verified"` | approve |
| **A7** | `VI-002` stays open on a terminal rejected document as an immutable record (D-14 unchanged); the downstream "may a recovery clear it" question is deferred | approve / request a terminal-specific reason or message (separate `DEMO_REVIEW_RULES` change) |
| **A8** | Patient-safe exposure: `failure_code`, `recovery_eligible`, `recovered_from_document_id` on `DocumentMeta` (§4.9); `ExtractionResponse` optional fields | approve |
| **A9** | Accept the revised §7 matrix as the gate, with R1–R8 red and G1–G9 green today; W2 remains **FAIL / NOT PROVEN** and is regression preservation only | approve |
| **A10** | Confirm: no OCR configuration change; `GOLD-EX-11` unchanged; synthetic fixtures unchanged; PR #10 stays DRAFT; P3 stays IN_REVIEW | confirm |

---

## 10. Explicit non-claims and exclusions

* This round changes **no** production code, API, schema, migration, OCR
  configuration, parser grammar, fixture or UI.
* It does not enable `preserve_interword_spaces=1`.
* It does not change `GOLD-EX-11` or any golden fixture.
* It does not claim any OCR accuracy result; W1/W2 are owner-Windows evidence.
* It does not close requirement B (reviewable OCR source) or requirement C
  (false-clean detection). A rejected measurement is a workflow outcome, not a
  recognition-fidelity claim.
* It does not merge or approve PR #10, and it does not start P4/P5.
* All data remains synthetic; every new surface is local, patient-scoped and
  audited.
* This corrigendum resolves the four findings in review
  [`5918165016`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5918165016)
  (B1–B4) and keeps W2 as **FAIL / NOT PROVEN**; it does not introduce new
  findings and does not authorize implementation.
* A `recovery_of` link is a patient-declared association, not a claim that the
  new document is clearer or clinically equivalent; the new document is
  re-evaluated independently for scope, identity and doctor verification.

PR #10 remains **DRAFT**; P3 remains **IN_REVIEW**; `GOLD-EX-11` remains **FAIL /
NOT PROVEN**.
