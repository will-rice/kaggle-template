import pandas as pd
import pytest
from pydantic import ValidationError

from competition.model import MeanRegressor
from competition.predict import predict_competition
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.predictions import OOFRow, validate_oof


def row(row_id: str, fold: int, prediction: float = 0.5) -> OOFRow:
    return OOFRow(
        row_id=row_id,
        fold=fold,
        prediction=[prediction],
        target=[1.0],
    )


def test_valid_oof_covers_each_row_once() -> None:
    validate_oof([row("a", 0), row("b", 1)], {"a": 0, "b": 1}, folds=2)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([row("a", 0), row("a", 1)], "duplicate"),
        ([row("a", 2), row("b", 1)], "fold"),
        ([row("a", 0)], "expected"),
        ([row("a", 1), row("b", 0)], "assignment"),
    ],
)
def test_rejects_invalid_oof(rows: list[OOFRow], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_oof(rows, {"a": 0, "b": 1}, folds=2)


def test_rejects_non_finite_oof_prediction() -> None:
    with pytest.raises(ValidationError):
        row("a", 0, float("nan"))


@pytest.mark.parametrize("sample_row_count", [1, 3])
def test_predict_rejects_sample_row_count_mismatch(
    sample_row_count: int,
    synthetic_config: CompetitionConfig,
    synthetic_paths: ProjectPaths,
) -> None:
    run_id = "trained-run"
    latest_path = synthetic_paths.experiments / "latest"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(run_id + "\n", encoding="utf-8")
    MeanRegressor(mean=2.5).save(
        synthetic_paths.experiments / run_id / "model.json",
    )
    pd.DataFrame(
        {
            "id": [f"sample-{index}" for index in range(sample_row_count)],
            "target": [0.0] * sample_row_count,
        }
    ).to_csv(synthetic_paths.data / "sample_submission.csv", index=False)

    with pytest.raises(
        ValueError,
        match=(
            rf"test data row count \(2\) does not match "
            rf"sample submission row count \({sample_row_count}\)"
        ),
    ):
        predict_competition(synthetic_config, synthetic_paths)
