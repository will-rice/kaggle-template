# NVIDIA Kaggle Skill Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vendored NVIDIA Kaggle skill snapshot with an optional, documented, project-scoped installation from NVIDIA's verified catalog.

**Architecture:** The template continues to ship six repository-owned core skills and does not run Node.js or network operations during Python bootstrap. Users who want NVIDIA's additional workflows explicitly invoke the canonical `skills` CLI from the repository root; NVIDIA and the installer own the generated skill files and updates.

**Tech Stack:** Markdown, pytest repository-contract tests, Ruff, mypy, pre-commit, `npx skills@latest`

## Global Constraints

- Never run the installer automatically during bootstrap, tests, CI, or package installation.
- Never run Kaggle API, download, upload, or submission workflows while installing the skill.
- Keep credentials outside the repository. Installing the skill does not require or inspect Kaggle credentials.
- Preserve the framework rule that submissions require explicit confirmation; the optional skill's own external-action safeguards apply when it is used.
- Keep Ruff, mypy, pytest, pre-commit, package-build, and installed-CLI checks unchanged for repository-owned code.
- No vendored NVIDIA source or checksum manifest.
- No automatic or mandatory NVIDIA skill installation.
- No global skill installation or modification of a user's home directory.
- No Node.js runtime dependency for the Python framework.
- No NVIDIA-specific framework APIs, CLI commands, or competition behavior.
- No guarantee that the optional upstream skill remains byte-identical across installations.

---

## File Map

| Path | Action | Responsibility |
|---|---|---|
| `.skills/nvidia-kaggle-skill/**` | Delete | Remove the copied external implementation and `SOURCE_MANIFEST.sha256`. |
| `tests/test_nvidia_kaggle_skill.py` | Delete | Remove tests that validate a vendored source snapshot. |
| `tests/test_repository_contract.py` | Modify | Require the six core skills as a subset and enforce the optional installer documentation and bootstrap isolation. |
| `README.md` | Modify | Document prerequisites, canonical project install, reload behavior, and deliberate updates. |
| `pyproject.toml` | Modify | Remove the Ruff exclusion that existed only for vendored NVIDIA source. |
| `docs/superpowers/specs/2026-09-23-nvidia-kaggle-skill-design.md` | Preserve | Source of truth for this replacement design. |
| `docs/superpowers/plans/2026-09-23-nvidia-kaggle-skill.md` | Modify | Replace the obsolete vendoring plan with this installer plan. |

### Task 1: Replace Vendoring With Optional Project Installation

**Files:**
- Delete: `.skills/nvidia-kaggle-skill/**`
- Delete: `tests/test_nvidia_kaggle_skill.py`
- Modify: `tests/test_repository_contract.py`
- Modify: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: NVIDIA's verified catalog identifier `nvidia/skills`; skill name `nvidia-kaggle-skill`; the six core skill names in `SKILLS: set[str]`.
- Produces: documented command `npx skills@latest add nvidia/skills --skill nvidia-kaggle-skill --yes`; repository contract that `SKILLS <= actual`; no Python API, CLI command, dependency, or runtime side effect.

- [ ] **Step 1: Write the failing repository-contract tests**

In `tests/test_repository_contract.py`, change the core-skill assertion and add
the optional installer contract:

```python
def test_all_six_skills_have_required_workflow_sections() -> None:
    actual = {path.parent.name for path in Path(".agents/skills").glob("*/SKILL.md")}
    assert SKILLS <= actual
    for name in SKILLS:
        content = Path(f".agents/skills/{name}/SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---\nname:")
        assert "## Preconditions" in content
        assert "## Workflow" in content
        assert "## Outputs" in content


def test_readme_documents_optional_nvidia_skill_installation() -> None:
    content = Path("README.md").read_text(encoding="utf-8")
    command = "npx skills@latest add nvidia/skills --skill nvidia-kaggle-skill --yes"

    assert "## Optional NVIDIA Kaggle Skill" in content
    assert "Node.js and npm" in content
    assert command in content
    assert "npx skills check" in content
    assert "npx skills update" in content
    assert "not required for `competition-init`" in content
    assert not Path(".skills/nvidia-kaggle-skill").exists()

    bootstrap_source = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("src/kaggle_template").rglob("*.py")
    )
    assert "nvidia-kaggle-skill" not in bootstrap_source
    assert "npx skills" not in bootstrap_source
```

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
uv run pytest \
  tests/test_repository_contract.py::test_all_six_skills_have_required_workflow_sections \
  tests/test_repository_contract.py::test_readme_documents_optional_nvidia_skill_installation \
  -v
