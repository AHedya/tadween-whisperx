from pathlib import Path

from typer.testing import CliRunner

from tadween_whisperx.cli import app
from tadween_whisperx.config import LocalInputConfig, S3InputConfig, load_config


class TestConfigInputLocal:
    def test_set_local_input(self, runner: CliRunner, isolated_config, tmp_path: Path):
        file1 = tmp_path / "audio1.wav"
        file2 = tmp_path / "audio2.mp3"
        file1.touch()
        file2.touch()

        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            ["config", "input", "local", str(file1), str(file2)],
        )
        assert result.exit_code == 0
        assert "local paths" in result.output
        config = load_config()
        assert isinstance(config.input, LocalInputConfig)
        assert len(config.input.paths) == 2

    def test_overwrites_previous_input(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):

        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "input", "local", str(tmp_path / "a.wav")],
        )
        result = runner.invoke(
            app,
            ["config", "input", "local", str(tmp_path / "b.mp3")],
        )
        assert result.exit_code == 0
        config = load_config()
        assert isinstance(config.input, LocalInputConfig)
        assert len(config.input.paths) == 1


class TestConfigInputS3:
    def test_s3_input_with_prefix(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "input",
                "s3",
                "my-bucket",
                "--prefix",
                "audio/",
                "--access-key",
                "AKIA123",
                "--secret-key",
                "secret123",
            ],
        )
        assert result.exit_code == 0
        assert "my-bucket" in result.output
        assert "audio/" in result.output
        config = load_config()
        assert isinstance(config.input, S3InputConfig)
        assert config.input.bucket == "my-bucket"
        assert config.input.prefix == "audio/"
        assert config.input.aws_access_key_id == "AKIA123"

    def test_s3_input_prefix_required(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "input",
                "s3",
                "my-bucket",
                "--access-key",
                "k",
                "--secret-key",
                "s",
            ],
        )
        assert result.exit_code != 0

    def test_s3_input_all_options(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "input",
                "s3",
                "my-bucket",
                "--prefix",
                "data/",
                "--access-key",
                "k",
                "--secret-key",
                "s",
                "--session-token",
                "tok",
                "--endpoint-url",
                "http://localhost:9000",
                "--region",
                "eu-west-1",
                "--download-path",
                str(download_dir),
                "--keep-downloaded",
                "--max-retries",
                "5",
                "--multipart-threshold-mb",
                "32",
                "--max-workers",
                "8",
                "--max-concurrency-per-file",
                "4",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert isinstance(config.input, S3InputConfig)
        assert config.input.prefix == "data/"
        assert config.input.aws_session_token == "tok"
        assert config.input.endpoint_url == "http://localhost:9000"
        assert config.input.region_name == "eu-west-1"
        assert config.input.keep_downloaded is True
        assert config.input.max_retries == 5
        assert config.input.multipart_threshold_mb == 32
        assert config.input.max_workers == 8
        assert config.input.max_concurrency_per_file == 4

    def test_s3_input_overwrites_local(self, runner: CliRunner, isolated_config):

        runner.invoke(app, ["config", "init"])
        runner.invoke(app, ["config", "input", "local", "/some/path"])
        config = load_config()
        assert isinstance(config.input, LocalInputConfig)

        result = runner.invoke(
            app,
            [
                "config",
                "input",
                "s3",
                "b",
                "--prefix",
                "p/",
                "--access-key",
                "k",
                "--secret-key",
                "s",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert isinstance(config.input, S3InputConfig)

    def test_s3_default_region(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "input",
                "s3",
                "b",
                "--prefix",
                "p/",
                "--access-key",
                "k",
                "--secret-key",
                "s",
            ],
        )
        config = load_config()
        assert config.input.region_name == "us-east-1"

    def test_s3_bucket_required(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            ["config", "input", "s3"],
        )
        assert result.exit_code != 0
