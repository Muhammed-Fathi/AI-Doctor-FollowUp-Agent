"""The Windows acceptance probe must report honestly, never fabricate a pass.

`scripts/python/windows_ocr_acceptance.py` is the executable half of the owner
handoff. It runs on a machine this sandbox is not, so the one thing the suite can
and must verify here is its **honesty contract**:

* with no Tesseract engine it reports ``NOT RUN`` — never ``PASS``;
* it exits non-zero in that case, so a copy-pasted log cannot be mistaken for
  acceptance;
* it never touches the repository's runtime database or upload directory.

A helper that quietly returned ``PASS`` when it could not run would be worse than
no helper at all, because the owner would accept a phase on it.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.paths import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "python" / "windows_ocr_acceptance.py"


def _module():
    """Import the probe as a module without executing ``main``.

    The module is registered in ``sys.modules`` *before* execution, because the
    probe defines a dataclass and ``dataclasses`` resolves the owning module
    through ``sys.modules`` — a spec-only load would fail on that lookup.
    """
    name = "windows_ocr_acceptance"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_probe_exists_and_is_importable():
    """The handoff references a real file, not a command the owner must invent."""
    assert SCRIPT.is_file(), "the Windows handoff points at this script"

    module = _module()
    for gate in (
        "gate_environment",
        "gate_engine",
        "gate_ocr_live",
        "gate_ocr_corruption",
        "gate_rasterizer",
        "gate_api_ocr_upload",
    ):
        assert hasattr(module, gate), gate

    # The guard and the evidence writer are what make a failed dependency
    # survivable: without them an ImportError would abort before the JSON exists.
    assert hasattr(module, "_guarded")
    assert hasattr(module, "_git_head")


def test_environment_gate_survives_a_missing_wheel(monkeypatch, capsys):
    """A missing dependency is a structured FAIL, not a traceback.

    The reviewer's point: ``gate_environment`` used to import PIL/pytesseract/
    pypdfium2 *before* recording anything, so an import error aborted the probe and
    no evidence was produced. The evidence file is the artifact the owner hands
    back, so it must always exist.
    """
    module = _module()
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __import__

    def _blocked(name, *args, **kwargs):
        if name in {"pytesseract", "pypdfium2"}:
            raise ImportError(f"simulated missing wheel: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocked)

    results: list = []
    module.gate_environment(results)
    capsys.readouterr()

    statuses = {result.gate: result.status for result in results}
    assert statuses["ENV-01 python"] in {module.PASS, module.FAIL}
    assert statuses["ENV-02 libraries"] == module.FAIL, "a missing wheel must be a FAIL"
    missing = next(
        result.data["missing"] for result in results if result.gate == "ENV-02 libraries"
    )
    assert any("pytesseract" in entry for entry in missing)


def test_a_raising_gate_becomes_a_recorded_fail(capsys):
    """``_guarded`` converts an escape into a FAIL row and keeps going."""
    module = _module()
    results: list = []

    def _explode():
        raise RuntimeError("simulated engine crash")

    module._guarded(results, "SIMULATED", _explode)
    capsys.readouterr()

    assert len(results) == 1
    assert results[0].status == module.FAIL
    assert "simulated engine crash" in results[0].detail


def test_gold_ex_07_and_08_are_never_silently_dropped(capsys):
    """Every contract case appears in the evidence, including without an engine.

    The reviewer noted the probe claimed ``GOLD-EX-05..08`` but only enumerated
    05/06. Now 07/08 has its own row, marked ``DERIVED`` (it depends on the OCR
    gates and ING-02), and with no engine it is explicitly ``NOT RUN`` rather than
    absent.
    """
    module = _module()

    without_engine: list = []
    module.gate_ocr_live(without_engine, engine_present=False)
    capsys.readouterr()

    gates = {result.gate: result.status for result in without_engine}
    assert gates["GOLD-EX-07/08 coverage"] == module.NOT_RUN
    for gate in ("GOLD-EX-05 PNG", "GOLD-EX-06 JPEG", "OCR-LIVE-01"):
        assert gates[gate] == module.NOT_RUN

    # A DERIVED row documents the mapping and must not be counted as a failure.
    assert module.DERIVED not in {module.PASS, module.FAIL, module.NOT_RUN}


def test_a_missing_engine_is_reported_not_run_never_pass(monkeypatch, capsys):
    """No engine ⇒ ``NOT RUN``, and the process exits non-zero."""
    module = _module()
    results: list = []

    # Simulate a machine without Tesseract, whatever this sandbox has.
    from app.services.documents.ocr import OcrUnavailableError

    def _unavailable(*args, **kwargs):
        raise OcrUnavailableError("tesseract is not installed or not on PATH")

    monkeypatch.setattr("app.services.documents.ocr.resolve_engine", _unavailable)

    assert module.gate_engine(results) is None
    capsys.readouterr()

    module.gate_ocr_live(results, engine_present=False)
    module.gate_ocr_corruption(results, engine_present=False)
    module.gate_api_ocr_upload(results, engine_present=False)

    statuses = {result.gate: result.status for result in results}
    assert statuses["OCR-ENGINE"] == module.NOT_RUN
    assert statuses["GOLD-EX-05 PNG"] == module.NOT_RUN
    assert statuses["GOLD-EX-06 JPEG"] == module.NOT_RUN
    assert statuses["OCR-LIVE-01"] == module.NOT_RUN
    assert statuses["GOLD-EX-11 OCR-produced 1O5"] == module.NOT_RUN
    assert statuses["ING-02 OCR upload end-to-end"] == module.NOT_RUN
    assert module.PASS not in statuses.values(), "a gate that did not run must not pass"


def test_the_probe_exits_non_zero_when_a_gate_is_not_run(tmp_path: Path):
    """Run the script for real and assert the honest exit code.

    This is the property that makes the log usable as evidence: exit ``2`` means
    "not everything ran", and it is expected on any machine without Tesseract.
    """
    output = tmp_path / "result.json"
    environment = {
        "PATH": "/nonexistent-bin",  # make a PATH-discovered engine impossible
        "PYTHONPATH": f"{REPO_ROOT / 'backend'}{paths_separator()}{REPO_ROOT / 'scripts' / 'python'}",
    }

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(output)],
        cwd=REPO_ROOT,
        env={**environment, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert completed.returncode in {0, 2}, completed.stderr
    if completed.returncode == 2:
        assert "NOT RUN" in completed.stdout
        assert "not passed" in completed.stdout
    if output.exists():
        payload = output.read_text(encoding="utf-8")
        assert "NOT RUN" in payload or "PASS" in payload


def test_the_probe_never_points_at_the_runtime_database():
    """A read-only guarantee: the probe must not open ``data/runtime``.

    ``data/runtime`` appears in the module docstring on purpose — as a promise
    *not* to touch it — so the assertion looks at executable lines only, not at
    documentation that says the opposite of the check.
    """
    import ast

    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    code_lines = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.stmt) and not isinstance(node, ast.Expr)
    }
    executable = "\n".join(
        line for number, line in enumerate(source.splitlines(), start=1) if number in code_lines
    )

    assert "data/runtime" not in executable, (
        "the probe must not use the repository runtime database"
    )
    # All probe state lives in a temporary directory. It is created explicitly with
    # ``mkdtemp`` rather than ``TemporaryDirectory``, because the latter deletes the
    # directory before an outer ``finally`` can dispose the engine still holding the
    # SQLite file open — which fails on Windows with WinError 32.
    assert "tempfile.mkdtemp(" in source, "all probe state belongs in a temp directory"
    assert "shutil.rmtree(" in source, "the probe must remove its temporary directory"
    assert "create_app" in source, "the end-to-end gate must use an isolated app instance"


def paths_separator() -> str:
    """Return the platform path separator used by ``PYTHONPATH``."""
    import os

    return os.pathsep


@pytest.mark.parametrize("status", ["PASS", "FAIL", "NOT RUN"])
def test_status_vocabulary_is_exactly_three_words(status):
    """Evidence uses a fixed vocabulary so a log can be read without guessing."""
    module = _module()
    assert {module.PASS, module.FAIL, module.NOT_RUN} == {"PASS", "FAIL", "NOT RUN"}
    assert status in {module.PASS, module.FAIL, module.NOT_RUN}


# --- the handoff document must stay executable and path-correct ---------------

# --- W1: the R21 real-engine rejection gate -----------------------------------
#
# These tests drive ``assess_w1``, the gate's pure verdict function, and
# ``gate_r21_rejection``'s evidence collection. They deliberately do **not** mock a
# Tesseract engine and call the result Windows evidence: a mocked engine proves the
# plumbing, never the real engine. The evidence that counts is the owner's Windows
# run, and the handoff says so.


def _w1_pass_evidence():
    """Evidence describing a fully successful real-engine rejection."""
    module = _module()
    candidate = {
        "fact_id": "fact-value",
        "raw_text": "104",
        "normalized_value": "104",
        "unit": "mg/dL",
        "confidence": 0.88,
        "verification_status": "pending",
        "extractor": "tesseract",
    }
    source = {
        "verification_status": "pending",
        "raw_text": "104",
        "normalized_value": "104",
        "quality_flags": '["clean"]',
        "decision_count": 0,
        "decision": None,
    }
    decided = {
        "verification_status": "rejected",
        "raw_text": "104",
        "normalized_value": "104",
        "quality_flags": '["clean"]',
        "decision_count": 1,
        "decision": "rejected",
    }
    return module, module.W1Evidence(
        candidate=candidate,
        # The real scan yields report_date/test_name/unit/reference_text beside the
        # value, so the siblings are still pending when the value is rejected —
        # which is what makes `measurement_rejected` the correct terminal code.
        non_value_fact_count=4,
        extracted_fields=("reference_text", "test_name", "unit", "value"),
        attempts=({"path": "tesseract", "succeeded": True},),
        document_status="failed",
        failure_code="measurement_rejected",
        promoted_observations=(),
        before=source,
        after=decided,
        issues=(
            {
                "issue_type": "VI-002",
                "reason_code": "fact_unverified",
                "state": "open",
                "blocking": 1,
            },
        ),
        redecision_status=409,
        redecision_code="E_FACT_ALREADY_DECIDED",
        decision_count_after_refusal=1,
    )


def test_w1_passes_only_when_every_requirement_holds():
    """The all-green path: seven requirements, seven PASS rows, nothing else."""
    module, evidence = _w1_pass_evidence()
    rows = module.assess_w1(evidence)

    assert len(rows) == len(module.W1_CASES)
    assert [row.gate for row in rows] == [
        f"{'W1 R21 rejection'}: {name}" for name in module.W1_CASES
    ]
    assert [row.status for row in rows] == [module.PASS] * len(module.W1_CASES)


def test_w1_reports_not_run_when_the_engine_produced_no_candidate():
    """No OCR ``value`` fact ⇒ every requirement NOT RUN, never a PASS.

    This is the honest non-result the review required: nothing is invented to
    manufacture a candidate, and the absence is recorded with what was extracted.
    """
    module = _module()
    rows = module.assess_w1(
        module.W1Evidence(
            candidate=None,
            candidate_absence="the real engine produced no mappable `value` fact",
            extracted_fields=("reference_text", "test_name"),
        )
    )

    assert [row.status for row in rows] == [module.NOT_RUN] * len(module.W1_CASES)
    assert module.PASS not in {row.status for row in rows}
    assert "no mappable" in rows[0].detail


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_status", "needs_verification"),
        ("failure_code", "all_facts_rejected"),
        ("failure_code", None),
        ("promoted_observations", ("obs-1",)),
        ("redecision_status", 200),
        ("redecision_code", None),
        ("decision_count_after_refusal", 2),
        ("issues", ()),
    ],
)
def test_w1_fails_when_any_single_requirement_breaks(field, value):
    """Each requirement fails on its own, so a partial result cannot read as green."""
    module, evidence = _w1_pass_evidence()
    setattr(evidence, field, value)
    rows = module.assess_w1(evidence)

    statuses = {row.gate: row.status for row in rows}
    failing = [gate for gate, status in statuses.items() if status != module.PASS]

    assert failing, f"changing {field} must break at least one requirement"
    assert len(failing) <= 2, f"changing {field} broke {failing}, expected a targeted failure"


@pytest.mark.parametrize(
    "mutate",
    [
        # The decision rewrote the source text it decided on.
        lambda after: after.update(raw_text="105"),
        # The decision silently dropped provenance flags.
        lambda after: after.update(quality_flags='["repaired"]'),
        # The decision duplicated the append-only decision row.
        lambda after: after.update(decision_count=2),
        # The fact never reached the rejected state.
        lambda after: after.update(verification_status="verified"),
    ],
)
def test_w1_fact_immutability_is_pinned(mutate):
    """Immutability is asserted on stored values, not on a "we did not touch it" claim."""
    module, evidence = _w1_pass_evidence()
    mutate(evidence.after)
    rows = module.assess_w1(evidence)

    immutable = next(row for row in rows if row.gate.endswith("fact immutable"))
    assert immutable.status == module.FAIL


def test_w1_vi002_failure_distinguishes_resolved_from_open():
    """A *resolved* VI-002 is not the same as an open one under D-14."""
    module, evidence = _w1_pass_evidence()
    evidence.issues = (
        {
            "issue_type": "VI-002",
            "reason_code": "fact_unverified",
            "state": "resolved",
            "blocking": 1,
        },
    )
    rows = module.assess_w1(evidence)
    vi002 = next(row for row in rows if row.gate.endswith("VI-002 stays open"))
    assert vi002.status == module.FAIL


def test_w1_uses_the_mappable_glucose_fixture():
    """W1 must not rely on a measurement whose Observation could never be created.

    A hemoglobin fixture creates no Observation even if the gate wrongly passed, so
    the "no Observation" assertion would be vacuous. The gate therefore names the
    glucose report explicitly.
    """
    module = _module()
    assert module.W1_SOURCE_NAME == "report_a_glucose.txt"
    source = REPO_ROOT / "data" / "synthetic" / "documents" / "sources" / module.W1_SOURCE_NAME
    text = source.read_text(encoding="utf-8")
    assert "mg/dL" in text and "glucose" in text.lower()


def test_w1_mappability_guard_fails_a_non_mappable_fixture(monkeypatch, capsys, tmp_path):
    """A substituted non-mappable fixture is a FAIL, not a hollow PASS."""
    module = _module()
    fake_sources = tmp_path / "sources"
    fake_sources.mkdir()
    (fake_sources / module.W1_SOURCE_NAME).write_text(
        "SYNTHETIC\nTest: Hemoglobin   Value: 13.4 g/dL\n", encoding="utf-8"
    )
    monkeypatch.setattr(module, "SOURCES", fake_sources)

    results: list = []
    module.gate_r21_rejection_is_mappable(results)
    capsys.readouterr()

    assert [row.status for row in results] == [module.FAIL]
    assert "vacuous" in results[0].detail


def test_w1_reports_not_run_when_the_document_has_only_a_value_fact():
    """A value-only document cannot yield ``measurement_rejected``.

    Rejecting the sole fact makes *every* fact rejected, and the service's own rule
    classifies that as ``all_facts_rejected``. Asserting ``measurement_rejected``
    there would be a false FAIL against correct behaviour, so W1 reports the
    untestable precondition instead.
    """
    module, evidence = _w1_pass_evidence()
    evidence.non_value_fact_count = 0
    rows = module.assess_w1(evidence)

    assert [row.status for row in rows] == [module.NOT_RUN] * len(module.W1_CASES)
    assert "all_facts_rejected" in rows[0].detail
    assert module.FAIL not in {row.status for row in rows}


def test_w1_passes_when_siblings_are_still_pending():
    """The shape the real scan produces: one value plus pending siblings."""
    module, evidence = _w1_pass_evidence()
    assert evidence.non_value_fact_count > 0
    rows = module.assess_w1(evidence)
    assert [row.status for row in rows] == [module.PASS] * len(module.W1_CASES)


def test_w1_reports_not_run_without_an_engine(capsys):
    """No engine ⇒ seven NOT RUN rows naming the reason, and no PASS."""
    module = _module()
    results: list = []
    module.gate_r21_rejection(results, None)
    capsys.readouterr()

    assert len(results) == len(module.W1_CASES)
    assert {row.status for row in results} == {module.NOT_RUN}
    assert all("Tesseract" in row.detail for row in results)


def test_w1_rejects_an_unusable_candidate_that_is_not_tesseract():
    """Only a tesseract ``value`` fact with a finite positive number and unit qualifies."""
    module = _module()
    facts = [
        {
            "field_name": "value",
            "raw_text": "104",
            "normalized_value": "104",
            "unit": "mg/dL",
            "quality_flags": [],
            "evidence": {"extractor": "pypdf"},
        },
        {
            "field_name": "value",
            "raw_text": "   ",
            "normalized_value": "104",
            "unit": "mg/dL",
            "quality_flags": [],
            "evidence": {"extractor": "tesseract"},
        },
        {
            "field_name": "value",
            "raw_text": "1O4",
            "normalized_value": None,
            "unit": "mg/dL",
            "quality_flags": ["unparseable_value"],
            "evidence": {"extractor": "tesseract"},
        },
        {
            "field_name": "value",
            "raw_text": "104",
            "normalized_value": "104",
            "unit": "g/dL",
            "quality_flags": [],
            "evidence": {"extractor": "tesseract"},
        },
        {
            "field_name": "value",
            "raw_text": "104",
            "normalized_value": "104",
            "unit": "mg/dL",
            "quality_flags": ["page_missing"],
            "evidence": {"extractor": "tesseract"},
        },
        {
            "field_name": "value",
            "raw_text": "-5",
            "normalized_value": "-5",
            "unit": "mg/dL",
            "quality_flags": [],
            "evidence": {"extractor": "tesseract"},
        },
        {
            "field_name": "value",
            "raw_text": "104",
            "normalized_value": "104",
            "unit": None,
            "quality_flags": ["ambiguous_unit"],
            "evidence": {"extractor": "tesseract"},
        },
    ]
    assert module._w1_candidate(facts) is None

    good = {
        "field_name": "value",
        "raw_text": "104",
        "normalized_value": "104",
        "unit": "mg/dL",
        "quality_flags": [],
        "evidence": {"extractor": "tesseract"},
    }
    assert module._w1_candidate([*facts, good]) is good


def test_w1_mappability_guard_rejects_keywords_without_valid_mapping(monkeypatch, capsys, tmp_path):
    """Simply mentioning 'glucose' and 'mg/dL' is not enough if mapping fails."""
    module = _module()
    fake_sources = tmp_path / "sources"
    fake_sources.mkdir()
    (fake_sources / module.W1_SOURCE_NAME).write_text(
        "SYNTHETIC\nTest: Unrecognized glucose marker   Value: 104 mg/dL\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "SOURCES", fake_sources)

    results: list = []
    ok = module.gate_r21_rejection_is_mappable(results)
    capsys.readouterr()

    assert ok is False
    assert [row.status for row in results] == [module.FAIL]
    assert "vacuous" in results[0].detail


def test_w1_assess_reports_not_run_when_document_not_mapping_eligible():
    """A parseable value fact still produces NOT RUN if document mapping is blocked."""
    module, evidence = _w1_pass_evidence()
    evidence.mapping_eligible = False
    evidence.mapping_reason = "extracted facts are not mappable (unmapped_test_name)"
    rows = module.assess_w1(evidence)

    assert [row.status for row in rows] == [module.NOT_RUN] * len(module.W1_CASES)
    assert module.PASS not in {row.status for row in rows}
    assert "unmapped_test_name" in rows[0].detail


def test_w1_assess_reports_not_run_when_candidate_lacks_normalized_value():
    """Even a direct caller passing an unparseable candidate cannot manufacture PASS."""
    module, evidence = _w1_pass_evidence()
    evidence.candidate["normalized_value"] = None
    rows = module.assess_w1(evidence)

    assert [row.status for row in rows] == [module.NOT_RUN] * len(module.W1_CASES)
    assert module.PASS not in {row.status for row in rows}


def _mock_intake_ocr(monkeypatch, text: str, *, confidence: float = 0.94) -> None:
    """Install a deterministic OCR simulation for W1 plumbing regressions.

    This simulates engine output so we can verify SQLite persistence, API
    routes, mapping eligibility and cleanup here; it is never Windows evidence.
    """
    from app.services.documents import intake, ocr

    def _fake_run_ocr(image, *, tesseract_cmd, language, preprocessing):
        return ocr.OcrResult(
            text=text,
            confidence=confidence,
            tool_version="5.3.0.simulated-w1-plumbing-test",
        )

    monkeypatch.setattr(intake, "run_ocr", _fake_run_ocr)


def test_w1_runner_end_to_end_with_mocked_ocr_and_cleanup(monkeypatch, capsys):
    """Exercise ``_w1_run(engine_present=True)`` through real FastAPI/SQLite plumbing.

    Uses deterministic simulated OCR on the committed glucose source, inspects
    persisted SQLite rows before teardown, and verifies zero ``KeyError``, seven
    PASS verdicts, engine pool disposal, temp-dir removal and env restoration.
    """
    from app.core.config import reset_settings_cache
    from app.db import models
    from app.db.session import cached_engine_urls

    module = _module()
    glucose_text = (
        REPO_ROOT / "data" / "synthetic" / "documents" / "sources" / module.W1_SOURCE_NAME
    ).read_text(encoding="utf-8")
    _mock_intake_ocr(monkeypatch, glucose_text)

    sentinels = {
        "DATABASE_URL": "sqlite:///sentinel-before-w1.db",
        "APP_ENV": "test",
        "UPLOAD_DIR": "/tmp/sentinel-w1-uploads",
        "DEMO_SEED_PASSWORD": "sentinel-demo-value",
    }
    for key, value in sentinels.items():
        monkeypatch.setenv(key, value)
    reset_settings_cache()

    urls_before = cached_engine_urls()
    observed: dict = {}
    orig_teardown = module._w1_teardown

    def _inspect_and_teardown(seam: dict) -> list[str]:
        observed["tmp"] = Path(seam["tmp"])
        observed["engine"] = seam.get("engine")
        observed["database_url"] = seam["database_url"]
        with seam["session_factory"]() as session:
            doc = session.execute(select(models.Document)).scalars().one()
            facts = session.execute(select(models.ExtractedFact)).scalars().all()
            fact_ids = [f.id for f in facts]
            decisions = session.execute(select(models.FactVerification)).scalars().all()
            observations = (
                session.execute(
                    select(models.Observation).where(
                        models.Observation.source_fact_id.in_(fact_ids)
                    )
                )
                .scalars()
                .all()
            )
            issues = (
                session.execute(
                    select(models.VerificationIssue).where(
                        models.VerificationIssue.document_id == doc.id
                    )
                )
                .scalars()
                .all()
            )
            value_fact = next(f for f in facts if f.field_name == "value")
            sibling_statuses = {f.verification_status for f in facts if f.field_name != "value"}
            observed["db"] = {
                "extraction_status": doc.extraction_status,
                "failure_code": doc.failure_code,
                "value_status": value_fact.verification_status,
                "value_raw": value_fact.raw_text,
                "value_norm": value_fact.normalized_value,
                "sibling_count": len(facts) - 1,
                "sibling_statuses": sibling_statuses,
                "decision_count": len(decisions),
                "decision": decisions[0].decision if decisions else None,
                "observation_count": len(observations),
                "issues": [(i.issue_type, i.state, i.blocking) for i in issues],
            }
        return orig_teardown(seam)

    monkeypatch.setattr(module, "_w1_teardown", _inspect_and_teardown)

    results: list = []
    module._w1_run(results, engine_present=True)
    capsys.readouterr()

    assert [row.gate for row in results] == [
        f"W1 R21 rejection: {name}" for name in module.W1_CASES
    ]
    assert [row.status for row in results] == [module.PASS] * len(module.W1_CASES)
    assert all("cleanup" not in row.gate.lower() for row in results)

    assert observed["db"] == {
        "extraction_status": "failed",
        "failure_code": "measurement_rejected",
        "value_status": "rejected",
        "value_raw": "104",
        "value_norm": "104",
        "sibling_count": 4,
        "sibling_statuses": {"pending"},
        "decision_count": 1,
        "decision": "rejected",
        "observation_count": 0,
        "issues": [("VI-002", "open", 1)],
    }

    assert not observed["tmp"].exists()
    assert observed["engine"] is not None
    assert observed["engine"].pool.checkedin() == 0
    assert observed["engine"].pool.checkedout() == 0
    assert cached_engine_urls() == urls_before
    for key, value in sentinels.items():
        assert os.environ.get(key) == value


def test_w1_positive_mapping_control_verifies_same_fixture_creates_observation(
    monkeypatch, tmp_path
):
    """Control: verifying the exact same W1 document promotes a glucose Observation.

    Proves W1's 'no Observation' assertion is non-vacuous without touching golden
    fixtures or parser code.
    """
    from fastapi.testclient import TestClient

    from app.core.config import reset_settings_cache
    from app.db import models

    module = _module()
    glucose_text = (
        REPO_ROOT / "data" / "synthetic" / "documents" / "sources" / module.W1_SOURCE_NAME
    ).read_text(encoding="utf-8")
    _mock_intake_ocr(monkeypatch, glucose_text)

    saved_env = {name: os.environ.get(name) for name in module._PROBE_ENV_KEYS}
    work_tmp = tmp_path / "control"
    work_tmp.mkdir()
    seam = None
    try:
        seam = module._isolated_app(str(work_tmp))
        doctor_headers = {"Authorization": f"Bearer {seam['doctor_token']}"}
        patient_headers = {"Authorization": f"Bearer {seam['patient_token']}"}

        with TestClient(seam["app"]) as http:
            upload = http.post(
                "/api/v1/documents/upload",
                headers=patient_headers,
                files={"file": ("glucose.png", seam["image_bytes"], "image/png")},
            )
            assert upload.status_code == 202, upload.text
            document_id = upload.json()["document_id"]

            extraction = http.get(
                f"/api/v1/documents/{document_id}/extraction",
                headers=doctor_headers,
            )
            assert extraction.status_code == 200, extraction.text
            body = extraction.json()

            eligible, reason = module._w1_mapping_eligibility(body)
            assert eligible is True, reason
            assert module._w1_candidate(body["facts"]) is not None

            file_resp = http.get(
                f"/api/v1/documents/{document_id}/file",
                headers=doctor_headers,
            )
            assert file_resp.status_code == 200, file_resp.text

            for fact in body["facts"]:
                verify_body: dict[str, object] = {
                    "fact_id": fact["fact_id"],
                    "decision": "verified",
                    "reason": "control confirms glucose report promotes when verified",
                }
                if fact["field_name"] == "value":
                    verify_body["source_image_compared"] = True
                    verify_body["confirmed_value"] = fact["normalized_value"]
                    verify_body["confirmed_unit"] = fact["unit"]
                elif fact["field_name"] == "unit":
                    verify_body["source_image_compared"] = True
                    verify_body["confirmed_unit"] = fact["normalized_value"]
                verify = http.post(
                    f"/api/v1/documents/{document_id}/verify",
                    headers=doctor_headers,
                    json=verify_body,
                )
                assert verify.status_code == 200, verify.text

            after = http.get(
                f"/api/v1/documents/{document_id}/extraction",
                headers=doctor_headers,
            )
            assert after.status_code == 200, after.text
            assert after.json()["document_status"] == "verified"

        fact_ids = [fact["fact_id"] for fact in body["facts"]]
        with seam["session_factory"]() as session:
            observations = (
                session.execute(
                    select(models.Observation).where(
                        models.Observation.source_fact_id.in_(fact_ids)
                    )
                )
                .scalars()
                .all()
            )
            assert len(observations) == 1
            obs = observations[0]
            assert obs.measure_type == "glucose"
            assert obs.value == pytest.approx(104.0)
            assert obs.unit == "mg/dL"
            assert obs.source == "verified_document"
    finally:
        if seam is not None:
            seam["saved_env"] = saved_env
            seam["tmp"] = str(work_tmp)
            problems = module._w1_teardown(seam)
            assert problems == []
        else:
            for key, prev in saved_env.items():
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev
        reset_settings_cache()


@pytest.mark.parametrize(
    "label,ocr_text",
    [
        (
            "o_confusion_unparseable_value",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
            "Test: Fasting glucose     Value: 1O4 mg/dL\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
        (
            "unsupported_unit_hemoglobin",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
            "Test: Hemoglobin          Value: 13.4 g/dL\n"
            "Reference range: 12.0 - 15.5 g/dL\n",
        ),
        (
            "mangled_test_name",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
            "Test: Fasting glucase     Value: 104 mg/dL\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
        (
            "missing_unit",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
            "Test: Fasting glucose     Value: 104\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
        (
            "ambiguous_slash_report_date",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 03/11/2026\n"
            "Test: Fasting glucose     Value: 104 mg/dL\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
        (
            "unreadable_empty_value_page_missing",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-11-02\n"
            "Test: Fasting glucose     Value:\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
        (
            "patient_identity_mismatch_vi004",
            "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\n"
            "Demo Patient B            Ref: DEMO-B-001            Report date: 2026-11-02\n"
            "Test: Fasting glucose     Value: 104 mg/dL\n"
            "Reference range: 70 - 99 mg/dL\n",
        ),
    ],
)
def test_w1_runner_does_not_pass_when_ocr_produces_unmappable_output(
    monkeypatch, capsys, label, ocr_text
):
    """Damaged or unmappable OCR output never yields a vacuous W1 PASS."""
    from app.core.config import reset_settings_cache

    module = _module()
    _mock_intake_ocr(monkeypatch, ocr_text)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///sentinel-{label}.db")
    reset_settings_cache()

    results: list = []
    module._w1_run(results, engine_present=True)
    capsys.readouterr()

    assert [row.gate for row in results] == [
        f"W1 R21 rejection: {name}" for name in module.W1_CASES
    ]
    assert [row.status for row in results] == [module.NOT_RUN] * len(module.W1_CASES)
    assert module.PASS not in {row.status for row in results}
    assert all(row.data.get("extracted_facts") for row in results)


def test_w1_runner_disposes_partial_engine_and_reports_all_cases_on_seam_failure(
    monkeypatch, capsys
):
    """If ``_isolated_app`` fails after creating an engine, nothing leaks and 7 FAILs emit."""
    import app.services.seed as seed_module
    from app.core.config import reset_settings_cache
    from app.db.session import cached_engine_urls

    module = _module()
    created_engines: list = []

    import app.db.session as db_session

    orig_create_db_engine = db_session.create_db_engine

    def _spy_create_db_engine(url: str):
        engine = orig_create_db_engine(url)
        created_engines.append(engine)
        return engine

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated mid-setup seed failure")

    monkeypatch.setattr(db_session, "create_db_engine", _spy_create_db_engine)
    monkeypatch.setattr(seed_module, "seed_demo_data", _boom)

    sentinels = {
        "DATABASE_URL": "sqlite:///sentinel-partial.db",
        "APP_ENV": "test",
        "UPLOAD_DIR": "/tmp/sentinel-partial-uploads",
        "DEMO_SEED_PASSWORD": "sentinel-demo-value",
    }
    for key, value in sentinels.items():
        monkeypatch.setenv(key, value)
    reset_settings_cache()
    urls_before = cached_engine_urls()

    seen_tmp: list[Path] = []
    orig_teardown = module._w1_teardown

    def _spy_teardown(seam: dict) -> list[str]:
        seen_tmp.append(Path(seam["tmp"]))
        return orig_teardown(seam)

    monkeypatch.setattr(module, "_w1_teardown", _spy_teardown)

    results: list = []
    module._w1_run(results, engine_present=True)
    capsys.readouterr()

    assert [row.gate for row in results] == [
        f"W1 R21 rejection: {name}" for name in module.W1_CASES
    ]
    assert [row.status for row in results] == [module.FAIL] * len(module.W1_CASES)
    assert all("simulated mid-setup seed failure" in row.detail for row in results)

    assert len(created_engines) == 1
    assert created_engines[0].pool.checkedin() == 0
    assert created_engines[0].pool.checkedout() == 0
    assert cached_engine_urls() == urls_before
    assert len(seen_tmp) == 1 and not seen_tmp[0].exists()
    for key, value in sentinels.items():
        assert os.environ.get(key) == value


def test_main_emits_unique_w1_verdicts_when_fixture_is_unmappable(monkeypatch, capsys, tmp_path):
    """Failing the W1 fixture guard skips ``_w1_run`` and emits each W1 case once."""
    module = _module()
    fake_sources = tmp_path / "sources"
    fake_sources.mkdir()
    for name in ("report_a_glucose.txt", "report_b_bp_hr.txt", "report_ocr_o_confusion.txt"):
        (fake_sources / name).write_text("SYNTHETIC\nTest: Hemoglobin\n", encoding="utf-8")

    called = {"w1_run": False}
    monkeypatch.setattr(module, "SOURCES", fake_sources)
    monkeypatch.setattr(module, "gate_environment", lambda r: None)
    monkeypatch.setattr(module, "gate_engine", lambda r: None)
    monkeypatch.setattr(module, "gate_ocr_live", lambda r, engine_present: None)
    monkeypatch.setattr(module, "gate_ocr_corruption", lambda r, engine_present: None)
    monkeypatch.setattr(module, "gate_rasterizer", lambda r: None)
    monkeypatch.setattr(module, "gate_api_ocr_upload", lambda r, engine_present: None)
    monkeypatch.setattr(
        module,
        "_w1_run",
        lambda r, engine_present: called.__setitem__("w1_run", True),
    )

    out_json = tmp_path / "out.json"
    exit_code = module.main(["windows_ocr_acceptance.py", "--json", str(out_json)])
    capsys.readouterr()

    assert exit_code == 2
    assert called["w1_run"] is False
    import json

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    gates = [row["gate"] for row in payload["gates"]]
    assert gates == [f"W1 R21 rejection: {name}" for name in module.W1_CASES]
    assert len(gates) == len(set(gates))
    assert all(row["status"] == module.FAIL for row in payload["gates"])


def test_the_probe_registers_w1_as_a_gate():
    """W1 must be wired into the probe, not merely defined beside it."""
    module = _module()
    for name in ("gate_r21_rejection", "gate_r21_rejection_is_mappable", "_w1_run", "assess_w1"):
        assert hasattr(module, name), name

    # The gate names must appear in main's harness so a run cannot silently omit them.
    source = SCRIPT.read_text(encoding="utf-8")
    main_body = source[source.index("def main(argv") :]
    assert "W1 R21 rejection" in main_body
    assert "_w1_run" in main_body


HANDOFF = REPO_ROOT / "docs" / "phase-reports" / "PHASE_3_WINDOWS_ACCEPTANCE.md"


def test_handoff_uses_the_owners_real_paths():
    """The procedure must target ``E:\\DEPI``, not the author's placeholder.

    An earlier revision hard-coded ``C:\\src\\…`` paths that do not exist on the
    owner's machine; a procedure that fails on step 1 is not a handoff.
    """
    text = HANDOFF.read_text(encoding="utf-8")

    assert r"E:\DEPI\AI-Doctor-FollowUp-Agent" in text
    assert r"E:\DEPI\P3-Acceptance" in text
    assert "C:\\src" not in text and "C:/src" not in text


def test_handoff_never_touches_the_main_runtime_database():
    """It must name the main database only to assert it stays unchanged."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "data\\runtime\\app.db" in text
    # The only CommandLine mentions are read-only assertions (Get-Item / compare).
    for line in text.splitlines():
        if "app.db" in line and line.strip().startswith("&"):
            raise AssertionError(f"no executable command may consume app.db: {line!r}")
    assert "P3-Acceptance\\artifacts" in text or "temp" in text.lower()


