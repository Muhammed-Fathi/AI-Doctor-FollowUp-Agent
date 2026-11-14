"""RFC-9457-style problem envelope and the P2 error catalogue.

``API_CONTRACT.md`` §1.1 fixes the error body shape and §4 fixes the stable
machine-readable ``code`` values. Every P2 failure path returns that envelope,
including framework-level validation errors, so a client never has to parse a
FastAPI default ``{"detail": ...}`` body.

Rules encoded here:

1. ``detail`` is neutral text. It never contains document content, patient free
   text, a password, a token, a SQL statement or a stack trace
   (``REQ-AUDIT-02``, ``AGENTS.md`` §3.1).
2. Field-level validation messages are reduced to ``{field, reason}`` pairs. The
   pydantic error *type* is used as ``reason``; the submitted input value is
   never echoed back, so a malformed credential body cannot be reflected.
3. ``401`` bodies are identical for "no token", "expired token", "revoked
   token" and "unknown token" (``REQ-AUTH-03``/``NEG-10``): the caller cannot
   learn whether a session ever existed.
4. Applying the handlers is a separate function (``install_problem_handlers``)
   so the ASGI wiring stays in ``app/main.py`` and this module remains
   import-side-effect free for unit tests.
"""

from __future__ import annotations

import logging
import uuid
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

#: Media type required by ``API_CONTRACT.md`` §1.1.
PROBLEM_MEDIA_TYPE: str = "application/problem+json"

#: Prefix used to build the ``type`` URI of a problem document.
PROBLEM_TYPE_PREFIX: str = "https://demo.local/errors"

#: Longest ``detail`` allowed by the contract (``Problem.detail`` maxLength 500).
MAX_DETAIL_LENGTH: int = 500

#: Longest client-supplied request id accepted before one is generated.
MAX_REQUEST_ID_LENGTH: int = 64

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    """Stable error codes implemented by the P2 surface.

    Only codes reachable in P2 (plus ``E_INTERNAL``) are listed. Codes owned by
    later phases (``E_UNVERIFIED_FACT``, ``E_FILE_TOO_LARGE``, …) are
    deliberately absent: this module must not advertise a capability that does
    not exist yet.
    """

    UNAUTHENTICATED = "E_UNAUTHENTICATED"
    INVALID_CREDENTIALS = "E_INVALID_CREDENTIALS"
    FORBIDDEN = "E_FORBIDDEN"
    SCOPE_VIOLATION = "E_SCOPE_VIOLATION"
    DEMO_MODE_REQUIRED = "E_DEMO_MODE_REQUIRED"
    NOT_FOUND = "E_NOT_FOUND"
    VALIDATION = "E_VALIDATION"
    UNIT_NOT_ALLOWED = "E_UNIT_NOT_ALLOWED"
    DUPLICATE_CHECKIN = "E_DUPLICATE_CHECKIN"
    IDEMPOTENCY_CONFLICT = "E_IDEMPOTENCY_CONFLICT"
    RATE_LIMITED = "E_RATE_LIMITED"
    INTERNAL = "E_INTERNAL"


#: Default human-readable titles; the contract's catalogue wording, kept short.
_TITLES: dict[ErrorCode, str] = {
    ErrorCode.UNAUTHENTICATED: "Not authenticated",
    ErrorCode.INVALID_CREDENTIALS: "Login failed",
    ErrorCode.FORBIDDEN: "Forbidden",
    ErrorCode.SCOPE_VIOLATION: "Out of scope",
    ErrorCode.DEMO_MODE_REQUIRED: "Demo mode required",
    ErrorCode.NOT_FOUND: "Not found",
    ErrorCode.VALIDATION: "Request validation failed",
    ErrorCode.UNIT_NOT_ALLOWED: "Unit not allowed",
    ErrorCode.DUPLICATE_CHECKIN: "Duplicate check-in",
    ErrorCode.IDEMPOTENCY_CONFLICT: "Idempotency conflict",
    ErrorCode.RATE_LIMITED: "Too many attempts",
    ErrorCode.INTERNAL: "Internal error",
}

#: Uniform wording for every unauthenticated response (no existence leak).
UNAUTHENTICATED_DETAIL: str = "A valid session is required."

#: Uniform wording for every credential failure (no user-existence leak).
INVALID_CREDENTIALS_DETAIL: str = "Username or password is incorrect."


