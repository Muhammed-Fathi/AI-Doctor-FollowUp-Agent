# Demo Scenarios — Three Synthetic Stories

| Field | Value |
|---|---|
| Document ID | `DEMO-001` |
| Version | `0.3.0-p0` |
| Status | **IN REVIEW — script for a feature that does not exist yet** |
| Phase | `P0` (design). Executable: P8 |
| Related | `docs/evaluation/GOLD_FIXTURES.md`, `docs/clinical-safety/DEMO_REVIEW_RULES.md`, `REQ-OPS-01`, `REQ-DATA-04`, `REQ-OPS-04` |
| Revision | 0.2.0: corrected Case B delta (12 mmHg, most recent prior), Case C date/chronology and pre-verification display, explicit self-reported labels, injected demo clock, and an optional agentic-path segment (PR #2 review) |

> **Every patient, value, report, and date below is invented.** The demo runs on a local machine with
> synthetic fixtures only, and is labelled `EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE`
> on every screen. Nothing here is medical advice.

---

## 1. Shared preconditions

| Item | Requirement |
|---|---|
| Environment | Local laptop, repository checkout, synthetic seed, `DEMO_MODE=true` |
| Accounts | `demo_doctor` (role doctor) and one patient account per case; seeded locally, never real credentials |
| Start | One documented command (created in P1/P8) or `start.ps1`; `GET /health` checked first |
| Reset | `POST /api/v1/demo/reset` (or the documented script) before each story, refused while a run is active |
| Model | Optional. If Ollama is absent, every draft is labelled `deterministic_fallback` and the banner is shown — this is a supported path, not a failure |
| Network | Not required at demo time |
| Data | Cases A, B, C only (`docs/evaluation/GOLD_FIXTURES.md`) |
| Clock | Rules use the injected `demo_as_of_utc = 2026-11-14T12:00:00Z`, shown in the run header; the demo never depends on the laptop date (`REQ-OPS-04`) |

## 2. Pre-demo checklist (5 items, ~2 minutes)

1. `GET /health` → `status: ok`; note `ollama: ok|unavailable`, `tesseract: ok|unavailable`.
2. Login as doctor; confirm exactly three synthetic patients appear.
3. Confirm the disclaimer banner is visible in the UI shell.
4. Reset demo data; confirm the reset response lists A/B/C and reports `as_of_utc`.
4a. Confirm the UI shows the provenance legend: `self-reported` vs `doctor-verified`.
5. Decide the drafting mode (model or fallback) and say it out loud before starting — honesty over polish.

## 3. Scenario A — stable follow-up (the "nothing changed" baseline)

| Step | Actor | Action | Expected on screen |
|---|---|---|---|
| A1 | Patient | Submit check-in: systolic `121 mmHg`, diastolic `78 mmHg`, HR `71 bpm`, `measured_at 2026-11-01T09:00:00Z` (seed holds only Oct 1 and Oct 15, so this is not a duplicate) | Success confirmation; patient sees **no** interpretation; the value is labelled `self-reported` |
| A2 | Patient | Upload `REPORT-A-01.pdf` (clean text PDF: hemoglobin 13.4 g/dL, reference range 12.0–15.5 g/dL, report date 2026-10-20) | Status `received → processing`; no values interpreted for the patient |
| A3 | Doctor | Open patient A → extraction view | 5 declared fields (including `reference_text`) with page/span provenance; quality `clean`; status `pending`; the verification panel is empty once they are verified |
| A4 | Doctor | Verify all facts | Document becomes `verified`; audit entries appear |
| A5 | Doctor | Start follow-up workflow (after A1) | Trace shows nodes; **no verification issues, no review items**; draft contains only cited claims; hemoglobin is cited as a doctor-verified fact but creates no measurement comparison |
| A6 | Doctor | Approve the draft unchanged | Exactly one task + one in-app notification; run `completed` |
| A7 | Doctor | Refresh; open task list and audit | Task persists; audit shows verification, run, approval, task |

Narration lock (say this, not more): "These are synthetic numbers the patient reported themselves. The summary restates recorded values, marks which ones are self-reported versus verified from the report, and links each statement to its source. I decide whether anything needs doing — the tool only organizes the evidence."

Do **not** say: "the patient is stable", "normal readings", "no concerns", or call a check-in "verified".

## 4. Scenario B — changed measurements (the review-queue story)

| Step | Actor | Action | Expected on screen |
|---|---|---|---|
| B1 | — | Seeded history: `138/88` (2026-10-02), `146/92` (2026-10-20), `158/96` (2026-11-03), HR `76→80→84`, glucose `98 mg/dL` (2026-10-02) | Timeline shows each point with its source and `self-reported` label |
| B2 | Doctor | Open patient B → timeline | Current vs **most recent prior** values and the arithmetic difference are visible (146 → 158 = 12) |
| B3 | Doctor | Start workflow | Exactly one review item: `DR-005`, message `Systolic BP differs from the previous recorded value by 12 mmHg (self-reported).`, evidence = the 2026-10-20 and 2026-11-03 systolic observations; header says `DEMO review prompts — not clinical risk assessment` |
| B4 | Doctor | Open the item's evidence | The two source observations are shown side by side, both labelled self-reported |
| B5 | Doctor | Read the draft | Neutral, cited prose; no risk wording, no recommendation |
| B6 | Doctor | Edit one sentence and approve | `decision=edit`; edited text stored; one task created |
| B7 | Doctor | View audit | Rule evaluation recorded with `policy_version`; decision and task recorded |

Narration lock: "The rule compares the latest value with the most recent previous value using a fixed demo parameter, chosen only so this story produces one predictable prompt. It is not a clinical threshold and it is not a judgement about this patient."

Do **not** say: "the blood pressure is high", "worsening trend", "needs treatment", "should be referred".

## 5. Scenario C — ambiguous OCR (the uncertainty story)

| Step | Actor | Action | Expected on screen |
|---|---|---|---|
| C1 | Patient | Upload `REPORT-C-01.png` (synthetic scanned report: `Value: 1O5`, no unit, date `03/11/2026`) | Status `processing → needs_attention`; patient sees status only |
| C2 | Doctor | Open extraction view | Value raw `1O5` flagged `low_confidence`; unit missing `ambiguous_unit`; date `ambiguous_date`; all `pending`; **Verification required** panel lists `VI-001`, `VI-002`, `VI-003`, `VI-005` |
| C3 | Doctor | Attempt to start the workflow | Blocked: a run halted at `needs_verification` listing the 4 blocking verification issues (`VI-001/002/003/005`; `VI-002` interpolates `{count}` = the 3 candidate facts the page actually produced). No review items exist at this stage; the queue section is empty by design. No observation exists for the document until the correction is verified (`REQ-DATA-05`) |
| C4 | Doctor | Try to preview a draft anyway | No draft is produced from the unverified value; uncertainty is listed, not guessed |
| C5 | Doctor | Correct value → `105`, unit → `mg/dL`, date → `2026-11-03` (after the 2026-10-10 baseline); verify the other fields | New `doctor_verified` fact with `previous_value=1O5`; document becomes `verified`; audit keeps the correction |
| C6 | Doctor | Resume the workflow | Run continues; no `DR-005` (96 → 105 = 9 mg/dL ≤ demo parameter 40); draft cites the corrected value with its page/span and marks it doctor-verified |
| C7 | Doctor | Approve | One task; audit shows original → corrected value |

Narration lock: "The system refused to guess. It knew it could not read the value, told me, and stopped. After I fixed it, the correction is permanently visible in the audit."

Do **not** say: "the AI read the report", "OCR is accurate", "glucose is fine".

### 5.1 Optional agentic-path segment (C2a, demonstrates ADR-0006 depth)

| Step | Actor | Action | Expected on screen |
|---|---|---|---|
| C2a | Doctor | Open the run trace for the scanned report (`GOLD-EX-13` variant, **mocked extractor** so the demo and `AD-01` are deterministic) | The trace shows two typed `triage` entries: `path_selected=ocr_preprocess_retry, path_reason=low_confidence, attempt_index=1, preprocessing_applied=false`, then `path_selected=ocr_direct, path_reason=confidence_ok, attempt_index=2, preprocessing_applied=true` — or `flag_for_human, path_reason=retry_exhausted` in the failure variant. Narration: "the agent chose a different extraction path because its own first attempt reported low confidence; it stopped at a fixed retry budget" |

This segment is **optional** for the live demo and **required** in the P8 evidence pack (`AD-01`). It is the concrete
answer to "where is the decision-making?".

## 6. Cross-cutting demo rules

1. **Never** speak as if the software assessed the patient. Use "records", "flags for review", "links to source". Say "self-reported" for check-ins and "verified from the report" only for doctor-verified facts.
2. Show at least once: an evidence reference resolving to a page/span, and the fallback banner (if fallback is used).
3. Show at least once: the audit trail entry for the doctor's decision, and once: the as-of clock on the run header.
4. If a step fails live, say what failed and show the error code; do not improvise a narrative and do not edit data live to hide it.
5. Reset between stories so each begins from a known state; keep the reset output visible.
6. Keep the synthetic notice on screen in every screenshot used in the report/slides.

## 7. Timing budget (targets, not measured results)

| Segment | Target | Note |
|---|---|---|
| A (stable) | ~4–5 min | Mostly verification + approval |
| B (changed) | ~4–5 min | Includes evidence inspection and an edit |
| C (ambiguous OCR) | ~5–6 min | Includes correction + resume; +1 min if C2a is shown |
| Fallback-only variant of any story | ~3–4 min | No model latency |

Actual durations must be measured at P8 and recorded; if the model is slow, run the fallback and say so.

## 8. Failure playbook (honest handling)

| Failure | Response during demo |
|---|---|
| Ollama not running / model missing | Continue in fallback; point at the visible banner; explain the provenance design |
| Tesseract missing | Case C cannot be demonstrated; show the fixture and the `E_DEPENDENCY_MISSING` design, and state that OCR was not shown |
| Backend restart needed | Use it as evidence: resume from the checkpoint, show exactly one task created |
| Duplicate click creates nothing | Explain the idempotency key and show the single task |
| Unexpected error | Read the error code, state the limitation, move on; never hide it |
| Laptop date differs from `demo_as_of_utc` | Expected: rules use the injected clock. Point at the run header instead of changing the system clock |

## 9. Evidence to capture for P8

Screenshots (with the synthetic notice visible) of: disclaimer banner, timeline comparison, review item with
evidence, draft with citations and provider metadata, fallback banner (if used), approval form, task list,
audit trail, and reset output. Record timings and machine model per `docs/evaluation/LOCAL_BENCHMARK_PLAN.md`.

## 10. Status

| Item | Status |
|---|---|
| Scenario design and expected outcomes | Complete for review in P0 |
| Any scenario executed | **No — no application exists in P0** |
| Screenshots | **None** |
| Timings | **Not measured** |
