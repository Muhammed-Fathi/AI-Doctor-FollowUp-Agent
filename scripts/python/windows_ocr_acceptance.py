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
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = REPO_ROOT / "data" / "synthetic" / "documents" / "sources"

PASS = "PASS"
FAIL = "FAIL"
NOT_RUN = "NOT RUN"


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


# --- environment -------------------------------------------------------------


def gate_environment(results: list[Result]) -> None:
    """Record the environment every other measurement depends on."""
    import PIL
    import pypdfium2
    import pytesseract

    detail = (
        f"{platform.system()} {platform.release()} build {platform.version()}; "
        f"Python {platform.python_version()}; "
        f"pytesseract {getattr(pytesseract, '__version__', 'unknown')}; "
        f"pillow {PIL.__version__}; "
        f"pypdfium2 {pypdfium2.version.PYPDFIUM_INFO}"
    )
    expected = "3.12."
    status = PASS if platform.python_version().startswith(expected) else FAIL
    reason = "" if status == PASS else f" project requires Python {expected}x"
    _record(
        results,
        Result(
            "ENV-01 runtime",
            status,
            detail + reason,
            {"python": platform.python_version(), "os": platform.platform()},
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
        for gate in ("GOLD-EX-05 PNG", "GOLD-EX-06 JPEG", "OCR-LIVE-01"):
            _record(results, Result(gate, NOT_RUN, "no Tesseract engine available"))
        return

    _engine_scan(results, source="report_a_clean.txt", fmt="PNG", gate="GOLD-EX-05 PNG")
    _engine_scan(results, source="report_a_clean.txt", fmt="JPEG", gate="GOLD-EX-06 JPEG")

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

    from PIL import Image, ImageDraw

    from app.core.enums import ExtractionPath
    from app.services.documents.field_parser import parse_pages
    from app.services.documents.ocr import run_ocr
    from app.services.documents.text_extraction import PageText

    # A source whose value token is already corrupt. The engine must *see* text;
    # the flag must come from the parser, never from the engine's opinion.
    image = Image.new("RGB", (1000, 300), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "SYNTHETIC DEMO DATA - NOT A REAL MEDICAL RECORD",
        "Demo Patient A            Ref: DEMO-A-001            Report date: 2026-10-20",
        "Test: Glucose             Value: 1O5 mg/dL",
    ]
    for index, line in enumerate(lines):
        draw.text((20, 20 + index * 22), line, fill="black")

    ocr = run_ocr(image, tesseract_cmd=os.environ.get("TESSERACT_CMD") or None, language="eng")
    page = PageText(
        page_index=0,
        text=ocr.text,
        extractor=ExtractionPath.TESSERACT,
        confidence=ocr.confidence,
    )
    parsed = parse_pages([page])

    flags = {
        flag.value
        for fact in parsed.facts
        for flag in fact.quality_flags
        if fact.field_name.value == "value"
    }
    repaired = [
        fact.normalized_value
        for fact in parsed.facts
        if fact.field_name.value == "value" and fact.normalized_value
    ]
    ok = "low_confidence" in flags or "unparseable_value" in flags
    _record(
        results,
        Result(
            gate,
            PASS if ok else FAIL,
            f"value flags={sorted(flags)} normalized={repaired} (must not be silently 105)",
            {"flags": sorted(flags), "normalized_values": repaired, "ocr_text": ocr.text},
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

    try:
        with tempfile.TemporaryDirectory(prefix="p3-accept-") as tmp:
            from fastapi.testclient import TestClient

            from app.db.session import create_db_engine
            from app.services.accounts import issue_session
            from app.services.seed import seed_demo_data

            db_path = Path(tmp) / "accept.db"
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
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
                    password=settings.demo_seed_password or "acceptance-only-password",
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
                patient_token, _ = issue_session(session, user=patient, ttl_minutes=60)
                doctor_token, _ = issue_session(session, user=doctor, ttl_minutes=60)
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
                            Result(
                                gate, FAIL, f"upload answered {upload.status_code}: {upload.text}"
                            ),
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

                    ok = (
                        facts and extractors == {"tesseract"} and stored_extractors == {"tesseract"}
                    )
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
            engine.dispose()
            reset_settings_cache()
    except Exception:
        _record(results, Result(gate, FAIL, traceback.format_exc(limit=3)))


# --- main --------------------------------------------------------------------


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
    gate_environment(results)
    executable = gate_engine(results)
    engine_present = executable is not None

    gate_ocr_live(results, engine_present=engine_present)
    gate_ocr_corruption(results, engine_present=engine_present)
    gate_rasterizer(results)
    gate_api_ocr_upload(results, engine_present=engine_present)

    print()
    print("=" * 78)
    for result in results:
        print(f"{result.status:>7}  {result.gate}")
    failures = [result for result in results if result.status != PASS]
    print("=" * 78)
    if failures:
        print(f"{len(failures)} gate(s) not passed. This is reported, not hidden.")
    else:
        print("All Windows-only gates passed.")

    if args.json is not None:
        args.json.write_text(
            json.dumps(
                [
                    {"gate": r.gate, "status": r.status, "detail": r.detail, "data": r.data}
                    for r in results
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {args.json}")

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
