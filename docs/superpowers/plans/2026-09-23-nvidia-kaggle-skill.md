# NVIDIA Kaggle Skill Vendoring Implementation Plan

**Goal:** Preserve one exact authored NVIDIA Kaggle skill snapshot under `.skills/nvidia-kaggle-skill` without rewriting external source to satisfy repository Ruff rules.

**Architecture:** `/Users/will/.agents/skills/nvidia-kaggle-skill` is the sole source of truth. Every authored file is restored byte-for-byte into `.skills/nvidia-kaggle-skill`, excluding only caches, `data`, env or credential files, and bytecode. `.skills/nvidia-kaggle-skill/SOURCE_MANIFEST.sha256` records deterministic SHA-256 hashes for all 41 authored files and repository tests enforce exact membership, exact hashes, relative-reference completeness, and Python syntax parsing without importing Kaggle workflows.

**Quality policy:** Repository-owned code and documentation continue to pass strict Ruff, mypy, pytest, and pre-commit checks. Ruff excludes only `.skills/nvidia-kaggle-skill`; mypy remains scoped to `src` and `tests`. The vendored external snapshot is validated by manifest, syntax, reference, secret, compile, and direct source-comparison checks instead of source rewriting.

## Global Constraints

- Keep the six existing `.agents/skills` directories unchanged.
- Do not integrate NVIDIA-specific behavior into `src/` or the framework.
- Do not weaken mypy or repository-owned Ruff coverage.
- Do not run Kaggle network, submission, dataset-upload, or kernel-execution workflows.
- Preserve the skill's explicit confirmation and secret-handling guidance exactly as authored.

## File Map

| Path | Responsibility |
|---|---|
| `.skills/nvidia-kaggle-skill/**` | Exact authored NVIDIA snapshot copied from `/Users/will/.agents/skills/nvidia-kaggle-skill`, excluding caches/data/env/credential files/bytecode. |
| `.skills/nvidia-kaggle-skill/SOURCE_MANIFEST.sha256` | Sorted SHA-256 manifest for every authored vendored file except the manifest itself. |
| `tests/test_nvidia_kaggle_skill.py` | Exact snapshot integrity, reference, authored-file exclusion, and syntax checks. |
| `pyproject.toml` | Ruff exclusion narrowed to `.skills/nvidia-kaggle-skill` only. |
| `docs/superpowers/specs/2026-09-23-nvidia-kaggle-skill-design.md` | Records the exact-snapshot vendoring policy. |
| `docs/superpowers/plans/2026-09-23-nvidia-kaggle-skill.md` | Records implementation steps and validation commands for the exact-snapshot policy. |
| `.superpowers/sdd/nvidia-skill-task-1-report.md` | RED/GREEN evidence plus exact source-comparison results. |

## Execution Steps

- [ ] **Step 1: Write failing integrity tests first**

Update `tests/test_nvidia_kaggle_skill.py` so the focused test suite requires:

- required workflow files and internal `./...` references from `SKILL.md`
- absence of `__pycache__`, `data`, `.env`, `kaggle.json`, and `.pyc`
- exact `SOURCE_MANIFEST.sha256` membership and hashes for all 41 authored vendored files
- successful `ast.parse` of every vendored `.py` file without importing or executing them

- [ ] **Step 2: Capture RED evidence**

Run:

```bash
uv run pytest tests/test_nvidia_kaggle_skill.py -v
```

Expected: FAIL until `SOURCE_MANIFEST.sha256` exists and matches the vendored files.

- [ ] **Step 3: Restore the authored snapshot exactly**

Run:

```bash
rm -rf .skills/nvidia-kaggle-skill
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

Expected: the 41 authored files match the source snapshot byte-for-byte.

- [ ] **Step 4: Generate the deterministic manifest**

Create `.skills/nvidia-kaggle-skill/SOURCE_MANIFEST.sha256` with one sorted line per authored file:

```text
<64 lowercase hex chars><two spaces><relative posix path>
```

The manifest excludes itself and covers all 41 authored vendored files.

- [ ] **Step 5: Narrow Ruff exclusion without changing other scopes**

Update `pyproject.toml` so:

- `tool.ruff.extend-exclude = [".skills/nvidia-kaggle-skill"]`
- no exclusion remains for `docs/superpowers/plans/*.md`
- `tool.mypy.files` stays exactly `["src", "tests"]`

- [ ] **Step 6: Validate the restored snapshot and the repository**

Run:

```bash
uv run pytest tests/test_nvidia_kaggle_skill.py -v
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pre-commit run --all-files
python3 - <<'PY'
from pathlib import Path
for path in Path(".skills/nvidia-kaggle-skill").rglob("*.py"):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("compiled vendored python sources in-memory")
PY
git diff --check
```

Expected:

- focused vendored-skill tests PASS
- full pytest suite PASS
- Ruff format and lint PASS for repository-owned files
- mypy PASS with unchanged scope
- pre-commit PASS
- vendored Python sources compile in memory without writing bytecode
- `git diff --check` emits no output

- [ ] **Step 7: Validate snapshot fidelity and secrets**

Run:

```bash
diff -qr \
  --exclude 'SOURCE_MANIFEST.sha256' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'data' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'kaggle.json' \
  /Users/will/.agents/skills/nvidia-kaggle-skill \
  .skills/nvidia-kaggle-skill
rg -n "(KAGGLE_API_TOKEN|kaggle\\.json|Authorization|api[_-]?key|secret|token|password|private[ _-]?key|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{20,})" \
  .skills/nvidia-kaggle-skill -g '*.{md,py,json}'
git diff -- .agents/skills
```

Expected:

- `diff -qr` reports no differences between source and vendored authored files
- secret scan shows no committed secret material
- `.agents/skills` diff is empty

- [ ] **Step 8: Update evidence and commit**

Append RED/GREEN evidence and exact source-comparison results to `.superpowers/sdd/nvidia-skill-task-1-report.md`, then commit:

```bash
git add .skills/nvidia-kaggle-skill/SOURCE_MANIFEST.sha256 \
  .skills/nvidia-kaggle-skill \
  tests/test_nvidia_kaggle_skill.py \
  pyproject.toml \
  docs/superpowers/specs/2026-09-23-nvidia-kaggle-skill-design.md \
  docs/superpowers/plans/2026-09-23-nvidia-kaggle-skill.md \
  .superpowers/sdd/nvidia-skill-task-1-report.md
git commit -m "fix: restore exact NVIDIA skill snapshot" \
  -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
```
