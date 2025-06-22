# 🔍 codn

A powerful and intuitive toolkit for analyzing Python codebases.

[![PyPI version](https://badge.fury.io/py/codn.svg)](https://badge.fury.io/py/codn)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **📊 Project Analysis** - Get comprehensive statistics about your codebase
- **🔍 Function References** - Find where functions are called across your project
- **🧹 Import Cleanup** - Detect unused imports automatically
- **📝 Function Signatures** - Extract detailed function information
- **🏗️ Class Analysis** - Analyze class structures and inheritance
- **⚡ Fast & Reliable** - Built on Python's AST for accurate analysis
- **🎨 Beautiful Output** - Rich terminal interface with progress bars and tables

## 🚀 Quick Start

### Installation

#### Using uv (Recommended)
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install codn
uv tool install codn
```

#### Using pip
```bash
pip install codn
```

#### For Development
```bash
# Clone the repository
git clone https://github.com/dweb-lab/codn.git
cd codn

# Install with uv (recommended)
uv sync
uv run codn --help

# Or install with pip
pip install -e .
```

### Basic Usage

```bash
# Quick project analysis (most common)
codn

# Or use the detailed commands
codn analyze project

# Simplified commands (less typing!)
codn unused              # Find unused imports
codn refs my_function    # Find function references
codn funcs               # List all functions

# Traditional verbose commands (still supported)
codn analyze unused-imports
codn analyze find-refs my_function
codn analyze functions --signatures
```

## 📖 Common Use Cases

### 🔍 Code Exploration

**Understand a new codebase:**
```bash
cd /path/to/project
codn --verbose          # Quick way
# or
codn analyze project --verbose
```

**Find where a function is used:**
```bash
codn refs calculate_total        # Quick way
# or
codn analyze find-refs calculate_total
```

### 🧹 Code Cleanup

**Find unused imports:**
```bash
codn unused                     # Quick way
# or
codn analyze unused-imports
```

**Get function overview:**
```bash
codn funcs --signatures         # Quick way
# or
codn analyze functions --signatures
```

### ⚡ Git Integration

**Check repository health:**
```bash
codn git check --verbose
```

## 💻 Python API

You can also use codn programmatically:

```python
from codn import find_function_references, extract_function_signatures

# Find function references
code = open('my_file.py').read()
refs = find_function_references(code, 'my_function')

# Extract function signatures
signatures = extract_function_signatures(code)
for func in signatures:
    print(f"{func['name']} at line {func['line']}")
```

## 📊 Example Output

```
Project Analysis Results
     Project Statistics
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric            ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Python Files      │    25 │
│ Total Lines       │  3142 │
│ Functions         │   156 │
│ Classes           │    18 │
│ Methods           │    89 │
│ Files with Issues │     3 │
│ Unused Imports    │     7 │
│ Git Repository    │     ✓ │
└───────────────────┴───────┘
```

## 🎯 Key Commands

### Quick Commands (Recommended)
| Command | Description | Example |
|---------|-------------|---------|
| `codn` | Project overview (default) | `codn` |
| `unused` | Find unused imports | `codn unused` |
| `refs <func>` | Find function references | `codn refs main` |
| `funcs` | List functions and methods | `codn funcs --signatures` |

### Full Commands (Traditional)
| Command | Description | Example |
|---------|-------------|---------|
| `analyze project` | Project overview and statistics | `codn analyze project` |
| `analyze find-refs` | Find function references | `codn analyze find-refs main` |
| `analyze unused-imports` | Detect unused imports | `codn analyze unused-imports` |
| `analyze functions` | List functions and methods | `codn analyze functions --signatures` |
| `git check` | Validate Git repository | `codn git check` |

> 💡 **Tip**: Use quick commands to save typing! `codn` = `codn analyze project`, `codn unused` = `codn analyze unused-imports`, etc.

## 🏗️ Requirements

- Python 3.8+
- Works with any Python project
- No configuration required

### Package Manager Notes

- **uv**: Recommended for faster installs and better dependency management
- **pip**: Traditional option, works everywhere
- Both methods install the same functionality

### Environment Management

```bash
# With uv (handles virtual environments automatically)
uv tool install codn

# With pip in virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install codn
```

## 📚 Documentation

- **[CLI User Guide](docs/cli-guide.md)** - Complete command reference
- **[API Documentation](docs/api/)** - Python API reference
- **[Examples](docs/examples/)** - Code examples and use cases
- **[Development](docs/development/)** - Contributing and development setup

## 🤝 Contributing

We welcome contributions! Please see our [development documentation](docs/development/) and [quick development guide](docs/development/QUICK-GUIDE.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **PyPI**: https://pypi.org/project/codn/
- **Source Code**: https://github.com/dweb-lab/codn
- **Issue Tracker**: https://github.com/dweb-lab/codn/issues

---

**Made with ❤️ for Python developers who love clean, analyzable code.**
