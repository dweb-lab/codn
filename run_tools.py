from typing import Optional, List
import asyncio
import sys
import os
from loguru import logger

from codn.utils.base_lsp_client import (
    get_snippets,
    get_snippets_by_line_nums,
    traverse,
    get_filenames_by_pattern,
)


def formatter(record):
    relpath = os.path.relpath(record["file"].path)
    return (
        f"<green>{record['time']:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        f"<level>{record['level'].name:<8}</level> | "
        f"<cyan>{relpath}:{record['line']}</cyan> "
        f"<magenta>{record['function']}</magenta> - "
        f"{record['message']}\n"
    )


logger.remove()
logger.add(sys.stderr, format=formatter, level="DEBUG", colorize=True)


def search_code_snippets(
    search_terms: Optional[List[str]] = None,
    line_nums: Optional[List] = None,
    file_path_or_pattern: Optional[str] = "**/*.py",
) -> str:
    """Searches the codebase to retrieve relevant code snippets based on given
    queries(terms or line numbers).

    This function supports retrieving the complete content of a code entity,
    searching for code entities such as classes or functions by keywords, or locating specific lines within a file.
    It also supports filtering searches based on a file path or file pattern.

    Note:
    1. If `search_terms` are provided, it searches for code snippets based on each term:
        - If a term is formatted as 'file_path:QualifiedName' (e.g., 'src/helpers/math_helpers.py:MathUtils.calculate_sum') ,
          or just 'file_path', the corresponding complete code is retrieved or file content is retrieved.
        - If a term matches a file, class, or function name, matched entities are retrieved.
        - If there is no match with any module name, it attempts to find code snippets that likely contain the term.

    2. If `line_nums` is provided, it searches for code snippets at the specified lines within the file defined by
       `file_path_or_pattern`.

    Args:
        search_terms (Optional[List[str]]): A list of names, keywords, or code snippets to search for within the codebase.
            Terms can be formatted as 'file_path:QualifiedName' to search for a specific module or entity within a file
            (e.g., 'src/helpers/math_helpers.py:MathUtils.calculate_sum') or as 'file_path' to retrieve the complete content
            of a file. This can also include potential function names, class names, or general code fragments.

        line_nums (Optional[List[int]]): Specific line numbers to locate code snippets within a specified file.
            When provided, `file_path_or_pattern` must specify a valid file path.

        file_path_or_pattern (Optional[str]): A glob pattern or specific file path used to filter search results
            to particular files or directories. Defaults to '**/*.py', meaning all Python files are searched by default.
            If `line_nums` are provided, this must specify a specific file path.

    Returns:
        str: The search results, which may include code snippets, matching entities, or complete file content.


    Example Usage:
        # Search for the full content of a specific file
        result = search_code_snippets(search_terms=['src/my_file.py'])

        # Search for a specific function
        result = search_code_snippets(search_terms=['src/my_file.py:MyClass.func_name'])

        # Search for specific lines (10 and 15) within a file
        result = search_code_snippets(line_nums=[10, 15], file_path_or_pattern='src/example.py')

        # Combined search for a module name and within a specific file pattern
        result = search_code_snippets(search_terms=["MyClass"], file_path_or_pattern="src/**/*.py")
    """

    path = "."
    if search_terms:
        results = asyncio.run(get_snippets(search_terms, str(path)))
        for result in results:
            print("=" * 88)
            print(result)
    elif line_nums and file_path_or_pattern and "*" not in file_path_or_pattern:
        results = asyncio.run(
            get_snippets_by_line_nums(
                line_nums=line_nums, file_path_or_pattern=file_path_or_pattern
            )
        )
        for result in results:
            print("=" * 88)
            print(result)
    elif not search_terms and not line_nums and file_path_or_pattern:
        results = asyncio.run(get_filenames_by_pattern(pattern=file_path_or_pattern))
        for result in results:
            print("=" * 88)
            print(result)

    return ""


