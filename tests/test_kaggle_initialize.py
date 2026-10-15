import shutil
import subprocess
import zipfile
from collections.abc import Callable
from datetime import datetime
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
            initialized_at=datetime.fromisoformat("2026-09-23T12:00:00+00:00"),
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
    def raise_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise raised_error

    monkeypatch.setattr(subprocess, "run", raise_run)

    with pytest.raises(KaggleCommandError, match="Failed to execute Kaggle CLI") as exc_info:
        SubprocessKaggleClient().authenticate()

    assert exc_info.value.__cause__ is raised_error


def _completed(stdout: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    return run


REAL_HEADER = "ref,deadline,category,reward,teamCount,userHasEntered,userRank\n"


@pytest.mark.parametrize(
    "output",
    [
        REAL_HEADER
        + "https://www.kaggle.com/competitions/synthetic-playground-2,2030-01-01 00:00:00,"
        "Playground,Swag,10,False,\n"
        + "https://www.kaggle.com/competitions/synthetic-playground,2030-01-01 00:00:00,"
        "Playground,Swag,100,False,\n",
        REAL_HEADER + "synthetic-playground,2030-01-01 00:00:00,Playground,Swag,100,True,5\n",
        "Next Page Token = abc123\n"
        + REAL_HEADER
        + "https://www.kaggle.com/competitions/synthetic-playground/,2030-01-01 00:00:00,"
        "Playground,Swag,100,False,\n",
    ],
)
def test_subprocess_metadata_accepts_real_kaggle_csv_without_title(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(subprocess, "run", _completed(output))

    metadata = SubprocessKaggleClient().metadata("synthetic-playground")

    assert metadata == CompetitionMetadata(
        slug="synthetic-playground",
        title="Synthetic Playground",
    )


def test_subprocess_metadata_prefers_optional_title_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        _completed("ref,title\nhttps://www.kaggle.com/c/synthetic-playground,Synthetic Cup\n"),
    )

    metadata = SubprocessKaggleClient().metadata("synthetic-playground")

    assert metadata.title == "Synthetic Cup"


@pytest.mark.parametrize(
    "output",
    [
        REAL_HEADER
        + "https://www.kaggle.com/competitions/other-playground,2030-01-01,Playground,Swag,1,False,\n",
        REAL_HEADER
        + "https://www.kaggle.com/competitions/synthetic-playground-2,2030-01-01,Playground,"
        "Swag,1,False,\n",
        "No competitions found\n",
    ],
)
def test_subprocess_metadata_rejects_unknown_real_slug(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(subprocess, "run", _completed(output))

    with pytest.raises(KaggleSlugError, match="not present"):
        SubprocessKaggleClient().metadata("synthetic-playground")


@pytest.mark.parametrize(
    "output",
    [
        "deadline,category\n2030-01-01,Playground\n",
        "Next Page Token = abc\nwrong,header\nx,y\n",
    ],
)
def test_subprocess_metadata_rejects_malformed_real_output(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(subprocess, "run", _completed(output))

    with pytest.raises(KaggleCommandError, match="malformed"):
        SubprocessKaggleClient().metadata("synthetic-playground")


def test_subprocess_download_uses_supported_arguments_and_extracts_archive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        destination = Path(command[command.index("-p") + 1])
        with zipfile.ZipFile(destination / "synthetic-playground.zip", "w") as archive:
            archive.writestr("train.csv", "id,target\n1,1.0\n")
            archive.writestr("nested/test.csv", "id\n2\n")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    destination = tmp_path / "data"

    SubprocessKaggleClient().download("synthetic-playground", destination)

    assert commands == [
        [
            "kaggle",
            "competitions",
            "download",
            "synthetic-playground",
            "-p",
            str(destination),
            "--force",
        ]
    ]
    assert (destination / "train.csv").read_text(encoding="utf-8") == "id,target\n1,1.0\n"
    assert (destination / "nested" / "test.csv").exists()
    assert not (destination / "synthetic-playground.zip").exists()


def test_subprocess_download_rejects_archive_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        destination = Path(command[command.index("-p") + 1])
        with zipfile.ZipFile(destination / "synthetic-playground.zip", "w") as archive:
            archive.writestr("../escaped.csv", "x\n")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(KaggleCommandError, match="unsafe archive member"):
        SubprocessKaggleClient().download("synthetic-playground", tmp_path / "data")

    assert not (tmp_path / "escaped.csv").exists()
    assert not (tmp_path / "data" / "synthetic-playground.zip").exists()


def test_subprocess_submit_uses_supported_arguments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout="Successfully submitted\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    candidate = tmp_path / "run.csv"

    result = SubprocessKaggleClient().submit("synthetic-playground", candidate, "baseline")

    assert commands == [
        [
            "kaggle",
            "competitions",
            "submit",
            "synthetic-playground",
            "-f",
            str(candidate),
            "-m",
            "baseline",
        ]
    ]
    assert result == SubmissionResult(
        ref="run.csv", status="submitted", message="Successfully submitted"
    )


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (
            "Could not submit to competition. Please accept the rules first.\n",
            "Could not submit to competition",
        ),
        (
            "Could not find competition 'synthetic-playground'\n",
            "Could not find competition",
        ),
        ("", "Kaggle submit command succeeded without any output"),
    ],
)
def test_subprocess_submit_rejects_success_exit_without_successful_submission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stdout: str,
    expected: str,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=0, stdout=stdout, stderr=""
        ),
    )

    with pytest.raises(KaggleCommandError, match=expected):
        SubprocessKaggleClient().submit("synthetic-playground", tmp_path / "run.csv", "baseline")


