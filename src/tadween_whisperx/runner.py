import logging
import time
from pathlib import Path

import typer
from rich.console import Console
from tadween_core.logger import set_logger as set_core_logger
from tadween_core.workflow import Workflow

from tadween_whisperx._logging import set_logger
from tadween_whisperx.builder import WorkflowBuilder
from tadween_whisperx.config import AppConfig, load_config
from tadween_whisperx.scanners import BaseScanner


class Runner:
    def __init__(
        self,
        config: AppConfig | Path | str | None = None,
        console: Console | None = None,
    ):
        if isinstance(config, AppConfig):
            self.config = config
        else:
            self.config = load_config(config)

        self.console = console or Console()
        self.builder = WorkflowBuilder(self.config)
        self.wf: Workflow | None = None
        self.scanner: BaseScanner | None = None
        self._start_time: float | None = None

        self._is_setup: bool = False

    def setup(self):
        """Initializes logging, validates configuration, and builds the workflow DAG."""
        if self._is_setup:
            return
        if self.config.input is None:
            self.console.print(
                "[bold red]Error:[/bold red] No input source provided. "
                "Set input in config or use a subcommand (local/s3)."
            )
            raise typer.Exit(code=1)

        self._start_time = time.perf_counter()

        set_logger(
            level=self.config.log_level,
            log_path=self.config.log_path,
        )
        set_core_logger(
            level=self.config.core_log_level,
            log_path=self.config.core_log_path,
        )
        DISABLED_LOGGERS = ["whisperx", "lightning.pytorch", "pytorch_lightning"]
        for i in DISABLED_LOGGERS:
            logging.getLogger(i).setLevel(logging.CRITICAL)

        self.builder.preflight_check()
        self.wf = self.builder.build()
        self.scanner = self.builder.get_scanner()
        self._is_setup = True

    def execute(self) -> int:
        """Scans for input artifacts and submits them to the workflow."""
        if not self.wf or not self.scanner:
            raise RuntimeError(
                "Runner must be set up before execution. Call setup() first."
            )

        self.console.print("[bold blue]Starting Tadween WhisperX Pipeline[/bold blue]")
        self.console.print(f"Input type: [green]{self.config.input.type}[/green]")

        count = 0
        for i, result in enumerate(
            self.scanner.scan(
                include=self.config.input.include, exclude=self.config.input.exclude
            )
        ):
            self.wf.submit(
                result.task_input,
                metadata={
                    "cache_key": str(i),
                    "file_name": str(result.source),
                    "artifact_id": result.artifact_id,
                    "id": result.artifact_id,
                },
            )
            count += 1

        if count == 0:
            self.console.print("[yellow]No files found to process.[/yellow]")
        else:
            self.console.print(
                f"Submitted [green]{count}[/green] tasks. Waiting for completion..."
            )
        return count

    def wait(self):
        """Waits for the workflow broker to finish all tasks."""
        if self.wf and hasattr(self.wf.broker, "join"):
            self.wf.broker.join()

    def close(self):
        """Closes the workflow and scanner, releasing resources."""
        if self.wf:
            self.wf.close()
        if self.scanner:
            self.scanner.close()

        if self._start_time:
            elapsed = time.perf_counter() - self._start_time
            self.console.print(
                f"[bold green]Pipeline finished.[/bold green] Time elapsed: [yellow]{elapsed:.2f}s[/yellow]"
            )

    def run(self):
        """Full lifecycle: setup, execute, wait, and close."""
        try:
            self.setup()
            self.execute()
        finally:
            self.wait()
            self.close()
