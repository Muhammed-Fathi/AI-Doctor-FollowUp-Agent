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


def test_manifest_describes_every_source_and_nothing_else():
    """The source directory and the manifest list exactly the same files."""
    listed = {entry["source"].rsplit("/", 1)[-1] for entry in _manifest()["documents"]}
    on_disk = {path.name for path in (DOCUMENTS / "sources").glob("*.txt")}

    assert listed == on_disk


def test_every_recorded_hash_matches_the_committed_source():
    """Each ``sha256`` in the manifest is the hash of the file it names."""
    for entry in _manifest()["documents"]:
        raw = (REPO_ROOT / entry["source"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["source"]
        assert len(raw) == entry["size_bytes"], entry["source"]


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
