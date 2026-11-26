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


## 9. A0 report review — independent exact-base reconciliation, 2026-11-26

Disposition: A0 PARTIALLY_VERIFIED_WITH_BLOCKERS. Candidate B is a preferred
candidate for continued verification, not approved for adoption. The reported
Python 3.11 resolver/install/pytest and upstream probe results are Arena
evidence; actual Python 3.12 Linux and Windows execution remains blocked/not
executed. No new dependencies or guards authorized.

### P07-A: source identity versus dependency content

The reported base SHA and package/hash counts agree with exact-base GitHub
reads, but the listed accepted pin versions do not. The following Git blob
identities were independently retrieved at the base in section 1:

- requirements/requirements.lock: 934b2522bc43426714598349ad3e6c0d703c6bc6
  (26 pins, 511 hash occurrences, 0 marked pins).
- requirements/requirements-dev.lock: 4684a8650d681b5d37c4b25cb724fd32c45dfa60
  (39 pins, 624 hash occurrences, 4 marked pins).

Actual runtime pins (from the GitHub file, not reconstructed from report prose):

```text
alembic==1.20.1
annotated-doc==0.0.6
annotated-types==0.8.0
anyio==4.16.0
click==8.5.1
fastapi==0.162.7
h11==0.16.0
idna==3.20
mako==1.4.3
markupsafe==3.0.4
opentelemetry-api==1.45.2
packaging==26.3
pillow==13.0.0
pydantic==2.14.3
pydantic-core==2.50.4
pydantic-settings==2.16.3
pypdf==7.1.0
pypdfium2==5.15.2
pytesseract==0.3.13
python-dotenv==1.2.4
python-multipart==0.0.33
sqlalchemy==2.1.8
starlette==1.10.0
typing-extensions==4.16.0
typing-inspection==0.4.5
uvicorn==0.54.0
```

Actual dev pins:

```text
alembic==1.20.1
annotated-doc==0.0.6
annotated-types==0.8.0
anyio==4.16.0
click==8.5.1
colorama==0.4.6 ; sys_platform == 'win32'
fastapi==0.162.7
h11==0.16.0
httpcore2==2.16.0 ; sys_platform != 'emscripten'
httpx2==2.16.0
httpx2-jsfetch==1.0 ; sys_platform == 'emscripten'
idna==3.20
iniconfig==2.3.1
mako==1.4.3
markupsafe==3.0.4
opentelemetry-api==1.45.2
packaging==26.3
pillow==13.0.0
pluggy==1.7.0
pydantic==2.14.3
pydantic-core==2.50.4
pydantic-settings==2.16.3
pygments==2.21.0
pypdf==7.1.0
pypdfium2==5.15.2
pytesseract==0.3.13
pytest==9.2.0
python-dotenv==1.2.4
python-multipart==0.0.33
pyyaml==6.0.3
ruff==0.17.5
setuptools==84.2.1
sqlalchemy==2.1.8
starlette==1.10.0
truststore==0.10.5 ; sys_platform != 'emscripten'
typing-extensions==4.16.0
typing-inspection==0.4.5
uvicorn==0.54.0
wheel==0.48.0
```

The A0 report instead lists click 8.3.2, h11 0.16.1, idna 3.12,
mako 1.4.2, markupsafe 3.1.1, packaging 26.2, pydantic-core 2.45.3,
python-dotenv 1.3.2, typing-extensions 4.16.1, typing-inspection 0.5.1
and greenlet 3.5.1 while omitting opentelemetry-api from the accepted
runtime set. Its remaining-dev list also differs (iniconfig, pluggy,
pygments). Matching package counts do not establish matching pins.

Do not infer that the resolver used the incorrect pins solely from this
report discrepancy: compare the actual temporary inputs, constraints,
candidate locks, installed inventory and raw output before classification.
Require original baseline blob identity and full SHA-256 of exported
files; exact name/version/marker diff; distinguish report-only error from
experimental-input drift. If experiment inputs differ, rerun affected
checks on corrected exact-base constraints. Do not hand-edit candidate
locks. No adoption PR before evidence review.

### P05-A: checkpoint/tracing implications of A0 (reported, not reproduced here)

