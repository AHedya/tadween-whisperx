from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel
from tadween_core.types.artifact.base import BaseArtifact, RootModel

from .alignment.schema import AlignmentOutput, AlignmentPart
from .diarization.schema import DiarizationOutput, DiarizationPart
from .normalizer.schema import NormalizationOutput, NormalizationPart
from .transcription.schema import TranscriptionOutput, TranscriptionPart


class MetaModel(BaseModel):
    stage: str = "init"
    source: str
    updated_at: float


@dataclass
class CacheSchema:
    file_path: Path | None = None
    audio_array: np.ndarray | None = None
    transcription: TranscriptionOutput | None = None
    diarization: DiarizationOutput | None = None
    alignment: AlignmentOutput | None = None
    normalization: NormalizationOutput | None = None

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
