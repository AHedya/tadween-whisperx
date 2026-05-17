import logging

from tadween_core.handler import BaseHandler
from whisperx import load_model

from .schema import (
    TranscriptionInput,
    TranscriptionModelConfig,
    TranscriptionOutput,
)

logger = logging.getLogger("tadween_whisperx")


class TranscriptionHandler(BaseHandler[TranscriptionInput, TranscriptionOutput]):
    def __init__(self, model_config: TranscriptionModelConfig):
        self.config = model_config
        self._model = None

    def run(self, inputs):
        if self._model is None:
            self.warmup()

        result = self._model.transcribe(inputs.audio, inputs.batch_size)

        return TranscriptionOutput.model_validate(result)

    def warmup(self, cfg: TranscriptionModelConfig | None = None):
        logger.info("warming up transcription model")
        cfg = cfg or self.config
        if self._model is not None:
            logger.debug("already loaded")
            return

        cfg = cfg.model_dump()
        model_id = cfg.pop("model_id")
        device = cfg.pop("device")
        self._model = load_model(model_id, device, **cfg)

    def shutdown(self):
        import gc

        import torch

        gc.collect()
        torch.cuda.empty_cache()
        del self._model