The synthetic graph reportedly generated four root checkpoints for two
nodes, with root namespace empty, node-specific namespace and only the
parent checkpoint ID visible in node context. Pending writes target the
pre-node checkpoint, with variable executor ordering. A saver failure
reportedly allowed a later node to run before invoke raised. Therefore
neither one-checkpoint-per-node nor synchronous saver-failure propagation
may be used as an invariant. Prove a quiescent outer completion barrier
before seal/state advancement; unsealed partial writes remain
non-authoritative. Do not rely on a future-node side effect being prevented
merely by an earlier saver exception.

Hostile tracing startup reportedly attempted DNS; guarded probes saw none.
This is evidence for the exercised paths, not a universal zero-egress
guarantee. Require fresh-process, actual Python 3.12 probes, explicit
legacy tracing handling, and verify the real API/configuration before
production implementation. No future nodes or LLM integration authorized.

### Next parallel work and gates

Arena: preserve the original session and export original A0 manifests,
constraints, locks, raw reports, installed inventory and probe scripts
with a SHA-256 manifest, no environment secrets or wheels/venvs required.
Correct the report or rerun affected experiments only as indicated by the
actual bytes. No production edits.

Reviewer: inspect artifact identity, determine exact Candidate B delta and
prepare a bounded Python 3.12 verification path using hosted Linux CI
and owner Windows after appropriate scope authorization. Standard CI
only installs the dev lock and runs existing checks; it does not itself
prove runtime-only install, non-editable wheel imports or the new graph
and egress probes.

A repeat of the small SQLite constraint/ABA probe was actually executed
in this review turn (CPython 3.13.5, SQLite 3.46.1): inserting 40 succeeded,
41 raised IntegrityError; after rollback stored rows were [(40,)].
Two external commits 40 -> 39 -> 40 changed observer data_version 2 -> 3.
This is not an application regression or Python 3.12 platform result.
No application tests or package installs executed here.

Main unchanged; PR #49 remains draft. Original docs-only report preserved
byte-for-byte as prefix. No change to application source, dependency
manifests, locks, tests, guards, migrations or runtime. P5 remains
IN_REVIEW; no owner decision or merge authorized.


## 10. A0 original artifact reconciliation — independent review, 2026-11-26

The owner transferred Arena's original artifacts via an ASCII Git binary
patch embedded in an exported workspace patch. The reviewer extracted only
the transfer text and executed git apply --check and git apply in a fresh
isolated directory (not a repository checkout).

Verified transfer: 1,791,791 bytes, SHA-256
4d4d4465de03e1e2e640cc91309d83b843c4b5047e87dc4f67c1ae864cba20f4.

- Evidence ZIP: 1,233,238 bytes, 70 entries, SHA-256
  b9fd006f8fad2507f4beec4e13738b940f73fc02c498b1b1da793221d46e50bb.
  CRC clean; all 69 listed internal SHA-256 checks matched.
- Baseline supplemental ZIP: 172,759 bytes, 11 entries, SHA-256
  11e4b5372cd8c57ec1e5dbf69f1c2ab15504b51246fac931408637c3a06064ed.
  CRC clean; all 10 listed internal SHA-256 checks matched.

No binary artifacts added to this PR. Original experiment inputs and fresh
baseline copies match byte-for-byte for all three files. Git blob SHA-1
computed directly over each original file (git blob header plus bytes)
matches previously retrieved exact-base GitHub identities:

- pyproject.toml: a9c3f0de97d925394558e6908b70999a957bdb23
- requirements/requirements.lock: 934b2522bc43426714598349ad3e6c0d703c6bc6
- requirements/requirements-dev.lock: 4684a8650d681b5d37c4b25cb724fd32c45dfa60

Machine-parsed constraints match all 39 accepted dev name/version/marker
entries. Both original generated candidate locks preserve every existing
name/version/marker entry in their respective baseline lock. No removals
or changes. All four original lockfiles are byte-identical to their
corresponding saved resolver stdout. Counts independently parsed:

| Candidate | Runtime pins | Dev pins | Net-new distributions | Promoted dev to runtime |
|---|---:|---:|---:|---:|
| A | 59 | 67 | 28 | 5 |
| B | 55 | 67 | 28 | 1 |

