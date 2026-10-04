from pathlib import Path
from types import SimpleNamespace

import pytest

from kaggle_template.tracking import TrackingError, WandbRunLogger


class FakeWandbError(Exception):
    pass


class FakeArtifact:
    def __init__(self, name: str, type: str) -> None:
        self.name = name
        self.type = type
        self.files: list[str] = []

    def add_file(self, path: str) -> None:
        self.files.append(path)


class FakeRun:
    def __init__(
        self,
        run_id: str = "fake-run",
        *,
        log_error: Exception | None = None,
        finish_error: Exception | None = None,
    ) -> None:
        self.id = run_id
        self.logged: list[dict[str, float]] = []
        self.artifacts: list[FakeArtifact] = []
        self.log_error = log_error
        self.finish_error = finish_error
        self.finish_calls = 0

    def log(self, metrics: dict[str, float]) -> None:
        if self.log_error is not None:
            raise self.log_error
        self.logged.append(metrics)

    def log_artifact(self, artifact: FakeArtifact) -> None:
        if self.log_error is not None:
            raise self.log_error
        self.artifacts.append(artifact)

    def finish(self) -> None:
        self.finish_calls += 1
        if self.finish_error is not None:
            raise self.finish_error


def test_wandb_logger_rejects_missing_lazy_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kaggle_template.tracking.wandb",
        SimpleNamespace(
            Error=FakeWandbError,
            init=lambda **_: None,
            Artifact=FakeArtifact,
        ),
    )

    logger = WandbRunLogger("demo", {"seed": 17})

    with pytest.raises(TrackingError, match="returned no run"):
        logger.log({"rmse": 0.1}, [Path("artifact.txt")])


def test_wandb_logger_translates_initialization_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_init(**_: object) -> FakeRun:
        raise FakeWandbError("boom")

    monkeypatch.setattr(
        "kaggle_template.tracking.wandb",
        SimpleNamespace(
            Error=FakeWandbError,
            init=fail_init,
            Artifact=FakeArtifact,
        ),
    )

    logger = WandbRunLogger("demo", {"seed": 17})

    with pytest.raises(TrackingError, match="W&B initialization failed: boom"):
        logger.log({"rmse": 0.1}, [Path("artifact.txt")])


def test_wandb_logger_translates_logging_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    run = FakeRun(log_error=FakeWandbError("log boom"))
    monkeypatch.setattr(
        "kaggle_template.tracking.wandb",
        SimpleNamespace(
            Error=FakeWandbError,
            init=lambda **_: run,
            Artifact=FakeArtifact,
        ),
    )

    logger = WandbRunLogger("demo", {"seed": 17})

    with pytest.raises(TrackingError, match="W&B logging failed: log boom"):
        logger.log({"rmse": 0.1}, [Path("artifact.txt")])


def test_wandb_logger_translates_finalization_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = FakeRun(finish_error=FakeWandbError("finish boom"))
    monkeypatch.setattr(
        "kaggle_template.tracking.wandb",
        SimpleNamespace(
            Error=FakeWandbError,
            init=lambda **_: run,
            Artifact=FakeArtifact,
        ),
    )

    logger = WandbRunLogger("demo", {"seed": 17})
    logger.log({"rmse": 0.1}, [Path("artifact.txt")])

    with pytest.raises(TrackingError, match="W&B finalization failed: finish boom"):
        logger.finish()
