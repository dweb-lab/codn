# Makefile for codn project
# Provides convenient commands for testing, linting, and development

.PHONY: help test test-unit test-integration test-slow test-cov test-html test-watch clean clean-all lint format install dev-install check all bandit

# Default target
help:
	@echo "🔍 Codn Development Commands"
	@echo "================================"
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  setup-help     - Show installation helper (detects uv/pip)"
	@echo "  install        - Install with uv (recommended)"
	@echo "  install-pip    - Install with pip (fallback)"
	@echo "  dev-install    - Install with dev dependencies"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  test-html      - Generate HTML coverage report"
	@echo "  test-watch     - Run tests in watch mode"
	@echo ""
	@echo "🔧 Code Quality:"
	@echo "  lint           - Run basic linting (ruff + mypy)"
	@echo "  lint-all       - Run all linting checks (ruff lint/format + mypy)"
	@echo "  ruff-check     - Run comprehensive ruff checks (lint + format)"
	@echo "  ruff-lint      - Run ruff linting only"
	@echo "  mypy-check     - Run mypy type checking only"
	@echo "  format         - Format code"
	@echo "  check          - Run all checks (lint + test)"
	@echo "  quality        - Run full quality pipeline"
	@echo "  pre-commit-fast - Fast ruff checks (no network)"
	@echo "  test-hooks-fast - Test hooks using local ruff"
	@echo ""
	@echo "🪝 Git Hooks:"
	@echo "  setup-hooks    - Setup git hooks for code quality"
	@echo "  install-hooks  - Install pre-commit framework (with proxy)"
	@echo "  install-hooks-direct - Install pre-commit framework (direct)"
	@echo "  test-hooks     - Test git hooks manually"
	@echo "  update-hooks   - Update pre-commit hooks"
	@echo ""
	@echo "🌐 Network & Proxy:"
	@echo "  setup-proxy    - Setup proxy for faster GitHub access"
	@echo "  test-network   - Test GitHub connectivity"
	@echo "  proxy-help     - Show proxy configuration help"
	@echo ""
	@echo "🚀 Quick Commands:"
	@echo "  run            - Run codn command (uv run codn)"
	@echo "  demo           - Run codn on current project"
	@echo "  clean          - Clean build artifacts and cache files"
	@echo "  clean-all      - Deep clean (including .venv)"
	@echo "  all            - Format, lint, and test"

# Test commands
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -v

test-integration:
	uv run pytest tests/integration -v -m integration

test-slow:
	uv run pytest -m slow -v

test-cov:
	uv run pytest --cov=codn --cov-report=term-missing

test-html:
	uv run pytest --cov=codn --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	uv run pytest --maxfail=1 --disable-warnings -q --tb=short --looponfail

test-parallel:
	uv run pytest -n auto

test-fast:
	uv run pytest -m "not slow" --maxfail=5 -q

test-debug:
	uv run pytest -v -s --tb=long --no-cov

# Specific test categories
test-network:
	uv run pytest -m network -v

test-no-network:
	uv run pytest -m "not network" -v

# Network connectivity test
github-connectivity-test:
	@echo "🔍 Testing GitHub connectivity..."
	@if curl -s --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then \
		echo "✅ Direct GitHub access works"; \
	else \
		echo "❌ GitHub access failed"; \
		echo "💡 Try: make setup-proxy"; \
	fi

# Development commands
# Code Quality
# Individual linting components
ruff-lint:
	@echo "📝 Running ruff lint..."
	@if command -v uv >/dev/null 2>&1; then \
		if uv run ruff check . --quiet; then \
			echo "✅ Ruff lint passed"; \
		else \
			echo "❌ Ruff lint failed"; \
			echo "💡 To see detailed errors, run: ruff check ."; \
			echo "💡 To auto-fix some issues, run: ruff check . --fix"; \
			exit 1; \
		fi; \
	else \
		if ruff check . --quiet; then \
			echo "✅ Ruff lint passed"; \
		else \
			echo "❌ Ruff lint failed"; \
			echo "💡 To see detailed errors, run: ruff check ."; \
			echo "💡 To auto-fix some issues, run: ruff check . --fix"; \
			exit 1; \
		fi; \
	fi

ruff-format-check:
	@echo "🎨 Checking ruff format..."
	@if command -v uv >/dev/null 2>&1; then \
		if uv run ruff format . --check --quiet; then \
			echo "✅ Ruff format check passed"; \
		else \
			echo "❌ Code needs formatting"; \
			echo "💡 To format the code, run: ruff format ."; \
			exit 1; \
		fi; \
	else \
		if ruff format . --check --quiet; then \
			echo "✅ Ruff format check passed"; \
		else \
			echo "❌ Code needs formatting"; \
			echo "💡 To format the code, run: ruff format ."; \
			exit 1; \
		fi; \
	fi

