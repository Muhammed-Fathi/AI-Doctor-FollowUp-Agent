#!/usr/bin/env python
"""Owner-laptop acceptance probe for the Windows-only P3 gates.

This script exists because four P3 gates **cannot** be executed in the agent's
sandbox and must never be claimed:

* ``GOLD-EX-05..08`` — clean PNG/JPEG scans read by the **real** Tesseract engine;
* ``OCR-LIVE-01``    — measured engine confidence / recovered characters / wall time;
* ``GOLD-EX-11``     — the OCR-produced ``1O5`` variant (a text-layer fixture covers
                       the flag and the correction path in the sandbox; the engine
                       variant does not exist there);
* ``D-01``           — ``pypdfium2`` rasterization on Windows.

It is deliberately **read-only with respect to the owner's data**: it writes
nothing outside a temporary directory it creates and deletes, never points at
``data/runtime/app.db``, and never mutates an existing document.

Everything printed is a measured observation. Where a gate cannot run, the script
prints ``NOT RUN`` with the reason and exits non-zero — it never reports a pass it
did not earn.

Usage (from the repository root, inside the prepared worktree)::

    .\\.venv\\Scripts\\python.exe scripts\\python\\windows_ocr_acceptance.py
    .\\.venv\\Scripts\\python.exe scripts\\python\\windows_ocr_acceptance.py --json ocr.json

Exit codes: ``0`` = every executable gate PASSED, ``2`` = at least one NOT RUN or
FAILED. A ``2`` is a normal, honest outcome when Tesseract is not installed.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import argparse
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = REPO_ROOT / "data" / "synthetic" / "documents" / "sources"

PASS = "PASS"
FAIL = "FAIL"
NOT_RUN = "NOT RUN"
#: A row that documents which other gates prove a contract case. It is neither a
#: pass nor a failure and never affects the exit code on its own.
DERIVED = "DERIVED"


@dataclass
class Result:
    """One gate's measured outcome."""

    gate: str
    status: str
    detail: str
    data: dict[str, object] = field(default_factory=dict)


def _record(results: list[Result], result: Result) -> Result:
    """Append ``result`` and echo it, so a human can follow along."""
    results.append(result)
    print(f"[{result.status:>7}] {result.gate}: {result.detail}")
    return result


