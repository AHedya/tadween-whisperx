from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from pyannote.core.segment import Segment
from pytest_mock.plugin import MockerFixture

import tadween_whisperx.config as config_module
from tadween_whisperx.components.alignment.schema import AlignmentOutput
from tadween_whisperx.components.diarization.schema import DiarizationOutput
from tadween_whisperx.components.loader.handler import AudioLoaderOutput
from tadween_whisperx.components.transcription.schema import TranscriptionOutput
from tadween_whisperx.config import (
    DEFAULT_CONFIG_FILE,
    AppConfig,
)


@pytest.fixture
def tmp_config_dir(tmp_path: Path):
    """Isolated config directory that patches USER_CONFIG_FILE for all tests."""

    config_dir = tmp_path / "tadween-whisperx"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    original = config_module.USER_CONFIG_FILE
    config_module.USER_CONFIG_FILE = config_file
    config_module._GLOBAL_CONFIG = None  # Clear global config
    yield config_file
    config_module.USER_CONFIG_FILE = original
    config_module._GLOBAL_CONFIG = None  # Clear global config again


@pytest.fixture(scope="session")
def default_config_data() -> dict:
    """Parsed default config.yaml as a dict."""
    with DEFAULT_CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def fresh_config() -> AppConfig:
    """A WhisperXConfig with all defaults (no profiles, no active)."""
    return AppConfig()


@pytest.fixture
def sample_audio(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.touch()
    return audio_file


@pytest.fixture
def mock_handlers(mocker: MockerFixture):
    mock_loader_run = mocker.patch(
        "tadween_whisperx.components.loader.handler.TorchCodecHandler.run"
    )
    mock_transcription_run = mocker.patch(
        "tadween_whisperx.components.transcription.handler.TranscriptionHandler.run"
    )
    mocker.patch(
        "tadween_whisperx.components.transcription.handler.TranscriptionHandler.warmup"
    )
    mock_diarization_run = mocker.patch(
        "tadween_whisperx.components.diarization.handler.DiarizationHandler.run"
    )
    mocker.patch(
        "tadween_whisperx.components.diarization.handler.DiarizationHandler.warmup"
    )
    mock_alignment_run = mocker.patch(
        "tadween_whisperx.components.alignment.handler.AlignmentHandler.run"
    )
    mocker.patch(
        "tadween_whisperx.components.alignment.handler.AlignmentHandler.warmup"
    )

    # Set default returns
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
                "words": [{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}],
            }
        ],
        word_segments=[{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.9}],
    )

    return {
        "loader": mock_loader_run,
        "transcription": mock_transcription_run,
        "diarization": mock_diarization_run,
        "alignment": mock_alignment_run,
    }
