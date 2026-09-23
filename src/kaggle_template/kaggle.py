import csv
import re
import subprocess
import zipfile
from io import StringIO
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class KaggleError(RuntimeError):
    pass


class KaggleCredentialsError(KaggleError):
    pass


class KaggleRulesError(KaggleError):
    pass


class KaggleSlugError(KaggleError):
    pass


class KaggleCommandError(KaggleError):
    pass


class CompetitionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str


class SubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    status: str
    message: str


@runtime_checkable
class KaggleClient(Protocol):
    def authenticate(self) -> None: ...

    def metadata(self, slug: str) -> CompetitionMetadata: ...

    def download(self, slug: str, destination: Path) -> None: ...

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult: ...


_CREDENTIAL_PATTERN = re.compile(
    r"\bunauthori[sz]ed\b|\bcredentials?\b|kaggle\.json|\bKAGGLE_(?:KEY|USERNAME|API_TOKEN)\b",
    re.IGNORECASE,
)
_SLUG_PATTERN = re.compile(r"\b404\b|not found", re.IGNORECASE)


def _competition_slug(ref: str) -> str:
    return ref.strip().rstrip("/").rsplit("/", maxsplit=1)[-1]


def _display_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _parse_metadata(output: str, slug: str) -> CompetitionMetadata:
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        raise KaggleCommandError("Kaggle returned empty competition metadata output")
    if lines == ["No competitions found"]:
        raise KaggleSlugError(f"competition {slug!r} is not present in Kaggle results")

    header_index = next(
        (index for index, line in enumerate(lines) if line.split(",", maxsplit=1)[0] == "ref"),
        None,
    )
    if header_index is None:
        raise KaggleCommandError("Kaggle returned malformed competition metadata")

    for row in csv.DictReader(StringIO("\n".join(lines[header_index:]))):
        if _competition_slug(row.get("ref") or "") == slug:
            title = (row.get("title") or "").strip() or _display_title(slug)
            return CompetitionMetadata(slug=slug, title=title)

    raise KaggleSlugError(f"competition {slug!r} is not present in Kaggle results")


def _extract_archive(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.namelist():
                if not (root / member).resolve().is_relative_to(root):
                    raise KaggleCommandError(
                        f"refusing unsafe archive member {member!r} in {archive_path}"
                    )
            archive.extractall(root)
    except zipfile.BadZipFile as exc:
        raise KaggleCommandError(f"Kaggle download is not a valid zip: {archive_path}") from exc
    finally:
        archive_path.unlink(missing_ok=True)


class SubprocessKaggleClient:
    def _run(self, arguments: list[str]) -> str:
        command = ["kaggle", *arguments]
        try:
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            joined = " ".join(command)
            raise KaggleCommandError(
                f"Failed to execute Kaggle CLI ({joined}): "
                "the 'kaggle' executable was not found on PATH."
            ) from exc
        except OSError as exc:
            joined = " ".join(command)
            raise KaggleCommandError(
                f"Failed to execute Kaggle CLI ({joined}): "
                f"{exc}. Check local process limits and filesystem permissions."
            ) from exc

        if process.returncode == 0:
            return process.stdout

        detail = (process.stderr or process.stdout).strip()
        lowered = detail.lower()
        if _CREDENTIAL_PATTERN.search(detail):
            raise KaggleCredentialsError(detail)
        if "rules" in lowered:
            raise KaggleRulesError(detail)
        if _SLUG_PATTERN.search(detail):
            raise KaggleSlugError(detail)
        raise KaggleCommandError(detail or "Kaggle command failed without output")

    def authenticate(self) -> None:
        self._run(["competitions", "list", "--csv"])

    def metadata(self, slug: str) -> CompetitionMetadata:
        output = self._run(["competitions", "list", "--search", slug, "--csv"])
        return _parse_metadata(output, slug)

    def download(self, slug: str, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "competitions",
                "download",
                slug,
                "-p",
                str(destination),
                "--force",
            ]
        )
        archive_path = destination / f"{slug}.zip"
        if archive_path.exists():
            _extract_archive(archive_path, destination)

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult:
        output = self._run(
            [
                "competitions",
                "submit",
                slug,
                "-f",
                str(file),
                "-m",
                message,
            ]
        )
        detail = output.strip()
        lowered = detail.lower()
        if not detail:
            raise KaggleCommandError("Kaggle submit command succeeded without any output")
        if "could not submit to competition" in lowered or "could not find competition" in lowered:
            raise KaggleCommandError(detail)
        return SubmissionResult(ref=file.name, status="submitted", message=detail)
