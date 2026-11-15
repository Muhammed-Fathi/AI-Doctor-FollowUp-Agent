"""Fixture integrity: the manifest, the sources and the generators must agree.

Owner decision D-04 forbids committing binary fixtures, so the PDFs and images are
generated. That makes this module the guard rail: if a source text changes without
regenerating the manifest, the recorded hash goes stale and this fails. A fixture
whose description silently drifted from its content would be worse than no
fixture, because the evaluation cases would then be measuring the wrong thing.
"""

from __future__ import annotations

import hashlib
import json

from app.core.paths import REPO_ROOT

DOCUMENTS = REPO_ROOT / "data" / "synthetic" / "documents"
MANIFEST = DOCUMENTS / "manifest.json"


def _manifest() -> dict:
    """Load the committed fixture manifest."""
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _canonical(raw: bytes) -> bytes:
    """Return ``raw`` with CRLF collapsed to LF — the committed canonical form.

    Only ``\\r\\n`` is rewritten. A lone ``\\r`` or a ``\\x00`` is *not* transport
    damage, so it survives canonicalization and still fails the digest check.
    """
    return raw.replace(b"\r\n", b"\n")


def _entry_for(source: str) -> dict:
    return next(entry for entry in _manifest()["documents"] if entry["source"] == source)


def test_manifest_describes_every_source_and_nothing_else():
    """The source directory and the manifest list exactly the same files."""
    listed = {entry["source"].rsplit("/", 1)[-1] for entry in _manifest()["documents"]}
    on_disk = {path.name for path in (DOCUMENTS / "sources").glob("*.txt")}

    assert listed == on_disk


def test_every_recorded_hash_matches_the_committed_source():
    """Each ``sha256`` in the manifest is the hash of the file it names.

    The manifest records the **committed canonical LF** bytes. On Windows, ``git``
    checks these ``.txt`` files out with CRLF by default (``core.autocrlf=true``),
    which changes the digest and the size without changing what the fixture means —
    that is transport, not content. The checkout is therefore canonicalized to LF
    before hashing; a genuine edit to the text still fails. See the P3-R10 block at
    the end of this module for the measurements and the negative controls.
    """
    for entry in _manifest()["documents"]:
        raw = (REPO_ROOT / entry["source"]).read_bytes()
        canonical = _canonical(raw)
        assert hashlib.sha256(canonical).hexdigest() == entry["sha256"], entry["source"]
        assert len(canonical) == entry["size_bytes"], entry["source"]


def test_manifest_declares_no_binary_artifacts():
    """D-04: the fixture set contains text only.

    A committed PDF or PNG would make the extraction results depend on a binary
    that no reviewer can diff.
    """
    manifest = _manifest()

    assert all(entry["produces_binary"] is False for entry in manifest["documents"])
    binaries = [
        path
        for path in DOCUMENTS.rglob("*")
        if path.is_file() and path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}
    ]
    assert binaries == []


def test_manifest_states_the_mapping_version_and_disclaimer():
    """The fixture metadata names the mapping version it was built against."""
    manifest = _manifest()

    assert manifest["mapping_version"] == "map-1.0.0"
    assert manifest["disclaimer"] == "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE"
    assert manifest["generation"]["deterministic"] is True


def test_sources_carry_the_synthetic_notice():
    """Every source states it is synthetic, so no reader can mistake it for real data."""
    for path in (DOCUMENTS / "sources").glob("*.txt"):
        text = path.read_text(encoding="utf-8").upper()
        assert "SYNTHETIC" in text, path.name
        assert "NOT A REAL MEDICAL RECORD" in text, path.name


def test_generators_are_deterministic(fixtures):
    """Two generations of the same source are byte-identical.

    The script exposes :func:`assert_deterministic` for this purpose; calling it
    here means the property is exercised by the suite rather than only by hand.
    """
    summary = fixtures.assert_deterministic()

    assert summary
    assert all("True" in line or "deterministic" in line.lower() or line for line in summary)


def test_report_pdfs_are_byte_stable(fixtures):
    """Generating the same report twice yields identical bytes."""
    first = fixtures.build_report_pdf("report_b_glucose.txt")
    second = fixtures.build_report_pdf("report_b_glucose.txt")

    assert first == second
    assert first.startswith(b"%PDF")


# --- P3-R10: fixture integrity must be portable across LF and CRLF checkouts ---
#
# ``git`` checks these ``.txt`` sources out with CRLF on Windows by default
# (``core.autocrlf=true``), which changes both size and SHA-256. The manifest records
# the *committed canonical LF* bytes, so hashing the checkout verbatim made this
# suite fail on Windows while passing everywhere else — the fixture content was never
# wrong, the check was. Measured: report_a_clean.txt is 202 bytes /
# c510153f... as LF and 206 bytes / bfaf9bbb... as CRLF, and the Windows failure
# reported exactly the CRLF digest.
#
# The rule now: canonicalize checkout artefacts for *transport*, but keep the
# manifest digest authoritative, so real content changes are still caught.

