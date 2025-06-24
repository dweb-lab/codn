import asyncio
from codn.utils.base_lsp_client import (
    get_snippet,
    get_refs,
)

import sys
from loguru import logger
import os


def formatter(record):
    relpath = os.path.relpath(record["file"].path)
    return (
        f"<green>{record['time']:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        f"<level>{record['level'].name:<8}</level> | "
        f"<cyan>{relpath}:{record['line']}</cyan> "
        f"<magenta>{record['function']}</magenta> - "
        f"{record['message']}\n"
    )


logger.remove()
logger.add(sys.stderr, format=formatter, level="DEBUG", colorize=True)


logger.info("test typescript")

function_name = "subtract"
path = "repos/ts1"
results = asyncio.run(get_snippet(function_name, str(path)))
total_snippets = len(results)
for result in results:
    print(result)

results = asyncio.run(get_refs(function_name, str(path)))
total_snippets = len(results)
for result in results:
    print(result)

logger.info("test cpp")

function_name = "add"
path = "repos/clang1"
results = asyncio.run(get_snippet(function_name, str(path)))
total_snippets = len(results)
for result in results:
    print(result)


results = asyncio.run(get_refs(function_name, str(path)))
total_snippets = len(results)
for result in results:
    print(result)
