import rich
import typer

from ...config import get_config, save_config


def transcription_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable transcription"
    ),
    model_id: str | None = typer.Option(None, "--model-id", help="Model ID"),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    compute_type: str | None = typer.Option(
        None, "--compute-type", help="Compute type (e.g., float16)"
    ),
    batch_size: int | None = typer.Option(None, "--batch-size", help="Batch size"),
    language: str | None = typer.Option(None, "--language", help="Language code"),
    threads: int | None = typer.Option(None, "--threads", help="Number of threads"),
) -> None:
    """Configure transcription settings."""
    updates = {
        "enabled": enabled,
        "model_id": model_id,
        "device": device,
        "compute_type": compute_type,
        "batch_size": batch_size,
        "language": language,
        "threads": threads,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = get_config()
    config.transcription = config.transcription.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Transcription configuration updated.[/green]")