def _git_head() -> str | None:
    """Return the worktree's HEAD SHA, so evidence is bound to one commit.

    Best-effort only: a missing ``git`` or a non-repository checkout must not stop
    the probe. The field is ``None`` in that case rather than a guess.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


#: The committed synthetic source rendered for ``GOLD-EX-11``. It contains a literal
#: ``1O5`` and renders legibly, so a real engine can be measured rather than guessed at.
SOURCE_NAME = "report_ocr_o_confusion.txt"


#: Environment variables the ING-02 gate overrides; snapshotted and restored in
#: ``finally`` so the probe never leaks its temporary configuration into the process.
_PROBE_ENV_KEYS = ("DATABASE_URL", "APP_ENV", "UPLOAD_DIR", "DEMO_SEED_PASSWORD")


def _verdicts_for(results: list[Result], gate: str) -> list[Result]:
    """Return the rows already recorded for ``gate``."""
    return [row for row in results if row.gate == gate]


def _guarded(results: list[Result], gate: str, probe) -> object:
    """Run ``probe`` and convert any escape into a truthful ``FAIL`` result.

    A missing wheel, an unreadable fixture or an unexpected engine error must not
    abort the run with a traceback: the JSON evidence file is the artifact the
    owner hands back, so it has to be written even when a gate blows up. The
    traceback is included — an error is reported, never hidden.

    **One verdict per gate.** A gate may record its conclusion and *then* raise, usually
    from a teardown path. Appending a second row would contradict the first — an earlier
    owner run contained ING-02 as both PASS and FAIL, making the evidence unreadable. If
    the gate has already concluded, that verdict stands and the exception is attributed
    to a separate ``<gate> cleanup`` row, so a cleanup failure stays visible and can
    never be mistaken for a pass.
    """
    try:
        return probe()
    except Exception as error:
        detail = f"unexpected {type(error).__name__}: {error}\n{traceback.format_exc(limit=3)}"
        if _verdicts_for(results, gate):
            _record(results, Result(f"{gate} cleanup", FAIL, detail))
        else:
            _record(results, Result(gate, FAIL, detail))
        return None


# --- environment -------------------------------------------------------------


def gate_environment(results: list[Result]) -> None:
    """Record the environment every other measurement depends on."""
    expected = "3.12."
    python_ok = platform.python_version().startswith(expected)

    # Record the interpreter first, then the libraries. A missing wheel is a
    # finding about the environment, not a crash of the probe: the owner needs a
    # JSON file with `pillow: NOT RUN` far more than a traceback.
    _record(
        results,
        Result(
            "ENV-01 python",
            PASS if python_ok else FAIL,
            (
                f"{platform.system()} {platform.release()} build {platform.version()}; "
                f"Python {platform.python_version()}"
                + ("" if python_ok else f" (project requires {expected}x)")
            ),
            {"python": platform.python_version(), "os": platform.platform()},
        ),
    )

    versions: dict[str, str] = {}
    missing: list[str] = []
    for module_name, getter in (
        ("PIL", lambda m: getattr(m, "__version__", "unknown")),
        ("pytesseract", lambda m: getattr(m, "__version__", "unknown")),
        ("pypdfium2", lambda m: str(m.version.PYPDFIUM_INFO)),
    ):
        try:
            module = __import__(module_name)
            versions[module_name] = getter(module)
        except Exception as error:
            missing.append(f"{module_name} ({type(error).__name__}: {error})")

    _record(
        results,
        Result(
            "ENV-02 libraries",
            FAIL if missing else PASS,
            (
                f"installed: {versions}"
                if not missing
                else f"not importable: {missing} — rerun the hash-locked install"
            ),
            {"versions": versions, "missing": missing},
        ),
    )


def gate_engine(results: list[Result]) -> str | None:
    """Resolve the Tesseract executable and report its version, languages, data.

    The engine is a **system prerequisite** (ASM-01), not a wheel. A missing
    engine is ``NOT RUN``, never a failure of the code under test.
    """
    from app.core.config import Settings
    from app.services.documents.ocr import OcrUnavailableError, engine_version, resolve_engine

    settings = Settings()
    try:
        executable = resolve_engine(settings.tesseract_cmd)
    except OcrUnavailableError as error:
        _record(
            results,
            Result(
                "OCR-ENGINE",
                NOT_RUN,
                f"engine not resolvable ({error}); install Tesseract and set TESSERACT_CMD",
            ),
        )
        return None

    version = engine_version(settings.tesseract_cmd)
    _record(
        results,
        Result(
            "OCR-ENGINE",
            PASS if version else FAIL,
            f"executable={executable} version={version or 'unreported'}",
            {"executable": str(executable), "version": version},
        ),
    )

    data_dirs = []
    root = Path(executable).parent
    for candidate in (root / "tessdata", root.parent / "share" / "tessdata"):
        if candidate.is_dir():
            data_dirs.append(candidate)
    found = {path.name for directory in data_dirs for path in directory.glob("*.traineddata")}
    has_eng = "eng.traineddata" in found
    _record(
        results,
        Result(
            "OCR-ENGINE eng.traineddata",
            PASS if has_eng else FAIL,
            (
                f"found in {[str(d) for d in data_dirs]}; languages={sorted(found)}"
                if data_dirs
                else "no tessdata directory found next to the executable"
            ),
            {"tessdata_dirs": [str(d) for d in data_dirs], "languages": sorted(found)},
        ),
    )
    return str(executable)


# --- OCR through the real engine ---------------------------------------------


def _engine_scan(results: list[Result], *, source: str, fmt: str, gate: str) -> None:
    """OCR one generated scan with the real engine and assert provenance facts."""
    from PIL import Image

    import generate_p3_fixtures as fixtures
    from app.services.documents.ocr import OcrUnavailableError, run_ocr

    sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

    payload = fixtures.image_bytes(source, fmt=fmt)
    image = Image.open(io.BytesIO(payload))

    started = time.perf_counter()
    try:
        ocr = run_ocr(
            image,
            tesseract_cmd=os.environ.get("TESSERACT_CMD") or None,
            language="eng",
        )
    except OcrUnavailableError as error:
        _record(results, Result(gate, NOT_RUN, f"engine unavailable: {error}"))
        return
    except Exception as error:
        _record(results, Result(gate, FAIL, f"{type(error).__name__}: {error}"))
        return
    elapsed = time.perf_counter() - started

    expected_tokens = {"glucose", "hemoglobin", "report", "value", "ref"}
    text_lower = ocr.text.lower()
    hit = sorted(token for token in expected_tokens if token in text_lower)
    readable = len(hit) >= 3

    _record(
        results,
        Result(
            gate,
            PASS if readable else FAIL,
            (
                f"{fmt}: chars={len(ocr.text)} confidence={ocr.confidence} "
                f"tool={ocr.tool_version} wall={elapsed:.2f}s tokens={hit}"
            ),
            {
                "format": fmt,
                "char_count": len(ocr.text),
                "confidence": ocr.confidence,
                "tool_version": ocr.tool_version,
                "wall_seconds": round(elapsed, 3),
                "tokens_recovered": hit,
            },
        ),
    )


def gate_ocr_live(results: list[Result], *, engine_present: bool) -> None:
    """``GOLD-EX-05..08`` and ``OCR-LIVE-01``: real engine, both preprocessings.

    ``OCR-LIVE-01`` is a **measurement**, not an assertion: the numbers are
    recorded whatever they are. Only "did the engine read recognisable tokens"
    is treated as pass/fail, because that is the thing the product depends on.
    """
    if not engine_present:
        # Every case still appears in the evidence, so a reader can see exactly
        # what did not run instead of inferring it from a gap.
        for gate in (
            "GOLD-EX-05 PNG",
            "GOLD-EX-06 JPEG",
            "GOLD-EX-07/08 coverage",
            "OCR-LIVE-01",
        ):
            _record(results, Result(gate, NOT_RUN, "no Tesseract engine available"))
        return

    _engine_scan(results, source="report_a_clean.txt", fmt="PNG", gate="GOLD-EX-05 PNG")
    _engine_scan(results, source="report_a_clean.txt", fmt="JPEG", gate="GOLD-EX-06 JPEG")

    # GOLD-EX-07/08 are the "same fields via the OCR path" pair, i.e. the *field
    # extraction* half rather than the bare read. They are covered end-to-end by
    # `ING-02 OCR upload end-to-end` below (PNG) — which asserts the fields, the
    # `tesseract` extractor and the stored provenance — and by the JPEG read
    # above. They are recorded here as an explicit mapping so no case is claimed
    # twice or silently dropped.
    _record(
        results,
        Result(
            "GOLD-EX-07/08 coverage",
            "DERIVED",
            (
                "GOLD-EX-07 (fields via the OCR path) is asserted by "
                "'ING-02 OCR upload end-to-end'; GOLD-EX-08 (JPEG readability) by "
                "'GOLD-EX-06 JPEG'. This row states the mapping only — it is not an "
                "independent pass and is never counted as one."
            ),
            {"derived_from": ["GOLD-EX-05 PNG", "GOLD-EX-06 JPEG", "ING-02 OCR upload end-to-end"]},
        ),
    )

    # Preprocessing off/on, twice, on a deliberately hostile source: small text.
    from PIL import Image

    import generate_p3_fixtures as fixtures
    from app.services.documents.ocr import Preprocessing, run_ocr

    measurements = []
    payload = fixtures.image_bytes("report_c_ambiguous.txt", fmt="PNG")
    for preprocessing in (Preprocessing.NONE, Preprocessing.GRAYSCALE_UPSCALE):
        for repeat in (1, 2):
            image = Image.open(io.BytesIO(payload))
            started = time.perf_counter()
            ocr = run_ocr(
                image,
                tesseract_cmd=os.environ.get("TESSERACT_CMD") or None,
                language="eng",
                preprocessing=preprocessing,
            )
            measurements.append(
                {
                    "preprocessing": preprocessing.value,
                    "repeat": repeat,
                    "char_count": len(ocr.text),
                    "confidence": ocr.confidence,
                    "wall_seconds": round(time.perf_counter() - started, 3),
                    "tool_version": ocr.tool_version,
                }
            )

    _record(
        results,
        Result(
            "OCR-LIVE-01 measured",
            PASS,
            "recorded, not asserted: " + json.dumps(measurements, separators=(",", ":")),
            {"measurements": measurements},
        ),
    )


def gate_ocr_corruption(results: list[Result], *, engine_present: bool) -> None:
    """``GOLD-EX-11``: an OCR-produced ``1O5`` must be flagged, not repaired."""
    gate = "GOLD-EX-11 OCR-produced 1O5"
    if not engine_present:
        _record(results, Result(gate, NOT_RUN, "no Tesseract engine available"))
        return

    from PIL import Image

    # The committed source literally contains the letter O in ``1O5``. It is rendered at
    # 40 px with Pillow's bundled scalable font: the previous 10 px bitmap render was
    # unreadable on the owner's Windows machine, which lost both the ``O`` and the
    # ``Value:`` label and made the gate unable to demonstrate anything.
    #
    # Legibility is the ONLY thing the render improves. Which character the engine sees
    # is still measured, never engineered — the source is not changed to make the test
    # pass, and both outcomes are reported honestly.
    import generate_p3_fixtures as fixtures
    from app.core.enums import ExtractionPath
    from app.services.documents.field_parser import parse_pages
    from app.services.documents.issues import collect_flag_issues
    from app.services.documents.ocr import run_ocr
    from app.services.documents.text_extraction import PageText

    rendered = fixtures.build_legible_scan_image(SOURCE_NAME)
    image = Image.open(io.BytesIO(rendered))

    ocr = run_ocr(image, tesseract_cmd=os.environ.get("TESSERACT_CMD") or None, language="eng")
    page = PageText(
        page_index=0,
        text=ocr.text,
        extractor=ExtractionPath.TESSERACT,
        confidence=ocr.confidence,
    )
    parsed = parse_pages([page])

    value_facts = [fact for fact in parsed.facts if fact.field_name.value == "value"]
    flags = {flag.value for fact in value_facts for flag in fact.quality_flags}
    normalized = [fact.normalized_value for fact in value_facts if fact.normalized_value]
    raw_tokens = [fact.raw_text for fact in value_facts]

    # **R17:** whether a human must review this value is a property of the real
    # blocker logic, not a sentence written into the payload. The previous
    # The field used to be a hard-coded true, emitted even when the gate had
    # failed to a reading nobody was asked about. These drafts are produced
    # by the same function the HTTP path uses (`intake` -> `quality.compute_drafts`),
    # so the flag cannot drift away from the application's behaviour.
    flag_drafts = collect_flag_issues(
        [
            (index, fact.field_name.value, tuple(flag.value for flag in fact.quality_flags))
            for index, fact in enumerate(parsed.facts)
        ]
    )
    blocking_issue_types = sorted({draft.issue_type.value for draft in flag_drafts})
    human_review_required = bool(blocking_issue_types)

    # What the ENGINE returned, independent of what the parser made of it. The source
    # image contains ``1O5``; the only question is whether the engine preserved it.
    intended = "1O5"
    preserved = intended in ocr.text
    substituted = "105" in ocr.text and not preserved

    # ``unparseable_value`` is the parser *refusing* an ambiguous token. ``low_confidence``
    # only says the reading is uncertain — a review signal, NOT evidence that an ambiguous
    # token was detected. Requiring the former stops a substituted ``105`` from being
    # reported as a demonstrated corruption case merely because the engine was unsure too.
    parser_refused = "unparseable_value" in flags
    low_confidence_only = "low_confidence" in flags and not parser_refused

    # Outcomes, which mean genuinely different things:
    #
    #  (a) engine preserved ``1O5`` and the parser refused it -> the documented
    #      behaviour. The only case that may PASS.
    #  (b) engine substituted a plausible ``105``, or the parser accepted a value ->
    #      the safety property was NOT demonstrated. Never a pass.
    #  (c) no value fact at all -> the engine lost the label. Not demonstrated.
    if preserved and parser_refused and not normalized:
        status = PASS
        reason = (
            "engine preserved the ambiguous 1O5 and the parser refused it as "
            "unparseable; no numeric value was produced"
        )
    elif not value_facts:
        status = FAIL
        if substituted:
            reason = (
                "engine transcribed 1O5 as a plausible 105 and damaged the labels, so no "
                "value fact was parsable. The ambiguous-token safety property is NOT "
                "PROVEN by this image (the substitution was the engine's, not ours)"
            )
        else:
            reason = (
                "no value fact was parsed and the engine returned neither 1O5 nor 105, so "
                "the ambiguous-token safety property is NOT PROVEN by this image"
            )
    elif substituted or normalized:
        status = FAIL
        reason = (
            f"engine substituted a plausible {normalized or raw_tokens} for the rendered "
            "1O5, so the ambiguous-token safety property is NOT PROVEN; it must not be "
            "reported as a demonstrated case"
        )
    elif low_confidence_only:
        status = FAIL
        reason = (
            "the value was only flagged low_confidence, which is a review signal, not "
            "evidence that an ambiguous token was preserved and refused; NOT PROVEN"
        )
    else:
        status = FAIL
        reason = "the OCR result did not exercise the ambiguous-token path; NOT PROVEN"

    _record(
        results,
        Result(
            gate,
            status,
            f"{reason}; value flags={sorted(flags)} normalized={normalized} raw={raw_tokens}",
            {
                # 3. whether a human must look at this value — DERIVED, not asserted:
                # it is true only when the real blocker logic raised a blocking VI-*
                # for these parsed facts (R17).
                "human_review_required": human_review_required,
                "human_review_required_basis": "persisted-blocker-logic:collect_flag_issues",
                "human_review_blocking_issues": blocking_issue_types,
                "human_review_reason": (
                    "a blocking verification issue is raised for these parsed facts, so "
                    "the value cannot be used without a doctor's decision"
                    if human_review_required
                    else "no blocking issue was raised for these parsed facts"
                ),
                "diagnosis": (
                    "preserved_and_refused"
                    if parser_refused and preserved
                    else ("substituted" if substituted else "not_proven")
                ),
                "flags": sorted(flags),
                "normalized_values": normalized,
                "raw_tokens": raw_tokens,
                # 1. what the engine returned (kept verbatim; never paraphrased)
                "engine_ocr_text": ocr.text,
                "engine_preserved_ambiguous_token": preserved,
                "engine_substituted_plausible_value": substituted,
                "ocr_text": ocr.text,
                # 2. what the parser produced from it
                "parser_refused_token": parser_refused,
                "source_token": intended,
                "application_substituted_value": False,
                "clinical_accuracy_claimed": False,
                "limitation": (
                    "the gate proves the parser flags an OCR-produced ambiguous token only "
                    "when the engine actually emits one; a low-resolution render may lose "
                    "the line. Parser behaviour is proven deterministically in "
                    "test_p3_windows_findings.py"
                ),
            },
        ),
    )


# --- rasterization ------------------------------------------------------------


def gate_rasterizer(results: list[Result]) -> None:
    """``D-01``: ``pypdfium2`` must rasterize a generated PDF on Windows."""
    gate = "PDFIUM-01 rasterize"
    try:
        import generate_p3_fixtures as fixtures
        from app.services.documents.rasterize import RasterizationError, render_page

        payload = fixtures.build_report_pdf("report_a_clean.txt")
        started = time.perf_counter()
        image = render_page(payload, page_index=0, max_pixels=40_000_000)
        elapsed = time.perf_counter() - started
        size = getattr(image, "size", None)
        _record(
            results,
            Result(
                gate,
                PASS if size else FAIL,
                f"page 0 rendered size={size} wall={elapsed:.2f}s",
                {"size": size, "wall_seconds": round(elapsed, 3)},
            ),
        )
    except RasterizationError as error:
        _record(results, Result(gate, FAIL, f"rasterization failed: {error}"))
    except Exception as error:
        _record(results, Result(gate, NOT_RUN, f"{type(error).__name__}: {error}"))


# --- end-to-end through the API ----------------------------------------------


def _seed_password(settings) -> str:
    """Extract the demo seed password as a **plain string**, never a ``SecretStr``.

    ``Settings.demo_seed_password`` is typed ``SecretStr``, so passing it straight to
    ``seed_demo_data`` crashed with
    ``AttributeError: 'SecretStr' object has no attribute 'strip'`` — the probe boundary
    was wrong, not the seed service (which correctly calls ``.get_secret_value()``).

    The value is read through the supported accessor and never logged or written to the
    evidence JSON. When nothing is configured, an explicit synthetic local password is
    used: this probe builds a throwaway database, so a fixed demo credential is
    appropriate and no real secret is needed.
    """
    configured = getattr(settings, "demo_seed_password", None)
    if configured is None:
        return "acceptance-only-password"
    if hasattr(configured, "get_secret_value"):
        secret = configured.get_secret_value()
        return secret or "acceptance-only-password"
    return str(configured) or "acceptance-only-password"


def _isolated_app(tmp: str, *, source_name: str | None = None) -> dict:
    """Build a throwaway settings/app/session seam over a temporary SQLite file.

    Extracted from ``gate_api_ocr_upload`` so the R21 rejection gate (``W1``) drives
    exactly the same isolated infrastructure instead of duplicating it: the
    overrides, the migrated database, the seeded demo users, the minted sessions and
    the disabled session cache are all established once, here.

    Returns ``engine``, ``database_url``, ``settings``, ``app``,
    ``session_factory``, ``patient_token``, ``doctor_token`` and ``image_bytes``.
    Callers must restore the environment and dispose ``engine`` themselves; the
    owning gate's ``finally`` does both. If setup raises after opening ``engine``,
    this function disposes it before re-raising so no handle leaks on Windows.
    """
    from sqlalchemy.orm import Session

    from app.core.config import get_settings, reset_settings_cache
    from app.db.models import User
    from app.db.session import create_db_engine
    from app.main import create_app
    from app.services.accounts import issue_session
    from app.services.seed import seed_demo_data

    db_path = Path(tmp) / "accept.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["APP_ENV"] = "test"
    os.environ["UPLOAD_DIR"] = str(Path(tmp) / "uploads")
    os.environ["DEMO_SEED_PASSWORD"] = os.environ.get(
        "DEMO_SEED_PASSWORD", "acceptance-only-password"
    )

    reset_settings_cache()
    settings = get_settings()

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select

    config = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")

    engine = create_db_engine(settings.database_url)
    try:
        with Session(engine) as session:
            seed_demo_data(
                session,
                password=_seed_password(settings),
                now=datetime(2026, 11, 15, tzinfo=UTC),
                iterations=1000,
            )
            session.commit()
            patient = session.execute(
                select(User).where(User.username == "demo_patient_a")
            ).scalar_one()
            doctor = session.execute(
                select(User).where(User.username == "demo_doctor")
            ).scalar_one()
            # ``issue_session`` is keyword-only and takes an explicit clock; the
            # reviewed probe omitted it and raised TypeError before any upload.
            #
            # The clock must be *now*, not a fixed date: a session lives for 60
            # minutes, so a hard-coded midnight expiry is already in the past and
            # the upload answers 401. That is the probe borrowing the seed's
            # deterministic timestamp for something time-sensitive.
            issued_at = datetime.now(UTC)
            patient_token, _ = issue_session(session, user=patient, now=issued_at, ttl_minutes=60)
            doctor_token, _ = issue_session(session, user=doctor, now=issued_at, ttl_minutes=60)
            session.commit()

        scripts_dir = str(REPO_ROOT / "scripts" / "python")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import generate_p3_fixtures as fixtures

        return {
            "engine": engine,
            "database_url": database_url,
            "settings": settings,
            "app": create_app(settings),
            "session_factory": lambda: Session(engine),
            "patient_token": patient_token,
            "doctor_token": doctor_token,
            "image_bytes": fixtures.build_legible_scan_image(
                source_name or W1_SOURCE_NAME, fmt="PNG"
            ),
        }
    except Exception:
        engine.dispose()
        raise


def gate_api_ocr_upload(results: list[Result], *, engine_present: bool) -> None:
    """GOLD-EX-05 through the real HTTP path: PNG upload ends with tesseract facts.

    Uses an isolated application instance over a temporary SQLite database and a
    temporary upload directory, so the owner's ``data/runtime`` is never touched.
    The seam is shared with the R21 rejection gate via ``_isolated_app``.
    """
    gate = "ING-02 OCR upload end-to-end"
    if not engine_present:
        _record(results, Result(gate, NOT_RUN, "no Tesseract engine available"))
        return

    import generate_p3_fixtures as fixtures

    tmp = tempfile.mkdtemp(prefix="p3-accept-")
    database_url = ""
    # Bound before the ``try`` so ``finally`` can always reach it, even when the body
    # fails before the engine is created.
    engine = None
    # Snapshot the overrides this gate mutates: the owner may legitimately have any of
    # these set in their shell, and the probe must leave the process as it found it.
    saved_env = {name: os.environ.get(name) for name in _PROBE_ENV_KEYS}
    try:
        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from app.db.models import ExtractedFact

        seam = _isolated_app(tmp)
        engine = seam["engine"]
        database_url = seam["database_url"]

        with TestClient(seam["app"]) as client:
            upload = client.post(
                "/api/v1/documents/upload",
                headers={"Authorization": f"Bearer {seam['patient_token']}"},
                files={
                    "file": (
                        "scan.png",
                        fixtures.image_bytes("report_a_clean.txt", fmt="PNG"),
                        "image/png",
                    )
                },
            )
            if upload.status_code != 202:
                _record(
                    results,
                    Result(gate, FAIL, f"upload answered {upload.status_code}: {upload.text}"),
                )
                return
            document_id = upload.json()["document_id"]

            extraction = client.get(
                f"/api/v1/documents/{document_id}/extraction",
                headers={"Authorization": f"Bearer {seam['doctor_token']}"},
            )
            if extraction.status_code != 200:
                _record(
                    results,
                    Result(
                        gate,
                        FAIL,
                        f"extraction answered {extraction.status_code}: {extraction.text}",
                    ),
                )
                return

            body = extraction.json()
            facts = body["facts"]
            extractors = {fact["evidence"]["extractor"] for fact in facts}
            attempts = [
                {
                    "path": attempt["path"],
                    "succeeded": attempt["succeeded"],
                    "confidence": attempt.get("engine_confidence"),
                }
                for attempt in body["attempts"]
            ]
            with seam["session_factory"]() as session:
                stored_extractors = {
                    row.extractor
                    for row in session.execute(
                        select(ExtractedFact).where(ExtractedFact.document_id == document_id)
                    ).scalars()
                }

            ok = facts and extractors == {"tesseract"} and stored_extractors == {"tesseract"}
            _record(
                results,
                Result(
                    gate,
                    PASS if ok else FAIL,
                    (
                        f"facts={len(facts)} evidence_extractors={sorted(extractors)} "
                        f"stored_extractors={sorted(stored_extractors)} attempts={attempts}"
                    ),
                    {
                        "fact_count": len(facts),
                        "evidence_extractors": sorted(extractors),
                        "stored_extractors": sorted(stored_extractors),
                        "attempts": attempts,
                        "ocr_issues": sorted(
                            issue["issue_type"] for issue in body["verification_issues"]
                        ),
                    },
                ),
            )
    except Exception:
        # A gate that has already concluded keeps its verdict; a failure before that
        # point is the verdict. Either way cleanup below still runs.
        if not _verdicts_for(results, gate):
            _record(results, Result(gate, FAIL, traceback.format_exc(limit=3)))
    finally:
        # Teardown order matters on Windows: a cached engine keeps a pooled connection
        # to the throwaway SQLite file, and the file cannot be deleted while any handle
        # is open (``PermissionError [WinError 32]``). Dispose first, delete second, and
        # report any failure under its own identifier rather than as a second verdict
        # for this gate.
        teardown_errors: list[str] = []
        # Dispose the engine this gate created. Closing a Session does not release the
        # engine's pooled SQLite handle, and on Windows that handle is exactly what makes
        # deleting ``accept.db`` fail with ``PermissionError [WinError 32]``.
        if engine is not None:
            try:
                engine.dispose()
            except Exception as error:
                teardown_errors.append(f"standalone engine: {type(error).__name__}: {error}")
        # Then the cached engine used by the app's request path (a different pool).
        try:
            from app.db.session import dispose_engines

            dispose_engines(database_url)
        except Exception as error:
            teardown_errors.append(f"cached engine: {type(error).__name__}: {error}")
        # Restore the environment before anything else uses it, then drop the settings
        # cache so the next reader re-reads the restored values.
        try:
            for name, previous in saved_env.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous
        except Exception as error:  # pragma: no cover - defensive
            teardown_errors.append(f"environment restore: {type(error).__name__}: {error}")
        try:
            from app.core.config import reset_settings_cache

            reset_settings_cache()
        except Exception as error:  # pragma: no cover - defensive
            teardown_errors.append(f"settings cache: {type(error).__name__}: {error}")
        try:
            shutil.rmtree(tmp)
        except PermissionError as error:
            teardown_errors.append(
                f"temporary directory still locked: {type(error).__name__}: {error} "
                "(a retained SQLite handle prevents deletion on Windows)"
            )
        except OSError as error:
            teardown_errors.append(f"temporary directory: {type(error).__name__}: {error}")

        if teardown_errors:
            _record(
                results,
                Result(
                    "ING-02 teardown",
                    FAIL,
                    "; ".join(teardown_errors),
                    {"cleanup_errors": teardown_errors},
                ),
            )


# --- W1: owner real-engine rejection gate (R21) -------------------------------

#: The synthetic source W1 renders. Deliberately the *mappable* glucose report —
#: Patient A, `104 mg/dL`, and `mg/dL` is a supported unit — so "no Observation was
#: promoted" is a real assertion. A hemoglobin fixture would create no Observation
#: even if the gate wrongly passed, which is why the design report rules it out.
W1_SOURCE_NAME = "report_a_glucose.txt"

#: The single terminal failure a rejected measurement must produce.
W1_FAILURE_CODE = "measurement_rejected"

#: Requirements W1 reports individually. One combined row would give one verdict
#: for seven distinct contract cases, which is the evidence shape that lets a
#: handoff overstate what was shown.
W1_CASES = (
    "OCR value fact",
    "doctor rejection",
    "terminal failure",
    "no Observation",
    "fact immutable",
    "VI-002 stays open",
    "re-decision refused",
)


@dataclass
class W1Evidence:
    """Everything W1 measured, as plain values.

    Kept separate from the gate that collects it so the verdict logic is a pure
    function of the evidence. That is what makes PASS/FAIL/NOT RUN testable without
    a Tesseract install — and without a mocked engine pretending to be Windows
    evidence: the tests drive *this* structure, not the engine.
    """

    #: The OCR-produced ``value`` fact, or ``None`` when the engine produced none.
    candidate: dict | None = None
    #: Why there is no candidate, for the NOT RUN detail.
    candidate_absence: str = ""
    #: How many non-``value`` facts the engine produced. ``measurement_rejected`` is
    #: only reachable when at least one sibling exists: with a value-only document
    #: the service's own rule classifies the outcome as ``all_facts_rejected``, so
    #: asserting ``measurement_rejected`` there would be a false FAIL.
    non_value_fact_count: int = 0
    extracted_fields: tuple[str, ...] = ()
    extracted_facts: tuple[dict, ...] = ()
    verification_issues: tuple[dict, ...] = ()
    #: Whether the extracted document satisfies closed mapping + promotion rules.
    mapping_eligible: bool = True
    mapping_reason: str = ""
    attempts: tuple[dict, ...] = ()
    #: Stored document state after the rejection.
    document_status: str | None = None
    failure_code: str | None = None
    #: Ids of Observations promoted from this document's own facts.
    promoted_observations: tuple[str, ...] = ()
    #: Fact fields a decision must never rewrite, before and after.
    before: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    issues: tuple[dict, ...] = ()
    #: The refused second decision.
    redecision_status: int | None = None
    redecision_code: str | None = None
    #: Decision rows on the fact after the refused attempt.
    decision_count_after_refusal: int = 0
    #: Stage 2 persisted OCR text, exact span equality, extractor & audit safety check.
    provenance_verified: bool | None = None
    provenance_detail: dict = field(default_factory=dict)


def _w1_open_vi002(issues) -> list[dict]:
    """Return the ``VI-002`` issues still ``open`` (D-14 keeps them open)."""
    return [
        dict(issue)
        for issue in issues
        if issue.get("issue_type") == "VI-002" and issue.get("state") == "open"
    ]


def assess_w1(evidence: W1Evidence) -> list[Result]:
    """Turn measured W1 evidence into one verdict per requirement.

    Pure: no I/O, no database, no engine. A missing or unmappable candidate
    short-circuits to ``NOT RUN`` for every requirement — an honest non-result,
    never a PASS and never a manufactured fact.
    """
    gate = "W1 R21 rejection"

    def rows(status: str, detail: str, data: dict | None = None) -> list[Result]:
        return [Result(f"{gate}: {name}", status, detail, dict(data or {})) for name in W1_CASES]

    extracted_summary = {
        "extracted_fields": list(evidence.extracted_fields),
        "extracted_facts": list(evidence.extracted_facts),
        "verification_issues": list(evidence.verification_issues),
        "attempts": list(evidence.attempts),
        **({"mapping_reason": evidence.mapping_reason} if evidence.mapping_reason else {}),
    }

    if evidence.candidate is None:
        return rows(
            NOT_RUN,
            evidence.candidate_absence or "no usable OCR value fact",
            extracted_summary,
        )

    if evidence.non_value_fact_count == 0:
        # The document holds only a ``value`` fact, so rejecting it makes *every*
        # fact rejected and the service correctly reports ``all_facts_rejected``.
        # ``measurement_rejected`` is unreachable in that shape, so neither PASS nor
        # FAIL would be a fair verdict: report the untestable precondition.
        return rows(
            NOT_RUN,
            "the engine produced only a `value` fact, so the contract-correct code is "
            "`all_facts_rejected`, not `measurement_rejected`; W1 cannot assert the "
            "required code on this shape",
            extracted_summary,
        )

    if not evidence.mapping_eligible or (
        "normalized_value" in evidence.candidate and not evidence.candidate.get("normalized_value")
    ):
        return rows(
            NOT_RUN,
            evidence.mapping_reason
            or "the extracted OCR value is not mappable to an Observation; "
            "W1's 'no Observation' assertion would be vacuous",
            {"candidate": evidence.candidate, **extracted_summary},
        )

    candidate = evidence.candidate
    results: list[Result] = []

    provenance_ok = evidence.provenance_verified is not False
    prov_suffix = f" provenance_error={evidence.provenance_detail}" if not provenance_ok else ""
    results.append(
        Result(
            f"{gate}: OCR value fact",
            PASS if provenance_ok else FAIL,
            f"tesseract value={candidate.get('raw_text')!r} "
            f"unit={candidate.get('unit')!r} confidence={candidate.get('confidence')} "
            f"attempts={list(evidence.attempts)}{prov_suffix}",
            {
                "candidate": candidate,
                "attempts": list(evidence.attempts),
                **(
                    {"provenance": dict(evidence.provenance_detail)}
                    if evidence.provenance_detail
                    else {}
                ),
            },
        )
    )

    decided = evidence.after.get("decision") == "rejected"
    results.append(
        Result(
            f"{gate}: doctor rejection",
            PASS if decided else FAIL,
            f"stored decision={evidence.after.get('decision')!r} "
            f"status={evidence.after.get('verification_status')!r}",
        )
    )

    terminal = evidence.document_status == "failed" and evidence.failure_code == W1_FAILURE_CODE
    results.append(
        Result(
            f"{gate}: terminal failure",
            PASS if terminal else FAIL,
            f"extraction_status={evidence.document_status!r} "
            f"failure_code={evidence.failure_code!r}",
        )
    )

    no_observation = not evidence.promoted_observations
    results.append(
        Result(
            f"{gate}: no Observation",
            PASS if no_observation else FAIL,
            (
                "no Observation references this document's facts"
                if no_observation
                else f"{len(evidence.promoted_observations)} Observation(s) promoted from a "
                f"rejected document: {list(evidence.promoted_observations)}"
            ),
            {"promoted": list(evidence.promoted_observations)},
        )
    )

    # Immutability: the decision sets the status once and rewrites no source text,
    # and exactly one decision row exists.
    before, after = evidence.before, evidence.after
    immutable = (
        after.get("verification_status") == "rejected"
        and after.get("raw_text") == before.get("raw_text")
        and after.get("normalized_value") == before.get("normalized_value")
        and after.get("quality_flags") == before.get("quality_flags")
        and after.get("decision_count") == 1
    )
    results.append(
        Result(
            f"{gate}: fact immutable",
            PASS if immutable else FAIL,
            f"status={after.get('verification_status')!r} "
            f"decisions={after.get('decision_count')} "
            f"raw_text={after.get('raw_text')!r} "
            f"raw_text_before={before.get('raw_text')!r} "
            f"flags_same={after.get('quality_flags') == before.get('quality_flags')}",
            {"before": dict(before), "after": dict(after)},
        )
    )

    open_vi002 = _w1_open_vi002(evidence.issues)
    results.append(
        Result(
            f"{gate}: VI-002 stays open",
            PASS if open_vi002 else FAIL,
            f"open VI-002={[i.get('reason_code') for i in open_vi002]} "
            f"all_issues={[(i.get('issue_type'), i.get('state')) for i in evidence.issues]}",
            {"open_vi002": open_vi002, "issues": [dict(i) for i in evidence.issues]},
        )
    )

    refused = (
        evidence.redecision_status == 409
        and evidence.redecision_code == "E_FACT_ALREADY_DECIDED"
        and evidence.decision_count_after_refusal == 1
    )
    results.append(
        Result(
            f"{gate}: re-decision refused",
            PASS if refused else FAIL,
            f"status={evidence.redecision_status} code={evidence.redecision_code!r} "
            f"stored_decisions={evidence.decision_count_after_refusal}",
        )
    )

    return results


def _w1_read(session_factory, models, document_id: str, fact_id: str) -> dict:
    """Read the refusal-relevant state straight from the database.

    The gate asserts on *stored* values, not on the response body: a response that
    merely claims ``failed`` would prove the API's wording, not the row.
    """
    from sqlalchemy import select

    with session_factory() as session:
        document = session.execute(
            select(models.Document).where(models.Document.id == document_id)
        ).scalar_one()
        fact = session.execute(
            select(models.ExtractedFact).where(models.ExtractedFact.id == fact_id)
        ).scalar_one()
        decisions = list(
            session.execute(
                select(models.FactVerification).where(models.FactVerification.fact_id == fact_id)
            ).scalars()
        )
        fact_ids = {
            row.id
            for row in session.execute(
                select(models.ExtractedFact).where(models.ExtractedFact.document_id == document_id)
            ).scalars()
        }
        promoted = [
            row.id
            for row in session.execute(select(models.Observation)).scalars()
            if row.source_fact_id in fact_ids
        ]
        issues = [
            {
                "issue_type": row.issue_type,
                "reason_code": row.reason_code,
                "state": row.state,
                "blocking": row.blocking,
            }
            for row in session.execute(
                select(models.VerificationIssue).where(
                    models.VerificationIssue.document_id == document_id
                )
            ).scalars()
        ]
        snapshot = {
            "verification_status": fact.verification_status,
            "raw_text": fact.raw_text,
            "normalized_value": fact.normalized_value,
            "quality_flags": fact.quality_flags,
            "decision_count": len(decisions),
            "decision": decisions[0].decision if decisions else None,
        }
        return {
            "document_status": document.extraction_status,
            "failure_code": document.failure_code,
            "promoted_observations": tuple(promoted),
            "issues": tuple(issues),
            "snapshot": snapshot,
        }


def _w1_candidate(facts: list[dict]) -> dict | None:
    """Return a mappable OCR-produced ``value`` fact, or ``None``.

    A ``value`` fact only qualifies when:
    * its extractor is ``tesseract`` (real engine output);
    * it carries non-empty ``raw_text`` and a finite positive numeric
      ``normalized_value``;
    * its ``unit`` is an observation-supported unit (``mmHg``, ``bpm``, ``mg/dL``);
    * its quality flags do not mark the reading unparseable, unit-ambiguous or
      page-missing.

    A candidate lacking any of those could never yield an ``Observation`` even if
    verified, which would make W1's "no Observation" assertion vacuous.
    """
    import math

    from app.core.enums import QualityFlag, Unit

    supported_units = {unit.value for unit in Unit}
    disqualifying_flags = {
        QualityFlag.UNPARSEABLE_VALUE.value,
        QualityFlag.AMBIGUOUS_UNIT.value,
        QualityFlag.PAGE_MISSING.value,
    }

    for fact in facts:
        if fact.get("field_name") != "value":
            continue
        if (fact.get("evidence") or {}).get("extractor") != "tesseract":
            continue
        if not (fact.get("raw_text") or "").strip():
            continue
        flags = set(fact.get("quality_flags") or ())
        if flags & disqualifying_flags:
            continue
        raw_normalized = fact.get("normalized_value")
        if not isinstance(raw_normalized, str) or not raw_normalized.strip():
            continue
        try:
            number = float(raw_normalized.strip().replace(",", "."))
        except ValueError:
            continue
        if not math.isfinite(number) or number <= 0:
            continue
        if fact.get("unit") not in supported_units:
            continue
        return fact
    return None


def _w1_mapping_eligibility(body: dict) -> tuple[bool, str]:
    """Verify the extracted document would promote an Observation if verified.

    Calls the production mapping boundary (``decide_mapping``) on the document's
    extracted facts as if every active fact were verified, and checks that no
    identity/conflict/unread-value blocker would prevent promotion. This guarantees
    W1's "no Observation" assertion is never vacuous on a damaged OCR read.
    """
    from app.core.enums import FactField, IssueType, QualityFlag
    from app.services.documents.mapping import VerifiedFactView, decide_mapping

    facts = body.get("facts") or []
    issues = body.get("verification_issues") or []

    blocking_for_promotion = {
        IssueType.VI_001.value,
        IssueType.VI_003.value,
        IssueType.VI_004.value,
        IssueType.VI_006.value,
    }
    open_blockers = sorted(
        {
            issue["issue_type"]
            for issue in issues
            if issue.get("issue_type") in blocking_for_promotion
        }
    )
    if open_blockers:
        return False, f"blocking issue(s) prevent mapping/promotion: {open_blockers}"

    if any(
        fact.get("field_name") == FactField.VALUE.value
        and QualityFlag.PAGE_MISSING.value in (fact.get("quality_flags") or ())
        for fact in facts
    ):
        return False, "extracted document contains a page_missing value fact"

    views = [
        VerifiedFactView(
            field_name=fact["field_name"],
            normalized_value=fact.get("normalized_value"),
            unit=fact.get("unit"),
            verification_status="verified",
        )
        for fact in facts
    ]
    decision = decide_mapping(views)
    if not decision.is_mapped or decision.mapped is None:
        return False, f"extracted facts are not mappable ({decision.reason})"

    return True, (
        f"eligible for {decision.mapped.measure_type.value} "
        f"{decision.mapped.value} {decision.mapped.unit} at {decision.mapped.measured_at}"
    )


def gate_r21_rejection(results: list[Result], objects: dict | None) -> None:
    """W1: the assigned doctor rejects the real engine's ``value`` fact.

    Reuses the isolated temporary database, seeded app, authorization and cleanup
    that ``gate_api_ocr_upload`` established, so this adds no new infrastructure.
    Every requirement is reported as its own row by ``assess_w1``.
    """
    if objects is None:
        for name in W1_CASES:
            _record(
                results,
                Result(f"W1 R21 rejection: {name}", NOT_RUN, "no Tesseract engine available"),
            )
        return

    from fastapi.testclient import TestClient

    from app.db import models as db_models

    evidence = W1Evidence()
    client = objects["test_client"] if "test_client" in objects else TestClient(objects["app"])
    doctor_headers = {"Authorization": f"Bearer {objects['doctor_token']}"}
    patient_headers = {"Authorization": f"Bearer {objects['patient_token']}"}
    models = objects.get("models", db_models)
    session_factory = objects["session_factory"]

    with client as http:
        upload = http.post(
            "/api/v1/documents/upload",
            headers=patient_headers,
            files={"file": ("glucose.png", objects["image_bytes"], "image/png")},
        )
        if upload.status_code != 202:
            for name in W1_CASES:
                _record(
                    results,
                    Result(
                        f"W1 R21 rejection: {name}",
                        FAIL,
                        f"upload answered {upload.status_code}: {upload.text[:300]}",
                    ),
                )
            return
        document_id = upload.json()["document_id"]

        extraction = http.get(f"/api/v1/documents/{document_id}/extraction", headers=doctor_headers)
        if extraction.status_code != 200:
            for name in W1_CASES:
                _record(
                    results,
                    Result(
                        f"W1 R21 rejection: {name}",
                        FAIL,
                        f"extraction answered {extraction.status_code}: {extraction.text[:300]}",
                    ),
                )
            return

        body = extraction.json()
        evidence.attempts = tuple(
            {"path": a["path"], "succeeded": a["succeeded"]} for a in body["attempts"]
        )
        evidence.extracted_fields = tuple(sorted(f["field_name"] for f in body["facts"]))
        evidence.extracted_facts = tuple(
            {
                "field_name": f.get("field_name"),
                "raw_text": f.get("raw_text"),
                "normalized_value": f.get("normalized_value"),
                "unit": f.get("unit"),
                "quality_flags": list(f.get("quality_flags") or ()),
                "extractor": (f.get("evidence") or {}).get("extractor"),
            }
            for f in body["facts"]
        )
        evidence.verification_issues = tuple(
            {
                "issue_type": issue.get("issue_type"),
                "reason_code": issue.get("reason_code"),
            }
            for issue in body.get("verification_issues", ())
        )
        evidence.non_value_fact_count = sum(
            1 for f in body["facts"] if f.get("field_name") != "value"
        )
        candidate = _w1_candidate(body["facts"])
        eligible, mapping_detail = _w1_mapping_eligibility(body)
        evidence.mapping_eligible = eligible
        evidence.mapping_reason = mapping_detail

        if candidate is None:
            # Honest NOT RUN. The engine ran and produced no mappable value fact;
            # inventing or rejecting an unmappable fact would make "no Observation"
            # vacuous.
            evidence.candidate_absence = (
                "the real engine produced no mappable `value` fact "
                f"({mapping_detail}); "
                f"fields={list(evidence.extracted_fields)} "
                f"facts={list(evidence.extracted_facts)} "
                f"attempts={list(evidence.attempts)}"
            )
            for row in assess_w1(evidence):
                _record(results, row)
            return

        evidence.candidate = {
            "fact_id": candidate["fact_id"],
            "raw_text": candidate["raw_text"],
            "normalized_value": candidate.get("normalized_value"),
            "unit": candidate.get("unit"),
            "confidence": candidate.get("confidence"),
            "verification_status": candidate["verification_status"],
            "extractor": (candidate.get("evidence") or {}).get("extractor"),
            "non_value_fact_count": evidence.non_value_fact_count,
            "mapping_detail": mapping_detail,
        }

        if not eligible:
            # A value fact exists, yet the extracted document as a whole cannot
            # promote an Observation (e.g. mangled test name, missing/ambiguous date,
            # VI-004/VI-006 blocker). Stop before rejection so we never report a
            # vacuous "no Observation" PASS.
            for row in assess_w1(evidence):
                _record(results, row)
            return

        before = _w1_read(session_factory, models, document_id, candidate["fact_id"])
        evidence.before = before["snapshot"]

        rejection = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={
                "fact_id": candidate["fact_id"],
                "decision": "rejected",
                "reason": "OCR reading is not a usable measurement",
            },
        )
        if rejection.status_code != 200:
            # One verdict per requirement. ``after`` stays at its pre-decision
            # snapshot, so ``assess_w1`` reports the rejection as FAIL and every
            # downstream requirement fails with it — no contradicting second row.
            evidence.after = dict(before["snapshot"])
            for row in assess_w1(evidence):
                _record(results, row)
            _record(
                results,
                Result(
                    "W1 R21 rejection detail",
                    FAIL,
                    f"verify answered {rejection.status_code}: {rejection.text[:300]}",
                ),
            )
            return

        stored = _w1_read(session_factory, models, document_id, candidate["fact_id"])
        evidence.after = stored["snapshot"]
        evidence.document_status = stored["document_status"]
        evidence.failure_code = stored["failure_code"]
        evidence.promoted_observations = stored["promoted_observations"]
        evidence.issues = stored["issues"]

        again = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={
                "fact_id": candidate["fact_id"],
                "decision": "verified",
                "reason": "a second decision must be refused",
            },
        )
        evidence.redecision_status = again.status_code
        try:
            evidence.redecision_code = again.json().get("code")
        except ValueError:
            evidence.redecision_code = None

        settled = _w1_read(session_factory, models, document_id, candidate["fact_id"])
        evidence.decision_count_after_refusal = settled["snapshot"]["decision_count"]

        prov_ok, prov_detail = _w1_check_provenance_and_audit(
            session_factory,
            models,
            http=http,
            doctor_headers=doctor_headers,
            document_id=document_id,
        )
        evidence.provenance_verified = prov_ok
        evidence.provenance_detail = prov_detail

        for row in assess_w1(evidence):
            _record(results, row)


def _w1_check_provenance_and_audit(
    session_factory,
    models,
    *,
    http=None,
    doctor_headers: dict[str, str] | None = None,
    document_id: str,
) -> tuple[bool, dict]:
    """Validate persisted OCR page text, exact span equality, extractor, & audit safety."""
    import hashlib

    from sqlalchemy import select

    text_read_status: int | None = None
    source_truth_notice_present = False
    http_text_matches = True
    if http is not None and doctor_headers is not None:
        text_resp = http.get(f"/api/v1/documents/{document_id}/text", headers=doctor_headers)
        text_read_status = text_resp.status_code
        if text_read_status == 200:
            payload = text_resp.json()
            source_truth_notice_present = bool(payload.get("source_truth_notice"))
            http_pages = payload.get("pages") or []
        else:
            http_pages = []
    else:
        http_pages = None

    with session_factory() as session:
        page_rows = list(
            session.execute(
                select(models.DocumentPageText)
                .where(models.DocumentPageText.document_id == document_id)
                .order_by(models.DocumentPageText.page_index)
            ).scalars()
        )
        fact_rows = list(
            session.execute(
                select(models.ExtractedFact).where(models.ExtractedFact.document_id == document_id)
            ).scalars()
        )
        audit_rows = list(session.execute(select(models.AuditEvent)).scalars())

    page_by_index = {row.page_index: row for row in page_rows}
    hash_matches = bool(page_rows) and all(
        row.text_length == len(row.text)
        and row.text_sha256 == hashlib.sha256(row.text.encode("utf-8")).hexdigest()
        for row in page_rows
    )
    page_extractor = page_rows[0].extractor if page_rows else None
    fact_extractors = {row.extractor for row in fact_rows}

    spans_match = bool(fact_rows) and all(
        row.page_index in page_by_index
        and 0 <= row.char_start < row.char_end <= len(page_by_index[row.page_index].text)
        and page_by_index[row.page_index].text[row.char_start : row.char_end] == row.raw_text
        for row in fact_rows
    )

    if http_pages is not None:
        http_text_matches = (
            text_read_status == 200
            and source_truth_notice_present
            and len(http_pages) == len(page_rows)
            and all(
                hp.get("text") == pr.text and hp.get("extractor") == "tesseract"
                for hp, pr in zip(http_pages, page_rows, strict=True)
            )
        )

    sensitive_tokens = ("104", "Fasting glucose", "Reference range", "mg/dL")
    audit_safe = True
    file_read_audits = 0
    text_read_audits = 0
    for audit in audit_rows:
        detail = audit.safe_detail or ""
        if any(tok in detail for tok in sensitive_tokens):
            audit_safe = False
        for pr in page_rows:
            if pr.text and pr.text in detail:
                audit_safe = False
        if audit.event_type == "document.file_read" and audit.subject_id == document_id:
            if audit.outcome == "ok":
                file_read_audits += 1
            else:
                audit_safe = False
        if audit.event_type == "document.text_read" and audit.subject_id == document_id:
            if audit.outcome == "ok":
                text_read_audits += 1
            else:
                audit_safe = False

    ok = (
        len(page_rows) >= 1
        and page_extractor == "tesseract"
        and fact_extractors == {"tesseract"}
        and hash_matches
        and spans_match
        and http_text_matches
        and audit_safe
    )
    return ok, {
        "page_text_count": len(page_rows),
        "page_text_extractor": page_extractor,
        "fact_extractors": sorted(fact_extractors),
        "page_text_hash_matches": hash_matches,
        "spans_match_exactly": spans_match,
        "text_read_status": text_read_status,
        "source_truth_notice_present": source_truth_notice_present,
        "http_text_matches": http_text_matches,
        "file_read_audit_count": file_read_audits,
        "text_read_audit_count": text_read_audits,
        "audit_events_safe": audit_safe,
    }


#: Requirements reported individually by the W1 positive source-confirmation gate.
W1_POSITIVE_CASES = (
    "OCR mappable candidate",
    "bare verify refused",
    "source retrieved and audited",
    "source-confirmed verification",
    "verified Observation created",
    "persisted provenance and audit safety",
)


@dataclass
class W1PositiveEvidence:
    """Measured evidence for the W1 positive source-confirmation control."""

    candidate: dict | None = None
    candidate_absence: str = ""
    non_value_fact_count: int = 0
    extracted_fields: tuple[str, ...] = ()
    extracted_facts: tuple[dict, ...] = ()
    verification_issues: tuple[dict, ...] = ()
    mapping_eligible: bool = True
    mapping_reason: str = ""
    attempts: tuple[dict, ...] = ()
    bare_verify_status: int | None = None
    bare_verify_code: str | None = None
    file_read_status: int | None = None
    file_read_audit_count: int = 0
    text_read_status: int | None = None
    text_read_audit_count: int = 0
    document_status: str | None = None
    value_verification_status: str | None = None
    value_source_image_compared: bool = False
    value_confirmed_value: str | None = None
    value_confirmed_unit: str | None = None
    promoted_observations: tuple[dict, ...] = ()
    page_text_count: int = 0
    page_text_extractor: str | None = None
    page_text_hash_matches: bool = False
    spans_match_exactly: bool = False
    source_truth_notice_present: bool = False
    audit_events_safe: bool = False


def assess_w1_positive(evidence: W1PositiveEvidence) -> list[Result]:
    """Turn measured W1 positive source-confirmation evidence into per-case verdicts."""
    gate = "W1 source confirmation"

    def rows(status: str, detail: str, data: dict | None = None) -> list[Result]:
        return [
            Result(f"{gate}: {name}", status, detail, dict(data or {}))
            for name in W1_POSITIVE_CASES
        ]

    extracted_summary = {
        "extracted_fields": list(evidence.extracted_fields),
        "extracted_facts": list(evidence.extracted_facts),
        "verification_issues": list(evidence.verification_issues),
        "attempts": list(evidence.attempts),
        **({"mapping_reason": evidence.mapping_reason} if evidence.mapping_reason else {}),
    }

    if evidence.candidate is None:
        return rows(
            NOT_RUN,
            evidence.candidate_absence or "no usable OCR value fact",
            extracted_summary,
        )

    if evidence.non_value_fact_count == 0:
        return rows(
            NOT_RUN,
            "the engine produced only a `value` fact; full source-confirmation "
            "promotion requires parsed sibling report fields",
            extracted_summary,
        )

    if not evidence.mapping_eligible or (
        "normalized_value" in evidence.candidate and not evidence.candidate.get("normalized_value")
    ):
        return rows(
            NOT_RUN,
            evidence.mapping_reason or "the extracted OCR value is not mappable to an Observation",
            {"candidate": evidence.candidate, **extracted_summary},
        )

    candidate = evidence.candidate
    results: list[Result] = []

    results.append(
        Result(
            f"{gate}: OCR mappable candidate",
            PASS,
            f"tesseract value={candidate.get('raw_text')!r} "
            f"unit={candidate.get('unit')!r} "
            f"requires_source_confirmation={candidate.get('requires_source_confirmation')}",
            {"candidate": candidate, "attempts": list(evidence.attempts)},
        )
    )

    bare_refused = (
        evidence.bare_verify_status == 400 and evidence.bare_verify_code == "E_VALIDATION"
    )
    results.append(
        Result(
            f"{gate}: bare verify refused",
            PASS if bare_refused else FAIL,
            f"status={evidence.bare_verify_status} code={evidence.bare_verify_code!r}",
        )
    )

    source_audited = (
        evidence.file_read_status == 200
        and evidence.file_read_audit_count >= 1
        and evidence.text_read_status == 200
        and evidence.text_read_audit_count >= 1
    )
    results.append(
        Result(
            f"{gate}: source retrieved and audited",
            PASS if source_audited else FAIL,
            f"file_status={evidence.file_read_status} "
            f"file_audits={evidence.file_read_audit_count} "
            f"text_status={evidence.text_read_status} "
            f"text_audits={evidence.text_read_audit_count}",
        )
    )

    confirmed = (
        evidence.document_status == "verified"
        and evidence.value_verification_status == "verified"
        and evidence.value_source_image_compared is True
        and evidence.value_confirmed_value == candidate.get("normalized_value")
        and evidence.value_confirmed_unit == candidate.get("unit")
    )
    results.append(
        Result(
            f"{gate}: source-confirmed verification",
            PASS if confirmed else FAIL,
            f"doc_status={evidence.document_status!r} "
            f"value_status={evidence.value_verification_status!r} "
            f"source_image_compared={evidence.value_source_image_compared} "
            f"confirmed_value={evidence.value_confirmed_value!r} "
            f"confirmed_unit={evidence.value_confirmed_unit!r}",
        )
    )

    obs = evidence.promoted_observations
    obs_ok = (
        len(obs) == 1
        and obs[0].get("source") == "verified_document"
        and obs[0].get("trust_level") == "doctor_verified"
        and obs[0].get("measure_type") == "glucose"
        and obs[0].get("unit") == "mg/dL"
        and obs[0].get("value") == 104.0
        and obs[0].get("source_fact_id") == candidate.get("fact_id")
    )
    results.append(
        Result(
            f"{gate}: verified Observation created",
            PASS if obs_ok else FAIL,
            f"observations={list(obs)}",
            {"observations": list(obs)},
        )
    )

    provenance_ok = (
        evidence.page_text_count >= 1
        and evidence.page_text_extractor == "tesseract"
        and evidence.page_text_hash_matches is True
        and evidence.spans_match_exactly is True
        and evidence.source_truth_notice_present is True
        and evidence.audit_events_safe is True
    )
    results.append(
        Result(
            f"{gate}: persisted provenance and audit safety",
            PASS if provenance_ok else FAIL,
            f"page_texts={evidence.page_text_count} "
            f"extractor={evidence.page_text_extractor!r} "
            f"hash_ok={evidence.page_text_hash_matches} "
            f"spans_ok={evidence.spans_match_exactly} "
            f"notice={evidence.source_truth_notice_present} "
            f"audit_safe={evidence.audit_events_safe}",
        )
    )

    return results


def gate_source_confirmation(results: list[Result], objects: dict | None) -> None:
    """W1 positive control: bare verify refused -> source read -> confirmed -> Observation."""
    if objects is None:
        for name in W1_POSITIVE_CASES:
            _record(
                results,
                Result(f"W1 source confirmation: {name}", NOT_RUN, "no Tesseract engine available"),
            )
        return

    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db import models as db_models

    evidence = W1PositiveEvidence()
    client = objects["test_client"] if "test_client" in objects else TestClient(objects["app"])
    doctor_headers = {"Authorization": f"Bearer {objects['doctor_token']}"}
    patient_headers = {"Authorization": f"Bearer {objects['patient_token']}"}
    models = objects.get("models", db_models)
    session_factory = objects["session_factory"]

    with client as http:
        upload = http.post(
            "/api/v1/documents/upload",
            headers=patient_headers,
            files={"file": ("glucose.png", objects["image_bytes"], "image/png")},
        )
        if upload.status_code != 202:
            for name in W1_POSITIVE_CASES:
                _record(
                    results,
                    Result(
                        f"W1 source confirmation: {name}",
                        FAIL,
                        f"upload answered {upload.status_code}: {upload.text[:300]}",
                    ),
                )
            return
        document_id = upload.json()["document_id"]

        extraction = http.get(
            f"/api/v1/documents/{document_id}/extraction",
            headers=doctor_headers,
        )
        if extraction.status_code != 200:
            for name in W1_POSITIVE_CASES:
                _record(
                    results,
                    Result(
                        f"W1 source confirmation: {name}",
                        FAIL,
                        f"extraction answered {extraction.status_code}: {extraction.text[:300]}",
                    ),
                )
            return

        body = extraction.json()
        evidence.attempts = tuple(
            {"path": a["path"], "succeeded": a["succeeded"]} for a in body["attempts"]
        )
        evidence.extracted_fields = tuple(sorted(f["field_name"] for f in body["facts"]))
        evidence.extracted_facts = tuple(
            {
                "field_name": f.get("field_name"),
                "raw_text": f.get("raw_text"),
                "normalized_value": f.get("normalized_value"),
                "unit": f.get("unit"),
                "quality_flags": list(f.get("quality_flags") or ()),
                "extractor": (f.get("evidence") or {}).get("extractor"),
            }
            for f in body["facts"]
        )
        evidence.verification_issues = tuple(
            {
                "issue_type": issue.get("issue_type"),
                "reason_code": issue.get("reason_code"),
            }
            for issue in body.get("verification_issues", ())
        )
        evidence.non_value_fact_count = sum(
            1 for f in body["facts"] if f.get("field_name") != "value"
        )
        candidate = _w1_candidate(body["facts"])
        eligible, mapping_detail = _w1_mapping_eligibility(body)
        evidence.mapping_eligible = eligible
        evidence.mapping_reason = mapping_detail

        if candidate is None:
            evidence.candidate_absence = (
                "the real engine produced no mappable `value` fact "
                f"({mapping_detail}); fields={list(evidence.extracted_fields)} "
                f"facts={list(evidence.extracted_facts)} attempts={list(evidence.attempts)}"
            )
            for row in assess_w1_positive(evidence):
                _record(results, row)
            return

        evidence.candidate = {
            "fact_id": candidate["fact_id"],
            "raw_text": candidate["raw_text"],
            "normalized_value": candidate.get("normalized_value"),
            "unit": candidate.get("unit"),
            "confidence": candidate.get("confidence"),
            "verification_status": candidate["verification_status"],
            "extractor": (candidate.get("evidence") or {}).get("extractor"),
            "requires_source_confirmation": candidate.get("requires_source_confirmation"),
        }

        if not eligible or evidence.non_value_fact_count == 0:
            for row in assess_w1_positive(evidence):
                _record(results, row)
            return

        # 1. Bare `verified` request without source review or confirmations must be refused.
        bare = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={"fact_id": candidate["fact_id"], "decision": "verified"},
        )
        evidence.bare_verify_status = bare.status_code
        try:
            evidence.bare_verify_code = bare.json().get("code")
        except ValueError:
            evidence.bare_verify_code = None

        # 2. Doctor retrieves original image (`GET /file`) and OCR page text (`GET /text`).
        file_resp = http.get(
            f"/api/v1/documents/{document_id}/file",
            headers=doctor_headers,
        )
        evidence.file_read_status = file_resp.status_code

        prov_ok, prov_detail = _w1_check_provenance_and_audit(
            session_factory,
            models,
            http=http,
            doctor_headers=doctor_headers,
            document_id=document_id,
        )

        # 3. Doctor explicitly confirms numeric value and unit after source comparison.
        for fact in body["facts"]:
            verify_body: dict[str, object] = {
                "fact_id": fact["fact_id"],
                "decision": "verified",
                "reason": "doctor confirmed reading against original source scan",
            }
            if fact["field_name"] == "value":
                verify_body["source_image_compared"] = True
                verify_body["confirmed_value"] = fact["normalized_value"]
                verify_body["confirmed_unit"] = fact["unit"]
            elif fact["field_name"] == "unit":
                verify_body["source_image_compared"] = True
                verify_body["confirmed_unit"] = fact["normalized_value"]
            elif fact.get("requires_source_confirmation"):
                verify_body["source_image_compared"] = True
                verify_body["confirmed_value"] = fact["normalized_value"]
            verify = http.post(
                f"/api/v1/documents/{document_id}/verify",
                headers=doctor_headers,
                json=verify_body,
            )
            if verify.status_code != 200:
                break

        with session_factory() as session:
            doc = session.execute(
                select(models.Document).where(models.Document.id == document_id)
            ).scalar_one()
            val_fact = session.execute(
                select(models.ExtractedFact).where(models.ExtractedFact.id == candidate["fact_id"])
            ).scalar_one()
            val_decisions = list(
                session.execute(
                    select(models.FactVerification).where(
                        models.FactVerification.fact_id == candidate["fact_id"]
                    )
                ).scalars()
            )
            fact_ids = [f["fact_id"] for f in body["facts"]]
            obs_rows = list(
                session.execute(
                    select(models.Observation).where(
                        models.Observation.source_fact_id.in_(fact_ids)
                    )
                ).scalars()
            )
            evidence.document_status = doc.extraction_status
            evidence.value_verification_status = val_fact.verification_status
            if val_decisions:
                evidence.value_source_image_compared = bool(val_decisions[0].source_image_compared)
                evidence.value_confirmed_value = val_decisions[0].confirmed_value
                evidence.value_confirmed_unit = val_decisions[0].confirmed_unit
            evidence.promoted_observations = tuple(
                {
                    "id": o.id,
                    "source": o.source,
                    "trust_level": o.trust_level,
                    "measure_type": o.measure_type,
                    "value": o.value,
                    "unit": o.unit,
                    "source_fact_id": o.source_fact_id,
                }
                for o in obs_rows
            )

        # Re-evaluate provenance & audit safety after all verification calls completed.
        prov_ok_after, prov_detail_after = _w1_check_provenance_and_audit(
            session_factory,
            models,
            http=http,
            doctor_headers=doctor_headers,
            document_id=document_id,
        )
        evidence.text_read_status = prov_detail.get("text_read_status")
        evidence.file_read_audit_count = int(prov_detail_after.get("file_read_audit_count", 0))
        evidence.text_read_audit_count = int(prov_detail_after.get("text_read_audit_count", 0))
        evidence.page_text_count = int(prov_detail_after.get("page_text_count", 0))
        evidence.page_text_extractor = prov_detail_after.get("page_text_extractor")
        evidence.page_text_hash_matches = bool(
            prov_detail_after.get("page_text_hash_matches", False)
        )
        evidence.spans_match_exactly = bool(prov_detail_after.get("spans_match_exactly", False))
        evidence.source_truth_notice_present = bool(
            prov_detail_after.get("source_truth_notice_present", False)
        )
        evidence.audit_events_safe = bool(
            prov_ok and prov_ok_after and prov_detail_after.get("audit_events_safe", False)
        )

        for row in assess_w1_positive(evidence):
            _record(results, row)


def gate_r21_rejection_is_mappable(results: list[Result]) -> bool:
    """Fail early if W1's fixture is not the mappable glucose report.

    W1 asserts that *no* Observation was promoted. That only means something when
    the rejected value would otherwise have mapped, so the fixture is checked
    through the parser and ``decide_mapping`` rather than assumed — an unsupported
    measurement would make the assertion vacuous while still reading as a PASS.
    """
    from app.core.enums import ExtractionPath
    from app.services.documents.field_parser import parse_pages
    from app.services.documents.mapping import VerifiedFactView, decide_mapping
    from app.services.documents.text_extraction import PageText

    gate = "W1 R21 rejection: OCR value fact"
    source = SOURCES / W1_SOURCE_NAME
    if not source.is_file():
        _record(results, Result(gate, FAIL, f"missing committed fixture {W1_SOURCE_NAME}"))
        return False
    text = source.read_text(encoding="utf-8", errors="replace")
    parsed = parse_pages(
        [PageText(page_index=0, text=text, extractor=ExtractionPath.TESSERACT, confidence=1.0)]
    )
    views = [
        VerifiedFactView(
            field_name=fact.field_name.value,
            normalized_value=fact.normalized_value,
            unit=fact.unit,
            verification_status="verified",
        )
        for fact in parsed.facts
    ]
    decision = decide_mapping(views)
    if "mg/dL" not in text or "glucose" not in text.lower() or not decision.is_mapped:
        _record(
            results,
            Result(
                gate,
                FAIL,
                f"{W1_SOURCE_NAME} is not a mappable glucose report "
                f"(mapping_reason={decision.reason}): W1's 'no Observation' "
                "assertion would be vacuous",
            ),
        )
        return False
    return True


def _w1_teardown(seam: dict) -> list[str]:
    """Release W1's seam, returning any teardown problems for the caller to record."""
    errors: list[str] = []
    engine = seam.get("engine")
    if engine is not None:
        try:
            engine.dispose()
        except Exception as error:  # pragma: no cover - defensive
            errors.append(f"engine: {type(error).__name__}: {error}")
    try:
        from app.db.session import dispose_engines

        dispose_engines(seam["database_url"])
    except Exception as error:  # pragma: no cover - defensive
        errors.append(f"cached engine: {type(error).__name__}: {error}")
    try:
        for name, previous in seam["saved_env"].items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous
    except Exception as error:  # pragma: no cover - defensive
        errors.append(f"environment restore: {type(error).__name__}: {error}")
    try:
        from app.core.config import reset_settings_cache

        reset_settings_cache()
    except Exception as error:  # pragma: no cover - defensive
        errors.append(f"settings cache: {type(error).__name__}: {error}")
    try:
        shutil.rmtree(seam["tmp"])
    except OSError as error:
        # On Windows a retained SQLite handle makes this raise WinError 32.
        errors.append(f"temporary directory: {type(error).__name__}: {error}")
    return errors


