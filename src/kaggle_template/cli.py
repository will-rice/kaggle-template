import tomllib
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from pydantic import ValidationError

from competition.predict import predict_competition
from competition.train import train_competition
from kaggle_template.config import CompetitionConfig, load_config
from kaggle_template.initialize import initialize_competition
from kaggle_template.kaggle import KaggleError, SubmissionResult, SubprocessKaggleClient
from kaggle_template.paths import ProjectPaths, resolve_project_paths
from kaggle_template.records import atomic_write_model
from kaggle_template.submissions import (
    SubmissionProof,
    assert_submission_unchanged,
    validate_submission,
)
from kaggle_template.tracking import TrackingError, WandbRunLogger

app = typer.Typer(no_args_is_help=True)


def _summarize_validation(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc']) or 'value'}: {detail['msg']}"
        for detail in error.errors()
    )


def _load_context(config_path: Path) -> tuple[CompetitionConfig, ProjectPaths]:
    try:
        config = load_config(config_path)
        paths = resolve_project_paths(Path.cwd(), config.paths)
    except tomllib.TOMLDecodeError as error:
        raise typer.BadParameter(f"invalid TOML: {error}", param_hint="'--config'") from error
    except ValidationError as error:
        raise typer.BadParameter(_summarize_validation(error), param_hint="'--config'") from error
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="'--config'") from error
    return config, paths


def _fail(prefix: str, error: Exception) -> NoReturn:
    typer.echo(f"{prefix}: {error}", err=True)
    raise typer.Exit(1) from error


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
    config: CompetitionConfig,
) -> None:
    try:
        assert_submission_unchanged(candidate, proof, sample)
        current = validate_submission(candidate, sample, config.slug, config.identifier)
    except (FileNotFoundError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="file") from error

    fields = ("candidate_sha256", "sample_sha256", "row_count", "columns")
    if any(getattr(current, field) != getattr(proof, field) for field in fields):
        raise typer.BadParameter(
            "validation proof does not match current submission content; rerun predict",
            param_hint="file",
        )


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
        _fail("Kaggle error", error)
    except (FileNotFoundError, ValueError) as error:
        _fail("Initialization error", error)
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
    try:
        record = train_competition(config, paths, logger)
    except TrackingError as error:
        _fail("W&B error", error)
    except (FileNotFoundError, ValueError) as error:
        _fail("Error", error)
    typer.echo(f"Recorded {record.manifest.artifact_id}: {record.manifest.metrics}")


@app.command()
def predict(
    config_path: Annotated[
        Path,
        typer.Option("--config", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/competition.toml"),
) -> None:
    config, paths = _load_context(config_path)
    try:
        candidate, proof = predict_competition(config, paths)
    except (FileNotFoundError, ValueError) as error:
        _fail("Error", error)
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
    _assert_submission_is_current(file, paths.data / "sample_submission.csv", proof, config)

    typer.echo(f"Competition: {config.slug}")
    typer.echo(f"File: {file}")
    typer.echo(f"Message: {message}")
    typer.echo(f"Validation: validated {proof.row_count} rows at {proof.validated_at.isoformat()}")

    if not confirm:
        typer.echo("Submission not sent: pass --confirm to submit.", err=True)
        raise typer.Exit(2)

    result_path = file.with_suffix(".result.json")
    client = SubprocessKaggleClient()
    try:
        result = client.submit(config.slug, file, message)
    except KaggleError as error:
        typer.echo(f"Kaggle error: {error}", err=True)
        failed = SubmissionResult(
            ref=file.name,
            status="failed",
            message=f"{type(error).__name__}: {error}",
        )
        try:
            atomic_write_model(result_path, failed)
        except OSError as persist_error:
            typer.echo(
                f"Also failed to record failed submission result: {persist_error}",
                err=True,
            )
        raise typer.Exit(1) from error

    typer.echo(f"Result: {result.status} ({result.ref}) {result.message}")
    try:
        atomic_write_model(result_path, result)
    except OSError as error:
        typer.echo(
            "Kaggle accepted the submission, but local recording failed: "
            f"{error}. Do not retry automatically.",
            err=True,
        )
        raise typer.Exit(1) from error
