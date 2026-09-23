# NVIDIA Kaggle Skill Vendoring Design

## Purpose

Vendor the complete `nvidia-kaggle-skill` into `.skills/nvidia-kaggle-skill` so repositories created from this template have a portable, self-contained Kaggle research and operations skill in the requested compatibility location.

## Chosen Approach

Copy the complete skill directory rather than using a symlink or a wrapper, and preserve the authored snapshot byte-for-byte:

- A full copy works in clones, archives, GitHub templates, and environments that do not follow symlinks during skill discovery.
- A wrapper would depend on an external user installation and would not include the referenced scripts and workflow documents.
- The vendored copy is limited to authored source files. Generated caches, local databases, downloaded data, credentials, and Python bytecode are excluded.
- Vendored authored files are not normalized to satisfy repository style. They are restored exactly from `/Users/will/.agents/skills/nvidia-kaggle-skill` and protected by `.skills/nvidia-kaggle-skill/SOURCE_MANIFEST.sha256`.

The existing six core workflows remain under `.agents/skills` unchanged. The NVIDIA skill is additive under `.skills`; it does not alter their names, behavior, or exact-count contract.

## Contents

`.skills/nvidia-kaggle-skill` contains:

- `SKILL.md` with the workflow catalog, prerequisites, safety requirements, and runtime dependencies
- focused workflow documents for kernels, kernel setup, writeups, research briefs, submissions, and evaluations
- the complete `scripts/` tree required by those workflows
- `SOURCE_MANIFEST.sha256` with deterministic SHA-256 entries for each authored vendored file except the manifest itself

All internal relative links and script paths must resolve inside the vendored directory.

## Safety and Validation

- Do not copy `KAGGLE_API_TOKEN`, environment files, local databases, downloaded datasets, caches, or bytecode.
- Preserve the skill's explicit confirmation requirements for submissions and dataset uploads.
- Add repository-contract tests that verify the skill entry point, every relative Markdown/script reference named by `SKILL.md`, the exact manifest membership and hashes, the absence of generated files, and `ast.parse` success for every vendored Python file.
- Keep strict Ruff, mypy, pytest, and pre-commit checks for repository-owned code. Ruff excludes only `.skills/nvidia-kaggle-skill`; mypy remains scoped to `src` and `tests`.
- Validate the vendored external snapshot with manifest, syntax, reference, secret, and source-comparison checks instead of rewriting external source to match repository style.

## Non-Goals

- Do not duplicate the NVIDIA skill into `.agents/skills`.
- Do not modify the six core competition skills.
- Do not integrate NVIDIA-specific behavior into the modality-agnostic framework package.
- Do not run Kaggle API, download, upload, or submission workflows as part of vendoring.
