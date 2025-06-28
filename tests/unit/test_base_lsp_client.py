from pathlib import Path
import pytest

from codn.utils.base_lsp_client import (
    path_to_file_uri,
    extract_symbol_code,
    get_client,
    get_snippet,
)


def test_path_to_file_uri():
    """Tests the path_to_file_uri function."""
    # Test with a simple path
    path = Path("/tmp/test_file.py")
    expected_uri = path.resolve().as_uri()
    assert path_to_file_uri(str(path)) == expected_uri

    # Test with a relative path (should resolve to absolute)
    path = Path("relative/path/to/file.txt")
    expected_uri = path.resolve().as_uri()
    assert path_to_file_uri(str(path)) == expected_uri


def test_extract_symbol_code_single_line():
    """Tests extract_symbol_code for a single-line symbol."""
    content = "def my_func(): pass"
    symbol = {
        "location": {
            "range": {
                "start": {"line": 0, "character": 4},
                "end": {"line": 0, "character": 11},
            }
        }
    }
    assert extract_symbol_code(symbol, content) == "def my_func(): pass"
    assert extract_symbol_code(symbol, content, strip=True) == "my_func"


def test_extract_symbol_code_multi_line():
    """Tests extract_symbol_code for a multi-line symbol."""
    content = "def my_func():\n    return self.value"
    symbol = {
        "location": {
            "range": {
                "start": {"line": 0, "character": 4},
                "end": {"line": 1, "character": 23},
            }
        }
    }
    expected_code = "def my_func():\n    return self.value"
    assert extract_symbol_code(symbol, content) == expected_code

    expected_stripped_code = "my_func():\n    return self.value"
    assert extract_symbol_code(symbol, content, strip=True) == expected_stripped_code


@pytest.mark.asyncio
async def test_get_client(mocker, fs):
    """Tests the get_client function."""
    # Mock dependencies
    mock_detect_dominant_languages = mocker.patch(
        "codn.utils.base_lsp_client.detect_dominant_languages",
        return_value=["python"],
    )

    # Define a mock BaseLSPClient class
    class MockBaseLSPClient:
        def __init__(self, root_uri):
            self.root_uri = root_uri
            self.open_files = []
            self.is_closing = False
            self.did_open_calls = []

        async def start(self, lang):
            pass

        async def send_did_open(self, uri, content, language_id):
            self.did_open_calls.append((uri, content, language_id))
            self.open_files.append(uri)

        async def shutdown(self):
            pass

    # Patch the BaseLSPClient class itself to return our mock instance
    mocker.patch(
        "codn.utils.base_lsp_client.BaseLSPClient",
        side_effect=MockBaseLSPClient,
    )

    # 1. 创建模拟文件系统中的文件
    fs.create_file("/file1.py", contents="print('hello')")
    fs.create_file("/file2.py", contents="import os")

    file1_path = Path("/file1.py")
    file2_path = Path("/file2.py")

    # 获取 pyfakefs 生成的实际 URI
    file1_uri = file1_path.as_uri()
    file2_uri = file2_path.as_uri()

    # Call the function
    client = await get_client("/")

    # Assertions
    mock_detect_dominant_languages.assert_called_once_with("/")
    # Assert that the mock client's start method was called (implicitly by get_client)
    # We don't have a direct mock object for the client instance, so we check its internal state

    # Assert send_did_open calls on the client instance returned by get_client
    assert len(client.did_open_calls) == 2
    assert (file1_uri, "print('hello')", "python") in client.did_open_calls
    assert (file2_uri, "import os", "python") in client.did_open_calls

    assert client is not None


def test_extract_symbol_code_invalid_range():
    """Tests extract_symbol_code with an invalid range."""
    content = "def my_func(): pass"
    symbol = {
        "location": {
            "range": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 10, "character": 5},
            }
        }
    }
    assert extract_symbol_code(symbol, content) == ""


def test_extract_symbol_code_empty_content():
    """Tests extract_symbol_code with empty content."""
    content = ""
    symbol = {
        "location": {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 5},
            }
        }
    }
    assert extract_symbol_code(symbol, content) == ""


@pytest.mark.asyncio
async def test_get_snippet(mocker, fs):
    """Tests the get_snippet function."""
    # Create a dummy file
    file_path = Path("/tmp/project/test_file.py")
    file_content = "def my_function():\n    return 1"
    fs.create_file(file_path, contents=file_content)
    file_uri = file_path.as_uri()

    # Mock BaseLSPClient and its methods
    mock_client_instance = mocker.AsyncMock()
    mock_client_instance.open_files = [file_uri]
    mock_client_instance.is_closing = False
    mock_client_instance.send_document_symbol.return_value = [
        {
            "name": "my_function",
            "kind": 12,  # Function
            "location": {
                "uri": file_uri,
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 1, "character": 11},
                },
            },
        }
    ]
    mock_client_instance.read_file.return_value = file_content  # Add this line
    mock_client_instance.shutdown = mocker.AsyncMock()

    mocker.patch(
        "codn.utils.base_lsp_client.BaseLSPClient",
        return_value=mock_client_instance,
    )
    mocker.patch(
        "codn.utils.base_lsp_client.get_client",
        return_value=mock_client_instance,
    )

    # Call the function
    snippets = await get_snippet(entity_name="my_function", path_str="/tmp/project")

    # Assertions
    mock_client_instance.send_document_symbol.assert_called_once_with(file_uri)
    mock_client_instance.shutdown.assert_called_once()
    assert snippets == [file_content]
