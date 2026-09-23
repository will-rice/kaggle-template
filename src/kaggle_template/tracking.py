from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import wandb


@runtime_checkable
class RunLogger(Protocol):
    @property
    def run_id(self) -> str | None: ...

    def log(self, metrics: dict[str, float], artifacts: list[Path]) -> None: ...

    def finish(self) -> None: ...


class TrackingError(RuntimeError):
    pass


class WandbRunLogger:
    def __init__(self, project: str, config: dict[str, object]) -> None:
        self._project = project
        self._config = config
        self._run: Any | None = None

    @property
    def run_id(self) -> str | None:
        return None if self._run is None else str(self._run.id)

    def _ensure_run(self) -> Any:
        if self._run is not None:
            return self._run
        try:
            run = wandb.init(project=self._project, config=self._config)
        except wandb.Error as error:
            raise TrackingError(f"W&B initialization failed: {error}") from error
        if run is None:
            raise TrackingError("W&B initialization returned no run")
        self._run = run
        return run

    def log(self, metrics: dict[str, float], artifacts: list[Path]) -> None:
        run = self._ensure_run()
        try:
            run.log(metrics)
            artifact = wandb.Artifact(f"run-{run.id}", type="experiment")
            for path in artifacts:
                artifact.add_file(str(path))
            run.log_artifact(artifact)
        except wandb.Error as error:
            raise TrackingError(f"W&B logging failed: {error}") from error

    def finish(self) -> None:
        if self._run is None:
            return
        try:
            self._run.finish()
        except wandb.Error as error:
            raise TrackingError(f"W&B finalization failed: {error}") from error
