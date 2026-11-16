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
                # 3. whether a human must look at this value
                "human_review_required": True,
                "human_review_reason": (
                    "the OCR reading is ambiguous or substituted, so the value is never "
                    "used without a doctor's decision"
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


def gate_api_ocr_upload(results: list[Result], *, engine_present: bool) -> None:
    """GOLD-EX-05 through the real HTTP path: PNG upload ends with tesseract facts.

    Uses an isolated application instance over a temporary SQLite database and a
    temporary upload directory, so the owner's ``data/runtime`` is never touched.
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

        from app.db.session import create_db_engine
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

        from app.core.config import get_settings, reset_settings_cache

        reset_settings_cache()
        settings = get_settings()

        from alembic import command
        from alembic.config import Config

        config = Config(str(REPO_ROOT / "backend" / "migrations" / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", settings.database_url)
        config.attributes["configure_logger"] = False
        command.upgrade(config, "head")

        engine = create_db_engine(settings.database_url)
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from app.db.models import ExtractedFact, User
        from app.main import create_app

        with Session(engine) as session:
            seed_demo_data(
                session,
                password=_seed_password(settings),
                now=__import__("datetime").datetime(
                    2026, 11, 15, tzinfo=__import__("datetime").timezone.utc
                ),
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
            issued_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            patient_token, _ = issue_session(session, user=patient, now=issued_at, ttl_minutes=60)
            doctor_token, _ = issue_session(session, user=doctor, now=issued_at, ttl_minutes=60)
            session.commit()

            with TestClient(create_app(settings)) as client:
                upload = client.post(
                    "/api/v1/documents/upload",
                    headers={"Authorization": f"Bearer {patient_token}"},
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
                    headers={"Authorization": f"Bearer {doctor_token}"},
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
                stored = session.execute(
                    select(ExtractedFact).where(ExtractedFact.document_id == document_id)
                ).scalars()
                stored_extractors = {row.extractor for row in stored}

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
