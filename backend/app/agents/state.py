"""P5-S0 typed shared-state contract — structural models only (no graph).

This is the first *executable* definition of the Pydantic v2 shared state
proposed in ``docs/contracts/STATE_AND_GRAPH_CONTRACT.md`` §3, reconciled with
the merged F0 run foundation, the F1 run-bound gate receipt, the F2 evaluable
evidence bridge and the sealed RB3 review-persistence receipt. The
reconciliation matrix, the decisions taken and the open owner questions are in
``docs/phase-reports/P5_S0_TYPED_STATE_IMPLEMENTATION_REVIEW_20261123.md``.

What this module is
-------------------
* Strict, frozen, JSON-round-trippable Pydantic v2 models. Unknown fields are
  rejected; every collection and numeric is bounded; every identifier is a
  real canonical UUID / SHA-256 / UTC instant / version token; and cross-field
  invariants are checked by validators, never repaired.
* Pure data. No I/O, no clock reads, no database, no HTTP, no model runtime.
  The only project imports are the shared vocabulary enums in
  ``app.core.enums`` and the RB3 denial-reason enum in
  ``app.schemas.p4_rb3_review_persistence`` (both pure constant modules).

Four assurance levels — never conflated
---------------------------------------
Passing validation here proves exactly **one** of these and no more:

1. ``SHAPE_VALIDATED`` — the payload is a well-formed, bounded, closed-vocabulary
   shape. This is the only level this module can grant.
2. ``IDENTITY_CONSISTENT`` — the identity *references* inside one payload agree
   with each other (run/patient/doctor scope, gate binding, selection binding).
   The validators below check this structurally, but a structurally consistent
   payload can still reference rows that do not exist.
3. ``EVIDENCE_REVALIDATED`` — the referenced evidence was independently re-read
   and re-hashed from the authoritative store. **Not implemented in S0.**
4. ``RUNTIME_AUTHORIZED`` — an authenticated, authorized runtime decided to act.
   **Not implemented in S0**, and no field in this module can express it.

What this module is NOT
----------------------
* Not a graph, checkpointer, node, tool adapter, model client, API, task or
  notification implementation. None of those modules are imported here.
* Not an authority. Passing validation proves *shape*, never authentication,
  authorization, clinical grounding, execution permission or policy approval.
  The honesty literals (``runtime_evaluable=False``, ``policy_status=
  "unapproved"``, ...) cannot be flipped through validation, but
  ``model_copy(update=...)`` bypasses validation by design: consumers must
  build state through validation and re-check authorization out of band.
* Frozen models and private constructors are *data-integrity* aids, not a
  security boundary. ``frozen=True`` prevents field rebinding; it does **not**
  make list contents deeply immutable.

ACADEMIC / SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    TypeAdapter,
    WithJsonSchema,
    model_validator,
)

from app.core.enums import (
    MEASURE_UNITS,
    ExtractionPath,
    FactField,
    MeasureType,
    ObservationSource,
    Preprocessing,
    QualityFlag,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.schemas.p4_rb3_review_persistence import RB3DenialReason

# --- contract versions pinned by this module (drift-checked against F0) ---------------#

#: Version of *this* state contract (``STATE_AND_GRAPH_CONTRACT.md`` §2).
STATE_SCHEMA_VERSION = "1.0.0"
#: Graph shape + node semantics the state is written for (§2).
WORKFLOW_VERSION = "1.0.0"
#: Demo rule-policy reference (not an activation claim).
POLICY_REFERENCE_VERSION = "demo-policy-1.1.0"
#: Fixed educational label every draft must carry (``REQ-SEC-05``).
DEMO_NOTICE = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"

# --- upstream producer maxima (documented bounded projection contract) -----------------#
#
# Every collection bound below is the *accepted producer's* maximum, so a valid
# upstream payload is never silently truncated or rejected. Where two producers
# feed one collection the bound is their documented sum.

#: F0 ``MAX_SELECTED_DOCUMENTS`` (``p4_rb3_review_persistence``).
MAX_SELECTED_DOCUMENTS = 5
#: F2 ``MAX_CURRENT_OBSERVATIONS`` — selected-current rows.
MAX_SELECTED_CURRENT = 6
#: F0 ``MAX_MANIFEST_OBSERVATIONS`` — manifest rows.
MAX_MANIFEST_OBSERVATIONS = 20
#: F0 ``MAX_MANIFEST_OMISSIONS``.
MAX_MANIFEST_OMISSIONS = 20
#: F2 ``MAX_FACTS`` — extracted *and* verified fact projections.
MAX_FACTS = 40
#: F2 ``MAX_HISTORY_OBSERVATIONS`` — source/history rows.
MAX_HISTORY_OBSERVATIONS = 100
#: F1 ``MAX_GATE_FACTS`` (also the persisted ``blocking_fact_count`` CHECK bound).
MAX_BLOCKING_FACTS = 40
#: RB3 ``MAX_PERSISTED_ITEMS`` / ``MAX_PERSISTED_LINKS`` / ``MAX_EXCLUSIONS``.
MAX_PERSISTED_ITEMS = 12
MAX_PERSISTED_LINKS = 24
MAX_MERGED_EXCLUSIONS = 200
#: Contract §8 collection bounds (state-only, no upstream producer).
MAX_EXTRACTION_ATTEMPTS = 10
MAX_EVENTS = 40
MAX_PENDING_TASKS = 5
MAX_ERRORS = 10
#: Selected-current (6) + source/history (100) observations in one projection.
MAX_OBSERVATIONS = MAX_SELECTED_CURRENT + MAX_HISTORY_OBSERVATIONS
#: At most one comparison per current observation per producer window.
MAX_COMPARISONS = MAX_SELECTED_CURRENT * 2
#: The accepted window widths. F2 implements ``HISTORY_LOOKBACK_DAYS = 365``
#: (``p5_evidence_bridge``) and the RB1 run-bound preview implements
#: ``POLICY_LOOKBACK_DAYS = 90`` (``p4_run_bound_preview``). They are pinned
#: constants, never configuration, and a baseline outside the labelled window is
#: not a member of that window at all (owner decision D-04).
F2_HISTORY_LOOKBACK_DAYS = 365
RB1_HISTORY_LOOKBACK_DAYS = 90

# --- primitive types: real validation, not permissive regex ---------------------------#

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

#: Versions actually emitted by the accepted producers. ``WorkflowRun.id`` and
#: every ``new_uuid()`` primary key are v4; the *seeded synthetic observation*
#: fixtures are v5 (``data/synthetic/observations.json`` — all 17 rows), and the
#: RB4 run-backed GOLD comparisons therefore carry v5 baseline identities.
#: Restricting stored identities to v4 would reject accepted GOLD/RB4 evidence.
_STORED_UUID_VERSIONS = frozenset({4, 5})


def _canonical_uuid(value: str, *, versions: frozenset[int], label: str) -> str:
    """Accept only the canonical lowercase hyphenated RFC-4122 form of a UUID."""
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("not a UUID") from exc
    if str(parsed) != value or parsed.variant != uuid.RFC_4122:
        raise ValueError(f"expected a canonical lowercase RFC-4122 {label}")
    if parsed.version not in versions:
        raise ValueError(f"expected a {label} (UUID versions {sorted(versions)})")
    return value


def _stored_uuid(value: str) -> str:
    return _canonical_uuid(value, versions=_STORED_UUID_VERSIONS, label="stored identity UUID")


def _run_uuid(value: str) -> str:
    """Run identity: genuine F0 UUIDv4 (``WorkflowRun.id`` default ``new_uuid``)."""
    return _canonical_uuid(value, versions=frozenset({4}), label="run identity UUIDv4")


def _task_uuid(value: str) -> str:
    """Derived task identity: UUIDv5 only (``uuid5(namespace, action_key)``)."""
    return _canonical_uuid(value, versions=frozenset({5}), label="derived task UUIDv5")


def _sha256_text(value: str) -> str:
    if value == "0" * 64:
        raise ValueError("an all-zero digest is a placeholder, not a digest")
    return value


def _utc_instant(value: str) -> str:
    """Accept only ``YYYY-MM-DDTHH:MM:SSZ`` (the persisted P2/F0 storage format)."""
    try:
        parsed = datetime.strptime(value, _UTC_FORMAT)
    except ValueError as exc:
        raise ValueError("expected an ISO-8601 UTC instant 'YYYY-MM-DDTHH:MM:SSZ'") from exc
    if parsed.strftime(_UTC_FORMAT) != value:
        raise ValueError("non-canonical UTC instant (zero padding required)")
    return value


def _parse_instant(value: str) -> datetime:
    """Parse an already-validated ``YYYY-MM-DDTHH:MM:SSZ`` instant (no I/O)."""
    return datetime.strptime(value, _UTC_FORMAT)


def _calendar_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("expected a real calendar date 'YYYY-MM-DD'") from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("non-canonical calendar date")
    return value


def _decimal_text(value: Decimal) -> str:
    """Canonical JSON text for a decimal, **independent of the ambient context**.

    ``Decimal.normalize()`` and ``format(value, "f")`` both consult the ambient
    ``decimal`` context (precision, rounding, traps), so the same value could
    serialise differently — or lose significant digits — under a hostile
    context. This reads ``as_tuple()`` only, which is context-free.
    """
    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):  # NaN / sNaN / Infinity
        raise ValueError("non-finite decimal")
    text = "".join(str(digit) for digit in digits)
    if exponent >= 0:
        int_part, frac_part = text + "0" * exponent, ""
    else:
        cut = len(text) + exponent
        if cut > 0:
            int_part, frac_part = text[:cut], text[cut:]
        else:
            int_part, frac_part = "0", "0" * (-cut) + text
    int_part = int_part.lstrip("0") or "0"
    frac_part = frac_part.rstrip("0")
    rendered = int_part if not frac_part else f"{int_part}.{frac_part}"
    return f"-{rendered}" if sign and rendered != "0" else rendered


def _decimal_string_only(value: object) -> object:
    """Reject JSON *numbers* for exact quantities (owner decision D-07).

    A JSON number reaches Pydantic as a Python ``int``/``float``; a binary float
    is a potentially lossy representation of a decimal quantity. Exact values
    must therefore arrive as JSON decimal **strings**. A Python ``Decimal`` is
    still accepted in Python mode.
    """
    if isinstance(value, (bool, int, float)):
        raise ValueError("exact decimals must be JSON decimal strings, never JSON numbers")
    if isinstance(value, str):
        # Construct explicitly: ``Decimal(text)`` never consults the ambient
        # context, and pydantic's strict mode then receives a real ``Decimal``.
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("exact decimals must be a finite decimal string") from exc
        if not parsed.is_finite():
            raise ValueError("exact decimals must be finite")
        return parsed
    return value


#: Explicit, ambient-independent context for exact subtraction (owner decision D-04/R04).
#: ``prec`` is far above the persisted 10-digit/4-decimal bound, so subtraction of
#: any two admissible values is exact and never rounds.
_EXACT_CONTEXT = Context(
    prec=60,
    rounding=ROUND_HALF_EVEN,
    traps=[InvalidOperation],
)


def exact_delta(current: Decimal, baseline: Decimal) -> Decimal:
    """``current - baseline`` under an explicit context — never the ambient one."""
    return _EXACT_CONTEXT.subtract(current, baseline)


#: Stored identity (patient, doctor, document, observation, fact, issue, evaluation...).
#: Accepts the canonical UUIDv4 **and** UUIDv5 forms actually emitted by the
#: accepted producers; every other variant/version is rejected.
Uuid = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(_stored_uuid)]
#: Run identity (``WorkflowRun.id``): genuine F0 UUIDv4 only.
RunUuid = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(_run_uuid)]
#: Derived task identity (``uuid5(namespace, action_key)``): UUIDv5 only.
TaskUuid = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(_task_uuid)]
#: Lowercase hex SHA-256 digest; the all-zero placeholder is rejected.
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$"), AfterValidator(_sha256_text)]
#: Persisted UTC instant, exactly ``YYYY-MM-DDTHH:MM:SSZ`` (``DATA_DICTIONARY`` §1).
Iso = Annotated[str, Field(min_length=20, max_length=20), AfterValidator(_utc_instant)]
#: SemVer 2.0.0 numeric identifiers (no leading zeros), bounded to the persisted width.
SemVer = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", max_length=12)]
#: Closed fact→observation mapping table version (``map-<major>.<minor>.<patch>``, P0-R12).
MappingVersion = Annotated[
    str, Field(pattern=r"^map-(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", max_length=16)
]
#: Demo policy reference ``<name>-<semver>`` (e.g. ``demo-policy-1.1.0``); a version, not activation.
PolicyVersion = Annotated[
    str,
    Field(
        pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*-(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$",
        max_length=24,
    ),
]
#: Prompt/template tag (e.g. ``draft-v1``): a bounded **32-character** lowercase token.
#: NOTE: ``WorkflowRun`` has **no** ``prompt_version`` column, so F0 persists nothing
#: here; this is a future contract slot, not an authority (owner decision D-06).
PromptVersion = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$", max_length=32)]
#: Snake_case machine reason code (F1/F2 exclusion and reason vocabularies).
ReasonCode = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
#: Typed error code ``E_<UPPER_SNAKE>`` (``app.core.errors.ErrorCode`` vocabulary shape).
ErrorCode = Annotated[str, Field(pattern=r"^E_[A-Z0-9_]{2,45}$", max_length=48)]
#: Bounded lowercase machine token (checkpoint ids, model metadata keys).
Token = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")]
#: Exact positive quantity (observation values): JSON decimal **string** only, never a float.
ExactDecimal = Annotated[
    Decimal,
    BeforeValidator(_decimal_string_only),
    Field(gt=0, max_digits=10, decimal_places=4),
    PlainSerializer(_decimal_text, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string"}),
]
#: Exact signed difference; may be negative, never non-finite.
DeltaDecimal = Annotated[
    Decimal,
    BeforeValidator(_decimal_string_only),
    Field(max_digits=10, decimal_places=4),
    PlainSerializer(_decimal_text, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string"}),
]
#: Model-metadata value (provider/model/latency summary text only; bounded).
MetadataValue = Annotated[str, Field(min_length=1, max_length=128)]
#: Engine-reported probability in ``[0, 1]``; ``NaN``/``inf`` are rejected.
Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


# --- assurance levels -----------------------------------------------------------------#


class AssuranceLevel(StrEnum):
    """What a successful validation actually proves — and what it does not.

    Only ``SHAPE_VALIDATED`` is granted by this module. ``IDENTITY_CONSISTENT``
    is a *structural* property the validators below also check, but it never
    implies the referenced rows exist. ``EVIDENCE_REVALIDATED`` and
    ``RUNTIME_AUTHORIZED`` are runtime obligations that no field here can carry.
    """

    SHAPE_VALIDATED = "shape_validated"
    IDENTITY_CONSISTENT = "identity_consistent"
    EVIDENCE_REVALIDATED = "evidence_revalidated"
    RUNTIME_AUTHORIZED = "runtime_authorized"


# --- vocabularies ---------------------------------------------------------------------#


class RunStatus(StrEnum):
    """``workflow_run.status`` — the app DB is the only authority (``P0-R09``)."""

    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_VERIFICATION = "needs_verification"  # halted, resumable
    AWAITING_DECISION = "awaiting_decision"  # interrupted, resumable
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"  # halted, resumable
    FAILED_TERMINAL = "failed_terminal"


#: Statuses that carry a ``halt_reason`` (contract §4.2, §6).
HALTED_STATUSES = frozenset(
    {RunStatus.NEEDS_VERIFICATION, RunStatus.FAILED_RETRYABLE, RunStatus.FAILED_TERMINAL}
)


class HaltReason(StrEnum):
    UNVERIFIED_FACTS = "unverified_facts"
    MODEL_FAILED = "model_failed"
    RETRY_EXHAUSTED = "retry_exhausted"
    NEEDS_HUMAN_DECISION = "needs_human_decision"


class TrustBasis(StrEnum):
    SELF_REPORTED = "self_reported"
    DOCTOR_VERIFIED = "doctor_verified"
    MIXED = "mixed"


class ComparisonWindow(StrEnum):
    """Which accepted producer's lookback produced a comparison (owner decision D-04).

    F2's implemented history policy is 365 days; the RB1 run-bound preview is an
    independently computed 90-day demo comparison. They are different rule
    inputs and must never be relabelled as one another. This is a *label*, not a
    configurable runtime lookback and not a policy activation.
    """

    F2_365D = "f2-history-365d-v1"
    RB1_90D = "rb1-demo-90d-v1"


class IncomparableReason(StrEnum):
    """Union of the contract §3 reasons and the P4/F2 codes (never silently dropped).

    F2 actually emits only ``no_baseline`` and ``not_admissible``. ``stale_baseline``
    is **reserved contract vocabulary** retained so a contract-conformant producer
    stays representable; no accepted service emits it today (owner decision D-03).
    """

    NO_BASELINE = "no_baseline"
    UNIT_MISMATCH = "unit_mismatch"
    STALE_BASELINE = "stale_baseline"
    MISSING_TIMESTAMP = "missing_timestamp"
    NOT_ADMISSIBLE = "not_admissible"


#: Reasons the F2 bridge actually emits for a comparison (``p5_evidence_bridge``).
F2_EMITTED_INCOMPARABLE = frozenset(
    {IncomparableReason.NO_BASELINE, IncomparableReason.NOT_ADMISSIBLE}
)


class ExclusionReason(StrEnum):
    """Closed set actually emitted by the F2 bridge (source checks + admissibility)."""

    VALIDATION_REJECTED = "validation_rejected"
    UNIT_MISMATCH = "unit_mismatch"
    MISSING_TIMESTAMP = "missing_timestamp"
    FUTURE_TIMESTAMP = "future_timestamp"
    VERIFIED_LINEAGE_UNAVAILABLE = "verified_lineage_unavailable"
    VERIFIED_MAPPING_UNPROVEN = "verified_mapping_unproven"
    STORED_TRUST_SOURCE_MISMATCH = "stored_trust_source_mismatch"
    MALFORMED_HISTORY = "malformed_history"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProvenanceKind(StrEnum):
    DOCUMENT_SPAN = "document_span"
    OBSERVATION = "observation"
    CHECKIN_NOTE = "checkin_note"


class ObservationRole(StrEnum):
    """Whether a row is a selected *current* value or *history* (R05).

    A history row can never silently become a selected current: a comparison's
    ``current_observation_id`` must resolve to a ``SELECTED_CURRENT`` row and its
    ``baseline_observation_id`` to a ``HISTORY`` row.
    """

    SELECTED_CURRENT = "selected_current"
    HISTORY = "history"


class Extractor(StrEnum):
    PYPDF = "pypdf"
    TESSERACT = "tesseract"
    MANUAL = "manual"
    PATIENT_FORM = "patient_form"


class IssueType(StrEnum):
    """Pre-verification blockers only (``VI-001``…``VI-006``)."""

    VI_001 = "VI-001"
    VI_002 = "VI-002"
    VI_003 = "VI-003"
    VI_004 = "VI-004"
    VI_005 = "VI-005"
    VI_006 = "VI-006"


class ReviewRuleId(StrEnum):
    """Post-verification demo review prompts; retired ``DR-002/004/007/010`` are absent (P0-R03)."""

    DR_001 = "DR-001"
    DR_003 = "DR-003"
    DR_005 = "DR-005"
    DR_006 = "DR-006"
    DR_008 = "DR-008"
    DR_009 = "DR-009"


class ReviewHint(StrEnum):
    DATA_QUALITY = "data_quality"
    VERIFICATION_NEEDED = "verification_needed"
    CHANGE_TO_REVIEW = "change_to_review"


class ReviewItemState(StrEnum):
    OPEN = "open"
    DECIDED = "decided"


class DraftProvider(StrEnum):
    OLLAMA = "ollama"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class DraftExecutionStatus(StrEnum):
    MODEL_OK = "model_ok"
    MODEL_INVALID_SCHEMA = "model_invalid_schema"
    MODEL_TIMEOUT = "model_timeout"
    MODEL_UNAVAILABLE = "model_unavailable"
    FALLBACK_NO_MODEL = "fallback_no_model"


class ApprovalChoice(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class NodeName(StrEnum):
    """The eleven graph nodes of contract §4.1 (``node_event.node`` vocabulary)."""

    INTAKE_VALIDATE = "intake_validate"
    DOCUMENT_EXTRACT = "document_extract"
    EXTRACTION_TRIAGE = "extraction_triage"
    FACT_VERIFY_GATE = "fact_verify_gate"
    MONITOR_COMPARE = "monitor_compare"
    REVIEW_RULES = "review_rules"
    DRAFT_SUMMARY = "draft_summary"
    DRAFT_VALIDATION = "draft_validation"
    CLINICIAN_APPROVAL = "clinician_approval"
    FINALIZE_ACTIONS = "finalize_actions"
    HALTED = "halted"


class NodeOutcome(StrEnum):
    OK = "ok"
    HALTED = "halted"
    INTERRUPTED = "interrupted"
    RETRIED = "retried"
    FAILED = "failed"


class ToolName(StrEnum):
    """Closed tool allowlist of contract §4.1."""

    EXTRACT_DOCUMENT = "extract_document"
    GET_DOCUMENT_PAGES = "get_document_pages"
    VALIDATE_STRUCTURED_FIELDS = "validate_structured_fields"
    READ_OBSERVATIONS = "read_observations"
    COMPARE_OBSERVATIONS = "compare_observations"
    READ_VERIFIED_FACTS = "read_verified_facts"
    EVALUATE_DEMO_REVIEW_RULES = "evaluate_demo_review_rules"
    DRAFT_GROUNDED_SUMMARY = "draft_grounded_summary"
    CREATE_IN_APP_TASK = "create_in_app_task"
    LIST_DUE_TASKS = "list_due_tasks"


#: Per-node tool allowlist (contract §4.1 "Tools (allowlist)" column, verbatim).
NODE_TOOLS: dict[NodeName, frozenset[ToolName]] = {
    NodeName.INTAKE_VALIDATE: frozenset(),
    NodeName.DOCUMENT_EXTRACT: frozenset(
        {
            ToolName.EXTRACT_DOCUMENT,
            ToolName.GET_DOCUMENT_PAGES,
            ToolName.VALIDATE_STRUCTURED_FIELDS,
        }
    ),
    NodeName.EXTRACTION_TRIAGE: frozenset(),
    NodeName.FACT_VERIFY_GATE: frozenset(),
    NodeName.MONITOR_COMPARE: frozenset(
        {ToolName.READ_OBSERVATIONS, ToolName.COMPARE_OBSERVATIONS}
    ),
    NodeName.REVIEW_RULES: frozenset(
        {ToolName.READ_VERIFIED_FACTS, ToolName.EVALUATE_DEMO_REVIEW_RULES}
    ),
    NodeName.DRAFT_SUMMARY: frozenset(
        {ToolName.READ_VERIFIED_FACTS, ToolName.DRAFT_GROUNDED_SUMMARY}
    ),
    NodeName.DRAFT_VALIDATION: frozenset(),
    NodeName.CLINICIAN_APPROVAL: frozenset(),
    NodeName.FINALIZE_ACTIONS: frozenset({ToolName.CREATE_IN_APP_TASK, ToolName.LIST_DUE_TASKS}),
    NodeName.HALTED: frozenset(),
}


class TriagePath(StrEnum):
    """Trace path vocabulary (contract §3/§4.2, OpenAPI ``TriageEventDetail``).

    Distinct from ``app.core.enums.TriagePath`` (the P3 *service* route), whose
    ``proceed`` maps onto ``text_layer`` or ``ocr_direct`` here (§4.2).
    """

    TEXT_LAYER = "text_layer"
    OCR_DIRECT = "ocr_direct"
    OCR_PREPROCESS_RETRY = "ocr_preprocess_retry"
    FLAG_FOR_HUMAN = "flag_for_human"


class PathReason(StrEnum):
    TEXT_LAYER_AVAILABLE = "text_layer_available"
    CONFIDENCE_OK = "confidence_ok"
    LOW_CONFIDENCE = "low_confidence"
    OCR_TRANSIENT_ERROR = "ocr_transient_error"
    RETRY_EXHAUSTED = "retry_exhausted"


class ValidationOutcome(StrEnum):
    ACCEPT = "accept"
    REPAIR_REQUESTED = "repair_requested"
    FALLBACK_SELECTED = "fallback_selected"


class ViolationCode(StrEnum):
    SCHEMA_INVALID = "schema_invalid"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    PROHIBITED_CONTENT = "prohibited_content"
    MISSING_DISCLAIMER = "missing_disclaimer"
    UNGROUNDED_NUMBER = "ungrounded_number"
    PATIENT_ADDRESSING = "patient_addressing"


#: Trace gate decision: the **two-valued** normative ``GateDetail`` contract
#: (``node_event.gate_decision CHECK IN ('proceed','halt')``). The F1
#: ``unavailable`` outcome is an *evaluation failure*, never a trace decision —
#: a proceed/halt value is never fabricated to satisfy the trace schema
#: (owner decision D-01). Its routing is an S2 obligation.
TraceGateDecision = Literal["proceed", "halt"]


class DetailKind(StrEnum):
    TRIAGE = "triage"
    VALIDATION = "validation"
    GATE = "gate"
    FINALIZE = "finalize"


#: Nodes that make a bounded decision → ``detail`` is mandatory and must match (P0-R08).
DETAIL_KIND_BY_NODE: dict[NodeName, DetailKind] = {
    NodeName.EXTRACTION_TRIAGE: DetailKind.TRIAGE,
    NodeName.FACT_VERIFY_GATE: DetailKind.GATE,
    NodeName.DRAFT_VALIDATION: DetailKind.VALIDATION,
    NodeName.FINALIZE_ACTIONS: DetailKind.FINALIZE,
}


class GateDecision(StrEnum):
    """F1 receipt decision set (``p5_run_gate.RunGateReceipt.decision``).

    Precedence in the accepted producer is ``unavailable`` > ``halt`` > ``proceed``:
    ``decision = "unavailable" if unavailable else "halt" if ordered else "proceed"``.
    ``ordered`` is the set of recorded ``RunGateIssue`` rows, so a **halt** is
    decided by recorded blocking issues — and a genuine halt can therefore have
    **zero** distinct blocking facts when every blocker is document-level.
    """

    PROCEED = "proceed"
    HALT = "halt"
    UNAVAILABLE = "unavailable"


class GateUnavailableReason(StrEnum):
    """Closed set emitted by ``p5_run_gate._evaluate_locked`` (``unavailable = "…"``)."""

    RUN_EXECUTION_STATE_UNEXPECTED = "run_execution_state_unexpected"
    UNSUPPORTED_RUN_VERSION = "unsupported_run_version"
    INVALID_RUN_CLOCK = "invalid_run_clock"
    SOURCE_BYTES_UNAVAILABLE = "source_bytes_unavailable"
    SOURCE_BYTES_CHANGED_DURING_GATE = "source_bytes_changed_during_gate"
    SELECTED_DOCUMENT_CHANGED = "selected_document_changed"
    SELECTED_DOCUMENT_NOT_VERIFIED = "selected_document_not_verified"
    SELECTED_DOCUMENT_PREFLIGHT_UNPROVEN = "selected_document_preflight_unproven"
    SELECTED_DOCUMENT_HAS_NO_ACTIVE_FACTS = "selected_document_has_no_active_facts"
    SELECTED_OBSERVATION_MISSING = "selected_observation_missing"
    SELECTED_OBSERVATION_INADMISSIBLE = "selected_observation_inadmissible"
    SELECTED_RECOVERY_LINEAGE_CHANGED = "selected_recovery_lineage_changed"
    FACT_PATIENT_SCOPE_CHANGED = "fact_patient_scope_changed"
    HISTORICAL_OMISSION_CHANGED = "historical_omission_changed"
    INVALID_QUALITY_FLAGS = "invalid_quality_flags"
    TOO_MANY_BLOCKING_FACTS = "too_many_blocking_facts"
    TOO_MANY_PATIENT_OBSERVATIONS = "too_many_patient_observations"
    TOO_MANY_SELECTED_FACTS = "too_many_selected_facts"
    UNRESOLVED_P3_VI002 = "unresolved_p3_vi002"
    UNSUPPORTED_OPEN_ISSUE_TYPE = "unsupported_open_issue_type"


#: F2 bridge history policy actually implemented (``p5_evidence_bridge`` constants).
F2_CONTRACT_VERSION = Literal["2.0.0"]
F2_HISTORY_POLICY = Literal["f2-history-365d-v1"]
#: RB1 run-bound preview lookback (``p4_run_bound_preview.POLICY_LOOKBACK_DAYS``).
RB1_LOOKBACK_DAYS = Literal[90]
#: RB3 receipt contract actually implemented (``p4_rb3_review_persistence`` constants).
RB3_RECEIPT_CONTRACT_VERSION = Literal["p4-rb3-receipt-1.0.0"]
RB3_FINGERPRINT_VERSION = Literal["rb3-full-input-1.0.0"]
#: The policy reference SHA the durable RB3 service pins in the database CHECK
#: (``review_evaluation.policy_reference_sha256``).
RB3_POLICY_REFERENCE_SHA256 = "f3bdad3f6a958b65b50598910cc91501dcc53ca210ff90d2e09b14695cb6bd36"
#: The durable RB3 service always records this value (DB CHECK ``review_eval_dr006_policy_pinned``).
RB3_DR006_POLICY = "prohibited_denied"
#: Doctor-authored omission reason fixed by the F0 schema (``RunSourceOmission`` CHECK).
OMISSION_REASON = Literal["selected_separate_recovery_source"]


class Strict(BaseModel):
    """Shared configuration: unknown fields rejected, strict input, frozen instances.

    ``frozen=True`` prevents field rebinding; list contents are **not** deeply
    immutable, so nodes must build new lists instead of mutating in place. See
    ``SharedGraphState.revalidate`` for the genuine full-revalidation path.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def _unique(values: list[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")


def _sorted_unique(values: list[str], label: str) -> None:
    _unique(values, label)
    if values != sorted(values):
        raise ValueError(f"{label} must be in ascending canonical order")


def _sorted_exclusions(
    items: Sequence[PersistedExclusionRef],
) -> list[PersistedExclusionRef]:
    """``sorted(set(...))`` over ``(observation_id, reason_code)``, as RB3 does."""
    unique = {(item.observation_id, item.reason_code) for item in items}
    return [
        PersistedExclusionRef(observation_id=observation_id, reason_code=reason_code)
        for observation_id, reason_code in sorted(unique)
    ]


def _distinct_fact_count(issues: Sequence[GateIssueRef | TraceGateIssue]) -> int:
    """``len({fact for item in ordered for fact in item.fact_ids})`` — the F1 recipe."""
    return len({fact for item in issues for fact in item.fact_ids})


# --- evidence --------------------------------------------------------------------------#


class ProvenanceRef(Strict):
    """One typed evidence pointer. ``raw_text`` is bounded and lives **only** here.

    Owner decision D-02: bounded raw text is permitted inside the evidence
    model and never inside a trace detail. This grants no document-span
    persistence authority — no page span, source text, OCR confidence or human
    verification is fabricated by this shape.
    """

    kind: ProvenanceKind
    document_id: Uuid | None = None
    page_index: int | None = Field(default=None, ge=0, le=200)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    observation_id: Uuid | None = None
    raw_text: str | None = Field(default=None, max_length=500)
    extractor: Extractor | None = None

    @model_validator(mode="after")
    def _kind_shape(self) -> Self:
        span_only = (self.page_index, self.char_start, self.char_end)
        if self.kind is ProvenanceKind.DOCUMENT_SPAN:
            if self.document_id is None or self.observation_id is not None:
                raise ValueError("document_span requires document_id and forbids observation_id")
            if (
                self.char_start is not None
                and self.char_end is not None
                and self.char_end <= self.char_start
            ):
                raise ValueError("char_end must be greater than char_start")
            spans = (self.page_index, self.char_start, self.char_end)
            if any(bound is not None for bound in spans) and not all(
                bound is not None for bound in spans
            ):
                raise ValueError(
                    "a document_span records page_index, char_start and char_end together"
                )
        else:
            if self.observation_id is None or self.document_id is not None:
                raise ValueError(f"{self.kind} requires observation_id and forbids document_id")
            if any(bound is not None for bound in span_only):
                raise ValueError(f"{self.kind} carries no page or character span")
        return self


class ExtractedFact(Strict):
    """Raw extraction output. Never admissible downstream (``REQ-SEC-04``)."""

    fact_id: Uuid
    patient_id: Uuid
    document_id: Uuid
    field_name: FactField
    raw_text: str = Field(max_length=300)
    normalized_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    quality_flags: list[QualityFlag] = Field(default_factory=list, max_length=7)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    corrected_from_fact_id: Uuid | None = None
    provenance: ProvenanceRef
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    verification_note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _decision_shape(self) -> Self:
        # A partial pair is rejected outright: a decision is all-or-nothing.
        decided = self.verified_by is not None and self.verified_at is not None
        if (self.verified_by is not None or self.verified_at is not None) and not decided:
            raise ValueError("verified_by and verified_at are recorded together")
        if self.verification_status is VerificationStatus.PENDING and decided:
            raise ValueError("a pending fact cannot carry a doctor decision")
        if self.verification_status is not VerificationStatus.PENDING and not decided:
            raise ValueError("a decided fact requires verified_by and verified_at")
        return self


class VerifiedFact(Strict):
    """A fact the accepted F2 bridge projects as verified.

    **Exact projection sources** (owner review R01) — the F2 ``VerifiedFactV2``
    DTO supplies only the first eight fields:

    * ``fact_id``, ``document_id``, ``field_name``, ``normalized_value``,
      ``unit``, ``corrected_from_fact_id``, ``verification_status`` and
      ``trust_basis`` come from ``p5_review_evidence.VerifiedFactV2``.
    * ``patient_id`` is projected from the stored ``ExtractedFact.patient_id``
      (the F2 DTO omits it). Absent means "not projected", never "unknown".
    * ``verified_by`` / ``verified_at`` are projected from the stored
      ``FactVerification.verified_by_user_id`` / ``decided_at`` (the F2 DTO
      omits them). Absent means "not projected".
    * ``evidence`` is an optional bounded projection; the F2 DTO carries none,
      so no page span or source text is ever fabricated here.

    Validating this shape does **not** re-verify anything: ``verification_status``
    and ``trust_basis`` are producer-asserted literals, not an independent check.
    """

    fact_id: Uuid
    document_id: Uuid
    field_name: FactField
    normalized_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    corrected_from_fact_id: Uuid | None = None
    verification_status: Literal["verified"] = "verified"
    trust_basis: Literal["doctor_verified"] = "doctor_verified"
    patient_id: Uuid | None = None
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _lineage(self) -> Self:
        if self.corrected_from_fact_id is not None and self.corrected_from_fact_id == self.fact_id:
            raise ValueError("a fact cannot be corrected from itself")
        if (self.verified_by is None) != (self.verified_at is None):
            raise ValueError("verified_by and verified_at are projected together")
        return self


class ObservationView(Strict):
    """Patient-scoped measurement with explicit trust and recorded provenance.

    Reconciles the P0 ``ObservationView`` with the F2 ``ObservationV2``: the
    value is an exact ``Decimal`` and the recorded ``source_fact_id`` lineage
    travels with the row (``REQ-DATA-04``).

    **Projection sources:** every field except ``role`` and ``source_document_id``
    is a stored ``Observation`` column (``verified_by`` ←
    ``verified_by_user_id``). ``source_document_id`` is projected from the F2
    ``ObservationV2`` DTO, because ``Observation`` has no such column — it is
    resolved through ``source_fact_id`` → ``ExtractedFact.document_id``.
    ``role`` is a state-level label (selected current vs history), not a column.
    """

    observation_id: Uuid
    patient_id: Uuid
    role: ObservationRole
    measure_type: MeasureType
    value: ExactDecimal
    unit: Unit
    measured_at: Iso
    source: ObservationSource
    validation: ValidationState
    trust_level: TrustLevel
    verified_by: Uuid | None = None
    verified_at: Iso | None = None
    source_fact_id: Uuid | None = None
    source_document_id: Uuid | None = None

    @model_validator(mode="after")
    def _trust_and_provenance(self) -> Self:
        if self.unit not in MEASURE_UNITS[self.measure_type]:
            raise ValueError("unit does not match the measure type's closed unit")
        doctor_verified = self.trust_level is TrustLevel.DOCTOR_VERIFIED
        if doctor_verified != (self.verified_by is not None and self.verified_at is not None):
            raise ValueError(
                "doctor_verified requires verified_by and verified_at; otherwise neither"
            )
        # A partial pair is rejected even when the trust label happens to agree.
        if (self.verified_by is None) != (self.verified_at is None):
            raise ValueError("verified_by and verified_at are recorded together")
        from_document = self.source is ObservationSource.VERIFIED_DOCUMENT
        if from_document != doctor_verified:
            raise ValueError("only a verified_document observation can be doctor_verified")
        has_fact = self.source_fact_id is not None
        has_document = self.source_document_id is not None
        if has_fact != has_document:
            raise ValueError("source_fact_id and source_document_id are recorded together")
        if has_fact != from_document:
            raise ValueError("source lineage is recorded iff source is verified_document")
        return self

    @property
    def admissible(self) -> bool:
        """Structural admissibility only: the deterministic data check passed.

        ``OK`` and ``OK_WITH_WARNING`` are both admissible and only ``REJECTED``
        is not — this mirrors the accepted ``monitoring.admissibility_reason``,
        which returns ``"validation_rejected"`` and nothing else for the data
        check. A warning is therefore never promoted and never hidden: the
        stored ``validation`` value stays exactly as recorded on the row.

        This is *not* trust and *not* eligibility — patient scope, temporal
        ordering and window bounds are checked against the run in
        ``SharedGraphState``.
        """
        return self.validation is not ValidationState.REJECTED


class ComparisonResult(Strict):
    """Deterministic comparison of one current observation with its latest prior.

    **Exact projection sources** (owner review R01): the first eight fields are
    the F2 ``ComparisonV2`` DTO verbatim (``p5_review_evidence.ComparisonV2``).
    ``ComparisonV2`` carries **no** ``current_value`` / ``baseline_value``, so
    those two are optional *projections from the bound observations*; when both
    are present the exact ``delta`` must follow from them. ``history_policy``
    labels which accepted producer's window produced the row (D-04) — it is a
    label, never a configurable lookback.
    """

    current_observation_id: Uuid
    baseline_observation_id: Uuid | None = None
    measure_type: MeasureType
    unit: Unit
    comparable: bool
    delta: DeltaDecimal | None = None
    incomparable_reason: IncomparableReason | None = None
    trust_basis: TrustBasis
    history_policy: ComparisonWindow
    current_value: ExactDecimal | None = None
    baseline_value: ExactDecimal | None = None
    evidence: list[ProvenanceRef] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.unit not in MEASURE_UNITS[self.measure_type]:
            raise ValueError("unit does not match the measure type's closed unit")
        if self.comparable:
            if self.baseline_observation_id is None or self.delta is None:
                raise ValueError("a comparable result needs a baseline id and delta")
            if self.incomparable_reason is not None:
                raise ValueError("a comparable result carries no incomparable_reason")
        elif self.incomparable_reason is None or self.delta is not None:
            raise ValueError("an incomparable result needs a reason and no delta")
        if self.baseline_observation_id == self.current_observation_id:
            raise ValueError("an observation cannot be its own baseline")
        both_values = self.current_value is not None and self.baseline_value is not None
        if both_values and (
            self.delta is None or self.delta != exact_delta(self.current_value, self.baseline_value)
        ):
            raise ValueError("delta must equal current_value - baseline_value exactly")
        if self.baseline_observation_id is None and self.trust_basis is TrustBasis.MIXED:
            raise ValueError("no baseline means trust_basis cannot be mixed")
        return self


class EvidenceExclusion(Strict):
    """One excluded observation with a closed reason (F2 ``EvidenceExclusionV2``)."""

    observation_id: Uuid
    reason_code: ExclusionReason


class PersistedExclusionRef(Strict):
    """One RB3 merged exclusion entry (``PersistedEvidenceExclusionV1``)."""

    observation_id: Uuid
    reason_code: ReasonCode


class LayeredExclusions(Strict):
    """RB3's explicit L0/L1/L2/L3 separation (``LayeredEvidenceExclusionsV1``)."""

    l0_lineage_checks: list[PersistedExclusionRef] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )
    l1_exclusions: list[PersistedExclusionRef] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )
    l2_exclusions: list[PersistedExclusionRef] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )
    l3_merged: list[PersistedExclusionRef] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )


