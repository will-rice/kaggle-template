# Final Whole-Branch Review — Fix Report

**Status:** DONE. All 13 findings remain addressed, plus the final-review follow-up for zero-exit Kaggle submit failures, failure-record persistence fallback, leftover zip safety, and missing-`git` provenance.
**Range:** `1cbe934..HEAD` (7 commits). The follow-up commit uses the required trailer `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`.

## Commits

| Commit | Summary | Findings |
|---|---|---|
| 376d9ef | fix: support real Kaggle CLI metadata, downloads, and re-init | 1, 3, 8 (+ real-CLI download/submit args) |
| 9721260 | fix: infer submission identifier from multi-column samples | 2 |
| 4ad1c3f | fix: harden submit gate and report CLI errors concisely | 4, 7, 10 |
| cefbdfb | fix: write latest pointer atomically and record honest provenance | 5, 9, 12, 13 |
| 152a092 | test: enforce network-free synthetic workflow and document submission contract | 6, 11 |
| 17b0ed5 | style: apply Ruff Markdown formatting to plan code blocks | pre-existing CI failure hidden by the cache |
| HEAD | fix: finalize final-review submit and safety edges | final Important follow-up + adjacent cheap minors |

## Changes by finding

1. **Real Kaggle init** (`kaggle.py`, `pyproject.toml`, `uv.lock`, `README.md`)
   - `_parse_metadata` handles real `competitions list --csv` output. It skips any preamble before the `ref,...` header (for example `Next Page Token = ...`) and does not require a `title` column.
   - A row matches when its `ref` is the bare slug or a URL/ref whose last path segment is the slug. Trailing `/` is tolerated. `slug-2` does not match `slug`.
   - The title comes from the optional `title` column if present; otherwise it is derived from the slug (`synthetic-playground` → `Synthetic Playground`).
   - Output of exactly `No competitions found` raises `KaggleSlugError`. Output with no `ref` header raises malformed `KaggleCommandError`. Empty output keeps the existing error.
   - Added runtime dependency `kaggle>=2.0,<3` (lock resolves 2.2.4). `uv sync` now provides the `kaggle` executable. The README bootstrap documents this and where credentials go.
   - **Extra defect found against installed CLI 2.2.4:** `kaggle competitions download ... --unzip` fails with `error: unrecognized arguments: --unzip`, so real init could never have worked. Download now runs `kaggle competitions download <slug> -p <dest> --force` and extracts `<slug>.zip` in Python with a zip-slip guard, then deletes the zip. Download and submit pass the competition as the documented positional argument instead of the hidden `-c`.
2. **Identifier absent** (`submissions.py`, `competition/predict.py`, `competition/data.py`)
   - New `resolve_submission_identifier(columns, identifier)`: returns the configured identifier, otherwise the first column of a multi-column sample, otherwise `None` (one-column samples are prediction-only).
   - `validate_submission` reads the identifier as a string using the resolved value.
   - The baseline predictor uses the same resolution and loads identifier columns as strings, so `007` stays `007`.
3. **Same-slug re-init** (`initialize.py`): if state exists and data is missing or empty, it re-authenticates and re-downloads without fetching metadata, checks the download is non-empty, and returns the existing state unchanged. If data is present, it is still a no-op.
4. **Failed submissions** (`cli.py`): on `KaggleError`, it atomically writes `SubmissionResult(ref=<file name>, status="failed", message="<ErrorType>: <detail>")` to `<candidate>.result.json` before printing the error and exiting 1. The ref is the local file name, the same value the success path uses. Successful results are still recorded.
5. **Provenance:** records `unversioned` when `git rev-parse` fails. The dirty sentinel was also renamed from `synthetic-fixture-dirty` to `status-unavailable`; it still counts as dirty.
6. **Network-free CI:** added dev dependency `pytest-socket>=0.7,<1` (0.8.1). The synthetic module has `pytestmark = pytest.mark.disable_socket` plus a test showing `socket.socket` raises `SocketBlockedError`. CI runs `uv run pytest tests/test_synthetic_workflow.py --disable-socket -v`, and a contract test asserts that command is in CI and the dependency is in `pyproject.toml`.
7. **Submit revalidation:** `_assert_submission_is_current` now:
   - checks checksums;
   - re-runs `validate_submission(candidate, sample, config.slug, config.identifier)`;
   - requires the proof's `candidate_sha256`, `sample_sha256`, `row_count` and `columns` to match the fresh result.

   All of this happens before the confirmation gate and before any external call.
