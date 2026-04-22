import time

from tadween_core.stage import DefaultStagePolicy, decorators

from tadween_whisperx.components.artifact import (
    PART_NAMES,
    Artifact,
    CacheSchema,
)
from tadween_whisperx.components.normalizer.schema import NormalizationPart
from tadween_whisperx.components.utils import timing_callback

from .handler import NormalizerInput


class NormalizerPolicy(
    DefaultStagePolicy[
        NormalizerInput, NormalizerInput, CacheSchema, Artifact, PART_NAMES
    ]
):
    def resolve_inputs(self, message, repo=None, cache=None):
        id = message.metadata.get("artifact_id")
        cache_key = message.metadata.get("cache_key")
        if cache[cache_key] and cache[cache_key].transcription is not None:
            return NormalizerInput(segments=cache[cache_key].transcription.segments)
        else:
            art = repo.load(id, ["transcription"])
            cache[cache_key].transcription = art.transcription
            return NormalizerInput(segments=art.transcription.segments)

    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        id = message.metadata.get("artifact_id")
        cache_key = message.metadata.get("cache_key")

        art = repo.load(id, None)
        art.meta.updated_at = time.time()
        art.meta.stage = "normalized"

        art.normalization = NormalizationPart.model_construct(
            segments=result.segments,
            language=cache[cache_key].transcription.language,
        )
        repo.save(art, include=["normalization"])

        cache[cache_key].normalization = art.normalization
        del art

    @decorators.done_timing(
        stage_name="Normalizer",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass
