from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kaggle_template.config import MetricDirection
from kaggle_template.kaggle import KaggleError, SubmissionResult
from kaggle_template.records import ArtifactManifest, ExperimentRecord
from kaggle_template.submissions import SubmissionProof

runner = CliRunner()


def _write_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
slug = "synthetic-playground"
target = "target"
identifier = "id"
seeds = [17]
folds = 2
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
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_proof(candidate: Path) -> SubmissionProof:
    proof = SubmissionProof(
        competition_slug="synthetic-playground",
        sample_sha256="sample",
        candidate_sha256=__import__("hashlib").sha256(candidate.read_bytes()).hexdigest(),
        row_count=1,
        columns=["id", "target"],
        validated_at=datetime.fromisoformat("2026-09-23T12:00:00+00:00"),
    )
    candidate.with_suffix(".validation.json").write_text(
        proof.model_dump_json(),
        encoding="utf-8",
    )
    return proof


class FakeSubmitClient:
    def __init__(self, failure: KaggleError | None = None) -> None:
        self.failure = failure
        self.calls = 0

    def authenticate(self) -> None:
        pass

    def metadata(self, slug: str) -> object:
        raise AssertionError("submit does not fetch metadata")

    def download(self, slug: str, destination: Path) -> None:
        raise AssertionError("submit does not download")

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return SubmissionResult(ref=file.name, status="submitted", message=message)


def test_help_lists_exactly_four_workflow_commands() -> None:
    from kaggle_template.cli import app

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("competition-init", "train", "predict", "submit"):
        assert command in result.output
    assert "Usage" in result.output


def test_train_delegates_without_submitting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    submit_attempted = False

    def fail_client() -> object:
        nonlocal submit_attempted
        submit_attempted = True
        raise AssertionError("train must not construct Kaggle submit client")

    manifest = ArtifactManifest(
        artifact_id="run-123",
        competition_slug="synthetic-playground",
        created_at=datetime.fromisoformat("2026-09-23T12:00:00+00:00"),
        command=["kaggle-template", "train"],
        resolved_config={},
        source_revision="abc123",
        dirty_worktree=False,
        seed=17,
        fold=None,
        inputs=["data/train.csv"],
        outputs=["artifacts/predictions/run-123/oof.csv"],
        checksums={"artifacts/predictions/run-123/oof.csv": "abc"},
        metrics={"rmse": 0.5},
        metric_direction=MetricDirection.MINIMIZE,
        wandb_run_id="wandb-123",
    )
    record = ExperimentRecord(manifest=manifest, status="complete", failure=None)

    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", fail_client)
    monkeypatch.setattr("kaggle_template.cli.WandbRunLogger", lambda **kwargs: object())
    monkeypatch.setattr("kaggle_template.cli.train_competition", lambda *args: record)

    result = runner.invoke(app, ["train", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "run-123" in result.output
    assert "rmse" in result.output
    assert not submit_attempted


def test_predict_delegates_without_submitting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    submit_attempted = False

    def fail_client() -> object:
        nonlocal submit_attempted
        submit_attempted = True
        raise AssertionError("predict must not construct Kaggle submit client")

    candidate = tmp_path / "artifacts" / "submissions" / "submission.csv"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    proof = _write_proof(candidate)

    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", fail_client)
    monkeypatch.setattr(
        "kaggle_template.cli.predict_competition",
        lambda *args: (candidate, proof),
    )

    result = runner.invoke(app, ["predict", "--config", str(config_path)])

    assert result.exit_code == 0
    assert str(candidate) in result.output
    assert "1 rows" in result.output
    assert not submit_attempted


def test_submit_without_confirm_exits_without_external_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate)
    client = FakeSubmitClient()
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: client)

    result = runner.invoke(
        app,
        [
            "submit",
            str(candidate),
            "--message",
            "baseline",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 2
    assert "Competition: synthetic-playground" in result.output
    assert f"File: {candidate}" in result.output
    assert "Message: baseline" in result.output
    assert "Validation: validated 1 rows at 2026-09-23T12:00:00+00:00" in result.output
    assert "--confirm" in result.output
    assert client.calls == 0
    assert not candidate.with_suffix(".result.json").exists()


def test_submit_displays_fields_and_calls_once_with_confirm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate)
    client = FakeSubmitClient()
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: client)

    result = runner.invoke(
        app,
        [
            "submit",
            str(candidate),
            "--message",
            "baseline",
            "--config",
            str(config_path),
            "--confirm",
        ],
    )

    assert result.exit_code == 0
    assert "Competition: synthetic-playground" in result.output
    assert f"File: {candidate}" in result.output
    assert "Message: baseline" in result.output
    assert "Validation: validated 1 rows at 2026-09-23T12:00:00+00:00" in result.output
    assert "Result: submitted (submission.csv) baseline" in result.output
    assert client.calls == 1
    assert candidate.with_suffix(".result.json").read_text(encoding="utf-8")


def test_submit_surfaces_kaggle_errors_without_recording_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate)
    client = FakeSubmitClient(KaggleError("rules not accepted"))
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: client)

    result = runner.invoke(
        app,
        [
            "submit",
            str(candidate),
            "--message",
            "baseline",
            "--config",
            str(config_path),
            "--confirm",
        ],
    )

    assert result.exit_code == 1
    assert "Kaggle error: rules not accepted" in result.output
    assert client.calls == 1
    assert not candidate.with_suffix(".result.json").exists()
