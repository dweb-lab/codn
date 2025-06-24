"""CLI commands for code LSP features."""

from pathlib import Path
from typing import Annotated  # Optional

import typer
from rich.console import Console
from rich.panel import Panel
# from rich.columns import Columns
# from rich.progress import BarColumn, Progress, TextColumn
# TaskProgressColumn
# from rich.table import Table

import asyncio

from ..utils.os_utils import list_all_files_sync
from codn.utils.base_lsp_client import (
    get_snippet,
    get_refs,
)

app = typer.Typer(help="Code analysis commands", invoke_without_command=True)
console = Console()


@app.callback()
def lsp_main(ctx: typer.Context) -> None:
    """📊 Code analysis and statistics.

    Using LSP in your Python codebase with powerful tools for understanding code
    structure, finding issues, and improving code quality.
    """
    if ctx.invoked_subcommand is None:
        show_lsp_welcome()


def show_lsp_welcome() -> None:
    """Display simple welcome message for lsp command."""

    console.print()
    console.print("[bold blue]📊 LSP Commands[/bold blue]")
    console.print()

    # Simple command list
    console.print("[cyan]search <func>[/cyan] 🔍 Find code snippets")
    console.print("[cyan]refs <func>[/cyan] 🔍 Find function references")
    # console.print("[cyan]functions[/cyan]        📝 List all functions")
    # console.print("[cyan]project[/cyan]           📈 Project overview & quality score")
    # console.print("[cyan]unused-imports[/cyan]   🧹 Find unused imports")

    console.print()
    console.print(
        "[bold yellow]💡 Tip:[/bold yellow] Use [green]codn[/green] "
        "(without lsp) for shorter commands!",
    )
    console.print("[dim]Examples: codn unused, codn refs <func>, codn funcs[/dim]")


@app.command("search")
def search(
    function_name: Annotated[
        str,
        typer.Argument(help="Function name to search snippet for"),
    ],
    path: Annotated[
        str,
        typer.Argument(help="Path to search (default: current directory)"),
    ] = ".",
    *,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files in search"),
    ] = False,
) -> None:
    """Find all snippets to a function in the project."""
    if not path:
        path = str(Path.cwd())

    if not Path(path).exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(
        f"[blue]Searching for snippets to '{function_name}' in: {path}[/blue]",
    )

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
    python_files = list_all_files_sync(Path(path), "*.py", ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    results = asyncio.run(get_snippet(function_name, str(path)))
    total_snippets = len(results)

    console.print()
    if total_snippets > 0:
        console.print(
            Panel.fit(
                f"[green]✅ Found {total_snippets} references to "
                f"'[bold]{function_name}[/bold]'[/green]",
                style="green",
            ),
        )
        for result in results:
            console.print("[yellow]==Code Snippet:[/yellow]")
            console.print(f"[green]{result}[/green]")

    else:
        console.print(
            Panel.fit(
                f"[yellow]Info: No snippets found for "
                f"'[bold]{function_name}[/bold]'[/yellow]\n"
                f"The function might be:\n"
                f"• Only used in excluded files (try --include-tests)\n"
                f"• Called dynamically or through reflection\n"
                f"• Not used in any code\n"
                f"• Misspelled or not defined\n",
                title="Search Results",
                style="yellow",
            ),
        )


@app.command("refs")
def find_references(
    function_name: Annotated[
        str,
        typer.Argument(help="Function name to find references for"),
    ],
    path: Annotated[
        str,
        typer.Argument(help="Path to search (default: current directory)"),
    ] = "",
    *,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files in search"),
    ] = False,
) -> None:
    """Find all references to a function in the project."""
    pass

    if not path:
        path = str(Path.cwd())

    if not Path(path).exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(
        f"[blue]Searching for references to '{function_name}' in: {path}[/blue]",
    )

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
    python_files = list_all_files_sync(Path(path), "*.py", ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    results = asyncio.run(get_refs(function_name, str(path)))
    total_refs = len(results)

    console.print()
    if total_refs > 0:
        console.print(
            Panel.fit(
                f"[green]✅ Found {total_refs} references to "
                f"'[bold]{function_name}[/bold]'[/green]",
                style="green",
            ),
        )
        console.print("[yellow]==Refs:[/yellow]")
        for result in results:
            console.print(f"[green]{result}[/green]")

    else:
        console.print(
            Panel.fit(
                f"[yellow]Info: No references found for "
                f"'[bold]{function_name}[/bold]'[/yellow]\n"
                f"The function might be:\n"
                f"• Unused (consider removing)\n"
                f"• Only used in excluded files (try --include-tests)\n"
                f"• Called dynamically or through reflection",
                title="Search Results",
                style="yellow",
            ),
        )


if __name__ == "__main__":
    app()
