"""Typed application settings.

Configuration is environment-first with safe local defaults (``AGENTS.md`` §7).
No secret is ever given a real default and ``.env`` is gitignored; see
``.env.example`` for the documented keys.

Settings cover the P1 foundation (ASGI bind address, SQLite URL, environment
name, optional explicit git SHA) and the P2 additions the patient domain needs:
session lifetime, login throttling, demo mode and the local demo seed password.
Ollama/Tesseract/OCR settings are deliberately **not** defined yet (P3/P5), and
``.env.example`` is updated in the same change that introduces a key.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import REPO_ROOT, RUNTIME_DIR
from app.core.version import UNKNOWN_GIT_SHA, resolve_git_sha

DEFAULT_DATABASE_URL = f"sqlite:///{(RUNTIME_DIR / 'app.db').as_posix()}"

Environment = Literal["local", "ci", "test"]


class Settings(BaseSettings):
    """Runtime configuration resolved from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- application -------------------------------------------------------
    app_env: Environment = Field(default="local", description="local | ci | test")
    app_host: str = Field(default="127.0.0.1", description="ASGI bind host (loopback only)")
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_git_sha: str | None = Field(
        default=None,
        description="Explicit build SHA; overrides git detection. Must be 7-40 hex chars.",
    )
    log_level: Literal["critical", "error", "warning", "info", "debug"] = "info"

    # --- database ----------------------------------------------------------
    database_url: str = Field(
        default=DEFAULT_DATABASE_URL,
        description="SQLAlchemy URL. Relative SQLite paths are resolved against the repo root.",
    )

    @field_validator("database_url")
    @classmethod
    def _resolve_sqlite_path(cls, value: str) -> str:
        """Make relative SQLite paths repository-root relative.

        A bare ``sqlite:///data/runtime/app.db`` would otherwise resolve against
        the current working directory, which differs between ``start.ps1``,
        pytest and Alembic on Windows.
        """
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw = value[len(prefix) :]
        if raw == ":memory:" or raw.startswith("file:"):
            return value
        from pathlib import Path

        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return f"{prefix}{path.as_posix()}"

    @field_validator("app_git_sha")
    @classmethod
    def _validate_sha(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        candidate = value.strip().lower()
        if len(candidate) < 7 or len(candidate) > 40:
            raise ValueError("APP_GIT_SHA must be 7-40 hexadecimal characters")
        if any(ch not in "0123456789abcdef" for ch in candidate):
            raise ValueError("APP_GIT_SHA must be hexadecimal")
        return candidate

    # --- P2 authentication and demo administration --------------------------
    # Session tokens are opaque and stored hashed. The TTL is a P2 decision
    # ("Token TTL and refresh are P2 decisions", API_CONTRACT.md §1.2): 60
    # minutes, configurable, no refresh token in the MVP.
    session_ttl_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Session lifetime in minutes (1-1440).",
    )
    login_rate_limit_attempts: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Failed logins tolerated per username inside the window.",
    )
    login_rate_limit_window_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Rolling window for the login failure counter.",
    )
    demo_mode: bool = Field(
        default=False,
        description=(
            "Enables POST /api/v1/demo/reset. False by default so the destructive "
            "demo operation is never reachable by accident (OQ-04)."
        ),
    )
    demo_seed_password: SecretStr | None = Field(
        default=None,
        description=(
            "Local-only demo account password used when seeding synthetic users. "
            "Supplied through the environment; never committed, never defaulted, "
            "never returned by an endpoint or written to a log."
        ),
    )

    @field_validator("demo_seed_password", mode="before")
    @classmethod
    def _empty_password_is_none(cls, value: object) -> object:
        """Treat an empty environment value as "not configured"."""
        if value is None:
            return None
        if isinstance(value, SecretStr):
            return value if value.get_secret_value() else None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    # --- derived helpers ---------------------------------------------------
    @property
    def git_sha(self) -> str:
        """Build SHA: explicit setting wins, then git detection, else ``unknown``."""
        return self.app_git_sha or resolve_git_sha()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used by the app, tests and scripts."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests that patch the environment)."""
    get_settings.cache_clear()


__all__ = [
    "DEFAULT_DATABASE_URL",
    "UNKNOWN_GIT_SHA",
    "Settings",
    "get_settings",
    "reset_settings_cache",
]
