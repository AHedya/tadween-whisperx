import gc
import logging
from typing import Any

from tadween_core.cache import BaseCache
from tadween_core.coord import WorkflowContext

from tadween_whisperx.config import get_config

from .artifact import CacheSchema

STASH_EVENT = "stash_limit"


def get_workflow_resources() -> dict[str, int]:
    """Returns the total resource capacity for the workflow."""
    return {"cuda": 1}


def stash_predicate(ctx: WorkflowContext, _meta: dict) -> bool:
    """Blocks if the number of active files in the pipeline exceeds MAX_STASH_DEPTH."""
    config = get_config()
    return ctx.state_get("active_stash", 0) >= config.loader.max_stashed_files


def claim_stash(ctx: WorkflowContext, meta: dict):
    """
    Claims a stash slot for the specific artifact.
    """
    artifact_id = meta.get("artifact_id")
    cache_key = meta.get("cache_key")
    key = f"stash:{artifact_id}"
    with ctx._lock:
        if cache_key:
            ctx.state[f"cache_key:{artifact_id}"] = cache_key
        if key not in ctx.state:
            ctx.state[key] = True
            ctx.increment("active_stash")


def rollback_stash(ctx: WorkflowContext, meta: dict):
    """
    Rolls back a stash claim if the stage fails to enqueue the task.
    """
    artifact_id = meta.get("artifact_id")
    key = f"stash:{artifact_id}"

    with ctx._lock:
        if ctx.state.pop(key, False):
            ctx.decrement("active_stash")
            ctx.notify(STASH_EVENT)


def release_cache(
    ctx: WorkflowContext,
    artifact_id: str,
    cache_key: str | None = None,
    **kwargs: Any,  # noqa: ARG001
):
    """
    Callback fired by tadween-core when an artifact has finished processing.
    Releases the stash slot and clears the heavy audio_array from cache.
    """
    # 1. Release stash slot regardless of cache presence
    with ctx._lock:
        if ctx.state.pop(f"stash:{artifact_id}", False):
            ctx.decrement("active_stash", 1)
            ctx.notify(STASH_EVENT)

    # 2. Centralized Cleanup: Clear audio_array from cache
    cache: BaseCache[CacheSchema] | None = ctx.state.get("__cache__")
    actual_cache_key = cache_key or ctx.state.pop(f"cache_key:{artifact_id}", None)

    if cache and actual_cache_key:
        with cache.lock:
            if actual_cache_key in cache:
                cache.delete_bucket(actual_cache_key)
                logging.getLogger("tadween.cache").info(
                    f"CACHE cleanup for `{actual_cache_key}`"
                )
        gc.collect()
