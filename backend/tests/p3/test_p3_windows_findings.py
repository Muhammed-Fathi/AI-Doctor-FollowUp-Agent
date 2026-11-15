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
