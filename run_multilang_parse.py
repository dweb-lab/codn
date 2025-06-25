import asyncio
import sys
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
    level="INFO",
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


def test_c():
    logger.info("test c")

    path_str = "."
    if len(sys.argv) > 1:
        path_str = sys.argv[1]

    repo_name = "default"
    if path_str != ".":
        repo_name = path_str.split("/")[-1]

    # function_name = "FUNC"
    # results = asyncio.run(get_snippet(function_name, str(path_str)))
    # total_snippets = len(results)
    # for result in results:
    #     print(result)

    # results = asyncio.run(get_called(path_str = str(path_str)))
    # results = asyncio.run(get_refs(entity_name=None, path_str = str(path_str)))
    results = asyncio.run(get_refs_clean(entity_name=None, path_str=str(path_str)))
    for result in list(results)[:3]:
        print(result)

    # 3. 输出 Graphviz
    with open(f"xcalls_{repo_name}.dot", "w") as f:
        f.write("digraph G {\n")
        # result 格式 f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{name}"
        for result in results:
            c, _, d = result.split("\t")
            f.write(f'  "{c}" -> "{d}";\n')
        f.write("}\n")


if __name__ == "__main__":
    test_basic()
    test_c()
