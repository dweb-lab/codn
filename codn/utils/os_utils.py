from pathlib import Path
from typing import AsyncGenerator, Optional, Set, Union

import pathspec

# Common directories to skip during file traversal
DEFAULT_SKIP_DIRS = {
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


def load_gitignore(root_path: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns from the root directory."""
    gitignore_path = root_path / ".gitignore"

    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    try:
        patterns = gitignore_path.read_text(encoding="utf-8").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    except (OSError, UnicodeDecodeError):
        return pathspec.PathSpec.from_lines("gitwildmatch", [])


def should_ignore(
    file_path: Path,
    root_path: Path,
    ignored_dirs: Set[str],
    gitignore_spec: pathspec.PathSpec,
) -> bool:
    """Check if a file should be ignored based on directory names and gitignore
    patterns.

    Args:
        file_path: The file path to check
        root_path: The root directory path
        ignored_dirs: Set of directory names to ignore
        gitignore_spec: Gitignore pattern specification

    Returns:
        True if the file should be ignored, False otherwise
    """
    # Check if any parent directory should be ignored
    if any(part in ignored_dirs for part in file_path.parts):
        return True

    # Check gitignore patterns using relative path
    try:
        relative_path = file_path.relative_to(root_path)
        return gitignore_spec.match_file(str(relative_path))
    except ValueError:
        # file_path is not relative to root_path
        return True


def list_all_python_files_sync(
    root: Union[str, Path] = ".",
    ignored_dirs: Optional[Set[str]] = None,
) -> list[Path]:
    """Synchronously return all Python files in the directory tree.

    Args:
        root: Root directory to start searching from
        ignored_dirs: Set of directory names to ignore

    Returns:
        List of Path objects for Python files that should not be ignored
    """
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_SKIP_DIRS

    root_path = Path(root).resolve()
    gitignore_spec = load_gitignore(root_path)

    python_files = [
        py_file
        for py_file in root_path.rglob("*.py")
        if not should_ignore(py_file, root_path, ignored_dirs, gitignore_spec)
    ]

    return python_files


async def list_all_python_files(
    root: Union[str, Path] = ".",
    ignored_dirs: Optional[Set[str]] = None,
) -> AsyncGenerator[Path, None]:
    """Asynchronously yield all Python files in the directory tree.

    Args:
        root: Root directory to start searching from
        ignored_dirs: Set of directory names to ignore

    Yields:
        Path objects for Python files that should not be ignored
    """
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_SKIP_DIRS

    root_path = Path(root).resolve()
    gitignore_spec = load_gitignore(root_path)

    for py_file in root_path.rglob("*.py"):
        if not should_ignore(py_file, root_path, ignored_dirs, gitignore_spec):
            yield py_file


async def test() -> None:
    """Test function to demonstrate usage."""
    async for py_file in list_all_python_files():
        print(py_file)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