The reported installed-package JSON inventories match all applicable Linux
CPython 3.11 lock pins (extra pip and, runtime only, setuptools are environment
tooling). The supply-chain inventory covers all 69 distinct distribution/version
pairs from the two development locks; its advisory arrays report no active
advisories. This verifies inventory consistency, not independently queried
advisory coverage or independent rehashing of absent third-party wheel bytes.

P07-A disposition: REPORT_ONLY_ERROR for the earlier accepted pin-version
discrepancy. Experimental-input drift not found in the original artifacts.
Do not rerun the 3.11 resolver solely for that discrepancy. Preserve the
original report and append this correction; no actual Python 3.12 platform
acceptance.

Candidate B preferred for continued feasibility: retains the httpx2 dev-only
guard, promotes only pyyaml, and its regression JSON records 1526 passed on
Python 3.11.2. This is Arena-executed evidence, not a reviewer rerun.
Exact Candidate B lock SHA-256:
runtime bf28103ffcc633bc5f20ca406639519376c2f37984bebe1d2fc8a511a90a7fd1;
dev bd77ba37b61fa37bf3c2d624f73aaa1c714ff384bbc5dd51d7bfe7c919efdc68.

### A0 remaining verification issues

- Windows script is a partial scaffold, not an executable end-to-end gate.
  It stops after creating the resolver venv and installing tools. It contains
  no complete manifest/lock install, wheel, regression or egress sequence.
- Linux script recompiles candidate locks rather than using the preserved
  exact experimental bytes, strips environment markers when reconstructing
  constraints, does not itself verify the exact base, and deletes a copied
  .git directory without a strict fresh-workspace guard. Do not run it
  verbatim. Use an isolated fresh checkout of the accepted SHA and the exact
  recovered candidate lock bytes, verify hashes, and compare any separately
  regenerated lock before using it.
- Nested wheel inventories directly inspected: current_packages_list has
  6 entries and no app/services entries; both candidate_packages_find_default_no_namespaces
  and candidate_packages_find_with_namespaces_true have 89 entries and 35
  app/services entries. The separate candidate_packages_find artifact also
  has 6 entries. The explicit corrected namespace-discovery wheel supports
  the packaging hypothesis; retain the distinction between artifacts and
  require actual non-editable installation under Python 3.12.
- Regression reports include summaries and tail output, not all requested
  complete raw logs. Some candidate probes are synthetic and should not be
  imported or executed as production code. Inspect and harden before rerun.
- No actual Linux/Windows Python 3.12 execution yet. Existing CI cannot prove
  runtime-only dependency installation, wheel import isolation, checkpoint
  scheduling or hostile-environment egress behavior without separate checks.

Reviewer executed archive extraction and manifest checking, Git-blob and
pin/marker/inventory comparisons, and nested wheel archive listing/CRC
checks; no third-party package installation, application tests or upstream
runtime execution in this turn. Main was re-read unchanged; PR #49 remains
draft. New session may start from the accepted main using recovered evidence
as historical input. Preserve the old session without applying its patch.
A0 remains PARTIALLY_VERIFIED_WITH_BLOCKERS. A1 dependency adoption,
schema, graph, policy activation, LLM and merge remain unauthorized.


## 11. Independent review of owner Windows Candidate B feasibility evidence — 2026-11-26

The owner executed the separate verification kit on Windows x64, against the
accepted base and recovered Candidate B inputs, not an adopted dependency
commit. Received ZIP P5-S2-Windows-Evidence-20261126-145707.zip; SHA-256
10154e427c84aea1df6cc96631afcd8f5d67dab1030043e870dd20806566a645.
Reviewer checked ZIP CRC (clean), parsed result.json and all relevant logs,
and compared installed inventories against original kit lock entries using
normalized distribution names and Windows CPython 3.12.9 marker evaluation.

- Recorded interpreter CPython 3.12.9 AMD64, Windows-11-10.0.22621-SP0,
  SQLite 3.45.3. Recorded base/tree match section 1.
