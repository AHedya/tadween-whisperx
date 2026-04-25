import time

from tadween_core.stage import DefaultStagePolicy, decorators
from tadween_core.stage.decorators import inject_cache

from tadween_whisperx.components.artifact import (
    PART_NAMES,
    Artifact,
    CacheSchema,
)
from tadween_whisperx.components.throttle import free_audio_cache
from tadween_whisperx.components.utils import timing_callback

from .handler import DiarizationInput, DiarizationOutput
from .schema import DiarizationPart


class DiarizationPolicy(
    DefaultStagePolicy[
        DiarizationInput, DiarizationOutput, CacheSchema, Artifact, PART_NAMES
    ]
):
    @inject_cache("audio_array", "audio")
    def resolve_inputs(
        self,
        message,
        repo=None,
        cache=None,
        **kwargs,
    ):
        return DiarizationInput(audio=kwargs["audio"], return_embeddings=False)

    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        if repo is None:
            return
        id = message.metadata.get("artifact_id")
        cache_key = message.metadata.get("cache_key")
        art = repo.load(id, None)
        art.meta.updated_at = time.time()
        art.meta.stage = "diarization"

        # result already validated. skip part validation
        art.diarization = DiarizationPart.model_construct(**result.__dict__)
        repo.save(art, include=["diarization"])

        del art
        free_audio_cache(cache, cache_key)

    @decorators.done_timing(
        stage_name="diarizer",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass
