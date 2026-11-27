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


## 14. Linux WSL2 partial evidence review — 2026-11-27

Owner-provided P5-S2-Linux-Partial-Evidence-20261127-013341.zip,
41325 bytes, SHA-256
855a27f1c00d4f13f18e5c1d77f1682818321cb2b59df2a1ecfab9c03c39831c.
Reviewer opened ZIP, verified CRC, parsed result.json, logs, and
compared both installed inventories with the recovered Candidate B
lock bytes using applicable Linux markers.

CPython 3.12.16, SQLite 3.54.1, Linux WSL2 x86_64/glibc 2.43.
Exact base/tree and three candidate hashes reported matching.
31 recorded subprocess steps, all expected rc=0. Runtime 55 and
Linux-applicable dev 65 pins match exactly; extra pip only. Windows-only
and Emscripten-only dev entries excluded. Hash-required binary installs,
pip checks, original six-entry/corrected 87-entry wheel builds,
non-editable installed imports, editable install, bounded clean/guarded
graph probes and trap control, legacy rejection, Ruff/format all passed.
Graph clean/guarded logs show counter 11, four checkpoints, eight
pending writes, zero recorded socket/DNS attempts, MainThread only.
These do not prove general egress isolation or saver failure behavior.
Collection 1526 (P2 284, P3 443, P4 379, P5 286, other 134).

Full pytest exceeded 1800 seconds; status BLOCKED_OR_FAILED and
79 success markers, no final summary. Do not classify timeout as
a failed assertion or a passing regression. First unreported node
in collection order is the protected GET observations test in
backend/tests/p2/test_p2_http_routes.py (ordinal 80); exact stalled
setup/call/teardown is unproven. Diagnose with isolated verbose targeted
run and timed faulthandler stack dumps before rerunning the entire suite.
Migration upgrade/downgrade/reupgrade, migration smoke, OpenAPI and
scanner steps 23–28 did not execute. Keep original logs and report
unchanged; supplementary diagnostics separate. No adoption or acceptance
implied. Windows evidence remains valid within section 11 limits.


## 15. Focused executable proof review and Linux I/O diagnosis — 2026-11-27

Disposition: c1-prime REJECTED; accept reported defect reproduction as
investigative evidence, not correction acceptance. Old evidence file
P5_S2_R4_SYNTHETIC_EVIDENCE_20261126.md independently rehashed:
32809 bytes, SHA-256
96045b83d59487e160fb4a101e09df82a81b2e7417b52a4f589939b6d01512c9.
New report attachment Pasted text(20261126-235754).txt, 18826 bytes,
SHA-256 5cd09a1827c409961b3d9b321ec7d4f46d82c7529aa5aca115432bae8a55004a.
New scripts, four-hunk disposable patch and JSON results still reside
in Arena's ephemeral scratch directory; they are NOT delivered or
independently rerun. Obtain these before session reset.

R4C-01: Arena reports real migrated F0/F1 cases on CPython 3.11.2 /
SQLite 3.40.1. Four valid old unavailable rows (cap, missing bytes,
inadmissible observation, excessive history) replay under 1.0.0
before c1-prime but return 409 E_IDEMPOTENCY_CONFLICT after it.
Count 37 -> 36 or 40 -> 39 and a VI-006 semantic tuple disappears.
This corroborates exact-source review of stable key and equality
at gate:736-785. Control unchanged. Exact40 overflow yields 41
distinct facts and old CHECK failure; c1-prime fresh count 40.
Late unavailable reason overwrites independently observed in two
observation cases; other sites only source-read. Do not adopt c1-prime.
Keep 1.0.0 persisted history and all successful replay comparisons.
A new non-persistable outcome is a contract decision: preferred
direction is a typed refusal explicitly distinct from a certified
persisted F1 receipt (or explicit non-persistence marker with
consumer changes). Do not approve returning an indistinguishable
ordinary RunGateReceipt with gate_evaluated=True/replayed=False and
no gate/audit rows. Require require_existing branch to keep F2
read-only and fail-closed; no silent deletion/clamping, schema
relaxation, exception swallowing or version bump. Tests must pin
historical semantics, actual count, rollback, audit/row absence,
repeat and consumer refusal. Owner approval and D-09 still needed.
Additional S0 representability defect: Arena reports 42 blocker
rows with 39 distinct facts in a valid HALT, accepted by F1 storage
but rejected by GateEvaluationRef.issues max_length=40
(state:1590). Count bound does not bound issue count. Do not truncate,
mislabel HALT, fake N8, or globally remove bounds. Derive separate
producer cardinality and bounded projection or typed abort before D.
Any S0 contract/version change requires separate authorization.

