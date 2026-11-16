# P3-R20 — Engineering decision report: OCR configuration vs. false-clean extraction

**Status: ANALYSIS AND SPECIFICATION ONLY. No production code, configuration, API, schema,
migration or UI change is proposed for implementation without the owner authorization listed
in §8.1.6 and §9.** PR #10 stays DRAFT; P3 stays IN_REVIEW; `GOLD-EX-11` stays
**FAIL / NOT PROVEN**; no merge; P4/P5 not started.

Base: `fdce02f7f5f743d4a0b77319729c060fe3685aa6`.
Owner evidence: review [`5916564273`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916564273)
(Windows 11, Tesseract `5.4.0.20240606`, Pillow 40 px fixture).

**Revision 2 (`baaf7ee` + this round).** The first revision of this report claimed that
rejecting the false-clean measurement left the document `verified` "with **no issue at
all**". **That claim was wrong** and is corrected in §1.1. The error came from reading
only the HTTP response and `document.extraction_status`/`failure_code`, never the
persisted `VerificationIssue` rows or the `DEMO_REVIEW_RULES.md` D-14 counting rule. The
actual defect is narrower and worse: **`verified` while a blocking `VI-002` is still
open, and no doctor action can ever clear it.** The correction was requested in review
[`5916697862`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916697862).

**Revision 3 (this round).** Review
[`5916921991`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916921991)
found three errors in revision 2's S1 test matrix: A-3 demanded a `VI-005` that no code path
emits for a rejected *clean* value; A-6 claimed a system-wide invariant that the report's own
§1.2 counterexample disproves; and the report implied S1 closes the corrected-from-unread
path and XO-3, which it does not. Revision 3 replaces §8.1 with a scoped acceptance
specification (C1–C8), states S1's exact bounds, corrects "adopted" to "recommended, not
authorized", and lists the precise owner authorization required in §8.1.6. §8.2 records the
three corrections. **Still no production change.**

---

## 0. Evidence ledger — who proved what

The report distinguishes three evidence classes throughout. A claim is never upgraded
between them.

| Class | What it establishes | Source |
|---|---|---|
| **Real engine** | Tesseract's actual recognition on the owner's Windows box, both configurations | Owner experiments, `5916564273` |
| **Scripted HTTP** | Application behaviour *given* engine output, through the real upload → extract → verify path | This session, on `fdce02f`, injected OCR text |
| **Existing code** | What the committed implementation does, readable/executable by anyone | This session, parser + issue-logic runs on `fdce02f` |

Nothing in this report is real-engine evidence produced by me. There is still no
Tesseract binary in this sandbox, so **no configuration option below has been measured
by me on a real engine.**

### 0.1 Reproduction of the owner's A/B result against the committed parser

Both owner OCR outputs fed to the shipped parser on `fdce02f` (existing-code class). This
independently reproduces the owner's finding:

| | **A** — current production config | **B** — experimental `preserve_interword_spaces=1` |
|---|---|---|
| owner OCR text | `Test: Glucose Value: 105 mg/dL` | `Test: Glucose         Value: 105 mg/dL` |
| fields extracted | `report_date`, `value`, `reference_text` (**3**) | `report_date`, `test_name`, `value`, `unit`, `reference_text` (**5**) |
| value fact | `raw='105 mg/dL'`, `norm=None`, `page_missing` | `raw='105'`, `norm='105'`, `unit='mg/dL'`, **`clean`** |
| flag-derived issues | `['VI-005']` | **`[]`** |
| span exact | yes (R18 fix holds) | yes |

The owner's statement that B is a *demonstrated false-clean extraction risk* is correct
and reproducible. In both cases the engine substituted `O`→`0`; the parser auto-corrected
nothing. B's better layout turns the same recognition error into a syntax-clean candidate.

---

### 0.2 The three requirements this report separates

Revision 1 treated the OCR risk as one problem with one fix. It is three problems with
different owners, different evidence classes and different acceptance gates. **They must
not be collapsed**, and closing one is never evidence that another is closed.

| Req | Statement | Observable failure today | Closes with | Not closed by |
|---|---|---|---|---|
| **A** | A rejected or unread declared measurement must not leave misleading document state | `verified` while blocking `VI-002` is open (§1.1) | S1 state-model change (§6.2, step 1) | any OCR configuration; any additional issue type |
| **B** | An OCR-derived fact needs a reviewable original source, accurate provenance, and an explicit verification process | `raw_text` is the engine's output presented as the page; no OCR text retrievable (§3) | persisted page text + scoped read endpoint + retention decision, plus accurate docs (steps 4–7) | A; a flag; `text_char_count` alone |
| **C** | False-clean OCR errors cannot be reliably inferred from parsed text alone — residual human-review risk | `1O5`→`105` is `clean`; a destroyed `Value:` label is invisible (§2, §10) | **nothing in this report** — documented as a carried risk | A and B both; B reduces but does not remove it |

**The load-bearing consequence:** fixing **A** does not fix **B** or **C**, and does not
make `preserve_interword_spaces=1` safe. B's doctor (§2) never rejects anything, so A's
fail-closed rule never fires for the case that actually produced a wrong
`doctor_verified` Observation.

---

## 1. The actual defect, re-measured against persisted state

The owner's framing — "neither weaker parser regex nor global B option alone is a safe
fix" — is right, but the second reason is not what revision 1 of this report said it was.

### 1.1 Correction of my previous claim

Revision 1 stated that after rejecting the false-clean measurement the document became
`verified` with **"no issue at all"**. **That is false.** Re-measured on `baaf7ee` with
the five artefacts the owner required — final document status, the full
`verification_issues` response, the persisted `VerificationIssue` rows, the `ExtractedFact`
verification statuses, and the Observation rows, all captured **after every decision**:

| Case | `document.extraction_status` | persisted open issues | Observation created |
|---|---|---|---|
| **A** (current prod, `page_missing`) | `needs_verification` | `VI-002`, `VI-005` | none |
| **B** (false-clean, `clean`) | **`verified`** | **`VI-002` (open, `blocking=1`)** | none |

