from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel
from tadween_core.types.artifact.base import BaseArtifact, RootModel

from .alignment.schema import AlignmentPart
from .diarization.schema import DiarizationPart
from .normalizer.schema import NormalizationPart
from .transcription.schema import TranscriptionPart


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

    diarization: DiarizationPart
    transcription: TranscriptionPart
    alignment: AlignmentPart
    normalization: NormalizationPart


PART_NAMES = Literal["diarization", "transcription", "alignment", "normalization"]
