# AGENTS.md

Guidance for AI coding agents working in `tadween-whisperx`.

## Project

tadween-whisperx is a **whisperx wrapper** and **tadween-core pipeline implementation**. It builds a configurable ASR DAG pipeline implementation (Audio Loading -> Diarization -> Transcription -> Alignment -> Normalization) using **tadween-core** orchestration primitives.

## Project Anatomy
- **`src/tadween_whisperx/`**: Root package.
    - **`components/`**: Domain logic. Each sub-folder contains the **Handler/Policy/Schema** triad.
    - **`scanners/`**: Input discovery logic (Local vs. S3).
    - **`cli/`**: Typer-based interface modules.
    - **`builder.py`**: DAG assembly and dependency resolution.
    - **`throttle.py`**: Execution control (concurrency, ref-counting, cache eviction).
    - **`artifact.py`**: Data models and part definitions.
    - **`config.py`**: Global configuration singleton and validation logic.

## Core Architecture
- **Triad Pattern**:
    - `handler.py`: Model lifecycle (warmup/run/shutdown).
    - `policy.py`: Stage orchestration (intercept/resolve/success).
    - `schema.py`: Pydantic I/O models.
- **Throttle**: Centralizes pressure management (stash logic) and resource capacity (`get_workflow_resources`).
- **Builder**: Assembles the `Workflow` DAG, handles fallback linking for disabled stages, and injects `StageContextConfig`.

## Commands
```bash
nox -t tests      # Run tests
nox -s lint       # Lint check
nox -s style      # Auto-fix lint & format (run before commit)
tadweenx run      # Execute pipeline
tadweenx scan     # Preview input discovery
```

## Critical Rules
1. **Separation of Concerns**: Keep `artifact.py` for data models only. Orchestration logic belongs in `throttle.py`.
2. **Context Efficiency**: Use `BaseCache` for heavy data and `throttle.free_audio_cache` for cleanup.
3. **Optional Repo**: Handle `repo=None` in policies for transient runs.
4. **Validation**: Call `config.validate()` manually in the builder or entry points; it is not automatic on instantiation.
5. **Deterministic IDs**: Always use `generate_artifact_id` from `scanners.base` when discovering new inputs to ensure unique, trackable, and repository-safe identifiers. If a higher-level system provides an ID, it should be passed via the `id_map` in the input configuration to override generation.

## Exploration Guide
- **Workflow assembly**: Check `builder.py` and `component.py`.
- **Throttling mechanics**: Check `throttle.py`.
- **Stage implementation**: Check `components/<name>/`.
- **Core Library**: `tadween-core` (External dependency).

## Development and Quality
Use nox for standard development tasks:
- `nox -t tests`: Run the full test suite.
- `nox -s lint`: Verify code quality and style.
- `nox -s style`: Automatically apply formatting and linting fixes.