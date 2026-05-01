import gc
import logging
import threading
from collections import OrderedDict
from typing import Any

import torch
from tadween_core.handler import BaseHandler
from whisperx import align, load_align_model

from .schema import AlignmentConfig, AlignmentInput, AlignmentOutput

logger = logging.getLogger("tadween_whisperx")


class AlignmentHandler(BaseHandler[AlignmentInput, AlignmentOutput]):
    def __init__(self, config: AlignmentConfig):
        self.config = config
        # OrderedDict LRU management. OrderedDict[language, tuple[alignment_model, metadata]]
        self._registry: OrderedDict[str, tuple[Any, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def warmup(self, cfg: AlignmentConfig | None = None, language: str | None = None):
        cfg = cfg or self.config
        lang = language or cfg.language_code

        if not lang:
            return

        with self._lock:
            # If already loaded, move to "most recent" (end of OrderedDict)
            if lang in self._registry:
                self._registry.move_to_end(lang)
                return

            # Check capacity and evict least recently used (first item)
            if len(self._registry) >= self.config.max_models:
                oldest_lang, (old_model, _) = self._registry.popitem(last=False)
                logger.info(f"Evicting alignment model for language: {oldest_lang}")

                del old_model
                gc.collect()
                if "cuda" in self.config.device:
                    torch.cuda.empty_cache()

            # Load the new model
            logger.info(f"Loading alignment model for language: {lang}")
            model, metadata = load_align_model(
                language_code=lang,
                device=cfg.device,
                model_name=cfg.model_name,
                model_dir=cfg.model_dir,
                model_cache_only=cfg.model_cache_only,
            )
            self._registry[lang] = (model, metadata)

    def run(self, inputs: AlignmentInput):
        lang = inputs.language or self.config.language_code
        if not lang:
            raise ValueError("No language code provided for alignment.")

        self.warmup(language=lang)

        # Access under lock is usually not needed for the read if model
        # is guaranteed to be there, but safer if eviction can happen mid-run.
        with self._lock:
            model, metadata = self._registry[lang]

        result = align(
            transcript=inputs.segments,
            model=model,
            align_model_metadata=metadata,
            audio=inputs.audio,
            device=self.config.device,
            return_char_alignments=inputs.return_char_alignments,
        )

        return AlignmentOutput.model_validate(result)

    def shutdown(self):
        with self._lock:
            self._registry.clear()
            gc.collect()
            if "cuda" in self.config.device:
                torch.cuda.empty_cache()
