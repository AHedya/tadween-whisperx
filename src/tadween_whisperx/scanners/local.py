from collections.abc import Generator

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import LocalInputConfig
from tadween_whisperx.scanners.base import (
    SUPPORTED_AUDIO_EXTENSIONS,
    BaseScanner,
    ScanResult,
)


class LocalScanner(BaseScanner[LocalInputConfig]):
    def scan(self) -> Generator[ScanResult, None, None]:
        self.logger.info(f"Scanning local paths: {self.config.paths}")
        for path in dict.fromkeys(self.config.paths):
            if path.is_file():
                if path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                    self.logger.debug(f"Found file: {path}")
                    yield ScanResult(
                        artifact_id=path.name,
                        file_path=str(path),
                        task_input=AudioLoaderInput(file_path=path),
                    )
            elif path.is_dir():
                self.logger.info(f"Scanning directory: {path}")
                for file in path.rglob("*"):
                    if (
                        file.is_file()
                        and file.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
                    ):
                        self.logger.debug(f"Found file in directory: {file}")
                        yield ScanResult(
                            artifact_id=file.name,
                            file_path=file,
                            task_input=AudioLoaderInput(file_path=file),
                        )
