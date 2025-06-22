# 开发快速指南

## 快速开始

```bash
git clone https://github.com/dweb-lab/codn.git
cd codn
uv sync  # 或 pip install -e .
make install-hooks  # 安装 pre-commit hooks
```

## 常用命令

### 代码质量
```bash
make pre-commit-fast  # 快速检查（推荐）
./check-ruff.sh       # 推送前的全面检查
ruff format .         # 格式化
ruff check . --fix    # 修复 lint 问题
```

### 测试
```bash
make test             # 运行所有测试
pytest tests/test_specific.py  # 运行特定测试
make test-coverage    # 测试覆盖率
```

### 开发工作流
```bash
make pre-commit-fast  # 提交前
make test && ./check-ruff.sh  # 推送前
make lint test        # 检查所有内容
```

## 常见问题

- **导入错误**: 检查是否在虚拟环境中
- **Ruff 失败**: 运行 `ruff check . --fix` 自动修复
- **测试失败**: 检查依赖是否安装完整

更多详细文档请参阅 [docs/](../README.md) 目录。