class VerificationIssue(Strict):
    """A **P3** ``verification_issue`` row — a different identity space from F1 blockers.

    ``issue_id`` is ``verification_issue.id``. It is never manufactured for an
    F1-derived blocker, and it is never compared against
    ``GateEvaluationRef.issues`` (owner decision D-12): the two spaces are
    disjoint and a state may carry both.
    """

    issue_id: Uuid
    issue_type: IssueType
    reason_code: ReasonCode
    blocking: Literal[True] = True
    message: str = Field(max_length=240)
    document_id: Uuid | None = None
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    created_at: Iso

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        return self


class ReviewFlag(Strict):
    """Post-verification deterministic demo review prompt (``DR-*``)."""

    review_item_id: Uuid
    rule_id: ReviewRuleId
    reason_code: ReasonCode
    workflow_hint: ReviewHint | None = None
    message: str = Field(max_length=240)
    trust_basis: TrustBasis
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=8)
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=8)
    policy_version: PolicyVersion
    demo_only: Literal[True] = True
    dedupe_key: Sha256
    state: ReviewItemState = ReviewItemState.OPEN

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        _unique(self.observation_ids, "observation_ids")
        return self


# --- draft / approval / task shapes (structure only) -----------------------------------#


class ClaimCitation(Strict):
    text: str = Field(min_length=1, max_length=400)
    evidence: list[ProvenanceRef] = Field(min_length=1, max_length=6)


