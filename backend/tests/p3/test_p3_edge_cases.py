"""Regression tests for the final pre-Windows review findings (P3-R06..P3-R08).

Every test in this module was written **before** its fix and executed against the
reviewed head ``b4f761f170a199e9bee784332b612d5fabdb4b86``. They exist because the
earlier suite tested each piece in isolation:

* **R06** — the single-measurement anchor counted every ``value`` fact with a
  non-null ``normalized_value`` *regardless of status*. Correcting an **already
  parseable** value leaves two such facts (the rejected original and the new
  verified row), so the anchor became ambiguous and a valid document silently
  produced **no** observation. The R05 tests missed it because ``1O5`` has a NULL
  ``normalized_value``, which hides the second row.
* **R07** — the parser kept the **first** printed patient reference and ignored
  any later, different one. A document printing ``DEMO-A-001`` then
  ``DEMO-B-001`` uploaded by A therefore looked consistent.
* **R08** — the upload handler called an unbounded ``file.file.read()``, so the
  whole payload was materialized before the 10 MiB cap was consulted.

The secondary point (no database-level uniqueness on
``verification_issue (document_id, issue_type)``) is covered at the end.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.models import (
    Document,
    ExtractedFact,
    FactVerification,
    Observation,
    VerificationIssue,
)

UPLOAD = "/api/v1/documents/upload"
PATIENT_A_REF = "DEMO-A-001"
PATIENT_B_REF = "DEMO-B-001"


# --- helpers -----------------------------------------------------------------


def _upload(client, headers, payload: bytes, *, filename="report.pdf", mime="application/pdf"):
    """POST one upload and return the raw response (status under test)."""
    return client.post(UPLOAD, headers=headers, files={"file": (filename, payload, mime)})


def _accepted(client, headers, payload: bytes, *, filename="report.pdf", mime="application/pdf"):
    """Upload expecting ``202`` and return the document id."""
    response = _upload(client, headers, payload, filename=filename, mime=mime)
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def _extraction(client, headers, document_id: str) -> dict:
    """Return the doctor's extraction view."""
    response = client.get(f"/api/v1/documents/{document_id}/extraction", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _issues(body: dict) -> dict[str, dict]:
    """Index the response's verification issues by type."""
    return {issue["issue_type"]: issue for issue in body["verification_issues"]}


def _verify(client, headers, document_id, fact_id, **body):
    """POST one verification decision."""
    return client.post(
        f"/api/v1/documents/{document_id}/verify",
        headers=headers,
        json={"fact_id": fact_id, "decision": "verified", **body},
    )


def _value_fact(facts: list[dict]) -> dict:
    """Return the ``value`` field of a report."""
    return next(fact for fact in facts if fact["field_name"] == "value")


def _document_observations(db: Session, document_id: str) -> list[Observation]:
    """Return the observations derived from ``document_id``."""
    fact_ids = [
        row.id
        for row in db.execute(
            select(ExtractedFact).where(ExtractedFact.document_id == document_id)
        ).scalars()
    ]
    return [
        row for row in db.execute(select(Observation)).scalars() if row.source_fact_id in fact_ids
    ]


def _clear_glucose(db: Session) -> None:
    """Remove seeded glucose observations so expectations are unambiguous."""
    for row in db.execute(
        select(Observation).where(Observation.measure_type == "glucose")
    ).scalars():
        db.delete(row)
    db.commit()


def _report_pdf(fixtures, lines: list[str]) -> bytes:
    """Build a one-page synthetic report from explicit lines.

    Used instead of a committed source where the *defect* is the shape of the
    document (two different patient references, an unparseable value). The
    content is still entirely synthetic and generated deterministically.
    """
    return fixtures.build_pdf([lines])


def _glucose_report(
    ref: str = PATIENT_A_REF, *, value: str = "104", date="2026-11-02"
) -> list[str]:
    """Return the lines of a one-measurement synthetic glucose report."""
    return [
        "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD",
        f"Demo Patient A            Ref: {ref}            Report date: {date}",
        f"Test: Fasting glucose     Value: {value} mg/dL",
        "Reference range: 70 - 99 mg/dL",
    ]


# =============================================================================
# P3-R06 — correcting a parseable value must not break the measurement anchor
# =============================================================================


def test_p3_r06_correcting_a_parseable_value_still_maps_one_observation(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R06: ``104`` corrected to ``105`` must still produce exactly one observation.

    The rejected original keeps ``normalized_value='104'``. Before the fix the
    anchor query counted it, saw two rows, returned ``None`` and promotion was
    skipped — a fully verified, mapped document silently produced nothing.
    """
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)

    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)
    assert value_fact["normalized_value"] == "104", "this case needs a parseable source value"

    response = _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
        reason="transcription error",
    )
    assert response.status_code == 200, response.text

    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    document = db.execute(select(Document).where(Document.id == document_id)).scalar_one()
    assert document.extraction_status == "verified", (
        "a fully decided, mapped document must reach verified after a correction"
    )

    created = _document_observations(db, document_id)
    assert len(created) == 1, "P0-R14: exactly one observation per document"
    assert created[0].value == 105.0, "the corrected value is the one that is mapped"
    assert created[0].measured_at.startswith("2026-11-02")


def test_p3_r06_superseded_original_is_not_the_anchor(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R06: the observation hangs off the **verified** row, never the rejected one."""
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)

    _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )
    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    created = _document_observations(db, document_id)
    assert len(created) == 1
    owner = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == created[0].source_fact_id)
    ).scalar_one()
    assert owner.id != value_fact["fact_id"], "the superseded fact must not own the observation"
    assert owner.verification_status == "verified"
    assert owner.corrected_from_fact_id == value_fact["fact_id"], "lineage is preserved"