def _w1_run(results: list[Result], *, engine_present: bool) -> None:
    """Own W1 end to end: build the isolated seam, judge, then always tear down.

    Cleanup lives here rather than in the gate so the temporary database and the
    restored environment are released on every path — including the honest
    ``NOT RUN`` when the engine produced no candidate and a mid-setup failure.
    """
    if not engine_present:
        gate_r21_rejection(results, None)
        return

    tmp = tempfile.mkdtemp(prefix="p3-w1-")
    saved_env = {name: os.environ.get(name) for name in _PROBE_ENV_KEYS}
    seam = None
    try:
        seam = _isolated_app(tmp)
        gate_r21_rejection(results, seam)
    except Exception as error:
        detail = f"unexpected {type(error).__name__}: {error}\n{traceback.format_exc(limit=3)}"
        recorded_any = False
        for name in W1_CASES:
            gate = f"W1 R21 rejection: {name}"
            if not _verdicts_for(results, gate):
                _record(results, Result(gate, FAIL, detail))
                recorded_any = True
        if not recorded_any:
            _record(results, Result("W1 R21 rejection error", FAIL, detail))
    finally:
        teardown_seam = (
            dict(seam)
            if seam is not None
            else {
                "engine": None,
                "database_url": f"sqlite:///{(Path(tmp) / 'accept.db').as_posix()}",
            }
        )
        teardown_seam["saved_env"] = saved_env
        teardown_seam["tmp"] = tmp
        problems = _w1_teardown(teardown_seam)
        if problems:
            _record(
                results,
                Result(
                    "W1 R21 rejection cleanup",
                    FAIL,
                    "; ".join(problems),
                    {"cleanup_errors": problems},
                ),
            )