class DraftSummary(Strict):
    """Draft prose shape. Its presence never implies clinician approval."""

    draft_id: Uuid
    provider: DraftProvider
    model: str | None = Field(default=None, min_length=1, max_length=64)
    execution_status: DraftExecutionStatus
    prompt_version: PromptVersion
    latency_ms: int | None = Field(default=None, ge=0)
    claims: list[ClaimCitation] = Field(default_factory=list, max_length=20)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    not_asserted: list[str] = Field(default_factory=list, max_length=10)
    disclaimer: Literal["EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"] = DEMO_NOTICE
    created_at: Iso

    @model_validator(mode="after")
    def _provider_shape(self) -> Self:
        if any(len(item) > 240 for item in (*self.uncertainties, *self.not_asserted)):
            raise ValueError("uncertainty / not_asserted entries are bounded to 240 characters")
        if self.provider is DraftProvider.OLLAMA:
            if self.model is None or self.execution_status is not DraftExecutionStatus.MODEL_OK:
                raise ValueError("an ollama draft records a model and execution_status=model_ok")
        elif self.model is not None or self.execution_status is DraftExecutionStatus.MODEL_OK:
            raise ValueError("a fallback draft has no model and is never model_ok")
        return self


class ApprovalDecision(Strict):
    """Doctor decision shape. Validating it is not authentication (contract §5.2).

    An **empty** shape (every field ``None``) is not a recorded approval: it is
    the "not yet decided" placeholder. ``recorded`` reports the difference, and
    ``SharedGraphState`` never treats an empty shape as consent.
    """

    decision_id: Uuid | None = None
    decision: ApprovalChoice | None = None
    edited_summary: str | None = Field(default=None, min_length=1, max_length=4000)
    reason: str | None = Field(default=None, max_length=500)
    doctor_id: Uuid | None = None
    decided_at: Iso | None = None

    @property
    def recorded(self) -> bool:
        return self.decision is not None

    @model_validator(mode="after")
    def _decision_shape(self) -> Self:
        present = (
            self.decision_id is not None,
            self.decision is not None,
            self.doctor_id is not None,
            self.decided_at is not None,
        )
        if any(present) and not all(present):
            raise ValueError(
                "decision_id, decision, doctor_id and decided_at are recorded together"
            )
        if self.decision is ApprovalChoice.EDIT and self.edited_summary is None:
            raise ValueError("an edit decision carries the edited summary")
        if self.decision is not ApprovalChoice.EDIT and self.edited_summary is not None:
            raise ValueError("edited_summary is only allowed with an edit decision")
        return self