def test_p3_r06_corrected_parseable_value_still_conflicts_with_existing_record(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R06: a same-day ``98`` must still raise ``VI-006`` and block promotion.

    Before the fix, the rejected original and the corrected row together looked
    like two measurement tuples, so ``decide_mapping`` reported the document as
    multi-measurement and the conflict silently disappeared — the worst possible
    outcome: no warning *and* no promotion, for the wrong reason.
    """
    _clear_glucose(db)
    db.add(
        Observation(
            patient_id="11111111-1111-4111-8111-111111111111",
            measure_type="glucose",
            value=98.0,
            unit="mg/dL",
            measured_at="2026-11-02T00:00:00Z",
            source="patient_checkin",
            validation="ok",
            trust_level="self_reported_validated",
            created_at="2026-11-02T08:00:00Z",
        )
    )
    db.commit()

    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)

    response = _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )
    assert response.status_code == 200, response.text

    body = _extraction(api, doctor_headers, document_id)
    assert "VI-006" in _issues(body), "98 vs 105 on the same day is still a conflict"

    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert _document_observations(db, document_id) == [], (
        "a conflicting document must not create a comparable observation"
    )


def test_p3_r06_corrected_match_is_not_a_conflict(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """Control: correcting to the *stored* value is agreement, not conflict."""
    _clear_glucose(db)
    db.add(
        Observation(
            patient_id="11111111-1111-4111-8111-111111111111",
            measure_type="glucose",
            value=105.0,
            unit="mg/dL",
            measured_at="2026-11-02T00:00:00Z",
            source="patient_checkin",
            validation="ok",
            trust_level="self_reported_validated",
            created_at="2026-11-02T08:00:00Z",
        )
    )
    db.commit()

    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)

    _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )
    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert "VI-006" not in _issues(_extraction(api, doctor_headers, document_id))
    created = _document_observations(db, document_id)
    assert len(created) == 1, "an agreeing correction still promotes"
    assert created[0].value == 105.0


# =============================================================================
# P3-R07 — conflicting printed references inside one document fail closed
# =============================================================================


@pytest.mark.parametrize(
    ("first_ref", "second_ref", "label"),
    [
        (PATIENT_A_REF, PATIENT_B_REF, "A-then-B"),
        (PATIENT_B_REF, PATIENT_A_REF, "B-then-A"),
    ],
)
def test_p3_r07_two_distinct_references_raise_vi_004(
    api, patient_headers, doctor_headers, fixtures, db: Session, first_ref, second_ref, label
):
    """R07: a document that prints two different references cannot be attributed.

    Both orders must fail closed. Before the fix only the *first* reference was
    kept, so ``A then B`` looked like a clean patient-A document.
    """
    lines = _glucose_report(ref=first_ref)
    lines.insert(
        2, f"Demo Patient X            Ref: {second_ref}            Report date: 2026-11-02"
    )
    payload = _report_pdf(fixtures, lines)

    document_id = _accepted(api, patient_headers, payload)
    body = _extraction(api, doctor_headers, document_id)

    issues = _issues(body)
    assert "VI-004" in issues, f"{label}: two distinct references must raise VI-004"
    assert issues["VI-004"]["reason_code"] == "wrong_patient_document"

    stored = db.execute(select(Document).where(Document.id == document_id)).scalar_one()
    assert stored.document_patient_ref is None, (
        "an ambiguous identity must not be silently reduced to one of the references"
    )

    for fact in body["facts"]:
        response = _verify(api, doctor_headers, document_id, fact["fact_id"])
        assert response.status_code == 409, f"{label}: no decision may be recorded"
        assert response.json()["code"] == "E_VI_004_UNRESOLVED"

    assert _document_observations(db, document_id) == []
    assert list(db.execute(select(FactVerification)).scalars()) == []


def test_p3_r07_repeated_same_reference_is_accepted(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """Control: printing the *same* reference twice is not a conflict."""
    lines = _glucose_report(ref=PATIENT_A_REF)
    lines.insert(
        2, f"Demo Patient A            Ref: {PATIENT_A_REF}            Report date: 2026-11-02"
    )
    payload = _report_pdf(fixtures, lines)

    document_id = _accepted(api, patient_headers, payload)
    body = _extraction(api, doctor_headers, document_id)

    assert "VI-004" not in _issues(body)
    stored = db.execute(select(Document).where(Document.id == document_id)).scalar_one()
    assert stored.document_patient_ref == PATIENT_A_REF


def test_p3_r07_references_on_separate_pages_fail_closed(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R07: the check spans pages, not only lines within the first page."""
    first = _glucose_report(ref=PATIENT_A_REF)
    second = [
        "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD",
        f"Demo Patient B            Ref: {PATIENT_B_REF}            Report date: 2026-11-02",
        "Reference range: 70 - 99 mg/dL",
    ]
    payload = fixtures.build_pdf([first, second])

    document_id = _accepted(api, patient_headers, payload)
    body = _extraction(api, doctor_headers, document_id)

    assert "VI-004" in _issues(body), "a cross-page mismatch is the same identity conflict"
    stored = db.execute(select(Document).where(Document.id == document_id)).scalar_one()
    assert stored.document_patient_ref is None


def test_p3_r07_single_reference_control_still_maps(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """Control: one printed reference behaves exactly as before."""
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(ref=PATIENT_A_REF))
    document_id = _accepted(api, patient_headers, payload)

    body = _extraction(api, doctor_headers, document_id)
    assert "VI-004" not in _issues(body)

    for fact in body["facts"]:
        assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200
    assert len(_document_observations(db, document_id)) == 1


# =============================================================================
# P3-R08 — the byte cap must be enforced before the payload is materialized
# =============================================================================


class _SpyStream:
    """A file-like stream that records the size argument of every ``read``."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.calls: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.calls.append(size)
        if size is None or size < 0:
            return self._payload
        return self._payload[:size]


def test_p3_r08_bounded_read_never_requests_the_whole_stream():
    """R08: the upload path must not call ``read()`` without a bound.

    Asserted against the real helper the route uses, with an argument-recording
    stream. ``read()``/``read(-1)`` would buffer the entire part before any size
    check; a future edit back to the unbounded call fails here.
    """
    from app.api.v1.documents.upload import _read_bounded

    stream = _SpyStream(b"%PDF-1.4\n small body \n")
    payload = _read_bounded(stream, max_bytes=1024)

    assert payload.startswith(b"%PDF-1.4")
    assert stream.calls == [1025], f"expected one bounded read of cap+1, got {stream.calls}"


def test_p3_r08_bounded_read_refuses_before_returning_oversize_bytes():
    """R08: the refusal happens at the read, not after the bytes are handed on."""
    from app.api.v1.documents.upload import _read_bounded

    stream = _SpyStream(b"x" * 4096)

    with pytest.raises(ApiError) as caught:
        _read_bounded(stream, max_bytes=1024)

    assert caught.value.code is ErrorCode.FILE_TOO_LARGE
    assert caught.value.status_code == 413
    assert stream.calls == [1025], "only cap+1 bytes are ever requested"


def test_p3_r08_bounded_read_accepts_exactly_the_cap():
    """Boundary: ``cap`` bytes is accepted; ``cap + 1`` is refused."""
    from app.api.v1.documents.upload import _read_bounded

    exact = _SpyStream(b"y" * 1024)
    assert len(_read_bounded(exact, max_bytes=1024)) == 1024

    over = _SpyStream(b"y" * 1025)
    with pytest.raises(ApiError) as caught:
        _read_bounded(over, max_bytes=1024)
    assert caught.value.code is ErrorCode.FILE_TOO_LARGE
    assert caught.value.status_code == 413


def test_p3_r08_oversized_payload_is_rejected_with_413(api, patient_headers, db: Session, tmp_path):
    """R08: a payload past the cap is ``413`` and leaves nothing behind."""
    from app.core.config import Settings

    settings = Settings()
    payload = b"%PDF-1.4\n" + b"x" * (settings.max_upload_bytes + 1)

    response = _upload(api, patient_headers, payload)

    assert response.status_code == 413, response.text
    assert response.json()["code"] == ErrorCodeName.FILE_TOO_LARGE
    assert list(db.execute(select(Document)).scalars()) == [], "no document row"
    assert list(db.execute(select(ExtractedFact)).scalars()) == [], "no facts"
    upload_dir = tmp_path / "uploads"
    assert not upload_dir.exists() or not any(upload_dir.iterdir()), "no stored file"


def test_p3_r08_payload_exactly_at_the_cap_is_still_assessed(api, patient_headers, fixtures):
    """Boundary: exactly ``max_upload_bytes`` is *not* a 413.

    The cap is inclusive, so the rejection must trigger on ``cap + 1`` only. The
    body here is not a valid PDF, so it fails a later check — but never the size
    one, which is what this boundary asserts.
    """
    from app.core.config import Settings

    settings = Settings()
    payload = b"%PDF-1.4\n" + b"x" * (settings.max_upload_bytes - len(b"%PDF-1.4\n"))

    response = _upload(api, patient_headers, payload)

    assert response.status_code != 413, "the cap is inclusive; equality must pass the size check"
    assert response.json()["code"] != ErrorCodeName.FILE_TOO_LARGE


def test_p3_r08_bad_multipart_does_not_leak_a_document(api, patient_headers, db: Session):
    """R08: a request with no file part is a ``400``/``422`` and stores nothing."""
    response = api.post(UPLOAD, headers=patient_headers, data={"declared_type": "application/pdf"})

    assert response.status_code in {400, 422}, response.text
    assert list(db.execute(select(Document)).scalars()) == []


# =============================================================================
# Secondary — (document_id, issue_type) must be unique in the database
# =============================================================================


def test_vi_document_issue_type_is_unique_in_the_database(
    api, patient_headers, doctor_headers, glucose_pdf, db: Session
):
    """The lifecycle's identity key is enforced by the schema, not by hope.

    ``sync_issues`` treats ``(document_id, issue_type)`` as the identity, so two
    concurrent sessions that both see "no row" would otherwise insert two rows.
    The unique index makes the second writer fail instead of duplicating.

    The test writes with raw SQL so the *database* is what refuses the row, not an
    ORM-side identity map, and it uses a real document id so the failure can only
    come from the unique index — not from a foreign key.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    document_id = _accepted(api, patient_headers, glucose_pdf)
    _extraction(api, doctor_headers, document_id)

    def _insert(issue_id: str) -> None:
        db.execute(
            text(
                "INSERT INTO verification_issue (id, patient_id, document_id, issue_type, "
                "reason_code, blocking, message, state, created_at) VALUES "
                "(:id, :pid, :doc, 'VI-004', 'wrong_patient_document', 1, "
                "'A document may not belong to this patient; please confirm.', 'open', "
                "'2026-11-15T12:00:00Z')"
            ),
            {"id": issue_id, "pid": "11111111-1111-4111-8111-111111111111", "doc": document_id},
        )

    _insert("issue-first")
    db.flush()
    with pytest.raises(IntegrityError):
        _insert("issue-second")
        db.flush()
    db.rollback()


def test_vi_document_type_index_is_declared_unique():
    """Guard the migration/model pair at the metadata level."""
    from app.db.models import VerificationIssue

    unique = {
        index.name
        for index in VerificationIssue.__table__.indexes
        if index.unique and [c.name for c in index.columns] == ["document_id", "issue_type"]
    }
    assert unique == {"ux_vi_document_type"}


def test_issue_sync_is_idempotent_across_two_sessions(
    api, patient_headers, doctor_headers, db: Session, glucose_pdf
):
    """Control: a normal re-read does not try to insert a second row."""
    document_id = _accepted(api, patient_headers, glucose_pdf)
    for _ in range(3):
        _extraction(api, doctor_headers, document_id)

    rows = list(
        db.execute(
            select(VerificationIssue).where(VerificationIssue.document_id == document_id)
        ).scalars()
    )
    by_type = [row.issue_type for row in rows]
    assert len(by_type) == len(set(by_type)), "one row per issue type per document"


class ErrorCodeName:
    """Error-code values used by the R08 assertions.

    Declared as plain strings so the test file does not import the application's
    error module merely to name two constants.
    """

    FILE_TOO_LARGE = "E_FILE_TOO_LARGE"


def _json(value: object) -> str:  # pragma: no cover - helper kept for debugging
    """Pretty-print a response body while debugging a failure."""
    return json.dumps(value, indent=2, sort_keys=True)


# =============================================================================
# P3-R09 — a superseded historical version is not a second measurement tuple
# =============================================================================


def test_p3_r09_corrected_single_measurement_has_no_false_multi_measurement_blocker(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R09: ``104 -> 105`` on a one-test report must not raise multi-measurement.

    The correction keeps the rejected original (``value=104``) beside the verified
    correction (``value=105``). R06 fixed the *mapping* to read only the active
    fact; ``_structural_measurement_count`` still counted both versions, so a
    document that describes **one** measurement was reported as describing two and
    a false ``VI-002 / multi_measurement_document`` was persisted as OPEN — on a
    document that had just mapped correctly.
    """
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)

    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)
    assert value_fact["normalized_value"] == "104"

    corrected = _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
        reason="transcription error",
    )
    assert corrected.status_code == 200, corrected.text

    for fact in facts:
        if fact["field_name"] != "value":
            assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    body = _extraction(api, doctor_headers, document_id)

    multi = [
        issue
        for issue in body["verification_issues"]
        if issue["reason_code"] == "multi_measurement_document"
    ]
    assert multi == [], (
        "a corrected one-test report is still one measurement; a superseded "
        f"historical version must not be counted as a second tuple: {multi}"
    )

    # The document really did map: this is not "blocked for a different reason".
    document = db.execute(select(Document).where(Document.id == document_id)).scalar_one()
    assert document.extraction_status == "verified"
    observation = _document_observations(db, document_id)
    assert len(observation) == 1 and observation[0].value == 105.0

    # And the persisted row agrees with the wire: the blocker is not left OPEN.
    rows = list(
        db.execute(
            select(VerificationIssue).where(
                VerificationIssue.document_id == document_id,
                VerificationIssue.issue_type == "VI-002",
            )
        ).scalars()
    )
    stale = [row for row in rows if row.state == "open"]
    assert stale == [], (
        "no stale VI-002 may remain OPEN after every fact is decided and the "
        f"document mapped: {[(r.reason_code, r.state) for r in rows]}"
    )


def test_p3_r09_generic_vi_002_is_not_left_stale_after_a_correction(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R09: the identical check for the *generic* ``fact_unverified`` reason.

    The review asked explicitly whether the accepted generic ``VI-002`` rule
    leaves a stale issue behind. It does not: once every fact is decided — the
    rejected original included — nothing is ``pending``, so no open ``VI-002`` of
    either reason survives. This test makes that a guarantee rather than a
    coincidence of ordering.
    """
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)

    _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )
    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    body = _extraction(api, doctor_headers, document_id)
    assert [issue for issue in body["verification_issues"] if issue["issue_type"] == "VI-002"] == []

    rows = list(
        db.execute(
            select(VerificationIssue).where(VerificationIssue.document_id == document_id)
        ).scalars()
    )
    assert [row for row in rows if row.state == "open"] == []
    resolved = {row.issue_type for row in rows if row.state == "resolved"}
    assert "VI-002" in resolved, "the blocker was raised and then resolved in place"


