# TODO 多个定义？
import asyncio
from pathlib import Path
from urllib.parse import unquote, urlparse

from watchfiles import awatch

from codn.utils.os_utils import list_all_python_files
from codn.utils.pyright_lsp_client import (
    PyrightLSPClient,
    extract_inheritance_relations,
    extract_symbol_code,
    find_enclosing_function,
    path_to_file_uri,
)


async def watch_and_sync(client, project_path):
    async for changes in awatch(project_path):
        for change_type, changed_path in changes:
            uri = path_to_file_uri(changed_path)
            if change_type.name in ("added", "modified"):
                with open(changed_path, encoding="utf-8") as f:
                    content = f.read()
                # 这里假设客户端有 send_did_open 和 send_did_change 方法
                await client.send_did_open(uri, content)
            elif change_type.name == "deleted":
                # 发送关闭通知
                await client.send_did_close(uri)


async def main():
    root_path = Path().resolve()
    root_uri = path_to_file_uri(str(root_path))
    print(str(root_uri))
    len_root_uri = len(str(root_uri))
    client = PyrightLSPClient(root_uri)
    await client.start()
    async for py_file in list_all_python_files("."):
        content = py_file.read_text(encoding="utf-8")
        if not content:
            continue
        uri = path_to_file_uri(str(py_file))
        await client.send_did_open(uri, content)

    print("\n\n")
    for uri in client.open_files:
        # print(uri)
        symbols = await client.send_document_symbol(uri)
        print("=" * 88)
        print(f"file: {uri[len_root_uri + 1 :]}")
        parsed = urlparse(uri)
        local_path = unquote(parsed.path)
        content = open(local_path).read()
        relations = extract_inheritance_relations(content, symbols)

        for sym in symbols:
            kind = sym["kind"]
            if kind in [13, 14]:
                continue

            name = sym["name"]
            if name == "__init__" and "containerName" in sym:
                continue
            loc = sym["location"]["range"]["start"]
            func_line = loc["line"]
            func_char = loc["character"]
            if "containerName" in sym:
                container_name = sym["containerName"]
                name = f"{container_name}.{name}"
            print(f"{kind} - {name}")
            if name in relations:
                print(f"    -→ {relations[name]}")

            # 获取定义位置 用于精确的获取位置，部分没有
            raw_def = await client.send_definition(uri, func_line, func_char + 4)
            raw_def_line = raw_def_char = None
            if raw_def:
                # assert len(raw_def) == 1, f"Expected 1 definition, got {len(raw_def)}"
                raw_def = raw_def[0]
                raw_uri = raw_def["uri"]
                raw_symbols = await client.send_document_symbol(raw_uri)

                raw_loc = raw_def["range"]["start"]
                raw_def_line = raw_loc["line"]
                raw_def_char = raw_loc["character"]

                raw_func_name = find_enclosing_function(
                    raw_symbols,
                    raw_def_line,
                    raw_def_char,
                )
                if raw_func_name:
                    print(f"---{raw_func_name}")

            # TODO 获取有哪些地方引用了该函数
            if raw_def_line and func_line == raw_def_line:
                # print(f'uri {uri} func_line {func_line} func_char {func_char}')
                # print(f'uri {uri} func_line {raw_def_line} func_char {raw_def_char}')
                # assert func_line == raw_def_line, f"Expected line {func_line}, got {raw_def_line}"
                ref_result = await client.send_references(
                    uri,
                    line=raw_def_line,
                    character=raw_def_char,
                )
                if not ref_result:
                    # print(references)
                    continue
                for i, ref in enumerate(ref_result, 1):
                    uri = ref.get("uri", "<no-uri>")
                    range_ = ref.get("range", {})
                    start = range_.get("start", {})
                    line = start.get("line", "?")
                    character = start.get("character", "?")
                    func_name = "?"
                    if line != "?" and character != "?":
                        _symbols = await client.send_document_symbol(uri)
                        func_name = find_enclosing_function(_symbols, line, character)
                        print(
                            f"  {i:02d}. {uri} @ Line {line + 1}, Char {character + 1}, Func {func_name}",
                        )  # LSP line/char 是从0开始的
                        raw_def = await client.send_definition(uri, line, character)
                        # assert len(raw_def) == 1, f"Expected 1 definition, got {len(raw_def)}"
                        raw_def = raw_def[0]["range"]["start"]
                        raw_def_line = raw_def["line"]
                        raw_def_char = raw_def["character"]
                        # assert raw_def_line == func_line, f"Expected line {func_line}, got {raw_def_line}"
                        # assert raw_def_char == func_char, f"Expected character {func_char}, got {raw_def_char}"
                    else:
                        print(f"  {i:02d}. {uri} @ Line {line}, Char {character}")

            if 1:
                code_snippet = extract_symbol_code(sym, content)
                print(f"==Code Snippet:\n{code_snippet}")

    await client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