R4C-03: Arena reports nested BEGIN failure, changed-timestamp auth
DML acquiring writer lock, reset rollback with history, reset-first
fresh F0 success. Useful but the proposed implicit auth writer lock
is not guaranteed. Exact accounts.py:257-258 assigns last_used_at and
flushes. A no-op assignment can emit no UPDATE. Independent reviewer
executed a disposable SQLAlchemy 2.0.50 / CPython 3.13.5 / SQLite
3.46.1 probe: mapped auth row, select and assign identical stored
timestamp, flush. Statements [SELECT], ORM in_transaction=True,
driver in_transaction=False, db.dirty=False; sibling BEGIN IMMEDIATE
succeeded. Changed value: [SELECT, UPDATE], driver in_transaction=True,
sibling refused database is locked. Both request transactions rolled
back. This is a mechanism probe, not exact app/target-pin execution.
A guaranteed request transaction lock before authority evaluation and
delete is required, including same-clock/no-op path; prefer explicit
reset-scoped acquisition before auth DML or equivalent tested
transaction owner, not nested BEGIN. Preserve auth 401 and 403
semantics, no arbitrary caller commit/rollback, no file deletion.
Do not imply no post-DML failure is possible; unexpected failures
must roll back atomically. Refuse before destructive DELETE, not
necessarily before all request auth DML. Any history protecting
immutable dependencies must block reset; active-status-only check
does not guarantee referential safety. Reset-first permits new F0
after live revalidation. D-22 contract/error-code and exact scope
still open. No implementation authorization.

R4C-02/04/05 acknowledged by Arena and retained for respective stages.
Do not request another full design revision. Deliver new scratch
evidence only, then stop for narrow owner decisions. No merge.

Linux supplementary owner diagnostic: same protected GET observations
test passed 1/1 (401, rc=0, 30.51s setup, 0.02s call). A/B profiling
on disk vs /dev/shm with same interpreter and test: 35.40s versus
0.85s reported pytest time; setup 35.17s vs 0.61s; disk _migrate
34.58s cumulative. Approx 41.6x for this specific profiled test only,
not a full-suite speed claim or proof of a storage subsystem fault.
Evidence Pasted text(20261126-235455).txt. Full regression restarted
by owner with temporary files on tmpfs, unchanged candidate locks
and source, no SQLite safety settings weakened. Await actual JUnit
and full log; migration/OpenAPI/scanner still outstanding. tmpfs
is not a durability or hosted-runner proof. A1 still not authorized.


## 16. Linux feasibility completion — independent archive review, 2026-11-27

Owner supplied three archives. Reviewer reopened their actual bytes,
recomputed SHA-256, checked ZIP CRC for every member and parsed logs,
JSON and JUnit (no application rerun by reviewer).

- Partial evidence (duplicate of section 14), 41325 bytes, 34 members:
  855a27f1c00d4f13f18e5c1d77f1682818321cb2b59df2a1ecfab9c03c39831c
- P5-S2-Linux-Regression-full-regression-mav5dToV.zip, 1142572 bytes,
  12 members:
  54cdf66f6d37b3be8b7326b3e5c1ef57a532c051a8b012a33cd9d853d8d893cb
- P5-S2-Linux-Final-final-checks-6lbloAe1.zip, 3428 bytes, 10 members:
  ecef079fffac7619a2f24f90f504f3cd3db0a238e61052ff627530ba737243e6

Original partial report remains BLOCKED_OR_FAILED (1800s timeout).
Supplementary tmpfs regression log explicitly reports 1526 passed in
288.16s, exit 0; JUnit reports tests=1526, failures=0, errors=0,
skipped=0, time=288.089s. All 1526 unique (classname,name) pairs match
the original collected node IDs exactly. Counts: P2 284, P3 443,
P4 379, P5 286, other 134. No frontend or new S2 implementation tested.
Only 264 MiB /dev/shm usage reported after completion. Original timeout
is retained; no rewritten result.json or single uninterrupted run claimed.
The 31 successful initial steps plus regression plus six supplementary
checks account for all 38 expected successful steps across executions.

