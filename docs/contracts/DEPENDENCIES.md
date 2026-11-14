# Dependency and Platform Verification Record

| Field | Value |
|---|---|
| Document ID | `CTR-DEPS-001` |
| Version | `0.1.0-p0` |
| Status | **IN REVIEW — metadata retrieved from registries; nothing installed, pinned, or tested** |
| Phase | `P0` (verification record). Pinning happens in P1 with lockfiles |
| Related | `AGENTS.md` §6, `REQ-SEC-06`, `ASM-01`..`ASM-03` |

## 1. What "verified" means here

| Claim level | Meaning in this table |
|---|---|
| **Registry-verified** | Version, license and engine constraint were read from the authoritative registry API (PyPI JSON / npm registry) on the date shown. The package was **not** installed or executed in this phase |
| **Doc-referenced** | The official documentation URL was recorded in `MASTER_PLAN.md`; API behaviour was **not** verified by execution |
| **Unverified** | No authoritative check was possible from this environment. Must be checked by the owner before use |

No version below is a pin. Phase 1 chooses and locks versions after a real install on the owner's laptop.
Installing a newer "latest" must pass the phase-1 setup and test gate before it is accepted.

## 2. Verification environment (authoring sandbox)

| Item | Observed value | How observed |
|---|---|---|
| Date of retrieval | 2026-11-14 | Session date |
| Python | 3.11.2 | `python3 -V` |
| Node.js | 22.22.3 | `node -v` |
| npm | 10.9.8 | `npm -v` |
| Tesseract | not installed | `which tesseract` → not found |
| Ollama | not installed | `which ollama` → not found |
| Poppler / `pdftoppm` | not installed | `which pdftoppm` → not found |
| Windows PowerShell | unavailable (Linux sandbox) | n/a |

Consequence: no OCR, no local model, no Windows script, and no browser E2E test could be executed in P0. Everything below is a *plan* plus registry metadata.

## 3. Python packages — registry-verified metadata (2026-11-14)

Retrieved with `curl -s https://pypi.org/pypi/<package>/json` and reading `info.version`,
`info.license_expression`, `info.requires_python`.

| Package | Latest published | License (registry) | `requires_python` | Planned phase | Notes |
|---|---|---|---|---|---|
| `fastapi` | 0.162.7 | MIT | `>=3.11` | P1 | HTTP layer + generated OpenAPI |
| `pydantic` | 2.14.3 | MIT | `>=3.10` | P1 | Typed contracts; v2 API assumed |
| `uvicorn` | 0.54.0 | BSD-3-Clause | `>=3.10` | P1 | Local ASGI server |
| `sqlalchemy` | 2.1.8 | MIT | `>=3.11` | P1 | ORM / Core for SQLite |
| `alembic` | 1.20.1 | MIT | `>=3.10` | P1 | Migrations |
| `python-multipart` | 0.0.33 | Apache-2.0 | `>=3.11` | P1 | Multipart upload support for FastAPI |
| `pytest` | 9.2.0 | MIT | `>=3.10` | P1 | Test runner |
| `httpx` | 0.28.1 | BSD-3-Clause | `>=3.8` | P1 | API contract tests |
| `ruff` | 0.17.5 | MIT | `>=3.7` | P1 | Lint/format |
| `langgraph` | 1.2.22 | MIT | `>=3.10` | P5 | StateGraph orchestration |
| `langgraph-checkpoint-sqlite` | 3.1.3 | MIT | `>=3.10` | P5 | Durable checkpoints |
| `pypdf` | 7.1.0 | BSD-3-Clause | `>=3.10` | P3 | Text-layer extraction |
| `pytesseract` | 0.3.13 | Apache-2.0 | `>=3.8` | P3 | OCR wrapper (needs the Tesseract binary) |
| `pillow` | 13.0.0 | MIT-CMU | `>=3.11` | P3 | Image handling |
| `pdf2image` | 1.17.0 | MIT | (not declared) | P3 | PDF → image for OCR; needs Poppler |

Consistency checks performed on this table (reasoning only, not execution):

- All `requires_python` values are compatible with Python **3.12** (`MASTER_PLAN.md` target) and with the sandbox's 3.11.
- `pytesseract` is a wrapper only: the Tesseract engine is a separate system dependency whose version is **unverified** here.
- `pdf2image` requires a Poppler install; the alternative pure-Python rasterizer decision is deferred to P3.
- Nothing above has been installed in this repository; no `pyproject.toml`, lockfile, or `requirements.txt` exists yet (by design in P0).

## 4. Frontend packages — registry-verified metadata (2026-11-14)

Retrieved with `curl -s https://registry.npmjs.org/<package>` reading `dist-tags.latest`,
`versions[latest].license`, `versions[latest].engines.node`.

