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


class DocumentMimeType(StrEnum):
    """``document.mime_type`` — the allowlist, derived from **magic bytes** only.

    The client-supplied filename/extension is never an input to this decision
    (``REQ-ING-01``, ``EXTRACTION_PROVENANCE.md`` §1 rule 1).
    """

    PDF = "application/pdf"
    PNG = "image/png"
    JPEG = "image/jpeg"


class DocumentStatus(StrEnum):
    """``document.extraction_status`` — ``DATA_DICTIONARY.md`` §2.4.

    ``verified`` at document level requires every blocking fact decided and at
    least one fact verified; nothing in this phase may jump straight to it.
    """

    PENDING_EXTRACTION = "pending_extraction"
    EXTRACTED = "extracted"
    NEEDS_VERIFICATION = "needs_verification"
    VERIFIED = "verified"
    FAILED = "failed"


class ExtractionPath(StrEnum):
    """``extraction_attempt.path`` — provenance of the extraction route.

    A fact records which route produced it (``REQ-ING-02``). ``MANUAL`` is
    reserved for a doctor-supplied correction, never for an automatic guess.
    """

    PYPDF = "pypdf"
    TESSERACT = "tesseract"
    MANUAL = "manual"


class Preprocessing(StrEnum):
    """``extraction_attempt.preprocessing`` — deterministic only (``P0-R08``).

    The set is closed on purpose: the retry budget cannot grow and the triage
    cannot invent a new transform at runtime.
    """

    NONE = "none"
    GRAYSCALE_UPSCALE = "grayscale_upscale"


class TriagePath(StrEnum):
    """Bounded extraction path selection (``ADR-0006`` §3.1).

    P3 returns this as a **pure service value** and persists ``extraction_attempt``
    rows. There is deliberately no graph node in this phase (``AGENTS.md`` §1).
    """

    PROCEED = "proceed"
    OCR_PREPROCESS_RETRY = "ocr_preprocess_retry"
    FLAG_FOR_HUMAN = "flag_for_human"


class FactField(StrEnum):
    """``extracted_fact.field_name`` — the closed five-field set.

    ``reference_text`` is optional: a report without a printed reference range
    yields four facts, not an error (``REQ-ING-03``).
    """

    REPORT_DATE = "report_date"
    TEST_NAME = "test_name"
    VALUE = "value"
    UNIT = "unit"
    REFERENCE_TEXT = "reference_text"


class FactVerificationStatus(StrEnum):
    """``extracted_fact.verification_status`` — always ``pending`` on creation."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class QualityFlag(StrEnum):
    """Closed quality-flag enum (``EXTRACTION_PROVENANCE.md`` §4).

    Every blocking flag maps to exactly one ``VI-*`` verification issue; none of
    them is a clinical judgement.
    """

    CLEAN = "clean"
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_DATE = "ambiguous_date"
    AMBIGUOUS_UNIT = "ambiguous_unit"
    UNPARSEABLE_VALUE = "unparseable_value"
    SOURCE_CONFLICT = "source_conflict"
    PAGE_MISSING = "page_missing"


class VerificationDecision(StrEnum):
    """``fact_verification.decision`` — a human, append-only decision."""

    VERIFIED = "verified"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class IssueState(StrEnum):
    """``verification_issue.state`` — the lifecycle of one persisted blocker.

    ``DATA_DICTIONARY.md`` §2.8a already declares this closed set. Recording the
    lifecycle is what makes an issue *identifiable* across reads: the row keeps its
    id and ``created_at`` while its state moves ``open`` -> ``resolved`` (or
    ``superseded`` when a later blocker replaces it).
    """

    OPEN = "open"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class IssueType(StrEnum):
    """``verification_issue.issue_type`` — ``DEMO_REVIEW_RULES.md`` §4.

    These are **pre-verification blockers**. They are a different output type
    from ``DR-*`` review items and can never be stored as one.
    """

    VI_001 = "VI-001"
    VI_002 = "VI-002"
    VI_003 = "VI-003"
    VI_004 = "VI-004"
    VI_005 = "VI-005"
    VI_006 = "VI-006"


class DocumentUnit(StrEnum):
    """Document-only units — report **text**, not an ``Observation`` unit.

    ``g/dL`` and ``%`` exist here and never in :class:`Unit`, so a hemoglobin or
    HbA1c value can be verified without ever becoming a comparable measurement
    (``P0-R06``, ``DATA_DICTIONARY.md`` §3.2).
    """

    MMHG = "mmHg"
    BPM = "bpm"
    MG_DL = "mg/dL"
    G_DL = "g/dL"
    PERCENT = "%"


#: Version of the closed verified-fact -> observation mapping
#: (``DATA_DICTIONARY.md`` §3.3). Typed on purpose: a bare semver is not a
#: mapping version and must never validate (``P0-R12``).
MAPPING_VERSION: str = "map-1.0.0"

#: Shape guard mirrored by the SQL ``CHECK`` on ``workflow_run.mapping_version``.
MAPPING_VERSION_PATTERN: str = r"^map-\d+\.\d+\.\d+$"

#: ``map-1.0.0``: accepted normalized alias -> (measure type, required unit).
#:
#: Matching is **literal**: lowercase, collapse internal whitespace, strip a
#: trailing colon, then exact set membership. No substring, prefix, stemming or
#: fuzzy match. A new alias is a mapping-version change, not a runtime guess.
MAPPING_TABLE: dict[str, tuple[MeasureType, DocumentUnit]] = {
    "systolic blood pressure": (MeasureType.SYSTOLIC_BP, DocumentUnit.MMHG),
    "systolic bp": (MeasureType.SYSTOLIC_BP, DocumentUnit.MMHG),
    "sbp": (MeasureType.SYSTOLIC_BP, DocumentUnit.MMHG),
    "diastolic blood pressure": (MeasureType.DIASTOLIC_BP, DocumentUnit.MMHG),
    "diastolic bp": (MeasureType.DIASTOLIC_BP, DocumentUnit.MMHG),
    "dbp": (MeasureType.DIASTOLIC_BP, DocumentUnit.MMHG),
    "heart rate": (MeasureType.HEART_RATE, DocumentUnit.BPM),
    "pulse": (MeasureType.HEART_RATE, DocumentUnit.BPM),
    "pulse rate": (MeasureType.HEART_RATE, DocumentUnit.BPM),
    "hr": (MeasureType.HEART_RATE, DocumentUnit.BPM),
    "glucose": (MeasureType.GLUCOSE, DocumentUnit.MG_DL),
    "blood glucose": (MeasureType.GLUCOSE, DocumentUnit.MG_DL),
    "fasting glucose": (MeasureType.GLUCOSE, DocumentUnit.MG_DL),
    "fasting blood sugar": (MeasureType.GLUCOSE, DocumentUnit.MG_DL),
    "fbg": (MeasureType.GLUCOSE, DocumentUnit.MG_DL),
}


__all__ = [
    "MAPPING_TABLE",
    "MAPPING_VERSION",
    "MAPPING_VERSION_PATTERN",
    "MEASURE_PLAUSIBLE_BANDS",
    "MEASURE_UNITS",
    "ActorType",
    "AuditOutcome",
    "DocumentMimeType",
    "DocumentStatus",
    "DocumentUnit",
    "EncounterType",
    "ExtractionPath",
    "FactField",
    "FactVerificationStatus",
    "IssueState",
    "IssueType",
    "MeasureType",
    "ObservationSource",
    "Preprocessing",
    "QualityFlag",
    "Role",
    "SexAtBirth",
    "TriagePath",
    "TrustLevel",
    "Unit",
    "ValidationState",
    "VerificationDecision",
]
