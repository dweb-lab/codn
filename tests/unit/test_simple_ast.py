"""Unit tests for codn.utils.simple_ast module.

This module contains comprehensive tests for Python AST analysis functionality,
including function detection, inheritance analysis, and edge cases.
"""

import ast

import pytest

from codn.utils.simple_ast import (
    _extract_base_name,
    extract_inheritance_relations,
    find_enclosing_function,
)


class TestFindEnclosingFunction:
    """Test cases for find_enclosing_function function."""

    def test_simple_function(self):
        """Test finding function in simple function definition."""
        content = """
def simple_function():
    print("Hello")  # Line 2 (0-based: line 1)
    return True
"""
        # Line 2 in 1-based indexing is line 1 in 0-based
        result = find_enclosing_function(content, 2, 0)
        assert result == "simple_function"

    def test_nested_function(self):
        """Test finding innermost function in nested functions."""
        content = """
def outer_function():
    def inner_function():
        print("Inner")  # Line 3 (0-based: line 2)
        return True
    return inner_function()
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "inner_function"

    def test_class_method(self):
        """Test finding method inside class."""
        content = """
class TestClass:
    def method_one(self):
        print("Method one")  # Line 3 (0-based: line 2)
        return True

    def method_two(self):
        print("Method two")
        return False
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "method_one"

        result = find_enclosing_function(content, 7, 0)
        assert result == "method_two"

    def test_async_function(self):
        """Test finding async function."""
        content = """
async def async_function():
    await some_operation()  # Line 2 (0-based: line 1)
    return "done"
"""
        result = find_enclosing_function(content, 2, 0)
        assert result == "async_function"

    def test_deeply_nested_functions(self):
        """Test deeply nested functions."""
        content = """
def level_1():
    def level_2():
        def level_3():
            print("Deep")  # Line 4 (0-based: line 3)
            return "deep"
        return level_3()
    return level_2()
"""
        result = find_enclosing_function(content, 4, 0)
        assert result == "level_3"

    def test_line_outside_function(self):
        """Test line that's not inside any function."""
        content = """
# This is a comment
print("Global code")  # Line 2 (0-based: line 1)

def some_function():
    print("Inside function")
"""
        result = find_enclosing_function(content, 2, 0)
        assert result is None

    def test_line_at_function_definition(self):
        """Test line that's at the function definition itself."""
        content = """
def test_function():  # Line 1 (0-based: line 0)
    print("Inside")
    return True
"""
        result = find_enclosing_function(content, 1, 0)
        assert result == "test_function"

    def test_line_at_function_end(self):
        """Test line that's at the end of function."""
        content = """
def test_function():
    print("Inside")
    return True  # Line 3 (0-based: line 2)
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "test_function"

    def test_multiple_functions_same_level(self):
        """Test multiple functions at the same level."""
        content = """
def function_one():
    print("Function one")  # Line 2 (0-based: line 1)
    return 1

def function_two():
    print("Function two")  # Line 6 (0-based: line 5)
    return 2
"""
        result = find_enclosing_function(content, 2, 0)
        assert result == "function_one"

        result = find_enclosing_function(content, 6, 0)
        assert result == "function_two"

    def test_class_and_function_mix(self):
        """Test mix of classes and functions."""
        content = """
def standalone_function():
    print("Standalone")  # Line 2 (0-based: line 1)

class MyClass:
    def class_method(self):
        print("Class method")  # Line 6 (0-based: line 5)

    @staticmethod
    def static_method():
        print("Static method")  # Line 10 (0-based: line 9)
"""
        result = find_enclosing_function(content, 2, 0)
        assert result == "standalone_function"

        result = find_enclosing_function(content, 6, 0)
        assert result == "class_method"

        result = find_enclosing_function(content, 10, 0)
        assert result == "static_method"

    def test_invalid_syntax(self):
        """Test with invalid Python syntax."""
        content = """