mypy-check:
	@echo "🔍 Running mypy type checking..."
	@command -v uv >/dev/null 2>&1 && uv run mypy . || mypy .
	@echo "✅ Type checking complete!"


bandit:
	@echo "🛡️ Running Bandit security checks..."
	@bandit -r . -x ./tests,__pycache__,venv
	@echo "✅ Bandit check complete!"

# Composite linting targets
ruff-check: ruff-lint ruff-format-check
	@echo "🎉 All ruff checks passed! Ready to commit."

lint: ruff-lint mypy-check bandit
	@echo "✅ Linting complete!"

lint-all: ruff-lint ruff-format-check mypy-check bandit
	@echo "🎉 All linting checks passed!"

# Fast pre-commit checks (using local ruff, no network required)
pre-commit-fast:
	@echo "🚀 Running fast pre-commit checks..."
	@echo "📝 Running ruff lint..."
	@command -v uv >/dev/null 2>&1 && uv run ruff check codn/ --fix || ruff check codn/ --fix
	@echo "🎨 Running ruff format..."
	@command -v uv >/dev/null 2>&1 && uv run ruff format codn/ || ruff format codn/
	@echo "✅ Fast pre-commit checks complete!"

format:
	@echo "Formatting code with ruff..."
	@command -v uv >/dev/null 2>&1 && uv run ruff format . || ruff format .
	@echo "Auto-fixing linting issues..."
	@command -v uv >/dev/null 2>&1 && uv run ruff check . --fix || ruff check . --fix
	@echo "✅ Formatting complete!"

format-check:
	@echo "Checking code formatting..."
	@command -v uv >/dev/null 2>&1 && uv run ruff format --check . || ruff format --check .

quality: format lint-all test-fast
	@echo "🎉 Full quality pipeline passed!"

check: lint-all test

# Setup and installation commands
setup-help:
	@echo "🔍 Checking your environment..."
	@python3 scripts/install.py

# Git hooks setup
setup-hooks:
	@echo "🪝 Setting up git hooks for code quality..."
	@python3 scripts/setup-hooks.py

install-hooks:
	@echo "📦 Installing pre-commit framework..."
	@echo "🌐 Using proxy for faster GitHub access (if needed)..."
	@export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890; \
	 command -v uv >/dev/null 2>&1 && uv tool install pre-commit || pip install pre-commit
	@export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890; \
	 pre-commit install
	@export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890; \
	 pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed!"

install-hooks-direct:
	@echo "📦 Installing pre-commit framework (direct connection)..."
	@command -v uv >/dev/null 2>&1 && uv tool install pre-commit || pip install pre-commit
	@pre-commit install
	@pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed!"

test-hooks:
	@echo "🧪 Testing git hooks manually..."
	@export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890; \
	 command -v pre-commit >/dev/null 2>&1 && pre-commit run --all-files || echo "Pre-commit not installed. Use 'make install-hooks' first."

update-hooks:
	@echo "🔄 Updating pre-commit hooks..."
	@export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890; \
	 pre-commit autoupdate

# Network and proxy setup
setup-proxy:
	@echo "🌐 Setting up proxy for faster GitHub access..."
	@bash scripts/setup-proxy.sh

test-network: github-connectivity-test

proxy-help:
	@echo "🌐 Proxy Configuration Help"
	@echo "=========================="
	@echo ""
	@echo "For users in China or with slow GitHub access:"
	@echo ""
	@echo "🔧 Quick setup:"
	@echo "  export https_proxy=http://127.0.0.1:7890"
	@echo "  export http_proxy=http://127.0.0.1:7890"
	@echo "  export all_proxy=socks5://127.0.0.1:7890"
	@echo ""
	@echo "🛠️  Automated setup:"
	@echo "  make setup-proxy"
	@echo ""
	@echo "📦 With proxy commands:"
	@echo "  make install-hooks     (uses proxy automatically)"
	@echo "  make test-hooks        (uses proxy automatically)"
	@echo "  make update-hooks      (uses proxy automatically)"
	@echo ""
	@echo "🚫 Direct commands (without proxy):"
	@echo "  make install-hooks-direct"

install:
	@echo "📦 Installing with uv (recommended)..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Run 'make setup-help' for installation options."; exit 1; }
	uv sync
	@echo "✅ Installation complete! Try: make run"

install-pip:
	@echo "📦 Installing with pip..."
	pip install -e .
	@echo "✅ Installation complete! Try: codn --help"

dev-install:
	@echo "📦 Installing development environment..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Installing with pip..."; pip install -e .; exit 0; }
	uv sync --group dev
	@echo "✅ Development environment ready!"

test-install:
	@command -v uv >/dev/null 2>&1 && uv sync --group test || pip install -e .[test]

