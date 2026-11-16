"""P3-R21 rejection/recovery acceptance tests — Stage 1 (RED first).

This module is the executable acceptance matrix from
``docs/phase-reports/P3_R21_REJECTION_RECOVERY_DESIGN.md`` §7. It was written
**before** the production change and is run against the reviewed PR #10 head
``18a53b2``. The contract:

* **R1-R8 are RED.** They describe capabilities that do not exist yet (the
  rejection-first terminal rule, ``recovery_of``, the self-FK column, the
  patient-safe metadata and the ``0004`` migration). A RED result is the
  expected baseline, not a defect in this module.
* **G1-G8 are GREEN.** They are existing guarantees that must survive the
  change. They are re-asserted here so a regression is visible next to the new
  behaviour instead of only in the older modules.
* **G9** is the pre-existing suite, run separately.
* **W1/W2** are owner-Windows evidence and are deliberately absent from this
  module.

No production code, schema, migration, API route, OCR configuration, parser
grammar, golden fixture or clinical contract is changed by this module. The
SQLite migration test (R8) is a *specification*: it drives the future
``0004_p3_rejection_recovery`` revision through Alembic and asserts the schema,
foreign-key, row-preservation and downgrade-refusal behaviour. Until Stage 3
lands that revision it fails at the first ``command.upgrade`` — the honest RED
baseline.

The migration operations are deliberately described as * behaviour*, not as
raw SQL: SQLite has no ``ALTER TABLE ... ADD/DROP CONSTRAINT``, so the Stage 3
implementation must use Alembic's batch mode (``batch_alter_table``) for the
self-FK. The test asserts the resulting schema, not the DDL text.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from support import FIXED_NOW, SEED_PASSWORD, TEST_HASH_ITERATIONS

from app.core.paths import REPO_ROOT
from app.db.models import (
    AuditEvent,
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    Patient,
    User,
    VerificationIssue,
)
from app.db.session import create_db_engine
from app.services.documents import quality
from app.services.seed import seed_demo_data

UPLOAD = "/api/v1/documents/upload"

ALEMBIC_INI = REPO_ROOT / "backend" / "migrations" / "alembic.ini"
P3_REVISION = "0003_p3_documents"
R21_REVISION = "0004_p3_rejection_recovery"

#: The rejection failure codes introduced by Approach A (§4.1).
MEASUREMENT_REJECTED = "measurement_rejected"
FACT_REJECTED = "fact_rejected"
ALL_FACTS_REJECTED = "all_facts_rejected"

#: The audit event that a successful recovery must append, and only then.
EVENT_DOCUMENT_RECOVERED = "document.recovered"


# --- helpers -----------------------------------------------------------------


def _upload(client, headers, payload: bytes, *, filename="report.pdf", data=None):
    """POST one upload, optionally carrying form fields such as ``recovery_of``."""
    return client.post(
        UPLOAD,
        headers=headers,
        files={"file": (filename, payload, "application/pdf")},
        data=data,
    )


def _accepted(client, headers, payload: bytes, *, filename="report.pdf", data=None) -> str:
    """Upload expecting ``202`` and return the new document id."""
    response = _upload(client, headers, payload, filename=filename, data=data)
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def _extraction(client, headers, document_id: str) -> dict:
    """Return the doctor's extraction view."""
    response = client.get(f"/api/v1/documents/{document_id}/extraction", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _facts(client, headers, document_id: str) -> list[dict]:
    """Return the doctor-visible candidate facts."""
    return _extraction(client, headers, document_id)["facts"]


def _fact_by_field(facts: list[dict], field_name: str) -> dict:
    """Return the single fact named ``field_name``."""
    return next(fact for fact in facts if fact["field_name"] == field_name)


def _verify(client, headers, document_id: str, fact_id: str, **body):
    """POST one verification decision."""
    return client.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=headers,
        json={"fact_id": fact_id, "decision": "verified", **body},
    )


def _reject_value(client, headers, document_id: str) -> object:
    """Reject the document's ``value`` fact, leaving siblings pending."""
    value = _fact_by_field(_facts(client, headers, document_id), "value")
    return _verify(
        client,
        headers,
        document_id,
        value["fact_id"],
        decision="rejected",
        reason="not a usable reading",
    )


def _document_row(db: Session, document_id: str) -> Document:
    """Return the stored document row."""
    return db.execute(select(Document).where(Document.id == document_id)).scalar_one()


def _document_count(db: Session) -> int:
    """Return the number of stored document rows."""
    return db.execute(select(func.count()).select_from(Document)).scalar_one()