So case B does **not** end issue-free. `VI-002` (`fact_unverified`) survives a plain
rejection exactly as `DEMO_REVIEW_RULES.md` D-14 and `quality.compute_drafts()` require:
the D-14 counting rule includes every non-`verified`, non-superseded fact, and a plain
rejection is not superseded. The report's error was an inference, not a reading — the
round-14 probe read `verification_issues` from the *response* and
`extraction_status`/`failure_code` from the document, and never queried the persisted
rows. **The response and the persisted rows agree here; the mistake was not querying them
at all.**

The real defect is therefore the one the owner named:

> **The document is `verified` while a blocking `VI-002` is still `open`.**

### 1.2 The contradiction is general, not OCR-specific

This is not a false-clean-OCR artefact. It reproduces on a **clean text-layer PDF with no
OCR involved**: upload `report_a_clean.txt` as a PDF, reject the single `reference_text`
fact, approve the remaining four.

```
document_status: verified | failure_code: None
persisted rows:  [('VI-002', 'open')]        open issues: ['VI-002']
-> CONTRADICTION
```

Same status, same open issue, no engine involved. **Requirement A is a core state-model
defect that P3 has today, independent of OCR configuration and independent of
`preserve_interword_spaces`.** Treating it as an OCR problem, as revision 1 did, would
have shipped a fix in the wrong subsystem.

### 1.3 Why this happens, and why the obvious fix deadlocks

Two independent derivations disagree about what "done" means:

* `_recompute_document_status()` sets `VERIFIED` when no fact is `pending`, not every
  fact is `rejected`, and `_unread_measurement_blocks_verification()` returns false. It
  never consults `VI-002`.
* `compute_drafts()` re-derives `VI-002` from the same facts on every read and keeps it
  open for a plain rejection, per D-14.

Case A escapes only by accident: `page_missing` is a *flag on the value fact*, a rejected
fact keeps its flags, and `_unread_measurement_blocks_verification()` finds a `page_missing`
value fact with no verified numeric value. Case B has no flag to inherit and no unread
declaration to detect, so it takes the last branch and writes `verified`.

The obvious repair — "derive document status from open issues" — **deadlocks**, and this is
measurable today:

| Sequence | Result |
|---|---|
| reject a fact, approve the rest | `verified` + `VI-002` open |
| re-decide that fact `verified` | **409 `E_FACT_ALREADY_DECIDED`** — cannot be undone |
| state afterwards | `verified` + `VI-002` **still open** |

Records are append-only (D-11): a decision cannot be revised, and `VI-002` counts the
rejected fact forever. So an open `VI-002` is **not always a doctor-actionable blocker** —
after a plain rejection it is permanently unclearable. Any implementation must not equate
"blocking" with "clearable", or it turns today's contradiction into a permanently stuck
document. This is the constraint that shapes §6.2 and §8.

By contrast the **correction** path is clean: correct the value, approve the rest →
`verified` with `VI-002` **`resolved`**, because a correction supersedes the original and
D-14 excludes superseded facts. The asymmetry is the whole defect: *correcting* resolves
the issue, *rejecting* strands it.

### 1.4 What follows for the recommendation

* **Requirement A** (a rejected or unread declared measurement must not leave misleading
  document state) is real, is a state-model problem, and **cannot be fixed by any OCR
  setting**. B makes recognition better structured and makes A strictly worse.
* Requirement A is **necessary but not sufficient**. It says nothing about whether the
  value the doctor *verified* was read correctly — that is requirement B (§3) and
  requirement C (§10.1). **Closing A does not close B or C, and does not make
  `preserve_interword_spaces=1` safe.**
* No part of this round changes D-14. `VI-002` must keep counting plain rejections; the
  fix belongs in status derivation and in giving a rejection a first-class meaning, not in
  suppressing the issue.

---

## 2. End-to-end realisation of the false-clean risk

Owner's B output through the real HTTP path (scripted HTTP, `fdce02f`):

```
document_status: needs_verification
verification_issues: [('VI-002', 'fact_unverified')]        <- generic only, no VI-005
value: raw='105' norm='105' flags=['clean'] conf=0.95 status=pending

after approving all five facts:
  document_status = verified
  observations created: 1  [('glucose', 105.0, 'mg/dL', 'doctor_verified')]
```

The committed source image reads `1O5`. A `doctor_verified` `glucose = 105.0`
Observation is derivable from it. This is **not** a clinical-accuracy claim about the
engine; it is the demonstration that the pipeline can attach the `doctor_verified`
provenance class to a value the source does not support, with nothing but generic
`VI-002` in the way.

**Requirement B, stated precisely.** The doctor approving `105` has no way to discover the
substitution through the application. Approving all five facts is a *complete, correct* use
of the interface, and it yields a `doctor_verified` Observation whose value the source
image contradicts. Nothing in the pipeline is buggy here — the process is missing a step it
was assumed to have. Closing requirement A (§1) does not change this: A only governs what
happens when a measurement is *rejected or unread*, and this doctor never rejects it. This
is why A and B must be accepted, gated and sequenced as **separate requirements**.

The existing guards that do *not* help here, with reasons:

| Guard | Why it does not catch B |
|---|---|
| `looks_corrupted()` | scans a fact's `raw_text` for `O`/`l` next to digits. After substitution `raw_text='105'` — no `O` remains. Structurally blind. |
| `ocr_confidence_floor` (0.70) | owner's confidence 0.95; the engine is *confident* about the wrong answer |
| `page_missing` | only present when the value is **not** parsed. That is the A case only |
| `VI-002` | generic; identical for a correct document with pending facts. It stays open after a plain rejection (§1.1) but says nothing about *this* value being wrong |
| `span_is_resolvable()` | bounds only; span is genuinely exact here |
| doctor verification | the only real gate — and it asks about a value the doctor cannot compare against OCR text (§3) |


---

## 3. Can the doctor compare source, OCR text, and proposed value?

**Source image: yes. OCR text: no.** Measured (scripted HTTP):

