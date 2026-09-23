# Task 1 Report: Package Foundation, Typed Configuration, and Canonical Paths

## Scope
Implemented only Task 1 from `.superpowers/sdd/task-1-brief.md` in the isolated worktree.

## RED evidence
### Added failing tests first
Created:
- `tests/__init__.py`
- `tests/test_config_paths.py`

### Failing command
```bash
PYTHONPATH=src uv run --with pytest --with pydantic pytest tests/test_config_paths.py -v
```

### Result
- Exit code: `2`
- Failure occurred during test collection.
- Key error:

```text
E   ModuleNotFoundError: No module named 'kaggle_template'
```

This matched the brief's expected initial failure mode.

## GREEN implementation
### Files created
- `pyproject.toml`
- `uv.lock`
- `configs/competition.toml`
- `src/kaggle_template/__init__.py`
- `src/kaggle_template/config.py`
- `src/kaggle_template/paths.py`
- `tests/__init__.py`
- `tests/test_config_paths.py`

### Implemented interfaces
- `MetricDirection`
- `MetricConfig`
- `PathsConfig`
- `CompetitionConfig`
- `load_config(path: Path) -> CompetitionConfig`
- `ProjectPaths`
- `resolve_project_paths(root: Path, config: PathsConfig) -> ProjectPaths`

### Notes
- Preserved the thin modality-agnostic framework boundary by limiting work to package/config/path foundation only.
- Used standard-library `tomllib` and `pathlib.Path` plus Pydantic as required.
- Enforced repository-contained canonical paths with explicit `ValueError` on traversal outside the repository root.

## Commands and results
### Dependency lock, sync, and focused tests
```bash
uv lock && uv sync --extra dev && uv run pytest tests/test_config_paths.py -v
```
- Exit code: `0`
- Result: all 7 focused tests passed.

### Full available test suite
```bash
uv run pytest -v
```
- Exit code: `0`
- Result: all 7 available tests passed.

### Self-review validation
```bash
uv run ruff check src/kaggle_template tests/test_config_paths.py && git --no-pager diff --check
```
- First run found one import-order issue in `src/kaggle_template/config.py`.
- Fixed import order.
- Re-ran validation successfully.

### Re-run after lint fix
```bash
uv run pytest tests/test_config_paths.py -v && uv run pytest -v
```
- Exit code: `0`
- Result: focused and full available tests both passed again.

## Commit
Created commit:
- `35cb6f7` — `feat: add typed competition configuration`

Commit trailer included exactly as requested:
```text
Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>
```

## Self-review
- Confirmed tests were written before implementation.
- Confirmed public names and signatures match the brief.
- Confirmed optional `target` and `identifier` stay absent/`None` when omitted.
- Confirmed slug validation rejects uppercase, path traversal-like, spaced, and empty values.
- Confirmed resolved paths are absolute and blocked from escaping the repository root.
- Confirmed repository was clean after commit before writing this report.

## Concerns
- Validation ran under the local environment's CPython `3.13.13`; project metadata requires `>=3.12`, so this is compatible, but exact 3.12-only behavior was not separately exercised.

## Review Fix
### Files
- `src/competition/__init__.py`
- `src/kaggle_template/cli.py`
- `tests/test_config_paths.py`
- `.superpowers/sdd/task-1-report.md`

### Commands and results
- `uv run pytest tests/test_config_paths.py -v` → passed, 8 tests
- `uv build` → passed, built `dist/kaggle_template-0.1.0.tar.gz` and `dist/kaggle_template-0.1.0-py3-none-any.whl`
- `uv run ruff check src tests` → passed
- `git diff --check` → passed

### Commit
- `feat: add minimal package entry points for buildability`

### Self-review
- Confirmed the declared script target `kaggle_template.cli:app` now imports cleanly.
- Confirmed the declared `competition` package target now exists as an importable package.
- Confirmed `ProjectPaths` coverage now asserts every resolved field, not just root and data.
- Kept the change minimal: no behavioral expansion beyond importability/buildability and coverage.

## Metadata Ordering Ruling
### Files
- `docs/superpowers/plans/2026-09-23-kaggle-template.md`
- `pyproject.toml`
- `src/competition/__init__.py`
- `src/kaggle_template/cli.py`
- `tests/test_config_paths.py`
- `.superpowers/sdd/task-1-report.md`

### Commands and results
- `git add docs/superpowers/plans/2026-09-23-kaggle-template.md && git commit -m "docs: correct metadata ordering in plan"` → passed; created the plan-only correction commit
- `uv run pytest tests/test_config_paths.py -v` → passed; 7 tests passed
- `uv run pytest -v` → passed; 21 tests passed
- `uv build` → passed; built `dist/kaggle_template-0.1.0.tar.gz` and `dist/kaggle_template-0.1.0-py3-none-any.whl`
- `uv run ruff check .` → passed
- `git --no-pager diff --check` → passed
- `git add pyproject.toml tests/test_config_paths.py src/competition/__init__.py src/kaggle_template/cli.py .superpowers/sdd/task-1-report.md && git commit --amend --no-edit` → passed; updated the implementation-correction commit

### Commits
- `docs: correct metadata ordering in plan`
- `fix: remove premature task 1 metadata targets`
