# LLM Adapter Design — Local Ollama with an Honest Fallback

| Field | Value |
|---|---|
| Document ID | `CTR-LLM-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — design only; no model call has been made from this repository** |
| Phase | `P0` (design). Implementation and measurement: P5; hardening: P7 |
| Related | `REQ-LLM-01..04`, ADR-0002, `docs/evaluation/LOCAL_BENCHMARK_PLAN.md` |

> Nothing in this document claims a model works, is fast, or is installed. All performance statements are
> plans to be measured on the owner's laptop (`ASM-01`, `ASM-02`) and reported as measured or not measured.

---

## 1. Capability surface

The adapter exposes exactly one operation:

```python
# PROPOSAL ONLY
class DraftRequest(BaseModel):
    patient_alias: str                        # "Demo Patient B", never a real name
    verified_facts: list[VerifiedFact]        # <= 20, evidence-linked
    comparisons: list[ComparisonResult]       # <= 20
    review_flags: list[ReviewFlag]            # <= 20, DEMO_ONLY
    max_claims: int = 12
    tone: Literal["neutral_doctor_facing"] = "neutral_doctor_facing"

class DraftResult(BaseModel):
    provider: Literal["ollama", "deterministic_fallback"]
    model: str | None
    execution_status: Literal["model_ok", "model_invalid_schema", "model_timeout",
                              "model_unavailable", "fallback_no_model"]
    prompt_version: str
    latency_ms: int | None
    claims: list[ClaimCitation]
    uncertainties: list[str]
    not_asserted: list[str]
    disclaimer: Literal["EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"]

class LLMProvider(Protocol):
    name: Literal["ollama", "deterministic_fallback"]
    def draft(self, request: DraftRequest) -> DraftResult: ...
```

The adapter **cannot**: choose a patient, read database rows, verify facts, create review items, approve, write tasks, call HTTP beyond the configured loopback endpoint, execute code, or return free-form text without evidence.

## 2. Providers

### 2.1 `OllamaProvider`

| Aspect | Design |
|---|---|
| Endpoint | Configurable base URL, default `http://127.0.0.1:11434` (loopback only; a non-loopback host is refused at startup) |
| API | Local HTTP API of Ollama; the exact request shape and structured-output parameter must be re-verified against the official Ollama documentation at P5 before coding |
| Output contract | JSON matching the `DraftResult` claim schema; constrained decoding/structured output if supported by the chosen model, otherwise a strict parse + one repair attempt |
| Prompt | System message fixes the role ("assist a doctor, never advise a patient"), the evidence-only rule, and the refusal rule. Evidence is injected as a delimited untrusted-data block |
| Bounds | ≤ 1500 output tokens, request timeout default 45 s (configurable), one retry on transport error, one repair on schema violation |
| Temperature | Low/deterministic setting for reproducibility, recorded with the model metadata |
| Logging | Provider, model name, latency, status, prompt version, and claim counts only — never full prompts containing data or full responses with patient text |
| Failure mapping | Connection refused → `model_unavailable`; timeout → `model_timeout`; schema failure after repair → `model_invalid_schema`; any of these → fallback |

Model name is **observed from the running Ollama instance**, not hard-coded in docs. P0 does not name a model as verified; `MASTER_PLAN.md` lists candidates only.

### 2.2 `DeterministicFallbackProvider`

| Aspect | Design |
|---|---|
| Input | Same `DraftRequest` |
| Output | Deterministic template sentences built from verified facts/comparisons/review items, each with its evidence references |
| Label | `provider="deterministic_fallback"`, `execution_status="fallback_no_model"`, `model=null` |
| UI | A visible banner: "Template summary — local model not used" plus the educational notice |
| Guarantee | No sentence without evidence; no invented values; missing data stated as missing |
| Limitation | Robotic wording; no cross-sentence synthesis; cannot express nuance beyond the template |

