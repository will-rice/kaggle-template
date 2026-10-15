# Validation Design

**Competition:** example-competition-slug
**Date:** 2026-09-23
**Source revision:** example-source-revision
**Author:** repository-maintainer

## Relevant Artifact Identifiers

- Data and EDA report: not-applicable
- Split manifest or fold artifact: not-applicable
- External tracking run: not-applicable

## Metric and Direction

Record the competition metric and whether the objective is to minimize or maximize it.

## Split Strategy

Describe the selected split family and why it matches the competition data risks.

## Seed, Folds, Groups, and Time Cutoffs

State deterministic seeds, fold counts, grouping keys, and temporal boundaries used by the split.

## Leakage Controls

List the explicit controls that prevent leakage across folds or holdout boundaries.

## OOF Row and Prediction Contract

Define the expected out-of-fold row identifiers, coverage rules, and prediction-shape guarantees.

## Expected Leaderboard Relationship

Explain why the offline metric should correlate with leaderboard behavior and where it might diverge.

## Evidence

Summarize the audit findings, assumptions, and trial results that justify this validation plan.

## Decision

State the validation contract the competition implementation must follow.

## Unresolved Risks

List remaining risks, unknowns, and follow-up checks before training or prediction changes.
