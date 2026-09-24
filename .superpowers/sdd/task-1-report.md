# Task 1 Report: Optional NVIDIA Kaggle Skill Installation

## Outcome

Replaced the copied NVIDIA Kaggle skill with documentation for an optional,
canonical project-local installation. The Python package, bootstrap path, CI,
tests, and package installation do not execute Node, `npx`, or network setup.
All six repository-owned `.agents/skills` remain intact.

## RED

Added the repository contract first, including the relaxed core-skill subset
contract and optional installer documentation/isolation assertions.

Command:

```bash
uv run pytest \
  tests/test_repository_contract.py::test_all_six_skills_have_required_workflow_sections \
  tests/test_repository_contract.py::test_readme_documents_optional_nvidia_skill_installation \
  -v
```

Result: exit 1; `1 passed, 1 failed`. The six-skill contract passed. The
installer contract failed at the expected missing
`## Optional NVIDIA Kaggle Skill` README section while the vendored directory
still existed.

## GREEN

Removed the vendored skill and obsolete vendored-source test, removed its Ruff
exception, and added the specified README section and canonical command:

```text
npx skills@latest add nvidia/skills --skill nvidia-kaggle-skill --yes
```

Re-ran the focused command. Result: exit 0; `2 passed`.

## Files Changed

- Modified `README.md`
- Modified `pyproject.toml`
- Modified `tests/test_repository_contract.py`
- Ruff-formatted the code sample in
  `docs/superpowers/plans/2026-09-23-nvidia-kaggle-skill.md`
- Deleted all 42 tracked files under `.skills/nvidia-kaggle-skill/`
- Deleted `tests/test_nvidia_kaggle_skill.py`

The committed design spec was unchanged.

## Validation

Deletion and isolation checks:

```bash
test ! -e .skills/nvidia-kaggle-skill
test ! -e tests/test_nvidia_kaggle_skill.py
test "$(find .agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" -eq 6
! rg -n "nvidia-kaggle-skill|npx skills" src
! rg -n 'extend-exclude.*nvidia-kaggle' pyproject.toml
git diff --check
```

Result: all exited 0.

Complete validation:

- `uv run pytest` — passed, 139 tests
- `uv run ruff format --check .` — passed, 45 files already formatted
- `uv run ruff check .` — passed
- `uv run mypy` — passed, 29 source files
- `uv run pre-commit run --all-files` — all four hooks passed
- `uv build` — source distribution and one wheel built successfully
- isolated wheel `kaggle-template --help` — passed; four commands shown
- `git diff --check` — passed

The first complete Ruff/pre-commit attempt correctly found the multiline
command expression needed Ruff formatting and `SIM300` objected to the
requirements-prescribed subset expression. I formatted the expression and
added a targeted `# noqa: SIM300` so `SKILLS <= actual` remains explicit. The
complete validation was then rerun successfully.

No documented `npx` command was executed during implementation or validation.

## Self-review

- Confirmed TDD RED failed for the intended missing feature.
- Confirmed the optional installer command and maintenance commands match the
  brief exactly.
- Confirmed no Python bootstrap or package dependency invokes the installer.
- Confirmed `.agents/skills` still contains exactly the six core directories
  and has no diff.
- Confirmed the NVIDIA design spec has no diff.
- Confirmed 43 obsolete files were deleted: 42 vendored files plus one test.
- Confirmed the commit contains the required co-author trailer.
- Confirmed the worktree was clean after the commit.

## Commit

`3eeb66892f852569daf75351708cbe443127bfab` —
`refactor: install NVIDIA skill on demand`

## Concerns

Validation ran on CPython 3.13.13 while the project supports Python 3.12 and
newer. No functional or validation concerns remain.
