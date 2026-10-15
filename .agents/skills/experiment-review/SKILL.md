---
name: experiment-review
description: Compare reproducible experiments using the configured metric direction.
---

# Experiment Review

## Preconditions

- At least two complete local experiment records exist.
- W&B status is known for every compared run.

## Workflow

1. Load local experiment records; reject incomplete runs from winner selection.
2. Verify metric names, direction, validation strategy, and row coverage are comparable.
3. Rank with `minimize` or `maximize` from `configs/competition.toml`.
4. Compare configuration, source revision, dirty state, seed, metrics, and artifact checksums.
5. Cross-reference W&B run identifiers without treating W&B as the only record.
6. Copy `reports/templates/experiment-comparison.md` to `reports/YYYY-MM-DD-experiment-comparison.md` and document the selected run and rationale.

## Outputs

- One versioned experiment-comparison report.
- A selected reproducible artifact identifier or an explicit no-selection conclusion.
