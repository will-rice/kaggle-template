---
name: competition-setup
description: Bootstrap and verify one Kaggle competition repository.
---

# Competition Setup

## Preconditions

- Confirm this repository instance is dedicated to one competition.
- Confirm `configs/competition.toml` contains the intended slug.
- Keep Kaggle credentials outside the repository.

## Workflow

1. Run `uv sync --extra dev`.
2. Run `uv run kaggle-template competition-init <slug>`.
3. If credentials, slug, or rules acceptance fails, stop and report the exact error.
4. Verify `.kaggle-template/init.json` records the same slug.
5. Verify the configured data directory contains competition files.
6. Do not overwrite existing competition modules or initialize a different slug.

## Outputs

- Idempotent initialization state for the configured slug.
- Downloaded, ignored competition files in the configured data directory.
