"""
CLI commands for code analysis features.
"""

import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text

from ..utils.simple_ast import (
    find_function_references,
    extract_function_signatures,
    find_unused_imports,
    extract_class_methods,
    find_enclosing_function,
    extract_inheritance_relations
)
from ..utils.os_utils import list_all_python_files_sync
from ..utils.git_utils import is_valid_git_repo

app = typer.Typer(help="Code analysis commands")
console = Console()


@app.command("project")
def analyze_project(
    path: Optional[Path] = typer.Argument(None, help="Path to analyze (default: current directory)"),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in analysis"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Analyze project structure and provide statistics."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Analyzing project at: {path}[/blue]")

    # Get all Python files
    ignored_dirs = [] if include_tests else ["tests", "test"]
    python_files = list_all_python_files_sync(path, ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    # Initialize statistics
    stats = {
        "total_files": len(python_files),
        "total_lines": 0,
        "total_functions": 0,
        "total_classes": 0,
        "total_methods": 0,
        "files_with_issues": 0,
        "unused_imports": 0,
    }

    file_details = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Analyzing files...", total=len(python_files))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Count lines
                lines = len(content.splitlines())
                stats["total_lines"] += lines

                # Extract functions
                functions = extract_function_signatures(content)
                stats["total_functions"] += len(functions)

                # Extract classes and methods
                methods = extract_class_methods(content)
                classes = set(method["class_name"] for method in methods)
                stats["total_classes"] += len(classes)
                stats["total_methods"] += len(methods)

                # Find unused imports
                unused = find_unused_imports(content)
                if unused:
                    stats["files_with_issues"] += 1
                    stats["unused_imports"] += len(unused)

                if verbose:
                    file_details.append({
                        "file": file_path,
                        "lines": lines,
                        "functions": len(functions),
                        "classes": len(classes),
                        "methods": len(methods),
                        "unused_imports": len(unused)
                    })

            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")

            progress.advance(task)

    # Display results
    console.print("\n[green]Project Analysis Results[/green]")

    # Summary table
    table = Table(title="Project Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta", justify="right")

    table.add_row("Python Files", str(stats["total_files"]))
    table.add_row("Total Lines", str(stats["total_lines"]))
    table.add_row("Functions", str(stats["total_functions"]))
    table.add_row("Classes", str(stats["total_classes"]))
    table.add_row("Methods", str(stats["total_methods"]))
    table.add_row("Files with Issues", str(stats["files_with_issues"]))
    table.add_row("Unused Imports", str(stats["unused_imports"]))

    if is_valid_git_repo(path):
        table.add_row("Git Repository", "✓", style="green")
    else:
        table.add_row("Git Repository", "✗", style="red")

    console.print(table)

    # Detailed file information if verbose
    if verbose and file_details:
        console.print("\n[green]File Details[/green]")

        detail_table = Table()
        detail_table.add_column("File", style="cyan")
        detail_table.add_column("Lines", justify="right")
        detail_table.add_column("Functions", justify="right")
        detail_table.add_column("Classes", justify="right")
        detail_table.add_column("Methods", justify="right")
        detail_table.add_column("Issues", justify="right")

        for detail in file_details:
            try:
                relative_path = detail["file"].relative_to(path)
            except ValueError:
                relative_path = detail["file"]

            detail_table.add_row(
                str(relative_path),
                str(detail["lines"]),
                str(detail["functions"]),
                str(detail["classes"]),
                str(detail["methods"]),
                str(detail["unused_imports"]) if detail["unused_imports"] > 0 else "-"
            )

        console.print(detail_table)


@app.command("find-refs")
def find_references(
    function_name: str = typer.Argument(..., help="Function name to find references for"),
    path: Optional[Path] = typer.Argument(None, help="Path to search (default: current directory)"),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in search"),
):
    """Find all references to a function in the project."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Searching for references to '{function_name}' in: {path}[/blue]")

    # Get all Python files
    ignored_dirs = [] if include_tests else ["tests", "test"]
    python_files = list_all_python_files_sync(path, ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    total_references = 0

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Searching files...", total=len(python_files))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                references = find_function_references(content, function_name)

                if references:
                    try:
                        relative_path = file_path.relative_to(path)
                    except ValueError:
                        relative_path = file_path
                    console.print(f"\n[green]{relative_path}[/green]")
                    for line_num, col_offset in references:
                        lines = content.splitlines()
                        if 0 < line_num <= len(lines):
                            line_content = lines[line_num - 1].strip()
                            console.print(f"  Line {line_num}: {line_content}")
                            total_references += 1

            except Exception as e:
                console.print(f"[red]Error searching {file_path}: {e}[/red]")

            progress.advance(task)

    console.print(f"\n[cyan]Found {total_references} references to '{function_name}'[/cyan]")


@app.command("unused-imports")
def find_unused_imports_cmd(
    path: Optional[Path] = typer.Argument(None, help="Path to analyze (default: current directory)"),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files in analysis"),
    fix: bool = typer.Option(False, "--fix", help="Automatically remove unused imports (experimental)"),
):
    """Find unused imports in Python files."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Finding unused imports in: {path}[/blue]")

    # Get all Python files
    ignored_dirs = [] if include_tests else ["tests", "test"]
    python_files = list_all_python_files_sync(path, ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    total_unused = 0
    files_with_unused = 0

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Analyzing imports...", total=len(python_files))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                unused = find_unused_imports(content)

                if unused:
                    files_with_unused += 1
                    try:
                        relative_path = file_path.relative_to(path)
                    except ValueError:
                        relative_path = file_path
                    console.print(f"\n[yellow]{relative_path}[/yellow]")

                    for import_name, line_num in unused:
                        console.print(f"  Line {line_num}: unused import '{import_name}'")
                        total_unused += 1

                        if fix:
                            console.print(f"    [dim]Note: Automatic fixing not implemented yet[/dim]")

            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")

            progress.advance(task)

    if total_unused == 0:
        console.print("[green]No unused imports found! 🎉[/green]")
    else:
        console.print(f"\n[cyan]Found {total_unused} unused imports in {files_with_unused} files[/cyan]")
        if fix:
            console.print("[yellow]Note: Automatic fixing is not yet implemented[/yellow]")


@app.command("functions")
def analyze_functions(
    path: Optional[Path] = typer.Argument(None, help="Path to analyze (default: current directory)"),
    class_name: Optional[str] = typer.Option(None, "--class", help="Filter by class name"),
    show_signatures: bool = typer.Option(False, "--signatures", help="Show function signatures"),
    include_tests: bool = typer.Option(False, "--include-tests", help="Include test files"),
):
    """Analyze functions and methods in the project."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Analyzing functions in: {path}[/blue]")

    # Get all Python files
    ignored_dirs = [] if include_tests else ["tests", "test"]
    python_files = list_all_python_files_sync(path, ignored_dirs=ignored_dirs)

    if not python_files:
        console.print("[yellow]No Python files found[/yellow]")
        return

    all_functions = []
    all_methods = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Analyzing functions...", total=len(python_files))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Extract functions
                functions = extract_function_signatures(content)
                for func in functions:
                    try:
                        func["file"] = file_path.relative_to(path)
                    except ValueError:
                        func["file"] = file_path
                    all_functions.append(func)

                # Extract methods
                methods = extract_class_methods(content, class_name)
                for method in methods:
                    try:
                        method["file"] = file_path.relative_to(path)
                    except ValueError:
                        method["file"] = file_path
                    all_methods.append(method)

            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")

            progress.advance(task)

    # Display functions
    if all_functions:
        console.print(f"\n[green]Functions ({len(all_functions)})[/green]")

        func_table = Table()
        func_table.add_column("Function", style="cyan")
        func_table.add_column("File", style="dim")
        func_table.add_column("Line", justify="right")
        if show_signatures:
            func_table.add_column("Arguments")
        func_table.add_column("Async", justify="center")

        for func in sorted(all_functions, key=lambda x: (str(x["file"]), x["line"])):
            row = [
                func["name"],
                str(func["file"]),
                str(func["line"]),
            ]
            if show_signatures:
                args_str = ", ".join(func["args"]) if func["args"] else ""
                row.append(args_str)
            row.append("✓" if func["is_async"] else "")
            func_table.add_row(*row)

        console.print(func_table)

    # Display methods
    if all_methods:
        console.print(f"\n[green]Methods ({len(all_methods)})[/green]")

        method_table = Table()
        method_table.add_column("Class", style="cyan")
        method_table.add_column("Method", style="bright_cyan")
        method_table.add_column("File", style="dim")
        method_table.add_column("Line", justify="right")
        method_table.add_column("Type", justify="center")

        for method in sorted(all_methods, key=lambda x: (x["class_name"], x["method_name"])):
            method_type = ""
            if method["is_staticmethod"]:
                method_type = "static"
            elif method["is_classmethod"]:
                method_type = "class"
            elif method["is_property"]:
                method_type = "prop"
            elif method["is_async"]:
                method_type = "async"

            method_table.add_row(
                method["class_name"],
                method["method_name"],
                str(method["file"]),
                str(method["line"]),
                method_type
            )

        console.print(method_table)

    if not all_functions and not all_methods:
        console.print("[yellow]No functions or methods found[/yellow]")


if __name__ == "__main__":
    app()
