# codn

**Codn** is a lightweight, modular Python library designed for common coding tasks and source code analysis. It provides essential utilities for Git operations, file system traversal, AST parsing, and language server integration.

## 🌟 Features

* ⚡ **Lightweight** — minimal footprint with carefully selected dependencies
* 🔧 **Practical** — packed with useful, reusable utility functions for real-world development
* 🧩 **Modular** — import only what you need, keeping your project lean
* 🚀 **Fast to integrate** — plug-and-play design for rapid development
* 🌱 **Extensible** — easy to grow and adapt with your project needs
* 🛠️ **CLI Ready** — includes command-line tools for immediate productivity

## 📦 Installation

```bash
pip install codn
```

Or using uv (recommended):

```bash
uv add codn
```

## 🚀 Quick Start

### As a Library

```python
# Git utilities
from codn.utils.git_utils import is_valid_git_repo
is_valid = is_valid_git_repo("/path/to/repo")

# File system utilities  
from codn.utils.os_utils import list_all_python_files
async for py_file in list_all_python_files():
    print(py_file)

# AST utilities
from codn.utils.simple_ast import find_enclosing_function, extract_inheritance_relations
function_name = find_enclosing_function(source_code, line_number, char_pos)
inheritance = extract_inheritance_relations(source_code)
```

### As a CLI Tool

```bash
# Check if a directory is a valid Git repository
codn git check /path/to/repo

# Check current directory
codn git check

# Verbose output
codn git check --verbose
```

## 📖 Documentation

### Git Utilities (`codn.utils.git_utils`)

#### `is_valid_git_repo(path: Union[str, Path]) -> bool`

Validates if a given path contains a healthy Git repository.

**Features:**
- Checks for `.git` directory existence
- Verifies HEAD commit accessibility
- Performs repository integrity checks
- Handles edge cases and provides detailed error reporting

**Example:**
```python
from codn.utils.git_utils import is_valid_git_repo
from pathlib import Path

# Check current directory
if is_valid_git_repo("."):
    print("✅ Valid Git repository")
else:
    print("❌ Not a valid Git repository")

# Check specific path
repo_path = Path("/home/user/my-project")
if is_valid_git_repo(repo_path):
    print(f"✅ {repo_path} is a valid Git repository")
```

### File System Utilities (`codn.utils.os_utils`)

#### `list_all_python_files(root: Union[str, Path], ignored_dirs: Optional[Set[str]]) -> AsyncGenerator[Path, None]`

Asynchronously discovers Python files while respecting `.gitignore` patterns and common ignore directories.

**Features:**
- Async file discovery for better performance
- Automatic `.gitignore` pattern matching
- Configurable directory exclusions
- Handles encoding issues gracefully

**Default ignored directories:**
`.git`, `.github`, `__pycache__`, `.venv`, `venv`, `env`, `.mypy_cache`, `.pytest_cache`, `node_modules`, `dist`, `build`, `.idea`, `.vscode`

**Example:**
```python
import asyncio
from codn.utils.os_utils import list_all_python_files

async def find_python_files():
    python_files = []
    async for py_file in list_all_python_files("./src"):
        python_files.append(py_file)
    return python_files

# Run async function
files = asyncio.run(find_python_files())
print(f"Found {len(files)} Python files")
```

#### Utility Functions

- `load_gitignore(root_path: Path) -> pathspec.PathSpec`: Loads and parses `.gitignore` patterns
- `should_ignore(file_path, root_path, ignored_dirs, gitignore_spec) -> bool`: Determines if a file should be ignored

### AST Utilities (`codn.utils.simple_ast`)

#### `find_enclosing_function(content: str, line: int, character: int) -> Optional[str]`

Finds the name of the function or method containing a specific line position.

**Example:**
```python
from codn.utils.simple_ast import find_enclosing_function

source_code = """
def outer_function():
    def inner_function():
        print("Hello")  # Line 3
        return True
    return inner_function()
"""

function_name = find_enclosing_function(source_code, 3, 0)
print(function_name)  # Output: "inner_function"
```

#### `extract_inheritance_relations(content: str) -> List[Tuple[str, str]]`

Extracts class inheritance relationships from Python source code.

**Example:**
```python
from codn.utils.simple_ast import extract_inheritance_relations

source_code = """
class Animal:
    pass

class Dog(Animal):
    pass

class Puppy(Dog):
    pass
"""

relations = extract_inheritance_relations(source_code)
print(relations)  # Output: [('Dog', 'Animal'), ('Puppy', 'Dog')]
```

### Pyright LSP Client (`codn.utils.pyright_lsp_client`)

A comprehensive Language Server Protocol client for Pyright integration, enabling advanced code analysis capabilities.

**Features:**
- Async LSP communication
- File watching and synchronization
- Diagnostic reporting
- Configurable timeout and logging

## 🛠️ CLI Commands

### Git Commands

```bash
# Check repository health
codn git check [PATH] [OPTIONS]

OPTIONS:
  --verbose, -v    Show detailed output
  --help          Show help message
```

**Examples:**
```bash
# Check current directory
codn git check

# Check specific directory with verbose output
codn git check /path/to/repo --verbose

# Check multiple repositories
codn git check ./project1 && codn git check ./project2
```

## 🔧 Development

### Prerequisites

- Python 3.8+
- uv (recommended) or pip

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/dweb-lab/codn.git
cd codn

# Install with development dependencies
uv sync --group dev

# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test categories
make test-unit
make test-integration
make test-slow

# Run tests in parallel
make test-parallel
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Run all checks
make check
```

### Available Make Commands

```bash
make help           # Show all available commands
make test           # Run all tests
make test-cov       # Run tests with coverage
make lint           # Run linting checks
make format         # Format code
make clean          # Clean build artifacts
make all            # Format, lint, and test
```

## 📋 Requirements

### Runtime Dependencies

- `typer` - CLI framework
- `watchfiles` - File watching capabilities
- `pathspec` - Gitignore pattern matching
- `loguru` - Structured logging

### Development Dependencies

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `ruff` - Fast Python linter
- `mypy` - Type checking

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make check`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Write tests for new functionality
- Follow PEP 8 style guidelines (automated by `black` and `ruff`)
- Add type hints for all public APIs
- Update documentation for user-facing changes
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Homepage**: https://github.com/dweb-lab/codn
- **Issues**: https://github.com/dweb-lab/codn/issues
- **PyPI**: https://pypi.org/project/codn/

## 🎯 Roadmap

- [ ] Enhanced AST analysis features
- [ ] Code graph generation and analysis
- [ ] Additional language server integrations
- [ ] Performance optimizations
- [ ] Extended CLI functionality
- [ ] Documentation website

## 💡 Use Cases

**codn** is perfect for:

- **Code analysis tools** - Build custom static analysis tools
- **Development workflows** - Automate common development tasks
- **Repository maintenance** - Validate and maintain code repositories
- **IDE integrations** - Power custom editor extensions
- **CI/CD pipelines** - Integrate code quality checks
- **Research projects** - Analyze codebases at scale

---

Made with ❤️ by the codn team