def _w1_positive_run(results: list[Result], *, engine_present: bool) -> None:
    """Own the W1 positive source-confirmation control end to end in a fresh DB."""
    if not engine_present:
        gate_source_confirmation(results, None)
        return

    tmp = tempfile.mkdtemp(prefix="p3-w1-pos-")
    saved_env = {name: os.environ.get(name) for name in _PROBE_ENV_KEYS}
    seam = None
    try:
        seam = _isolated_app(tmp)
        gate_source_confirmation(results, seam)
    except Exception as error:
        detail = f"unexpected {type(error).__name__}: {error}\n{traceback.format_exc(limit=3)}"
        recorded_any = False
        for name in W1_POSITIVE_CASES:
            gate = f"W1 source confirmation: {name}"
            if not _verdicts_for(results, gate):
                _record(results, Result(gate, FAIL, detail))
                recorded_any = True
        if not recorded_any:
            _record(results, Result("W1 source confirmation error", FAIL, detail))
    finally:
        teardown_seam = (
            dict(seam)
            if seam is not None
            else {
                "engine": None,
                "database_url": f"sqlite:///{(Path(tmp) / 'accept.db').as_posix()}",
            }
        )
        teardown_seam["saved_env"] = saved_env
        teardown_seam["tmp"] = tmp
        problems = _w1_teardown(teardown_seam)
        if problems:
            _record(
                results,
                Result(
                    "W1 source confirmation cleanup",
                    FAIL,
                    "; ".join(problems),
                    {"cleanup_errors": problems},
                ),
            )


