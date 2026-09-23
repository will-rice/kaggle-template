from pathlib import Path

import pandas as pd

from competition.data import load_sample_submission, load_test
from competition.model import MeanRegressor
from kaggle_template.config import CompetitionConfig
from kaggle_template.paths import ProjectPaths
from kaggle_template.records import atomic_write_model
from kaggle_template.submissions import SubmissionProof, validate_submission


def predict_competition(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> tuple[Path, SubmissionProof]:
    latest_path = paths.experiments / "latest"
    if not latest_path.exists():
        raise FileNotFoundError("no trained experiment is recorded")

    run_id = latest_path.read_text(encoding="utf-8").strip()
    model = MeanRegressor.load(paths.experiments / run_id / "model.json")
    test = load_test(paths.data)
    sample = load_sample_submission(paths.data)
    candidate = sample.copy()
    prediction_columns = [column for column in candidate.columns if column != config.identifier]
    if len(prediction_columns) != 1:
        raise ValueError("baseline requires exactly one prediction column")

    candidate[prediction_columns[0]] = pd.Series(model.predict(len(test)))
    output = paths.submissions / f"{run_id}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(output, index=False)

    proof = validate_submission(
        output,
        paths.data / "sample_submission.csv",
        config.slug,
        config.identifier,
    )
    atomic_write_model(output.with_suffix(".validation.json"), proof)
    return output, proof
