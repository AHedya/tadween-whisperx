from collections.abc import Generator

from tadween_whisperx.components.loader.handler import AudioLoaderInput
from tadween_whisperx.config import LocalInputConfig
from tadween_whisperx.scanners.base import (
    SUPPORTED_AUDIO_EXTENSIONS,
    BaseScanner,
    ScanResult,
    generate_artifact_id,
)


class LocalScanner(BaseScanner[LocalInputConfig]):
    def scan(
        self,
        include: str | list[str] | None = None,
        exclude: str | list[str] | None = None,
    ) -> Generator[ScanResult, None, None]:
        self.logger.info(f"Scanning local paths: {self.config.paths}")
        for path in dict.fromkeys(self.config.paths):
            if path.is_file():
                if (
                    path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
                    and self.matches_filters(path.name, include, exclude)
                ):
                    self.logger.debug(f"Found file: {path}")
                    uri = path.absolute().as_uri()
                    artifact_id = self.config.id_map.get(
                        uri,
                        self.config.id_map.get(
                            str(path), generate_artifact_id(uri, path.name)
                        ),
                    )
                    yield ScanResult(
                        artifact_id=artifact_id,
                        source=str(path),
                        task_input=AudioLoaderInput(file_path=path),
                    )
            elif path.is_dir():
                self.logger.info(f"Scanning directory: {path}")
                for file in path.rglob("*"):
                    if (
                        file.is_file()
                        and file.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
                        and self.matches_filters(file.name, include, exclude)
                    ):
                        self.logger.debug(f"Found file in directory: {file}")
                        uri = file.absolute().as_uri()
                        artifact_id = self.config.id_map.get(
                            uri,
                            self.config.id_map.get(
                                str(file), generate_artifact_id(uri, file.name)
                            ),
                        )
                        yield ScanResult(
                            artifact_id=artifact_id,
                            source=str(file),
                            task_input=AudioLoaderInput(file_path=file),
                        )
