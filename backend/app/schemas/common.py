"""Shared response/request primitives for the P2 API surface.

Two contract details are centralised here so they cannot drift per module:

* **UTC timestamps** are rendered as ``YYYY-MM-DDTHH:MM:SSZ`` on the wire. A
  plain ``datetime`` would serialise as ``+00:00``; the accepted contract uses
  the ``Z`` suffix (``API_CONTRACT.md`` §1), so every response timestamp field
  uses ``UtcDatetime``.
* **Bodies are closed.** Every schema forbids unknown properties, mirroring
  ``additionalProperties: false`` in ``openapi.phase0.yaml``. An unknown field is
  a client error, which also means a client cannot smuggle ``trust_level``,
  ``verified_by`` or a patient id into a check-in.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.core.clock import format_utc
from app.core.errors import MAX_DETAIL_LENGTH

#: A UTC datetime rendered in the contract's storage/transport format.
UtcDatetime = Annotated[datetime, PlainSerializer(format_utc, return_type=str)]

#: Query parameter types shared by list endpoints (``API_CONTRACT.md`` §1).
Limit = Annotated[int, Field(default=20, ge=1, le=100, description="Page size (1-100).")]
Cursor = Annotated[
    str | None,
    Field(default=None, max_length=64, description="Opaque cursor from the prior page."),
]


class ApiModel(BaseModel):
    """Base for every P2 request/response body."""

    model_config = ConfigDict(extra="forbid")


class ProblemDetail(ApiModel):
    """One field-level validation finding (``Problem.details[]``)."""

    field: str
    reason: str


class Problem(ApiModel):
    """RFC-9457-style problem document (``API_CONTRACT.md`` §1.1).

    ``detail`` is bounded and neutral: no document text, no patient free text,
    no credential and no stack trace.
    """

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    code: str = Field(pattern=r"^E_[A-Z0-9_]+$")
    detail: str = Field(max_length=MAX_DETAIL_LENGTH)
    instance: str | None = None
    request_id: str | None = None
    details: list[ProblemDetail] | None = None


class EmptyPayload(ApiModel):
    """Placeholder type for ``204 No Content`` documentation."""

    detail: Literal["no content"] = "no content"


def dump(body: ApiModel) -> dict[str, Any]:
    """Serialise a model for explicit dictionary construction in tests."""
    return body.model_dump()


__all__ = [
    "ApiModel",
    "Cursor",
    "EmptyPayload",
    "Limit",
    "Problem",
    "ProblemDetail",
    "UtcDatetime",
    "dump",
]
