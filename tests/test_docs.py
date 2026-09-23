import ast
from pathlib import Path

import pytest


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


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            modules.add(node.module)
    return modules


def _imports_competition(path: Path) -> bool:
    return any(
        module == "competition" or module.startswith("competition.")
        for module in _imported_modules(path)
    )


def test_framework_never_imports_competition_modules() -> None:
    allowed = Path("src/kaggle_template/cli.py")
    offenders = [
        path
        for path in Path("src/kaggle_template").rglob("*.py")
        if path != allowed and _imports_competition(path)
    ]
    assert offenders == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from competition.train import train_competition\n", True),
        ("import competition\n", True),
        ("import competition.model as model\n", True),
        ("def load():\n    from competition import data\n", True),
        ("import competitions\nfrom kaggle_template import config\n", False),
        ("text = 'from competition import x'\n", False),
    ],
)
def test_framework_boundary_detects_every_competition_import_form(
    tmp_path: Path,
    source: str,
    expected: bool,
) -> None:
    module = tmp_path / "module.py"
    module.write_text(source, encoding="utf-8")
    assert _imports_competition(module) is expected


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
