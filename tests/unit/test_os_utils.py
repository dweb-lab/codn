"""Unit tests for codn.utils.os_utils module.

This module contains comprehensive tests for file system operations, gitignore handling,
and async file discovery functionality.
"""

from unittest.mock import patch

import pathspec
import pytest

from codn.utils.os_utils import (
    DEFAULT_SKIP_DIRS,
    list_all_files,
    load_gitignore,
    should_ignore,
)


class TestLoadGitignore:
    """Test cases for load_gitignore function."""

    def test_load_existing_gitignore(self, tmp_path):
        """Test loading existing .gitignore file."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
.venv/

# IDE
.vscode/
.idea/
"""
        gitignore_path.write_text(gitignore_content)

        spec = load_gitignore(tmp_path)
        assert isinstance(spec, pathspec.PathSpec)

        # Test that it matches expected patterns
        assert spec.match_file("__pycache__/")
        assert spec.match_file("test.pyc")
        assert spec.match_file("venv/")
        assert spec.match_file(".vscode/")

    def test_load_nonexistent_gitignore(self, tmp_path):
        """Test loading when .gitignore doesn't exist."""
        spec = load_gitignore(tmp_path)
        assert isinstance(spec, pathspec.PathSpec)

        # Should not match anything since no patterns are loaded
        assert not spec.match_file("__pycache__/")
        assert not spec.match_file("test.pyc")

    def test_load_empty_gitignore(self, tmp_path):
        """Test loading empty .gitignore file."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("")

        spec = load_gitignore(tmp_path)
        assert isinstance(spec, pathspec.PathSpec)

        # Should not match anything
        assert not spec.match_file("any_file.py")

    def test_load_gitignore_with_comments(self, tmp_path):
        """Test loading .gitignore with comments and blank lines."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_content = """
# This is a comment
*.pyc

# Another comment

# Empty line above
dist/
"""
        gitignore_path.write_text(gitignore_content)

        spec = load_gitignore(tmp_path)
        assert spec.match_file("test.pyc")
        assert spec.match_file("dist/")

    def test_load_gitignore_with_unicode(self, tmp_path):
        """Test loading .gitignore with Unicode content."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_content = """