Final status.txt: 23_upgrade=0, 24_downgrade=0, 25_reupgrade=0,
26_migration_smoke=0, 27_openapi=0, 28_scanner=0, FINAL_EXIT_CODE=0.
Migration logs traverse all eight revisions in each direction as
appropriate. Smoke reports head 0008_p4_rb3_review_persistence, 24
tables; OpenAPI 17 paths/18 operations/43 schemas; scanner 306 tracked
files/7 secret patterns/4 claim patterns. Before/after git status in
both supplement archives identical (only pyproject.toml and two
requirements locks modified, unstaged). Final integrity log all OK.
Reviewer recomputed corrected manifest from original verification kit
bytes using the exact inspect_candidate replacement:
4ef491232430a1910c3ed87f67fe127f9be7d32469d276fdca389f73a0875976.
Matches regression hash record. Both candidate lock hashes match kit
and partial JSON (runtime bf28103ffcc633bc5f20ca406639519376c2f37984bebe1d2fc8a511a90a7fd1;
dev bd77ba37b61fa37bf3c2d624f73aaa1c714ff384bbc5dd51d7bfe7c919efdc68).
Runtime and Linux-applicable dev installed inventories independently
compared again: 55/65 exact applicable pins; extra pip 26.3 in each.
Reopened Windows original archive, CRC and hash match section 11,
pytest summary 1522 passed, 4 skipped, 610.70s; skip identities
remain unrecorded there, not inferred from Linux outcomes.

Disposition: bounded Windows and Linux WSL2 CPython 3.12 feasibility
execution evidence COMPLETE / REVIEWED for Candidate B and tested
package-discovery correction. Not a durability proof (tmpfs), hosted
CI proof, complete application deployment proof, or runtime safety
authorization. Wheel byte artifacts not supplied. Original candidate
manifest without packaging correction is not the tested adoption target.
Independent current advisory lookup across all 67 universal candidate
dev pins (which include all 55 runtime pins), pin/packaging authorization,
exact A1 change scope, and owner decision still required. OSV or other
public advisory results must be preserved; no assertion of zero
vulnerabilities until a complete query succeeds. No dependency
adoption, application source, guard, migration, implementation,
merge, or Phase 5 acceptance authorized. Arena's new scratch proof
transfer from section 15 still pending, separate from A1 feasibility.


## 17. Candidate B advisory evidence and proposed A1 authorization — 2026-11-27

Owner executed the reviewer-supplied stdlib HTTPS OSV querybatch script.
Evidence P5-S2-Candidate-B-Advisory-20261127-021958.json, 35512 bytes,
SHA-256 e06e18897193c11f043ffde0f8b0e329b168f9fbd38d473da7a63a037a06a717.
Timestamp 2026-11-27T00:19:58.751539+00:00.
Reviewer parsed actual attachment and original verification kit ZIP:
67 unique Candidate B name/version pairs match dev lock exactly; all
55 runtime pairs included. Lock SHA-256 matches section 16. All queries
PyPI; single raw response contains 68 ordered entries for 67 candidate
queries plus requests==2.19.0 positive control. Findings agree with
raw response, no next_page_token, zero candidate hits; control has 10
advisory records (not necessarily 10 distinct vulnerabilities).
This is owner-executed API evidence independently parsed by reviewer,
not a second live query, not a malware audit or guarantee against
unknown vulnerabilities. OSV does not certify the application or
runtime. All bounded A0 execution evidence is now reviewed; owner
adoption decision remains pending. No phase PASS, implementation,
or merge authorization implied.

