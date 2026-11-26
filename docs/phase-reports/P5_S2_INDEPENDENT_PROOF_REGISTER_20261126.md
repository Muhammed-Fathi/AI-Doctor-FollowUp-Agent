# P5-S2 independent engineering proof register — 2026-11-26

ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.

Status: PROPOSED / IN_REVIEW. This is a parallel review work product, not a ratified
design, implementation authorization, or owner acceptance.

## 1. Baseline and work allocation

Reviewed base: `96589dd35df7e8b9ecc690f19f51105a570e1b69`.
Root tree: `c27ae9c1574b96b149db839abf5d5b4c430dd8a7`.
Merge parents (in order): `4e92abbde1ad1c3a8e77e0a741617c19c8133413`,
`1a53b4632efff4defdf63097e546b12dccdc93ee`.
PR #48 merged; owner acceptance comment #7186018816; post-merge CI run 45779348512
was previously independently verified successful at this base. Current main
and merge object identities re-read via GitHub on 2026-11-26.

Accepted collection pairing: backend 1526, P3 443, P5 286, P2 284.
Owner Windows evidence: 1522 success markers and 4 skip markers derived from
progress output; 13 Vitest tests; 12 mandatory gates passed, zero failed,
optional Playwright skipped. Skip identities not established by those markers.

The owner requested parallel work while Arena runs S2-A0. Allocation:

- Arena: isolated dependency resolution, package integrity, installation,
  packaging, upstream API and local graph probes. No tracked edits in A0.
- Reviewer: exact-source compatibility, invariant proof obligations, focused
  independent probes, schema and integration review. This document only.
- Owner: decisions, Windows evidence, acceptance and merge.

Keep Arena's accepted starting tree intact. Do not merge or cherry-pick this
review branch into its A0 session. Consolidate evidence after A0. A1 dependency
adoption and B/C/D implementation remain separately gated.

## 2. Stable finding register

IDs below supplement the R3 review, not replace or silently renumber owner
decisions. All source locations refer to the reviewed base, not moving main.

| ID | Finding | Disposition |
|---|---|---|
| S2-P01 | F1 blocker-count overflow: possible second-pass escape from first-pass cap | OPEN: service regression required |
| S2-P02 | Exact F1 call and typed receipt/DB binding | SOURCE VERIFIED; mapping proof pending |
| S2-P03 | N3 allowlist and F2-owned transaction; no per-call fingerprint in S1 result | OPEN: authority design required |
| S2-P04 | Lease scope cannot automatically fence independently committing services | OPEN: ownership design required |
| S2-P05 | Complete checkpoint carrier, scheduling and seal authority | OPEN: A0 API evidence prerequisite |
| S2-P06 | Audit companion semantic collision and actual adapter result | OPEN: schema/service proof required |
| S2-P07 | Packaging and dependency closure | Arena A0; no adoption yet |
| S2-P08 | Reset transaction and immutable-history contract | OPEN: source/transaction proof and owner decision |
| S2-P09 | Exact module scope and D-09 collection pairing | PRESERVE; no guard exception authorized |

## 3. S2-P01 — targeted F1 overflow investigation

Source: [p5_run_gate.py](../../backend/app/services/p5_run_gate.py),
lines 330–341, 421–434, 608–661, 736–744, 805–830, 887–925;
[models.py](../../backend/app/db/models.py), lines 911–945.

The first selected-document loop fetches at most MAX_GATE_FACTS + 1 facts,
adds their length to total_facts, and breaks when the cumulative count exceeds
40. Pending active facts and multi-measurement facts can contribute distinct
fact identities to recorded blockers. The later conflict-detection loop
iterates ALL doc_ids, independently fetches facts, and can add a VI-006
blocker with values[0].id. It does not use the first-loop total_facts cap.
Finally blocking_count is the distinct union of recorded fact IDs. Values
above 40 set unavailable="too_many_blocking_facts" but are not reset or
truncated. RunGateEvaluation receives the actual blocking_count; db.flush()
precedes the blocker and audit inserts. The model CHECK requires 0..40.

This is more specific than a generic count mismatch: a later selected document
can contribute a fact not processed before the first-loop break. Reachability
under the full F0/F1 fixture and admissibility constraints is NOT yet proven.

Independent disposable stdlib experiment executed by reviewer (SQLite 3.46.1):

    CREATE TABLE gate (n INTEGER NOT NULL CHECK(n BETWEEN 0 AND 40));
    INSERT INTO gate VALUES (40);
    INSERT INTO gate VALUES (41);

Observed: 40 committed; 41 raised
`IntegrityError: CHECK constraint failed: n BETWEEN 0 AND 40`.
After rollback the only stored row was (40,). This miniature constraint probe
is not an Alembic migration or an application service test.

### Required regression before selecting a fix

