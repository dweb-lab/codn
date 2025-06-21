"""
Global pytest configuration and fixtures.

This file contains shared fixtures and configuration for all tests.
"""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
from loguru import logger

from codn.utils.pyright_lsp_client import LSPConfig, PyrightLSPClient, path_to_file_uri


# ==================== Test Configuration ====================


def pytest_configure(config):
    """Configure pytest behavior."""
    # Suppress loguru logs during tests unless explicitly requested
    logger.remove()
    if config.getoption("--verbose") >= 2:
        logger.add(
            lambda msg: print(msg, end=""),
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker("async")

        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker("integration")

        # Auto-mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker("unit")


# ==================== Shared Fixtures ====================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_python_file(temp_dir: Path) -> Path:
    """Create a sample Python file for testing."""
    content = '''"""Sample Python module for testing."""

class TestClass:
    """A test class."""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        """Return a greeting."""
        return f"Hello, {self.name}!"

    def calculate(self, x: int, y: int) -> int:
        """Calculate sum of two numbers."""
        return x + y


def standalone_function(data: str) -> str:
    """A standalone function."""
    return data.upper()


def another_function():
    """Another function with no parameters."""
    test_instance = TestClass("World")
    result = test_instance.greet()
    return result


if __name__ == "__main__":
    obj = TestClass("Test")
    print(obj.greet())
'''

    file_path = temp_dir / "sample.py"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_project_structure(temp_dir: Path) -> Path:
    """Create a sample project structure for testing."""
    # Create directory structure
    (temp_dir / "src" / "mypackage").mkdir(parents=True)
    (temp_dir / "tests").mkdir()

    # Create __init__.py files
    (temp_dir / "src" / "__init__.py").touch()
    (temp_dir / "src" / "mypackage" / "__init__.py").touch()

    # Create main module
    main_content = '''"""Main module."""

from .utils import helper_function

class MainClass:
    def __init__(self, value: int):
        self.value = value

    def process(self) -> str:
        return helper_function(self.value)
'''
    (temp_dir / "src" / "mypackage" / "main.py").write_text(main_content)

    # Create utils module
    utils_content = '''"""Utility functions."""

def helper_function(value: int) -> str:
    """Convert value to string with prefix."""
    return f"processed_{value}"

def another_helper(data: list) -> int:
    """Get length of data."""
    return len(data)
'''
    (temp_dir / "src" / "mypackage" / "utils.py").write_text(utils_content)

    return temp_dir


@pytest.fixture
def lsp_config() -> LSPConfig:
    """Create a test LSP configuration."""
    return LSPConfig(
        timeout=10.0,  # Shorter timeout for tests
        enable_file_watcher=False,  # Disable file watcher in tests
        log_level="ERROR",  # Reduce log noise
    )


@pytest.fixture
async def mock_lsp_client(lsp_config: LSPConfig) -> AsyncGenerator[Mock, None]:
    """Create a mock LSP client for testing."""
    mock_client = Mock(spec=PyrightLSPClient)
    mock_client.state = Mock()
    mock_client.config = lsp_config

    # Mock async methods
    mock_client.start = AsyncMock()
    mock_client.shutdown = AsyncMock()
    mock_client.send_did_open = AsyncMock()
    mock_client.send_did_change = AsyncMock()
    mock_client.send_did_close = AsyncMock()
    mock_client.send_references = AsyncMock(return_value=[])
    mock_client.send_definition = AsyncMock(return_value=[])
    mock_client.send_document_symbol = AsyncMock(return_value=[])

    return mock_client


@pytest.fixture
async def real_lsp_client(
    temp_dir: Path, lsp_config: LSPConfig,
) -> AsyncGenerator[PyrightLSPClient, None]:
    """Create a real LSP client for integration tests."""
    import shutil

    # Check if pyright-langserver is available
    if not shutil.which("pyright-langserver"):
        pytest.skip(
            "pyright-langserver not found. Install with: npm install -g pyright",
        )

    root_uri = path_to_file_uri(str(temp_dir))
    client = PyrightLSPClient(root_uri, lsp_config)

    try:
        await client.start()
        yield client
    except Exception as e:
        pytest.skip(f"Could not start LSP client: {e}")
    finally:
        try:
            await client.shutdown()
        except Exception:
            pass  # Ignore shutdown errors in tests


@pytest.fixture
def sample_symbols() -> list:
    """Sample LSP symbol data for testing."""
    return [
        {
            "name": "TestClass",
            "kind": 5,  # Class
            "location": {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 2, "character": 0},
                    "end": {"line": 15, "character": 0},
                },
            },
            "children": [
                {
                    "name": "__init__",
                    "kind": 12,  # Method
                    "location": {
                        "uri": "file:///test.py",
                        "range": {
                            "start": {"line": 5, "character": 4},
                            "end": {"line": 6, "character": 25},
                        },
                    },
                },
                {
                    "name": "greet",
                    "kind": 12,  # Method
                    "location": {
                        "uri": "file:///test.py",
                        "range": {
                            "start": {"line": 8, "character": 4},
                            "end": {"line": 10, "character": 35},
                        },
                    },
                },
            ],
        },
        {
            "name": "standalone_function",
            "kind": 12,  # Function
            "location": {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 17, "character": 0},
                    "end": {"line": 19, "character": 25},
                },
            },
        },
    ]


@pytest.fixture
def sample_diagnostics() -> list:
    """Sample LSP diagnostic data for testing."""
    return [
        {
            "range": {
                "start": {"line": 10, "character": 15},
                "end": {"line": 10, "character": 25},
            },
            "severity": 1,  # Error
            "message": "Undefined variable 'undefined_var'",
            "source": "Pyright",
        },
        {
            "range": {
                "start": {"line": 20, "character": 0},
                "end": {"line": 20, "character": 10},
            },
            "severity": 2,  # Warning
            "message": "Unused import 'os'",
            "source": "Pyright",
        },
    ]


# ==================== Pytest Markers ====================

pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning"),
]


# ==================== Helper Functions ====================


def skip_if_no_pyright():
    """Skip test if pyright is not available."""
    import shutil

    if not shutil.which("pyright-langserver"):
        pytest.skip("pyright-langserver not found")


def requires_network():
    """Mark test as requiring network access."""
    return pytest.mark.network


def slow_test():
    """Mark test as slow."""
    return pytest.mark.slow
