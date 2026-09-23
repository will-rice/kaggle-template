from pathlib import Path

import pytest

from competition.predict import predict_competition
from competition.train import train_competition
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.tracking import TrackingError


class FakeLogger:
    def __init__(self, failure: TrackingError | None = None) -> None:
        self._run_id = "fake-run"
        self.failure = failure
        self.logged = False
        self.finished = False

    @property
    def run_id(self) -> str | None:
        return self._run_id

    def log(self, metrics: dict[str, float], artifacts: list[Path]) -> None:
        if self.failure:
            raise self.failure
        assert "rmse" in metrics
        assert all(path.exists() for path in artifacts)
        self.logged = True

    def finish(self) -> None:
        self.finished = True


def test_train_and_predict_write_contract_artifacts(
    synthetic_config: CompetitionConfig,
    synthetic_paths: ProjectPaths,
) -> None:
    logger = FakeLogger()

    record = train_competition(synthetic_config, synthetic_paths, logger)
    candidate, proof = predict_competition(synthetic_config, synthetic_paths)

    assert record.status == "complete"
    assert record.manifest.wandb_run_id == "fake-run"
    assert (synthetic_paths.experiments / record.manifest.artifact_id / "manifest.json").exists()
    assert logger.logged and logger.finished
    assert candidate.exists()
    assert proof.row_count == 2


def test_wandb_failure_is_persisted_and_raised(
    synthetic_config: CompetitionConfig,
    synthetic_paths: ProjectPaths,
) -> None:
    with pytest.raises(RuntimeError, match="wandb unavailable"):
        train_competition(
            synthetic_config,
            synthetic_paths,
            FakeLogger(TrackingError("wandb unavailable")),
        )

    records = list(synthetic_paths.experiments.glob("*/experiment.json"))
    assert len(records) == 1
    assert '"status": "incomplete"' in records[0].read_text(encoding="utf-8")
