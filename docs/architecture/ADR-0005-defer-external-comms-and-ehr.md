# ADR-0005 — Defer external communications and EHR/FHIR integration

| Field | Value |
|---|---|
| Status | **Proposed** (accepted only on owner approval of the P0 PR) |
| Date | 2026-11-14 |
| Phase | P0 |
| Related | `REQ-TASK-01/02`, `REQ-SEC-03`, ADR-0001 |

## Context

A realistic clinical assistant would message patients, sync with a hospital EHR, and import FHIR resources. Each of those creates real-world side effects, credential handling, privacy exposure, and integrations that cannot be built or honestly demonstrated within a local, synthetic, zero-cost graduation project. Messaging is also the most dangerous place for a mistaken AI action.

## Decision

1. The MVP has **no** outbound communication channel. Notifications and follow-up tasks are records in the local database, surfaced in-app.
2. Doctor-approved actions create in-app tasks only; there is no adapter, client, SDK, or TODO stub for SMS/email/WhatsApp/push/webhooks.
3. No EHR or FHIR integration is implemented or stubbed. The data model is intentionally simple and would need mapping work accepted as post-graduation design.
4. A repository-level test at P6/P7 asserts the absence of external-messaging dependencies and endpoints (`REQ-SEC-03`).
5. Any future extension must be a separate, owner-approved phase with explicit consent, audit, and delivery-verification design.

## Consequences

Positive:
- Removes the highest-consequence failure mode: the system cannot contact a real person.
- No secrets, no deliverability, no provider accounts, no privacy exposure during the demo.
- Simplifies the approval model: "approved" means "task recorded", not "message sent".

Negative / accepted costs:
- The demo is less "complete" as a product; the defense must explain why this boundary exists (it is a safety strength, not a missing feature).
- Reviewers may ask about NotificationService extensibility; the answer is deliberately "not in MVP".

## Alternatives rejected

| Alternative | Reason |
|---|---|
| Mock email/notification service that logs "sent" | Invites the impression of real delivery; still risks accidental real transmission |
| Real SMTP/SMS with test accounts | Cost, credentials, and a dangerous real side effect with synthetic personas |
| FHIR import from a public sandbox | Out of scope, large mapping surface, no demo value |
| Silent TODO stubs for messaging | Violates `AGENTS.md` §1 (no speculative future-phase code) |

## Verification (P0, docs-only)

- Absence is currently a documentation statement only. The enforcing negative test is defined in `docs/evaluation/EVALUATION_MATRIX.md` (`SEC-03`) and is **not executed** — scheduled P6/P7.
- Permission matrix in `docs/architecture/ARCHITECTURE.md` §6 denies external messaging to every role.

## Review notes for owner

Confirm in-app-only follow-up is sufficient for the graduation scope, and that no demo step requires sending anything to a phone or inbox.
