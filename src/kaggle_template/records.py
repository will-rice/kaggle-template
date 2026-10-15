import json
import os
import tempfile
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kaggle_template.config import MetricDirection


class ArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    artifact_id: str = Field(min_length=1)
    competition_slug: str = Field(min_length=1)
    created_at: datetime
    command: list[str] = Field(min_length=1)
    resolved_config: dict[str, object]
    source_revision: str = Field(min_length=1)
    dirty_worktree: bool
    seed: int | None = None
    fold: int | None = None
    inputs: list[str]
    outputs: list[str]
    checksums: dict[str, str]
    metrics: dict[str, float]
    metric_direction: MetricDirection
    wandb_run_id: str | None = None


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: ArtifactManifest
    status: Literal["complete", "incomplete"]
    failure: str | None = None

    @model_validator(mode="after")
    def require_failure_for_incomplete(self) -> Self:
        if self.status == "incomplete" and not self.failure:
            raise ValueError("failure is required when status is incomplete")
        if self.status == "complete" and self.failure is not None:
            raise ValueError("failure must be absent when status is complete")
        return self


def is_better(
    candidate: float,
    incumbent: float,
    direction: MetricDirection,
) -> bool:
    if direction == MetricDirection.MINIMIZE:
        return candidate < incumbent
    return candidate > incumbent


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write text via a unique sibling temp file, fsync it, then atomically replace path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_model(path: Path, model: BaseModel) -> None:
    payload = model.model_dump(mode="json")
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
