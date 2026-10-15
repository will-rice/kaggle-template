---
name: baseline-creation
description: Build the simplest credible replaceable competition baseline.
---

# Baseline Creation

## Preconditions

- Data/EDA and validation reports are complete.
- `configs/competition.toml` has target and identifier values required by training.

## Workflow

1. Change only `src/competition/data.py`, `validation.py`, `model.py`, `train.py`, and `predict.py`.
2. Keep framework contracts unchanged unless a competition-independent defect is proven.
3. Implement the simplest credible non-neural or neural approach for the metric.
4. Run focused tests, then `uv run kaggle-template train`.
5. Run `uv run kaggle-template predict` and inspect the validation proof.
6. Copy `reports/templates/baseline.md` to `reports/YYYY-MM-DD-baseline.md` and record artifact and W&B run identifiers.

## Outputs

- Replaceable competition implementation.
- Valid OOF predictions, local experiment record, W&B run, and validated candidate submission.
- One versioned baseline report.
