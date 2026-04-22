import logging
import logging.handlers
import queue


def setup_benchmark_logger(
    log_file: str = "benchmark.log",
    level=logging.DEBUG,
    queue_maxsize: int = 10_000,
) -> logging.Logger:
    """
    Creates a 'benchmark' logger that:
        - Writes to `log_file` via a background QueueListener (thread-safe).
        - Workers push records through a QueueHandler (non-blocking).
        - Shares the same format as set_logger().
    """
    logger = logging.getLogger("benchmark")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if called more than once
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s:[%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = logging.FileHandler(
        log_file, mode="a", encoding="utf-8", delay=False
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    # --- Queue + listener (runs in its own daemon thread)
    log_queue: queue.Queue = queue.Queue(maxsize=queue_maxsize)
    listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        respect_handler_level=True,
    )
    listener.start()

    # --- QueueHandler attached to the logger itself
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(level)
    logger.addHandler(queue_handler)

    # Prevent records from bubbling up to the root logger
    logger.propagate = False

    logger._queue_listener = listener

    return logger


def stop_benchmark_logger():
    """Flush & stop the QueueListener. Call once at program exit."""
    logger = logging.getLogger("benchmark")
    listener: logging.handlers.QueueListener | None = getattr(
        logger, "_queue_listener", None
    )
    if listener:
        listener.stop()
