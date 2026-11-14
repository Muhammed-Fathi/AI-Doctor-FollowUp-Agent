"""Observation and check-in schemas (``API_CONTRACT.md`` §2.4, ``§2.3``).

Deliberate detail — the request ``unit`` is a bounded **string**, not the
``Unit`` enum:

``NEG-13`` requires ``400 E_UNIT_NOT_ALLOWED`` for a glucose check-in in
``mmol/L``. ``mmol/L`` is outside the contract's ``Unit`` enum, so validating the
field as an enum would produce a generic schema error instead of the documented
code. The request therefore accepts a bounded string and
``services.checkins`` applies the measurement→unit allowlist, which can answer
with the precise error. The **response** keeps the closed ``Unit`` enum, so a
client only ever sees a stored, allowlisted unit.

``extra="forbid"`` on the request also means a client cannot supply
``trust_level``, ``validation``, ``verified_by`` or ``verified_at``: those are
derived server-side from provenance (``REQ-DATA-04``).
"""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from app.core.enums import MeasureType, ObservationSource, TrustLevel, Unit, ValidationState
from app.schemas.common import ApiModel, UtcDatetime


class CheckInCreate(ApiModel):
    """A patient's self-scoped, timestamped measurement.

    ``measured_at`` must be timezone-aware and is normalised to UTC; the
    clock-skew guard (≤ 5 minutes ahead) is applied in the service so the
    comparison uses the injected clock rather than the parser's opinion.
    """

    measured_at: AwareDatetime
    measure_type: MeasureType
    value: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=16)
    note: str | None = Field(default=None, max_length=500)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=100)


class ObservationVerification(ApiModel):
    """Present only when ``trust_level='doctor_verified'``."""

    verified_by: str
    verified_at: UtcDatetime


class ObservationRead(ApiModel):
    """A stored measurement with its provenance labels.

    ``validation`` is a deterministic data check; ``trust_level`` is the
    provenance class. A ``self_reported_validated`` value is never presented as
    doctor-verified, and the API offers no field that could relabel it.
    """

    id: str
    patient_id: str
    measure_type: MeasureType
    value: float
    unit: Unit
    measured_at: UtcDatetime
    source: ObservationSource
    validation: ValidationState
    trust_level: TrustLevel
    verification: ObservationVerification | None = None
    note: str | None = None


class ObservationList(ApiModel):
    """A page of observations."""

    items: list[ObservationRead]
    next_cursor: str | None = None


__all__ = [
    "CheckInCreate",
    "ObservationList",
    "ObservationRead",
    "ObservationVerification",
]
