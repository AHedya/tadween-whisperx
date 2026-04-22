from pathlib import Path

import yaml
from typer.testing import CliRunner

from tadween_whisperx.cli import app
from tadween_whisperx.config import load_config


class TestConfigInit:
    def test_init_creates_config_file(self, runner: CliRunner, isolated_config):
        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 0
        assert isolated_config.exists()

    def test_init_prints_success(self, runner: CliRunner, isolated_config):
        result = runner.invoke(app, ["config", "init"])
        assert "Config initialized" in result.output

    def test_init_already_exists_no_force(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_force_overwrites(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "init", "--force"])
        assert result.exit_code == 0
        assert "Config initialized" in result.output


class TestConfigReset:
    def test_reset_creates_file(self, runner: CliRunner, isolated_config):
        result = runner.invoke(app, ["config", "reset"])
        assert result.exit_code == 0
        assert isolated_config.exists()

    def test_reset_prints_success(self, runner: CliRunner, isolated_config):
        result = runner.invoke(app, ["config", "reset"])
        assert "Config reset" in result.output

    def test_reset_overwrites_existing(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(app, ["config", "repo", "json"])
        result = runner.invoke(app, ["config", "reset"])
        assert result.exit_code == 0
        config = load_config()
        assert config.repo.active is None
        assert config.repo.profiles == {}


class TestConfigShow:
    def test_show_outputs_yaml(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert "repo" in parsed

    def test_show_redacts_secrets(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "super-secret",
            ],
        )
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "super-secret" not in result.output
        assert "***" in result.output

    def test_show_reveal_shows_secrets(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "super-secret",
            ],
        )
        result = runner.invoke(app, ["config", "show", "--reveal"])
        assert result.exit_code == 0
        assert "super-secret" in result.output

    def test_show_component_outputs_only_component(
        self, runner: CliRunner, isolated_config
    ):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "show", "--component", "transcription"])
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert "transcription" in parsed
        assert "repo" not in parsed
        assert "diarization" not in parsed

    def test_show_component_shortcuts(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "show", "-c", "tr"])
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert "transcription" in parsed
        assert "repo" not in parsed

    def test_show_multiple_values_and_deduplication(
        self, runner: CliRunner, isolated_config
    ):
        runner.invoke(app, ["config", "init"])
        # Mix of -c flag, shortcuts, and positional arguments with duplicates
        result = runner.invoke(app, ["config", "show", "-c", "repo", "di", "re"])
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert "repo" in parsed
        assert "diarization" in parsed
        assert len(parsed) == 2  # repo and diarization only

    def test_show_multiple_components(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app, ["config", "show", "-c", "transcription", "-c", "alignment"]
        )
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert "transcription" in parsed
        assert "alignment" in parsed
        assert "repo" not in parsed

    def test_show_invalid_component(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "show", "-c", "invalid_component"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output


class TestRepoJson:
    def test_json_creates_profile(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "my-repo")],
        )
        assert result.exit_code == 0
        config = load_config()
        assert "json" in config.repo.profiles
        assert config.repo.profiles["json"].type == "json"

    def test_json_sets_active(self, runner: CliRunner, isolated_config, tmp_path: Path):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        config = load_config()
        assert config.repo.active == "json"

    def test_json_custom_path(self, runner: CliRunner, isolated_config, tmp_path: Path):
        runner.invoke(app, ["config", "init"])
        custom_path = tmp_path / "custom-dir"
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(custom_path)],
        )
        config = load_config()
        assert config.repo.profiles["json"].path == custom_path

    def test_json_custom_name(self, runner: CliRunner, isolated_config, tmp_path: Path):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "json",
                "--name",
                "local-dev",
                "--path",
                str(tmp_path / "repo"),
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert "local-dev" in config.repo.profiles
        assert config.repo.active == "local-dev"

    def test_json_duplicate_no_force(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_json_duplicate_with_force(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo2"), "--force"],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.repo.profiles["json"].path == tmp_path / "repo2"


class TestRepoS3:
    def test_s3_creates_profile(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "my-bucket",
                "--aws-access-key-id",
                "AKIA123",
                "--aws-secret-access-key",
                "secret",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert "s3" in config.repo.profiles
        assert config.repo.profiles["s3"].type == "s3"
        assert config.repo.profiles["s3"].bucket == "my-bucket"

    def test_s3_sets_active(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
            ],
        )
        config = load_config()
        assert config.repo.active == "s3"

    def test_s3_all_options(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--prefix",
                "data/",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
                "--aws-session-token",
                "tok",
                "--endpoint-url",
                "http://localhost:9000",
                "--region",
                "eu-west-1",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        profile = config.repo.profiles["s3"]
        assert profile.prefix == "data/"
        assert profile.aws_session_token == "tok"
        assert profile.endpoint_url == "http://localhost:9000"
        assert profile.region_name == "eu-west-1"

    def test_s3_custom_name(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
                "--name",
                "s3-prod",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert "s3-prod" in config.repo.profiles
        assert config.repo.active == "s3-prod"

    def test_s3_duplicate_no_force(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
            ],
        )
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b2",
                "--aws-access-key-id",
                "k2",
                "--aws-secret-access-key",
                "s2",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_s3_duplicate_with_force(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "old-bucket",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
            ],
        )
        result = runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "new-bucket",
                "--aws-access-key-id",
                "k2",
                "--aws-secret-access-key",
                "s2",
                "--force",
            ],
        )
        assert result.exit_code == 0
        config = load_config()
        assert config.repo.profiles["s3"].bucket == "new-bucket"

    def test_s3_missing_required_options(self, runner: CliRunner, isolated_config):
        result = runner.invoke(app, ["config", "repo", "s3"])
        assert result.exit_code != 0


