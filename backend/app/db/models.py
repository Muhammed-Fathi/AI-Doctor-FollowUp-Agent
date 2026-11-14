"""ORM models.

Phase 1 contributed the minimal ``schema_meta`` marker table. Phase 2 adds the
**patient-domain core** described by ``DATA_DICTIONARY.md`` §2.1-§2.3, §2.8 and
§2.17, plus two internal tables that the approved contracts require but the data
dictionary does not name (see the "Phase 2 additions" note below).

Everything here is synthetic-data only. There is no column that could hold a
real medical record number, contact detail or clinical narrative beyond the
bounded ``note``/``display_name`` fields.

Phase 2 additions outside ``DATA_DICTIONARY.md`` §2
---------------------------------------------------
``session``
    Opaque bearer sessions with an expiry and a revocation timestamp
    (``REQ-AUTH-03``). The raw token is never stored — only its SHA-256 digest
    (``token_sha256``), so a database read does not yield usable credentials.

``checkin_idempotency``
    Replay records for ``Idempotency-Key`` on ``POST /api/v1/patient/check-ins``
    (``API_CONTRACT.md`` §1). Stored separately so ``observation`` keeps exactly
    the columns the data dictionary specifies.

Both are additive and reversible; the amendment is requested in the P2 report
rather than applied silently to the contract document.

Documented P2 decisions (no silent deviations)
----------------------------------------------
* ``user.patient_id`` **does** carry a foreign key to ``patient.id``
  (``DATA_DICTIONARY.md`` §2.1), declared with ``use_alter=True``. The
  ``user -> patient -> user`` reference cycle cannot be topologically sorted, and
  SQLAlchemy reports that as ``SAWarning`` (fatal under our
  ``filterwarnings = error``). ``use_alter=True`` marks the cycle as known: the
  metadata sorts deterministically, and on SQLite the constraint is still emitted
  inline in ``CREATE TABLE`` (an ``ALTER TABLE ADD CONSTRAINT`` step is neither
  needed nor supported, and none is emitted). Enforcement then comes from
  ``PRAGMA foreign_keys=ON`` in :func:`app.db.session.create_db_engine`, so an
  orphan ``patient_id`` is rejected by the database, not only by the service
  layer.

  Consequence for migrations: ``DROP TABLE`` of a referenced parent fails while
  enforcement is on, so the Alembic environment runs migrations with
  ``foreign_keys=OFF`` (the documented SQLite pattern) and the gate verifies
  ``PRAGMA foreign_key_check`` afterwards. Row-level inserts are *not* cyclic —
  a patient's ``assigned_doctor_id`` points at a doctor account, and
  ``user.patient_id`` points back from a different (patient) account — so ordered
  seeding needs no deferred checks.
* ``observation.source_fact_id`` is deferred to P3 with ``extracted_fact``: the
  column's foreign key target does not exist yet, and creating a dangling
  reference (or a column that can never be populated) would be speculative.
* ``audit_event.workflow_run_id`` exists as an unconstrained column because
  ``workflow_run`` arrives in P5; adding the foreign key later is additive.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ActorType,
    AuditOutcome,
    EncounterType,
    MeasureType,
    ObservationSource,
    Role,
    SexAtBirth,
    TrustLevel,
    Unit,
    ValidationState,
)
from app.db.base import Base


def new_uuid() -> str:
    """Return a random UUIDv4 as the 36-character lowercase text used as a PK."""
    return str(uuid.uuid4())


def _in_list(values: type[str]) -> str:
    """Render a SQL ``IN`` list from an enum, keeping the CHECK text readable."""
    return ", ".join(f"'{value}'" for value in values)


class SchemaMeta(Base):
    """Key/value record describing the applied schema baseline."""

    __tablename__ = "schema_meta"
    __table_args__ = (
        CheckConstraint("length(key) > 0", name="key_not_empty"),
        CheckConstraint("length(value) > 0", name="value_not_empty"),
    )

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    # Match the baseline migration exactly (``CURRENT_TIMESTAMP``), so Alembic
    # autogenerate reports no spurious diff.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"SchemaMeta(key={self.key!r}, value={self.value!r})"


class User(Base):
    """A local demo account (``DATA_DICTIONARY.md`` §2.1).

    Roles are ``doctor``, ``patient`` and ``demo_admin``. There is no signup, no
    password reset and no role-granting path in the API; accounts exist only
    because the seeder created them.
    """

    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(f"role IN ({_in_list(Role)})", name="role_allowed"),
        CheckConstraint("length(username) >= 3 AND length(username) <= 64", name="username_length"),
        CheckConstraint(
            "(role = 'patient') = (patient_id IS NOT NULL)", name="patient_scope_matches_role"
        ),
        Index("ix_user_role", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Only the salted, self-describing hash (``core.security``) is stored.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Self scope for ``role='patient'``; NULL for every other role.
    #: ``use_alter`` breaks the ``user <-> patient`` metadata cycle; see the
    #: module docstring. The unique constraint keeps one account per patient.
    patient_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("patient.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        unique=True,
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Africa/Cairo", server_default="Africa/Cairo"
    )
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    last_login_at: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"User(username={self.username!r}, role={self.role!r})"


class Patient(Base):
    """A synthetic patient record (``DATA_DICTIONARY.md`` §2.2).

    ``assigned_doctor_id`` drives the doctor's ``S`` scope in
    ``ARCHITECTURE.md`` §6 and is the **only** source of truth for it: a request
    body can never assert an assignment.
    """

    __tablename__ = "patient"
    __table_args__ = (
        CheckConstraint(f"sex_at_birth IN ({_in_list(SexAtBirth)})", name="sex_allowed"),
        CheckConstraint("data_source = 'synthetic_fixture'", name="synthetic_data_only"),
        CheckConstraint("external_ref LIKE 'DEMO-%'", name="external_ref_demo_prefix"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sex_at_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    assigned_doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    external_ref: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True)
    data_source: Mapped[str] = mapped_column(
        String(24), nullable=False, default="synthetic_fixture", server_default="synthetic_fixture"
    )
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Patient(external_ref={self.external_ref!r})"


class Encounter(Base):
    """A synthetic outpatient visit (``DATA_DICTIONARY.md`` §2.3)."""

    __tablename__ = "encounter"
    __table_args__ = (
        CheckConstraint(
            f"encounter_type IN ({_in_list(EncounterType)})", name="encounter_type_allowed"
        ),
        Index("ix_encounter_patient_date", "patient_id", "encounter_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    encounter_date: Mapped[str] = mapped_column(String(10), nullable=False)
    encounter_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EncounterType.ROUTINE_FOLLOW_UP.value,
        server_default=EncounterType.ROUTINE_FOLLOW_UP.value,
    )
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Encounter(patient_id={self.patient_id!r}, date={self.encounter_date!r})"


class Observation(Base):
    """A timestamped measurement (``DATA_DICTIONARY.md`` §2.8).

    Two independent labels travel with every row and are never interchangeable:

    * ``validation`` — a deterministic data check (schema, unit allowlist,
      arbitrary plausibility band). It is **not** a human verification.
    * ``trust_level`` — the provenance class. A check-in is
      ``self_reported_validated``; only a doctor-verified document fact may be
      ``doctor_verified``, and the CHECK constraints below make a self-reported
      row claiming doctor verification impossible to insert.
    """

    __tablename__ = "observation"
    __table_args__ = (
        CheckConstraint(f"measure_type IN ({_in_list(MeasureType)})", name="measure_allowed"),
        CheckConstraint(f"unit IN ({_in_list(Unit)})", name="unit_allowed"),
        CheckConstraint(f"source IN ({_in_list(ObservationSource)})", name="source_allowed"),
        CheckConstraint(f"validation IN ({_in_list(ValidationState)})", name="validation_allowed"),
        CheckConstraint(f"trust_level IN ({_in_list(TrustLevel)})", name="trust_allowed"),
        CheckConstraint("value > 0", name="value_positive"),
        CheckConstraint(
            "trust_level <> 'doctor_verified' OR "
            "(verified_by_user_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="doctor_verified_requires_verifier",
        ),
        CheckConstraint(
            "trust_level <> 'self_reported_validated' OR "
            "(verified_by_user_id IS NULL AND verified_at IS NULL)",
            name="self_reported_forbids_verifier",
        ),
        Index("ix_obs_patient_type_time", "patient_id", "measure_type", "measured_at"),
        Index("ix_obs_trust", "patient_id", "trust_level"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    encounter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("encounter.id", ondelete="RESTRICT"), nullable=True
    )
    measure_type: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    measured_at: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    validation: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ValidationState.OK.value, server_default="ok"
    )
    trust_level: Mapped[str] = mapped_column(String(28), nullable=False)
    verified_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
    )
    verified_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Observation(measure_type={self.measure_type!r}, measured_at={self.measured_at!r})"


class UserSession(Base):
    """An opaque bearer session (``REQ-AUTH-03``).

    Not part of ``DATA_DICTIONARY.md`` §2 — see the module docstring. Only the
    SHA-256 digest of the token is stored; ``revoked_at`` implements logout
    invalidation and ``expires_at`` implements expiry.
    """

    __tablename__ = "session"
    __table_args__ = (
        CheckConstraint("length(token_sha256) = 64", name="token_sha256_length"),
        Index("ix_session_user", "user_id"),
        Index("ix_session_expiry", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    token_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[str] = mapped_column(String(20), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_used_at: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"UserSession(id={self.id!r}, user_id={self.user_id!r})"


class CheckinIdempotency(Base):
    """Replay record for an ``Idempotency-Key`` on a patient check-in.

    ``request_fingerprint`` is the SHA-256 of the canonical request body, so the
    same key with a different payload is detectable and must fail with
    ``409 E_IDEMPOTENCY_CONFLICT`` instead of silently returning the old result.
    """

    __tablename__ = "checkin_idempotency"
    __table_args__ = (
        UniqueConstraint("patient_id", "idempotency_key", name="uq_checkin_idem_patient_key"),
        CheckConstraint("length(request_fingerprint) = 64", name="fingerprint_length"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    observation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("observation.id", ondelete="CASCADE"), nullable=False
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"CheckinIdempotency(patient_id={self.patient_id!r})"


class AuditEvent(Base):
    """Append-only audit record (``DATA_DICTIONARY.md`` §2.17).

    The application layer exposes only an insert helper
    (``services.audit.append_audit_event``) — there is no update or delete path.
    ``safe_detail`` is built from enums, ids and route templates only; it never
    carries a password, a token, a document body or patient free text
    (``REQ-AUDIT-02``).
    """

    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint(f"actor_type IN ({_in_list(ActorType)})", name="actor_type_allowed"),
        CheckConstraint(f"outcome IN ({_in_list(AuditOutcome)})", name="outcome_allowed"),
        Index("ix_audit_patient_time", "patient_id", "created_at"),
        Index("ix_audit_run", "workflow_run_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: Column exists for P5 runs; the foreign key is added when ``workflow_run``
    #: is created (additive migration), so no dangling reference is declared now.
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    safe_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"AuditEvent(event_type={self.event_type!r}, outcome={self.outcome!r})"


__all__ = [
    "AuditEvent",
    "CheckinIdempotency",
    "Encounter",
    "Observation",
    "Patient",
    "SchemaMeta",
    "User",
    "UserSession",
    "new_uuid",
]
