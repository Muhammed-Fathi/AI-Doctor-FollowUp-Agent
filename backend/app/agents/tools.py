"""P5-S1 bounded read-only tool adapters over the S0 typed shared state.

Owner authorization (2026-11-24) covers exactly three read-only adapters:

* ``read_verified_facts`` projects only the accepted F2 verified facts.
* ``read_observations`` projects only F2-selected observations and the actual
  F2 exclusions, explicitly labelled ``f2_selected_only``.
* ``compare_observations`` projects the accepted F2 comparisons exactly.

These are **narrowed internal projection semantics**, not the broader proposed
signatures in ``TOOL_CONTRACTS.md`` sections 3.4-3.5. There is no caller-supplied
patient id, document id, baseline, lookback, current list, trust label or fact
list. The trusted server supplies the principal, run identity, node and clocks.

This module is not an active runtime tool system. It is imported by tests and by
a future S2 orchestrator only. Nothing here is wired into a graph, checkpointer,
HTTP route, LLM, task or notification. The ``NODE_TOOLS`` check is a structural
shape check, not runtime clinical authorization.

No database writes, no audit rows and no network egress. The adapter returns a
bounded structured audit payload for S2 to persist; S1 does not claim a durable
audit trail.

**Transaction lifecycle (S1-R1).** The accepted F2 bridge rolls back its own
``BEGIN IMMEDIATE`` snapshot before returning. The stored-row reconciliation that
follows autobegins a fresh read transaction, and the adapter ends it with
``ROLLBACK`` before returning - on success and on every error path. ``COMMIT`` is
never used as a cleanup mechanism, a caller-owned session is never closed, and a
session that was already dirty on entry is left untouched.

**Snapshot authority limit (S1-R2).** The bridge's snapshot and the adapter's
stored-row reads are two independent reads. Detectable drift - a changed value,
unit, measure type, timestamp, source or trust label, a row that became
``rejected``, or a row beyond the accepted future-skew boundary - fails closed.
This does not make the two reads one atomic snapshot, and nothing here claims
that it does.

ACADEMIC / SYNTHETIC DATA ONLY - NOT FOR CLINICAL USE.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Generic, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from app.agents.state import (
    MAX_HISTORY_OBSERVATIONS,
    MAX_SELECTED_CURRENT,
    NODE_TOOLS,
    ComparisonResult,
    ComparisonWindow,
    EvidenceExclusion,
    ExclusionReason,
    IncomparableReason,
    NodeName,
    ObservationRole,
    ObservationView,
    ToolName,
    TrustBasis,
    VerifiedFact,
)
from app.core.clock import format_utc, parse_utc
from app.core.enums import (
    FactField,
    MeasureType,
    ObservationSource,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.core.errors import ApiError
from app.core.policies import Principal
from app.db.models import Document, ExtractedFact, Observation
from app.schemas.p5_review_evidence import EvaluableReviewEvidenceV2, ObservationV2
from app.services.monitoring import MonitoringInputError, admissibility_reason
from app.services.p5_evidence_bridge import (
    COMPARISON_HISTORY_VERSION,
    HISTORY_LOOKBACK_DAYS,
    build_run_evaluable_review_evidence,
)

#: Bounded evidence-identity list carried by the structured audit metadata.
MAX_AUDIT_EVIDENCE_IDS = MAX_SELECTED_CURRENT + MAX_HISTORY_OBSERVATIONS


class _Strict(BaseModel):
    """Unknown fields rejected, strict input, frozen instances (the S0 shape)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ToolErrorCode(StrEnum):
    """The closed S1 error-code vocabulary (``TOOL_CONTRACTS.md`` section 2)."""

    TOOL_NOT_ALLOWED = "E_TOOL_NOT_ALLOWED"
    NOT_FOUND = "E_NOT_FOUND"
    SCOPE_VIOLATION = "E_SCOPE_VIOLATION"
    UNVERIFIED_FACT = "E_UNVERIFIED_FACT"
    VALIDATION = "E_VALIDATION"


