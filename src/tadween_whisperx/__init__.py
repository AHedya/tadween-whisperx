import logging
import os
import warnings
from importlib.metadata import PackageNotFoundError, version

from ._logging import set_logger

warnings.filterwarnings("ignore")


logger = logging.getLogger("tadween_whisperx")
logger.addHandler(logging.NullHandler())


try:
    __version__ = version("tadween-whisperx")
except PackageNotFoundError:
    __version__ = "0.1.0"

DISABLED_LOGGERS = ["whisperx", "lightning.pytorch", "pytorch_lightning"]
for i in DISABLED_LOGGERS:
    logging.getLogger(i).setLevel(logging.CRITICAL)

__all__ = [
    "set_logger",
    "__version__",
]

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
os.environ["PYANNOTE_METRICS_ENABLED"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["LIGHTNING_WHISPER_LOG_LEVEL"] = "ERROR"
