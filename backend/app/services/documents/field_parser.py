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
from datetime import datetime

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

#: A bare ``Value:`` label, used only to detect a measurement the lab-line
#: grammar above could not attribute (P3-R17).
_VALUE_LABEL = re.compile(r"value\s*:", re.IGNORECASE)

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
    #: The **single** synthetic patient reference printed in the document, if one
    #: was readable (``DEMO-A-001``). ``None`` means either that the document made
    #: no claim, or that it made **more than one conflicting claim** — the two are
    #: indistinguishable downstream on purpose, because both mean "this document
    #: cannot be attributed". ``None`` is **not** treated as agreement with the
    #: uploader (``VI-004`` semantics).
    #:
    #: This is deliberately not a ``CandidateFact``: it is document identity, not
    #: a reported measurement, so it must never be verified, corrected or mapped
    #: by a doctor. Storing it separately is what keeps "who this report is about"
    #: out of the fact-verification surface.
    document_patient_ref: str | None = None
    #: **R07:** every distinct reference printed anywhere in the document, in
    #: first-seen order. ``len(...) > 1`` is an identity conflict that must fail
    #: closed; it is recorded rather than discarded so the reason is inspectable.
    patient_refs_seen: tuple[str, ...] = ()

    @property
    def identity_is_ambiguous(self) -> bool:
        """Return ``True`` when the document printed conflicting references.

        A document that names two different patients is not "the first one wins":
        it is a document this demo cannot attribute at all, and it must raise
        ``VI-004`` whatever order the references appear in (``VI-03``).
        """
        return len(self.patient_refs_seen) > 1

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


def _trimmed_bounded_span(
    raw_segment: str, group_start: int, *, max_len: int = 300
) -> tuple[str, int, int]:
    """Return ``(trimmed_text, char_start, char_end)`` anchored to the same slice."""
    stripped = raw_segment.strip()
    if not stripped:
        return "", group_start, group_start
    leading = len(raw_segment) - len(raw_segment.lstrip())
    bounded = stripped[:max_len]
    start = group_start + leading
    return bounded, start, start + len(bounded)


