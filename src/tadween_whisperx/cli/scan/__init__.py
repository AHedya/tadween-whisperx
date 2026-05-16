from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tadween_whisperx import scanners
from tadween_whisperx.config import AppConfig

from ..shared import add_input_commands

app = typer.Typer(help="Scan input for compatible files.")
console = Console()


def _execute_scan(config: AppConfig) -> None:
    """Internal helper to scan the input from a resolved config."""
    if config.input is None:
        console.print(
            "[bold red]Error:[/bold red] No input source provided. "
            "Set input in config or use a subcommand (local/s3)."
        )
        raise typer.Exit(code=1)

    scanner = scanners.create_scanner(config.input)

    console.print("[bold blue]Scanning Input[/bold blue]")
    console.print(f"Input type: [green]{config.input.type}[/green]")

    try:
        count = 0
        for result in scanner.scan(
            include=config.input.include, exclude=config.input.exclude
        ):
            console.print(
                f"Found: [cyan]{result.source}[/cyan] "
                f"(Artifact ID: [magenta]{result.artifact_id}[/magenta])"
            )
            count += 1

        if count == 0:
            console.print("[yellow]No files found.[/yellow]")
        else:
            console.print(f"\n[bold green]Total files found: {count}[/bold green]")

    finally:
        scanner.close()


@app.callback(invoke_without_command=True)
def scan(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a custom configuration file. Overrides default and user config.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Scan for compatible files."""
    from tadween_whisperx.config import bootstrap_env, load_config, set_config

    try:
        # 1. Bootstrap environment variables first
        bootstrap_env()

        # 2. Load and set the global config
        config = load_config(config_path)
        set_config(config)

        # 3. If no subcommand (local, s3, http), execute with the loaded config
        if ctx.invoked_subcommand is None:
            _execute_scan(config)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


add_input_commands(
    app,
    action=_execute_scan,
    local_help="Scan local files/directories.",
    s3_help="Scan S3 objects.",
    http_help="Scan HTTP URLs.",
)
