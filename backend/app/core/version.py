"""Application version and contract-version constants.

Values mirror the accepted P0 contracts:

* ``API_VERSION`` — URL prefix, ``API_CONTRACT.md`` §1.
* ``WORKFLOW_VERSION`` — graph shape/semantics, ``STATE_AND_GRAPH_CONTRACT.md`` §2.
* ``POLICY_VERSION`` — demo review policy, ``DEMO_REVIEW_RULES.md`` §"policy_version".

Phase 1 exposes them only as metadata on ``/version``; no workflow or policy
engine exists yet.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache

APP_VERSION: str = "0.1.0"
API_VERSION: str = "v1"
WORKFLOW_VERSION: str = "1.0.0"
POLICY_VERSION: str = "demo-policy-1.1.0"

UNKNOWN_GIT_SHA: str = "unknown"

#: Educational notice required by ``REQ-SEC-05``. Rendered by the API and the UI.
DEMO_NOTICE: str = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"


def _normalise_sha(value: str | None) -> str | None:
    """Return a commit SHA if ``value`` looks like one, else ``None``.

    Accepts a 40-character SHA-1 or a 7-39 character abbreviated SHA and an
    optional ``-dirty`` suffix would break the OpenAPI ``maxLength: 40``
    constraint, so it is stripped and reported as the plain SHA instead.
    """
    if not value:
        return None
    candidate = value.strip()
    if candidate.endswith("-dirty"):
        candidate = candidate[: -len("-dirty")]
    if not candidate or len(candidate) > 40:
        return None
    if not all(ch in "0123456789abcdef" for ch in candidate.lower()):
        return None
    return candidate.lower()


@lru_cache(maxsize=1)
def resolve_git_sha() -> str:
    """Resolve the build SHA deterministically.

    Order of precedence:

    1. ``APP_GIT_SHA`` environment variable (set by CI and by ``start.ps1``).
    2. ``git rev-parse HEAD`` executed in the repository root, if git is present.
    3. ``"unknown"`` — never an invented value.
    """
    from_env = _normalise_sha(os.environ.get("APP_GIT_SHA"))
    if from_env:
        return from_env

    from app.core.paths import REPO_ROOT

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # git missing or timed out
        return UNKNOWN_GIT_SHA

    if completed.returncode != 0:
        return UNKNOWN_GIT_SHA
    return _normalise_sha(completed.stdout) or UNKNOWN_GIT_SHA
