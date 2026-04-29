from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pyannote.core.segment import Segment

from tadween_whisperx.builder import WorkflowBuilder
from tadween_whisperx.components.alignment.schema import AlignmentOutput
from tadween_whisperx.components.diarization.schema import DiarizationOutput
from tadween_whisperx.components.loader.handler import AudioLoaderOutput
from tadween_whisperx.components.transcription.schema import TranscriptionOutput
from tadween_whisperx.config import (
    AlignmentConfig,
    AppConfig,
    DiarizationConfig,
    LocalInputConfig,
    NormalizerConfig,
    TranscriptionConfig,
)
from tadween_whisperx.runner import Runner


@pytest.fixture
def tmp_audio(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.touch()
    return audio_file


def test_runner_happy_path(tmp_audio, tmp_path):  # noqa: ARG001
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

    # Mocking Handlers
    with (
        patch(
            "tadween_whisperx.components.loader.handler.TorchCodecHandler.run"
        ) as mock_loader_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.run"
        ) as mock_transcription_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.warmup"
        ),
        patch(
            "tadween_whisperx.components.diarization.handler.DiarizationHandler.run"
        ) as mock_diarization_run,
        patch(
            "tadween_whisperx.components.diarization.handler.DiarizationHandler.warmup"
        ),
        patch(
            "tadween_whisperx.components.alignment.handler.AlignmentHandler.run"
        ) as mock_alignment_run,
        patch("tadween_whisperx.components.alignment.handler.AlignmentHandler.warmup"),
        patch("tadween_whisperx.components.throttle.get_config", return_value=config),
    ):
        mock_loader_run.return_value = AudioLoaderOutput(
            audio_array=np.array([0.1, 0.2], dtype=np.float32)
        )

        mock_transcription_run.return_value = TranscriptionOutput(
            language="en", segments=[{"start": 0.0, "end": 1.0, "text": "hello"}]
        )

        mock_diarization_run.return_value = DiarizationOutput(
            diarization_df=pd.DataFrame(
                [{"segment": Segment(0.0, 1.0), "label": "SPEAKER_00"}]
            )
        )

        mock_alignment_run.return_value = AlignmentOutput(
            segments=[
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "hello",
                    "words": [
                        {"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}
                    ],
                }
            ],
            word_segments=[{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}],
        )

        runner = Runner(config)
        runner.run()

        # Verify the pipeline called our mocks
        mock_loader_run.assert_called()
        mock_transcription_run.assert_called()
        mock_diarization_run.assert_called()
        mock_alignment_run.assert_called()

        # Assert cache free-ed
        assert runner.wf.cache.get_bucket("0") is None
        # memory broker
        assert not runner.wf.broker._running
        assert runner.wf.context.is_shutdown
        assert runner.wf.resource_manager.is_shutdown


def test_runner_failing_task_rollback(tmp_audio, tmp_path):  # noqa: ARG001
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

        with (
            patch(
                "tadween_whisperx.components.loader.handler.TorchCodecHandler.run",
                side_effect=RuntimeError("Simulated failure"),
            ),
            patch(
                "tadween_whisperx.components.throttle.get_config", return_value=config
            ),
        ):
            runner.run()

        assert wf.context.state.get("active_stash") == 0
    finally:
        runner.close()


def test_runner_keyboard_interrupt_during_scan(tmp_audio, tmp_path):  # noqa: ARG001
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
    )

    with (
        patch(
            "tadween_whisperx.scanners.local.LocalScanner.scan",
            side_effect=KeyboardInterrupt(),
        ),
        patch("tadween_whisperx.builder.WorkflowBuilder.build") as mock_build,
    ):
        mock_wf = MagicMock()
        mock_build.return_value = mock_wf

        runner = Runner(config)
        with pytest.raises(KeyboardInterrupt):
            runner.run()

        mock_wf.close.assert_called_once()


def test_runner_dynamic_cleanup_on_chain_failure(tmp_audio, tmp_path):  # noqa: ARG001
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

    # Mocking Handlers: Transcription fails
    with (
        patch(
            "tadween_whisperx.components.loader.handler.TorchCodecHandler.run"
        ) as mock_loader_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.run",
            side_effect=RuntimeError("Transcription failed"),
        ) as mock_transcription_run,  # noqa: F841
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.warmup"
        ),
        patch(
            "tadween_whisperx.components.alignment.handler.AlignmentHandler.run"
        ) as mock_alignment_run,
        patch("tadween_whisperx.components.alignment.handler.AlignmentHandler.warmup"),
        patch("tadween_whisperx.components.throttle.get_config", return_value=config),
    ):
        mock_loader_run.return_value = AudioLoaderOutput(
            audio_array=np.array([0.1, 0.2], dtype=np.float32)
        )

        real_workflows = []
        original_build = WorkflowBuilder.build

        def wrapped_build(self):
            wf = original_build(self)
            real_workflows.append(wf)
            return wf

        with patch(
            "tadween_whisperx.builder.WorkflowBuilder.build",
            side_effect=wrapped_build,
            autospec=True,
        ):
            runner = Runner(config)
            runner.run()

            wf = real_workflows[0]
            # active_stash must be 0
            assert wf.context.state_get("active_stash") == 0

            # CACHE CLEANUP VERIFICATION
            # The bucket for the first file (cache_key="0") should be deleted
            assert wf.cache.get_bucket("0") is None

            # Alignment should never have been called
            mock_alignment_run.assert_not_called()


