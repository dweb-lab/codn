import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
import os

from codn.utils.base_lsp_client import (
    BaseLSPClient,
    path_to_file_uri,
    LSPConfig,
    watch_and_sync,
)


def formatter(record):
    relpath = os.path.relpath(record["file"].path)
    message = record["message"]
    # 显式防止 message 中的 {} 被 loguru 误解析
    message = message.replace("{", "{{").replace("}", "}}")

    return (
        f"<green>{record['time']:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        f"<level>{record['level'].name:<8}</level> | "
        f"<cyan>{relpath}:{record['line']}</cyan> "
        f"<magenta>{record['function']}</magenta> - "
        f"{message}\n"
    )


logger.remove()
logger.add(sys.stderr, format=formatter, level="TRACE", colorize=True)
# logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")


async def main() -> None:
    root_path = Path.cwd()

    config = LSPConfig(timeout=30.0, enable_file_watcher=True, log_level="INFO")
    client = BaseLSPClient(path_to_file_uri(str(root_path)), config)
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame) -> None:
        logger.trace(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        await client.start("py")

        if config.enable_file_watcher:
            watcher_task = asyncio.create_task(watch_and_sync(client, root_path))
            client._tasks.add(watcher_task)
            watcher_task.add_done_callback(client._tasks.discard)

        logger.trace("LSP client started successfully. Press Ctrl+C to stop.")
        await shutdown_event.wait()
    except KeyboardInterrupt:
        logger.trace("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await client.shutdown()
        logger.trace("Application shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
