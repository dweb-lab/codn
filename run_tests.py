#!/usr/bin/env python3
"""
Test runner script for codn project.

This script provides a convenient way to run different types of tests
with various options and configurations.
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import List


def run_command(cmd: List[str], description: str) -> int:
    """Run a command and return its exit code."""
    print(f"🚀 {description}")
    print(f"   Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED")
        print()
        return result.returncode
    except KeyboardInterrupt:
        print(f"\n⚠️  {description} - INTERRUPTED")
        return 130
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for codn project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --integration      # Run integration tests only
  python run_tests.py --fast             # Run fast tests only
  python run_tests.py --coverage         # Run with coverage
  python run_tests.py --parallel         # Run tests in parallel
  python run_tests.py --watch            # Run in watch mode
  python run_tests.py --debug            # Run with debug output
  python run_tests.py --file tests/test_specific.py  # Run specific file
        """
    )

    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--unit", "-u",
        action="store_true",
        help="Run unit tests only"
    )
    test_group.add_argument(
        "--integration", "-i",
        action="store_true",
        help="Run integration tests only"
    )
    test_group.add_argument(
        "--slow", "-s",
        action="store_true",
        help="Run slow tests only"
    )
    test_group.add_argument(
        "--fast", "-f",
        action="store_true",
        help="Run fast tests only (exclude slow tests)"
    )
    test_group.add_argument(
        "--network", "-n",
        action="store_true",
        help="Run network tests only"
    )
    test_group.add_argument(
        "--no-network",
        action="store_true",
        help="Run tests without network requirements"
    )

    # Test execution options
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--html-coverage",
        action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel using pytest-xdist"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run tests in watch mode"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Run tests with debug output"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Run specific test file"
    )
    parser.add_argument(
        "--marker", "-m",
        type=str,
        help="Run tests with specific marker"
    )
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        help="Run tests matching keyword expression"
    )

    # Output options
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet output"
    )
    parser.add_argument(
        "--tb",
        choices=["short", "long", "line", "no"],
        default="short",
        help="Traceback format"
    )
    parser.add_argument(
        "--maxfail",
        type=int,
        default=0,
        help="Maximum number of failures before stopping"
    )

    # Additional options
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Disable coverage even if enabled by default"
    )
    parser.add_argument(
        "--pytest-args",
        type=str,
        help="Additional arguments to pass to pytest"
    )

    args = parser.parse_args()

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run from project root.")
        return 1

    # Install dependencies if requested
    if args.install_deps:
        install_cmd = [sys.executable, "-m", "pip", "install", "-e", ".[test]"]
        exit_code = run_command(install_cmd, "Installing test dependencies")
        if exit_code != 0:
            return exit_code

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add test selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.slow:
        cmd.extend(["-m", "slow"])
    elif args.fast:
        cmd.extend(["-m", "not slow"])
    elif args.network:
        cmd.extend(["-m", "network"])
    elif args.no_network:
        cmd.extend(["-m", "not network"])

    # Add specific file if provided
    if args.file:
        cmd.append(args.file)

    # Add marker if provided
    if args.marker:
        cmd.extend(["-m", args.marker])

    # Add keyword if provided
    if args.keyword:
        cmd.extend(["-k", args.keyword])

    # Add verbosity
    if args.quiet:
        cmd.append("-q")
    elif args.verbose:
        cmd.extend(["-" + "v" * min(args.verbose, 3)])

    # Add traceback format
    cmd.extend(["--tb", args.tb])

    # Add maxfail
    if args.maxfail > 0:
        cmd.extend(["--maxfail", str(args.maxfail)])

    # Add coverage options
    if args.coverage or args.html_coverage:
        if not args.no_cov:
            cmd.extend(["--cov=codn", "--cov-report=term-missing"])

            if args.html_coverage:
                cmd.extend(["--cov-report=html:htmlcov"])
                cmd.extend(["--cov-report=xml"])

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])

    # Add watch mode
    if args.watch:
        cmd.extend(["--looponfail"])

    # Add debug options
    if args.debug:
        cmd.extend(["-s", "--tb=long", "--no-cov"])

    # Add additional pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())

    # Run the tests
    description = "Running tests"
    if args.unit:
        description = "Running unit tests"
    elif args.integration:
        description = "Running integration tests"
    elif args.slow:
        description = "Running slow tests"
    elif args.fast:
        description = "Running fast tests"
    elif args.network:
        description = "Running network tests"
    elif args.no_network:
        description = "Running offline tests"

    exit_code = run_command(cmd, description)

    # Show coverage report location if HTML coverage was generated
    if args.html_coverage and exit_code == 0:
        print("📊 HTML coverage report generated at: htmlcov/index.html")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
