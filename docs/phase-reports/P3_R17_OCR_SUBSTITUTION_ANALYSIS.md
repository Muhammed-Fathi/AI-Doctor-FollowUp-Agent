# P3-R17 — Real OCR substitution and end-to-end safety

**Status: committed for the review trail.** §1–§7 are the original analysis, preserved
verbatim as the record of what was found against `1b17a9a` — including the items that
turned out to be wrong or out of scope, which §8 records honestly rather than editing
away. **§8 (appended 2026-11-16)** records what was actually implemented, what was
dropped and why, and what still needs owner approval.

PR #10 stays DRAFT; P3 stays IN_REVIEW; P4/P5 not started; nothing merged.

Answers review [`5913742849`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5913742849)
against head `1b17a9a991c7a8d470c3aa18f478a4834c6b38a5`, and review
[`5915830616`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5915830616)
which ruled on the implementation order.

## 0. Method and honesty statement — read this before the findings

| | |
|---|---|
| Runs executed here | Linux sandbox, **scripted stand-in engine** (a shell script that prints a fixed OCR text file). **Not real Tesseract.** |
| Real Tesseract in this sandbox | **NOT RUN.** Still unobtainable (`apt-get download tesseract-ocr` → unable to locate package, no root, restricted network). |
| What the stand-in proves | The **gate decision logic** and the **end-to-end HTTP path** downstream of the engine. Those are engine-independent. |
| What it cannot prove | Anything about real recognition fidelity, including whether real Tesseract sets `preserve_interword_spaces`, or how often it substitutes `O`→`0`. |
| Owner evidence used as input | The exact real Windows OCR text from `1b17a9a`, reproduced as a byte file and injected. This is the one real-engine data point in the whole document, and it comes from your run, not mine. |
| Windows behaviour claimed from here | None. |

Where a number appears below it was produced by a command in this session, not recalled.

The input text used for the main cases is your real OCR output, verbatim:

```
SYNTHETIC DEMO DATA- NOT A REAL MEDICAL RECORD

Demo Patient A Ref: DEMO-A-001 Report date: 2026-10-20
Test: Glucose Value: 105 mg/dL

Reference range: 70 - 110 mg/dL
```

Two structural variants are used to separate the two questions that your review
correctly insists on separating:

* **A** — your exact bytes (single space before `Value:`, engine-substituted `105`).
* **B** — the same content with a two-space column gap (`105`), i.e. *parseable but substituted*.
* **C** — two-space gap with `1O5` preserved, i.e. *parseable layout, parser refuses the token*.

A, B and C differ **only** in the OCR text handed to the real application. Everything
downstream is the shipped code path: `POST /api/v1/documents/upload` → intake → OCR page
substitution → `parse_pages` → `_persist_facts` → `GET /{id}/extraction`.

---

## 1. Root cause of "no value fact was parsed" — a configuration mismatch, not a parser bug

Your observation is confirmed exactly, and the reason is one layer deeper than the regex.

`backend/app/services/documents/ocr.py:189`:

```python
config = f"--psm 6 -l {language}"
```

Tesseract collapses runs of inter-word spaces to a single space **unless**
`-c preserve_interword_spaces=1` is passed. This repository never passes it
(`grep preserve_interword_spaces` → no hits).

`backend/app/services/documents/field_parser.py:34-39` requires a gap of **two or more**
whitespace characters:

```python
_TEST_VALUE = re.compile(
    r"test\s*:\s*(?P<test>[A-Za-z][A-Za-z0-9 ()%/._-]*?)\s{2,}"
    r"value\s*:\s*(?P<value>[^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
```

So for a scanned lab report the parser asks for a column gap that the engine is
configured never to emit. **Every** OCR'd report in this layout family loses its
measurement line, whether or not any character was substituted. `GOLD-EX-11` is a
symptom; the defect is generic to the OCR path.

This matters for how the previous failure was read. `GOLD-EX-11`'s FAIL was labelled
"engine substituted `1O5`→`105`", and that is also true, but on your image the parser
would have dropped the line even if the engine had preserved `O`. The gate's diagnosis
was therefore **understated, not overstated**: the safety property is even less exercised
than it appeared.

---

## 2. What the real HTTP path actually does (your six questions)

### Q1 — real rendered fixture through upload/extraction

