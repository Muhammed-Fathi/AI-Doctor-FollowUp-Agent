# P3-R20 — Engineering decision report: OCR configuration vs. false-clean extraction

**Status: ANALYSIS AND PLAN ONLY. No configuration, API, schema, migration or UI change is
proposed for implementation without the owner decision requested in §9.** PR #10 stays
DRAFT; P3 stays IN_REVIEW; `GOLD-EX-11` stays **FAIL / NOT PROVEN**; P4/P5 not started.

Base: `fdce02f7f5f743d4a0b77319729c060fe3685aa6`.
Owner evidence: review [`5916564273`](https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#pullrequestreview-5916564273)
(Windows 11, Tesseract `5.4.0.20240606`, Pillow 40 px fixture).

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

## 1. The finding my analysis had missed, and it changes the recommendation

The owner's framing — "neither weaker parser regex nor global B option alone is a safe
fix" — is right, and there is a second reason that is not about recognition at all.

**Escalation is not actually reachable in production today.** Measured (scripted HTTP,
`fdce02f`):

| Case | Doctor rejects the value with reason "image says 1O5", approves the rest | Document status | `VI-005` after |
|---|---|---|---|
| **A** (current prod, `page_missing`) | rejection leaves `VI-005` open | `needs_verification` | **open** |
| **B** (false-clean) | rejection closes everything | **`verified`** | absent |

Case A blocks correctly only because `page_missing` happens to be a *flag on the value
fact*, and a rejected fact keeps its flags. Case B has no flag to inherit. So the two
cases differ by **document status**, and the false-clean one produces the *better*
outcome — exactly inverted.

Worse, discovery happens in the wrong order:

* **Before** rejection, `VI-005` and `VI-002` are open, so nothing can be promoted and the
  status is not misleading.
* **After** a doctor rejects the wrong value and approves the remaining facts, the
  document becomes `verified` with `failure_code=None` and **no issue at all**. Measured.
* If the doctor instead **corrects** the value to a number, one whose correctness no
  actor can check, a `doctor_verified` glucose Observation is created (§2).

So the current design has a **discovery/state mismatch**: a rejected measurement leaves
the document looking healthy, and there is no first-class way to record "a measurement
was declared here and nobody ever read it."

That is the core defect this report has to solve, and it is a **state-model** problem,
not an OCR-configuration problem. No OCR setting can fix it: B makes recognition better
structured and simultaneously makes this worse.

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

The existing guards that do *not* help here, with reasons:

| Guard | Why it does not catch B |
|---|---|
| `looks_corrupted()` | scans a fact's `raw_text` for `O`/`l` next to digits. After substitution `raw_text='105'` — no `O` remains. Structurally blind. |
| `ocr_confidence_floor` (0.70) | owner's confidence 0.95; the engine is *confident* about the wrong answer |
| `page_missing` | only present when the value is **not** parsed. That is the A case only |
| `VI-002` | generic; identical for a correct document with pending facts |
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
| FC-2 | A **rejected** measurement leaves the document blocked, not `verified` | **FAIL** — measured `verified`, `failure_code=None`, no issue |
| FC-3 | A false-clean candidate cannot reach `verified` with **no** issue open | **FAIL** — B reaches `verified` with zero open issues |
| FC-4 | Zero-fact document surfaces a reviewable blocker | **FAIL** — `failed` + `verification_issues: []` |
| FC-5 | Destroyed `Value:` label cannot reach `verified` on a date alone | **FAIL** — measured `verified`, 0 observations |

FC-2…FC-5 are all reachable today and all independent of OCR configuration. **This is the
increment to approve first.**

### G4 — `XO` Explicitly doctor-verified observations *(scripted HTTP)*

| ID | Criterion | Today |
|---|---|---|
| XO-1 | No Observation is created without an explicit doctor decision | **PASS** |
| XO-2 | Every Observation carries `source_fact_id`, `doctor_verified`, `verified_by_user_id` | **PASS** |
| XO-3 | A `doctor_verified` Observation cannot be derived from a value the pipeline knows was unread or rejected | **FAIL** (FC-2/FC-3 path) |
| XO-4 | Correction is append-only with lineage, original excerpt preserved | **PASS** (R17/R18) |

---

## 6. Options

### 6.1 For the recognition/layout problem (§0, G1/G2)

| # | Option | Effect on G1/G2 | Effect on G3/G4 | Scope | Verdict |
|---|---|---|---|---|---|
| **O1** | Keep current config; improve nothing | A stays: 3 fields, `page_missing` | unchanged, fail-closed preserved | none | Safest, leaves SFE lossy |
| **O2** | Global `preserve_interword_spaces=1` | 5 fields on clean reports | **regresses FC-3**: false-clean with no issue | 1 line in `ocr.py` | **Reject.** Owner already ruled against; §1/§2 show why it is unsafe *without* FC-3 fixed |
| **O3** | Parser relaxation `\s{2,}`→`\s+` | 5 fields from collapsed text | **same false-clean regression**, and breaks the two-space column contract that distinguishes a lab row from prose | 1 line | **Reject** for the same reason |
| **O4** | Two-pass OCR: read with and without space preservation; parse the **intersection** | 5 fields when both agree | disagreement is itself a flag → no false-clean when passes differ | moderate, `ocr.py` + attempt model | **Most promising**, but needs G3 fixed to be safe |
| **O5** | Layout-independent parse: use `image_to_data` word boxes for column detection instead of whitespace | best structural result | none by itself | large, new parser path | Best long-term; not now |
| **O6** | Adopt O2/O3 **only behind** FC-3 | 5 fields | FC-3 must make a `clean` false-clean candidate still require human confirmation | small once FC-3 exists | **Sequenced option** — configuration becomes safe only *after* the gate |

**Key point:** O2/O3 are not unsafe because they are wrong about layout. They are unsafe
because **no gate currently notices a false-clean candidate**. Fix FC-3 and they become
defensible. Leave FC-3 broken and they are indefensible at any combination of settings.

### 6.2 For the state-model problem (§1, G3)

| # | Option | Fixes | Cost / risk |
|---|---|---|---|
| **S1** | Treat a rejected `value` fact as "measurement unresolved": keep the document `needs_verification`, reopen `VI-005` | FC-2, XO-3 | changes status semantics for *any* rejected value fact — including a doctor deliberately rejecting a value they consider spurious. **Needs owner ruling.** |
| **S2** | Record the reason for rejection as a typed code, and block on `reason ∈ {unreadable, ambiguous, ocr_doubt}` | FC-2 precisely, no over-blocking | new enum + `fact_verification` column → migration + contract change |
| **S3** | Give a false-clean candidate a flag at intake, e.g. `unverified_ocr`, when its value token came from a page whose sibling lines were collapsed | FC-3 without touching configuration | requires a deterministic detector — and there may not be one. **Unproven; needs investigation before it is promised** |
| **S4** | Make `verified` require ≥1 non-rejected `value` **or** an explicit "no measurement in this document" acknowledgement | FC-2, FC-3, FC-5 | new acknowledgement surface → API change |
| **S5** | Surface every document in a terminal state with zero open issues for review (fix zero-fact FC-4) | FC-4 | small; needs a governance decision on failed-document triage |

**S2 is the most precise** and the only one that does not over-block; it is also the most
expensive (schema). **S1 is cheapest** and over-blocks. **S3 is unproven.** S4 is cleanest
conceptually and largest.

### 6.3 For reviewability (§3, P2)

| # | Option | Gives doctor | Scope | Verdict |
|---|---|---|---|---|
| **P-a** | Add `text_char_count` to `ExtractionAttemptSummary` (already stored) | "91 chars read" — weak but real | wire change, no migration | cheapest useful step |
| **P-b** | Add `GET /{id}/text` + persisted page text | full comparison | table + endpoint + retention decision | the real fix; blocked on governance |
| **P-c** | Correct the documentation to say spans resolve at intake only | honest, no capability | docs only | should happen regardless |
| **P-d** | Show `extractor` more prominently / require acknowledgement before approving an OCR value | friction-based mitigation | API/UI change | weak; false confidence |

**P-c is unconditional.** P-a is the smallest honest step. P-b is required for the review
premise to hold.

---

## 7. Safeguards enforceable before and during verification

Ranked by what exists today versus what needs a decision.

| Stage | Safeguard | Status |
|---|---|---|
| Intake | `pending` on every fact; no auto-promotion | **existing, PASS** |
| Intake | explicit rejection / correction only, append-only | **existing, PASS** |
| Intake | `page_missing` for an unread declared measurement | **existing (A only)** |
| Intake | per-field correction validation (no `'   '`/`'abc'`) | **existing (R17)** |
| Intake | rejection leaves the measurement unresolved | **GAP — FC-2** |
| Intake | a false-clean candidate is never issue-free | **GAP — FC-3** |
| Review | doctor can read the OCR text | **GAP — P2** |
| Review | doctor is told OCR was the route in a way they must acknowledge | **GAP — optional** |
| Promotion | observation requires a doctor decision | **existing, PASS** |
| Promotion | observation blocked when a measurement is unresolved | **GAP — XO-3** |

The pattern is consistent: **everything before the doctor works; everything about giving
the doctor the evidence, and everything about the state after a rejection, does not.**

---

## 8. Proposed implementation sequence

Each step is independently reviewable and independently gated. **Nothing starts without
the decision in §9.**

| Step | Work | Closes | Evidence class | Approval |
|---|---|---|---|---|
| **1** | FC-2/FC-3 state model: a rejected/unread declared measurement keeps the document blocked, with a typed reason so a deliberate "spurious value" rejection is still expressible | FC-2, FC-3, XO-3 | scripted HTTP | **owner: S1/S2/S4 choice** |
| **2** | FC-5: destroyed-label documents cannot reach `verified` on a date alone | FC-5 | scripted HTTP | owner (status semantics) |
| **3** | FC-4: zero-fact documents surface a reviewable blocker | FC-4 | scripted HTTP | owner (triage governance) |
| **4** | P-c: correct the "stored page text" documentation; state the limitation in the report | doc truth | docs | none |
| **5** | P-a: `text_char_count` on the attempt summary | reviewability floor | wire change | **owner** |
| **6** | P-b: persisted page text + `GET /{id}/text` + retention position | full comparison | real review capability | **owner: table + endpoint + retention** |
| **7** | Re-run the owner Windows A/B experiment with the **unchanged** configuration to establish RF baseline at the new SHA | G1 baseline | real engine | owner |
| **8** | *Only then*, evaluate O4/O6 with FC-3 in place | SFE improvement without regression | real engine + scripted | owner |

Rationale for the order: **steps 1–3 make the pipeline safe regardless of OCR
configuration**, which is the only ordering in which a later configuration change can be
judged. Doing 6–8 first would put a better-looking extraction in front of a review surface
that cannot show the doctor what the engine read.

Steps 1–3 need no migration if S1 or S4 is chosen; S2 needs one.

---

## 9. Owner decisions requested

I am not implementing any of these. Each is a genuine choice I should not make for you.

| # | Decision | Options |
|---|---|---|
| **R20-D1** | State model for a rejected/unread declared measurement | **S1** (rejection keeps doc blocked; may over-block) / **S2** (typed rejection reason; needs migration) / **S4** (explicit "no measurement" acknowledgement; needs API) |
| **R20-D2** | May a document reach `verified` with **zero** open issues while its measurement was never read? | currently yes for FC-2/FC-5 — recommend **no** |
| **R20-D3** | Is a destroyed-`Value:`-label document (FC-5) required to block, or accepted as document-only with the limitation documented? | recommend **documented limitation**, since it is undetectable deterministically |
| **R20-D4** | Zero-fact documents (FC-4): reviewable blocker, or `failed` is sufficient? | needs triage governance |
| **R20-D5** | P2 minimum: **P-a** (char count only), **P-b** (text + endpoint), or **P-c** (docs correction only) for P3? | recommend **P-c now, P-a next, P-b when retention is decided** |
| **R20-D6** | Retention position for persisted page text if P-b is approved | persist with document / purge on verification / do not persist |
| **R20-D7** | Is `preserve_interword_spaces=1` permitted **after** FC-3 is green (O6), or never in P3? | recommend **after**, with the A/B probe re-run in both modes |

---

## 10. Residual risks, stated

1. **A false-clean OCR read is indistinguishable from a correct one at parse time.** No
   configuration tested removes this; §2 shows it can reach a `doctor_verified`
   Observation. Only source comparison (P2) plus fail-closed state (steps 1–3) addresses
   it, and even then a doctor who does not look will approve a wrong value. **That is a
   human-factors limit, not a solved problem.**
2. **`GOLD-EX-11` remains FAIL / NOT PROVEN** and should stay that way. Enabling O2 would
   not fix it (the engine still substitutes), and forcing it green would be exactly the
   engineering the owner has consistently refused.
3. **No option here makes OCR accurate.** None of RF-1/RF-2 are claimed as results.
4. **S3 may be impossible.** I have no evidence a deterministic detector for "this page
   was collapsed" exists. It is listed to be investigated, not promised.
5. **Steps 6–8 are blocked on governance** (table, endpoint, retention), not on effort.
6. **Every number in this report was produced on `fdce02f` in this session** using scripted
   OCR text and the shipped parser; the real-engine facts are the owner's. Where I could
   not execute something, it is labelled, not estimated.
