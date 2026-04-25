import pytest
from typer.testing import CliRunner

from tadween_whisperx.cli import app
from tadween_whisperx.config import ConfigError, load_config


class TestConfigDiarization:
    def test_no_changes(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "diarization"])
        assert result.exit_code == 0
        assert "No changes provided" in result.output

    def test_update_enabled(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "diarization", "--no-enabled"])
        assert result.exit_code == 0
        assert "Diarization configuration updated" in result.output
        config = load_config()
        assert config.diarization.enabled is False

    def test_update_fields(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "diarization",
                "--device",
                "cpu",
                "--model-name",
                "custom",
                "--token",
                "abc",
                "--cache-dir",
                "/tmp/cache",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.diarization.device == "cpu"
        assert config.diarization.model_name == "custom"
        assert config.diarization.token == "abc"
        assert config.diarization.cache_dir == "/tmp/cache"


class TestConfigTranscription:
    def test_no_changes(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "transcription"])
        assert result.exit_code == 0
        assert "No changes provided" in result.output

    def test_update_enabled(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "transcription", "--no-enabled"])
        assert result.exit_code == 0
        # disabling transcription leads to no active nodes.
        with pytest.raises(ConfigError):
            config = load_config()
            config.validate()

    def test_update_fields(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "transcription",
                "--device",
                "cpu",
                "--model",
                "small",
                "--compute-type",
                "int8",
                "--language",
                "en",
                "--threads",
                "8",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.transcription.device == "cpu"
        assert config.transcription.model == "small"
        assert config.transcription.compute_type == "int8"
        assert config.transcription.language == "en"
        assert config.transcription.threads == 8


class TestConfigAlignment:
    def test_no_changes(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "alignment"])
        assert result.exit_code == 0
        assert "No changes provided" in result.output

    def test_update_enabled(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "alignment", "--enabled"])
        assert result.exit_code == 0
        config = load_config()
        assert config.alignment.enabled is True

    def test_update_fields(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "alignment",
                "--device",
                "cpu",
                "--model-name",
                "custom_align",
                "--language-code",
                "en",
                "--max-models",
                "2",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.alignment.device == "cpu"
        assert config.alignment.model_name == "custom_align"
        assert config.alignment.language_code == "en"
        assert config.alignment.max_models == 2


class TestConfigNormalizer:
    def test_no_changes(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "normalizer"])
        assert result.exit_code == 0
        assert "No changes provided" in result.output

    def test_update_enabled(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "normalizer", "--no-enabled"])
        assert result.exit_code == 0
        config = load_config()
        assert config.normalizer.enabled is False

    def test_update_fields(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "normalizer",
                "--allowed-chars",
                "5",
                "--max-word-len",
                "20",
                "--allowed-words",
                "10",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.normalizer.allowed_chars == 5
        assert config.normalizer.max_word_len == 20
        assert config.normalizer.allowed_words == 10


class TestConfigLoader:
    def test_no_changes(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "loader"])
        assert result.exit_code == 0
        assert "No changes provided" in result.output

    def test_update_fields(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "loader",
                "--type",
                "av",
                "--max-stashed-files",
                "5",
            ],
        )
        assert result.exit_code == 0
        assert "Loader configuration updated" in result.output
        config = load_config()
        assert config.loader.type == "av"
        assert config.loader.max_stashed_files == 5

    def test_invalid_type(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "loader",
                "--type",
                "invalid",
            ],
        )
        assert result.exit_code != 0
