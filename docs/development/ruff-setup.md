# Ruff Configuration Guide

This guide explains how to use ruff for linting and formatting in the codn project.

## Quick Start

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Format code
ruff format .

# Quick pre-commit check
./check-ruff.sh
```

## Configuration Overview

The project uses ruff for both linting and formatting with a practical configuration that:

- ✅ Enforces code quality without being overly strict
- ✅ Focuses on readability and maintainability
- ✅ Integrates seamlessly with development workflow
- ✅ Provides fast performance with local installation

## Available Commands

### Make Targets
```bash
make ruff-check        # Check for linting issues
make pre-commit-fast   # Fast pre-commit check (recommended)
make test-hooks-fast   # Test pre-commit hooks locally
```

### Direct Commands
```bash
# Linting
ruff check .                    # Check all files
ruff check . --fix             # Auto-fix issues
ruff check path/to/file.py     # Check specific file

# Formatting
ruff format .                  # Format all files
ruff format . --check          # Check formatting without changes
ruff format path/to/file.py    # Format specific file
```

### Shell Script
```bash
./check-ruff.sh              # Combined lint + format check
```

## Pre-commit Integration

The project uses optimized pre-commit hooks with local ruff installation for speed:

```bash
# Install hooks
make install-hooks

# Test hooks (fast)
make test-hooks-fast

# Manual hook run
pre-commit run ruff --all-files
pre-commit run ruff-format --all-files
```

**Performance**: Pre-commit hooks use local ruff installation (10x faster than GitHub downloads).

## Configuration Details

### Excluded Rules
The following rule categories are currently disabled for practical development:

- **Type annotations** (ANN*) - Focus on core functionality first
- **Boolean parameters** (FBT*) - Common pattern in CLI applications
- **Some security warnings** (S602, S603, S607) - Handled appropriately in context
- **Exception patterns** (TRY*, EM*, B904) - Current patterns are acceptable

### Key Settings
- **Line length**: 88 characters (Black compatible)
- **Target Python**: 3.8+
- **Formatter conflicts**: Resolved (COM812, ISC001 disabled)
- **File exclusions**: Tests, docs, and scripts have relaxed rules

## Recommended Workflow

### During Development
```bash
# Quick check before committing
make pre-commit-fast
```

### Before Push
```bash
# Comprehensive check
./check-ruff.sh

# Or individual steps
ruff check . --fix
ruff format .
```

### CI/CD Integration
The configuration is ready for automated checking in CI pipelines:

```yaml
- name: Lint with ruff
  run: |
    pip install ruff
    ruff check .
    ruff format . --check
```

## Troubleshooting

### Common Issues

**Import organization**: Move all imports to the top of files
```python
# Good
import os
import sys
from pathlib import Path

# Bad - imports mixed with code
import os
some_code()
import sys  # This will fail
```

**Line length**: Break long lines
```python
# Good
result = some_function(
    parameter1=value1,
    parameter2=value2,
    parameter3=value3,
)

# Bad - too long
result = some_function(parameter1=value1, parameter2=value2, parameter3=value3, parameter4=value4)
```

**Type annotations**: Use modern patterns
```python
# Good
from typing import Annotated
import typer

def command(name: Annotated[str, typer.Argument()]) -> None:
    pass

# Deprecated - will be flagged
def command(name: str = typer.Argument()) -> None:
    pass
```

### Getting Help

- Check `ruff.toml` for current configuration
- Run `ruff check --help` for command options
- See [Ruff documentation](https://docs.astral.sh/ruff/) for rule details

## Future Improvements

- Gradually re-enable stricter type checking rules
- Add more comprehensive security checks
- Consider additional code quality metrics

---

**Result**: Clean, consistent code that passes all checks automatically! 🚀
