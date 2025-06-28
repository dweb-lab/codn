import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import Any, Optional
from typing import Callable, Awaitable, Tuple
from loguru import logger
from asyncio import Semaphore, Queue, create_task, gather

LSP_COMMANDS = {
    "cpp": ["clangd"],
    "c": ["clangd", "--pch-storage=memory"],
    "py": ["pyright-langserver", "--stdio"],
    "ts": ["typescript-language-server", "--stdio"],
    "tsx": ["typescript-language-server", "--stdio"],
}
DEFAULT_TIMEOUT = 30


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
        self._lock = asyncio.Lock()
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._tasks: set[asyncio.Task[Any]] = set()  # 当任务返回类型不确定时
        self._shutdown_event = asyncio.Event()
        self._state = LSPClientState.STOPPED
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.lang = ""
        self.open_files: set[str] = set()
        self.file_versions: dict[str, int] = {}
        self.file_states: dict[str, dict[str, Any]] = {}

    @property
    def state(self) -> LSPClientState:
        return self._state

    @property
    def is_closing(self) -> bool:
        """客户端是否处于关闭流程中（对外暴露为主）"""
        return self._state in (LSPClientState.STOPPING, LSPClientState.STOPPED)

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

    async def _send(self, msg: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise LSPError("LSP process not available")
        try:
            data = json.dumps(msg).encode("utf-8")
            header = f"Content-Length: {len(data)}\r\n\r\n".encode()
            self.proc.stdin.write(header + data)
            await self.proc.stdin.drain()
        except Exception as e:
            raise LSPError(f"Failed to send message: {e}") from e

    async def _request(
        self, method: str, params: dict[str, Any], timeout: float = -1
    ) -> Any:
        if timeout < 0:
            timeout = self.config.timeout
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
            result: dict[str, Any] = await asyncio.wait_for(future, timeout=timeout)
            if "error" in result:
                error_msg: str = result["error"].get("message", "Unknown error")
                raise LSPError(f"LSP request failed: {error_msg}")

            return result.get("result")
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise LSPError(f"Request {method} (id: {msg_id}) timed out")
        except Exception as e:
            if isinstance(e, LSPError):
                raise
            raise LSPError(f"Request {method} failed: {e}") from e
        finally:
            async with self._lock:
                self._pending.pop(msg_id, None)

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
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
                # ✅ 检查 subprocess 是否崩溃（早于 read）
                if self.proc.returncode is not None:
                    logger.error(
                        f"LSP process crashed with code {self.proc.returncode}, restarting..."
                    )
                    raise LSPError("LSP process crashed")
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

    async def _read_headers(self) -> dict[str, str]:
        """读取并解析 HTTP 头部，返回键值对字典."""
        headers: dict[str, str] = {}  # 显式声明类型
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

    async def _read_body(self, length: int) -> Optional[dict[str, Any]]:
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

    async def _handle_message(self, msg: dict[str, Any]) -> None:
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

    async def _handle_diagnostics(self, params: dict[str, Any]) -> None:
        uri = params.get("uri", "")
        diagnostics = params.get("diagnostics", [])
        if diagnostics:
            logger.trace(f"Diagnostics for {uri}: {len(diagnostics)} issues")
            for diag in diagnostics:
                message = diag.get("message", "")
                line = diag.get("range", {}).get("start", {}).get("line", 0)
                logger.trace(f"  Line {line + 1}: {message}")

    async def _handle_log_message(self, params: dict[str, Any]) -> None:
        """处理 LSP 日志消息，根据类型分派到不同的日志级别."""
        message: str = str(params.get("message", ""))
        msg_type: int = int(params.get("type", 1))
        if msg_type > 2:
            return
        log_func = [logger.error, logger.warning, logger.debug, logger.trace][
            min(msg_type - 1, 3)
        ]
        log_func(f"LSP: {message}")

    async def _handle_show_message(self, params: dict[str, Any]) -> None:
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
        """发送 textDocument/didOpen 通知到语言服务器."""
        await self._manage_file_state(uri, "open", content, language_id)

    async def send_did_change(self, uri: str, content: str) -> None:
        await self._manage_file_state(uri, "change", content)

    async def stream_requests(
        self,
        method: Callable[..., Awaitable[Any]],
        args_list: list[Tuple[Any, ...]],
        *,
        max_concurrency: int = 10,
        show_progress: bool = True,
        progress_every: int = 10,  # 每N个任务打印一次
        progress_interval: float = 1.0,  # 最小打印间隔（秒）
    ) -> list[Any]:
        total = len(args_list)
        semaphore = Semaphore(max_concurrency)
        queue: Queue[Tuple[int, Any]] = Queue()
        results = [None] * total
        completed = 0
        last_print_time = time.perf_counter()
        start_time = last_print_time
        # printed = False

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
                    last_print_time = now

        await gather(*tasks, return_exceptions=True)
        return results

    async def batch_requests(
        self,
        method: Callable[..., Awaitable[Any]],
        args_list: list[Tuple[Any, ...]],
        *,
        max_concurrency: int = 100,
    ) -> list[Any]:
        """批量并发执行多个请求（如 send_references 等）

        Args:
            method: 类似 self.send_references 的方法
            args_list: 每次调用方法所需的参数元组
            max_concurrency: 最大并发数

        Returns:
            各请求的响应结果，顺序与输入顺序一致
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_with_semaphore(args: tuple[Any, ...]) -> Any:
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

    async def send_references(
        self, uri: str, line: int, character: int, name: str = "", timeout: float = -1
    ) -> Any:
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
            timeout,
        )
        duration = time.perf_counter() - start_time
        return uri, line, character, name, ret, duration

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

    async def send_document_symbol(self, uri: str, timeout: float = -1) -> Any:
        if not uri:
            raise ValueError("URI is required for documentSymbol")
        return await self._request(
            "textDocument/documentSymbol",
            {"textDocument": {"uri": uri}},
            timeout,
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
