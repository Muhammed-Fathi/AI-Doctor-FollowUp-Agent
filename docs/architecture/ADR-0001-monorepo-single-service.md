# ADR-0001 — Monorepo with one FastAPI service and one React app

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Deciders | Project owner (pending), Arena agent (author) |
| Related | `REQ-OPS-02`, ADR-0003, ADR-0006 |

## Context

A graduation project must be demonstrable on a single Windows laptop, reviewable by a supervisor, and explainable in a short defense. The system spans auth, patient data, OCR, a stateful agent graph, a local model, and two UI roles. Candidate structures: microservices, serverless, or a monorepo with one backend and one frontend.

## Decision

One repository, one deployable backend process (FastAPI + Uvicorn) and one frontend build (React + TypeScript + Vite), started by a single local script. Python domain modules are organized by responsibility (`api/`, `services/`, `agents/`, `llm/`, `db/`) but run in the same process. No message broker, container orchestration, or separate agent service.

## Consequences

Positive:
- One command starts the demo; one log stream; no cross-service auth or network failure modes.
- Agent nodes can share typed Python state and a single SQLite session in-process.
- Reviewer can audit the whole system from one `git clone` and one test command.

Negative / accepted costs:
- No horizontal scaling or independent deployment (explicitly out of scope).
- Imports can drift into cycles if layering rules are not enforced; mitigated by the layer table in `docs/architecture/ARCHITECTURE.md` §3 and Ruff import rules at P1/P7.
- A crash takes down API and workers together; mitigated by durable checkpoints (ADR-0003) and resume tests at P7.

## Alternatives rejected

| Alternative | Reason |
|---|---|
| Microservices for API / agents / OCR | Adds network, packaging, discovery, and failure surface with zero demo benefit |
| Serverless/cloud functions | Violates local-only, zero-paid-API constraint |
| Notebook-only prototype | No auth, no persistence, no audit — fails safety requirements |
| Separate agent service with its own queue | Unnecessary for one synchronous human-in-the-loop workflow |

## Verification (P0, docs-only)

- Documented layering is consistent with `docs/contracts/*` and the target layout in `MASTER_PLAN.md` §4.
- **Not executed:** any build, start, or import-boundary test (no code exists in P0). Enforced from P1 onward.

## Review notes for owner

Confirm the single-process model is acceptable for the defense demo, and that one React app with role-scoped routes is preferred over two separate frontends.
