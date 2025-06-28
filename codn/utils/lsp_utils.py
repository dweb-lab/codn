import re
from typing import Any, Dict, List, Optional
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
    symbols: List[Dict[str, Any]],
    line: int,
) -> Optional[str]:
    def _search_symbols(syms: List[Dict[str, Any]]) -> Optional[str]:
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
    symbols: List[Dict[str, Any]],
) -> Dict[str, str]:
    try:
        lines = content.splitlines()
        relations = {}

        for symbol in symbols:
            if symbol.get("kind") != 5:  # Not a class
                continue

            name = symbol.get("name")
            if not name:
                continue

            line_num = (
                symbol.get("location", {})
                .get("range", {})
                .get("start", {})
                .get("line", 0)
            )
            if not (0 <= line_num < len(lines)):
                continue

            line = lines[line_num].strip()
            pattern = rf"class\s+{re.escape(name)}\s*\((.*?)\)\s*:"
            match = re.search(pattern, line)

            if match:
                base_classes = match.group(1).strip()
                if base_classes:
                    first_base = base_classes.split(",")[0].strip()
                    if first_base:
                        relations[name] = first_base

        return relations
    except Exception as e:
        logger.trace(f"Error extracting inheritance relations: {e}")
        return {}
