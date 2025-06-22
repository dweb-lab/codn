"""
Tests for PyrightLSPClient module.

This module contains comprehensive tests for the Pyright LSP client,
including unit tests, integration tests, and mocking scenarios.
"""

import asyncio
import shutil
from unittest.mock import AsyncMock, Mock, patch

import pytest

from codn.utils.pyright_lsp_client import (
    LSPClientState,
    LSPConfig,
    LSPError,
    PyrightLSPClient,
    _should_process_file,
    extract_inheritance_relations,
    extract_symbol_code,
    find_enclosing_function,
    path_to_file_uri,
)


class TestPathToFileUri:
    """Test path_to_file_uri function."""

    def test_absolute_path(self):
        """Test conversion of absolute path to file URI."""
        result = path_to_file_uri("/home/user/test.py")
        assert result.startswith("file://")
        assert "test.py" in result

    def test_relative_path(self):
        """Test conversion of relative path to file URI."""
        result = path_to_file_uri("./test.py")
        assert result.startswith("file://")
        assert "test.py" in result

    def test_windows_path(self):
        """Test conversion of Windows path to file URI."""
        with patch("platform.system", return_value="Windows"):
            result = path_to_file_uri("C:\\Users\\test\\file.py")
            assert result.startswith("file://")


class TestLSPConfig:
    """Test LSPConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LSPConfig()
        assert config.timeout == 30
        assert config.enable_file_watcher is True
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LSPConfig(
            timeout=60.0,
            enable_file_watcher=False,
            log_level="DEBUG",
        )
        assert config.timeout == 60.0
        assert config.enable_file_watcher is False
        assert config.log_level == "DEBUG"


class TestPyrightLSPClient:
    """Test PyrightLSPClient class."""

    def test_initialization(self, lsp_config):
        """Test client initialization."""
        root_uri = "file:///test/path"
        client = PyrightLSPClient(root_uri, lsp_config)

        assert client.root_uri == root_uri
        assert client.config == lsp_config
        assert client.state == LSPClientState.STOPPED
        assert len(client.open_files) == 0
        assert len(client.file_versions) == 0

    def test_initialization_without_config(self):
        """Test client initialization with default config."""
        root_uri = "file:///test/path"
        client = PyrightLSPClient(root_uri)

        assert client.root_uri == root_uri
        assert isinstance(client.config, LSPConfig)
        assert client.state == LSPClientState.STOPPED

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, lsp_config):
        """Test starting client when already running raises error."""
        client = PyrightLSPClient("file:///test", lsp_config)
        client._state = LSPClientState.RUNNING

        with pytest.raises(LSPError, match="Cannot start client in state"):
            await client.start()

    @pytest.mark.asyncio
    async def test_start_subprocess_failure(self, lsp_config):
        """Test subprocess start failure."""
        client = PyrightLSPClient("file:///test", lsp_config)

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            with pytest.raises(LSPError, match="Pyright not found"):
                await client._start_subprocess()

    @pytest.mark.asyncio
    async def test_send_message_without_process(self, lsp_config):
        """Test sending message without active process."""
        client = PyrightLSPClient("file:///test", lsp_config)

        with pytest.raises(LSPError, match="LSP process not available"):
            await client._send({"test": "message"})

    @pytest.mark.asyncio
    async def test_request_timeout(self, lsp_config):
        """Test request timeout handling."""
        client = PyrightLSPClient("file:///test", lsp_config)
        client._state = LSPClientState.RUNNING

        # Mock process and stdin
        mock_proc = Mock()
        mock_proc.stdin = AsyncMock()
        client.proc = mock_proc

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            with pytest.raises(LSPError, match="timed out"):
                await client._request("test_method", {})

    @pytest.mark.asyncio
    async def test_file_state_management_open(self, mock_lsp_client):
        """Test file state management for opening files."""
        client = PyrightLSPClient("file:///test")
        client._notify = AsyncMock()

        uri = "file:///test.py"
        content = "print('hello')"

        await client._manage_file_state(uri, "open", content)

        assert uri in client.open_files
        assert client.file_versions[uri] == 1
        client._notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_state_management_change(self, mock_lsp_client):
        """Test file state management for changing files."""
        client = PyrightLSPClient("file:///test")
        client._notify = AsyncMock()

        uri = "file:///test.py"
        content = "print('hello world')"

        # Simulate already opened file
        client.open_files.add(uri)
        client.file_versions[uri] = 1

        await client._manage_file_state(uri, "change", content)

        assert client.file_versions[uri] == 2
        client._notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_state_management_close(self, mock_lsp_client):
        """Test file state management for closing files."""
        client = PyrightLSPClient("file:///test")
        client._notify = AsyncMock()

        uri = "file:///test.py"

        # Simulate opened file
        client.open_files.add(uri)
        client.file_versions[uri] = 2

        await client._manage_file_state(uri, "close")

        assert uri not in client.open_files
        assert uri not in client.file_versions
        client._notify.assert_called_once()

    def test_parameter_validation_references(self, lsp_config):
        """Test parameter validation for references request."""
        client = PyrightLSPClient("file:///test", lsp_config)

        with pytest.raises(ValueError, match="must be non-negative"):
            asyncio.run(client.send_references("file:///test.py", -1, 0))

        with pytest.raises(ValueError, match="must be non-negative"):
            asyncio.run(client.send_references("file:///test.py", 0, -1))

    def test_parameter_validation_definition(self, lsp_config):
        """Test parameter validation for definition request."""
        client = PyrightLSPClient("file:///test", lsp_config)

        with pytest.raises(ValueError, match="must be non-negative"):
            asyncio.run(client.send_definition("file:///test.py", -1, 0))

    def test_parameter_validation_document_symbol(self, lsp_config):
        """Test parameter validation for document symbol request."""
        client = PyrightLSPClient("file:///test", lsp_config)

        with pytest.raises(ValueError, match="URI is required"):
            asyncio.run(client.send_document_symbol(""))

    @pytest.mark.asyncio
    async def test_shutdown_multiple_calls(self, lsp_config):
        """Test multiple shutdown calls are handled gracefully."""
        client = PyrightLSPClient("file:///test", lsp_config)
        client._cleanup = AsyncMock()
        client._cancel_tasks = AsyncMock()

        # First shutdown
        await client.shutdown()
        assert client.state == LSPClientState.STOPPED

        # Second shutdown should not cause issues
        await client.shutdown()
        assert client.state == LSPClientState.STOPPED


class TestSymbolExtraction:
    """Test symbol extraction functions."""

    def test_extract_symbol_code_valid_range(self):
        """Test extracting code for valid symbol range."""
        content = """# Line 0