def _test_value_facts(page: PageText) -> list[CandidateFact]:
    """Return the test-name, value and unit candidates for ``page``."""
    facts: list[CandidateFact] = []

    for match in _TEST_VALUE.finditer(page.text):
        test_raw = match.group("test")
        value_raw = match.group("value")
        test_name, test_start, test_end = _trimmed_bounded_span(test_raw, match.start("test"))
        raw_value, val_group_start, _ = _trimmed_bounded_span(
            value_raw, match.start("value"), max_len=len(value_raw)
        )
        if not test_name or not raw_value:
            continue

        # Some layouts put the value and unit on a following line; the regex is
        # deliberately conservative and simply skips what it cannot attribute.
        value_token, unit = _split_value_and_unit(raw_value)
        bounded_value = value_token[:300]
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
                char_start=test_start,
                char_end=test_end,
                quality_flags=(QualityFlag.CLEAN,),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
        facts.append(
            CandidateFact(
                field_name=FactField.VALUE,
                raw_text=bounded_value,
                normalized_value=normalized,
                unit=unit.value if unit is not None else None,
                page_index=page.page_index,
                char_start=val_group_start,
                char_end=val_group_start + len(bounded_value),
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
                        char_start=val_group_start + unit_offset,
                        char_end=val_group_start + unit_offset + len(unit.value),
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
    reference, ref_start, ref_end = _trimmed_bounded_span(
        match.group("reference"), match.start("reference")
    )
    if not reference:
        return []
    return [
        CandidateFact(
            field_name=FactField.REFERENCE_TEXT,
            raw_text=reference,
            normalized_value=reference,
            unit=None,
            page_index=page.page_index,
            char_start=ref_start,
            char_end=ref_end,
            quality_flags=(QualityFlag.CLEAN,),
            confidence=page.confidence,
            extractor=page.extractor,
        )
    ]


def _unattributed_value_facts(
    page: PageText, matched_spans: list[tuple[int, int]]
) -> list[CandidateFact]:
    """Return a ``page_missing``-flagged value candidate for an unread measurement.

    **P3-R17.** The lab-line grammar (``_TEST_VALUE``) requires a two-space column
    gap, because that is what distinguishes a lab row from prose. When OCR
    collapses the gap — or damages the ``Value:`` label — the line does not match
    and *nothing at all* is produced for it. The engine's plausible value was then
    invisible to every downstream blocker, because each of those is derived from a
    fact, and a dropped line leaves no fact. Measured consequence on the owner's
    real Windows OCR at ``1b17a9a``: a document whose image printed a measurement
    could reach ``verified`` after only its date and reference range were
    approved.

    This function keeps the line as evidence instead of discarding it. The
    candidate carries:

    * ``field_name=value`` and ``normalized_value=None`` — no number is invented;
    * ``raw_text`` = the literal token after the label (bounded), so the doctor
      sees exactly what the page produced;
    * ``QualityFlag.PAGE_MISSING`` — the closed-enum flag documented as *"OCR
      yielded nothing usable for the page / blocking if the field was expected
      there"*. That documentation is exactly this situation, and the flag was
      previously unreachable dead code.

    It is emitted only when the page carries a ``Value:`` label that the lab-line
    grammar did not already attribute, so a report that never declared a
    measurement (title and reference range only) is left genuinely document-only.
    Every golden fixture has zero such lines, so this changes no existing parse.
    """
    facts: list[CandidateFact] = []
    for label in _VALUE_LABEL.finditer(page.text):
        if any(start <= label.start() < end for start, end in matched_spans):
            continue
        line_end = page.text.find("\n", label.end())
        line_end = len(page.text) if line_end < 0 else line_end

        # **R18-A.** The span and ``raw_text`` are computed from the *same* slice.
        # The previous version stripped the token but offset from ``label.end()``,
        # so the emitted span kept the leading whitespace and lost the tail: for the
        # owner's real line the fact claimed ``'105 mg/dL'`` while its own span
        # resolved to ``' 105 mg/d'``. ``EXTRACTION_PROVENANCE.md`` §3/§5 requires
        # the span to be the exact source slice, and ``span_is_resolvable()`` only
        # checked bounds, so nothing caught the drift. Compute the trimmed range
        # first, then derive both fields from it.
        raw_segment = page.text[label.end() : line_end]
        segment = raw_segment.strip()
        if segment:
            # ``lstrip`` offset: where the token itself begins in the page text.
            value_start = label.end() + (len(raw_segment) - len(raw_segment.lstrip()))
            # Bounded evidence, and the span is bounded to exactly that length so a
            # >120-char token still resolves to its own recorded ``raw_text``.
            raw_text = segment[:120]
            value_end = value_start + len(raw_text)
        else:
            # **R18-B.** A bare ``Value:`` label is a *declaration*, not an absence:
            # the document says a measurement exists and OCR read nothing after it.
            # Skipping the line left no evidence, so no blocker could be raised and
            # approving only the date and reference range reached ``verified``.
            # The label itself is preserved as the literal evidence — non-empty,
            # exact, and it fabricates no number.
            value_start = label.start()
            raw_text = page.text[label.start() : label.end()]
            value_end = label.end()

        facts.append(
            CandidateFact(
                field_name=FactField.VALUE,
                raw_text=raw_text,
                # Never repaired, never guessed: the page's own characters remain
                # the only evidence and no numeric meaning is asserted.
                normalized_value=None,
                unit=None,
                page_index=page.page_index,
                char_start=value_start,
                char_end=value_end,
                quality_flags=(QualityFlag.PAGE_MISSING,),
                confidence=page.confidence,
                extractor=page.extractor,
            )
        )
    return facts


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

        # **R07:** collect *every* distinct reference, across lines and pages.
        # Taking only the first match silently reduced an ``A then B`` document to
        # patient A, so the mismatch never surfaced. A document that prints two
        # different references is one this demo cannot attribute, so it ends with
        # ``document_patient_ref = None`` and raises ``VI-004`` regardless of the
        # order the references appear in. No reference is preferred or guessed.
        for ref_match in _PATIENT_REF.finditer(page.text):
            seen = ref_match.group("ref").upper()
            if seen not in result.patient_refs_seen:
                result.patient_refs_seen = (*result.patient_refs_seen, seen)

        matched_spans = [(m.start(), m.end()) for m in _TEST_VALUE.finditer(page.text)]
        for candidate in (
            *_date_fact(page),
            *_test_value_facts(page),
            *_unattributed_value_facts(page, matched_spans),
            *_reference_fact(page),
        ):
            if len(result.facts) >= MAX_FACTS:
                _finalize_identity(result)
                return result
            result.facts.append(candidate)

    _finalize_identity(result)
    return result


def _finalize_identity(result: ParseResult) -> None:
    """Resolve the document's identity claim from every reference seen (R07).

    Exactly one distinct reference -> that reference. Zero -> no claim. Two or
    more -> ``None`` (unattributable), which ``evaluate_identity`` turns into
    ``VI-004``. There is no "first wins" and no majority vote: identity is not
    something this demo may guess.
    """
    if len(result.patient_refs_seen) == 1:
        result.document_patient_ref = result.patient_refs_seen[0]
    else:
        result.document_patient_ref = None


#: ``YYYY-MM-DD`` shape, shared by the parser and by correction validation so the
#: two cannot drift apart into different date grammars.
_ISO_DATE_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_corrected_value(field_name: str, value: str) -> str | None:
    """Return the admissible canonical form of a doctor-supplied correction.

    **P3-R17 (P1).** ``VerifyRequest.corrected_value`` is a bounded string and the
    route only refused an empty one, so ``'   '``, ``'abc'`` and ``'nan'`` were all
    accepted as verified measurements. Validation is deliberately **per field**
    rather than one global numeric rule, because a date and a reference range are
    not numbers:

    * ``value`` -> must survive the parser's own :func:`_normalize_number`, which
      only unifies the decimal separator and refuses everything else. The doctor's
      correction goes through the same gate as the extractor's reading, so a
      correction cannot assert a value the parser itself would reject.
    * ``unit`` -> must be in the closed :class:`DocumentUnit` list.
    * ``report_date`` -> ``YYYY-MM-DD``; the calendar validity is checked here
      because ``2026-13-45`` is well shaped and still not a date.
    * ``test_name`` / ``reference_text`` -> free text, but must not be blank and
      must not contain control characters.

    Returns ``None`` when the input is inadmissible. It never repairs: repairing
    is exactly what ``_normalize_number`` refuses to do for ``1O5``.
    """
    if field_name == FactField.VALUE.value:
        return _normalize_number(value)
    if field_name == FactField.UNIT.value:
        try:
            return DocumentUnit(value.strip()).value
        except ValueError:
            return None
    if field_name == FactField.REPORT_DATE.value:
        candidate = value.strip()
        if not _ISO_DATE_SHAPE.match(candidate):
            return None
        try:
            datetime.strptime(candidate, "%Y-%m-%d")
        except ValueError:
            return None
        return candidate
    # ``test_name`` / ``reference_text``: human text, still bounded and printable.
    candidate = value.strip()
    if not candidate:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    return candidate


def page_text_for_span(pages: list[PageText], page_index: int) -> str:
    """Return the extracted text a span addresses, for re-resolution."""
    for page in pages:
        if page.page_index == page_index:
            return page.text
    raise KeyError(f"no extracted text for page {page_index}")


def span_is_resolvable(pages: list[PageText], fact: CandidateFact) -> bool:
    """Return ``True`` when ``fact``'s span matches the exact page substring."""
    try:
        text = page_text_for_span(pages, fact.page_index)
    except KeyError:
        return False
    bounded_raw = fact.raw_text[:300]
    return (
        0 <= fact.char_start < fact.char_end <= len(text)
        and text[fact.char_start : fact.char_end] == bounded_raw
    )


__all__ = [
    "MAX_FACTS",
    "CandidateFact",
    "ParseResult",
    "normalize_corrected_value",
    "page_text_for_span",
    "parse_pages",
    "span_is_resolvable",
]
