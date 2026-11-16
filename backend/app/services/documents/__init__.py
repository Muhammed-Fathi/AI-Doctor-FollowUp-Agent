"""Document ingestion, extraction and pre-verification (Phase 3).

The package is deliberately decomposed by *concern* rather than by *resource*, so
each safety rule has exactly one owner:

``storage``          path-escape-proof file naming and resolution,
``media``            magic-byte validation, size and page caps,
``text_extraction``  the pypdf text layer,
``rasterize``        PDF page rendering for OCR,
``ocr``              the Tesseract boundary and its honest absence,
``field_parser``     deterministic field candidates with character spans,
``mapping``          the closed ``map-1.0.0`` promotion table,
``issues``           ``VI-001..VI-006`` text and reason codes,
``quality``          assembling a document's blocking issues,
``verification``     append-only doctor decisions and the mapping transaction,
``intake``           upload acceptance and the bounded extraction pipeline,
``access``           authorization composed from the P2 policy primitives.

Nothing in this package can set ``verification_status='verified'`` on its own: the
only path is :func:`app.services.documents.verification.record_decision`, called by
a doctor-scoped route, and the database trigger installed by migration
``0003_p3_documents`` enforces the same rule independently.

The audit event names below are P3 additions to the P2 vocabulary. They live here
rather than in :mod:`app.services.audit` so the P3 change stays inside its
authorized file set; ``audit.append_audit_event`` accepts any namespaced string.
"""

from __future__ import annotations

#: A patient's upload was accepted and stored (unverified).
EVENT_DOCUMENT_UPLOADED = "document.uploaded"

#: A re-upload of identical bytes for the same patient was refused.
EVENT_DOCUMENT_DUPLICATE = "document.duplicate"

#: Extraction completed, wholly or with a recorded terminal failure.
EVENT_DOCUMENT_EXTRACTED = "document.extracted"

#: A doctor recorded a decision on one extracted fact.
EVENT_FACT_VERIFIED = "fact.verified"

#: A doctor-visible read of extraction content.
EVENT_EXTRACTION_READ = "document.extraction_read"

#: Instruction-like text was found in extracted content and ignored
#: (``CTR-EXTRACT-001`` §7.4). Recorded, never acted on.
EVENT_UNTRUSTED_CONTENT = "document.untrusted_content"

#: A recovery upload was accepted and linked to its patient-declared source
#: (R21 §4.3). Written **only** after the document row exists; a refused
#: ``recovery_of`` appends nothing. The detail names ids, never document text,
#: and never calls the link "corrected" or "validated" — it is a declaration.
EVENT_DOCUMENT_RECOVERED = "document.recovered"

__all__ = [
    "EVENT_DOCUMENT_DUPLICATE",
    "EVENT_DOCUMENT_EXTRACTED",
    "EVENT_DOCUMENT_RECOVERED",
    "EVENT_DOCUMENT_UPLOADED",
    "EVENT_EXTRACTION_READ",
    "EVENT_FACT_VERIFIED",
    "EVENT_UNTRUSTED_CONTENT",
]