def explore_tree_structure(
    start_entities: List[str],
    direction: str = "downstream",
    traversal_depth: int = 2,
    entity_type_filter: Optional[List[str]] = None,
    dependency_type_filter: Optional[List[str]] = None,
):
    """Analyzes and displays the dependency structure around specified entities in a
    code graph.

    This function searches and presents relationships and dependencies for the specified entities (such as classes, functions, files, or directories) in a code graph.
    It explores how the input entities relate to others, using defined types of dependencies, including 'contains', 'imports', 'invokes' and 'inherits'.
    The search can be controlled to traverse upstream (exploring dependencies that entities rely on) or downstream (exploring how entities impact others), with optional limits on traversal depth and filters for entity and dependency types.

    Example Usage:
    1. Exploring Outward Dependencies:
        ```
        explore_tree_structure(
            start_entities=['src/module_a.py:ClassA'],
            direction='downstream',
            traversal_depth=2,
            entity_type_filter=['class', 'function'],
            dependency_type_filter=['invokes', 'imports']
        )
        ```
        This retrieves the dependencies of `ClassA` up to 2 levels deep, focusing only on classes and functions with 'invokes' and 'imports' relationships.

    2. Exploring Inward Dependencies:
        ```
        explore_tree_structure(
            start_entities=['src/module_b.py:FunctionY'],
            direction='upstream',
            traversal_depth=-1
        )
        ```
        This finds all entities that depend on `FunctionY` without restricting the traversal depth.

    Notes:
    * Traversal Control: The `traversal_depth` parameter specifies how deep the function should explore the graph starting from the input entities.
    * Filtering: Use `entity_type_filter` and `dependency_type_filter` to narrow down the scope of the search, focusing on specific entity types and relationships.
    * Graph Context: The function operates on a pre-built code graph containing entities (e.g., files, classes and functions) and dependencies representing their interactions and relationships.

    Parameters:
    ----------
    start_entities : list[str]
        List of entities (e.g., class, function, file, or directory paths) to begin the search from.
        - Entities representing classes or functions must be formatted as "file_path:QualifiedName"
          (e.g., `interface/C.py:C.method_a.inner_func`).
        - For files or directories, provide only the file or directory path (e.g., `src/module_a.py` or `src/`).

    direction : str, optional
        Direction of traversal in the code graph; allowed options are:
        - 'upstream': Traversal to explore dependencies that the specified entities rely on (how they depend on others).
        - 'downstream': Traversal to explore the effects or interactions of the specified entities on others
          (how others depend on them).
        - 'both': Traversal in both directions.
        Default is 'downstream'.

    traversal_depth : int, optional
        Maximum depth of traversal. A value of -1 indicates unlimited depth (subject to a maximum limit).
        Must be either `-1` or a non-negative integer (≥ 0).
        Default is 2.

    entity_type_filter : list[str], optional
        List of entity types (e.g., 'class', 'function', 'file', 'directory') to include in the traversal.
        If None, all entity types are included.
        Default is None.

    dependency_type_filter : list[str], optional
        List of dependency types (e.g., 'contains', 'imports', 'invokes', 'inherits') to include in the traversal.
        If None, all dependency types are included.
        Default is None.

    Returns:
    -------
    result : object
        An object representing the traversal results, which includes discovered entities and their dependencies.
    """

    entity_type_filter = entity_type_filter or [
        "class",
        "function",
        "file",
        "directory",
    ]
    dependency_type_filter = dependency_type_filter or [
        "contains",
        "imports",
        "invokes",
        "inherits",
    ]

    # Perform the traversal
    results = asyncio.run(
        traverse(
            start_entities,
            entity_type_filter,
            dependency_type_filter,
            direction,
            traversal_depth,
        )
    )

    for result in results:
        print("=" * 88)
        print(result)

    return results


if 1:
    file_name = "codn/utils/base_lsp_client.py"
    entity_name = "send_did_open"
    search_code_snippets(search_terms=[file_name])
    search_code_snippets(search_terms=[entity_name])

    entity_name = "codn/utils/base_lsp_client.py:BaseLSPClient.send_did_open"
    search_code_snippets(search_terms=[entity_name])

    start = 1
    end = 10
    line_nums = [start - 1, end]
    # search_code_snippets(line_nums=line_nums, file_path_or_pattern=file_name)


if 1:
    # entity = "codn/utils/base_lsp_client.py:BaseLSPClient"
    entity = "BaseLSPClient"
    results = explore_tree_structure(
        start_entities=[entity],
        direction="downstream",
        traversal_depth=20,
        entity_type_filter=["class", "function"],
        dependency_type_filter=["invokes", "imports"],
    )
    # print(results)


entity_name = "send_did_open"
file_path_or_pattern = "codn/**/*.py"
search_code_snippets(
    search_terms=[entity_name], file_path_or_pattern=file_path_or_pattern
)

file_path_or_pattern = "codn/**/*.py"
search_code_snippets(file_path_or_pattern=file_path_or_pattern)
