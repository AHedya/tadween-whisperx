import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from tadween_whisperx.config import (
    AppConfig,
    ConfigError,
    JsonRepoConfig,
    LocalInputConfig,
    RepoProfiles,
    S3InputConfig,
    S3RepoConfig,
    load_config,
    redact_secrets,
    reset_config,
    save_config,
)


class TestJsonRepoConfig:
    def test_default_path_is_cwd_repo(self):
        config = JsonRepoConfig()
        assert Path.cwd() == config.path.parent

    def test_type_literal(self):
        config = JsonRepoConfig()
        assert config.type == "json"

    def test_custom_path(self, tmp_path: Path):
        custom = tmp_path / "my-data"
        config = JsonRepoConfig(path=custom)
        assert config.path == custom

    def test_existing_path_no_error(self, tmp_path: Path):
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        config = JsonRepoConfig(path=repo_path)
        assert config.path == repo_path


class TestS3RepoConfig:
    def test_required_fields(self):
        config = S3RepoConfig(
            bucket="my-bucket",
            aws_access_key_id="AKIA123",
            aws_secret_access_key="secret",
        )
        assert config.bucket == "my-bucket"
        assert config.aws_access_key_id == "AKIA123"
        assert config.aws_secret_access_key == "secret"

    def test_optional_fields_default_none(self):
        config = S3RepoConfig(
            bucket="my-bucket",
            aws_access_key_id="AKIA123",
            aws_secret_access_key="secret",
        )
        assert config.prefix is None
        assert config.aws_session_token is None
        assert config.endpoint_url is None

    def test_region_default(self):
        config = S3RepoConfig(
            bucket="b",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        assert config.region_name == "us-east-1"

    def test_type_literal(self):
        config = S3RepoConfig(
            bucket="b",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        assert config.type == "s3"

    def test_all_fields(self):
        config = S3RepoConfig(
            bucket="bucket",
            prefix="pre/",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            aws_session_token="token",
            endpoint_url="http://localhost:9000",
            region_name="eu-west-1",
        )
        assert config.prefix == "pre/"
        assert config.aws_session_token == "token"
        assert config.endpoint_url == "http://localhost:9000"
        assert config.region_name == "eu-west-1"

    def test_to_s3_client_config(self):
        config = S3RepoConfig(
            bucket="bucket",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            endpoint_url="http://localhost:9000",
        )
        s3_cfg = config.to_s3_client_config
        assert s3_cfg.access_key == "key"
        assert s3_cfg.secret_key == "secret"
        assert s3_cfg.endpoint_url == "http://localhost:9000"


class TestRepoProfiles:
    def test_empty_profiles(self):
        profiles = RepoProfiles()
        assert profiles.active is None
        assert profiles.profiles == {}

    def test_get_active_none_raises(self):
        profiles = RepoProfiles()
        with pytest.raises(ConfigError, match="No active repo profile"):
            profiles.get_active()

    def test_get_active_missing_raises(self):
        profiles = RepoProfiles(active="nonexistent", profiles={})
        with pytest.raises(ConfigError, match="not found in profiles"):
            profiles.get_active()

    def test_get_active_json(self, tmp_path: Path):
        json_config = JsonRepoConfig(path=tmp_path / "repo")
        profiles = RepoProfiles(
            active="local",
            profiles={"local": json_config},
        )
        result = profiles.get_active()
        assert isinstance(result, JsonRepoConfig)
        assert result.type == "json"

    def test_get_active_s3(self):
        s3_config = S3RepoConfig(
            bucket="b",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        profiles = RepoProfiles(
            active="remote",
            profiles={"remote": s3_config},
        )
        result = profiles.get_active()
        assert isinstance(result, S3RepoConfig)
        assert result.type == "s3"

    def test_discriminator_json(self, tmp_path: Path):
        profiles = RepoProfiles(
            active="local",
            profiles={
                "local": {"type": "json", "path": str(tmp_path / "repo")},
            },
        )
        assert isinstance(profiles.profiles["local"], JsonRepoConfig)

    def test_discriminator_s3(self):
        profiles = RepoProfiles(
            active="remote",
            profiles={
                "remote": {
                    "type": "s3",
                    "bucket": "b",
                    "aws_access_key_id": "k",
                    "aws_secret_access_key": "s",
                },
            },
        )
        assert isinstance(profiles.profiles["remote"], S3RepoConfig)

    def test_multiple_profiles(self, tmp_path: Path):
        json_config = JsonRepoConfig(path=tmp_path / "repo")
        s3_config = S3RepoConfig(
            bucket="b",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        profiles = RepoProfiles(
            active="local",
            profiles={"local": json_config, "remote": s3_config},
        )
        assert len(profiles.profiles) == 2
        assert isinstance(profiles.get_active(), JsonRepoConfig)

    def test_switch_active(self, tmp_path: Path):
        json_config = JsonRepoConfig(path=tmp_path / "repo")
        s3_config = S3RepoConfig(
            bucket="b",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        profiles = RepoProfiles(
            active="local",
            profiles={"local": json_config, "remote": s3_config},
        )
        profiles.active = "remote"
        assert isinstance(profiles.get_active(), S3RepoConfig)


class TestWhisperXConfig:
    def test_defaults(self):
        config = AppConfig()
        assert config.repo.active is None
        assert config.repo.profiles == {}
        assert config.input is None
        assert (
            config.diarization.model_name == "pyannote/speaker-diarization-community-1"
        )
        assert config.transcription.model == "large-v3"
        assert config.alignment.enabled is False
        assert config.normalizer.enabled is True

    def test_from_dict_with_profiles(self, tmp_path: Path):
        data = {
            "repo": {
                "active": "local",
                "profiles": {
                    "local": {"type": "json", "path": str(tmp_path / "repo")},
                },
            },
            "diarization": {"enabled": False},
            "transcription": {"enabled": True},
            "alignment": {"enabled": False},
            "normalizer": {"enabled": False},
        }
        config = AppConfig(**data)
        assert config.repo.active == "local"
        assert isinstance(config.repo.profiles["local"], JsonRepoConfig)


class TestLoadConfig:
    def test_load_fallback_to_default(self, tmp_config_dir):
        config = load_config()
        assert config.repo.active == "default"

    def test_load_from_user_file(self, tmp_config_dir):

        original = AppConfig()
        original.repo.profiles["json"] = JsonRepoConfig(
            path=tmp_config_dir.parent / "repo"
        )
        original.repo.active = "json"
        save_config(original)

        loaded = load_config()
        assert loaded.repo.active == "json"
        assert "json" in loaded.repo.profiles

    def test_load_corrupt_user_falls_back(self, tmp_config_dir):
        tmp_config_dir.write_text("::invalid yaml:::{{", encoding="utf-8")
        config = load_config()
        assert config.repo.active == "default"


class TestSaveConfig:
    def test_save_creates_file(self, tmp_config_dir):
        config = AppConfig()
        path = save_config(config)
        assert path == tmp_config_dir
        assert tmp_config_dir.exists()

    def test_roundtrip(self, tmp_config_dir, tmp_path: Path):
        json_config = JsonRepoConfig(path=tmp_path / "repo")
        s3_config = S3RepoConfig(
            bucket="my-bucket",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            endpoint_url="http://localhost:9000",
        )
        original = AppConfig()
        original.repo.profiles["local"] = json_config
        original.repo.profiles["remote"] = s3_config
        original.repo.active = "local"

        save_config(original)
        loaded = load_config()

        assert loaded.repo.active == "local"
        assert isinstance(loaded.repo.profiles["local"], JsonRepoConfig)
        assert isinstance(loaded.repo.profiles["remote"], S3RepoConfig)
        assert loaded.repo.profiles["remote"].bucket == "my-bucket"


class TestResetConfig:
    def test_reset_creates_file(self, tmp_config_dir):
        path = reset_config()
        assert path == tmp_config_dir
        assert tmp_config_dir.exists()

    def test_reset_overwrites(self, tmp_config_dir):
        reset_config()
        assert tmp_config_dir.exists()

        content = yaml.safe_load(tmp_config_dir.read_text(encoding="utf-8"))
        assert content["repo"]["active"] == "default"

        reset_config()
        content2 = yaml.safe_load(tmp_config_dir.read_text(encoding="utf-8"))
        assert content2["repo"]["active"] == "default"


class TestRedactSecrets:
    def test_redact_masks_secrets(self):
        data = {
            "aws_secret_access_key": "my-secret-key",
            "token": "my-token",
            "aws_session_token": "my-session",
            "bucket": "my-bucket",
        }
        result = redact_secrets(data)
        assert result["aws_secret_access_key"] == "***"
        assert result["token"] == "***"
        assert result["aws_session_token"] == "***"
        assert result["bucket"] == "my-bucket"

    def test_redact_preserves_non_secrets(self):
        data = {"bucket": "my-bucket", "region_name": "us-east-1"}
        result = redact_secrets(data)
        assert result == data

    def test_redact_nested(self):
        data = {
            "profiles": {
                "remote": {
                    "type": "s3",
                    "aws_secret_access_key": "my-key",
                    "bucket": "b",
                }
            }
        }
        result = redact_secrets(data)
        assert result["profiles"]["remote"]["aws_secret_access_key"] == "***"
        assert result["profiles"]["remote"]["bucket"] == "b"

    def test_redact_does_not_mutate_original(self):
        data = {"aws_secret_access_key": "my-secret", "bucket": "b"}
        original = copy.deepcopy(data)
        redact_secrets(data)
        assert data == original


class TestLocalInputConfig:
    def test_defaults(self):
        config = LocalInputConfig()
        assert config.type == "local"
        assert config.paths == []

    def test_with_paths(self, tmp_path: Path):
        p1 = tmp_path / "a.wav"
        p2 = tmp_path / "b.mp3"
        p1.touch()
        p2.touch()
        config = LocalInputConfig(paths=[p1, p2])
        assert config.paths == [p1, p2]

    def test_discriminator(self):
        config = AppConfig.model_validate({"input": {"type": "local"}})
        assert isinstance(config.input, LocalInputConfig)


class TestS3InputConfig:
    def test_required_fields(self):
        config = S3InputConfig(
            bucket="b",
            prefix="audio/",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        assert config.type == "s3"
        assert config.bucket == "b"
        assert config.prefix == "audio/"

    def test_prefix_empty_rejected(self):
        with pytest.raises(ConfigError, match="non-empty"):
            S3InputConfig(
                bucket="b", prefix="", aws_access_key_id="k", aws_secret_access_key="s"
            )

    def test_prefix_whitespace_rejected(self):
        with pytest.raises(ConfigError, match="non-empty"):
            S3InputConfig(
                bucket="b",
                prefix="  ",
                aws_access_key_id="k",
                aws_secret_access_key="s",
            )

    def test_prefix_missing_rejected(self):

        with pytest.raises(ValidationError):
            S3InputConfig(bucket="b", aws_access_key_id="k", aws_secret_access_key="s")

    def test_prefix_none_rejected(self):

        with pytest.raises(ValidationError):
            S3InputConfig(
                bucket="b",
                prefix=None,
                aws_access_key_id="k",
                aws_secret_access_key="s",
            )

    def test_optional_fields_default(self):
        config = S3InputConfig(
            bucket="b",
            prefix="audio/",
            aws_access_key_id="k",
            aws_secret_access_key="s",
        )
        assert config.aws_session_token is None
        assert config.endpoint_url is None
        assert config.region_name == "us-east-1"
        assert config.keep_downloaded is False

    def test_all_fields(self, tmp_path: Path):
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()
        config = S3InputConfig(
            bucket="my-bucket",
            prefix="data/",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            aws_session_token="token",
            endpoint_url="http://localhost:9000",
            region_name="eu-west-1",
            download_path=download_dir,
            keep_downloaded=True,
        )
        assert config.prefix == "data/"
        assert config.aws_session_token == "token"
        assert config.endpoint_url == "http://localhost:9000"
        assert config.region_name == "eu-west-1"
        assert config.download_path == download_dir
        assert config.keep_downloaded is True

    def test_discriminator(self):
        config = AppConfig.model_validate(
            {
                "input": {
                    "type": "s3",
                    "bucket": "b",
                    "prefix": "audio/",
                    "aws_access_key_id": "k",
                    "aws_secret_access_key": "s",
                }
            }
        )
        assert isinstance(config.input, S3InputConfig)


class TestInputConfigUnion:
    def test_local_from_dict(self):
        config = AppConfig.model_validate({"input": {"type": "local"}})
        assert isinstance(config.input, LocalInputConfig)

    def test_s3_from_dict(self):
        config = AppConfig.model_validate(
            {
                "input": {
                    "type": "s3",
                    "bucket": "b",
                    "prefix": "audio/",
                    "aws_access_key_id": "k",
                    "aws_secret_access_key": "s",
                }
            }
        )
        assert isinstance(config.input, S3InputConfig)

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            AppConfig.model_validate({"input": {"type": "ftp"}})

    def test_s3_without_prefix_rejected_in_union(self):
        with pytest.raises(ValidationError):
            AppConfig.model_validate(
                {
                    "input": {
                        "type": "s3",
                        "bucket": "b",
                        "aws_access_key_id": "k",
                        "aws_secret_access_key": "s",
                    }
                }
            )
