from pathlib import Path

import pandas as pd
import pytest

from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths, resolve_project_paths


@pytest.fixture
def synthetic_config() -> CompetitionConfig:
    return CompetitionConfig.model_validate(
        {
            "slug": "synthetic-playground",
            "target": "target",
            "identifier": "id",
            "metric": {"name": "rmse", "direction": "minimize"},
            "seeds": [17],
            "folds": 2,
            "wandb_project": "synthetic-playground",
            "paths": {
                "data": "data",
                "reports": "reports",
                "experiments": "artifacts/experiments",
                "predictions": "artifacts/predictions",
                "submissions": "artifacts/submissions",
            },
        }
    )


@pytest.fixture
def synthetic_paths(
    tmp_path: Path,
    synthetic_config: CompetitionConfig,
) -> ProjectPaths:
    paths = resolve_project_paths(tmp_path, synthetic_config.paths)
    paths.data.mkdir(parents=True)
    pd.DataFrame(
        {"id": ["a", "b", "c", "d"], "feature": [0, 1, 2, 3], "target": [1.0, 2.0, 3.0, 4.0]}
    ).to_csv(paths.data / "train.csv", index=False)
    pd.DataFrame({"id": ["e", "f"], "feature": [4, 5]}).to_csv(
        paths.data / "test.csv",
        index=False,
    )
    pd.DataFrame({"id": ["e", "f"], "target": [0.0, 0.0]}).to_csv(
        paths.data / "sample_submission.csv",
        index=False,
    )
    return paths
