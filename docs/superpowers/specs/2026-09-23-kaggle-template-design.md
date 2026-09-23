# Kaggle Template Design

## Purpose

`kaggle-template` is a public, reusable GitHub template instantiated once per Kaggle competition. It is modality-agnostic from the first commit and supports the same Python package and command-line workflows on local and remote machines, including Kaggle CLI operations.

The template adopts the tooling conventions of `will-rice/ml-template`:

- Python 3.12 or newer, managed with `uv`
- Pydantic for typed configuration and records
- Lightning and PyTorch where they suit the competition, without requiring neural models
- Weights & Biases (W&B) tracking plus durable local artifacts
- pytest, Ruff, static type checking, pre-commit, and CI

Success means a user can create a repository from the template, run one bootstrap command, follow six agent skills, and produce a validated synthetic submission before adding competition-specific code.

## Design Decisions

The project uses a thin, modality-agnostic framework rather than a modality hierarchy or general plugin system. This keeps stable Kaggle workflow contracts separate from replaceable competition code without introducing registration, discovery, lifecycle, or compatibility machinery.

The framework owns:

- typed project configuration
- canonical project and artifact paths
- the Kaggle operations boundary
- experiment metadata and atomic local persistence
- out-of-fold prediction contracts
- submission generation and validation contracts
- command-line entry points

Competition-specific ingestion, feature engineering, validation logic, models, training, and prediction live under `src/competition`. Those modules are replaceable for each competition and may use tree-based, linear, nearest-neighbor, heuristic, ensemble, neural, or other appropriate solutions. Replacing competition modules must not require edits to framework internals as long as their public contracts remain satisfied.

Two broader alternatives are intentionally rejected:

1. **Modality plugins:** image, text, tabular, time-series, and multimodal plugin hierarchies would encode premature abstractions and constrain hybrid competitions.
2. **Unstructured scripts:** competition-only scripts would be quick initially but would duplicate safety checks, artifact conventions, experiment records, and Kaggle integration across repositories.

## Repository Components

### Framework package

`src/kaggle_template` contains stable, reusable infrastructure. Its public interfaces cover:

- loading and validating `configs/competition.toml`
- resolving canonical repository, data, report, experiment, prediction, and submission paths
- invoking Kaggle operations through one injectable CLI/API boundary
- reading and writing artifact manifests and experiment metadata
- validating out-of-fold predictions and submissions
- implementing the project CLI

The Kaggle boundary returns structured results and raises explicit, actionable errors. Competition modules and commands do not invoke the Kaggle executable or API directly.

### Competition package

`src/competition` contains the replaceable implementation:

| Module | Responsibility |
|---|---|
| `data.py` | Load competition data and construct model-ready inputs. |
| `validation.py` | Define folds or holdouts and expose validation metadata. |
| `model.py` | Define the model or algorithm and serialization boundary. |
| `train.py` | Fit models, calculate metrics, and emit out-of-fold predictions. |
| `predict.py` | Load trained artifacts and emit test predictions. |

These modules depend on framework contracts, not framework internals. The framework must not import modality-specific libraries.

### Configuration

`configs/competition.toml` is the single typed project configuration source. It contains:

- Kaggle competition slug
- optional target column and identifier column
- metric name and optimization direction (`minimize` or `maximize`)
- deterministic seeds and fold count
- W&B project name
- canonical data, report, experiment, prediction, and submission paths

Fields that are unknown at bootstrap remain explicitly absent rather than represented by placeholder strings. Commands that require an optional field validate its presence at use time and identify the missing key.

### Commands

The CLI exposes four primary commands:

- `competition-init <slug>` bootstraps and records competition state, verifies Kaggle access and rules acceptance, and downloads or locates competition files.
- `train` runs the competition training implementation and records metrics, folds, configuration, code provenance, and artifacts locally and in W&B.
- `predict` generates predictions and a candidate submission, then validates it against the sample submission.
- `submit` submits one already validated file through the Kaggle boundary.

Training never submits to Kaggle. Submission is a separate, explicit operation.

### Agent skills

`.agents/skills` provides six core workflows:

1. competition setup
2. data and EDA audit
3. validation design
4. baseline creation
5. experiment review
6. submission

Each skill produces or consumes explicit repository artifacts rather than relying only on chat history. Skills guide work within the stable framework and replaceable competition boundaries; they do not create alternate orchestration systems.

### Reports and manifests

Human-readable reports are versioned in the repository so assumptions and decisions remain reviewable. At minimum, the workflow produces dated or otherwise uniquely versioned data/EDA, validation, baseline, and experiment-comparison reports. Reports reference artifact identifiers rather than embedding large machine outputs.

Machine artifacts are ignored by Git. Each artifact set includes a manifest conforming to a tracked schema owned by the framework. The schema records:

- schema version and artifact identifier
- competition slug and creation timestamp
- command and resolved configuration
- source revision and dirty-worktree state
- seed and validation/fold identity where applicable
- input and output relative paths
- checksums for persisted outputs
- metrics with direction
- W&B run identifier when available

The tracked schema is versioned; generated manifests are local machine artifacts and are not committed by default.

### Prediction contracts

