"""Deterministic parsing of the five declared report fields.

Only ``report_date``, ``test_name``, ``value``, ``unit`` and ``reference_text``
are ever produced (``REQ-ING-03``). There is no "impression", no clinical
free-text summarisation, and no fallback that invents a field.

Provenance rules (``REQ-VERIFY-01``, ``EXTRACTION_PROVENANCE.md`` §5):

* every candidate carries ``page_index`` plus a ``char_start``/``char_end`` span
  into the text that was actually extracted for that page;
* the span is computed from the match offsets in that text, so it can always be
  re-resolved against the stored page text;
* ``raw_text`` is the exact source slice, not a re-formatted value.

Ambiguity is *flagged*, never resolved by a guess: a date like ``03/11/2026``
yields an ``ambiguous_date`` fact that a doctor must settle, and a missing or
non-allowlisted unit yields ``ambiguous_unit``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import DocumentUnit, ExtractionPath, FactField, QualityFlag
from app.services.documents.text_extraction import PageText

#: ``Report date: 2026-10-20`` — ISO first, because ISO is unambiguous.
_ISO_DATE = re.compile(r"report\s*date\s*:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

#: ``Report date: 03/11/2026`` — genuinely ambiguous (3 Nov or 11 Mar).
_SLASH_DATE = re.compile(r"report\s*date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE)

#: ``Test: Hemoglobin          Value: 13.4 g/dL`` — the lab line.
_TEST_VALUE = re.compile(
    r"test\s*:\s*(?P<test>[A-Za-z][A-Za-z0-9 ()%/._-]*?)\s{2,}"
    r"value\s*:\s*(?P<value>[^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

#: ``Reference range: 12.0 - 15.5 g/dL``
_REFERENCE = re.compile(
    r"reference\s*range\s*:\s*(?P<reference>[^\n]+?)\s*$", re.IGNORECASE | re.MULTILINE
)

#: ``Ref: DEMO-A-001`` — the synthetic patient reference printed in the report
#: header. Matched strictly to the demo reference shape so a stray ``Ref:`` in
#: prose cannot become an identity claim.
_PATIENT_REF = re.compile(r"\bref\s*:\s*(?P<ref>DEMO-[A-Z0-9-]{1,32})", re.IGNORECASE)

#: A numeric token, optionally signed, with at most one decimal separator.
_NUMERIC_TOKEN = re.compile(r"^-?\d+(?:[.,]\d+)?$")

#: Document unit allowlist, longest first so ``mg/dL`` wins over a bare ``%``.
_UNIT_BY_TEXT: dict[str, DocumentUnit] = {
    "mmhg": DocumentUnit.MMHG,
    "bpm": DocumentUnit.BPM,
    "mg/dl": DocumentUnit.MG_DL,
    "g/dl": DocumentUnit.G_DL,
    "%": DocumentUnit.PERCENT,
}

#: Guard so a pathological page cannot produce unbounded candidates.
MAX_FACTS = 40


@dataclass(frozen=True, slots=True)
class CandidateFact:
    """One parsed candidate, still unverified.

    ``page_index``/``char_start``/``char_end`` address the extracted page text, so
    the value is always re-derivable from the source.
    """

    field_name: FactField
    raw_text: str
    normalized_value: str | None
    unit: str | None
    page_index: int
    char_start: int
    char_end: int
    quality_flags: tuple[QualityFlag, ...] = ()
    confidence: float | None = None
    #: The route that produced this page's text (``REQ-ING-02`` provenance).
    #: Defaults to the text layer because that is what an unmarked page is; the
    #: parser overwrites it per candidate from the page it actually read, so a
    #: scanned page inside a text PDF is attributed to the OCR engine, not to
    #: ``pypdf``.
    extractor: ExtractionPath = ExtractionPath.PYPDF

    def __post_init__(self) -> None:
        if self.char_end < self.char_start:
            raise ValueError("char_end must be >= char_start")
        if self.char_start < 0:
            raise ValueError("char_start must be non-negative")
        if not self.raw_text:
            raise ValueError("raw_text must not be empty")


@dataclass(slots=True)
class ParseResult:
    """The full parse outcome for one document's pages."""

    facts: list[CandidateFact] = field(default_factory=list)
    #: The synthetic patient reference printed in the document, if one was
    #: readable (``DEMO-A-001``). ``None`` means the document made no claim; it
    #: is **not** treated as agreement with the uploader (``VI-004`` semantics).
    #:
    #: This is deliberately not a ``CandidateFact``: it is document identity, not
    #: a reported measurement, so it must never be verified, corrected or mapped
    #: by a doctor. Storing it separately is what keeps "who this report is about"
    #: out of the fact-verification surface.
    document_patient_ref: str | None = None
    #: True when instruction-like text was seen. Recorded, never acted on.
    untrusted_content_detected: bool = False


