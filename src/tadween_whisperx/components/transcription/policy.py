import time

from tadween_core.stage import DefaultStagePolicy, decorators
from tadween_core.stage.decorators import inject_cache, write_cache
from tadween_core.stage.policy import InterceptionAction, InterceptionContext  # noqa

from tadween_whisperx.components.artifact import (
    PART_NAMES,
    Artifact,
    CacheSchema,
    free_audio_cache,
)
from tadween_whisperx.components.utils import timing_callback

from .handler import TranscriptionInput, TranscriptionOutput
from .schema import TranscriptionPart


class TranscriptionPolicy(
    DefaultStagePolicy[
        TranscriptionInput, TranscriptionOutput, CacheSchema, Artifact, PART_NAMES
    ]
):
    @inject_cache("audio_array", "audio")
    def resolve_inputs(self, message, repo=None, cache=None, **kwargs):
        return TranscriptionInput(audio=kwargs["audio"])

    @write_cache("transcription", None)  # None means the whole result.
    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        if repo is None:
            return
        id = message.metadata.get("artifact_id")
        cache_key = message.metadata.get("cache_key")
        art = repo.load(id, None)
        art.meta.updated_at = time.time()
        art.meta.stage = "transcription"

        art.transcription = TranscriptionPart.model_construct(**result.__dict__)
        repo.save(art, include=["transcription"])

        del art
        free_audio_cache(cache, cache_key)

    @decorators.done_timing(
        stage_name="transcriber",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass
