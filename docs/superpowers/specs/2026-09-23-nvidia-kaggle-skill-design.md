# NVIDIA Kaggle Skill Installation Design

## Purpose

Offer NVIDIA's official `nvidia-kaggle-skill` as an optional, project-scoped
extension without vendoring its implementation into this GitHub template.
Repositories created from the template keep the six built-in competition
skills and can install or update NVIDIA's skill directly from its maintained
catalog when they need the additional research and Kaggle operations
workflows.

## Chosen Approach

Document NVIDIA's canonical non-interactive project installation command:

```bash
npx skills@latest add nvidia/skills --skill nvidia-kaggle-skill --yes
```

Installation is an explicit user action after creating a repository from the
template. It is not part of `competition-init`, `uv sync`, CI, or any Python
package entry point.

This approach is preferred because:

- `nvidia/skills` is NVIDIA's verified catalog and is updated from the
  maintained product repository.
- `skills@latest` satisfies NVIDIA's requirement for a current installer and
  avoids known linking problems in `skills` 1.5.15 and earlier.
- Project scope lets compatible agents discover the skill for this competition
  without making it available to unrelated repositories.
- The template no longer owns copied NVIDIA source, checksum manifests,
  third-party lint exceptions, or manual refresh work.

The installation intentionally follows the current NVIDIA catalog rather than
pinning a source commit. Users who require a frozen external dependency may
pin the installer or source separately, but the template does not claim that
the optional skill is reproducible or available offline.

## Repository Changes

- Remove `.skills/nvidia-kaggle-skill` and its source manifest.
- Remove vendored-source integrity tests and the Ruff exclusion that existed
  only for the copied source.
- Add an optional NVIDIA skill section to `README.md` with Node.js/npm and
  network prerequisites, the install command, `npx skills check`, and
  `npx skills update`.
- Preserve the six built-in `.agents/skills` as the stable template-provided
  core. Repository tests assert that those six names are present rather than
  forbidding additional project-installed skills.
- Do not add a wrapper script or a Node dependency manifest for one documented
  installer command.

The installer may create agent-specific links or project skill files according
to the current `skills` CLI and detected agents. Those generated installation
artifacts are external-tool output, not template-owned source.

## User Flow

1. Create a repository from the template and complete the normal Python
   bootstrap.
2. Optionally install Node.js/npm if they are not already available.
3. Run the documented `npx skills@latest add ... --yes` command from the
   repository root.
4. Reload or restart the active agent so it discovers the new skill.
5. Use `npx skills check` to inspect available updates and
   `npx skills update` to apply them deliberately.

Failure to install the optional skill does not affect configuration,
`competition-init`, training, prediction, submission, or the six built-in
skills. Installer, network, catalog, or permission failures remain visible to
the user; the template does not convert them into successful setup.

## Safety and Validation

- Never run the installer automatically during bootstrap, tests, CI, or
  package installation.
- Never run Kaggle API, download, upload, or submission workflows while
  installing the skill.
- Keep credentials outside the repository. Installing the skill does not
  require or inspect Kaggle credentials.
- Preserve the framework rule that submissions require explicit confirmation;
  the optional skill's own external-action safeguards apply when it is used.
- Add repository-contract tests for the exact documented installer command,
  optional prerequisites and update instructions, absence of the vendored
  directory, presence of all six core skills, and absence of NVIDIA-specific
  behavior from the Python bootstrap.
- Keep Ruff, mypy, pytest, pre-commit, package-build, and installed-CLI checks
  unchanged for repository-owned code.

Tests do not execute `npx` or access the network. They validate the template
contract, while NVIDIA and the `skills` CLI own installer behavior.

## Non-Goals

- No vendored NVIDIA source or checksum manifest.
- No automatic or mandatory NVIDIA skill installation.
- No global skill installation or modification of a user's home directory.
- No Node.js runtime dependency for the Python framework.
- No NVIDIA-specific framework APIs, CLI commands, or competition behavior.
- No guarantee that the optional upstream skill remains byte-identical across
  installations.
