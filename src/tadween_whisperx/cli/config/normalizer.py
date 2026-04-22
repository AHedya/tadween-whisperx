import rich
import typer

from ...config import load_config, save_config


def normalizer_cmd(
    enabled: bool | None = typer.Option(
        None, "--enabled/--no-enabled", help="Enable or disable normalizer"
    ),
    allowed_chars: int | None = typer.Option(
        None, "--allowed-chars", help="Allowed characters limit"
    ),
    max_word_len: int | None = typer.Option(
        None, "--max-word-len", help="Maximum word length"
    ),
    allowed_words: int | None = typer.Option(
        None, "--allowed-words", help="Allowed words limit"
    ),
) -> None:
    """Configure normalizer settings."""
    updates = {
        "enabled": enabled,
        "allowed_chars": allowed_chars,
        "max_word_len": max_word_len,
        "allowed_words": allowed_words,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        rich.print("No changes provided.")
        return

    config = load_config()
    config.normalizer = config.normalizer.model_copy(update=updates)
    save_config(config)
    rich.print("[green]Normalizer configuration updated.[/green]")