Use the real F0/F1 entry points, actual migrations, synthetic fixtures and
clean sessions. Existing helpers in
`backend/tests/p5/test_p5_run_gate.py` lines 76–186 and 363–387 demonstrate
document creation and same-day conflict fixtures. The existing _start helper
accepts one document; a new case must explicitly call create_run_foundation
with both selected IDs. Choose deterministic valid document IDs so the first
document sorts first. Do not alter accepted fixture semantics merely to force
reachability.

Candidate fixture (proposal, not executed):
1. First selected document has exactly 40 admissibly stored active fact IDs
   capable of producing recorded blockers, e.g. pending facts. Verify the
   first-pass recorded union actually contains 40; do not assume it.
2. A later selected document has a valid mapped test/date/value tuple with a
   distinct verified value fact and a synthetic conflicting stored observation,
   following the existing VI-006 fixture pattern. Its fact count makes the first
   pass break. Verify the second-pass conflict path can contribute its ID.
3. Invoke public evaluate_run_verification_gate in a fresh Session.
4. Inspect the actual result/exception, persisted evaluation and blocker rows,
   audit rows, and rollback. Test repeat invocation and unchanged manifest.
5. Also test exactly-at-boundary, overflow without second-pass conflict, and
   multiple blockers sharing one fact ID. Preserve document-level HALT with
   zero facts. No PROCEED on any incomplete snapshot.

If the candidate cannot be constructed with accepted invariants, record
why and reassess reachability. Do not label a hypothetical path a reproduced
application defect. If reproduced, owner must choose a bounded failure receipt
or an explicitly revised persistence contract. No arbitrary zeroing, truncation,
migration edit, or exception suppression. Test full receipt semantics and
idempotency for any authorized correction.

## 4. S2-P02/P03 — exact interface and evidence compatibility

- F1 public signature (p5_run_gate.py:887–894):
  evaluate_run_verification_gate(db, *, principal, run_id, validation_clock,
  upload_root). It acquires its own IMMEDIATE transaction and commits/rolls
  back (900–925); neither as_of_utc nor upload_dir is an accepted keyword.
- RunGateReceipt has no gate_evaluation_id. Resolve the persisted ID using
  run/version/fingerprint and compare semantic blocker tuples. RunGateBlocker
  does not store message; preserve fresh producer messages separately.
- S0 MAX_BLOCKING_FACTS is 40 (state.py:120). ComparisonResult.evidence DOES
  exist (974), whereas ComparisonV2 lacks it. The earlier contrary reviewer
  observation is withdrawn. S1 leaves that field empty.
- N0 = intake_validate; N8 = halted. MONITOR_COMPARE may call only
  READ_OBSERVATIONS and COMPARE_OBSERVATIONS (state.py:577–603).
  READ_VERIFIED_FACTS belongs to deferred nodes, not N3.
- F2 (p5_evidence_bridge.py:430–472) demands a clean session, owns BEGIN
  IMMEDIATE and rolls back in finally. Later ORM queries are separate
  transactions. EvaluableReviewEvidenceV2 lacks history_observations.
- F2 fingerprint payload (p5_evidence_bridge.py:350–404) includes projected
  current rows, comparison fields, exclusion IDs and reasons, etc.; it does
  not directly serialize every complete history observation as claimed by
  Revision 3. Do not duplicate private digest recipes in the runtime and
  describe the result as an accepted producer identity.
- ToolResult has ok/data/error/duration_ms/audit (tools.py:160–177).
  ToolAuditMetadata has evidence_ids (143–154); ToolError does not (127–133).
  MAX_AUDIT_EVIDENCE_IDS = MAX_SELECTED_CURRENT + MAX_HISTORY_OBSERVATIONS
  (106). Preserve actual ordering/deduplication semantics.

### N3 proof contract (proposed)

Compare two approaches before choosing: observational equivalence across
independent read transactions, or separately ratified narrow producer
snapshot-binding amendment. Both must compare complete typed results, not
merely IDs, and preserve S1 delta. For the first option, a dedicated persistent
observer connection must sample before reads and again under the final app-DB
write lock; never assume SELECT 1 pins a table snapshot. Account for self-writes,
lease/auth updates, connection-pool replacement, DB-wide false positives,
all source-file checks, and drift from N0/N2. State explicitly that filesystem
swap-and-restore cannot be excluded by endpoint hashes and that S1 does not
emit its internal F2 fingerprint.

Reviewer disposable two-connection WAL experiment: a read observer sampled
PRAGMA data_version; another connection committed 40 -> 39 -> 40; the observer
sample changed (True). This confirms that one specific cross-connection ABA
sequence was detected, not that every commit increments a monotonic counter
or that separate reads are atomic.

## 5. S2-P04/P05 — ownership and checkpoint proof obligations

The accepted app DB owns workflow run status. A new slice table is a proposed
contract amendment, not authority to reinterpret queued as halted or completed.
Separate run status, lease, slice disposition and historical state. F1 and RB3
own independent transactions and do not know the proposed lease; detecting
their later write is not prevention. In particular, a forbidden RB3 side effect
cannot be undone by aborting N3. Require an exact writer/entrypoint authority
matrix and enforce it or explicitly bound the guarantee. No S2 takeover,
automatic replay or reset to queued without separately approved design.

