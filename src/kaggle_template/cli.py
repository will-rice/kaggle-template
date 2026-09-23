from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from competition.predict import predict_competition
from competition.train import train_competition
from kaggle_template.config import CompetitionConfig, load_config
from kaggle_template.initialize import initialize_competition
from kaggle_template.kaggle import KaggleError, SubprocessKaggleClient
from kaggle_template.paths import ProjectPaths, resolve_project_paths
from kaggle_template.records import atomic_write_model
from kaggle_template.submissions import (
    SubmissionProof,
    assert_submission_unchanged,
)
from kaggle_template.tracking import WandbRunLogger

app = typer.Typer(no_args_is_help=True)


def _load_context(config_path: Path) -> tuple[CompetitionConfig, ProjectPaths]:
    config = load_config(config_path)
    paths = resolve_project_paths(Path.cwd(), config.paths)
    return config, paths


def _load_submission_proof(proof_path: Path, config: CompetitionConfig) -> SubmissionProof:
    try:
        proof = SubmissionProof.model_validate_json(proof_path.read_text(encoding="utf-8"))
    except ValidationError as error:
        raise typer.BadParameter("validation proof is malformed", param_hint="file") from error

    if proof.competition_slug != config.slug:
        raise typer.BadParameter(
            f"proof is for {proof.competition_slug!r}, not {config.slug!r}",
            param_hint="file",
        )
    return proof


def _assert_submission_is_current(
    candidate: Path,
    sample: Path,
    proof: SubmissionProof,
) -> None:
    try:
        assert_submission_unchanged(candidate, proof, sample)
    except (FileNotFoundError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="file") from error


@app.command("competition-init")
def competition_init(
    slug: str,
    config_path: Annotated[
        Path,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/competition.toml"),
) -> None:
    config, paths = _load_context(config_path)
    if slug != config.slug:
        raise typer.BadParameter(
            f"slug {slug!r} does not match config slug {config.slug!r}",
            param_hint="slug",
        )
    try:
        state = initialize_competition(config, paths, SubprocessKaggleClient())
    except KaggleError as error:
        typer.echo(f"Kaggle error: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(f"Initialized {state.slug}: {state.title}")


@app.command()
def train(
    config_path: Annotated[
        Path,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/competition.toml"),
) -> None:
    config, paths = _load_context(config_path)
    logger = WandbRunLogger(
        project=config.wandb_project,
        config=config.model_dump(mode="json"),
    )
    record = train_competition(config, paths, logger)
    typer.echo(f"Recorded {record.manifest.artifact_id}: {record.manifest.metrics}")


@app.command()
def predict(
    config_path: Annotated[
        Path,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/competition.toml"),
) -> None:
    config, paths = _load_context(config_path)
    candidate, proof = predict_competition(config, paths)
    typer.echo(f"Validated {candidate} ({proof.row_count} rows)")


@app.command()
def submit(
    file: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True),
    ],
    message: Annotated[str, typer.Option("--message")],
    confirm: Annotated[bool, typer.Option("--confirm")] = False,
    config_path: Annotated[
        Path,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/competition.toml"),
) -> None:
    config, paths = _load_context(config_path)
    if not message.strip():
        raise typer.BadParameter("message must not be empty", param_hint="message")
    proof_path = file.with_suffix(".validation.json")
    if not proof_path.exists():
        raise typer.BadParameter(
            f"validation proof not found: {proof_path}",
            param_hint="file",
        )

    proof = _load_submission_proof(proof_path, config)
    _assert_submission_is_current(file, paths.data / "sample_submission.csv", proof)

    typer.echo(f"Competition: {config.slug}")
    typer.echo(f"File: {file}")
    typer.echo(f"Message: {message}")
    typer.echo(f"Validation: validated {proof.row_count} rows at {proof.validated_at.isoformat()}")

    if not confirm:
        typer.echo("Submission not sent: pass --confirm to submit.", err=True)
        raise typer.Exit(2)

    client = SubprocessKaggleClient()
    try:
        result = client.submit(config.slug, file, message)
    except KaggleError as error:
        typer.echo(f"Kaggle error: {error}", err=True)
        raise typer.Exit(1) from error

    atomic_write_model(file.with_suffix(".result.json"), result)
    typer.echo(f"Result: {result.status} ({result.ref}) {result.message}")