Out-of-fold predictions use an explicit framework contract containing the training-row identifier or stable row position, fold assignment, prediction value or values, and target when available. Validation requires exactly one prediction per expected training row, no duplicate identifiers, finite prediction values, and fold assignments consistent with the validation definition. This contract allows experiment comparison without prescribing a model family.

## End-to-End Flow

1. **Bootstrap:** `competition-init <slug>` validates configuration and Kaggle prerequisites, establishes canonical paths, obtains competition metadata and data, and records idempotent initialization state.
2. **Audit data and rules:** the data/EDA skill records dataset shape, columns, target and identifier assumptions, leakage risks, missingness, and competition rule constraints.
3. **Design validation:** the validation skill creates a versioned report explaining the split strategy, metric, direction, leakage controls, seed, and fold policy.
4. **Create a baseline:** the baseline skill implements the simplest credible competition-specific pipeline and exercises the full local workflow.
5. **Train and record:** `train` writes model outputs, out-of-fold predictions, and atomic local experiment metadata, then records the same run in W&B.
6. **Compare experiments:** the experiment-review skill compares validation results using the configured metric direction and references reproducible artifacts.
7. **Generate and validate:** `predict` creates a candidate submission and validates it exactly against the sample-submission contract.
8. **Submit explicitly:** `submit` displays the competition, file, message, and validation result, then proceeds only when the caller supplies the explicit confirmation flag.

No stage implicitly invokes the next destructive or external stage. In particular, training and prediction cannot submit a competition entry.

## Safety and Error Handling

Commands fail explicitly with actionable messages for:

- missing or invalid Kaggle credentials
- an unknown or malformed competition slug
- competition rules that have not been accepted
- missing competition data or required artifacts
- incomplete or invalid typed configuration
- incompatible manifest or prediction schema versions
- submission output that does not match the sample submission
- W&B initialization, logging, or finalization failures

Errors are not converted into successful-looking local records. A W&B failure is surfaced even when local persistence succeeds; the local record identifies the run as incomplete rather than silently treating it as fully recorded.

### Initialization safety

Initialization writes a durable state record containing the competition slug and relevant metadata. Re-running `competition-init` with the same slug is idempotent: it verifies existing state and completes only missing safe steps. Running it with a different slug fails before changing files and explains that a new repository instance is required. Initialization never destructively overwrites user-authored configuration, reports, or competition modules.

### Submission validation

Before a file can be submitted, validation enforces:

- exact row count equality with the sample submission
- exact column names and order
- identifier values aligned to the sample submission in the same order
- unique identifiers when an identifier column applies
- finite prediction values, with no `NaN` or positive/negative infinity

The validated artifact records the sample-submission checksum and candidate checksum. Any file change after validation invalidates that result and requires revalidation.

`submit` accepts only a currently validated artifact. Before invoking Kaggle it displays the competition slug, resolved file path, submission message, and validation result. It requires an explicit non-interactive confirmation flag; absence of the flag exits without submitting. Kaggle's structured response, including success or failure, is displayed and recorded.

### Secrets and generated data

Git ignores credentials, environment-secret files, competition datasets, checkpoints, generated predictions, generated submissions, generated manifests, and other machine-scale artifacts. No command copies secrets into tracked configuration or reports.

### Atomic experiment metadata

Local experiment metadata is written to a temporary file in the destination directory, flushed, and atomically renamed only after validation. Interrupted writes cannot replace the last valid record with a partial document. Artifact checksums are calculated before the record is finalized.

## Testing Strategy

Unit tests cover:

- configuration defaults, optional fields, and invalid values
- canonical path resolution and repository containment
- manifest schema validation and version handling
- metric-direction comparisons
- out-of-fold prediction invariants
- every submission validation rule
- initialization idempotency and different-slug rejection
- atomic experiment-record writes

Kaggle integration is tested behind a fake CLI/API boundary and temporary directories. CI never requires real Kaggle credentials and never performs a real download or submission. Boundary tests cover success, malformed responses, missing credentials, unaccepted rules, invalid slugs, command failures, and submission result recording.

A synthetic competition fixture exercises the complete supported path: initialize state, load synthetic train/test/sample-submission data, produce folds, train a deterministic baseline, write valid out-of-fold predictions and experiment metadata, generate predictions, and produce a validated submission. It stops before external submission.

Pre-commit and CI run formatting checks, linting, static type checking, tests, and documentation checks. CI also verifies ignored artifact classes and ensures the synthetic workflow does not access the network.

## Definition of Done

The template is complete when a user can:

- create a repository from the GitHub template
- run one bootstrap command for a competition
- use all six agent skills in the documented sequence
- run the synthetic fixture from initialization through a validated submission
- replace competition ingestion, validation, model, training, and prediction code without editing framework internals
- run the same package commands locally and on a remote Python environment
- inspect local experiment artifacts and corresponding W&B records

The repository must also demonstrate that unsafe states fail explicitly and that no training or prediction command can submit automatically.

## Non-Goals

- No modality plugin hierarchy or plugin discovery framework
- No hosted training or workflow orchestration service
- No automatic Kaggle competition submission
- No generalized feature store or model registry
- No committing competition datasets, credentials, secrets, checkpoints, predictions, submissions, or generated manifests
- No requirement that competition solutions use Lightning, PyTorch, or neural networks
