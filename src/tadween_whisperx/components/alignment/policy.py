import time

from tadween_core.repo.base import BaseArtifactRepo
from tadween_core.stage import DefaultStagePolicy, decorators
from tadween_core.stage.decorators import inject_cache
from tadween_core.stage.policy import InterceptionAction, InterceptionContext  # noqa

from tadween_whisperx.components.artifact import (
    PART_NAMES,
    Artifact,
    CacheSchema,
    free_audio_cache,
)
from tadween_whisperx.components.utils import timing_callback

from .handler import AlignmentInput, AlignmentOutput
from .schema import AlignmentPart


class AlignmentPolicy(
    DefaultStagePolicy[
        AlignmentInput, AlignmentOutput, CacheSchema, Artifact, PART_NAMES
    ]
):
    # def intercept(self, message, broker=None, repo=None, cache=None):
    #     id = message.metadata.get("artifact_id")
    #     if repo.has_parts(id).get("alignment"):
    #         return InterceptionContext(
    #             True,
    #             action=InterceptionAction.cancel(),
    #             reason="SKIP. Already aligned",
    #         )

    @inject_cache("audio_array", "audio")
    @inject_cache("transcription", "transcription")
    def resolve_inputs(
        self,
        message,
        repo: BaseArtifactRepo[Artifact] = None,
        cache=None,
        **kwargs,
    ):
        id = message.metadata.get("artifact_id")
        transcription = kwargs.get("transcription")
        if not transcription:
            art = repo.load(id, ["transcription"])
            transcription = art.transcription

        return AlignmentInput(
            segments=transcription.segments,
            audio=kwargs["audio"],
            language=transcription.language,
        )

    def on_success(self, task_id, message, result, broker=None, repo=None, cache=None):
        id = message.metadata.get("artifact_id")
        cache_key = message.metadata.get("cache_key")
        art = repo.load(id, None)
        art.meta.updated_at = time.time()
        art.meta.stage = "aligned"

        art.alignment = AlignmentPart.model_construct(**result.__dict__)
        repo.save(art, include=["alignment"])

        del art
        free_audio_cache(cache, cache_key)

    @decorators.done_timing(
        stage_name="Alignment",
        label_key="file_name",
        mode="before",
        callback=timing_callback,
    )
    def on_done(self, message, envelope):
        pass
