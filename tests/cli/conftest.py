import pytest
from typer.testing import CliRunner

import tadween_whisperx.config as config_module
from tadween_whisperx.cli import app
from tadween_whisperx.cli.config import Config


def _patch_user_config(tmp_path):
    """Patch USER_CONFIG_FILE to a temp path; return that path."""
    config_file = tmp_path / "config.yaml"
    original = config_module.USER_CONFIG_FILE
    config_module.USER_CONFIG_FILE = config_file
    return config_file, original


def _restore_user_config(original):
    """Restore USER_CONFIG_FILE to its original value."""
    config_module.USER_CONFIG_FILE = original


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_app():
    return app


@pytest.fixture
def config_typer():
    return Config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path):
    """Ensure every CLI test uses an isolated config file."""
    config_file, original = _patch_user_config(tmp_path)
    yield config_file
    _restore_user_config(original)
