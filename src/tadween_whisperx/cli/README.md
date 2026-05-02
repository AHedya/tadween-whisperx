# CLI Documentation

The `tadween-whisperx` CLI (aliased as `tadweenx`) is the primary interface for managing and executing the ASR pipeline. It is built using [Typer](https://typer.tiangolo.com/) and provides a hierarchical command structure for scanning inputs, running workflows, and managing configuration.

## Command Overview

- `tadweenx run`: Execute the full ASR pipeline on specified inputs.
- `tadweenx scan`: Preview and validate input files before processing.
- `tadweenx config`: Manage the system configuration (global and component-specific).

---

## 1. Running the Pipeline (`run`)

The `run` command executes the ASR workflow. It supports three input sources: `local`, `s3`, and `http`.

### Local Files
```bash
tadweenx run local [PATHS]... [OPTIONS]
```
- **Arguments**: One or more file or directory paths.
- **Options**:
    - `--include [GLOB]`: Pattern to include (e.g., `"*.mp3"`).
    - `--exclude [GLOB]`: Pattern to exclude.

### S3 Objects
```bash
tadweenx run s3 [BUCKET] --prefix [PREFIX] [OPTIONS]
```
- **Options**:
    - `--access-key`, `--secret-key`, `--region`: AWS credentials and region.
    - `--endpoint-url`: Custom S3 endpoint (e.g., MinIO).
    - `--download-path`: Where to store downloaded files.
    - `--keep/--no-keep`: Whether to retain files after processing (default: false).

### HTTP URLs
```bash
tadweenx run http [URLS]... [OPTIONS]
```
- **Options**:
    - `--timeout`: Download timeout in seconds.
    - `--keep/--no-keep`: Retain downloaded files (default: true).

---

## 2. Scanning Inputs (`scan`)

The `scan` command uses the same input logic as `run` but only performs discovery and validation. Use this to verify that your patterns and credentials correctly identify the target files.

```bash
# Example: Scan an S3 bucket for specific extensions
tadweenx scan s3 my-bucket --prefix raw/ --include "*.wav"
```

---

## 3. Configuration Management (`config`)

The system uses a persistent YAML configuration file (typically in `~/.config/tadween-whisperx/config.yaml`).

### Basic Commands
- `tadweenx config init`: Initialize a new configuration file with defaults.
- `tadweenx config show`: Display the current configuration.
- `tadweenx config reset`: Reset all settings to factory defaults.

### Component Configuration
You can configure specific stages of the pipeline directly from the CLI. This updates the persistent config file.

- **Loader**: `tadweenx config loader --type [torchcodec|av|ffmpeg_stream]`
- **Diarization**: `tadweenx config diarization --enabled/--disabled`
- **Transcription**: `tadweenx config transcription --model [base|small|medium|large-v3]`
- **Alignment**: `tadweenx config alignment --enabled/--disabled`
- **Normalizer**: `tadweenx config normalizer --enabled/--disabled`

### Repository Management
Manage where results are stored.
```bash
# Set the active repository profile
tadweenx config repo set-active [PROFILE_NAME]

# Add a local JSON repository
tadweenx config repo add-local my-repo /path/to/storage
```

---

## Input Patterns and Globbing

All input commands support multiple `--include` and `--exclude` flags. These use standard glob patterns:
- `*.mp3`: Matches all MP3 files in the current scope.
- `**/audio/*`: Matches all files in any `audio` subdirectory.

## Environment Variables

While most settings are in `config.yaml`, you can also use environment variables for sensitive data:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: Standard AWS credentials.
- `HF_TOKEN`: Huggingface token.
