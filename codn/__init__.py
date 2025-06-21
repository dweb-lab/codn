"""
codn - A tiny, modular library for common coding tasks.

This package provides utilities for Python development including:
- AST-based code analysis tools
- Language Server Protocol client for Pyright
- Git repository validation utilities
- File system operations with gitignore support
"""

__version__ = "0.1.1"
__author__ = "askender"
__email__ = "askender43@gmail.com"

# Import main utilities for convenient access
from .utils.simple_ast import find_enclosing_function, extract_inheritance_relations
from .utils.git_utils import is_valid_git_repo
from .utils.os_utils import list_all_python_files, load_gitignore, should_ignore

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "find_enclosing_function",
    "extract_inheritance_relations",
    "is_valid_git_repo",
    "list_all_python_files",
    "load_gitignore",
    "should_ignore",
]
