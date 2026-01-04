from __future__ import annotations

import ast

from awepatch.utils import load_stmts


def test_load_stmts_single_statement() -> None:
    """Test loading a single statement."""
    code = "x = 1"
    stmts = load_stmts(code)
    assert len(stmts) == 1
    assert isinstance(stmts[0], ast.Assign)


def test_load_stmts_multiple_statements() -> None:
    """Test loading multiple statements."""
    code = "x = 1\ny = 2\nz = 3"
    stmts = load_stmts(code)
    assert len(stmts) == 3
    assert all(isinstance(stmt, ast.Assign) for stmt in stmts)


def test_load_stmts_complex_statements() -> None:
    """Test loading complex statements."""
    code = """
if x > 0:
    y = 1
else:
    y = 2
"""
    stmts = load_stmts(code)
    assert len(stmts) == 1
    assert isinstance(stmts[0], ast.If)


def test_load_stmts_with_imports() -> None:
    """Test loading import statements."""
    code = "import os\nfrom pathlib import Path"
    stmts = load_stmts(code)
    assert len(stmts) == 2
    assert isinstance(stmts[0], ast.Import)
    assert isinstance(stmts[1], ast.ImportFrom)


def test_load_stmts_with_function_def() -> None:
    """Test loading function definition."""
    code = """
def foo(x):
    return x * 2
"""
    stmts = load_stmts(code)
    assert len(stmts) == 1
    assert isinstance(stmts[0], ast.FunctionDef)
    assert stmts[0].name == "foo"


def test_load_stmts_with_class_def() -> None:
    """Test loading class definition."""
    code = """
class MyClass:
    def __init__(self):
        pass
"""
    stmts = load_stmts(code)
    assert len(stmts) == 1
    assert isinstance(stmts[0], ast.ClassDef)
    assert stmts[0].name == "MyClass"


def test_load_stmts_empty_code() -> None:
    """Test loading empty code returns empty list."""
    code = ""
    stmts = load_stmts(code)
    assert len(stmts) == 0


def test_load_stmts_only_whitespace() -> None:
    """Test loading code with only whitespace."""
    code = "   \n\n   "
    stmts = load_stmts(code)
    assert len(stmts) == 0


def test_load_stmts_with_comments() -> None:
    """Test that comments are ignored when loading statements."""
    code = """
# This is a comment
x = 1  # Inline comment
# Another comment
y = 2
"""
    stmts = load_stmts(code)
    # Comments are not statements
    assert len(stmts) == 2
    assert all(isinstance(stmt, ast.Assign) for stmt in stmts)
