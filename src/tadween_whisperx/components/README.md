# Components

Components are the implementation of [tadween-core](https://github.com/AHedya/tadween-core) stage contracts prepared with policy and schema definition, ready to be plugged into the workflow. Each stage of the ASR pipeline (Diarization, Transcription, etc.) is a "Component" that follows a strict **Triad Pattern** to separate model logic, orchestration, and data structure.

## The Triad Pattern

1. **`handler.py`**: Implementation of `BaseHandler`. Manages the model lifecycle, including loading into VRAM/RAM and executing inference.
2. **`policy.py`**: Implementation of `BaseStagePolicy`. Defines orchestration rules such as result resolution, skipping logic, and error handling.
3. **`schema.py`**: Pydantic models (extending `BaseModel`) defining the strict I/O interface for the stage.

## Pipeline Stages

The default pipeline is organized as a Directed Acyclic Graph (DAG) with the following stages:

### 1. Downloader
Our remote scanners: `http` and `S3`. This stage is optional depending on where are target files located.

### 2. Audio Loader
Decodes and resamples audio files. Optimized for high-speed processing using `torchcodec` loader. There are also other loaders: `ffmpeg-stream` which is the `whisperx` default (as of v3.8.4) ,and `av` loader.

### 3.1 Diarization
Speaker identification and segmentation. Wraps Pyannote models via WhisperX.

### 3.2.1 Transcription
Converts speech to text using Whisper models (via Faster-Whisper).

### 3.2.2 Alignment
Refines word-level timestamps using phoneme-based alignment.

### 3.2.3 Normalization
Post-processes the transcript removing potential ASR artifacts and hallucination. Those artifact appear as a repeating character or segment.

## Operational Reliability

Components leverage `tadween-core` primitives and custom throttling logic to ensure stability under heavy workloads:

### 1. Resource Guards
Execution is gated by resource capacity checks. By default, the pipeline is configured with a `cuda: 1` capacity, ensuring that only one GPU-intensive task (like Transcription or Diarization) runs at a time, preventing VRAM fragmentation and OOM errors.

### 2. Stashing Mechanism (Pressure Management)
To prevent system RAM exhaustion when scanning thousands of files, `tadween-whisperx` implements a **Stash Limit**.
- **The Problem**: If the scanner finds 1,000 files, the `Downloader` and `Audio Loader` might decode all of them into memory before the slower `Transcription` stage can keep up.
- **The Solution**: The `Audio Loader` is gated by a `stash_predicate`. It will block further decoding if the number of active files in the pipeline exceeds `loader.max_stashed_files` (default: 5).
- **Cleanup**: As soon as an artifact completes the entire pipeline (or fails), a `release_cache` callback is triggered via `on_artifact_done`. This releases the stash slot and evicts the heavy `audio_array` from the cache, allowing the next file to be loaded.
