import asyncio
import json
import re
import signal
import sys
from dataclasses import dataclass
from enum import Enum
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from watchfiles import awatch

PYRIGHT_COMMAND = ["pyright-langserver", "--stdio"]
DEFAULT_TIMEOUT = 30
BUFFER_SIZE = 8192


def path_to_file_uri(path_str: str) -> str:
    return Path(path_str).resolve().as_uri()


class LSPError(Exception):
    pass


class LSPClientState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


@dataclass
class LSPConfig:
    timeout: float = DEFAULT_TIMEOUT
    enable_file_watcher: bool = True
    log_level: str = "INFO"


class PyrightLSPClient:
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

    @property
    def state(self) -> LSPClientState:
        return self._state

    async def start(self) -> None:
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
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *PYRIGHT_COMMAND,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            task = asyncio.create_task(self._response_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        except FileNotFoundError:
            raise LSPError("Pyright not found. Please install pyright-langserver.")
        except Exception as e:
            raise LSPError(f"Failed to start Pyright subprocess: {e}") from e

    async def _initialize(self) -> None:
        init_params = {
            "processId": None,
            "rootUri": self.root_uri,
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": True,
                        "willSave": True,
                        "didSave": True,
                    },
                    "completion": {"dynamicRegistration": True},
                    "hover": {"dynamicRegistration": True},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {"dynamicRegistration": True},
                },
                "workspace": {
                    "applyEdit": True,
                    "workspaceEdit": {"documentChanges": True},
                    "didChangeConfiguration": {"dynamicRegistration": True},
                    "didChangeWatchedFiles": {"dynamicRegistration": True},
                },
            },
            "workspaceFolders": [{"uri": self.root_uri, "name": "workspace"}],
        }
        await self._request("initialize", init_params)
        await self._notify("initialized", {})

    async def _send(self, msg: Dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise LSPError("LSP process not available")
        try:
            data = json.dumps(msg).encode("utf-8")
            header = f"Content-Length: {len(data)}\r\n\r\n".encode()
            self.proc.stdin.write(header + data)
            await self.proc.stdin.drain()
        except Exception as e:
            raise LSPError(f"Failed to send message: {e}") from e

    async def _request(self, method: str, params: Dict[str, Any]) -> Any:
        if self._state != LSPClientState.RUNNING and method != "initialize":
            raise LSPError(f"Cannot send request in state: {self._state}")

        msg_id = next(self._msg_id)
        future: asyncio.Future[Any] = asyncio.Future()

        async with self._lock:
            self._pending[msg_id] = future

        try:
            await self._send(
                {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params},
            )
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
        if self._state not in (LSPClientState.RUNNING, LSPClientState.STARTING):
            if method not in ("initialized", "exit"):
                raise LSPError(f"Cannot send notification in state: {self._state}")
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    async def _response_loop(self) -> None:
        try:
            while (
                self.proc
                and self.proc.stdout
                and not self._shutdown_event.is_set()
                and self.proc.returncode is None
            ):
                try:
                    headers = await self._read_headers()
                    if not headers:
                        continue
                    content_length = int(headers.get("Content-Length", 0))
                    if content_length > 0:
                        message = await self._read_body(content_length)
                        if message:
                            await self._handle_message(message)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if not self._shutdown_event.is_set():
                        logger.error(f"Response loop error: {e}")
                        await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._shutdown_event.is_set():
                logger.error(f"Fatal response loop error: {e}")

    async def _read_headers(self) -> Dict[str, str]:
        headers = {}
        while True:
            line = await self._read_line()
            if not line or line == b"\r\n":
                break
            try:
                decoded = line.decode("utf-8", errors="replace").strip()
                if ":" in decoded:
                    key, value = decoded.split(":", 1)
                    headers[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Failed to parse header line: {e}")
        return headers

    async def _read_line(self) -> bytes:
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
        if not self.proc or not self.proc.stdout:
            return None
        try:
            body = await self.proc.stdout.read(length)
            if not body:
                return None
            return json.loads(body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read message body: {e}")
            return None

    async def _handle_message(self, msg: Dict[str, Any]) -> None:
        try:
            if msg_id := msg.get("id"):
                async with self._lock:
                    if future := self._pending.get(msg_id):
                        if not future.done():
                            future.set_result(msg)
                        return

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
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_diagnostics(self, params: Dict[str, Any]) -> None:
        uri = params.get("uri", "")
        diagnostics = params.get("diagnostics", [])
        if diagnostics:
            logger.info(f"Diagnostics for {uri}: {len(diagnostics)} issues")
            for diag in diagnostics:
                message = diag.get("message", "")
                line = diag.get("range", {}).get("start", {}).get("line", 0)
                logger.debug(f"  Line {line + 1}: {message}")

    async def _handle_log_message(self, params: Dict[str, Any]) -> None:
        message = params.get("message", "")
        msg_type = params.get("type", 1)
        log_func = [logger.error, logger.warning, logger.info, logger.debug][
            min(msg_type - 1, 3)
        ]
        log_func(f"LSP: {message}")

    async def _handle_show_message(self, params: Dict[str, Any]) -> None:
        message = params.get("message", "")
        msg_type = params.get("type", 1)
        logger.info(f"LSP Message (type {msg_type}): {message}")

    async def _manage_file_state(
        self,
        uri: str,
        action: str,
        content: str = "",
        language_id: str = "python",
    ) -> None:
        """Unified file state management."""
        async with self._lock:
            if action == "open":
                if uri in self.open_files:
                    self.file_versions[uri] = self.file_versions.get(uri, 0) + 1
                    await self._notify(
                        "textDocument/didChange",
                        {
                            "textDocument": {
                                "uri": uri,
                                "version": self.file_versions[uri],
                            },
                            "contentChanges": [{"text": content}],
                        },
                    )
                    return
                self.open_files.add(uri)
                self.file_versions[uri] = 1
                await self._notify(
                    "textDocument/didOpen",
                    {
                        "textDocument": {
                            "uri": uri,
                            "languageId": language_id,
                            "version": 1,
                            "text": content,
                        },
                    },
                )
            elif action == "change":
                if uri not in self.open_files:
                    await self._manage_file_state(uri, "open", content)
                    return
                self.file_versions[uri] = self.file_versions.get(uri, 0) + 1
                await self._notify(
                    "textDocument/didChange",
                    {
                        "textDocument": {
                            "uri": uri,
                            "version": self.file_versions[uri],
                        },
                        "contentChanges": [{"text": content}],
                    },
                )
            elif action == "close":
                if uri in self.open_files:
                    self.open_files.remove(uri)
                    self.file_versions.pop(uri, None)
                    await self._notify(
                        "textDocument/didClose",
                        {"textDocument": {"uri": uri}},
                    )

    async def send_did_open(
        self,
        uri: str,
        content: str,
        language_id: str = "python",
    ) -> None:
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didOpen")
        await self._manage_file_state(uri, "open", content, language_id)

    async def send_did_change(self, uri: str, content: str) -> None:
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didChange")
        await self._manage_file_state(uri, "change", content)

    async def send_did_close(self, uri: str) -> None:
        if not uri:
            raise ValueError("Invalid URI for didClose")
        await self._manage_file_state(uri, "close")

    async def send_references(self, uri: str, line: int, character: int) -> Any:
        if line < 0 or character < 0:
            raise ValueError("Line and character must be non-negative")
        return await self._request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": False},
            },
        )

    async def send_definition(self, uri: str, line: int, character: int) -> Any:
        if line < 0 or character < 0:
            raise ValueError("Line and character must be non-negative")
        return await self._request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
            },
        )

    async def send_document_symbol(self, uri: str) -> Any:
        if not uri:
            raise ValueError("URI is required for documentSymbol")
        return await self._request(
            "textDocument/documentSymbol",
            {"textDocument": {"uri": uri}},
        )

    async def shutdown(self) -> None:
        if self._state in (LSPClientState.STOPPING, LSPClientState.STOPPED):
            if self._state == LSPClientState.STOPPING:
                await self._shutdown_event.wait()
            return

        self._state = LSPClientState.STOPPING
        logger.info("Shutting down LSP client...")

        try:
            self._shutdown_event.set()

            async with self._lock:
                for future in self._pending.values():
                    if not future.done():
                        future.cancel()
                self._pending.clear()

            if self.proc:
                try:
                    await asyncio.wait_for(self._request("shutdown", {}), timeout=5.0)
                    await self._notify("exit", {})
                except (asyncio.TimeoutError, LSPError):
                    logger.warning("LSP shutdown sequence failed or timed out")

            await self._cancel_tasks()
            await self._cleanup()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._state = LSPClientState.STOPPED
            logger.info("LSP client shutdown complete")

    async def _cancel_tasks(self) -> None:
        if not self._tasks:
            return
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete within timeout")
            finally:
                self._tasks.clear()

    async def _cleanup(self) -> None:
        if self.proc:
            try:
                if self.proc.stdin and not self.proc.stdin.is_closing():
                    self.proc.stdin.close()
                    await self.proc.stdin.wait_closed()
                if self.proc.returncode is None:
                    self.proc.terminate()
                    try:
                        await asyncio.wait_for(self.proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self.proc.kill()
                        await self.proc.wait()
            except Exception as e:
                logger.debug(f"Error during cleanup: {e}")

        self.open_files.clear()
        self.file_versions.clear()
        async with self._lock:
            self._pending.clear()


def extract_symbol_code(sym: Dict[str, Any], content: str, strip: bool = False) -> str:
    try:
        rng = sym.get("location", {}).get("range", {})
        if not rng:
            return ""

        start = rng.get("start", {})
        end = rng.get("end", {})
        start_line, start_char = start.get("line", 0), start.get("character", 0)
        end_line, end_char = end.get("line", 0), end.get("character", 0)

        lines = content.splitlines()
        if not (0 <= start_line < len(lines) and 0 <= end_line < len(lines)):
            return ""

        if start_line == end_line:
            line = lines[start_line]
            return line[start_char:end_char] if strip else line

        code_lines = lines[start_line : end_line + 1]
        if not code_lines:
            return ""

        if strip:
            code_lines[0] = code_lines[0][start_char:]
            if len(code_lines) > 1:
                code_lines[-1] = code_lines[-1][:end_char]

        return "\n".join(code_lines)
    except Exception as e:
        logger.debug(f"Error extracting symbol code: {e}")
        return ""


def extract_inheritance_relations(
    content: str,
    symbols: List[Dict[str, Any]],
) -> Dict[str, str]:
    try:
        lines = content.splitlines()
        relations = {}

        for symbol in symbols:
            if symbol.get("kind") != 5:  # Not a class
                continue

            name = symbol.get("name")
            if not name:
                continue

            line_num = (
                symbol.get("location", {})
                .get("range", {})
                .get("start", {})
                .get("line", 0)
            )
            if not (0 <= line_num < len(lines)):
                continue

            line = lines[line_num].strip()
            pattern = rf"class\s+{re.escape(name)}\s*\((.*?)\)\s*:"
            match = re.search(pattern, line)

            if match:
                base_classes = match.group(1).strip()
                if base_classes:
                    first_base = base_classes.split(",")[0].strip()
                    if first_base:
                        relations[name] = first_base

        return relations
    except Exception as e:
        logger.debug(f"Error extracting inheritance relations: {e}")
        return {}


def find_enclosing_function(
    symbols: List[Dict[str, Any]],
    line: int,
    character: int,
) -> Optional[str]:
    def _search_symbols(syms: List[Dict[str, Any]]) -> Optional[str]:
        result = None
        for symbol in syms:
            if symbol.get("kind") == 12:  # Function
                rng = symbol.get("location", {}).get("range", {})
                start_line = rng.get("start", {}).get("line", -1)
                end_line = rng.get("end", {}).get("line", -1)
                if start_line <= line <= end_line:
                    result = symbol.get("name", "")

            children = symbol.get("children", [])
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
    path_str = str(path_obj)
    if not path_str.endswith((".py", ".pyi")):
        return False
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules"}
    return not any(part in path_obj.parts for part in skip_dirs)


async def _handle_file_change(
    client: PyrightLSPClient,
    change_type,
    file_path: Path,
) -> None:
    try:
        uri = path_to_file_uri(str(file_path))
        change_name = change_type.name

        if change_name == "deleted":
            await client.send_did_close(uri)
        else:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if change_name == "added":
                    await client.send_did_open(uri, content)
                elif change_name == "modified":
                    await client.send_did_change(uri, content)
            except (FileNotFoundError, PermissionError) as e:
                logger.warning(f"Could not read file {file_path}: {e}")
    except Exception as e:
        if not client._shutdown_event.is_set():
            logger.error(f"Error handling file change {file_path}: {e}")


async def watch_and_sync(client: PyrightLSPClient, root_path: Path) -> None:
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
                file_path = Path(path_obj)
                if _should_process_file(file_path):
                    await _handle_file_change(client, change_type, file_path)
    except Exception as e:
        if not client._shutdown_event.is_set():
            logger.error(f"File watcher error: {e}")


async def main() -> None:
    root_path = Path.cwd()
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")

    config = LSPConfig(timeout=30.0, enable_file_watcher=True, log_level="INFO")
    client = PyrightLSPClient(path_to_file_uri(str(root_path)), config)
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame) -> None:
        logger.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        await client.start()

        if config.enable_file_watcher:
            watcher_task = asyncio.create_task(watch_and_sync(client, root_path))
            client._tasks.add(watcher_task)
            watcher_task.add_done_callback(client._tasks.discard)

        logger.info("LSP client started successfully. Press Ctrl+C to stop.")
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await client.shutdown()
        logger.info("Application shutdown complete")
