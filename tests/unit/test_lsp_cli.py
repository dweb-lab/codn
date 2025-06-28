import pytest
from typer.testing import CliRunner

from codn.cli_commands.lsp_cli import search

runner = CliRunner()


@pytest.mark.asyncio
async def test_search(fs, mocker, capsys):
    """Tests the lsp search command."""
    # Setup a fake file system
    fs.create_file("project/main.py", contents="def foo(): pass")

    # Mock the async function
    mocker.patch(
        "codn.cli_commands.lsp_cli.get_snippet", return_value=["def foo(): pass"]
    )

    # Run the function directly
    await search(function_name="foo", path="project")

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Found 1 references to 'foo'" in output
    assert "==Code Snippet:" in output
    assert "def foo(): pass" in output


@pytest.mark.asyncio
async def test_find_references(fs, mocker, capsys):
    """Tests the lsp find_references command."""
    # Setup a fake file system
    fs.create_file("project/main.py", contents="def bar(): pass")

    # Mock the async function
    mocker.patch("codn.cli_commands.lsp_cli.get_refs", return_value=["def bar(): pass"])

    # Run the function directly
    from codn.cli_commands.lsp_cli import find_references

    await find_references(function_name="bar", path="project")

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Found 1 references to 'bar'" in output
    assert "==Refs:" in output
    assert "def bar(): pass" in output
