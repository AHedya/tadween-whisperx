import rich
import typer
from typing import Literal

from ...config import load_config, save_config


def loader_cmd(
    type: Literal["torchcodec", "av", "ffmpeg_stream"] | None = typer.Option(
        None, "--type", help="Loader type"
    ),
    max_stashed_files: int | None = typer.Option(
        None, "--max-stashed-files", help="Maximum stashed files"
    ),
) -> None:
    """Configure audio loader settings."""
    updates = {
        "type": type,
        "max_stashed_files": max_stashed_files,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.loader = config.loader.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Loader configuration updated.[/green]")
