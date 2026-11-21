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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ActorType,
    AuditOutcome,
    DocumentMimeType,
    DocumentStatus,
    EncounterType,
    ExtractionPath,
    FactField,
    FactVerificationStatus,
    IssueState,
    IssueType,
    MeasureType,
    ObservationSource,
    Preprocessing,
    Role,
    SexAtBirth,
    TrustLevel,
    Unit,
    ValidationState,
    VerificationDecision,
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
        # P3: one observation per verified fact. SQLite treats NULLs as
        # distinct, so seeded and check-in rows are unaffected; replaying a
        # verification can therefore never duplicate a measurement
        # (REQ-DATA-05, ``ux_obs_source_fact``).
        Index("ux_obs_source_fact", "source_fact_id", unique=True),
        # Semantic check-in identity, enforced by the database so two racing
        # writers cannot persist the same self-reported measurement twice
        # (``E_DUPLICATE_CHECKIN``). Partial on purpose: document facts (P3) and
        # seed fixtures may legitimately share a timestamp, and this index must
        # never constrain them.
        Index(
            "uq_observation_checkin_identity",
            "patient_id",
            "measure_type",
            "measured_at",
            "value",
            "unit",
            unique=True,
            sqlite_where=text("source = 'patient_checkin'"),
        ),
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
    #: Set only when ``source='verified_document'``. Deferred by P2 until
    #: ``extracted_fact`` existed; the foreign key is added by migration 0003.
    source_fact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("extracted_fact.id", ondelete="RESTRICT"), nullable=True
    )
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
    workflow_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="RESTRICT"), nullable=True
    )
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    safe_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"AuditEvent(event_type={self.event_type!r}, outcome={self.outcome!r})"


# =============================================================================
# P3 — document ingestion, extraction provenance and doctor verification
# =============================================================================
#
# Five tables from ``DATA_DICTIONARY.md`` §2.4-§2.8a. Every candidate fact is
# unverified by construction: ``verification_status`` defaults to ``pending``
# and only ``services.documents.verification`` may change it, inside the same
# transaction that appends the ``fact_verification`` row.


class Document(Base):
    """An uploaded synthetic report (``DATA_DICTIONARY.md`` §2.4).

    ``mime_type`` comes from magic bytes, never from the client filename
    (``EXTRACTION_PROVENANCE.md`` §1 rule 1). ``stored_path`` is a generated
    name relative to the gitignored runtime upload directory, so a client can
    never influence the path on disk.
    """

    __tablename__ = "document"
    __table_args__ = (
        CheckConstraint(f"mime_type IN ({_in_list(DocumentMimeType)})", name="mime_type_allowed"),
        CheckConstraint(
            f"extraction_status IN ({_in_list(DocumentStatus)})", name="status_allowed"
        ),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="size_within_cap"),
        CheckConstraint("page_count IS NULL OR page_count <= 20", name="page_count_within_cap"),
        CheckConstraint("length(original_filename) > 0", name="filename_not_empty"),
        Index("ix_document_patient", "patient_id"),
        # Duplicate-upload detection is per patient, so an identical report
        # belonging to another patient is not blocked (NEG-18).
        Index("ux_document_sha_patient", "patient_id", "sha256", unique=True),
        # Recovery lineage is a self-reference, so it needs its own index:
        # SQLite does not index a foreign key automatically, and the downgrade
        # guard in migration ``0004`` scans this column before dropping it.
        Index("ix_document_recovered_from", "recovered_from_document_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    #: Sanitized metadata only: no path separators, no control characters.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Generated name relative to the runtime upload directory. Never committed.
    stored_path: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=DocumentStatus.PENDING_EXTRACTION.value,
        server_default=DocumentStatus.PENDING_EXTRACTION.value,
    )
    #: Mirrors the tool error codes; enum/ID only, never document text.
    failure_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    #: The synthetic patient reference printed in the document header, when the
    #: extractor could read one (``DEMO-A-001`` style, bounded).
    #:
    #: Compared against the *uploading patient's* ``external_ref`` to raise
    #: ``VI-004``. Without it the wrong-patient safeguard is unreachable: the
    #: document row only knows who uploaded it, never who the paper claims to be
    #: about. Bounded to the contract's synthetic-reference width.
    document_patient_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)
    #: **R07:** every *distinct* patient reference printed anywhere in the
    #: document, as a compact JSON array (``["DEMO-A-001","DEMO-B-001"]``).
    #:
    #: ``document_patient_ref`` alone cannot express "the document named two
    #: different patients": that column is ``None`` both for "made no claim" and
    #: for "made a contradictory claim", and the two need different verdicts. This
    #: keeps the distinction so an ``A then B`` document fails closed with
    #: ``VI-004`` instead of being silently reduced to its first reference.
    document_patient_refs: Mapped[str | None] = mapped_column(String(240), nullable=True)
    uploaded_at: Mapped[str] = mapped_column(String(20), nullable=False)

    #: **R21 §4.3 — patient-declared recovery lineage.** The terminal document
    #: this upload replaces, or ``NULL`` for an ordinary upload.
    #:
    #: This is a *declaration by the uploader*, not a claim of clinical
    #: equivalence: nothing here asserts the new bytes are clearer, related or
    #: safer. The new document is extracted, scope-checked, identity-checked
    #: (``VI-004``), conflict-checked (``VI-006``) and doctor-verified on its own,
    #: and a link never substitutes for any of those.
    #:
    #: ``ON DELETE RESTRICT`` on a *self*-reference keeps provenance intact: a
    #: source document cannot be deleted out from under a recovery that names it.
    recovered_from_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document.id", ondelete="RESTRICT"),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Document(id={self.id!r}, status={self.extraction_status!r})"


