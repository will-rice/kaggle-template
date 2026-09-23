# Task 5 Report: Replaceable Baseline, Local Artifacts, and W&B Tracking

## RED evidence

Command:

```bash
uv run pytest tests/test_training.py -v
```

Result:

```text
collecting ... collected 0 items / 1 error
E   ModuleNotFoundError: No module named 'competition.predict'
```

This confirmed the new training/prediction surface was absent before implementation.

## GREEN evidence

Command:

```bash
uv run pytest tests/test_training.py -v
```

Result:

```text
tests/test_training.py::test_train_and_predict_write_contract_artifacts PASSED
tests/test_training.py::test_wandb_failure_is_persisted_and_raised PASSED
```

Behavior covered:

- training writes manifest, experiment record, model, and OOF artifacts
- prediction writes a candidate submission plus validation proof
- W&B failures are surfaced and still persist an incomplete local experiment record

## Verification commands and results

1. `uv run pytest tests/test_training.py -v` → `2 passed`
2. `uv run pytest -q` → `45 passed`
3. `uv run ruff check .` → `All checks passed!`
4. `uv run mypy .` → `Success: no issues found in 23 source files`
5. `uv build` → built `dist/kaggle_template-0.1.0.tar.gz` and `dist/kaggle_template-0.1.0-py3-none-any.whl`
6. `git --no-pager diff --check` → no output, clean diff formatting

## Files changed

- `pyproject.toml`
- `src/kaggle_template/tracking.py`
- `src/competition/__init__.py`
- `src/competition/data.py`
- `src/competition/validation.py`
- `src/competition/model.py`
- `src/competition/train.py`
- `src/competition/predict.py`
- `tests/conftest.py`
- `tests/test_training.py`
- `src/kaggle_template/submissions.py`
- `tests/test_kaggle_initialize.py`

## Commit

- `e60fd8b` `feat: add replaceable baseline workflow`

## Self-review

- Kept competition-specific data loading, fold assignment, baseline modeling, training, and prediction inside `src/competition`.
- Added `competition` to Hatch packaging only in this task, while keeping generic tracking in `kaggle_template`.
- Persisted `manifest.json` separately from atomic `experiment.json`, and wrote incomplete experiment records before re-raising W&B failures.
- Preserved the no-auto-submit constraint by validating submissions locally without touching Kaggle submission behavior.
- Fixed two existing mypy blockers in generic submission/test code so the requested mypy verification could pass.

## Concerns

- The baseline intentionally uses a single-target mean regressor and a single prediction column; multi-target or modality-specific behavior remains out of scope for this task by design.

## Review findings follow-up

### RED evidence

Command:

```bash
uv run pytest tests/test_training.py tests/test_tracking.py -q
```

Result:

```text
.F......
FAILED tests/test_training.py::test_train_persists_oof_rows_using_public_contract
E       AssertionError: assert ['[3.5]', '[3.5]', '[1.5]', '[1.5]'] == ['[3.0]', '[4.0]', '[1.0]', '[2.0]']
```

This confirmed the new OOF-contract test was exercising the persisted CSV representation before the follow-up fix was complete.

### Fix evidence

- `src/kaggle_template/predictions.py` now writes OOF `prediction` and `target` cells as JSON payloads from the public `OOFRow` contract instead of flattening them to scalars.
- `src/competition/train.py` now persists OOF rows through that shared serializer, keeping the Task 5 manifest command unchanged as `["kaggle-template", "train"]` without adding the Task 6 project script.
- `src/competition/predict.py` now checks the resolved `model.json` path before loading and raises `FileNotFoundError` with the missing artifact path.
- `tests/test_training.py` now reconstructs `OOFRow` instances from the persisted CSV, validates expected fold assignments, and covers the missing-model error path.
- `tests/test_tracking.py` now covers lazy W&B initialization returning no run plus initialization, logging, and finalization failures translated to `TrackingError` without network access.

### GREEN evidence

Command:

```bash
uv run pytest tests/test_training.py tests/test_tracking.py -q
```

Result:

```text
........
8 passed in 0.34s
```

### Verification commands and results (follow-up)

1. `uv run pytest tests/test_training.py tests/test_tracking.py -q` → `8 passed`
2. `uv run pytest -q` → `51 passed`
3. `uv run ruff check .` → `All checks passed!`
4. `uv run mypy .` → `Success: no issues found in 24 source files`
5. `uv build` → built `dist/kaggle_template-0.1.0.tar.gz` and `dist/kaggle_template-0.1.0-py3-none-any.whl`
6. `git --no-pager diff --check` → no output, clean diff formatting