@pytest.mark.parametrize("failing_stage", ["diarization", "transcription", "alignment"])
def test_runner_comprehensive_failure_scenarios(tmp_audio, tmp_path, failing_stage):  # noqa: ARG001
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

    # Define side effects based on which stage should fail
    loader_ret = AudioLoaderOutput(audio_array=np.array([0.1, 0.2], dtype=np.float32))
    trans_ret = TranscriptionOutput(
        language="en", segments=[{"start": 0.0, "end": 1.0, "text": "hello"}]
    )
    diar_ret = DiarizationOutput(
        diarization_df=pd.DataFrame(
            [{"segment": Segment(0.0, 1.0), "label": "SPEAKER_00"}]
        )
    )
    align_ret = AlignmentOutput(
        segments=[
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "words": [{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}],
            }
        ],
        word_segments=[{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}],
    )

    with (
        patch(
            "tadween_whisperx.components.loader.handler.TorchCodecHandler.run"
        ) as mock_loader_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.run"
        ) as mock_transcription_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.warmup"
        ),
        patch(
            "tadween_whisperx.components.diarization.handler.DiarizationHandler.run"
        ) as mock_diarization_run,
        patch(
            "tadween_whisperx.components.diarization.handler.DiarizationHandler.warmup"
        ),
        patch(
            "tadween_whisperx.components.alignment.handler.AlignmentHandler.run"
        ) as mock_alignment_run,
        patch("tadween_whisperx.components.alignment.handler.AlignmentHandler.warmup"),
        patch("tadween_whisperx.components.throttle.get_config", return_value=config),
    ):
        mock_loader_run.return_value = loader_ret
        mock_transcription_run.return_value = trans_ret
        mock_diarization_run.return_value = diar_ret
        mock_alignment_run.return_value = align_ret

        if failing_stage == "diarization":
            mock_diarization_run.side_effect = RuntimeError("Diarization failed")
        elif failing_stage == "transcription":
            mock_transcription_run.side_effect = RuntimeError("Transcription failed")
        elif failing_stage == "alignment":
            mock_alignment_run.side_effect = RuntimeError("Alignment failed")

        real_workflows = []
        original_build = WorkflowBuilder.build

        def wrapped_build(self):
            wf = original_build(self)
            real_workflows.append(wf)
            return wf

        with patch(
            "tadween_whisperx.builder.WorkflowBuilder.build",
            side_effect=wrapped_build,
            autospec=True,
        ):
            runner = Runner(config)
            runner.run()

            wf = real_workflows[0]
            # active_stash must be 0
            assert wf.context.state_get("active_stash") == 0
            # CACHE CLEANUP VERIFICATION
            assert wf.cache.get_bucket("0") is None


def test_runner_partial_dag_failure(tmp_audio, tmp_path):  # noqa: ARG001
    """
    Verifies cleanup when only a subset of the DAG is enabled and it fails.
    Scenario: Only Transcription enabled, and it fails.
    """
    config = AppConfig(
        input=LocalInputConfig(paths=[tmp_path]),
        diarization=DiarizationConfig(enabled=False),
        transcription=TranscriptionConfig(enabled=True),
        alignment=AlignmentConfig(enabled=False),
        normalizer=NormalizerConfig(enabled=False),
        log_level="ERROR",
        core_log_level="ERROR",
    )

    with (
        patch(
            "tadween_whisperx.components.loader.handler.TorchCodecHandler.run"
        ) as mock_loader_run,
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.run",
            side_effect=RuntimeError("Standalone transcription failed"),
        ) as mock_transcription_run,  # noqa: F841
        patch(
            "tadween_whisperx.components.transcription.handler.TranscriptionHandler.warmup"
        ),
        patch("tadween_whisperx.components.throttle.get_config", return_value=config),
    ):
        mock_loader_run.return_value = AudioLoaderOutput(
            audio_array=np.array([0.1, 0.2], dtype=np.float32)
        )

        real_workflows = []
        original_build = WorkflowBuilder.build

        def wrapped_build(self):
            wf = original_build(self)
            real_workflows.append(wf)
            return wf

        with patch(
            "tadween_whisperx.builder.WorkflowBuilder.build",
            side_effect=wrapped_build,
            autospec=True,
        ):
            runner = Runner(config)
            runner.run()

            wf = real_workflows[0]
            assert wf.context.state_get("active_stash") == 0
            assert wf.cache.get_bucket("0") is None