def _document_observations(db: Session, document_id: str) -> list[Observation]:
    """Return the observations derived from ``document_id``'s own facts."""
    fact_ids = {
        row.id
        for row in db.execute(
            select(ExtractedFact).where(ExtractedFact.document_id == document_id)
        ).scalars()
    }
    return [
        row for row in db.execute(select(Observation)).scalars() if row.source_fact_id in fact_ids
    ]


def _issue_rows(db: Session, document_id: str) -> list[VerificationIssue]:
    """Return the persisted verification issues for ``document_id``."""
    return list(
        db.execute(
            select(VerificationIssue).where(VerificationIssue.document_id == document_id)
        ).scalars()
    )


def _open_issue_types(db: Session, document_id: str) -> set[str]:
    """Return the issue types still open for ``document_id``."""
    return {row.issue_type for row in _issue_rows(db, document_id) if row.state == "open"}


def _audit_count(db: Session, *, event_type: str | None = None) -> int:
    """Count audit events, optionally of one type."""
    query = select(func.count()).select_from(AuditEvent)
    if event_type is not None:
        query = query.where(AuditEvent.event_type == event_type)
    return db.execute(query).scalar_one()


def _recovery_link(document: Document) -> str | None:
    """Return the recovery source id, or ``None`` when the column is absent.

    ``getattr`` keeps the RED failure a clean assertion instead of an
    ``AttributeError``: the capability is missing, not broken.
    """
    return getattr(document, "recovered_from_document_id", None)


def _active_rejected_ids(db: Session, document_id: str) -> set[str]:
    """Return the rejected facts that no correction superseded."""
    facts = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document_id)).scalars()
    )
    superseded = quality.superseded_fact_ids(facts)
    return {
        fact.id
        for fact in facts
        if fact.verification_status == "rejected" and fact.id not in superseded
    }


def _glucose_pdf(fixtures, *, value: str = "104", date: str = "2026-11-02") -> bytes:
    """Build a one-measurement synthetic glucose report with distinct bytes."""
    return fixtures.build_pdf(
        [
            [
                "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD",
                f"Demo Patient A            Ref: DEMO-A-001            Report date: {date}",
                f"Test: Fasting glucose     Value: {value} mg/dL",
                "Reference range: 70 - 99 mg/dL",
            ]
        ]
    )


def _no_facts_pdf(fixtures) -> bytes:
    """Build a text-layer page that parses to zero candidate facts.

    The line is long enough to count as a usable text layer (>= 40 non-space
    characters) but carries no date, no ``Value:`` label, no ``Test:`` row, no
    ``Reference range:`` and no ``Ref:``, so the parser produces no facts and
    intake records ``no_facts_extracted`` without touching the OCR path.
    """
    return fixtures.build_pdf(
        [["SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD - THIS PAGE DECLARES NO MEASUREMENT"]]
    )


def _document_only_pdf(fixtures, *, date: str = "2026-11-04") -> bytes:
    """Build a report that declares no measurement (title and range only)."""
    return fixtures.build_pdf(
        [
            [
                "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD",
                f"Demo Patient A            Ref: DEMO-A-001            Report date: {date}",
                "Reference range: 70 - 99 mg/dL",
            ]
        ]
    )


def _alembic_config(url: str) -> Config:
    """Return an Alembic config bound to ``url`` with logging silenced."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


def _table_columns(conn, table: str) -> dict[str, dict]:
    """Return ``PRAGMA table_info`` keyed by column name."""
    return {row["name"]: dict(row) for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _index_names(conn, table: str) -> set[str]:
    """Return ``PRAGMA index_list`` names for ``table``."""
    return {row["name"] for row in conn.execute(text(f"PRAGMA index_list({table})"))}


def _foreign_keys(conn, table: str) -> list[dict]:
    """Return ``PRAGMA foreign_key_list`` rows for ``table``."""
    return [dict(row) for row in conn.execute(text(f"PRAGMA foreign_key_list({table})"))]


# --- R1 / R1a / R1b — terminal timing ----------------------------------------


def test_r1_rejected_measurement_reject_last(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """R1: rejecting the measurement last is terminal ``failed``."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    facts = _facts(api, doctor_headers, document_id)
    value = _fact_by_field(facts, "value")

    for fact in facts:
        if fact["field_name"] != "value":
            assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    response = _verify(
        api,
        doctor_headers,
        document_id,
        value["fact_id"],
        decision="rejected",
        reason="not a usable reading",
    )

    assert response.status_code == 200, response.text
    assert response.json()["document_status"] == "failed"
    document = _document_row(db, document_id)
    assert document.extraction_status == "failed"
    assert document.failure_code == MEASUREMENT_REJECTED
    assert _document_observations(db, document_id) == []


