import gc  # noqa
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel
from tadween_core.cache.base import BaseCache
from tadween_core.coord import WorkflowContext
from tadween_core.types.artifact.base import BaseArtifact, RootModel

from tadween_whisperx.config import get_config

from .alignment.schema import AlignmentPart
from .diarization.schema import DiarizationPart
from .normalizer.schema import NormalizationPart
from .transcription.schema import TranscriptionPart

STASH_EVENT = "stash_limit"
NUM_REQUIRING_AUDIO: int | None = None


def get_num_requiring_audio() -> int:
    global NUM_REQUIRING_AUDIO
    if NUM_REQUIRING_AUDIO is not None:
        return NUM_REQUIRING_AUDIO

    config = get_config()
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
    Reference count is based on the number of parallel branches (Diarization & Transcription).
    """
    config = get_config()
    artifact_id = meta.get("artifact_id")
    ctx.increment("active_stash")

    # Calculate branches that will independently release this artifact. Can be overridden with per-artifact active stages.
    branches = 0
    if config.diarization.enabled:
        branches += 1
    if config.transcription.enabled:
        branches += 1

    ctx.state[f"ref:{artifact_id}"] = branches


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


class MetaModel(BaseModel):
    stage: str = "init"
    local_path: str
    updated_at: float


@dataclass
class CacheSchema:
    file_path: Path | None = None
    audio_array: np.ndarray | None = None
    transcription: Any | None = None  # Using Any to avoid circular imports
    diarization: Any | None = None
    alignment: Any | None = None
    normalization: Any | None = None

    # For SimpleCache manual management if needed
    audio_array_touch_counter: int = 0


class ArtifactRoot(RootModel):
    pass


class Artifact(BaseArtifact):
    root: ArtifactRoot
    meta: MetaModel

    # Parts will be dynamically added or kept optional
    diarization: DiarizationPart
    transcription: TranscriptionPart
    alignment: AlignmentPart
    normalization: NormalizationPart


# We'll define PART_NAMES in a way that can be extended or imported from here
PART_NAMES = Literal["diarization", "transcription", "alignment", "normalization"]


def free_audio_cache(
    cache: BaseCache[CacheSchema],
    cache_key: str,
    touches: int | None = None,
):
    if touches is None:
        touches = get_num_requiring_audio()

    logger = logging.getLogger("tadween.cache")
    with cache.lock:
        if bkt := cache.get_bucket(cache_key):
            bkt.audio_array_touch_counter += 1
            if bkt.audio_array_touch_counter >= touches:
                bkt.audio_array = None
                logger.info(
                    "FREEING cache "
                    f"`{cache_key}.audio_array` [{bkt.audio_array_touch_counter}]"
                )
                gc.collect()
