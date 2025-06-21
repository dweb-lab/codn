# Make Clean Commands Documentation

This document describes the various cleaning commands available in the codn project's Makefile.

## Overview

The codn project provides several `make clean` commands to help you manage build artifacts, cache files, and temporary files efficiently. These commands are designed to keep your development environment clean and free up disk space.

## Available Commands

### Basic Clean Commands

#### `make clean`
**Full cleaning with detailed progress**
- Removes all build artifacts, cache files, and temporary files
- Preserves `.venv` directory and important project files
- Shows detailed progress with emoji indicators
- **Recommended for regular cleanup**

```bash
make clean
```

#### `make clean-all`
**Deep cleaning (includes virtual environment)**
- Performs all operations of `make clean`
- **Additionally removes `.venv` directory**
- Use with caution - you'll need to reinstall dependencies
- Good for complete project reset

```bash
make clean-all
```

#### `make clean-safe`
**Conservative cleaning**
- Cleans only essential build and cache files
- Extra safety checks to preserve important files
- Good for automated scripts or CI/CD

```bash
make clean-safe
```

### Targeted Clean Commands

#### `make clean-build`
**Build artifacts only**
- Removes `build/`, `dist/`, `*.egg-info/` directories
- Preserves all other files
- Fast and focused

```bash
make clean-build
```

#### `make clean-test`
**Test artifacts only**
- Removes `.pytest_cache/`, `.coverage`, `htmlcov/`, `reports/`
- Cleans test-related temporary files
- Useful during test development

```bash
make clean-test
```

#### `make clean-cache`
**Cache files only**
- Removes `.mypy_cache/`, `.ruff_cache/`, `.ropeproject/`
- Cleans Python `__pycache__` directories and `.pyc` files
- Good for fixing cache-related issues

```bash
make clean-cache
```

### Inspection Commands

#### `make clean-status`
**Show what would be cleaned**
- Lists all files and directories that would be affected
- Shows ✓ for items found, ✗ for items not found
- Provides counts for categories like cache files
- **Run this before cleaning to see what will happen**

```bash
make clean-status
```

Example output:
```
🔍 Checking for files and directories that would be cleaned...

📦 Build artifacts:
  ✓ build/
  ✗ dist/ (not found)
  ✓ *.egg-info/

🧪 Test artifacts:
  ✓ .pytest_cache/
  ✓ .coverage
  ✗ htmlcov/ (not found)

🐍 Python cache files:
  ✓ 3 __pycache__ directories
  ✓ 12 .pyc files

📝 Temporary files:
  ✓ 2 temporary files
  ✗ No .DS_Store files found

💡 Run 'make clean' to clean all items marked with ✓
```

#### `make clean-size`
**Show disk space that would be freed**
- Calculates and displays the size of files to be cleaned
- Breaks down size by category
- Shows total space that would be freed
- **Useful for understanding disk space impact**

```bash
make clean-size
```

Example output:
```
📊 Calculating size of files and directories to be cleaned...

📦 Build artifacts:
  build/: 2.3M
  dist/: 1.1M

🧪 Test artifacts:
  .pytest_cache/: 450K
  htmlcov/: 2.1M

🔍 Cache directories:
  .mypy_cache/: 15.2M
  .ruff_cache/: 3.4M

📊 Total size to be cleaned: 24.5M

💡 Run 'make clean' to free up this space
```

## What Gets Cleaned

### Build Artifacts
- `build/` - Build output directory
- `dist/` - Distribution packages
- `*.egg-info/` - Python package metadata
- `codn.egg-info/` - Project-specific metadata

### Test Artifacts
- `.pytest_cache/` - Pytest cache
- `.coverage` - Coverage data file
- `.coverage.*` - Coverage data files (multiple runs)
- `htmlcov/` - HTML coverage reports
- `reports/` - Test reports directory
- `junit.xml` - JUnit test reports
- `.testmondata` - Test monitoring data
- `test-results/` - Test result files
- `pytest.xml` - Pytest XML reports
- `mypy.xml` - MyPy XML reports

