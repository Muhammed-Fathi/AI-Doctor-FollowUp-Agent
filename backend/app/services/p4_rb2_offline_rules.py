"""Pure P4-RB2 six-rule evaluation over explicitly SYNTHETIC fixture records.

No database, filesystem, network, F1 gate, run, API, graph, LLM or task access.
Neither results nor caller-supplied fixture lineage are proof of verification.
NOT FOR CLINICAL USE.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from itertools import combinations

from app.core.clock import parse_utc, to_utc
from app.core.enums import MEASURE_PLAUSIBLE_BANDS, MEASURE_UNITS, MeasureType
from app.schemas.p4_rb2_offline_rules import (
    OfflineEvidenceExclusion,
    OfflineObservation,
    OfflineRuleError,
    OfflineRuleFlag,
    OfflineRuleInput,
    OfflineRulePolicy,
    OfflineRuleResult,
)

_LABELS = {
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "heart_rate": "Heart rate",
    "glucose": "Glucose",
}
_UNITS = {
    key.value: frozenset(value.value for value in values)
    for key, values in MEASURE_UNITS.items()
}
_BANDS = {
    key.value: (Decimal(str(lo)), Decimal(str(hi)))
    for key, (lo, hi) in MEASURE_PLAUSIBLE_BANDS.items()
}
_HINT_ORDER = {"verification_needed": 0, "data_quality": 1, "change_to_review": 2}
_RULES = ("DR-001", "DR-003", "DR-005", "DR-006", "DR-008", "DR-009")
_ISSUES = ("VI-001", "VI-002", "VI-003", "VI-004", "VI-005", "VI-006")
_NOTICE = (
    "DEMO review prompts only — not clinical risk assessment. "
    "Not for clinical use."
)
_SUFFIXES = {
    "doctor_verified": "",
    "self_reported": " (self-reported)",
    "mixed": " (includes self-reported values)",
}


def _decimal(value: object, *, policy: bool = False) -> Decimal:
    code = "E_RULE_POLICY_INVALID" if policy else "E_VALIDATION"
    if isinstance(value, bool):
        raise OfflineRuleError(code, "Boolean cannot be a numeric measurement.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise OfflineRuleError(code, "Invalid finite numeric value.") from None
    if not amount.is_finite():
        raise OfflineRuleError(code, "Invalid finite numeric value.")
    return amount


def _clock(value: datetime | str | None) -> datetime | None:
    try:
        if isinstance(value, datetime):
            return to_utc(value)
        if isinstance(value, str):
            return parse_utc(value)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return None
    return None


def _policy(policy: OfflineRulePolicy, clock: datetime) -> dict[str, Decimal]:
    if not isinstance(policy, OfflineRulePolicy):
        raise OfflineRuleError("E_RULE_POLICY_INVALID", "Typed fixture policy required.")
    if (
        policy.policy_version != "demo-policy-1.1.0"
        or policy.demo_only is not True
        or _clock(policy.demo_as_of_utc) != clock
        or policy.notice != _NOTICE
        or type(policy.baseline_lookback_days) is not int
        or policy.baseline_lookback_days != 90
        or type(policy.stale_measurement_days) is not int
        or policy.stale_measurement_days != 30
        or type(policy.max_items_per_type) is not int
        or policy.max_items_per_type != 3
        or policy.enabled_rules != _RULES
        or policy.enabled_verification_issues != _ISSUES
    ):
        raise OfflineRuleError("E_RULE_POLICY_INVALID", "R3-A fixture values differ.")
    parameters = {
        "systolic_bp": (policy.demo_delta_systolic_mmHg, "10"),
        "diastolic_bp": (policy.demo_delta_diastolic_mmHg, "8"),
        "heart_rate": (policy.demo_delta_heart_rate_bpm, "15"),
        "glucose": (policy.demo_delta_glucose_mgdl, "40"),
    }
    deltas = {key: _decimal(value, policy=True) for key, (value, _) in parameters.items()}
    if (
        any(deltas[key] != Decimal(expected) for key, (_, expected) in parameters.items())
        or _decimal(policy.conflict_tolerance, policy=True) != 0
        or _decimal(policy.ocr_confidence_floor, policy=True) != Decimal("0.70")
    ):
        raise OfflineRuleError("E_RULE_POLICY_INVALID", "R3-A fixture threshold mismatch.")
    return deltas


def _basis(*rows: OfflineObservation) -> str:
    levels = {row.trust_level for row in rows}
    if levels == {"doctor_verified"}:
        return "doctor_verified"
    if levels == {"self_reported_validated"}:
        return "self_reported"
    return "mixed"


def _text(template: str, basis: str) -> str:
    result = template.removesuffix(".") + _SUFFIXES[basis] + "."
    if len(result) > 240:
        raise OfflineRuleError("E_VALIDATION", "Template length exceeded.")
    return result


def _flag(
    patient_id: str,
    policy: OfflineRulePolicy,
    rule: str,
    reason: str,
    hint: str,
    text: str,
    rows: tuple[OfflineObservation, ...],
    extra_evidence: tuple[str, ...] = (),
) -> OfflineRuleFlag:
    refs = tuple(
        sorted(
            {*(f"observation:{row.id}" for row in rows), *extra_evidence}
        )
    )
    if not refs:
        raise OfflineRuleError("E_VALIDATION", "Missing typed evidence.")
    trust = _basis(*rows)
    digest = sha256("|".join((patient_id, rule, *refs, trust)).encode("utf-8"))
    return OfflineRuleFlag(
        rule_id=rule,
        reason_code=reason,
        workflow_hint=hint,
        message=_text(text, trust),
        evidence=refs,
        trust_basis=trust,
        policy_version=policy.policy_version,
        dedupe_key=digest.hexdigest(),
    )


def _validate_row(row: OfflineObservation, patient_id: str) -> None:
    if not isinstance(row, OfflineObservation):
        raise OfflineRuleError("E_VALIDATION", "Typed synthetic evidence required.")
    if not isinstance(row.id, str) or not row.id.strip():
        raise OfflineRuleError("E_VALIDATION", "Missing observation ID.")
    if row.patient_id != patient_id:
        raise OfflineRuleError("E_SCOPE_VIOLATION", "Foreign patient evidence.")
    if row.measure_type not in _LABELS:
        raise OfflineRuleError("E_VALIDATION", "Unknown measure type.")
    if row.validation not in {"ok", "ok_with_warning", "rejected"}:
        raise OfflineRuleError("E_VALIDATION", "Unknown validation status.")
    if row.trust_level not in {"doctor_verified", "self_reported_validated"}:
        raise OfflineRuleError("E_VALIDATION", "Unknown trust level.")
    if row.source not in {"seed_fixture", "verified_document", "patient_checkin"}:
        raise OfflineRuleError("E_VALIDATION", "Unknown source.")
    if row.source == "patient_checkin" and row.trust_level != "self_reported_validated":
        raise OfflineRuleError("E_VALIDATION", "Patient check-in cannot be doctor-verified.")
    if row.lineage_status not in {"unavailable", "fixture_asserted"}:
        raise OfflineRuleError("E_VALIDATION", "Unsupported or forged provenance authority.")
    if (
        (row.source_document_id is not None or row.source_fact_id is not None)
        and row.source != "verified_document"
    ):
        raise OfflineRuleError("E_VALIDATION", "Provenance claims on non-document row.")
    if (
        row.source_fact_verification_status is not None
        and row.source_fact_verification_status not in {"verified", "pending", "rejected"}
    ):
        raise OfflineRuleError("E_VALIDATION", "Invalid fact verification label.")


def _independent_fixture_source(row: OfflineObservation) -> bool:
    return (
        row.source == "verified_document"
        and row.trust_level == "doctor_verified"
        and row.lineage_status == "fixture_asserted"
        and row.source_fact_verification_status == "verified"
        and isinstance(row.source_document_id, str)
        and bool(row.source_document_id.strip())
        and isinstance(row.source_fact_id, str)
        and bool(row.source_fact_id.strip())
    )


def evaluate_p4_rb2_offline_fixture(data: OfflineRuleInput) -> OfflineRuleResult:
    """Produce zero-side-effect, non-authoritative candidates, never live DR items."""
    if not isinstance(data, OfflineRuleInput):
        raise OfflineRuleError("E_VALIDATION", "Typed fixture input required.")
    clock = _clock(data.as_of_utc)
    if clock is None:
        raise OfflineRuleError("E_RULE_POLICY_INVALID", "Invalid injected UTC clock.")
    deltas = _policy(data.policy, clock)
    if not isinstance(data.patient_id, str) or not data.patient_id.strip():
        raise OfflineRuleError("E_VALIDATION", "Missing patient scope.")
    if (
        not isinstance(data.selected_current, tuple)
        or len(data.selected_current) > 6
        or not isinstance(data.history, tuple)
        or len(data.history) > 100
    ):
        raise OfflineRuleError("E_VALIDATION", "Invalid bounded fixture selection.")
    if (
        not isinstance(data.active_fact_verification_statuses, tuple)
        or any(
            status not in {"verified", "pending", "rejected"}
            for status in data.active_fact_verification_statuses
        )
    ):
        raise OfflineRuleError("E_VALIDATION", "Invalid fixture fact status.")
    if any(status != "verified" for status in data.active_fact_verification_statuses):
        raise OfflineRuleError("E_UNVERIFIED_FACT", "Fixture contains unresolved facts.")

    rows = (*data.selected_current, *data.history)
    ids: set[str] = set()
    eligible: list[OfflineObservation] = []
    excluded: list[OfflineEvidenceExclusion] = []
    stamps: dict[str, datetime] = {}
    amounts: dict[str, Decimal] = {}
    for row in rows:
        _validate_row(row, data.patient_id)
        if row.id in ids:
            raise OfflineRuleError("E_VALIDATION", "Repeated observation ID.")
        ids.add(row.id)
        reason = None
        if row.validation == "rejected":
            reason = "validation_rejected"
        elif row.unit not in _UNITS[row.measure_type]:
            reason = "unit_mismatch"
        stamp = _clock(row.measured_at)
        if reason is None and stamp is None:
            reason = "missing_timestamp"
        elif reason is None and stamp is not None and stamp > clock:
            reason = "future_timestamp"
        if reason is not None:
            excluded.append(OfflineEvidenceExclusion(row.id, reason))
            continue
        assert stamp is not None
        amount = _decimal(row.value)
        if amount <= 0:
            raise OfflineRuleError("E_VALIDATION", "Non-positive measurement.")
        eligible.append(row)
        stamps[row.id] = stamp
        amounts[row.id] = amount

    selected_ids = {row.id for row in data.selected_current}
    by_type: dict[str, list[OfflineObservation]] = {}
    for row in eligible:
        by_type.setdefault(row.measure_type, []).append(row)
    candidates: list[tuple[str, OfflineRuleFlag]] = []
    for measure in sorted(by_type):
        ordered = sorted(by_type[measure], key=lambda r: (stamps[r.id], r.id))
        selected = [r for r in ordered if r.id in selected_ids]
        if not selected:
            continue
        current = selected[-1]
        current_at = stamps[current.id]
        label = _LABELS[measure]
        past = [
            r for r in ordered if current_at - timedelta(days=90) <= stamps[r.id] < current_at
        ]
        baseline = past[-1] if past else None
        if baseline is None:
            candidates.append(
                (
                    measure,
                    _flag(
                        data.patient_id, data.policy, "DR-001", "missing_baseline",
                        "data_quality",
                        f"No previous recorded {label} to compare against.",
                        (current,),
                    ),
                )
            )
        days = (clock - current_at).days
        if days > 30:
            candidates.append(
                (
                    measure,
                    _flag(
                        data.patient_id, data.policy, "DR-003", "measurement_stale",
                        "data_quality", f"The most recent {label} was recorded {days} days ago.",
                        (current,),
                    ),
                )
            )
        if baseline is not None:
            delta = abs(amounts[current.id] - amounts[baseline.id])
            if delta > deltas[measure]:
                amount_text = format(delta.normalize(), "f")
                candidates.append(
                    (
                        measure,
                        _flag(
                            data.patient_id, data.policy, "DR-005",
                            "change_exceeds_demo_parameter", "change_to_review",
                            f"{label} differs from the previous recorded value by "
                            f"{amount_text} {current.unit}.",
                            (baseline, current),
                        ),
                    )
                )
        low, high = _BANDS[measure]
        if not low <= amounts[current.id] <= high:
            candidates.append(
                (
                    measure,
                    _flag(
                        data.patient_id, data.policy, "DR-009", "implausible_value",
                        "data_quality",
                        "A recorded value is outside the demo plausibility range "
                        "and may be a typo.",
                        (current,),
                    ),
                )
            )

        # Source independence is *asserted by an offline fixture only*. Even
        # qualifying records do not constitute a real doctor's attestation.
        for first, second in combinations(ordered, 2):
            if (
                first.source == "verified_document"
                and first.trust_level == "doctor_verified"
                and not _independent_fixture_source(first)
            ):
                excluded.append(
                    OfflineEvidenceExclusion(first.id, "verified_lineage_unavailable")
                )
            if (
                second.source == "verified_document"
                and second.trust_level == "doctor_verified"
                and not _independent_fixture_source(second)
            ):
                excluded.append(
                    OfflineEvidenceExclusion(second.id, "verified_lineage_unavailable")
                )
            if (
                stamps[first.id] == stamps[second.id]
                and amounts[first.id] != amounts[second.id]
                and _independent_fixture_source(first)
                and _independent_fixture_source(second)
                and first.source_document_id != second.source_document_id
                and first.source_fact_id != second.source_fact_id
            ):
                evidence = (
                    f"document:{first.source_document_id}",
                    f"document:{second.source_document_id}",
                    f"fact:{first.source_fact_id}",
                    f"fact:{second.source_fact_id}",
                )
                candidates.append(
                    (
                        measure,
                        _flag(
                            data.patient_id, data.policy, "DR-006",
                            "verified_source_conflict", "verification_needed",
                            f"Two verified sources disagree for {label} at "
                            f"{stamps[first.id].isoformat().replace('+00:00', 'Z')}.",
                            (first, second), evidence,
                        ),
                    )
                )
            same = (
                stamps[first.id] == stamps[second.id]
                and amounts[first.id] == amounts[second.id]
            )
            a_created, b_created = _clock(first.created_at), _clock(second.created_at)
            if (first.created_at is None or second.created_at is None) and not same:
                excluded.append(
                    OfflineEvidenceExclusion(
                        first.id if first.created_at is None else second.id,
                        "missing_created_at",
                    )
                )
            out_of_order = (
                a_created is not None
                and b_created is not None
                and (
                    (a_created > b_created and stamps[first.id] < stamps[second.id])
                    or (b_created > a_created and stamps[second.id] < stamps[first.id])
                )
            )
            if same or out_of_order:
                candidates.append(
                    (
                        measure,
                        _flag(
                            data.patient_id, data.policy, "DR-008",
                            "duplicate_or_out_of_order", "data_quality",
                            f"A repeated or out-of-order entry was detected for {label}.",
                            (first, second),
                        ),
                    )
                )

    dedup: dict[str, tuple[str, OfflineRuleFlag]] = {}
    for measure, item in candidates:
        dedup[item.dedupe_key] = (measure, item)
    counts: dict[str, int] = {}
    for measure, _ in dedup.values():
        counts[measure] = counts.get(measure, 0) + 1
    if any(count > data.policy.max_items_per_type for count in counts.values()):
        raise OfflineRuleError("E_RULE_POLICY_INVALID", "Rule item cap exceeded.")
    flags = tuple(
        sorted(
            (item for _, item in dedup.values()),
            key=lambda f: (
                _HINT_ORDER[f.workflow_hint], f.rule_id, f.evidence, f.dedupe_key
            ),
        )
    )
    return OfflineRuleResult(
        flags=flags,
        excluded=tuple(sorted(set(excluded), key=lambda x: (x.observation_id, x.reason))),
        policy_version=data.policy.policy_version,
    )


__all__ = ["evaluate_p4_rb2_offline_fixture"]