| Artefact | Retrievable | Where |
|---|---|---|
| original bytes | **yes** | `GET /{id}/file`, 37 656 B, byte-identical to upload |
| per-fact excerpt + span | **yes** | `evidence.raw_text`, `page_index`, `char_start`, `char_end` |
| full OCR page text | **no** | not returned; **not stored anywhere** |
| `text_char_count`, `engine_confidence`, `preprocessing` | **no** | stored in `extraction_attempt`, deliberately omitted from `ExtractionAttemptSummary` |
| attempted paths / tool version | yes | `attempts[]` |

Response keys are exactly `document_id, document_status, facts, attempts,
verification_issues, disclaimer`. There is no field that carries what the engine read.

The consequence for B is precise: the doctor sees the image (`1O5`), and sees
`raw_text='105'`. `raw_text` is documented as *"the exact source slice"*, and after R18 it
genuinely is **the exact slice of the OCR text** — not of the image. For a text-layer PDF
those coincide. For OCR they do not, and nothing in the response distinguishes them. A
doctor comparing "the excerpt" to "the image" is comparing the engine's output to the
image and calling the difference a transcription of the page.

`evidence.extractor='tesseract'` is the only signal that OCR was involved. It is easy to
miss and does not say *what* the engine read.

So: **the review premise of US-09 / `EXTRACTION_PROVENANCE.md` §5 rule 4 — "the UI must be
able to render the source page/snippet for any cited claim, so the doctor can audit the
extraction" — cannot be satisfied for an OCR document today.** The snippet is the claim,
not the source.

---

## 4. Is P2 durable provenance a required dependency?

**Yes for trustworthy review; not for narrowing the false-clean window.** These are
separable and the separation is what makes an approved increment possible now.

* **Not required** to stop a false-clean candidate from being *silently* treated as
  verified evidence. That is a state-model problem (§1) solvable with no new storage.
* **Required** to let a doctor *detect* a substitution and record a defensible decision.
  Without the OCR text, a substitution is undetectable from inside the app; the doctor is
  asked to certify a number against evidence they cannot see.

The minimum P2 surface is much smaller than the full table I proposed in
`P3_R17_P2_OCR_PROVENANCE_DESIGN.md`. One field on the existing
`ExtractionAttemptSummary` — `text_char_count` — is already persisted and would let a
doctor see "the engine read 91 characters for this page". A second, larger option adds the
text itself. Both are wire-contract changes and neither is authorized.

**Deferred but relevant:** `EXTRACTION_PROVENANCE.md` §5 and `field_parser`'s module
docstring both claim spans are re-resolvable against *stored* page text. No stored page
text exists. That documentation is currently untrue and should be corrected or the feature
built — it is a governance item whether or not any code changes.

---

## 5. Acceptance gates (four separate properties)

The point is that they can be green or red **independently**: a recognition improvement
must never be able to cost a fail-closed property without a red gate.

| Gate | Property | Never evidence for |
|---|---|---|
| **G1 `OCR-RF`** | did the engine read the right characters? | that a field was extracted, or that review is safe |
| **G2 `SFE`** | did the parser extract clean structured fields? | recognition fidelity — B extracts 5 clean fields from a **wrong** value |
| **G3 `FC`** | does the workflow fail closed on an unresolved measurement? | that any given approved value is correct |
| **G4 `XO`** | is a promotion explicitly doctor-decided and attributable? | that the doctor had the evidence to decide it |

A clean positive field extraction (G2) co-existing with a wrong character read (G1) is
exactly case B, and it is the reason these four are never summed into a single verdict.

### G1 — `OCR-RF` Recognition fidelity *(real engine only; owner Windows)*

| ID | Criterion | Today |
|---|---|---|
| RF-1 | Clean 40 px report: all 5 declared fields recognized with intact `Value:` label | **PASS under B only**; FAIL under A (3 fields) |
| RF-2 | Ambiguous `1O5` source: does the engine preserve `O`? | **FAIL, both configs** — engine emits `105` |
| RF-3 | Character fidelity of the value token **measured and published**, never asserted | Already published by the probe |

RF-1 and RF-2 are in direct tension: the configuration that fixes one does not fix the
other, and no configuration tested fixes RF-2. **G1 should be reported as a measured
limitation, not a P3 gate.** P3's safety story must not depend on RF-2 passing.

### G2 — `SFE` Structured field extraction *(parser only; scripted/parser evidence)*

| ID | Criterion | Today |
|---|---|---|
| SFE-1 | A two-space lab line yields `test_name`, `value`, `unit` | PASS |
| SFE-2 | A collapsed one-space line yields a preserved `page_missing` value, never a guessed number | PASS (R18) |
| SFE-3 | Spans are exact slices (R18-A) | PASS |
| SFE-4 | No OC configuration change is adopted without G3/G4 staying green | *pending decision* |

SFE is where B is attractive and where its cost must be priced: B converts SFE-2 from a
preserved `page_missing` fact into a `clean` parsed one. **SFE must not be allowed to
improve at G3/G4's expense.**

### G3 — `FC` Fail-closed routing *(scripted HTTP; engine-independent)*

| ID | Criterion | Today |
|---|---|---|
| FC-1 | A declared-but-unread measurement blocks `verified` | **PASS for A** (R17/R18) |
| FC-2 | A **rejected** measurement cannot leave a document whose status contradicts its open issues | **FAIL** — measured `verified` with `VI-002` open, and D-14 keeps it open forever (§1.1, §1.3) |
| FC-3 | A false-clean candidate cannot reach a `doctor_verified` Observation without source comparison | **FAIL** — B reaches `verified` + 1 `doctor_verified` Observation on approval; `VI-002` is open but does not block promotion (§2) |
| FC-4 | Zero-fact document surfaces a reviewable blocker | **FAIL** — `failed` + `verification_issues: []` |
| FC-5 | Destroyed `Value:` label cannot reach `verified` on a date alone | **FAIL** — measured `verified`, 0 observations |

FC-2…FC-5 are all reachable today and all independent of OCR configuration. **This is the
increment to approve first.**

