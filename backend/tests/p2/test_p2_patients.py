"""``NEG-02`` / ``AUD-01`` — doctor scope, timeline and observation series.

Requirement mapping: ``REQ-AUTH-02``, ``REQ-SEC-01``, ``REQ-DATA-01``,
``REQ-DATA-03``, ``REQ-AUDIT-01``, ``NEG-02`` (unassigned doctor denied),
``AUD-01`` (denied access leaves a safe audit row).

No HTTP is involved: these are the service functions the doctor routes will call.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from support import FIXED_NOW, PATIENT_A_ID, PATIENT_B_ID, PATIENT_C_ID

from app.core.clock import format_utc
from app.core.enums import MeasureType, ValidationState
from app.core.errors import ApiError, ErrorCode
from app.core.policies import Principal
from app.db.models import AuditEvent, Observation, new_uuid
from app.services.patients import (
    list_assigned_patients,
    list_patient_observations,
    patient_header,
    patient_timeline,
    validate_patient_id,
)

ROUTE_TIMELINE = "GET /api/v1/doctor/patients/{patient_id}/timeline"
REQUEST_ID = "33333333-3333-4333-8333-cccccccccccc"


def timeline_for(db: Session, principal: Principal, patient_id: str = PATIENT_A_ID):
    """Call the timeline service with the fixed clock."""
    return patient_timeline(
        db,
        principal=principal,
        patient_id=patient_id,
        route=ROUTE_TIMELINE,
        request_id=REQUEST_ID,
        now=FIXED_NOW,
    )


def test_assigned_doctor_sees_only_their_patients(
    seeded: Session, doctor_principal: Principal
) -> None:
    """US-01: the patient list is the assignment, not the whole table."""
    page = list_assigned_patients(seeded, principal=doctor_principal)

    assert [item.external_ref for item in page.items] == ["DEMO-A-001", "DEMO-B-001", "DEMO-C-001"]
    assert page.next_cursor is None
    assert all(item.data_source == "synthetic_fixture" for item in page.items)


def test_unassigned_doctor_sees_no_patients(
    seeded: Session, unassigned_doctor_principal: Principal
) -> None:
    """A doctor without assignments gets an empty page, not an error."""
    page = list_assigned_patients(seeded, principal=unassigned_doctor_principal)

    assert page.items == []


def test_patient_list_paginates(seeded: Session, doctor_principal: Principal) -> None:
    """Pagination returns disjoint pages in a stable order."""
    first = list_assigned_patients(seeded, principal=doctor_principal, limit=2)
    second = list_assigned_patients(
        seeded, principal=doctor_principal, limit=2, cursor=first.next_cursor
    )

    assert len(first.items) == 2
    assert first.next_cursor is not None
    assert len(second.items) == 1
    assert second.next_cursor is None
    assert {item.id for item in first.items}.isdisjoint({item.id for item in second.items})


def test_unassigned_doctor_is_denied_and_audited(
    seeded: Session, unassigned_doctor_principal: Principal
) -> None:
    """NEG-02 + AUD-01: 403 with an audit row that carries no patient data."""
    with pytest.raises(ApiError) as caught:
        timeline_for(seeded, unassigned_doctor_principal)
    seeded.commit()

    assert caught.value.status_code == 403
    assert caught.value.code is ErrorCode.SCOPE_VIOLATION
    assert "Demo Patient A" not in caught.value.detail

    event = (
        seeded.execute(select(AuditEvent).where(AuditEvent.event_type == "access.denied"))
        .scalars()
        .one()
    )
    assert event.actor_id == unassigned_doctor_principal.user_id
    assert event.outcome == "denied"
    assert event.patient_id == PATIENT_A_ID
    assert event.created_at == format_utc(FIXED_NOW)
    assert event.idempotency_key
    assert "reason=patient_not_assigned" in (event.safe_detail or "")
    assert "route=GET /api/v1/doctor/patients/{patient_id}/timeline" in (event.safe_detail or "")
    # No request payload, note, or measurement value may appear in the row.
    assert "121" not in (event.safe_detail or "")


def test_denial_audit_key_is_deterministic(
    seeded: Session, unassigned_doctor_principal: Principal
) -> None:
    """The audit idempotency key is derived from immutable request facts."""
    for _ in range(2):
        with pytest.raises(ApiError):
            timeline_for(seeded, unassigned_doctor_principal)
        seeded.commit()

    keys = (
        seeded.execute(
            select(AuditEvent.idempotency_key).where(AuditEvent.event_type == "access.denied")
        )
        .scalars()
        .all()
    )

    # Same actor, same route, same request id -> the unique key collides.
    assert len(keys) == 1


def test_assigned_doctor_reads_the_timeline(seeded: Session, doctor_principal: Principal) -> None:
    """US-07 groundwork: observations are returned newest-first with labels."""
    timeline = timeline_for(seeded, doctor_principal)

    assert timeline.patient_id == PATIENT_A_ID
    assert timeline.documents == []
    assert timeline.review_items == []
    assert timeline.tasks == []
    assert len(timeline.observations) == 6
    measured = [item.measured_at for item in timeline.observations]
    assert measured == sorted(measured, reverse=True)
    assert {item.trust_level.value for item in timeline.observations} == {"self_reported_validated"}


def test_unknown_patient_is_not_found(seeded: Session, doctor_principal: Principal) -> None:
    """A patient that does not exist is ``404`` and is not acknowledged."""
    with pytest.raises(ApiError) as caught:
        timeline_for(seeded, doctor_principal, patient_id="99999999-9999-4999-8999-999999999999")

    assert caught.value.status_code == 404
    assert caught.value.code is ErrorCode.NOT_FOUND


def test_malformed_patient_id_is_a_validation_error() -> None:
    """A non-UUID path parameter is a client error, not a server error."""
    with pytest.raises(ApiError) as caught:
        validate_patient_id("patient-a")

    assert caught.value.code is ErrorCode.VALIDATION


def test_patient_role_cannot_read_a_timeline(seeded: Session, patient_principal: Principal) -> None:
    """REQ-AUTH-02: a patient account has no doctor read capability."""
    with pytest.raises(ApiError) as caught:
        timeline_for(seeded, patient_principal)

    assert caught.value.code is ErrorCode.FORBIDDEN


def test_patient_header_reports_counts_without_future_phase_data(
    seeded: Session, doctor_principal: Principal
) -> None:
    """Counts are real for P2 data and zero for unimplemented phases."""
    header = patient_header(
        seeded,
        principal=doctor_principal,
        patient_id=PATIENT_A_ID,
        route="GET /api/v1/doctor/patients/{patient_id}",
        request_id=REQUEST_ID,
        now=FIXED_NOW,
    )

    assert header.observation_count == 6
    assert header.document_count == 0
    assert header.open_review_item_count == 0
    assert header.external_ref == "DEMO-A-001"


def test_observation_series_excludes_rejected_rows(
    seeded: Session, doctor_principal: Principal
) -> None:
    """REQ-DATA-04: a rejected row is retained but not admissible."""
    seeded.add(
        Observation(
            id=new_uuid(),
            patient_id=PATIENT_A_ID,
            encounter_id=None,
            measure_type="systolic_bp",
            value=400.0,
            unit="mmHg",
            measured_at=format_utc(FIXED_NOW - timedelta(days=3)),
            source="patient_checkin",
            validation=ValidationState.REJECTED.value,
            trust_level="self_reported_validated",
            verified_by_user_id=None,
            verified_at=None,
            note=None,
            created_at=format_utc(FIXED_NOW - timedelta(days=3)),
            created_by_user_id=None,
        )
    )
    seeded.commit()

    series = list_patient_observations(
        seeded,
        principal=doctor_principal,
        patient_id=PATIENT_A_ID,
        route="GET /api/v1/doctor/patients/{patient_id}/observations",
        request_id=REQUEST_ID,
        now=FIXED_NOW,
    )
    timeline = timeline_for(seeded, doctor_principal)

    assert all(item.validation is not ValidationState.REJECTED for item in series.items)
    assert any(item.validation is ValidationState.REJECTED for item in timeline.observations)


def test_observation_filters(seeded: Session, doctor_principal: Principal) -> None:
    """Filters by measurement type and time window are applied server-side."""
    from datetime import UTC, datetime

    series = list_patient_observations(
        seeded,
        principal=doctor_principal,
        patient_id=PATIENT_B_ID,
        route="GET /api/v1/doctor/patients/{patient_id}/observations",
        request_id=REQUEST_ID,
        now=FIXED_NOW,
        measure_type=MeasureType.SYSTOLIC_BP,
        from_=datetime(2026, 10, 15, tzinfo=UTC),
        to=datetime(2026, 11, 4, tzinfo=UTC),
    )

    assert [item.value for item in series.items] == [158.0, 146.0]
    assert {item.measure_type for item in series.items} == {MeasureType.SYSTOLIC_BP}


def test_inverted_time_window_is_refused(seeded: Session, doctor_principal: Principal) -> None:
    """A reversed window is a client error."""
    from datetime import UTC, datetime

    with pytest.raises(ApiError) as caught:
        list_patient_observations(
            seeded,
            principal=doctor_principal,
            patient_id=PATIENT_A_ID,
            route="GET /api/v1/doctor/patients/{patient_id}/observations",
            request_id=REQUEST_ID,
            now=FIXED_NOW,
            from_=datetime(2026, 11, 1, tzinfo=UTC),
            to=datetime(2026, 10, 1, tzinfo=UTC),
        )

    assert caught.value.code is ErrorCode.VALIDATION


def test_observation_series_paginates(seeded: Session, doctor_principal: Principal) -> None:
    """Keyset pagination over the series returns disjoint pages."""
    first = list_patient_observations(
        seeded,
        principal=doctor_principal,
        patient_id=PATIENT_B_ID,
        route="GET /api/v1/doctor/patients/{patient_id}/observations",
        request_id=REQUEST_ID,
        now=FIXED_NOW,
        limit=4,
    )
    second = list_patient_observations(
        seeded,
        principal=doctor_principal,
        patient_id=PATIENT_B_ID,
        route="GET /api/v1/doctor/patients/{patient_id}/observations",
        request_id=REQUEST_ID,
        now=FIXED_NOW,
        limit=4,
        cursor=first.next_cursor,
    )

    assert len(first.items) == 4
    assert first.next_cursor is not None
    assert {item.id for item in first.items}.isdisjoint({item.id for item in second.items})


def test_limit_is_clamped_to_the_contract_maximum(
    seeded: Session, doctor_principal: Principal
) -> None:
    """A limit above 100 is clamped rather than honoured."""
    page = list_assigned_patients(seeded, principal=doctor_principal, limit=1000)
    assert len(page.items) == 3


def test_a_doctor_assigned_elsewhere_cannot_read_this_patient(
    seeded: Session, unassigned_doctor_principal: Principal
) -> None:
    """REQ-SEC-01 / NEG-01 mechanics: scope, not just "some assignment".

    The caller here *is* a doctor with an active assignment (patient C), so the
    denial cannot be explained by "no assignments at all". Patient A belongs to a
    different doctor, and the attempt is audited.
    """
    from app.db.models import Patient

    patient_c = seeded.get(Patient, PATIENT_C_ID)
    assert patient_c is not None
    patient_c.assigned_doctor_id = unassigned_doctor_principal.user_id
    seeded.commit()

    with pytest.raises(ApiError) as caught:
        timeline_for(seeded, unassigned_doctor_principal, PATIENT_A_ID)
    seeded.commit()

    assert caught.value.status_code == 403
    assert caught.value.code is ErrorCode.SCOPE_VIOLATION

    denials = (
        seeded.execute(select(AuditEvent).where(AuditEvent.event_type == "access.denied"))
        .scalars()
        .all()
    )
    assert len(denials) == 1
    assert denials[0].actor_id == unassigned_doctor_principal.user_id
    assert denials[0].patient_id == PATIENT_A_ID

    # And the assignment it does hold is readable, so the check is not blanket.
    assigned = timeline_for(seeded, unassigned_doctor_principal, PATIENT_C_ID)
    assert assigned.patient_id == PATIENT_C_ID
