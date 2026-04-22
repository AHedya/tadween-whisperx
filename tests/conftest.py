from pathlib import Path

import pytest
import yaml

from tadween_whisperx.config import (
    DEFAULT_CONFIG_FILE,
    AppConfig,
)


@pytest.fixture
def tmp_config_dir(tmp_path: Path):
    """Isolated config directory that patches USER_CONFIG_FILE for all tests."""
    import tadween_whisperx.config as config_module

    config_dir = tmp_path / "tadween-whisperx"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    original = config_module.USER_CONFIG_FILE
    config_module.USER_CONFIG_FILE = config_file
    yield config_file
    config_module.USER_CONFIG_FILE = original


@pytest.fixture(scope="session")
def default_config_data() -> dict:
    """Parsed default config.yaml as a dict."""
    with DEFAULT_CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def fresh_config() -> AppConfig:
    """A WhisperXConfig with all defaults (no profiles, no active)."""
    return AppConfig()
