# P3-G11 — Independent Source Review of W2-R3 and Windows Preflight Handoff

**Date:** 2026-11-18  
**Disposition:** **SOURCE REVIEW ACCEPTED FOR READ-ONLY OWNER WINDOWS PREFLIGHT; NOT REAL-OCR AUTHORIZATION OR P3 ACCEPTANCE.**  
**Implementing branch:** `arena/752cca1f-ai-doctor-followup-agent`.  
**Reviewed exact commit:** `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821` (parent `358f31df3b9d373566caa695b0cd930d138223da`).  
**Test provenance:** Arena-provided report `Pasted text(20261118-161956).txt`; independent reviewer read the corresponding commit, source and tests through authenticated GitHub, **did not independently run those tests and did not access owner's Windows laptop**.

## 1. GitHub and scope verification

Authenticated GitHub comparison confirms `358f31d..6e6fcdf` is **one ahead, zero behind**, changing **exactly three** paths:
- `scripts/python/windows_ocr_acceptance.py`
- `backend/tests/p3/test_windows_ocr_acceptance.py`
- `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md`

Entire `af2bfd2..6e6fcdf` is three linear commits and changes **exactly seven** owner-approved paths; `main`, PR #10 head `18a53b2...`, fixture source, manifest, `gate_ocr_corruption`, P1 acceptance contract, and nonallowed source files are not in this diff. `origin/arena/752cca1f-ai-doctor-followup-agent` equals `6e6fcdf` at review time. PR #10 and PR #11 remain OPEN/DRAFT, not merged.

## 2. W2-R3 source-level disposition

**ACCEPTED for the specific W2-R3 objection raised on previous review.** In `assess_w2`:
- The `candidate=None / preserved_1o5_refused` path now returns **FAIL** for missing `all_facts_pending`, `all_facts_tesseract`, or `all_facts_require_source`.
- The special `DERIVED` case requires independent unchanged `GOLD-EX-11=PASS`, genuine preserved/refused `1O5`, zero pre-review Observations, intact source/upload/page SHA and Tesseract provenance, `non_value_fact_count > 0`, and `report_date`, `test_name`, `unit` field presence. Missing siblings yield blocking `NOT RUN`, not `DERIVED` or `PASS`.
- Full test file includes parameterized eight negative controls and additional simulated-HTTP missing-sibling cases, with legitimate preserved/refused `1O5` still `DERIVED` (never an independent W2 PASS). The `GOLD-EX-11` literal gate remains untouched.
- W2-R2 pinned fixture SHA `0f8cae895dff04f3017b32d3e2d9b5e50e75c60f2498cb188991c749732c2492` and canonical-LF size 200 are unchanged.

**Scope of claim:** Static/code-level review confirms the intended guard branches and regression coverage. It does not prove all corner cases of clinical OCR handling, genuine source comprehension, or the runtime path under real Windows Tesseract.

## 3. Arena-reported tests, not independently rerun

- Focused RED before fix: `9 failed, 30 passed, 72 deselected`.
- Focused GREEN: `39 passed, 72 deselected`.
- Target W2 file: `111 passed`.
- P3 subset: `443 passed`; full backend: `837 passed`.
- Ruff lint and format PASS; OpenAPI PASS (17 paths, 18 operations, 43 schemas).
- **All above are under Linux Python 3.11.2** (per Arena), outside `pyproject.toml`'s supported `>=3.12,<3.13`. Owner Windows/Python 3.12 full tests, real Tesseract, PDFium, W1/W2 real-engine evidence: **NOT RUN**.

This review does not interpret Linux 3.11 GREEN as supported-platform acceptance.

## 4. Existing Windows handoff cautions / nonblocking documentation discrepancies

The checked-in `docs/phase-reports/PHASE_3_WINDOWS_ACCEPTANCE.md` is a **procedure**, not result, and has historically inherited stale stage labels (e.g. “Stage 6a” in the `$ApprovedSha` placeholder), plus a line broadly saying the probe exits 2 for *any* non-PASS status even though source explicitly permits `DERIVED` as nonblocking. **Operationally, the code determines status**, and `DERIVED` must not be counted as an independent PASS. The `GOLD-EX-11` explanation also contains historical prose suggesting a preserved `1O5` where the owner's previously captured actual real-engine read was the substituted `105`. These are **wording caveats to reconcile in a future authorized documentation cleanup**, not reason to change the gate or to relabel the historical failure.

When checking Windows, pin **exact commit `6e6fcdf02d39d3a97ca3221ef2cc84b2ba528821`**, **not** the older Stage 6a SHA, PR #10 branch, `main`, or moving branch tip. The expected backend counts at this commit are 837 (P3 443), to verify by actual Windows collection/tests.

## 5. Controlled next step — READ-ONLY WINDOWS PREFLIGHT ONLY

Before any Windows install, worktree operation or real OCR execution, the owner may run a simple **read-only** PowerShell 5.1 preflight in an existing console, capturing:
- `py -3.12 --version` (or explicit already installed Python 3.12 location); `git --version`; `node --version`.
- Real Tesseract `--version`, `--list-langs`, `eng.traineddata` presence.
- `git -C E:\DEPI\AI-Doctor-FollowUp-Agent rev-parse HEAD`, `status --porcelain`, `worktree list --porcelain`, and remote pinned branch SHA via `git ls-remote`, all **read-only**.
- SHA-256/length of protected main database, without modifying it.
- Presence/nonpresence of the candidate new detached worktree folder. Keep earlier `E:\DEPI\P3-Acceptance-af2bfd226cc5` and diagnostic folders untouched.

Compare actual read-only output to expected main HEAD `867ab122394ffcc14df099bc2c7a11bce3143d8f`, known prior protected DB digest `6728a3d4bdc69b88816dc89b14eadb66808da36efa9bdf0312a77bec9144029b`, and remote exact candidate SHA. If any changed/unexpected value, **STOP** and investigate; do not repair/reset/check out in place.

**The preflight is not approval for a new worktree, running `setup.ps1`, `test_all.ps1`, real `windows_ocr_acceptance.py` or canonical/holdout**. After independent review of preflight output, seek separate owner authorization for an isolated fresh detached acceptance worktree, and then another explicit approval for the specified Windows tests. The known historical `GOLD-EX-11` is still **FAIL / NOT PROVEN**; strict P1 remains release-blocking until actual evidence meets it, or a new policy is explicitly accepted (P2 currently DEFERRED).

**Release ledger:** `CODE REVIEW OF W2-R3 ACCEPTED / WINDOWS PREFLIGHT READY / WINDOWS TESTS NOT RUN / P3 IN_REVIEW / GOLD-EX-11 FAIL NOT PROVEN / NO PR MERGE OR PHASE PROMOTION`.

*Educational synthetic demo only. NOT FOR CLINICAL USE.*
