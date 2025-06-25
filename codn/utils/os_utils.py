from pathlib import Path
from typing import AsyncGenerator, Optional, Set, Union, List, Generator
import pathspec
from collections import Counter, OrderedDict
import asyncio
from itertools import chain

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


# 映射常见文件扩展名到语言类型
LANG_TO_LANGUAGE = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "java": "java",
    "cpp": "cpp",
    "c": "c",
    "cs": "csharp",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "rs": "rust",
    "swift": "swift",
    "kt": "kotlin",
    "m": "objective-c",
    "sh": "shell",
    "html": "html",
    "css": "css",
    "lua": "lua",
    "json": "json",
    "xml": "xml",
    "yml": "yaml",
    "yaml": "yaml",
}


EXTENSION_TO_LANGUAGE_FULL = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".rs": "Rust",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".m": "Objective-C",
    ".sh": "Shell",
    ".html": "HTML",
    ".css": "CSS",
    ".lua": "Lua",
    ".json": "JSON",
    ".xml": "XML",
    ".yml": "YAML",
    ".yaml": "YAML",
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


async def list_all_files(
    root: Union[str, Path] = ".",
    pattern: str = "*",
    ignored_dirs: Optional[Set[str]] = None,
) -> AsyncGenerator[Path, None]:
    """Asynchronously yield all files in the directory tree.

    Args:
        root: Root directory to start searching from
        ignored_dirs: Set of directory names to ignore

    Yields:
        Path objects for files that should not be ignored
    """
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_SKIP_DIRS

    root_path = Path(root).resolve()
    gitignore_spec = load_gitignore(root_path)

    if "," not in pattern:
        for _file in root_path.rglob(pattern):
            if not should_ignore(_file, root_path, ignored_dirs, gitignore_spec):
                yield _file

    else:
        patterns = pattern.split(",")
        for _file in chain.from_iterable(root_path.rglob(p) for p in patterns):
            if not should_ignore(_file, root_path, ignored_dirs, gitignore_spec):
                yield _file


def list_all_files_sync(
    root: Union[str, Path] = ".",
    pattern: str = "*",
    ignored_dirs: Optional[Set[str]] = None,
) -> list[Path]:
    return [f for f in gen_all_files_sync(root, pattern, ignored_dirs)]


def gen_all_files_sync(
    root: Union[str, Path] = ".",
    pattern: str = "*",
    ignored_dirs: Optional[Set[str]] = None,
) -> Generator[Path, None, None]:
    """同步版本，遍历目录树，生成符合条件的文件路径。

    Args:
        root: 起始目录
        pattern: 文件匹配模式，默认为 "*"
        ignored_dirs: 需要忽略的目录名集合

    Yields:
        Path: 不被忽略的文件路径
    """
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_SKIP_DIRS

    root_path = Path(root).resolve()
    gitignore_spec = load_gitignore(root_path)

    for _file in root_path.rglob(pattern):
        if not should_ignore(_file, root_path, ignored_dirs, gitignore_spec):
            yield _file


def detect_dominant_languages(
    root: Union[str, Path] = ".",
    ignored_dirs: Optional[Set[str]] = None,
    top_n: int = 1,
) -> List[str]:
    """检测目录中使用频率最高的语言类型列表（可能有多个并列）

    Args:
        root: 要分析的根目录
        ignored_dirs: 要忽略的子目录名称集合
        top_n: 返回前N种语言（频率相同则并列）

    Returns:
        最常出现的语言类型名称列表
    """
    counter: Counter[str] = Counter()

    for file_path in gen_all_files_sync(root=root, ignored_dirs=ignored_dirs):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in EXTENSION_TO_LANGUAGE_FULL:
                lang = ext[1:]
                counter[lang] += 1

    if not counter:
        return []

    most_common = counter.most_common()
    if top_n == 1:
        max_count = most_common[0][1]
        return [lang for lang, count in most_common if count == max_count]
    else:
        return [lang for lang, _ in most_common[:top_n]]


async def group_files_by_dominant_language(
    root: Union[str, Path] = ".", ignored_dirs: Optional[Set[str]] = None
) -> OrderedDict[str, list[Path]]:
    """返回一个有序字典，键是最高频语言，值是该语言下的所有文件路径。

    Args:
        root: 要分析的代码根目录
        ignored_dirs: 要忽略的目录名集合

    Returns:
        OrderedDict[str, List[Path]]: 最高频语言及对应的文件路径列表
    """
    lang_counter: Counter[str] = Counter()
    file_lang_map = []

    async for file_path in list_all_files(root=root, ignored_dirs=ignored_dirs):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            lang = EXTENSION_TO_LANGUAGE_FULL.get(ext)
            if lang:
                lang_counter[lang] += 1
                file_lang_map.append((file_path, lang))

    if not lang_counter:
        return OrderedDict()

    max_count = max(lang_counter.values())
    dominant_langs = [
        lang for lang, count in lang_counter.items() if count == max_count
    ]

    # 按语言分组文件
    result = OrderedDict()
    for lang in dominant_langs:
        result[lang] = [fp for fp, alang in file_lang_map if alang == lang]

    return result


def get_dominant_language_file_groups(
    root: Union[str, Path] = ".", ignored_dirs: Optional[Set[str]] = None
) -> OrderedDict[str, list[Path]]:
    """同步版本：返回最高频语言及对应的文件路径（有序）

    Returns:
        OrderedDict[str, List[Path]]
    """
    try:
        loop = asyncio.get_running_loop()
        coro = group_files_by_dominant_language(root, ignored_dirs)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(group_files_by_dominant_language(root, ignored_dirs))


async def test() -> None:
    """Test function to demonstrate usage."""
    async for _file in list_all_files():
        print(_file)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
