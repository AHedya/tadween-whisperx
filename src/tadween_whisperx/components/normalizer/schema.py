from pydantic import BaseModel
from tadween_core.types.artifact.part import PicklePart

from tadween_whisperx.components.schema import SingleSegment


class NormalizationOutput(BaseModel):
    segments: list[SingleSegment]
    language: str


class NormalizationPart(NormalizationOutput, PicklePart):
    pass
