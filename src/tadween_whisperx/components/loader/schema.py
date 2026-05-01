from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, SkipValidation


class AudioLoaderInput(BaseModel):
    file_path: Path
    sr: int = 16_000


class AudioLoaderOutput(BaseModel):
    audio_array: SkipValidation[np.ndarray]

    model_config = ConfigDict(arbitrary_types_allowed=True)