class ToolErrorReason(StrEnum):
    """Closed machine reason for one typed tool error."""

    TOOL_NOT_ALLOWED = "tool_not_allowed_for_node"
    RUN_NOT_FOUND = "run_not_found"
    FACT_NOT_FOUND = "fact_not_found"
    OBSERVATION_NOT_FOUND = "observation_not_found"
    DOCUMENT_NOT_FOUND = "document_not_found"
    ACCESS_DENIED = "access_denied"
    PATIENT_SCOPE_MISMATCH = "patient_scope_mismatch"
    DOCUMENT_SCOPE_MISMATCH = "document_scope_mismatch"
    UNVERIFIED_FACT = "unverified_fact"
    PRODUCER_EVIDENCE_INCONSISTENT = "producer_evidence_inconsistent"
    SESSION_NOT_CLEAN = "session_not_clean"
    PRODUCER_NOT_EVALUABLE = "producer_not_evaluable"
    INVALID_CONTEXT = "invalid_context"


class ToolError(_Strict):
    """A bounded typed error; it never carries a document body or a secret."""

    code: ToolErrorCode
    reason: ToolErrorReason
    message: str = Field(min_length=1, max_length=300)
    retryable: bool = False


class ToolAuditMetadata(_Strict):
    """Bounded structured audit data for S2 to persist.

    It records the tool, node, run, outcome class and evidence identities. It
    carries no payload body, no prompt and no document text.
    """

    tool: ToolName
    node: NodeName
    run_id: str
    outcome: Literal["ok", "error"]
    error_code: ToolErrorCode | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=MAX_AUDIT_EVIDENCE_IDS)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if (self.outcome == "error") != (self.error_code is not None):
            raise ValueError("an error outcome carries exactly one error code")
        return self


T = TypeVar("T")


class ToolResult(_Strict, Generic[T]):  # noqa: UP046 (py3.11-compatible generics)
    """The canonical discriminated envelope: ``ok`` or ``error``, never both."""

    ok: bool
    data: T | None = None
    error: ToolError | None = None
    duration_ms: int = Field(ge=0)
    audit: ToolAuditMetadata

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.ok and self.error is not None:
            raise ValueError("a successful result carries no error")
        if not self.ok and (self.data is not None or self.error is None):
            raise ValueError("a failed result carries an error and no data")
        if self.audit.outcome != ("ok" if self.ok else "error"):
            raise ValueError("the audit outcome must match the result")
        return self


