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

    # Most popular commands
    console.print("\n[bold cyan]🌟 Most Popular Commands:[/bold cyan]")

    popular_table = Table(show_header=True, header_style="bold magenta")
    popular_table.add_column("Command", style="cyan", width=30)
    popular_table.add_column("Description", style="white")

    popular_table.add_row(
        "codn analyze project",
        "📊 Get comprehensive project overview & quality score"
    )
    popular_table.add_row(
        "codn analyze unused-imports",
        "🧹 Find and clean up unused imports"
    )
    popular_table.add_row(
        "codn analyze find-refs <function>",
        "🔍 Find where a function is referenced"
    )

    console.print(popular_table)

    # All available commands
    console.print("\n[bold cyan]📋 All Available Commands:[/bold cyan]")

    all_commands_table = Table(show_header=True, header_style="bold blue")
    all_commands_table.add_column("Category", style="bold cyan", width=15)
    all_commands_table.add_column("Command", style="green", width=25)
    all_commands_table.add_column("Description", style="white")

    all_commands_table.add_row(
        "Analysis", "analyze project", "Project statistics and quality metrics"
    )
    all_commands_table.add_row(
        "", "analyze unused-imports", "Detect unused import statements"
    )
    all_commands_table.add_row(
        "", "analyze functions", "List all functions and methods"
    )
    all_commands_table.add_row(
        "", "analyze find-refs", "Find function references"
    )
    all_commands_table.add_row(
        "Git", "git check", "Validate repository health"
    )

    console.print(all_commands_table)

    # Quick start guide
    console.print("\n[bold cyan]🚀 Quick Start Guide:[/bold cyan]")

    start_panel = Panel(
        "[bold white]New to codn? Start here:[/bold white]\n\n"
        "1️⃣  [green]codn analyze project[/green]        [dim]← Get overview of your codebase[/dim]\n"
        "2️⃣  [green]codn analyze unused-imports[/green] [dim]← Clean up your imports[/dim]\n"
        "3️⃣  [green]codn analyze functions[/green]      [dim]← Explore your functions[/dim]\n\n"
        "[bold yellow]💡 Pro tip:[/bold yellow] Use [green]--verbose[/green] flag for detailed output!",
        title="Getting Started",
        border_style="green"
    )
    console.print(start_panel)

    # Advanced examples
    console.print("\n[bold cyan]🔧 Advanced Examples:[/bold cyan]")
    examples = [
        "[dim]# Detailed project analysis[/dim]",
        "[green]codn analyze project --verbose[/green]",
        "",
        "[dim]# Find function usage across codebase[/dim]",
        "[green]codn analyze find-refs my_function[/green]",
        "",
        "[dim]# Analyze functions with signatures[/dim]",
        "[green]codn analyze functions --signatures[/green]"
    ]

    for example in examples:
        console.print(f"  {example}")

    # Help and resources
    console.print(f"\n[bold cyan]📚 Need Help?[/bold cyan]")
    help_info = [
        "[green]codn --help[/green]                Show this help screen",
        "[green]codn analyze[/green]               Show analysis tools overview",
        "[green]codn analyze --help[/green]        Show detailed analysis help",
        "[green]codn <command> --help[/green]      Show help for specific command"
    ]

    for info in help_info:
        console.print(f"  {info}")

    # Footer with resources
    console.print()
    footer_panel = Panel(
        "[bold blue]🔗 Resources[/bold blue]\n"
        "📖 Documentation: [link=https://github.com/dweb-lab/codn/tree/main/docs]github.com/dweb-lab/codn/docs[/link]\n"
        "🐛 Issues: [link=https://github.com/dweb-lab/codn/issues]github.com/dweb-lab/codn/issues[/link]\n"
        "⭐ Star us: [link=https://github.com/dweb-lab/codn]github.com/dweb-lab/codn[/link]",
        border_style="blue"
    )
    console.print(footer_panel)

if __name__ == "__main__":
    app()