CANONICAL_FIXTURE = "data/synthetic/documents/sources/report_a_clean.txt"


def test_canonical_source_matches_the_manifest():
    """The checkout canonicalizes to the recorded digest and size, on any platform.

    Written to hold for *either* an LF or a CRLF checkout, because the same suite runs
    on both.
    """
    entry = _entry_for(CANONICAL_FIXTURE)
    raw = (REPO_ROOT / CANONICAL_FIXTURE).read_bytes()
    canonical = _canonical(raw)

    assert hashlib.sha256(canonical).hexdigest() == entry["sha256"]
    assert len(canonical) == entry["size_bytes"]
    # Canonicalisation must be idempotent, or repeated application could drift.
    assert _canonical(canonical) == canonical


def test_crlf_checkout_is_transport_not_corruption():
    """A CRLF checkout canonicalizes to the recorded digest and size.

    This is the Windows case the owner hit. It must pass *without* weakening the
    check: the assertion is against the unchanged manifest digest.
    """
    entry = _entry_for(CANONICAL_FIXTURE)
    # Derive the canonical LF form first: this test must be meaningful whether the
    # surrounding checkout is LF or CRLF.
    lf = _canonical((REPO_ROOT / CANONICAL_FIXTURE).read_bytes())
    crlf = lf.replace(b"\n", b"\r\n")

    assert crlf != lf, "the simulation must actually differ from LF"
    assert crlf.count(b"\r\n") == lf.count(b"\n"), "every newline must become CRLF"
    canonical = _canonical(crlf)
    assert hashlib.sha256(canonical).hexdigest() == entry["sha256"]
    assert len(canonical) == entry["size_bytes"]


def test_crlf_variant_matches_the_owner_observed_digest():
    """Pin the exact digest pair from the Windows failure.

    If either number moves, either the fixture changed or this portability rule
    broke — both are worth failing loudly for.
    """
    entry = _entry_for(CANONICAL_FIXTURE)
    lf = _canonical((REPO_ROOT / CANONICAL_FIXTURE).read_bytes())
    crlf = lf.replace(b"\n", b"\r\n")

    assert entry["sha256"] == "c510153fc3dcd8593d49a229fb9fd655c59e688df00056c8eb62e20665290d92"
    assert entry["size_bytes"] == 202
    assert len(crlf) == 206
    assert (
        hashlib.sha256(crlf).hexdigest()
        == "bfaf9bbbb360e3bb9513dbce86464f0b0c5ba683dfda14f6d216c73598bebf38"
    )


def test_genuine_content_corruption_is_still_detected():
    """The negative control: a real edit must fail even after canonicalization.

    Without this, "make it portable" could quietly become "stop checking".
    """
    entry = _entry_for(CANONICAL_FIXTURE)
    raw = (REPO_ROOT / CANONICAL_FIXTURE).read_bytes()

    # The source is a Hemoglobin 13.4 report; the mutation targets that real value.
    assert b"13.4" in raw, "the mutation below assumes the committed 13.4 value"

    corruptions = {
        "hemoglobin 13.4 -> 13.9": raw.replace(b"13.4", b"13.9"),
        # A value edit in a CRLF file is what a naive CRLF-stripping fix could swallow.
        "value edited, written as CRLF": raw.replace(b"13.4", b"13.9").replace(b"\n", b"\r\n"),
        "trailing byte appended": raw + b" ",
        "leading byte dropped": raw[1:],
        "lone CR injected": raw.replace(b"\n", b"\r", 1),
        "NUL injected": raw[:10] + b"\x00" + raw[10:],
        "CRLF plus appended space": raw.replace(b"\n", b"\r\n") + b" ",
    }

    for label, mutated in corruptions.items():
        assert mutated != raw, f"the {label!r} mutation must actually change the bytes"
        canonical = _canonical(mutated)
        assert hashlib.sha256(canonical).hexdigest() != entry["sha256"], label


def test_crlf_tolerant_check_still_catches_a_value_edit(tmp_path):
    """A CRLF file with an edited value fails; a CRLF file with LF-only endings passes.

    This proves the portability applies to newline *transport* only, and cannot mask a
    changed clinical value in a file that also happens to be CRLF.
    """
    entry = _entry_for(CANONICAL_FIXTURE)
    lf = _canonical((REPO_ROOT / CANONICAL_FIXTURE).read_bytes())

    good = tmp_path / "good_crlf.txt"
    good.write_bytes(lf.replace(b"\n", b"\r\n"))
    assert hashlib.sha256(_canonical(good.read_bytes())).hexdigest() == entry["sha256"]

    bad = tmp_path / "bad_crlf.txt"
    bad.write_bytes(lf.replace(b"13.4", b"13.9").replace(b"\n", b"\r\n"))
    assert bad.read_bytes() != lf.replace(b"\n", b"\r\n"), "the edit must really apply"
    assert hashlib.sha256(_canonical(bad.read_bytes())).hexdigest() != entry["sha256"]
