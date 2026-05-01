from typing import Any

import numpy as np
from pandas import DataFrame
from pydantic import (
    BaseModel,
    ConfigDict,
    SerializationInfo,
    field_serializer,
    field_validator,
)
from tadween_core.types.artifact.part import PicklePart


class DiarizationModelConfig(BaseModel):
    token: str | None = None
    model_name: str = "pyannote/speaker-diarization-community-1"
    device: str = "cuda"
    cache_dir: str | None = None


class DiarizationInput(BaseModel):
    audio: str | np.ndarray
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    return_embeddings: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)


class DiarizationOutput(BaseModel):
    diarization_df: DataFrame
    speaker_embeddings: dict | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("diarization_df")
    def serialize_df(self, value: DataFrame, info: SerializationInfo) -> list:
        return value.to_dict(orient="records")

    @field_validator("diarization_df", mode="before")
    @classmethod
    def validate_df(cls, value: Any) -> DataFrame:
        if isinstance(value, list):
            from pyannote.core.segment import Segment

            for v in value:
                v["segment"] = Segment(
                    start=v["segment"]["start"], end=v["segment"]["end"]
                )
            return DataFrame(value)

        return value


class DiarizationPart(DiarizationOutput, PicklePart):
    pass