class TaskDraft(Strict):
    """Follow-up task *draft*. ``task_id`` is derived (UUIDv5), never random (P0-R04).

    The exact ``uuid5(TASK_NAMESPACE, action_key)`` check is **not** enforced:
    the fixed namespace and the action-key generation contract are deferred to S4
    (owner decision D-05). ``derive_task_id`` is pure UUID derivation, not task
    authority, and no task is ever created here.
    """

    action_key: Sha256
    task_id: TaskUuid
    title: str = Field(min_length=1, max_length=160)
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: str | None = Field(default=None, max_length=500)
    notification_text: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def _due_date(self) -> Self:
        if self.due_date is not None:
            _calendar_date(self.due_date)
        return self


class AgentError(Strict):
    code: ErrorCode
    node: NodeName
    message: str = Field(max_length=300)
    retryable: bool
    attempt: int = Field(ge=1, le=5)
    occurred_at: Iso


class GateIssueRef(Strict):
    """``RunGateIssue`` shape as emitted by the F1 gate — **full semantic identity**.

    The accepted producer orders blockers by exactly these fields when it
    validates a replay: ``(issue_type, reason_code, document_id, fact_ids)``.
    ``message`` is the canonical rendered message (``render_message``). Comparing
    only the issue-type names would accept a forged blocker (owner decision D-12).
    """

    issue_type: IssueType
    reason_code: ReasonCode
    document_id: Uuid
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=MAX_BLOCKING_FACTS)
    message: str = Field(max_length=240)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        return self

    def semantic_key(self) -> tuple[object, ...]:
        """The identity the accepted F1 producer compares on replay."""
        return (self.issue_type, self.reason_code, self.document_id, tuple(self.fact_ids))


class TraceGateIssue(Strict):
    """Typed trace payload for one gate blocker - **no free text** (R2-04).

    The accepted typed-trace boundary admits enums, identifiers, bounded counts
    and probabilities, never arbitrary text. ``GateIssueRef`` keeps the full F1
    blocker semantics *including the canonical rendered message*, because the
    gate/evidence reference is where that message belongs. This projection keeps
    the blocker's **identity** - ``issue_type``, ``reason_code``, ``document_id``
    and ``fact_ids`` - and drops the message: a rendered message is presentation
    text, not identity. ``semantic_key()`` is identical to
    ``GateIssueRef.semantic_key()``, which is exactly the tuple the accepted F1
    producer compares on replay.
    """

    issue_type: IssueType
    reason_code: ReasonCode
    document_id: Uuid
    fact_ids: list[Uuid] = Field(default_factory=list, max_length=MAX_BLOCKING_FACTS)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.fact_ids, "fact_ids")
        return self

    def semantic_key(self) -> tuple[object, ...]:
        """The identity the accepted F1 producer compares on replay."""
        return (self.issue_type, self.reason_code, self.document_id, tuple(self.fact_ids))


# --- typed node trace (REQ-AUDIT-01, P0-R08) -------------------------------------------#


class ExtractionAttempt(Strict):
    """Typed per-attempt extraction metadata — the only triage input besides facts."""

    attempt_id: Uuid
    document_id: Uuid
    path: ExtractionPath
    preprocessing: Preprocessing
    page_from: int = Field(ge=0, le=200)
    page_to: int = Field(ge=0, le=200)
    engine_confidence: Confidence | None = None
    text_char_count: int = Field(ge=0, le=200000)
    succeeded: bool
    error_code: str | None = Field(default=None, max_length=48)
    duration_ms: int = Field(ge=0)
    tool_version: str | None = Field(default=None, max_length=64)
    created_at: Iso

    @model_validator(mode="after")
    def _pages(self) -> Self:
        if self.page_to < self.page_from:
            raise ValueError("page_to must not precede page_from")
        return self


class TriageDetail(Strict):
    kind: Literal["triage"] = "triage"
    path_selected: TriagePath
    path_reason: PathReason
    document_id: Uuid
    attempt_index: int = Field(ge=1, le=2)
    engine_confidence: Confidence | None = None
    preprocessing_applied: bool


class ValidationDetail(Strict):
    kind: Literal["validation"] = "validation"
    validation_outcome: ValidationOutcome
    attempt_index: int = Field(ge=1, le=2)
    violation_codes: list[ViolationCode] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        _unique(self.violation_codes, "violation_codes")
        return self


class GateDetail(Strict):
    """Bounded gate decision recorded in the trace.

    ``decision`` is the **two-valued** normative trace contract
    (``node_event.gate_decision CHECK IN ('proceed','halt')``). The F1
    ``unavailable`` outcome is an *evaluation failure*: it never becomes a trace
    decision, so no proceed/halt value is fabricated to satisfy this schema
    (owner decision D-01). Routing an ``unavailable`` gate to a trace/error path
    is an S2 obligation, recorded in the S0 review.

    ``issues`` carries the **typed identity** of each blocker - issue type, reason
    code, document and fact identities - and never the rendered message text
    (owner decision D-12 for the identity, R2-04 for the trace boundary). The
    canonical message stays in ``GateEvaluationRef``, which is the gate/evidence
    reference, not the trace.

    ``verification_gate`` on ``SharedGraphState`` is the **current** evaluation;
    ``events`` is an append-only historical record. Only the most recent gate
    event is required to mirror the current evaluation. Binding an *earlier*
    trace event to the evaluation that actually produced it needs a persisted
    evaluation identity that S0 does not have, so that association remains an S2
    obligation and is deliberately not implemented here.
    """

    kind: Literal["gate"] = "gate"
    decision: TraceGateDecision
    blocking_fact_count: int = Field(ge=0, le=MAX_BLOCKING_FACTS)
    issues: list[TraceGateIssue] = Field(default_factory=list, max_length=MAX_BLOCKING_FACTS)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.decision == "proceed":
            if self.issues or self.blocking_fact_count != 0:
                raise ValueError("proceed records no blocking issue and zero blocking facts")
        elif not self.issues:
            raise ValueError("halt records at least one blocking issue")
        if self.blocking_fact_count != _distinct_fact_count(self.issues):
            raise ValueError("blocking_fact_count must equal the distinct referenced fact count")
        return self

    @classmethod
    def from_gate_evaluation(cls, ref: GateEvaluationRef) -> GateDetail:
        """Derive the trace projection from a matching gate outcome.

        The projection is derived, never assembled by hand: a ``halt`` keeps its
        blockers' identity and a ``proceed`` records none. An ``unavailable``
        evaluation is an *evaluation failure*, not a decision, so it raises
        instead of fabricating ``proceed`` or ``halt`` (owner decision D-01).
        """
        if ref.decision is GateDecision.UNAVAILABLE:
            raise ValueError("an unavailable gate evaluation has no trace decision")
        return cls(
            decision=ref.decision.value,
            blocking_fact_count=ref.blocking_fact_count,
            issues=[
                TraceGateIssue(
                    issue_type=item.issue_type,
                    reason_code=item.reason_code,
                    document_id=item.document_id,
                    fact_ids=list(item.fact_ids),
                )
                for item in ref.issues
            ],
        )


