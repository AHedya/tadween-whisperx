import typer
from rich.console import Console

from tadween_whisperx.config import (
    AppConfig,
    HTTPInputConfig,
    LocalInputConfig,
    S3InputConfig,
    save_config,
)

from ..shared import add_input_commands

app = typer.Typer(help="Configure input settings")
console = Console()


def _save_config_action(config: AppConfig) -> None:
    save_config(config)
    if isinstance(config.input, LocalInputConfig):
        paths = ", ".join(str(p) for p in config.input.paths)
        console.print(f"[green]Input set to local paths: {paths}[/green]")
    elif isinstance(config.input, S3InputConfig):
        console.print(
            f"[green]Input set to S3 bucket: {config.input.bucket} "
            f"(prefix: {config.input.prefix})[/green]"
        )
    elif isinstance(config.input, HTTPInputConfig):
        console.print(f"[green]Input set to {len(config.input.urls)} HTTP URLs[/green]")


add_input_commands(
    app,
    action=_save_config_action,
    local_help="Set input source to local paths.",
    s3_help="Set input source to an S3 bucket.",
    http_help="Set input source to HTTP URLs.",
)