def test_r1a_rejected_measurement_reject_first(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """R1a: the first rejection is terminal even while siblings are pending."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    facts = _facts(api, doctor_headers, document_id)
    value = _fact_by_field(facts, "value")
    siblings = [fact for fact in facts if fact["field_name"] != "value"]
    assert siblings, "the scenario needs pending siblings"

    response = _verify(
        api,
        doctor_headers,
        document_id,
        value["fact_id"],
        decision="rejected",
        reason="not a usable reading",
    )

    assert response.status_code == 200, response.text
    assert response.json()["document_status"] == "failed"
    document = _document_row(db, document_id)
    assert document.extraction_status == "failed"
    assert document.failure_code == MEASUREMENT_REJECTED

    # The patient can already see that recovery is allowed.
    meta = api.get(f"/api/v1/documents/{document_id}", headers=patient_headers)
    assert meta.status_code == 200
    assert meta.json().get("recovery_eligible") is True

    # A later sibling decision is still accepted and cannot resurrect the document.
    later = _verify(api, doctor_headers, document_id, siblings[0]["fact_id"])
    assert later.status_code == 200, later.text
    assert later.json()["document_status"] == "failed"
    assert _document_row(db, document_id).extraction_status == "failed"


def test_r1b_reject_first_and_reject_last_are_equivalent(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """R1b: reject-first and reject-last reach the same terminal state."""
    # reject-last
    last_id = _accepted(api, patient_headers, glucose_pdf)
    last_facts = _facts(api, doctor_headers, last_id)
    for fact in last_facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, last_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        last_id,
        _fact_by_field(last_facts, "value")["fact_id"],
        decision="rejected",
    )

    # reject-first, then decide the siblings
    first_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="105", date="2026-11-03"),
        filename="first.pdf",
    )
    first_facts = _facts(api, doctor_headers, first_id)
    _verify(
        api,
        doctor_headers,
        first_id,
        _fact_by_field(first_facts, "value")["fact_id"],
        decision="rejected",
    )
    for fact in first_facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, first_id, fact["fact_id"])

    last_row = _document_row(db, last_id)
    first_row = _document_row(db, first_id)
    assert last_row.extraction_status == first_row.extraction_status == "failed"
    assert last_row.failure_code == first_row.failure_code == MEASUREMENT_REJECTED
    assert _document_observations(db, last_id) == []
    assert _document_observations(db, first_id) == []


# --- R2 / R3 — the misleading ``verified`` -----------------------------------


def test_r2_rejected_non_measurement_fact(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """R2: rejecting a non-measurement fact is terminal ``fact_rejected``."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    facts = _facts(api, doctor_headers, document_id)
    reference = _fact_by_field(facts, "reference_text")

    for fact in facts:
        if fact["field_name"] != "reference_text":
            assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    response = _verify(
        api,
        doctor_headers,
        document_id,
        reference["fact_id"],
        decision="rejected",
        reason="not this patient's reading",
    )

    assert response.status_code == 200, response.text
    assert response.json()["document_status"] == "failed"
    document = _document_row(db, document_id)
    assert document.extraction_status == "failed"
    assert document.failure_code == FACT_REJECTED
    assert _document_observations(db, document_id) == []


def test_r3_no_misleading_verified_status(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """R3: an active rejected fact can never coexist with ``verified``."""
    # reject-last value
    last_id = _accepted(api, patient_headers, glucose_pdf)
    last_facts = _facts(api, doctor_headers, last_id)
    for fact in last_facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, last_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        last_id,
        _fact_by_field(last_facts, "value")["fact_id"],
        decision="rejected",
    )

    # reject-first value
    first_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="105", date="2026-11-03"),
        filename="first.pdf",
    )
    _reject_value(api, doctor_headers, first_id)

    # reject a non-measurement fact
    reference_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="106", date="2026-11-05"),
        filename="reference.pdf",
    )
    reference_facts = _facts(api, doctor_headers, reference_id)
    for fact in reference_facts:
        if fact["field_name"] != "reference_text":
            _verify(api, doctor_headers, reference_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        reference_id,
        _fact_by_field(reference_facts, "reference_text")["fact_id"],
        decision="rejected",
    )

    for document_id in (last_id, first_id, reference_id):
        assert _active_rejected_ids(db, document_id), "the scenario must have an active rejection"
        assert _document_row(db, document_id).extraction_status != "verified"
        assert not (
            _document_row(db, document_id).extraction_status == "verified"
            and "VI-002" in _open_issue_types(db, document_id)
        )


# --- R4 / R5 — recovery creation and lineage ---------------------------------


