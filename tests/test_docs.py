from pathlib import Path


def test_no_unfinished_markers_in_tracked_guidance() -> None:
    paths = [
        Path("README.md"),
        *Path(".agents/skills").glob("*/SKILL.md"),
        *Path("reports").glob("**/*.md"),
    ]
    forbidden = ("T" + "BD", "TO" + "DO", "FIX" + "ME")
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert not any(token in content for token in forbidden), path


def test_manifest_schema_and_model_use_version_one() -> None:
    schema = Path("schemas/artifact-manifest.schema.json").read_text(encoding="utf-8")
    model = Path("src/kaggle_template/records.py").read_text(encoding="utf-8")
    assert '"const": 1' in schema
    assert "Literal[1] = 1" in model


def test_framework_never_imports_competition_modules() -> None:
    allowed = Path("src/kaggle_template/cli.py")
    offenders = []
    for path in Path("src/kaggle_template").glob("*.py"):
        if path != allowed and "from competition" in path.read_text(encoding="utf-8"):
            offenders.append(path)
    assert offenders == []


def test_ci_and_precommit_cover_every_quality_gate() -> None:
    precommit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in ("ruff-check", "ruff-format", "mypy", "pytest"):
        assert required in precommit
    for command in (
        "uv sync --extra dev --locked",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run mypy",
        "uv run pytest",
        "uv run pre-commit run --all-files",
    ):
        assert command in workflow
