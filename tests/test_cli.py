from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from kaggle_template.config import MetricDirection
from kaggle_template.kaggle import KaggleError, SubmissionResult
from kaggle_template.records import ArtifactManifest, ExperimentRecord, sha256_file
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


def _write_sample_submission(root: Path) -> Path:
    sample = root / "data" / "sample_submission.csv"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text("id,target\n1,0.0\n", encoding="utf-8")
    return sample


def _write_proof(candidate: Path, sample: Path | None = None) -> SubmissionProof:
    proof = SubmissionProof(
        competition_slug="synthetic-playground",
        sample_sha256=sha256_file(sample) if sample is not None else "sample",
        candidate_sha256=sha256_file(candidate),
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
    commands_section = result.output.split("│ --help", maxsplit=1)[-1]
    command_names = re.findall(r"^│ ([a-z-]+)\s+│$", commands_section, flags=re.MULTILINE)
    assert command_names == ["competition-init", "train", "predict", "submit"]
    assert "Usage" in result.output


def test_train_delegates_without_submitting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    submit_attempted = False
    monkeypatch.chdir(tmp_path)

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
    monkeypatch.chdir(tmp_path)

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
    _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate, tmp_path / "data" / "sample_submission.csv")
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
    _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate, tmp_path / "data" / "sample_submission.csv")
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
    assert SubmissionResult.model_validate_json(
        candidate.with_suffix(".result.json").read_text(encoding="utf-8")
    ) == SubmissionResult(ref="submission.csv", status="submitted", message="baseline")


def test_submit_surfaces_kaggle_errors_and_records_failed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate, tmp_path / "data" / "sample_submission.csv")
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
    recorded = SubmissionResult.model_validate_json(
        candidate.with_suffix(".result.json").read_text(encoding="utf-8")
    )
    assert recorded == SubmissionResult(
        ref="submission.csv",
        status="failed",
        message="KaggleError: rules not accepted",
    )
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("proof_content", "expected_reason"),
    [
        ("{not json}", "validation proof is malformed"),
        ('{"competition_slug":"synthetic-playground"}', "validation proof is malformed"),
    ],
)
def test_submit_rejects_malformed_proof_before_external_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    proof_content: str,
    expected_reason: str,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    candidate.with_suffix(".validation.json").write_text(proof_content, encoding="utf-8")
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

    assert result.exit_code != 0
    assert expected_reason in result.output
    assert client.calls == 0
    assert not candidate.with_suffix(".result.json").exists()


def test_submit_rejects_changed_candidate_before_external_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate, tmp_path / "data" / "sample_submission.csv")
    candidate.write_text("id,target\n1,0.7\n", encoding="utf-8")
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

    assert result.exit_code != 0
    assert "submission changed since validation" in result.output
    assert client.calls == 0
    assert not candidate.with_suffix(".result.json").exists()


def test_submit_rejects_changed_sample_before_external_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    sample = _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    _write_proof(candidate, sample)
    sample.write_text("id,target\n1,1.0\n", encoding="utf-8")
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

    assert result.exit_code != 0
    assert "sample submission changed since validation" in result.output
    assert client.calls == 0
    assert not candidate.with_suffix(".result.json").exists()


def test_competition_init_rejects_slug_mismatch_without_initializing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    initialized = False
    client_constructed = False
    monkeypatch.chdir(tmp_path)

    def fail_initialize(*args: object, **kwargs: object) -> object:
        nonlocal initialized
        initialized = True
        raise AssertionError("competition-init must stop before initialize on slug mismatch")

    def fail_client() -> object:
        nonlocal client_constructed
        client_constructed = True
        raise AssertionError("competition-init must not construct Kaggle client on slug mismatch")

    monkeypatch.setattr("kaggle_template.cli.initialize_competition", fail_initialize)
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", fail_client)

    result = runner.invoke(
        app,
        ["competition-init", "different-competition", "--config", str(config_path)],
    )

    assert result.exit_code != 0
    assert "Invalid value for slug" in result.output
    assert "different-competition" in result.output
    assert "synthetic-playground" in result.output
    assert not initialized
    assert not client_constructed


