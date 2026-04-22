from numpy import ndarray
from pydantic import BaseModel, ConfigDict
from tadween_core.types.artifact.part import PicklePart

from tadween_whisperx.schema import (
    SingleAlignedSegment,
    SingleSegment,
    SingleWordSegment,
)


class AlignmentInput(BaseModel):
    segments: list[SingleSegment]
    audio: ndarray | str
    language: str | None = None
    return_char_alignments: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AlignmentOutput(BaseModel):
    segments: list[SingleAlignedSegment]
    word_segments: list[SingleWordSegment]


class AlignmentPart(AlignmentOutput, PicklePart):
    pass
