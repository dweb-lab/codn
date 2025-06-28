# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## [0.1.6] - 2025-06-28

### 🔧 Chores
- bump version to 0.1.6.dev0 and add asttokens dependency
- prepare and document changes for v0.1.5

### 🔨 Refactoring
- improve C reference analysis and update script structure
- update imports to reflect LSP client refactor
- restructure and enhance reference analysis
- improve reference extraction and timeout handling



## [0.1.5] - 2025-06-27

### Added
- **LSP Enhancements**:
  - Added `get_funcs_for_lines` for improved function extraction by line ranges
  - Introduced stream and batch request helpers to improve LSP file state tracking
- **Multi-language Parsing**:
  - Enhanced multi-language parser runner with improved logging, testing, and call graph generation
- **Benchmarking**:
  - Added benchmarking tests for key functions: `get_called`, `get_refs_clean`, and `get_refs`

### Changed
- Refactored LSP client code with better cleanup, logging, and timeout handling
- Improved language detection and multi-pattern file matching in `os_utils`

### Fixed
- Hardened subprocess usage in installation scripts to comply with Bandit security checks
- Removed unused imports and commented out flaky timeout test to stabilize test suite

### Chore
- Refined Bandit configuration in Makefile to exclude test and cache directories
- Reflowed and reformatted documentation docstrings for better readability
- Prepared release for version 0.1.5

## [0.1.4] - 2025-06-24

### Added
- **Multi-language parsing support**:
  - Added `run_multilang_parse.py` to test snippet and reference extraction across languages
  - Added `run_codn_graph.py` and `run_watch.py` scripts for graph-based analysis and file watching
- **CLI Enhancements**:
  - Introduced `codn tools` CLI for code snippet search and dependency exploration
  - Added `lsp` command group for code understanding via Language Server Protocol
- **LSP Improvements**:
  - Enhanced LSP client to support snippet extraction by pattern, line number, or symbol
  - Added support for identifying language types and grouping files by primary language
  - Introduced `SYMBOL_KIND_MAP` and `kind_to_str` for better symbol kind interpretation

### Changed
- **Refactoring**:
  - Unified LSP client implementation under `BaseLSPClient` and enhanced logging
  - Replaced `list_all_python_files_sync` with a more flexible `list_all_files_sync`
  - Generalized and simplified Pyright client logic for better multi-language support
  - Updated tests to align with the generalized `BaseLSPClient`

- **Developer Experience**:
  - Wrapped and reformatted long docstrings across CLI, scripts, and tests
  - Improved typing with `TypedDict` for function signatures in `simple_ast.py`

### Fixed
- Resolved Pyright attribute access issues in `simple_ast.py`
- Ensured `asttokens` is always imported and initialized correctly

### Security
- Integrated Bandit security checks into the Makefile

### Chore
- Updated pre-commit configuration:
  - Excluded `tests/` from Bandit scans
  - Removed redundant or unnecessary configuration options
  - Merged local hooks to avoid duplicate runs

## [0.1.3] - 2025-06-22

### Changed
- **Project Structure Refactoring**:
  - Moved `install.py` to `scripts/` directory for better organization
  - Reorganized documentation structure with dedicated `docs/` directory
  - Simplified development documentation and moved to `docs/development`
  - Restructured Makefile linting targets for better clarity

- **Code Quality Improvements**:
  - Comprehensive code formatting with ruff
  - Removed overly complex `ruff.toml` configuration
  - Fixed import sorting and linting issues throughout codebase
  - Enhanced pre-commit hooks for faster ruff execution
  - Optimized pre-commit configuration to use local tools

- **Build and Development Tools**:
  - Added pip wrapper to use `uv pip` instead of system pip
  - Updated `uv.lock` with pre-commit dependencies
  - Improved package manager support and configuration
  - Enhanced clean commands with detailed documentation

### Removed
- Removed redundant and unused files:
  - `run_tests.py` script (functionality moved to Makefile)
  - `quickstart.sh` script (superseded by better tooling)
  - `.package-manager`, `scripts/setup-hooks.py`, `scripts/setup-proxy.sh`
  - Simplified and relocated `check-ruff.sh`

### Fixed
- Fixed script paths in `install-dev-tools.sh`
- Corrected function calls to use keyword arguments after ruff fixes
- Resolved all ruff linting issues for consistent code quality
- Fixed 'codn analyze' missing command errors with user-friendly guidance

### Added
- Comprehensive Git hooks and code quality assurance system
- Friendly welcome interface for CLI commands
- Better user guidance and error messages

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

[Unreleased]: https://github.com/dweb-lab/codn/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/dweb-lab/codn/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/dweb-lab/codn/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/dweb-lab/codn/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/dweb-lab/codn/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/dweb-lab/codn/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/dweb-lab/codn/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dweb-lab/codn/releases/tag/v0.1.0
