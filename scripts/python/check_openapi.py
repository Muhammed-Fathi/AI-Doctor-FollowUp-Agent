#!/usr/bin/env python
"""Assert the generated OpenAPI surface matches the Phase 1 contract.

Used by ``scripts/powershell/test_all.ps1`` and by CI as a cheap, offline
contract gate. It imports the FastAPI app (no server, no network) and checks:

1. exactly ``/health`` and ``/version`` are exposed;
2. the ``Health`` and ``VersionInfo`` required sets match
   ``docs/contracts/openapi.phase0.yaml``;
3. both operations are public (``security: []``);
4. the educational notice is present in ``info``.

Exit code 0 = contract matches, 1 = mismatch (details on stderr).

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

EXPECTED_PATHS = {"/health", "/version"}
EXPECTED_HEALTH_REQUIRED = {"status", "version", "db", "ollama", "tesseract"}
EXPECTED_VERSION_REQUIRED = {
    "app_version",
    "api_version",
    "workflow_version",
    "policy_version",
}
EXPECTED_DEPENDENCY_ENUM = ["ok", "unavailable", "not_configured"]
EXPECTED_NOTICE = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"


def collect_errors(schema: dict[str, Any]) -> list[str]:
    """Return every contract deviation found in ``schema`` (empty = conforming)."""
    errors: list[str] = []

    paths = set(schema.get("paths", {}))
    if paths != EXPECTED_PATHS:
        errors.append(f"paths mismatch: expected {sorted(EXPECTED_PATHS)}, found {sorted(paths)}")

    components = schema.get("components", {}).get("schemas", {})

    health = components.get("Health")
    if not health:
        errors.append("components.schemas.Health is missing")
    else:
        required = set(health.get("required", []))
        if required != EXPECTED_HEALTH_REQUIRED:
            errors.append(
                f"Health.required mismatch: expected {sorted(EXPECTED_HEALTH_REQUIRED)}, "
                f"found {sorted(required)}"
            )
        status_enum = health.get("properties", {}).get("status", {}).get("enum")
        if status_enum != ["ok", "degraded"]:
            errors.append(f"Health.status enum mismatch: {status_enum!r}")

    dependency = components.get("DependencyState")
    if not dependency:
        errors.append("components.schemas.DependencyState is missing")
    elif dependency.get("enum") != EXPECTED_DEPENDENCY_ENUM:
        errors.append(f"DependencyState enum mismatch: {dependency.get('enum')!r}")

    version = components.get("VersionInfo")
    if not version:
        errors.append("components.schemas.VersionInfo is missing")
    else:
        required = set(version.get("required", []))
        if required != EXPECTED_VERSION_REQUIRED:
            errors.append(
                f"VersionInfo.required mismatch: expected {sorted(EXPECTED_VERSION_REQUIRED)}, "
                f"found {sorted(required)}"
            )
        if version.get("properties", {}).get("api_version", {}).get("const") != "v1":
            errors.append("VersionInfo.api_version must be const 'v1'")

    for path in EXPECTED_PATHS & paths:
        operation = schema["paths"][path].get("get", {})
        if operation.get("security") != []:
            errors.append(f"{path} must declare security: [] (public endpoint)")

    if schema.get("info", {}).get("x-demo-notice") != EXPECTED_NOTICE:
        errors.append("info.x-demo-notice is missing or has drifted from the required notice")

    return errors


def main() -> int:
    """Run the check and report the result."""
    from app.main import create_app

    schema = create_app().openapi()
    errors = collect_errors(schema)

    if errors:
        print("OpenAPI contract check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "OpenAPI contract check: PASS "
        f"({len(schema['paths'])} paths, {len(schema['components']['schemas'])} schemas)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