@pytest.mark.parametrize(
    "stderr",
    [
        "error at row 401: service unavailable",
        "uploaded 14010 bytes before timeout",
    ],
)
def test_subprocess_boundary_does_not_treat_arbitrary_401_text_as_credentials(
    monkeypatch: pytest.MonkeyPatch,
    stderr: str,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr=stderr
        ),
    )

    with pytest.raises(KaggleCommandError) as exc_info:
        SubprocessKaggleClient().authenticate()

    assert not isinstance(exc_info.value, KaggleCredentialsError)


@pytest.mark.parametrize(
    "stderr",
    [
        "401 Client Error: Unauthorized for url: https://www.kaggle.com/api/v1/competitions/list",
        "Could not find kaggle.json. Make sure it's located in ~/.kaggle",
    ],
)
def test_subprocess_boundary_maps_real_unauthorized_errors(
    monkeypatch: pytest.MonkeyPatch,
    stderr: str,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr=stderr
        ),
    )

    with pytest.raises(KaggleCredentialsError):
        SubprocessKaggleClient().authenticate()


@pytest.mark.parametrize("data_state", ["missing", "empty"])
def test_same_slug_reinit_downloads_missing_data_and_keeps_state(
    config: CompetitionConfig,
    paths: ProjectPaths,
    data_state: str,
) -> None:
    first_client = FakeKaggleClient()
    first = initialize_competition(config, paths, first_client)
    state_path = paths.root / ".kaggle-template" / "init.json"
    original_state = state_path.read_text(encoding="utf-8")
    shutil.rmtree(paths.data)
    if data_state == "empty":
        paths.data.mkdir()

    client = FakeKaggleClient()
    second = initialize_competition(config, paths, client)

    assert second == first
    assert client.authentications == 1
    assert client.metadata_requests == 0
    assert client.downloads == 1
    assert (paths.data / "train.csv").exists()
    assert state_path.read_text(encoding="utf-8") == original_state


def test_same_slug_reinit_with_data_is_noop(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    initialize_competition(config, paths, FakeKaggleClient())
    client = FakeKaggleClient()

    initialize_competition(config, paths, client)

    assert client.authentications == 0
    assert client.metadata_requests == 0
    assert client.downloads == 0


def test_same_slug_reinit_rejects_empty_redownload(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    initialize_competition(config, paths, FakeKaggleClient())
    shutil.rmtree(paths.data)

    with pytest.raises(FileNotFoundError, match="produced no data"):
        initialize_competition(config, paths, EmptyDownloadClient())


def test_same_slug_reinit_ignores_leftover_zip_when_data_is_otherwise_missing(
    config: CompetitionConfig,
    paths: ProjectPaths,
) -> None:
    initialize_competition(config, paths, FakeKaggleClient())
    shutil.rmtree(paths.data)
    paths.data.mkdir()
    (paths.data / f"{config.slug}.zip").write_text("leftover", encoding="utf-8")
    client = FakeKaggleClient()

    initialize_competition(config, paths, client)

    assert client.authentications == 1
    assert client.metadata_requests == 0
    assert client.downloads == 1
    assert (paths.data / "train.csv").exists()
