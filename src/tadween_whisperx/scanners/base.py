import logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel
from tadween_core.handler.defaults.s3_downloader import S3DownloadInput

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import InputConfig

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".flac", ".opus"})

T = TypeVar("T", bound=InputConfig)


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

    @abstractmethod
    def scan(self) -> Generator[ScanResult, None, None]: ...

    def close(self):
        pass
