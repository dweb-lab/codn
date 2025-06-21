# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2025-06-21

### Added
- **New AST Analysis Functions**:
  - `find_function_references()` - Find all references to a function in source code
  - `extract_function_signatures()` - Extract detailed function signature information
  - `find_unused_imports()` - Detect unused import statements
  - `extract_class_methods()` - Extract methods from classes with detailed metadata

- **Enhanced CLI Commands**:
  - `codn analyze project` - Comprehensive project analysis with statistics
  - `codn analyze find-refs <function_name>` - Find function references across project
  - `codn analyze unused-imports` - Find and report unused imports
  - `codn analyze functions` - Analyze functions and methods with signature details

- **Rich UI Support**:
  - Added rich library for beautiful terminal output
  - Progress bars for long-running operations
  - Colorized tables and formatted output
  - Better error display and user experience

- **Synchronous File Operations**:
  - Added `list_all_python_files_sync()` for non-async file discovery
  - Improved CLI performance with synchronous operations

### Changed
- Enhanced package imports to include all new analysis functions
- Improved error handling in CLI commands with graceful path resolution
- Better test coverage with 12+ new test cases for analysis functions

### Fixed
- Fixed path resolution issues in CLI commands
- Improved AST function signature extraction with proper default value handling
- Better handling of edge cases in reference detection

## [0.1.1] - 2025-06-21

### Fixed
- Fixed `find_enclosing_function` in `simple_ast.py` to handle cases when `end_lineno` is not available
- Added fallback strategy to estimate function end line by traversing AST nodes in function body
- Corrected test expectations in `test_parametrized_function_detection` to match actual line numbers

### Changed
- Optimized pytest configuration for more concise test output
- Changed test output format to use `-q` and `--tb=line` for cleaner display
- Reduced log verbosity during test runs

### Added
- Enhanced unit test coverage with comprehensive test cases
- Added robust AST function detection with fallback mechanisms

## [0.1.0] - 2025-06-18

### Added
- Initial release of codn library
- Core utilities for Python development:
  - `simple_ast`: AST-based code analysis tools
  - `pyright_lsp_client`: Language Server Protocol client for Pyright
  - `git_utils`: Git repository validation utilities  
  - `os_utils`: File system operations with gitignore support
- Command-line interface with `typer`
- Comprehensive test suite with pytest
- Type checking support with mypy
- Code formatting with black and ruff
- Documentation and examples

### Features
- Function detection in Python source code
- Class inheritance relationship extraction
- Git repository validation and health checks
- Python file discovery with gitignore filtering
- LSP client for static analysis integration
- Cross-platform compatibility

[Unreleased]: https://github.com/dweb-lab/codn/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/dweb-lab/codn/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/dweb-lab/codn/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dweb-lab/codn/releases/tag/v0.1.0