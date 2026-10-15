---
name: validation-design
description: Define a competition-aligned validation strategy and metric.
---

# Validation Design

## Preconditions

- A versioned data/EDA audit exists.
- The competition metric and optimization direction are confirmed.

## Workflow

1. Copy `reports/templates/validation.md` to `reports/YYYY-MM-DD-validation.md`.
2. State the metric name and exactly `minimize` or `maximize`.
3. Choose folds or a holdout that addresses recorded leakage, time, group, and stratification risks.
4. Record fold count, seed, grouping keys, temporal cutoffs, and leakage controls.
5. Define the expected out-of-fold row identifiers and prediction shape.
6. Explain why offline validation should correlate with the leaderboard.

## Outputs

- One versioned `reports/YYYY-MM-DD-validation.md`.
- A deterministic split contract consumable by `src/competition/validation.py`.
