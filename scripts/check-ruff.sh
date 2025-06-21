#!/bin/bash
# Simplified ruff checker
set -e

echo "🔍 Running ruff checks..."
ruff check . --quiet && echo "✅ Lint passed" || { echo "❌ Lint failed"; exit 1; }
ruff format . --check --quiet && echo "✅ Format passed" || { echo "❌ Format failed"; exit 1; }
echo "🎉 All checks passed!"