### Cache Directories
- `.mypy_cache/` - MyPy type checker cache
- `.ruff_cache/` - Ruff linter cache
- `.ropeproject/` - Rope refactoring tool cache
- `.tox/` - Tox testing environments
- `.nox/` - Nox testing sessions

### Python Cache Files
- `__pycache__/` directories (excluding those in `.venv/`)
- `*.pyc` files - Python compiled bytecode
- `*.pyo` files - Python optimized bytecode
- `*.pyd` files - Python dynamic modules

### Temporary Files
- `*.tmp` - Temporary files
- `*.temp` - Temporary files
- `*.log` - Log files
- `*~` - Backup files (created by editors)
- `.DS_Store` - macOS Finder metadata files
- `.coverage.lock` - Coverage lock files

### Empty Directories
- Any empty directories (excluding `.git/` and `.venv/`)

## Safety Features

### Virtual Environment Protection
All commands (except `clean-all`) preserve the `.venv/` directory and its contents, ensuring your Python environment remains intact.

### Git Repository Protection
The `.git/` directory and its contents are never touched by any clean command.

### Progress Indicators
All commands provide clear visual feedback with:
- 🧹 Cleaning indicators
- 📦 Build artifact operations
- 🧪 Test artifact operations
- 🔍 Cache operations
- 🐍 Python file operations
- ✅ Success confirmations

## Best Practices

### Regular Maintenance
```bash
# Check what needs cleaning
make clean-status

# Clean regularly during development
make clean

# Deep clean when switching branches or major changes
make clean-all
```

### Before Important Operations
```bash
# Before creating releases
make clean-build
make clean-test

# Before running comprehensive tests
make clean-cache
```

### Disk Space Management
```bash
# Check how much space you can free
make clean-size

# Free up space quickly
make clean
```

### CI/CD Integration
```bash
# Safe cleaning in automated environments
make clean-safe

# Full clean for fresh builds
make clean-all
```

## Troubleshooting

### Permission Errors
If you encounter permission errors, ensure you have write access to all directories. The commands use `rm -rf` which requires appropriate permissions.

### Files Not Being Cleaned
1. Check if files are in use by running processes
2. Verify file permissions
3. Use `make clean-status` to see what the command detects

### Accidentally Removed Important Files
The clean commands are designed to be safe, but if you accidentally run `make clean-all`:
1. Recreate virtual environment: `make install` or `make dev-install`
2. Reinstall dependencies: `uv sync` or `pip install -e .`

### Performance Issues
If cleaning is slow:
- Large `.venv/` directories are preserved (good!)
- Use targeted commands like `make clean-cache` for faster operations
- The `find` commands may be slow on large codebases

## Integration with Development Workflow

### Daily Development
```bash
# Start of day - check status
make clean-status

# After major refactoring
make clean-cache

# Before committing
make clean
```

### Testing Workflow
```bash
# Before running test suite
make clean-test

# After coverage analysis
make clean-test
```

### Release Workflow
```bash
# Before building packages
make clean-build

# Full clean before final build
make clean
```

## Command Reference Quick Card

| Command | Speed | Safety | What it cleans |
|---------|-------|--------|----------------|
| `make clean` | Medium | High | Everything except .venv |
| `make clean-all` | Medium | Low | Everything including .venv |
| `make clean-safe` | Fast | Very High | Essential files only |
| `make clean-build` | Fast | Very High | Build artifacts only |
| `make clean-test` | Fast | Very High | Test artifacts only |
| `make clean-cache` | Fast | High | Cache files only |
| `make clean-status` | Very Fast | N/A | Shows status only |
| `make clean-size` | Fast | N/A | Shows sizes only |

## Error Handling

The clean commands are designed to be robust:
- Use `2>/dev/null || true` to handle missing files gracefully
- Include safety checks for important directories
- Provide clear error messages when operations fail
- Never fail the entire build due to cleaning issues

## Customization

To add custom cleaning rules, edit the `Makefile` and add your patterns to the appropriate clean command. Follow the existing pattern of:
1. Clear progress indication with emoji
2. Safety checks for important directories
3. Graceful error handling
4. Detailed success confirmation
