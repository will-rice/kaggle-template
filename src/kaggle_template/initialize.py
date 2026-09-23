from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from kaggle_template.config import CompetitionConfig
from kaggle_template.kaggle import KaggleClient
from kaggle_template.paths import ProjectPaths
from kaggle_template.records import atomic_write_model


class InitState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    initialized_at: datetime


def _state_path(root: Path) -> Path:
    return root / ".kaggle-template" / "init.json"


def initialize_competition(
    config: CompetitionConfig,
    paths: ProjectPaths,
    client: KaggleClient,
) -> InitState:
    state_path = _state_path(paths.root)
    if state_path.exists():
        state = InitState.model_validate_json(state_path.read_text(encoding="utf-8"))
        if state.slug != config.slug:
            raise ValueError(
                f"repository is initialized for {state.slug!r}; "
                f"refusing destructive overwrite with {config.slug!r}"
            )
        return state

    client.authenticate()
    metadata = client.metadata(config.slug)
    client.download(config.slug, paths.data)
    if not paths.data.exists() or not any(paths.data.iterdir()):
        raise FileNotFoundError(f"Kaggle download produced no data in {paths.data}")

    state = InitState(
        slug=metadata.slug,
        title=metadata.title,
        initialized_at=datetime.now(UTC),
    )
    atomic_write_model(state_path, state)
    return state
