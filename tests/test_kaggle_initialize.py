import subprocess
from pathlib import Path

import pytest

from kaggle_template.config import CompetitionConfig, load_config
from kaggle_template.initialize import InitState, initialize_competition
from kaggle_template.kaggle import (
    CompetitionMetadata,
    KaggleClient,
    KaggleCommandError,
    KaggleCredentialsError,
    KaggleRulesError,
    KaggleSlugError,
    SubmissionResult,
    SubprocessKaggleClient,
)
from kaggle_template.paths import ProjectPaths, resolve_project_paths


class FakeKaggleClient(KaggleClient):
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.authentications = 0
        self.metadata_requests = 0
        self.downloads = 0

    def authenticate(self) -> None:
        self.authentications += 1
        if self.failure:
            raise self.failure

    def metadata(self, slug: str) -> CompetitionMetadata:
        self.metadata_requests += 1
        return CompetitionMetadata(slug=slug, title="Synthetic Playground")

    def download(self, slug: str, destination: Path) -> None:
        self.downloads += 1
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "train.csv").write_text("id,target\n1,1.0\n", encoding="utf-8")

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult:
        raise AssertionError("initialization must not submit")


class EmptyDownloadClient(FakeKaggleClient):
    def download(self, slug: str, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def config() -> CompetitionConfig:
    return load_config(Path("configs/competition.toml"))


@pytest.fixture
def paths(tmp_path: Path, config: CompetitionConfig) -> ProjectPaths:
    return resolve_project_paths(tmp_path, config.paths)


def test_initialization_is_idempotent_for_same_slug(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    client = FakeKaggleClient()

    first = initialize_competition(config, paths, client)
    second = initialize_competition(config, paths, client)

    assert first.slug == second.slug == config.slug
    assert client.downloads == 1


def test_rejects_different_initialized_slug(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    state_path = paths.root / ".kaggle-template" / "init.json"
    state_path.parent.mkdir()
    state_path.write_text(
        InitState(
            slug="different-competition",
            title="Different",
            initialized_at="2026-09-23T12:00:00Z",
        ).model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="different-competition"):
        initialize_competition(config, paths, FakeKaggleClient())


def test_surfaces_kaggle_failure_without_state(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    client = FakeKaggleClient(KaggleCommandError("rules not accepted"))

    with pytest.raises(KaggleCommandError, match="rules not accepted"):
        initialize_competition(config, paths, client)

    assert not (paths.root / ".kaggle-template" / "init.json").exists()


def test_rejects_empty_download(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    with pytest.raises(FileNotFoundError, match="produced no data"):
        initialize_competition(config, paths, EmptyDownloadClient())


@pytest.mark.parametrize(
    ("data_path", "reports_path", "expected_match"),
    [
        ("root", "reports", "repository root"),
        ("src/downloads", "reports", "inside protected path"),
        ("artifacts", "artifacts/reports", "contains protected path"),
    ],
)
def test_rejects_unsafe_data_destination_before_kaggle_calls(
    config: CompetitionConfig,
    tmp_path: Path,
    data_path: str,
    reports_path: str,
    expected_match: str,
) -> None:
    root = tmp_path.resolve()
    client = FakeKaggleClient()
    paths = ProjectPaths(
        root=root,
        data=root if data_path == "root" else root / data_path,
        reports=root / reports_path,
        experiments=root / "artifacts/experiments",
        predictions=root / "artifacts/predictions",
        submissions=root / "artifacts/submissions",
    )

    with pytest.raises(ValueError, match=expected_match):
        initialize_competition(config, paths, client)

    assert client.authentications == 0
    assert client.metadata_requests == 0
    assert client.downloads == 0
    assert not (root / ".kaggle-template" / "init.json").exists()
    if data_path != "root":
        assert not paths.data.exists()


@pytest.mark.parametrize(
    ("stderr", "error_type"),
    [
        ("401 Unauthorized: invalid credentials", KaggleCredentialsError),
        ("You must accept the competition rules", KaggleRulesError),
        ("404 competition not found", KaggleSlugError),
        ("service unavailable", KaggleCommandError),
    ],
)
def test_subprocess_boundary_maps_explicit_errors(
    monkeypatch: pytest.MonkeyPatch,
    stderr: str,
    error_type: type[Exception],
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr=stderr,
        ),
    )

    with pytest.raises(error_type, match=stderr):
        SubprocessKaggleClient().authenticate()


def test_subprocess_boundary_rejects_unknown_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="ref,title\nother,Other Competition\n",
            stderr="",
        ),
    )

    with pytest.raises(KaggleSlugError, match="not present"):
        SubprocessKaggleClient().metadata("synthetic-playground")


def test_subprocess_boundary_rejects_malformed_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="wrong,header\nx,y\n",
            stderr="",
        ),
    )

    with pytest.raises(KaggleCommandError, match="malformed"):
        SubprocessKaggleClient().metadata("synthetic-playground")


def test_subprocess_boundary_rejects_empty_metadata_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        ),
    )

    with pytest.raises(KaggleCommandError, match="empty competition metadata"):
        SubprocessKaggleClient().metadata("synthetic-playground")


@pytest.mark.parametrize(
    "raised_error",
    [
        FileNotFoundError("kaggle"),
        OSError("temporary fork failure"),
    ],
)
def test_subprocess_boundary_wraps_run_failures_with_cause(
    monkeypatch: pytest.MonkeyPatch,
    raised_error: OSError,
) -> None:
    def raise_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        raise raised_error

    monkeypatch.setattr(subprocess, "run", raise_run)

    with pytest.raises(KaggleCommandError, match="Failed to execute Kaggle CLI") as exc_info:
        SubprocessKaggleClient().authenticate()

    assert exc_info.value.__cause__ is raised_error