- 38 recorded subprocess commands, all rc=0 and expected rc=0. The run
  used isolated clones, removed remotes, and separate venvs; no adoption.
- Reported candidate manifest and both lock hashes match the recovered
  Candidate B identities. All 55 runtime and 66 Windows-applicable dev
  pins match installed inventories exactly; pip 24.3.1 is additional
  venv tooling in each. Universal dev lock has 67 entries; the Emscripten
  only package does not apply to Windows. Both installs used binary-only,
  hash-required, no-deps pip commands; pip checks report no broken requirements.
- Original wheel 6 entries; corrected wheel 87 entries (no disposable
  dummy runtime package in this comparison). Non-editable installation
  succeeded into runtime venv. Isolated Python -I imports of app.main,
  app.agents.state/tools, app.services.p5_run_gate/p5_evidence_bridge,
  and app.db.models succeeded; app.main location is within venv site-packages.
  Wheel entry inventories and hashes are recorded, not wheel bytes supplied
  for independent rehash. This tests imports, not wheel-only application
  deployment, path layout, or all resource packaging.
- Clean and guarded two-node synthetic probes each returned counter 11
  and trace [one, two], four root checkpoints, eight pending-write rows,
  history steps [2,1,0,-1], zero recorded socket/DNS attempts and only
  MainThread at observation. Positive control explicitly exercised the
  socket trap. Legacy-reject probe exits before imports by construction;
  it is not evidence of production wrapper enforcement. Clean and guarded
  both disable tracing via tracing_context; no unguarded hostile case
  rerun in this kit. No saver-failure injection or custom HMAC serializer
  test in this Windows run. Prior host probe failure evidence remains
  separate; no general network isolation guarantee.
- Full pytest summary: 1522 passed, 4 skipped, 0 failed in 610.70 s.
  Collection 1526; P2 284, P3 443, P4 379, P5 286, remaining 134.
  Skip identities and reasons not printed; do not infer them from count.
- Ruff lint PASS, format 151 files already formatted. Alembic upgrade,
  downgrade, reupgrade and smoke PASS (0008_p4_rb3_review_persistence,
  24 tables). OpenAPI PASS (17 paths, 18 operations, 43 schemas).
  Scanner PASS (306 tracked files, 7 secret patterns, 4 claim patterns).
  No frontend execution or newly implemented S2 behavior in this kit.

Disposition: Windows CPython 3.12 Candidate B bounded feasibility evidence
reviewed, successful for the executed checks. Linux CPython 3.12 remains
outstanding; supply-chain/advisory independent verification and final
design review remain open. No owner ratification, dependency adoption,
scope/guard changes, or implementation authorization follows from this run.
The reviewer parsed owner-provided evidence; did not rerun Windows commands.
Arena reportedly completed its parallel design task; report not yet
received/reviewed. Do not merge this draft or change main.


## 12. Independent Revision 4 review — 2026-11-26

Disposition: useful investigative progress; NOT RATIFIED. Arena reports
reproduction of P01 (41 distinct blocker facts causes F1 CHECK failure,
rollback), P08 (reset DELETE observation FK failure with a selected run),
and P06 (same audit key returns old content). These are Arena-reported
scratch Python 3.11.2 / SQLite 3.40.1 experiments, not independently
executed on accepted Python 3.12/locks. Preserve actual scripts, input
identities, commands and outputs. No production patch is authorized.

R4-01 (P01): c1 is a promising minimal approach, not yet an approved fix.
The first scan may break before all selected facts/documents are captured
in snapshot (p5_run_gate.py:289–341), and the second scan (608–661) adds
conflicts from all doc IDs. A bounded incomplete projection must remain
unavailable; prove deterministic reason precedence, omitted-source
semantics and fingerprint/replay compatibility. Same gate_version +
fingerprint keys immutable existing rows (736–785); changed semantics can
cause replay conflict, including with historical unavailable receipts.
Prove compatibility or propose explicit versioning, not deleting rows
or clamping counts. Test source bytes unavailable, exact 40, overflow with
and without conflict, distinct fact/issue count bounds and F2 ineligibility.
Rev4 calls c1 necessary but excludes p5_run_gate.py in its B allowlist;
propose separately authorized correction with exact test paths and D-09.