def test_handoff_pins_the_sha_and_refuses_a_stale_fetch():
    """A detached worktree at the reviewed SHA, with an explicit mismatch guard."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "worktree add --detach" in text
    assert "FETCH_HEAD" in text
    assert "Refusing to proceed" in text
    assert "git -C $Main worktree add" in text


def test_handoff_uses_repo_native_setup_with_frontend():
    """``setup.ps1 -SkipDatabase`` must not also skip the frontend.

    Skipping it would leave ``node_modules`` absent, and the full ``test_all.ps1``
    gate would then correctly FAIL the frontend checks — a false negative caused by
    the procedure, not by the code.
    """
    text = HANDOFF.read_text(encoding="utf-8")

    assert "-SkipDatabase" in text
    setup_call = [
        line for line in text.splitlines() if "setup.ps1" in line and "-SkipDatabase" in line
    ]
    assert setup_call, "the handoff must invoke setup.ps1"
    for line in text.splitlines():
        if "setup.ps1" in line and "-SkipFrontend" in line and "-SkipDatabase" in line:
            raise AssertionError(f"setup.ps1 must not skip the frontend: {line!r}")
    assert "test_all.ps1" in text


def test_handoff_distinguishes_derived_from_executed_cases():
    """GOLD-EX-07/08 must be documented, not claimed as independently executed."""
    text = HANDOFF.read_text(encoding="utf-8")

    assert "GOLD-EX-07/08 coverage" in text
    assert "DERIVED" in text
    assert "never claimed as an independent pass" in text


def test_the_owner_comment_is_the_cited_authorization_source():
    """D-14 must cite the owner's comment, not the independent review.

    The owner asked explicitly that the ledger and report reference *their*
    authorization comment rather than a technical review, which is not an approval.
    This pins the distinction so it cannot drift back.
    """
    owner_url = (
        "https://github.com/Muhammed-Fathi/AI-Doctor-FollowUp-Agent/pull/10#issuecomment-6900700171"
    )
    review_id = "5912501268"

    for relative in ("docs/roadmap/PHASE_PROGRESS.md", "docs/phase-reports/PHASE_3_REPORT.md"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert owner_url in text, f"{relative} must cite the owner's authorization comment"
        # The review may only appear as context/prior finding, never as approval.
        assert "review `5912501268`" not in text or "not" in text, relative
        for line in text.splitlines():
            if review_id in line:
                # Strip markdown emphasis so "**not** the authorization" still matches.
                plain = line.lower().replace("*", "").replace("`", "")
                assert any(
                    marker in plain
                    for marker in (
                        "not the authorization",
                        "not an approval",
                        "not cited as one",
                        "raised by",
                        "prior context",
                        "pullrequestreview",
                    )
                ), f"{relative}: review must not be presented as approval: {line!r}"


def _collect(subdir: str) -> dict[str, int]:
    """Return real pytest collection counts under ``subdir``, keyed by file name.

    Shelling out to pytest is slower than counting ``def test_`` lines, but it is the
    only way to stay correct as parametrization changes. A hard-coded count rots the
    moment someone adds a test — which is exactly how the handoff drifted to
    ``522 (P3: 139)`` in the first place.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            subdir,
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    counts: dict[str, int] = {}
    for line in completed.stdout.splitlines():
        # Format: "backend/tests/p3/test_x.py: 12"
        name, _, count = line.partition(": ")
        if name.startswith(f"{subdir}/") and name.endswith(".py") and count.strip().isdigit():
            counts[name.rsplit("/", 1)[-1]] = int(count)
    assert counts, f"could not parse collection output:\n{completed.stdout[-2000:]}"
    return counts


