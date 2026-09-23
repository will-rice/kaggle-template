from pathlib import Path

import pandas as pd

from competition.data import load_sample_submission, load_test
from competition.model import MeanRegressor
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.records import atomic_write_model
from kaggle_template.submissions import (
    SubmissionProof,
    resolve_submission_identifier,
    validate_submission,
)


def predict_competition(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> tuple[Path, SubmissionProof]:
    latest_path = paths.experiments / "latest"
    if not latest_path.exists():
        raise FileNotFoundError("no trained experiment is recorded")

    run_id = latest_path.read_text(encoding="utf-8").strip()
    model_path = (paths.experiments / run_id / "model.json").resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"trained model artifact not found: {model_path}")
    model = MeanRegressor.load(model_path)
    test = load_test(paths.data)
    sample_path = paths.data / "sample_submission.csv"
    identifier = resolve_submission_identifier(
        list(pd.read_csv(sample_path, nrows=0).columns) if sample_path.exists() else [],
        config.identifier,
    )
    candidate = load_sample_submission(paths.data, identifier)
    prediction_columns = [column for column in candidate.columns if column != identifier]
    if len(prediction_columns) != 1:
        raise ValueError("baseline requires exactly one prediction column")

    candidate[prediction_columns[0]] = pd.Series(model.predict(len(test)))
    output = paths.submissions / f"{run_id}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(output, index=False)

    proof = validate_submission(
        output,
        sample_path,
        config.slug,
        config.identifier,
    )
    atomic_write_model(output.with_suffix(".validation.json"), proof)
    return output, proof
