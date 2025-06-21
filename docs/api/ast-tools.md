# AST Analysis Tools

This module provides powerful Abstract Syntax Tree (AST) analysis tools for Python code.

## Functions

### `find_enclosing_function(content: str, line: int, character: int) -> Optional[str]`

Find the name of the function or method that contains the given position.

**Parameters:**
- `content` (str): Python source code
- `line` (int): Line number (1-based)
- `character` (int): Character position (0-based)

**Returns:**
- `Optional[str]`: Function name if position is inside a function, None otherwise

**Example:**
```python
from codn.utils.simple_ast import find_enclosing_function

code = """
def outer_function():
    def inner_function():
        print("Hello")  # Line 4
        return True
    return inner_function()
"""

function_name = find_enclosing_function(code, 4, 0)
print(function_name)  # Output: "inner_function"
```

### `find_function_references(content: str, function_name: str) -> List[Tuple[int, int]]`

Find all references to a function in the given content.

**Parameters:**
- `content` (str): Python source code
- `function_name` (str): Name of the function to find references for

**Returns:**
- `List[Tuple[int, int]]`: List of (line_number, column_offset) tuples

**Example:**
```python
from codn.utils.simple_ast import find_function_references

code = """
def my_function():
    return True

result = my_function()
value = my_function()
"""

references = find_function_references(code, "my_function")
print(references)  # Output: [(5, 9), (6, 8)]
```

### `extract_function_signatures(content: str) -> List[Dict[str, Any]]`

Extract function signatures from Python source code.

**Parameters:**
- `content` (str): Python source code

**Returns:**
- `List[Dict[str, Any]]`: List of dictionaries containing function information

**Function Info Dictionary:**
- `name` (str): Function name
- `line` (int): Line number where function is defined
- `args` (List[str]): List of argument names
- `defaults` (List[str]): List of default values
- `return_type` (Optional[str]): Return type annotation
- `is_async` (bool): Whether function is async
- `docstring` (Optional[str]): Function docstring

**Example:**
```python
from codn.utils.simple_ast import extract_function_signatures

code = """
def greet(name: str, greeting: str = "Hello") -> str:
    '''Greet someone with a message.'''
    return f"{greeting}, {name}!"

async def fetch_data(url: str):
    pass
"""

signatures = extract_function_signatures(code)
print(signatures[0])
# Output: {
#     'name': 'greet',
#     'line': 2,
#     'args': ['name', 'greeting'],
#     'defaults': ["'Hello'"],
#     'return_type': 'str',
#     'is_async': False,
#     'docstring': 'Greet someone with a message.'
# }
```

### `find_unused_imports(content: str) -> List[Tuple[str, int]]`

Find unused imports in Python source code.

**Parameters:**
- `content` (str): Python source code

**Returns:**
- `List[Tuple[str, int]]`: List of (import_name, line_number) tuples for unused imports

**Example:**
```python
from codn.utils.simple_ast import find_unused_imports

code = """
import os
import sys
from pathlib import Path

print("Hello World")
"""

unused = find_unused_imports(code)
print(unused)  # Output: [('os', 2), ('sys', 3), ('Path', 4)]
```

### `extract_class_methods(content: str, class_name: Optional[str] = None) -> List[Dict[str, Any]]`

Extract methods from classes in Python source code.

**Parameters:**
- `content` (str): Python source code
- `class_name` (Optional[str]): Optional specific class name to extract methods from

**Returns:**
- `List[Dict[str, Any]]`: List of dictionaries containing method information

**Method Info Dictionary:**
- `class_name` (str): Name of the class
- `method_name` (str): Name of the method
- `line` (int): Line number where method is defined
- `is_async` (bool): Whether method is async
- `is_classmethod` (bool): Whether method is a classmethod
- `is_staticmethod` (bool): Whether method is a staticmethod
- `is_property` (bool): Whether method is a property
- `docstring` (Optional[str]): Method docstring

**Example:**
```python
from codn.utils.simple_ast import extract_class_methods

code = """
class Calculator:
    def __init__(self):
        pass

    @staticmethod
    def add(a, b):
        return a + b

    @classmethod
    def create(cls):
        return cls()

    @property
    def version(self):
        return "1.0"
"""

methods = extract_class_methods(code, "Calculator")
print(methods[1])
# Output: {
#     'class_name': 'Calculator',
#     'method_name': 'add',
#     'line': 6,
#     'is_async': False,
#     'is_classmethod': False,
#     'is_staticmethod': True,
#     'is_property': False,
#     'docstring': None
# }
```

### `extract_inheritance_relations(content: str) -> List[Tuple[str, str]]`

Extract class inheritance relationships from Python source code.

**Parameters:**
- `content` (str): Python source code

**Returns:**
- `List[Tuple[str, str]]`: List of (child_class, parent_class) tuples

**Example:**
```python
from codn.utils.simple_ast import extract_inheritance_relations

code = """
class Animal:
    pass

class Dog(Animal):
    pass

class Cat(Animal):
    pass
"""

relations = extract_inheritance_relations(code)
print(relations)  # Output: [('Dog', 'Animal'), ('Cat', 'Animal')]
```

## Error Handling

All functions handle syntax errors gracefully:
- If the Python code contains syntax errors, functions return empty results (empty lists, None values)
- No exceptions are raised for malformed code
- Functions are designed to be robust and continue processing even with partial or incomplete code

## Performance Notes

- Functions use Python's built-in `ast` module for parsing
- Performance is optimized for typical source files (< 10K lines)
- For very large files, consider processing in chunks or using async variants where available
