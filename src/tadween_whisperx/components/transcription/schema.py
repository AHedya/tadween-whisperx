import numpy as np
from pydantic import BaseModel, ConfigDict
from tadween_core.types.artifact.part import PicklePart

from tadween_whisperx.components.schema import SingleSegment


class TranscriptionModelConfig(BaseModel):
    model_id: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str | None = None
    threads: int = 4


class TranscriptionInput(BaseModel):
    audio: str | np.ndarray
    batch_size: int = 8

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TranscriptionOutput(BaseModel):
    language: str
    segments: list[SingleSegment]


class TranscriptionPart(TranscriptionOutput, PicklePart):
    pass