class ObservationEvidence(_Strict):
    """The bounded ``read_observations`` payload: selected rows plus exclusions.

    ``scope`` is deliberately ``f2_selected_only``: the F2 envelope carries the
    run's selected current observations and the excluded history identities,
    not the full history dataset.
    """

    scope: Literal["f2_selected_only"] = "f2_selected_only"
    observations: list[ObservationView] = Field(
        default_factory=list, max_length=MAX_SELECTED_CURRENT
    )
    exclusions: list[EvidenceExclusion] = Field(
        default_factory=list, max_length=MAX_HISTORY_OBSERVATIONS
    )
    no_current_reason: Literal["no_current_selected"] | None = None


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Trusted server-supplied context. Nothing here is agent-controlled.

    ``db`` must be a fresh clean Session: the accepted F2 bridge opens its own
    ``BEGIN IMMEDIATE`` snapshot and rolls it back, and refuses a session that
    is already in a transaction or holds pending writes.
    """

    db: Session
    principal: Principal
    run_id: str
    node: NodeName
    validation_clock: datetime
    upload_root: str


class ToolPermissionError(Exception):
    """Raised by the structural pre-call allowlist guard."""

    def __init__(self, node: NodeName, tool: ToolName) -> None:
        self.node = node
        self.tool = tool
        super().__init__(f"{tool.value} is not permitted for {node.value}")


def assert_tool_allowed(node: NodeName, tool: ToolName) -> None:
    """Structural pre-call guard over the S0 ``NODE_TOOLS`` allowlist.

    This is a shape check, not runtime authorization and not a clinical
    decision. An unknown or unauthorized combination raises.
    """
    if tool not in NODE_TOOLS.get(node, frozenset()):
        raise ToolPermissionError(node, tool)


def _start() -> float:
    return time.perf_counter()


def _elapsed_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _bounded(text: str) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:300] if collapsed else "Producer request failed."


def _tool_error(code: ToolErrorCode, reason: ToolErrorReason, message: str) -> ToolError:
    return ToolError(code=code, reason=reason, message=_bounded(message))


def _audit(
    ctx: ToolContext,
    tool: ToolName,
    outcome: Literal["ok", "error"],
    error_code: ToolErrorCode | None = None,
    evidence_ids: tuple[str, ...] = (),
) -> ToolAuditMetadata:
    return ToolAuditMetadata(
        tool=tool,
        node=ctx.node,
        run_id=ctx.run_id,
        outcome=outcome,
        error_code=error_code,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
    )


def _error_from(
    ctx: ToolContext,
    tool: ToolName,
    start: float,
    error: ToolError,
    evidence_ids: tuple[str, ...] = (),
) -> ToolResult[None]:
    return ToolResult(
        ok=False,
        data=None,
        error=error,
        duration_ms=_elapsed_ms(start),
        audit=_audit(ctx, tool, "error", error.code, evidence_ids),
    )


def _ok(  # noqa: UP047 (py3.11-compatible generics)
    ctx: ToolContext,
    tool: ToolName,
    start: float,
    data: T,
    evidence_ids: tuple[str, ...] = (),
) -> ToolResult[T]:
    return ToolResult(
        ok=True,
        data=data,
        error=None,
        duration_ms=_elapsed_ms(start),
        audit=_audit(ctx, tool, "ok", None, evidence_ids),
    )


def _denied(ctx: ToolContext, tool: ToolName) -> ToolError | None:
    try:
        assert_tool_allowed(ctx.node, tool)
    except ToolPermissionError as exc:
        return _tool_error(
            ToolErrorCode.TOOL_NOT_ALLOWED,
            ToolErrorReason.TOOL_NOT_ALLOWED,
            str(exc),
        )
    return None


def _api_error(exc: ApiError) -> ToolError:
    if exc.status_code == 404:
        return _tool_error(ToolErrorCode.NOT_FOUND, ToolErrorReason.RUN_NOT_FOUND, exc.detail)
    if exc.status_code == 403:
        return _tool_error(ToolErrorCode.SCOPE_VIOLATION, ToolErrorReason.ACCESS_DENIED, exc.detail)
    return _tool_error(ToolErrorCode.VALIDATION, ToolErrorReason.PRODUCER_NOT_EVALUABLE, exc.detail)


def _evidence(
    ctx: ToolContext, tool: ToolName, start: float, *, started_clean: bool
) -> EvaluableReviewEvidenceV2 | ToolResult[None]:
    """Call the accepted F2 bridge first, on a fresh clean session.

    The bridge authenticates the doctor session and patient assignment, re-runs
    the F1 gate, re-hashes the selected bytes, builds the evidence and rolls
    back. S1 never calls it with a dirty or already-transacting session.
    """
    if not isinstance(ctx.run_id, str) or not ctx.run_id.strip():
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.INVALID_CONTEXT,
                "A run identity is required.",
            ),
        )
    if not isinstance(ctx.upload_root, str) or not ctx.upload_root:
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.INVALID_CONTEXT,
                "A trusted upload root is required.",
            ),
        )
    if not started_clean:
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.SESSION_NOT_CLEAN,
                "The adapter requires a fresh clean session.",
            ),
        )
    try:
        return build_run_evaluable_review_evidence(
            ctx.db,
            principal=ctx.principal,
            run_id=ctx.run_id,
            validation_clock=ctx.validation_clock,
            upload_root=ctx.upload_root,
        )
    except ApiError as exc:
        return _error_from(ctx, tool, start, _api_error(exc))


def _decimal(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("invalid stored observation value") from None
    if not parsed.is_finite():
        raise ValueError("invalid stored observation value")
    return parsed


def _instant(value: object) -> str:
    try:
        return format_utc(parse_utc(value))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("invalid stored observation timestamp") from None


class _Drift(Exception):
    """Internal signal: a stored row disagrees with the accepted F2 projection."""

    def __init__(self, code: ToolErrorCode, reason: ToolErrorReason, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.reason = reason
        self.message = message


def _session_is_clean(db: Session) -> bool:
    """The accepted bridge's own precondition, reused by the adapter."""
    return not (db.in_transaction() or db.new or db.dirty or db.deleted)


def _end_adapter_transaction(ctx: ToolContext, *, started_clean: bool) -> None:
    """End the read transaction this adapter opened. Never COMMIT.

    The accepted F2 bridge rolls back its own snapshot before returning. The
    stored-row reconciliation that follows then autobegins a fresh read
    transaction under SQLAlchemy, and it must not outlive the call: an open
    transaction would pin a read snapshot on a session the caller still owns.
    It is ended with ROLLBACK. COMMIT is never used, because it would turn a
    read-only adapter into a writer. A session that was already dirty on entry
    is left untouched, so no caller-owned pending write is ever discarded and
    no caller-owned session is ever closed.
    """
    if started_clean and ctx.db.in_transaction():
        ctx.db.rollback()