def test_competition_init_surfaces_kaggle_failure_without_success_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    monkeypatch.chdir(tmp_path)

    def raise_kaggle_error(*args: object) -> object:
        raise KaggleError("rules not accepted")

    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: object())
    monkeypatch.setattr("kaggle_template.cli.initialize_competition", raise_kaggle_error)

    result = runner.invoke(
        app,
        ["competition-init", "synthetic-playground", "--config", str(config_path)],
    )

    assert result.exit_code == 1
    assert "Kaggle error: rules not accepted" in result.output
    assert "Initialized" not in result.output


def _plain(output: str) -> str:
    return " ".join(re.sub(r"[│╭╮╰╯─]", " ", output).split())


def _submit_args(candidate: Path, config_path: Path) -> list[str]:
    return [
        "submit",
        str(candidate),
        "--message",
        "baseline",
        "--config",
        str(config_path),
        "--confirm",
    ]


@pytest.mark.parametrize(
    ("content", "expected_reason"),
    [
        ("id,target\n2,0.5\n", "identifier values or order do not match"),
        ("id,target\n1,nan\n", "must contain finite numbers"),
        ("id,prediction\n1,0.5\n", "column mismatch"),
    ],
)
def test_submit_revalidates_content_despite_hand_written_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    expected_reason: str,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    sample = _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text(content, encoding="utf-8")
    _write_proof(candidate, sample)
    client = FakeSubmitClient()
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: client)

    result = runner.invoke(app, _submit_args(candidate, config_path))

    assert result.exit_code == 2
    assert expected_reason in _plain(result.output)
    assert client.calls == 0
    assert not candidate.with_suffix(".result.json").exists()


def test_submit_rejects_proof_that_disagrees_with_revalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    sample = _write_sample_submission(tmp_path)
    monkeypatch.chdir(tmp_path)
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    proof = _write_proof(candidate, sample).model_copy(update={"row_count": 5})
    candidate.with_suffix(".validation.json").write_text(proof.model_dump_json(), encoding="utf-8")
    client = FakeSubmitClient()
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: client)

    result = runner.invoke(app, _submit_args(candidate, config_path))

    assert result.exit_code == 2
    assert "validation proof does not match" in _plain(result.output)
    assert client.calls == 0


def _assert_concise_failure(result: Result, expected: str) -> None:
    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
    assert expected in _plain(result.output)


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        (('slug = "synthetic-playground"', 'slug = "Not A Slug"'), "slug"),
        (("folds = 2", "folds = [unclosed"), "invalid TOML"),
        (('data = "data"', 'data = "../outside"'), "must stay within repository"),
    ],
)
@pytest.mark.parametrize("command", ["train", "predict", "submit", "competition-init"])
def test_cli_reports_config_and_path_errors_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: tuple[str, str],
    expected: str,
    command: str,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(*replacement),
        encoding="utf-8",
    )
    candidate = tmp_path / "submission.csv"
    candidate.write_text("id,target\n1,0.5\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", FakeSubmitClient)
    arguments = {
        "train": ["train"],
        "predict": ["predict"],
        "submit": ["submit", str(candidate), "--message", "baseline"],
        "competition-init": ["competition-init", "synthetic-playground"],
    }[command]

    result = runner.invoke(app, [*arguments, "--config", str(config_path)])

    _assert_concise_failure(result, expected)
    assert "Invalid value for '--config'" in _plain(result.output)


def test_competition_init_reports_initialization_errors_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    monkeypatch.chdir(tmp_path)

    def raise_value_error(*args: object) -> object:
        raise ValueError("repository is initialized for 'other'")

    monkeypatch.setattr("kaggle_template.cli.SubprocessKaggleClient", lambda: object())
    monkeypatch.setattr("kaggle_template.cli.initialize_competition", raise_value_error)

    result = runner.invoke(
        app,
        ["competition-init", "synthetic-playground", "--config", str(config_path)],
    )

    _assert_concise_failure(result, "Initialization error: repository is initialized for 'other'")
    assert result.exit_code == 1


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("train", "Error: missing training data"),
        ("predict", "Error: no trained experiment is recorded"),
    ],
)
def test_train_and_predict_report_missing_artifacts_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    expected: str,
) -> None:
    from kaggle_template.cli import app

    config_path = tmp_path / "configs" / "competition.toml"
    _write_config(config_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("kaggle_template.cli.WandbRunLogger", lambda **kwargs: object())

    result = runner.invoke(app, [command, "--config", str(config_path)])

    _assert_concise_failure(result, expected)
    assert result.exit_code == 1
