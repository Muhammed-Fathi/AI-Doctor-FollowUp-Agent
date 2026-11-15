"""Doctor verification, append-only decisions and the closed mapping.

Covers ``REQ-VERIFY-02``, ``REQ-VERIFY-03``, ``MAP-01`` and owner decisions
D-07/D-11/D-12/D-13. The single most important assertions here are:

* a second decision on a fact is refused **even when identical** (D-11);
* the only path to a ``doctor_verified`` observation is a doctor decision;
* the mapping is literal — an unmapped name or a wrong unit promotes nothing;
* ``measured_at`` comes from the report date, never from the wall clock;
* the database trigger refuses a non-doctor verifier independently of the service.

The trigger test deliberately bypasses the service layer and writes with raw SQL,
because a test that goes through ``record_decision`` would only prove that Python
checks the role — it would not prove the database does.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.models import ExtractedFact, FactVerification, Observation
from app.services.documents.mapping import (
    MappingDecision,
    VerifiedFactView,
    decide_mapping,
    mapping_version_is_valid,
    measured_at_for,
    normalize_test_name,
    resolve_alias,
)


def _upload(client, headers, payload, *, filename="report.pdf"):
    """Upload ``payload`` and return the document id."""
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (filename, payload, "application/pdf")},
    )
    assert response.status_code == 202, response.text
    return response.json()["document_id"]


def _facts(client, headers, document_id) -> list[dict]:
    """Return the doctor view of a document's candidate facts."""
    response = client.get(f"/api/v1/documents/{document_id}/extraction", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["facts"]


def _value_fact(facts: list[dict]) -> dict:
    """Return the ``value`` field of a report."""
    return next(fact for fact in facts if fact["field_name"] == "value")


def _verify(client, headers, document_id, fact_id, **body) -> object:
    """POST one verification decision."""
    payload = {"fact_id": fact_id, "decision": "verified", **body}
    return client.post(f"/api/v1/documents/{document_id}/verify", headers=headers, json=payload)


# --- the decision is append-only (D-11) -------------------------------------


def test_first_verification_is_recorded_and_returns_the_fact(
    api, patient_headers, doctor_headers, report_b_pdf
):
    """``200`` with the updated fact, the decision and the document status."""
    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    response = _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert response.status_code == 200
    body = response.json()
    assert body["verification"]["decision"] == "verified"
    assert body["verification"]["verified_by"]
    assert body["fact"]["verification_status"] == "verified"


def test_identical_repeat_decision_is_refused_with_409(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """D-11: an identical repeat is ``409 E_FACT_ALREADY_DECIDED``, never a silent ``200``.

    This is the deliberate deviation from ``API_CONTRACT.md`` §1's
    ``Idempotency-Key`` convention. The test also asserts that only **one**
    ``fact_verification`` row exists afterwards, so "refused" cannot mean
    "recorded twice".
    """
    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    first = _verify(api, doctor_headers, document_id, fact["fact_id"])
    second = _verify(api, doctor_headers, document_id, fact["fact_id"])

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "E_FACT_ALREADY_DECIDED"

    rows = list(
        db.execute(
            select(FactVerification).where(FactVerification.fact_id == fact["fact_id"])
        ).scalars()
    )
    assert len(rows) == 1


def test_conflicting_second_decision_is_also_refused(
    api, patient_headers, doctor_headers, report_b_pdf
):
    """Verify-then-reject is refused too: the first decision stands."""
    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200
    response = _verify(
        api,
        doctor_headers,
        document_id,
        fact["fact_id"],
        decision="rejected",
        reason="changed mind",
    )

    assert response.status_code == 409
    assert response.json()["code"] == "E_FACT_ALREADY_DECIDED"


def test_correction_requires_a_replacement_value(
    api, patient_headers, doctor_headers, ambiguous_pdf
):
    """``corrected`` with no value is ``400 E_VALIDATION``, not a hidden rejection."""
    document_id = _upload(api, patient_headers, ambiguous_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    response = _verify(api, doctor_headers, document_id, fact["fact_id"], decision="corrected")

    assert response.status_code == 400
    assert response.json()["code"] == "E_VALIDATION"


def test_correction_supersedes_the_original_fact(
    api, patient_headers, doctor_headers, ambiguous_pdf, db: Session
):
    """A correction writes the new value and marks the original ``rejected``."""
    document_id = _upload(api, patient_headers, ambiguous_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    response = _verify(
        api,
        doctor_headers,
        document_id,
        fact["fact_id"],
        decision="corrected",
        corrected_value="105",
        corrected_unit="mg/dL",
    )

    assert response.status_code == 200
    original = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == fact["fact_id"])
    ).scalar_one()
    assert original.verification_status == "rejected"

    created = list(
        db.execute(
            select(ExtractedFact).where(
                ExtractedFact.document_id == document_id,
                ExtractedFact.verification_status == "verified",
            )
        ).scalars()
    )
    assert [row.normalized_value for row in created if row.field_name == "value"] == ["105"]


def test_fact_from_another_document_is_not_found(
    api, patient_headers, doctor_headers, report_b_pdf, ambiguous_pdf
):
    """A fact id belonging to a different document answers the neutral ``404``."""
    first = _upload(api, patient_headers, report_b_pdf)
    second = _upload(api, patient_headers, ambiguous_pdf, filename="b.pdf")
    foreign_fact = _value_fact(_facts(api, doctor_headers, second))

    response = _verify(api, doctor_headers, first, foreign_fact["fact_id"])

    assert response.status_code == 404
    assert response.json()["code"] == "E_NOT_FOUND"


def test_all_facts_verified_promotes_the_document(
    api, patient_headers, doctor_headers, report_b_pdf
):
    """``verified`` at document level requires every blocking fact decided."""
    document_id = _upload(api, patient_headers, report_b_pdf)
    facts = _facts(api, doctor_headers, document_id)

    for index, fact in enumerate(facts):
        response = _verify(api, doctor_headers, document_id, fact["fact_id"])
        assert response.status_code == 200
        expected = "verified" if index == len(facts) - 1 else "needs_verification"
        assert response.json()["document_status"] == expected


def test_document_with_every_fact_rejected_fails(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """All-rejected is ``failed``, never ``verified``."""
    document_id = _upload(api, patient_headers, report_b_pdf)
    facts = _facts(api, doctor_headers, document_id)

    response = None
    for fact in facts:
        response = _verify(api, doctor_headers, document_id, fact["fact_id"], decision="rejected")
    assert response is not None

    assert response.status_code == 200
    assert response.json()["document_status"] == "failed"
    document = db.execute(
        select(ExtractedFact).where(ExtractedFact.document_id == document_id)
    ).scalars()
    assert all(row.verification_status == "rejected" for row in document)


# --- the mapping (MAP-01) ----------------------------------------------------


def _views(
    report_date: str | None,
    name: str | None,
    value: str | None,
    unit: str | None,
    status="verified",
):
    """Build the mapping view for one lab line."""
    return [
        VerifiedFactView("report_date", report_date, None, status),
        VerifiedFactView("test_name", name, None, status),
        VerifiedFactView("value", value, unit, status),
        VerifiedFactView("unit", unit, unit, status),
    ]


def test_case_b_glucose_is_mapped_with_the_report_date():
    """Case B: ``glucose 104 mg/dL`` maps, and ``measured_at`` is the report date."""
    decision = decide_mapping(_views("2026-11-02", "Fasting glucose", "104", "mg/dL"))

    assert decision.is_mapped
    assert decision.mapped is not None
    assert decision.mapped.measure_type.value == "glucose"
    assert decision.mapped.value == 104.0
    assert decision.mapped.unit == "mg/dL"
    assert decision.mapped.measured_at == "2026-11-02T00:00:00Z"


def test_case_a_hemoglobin_is_not_mapped():
    """Case A: a correct reading whose name is outside the table stays document-only."""
    decision = decide_mapping(_views("2026-10-20", "Hemoglobin", "13.4", "g/dL"))

    assert not decision.is_mapped
    assert decision.reason == "unmapped_test_name"


def test_multi_measurement_document_is_not_mapped():
    """``GOLD-NEG-10``: two measurements mean no measurement is promoted."""
    facts = _views("2026-10-21", "Hemoglobin", "13.4", "g/dL") + _views(
        "2026-10-21", "Fasting glucose", "104", "mg/dL"
    )
    decision = decide_mapping(facts)

    assert not decision.is_mapped
    assert decision.reason == "multi_measurement_document"
    assert decision.candidate_count == 2


def test_pending_fact_blocks_the_mapping():
    """An undecided fact is invisible to the mapping, so nothing is promoted."""
    decision = decide_mapping(_views("2026-11-02", "Glucose", "104", "mg/dL", status="pending"))

    assert not decision.is_mapped


def test_unit_must_match_the_table_entry():
    """``Glucose 104 mmol/L`` is refused: no unit conversion exists in the MVP."""
    decision = decide_mapping(_views("2026-11-02", "Glucose", "104", "mmol/L"))

    assert not decision.is_mapped


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Glucose", "glucose"),
        ("  Fasting   Glucose ", "fasting glucose"),
        ("Hemoglobin A1c:", "hemoglobin a1c"),
        ("Glucosex", "glucosex"),
    ],
)
def test_alias_normalisation_is_literal(raw: str, expected: str):
    """Lowercase, collapse whitespace, strip a trailing colon. Nothing else."""
    assert normalize_test_name(raw) == expected


def test_alias_lookup_does_not_fuzzy_match():
    """An unknown name resolves to ``None``; a near miss is still a miss.

    ``blood glucose`` *is* a table alias, so it resolves. ``Glucosex`` and
    ``glucose fasting`` are not, and neither is silently coerced.
    """
    assert resolve_alias("Blood glucose") is not None
    assert resolve_alias(" glucose ") is not None
    assert resolve_alias("Glucosex") is None
    assert resolve_alias("glucose fasting") is None
    assert resolve_alias("Glucose (fasting)") is None
    assert resolve_alias("") is None


def test_aliases_map_only_to_their_declared_measure_and_unit():
    """Each alias carries its own required unit, not a global default."""
    glucose = resolve_alias("fasting glucose")
    heart = resolve_alias("pulse")
    bp = resolve_alias("sbp")

    assert glucose is not None and glucose[1].value == "mg/dL"
    assert heart is not None and heart[1].value == "bpm"
    assert bp is not None and bp[1].value == "mmHg"


def test_mapping_version_shape():
    """The version is ``map-<major>.<minor>.<patch>``; a bare semver is not."""
    assert mapping_version_is_valid("map-1.0.0")
    assert not mapping_version_is_valid("1.0.0")
    assert not mapping_version_is_valid("map-1.0")


def test_measured_at_rejects_an_ambiguous_date():
    """An ambiguous date yields no timestamp rather than a guess."""
    assert measured_at_for("2026-11-02") == "2026-11-02T00:00:00Z"
    assert measured_at_for("03/11/2026") is None
    assert measured_at_for(None) is None


# --- end-to-end promotion ----------------------------------------------------


def test_verified_glucose_produces_one_observation_with_report_date(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """The full path: upload, decide every fact, observe the derived row.

    Asserts the provenance class and the timestamp origin, because those are the
    two facts a reviewer cannot infer from the response body alone.
    """
    document_id = _upload(api, patient_headers, report_b_pdf)
    facts = _facts(api, doctor_headers, document_id)
    for fact in facts:
        assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    created = list(
        db.execute(select(Observation).where(Observation.source == "verified_document")).scalars()
    )
    assert len(created) == 1
    observation = created[0]
    assert observation.measure_type == "glucose"
    assert observation.value == 104.0
    assert observation.unit == "mg/dL"
    # The report date, not the frozen demo clock.
    assert observation.measured_at == "2026-11-02T00:00:00Z"
    assert observation.trust_level == "doctor_verified"
    assert observation.verified_by_user_id
    assert observation.source_fact_id


def test_hemoglobin_document_produces_no_observation(
    api, patient_headers, doctor_headers, report_a_pdf, db: Session
):
    """Case A: verified facts, but nothing promoted — no comparison is possible."""
    document_id = _upload(api, patient_headers, report_a_pdf)
    facts = _facts(api, doctor_headers, document_id)
    for fact in facts:
        assert _verify(api, doctor_headers, document_id, fact["fact_id"]).status_code == 200

    created = list(
        db.execute(select(Observation).where(Observation.source == "verified_document")).scalars()
    )
    assert created == []


def test_no_observation_exists_before_a_decision(api, patient_headers, report_b_pdf, db: Session):
    """Uploading and extracting promotes nothing on its own."""
    _upload(api, patient_headers, report_b_pdf)

    created = list(
        db.execute(select(Observation).where(Observation.source == "verified_document")).scalars()
    )
    assert created == []


# --- the database trigger (D-07) --------------------------------------------


def _insert_verification_raw(db: Session, *, fact_id: str, user_id: str) -> None:
    """Insert a ``fact_verification`` row with raw SQL, bypassing the service."""
    db.execute(
        text(
            "INSERT INTO fact_verification "
            "(id, fact_id, decision, verified_by_user_id, decided_at) "
            "VALUES (:id, :fact_id, 'verified', :user_id, '2026-11-14T12:00:00Z')"
        ),
        {"id": "11111111-2222-4333-8444-555555555555", "fact_id": fact_id, "user_id": user_id},
    )


def test_trigger_rejects_a_non_doctor_verifier(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """Even with the service bypassed, SQLite refuses a patient as verifier.

    This is the D-07 requirement: the role rule must hold in the database, not only
    in Python. A patient's user id is looked up from the seeded account rather than
    invented, so the row would otherwise be structurally valid.
    """
    from app.db.models import User

    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))
    patient = db.execute(select(User).where(User.username == "demo_patient_a")).scalar_one()

    with pytest.raises(IntegrityError) as caught:
        _insert_verification_raw(db, fact_id=fact["fact_id"], user_id=patient.id)
    db.rollback()

    assert "doctor" in str(caught.value).lower()


def test_trigger_rejects_an_unknown_verifier(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """A nonexistent user id fails the ``IS NOT 'doctor'`` comparison too.

    This is why the trigger uses ``IS NOT`` rather than ``<>``: a missing role is
    ``NULL``, and ``NULL <> 'doctor'`` would be ``NULL`` (not true), silently
    admitting the row.
    """
    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))

    with pytest.raises(IntegrityError):
        _insert_verification_raw(
            db, fact_id=fact["fact_id"], user_id="99999999-9999-4999-8999-999999999999"
        )
    db.rollback()


