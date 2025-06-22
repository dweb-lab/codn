# codn Documentation

Welcome to the codn documentation! This guide will help you get the most out of codn's powerful code analysis capabilities.

## 🚀 Quick Links

- **[Getting Started](#getting-started)** - Installation and basic usage
- **[Recent Improvements](RECENT_IMPROVEMENTS.md)** - Latest enhancements and features
- **[CLI Guide](cli-guide.md)** - Complete command reference
- **[API Reference](api/)** - Python API documentation
- **[Examples](examples/)** - Code examples and use cases
- **[Development](development/)** - Contributing and development setup
- **[Quick Development Guide](development/QUICK-GUIDE.md)** - Essential commands for developers

## 📚 What is codn?

codn is a powerful toolkit for analyzing Python codebases. It provides:

- **Project Analysis** - Comprehensive codebase statistics
- **Function References** - Find where functions are used
- **Import Analysis** - Detect unused imports
- **Code Structure** - Analyze classes, methods, and inheritance
- **CLI Tools** - Beautiful command-line interface
- **Python API** - Programmatic access to all features

## 🎯 Getting Started

### Installation

```bash
pip install codn
```

### Basic Commands

```bash
# Analyze your project
codn analyze project

# Find function references
codn analyze find-refs my_function

# Check for unused imports
codn analyze unused-imports

# List all functions
codn analyze functions --signatures
```

### Python API

```python
from codn import find_function_references, extract_function_signatures

# Analyze code
code = open('my_file.py').read()
refs = find_function_references(code, 'my_function')
sigs = extract_function_signatures(code)
```

## 📖 Documentation Sections

### For Users

- **[CLI User Guide](cli-guide.md)** - Complete command-line reference
  - All available commands
  - Options and flags
  - Usage examples
  - Common workflows

- **[API Documentation](api/)** - Python API reference
  - [AST Tools](api/ast-tools.md) - Function and class analysis
  - Code examples for each function
  - Parameter descriptions and return values

- **[Examples](examples/)** - Practical code examples
  - [Basic Usage](examples/basic-usage.py) - Getting started examples
  - Real-world use cases
  - Integration patterns

### For Developers

- **[Contributing Guide](development/contributing.md)** - How to contribute
  - Development setup
  - Code style guidelines
  - Testing procedures
  - Submission process

- **[Development Docs](development/)** - Technical documentation
  - [Quick Development Guide](development/QUICK-GUIDE.md) - Essential commands and workflows
  - [Analyze Command Improvements](development/analyze-command-improvements.md) - UI/UX improvements
  - [Ruff Setup Guide](development/ruff-setup.md) - Linting and formatting configuration
  - [Roadmap](development/roadmap.md) - Future plans and features
  - [Testing Guide](development/pytest-guide.md) - Comprehensive testing docs
  - [Quick Reference](development/pytest-quickref.md) - Testing quick reference

## 🔍 Use Cases

### Code Exploration
- Understand new codebases quickly
- Find function usage across projects
- Analyze code structure and relationships

### Code Quality
- Detect unused imports
- Find dead code
- Analyze function complexity

### Refactoring
- Safely rename functions by finding all references
- Understand impact of changes
- Clean up imports and dependencies

### Development Tools
- Build custom analysis tools
- Integrate with CI/CD pipelines
- Create IDE extensions

## 💡 Examples

### Analyze a Django Project

```bash
cd my-django-project
codn analyze project --verbose
codn analyze unused-imports
codn analyze find-refs User
```

### Find Dead Code

```bash
# List all functions
codn analyze functions > all_functions.txt

# Check each function for references
# (automation script recommended)
```

### Clean Up Imports

```bash
# Find unused imports
codn analyze unused-imports

# Review and remove manually
# (automatic removal coming in future versions)
```

## 🛠️ Integration

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Code Analysis
  run: |
    pip install codn
    codn analyze project
    codn analyze unused-imports
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/dweb-lab/codn
    hooks:
      - id: codn-check
        args: [analyze, unused-imports]
```

### VS Code Integration

Use codn in VS Code tasks:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Analyze Project",
      "type": "shell",
      "command": "codn analyze project",
      "group": "build"
    }
  ]
}
```

## 🚀 Performance Tips

- Use specific paths instead of analyzing entire large repositories
- Exclude test directories when focusing on production code (`--include-tests` flag)
- Use `--verbose` only when you need detailed information

## 🤝 Getting Help

- **Issues**: [GitHub Issues](https://github.com/dweb-lab/codn/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dweb-lab/codn/discussions)
- **Examples**: See the [examples directory](examples/)

## 📝 Contributing

We welcome contributions! See our [Contributing Guide](development/contributing.md) for details on:

- Setting up development environment
- Code style and testing requirements
- Submitting pull requests
- Areas where we need help

## 🎯 Roadmap

See our [development roadmap](development/roadmap.md) for planned features and improvements.

---

**Happy coding with codn! 🚀**