def test_r4_recovery_attempt_is_created_and_linked(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """R4: a recovery upload creates a new linked document."""
    old_id = _accepted(api, patient_headers, glucose_pdf)
    _reject_value(api, doctor_headers, old_id)
    assert _document_row(db, old_id).extraction_status == "failed"

    new_bytes = _glucose_pdf(fixtures, value="105", date="2026-11-03")
    response = _upload(
        api,
        patient_headers,
        new_bytes,
        filename="recovery.pdf",
        data={"recovery_of": old_id},
    )

    assert response.status_code == 202, response.text
    new_id = response.json()["document_id"]
    assert _recovery_link(_document_row(db, new_id)) == old_id

    old_row = _document_row(db, old_id)
    assert old_row.extraction_status == "failed"
    assert old_row.failure_code == MEASUREMENT_REJECTED
    old_rejected = list(
        db.execute(
            select(ExtractedFact).where(
                ExtractedFact.document_id == old_id,
                ExtractedFact.verification_status == "rejected",
            )
        ).scalars()
    )
    assert old_rejected, "the rejected fact must stay in the history"
    assert all(row.corrected_from_fact_id is None for row in old_rejected)


def test_r5_observation_lineage_after_recovery(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """R5: the recovery's observation hangs off the new document's own fact."""
    old_id = _accepted(api, patient_headers, glucose_pdf)
    _reject_value(api, doctor_headers, old_id)

    new_bytes = _glucose_pdf(fixtures, value="105", date="2026-11-03")
    response = _upload(
        api,
        patient_headers,
        new_bytes,
        filename="recovery.pdf",
        data={"recovery_of": old_id},
    )
    assert response.status_code == 202, response.text
    new_id = response.json()["document_id"]
    assert _recovery_link(_document_row(db, new_id)) == old_id

    new_facts = _facts(api, doctor_headers, new_id)
    for fact in new_facts:
        assert _verify(api, doctor_headers, new_id, fact["fact_id"]).status_code == 200

    new_observations = _document_observations(db, new_id)
    assert len(new_observations) == 1
    new_fact_ids = {
        row.id
        for row in db.execute(
            select(ExtractedFact).where(ExtractedFact.document_id == new_id)
        ).scalars()
    }
    assert new_observations[0].source_fact_id in new_fact_ids
    assert _document_observations(db, old_id) == []


# --- R6 — recovery-source correctness ----------------------------------------


def test_r6_recovery_source_correctness(
    api,
    patient_headers,
    other_patient_headers,
    doctor_headers,
    glucose_pdf,
    report_b_pdf,
    fixtures,
    db: Session,
):
    """R6: ``recovery_of`` is validated, and a refusal writes nothing."""
    # A terminal, self-owned source.
    terminal_id = _accepted(api, patient_headers, glucose_pdf)
    _reject_value(api, doctor_headers, terminal_id)

    # Sources in every non-recoverable state.
    pending_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="107", date="2026-11-06"),
        filename="pending.pdf",
    )
    verified_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="108", date="2026-11-07"),
        filename="verified.pdf",
    )
    for fact in _facts(api, doctor_headers, verified_id):
        assert _verify(api, doctor_headers, verified_id, fact["fact_id"]).status_code == 200

    blank_id = _accepted(
        api,
        patient_headers,
        _no_facts_pdf(fixtures),
        filename="blank.pdf",
    )
    assert _document_row(db, blank_id).failure_code == "no_facts_extracted"

    forced_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="109", date="2026-11-08"),
        filename="forced.pdf",
    )
    db.execute(
        text("UPDATE document SET extraction_status = 'pending_extraction' WHERE id = :id"),
        {"id": forced_id},
    )
    db.commit()

    other_id = _accepted(api, other_patient_headers, report_b_pdf, filename="other.pdf")

    # An identity-blocked document is never a valid source. It cannot even reach
    # `failed` through decisions (every decision is 409 E_VI_004_UNRESOLVED), so
    # it is refused on its status, not on the link rule.
    vi004_id = _accepted(api, patient_headers, report_b_pdf, filename="wrong_patient.pdf")
    _facts(api, doctor_headers, vi004_id)  # the doctor read is what syncs the issue rows
    assert "VI-004" in _open_issue_types(db, vi004_id)
    assert _document_row(db, vi004_id).extraction_status == "needs_verification"

    # A missing ``recovery_of`` is a normal upload with no link.
    plain = _upload(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="110", date="2026-11-09"),
        filename="plain.pdf",
    )
    assert plain.status_code == 202, plain.text
    assert _recovery_link(_document_row(db, plain.json()["document_id"])) is None

    documents_before = _document_count(db)

    refusals = [
        ("malformed", "not-a-uuid"),
        ("absent", "00000000-0000-4000-8000-000000000000"),
        ("cross-patient", other_id),
        ("needs_verification", pending_id),
        ("verified", verified_id),
        ("no_facts_extracted", blank_id),
        ("pending_extraction", forced_id),
        ("vi_004_unresolved", vi004_id),
    ]
    expected_status = {
        "malformed": 400,
        "absent": 404,
        "cross-patient": 404,
        "needs_verification": 400,
        "verified": 400,
        "no_facts_extracted": 400,
        "pending_extraction": 400,
        "vi_004_unresolved": 400,
    }
    for index, (label, source_id) in enumerate(refusals):
        payload = _glucose_pdf(
            fixtures,
            value=str(120 + index),
            date=f"2026-11-{10 + index:02d}",
        )
        response = _upload(
            api,
            patient_headers,
            payload,
            filename=f"{label}.pdf",
            data={"recovery_of": source_id},
        )
        assert response.status_code == expected_status[label], (
            f"{label}: {response.status_code} {response.text}"
        )

    assert _document_count(db) == documents_before, "a refused recovery must not create a row"
    assert _audit_count(db, event_type=EVENT_DOCUMENT_RECOVERED) == 0

    # Identical bytes are still a duplicate, with or without a recovery link.
    duplicate = _upload(
        api,
        patient_headers,
        glucose_pdf,
        filename="duplicate.pdf",
        data={"recovery_of": terminal_id},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "E_DUPLICATE_DOCUMENT"
    assert _document_count(db) == documents_before

    # A chain is allowed: recover a document that was itself a recovery.
    first = _upload(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="130", date="2026-11-20"),
        filename="chain_first.pdf",
        data={"recovery_of": terminal_id},
    )
    assert first.status_code == 202, first.text
    first_id = first.json()["document_id"]
    assert _recovery_link(_document_row(db, first_id)) == terminal_id
    _reject_value(api, doctor_headers, first_id)

    second = _upload(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="131", date="2026-11-21"),
        filename="chain_second.pdf",
        data={"recovery_of": first_id},
    )
    assert second.status_code == 202, second.text
    assert _recovery_link(_document_row(db, second.json()["document_id"])) == first_id

    # Only the two successful recoveries are audited.
    assert _audit_count(db, event_type=EVENT_DOCUMENT_RECOVERED) == 2


