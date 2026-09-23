import math
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from kaggle_template.records import sha256_file


def _identifier_value(value: str) -> str:
    return value


def resolve_submission_identifier(columns: list[str], identifier: str | None) -> str | None:
    """Return the configured identifier, else the first column of a multi-column sample."""
    if identifier is not None:
        return identifier
    return columns[0] if len(columns) > 1 else None


class SubmissionProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competition_slug: str
    sample_sha256: str
    candidate_sha256: str
    row_count: int
    columns: list[str]
    validated_at: datetime


def validate_submission(
    candidate: Path,
    sample: Path,
    slug: str,
    identifier: str | None,
) -> SubmissionProof:
    if not candidate.exists():
        raise FileNotFoundError(f"candidate submission not found: {candidate}")
    if not sample.exists():
        raise FileNotFoundError(f"sample submission not found: {sample}")

    sample_columns = list(pd.read_csv(sample, nrows=0).columns)
    identifier = resolve_submission_identifier(sample_columns, identifier)
    converters = {} if identifier is None else {identifier: _identifier_value}
    expected = pd.read_csv(sample, converters=converters)
    actual = pd.read_csv(candidate, converters=converters)

    if len(actual) != len(expected):
        raise ValueError(f"row count mismatch: expected {len(expected)}, got {len(actual)}")
    if list(actual.columns) != list(expected.columns):
        raise ValueError(
            f"column mismatch: expected {list(expected.columns)}, got {list(actual.columns)}"
        )

    if identifier is not None:
        if identifier not in expected.columns:
            raise ValueError(f"identifier column {identifier!r} is absent from sample submission")
        if not actual[identifier].equals(expected[identifier]):
            raise ValueError("identifier values or order do not match sample submission")
        if not actual[identifier].is_unique:
            raise ValueError("identifier values must be unique")

    prediction_columns = [column for column in actual.columns if column != identifier]
    for column in prediction_columns:
        numeric = pd.to_numeric(actual[column], errors="coerce")
        if numeric.isna().any() or not numeric.map(math.isfinite).all():
            raise ValueError(f"prediction column {column!r} must contain finite numbers")

    return SubmissionProof(
        competition_slug=slug,
        sample_sha256=sha256_file(sample),
        candidate_sha256=sha256_file(candidate),
        row_count=len(actual),
        columns=list(actual.columns),
        validated_at=datetime.now(UTC),
    )


def assert_submission_unchanged(
    candidate: Path,
    proof: SubmissionProof,
    sample: Path | None = None,
) -> None:
    if not candidate.exists():
        raise FileNotFoundError(f"candidate submission not found: {candidate}")
    if sha256_file(candidate) != proof.candidate_sha256:
        raise ValueError("submission changed since validation")
    if sample is None:
        return
    if not sample.exists():
        raise FileNotFoundError(f"sample submission not found: {sample}")
    if sha256_file(sample) != proof.sample_sha256:
        raise ValueError("sample submission changed since validation")