def _require_admissible(stored: Observation, *, patient_id: str, as_of_utc: datetime) -> None:
    """Apply the accepted admissibility predicate to the post-bridge row.

    The F2 bridge proved admissibility inside its own snapshot. Re-applying the
    same accepted predicate to the row read afterwards is what detects drift
    between the two reads: a row that became ``rejected`` or that now exceeds
    the accepted future-skew boundary can no longer be returned as an eligible
    current observation. No new boundary is invented here.
    """
    try:
        reason = admissibility_reason(stored, patient_id=patient_id, as_of_utc=as_of_utc)
    except MonitoringInputError as exc:
        if exc.code == "E_SCOPE_VIOLATION":
            raise _Drift(
                ToolErrorCode.SCOPE_VIOLATION,
                ToolErrorReason.PATIENT_SCOPE_MISMATCH,
                "A stored observation belongs to a different patient.",
            ) from None
        raise _Drift(
            ToolErrorCode.VALIDATION,
            ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
            "A stored observation is malformed.",
        ) from None
    if reason is not None:
        raise _Drift(
            ToolErrorCode.VALIDATION,
            ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
            "A stored observation is no longer admissible.",
        )


def _stored_view(
    stored: Observation,
    *,
    role: ObservationRole,
    source_document_id: str | None,
) -> ObservationView:
    """Build the S0 view from the stored row; the S0 validators do the rest."""
    return ObservationView(
        observation_id=stored.id,
        patient_id=stored.patient_id,
        role=role,
        measure_type=MeasureType(stored.measure_type),
        value=_decimal(stored.value),
        unit=Unit(stored.unit),
        measured_at=_instant(stored.measured_at),
        source=ObservationSource(stored.source),
        validation=ValidationState(stored.validation),
        trust_level=TrustLevel(stored.trust_level),
        verified_by=stored.verified_by_user_id,
        verified_at=stored.verified_at,
        source_fact_id=stored.source_fact_id,
        source_document_id=source_document_id,
    )


def _reconcile_selected(
    ctx: ToolContext, evidence: EvaluableReviewEvidenceV2, row: ObservationV2
) -> ObservationView:
    """Read the selected row and prove it still matches the F2 projection.

    The F2 envelope is never trusted on its own for the *current* row: the
    stored value, measure type, unit, timestamp, source, trust label and fact
    lineage are compared field by field. Any drift fails closed, so a
    ``current_value`` taken from this view and a ``baseline_value`` taken from
    a stored row can never be silently combined from disagreeing snapshots.
    """
    stored = ctx.db.get(Observation, row.observation_id)
    if stored is None:
        raise _Drift(
            ToolErrorCode.NOT_FOUND,
            ToolErrorReason.OBSERVATION_NOT_FOUND,
            "A selected observation is not stored.",
        )
    if stored.patient_id != evidence.patient_id:
        raise _Drift(
            ToolErrorCode.SCOPE_VIOLATION,
            ToolErrorReason.PATIENT_SCOPE_MISMATCH,
            "A selected observation belongs to a different patient.",
        )
    if row.source_document_id is not None and (
        row.source_document_id not in evidence.selected_document_ids
    ):
        raise _Drift(
            ToolErrorCode.SCOPE_VIOLATION,
            ToolErrorReason.DOCUMENT_SCOPE_MISMATCH,
            "A selected observation lineage document is outside the run selection.",
        )
    _require_admissible(stored, patient_id=evidence.patient_id, as_of_utc=ctx.validation_clock)
    view = _stored_view(
        stored, role=ObservationRole.SELECTED_CURRENT, source_document_id=row.source_document_id
    )
    if (
        view.measure_type.value != row.measure_type
        or view.unit.value != row.unit
        or view.source.value != row.source
        or view.trust_level.value != row.trust_level
        or view.source_fact_id != row.source_fact_id
        or view.value != row.value
        or view.measured_at != row.measured_at
    ):
        raise _Drift(
            ToolErrorCode.VALIDATION,
            ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
            "A stored observation differs from the F2 projection.",
        )
    return view


