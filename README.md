# tadween-whisperx

**tadween-whisperx** is a production-ready ASR (Automatic Speech Recognition) pipeline wrapper for [WhisperX](https://github.com/m-bain/whisperX), built on the [tadween-core](https://github.com/AHedya/tadween-core) orchestration library.

It provides a stable, resource-efficient implementation of the WhisperX toolset (Diarization, Transcription, Alignment) designed for processing heavy audio workloads on a single node with minimal overhead.

## Why use this?

While the underlying models (Whisper, Pyannote) determine the ASR accuracy, **tadween-whisperx** focuses on the **operational reliability** and **orchestration** of the pipeline:

- **Resource Efficiency**: Automatically manages resource pressure using [tadween-core](https://github.com/AHedya/tadween-core)'s coordination primitives.
- **Persistent Results**: Integrated support for local or S3-based repositories to store, track, and resume processing artifacts.
- **Production Monitoring**: Comprehensive logging and stage-level event tracking for pipeline observability.
- **Multi-Source Ingestion**: Built-in scanners for local files, S3 buckets, and direct HTTP URLs with platform-aware temp file management.
- **Modular DAG**: A fully configurable Directed Acyclic Graph pipeline:
```md
`Downloader`
    ↓
  `Loader` ─┬─> `Diarization`
            └─> `Transcription` ─┬─> `Alignment` 
                                 └─> `Normalization`
``` 

## Quick Start

### Installation
Requires Python 3.11+ and a CUDA-compatible GPU (recommended).

```bash
# Clone and install dependencies
git clone https://github.com/AHedya/tadween-whisperx
cd tadween-whisperx
uv sync

# Initialize configuration
uv run tadweenx config init
```

### Basic Usage

**Transcribe a local folder:**
```bash
uv run tadweenx run local ./my_audio_files/
```

**Transcribe from a URL:**
```bash
uv run tadweenx run http https://assets.hedya.dev/audio/en-1-000842-vlogbrothers1.opus
```

**Preview files before running:**
```bash
uv run tadweenx scan local ./audio/ --include "*.wav" --exclude "glob-to-exclude"
```

## Production & Docker

For production environments, **tadween-whisperx** is designed to run as a containerized service. Due to gated model licensing (e.g., Pyannote), we do not publish a public image; users are encouraged to build their own using the provided optimized `Dockerfile`.

See [**README.production.md**](README.production.md) for more details
## Production Readiness & Shared Responsibility

**tadween-whisperx** is a robust wrapper ready for many production use cases out-of-the-box. It leverages [tadween-core](https://github.com/AHedya/tadween-core) to handle complex orchestration, resource management, and graceful shutdowns. 

However, achieving "enterprise-grade" readiness for unmonitored, highly-concurrent environments (like serverless batch processing) is a **shared responsibility**. While the framework provides the hooks and architecture, developers must configure specific operational concerns—such as **Retry Logic**, **Idempotency**, and **Custom Observability**—based on their unique environment and workflow needs.

For deep technical details on how to extend the application for these serious use cases, refer to the following subpackage documentation:

- [**CLI Documentation**](src/tadween_whisperx/cli/README.md): Full command reference and examples.
- [**Production docs**](README.production.md): Detailed build strategies, shared responsibility guidelines, and production-ready examples. 
- [**Pipeline Components**](src/tadween_whisperx/components/README.md): Details on the Triad pattern and implementation of `tadween-core` contracts.
- [**Scanners & Input Sources**](src/tadween_whisperx/scanners/README.md): How local, S3, and HTTP sources are handled.
- [**Agent Guidance (AGENTS.md)**](AGENTS.md): Foundational mandates and architectural rules for AI contributors.

For more information about the underlying orchestration engine, see [**tadween-core**](https://github.com/AHedya/tadween-core).