def _unit_from_token(token: str) -> DocumentUnit | None:
    """Return the allowlisted unit for ``token``, or ``None`` when unsupported."""
    return _UNIT_BY_TEXT.get(token.strip().lower())


def _split_value_and_unit(raw: str) -> tuple[str, DocumentUnit | None]:
    """Split ``"13.4 g/dL"`` into ``("13.4", DocumentUnit.G_DL)``.

    A value with no trailing unit returns ``None``, which the caller turns into an
    ``ambiguous_unit`` flag rather than an assumption.
    """
    parts = raw.strip().split()
    if not parts:
        return "", None
    if len(parts) == 1:
        return parts[0], None
    # The unit is the last token; anything between value and unit is ignored
    # rather than guessed at.
    return parts[0], _unit_from_token(parts[-1])


def _normalize_number(token: str) -> str | None:
    """Return a canonical numeric string, or ``None`` when unparseable.

    Only decimal-separator unification is applied. A token such as ``1O5`` (OCR
    confusion of ``105``) is deliberately **not** repaired: guessing would
    fabricate a value.
    """
    candidate = token.strip().rstrip(".,;:")
    if not candidate:
        return None
    candidate = candidate.replace(",", ".")
    if not _NUMERIC_TOKEN.match(candidate):
        return None
    return candidate


def _looks_like_instruction(text: str) -> bool:
    """Return ``True`` when the text contains instruction-like content.

    This is a detection signal for the audit trail only. The text is stored as
    data and never parsed as an instruction, and the result never changes control
    flow (``REQ-SEC-02``, ``EXTRACTION_PROVENANCE.md`` §7).
    """
    lowered = text.lower()
    markers = (
        "ignore previous instructions",
        "ignore all previous instructions",
        "approve this",
        "disregard the above",
        "system prompt",
    )
    return any(marker in lowered for marker in markers)


