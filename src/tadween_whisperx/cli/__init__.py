import typer

# from tadween_whisperx.config import get_config
from .config import Config
from .run import app as Run
from .scan import app as Scan

app = typer.Typer(name="tadween-whisperx", help="tadween-whisperx CLI")


# @app.callback()
# def main():
#     """tadween-whisperx CLI entry point."""
#     get_config()


app.add_typer(Config, name="config")
app.add_typer(Run, name="run")
app.add_typer(Scan, name="scan")
