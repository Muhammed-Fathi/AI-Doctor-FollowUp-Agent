"""Single assembly point for the versioned application router.

Every P2 route is included here so the whole HTTP surface can be reviewed in one
place and enumerated by the OpenAPI contract gate
(``scripts/python/check_openapi.py``), which asserts an exact allowlist rather
than "at least these paths".
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.demo import router as demo_router
from app.api.v1.doctor import patients as doctor_patients
from app.api.v1.documents import router as documents_router
from app.api.v1.patient import checkins as patient_checkins

router = APIRouter()
router.include_router(auth_router)
router.include_router(doctor_patients.router)
router.include_router(patient_checkins.router)
router.include_router(demo_router.router)
router.include_router(documents_router)

__all__ = ["router"]
