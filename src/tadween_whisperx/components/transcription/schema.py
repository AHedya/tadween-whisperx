import numpy as np
from pydantic import BaseModel, ConfigDict
from tadween_core.types.artifact.part import PicklePart

from tadween_whisperx.schema import SingleSegment


class TranscriptionInput(BaseModel):
    audio: str | np.ndarray
    batch_size: int = 8

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TranscriptionOutput(BaseModel):
    language: str
    segments: list[SingleSegment]


class TranscriptionPart(TranscriptionOutput, PicklePart):
    pass
