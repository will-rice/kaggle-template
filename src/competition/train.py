import math
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from competition.data import load_train
from competition.model import MeanRegressor
from competition.validation import assign_folds
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.predictions import OOFRow, validate_oof, write_oof_rows
from kaggle_template.records import (
    ArtifactManifest,
    ExperimentRecord,
    atomic_write_model,
    sha256_file,
)
from kaggle_template.tracking import RunLogger, TrackingError


def _git(command: list[str], root: Path) -> str:
    process = subprocess.run(
        ["git", *command],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        if command == ["rev-parse", "HEAD"]:
            return "unversioned-synthetic-fixture"
        if command == ["status", "--porcelain"]:
            return "synthetic-fixture-dirty"
        detail = (process.stderr or process.stdout).strip()
        raise RuntimeError(f"git {' '.join(command)} failed: {detail}")
    return process.stdout.strip()


def train_competition(
    config: CompetitionConfig,
    paths: ProjectPaths,
    logger: RunLogger,
) -> ExperimentRecord:
    if config.target is None:
        raise ValueError("config key 'target' is required for training")

    frame = load_train(paths.data)
    if config.target not in frame:
        raise ValueError(f"target column {config.target!r} is absent from train.csv")

    row_ids = (
        frame[config.identifier].astype(str).tolist()
        if config.identifier is not None
        else [str(index) for index in frame.index]
    )
    fold_ids = assign_folds(len(frame), config.folds, config.seeds[0])
    predictions = [0.0] * len(frame)

    for fold in range(config.folds):
        train_targets = (
            frame.loc[
                [assigned != fold for assigned in fold_ids],
                config.target,
            ]
            .astype(float)
            .tolist()
        )
        model = MeanRegressor()
        model.fit(train_targets)
        held_out = [assigned == fold for assigned in fold_ids]
        fold_predictions = iter(model.predict(sum(held_out)))
        for index, is_held_out in enumerate(held_out):
            if is_held_out:
                predictions[index] = next(fold_predictions)

    rows = [
        OOFRow(
            row_id=row_id,
            fold=fold,
            prediction=[prediction],
            target=[float(target)],
        )
        for row_id, fold, prediction, target in zip(
            row_ids,
            fold_ids,
            predictions,
            frame[config.target],
            strict=True,
        )
    ]
    validate_oof(rows, dict(zip(row_ids, fold_ids, strict=True)), config.folds)

    run_id = uuid4().hex
    run_dir = paths.experiments / run_id

    oof_path = paths.predictions / run_id / "oof.csv"
    write_oof_rows(rows, oof_path)

    final_model = MeanRegressor()
    final_model.fit(frame[config.target].astype(float).tolist())
    model_path = run_dir / "model.json"
    final_model.save(model_path)

    rmse = math.sqrt(
        sum(
            (prediction - float(target)) ** 2
            for prediction, target in zip(predictions, frame[config.target], strict=True)
        )
        / len(frame)
    )

    manifest = ArtifactManifest(
        artifact_id=run_id,
        competition_slug=config.slug,
        created_at=datetime.now(UTC),
        command=["kaggle-template", "train"],
        resolved_config=config.model_dump(mode="json"),
        source_revision=_git(["rev-parse", "HEAD"], paths.root),
        dirty_worktree=bool(_git(["status", "--porcelain"], paths.root)),
        seed=config.seeds[0],
        fold=None,
        inputs=[str((paths.data / "train.csv").relative_to(paths.root))],
        outputs=[
            str(oof_path.relative_to(paths.root)),
            str(model_path.relative_to(paths.root)),
        ],
        checksums={
            str(oof_path.relative_to(paths.root)): sha256_file(oof_path),
            str(model_path.relative_to(paths.root)): sha256_file(model_path),
        },
        metrics={config.metric.name: rmse},
        metric_direction=config.metric.direction,
        wandb_run_id=logger.run_id,
    )

    record_path = run_dir / "experiment.json"
    atomic_write_model(run_dir / "manifest.json", manifest)
    try:
        logger.log({config.metric.name: rmse}, [oof_path, model_path])
        logger.finish()
    except TrackingError as error:
        manifest = manifest.model_copy(update={"wandb_run_id": logger.run_id})
        atomic_write_model(run_dir / "manifest.json", manifest)
        incomplete = ExperimentRecord(
            manifest=manifest,
            status="incomplete",
            failure=f"{type(error).__name__}: {error}",
        )
        atomic_write_model(record_path, incomplete)
        raise

    manifest = manifest.model_copy(update={"wandb_run_id": logger.run_id})
    atomic_write_model(run_dir / "manifest.json", manifest)
    complete = ExperimentRecord(manifest=manifest, status="complete", failure=None)
    atomic_write_model(record_path, complete)
    (paths.experiments / "latest").write_text(run_id + "\n", encoding="utf-8")
    return complete
