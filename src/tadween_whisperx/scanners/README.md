# Scanners

Scanners are responsible for discovering input files and preparing them for the workflow. They normalize various sources (Local, S3, HTTP) into a consistent set of `ScanResult` objects.

## Supported Sources

### 1. Local Files (`local`)
Scans a list of directory paths or specific files on the local filesystem.

### 2. S3 Buckets (`s3`)
Scans S3 prefixes for compatible audio files. Requires valid AWS credentials.

### 3. HTTP URLs (`http`)
Processes audio files directly from the web.
- **Validation**: Performs a HEAD check to ensure a valid audio source.
- **Operational Side Effects**: 
    - Files are downloaded to a local path before processing.
    - **Temp Management**: If no `--download-path` is provided, a platform-specific temporary directory is created with the prefix `tadween-x-`. This ensures easy isolation and cleanup.
    - **Cleanup**: If `--keep-downloaded` is not set, the download directory is recursively deleted after the pipeline completes.

## Deterministic Artifact IDs

To ensure results are reliably trackable across different environments, `tadween-whisperx` uses a deterministic hashing function to generate `artifact_id`s.

The ID format is: `{hash_of_canonical_uri}_{sanitized_filename}`

- **Canonical URIs**:
    - Local: `file:///absolute/path/to/audio.mp3`
    - S3: `s3://bucket-name/key/to/audio.mp3`
    - HTTP: The full source URL.
- **Hash**: An 8-character MD5 hash of the Canonical URI.
- **Sanitization**: Filenames are URL-encoded.

### Overriding Artifact IDs
Use the `id_map` in your configuration to provide custom identifiers for specific sources:

```yaml
input:
  type: local
  paths: ["./audio.mp3"]
  id_map:
    "file:///absolute/path/to/audio.mp3": "custom-id-123"
```
