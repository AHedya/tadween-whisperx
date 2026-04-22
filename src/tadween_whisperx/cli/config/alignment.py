import rich
import typer

from ...config import load_config, save_config


def alignment_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable alignment"
    ),
    device: str | None = typer.Option(None, "--device", help="Device to use"),
    model_name: str | None = typer.Option(None, "--model-name", help="Model name"),
    language_code: str | None = typer.Option(
        None, "--language-code", help="Default language code"
    ),
    model_dir: str | None = typer.Option(None, "--model-dir", help="Model directory"),
    model_cache_only: bool | None = typer.Option(
        None, "--model-cache-only/--no-model-cache-only", help="Use only cached models"
    ),
    max_models: int | None = typer.Option(
        None, "--max-models", help="Maximum models to keep in memory"
    ),
) -> None:
    """Configure alignment settings."""
    updates = {
        "enabled": enabled,
        "device": device,
        "model_name": model_name,
        "language_code": language_code,
        "model_dir": model_dir,
        "model_cache_only": model_cache_only,
        "max_models": max_models,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.alignment = config.alignment.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Alignment configuration updated.[/green]")