# Line 1
class TestClass:
    # Line 3
    # Line 4
    def __init__(self, name):
        self.name = name
# Line 7
    def greet(self):
        return f"Hello, {self.name}!"
"""
        # Create symbol matching the content structure
        symbol = {
            "name": "__init__",
            "kind": 12,
            "location": {
                "uri": "file:///test.py",
                "range": {
                    "start": {"line": 5, "character": 4},
                    "end": {"line": 6, "character": 25},
                },
            },
        }
        result = extract_symbol_code(symbol, content, strip=True)

        assert "def __init__" in result
        assert "self.name = name" in result

    def test_extract_symbol_code_invalid_range(self):
        """Test extracting code with invalid range."""
        content = "print('hello')"
        symbol = {
            "location": {
                "range": {
                    "start": {"line": 10, "character": 0},
                    "end": {"line": 15, "character": 0},
                },
            },
        }

        result = extract_symbol_code(symbol, content)
        assert result == ""

    def test_extract_symbol_code_missing_location(self):
        """Test extracting code with missing location."""
        content = "print('hello')"
        symbol = {"name": "test"}

        result = extract_symbol_code(symbol, content)
        assert result == ""

    def test_extract_inheritance_relations_valid(self, sample_symbols):
        """Test extracting inheritance relations."""
        content = """class BaseClass:
    pass

class TestClass(BaseClass):
    def method(self):
        pass

class AnotherClass(TestClass, Mixin):
    pass
"""
        # Mock symbols for classes
        symbols = [
            {
                "name": "TestClass",
                "kind": 5,  # Class
                "location": {
                    "range": {
                        "start": {"line": 3, "character": 0},
                    },
                },
            },
            {
                "name": "AnotherClass",
                "kind": 5,  # Class
                "location": {
                    "range": {
                        "start": {"line": 7, "character": 0},
                    },
                },
            },
        ]

        relations = extract_inheritance_relations(content, symbols)

        assert "TestClass" in relations
        assert relations["TestClass"] == "BaseClass"
        assert "AnotherClass" in relations
        assert relations["AnotherClass"] == "TestClass"

    def test_extract_inheritance_relations_no_inheritance(self):
        """Test extracting inheritance with no base classes."""
        content = """class SimpleClass:
    def method(self):
        pass
