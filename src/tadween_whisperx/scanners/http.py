import shutil
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

import requests
from tadween_core.handler.defaults.downloader import DownloadInput

from tadween_whisperx.config import HTTPInputConfig
from tadween_whisperx.scanners.base import (
    SUPPORTED_AUDIO_EXTENSIONS,
    BaseScanner,
    ScanResult,
)


class HTTPScanner(BaseScanner[HTTPInputConfig]):
    def scan(
        self,
        include: str | list[str] | None = None,
        exclude: str | list[str] | None = None,
    ) -> Generator[ScanResult, None, None]:
        self.logger.info(f"Scanning HTTP URLs: {self.config.urls}")
        for url in set(self.config.urls):
            parsed = urlparse(url)
            path = Path(parsed.path)
            name = path.name or "audio"
            ext = path.suffix.lower()

            # Check if it has a supported extension or if we should perform a HEAD check
            is_supported = ext in SUPPORTED_AUDIO_EXTENSIONS
            if not is_supported:
                self.logger.debug(
                    f"URL lacks recognized extension: {url}. Performing HEAD check..."
                )
                if self._check_is_audio(url):
                    is_supported = True
                else:
                    self.logger.warning(
                        f"URL rejected (not a recognized audio source): {url}"
                    )
                    continue

            if is_supported and self.matches_filters(name, include, exclude):
                self.logger.debug(f"Found HTTP URL: {url}")

                # Improved artifact_id: domain + hash of path to avoid collisions
                # path_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                # artifact_id = f"{parsed.netloc}_{path_hash}_{name}"

                artifact_id = name
                local_path = self.config.download_path / name

                if not local_path.suffix and not name.endswith(
                    tuple(SUPPORTED_AUDIO_EXTENSIONS)
                ):
                    # Optionally append a default suffix if missing to help downstream loaders
                    pass

                yield ScanResult(
                    artifact_id=artifact_id,
                    source=url,
                    task_input=DownloadInput(
                        url=url,
                        local_path=local_path,
                        timeout_seconds=self.config.timeout_seconds,
                        retries=self.config.max_retries,
                    ),
                )

    def _check_is_audio(self, url: str) -> bool:
        """Performs a HEAD request to check if Content-Type is audio."""
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()
                return content_type.startswith("audio/")
            return False
        except Exception as e:
            self.logger.error(f"HEAD request failed for {url}: {e}")
            return False

    def close(self):
        if not self.config.keep_downloaded:
            shutil.rmtree(self.config.download_path, ignore_errors=True)
