import logging
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tadween_whisperx._logging import set_logger
from tadween_whisperx.builder import WorkflowBuilder
from tadween_whisperx.config import (
    AppConfig,
    LocalInputConfig,
    S3InputConfig,
    load_config,
)

app = typer.Typer(help="Run the ASR pipeline.")
console = Console()

# Disable model loading warnings and noisy logs
DISABLED_LOGGERS = ["whisperx", "lightning.pytorch", "pytorch_lightning"]


def _execute_pipeline(config: AppConfig):
    """Internal helper to build and run the pipeline from a resolved config."""
    for logger_name in DISABLED_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)

    if config.input is None:
        console.print(
            "[bold red]Error:[/bold red] No input source provided. "
            "Set input in config or use a subcommand (local/s3)."
        )
        raise typer.Exit(code=1)

    begin = time.perf_counter()

    if config.log_path:
        set_logger(level=config.log_level, log_path=config.log_path)

    builder = WorkflowBuilder(config)
    wf = builder.build()
    scanner = builder.get_scanner()

    console.print("[bold blue]Starting Tadween WhisperX Pipeline[/bold blue]")
    console.print(f"Input type: [green]{config.input.type}[/green]")

    try:
        count = 0
        for i, result in enumerate(scanner.scan()):
            wf.submit(
                result.task_input,
                metadata={
                    "cache_key": str(i),
                    "file_name": str(result.file_path),
                    "artifact_id": result.artifact_id,
                },
            )
            count += 1

        if count == 0:
            console.print("[yellow]No files found to process.[/yellow]")
        else:
            console.print(
                f"Submitted [green]{count}[/green] tasks. Waiting for completion..."
            )

            # Wait for all tasks to finish if it's an InMemoryBroker
            if hasattr(wf.broker, "join"):
                wf.broker.join()

    finally:
        wf.close()
        scanner.close()
        console.print(
            f"[bold green]Pipeline finished.[/bold green] Time elapsed: [cyan]{time.perf_counter() - begin:.2f}s[/cyan]"
        )


@app.callback(invoke_without_command=True)
def run(ctx: typer.Context):
    """Run the ASR pipeline using the default configuration."""
    if ctx.invoked_subcommand is None:
        config = load_config()
        _execute_pipeline(config)


@app.command()
def local(
    paths: Annotated[
        list[Path], typer.Argument(help="Files or directories to process")
    ],
):
    """Run pipeline on local files/directories."""
    config = load_config()
    config.input = LocalInputConfig(paths=paths)
    _execute_pipeline(config)


@app.command()
def s3(
    bucket: Annotated[str, typer.Option(help="S3 bucket name")],
    prefix: Annotated[str, typer.Option(help="S3 prefix (folder path)")],
    access_key: Annotated[
        str | None, typer.Option("--access-key", help="AWS Access Key")
    ] = None,
    secret_key: Annotated[
        str | None, typer.Option("--secret-key", help="AWS Secret Key")
    ] = None,
    endpoint_url: Annotated[
        str | None, typer.Option("--endpoint", help="S3 Endpoint URL")
    ] = None,
    region: Annotated[str, typer.Option("--region", help="AWS Region")] = "us-east-1",
    download_path: Annotated[
        Path | None, typer.Option("--download-path", help="Local download directory")
    ] = None,
    keep: Annotated[
        bool,
        typer.Option("--keep/--no-keep", help="Whether to keep downloaded files"),
    ] = False,
):
    """Run pipeline on S3 objects."""
    config = load_config()

    # Merge existing S3 config if available to avoid re-typing everything
    if isinstance(config.input, S3InputConfig):
        input_cfg = config.input.model_copy(
            update={
                "bucket": bucket,
                "prefix": prefix,
                "aws_access_key_id": access_key or config.input.aws_access_key_id,
                "aws_secret_access_key": secret_key
                or config.input.aws_secret_access_key,
                "endpoint_url": endpoint_url or config.input.endpoint_url,
                "region_name": region,
                "keep_downloaded": keep,
            }
        )
        if download_path:
            input_cfg.download_path = download_path
    else:
        # Fallback to defaults for S3InputConfig if no base config is present
        # We need to handle required fields carefully
        input_cfg_data = {
            "bucket": bucket,
            "prefix": prefix,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
            "region_name": region,
            "keep_downloaded": keep,
        }
        if download_path:
            input_cfg_data["download_path"] = download_path

        # Filters None values so Pydantic defaults kick in
        input_cfg_data = {k: v for k, v in input_cfg_data.items() if v is not None}
        input_cfg = S3InputConfig.model_validate(input_cfg_data)

    config.input = input_cfg
    _execute_pipeline(config)