Rendering `data/synthetic/documents/sources/report_ocr_o_confusion.txt` with
`build_legible_scan_image()` and uploading it as a PNG gives, for the three injected
engine outputs:

| | **A** (your real bytes, 1 space) | **B** (2 space, `105`) | **C** (2 space, `1O5`) |
|---|---|---|---|
| `document_status` | `needs_verification` | `needs_verification` | `needs_verification` |
| facts persisted | **2** (`report_date`, `reference_text`) | 5 | 5 |
| `value` fact | **none** | `'105'` | `'1O5'` → `normalized_value=None` |
| value `quality_flags` | — (no fact) | `['clean']` | `['low_confidence','unparseable_value']` |
| issues | `VI-002 fact_unverified` | `VI-002 fact_unverified` | `VI-002` + `VI-005 value_unreadable` |
| observations created | 0 | 0 | 0 |
| extractor on facts | — | `tesseract` | `tesseract` |
| provenance | — | span 137–140, `raw_text='105'` | span 137–140, `raw_text='1O5'` |

Reading of that table:

* **Your exact case (A) produces no `VI-005`.** The most dangerous outcome in the whole
  matrix is also the quietest one: a measurement line existed in the image, the engine
  emitted a plausible number, and the application says only *"2 extracted value(s) are
  not yet verified."* Nothing states that a value was expected and not read.
* **C is the good case** and it behaves exactly as the contract says: flagged, blocking,
  `VI-005`, no numeric value.
* **B is the case that must never be silent.** The substituted `105` arrives with
  `flags=['clean']` — byte-identical in appearance to a correctly read value. The
  substitution is invisible to the doctor unless they open the image.

### Q2 — can a substituted `105` create a trusted Observation without explicit verification?

**No automatic promotion. Yes after one explicit verification click.** Both halves
matter, and the second is where the honest answer is less comfortable than "the design
prevents it".

* All persisted facts are created `verification_status='pending'` (`intake._persist_facts`).
* `decide_mapping()` only reads `verified` facts; `_maybe_promote_document` is only
  reachable from `record_decision`. With zero decisions, **0** observations — measured
  for A, B and C.
* After a doctor decides every fact in B, **exactly 1** observation is created
  (`glucose`, doctor_verified, `source_fact_id` set). That is the contract working as
  designed: verification is the gate.

The gap is **not** that verification is bypassed. It is that the doctor is asked to
approve `105` with **no cue that OCR may have substituted it**. `flags=['clean']`,
`confidence=0.95`, and the extracted `raw_text` is `'105'` — the same value the source
image does *not* contain. The one artifact that shows the substitution is the OCR text,
and the application does not expose it (§4, Q4).

### Q3 — the two cases, and mocked vs real

| Test kind | What it may assert | Where |
|---|---|---|
| Real engine | that this engine, on this image, produced this text | **owner's Windows only** |
| Injected OCR output ("simulation") | the application's behaviour **given** engine output | permissible here, must be labelled |
| Parser-direct (no engine at all) | `parse_pages` on a known string | deterministic, already covered |

Everything in this document is row 2 or row 3. Row 1 is yours. The existing suite already
has the row-3 coverage (`test_p3_windows_findings.py`, 47 tests). What does not exist is
row 2 at the **HTTP level** for these three variants — the probe parses in-process and
never uploads, so "the app dropped the measurement" was never asserted end-to-end. That
is gap G1.

### Q4 — can the doctor reach the original document, compare, correct, and keep lineage?

**Reach: yes. Compare: no. Correct: yes, with lineage. Reject: yes.**

Verified with your exact bytes and variant C:

* `GET /{id}/file` → `200 image/png`, 37 656 bytes, **byte-identical to the upload**.
  Original bytes are reachable by the assigned doctor.
* Evidence per fact carries `page_index`, `char_start`, `char_end`, `raw_text`,
  `extractor='tesseract'`.
* Correction of C's `1O5` → `105`: `200`; original fact `rejected`; new fact
  `raw_text='1O5'`, `normalized_value='105'`, `corrected_from_fact_id` set to the
  original; `fact_verification` row `decision='corrected' previous_value=None
  new_value='105' reason=…`. **Lineage is preserved and the excerpt is not rewritten** —
  a corrected `1O5` still reads `1O5` as evidence. That part of the design is sound.

**The comparison is impossible through the API.** There is no endpoint, field or table
that returns the page text the parser saw:

