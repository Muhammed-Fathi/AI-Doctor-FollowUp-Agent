"""P4 R2-A + C-37A: bounded *inspection* of selected synthetic SQLite data.

The result is NOT EvaluableReviewEvidenceV2, a real run-scoped gate, a
snapshot/freshness attestation or authorization to invoke rule engines.
This internal service must only receive a server-derived Principal and a
single ORM Session from the caller; it creates no API, run or review item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import parse_utc, to_utc
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import UserSession, VerificationIssue
from app.services.monitoring import ObservationSnapshot
from app.services.p4_document_preflight import (
    MAX_SELECTED_DOCUMENTS,
    SelectedDocumentPreflight,
    inspect_selected_document_verification,
)
from app.services.p4_explicit_history import (
    MAX_CURRENT,
    ExplicitHistoryResult,
    compare_explicit_current_with_history,
)
from app.services.p4_readonly_provenance import load_readonly_provenance_evidence

ISSUE_STATES = frozenset({"open", "resolved", "superseded"})


@dataclass(frozen=True, slots=True)
class SelectedIssueState:
    document_id: str
    issue_type: str
    state: str


@dataclass(frozen=True, slots=True)
class SelectedSourceExclusion:
    observation_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class SelectedEvidenceInspection:
    """Immutable internal P4 inspection; deliberately never runtime evaluable."""

    patient_id: str
    doctor_user_id: str
    as_of_utc: datetime
    document_ids: tuple[str, ...]
    current_observation_ids: tuple[str, ...]
    selected_document_preflight: SelectedDocumentPreflight | None
    selected_issue_states: tuple[SelectedIssueState, ...]
    source_exclusions: tuple[SelectedSourceExclusion, ...]
    comparison: ExplicitHistoryResult
    run_gate_status: Literal["unavailable"] = field(default="unavailable", init=False)
    run_gate_completed: bool = field(default=False, init=False)
    runtime_evaluable: bool = field(default=False, init=False)
    policy_status: Literal["unapproved"] = field(default="unapproved", init=False)


def _ids(value: object, *, min_count: int, max_count: int) -> tuple[str, ...]:
    if (
        not isinstance(value, tuple)
        or not min_count <= len(value) <= max_count
        or any(not isinstance(x, str) or not x.strip() for x in value)
        or len(set(value)) != len(value)
    ):
        raise ApiError(400, ErrorCode.VALIDATION, "Invalid explicit evidence selection.")
    return tuple(sorted(value))


def inspect_selected_evidence(
    db: Session,
    *,
    principal: Principal,
    patient_id: str,
    document_ids: tuple[str, ...],
    current_observation_ids: tuple[str, ...],
    as_of_utc: datetime,
    baseline_lookback_days: int,
) -> SelectedEvidenceInspection:
    """Read synthetic, patient-scoped state; compare explicitly selected current/history.

    No client boolean/count, doc text, medical evaluation, policy defaults or
    write. All component reads use the *same ORM session*; this is NOT a
    serializable source snapshot or a durable workflow-run freshness proof.
    """
    docs = _ids(document_ids, min_count=0, max_count=MAX_SELECTED_DOCUMENTS)
    currents = _ids(current_observation_ids, min_count=1, max_count=MAX_CURRENT)
    try:
        clock = to_utc(as_of_utc)
    except (TypeError, ValueError, AttributeError):
        raise ApiError(400, ErrorCode.VALIDATION, "An aware evaluation clock is required.") from None
    if not isinstance(principal, Principal):
        raise ApiError(403, ErrorCode.FORBIDDEN, "A server identity is required.")

    # Prevent inspection from silently consuming unflushed caller mutations.
    if db.new or db.dirty or db.deleted:
        raise ApiError(400, ErrorCode.VALIDATION, "An unchanged database session is required.")
    with db.no_autoflush:
        # A Principal object alone is insufficient; bind it to a persisted,
        # active, unrevoked, time-valid session and matching stored user.
        row = db.execute(
            select(UserSession).where(
                UserSession.id == principal.session_id,
                UserSession.user_id == principal.user_id,
            )
        ).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            raise ApiError(403, ErrorCode.FORBIDDEN, "An active authenticated session is required.")
        try:
            valid_session = (
                parse_utc(row.created_at) <= clock < parse_utc(row.expires_at)
            )
        except (TypeError, ValueError, AttributeError):
            valid_session = False
        if not valid_session:
            raise ApiError(403, ErrorCode.FORBIDDEN, "An active authenticated session is required.")

        # This call checks the actual stored active doctor and assigned synthetic
        # patient, and projects ALL scoped rows before an explicit ID selector.
        evidence = load_readonly_provenance_evidence(
            db, principal=principal, patient_id=patient_id, as_of_utc=clock
        )
        preflight = (
            inspect_selected_document_verification(
                db, principal=principal, patient_id=patient_id, document_ids=docs
            )
            if docs
            else None
        )
        issues: list[SelectedIssueState] = []
        if docs:
            rows = list(
                db.execute(
                    select(VerificationIssue).where(
                        VerificationIssue.document_id.in_(docs),
                        VerificationIssue.patient_id == patient_id,
                    )
                ).scalars()
            )
            if len(rows) > 100:
                raise ApiError(400, ErrorCode.VALIDATION, "Too many selected issue records.")
            for issue in rows:
                if issue.state not in ISSUE_STATES:
                    raise ApiError(400, ErrorCode.VALIDATION, "Unsupported persisted issue state.")
                issues.append(SelectedIssueState(issue.document_id, issue.issue_type, issue.state))

        by_id = {record.observation.id: record for record in evidence.records}
        if any(obs_id not in by_id for obs_id in currents):
            # Foreign/missing IDs are deliberately indistinguishable.
            raise ApiError(404, ErrorCode.NOT_FOUND, "Selected observation is unavailable.")

        included: dict[str, ObservationSnapshot] = {}
        excluded: list[SelectedSourceExclusion] = []
        for obs_id, record in by_id.items():
            entry = record.observation
            if record.source == "verified_document":
                if (
                    record.source_fact_verification_status != "verified"
                    or not record.source_fact_id
                    or not record.source_document_id
                ):
                    excluded.append(SelectedSourceExclusion(obs_id, "verified_lineage_unavailable"))
                    continue
                if record.source_document_id not in docs:
                    excluded.append(SelectedSourceExclusion(obs_id, "source_document_not_selected"))
                    continue
                if preflight is None or not preflight.candidate_documents_clear:
                    excluded.append(SelectedSourceExclusion(obs_id, "selected_document_preflight_blocked"))
                    continue
                if entry.trust_level != "doctor_verified":
                    excluded.append(SelectedSourceExclusion(obs_id, "stored_trust_source_mismatch"))
                    continue
            elif (
                record.source not in {"seed_fixture", "patient_checkin"}
                or entry.trust_level != "self_reported_validated"
            ):
                excluded.append(SelectedSourceExclusion(obs_id, "stored_trust_source_mismatch"))
                continue
            included[obs_id] = entry

        # Fail closed rather than let an ineligible explicitly selected current
        # observation silently disappear and change a downstream delta.
        if any(obs_id not in included for obs_id in currents):
            raise ApiError(400, ErrorCode.VALIDATION, "Selected observation provenance is ineligible.")

        current_rows = tuple(included[obs_id] for obs_id in currents)
        history_rows = tuple(
            included[obs_id] for obs_id in sorted(included) if obs_id not in currents
        )
        comparison = compare_explicit_current_with_history(
            current=current_rows,
            history=history_rows,
            patient_id=patient_id,
            as_of_utc=clock,
            baseline_lookback_days=baseline_lookback_days,
        )

    return SelectedEvidenceInspection(
        patient_id=evidence.patient_id,
        doctor_user_id=principal.user_id,
        as_of_utc=clock,
        document_ids=docs,
        current_observation_ids=currents,
        selected_document_preflight=preflight,
        selected_issue_states=tuple(sorted(issues, key=lambda x: (x.document_id, x.issue_type))),
        source_exclusions=tuple(sorted(excluded, key=lambda x: (x.observation_id, x.reason))),
        comparison=comparison,
    )


__all__ = [
    "ISSUE_STATES",
    "SelectedEvidenceInspection",
    "SelectedIssueState",
    "SelectedSourceExclusion",
    "inspect_selected_evidence",
]