# --- R7 — patient-safe recovery metadata -------------------------------------


def test_r7_patient_sees_recovery_metadata(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """R7: the owning patient sees the terminal reason and recovery state."""
    old_id = _accepted(api, patient_headers, glucose_pdf)
    _reject_value(api, doctor_headers, old_id)

    meta = api.get(f"/api/v1/documents/{old_id}", headers=patient_headers)
    assert meta.status_code == 200
    body = meta.json()
    assert body.get("failure_code") == MEASUREMENT_REJECTED
    assert body.get("recovery_eligible") is True
    assert body.get("recovered_from_document_id") is None

    new_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="105", date="2026-11-03"),
        filename="recovery.pdf",
        data={"recovery_of": old_id},
    )
    new_meta = api.get(f"/api/v1/documents/{new_id}", headers=patient_headers)
    assert new_meta.status_code == 200
    assert new_meta.json().get("recovered_from_document_id") == old_id
    # A freshly extracted document is not terminal, so it is not recovery-eligible.
    assert new_meta.json().get("recovery_eligible") is False


def test_r7_patient_view_redaction_and_authorization_unchanged(
    api,
    patient_headers,
    other_patient_headers,
    doctor_headers,
    glucose_pdf,
):
    """R7 (existing guarantee): the patient view still hides clinical content.

    This half of R7 is GREEN today: the new fields must be added without
    widening the patient's view or the authorization boundary.
    """
    document_id = _accepted(api, patient_headers, glucose_pdf)

    body = api.get(f"/api/v1/documents/{document_id}", headers=patient_headers).json()
    for forbidden in (
        "facts",
        "raw_text",
        "normalized_value",
        "unit",
        "char_start",
        "char_end",
        "quality_flags",
        "confidence",
    ):
        assert forbidden not in body

    other = api.get(f"/api/v1/documents/{document_id}", headers=other_patient_headers)
    assert other.status_code == 403
    doctor = api.get(f"/api/v1/documents/{document_id}", headers=doctor_headers)
    assert doctor.status_code == 200
    anonymous = api.get(f"/api/v1/documents/{document_id}")
    assert anonymous.status_code == 401


# --- R8 — SQLite migration integrity (specification) -------------------------