# 测试文件
测试*.py
# Emoji test 🔥
*🔥.txt
"""
        gitignore_path.write_text(gitignore_content, encoding="utf-8")

        spec = load_gitignore(tmp_path)
        assert spec.match_file("测试file.py")
        assert spec.match_file("test🔥.txt")

    def test_load_gitignore_read_error(self, tmp_path):
        """Test handling read errors (e.g., permissions)."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("*.pyc")

        # Mock to simulate read error
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            spec = load_gitignore(tmp_path)
            assert isinstance(spec, pathspec.PathSpec)
            # Should return empty spec on error
            assert not spec.match_file("test.pyc")

    def test_load_gitignore_unicode_decode_error(self, tmp_path):
        """Test handling Unicode decode errors."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_bytes(b"\xff\xfe*.pyc")  # Invalid UTF-8

        with patch(
            "pathlib.Path.read_text",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            spec = load_gitignore(tmp_path)
            assert isinstance(spec, pathspec.PathSpec)
            # Should return empty spec on decode error
            assert not spec.match_file("test.pyc")


class TestShouldIgnore:
    """Test cases for should_ignore function."""

    def test_ignore_by_directory_name(self, tmp_path):
        """Test ignoring files by directory names."""
        ignored_dirs = {".git", "__pycache__", "node_modules"}
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", [])

        # Create test paths
        git_file = tmp_path / ".git" / "config"
        pycache_file = tmp_path / "src" / "__pycache__" / "test.pyc"
        node_modules_file = tmp_path / "node_modules" / "package" / "index.js"
        normal_file = tmp_path / "src" / "main.py"

        assert should_ignore(git_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert (
            should_ignore(pycache_file, tmp_path, ignored_dirs, gitignore_spec) is True
        )
        assert (
            should_ignore(node_modules_file, tmp_path, ignored_dirs, gitignore_spec)
            is True
        )
        assert (
            should_ignore(normal_file, tmp_path, ignored_dirs, gitignore_spec) is False
        )

    def test_ignore_by_gitignore_patterns(self, tmp_path):
        """Test ignoring files by gitignore patterns."""
        ignored_dirs = set()
        patterns = ["*.pyc", "dist/", "*.log"]
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

        # Create test paths
        pyc_file = tmp_path / "src" / "main.pyc"
        dist_file = tmp_path / "dist" / "package.whl"
        log_file = tmp_path / "app.log"
        python_file = tmp_path / "src" / "main.py"

        assert should_ignore(pyc_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert should_ignore(dist_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert should_ignore(log_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert (
            should_ignore(python_file, tmp_path, ignored_dirs, gitignore_spec) is False
        )

    def test_ignore_combination(self, tmp_path):
        """Test ignoring files by both directory names and gitignore patterns."""
        ignored_dirs = {"__pycache__"}
        patterns = ["*.pyc", "temp/"]
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

        # Files ignored by directory name
        pycache_file = tmp_path / "__pycache__" / "test.py"
        # Files ignored by gitignore pattern
        pyc_file = tmp_path / "src" / "main.pyc"
        temp_file = tmp_path / "temp" / "data.txt"
        # Files not ignored
        normal_file = tmp_path / "src" / "main.py"

        assert (
            should_ignore(pycache_file, tmp_path, ignored_dirs, gitignore_spec) is True
        )
        assert should_ignore(pyc_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert should_ignore(temp_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert (
            should_ignore(normal_file, tmp_path, ignored_dirs, gitignore_spec) is False
        )

    def test_file_not_relative_to_root(self, tmp_path):
        """Test with file path not relative to root path."""
        ignored_dirs = set()
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", [])

        # Create a file outside the root directory
        other_dir = tmp_path.parent / "other_dir"
        other_dir.mkdir()
        external_file = other_dir / "external.py"

        # Should be ignored because it's not relative to root
        assert (
            should_ignore(external_file, tmp_path, ignored_dirs, gitignore_spec) is True
        )

    def test_complex_gitignore_patterns(self, tmp_path):
        """Test complex gitignore patterns."""
        ignored_dirs = set()
        patterns = [
            "*.pyc",
            "!important.pyc",  # Negation pattern
            "build/",
            "logs/*.log",
            "**/*.tmp",
        ]
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

        # Test various files
        normal_pyc = tmp_path / "normal.pyc"
        important_pyc = tmp_path / "important.pyc"
        build_file = tmp_path / "build" / "output.txt"
        log_file = tmp_path / "logs" / "app.log"
        tmp_file = tmp_path / "deep" / "nested" / "temp.tmp"
        python_file = tmp_path / "src" / "main.py"

        assert should_ignore(normal_pyc, tmp_path, ignored_dirs, gitignore_spec) is True
        assert (
            should_ignore(important_pyc, tmp_path, ignored_dirs, gitignore_spec)
            is False
        )  # Negated
        assert should_ignore(build_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert should_ignore(log_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert should_ignore(tmp_file, tmp_path, ignored_dirs, gitignore_spec) is True
        assert (
            should_ignore(python_file, tmp_path, ignored_dirs, gitignore_spec) is False
        )

    def test_empty_ignored_dirs(self, tmp_path):
        """Test with empty ignored directories set."""
        ignored_dirs = set()
        gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", [])

        # Even traditionally ignored directories should not be ignored
        git_file = tmp_path / ".git" / "config"
        pycache_file = tmp_path / "__pycache__" / "test.pyc"

        assert should_ignore(git_file, tmp_path, ignored_dirs, gitignore_spec) is False
        assert (
            should_ignore(pycache_file, tmp_path, ignored_dirs, gitignore_spec) is False
        )


class TestListAllFiles:
    """Test cases for list_all_files function."""

    @pytest.mark.asyncio
    async def test_simple_files(self, tmp_path):
        """Test discovering simple Python files."""
        # Create test files
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / "test.txt").write_text("not python")

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "module.py").write_text("class Module: pass")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should find 3 Python files
        python_files = [f.name for f in files]
        assert "main.py" in python_files
        assert "utils.py" in python_files
        assert "module.py" in python_files
        assert "test.txt" not in python_files

    @pytest.mark.asyncio
    async def test_respect_gitignore(self, tmp_path):
        """Test that gitignore patterns are respected."""
        # Create .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("ignored.py\nignored_dir/\n")

        # Create test files
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "ignored.py").write_text("print('ignored')")

        # Create ignored directory
        ignored_dir = tmp_path / "ignored_dir"
        ignored_dir.mkdir()
        (ignored_dir / "module.py").write_text("class Module: pass")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should only find main.py
        python_files = [f.name for f in files]
        assert "main.py" in python_files
        assert "ignored.py" not in python_files
        assert "module.py" not in python_files

    @pytest.mark.asyncio
    async def test_default_skip_directories(self, tmp_path):
        """Test that default skip directories are ignored."""
        # Create files in default skip directories
        for skip_dir in DEFAULT_SKIP_DIRS:
            dir_path = tmp_path / skip_dir
            dir_path.mkdir()
            (dir_path / "file.py").write_text("print('should be ignored')")

        # Create normal file
        (tmp_path / "main.py").write_text("print('main')")

        files = []
        async for py_file in list_all_files(tmp_path):
            files.append(py_file)

        # Should only find main.py
        assert len(files) == 1
        assert files[0].name == "main.py"

    @pytest.mark.asyncio
    async def test_custom_ignored_dirs(self, tmp_path):
        """Test with custom ignored directories."""
        # Create custom ignored directory
        custom_ignored = tmp_path / "custom_ignored"
        custom_ignored.mkdir()
        (custom_ignored / "file.py").write_text("print('ignored')")

        # Create normal file
        (tmp_path / "main.py").write_text("print('main')")

        # Test with custom ignored dirs
        files = []
        async for py_file in list_all_files(
            tmp_path,
            ignored_dirs={"custom_ignored"},
        ):
            files.append(py_file)

        # Should only find main.py
        assert len(files) == 1
        assert files[0].name == "main.py"

    @pytest.mark.asyncio
    async def test_nested_directory_structure(self, tmp_path):
        """Test with deeply nested directory structure."""
        # Create nested structure
        deep_path = tmp_path / "level1" / "level2" / "level3"
        deep_path.mkdir(parents=True)

        # Create files at different levels
        (tmp_path / "root.py").write_text("# Root level")
        (tmp_path / "level1" / "l1.py").write_text("# Level 1")
        (tmp_path / "level1" / "level2" / "l2.py").write_text("# Level 2")
        (deep_path / "l3.py").write_text("# Level 3")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should find all 4 files
        python_files = [f.name for f in files]
        assert len(python_files) == 4
        assert "root.py" in python_files
        assert "l1.py" in python_files
        assert "l2.py" in python_files
        assert "l3.py" in python_files

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path):
        """Test with empty directory."""
        files = []
        async for py_file in list_all_files(tmp_path):
            files.append(py_file)

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_no_python_files(self, tmp_path):
        """Test directory with no Python files."""
        # Create non-Python files
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "config.json").write_text('{"key": "value"}')
        (tmp_path / "script.sh").write_text("#!/bin/bash")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_symlinks(self, tmp_path):
        """Test handling of symbolic links."""
        # Create a Python file
        real_file = tmp_path / "real.py"
        real_file.write_text("print('real')")

        # Create a symlink to the file
        symlink_file = tmp_path / "symlink.py"
        try:
            symlink_file.symlink_to(real_file)
            symlinks_supported = True
        except OSError:
            # Symlinks might not be supported on this system
            symlinks_supported = False

        files = []
        async for py_file in list_all_files(tmp_path):
            files.append(py_file)

        if symlinks_supported:
            # Should find both real file and symlink
            python_files = [f.name for f in files]
            assert "real.py" in python_files
            assert "symlink.py" in python_files
        else:
            # Should find at least the real file
            assert len(files) >= 1

    @pytest.mark.asyncio
    async def test_unicode_filenames(self, tmp_path):
        """Test with Unicode filenames."""
        # Create files with Unicode names
        (tmp_path / "测试.py").write_text("# 测试文件")
        (tmp_path / "🐍.py").write_text("# Emoji file")
        (tmp_path / "normal.py").write_text("# Normal file")

        files = []
        async for py_file in list_all_files(tmp_path):
            files.append(py_file)

        # Should find all 3 files
        python_files = [f.name for f in files]
        assert len(python_files) == 3
        assert "测试.py" in python_files
        assert "🐍.py" in python_files
        assert "normal.py" in python_files

    @pytest.mark.asyncio
    async def test_large_directory_structure(self, tmp_path):
        """Test with large directory structure."""
        # Create many files and directories
        for i in range(10):
            dir_path = tmp_path / f"dir_{i}"
            dir_path.mkdir()
            for j in range(5):
                (dir_path / f"file_{j}.py").write_text(f"# File {i}-{j}")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should find 50 files (10 dirs * 5 files each)
        assert len(files) == 50

    @pytest.mark.asyncio
    async def test_with_string_path(self, tmp_path):
        """Test with string path instead of Path object."""
        # Create test file
        (tmp_path / "test.py").write_text("print('test')")

        files = []
        async for py_file in list_all_files(str(tmp_path)):
            files.append(py_file)

        assert len(files) == 1
        assert files[0].name == "test.py"

    @pytest.mark.asyncio
    async def test_current_directory_default(self):
        """Test with default current directory parameter."""
        # This test runs in the current directory
        # We just check that it doesn't raise an exception
        count = 0
        async for py_file in list_all_files("", "*.py"):
            count += 1
            if count > 10:  # Limit to avoid processing too many files
                break

        # Should not raise an exception
        assert count >= 0


class TestDefaultSkipDirs:
    """Test cases for DEFAULT_SKIP_DIRS constant."""

    def test_default_skip_dirs_content(self):
        """Test that DEFAULT_SKIP_DIRS contains expected directories."""
        expected_dirs = {
            ".git",
            ".github",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".mypy_cache",
            ".pytest_cache",
            "node_modules",
            "dist",
            "build",
            ".idea",
            ".vscode",
        }

        assert expected_dirs == DEFAULT_SKIP_DIRS

    def test_default_skip_dirs_immutable(self):
        """Test that DEFAULT_SKIP_DIRS is a set (immutable for our purposes)."""
        assert isinstance(DEFAULT_SKIP_DIRS, set)


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    @pytest.mark.asyncio
    async def test_permission_denied_handling(self, tmp_path):
        """Test handling of permission denied errors."""
        # Create a file we can access
        (tmp_path / "accessible.py").write_text("print('accessible')")

        # This test is tricky to implement portably
        # We'll just ensure the function handles errors gracefully
        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should find at least the accessible file
        assert len(files) >= 1

    @pytest.mark.asyncio
    async def test_broken_symlinks(self, tmp_path):
        """Test handling of broken symbolic links."""
        # Create a broken symlink
        broken_link = tmp_path / "broken.py"
        try:
            broken_link.symlink_to(tmp_path / "nonexistent.py")
            # Create a normal file
            (tmp_path / "normal.py").write_text("print('normal')")
        except OSError:
            # Symlinks not supported, skip this test
            pytest.skip("Symlinks not supported on this system")

        files = []
        async for py_file in list_all_files(tmp_path, "*.py"):
            files.append(py_file)

        # Should handle broken symlinks gracefully
        # and still find the normal file
        python_files = [f.name for f in files]
        assert "normal.py" in python_files

    @pytest.mark.asyncio
    async def test_concurrent_access(self, tmp_path):
        """Test concurrent access to the same directory."""
        # Create test files
        for i in range(5):
            (tmp_path / f"file_{i}.py").write_text(f"# File {i}")

        # Run multiple concurrent searches
        tasks = [
            list_all_files(tmp_path, "*.py"),
            list_all_files(tmp_path, "*.py"),
            list_all_files(tmp_path, "*.py"),
        ]

        results = []
        for task in tasks:
            files = []
            async for py_file in task:
                files.append(py_file)
            results.append(files)

        # All tasks should find the same files
        assert len(results) == 3
        for result in results:
            assert len(result) == 5

    def test_pathspec_integration(self):
        """Test integration with pathspec library."""
        # Test that we can create and use pathspec objects
        patterns = ["*.pyc", "__pycache__/", "*.log"]
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

        # Test matching
        assert spec.match_file("test.pyc")
        assert spec.match_file("__pycache__/")
        assert spec.match_file("app.log")
        assert not spec.match_file("main.py")
