# Contributing

Thanks for your interest in **AI Doctor Follow-Up Agent**, an academic, local-only,
synthetic-data graduation project (DEPI). It is not for clinical use.

## Before you start

1. Read [AGENTS.md](AGENTS.md). Its operating rules apply to all contributors and to any
   AI assistant used on this repository. Key points:
   - One phase (`P0`-`P8`) per branch and per pull request. No future-phase code.
   - No direct commits to `main`; all work lands through a phase branch
     (`feat/pN-short-scope`) and a pull request. Only the project owner merges and
     accepts phases.
2. Check the current project state in
   [docs/roadmap/PHASE_PROGRESS.md](docs/roadmap/PHASE_PROGRESS.md) and the
   [MASTER_PLAN.md](docs/roadmap/MASTER_PLAN.md) status index before proposing work.
3. Read the [MVP specification](docs/contracts/MVP_SPEC.md), especially the non-goals
   (section 6), before suggesting features.

## Hard boundaries for any contribution

- Synthetic, fictitious, clearly labelled demo data only. Never add real patient data,
  real credentials, `.env` files, databases, model weights, or OCR output.
- No diagnosis, risk scoring, triage, treatment or dosing logic, patient-facing medical
  advice, external messaging, or compliance claims - in code, fixtures, docs, or UI copy.
- See [docs/clinical-safety/CLINICAL_SAFETY.md](docs/clinical-safety/CLINICAL_SAFETY.md)
  and the threat model for details.

## Proposing a change

1. Open an issue describing the change and which phase it belongs to, or comment on the
   relevant open phase PR.
2. Create a phase branch from `main`, keep the change inside that phase's scope, and open
   a pull request targeting `main`.
3. In the PR body, state what was executed and attach evidence (run logs, reports) as the
   existing phase PRs do. Do not mark anything `PASS` yourself; the owner reviews and
   accepts.

## Local setup

Windows PowerShell scripts under `scripts/powershell/` handle preflight, setup, start,
test and stop. See the [Windows setup guide](docs/runbooks/WINDOWS_SETUP.md) and the
dependency notes in [docs/contracts/DEPENDENCIES.md](docs/contracts/DEPENDENCIES.md).
Python dependencies are pinned in `pyproject.toml`.
