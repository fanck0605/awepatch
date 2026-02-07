from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import pytest

from awepatch._utils import CompiledIdent, find_matched_node

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_find_matched_node_exact_string_match() -> None:
    """Test finding a node by exact string match."""
    source = r"""def foo():
    x = 1
    y = 2
    return x + y
"""

    tree = ast.parse(source)
    slines = source.splitlines(keepends=True)
    target = (CompiledIdent("x = 1"),)

    matched = find_matched_node(tree.body[0], slines, target)
    assert matched == ("body", 0)


def test_find_matched_node_regex_pattern() -> None:
    """Test finding a node using a compiled regex pattern."""

    source = r"""def foo():
    x = 1
    y = 2
    return x + y
"""

    tree = ast.parse(source)
    slines = source.splitlines(keepends=True)
    target = (CompiledIdent(re.compile(r"x = \d+")),)

    matched = find_matched_node(tree.body[0], slines, target)
    assert matched == ("body", 0)


def test_find_matched_node_in_nested_block() -> None:
    """Test finding a node inside a nested control flow block."""

    source: str = """def example_function(x):
    if x > 0:
        x = x * 3
    x = x * 2
    return x
"""

    tree = ast.parse(source)
    slines: Sequence[str] = source.splitlines(keepends=True)
    target = (CompiledIdent("x = x * 3"),)

    matched = find_matched_node(tree.body[0], slines, target)
    assert matched == ("body", 0, "body", 0)


def test_find_matched_node_with_context() -> None:
    """Test disambiguating duplicate patterns using context lines."""

    source: str = """def example_function(x):
    if x > 0:
        x = x * 2
    x = x * 2
    return x
"""

    tree = ast.parse(source)
    slines: Sequence[str] = source.splitlines(keepends=True)
    target = (CompiledIdent("if x > 0:"), CompiledIdent("x = x * 2"))

    matched = find_matched_node(tree.body[0], slines, target)
    assert matched == ("body", 0, "body", 0)


def test_find_matched_node_raises_on_ambiguous_match() -> None:
    """Test that multiple matches raise ValueError when no context is provided."""

    source: str = """def example_function(x):
    if x > 0:
        x = x * 2
    x = x * 2
    return x
"""

    tree = ast.parse(source)
    slines: Sequence[str] = source.splitlines(keepends=True)
    target = (CompiledIdent("x = x * 2"),)

    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):
        find_matched_node(tree.body[0], slines, target)


def test_find_matched_node_ignores_trailing_whitespace() -> None:
    """Test that matching ignores trailing whitespace in source lines."""
    slines = [
        "def foo():\n",
        "    x = 1    \n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    tree = ast.parse("".join(slines))
    matched = find_matched_node(tree.body[0], slines, (CompiledIdent("x = 1"),))
    assert matched == ("body", 0)


def test_find_matched_node_returns_none_when_not_found() -> None:
    """Test that None is returned when the pattern doesn't match any node."""
    slines = [
        "def foo():\n",
        "    x = 1\n",
        "    y = 2\n",
        "    return x + y\n",
    ]
    tree = ast.parse("".join(slines))
    matched = find_matched_node(tree.body[0], slines, (CompiledIdent("z = 3"),))
    assert matched is None


def test_find_matched_node_raises_on_duplicate_lines() -> None:
    """Test that identical duplicate lines raise ValueError without context."""
    slines = [
        "def foo():\n",
        "    x = 1\n",
        "    x = 1\n",
        "    return x\n",
    ]
    tree = ast.parse("".join(slines))
    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):
        find_matched_node(tree.body[0], slines, (CompiledIdent("x = 1"),))


def test_find_matched_node_case_sensitive_matching() -> None:
    """Test that pattern matching is case-sensitive."""
    slines = [
        "def foo():\n",
        "    X = 1\n",
        "    return X\n",
    ]
    tree = ast.parse("".join(slines))
    matched = find_matched_node(tree.body[0], slines, (CompiledIdent("x = 1"),))
    assert matched is None
