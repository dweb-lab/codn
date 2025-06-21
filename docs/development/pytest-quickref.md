# Pytest 快速参考卡片

## 🚀 快速开始

```bash
# 安装依赖
uv sync --group test

# 运行所有测试
uv run pytest

# 运行特定文件
uv run pytest tests/test_basic.py

# 详细输出
uv run pytest -v
```

## 📋 常用命令

### 基本测试
```bash
uv run pytest                    # 所有测试
uv run pytest -v                # 详细输出
uv run pytest -s                # 显示 print
uv run pytest -x                # 首次失败时停止
uv run pytest -q                # 简洁输出
```

### 标记过滤
```bash
uv run pytest -m unit                    # 只运行单元测试
uv run pytest -m "not slow"             # 跳过慢速测试
uv run pytest -m "unit and not network" # 组合条件
```

### 关键词过滤
```bash
uv run pytest -k "test_basic"           # 包含关键词
uv run pytest -k "not slow"             # 排除关键词
```

### 覆盖率
```bash
uv run pytest --cov=codn                        # 基本覆盖率
uv run pytest --cov=codn --cov-report=html      # HTML报告
uv run pytest --cov=codn --cov-report=term-missing  # 显示缺失行
```

### 并行测试
```bash
uv run pytest -n auto              # 自动并行
uv run pytest -n 4                 # 4个进程
```

### 调试
```bash
uv run pytest --pdb                # 失败时进入调试器
uv run pytest --tb=long            # 详细错误信息
uv run pytest --lf                 # 只运行失败的测试
uv run pytest --ff                 # 先运行失败的测试
```

## 🏷️ 测试标记

### 内置标记
- `@pytest.mark.skip` - 跳过测试
- `@pytest.mark.skipif(condition)` - 条件跳过
- `@pytest.mark.xfail` - 预期失败
- `@pytest.mark.parametrize` - 参数化测试

### 项目标记
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.network` - 需要网络
- `@pytest.mark.asyncio` - 异步测试

## ✨ 编写测试

### 基本测试
```python
def test_simple_function():
    assert add(2, 3) == 5

class TestUserService:
    def test_create_user(self):
        user = UserService.create({"name": "test"})
        assert user.name == "test"
```

### 异常测试
```python
def test_exception():
    with pytest.raises(ValueError, match="Invalid"):
        invalid_function()
```

### 参数化测试
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2), (2, 4), (3, 6)
])
def test_double(input, expected):
    assert double(input) == expected
```

### 异步测试
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == "expected"
```

### Fixture使用
```python
@pytest.fixture
def sample_data():
    return {"name": "test", "value": 42}

def test_with_fixture(sample_data):
    assert sample_data["name"] == "test"
```

### Mock使用
```python
def test_with_mock(mocker):
    mock_func = mocker.patch('module.function')
    mock_func.return_value = "mocked"

    result = call_function()
    assert result == "mocked"
```

## 🛠️ Makefile命令

```bash
make test              # 运行所有测试
make test-fast         # 快速测试(跳过慢速)
make test-unit         # 单元测试
make test-integration  # 集成测试
make test-cov          # 覆盖率测试
make test-parallel     # 并行测试
```

## 📊 覆盖率目标

- 单元测试覆盖率: ≥ 90%
- 集成测试覆盖率: ≥ 70%
- 总体覆盖率: ≥ 80%

## 🔧 配置文件

### pyproject.toml
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--strict-markers", "--verbose"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow",
    "unit: marks tests as unit tests",
    "integration: marks tests as integration tests",
]
```

### 覆盖率配置
```toml
[tool.coverage.run]
source = ["codn"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if __name__ == .__main__."]
```

## 🚀 性能优化

- 使用 `-m "not slow"` 跳过慢速测试
- 使用 `-n auto` 并行执行
- 使用 `--lf` 只运行失败的测试
- 使用 `--cache-clear` 清理缓存

## 💡 最佳实践

1. **测试命名**: 使用 `test_` 前缀
2. **测试组织**: 使用类分组相关测试
3. **断言清晰**: 使用有意义的断言消息
4. **独立性**: 每个测试应该独立运行
5. **可读性**: 测试应该易于理解和维护

## 🔍 故障排除

- 导入错误: 检查 `PYTHONPATH` 或使用 `uv run`
- 测试未发现: 确保文件名以 `test_` 开头
- 异步测试问题: 确保使用 `@pytest.mark.asyncio`
- 覆盖率不准确: 检查 `source` 配置
