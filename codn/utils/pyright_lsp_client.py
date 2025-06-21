import asyncio
import json
import re
import signal
import sys
from pathlib import Path
from itertools import count
from watchfiles import awatch
from loguru import logger
from typing import Any, Optional, Dict, List, Set
from dataclasses import dataclass
from enum import Enum

PYRIGHT_COMMAND = ["pyright-langserver", "--stdio"]
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BUFFER_SIZE = 8192

def path_to_file_uri(path_str: str) -> str:
    """Convert a file path to a file URI."""
    return Path(path_str).resolve().as_uri()

class LSPError(Exception):
    """Custom exception for LSP-related errors."""
    pass

class LSPClientState(Enum):
    """LSP client state enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

@dataclass
class LSPConfig:
    """Configuration for LSP client."""
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    buffer_size: int = BUFFER_SIZE
    enable_file_watcher: bool = True
    log_level: str = "INFO"

class LSPClient:
    """Base LSP client interface."""

    async def start(self) -> None:
        """Start the LSP client."""
        raise NotImplementedError

    async def shutdown(self) -> None:
        """Shutdown the LSP client."""
        raise NotImplementedError

class PyrightLSPClient(LSPClient):
    """Pyright Language Server Protocol client."""

    def __init__(self, root_uri: str, config: Optional[LSPConfig] = None):
        self.root_uri = root_uri
        self.config = config or LSPConfig()
        self._msg_id = count(1)
        self.open_files: Set[str] = set()
        self.file_versions: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._pending: Dict[int, asyncio.Future] = {}
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._state = LSPClientState.STOPPED
        self._retry_count = 0

    @property
    def state(self) -> LSPClientState:
        """Get current client state."""
        return self._state

    async def start(self) -> None:
        """Start the LSP client."""
        if self._state != LSPClientState.STOPPED:
            raise LSPError(f"Cannot start client in state: {self._state}")

        self._state = LSPClientState.STARTING

        try:
            await self._start_subprocess()
            await self._initialize()
            self._state = LSPClientState.RUNNING
            logger.info("LSP client started successfully")
        except Exception as e:
            self._state = LSPClientState.STOPPED
            await self._cleanup()
            raise LSPError(f"Failed to start LSP client: {e}") from e

    async def _start_subprocess(self) -> None:
        """Start the Pyright subprocess."""
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *PYRIGHT_COMMAND,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Start response loop
            task = asyncio.create_task(self._response_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        except FileNotFoundError:
            raise LSPError("Pyright not found. Please install pyright-langserver.")
        except Exception as e:
            raise LSPError(f"Failed to start Pyright subprocess: {e}") from e

    async def _initialize(self) -> None:
        """Initialize the LSP connection."""
        init_params = {
            "processId": None,
            "rootUri": self.root_uri,
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": True,
                        "willSave": True,
                        "willSaveWaitUntil": True,
                        "didSave": True
                    },
                    "completion": {"dynamicRegistration": True},
                    "hover": {"dynamicRegistration": True},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {"dynamicRegistration": True}
                },
                "workspace": {
                    "applyEdit": True,
                    "workspaceEdit": {"documentChanges": True},
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "didChangeWatchedFiles": {"dynamicRegistration": True}
                }
            },
            "workspaceFolders": [{"uri": self.root_uri, "name": "workspace"}]
        }

        await self._request("initialize", init_params)
        await self._notify("initialized", {})

    async def _send(self, msg: Dict[str, Any]) -> None:
        """Send a message to the LSP server."""
        if not self.proc or not self.proc.stdin:
            raise LSPError("LSP process not available")

        try:
            data = json.dumps(msg).encode('utf-8')
            header = f"Content-Length: {len(data)}\r\n\r\n".encode('utf-8')
            self.proc.stdin.write(header + data)
            await self.proc.stdin.drain()
        except Exception as e:
            raise LSPError(f"Failed to send message: {e}") from e

    async def _request(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a request and wait for response."""
        if self._state != LSPClientState.RUNNING and method != "initialize":
            raise LSPError(f"Cannot send request in state: {self._state}")

        msg_id = next(self._msg_id)
        future = asyncio.Future()

        async with self._lock:
            self._pending[msg_id] = future

        try:
            await self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": method,
                "params": params
            })

            result = await asyncio.wait_for(future, timeout=self.config.timeout)

            if isinstance(result, dict) and "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise LSPError(f"LSP request failed: {error_msg}")

            return result.get("result") if isinstance(result, dict) else result

        except asyncio.TimeoutError:
            raise LSPError(f"Request {method} (id: {msg_id}) timed out")
        except Exception as e:
            if isinstance(e, LSPError):
                raise
            raise LSPError(f"Request {method} failed: {e}") from e
        finally:
            async with self._lock:
                self._pending.pop(msg_id, None)

    async def _notify(self, method: str, params: Dict[str, Any]) -> None:
        """Send a notification (no response expected)."""
        if self._state not in (LSPClientState.RUNNING, LSPClientState.STARTING):
            if method not in ("initialized", "exit"):
                raise LSPError(f"Cannot send notification in state: {self._state}")

        await self._send({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })

    async def _response_loop(self) -> None:
        """Main response processing loop."""
        try:
            while (self.proc and self.proc.stdout and
                   not self._shutdown_event.is_set() and
                   self.proc.returncode is None):

                try:
                    headers = await self._read_headers()
                    if not headers:
                        continue

                    content_length = int(headers.get("Content-Length", 0))
                    if content_length <= 0:
                        continue

                    message = await self._read_body(content_length)
                    if message:
                        await self._handle_message(message)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if not self._shutdown_event.is_set():
                        logger.error(f"Response loop error: {e}")
                        # Try to recover from non-critical errors
                        await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._shutdown_event.is_set():
                logger.error(f"Fatal response loop error: {e}")
        finally:
            logger.debug("Response loop ended")

    async def _read_headers(self) -> Dict[str, str]:
        """Read LSP message headers."""
        headers = {}

        while True:
            line = await self._read_line()
            if not line:
                break

            if line == b"\r\n":
                break

            try:
                decoded = line.decode('utf-8', errors='replace').strip()
                if ":" in decoded:
                    key, value = decoded.split(":", 1)
                    headers[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Failed to parse header line: {e}")

        return headers

    async def _read_line(self) -> bytes:
        """Read a single line from the LSP stream."""
        if not self.proc or not self.proc.stdout:
            return b""

        line = bytearray()
        try:
            while True:
                char = await self.proc.stdout.read(1)
                if not char:
                    break

                line.extend(char)
                if line.endswith(b"\r\n"):
                    break

        except Exception as e:
            logger.debug(f"Error reading line: {e}")

        return bytes(line)

    async def _read_body(self, length: int) -> Optional[Dict[str, Any]]:
        """Read LSP message body."""
        if not self.proc or not self.proc.stdout:
            return None

        try:
            body = await self.proc.stdout.read(length)
            if not body:
                return None

            return json.loads(body.decode('utf-8', errors='replace'))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read message body: {e}")
            return None

    async def _handle_message(self, msg: Dict[str, Any]) -> None:
        """Handle incoming LSP messages."""
        try:
            # Handle responses
            if msg_id := msg.get("id"):
                async with self._lock:
                    if future := self._pending.get(msg_id):
                        if not future.done():
                            future.set_result(msg)
                        return

            # Handle notifications
            method = msg.get("method")
            if not method:
                return

            params = msg.get("params", {})

            if method == "textDocument/publishDiagnostics":
                await self._handle_diagnostics(params)
            elif method == "window/logMessage":
                await self._handle_log_message(params)
            elif method == "window/showMessage":
                await self._handle_show_message(params)
            else:
                logger.debug(f"Unhandled LSP notification: {method}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_diagnostics(self, params: Dict[str, Any]) -> None:
        """Handle diagnostic notifications."""
        uri = params.get("uri", "")
        diagnostics = params.get("diagnostics", [])

        if diagnostics:
            logger.info(f"Diagnostics for {uri}: {len(diagnostics)} issues")
            for diag in diagnostics:
                severity = diag.get("severity", 1)
                message = diag.get("message", "")
                range_info = diag.get("range", {})
                line = range_info.get("start", {}).get("line", 0)
                logger.debug(f"  Line {line + 1}: {message} (severity: {severity})")

    async def _handle_log_message(self, params: Dict[str, Any]) -> None:
        """Handle log message notifications."""
        message = params.get("message", "")
        msg_type = params.get("type", 1)

        if msg_type == 1:  # Error
            logger.error(f"LSP: {message}")
        elif msg_type == 2:  # Warning
            logger.warning(f"LSP: {message}")
        elif msg_type == 3:  # Info
            logger.info(f"LSP: {message}")
        else:  # Log
            logger.debug(f"LSP: {message}")

    async def _handle_show_message(self, params: Dict[str, Any]) -> None:
        """Handle show message notifications."""
        message = params.get("message", "")
        msg_type = params.get("type", 1)
        logger.info(f"LSP Message (type {msg_type}): {message}")

    async def send_did_open(self, uri: str, content: str, language_id: str = "python") -> None:
        """Send textDocument/didOpen notification."""
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didOpen")

        async with self._lock:
            if uri in self.open_files:
                # File already open, send change instead
                self.file_versions[uri] = self.file_versions.get(uri, 0) + 1
                await self._notify("textDocument/didChange", {
                    "textDocument": {
                        "uri": uri,
                        "version": self.file_versions[uri]
                    },
                    "contentChanges": [{"text": content}]
                })
                return

            # Open new file
            self.open_files.add(uri)
            self.file_versions[uri] = 1

        try:
            await self._notify("textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": content
                }
            })
        except Exception as e:
            # Rollback state on error
            async with self._lock:
                self.open_files.discard(uri)
                self.file_versions.pop(uri, None)
            raise LSPError(f"Failed to send didOpen for {uri}: {e}") from e

    async def send_did_change(self, uri: str, content: str) -> None:
        """Send textDocument/didChange notification."""
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didChange")

        async with self._lock:
            if uri not in self.open_files:
                # File not open, send open instead
                await self.send_did_open(uri, content)
                return

            self.file_versions[uri] = self.file_versions.get(uri, 0) + 1
            version = self.file_versions[uri]

        await self._notify("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}]
        })

    async def send_did_close(self, uri: str) -> None:
        """Send textDocument/didClose notification."""
        if not uri:
            raise ValueError("Invalid URI for didClose")

        async with self._lock:
            if uri not in self.open_files:
                return

            self.open_files.remove(uri)
            self.file_versions.pop(uri, None)

        await self._notify("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })

    async def send_references(self, uri: str, line: int, character: int) -> Any:
        """Send textDocument/references request."""
        if line < 0 or character < 0:
            raise ValueError("Line and character must be non-negative")

        return await self._request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": False}
        })

    async def send_definition(self, uri: str, line: int, character: int) -> Any:
        """Send textDocument/definition request."""
        if line < 0 or character < 0:
            raise ValueError("Line and character must be non-negative")

        return await self._request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        })

    async def send_document_symbol(self, uri: str) -> Any:
        """Send textDocument/documentSymbol request."""
        if not uri:
            raise ValueError("URI is required for documentSymbol")

        return await self._request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })

    async def shutdown(self) -> None:
        """Shutdown the LSP client gracefully."""
        if self._state == LSPClientState.STOPPING:
            await self._shutdown_event.wait()
            return

        if self._state == LSPClientState.STOPPED:
            return

        self._state = LSPClientState.STOPPING
        logger.info("Shutting down LSP client...")

        try:
            # Signal shutdown to all components
            self._shutdown_event.set()

            # Cancel all pending requests
            async with self._lock:
                for future in self._pending.values():
                    if not future.done():
                        future.cancel()
                self._pending.clear()

            # Send LSP shutdown sequence
            if self.proc and self._state == LSPClientState.STOPPING:
                try:
                    await asyncio.wait_for(self._request("shutdown", {}), timeout=5.0)
                    await self._notify("exit", {})
                except (asyncio.TimeoutError, LSPError):
                    logger.warning("LSP shutdown sequence failed or timed out")
                except Exception as e:
                    logger.error(f"Error during LSP shutdown: {e}")

            # Cancel and wait for tasks
            await self._cancel_tasks()

            # Clean up resources
            await self._cleanup()

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._state = LSPClientState.STOPPED
            logger.info("LSP client shutdown complete")

    async def _cancel_tasks(self) -> None:
        """Cancel all running tasks."""
        if not self._tasks:
            return

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete within timeout")
            finally:
                self._tasks.clear()

    async def _cleanup(self) -> None:
        """Clean up all resources."""
        # Close subprocess
        if self.proc:
            try:
                if self.proc.stdin and not self.proc.stdin.is_closing():
                    self.proc.stdin.close()
                    await self.proc.stdin.wait_closed()
            except Exception as e:
                logger.debug(f"Error closing stdin: {e}")

            # Terminate process
            if self.proc.returncode is None:
                self.proc.terminate()
                try:
                    await asyncio.wait_for(self.proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Process termination timed out, killing...")
                    self.proc.kill()
                    await self.proc.wait()

        # Clear state
        self.open_files.clear()
        self.file_versions.clear()

        async with self._lock:
            self._pending.clear()

def extract_symbol_code(sym: Dict[str, Any], content: str, strip: bool = False) -> str:
    """Extract code for a symbol from content."""
    try:
        rng = sym.get('location', {}).get('range', {})
        if not rng:
            return ""

        start = rng.get("start", {})
        end = rng.get("end", {})

        start_line = start.get("line", 0)
        start_char = start.get("character", 0)
        end_line = end.get("line", 0)
        end_char = end.get("character", 0)

        lines = content.splitlines()

        if start_line < 0 or end_line < 0 or start_line >= len(lines) or end_line >= len(lines):
            return ""

        if start_line == end_line:
            line = lines[start_line]
            if strip:
                return line[start_char:end_char]
            return line

        code_lines = lines[start_line:end_line + 1]
        if not code_lines:
            return ""

        if strip:
            code_lines[0] = code_lines[0][start_char:]
            if len(code_lines) > 1:
                code_lines[-1] = code_lines[-1][:end_char]

        return "\n".join(code_lines)

    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.debug(f"Error extracting symbol code: {e}")
        return ""

def extract_inheritance_relations(content: str, symbols: List[Dict[str, Any]]) -> Dict[str, str]:
    """Extract class inheritance relations from symbols."""
    try:
        lines = content.splitlines()
        relations = {}

        for symbol in symbols:
            # Check if it's a class (kind 5 in LSP)
            if symbol.get("kind") != 5:
                continue

            name = symbol.get("name")
            if not name:
                continue

            # Get the line where the class is defined
            location = symbol.get("location", {})
            rng = location.get("range", {})
            start = rng.get("start", {})
            line_num = start.get("line", 0)

            if line_num < 0 or line_num >= len(lines):
                continue

            line = lines[line_num].strip()

            # Parse class definition for inheritance
            pattern = rf"class\s+{re.escape(name)}\s*\((.*?)\)\s*:"
            match = re.search(pattern, line)

            if match:
                base_classes = match.group(1).strip()
                if base_classes:
                    # Take the first base class
                    first_base = base_classes.split(",")[0].strip()
                    if first_base:
                        relations[name] = first_base

        return relations

    except Exception as e:
        logger.debug(f"Error extracting inheritance relations: {e}")
        return {}

def find_enclosing_function(symbols: List[Dict[str, Any]], line: int, character: int) -> Optional[str]:
    """Find the function that encloses the given position."""
    def _search_symbols(syms: List[Dict[str, Any]]) -> Optional[str]:
        result = None

        for symbol in syms:
            # Check if it's a function (kind 12 in LSP)
            if symbol.get('kind') == 12:
                location = symbol.get('location', {})
                rng = location.get('range', {})
                start = rng.get('start', {})
                end = rng.get('end', {})

                start_line = start.get('line', -1)
                end_line = end.get('line', -1)

                # Check if position is within function bounds
                if start_line <= line <= end_line:
                    result = symbol.get('name', '')

            # Search in nested symbols
            children = symbol.get('children', [])
            if children:
                nested_result = _search_symbols(children)
                if nested_result:
                    result = nested_result

        return result

    try:
        return _search_symbols(symbols)
    except Exception as e:
        logger.debug(f"Error finding enclosing function: {e}")
        return None

def _should_process_file(path_obj: Path) -> bool:
    """Check if a file should be processed by the file watcher."""
    path_str = str(path_obj)

    # Only handle Python files
    if not path_str.endswith(('.py', '.pyi')):
        return False

    # Skip certain directories
    skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules'}
    return not any(part in path_obj.parts for part in skip_dirs)


async def _handle_file_added(client: PyrightLSPClient, file_path: Path) -> None:
    """Handle file addition event."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        uri = path_to_file_uri(str(file_path))
        await client.send_did_open(uri, content)
    except FileNotFoundError:
        # File might have been deleted before we could read it
        pass
    except PermissionError:
        logger.warning(f"Permission denied reading file: {file_path}")


async def _handle_file_modified(client: PyrightLSPClient, file_path: Path) -> None:
    """Handle file modification event."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        uri = path_to_file_uri(str(file_path))
        await client.send_did_change(uri, content)
    except FileNotFoundError:
        # File might have been deleted before we could read it
        pass
    except PermissionError:
        logger.warning(f"Permission denied reading file: {file_path}")


async def _handle_file_deleted(client: PyrightLSPClient, file_path: Path) -> None:
    """Handle file deletion event."""
    uri = path_to_file_uri(str(file_path))
    await client.send_did_close(uri)


async def _process_file_change(client: PyrightLSPClient, change_type, path_obj: Path) -> None:
    """Process a single file change event."""
    if not _should_process_file(path_obj):
        return

    try:
        change_name = change_type.name
        if change_name == "added":
            await _handle_file_added(client, path_obj)
        elif change_name == "modified":
            await _handle_file_modified(client, path_obj)
        elif change_name == "deleted":
            await _handle_file_deleted(client, path_obj)
    except Exception as e:
        if not client._shutdown_event.is_set():
            logger.error(f"Error handling file change {path_obj}: {e}")


async def watch_and_sync(client: PyrightLSPClient, root_path: Path) -> None:
    """Watch files and sync changes with LSP client."""
    if not root_path.exists():
        logger.error(f"Root path does not exist: {root_path}")
        return

    try:
        logger.info(f"Starting file watcher for: {root_path}")

        async for changes in awatch(root_path):
            if client._shutdown_event.is_set():
                break

            for change_type, path_obj in changes:
                if client._shutdown_event.is_set():
                    break

                await _process_file_change(client, change_type, Path(path_obj))

    except Exception as e:
        if not client._shutdown_event.is_set():
            logger.error(f"File watcher error: {e}")

async def main() -> None:
    """Main entry point."""
    root_path = Path(".").resolve()

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")

    config = LSPConfig(
        timeout=30.0,
        enable_file_watcher=True,
        log_level="INFO"
    )

    client = PyrightLSPClient(path_to_file_uri(str(root_path)), config)

    # Setup signal handling
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()

    # Register signal handlers properly
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        # Start the LSP client
        await client.start()

        # Start file watcher if enabled
        watcher_task = None
        if config.enable_file_watcher:
            watcher_task = asyncio.create_task(watch_and_sync(client, root_path))
            client._tasks.add(watcher_task)
            watcher_task.add_done_callback(client._tasks.discard)

        logger.info("LSP client started successfully. Press Ctrl+C to stop.")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Ensure cleanup
        await client.shutdown()
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