Two criteria are deliberately *not* claimed as fixed by any option here:

* FC-3 is a **process** failure, not an issue-emission failure. Emitting more issues would
  not make the doctor able to compare anything. It needs requirement B (§3), which is a
  review-capability and provenance question, not a flag.
* FC-2's fix must not simply make document status follow open issues: `VI-002` is
  permanently unclearable after a plain rejection (409 `E_FACT_ALREADY_DECIDED`, §1.3), so
  that would convert a contradiction into a deadlock. Status must key on *the specific
  condition* (declared measurement unresolved), not on the issue count.

### G4 — `XO` Explicitly doctor-verified observations *(scripted HTTP)*

| ID | Criterion | Today |
|---|---|---|
| XO-1 | No Observation is created without an explicit doctor decision | **PASS** |
| XO-2 | Every Observation carries `source_fact_id`, `doctor_verified`, `verified_by_user_id` | **PASS** |
| XO-3 | A `doctor_verified` Observation cannot be derived from a value the pipeline knows was unread or rejected | **FAIL** — see note |
| XO-4 | Correction is append-only with lineage, original excerpt preserved | **PASS** (R17/R18) |

**XO-3 note.** The pipeline does *not* currently emit an Observation from a rejected fact
(`decide_mapping` reads verified facts only), so the narrow literal reading passes. It fails
on the substantive reading: a value the pipeline knows it could not read can reach
`doctor_verified` by being **corrected** to a number no actor can check, and the
false-clean case reaches it by plain approval. Step 1 closes the corrected-from-unread path
by keeping the document in review; **it does not close the false-clean path** — that is
requirement B, and XO-3 stays FAIL until B lands.

---

## 6. Options

### 6.1 For the recognition/layout problem (§0, G1/G2)

| # | Option | Effect on G1/G2 | Effect on G3/G4 | Scope | Verdict |
|---|---|---|---|---|---|
| **O1** | Keep current config; improve nothing | A stays: 3 fields, `page_missing` | unchanged, fail-closed preserved | none | Safest, leaves SFE lossy |
| **O2** | Global `preserve_interword_spaces=1` | 5 fields on clean reports | **regresses FC-3**: a syntax-clean candidate goes straight to `doctor_verified` | 1 line in `ocr.py` | **Reject** (owner ruled against; `preserve_interword_spaces=1` stays off). Not because of `VI-002` — B still has `VI-002` open — but because B removes the only signal (a `page_missing` declaration) that made a doctor look at the value at all |
| **O3** | Parser relaxation `\s{2,}`→`\s+` | 5 fields from collapsed text | **same false-clean regression**, and breaks the two-space column contract that distinguishes a lab row from prose | 1 line | **Reject** for the same reason |
| **O4** | Two-pass OCR: read with and without space preservation; parse the **intersection** | 5 fields when both agree | disagreement is itself a flag → no false-clean when passes differ | moderate, `ocr.py` + attempt model | **Most promising**, but needs G3 fixed to be safe |
| **O5** | Layout-independent parse: use `image_to_data` word boxes for column detection instead of whitespace | best structural result | none by itself | large, new parser path | Best long-term; not now |
| **O6** | Adopt O2/O3 **only behind** a requirement-B control | 5 fields | needs the doctor to confirm against source, not merely to see a flag | small once B exists | **Deferred.** It is not a "FC-3 gate" — FC-3 is only closed by B (§3), and B's review capability is itself blocked on governance (§6.3) |

**Key point:** O2/O3 are not unsafe because they are wrong about layout. They are unsafe
because **a syntax-clean candidate currently needs no source comparison** — the doctor's
approval is the only control, and it is given the parsed value with no way to check it. A
flag alone does not repair this: an extra `VI-*` row would sit beside the same unverifiable
value. **Only requirement B (reviewable original source + accurate provenance) closes
FC-3**; A restricts what happens to an unresolved measurement, and neither A nor any flag
makes `preserve_interword_spaces=1` safe.

### 6.2 For the state-model problem (§1, G3)

| # | Option | Fixes | Cost / risk |
|---|---|---|---|
| **S1** | Treat a rejected `value` fact as "measurement unresolved": keep the document `needs_verification`, reopen `VI-005` | FC-2, XO-3 | changes status semantics for *any* rejected value fact — including a doctor deliberately rejecting a value they consider spurious. **Over-blocks by design.** Owner direction: adopt as the narrow interim fail-closed measure. |
| **S2** | Record the reason for rejection as a typed code, and block on `reason ∈ {unreadable, ambiguous, ocr_doubt}` | FC-2 precisely, no over-blocking | new enum + `fact_verification` column → migration + contract change |
| **S3** | Give a false-clean candidate a flag at intake, e.g. `unverified_ocr`, when its value token came from a page whose sibling lines were collapsed | FC-3 without touching configuration | requires a deterministic detector — and there may not be one. **Unproven; needs investigation before it is promised** |
| **S4** | Make `verified` require ≥1 non-rejected `value` **or** an explicit "no measurement in this document" acknowledgement | FC-2, FC-3, FC-5 | new acknowledgement surface → API change |
| **S5** | Surface every document in a terminal state with zero open issues for review (fix zero-fact FC-4) | FC-4 | small; needs a governance decision on failed-document triage |

**S2 is the most precise** and the only one that does not over-block; it is also the most
expensive (schema). **S1 is cheapest** and over-blocks. **S3 is unproven.** S4 is cleanest
conceptually and largest.

**Adopted direction: S1, narrowed.** The owner's ruling favors S1 as an *interim*
fail-closed measure, accepting that it over-blocks. The reasoning:

1. **Fail-closed is the correct default when the alternative is a false `verified`.** A
   doctor rejecting a value is stating the measurement is unknown; `needs_verification` is
   the honest representation of "unknown", and `verified` is the dishonest one.
2. **It preserves the append-only contract.** S1 changes a derivation, not a record. It
   writes no new fact state, revises no decision, and deletes no history. D-11 and D-14
   both hold unchanged.
