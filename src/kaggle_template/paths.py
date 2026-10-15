from dataclasses import dataclass
from pathlib import Path

from kaggle_template.config import PathsConfig


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data: Path
    reports: Path
    experiments: Path
    predictions: Path
    submissions: Path


def _contained(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"path {value!r} must stay within repository {root}")
    return candidate


def resolve_project_paths(root: Path, config: PathsConfig) -> ProjectPaths:
    resolved_root = root.resolve()
    return ProjectPaths(
        root=resolved_root,
        data=_contained(resolved_root, config.data),
        reports=_contained(resolved_root, config.reports),
        experiments=_contained(resolved_root, config.experiments),
        predictions=_contained(resolved_root, config.predictions),
        submissions=_contained(resolved_root, config.submissions),
    )