* no `page_text`/`ocr_text` table exists (`grep __tablename__` — 12 tables, none for page text);
* `ExtractionAttemptSummary` deliberately omits `text_char_count`, `engine_confidence`,
  `preprocessing`, `page_from/page_to`;
* facts expose only `raw_text`, capped at 300 characters at persist time.

Consequences, both real:

1. A doctor can see `raw_text='105'` and the image, but cannot see that the engine read
   the line as `Test: Glucose Value: 105 mg/dL` and thereby cannot see that the column
   gap was destroyed. The only place that text exists today is the acceptance probe's
   `engine_ocr_text` field.
2. `field_parser`'s docstring and `EXTRACTION_PROVENANCE.md` §5 claim spans "can always be
   re-resolved against the stored page text". **No stored page text exists.** Spans are
   only resolvable during ingest, in-memory. The immutability claim that depends on it
   (`rule 1: spans are bounded by the stored page text length`) is currently unenforceable
   after the request ends. This is a documentation/implementation mismatch, not a data
   corruption — but it is a gap (G3).

### Q5 — are missing measurement facts surfaced for review?

**No. This is the most serious finding, and it is not the one the review predicted.**

Variant A does not merely fail to flag a bad value; it produces a document that can be
marked **`verified` with no measurement at all**:

```
verify report_date    -> 200  document_status=needs_verification
verify reference_text -> 200  document_status=verified      <-- no value fact exists
```

`_recompute_document_status` (`verification.py:126`) sets `verified` when no fact is
`pending` **and at least one fact is `verified`**. It never checks that a `value` fact
exists. So a scan whose measurement line was lost transitions to `verified` — the
strongest status in the model — carrying only a date and a reference range.

A weaker but related variant: wholly unreadable OCR (variant D, no parsable text) gives
`document_status='failed'`, `failure_code='no_facts_extracted'`, **`facts=[]` and
`verification_issues=[]`** — a failed document with zero blockers and nothing for a
review queue to pick up. The failure is honest in `failure_code` but invisible in the
issue list.

No `VI-*` code exists for "a measurement was expected here and none was extracted".
`QualityFlag.PAGE_MISSING` is declared in the closed enum and mapped in `mapping.BLOCKING_FLAGS`
but is **never produced by any code path**, and has no issue-type mapping — so the one
concept in the contract that names this situation is dead. `collect_flag_issues` derives
issues only from flags attached to *facts*, and a missing fact has no row to attach to.

### Q6 — is `human_review_required` proof of an enforced decision?

**No — you are right, and it is worse than "probe metadata".**

* It is a hardcoded literal at `scripts/python/windows_ocr_acceptance.py:491`
  (`"human_review_required": True`), emitted unconditionally for the gate.
* The probe never calls `POST /verify` and never reads an `Observation`
  (`grep` for `/verify` → absent; `Observation` → absent).
* The `ocr_issues` field in the *other* gate (`ING-02`) does read persisted
  `verification_issues`, but `GOLD-EX-11` does not.

The genuine artifact is the persisted `verification_issue` row. For your image (A) that
row is `VI-002 fact_unverified` only — which is present for any document with pending
facts and therefore says nothing about the substitution. For A, the truthful answer to
"was human review *required* by the system?" is: **the document was blocked by `VI-002`
like any pending document, and the specific risk was never recorded.**

---

## 3. Additional defects found while testing (not in the review)

| # | Finding | Evidence |
|---|---|---|
| D1 | **`verified` document with no measurement** (§2 Q5). | A: 2 verify calls → `document_status=verified`, 0 value facts. |
| D2 | **Correction accepts any non-empty string.** `verify.py:108` only checks `not payload.corrected_value`, so `'   '`, `'abc'`, `'-5'`, `'0'` are all accepted `200`, fact `verified`, document `verified`. Only `''` is refused (`400`). | Four corrections run; all `200`; `normalized_value` literally `'   '` and `'abc'`. |
| D3 | **`VI-005` never closes after correction.** After correcting C's `1O5`, the open issues are still `[VI-005 value_unreadable]` while `document_status=verified`. `_flags_of` keeps reading the rejected original's flags, and `sync_issues` re-derives it every read. | Post-correction `GET /extraction`. |
| D4 | **Document-level issue on an OCR-only document claims `extractor: 'pypdf'`.** `read._issue_schemas` falls back to `EvidenceRef(..., extractor="pypdf")` when an issue has no linked fact. On a PNG that never touched pypdf, `VI-004`'s evidence says pypdf — the same class of misattribution R01 fixed for facts. That ref also has `page_index/char_start/char_end = null`, which `EXTRACTION_PROVENANCE.md` §5 lists as **required** for `document_span`. | VI-004 payload on a tesseract-only document. |
| D5 | `QualityFlag.PAGE_MISSING` is unreachable and unmapped to any `VI-*`. | `grep` — declared, listed in `BLOCKING_FLAGS`, never produced. |
| D6 | No measurement UI exists at all: frontend is the P1 health shell only (`frontend/src/app/App.tsx` renders `HealthPage`; doctor/patient routes arrive in P6). So req. #4's "doctor can compare" is not achievable today for **any** document, independent of OCR. | `frontend/src` tree. |

