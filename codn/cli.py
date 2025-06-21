import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from codn.cli_commands import git_cli, analyze_cli

console = Console()

app = typer.Typer(
    help="🔍 Codn - A powerful toolkit for analyzing Python codebases.",
    rich_markup_mode="rich",
    invoke_without_command=True
)

# 注册子命令组
app.add_typer(git_cli.app, name="git", help="🔧 Git repository validation and health checks")
app.add_typer(analyze_cli.app, name="analyze", help="📊 Code analysis and statistics")

@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version information")
):
    """
    🔍 Codn - A powerful toolkit for analyzing Python codebases.

    Codn provides fast, accurate analysis of Python projects with beautiful output.
    Perfect for code exploration, quality checks, and refactoring assistance.

    🚀 Quick Start:
      codn analyze project              - Get project statistics
      codn analyze find-refs <function> - Find function references
      codn analyze unused-imports       - Detect unused imports
      codn git check                    - Validate Git repository

    📚 Documentation: https://github.com/dweb-lab/codn/tree/main/docs
    """
    if version:
        from codn import __version__
        console.print(f"[bold blue]codn[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()

    # 如果没有子命令，显示友好的欢迎信息
    if ctx.invoked_subcommand is None:
        show_welcome()

def show_welcome():
    """Display a friendly welcome message with usage examples."""

    # Welcome header
    welcome_text = Text()
    welcome_text.append("🔍 ", style="blue")
    welcome_text.append("Welcome to ", style="white")
    welcome_text.append("codn", style="bold blue")
    welcome_text.append(" - Python Code Analysis Toolkit", style="white")

    welcome_panel = Panel(
        welcome_text,
        title="[bold green]Welcome![/bold green]",
        subtitle="[dim]Analyze Python codebases with ease[/dim]",
        border_style="blue"
    )
    console.print(welcome_panel)

    # Quick start commands
    console.print("\n[bold cyan]🚀 Quick Start Commands:[/bold cyan]")

    commands_table = Table(show_header=True, header_style="bold magenta")
    commands_table.add_column("Command", style="cyan", width=30)
    commands_table.add_column("Description", style="white")

    commands_table.add_row(
        "codn analyze project",
        "📊 Get comprehensive project statistics"
    )
    commands_table.add_row(
        "codn analyze find-refs <function>",
        "🔍 Find where a function is used"
    )
    commands_table.add_row(
        "codn analyze unused-imports",
        "🧹 Detect unused import statements"
    )
    commands_table.add_row(
        "codn analyze functions",
        "📝 List all functions and methods"
    )
    commands_table.add_row(
        "codn git check",
        "🔧 Validate Git repository health"
    )

    console.print(commands_table)

    # Examples
    console.print("\n[bold cyan]💡 Usage Examples:[/bold cyan]")
    examples = [
        "[dim]# Analyze current directory[/dim]",
        "[green]codn analyze project[/green]",
        "",
        "[dim]# Find function references[/dim]",
        "[green]codn analyze find-refs my_function[/green]",
        "",
        "[dim]# Check for code quality issues[/dim]",
        "[green]codn analyze unused-imports[/green]"
    ]

    for example in examples:
        console.print(f"  {example}")

    # Help footer
    console.print(f"\n[bold cyan]📚 Get More Help:[/bold cyan]")
    console.print("  [green]codn --help[/green]           Show detailed help")
    console.print("  [green]codn analyze --help[/green]   Show analysis commands")
    console.print("  [green]codn git --help[/green]       Show git commands")

    console.print(f"\n[dim]💫 Documentation: https://github.com/dweb-lab/codn/tree/main/docs[/dim]")

if __name__ == "__main__":
    app()
