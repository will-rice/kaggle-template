from pathlib import Path

import pytest
from pydantic import ValidationError

from kaggle_template.config import CompetitionConfig, MetricDirection, load_config
from kaggle_template.paths import resolve_project_paths


def test_load_config_preserves_absent_optional_columns(tmp_path: Path) -> None:
    path = tmp_path / "competition.toml"
    path.write_text(
        """
slug = "synthetic-playground"
seeds = [17, 29]
folds = 3
wandb_project = "synthetic-playground"

[metric]
name = "rmse"
direction = "minimize"

[paths]
data = "data"
reports = "reports"
experiments = "artifacts/experiments"
predictions = "artifacts/predictions"
submissions = "artifacts/submissions"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.target is None
    assert config.identifier is None
    assert config.metric.direction is MetricDirection.MINIMIZE
    assert config.seeds == [17, 29]


@pytest.mark.parametrize("slug", ["Upper_Case", "../escape", "two words", ""])
def test_rejects_invalid_slug(slug: str) -> None:
    with pytest.raises(ValidationError):
        CompetitionConfig.model_validate(
            {
                "slug": slug,
                "metric": {"name": "rmse", "direction": "minimize"},
                "seeds": [17],
                "folds": 2,
                "wandb_project": "test",
                "paths": {
                    "data": "data",
                    "reports": "reports",
                    "experiments": "artifacts/experiments",
                    "predictions": "artifacts/predictions",
                    "submissions": "artifacts/submissions",
                },
            }
        )


def test_paths_are_absolute_and_contained(tmp_path: Path) -> None:
    config = load_config(Path("configs/competition.toml"))
    paths = resolve_project_paths(tmp_path, config.paths)
    assert paths.root == tmp_path.resolve()
    assert paths.data == tmp_path.resolve() / "data"


def test_rejects_path_outside_repository(tmp_path: Path) -> None:
    config = load_config(Path("configs/competition.toml"))
    invalid = config.paths.model_copy(update={"data": "../outside"})
    with pytest.raises(ValueError, match="must stay within repository"):
        resolve_project_paths(tmp_path, invalid)
