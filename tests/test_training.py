import csv
import json
from pathlib import Path

import pytest

from competition.predict import predict_competition
from competition.train import train_competition
from competition.validation import assign_folds
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.predictions import OOFRow, validate_oof
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


def test_train_persists_oof_rows_using_public_contract(
    synthetic_config: CompetitionConfig,
    synthetic_paths: ProjectPaths,
) -> None:
    record = train_competition(synthetic_config, synthetic_paths, FakeLogger())

    oof_path = synthetic_paths.predictions / record.manifest.artifact_id / "oof.csv"
    csv_rows = list(csv.DictReader(oof_path.open(encoding="utf-8")))
    raw_rows = [
        OOFRow.model_validate(
            {
                "row_id": row["row_id"],
                "fold": int(row["fold"]),
                "prediction": json.loads(row["prediction"]),
                "target": json.loads(row["target"]),
            }
        )
        for row in csv_rows
    ]

    expected_folds = dict(
        zip(
            ["a", "b", "c", "d"],
            assign_folds(4, synthetic_config.folds, synthetic_config.seeds[0]),
            strict=True,
        )
    )
    source_targets = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    validate_oof(raw_rows, expected_folds, synthetic_config.folds)

    assert [row["prediction"] for row in csv_rows] == [
        json.dumps(
            [
                sum(
                    target
                    for other_row_id, target in source_targets.items()
                    if expected_folds[other_row_id] != expected_folds[row["row_id"]]
                )
                / sum(
                    1
                    for other_row_id in source_targets
                    if expected_folds[other_row_id] != expected_folds[row["row_id"]]
                )
            ]
        )
        for row in csv_rows
    ]
    assert [row["target"] for row in csv_rows] == [
        "[1.0]",
        "[2.0]",
        "[3.0]",
        "[4.0]",
    ]
    assert [row.prediction for row in raw_rows] == [
        json.loads(cell) for cell in [row["prediction"] for row in csv_rows]
    ]
    assert [row.target for row in raw_rows] == [[1.0], [2.0], [3.0], [4.0]]


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


def test_predict_requires_resolved_model_artifact(
    synthetic_config: CompetitionConfig,
    synthetic_paths: ProjectPaths,
) -> None:
    run_id = "missing-model"
    latest_path = synthetic_paths.experiments / "latest"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(run_id + "\n", encoding="utf-8")

    missing_model = synthetic_paths.experiments / run_id / "model.json"
    with pytest.raises(FileNotFoundError, match=str(missing_model)):
        predict_competition(synthetic_config, synthetic_paths)