Recommended narrow A1 owner decision: D-24 exact Candidate B plus
the independently tested package discovery correction (not D-23
runtime module approval). Exact byte targets from section 16:
pyproject.toml 4ef491232430a1910c3ed87f67fe127f9be7d32469d276fdca389f73a0875976;
requirements/requirements.lock bf28103ffcc633bc5f20ca406639519376c2f37984bebe1d2fc8a511a90a7fd1;
requirements/requirements-dev.lock bd77ba37b61fa37bf3c2d624f73aaa1c714ff384bbc5dd51d7bfe7c919efdc68.
The original verified kit ZIP is the transfer source; use inspect_candidate
to obtain fixed manifest, do not re-resolve or manually reconstruct locks.
Retain all baseline pins and markers. Proposed A1 exact allowlist:
these three files plus append-only docs/phase-reports/PHASE_5_REPORT.md
and docs/roadmap/PHASE_PROGRESS.md (record actual owner decision, sources,
evidence and limitations). Separate new feat/p5-s2-a1-dependencies branch
and draft PR from exact base 96589dd35df7e8b9ecc690f19f51105a570e1b69.
AGENTS.md requires explicit owner decision in PR thread and roadmap
for scope outside default phase paths. No other paths; no imports,
application code, runtime package, guards, migrations, tests, CI
changes, or collection pairing edits. Stop if a gate requires scope
expansion. Exact-head CI plus fresh applicable checks and reviewer
verification required before any owner merge consideration. Preserve
P01/P02/P03/P04/P05/P06/P08/P09 and all deferred safety gates. Arena
scratch evidence transfer pending, separate from A1. Owner may approve
only this narrow implementation scope; B/C/D remain unapproved.


## 18. R4C evidence transfer verified; A1 authorization recorded — 2026-11-27

Owner supplied patch 01a217c9-367c-7625-a898-b360d5c008e5 (2).patch,
566768 bytes, SHA-256
7dd89d4ee980ce21b5a9ca737b5a8051ff4970d934531cb19fda2fe685eae1b3.
Reviewer extracted the added Base64 text (525752 bytes, SHA-256
d87c1064f80d50c0f406d36bb69da8d424eb830f32a41bd0dbd60ea1d2f2caef),
decoded strictly, and recovered P5_S2_R4C_EVIDENCE_20261127.zip,
389192 bytes, SHA-256
ddfc635732c3b2e0449c6ef579a13ebb9339639b18da63bfcb11a9487d0d2401.
All match Arena's reported values. ZIP CRC clean; 65 entries including
18 directory entries, 47 regular files including SHA256SUMS.txt;
46/46 unique manifest digests verified, no unlisted regular files.
Original R4 Markdown inside archive matches section 15 hash exactly.

Original R4C scratch bytes lost on sandbox reset. Archive contains
as-reported record, regenerated baseline experiments on CPython
3.11.2/SQLite 3.40.1, new scripts/logs/JSON/DBs, and reconstructed
c1-prime diff explicitly NOT EXECUTED. Do not promote this to
byte-exact original proof or new patched replay execution. The
archive's stale Linux/A1 pending statements reflect its authoring
context; sections 16-17 and owner authorization supersede them.

Reviewer parsed both scripts with ast (syntax only), parsed JSONs,
and queried all seven included R4C-01 SQLite DB copies read-only.
PRAGMA integrity_check returned ok for each. Stored outcomes/counts:
cap unavailable 37/3 blockers; missing bytes unavailable 37/3;
inadmissible observation unavailable 40/3; excessive history
unavailable 40/3; control halt 36/2; lowconf halt 39/42;
exact40 zero evaluations/blockers and one audit row. Other six
DBs each contain one evaluation and two audit rows. These are
independent observations of delivered regenerated DBs, NOT
independent execution of the application. Reset transaction and
old/new patched replay results remain limited to reported evidence
and exact-source analysis. No further regeneration needed for A1.
Keep c1-prime rejected; B/C/D proof obligations remain open.

Owner authorization verified on PR #49:
https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/49#issuecomment-7206403871
author Muhammed-Fathi, id 209275999, 2026-11-27T00:22:17Z.
Exact five-path scope in section 17 explicitly authorized; A1
implementer must append the decision to PHASE_PROGRESS.md on its
separate branch. Reviewer-prepared transfer patch
P5_S2_A1_Exact_Candidate_B_Artifacts.patch, 189156 bytes,
SHA-256 1b958fe1f2974eba57ce2617620adf5b035ca81c9a01e792be5b0da9782d62dc
rehash matches previous handoff. No additional authorization,
runtime change, implementation acceptance, merge or phase advancement.
A1 remains a separate draft-PR implementation and review track.


