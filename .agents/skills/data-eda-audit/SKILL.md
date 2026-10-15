---
name: data-eda-audit
description: Audit competition data, rules, leakage risks, and schema assumptions.
---

# Data and EDA Audit

## Preconditions

- Competition setup is complete.
- Read competition rules and dataset descriptions before inspecting features.

## Workflow

1. Copy `reports/templates/data-eda.md` to `reports/YYYY-MM-DD-data-eda.md`.
2. Record train, test, and sample-submission shapes and columns.
3. Record target and identifier assumptions, missingness, cardinality, duplicates, and class or target distribution.
4. Identify leakage risks, time/group structure, modality constraints, and prohibited external data.
5. Reference local paths and artifact identifiers; do not embed datasets.
6. Resolve every assumption in the report before validation design.

## Outputs

- One versioned `reports/YYYY-MM-DD-data-eda.md`.
- Explicit target, identifier, leakage, missingness, and rules findings.
