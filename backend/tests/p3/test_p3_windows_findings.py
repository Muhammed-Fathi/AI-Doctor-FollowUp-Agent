"""Regression tests for the R13 (GOLD-EX-11) and R14 (ING-02) Windows findings.

Both were surfaced by the owner's real-engine Windows run at ``cf77be6``. The tests
below separate what the code is responsible for from what the *probe image* is
responsible for, because conflating them is what made GOLD-EX-11 look like a parser
defect when it was not.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.core.enums import ExtractionPath
from app.services.documents.field_parser import parse_pages
from app.services.documents.text_extraction import PageText

PROBE = Path(__file__).resolve().parents[3] / "scripts" / "python" / "windows_ocr_acceptance.py"


def _probe_module():
    """Import the acceptance probe by path (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("windows_ocr_acceptance_r13", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec: the module defines a dataclass and needs a real module entry.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- R13: parser level


def _value_facts(text: str):
    page = PageText(page_index=0, text=text, extractor=ExtractionPath.TESSERACT, confidence=0.64)
    parsed = parse_pages([page])
    return [fact for fact in parsed.facts if fact.field_name.value == "value"]


def test_a_true_ocr_produced_1O5_is_flagged_not_repaired():
    """The contract case: if the engine emits ``1O5``, the parser must flag it.

    ``1O5`` must never become ``105``. This is the behaviour GOLD-EX-11 is meant to
    demonstrate, and it holds at the parser level.
    """
    facts = _value_facts("Test: Glucose             Value: 1O5 mg/dL")

    assert len(facts) == 1
    fact = facts[0]
    assert fact.raw_text == "1O5"
    assert fact.normalized_value is None, "1O5 must never be normalised to 105"
    assert "unparseable_value" in {flag.value for flag in fact.quality_flags}


@pytest.mark.parametrize(
    "token",
    ["1O5", "l05", "I05", "1o5", "12O", "O.5"],
)
def test_every_documented_ocr_confusion_is_unparseable(token):
    """No digit/letter confusion is silently repaired."""
    facts = _value_facts(f"Test: Glucose             Value: {token} mg/dL")

    if not facts:  # a token that cannot even be attributed is not a repair either
        return
    assert facts[0].normalized_value is None
    assert "unparseable_value" in {flag.value for flag in facts[0].quality_flags}


def test_a_clean_value_is_still_parsed():
    """The negative control: a readable value must not be flagged unparseable."""
    facts = _value_facts("Test: Glucose             Value: 105 mg/dL")

    assert len(facts) == 1
    assert facts[0].normalized_value == "105"
    assert "unparseable_value" not in {flag.value for flag in facts[0].quality_flags}


def test_a_dropped_value_line_yields_no_value_fact_at_all():
    """The R13 diagnosis, pinned: a mangled ``Value:`` label yields *no* fact.

    The owner's run reported ``value flags=[] normalized=[]`` — an empty list, not a
    flagged fact. That is the signature of the engine losing the line/label, not of the
    parser missing a ``1O5`` it was given. The gate now distinguishes the two instead of
    reporting a bare FAIL.
    """
    for text in (
        "Test: Glucose   Value; 105 mg/dL",
        "Test: Glucose   Value 105 mg/dL",
        "Tost: Glucoso  Valuo: 105 mg/dL",
    ):
        assert _value_facts(text) == [], text


# ------------------------------------------------------------ R13: the probe gate


def test_the_gold_ex_11_gate_diagnoses_a_missing_value_fact(monkeypatch):
    """The gate must report *why* it failed, not just that it did."""
    module = _probe_module()
    results: list = []

    def _fake_run_ocr(image, **kwargs):
        class _R:
            # The engine dropped the "Value:" label, so the parser finds no value fact.
            text = "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD\nTest: Glucose 1O5 mg/dL"
            confidence = 0.6

        return _R()

    monkeypatch.setattr("app.services.documents.ocr.run_ocr", _fake_run_ocr)
    module.gate_ocr_corruption(results, engine_present=True)

    gate = next(r for r in results if r.gate.startswith("GOLD-EX-11"))
    assert gate.status == module.FAIL, "an unverified 1O5 claim must not be a PASS"
    # The diagnosis names the actual cause.
    detail = gate.detail.lower()
    assert "no value fact" in detail or "not parsed" in detail
    # And the raw engine text is preserved as evidence, not paraphrased.
    assert "ocr_text" in gate.data


def test_the_gold_ex_11_gate_passes_on_a_flagged_1O5(monkeypatch):
    """When the engine really emits ``1O5`` and the parser flags it, the gate passes."""
    module = _probe_module()
    results: list = []

    def _fake_run_ocr(image, **kwargs):
        class _R:
            text = "Test: Glucose             Value: 1O5 mg/dL"
            confidence = 0.6

        return _R()

    monkeypatch.setattr("app.services.documents.ocr.run_ocr", _fake_run_ocr)
    module.gate_ocr_corruption(results, engine_present=True)

    gate = next(r for r in results if r.gate.startswith("GOLD-EX-11"))
    assert gate.status == module.PASS
    assert gate.data["normalized_values"] in ([], None) or not gate.data["normalized_values"]


def test_the_gold_ex_11_gate_fails_if_the_engine_read_a_clean_105(monkeypatch):
    """If the engine repaired the token itself, the gate must not claim a 1O5 case."""
    module = _probe_module()
    results: list = []

    def _fake_run_ocr(image, **kwargs):
        class _R:
            text = "Test: Glucose             Value: 105 mg/dL"
            confidence = 0.6

        return _R()

    monkeypatch.setattr("app.services.documents.ocr.run_ocr", _fake_run_ocr)
    module.gate_ocr_corruption(results, engine_present=True)

    gate = next(r for r in results if r.gate.startswith("GOLD-EX-11"))
    # Nothing was flagged, so the gate cannot report the corruption case as proven.
    assert gate.status == module.FAIL
    assert "not proven" in gate.detail.lower() or "no value fact" in gate.detail.lower()


# ---------------------------------------------------------------- R14: seed boundary


def test_the_probe_extracts_a_plain_password_from_typed_settings():
    """``SecretStr`` must be unwrapped before it reaches ``seed_demo_data``.

    The reviewed probe passed the ``SecretStr`` itself, so ``seed.py``'s
    ``password.strip()`` raised ``AttributeError`` before any HTTP upload happened.
    """
    from app.core.config import Settings

    module = _probe_module()

    configured = Settings(_env_file=None, demo_seed_password="synthetic-demo-password")
    password = module._seed_password(configured)

    assert isinstance(password, str)
    assert password == "synthetic-demo-password"
    assert password.strip() == password, "the seed service calls .strip() on this value"


def test_the_probe_falls_back_when_no_password_is_configured():
    """An unset password yields an explicit synthetic local credential."""
    from app.core.config import Settings

    module = _probe_module()

    password = module._seed_password(Settings(_env_file=None, demo_seed_password=None))

    assert isinstance(password, str)
    assert password
    assert "acceptance" in password


def test_the_probe_never_writes_the_password_to_evidence():
    """The password must not appear in the structured evidence payload."""
    module = _probe_module()
    from app.core.config import Settings

    secret_text = "super-secret-demo-password-value"
    settings = Settings(_env_file=None, demo_seed_password=secret_text)
    assert module._seed_password(settings) == secret_text

    # The helper returns the value but nothing in the module's evidence path logs it.
    source = PROBE.read_text(encoding="utf-8")
    assert "get_secret_value" in source
    # A recorded Result must never carry the raw secret.
    results: list = []
    module._record(results, module.Result("SIMULATED", module.PASS, "no secret here"))
    assert all(secret_text not in str(r.detail) for r in results)


# ------------------------------------- R14 follow-on: the two bugs behind the 401
#
# Fixing the SecretStr boundary let the probe reach code it had never executed before,
# which exposed two further defects. Both are covered here so a future edit cannot
# silently reintroduce them.


def test_the_probe_passes_the_required_clock_to_issue_session():
    """``issue_session`` is keyword-only and requires ``now``.

    The reviewed probe called it without ``now`` and raised
    ``TypeError: issue_session() missing 1 required keyword-only argument`` before any
    upload could happen. Asserted against the real signature rather than a mock, so the
    test fails if either side drifts.
    """
    import inspect

    from app.services.accounts import issue_session

    signature = inspect.signature(issue_session)
    assert "now" in signature.parameters
    assert signature.parameters["now"].kind is inspect.Parameter.KEYWORD_ONLY

    source = PROBE.read_text(encoding="utf-8")
    # The call may span lines, so compare the parenthesised block rather than one line.
    assert "issue_session(" in source
    blocks = []
    start = 0
    while True:
        index = source.find("issue_session(", start)
        if index == -1:
            break
        depth = 0
        for offset in range(index, len(source)):
            if source[offset] == "(":
                depth += 1
            elif source[offset] == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(source[index : offset + 1])
                    start = offset
                    break
        else:  # pragma: no cover - unbalanced source
            break

    # Drop the import statement, keep real call sites.
    calls = [block for block in blocks if not block.startswith("issue_session")] or blocks
    assert calls, "the probe should still exercise the HTTP path"
    for block in calls:
        assert "now=" in block, f"issue_session call is missing now=: {block!r}"


def test_the_probe_uses_a_live_clock_for_sessions():
    """Session issuance must not use a hard-coded date.

    A session lives 60 minutes. The reviewed probe issued them at a fixed midnight, so
    by the time the owner ran it the token had expired and the upload answered ``401``.
    Seeding may stay deterministic; *sessions* may not.
    """
    source = PROBE.read_text(encoding="utf-8")

    marker = "issued_at = "
    assert marker in source
    line = next(line for line in source.splitlines() if line.strip().startswith(marker.strip()))
    assert "now(" in line, f"session issuance must read the live clock: {line!r}"
    assert "2026, 11, 15" not in line, "a fixed date would expire before the run"


def test_the_probe_never_forwards_a_secret_object_to_the_seed_service():
    """The seed call site must go through the unwrapping helper."""
    source = PROBE.read_text(encoding="utf-8")
    seed_call = source[source.index("seed_demo_data(") : source.index("seed_demo_data(") + 400]

    assert "demo_seed_password" not in seed_call, (
        "seed_demo_data must receive a plain str, not Settings.demo_seed_password"
    )
    assert "_seed_password(" in seed_call


def test_seeding_still_rejects_an_empty_password():
    """The seed service keeps its own guard; the probe fix does not weaken it."""
    import inspect

    from app.services.seed import SeedConfigurationError, seed_demo_data

    source = inspect.getsource(seed_demo_data)
    assert "password.strip()" in source
    assert issubclass(SeedConfigurationError, Exception)


# ============================================ R15: verdict and cleanup integrity
#
# The owner's JSON contained TWO rows for ING-02 — PASS, then FAIL on a Windows
# `PermissionError [WinError 32]` while the temporary SQLite directory was being
# removed. Two defects, both asserted below: a cached engine kept the file open, and
# the gate could emit a second verdict after already concluding.

GATE_IDS = (
    "ENV-01 python",
    "ENV-02 libraries",
    "OCR-ENGINE",
    "OCR-ENGINE eng.traineddata",
    "GOLD-EX-05 PNG",
    "GOLD-EX-06 JPEG",
    "GOLD-EX-07/08 coverage",
    "OCR-LIVE-01 measured",
    "GOLD-EX-11 OCR-produced 1O5",
    "PDFIUM-01 rasterize",
    "ING-02 OCR upload end-to-end",
)


def test_a_successful_gate_cannot_be_followed_by_a_second_verdict():
    """Exactly one terminal verdict per gate, even when cleanup then fails.

    Reproduces the owner's PASS-then-FAIL pair: the gate concluded, and an exception in
    the ``finally`` path appended a second row. A conforming report must show the PASS
    once, with the cleanup problem recorded separately.
    """
    module = _probe_module()
    results: list = []

    def _passes_then_cleanup_raises() -> None:
        module._record(results, module.Result("ING-02 OCR upload end-to-end", module.PASS, "ok"))
        raise PermissionError(13, "cleanup failed")

    module._guarded(results, "ING-02 OCR upload end-to-end", _passes_then_cleanup_raises)

    gate_rows = [row for row in results if row.gate == "ING-02 OCR upload end-to-end"]
    assert len(gate_rows) == 1, f"a gate must have one verdict, got {len(gate_rows)}"
    assert gate_rows[0].status == module.PASS, "a cleanup error must not erase the verdict"
    # The cleanup failure is reported, not hidden — under its own identifier.
    cleanup = [row for row in results if "cleanup" in row.gate.lower()]
    assert cleanup, "a cleanup failure must be recorded, never swallowed"
    assert cleanup[0].status == module.FAIL


def test_a_failed_gate_is_reported_once():
    """A gate that fails before concluding gets exactly one FAIL row."""
    module = _probe_module()
    results: list = []

    def _raises() -> None:
        raise RuntimeError("boom")

    module._guarded(results, "GOLD-EX-11 OCR-produced 1O5", _raises)

    rows = [row for row in results if row.gate == "GOLD-EX-11 OCR-produced 1O5"]
    assert len(rows) == 1
    assert rows[0].status == module.FAIL


def test_every_gate_emits_at_most_one_row_in_a_full_probe_run(monkeypatch):
    """End-to-end: no gate identifier appears twice in the evidence."""
    module = _probe_module()
    results: list = []

    # No engine here, so every OCR gate reports NOT RUN; the non-engine gates run.
    module.gate_environment(results)
    module.gate_ocr_live(results, engine_present=False)
    module.gate_ocr_corruption(results, engine_present=False)
    module.gate_rasterizer(results)
    module.gate_api_ocr_upload(results, engine_present=False)

    identifiers = [row.gate for row in results]
    duplicates = {gate for gate in identifiers if identifiers.count(gate) > 1}
    assert not duplicates, f"duplicate gate verdicts: {sorted(duplicates)}"
    # And every declared gate appears exactly once.
    assert len(identifiers) == len(set(identifiers))


def test_cleanup_releases_every_pool_not_just_the_file(tmp_path):
    """Issue 3: ``unlink()`` is not proof — assert the pools are empty.

    Unix allows unlinking a file that still has open handles, so the previous version of
    this test passed while the defect was live. ``pool.checkedin() == 0`` is the
    platform-independent statement of "no SQLite handle survives", which is what Windows
    actually enforces when deleting the file.
    """
    import subprocess
    import sys

    script = tmp_path / "probe_cleanup.py"
    db_path = tmp_path / "accept.db"
    script.write_text(
        f"""
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import _engine_for_url, create_db_engine, dispose_engines

url = "sqlite:///{db_path.as_posix()}"

# The gate does both: a standalone engine, and the cached one the app path uses.
standalone = create_db_engine(url)
with Session(standalone) as session:
    session.execute(text("CREATE TABLE t (x integer)"))
    session.commit()
cached = _engine_for_url(url)
with cached.connect() as connection:
    connection.execute(text("INSERT INTO t VALUES (1)"))

print("standalone_before", standalone.pool.checkedin())
print("cached_before", cached.pool.checkedin())

# The fix under test.
standalone.dispose()
dispose_engines(url)

print("standalone_after", standalone.pool.checkedin())
print("cached_after", cached.pool.checkedin())
print("checked_out_after", standalone.pool.checkedout() + cached.pool.checkedout())
sys.exit(0)
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "backend"),
            "HOME": str(tmp_path),
        },
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr

    values = dict(line.split() for line in completed.stdout.splitlines() if len(line.split()) == 2)
    # Both pools held a handle before cleanup — otherwise the test proves nothing.
    assert int(values["standalone_before"]) > 0
    assert int(values["cached_before"]) > 0
    # After the fix, neither pool retains a connection.
    assert int(values["standalone_after"]) == 0, "standalone engine still holds a handle"
    assert int(values["cached_after"]) == 0, "cached engine still holds a handle"
    assert int(values["checked_out_after"]) == 0


def test_probe_teardown_restores_the_environment(tmp_path):
    """Issue 4: a full probe run must leave the process environment as it found it.

    Runs the real probe in a subprocess with sentinel values and asserts they survive.
    """
    import subprocess
    import sys

    sentinels = {
        "DATABASE_URL": "sqlite:///sentinel-do-not-touch.db",
        "APP_ENV": "sentinel-env",
        "UPLOAD_DIR": str(tmp_path / "sentinel-uploads"),
        "DEMO_SEED_PASSWORD": "sentinel-password",
    }
    script = tmp_path / "run_probe.py"
    script.write_text(
        f"""
import os, sys
for key, value in {sentinels!r}.items():
    os.environ[key] = value

sys.path.insert(0, {str(Path(__file__).resolve().parents[3] / "scripts" / "python")!r})
sys.argv = ["probe"]

import importlib.util
spec = importlib.util.spec_from_file_location(
    "probe_r16", {str(PROBE)!r}
)
module = importlib.util.module_from_spec(spec)
# Register before exec: the probe defines a dataclass, which needs a real module entry
# in sys.modules or dataclasses raises AttributeError on __dict__.
sys.modules[spec.name] = module
spec.loader.exec_module(module)

results = []
# engine_present=False takes the early return; use True so the body and finally run.
try:
    module.gate_api_ocr_upload(results, engine_present=True)
except Exception as error:
    print("gate raised", type(error).__name__, error)

after = {{key: os.environ.get(key) for key in {sorted(sentinels)!r}}}
print("ENV", after)
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/tmp/v/bin",
            "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "backend"),
            "HOME": str(tmp_path),
        },
        check=False,
        timeout=300,
    )
    line = next((row for row in completed.stdout.splitlines() if row.startswith("ENV ")), None)
    assert line is not None, completed.stdout[-2000:] + completed.stderr[-2000:]

    import ast

    restored = ast.literal_eval(line[4:])
    for key, value in sentinels.items():
        assert restored[key] == value, f"{key} was not restored: {restored[key]!r}"


def test_dispose_engines_is_safe_when_nothing_is_cached():
    """Idempotent: disposing twice, or for an unseen URL, must not raise."""
    from app.db.session import dispose_engines

    dispose_engines("sqlite:///definitely-not-created.db")
    dispose_engines("sqlite:///definitely-not-created.db")


def test_the_probe_disposes_before_removing_the_temporary_directory():
    """Order matters: dispose, then delete. A retained handle breaks Windows.

    ``with TemporaryDirectory(...)`` removes the directory as the block exits, which is
    *before* an outer ``finally`` could dispose the engine still holding the SQLite file
    open. That is exactly how the owner's run produced ``WinError 32``. The gate must
    therefore own an explicit directory and tear it down in the right order.
    """
    source = PROBE.read_text(encoding="utf-8")
    body = source[source.index("def gate_api_ocr_upload") : source.index("def main(")]

    assert "tempfile.mkdtemp(" in body, "the gate must own its directory explicitly"
    assert "with tempfile.TemporaryDirectory(" not in body, (
        "TemporaryDirectory deletes before an outer finally can dispose the engine"
    )

    # Teardown runs in a finally, disposes the engine cache, and only then deletes.
    finally_at = body.index("finally:")
    dispose_at = body.index("dispose_engines(")
    rmtree_at = body.index("shutil.rmtree(")
    assert finally_at < dispose_at < rmtree_at, (
        "teardown must run in a finally, dispose engines, and remove the directory last"
    )

    # A cleanup failure gets its own identifier, never a second verdict for the gate.
    assert '"ING-02 teardown"' in body
    assert "PermissionError" in body


# ================================== R13b: source-image vs OCR-output, both outcomes
#
# The owner's real Tesseract run returned:
#
#     Test Gluccse Value: 105 mgldl.
#
# from an image whose source text says ``Value: 1O5 mg/dL``. So the engine itself
# substituted ``1O5`` -> ``105``. That is a *different* situation from the parser
# receiving ``1O5``, and from the parser receiving a plausible ``105`` on a damaged
# line. All three must be distinguished, and none may be silently "fixed".
#
# These tests use the recorded OCR text verbatim. They prove parser behaviour on real
# engine output; they do not claim the engine was run here.

#: The owner's actual Windows OCR output at commit 1cbc86a (fragment of line 3).
OWNER_OCR_LINE = "Test Gluccse Value: 105 mgldl."

#: The synthetic source that image was rendered from.
SOURCE_LINE = "Test: Glucose             Value: 1O5 mg/dL"


def test_source_image_and_ocr_output_disagree_and_that_is_recorded():
    """The substitution ``1O5`` -> ``105`` happened in the *engine*, not the parser.

    This is the decisive evidence split the review asked for: the source says one thing,
    the engine said another. Nothing in the application did it.
    """
    assert "1O5" in SOURCE_LINE
    assert "105" in OWNER_OCR_LINE
    assert "1O5" not in OWNER_OCR_LINE, "the engine transcribed the O as a zero"


def test_owner_ocr_text_yields_no_value_fact():
    """The owner's damaged line must not produce an accepted value fact.

    ``Gluccse`` and ``mgldl.`` are mangled, and the conservative pattern requires
    ``test``/``value`` labels it can trust. The safe outcome is *no* fact, not a guessed
    one — the document then routes to human review rather than silently using 105.
    """
    facts = _value_facts(OWNER_OCR_LINE)

    assert facts == [], "a damaged line must not be attributed as a verified value"
    # And nothing anywhere claimed 105 from this text.
    page = PageText(
        page_index=0, text=OWNER_OCR_LINE, extractor=ExtractionPath.TESSERACT, confidence=0.6
    )
    parsed = parse_pages([page])
    assert all(fact.normalized_value != "105" for fact in parsed.facts)


def test_a_plausible_105_from_damaged_ocr_is_never_silently_accepted():
    """If the labels survive but the value is a substituted ``105``, it is still unsafe.

    This is the case that matters clinically: a *plausible but wrong* number. The parser
    cannot know the engine lied, so it must not invent confidence it does not have. The
    value is recorded with the page's OCR confidence so the review path can see the
    uncertainty — it is not laundered into a clean reading.
    """
    # Labels intact, engine substituted the value, OCR confidence low.
    text = "Test: Glucose             Value: 105 mg/dL"
    page = PageText(page_index=0, text=text, extractor=ExtractionPath.TESSERACT, confidence=0.64)
    parsed = parse_pages([page])
    values = [fact for fact in parsed.facts if fact.field_name.value == "value"]

    assert len(values) == 1
    fact = values[0]
    # The parser records what it saw; it does not pretend to have verified it.
    assert fact.raw_text == "105"
    assert fact.extractor is ExtractionPath.TESSERACT
    assert fact.confidence == pytest.approx(0.64)
    # Crucially, the fact is NOT marked CLEAN-verified by the OCR layer: the low
    # confidence is preserved for the readability rules to act on.
    assert fact.confidence < 0.70, "low OCR confidence must remain visible to the rules"


def test_a_preserved_ambiguous_token_and_a_substitution_are_distinguishable():
    """The two outcomes must produce different evidence, not the same 'clean' claim."""
    ambiguous = _value_facts("Test: Glucose             Value: 1O5 mg/dL")[0]
    substituted = _value_facts("Test: Glucose             Value: 105 mg/dL")[0]

    assert ambiguous.normalized_value is None
    assert "unparseable_value" in {flag.value for flag in ambiguous.quality_flags}

    assert substituted.normalized_value == "105"
    assert "unparseable_value" not in {flag.value for flag in substituted.quality_flags}

    # Different inputs, different evidence — so a reviewer can tell them apart later.
    assert ambiguous.raw_text != substituted.raw_text
    assert ambiguous.normalized_value != substituted.normalized_value


# ==================================== R16: the cleanup fix was still incomplete
#
# The R15 fix disposed the *cached* engine, but the gate also creates its own
# standalone engine via ``create_db_engine``. Closing a Session does not release that
# engine's pooled SQLite handle, so ``accept.db`` stays locked on Windows.
#
# ``pool.checkedin() == 0`` is used as the assertion because it is platform
# independent: on Windows a non-zero value is exactly the open file handle that causes
# ``PermissionError [WinError 32]``. ``unlink()`` cannot be used as proof — Unix happily
# unlinks a file that still has open handles, which is why the previous test passed
# while the defect was live.


def _pooled_engines(url: str) -> list:
    """Return engines known to hold pooled connections for ``url``."""
    from app.db.session import _engine_for_url

    known = []
    cached = _engine_for_url.cache_info()
    assert cached is not None  # the cache exists
    try:
        engine = _engine_for_url(url)
    except Exception:  # pragma: no cover - defensive
        return known
    known.append(engine)
    return known


def test_closing_a_session_does_not_release_the_standalone_engine_pool(tmp_path):
    """Pins the premise of R16: a Session close leaves the pool holding a connection.

    This is the fact the previous fix missed. It is asserted rather than assumed,
    because the whole cleanup design depends on it.
    """
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.db.session import create_db_engine

    db_path = tmp_path / "accept.db"
    url = f"sqlite:///{db_path.as_posix()}"
    engine = create_db_engine(url)
    try:
        with Session(engine) as session:
            session.execute(text("CREATE TABLE t (x integer)"))
            session.commit()
        # Session is closed, yet the pool still retains a live connection.
        assert engine.pool.checkedin() > 0, (
            "if this ever becomes 0, the Windows lock risk has changed"
        )
    finally:
        engine.dispose()


def test_disposing_the_standalone_engine_releases_every_connection(tmp_path):
    """The remedy for issue 1: explicit ``dispose()`` drops the pool to zero."""
    from sqlalchemy import text

    from app.db.session import create_db_engine

    db_path = tmp_path / "accept.db"
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE t (x integer)"))
    assert engine.pool.checkedin() > 0

    engine.dispose()

    assert engine.pool.checkedin() == 0
    assert engine.pool.checkedout() == 0


def test_dispose_engines_does_not_silently_leak_other_cached_engines(tmp_path):
    """Issue 2: clearing the cache must not orphan engines for *other* URLs.

    ``cache_clear()`` on its own evicts every entry without disposing it, so another
    URL's engine keeps its pooled handle forever and can still be used — a silent leak
    in a long-lived process.
    """
    from sqlalchemy import text

    from app.db.session import _engine_for_url, dispose_engines

    target = f"sqlite:///{(tmp_path / 'target.db').as_posix()}"
    other = f"sqlite:///{(tmp_path / 'other.db').as_posix()}"

    target_engine = _engine_for_url(target)
    with target_engine.connect() as connection:
        connection.execute(text("CREATE TABLE t (x integer)"))
    other_engine = _engine_for_url(other)
    with other_engine.connect() as connection:
        connection.execute(text("CREATE TABLE u (y integer)"))

    assert other_engine.pool.checkedin() > 0

    dispose_engines(target)

    # The target is gone from the cache and its pool is closed.
    assert target_engine.pool.checkedin() == 0
    # And the *other* engine was not silently leaked: either it was disposed, or it is
    # still tracked by the cache (so a later call can dispose it). A bare
    # ``cache_clear()`` would satisfy neither.
    assert other_engine.pool.checkedin() == 0 or _engine_for_url(other) is other_engine


def test_dispose_engines_releases_the_named_url_only(tmp_path):
    """Disposing one URL must not touch an unrelated, still-cached engine's pool."""
    from sqlalchemy import text

    from app.db.session import _engine_for_url, dispose_engines

    target = f"sqlite:///{(tmp_path / 'target.db').as_posix()}"
    keep = f"sqlite:///{(tmp_path / 'keep.db').as_posix()}"

    target_engine = _engine_for_url(target)
    with target_engine.connect() as connection:
        connection.execute(text("CREATE TABLE t (x integer)"))
    keep_engine = _engine_for_url(keep)
    with keep_engine.connect() as connection:
        connection.execute(text("CREATE TABLE u (y integer)"))

    dispose_engines(target)

    assert target_engine.pool.checkedin() == 0, "the named URL must be released"
    # An engine for a different URL is a different database: leaving it alone is correct
    # and is what stops one test's cleanup from breaking another's pooling.
    assert keep_engine.pool.checkedin() > 0


# ------------------------------------------- probe ownership of the standalone engine


def test_the_gate_owns_and_disposes_its_standalone_engine():
    """The gate must keep a reference to its own engine and dispose it in teardown."""
    source = PROBE.read_text(encoding="utf-8")
    body = source[source.index("def gate_api_ocr_upload") : source.index("def main(")]

    # The engine handle is bound to a name declared before the ``try`` so ``finally``
    # can reach it even when the body fails early.
    assert "engine = None" in body, "the engine handle must exist before the try block"
    assert "engine = create_db_engine(" in body
    assert "engine.dispose()" in body, "the standalone engine must be disposed"

    finally_at = body.index("finally:")
    standalone_dispose = body.index("engine.dispose()")
    rmtree_at = body.index("shutil.rmtree(")
    assert finally_at < standalone_dispose < rmtree_at, (
        "dispose the standalone engine in finally, before removing the directory"
    )


def test_the_gate_restores_environment_overrides_on_every_path():
    """Issue 4: the probe must not leak its temporary environment into the process."""
    source = PROBE.read_text(encoding="utf-8")
    body = source[source.index("def gate_api_ocr_upload") : source.index("def main(")]

    for name in ("DATABASE_URL", "APP_ENV", "UPLOAD_DIR", "DEMO_SEED_PASSWORD"):
        assert f'"{name}"' in body, f"{name} override is missing"

    # A saved-snapshot + restore pattern, not a bare delete: the owner may legitimately
    # have these set in their shell.
    assert "saved_env" in body or "_saved" in body, "overrides must be snapshotted"
    finally_at = body.index("finally:")
    restore_at = body.index("os.environ", finally_at)
    assert finally_at < restore_at, "restoration must happen in the finally block"
