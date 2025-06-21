#!/usr/bin/env python3
"""
Basic usage examples for codn library.

This file demonstrates the core functionality of codn's AST analysis tools.
"""

from codn.utils.simple_ast import (
    find_enclosing_function,
    find_function_references,
    extract_function_signatures,
    find_unused_imports,
    extract_class_methods,
    extract_inheritance_relations
)

# Sample code for analysis
SAMPLE_CODE = """
import os
import sys
from pathlib import Path
from typing import Optional

class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return "Some sound"

    @property
    def species(self) -> str:
        return "Unknown"

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

    @staticmethod
    def breed_info() -> dict:
        return {"family": "Canidae"}

def greet(name: str, greeting: str = "Hello") -> str:
    '''Greet someone with a message.'''
    return f"{greeting}, {name}!"

async def fetch_data(url: str) -> Optional[dict]:
    # This function uses some imports
    data_path = Path("/tmp/data")
    return {"status": "ok"}

def main():
    dog = Dog("Rex")
    message = greet("World")
    result = dog.speak()
    print(message)
    print(result)

if __name__ == "__main__":
    main()
"""


def demonstrate_function_analysis():
    """Demonstrate function signature extraction."""
    print("=== Function Signature Analysis ===")

    signatures = extract_function_signatures(SAMPLE_CODE)

    for func in signatures:
        print(f"Function: {func['name']}")
        print(f"  Line: {func['line']}")
        print(f"  Arguments: {func['args']}")
        if func['defaults']:
            print(f"  Defaults: {func['defaults']}")
        if func['return_type']:
            print(f"  Return type: {func['return_type']}")
        print(f"  Async: {func['is_async']}")
        if func['docstring']:
            print(f"  Docstring: {func['docstring']}")
        print()


def demonstrate_reference_finding():
    """Demonstrate finding function references."""
    print("=== Function Reference Analysis ===")

    # Find references to the 'greet' function
    references = find_function_references(SAMPLE_CODE, "greet")
    print(f"References to 'greet' function:")
    for line, col in references:
        print(f"  Line {line}, Column {col}")

    # Find references to the 'speak' method
    speak_refs = find_function_references(SAMPLE_CODE, "speak")
    print(f"\nReferences to 'speak' method:")
    for line, col in speak_refs:
        print(f"  Line {line}, Column {col}")
    print()


def demonstrate_enclosing_function():
    """Demonstrate finding enclosing functions."""
    print("=== Enclosing Function Analysis ===")

    # Test different line numbers
    test_lines = [26, 30, 40, 45]

    for line_num in test_lines:
        func_name = find_enclosing_function(SAMPLE_CODE, line_num, 0)
        print(f"Line {line_num}: {func_name or 'Not in any function'}")
    print()


def demonstrate_unused_imports():
    """Demonstrate unused import detection."""
    print("=== Unused Import Analysis ===")

    unused = find_unused_imports(SAMPLE_CODE)

    if unused:
        print("Unused imports found:")
        for import_name, line_num in unused:
            print(f"  Line {line_num}: {import_name}")
    else:
        print("No unused imports found!")
    print()


def demonstrate_class_analysis():
    """Demonstrate class and method analysis."""
    print("=== Class and Method Analysis ===")

    # Extract all methods
    methods = extract_class_methods(SAMPLE_CODE)

    print("All methods:")
    for method in methods:
        decorators = []
        if method['is_staticmethod']:
            decorators.append("@staticmethod")
        if method['is_classmethod']:
            decorators.append("@classmethod")
        if method['is_property']:
            decorators.append("@property")
        if method['is_async']:
            decorators.append("async")

        decorator_str = " ".join(decorators)
        print(f"  {method['class_name']}.{method['method_name']} "
              f"(line {method['line']}) {decorator_str}")

    # Extract inheritance relationships
    print("\nInheritance relationships:")
    relations = extract_inheritance_relations(SAMPLE_CODE)
    for child, parent in relations:
        print(f"  {child} inherits from {parent}")
    print()


def analyze_real_file(filepath: str):
    """Analyze a real Python file."""
    print(f"=== Analyzing File: {filepath} ===")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get basic statistics
        functions = extract_function_signatures(content)
        methods = extract_class_methods(content)
        unused = find_unused_imports(content)
        relations = extract_inheritance_relations(content)

        print(f"Statistics for {filepath}:")
        print(f"  Functions: {len(functions)}")
        print(f"  Methods: {len(methods)}")
        print(f"  Classes: {len(set(m['class_name'] for m in methods))}")
        print(f"  Unused imports: {len(unused)}")
        print(f"  Inheritance relations: {len(relations)}")

        # Show some details
        if functions:
            print(f"\nFirst few functions:")
            for func in functions[:3]:
                args_str = ", ".join(func['args']) if func['args'] else ""
                async_str = "async " if func['is_async'] else ""
                print(f"  {async_str}def {func['name']}({args_str})")

        if unused:
            print(f"\nUnused imports:")
            for name, line in unused[:5]:  # Show first 5
                print(f"  Line {line}: {name}")

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error analyzing file: {e}")
    print()


def main():
    """Run all demonstrations."""
    print("Codn Library - Basic Usage Examples")
    print("=" * 50)

    # Demonstrate all features with sample code
    demonstrate_function_analysis()
    demonstrate_reference_finding()
    demonstrate_enclosing_function()
    demonstrate_unused_imports()
    demonstrate_class_analysis()

    # Analyze this file itself as an example
    analyze_real_file(__file__)

    print("For more examples, see the CLI guide:")
    print("  codn analyze project")
    print("  codn analyze find-refs main")
    print("  codn analyze unused-imports")


if __name__ == "__main__":
    main()
