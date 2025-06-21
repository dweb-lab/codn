# Development Quick Reference

Essential commands for developing codn.

## 🚀 Quick Start

```bash
# Setup development environment
git clone https://github.com/dweb-lab/codn.git
cd codn
uv sync  # or pip install -e .

# Install pre-commit hooks
make install-hooks
```

## 🔧 Common Commands

### Code Quality
```bash
# Quick pre-commit check (recommended)
make pre-commit-fast

# Comprehensive check before push
./check-ruff.sh

# Manual formatting
ruff format .
ruff check . --fix
```

### Testing
```bash
# Run all tests
make test

# Run specific test
pytest tests/test_specific.py

# Test with coverage
make test-coverage
```

### Development Workflow
```bash
# Before committing
make pre-commit-fast

# Before pushing
make test && ./check-ruff.sh

# Check everything
make lint test
```

## 📚 Documentation

- **[Complete Documentation](docs/)** - Full developer guides
- **[Recent Improvements](docs/RECENT_IMPROVEMENTS.md)** - Latest features
- **[Ruff Setup](docs/development/ruff-setup.md)** - Linting guide

## 🛠️ Make Targets

```bash
make help           # Show all available targets
make test           # Run tests
make lint           # Run all linting
make install-hooks  # Install pre-commit hooks
make clean          # Clean build artifacts
```

## 🐛 Troubleshooting

**Import errors**: Check that you're in the virtual environment
**Ruff failures**: Run `ruff check . --fix` to auto-fix issues
**Test failures**: Check that all dependencies are installed

---

For detailed documentation, see the [docs/](docs/) directory.
