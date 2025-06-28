import asyncio
import sys
import time
from loguru import logger
from codn.utils.base_lsp_client import (
    get_snippet,
    get_refs,
    get_refs_clean,
    get_called,
)

logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level:<8}</level> | "
        "<cyan>{file.path}:{line}</cyan> "
        "<magenta>{function}</magenta> - "
        "<level>{message}</level>"
    ),
    level="DEBUG",  # INFO DEBUG
    colorize=True,
)


def test_basic():
    logger.info("test typescript")

    function_name = "subtract"
    path = "repos/ts1"
    results = asyncio.run(get_snippet(function_name, str(path)))
    for result in results:
        print(result)

    results = asyncio.run(get_refs(function_name, str(path)))
    for result in results:
        print(result)

    logger.info("test cpp")

    function_name = "add"
    path = "repos/clang1"
    results = asyncio.run(get_snippet(function_name, str(path)))
    for result in results:
        print(result)

    results = asyncio.run(get_refs(function_name, str(path)))
    for result in results:
        print(result)

    logger.info("test clang")

    function_name = "greet"
    path = "repos/clang2"
    results = asyncio.run(get_snippet(function_name, str(path)))
    for result in results:
        print(result)

    results = asyncio.run(get_refs(function_name, str(path)))
    for result in results:
        print(result)
    results = asyncio.run(get_called(str(path)))
    for result in results:
        print(result)


def test_c_retry():
    logger.info("test c retry")

    path_str = "."
    if len(sys.argv) > 1:
        path_str = sys.argv[1]

    repo_name = "default"
    if path_str != ".":
        repo_name = path_str.split("/")[-1]

    # 我们假定，清晰的知道任务数量和未完成数量
    # - 一旦超时，则重新开始。因为c语言项目会无故卡住

    t_start = time.time()
    results = asyncio.run(get_refs_clean(path_str=path_str))
    # results = asyncio.run(get_refs(path_str=path_str))
    for result in list(results)[:3]:
        print(result)
    t_used = time.time() - t_start
    logger.info(f"Time used: {t_used:.2f} seconds")
    logger.info(f"ref count: {len(results)}")

    # 3. 输出 Graphviz
    with open(f"xcalls_{repo_name}.dot", "w") as f:
        f.write("digraph G {\n")
        # result 格式 f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{name}"
        for result in results:
            c, _, d = result.split("\t")
            # if c.split(':')[0]!=d.split(':')[0]:
            # if c.split('/')[0]!=d.split('/')[0]:
            f.write(f'  "{c}" -> "{d}";\n')
        f.write("}\n")


if __name__ == "__main__":
    # test_basic()
    test_c_retry()
