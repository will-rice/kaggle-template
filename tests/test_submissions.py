from pathlib import Path

import pandas as pd
import pytest

from kaggle_template.records import sha256_file
from kaggle_template.submissions import (
    assert_submission_unchanged,
    validate_submission,
)


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    sample = tmp_path / "sample_submission.csv"
    candidate = tmp_path / "submission.csv"
    pd.DataFrame({"id": [10, 11], "target": [0.0, 0.0]}).to_csv(sample, index=False)
    pd.DataFrame({"id": [10, 11], "target": [1.2, 2.3]}).to_csv(candidate, index=False)
    return sample, candidate


def test_valid_submission_creates_checksum_proof(files: tuple[Path, Path]) -> None:
    sample, candidate = files
    proof = validate_submission(candidate, sample, "synthetic-playground", "id")
    assert proof.row_count == 2
    assert proof.columns == ["id", "target"]
    assert proof.sample_sha256 == sha256_file(sample)
    assert proof.candidate_sha256 == sha256_file(candidate)
    assert_submission_unchanged(candidate, proof)


@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame({"id": [10], "target": [1.0]}),
        pd.DataFrame({"target": [1.0, 2.0], "id": [10, 11]}),
        pd.DataFrame({"id": [11, 10], "target": [1.0, 2.0]}),
        pd.DataFrame({"id": [10, 10], "target": [1.0, 2.0]}),
        pd.DataFrame({"id": [10, 11], "target": [float("nan"), 2.0]}),
        pd.DataFrame({"id": [10, 11], "target": [float("inf"), 2.0]}),
    ],
)
def test_rejects_submission_mismatch(
    files: tuple[Path, Path],
    frame: pd.DataFrame,
) -> None:
    sample, candidate = files
    frame.to_csv(candidate, index=False)
    with pytest.raises(ValueError):
        validate_submission(candidate, sample, "synthetic-playground", "id")


def test_changed_file_invalidates_proof(files: tuple[Path, Path]) -> None:
    sample, candidate = files
    proof = validate_submission(candidate, sample, "synthetic-playground", "id")
    candidate.write_text("id,target\n10,9\n11,9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since validation"):
        assert_submission_unchanged(candidate, proof)


def test_rejects_duplicate_identifiers_even_when_sample_matches(tmp_path: Path) -> None:
    sample = tmp_path / "sample_submission.csv"
    candidate = tmp_path / "submission.csv"
    frame = pd.DataFrame({"id": [10, 10], "target": [0.0, 1.0]})
    frame.to_csv(sample, index=False)
    frame.to_csv(candidate, index=False)
    with pytest.raises(ValueError, match="unique"):
        validate_submission(candidate, sample, "synthetic-playground", "id")


def test_preserves_identifier_formatting_when_identifier_is_configured(
    tmp_path: Path,
) -> None:
    sample = tmp_path / "sample_submission.csv"
    candidate = tmp_path / "submission.csv"

    pd.DataFrame({"id": ["001", "002"], "target": [0.0, 0.0]}).to_csv(sample, index=False)

    pd.DataFrame({"id": ["1", "2"], "target": [1.0, 2.0]}).to_csv(candidate, index=False)
    with pytest.raises(ValueError, match="identifier values or order do not match"):
        validate_submission(candidate, sample, "synthetic-playground", "id")

    pd.DataFrame({"id": ["001", "002"], "target": [1.0, 2.0]}).to_csv(candidate, index=False)
    proof = validate_submission(candidate, sample, "synthetic-playground", "id")
    assert proof.columns == ["id", "target"]
