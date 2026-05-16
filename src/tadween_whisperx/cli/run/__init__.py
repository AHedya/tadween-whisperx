from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ..shared import add_input_commands
from .run import _execute_pipeline

app = typer.Typer(help="Run the ASR pipeline.")
console = Console()


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a custom configuration file. Overrides default and user config.",
            exists=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
):
    """Run the ASR pipeline."""
    from tadween_whisperx.config import bootstrap_env, load_config, set_config

    try:
        bootstrap_env()
        config = load_config(config_path)
        set_config(config)

        # If no subcommand (local, s3, http), execute with the loaded config
        if ctx.invoked_subcommand is None:
            _execute_pipeline(config)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


add_input_commands(
    app,
    action=_execute_pipeline,
    local_help="Run pipeline on local files/directories.",
    s3_help="Run pipeline on S3 objects.",
    http_help="Run pipeline on HTTP URLs.",
)