class ApiError(Exception):
    """An error that renders as the contract problem envelope."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode | str,
        detail: str,
        *,
        title: str | None = None,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = int(status_code)
        self.code = ErrorCode(code) if not isinstance(code, ErrorCode) else code
        self.detail = _bounded(detail)
        self.title = title or _TITLES.get(self.code, "Request failed")
        self.details = details or []
        self.headers = headers or {}
        super().__init__(self.detail)

    def payload(self, request: Request) -> dict[str, Any]:
        """Render the problem document for ``request``."""
        body: dict[str, Any] = {
            "type": f"{PROBLEM_TYPE_PREFIX}/{self.code.value}",
            "title": self.title,
            "status": self.status_code,
            "code": self.code.value,
            "detail": self.detail,
            "instance": request.url.path,
            "request_id": request_id_for(request),
        }
        if self.details:
            body["details"] = self.details
        return body


def _bounded(text: str) -> str:
    """Clamp ``text`` to the contract's ``detail`` length, never splitting content."""
    collapsed = " ".join(text.split())
    return collapsed[:MAX_DETAIL_LENGTH]


def request_id_for(request: Request) -> str:
    """Return the request id for ``request``, generating one when absent.

    A client-supplied ``X-Request-ID`` is honoured only when it is a bounded,
    identifier-shaped string; otherwise a fresh UUID4 is used. The value is used
    for correlation and audit only, never as an authorization input.
    """
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing:
        return existing

    candidate = request.headers.get("X-Request-ID", "").strip()
    if candidate and len(candidate) <= MAX_REQUEST_ID_LENGTH and _is_identifier(candidate):
        resolved = candidate
    else:
        resolved = str(uuid.uuid4())
    request.state.request_id = resolved
    return resolved


def _is_identifier(value: str) -> bool:
    """Return ``True`` for a conservative identifier charset."""
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
    return bool(value) and all(character in allowed for character in value)


def _json(status_code: int, body: dict[str, Any], headers: dict[str, str] | None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers or None,
    )


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Reduce pydantic errors to ``{field, reason}`` without echoing input."""
    details: list[dict[str, Any]] = []
    for error in exc.errors()[:10]:
        location = [
            str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")
        ]
        details.append(
            {
                "field": ".".join(location) or "body",
                "reason": str(error.get("type", "invalid")),
            }
        )
    return details


def install_problem_handlers(app: FastAPI) -> None:
    """Attach the request-id middleware and the problem-envelope handlers.

    Called from ``app/main.py`` when the application router is wired. Kept out of
    module import so unit tests can construct an isolated app.
    """

    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next: Any) -> Any:
        request.state.request_id = request_id_for(request)
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request.state.request_id)
        return response

    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return _json(exc.status_code, exc.payload(request), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        problem = ApiError(
            400,
            ErrorCode.VALIDATION,
            "The request body or parameters are not valid.",
            details=_validation_details(exc),
        )
        return _json(problem.status_code, problem.payload(request), None)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: ErrorCode.UNAUTHENTICATED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            405: ErrorCode.VALIDATION,
            429: ErrorCode.RATE_LIMITED,
        }.get(
            exc.status_code, ErrorCode.INTERNAL if exc.status_code >= 500 else ErrorCode.VALIDATION
        )
        detail = (
            UNAUTHENTICATED_DETAIL
            if code is ErrorCode.UNAUTHENTICATED
            else _bounded(str(exc.detail or _TITLES.get(code, "Request failed")))
        )
        problem = ApiError(exc.status_code, code, detail)
        return _json(problem.status_code, problem.payload(request), None)

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the exception type and request id only; the response stays generic.
        logger.error(
            "unhandled error request_id=%s type=%s",
            request_id_for(request),
            type(exc).__name__,
        )
        problem = ApiError(500, ErrorCode.INTERNAL, "An unexpected error occurred.")
        return _json(problem.status_code, problem.payload(request), None)


__all__ = [
    "INVALID_CREDENTIALS_DETAIL",
    "MAX_DETAIL_LENGTH",
    "PROBLEM_MEDIA_TYPE",
    "PROBLEM_TYPE_PREFIX",
    "UNAUTHENTICATED_DETAIL",
    "ApiError",
    "ErrorCode",
    "install_problem_handlers",
    "request_id_for",
]
