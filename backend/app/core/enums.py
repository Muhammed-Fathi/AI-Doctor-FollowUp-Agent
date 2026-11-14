"""Domain enumerations shared by the ORM layer, schemas and services.

Keeping one definition per vocabulary matters for the audit trail: a SQLite
``CHECK`` constraint, a Python ``StrEnum`` and an OpenAPI enum that disagree is
exactly how a value silently becomes "unknown" downstream. Each enum below
mirrors a constraint named in ``DATA_DICTIONARY.md`` or ``openapi.phase0.yaml``,
and the module docstring records which one.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """``user.role`` — ``DATA_DICTIONARY.md`` §2.1; ``User.role`` in the API."""

    DOCTOR = "doctor"
    PATIENT = "patient"
    DEMO_ADMIN = "demo_admin"


class ActorType(StrEnum):
    """``audit_event.actor_type`` — ``DATA_DICTIONARY.md`` §2.17."""

    USER = "user"
    SYSTEM = "system"
    DEMO_ADMIN = "demo_admin"


class SexAtBirth(StrEnum):
    """``patient.sex_at_birth`` — demo attribute only, never a scoring input."""

    FEMALE = "female"
    MALE = "male"
    UNKNOWN = "unknown"


class EncounterType(StrEnum):
    """``encounter.encounter_type`` — the MVP has exactly one type."""

    ROUTINE_FOLLOW_UP = "routine_follow_up"


class MeasureType(StrEnum):
    """``observation.measure_type`` — ``DATA_DICTIONARY.md`` §2.8/§3.1."""

    SYSTOLIC_BP = "systolic_bp"
    DIASTOLIC_BP = "diastolic_bp"
    HEART_RATE = "heart_rate"
    GLUCOSE = "glucose"


class Unit(StrEnum):
    """``observation.unit`` — the comparable-measurement allowlist (§3.1).

    ``mg/dL`` is the only member whose name and value differ; the value is what
    is stored and transported. Document-only units (``g/dL``, ``%``) are
    deliberately absent: they never become an observation unit (``P0-R06``).
    """

    MMHG = "mmHg"
    BPM = "bpm"
    MG_DL = "mg/dL"


class ObservationSource(StrEnum):
    """``observation.source`` — where the measurement came from."""

    PATIENT_CHECKIN = "patient_checkin"
    VERIFIED_DOCUMENT = "verified_document"
    SEED_FIXTURE = "seed_fixture"


class ValidationState(StrEnum):
    """``observation.validation`` — a data check, **not** a human verification.

    ``ok_with_warning`` means the recorded value sits outside the arbitrary demo
    plausibility band in ``DATA_DICTIONARY.md`` §3.1. It is a typo/unit-confusion
    heuristic and must never be presented as a clinical judgement.
    """

    OK = "ok"
    OK_WITH_WARNING = "ok_with_warning"
    REJECTED = "rejected"


class TrustLevel(StrEnum):
    """``observation.trust_level`` — the provenance class (``REQ-DATA-04``).

    A self-reported check-in is ``SELF_REPORTED_VALIDATED`` and must never be
    described as doctor-verified anywhere in the API, logs or UI.
    """

    SELF_REPORTED_VALIDATED = "self_reported_validated"
    DOCTOR_VERIFIED = "doctor_verified"


class AuditOutcome(StrEnum):
    """``audit_event.outcome`` — ``DATA_DICTIONARY.md`` §2.17."""

    OK = "ok"
    DENIED = "denied"
    ERROR = "error"


#: Measurement → allowed observation unit(s) (``DATA_DICTIONARY.md`` §3.1).
#: Exactly one unit per type in the MVP: no unit conversion exists.
MEASURE_UNITS: dict[MeasureType, frozenset[Unit]] = {
    MeasureType.SYSTOLIC_BP: frozenset({Unit.MMHG}),
    MeasureType.DIASTOLIC_BP: frozenset({Unit.MMHG}),
    MeasureType.HEART_RATE: frozenset({Unit.BPM}),
    MeasureType.GLUCOSE: frozenset({Unit.MG_DL}),
}

#: Arbitrary demo plausibility bands (``DATA_DICTIONARY.md`` §3.1). They catch
#: unit confusion and typos and are explicitly **not** clinical ranges.
MEASURE_PLAUSIBLE_BANDS: dict[MeasureType, tuple[float, float]] = {
    MeasureType.SYSTOLIC_BP: (50.0, 300.0),
    MeasureType.DIASTOLIC_BP: (20.0, 200.0),
    MeasureType.HEART_RATE: (20.0, 250.0),
    MeasureType.GLUCOSE: (10.0, 900.0),
}


__all__ = [
    "MEASURE_PLAUSIBLE_BANDS",
    "MEASURE_UNITS",
    "ActorType",
    "AuditOutcome",
    "EncounterType",
    "MeasureType",
    "ObservationSource",
    "Role",
    "SexAtBirth",
    "TrustLevel",
    "Unit",
    "ValidationState",
]
