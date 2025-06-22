from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from codn import __version__
from codn.cli_commands import analyze_cli, git_cli
from codn.cli_commands.analyze_cli import (
    analyze_functions,
    analyze_project,
    find_references,
    find_unused_imports_cmd,
)

console = Console()

app = typer.Typer(
    help="🔍 Codn - Fast Python code analysis.",
    rich_markup_mode="rich",
    invoke_without_command=True,
)

# 注册子命令组
app.add_typer(
    git_cli.app,
    name="git",
    help="🔧 Git repository validation and health checks",
)
app.add_typer(
    analyze_cli.app,
    name="analyze",
    help="📊 Code analysis and statistics",
)


# 添加简化的直接命令
@app.command("unused")
def unused_imports(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to analyze (default: current directory)"),
    ] = None,
    *,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files in analysis"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Automatically remove unused imports (experimental)",
        ),
    ] = False,
) -> None:
    """🧹 Find unused imports in Python files."""
    find_unused_imports_cmd(path, include_tests=include_tests, fix=fix)


@app.command("refs")
def find_refs(
    function_name: Annotated[
        str,
        typer.Argument(help="Function name to find references for"),
    ],
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to search (default: current directory)"),
    ] = None,
    *,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files in search"),
    ] = False,
) -> None:
    """🔍 Find all references to a function."""
    find_references(function_name, path, include_tests=include_tests)


@app.command("funcs")
def functions(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to analyze (default: current directory)"),
    ] = None,
    *,
    class_name: Annotated[
        Optional[str],
        typer.Option("--class", help="Filter by class name"),
    ] = None,
    show_signatures: Annotated[
        bool,
        typer.Option("--signatures", help="Show function signatures"),
    ] = False,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files"),
    ] = False,
) -> None:
    """📝 List all functions and methods."""
    analyze_functions(
        path,
        class_name=class_name,
        show_signatures=show_signatures,
        include_tests=include_tests,
    )


@app.callback()
def main(
    ctx: typer.Context,
    *,
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show version information"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """
    🔍 Codn - Fast Python code analysis.

    Quick commands:
      codn              - Analyze current project
      codn unused       - Find unused imports
      codn refs <func>  - Find function references
      codn funcs        - List all functions
    """
    if version:
        console.print(
            f"[bold blue]codn[/bold blue] version [green]{__version__}[/green]",
        )
        raise typer.Exit

    # 如果没有子命令, 默认执行项目分析
    if ctx.invoked_subcommand is None:
        analyze_project(Path.cwd(), include_tests=False, verbose=verbose)


if __name__ == "__main__":
    app()
