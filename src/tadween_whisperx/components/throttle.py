import gc
import logging

from tadween_core.cache import BaseCache
from tadween_core.coord import WorkflowContext

from tadween_whisperx.config import get_config

from .artifact import CacheSchema

STASH_EVENT = "stash_limit"
# how many audio "touches" before freeing it.
NUM_REQUIRING_AUDIO: int | None = None


def get_workflow_resources() -> dict[str, int]:
    """Returns the total resource capacity for the workflow."""
    return {"cuda": 1}


def get_num_requiring_audio() -> int:
    global NUM_REQUIRING_AUDIO
    if NUM_REQUIRING_AUDIO is not None:
        return NUM_REQUIRING_AUDIO

    config = get_config()
    # Count every enabled stage that consumes the audio array
    stages = [
        config.diarization.enabled,
        config.transcription.enabled,
        config.alignment.enabled,
    ]
    NUM_REQUIRING_AUDIO = sum(stages)
    return NUM_REQUIRING_AUDIO


def stash_predicate(ctx: WorkflowContext, _meta: dict) -> bool:
    """Blocks if the number of active files in the pipeline exceeds MAX_STASH_DEPTH."""
    config = get_config()
    return ctx.state_get("active_stash", 0) >= config.loader.max_stashed_files


def claim_stash(ctx: WorkflowContext, meta: dict):
    """
    Claims a stash slot and initializes reference counting for the specific artifact.
    The reference count is equal to the number of stages that must call release_stash.
    """
    artifact_id = meta.get("artifact_id")
    ctx.increment("active_stash")

    # Every stage that consumes audio/processing must release the stash slot.
    # This matches the cache freeing philosophy (ref count = total touches).
    ctx.state[f"ref:{artifact_id}"] = get_num_requiring_audio()


def release_stash(ctx: WorkflowContext, meta: dict):
    """
    Decrements reference count for an artifact and releases the stash slot if it reaches zero.
    """
    artifact_id = meta.get("artifact_id")
    key = f"ref:{artifact_id}"

    with ctx._lock:
        if key not in ctx.state:
            return

        ctx.state[key] -= 1
        if ctx.state[key] <= 0:
            del ctx.state[key]
            ctx.decrement("active_stash")
            ctx.notify(STASH_EVENT)


def rollback_stash(ctx: WorkflowContext, meta: dict):
    """
    Rolls back a stash claim if the stage fails to enqueue the task.
    """
    artifact_id = meta.get("artifact_id")
    key = f"ref:{artifact_id}"

    with ctx._lock:
        if key in ctx.state:
            del ctx.state[key]
            ctx.decrement("active_stash")
            ctx.notify(STASH_EVENT)


def free_audio_cache(
    cache: BaseCache[CacheSchema],
    cache_key: str,
    touches: int | None = None,
):
    if touches is None:
        touches = get_num_requiring_audio()

    cache_logger = logging.getLogger("tadween.cache")
    with cache.lock:
        if bkt := cache.get_bucket(cache_key):
            bkt.audio_array_touch_counter += 1
            if bkt.audio_array_touch_counter >= touches:
                bkt.audio_array = None
                cache_logger.info(
                    "FREEING cache "
                    f"`{cache_key}.audio_array` [{bkt.audio_array_touch_counter}]"
                )
                gc.collect()
