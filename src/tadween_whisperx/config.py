from __future__ import annotations

import copy
import logging
import shutil
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal

import platformdirs
import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from tadween_core.types.s3_config import S3ClientConfig

from tadween_whisperx.components.alignment.handler import (
    AlignmentConfig as AlignmentModelConfig,
)
from tadween_whisperx.components.diarization.handler import (
    ModelConfig as DiarizationModelConfig,
)
from tadween_whisperx.components.transcription.handler import TranscriptionModelConfig

_GLOBAL_CONFIG: AppConfig | None = None


APP_NAME = "tadween-whisperx"
CONFIG_NAME = "config.yaml"
USER_CONFIG_FILE = platformdirs.user_config_path(APP_NAME) / CONFIG_NAME
DEFAULT_CONFIG_FILE = files("tadween_whisperx.resources").joinpath(CONFIG_NAME)
logger = logging.getLogger("tadween_whisperx")

_SECRET_FIELDS = {"aws_secret_access_key", "token", "aws_session_token"}
_MASK = "***"


class ConfigError(Exception):
    pass


class FSRepoConfig(BaseModel):
    type: Literal["fs"] = "fs"
    path: Path | None = Field(default_factory=lambda: Path.cwd() / "tadweenx-fs-repo")

    @field_validator("path", mode="after")
    @classmethod
    def ensure_path_exists(cls, v: Path | None) -> Path:
        pth = v or Path.cwd() / f"tadweenx-{cls.model_fields['type'].default}-repo"
        return pth


class JsonRepoConfig(FSRepoConfig):
    type: Literal["json"] = "json"
    path: Path | None = Field(default_factory=lambda: Path.cwd() / "tadweenx-json-repo")


class S3RepoConfig(BaseModel):
    type: Literal["s3"] = "s3"
    bucket: str
    prefix: str | None = None
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str | None = None
    endpoint_url: str | None = None
    region_name: str = "us-east-1"

    @property
    def to_s3_client_config(self):

        return S3ClientConfig(
            access_key=self.aws_access_key_id,
            secret_key=self.aws_secret_access_key,
            session_token=self.aws_session_token,
            endpoint_url=self.endpoint_url,
            region=self.region_name,
        )


RepoConfig = Annotated[
    FSRepoConfig | JsonRepoConfig | S3RepoConfig, Field(discriminator="type")
]


class RepoProfiles(BaseModel):
    active: str | None = None
    profiles: dict[str, Annotated[RepoConfig, Field(discriminator="type")]] = Field(
        default_factory=dict
    )

    def get_active(self) -> FSRepoConfig | JsonRepoConfig | S3RepoConfig:
        if self.active is None:
            raise ConfigError(
                "No active repo profile. "
                "Run: tadween-whisperx config repo json or config repo s3"
            )
        if self.active not in self.profiles:
            raise ConfigError(
                f"Active profile '{self.active}' not found in profiles. "
                f"Available: {', '.join(self.profiles) or '(none)'}"
            )
        return self.profiles[self.active]


class DiarizationConfig(DiarizationModelConfig):
    enabled: bool = True
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 1,
        "name": "diarization_queue",
    }


class TranscriptionConfig(TranscriptionModelConfig):
    enabled: bool = True
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 1,
        "name": "transcription_queue",
    }


class AlignmentConfig(AlignmentModelConfig):
    enabled: bool = False
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 1,
        "name": "alignment_queue",
    }


class NormalizerConfig(BaseModel):
    enabled: bool = True
    allowed_chars: int = 3
    max_word_len: int = 16
    allowed_words: int = 3


class LoaderConfig(BaseModel):
    type: Literal["torchcodec", "av", "ffmpeg_stream"] = "torchcodec"
    max_stashed_files: int = 2
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 2,
        "name": "loader_queue",
    }


class BaseInputConfig(BaseModel):
    include: list[str] | str | None = None
    exclude: list[str] | str | None = None


class LocalInputConfig(BaseInputConfig):
    type: Literal["local"] = "local"
    paths: list[Path] = Field(default_factory=list)


