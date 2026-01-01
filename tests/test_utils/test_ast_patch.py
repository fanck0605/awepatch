from __future__ import annotations

import ast
import re

import pytest

from awepatch.utils import ast_patch


def test_ast_patch_function() -> None:
    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 10", "x = x + 20", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 20
    return x"""
    )


def test_ast_patch_one_line_decorator() -> None:
    @classmethod
    def function_to_patch(cls, x: int) -> int:  # type: ignore
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        "x = x + 10",
        "x = x + 20",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(cls, x: int) -> int:
    x = x + 20
    return x"""
    )


def test_ast_patch_function_multi_line_decorator() -> None:
    @pytest.mark.skip(
        reason="remove_decorators not implemented yet",
    )
    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        "x = x + 10",
        "x = x + 20",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 20
    return x"""
    )


def test_ast_patch_mode_before() -> None:
    """Test inserting code before the target line."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(function_to_patch, "return x", "x = x * 2", mode="before")
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 10
    x = x * 2
    return x"""
    )


def test_ast_patch_mode_after() -> None:
    """Test inserting code after the target line."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(function_to_patch, "x = x + 10", "x = x * 2", mode="after")
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 10
    x = x * 2
    return x"""
    )


def test_ast_patch_with_regex_pattern() -> None:
    """Test patching using a regex pattern."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        re.compile(r"x = x \+ \d+"),
        "x = x + 30",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 30
    return x"""
    )


def test_ast_patch_nested_statements() -> None:
    """Test patching code inside nested statements (if, for, while)."""

    def function_to_patch(x: int) -> int:
        if x > 0:
            x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 10", "x = x + 20", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    if x > 0:
        x = x + 20
    return x"""
    )


def test_ast_patch_deeply_nested_statements() -> None:
    """Test patching code inside deeply nested statements."""

    def function_to_patch(x: int) -> int:
        if x > 0:
            for _ in range(10):
                while x < 100:
                    x = x + 5
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 5", "x = x + 10", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    if x > 0:
        for _ in range(10):
            while x < 100:
                x = x + 10
    return x"""
    )


def test_ast_patch_with_multiple_statements() -> None:
    """Test replacing with multiple statements."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        "x = x + 10",
        "y = x * 2\nx = y + 5",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    y = x * 2
    x = y + 5
    return x"""
    )


def test_ast_patch_with_ast_statements() -> None:
    """Test patching with AST statement objects instead of string."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    # Create AST statements directly
    new_stmts = ast.parse("x = x + 50").body

    res_ast_obj = ast_patch(function_to_patch, "x = x + 10", new_stmts, mode="replace")
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 50
    return x"""
    )


def test_ast_patch_error_pattern_not_found() -> None:
    """Test error when pattern is not found in the function."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    with pytest.raises(ValueError, match="No match found for pattern"):
        ast_patch(function_to_patch, "x = x + 999", "x = x + 20", mode="replace")


def test_ast_patch_error_multiple_matches() -> None:
    """Test error when pattern matches multiple lines."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        x = x + 10
        return x

    with pytest.raises(ValueError, match="Multiple matches found for pattern"):
        ast_patch(function_to_patch, "x = x + 10", "x = x + 20", mode="replace")


def test_ast_patch_with_try_except() -> None:
    """Test patching code inside try-except blocks."""

    def function_to_patch(x: int) -> int:
        try:
            x = x + 10
        except Exception:
            x = 0
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 10", "x = x + 20", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    try:
        x = x + 20
    except Exception:
        x = 0
    return x"""
    )