D1–D3 are safety-relevant and cheap to fix. D4/D5 are one-line provenance/hygiene
corrections. D6 is out of P3 scope.

---

## 4. Proposed acceptance criteria: split recognition fidelity from safe verification

`GOLD-EX-11` should **not** change and should keep failing until a real engine preserves
`O` and the parser refuses it. Today's failure is honest and should stay visible. What is
missing is a *second* axis that can be green or red on its own, so a legible-scan
limitation can never again be confused with a safety regression.

### Axis 1 — `OCR-RF` Recognition fidelity (real engine only, Windows)

Measures what the engine did. Never a safety claim.

| ID | Criterion | Today |
|---|---|---|
| `OCR-RF-01` | The rendered `report_ocr_o_confusion.txt` yields the line `Test: Glucose … Value: … mg/dL` with the `Value:` label intact, at confidence ≥ floor. | **FAIL** on `1b17a9a`: label present but the column gap is destroyed — see `OCR-RF-02`. |
| `OCR-RF-02` | The engine preserves a ≥2-space column gap **or** the pipeline explicitly enables `preserve_interword_spaces=1` so it is recoverable. | **FAIL** — not configured. |
| `OCR-RF-03` | Character-level fidelity of the value token is **measured and published**, never asserted: `preserved` / `substituted` / `lost` with the raw token pair. | `GOLD-EX-11` already publishes this correctly. |
| `OCR-RF-04` | `GOLD-EX-11` PASS = preserved `1O5` **AND** `unparseable_value` **AND** no normalized value. | Unchanged, still **FAIL/NOT PROVEN**. |

`OCR-RF` may legitimately stay red forever and be reported as a **known limitation**
rather than blocking P3 — the product's safety does not depend on OCR being perfect, it
depends on Axis 2.

### Axis 2 — `E2E-SV` End-to-end safe verification (engine-independent; injected output is valid input)

Measures the application's behaviour **given** engine output. This is the axis that can
and must be green, and it is where your six questions live.

| ID | Criterion | Today |
|---|---|---|
| `E2E-SV-01` | Uploading the committed rendered fixture with injected OCR output equal to your real bytes (A) yields `needs_verification`, **and** a blocking issue naming the unread measurement. | **FAIL** — only `VI-002`. |
| `E2E-SV-02` | `document_status` may never reach `verified` without at least one `value` fact. | **FAIL (D1)**. |
| `E2E-SV-03` | A substituted `105` (B) never creates an Observation before an explicit doctor decision, and every created Observation has `source_fact_id`, `trust_level='doctor_verified'`, `verified_by_user_id`. | **PASS** (0 before, exactly 1 after). |
| `E2E-SV-04` | A corrected value must be a valid number for a numeric field; `'   '`, `'abc'`, `''` are refused `400`. | **FAIL (D2)**. |
| `E2E-SV-05` | Correction preserves lineage: original `rejected`, new fact `verified`, `raw_text` unchanged (`1O5`), `corrected_from_fact_id` set, `fact_verification` row with previous/new value and reason. | **PASS**. |
| `E2E-SV-06` | After a correction resolves a flagged value, that `VI-005` closes. | **FAIL (D3)**. |
| `E2E-SV-07` | The doctor can fetch the original bytes (`200`, byte-identical) and a machine-readable OCR text for the same document, so image and OCR output can be compared. | Bytes **PASS**; OCR text **FAIL (G3)**. |
| `E2E-SV-08` | A document with zero extracted facts reports a blocking issue, not an empty issue list. | **FAIL** (variant D). |
| `E2E-SV-09` | No literal boolean in a probe stands in for an enforced decision: `human_review_required` must be **derived** from persisted `verification_issue` rows. | **FAIL (Q6)**. |

