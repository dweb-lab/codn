import re
import os
import asyncio
from pathlib import Path
from codn.utils.lsp_core import BaseLSPClient, LSPError  # noqa
from typing import Any
from loguru import logger
from codn.utils.os_utils import LANG_TO_LANGUAGE, LANG_TO_EXTENSION
from codn.utils.os_utils import list_all_files, detect_dominant_languages
from codn.utils.lsp_utils import extract_code, find_enclosing_function
from urllib.parse import unquote, urlparse
from watchfiles import awatch  # type: ignore[reportUnknownVariableType]

# Variable Constant Field Enum Constructor Namespace Property
l_sym_ignore = [int(j) for j in "13 14 8 10 15 9 3 7".split()]


def path_to_file_uri(path_str: str) -> str:
    return Path(path_str).resolve().as_uri()


def extract_symbol_code(sym: dict[str, Any], content: str, strip: bool = False) -> str:
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
        if not client.is_closing:
            logger.error(f"Error handling file change {file_path}: {e}")


async def watch_and_sync(client: BaseLSPClient, root_path: Path) -> None:
    if not root_path.exists():
        logger.error(f"Root path does not exist: {root_path}")
        return

    try:
        logger.trace(f"Starting file watcher for: {root_path}")
        async for changes in awatch(root_path):
            if client.is_closing:
                break
            for change_type, path_obj in changes:
                if client.is_closing:
                    break
                file_path = Path(path_obj)
                if _should_process_file(file_path):
                    await _handle_file_change(client, change_type, file_path)
    except Exception as e:
        if not client.is_closing:
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
    client.lang = lang
    await client.start(lang)
    logger.debug(f"Started LSP client for {lang} at {root_path}")
    language_id = LANG_TO_LANGUAGE.get(lang, lang)
    file_ext = LANG_TO_EXTENSION.get(lang, lang)
    if lang == "c":
        file_ext = "c,h"
    if lang == "cpp":
        file_ext = "cpp,hpp"

    async for py_file in list_all_files(path_str, f"*.{file_ext}"):
        content = py_file.read_text(encoding="utf-8")
        if not content:
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
        local_path = unquote(urlparse(uri).path)

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


async def get_funcs_for_lines(
    line_nums, file_name="", content="", lang="", path_str="."
):
    if not lang and file_name:
        lang = file_name.split(".")[-1]
    if not lang:
        raise ValueError("Language not specified")

    if content:
        if file_name:
            raise ValueError("Cannot specify both content and file_name")
        file_name = f"sample.{lang}"

    full_path = os.path.join(path_str, file_name)
    if not content:
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")
        with open(full_path) as f:
            content = f.read()

    if not content:
        logger.error(f"Empty file: {full_path}")

    d_func_name = {}
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    client = BaseLSPClient(root_uri)
    await client.start(lang)
    language_id: str = LANG_TO_LANGUAGE.get(lang, lang)
    if not file_name:
        file_name = f"sample.{lang}"

    uri = path_to_file_uri(str(full_path))
    await client.send_did_open(uri, content, language_id)

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
    line_nums: list[int], file_path_or_pattern: str, path_str="."
):
    if not line_nums or len(line_nums) != 2:
        return []
    start, end = line_nums
    client = await get_client(path_str)
    l_code_snippets = []
    root_path = Path(path_str).resolve()
    str_root_path = str(root_path)
    for uri in client.open_files:
        local_path = unquote(urlparse(uri).path)
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
        local_path = unquote(urlparse(uri).path)
        _local_path = local_path[len(str_root_path) + 1 :]
        if pattern and not match_pattern(_local_path, pattern):
            filenames.append(_local_path)
    await client.shutdown()
    return filenames


async def get_snippets(search_terms: list[str], path_str=".", file_path_or_pattern=""):
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


