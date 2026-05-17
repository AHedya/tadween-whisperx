# Production & Containerization Guide

This document provides guidance for deploying **tadween-whisperx** across different environments, distinguishing between local usage and stateless production workers.

**Tadween-whisperx** follows a "build-once, configure-everywhere" approach. We do not provide a public pre-built Docker image due to community model licensing of the underlying diarization model (`pyannote/speaker-diarization-community-1`) and various workflow needs. Each user builds their own image, accepts model conditions, and bakes essential weights into the image to ensure production reliability and offline readiness.

---
## Building

By building your own image, you:
1. **Maintain Compliance**: You accept the user conditions for gated models directly on `Hugging Face`.
2. **Ensure Offline Readiness**: You can "bake" gigabytes of model weights into the image, making it suitable for air-gapped or restricted production environments.
3. **Optimize for Hardware**: You understand your workflow requirements, and your hardware availability.

### Prerequisites
- Docker with [BuildKit](https://docs.docker.com/build/buildkit/) enabled.
- NVIDIA GPU.

### Build Strategies

#### 1. Fast Build (Host Cache Bind)
Reuse your local HuggingFace cache to avoid re-downloading gigabytes of models:

```bash
docker build \
  --build-context hf-cache=$HOME/.cache/huggingface \
  -t tadweenx:latest \
  --target app .
```

#### 2. Clean Build (Token Injection)
Build from scratch by providing a `Hugging Face` token to download gated models:
```bash
HF_TOKEN=your_token_here docker build \
  --secret id=HF_TOKEN,env=HF_TOKEN \
  -t tadweenx:latest \
  --target app .
```

## Environment Use Cases

### 1. Docker for Local
If your goal is isolation and reproducibility. Though, you can mount volumes to bridge the host and the worker

**Stateless Worker**:
If you aim for batch processing to mimic *serverless*-like job but need to provide input, and receive results, you can use command such as the following:
```bash
docker run --rm -it --gpus all \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $HOME/.cache/huggingface:/app/models/hf \
  -v $(pwd)/results:/app/tadweenx-json-repo \
  -v $(pwd)/my_audio:/audio \
  tadweenx:latest --config /app/config.yaml run local /audio
```
Previous command follows app defaults (such as `app/tadweenx-json-repo`, the default path for the default repo if not set). Adjust params and vars according to your workflow config.



### 2. Production Worker (Serverless / Batch)
For true serverless environments, you'd typically need to override the image entrypoint and command to use serverless provider entrypoint/command.

**Tips:**
- Use `S3` for repo or `Fs` with custom retrieval logic if you care about round-trips
- Use `http` or `s3` for input.
- Use runtime config override instead of baking your *default config* into your image

## Shared Responsibility Model for Production

**tadween-whisperx** is designed to be highly reliable, but "production-grade" means different things depending on your environment. We have intentionally divided the responsibilities between the framework (us) and the environment owner (you). 

By delegating the hardest problems of distributed systems to the underlying engine (`tadween-core`), the application remains an un-opinionated, flexible wrapper. Here is how the responsibilities break down for serious production workloads:

### What the Framework Handles (Out-of-the-Box)
- **Graceful Shutdowns:** `tadween-core` automatically handles `SIGTERM` and `Ctrl+C`, ensuring tasks complete or abort cleanly, GPU memory is released, and temporary files are cleaned up.
- **Resource Coordination:** Using `tadween-core`'s `ResourceManager`, the application prevents physical resource starvation (like trying to run 5 models on a GPU with 24GB of VRAM) by managing logical and physical backpressure.
- **Containerization Strategy:** We provide the `Dockerfile` to bake models directly into the image, preventing S3/HuggingFace download timeouts during ephemeral scale-ups.

### What You Must Configure (Environment-Specific)

#### 1. Retry Logic & Fault Tolerance
Network failures, S3 timeouts, and API rate limits are inevitable in distributed systems. `tadween-core` has a robust, workflow-level retry mechanism built into its `WorkflowRoutingPolicy`.
- **Your Responsibility:** We do not hardcode which errors should be retried or how many times. You must configure the `RetryPolicy` (e.g., `retry_on=["S3DownloadError"]`, `max_retries=3`) programmatically or via your configuration overrides based on what is considered a transient error in your infrastructure.

#### 2. Idempotency (Avoiding Re-work)
In batch processing, if a worker crashes halfway through a queue, you don't want the next worker to re-process an audio file that was already transcribed.
- **Your Responsibility:** Idempotency is workflow-dependent. You can easily achieve this by hooking into the `Policy.intercept` event in the Triad pattern. Before a stage processes an audio file, your custom policy can query the Repository (`repo.exists(id)`); if the result exists, return `context.intercepted = True, action=InterceptionAction.short_circuit()` to skip the computation. It's worth mentioning that `InterceptionAction` can be configured to skip `on_done` or `on_success` if your environment doesn't need those events to fire if work is skipped.

#### 3. Observability, Logging, and Monitoring
Enterprise environments use different tools (Datadog, Prometheus, ELK). `tadween-whisperx` uses Python's standard logging with a strict hierarchical namespace (`tadween.stage`, `tadween.cache`).
- **Your Responsibility:** We provide the hooks; you plug in the metrics. `tadween-core` supports Dependency Injection for loggers (like `ProcessQueueLogger` for thread/process safety. Or `QueueLogger` for thread-safety only but lighter). You can also attach listeners directly to the `InMemoryBroker` to track queue sizes, throughput, and stage-level latency without modifying the core `whisperx` source code.

#### 4. OOM (Out-of-Memory) Protection
Audio processing is memory intensive. While we provide resource coordination, a single massive audio file could still spike VRAM usage.
- **Your Responsibility:** OOM constraints vary wildly based on your GPU and the specific Whisper/Pyannote model sizes you configured. We provide tips (e.g., keeping `"cuda"` workflow resources to `1`), but explicit handling or dynamic batch-sizing for CUDA OOM errors must be tailored to your specific hardware setup.

---

## Configuration Management

### Remote Configuration (URL-based)
In serverless environments where you cannot easily mount a `config.yaml`, you can host your configuration on a remote server (e.g., S3, GitHub Gist) and pass the URL directly to the application.

```bash
docker run --rm --gpus all \
tadweenx:latest --config https://your-server.com/config.yaml run s3
```

The application will download the config at runtime. If the download or parsing fails, it will either fallback to defaults or exit depending on the `TADWEENX_DEFAULT_FALLBACK` setting.


## Resource Management
Tips for mitigating the dreaded Out-of-Memory OOM errors

- Don't increase `loader.max_stashed_files` unless you know what you do.
- Don't increase `"cuda"` workflow resources to more than `1`

## Build Strategies
Refer to the `Dockerfile` for standard build instructions using `--build-context hf-cache` for fast builds or `--secret id=HF_TOKEN` for fresh downloads.