---

## 5. Minimum necessary code changes

Not implemented. Each item is scoped, and the ones marked **AUTH** need your decision
because they change a documented contract or add a surface.

| # | Change | File | Size | Auth |
|---|---|---|---|---|
| C1 | Enable `-c preserve_interword_spaces=1` in the OCR config so a column gap survives and the `\s{2,}` parser rule becomes satisfiable. Does not weaken anything; adds no dependency; `GOLD-EX-11` still FAILs unless the `O` is genuinely preserved. | `ocr.py:189` | 1 line | **AUTH** (changes recorded OCR behaviour for all scans) |
| C2 | *Alternative to C1, mutually exclusive:* relax `_TEST_VALUE` to `\s+`. Measured: **0 of 12** golden fixtures change parse, full suite still 597 passed. Broader blast radius — accepts single-space layouts everywhere. | `field_parser.py:34-39` | 1 line | **AUTH** (acceptance-criteria change) |
| C3 | Block `verified` without a measurement: require ≥1 `value` fact, else `needs_verification`/`failed`. | `verification.py:126` | ~5 lines | **AUTH** (status semantics) |
| C4 | Report a missing measurement as a blocking issue (reuse `VI-005` + a `measurement_not_read` reason code, or revive `PAGE_MISSING`). | `intake.py`, `issues.py` | ~25 lines | **AUTH** (new reason code / enum use) |
| C5 | Validate `corrected_value` as a number for numeric fields; refuse blank/whitespace. | `verify.py:108`, `schemas/document.py:205` | ~8 lines | no (closes a validation hole; 400 shape already declared) |
| C6 | Re-derive `VI-005` from the *current* fact set so a correction closes it. | `quality.py:~400` | ~6 lines | no (fixes a stuck blocker) |
| C7 | Derive `human_review_required` in the probe from persisted issues instead of a literal. | `windows_ocr_acceptance.py:491` | ~5 lines | no |
| C8 | Stop claiming `extractor='pypdf'` for issues with no linked fact; make it `None`/document-level, and stop emitting a `document_span` without span fields. | `read.py:175-180` | ~6 lines | **AUTH** (touches a schema contract) |
| C9 | Expose OCR text read-only for comparison (new field on `ExtractionAttemptSummary` or a new `GET /{id}/text`). Needs a storage decision: **page text is currently not persisted at all**, so this is a design choice, not a one-liner. | `read.py`, `schemas`, migration | L | **AUTH** (new surface + storage) |

Recommended minimum for the next round, if you want the smallest defensible increment:
**C5 + C6 + C7** (no authorization, close two real holes and stop the probe overclaiming),
then **C3 + C4** together as one authorized safety increment, and treat **C1 vs C2** as a
single either/or decision. **C9** should be planned, not rushed — it determines whether
`EXTRACTION_PROVENANCE.md` §5's re-resolution claim is true or must be corrected.

## 6. Proposed tests

All deterministic, all injection-labelled, none asserting real-engine behaviour.

1. `test_e2e_r17_owner_real_ocr_text_surfaces_missing_measurement` — inject your exact
   bytes; assert `needs_verification` **and** a blocking issue for the unread measurement
   (C4). Fails today.
2. `test_e2e_r17_verified_requires_a_measurement_fact` — decide every fact on variant A;
   assert status never reaches `verified` (C3). Fails today.
3. `test_e2e_r17_correction_rejects_blank_and_non_numeric` — `''`, `'   '`, `'abc'` → `400`;
   `'105'` → `200` (C5). Fails today.
4. `test_e2e_r17_correction_closes_vi_005` — after correcting `1O5`, no open `VI-005`,
   lineage intact (C6). Fails today.
5. `test_e2e_r17_substituted_value_never_promotes_without_a_decision` — variant B, 0
   observations before any decision, exactly 1 after, `source_fact_id` set. **Passes today**
   — lock it in so D-11/D-14 protections cannot regress.
6. `test_e2e_r17_corrected_fact_keeps_original_excerpt` — `raw_text='1O5'` survives the
   correction to `105`. **Passes today** — regression lock.
