"""
codn - A tiny, modular library for common coding tasks.

This package provides utilities for Python development including:
- AST-based code analysis tools
- Language Server Protocol client for Pyright
- Git repository validation utilities
- File system operations with gitignore support
"""

__version__ = "0.1.2"
__author__ = "askender"
__email__ = "askender43@gmail.com"

# Import main utilities for convenient access
from .utils.git_utils import is_valid_git_repo
from .utils.os_utils import list_all_python_files, load_gitignore, should_ignore
from .utils.simple_ast import (
    extract_class_methods,
    extract_function_signatures,
    extract_inheritance_relations,
    find_enclosing_function,
    find_function_references,
    find_unused_imports,
)

__all__ = [
    "__author__",
    "__email__",
    "__version__",
    "extract_class_methods",
    "extract_function_signatures",
    "extract_inheritance_relations",
    "find_enclosing_function",
    "find_function_references",
    "find_unused_imports",
    "is_valid_git_repo",
    "list_all_python_files",
    "load_gitignore",
    "should_ignore",
]
