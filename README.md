# tadween-whisperx

A configurable ASR (automatic speech recognition) pipeline built on [tadween-core](https://github.com/AHedya/tadween-core), wrapping [whisperx](https://github.com/m-bain/whisperX) for transcription, diarization, and alignment.

## Pipeline

tadween-whisperx assembles a DAG of optional, swappable stages:

```
audio loader → diarization → transcription → alignment → normalization
```

Each stage can be enabled or disabled via configuration. Disabled stages are skipped and their dependents inherit their upstream dependencies automatically.

## Installation

Requires Python ≥ 3.11 and CUDA 12.8 (PyTorch).

```bash
uv sync              # runtime dependencies
uv sync --group test # add pytest
uv sync --group dev  # add jupyter/ipykernel
```

## Configuration

The CLI (`tadween-whisperx`) provides config management:

```bash
tadween-whisperx config init              # create user config from defaults
tadween-whisperx config show              # display current config (secrets redacted)
tadween-whisperx config show --reveal     # display with secrets visible
tadween-whisperx config reset             # reset to defaults

tadween-whisperx config repo json         # add a local JSON repo profile
tadween-whisperx config repo s3           # add an S3 repo profile
tadween-whisperx config repo list         # list profiles
tadween-whisperx config repo switch {NAME}  # switch active profile
tadween-whisperx config repo remove {NAME}  # remove a profile

tadween-whisperx config diarization       # configure diarization
tadween-whisperx config transcription     # configure transcription
tadween-whisperx config alignment         # configure alignment
tadween-whisperx config normalizer        # configure normalizer

# `tadweenx` is an alias to tadween-whisperx
tadweenx scan                           # uses config `input` section and print scan result
tadweenx scan local PATH_1 PATH_2 ...   # print scan result of given local input
tadweenx scan s3 ...                    # print scan result of s3 input
```

Config is loaded from `~/.config/tadween-whisperx/config.yaml`, falling back to bundled defaults. <br>

Task queue configuration is handled from `config.yaml` file.


### Validation rules

- At least one of diarization or transcription must be enabled.
- Alignment and normalizer require transcription.

## Architecture

Each pipeline component follows a **Handler / Policy / Schema** triad:

| File | Role |
|---|---|
| `handler.py` | Wraps a whisperx model. Implements `BaseHandler` with `warmup()`, `run()`, `shutdown()`. |
| `policy.py` | Controls lifecycle: interception, input resolution, caching, result persistence. Uses tadween-core decorators (`@inject_cache`, `@write_cache`, `@done_timing`). |
| `schema.py` | Pydantic input/output models. Heavy data uses `PicklePart` for lazy serialization. |

Components are declared as `WorkflowComponent` subclasses and assembled by `WorkflowBuilder` into a tadween-core `Workflow` DAG.

### Audio loading strategies

Three handlers are available for audio loading:

- **torchcodec** (default, and the fastest) — uses `torchcodec.AudioDecoder`
- **av** — uses PyAV (ffmpeg bindings)
- **ffmpeg_stream** — uses ffmpeg subprocess

### Normalizer

Custom post-processing that collapses repeated characters and words in transcribed speech using Unicode-aware regex patterns. Configurable via `allowed_chars`, `max_word_len`, and `allowed_words`.

## Testing

```bash
uv run pytest                   # all tests
uv run pytest tests/config.py   # config unit tests
uv run pytest -k "test_pattern" # by pattern
```

Tests cover config loading/saving/validation and CLI commands. No tests exist yet for handlers, policies, builder, or workflow execution.

## Status

This project is a work in progress. The following areas are incomplete:

- **`cli run`** subcommand — not yet implemented.
- **Diarization, alignment, normalizer** components — `add_to_workflow()` is stubbed.
- **Audio loader** component — contains a copy-paste bug (creates `TranscriptionHandler` instead of a loader handler).

## Gotchas

- Make sure your models do exist before firing the workflow. It's not catastrophic, but it's recommended to have the model downloaded instead of downloading them mid workflow execution.