## 19. A1 exact-head independent review — 2026-11-27

PR #50 OPEN / DRAFT / NOT MERGED / MERGEABLE. Head
0644a26472a846cf8c9eca0d8b3b058394266f78, one commit ahead and zero
behind exact main 96589dd35df7e8b9ecc690f19f51105a570e1b69.
Owner authorization comment 7206403871 remains the scope authority.
The Arena-assigned branch arena/14e106e4-ai-doctor-followup-agent
satisfies the separate-branch requirement; the proposed feat name
was not used. No rename or history rewrite recommended.

Reviewer reopened original verification kit, computed SHA-256 and
Git blob SHA-1 (blob header plus exact bytes) for the corrected
manifest and both locks. All three exact blob IDs match GitHub at
PR #50 head: pyproject.toml b6afe4b52c5c414678763aaa52736c3fb198e745;
runtime lock 9b244d2df0af03d6f355b7dd45919c037e3dbc0f;
dev lock 42f93837b65cfacaca2f35b912945133338c5ccb.
SHA-256 targets in section 17 unchanged. Both locks preserve every
baseline name/version/marker line (26->55 runtime; 39->67 universal
dev). Exact five authorized paths, docs byte-prefix append-only
by fetched text comparison, no source/tests/guard/migration/CI
changes. Owner authorization recorded in roadmap. No runtime
activation, phase acceptance or merge.

GitHub Actions API confirms run 45918205563, pull_request event,
head_sha 0644a26472a846cf8c9eca0d8b3b058394266f78, completed/success.
Backend Python 3.12 all 14 steps success, frontend Node 22 all 11
steps success. Workflow blob unchanged
859029dbbed8b44bddd648e1ba1affd238d6a678. Reviewer inspected job
metadata and actual workflow, not raw job logs or a fresh local
execution. Arena reports 1526 passed on 3.11.2 supplementary only.
A0 owner Windows 1522 passed/4 skips and Linux 1526 passed/0 skips
are exact-artifact feasibility evidence, not new PR-head runs.

Two narrow evidence wording corrections before owner acceptance:
(1) 67 universal dev pins is not 67 installed on Linux. colorama
is Windows-only and httpx2-jsfetch Emscripten-only, leaving 65
applicable pins on ordinary Linux; report actual inventory only
if preserved, otherwise label count derived from markers.
(2) CI uses editable install, not a non-editable wheel build/import
check. A0 supplies wheel/non-editable evidence for these exact
three blobs with unchanged application source; no fresh non-editable
run at A1 head. Arena's pip wheel attempt exited 1 on unsupported
3.11, an environment blocker, not a regression assertion failure
or a successful check. Append a concise correction to the two
authorized docs and reconcile PR body; no dependency/source changes
or new experiments needed for this correction. Verify refreshed CI
at final head. Explicit owner decision needed whether to reuse
same-artifact Windows A0 evidence for this bounded A1 acceptance
rather than repeat Windows campaign (docs currently list owner
Windows verification as pending); do not silently waive the gate.

Disposition: exact implementation and hosted checks verified at
0644a26; evidence wording correction and owner acceptance decision
pending. All S2-B/C/D issues remain open. No merge recommendation
until remaining evidence/owner conditions satisfied. P5 IN_REVIEW.


## 20. A1 documentation reconciliation and final technical review — 2026-11-27

PR #50 at 2cf593d370008e3023e4a6c8f81e075c2620edb0, OPEN / DRAFT /
NOT MERGED / MERGEABLE; two commits ahead, zero behind main
96589dd35df7e8b9ecc690f19f51105a570e1b69. Delta from 0644a26 is
exactly two authorized docs (+7/+5, zero deletions). Fetched prior
and current texts independently; both append-only, corrections
accurate in substance, PR body contains reconciliation. Earlier
body head label refers to original implementation; authoritative
current PR metadata and this section identify the reviewed head.
All three dependency/manifest blob IDs and contents unchanged
from section 19. Total scope remains five authorized paths.