3. **It needs no migration and no API change**, so it is reviewable as a small diff.
4. **Its cost is over-blocking, and over-blocking is visible and safe.** A doctor who
   deliberately rejected a spurious value sees a document that stays in review; they are
   inconvenienced, not misled. The reverse error is a `verified` document whose
   measurement nobody read.

**Explicit non-claims for S1:**

* S1 does **not** close FC-3. B's doctor never rejects; S1 never fires.
* S1 does **not** give the doctor a way to read the OCR text (requirement B).
* S1 does **not** detect a wrong value that was verified (§10.1, requirement C).
* S1 does **not** make `preserve_interword_spaces=1` safe, and must not be cited as
  grounds for enabling it.
* S1 does **not** close the corrected-from-unread path and does **not** close XO-3 in
  general. A correction creates a verified numeric replacement and supersedes the original,
  which is the sanctioned route out of an unread measurement; source review of such a
  correction is requirement B (§8.1.3).
* S1 does **not** harmonize status for rejected **non-measurement** facts. A rejected
  `reference_text` can still leave `verified` with open `VI-002` — measured in §1.2. That is
  R20-D2 and is deliberately out of scope.
* S1 must key on **the declared-measurement condition over active (non-superseded) facts**,
  not on `VI-002` being open: an open `VI-002` after a plain rejection is unclearable (409,
  §1.3), so "status follows open issues" would deadlock. It must also not match a
  *superseded* rejected value, which is exactly what a valid correction leaves behind
  (§8.1.1, measured).

A later explicit acknowledgement / typed rejection-reason design (S2 or S4) remains
available if over-blocking proves unacceptable in use; it is **not** required for the
interim measure and is out of scope for the next increment.

### 6.3 For reviewability (§3, P2)

| # | Option | Gives doctor | Scope | Verdict |
|---|---|---|---|---|
| **P-a** | Add `text_char_count` to `ExtractionAttemptSummary` (already stored) | "91 chars read" — weak but real | wire change, no migration | cheapest useful step |
| **P-b** | Add `GET /{id}/text` + persisted page text | full comparison | table + endpoint + retention decision | the real fix; blocked on governance |
| **P-c** | Correct the documentation to say spans resolve at intake only | honest, no capability | docs only | should happen regardless |
| **P-d** | Show `extractor` more prominently / require acknowledgement before approving an OCR value | friction-based mitigation | API/UI change | weak; false confidence |

**P-c is unconditional.** P-a is the smallest honest step. P-b is required for the review
premise to hold.

**P-c is documentation correction only, and it is separable from P-b.** The docs currently
describe a source-comparison capability that does not exist: `EXTRACTION_PROVENANCE.md` §5
rule 4 / US-09 describe re-resolving a span against stored page text, but no OCR page text
is persisted anywhere and no endpoint returns it. Correcting that text to say spans resolve
**at intake only** is authorized by the owner direction and is the next increment's only
documentation change.

**Persisted page text, a scoped read endpoint, and retention are three separate governance
decisions, and P-c does not pre-approve any of them.** P-b stays blocked until each is
decided on its own terms (R20-D5/D6). Requirement B is therefore *acknowledged as
unclosed* by this round, not quietly satisfied by a docs edit.

---
## 7. Safeguards enforceable before and during verification

Ranked by what exists today versus what needs a decision.

| Stage | Safeguard | Status |
|---|---|---|
| Intake | `pending` on every fact; no auto-promotion | **existing, PASS** |
| Intake | explicit rejection / correction only, append-only | **existing, PASS** (D-11) |
| Intake | `page_missing` for an unread declared measurement | **existing (A only)** |
| Intake | per-field correction validation (no `'   '`/`'abc'`) | **existing (R17)** |
| Intake | `VI-002` counts a plain rejection and is never suppressed | **existing, PASS** (D-14, must not change) |
| Intake | rejected **measurement** leaves the document unresolved **in document status** | **GAP — A / FC-2 → S1, not authorized** |
| Intake | rejected **non-measurement** fact leaves a consistent status | **GAP — out of S1 scope, R20-D2** |
| Intake | a plain rejection's `VI-002` is clearable by some doctor action | **GAP — §1.3 (409); unchanged by S1** |
| Review | doctor can read the OCR text beside the parsed value | **GAP — B / P2** |
| Review | provenance says spans resolve at intake only | **GAP — P-c (docs)** |
| Promotion | observation requires a doctor decision | **existing, PASS** |
| Promotion | no observation derived from a rejected measurement | **existing, PASS** (measured, C5) |
| Promotion | a corrected-from-unread value is blocked | **NOT CLAIMED — correction is the sanctioned route** (§8.1.3) |
| Promotion | a false-clean value requires source comparison before `doctor_verified` | **GAP — B / FC-3** |

The pattern is consistent: **everything before the doctor works; everything about giving
the doctor the evidence, and everything about the state after a rejection, does not.**

**S1 closes exactly two rows above** — the rejected-measurement status gap and, with it, the
narrow form of XO-3. It closes **no** non-measurement row, **no** reviewability row and
**no** false-clean row.

---

## 8. Proposed implementation sequence

Each step is independently reviewable and independently gated. **Nothing starts without
the decision in §9.** Steps are ordered by dependency, not by appeal.

| Step | Requirement | Work | Closes | Evidence class | Approval |
|---|---|---|---|---|---|
| **1** | **A** | S1: an **active** rejected `value` fact leaves the document `needs_verification`, keyed on the declared-measurement condition — **not** on open-issue count, **not** on a superseded original | FC-2, narrow XO-3 only | scripted HTTP | **owner — NOT YET AUTHORIZED** (§8.1.6) |
| **2** | **C** | Document the destroyed-`Value:`-label case (FC-5) as an **honest limitation**, with no claim of detection | FC-5 (as limitation) | analysis | owner (status wording) |
| **3** | **A** | FC-4: zero-fact documents surface an explicit, reviewable failure rather than an empty issue list | FC-4 | scripted HTTP | owner (triage governance) |
| **4** | **B (partial)** | P-c: correct `EXTRACTION_PROVENANCE.md` / US-09 to "spans resolve at intake only" | doc truth | docs | none |
| **5** | **B** | P-a: `text_char_count` on the attempt summary | reviewability floor | wire change | **owner** |
| **6** | **B** | P-b: persisted page text + `GET /{id}/text` + retention position — **three separate decisions** | source comparison | real review capability | **owner: table + endpoint + retention** |
| **7** | **B** | FC-3: require source comparison before a `doctor_verified` Observation from an OCR-derived fact | FC-3 | scripted HTTP | owner |
| **8** | — | Re-run the owner Windows A/B with **unchanged** configuration at the new SHA to re-establish the G1/RF baseline | G1 baseline | real engine | owner |
| **9** | — | *Only after 7*: revisit O4/O6 | SFE improvement without regression | real engine + scripted | owner |