# --- W2: non-vacuous source-aware acceptance on real `1O5` fixture (FC-3) ----

W2_SOURCE_NAME = "report_ocr_o_confusion.txt"
#: Committed canonical LF SHA-256 and byte length from ``data/synthetic/documents/manifest.json``.
W2_SOURCE_SHA256 = "0f8cae895dff04f3017b32d3e2d9b5e50e75c60f2498cb188991c749732c2492"
W2_SOURCE_SIZE_BYTES = 200

W2_CASES = (
    "source fixture intact",
    "OCR mappable 105 candidate",
    "no autonomous promotion",
    "unreviewed verify refused",
    "R21 rejection blocks promotion",
)


@dataclass
class W2Evidence:
    """Measured evidence for the non-vacuous W2 / FC-3 gate on real ``1O5``."""

    fixture_has_1o5: bool = False
    fixture_source_sha256_matches: bool = False
    upload_sha256_matches: bool = False
    tesseract_attempt_succeeded: bool = False
    page_text_extractor: str | None = None
    page_text_hash_matches: bool = False
    preserved_1o5_refused: bool = False
    gold_ex_11_passed: bool = False
    candidate: dict | None = None
    candidate_absence: str = ""
    non_value_fact_count: int = 0
    all_facts_pending: bool = False
    all_facts_tesseract: bool = False
    all_facts_require_source: bool = False
    extracted_fields: tuple[str, ...] = ()
    extracted_facts: tuple[dict, ...] = ()
    verification_issues: tuple[dict, ...] = ()
    mapping_eligible: bool = True
    mapping_reason: str = ""
    attempts: tuple[dict, ...] = ()
    pre_verify_observation_count: int = 0
    bare_verify_status: int | None = None
    bare_verify_code: str | None = None
    unreviewed_flag_verify_status: int | None = None
    unreviewed_flag_verify_code: str | None = None
    post_refusal_observation_count: int = 0
    post_refusal_decision_count: int = 0
    rejection_status: int | None = None
    document_status: str | None = None
    failure_code: str | None = None
    post_rejection_observations: tuple[str, ...] = ()
    redecision_status: int | None = None
    redecision_code: str | None = None
    vi002_open_count: int = 0
    audit_events_safe: bool = False
    precondition_failure: str = ""


