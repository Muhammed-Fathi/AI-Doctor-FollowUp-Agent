#!/usr/bin/env python
"""Assert the state of a database after the Alembic smoke sequence.

Called by ``.github/workflows/ci.yml`` and usable locally after
``alembic upgrade head``. Verifies that the P1 baseline is present and that no
P2 domain table was created early.

Usage::

    python scripts/python/check_alembic_smoke.py <path-to-sqlite-db>

Exit code 0 = PASS, 1 = FAIL.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASELINE_REVISION = "0001_p1_baseline"
REQUIRED_TABLES = {"schema_meta", "alembic_version"}

#: Tables owned by later phases (P2+) that must not exist in a P1 database.
P2_TABLES = {
    "user",
    "patient",
    "encounter",
    "document",
    "extraction_attempt",
    "extracted_fact",
    "fact_verification",
    "observation",
    "review_item",
    "summary_draft",
    "approval_decision",
    "follow_up_task",
    "in_app_notification",
    "workflow_run",
    "audit_event",
}


def main(argv: list[str]) -> int:
    """Validate the SQLite database at ``argv[1]``."""
    if len(argv) != 2:
        print("usage: check_alembic_smoke.py <path-to-sqlite-db>", file=sys.stderr)
        return 1

    database = Path(argv[1])
    if not database.is_file():
        print(f"FAIL: database file not found: {database}", file=sys.stderr)
        return 1

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        revisions = [
            row[0] for row in connection.execute("SELECT version_num FROM alembic_version")
        ]

    problems: list[str] = []

    missing = REQUIRED_TABLES - tables
    if missing:
        problems.append(f"missing required tables: {sorted(missing)}")

    if revisions != [BASELINE_REVISION]:
        problems.append(f"expected alembic_version {[BASELINE_REVISION]}, found {revisions}")

    early_tables = P2_TABLES & tables
    if early_tables:
        problems.append(f"P2 domain tables must not exist in P1: {sorted(early_tables)}")

    if problems:
        print("Alembic smoke check: FAIL", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"Alembic smoke check: PASS (revision {BASELINE_REVISION}, tables {sorted(tables)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