def _history_view(ctx: ToolContext, stored: Observation, *, patient_id: str) -> ObservationView:
    """Build a HISTORY view, resolving document lineage only from stored rows."""
    document_id: str | None = None
    if stored.source_fact_id is not None:
        fact = ctx.db.get(ExtractedFact, stored.source_fact_id)
        if fact is None or fact.patient_id != patient_id:
            raise _Drift(
                ToolErrorCode.SCOPE_VIOLATION,
                ToolErrorReason.PATIENT_SCOPE_MISMATCH,
                "A comparison baseline lineage is outside the patient scope.",
            )
        document_id = fact.document_id
    return _stored_view(stored, role=ObservationRole.HISTORY, source_document_id=document_id)


def _expected_trust_basis(current: ObservationView, baseline: ObservationView | None) -> TrustBasis:
    """Mirror the accepted producer's label derivation; invent nothing."""
    if baseline is not None and current.trust_level != baseline.trust_level:
        return TrustBasis.MIXED
    if current.trust_level is TrustLevel.DOCTOR_VERIFIED:
        return TrustBasis.DOCTOR_VERIFIED
    return TrustBasis.SELF_REPORTED


def read_verified_facts(ctx: ToolContext) -> ToolResult[list[VerifiedFact]]:
    """Project the accepted F2 verified facts, reconciled with stored rows.

    Caller-authored evidence is never accepted: the only input is the trusted
    context, and every F2 fact is checked against the stored fact, its patient,
    its document scope and the run's selected document set.
    """
    start = _start()
    tool = ToolName.READ_VERIFIED_FACTS
    denied = _denied(ctx, tool)
    if denied is not None:
        return _error_from(ctx, tool, start, denied)
    started_clean = _session_is_clean(ctx.db)
    facts: list[VerifiedFact] = []
    evidence_ids: list[str] = []
    try:
        evidence = _evidence(ctx, tool, start, started_clean=started_clean)
        if isinstance(evidence, ToolResult):
            return evidence
        for row in evidence.verified_facts:
            stored = ctx.db.get(ExtractedFact, row.fact_id)
            if stored is None:
                raise _Drift(
                    ToolErrorCode.NOT_FOUND,
                    ToolErrorReason.FACT_NOT_FOUND,
                    "A verified fact is not stored.",
                )
            if stored.verification_status != "verified":
                raise _Drift(
                    ToolErrorCode.UNVERIFIED_FACT,
                    ToolErrorReason.UNVERIFIED_FACT,
                    "A projected fact is not verified.",
                )
            if stored.patient_id != evidence.patient_id:
                raise _Drift(
                    ToolErrorCode.SCOPE_VIOLATION,
                    ToolErrorReason.PATIENT_SCOPE_MISMATCH,
                    "A verified fact belongs to a different patient.",
                )
            if stored.document_id != row.document_id:
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "The stored fact document differs from the F2 projection.",
                )
            document = ctx.db.get(Document, stored.document_id)
            if document is None:
                raise _Drift(
                    ToolErrorCode.NOT_FOUND,
                    ToolErrorReason.DOCUMENT_NOT_FOUND,
                    "A verified fact document is not stored.",
                )
            if document.patient_id != evidence.patient_id:
                raise _Drift(
                    ToolErrorCode.SCOPE_VIOLATION,
                    ToolErrorReason.DOCUMENT_SCOPE_MISMATCH,
                    "A verified fact document belongs to a different patient.",
                )
            if stored.document_id not in evidence.selected_document_ids:
                raise _Drift(
                    ToolErrorCode.SCOPE_VIOLATION,
                    ToolErrorReason.DOCUMENT_SCOPE_MISMATCH,
                    "A verified fact document is outside the run selection.",
                )
            if (
                stored.field_name != row.field_name
                or stored.normalized_value != row.normalized_value
                or stored.unit != row.unit
                or stored.corrected_from_fact_id != row.corrected_from_fact_id
            ):
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "The stored fact differs from the F2 projection.",
                )
            facts.append(
                VerifiedFact(
                    fact_id=row.fact_id,
                    document_id=row.document_id,
                    field_name=FactField(row.field_name),
                    normalized_value=row.normalized_value,
                    unit=row.unit,
                    corrected_from_fact_id=row.corrected_from_fact_id,
                    verification_status="verified",
                    trust_basis="doctor_verified",
                    patient_id=stored.patient_id,
                )
            )
            evidence_ids.append(row.fact_id)
    except _Drift as exc:
        return _error_from(ctx, tool, start, _tool_error(exc.code, exc.reason, exc.message))
    except (ValidationError, ValueError):
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                "A projected fact is not representable in the S0 state.",
            ),
            tuple(evidence_ids),
        )
    finally:
        _end_adapter_transaction(ctx, started_clean=started_clean)
    return _ok(ctx, tool, start, facts, tuple(evidence_ids))