async def get_refs(entity_name=None, path_str=".", l_done=None):
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
            # if func_char not in [0, 1, 4, 8, 12, 16, 20, 24]:
            #     raise ValueError(
            #         f"func: {func_name} in {uri_short}:{func_line + 1} func_char is {func_char}"
            #     )

            ref_result = None
            if l_done and f"{uri}\t{func_line}\t{func_char}" in l_done:
                continue

            content = await client.read_file(uri)
            line = "\n".join(content.split("\n")[func_line : func_line + 10])
            _line = line
            while _line.strip().startswith("#") or _line.strip().startswith("@"):
                _line = "\n".join(_line.split("\n")[1:])

            real_func_char = check_real_func_char(
                _line, line, func_char, full_name, kind, uri, func_line
            )
            ref_result = await client.send_references(
                uri, line=func_line, character=real_func_char
            )

            if not ref_result:
                continue
                raise ValueError(
                    f"No references found for func: {uri}:{func_line}:{func_char} kind: {kind}"
                )
            n_symbols += 1
            ref_result = ref_result[4]
            for i, ref in enumerate(ref_result, 1):
                if isinstance(ref, str):  # err
                    continue
                    print(f"ref {repr(ref)}")
                    raise
                # continue
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


def check_real_func_char(_line, line, real_func_char, full_name, kind, uri, func_line):
    if full_name.startswith("__builtin___"):
        full_name = full_name[12:]
    real_func_char = -1
    raw_line = line
    if kind in [12, 6]:
        final_prefix = None
        if full_name in raw_line:
            final_prefix = raw_line.index(full_name)
        if final_prefix is not None:
            real_func_char = final_prefix
        if not raw_line[real_func_char:].strip().startswith(full_name):
            raw_first_line = repr(raw_line.split("\n")[0])
            print("==", repr(raw_line[real_func_char:]), repr(full_name))
            raise ValueError(
                f"Unexpected def line={raw_first_line} full_name={full_name} _line={_line} uri={uri}:{func_line}"
            )
    elif kind in [5]:
        if full_name in raw_line:
            final_prefix = raw_line.index(full_name)
            real_func_char = final_prefix
            if not raw_line[real_func_char:].startswith(full_name):
                raw_first_line = repr(raw_line.split("\n")[0])
                print("==", raw_line[real_func_char:])
                raise ValueError(
                    f"Unexpected class raw_first_line={raw_first_line} _line={_line} full_name={full_name} uri={uri}:{func_line}"
                )

    return real_func_char


async def get_all_symbols(path_str=".", entity_name=None):
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))

    client = await get_client(path_str)
    l_uri = [(uri, 1) for uri in client.open_files]
    # result = await client.batch_requests(client.send_document_symbol, l_uri)
    result = await client.stream_requests(
        client.send_document_symbol, l_uri, max_concurrency=20, show_progress=False
    )
    if len(result) != len(l_uri):
        raise ValueError(f"Unexpected number of results: {len(result)}")
    d_symbols = {uri[0]: symbols for uri, symbols in zip(l_uri, result)}

    l_params = []
    for uri in client.open_files:
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
            loc = sym["location"]["range"]
            func_line = loc["start"]["line"]
            func_end_line = loc["end"]["line"]
            func_char = loc["start"]["character"]
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
            line = "\n".join(content.split("\n")[func_line : func_end_line + 1])
            _line = line
            while _line.strip().startswith("#") or _line.strip().startswith("@"):
                _line = "\n".join(_line.split("\n")[1:])

            if full_name == "(anonymous struct)":
                continue

            real_func_char = check_real_func_char(
                _line,
                line,
                func_char,
                name,
                kind,
                uri,
                func_line,
            )
            if real_func_char < 0:
                continue
            l_params.append((uri, func_line, real_func_char, name))

    return client, d_symbols, l_params


