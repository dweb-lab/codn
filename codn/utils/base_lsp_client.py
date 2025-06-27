import asyncio
import json
import re
from dataclasses import dataclass
from enum import Enum
from itertools import count
from pathlib import Path
from typing import Any, Dict, List, Set, Optional
from typing import Callable, Awaitable, Tuple
from loguru import logger
from watchfiles import awatch
from asyncio import Semaphore, Queue, create_task, gather
from codn.utils.os_utils import list_all_files, detect_dominant_languages
from urllib.parse import unquote, urlparse
import time
from codn.utils.os_utils import LANG_TO_LANGUAGE

LSP_COMMANDS = {
    "cpp": ["clangd"],
    "c": ["clangd", "--pch-storage=memory"],
    "py": ["pyright-langserver", "--stdio"],
    "ts": ["typescript-language-server", "--stdio"],
    "tsx": ["typescript-language-server", "--stdio"],
}
DEFAULT_TIMEOUT = 30
BUFFER_SIZE = 8192

# Variable Constant Field Enum Constructor Namespace Property
l_sym_ignore = [int(j) for j in "13 14 8 10 15 9 3 7".split()]


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


class BaseLSPClient:
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
        self.file_states: Dict[str, Dict[str, Any]] = {}

    @property
    def state(self) -> LSPClientState:
        return self._state

    async def start(self, lang: str) -> None:
        if self._state != LSPClientState.STOPPED:
            raise LSPError(f"Cannot start client in state: {self._state}")

        self._state = LSPClientState.STARTING
        try:
            await self._start_subprocess(lang)
            await self._initialize()
            self._state = LSPClientState.RUNNING
            logger.trace("LSP client started successfully")
        except Exception as e:
            self._state = LSPClientState.STOPPED
            await self._cleanup()
            raise LSPError(f"Failed to start LSP client: {e}") from e

    async def _start_subprocess(self, lang: str) -> None:
        try:
            self.proc = await asyncio.create_subprocess_exec(
                *LSP_COMMANDS[lang],
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
            self._pending.pop(msg_id, None)
            return {"err": "timed out"}
            # logger.error(f"Request {method} (id: {msg_id}) timed out. params {params}")
            # raise LSPError(f"Request {method} (id: {msg_id}) timed out")
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
            logger.trace(f"Error reading line: {e}")
        return bytes(line)

    async def _read_body(self, length: int) -> Optional[Dict[str, Any]]:
        if not self.proc or not self.proc.stdout:
            return None

        data = bytearray()
        remaining = length
        try:
            while remaining > 0:
                chunk = await self.proc.stdout.read(remaining)
                if not chunk:  # 流结束或读取失败
                    break
                data.extend(chunk)
                remaining -= len(chunk)

            if len(data) != length:
                logger.error(f"Expected {length} bytes but got {len(data)} bytes")
                return None

            return json.loads(data.decode("utf-8", errors="replace"))
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
            logger.trace(f"Diagnostics for {uri}: {len(diagnostics)} issues")
            for diag in diagnostics:
                message = diag.get("message", "")
                line = diag.get("range", {}).get("start", {}).get("line", 0)
                logger.trace(f"  Line {line + 1}: {message}")

    async def _handle_log_message(self, params: Dict[str, Any]) -> None:
        message = params.get("message", "")
        msg_type = params.get("type", 1)
        if msg_type > 2:
            return
        log_func = [logger.error, logger.warning, logger.trace, logger.trace][
            min(msg_type - 1, 3)
        ]
        log_func(f"LSP: {message}")

    async def _handle_show_message(self, params: Dict[str, Any]) -> None:
        message = params.get("message", "")
        msg_type = params.get("type", 1)
        logger.trace(f"LSP Message (type {msg_type}): {message}")

    async def _manage_file_state(
        self,
        uri: str,
        action: str,
        content: str = "",
        language_id: str = "",
    ) -> None:
        """Unified file state management."""
        async with self._lock:
            if action == "open":
                self.file_states[uri] = {
                    "content": content,
                    "language_id": language_id,
                    "status": "open",
                }
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
                self.file_states[uri] = {
                    "content": content,
                    "language_id": language_id,
                    "status": "change",
                }
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

    async def read_file(self, uri: str) -> str:
        """根据uri读取当前缓存的文件内容，如果文件不存在或未打开，返回None。"""
        state = self.file_states.get(uri, {})
        if state and "content" in state:
            return state["content"]
        return ""

    async def send_did_open(
        self,
        uri: str,
        content: str,
        language_id: str = "",
    ) -> None:
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didOpen")
        await self._manage_file_state(uri, "open", content, language_id)

    async def send_did_change(self, uri: str, content: str) -> None:
        if not uri or not isinstance(content, str):
            raise ValueError("Invalid parameters for didChange")
        await self._manage_file_state(uri, "change", content)

    async def stream_requests(
        self,
        method: Callable[..., Awaitable[Any]],
        args_list: List[Tuple[Any, ...]],
        *,
        max_concurrency: int = 10,
        show_progress: bool = True,
        progress_every: int = 10,  # 每N个任务打印一次
        progress_interval: float = 1.0,  # 最小打印间隔（秒）
    ) -> List[Any]:
        total = len(args_list)
        semaphore = Semaphore(max_concurrency)
        queue: Queue[Tuple[int, Any]] = Queue()
        results = [None] * total
        completed = 0
        last_print_time = time.perf_counter()
        start_time = last_print_time
        printed = False

        async def worker(index: int, args: Tuple[Any, ...]):
            async with semaphore:
                try:
                    result = await method(*args)
                    await queue.put((index, result))
                except Exception as e:
                    logger.error(f"Request failed at index {index}: {e}")
                    await queue.put((index, None))

        tasks = [create_task(worker(i, args)) for i, args in enumerate(args_list)]

        for _ in range(total):
            index, result = await queue.get()
            results[index] = result
            completed += 1

            if show_progress:
                now = time.perf_counter()
                if (
                    completed % progress_every == 0
                    or (now - last_print_time) >= progress_interval
                ):
                    elapsed = now - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    percent = (completed / total) * 100
                    eta = (total - completed) / speed if speed > 0 else float("inf")
                    logger.info(
                        f"Progress: {completed}/{total} ({percent:.1f}%) "
                        f"| Elapsed: {elapsed:.1f}s "
                        f"| Speed: {speed:.2f}/s "
                        f"| ETA: {eta:.1f}s",
                        end="\n",
                        flush=True,
                    )
                    printed = True
                    last_print_time = now

        if show_progress and printed:
            print()

        await gather(*tasks, return_exceptions=True)
        return results

    async def batch_requests(
        self,
        method: Callable[..., Awaitable[Any]],
        args_list: List[Tuple[Any, ...]],
        *,
        max_concurrency: int = 100,
    ) -> List[Any]:
        """批量并发执行多个请求（如 send_references 等）

        Args:
            method: 类似 self.send_references 的方法
            args_list: 每次调用方法所需的参数元组
            max_concurrency: 最大并发数

        Returns:
            各请求的响应结果，顺序与输入顺序一致
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_with_semaphore(args: Tuple[Any, ...]) -> Any:
            async with semaphore:
                try:
                    return await method(*args)
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                    return None

        tasks = [asyncio.create_task(_run_with_semaphore(args)) for args in args_list]
        return await asyncio.gather(*tasks)

    async def send_did_close(self, uri: str) -> None:
        if not uri:
            raise ValueError("Invalid URI for didClose")
        await self._manage_file_state(uri, "close")

    async def send_references(self, uri: str, line: int, character: int) -> Any:
        if line < 0 or character < 0:
            raise ValueError("Line and character must be non-negative")
        start_time = time.perf_counter()
        ret = await self._request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": False},
            },
        )
        duration = time.perf_counter() - start_time
        r = "\t".join(
            [uri, str(line), str(character), json.dumps(ret), str(round(duration, 4))]
        )
        print(r)
        return ret

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
        logger.trace("Shutting down LSP client...")

        try:
            self._shutdown_event.set()

            async with self._lock:
                for future in self._pending.values():
                    if not future.done():
                        future.cancel()
                self._pending.clear()

            if self.proc and self.state not in {
                LSPClientState.STOPPING,
                LSPClientState.STOPPED,
            }:
                try:
                    await asyncio.wait_for(self._request("shutdown", {}), timeout=5.0)
                except Exception as e:
                    logger.warning(f"LSP shutdown request failed or timed out: {e}")
                try:
                    await self._notify("exit", {})
                except Exception as e:
                    logger.warning(f"LSP exit notify failed: {e}")
            else:
                logger.trace(f"LSP already stopping or stopped: {self.state}")

            await self._cancel_tasks()
            await self._cleanup()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._state = LSPClientState.STOPPED
            logger.trace("LSP client shutdown complete")

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
                # 优先关闭 stdin
                if self.proc.stdin and not self.proc.stdin.is_closing():
                    self.proc.stdin.close()
                    await self.proc.stdin.wait_closed()

                for pipe in (self.proc.stdout, self.proc.stderr):
                    if pipe:
                        # 读取直到 EOF，或忽略（让子进程回收时自动关闭）
                        try:
                            await pipe.read()  # 或者 readuntil() 或 readline()
                        except Exception as e:
                            logger.debug(
                                f"Error while reading from pipe during cleanup: {e}"
                            )

                # 等待子进程退出
                if self.proc.returncode is None:
                    self.proc.terminate()
                    try:
                        await asyncio.wait_for(self.proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self.proc.kill()
                        await self.proc.wait()
            except Exception as e:
                logger.trace(f"Error during cleanup: {e}")
            finally:
                self.proc = None  # ✅ 断开引用，避免误用

        # 清理状态
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
        logger.trace(f"Error extracting symbol code: {e}")
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
        logger.trace(f"Error extracting inheritance relations: {e}")
        return {}


def find_enclosing_function(
    symbols: List[Dict[str, Any]],
    line: int,
) -> Optional[str]:
    def _search_symbols(syms: List[Dict[str, Any]]) -> Optional[str]:
        result = None
        for symbol in syms:
            if symbol.get("kind") in (5, 6, 12):  # Function Method
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
        logger.trace(f"Error finding enclosing function: {e}")
        return None


def _should_process_file(path_obj: Path) -> bool:
    path_str = str(path_obj)
    if not path_str.endswith((".py", ".pyi")):
        return False
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules"}
    return not any(part in path_obj.parts for part in skip_dirs)


async def _handle_file_change(
    client: BaseLSPClient,
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


async def watch_and_sync(client: BaseLSPClient, root_path: Path) -> None:
    if not root_path.exists():
        logger.error(f"Root path does not exist: {root_path}")
        return

    try:
        logger.trace(f"Starting file watcher for: {root_path}")
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


async def get_client(path_str: str):
    langs = detect_dominant_languages(path_str)
    if not langs:
        logger.error(f"Failed to detect dominant language for {path_str}")
        raise ValueError("Failed to detect dominant language")
    lang = langs[0]
    logger.trace(f"Detected dominant language: {lang} for path: {path_str}")
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = BaseLSPClient(root_uri)
    await client.start(lang)
    logger.debug(f"Started LSP client for {lang} at {root_path}")
    language_id = LANG_TO_LANGUAGE.get(lang, lang)
    if lang == "c":
        lang = "c,*.h"
    if lang == "cpp":
        lang = "cpp,*.hpp"

    async for py_file in list_all_files(path_str, f"*.{lang}"):
        str_py_file = str(py_file)
        if "tests/" in str_py_file or "test_" in str_py_file:
            continue
        # if "deprecated/" in str_py_file:
        #     continue
        content = py_file.read_text(encoding="utf-8")
        if not content:
            # if not str_py_file.endswith("__init__.py"):
            #     logger.warning(f"file:{str_py_file} is empty")
            continue
        uri = path_to_file_uri(str(py_file))
        if not content:
            logger.error(f"Empty file: {uri}")
        await client.send_did_open(uri, content, language_id)
    return client


async def get_snippet(entity_name=None, path_str="."):
    client = await get_client(path_str)
    l_code_snippets = []
    for uri in client.open_files:
        symbols = await client.send_document_symbol(uri)
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)

        for sym in symbols:
            name = sym["name"]
            if entity_name and name != entity_name:
                continue
            content = open(local_path).read()
            code_snippet = extract_symbol_code(sym, content)
            # logger.trace(f"==Code Snippet:\n{code_snippet}")
            l_code_snippets.append(code_snippet)

    await client.shutdown()
    return l_code_snippets


async def get_funcs_for_lines(line_nums, file_name, path_str="."):
    d_func_name = {}
    lang: str = file_name.split(".")[-1]
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = BaseLSPClient(root_uri)
    await client.start(lang)
    language_id: str = LANG_TO_LANGUAGE.get(lang, lang)

    async for py_file in list_all_files(path_str, f"{file_name}"):
        content = py_file.read_text(encoding="utf-8")
        if not content:
            continue
        uri = path_to_file_uri(str(py_file))
        if not content:
            logger.error(f"Empty file: {uri}")
        await client.send_did_open(uri, content, language_id)

    uri = list(client.open_files)[0]
    symbols = await client.send_document_symbol(uri)
    for sym in symbols:
        name = sym["name"]
        kind = sym["kind"]
        if kind not in [12, 6, 5]:
            continue
        loc = sym["location"]
        start = loc["range"]["start"]["line"]
        end = loc["range"]["end"]["line"]
        for line_num in line_nums:
            if start <= line_num - 1 <= end:
                full_name = name
                if sym.get("containerName"):
                    container_name = sym["containerName"]
                    full_name = f"{container_name}.{name}"
                d_func_name[line_num] = (full_name, start + 1, end + 1)

    await client.shutdown()
    return d_func_name


def get_search_type(search_terms):
    first_search_terms = search_terms[0]
    if first_search_terms.endswith(".py"):
        return "files"
    elif ":" in first_search_terms:
        return "symbols_with_file"
    else:
        return "symbols"


async def get_snippets_by_line_nums(
    line_nums: List[int], file_path_or_pattern: str, path_str="."
):
    if not line_nums or len(line_nums) != 2:
        return []
    start, end = line_nums
    client = await get_client(path_str)
    l_code_snippets = []
    root_path = Path(path_str).resolve()
    str_root_path = str(root_path)
    for uri in client.open_files:
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)
        _local_path = local_path[len(str_root_path) + 1 :]
        if _local_path == file_path_or_pattern:
            content = open(local_path).read()
            l_content = content.split("\n")
            content = "\n".join(l_content[start:end])
            l_code_snippets.append(content)

    await client.shutdown()
    return l_code_snippets


def match_pattern(file_path: str, patten: str) -> bool:
    path = Path(file_path)
    # 注意 Path.match 是从路径的末尾开始匹配，且不支持从中间任意位置匹配
    # 所以要确保 file_path 是相对于某个根目录的路径
    return path.match(patten)


async def get_filenames_by_pattern(path_str=".", pattern=""):
    client = await get_client(path_str)
    root_path = Path(path_str).resolve()
    str_root_path = str(root_path)

    filenames = []
    for uri in client.open_files:
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)
        _local_path = local_path[len(str_root_path) + 1 :]
        if pattern and not match_pattern(_local_path, pattern):
            filenames.append(_local_path)
    await client.shutdown()
    return filenames


async def get_snippets(search_terms: List[str], path_str=".", file_path_or_pattern=""):
    if not search_terms:
        return []
    search_type = get_search_type(search_terms)
    filenames = [j.split(":")[0] for j in search_terms]
    _search_terms = set(search_terms)
    _filenames = set(filenames)
    logger.info(f"path_str {path_str}")

    client = await get_client(path_str)
    l_code_snippets = []
    root_path = Path(path_str).resolve()
    str_root_path = str(root_path)
    if search_type == "files":
        for uri in client.open_files:
            parsed = urlparse(uri)
            local_path = unquote(parsed.path)
            _local_path = local_path[len(str_root_path) + 1 :]
            if _local_path not in _search_terms:
                continue
            if file_path_or_pattern and not match_pattern(
                _local_path, file_path_or_pattern
            ):
                continue
            content = open(local_path).read()
            l_code_snippets.append(content)

    if search_type == "symbols":
        for uri in client.open_files:
            symbols = await client.send_document_symbol(uri)
            parsed = urlparse(uri)
            local_path = unquote(parsed.path)
            _local_path = local_path[len(str_root_path) + 1 :]
            if file_path_or_pattern and not match_pattern(
                _local_path, file_path_or_pattern
            ):
                continue
            for sym in symbols:
                name = sym["name"]
                if name not in _search_terms:
                    continue
                content = open(local_path).read()
                code_snippet = extract_symbol_code(sym, content)
                l_code_snippets.append(code_snippet)

    if search_type == "symbols_with_file":
        root_path = Path(path_str).resolve()
        str_root_path = str(root_path)
        for uri in client.open_files:
            symbols = await client.send_document_symbol(uri)
            parsed = urlparse(uri)
            local_path = unquote(parsed.path)
            _local_path = local_path[len(str_root_path) + 1 :]
            if _local_path not in _filenames:
                continue
            if file_path_or_pattern and not match_pattern(
                _local_path, file_path_or_pattern
            ):
                continue
            for sym in symbols:
                name = sym["name"]
                full_name = name
                if sym.get("containerName"):
                    container_name = sym["containerName"]
                    full_name = f"{container_name}.{name}"
                full_name_with_file = f"{_local_path}:{full_name}"
                if full_name_with_file not in _search_terms:
                    continue
                content = open(local_path).read()
                code_snippet = extract_symbol_code(sym, content)
                l_code_snippets.append(code_snippet)

    await client.shutdown()
    return l_code_snippets


async def get_refs(entity_name=None, path_str="."):
    l_refs = set()
    client = await get_client(path_str)

    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    len_root_uri = len(str(root_uri))

    n_symbols = 0
    for uri in client.open_files:
        uri_short = uri[len_root_uri + 1 :]
        symbols = await client.send_document_symbol(uri)

        for sym in symbols:
            name = sym["name"]
            if entity_name and name != entity_name:
                continue
            kind = sym["kind"]
            if kind in [13, 14, 10, 8]:  # Variable Constant Enum Field
                continue
            if kind not in [12, 6, 5]:  # func method class
                raise ValueError(
                    f"Unexpected kind value: {kind}, expected one of [12, 6, 5]"
                )
            if name == "__init__" and "containerName" in sym:
                continue
            loc = sym["location"]["range"]["start"]
            func_line = loc["line"]
            func_char = loc["character"]
            full_name = name
            if sym.get("containerName"):
                container_name = sym["containerName"]
                full_name = f"{container_name}.{name}"
            if name == "main":
                continue
            logger.trace(f"{kind} - {full_name}")

            # just check find_enclosing_function
            func_name = find_enclosing_function(symbols, func_line)
            if func_name != name:
                continue
                # raise ValueError(f"Expected {name}, got {func_name}")

            if not uri.startswith(root_uri):
                continue

            # func_char wrong
            # if func_char not in [0, 4, 8, 12, 16, 20, 24]:
            if func_char not in [0, 1, 4, 8, 12, 16, 20, 24]:
                raise ValueError(
                    f"func: {func_name} in {uri_short}:{func_line + 1} func_char is {func_char}"
                )

            ref_result = None
            if kind in [12, 6]:
                func_char += 4  # def
                ref_result = await client.send_references(
                    uri, line=func_line, character=func_char
                )
                if not ref_result:
                    func_char += 6  # async
                    ref_result = await client.send_references(
                        uri, line=func_line, character=func_char
                    )
                    if not ref_result:
                        logger.trace(
                            f"No references found for func: {uri}:{func_line}:{func_char}"
                        )
                        continue

            if kind in [5]:
                func_char += 6  # class
                ref_result = await client.send_references(
                    uri, line=func_line, character=func_char
                )
                if not ref_result:
                    func_char += 6  # async
                    ref_result = await client.send_references(
                        uri, line=func_line, character=func_char
                    )
                    if not ref_result:
                        logger.trace(
                            f"No references found for func: {uri}:{func_line}:{func_char}"
                        )
                        continue

            if not ref_result:
                raise ValueError(
                    f"No references found for func: {uri}:{func_line}:{func_char} kind: {kind}"
                )
            n_symbols += 1
            for i, ref in enumerate(ref_result, 1):
                ref_uri = ref.get("uri", "<no-uri>")
                logger.trace(f"ref_uri {ref_uri}")
                if "tests" in ref_uri:
                    continue
                if "test_" in ref_uri:
                    continue
                range_ = ref.get("range", {})
                start = range_.get("start", {})
                line = start.get("line", "?")
                character = start.get("character", "?")
                _func_name = "?"
                if line == "?" or character == "?":
                    raise ValueError(
                        f"  {i:02d}. {uri} @ Line {line}, Char {character}"
                    )

                _symbols = await client.send_document_symbol(ref_uri)
                _func_name = find_enclosing_function(_symbols, line)
                # if not _func_name:  # import? or direct use
                #     logger.error(f"no _func_name  {i:02d}. {uri} @ Line {line}, Char {character}")
                #     continue

                ref_uri_short = ref_uri[len_root_uri + 1 :]

                if "test" in ref_uri_short:
                    continue
                if "docs" in ref_uri_short:
                    continue
                if "__init__.py" in ref_uri_short:
                    continue
                if "cli.py" in ref_uri_short:
                    continue

                # if ref_uri_short == uri_short: # 是否分析文件内部的调用
                #     continue
                if _func_name is None:
                    continue
                invoke_info = f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{func_name}"
                if invoke_info not in l_refs:
                    l_refs.add(invoke_info)
                    if len(l_refs) % 1000 == 0:
                        logger.info(f"Processed {len(l_refs)} references")

    await client.shutdown()
    logger.trace(f"n_symbols={n_symbols} l_refs={len(l_refs)}")
    return l_refs


async def get_refs_clean(entity_name=None, path_str=".", l_done=None):
    l_refs = set()
    client = await get_client(path_str)

    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    len_root_uri = len(str(root_uri))
    l_uri = [(uri,) for uri in client.open_files]
    # result = await client.batch_requests(client.send_document_symbol, l_uri)
    result = await client.stream_requests(
        client.send_document_symbol, l_uri, max_concurrency=10
    )
    if len(result) != len(l_uri):
        raise ValueError(f"Unexpected number of results: {len(result)}")
    d_symbols = {uri[0]: symbols for uri, symbols in zip(l_uri, result)}
    logger.info(f"Processed {len(d_symbols)} files")

    l_params = []
    l_meta = []
    for uri in client.open_files:
        uri_short = uri[len_root_uri + 1 :]
        symbols = d_symbols[uri]
        if not symbols:
            continue

        for sym in symbols:
            name = sym["name"]
            if entity_name and name != entity_name:
                continue
            kind = sym["kind"]
            if kind in l_sym_ignore:
                continue
            if kind not in [12, 6, 5]:  # func method class
                raise ValueError(f"Unexpected kind: {kind}, expected one of [12, 6, 5]")
            if name == "__init__" and "containerName" in sym:
                continue
            loc = sym["location"]["range"]["start"]
            func_line = loc["line"]
            func_char = loc["character"]
            full_name = name
            if sym.get("containerName"):
                container_name = sym["containerName"]
                full_name = f"{container_name}.{name}"
            if name == "main":
                continue
            logger.trace(f"{kind} - {full_name}")

            # optional: just check find_enclosing_function
            # func_name = find_enclosing_function(symbols, func_line)
            # if func_name != name:
            #     raise ValueError(f"Expected {name}, got {func_name}")

            if not uri.startswith(root_uri):
                continue

            # optional: check func_char for format checking

            content = await client.read_file(uri)
            line = "\n".join(content.split("\n")[func_line : func_line + 10])
            _line = line
            while _line.strip().startswith("#") or _line.strip().startswith("@"):
                _line = "\n".join(_line.split("\n")[1:])
            real_func_char = func_char
            if kind in [12, 6]:
                final_prefix = 0
                if _line.strip().startswith("static"):
                    base_prefix = line.index("static")
                    line = line[:base_prefix] + line[base_prefix + 7 :]
                    final_prefix += base_prefix + 7
                if _line.strip().startswith("void"):
                    base_prefix = line.index("void")
                    line = line[:base_prefix] + line[base_prefix + 5 :]
                    final_prefix += base_prefix + 5
                    _line = line

                if _line.strip().startswith("int"):
                    base_prefix = line.index("int")
                    line = line[:base_prefix] + line[base_prefix + 4 :]
                    final_prefix += base_prefix + 4
                    _line = line
                if _line.strip().startswith("char *"):
                    base_prefix = line.index("char *")
                    line = line[:base_prefix] + line[base_prefix + 6 :]
                    final_prefix += base_prefix + 6
                    _line = line

                if final_prefix:
                    pass
                elif _line.strip().startswith("def"):
                    real_func_char = line.index("def") + 4
                elif full_name in _line:
                    base_prefix = line.index(full_name)
                    line = line[:base_prefix] + line[base_prefix + len(full_name) :]
                    final_prefix += base_prefix + len(full_name)
                    _line = line

                else:
                    first_line = repr(_line.split("\n")[0])
                    logger.error(
                        f"Unexpected def line={first_line} full_name={full_name}"
                    )
                real_func_char += final_prefix
            elif kind in [5]:
                final_prefix = 0
                if final_prefix:
                    pass
                elif _line.strip().startswith("class"):
                    real_func_char = line.index("class") + 6
                elif _line.strip().startswith("typedef"):
                    pass
                elif _line.strip().startswith("struct"):
                    pass
                elif "struct " in _line.strip():
                    pass
                else:
                    first_line = repr(_line.split("\n")[0])
                    logger.error(f"Unexpected class line: {first_line}")
                real_func_char += final_prefix
            l_params.append((uri, func_line, real_func_char))
            l_meta.append((name,))

    logger.info(f"==l_params== {len(l_params)}")
    if l_done:
        l_params_new = []
        for param in l_params:
            r = "\t".join([str(j) for j in param[:2]])
            if r not in l_done:
                l_params_new.append(param)
        logger.info(f"==l_params_new== {len(l_params_new)}")
    else:
        l_params_new = l_params

    results = await client.stream_requests(
        client.send_references, l_params_new, max_concurrency=1
    )
    n_symbols = 0
    for ref_result, params, meta in zip(results, l_params, l_meta):
        if not ref_result:
            continue
        n_symbols += 1
        uri, func_line, real_func_char = params
        uri_short = uri[len_root_uri + 1 :]
        name = meta[0]
        for i, ref in enumerate(ref_result, 1):
            ref_uri = ref.get("uri", "<no-uri>")
            logger.trace(f"ref_uri {ref_uri}")
            if "tests" in ref_uri:
                continue
            if "test_" in ref_uri:
                continue
            range_ = ref.get("range", {})
            start = range_.get("start", {})
            line = start.get("line", "?")
            # character = start.get("character", "?")
            _symbols = await client.send_document_symbol(ref_uri)
            _func_name = find_enclosing_function(_symbols, line)
            # if not _func_name:  # import? or direct use
            #     logger.error(f"no _func_name  {i:02d}. {uri} @ Line {line}, Char {character}")
            #     continue

            ref_uri_short = ref_uri[len_root_uri + 1 :]
            if "test" in ref_uri_short:
                continue
            if "docs" in ref_uri_short:
                continue
            if "__init__.py" in ref_uri_short:
                continue
            if "cli.py" in ref_uri_short:
                continue
            # if ref_uri_short == uri_short: # 是否分析文件内部的调用
            #     continue
            invoke_info = f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{name}"
            if invoke_info not in l_refs:
                l_refs.add(invoke_info)
                if len(l_refs) % 1000 == 0:
                    logger.info(f"Processed {len(l_refs)} references")

    await client.shutdown()
    logger.info(f"Processed {len(l_refs)} references. n_symbols: {n_symbols}")
    return l_refs


async def _traverse(client, len_root_uri, start_entities, root_uri):
    str_start_entities = "|".join(start_entities)
    is_full_path = False
    clean_start_entities = []
    if ":" in str_start_entities:
        is_full_path = True
        clean_start_entities = [
            f"{j.split(':')[0]}:{j.split(':')[2]}" for j in start_entities
        ]
    l_refs = set()
    for uri in client.open_files:
        uri_short = uri[len_root_uri + 1 :]
        symbols = await client.send_document_symbol(uri)

        for sym in symbols:
            name = sym["name"]
            # logger.info(f"start_entities {start_entities} name {name} uri {uri}")
            if not is_full_path:
                if start_entities and name not in start_entities:
                    continue
            else:
                full_name = f"{uri_short}:{name}"
                if clean_start_entities and full_name not in clean_start_entities:
                    continue

            kind = sym["kind"]
            if kind in [13, 14]:  # Variable Constant
                continue
            if kind not in [12, 6, 5]:  # func method class
                raise ValueError(
                    f"Unexpected kind value: {kind}, expected one of [12, 6, 5]"
                )
            if name == "__init__" and "containerName" in sym:
                continue
            loc = sym["location"]["range"]["start"]
            func_line = loc["line"]
            func_char = loc["character"]
            full_name = name
            if sym.get("containerName"):
                container_name = sym["containerName"]
                full_name = f"{container_name}.{name}"
            if name == "main":
                continue
            logger.trace(f"{kind} - {full_name}")

            # just check find_enclosing_function
            func_name = find_enclosing_function(symbols, func_line)
            if func_name != name:
                raise ValueError(f"Expected {name}, got {func_name}")
            if not uri.startswith(root_uri):
                continue

            # func_char wrong
            if func_char not in [0, 4, 8, 12, 16, 20, 24, 28]:
                raise ValueError(
                    f"func: {func_name} in {uri_short}:{func_line + 1} func_char is {func_char}"
                )

            ref_result = None
            # logx.info(f" func: {uri}:{func_line}:{func_char}")
            if kind in [12, 6]:
                func_char += 4  # def
                ref_result = await client.send_references(
                    uri, line=func_line, character=func_char
                )
                if not ref_result:
                    func_char += 6  # async
                    ref_result = await client.send_references(
                        uri, line=func_line, character=func_char
                    )
                    if not ref_result:
                        logger.trace(
                            f"No references found for func: {uri}:{func_line}:{func_char}"
                        )
                        continue

            if kind in [5]:
                func_char += 6  # class
                ref_result = await client.send_references(
                    uri, line=func_line, character=func_char
                )
                if not ref_result:
                    func_char += 6  # async
                    ref_result = await client.send_references(
                        uri, line=func_line, character=func_char
                    )
                    if not ref_result:
                        logger.trace(
                            f"No references found for func: {uri}:{func_line}:{func_char}"
                        )
                        continue

            if not ref_result:
                raise ValueError(
                    f"No references found for func: {uri}:{func_line}:{func_char} kind: {kind}"
                )
            for i, ref in enumerate(ref_result, 1):
                ref_uri = ref.get("uri", "<no-uri>")
                logger.trace(f"ref_uri {ref_uri}")
                if "tests" in ref_uri:
                    continue
                if "test_" in ref_uri:
                    continue
                range_ = ref.get("range", {})
                start = range_.get("start", {})
                line = start.get("line", "?")
                character = start.get("character", "?")
                _func_name = "?"
                if line == "?" or character == "?":
                    raise ValueError(
                        f"  {i:02d}. {uri} @ Line {line}, Char {character}"
                    )

                _symbols = await client.send_document_symbol(ref_uri)
                _func_name = find_enclosing_function(_symbols, line)
                ref_uri_short = ref_uri[len_root_uri + 1 :]
                if "test" in ref_uri_short:
                    continue
                if "docs" in ref_uri_short:
                    continue
                if "__init__.py" in ref_uri_short:
                    continue
                if "cli.py" in ref_uri_short:
                    continue
                invoke_info = f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{func_name}"
                if invoke_info not in l_refs:
                    l_refs.add(invoke_info)
    return l_refs


async def traverse(
    start_entities,
    # entity_type_filter,
    # dependency_type_filter,
    direction,
    traversal_depth,
    path_str=".",
):
    # 暂时无视 entity_type_filter dependency_type_filter
    l_refs = set()
    client = await get_client(path_str)
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    len_root_uri = len(str(root_uri))

    if direction == "downstream":
        current_depth = 1
        todo = []
        if traversal_depth >= current_depth:
            _l_refs = await _traverse(client, len_root_uri, start_entities, root_uri)
            for i in list(_l_refs):
                l_refs.add(i)
                a, b, c = i.split("\t")
                x, y, z = a.split(":")
                if z != "None":
                    todo.append(a)
        current_depth = 2
        while traversal_depth >= current_depth:
            _l_refs = await _traverse(client, len_root_uri, todo, root_uri)
            for i in list(_l_refs):
                l_refs.add(i)
                a, b, c = i.split("\t")
                x, y, z = a.split(":")
                if z != "None":
                    todo.append(a)
            current_depth += 1

    await client.shutdown()
    return list(l_refs)


async def get_called(path_str):
    l_refs = set()
    client = await get_client(path_str)
    file_uris = [uri for uri in client.open_files]
    analyzer = CallGraphAnalyzer(client)
    call_graph = await analyzer.analyze_project(file_uris)

    for caller, callees in call_graph.items():
        # print(f"{caller} called: {', '.join(callees)}")
        for callee in callees:
            r = "\t".join([caller, "called", callee])
            l_refs.add(r)
    return l_refs


class CallGraphAnalyzer:
    def __init__(self, client: BaseLSPClient):
        self.client = client  # 你的LSP客户端实例

    async def analyze_project(self, file_uris: List[str]) -> Dict[str, List[str]]:
        call_graph: Dict[str, List[str]] = {}

        l_uri = [(uri,) for uri in file_uris]
        results = await self.client.stream_requests(
            self.client.send_document_symbol, l_uri
        )
        if len(results) != len(l_uri):
            raise ValueError(f"Unexpected number of results: {len(results)}")
        d_symbols = {uri[0]: symbols for uri, symbols in zip(l_uri, results)}

        set_params = set()
        l_params = []
        l_meta = []
        for uri in file_uris:
            # 1. 获取文件符号（函数、类、方法）
            # symbols = await self.client.send_document_symbol(uri)
            symbols = d_symbols[uri]
            # 2. 读取文件内容
            text = await self.client.read_file(uri)
            # 3. 遍历函数符号，提取调用关系
            for sym in symbols:
                if sym["kind"] in [12, 6]:
                    caller_name = sym["name"]
                    caller_range = sym["location"]["range"]
                    start_line = caller_range["start"]["line"]
                    func_body = self._extract_code(text, caller_range)
                    # 4. 找调用的函数名（简单用正则，示例为 Python 调用）
                    called_names = self._find_called_functions(func_body)

                    for name in called_names:  # 5. 查询调用定义
                        d_params = position_for_name(func_body, name, start_line)
                        line = d_params["line"]
                        character = d_params["character"]
                        # r = '\t'.join([uri, str(line), str(character)])
                        r = tuple([uri, line, character])
                        if r not in set_params:
                            set_params.add(r)
                        l_params.append((uri, line, character))
                        l_meta.append([name, caller_name, caller_range])

        logger.debug(f"before {len(l_params)}; after {len(set_params)}")
        l_set_params = list(set_params)
        locations = await self.client.stream_requests(
            self.client.send_definition, l_set_params, max_concurrency=10
        )
        d_cached_loc = {}
        for params, location in zip(l_set_params, locations):
            d_cached_loc[params] = location

        for meta, params in zip(l_meta, l_params):
            location = d_cached_loc[params]
            if location:
                name = meta[0]
                caller_name = meta[1]
                if caller_name not in call_graph:
                    call_graph[caller_name] = []
                call_graph[caller_name].append(name)

        return call_graph

    def _extract_code(self, text: str, rng: dict) -> str:
        # 根据range（start/end行列）提取源码，示例只用行范围
        lines = text.splitlines()
        start_line = rng["start"]["line"]
        end_line = rng["end"]["line"]
        return "\n".join(lines[start_line : end_line + 1])

    def _find_called_functions(self, code: str) -> List[str]:
        # 简单示例用正则匹配函数调用：foo(...)，忽略复杂语法
        pattern = r"(\w+)\s*\("
        return re.findall(pattern, code)[1:]


def position_for_name(code: str, name: str, start_line: int) -> dict:
    # TODO 目前只是简单返回第一个找到调用名字的位置
    lines = code.splitlines()
    for lineno, line in enumerate(lines):
        col = line.find(name)
        if col >= 0:
            return {"line": lineno + start_line, "character": col}
    return {"line": -1, "character": -1}
