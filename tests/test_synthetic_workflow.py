from pathlib import Path

from competition.predict import predict_competition
from competition.train import train_competition
from kaggle_template.config import CompetitionConfig
from kaggle_template.initialize import initialize_competition
from kaggle_template.kaggle import CompetitionMetadata, KaggleClient, SubmissionResult
from kaggle_template.paths import resolve_project_paths
from kaggle_template.records import ArtifactManifest, ExperimentRecord
from kaggle_template.submissions import assert_submission_unchanged


class SyntheticKaggleClient(KaggleClient):
    def __init__(self, source_data: Path) -> None:
        self.source_data = source_data
        self.authentications = 0
        self.metadata_requests = 0
        self.downloads = 0
        self.submissions = 0

    def authenticate(self) -> None:
        self.authentications += 1

    def metadata(self, slug: str) -> CompetitionMetadata:
        self.metadata_requests += 1
        return CompetitionMetadata(slug=slug, title="Synthetic Playground")

    def download(self, slug: str, destination: Path) -> None:
        self.downloads += 1
        destination.mkdir(parents=True, exist_ok=True)
        for source in self.source_data.glob("*.csv"):
            (destination / source.name).write_bytes(source.read_bytes())

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult:
        self.submissions += 1
        raise AssertionError("synthetic workflow must stop before external submission")


class LocalLogger:
    def __init__(self) -> None:
        self.logged_metrics: dict[str, float] | None = None
        self.logged_artifacts: list[Path] | None = None
        self.finished = False

    @property
    def run_id(self) -> str | None:
        return "synthetic-run"

    def log(self, metrics: dict[str, float], artifacts: list[Path]) -> None:
        self.logged_metrics = metrics
        self.logged_artifacts = artifacts
        assert metrics and artifacts

    def finish(self) -> None:
        self.finished = True


def test_synthetic_init_to_validated_submission(
    tmp_path: Path,
    synthetic_config: CompetitionConfig,
) -> None:
    source = Path(__file__).parent / "fixtures" / "synthetic"
    repository = tmp_path / "repository"
    repository.mkdir()
    paths = resolve_project_paths(repository, synthetic_config.paths)
    client = SyntheticKaggleClient(source)
    logger = LocalLogger()

    state = initialize_competition(synthetic_config, paths, client)
    record = train_competition(synthetic_config, paths, logger)
    candidate, proof = predict_competition(synthetic_config, paths)
    assert_submission_unchanged(candidate, proof)

    run_dir = paths.experiments / record.manifest.artifact_id
    manifest_path = run_dir / "manifest.json"
    experiment_path = run_dir / "experiment.json"
    oof_path = paths.root / record.manifest.outputs[0]
    model_path = paths.root / record.manifest.outputs[1]
    latest_path = paths.experiments / "latest"

    assert state.slug == synthetic_config.slug
    assert state.title == "Synthetic Playground"
    assert client.authentications == 1
    assert client.metadata_requests == 1
    assert client.downloads == 1
    assert client.submissions == 0

    assert manifest_path.exists()
    assert model_path.exists()
    assert oof_path.exists()
    assert latest_path.read_text(encoding="utf-8").strip() == record.manifest.artifact_id
    assert (
        ArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        == record.manifest
    )
    assert (
        ExperimentRecord.model_validate_json(experiment_path.read_text(encoding="utf-8")) == record
    )

    assert record.status == "complete"
    assert record.failure is None
    assert record.manifest.source_revision == "unversioned"
    assert record.manifest.dirty_worktree is True
    assert record.manifest.wandb_run_id == logger.run_id
    assert logger.logged_metrics is not None
    assert logger.logged_artifacts is not None
    assert logger.finished is True
    assert proof.row_count == 2
    assert proof.competition_slug == synthetic_config.slug
