import time
from pathlib import Path

from tadween_core.handler.defaults.s3_downloader import (
    S3DownloadInput,
    S3DownloadOutput,
)
from tadween_core.stage import DefaultStagePolicy, decorators
from tadween_core.stage.policy import InterceptionAction, InterceptionContext

from tadween_whisperx.components.artifact import (
    PART_NAMES,
    Artifact,
    ArtifactRoot,
    CacheSchema,
    MetaModel,
)
from tadween_whisperx.components.utils import timing_callback

from .handler import AudioLoaderInput, AudioLoaderOutput


class S3Policy(DefaultStagePolicy[S3DownloadInput, S3DownloadOutput, CacheSchema]):
    # check if already downloaded
    def intercept(self, message, broker=None, repo=None, cache=None):
        if message.metadata.get("file_name") == "compressed-1/ar-180m-podcast-3s.opus":
            return InterceptionContext(
                True, reason="lengthy", action=InterceptionAction.cancel()
            )

        if local_fp := message.metadata.get("local_path"):
            local_fp = Path(local_fp)
            if local_fp.exists():
                return InterceptionContext(
                    True,
                    S3DownloadOutput(
                        local_path=local_fp,
                        size_bytes=local_fp.stat().st_size,
                        download_duration_seconds=0,
                    ),
                )

    @decorators.write_cache(cache_field="file_path", result_field="local_path")
    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        pass

    @decorators.done_timing(
        stage_name="downloader",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass


class LoaderPolicy(
    DefaultStagePolicy[
        AudioLoaderInput, AudioLoaderOutput, CacheSchema, Artifact, PART_NAMES
    ]
):
    def resolve_inputs(self, message, repo=None, cache=None):
        # Loader might get file path from message payload directly if locally, or stashed to cache if downloaded first
        cache_key = message.metadata.get("cache_key")
        if cache_key and cache[cache_key]:
            file_path = cache[cache_key].file_path
            if file_path is not None:
                return AudioLoaderInput(file_path=file_path)
        return AudioLoaderInput(file_path=message.payload.get("file_path"))

    @decorators.write_cache("audio_array", result_field="audio_array")
    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        if repo is None:
            return
        id = message.metadata.get("artifact_id")
        # initialize the artifact
        if not repo.exists(id):
            art = Artifact(
                root=ArtifactRoot(id=id),
                meta=MetaModel(
                    stage="loaded",
                    local_path=message.metadata.get("file_name", ""),
                    updated_at=time.time(),
                ),
            )
            repo.save(art, include=None)

    @decorators.done_timing(
        stage_name="loader",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass
