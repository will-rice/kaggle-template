from pathlib import Path

import pandas as pd


def load_train(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "train.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing training data: {path}")
    return pd.read_csv(path)


def load_test(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "test.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing test data: {path}")
    return pd.read_csv(path)


def load_sample_submission(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "sample_submission.csv"
    if not path.exists():
        raise FileNotFoundError(f"missing sample submission: {path}")
    return pd.read_csv(path)