class TestRepoList:
    def test_list_empty(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "repo", "list"])
        assert result.exit_code == 0
        assert "No repo profiles configured" in result.output

    def test_list_shows_profiles(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(app, ["config", "repo", "list"])
        assert result.exit_code == 0
        assert "json" in result.output
        assert "type=json" in result.output

    def test_list_marks_active(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(app, ["config", "repo", "list"])
        assert "*" in result.output

    def test_list_no_active_warning(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        config = load_config()
        config.repo.active = None
        import tadween_whisperx.config as config_module

        config_module.save_config(config)

        result = runner.invoke(app, ["config", "repo", "list"])
        assert "No active profile" in result.output


class TestRepoSwitch:
    def test_switch_changes_active(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
                "--name",
                "s3-remote",
            ],
        )
        result = runner.invoke(app, ["config", "repo", "switch", "json"])
        assert result.exit_code == 0
        config = load_config()
        assert config.repo.active == "json"

    def test_switch_nonexistent(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(app, ["config", "repo", "switch", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestRepoRemove:
    def test_remove_deletes_profile(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "b",
                "--aws-access-key-id",
                "k",
                "--aws-secret-access-key",
                "s",
                "--name",
                "s3-remote",
            ],
        )
        result = runner.invoke(app, ["config", "repo", "switch", "s3-remote"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["config", "repo", "remove", "json"])
        assert result.exit_code == 0
        config = load_config()
        assert "json" not in config.repo.profiles

    def test_remove_nonexistent(self, runner: CliRunner, isolated_config):
        runner.invoke(app, ["config", "init"])
        result = runner.invoke(app, ["config", "repo", "remove", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_active_forbidden(
        self, runner: CliRunner, isolated_config, tmp_path: Path
    ):
        runner.invoke(app, ["config", "init"])
        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        result = runner.invoke(app, ["config", "repo", "remove", "json"])
        assert result.exit_code == 1
        assert "Cannot remove active profile" in result.output


class TestEndToEnd:
    def test_full_workflow(self, runner: CliRunner, isolated_config, tmp_path: Path):
        runner.invoke(app, ["config", "init"])
        config = load_config()
        assert config.repo.active is None

        runner.invoke(
            app,
            ["config", "repo", "json", "--path", str(tmp_path / "repo")],
        )
        config = load_config()
        assert config.repo.active == "json"
        assert "json" in config.repo.profiles

        runner.invoke(
            app,
            [
                "config",
                "repo",
                "s3",
                "--bucket",
                "my-bucket",
                "--aws-access-key-id",
                "key",
                "--aws-secret-access-key",
                "secret",
                "--name",
                "s3-prod",
            ],
        )
        config = load_config()
        assert config.repo.active == "s3-prod"
        assert "s3-prod" in config.repo.profiles
        assert "json" in config.repo.profiles

        result = runner.invoke(app, ["config", "repo", "list"])
        assert result.exit_code == 0
        assert "s3-prod" in result.output
        assert "json" in result.output

        runner.invoke(app, ["config", "repo", "switch", "json"])
        config = load_config()
        assert config.repo.active == "json"

        result = runner.invoke(app, ["config", "repo", "remove", "s3-prod"])
        assert result.exit_code == 0
        config = load_config()
        assert "s3-prod" not in config.repo.profiles

        runner.invoke(app, ["config", "reset"])
        config = load_config()
        assert config.repo.active is None
        assert config.repo.profiles == {}
