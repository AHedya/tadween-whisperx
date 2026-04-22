from pathlib import Path

import typer
from rich.console import Console

from tadween_whisperx.config import (
    LocalInputConfig,
    S3InputConfig,
    load_config,
    save_config,
)

app = typer.Typer(help="Configure input settings")
console = Console()


@app.command("local")
def set_local(
    paths: list[Path] = typer.Argument(..., help="List of file or directory paths."),
):
    """Set input source to local paths."""
    config = load_config()
    config.input = LocalInputConfig(paths=paths)
    save_config(config)
    console.print(
        f"[green]Input set to local paths: {', '.join(str(p) for p in paths)}[/green]"
    )


@app.command("s3")
def set_s3(
    bucket: str = typer.Argument(..., help="S3 bucket name."),
    prefix: str = typer.Option(..., help="S3 key prefix (required)."),
    access_key: str = typer.Option(..., help="AWS access key."),
    secret_key: str = typer.Option(..., help="AWS secret key."),
    endpoint_url: str | None = typer.Option(None, help="S3 endpoint URL."),
    session_token: str | None = typer.Option(None, help="AWS session token."),
    region: str = typer.Option("us-east-1", help="AWS region."),
    download_path: Path | None = typer.Option(None, help="Local download directory."),
    keep_downloaded: bool = typer.Option(
        False, help="Keep downloaded files after processing."
    ),
    max_retries: int | None = typer.Option(None, help="Maximum S3 download retries."),
    multipart_threshold_mb: int | None = typer.Option(
        None, help="Multipart download threshold in MB."
    ),
    max_workers: int | None = typer.Option(
        None, help="Maximum workers for S3 downloads."
    ),
    max_concurrency_per_file: int | None = typer.Option(
        None, help="Maximum concurrency per file for S3 downloads."
    ),
):
    """Set input source to an S3 bucket."""
    config = load_config()
    s3_kwargs = {
        "bucket": bucket,
        "prefix": prefix,
        "endpoint_url": endpoint_url,
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "aws_session_token": session_token,
        "region_name": region,
        "keep_downloaded": keep_downloaded,
        "max_retries": max_retries,
        "multipart_threshold_mb": multipart_threshold_mb,
        "max_workers": max_workers,
        "max_concurrency_per_file": max_concurrency_per_file,
    }
    s3_kwargs = {k: v for k, v in s3_kwargs.items() if v is not None}
    if download_path is not None:
        s3_kwargs["download_path"] = download_path
    config.input = S3InputConfig(**s3_kwargs)
    save_config(config)
    console.print(f"[green]Input set to S3 bucket: {bucket} (prefix: {prefix})[/green]")