def invalid_function(
    print("This is invalid syntax"
    return True
"""
        result = find_enclosing_function(content, 2, 0)
        assert result is None

    def test_empty_content(self):
        """Test with empty content."""
        result = find_enclosing_function("", 0, 0)
        assert result is None

    def test_line_number_out_of_bounds(self):
        """Test with line number beyond content."""
        content = """
def simple_function():
    return True
"""
        result = find_enclosing_function(content, 100, 0)
        assert result is None

    def test_negative_line_number(self):
        """Test with negative line number."""
        content = """
def simple_function():
    return True
"""
        result = find_enclosing_function(content, -1, 0)
        assert result is None

    def test_lambda_function(self):
        """Test with lambda functions (should not be detected as regular functions)."""
        content = """
lambda_func = lambda x: x * 2  # Line 1 (0-based: line 0)

def regular_function():
    another_lambda = lambda y: y + 1  # Line 4 (0-based: line 3)
    return another_lambda(5)
"""
        # Lambda functions should not be detected
        result = find_enclosing_function(content, 1, 0)
        assert result is None

        # Inside regular function
        result = find_enclosing_function(content, 4, 0)
        assert result == "regular_function"

    def test_decorator_function(self):
        """Test function with decorators."""
        content = """
@decorator
def decorated_function():
    print("Decorated")  # Line 3 (0-based: line 2)
    return True
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "decorated_function"

    def test_generator_function(self):
        """Test generator function."""
        content = """
def generator_function():
    for i in range(3):
        yield i  # Line 3 (0-based: line 2)
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "generator_function"


class TestExtractInheritanceRelations:
    """Test cases for extract_inheritance_relations function."""

    def test_simple_inheritance(self):
        """Test simple single inheritance."""
        content = """
class Parent:
    pass

class Child(Parent):
    pass
"""
        result = extract_inheritance_relations(content)
        assert result == [("Child", "Parent")]

    def test_multiple_inheritance(self):
        """Test multiple inheritance."""
        content = """
class Base1:
    pass

class Base2:
    pass

class Child(Base1, Base2):
    pass
"""
        result = extract_inheritance_relations(content)
        assert set(result) == {("Child", "Base1"), ("Child", "Base2")}

    def test_no_inheritance(self):
        """Test classes with no inheritance."""
        content = """
class StandaloneClass:
    pass

class AnotherClass:
    def method(self):
        pass
"""
        result = extract_inheritance_relations(content)
        assert result == []

    def test_mixed_inheritance_and_standalone(self):
        """Test mix of classes with and without inheritance."""
        content = """
class Base:
    pass

class Standalone:
    pass

class Derived(Base):
    pass
"""
        result = extract_inheritance_relations(content)
        assert result == [("Derived", "Base")]

    def test_chain_inheritance(self):
        """Test inheritance chain."""
        content = """
class GrandParent:
    pass

class Parent(GrandParent):
    pass

class Child(Parent):
    pass
"""
        result = extract_inheritance_relations(content)
        assert set(result) == {("Parent", "GrandParent"), ("Child", "Parent")}

    def test_module_qualified_inheritance(self):
        """Test inheritance from module-qualified classes."""
        content = """
import some_module

class MyClass(some_module.BaseClass):
    pass

class AnotherClass(package.module.BaseClass):
    pass
"""
        result = extract_inheritance_relations(content)
        assert set(result) == {
            ("MyClass", "some_module.BaseClass"),
            ("AnotherClass", "package.module.BaseClass"),
        }

    def test_builtin_inheritance(self):
        """Test inheritance from built-in types."""
        content = """
class MyList(list):
    pass

class MyDict(dict):
    pass

class MyException(Exception):
    pass
"""
        result = extract_inheritance_relations(content)
        assert set(result) == {
            ("MyList", "list"),
            ("MyDict", "dict"),
            ("MyException", "Exception"),
        }

    def test_complex_inheritance_scenario(self):
        """Test complex inheritance scenario."""
        content = """
class A:
    pass

class B(A):
    pass

class C:
    pass

class D(B, C):
    pass

class E(collections.abc.Mapping):
    pass
"""
        result = extract_inheritance_relations(content)
        expected = {
            ("B", "A"),
            ("D", "B"),
            ("D", "C"),
            ("E", "collections.abc.Mapping"),
        }
        assert set(result) == expected

    def test_invalid_syntax(self):
        """Test with invalid Python syntax."""
        content = """
class InvalidClass(
    pass
"""
        result = extract_inheritance_relations(content)
        assert result == []

    def test_empty_content(self):
        """Test with empty content."""
        result = extract_inheritance_relations("")
        assert result == []

    def test_no_classes(self):
        """Test with content that has no classes."""
        content = """
def function():
    pass

variable = 42
"""
        result = extract_inheritance_relations(content)
        assert result == []

    def test_nested_classes(self):
        """Test with nested classes."""
        content = """
class Outer:
    class Inner(Outer):
        pass

    class AnotherInner:
        pass
"""
        result = extract_inheritance_relations(content)
        assert result == [("Inner", "Outer")]


class TestExtractBaseName:
    """Test cases for _extract_base_name helper function."""

    def test_simple_name(self):
        """Test simple name node."""
        node = ast.Name(id="BaseClass", ctx=ast.Load())
        result = _extract_base_name(node)
        assert result == "BaseClass"

    def test_attribute_access(self):
        """Test attribute access (module.Class)."""
        # Create AST for "module.BaseClass"
        node = ast.Attribute(
            value=ast.Name(id="module", ctx=ast.Load()),
            attr="BaseClass",
            ctx=ast.Load(),
        )
        result = _extract_base_name(node)
        assert result == "module.BaseClass"

    def test_nested_attribute_access(self):
        """Test nested attribute access (package.module.Class)."""
        # Create AST for "package.module.BaseClass"
        node = ast.Attribute(
            value=ast.Attribute(
                value=ast.Name(id="package", ctx=ast.Load()),
                attr="module",
                ctx=ast.Load(),
            ),
            attr="BaseClass",
            ctx=ast.Load(),
        )
        result = _extract_base_name(node)
        assert result == "package.module.BaseClass"

    def test_unsupported_node_type(self):
        """Test with unsupported node type."""
        # Use a node type that's not Name or Attribute
        node = ast.Constant(value=42)
        result = _extract_base_name(node)
        assert result is None

    def test_attribute_with_unsupported_value(self):
        """Test attribute node with unsupported value type."""
        # Create attribute with unsupported value type
        node = ast.Attribute(
            value=ast.Constant(value=42),  # Unsupported value type
            attr="BaseClass",
            ctx=ast.Load(),
        )
        result = _extract_base_name(node)
        assert result == "BaseClass"


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    def test_large_file_simulation(self):
        """Test with a large file simulation."""
        # Create content with many classes and functions
        lines = ["# Large file simulation"]

        for i in range(50):
            lines.extend(
                [
                    f"class Class{i}:",
                    f"    def method_{i}(self):",
                    f"        print('Method {i}')  # Line for class {i}",
                    f"        return {i}",
                    "",
                ],
            )

        content = "\n".join(lines)

        # Test finding function in the middle
        # Each class block is 5 lines starting from line 1, so find a method line
        # Class 10's method should be around line 1 + (10 * 5) + 2 = 53
        method_line = (
            1 + (10 * 5) + 2
        )  # First line + (class_index * lines_per_class) + method_line_offset
        result = find_enclosing_function(content, method_line, 0)
        assert result is not None
        assert "method_" in result

    def test_unicode_content(self):
        """Test with Unicode content."""
        content = """
class 测试类:
    def 方法(self):
        print("测试")  # Line 3
        return True

class TestClass(测试类):
    pass
"""
        result = find_enclosing_function(content, 3, 0)
        assert result == "方法"

        inheritance = extract_inheritance_relations(content)
        assert ("TestClass", "测试类") in inheritance

    def test_mixed_indentation(self):
        """Test with mixed indentation (tabs and spaces)."""
        content = """
def function_with_spaces():
    print("Using spaces")  # Line 2
    return True

def function_with_tabs():
\tprint("Using tabs")  # Line 6
\treturn True
"""
        result = find_enclosing_function(content, 2, 0)
        assert result == "function_with_spaces"

        result = find_enclosing_function(content, 6, 0)
        assert result == "function_with_tabs"

    def test_comments_and_docstrings(self):
        """Test with extensive comments and docstrings."""
        content = '''
def documented_function():
    """
    This is a comprehensive docstring.
    It spans multiple lines.
    """
    # This is a comment
    print("Function body")  # Line 8
    return True
'''
        result = find_enclosing_function(content, 8, 0)
        assert result == "documented_function"

    @pytest.mark.parametrize(
        "line_num,expected",
        [
            (2, "func1"),  # Line 2 is inside func1
            (5, "func2"),  # Line 5 is inside func2
            (7, None),  # Line 7 is between functions (comment)
            (10, "func3"),  # Line 10 is inside func3
        ],
    )
    def test_parametrized_function_detection(self, line_num, expected):
        """Test function detection with various line numbers."""
        content = """
def func1():
    return 1  # Line 2

def func2():
    return 2  # Line 6

# Comment between functions  # Line 8

def func3():
    return 3  # Line 11
"""
        result = find_enclosing_function(content, line_num, 0)
        assert result == expected


class TestFindFunctionReferences:
    """Test cases for find_function_references function."""

    def test_simple_function_references(self):
        """Test finding references to a simple function."""
        content = """
def my_function():
    return True

result = my_function()
value = my_function()
"""
        from codn.utils.simple_ast import find_function_references

        references = find_function_references(content, "my_function")
        assert len(references) == 2
        assert (5, 9) in references  # First call
        assert (6, 8) in references  # Second call

    def test_no_references(self):
        """Test function with no references."""
        content = """
def my_function():
    return True

def other_function():
    return False
"""
        from codn.utils.simple_ast import find_function_references

        references = find_function_references(content, "unused_function")
        assert len(references) == 0

    def test_method_references(self):
        """Test finding references to methods."""
        content = """
class MyClass:
    def method(self):
        return True

obj = MyClass()
obj.method()
"""
        from codn.utils.simple_ast import find_function_references

        references = find_function_references(content, "method")
        assert len(references) == 1
        assert (7, 0) in references


class TestExtractFunctionSignatures:
    """Test cases for extract_function_signatures function."""

    def test_simple_function_signature(self):
        """Test extracting signature of a simple function."""
        content = """
def simple_func(a, b):
    '''A simple function.'''
    return a + b
"""
        from codn.utils.simple_ast import extract_function_signatures

        signatures = extract_function_signatures(content)
        assert len(signatures) == 1

        func = signatures[0]
        assert func["name"] == "simple_func"
        assert func["line"] == 2
        assert func["args"] == ["a", "b"]
        assert func["docstring"] == "A simple function."
        assert func["is_async"] is False

    def test_async_function_signature(self):
        """Test extracting signature of an async function."""
        content = """
async def async_func(x: int) -> str:
    return str(x)
"""
        from codn.utils.simple_ast import extract_function_signatures

        signatures = extract_function_signatures(content)
        assert len(signatures) == 1

        func = signatures[0]
        assert func["name"] == "async_func"
        assert func["is_async"] is True
        assert func["args"] == ["x"]

    def test_function_with_defaults(self):
        """Test extracting signature with default arguments."""
        content = """
def func_with_defaults(a, b=10, c="hello"):
    return a + b
"""
        from codn.utils.simple_ast import extract_function_signatures

        signatures = extract_function_signatures(content)
        assert len(signatures) == 1

        func = signatures[0]
        assert func["name"] == "func_with_defaults"
        assert func["args"] == ["a", "b", "c"]
        assert func["defaults"] == ["10", "'hello'"]


class TestFindUnusedImports:
    """Test cases for find_unused_imports function."""

    def test_unused_import(self):
        """Test finding unused imports."""
        content = """
import os
import sys
from pathlib import Path

print("Hello")
"""
        from codn.utils.simple_ast import find_unused_imports

        unused = find_unused_imports(content)
        assert len(unused) == 3
        unused_names = [name for name, line in unused]
        assert "os" in unused_names
        assert "sys" in unused_names
        assert "Path" in unused_names

    def test_used_import(self):
        """Test that used imports are not reported as unused."""
        content = """
import os
from pathlib import Path

path = Path("/tmp")
print(os.getcwd())
"""
        from codn.utils.simple_ast import find_unused_imports

        unused = find_unused_imports(content)
        assert len(unused) == 0

    def test_import_with_alias(self):
        """Test imports with aliases."""
        content = """
import numpy as np
import pandas as pd

data = np.array([1, 2, 3])
"""
        from codn.utils.simple_ast import find_unused_imports

        unused = find_unused_imports(content)
        assert len(unused) == 1
        assert unused[0][0] == "pd"


class TestExtractClassMethods:
    """Test cases for extract_class_methods function."""

    def test_simple_class_methods(self):
        """Test extracting methods from a simple class."""
        content = """
class MyClass:
    def __init__(self):
        pass

    def method1(self):
        return True

    @staticmethod
    def static_method():
        return False

    @classmethod
    def class_method(cls):
        return cls
"""
        from codn.utils.simple_ast import extract_class_methods

        methods = extract_class_methods(content)
        assert len(methods) == 4

        method_names = [m["method_name"] for m in methods]
        assert "__init__" in method_names
        assert "method1" in method_names
        assert "static_method" in method_names
        assert "class_method" in method_names

        # Check static method detection
        static_method = next(m for m in methods if m["method_name"] == "static_method")
        assert static_method["is_staticmethod"] is True

        # Check class method detection
        class_method = next(m for m in methods if m["method_name"] == "class_method")
        assert class_method["is_classmethod"] is True

    def test_specific_class_methods(self):
        """Test extracting methods from a specific class."""
        content = """
class ClassA:
    def method_a(self):
        pass

class ClassB:
    def method_b(self):
        pass
"""
        from codn.utils.simple_ast import extract_class_methods

        methods = extract_class_methods(content, "ClassA")
        assert len(methods) == 1
        assert methods[0]["method_name"] == "method_a"
        assert methods[0]["class_name"] == "ClassA"

    def test_async_method(self):
        """Test extracting async methods."""
        content = """
class AsyncClass:
    async def async_method(self):
        return True
"""
        from codn.utils.simple_ast import extract_class_methods

        methods = extract_class_methods(content)
        assert len(methods) == 1
        assert methods[0]["is_async"] is True