Test expired and revoked worker before/after each write, including independent
F1 commit and checkpoint write. Use live authorization and ownership clocks,
not evaluation clock. Do not call deferred services as a production probe.
Require explicit authority before changing F1/RB3.

A0 should supply the actual pinned saver signatures and observed sync graph
checkpoint/pending-write scheduling before finalizing C. Do not assume
one checkpoint per node, namespace accepted by root graph, or node-local
access to generated checkpoint IDs. Prove pending writes to an already sealed
parent cannot break seal validity or silently bypass it. Resolve lock ordering
when saver operations execute on a different thread while coordinator owns
app-DB write lock. Do not acquire that lock recursively via another connection.

Seal only the runtime-generated bytes/control data, including metadata, task
IDs, pending writes, parent, versions, channels, run and epoch. A historical
inspection is not live authorization. A seal provides integrity within a stated
trust boundary, not protection against unrestricted host/process compromise.
Select and verify exact serializer design; Revision 3 switches away from the
previous primitive single-channel design without ratification. Reject unsafe
deserialization before materializing any untrusted object. Define input bounds,
key lifecycle and immutable seal timing. No promotion of unsealed output.

## 6. S2-P06/P08 — persistence and reset

append_audit_event (audit.py:90–146) accepts request_id and derives key itself.
derive_audit_key (49–74) requires typed enums via .value. Existing-key lookup
returns the old row without full semantic equality; the S2 companion wrapper
must verify patient/run/actor/subject/outcome/detail and collision semantics
before advancing state. safe_detail is bounded and truncated: it cannot be
lossless tool metadata storage. Preserve error evidence IDs and separate
adapter success from runtime acceptance. Do not manufacture a result for an
uninvoked tool. Specify durability after tool return but before audit commit.

No schema ratified. Revision 3 introduces inconsistent table inventories
(workflow_slice_run in lifecycle and seal operations but not among three
proposed new tables). Require one canonical table/column/key/trigger
inventory, including slice disposition. Test every unique-key conflict,
anti-REPLACE/UPSERT, foreign-key scope, lease transitions, and nonempty
downgrade. No mutable history or reset bypass.

Reset must never commit arbitrary caller changes merely because a transaction
exists. Recheck live authority after restarting a transaction; establish exact
request dependency/session ownership and all competing F0/S2 write ordering.
Do not delete immutable history or checkpoint files. Refusal semantics and
any ErrorCode addition need contract reconciliation and owner decision.

## 7. Stage handoffs and acceptance gates

| Stage | Required input | Stop before |
|---|---|---|
| A0 | Actual candidate resolver, installed API, platform/hash/packaging and regression evidence | Any tracked change |
| A1 | Owner choice of exact candidate, exact paths and justified guard implications | Migration or runtime code |
| B | Ratified P01/P02/P04/P06/P08 lifecycle and schema, DDL parity and adversarial tests | Checkpoint/graph wiring |
| C | A0 actual saver evidence and ratified P05 | Executable workflow nodes |
| D | P03 producer/equivalence contract and P01/P02 regression closure, B/C evidence | Future nodes, policy activation, LLM |

No owner decision is ratified by this report. Preserve D-15 exactly:
AUTHORIZED_AGENT_MODULE_PATHS = ("__init__.py", "state.py", "tools.py").
An explicitly authorized separate package is only a candidate. D-09 remains
unchanged until a fresh measured pairing and owner decision.

## 8. Verification record, non-goals and review checklist

Executed here: GitHub exact-base source reads and raw commit/main identity
queries; isolated stdlib Python SQLite experiment described in sections 3–4.
Observed local SQLite version 3.46.1; constraint rejection and ABA sample
change as described. No application test or full migration executed by reviewer.
No Python 3.12 installation, dependency resolver, Windows gate, application
regression, scanner, lint, or production build executed for this change.
A0 reports and any hosted CI must be reviewed separately.

Changed-file allowlist for this review branch: this new report only.
No application code, manifests, locks, tests, CI, migrations, or existing
contracts changed. No clinical decisions, trust promotion, network runtime,
rule activation, tasks, notifications or LLM execution added. P5 remains
IN_REVIEW / NOT ACCEPTED; issue #14 remains OPEN. P4 remains
CONDITIONALLY_ACCEPTED_SYNTHETIC; GOLD-EX-11 remains FAIL / NOT PROVEN;
RB3-75..77 remain DEFERRED / NOT EXECUTED; DR-006 persistence PROHIBITED;
runtime demo policy unapproved and inactive.

Owner review: confirm parallel allocation, verify evidence and approve or
reject this review register; no acceptance or merge implied. Keep the branch
isolated pending A0 evidence. Rollback: simply leave the draft unmerged;
main and Arena's A0 starting tree are unaffected. No branch deletion or
history rewrite required.