7. `test_e2e_r17_zero_fact_document_reports_a_blocking_issue` — variant D (C4). Fails today.
8. `test_probe_human_review_required_is_derived_not_literal` — parse the probe payload
   builder; assert the flag comes from persisted issues (C7).
9. `test_parser_two_space_and_single_space_layouts_are_distinguishable` — pins the current
   `\s{2,}` behaviour explicitly, so C1/C2 cannot be applied silently.
10. `test_issue_evidence_never_claims_an_extractor_that_did_not_run` — VI-004 on a
    tesseract-only document (C8). Fails today.

Tests 1–4, 7, 10 each fail against `1b17a9a` before any fix, which is the point: they are
the regression witnesses for the findings above.

## 7. Risks and open questions for you

1. **C1 vs C2 is a real fork.** C1 keeps the strict parser and makes the engine honest
   about layout; C2 makes the parser forgiving. C1 is narrower and preserves the
   two-column assumption that distinguishes a lab line from prose. My recommendation is
   **C1**, with C2 considered only if real Tesseract still destroys the gap under
   `preserve_interword_spaces=1`. I cannot measure that here.
2. **C3 changes what `verified` means.** A document with four clean facts and no value
   currently reaches `verified` legitimately (e.g. a report with no measurement). C3 must
   not turn that into a failure — the distinction is "a measurement line was present and
   unread" versus "this document type has no measurement". That distinction needs your
   ruling, which is why C3/C4 are one item.
3. **C9 is the only change that makes req. #4 achievable at all**, and it is the largest.
   It should not be bolted onto a fix round.
4. **`GOLD-EX-11` stays FAIL.** Nothing proposed here redefines it. Axis 1 keeps it
   exactly as-is; Axis 2 is additive and separate.
5. **Nothing here says the OCR pipeline is accurate.** No clinical accuracy claim is made
   or implied by any of the above.

---

# 8. Implementation record — owner ruling `5915830616`

Appended after the owner's priority ruling. Sections 1–7 above are unchanged; where
this section contradicts them, **this section is what the code does now**.

## 8.1 What was implemented

### P0 — Fail-closed document verification (implemented)

The chosen instrument is the **`page_missing` quality flag**, because the owner asked
for the existing `PAGE_MISSING` / `VI-005` / `VI-002` contracts to be reviewed before
choosing. What that review showed:

* `PAGE_MISSING` was declared in the closed enum, listed in `mapping.BLOCKING_FLAGS`,
  and documented in `EXTRACTION_PROVENANCE.md` §4 as *"OCR yielded nothing usable for
  the page / blocking if the field was expected there"* — **and produced by no code
  path at all.** It was dead code.
* That documentation is precisely the R17 case, so no new flag, enum value, column,
  migration or reason code was required. Nothing locked was redefined.

**`field_parser._unattributed_value_facts()`** now keeps a `Value:` line the lab-line
grammar could not attribute as a `value` candidate with:

| Property | Value | Why |
|---|---|---|
| `normalized_value` | `None` | no number is inferred from an unread line |
| `raw_text` | literal token after the label, bounded to 120 chars | the page's own characters remain the evidence |
| `quality_flags` | `(PAGE_MISSING,)` | the documented marker for this exact situation |

It fires only when the page carries a `Value:` label that `_TEST_VALUE` did not already
match, so a title/reference-only report stays genuinely document-only. **Measured: all
12 committed fixtures have zero unmatched `Value:` lines, so no existing parse changes.**

**`issues.collect_flag_issues()`** maps `page_missing` on a `value` fact to `VI-005`
(`value_unreadable`) — the documented consequence in §4 of the provenance contract. The
message template is unchanged and pre-existing.

**`verification._unread_measurement_blocks_verification()`** stops `verified` from being
reachable while a declared measurement has never been successfully read. The document
stays `needs_verification` with `VI-005` open — an actionable blocker, not a silent
`verified`. It clears only when a **verified `value` fact with a normalized number**
exists, i.e. when a doctor actually supplies the reading by correction.

Superseded originals are excluded, so a later correction resolves the block instead of
being shadowed by its own history.

### P1 — Correction and issue lifecycle integrity (implemented)

**`field_parser.normalize_corrected_value()`** validates per field, deliberately not
with one global numeric rule:

