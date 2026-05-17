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
*(Delegated to `tadween-core` orchestration and the end-user via the Shared Responsibility Model)*
- [x] **OOM Protection**: Mitigated via core `ResourceManager` capacity limits; explicit handling left to environment owners.
- [x] **Retry Logic**: Provided natively by `WorkflowRoutingPolicy` in `tadween-core`; users configure `RetryPolicy` per their infra needs.
- [x] **Graceful Shutdown**: Handled natively by `tadween-core` on SIGTERM/Ctrl+C.
- [x] **Idempotency**: Handled via `Policy.intercept` event hooks by the developer based on their specific repository logic.

## DX & Features
- [x] **Scanner pattern**: Add matching patterns for exclusion or strict include for scanners.
- [x] **Documentation**: Documented the "Handler/Policy/Schema" pattern, stashing mechanism, and containerization strategies in README.md and sub-packages.
- [x] **Lazy load**
- [x] **Multiple Repo Support**: Enhance the CLI to easily switch between different S3/Local repo profiles.
- [ ] **Export Formats**: Add a post-processing stage to export results into common formats (SRT, VTT, JSON, TXT).
- [ ] **CPU support**
- [x] **Various model sizes support**
- [ ] **Multiple alignment models bake-in**: Add alignment models to both *Dockerfile* and runtime app config and preflight check.
- [ ] **Low-friction config**: Add support for nested env vars overriding selective config params. For instance: `LOADER__MAX_STASHED_FILES` overrides `config.loader.max_stashed_files`

## Production
- [x] **Dockerfile**: Write dockerfile for encapsulating `tadween-whisperx` as a service. Bake essential models into the image.