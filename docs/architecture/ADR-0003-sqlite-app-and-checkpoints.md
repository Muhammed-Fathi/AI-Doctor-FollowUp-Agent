# ADR-0003 — SQLite for application data and LangGraph checkpoints

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Related | `REQ-DATA-03`, `REQ-GRAPH-02`, `REQ-OPS-01`, ADR-0001, ADR-0006 |

## Context

The orchestrator must persist state so a run survives a backend restart and so the doctor approval gate is durable. The app also needs users, patients, observations, documents, facts, review items, drafts, decisions, tasks, and audit events. The demo is a single-machine, single-user-at-a-time educational deployment.

## Decision

1. Application data: SQLite via SQLAlchemy 2.x with Alembic migrations, stored in a gitignored runtime directory.
2. Workflow state: LangGraph's SQLite checkpointer (`langgraph-checkpoint-sqlite`) in a separate gitignored SQLite file, so workflow durability does not depend on application migration history.
3. Both files live under an ignored runtime path; the database is recreated from deterministic seed scripts, never committed.
4. Timestamps are stored in UTC ISO-8601; identifiers are UUIDs; JSON columns are used only for bounded, versioned structures.

## Consequences

Positive:
- Zero-install, zero-cost, file-copyable database; ideal for a laptop demo and for resetting between stories.
- Real durable state rather than in-memory graphs — required to demonstrate genuine interrupt/resume.
- Easy reviewer inspection with any SQLite browser, without exposing real data (everything is synthetic).

Negative / accepted costs:
- WAL mode and single-writer limits: concurrent writers can raise `database is locked`; mitigated by short transactions, bounded retries, and the explicit single-user assumption (`ASM-06`).
- No row-level security: authorization must be enforced in the service layer and tested negatively (`REQ-SEC-01`).
- Two SQLite files must stay consistent on reset; the reset routine will delete/rebuild both.
- Not suitable for production or multiuser deployment — documented limitation, not a hidden risk.

## Alternatives rejected

| Alternative | Reason |
|---|---|
| PostgreSQL | Requires a server install/containers; no demo benefit; heavier setup for the owner |
| In-memory LangGraph `MemorySaver` | Loses the approval gate on restart; fails `REQ-GRAPH-02` |
| JSON files as the store | No transactions, no indexes, no referential integrity, race-prone |
| Cloud-managed DB | Violates local-only and privacy constraints |

## Verification (P0, docs-only)

- Data dictionary (`docs/contracts/DATA_DICTIONARY.md`) defines the tables, keys and indexes needed, including the unique idempotency index.
- Restart/resume acceptance criteria are written as testable items in `docs/contracts/STATE_AND_GRAPH_CONTRACT.md` §6 and `docs/evaluation/EVALUATION_MATRIX.md`.
- **Not executed:** no schema created, no migration run, no restart test performed. Scheduled P2 (schema) and P5/P7 (resume).

## Review notes for owner

Confirm that a disposable local SQLite database plus deterministic seed/reset is acceptable, and that resetting between demo stories is desired.
