"""CLI commands for code analysis features."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table

from ..utils.git_utils import is_valid_git_repo
from ..utils.os_utils import list_all_python_files_sync
from ..utils.simple_ast import (
    extract_class_methods,
    extract_function_signatures,
    find_function_references,
    find_unused_imports,
)

app = typer.Typer(help="Code analysis commands", invoke_without_command=True)
console = Console()


@app.callback()
def analyze_main(ctx: typer.Context) -> None:
    """📊 Code analysis and statistics.

    Analyze your Python codebase with powerful tools for understanding code structure,
    finding issues, and improving code quality.
    """
    if ctx.invoked_subcommand is None:
        show_analyze_welcome()


def show_analyze_welcome() -> None:
    """Display simple welcome message for analyze command."""

    console.print()
    console.print("[bold blue]📊 Analysis Commands[/bold blue]")
    console.print()

    # Simple command list
    console.print("[cyan]project[/cyan]           📈 Project overview & quality score")
    console.print("[cyan]unused-imports[/cyan]   🧹 Find unused imports")
    console.print("[cyan]find-refs <func>[/cyan] 🔍 Find function references")
    console.print("[cyan]functions[/cyan]        📝 List all functions")

    console.print()
    console.print(
        "[bold yellow]💡 Tip:[/bold yellow] Use [green]codn[/green] "
        "(without analyze) for shorter commands!",
    )
    console.print("[dim]Examples: codn unused, codn refs <func>, codn funcs[/dim]")


@app.command("project")
def analyze_project(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Path to analyze (default: current directory)"),
    ] = None,
    *,
    include_tests: Annotated[
        bool,
        typer.Option("--include-tests", help="Include test files in analysis"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Analyze project structure and provide statistics."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Analyzing project at: {path}[/blue]")

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
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
                content = file_path.read_text(encoding="utf-8")

                # Count lines
                lines = len(content.splitlines())
                stats["total_lines"] += lines

                # Extract functions
                functions = extract_function_signatures(content)
                stats["total_functions"] += len(functions)

                # Extract classes and methods
                methods = extract_class_methods(content)
                classes = {method["class_name"] for method in methods}
                stats["total_classes"] += len(classes)
                stats["total_methods"] += len(methods)

                # Find unused imports
                unused = find_unused_imports(content)
                if unused:
                    stats["files_with_issues"] += 1
                    stats["unused_imports"] += len(unused)

                if verbose:
                    file_details.append(
                        {
                            "file": file_path,
                            "lines": lines,
                            "functions": len(functions),
                            "classes": len(classes),
                            "methods": len(methods),
                            "unused_imports": len(unused),
                        },
                    )

            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")

            progress.advance(task)

    # Display results with enhanced formatting
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]📊 Project Analysis Complete[/bold blue]",
            style="blue",
        ),
    )
    console.print()

    # Calculate derived metrics
    avg_lines_per_file = (
        stats["total_lines"] / stats["total_files"] if stats["total_files"] > 0 else 0
    )
    avg_functions_per_file = (
        stats["total_functions"] / stats["total_files"]
        if stats["total_files"] > 0
        else 0
    )
    code_quality_score = max(
        0,
        100 - (stats["unused_imports"] * 2) - (stats["files_with_issues"] * 5),
    )

    # Create main statistics table with better formatting
    stats_table = Table(
        title="📈 Project Overview",
        show_header=True,
        header_style="bold magenta",
    )
    stats_table.add_column("Metric", style="cyan", width=20)
    stats_table.add_column("Value", style="bright_white", justify="right", width=10)
    stats_table.add_column("Assessment", style="dim", width=20)

    # Add rows with assessments
    stats_table.add_row(
        "🐍 Python Files",
        str(stats["total_files"]),
        _get_file_count_assessment(stats["total_files"]),
    )
    stats_table.add_row(
        "📝 Total Lines",
        f"{stats['total_lines']:,}",
        f"~{avg_lines_per_file:.0f} per file",
    )
    stats_table.add_row(
        "⚡ Functions",
        str(stats["total_functions"]),
        f"~{avg_functions_per_file:.1f} per file",
    )
    stats_table.add_row(
        "📦 Classes",
        str(stats["total_classes"]),
        _get_class_assessment(stats["total_classes"]),
    )
    stats_table.add_row(
        "🔧 Methods",
        str(stats["total_methods"]),
        _get_method_ratio_assessment(stats["total_methods"], stats["total_classes"]),
    )

    # Quality metrics with color coding
    issue_style = "red" if stats["files_with_issues"] > 0 else "green"
    import_style = (
        "red"
        if stats["unused_imports"] > 5
        else "yellow"
        if stats["unused_imports"] > 0
        else "green"
    )

    stats_table.add_row(
        "⚠️  Files with Issues",
        f"[{issue_style}]{stats['files_with_issues']}[/{issue_style}]",
        _get_issue_assessment(stats["files_with_issues"], stats["total_files"]),
    )
    stats_table.add_row(
        "🗂️  Unused Imports",
        f"[{import_style}]{stats['unused_imports']}[/{import_style}]",
        _get_import_assessment(stats["unused_imports"]),
    )

    # Repository status
    repo_status = "✅ Yes" if is_valid_git_repo(path) else "❌ No"
    repo_style = "green" if is_valid_git_repo(path) else "red"
    stats_table.add_row(
        "🔄 Git Repository",
        f"[{repo_style}]{repo_status}[/{repo_style}]",
        "Version controlled" if is_valid_git_repo(path) else "Consider using git",
    )

    console.print(stats_table)
    console.print()

    # Code quality score panel
    quality_color = (
        "green"
        if code_quality_score >= 80
        else "yellow"
        if code_quality_score >= 60
        else "red"
    )
    quality_panel = Panel(
        f"[bold {quality_color}]{code_quality_score:.0f}/100[/bold {quality_color}] 📊",
        title="Code Quality Score",
        title_align="center",
        style=quality_color,
    )

    # Recommendations panel
    recommendations = _generate_recommendations(stats, is_valid_git_repo(path))
    rec_panel = Panel(
        recommendations,
        title="💡 Recommendations",
        title_align="left",
        style="blue",
    )

    # Display panels side by side
    console.print(Columns([quality_panel, rec_panel], equal=True, expand=True))

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
                file_path_str = str(detail["file"])
                relative_path = Path(file_path_str).relative_to(path)
            except (ValueError, TypeError):
                file_path_str = str(detail["file"])
                relative_path = Path(file_path_str)

            detail_table.add_row(
                str(relative_path),
                str(detail["lines"]),
                str(detail["functions"]),
                str(detail["classes"]),
                str(detail["methods"]),
                str(detail["unused_imports"])
                if isinstance(detail["unused_imports"], int)
                and detail["unused_imports"] > 0
                else "-",
            )

        console.print(detail_table)


@app.command("find-refs")
def find_references(
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
    """Find all references to a function in the project."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(
        f"[blue]Searching for references to '{function_name}' in: {path}[/blue]",
    )

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
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
                content = file_path.read_text(encoding="utf-8")
                references = find_function_references(content, function_name)

                if references:
                    try:
                        relative_path = file_path.relative_to(path)
                    except ValueError:
                        relative_path = file_path
                    console.print(f"\n[green]{relative_path}[/green]")
                    for line_num, _col_offset in references:
                        lines = content.splitlines()
                        if 0 < line_num <= len(lines):
                            line_content = lines[line_num - 1].strip()
                            console.print(f"  Line {line_num}: {line_content}")
                            total_references += 1

            except Exception as e:
                console.print(f"[red]Error searching {file_path}: {e}[/red]")

            progress.advance(task)

    console.print()
    if total_references > 0:
        console.print(
            Panel.fit(
                f"[green]✅ Found {total_references} references to "
                f"'[bold]{function_name}[/bold]'[/green]",
                style="green",
            ),
        )
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


