# Versioned Reports

Commit human-readable decision records as `YYYY-MM-DD-<kind>.md`.

Store exactly four reusable templates in `reports/templates/`: `data-eda.md`, `validation.md`, `baseline.md`, and `experiment-comparison.md`.

Every report names the competition slug, source revision, relevant artifact identifiers, author/date, evidence, decision, and unresolved risks.

Never commit datasets, downloaded competition files, checkpoints, predictions, submissions, or other generated machine artifacts. Reports reference artifact identifiers and paths instead of embedding machine outputs.

Valid kinds are `data-eda`, `validation`, `baseline`, and `experiment-comparison`; create a new dated report instead of overwriting historical decisions.
