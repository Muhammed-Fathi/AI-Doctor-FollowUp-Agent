"""Document endpoints (Phase 3, ``API_CONTRACT.md`` §2.4).

Split by operation group rather than by resource so each module has one
authorization posture and one response contract:

``upload``  patient-self, write, ``202``
``read``    metadata/file for patient-self or doctor-assigned; extraction is doctor-only
``verify``  doctor-assigned, append-only write

``router`` in this package is the union the versioned application router mounts.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import read, upload, verify

#: The five P3 document operations, in contract order.
router = APIRouter()
router.include_router(upload.router)
router.include_router(read.router)
router.include_router(verify.router)

__all__ = ["read", "router", "upload", "verify"]
