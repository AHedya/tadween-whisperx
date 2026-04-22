import rich
import typer

from ...config import load_config, save_config


def transcription_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable transcription"
    ),
    model: str | None = typer.Option(None, "--model", help="Model name"),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    compute_type: str | None = typer.Option(
        None, "--compute-type", help="Compute type (e.g., float16)"
    ),
    batch_size: int | None = typer.Option(None, "--batch-size", help="Batch size"),
) -> None:
    """Configure transcription settings."""
    updates = {
        "enabled": enabled,
        "model": model,
        "device": device,
        "compute_type": compute_type,
        "batch_size": batch_size,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.transcription = config.transcription.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Transcription configuration updated.[/green]")
