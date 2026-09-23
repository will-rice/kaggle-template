# NVIDIA Kaggle Skill Vendoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor the complete NVIDIA Kaggle skill into `.skills/nvidia-kaggle-skill` as a portable, self-contained repository skill.

**Architecture:** The installed skill at `/Users/will/.agents/skills/nvidia-kaggle-skill` is the source of truth for one authored snapshot. Its complete documentation, evaluations, and Python scripts are copied into `.skills/nvidia-kaggle-skill`; generated caches, data, credentials, and bytecode are excluded. A repository-contract test verifies the entry point, required workflow files, internal relative references, and absence of generated files.

**Tech Stack:** Agent Skills Markdown, Python 3.12 or newer, pytest, Ruff, mypy, pre-commit, and Git.

## Global Constraints

- Copy the complete skill directory rather than using a symlink or a wrapper.
- The vendored copy is limited to authored source files.
- Generated caches, local databases, downloaded data, credentials, and Python bytecode are excluded.
- The existing six core workflows remain under `.agents/skills` unchanged.
- The NVIDIA skill is additive under `.skills`; it does not alter their names, behavior, or exact-count contract.
- All internal relative links and script paths must resolve inside the vendored directory.
- Preserve the skill's explicit confirmation requirements for submissions and dataset uploads.
- Do not integrate NVIDIA-specific behavior into the modality-agnostic framework package.
- Do not run Kaggle API, download, upload, or submission workflows as part of vendoring.

---

## File Map

| Path | Responsibility |
|---|---|
| `.skills/nvidia-kaggle-skill/SKILL.md` | Skill entry point, safety rules, dependencies, and workflow catalog. |
| `.skills/nvidia-kaggle-skill/research-brief.md` | Competition research-brief workflow. |
| `.skills/nvidia-kaggle-skill/writeups.md` | Writeup discovery and retrieval workflow. |
| `.skills/nvidia-kaggle-skill/kernels.md` | Kernel ingestion, query, reading, and scoring workflow. |
| `.skills/nvidia-kaggle-skill/kernel-setup.md` | Local kernel reproduction workflow. |
| `.skills/nvidia-kaggle-skill/submission.md` | Explicit Kaggle kernel-submission workflow. |
| `.skills/nvidia-kaggle-skill/evals/evals.json` | Skill evaluation cases. |
| `.skills/nvidia-kaggle-skill/scripts/` | Self-contained Python commands and their `kernels`/`discussions` support packages. |
| `tests/test_nvidia_kaggle_skill.py` | Vendored-skill completeness, reference, safety, and generated-file contract. |

### Task 1: Vendor and Validate the NVIDIA Kaggle Skill

**Files:**
- Create: `.skills/nvidia-kaggle-skill/SKILL.md`
- Create: `.skills/nvidia-kaggle-skill/research-brief.md`
- Create: `.skills/nvidia-kaggle-skill/writeups.md`
- Create: `.skills/nvidia-kaggle-skill/kernels.md`
- Create: `.skills/nvidia-kaggle-skill/kernel-setup.md`
- Create: `.skills/nvidia-kaggle-skill/submission.md`
- Create: `.skills/nvidia-kaggle-skill/evals/evals.json`
- Create: `.skills/nvidia-kaggle-skill/scripts/*.py`
- Create: `.skills/nvidia-kaggle-skill/scripts/kernels/*.py`
- Create: `.skills/nvidia-kaggle-skill/scripts/discussions/*.py`
- Create: `tests/test_nvidia_kaggle_skill.py`

**Interfaces:**
- Consumes: authored files under `/Users/will/.agents/skills/nvidia-kaggle-skill`.
- Produces: a self-contained skill rooted at `.skills/nvidia-kaggle-skill/SKILL.md`; every relative `./path` named by `SKILL.md` resolves beneath that root.

- [ ] **Step 1: Write the failing repository-contract test**

Create `tests/test_nvidia_kaggle_skill.py`:

```python
from pathlib import Path
import re


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
    assert REQUIRED_WORKFLOWS <= {
        path.relative_to(SKILL_ROOT).as_posix()
        for path in SKILL_ROOT.rglob("*")
        if path.is_file()
    }
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
```

- [ ] **Step 2: Run the focused test and verify the skill is absent**

Run: `uv run pytest tests/test_nvidia_kaggle_skill.py -v`

Expected: FAIL because `.skills/nvidia-kaggle-skill/SKILL.md` does not exist.

- [ ] **Step 3: Copy the authored skill snapshot**

Run:

```bash
mkdir -p .skills
rsync -a \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'data/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'kaggle.json' \
  /Users/will/.agents/skills/nvidia-kaggle-skill/ \
  .skills/nvidia-kaggle-skill/
```

Expected: `find .skills/nvidia-kaggle-skill -type f | wc -l` prints `41`, and no excluded path is present.

- [ ] **Step 4: Run focused and repository validation**

Run:

```bash
uv run pytest tests/test_nvidia_kaggle_skill.py -v
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pre-commit run --all-files
git diff --check
```

Expected:

- focused skill tests PASS
- the full suite PASS
- Ruff formatting and linting PASS
- mypy reports no issues
- every pre-commit hook reports `Passed`
- `git diff --check` emits no output

- [ ] **Step 5: Scan the vendored files for secrets**

Run the repository secret scanner against the raw contents of all non-ignored files under `.skills/nvidia-kaggle-skill`.

Expected: no credential, token, password, or private key findings.

- [ ] **Step 6: Commit the vendored skill**

```bash
git add .skills/nvidia-kaggle-skill tests/test_nvidia_kaggle_skill.py
git commit -m "feat: vendor NVIDIA Kaggle skill" \
  -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
```
