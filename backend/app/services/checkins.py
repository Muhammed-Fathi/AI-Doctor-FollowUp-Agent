"""Check-in intake: validation, idempotency and self-scoped listing.

What this service refuses to do
-------------------------------
* It never accepts a patient id, a ``trust_level``, a ``validation`` value or a
  verifier from the client. The patient is the authenticated session's own
  ``user.patient_id``; the labels are derived from provenance.
* It never converts units. ``mmol/L`` glucose is rejected with
  ``400 E_UNIT_NOT_ALLOWED`` (``NEG-13``) rather than converted, because the MVP
  has no conversion table and a silent conversion is exactly the failure mode
  ``THREAT_MODEL.md`` T-09 describes.
* It never treats a value outside the demo plausibility band as valid *or*
  invalid on clinical grounds: the row is stored with
  ``validation='ok_with_warning'``, which is a data-quality hint, not a
  judgement about the patient.

Idempotency semantics (``API_CONTRACT.md`` §1 and §2.4)
-------------------------------------------------------
======================  =========================================  ==============
Condition               Behaviour                                  Response
======================  =========================================  ==============
Same key, same payload  Return the originally stored observation   ``201`` replay
Same key, other payload ``409 E_IDEMPOTENCY_CONFLICT``              no write
No key, semantic dup    ``409 E_DUPLICATE_CHECKIN``                 no write
New key, semantic dup   ``409 E_DUPLICATE_CHECKIN``                 no write
======================  =========================================  ==============

A replay is answered with ``201`` and the original body so a retry is
indistinguishable from the first success, as ``API_CONTRACT.md`` §1 requires
("repeats return the original result").
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.clock import MAX_FUTURE_SKEW_MINUTES, format_utc, parse_utc, to_utc
from app.core.enums import (
    MEASURE_PLAUSIBLE_BANDS,
    MEASURE_UNITS,
    AuditOutcome,
    MeasureType,
    ObservationSource,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal, self_patient_id
from app.db.models import CheckinIdempotency, Observation, new_uuid
from app.schemas.observation import (
    CheckInCreate,
    ObservationList,
    ObservationRead,
    ObservationVerification,
)
from app.services.audit import EVENT_CHECKIN_CREATED, append_audit_event
from app.services.pagination import decode_cursor, encode_cursor

#: Longest accepted ``Idempotency-Key`` (contract: a client-generated UUID).
IDEMPOTENCY_KEY_MAX_LENGTH: int = 100


def validate_idempotency_key(value: str | None) -> str | None:
    """Validate a supplied ``Idempotency-Key`` and return its canonical form.

    The contract defines it as a client-generated UUID. Anything else is a client
    error rather than a silent no-op, so a typo cannot quietly disable replay
    protection.
    """
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ApiError(400, ErrorCode.VALIDATION, "The Idempotency-Key header is not valid.")
    try:
        return str(uuid.UUID(candidate))
    except (ValueError, AttributeError):
        raise ApiError(
            400, ErrorCode.VALIDATION, "The Idempotency-Key header is not valid."
        ) from None


def resolve_unit(measure_type: MeasureType, raw_unit: str) -> Unit:
    """Return the allowlisted unit for ``measure_type`` or raise.

    Raises:
        ApiError: ``400 E_UNIT_NOT_ALLOWED`` when the unit is unknown or not the
            one allowed for this measurement — including a unit that is valid
            for a *different* measurement (``bpm`` for ``systolic_bp``).
    """
    candidate = raw_unit.strip()
    allowed = MEASURE_UNITS[measure_type]
    for unit in allowed:
        if candidate == unit.value:
            return unit
    allowed_text = ", ".join(sorted(unit.value for unit in allowed))
    raise ApiError(
        400,
        ErrorCode.UNIT_NOT_ALLOWED,
        f"Unit {candidate!r} is not allowed for {measure_type.value}. Allowed: {allowed_text}.",
    )


def classify_value(measure_type: MeasureType, value: float) -> ValidationState:
    """Return the deterministic data-quality label for a stored value.

    The band is the arbitrary demo plausibility range from
    ``DATA_DICTIONARY.md`` §3.1. It exists to catch typos and unit confusion
    (e.g. ``1200 mmHg``); it is **not** a clinical range and never implies a
    judgement about the patient.
    """
    low, high = MEASURE_PLAUSIBLE_BANDS[measure_type]
    if value < low or value > high:
        return ValidationState.OK_WITH_WARNING
    return ValidationState.OK


def request_fingerprint(payload: CheckInCreate, *, measured_at: datetime) -> str:
    """Return the stable fingerprint of a check-in request body.

    Only values that the client actually controls are included, and the timestamp
    is normalised to UTC first, so two spellings of the same instant produce the
    same fingerprint.
    """
    canonical = {
        "measured_at": format_utc(measured_at),
        "measure_type": payload.measure_type.value,
        "value": float(payload.value),
        "unit": payload.unit.strip(),
        "note": payload.note,
        "client_request_id": payload.client_request_id,
    }
    serialised = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _normalise_measured_at(payload: CheckInCreate, now: datetime) -> datetime:
    """Convert ``measured_at`` to UTC and apply the clock-skew guard."""
    try:
        measured_at = to_utc(payload.measured_at)
    except ValueError:
        raise ApiError(400, ErrorCode.VALIDATION, "measured_at must include a timezone.") from None

    if measured_at > now + timedelta(minutes=MAX_FUTURE_SKEW_MINUTES):
        raise ApiError(
            400,
            ErrorCode.VALIDATION,
            f"measured_at is more than {MAX_FUTURE_SKEW_MINUTES} minutes in the future.",
        )
    return measured_at


def observation_to_read(observation: Observation) -> ObservationRead:
    """Project a stored row into the response model."""
    verification = None
    if observation.trust_level == TrustLevel.DOCTOR_VERIFIED.value:
        verification = ObservationVerification(
            verified_by=observation.verified_by_user_id or "",
            verified_at=parse_utc(observation.verified_at or observation.created_at),
        )

    return ObservationRead(
        id=observation.id,
        patient_id=observation.patient_id,
        measure_type=MeasureType(observation.measure_type),
        value=observation.value,
        unit=Unit(observation.unit),
        measured_at=parse_utc(observation.measured_at),
        source=ObservationSource(observation.source),
        validation=ValidationState(observation.validation),
        trust_level=TrustLevel(observation.trust_level),
        verification=verification,
        note=observation.note,
    )


def _existing_duplicate(
    db: Session,
    *,
    patient_id: str,
    measure_type: MeasureType,
    measured_at: datetime,
    value: float,
    unit: Unit,
) -> Observation | None:
    """Return an existing observation with the same semantic identity, if any."""
    statement = select(Observation).where(
        Observation.patient_id == patient_id,
        Observation.measure_type == measure_type.value,
        Observation.measured_at == format_utc(measured_at),
        Observation.value == float(value),
        Observation.unit == unit.value,
    )
    return db.execute(statement).scalars().first()


def create_check_in(
    db: Session,
    *,
    principal: Principal,
    payload: CheckInCreate,
    idempotency_key: str | None,
    now: datetime,
    request_id: str,
) -> tuple[ObservationRead, bool]:
    """Store a self-scoped check-in.

    Returns:
        ``(observation, created)`` where ``created`` is ``False`` for an exact
        replay of an already stored request.

    Raises:
        ApiError: ``403`` when the caller is not a patient with a self scope,
            ``400`` for a validation or unit failure, ``409`` for a duplicate
            check-in or a conflicting idempotency key.
    """
    patient_id = self_patient_id(principal)
    key = validate_idempotency_key(idempotency_key)
    measured_at = _normalise_measured_at(payload, now)
    unit = resolve_unit(payload.measure_type, payload.unit)
    fingerprint = request_fingerprint(payload, measured_at=measured_at)

    if key is not None:
        recorded = db.execute(
            select(CheckinIdempotency).where(
                CheckinIdempotency.patient_id == patient_id,
                CheckinIdempotency.idempotency_key == key,
            )
        ).scalar_one_or_none()
        if recorded is not None:
            if recorded.request_fingerprint != fingerprint:
                raise ApiError(
                    409,
                    ErrorCode.IDEMPOTENCY_CONFLICT,
                    "This Idempotency-Key was already used with a different request body.",
                )
            stored = db.get(Observation, recorded.observation_id)
            if stored is not None:
                return observation_to_read(stored), False

    duplicate = _existing_duplicate(
        db,
        patient_id=patient_id,
        measure_type=payload.measure_type,
        measured_at=measured_at,
        value=payload.value,
        unit=unit,
    )
    if duplicate is not None:
        raise ApiError(
            409,
            ErrorCode.DUPLICATE_CHECKIN,
            "An identical check-in (type, value, unit, measured_at) already exists.",
        )

    observation = Observation(
        id=new_uuid(),
        patient_id=patient_id,
        encounter_id=None,
        measure_type=payload.measure_type.value,
        value=float(payload.value),
        unit=unit.value,
        measured_at=format_utc(measured_at),
        source=ObservationSource.PATIENT_CHECKIN.value,
        validation=classify_value(payload.measure_type, float(payload.value)).value,
        trust_level=TrustLevel.SELF_REPORTED_VALIDATED.value,
        verified_by_user_id=None,
        verified_at=None,
        note=payload.note,
        created_at=format_utc(now),
        created_by_user_id=principal.user_id,
    )
    db.add(observation)
    db.flush()

    if key is not None:
        db.add(
            CheckinIdempotency(
                id=new_uuid(),
                patient_id=patient_id,
                idempotency_key=key,
                observation_id=observation.id,
                request_fingerprint=fingerprint,
                created_at=format_utc(now),
            )
        )
        db.flush()

    append_audit_event(
        db,
        event_type=EVENT_CHECKIN_CREATED,
        actor_type=principal.actor_type,
        actor_id=principal.user_id,
        outcome=AuditOutcome.OK,
        request_id=request_id,
        now=now,
        patient_id=patient_id,
        subject_type="observation",
        subject_id=observation.id,
        detail_fragments=(
            f"measure_type={observation.measure_type}",
            f"validation={observation.validation}",
        ),
    )
    return observation_to_read(observation), True


def list_own_check_ins(
    db: Session,
    *,
    principal: Principal,
    limit: int,
    cursor: str | None,
) -> ObservationList:
    """List the caller's own check-ins, newest first."""
    patient_id = self_patient_id(principal)

    statement = select(Observation).where(
        Observation.patient_id == patient_id,
        Observation.source == ObservationSource.PATIENT_CHECKIN.value,
    )
    if cursor:
        measured_at, row_id = decode_cursor(cursor)
        statement = statement.where(
            or_(
                Observation.measured_at < measured_at,
                and_(Observation.measured_at == measured_at, Observation.id < row_id),
            )
        )
    statement = statement.order_by(Observation.measured_at.desc(), Observation.id.desc()).limit(
        limit + 1
    )

    rows = list(db.execute(statement).scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].measured_at, page[-1].id) if has_more and page else None
    return ObservationList(
        items=[observation_to_read(row) for row in page], next_cursor=next_cursor
    )


__all__ = [
    "IDEMPOTENCY_KEY_MAX_LENGTH",
    "classify_value",
    "create_check_in",
    "list_own_check_ins",
    "observation_to_read",
    "request_fingerprint",
    "resolve_unit",
    "validate_idempotency_key",
]
