import logging
import sys

# local logger
logger = logging.getLogger("tadween_whisperx.timing")
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(
    "%(message)s",
    datefmt="%H:%M:%S",
)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
# logger.addHandler(stdout_handler)


def timing_callback(stage: str, label: str, waiting: float, duration: float):
    logger.info(
        f"[{stage} — {label}] Waiting: {waiting:.3f}s duration: {duration:.3f}s"
    )
