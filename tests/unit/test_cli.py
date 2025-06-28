from typer.testing import CliRunner

from codn.cli import app
from codn import __version__

runner = CliRunner()


def test_version_command():
    """Tests the --version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"codn version {__version__}" in result.stdout


def test_default_command_calls_analyze_project(mocker):
    """Tests that running `codn` without subcommands calls analyze_project."""
    mock_analyze_project = mocker.patch("codn.cli.analyze_project")

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    mock_analyze_project.assert_called_once()


def test_unused_command_calls_find_unused_imports_cmd(mocker):
    """Tests that the `unused` command calls find_unused_imports_cmd."""
    mock_find_unused_imports_cmd = mocker.patch("codn.cli.find_unused_imports_cmd")

    result = runner.invoke(app, ["unused"])

    assert result.exit_code == 0
    mock_find_unused_imports_cmd.assert_called_once()


def test_refs_command_calls_find_references(mocker):
    """Tests that the `refs` command calls find_references."""
    mock_find_references = mocker.patch("codn.cli.find_references")

    result = runner.invoke(app, ["refs", "my_func"])

    assert result.exit_code == 0
    mock_find_references.assert_called_once_with("my_func", None, include_tests=False)


def test_funcs_command_calls_analyze_functions(mocker):
    """Tests that the `funcs` command calls analyze_functions."""
    mock_analyze_functions = mocker.patch("codn.cli.analyze_functions")

    result = runner.invoke(app, ["funcs"])

    assert result.exit_code == 0
    mock_analyze_functions.assert_called_once_with(
        None, class_name=None, show_signatures=False, include_tests=False
    )
