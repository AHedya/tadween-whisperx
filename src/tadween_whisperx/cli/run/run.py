from tadween_whisperx.config import (
    AppConfig,
)
from tadween_whisperx.runner import Runner


def _execute_pipeline(config: AppConfig):
    runner = Runner(config)
    runner.run()
