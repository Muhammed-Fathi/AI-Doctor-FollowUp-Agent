# Local Runtime Benchmark Plan (Owner Windows Laptop)

| Field | Value |
|---|---|
| Document ID | `EVAL-BENCH-001` |
| Version | `0.3.0-p0` |
| Status | **IN REVIEW — protocol only. Nothing was measured, downloaded, or installed in Phase 0** |
| Phase | `P0` (plan). Execution: P5 (first measurement), P7/P8 (final, offline) |
| Related | `REQ-EVAL-03`, `REQ-LLM-03/04`, `REQ-OPS-04`, `ASM-01`, `ASM-02`, `docs/contracts/LLM_ADAPTER.md` |

> **No performance numbers are promised anywhere in this repository.** Any figure that appears later must
> come with: command, machine, model, and date. If the owner's laptop cannot run a model, the demo runs on
> the labelled deterministic fallback and the limitation is stated plainly.

## 1. Why benchmark at all

1. Choose a model that actually runs on the demo laptop (CPU-only vs GPU).
2. Decide whether the live demo can afford a model draft or should use the fallback deliberately.
3. Produce honest evidence for the defense: measured latency and memory, not marketing claims.
4. Confirm the offline path works before standing in front of judges.

## 2. Machine record sheet (fill in before any timing)

| Field | How to capture | Value |
|---|---|---|
| OS + build | `winver`, `Get-ComputerInfo` | _owner fills_ |
| CPU model, cores | `Get-CimInstance Win32_Processor` | _owner fills_ |
| RAM total | `Get-CimInstance Win32_ComputerSystem` | _owner fills_ |
| GPU + VRAM (if any) | Task Manager / `nvidia-smi` if present | _owner fills_ |
| Free disk before/after model pull | `Get-PSDrive` | _owner fills_ |
| Windows PowerShell version | `$PSVersionTable` | _owner fills_ |
| Python version | `python --version` | _owner fills_ |
| Node + npm versions | `node -v`, `npm -v` | _owner fills_ |
| Tesseract version + languages | `tesseract --version`, `tesseract --list-langs` | _owner fills_ |
| Poppler availability | `pdftoppm -v` | _owner fills_ |
| Ollama version | `ollama --version` | _owner fills_ |
| Model(s) pulled + size | `ollama list` | _owner fills_ |

## 3. Protocol

### 3.1 Environment

- Laptop on mains power, "Balanced" (or documented) power plan, no other heavy applications.
- Report whether a GPU is used by the model; never mix GPU and CPU results in one table.
- Record whether the model was already loaded (warm) or had to load (cold).

### 3.2 Model draft measurement

For each candidate model, 3 runs of the same gold Case B input (same prompt version):

1. Cold: stop the model server, then run once and record time-to-first-output and total.
2. Warm: run twice more; record total latency for each.
3. Record: total latency (ms), tokens/sec if the runtime reports it, prompt/response sizes, peak RSS of the model process, and any warnings.
4. Record the fallback latency for the same input (should be milliseconds) as the comparison baseline.

### 3.3 Full-pipeline measurement

**Record the injected clock.** Every run in this plan uses `demo_as_of_utc = 2026-11-14T12:00:00Z` from the
policy file, and the run header/API must show it. Timings and screenshots are only comparable if the clock is
pinned; the laptop's real date is irrelevant and must not be used for rule expectations (`REQ-OPS-04`).

| Step | What to time |
|---|---|
| Upload + extraction (text PDF) | API call duration, extraction attempts |
| Upload + extraction (scanned PNG) | API call duration, OCR path used |
| Workflow run to `awaiting_decision` (model on) | end-to-end |
| Workflow run to `awaiting_decision` (model off) | end-to-end with fallback |
| Approval resume | decision → task committed |
| Restart + resume | kill process, restart, resume, count tasks/audit rows (expect exactly one task; the task ID is derived from the stored decision) |
| Agentic path (`AD-01`) | **mocked-extractor contract run** (deterministic, no OCR binary): trace of a low-confidence scan showing two extraction attempts with typed `detail` payloads and the final path |
| Live OCR measurement (`OCR-LIVE-01`) | the same degraded scans through the installed Tesseract, twice (preprocessing off/on): engine-reported confidence per pass, characters recovered, wall time, `tesseract --version`, OS build. **These are recorded measurements, not pass/fail assertions** — a value that differs from the mocked fixture is data, not a failure |

### 3.4 Offline check

Disable network (or unplug), run Case A end-to-end, confirm:
frontend loads from the local build, API works, DB works, Tesseract works locally, and either the local model
works or the fallback is used with its banner visible.

## 4. Recording format

```text
Date: 2026-MM-DD            Machine: <CPU> / <RAM> / <GPU or none>
OS: <version>               Ollama: <version>        Model: <name:tag> (<size>)
Prompt version: draft-v1    Case: GOLD-B
Run 1 (cold): total 0000 ms, first-token 0000 ms, peak RSS 0000 MB
Run 2 (warm): total 0000 ms
Run 3 (warm): total 0000 ms
Fallback:     total 00 ms
Notes: <warnings, GPU offload, thermal throttling, etc.>
```

Store results in `docs/evaluation/` (a dedicated results file) and summarise them in the phase report.
Do not overwrite a previous measurement; append with a date.

## 5. Decision rules after measuring

| Observation | Decision |
|---|---|
| Median draft latency ≤ ~20 s and stable | Use the model in the live demo |
| Median > ~20 s or highly variable | Demo the fallback live; show one pre-recorded model run with its measured timing |
| Model cannot run at all | Fallback-only demo, documented as a limitation; ADR-0002 stays valid |
| GPU available and used | Record it explicitly; do not claim GPU performance on CPU machines |
| RAM pressure / disk full | Choose a smaller quantized model or drop to fallback |

These thresholds are user-experience choices for a demo, not clinical or benchmark standards.

## 6. Explicit constraints

- Do not download models as part of Pull Request automation or CI.
- Do not commit weights, caches, or large logs.
- Do not publish a number obtained on a different machine as if it were the owner's laptop.
- Do not present a single warm run as a representative measurement.
- Do not omit a failed measurement.

## 7. Phase 0 status

| Item | Status |
|---|---|
| Protocol written | Yes |
| Machine record sheet filled | **No — requires owner Windows laptop** |
| Model downloaded | **No** |
| Any latency/memory figure measured | **No** |
| Injected `demo_as_of_utc` used in a real run | **No — no rules engine exists yet** |
| Offline end-to-end executed | **No — no code exists yet** |

`ollama` and `tesseract` are both absent from the Phase 0 authoring environment
(`which ollama` / `which tesseract` → not found), so no model or OCR measurement was possible here.