def test_ast_patch_with_context_manager() -> None:
    """Test patching code inside with statements."""

    def function_to_patch(x: int) -> int:
        with open("test.txt") as f:  # type: ignore  # noqa: F841
            x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 10", "x = x + 20", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    with open('test.txt') as f:
        x = x + 20
    return x"""
    )


def test_ast_patch_multiline_statement() -> None:
    """Test patching a statement that spans multiple lines."""

    def function_to_patch(x: int) -> int:
        result = x + 10 + 20 + 30
        return result

    # Match the multiline statement
    res_ast_obj = ast_patch(
        function_to_patch,
        "result = x + 10 + 20 + 30",
        "result = x * 2",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    result = x * 2
    return result"""
    )


def test_ast_patch_for_loop() -> None:
    """Test patching code inside for loops."""

    def function_to_patch(items: list[int]) -> int:
        total = 0
        for item in items:
            total = total + item
        return total

    res_ast_obj = ast_patch(
        function_to_patch,
        "total = total + item",
        "total = total + item * 2",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(items: list[int]) -> int:
    total = 0
    for item in items:
        total = total + item * 2
    return total"""
    )


def test_ast_patch_while_loop() -> None:
    """Test patching code inside while loops."""

    def function_to_patch(x: int) -> int:
        while x < 100:
            x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch, "x = x + 10", "x = x + 20", mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    while x < 100:
        x = x + 20
    return x"""
    )


def test_ast_patch_match_statement() -> None:
    """Test patching code inside match statements (Python 3.10+)."""

    def function_to_patch(x: int) -> str:
        match x:
            case 1:
                result = "one"
            case _:
                result = "other"
        return result

    res_ast_obj = ast_patch(
        function_to_patch, 'result = "one"', 'result = "ONE"', mode="replace"
    )
    res_str = ast.unparse(res_ast_obj)

    # ast.unparse may use single quotes instead of double quotes
    assert "result = 'ONE'" in res_str or 'result = "ONE"' in res_str
    assert "match x:" in res_str


def test_ast_patch_insert_multiple_lines_before() -> None:
    """Test inserting multiple lines before a statement."""

    def function_to_patch(x: int) -> int:
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        "return x",
        "x = x * 2\nx = x + 10",
        mode="before",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x * 2
    x = x + 10
    return x"""
    )


def test_ast_patch_insert_multiple_lines_after() -> None:
    """Test inserting multiple lines after a statement."""

    def function_to_patch(x: int) -> int:
        x = x + 5
        return x

    res_ast_obj = ast_patch(
        function_to_patch,
        "x = x + 5",
        "x = x * 2\nx = x + 10",
        mode="after",
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 5
    x = x * 2
    x = x + 10
    return x"""
    )


def test_ast_patch_complex_function() -> None:
    """Test patching a more complex function with multiple control structures."""

    def function_to_patch(items: list[int]) -> int:
        total = 0
        for item in items:
            if item > 0:
                try:  # noqa: SIM105
                    total = total + item
                except Exception:
                    pass
        return total

    res_ast_obj = ast_patch(
        function_to_patch,
        "total = total + item",
        "total = total + item * 10",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert "total = total + item * 10" in res_str
    assert "for item in items:" in res_str
    assert "if item > 0:" in res_str


def test_ast_patch_list_comprehension_in_body() -> None:
    """Test patching when function contains list comprehensions."""

    def function_to_patch(items: list[int]) -> list[int]:
        result = [x * 2 for x in items]
        return result

    res_ast_obj = ast_patch(
        function_to_patch,
        "result = [x * 2 for x in items]",
        "result = [x * 3 for x in items]",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert "x * 3" in res_str


def test_ast_patch_lambda_in_body() -> None:
    """Test patching when function contains lambda expressions."""

    def function_to_patch(x: int) -> int:
        func = lambda n: n + 10  # pyright: ignore # noqa: E731
        result = func(x)  # type: ignore
        return result  # type: ignore

    res_ast_obj = ast_patch(
        function_to_patch,
        "result = func(x)  # type: ignore",
        "result = func(x) * 2",
        mode="replace",
    )
    res_str = ast.unparse(res_ast_obj)

    assert "result = func(x) * 2" in res_str