Rationale: **steps 1–3 make the pipeline honest, steps 4–7 make it reviewable, and only
then can a configuration change be judged.** Doing 8–9 first would put a better-looking
extraction in front of a review surface that still cannot show the doctor what the engine
read.

Steps 2 needs no migration; step 1 needs none under S1 or S4, and one under S2. Step 1 alone
is the smallest bounded increment, specified in §8.1.

### 8.1 The S1 acceptance specification

**This is a specification only. No production change is implemented, authorized or
started.** §8.1 states exactly what the narrow S1 predicate must do, what it must not do,
and what evidence would show it works. It supersedes revision 2's §8.1, whose test matrix
contained three errors identified in review
[`5916921991`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916921991)
and corrected in §8.2.

#### 8.1.1 The predicate, stated narrowly

`_unread_measurement_blocks_verification()` already blocks when a `page_missing` value fact
exists with no verified numeric value. S1 adds **one** clause to that same predicate:

> the document is also blocked when there exists at least one **active** (non-superseded)
> `value` fact whose `verification_status == rejected` and no active verified `value` fact
> carries a `normalized_value`.

Everything else is unchanged. In particular:

| Untouched | Why |
|---|---|
| `quality.compute_drafts()` / `issues.collect_flag_issues()` | D-14 and the fixed VI-005 semantics stay byte-identical. **S1 emits no new issues and removes none.** |
| `VI-005` triggers (`unparseable_value`, `low_confidence`, `page_missing`) | A rejected *clean* value has no VI-005 trigger and S1 does not add one (§8.2.1) |
| API surface, request/response schemas, error codes, statuses | no contract change (§8.1.6) |
| `record_decision`, append-only lifecycle, 409 on re-decision | D-11 preserved |
| OCR configuration | not touched; `preserve_interword_spaces` stays off |

**Activeness is essential, and this is a measured trap.** After a correction, the original
`value` fact remains `rejected` **with `page_missing`** and a new `verified` value fact
exists beside it. Measured on the corrected-from-unread case:

```
report_date    verified  ["clean"]        active
value          rejected  ["page_missing"] SUPERSEDED
reference_text verified  ["clean"]        active
value          verified  ["clean"]        active

naive   "any rejected value fact"        -> True    # WRONG: blocks a valid correction
correct "any ACTIVE rejected value fact" -> False   # S1 must use this
```

A predicate written against all facts, rather than active ones, would regress the
correction path — the very path D-14 already handles correctly. S1 must reuse
`quality.superseded_fact_ids()` exactly as `_unread_measurement_blocks_verification()`
already does.

#### 8.1.2 The eight acceptance cases

Each case is one test. "RED" means it **must fail on `07442e7`** before the predicate
changes. Cases 4–8 are **guard tests**: they pass today and must still pass, proving S1
did not over-reach.

| # | Case | Setup | Required assertion | Today |
|---|---|---|---|---|
| **C1** | Plain rejected measurement, text-layer PDF | text PDF, reject `value`, verify the rest | `document_status != "verified"`; no Observation from that document | **RED** |
| **C2** | Plain rejected measurement, scripted OCR | scripted engine, case-B text (clean `105`), reject `value`, verify the rest | same as C1 | **RED** |
| **C3** | `VI-002` preserved under D-14 | C1/C2 state | `VI-002` present in `verification_issues`, `state == open`, `reason_code == fact_unverified`; **open-issue set identical to today's** | **GREEN — must stay green** |
| **C4** | No false `verified` in covered cases | C1/C2 | the specific contradiction (`verified` + open `VI-002`) is unreachable **for a rejected active `value` fact** | **RED** |
| **C5** | Zero Observations from rejected measurements | C1/C2 | `source_fact_id`-bearing Observation count for the document is 0; document-derived total unchanged | **GREEN** |
| **C6** | Valid correction still works, lineage intact | correct a `value` (both a clean value and a `page_missing` value), verify the rest | status `verified`; `corrected_from_fact_id` lineage present; original row retained `rejected`; `VI-002`/`VI-005` **`resolved`** | **GREEN** |
| **C7** | Document-only reports unaffected | report with `report_date` + `reference_text`, **no `value` fact**; verify both | predicate does not fire; status `verified`; `VI-002` `resolved` | **GREEN** |
| **C8** | Identity-blocker precedence and contract preserved | document with unresolved identity (`VI-004`) | `409 E_VI_004_UNRESOLVED` still raised **before** any decision is recorded; S1 does not mask or reorder it | **GREEN** |

Measured baselines for C5–C8 on `07442e7`, so the guard tests have a known reference:

* C6 corrected-from-unread → `verified`, issues `VI-002 resolved`, `VI-005 resolved`, 0 document Observations.
* C6 corrected-from-clean → `verified`, `VI-002 resolved`, 0 document Observations.
* C7 document-only → `verified`, `VI-002 resolved`, predicate false.
* C1/C2 today → `verified` with `VI-002` **open** (the defect C4 targets).

#### 8.1.3 What S1 explicitly does **not** claim

Revision 2 overstated three things. Each is now a bound on the claim, not a goal:

