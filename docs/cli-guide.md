# CLI User Guide

The `codn` command-line interface provides powerful tools for analyzing Python codebases. This guide covers all available commands and their usage.

## Installation

```bash
pip install codn
```

## Quick Start

```bash
# Analyze your current project
codn analyze project

# Find all references to a function
codn analyze find-refs my_function

# Check for unused imports
codn analyze unused-imports
```

## Commands Overview

### Git Commands

#### `codn git check`

Check if a directory is a valid Git repository.

```bash
# Check current directory
codn git check

# Check specific path
codn git check /path/to/repo

# Verbose output
codn git check --verbose
```

**Options:**
- `--verbose, -v`: Show detailed validation information

### Analysis Commands

#### `codn analyze project`

Analyze project structure and provide comprehensive statistics.

```bash
# Analyze current directory
codn analyze project

# Analyze specific path
codn analyze project /path/to/project

# Include test files in analysis
codn analyze project --include-tests

# Show detailed file-by-file breakdown
codn analyze project --verbose
```

**Options:**
- `--include-tests`: Include test files in analysis (default: excludes test directories)
- `--verbose, -v`: Show detailed output with per-file statistics

**Example Output:**
```
Project Analysis Results
     Project Statistics
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric            ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Python Files      │    15 │
│ Total Lines       │  2431 │
│ Functions         │    89 │
│ Classes           │     8 │
│ Methods           │    52 │
│ Files with Issues │     3 │
│ Unused Imports    │    12 │
│ Git Repository    │     ✓ │
└───────────────────┴───────┘
```

#### `codn analyze find-refs`

Find all references to a function across the project.

```bash
# Find references to a function
codn analyze find-refs function_name

# Search in specific directory
codn analyze find-refs function_name /path/to/search

# Include test files in search
codn analyze find-refs function_name --include-tests
```

**Options:**
- `--include-tests`: Include test files in search

**Example Output:**
```
Searching for references to 'extract_function_signatures' in: .

codn/cli_commands/analyze_cli.py
  Line 83: functions = extract_function_signatures(content)
  Line 335: functions = extract_function_signatures(content)

Found 2 references to 'extract_function_signatures'
```

#### `codn analyze unused-imports`

Find unused import statements in Python files.

```bash
# Find unused imports in current directory
codn analyze unused-imports

# Analyze specific path
codn analyze unused-imports /path/to/analyze

# Include test files
codn analyze unused-imports --include-tests

# Experimental: attempt to fix automatically (not yet implemented)
codn analyze unused-imports --fix
```

**Options:**
- `--include-tests`: Include test files in analysis
- `--fix`: Automatically remove unused imports (experimental, not yet implemented)

**Example Output:**
```
Finding unused imports in: .

codn/utils/simple_ast.py
  Line 3: unused import 'Path'
  Line 2: unused import 'Set'

codn/cli_commands/analyze_cli.py
  Line 11: unused import 'Panel'
  Line 7: unused import 'List'

Found 4 unused imports in 2 files
```

#### `codn analyze functions`

Analyze functions and methods in the project.

```bash
# List all functions and methods
codn analyze functions

# Show function signatures
codn analyze functions --signatures

# Filter by specific class
codn analyze functions --class ClassName

# Include test files
codn analyze functions --include-tests

# Analyze specific directory
codn analyze functions /path/to/analyze
```

**Options:**
- `--class`: Filter methods by class name
- `--signatures`: Show function signatures (arguments)
- `--include-tests`: Include test files in analysis

**Example Output:**
```
Functions (70)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┓
┃ Function                  ┃ File                      ┃ Line ┃ Async ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━┩
│ analyze_project           │ cli_commands/analyze_cli… │   30 │       │
│ find_references           │ cli_commands/analyze_cli… │  167 │       │
│ extract_function_signatu… │ utils/simple_ast.py       │  171 │       │
└───────────────────────────┴───────────────────────────┴──────┴───────┘

Methods (40)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┓
┃ Class            ┃ Method                 ┃ File                      ┃ Line ┃ Type  ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━┩
│ PyrightLSPClient │ __init__               │ utils/pyright_lsp_client… │   37 │       │
│ PyrightLSPClient │ start                  │ utils/pyright_lsp_client… │   54 │ async │
│ Calculator       │ add                    │ examples/calculator.py    │   10 │ static│
└──────────────────┴────────────────────────┴───────────────────────────┴──────┴───────┘
```

## Common Workflows

### 1. Project Health Check

```bash
# Get overall project statistics
codn analyze project

# Check for code quality issues
codn analyze unused-imports
```

### 2. Code Exploration

```bash
# Find where a function is used
codn analyze find-refs my_function

# List all functions in the project
codn analyze functions --signatures
```

### 3. Refactoring Assistance

```bash
# Before renaming a function, see where it's used
codn analyze find-refs old_function_name

# Clean up unused imports
codn analyze unused-imports
```

### 4. Code Review

```bash
# Analyze changes in a specific directory
codn analyze project src/ --verbose

# Check for unused imports in new code
codn analyze unused-imports src/
```

## Configuration

Currently, `codn` uses sensible defaults and doesn't require configuration files. Future versions may support configuration through:

- `codn.toml` - Project-specific settings
- `~/.codn/config.toml` - Global user settings

## Tips and Best Practices

### Performance Tips

- Use specific paths instead of analyzing entire large repositories
- Exclude test directories when focusing on production code
- Use `--verbose` only when you need detailed information

### Integration with Other Tools

```bash
# Combine with git for analyzing recent changes
git diff --name-only HEAD~1 | grep '\.py$' | xargs -I {} codn analyze functions {}

# Use with find for specific file patterns
find . -name "*.py" -path "*/api/*" | xargs codn analyze unused-imports
```

### Scripting

```bash
#!/bin/bash
# Simple code quality check script

echo "=== Project Analysis ==="
codn analyze project

echo -e "\n=== Unused Imports ==="
codn analyze unused-imports

echo -e "\n=== Functions Overview ==="
codn analyze functions | head -20
```

## Troubleshooting

### Common Issues

**"No Python files found"**
- Check that you're in the correct directory
- Ensure the path contains `.py` files
- Check if files are being ignored by `.gitignore`

**"Permission denied" errors**
- Ensure you have read permissions for the target directory
- Some system directories may be protected

**Slow performance on large codebases**
- Use specific subdirectories instead of analyzing the entire repository
- Exclude large generated or vendor directories

### Getting Help

```bash
# General help
codn --help

# Command-specific help
codn analyze --help
codn analyze project --help
```

## Examples

See the [examples directory](../examples/) for complete code examples and use cases.