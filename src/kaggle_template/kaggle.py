import csv
import subprocess
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
        if "401" in detail or "credential" in lowered:
            raise KaggleCredentialsError(detail)
        if "rules" in lowered:
            raise KaggleRulesError(detail)
        if "404" in detail or "not found" in lowered:
            raise KaggleSlugError(detail)
        raise KaggleCommandError(detail or "Kaggle command failed without output")

    def authenticate(self) -> None:
        self._run(["competitions", "list", "--csv"])

    def metadata(self, slug: str) -> CompetitionMetadata:
        output = self._run(["competitions", "list", "--search", slug, "--csv"])
        reader = csv.DictReader(StringIO(output))
        if reader.fieldnames is None:
            raise KaggleCommandError("Kaggle returned empty competition metadata output")
        if not {"ref", "title"}.issubset(reader.fieldnames):
            raise KaggleCommandError("Kaggle returned malformed competition metadata")
        rows = list(reader)

        for row in rows:
            if row.get("ref") == slug and row.get("title"):
                return CompetitionMetadata(slug=slug, title=row["title"])

        raise KaggleSlugError(f"competition {slug!r} is not present in Kaggle results")

    def download(self, slug: str, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "competitions",
                "download",
                "-c",
                slug,
                "-p",
                str(destination),
                "--force",
                "--unzip",
            ]
        )

    def submit(self, slug: str, file: Path, message: str) -> SubmissionResult:
        output = self._run(
            [
                "competitions",
                "submit",
                "-c",
                slug,
                "-f",
                str(file),
                "-m",
                message,
            ]
        )
        return SubmissionResult(ref=file.name, status="submitted", message=output.strip())
