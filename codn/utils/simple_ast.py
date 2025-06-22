import ast
from typing import Dict, List, Optional, Tuple, Union

try:
    import asttokens  # type: ignore[import-untyped]
except ImportError:
    asttokens = None


def find_enclosing_function(content: str, line: int, _character: int) -> Optional[str]:
    """Find the name of the function or method that contains the given position.

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
    if asttokens is not None:
        asttokens.ASTTokens(content, tree=tree)

    enclosing_functions: List[str] = []

    class FunctionVisitor(ast.NodeVisitor):
        """Visitor to find functions containing the target line."""

        def _check_function_node(
            self,
            node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        ) -> None:
            """Check if a function node contains the target line."""
            start_line = getattr(node, "lineno", None)
            end_line = getattr(node, "end_lineno", None)

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

        def _estimate_function_end(
            self,
            node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        ) -> int:
            """Estimate the end line of a function when end_lineno is not available."""
            if not node.body:
                return getattr(node, "lineno", 1) - 1

            # Find the maximum line number among all statements in the function body
            max_line = getattr(node, "lineno", 1)
            for stmt in node.body:
                if hasattr(stmt, "lineno") and stmt.lineno:
                    max_line = max(max_line, stmt.lineno)
                # Also check nested nodes within each statement
                for child in ast.walk(stmt):
                    if hasattr(child, "lineno") and child.lineno:
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
    """Extract class inheritance relationships from Python source code.

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
    """Extract the name of a base class from an AST node.

    Args:
        base: AST node representing a base class

    Returns:
        Base class name or None if it cannot be determined
    """
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        # Handle cases like module.BaseClass
        value_name = _extract_base_name(base.value)
        if value_name:
            return f"{value_name}.{base.attr}"
        return base.attr
    return None


def find_function_references(content: str, function_name: str) -> List[Tuple[int, int]]:
    """Find all references to a function in the given content.

    Args:
        content: Python source code
        function_name: Name of the function to find references for

    Returns:
        List of tuples (line_number, column_offset) where the function is referenced
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    references = []

    class ReferenceVisitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if node.id == function_name and isinstance(node.ctx, ast.Load):
                references.append((node.lineno, node.col_offset))
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == function_name:
                references.append((node.lineno, node.col_offset))
            self.generic_visit(node)

    visitor = ReferenceVisitor()
    visitor.visit(tree)
    return references


def extract_function_signatures(
    content: str,
) -> List[Dict[str, object]]:
    """Extract function signatures from Python source code.

    Args:
        content: Python source code

    Returns:
        List of dictionaries containing function information
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    functions = []

    class FunctionVisitor(ast.NodeVisitor):
        def _extract_function_info(
            self,
            node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        ) -> None:
            args: list[str] = []
            defaults = []

            # Extract argument names
            args.extend(arg.arg for arg in node.args.args)

            # Extract default values
            for default in node.args.defaults:
                if isinstance(default, ast.Constant):
                    if isinstance(default.value, str):
                        defaults.append(f"'{default.value}'")
                    else:
                        defaults.append(str(default.value))
                elif isinstance(default, ast.Name):
                    defaults.append(default.id)
                else:
                    defaults.append("...")

            # Extract return type annotation if present
            return_type = None
            if node.returns:
                if isinstance(node.returns, ast.Name):
                    return_type = node.returns.id
                elif isinstance(node.returns, ast.Constant):
                    return_type = str(node.returns.value)

            function_info = {
                "name": node.name,
                "line": node.lineno,
                "args": args,
                "defaults": defaults,
                "return_type": return_type,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "docstring": ast.get_docstring(node),
            }

            functions.append(function_info)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._extract_function_info(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._extract_function_info(node)

    visitor = FunctionVisitor()
    visitor.visit(tree)
    return functions


def find_unused_imports(content: str) -> List[Tuple[str, int]]:
    """Find unused imports in Python source code.

    Args:
        content: Python source code

    Returns:
        List of tuples (import_name, line_number) for unused imports
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    imported_names = set()
    used_names = set()

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names.add((name, node.lineno))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names.add((name, node.lineno))

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            # Handle module.attribute usage
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
            self.generic_visit(node)

    visitor = ImportVisitor()
    visitor.visit(tree)

    unused_imports = []
    for name, line in imported_names:
        if name not in used_names:
            unused_imports.append((name, line))

    return unused_imports


def extract_class_methods(
    content: str,
    class_name: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Extract methods from classes in Python source code.

    Args:
        content: Python source code
        class_name: Optional specific class name to extract methods from

    Returns:
        List of dictionaries containing method information
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    methods = []

    class ClassVisitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if class_name is None or node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_info = {
                            "class_name": node.name,
                            "method_name": item.name,
                            "line": item.lineno,
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                            "is_classmethod": any(
                                isinstance(d, ast.Name) and d.id == "classmethod"
                                for d in item.decorator_list
                            ),
                            "is_staticmethod": any(
                                isinstance(d, ast.Name) and d.id == "staticmethod"
                                for d in item.decorator_list
                            ),
                            "is_property": any(
                                isinstance(d, ast.Name) and d.id == "property"
                                for d in item.decorator_list
                            ),
                            "docstring": ast.get_docstring(item),
                        }
                        methods.append(method_info)
            self.generic_visit(node)

    visitor = ClassVisitor()
    visitor.visit(tree)
    return methods