8. **Credential classification:** errors map to credentials only for `unauthorized`/`unauthorised`, `credential(s)`, `kaggle.json`, or `KAGGLE_KEY|USERNAME|API_TOKEN`, each as a whole word. A bare `401` no longer counts. `404` also uses word boundaries now.
9. **Atomic `latest`:** new `records.atomic_write_text` writes a unique sibling temp file (`mkstemp` in the destination directory), fsyncs it, calls `os.replace`, and removes the temp file on any failure. `atomic_write_model` delegates to it, and `train.py` writes `latest` through it.
10. **CLI errors:**
    - Invalid TOML, Pydantic config errors (summarised as `loc: msg`) and path-containment `ValueError` become `Invalid value for '--config': ...` with exit 2 and no traceback.
    - `competition-init` reports `Initialization error:`, `train` reports `W&B error:` or `Error:`, and `predict` reports `Error:`, each with exit 1.
    - Proof errors were already `BadParameter`.
11. **Docs:** the README has a "Submission contract" paragraph: prediction columns must be finite numeric values; how identifier inference works; submit revalidation; result recording. The submission skill step mentions numeric predictions.
12. **Task 2 tests:** checksum is checked against the known SHA-256 of `abc` and shown to change when content changes. A complete record with a non-`None` failure is rejected. The atomic write round-trips with no leftover temp files.
13. **Boundary test:** an AST walk over `src/kaggle_template/**/*.py` (only `cli.py` is allowed) catches `import competition[...]` and `from competition[...] import`, including imports inside functions. It ignores `competitions` and string literals, and parametrized detector cases cover each form.

## RED/GREEN evidence

| Area | RED (tests before implementation) | GREEN |
|---|---|---|
| Kaggle/init (1, 3, 8, download/submit args) | `16 failed, 20 passed` in `tests/test_kaggle_initialize.py` | `36 passed` |
| Identifier inference (2) | `tests/test_submissions.py` collection `ImportError: resolve_submission_identifier`; `test_predict_infers_identifier...` `1 failed, 4 passed` | `101 passed` (full suite) |
| CLI (4, 7, 10) | `20 failed, 11 passed` in `tests/test_cli.py` | `31 passed` |
| Records/latest/provenance (5, 9, 12) | `tests/test_records.py` `ImportError: atomic_write_text`; `2 failed, 121 passed` (synthetic provenance, latest spy) | `131 passed` |
| Socket/docs (6, 11) | `ModuleNotFoundError: pytest_socket`; `2 failed, 128 passed` (CI contract, README contract) | `132 passed` |
| AST boundary (13) | Test-only strengthening: the old substring test missed `import competition`; the new parametrized detector cases prove both forms are caught. No production code changed, so there is no failing production test. | passes |

## Validation (final, at 17b0ed5)

