#!/usr/bin/env python3
"""
Git Hooks Setup Script for Codn

This script sets up git hooks to ensure code quality before commits.
It provides multiple options for different development workflows.
"""

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Optional


def setup_proxy_env() -> dict:
    """Setup proxy environment variables for better GitHub access."""
    proxy_env = os.environ.copy()

    # Check if proxy is needed (China or slow connections)
    print_colored("🌐 Checking network connectivity...", "blue")

    # Test GitHub connectivity
    test_success, _, _ = run_command_simple(
        "curl -s --connect-timeout 5 https://api.github.com/zen"
    )

    if not test_success:
        print_colored("🚧 GitHub access seems slow, setting up proxy...", "yellow")

        # Set proxy environment variables
        proxy_settings = {
            "https_proxy": "http://127.0.0.1:7890",
            "http_proxy": "http://127.0.0.1:7890",
            "all_proxy": "socks5://127.0.0.1:7890",
        }

        proxy_env.update(proxy_settings)
        print_colored("✅ Proxy configured for faster GitHub access", "green")
    else:
        print_colored("✅ Direct GitHub access is working fine", "green")

    return proxy_env


def run_command_simple(cmd: str) -> tuple[bool, str, str]:
    """Run a simple command without proxy for testing."""
    try:
        result = subprocess.run(
            cmd,
            check=False,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,  # nosec B602
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def run_command(
    cmd: str, capture_output: bool = True, use_proxy: bool = True
) -> tuple[bool, str, str]:
    """Run a command and return success status and output."""
    try:
        env = setup_proxy_env() if use_proxy else os.environ.copy()
        result = subprocess.run(
            cmd,
            check=False,
            shell=True,
            capture_output=capture_output,
            text=True,  # nosec B602
            cwd=get_repo_root(),
            env=env,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not in a git repository")


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(cmd) is not None


def print_colored(text: str, color: str = "") -> None:
    """Print colored text."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "end": "\033[0m",
    }

    if color in colors:
        print(f"{colors[color]}{text}{colors['end']}")
    else:
        print(text)


def setup_pre_commit() -> bool:
    """Setup pre-commit hooks."""
    print_colored("🔧 Setting up pre-commit hooks...", "blue")

    # Check if pre-commit is available
    has_uv = check_command_exists("uv")
    has_pip = check_command_exists("pip")

    if not (has_uv or has_pip):
        print_colored(
            "❌ Neither uv nor pip found. Please install a package manager first.",
            "red",
        )
        return False

    # Install pre-commit with proxy support
    print_colored("📦 Installing pre-commit (with proxy if needed)...", "blue")
    if has_uv:
        success, _, stderr = run_command("uv tool install pre-commit", use_proxy=True)
        if not success:
            # Try with uv pip
            success, _, stderr = run_command(
                "uv pip install pre-commit", use_proxy=True
            )
    else:
        success, _, stderr = run_command("pip install pre-commit", use_proxy=True)

    if not success:
        print_colored(f"❌ Failed to install pre-commit: {stderr}", "red")
        return False

    # Install the hooks (may need to download from GitHub)
    print_colored("🔗 Installing pre-commit hooks from GitHub...", "blue")
    success, _, stderr = run_command("pre-commit install", use_proxy=True)
    if not success:
        print_colored(f"❌ Failed to install pre-commit hooks: {stderr}", "red")
        return False

    # Install commit-msg hook for conventional commits
    success, _, _ = run_command(
        "pre-commit install --hook-type commit-msg", use_proxy=True
    )

    print_colored("✅ Pre-commit hooks installed successfully!", "green")
    return True


def create_simple_pre_commit_hook() -> bool:
    """Create a simple pre-commit hook without pre-commit framework."""
    print_colored("🔧 Creating simple pre-commit hook...", "blue")

    repo_root = get_repo_root()
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    # Create pre-commit hook script
    hook_content = """#!/bin/bash
# Simple pre-commit hook for codn
# Runs ruff checks before allowing commit

set -e

echo "🔍 Running code quality checks..."

# Check if uv is available
if command -v uv >/dev/null 2>&1; then
    PYTHON_CMD="uv run"
else
    PYTHON_CMD=""
fi

# Run ruff check
echo "📝 Running ruff lint..."
if $PYTHON_CMD ruff check .; then
    echo "✅ Ruff lint passed"
else
    echo "❌ Ruff lint failed. Please fix the issues before committing."
    echo "💡 Try: ruff check . --fix"
    exit 1
fi

# Run ruff format check
echo "🎨 Checking code formatting..."
if $PYTHON_CMD ruff format --check .; then
    echo "✅ Code formatting is correct"
else
    echo "❌ Code formatting issues found. Please format the code."
    echo "💡 Try: ruff format ."
    exit 1
fi

# Run basic tests if available
if [ -f "pyproject.toml" ] && grep -q "pytest" pyproject.toml; then
    echo "🧪 Running basic tests..."
    if $PYTHON_CMD pytest tests/unit/ -x --tb=short; then
        echo "✅ Basic tests passed"
    else
        echo "❌ Tests failed. Please fix before committing."
        exit 1
    fi
fi

echo "🎉 All checks passed! Proceeding with commit..."
"""

    hook_file = hooks_dir / "pre-commit"
    hook_file.write_text(hook_content)
    hook_file.chmod(0o755)

    print_colored("✅ Simple pre-commit hook created!", "green")
    return True


def create_commit_msg_hook() -> bool:
    """Create commit message validation hook."""
    print_colored("🔧 Creating commit message validation hook...", "blue")

    repo_root = get_repo_root()
    hooks_dir = repo_root / ".git" / "hooks"

    # Create commit-msg hook for conventional commits
    hook_content = """#!/bin/bash
# Commit message validation hook
# Ensures commit messages follow conventional commit format

commit_regex='^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|revert)(\\(.+\\))?: .{1,100}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ Invalid commit message format!"
    echo ""
    echo "📝 Commit message must follow conventional commit format:"
    echo "   <type>[optional scope]: <description>"
    echo ""
    echo "📋 Valid types:"
    echo "   feat:     A new feature"
    echo "   fix:      A bug fix"
    echo "   docs:     Documentation only changes"
    echo "   style:    Changes that do not affect the meaning of the code"
    echo "   refactor: A code change that neither fixes a bug nor adds a feature"
    echo "   test:     Adding missing tests or correcting existing tests"
    echo "   chore:    Changes to the build process or auxiliary tools"
    echo "   ci:       Changes to CI configuration files and scripts"
    echo "   perf:     A code change that improves performance"
    echo "   build:    Changes that affect the build system or external dependencies"
    echo "   revert:   Reverts a previous commit"
    echo ""
    echo "💡 Examples:"
    echo "   feat: add new analysis command"
    echo "   fix(cli): resolve import error"
    echo "   docs: update installation guide"
    echo ""
    exit 1
fi
"""

    hook_file = hooks_dir / "commit-msg"
    hook_file.write_text(hook_content)
    hook_file.chmod(0o755)

    print_colored("✅ Commit message validation hook created!", "green")
    return True


def setup_github_actions() -> bool:
    """Setup GitHub Actions for CI/CD."""
    print_colored("🔧 Setting up GitHub Actions...", "blue")

    repo_root = get_repo_root()
    workflows_dir = repo_root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Create code quality workflow
    workflow_content = """name: Code Quality

on:
  push:
    branches: [ main, develop, study ]
  pull_request:
    branches: [ main, develop ]

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"

    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}

    - name: Install dependencies
      run: uv sync --all-extras --dev

    - name: Run ruff linting
      run: uv run ruff check .

    - name: Run ruff formatting check
      run: uv run ruff format --check .

    - name: Run mypy type checking
      run: uv run mypy codn --ignore-missing-imports

    - name: Run tests
      run: uv run pytest tests/ --cov=codn --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
"""

    workflow_file = workflows_dir / "quality.yml"
    workflow_file.write_text(workflow_content)

    print_colored("✅ GitHub Actions workflow created!", "green")
    return True


def show_usage_examples() -> None:
    """Show usage examples and best practices."""
    print_colored("\n📚 Usage Examples and Best Practices", "cyan")
    print_colored("=" * 50, "cyan")

    print("\n🔧 Development Workflow:")
    print("1. Make your changes")
    print("2. Run manual checks: make check")
    print("3. Commit: git commit -m 'feat: add new feature'")
    print("4. Hooks run automatically ✨")

    print("\n⚡ Quick Commands:")
    print("• ruff check . --fix          # Auto-fix linting issues")
    print("• ruff format .               # Format code")
    print("• uv run pytest              # Run tests")
    print("• make check                  # Run all checks")

    print("\n🚨 If hooks fail:")
    print("• Fix the reported issues")
    print("• Stage the fixes: git add .")
    print("• Commit again: git commit")

    print("\n🔄 Bypass hooks (emergency only):")
    print("• git commit --no-verify")
    print("• Use sparingly and fix issues later!")

    print("\n📝 Commit Message Examples:")
    print("• feat: add new analysis command")
    print("• fix(cli): resolve import error")
    print("• docs: update installation guide")
    print("• refactor: simplify command structure")
    print("• test: add unit tests for analyzer")


def main() -> None:
    """Main setup function."""
    print_colored("🚀 Codn Git Hooks Setup", "bold")
    print_colored("=" * 30, "cyan")

    try:
        repo_root = get_repo_root()
        print(f"📁 Repository: {repo_root}")
    except RuntimeError as e:
        print_colored(f"❌ {e}", "red")
        sys.exit(1)

    # Check network and setup proxy if needed
    print_colored("\n🌐 Network Setup", "cyan")
    proxy_env = setup_proxy_env()

    print("\n📋 Available setup options:")
    print("1. 🔧 Full setup with pre-commit framework (recommended)")
    print("2. ⚡ Simple hooks (lightweight)")
    print("3. 📝 Commit message validation only")
    print("4. 🏗️  GitHub Actions setup")
    print("5. 🎯 All of the above")

    try:
        choice = input("\n👉 Choose an option (1-5): ").strip()
    except (EOFError, KeyboardInterrupt):
        print_colored("\n❌ Setup cancelled by user.", "yellow")
        sys.exit(0)

    success = True

    if choice == "1":
        success &= setup_pre_commit()
    elif choice == "2":
        success &= create_simple_pre_commit_hook()
        success &= create_commit_msg_hook()
    elif choice == "3":
        success &= create_commit_msg_hook()
    elif choice == "4":
        success &= setup_github_actions()
    elif choice == "5":
        print_colored("\n🎯 Setting up complete code quality pipeline...", "bold")
        success &= setup_pre_commit()
        success &= create_commit_msg_hook()
        success &= setup_github_actions()
    else:
        print_colored("❌ Invalid choice. Please run the script again.", "red")
        sys.exit(1)

    if success:
        print_colored("\n🎉 Setup completed successfully!", "green")
        show_usage_examples()

        print_colored("\n💡 Next steps:", "yellow")
        print("• Test the hooks: make a small change and commit")
        print("• Check .pre-commit-config.yaml for configuration")
        print("• Run 'pre-commit run --all-files' to check existing code")

        if "https_proxy" in proxy_env:
            print_colored("\n🌐 Network Note:", "cyan")
            print("• Proxy was configured for GitHub access")
            print("• If you have network issues, the proxy settings are:")
            print("  export https_proxy=http://127.0.0.1:7890")
            print("  export http_proxy=http://127.0.0.1:7890")
            print("  export all_proxy=socks5://127.0.0.1:7890")
    else:
        print_colored("\n❌ Setup failed. Please check the errors above.", "red")
        print_colored(
            "💡 If you're in China or having GitHub connectivity issues, try:", "yellow"
        )
        print("export https_proxy=http://127.0.0.1:7890")
        print("export http_proxy=http://127.0.0.1:7890")
        print("export all_proxy=socks5://127.0.0.1:7890")
        print("Then run this script again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
