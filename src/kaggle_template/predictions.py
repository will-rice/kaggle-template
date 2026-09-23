import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OOFRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: str
    fold: int = Field(ge=0)
    prediction: list[float] = Field(min_length=1)
    target: list[float] | None

    @field_validator("prediction")
    @classmethod
    def finite_predictions(cls, values: list[float]) -> list[float]:
        if not all(math.isfinite(value) for value in values):
            raise ValueError("prediction values must be finite")
        return values


def validate_oof(
    rows: list[OOFRow],
    expected_folds: dict[str, int],
    folds: int,
) -> None:
    actual = [row.row_id for row in rows]
    if len(actual) != len(set(actual)):
        raise ValueError("duplicate OOF row identifiers")
    if set(actual) != set(expected_folds) or len(actual) != len(expected_folds):
        raise ValueError("OOF rows do not match expected training rows")
    if any(row.fold >= folds for row in rows):
        raise ValueError(f"OOF fold must be between 0 and {folds - 1}")
    if any(expected_folds[row.row_id] != row.fold for row in rows):
        raise ValueError("OOF fold assignment does not match validation definition")