```
$ uv lock --check                                   -> Resolved 79 packages in 3ms (exit 0)
$ uv run ruff format --check --no-cache .           -> 43 files already formatted (exit 0)
$ uv run ruff check --no-cache .                    -> All checks passed! (exit 0)
$ uv run mypy                                       -> Success: no issues found in 29 source files (exit 0)
$ WANDB_MODE=offline NO_PROXY='*' no_proxy='*' uv run pytest --cov=src --cov-report=term-missing
                                                    -> 132 passed in 1.10s; TOTAL 645 stmts, 26 miss, 96% (exit 0)
$ uv run pytest tests/test_synthetic_workflow.py --disable-socket -v -> 2 passed in 0.29s (exit 0)
$ uv run pytest tests/test_repository_contract.py::test_machine_artifacts_and_secrets_are_ignored -v -> 1 passed (exit 0)
$ uv run pre-commit run --all-files                 -> ruff check/ruff format/mypy/pytest Passed (exit 0)
$ uv run pre-commit run -a                          -> ruff check/ruff format/mypy/pytest Passed (exit 0)
$ git diff --check                                  -> (no output, exit 0)
$ uv run kaggle-template --help                     -> commands: competition-init, train, predict, submit (exit 0)
$ uv build                                          -> Successfully built dist/kaggle_template-0.1.0.tar.gz and -py3-none-any.whl (exit 0)
$ uv run --isolated --no-project --with dist/...whl kaggle-template --help            -> exit 0
$ uv run --isolated --no-project --with dist/...whl kaggle competitions list --help   -> exit 0 (wheel deps supply the kaggle executable)
$ uv run kaggle --version                           -> Kaggle CLI 2.2.4
```

The raw log is at `.superpowers/sdd/evidence/matrix.txt`. One wheel smoke check first showed exit 1 only because `| head` caused SIGPIPE under `pipefail`; rerun without the pipe, it exits 0.

## Pre-existing failure fixed without weakening checks

Ruff 0.16.8 formats Python code blocks in Markdown. At `HEAD` (`1cbe934`), `ruff format --check --no-cache .` failed on the plan file (`1 file would be reformatted`). Earlier runs passed only because of the local `.ruff_cache`; CI starts with no cache and would have failed. Commit 17b0ed5 applies `ruff format` to the plan. The change is layout-only inside code blocks (14+/32−, whitespace and line-wrapping), with no content or contract edits. The spec was not edited. Pre-commit pins ruff v0.13.2, which does not format Markdown, so that is why pre-commit passed.

## Self-review

- **Framework/replacement boundary:** the framework still imports competition code only from `cli.py`, and the AST test enforces this. The competition code uses only the public framework helpers `resolve_submission_identifier` and `atomic_write_text`.
- **Safety:** the explicit `--confirm` gate, checksum binding, slug check on the proof, different-slug refusal, protected data destinations, and no-submit in train/predict are all unchanged. Submit now also re-runs content validation.
- **Tests:** tests make no real network calls, use no credentials and make no submissions. The Kaggle subprocess is monkeypatched everywhere, and the synthetic module blocks sockets.
- **Title derivation:** it is deterministic and uses only the slug when `title` is absent.

## Concerns

1. A failed submit overwrites any earlier `<candidate>.result.json`, including a previous success from submitting the same file again. Keeping history would need per-attempt files, which is a contract change I did not make.
2. The Kaggle CLI output format (the `ref` URL shape, the `No competitions found` text, the zip name `<slug>.zip`, and the zero-exit submit failure phrases) is based on reading the installed kaggle 2.2.4 source plus the final-review feedback. It has not been checked against live Kaggle, which was intentionally not contacted. The version bound `<3` limits drift.
3. The plan file's historical snippets (for example `--unzip` and `unversioned-synthetic-fixture`) now differ from the code. The plan was deliberately not edited beyond the mechanical formatting.

## Follow-up addendum (HEAD)

### Additional fixes

- `SubprocessKaggleClient.submit()` now rejects exit-0 stdout that still says `Could not submit to competition...`, `Could not find competition...`, or says nothing at all. Those cases now raise `KaggleCommandError` instead of returning `SubmissionResult(status="submitted")`.
- `submit` now always surfaces the original Kaggle error first. If writing `<candidate>.result.json` for the failed attempt raises `OSError`, the CLI also prints `Also failed to record failed submission result: ...`, exits 1, and still avoids traceback/success-shaped output.
- Initialization now ignores leftover `.zip` archives when deciding whether downloaded data is usable, and archive cleanup happens even when Python-side extraction rejects the archive.
- Training provenance now treats a missing `git` executable the same as unavailable git metadata: `source_revision="unversioned"` and `dirty_worktree=True`.

