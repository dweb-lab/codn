import ast
from typing import Optional, List, Tuple, Union


def find_enclosing_function(content: str, line: int, character: int) -> Optional[str]:
    """
    Find the name of the function or method that contains the given position.

    Args:
        content: Python source code
        line: Line number (0-based)
        character: Character position (0-based, unused but kept for compatibility)

    Returns:
        Function name if position is inside a function, None otherwise
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    # Try to add end_lineno information if asttokens is available
    try:
        import asttokens  # type: ignore
        asttokens.ASTTokens(content, tree=tree)
    except ImportError:
        pass

    enclosing_functions: List[str] = []

    class FunctionVisitor(ast.NodeVisitor):
        """Visitor to find functions containing the target line."""

        def _check_function_node(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None:
            """Check if a function node contains the target line."""
            start_line = getattr(node, 'lineno', None)
            end_line = getattr(node, 'end_lineno', None)

            if start_line is not None:
                # Convert to 0-based indexing for comparison
                start_line_0based = start_line - 1

                if end_line is not None:
                    # If end_lineno is available, use precise range check
                    end_line_0based = end_line - 1
                    if start_line_0based <= line <= end_line_0based:
                        enclosing_functions.append(node.name)
                else:
                    # Fallback: estimate end line based on function body
                    estimated_end_line = self._estimate_function_end(node)
                    if start_line_0based <= line <= estimated_end_line:
                        enclosing_functions.append(node.name)

            self.generic_visit(node)

        def _estimate_function_end(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int:
            """Estimate the end line of a function when end_lineno is not available."""
            if not node.body:
                return getattr(node, 'lineno', 1) - 1

            # Find the maximum line number among all statements in the function body
            max_line = getattr(node, 'lineno', 1)
            for stmt in node.body:
                if hasattr(stmt, 'lineno') and stmt.lineno:
                    max_line = max(max_line, stmt.lineno)
                # Also check nested nodes within each statement
                for child in ast.walk(stmt):
                    if hasattr(child, 'lineno') and child.lineno:
                        max_line = max(max_line, child.lineno)

            return max_line - 1  # Convert to 0-based

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._check_function_node(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._check_function_node(node)

    visitor = FunctionVisitor()
    visitor.visit(tree)

    # Return the innermost function (last in the list)
    return enclosing_functions[-1] if enclosing_functions else None


def extract_inheritance_relations(content: str) -> List[Tuple[str, str]]:
    """
    Extract class inheritance relationships from Python source code.

    Args:
        content: Python source code

    Returns:
        List of tuples (child_class, parent_class)
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    relations: List[Tuple[str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            child_name = node.name

            for base in node.bases:
                parent_name = _extract_base_name(base)
                if parent_name:
                    relations.append((child_name, parent_name))

    return relations


def _extract_base_name(base: ast.expr) -> Optional[str]:
    """
    Extract the name of a base class from an AST node.

    Args:
        base: AST node representing a base class

    Returns:
        Base class name or None if it cannot be determined
    """
    if isinstance(base, ast.Name):
        return base.id
    elif isinstance(base, ast.Attribute):
        # Handle cases like module.BaseClass
        value_name = _extract_base_name(base.value)
        if value_name:
            return f"{value_name}.{base.attr}"
        return base.attr
    return None
