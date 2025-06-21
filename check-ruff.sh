#!/bin/bash

# Simple script to check ruff before commits
# Usage: ./check-ruff.sh

set -e

echo "🔍 Running ruff checks..."

# Check if we're in the right directory
if [ ! -f "ruff.toml" ]; then
    echo "❌ Error: ruff.toml not found. Please run this script from the project root."
    exit 1
fi

# Run ruff linting
echo "📝 Running ruff lint..."
if ruff check . --quiet; then
    echo "✅ Ruff lint passed"
else
    echo "❌ Ruff lint failed"
    echo ""
    echo "💡 To see detailed errors, run: ruff check ."
    echo "💡 To auto-fix some issues, run: ruff check . --fix"
    exit 1
fi

# Run ruff formatting check
echo "🎨 Checking ruff format..."
if ruff format . --check --quiet; then
    echo "✅ Ruff format check passed"
else
    echo "❌ Code needs formatting"
    echo ""
    echo "💡 To format the code, run: ruff format ."
    exit 1
fi

echo ""
echo "🎉 All ruff checks passed! Ready to commit."
