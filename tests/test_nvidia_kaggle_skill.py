import ast
import hashlib
import re
from pathlib import Path

SKILL_ROOT = Path(".skills/nvidia-kaggle-skill")
MANIFEST_PATH = SKILL_ROOT / "SOURCE_MANIFEST.sha256"
REQUIRED_WORKFLOWS = {
    "SKILL.md",
    "research-brief.md",
    "writeups.md",
    "kernels.md",
    "kernel-setup.md",
    "submission.md",
    "evals/evals.json",
}
FORBIDDEN_PARTS = {"__pycache__", "data"}
FORBIDDEN_NAMES = {".env", "kaggle.json"}
EXPECTED_RELATIVE_REFERENCES = {
    "kernel-setup.md",
    "kernels.md",
    "research-brief.md",
    "scripts/<script>.py",
    "scripts/discussion_db_info.py",
    "scripts/discussion_ingest.py",
    "scripts/discussion_query.py",
    "scripts/discussion_read.py",
    "scripts/fetch_competition_info.py",
    "scripts/fetch_dataset_info.py",
    "scripts/upload_dataset.py",
    "submission.md",
    "writeups.md",
}
ALLOWED_NONEXISTENT_RELATIVE_REFERENCES = {"scripts/<script>.py"}


def _is_forbidden_file(path: Path) -> bool:
    return (
        bool(FORBIDDEN_PARTS & set(path.parts))
        or path.name in FORBIDDEN_NAMES
        or path.name.startswith(".env.")
        or path.suffix == ".pyc"
    )


def _extract_relative_references(skill_text: str) -> set[str]:
    return {match[2:] for match in re.findall(r"\./[A-Za-z0-9_./<>-]+", skill_text)}


def _authored_files() -> list[Path]:
    return sorted(
        path
        for path in SKILL_ROOT.rglob("*")
        if path.is_file() and path.name != MANIFEST_PATH.name and not _is_forbidden_file(path)
    )


def _parse_manifest() -> dict[str, str]:
    entries: dict[str, str] = {}
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    assert lines
    relative_paths: list[str] = []
    for line in lines:
        digest, relative_path = line.split("  ", maxsplit=1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest), line
        assert relative_path not in entries, relative_path
        relative_paths.append(relative_path)
        entries[relative_path] = digest
    assert relative_paths == sorted(relative_paths)
    return entries


def test_nvidia_kaggle_skill_is_self_contained() -> None:
    assert {
        path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*") if path.is_file()
    } >= REQUIRED_WORKFLOWS
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    relative_references = _extract_relative_references(skill)
    assert relative_references
    assert relative_references == EXPECTED_RELATIVE_REFERENCES
    for reference in relative_references:
        if reference not in ALLOWED_NONEXISTENT_RELATIVE_REFERENCES:
            assert (SKILL_ROOT / reference).exists(), reference


def test_nvidia_kaggle_skill_preserves_external_action_guards() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Require explicit user confirmation" in skill
    assert "competition submissions" in skill
    assert "dataset uploads" in skill
    assert "never print, log, or echo" in skill


def test_nvidia_kaggle_skill_contains_only_authored_files() -> None:
    files = [path for path in SKILL_ROOT.rglob("*") if path.is_file()]
    assert files
    assert not any(_is_forbidden_file(path) for path in files)


def test_nvidia_kaggle_skill_manifest_matches_authored_files() -> None:
    manifest_entries = _parse_manifest()
    authored_files = _authored_files()
    assert len(authored_files) == 41
    actual_entries = {
        path.relative_to(SKILL_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in authored_files
    }
    assert set(manifest_entries) == set(actual_entries)
    assert manifest_entries == actual_entries


def test_nvidia_kaggle_skill_python_sources_parse() -> None:
    python_files = [path for path in _authored_files() if path.suffix == ".py"]
    assert python_files
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
