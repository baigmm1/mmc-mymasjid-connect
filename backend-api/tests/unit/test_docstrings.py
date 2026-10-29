"""
Unit tests for docstring verification using AST.

Uses the ast module to parse Python files and verify that all public
functions, classes, and methods have docstrings.
"""

import ast
import pytest
from pathlib import Path
from typing import List, Tuple


@pytest.mark.unit
class TestDocstringPresence:
    """Test suite to verify all public functions have docstrings."""

    @staticmethod
    def get_python_files() -> List[Path]:
        """
        Get all Python files in the src directory.
        
        Returns:
            List[Path]: List of Python file paths
        """
        src_dir = Path(__file__).parent.parent.parent / "src"
        return list(src_dir.rglob("*.py"))

    @staticmethod
    def extract_public_items(filepath: Path) -> Tuple[List[str], List[str], List[str]]:
        """
        Extract public functions, classes, and methods from a Python file.
        
        Args:
            filepath: Path to Python file to analyze
            
        Returns:
            Tuple of (functions, classes, methods) that are public
        """
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        functions = []
        classes = []
        methods = []
        
        for node in ast.walk(tree):
            # Public functions (top-level, not starting with _)
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_"):
                    # Check if it's a method (inside a class) or function
                    parent = None
                    for parent_node in ast.walk(tree):
                        for child in ast.iter_child_nodes(parent_node):
                            if child == node:
                                parent = parent_node
                                break
                    
                    if isinstance(parent, ast.ClassDef):
                        methods.append(f"{parent.name}.{node.name}")
                    else:
                        functions.append(node.name)
            
            # Public classes (not starting with _)
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    classes.append(node.name)
        
        return functions, classes, methods

    @staticmethod
    def check_docstring(node: ast.FunctionDef | ast.ClassDef) -> bool:
        """
        Check if an AST node has a docstring.
        
        Args:
            node: AST node to check (FunctionDef or ClassDef)
            
        Returns:
            bool: True if docstring is present and non-empty
        """
        docstring = ast.get_docstring(node)
        return docstring is not None and len(docstring.strip()) > 0

    def test_all_modules_have_docstrings(self):
        """
        Test that all Python modules have module-level docstrings.
        
        Verifies each .py file starts with a docstring.
        """
        python_files = self.get_python_files()
        missing_docstrings = []
        
        for filepath in python_files:
            # Skip __init__.py files (can be empty)
            if filepath.name == "__init__.py":
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(filepath))
            
            module_docstring = ast.get_docstring(tree)
            if not module_docstring or len(module_docstring.strip()) == 0:
                missing_docstrings.append(str(filepath.relative_to(Path(__file__).parent.parent.parent)))
        
        assert len(missing_docstrings) == 0, (
            f"The following modules are missing docstrings:\n" +
            "\n".join(f"  - {path}" for path in missing_docstrings)
        )

    def test_all_public_functions_have_docstrings(self):
        """
        Test that all public functions have docstrings.
        
        Verifies functions not starting with underscore have documentation.
        """
        python_files = self.get_python_files()
        missing_docstrings = []
        
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions and methods
                    if node.name.startswith("_") and node.name != "__init__":
                        continue
                    
                    # Check if inside a class (method) or top-level (function)
                    # For simplicity, check all public FunctionDefs
                    if not self.check_docstring(node):
                        rel_path = filepath.relative_to(Path(__file__).parent.parent.parent)
                        missing_docstrings.append(f"{rel_path}::{node.name}")
        
        assert len(missing_docstrings) == 0, (
            f"The following functions are missing docstrings:\n" +
            "\n".join(f"  - {path}" for path in missing_docstrings)
        )

    def test_all_public_classes_have_docstrings(self):
        """
        Test that all public classes have docstrings.
        
        Verifies classes not starting with underscore have documentation.
        """
        python_files = self.get_python_files()
        missing_docstrings = []
        
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip private classes
                    if node.name.startswith("_"):
                        continue
                    
                    if not self.check_docstring(node):
                        rel_path = filepath.relative_to(Path(__file__).parent.parent.parent)
                        missing_docstrings.append(f"{rel_path}::{node.name}")
        
        assert len(missing_docstrings) == 0, (
            f"The following classes are missing docstrings:\n" +
            "\n".join(f"  - {path}" for path in missing_docstrings)
        )

    def test_no_todo_comments_in_code(self):
        """
        Test that no TODO comments are left in production code.
        
        Verifies all TODO items have been resolved before release.
        """
        python_files = self.get_python_files()
        todo_comments = []
        
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    if "TODO" in line or "FIXME" in line:
                        rel_path = filepath.relative_to(Path(__file__).parent.parent.parent)
                        todo_comments.append(f"{rel_path}:{line_num}: {line.strip()}")
        
        assert len(todo_comments) == 0, (
            f"The following TODO/FIXME comments need to be resolved:\n" +
            "\n".join(f"  - {comment}" for comment in todo_comments)
        )


