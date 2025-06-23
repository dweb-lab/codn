import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger

from codn.utils.pyright_lsp_client import (
    PyrightLSPClient,
    path_to_file_uri,
    LSPConfig,
    watch_and_sync,
)


async def main() -> None:
    root_path = Path.cwd()
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")

    config = LSPConfig(timeout=30.0, enable_file_watcher=True, log_level="INFO")
    client = PyrightLSPClient(path_to_file_uri(str(root_path)), config)
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame) -> None:
        logger.trace(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        await client.start()

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
