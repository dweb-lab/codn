# Makefile for codn project
# Provides convenient commands for testing, linting, and development

.PHONY: help test test-unit test-integration test-slow test-cov test-html test-watch clean lint format install dev-install check all

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
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code"
	@echo "  check          - Run all checks (lint + test)"
	@echo ""
	@echo "🚀 Quick Commands:"
	@echo "  run            - Run codn command (uv run codn)"
	@echo "  demo           - Run codn on current project"
	@echo "  clean          - Clean build artifacts"
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

# Development commands
lint:
	@echo "Running ruff..."
	uv run ruff check .
	@echo "Running mypy..."
	uv run mypy codn
	@echo "Linting complete!"

format:
	@echo "Formatting with black..."
	uv run black .
	@echo "Sorting imports with ruff..."
	uv run ruff check --fix --select I .
	@echo "Formatting complete!"

check: lint test

# Setup and installation commands
setup-help:
	@echo "🔍 Checking your environment..."
	@python3 install.py

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
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf reports/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean complete!"

clean-all: clean
	rm -rf .venv/
	rm -rf .ruff_cache/

# Continuous Integration commands
ci-test:
	uv run pytest --cov=codn --cov-report=xml --cov-report=term-missing --junitxml=reports/junit.xml

ci-lint:
	uv run ruff check . --output-format=github
	uv run mypy codn --junit-xml reports/mypy.xml

# Quick run commands
run:
	@command -v uv >/dev/null 2>&1 && uv run codn $(ARGS) || codn $(ARGS)

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

pre-commit: format lint test-fast
	@echo "✅ Pre-commit checks passed!"

first-time-setup:
	@echo "🚀 First-time setup for codn development"
	@echo "========================================"
	@python3 install.py
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
all: format lint test
	@echo "🎉 All checks passed!"

quick: format lint test-fast
	@echo "⚡ Quick checks passed!"

# Environment info
env-info:
	@echo "🔍 Environment Information"
	@echo "========================="
	@echo "Python: $(shell python3 --version)"
	@echo "uv: $(shell command -v uv >/dev/null 2>&1 && uv --version || echo 'Not installed')"
	@echo "pip: $(shell command -v pip >/dev/null 2>&1 && pip --version || echo 'Not installed')"
	@echo "Virtual env: $(shell python3 -c 'import sys; print("Yes" if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix) else "No")')"
	@echo "Project root: $(shell pwd)"

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