### RED / GREEN evidence

- **RED:** `uv run pytest tests/test_kaggle_initialize.py -k 'submit_rejects_success_exit_without_successful_submission or archive_path_traversal or ignores_leftover_zip' tests/test_cli.py -k 'failure_recording_also_fails' tests/test_training.py -k 'git_is_unavailable' -q` → `1 failed, 78 deselected` (`FileNotFoundError: git` from `test_train_marks_provenance_unversioned_and_dirty_when_git_is_unavailable`).
- **GREEN:** `uv run pytest tests/test_kaggle_initialize.py::test_subprocess_submit_rejects_success_exit_without_successful_submission tests/test_kaggle_initialize.py::test_subprocess_download_rejects_archive_path_traversal tests/test_kaggle_initialize.py::test_same_slug_reinit_ignores_leftover_zip_when_data_is_otherwise_missing tests/test_cli.py::test_submit_surfaces_kaggle_errors_even_when_failure_recording_also_fails tests/test_training.py::test_train_marks_provenance_unversioned_and_dirty_when_git_is_unavailable -q` → `7 passed in 0.38s`.
- **Focused regression suite:** `uv run pytest tests/test_kaggle_initialize.py tests/test_cli.py tests/test_training.py -q` → `79 passed in 0.67s`.

### Validation evidence

```
$ uv run ruff format --check .
43 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy
Success: no issues found in 29 source files

$ WANDB_MODE=offline NO_PROXY='*' no_proxy='*' uv run pytest -q
138 passed in 0.71s

$ WANDB_MODE=offline NO_PROXY='*' no_proxy='*' uv run pytest --cov=src --cov-report=term-missing -q
138 passed in 1.00s
TOTAL 664 stmts, 27 miss, 96% coverage

$ uv run pytest tests/test_synthetic_workflow.py --disable-socket -q
2 passed in 0.32s

$ uv run pre-commit run -a
ruff check / ruff format / mypy / pytest Passed

$ uv build
Successfully built dist/kaggle_template-0.1.0.tar.gz
Successfully built dist/kaggle_template-0.1.0-py3-none-any.whl

$ git diff --check
(no output, exit 0)
```

## 2026-09-23 CI packaging smoke-test addendum

- Added a contract assertion in `tests/test_docs.py` that CI must include `uv build`, a wheel path capture via `set -- dist/kaggle_template-*.whl`, and an isolated installed-wheel `kaggle-template --help` smoke test.
- Updated `.github/workflows/ci.yml` to build the sdist and wheel with `uv build`, then run the console entry point from the built wheel via `uv run --isolated --no-project --with "$wheel" kaggle-template --help`.
- Preserved the existing `.superpowers/sdd` artifacts; no report cleanup/removal was performed.

Validation:

```text
$ WANDB_MODE=offline NO_PROXY='*' no_proxy='*' uv run pytest tests/test_docs.py::test_ci_and_precommit_cover_every_quality_gate -q
1 passed in 0.01s

$ uv build
Successfully built dist/kaggle_template-0.1.0.tar.gz
Successfully built dist/kaggle_template-0.1.0-py3-none-any.whl

$ set -- dist/kaggle_template-*.whl && [ -e "$1" ] && [ "$#" -eq 1 ] && wheel="$1" && uv run --isolated --no-project --with "$wheel" kaggle-template --help
Installed 57 packages in 131ms
Usage: kaggle-template [OPTIONS] COMMAND [ARGS]...

$ WANDB_MODE=offline NO_PROXY='*' no_proxy='*' uv run pytest -q
143 passed in 0.92s

$ uv run ruff format --check .
46 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy
Success: no issues found in 30 source files

$ uv run pre-commit run --all-files
ruff check / ruff format / mypy / pytest Passed

$ git diff --check
(no output, exit 0)
```
