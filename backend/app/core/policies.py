"""Role and patient-scope authorization rules.

``ARCHITECTURE.md`` §6 is the normative matrix. This module implements it as
plain functions so every router calls the same code path and the rules are unit
testable without HTTP:

* **Doctor** may read only patients whose ``assigned_doctor_id`` equals the
  authenticated user id.
* **Patient** may read/write only the row referenced by their own
  ``user.patient_id``. A patient id is never taken from a request body as proof
  of scope (``THREAT_MODEL.md`` T-01).
* **Demo admin** may only reach the explicitly authorized local demo
  operations, and reset additionally requires ``DEMO_MODE=true``.
* Denials use ``403 E_SCOPE_VIOLATION`` for an authenticated actor outside its
  scope and ``404 E_NOT_FOUND`` when the resource must not be acknowledged at
  all (``API_CONTRACT.md`` §1.1 rule 3).

Audit writes are **not** performed here: the function raises, and the calling
service appends the ``access.denied`` event inside the same transaction so a
denial can never be silently swallowed.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import ActorType, Role
from app.core.errors import ApiError, ErrorCode


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated identity behind a request.

    Built exclusively from a stored session row plus its user row; nothing here
    is trusted from a request body or query parameter.
    """

    user_id: str
    username: str
    display_name: str
    role: Role
    patient_id: str | None
    session_id: str
    timezone: str = "Africa/Cairo"

    @property
    def actor_type(self) -> ActorType:
        """Audit actor class derived from the role."""
        return ActorType.DEMO_ADMIN if self.role is Role.DEMO_ADMIN else ActorType.USER


def require_role(principal: Principal, *allowed: Role) -> None:
    """Raise ``403 E_FORBIDDEN`` unless ``principal`` holds an allowed role."""
    if principal.role not in allowed:
        raise ApiError(
            403,
            ErrorCode.FORBIDDEN,
            "This operation is not available for the current role.",
        )


def require_doctor(principal: Principal) -> None:
    """Require the doctor role."""
    require_role(principal, Role.DOCTOR)


def require_patient(principal: Principal) -> None:
    """Require the patient role."""
    require_role(principal, Role.PATIENT)


def require_demo_admin(principal: Principal, *, demo_mode: bool) -> None:
    """Require a demo administrator while demo mode is enabled.

    The two failures are deliberately distinct: a non-admin gets
    ``403 E_FORBIDDEN``; an admin outside demo mode gets
    ``403 E_DEMO_MODE_REQUIRED`` (``NEG-12`` semantics, built in P2).
    """
    require_role(principal, Role.DEMO_ADMIN)
    if not demo_mode:
        raise ApiError(
            403,
            ErrorCode.DEMO_MODE_REQUIRED,
            "Demo administration is disabled unless demo mode is enabled locally.",
        )


def require_assigned_patient(principal: Principal, *, assigned_doctor_id: str) -> None:
    """Raise unless the doctor in ``principal`` is assigned to the patient row.

    ``assigned_doctor_id`` must come from the database read of the patient row,
    never from the request.
    """
    require_doctor(principal)
    if assigned_doctor_id != principal.user_id:
        raise ApiError(
            403,
            ErrorCode.SCOPE_VIOLATION,
            "This patient is not assigned to the current user.",
        )


def require_self_patient(principal: Principal, *, patient_id: str | None) -> None:
    """Raise unless ``patient_id`` is the caller's own patient scope."""
    require_patient(principal)
    if principal.patient_id is None or principal.patient_id != patient_id:
        raise ApiError(
            403,
            ErrorCode.SCOPE_VIOLATION,
            "This record is not available to the current user.",
        )


def self_patient_id(principal: Principal) -> str:
    """Return the caller's own patient id, refusing a patient without one."""
    require_patient(principal)
    if principal.patient_id is None:
        raise ApiError(
            403,
            ErrorCode.SCOPE_VIOLATION,
            "This account has no patient record.",
        )
    return principal.patient_id


__all__ = [
    "ActorType",
    "Principal",
    "Role",
    "require_assigned_patient",
    "require_demo_admin",
    "require_doctor",
    "require_patient",
    "require_role",
    "require_self_patient",
    "self_patient_id",
]
