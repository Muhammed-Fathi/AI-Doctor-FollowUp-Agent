"""``REQ-AUTH-02`` — the role/scope matrix as executable policy.

Requirement mapping: ``REQ-AUTH-02`` (role + patient-scope enforcement),
``REQ-SEC-01`` (cross-patient denial), ``NEG-16`` (a patient may not use doctor
capabilities), ``NEG-02`` (an unassigned doctor is out of scope), plus the
``DEMO_MODE`` guard (``NEG-12`` semantics, built in P2).

These are direct calls to ``app.core.policies`` with real principals created from
seeded rows, so the assertions test the same functions the routers use.
"""

from __future__ import annotations

import pytest
from support import PATIENT_A_ID, PATIENT_B_ID

from app.core.enums import Role
from app.core.errors import ApiError, ErrorCode
from app.core.policies import (
    Principal,
    require_assigned_patient,
    require_demo_admin,
    require_doctor,
    require_patient,
    require_role,
    require_self_patient,
    self_patient_id,
)


def test_assigned_doctor_passes_the_scope_check(doctor_principal: Principal) -> None:
    """A doctor assigned to the patient may read it."""
    require_doctor(doctor_principal)
    require_assigned_patient(doctor_principal, assigned_doctor_id=doctor_principal.user_id)


def test_unassigned_doctor_is_a_scope_violation(unassigned_doctor_principal: Principal) -> None:
    """NEG-02: another doctor's patient is ``403 E_SCOPE_VIOLATION``."""
    with pytest.raises(ApiError) as caught:
        require_assigned_patient(
            unassigned_doctor_principal,
            assigned_doctor_id="11111111-1111-4111-8111-111111111111",
        )

    assert caught.value.status_code == 403
    assert caught.value.code is ErrorCode.SCOPE_VIOLATION


def test_patient_cannot_use_a_doctor_capability(patient_principal: Principal) -> None:
    """NEG-16: the patient role is refused before any data is read."""
    with pytest.raises(ApiError) as caught:
        require_doctor(patient_principal)

    assert caught.value.code is ErrorCode.FORBIDDEN
    assert caught.value.status_code == 403


def test_demo_admin_cannot_use_a_doctor_capability(admin_principal: Principal) -> None:
    """The administrator has no clinical read capability."""
    with pytest.raises(ApiError) as caught:
        require_doctor(admin_principal)

    assert caught.value.code is ErrorCode.FORBIDDEN


def test_doctor_cannot_use_a_patient_capability(doctor_principal: Principal) -> None:
    """There is no "act as the patient" path: check-ins are patient-only."""
    with pytest.raises(ApiError) as caught:
        require_patient(doctor_principal)

    assert caught.value.code is ErrorCode.FORBIDDEN


def test_patient_self_scope_accepts_only_its_own_patient_id(patient_principal: Principal) -> None:
    """REQ-SEC-01: a patient's scope is the stored ``user.patient_id``."""
    require_self_patient(patient_principal, patient_id=PATIENT_A_ID)
    assert self_patient_id(patient_principal) == PATIENT_A_ID

    with pytest.raises(ApiError) as caught:
        require_self_patient(patient_principal, patient_id=PATIENT_B_ID)

    assert caught.value.code is ErrorCode.SCOPE_VIOLATION


def test_the_self_scope_comes_from_the_server_not_the_caller(patient_principal: Principal) -> None:
    """A caller cannot inject a scope: the value is read from the stored account."""
    forged = Principal(
        user_id=patient_principal.user_id,
        username=patient_principal.username,
        display_name=patient_principal.display_name,
        role=Role.PATIENT,
        patient_id=None,
        session_id=patient_principal.session_id,
    )

    with pytest.raises(ApiError) as caught:
        self_patient_id(forged)

    assert caught.value.code is ErrorCode.SCOPE_VIOLATION


def test_demo_admin_requires_admin_role_and_demo_mode(
    admin_principal: Principal, doctor_principal: Principal
) -> None:
    """NEG-12 semantics: role first, then the local demo-mode flag."""
    require_demo_admin(admin_principal, demo_mode=True)

    with pytest.raises(ApiError) as disabled:
        require_demo_admin(admin_principal, demo_mode=False)
    assert disabled.value.code is ErrorCode.DEMO_MODE_REQUIRED

    with pytest.raises(ApiError) as not_admin:
        require_demo_admin(doctor_principal, demo_mode=True)
    assert not_admin.value.code is ErrorCode.FORBIDDEN


def test_require_role_accepts_only_the_listed_roles(doctor_principal: Principal) -> None:
    """The generic role guard is an exact membership test."""
    require_role(doctor_principal, Role.DOCTOR)
    with pytest.raises(ApiError):
        require_role(doctor_principal, Role.PATIENT, Role.DEMO_ADMIN)
