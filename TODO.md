# TODO List

Enhancement and priority guide for `tadween-whisperx`.

## Testing & Validation
- [x] **Unit Tests for Builder**: Test `WorkflowBuilder` to ensure DAG integrity when various components are disabled.
- [x] **Integration Tests**: Create an end-to-end test suite using a small sample audio file to verify the pipeline flow.
- [ ] **Policy Tests**: Test individual stage policies.

## Observability & UI
- [ ] **CLI Progress Tracking**: Re-integrate and complete the `ProgressUIListener` using `rich.live` to show real-time stage progress.
- [x] **Stage-Specific Metrics**: Log and display processing speed for transcription and diarization.
- [x] **Detailed Logging**: Add more granular logging in `tadween-whisperx`.

## Stability & Resiliency
- [ ] **OOM Protection**: Implement explicit handling for CUDA Out-of-Memory errors to prevent the entire pipeline from crashing.
- [ ] **Retry Logic**: Add retry decorators to Policies for transient failures (especially for S3 downloads and model inference)
- [ ] **Graceful Shutdown**: Ensure `wf.close()` and `scanner.close()` handle interrupts (Ctrl+C) cleanly, releasing GPU memory and deleting temp files.
- [ ] **Idempotency**: Add `Idempotency` feature to app config. The application queries the repo if the result to produce already exists or not.

## DX & Features
- [x] **Scanner pattern**: Add matching patterns for exclusion or strict include for scanners.
- [x] **Documentation**: Document the "Handler/Policy/Schema" pattern and the stashing mechanism in a new `docs/` folder or updated `README.md`.
- [x] **Lazy load**
- [x] **Multiple Repo Support**: Enhance the CLI to easily switch between different S3/Local repo profiles.
- [ ] **Export Formats**: Add a post-processing stage to export results into common formats (SRT, VTT, JSON, TXT).
- [ ] **CPU support**
- [ ] **Various model sizes support**


## Production
- [x] **Dockerfile**: Write dockerfile for encapsulating `tadween-whisperx` as a service. Bake essential models into the image.