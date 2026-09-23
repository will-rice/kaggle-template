from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from kaggle_template.config import MetricDirection
from kaggle_template.records import (
    ArtifactManifest,
    ExperimentRecord,
    atomic_write_model,
    is_better,
    sha256_file,
)


def manifest() -> ArtifactManifest:
    return ArtifactManifest(
        artifact_id="run-001",
        competition_slug="synthetic-playground",
        created_at=datetime.now(UTC),
        command=["kaggle-template", "train"],
        resolved_config={"folds": 3},
        source_revision="abc123",
        dirty_worktree=False,
        seed=17,
        fold=None,
        inputs=["data/train.csv"],
        outputs=["artifacts/predictions/oof.csv"],
        checksums={"artifacts/predictions/oof.csv": "abc"},
        metrics={"rmse": 0.5},
        metric_direction=MetricDirection.MINIMIZE,
        wandb_run_id=None,
    )


def test_metric_direction() -> None:
    assert is_better(0.4, 0.5, MetricDirection.MINIMIZE)
    assert is_better(0.6, 0.5, MetricDirection.MAXIMIZE)
    assert not is_better(0.5, 0.5, MetricDirection.MAXIMIZE)


def test_manifest_rejects_unknown_schema_version() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        ArtifactManifest.model_validate({**manifest().model_dump(), "schema_version": 2})


def test_checksum_and_atomic_record(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "experiment.json"
    record = ExperimentRecord(
        manifest=manifest(),
        status="complete",
        failure=None,
    )
    atomic_write_model(output, record)
    assert output.exists()
    assert not output.with_suffix(".json.tmp").exists()
    assert sha256_file(output) == sha256_file(output)


def test_incomplete_record_requires_failure() -> None:
    with pytest.raises(ValidationError, match="failure"):
        ExperimentRecord(manifest=manifest(), status="incomplete", failure=None)
