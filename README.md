# kaggle-template

A public, modality-agnostic GitHub template instantiated once per Kaggle competition.

## Bootstrap

1. Create a repository from this template.
2. Install Python 3.12 or newer and `uv`.
3. Set the competition slug and known fields in `configs/competition.toml`.
4. Configure Kaggle credentials outside the repository and accept the competition rules.
5. Run `uv sync --extra dev`.
6. Run `uv run kaggle-template competition-init <slug>`.

`uv sync` installs the official `kaggle` CLI as a runtime dependency, so `uv run kaggle ...` and `competition-init` need no separate install. Provide credentials through `~/.kaggle/kaggle.json` or the `KAGGLE_USERNAME`/`KAGGLE_KEY` environment variables; never place them in the repository.

Initialization is idempotent for the configured slug: re-running it is a no-op when data is present and re-downloads only when the data directory is missing or empty. It rejects a different slug without overwriting competition work.

## Boundaries

`src/kaggle_template` is the stable framework: typed config, canonical paths, Kaggle operations, records, OOF contracts, submission validation, tracking, and CLI commands.

`src/competition` is replaceable: data loading, validation, model, training, and prediction. It may use non-neural or neural solutions. Replacing it must not require framework edits when the public contracts are preserved.

## Workflow

Use the six skills in `.agents/skills` in order:

1. competition setup
2. data and EDA audit
3. validation design
4. baseline creation
5. experiment review
6. submission

Commands:

```bash
uv run kaggle-template train
uv run kaggle-template predict
uv run kaggle-template submit artifacts/submissions/<run>.csv --message "<experiment and validation>" --confirm
```

`train` records local artifacts and W&B results. `predict` generates and validates a candidate. The framework never submits during training or prediction. Only `submit` can submit, and it requires a current checksum-bound validation proof plus `--confirm`.

## Local and Remote Execution

Run the same `uv sync --extra dev`, `uv run kaggle-template train`, `uv run kaggle-template predict`, and `uv run kaggle-template submit` commands on local or remote Python 3.12+ machines. Copy credentials and ignored competition data through secure machine-specific mechanisms; do not commit them.

## Quality

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run pre-commit run --all-files
```

CI uses fake Kaggle integration and synthetic data. It never downloads or submits to a real competition.