@app.command("unused-imports")
def find_unused_imports_cmd(
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
    """Find unused imports in Python files."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Finding unused imports in: {path}[/blue]")

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
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
                content = file_path.read_text(encoding="utf-8")
                unused = find_unused_imports(content)

                if unused:
                    files_with_unused += 1
                    try:
                        relative_path = file_path.relative_to(path)
                    except ValueError:
                        relative_path = file_path
                    console.print(f"\n[yellow]{relative_path}[/yellow]")

                    for import_name, line_num in unused:
                        console.print(
                            f"  Line {line_num}: unused import '{import_name}'",
                        )
                        total_unused += 1

                        if fix:
                            console.print(
                                "    [dim]Note: Automatic fixing not "
                                "implemented yet[/dim]",
                            )

            except Exception as e:
                console.print(f"[red]Error analyzing {file_path}: {e}[/red]")

            progress.advance(task)

    console.print()
    if total_unused == 0:
        console.print(
            Panel.fit(
                "[green]🎉 Excellent! No unused imports found[/green]\n"
                "Your code is clean and well-maintained!",
                title="Import Analysis Results",
                style="green",
            ),
        )
    else:
        impact_level = (
            "high" if total_unused > 10 else "medium" if total_unused > 5 else "low"
        )
        impact_color = (
            "red"
            if impact_level == "high"
            else "yellow"
            if impact_level == "medium"
            else "blue"
        )

        result_text = (
            f"Found [bold {impact_color}]{total_unused}[/bold {impact_color}] "
            f"unused imports in [bold]{files_with_unused}[/bold] files\n\n"
        )
        result_text += "💡 Benefits of removing unused imports:\n"
        result_text += "• Faster import times\n"
        result_text += "• Cleaner, more readable code\n"
        result_text += "• Reduced dependencies\n"
        result_text += "• Better IDE performance"

        if fix:
            result_text += (
                "\n\n[yellow]⚠️  Automatic fixing is not yet implemented[/yellow]"
            )
        else:
            result_text += (
                "\n\n[dim]Use [bold]--fix[/bold] flag to automatically "
                "remove them (when available)[/dim]"
            )

        console.print(
            Panel(
                result_text,
                title=f"🔍 Import Analysis Results ({impact_level.title()} Impact)",
                style=impact_color,
            ),
        )


@app.command("functions")
def analyze_functions(
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
    """Analyze functions and methods in the project."""
    if path is None:
        path = Path.cwd()

    if not path.exists():
        console.print(f"[red]Error: Path {path} does not exist[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Analyzing functions in: {path}[/blue]")

    # Get all Python files
    ignored_dirs = set() if include_tests else {"tests", "test"}
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
                content = file_path.read_text(encoding="utf-8")

                # Extract functions
                functions = extract_function_signatures(content)
                for func in functions:
                    try:
                        func["file"] = str(file_path.relative_to(path))
                    except ValueError:
                        func["file"] = str(file_path)
                    all_functions.append(func)

                # Extract methods
                methods = extract_class_methods(content, class_name)
                for method in methods:
                    try:
                        method["file"] = str(file_path.relative_to(path))
                    except ValueError:
                        method["file"] = str(file_path)
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
                args_list = func["args"] if isinstance(func["args"], list) else []
                args_str = ", ".join(str(arg) for arg in args_list) if args_list else ""
                row.append(args_str)
            row.append("✓" if func["is_async"] else "")
            func_table.add_row(*[str(item) for item in row])

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

        for method in sorted(
            all_methods,
            key=lambda x: (x["class_name"], x["method_name"]),
        ):
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
                str(method["class_name"]),
                str(method["method_name"]),
                str(method["file"]),
                str(method["line"]),
                method_type,
            )

        console.print(method_table)

    if not all_functions and not all_methods:
        console.print()
        console.print(
            Panel(
                "[yellow]Info: No functions or methods found in the "
                "analyzed files[/yellow]\n"
                "This might indicate:\n"
                "• Empty or non-functional Python files\n"
                "• Files containing only imports or constants\n"
                "• Analysis scope too narrow (try --include-tests)",
                title="Analysis Results",
                style="yellow",
            ),
        )
    else:
        # Add summary at the end
        console.print()
        summary_text = (
            f"✨ Analysis complete! Found [bold cyan]{len(all_functions)}[/bold cyan] "
            f"functions and [bold cyan]{len(all_methods)}[/bold cyan] methods"
        )
        if len(all_functions) > 20 or len(all_methods) > 20:
            summary_text += (
                "\n💡 Use filters like [dim]--class MyClass[/dim] or "
                "[dim]--signatures[/dim] for more focused analysis"
            )

        console.print(Panel.fit(summary_text, style="green"))


def _get_file_count_assessment(count: int) -> str:
    """Get assessment for file count."""
    if count < 5:
        return "Small project"
    if count < 20:
        return "Medium project"
    if count < 50:
        return "Large project"
    return "Very large project"


def _get_class_assessment(count: int) -> str:
    """Get assessment for class count."""
    if count == 0:
        return "Functional style"
    if count < 5:
        return "Simple structure"
    if count < 20:
        return "Moderate complexity"
    return "Complex architecture"


def _get_method_ratio_assessment(methods: int, classes: int) -> str:
    """Get assessment for method-to-class ratio."""
    if classes == 0:
        return "No classes"
    ratio = methods / classes
    if ratio < 3:
        return "Simple classes"
    if ratio < 8:
        return "Moderate complexity"
    return "Complex classes"


def _get_issue_assessment(issues: int, total_files: int) -> str:
    """Get assessment for files with issues."""
    if issues == 0:
        return "Clean codebase"
    percentage = (issues / total_files) * 100
    if percentage < 10:
        return "Minor issues"
    if percentage < 25:
        return "Some issues"
    return "Needs attention"


def _get_import_assessment(unused: int) -> str:
    """Get assessment for unused imports."""
    if unused == 0:
        return "Clean imports"
    if unused < 5:
        return "Minor cleanup"
    if unused < 15:
        return "Moderate cleanup"
    return "Major cleanup needed"


def _generate_recommendations(stats: dict, has_git: bool) -> str:
    """Generate recommendations based on analysis results."""
    recommendations = []

    # Code quality recommendations
    if stats["unused_imports"] > 0:
        recommendations.append(f"🧹 Remove {stats['unused_imports']} unused imports")

    if stats["files_with_issues"] > 0:
        recommendations.append(f"🔧 Fix issues in {stats['files_with_issues']} files")

    # Project structure recommendations
    if stats["total_functions"] > stats["total_methods"] * 3:
        recommendations.append("📦 Consider organizing code into classes")

    if stats["total_files"] > 20 and stats["total_classes"] < 5:
        recommendations.append("🏗️  Consider modular architecture")

    # Git recommendations
    if not has_git:
        recommendations.append("🔄 Initialize git repository for version control")

    # General recommendations
    avg_lines = (
        stats["total_lines"] / stats["total_files"] if stats["total_files"] > 0 else 0
    )
    if avg_lines > 500:
        recommendations.append("📝 Consider splitting large files")

    if not recommendations:
        recommendations.append("✅ Code structure looks good!")
        recommendations.append("🔍 Run detailed analysis with --verbose")

    return "\n".join(
        f"• {rec}" for rec in recommendations[:5]
    )  # Limit to 5 recommendations


if __name__ == "__main__":
    app()
