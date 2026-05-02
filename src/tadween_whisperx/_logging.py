import logging
import sys
from pathlib import Path

from rich.console import Console

console = Console()
timing_logger = logging.getLogger("tadween_whisperx.timing")


def set_logger(level=logging.INFO, log_path=None, silent_console=False):
    """
    Configures 'tadween_whisperx' logger and its timing child.

    Args:
        level: Logging level (e.g., logging.DEBUG)
        log_path: Optional string or Path to a log file.
        silent_console: If True, StreamHandler (console) will not be added.
    """
    app_logger = logging.getLogger("tadween_whisperx")
    app_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s:[%(levelname)s] - %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if app_logger.hasHandlers():
        app_logger.handlers.clear()

    if not silent_console:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        app_logger.addHandler(stdout_handler)

    if log_path:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        app_logger.addHandler(file_handler)

    # Configure timing logger specifically
    # It should NOT have a stream handler, but should have a file handler if log_path is provided.
    timing_logger.setLevel(level)
    timing_logger.propagate = False  # Avoid parent's StreamHandler
    if timing_logger.hasHandlers():
        timing_logger.handlers.clear()

    if log_path:
        path = Path(log_path)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        timing_logger.addHandler(file_handler)

    return app_logger


def timing_callback(stage: str, label: str, waiting: float, duration: float):
    # Log to file (if configured)
    timing_logger.info(
        f"[{stage} — {label}] Waiting: {waiting:.2f}s duration: {duration:.2f}s"
    )

    # Rich console feedback
    console.print(
        rf"[bold blue]\[{stage}][/bold blue] "
        f"[cyan]{label}[/cyan] — "
        f"Wait: [yellow]{waiting:.3f}s[/yellow] "
        f"Duration: [green]{duration:.3f}s[/green]"
    )
