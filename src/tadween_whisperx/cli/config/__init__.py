from enum import StrEnum

import rich
import typer
import yaml

import tadween_whisperx.config as config_module

from ...config import (
    config_exists,
    load_config,
    redact_secrets,
    reset_config,
)
from .alignment import alignment_cmd
from .diarization import diarization_cmd
from .input import app as input_app
from .loader import loader_cmd
from .normalizer import normalizer_cmd
from .repo import repo_app  # noqa: E402
from .transcription import transcription_cmd


class ConfigComponent(StrEnum):
    repo = "repo"
    re = "re"
    input = "input"
    in_ = "in"
    loader = "loader"
    lo = "lo"
    diarization = "diarization"
    di = "di"
    transcription = "transcription"
    tr = "tr"
    alignment = "alignment"
    al = "al"
    normalizer = "normalizer"
    no = "no"

    @property
    def full_name(self) -> str:
        mapping = {
            "re": "repo",
            "in": "input",
            "lo": "loader",
            "di": "diarization",
            "tr": "transcription",
            "al": "alignment",
            "no": "normalizer",
        }
        return mapping.get(self.value, self.value)


COMPONENTS_PANEL = "Components settings"

Config = typer.Typer(name="config", help="Manage tadween-whisperx configuration.")
Config.add_typer(repo_app, name="repo", rich_help_panel=COMPONENTS_PANEL)
Config.add_typer(input_app, name="input", rich_help_panel=COMPONENTS_PANEL)
Config.command(name="loader", rich_help_panel=COMPONENTS_PANEL)(loader_cmd)
Config.command(name="diarization", rich_help_panel=COMPONENTS_PANEL)(diarization_cmd)
Config.command(name="alignment", rich_help_panel=COMPONENTS_PANEL)(alignment_cmd)
Config.command(name="normalizer", rich_help_panel=COMPONENTS_PANEL)(normalizer_cmd)
Config.command(
    name="transcription",
    rich_help_panel=COMPONENTS_PANEL,
)(transcription_cmd)


@Config.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing config"
    ),
) -> None:
    """Initialize user configuration from package defaults."""
    if config_exists() and not force:
        rich.print(
            f"[yellow]Config already exists[/yellow]: {config_module.USER_CONFIG_FILE}\n"
            "Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    path = reset_config()
    rich.print(f"[green]Config initialized[/green]: {path}")


@Config.command()
def reset() -> None:
    """Reset user configuration to package defaults."""
    path = reset_config()
    rich.print(f"[green]Config reset[/green]: {path}")


@Config.command()
def show(
    component: list[ConfigComponent] = typer.Option(
        None, "--component", "-c", help="Specific component(s) to show"
    ),
    components: list[ConfigComponent] = typer.Argument(
        None, help="Additional component(s) to show"
    ),
    reveal: bool = typer.Option(
        False, "--reveal", help="Show secret values (default: masked)"
    ),
) -> None:
    """Display current configuration."""
    config = load_config()
    data = config.model_dump(mode="json")

    all_requested = (component or []) + (components or [])
    if all_requested:
        # Deduplicate names (handling shortcuts) while preserving order
        unique_names = list(dict.fromkeys(c.full_name for c in all_requested))
        data = {name: data[name] for name in unique_names}

    if not reveal:
        data = redact_secrets(data)
    rich.print(yaml.dump(data, default_flow_style=False, sort_keys=False))
