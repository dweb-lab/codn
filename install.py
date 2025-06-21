#!/usr/bin/env python3
"""
Codn Installation Helper

This script helps users install codn using the best available package manager.
It detects uv, pip, and provides appropriate installation commands.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=True, text=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, check=False, shell=True, capture_output=capture_output, text=text
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_uv():
    """Check if uv is available."""
    success, stdout, _ = run_command("uv --version")
    if success:
        version = stdout.strip()
        return True, version
    return False, None


def check_pip():
    """Check if pip is available."""
    success, stdout, _ = run_command("pip --version")
    if success:
        version = stdout.strip()
        return True, version
    return False, None


def is_in_virtual_env():
    """Check if we're in a virtual environment."""
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def detect_project_type():
    """Detect if we're in a codn development environment."""
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"

    if pyproject_path.exists():
        content = pyproject_path.read_text()
        if 'name = "codn"' in content:
            return "development"

    return "user"


def print_colored(text, color=""):
    """Print colored text."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "end": "\033[0m",
    }

    if color in colors:
        print(f"{colors[color]}{text}{colors['end']}")
    else:
        print(text)


def main():
    """Main installation helper."""
    print_colored("🔍 Codn Installation Helper", "bold")
    print_colored("=" * 40, "cyan")

    # Detect environment
    project_type = detect_project_type()
    in_venv = is_in_virtual_env()

    print("\n📍 Environment Detection:")
    print(f"   Project type: {project_type}")
    print(f"   Virtual environment: {'Yes' if in_venv else 'No'}")

    # Check available package managers
    uv_available, uv_version = check_uv()
    pip_available, pip_version = check_pip()

    print("\n📦 Package Managers:")
    if uv_available:
        print_colored(f"   ✅ uv: {uv_version}", "green")
    else:
        print_colored("   ❌ uv: Not available", "red")

    if pip_available:
        print_colored(f"   ✅ pip: {pip_version}", "green")
    else:
        print_colored("   ❌ pip: Not available", "red")

    # Provide recommendations
    print("\n💡 Recommended Installation:")

    if project_type == "development":
        print_colored("   📚 Development Setup Detected", "yellow")
        if uv_available:
            print_colored("   🚀 Use: uv sync", "green")
            print("   Then run: uv run codn --help")
        else:
            print_colored("   🚀 Use: pip install -e .", "green")
            print("   (Install in editable mode)")
    else:
        print_colored("   👤 User Installation", "blue")
        if uv_available:
            print_colored("   🚀 Recommended: uv tool install codn", "green")
            print("   (Faster, better dependency management)")
        elif pip_available:
            if not in_venv:
                print_colored(
                    "   ⚠️  Consider creating a virtual environment:", "yellow"
                )
                print("   python -m venv venv")
                print(
                    "   source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
                )
            print_colored("   🚀 Use: pip install codn", "green")
        else:
            print_colored("   ❌ No package manager available!", "red")
            print("   Please install pip or uv first.")

    # Installation commands
    print("\n⚡ Quick Install Commands:")

    if uv_available:
        if project_type == "development":
            print_colored("   uv sync", "cyan")
        else:
            print_colored("   uv tool install codn", "cyan")

    if pip_available:
        if project_type == "development":
            print_colored("   pip install -e .", "cyan")
        else:
            print_colored("   pip install codn", "cyan")

    # Install uv if not available
    if not uv_available:
        print("\n🔧 To install uv (recommended):")
        print_colored("   curl -LsSf https://astral.sh/uv/install.sh | sh", "cyan")
        print("   # Then restart your terminal")

    # Show usage examples
    print("\n📖 After Installation:")
    print("   codn                    # Analyze current project")
    print("   codn unused             # Find unused imports")
    print("   codn refs <function>    # Find function references")
    print("   codn --help             # Show all commands")

    # Environment-specific notes
    if project_type == "development":
        print("\n🔨 Development Notes:")
        print("   • Use 'uv run codn' if installed with uv sync")
        print("   • Use 'python -m codn.cli' for direct execution")
        print("   • Run tests with 'uv run pytest' or 'python run_tests.py'")

    if not in_venv and project_type != "development" and pip_available:
        print("\n⚠️  Virtual Environment Recommendation:")
        print("   Consider using a virtual environment to avoid conflicts:")
        print("   python -m venv codn-env")
        print("   source codn-env/bin/activate")
        print("   pip install codn")


if __name__ == "__main__":
    main()