def test_r8_sqlite_migration_integrity(tmp_path):
    """R8: the additive self-FK migration is real, enforced and safely reversible.

    This test is a specification for Stage 3. It fails today because the
    ``0004_p3_rejection_recovery`` revision does not exist. When it lands, the
    test drives a real SQLite database through Alembic and asserts the schema,
    ``PRAGMA foreign_keys=ON`` enforcement, row preservation, ``RESTRICT`` and
    the downgrade refusal.
    """
    url = f"sqlite:///{(tmp_path / 'r21_migration.db').as_posix()}"
    config = _alembic_config(url)

    # A real P3 baseline with P2 rows and one P3 document row.
    command.upgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        with Session(engine) as session:
            seed_demo_data(
                session,
                password=SEED_PASSWORD,
                now=FIXED_NOW,
                iterations=TEST_HASH_ITERATIONS,
            )
            session.commit()
            patient_id = session.execute(select(Patient.id)).scalars().first()
            user_id = session.execute(select(User.id)).scalars().first()
            document = Document(
                patient_id=patient_id,
                uploaded_by_user_id=user_id,
                original_filename="baseline.pdf",
                stored_path="baseline.pdf",
                mime_type="application/pdf",
                sha256="a" * 64,
                size_bytes=10,
                page_count=1,
                extraction_status="needs_verification",
                uploaded_at="2026-11-14T12:00:00Z",
            )
            session.add(document)
            session.commit()
            document_id = document.id
            baseline = {
                "patient": session.execute(select(func.count()).select_from(Patient)).scalar_one(),
                "user": session.execute(select(func.count()).select_from(User)).scalar_one(),
                "observation": session.execute(
                    select(func.count()).select_from(Observation)
                ).scalar_one(),
                "document": session.execute(
                    select(func.count()).select_from(Document)
                ).scalar_one(),
            }
    finally:
        engine.dispose()

    # RED today: the revision does not exist.
    command.upgrade(config, R21_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as conn:
            # The runtime connection really enforces foreign keys.
            assert conn.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

            columns = _table_columns(conn, "document")
            assert "recovered_from_document_id" in columns
            assert columns["recovered_from_document_id"]["notnull"] == 0

            indexes = _index_names(conn, "document")
            assert {
                "ix_document_recovered_from",
                "ix_document_patient",
                "ux_document_sha_patient",
            } <= indexes

            foreign_keys = _foreign_keys(conn, "document")
            self_fk = [
                row
                for row in foreign_keys
                if row["table"] == "document" and row["from"] == "recovered_from_document_id"
            ]
            assert len(self_fk) == 1
            assert self_fk[0]["on_delete"] == "RESTRICT"

            assert conn.execute(text("PRAGMA foreign_key_check")).all() == []

            for table, expected in baseline.items():
                actual = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                assert actual == expected, f"{table} rows were not preserved"

            assert (
                conn.execute(
                    text("SELECT recovered_from_document_id FROM document WHERE id = :id"),
                    {"id": document_id},
                ).scalar_one()
                is None
            )

            # The existing CHECK constraints must survive a batch rebuild.
            create_sql = conn.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name='document'")
            ).scalar_one()
            assert "status_allowed" in create_sql
            assert "mime_type_allowed" in create_sql

        # A bad parent is refused while enforcement is on.
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                    "original_filename, stored_path, mime_type, sha256, size_bytes, "
                    "page_count, extraction_status, uploaded_at, recovered_from_document_id) "
                    "VALUES (:id, :pid, :uid, 'bad.pdf', 'bad.pdf', 'application/pdf', "
                    ":sha, 10, 1, 'needs_verification', '2026-11-14T12:00:00Z', "
                    "'00000000-0000-4000-8000-000000000000')"
                ),
                {
                    "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    "pid": patient_id,
                    "uid": user_id,
                    "sha": "b" * 64,
                },
            )

        # A linked child makes the parent RESTRICT-deletable.
        child_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO document (id, patient_id, uploaded_by_user_id, "
                    "original_filename, stored_path, mime_type, sha256, size_bytes, "
                    "page_count, extraction_status, uploaded_at, recovered_from_document_id) "
                    "VALUES (:id, :pid, :uid, 'child.pdf', 'child.pdf', 'application/pdf', "
                    ":sha, 10, 1, 'needs_verification', '2026-11-14T12:00:00Z', :parent)"
                ),
                {
                    "id": child_id,
                    "pid": patient_id,
                    "uid": user_id,
                    "sha": "c" * 64,
                    "parent": document_id,
                },
            )
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text("DELETE FROM document WHERE id = :id"), {"id": document_id})
    finally:
        engine.dispose()

    # A downgrade with a live link must refuse and change nothing. The exact
    # exception type is defined by the Stage 3 migration; the contract is that
    # it refuses rather than silently dropping the column.
    with pytest.raises(Exception) as downgrade_error:
        command.downgrade(config, P3_REVISION)
    assert "recover" in str(downgrade_error.value).lower()

    engine = create_db_engine(url)
    try:
        with engine.begin() as conn:
            assert "recovered_from_document_id" in _table_columns(conn, "document")
            assert (
                conn.execute(
                    text("SELECT recovered_from_document_id FROM document WHERE id = :id"),
                    {"id": child_id},
                ).scalar_one()
                == document_id
            )
    finally:
        engine.dispose()

    # With no link, the downgrade removes the column/index/FK and the upgrade
    # restores them without losing rows.
    engine = create_db_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM document WHERE id = :id"), {"id": child_id})
    finally:
        engine.dispose()

    command.downgrade(config, P3_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as conn:
            assert "recovered_from_document_id" not in _table_columns(conn, "document")
            assert "ix_document_recovered_from" not in _index_names(conn, "document")
            assert not [
                row
                for row in _foreign_keys(conn, "document")
                if row["from"] == "recovered_from_document_id"
            ]
    finally:
        engine.dispose()

    command.upgrade(config, R21_REVISION)

    engine = create_db_engine(url)
    try:
        with engine.begin() as conn:
            assert "recovered_from_document_id" in _table_columns(conn, "document")
            assert "ix_document_recovered_from" in _index_names(conn, "document")
            for table, expected in baseline.items():
                actual = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                assert actual == expected, f"{table} rows were not preserved"
    finally:
        engine.dispose()


# --- G1-G8 - existing guarantees that must stay green ------------------------


def test_g1_correction_as_the_initial_decision(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """G1: a first-decision correction still resolves and maps."""
    payload = fixtures.build_report_pdf("report_ocr_o_confusion.txt")
    document_id = _accepted(api, patient_headers, payload, filename="correction.pdf")
    facts = _facts(api, doctor_headers, document_id)
    value = _fact_by_field(facts, "value")

    response = _verify(
        api,
        doctor_headers,
        document_id,
        value["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
        reason="checked source",
    )
    assert response.status_code == 200, response.text

    original = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == value["fact_id"])
    ).scalar_one()
    assert original.verification_status == "rejected"
    corrected = (
        db.execute(
            select(ExtractedFact).where(ExtractedFact.corrected_from_fact_id == value["fact_id"])
        )
        .scalars()
        .all()
    )
    assert len(corrected) == 1
    assert corrected[0].verification_status == "verified"
    assert corrected[0].normalized_value == "105"

    for fact in facts:
        if fact["fact_id"] != value["fact_id"]:
            assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    assert _document_row(db, document_id).extraction_status == "verified"
    open_types = _open_issue_types(db, document_id)
    assert "VI-002" not in open_types
    assert "VI-005" not in open_types
    observations = _document_observations(db, document_id)
    assert len(observations) == 1
    assert observations[0].value == 105.0


def test_g2_immutable_rejection_history(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """G2: a rejection is append-only and the history row is never rewritten."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    facts = _facts(api, doctor_headers, document_id)
    value = _fact_by_field(facts, "value")

    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])
    assert (
        _verify(
            api,
            doctor_headers,
            document_id,
            value["fact_id"],
            decision="rejected",
        ).status_code
        == 200
    )

    rows = (
        db.execute(select(FactVerification).where(FactVerification.fact_id == value["fact_id"]))
        .scalars()
        .all()
    )
    assert len(rows) == 1

    for decision, body in (
        ("verified", {}),
        ("corrected", {"corrected_value": "105", "corrected_unit": "mg/dL"}),
    ):
        response = _verify(
            api,
            doctor_headers,
            document_id,
            value["fact_id"],
            decision=decision,
            **body,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "E_FACT_ALREADY_DECIDED"

    fact = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == value["fact_id"])
    ).scalar_one()
    assert fact.verification_status == "rejected"


def test_g3_identity_blocker_precedence(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """G3: an identity blocker is answered before any decision.

    This is the precondition the ``recovery_of`` rule rests on: because
    ``record_decision`` refuses every decision while ``VI-004`` is open, a
    ``VI-004`` document can never accumulate rejections, so it can never reach a
    recoverable terminal state and never becomes a recovery source. That
    consequence is asserted in R6, which is RED.
    """
    document_id = _accepted(api, patient_headers, report_b_pdf, filename="wrong_patient.pdf")
    facts = _facts(api, doctor_headers, document_id)

    assert "VI-004" in _open_issue_types(db, document_id)
    response = _verify(api, doctor_headers, document_id, facts[0]["fact_id"])
    assert response.status_code == 409
    assert response.json()["code"] == "E_VI_004_UNRESOLVED"


def test_g4_no_observation_from_a_rejected_fact(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """G4: no observation may cite a rejected fact."""
    # reject the value
    value_id = _accepted(api, patient_headers, glucose_pdf)
    value_facts = _facts(api, doctor_headers, value_id)
    for fact in value_facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, value_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        value_id,
        _fact_by_field(value_facts, "value")["fact_id"],
        decision="rejected",
    )

    # reject a non-measurement fact
    reference_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="105", date="2026-11-03"),
        filename="reference.pdf",
    )
    reference_facts = _facts(api, doctor_headers, reference_id)
    for fact in reference_facts:
        if fact["field_name"] != "reference_text":
            _verify(api, doctor_headers, reference_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        reference_id,
        _fact_by_field(reference_facts, "reference_text")["fact_id"],
        decision="rejected",
    )

    for document_id in (value_id, reference_id):
        rejected_ids = {
            row.id
            for row in db.execute(
                select(ExtractedFact).where(
                    ExtractedFact.document_id == document_id,
                    ExtractedFact.verification_status == "rejected",
                )
            ).scalars()
        }
        assert rejected_ids
        assert [
            row
            for row in db.execute(select(Observation)).scalars()
            if row.source_fact_id in rejected_ids
        ] == []


def test_g5_vi002_preserved(
    api, patient_headers, doctor_headers, glucose_pdf, fixtures, db: Session
):
    """G5: a plain rejection still counts for ``VI-002`` (D-14)."""
    # reject the value
    value_id = _accepted(api, patient_headers, glucose_pdf)
    value_facts = _facts(api, doctor_headers, value_id)
    for fact in value_facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, value_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        value_id,
        _fact_by_field(value_facts, "value")["fact_id"],
        decision="rejected",
    )

    # reject a non-measurement fact
    reference_id = _accepted(
        api,
        patient_headers,
        _glucose_pdf(fixtures, value="105", date="2026-11-03"),
        filename="reference.pdf",
    )
    reference_facts = _facts(api, doctor_headers, reference_id)
    for fact in reference_facts:
        if fact["field_name"] != "reference_text":
            _verify(api, doctor_headers, reference_id, fact["fact_id"])
    _verify(
        api,
        doctor_headers,
        reference_id,
        _fact_by_field(reference_facts, "reference_text")["fact_id"],
        decision="rejected",
    )

    for document_id in (value_id, reference_id):
        open_vi002 = [
            row
            for row in _issue_rows(db, document_id)
            if row.issue_type == "VI-002" and row.state == "open"
        ]
        assert open_vi002, "a plain rejection must keep VI-002 open"
        assert open_vi002[0].reason_code == "fact_unverified"


def test_g6_all_rejected_unchanged(api, patient_headers, doctor_headers, glucose_pdf, db: Session):
    """G6: rejecting every fact keeps the existing ``all_facts_rejected`` code."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    facts = _facts(api, doctor_headers, document_id)

    response = None
    for fact in facts:
        response = _verify(
            api,
            doctor_headers,
            document_id,
            fact["fact_id"],
            decision="rejected",
        )
    assert response is not None
    assert response.status_code == 200
    assert response.json()["document_status"] == "failed"

    document = _document_row(db, document_id)
    assert document.extraction_status == "failed"
    assert document.failure_code == ALL_FACTS_REJECTED


def test_g7_document_only_report_unaffected(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """G7: a report with no measurement still reaches ``verified``."""
    payload = _document_only_pdf(fixtures)
    document_id = _accepted(api, patient_headers, payload, filename="document_only.pdf")
    facts = _facts(api, doctor_headers, document_id)

    assert [fact["field_name"] for fact in facts] == ["report_date", "reference_text"]
    for fact in facts:
        assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    assert _document_row(db, document_id).extraction_status == "verified"
    assert "VI-002" not in _open_issue_types(db, document_id)


def test_g8_duplicate_upload_with_and_without_recovery_of(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """G8: identical bytes stay a duplicate, with or without a recovery link."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    _reject_value(api, doctor_headers, document_id)

    before = _document_count(db)
    for data in (None, {"recovery_of": document_id}):
        response = _upload(
            api,
            patient_headers,
            glucose_pdf,
            filename="duplicate.pdf",
            data=data,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "E_DUPLICATE_DOCUMENT"
    assert _document_count(db) == before


__all__ = [
    "ALL_FACTS_REJECTED",
    "EVENT_DOCUMENT_RECOVERED",
    "FACT_REJECTED",
    "MEASUREMENT_REJECTED",
    "P3_REVISION",
    "R21_REVISION",
]
