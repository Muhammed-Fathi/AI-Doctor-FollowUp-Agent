"""Patient, timeline and demo-administration schemas.

Timeline note
-------------
``GET /api/v1/doctor/patients/{patient_id}/timeline`` is a P2 endpoint whose
response also carries documents (P3), review items (P4) and tasks (P6). Those
collections are returned as **empty arrays** in P2 rather than fabricated rows,
exactly as ``openapi.phase0.yaml`` allows and Issue #6 §3.4 requires.

Demo-status note
----------------
``DemoStatus`` is intentionally **not** defined here: the accepted schema
requires a ``provider`` block whose ``provider`` enum only admits ``ollama`` and
``deterministic_fallback``, and no drafting provider exists before P5. Returning
either value in P2 would assert something about a component that does not exist,
so ``GET /api/v1/demo/status`` is deferred and the conflict is documented for
owner review (``OQ-P2-01``). ``DemoResetResponse`` has no such dependency and is
implemented.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.core.enums import MeasureType
from app.schemas.common import ApiModel, UtcDatetime
from app.schemas.observation import ObservationRead


class PatientRead(ApiModel):
    """A synthetic patient header (``Patient`` in ``openapi.phase0.yaml``)."""

    id: str
    display_name: str
    external_ref: str = Field(pattern=r"^DEMO-")
    data_source: Literal["synthetic_fixture"] = "synthetic_fixture"
    date_of_birth: str | None = None
    observation_count: int = Field(default=0, ge=0)
    document_count: int = Field(default=0, ge=0)
    open_review_item_count: int = Field(default=0, ge=0)


class PatientList(ApiModel):
    """A page of patients assigned to the authenticated doctor."""

    items: list[PatientRead]
    next_cursor: str | None = None


class Timeline(ApiModel):
    """Longitudinal doctor view.

    ``documents``, ``review_items`` and ``tasks`` are always ``[]`` in P2: the
    corresponding phases have not been implemented, and inventing entries would
    be exactly the fabrication the evaluation matrix forbids.
    """

    patient_id: str
    observations: list[ObservationRead]
    documents: list[dict[str, Any]] = Field(default_factory=list)
    review_items: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class ObservationQuery(ApiModel):
    """Optional filters for the observation series endpoint."""

    measure_type: MeasureType | None = None
    from_: UtcDatetime | None = None
    to: UtcDatetime | None = None


class DemoResetResponse(ApiModel):
    """Result of ``POST /api/v1/demo/reset``.

    ``cases_loaded`` lists the three synthetic demo cases only; a reset never
    removes audit rows, runtime uploads of a future phase or any file outside the
    application's own synthetic rows.
    """

    reset_at: UtcDatetime
    cases_loaded: list[Literal["A_stable", "B_changed", "C_ambiguous_ocr"]]
    disclaimer: str


__all__ = [
    "DemoResetResponse",
    "ObservationQuery",
    "PatientList",
    "PatientRead",
    "Timeline",
]
