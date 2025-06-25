import asyncio
import sys
import os
from loguru import logger
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from watchfiles import awatch
from codn.utils.os_utils import list_all_files

from codn.utils.base_lsp_client import (
    BaseLSPClient,
    extract_inheritance_relations,
    extract_symbol_code,
    find_enclosing_function,
    path_to_file_uri,
    get_refs,
    get_refs_clean,
    get_called,
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
logger.add(sys.stderr, format=formatter, level="INFO", colorize=True)
logx = logger


# 特殊情况: 不进行类型注解 client: BaseLSPClient ，pyright无法分析出来
async def watch_and_sync2(client, project_path):
    async for changes in awatch(project_path):
        for change_type, changed_path in changes:
            uri = path_to_file_uri(changed_path)
            if change_type.name in ("added", "modified"):
                with open(changed_path, encoding="utf-8") as f:
                    content = f.read()
                await client.send_did_open(uri, content)
            elif change_type.name == "deleted":
                await client.send_did_close(uri)


async def test_get_refs(entity_name=None):
    l_refs = set()
    path_str = "."
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = await get_client(root_uri)
    len_root_uri = len(str(root_uri))

    for uri in client.open_files:
        uri_short = uri[len_root_uri + 1 :]
        symbols = await client.send_document_symbol(uri)

        for sym in symbols:
            name = sym["name"]
            if entity_name and name != entity_name:
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
            if "containerName" in sym:
                container_name = sym["containerName"]
                full_name = f"{container_name}.{name}"
            if name == "main":
                continue
            logx.trace(f"{kind} - {full_name}")

            # just check find_enclosing_function
            func_name = find_enclosing_function(symbols, func_line)
            if func_name != name:
                raise ValueError(f"Expected {name}, got {func_name}")
            if not uri.startswith(root_uri):
                continue

            # func_char wrong
            if func_char not in [0, 4, 8, 12]:
                print(func_char)
                raise ValueError(
                    f"func: {func_name} in {uri_short}:{func_line + 1} func_char is {func_char}"
                )

            ref_result = None
            logx.trace(f" func: {uri}:{func_line}:{func_char}")
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
                        logx.info(
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
                        logx.info(
                            f"No references found for func: {uri}:{func_line}:{func_char}"
                        )
                        continue

            if not ref_result:
                raise ValueError(
                    f"No references found for func: {uri}:{func_line}:{func_char} kind: {kind}"
                )
                continue
            # logx.warning(f"ref_result {json.dumps(ref_result, indent=2)}")
            for i, ref in enumerate(ref_result, 1):
                ref_uri = ref.get("uri", "<no-uri>")
                # print(f'ref_uri {ref_uri}')
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
                if not _func_name:  # import?
                    continue

                ref_uri_short = ref_uri[len_root_uri + 1 :]

                if "test" in ref_uri_short:
                    continue
                if "docs" in ref_uri_short:
                    continue
                if "__init__.py" in ref_uri_short:
                    continue
                if "cli.py" in ref_uri_short:
                    continue
                if ref_uri_short == uri_short:
                    continue
                invoke_info = f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line}:{func_name}"
                if invoke_info not in l_refs:
                    print(invoke_info)
                    l_refs.add(invoke_info)
                continue

    await client.shutdown()


async def get_client(root_uri: str):
    client = BaseLSPClient(root_uri)
    await client.start("py")
    async for py_file in list_all_files(".", "*.py"):
        str_py_file = str(py_file)
        if "tests/" in str_py_file or "test_" in str_py_file:
            continue
        if "docs/" in str_py_file:
            continue
        if "scripts/" in str_py_file:
            continue
        if "simple_ast" in str_py_file:
            continue
        content = py_file.read_text(encoding="utf-8")
        if not content:
            if not str_py_file.endswith("__init__.py"):
                logx.error(str_py_file)
                raise
            continue
        uri = path_to_file_uri(str(py_file))
        await client.send_did_open(uri, content)
    return client


async def test_get_snippet(entity_name=None):
    path_str = "."
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = await get_client(root_uri)

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
            print(f"==Code Snippet:\n{code_snippet}")

    await client.shutdown()


async def test_get_superclasses():
    path_str = "."
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = await get_client(root_uri)
    for uri in client.open_files:
        symbols = await client.send_document_symbol(uri)
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)
        content = open(local_path).read()
        relations = extract_inheritance_relations(content, symbols)

        for sym in symbols:
            name = sym["name"]
            if name in relations:
                kind = sym["kind"]
                print(f"{kind} - {name} → {relations[name]}")


async def test_get_superclass(class_name):
    path_str = "."
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = await get_client(root_uri)
    d_class = {}
    for uri in client.open_files:
        symbols = await client.send_document_symbol(uri)
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)
        content = open(local_path).read()
        relations = extract_inheritance_relations(content, symbols)
        for k, v in relations.items():
            d_class[k] = v

    r = d_class.get(class_name)
    print(r)
    return r


async def test_get_refs_bench(path_str="."):
    logger.info("use get_called")
    t_start = time.time()
    l_refs = await get_called(path_str)
    t_end = time.time()
    logger.info(f"Time taken: {t_end - t_start} seconds")
    logger.info(f"final rels: {len(l_refs)}\n")

    logger.info("use get_refs_clean")
    t_start = time.time()
    l_refs = await get_refs_clean(path_str=path_str)
    t_end = time.time()
    logger.info(f"Time taken: {t_end - t_start} seconds")
    logger.info(f"final rels: {len(l_refs)}\n")

    logger.info("use get_refs")
    t_start = time.time()
    l_refs = await get_refs(path_str=path_str)
    t_end = time.time()
    logger.info(f"Time taken: {t_end - t_start} seconds")
    logger.info(f"final rels: {len(l_refs)}\n")


if __name__ == "__main__":
    # asyncio.run(test_get_refs())
    # asyncio.run(test_get_refs('find_enclosing_function'))
    # asyncio.run(test_get_refs('list_all_files'))
    # asyncio.run(test_get_refs("extract_inheritance_relations"))
    # asyncio.run(test_get_refs("send_did_open"))
    # asyncio.run(test_get_snippet("send_did_open"))
    # asyncio.run(test_get_superclasses())
    # asyncio.run(test_get_superclass("LSPClientState"))
    # asyncio.run(test_get_snippet("parse_ecu_definition"))
    # asyncio.run(test_get_refs_clean())
    path_str = "."
    if len(sys.argv) > 1:
        path_str = sys.argv[1]
    asyncio.run(test_get_refs_bench(path_str=path_str))