class FinalizeDetail(Strict):
    kind: Literal["finalize"] = "finalize"
    approval_decision: Literal["approve", "edit"]
    task_created: bool
    notification_created: bool

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.notification_created and not self.task_created:
            raise ValueError("a notification is only created together with its task")
        return self


EventDetail = Annotated[
    TriageDetail | ValidationDetail | GateDetail | FinalizeDetail, Field(discriminator="kind")
]


class NodeEvent(Strict):
    """One graph-node execution record: enums, IDs, counts and probabilities only."""

    node: NodeName
    attempt: int = Field(default=1, ge=1, le=5)
    started_at: Iso
    ended_at: Iso | None = None
    outcome: NodeOutcome | None = None
    tools_called: list[ToolName] = Field(default_factory=list, max_length=6)
    detail: EventDetail | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at precedes started_at")
        _unique(self.tools_called, "tools_called")
        allowed = NODE_TOOLS[self.node]
        if not set(self.tools_called) <= allowed:
            raise ValueError(f"tools_called exceeds the {self.node} allowlist")
        expected = DETAIL_KIND_BY_NODE.get(self.node)
        if expected is None:
            if self.detail is not None:
                raise ValueError(f"{self.node} makes no bounded decision; detail must be null")
        elif self.detail is None or self.detail.kind != expected:
            raise ValueError(f"{self.node} must carry exactly one {expected} detail")
        return self


# --- run identity and immutable selection ---------------------------------------------#


class RunIdentity(Strict):
    """Immutable identity block of one run (contract §2): ``thread_id == run_id``.

    ``as_of_utc`` is the *pinned evaluation clock* used by every time-dependent
    rule (``REQ-OPS-04``). It is not the authorization/validation clock.

    ``prompt_version`` and ``encounter_id`` are **future contract slots**: F0's
    ``WorkflowRun`` has neither column, so nothing persists them today. They are
    optional, carry no authority, and a persisted requirement needs its own
    explicit contract reconciliation (owner decision D-06).
    """

    run_id: RunUuid
    thread_id: RunUuid
    patient_id: Uuid
    doctor_id: Uuid
    encounter_id: Uuid | None = None
    workflow_version: SemVer
    state_schema_version: SemVer
    policy_version: PolicyVersion
    prompt_version: PromptVersion | None = None
    mapping_version: MappingVersion
    as_of_utc: Iso
    idempotency_key: Sha256
    started_at: Iso

    @model_validator(mode="after")
    def _thread(self) -> Self:
        if self.thread_id != self.run_id:
            raise ValueError("thread_id must equal run_id (one thread per run)")
        return self

    def supported_versions(self) -> bool:
        """Pure predicate: do the run's versions match *this* contract module?"""
        return (
            self.workflow_version == WORKFLOW_VERSION
            and self.state_schema_version == STATE_SCHEMA_VERSION
        )

    def assert_unchanged(self, previous: RunIdentity) -> None:
        """Raise if any immutable identity field differs from ``previous`` (§2, §5.3)."""
        if self != previous:
            changed = sorted(
                name
                for name in type(self).model_fields
                if getattr(self, name) != getattr(previous, name)
            )
            raise ValueError(f"run identity changed: {', '.join(changed)}")


class SelectedDocumentRef(Strict):
    """``run_selected_document`` row projection."""

    document_id: Uuid
    source_sha256: Sha256
    source_status: str = Field(pattern=r"^[a-z_]{1,24}$")


class SelectedObservationRef(Strict):
    """``run_selected_observation`` row projection (manifest identity only)."""

    observation_id: Uuid
    trust_level: TrustLevel
    source_fact_id: Uuid | None = None
    observation_created_at: Iso

    @model_validator(mode="after")
    def _trust(self) -> Self:
        if (self.trust_level is TrustLevel.DOCTOR_VERIFIED) != (self.source_fact_id is not None):
            raise ValueError("doctor_verified selection requires source_fact_id; otherwise none")
        return self


class SelectedOmissionRef(Strict):
    """``run_source_omission`` row projection (doctor-authored, audited)."""

    document_id: Uuid
    vi002_issue_id: Uuid
    reason_code: OMISSION_REASON
    doctor_id: Uuid
    source_sha256: Sha256


#: Member adapters used by ``SelectedSourceManifest.build`` (validated before digesting).
_MANIFEST_MEMBER_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "document_ids": TypeAdapter(list[Uuid]),
    "documents": TypeAdapter(list[SelectedDocumentRef]),
    "observation_ids": TypeAdapter(list[Uuid]),
    "observations": TypeAdapter(list[SelectedObservationRef]),
    "omission_document_ids": TypeAdapter(list[Uuid]),
    "omissions": TypeAdapter(list[SelectedOmissionRef]),
}


class SelectedSourceManifest(Strict):
    """Immutable selected-source manifest; ``selection_fingerprint`` is self-verifying.

    The fingerprint is a SHA-256 over the canonical JSON of every other field
    (sorted keys, compact separators). It is the state-level identity of *what
    was selected* and is distinct from the F1 ``gate_input_fingerprint_sha256``,
    which additionally covers recomputed gate inputs.
    """

    document_ids: list[Uuid] = Field(default_factory=list, max_length=MAX_SELECTED_DOCUMENTS)
    documents: list[SelectedDocumentRef] = Field(
        default_factory=list, max_length=MAX_SELECTED_DOCUMENTS
    )
    observation_ids: list[Uuid] = Field(default_factory=list, max_length=MAX_MANIFEST_OBSERVATIONS)
    observations: list[SelectedObservationRef] = Field(
        default_factory=list, max_length=MAX_MANIFEST_OBSERVATIONS
    )
    omission_document_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_MANIFEST_OMISSIONS
    )
    omissions: list[SelectedOmissionRef] = Field(
        default_factory=list, max_length=MAX_MANIFEST_OMISSIONS
    )
    selection_fingerprint: Sha256

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.document_ids, "document_ids")
        _sorted_unique(self.observation_ids, "observation_ids")
        _sorted_unique(self.omission_document_ids, "omission_document_ids")
        if set(self.omission_document_ids) & set(self.document_ids):
            raise ValueError("an omitted document cannot also be a selected document")
        if [item.document_id for item in self.documents] != self.document_ids:
            raise ValueError("documents must list exactly document_ids in order")
        if [item.observation_id for item in self.observations] != self.observation_ids:
            raise ValueError("observations must list exactly observation_ids in order")
        if [item.document_id for item in self.omissions] != self.omission_document_ids:
            raise ValueError("omissions must list exactly omission_document_ids in order")
        if self.selection_fingerprint != self.compute_fingerprint():
            raise ValueError("selection_fingerprint does not match the manifest content")
        return self

    def compute_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"selection_fingerprint"})
        return _canonical_sha256(payload)

    @classmethod
    def build(cls, **fields: object) -> Self:
        """Validate the content members, stamp the canonical digest, validate the whole.

        Every member is validated by its own type before it enters the digest
        payload (no unvalidated scratch instance, no ``model_construct``), and
        the returned manifest passes the same full validation as any other input
        — including the self-check ``selection_fingerprint == compute_fingerprint()``.

        An **unknown keyword argument raises** instead of being silently
        discarded (owner review R07): a typo in a member name must never produce
        a manifest that quietly omits evidence.
        """
        unknown = sorted(set(fields) - set(_MANIFEST_MEMBER_ADAPTERS))
        if unknown:
            raise ValueError(f"unknown manifest member(s): {', '.join(unknown)}")
        members: dict[str, Any] = {}
        for name, adapter in _MANIFEST_MEMBER_ADAPTERS.items():
            members[name] = adapter.validate_python(fields.get(name, []))
        payload = {
            name: (
                [item.model_dump(mode="json") for item in value]
                if name in {"documents", "observations", "omissions"}
                else value
            )
            for name, value in members.items()
        }
        return cls(**{**members, "selection_fingerprint": _canonical_sha256(payload)})


def _canonical_sha256(payload: object) -> str:
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(stable.encode("utf-8")).hexdigest()


def derived_trust_basis(current: TrustLevel, baseline: TrustLevel | None) -> TrustBasis:
    """Pure derivation mirroring ``monitoring._trust_basis`` (same labels, same rules)."""
    labels = {current} if baseline is None else {current, baseline}
    if labels == {TrustLevel.DOCTOR_VERIFIED}:
        return TrustBasis.DOCTOR_VERIFIED
    if labels == {TrustLevel.SELF_REPORTED_VALIDATED}:
        return TrustBasis.SELF_REPORTED
    return TrustBasis.MIXED


def selection_fingerprint(payload: object) -> str:
    """Public pure helper so S2/S4 compute the manifest digest with one recipe."""
    return _canonical_sha256(payload)


# --- F1 gate evaluation, F2 evidence identity, RB3 persistence outcome ------------------#


class GateEvaluationRef(Strict):
    """``RunGateReceipt`` shape: all three F1 outcomes, with no caller-supplied blocker count.

    This is a *reference* to a server evaluation. Its presence says nothing
    about graph completion, and it never substitutes for revalidation.

    ``gate_evaluation_id`` is **optional** because the F1 receipt does not expose
    it: the stored identity is ``run_gate_evaluation.id``, which the F2 DTO and
    the RB3 receipt *do* carry. Receipt identity, stored gate-evaluation identity
    and P3 ``verification_issue`` identity are three different spaces and are
    never conflated (owner review R01/R03).
    """

    run_id: RunUuid
    patient_id: Uuid
    doctor_id: Uuid
    gate_version: SemVer
    input_fingerprint_sha256: Sha256
    decision: GateDecision
    issues: list[GateIssueRef] = Field(default_factory=list, max_length=MAX_BLOCKING_FACTS)
    historical_excluded_vi002_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_BLOCKING_FACTS
    )
    blocking_fact_count: int = Field(ge=0)
    unavailable_reason: GateUnavailableReason | None = None
    replayed: bool
    gate_evaluated: Literal[True] = True
    runtime_evaluable: Literal[False] = False
    #: ``run_gate_evaluation.id`` — projected from the stored row, **not** the receipt.
    gate_evaluation_id: Uuid | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.historical_excluded_vi002_ids, "historical_excluded_vi002_ids")
        if (self.decision is GateDecision.UNAVAILABLE) != (self.unavailable_reason is not None):
            raise ValueError("unavailable_reason is present iff decision is unavailable")
        distinct = _distinct_fact_count(self.issues)
        if self.decision is GateDecision.PROCEED:
            # ``proceed`` means no issue was recorded at all.
            if self.issues or self.blocking_fact_count != 0:
                raise ValueError("proceed records no blocking issue and zero blocking facts")
        elif self.decision is GateDecision.HALT and not self.issues:
            # A halt is decided by recorded issues, not by a fact count: every
            # blocker may be document-level, leaving zero distinct facts.
            raise ValueError("halt records at least one blocking issue")
        # ``unavailable`` keeps its recorded failure detail (it is not discarded
        # to satisfy this schema), so issues are legal there too.
        if self.blocking_fact_count <= MAX_BLOCKING_FACTS:
            if self.blocking_fact_count != distinct:
                raise ValueError(
                    "blocking_fact_count must equal the distinct referenced fact count"
                )
        elif (
            self.decision is not GateDecision.UNAVAILABLE
            or self.unavailable_reason is not GateUnavailableReason.TOO_MANY_BLOCKING_FACTS
        ):
            # Above the persisted bound the producer can only have returned
            # ``unavailable`` with reason ``too_many_blocking_facts``.
            raise ValueError("blocking_fact_count above the bound requires too_many_blocking_facts")
        return self


