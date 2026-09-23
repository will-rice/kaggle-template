import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from kaggle_template.config import MetricDirection
from kaggle_template.records import (
    ArtifactManifest,
    ExperimentRecord,
    atomic_write_model,
    atomic_write_text,
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
    assert ExperimentRecord.model_validate_json(output.read_text(encoding="utf-8")) == record
    assert not list(output.parent.glob("*.tmp"))


def test_checksum_matches_known_digest_and_detects_content_change(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    path.write_bytes(b"abc")
    assert sha256_file(path) == ("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    path.write_bytes(b"abd")
    assert sha256_file(path) != ("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


def test_complete_record_rejects_failure() -> None:
    with pytest.raises(ValidationError, match="failure must be absent"):
        ExperimentRecord(manifest=manifest(), status="complete", failure="W&B failed")


def test_atomic_write_text_replaces_content_without_leftovers(tmp_path: Path) -> None:
    path = tmp_path / "experiments" / "latest"
    atomic_write_text(path, "run-1\n")
    atomic_write_text(path, "run-2\n")

    assert path.read_text(encoding="utf-8") == "run-2\n"
    assert sorted(item.name for item in path.parent.iterdir()) == ["latest"]


def test_atomic_write_text_preserves_previous_content_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "latest"
    atomic_write_text(path, "run-1\n")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated crash"):
        atomic_write_text(path, "run-2\n")

    assert path.read_text(encoding="utf-8") == "run-1\n"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["latest"]


def test_incomplete_record_requires_failure() -> None:
    with pytest.raises(ValidationError, match="failure"):
        ExperimentRecord(manifest=manifest(), status="incomplete", failure=None)