# Clean commands
clean:
	@echo "🧹 Cleaning project artifacts..."
	@rm -rf build/ dist/ *.egg-info/
	@rm -rf .pytest_cache/ .coverage* htmlcov/
	@rm -rf .mypy_cache/ .ruff_cache/
	@find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./.venv/*" -delete 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✅ Clean complete!"



clean-all: clean
	@echo "🔥 Deep cleaning (including virtual environment)..."
	@rm -rf .venv/
	@echo "✅ Deep clean complete!"

# Continuous Integration commands
ci-test:
	uv run pytest --cov=codn --cov-report=xml --cov-report=term-missing --junitxml=reports/junit.xml

ci-lint:
	uv run ruff check . --output-format=github
	uv run mypy codn --junit-xml reports/mypy.xml

# Quick run commands
run:
	@command -v uv >/dev/null 2>&1 && uv run codn $(ARGS) || codn $(ARGS)

# Test pre-commit hooks (using local installation, fast)
test-hooks-fast:
	@echo "🧪 Testing git hooks (fast, using local ruff)..."
	@make pre-commit-fast
	@echo "✅ Fast hooks test complete!"

demo:
	@echo "🔍 Running codn analysis on current project..."
	@command -v uv >/dev/null 2>&1 && uv run codn || codn

demo-unused:
	@echo "🧹 Checking for unused imports..."
	@command -v uv >/dev/null 2>&1 && uv run codn unused || codn unused

demo-funcs:
	@echo "📝 Listing functions..."
	@command -v uv >/dev/null 2>&1 && uv run codn funcs || codn funcs

# Development workflow
dev-setup: dev-install
	@echo "✅ Development environment setup complete!"
	@echo "Try: make demo"

pre-commit: format lint-all test-fast
	@echo "✅ Pre-commit checks passed!"

first-time-setup:
	@echo "🚀 First-time setup for codn development"
	@echo "========================================"
	@python3 scripts/install.py
	@echo ""
	@echo "Choose your setup method:"
	@echo "1. make install     (with uv - recommended)"
	@echo "2. make install-pip (with pip - fallback)"

# Build commands
build:
	uv build

build-wheel:
	uv build --wheel

# Documentation commands (if you add docs later)
docs:
	@echo "Documentation not yet implemented"

# Release commands (if you need them)
release-test:
	uv build
	uv run twine check dist/*

# All-in-one commands
all: format lint-all test
	@echo "🎉 All checks passed!"

quick: format lint test-fast
	@echo "⚡ Quick checks passed!"

# Pre-commit simulation (full)
pre-commit-check: format-check lint-all test-fast
	@echo "🪝 Pre-commit checks simulation passed!"

# Pre-commit simulation (fast, ruff only)
pre-commit-ruff-only: pre-commit-fast
	@echo "🪝 Fast ruff-only pre-commit checks passed!"

# Environment info
env-info:
	@echo "🔍 Environment Information"
	@echo "========================="
	@echo "Python: $(shell python3 --version)"
	@echo "uv: $(shell command -v uv >/dev/null 2>&1 && uv --version || echo 'Not installed')"
	@echo "pip: $(shell command -v pip >/dev/null 2>&1 && pip --version || echo 'Not installed')"
	@echo "ruff: $(shell command -v ruff >/dev/null 2>&1 && ruff --version || echo 'Not installed')"
	@echo "pre-commit: $(shell command -v pre-commit >/dev/null 2>&1 && pre-commit --version || echo 'Not installed')"
	@echo "Virtual env: $(shell python3 -c 'import sys; print("Yes" if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix) else "No")')"
	@echo "Project root: $(shell pwd)"
	@echo "Git hooks: $(shell [ -f .git/hooks/pre-commit ] && echo 'Installed' || echo 'Not installed')"

# Docker commands (if you use Docker)
docker-test:
	docker run --rm -v $(PWD):/app -w /app python:3.11 make dev-install test

# Profile tests (for performance analysis)
test-profile:
	uv run pytest --profile

# Coverage with different formats
coverage-xml:
	uv run pytest --cov=codn --cov-report=xml

coverage-json:
	uv run pytest --cov=codn --cov-report=json

# Security checks (if you add security tools)
security:
	@echo "Security checks not yet implemented"
	# pip-audit or safety can be added here

# Performance tests
test-perf:
	uv run pytest tests/ -k "perf" -v

# Verbose output for debugging
verbose-test:
	uv run pytest -vvv --tb=long --capture=no

# Test specific file
test-file:
	@read -p "Enter test file path: " file; \
	uv run pytest $$file -v

# Show test configuration
show-config:
	uv run pytest --collect-only -q

# List all tests
list-tests:
	uv run pytest --collect-only

# Run tests with specific marker
test-marker:
	@read -p "Enter marker name: " marker; \
	uv run pytest -m $$marker -v