1. **S1 does not produce `VI-005` for a rejected clean value, and must not.** `VI-005` fires
   only from `unparseable_value`, `low_confidence` or `page_missing`. A plain rejection of a
   *clean* value has no trigger. C3 asserts **`VI-002` open, unchanged** — it does **not**
   assert `VI-005`. Adding a VI-005 trigger for clean rejections would be a **separate
   VI-005 policy change requiring its own owner approval**; it is not in S1 and is not
   proposed here.
2. **S1 is not a system-wide `verified`/issue invariant.** S1 blocks exactly one condition:
   an active rejected `value` fact. A text-layer PDF where the doctor rejects
   `reference_text` and verifies everything else **still** reaches `verified` with `VI-002`
   open — measured in §1.2. That counterexample remains, deliberately. General
   document/issue harmonization is **R20-D2**, a separately governed redesign. C4 is
   scoped to the rejected-measurement case only, and no test may be written as "for every
   document, `verified` implies no open issue".
3. **S1 does not block the corrected-from-unread path and does not close XO-3.** A doctor
   correcting an unread `page_missing` value creates a **new verified numeric** fact; the
   original is superseded and R17 excludes it, so status legitimately becomes `verified`
   with a mapped Observation. This is by design (the correction path is the *only* clean
   route out of an unread measurement) and it remains doctor-attributable. Whether such a
   corrected value needs source review is **requirement B**, not S1. XO-3 stays **FAIL**
   until B lands.

**The single-sentence scope:** *S1 prevents a document from becoming `verified` while a
doctor has rejected its measurement and no verified replacement exists — and nothing more.*

#### 8.1.4 Interaction with the permanently-open `VI-002`

S1 keeps the document in `needs_verification` after a plain rejection. Because D-11 makes
re-decision return **409 `E_FACT_ALREADY_DECIDED`**, that document cannot be cleared by
retrying the rejected fact. S1 therefore **must not** be paired with a "verify again" prompt
or any affordance implying the doctor can resolve it: the only forward actions are a
**correction** of the value (creates a verified replacement, clears the block) or leaving
the document in review. The UI/API must not misrepresent this. Making a plain rejection
clearable is **S2/S4 territory** (typed reason / explicit acknowledgement) and is out of
scope.

#### 8.1.5 Tests described, not written

Per this round's boundary, tests are **specified here and not added to
`backend/tests/p3/`**. Writing them is production-test code. Known test-suite couplings the
implementing change must handle:

* `test_p3_r09_plain_rejection_still_counts_for_vi_002` (`test_p3_edge_cases.py`) already
  asserts `VI-002` survives a plain rejection. **C3 duplicates its intent from the status
  side** — the implementing change should extend rather than duplicate, and must not alter
  that test's assertion.
* `test_all_facts_verified_promotes_the_document` and
  `test_document_with_every_fact_rejected_fails` (`test_p3_verification.py`) assert
  `verified` on the all-verified path and `failed` on the all-rejected path. **Neither path
  has an active rejected `value` beside a verified one**, so S1 must leave both green; if
  either turns red the predicate is too broad.
* Adding tests drifts
  `test_handoff_test_count_matches_the_suite_it_describes`, so
  `PHASE_3_WINDOWS_ACCEPTANCE.md` counts must be updated in the same change.

#### 8.1.6 Exact owner authorization required

S1 is **not authorized**. Revision 2's §9 entry "Adopted: S1 interim" overstated a
recommendation as a decision, and that wording is corrected in §9. Implementation requires
an explicit owner authorization of this scope, stated as all of:

| Requirement | Authorization needed |
|---|---|
| A1 | Change **one predicate** in `verification.py` (`_unread_measurement_blocks_verification` or a sibling), keyed on **active** rejected `value` facts — no other production change |
| A2 | Accept that a document with a plain-rejected measurement stays in `needs_verification`, including for the doctor who deliberately rejected a spurious value |
| A3 | Accept that the stranded `VI-002` remains open and unclearable, with **no** "verify again" affordance, and that clearing requires a correction |
| A4 | Accept that general non-measurement rejection (`reference_text` → `verified` + open `VI-002`) **remains** as R20-D2 |
| A5 | Accept that corrected-from-unread still reaches `verified` with an Observation, and XO-3 stays FAIL pending requirement B |
| A6 | Approve the C1–C8 test set as the acceptance criteria, with C1/C2/C4 red and C3/C5–C8 green |
| A7 | Confirm **no** VI-005 policy change for clean rejections (that would be a separate approval) |

#### 8.1.7 Gaps that remain outside S1

Stated explicitly so no reader mistakes S1 for a general fix:

| Gap | Status after S1 | Governed by |
|---|---|---|
| Rejection of **non-measurement** facts (`reference_text`, `unit`, `test_name`) | **unchanged** — can still yield `verified` + open `VI-002` | R20-D2 |
| Permanently open, unclearable `VI-002` after a plain rejection | **unchanged** (S1 makes it honest, not clearable) | S2/S4, later design |
| False-clean OCR approval reaching `doctor_verified` | **unchanged**; S1 never fires because the doctor rejects nothing | requirement B |
| Durable OCR page text / scoped read endpoint / retention | **unchanged**; three separate decisions | R20-D5, R20-D6 |
| Zero-fact documents (`verification_issues: []`) | **unchanged** | step 3 / R20-D4 |
| Destroyed `Value:` label | **unchanged**; documented limitation | R20-D3 / requirement C |
| General `verified`/issue consistency across all fact types | **unchanged** | R20-D2 |

### 8.2 What revision 2 of this section got wrong

Recorded so the correction is auditable:

1. **A-3 demanded `VI-005` for a rejected clean value.** No code path produces it and
   §8.1 forbids touching the issue emitters, so the test was unsatisfiable by design.
   Replacement **C3** asserts `VI-002` open and the open-issue set unchanged.
2. **A-6 claimed a system-wide invariant** that the report's own §1.2 counterexample
   disproves. Replacement **C4** is scoped to rejected active `value` facts.
3. **XO-3 was described as closed by step 1.** It is not: correction creates a verified
   replacement and supersedes the original, so the corrected-from-unread path legitimately
   reaches `verified`. Correction of that claim is in §5 (XO-3 note) and §8.1.3.