The 65 installed Linux pins are reported from Arena's preserved
3.11 venv inventory, not independently rerun or supplied as a raw
inventory in this turn; applicable count is independently supported
by A0 and platform markers. Hosted CI editable install is distinct
from wheel evidence. No fresh A1 wheel or Windows execution.
GitHub job metadata confirms push run 45920018408 and PR run
45920025737 each succeeded on 2cf593d: backend Python 3.12
14/14 steps and frontend Node 22 11/11 steps. Raw CI logs not
inspected and no reviewer-local tests rerun.

Technical review complete for bounded A1, conditional on owner
acceptance of reuse of the prior same-artifact Windows A0 evidence
(1522 pass, 4 skips; skip identities not recorded) and A0
non-editable packaging evidence. Reviewer recommends this reuse
because exact three blobs and all application/test/CI paths remain
unchanged; it is not a fresh PR-head Windows or wheel run. No
claim of a full Phase 5 PASS, durability or clinical validation.
Owner must explicitly record that decision and the A1-only
acceptance in the PR thread and roadmap per governance before
merge consideration. Keep reviewer register PR #49 draft and
separate. S2-B/C/D not authorized. Verify any resulting
documentation-only head and refreshed CI before owner merges.


## 21. A1 owner acceptance and integration identity — 2026-11-27

Owner acceptance comment 7207340642 on PR #50, author Muhammed-Fathi,
2026-11-27T01:30:22Z, explicitly authorizes reuse of A0 Windows and
non-editable packaging evidence for A1 only. Acceptance record appended
to the two authorized docs, no implementation changes, at
c8a5d7c0590dd03ab32ba8179b8ddfd509e50158. Exact-head PR CI 45923023056
completed/success, backend 14/14 and frontend 11/11, independently
checked job metadata, not raw logs. Owner merged PR #50 at
2026-11-27T01:39:27Z. Main now 91bbca728273b676f9669e3c39c597c44257849b;
parents 96589dd35df7e8b9ecc690f19f51105a570e1b69 and c8a5d7c0590dd03ab32ba8179b8ddfd509e50158.
Root tree 7f6fc8c5952e6030d0cfea3fbf246843b48c97ec exactly matches the
reviewed PR head tree; GitHub comparison contains zero file differences.
Post-merge CI not yet returned by exact-main workflow lookup; pending,
not failed or waived. A1 merged; final post-merge CI confirmation remains.
PR #49 stays separate and draft. No new runtime import, schema, guard
exception, collection pairing change or Phase 5 acceptance.

Next bounded work: B decision packet only, read-only preparation pending
main CI. Use existing proof obligations P01/P02/P04/P06/P08 and sections
12–15,18; do not reopen A0 or request a wholesale design revision. Resolve
typed F1 non-persistable refusal and historical replay, S0 issue
representability boundary, transaction/ownership matrix, audit semantic
identity, canonical schema/DDL parity and reset contract before B code.
Owner must explicitly ratify concrete decisions and paths (including
D-09 remeasurement permission if tests change). Preserve all C/D
obligations and D-15 unchanged. No B implementation authorization yet.


## 22. A1 post-merge verification and B preparation — 2026-11-27

Direct GitHub Actions branch/main and head_sha queries confirm push run
45923806071 completed/success on exact main
91bbca728273b676f9669e3c39c597c44257849b, tree unchanged from accepted
PR #50. Commit check-runs and job metadata agree. Backend Python 3.12
14/14 steps successful; frontend Node 22 11/11 steps successful.
The connector's commit-workflow convenience query returned an empty list;
direct Actions API resolved that discrepancy. No fresh local execution
or raw job logs inspected. A1 integration verification complete.
Owner acceptance remains bounded to A1; P5 IN_REVIEW / NOT_ACCEPTED.

B next: prepare only a focused decision packet using existing sections
3–7,12–15,18 and current exact source. No repeat A0, full design revision,
tracked changes, migration or runtime implementation until explicit
owner authorization. Resolve P01/P02/P04/P06/P08 and distinguish S0
issue-cardinality handling from deferred D execution. Preserve old F1
1.0.0 replay, reject c1-prime, require typed non-persistable refusal;
establish canonical schema, transaction and reset authority, semantic
audit collision checks, bounded tests and exact allowed paths.
D-09 remeasurement and D-15 scope are independent decisions, not waived.
Keep PR #49 draft. S2-B/C/D implementation remains NOT_STARTED.