def _date_fact(page: PageText) -> list[CandidateFact]:
    """Return the report-date candidate(s) for ``page``."""
    facts: list[CandidateFact] = []

    iso_match = _ISO_DATE.search(page.text)
    if iso_match is not None:
        facts.append(
            CandidateFact(
                field_name=FactField.REPORT_DATE,
                raw_text=iso_match.group(1),
                normalized_value=iso_match.group(1),
                unit=None,
                page_index=page.page_index,
                char_start=iso_match.start(1),
                char_end=iso_match.end(1),
                quality_flags=(QualityFlag.CLEAN,),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
        return facts

    slash_match = _SLASH_DATE.search(page.text)
    if slash_match is not None:
        # Two plausible calendar readings: flagged, not resolved.
        facts.append(
            CandidateFact(
                field_name=FactField.REPORT_DATE,
                raw_text=slash_match.group(1),
                normalized_value=None,
                unit=None,
                page_index=page.page_index,
                char_start=slash_match.start(1),
                char_end=slash_match.end(1),
                quality_flags=(QualityFlag.AMBIGUOUS_DATE,),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
    return facts


def _test_value_facts(page: PageText) -> list[CandidateFact]:
    """Return the test-name, value and unit candidates for ``page``."""
    facts: list[CandidateFact] = []

    for match in _TEST_VALUE.finditer(page.text):
        test_name = match.group("test").strip()
        raw_value = match.group("value").strip()
        if not test_name or not raw_value:
            continue

        # Some layouts put the value and unit on a following line; the regex is
        # deliberately conservative and simply skips what it cannot attribute.
        value_token, unit = _split_value_and_unit(raw_value)
        normalized = _normalize_number(value_token)

        flags: list[QualityFlag] = []
        if normalized is None:
            flags.append(QualityFlag.UNPARSEABLE_VALUE)
        if unit is None:
            flags.append(QualityFlag.AMBIGUOUS_UNIT)
        if not flags:
            flags.append(QualityFlag.CLEAN)

        facts.append(
            CandidateFact(
                field_name=FactField.TEST_NAME,
                raw_text=test_name,
                normalized_value=test_name,
                unit=None,
                page_index=page.page_index,
                char_start=match.start("test"),
                char_end=match.end("test"),
                quality_flags=(QualityFlag.CLEAN,),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
        facts.append(
            CandidateFact(
                field_name=FactField.VALUE,
                raw_text=value_token,
                normalized_value=normalized,
                unit=unit.value if unit is not None else None,
                page_index=page.page_index,
                char_start=match.start("value"),
                char_end=match.start("value") + len(value_token),
                quality_flags=tuple(flags),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
        if unit is not None:
            unit_offset = raw_value.rfind(unit.value)
            if unit_offset >= 0:
                facts.append(
                    CandidateFact(
                        field_name=FactField.UNIT,
                        raw_text=unit.value,
                        normalized_value=unit.value,
                        unit=unit.value,
                        page_index=page.page_index,
                        char_start=match.start("value") + unit_offset,
                        char_end=match.start("value") + unit_offset + len(unit.value),
                        quality_flags=(QualityFlag.CLEAN,),
                        confidence=page.confidence,
                        extractor=page.extractor,
                    )
                )

    return facts


def _reference_fact(page: PageText) -> list[CandidateFact]:
    """Return the optional ``reference_text`` candidate for ``page``."""
    match = _REFERENCE.search(page.text)
    if match is None:
        return []
    reference = match.group("reference").strip()
    if not reference:
        return []
    return [
        CandidateFact(
            field_name=FactField.REFERENCE_TEXT,
            raw_text=reference,
            normalized_value=reference,
            unit=None,
            page_index=page.page_index,
            char_start=match.start("reference"),
            char_end=match.end("reference"),
            quality_flags=(QualityFlag.CLEAN,),
            confidence=page.confidence,
            extractor=page.extractor,
        )
    ]


def parse_pages(pages: list[PageText]) -> ParseResult:
    """Parse every page and return the full candidate set.

    Deterministic: the same pages always produce the same ordered candidates. No
    field outside the declared five is ever produced.
    """
    result = ParseResult()

    for page in pages:
        if not page.text.strip():
            continue

        if _looks_like_instruction(page.text):
            result.untrusted_content_detected = True

        # The first readable reference wins. A document that prints two different
        # references is not one this demo can attribute, so it keeps the first and
        # the mismatch surfaces as ``VI-004`` against the uploader.
        if result.document_patient_ref is None:
            ref_match = _PATIENT_REF.search(page.text)
            if ref_match is not None:
                result.document_patient_ref = ref_match.group("ref").upper()

        for candidate in (
            *_date_fact(page),
            *_test_value_facts(page),
            *_reference_fact(page),
        ):
            if len(result.facts) >= MAX_FACTS:
                return result
            result.facts.append(candidate)

    return result


def page_text_for_span(pages: list[PageText], page_index: int) -> str:
    """Return the extracted text a span addresses, for re-resolution."""
    for page in pages:
        if page.page_index == page_index:
            return page.text
    raise KeyError(f"no extracted text for page {page_index}")


def span_is_resolvable(pages: list[PageText], fact: CandidateFact) -> bool:
    """Return ``True`` when ``fact``'s span lies inside its page's stored text."""
    try:
        text = page_text_for_span(pages, fact.page_index)
    except KeyError:
        return False
    return 0 <= fact.char_start < fact.char_end <= len(text)


__all__ = [
    "MAX_FACTS",
    "CandidateFact",
    "ParseResult",
    "page_text_for_span",
    "parse_pages",
    "span_is_resolvable",
]
