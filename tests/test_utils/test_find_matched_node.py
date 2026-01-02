from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import pytest

from awepatch.utils import _find_matched_node  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_find_matched_node_exact_string_match() -> None:
    """Test finding a node by exact string match."""
    source = [
        "def foo():\n",
        "    x = 1\n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    tree = ast.parse("".join(source))
    matched = _find_matched_node(tree.body[0], source, ("x = 1",))
    assert matched is not None
    assert ast.unparse(getattr(matched[0], matched[1])[matched[2]]) == "x = 1"


def test_find_matched_node_in_nested_block() -> None:
    """Test finding a node inside a nested control flow block."""

    source_code: str = """def example_function(x):
    if x > 0:
        x = x * 3
    x = x * 2
    return x
"""

    tree = ast.parse(source_code)
    target = ("x = x * 3",)
    source_lines: Sequence[str] = source_code.splitlines(keepends=True)

    matched = _find_matched_node(
        tree.body[0],
        source_lines,
        target,
    )

    assert matched is not None
    assert ast.unparse(getattr(matched[0], matched[1])[matched[2]]) == "x = x * 3"


def test_find_matched_node_with_context() -> None:
    """Test disambiguating duplicate patterns using context lines."""

    source_code: str = """def example_function(x):
    if x > 0:
        x = x * 2
    x = x * 2
    return x
"""

    tree = ast.parse(source_code)

    target = ("if x > 0:", "x = x * 2")

    source_lines: Sequence[str] = source_code.splitlines(keepends=True)
    matched = _find_matched_node(
        tree.body[0],
        source_lines,
        target,
    )

    assert matched is not None
    assert ast.unparse(matched[0]) == "if x > 0:\n    x = x * 2"
    assert ast.unparse(getattr(matched[0], matched[1])[matched[2]]) == "x = x * 2"


def test_find_matched_node_raises_on_ambiguous_match() -> None:
    """Test that multiple matches raise ValueError when no context is provided."""

    source_code: str = """def example_function(x):
    if x > 0:
        x = x * 2
    x = x * 2
    return x
"""

    tree = ast.parse(source_code)
    target = ("x = x * 2",)
    source_lines: Sequence[str] = source_code.splitlines(keepends=True)

    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):
        _find_matched_node(
            tree.body[0],
            source_lines,
            target,
        )


def test_find_matched_node_regex_pattern() -> None:
    """Test finding a node using a compiled regex pattern."""
    source = [
        "def foo():\n",
        "    x = 1\n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    pattern = re.compile(r"x = \d+")
    tree = ast.parse("".join(source))
    matched = _find_matched_node(tree.body[0], source, (pattern,))
    assert matched is not None
    assert ast.unparse(getattr(matched[0], matched[1])[matched[2]]) == "x = 1"


def test_find_matched_node_ignores_trailing_whitespace() -> None:
    """Test that matching ignores trailing whitespace in source lines."""
    source = [
        "def foo():\n",
        "    x = 1    \n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    tree = ast.parse("".join(source))
    matched = _find_matched_node(tree.body[0], source, ("x = 1",))
    assert matched is not None
    assert ast.unparse(getattr(matched[0], matched[1])[matched[2]]) == "x = 1"


def test_find_matched_node_returns_none_when_not_found() -> None:
    """Test that None is returned when the pattern doesn't match any node."""
    source = [
        "def foo():\n",
        "    x = 1\n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    tree = ast.parse("".join(source))
    matched = _find_matched_node(tree.body[0], source, ("z = 3",))
    assert matched is None


def test_find_matched_node_raises_on_duplicate_lines() -> None:
    """Test that identical duplicate lines raise ValueError without context."""
    source = [
        "def foo():\n",
        "    x = 1\n",
        "    x = 1\n",
        "    return x\n",
    ]
    tree = ast.parse("".join(source))
    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):
        _find_matched_node(tree.body[0], source, ("x = 1",))


def test_find_matched_node_complex_regex_pattern() -> None:
    """Test finding a node using a complex regex with multiple groups."""
    source = [
        "def foo():\n",
        "    result = calculate(10, 20, 30)\n",
        "    return result\n",
    ]
    tree = ast.parse("".join(source))
    pattern = re.compile(r"result = calculate\(\d+,\s*\d+,\s*\d+\)")
    matched = _find_matched_node(tree.body[0], source, (pattern,))
    assert matched is not None
    assert (
        ast.unparse(getattr(matched[0], matched[1])[matched[2]])
        == "result = calculate(10, 20, 30)"
    )


def test_find_matched_node_case_sensitive_matching() -> None:
    """Test that pattern matching is case-sensitive."""
    source = [
        "def foo():\n",
        "    X = 1\n",
        "    return X\n",
    ]
    tree = ast.parse("".join(source))
    matched = _find_matched_node(tree.body[0], source, ("x = 1",))
    assert matched is None