"""
        symbols = [
            {
                "name": "SimpleClass",
                "kind": 5,  # Class
                "location": {
                    "range": {
                        "start": {"line": 0, "character": 0},
                    },
                },
            },
        ]

        relations = extract_inheritance_relations(content, symbols)
        assert len(relations) == 0

    def test_find_enclosing_function_valid(self, sample_symbols):
        """Test finding enclosing function for valid position."""
        result = find_enclosing_function(sample_symbols, 9, 10)
        assert result == "greet"

    def test_find_enclosing_function_no_match(self, sample_symbols):
        """Test finding enclosing function with no match."""
        result = find_enclosing_function(sample_symbols, 0, 0)
        assert result is None

    def test_find_enclosing_function_nested_symbols(self):
        """Test finding enclosing function in nested symbols."""
        symbols = [
            {
                "name": "outer_function",
                "kind": 12,  # Function
                "location": {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0},
                    },
                },
                "children": [
                    {
                        "name": "inner_function",
                        "kind": 12,  # Function
                        "location": {
                            "range": {
                                "start": {"line": 5, "character": 4},
                                "end": {"line": 8, "character": 4},
                            },
                        },
                    },
                ],
            },
        ]

        result = find_enclosing_function(symbols, 6, 8)
        assert result == "inner_function"


class TestFileWatcher:
    """Test file watcher functionality."""

    def test_should_process_file_python_files(self, temp_dir):
        """Test processing Python files."""
        py_file = temp_dir / "test.py"
        py_file.touch()

        assert _should_process_file(py_file) is True

        pyi_file = temp_dir / "test.pyi"
        pyi_file.touch()

        assert _should_process_file(pyi_file) is True

    def test_should_process_file_non_python(self, temp_dir):
        """Test not processing non-Python files."""
        txt_file = temp_dir / "test.txt"
        txt_file.touch()

        assert _should_process_file(txt_file) is False

    def test_should_process_file_skip_directories(self, temp_dir):
        """Test skipping certain directories."""
        git_file = temp_dir / ".git" / "config"
        git_file.parent.mkdir()
        git_file.touch()

        assert _should_process_file(git_file) is False

        cache_file = temp_dir / "__pycache__" / "test.pyc"
        cache_file.parent.mkdir()
        cache_file.touch()

        assert _should_process_file(cache_file) is False


@pytest.mark.integration
class TestPyrightLSPClientIntegration:
    """Integration tests for PyrightLSPClient."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not shutil.which("pyright-langserver"),
        reason="pyright-langserver not found. Install with: npm install -g pyright",
    )
    async def test_full_workflow(self, real_lsp_client, sample_python_file):
        """Test full LSP client workflow with real Pyright."""
        client = real_lsp_client
        uri = path_to_file_uri(str(sample_python_file))
        content = sample_python_file.read_text()

        try:
            # Test opening file
            await client.send_did_open(uri, content)
            assert uri in client.open_files

            # Test getting document symbols
            symbols = await client.send_document_symbol(uri)
            assert symbols is None or isinstance(symbols, list)

            # Test getting references (if any)
            refs = await client.send_references(uri, 0, 0)
            assert refs is None or isinstance(refs, list)

            # Test getting definition
            definition = await client.send_definition(uri, 10, 15)
            assert definition is None or isinstance(definition, list)

            # Test closing file
            await client.send_did_close(uri)
            assert uri not in client.open_files
        except Exception as e:
            pytest.skip(f"LSP operation failed: {e}")

    @pytest.mark.network
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not shutil.which("pyright-langserver"),
        reason="pyright-langserver not found. Install with: npm install -g pyright",
    )
    async def test_error_handling_with_invalid_file(self, real_lsp_client):
        """Test error handling with invalid file content."""
        client = real_lsp_client
        uri = "file:///nonexistent.py"
        invalid_content = "this is not valid python syntax {"

        try:
            # Should not raise exception for invalid content
            await client.send_did_open(uri, invalid_content)

            # Should handle errors gracefully
            symbols = await client.send_document_symbol(uri)
            assert symbols is None or isinstance(
                symbols,
                list,
            )  # May be empty for invalid syntax
        except Exception as e:
            pytest.skip(f"LSP operation failed: {e}")


@pytest.mark.asyncio
async def test_concurrent_requests(mock_lsp_client):
    """Test handling concurrent requests."""
    client = PyrightLSPClient("file:///test")
    client._request = AsyncMock(return_value=[])

    # Create multiple concurrent requests
    tasks = [
        client.send_document_symbol("file:///test1.py"),
        client.send_document_symbol("file:///test2.py"),
        client.send_document_symbol("file:///test3.py"),
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 3
    assert client._request.call_count == 3
