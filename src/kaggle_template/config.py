import tomllib
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class MetricDirection(StrEnum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class MetricConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    direction: MetricDirection


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: str
    reports: str
    experiments: str
    predictions: str
    submissions: str


class CompetitionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    target: str | None = None
    identifier: str | None = None
    metric: MetricConfig
    seeds: list[int] = Field(min_length=1)
    folds: int = Field(ge=2)
    wandb_project: str = Field(min_length=1)
    paths: PathsConfig


def load_config(path: Path) -> CompetitionConfig:
    with path.open("rb") as handle:
        return CompetitionConfig.model_validate(tomllib.load(handle))
