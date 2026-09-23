# NVIDIA Kaggle Skill Vendoring Design

## Purpose

Vendor the complete `nvidia-kaggle-skill` into `.skills/nvidia-kaggle-skill` so repositories created from this template have a portable, self-contained Kaggle research and operations skill in the requested compatibility location.

## Chosen Approach

Copy the complete skill directory rather than using a symlink or a wrapper:

- A full copy works in clones, archives, GitHub templates, and environments that do not follow symlinks during skill discovery.
- A wrapper would depend on an external user installation and would not include the referenced scripts and workflow documents.
- The vendored copy is limited to authored source files. Generated caches, local databases, downloaded data, credentials, and Python bytecode are excluded.

The existing six core workflows remain under `.agents/skills` unchanged. The NVIDIA skill is additive under `.skills`; it does not alter their names, behavior, or exact-count contract.

## Contents

`.skills/nvidia-kaggle-skill` contains:

- `SKILL.md` with the workflow catalog, prerequisites, safety requirements, and runtime dependencies
- focused workflow documents for kernels, kernel setup, writeups, research briefs, submissions, and evaluations
- the complete `scripts/` tree required by those workflows

All internal relative links and script paths must resolve inside the vendored directory.

## Safety and Validation

- Do not copy `KAGGLE_API_TOKEN`, environment files, local databases, downloaded datasets, caches, or bytecode.
- Preserve the skill's explicit confirmation requirements for submissions and dataset uploads.
- Add a repository-contract test that verifies the skill entry point and every relative Markdown/script reference named by `SKILL.md` exists.
- Run repository tests, Ruff, mypy, pre-commit, and secret scanning on the added files.

## Non-Goals

- Do not duplicate the NVIDIA skill into `.agents/skills`.
- Do not modify the six core competition skills.
- Do not integrate NVIDIA-specific behavior into the modality-agnostic framework package.
- Do not run Kaggle API, download, upload, or submission workflows as part of vendoring.