| Field | Rule | Rejected examples |
|---|---|---|
| `value` | the parser's own `_normalize_number` | `'   '`, `'abc'`, `'nan'`, `'inf'`, `'10\n5'`, `'1O5'` |
| `unit` | closed `DocumentUnit` list | `'mmol/L'` |
| `report_date` | `YYYY-MM-DD` **and** calendar-valid | `'not-a-date'`, `'2026-13-45'` |
| `test_name`, `reference_text` | non-blank, no control characters | `'   '`, `'a\tb'` |

It never repairs: `'1O5'` stays refused, exactly as `_normalize_number` refuses it.

**Precedence is deliberate.** Validation runs in `record_decision` *after* the identity
guard and the append-only guard, not in the route. An earlier draft validated in the
route and broke `test_p3_r02_corrected_fact_cannot_bypass_the_identity_blocker`: a
wrong-patient document answered `400 malformed date` instead of
`409 E_VI_004_UNRESOLVED`, which would have hidden the real reason for refusal. A
cosmetic validation message must never mask an identity blocker.

**`quality.compute_drafts()`** no longer derives flag issues from superseded originals.
This is the D-14 defect one layer over: `VI-005` stayed open forever on a document
whose value had already been corrected, because the rejected history row kept its
flags. History still keeps its flags for audit; it stops generating blockers. Plain
rejections are **not** superseded, so a rejected value still blocks — unchanged.

**Probe evidence is no longer asserted.** The `GOLD-EX-11` payload's
`human_review_required` was a hard-coded `True`. It is now computed by
`collect_flag_issues()` — the same function the HTTP path uses — and accompanied by
`human_review_required_basis` and `human_review_blocking_issues`. Measured on the
owner's exact OCR text: `True` with `['VI-005']`. (It would read `False` if no blocking
issue were raised, which is the point.)

### P2 — Durable OCR provenance (DESIGN ONLY, not implemented)

See `docs/phase-reports/P3_R17_P2_OCR_PROVENANCE_DESIGN.md`. Requires owner approval:
it needs a schema addition and a new read surface, both of which the ruling forbids
without explicit authorization.

### P3 — OCR recognition experiments (NOT RUN)

Blocked: there is still no Tesseract binary in this sandbox. `preserve_interword_spaces`
vs. parser relaxation remains **unmeasured** and is not claimed. The conservative
parser-relaxation datapoint from §5 (`\s{2,}` → `\s+` changes 0 of 12 fixtures and
leaves the suite green) stands as the only evidence gathered, and it was reverted.

## 8.2 Findings from §1–§7 that did **not** hold up

Recorded because the analysis was published and should be corrected where wrong.

| Ref | Original claim | Outcome |
|---|---|---|
| C4/§5 | "Revive `PAGE_MISSING` **or** add a `measurement_not_read` reason code." | Partly wrong. `page_missing` + the existing `value_unreadable` reason covered it. The new reason code I first implemented was **removed** — it would have added a value to a documented reason set for no gain. |
| §2-Q4 | "The doctor can correct and keep lineage: **PASS**." | Correct, and re-verified. My §5 proposal C9 (expose OCR text) remains valid but unimplemented. |
| §5 C8 | "Document-level issues claim `extractor='pypdf'`." | **Not fixed this round.** It is real, but it is a wire-contract change (`document_span` evidence with null span fields), and the ruling forbids changing the public API contract without approval. Documented in the P2 design instead. |
| §5 C2 | "Relax `\s{2,}` → `\s+`; 0 of 12 fixtures change." | Measurement reproduced and still true, but **not adopted** — the ruling defers recognition tuning to P3 experiments. |
| §2-Q5 | "A zero-fact document reports an empty issue list." | **Still true and still unfixed.** A document whose OCR yields no text at all is `failed`/`no_facts_extracted` with `verification_issues: []`. That case has no `Value:` label, so `page_missing` cannot fire. It needs its own governance decision (does a failed document belong in a review queue?) and is not silently changed here. |

## 8.3 Known limits of this round, stated plainly

1. **No real-engine evidence.** Every R17 test injects OCR text. The gate was exercised
   end-to-end with a scripted engine only. Recognition fidelity is unmeasured.
2. **A destroyed `Value:` label is undetectable.** If OCR damages the label itself, no
   deterministic signal remains that a measurement was declared, so no blocker is
   raised. `test_r17_lost_label_line_cannot_reach_verified` asserts the property that
   still holds (no observation can be manufactured). The owner's actual OCR preserved
   the label, which is why the real case *is* covered.
