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

REQUIRED_REPORT_TEMPLATES = {
    "baseline.md",
    "data-eda.md",
    "experiment-comparison.md",
    "validation.md",
}

REPORT_TEMPLATE_SECTIONS = {
    "baseline.md": [
        "## Approach",
        "## Validation Result",
        "## Local Artifact Identifier",
        "## W&B Run Identifier",
        "## Candidate Submission Validation",
        "## Limitations and Next Experiment",
    ],
    "data-eda.md": [
        "## Rules and Constraints",
        "## Train, Test, and Sample Submission",
        "## Target and Identifier",
        "## Missingness, Cardinality, and Duplicates",
        "## Leakage, Group, Time, and Modality Risks",
    ],
    "experiment-comparison.md": [
        "## Comparable Runs",
        "## Metric and Direction",
        "## Configuration and Artifact Differences",
        "## Selected Run",
    ],
    "validation.md": [
        "## Metric and Direction",
        "## Split Strategy",
        "## Seed, Folds, Groups, and Time Cutoffs",
        "## Leakage Controls",
        "## OOF Row and Prediction Contract",
        "## Expected Leaderboard Relationship",
    ],
}

README_SKILL_ORDER = [
    "1. competition setup",
    "2. data and EDA audit",
    "3. validation design",
    "4. baseline creation",
    "5. experiment review",
    "6. submission",
]


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


def test_reports_readme_documents_contract_and_policy() -> None:
    content = Path("reports/README.md").read_text(encoding="utf-8")

    assert "Commit human-readable decision records as `YYYY-MM-DD-<kind>.md`." in content
    assert (
        "Store exactly four reusable templates in `reports/templates/`: `data-eda.md`, "
        "`validation.md`, `baseline.md`, and `experiment-comparison.md`." in content
    )
    assert (
        "Every report names the competition slug, source revision, relevant artifact "
        "identifiers, author/date, evidence, decision, and unresolved risks." in content
    )
    assert (
        "Valid kinds are `data-eda`, `validation`, `baseline`, and "
        "`experiment-comparison`" in content
    )
    assert "Never commit datasets" in content
    assert "generated machine artifacts" in content


def test_report_templates_match_the_documented_contract() -> None:
    template_dir = Path("reports/templates")
    actual = {path.name for path in template_dir.glob("*.md")}
    assert actual == REQUIRED_REPORT_TEMPLATES

    for path in template_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        assert "**Competition:**" in content
        assert "**Date:**" in content
        assert "**Source revision:**" in content
        assert "**Author:**" in content
        assert "## Relevant Artifact Identifiers" in content
        assert "## Evidence" in content
        assert "## Decision" in content
        assert "## Unresolved Risks" in content
        for section in REPORT_TEMPLATE_SECTIONS[path.name]:
            assert section in content


def test_readme_documents_workflow_boundaries_commands_and_submission_rules() -> None:
    content = Path("README.md").read_text(encoding="utf-8")

    for step in (
        "1. Create a repository from this template.",
        "2. Install Python 3.12 or newer and `uv`.",
        "3. Set the competition slug and known fields in `configs/competition.toml`.",
        "4. Configure Kaggle credentials outside the repository and accept the competition rules.",
        "5. Run `uv sync --extra dev`.",
        "6. Run `uv run kaggle-template competition-init <slug>`.",
    ):
        assert step in content

    assert "`src/kaggle_template` is the stable framework" in content
    assert "`src/competition` is replaceable" in content

    positions = [content.index(step) for step in README_SKILL_ORDER]
    assert positions == sorted(positions)
    for step in README_SKILL_ORDER:
        assert step in content
        assert content.count(step) == 1

    for command in (
        "uv sync --extra dev",
        "uv run kaggle-template train",
        "uv run kaggle-template predict",
        "uv run kaggle-template submit artifacts/submissions/<run>.csv --message "
        '"<experiment and validation>" --confirm',
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run mypy",
        "uv run pytest",
        "uv run pre-commit run --all-files",
    ):
        assert command in content

    assert "local or remote Python 3.12+ machines" in content
    assert "The framework never submits during training or prediction." in content
    assert "Only `submit` can submit" in content
    assert "prediction columns must contain finite numeric values" in content
    assert "first sample column is treated as the identifier" in content
