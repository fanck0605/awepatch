from __future__ import annotations

from awepatch.utils import _remove_source_indent  # type: ignore


def test_remove_source_indent_basic() -> None:
    """Test removing common indentation from code lines."""
    lines = [
        "    def foo():\n",
        "        return 42\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "def foo():\n",
        "    return 42\n",
    ]


def test_remove_source_indent_no_indent() -> None:
    """Test with lines that have no indentation."""
    lines = [
        "def foo():\n",
        "    return 42\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "def foo():\n",
        "    return 42\n",
    ]


def test_remove_source_indent_blank_lines() -> None:
    """Test that blank lines are replaced with newline character."""
    lines = [
        "    def foo():\n",
        "        pass\n",
        "    \n",  # Blank line with spaces less than indent
        "        return 42\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "def foo():\n",
        "    pass\n",
        "\n",
        "    return 42\n",
    ]


def test_remove_source_indent_short_blank_line() -> None:
    """Test blank line shorter than indent level."""
    lines = [
        "        def foo():\n",
        "  \n",  # Only 2 spaces, less than 8 space indent
        "            pass\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "def foo():\n",
        "\n",
        "    pass\n",
    ]


def test_remove_source_indent_empty_blank_line() -> None:
    """Test completely empty blank line."""
    lines = [
        "    def foo():\n",
        "\n",  # Empty line
        "        pass\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "def foo():\n",
        "\n",
        "    pass\n",
    ]


def test_remove_source_indent_single_line() -> None:
    """Test with a single line."""
    lines = ["    x = 1\n"]
    result = _remove_source_indent(lines)
    assert result == ["x = 1\n"]


def test_remove_source_indent_deeply_nested() -> None:
    """Test with deeply nested indentation."""
    lines = [
        "            if True:\n",
        "                if True:\n",
        "                    return 1\n",
    ]
    result = _remove_source_indent(lines)
    assert result == [
        "if True:\n",
        "    if True:\n",
        "        return 1\n",
    ]
