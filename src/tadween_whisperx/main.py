"""Experimental script"""

import logging
import time
import warnings

from tadween_whisperx._logging import set_logger
from tadween_whisperx.builder import WorkflowBuilder
from tadween_whisperx.config import load_config

warnings.filterwarnings("ignore")

DISABLED_LOGGERS = ["whisperx", "lightning.pytorch", "pytorch_lightning"]

logger = logging.getLogger("tadween_whisperx")


def main():
    for i in DISABLED_LOGGERS:
        logging.getLogger(i).setLevel(logging.CRITICAL)
    config = load_config()

    set_logger(
        level=config.log_level,
        log_path=config.log_path,
    )

    begin = time.perf_counter()
    builder = WorkflowBuilder(config)
    wf = builder.build()
    if wf is None:
        return
    scanner = builder.get_scanner()
    print(wf.resource_manager)
    try:
        for i, result in enumerate(scanner.scan()):  # noqa
            wf.submit(
                result.task_input,
                metadata={
                    "file_name": result.file_path.name,
                    "cache_key": str(result.artifact_id),
                    "artifact_id": result.artifact_id,
                },
            )
            if i == 4:
                break
    finally:
        wf.close()
        scanner.close()

    end = time.perf_counter()
    logger.info(f"\n{'-' * 30}\ntime elapsed: {(end - begin):.5f}")


if __name__ == "__main__":
    # from tadween_core.devtools.analytics.collectors.memory import MemoryCollector
    # with MemoryCollector().session(
    #     title="many-stash",
    #     main_interval=0.5,
    #     include_children=False,
    #     log_dir="/home/projects/tadween/packages/tadween-whisperx/",
    #     file_name="ram.log",
    #     main_metric_collector="vms",
    # ):
    main()
