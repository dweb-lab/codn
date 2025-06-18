import typer
from pathlib import Path
from codn.utils import git_utils

app = typer.Typer(help="Git related commands")

@app.command()
def check(path: str = typer.Argument(".", help="Path to the Git repository")):
    """
    Check if the given path is a valid and healthy Git repository.
    """
    full_path = Path(path).resolve()
    if not full_path.exists():
        typer.echo(f"[ERROR] Path does not exist: {full_path}")
        raise typer.Exit(code=1)

    if git_utils.is_valid_git_repo(str(full_path)):
        typer.echo(f"[OK] '{full_path}' is a valid Git repository.")
    else:
        typer.echo(f"[FAIL] '{full_path}' is NOT a valid Git repository.")