```

Expected: the core-skill test passes and the installer test fails because the
README section is absent and `.skills/nvidia-kaggle-skill` still exists.

- [ ] **Step 3: Remove vendored-source files and their obsolete test**

Run:

```bash
git rm -r .skills/nvidia-kaggle-skill
git rm tests/test_nvidia_kaggle_skill.py
```

Expected: all 42 vendored files, including `SOURCE_MANIFEST.sha256`, and the
vendored-source test are staged for deletion. The six directories under
`.agents/skills` are untouched.

- [ ] **Step 4: Remove the vendored-source Ruff exception**

In `pyproject.toml`, replace:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = [".skills/nvidia-kaggle-skill"]
```

with:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
```

Do not change any other Ruff, mypy, pytest, dependency, build, or script
configuration.

- [ ] **Step 5: Document the optional installer**

In `README.md`, insert this section after **Bootstrap** and before
**Boundaries**:

````markdown
## Optional NVIDIA Kaggle Skill

The six skills in `.agents/skills` are included with the template. For
additional NVIDIA-maintained Kaggle research, kernel, discussion, dataset, and
submission workflows, install the optional project-scoped skill from NVIDIA's
verified catalog:

```bash
npx skills@latest add nvidia/skills --skill nvidia-kaggle-skill --yes
```

This optional command requires Node.js and npm plus network access to GitHub.
It is not required for `competition-init`, training, prediction, or submission,
and the template never runs it automatically. Restart or reload the active
agent after installation so it discovers the new skill.

Use `npx skills check` to inspect upstream changes and `npx skills update` to
apply updates deliberately. Installing or updating the skill does not require
Kaggle credentials and must not run Kaggle downloads, uploads, or submissions.
````

- [ ] **Step 6: Run focused tests and capture GREEN**

Run:

```bash
uv run pytest \
  tests/test_repository_contract.py::test_all_six_skills_have_required_workflow_sections \
  tests/test_repository_contract.py::test_readme_documents_optional_nvidia_skill_installation \
  -v
```

Expected: `2 passed`.

- [ ] **Step 7: Verify deletion and bootstrap isolation**

Run:

```bash
test ! -e .skills/nvidia-kaggle-skill
test ! -e tests/test_nvidia_kaggle_skill.py
test "$(find .agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" -eq 6
! rg -n "nvidia-kaggle-skill|npx skills" src
! rg -n 'extend-exclude.*nvidia-kaggle' pyproject.toml
git diff --check
```

Expected: every command exits zero; the Python framework contains no NVIDIA
installer behavior, the six core skill directories remain, and no vendored
Ruff exception remains.

- [ ] **Step 8: Run complete validation**

Run:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pre-commit run --all-files
uv build
set -- dist/kaggle_template-*.whl
test "$#" -eq 1
wheel="$1"
uv run --isolated --no-project --with "$wheel" kaggle-template --help
git diff --check
```

Expected:

- full pytest suite passes with the vendored-source tests removed
- Ruff format and lint pass without an NVIDIA exclusion
- strict mypy and all pre-commit hooks pass
- source distribution and wheel build
- the installed wheel exposes `kaggle-template --help`
- `git diff --check` emits no output

Do not execute the documented `npx` installer in CI or validation.

- [ ] **Step 9: Commit the replacement**

Run:

```bash
git add -A \
  .skills/nvidia-kaggle-skill \
  tests/test_nvidia_kaggle_skill.py \
  tests/test_repository_contract.py \
  README.md \
  pyproject.toml \
  docs/superpowers/plans/2026-09-23-nvidia-kaggle-skill.md
git commit -m "refactor: install NVIDIA skill on demand" \
  -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
```

Expected: one commit removes vendored NVIDIA source, adds the opt-in installer
documentation and contract tests, and preserves the already committed design
spec unchanged.