def read_observations(ctx: ToolContext) -> ToolResult[ObservationEvidence]:
    """Project F2-selected observations and actual F2 exclusions only.

    The result is labelled ``f2_selected_only``. It is not a full-history
    retrieval, and no excluded observation is silently dropped: every F2
    exclusion is returned with its producer reason code.
    """
    start = _start()
    tool = ToolName.READ_OBSERVATIONS
    denied = _denied(ctx, tool)
    if denied is not None:
        return _error_from(ctx, tool, start, denied)
    started_clean = _session_is_clean(ctx.db)
    observations: list[ObservationView] = []
    exclusions: list[EvidenceExclusion] = []
    evidence_ids: list[str] = []
    try:
        evidence = _evidence(ctx, tool, start, started_clean=started_clean)
        if isinstance(evidence, ToolResult):
            return evidence
        for row in evidence.selected_observations:
            view = _reconcile_selected(ctx, evidence, row)
            observations.append(view)
            evidence_ids.append(view.observation_id)
        for item in evidence.history_exclusions:
            stored = ctx.db.get(Observation, item.observation_id)
            if stored is None:
                raise _Drift(
                    ToolErrorCode.NOT_FOUND,
                    ToolErrorReason.OBSERVATION_NOT_FOUND,
                    "An excluded observation is not stored.",
                )
            if stored.patient_id != evidence.patient_id:
                raise _Drift(
                    ToolErrorCode.SCOPE_VIOLATION,
                    ToolErrorReason.PATIENT_SCOPE_MISMATCH,
                    "An excluded observation belongs to a different patient.",
                )
            exclusions.append(
                EvidenceExclusion(
                    observation_id=item.observation_id,
                    reason_code=ExclusionReason(item.reason_code),
                )
            )
            evidence_ids.append(item.observation_id)
    except _Drift as exc:
        return _error_from(ctx, tool, start, _tool_error(exc.code, exc.reason, exc.message))
    except (ValidationError, ValueError):
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                "A projected observation is not representable in the S0 state.",
            ),
            tuple(evidence_ids),
        )
    finally:
        _end_adapter_transaction(ctx, started_clean=started_clean)
    return _ok(
        ctx,
        tool,
        start,
        ObservationEvidence(
            scope="f2_selected_only",
            observations=observations,
            exclusions=exclusions,
            no_current_reason=evidence.no_current_reason,
        ),
        tuple(evidence_ids),
    )


