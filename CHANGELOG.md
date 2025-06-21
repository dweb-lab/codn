# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2024-12-19

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

## [0.1.0] - 2024-12-19

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

[Unreleased]: https://github.com/dweb-lab/codn/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/dweb-lab/codn/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dweb-lab/codn/releases/tag/v0.1.0