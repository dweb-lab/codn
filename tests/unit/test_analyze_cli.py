from pathlib import Path
from typer.testing import CliRunner

from codn.cli_commands.analyze_cli import analyze_project

runner = CliRunner()


def test_analyze_project_basic(fs, capsys):
    """Tests the basic functionality of the analyze_project command."""
    # Setup a fake file system
    project_path = Path("project")
    fs.create_dir(project_path)
    fs.create_file(
        project_path / "main.py",
        contents="""
import os

def hello():
    print("hello")
""",
    )
    fs.create_file(
        project_path / "utils.py",
        contents="""
import sys

def utility_function():
    return True
""",
    )
    fs.create_dir(project_path / "tests")
    fs.create_file(
        project_path / "tests" / "test_utils.py",
        contents="""
import pytest
from utils import utility_function

def test_utility():
    assert utility_function()
""",
    )

    # Run the function directly
    analyze_project(path=project_path)

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Project Analysis Complete" in output
    assert "Python Files" in output
    assert "2" in output  # main.py and utils.py
    assert "Total Lines" in output
    assert "Unused Imports" in output


def test_analyze_project_include_tests(fs, capsys):
    """Tests that the --include-tests flag includes test files in the analysis."""
    # Setup a fake file system
    project_path = Path("project")
    fs.create_dir(project_path)
    fs.create_file(
        project_path / "main.py",
        contents="""
import os

def hello():
    print("hello")
""",
    )
    fs.create_dir(project_path / "tests")
    fs.create_file(
        project_path / "tests" / "test_main.py",
        contents="""
import pytest
from main import hello

def test_hello():
    hello()
""",
    )

    # Run the function directly
    analyze_project(path=project_path, include_tests=True)

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Project Analysis Complete" in output
    assert "Python Files" in output
    assert "2" in output  # main.py and tests/test_main.py


def test_find_references(fs, capsys):
    """Tests the find_references command."""
    # Setup a fake file system
    project_path = Path("project")
    fs.create_dir(project_path)
    fs.create_file(
        project_path / "main.py",
        contents="""
def foo():
    pass

foo()
""",
    )

    # Run the function directly
    from codn.cli_commands.analyze_cli import find_references as find_refs_cmd

    find_refs_cmd(function_name="foo", path=project_path)

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Found 1 references to 'foo'" in output


def test_find_unused_imports(fs, capsys):
    """Tests the find_unused_imports_cmd command."""
    # Setup a fake file system
    project_path = Path("project")
    fs.create_dir(project_path)
    fs.create_file(
        project_path / "main.py",
        contents="""
import os
import sys

print(sys.version)
""",
    )

    # Run the function directly
    from codn.cli_commands.analyze_cli import find_unused_imports_cmd

    find_unused_imports_cmd(path=project_path)

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Found 1 unused imports" in output
    assert "unused import 'os'" in output


def test_analyze_functions(fs, capsys):
    """Tests the analyze_functions command."""
    # Setup a fake file system
    project_path = Path("project")
    fs.create_dir(project_path)
    fs.create_file(
        project_path / "main.py",
        contents="""
def foo():
    pass

class MyClass:
    def bar(self):
        pass
""",
    )

    # Run the function directly
    from codn.cli_commands.analyze_cli import analyze_functions

    analyze_functions(path=project_path)

    # Capture the output
    captured = capsys.readouterr()
    output = captured.out

    # Assertions
    assert "Functions (2)" in output
    assert "Methods (1)" in output
    assert "foo" in output
    assert "bar" in output
