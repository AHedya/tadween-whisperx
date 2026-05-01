import logging
import warnings
from importlib.metadata import PackageNotFoundError, version

from ._logging import set_logger
from .config import bootstrap_env

bootstrap_env()

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