def test_p3_r09_genuine_two_measurement_document_still_blocks(
    api, patient_headers, doctor_headers, multi_test_pdf, db: Session
):
    """Control (must not regress): two real tests still block and map nothing."""
    document_id = _accepted(api, patient_headers, multi_test_pdf)
    body = _extraction(api, doctor_headers, document_id)

    reasons = {issue["reason_code"] for issue in body["verification_issues"]}
    assert "multi_measurement_document" in reasons

    for fact in body["facts"]:
        _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert _document_observations(db, document_id) == [], (
        "a genuine two-measurement document must still map zero observations"
    )
    after = _extraction(api, doctor_headers, document_id)
    still = [
        issue
        for issue in after["verification_issues"]
        if issue["reason_code"] == "multi_measurement_document"
    ]
    assert still, "deciding the facts does not make a two-test document attributable"


def test_p3_r09_repeated_get_keeps_issue_identity_after_correction(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R09: the post-correction issue set is stable across repeated reads."""
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)

    _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )
    for fact in facts:
        if fact["field_name"] != "value":
            _verify(api, doctor_headers, document_id, fact["fact_id"])

    first = _extraction(api, doctor_headers, document_id)
    second = _extraction(api, doctor_headers, document_id)
    third = _extraction(api, doctor_headers, document_id)

    def key(body: dict) -> list[tuple[str, str, str]]:
        return [
            (issue["issue_type"], issue["issue_id"], issue["created_at"])
            for issue in body["verification_issues"]
        ]

    assert key(first) == key(second) == key(third)
    assert key(first) == [], "a fully decided, corrected single-test document has no open blocker"


def test_p3_r09_historical_version_is_retained_but_not_active(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """R09: the fix must not delete history to make the count agree.

    The rejected original keeps its immutable excerpt, span and extractor, and the
    corrected row keeps the lineage link. Only its *participation in the active
    tuple* changed.
    """
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]
    value_fact = _value_fact(facts)
    original_raw = value_fact["raw_text"]

    _verify(
        api,
        doctor_headers,
        document_id,
        value_fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )

    original = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == value_fact["fact_id"])
    ).scalar_one()
    assert original.verification_status == "rejected", "history is preserved, not rewritten"
    assert original.raw_text == original_raw
    assert original.normalized_value == "104", "the historical value stays exactly as extracted"

    corrected_rows = list(
        db.execute(
            select(ExtractedFact).where(ExtractedFact.corrected_from_fact_id == original.id)
        ).scalars()
    )
    assert len(corrected_rows) == 1
    assert corrected_rows[0].verification_status == "verified"
    assert corrected_rows[0].normalized_value == "105"


def test_p3_r09_plain_rejection_still_counts_for_vi_002(
    api, patient_headers, doctor_headers, fixtures, db: Session
):
    """Guardrail: only *superseded* history is excluded, not plain rejections.

    ``DEMO_REVIEW_RULES.md`` §4/§6.1 counts candidate facts whose status is not
    ``verified``. A doctor rejecting a current reading is a verdict about live
    data, and the generic ``VI-002`` must still report it. Narrowing the rule any
    further than "a correction replaced this row" would weaken the accepted
    contract, so this test pins the boundary.
    """
    _clear_glucose(db)
    payload = _report_pdf(fixtures, _glucose_report(value="104"))
    document_id = _accepted(api, patient_headers, payload)
    facts = _extraction(api, doctor_headers, document_id)["facts"]

    value_fact = _value_fact(facts)
    assert (
        _verify(
            api,
            doctor_headers,
            document_id,
            value_fact["fact_id"],
            decision="rejected",
            reason="not this patient's reading",
        ).status_code
        == 200
    )

    body = _extraction(api, doctor_headers, document_id)
    vi_002 = [issue for issue in body["verification_issues"] if issue["issue_type"] == "VI-002"]
    assert vi_002, "a rejected (not superseded) fact is still an open VI-002"
    assert vi_002[0]["reason_code"] == "fact_unverified"

    superseded = {
        row.id
        for row in db.execute(
            select(ExtractedFact).where(
                ExtractedFact.document_id == document_id,
                ExtractedFact.verification_status == "rejected",
            )
        ).scalars()
    }
    assert superseded, "the fact really is rejected"
    rows = list(
        db.execute(select(ExtractedFact).where(ExtractedFact.document_id == document_id)).scalars()
    )
    assert all(row.corrected_from_fact_id is None for row in rows), (
        "no correction happened, so nothing is superseded — the exclusion must not apply"
    )
