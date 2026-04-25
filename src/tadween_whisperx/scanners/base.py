import fnmatch
import logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel
from tadween_core.handler.defaults.s3_downloader import S3DownloadInput

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import BaseInputConfig

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".flac", ".opus"})

T = TypeVar("T", bound=BaseInputConfig)


class ScanResult(BaseModel):
    artifact_id: str
    file_path: Path
    task_input: AudioLoaderInput | S3DownloadInput


class BaseScanner(ABC, Generic[T]):
    def __init__(self, config: T):
        self.config = config
        self.logger = logging.getLogger(
            f"tadween_whisperx.scanner.{self.__class__.__name__.lower()}"
        )

    @classmethod
    def matches_filters(
        cls,
        name: str,
        include: str | list[str] | None = None,
        exclude: str | list[str] | None = None,
    ) -> bool:
        include_list = [include] if isinstance(include, str) else (include or [])
        exclude_list = [exclude] if isinstance(exclude, str) else (exclude or [])

        if include_list:
            if not any(fnmatch.fnmatch(name, pattern) for pattern in include_list):
                return False
        if exclude_list:
            if any(fnmatch.fnmatch(name, pattern) for pattern in exclude_list):
                return False
        return True

    @abstractmethod
    def scan(
        self,
        include: str | list[str] | None = None,
        exclude: str | list[str] | None = None,
    ) -> Generator[ScanResult, None, None]: ...

    def close(self):
        pass
