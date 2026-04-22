import rich
import typer

from ...config import load_config, save_config


def diarization_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable diarization"
    ),
    model_name: str | None = typer.Option(None, "--model-name", help="Model name"),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    token: str | None = typer.Option(None, "--token", help="HuggingFace token"),
) -> None:
    """Configure diarization settings."""
    updates = {
        "enabled": enabled,
        "model_name": model_name,
        "device": device,
        "token": token,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.diarization = config.diarization.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Diarization configuration updated.[/green]")