3. **`GOLD-EX-11` remains FAIL / NOT PROVEN** and was not touched.
4. **Windows behaviour is unchanged and unverified here.** A re-run of the acceptance
   probe is the owner's.

## 8.4 Traceable test matrix

The required matrix lives in `docs/phase-reports/P3_R17_TEST_MATRIX.md`, and is
implemented by `backend/tests/p3/test_p3_r17_safety.py` (24 tests). Every row names the
test that enforces it and the pre-fix result.

---

# 9. R18 — two correction defects in the R17 fallback

Owner review [`5916114433`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916114433)
found two defects **in R17's own new code**, not in the code it replaced. Both were
real; both were reproduced before being fixed, and 12 of the 14 new tests were red
against `73639d0`.

## 9.1 R18-A — the span did not resolve to `raw_text`

R17 computed `raw_text` from a **stripped** token but derived `char_start`/`char_end`
from the **unstripped** source, offsetting from `label.end()`. Measured on the owner's
real OCR line:

| | Before (`73639d0`) | After |
|---|---|---|
| `raw_text` | `'105 mg/dL'` | `'105 mg/dL'` |
| `page.text[char_start:char_end]` | `' 105 mg/d'` | `'105 mg/dL'` |
| exact slice? | **no** | **yes** |

The span retained the leading space and dropped the final character. With several
leading spaces it drifted further (`'     105 '`), and a >120-char token broke in two
ways at once: the span length came from the *unbounded* token while `raw_text` was
truncated to 120.

`EXTRACTION_PROVENANCE.md` §3/§5 requires the span to be the exact source slice, and
`span_is_resolvable()` only checked *bounds*, so no test could have caught this. The fix
computes the trimmed range first and derives both fields from it:

```python
raw_segment = page.text[label.end():line_end]
segment = raw_segment.strip()
value_start = label.end() + (len(raw_segment) - len(raw_segment.lstrip()))
raw_text    = segment[:120]
value_end   = value_start + len(raw_text)   # bounded to the stored text
```

The clamp is essential: bounding `raw_text` without bounding the span is what made the
long-token case diverge.

**Not fixed, and deliberately so:** `span_is_resolvable()` still checks bounds only, so
it cannot detect a future `raw_text`/span mismatch. Asserting equality inside it would
change validation semantics for every fact and was not authorized here. The R18 tests
assert the equality property directly instead. Flagged for the owner as a candidate
hardening.

## 9.2 R18-B — a bare `Value:` label was dropped

`if not token: continue` skipped a line ending in `Test: Glucose Value:`. The label is
present, so this is **not** the documented destroyed-label limit: the document declares a
measurement, nothing recorded it, and — measured — approving only the date and reference
range reached **`verified`**. Precisely the failure R17 existed to prevent, one branch
over.

Now a bare label is preserved as literal evidence:

| | Value |
|---|---|
| `raw_text` | `'Value:'` — the label itself, exact and non-empty |
| span | `text[label.start():label.end()]`, resolves exactly to `raw_text` |
| `normalized_value` | `None` |
| flag | `page_missing` → blocking `VI-005` |

No number is fabricated and a bare label is never treated as document-only. The
distinction that still holds: a report with **no** `Value:` label at all remains
legitimately document-only and raises no missing-measurement blocker (control test
`test_r18_b_bare_label_is_not_treated_as_document_only`).

## 9.3 Evidence

* `backend/tests/p3/test_p3_r18_provenance.py` — **14 tests**; 12 red against `73639d0`,
  including `assert 'verified' != 'verified'` for the bare-label HTTP case.
* Full suite **635 passed**, P3 **252** (was 238).
* `ruff` clean, 103 files formatted; OpenAPI **PASS (16 paths / 17 operations, 41
  schemas)**; secret scan PASS (196 files); Alembic smoke PASS in `head`/`p2`/`p1`/`base`.
* 12 fixture hashes verify, **zero** changed; no API, schema, or migration change.
* Gate re-run (scripted engine, owner's bytes): still **FAIL** / `diagnosis=substituted`
  / `human_review_required=True` from `['VI-005']`. `GOLD-EX-11` untouched.

## 9.4 What this round did not establish

Real-engine behaviour at this SHA. R17 and R18 are verified deterministically and over
HTTP with injected OCR text; the last real Windows evidence remains `1b17a9a`. A
real-engine re-run is the owner's.