def assess_w2(evidence: W2Evidence) -> list[Result]:
    """Turn measured W2/FC-3 evidence into non-vacuous per-requirement verdicts."""
    gate = "W2 FC-3 source-aware"

    def rows(status: str, detail: str, data: dict | None = None) -> list[Result]:
        return [Result(f"{gate}: {name}", status, detail, dict(data or {})) for name in W2_CASES]

    extracted_summary = {
        "extracted_fields": list(evidence.extracted_fields),
        "extracted_facts": list(evidence.extracted_facts),
        "verification_issues": list(evidence.verification_issues),
        "attempts": list(evidence.attempts),
        **({"mapping_reason": evidence.mapping_reason} if evidence.mapping_reason else {}),
    }

    if evidence.precondition_failure:
        return rows(FAIL, evidence.precondition_failure, extracted_summary)

    if not evidence.fixture_has_1o5 or not evidence.fixture_source_sha256_matches:
        return rows(
            FAIL,
            f"W2 fixture {W2_SOURCE_NAME} failed pinned source SHA-256/size verification "
            f"(expected sha256={W2_SOURCE_SHA256}, size={W2_SOURCE_SIZE_BYTES}, literal '1O5')",
            extracted_summary,
        )
    if not evidence.upload_sha256_matches:
        return rows(
            FAIL, "uploaded document SHA-256 does not match W2 PNG bytes", extracted_summary
        )
    if (
        not evidence.tesseract_attempt_succeeded
        or evidence.page_text_extractor != "tesseract"
        or not evidence.page_text_hash_matches
    ):
        return rows(
            FAIL,
            "missing or mismatched persisted tesseract extraction attempt / page text provenance",
            extracted_summary,
        )
    if evidence.pre_verify_observation_count != 0:
        return rows(
            FAIL,
            f"autonomous Observation promotion occurred before verification "
            f"({evidence.pre_verify_observation_count} Observation(s))",
            extracted_summary,
        )

    if evidence.candidate is None and evidence.gold_ex_11_passed and evidence.preserved_1o5_refused:
        return rows(
            DERIVED,
            "not applicable (DERIVED from GOLD-EX-11 PASS): independent GOLD-EX-11 "
            "passed with OCR preserving literal '1O5' and parser refusing it as "
            "unparseable_value (0 Observations); false-clean 105 counterexample did not arise",
            extracted_summary,
        )

    if evidence.candidate is None:
        return rows(
            NOT_RUN,
            evidence.candidate_absence
            or "real OCR preserved literal '1O5' or produced no mappable 105 mg/dL value fact",
            extracted_summary,
        )

    if evidence.non_value_fact_count == 0:
        return rows(
            NOT_RUN,
            "real OCR produced only a value fact without sibling labels; non-vacuous FC-3 requires sibling layout",
            extracted_summary,
        )

    if not evidence.mapping_eligible or not evidence.candidate.get("normalized_value"):
        return rows(
            NOT_RUN,
            evidence.mapping_reason
            or "extracted OCR facts are not mapping-eligible for an Observation",
            {"candidate": evidence.candidate, **extracted_summary},
        )

    if (
        evidence.candidate.get("normalized_value") != "105"
        or evidence.candidate.get("unit") != "mg/dL"
    ):
        return rows(
            NOT_RUN,
            f"expected substituted 105 mg/dL glucose candidate on 1O5 fixture, got "
            f"{evidence.candidate.get('normalized_value')!r} {evidence.candidate.get('unit')!r}",
            {"candidate": evidence.candidate, **extracted_summary},
        )

    candidate = evidence.candidate
    fixture_ok = (
        evidence.fixture_has_1o5
        and evidence.fixture_source_sha256_matches
        and evidence.upload_sha256_matches
        and evidence.tesseract_attempt_succeeded
        and evidence.page_text_extractor == "tesseract"
        and evidence.page_text_hash_matches
    )
    candidate_ok = (
        evidence.all_facts_pending
        and evidence.all_facts_tesseract
        and evidence.all_facts_require_source
        and evidence.mapping_eligible
        and candidate.get("normalized_value") == "105"
        and candidate.get("unit") == "mg/dL"
    )
    no_auto_ok = evidence.pre_verify_observation_count == 0
    refusal_ok = (
        evidence.bare_verify_status == 400
        and evidence.bare_verify_code == "E_VALIDATION"
        and evidence.unreviewed_flag_verify_status == 400
        and evidence.unreviewed_flag_verify_code == "E_VALIDATION"
        and evidence.post_refusal_observation_count == 0
        and evidence.post_refusal_decision_count == 0
    )
    rejection_ok = (
        evidence.rejection_status == 200
        and evidence.document_status == "failed"
        and evidence.failure_code == W1_FAILURE_CODE
        and not evidence.post_rejection_observations
        and evidence.redecision_status == 409
        and evidence.redecision_code == "E_FACT_ALREADY_DECIDED"
        and evidence.vi002_open_count >= 1
        and evidence.audit_events_safe
    )

    return [
        Result(
            f"{gate}: source fixture intact",
            PASS if fixture_ok else FAIL,
            f"fixture_has_1o5={evidence.fixture_has_1o5} "
            f"sha_match={evidence.upload_sha256_matches} "
            f"tesseract={evidence.tesseract_attempt_succeeded} "
            f"page_ext={evidence.page_text_extractor!r} "
            f"page_hash={evidence.page_text_hash_matches}",
            {"attempts": list(evidence.attempts)},
        ),
        Result(
            f"{gate}: OCR mappable 105 candidate",
            PASS if candidate_ok else FAIL,
            f"value={candidate.get('normalized_value')!r} unit={candidate.get('unit')!r} "
            f"siblings={evidence.non_value_fact_count} pending={evidence.all_facts_pending} "
            f"tesseract={evidence.all_facts_tesseract} req_src={evidence.all_facts_require_source}",
            {"candidate": candidate},
        ),
        Result(
            f"{gate}: no autonomous promotion",
            PASS if no_auto_ok else FAIL,
            f"pre_verify_observations={evidence.pre_verify_observation_count}",
        ),
        Result(
            f"{gate}: unreviewed verify refused",
            PASS if refusal_ok else FAIL,
            f"bare=({evidence.bare_verify_status}, {evidence.bare_verify_code!r}) "
            f"unreviewed_flag=({evidence.unreviewed_flag_verify_status}, {evidence.unreviewed_flag_verify_code!r}) "
            f"post_obs={evidence.post_refusal_observation_count} "
            f"post_decisions={evidence.post_refusal_decision_count}",
        ),
        Result(
            f"{gate}: R21 rejection blocks promotion",
            PASS if rejection_ok else FAIL,
            f"rej={evidence.rejection_status} doc={evidence.document_status!r} "
            f"code={evidence.failure_code!r} obs={list(evidence.post_rejection_observations)} "
            f"redec=({evidence.redecision_status}, {evidence.redecision_code!r}) "
            f"vi002={evidence.vi002_open_count} audit_safe={evidence.audit_events_safe}",
        ),
    ]


