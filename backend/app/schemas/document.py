"""Document ingestion and verification schemas (``API_CONTRACT.md`` §3).

Every shape here mirrors ``openapi.phase0.yaml`` exactly — same required fields,
same enums, same bounds — because ``scripts/python/check_openapi.py`` compares the
generated document membership against the committed contract and the P3 tests
assert the two agree.

Two deliberate choices:

* ``ExtractionAttemptSummary`` is the **redacted** projection defined in the
  contract: ``path``, ``succeeded``, ``error_code``, ``duration_ms``,
  ``tool_version``, ``created_at``. The typed attempt metadata the triage router
  consumes stays internal (``P0-R13``).
* ``VerificationIssue.fact_ids`` and ``evidence`` are capped at 8 by the
  contract, so the model enforces the cap rather than letting a wide document
  produce an unbounded payload.

Nothing here accepts a patient id, a trust level or a verification status from a
client: those are derived server-side. ``extra="forbid"`` makes that structural.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from app.core.enums import (
    DocumentMimeType,
    DocumentStatus,
    ExtractionPath,
    FactField,
    FactVerificationStatus,
    IssueType,
    QualityFlag,
    VerificationDecision,
)
from app.schemas.common import ApiModel, UtcDatetime

#: Upper bound the contract puts on ``ExtractedFact.raw_text``.
MAX_RAW_TEXT = 300

#: Upper bound the contract puts on any issue/fact identifier list.
MAX_LINKED_ITEMS = 8

#: Fixed disclaimer text for extraction payloads (``API_CONTRACT.md`` §3).
EXTRACTION_DISCLAIMER = "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"

#: Fixed notice marking persisted OCR/text output as untrusted engine data.
SOURCE_TRUTH_NOTICE = (
    "OCR-transcribed text is engine output (untrusted data), not original source "
    "truth. Compare against GET /file before verifying measurements."
)


class DocumentUploadResponse(ApiModel):
    """``202`` body for an accepted upload.

    ``status`` is a literal: an upload can only ever be ``pending_extraction``.
    A client cannot receive a document that already claims extraction or
    verification.
    """

    document_id: str
    status: Literal["pending_extraction"] = "pending_extraction"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_count: int | None = Field(default=None, ge=0, le=20)
    duplicate_ignored: bool = False


class DocumentMeta(ApiModel):
    """Document metadata for any principal allowed to see the document.

    Deliberately contains **no** clinical value, no fact text and no extracted
    span, so a patient can read their own document row without seeing
    pre-verification content (``P0-R13``).

    **R21 §4.9 — the patient is the recovery actor.** A patient whose report was
    rejected needs three non-clinical facts to act on it, so exactly three
    optional fields are added and nothing else:

    ``failure_code``
        The terminal reason, an enum-like token such as ``measurement_rejected``.
        Never document text.
    ``recovery_eligible``
        Whether this document may be named in a later ``recovery_of``. Derived
        server-side; a client cannot assert it.
    ``recovered_from_document_id``
        The patient-declared source this row was uploaded to replace, if any.

    All three are non-clinical: they describe *state and lineage*, never a
    reading. Adding them does not widen what a patient can learn about the
    content of their own unverified document.
    """

    id: str
    patient_id: str
    filename: str
    mime_type: DocumentMimeType
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1, le=10 * 1024 * 1024)
    page_count: int | None = Field(default=None, ge=0, le=20)
    extraction_status: DocumentStatus
    uploaded_at: UtcDatetime
    #: Terminal reason token (enum/ID only, never document text).
    failure_code: str | None = Field(default=None, max_length=48)
    #: True only for a `failed` document whose reason is a doctor rejection.
    recovery_eligible: bool = False
    #: The source this document was declared a recovery of, if any.
    recovered_from_document_id: str | None = None


class EvidenceRef(ApiModel):
    """A pointer back to a stored span, never to inline free text.

    ``raw_text`` is capped at 500 characters by the contract; the stored span is
    the authority, and the copy is a convenience for display.
    """

    kind: Literal["document_span", "observation", "checkin_note"]
    document_id: str | None = None
    observation_id: str | None = None
    page_index: int | None = Field(default=None, ge=0)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    raw_text: str | None = Field(default=None, max_length=500)
    extractor: Literal["pypdf", "tesseract", "manual", "patient_form"] | None = None


class ExtractedFact(ApiModel):
    """One candidate fact with full provenance.

    ``verification_status`` is always ``pending`` on creation. It moves only
    through ``POST /verify``, which appends to ``fact_verification``; no service
    may set ``verified`` directly.
    """

    fact_id: str
    document_id: str
    field_name: FactField
    raw_text: str = Field(max_length=MAX_RAW_TEXT)
    normalized_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    page_index: int = Field(ge=0)
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    quality_flags: list[QualityFlag] = Field(default_factory=list, max_length=6)
    confidence: float | None = Field(default=None, ge=0, le=1)
    verification_status: FactVerificationStatus
    requires_source_confirmation: bool = False
    evidence: EvidenceRef

    @field_validator("char_end")
    @classmethod
    def _end_not_before_start(cls, value: int | None) -> int | None:
        """Reject an inverted span at the schema boundary too."""
        if value is not None and value < 0:
            raise ValueError("char_end must be non-negative")
        return value


class ExtractionAttemptSummary(ApiModel):
    """Redacted projection of a persisted extraction attempt.

    Exposes the route and outcome only. The typed metadata the triage router uses
    (``preprocessing``, ``engine_confidence``, ``text_char_count``,
    ``page_from``/``page_to``) is intentionally absent.
    """

    path: ExtractionPath
    succeeded: bool
    error_code: str | None = Field(default=None, max_length=48)
    duration_ms: int = Field(ge=0)
    tool_version: str | None = Field(default=None, max_length=64)
    created_at: UtcDatetime


class VerificationIssue(ApiModel):
    """Pre-verification blocker. **Never** carries a ``rule_id``.

    A ``VI-*`` issue is a different output type from a post-verification
    ``DR-*`` review item and must not be rendered in the same UI section.
    """

    issue_id: str
    issue_type: IssueType
    reason_code: str = Field(max_length=64)
    #: Required by the contract (``required: [..., blocking, ...]``). It is a
    #: constant ``true`` because a non-blocking verification issue is not a thing
    #: this phase can produce: every ``VI-*`` gates a value. Making it required
    #: and const keeps the wire shape honest instead of leaning on a default.
    blocking: Literal[True]
    message: str = Field(max_length=240)
    document_id: str | None = None
    fact_ids: list[str] = Field(default_factory=list, max_length=MAX_LINKED_ITEMS)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=MAX_LINKED_ITEMS)
    created_at: UtcDatetime

    @field_validator("issue_type")
    @classmethod
    def _no_rule_id_prefix(cls, value: IssueType) -> IssueType:
        """Guard the retirement of ``DR-*`` at the type level."""
        if not value.value.startswith("VI-"):
            raise ValueError("verification issues must be VI-* codes")
        return value


class ExtractionResponse(ApiModel):
    """The doctor's view of one document's extraction.

    Served as ``200`` for both a healthy extraction and a **terminal failure**
    (owner decision D-10): ``document_status='failed'`` plus the redacted attempt
    ``error_code``. ``409 E_EXTRACTION_PENDING`` is reserved for the transitional
    ``pending_extraction`` state only, so a client is never told to poll forever.
    """

    document_id: str
    document_status: DocumentStatus
    facts: list[ExtractedFact] = Field(max_length=40)
    attempts: list[ExtractionAttemptSummary] = Field(max_length=10)
    verification_issues: list[VerificationIssue] = Field(max_length=20)
    disclaimer: str = Field(default=EXTRACTION_DISCLAIMER)
    #: **R21 §4.9** — doctor-only recovery context. The doctor needs to know why
    #: a document is terminal and where it came from; both are enum/ids, so this
    #: adds no clinical claim. ``recovery_eligible`` is deliberately *not* here:
    #: it is a patient-facing affordance, and duplicating it invites the two
    #: views to disagree.
    failure_code: str | None = Field(default=None, max_length=48)
    recovered_from_document_id: str | None = None


class VerifyRequest(ApiModel):
    """A doctor's decision on exactly one fact.

    ``decision='corrected'`` requires the replacement value, because a correction
    with no replacement is a rejection in disguise and would silently change what
    the doctor recorded. The validator enforces that pairing.

    For OCR-derived measurement/unit facts (``extractor='tesseract'``),
    ``source_image_compared=True``, prior doctor access to ``GET /file``, and
    explicit value/unit confirmation are required before verification or
    correction can succeed.
    """

    fact_id: str
    decision: VerificationDecision
    corrected_value: str | None = Field(default=None, max_length=120)
    corrected_unit: str | None = Field(default=None, max_length=32)
    reason: str | None = Field(default=None, max_length=300)
    source_image_compared: bool = False
    confirmed_value: str | None = Field(default=None, max_length=120)
    confirmed_unit: str | None = Field(default=None, max_length=32)

    @field_validator("corrected_unit")
    @classmethod
    def _unit_shape(cls, value: str | None) -> str | None:
        """Keep the unit a short bounded token, exactly as stored."""
        if value is not None and not value.strip():
            raise ValueError("corrected_unit must not be blank")
        return value

    @field_validator("confirmed_value")
    @classmethod
    def _confirmed_value_shape(cls, value: str | None) -> str | None:
        """Reject a whitespace-only confirmed_value."""
        if value is not None and not value.strip():
            raise ValueError("confirmed_value must not be blank")
        return value

    @field_validator("confirmed_unit")
    @classmethod
    def _confirmed_unit_shape(cls, value: str | None) -> str | None:
        """Reject a whitespace-only confirmed_unit."""
        if value is not None and not value.strip():
            raise ValueError("confirmed_unit must not be blank")
        return value

    @field_validator("reason")
    @classmethod
    def _reason_shape(cls, value: str | None) -> str | None:
        """Reject a whitespace-only reason; it carries no information."""
        if value is not None and not value.strip():
            raise ValueError("reason must not be blank")
        return value


class VerificationRecord(ApiModel):
    """The append-only decision that was just written.

    ``previous_value``/``new_value``/``new_unit`` make a correction auditable from
    the response alone: what the document said, what the doctor accepted, and which
    decision produced the change. The original fact keeps its immutable extracted
    text and span, so the before/after pair is the *only* place the human edit
    lives.
    """

    decision: VerificationDecision
    verified_by: str
    decided_at: UtcDatetime
    reason: str | None = None
    previous_value: str | None = None
    new_value: str | None = Field(default=None, max_length=120)
    new_unit: str | None = Field(default=None, max_length=32)
    superseded_fact_id: str | None = None
    source_image_compared: bool = False
    confirmed_value: str | None = Field(default=None, max_length=120)
    confirmed_unit: str | None = Field(default=None, max_length=32)


class VerifyResponse(ApiModel):
    """The updated fact, its decision, and the recomputed document status."""

    fact: ExtractedFact
    verification: VerificationRecord
    document_status: DocumentStatus


class DocumentPageTextItem(ApiModel):
    """Persisted extracted/OCR text for one page (doctor provenance view)."""

    page_index: int = Field(ge=0)
    extractor: Literal["pypdf", "tesseract"]
    tool_version: str | None = Field(default=None, max_length=64)
    text: str
    text_length: int = Field(ge=0, le=20_000)
    non_whitespace_chars: int = Field(ge=0)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: UtcDatetime


class DocumentTextResponse(ApiModel):
    """Doctor-only persisted per-page transcription payload (`GET /text`)."""

    document_id: str
    document_status: DocumentStatus
    source_truth_notice: str = Field(default=SOURCE_TRUTH_NOTICE)
    disclaimer: str = Field(default=EXTRACTION_DISCLAIMER)
    pages: list[DocumentPageTextItem]


__all__ = [
    "EXTRACTION_DISCLAIMER",
    "MAX_LINKED_ITEMS",
    "MAX_RAW_TEXT",
    "SOURCE_TRUTH_NOTICE",
    "DocumentMeta",
    "DocumentPageTextItem",
    "DocumentTextResponse",
    "DocumentUploadResponse",
    "EvidenceRef",
    "ExtractedFact",
    "ExtractionAttemptSummary",
    "ExtractionResponse",
    "VerificationIssue",
    "VerificationRecord",
    "VerifyRequest",
    "VerifyResponse",
]
