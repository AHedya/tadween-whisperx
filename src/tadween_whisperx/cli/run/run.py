import logging
import time

import typer
from rich.console import Console
from tadween_core.logger import set_logger as set_core_logger

from tadween_whisperx._logging import set_logger
from tadween_whisperx.builder import WorkflowBuilder
from tadween_whisperx.config import (
    AppConfig,
)

console = Console()

# Disable model loading warnings and noisy logs
DISABLED_LOGGERS = ["whisperx", "lightning.pytorch", "pytorch_lightning"]

for logger_name in DISABLED_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def _execute_pipeline(config: AppConfig):

    if config.input is None:
        console.print(
            "[bold red]Error:[/bold red] No input source provided. "
            "Set input in config or use a subcommand (local/s3)."
        )
        raise typer.Exit(code=1)

    begin = time.perf_counter()

    set_logger(
        level=config.log_level,
        log_path=config.log_path,
    )
    set_core_logger(
        level=config.core_log_level,
        log_path=config.core_log_path,
    )

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

    finally:
        wf.close()
        scanner.close()
        console.print(
            f"[bold green]Pipeline finished.[/bold green] Time elapsed: [yellow]{time.perf_counter() - begin:.2f}s[/yellow]"
        )
