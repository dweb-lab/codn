# Contributing to codn

Thank you for your interest in contributing to codn! This guide will help you get started with development and understand our contribution process.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/codn.git
   cd codn
   ```

2. **Set up development environment**
   ```bash
   # Using uv (recommended)
   uv sync --group dev
   
   # Or using pip
   pip install -e ".[dev]"
   ```

3. **Verify setup**
   ```bash
   # Run tests
   python -m pytest
   
   # Check CLI
   python -m codn.cli --help
   ```

## 🔧 Development Workflow

### Project Structure

```
codn/
├── codn/                   # Main package
│   ├── cli.py             # CLI entry point
│   ├── cli_commands/      # CLI command modules
│   └── utils/             # Core utilities
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── *.py               # Integration tests
├── docs/                  # Documentation
│   ├── api/               # API reference
│   ├── examples/          # Code examples
│   └── development/       # Development docs
└── Makefile              # Development commands
```

### Available Commands

We use a Makefile for common development tasks:

```bash
# Show all available commands
make help

# Code quality
make format         # Format code with black and ruff
make lint           # Run linting checks
make check          # Run all quality checks

# Testing
make test           # Run all tests
make test-cov       # Run tests with coverage
make test-unit      # Run unit tests only
make test-fast      # Run fast tests only

# Cleanup
make clean          # Remove build artifacts
```

### Code Style

We follow these style guidelines:

- **PEP 8** for Python code style
- **Black** for automatic code formatting
- **Ruff** for fast linting
- **Type hints** for all public APIs
- **Docstrings** for all public functions and classes

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=codn

# Run specific test files
python -m pytest tests/unit/test_simple_ast.py

# Run tests matching a pattern
python -m pytest -k "test_function"

# Run tests with verbose output
python -m pytest -v
```

### Type Checking

```bash
# Run mypy type checking
mypy codn/

# Check specific files
mypy codn/utils/simple_ast.py
```

## 📝 Contributing Guidelines

### Submitting Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, focused commits
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   make check
   make test
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: add function reference analysis
fix: handle missing end_lineno in AST parsing
docs: update CLI usage examples
test: add edge cases for inheritance extraction
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests** (`tests/unit/`): Test individual functions and classes
- **Integration tests** (`tests/`): Test component interactions
- **CLI tests**: Test command-line interface

### Writing Tests

1. **Use descriptive test names**
   ```python
   def test_find_function_references_with_multiple_calls():
       """Test finding multiple references to the same function."""
   ```

2. **Follow the AAA pattern**
   ```python
   def test_extract_function_signatures():
       # Arrange
       content = "def hello(name: str) -> str: return f'Hello {name}'"
       
       # Act
       signatures = extract_function_signatures(content)
       
       # Assert
       assert len(signatures) == 1
       assert signatures[0]['name'] == 'hello'
   ```

3. **Test edge cases**
   - Empty input
   - Invalid syntax
   - Large files
   - Unicode content

4. **Use fixtures for common data**
   ```python
   @pytest.fixture
   def sample_python_code():
       return """
       def greet(name: str) -> str:
           return f"Hello, {name}!"
       """
   ```

### Test Coverage

We aim for >95% test coverage. Check coverage with:

```bash
make test-cov
```

View detailed coverage report:
```bash
python -m pytest --cov=codn --cov-report=html
open htmlcov/index.html
```

## 📖 Documentation

### API Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include examples in docstrings

```python
def find_function_references(content: str, function_name: str) -> List[Tuple[int, int]]:
    """
    Find all references to a function in the given content.

    Args:
        content: Python source code to analyze
        function_name: Name of the function to find references for

    Returns:
        List of (line_number, column_offset) tuples where function is referenced

    Example:
        >>> code = "def foo(): pass\\nresult = foo()"
        >>> find_function_references(code, "foo")
        [(2, 9)]
    """
```

### CLI Documentation

- Update CLI help text for new commands
- Add examples to the CLI guide
- Test all documented examples

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to reproduce**: Minimal example to reproduce the bug
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: Python version, OS, codn version
6. **Code sample**: Minimal code that demonstrates the issue

## 💡 Feature Requests

For new features:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and why it's valuable
3. **Propose an API** if applicable
4. **Consider backward compatibility**

## 🔍 Code Review Process

All changes go through code review:

1. **Automated checks** must pass (tests, linting, type checking)
2. **At least one reviewer** must approve
3. **All discussions** must be resolved
4. **Documentation** must be updated for user-facing changes

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] Backward compatibility is maintained
- [ ] Performance impact is considered
- [ ] Security implications are reviewed

## 🚀 Release Process

Releases follow semantic versioning (SemVer):

- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

### Release Steps

1. Update version numbers
2. Update CHANGELOG.md
3. Create git tag
4. Build and test package
5. Publish to PyPI
6. Create GitHub release

## 🤝 Community

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Discord/Slack**: Community chat (if available)

### Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct. Be respectful, inclusive, and constructive in all interactions.

## 📋 Development Tips

### Performance Considerations

- Profile code changes with large codebases
- Consider memory usage for file processing
- Use async/await for I/O operations when appropriate

### Debugging

```python
# Add debug logging
from loguru import logger
logger.debug(f"Processing file: {file_path}")

# Use pdb for interactive debugging
import pdb; pdb.set_trace()
```

### IDE Setup

**VS Code:**
- Install Python extension
- Configure settings for black, ruff, mypy
- Use debugger for testing

**PyCharm:**
- Configure code style settings
- Set up run configurations for tests
- Use integrated debugger

## 🎯 Areas for Contribution

Current areas where we welcome contributions:

1. **New AST analysis features**
2. **Performance optimizations**
3. **CLI improvements**
4. **Documentation and examples**
5. **Test coverage improvements**
6. **Bug fixes**

Check our [roadmap](roadmap.md) for planned features and our [GitHub issues](https://github.com/dweb-lab/codn/issues) for current tasks.

---

Thank you for contributing to codn! Your efforts help make Python development more productive and enjoyable for everyone. 🎉