class EvaluableEvidenceRef(Strict):
    """Identity of one F2 ``EvaluableReviewEvidenceV2`` projection (not its content).

    The typed content lives in the state's evidence collections; this reference
    binds them to the gate evaluation and bridge fingerprint they were computed
    from. ``history_policy`` records the implemented 365-day window.
    """

    contract_version: F2_CONTRACT_VERSION = "2.0.0"
    run_id: RunUuid
    patient_id: Uuid
    doctor_id: Uuid
    as_of_utc: Iso
    workflow_version: SemVer
    state_schema_version: SemVer
    mapping_version: MappingVersion
    policy_version: PolicyVersion
    gate_evaluation_id: Uuid
    gate_version: SemVer
    gate_input_fingerprint_sha256: Sha256
    bridge_input_fingerprint_sha256: Sha256
    history_policy: F2_HISTORY_POLICY = "f2-history-365d-v1"
    history_lookback_days: Literal[365] = 365
    selected_document_ids: list[Uuid] = Field(min_length=1, max_length=MAX_SELECTED_DOCUMENTS)
    selected_observation_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_SELECTED_CURRENT
    )
    historical_excluded_vi002_ids: list[Uuid] = Field(
        default_factory=list, max_length=MAX_BLOCKING_FACTS
    )
    no_current_reason: Literal["no_current_selected"] | None = None
    bridge_validated: Literal[True] = True
    runtime_evaluable: Literal[False] = False
    rules_executed: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.selected_document_ids, "selected_document_ids")
        _sorted_unique(self.selected_observation_ids, "selected_observation_ids")
        _sorted_unique(self.historical_excluded_vi002_ids, "historical_excluded_vi002_ids")
        if (self.no_current_reason is None) != bool(self.selected_observation_ids):
            raise ValueError("no_current_reason is set iff no current observation was selected")
        return self


class SealedReviewEvaluation(Strict):
    """Shape of one sealed RB3 ``ReviewPersistenceReceiptV1`` (``ux_review_evaluation_run``).

    A sealed evaluation is **not** graph completion. It is immutable, replay
    is exact-only, and it must never be reused after a corrected source
    identity (a corrected source requires a new run — RB4-05).

    **Replay arithmetic** (owner review R02), matching the accepted durable
    service exactly:

    * first successful persistence — ``replayed=False`` and the per-call write
      counts equal the totals;
    * exact replay — ``replayed=True``, both per-call write counts are **zero**,
      and the *existing* totals stay non-zero while the sealed evaluation and
      audit identities are unchanged.

    ``exclusion_count`` is ``len(l3_merged)`` — the deduplicated merged count —
    **not** ``l1 + l2``, because the same observation can be excluded at several
    layers.
    """

    kind: Literal["sealed"] = "sealed"
    contract_version: RB3_RECEIPT_CONTRACT_VERSION = "p4-rb3-receipt-1.0.0"
    run_id: RunUuid
    patient_id: Uuid
    doctor_id: Uuid
    as_of_utc: Iso
    policy_version: PolicyVersion
    policy_reference_sha256: Sha256
    gate_evaluation_id: Uuid
    gate_version: SemVer
    gate_input_fingerprint_sha256: Sha256
    bridge_input_fingerprint_sha256: Sha256
    rb3_fingerprint_version: RB3_FINGERPRINT_VERSION = "rb3-full-input-1.0.0"
    input_fingerprint_sha256: Sha256
    output_identity_sha256: Sha256
    evaluation_id: Uuid
    audit_event_id: Uuid
    lineage_label_policy: Literal["a2_transport_label"]
    dr006_policy: Literal["prohibited_denied", "not_present"]
    replayed: bool
    review_items_persisted: int = Field(ge=0, le=MAX_PERSISTED_ITEMS)
    review_items_total: int = Field(ge=0, le=MAX_PERSISTED_ITEMS)
    evidence_links_persisted: int = Field(ge=0, le=MAX_PERSISTED_LINKS)
    evidence_links_total: int = Field(ge=0, le=MAX_PERSISTED_LINKS)
    excluded_evidence: list[PersistedExclusionRef] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )
    layered_exclusions: LayeredExclusions
    exclusion_count: int = Field(ge=0, le=MAX_MERGED_EXCLUSIONS)
    l1_exclusion_count: int = Field(ge=0, le=MAX_MERGED_EXCLUSIONS)
    l2_exclusion_count: int = Field(ge=0, le=MAX_MERGED_EXCLUSIONS)
    evaluation_completed: Literal[True] = True
    offline_evaluator_invoked: Literal[True] = True
    runtime_evaluable: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"
    demo_only: Literal[True] = True
    not_for_clinical_use: Literal[True] = True

    @model_validator(mode="after")
    def _all_or_nothing(self) -> Self:
        if self.replayed:
            if self.review_items_persisted != 0 or self.evidence_links_persisted != 0:
                raise ValueError("an exact replay writes zero review items and zero evidence links")
        elif self.review_items_persisted != self.review_items_total:
            raise ValueError("a first persistence writes every review item (one transaction)")
        elif self.evidence_links_persisted != self.evidence_links_total:
            raise ValueError("a first persistence writes every evidence link (one transaction)")
        if self.evidence_links_total < self.review_items_total:
            raise ValueError("evidence_links_total is never below review_items_total")
        # R2-05: the accepted service computes
        # ``l3_merged = tuple(sorted(set(l1_exclusions) | set(l2_exclusions)))``
        # and stores ``excluded_evidence = l3_merged``. Lengths alone would let
        # equal-length contradictory lists through, so the content is validated.
        l1 = self.layered_exclusions.l1_exclusions
        l2 = self.layered_exclusions.l2_exclusions
        if l1 != _sorted_exclusions(l1):
            raise ValueError("l1_exclusions must be in canonical order")
        if l2 != _sorted_exclusions(l2):
            raise ValueError("l2_exclusions must be in canonical order")
        merged = _sorted_exclusions([*l1, *l2])
        if self.layered_exclusions.l3_merged != merged:
            raise ValueError("l3_merged must be the canonical deduplicated union of l1 and l2")
        if self.excluded_evidence != merged:
            raise ValueError(
                "excluded_evidence must equal l3_merged exactly, not merely its length"
            )
        if self.exclusion_count != len(merged):
            raise ValueError("exclusion_count must equal the merged exclusion entry count")
        if self.l1_exclusion_count != len(l1):
            raise ValueError("l1_exclusion_count must equal len(l1_exclusions)")
        if self.l2_exclusion_count != len(l2):
            raise ValueError("l2_exclusion_count must equal len(l2_exclusions)")
        # Pinned exactly as the durable service and its DB CHECKs pin them.
        if self.policy_reference_sha256 != RB3_POLICY_REFERENCE_SHA256:
            raise ValueError("policy_reference_sha256 must equal the pinned RB3 policy SHA")
        if self.dr006_policy != RB3_DR006_POLICY:
            raise ValueError(
                "the durable RB3 service always records dr006_policy=prohibited_denied"
            )
        return self


class DeniedReviewPersistence(Strict):
    """A denied persistence is an outcome, never a completion: zero writes, no ids.

    ``DR-006`` presence denies the whole invocation
    (``dr006_persistence_not_authorized``); the graph's reaction to any denial
    is an open S2/S4 decision and is deliberately not encoded here.
    """

    kind: Literal["denied"] = "denied"
    reason: RB3DenialReason
    writes_performed: Literal[0] = 0
    observed_at_utc: Iso
    runtime_evaluable: Literal[False] = False
    policy_status: Literal["unapproved"] = "unapproved"


ReviewPersistenceOutcome = Annotated[
    SealedReviewEvaluation | DeniedReviewPersistence, Field(discriminator="kind")
]


# --- checkpoint reference and resume classification (shape only) ----------------------#


class CheckpointRef(Strict):
    """Replay-state reference. ``claimed_status`` is informational, never authority.

    A lagging or diverging checkpoint is normal (contract §5.1) and is
    reconciled against the app DB per §7.3 at runtime — unexecuted here. This
    reference can never authorize execution, resume, approval or finalization
    (owner decision D-10).
    """

    checkpoint_id: Token
    thread_id: RunUuid
    last_completed_node: NodeName | None = None
    claimed_status: RunStatus | None = None


class ResumeDisposition(StrEnum):
    RESUME_UNCHANGED = "resume_unchanged"
    CHANGED_SOURCE_IDENTITY = "changed_source_identity"
    CORRECTED_SOURCE_NEW_RUN = "corrected_source_new_run"


class ResumeAssessment(Strict):
    """Schema-level halt/resume distinction for S4 (no resume implementation).

    * ``resume_unchanged`` — selection identity unchanged, nothing corrected.
    * ``changed_source_identity`` — observed selection differs from the stored one.
    * ``corrected_source_new_run`` — at least one selected source fact was
      corrected; RB4-05 requires a **new** run identity, never a resumed one.
    """

    disposition: ResumeDisposition
    app_db_status: RunStatus
    stored_selection_fingerprint: Sha256
    observed_selection_fingerprint: Sha256
    corrected_fact_ids: list[Uuid] = Field(default_factory=list, max_length=20)
    sealed_evaluation_present: bool
    checkpoint_present: bool

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _sorted_unique(self.corrected_fact_ids, "corrected_fact_ids")
        same = self.stored_selection_fingerprint == self.observed_selection_fingerprint
        corrected = bool(self.corrected_fact_ids)
        if self.disposition is ResumeDisposition.RESUME_UNCHANGED and (not same or corrected):
            raise ValueError("resume_unchanged requires identical fingerprints and no correction")
        if self.disposition is ResumeDisposition.CHANGED_SOURCE_IDENTITY and (same or corrected):
            raise ValueError(
                "changed_source_identity requires differing fingerprints, no correction"
            )
        if self.disposition is ResumeDisposition.CORRECTED_SOURCE_NEW_RUN and not corrected:
            raise ValueError("corrected_source_new_run requires at least one corrected fact id")
        return self


# --- the shared state ------------------------------------------------------------------#


