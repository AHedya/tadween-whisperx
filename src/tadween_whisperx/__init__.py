import logging
import warnings
from importlib.metadata import PackageNotFoundError, version

from ._logging import set_logger
from .config import bootstrap_env

# consider moving it to pre-run entrypoints instead of app entrypoint
bootstrap_env()

warnings.filterwarnings("ignore")


logger = logging.getLogger("tadween_whisperx")
logger.addHandler(logging.NullHandler())


try:
    __version__ = version("tadween-whisperx")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = [
    "set_logger",
    "__version__",
]