R4-02 (P03/P04): Option A as written cannot execute. S1 _evidence calls
F2 (tools.py:351–371); F2 rejects dirty/active sessions (450–451) and owns
BEGIN IMMEDIATE (454), always rolls back (470–472). Same-session nested
calls are rejected; a separate connection cannot acquire a second
IMMEDIATE lock while the barrier owns one. Reviewer executed a disposable
stdlib sqlite3 experiment (CPython 3.13.5 / SQLite 3.46.1): two independent
connections, first BEGIN IMMEDIATE, second BEGIN IMMEDIATE with timeout
0.1 s. Both DELETE and WAL modes returned SQLITE_BUSY (database is locked);
second acquisition succeeded after first rollback. A third observer could
read a table and data_version while first held the lock. This is a
transaction mechanism probe, not an S1 test. A0 Windows evidence separately
confirmed the existing adapters' baseline suite.

Propose sampling the same dedicated observer AFTER intended lease/F1 writes,
perform all F2/S1 reads and repeats BEFORE the final write lock, then under
lock only compare observer version, live scope/lease and any explicitly
authorized locked read evidence. Any foreign commit (including auth
last_used_at) conservatively rejects; do not ignore it selectively.
No adapter invocation under barrier. Explain F1 commits and audit cannot
be called no-write; F1/RB3 do not honor S2 lease. Prove how earlier N0/N2
receipt is rebound to the N3 producer evidence, including HALT path and
filesystem ABA limitation. If unable to prove, propose a separately
authorized snapshot-binding producer amendment; no private API shortcut.
Do not call inspect_current_run_gate_locked directly in S2: its contract
says only the F2 bridge may call it (p5_run_gate.py:857–884).

R4-03 (P08): authenticated route uses PrincipalDep AND DbSession
(api/v1/demo/router.py:59–77). auth/dependencies.py current_principal
uses the same DbSession dependency, and resolve_session (accounts.py:
224–259) flushes last_used_at. Rejecting any active transaction in
reset_demo would reject ordinary authenticated reset requests. Need
one explicit transaction owner with actual endpoint/auth integration,
never an arbitrary commit or rollback of caller changes. Re-check live
authority under lock; race F0 vs reset and revocation; retain files and
audit. API_CONTRACT.md:197–200 also says deletes runtime files and lists
only active statuses, conflicting with accepted no-file-delete behavior
and proposed any-history refusal. Explicit owner contract reconciliation,
not silent addition of E_RUN_IN_PROGRESS or E_VALIDATION substitution.

R4-04 (P05/P06): define concrete seal table, atomicity with exact stored
bytes, verified raw read-before-deserialize, key provisioning and
anti-replay/anti-rollback trusted app-DB anchor. A valid old HMAC prefix
must not itself authorize continuation. Pending writes have no
new_versions parameter; that parameter belongs to put. Exact pinned
API and threading/failure injection needed. Append-only pending-write
seals must handle saver UPSERT/REPLACE behavior and duplicate keys;
prove canonical current-set commitment and no unsealed promotion.
Define adapter result separately from runtime rejection, retry/attempt
identity, non-invoked vs invoked-and-raised, duration nondeterminism
and complete audit semantic equality; do not use whole ToolResult JSON
as retry-stable identity. Do not authorize automatic retry contrary to
no-takeover. Table/trigger/FK/constraints and downgrade inventory
remain proposals, not closed specification.

R4-05 (P02/P09): specify separate HALT -> N8 vs PROCEED -> N3 -> bounded
quiescent END. N8 is a halted node; do not fabricate halt_reason on
successful N3 or app-DB status. Unavailable/out-of-graph abort must
carry actual typed cause, not a fabricated N2 trace. GateEvaluationRef
limits issues and historical exclusions as well as distinct fact count;
prove bounds. Preserve current phase gates. Exact source guard
test_p2_scope_guards.py:85 and test_safety_guards.py:33 prohibit langgraph
imports. check_alembic_smoke.py:76 hardcodes 0008. Future B/C/D require
explicitly authorized narrow guard/smoke changes or a compatible
alternative; no scope bypass or silent weakening. Current allowlists
exclude these prerequisites and D-09 append path. Reconcile actual old
OD-01..OD-11 topics against proposed D-16..D-25; do not overwrite existing
owner decisions. Separate A1 packaging decision from future runtime module.

