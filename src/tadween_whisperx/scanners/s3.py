import shutil
from collections.abc import Generator
from pathlib import Path

import boto3
from tadween_core.handler.defaults.s3_downloader import S3DownloadInput
from tadween_core.repo.s3 import preflight_check

from tadween_whisperx.config import S3InputConfig
from tadween_whisperx.scanners.base import (
    SUPPORTED_AUDIO_EXTENSIONS,
    BaseScanner,
    ScanResult,
)


class S3Scanner(BaseScanner[S3InputConfig]):
    def __init__(self, config: S3InputConfig):
        super().__init__(config)
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            aws_session_token=config.aws_session_token,
            region_name=config.region_name,
        )
        preflight_check(self._client, config.bucket, config.prefix, logger=self.logger)

    def scan(
        self,
        include: str | list[str] | None = None,
        exclude: str | list[str] | None = None,
    ) -> Generator[ScanResult, None, None]:
        s3_cfg = self.config
        self.logger.info(
            f"Scanning S3 bucket '{s3_cfg.bucket}' with prefix '{s3_cfg.prefix}'"
        )
        paginator = self._client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=s3_cfg.bucket, Prefix=s3_cfg.prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if Path(
                    key
                ).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and self.matches_filters(
                    key, include, exclude
                ):
                    self.logger.debug(f"Found S3 object: {key}")
                    local_path = self.config.download_path / Path(key).name
                    yield ScanResult(
                        artifact_id=key.replace("/", "_"),
                        file_path=key,
                        task_input=S3DownloadInput(
                            bucket=s3_cfg.bucket,
                            key=key,
                            local_path=local_path,
                        ),
                    )

    def close(self):
        self._client.close()
        if not self.config.keep_downloaded:
            shutil.rmtree(self.config.download_path, ignore_errors=True)
