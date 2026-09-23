import subprocess
from pathlib import Path

SKILLS = {
    "competition-setup",
    "data-eda-audit",
    "validation-design",
    "baseline-creation",
    "experiment-review",
    "submission",
}


def test_all_six_skills_have_required_workflow_sections() -> None:
    actual = {path.parent.name for path in Path(".agents/skills").glob("*/SKILL.md")}
    assert actual == SKILLS
    for name in actual:
        content = Path(f".agents/skills/{name}/SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---\nname:")
        assert "## Preconditions" in content
        assert "## Workflow" in content
        assert "## Outputs" in content


def test_machine_artifacts_and_secrets_are_ignored() -> None:
    paths = [
        ".env",
        "kaggle.json",
        "data/train.csv",
        "checkpoints/model.ckpt",
        "artifacts/predictions/oof.csv",
        "artifacts/submissions/submission.csv",
        "artifacts/experiments/run/manifest.json",
        ".kaggle-template/init.json",
        "wandb/run-1/file",
    ]
    process = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input="\n".join(paths) + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 0
    assert set(process.stdout.splitlines()) == set(paths)


def test_readme_documents_boundary_and_explicit_submission() -> None:
    content = Path("README.md").read_text(encoding="utf-8")
    assert "src/kaggle_template" in content
    assert "src/competition" in content
    assert "kaggle-template submit" in content
    assert "--confirm" in content
    assert "never submits" in content.lower()
