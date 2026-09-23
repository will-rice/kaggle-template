import re
from pathlib import Path

SKILL_ROOT = Path(".skills/nvidia-kaggle-skill")
REQUIRED_WORKFLOWS = {
    "SKILL.md",
    "research-brief.md",
    "writeups.md",
    "kernels.md",
    "kernel-setup.md",
    "submission.md",
    "evals/evals.json",
}


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
    forbidden_parts = {"__pycache__", "data"}
    forbidden_names = {".env", "kaggle.json"}
    files = [path for path in SKILL_ROOT.rglob("*") if path.is_file()]
    assert files
    assert not any(forbidden_parts & set(path.parts) for path in files)
    assert not any(path.name in forbidden_names or path.suffix == ".pyc" for path in files)
