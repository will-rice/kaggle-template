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


def _authored_files() -> list[Path]:
    return sorted(
        path
        for path in SKILL_ROOT.rglob("*")
        if path.is_file()
        and path.name != MANIFEST_PATH.name
        and not FORBIDDEN_PARTS & set(path.parts)
        and path.name not in FORBIDDEN_NAMES
        and path.suffix != ".pyc"
    )


def _parse_manifest() -> dict[str, str]:
    entries: dict[str, str] = {}
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        digest, relative_path = line.split("  ", maxsplit=1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest), line
        assert relative_path not in entries, relative_path
        entries[relative_path] = digest
    return entries


def test_nvidia_kaggle_skill_is_self_contained() -> None:
    assert {
        path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*") if path.is_file()
    } >= REQUIRED_WORKFLOWS
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    relative_references = set(
        re.findall(r"(?:^|\s)\./([A-Za-z0-9_./-]+)", skill, flags=re.MULTILINE)
    )
    assert relative_references
    for reference in relative_references:
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
    assert not any(FORBIDDEN_PARTS & set(path.parts) for path in files)
    assert not any(path.name in FORBIDDEN_NAMES or path.suffix == ".pyc" for path in files)


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