class ExtractionAttempt(Base):
    """One bounded extraction attempt (``DATA_DICTIONARY.md`` §2.5).

    These rows are the only typed source for triage decisions. ``engine_confidence``
    is **engine-reported only**: NULL means the engine reported nothing, and is
    never estimated or back-filled (``API_CONTRACT.md`` §1.1 rule 1a).
    """

    __tablename__ = "extraction_attempt"
    __table_args__ = (
        CheckConstraint(f"path IN ({_in_list(ExtractionPath)})", name="path_allowed"),
        CheckConstraint(
            f"preprocessing IN ({_in_list(Preprocessing)})", name="preprocessing_allowed"
        ),
        CheckConstraint(
            "engine_confidence IS NULL OR (engine_confidence >= 0.0 AND engine_confidence <= 1.0)",
            name="confidence_in_range",
        ),
        CheckConstraint("text_char_count >= 0", name="text_char_count_non_negative"),
        CheckConstraint("duration_ms >= 0", name="duration_non_negative"),
        CheckConstraint("page_from >= 0 AND page_to >= page_from", name="page_range_valid"),
        Index("ix_attempt_document", "document_id", "created_at"),
        Index("ix_attempt_doc_conf", "document_id", "engine_confidence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(16), nullable=False)
    preprocessing: Mapped[str] = mapped_column(
        String(20), nullable=False, default=Preprocessing.NONE.value, server_default="none"
    )
    engine_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_char_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    page_from: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    page_to: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"ExtractionAttempt(path={self.path!r}, succeeded={self.succeeded!r})"


class ExtractedFact(Base):
    """A candidate fact — **unverified by construction** (§2.6).

    ``raw_text`` is stored exactly as extracted (bounded), ``normalized_value``
    carries deterministic normalization only, and the span makes the value
    auditable against the source page.
    """

    __tablename__ = "extracted_fact"
    __table_args__ = (
        CheckConstraint(f"field_name IN ({_in_list(FactField)})", name="field_allowed"),
        CheckConstraint(
            f"verification_status IN ({_in_list(FactVerificationStatus)})",
            name="verification_status_allowed",
        ),
        CheckConstraint("raw_text <> ''", name="raw_text_not_empty"),
        CheckConstraint("length(raw_text) <= 300", name="raw_text_bounded"),
        CheckConstraint("page_index >= 0", name="page_index_non_negative"),
        CheckConstraint("char_start >= 0 AND char_end >= char_start", name="span_ordered"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="confidence_in_range",
        ),
        Index("ix_fact_document", "document_id"),
        Index("ix_fact_status", "patient_id", "verification_status"),
        # R05 lineage: "which fact supersedes this one?" is a per-correction lookup.
        Index("ix_fact_corrected_from", "corrected_from_fact_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    #: Denormalized so every scope check is a single-index read.
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(24), nullable=False)
    raw_text: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Document unit text (``mmHg``/``bpm``/``mg/dL``/``g/dL``/``%``) — never an
    #: ``Observation`` unit unless the closed mapping table says so (P0-R06).
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Which extraction route produced this fact (``REQ-ING-02`` provenance).
    #: ``pypdf`` for the embedded text layer, ``tesseract`` for OCR, ``manual``
    #: only for a doctor-supplied correction. Stored per fact because a single
    #: document may mix routes (a scanned page inside a text PDF), so the
    #: document-level attempts cannot answer "where did *this* value come from".
    extractor: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ExtractionPath.PYPDF.value,
        server_default=ExtractionPath.PYPDF.value,
    )
    #: Set on a doctor-corrected fact to the original fact it supersedes. The
    #: original keeps its immutable ``raw_text``/span; the corrected row carries
    #: the human-supplied value. This keeps the extraction evidence and the human
    #: decision distinctly traceable instead of rewriting one into the other.
    corrected_from_fact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    #: JSON array of ``QualityFlag`` values.
    quality_flags: Mapped[str] = mapped_column(
        String(200), nullable=False, default="[]", server_default="[]"
    )
    #: OCR confidence when the engine reported one; NULL for a text layer.
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=FactVerificationStatus.PENDING.value,
        server_default=FactVerificationStatus.PENDING.value,
    )
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"ExtractedFact(field={self.field_name!r}, status={self.verification_status!r})"


class DocumentPageText(Base):
    """Durable per-page extracted/OCR text for provenance & doctor comparison.

    Stores the bounded page string actually parsed into ``extracted_fact`` rows
    so ``char_start:char_end`` spans remain auditable against persisted text.
    OCR output here is engine output (untrusted data), never original source truth.
    """

    __tablename__ = "document_page_text"
    __table_args__ = (
        CheckConstraint("page_index >= 0", name="page_index_non_negative"),
        CheckConstraint(
            f"extractor IN ('{ExtractionPath.PYPDF.value}', '{ExtractionPath.TESSERACT.value}')",
            name="extractor_allowed",
        ),
        CheckConstraint("text_length >= 0 AND text_length <= 20000", name="text_length_bounded"),
        CheckConstraint("length(text) <= 20000", name="text_bounded"),
        CheckConstraint("non_whitespace_chars >= 0", name="non_whitespace_non_negative"),
        CheckConstraint("length(text_sha256) = 64", name="sha256_hex_length"),
        Index("ux_page_text_doc_page", "document_id", "page_index", unique=True),
        Index("ix_page_text_document", "document_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    extractor: Mapped[str] = mapped_column(String(16), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)
    non_whitespace_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"DocumentPageText(doc={self.document_id!r}, page={self.page_index!r})"


class FactVerification(Base):
    """Append-only human decision log (``DATA_DICTIONARY.md`` §2.7).

    There is no update or delete path in the service layer, and migration 0003
    installs a ``BEFORE INSERT`` trigger that rejects a ``verified_by_user_id``
    whose ``user.role`` is not ``doctor``. Service *and* database, per the
    accepted data dictionary.
    """

    __tablename__ = "fact_verification"
    __table_args__ = (
        CheckConstraint(f"decision IN ({_in_list(VerificationDecision)})", name="decision_allowed"),
        CheckConstraint("source_image_compared IN (0, 1)", name="source_compared_bool"),
        Index("ix_factver_fact", "fact_id", "decided_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fact_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extracted_fact.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    verified_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    decided_at: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Explicit attestation submitted by the deciding doctor; records attestation,
    #: not independent proof of visual inspection.
    source_image_compared: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    confirmed_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confirmed_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"FactVerification(decision={self.decision!r})"


class VerificationIssue(Base):
    """Pre-verification blocker (``DATA_DICTIONARY.md`` §2.8a).

    There is deliberately **no ``rule_id`` column**: a ``VerificationIssue`` can
    never be stored or rendered as a ``DR-*`` review item (``P0-R03``).
    """

    __tablename__ = "verification_issue"
    __table_args__ = (
        CheckConstraint(f"issue_type IN ({_in_list(IssueType)})", name="issue_type_allowed"),
        CheckConstraint("blocking = 1", name="always_blocking"),
        CheckConstraint(f"state IN ({_in_list(IssueState)})", name="state_allowed"),
        CheckConstraint("length(message) <= 240", name="message_bounded"),
        Index("ix_vi_document_state", "document_id", "state"),
        Index("ix_vi_run", "workflow_run_id"),
        # The lifecycle's identity key (``sync_issues`` upserts on this pair). A
        # UNIQUE index makes a concurrent double-insert fail loudly instead of
        # producing two blockers for the same document. ``document_id`` is
        # nullable for the future workflow-run flavour of an issue, and SQLite
        # treats NULLs as distinct, so those rows stay unconstrained.
        Index("ux_vi_document_type", "document_id", "issue_type", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="CASCADE"), nullable=True
    )
    issue_type: Mapped[str] = mapped_column(String(8), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    #: JSON array of ``extracted_fact.id`` values this blocker refers to, so the
    #: linkage survives across reads instead of being recomputed per request.
    fact_ids: Mapped[str | None] = mapped_column(String(1200), nullable=True)
    blocking: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    message: Mapped[str] = mapped_column(String(240), nullable=False)
    state: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        default=IssueState.OPEN.value,
        server_default=IssueState.OPEN.value,
    )
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"VerificationIssue(issue_type={self.issue_type!r})"


# =============================================================================
# P5-F0 — persisted run identity and immutable doctor-selected source manifest
# =============================================================================
# CH-01 authorizes this *foundation*, not a LangGraph run, real VI gate, DR
# evaluation or runtime policy activation. Every run starts queued.


class WorkflowRun(Base):
    """Durable parent for later graph runs; app SQLite owns run status."""

    __tablename__ = "workflow_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'needs_verification', "
            "'awaiting_decision', 'finalizing', 'completed', "
            "'failed_retryable', 'failed_terminal')",
            name="status_allowed",
        ),
        CheckConstraint("length(idempotency_key) = 64", name="idem_sha_length"),
        CheckConstraint("mapping_version LIKE 'map-%.%.%'", name="mapping_version_shape"),
        Index("ix_run_patient", "patient_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    workflow_version: Mapped[str] = mapped_column(String(12), nullable=False)
    state_schema_version: Mapped[str] = mapped_column(String(12), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(24), nullable=False)
    as_of_utc: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="queued", server_default="queued"
    )
    current_node: Mapped[str | None] = mapped_column(String(32), nullable=True)
    halt_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    retry_counts: Mapped[str] = mapped_column(
        String(500), nullable=False, default="{}", server_default="{}"
    )
    mapping_version: Mapped[str] = mapped_column(String(16), nullable=False)
    checkpoint_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(20), nullable=False)
    ended_at: Mapped[str | None] = mapped_column(String(20), nullable=True)


class RunSelectedDocument(Base):
    """Run-selected document and source hash snapshot (not glyph attestation)."""

    __tablename__ = "run_selected_document"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "document_id", name="ux_run_selected_document"),
        CheckConstraint("length(source_sha256) = 64", name="source_sha_length"),
        Index("ix_selected_document_run", "workflow_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="RESTRICT"), nullable=False
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)


class RunSelectedObservation(Base):
    """Run-selected stored observation, preserving its trust and source identity."""

    __tablename__ = "run_selected_observation"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "observation_id", name="ux_run_selected_observation"),
        Index("ix_selected_observation_run", "workflow_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="RESTRICT"), nullable=False
    )
    observation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("observation.id", ondelete="RESTRICT"), nullable=False
    )
    observation_created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(28), nullable=False)
    source_fact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)


class RunSourceOmission(Base):
    """Durable doctor-authored omission; original VI-002 is never modified."""

    __tablename__ = "run_source_omission"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "document_id", name="ux_run_source_omission"),
        CheckConstraint("reason_code = 'selected_separate_recovery_source'", name="reason_allowed"),
        CheckConstraint("length(source_sha256) = 64", name="source_sha_length"),
        Index("ix_run_omission_run", "workflow_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_run.id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document.id", ondelete="RESTRICT"), nullable=False
    )
    vi002_issue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_issue.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)


__all__ = [
    "AuditEvent",
    "CheckinIdempotency",
    "Document",
    "DocumentPageText",
    "Encounter",
    "ExtractedFact",
    "ExtractionAttempt",
    "FactVerification",
    "Observation",
    "Patient",
    "RunSelectedDocument",
    "RunSelectedObservation",
    "RunSourceOmission",
    "SchemaMeta",
    "User",
    "UserSession",
    "VerificationIssue",
    "WorkflowRun",
    "new_uuid",
]
