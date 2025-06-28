import re
from typing import Any, Optional
from loguru import logger

SYMBOL_KIND_MAP = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Method",
    7: "Property",
    8: "Field",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    13: "Variable",
    14: "Constant",
    15: "String",
    16: "Number",
    17: "Boolean",
    18: "Array",
    19: "Object",
    20: "Key",
    21: "Null",
    22: "EnumMember",
    23: "Struct",
    24: "Event",
    25: "Operator",
    26: "TypeParameter",
}


def kind_to_str(kind: int) -> str:
    return SYMBOL_KIND_MAP.get(kind, f"Unknown({kind})")


def extract_code(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[start_line : end_line + 1])


def find_enclosing_function(
    symbols: list[dict[str, Any]],
    line: int,
) -> Optional[str]:
    def _search_symbols(syms: list[dict[str, Any]]) -> Optional[str]:
        result = None
        for symbol in syms:
            if symbol.get("kind") in (5, 6, 12):  # Function Method
                rng = symbol.get("location", {}).get("range", {})
                start_line = rng.get("start", {}).get("line", -1)
                end_line = rng.get("end", {}).get("line", -1)
                if start_line <= line <= end_line:
                    result = symbol.get("name", "")

            children = symbol.get("children", [])
            if children:
                nested_result = _search_symbols(children)
                if nested_result:
                    result = nested_result
        return result

    try:
        return _search_symbols(symbols)
    except Exception as e:
        logger.trace(f"Error finding enclosing function: {e}")
        return None


def extract_inheritance_relations(
    content: str,
    symbols: list[dict[str, Any]],
) -> dict[str, str]:
    """Extract {child_class: parent_class} from source code and LSP symbols."""
    lines = content.splitlines()
    relations: dict[str, str] = {}

    for sym in symbols:
        if sym.get("kind") != 5:
            continue

        name = sym.get("name")
        if not isinstance(name, str):
            continue

        line_num = sym.get("location", {}).get("range", {}).get("start", {}).get("line")
        if not isinstance(line_num, int) or not (0 <= line_num < len(lines)):
            continue

        line = lines[line_num].strip()
        match: Optional[re.Match[str]] = re.search(
            rf"class\s+{re.escape(name)}\s*\(([^)]*)\)\s*:", line
        )
        if match:
            bases = [b.strip() for b in match.group(1).split(",") if b.strip()]
            if bases:
                relations[name] = bases[0]

    return relations
