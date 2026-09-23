# Versioned Reports

Commit human-readable decision records as `YYYY-MM-DD-<kind>.md`. Never commit datasets or generated machine artifacts. Every report names the competition slug, source revision, relevant artifact identifiers, author/date, evidence, decision, and unresolved risk. Valid kinds are `data-eda`, `validation`, `baseline`, and `experiment-comparison`; create a new dated report instead of overwriting historical decisions.
