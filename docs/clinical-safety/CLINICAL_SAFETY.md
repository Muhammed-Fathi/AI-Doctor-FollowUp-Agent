# Clinical Safety Boundaries and Wording Rules

| Field | Value |
|---|---|
| Document ID | `SAFE-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — wording requires owner (and clinician-adjacent reviewer if available) approval** |
| Phase | `P0`; enforced from P2 onward; tested at P7 |
| Related | `REQ-SEC-01..06`, `REQ-RULE-01..03`, `REQ-LLM-02`, ADR-0004, ADR-0005 |

> **EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.**
> This project is a university graduation prototype. It is not a medical device, has not been clinically
> evaluated, and must never be used to make decisions about a real person.

---

## 1. Purpose of this document

Define the safety boundary of the prototype in operational terms: what the software may do, what it must
never do, what it must display, and how those boundaries are verified. It is written so a reviewer can
check a PR against it without reading code.

## 2. The boundary in one paragraph

The system may store synthetic patient data, extract and display source-referenced values, compare values
to previous values, raise deterministic **"please look at this"** workflow items, and produce a draft prose
summary for a doctor. A human doctor must verify every extracted value before it is used and must explicitly
approve every follow-up action. The system never decides what is wrong with a patient, never recommends or
changes treatment, never contacts anyone, and never presents its output as medical advice.

## 3. Allowed vs prohibited behaviour

| Allowed (with evidence) | Prohibited (must fail review) |
|---|---|
| Store and display a value with its exact source location | Infer a value that is not printed in the source |
| State a numeric difference between two verified values | Declare the difference normal, abnormal, dangerous, or urgent |
| Emit a DEMO_ONLY review item asking the doctor to look | Assign a clinical risk level, score, triage category, or diagnosis |
| Draft neutral prose citing evidence | Recommend treatment, medication, dose, referral, or emergency action |
| List what is missing or uncertain | Impute, interpolate, or "fill in" a missing measurement |
| Summarize the patient's own quoted words | Paraphrase the patient into clinical findings |
| Route an unreadable field to human verification | Guess a unit, a date, or a decimal separator |
| Show the model's provider/status | Present fallback text as model output, or model text as verified fact |
| Create an in-app task after approval | Send SMS/email/WhatsApp/push or call an external API |
| Keep an audit trail of human decisions | Let the model or a background job approve anything |

## 4. Prohibited output content (checked mechanically)

A draft or task text fails validation if it contains advice/diagnosis patterns, including (non-exhaustive):

- second-person directives: "you should", "you must", "take", "stop taking", "increase", "reduce";
- diagnostic assertions: "diagnosis", "diagnosed with", "indicates", "confirms", "ruled out";
- risk/urgency assertions: "high risk", "low risk", "critical", "emergency", "urgent", "dangerous", "normal range";
- treatment artefacts: "prescription", "dose", "mg/kg", "therapy", "referral to";
- authority claims: "clinically validated", "medically accurate", "HIPAA compliant", "approved by".

A blocked draft is replaced by the deterministic fallback, and the event is audited. The pattern list is a
**best-effort guard**, not a proof of safety; the primary control is that the model never decides anything.

## 5. Required visible notices

| Location | Text |
|---|---|
| UI shell (all views) | `EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE` |
| Every draft summary (API field `disclaimer`) | same constant string |
| Fallback drafts | additional banner: `Template summary — local model not used` |
| Review queue header | `DEMO review prompts — not clinical risk assessment` |
| Fixture files | header comment: fictional, synthetic, no real patient data |
| README / demo docs | same notice plus the explicit non-goals |

The disclaimer is a typed constant (`Literal[...]`) so it cannot be omitted accidentally.

## 6. Human-in-the-loop invariants

| Invariant | Enforcement | Test |
|---|---|---|
| A doctor must verify a blocking extracted value before it is used | `fact_verify_gate` halts the graph; tool layer rejects unverified facts | `NEG-06`, `SAFE-02` |
| A doctor must approve a follow-up action before a task exists | Task requires `approval_decision_id`; unique per run | `SAFE-01`, `NEG-08` |
| Rejection creates nothing | `reject` routes to `completed` with no task | `SAFE-03` |
| The model cannot approve, verify, or create tasks | One tool with no side effects beyond a draft row | `SAFE-05` |
| The system cannot contact anyone | No transport code, dependency, or endpoint | `SEC-03` / `NEG-15` |
| Restart cannot duplicate actions | Idempotency keys + unique indexes | `NEG-07`, `NEG-09` |

## 7. Uncertainty and missing data

1. Missing data is displayed as missing — never as "normal" or zero.
2. An incomparable unit pair is reported as incomparable; no conversion is attempted (`mmol/L` glucose is rejected at intake).
3. Conflicting sources are both shown with their evidence; the system does not pick a winner.
4. Out-of-order or duplicate observations become data-quality prompts, not corrections.
5. Every draft carries `uncertainties` and `not_asserted` lists (possibly empty).

## 8. Privacy and data-handling boundary

- Synthetic, clearly fictional personas only; prefixes such as `DEMO-` on any reference; no real MRNs, names, phone numbers, or addresses.
- No network egress except the loopback model endpoint; uploads, DBs, checkpoints, and OCR temp files stay on the local disk and are gitignored.
- Logs contain IDs, codes, and durations — not document text, patient notes, or prompts with data.
- Audit records keep who did what and when, without clinical narrative.
- The demo reset destroys runtime data; no backup/restore claim is made.

## 9. Language rules for all project material

| Say | Do not say |
|---|---|
| "flags this for the doctor to review" | "detects a dangerous change" |
| "compares current and previous recorded values" | "monitors the patient's condition" |
| "DEMO rule with an arbitrary demo parameter" | "clinical threshold", "normal range", "guideline-based" |
| "draft summary for doctor review" | "AI diagnosis", "AI recommendation" |
| "has not been clinically validated" | "clinically safe", "medically accurate" |
| "synthetic demonstration data" | "anonymized patient data" |
| "not for clinical use" | "ready for hospital deployment" |

These substitutions are required in PR descriptions, slides, and the demo script — not only in code comments.

## 10. Incident and defect handling

1. Any discovered case where unverified data could influence a draft, rule, or task is a **safety defect**: stop, fix, add a regression test, and note it in the phase report.
2. Any accidental real-data upload during testing must be deleted immediately and reported; the repository must never contain it.
3. Any wording that implies clinical validity must be corrected in the same PR that introduced it.
4. A defect that cannot be fixed before the deadline is documented as a known limitation with the demo path that avoids it.

## 11. Verification status at P0

| Item | Status |
|---|---|
| Boundary documented and internally consistent with contracts | Design-reviewed in P0 |
| Prohibited-content filter | Not implemented (P5) |
| Human-in-the-loop enforcement | Not implemented (P5/P6) |
| Negative safety tests | Defined (`docs/evaluation/EVALUATION_MATRIX.md`), not executed |
| Wording audit of repository documents | Performed in P0 by the author (see phase report); owner review pending |
| Clinician-adjacent wording review | **Requires owner**; not performed |

## 12. Explicit non-claim

Completion of every test listed in this repository would still **not** establish clinical safety, diagnostic
accuracy, or regulatory compliance. Those require clinical validation, real-world data, and formal review
that are outside this project's scope and are not attempted here.
