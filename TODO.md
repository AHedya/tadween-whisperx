# TODO List

Enhancement and priority guide for `tadween-whisperx`.

## Testing & Validation
- [ ] **Unit Tests for Builder**: Test `WorkflowBuilder` to ensure DAG integrity when various components are disabled.
- [ ] **Integration Tests**: Create an end-to-end test suite using a small sample audio file to verify the pipeline flow.
- [ ] **Policy Tests**: Test individual stage policies.

## Observability & UI
- [ ] **CLI Progress Tracking**: Re-integrate and complete the `ProgressUIListener` using `rich.live` to show real-time stage progress.
- [ ] **Stage-Specific Metrics**: Log and display processing speed (e.g., RTF - Real Time Factor) for transcription and diarization.
- [ ] **Detailed Logging**: Add more granular logging in `tadween-whisperx`.

## Stability & Resiliency
- [ ] **OOM Protection**: Implement explicit handling for CUDA Out-of-Memory errors to prevent the entire pipeline from crashing.
- [ ] **Retry Logic**: Add retry decorators to Policies for transient failures (especially for S3 downloads and model inference) *(tadween_core limitation)*.
- [ ] **Graceful Shutdown**: Ensure `wf.close()` and `scanner.close()` handle interrupts (Ctrl+C) cleanly, releasing GPU memory and deleting temp files.

## DX & Features
- [x] **Scanner pattern**: Add matching patterns for exclusion or strict include for scanners.
- [ ] **Documentation**: Document the "Handler/Policy/Schema" pattern and the stashing mechanism in a new `docs/` folder or updated `README.md`.
- [ ] **Lazy load**
- [ ] **Multiple Repo Support**: Enhance the CLI to easily switch between different S3/Local repo profiles.
- [ ] **Export Formats**: Add a post-processing stage to export results into common formats (SRT, VTT, JSON, TXT).

## Cleanup
- [ ] **Prototype Migration**: Review `main.py` and migrate any useful performance-tracking or debugging logic into the core package or tests.

## Production
- [ ] **Dockerfile**: Write dockerfile for encapsulating `tadween-whisperx` as a service. Bake essential models into the image.