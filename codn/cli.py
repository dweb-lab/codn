from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from codn.cli_commands import analyze_cli, git_cli

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
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to analyze (default: current directory)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include test files in analysis",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Automatically remove unused imports (experimental)",
    ),
) -> None:
    """🧹 Find unused imports in Python files."""
    from .cli_commands.analyze_cli import find_unused_imports_cmd

    find_unused_imports_cmd(path, include_tests, fix)


@app.command("refs")
def find_refs(
    function_name: str = typer.Argument(
        ...,
        help="Function name to find references for",
    ),
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to search (default: current directory)",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include test files in search",
    ),
) -> None:
    """🔍 Find all references to a function."""
    from .cli_commands.analyze_cli import find_references

    find_references(function_name, path, include_tests)


@app.command("funcs")
def functions(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path to analyze (default: current directory)",
    ),
    class_name: Optional[str] = typer.Option(
        None,
        "--class",
        help="Filter by class name",
    ),
    show_signatures: bool = typer.Option(
        False,
        "--signatures",
        help="Show function signatures",
    ),
    include_tests: bool = typer.Option(
        False,
        "--include-tests",
        help="Include test files",
    ),
) -> None:
    """📝 List all functions and methods."""
    from .cli_commands.analyze_cli import analyze_functions

    analyze_functions(path, class_name, show_signatures, include_tests)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version information",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
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
        from codn import __version__

        console.print(
            f"[bold blue]codn[/bold blue] version [green]{__version__}[/green]"
        )
        raise typer.Exit

    # 如果没有子命令, 默认执行项目分析
    if ctx.invoked_subcommand is None:
        from .cli_commands.analyze_cli import analyze_project

        analyze_project(Path.cwd(), False, verbose)


if __name__ == "__main__":
    app()