| Package | Latest published | License | Engines (node) | Planned phase |
|---|---|---|---|---|
| `react` | 19.3.1 | MIT | (not declared) | P1 |
| `react-dom` | 19.3.1 | MIT | (not declared) | P1 |
| `vite` | 8.3.8 | MIT | `^20.19.0 \|\| >=22.12.0` | P1 |
| `@vitejs/plugin-react` | 6.3.0 | MIT | `^20.19.0 \|\| >=22.12.0` | P1 |
| `typescript` | 7.0.2 | Apache-2.0 | `>=16.20.0` | P1 |
| `vitest` | 5.1.0 | MIT | `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0` | P1 |
| `@playwright/test` | 1.65.1 | Apache-2.0 | `>=20` | P1 (installed) / P6 (E2E) |
| `eslint` | 10.15.0 | MIT | `^20.19.0 \|\| ^22.13.0 \|\| >=24` | P1 |

Consistency checks (reasoning only):

- The sandbox Node 22.22.3 satisfies Vite's and Vitest's engine constraints.
- **Owner must confirm the laptop's Node LTS** before P1 pins these; a Vite 8 / TypeScript 7 generation is recent, so the owner may prefer a conservatively older major for the defense build. That is a P1 decision with a documented reason, not a silent downgrade.
- Playwright browser binaries are **not** downloaded in P0; installing them requires network + disk on the owner machine.

## 5. Platform and system dependencies — UNVERIFIED

| Item | Why it matters | How the owner must verify |
|---|---|---|
| Windows version + PowerShell version | `scripts/powershell/*.ps1` execution policy and syntax | `$PSVersionTable` on the laptop |
| Python 3.12 installer on Windows | Backend runtime | `python --version` after install |
| Node.js LTS on Windows | Frontend build | `node -v`, `npm -v` |
| Tesseract for Windows + `eng.traineddata` | OCR fallback | `tesseract --version`, `tesseract --list-langs` |
| Poppler for Windows (`pdftoppm`) | PDF rasterization for OCR | `pdftoppm -v` |
| Ollama for Windows | Local drafting | `ollama --version`, `ollama list` |
| Model availability and size (e.g. a 3B-class quantized model) | Demo drafting and latency | `ollama pull <model>` then `ollama list` (owner decision; nothing downloaded here) |
| GPU presence / VRAM | Benchmark expectations | OS display adapter info; recorded in the benchmark sheet |
| Free disk for models + dependencies | Prevents a failed demo setup | `Get-PSDrive` / Explorer |
| GitHub Free plan + Actions allowance | CI budget | Owner checks account billing settings; plan limits are **not** asserted in this repo |
| GitHub issue #1 readability | Tracking reference | The integration token used in this session received `403 Resource not accessible by integration` when reading the issue; the PR links it by number without asserting its content |

## 6. Official documentation references (recorded, not verified by execution)

| Topic | URL | Status |
|---|---|---|
| LangGraph overview | https://docs.langchain.com/oss/python/langgraph/overview | Doc-referenced |
| LangGraph checkpoints | https://langchain-ai.github.io/langgraph/reference/checkpoints/ | Doc-referenced |
| LangGraph interrupts / human-in-the-loop | https://docs.langchain.com/oss/python/langgraph/interrupts | Doc-referenced — exact `interrupt()`/`Command(resume=…)` semantics must be re-checked at P5 |
| LangGraph SQLite checkpointer source | https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-sqlite | Registry metadata + source URL observed |
| Ollama local API | https://docs.ollama.com/api/introduction | Doc-referenced |
| Ollama structured outputs | https://docs.ollama.com/capabilities/structured-outputs | Doc-referenced |
| FastAPI testing | https://fastapi.tiangolo.com/tutorial/testing/ | Doc-referenced |
| Tesseract documentation | https://tesseract-ocr.github.io/tessdoc/ | Doc-referenced |
| GitHub Free plans | https://github.com/pricing | Doc-referenced — plan limits **not** claimed |
| GitHub Actions billing | https://docs.github.com/en/billing/concepts/product-billing/github-actions | Doc-referenced — minutes **not** claimed |

The authoring environment could reach `pypi.org`, `registry.npmjs.org`, `github.com`, `api.github.com`,
`codeload.github.com` and `files.pythonhosted.org` only. Documentation sites were **not** fetched, so no
API-level claim in the contracts is presented as independently verified; the P5 task must re-check them.

## 7. License posture

| Aspect | Position |
|---|---|
| Declared licenses of planned dependencies | Permissive (MIT / BSD / Apache-2.0 / MIT-CMU) per registry metadata |
| Project's own license | **Not chosen yet** — owner decision at P1; `openapi.phase0.yaml` uses `NOASSERTION` until then |
| Model licenses | Model-specific terms must be reviewed by the owner before the demo is published; not asserted here |
| Assets | No third-party datasets, images, or medical documents are included; every fixture is authored for the demo |

## 8. Pinning policy for Phase 1

1. Pin exact versions in `pyproject.toml`/`package-lock.json` after a clean install and a passing smoke test on the owner's laptop.
2. Record each pinned version and its install command in the P1 phase report, with the date.
3. Do not silently upgrade across majors during the project; any upgrade needs a PR note and a re-run of the gate.
4. Never commit `.venv`, `node_modules`, model weights, or downloaded binaries (`REQ-SEC-06`).
