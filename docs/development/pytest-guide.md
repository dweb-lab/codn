# Pytest 最佳实践指南

本指南提供了在codn项目中使用pytest的完整最佳实践配置。

## 📋 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置详解](#配置详解)
- [测试分类](#测试分类)
- [运行测试](#运行测试)
- [覆盖率报告](#覆盖率报告)
- [最佳实践](#最佳实践)
- [CI/CD集成](#cicd集成)

## 🚀 快速开始

### 使用uv安装依赖

```bash
# 安装测试依赖
uv sync --group test

# 或者直接安装
uv add --group test pytest pytest-asyncio pytest-cov pytest-mock
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定文件
uv run pytest tests/test_basic.py

# 运行带覆盖率的测试
uv run pytest --cov=codn --cov-report=term-missing
```

## 📁 项目结构

```
codn/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 全局配置和fixtures
│   ├── fixtures/                # 测试数据和fixtures
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   ├── test_basic.py           # 基础功能测试
│   ├── test_pyright_lsp_client.py
│   └── test_*.py               # 其他测试文件
├── reports/                     # 测试报告目录
├── pyproject.toml              # pytest配置
├── Makefile                    # 便捷命令
├── run_tests.py               # 测试运行脚本
└── tox.ini                    # 多环境测试配置
```

## ⚙️ 配置详解

### pyproject.toml配置

```toml
[tool.pytest.ini_options]
# 测试发现
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 输出格式
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--tb=short",
]

# 异步测试支持
asyncio_mode = "auto"

# 测试标记
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "async: marks tests as async tests",
    "network: marks tests that require network access",
    "skip_ci: marks tests to skip in CI environment",
]
```

### conftest.py - 全局配置

```python
import pytest
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator

# 自动标记测试
def pytest_collection_modifyitems(config, items):
    for item in items:
        # 自动标记异步测试
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker("async")

        # 根据路径自动标记
        if "integration" in str(item.fspath):
            item.add_marker("integration")
        if "unit" in str(item.fspath):
            item.add_marker("unit")

# 共享fixtures
@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)
```

## 🏷️ 测试分类

### 测试标记 (Markers)

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.async` - 异步测试
- `@pytest.mark.network` - 需要网络的测试
- `@pytest.mark.skip_ci` - CI中跳过的测试

### 测试类型示例

```python
# 单元测试
@pytest.mark.unit
def test_simple_function():
    assert add(2, 3) == 5

# 异步测试
@pytest.mark.asyncio
async def test_async_function():
    result = await async_add(2, 3)
    assert result == 5

# 参数化测试
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected

# 慢速测试
@pytest.mark.slow
def test_slow_operation():
    time.sleep(1)
    assert True
```

## 🔧 运行测试

### 基本命令

```bash
# 使用uv运行测试
uv run pytest                              # 运行所有测试
uv run pytest tests/test_basic.py         # 运行特定文件
uv run pytest -v                          # 详细输出
uv run pytest -s                          # 显示print输出
uv run pytest -x                          # 遇到失败时停止

# 使用Makefile
make test                                  # 运行所有测试
make test-unit                            # 只运行单元测试
make test-integration                     # 只运行集成测试
make test-fast                           # 跳过慢速测试

# 使用运行脚本
python run_tests.py                      # 运行所有测试
python run_tests.py --unit              # 只运行单元测试
python run_tests.py --coverage          # 带覆盖率运行
```

### 按标记运行

```bash
# 运行特定标记的测试
uv run pytest -m unit                    # 只运行单元测试
uv run pytest -m "not slow"             # 跳过慢速测试
uv run pytest -m "unit and not network" # 单元测试但不包括网络测试

# 运行特定关键词
uv run pytest -k "test_basic"           # 运行包含test_basic的测试
uv run pytest -k "not slow"             # 跳过包含slow的测试
```

### 并行运行

```bash
# 安装pytest-xdist
uv add --group test pytest-xdist

# 并行运行
uv run pytest -n auto                   # 自动检测CPU核心数
uv run pytest -n 4                      # 使用4个进程
```

## 📊 覆盖率报告

### 生成覆盖率报告

```bash
# 终端报告
uv run pytest --cov=codn --cov-report=term-missing

# HTML报告
uv run pytest --cov=codn --cov-report=html

# XML报告（用于CI）
uv run pytest --cov=codn --cov-report=xml

# 多种格式
uv run pytest --cov=codn --cov-report=term-missing --cov-report=html --cov-report=xml
```

### 覆盖率配置

```toml
[tool.coverage.run]
source = ["codn"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
    "setup.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## 💡 最佳实践

### 1. 测试组织

```python
# ✅ 好的做法
class TestUserService:
    """用户服务相关测试"""

    @pytest.fixture
    def user_data(self):
        return {"name": "test", "email": "test@example.com"}

    def test_create_user(self, user_data):
        user = UserService.create(user_data)
        assert user.name == "test"

    def test_invalid_email(self):
        with pytest.raises(ValueError, match="Invalid email"):
            UserService.create({"email": "invalid"})

# ❌ 避免的做法
def test_everything():  # 测试太宽泛
    # 做很多不相关的测试
    pass
```

### 2. Fixture使用

```python
# ✅ 作用域明确的fixture
@pytest.fixture(scope="session")
def database():
    """会话级别的数据库连接"""
    db = create_test_database()
    yield db
    db.close()

@pytest.fixture(scope="function")
def clean_database(database):
    """每个测试后清理数据库"""
    yield database
    database.clear_all_tables()

# ✅ 参数化fixture
@pytest.fixture(params=["sqlite", "postgres"])
def database_type(request):
    return request.param
```

### 3. 异步测试

```python
# ✅ 异步测试最佳实践
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result == expected_value

# ✅ 测试异步异常
@pytest.mark.asyncio
async def test_async_exception():
    with pytest.raises(SomeException):
        await failing_async_function()

# ✅ 并发测试
@pytest.mark.asyncio
async def test_concurrent_operations():
    tasks = [
        asyncio.create_task(operation1()),
        asyncio.create_task(operation2()),
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 2
```

### 4. Mock使用

```python
# ✅ 适当使用mock
def test_external_api(mocker):
    # Mock外部依赖
    mock_response = mocker.patch('requests.get')
    mock_response.return_value.json.return_value = {"status": "ok"}

    result = api_client.get_status()
    assert result == {"status": "ok"}

# ✅ 异步mock
@pytest.mark.asyncio
async def test_async_mock(mocker):
    mock_func = mocker.AsyncMock(return_value="mocked")
    result = await mock_func()
    assert result == "mocked"
```

### 5. 测试数据管理

```python
# ✅ 使用fixture提供测试数据
@pytest.fixture
def sample_users():
    return [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35},
    ]

# ✅ 临时文件测试
def test_file_processing(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    result = process_file(test_file)
    assert result.success
```

## 🔄 CI/CD集成

### GitHub Actions配置

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}

    - name: Install dependencies
      run: uv sync --group test

    - name: Run tests
      run: uv run pytest --cov=codn --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 常用命令总结

```bash
# 开发流程
uv sync --group test                     # 安装测试依赖
uv run pytest -v                        # 运行详细测试
uv run pytest --cov=codn --cov-report=html  # 生成覆盖率报告

# 快速测试
uv run pytest -x --tb=short            # 快速失败，简短错误信息
uv run pytest -m "not slow"            # 跳过慢速测试

# 调试测试
uv run pytest -s -vv                   # 显示所有输出
uv run pytest --pdb                    # 失败时进入调试器
uv run pytest --lf                     # 只运行上次失败的测试

# CI流程
uv run pytest --cov=codn --cov-report=xml --junitxml=junit.xml
```

## 🎯 性能优化

### 1. 并行测试

```bash
# 安装并行插件
uv add --group test pytest-xdist

# 运行并行测试
uv run pytest -n auto
```

### 2. 测试分组

```bash
# 只运行快速测试用于开发
uv run pytest -m "not slow"

# 完整测试用于CI
uv run pytest
```

### 3. 缓存利用

```bash
# 清理缓存
uv run pytest --cache-clear

# 只运行失败的测试
uv run pytest --lf

# 先运行失败的测试
uv run pytest --ff
```

这个完整的pytest配置为你的项目提供了：

- ✅ 完整的测试分类和标记系统
- ✅ 异步测试支持
- ✅ 覆盖率报告
- ✅ CI/CD集成
- ✅ 性能优化配置
- ✅ 最佳实践指导

根据项目需要，你可以逐步添加更多测试插件和配置。