4. **§9 said S1 was "adopted".** It was a recommendation. §9 now records it as
   **recommended, awaiting explicit scope authorization** per §8.1.6.

---
## 9. Owner decisions requested

I am not implementing any of these. Each is a genuine choice I should not make for you.

| # | Decision | Options | Status |
|---|---|---|---|
| **R20-D1** | State model for a rejected/unread declared measurement | **S1** (rejection keeps doc blocked; may over-block) / **S2** (typed rejection reason; needs migration) / **S4** (explicit "no measurement" acknowledgement; needs API) | **Recommended: S1 interim — NOT authorized.** Requires explicit scope approval per §8.1.6 (A1–A7). S2/S4 remain available later |
| **R20-D1b** | Approve the narrow S1 scope as specified in §8.1 | **A1–A7** as listed in §8.1.6 | **open — this is the blocking decision for the next increment** |
| **R20-D2** | May a document reach `verified` while a blocking issue is open **for non-measurement facts**? | currently yes (`reference_text`, §1.2) — general harmonization | open — **deliberately outside S1** (§8.1.7) |
| **R20-D3** | Is a destroyed-`Value:`-label document (FC-5) required to block, or accepted as document-only with the limitation documented? | recommend **documented limitation**, since it is undetectable deterministically | open |
| **R20-D4** | Zero-fact documents (FC-4): reviewable blocker, or `failed` is sufficient? | needs triage governance | open |
| **R20-D5** | P2 minimum: **P-a** (char count only), **P-b** (text + endpoint), or **P-c** (docs correction only) for P3? | recommend **P-c now, P-a next, P-b when retention is decided** | open |
| **R20-D6** | Retention position for persisted page text if P-b is approved | persist with document / purge on verification / do not persist | open — **separate** from D5 |
| **R20-D7** | Is `preserve_interword_spaces=1` permitted at all in P3? | recommend **not in P3**; revisitable only after requirement B | open |

**D7 note:** revision 1 framed this as "after FC-3 is green". That framing was wrong —
FC-3 is only closed by requirement B (source comparison), so the correct precondition is
B, not a flag. Until B exists there is no configuration argument that makes the substitution
detectable, and the recommendation is to leave the option off. **S1 is not a precondition for
D7 either**: S1 never fires on the false-clean case, so enabling the option after S1 would
still be unsafe.

**D1 note:** "recommended" is not "decided". Review `5916921991` correctly observed that
prior discussion favored S1 as a recommendation for interim fail-closed protection, never an
approval to implement. §8.1.6 lists the exact scope that must be granted before any
production code is written.

---

## 10. Residual risks, stated

1. **A false-clean OCR read is indistinguishable from a correct one at parsed-text level.**
   Requirement C. No configuration tested removes this, and §2 shows it can reach a
   `doctor_verified` Observation. Neither S1 nor any issue-emission change addresses it;
   only requirement B (source comparison) plus a doctor who actually looks does, and even
   then a doctor who does not look will approve a wrong value. **That is a residual
   human-review risk, not a solved problem, and it must be carried as such into any
   acceptance decision.**
2. **A destroyed `Value:` label is undetectable.** Requirement C. A document whose value
   line vanished entirely can reach `verified` on its date alone with zero observations
   (§ measured). This is an honest limitation of deterministic parsing, not a bug this
   increment fixes, and it is **not** to be recorded as solved by S1 or by FC-3.
3. **`GOLD-EX-11` remains FAIL / NOT PROVEN.** Enabling O2 would not fix it (the engine
   still substitutes), and forcing it green would be exactly the engineering the owner has
   consistently refused. It is **not** reclassified as a nonblocking measurement by this
   report; that would require an explicit owner decision this round did not receive.
4. **No option here makes OCR accurate.** None of RF-1/RF-2 are claimed as results. Clean
   positive field extraction (G2/`SFE`), OCR recognition fidelity (G1/`OCR-RF`), fail-closed
   workflow behaviour (G3/`FC`) and doctor-verified observations (G4/`XO`) remain **four
   separate properties**; progress on one is never evidence for another.
5. **Over-blocking is a real cost of S1.** Documents whose value a doctor deliberately
   rejects will stay in review, with an open `VI-002` that **no action clears** (409 on
   retry) — only a correction clears it. This is accepted deliberately as the fail-closed
   direction, must not be papered over with a "verify again" affordance (§8.1.4), and
   should be revisited only with data from use or via S2/S4.
6. **The append-only contract leaves a stranded `VI-002`.** A plain rejection cannot be
   revised (409 `E_FACT_ALREADY_DECIDED`), so `VI-002` remains open with no clearing action.
   S1 makes this honest by keeping the document in review; it does not make the issue
   clearable. A typed rejection-reason design (S2) or a superseding correction (existing)
   are the only routes, and both are out of scope here.

---

## 11. What this round did and did not do

**Did:** replaced §8.1 with a scoped S1 acceptance specification (C1–C8) that matches a
one-predicate implementation; removed the unsatisfiable `VI-005` demand; scoped the
invariant claim to rejected **measurement** facts; corrected the corrected-from-unread and
XO-3 overclaims; downgraded "adopted" to "recommended, not authorized"; listed the exact
owner authorization required (§8.1.6, A1–A7) and the gaps S1 leaves open (§8.1.7);
measured the corrected-from-unread supersession trap that a naive predicate would hit.

**Did not:** change production code, API, schema, migrations, UI or OCR configuration; touch
D-14, `VI-002` or the `VI-005` triggers; reclassify `GOLD-EX-11`; write the tests (specified
only); enable `preserve_interword_spaces=1`; persist OCR page text; add an endpoint; decide
retention; authorize S1.

**Next step requires the owner:** grant or decline A1–A7 (§8.1.6). No implementation begins
before that.

PR #10 remains **DRAFT**; P3 remains **IN_REVIEW**; `GOLD-EX-11` remains **FAIL / NOT
PROVEN**; no merge; P4/P5 not started.
