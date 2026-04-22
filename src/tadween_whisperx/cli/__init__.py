import typer

from .config import Config
from .run import app as Run

app = typer.Typer(name="tadween-whisperx", help="tadween-whisperx CLI")
app.add_typer(Config, name="config")
app.add_typer(Run, name="run")
