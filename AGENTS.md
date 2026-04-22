# AGENTS.md

Guidance for AI coding agents working in `tadween-whisperx`.

## Project

tadween-whisperx is a **whisperx wrapper** and **tadween-core pipeline implementation**. It builds a configurable ASR DAG pipeline — audio loading → diarization → transcription → alignment → normalization — using tadween-core's orchestration primitives.

**Core library**: [AHedya/tadween-core](https://github.com/AHedya/tadween-core) (editable local dep at `../../core`).

## Commands

```bash
uv sync                          # install runtime deps
uv sync --group test             # install + test deps
uv sync --group dev              # install + dev deps (notebooks)

uv run pytest                    # run all tests
uv run pytest tests/config.py    # single file
uv run pytest -k "test_pattern"  # by pattern

ruff check .                     # lint
ruff check . --fix               # lint + auto-fix
ruff format .                    # format
ruff format --check .            # format check
```

CLI entry point: `tadween-whisperx` (Typer app). Subcommands: `config init`, `config show`, `config reset`, `config repo ...`, `config diarization`, `config transcription`, `config alignment`, `config normalizer`, `run`.

## Architecture

### Handler / Policy / Schema triad

Every pipeline component follows this pattern under `src/tadween_whisperx/components/<name>/`:

| File | Role |
|---|---|
| `handler.py` | Implements `tadween_core.handler.BaseHandler[InputT, OutputT]`. Holds model loading (`warmup`), execution (`run`), and cleanup (`shutdown`). |
| `policy.py` | Implements `tadween_core.stage.DefaultStagePolicy` (or uses `StagePolicyBuilder`). Handles `intercept`, `resolve_inputs`, `on_success`, etc. Uses decorators like `@inject_cache`, `@write_cache`, `@done_timing`. |
| `schema.py` | Pydantic `BaseModel` input/output types for the handler. Parts extend `tadween_core.types.artifact.part.PicklePart`. |

### WorkflowComponent + WorkflowBuilder

- Each component is a `WorkflowComponent` ABC (`components/component.py`) with `name`, `depends_on`, `is_enabled(config)`, and `add_to_workflow(config, wf)`.
- `WorkflowBuilder` (`builder.py`) collects components, determines which are enabled, resolves inherited dependencies for disabled parents, then adds + links stages in a tadween-core `Workflow` DAG.
- **Disabled components**: if a parent is disabled, `_resolve_active_dependencies` walks upward to find the nearest enabled ancestor. The DAG still flows correctly with optional stages.

### Scanner system

- `create_scanner(config)` dispatches to `LocalScanner` or `S3Scanner` based on `config.input.type`.
- `BaseScanner` produces `ScanResult(artifact_id, file_name, task_input)` where `task_input` is either `AudioLoaderInput` (local) or `S3DownloadInput` (S3).
- `SUPPORTED_AUDIO_EXTENSIONS` (`frozenset`) filters files: `.wav`, `.mp3`, `.m4a`, `.flac`, `.opus`.

### Artifact model

- `ArtifactRoot(RootModel)` — flat, primitive-only identity fields (currently empty).
- `MetaModel(BaseModel)` — eagerly loaded metadata (stage, path, timestamps).
- `DiarizationPart`, `TranscriptionPart`, `AlignmentPart` — lazy-loaded `PicklePart` subclasses (binary-serialized, loaded on demand from repo).
- `CacheSchema` is a `@dataclass(slots=True)`, **not** a Pydantic model. Used with `SimpleCache`.

### Config system

- `AppConfig` extends `pydantic_settings.BaseSettings`. Loads from `~/.config/tadween-whisperx/config.yaml` (via `platformdirs`), falls back to bundled `resources/config.yaml`.
- `RepoProfiles` manages named repo profiles (JSON local or S3) with an active selection — discriminated union on `type` field.
- `redact_secrets()` masks fields in `_SECRET_FIELDS` (`aws_secret_access_key`, `token`, `aws_session_token`).
- Model validators enforce: at least one of diarization/transcription must be enabled; alignment and normalizer require transcription.
### Import-time side effects

`src/tadween_whisperx/__init__.py` sets two env vars at import time:

- `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` — workaround for torch weights loading.
- `PYANNOTE_METRICS_ENABLED=0` — disables pyannote telemetry.

These apply globally as soon as the package is imported.

## WIP / Known Issues

- **`main.py`** — prototype script, not production code. Uses `LocalInputConfig` with `tests/data` path fallback.

## Testing

- Config tests (`tests/config.py`), CLI tests (`tests/cli/`), and scanner tests (`tests/test_scanner.py`). No tests for builder, handlers, policies, or workflow execution.
- CLI tests use `typer.testing.CliRunner`.
- `tests/cli/conftest.py` has an autouse `isolated_config` fixture that patches `USER_CONFIG_FILE` to a temp directory.
- `tests/conftest.py` provides `tmp_config_dir`, `default_config_data`, `fresh_config` fixtures.

## PyTorch / CUDA

Dependencies require `torch==2.8.0+cu128` and `torchaudio==2.8.0+cu128` from a custom PyTorch index (`pytorch-cu128`). Also pins `torchcodec==0.6.0`. This means `uv sync` needs the index configured in `pyproject.toml` (already set via `[tool.uv.index]`).

## Style

Same ruff config as tadween-core: rules `UP, E, F, W, I, B, C4, ARG001, F401`; ignores `E501, B008, W191, B904`; target Python 3.11; `keep-runtime-typing = true`.

**No comments in code** unless explicitly requested.