class SharedGraphState(Strict):
    """Typed shared state of one run. Pure data; serializing it authorizes nothing.

    Field groups follow the contract §3 proposal. Reconciled differences are
    documented in the S0 review: nested immutable ``identity`` and
    ``selection`` blocks, exact ``Decimal`` values, the F1 gate reference, the
    F2 evidence reference, the RB3 persistence outcome, the checkpoint
    reference, and fixed honesty literals.
    """

    identity: RunIdentity
    selection: SelectedSourceManifest
    status: RunStatus = RunStatus.QUEUED
    current_node: NodeName | None = None
    halt_reason: HaltReason | None = None
    #: Authorization/validation clock of the latest gate/bridge revalidation —
    #: deliberately distinct from the pinned ``identity.as_of_utc``.
    last_validated_at_utc: Iso | None = None

    # evidence
    extraction_attempts: list[ExtractionAttempt] = Field(
        default_factory=list, max_length=MAX_EXTRACTION_ATTEMPTS
    )
    extraction_facts: list[ExtractedFact] = Field(default_factory=list, max_length=MAX_FACTS)
    verified_facts: list[VerifiedFact] = Field(default_factory=list, max_length=MAX_FACTS)
    observations: list[ObservationView] = Field(default_factory=list, max_length=MAX_OBSERVATIONS)
    comparisons: list[ComparisonResult] = Field(default_factory=list, max_length=MAX_COMPARISONS)
    evidence_exclusions: list[EvidenceExclusion] = Field(
        default_factory=list, max_length=MAX_MERGED_EXCLUSIONS
    )
    verification_gate: GateEvaluationRef | None = None
    evaluable_evidence: EvaluableEvidenceRef | None = None

    # agent outputs
    verification_issues: list[VerificationIssue] = Field(default_factory=list, max_length=20)
    review_flags: list[ReviewFlag] = Field(default_factory=list, max_length=MAX_PERSISTED_ITEMS)
    draft_summary: DraftSummary | None = None
    approval: ApprovalDecision | None = None
    pending_tasks: list[TaskDraft] = Field(default_factory=list, max_length=MAX_PENDING_TASKS)
    created_task_ids: list[TaskUuid] = Field(default_factory=list, max_length=MAX_PENDING_TASKS)

    # control
    retry_counts: dict[NodeName, int] = Field(default_factory=dict, max_length=11)
    errors: list[AgentError] = Field(default_factory=list, max_length=MAX_ERRORS)
    events: list[NodeEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    model_metadata: dict[Token, MetadataValue] = Field(default_factory=dict, max_length=8)
    checkpoint: CheckpointRef | None = None
    review_persistence: ReviewPersistenceOutcome | None = None
    updated_at: Iso

    # honesty literals: shape can never claim runtime authority
    policy_status: Literal["unapproved"] = "unapproved"
    runtime_policy_activated: Literal[False] = False
    runtime_evaluable: Literal[False] = False
    demo_only: Literal[True] = True
    not_for_clinical_use: Literal[True] = True

    # -- convenience read-only projections (not serialized, not authority) --#
    @property
    def run_id(self) -> str:
        return self.identity.run_id

    @property
    def patient_id(self) -> str:
        return self.identity.patient_id

    @property
    def document_ids(self) -> list[str]:
        return list(self.selection.document_ids)

    @property
    def observation_ids(self) -> list[str]:
        return list(self.selection.observation_ids)

    @property
    def workflow_completed(self) -> bool:
        """Graph completion is exactly ``status == completed`` (app DB authority)."""
        return self.status is RunStatus.COMPLETED

    @property
    def review_evaluation_sealed(self) -> bool:
        """A sealed RB3 evaluation exists for this run — independent of completion."""
        return self.review_persistence is not None and self.review_persistence.kind == "sealed"

    @property
    def checkpoint_diverges(self) -> bool:
        """Checkpoint claims a status the app DB does not (informational only)."""
        return self.checkpoint is not None and self.checkpoint.claimed_status not in (
            None,
            self.status,
        )

    @property
    def assurance_level(self) -> AssuranceLevel:
        """The only level this module can grant — never more (owner review R07)."""
        return AssuranceLevel.SHAPE_VALIDATED

    @classmethod
    def revalidate(cls, instance: SharedGraphState) -> SharedGraphState:
        """Genuine full revalidation: re-parse from JSON text, never trust instances.

        ``frozen=True`` does not make list contents immutable, and Pydantic's
        ``model_copy``/``model_construct`` bypass validation by design (owner
        decision D-08). This is the boundary a future trust-boundary ingestion
        must call: the instance is serialised to JSON text and parsed back, so a
        mutated container, a forged nested instance or a skipped field is
        re-checked from scratch.
        """
        return cls.model_validate_json(instance.model_dump_json())

    # -- cross-field invariants --#
    @model_validator(mode="after")
    def _scope_and_uniqueness(self) -> Self:
        ident = self.identity
        if self.updated_at < ident.started_at:
            raise ValueError("updated_at precedes started_at")
        if self.checkpoint is not None and self.checkpoint.thread_id != ident.run_id:
            raise ValueError("checkpoint thread must be the run's own thread")
        for group, key in (
            (self.extraction_attempts, "attempt_id"),
            (self.extraction_facts, "fact_id"),
            (self.verified_facts, "fact_id"),
            (self.observations, "observation_id"),
            (self.verification_issues, "issue_id"),
            (self.review_flags, "review_item_id"),
        ):
            _unique([str(getattr(item, key)) for item in group], key)
        _unique([item.task_id for item in self.pending_tasks], "task_id")
        _unique([item.action_key for item in self.pending_tasks], "action_key")
        _unique(self.created_task_ids, "created_task_ids")
        _unique(
            [(item.current_observation_id, item.history_policy) for item in self.comparisons],
            "current_observation_id/history_policy",
        )
        for fact in (*self.extraction_facts, *self.verified_facts):
            # A projection that carries no patient scope is not evidence of scope.
            if fact.patient_id is not None and fact.patient_id != ident.patient_id:
                raise ValueError("fact patient scope differs from the run")
        for observation in self.observations:
            if observation.patient_id != ident.patient_id:
                raise ValueError("observation patient scope differs from the run")
        for omission in self.selection.omissions:
            if omission.doctor_id != ident.doctor_id:
                raise ValueError("a manifest omission must be authored by the run's own doctor")
        return self

    @model_validator(mode="after")
    def _selected_current_roles(self) -> Self:
        """Selected-current rows and the F2 selection must agree exactly (R05).

        A history row can never silently become a selected current: the
        ``SELECTED_CURRENT`` set is pinned to the F2 ``selected_observation_ids``.
        """
        current = {
            row.observation_id
            for row in self.observations
            if row.role is ObservationRole.SELECTED_CURRENT
        }
        # R2-03: the immutable selected manifest is authoritative for *what was
        # selected*, and it is present whether or not the state carries an F2
        # reference. A selected-current label that the manifest does not carry
        # is a relabelled row, not a selection.
        if current != set(self.selection.observation_ids):
            raise ValueError(
                "selected-current observations must equal the immutable selected manifest"
            )
        evidence = self.evaluable_evidence
        if evidence is not None and current != set(evidence.selected_observation_ids):
            raise ValueError(
                "selected-current observations must equal the F2 selected_observation_ids"
            )
        for row in self.observations:
            if row.role is ObservationRole.SELECTED_CURRENT and not row.admissible:
                raise ValueError("a selected-current observation must pass the data check")
        return self

    @model_validator(mode="after")
    def _evidence_binding(self) -> Self:
        """Structural binding of comparisons, facts and history to typed rows (R05)."""
        observations = {row.observation_id: row for row in self.observations}
        for selected in self.selection.observations:
            row = observations.get(selected.observation_id)
            if row is None:
                raise ValueError("every selected observation must be present in observations")
            if (
                row.trust_level is not selected.trust_level
                or row.source_fact_id != selected.source_fact_id
            ):
                raise ValueError("selected observation manifest differs from the typed observation")

        extracted = {item.fact_id: item for item in self.extraction_facts}
        verified_by_id = {item.fact_id: item for item in self.verified_facts}
        for verified in self.verified_facts:
            source = extracted.get(verified.fact_id)
            if source is None:
                continue
            if source.verification_status is not VerificationStatus.VERIFIED:
                raise ValueError("a verified fact cannot project a pending/rejected extracted fact")
            if source.document_id != verified.document_id:
                raise ValueError("a verified projection must keep its source document")
            if source.field_name != verified.field_name:
                raise ValueError("a verified projection must keep its source field")
            if source.corrected_from_fact_id != verified.corrected_from_fact_id:
                raise ValueError("a verified projection must keep its corrected lineage")
            # R2-06: value, unit and every *supplied* optional projection must
            # agree. An absent projection stays absent - it is never fabricated
            # to make the pair look complete.
            if source.normalized_value != verified.normalized_value:
                raise ValueError("a verified projection must keep its normalized value")
            if source.unit != verified.unit:
                raise ValueError("a verified projection must keep its unit")
            if (
                verified.patient_id is not None
                and source.patient_id is not None
                and source.patient_id != verified.patient_id
            ):
                raise ValueError("a verified projection must keep its patient scope")
            if (
                verified.verified_by is not None
                and source.verified_by is not None
                and source.verified_by != verified.verified_by
            ):
                raise ValueError("a verified projection must keep its verifier")
            if (
                verified.verified_at is not None
                and source.verified_at is not None
                and source.verified_at != verified.verified_at
            ):
                raise ValueError("a verified projection must keep its decision time")

        # R2-06: an observation's recorded source document must be the document
        # of the fact it cites. Contradictory provenance identities are rejected
        # instead of being presented as structurally bound.
        for row in self.observations:
            if row.source_document_id is None or row.source_fact_id is None:
                continue
            cited = extracted.get(row.source_fact_id)
            if cited is not None and cited.document_id != row.source_document_id:
                raise ValueError("observation source_document_id contradicts its extracted fact")
            projected = verified_by_id.get(row.source_fact_id)
            if projected is not None and projected.document_id != row.source_document_id:
                raise ValueError(
                    "observation source_document_id contradicts its verified projection"
                )

        for comparison in self.comparisons:
            current = observations.get(comparison.current_observation_id)
            if current is None:
                raise ValueError("a comparison current must resolve to a typed observation")
            if current.role is not ObservationRole.SELECTED_CURRENT:
                raise ValueError("a comparison current must be a selected current, not history")
            if (
                current.measure_type is not comparison.measure_type
                or current.unit is not comparison.unit
            ):
                raise ValueError("comparison measure/unit differs from the typed observation")
            if comparison.current_value is not None and current.value != comparison.current_value:
                raise ValueError("comparison current value differs from the typed observation")
            if not current.admissible:
                raise ValueError("a comparison current must pass the data check")
            # D-04: the window label is typed and never relabelled. ``p5_evidence_bridge``
            # is the only producer of comparisons in an F2-shaped state and it pins
            # ``f2-history-365d-v1``; a 90-day RB1 label beside an F2 evidence
            # reference would present 90-day rule input as the 365-day window.
            if (
                comparison.history_policy is ComparisonWindow.RB1_90D
                and self.evaluable_evidence is not None
            ):
                raise ValueError("an F2 evidence reference cannot carry a 90-day RB1 comparison")
            baseline_id = comparison.baseline_observation_id
            if baseline_id is None:
                # R2-03: "no baseline" and "comparable" are contradictory shapes;
                # the row-level validator already forbids the pair, and the state
                # re-checks it against the resolved evidence.
                if comparison.comparable:
                    raise ValueError("a comparable result needs a resolved baseline row")
                # No baseline: the label can only follow the current trust level.
                expected = derived_trust_basis(current.trust_level, None)
                if comparison.trust_basis is not expected:
                    raise ValueError("trust_basis without a baseline must follow the current trust")
                continue
            baseline = observations.get(baseline_id)
            if baseline is None:
                raise ValueError("a claimed baseline must resolve to a typed observation")
            if baseline.role is not ObservationRole.HISTORY:
                raise ValueError("a comparison baseline must be a history row")
            if (
                baseline.measure_type is not comparison.measure_type
                or baseline.unit is not comparison.unit
            ):
                raise ValueError(
                    "comparison baseline measure/unit differs from the typed observation"
                )
            if (
                comparison.baseline_value is not None
                and baseline.value != comparison.baseline_value
            ):
                raise ValueError("comparison baseline value differs from the typed observation")
            if not baseline.admissible:
                raise ValueError("a comparison baseline must pass the data check")
            if baseline.measured_at >= current.measured_at:
                raise ValueError("a baseline must precede the current observation")
            # R2-03: the baseline must lie inside the *labelled* window, using the
            # accepted producer semantics (F2 365 days, RB1 90 days). This is a
            # membership check only: the state carries a bounded history
            # projection and cannot prove that the resolved row is the *latest
            # prior* among all history - that selection belongs to the
            # authoritative service, not to this structural check.
            window_days = (
                F2_HISTORY_LOOKBACK_DAYS
                if comparison.history_policy is ComparisonWindow.F2_365D
                else RB1_HISTORY_LOOKBACK_DAYS
            )
            if _parse_instant(current.measured_at) - _parse_instant(
                baseline.measured_at
            ) > timedelta(days=window_days):
                raise ValueError("a baseline must lie inside the labelled comparison window")
            if comparison.trust_basis is not derived_trust_basis(
                current.trust_level, baseline.trust_level
            ):
                raise ValueError("trust_basis must follow both observations' trust levels")
            # R2-03: a comparable delta is always validated against the *resolved*
            # observation values. The optional projected values are a cross-check
            # on the rows, never a substitute for them, so a comparison that
            # omits them can no longer carry an incorrect delta.
            if comparison.delta is not None and comparison.delta != exact_delta(
                current.value, baseline.value
            ):
                raise ValueError("delta must equal current_value - baseline_value exactly")
        return self

    @model_validator(mode="after")
    def _references(self) -> Self:
        ident = self.identity
        gate = self.verification_gate
        if gate is not None:
            if (gate.run_id, gate.patient_id, gate.doctor_id) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
            ):
                raise ValueError("gate evaluation belongs to a different run or scope")
            if self.last_validated_at_utc is None:
                raise ValueError("a gate reference requires the validation clock")
        evidence = self.evaluable_evidence
        if evidence is not None:
            if (
                evidence.run_id,
                evidence.patient_id,
                evidence.doctor_id,
                evidence.as_of_utc,
                evidence.workflow_version,
                evidence.state_schema_version,
                evidence.mapping_version,
                evidence.policy_version,
            ) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
                ident.as_of_utc,
                ident.workflow_version,
                ident.state_schema_version,
                ident.mapping_version,
                ident.policy_version,
            ):
                raise ValueError("evidence reference belongs to a different run identity")
            if self.last_validated_at_utc is None:
                raise ValueError("an evidence reference requires the validation clock")
            if evidence.selected_document_ids != self.selection.document_ids:
                raise ValueError("evidence documents differ from the selected manifest")
            if evidence.selected_observation_ids != self.selection.observation_ids:
                raise ValueError("evidence observations differ from the selected manifest")
            if gate is None:
                raise ValueError(
                    "evidence reference requires the gate evaluation it was built from"
                )
            if (
                evidence.gate_version != gate.gate_version
                or evidence.gate_input_fingerprint_sha256 != gate.input_fingerprint_sha256
            ):
                raise ValueError("evidence reference is bound to a different gate evaluation")
            if gate.gate_evaluation_id is not None and (
                evidence.gate_evaluation_id != gate.gate_evaluation_id
            ):
                raise ValueError("evidence reference is bound to a different stored gate row")
            if gate.decision is not GateDecision.PROCEED:
                raise ValueError("evaluable evidence can only follow a proceed decision")
            # R2-06: F1 and F2 must agree on the historical VI-002 exclusions.
            if evidence.historical_excluded_vi002_ids != list(gate.historical_excluded_vi002_ids):
                raise ValueError(
                    "evidence and gate disagree on the historical excluded VI-002 identities"
                )
        persistence = self.review_persistence
        if isinstance(persistence, SealedReviewEvaluation):
            if (persistence.run_id, persistence.patient_id, persistence.doctor_id) != (
                ident.run_id,
                ident.patient_id,
                ident.doctor_id,
            ):
                raise ValueError("sealed evaluation belongs to a different run or scope")
            if persistence.as_of_utc != ident.as_of_utc:
                raise ValueError("sealed evaluation was computed at a different as-of clock")
            if persistence.policy_version != ident.policy_version:
                raise ValueError("sealed evaluation used a different policy version")
            # R2-06: the sealed evaluation's stored gate identity is checked
            # directly against the F2 gate identity (which always carries it) and
            # only conditionally against the F1 *row id*, because the F1 receipt
            # genuinely does not expose one: an absent row-id projection is not a
            # contradiction and is never invented to satisfy this check.
            if evidence is not None and (
                persistence.gate_evaluation_id != evidence.gate_evaluation_id
                or persistence.gate_version != evidence.gate_version
                or persistence.gate_input_fingerprint_sha256
                != evidence.gate_input_fingerprint_sha256
            ):
                raise ValueError("sealed evaluation is bound to a different F2 gate identity")
            if gate is not None and (
                gate.gate_evaluation_id is not None
                and persistence.gate_evaluation_id != gate.gate_evaluation_id
            ):
                raise ValueError("sealed evaluation is bound to a different stored gate row")
            if gate is not None and (
                persistence.gate_version != gate.gate_version
                or persistence.gate_input_fingerprint_sha256 != gate.input_fingerprint_sha256
            ):
                raise ValueError("sealed evaluation is bound to a different gate evaluation")
            if evidence is not None and persistence.bridge_input_fingerprint_sha256 != (
                evidence.bridge_input_fingerprint_sha256
            ):
                raise ValueError("sealed evaluation is bound to different bridge evidence")
            if evidence is None:
                raise ValueError(
                    "a sealed evaluation requires the F2 evidence it was computed from"
                )
        return self

    @model_validator(mode="after")
    def _lifecycle(self) -> Self:
        status = self.status
        halted = status in HALTED_STATUSES
        if halted != (self.halt_reason is not None):
            raise ValueError("halt_reason is present iff the run is in a halted status")
        if status is RunStatus.NEEDS_VERIFICATION and self.halt_reason is not (
            HaltReason.UNVERIFIED_FACTS
        ):
            raise ValueError("needs_verification halts with halt_reason=unverified_facts")
        if (
            status is RunStatus.FAILED_RETRYABLE
            and self.halt_reason is not HaltReason.RETRY_EXHAUSTED
        ):
            raise ValueError("failed_retryable halts with halt_reason=retry_exhausted")
        approval = self.approval
        # An empty ApprovalDecision shape is *not* a recorded decision (R06).
        recorded = approval is not None and approval.recorded
        if recorded and approval.doctor_id != self.identity.doctor_id:
            raise ValueError("an approval decision must come from the run's own doctor")
        if (
            status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.NEEDS_VERIFICATION}
            and approval is not None
        ):
            raise ValueError("no approval can exist before the draft is approved-for-decision")
        if status is RunStatus.FINALIZING:
            if not recorded or approval.decision not in {
                ApprovalChoice.APPROVE,
                ApprovalChoice.EDIT,
            }:
                raise ValueError("finalizing requires an approve-or-edit decision")
            if self.draft_summary is None:
                raise ValueError("finalizing requires the draft it finalizes")
        if status is RunStatus.AWAITING_DECISION and (
            approval is not None or self.draft_summary is None
        ):
            raise ValueError("awaiting_decision has a draft and no recorded decision")
        if status is RunStatus.COMPLETED:
            if self.draft_summary is None or not recorded:
                raise ValueError("completed requires a draft and a recorded decision")
            if approval.decision is ApprovalChoice.REJECT:
                # Rejection completes with zero tasks and zero notifications, and it
                # never routes through the action-finalization state (R06).
                if self.pending_tasks or self.created_task_ids:
                    raise ValueError("a rejected run completes with no task")
                if any(event.node is NodeName.FINALIZE_ACTIONS for event in self.events):
                    raise ValueError("a rejected run never passes through finalize_actions")
            elif self.pending_tasks and not recorded:
                raise ValueError("task drafts exist only after an approve/edit decision")
        if self.pending_tasks and (
            status not in {RunStatus.FINALIZING, RunStatus.COMPLETED}
            or not recorded
            or approval.decision is ApprovalChoice.REJECT
        ):
            raise ValueError("task drafts exist only after an approve/edit decision")
        task_ids = {item.task_id for item in self.pending_tasks}
        if not set(self.created_task_ids) <= task_ids:
            raise ValueError("created_task_ids must reference pending task drafts")
        if self.created_task_ids and status not in {RunStatus.FINALIZING, RunStatus.COMPLETED}:
            raise ValueError("tasks are created only while finalizing or completed")
        # A denied persistence is an outcome, never a successful downstream
        # review completion (R06).
        if (
            self.review_persistence is not None
            and self.review_persistence.kind == "denied"
            and status in {RunStatus.FINALIZING, RunStatus.COMPLETED}
        ):
            raise ValueError("a denied persistence cannot be a successful review completion")
        finalize_events = [
            event for event in self.events if event.node is NodeName.FINALIZE_ACTIONS
        ]
        if finalize_events:
            detail = finalize_events[-1].detail
            if not isinstance(detail, FinalizeDetail):  # pragma: no cover - NodeEvent guarantees it
                raise ValueError("finalize event must carry a finalize detail")
            if detail.task_created != bool(self.created_task_ids):
                raise ValueError("finalize detail task_created must match created_task_ids")
            if approval is not None and detail.approval_decision != approval.decision:
                raise ValueError("finalize detail decision must match the approval")
        if self.retry_counts:
            for _node, count in self.retry_counts.items():
                if not 1 <= count <= 5:
                    raise ValueError("retry_counts values are bounded to 1..5")
        return self

    @model_validator(mode="after")
    def _gate_binding(self) -> Self:
        """No draft, comparison, prompt or decision can exist past a gate that did not proceed."""
        gate = self.verification_gate
        proceeded = gate is not None and gate.decision is GateDecision.PROCEED
        post_draft = self.status in {
            RunStatus.AWAITING_DECISION,
            RunStatus.FINALIZING,
            RunStatus.COMPLETED,
        }
        if gate is not None and gate.decision is GateDecision.HALT and post_draft:
            raise ValueError("a halting gate cannot coexist with a post-draft status")
        if (
            self.comparisons or self.review_flags or self.draft_summary is not None
        ) and not proceeded:
            raise ValueError("comparisons, review prompts and drafts require a proceed decision")
        if post_draft and not proceeded:
            raise ValueError("post-draft statuses require a proceed decision")
        if self.status is RunStatus.NEEDS_VERIFICATION and (
            gate is None or gate.decision is not GateDecision.HALT
        ):
            raise ValueError("needs_verification requires a recorded halt decision")
        return self

    @model_validator(mode="after")
    def _trace_gate_consistency(self) -> Self:
        """The **current** gate evaluation is mirrored by the latest trace event (R03).

        ``verification_gate`` is the current evaluation; ``events`` is an
        append-only historical record (R2-04). Only the most recent gate event is
        required to mirror the current evaluation - an earlier event records an
        earlier evaluation and is a historical trace, not a claim about the
        present gate. Binding a historical event to the evaluation that actually
        produced it needs a persisted evaluation identity that S0 does not have,
        so that association remains an S2 obligation and is not implemented here.
        """
        gate = self.verification_gate
        gate_events = [event for event in self.events if event.node is NodeName.FACT_VERIFY_GATE]
        if not gate_events:
            return self
        detail = gate_events[-1].detail
        if not isinstance(detail, GateDetail):  # pragma: no cover - NodeEvent guarantees it
            raise ValueError("fact_verify_gate event must carry a gate detail")
        if gate is None:
            raise ValueError("a gate trace requires the gate evaluation it mirrors")
        if gate.decision is GateDecision.UNAVAILABLE:
            # Never fabricate a proceed/halt trace decision for an
            # evaluation failure (owner decision D-01).
            raise ValueError("an unavailable gate produces no proceed/halt trace decision")
        if detail.decision != gate.decision.value:
            raise ValueError("gate trace decision differs from the evaluation")
        if detail.blocking_fact_count != gate.blocking_fact_count:
            raise ValueError("gate trace blocking_fact_count differs from the evaluation")
        if [item.semantic_key() for item in detail.issues] != [
            item.semantic_key() for item in gate.issues
        ]:
            raise ValueError("gate trace blockers differ from the evaluation's blockers")
        return self


