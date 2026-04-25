from pathlib import Path

import rich
import typer

from ...config import (
    JsonRepoConfig,
    S3RepoConfig,
    get_config,
    save_config,
)

repo_app = typer.Typer(name="repo", help="Manage repo profiles.")


@repo_app.command("json")
def json_repo(
    path: Path | None = typer.Option(
        None, "--path", "-p", help="Repo path (default: <cwd>/repo)"
    ),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Profile name (default: 'json')"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing profile"),
) -> None:
    """Create or update a json repo profile."""
    profile_name = name or "json"
    repo_path = path or Path.cwd() / "repo"

    config = get_config()

    if profile_name in config.repo.profiles and not force:
        rich.print(
            f"[yellow]Profile '{profile_name}' already exists.[/yellow] "
            "Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    config.repo.profiles[profile_name] = JsonRepoConfig(path=repo_path)
    config.repo.active = profile_name
    saved = save_config(config)

    rich.print(
        f"[green]Profile '{profile_name}' (json) created and set as active.[/green]\n"
        f"  path: {repo_path}\n"
        f"  config: {saved}"
    )


@repo_app.command("s3")
def s3_repo(
    bucket: str = typer.Option(..., "--bucket", "-b", help="S3 bucket name"),
    prefix: str | None = typer.Option(None, "--prefix", help="S3 key prefix"),
    aws_access_key_id: str = typer.Option(
        ..., "--aws-access-key-id", help="AWS access key ID"
    ),
    aws_secret_access_key: str = typer.Option(
        ..., "--aws-secret-access-key", help="AWS secret access key"
    ),
    aws_session_token: str | None = typer.Option(
        None, "--aws-session-token", help="AWS session token"
    ),
    endpoint_url: str | None = typer.Option(
        None, "--endpoint-url", help="S3-compatible endpoint URL"
    ),
    region_name: str = typer.Option("us-east-1", "--region", help="AWS region"),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Profile name (default: 's3')"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing profile"),
) -> None:
    """Create or update an S3 repo profile."""
    profile_name = name or "s3"

    config = get_config()

    if profile_name in config.repo.profiles and not force:
        rich.print(
            f"[yellow]Profile '{profile_name}' already exists.[/yellow] "
            "Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    s3_config = S3RepoConfig(
        bucket=bucket,
        prefix=prefix,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
        endpoint_url=endpoint_url,
        region_name=region_name,
    )
    config.repo.profiles[profile_name] = s3_config
    config.repo.active = profile_name
    saved = save_config(config)

    rich.print(
        f"[green]Profile '{profile_name}' (s3) created and set as active.[/green]\n"
        f"  bucket: {bucket}\n"
        f"  prefix: {prefix or '(none)'}\n"
        f"  endpoint: {endpoint_url or 'default'}\n"
        f"  config: {saved}"
    )


@repo_app.command("list")
def list_profiles() -> None:
    """List all repo profiles."""
    config = get_config()

    if not config.repo.profiles:
        rich.print("[dim]No repo profiles configured.[/dim]")
        return

    for name, profile in config.repo.profiles.items():
        active_marker = " [bold green]*[/]" if name == config.repo.active else ""
        if profile.type == "json":
            rich.print(
                f"  {name}{active_marker}  type={profile.type}  path={profile.path}"
            )
        elif profile.type == "s3":
            rich.print(
                f"  {name}{active_marker}  type={profile.type}  "
                f"bucket={profile.bucket}  "
                f"prefix={profile.prefix or '(none)'}  "
                f"endpoint={profile.endpoint_url or 'default'}"
            )

    if config.repo.active is None:
        rich.print("\n[yellow]No active profile set.[/yellow]")


@repo_app.command("switch")
def switch_profile(
    name: str = typer.Argument(..., help="Profile name to activate"),
) -> None:
    """Switch the active repo profile."""
    config = get_config()

    if name not in config.repo.profiles:
        available = ", ".join(config.repo.profiles) or "(none)"
        rich.print(f"[red]Profile '{name}' not found.[/red] Available: {available}")
        raise typer.Exit(code=1)

    config.repo.active = name
    save_config(config)
    profile = config.repo.profiles[name]
    rich.print(
        f"[green]Active profile switched to '{name}'[/green] (type={profile.type})"
    )


@repo_app.command("remove")
def remove_profile(
    name: str = typer.Argument(..., help="Profile name to remove"),
) -> None:
    """Remove a repo profile."""
    config = get_config()

    if name not in config.repo.profiles:
        available = ", ".join(config.repo.profiles) or "(none)"
        rich.print(f"[red]Profile '{name}' not found.[/red] Available: {available}")
        raise typer.Exit(code=1)

    if config.repo.active == name:
        rich.print(
            f"[red]Cannot remove active profile '{name}'.[/red] "
            "Switch to another profile first."
        )
        raise typer.Exit(code=1)

    del config.repo.profiles[name]
    saved = save_config(config)
    rich.print(f"[green]Profile '{name}' removed.[/green]  config: {saved}")
