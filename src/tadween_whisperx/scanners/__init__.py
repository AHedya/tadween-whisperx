from tadween_whisperx.config import InputConfig
from tadween_whisperx.scanners.base import (
    SUPPORTED_AUDIO_EXTENSIONS,
    BaseScanner,
    ScanResult,
)

from .local import LocalScanner
from .s3 import S3Scanner


def create_scanner(config: InputConfig) -> BaseScanner:
    if config.type == "local":
        return LocalScanner(config)
    if config.type == "s3":
        return S3Scanner(config)
    raise ValueError(f"Unknown scanner type: {config.type}")


__all__ = [
    "BaseScanner",
    "LocalScanner",
    "S3Scanner",
    "ScanResult",
    "SUPPORTED_AUDIO_EXTENSIONS",
    "create_scanner",
]