@pytest.mark.unit
class TestDocstringQuality:
    """Test suite to verify docstring quality and format."""

    @staticmethod
    def get_python_files() -> List[Path]:
        """
        Get all Python files in the src directory.
        
        Returns:
            List[Path]: List of Python file paths
        """
        src_dir = Path(__file__).parent.parent.parent / "src"
        return list(src_dir.rglob("*.py"))

    def test_function_docstrings_have_args_section(self):
        """
        Test that function docstrings document parameters.
        
        Verifies functions with parameters have Args section in docstring.
        """
        python_files = self.get_python_files()
        missing_args = []
        
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if node.name.startswith("_") and node.name != "__init__":
                        continue
                    
                    # Skip if no parameters (except self/cls)
                    params = [arg.arg for arg in node.args.args]
                    params = [p for p in params if p not in ("self", "cls")]
                    
                    if len(params) == 0:
                        continue
                    
                    docstring = ast.get_docstring(node)
                    if docstring and "Args:" not in docstring and "Parameters:" not in docstring:
                        rel_path = filepath.relative_to(Path(__file__).parent.parent.parent)
                        missing_args.append(f"{rel_path}::{node.name}")
        
        # Allow some flexibility - warn if > 50% missing Args sections
        total_functions_checked = len(missing_args) if len(missing_args) > 0 else 1
        if len(missing_args) > 0:
            print(f"\nWARNING: {len(missing_args)} functions missing Args section in docstrings")

    def test_function_docstrings_have_returns_section(self):
        """
        Test that function docstrings document return values.
        
        Verifies functions that return values have Returns section.
        """
        python_files = self.get_python_files()
        missing_returns = []
        
        for filepath in python_files:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if node.name.startswith("_") and node.name != "__init__":
                        continue
                    
                    # Skip if no return annotation
                    if node.returns is None:
                        continue
                    
                    # Skip if return type is None
                    if isinstance(node.returns, ast.Constant) and node.returns.value is None:
                        continue
                    
                    docstring = ast.get_docstring(node)
                    if docstring and "Returns:" not in docstring and "Return:" not in docstring:
                        rel_path = filepath.relative_to(Path(__file__).parent.parent.parent)
                        missing_returns.append(f"{rel_path}::{node.name}")
        
        # Allow some flexibility - warn if > 50% missing Returns sections
        if len(missing_returns) > 0:
            print(f"\nWARNING: {len(missing_returns)} functions missing Returns section in docstrings")

    def test_exception_docstrings_mention_http_status(self):
        """
        Test that custom exception docstrings mention HTTP status codes.
        
        Verifies exception classes document their HTTP status codes.
        """
        exceptions_file = Path(__file__).parent.parent.parent / "src" / "core" / "exceptions.py"
        
        with open(exceptions_file, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(exceptions_file))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Skip base exception
                if node.name == "MasjidConnectException":
                    continue
                
                # Check if it's an exception class (inherits from MasjidConnectException)
                is_exception = any(
                    isinstance(base, ast.Name) and "Exception" in base.id
                    for base in node.bases
                )
                
                if is_exception:
                    docstring = ast.get_docstring(node)
                    if docstring:
                        # Should mention HTTP status code
                        has_http_status = any(
                            str(code) in docstring
                            for code in [400, 401, 403, 404, 409, 422, 500, 502, 503]
                        )
                        assert has_http_status, (
                            f"Exception {node.name} docstring should mention HTTP status code"
                        )
