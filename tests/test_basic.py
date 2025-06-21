"""
Basic test file to verify pytest configuration.

This file contains simple tests to ensure that the pytest setup is working correctly.
"""

import asyncio
from pathlib import Path

import pytest


class TestBasicFunctionality:
    """Basic functionality tests."""

    def test_simple_assertion(self):
        """Test that basic assertions work."""
        assert 1 + 1 == 2
        assert "hello" == "hello"
        assert [1, 2, 3] == [1, 2, 3]

    def test_string_operations(self):
        """Test string operations."""
        text = "Hello, World!"
        assert text.upper() == "HELLO, WORLD!"
        assert text.lower() == "hello, world!"
        assert len(text) == 13

    def test_list_operations(self):
        """Test list operations."""
        numbers = [1, 2, 3, 4, 5]
        assert len(numbers) == 5
        assert sum(numbers) == 15
        assert max(numbers) == 5
        assert min(numbers) == 1

    def test_dict_operations(self):
        """Test dictionary operations."""
        data = {"name": "test", "value": 42}
        assert data["name"] == "test"
        assert data["value"] == 42
        assert "name" in data
        assert "missing" not in data

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (0, 0),
            (1, 1),
            (2, 4),
            (3, 9),
            (4, 16),
        ],
    )
    def test_square_function(self, input_val, expected):
        """Test square function with different inputs."""
        assert input_val**2 == expected


class TestAsyncFunctionality:
    """Async functionality tests."""

    @pytest.mark.asyncio
    async def test_simple_async(self):
        """Test simple async functionality."""

        async def async_function():
            await asyncio.sleep(0.01)
            return "async result"

        result = await async_function()
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_async_with_exception(self):
        """Test async function that raises exception."""

        async def failing_async_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_async_function()

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self):
        """Test running concurrent async tasks."""

        async def task(delay, value):
            await asyncio.sleep(delay)
            return value * 2

        tasks = [
            asyncio.create_task(task(0.01, 1)),
            asyncio.create_task(task(0.01, 2)),
            asyncio.create_task(task(0.01, 3)),
        ]

        results = await asyncio.gather(*tasks)
        assert results == [2, 4, 6]


class TestFileOperations:
    """File operations tests."""

    def test_path_operations(self, tmp_path):
        """Test path operations with temporary directory."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, pytest!"

        # Write to file
        test_file.write_text(test_content)

        # Read from file
        content = test_file.read_text()
        assert content == test_content

        # Check file exists
        assert test_file.exists()
        assert test_file.is_file()

    def test_directory_operations(self, tmp_path):
        """Test directory operations."""
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()

        assert test_dir.exists()
        assert test_dir.is_dir()

        # Create files in directory
        for i in range(3):
            (test_dir / f"file_{i}.txt").write_text(f"Content {i}")

        files = list(test_dir.glob("*.txt"))
        assert len(files) == 3


class TestExceptionHandling:
    """Exception handling tests."""

    def test_expected_exception(self):
        """Test that expected exceptions are raised."""
        with pytest.raises(ZeroDivisionError):
            1 / 0

        with pytest.raises(ValueError, match="invalid literal"):
            int("not_a_number")

        with pytest.raises(KeyError):
            {"a": 1}["b"]

    def test_no_exception_raised(self):
        """Test that no exception is raised when expected."""
        try:
            result = 10 / 2
            assert result == 5.0
        except Exception:
            pytest.fail("Unexpected exception raised")


class TestFixtures:
    """Test fixture usage."""

    @pytest.fixture
    def sample_data(self):
        """Sample data fixture."""
        return {
            "users": ["alice", "bob", "charlie"],
            "scores": [95, 87, 92],
            "active": True,
        }

    def test_fixture_usage(self, sample_data):
        """Test using custom fixture."""
        assert len(sample_data["users"]) == 3
        assert sample_data["active"] is True
        assert sum(sample_data["scores"]) == 274

    def test_multiple_fixtures(self, sample_data, tmp_path):
        """Test using multiple fixtures."""
        # Write sample data to temporary file
        data_file = tmp_path / "data.txt"
        data_file.write_text(str(sample_data))

        # Read it back
        content = data_file.read_text()
        assert "alice" in content
        assert "scores" in content


@pytest.mark.slow
class TestSlowOperations:
    """Slow operations that can be skipped with -m 'not slow'."""

    def test_slow_operation(self):
        """Test marked as slow."""
        import time

        time.sleep(0.1)  # Simulate slow operation
        assert True


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_integration_example(self):
        """Example integration test."""
        # This would test interaction between components
        assert True


# Test markers and skipping
@pytest.mark.skipif(not Path("/usr/bin").exists(), reason="Unix-like system required")
def test_unix_specific():
    """Test that only runs on Unix-like systems."""
    assert Path("/usr/bin").exists()


@pytest.mark.xfail(reason="Known issue, fix in progress")
def test_known_failure():
    """Test that is expected to fail."""
    assert False  # This will be marked as expected failure


# Test with custom markers
pytestmark = pytest.mark.unit
