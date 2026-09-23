---
name: submission
description: Generate, validate, inspect, and explicitly submit one Kaggle file.
---

# Submission

## Preconditions

- A selected complete experiment exists.
- Competition rules and daily submission limits are understood.

## Workflow

1. Run `uv run kaggle-template predict`.
2. Inspect the candidate path and `.validation.json` proof.
3. Confirm row count, columns, identifier order, uniqueness, finite predictions, sample checksum, and candidate checksum.
4. Choose a message identifying the experiment and validation result.
5. Display the competition, file, message, and validation result to the user.
6. Submit only after explicit approval with `uv run kaggle-template submit <file> --message "<message>" --confirm`.
7. Record Kaggle's returned status; do not retry a failed submission silently.

## Outputs

- A checksum-bound validated submission.
- An explicit Kaggle result only when `--confirm` was supplied.
