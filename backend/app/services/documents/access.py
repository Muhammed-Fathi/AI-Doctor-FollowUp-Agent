"""Document access control, composed from the P2 policy primitives.

P3 deliberately adds **no new authorization primitive**. Every check here calls
an existing function in :mod:`app.core.policies`, so the document surface cannot
drift from the P2 role/scope matrix:

* a **patient** may reach only the document whose ``patient_id`` equals their own
  ``user.patient_id`` (taken from the session, never the request);
* a **doctor** may reach only documents of patients whose
  ``assigned_doctor_id`` is that doctor;
* everyone else is out of scope.

Denials raise the shared ``403 E_SCOPE_VIOLATION`` and the calling service appends
an ``access.denied`` audit event, so a denial can never be silently swallowed
(``API_CONTRACT.md`` §1.1 rule 4).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.core.policies import (
    Principal,
    require_assigned_patient,
    require_doctor,
    require_self_patient,
)
from app.db.models import Document, Patient

#: Wording reused for "absent or not yours", so a caller cannot distinguish the
#: two cases for a resource they may not acknowledge (``API_CONTRACT.md`` §1.1).
_NOT_FOUND_DETAIL = "This document is not available."


def load_patient(db: Session, patient_id: str) -> Patient | None:
    """Return the patient row for ``patient_id``, or ``None``."""
    return db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()


def load_document(db: Session, document_id: str) -> Document | None:
    """Return the document row for ``document_id``, or ``None``."""
    return db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()


def require_document_read_access(db: Session, principal: Principal, document: Document) -> None:
    """Raise unless ``principal`` may read ``document``.

    A patient may read their own document; a doctor may read a document of a
    patient assigned to them. Anything else is ``403 E_SCOPE_VIOLATION``.

    The patient branch uses ``require_self_patient``, which reads
    ``principal.patient_id`` from the session — a request body can never assert
    someone else's patient id.
    """
    if principal.role.value == "patient":
        require_self_patient(principal, patient_id=document.patient_id)
        return

    if principal.role.value == "doctor":
        patient = load_patient(db, document.patient_id)
        if patient is None:  # pragma: no cover - FK guarantees the row
            raise ApiError(404, ErrorCode.NOT_FOUND, _NOT_FOUND_DETAIL)
        require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)
        return

    # demo_admin and any future role have no clinical read access.
    raise ApiError(
        403,
        ErrorCode.FORBIDDEN,
        "This operation is not available for the current role.",
    )


def require_doctor_document_scope(db: Session, principal: Principal, document: Document) -> None:
    """Raise unless ``principal`` is a doctor assigned to the document's patient.

    Used by every doctor-only operation (extraction view, verification), where a
    patient must never be allowed even for their own document
    (``API_CONTRACT.md`` §2.4).
    """
    require_doctor(principal)
    patient = load_patient(db, document.patient_id)
    if patient is None:  # pragma: no cover - FK guarantees the row
        raise ApiError(404, ErrorCode.NOT_FOUND, _NOT_FOUND_DETAIL)
    require_assigned_patient(principal, assigned_doctor_id=patient.assigned_doctor_id)


def patient_id_for_upload(principal: Principal) -> str:
    """Return the uploader's own patient id, refusing any other role.

    The patient id used for an upload is the authenticated session's, never a
    request field. That is what makes cross-patient upload impossible rather than
    merely discouraged.
    """
    from app.core.policies import self_patient_id

    return self_patient_id(principal)


__all__ = [
    "load_document",
    "load_patient",
    "patient_id_for_upload",
    "require_doctor_document_scope",
    "require_document_read_access",
]
