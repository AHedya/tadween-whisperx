from tadween_whisperx.config import (
    AppConfig,
)


def _execute_pipeline(config: AppConfig):
    from tadween_whisperx.runner import Runner

    runner = Runner(config)
    runner.run()
