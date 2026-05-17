import rich
import typer

from ...config import get_config, save_config


def diarization_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable diarization"
    ),
    model_id: str | None = typer.Option(None, "--model-id", help="Model ID"),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    token: str | None = typer.Option(None, "--token", help="Hugging Face token"),
    cache_dir: str | None = typer.Option(None, "--cache-dir", help="Cache directory"),
) -> None:
    """Configure diarization settings."""
    updates = {
        "enabled": enabled,
        "model_id": model_id,
        "device": device,
        "token": token,
        "cache_dir": cache_dir,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = get_config()
    config.diarization = config.diarization.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Diarization configuration updated.[/green]")
