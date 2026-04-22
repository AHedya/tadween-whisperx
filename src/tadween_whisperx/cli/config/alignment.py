import rich
import typer

from ...config import load_config, save_config


def alignment_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable alignment"
    ),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    model_name: str | None = typer.Option(None, "--model-name", help="Model name"),
) -> None:
    """Configure alignment settings."""
    updates = {
        "enabled": enabled,
        "device": device,
        "model_name": model_name,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.alignment = config.alignment.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Alignment configuration updated.[/green]")
