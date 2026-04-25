# tadween-whisperx

tadween-whisperx is a modular ASR (Automatic Speech Recognition) pipeline built on [tadween-core](https://github.com/AHedya/tadween-core), wrapping [whisperx](https://github.com/m-bain/whisperX) for transcription, diarization, and alignment.

## Project Overview

The application functions as a Directed Acyclic Graph (DAG) pipeline. It is designed to process audio files through a series of specialized stages, managing hardware resources and memory pressure automatically.

### The Pipeline Flow
1. **Audio Loader**: High-speed decoding and resampling (defaulting to torchcodec).
2. **Diarization**: Speaker identification and segmentation.
3. **Transcription**: Speech-to-text conversion.
4. **Alignment**: Precise word-level timestamping.
5. **Normalization**: Post-processing for text cleanliness and consistency.

## Project Anatomy

The codebase is organized into several distinct layers, making it easy to navigate based on your intent:

### 1. Components (`src/tadween_whisperx/components/`)
This is the core of the application. Each folder (e.g., `transcription`, `diarization`) follows a strict triad pattern:
*   `handler.py`: Contains the actual model loading and execution logic.
*   `policy.py`: Defines the orchestration rules, such as when to skip a stage or how to handle results.
*   `schema.py`: Defines the data structures for inputs and outputs.

### 2. Orchestration (`src/tadween_whisperx/`)
*   `builder.py`: The assembly line that connects components into a functional workflow.
*   `throttle.py`: The control plane managing concurrency, memory limits (stash logic), and hardware resources.
*   `artifact.py`: Pure data models representing the state of an audio file as it moves through the system.

### 3. Command Line Interface (`src/tadween_whisperx/cli/`)
The CLI is built with Typer and provides a human-friendly way to interact with the system.
*   `run/`: Logic for executing the full pipeline.
*   `scan/`: Utilities for previewing input files from local or S3 sources.
*   `config/`: Detailed management of the YAML configuration.

## Getting Started

### Installation
Requires Python 3.11 or higher and a CUDA-compatible environment.

```bash
uv sync                # Setup environment
tadweenx config init   # Generate initial configuration
```

### Common Commands
The CLI is accessible via the `tadweenx` alias.

```bash
# Preview compatible files in a directory
tadweenx scan local ./audio_files/

# Execute the pipeline on local files
tadweenx run local ./audio_files/

# View the current configuration
tadweenx config show
```

## Configuration and Persistence

The system uses a YAML configuration stored in `~/.config/tadween-whisperx/config.yaml`. It supports multiple "Repo Profiles," allowing you to save processing results to a local JSON structure or an S3 bucket.

## Development and Quality

We use nox for standard development tasks:
- `nox -t tests`: Run the full test suite.
- `nox -s lint`: Verify code quality and style.
- `nox -s style`: Automatically apply formatting and linting fixes.

For detailed technical guidance intended for AI agents or deep architectural dives, refer to AGENTS.md.
