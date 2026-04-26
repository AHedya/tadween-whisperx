import fnmatch
import hashlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Generic, TypeVar
from urllib.parse import quote_plus

from pydantic import BaseModel
from tadween_core.handler.defaults.downloader import DownloadInput
from tadween_core.handler.defaults.s3_downloader import S3DownloadInput

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import BaseInputConfig

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".flac", ".opus"})


def generate_artifact_id(canonical_uri: str, filename: str) -> str:
    """
    Generates a deterministic, filesystem-safe artifact ID.

    Args:
        canonical_uri: A standardized string representing the exact location.
        filename: The original filename to include in the ID.

    Returns:
        A unique, sanitized string: {hash_of_canonical_uri}_{sanitized_filename}
    """
    uri_hash = hashlib.md5(canonical_uri.encode("utf-8")).hexdigest()[:8]

    # Sanitize the filename to ensure it's safe for any repository backend
    safe_filename = quote_plus(filename)

    return f"{uri_hash}_{safe_filename}"


T = TypeVar("T", bound=BaseInputConfig)


class ScanResult(BaseModel):
    artifact_id: str
    source: str
    task_input: AudioLoaderInput | S3DownloadInput | DownloadInput


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