The fallback is a **feature**, not a failure: it guarantees the demo can run offline and makes the model's contribution legible by contrast.

## 3. Prompting and grounding rules

1. **Evidence in, prose out.** The model receives only verified facts, comparisons, and rule items — never raw document text, never unverified values, never another patient's data.
2. **Citation obligation.** Every claim must reference at least one supplied evidence ID. Post-processing drops claims that reference unknown evidence IDs, and the count is recorded.
3. **No new numbers.** Any number in a claim must appear in the supplied evidence; a mismatch drops the claim.
4. **No advice, no diagnosis, no thresholds.** The prompt forbids recommendations, risk statements, and patient-directed language; a content filter rejects drafts containing prohibited patterns (e.g. "you should", "take", "diagnosis", "urgent", "dose").
5. **Uncertainty is explicit.** Missing baselines, pending facts, and incomparable units must appear in `uncertainties`/`not_asserted`, never be smoothed over.
6. **Untrusted data.** Document-derived strings are delimited and labelled as data. A detected instruction-like string is preserved verbatim in evidence but never executed (`REQ-SEC-02`).
7. **Deterministic validation before display.** A draft passes a validator (schema, citations, prohibited content, length) or it is replaced by the fallback.

## 4. Reproducibility and provenance

Recorded per draft: `provider`, `model`, `execution_status`, `prompt_version`, `latency_ms`, `temperature`/generation options, `claims_count`, `dropped_claim_count`. Stored in `summary_draft` + `model_metadata` and displayed in the doctor UI.

Not stored: full prompts, full raw model responses, API keys (none exist), or any patient text beyond the accepted claims.

## 5. Failure and degradation matrix

| Situation | Behaviour | User-visible |
|---|---|---|
| Ollama not installed | Fallback draft | Banner: model unavailable → template |
| Ollama installed, model missing | Fallback draft + audit note | Banner with the model name that was requested |
| Model returns invalid JSON | One repair attempt → fallback | `model_invalid_schema` |
| Model exceeds timeout | One retry with reduced budget → fallback | `model_timeout` |
| Model output cites unknown evidence | Claims dropped; if none remain → fallback | Dropped-claim note |
| Model emits prohibited advice | Draft rejected → fallback | Safety note, audited |
| Fallback explicitly disabled by config | `503 E_MODEL_UNAVAILABLE` | Clear error; no silent fabrication |

A workflow **never** completes with an unlabeled draft, and never fabricates content to fill a failed model call (`REQ-LLM-04`).

## 6. Benchmark plan (summary)

Full protocol: `docs/evaluation/LOCAL_BENCHMARK_PLAN.md`. In short, on the owner's Windows laptop:

1. Record machine facts (CPU, RAM, OS, optional GPU/VRAM) and Ollama version.
2. Record model pull size and disk usage.
3. Measure cold-load latency, warm first-token latency, total draft latency (3 runs, report min/median/max), tokens/second if reported, and peak RAM.
4. Repeat with the fallback enabled/disabled, and with the laptop offline.
5. Record actual values in `docs/evaluation/` and the phase report — never in advance.

**P0 status:** no model was downloaded, installed, or benchmarked. `ollama` is not present in the authoring environment; the benchmark is marked *requires owner Windows laptop*.

## 7. Open questions

| ID | Question | Default |
|---|---|---|
| `OQ-L01` | Which model family/size is permitted for the demo? | `MASTER_PLAN.md` candidates; final choice after benchmark |
| `OQ-L02` | Is a 45 s drafting budget acceptable on the demo laptop? | Yes, with the fallback available and a visible spinner |
| `OQ-L03` | Should the model be warmed at startup to hide cold-load? | Optional preflight warm-up at P5, reported honestly |
| `OQ-L04` | Is one repair attempt enough before falling back? | Yes; two attempts would double worst-case latency |
| `OQ-L05` | Should generated drafts be translatable to Arabic? | Out of MVP scope |
