# 分析函数调用
import asyncio
from codn.utils.pyright_lsp_client import PyrightLSPClient
from codn.utils.pyright_lsp_client import path_to_file_uri
from codn.utils.pyright_lsp_client import find_enclosing_function

from codn.utils.pyright_lsp_client import extract_inheritance_relations
from codn.utils.pyright_lsp_client import extract_symbol_code

async def main():
    filepath = "demo/test.py"  # 你测试的文件
    uri = path_to_file_uri(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    root_uri = path_to_file_uri(".")
    client = PyrightLSPClient(root_uri)
    await client.start()

    func_line = 0
    func_char = 4
    symbols = await client.send_document_symbol(uri)
    func_name = find_enclosing_function(symbols, func_line, func_char)
    print(f'func_name {func_name}')

    ref_result = await client.send_references(uri, line=func_line, character=func_char)
    if not ref_result:
        print("No references found.")
        return
    if ref_result:
        print("🔎 References Found:")
        for i, ref in enumerate(ref_result, 1):
            uri = ref.get("uri", "<no-uri>")
            range_ = ref.get("range", {})
            start = range_.get("start", {})
            line = start.get("line", "?")
            character = start.get("character", "?")
            func_name = '?'
            if line!='?' and character!='?':
                _symbols = await client.send_document_symbol(uri)
                func_name = find_enclosing_function(_symbols, line, character)
                print(f"  {i:02d}. {uri} @ Line {line + 1}, Char {character + 1}, Func {func_name}")  # LSP line/char 是从0开始的
                raw_def = await client.send_definition(uri, line, character)
                assert len(raw_def) == 1, f"Expected 1 definition, got {len(raw_def)}"
                raw_def = raw_def[0]['range']['start']
                raw_def_line = raw_def['line']
                raw_def_char = raw_def['character']
                assert raw_def_line == func_line, f"Expected line {func_line}, got {raw_def_line}"
                assert raw_def_char == func_char, f"Expected character {func_char}, got {raw_def_char}"
            else:
                print(f"  {i:02d}. {uri} @ Line {line}, Char {character}")

        for sym in symbols:
            kind = sym["kind"]
            name = sym["name"]
            loc = sym["location"]['range']['start']
            func_line = loc['line']
            func_char = loc['character']
            if 'containerName' in sym:
                container_name = sym['containerName']
                name = f"{container_name}.{name}"
            print(f"{kind} - {name}")
            # TODO
            references = await client.send_references(uri, line=func_line, character=func_char)
            if 1:
                code_snippet = extract_symbol_code(sym, content)
                print(f"==Code Snippet:\n{code_snippet}")

            # location = sym["location"]["range"]["start"]
            # kind in (12, 6):  # Function (12), Method (6)

    relations = extract_inheritance_relations(content, symbols)
    if relations:
        print("=== Class Inheritance ===")
        for child, parent in relations.items():
            print(f"  {child} → {parent}")

    await client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