def test_trigger_allows_a_doctor_verifier(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """The same raw insert succeeds for a doctor, proving the trigger is not vacuous."""
    from app.db.models import User

    document_id = _upload(api, patient_headers, report_b_pdf)
    fact = _value_fact(_facts(api, doctor_headers, document_id))
    doctor = db.execute(select(User).where(User.username == "demo_doctor")).scalar_one()

    _insert_verification_raw(db, fact_id=fact["fact_id"], user_id=doctor.id)

    stored = db.execute(
        select(FactVerification).where(FactVerification.fact_id == fact["fact_id"])
    ).scalar_one()
    assert stored.verified_by_user_id == doctor.id


# --- service-level guards ----------------------------------------------------


def test_service_refuses_a_second_decision_directly(
    api, patient_headers, doctor_headers, report_b_pdf, db: Session
):
    """The service enforces append-only itself, not only via the route.

    Driven through HTTP for the *setup* (so a real fact and a real decision exist),
    then calling :func:`record_decision` again directly. The 409 is therefore
    attributable to the service guard rather than to the endpoint's own pre-check.
    """
    from app.core.enums import VerificationDecision
    from app.services.documents.verification import record_decision

    document_id = _upload(api, patient_headers, report_b_pdf)
    fact_payload = _value_fact(_facts(api, doctor_headers, document_id))
    assert _verify(api, doctor_headers, document_id, fact_payload["fact_id"]).status_code == 200

    fact = db.execute(
        select(ExtractedFact).where(ExtractedFact.id == fact_payload["fact_id"])
    ).scalar_one()

    with pytest.raises(ApiError) as caught:
        record_decision(
            db,
            document=None,  # type: ignore[arg-type]
            fact=fact,
            decision=VerificationDecision.VERIFIED,
            doctor_user_id="irrelevant-because-it-is-refused-first",
        )

    assert caught.value.code is ErrorCode.FACT_ALREADY_DECIDED
    assert caught.value.status_code == 409


def test_mapping_decision_is_immutable():
    """A decision is a frozen value; a caller cannot mutate it after the fact."""
    from dataclasses import FrozenInstanceError

    decision = MappingDecision(mapped=None, reason="unmapped_test_name", candidate_count=1)

    with pytest.raises(FrozenInstanceError):
        decision.reason = "tampered"  # type: ignore[misc]
