import json
from pathlib import Path


class MeanRegressor:
    def __init__(self, mean: float | None = None) -> None:
        self.mean = mean

    def fit(self, targets: list[float]) -> None:
        if not targets:
            raise ValueError("cannot fit MeanRegressor without targets")
        self.mean = sum(targets) / len(targets)

    def predict(self, row_count: int) -> list[float]:
        if self.mean is None:
            raise RuntimeError("MeanRegressor must be fitted before prediction")
        return [self.mean] * row_count

    def save(self, path: Path) -> None:
        if self.mean is None:
            raise RuntimeError("cannot save an unfitted MeanRegressor")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"mean": self.mean}) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "MeanRegressor":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(mean=float(payload["mean"]))
