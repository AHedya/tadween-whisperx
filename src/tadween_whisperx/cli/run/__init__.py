import typer
from rich.console import Console

from tadween_whisperx.config import get_config

from ..shared import add_input_commands
from .run import _execute_pipeline

app = typer.Typer(help="Run the ASR pipeline.")
console = Console()


@app.callback(invoke_without_command=True)
def run(ctx: typer.Context):
    """Run the ASR pipeline using the default configuration."""
    if ctx.invoked_subcommand is None:
        try:
            config = get_config()
            _execute_pipeline(config)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red]: {e}")


add_input_commands(
    app,
    action=_execute_pipeline,
    local_help="Run pipeline on local files/directories.",
    s3_help="Run pipeline on S3 objects.",
)
