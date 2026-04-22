import logging
import sys
from pathlib import Path


def set_logger(level=logging.INFO, log_path=None, silent_console=False):
    """
    Configures 'tadween' and 'tadween_whisperx' loggers.

    Args:
        level: Logging level (e.g., logging.DEBUG)
        log_path: Optional string or Path to a log file.
        silent_console: If True, StreamHandler (console) will not be added.
    """
    loggers = [logging.getLogger("tadween_whisperx"), logging.getLogger("tadween")]

    formatter = logging.Formatter(
        "%(asctime)s:[%(levelname)s] - %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    for logger in loggers:
        logger.setLevel(level)
        if logger.hasHandlers():
            logger.handlers.clear()

        if not silent_console:
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(formatter)
            logger.addHandler(stdout_handler)

        if log_path:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return loggers[0]
