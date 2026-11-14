#!/usr/bin/env python
"""Scan the tracked files for secrets, runtime artefacts and unsafe claims.

Implements the P1 evidence for ``REQ-SEC-06`` (no secrets, databases, uploads or
model weights committed) and the ``SEC-06`` evaluation row.

Three independent checks:

1. **Tracked artefacts** — no ``.env``, database, log, virtual environment,
   ``node_modules`` or model binary is tracked. Ignored-but-present files are
   fine; only tracked files matter.
2. **Secret-shaped content** — common credential patterns (private keys, cloud
   keys, bearer tokens, ``password = "..."``) in tracked text files.
3. **Unsafe claims** — forbidden compliance/clinical claims in tracked
   documentation and UI copy (``AGENTS.md`` §3.7).

Exit code 0 = clean, 1 = findings (printed). Offline, deterministic, read-only.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# --- 1. artefact rules --------------------------------------------------------
FORBIDDEN_SUFFIXES = (
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite3",
    ".pyc",
    ".gguf",
    ".safetensors",
    ".onnx",
    ".pt",
    ".pth",
    ".pem",
    ".key",
    ".pfx",
    ".p12",
)
FORBIDDEN_NAMES = {".env"}
FORBIDDEN_PREFIXES = (".venv/", "venv/", "node_modules/", "data/runtime/", "dist/", "coverage/")

# --- 2. secret patterns -------------------------------------------------------
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    (
        "assigned password/secret",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*"
            r"[\"'][^\"'\s]{8,}[\"']"
        ),
    ),
)

# --- 3. forbidden claim patterns ---------------------------------------------
CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("clinical safety claim", re.compile(r"(?i)\bclinically (?:safe|validated|proven)\b")),
    ("medical accuracy claim", re.compile(r"(?i)\bmedically accurate\b")),
    ("compliance claim", re.compile(r"(?i)\b(?:HIPAA|GDPR)[ -]compliant\b")),
    ("production-readiness claim", re.compile(r"(?i)\bproduction[ -]ready\b")),
)

# Files that legitimately *mention* the forbidden phrases in order to forbid them.
CLAIM_PATTERN_ALLOWLIST = {
    "AGENTS.md",
    "scripts/python/scan_repository.py",
    "docs/clinical-safety/CLINICAL_SAFETY.md",
    "docs/contracts/MVP_SPEC.md",
    "docs/contracts/DEPENDENCIES.md",
    "docs/roadmap/MASTER_PLAN.md",
    "docs/roadmap/PHASE_PROGRESS.md",
    "docs/phase-reports/PHASE_0_REPORT.md",
    "docs/phase-reports/PHASE_1_REPORT.md",
    "docs/evaluation/EVALUATION_MATRIX.md",
    "docs/clinical-safety/THREAT_MODEL.md",
}

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".css",
    ".html",
    ".ps1",
    ".txt",
    ".cfg",
    ".lock",
    ".example",
}
TEXT_NAMES = {".env.example", ".gitignore", "Dockerfile", "LICENSE"}


def tracked_files() -> list[str]:
    """Return repository-relative paths git would commit.

    ``--cached --others --exclude-standard`` returns tracked files **plus** new
    files that are not ignored, so the scan is meaningful before as well as
    after ``git add`` (CI checks out tracked files only, a developer runs it on
    a dirty tree).
    """
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise SystemExit(f"git ls-files failed: {completed.stderr.strip()}")
    return [item for item in completed.stdout.split("\0") if item]


def is_text_file(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in TEXT_SUFFIXES or Path(path).name in TEXT_NAMES


def check_artefacts(files: list[str]) -> list[str]:
    """Findings for tracked runtime artefacts."""
    findings: list[str] = []
    for path in files:
        name = Path(path).name
        if name in FORBIDDEN_NAMES:
            findings.append(f"tracked environment file: {path}")
            continue
        if path.lower().endswith(FORBIDDEN_SUFFIXES):
            findings.append(f"tracked runtime/binary artefact: {path}")
            continue
        if path.startswith(FORBIDDEN_PREFIXES):
            findings.append(f"tracked generated directory: {path}")
    return findings


def check_secrets(files: list[str]) -> list[str]:
    """Findings for secret-shaped content in tracked text files."""
    findings: list[str] = []
    for path in files:
        if not is_text_file(path):
            continue
        try:
            content = (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                line_number = content.count("\n", 0, match.start()) + 1
                findings.append(f"{label} in {path}:{line_number}")
    return findings


def check_claims(files: list[str]) -> list[str]:
    """Findings for forbidden clinical/compliance claims in tracked text files."""
    findings: list[str] = []
    for path in files:
        normalized = path.replace("\\", "/")
        if normalized in CLAIM_PATTERN_ALLOWLIST or not is_text_file(path):
            continue
        try:
            content = (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for label, pattern in CLAIM_PATTERNS:
            match = pattern.search(content)
            if match:
                line_number = content.count("\n", 0, match.start()) + 1
                findings.append(f"{label} in {path}:{line_number} ({match.group(0)!r})")
    return findings


def main() -> int:
    """Run all checks and print a summary."""
    try:
        files = tracked_files()
    except SystemExit as error:
        print(f"Secret/artefact scan: FAIL ({error})", file=sys.stderr)
        return 1

    artefact_findings = check_artefacts(files)
    secret_findings = check_secrets(files)
    claim_findings = check_claims(files)

    groups = (
        ("tracked artefacts", artefact_findings),
        ("secret patterns", secret_findings),
        ("forbidden claims", claim_findings),
    )

    total = sum(len(findings) for _, findings in groups)
    if total:
        print(
            f"Secret/artefact scan: FAIL ({total} finding(s) in {len(files)} tracked files)",
            file=sys.stderr,
        )
        for label, findings in groups:
            for finding in findings:
                print(f"  - [{label}] {finding}", file=sys.stderr)
        return 1

    print(
        f"Secret/artefact scan: PASS ({len(files)} tracked files; "
        f"{len(SECRET_PATTERNS)} secret patterns, {len(CLAIM_PATTERNS)} claim patterns)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
