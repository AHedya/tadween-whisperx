from unittest.mock import MagicMock

import pytest

from tadween_whisperx.config import (
    AlignmentConfig,
    AppConfig,
    DiarizationConfig,
    LocalInputConfig,
    NormalizerConfig,
    TranscriptionConfig,
)
from tadween_whisperx.runner import Runner


def test_runner_happy_path(sample_audio, tmp_path, mock_handlers, mocker):  # noqa: ARG001
    # Setup config
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
        diarization=DiarizationConfig(enabled=True),
        transcription=TranscriptionConfig(enabled=True),
        alignment=AlignmentConfig(enabled=True),
        normalizer=NormalizerConfig(enabled=True),
        log_level="ERROR",
        core_log_level="ERROR",
    )

    mocker.patch("tadween_whisperx.components.throttle.get_config", return_value=config)

    runner = Runner(config)
    runner.run()

    # Verify the pipeline called our mocks
    mock_handlers["loader"].assert_called()
    mock_handlers["transcription"].assert_called()
    mock_handlers["diarization"].assert_called()
    mock_handlers["alignment"].assert_called()

    # Assert cache free-ed
    assert runner.wf.cache.get_bucket("0") is None
    # memory broker
    assert not runner.wf.broker._running
    assert runner.wf.context.is_shutdown
    assert runner.wf.resource_manager.is_shutdown


def test_runner_failing_task_rollback(sample_audio, tmp_path, mocker):  # noqa: ARG001
    try:
        config = AppConfig(
            input=LocalInputConfig(paths=[tmp_path]),
            log_level="ERROR",
            core_log_level="ERROR",
        )
        runner = Runner(config)
        runner.setup()
        wf = runner.wf
        assert wf.context.state.get("active_stash", 0) == 0

        mocker.patch(
            "tadween_whisperx.components.loader.handler.TorchCodecHandler.run",
            side_effect=RuntimeError("Simulated failure"),
        )
        mocker.patch(
            "tadween_whisperx.components.throttle.get_config", return_value=config
        )

        runner.run()

        assert wf.context.state.get("active_stash") == 0
        assert len(wf.context.state.get("__cache__")) == 0
    finally:
        runner.close()


def test_runner_keyboard_interrupt_during_scan(sample_audio, tmp_path, mocker):  # noqa: ARG001
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
    )

    mocker.patch(
        "tadween_whisperx.scanners.local.LocalScanner.scan",
        side_effect=KeyboardInterrupt(),
    )
    mock_build = mocker.patch("tadween_whisperx.builder.WorkflowBuilder.build")

    mock_wf = MagicMock()
    mock_build.return_value = mock_wf

    runner = Runner(config)
    with pytest.raises(KeyboardInterrupt):
        runner.run()

    mock_wf.close.assert_called_once()


def test_runner_dynamic_cleanup_on_chain_failure(
    sample_audio,  # noqa: ARG001
    tmp_path,
    mock_handlers,
    mocker,
):
    """
    Verifies that a failure in a parent stage (Transcription)
    correctly releases the stash slot AND clears the audio cache,
    even if children (Alignment) are skipped.
    """
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
        transcription=TranscriptionConfig(enabled=True),
        alignment=AlignmentConfig(enabled=True),  # Depends on transcription
        diarization=DiarizationConfig(enabled=False),
        normalizer=NormalizerConfig(enabled=False),
    )

    # Transcription fails
    mock_handlers["transcription"].side_effect = RuntimeError("Transcription failed")
    mocker.patch("tadween_whisperx.config.get_config", return_value=config)

    runner = Runner(config)
    runner.run()

    wf = runner.wf
    # active_stash must be 0
    assert wf.context.state_get("active_stash") == 0
    assert wf.cache.get_bucket("0") is None

    # Alignment should never have been called
    mock_handlers["alignment"].assert_not_called()


@pytest.mark.parametrize("failing_stage", ["diarization", "transcription", "alignment"])
def test_runner_comprehensive_failure_scenarios(
    sample_audio,  # noqa: ARG001
    tmp_path,
    failing_stage,
    mock_handlers,
    mocker,
):
    """
    Verifies that a failure in ANY consumer stage in a full DAG
    correctly releases the stash slot AND clears the audio cache.
    """
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
        diarization=DiarizationConfig(enabled=True),
        transcription=TranscriptionConfig(enabled=True),
        alignment=AlignmentConfig(enabled=True),
        normalizer=NormalizerConfig(enabled=True),
        log_level="ERROR",
        core_log_level="ERROR",
    )

    mocker.patch("tadween_whisperx.config.get_config", return_value=config)
    mock_handlers.get(failing_stage).side_effect = RuntimeError("Stage failed")

    runner = Runner(config)
    runner.run()

    wf = runner.wf

    # active_stash must be 0
    assert wf.context.state_get("active_stash") == 0
    assert wf.cache.get_bucket("0") is None
