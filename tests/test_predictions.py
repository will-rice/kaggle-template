import pytest
from pydantic import ValidationError

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
