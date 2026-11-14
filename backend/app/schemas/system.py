"""Typed response models for the two public system endpoints.

Field names, required sets and the ``DependencyState`` enum match the accepted
P0 contract exactly (``docs/contracts/openapi.phase0.yaml`` components
``Health``, ``DependencyState`` and ``VersionInfo``). Any change here is a
contract change and must be raised with the owner instead of applied silently.

``DependencyState`` is a shared ``StrEnum`` component so the generated OpenAPI
document references one ``#/components/schemas/DependencyState`` instead of
inlining three anonymous enums (contract parity, ``P0`` review finding R-05).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DependencyState(StrEnum):
    """Dependency health vocabulary shared by every ``/health`` field."""

    OK = "ok"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


class Health(BaseModel):
    """``GET /health`` — liveness and dependency status only.

    ``/health`` never reports a clinical or demo-success state; dependency
    fields report process facts as ``ok`` / ``unavailable`` / ``not_configured``.
    A missing local model or OCR engine must not fail liveness.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    version: str
    db: DependencyState
    ollama: DependencyState
    tesseract: DependencyState
    disclaimer: str | None = None


class VersionInfo(BaseModel):
    """``GET /version`` — build and contract versions, never secrets."""

    model_config = ConfigDict(extra="forbid")

    app_version: str
    api_version: Literal["v1"]
    workflow_version: str
    policy_version: str
    git_sha: str = Field(default="unknown", max_length=40)


__all__ = ["DependencyState", "Health", "VersionInfo"]
