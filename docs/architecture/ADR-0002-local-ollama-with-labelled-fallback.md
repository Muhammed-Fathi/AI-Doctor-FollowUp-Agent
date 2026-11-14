# ADR-0002 — Local Ollama behind an adapter, with an explicitly labelled deterministic fallback

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Related | `REQ-LLM-01`, `REQ-LLM-02`, `REQ-LLM-03`, `REQ-LLM-04`, `ASM-02` |

## Context

The project requires a genuinely local model with no paid inference. Ollama provides a local HTTP API on loopback. Small local models can hallucinate, refuse, emit invalid JSON, time out, or be absent during a demo. The drafting step must never be the source of clinical facts and must never fabricate on failure.

## Decision

1. A single `LLMProvider` interface exposes one capability: produce a **grounded draft summary** from verified, evidence-linked input using a strict JSON schema.
2. `OllamaProvider` calls `http://127.0.0.1:11434` with a bounded prompt, schema-constrained output, request timeout, and one bounded retry on transport failure only.
3. `DeterministicFallbackProvider` renders a template from the same structured evidence with no model call. It is **always** labelled: `provider=deterministic_fallback`, `execution_status=fallback_no_model`, with a visible UI notice.
4. Provider, model name, prompt version, latency, and status are stored on the draft and returned by the API.
5. Model choice is deferred until the owner benchmarks candidates on the demo laptop. No version compatibility claim is made in P0.

## Consequences

Positive:
- Zero inference cost; works offline; demo cannot be blocked by a missing model.
- Factual content stays in deterministic code; the model only writes prose over supplied evidence.
- Honest provenance makes it impossible to mistake a template for AI output.

Negative / accepted costs:
- Two output paths to test (model and fallback) and both must satisfy citation rules.
- Small models may be slow on CPU; the demo must budget for latency or use the fallback deliberately.
- Model quality/version is environment-dependent, so the graduation evidence includes the owner's measured numbers, not promised numbers.

## Alternatives rejected

| Alternative | Reason |
|---|---|
| Hosted LLM API | Violates zero-paid-API and data-locality constraints |
| No LLM (template only) | Removes the required local-model integration and agentic drafting element |
| LLM as decision-maker for review flags | Forbidden by `docs/clinical-safety/CLINICAL_SAFETY.md` |
| Silent fallback (indistinguishable output) | Dishonest provenance; rejected outright |

## Verification (P0, docs-only)

- Interface, fallback labelling and failure semantics are specified in `docs/contracts/LLM_ADAPTER.md`.
- Benchmark plan (commands, metrics to capture) in `docs/evaluation/LOCAL_BENCHMARK_PLAN.md`.
- **Not executed:** no model call, download, latency measurement, or schema test was performed in P0. These are P5 activities and partly require the owner's laptop (`ASM-01`, `ASM-02`).

## Review notes for owner

Confirm: (a) fallback is acceptable for the live demo if the model is slow, (b) which model families are permitted, (c) the owner's laptop can host a 3B-class quantized model.