def gate_w2_fc3(
    results: list[Result], objects: dict | None, *, gold_ex_11_passed: bool = False
) -> None:
    """W2 / FC-3: non-vacuous source-aware acceptance on the real ``1O5`` fixture."""
    if objects is None:
        for name in W2_CASES:
            _record(
                results,
                Result(f"W2 FC-3 source-aware: {name}", NOT_RUN, "no Tesseract engine available"),
            )
        return

    import hashlib

    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db import models as db_models

    evidence = W2Evidence(gold_ex_11_passed=gold_ex_11_passed)
    source_path = SOURCES / W2_SOURCE_NAME
    if not source_path.is_file():
        evidence.precondition_failure = f"missing committed W2 fixture {W2_SOURCE_NAME}"
        for row in assess_w2(evidence):
            _record(results, row)
        return
    canonical = source_path.read_bytes().replace(b"\r\n", b"\n")
    actual_sha256 = hashlib.sha256(canonical).hexdigest()
    actual_size = len(canonical)
    evidence.fixture_has_1o5 = b"1O5" in canonical
    evidence.fixture_source_sha256_matches = (
        actual_sha256 == W2_SOURCE_SHA256 and actual_size == W2_SOURCE_SIZE_BYTES
    )
    if not evidence.fixture_has_1o5 or not evidence.fixture_source_sha256_matches:
        for row in assess_w2(evidence):
            _record(results, row)
        return

    client = objects["test_client"] if "test_client" in objects else TestClient(objects["app"])
    doctor_headers = {"Authorization": f"Bearer {objects['doctor_token']}"}
    patient_headers = {"Authorization": f"Bearer {objects['patient_token']}"}
    models = objects.get("models", db_models)
    session_factory = objects["session_factory"]
    expected_sha256 = hashlib.sha256(objects["image_bytes"]).hexdigest()

    with client as http:
        upload = http.post(
            "/api/v1/documents/upload",
            headers=patient_headers,
            files={"file": ("ocr_1o5.png", objects["image_bytes"], "image/png")},
        )
        if upload.status_code != 202:
            evidence.precondition_failure = (
                f"upload answered {upload.status_code}: {upload.text[:300]}"
            )
            for row in assess_w2(evidence):
                _record(results, row)
            return
        document_id = upload.json()["document_id"]

        extraction = http.get(
            f"/api/v1/documents/{document_id}/extraction",
            headers=doctor_headers,
        )
        if extraction.status_code != 200:
            evidence.precondition_failure = (
                f"extraction answered {extraction.status_code}: {extraction.text[:300]}"
            )
            for row in assess_w2(evidence):
                _record(results, row)
            return

        body = extraction.json()
        evidence.attempts = tuple(
            {"path": a["path"], "succeeded": a["succeeded"]} for a in body["attempts"]
        )
        facts = body["facts"]
        evidence.extracted_fields = tuple(sorted(f["field_name"] for f in facts))
        evidence.extracted_facts = tuple(
            {
                "field_name": f.get("field_name"),
                "raw_text": f.get("raw_text"),
                "normalized_value": f.get("normalized_value"),
                "unit": f.get("unit"),
                "quality_flags": list(f.get("quality_flags") or ()),
                "extractor": (f.get("evidence") or {}).get("extractor"),
            }
            for f in facts
        )
        evidence.verification_issues = tuple(
            {
                "issue_type": issue.get("issue_type"),
                "reason_code": issue.get("reason_code"),
            }
            for issue in body.get("verification_issues", ())
        )
        evidence.non_value_fact_count = sum(1 for f in facts if f.get("field_name") != "value")
        evidence.all_facts_pending = bool(facts) and all(
            f.get("verification_status") == "pending" for f in facts
        )
        evidence.all_facts_tesseract = bool(facts) and all(
            (f.get("evidence") or {}).get("extractor") == "tesseract" for f in facts
        )
        evidence.all_facts_require_source = bool(facts) and all(
            f.get("requires_source_confirmation") is True for f in facts
        )

        with session_factory() as session:
            doc = session.execute(
                select(models.Document).where(models.Document.id == document_id)
            ).scalar_one()
            evidence.upload_sha256_matches = doc.sha256 == expected_sha256
            attempts_db = list(
                session.execute(
                    select(models.ExtractionAttempt).where(
                        models.ExtractionAttempt.document_id == document_id
                    )
                ).scalars()
            )
            evidence.tesseract_attempt_succeeded = any(
                a.path == "tesseract" and a.succeeded == 1 for a in attempts_db
            )
            page_rows = list(
                session.execute(
                    select(models.DocumentPageText)
                    .where(models.DocumentPageText.document_id == document_id)
                    .order_by(models.DocumentPageText.page_index)
                ).scalars()
            )
            evidence.page_text_extractor = page_rows[0].extractor if page_rows else None
            evidence.page_text_hash_matches = bool(page_rows) and all(
                pr.text_length == len(pr.text)
                and pr.text_sha256 == hashlib.sha256(pr.text.encode("utf-8")).hexdigest()
                for pr in page_rows
            )
            fact_ids = [f["fact_id"] for f in facts]
            pre_obs = (
                list(
                    session.execute(
                        select(models.Observation).where(
                            models.Observation.source_fact_id.in_(fact_ids)
                        )
                    ).scalars()
                )
                if fact_ids
                else []
            )
            evidence.pre_verify_observation_count = len(pre_obs)

            value_facts = [f for f in facts if f.get("field_name") == "value"]
            has_preserved_1o5_page = bool(page_rows) and any("1O5" in pr.text for pr in page_rows)
            has_unparseable_1o5_fact = any(
                "unparseable_value" in (vf.get("quality_flags") or ())
                and vf.get("normalized_value") is None
                and "1O5" in (vf.get("raw_text") or "")
                for vf in value_facts
            )
            has_any_numeric_value_fact = any(
                vf.get("normalized_value") is not None for vf in value_facts
            )
            evidence.preserved_1o5_refused = (
                has_preserved_1o5_page
                and has_unparseable_1o5_fact
                and not has_any_numeric_value_fact
            )

        candidate = _w1_candidate(facts)
        eligible, mapping_detail = _w1_mapping_eligibility(body)
        evidence.mapping_eligible = eligible
        evidence.mapping_reason = mapping_detail

        if candidate is None:
            evidence.candidate_absence = (
                "OCR preserved '1O5' or produced no mappable 105 mg/dL `value` fact "
                f"({mapping_detail}); fields={list(evidence.extracted_fields)} "
                f"facts={list(evidence.extracted_facts)}"
            )
            for row in assess_w2(evidence):
                _record(results, row)
            return

        evidence.candidate = {
            "fact_id": candidate["fact_id"],
            "raw_text": candidate["raw_text"],
            "normalized_value": candidate.get("normalized_value"),
            "unit": candidate.get("unit"),
            "confidence": candidate.get("confidence"),
            "verification_status": candidate["verification_status"],
            "extractor": (candidate.get("evidence") or {}).get("extractor"),
            "requires_source_confirmation": candidate.get("requires_source_confirmation"),
        }

        if (
            not eligible
            or evidence.non_value_fact_count == 0
            or candidate.get("normalized_value") != "105"
            or candidate.get("unit") != "mg/dL"
        ):
            for row in assess_w2(evidence):
                _record(results, row)
            return

        # 1. Negative controls BEFORE any GET /file: bare verify & unreviewed flag both refused.
        bare = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={"fact_id": candidate["fact_id"], "decision": "verified"},
        )
        evidence.bare_verify_status = bare.status_code
        try:
            evidence.bare_verify_code = bare.json().get("code")
        except ValueError:
            evidence.bare_verify_code = None

        unreviewed = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={
                "fact_id": candidate["fact_id"],
                "decision": "verified",
                "source_image_compared": True,
                "confirmed_value": "105",
                "confirmed_unit": "mg/dL",
                "reason": "unreviewed attestation before GET /file",
            },
        )
        evidence.unreviewed_flag_verify_status = unreviewed.status_code
        try:
            evidence.unreviewed_flag_verify_code = unreviewed.json().get("code")
        except ValueError:
            evidence.unreviewed_flag_verify_code = None

        mid_read = _w1_read(session_factory, models, document_id, candidate["fact_id"])
        evidence.post_refusal_observation_count = len(mid_read["promoted_observations"])
        evidence.post_refusal_decision_count = int(mid_read["snapshot"]["decision_count"])

        # 2. R21 rejection on substituted 105 blocks promotion & re-decision without needing GET /file.
        rejection = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={
                "fact_id": candidate["fact_id"],
                "decision": "rejected",
                "reason": "source scan carries ambiguous 1O5 character; reject OCR 105",
            },
        )
        evidence.rejection_status = rejection.status_code

        stored = _w1_read(session_factory, models, document_id, candidate["fact_id"])
        evidence.document_status = stored["document_status"]
        evidence.failure_code = stored["failure_code"]
        evidence.post_rejection_observations = stored["promoted_observations"]
        evidence.vi002_open_count = len(_w1_open_vi002(stored["issues"]))

        again = http.post(
            f"/api/v1/documents/{document_id}/verify",
            headers=doctor_headers,
            json={
                "fact_id": candidate["fact_id"],
                "decision": "verified",
                "reason": "second decision must be refused",
            },
        )
        evidence.redecision_status = again.status_code
        try:
            evidence.redecision_code = again.json().get("code")
        except ValueError:
            evidence.redecision_code = None

        # 3. Audit safety: zero OCR text tokens leaked into AuditEvent.safe_detail.
        sensitive_tokens = ("105", "1O5", "Fasting glucose", "Reference range", "mg/dL")
        with session_factory() as session:
            page_texts = list(
                session.execute(
                    select(models.DocumentPageText).where(
                        models.DocumentPageText.document_id == document_id
                    )
                ).scalars()
            )
            audit_rows = list(session.execute(select(models.AuditEvent)).scalars())
        audit_safe = True
        for audit in audit_rows:
            detail = audit.safe_detail or ""
            if any(tok in detail for tok in sensitive_tokens):
                audit_safe = False
            for pt in page_texts:
                if pt.text and pt.text in detail:
                    audit_safe = False
        evidence.audit_events_safe = audit_safe

        for row in assess_w2(evidence):
            _record(results, row)