def compare_observations(ctx: ToolContext) -> ToolResult[list[ComparisonResult]]:
    """Project the accepted F2 comparisons exactly.

    There is no caller-supplied baseline or lookback: the F2 bridge selected the
    baseline under its pinned history policy and computed the delta. This
    adapter never reselects, never recalculates and never converts units. The
    F2 delta is the output; it is only cross-checked, never replaced.

    The current row and the baseline row are reconciled against their stored
    rows and against the accepted admissibility predicate before any value is
    emitted, so a current value and a baseline value can never be combined from
    rows that drifted after the bridge's snapshot.
    """
    start = _start()
    tool = ToolName.COMPARE_OBSERVATIONS
    denied = _denied(ctx, tool)
    if denied is not None:
        return _error_from(ctx, tool, start, denied)
    started_clean = _session_is_clean(ctx.db)
    comparisons: list[ComparisonResult] = []
    evidence_ids: list[str] = []
    try:
        evidence = _evidence(ctx, tool, start, started_clean=started_clean)
        if isinstance(evidence, ToolResult):
            return evidence
        selected_by_id = {row.observation_id: row for row in evidence.selected_observations}
        for item in evidence.comparisons:
            selected = selected_by_id.get(item.current_observation_id)
            if selected is None:
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "A comparison current is outside the F2 selection.",
                )
            current_view = _reconcile_selected(ctx, evidence, selected)
            if (
                current_view.measure_type.value != item.measure_type
                or current_view.unit.value != item.unit
            ):
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "A comparison measure or unit differs from the reconciled current row.",
                )
            baseline_view: ObservationView | None = None
            if item.baseline_observation_id is not None:
                baseline = ctx.db.get(Observation, item.baseline_observation_id)
                if baseline is None:
                    raise _Drift(
                        ToolErrorCode.NOT_FOUND,
                        ToolErrorReason.OBSERVATION_NOT_FOUND,
                        "A comparison baseline is not stored.",
                    )
                if baseline.patient_id != evidence.patient_id:
                    raise _Drift(
                        ToolErrorCode.SCOPE_VIOLATION,
                        ToolErrorReason.PATIENT_SCOPE_MISMATCH,
                        "A comparison baseline belongs to a different patient.",
                    )
                baseline_view = _history_view(ctx, baseline, patient_id=evidence.patient_id)
                _require_admissible(
                    baseline, patient_id=evidence.patient_id, as_of_utc=ctx.validation_clock
                )
                if (
                    baseline_view.measure_type.value != item.measure_type
                    or baseline_view.unit.value != item.unit
                ):
                    raise _Drift(
                        ToolErrorCode.VALIDATION,
                        ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                        "A comparison baseline has a different measure or unit.",
                    )
                baseline_stamp = parse_utc(baseline_view.measured_at)
                current_stamp = parse_utc(current_view.measured_at)
                # The accepted F2 producer selects a baseline with an inclusive
                # lower bound and an exclusive upper bound, relative to the
                # current observation's own timestamp:
                #     current - HISTORY_LOOKBACK_DAYS <= baseline < current
                # The same constant is reused here; no new period is introduced.
                if not (
                    current_stamp - timedelta(days=HISTORY_LOOKBACK_DAYS)
                    <= baseline_stamp
                    < current_stamp
                ):
                    raise _Drift(
                        ToolErrorCode.VALIDATION,
                        ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                        "A comparison baseline is outside the accepted F2 history window.",
                    )
            if item.trust_basis != _expected_trust_basis(current_view, baseline_view):
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "A comparison trust label disagrees with the reconciled rows.",
                )
            if item.comparable and (item.baseline_observation_id is None or item.delta is None):
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "A comparable result lacks a baseline or a delta.",
                )
            if not item.comparable and (item.incomparable_reason is None or item.delta is not None):
                raise _Drift(
                    ToolErrorCode.VALIDATION,
                    ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                    "An incomparable result lacks a reason or carries a delta.",
                )
            comparisons.append(
                ComparisonResult(
                    current_observation_id=item.current_observation_id,
                    baseline_observation_id=item.baseline_observation_id,
                    measure_type=MeasureType(item.measure_type),
                    unit=Unit(item.unit),
                    comparable=item.comparable,
                    delta=item.delta,
                    incomparable_reason=(
                        IncomparableReason(item.incomparable_reason)
                        if item.incomparable_reason
                        else None
                    ),
                    trust_basis=TrustBasis(item.trust_basis),
                    history_policy=ComparisonWindow(COMPARISON_HISTORY_VERSION),
                    current_value=current_view.value,
                    baseline_value=(baseline_view.value if baseline_view is not None else None),
                )
            )
            evidence_ids.append(item.current_observation_id)
            if item.baseline_observation_id:
                evidence_ids.append(item.baseline_observation_id)
    except _Drift as exc:
        return _error_from(ctx, tool, start, _tool_error(exc.code, exc.reason, exc.message))
    except (ValidationError, ValueError):
        return _error_from(
            ctx,
            tool,
            start,
            _tool_error(
                ToolErrorCode.VALIDATION,
                ToolErrorReason.PRODUCER_EVIDENCE_INCONSISTENT,
                "A projected comparison is not representable in the S0 state.",
            ),
            tuple(evidence_ids),
        )
    finally:
        _end_adapter_transaction(ctx, started_clean=started_clean)
    return _ok(ctx, tool, start, comparisons, tuple(evidence_ids))


__all__ = [
    "MAX_AUDIT_EVIDENCE_IDS",
    "ObservationEvidence",
    "ToolAuditMetadata",
    "ToolContext",
    "ToolError",
    "ToolErrorCode",
    "ToolErrorReason",
    "ToolPermissionError",
    "ToolResult",
    "assert_tool_allowed",
    "compare_observations",
    "read_observations",
    "read_verified_facts",
]