async def get_refs_clean(entity_name=None, path_str=".", l_done=None):
    l_refs = set()
    root_path = Path(path_str).resolve()
    root_uri = path_to_file_uri(str(root_path))
    len_root_uri = len(str(root_uri))

    client, d_symbols, l_params = await get_all_symbols(path_str, entity_name)
    logger.info(f"Processed {len(d_symbols)} files, got {len(l_params)} uniq symbols.")
    logger.info(f"==l_params== {len(l_params)}")

    d_line_symbol = {}
    for params in l_params:
        uri, func_line, real_func_char, _ = params
        d_line_symbol[f"{uri}\t{func_line}"] = params
    l_params_left = l_params

    # will timeout and stucked
    # results = await client.stream_requests(client.send_references, l_params_left)

    l_done = set()
    results = []
    timeout = -1  # default
    if client.lang == "c":
        timeout = 0.1
    while len(l_params_left):
        for params in l_params_left:
            try:
                r = await client.send_references(*params, timeout=timeout)
                results.append(r)
                r = "\t".join([str(j) for j in r[:3]])
                l_done.add(r)

            except LSPError as e:
                logger.error(e)
                client, d_symbols, l_params = await get_all_symbols(
                    path_str, entity_name
                )
                break
        l_params_left_new = []
        for param in l_params_left:
            r = "\t".join([str(j) for j in param[:3]])
            if r not in l_done:
                l_params_left_new.append(param)
        l_params_left = l_params_left_new
        logger.info(f"==l_params_left== {len(l_params_left)}")

    n_symbols = 0
    for uri, func_line, real_func_char, func_name, ref_result, _ in results:
        if not ref_result:
            continue
        n_symbols += 1

        uri_short = uri[len_root_uri + 1 :]
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

            if not ref_result:
                raise ValueError(
                    f"No references found for func: {uri}:{func_line}:{real_func_char}"
                )
            n_symbols += 1
            # ref_result = ref_result[4]
            for i, ref in enumerate(ref_result, 1):
                if isinstance(ref, str):  # err
                    continue
                    print(f"ref {repr(ref)}")
                    raise
                # continue
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

                # character = start.get("character", "?")
                func_key = f"{ref_uri}\t{line}"
                if func_key in d_line_symbol:
                    func_info = d_line_symbol[
                        func_key
                    ]  # uri, func_line, real_func_char, name
                    _func_name = func_info[3]
                else:
                    max_try_num = 1
                    _symbols = d_symbols.get(ref_uri)
                    while not _symbols and max_try_num > 0:
                        logger.warning(f"ref_uri {ref_uri} not in cache?")
                        try:
                            _symbols = await client.send_document_symbol(ref_uri)
                            break
                        except LSPError as e:
                            logger.debug(
                                f"err: {e} for ref_uri:{ref_uri} start:{start}"
                            )
                            max_try_num -= 1
                            await asyncio.sleep(0.01)
                            client, _, _ = await get_all_symbols(path_str, entity_name)

                    if not _symbols:
                        continue
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
                invoke_info = f"{ref_uri_short}:{line + 1}:{_func_name}\tinvoke\t{uri_short}:{func_line + 1}:{func_name}"
                if invoke_info not in l_refs:
                    print(invoke_info)
                    l_refs.add(invoke_info)
                    if len(l_refs) % 100 == 0:
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
    entity_type_filter,
    dependency_type_filter,
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
                a = i.split("\t")[0]
                z = a.split(":")[-1]
                if z != "None":
                    todo.append(a)
        current_depth = 2
        while traversal_depth >= current_depth:
            _l_refs = await _traverse(client, len_root_uri, todo, root_uri)
            for i in list(_l_refs):
                l_refs.add(i)
                a = i.split("\t")[0]
                z = a.split(":")[-1]
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

    async def analyze_project(self, file_uris: list[str]) -> dict[str, list[str]]:
        call_graph: dict[str, list[str]] = {}

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
                    end_line = caller_range["end"]["line"]
                    func_body = extract_code(text, start_line, end_line)
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

    def _find_called_functions(self, code: str) -> list[str]:
        # 简单示例用正则匹配函数调用：foo(...)，忽略复杂语法
        pattern = r"(\w+)\s*\("
        return re.findall(pattern, code)[1:]


def position_for_name(code: str, name: str, start_line: int) -> dict[str, int]:
    # TODO 目前只是简单返回第一个找到调用名字的位置
    lines = code.splitlines()
    for lineno, line in enumerate(lines):
        col = line.find(name)
        if col >= 0:
            return {"line": lineno + start_line, "character": col}
    return {"line": -1, "character": -1}