def derive_task_id(namespace: uuid.UUID, action_key: str) -> str:
    """Pure helper: the derived ``uuid5(namespace, action_key)`` task identity (P0-R04).

    ``TASK_NAMESPACE`` and the action-key generation contract are **not** pinned
    by any accepted contract; S0 invents neither and defers both to S4 (owner
    decision D-05). This is UUID derivation only — it creates no task and grants
    no authority.
    """
    return str(uuid.uuid5(namespace, action_key))


__all__ = [
    "DEMO_NOTICE",
    "DETAIL_KIND_BY_NODE",
    "F2_CONTRACT_VERSION",
    "F2_EMITTED_INCOMPARABLE",
    "F2_HISTORY_POLICY",
    "HALTED_STATUSES",
    "MAX_BLOCKING_FACTS",
    "MAX_COMPARISONS",
    "MAX_ERRORS",
    "MAX_EVENTS",
    "MAX_EXTRACTION_ATTEMPTS",
    "MAX_FACTS",
    "MAX_HISTORY_OBSERVATIONS",
    "MAX_MANIFEST_OBSERVATIONS",
    "MAX_MANIFEST_OMISSIONS",
    "MAX_MERGED_EXCLUSIONS",
    "MAX_OBSERVATIONS",
    "MAX_PENDING_TASKS",
    "MAX_PERSISTED_ITEMS",
    "MAX_PERSISTED_LINKS",
    "MAX_SELECTED_CURRENT",
    "MAX_SELECTED_DOCUMENTS",
    "NODE_TOOLS",
    "OMISSION_REASON",
    "POLICY_REFERENCE_VERSION",
    "RB1_LOOKBACK_DAYS",
    "RB3_DR006_POLICY",
    "RB3_FINGERPRINT_VERSION",
    "RB3_POLICY_REFERENCE_SHA256",
    "RB3_RECEIPT_CONTRACT_VERSION",
    "STATE_SCHEMA_VERSION",
    "WORKFLOW_VERSION",
    "AgentError",
    "ApprovalChoice",
    "ApprovalDecision",
    "AssuranceLevel",
    "CheckpointRef",
    "ClaimCitation",
    "ComparisonResult",
    "ComparisonWindow",
    "DeniedReviewPersistence",
    "DetailKind",
    "DraftExecutionStatus",
    "DraftProvider",
    "DraftSummary",
    "ErrorCode",
    "EvaluableEvidenceRef",
    "EventDetail",
    "EvidenceExclusion",
    "ExclusionReason",
    "ExtractionAttempt",
    "Extractor",
    "FactField",
    "FinalizeDetail",
    "GateDecision",
    "GateDetail",
    "GateEvaluationRef",
    "GateIssueRef",
    "GateUnavailableReason",
    "HaltReason",
    "IncomparableReason",
    "Iso",
    "IssueType",
    "LayeredExclusions",
    "MappingVersion",
    "MeasureType",
    "MetadataValue",
    "NodeEvent",
    "NodeName",
    "NodeOutcome",
    "ObservationRole",
    "ObservationSource",
    "ObservationView",
    "PathReason",
    "PersistedExclusionRef",
    "PolicyVersion",
    "Preprocessing",
    "PromptVersion",
    "ProvenanceKind",
    "ProvenanceRef",
    "QualityFlag",
    "RB3DenialReason",
    "ReasonCode",
    "ReviewFlag",
    "ReviewHint",
    "ReviewItemState",
    "ReviewPersistenceOutcome",
    "ReviewRuleId",
    "RunIdentity",
    "RunStatus",
    "RunUuid",
    "SelectedDocumentRef",
    "SelectedObservationRef",
    "SelectedOmissionRef",
    "SelectedSourceManifest",
    "Self",
    "SemVer",
    "Sha256",
    "SharedGraphState",
    "Strict",
    "TaskDraft",
    "TaskUuid",
    "Token",
    "ToolName",
    "TraceGateDecision",
    "TriageDetail",
    "TriagePath",
    "TrustBasis",
    "TrustLevel",
    "Unit",
    "Uuid",
    "ValidationDetail",
    "ValidationOutcome",
    "ValidationState",
    "VerificationIssue",
    "VerificationStatus",
    "ViolationCode",
    "derive_task_id",
    "derived_trust_basis",
    "exact_delta",
    "selection_fingerprint",
]
