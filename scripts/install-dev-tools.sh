#!/bin/bash

# 安装开发工具脚本
# 用于确保pre-commit hooks所需的本地工具都已安装

set -e

echo "🔧 安装开发工具中..."

# 设置代理（如果需要）
if [ -n "$USE_PROXY" ]; then
    export https_proxy=http://127.0.0.1:7890
    export http_proxy=http://127.0.0.1:7890
    export all_proxy=socks5://127.0.0.1:7890
    echo "✓ 已设置代理"
fi

# 安装开发依赖
echo "📦 安装开发依赖..."
uv pip install -e ".[dev]"

# 检查并安装额外的工具
echo "🔍 检查额外工具..."

# 安装bandit（如果不在dev依赖中）
if ! python -c "import bandit" 2>/dev/null; then
    echo "📦 安装 bandit..."
    uv pip install bandit
else
    echo "✓ bandit 已安装"
fi

# 安装docformatter
if ! python -c "import docformatter" 2>/dev/null; then
    echo "📦 安装 docformatter..."
    uv pip install docformatter
else
    echo "✓ docformatter 已安装"
fi

# 验证所有工具
echo "🧪 验证工具安装..."

tools=(
    "ruff --version"
    "python -m mypy --version"
    "python -m bandit --version"
    "python -m docformatter --version"
)

for tool in "${tools[@]}"; do
    if $tool >/dev/null 2>&1; then
        echo "✓ $tool"
    else
        echo "❌ $tool 安装失败"
        exit 1
    fi
done

# 安装pre-commit hooks
echo "🪝 安装 pre-commit hooks..."
pre-commit install

echo "🎉 所有开发工具安装完成！"
echo ""
echo "使用方法："
echo "  1. 直接提交代码，pre-commit会自动运行检查"
echo "  2. 手动运行: pre-commit run --all-files"
echo "  3. 如需使用代理: USE_PROXY=1 ./scripts/install-dev-tools.sh"
echo ""
echo "⚠️  注意: 本项目使用 uv 作为包管理器"
echo "    - 安装包: uv pip install <package>"
echo "    - 不要使用系统 pip install"
