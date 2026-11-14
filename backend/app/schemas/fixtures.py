"""Typed models for the tracked synthetic fixtures in ``data/synthetic/``.

The fixtures are the only patient-shaped data in the repository, so they are
validated like code, not parsed loosely:

* every file must carry the synthetic-data notice and the educational
  disclaimer — a fixture without them is rejected, which makes an accidental
  import of non-synthetic data fail closed;
* ``data_source`` is fixed to ``synthetic_fixture`` and ``external_ref`` must use
  the ``DEMO-`` prefix (``DATA_DICTIONARY.md`` §5);
* identifiers are explicit UUIDs, so seeding is byte-stable (``REQ-OPS-01``)
  instead of relying on a random generator at run time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, ValidationInfo, field_validator

from app.core.enums import (
    MeasureType,
    ObservationSource,
    Role,
    SexAtBirth,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.core.version import DEMO_NOTICE
from app.schemas.common import ApiModel

#: Header every synthetic fixture file must carry.
REQUIRED_FIXTURE_NOTICE: str = "SYNTHETIC DEMO DATA — NOT A REAL MEDICAL RECORD"

_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class FixtureFile(ApiModel):
    """Fields common to every fixture file."""

    notice: str
    disclaimer: str
    fixture_version: str = Field(min_length=1, max_length=32)

    @field_validator("notice")
    @classmethod
    def _require_notice(cls, value: str) -> str:
        if value != REQUIRED_FIXTURE_NOTICE:
            raise ValueError("fixture must carry the synthetic-data notice")
        return value

    @field_validator("disclaimer")
    @classmethod
    def _require_disclaimer(cls, value: str) -> str:
        if value != DEMO_NOTICE:
            raise ValueError("fixture must carry the educational disclaimer")
        return value


class UserFixture(ApiModel):
    """A seeded demo account. Never contains a password or a hash."""

    id: str = Field(pattern=_UUID_PATTERN)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]{3,64}$")
    display_name: str = Field(min_length=1, max_length=80)
    role: Role
    patient_id: str | None = Field(default=None, pattern=_UUID_PATTERN)
    timezone: str = Field(default="Africa/Cairo", max_length=64)

    @field_validator("patient_id")
    @classmethod
    def _patient_scope_requires_patient_role(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        role = info.data.get("role")
        if role is Role.PATIENT and value is None:
            raise ValueError("a patient account requires a patient_id")
        if role is not Role.PATIENT and value is not None:
            raise ValueError("only a patient account may carry a patient_id")
        return value


class UserFixtureFile(FixtureFile):
    """``data/synthetic/users.json``."""

    users: list[UserFixture]


class PatientFixture(ApiModel):
    """A seeded synthetic patient."""

    id: str = Field(pattern=_UUID_PATTERN)
    display_name: str = Field(min_length=1, max_length=80)
    date_of_birth: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    sex_at_birth: SexAtBirth | None = None
    assigned_doctor_username: str = Field(pattern=r"^[a-z0-9_.-]{3,64}$")
    external_ref: str = Field(pattern=r"^DEMO-[A-Z0-9-]{1,35}$")
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"


class PatientFixtureFile(FixtureFile):
    """``data/synthetic/patients.json``."""

    patients: list[PatientFixture]


class EncounterFixture(ApiModel):
    """A seeded synthetic visit."""

    id: str = Field(pattern=_UUID_PATTERN)
    ref: str = Field(pattern=r"^DEMO-[A-Z0-9-]{1,35}$")
    patient_external_ref: str = Field(pattern=r"^DEMO-[A-Z0-9-]{1,35}$")
    encounter_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    encounter_type: Literal["routine_follow_up"] = "routine_follow_up"
    note: str | None = Field(default=None, max_length=1000)


class EncounterFixtureFile(FixtureFile):
    """``data/synthetic/encounters.json``."""

    encounters: list[EncounterFixture]


class ObservationFixture(ApiModel):
    """A seeded measurement.

    ``trust_level`` is fixed to ``self_reported_validated``: no document exists
    before P3, so no fixture may claim doctor verification.
    """

    id: str = Field(pattern=_UUID_PATTERN)
    patient_external_ref: str = Field(pattern=r"^DEMO-[A-Z0-9-]{1,35}$")
    encounter_ref: str | None = Field(default=None, pattern=r"^DEMO-[A-Z0-9-]{1,35}$")
    measure_type: MeasureType
    value: float = Field(gt=0, allow_inf_nan=False)
    unit: Unit
    measured_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    source: ObservationSource
    trust_level: TrustLevel = TrustLevel.SELF_REPORTED_VALIDATED
    validation: ValidationState = ValidationState.OK
    note: str | None = Field(default=None, max_length=500)

    @field_validator("trust_level")
    @classmethod
    def _no_seeded_doctor_verified(cls, value: TrustLevel) -> TrustLevel:
        if value is not TrustLevel.SELF_REPORTED_VALIDATED:
            raise ValueError("seeded observations must be self_reported_validated")
        return value


class ObservationFixtureFile(FixtureFile):
    """``data/synthetic/observations.json``."""

    observations: list[ObservationFixture]


__all__ = [
    "REQUIRED_FIXTURE_NOTICE",
    "EncounterFixture",
    "EncounterFixtureFile",
    "FixtureFile",
    "ObservationFixture",
    "ObservationFixtureFile",
    "PatientFixture",
    "PatientFixtureFile",
    "UserFixture",
    "UserFixtureFile",
]