class S3InputConfig(BaseInputConfig):
    type: Literal["s3"] = "s3"
    bucket: str
    prefix: str
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    endpoint_url: str | None = None
    region_name: str = "us-east-1"

    max_retries: int = 3
    multipart_threshold_mb: int = 16
    max_workers: int = 4
    max_concurrency_per_file: int = 2
    # queue
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 1,  # let internal pool handle concurrency.
        "name": "s3_input",
    }

    download_path: Path = Field(
        default_factory=lambda: Path(tempfile.mkdtemp(prefix="tadween-x_"))
    )
    keep_downloaded: bool = False

    @field_validator("prefix", mode="after")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        if not v.strip():
            raise ConfigError("S3InputConfig.prefix must be a non-empty string")
        return v


class HTTPInputConfig(BaseInputConfig):
    type: Literal["http"] = "http"
    urls: list[str] = Field(default_factory=list)

    max_retries: int = 3
    timeout_seconds: int = 300

    # queue
    task_queue: dict = {
        "executor": "thread",
        "max_workers": 2,
        "name": "http_input",
    }

    download_path: Path = Field(
        default_factory=lambda: Path(tempfile.mkdtemp(prefix="tadween-x_"))
    )
    keep_downloaded: bool = False


InputConfig = Annotated[
    LocalInputConfig | S3InputConfig | HTTPInputConfig, Field(discriminator="type")
]


class AppConfig(BaseSettings):
    repo: RepoProfiles = Field(default_factory=RepoProfiles)
    loader: LoaderConfig = Field(default_factory=LoaderConfig)
    input: InputConfig | None = Field(default=None)

    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    alignment: AlignmentConfig = Field(default_factory=AlignmentConfig)
    normalizer: NormalizerConfig = Field(default_factory=NormalizerConfig)

    log_level: str = "INFO"
    log_path: Path | None = None

    core_log_level: str = "INFO"
    core_log_path: Path | None = None

    def validate(self):
        if not self.diarization.enabled and not self.transcription.enabled:
            raise ConfigError(
                "Can't build an ASR pipeline without diarization nor transcription. Enable at least one."
            )

        if not self.transcription.enabled:
            if self.alignment.enabled:
                raise ConfigError(
                    "Can't align audio without transcription. Either enable transcription "
                    "or disable alignment "
                )
            if self.normalizer.enabled:
                raise ConfigError(
                    "Can't normalize audio without transcription. Either enable transcription "
                    "or disable normalization "
                )
        return self


def get_config() -> AppConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = load_config()
    return _GLOBAL_CONFIG


def set_config(config: AppConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config


def load_default_config() -> dict:
    if USER_CONFIG_FILE.exists():
        try:
            with USER_CONFIG_FILE.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                logger.debug(f"Loaded config from {USER_CONFIG_FILE}")
                return data
            logger.warning(
                "User config is not a valid YAML mapping. "
                "Falling back to package defaults."
            )
        except Exception as e:
            logger.warning(
                "Couldn't load user config. "
                f"Falling back to package defaults. Error: {e}"
            )

    logger.debug(f"Loading default config from {DEFAULT_CONFIG_FILE}")
    with DEFAULT_CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config() -> AppConfig:
    data = load_default_config()
    return AppConfig(**data)


def save_config(config: AppConfig) -> Path:
    global _GLOBAL_CONFIG
    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    with USER_CONFIG_FILE.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Saved config to {USER_CONFIG_FILE}")
    _GLOBAL_CONFIG = None
    return USER_CONFIG_FILE


def config_exists() -> bool:
    return USER_CONFIG_FILE.exists()


def reset_config() -> Path:
    global _GLOBAL_CONFIG
    USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEFAULT_CONFIG_FILE, USER_CONFIG_FILE)
    _GLOBAL_CONFIG = None
    return USER_CONFIG_FILE


def redact_secrets(data: dict) -> dict:
    result = copy.deepcopy(data)
    _redact_recursive(result)
    return result


def _redact_recursive(d: dict) -> None:
    for key, value in d.items():
        if key in _SECRET_FIELDS:
            d[key] = _MASK
        elif isinstance(value, dict):
            _redact_recursive(value)
