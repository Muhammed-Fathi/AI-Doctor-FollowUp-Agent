"""Authentication request/response schemas (``API_CONTRACT.md`` §2.2).

``LoginRequest`` mirrors the accepted contract exactly: ``username`` 3-64
characters matching ``^[a-z0-9_.-]{3,64}$`` (``DATA_DICTIONARY.md`` §2.1) and a
``password`` of 8-200 characters. ``TokenResponse`` carries the opaque bearer
token once, its expiry and the caller's identity — never a password, a hash or
a refresh token, because no refresh mechanism exists in the MVP.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.core.enums import Role
from app.schemas.common import ApiModel, UtcDatetime


class LoginRequest(ApiModel):
    """Local demo credentials."""

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9_.-]{3,64}$")
    password: str = Field(min_length=8, max_length=200)


class UserRead(ApiModel):
    """The authenticated identity (``User`` in ``openapi.phase0.yaml``).

    ``patient_id`` is present only for ``role=patient``; it is the self scope
    the server enforces, never a value taken from the request.
    """

    id: str
    username: str
    display_name: str
    role: Role
    patient_id: str | None = None
    timezone: str


class TokenResponse(ApiModel):
    """A newly issued session."""

    access_token: str
    #: Required (no default) so the generated OpenAPI ``required`` set matches the
    #: accepted contract exactly.
    token_type: Literal["Bearer"]
    expires_at: UtcDatetime
    user: UserRead


__all__ = ["LoginRequest", "TokenResponse", "UserRead"]
