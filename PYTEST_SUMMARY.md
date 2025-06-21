# Pytest 最佳实践总结

本文档总结了在 codn 项目中成功实施的 pytest 最佳实践配置。

## 🎯 配置概览

### 项目结构
```
codn/
├── tests/
│   ├── conftest.py              # 全局配置和 fixtures
│   ├── test_basic.py           # 基础功能测试示例
│   ├── test_pyright_lsp_client.py  # 核心模块测试
│   ├── unit/                   # 单元测试目录
│   ├── integration/            # 集成测试目录
│   └── fixtures/               # 测试数据
├── pyproject.toml              # pytest 配置
├── Makefile                    # 便捷命令
├── run_tests.py               # 自定义测试运行器
└── tox.ini                    # 多环境测试
```

### 依赖管理 (uv)
```toml
[dependency-groups]
test = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=6.0",
    "pytest-mock>=3.10",
    "pytest-xdist>=3.0",
    "pytest-timeout>=2.1",
]
```

## ⚙️ 核心配置

### pytest 配置 (pyproject.toml)
```toml
[tool.pytest.ini_options]
# 测试发现
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 基本选项
addopts = [
    "--strict-markers",
    "--strict-config", 
    "--verbose",
    "--tb=short",
]

# 异步支持
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

## 🔧 常用命令

### 基本测试命令
```bash
# 使用 uv (推荐)
uv run pytest                              # 运行所有测试
uv run pytest tests/test_basic.py         # 运行特定文件
uv run pytest -v                          # 详细输出
uv run pytest -s                          # 显示 print 输出
uv run pytest -x                          # 遇到失败时停止

# 使用 Makefile
make test                                  # 运行所有测试
make test-unit                            # 单元测试
make test-integration                     # 集成测试
make test-fast                           # 快速测试(跳过慢速)
make test-cov                            # 带覆盖率
```

### 标记和过滤
```bash
# 按标记运行
uv run pytest -m unit                    # 只运行单元测试
uv run pytest -m "not slow"             # 跳过慢速测试
uv run pytest -m "unit and not network" # 组合条件

# 按关键词过滤
uv run pytest -k "test_basic"           # 包含特定关键词
uv run pytest -k "not slow"             # 排除特定关键词
```

### 覆盖率报告
```bash
# 终端报告
uv run pytest --cov=codn --cov-report=term-missing

# HTML 报告
uv run pytest --cov=codn --cov-report=html

# 多种格式报告
uv run pytest --cov=codn --cov-report=term-missing --cov-report=html --cov-report=xml
```

### 并行测试
```bash
# 并行运行
uv run pytest -n auto                   # 自动检测 CPU 核心数
uv run pytest -n 4                      # 使用 4 个进程
```

## 📝 编写测试最佳实践

### 1. 测试组织
```python
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
```

### 2. 异步测试
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_exception():
    with pytest.raises(SomeException):
        await failing_async_function()
```

### 3. 参数化测试
```python
@pytest.mark.parametrize("input_val,expected", [
    (0, 0),
    (1, 1), 
    (2, 4),
    (3, 9),
])
def test_square_function(input_val, expected):
    assert square(input_val) == expected
```

### 4. Fixture 使用
```python
@pytest.fixture(scope="session")
def database():
    """会话级别的数据库连接"""
    db = create_test_database()
    yield db
    db.close()

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录 fixture"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)
```

### 5. Mock 使用
```python
def test_external_api(mocker):
    # Mock 外部依赖
    mock_response = mocker.patch('requests.get')
    mock_response.return_value.json.return_value = {"status": "ok"}
    
    result = api_client.get_status()
    assert result == {"status": "ok"}

@pytest.mark.asyncio
async def test_async_mock(mocker):
    mock_func = mocker.AsyncMock(return_value="mocked")
    result = await mock_func()
    assert result == "mocked"
```

## 🏷️ 测试标记策略

### 标记定义
- `@pytest.mark.unit` - 单元测试，快速执行
- `@pytest.mark.integration` - 集成测试，可能较慢
- `@pytest.mark.slow` - 慢速测试，开发时可跳过
- `@pytest.mark.network` - 需要网络连接的测试
- `@pytest.mark.skip_ci` - CI 环境中跳过的测试

### 使用示例
```python
@pytest.mark.unit
def test_pure_function():
    assert add(2, 3) == 5

@pytest.mark.integration
@pytest.mark.slow  
def test_database_integration():
    # 复杂的数据库集成测试
    pass

@pytest.mark.network
def test_api_call():
    # 需要真实 API 调用的测试
    pass
```

## 🚀 性能优化

### 1. 测试分层
```bash
# 开发时只运行快速测试
uv run pytest -m "not slow"

# CI 时运行完整测试套件
uv run pytest
```

### 2. 并行执行
```bash
# 本地开发
uv run pytest -n auto

# CI 环境
uv run pytest -n 4
```

### 3. 测试缓存
```bash
# 只运行失败的测试
uv run pytest --lf

# 先运行失败的测试
uv run pytest --ff

# 清理缓存
uv run pytest --cache-clear
```

## 🔄 CI/CD 集成

### GitHub Actions 示例
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
    
    - name: Set up Python
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

## 📊 测试报告

### 覆盖率目标
- 单元测试覆盖率: ≥ 90%
- 集成测试覆盖率: ≥ 70%
- 总体覆盖率: ≥ 80%

### 报告格式
- 开发环境: 终端报告 + HTML 报告
- CI 环境: XML 报告上传到覆盖率服务

## 🛠️ 调试技巧

### 调试命令
```bash
# 显示详细输出
uv run pytest -vvv

# 进入 pdb 调试器
uv run pytest --pdb

# 显示最慢的 10 个测试
uv run pytest --durations=10

# 详细的失败信息
uv run pytest --tb=long
```

### 日志输出
```bash
# 显示日志输出
uv run pytest -s --log-cli-level=INFO

# 捕获日志到文件
uv run pytest --log-file=tests.log
```

## ✅ 成功指标

### 开发效率
- 测试运行时间 < 30 秒（快速测试）
- 完整测试套件 < 5 分钟
- 并行测试加速比 > 2x

### 质量指标
- 测试通过率 > 95%
- 覆盖率稳定在 80% 以上
- 测试维护成本低

### 团队协作
- 测试易于理解和维护
- 新开发者可快速上手
- CI 流程稳定可靠

## 📚 推荐资源

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [pytest-mock 文档](https://pytest-mock.readthedocs.io/)

---

这套 pytest 配置为 codn 项目提供了完整的测试基础设施，支持高效的测试驱动开发和持续集成。