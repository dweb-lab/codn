import typer
from codn.cli_commands import git_cli, analyze_cli

app = typer.Typer(help="Codn CLI - Analyze and explore source code repositories.")

# 注册子命令组
app.add_typer(git_cli.app, name="git")
app.add_typer(analyze_cli.app, name="analyze")

if __name__ == "__main__":
    app()