def _collected_counts() -> dict[str, int]:
    """Per-file P3 collection counts (the handoff's per-suite table)."""
    return _collect("backend/tests/p3")


def _whole_backend_total() -> int:
    """Total collected backend tests, including suites outside ``p3``.

    The per-file table above only covers ``p3``, so the handoff's *headline*
    figure — the number the owner compares against `test_all.ps1` output — was
    never gated and drifted to 661 while the truth was 663. Collect the whole
    tree so a test added anywhere is reflected in the handoff.
    """
    return sum(_collect("backend/tests").values())


def test_handoff_test_count_matches_the_suite_it_describes():
    """The counts quoted in the handoff must match real pytest collection.

    A handoff that tells the owner to expect the wrong number invites a false FAIL.
    An earlier revision said ``522 passed (P3: 139)`` when the truth was 529/146, so
    the figures are now derived from collection rather than trusted.
    """
    text = HANDOFF.read_text(encoding="utf-8")
    counts = _collected_counts()
    p3_total = sum(counts.values())

    assert f"**{p3_total}**" in text, f"handoff should quote the P3 total {p3_total}"

    # The headline "whole backend" figure must also be real, not remembered.
    backend_total = _whole_backend_total()
    assert f"**{backend_total} passed**" in text, (
        f"handoff should quote the whole-backend total {backend_total}"
    )

    # The two figures must also agree *within the sentence* that pairs them, so
    # the headline number and the P3 number cannot drift apart independently.
    # Collapse the wrapped prose first: the sentence breaks across Markdown lines,
    # and the pairing is what matters, not where the newline fell.
    paired = f"**{backend_total} passed**, of which **{p3_total}** are the P3 suite"
    assert paired in " ".join(text.split()), f"handoff should pair {backend_total} with {p3_total}"

    for name, count in counts.items():
        row = next((line for line in text.splitlines() if name in line), None)
        assert row is not None, f"handoff table is missing a row for {name}"
        assert f"| {count} |" in row, f"{name}: expected {count} in {row!r}"

    # And the stale pair must never come back.
    assert "522 passed" not in text and "P3: 139" not in text
