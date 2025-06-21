# 🪝 Git Hooks Guide for Codn

This guide explains how to set up and use Git hooks to maintain code quality in the codn project.

## 🎯 Overview

Git hooks are scripts that run automatically at certain points in the Git workflow. They help ensure code quality by running checks before commits and pushes.

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
python scripts/setup-hooks.py

# Choose option 5 for complete setup
```

### Option 2: Using Makefile

```bash
# Install pre-commit framework
make install-hooks

# Or setup simple hooks
make setup-hooks
```

### Option 3: Manual Setup

```bash
# Install pre-commit
uv tool install pre-commit  # or pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

## 🔧 Available Hook Types

### 1. Pre-commit Hooks (Recommended)

**What it does:**
- Runs ruff linting and formatting
- Runs mypy type checking
- Runs basic tests
- Checks file formats (JSON, YAML, TOML)
- Validates Python syntax

**Setup:**
```bash
# Install pre-commit framework
uv tool install pre-commit
pre-commit install

# Test the hooks
pre-commit run --all-files
```

### 2. Simple Hooks (Lightweight)

**What it does:**
- Basic ruff checks
- Format validation
- Quick unit tests

**Setup:**
```bash
python scripts/setup-hooks.py
# Choose option 2
```

### 3. Commit Message Validation

**What it does:**
- Enforces conventional commit format
- Validates commit message structure

**Format required:**
```
<type>[optional scope]: <description>

Examples:
feat: add new analysis command
fix(cli): resolve import error
docs: update installation guide
```

## 📋 Supported Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add unused imports detection` |
| `fix` | Bug fix | `fix(parser): handle empty files` |
| `docs` | Documentation | `docs: update API reference` |
| `style` | Code style changes | `style: format with ruff` |
| `refactor` | Code refactoring | `refactor: simplify AST parsing` |
| `test` | Add/update tests | `test: add unit tests for CLI` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `ci` | CI/CD changes | `ci: add GitHub Actions workflow` |
| `perf` | Performance improvements | `perf: optimize file scanning` |
| `build` | Build system changes | `build: update pyproject.toml` |
| `revert` | Revert changes | `revert: undo feature X` |

## 🔍 Hook Configuration

### Pre-commit Configuration (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff           # Linting
      - id: ruff-format    # Formatting

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-ast
```

### Ruff Configuration (`ruff.toml`)

Key settings:
- Line length: 88 characters
- Target Python version: 3.8+
- Comprehensive rule set
- Project-specific ignores

## 💻 Development Workflow

### 1. Make Changes
```bash
# Edit your code
vim codn/cli.py

# Add files
git add .
```

### 2. Commit (Hooks Run Automatically)
```bash
git commit -m "feat: add new command"
```

**What happens:**
1. Pre-commit hooks run
2. Code is checked and formatted
3. Tests are executed
4. Commit message is validated
5. Commit proceeds if all checks pass

### 3. If Hooks Fail
```bash
# Fix the reported issues
ruff check . --fix
ruff format .

# Stage the fixes
git add .

# Commit again
git commit -m "feat: add new command"
```

## ⚡ Quick Commands

### Manual Checks
```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff

# Run linting only
make lint

# Run formatting
make format

# Run full quality pipeline
make quality
```

### Testing Hooks
```bash
# Test hooks without committing
make test-hooks

# Simulate pre-commit checks
make pre-commit-check
```

### Bypass Hooks (Emergency Only)
```bash
# Skip all hooks (use sparingly!)
git commit --no-verify -m "emergency fix"

# Skip specific hook
SKIP=ruff git commit -m "skip ruff for this commit"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Hook Installation Failed
```bash
# Check if pre-commit is installed
pre-commit --version

# Reinstall if needed
uv tool install pre-commit --force
pre-commit install
```

#### 2. Ruff Not Found
```bash
# Install ruff
uv tool install ruff

# Or install in project
uv add ruff --dev
```

#### 3. Hooks Too Slow
```bash
# Skip slow hooks in development
SKIP=mypy,bandit git commit -m "quick fix"

# Or use simple hooks instead
python scripts/setup-hooks.py  # Choose option 2
```

#### 4. Format Conflicts
```bash
# Auto-fix formatting issues
ruff format .
git add .
git commit -m "style: fix formatting"
```

### Debug Mode

```bash
# Verbose output
pre-commit run --all-files --verbose

# Show diff for failed hooks
pre-commit run --show-diff-on-failure

# Run specific file
pre-commit run --files codn/cli.py
```

## 🏗️ GitHub Actions Integration

The project includes GitHub Actions that run the same checks:

```yaml
# .github/workflows/code-quality.yml
- name: Run ruff linting
  run: uv run ruff check . --output-format=github

- name: Run pre-commit
  run: pre-commit run --all-files
```

This ensures consistent quality checks locally and in CI.

## 📊 Best Practices

### ✅ Do's
- ✅ Run `make check` before major commits
- ✅ Fix formatting issues automatically with `ruff format .`
- ✅ Use conventional commit messages
- ✅ Test hooks on existing code: `pre-commit run --all-files`
- ✅ Keep hooks fast (< 30 seconds)

### ❌ Don'ts
- ❌ Don't bypass hooks regularly (`--no-verify`)
- ❌ Don't commit broken code
- ❌ Don't ignore hook failures
- ❌ Don't commit large files without review
- ❌ Don't use vague commit messages

## 🔄 Updating Hooks

### Update Pre-commit Hooks
```bash
# Update to latest versions
pre-commit autoupdate

# Update specific hook
pre-commit autoupdate --repo https://github.com/astral-sh/ruff-pre-commit
```

### Update Ruff Configuration
```bash
# Edit ruff.toml to adjust rules
vim ruff.toml

# Test new configuration
ruff check .
```

## 📈 Monitoring Code Quality

### Metrics to Track
- Pre-commit hook success rate
- Average hook execution time
- Number of auto-fixed issues
- Commit message compliance

### Tools
- GitHub Actions provide CI metrics
- Pre-commit generates local reports
- Ruff provides detailed linting reports

## 🆘 Getting Help

### Resources
- [Pre-commit Documentation](https://pre-commit.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Conventional Commits](https://www.conventionalcommits.org/)

### Commands
```bash
# Get help
pre-commit --help
ruff --help
make help

# Run diagnostics
make env-info

# Check hook status
ls -la .git/hooks/
```

### Support
- 🐛 [Report Issues](https://github.com/dweb-lab/codn/issues)
- 💬 [Discussions](https://github.com/dweb-lab/codn/discussions)
- 📖 [Documentation](https://github.com/dweb-lab/codn/tree/main/docs)

---

**Remember:** Hooks are there to help maintain code quality. Embrace them as part of your development workflow! 🚀
