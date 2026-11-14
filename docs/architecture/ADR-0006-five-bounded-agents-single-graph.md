# ADR-0006 — Five bounded agent nodes inside one orchestrated graph

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Related | `REQ-GRAPH-01/05`, `REQ-LLM-01`, ADR-0001, ADR-0002 |

## Context

The graduation requirement speaks of a "multi-agent" system with five agents. A literal implementation as five autonomous LLM peers would multiply cost, latency, and unpredictability; it would also make the doctor gate, idempotency and audit nearly impossible to guarantee. The project must demonstrate genuine multi-agent orchestration, not just function chaining, while staying local, cheap and auditable.

## Decision

1. One LangGraph `StateGraph` with five **named, bounded agent nodes**: `medical_document`, `patient_monitoring`, `review_priority`, `doctor_communication`, `follow_up`.
2. Each node has: a single responsibility, an explicit tool allowlist, declared state reads/writes, and its own bounded retry policy.
3. Only `doctor_communication` may call the local model; the other four are deterministic Python. "Agent" here means *bounded autonomous component with a contract*, not *another LLM instance*.
4. Nodes communicate **only** through the typed shared state — no free-form agent-to-agent message passing, no shared mutable globals, no agent-created agents.
5. Authentic multi-agent behaviour is demonstrated by: conditional routing (e.g. halt on unverified facts), durable checkpoints, a human interrupt/resume before finalization, per-node traces, and bounded tool use — not by having several models talk.
6. The graph is versioned (`workflow_version`); changing nodes/edges requires a version bump and regression fixtures.

## Consequences

Positive:
- Deterministic, testable, cheap, fast, and offline-capable.
- Every transition is explainable in a defense; the trace reads like a workflow, not a chat log.
- The model's blast radius is one node with one tool.
- Idempotency, retries and approvals are enforceable because side effects live in one node.

Negative / accepted costs:
- Reviewers may challenge "is this really multi-agent?" — mitigated by the explicit trace, routing, interrupts, and per-node tool allowlists shown in the demo.
- Adding an LLM to a deterministic node later requires re-evaluating safety and cost.
- Shared-state schema evolution must be managed carefully (versioned state schema).

## Alternatives rejected

| Alternative | Reason |
|---|---|
| Five autonomous LLM agents with a conversation bus | Unbounded cost/latency, unverifiable, unsafe, hard to audit |
| AutoGen/CrewAI-style role chat | Same problems; approval guarantees harder |
| Plain sequential function calls with no graph | Loses checkpointing, interrupt/resume, and the required orchestration evidence |
| One mega-agent calling all tools | No separation of responsibility; a single prompt failure compromises everything |

## Verification (P0, docs-only)

- Node/tool/state permissions: `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §3 and `docs/contracts/TOOL_CONTRACTS.md`.
- Conditional routing and halt semantics: `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §4.
- **Not executed:** no graph compiled, no checkpoint written, no interrupt exercised. Scheduled P5; resume-after-restart evidence P7.

## Review notes for owner

Confirm the interpretation "five bounded agent components in one graph, only one of which uses an LLM" is acceptable for the assignment wording. This is the most important semantic decision in the baseline.
