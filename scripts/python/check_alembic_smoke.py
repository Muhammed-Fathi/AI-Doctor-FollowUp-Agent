#!/usr/bin/env python
"""Assert the state of a SQLite database after an Alembic migration sequence.

Called by ``.github/workflows/ci.yml`` (after ``upgrade head``) and usable
locally. Phase 2 replaces the old "no patient-domain tables" assertion with an
**exact** expected schema per revision state, so neither a missing table nor an
unplanned one can pass.

Usage::

    python scripts/python/check_alembic_smoke.py <path-to-sqlite-db> [--state STATE]

``--state`` (default ``head``):

``head``
    revision ``0002_p2_patient_domain``; tables = P1 + the seven P2 tables;
    ``user.patient_id`` foreign key present; ``PRAGMA foreign_key_check`` empty.
``p1``
    revision ``0001_p1_baseline``; tables = ``schema_meta`` + ``alembic_version``
    and **no** P2 table — this is what ``0002 -> 0001`` must leave behind, and the
    only way to test "P1 is preserved" (``downgrade base`` cannot test it, because
    it also drops ``schema_meta``).
``base``
    no revision recorded; only ``alembic_version`` remains — the documented empty
    state after ``0002 -> base``.

``PRAGMA foreign_key_check`` is evaluated on a connection with
``PRAGMA foreign_keys=ON``, i.e. the same setting the runtime engine uses, not the
migration engine's.

Exit code 0 = PASS, 1 = FAIL.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

P1_REVISION = "0001_p1_baseline"
HEAD_REVISION = "0002_p2_patient_domain"

P1_TABLES = {"schema_meta", "alembic_version"}

#: Tables owned by the P2 revision (exactly the seven in ``0002``).
P2_TABLES = {
    "audit_event",
    "checkin_idempotency",
    "encounter",
    "observation",
    "patient",
    "session",
    "user",
}

#: Anything belonging to a later phase. Their appearance is a scope violation.
P3_PLUS_TABLES = {
    "document",
    "extraction_attempt",
    "extracted_fact",
    "fact_verification",
    "review_item",
    "summary_draft",
    "approval_decision",
    "follow_up_task",
    "in_app_notification",
    "workflow_run",
}

VALID_STATES = {"head", "p1", "base"}


def _parse_args(argv: list[str]) -> tuple[Path, str] | None:
    """Return ``(database, state)`` or ``None`` for a usage error."""
    args = list(argv[1:])
    state = "head"
    if "--state" in args:
        index = args.index("--state")
        try:
            state = args[index + 1]
        except IndexError:
            return None
        del args[index : index + 2]
    if len(args) != 1 or state not in VALID_STATES:
        return None
    return Path(args[0]), state


def _expected_tables(state: str) -> set[str]:
    if state == "head":
        return P1_TABLES | P2_TABLES
    if state == "p1":
        return set(P1_TABLES)
    return {"alembic_version"}


def _expected_revisions(state: str) -> list[str]:
    if state == "head":
        return [HEAD_REVISION]
    if state == "p1":
        return [P1_REVISION]
    return []


def main(argv: list[str]) -> int:
    """Validate the SQLite database at ``argv[1]`` for ``--state``."""
    parsed = _parse_args(argv)
    if parsed is None:
        print(
            "usage: check_alembic_smoke.py <path-to-sqlite-db> [--state head|p1|base]",
            file=sys.stderr,
        )
        return 1

    database, state = parsed
    if not database.is_file():
        print(f"FAIL: database file not found: {database}", file=sys.stderr)
        return 1

    with sqlite3.connect(database) as connection:
        # Runtime-equivalent enforcement, so a broken FK surfaces here rather
        # than at the first application query.
        connection.execute("PRAGMA foreign_keys=ON")
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        revisions = [
            row[0] for row in connection.execute("SELECT version_num FROM alembic_version")
        ]
        user_foreign_keys = (
            list(connection.execute("PRAGMA foreign_key_list('user')")) if "user" in tables else []
        )
        foreign_key_violations = (
            connection.execute("PRAGMA foreign_key_check").fetchall() if tables else []
        )

    problems: list[str] = []

    expected_tables = _expected_tables(state)
    missing = expected_tables - tables
    if missing:
        problems.append(f"missing tables for state {state!r}: {sorted(missing)}")
    unexpected = tables - expected_tables
    if unexpected:
        problems.append(f"unexpected tables for state {state!r}: {sorted(unexpected)}")

    early = P3_PLUS_TABLES & tables
    if early:
        problems.append(f"later-phase tables must not exist: {sorted(early)}")

    expected_revisions = _expected_revisions(state)
    if revisions != expected_revisions:
        problems.append(f"expected alembic_version {expected_revisions}, found {revisions}")

    if state == "head":
        references_patient = any(row[2] == "patient" for row in user_foreign_keys)
        if not references_patient:
            problems.append("user.patient_id foreign key to patient is missing")
        if foreign_key_violations:
            problems.append(f"foreign key violations: {foreign_key_violations}")
        partial_index = "uq_observation_checkin_identity"
        with sqlite3.connect(database) as connection:
            indexes = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
        if partial_index not in indexes:
            problems.append(f"missing unique index {partial_index}")

    if problems:
        print("Alembic smoke check: FAIL", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"Alembic smoke check: PASS (state {state}, revision {expected_revisions or 'none'}, "
        f"tables {sorted(tables)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