R4-06 (P07): reviewer Windows evidence section 11 supersedes Arena's
unexecuted-Windows statement. Reopened owner ZIP; CRC clean, 38/38
recorded expected zero exits, explicit pytest 1522 passed/4 skipped.
Linux actual CPython 3.12 remains outstanding. Do not rerun the Windows
baseline campaign just to refresh prose. No 3.12 interpreter in reviewer
container (3.13.5 only); do not substitute. Linux isolated kit execution
or separately authorized experimental hosted CI is next dependency gate.
Keep original Candidate B lock bytes; no dependency adoption.

Next: focused R4 correction and preserve proof scripts in parallel with
Linux feasibility. No full new design rewrite; no implementation,
migration, dependency adoption or merge authorized. Reviewer read exact
base source and executed the small SQLite locking probe, not app tests.
Main remains unchanged. All earlier register content retained.


## 13. Independent review of R4 focused closure addendum — 2026-11-27

Disposition: NOT RATIFIED. Accept the correction of the impossible nested
F2 barrier invocation and the distinction between HALT and quiescent END
as design progress, not completed implementation. The owner has a WSL2
Ubuntu 26.04.1 x86_64 environment, independently installed CPython 3.12.16
via uv 0.13.10, reported SQLite 3.54.1, and the accepted baseline identity.
Linux full execution results are not yet received. Windows section 11
stands. No substitution or additional adoption authority.

R4C-01: c1-prime does not establish historical replay equality. A run
whose first pass processed 36 blocker facts, then tripped the cumulative
cap in a later document, could formerly record one additional VI-006
from the skipped document and persist union 37. The new rule would remove
that blocker (union 36), despite both being below 40. Reviewer executed
only the abstract set example (37 vs 36, not equal), NOT the real app
fixture. Arena must construct a reachable synthetic old-persist/new-replay
case and compare actual semantic tuples and fingerprints; cover skipped
docs due to missing bytes as well as cap, and late unavailable reason
overwrites (observations 540–606, omissions 669–681, recovery 727–728,
file recheck 730–734). Do not assert the cap reason is always final.
Do not assert issue-count <=40 from fact-union <=40; multiple issues
can share a fact or be document-only. Test the S0 representability
boundary separately. Decide gate-version/replay strategy after proof;
F2 imports GATE_VERSION (bridge:44,99). No silent replay relaxation,
history rewrite, clamp, or source edit authorized.

R4C-02: observer after N2 leaves an unobserved gap. If another writer
commits between F1 receipt and v0, including a different valid persisted
F1 proceed evaluation, N3 may read a different gate through F2. Selecting
the old receipt's immutable row and comparing manifest IDs does not bind
the actual N3 DTOs to that gate. F2 emits gate_evaluation_id, gate_version,
gate_input_fingerprint_sha256 (bridge:415–417); S1 results do not expose
this complete binding. Prove a shared authority window covering N2 and
N3 without mistaking intentional own writes for foreign ones, or propose
a narrow, independently authorized producer amendment carrying actual
producer identity and digest. Hashes of DB projections alone do not
prevent filesystem swap/restore. HALT, abort and successful paths all
need fencing/quiescence before advancing durable slice disposition;
no fabricated NodeEvent for HALTED with GateDetail (state:1358–1372).
A full successful N2 trace must not be omitted merely because N3 succeeds.

R4C-03: reset design still impossible as written. The request auth path
has already flushed DML into the same session (accounts:257–258).
Reviewer executed disposable stdlib SQLite 3.46.1 / CPython 3.13.5
probe: create table user_session, insert/commit, UPDATE last_used_at,
observe in_transaction=True, execute BEGIN IMMEDIATE => OperationalError
"cannot start a transaction within a transaction"; rollback restores
old value. This proves transaction mechanism, not whole endpoint.
After flush, db.dirty is not proof that no other writes happened.
Choose transaction ownership BEFORE auth DML, or leverage a demonstrably
already-held SQLite writer lock under the request transaction with actual
provenance/authority and integration tests. No nested BEGIN, no commit
or rollback of arbitrary caller state. Live auth re-read must bypass
stale identity-map state and respect uniform existing error semantics.
Reset-first must allow fresh valid F0 creation, not require no history
for all normal subsequent F0 runs. F0 must revalidate live scope and
selection after serialization, not trust pre-reset identities. Explicit
contract reconciliation remains required.

