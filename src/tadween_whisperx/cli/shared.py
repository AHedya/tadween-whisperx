from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from tadween_whisperx.config import (
    AppConfig,
    HTTPInputConfig,
    LocalInputConfig,
    S3InputConfig,
    get_config,
)


def add_input_commands(
    app: typer.Typer,
    action: Callable[[AppConfig], None],
    local_help: str = "Use local files/directories.",
    s3_help: str = "Use S3 objects.",
    http_help: str = "Use HTTP URLs.",
) -> None:
    """Add local, s3, and http subcommands to a Typer app."""

    @app.command("local", help=local_help)
    def local(
        paths: Annotated[
            list[Path], typer.Argument(help="Files or directories to process")
        ],
        include: Annotated[
            list[str] | None, typer.Option("--include", help="Include patterns (glob)")
        ] = None,
        exclude: Annotated[
            list[str] | None, typer.Option("--exclude", help="Exclude patterns (glob)")
        ] = None,
    ) -> None:
        config = get_config()
        config.input = LocalInputConfig(paths=paths, include=include, exclude=exclude)
        action(config)

    @app.command("s3", help=s3_help)
    def s3(
        bucket: Annotated[str, typer.Argument(help="S3 bucket name")],
        prefix: Annotated[str, typer.Option(help="S3 prefix (folder path)")],
        access_key: Annotated[
            str | None, typer.Option("--access-key", help="AWS Access Key")
        ] = None,
        secret_key: Annotated[
            str | None, typer.Option("--secret-key", help="AWS Secret Key")
        ] = None,
        session_token: Annotated[
            str | None, typer.Option("--session-token", help="AWS Session Token")
        ] = None,
        endpoint_url: Annotated[
            str | None,
            typer.Option("--endpoint", "--endpoint-url", help="S3 Endpoint URL"),
        ] = None,
        region: Annotated[
            str | None, typer.Option("--region", help="AWS Region")
        ] = None,
        download_path: Annotated[
            Path | None,
            typer.Option("--download-path", help="Local download directory"),
        ] = None,
        keep: Annotated[
            bool,
            typer.Option(
                "--keep/--no-keep",
                "--keep-downloaded/--no-keep-downloaded",
                help="Whether to keep downloaded files",
            ),
        ] = False,
        include: Annotated[
            list[str] | None, typer.Option("--include", help="Include patterns (glob)")
        ] = None,
        exclude: Annotated[
            list[str] | None, typer.Option("--exclude", help="Exclude patterns (glob)")
        ] = None,
        max_retries: Annotated[
            int | None, typer.Option("--max-retries", help="Maximum download retries")
        ] = None,
        multipart_threshold: Annotated[
            int | None,
            typer.Option(
                "--multipart-threshold",
                "--multipart-threshold-mb",
                help="Multipart threshold in MB",
            ),
        ] = None,
        max_workers: Annotated[
            int | None, typer.Option("--max-workers", help="Maximum download workers")
        ] = None,
        max_concurrency: Annotated[
            int | None,
            typer.Option(
                "--max-concurrency",
                "--max-concurrency-per-file",
                help="Maximum concurrency per file",
            ),
        ] = None,
    ) -> None:
        config = get_config()

        updates = {
            "bucket": bucket,
            "prefix": prefix,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "aws_session_token": session_token,
            "endpoint_url": endpoint_url,
            "region_name": region,
            "keep_downloaded": keep,
            "download_path": download_path,
            "include": include,
            "exclude": exclude,
            "max_retries": max_retries,
            "multipart_threshold_mb": multipart_threshold,
            "max_workers": max_workers,
            "max_concurrency_per_file": max_concurrency,
        }
        updates = {k: v for k, v in updates.items() if v is not None}

        # Merge existing S3 config if available
        if isinstance(config.input, S3InputConfig):
            input_cfg = config.input.model_copy(update=updates)
        else:
            input_cfg = S3InputConfig.model_validate(updates)

        config.input = input_cfg
        action(config)

    @app.command("http", help=http_help)
    def http(
        urls: Annotated[list[str], typer.Argument(help="URLs to process")],
        include: Annotated[
            list[str] | None, typer.Option("--include", help="Include patterns (glob)")
        ] = None,
        exclude: Annotated[
            list[str] | None, typer.Option("--exclude", help="Exclude patterns (glob)")
        ] = None,
        download_path: Annotated[
            Path | None,
            typer.Option("--download-path", help="Local download directory"),
        ] = None,
        keep: Annotated[
            bool,
            typer.Option(
                "--keep/--no-keep",
                "--keep-downloaded/--no-keep-downloaded",
                help="Whether to keep downloaded files",
            ),
        ] = True,
        max_retries: Annotated[
            int | None, typer.Option("--max-retries", help="Maximum download retries")
        ] = None,
        timeout: Annotated[
            int | None, typer.Option("--timeout", help="Download timeout in seconds")
        ] = None,
    ) -> None:
        config = get_config()
        updates = {
            "urls": urls,
            "include": include,
            "exclude": exclude,
            "download_path": download_path,
            "keep_downloaded": keep,
            "max_retries": max_retries,
            "timeout_seconds": timeout,
        }
        updates = {k: v for k, v in updates.items() if v is not None}

        if isinstance(config.input, HTTPInputConfig):
            input_cfg = config.input.model_copy(update=updates)
        else:
            input_cfg = HTTPInputConfig.model_validate(updates)

        config.input = input_cfg
        action(config)