def _w2_run(
    results: list[Result], *, engine_present: bool, gold_ex_11_passed: bool = False
) -> None:
    """Own W2/FC-3 end to end on the real ``1O5`` fixture in an isolated temporary DB."""
    if not engine_present:
        gate_w2_fc3(results, None, gold_ex_11_passed=gold_ex_11_passed)
        return

    tmp = tempfile.mkdtemp(prefix="p3-w2-")
    saved_env = {name: os.environ.get(name) for name in _PROBE_ENV_KEYS}
    seam = None
    try:
        seam = _isolated_app(tmp, source_name=W2_SOURCE_NAME)
        gate_w2_fc3(results, seam, gold_ex_11_passed=gold_ex_11_passed)
    except Exception as error:
        detail = f"unexpected {type(error).__name__}: {error}\n{traceback.format_exc(limit=3)}"
        recorded_any = False
        for name in W2_CASES:
            gate = f"W2 FC-3 source-aware: {name}"
            if not _verdicts_for(results, gate):
                _record(results, Result(gate, FAIL, detail))
                recorded_any = True
        if not recorded_any:
            _record(results, Result("W2 FC-3 source-aware error", FAIL, detail))
    finally:
        teardown_seam = (
            dict(seam)
            if seam is not None
            else {
                "engine": None,
                "database_url": f"sqlite:///{(Path(tmp) / 'accept.db').as_posix()}",
            }
        )
        teardown_seam["saved_env"] = saved_env
        teardown_seam["tmp"] = tmp
        problems = _w1_teardown(teardown_seam)
        if problems:
            _record(
                results,
                Result(
                    "W2 FC-3 source-aware cleanup",
                    FAIL,
                    "; ".join(problems),
                    {"cleanup_errors": problems},
                ),
            )


def main(argv: list[str]) -> int:
    """Run every Windows-only gate and return 0 only if none is NOT RUN/FAIL."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None, help="write the results as JSON")
    args = parser.parse_args(argv[1:])

    if not SOURCES.is_dir():
        print(f"FAIL: fixture sources not found at {SOURCES}", file=sys.stderr)
        return 2

    system_path = str(REPO_ROOT / "scripts" / "python")
    if system_path not in sys.path:
        sys.path.insert(0, system_path)

    results: list[Result] = []
    _guarded(results, "ENV-01/02 environment", lambda: gate_environment(results))
    executable = _guarded(results, "OCR-ENGINE", lambda: gate_engine(results))
    engine_present = executable is not None

    _guarded(
        results,
        "GOLD-EX-05/06/OCR-LIVE-01",
        lambda: gate_ocr_live(results, engine_present=engine_present),
    )
    _guarded(
        results,
        "GOLD-EX-11 OCR-produced 1O5",
        lambda: gate_ocr_corruption(results, engine_present=engine_present),
    )
    _guarded(results, "PDFIUM-01 rasterize", lambda: gate_rasterizer(results))
    _guarded(
        results,
        "ING-02 OCR upload end-to-end",
        lambda: gate_api_ocr_upload(results, engine_present=engine_present),
    )
    # W1 is the R21 rejection + positive source-confirmation gate pair. The fixture guard
    # runs first: if the source is not the mappable glucose report, W1's assertions would
    # be vacuous, so it fails loudly instead of passing hollowly.
    mappable_ok = _guarded(
        results,
        "W1 R21 rejection: OCR value fact",
        lambda: gate_r21_rejection_is_mappable(results),
    )
    if mappable_ok:
        _guarded(
            results,
            "W1 R21 rejection",
            lambda: _w1_run(results, engine_present=engine_present),
        )
        _guarded(
            results,
            "W1 source confirmation",
            lambda: _w1_positive_run(results, engine_present=engine_present),
        )
    else:
        detail = (
            _verdicts_for(results, "W1 R21 rejection: OCR value fact")[-1].detail
            if _verdicts_for(results, "W1 R21 rejection: OCR value fact")
            else "W1 source fixture is not mappable"
        )
        for name in W1_CASES:
            gate = f"W1 R21 rejection: {name}"
            if not _verdicts_for(results, gate):
                _record(results, Result(gate, FAIL, detail))
        for name in W1_POSITIVE_CASES:
            gate = f"W1 source confirmation: {name}"
            if not _verdicts_for(results, gate):
                _record(results, Result(gate, FAIL, detail))

    gold_ex_11_verdicts = _verdicts_for(results, "GOLD-EX-11 OCR-produced 1O5")
    gold_ex_11_passed = len(gold_ex_11_verdicts) == 1 and gold_ex_11_verdicts[0].status == PASS
    _guarded(
        results,
        "W2 FC-3 source-aware",
        lambda: _w2_run(
            results,
            engine_present=engine_present,
            gold_ex_11_passed=gold_ex_11_passed,
        ),
    )

    print()
    print("=" * 78)
    for result in results:
        print(f"{result.status:>7}  {result.gate}")
    failures = [result for result in results if result.status not in {PASS, DERIVED}]
    print("=" * 78)
    if failures:
        print(f"{len(failures)} gate(s) not passed. This is reported, not hidden.")
    else:
        print("All Windows-only gates passed.")

    if args.json is not None:
        payload = {
            "generated_at_utc": datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "repository_head": _git_head(),
            "gates": [
                {"gate": r.gate, "status": r.status, "detail": r.detail, "data": r.data}
                for r in results
            ],
            "summary": {
                PASS: sum(1 for r in results if r.status == PASS),
                FAIL: sum(1 for r in results if r.status == FAIL),
                NOT_RUN: sum(1 for r in results if r.status == NOT_RUN),
                DERIVED: sum(1 for r in results if r.status == DERIVED),
            },
            "notice": "EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE",
        }
        try:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Wrote {args.json}")
        except OSError as error:
            # Losing the evidence file is itself a failure to report, not a crash.
            print(f"[   FAIL] EVIDENCE: could not write {args.json}: {error}")
            return 2

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