R4C-04: checkpoint storage and anchor proposals improve specificity but
are not complete. Same call stack != same transaction. Specify actual
carrier type/channel/metadata/pending-write identity and HMAC coverage
including lease and slice provenance. Confirm pinned PK and replacement
semantics, no invented genesis id 0, verify complete set and authenticated
head at exact read/commit boundary; old anchor denotes previous head
rather than requiring new head equal old head. Address deletion of sealed
rows and seal-without-carrier, replay of valid branches, rollback of
pending-write set, bounded safe raw reads. Clarify app-DB trust assumption.
Audit identity must include complete semantic error fields, not merely
error_code; duration excluded. A pre-invocation durable slot reservation
is not present in the buffered-only transaction proposal, so crash
cannot prove invoked_no_return without durable intent and even then
invocation itself may be unknown. Separate unknown/invoked/returned
evidence, never invent a persisted slot or post-crash event. No implicit
retry or takeover. Later C/B-specific proofs, not full rewrite now.

R4C-05: existing guards scan all backend/app Python sources
(test_safety_guards.py:53–70, test_p2_scope_guards.py:269–281). Adding a
new exact-path guard cannot make unchanged global bans permit LangGraph.
Authorize exact-path amendments to BOTH existing bans at runtime stage
only; preserve remaining bans and D-15, add negative fixtures. No dynamic
import bypass. Migration smoke changes explicitly scoped to B, preserve
0008 historical assertions. D-09 handoff file must be included and
fresh measured pairing authorized. Packaging is a separate A1 item.

Historical proposal crosswalk recovered by reviewer from prior owner
chat attachments, not the accepted tree. Revision 2 attachment
Pasted text(20261126-095417).txt section 14 (all unratified):
- R2:OD-01 graph scope/bootstrap -> D-18, D-26.
- R2:OD-02 workflow lifecycle -> D-19, D-26.
- R2:OD-03 ownership -> D-19.
- R2:OD-04 checkpoint/serializer/crash window -> D-20.
- R2:OD-05 dependency/import guard -> D-24, D-23 (split).
- R2:OD-06 migration -> D-21.
- R2:OD-07 module placement/D-15 -> D-23.
- R2:OD-08 audit error and deferred slots -> D-21.
- R2:OD-09 transitive pins -> D-24.
- R2:OD-10 failure halt mapping -> D-18.
- R2:OD-11 cross-call snapshot -> D-17, D-27.
Revision 3 attachment Pasted text(20261126-104817).txt section 11
reused OD-01 for pin selection (D-24), OD-02 for wheel discovery
(separate A1 packaging decision), OD-11 for snapshot (D-17/D-27),
and added OD-12 failure boundary (D-18), OD-13 takeover (D-19),
OD-14 reset (D-22). Qualify references by revision; do not confuse these
with accepted S0 D-01..D-15. This is a topic crosswalk, not equivalence
or ratification. Arena's inability to find external history in main is
explained. Preserve original proposal text in owner attachments.

R4C-06: reported untracked P5_S2_R4_SYNTHETIC_EVIDENCE_20261126.md
not yet delivered to reviewer. Request actual downloadable evidence
first; preserve old scripts/output and checksum. Next narrow experiment
only: prove or refute old persisted <=40 overflow receipt replay under
proposed c1-prime, and demonstrate actual endpoint transaction ordering
on isolated synthetic fixture if feasible. No tracked edits, commits,
pushes, migration or dependency adoption. Park later B/C/D design
obligations until their implementation planning, not another complete
revision cycle. No final design ratification or merge. S2-A1 may be
considered separately after Linux evidence, exact pin/supply-chain review,
explicit packaging decision and owner authorization.
