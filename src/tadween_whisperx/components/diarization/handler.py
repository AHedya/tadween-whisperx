import logging

from pydantic import BaseModel
from tadween_core.handler import BaseHandler
from whisperx.diarize import DiarizationPipeline

from .schema import DiarizationInput, DiarizationOutput

logger = logging.getLogger("tadween_whisperx")


class ModelConfig(BaseModel):
    token: str | None = None
    model_name: str = "pyannote/speaker-diarization-community-1"
    device: str = "cuda"
    cache_dir: str | None = None


class DiarizationHandler(BaseHandler[DiarizationInput, DiarizationOutput]):
    def __init__(self, model_config: ModelConfig = ModelConfig()):
        self.config = model_config
        self._model = None

    def run(self, inputs):
        if self._model is None:
            self.warmup()
        inputs = inputs.model_dump()
        res = self._model(**inputs)
        if inputs.get("return_embeddings"):
            df, embeds = res
        else:
            df = res
            embeds = None
        return DiarizationOutput(diarization_df=df, speaker_embeddings=embeds)

    def warmup(self, cfg: ModelConfig | None = None):
        logger.info("warming up diarization model")
        cfg = cfg or self.config
        if self._model is not None:
            logger.debug("already loaded")
            return
        self._model = DiarizationPipeline(**cfg.model_dump())

    def shutdown(self):
        import gc

        import torch

        gc.collect()
        torch.cuda.empty_cache()
        del self._model
