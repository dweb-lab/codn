from pathlib import Path
from typing import Annotated

import typer

from codn.utils import git_utils

app = typer.Typer(help="Git related commands")


@app.command()
def check(
    path: Annotated[
        str,
        typer.Argument(help="Path to the Git repository"),
    ] = ".",
    *,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Check if the given path is a valid and healthy Git repository.

    This command verifies:
    - The existence of the .git directory
    - The ability to access the current HEAD commit
    - The repository integrity (no corruption)
    """
    try:
        full_path = Path(path).resolve()

        if not full_path.exists():
            typer.echo(f"❌ [ERROR] Path does not exist: {full_path}", err=True)
            raise typer.Exit(code=1)

        if not full_path.is_dir():
            typer.echo(f"❌ [ERROR] Path is not a directory: {full_path}", err=True)
            raise typer.Exit(code=1)

        if verbose:
            typer.echo(f"🔍 Checking Git repository at: {full_path}")

        if git_utils.is_valid_git_repo(full_path):
            typer.echo(f"✅ [OK] '{full_path}' is a valid Git repository.")
        else:
            typer.echo(
                f"❌ [FAIL] '{full_path}' is NOT a valid Git repository.",
                err=True,
            )
            raise typer.Exit(code=1)

    except KeyboardInterrupt:
        typer.echo("\n⚠️  Operation cancelled by user.", err=True)
        raise typer.Exit(code=130)
    except Exception as e:
        typer.echo(f"❌ [ERROR] Unexpected error: {e}", err=True)
        raise typer.Exit(code=1)
