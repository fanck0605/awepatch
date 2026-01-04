from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

import pytest

from awepatch.utils import Patch, ast_patch, get_origin_function


def test_ast_patch_function() -> None:
    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 20
    return x"""
    )


def test_ast_patch_function_dataclass() -> None:
    @dataclass
    class Data:
        value: int
        matched: bool

    def function_to_patch(x: int) -> Data:
        a = Data(
            value=x,
            matched=False,
        )
        return a

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("a = Data(", "a = x", "after")]
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> Data:
    a = Data(value=x, matched=False)
    a = x
    return a"""
    )


def test_ast_patch_function_complex() -> None:
    @dataclass
    class Data:
        value: int
        matched: bool

    def function_to_patch(x: int) -> list[Data]:
        ll: list[Data] = []
        for i in range(5):
            ll.append(
                Data(
                    value=x + i,
                    matched=False,
                )
            )
        return ll

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("ll.append(", "a = x", "after")]
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> list[Data]:
    ll: list[Data] = []
    for i in range(5):
        ll.append(Data(value=x + i, matched=False))
        a = x
    return ll"""
    )


def test_ast_patch_function_remove() -> None:
    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", "", "replace")]
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    return x"""
    )


def test_ast_patch_one_line_decorator() -> None:
    @classmethod
    def function_to_patch(cls: Any, x: int) -> int:  # type: ignore  # noqa: ANN401
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        get_origin_function(function_to_patch).__code__,
        [Patch("x = x + 10", "x = x + 20", "replace")],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(cls: Any, x: int) -> int:
    x = x + 20
    return x"""
    )


def test_ast_patch_function_multi_line_decorator() -> None:
    @pytest.mark.skip(
        reason="""
remove_decorators not implemented yet
""",
    )
    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [Patch("x = x + 10", "x = x + 20", "replace")],
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

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("return x", "x = x * 2", "before")]
    )
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

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", "x = x * 2", "after")]
    )
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
        function_to_patch.__code__,
        [Patch(re.compile(r"x = x \+ \d+"), "x = x + 30", "replace")],
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
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
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
        function_to_patch.__code__, [Patch("x = x + 5", "x = x + 10", "replace")]
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
        function_to_patch.__code__,
        [Patch("x = x + 10", "y = x * 2\nx = y + 5", "replace")],
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

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", new_stmts, "replace")]
    )
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

    with pytest.raises(ValueError, match="No match found for target pattern"):
        ast_patch(
            function_to_patch.__code__, [Patch("x = x + 999", "x = x + 20", "replace")]
        )


def test_ast_patch_error_multiple_matches() -> None:
    """Test error when pattern matches multiple lines."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        x = x + 10
        return x

    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):
        ast_patch(
            function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
        )


def test_ast_patch_with_try_except() -> None:
    """Test patching code inside try-except blocks."""

    def function_to_patch(x: int) -> int:
        try:
            x = x + 10
        except Exception:
            x = 0
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
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
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
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
        function_to_patch.__code__,
        [Patch("result = x + 10 + 20 + 30", "result = x * 2", "replace")],
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
        function_to_patch.__code__,
        [Patch("total = total + item", "total = total + item * 2", "replace")],
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
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
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
        function_to_patch.__code__,
        [Patch('result = "one"', 'result = "ONE"', "replace")],
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
        function_to_patch.__code__,
        [Patch("return x", "x = x * 2\nx = x + 10", "before")],
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
        function_to_patch.__code__,
        [Patch("x = x + 5", "x = x * 2\nx = x + 10", "after")],
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
        function_to_patch.__code__,
        [Patch("total = total + item", "total = total + item * 10", "replace")],
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
        function_to_patch.__code__,
        [
            Patch(
                "result = [x * 2 for x in items]",
                "result = [x * 3 for x in items]",
                "replace",
            )
        ],
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
        function_to_patch.__code__,
        [Patch("result = func(x)  # type: ignore", "result = func(x) * 2", "replace")],
    )
    res_str = ast.unparse(res_ast_obj)

    assert "result = func(x) * 2" in res_str


def test_multiple_patches_different_lines() -> None:
    """Test applying multiple patches to different lines."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        x = x * 2
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("x = x + 10", "x = x + 20", "replace"),
            Patch("x = x * 2", "x = x * 3", "replace"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    x = x + 20
    x = x * 3
    return x"""
    )


def test_multiple_patches_before_and_after_same_line() -> None:
    """Test applying both before and after patches to the same line."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("x = x + 10", "print('before return')", "before"),
            Patch("x = x + 10", "print('after return')", "after"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    print('before return')
    x = x + 10
    print('after return')
    return x"""
    )


def test_multiple_patches_mixed_modes() -> None:
    """Test applying patches with different modes to different lines."""

    def function_to_patch(x: int, y: int) -> int:
        x = x + 10
        y = y * 2
        result = x + y
        return result

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("x = x + 10", "print('processing x')", "before"),
            Patch("y = y * 2", "y = y * 3", "replace"),
            Patch("result = x + y", "print('result calculated')", "after"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int, y: int) -> int:
    print('processing x')
    x = x + 10
    y = y * 3
    result = x + y
    print('result calculated')
    return result"""
    )


def test_multiple_patches_with_default_mode() -> None:
    """Test applying multiple patches with default 'before' mode."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        x = x * 2
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("x = x + 10", "print('before first')"),  # default mode='before'
            Patch("x = x * 2", "print('before second')"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    print('before first')
    x = x + 10
    print('before second')
    x = x * 2
    return x"""
    )


def test_multiple_patches_error_duplicate_mode_same_line() -> None:
    """Test error when multiple patches with same mode target the same line."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    with pytest.raises(
        ValueError, match="Multiple 'before' patches on the same target"
    ):
        ast_patch(
            function_to_patch.__code__,
            [
                Patch("x = x + 10", "print('first')", "before"),
                Patch("x = x + 10", "print('second')", "before"),
            ],
        )


def test_multiple_patches_error_replace_conflict() -> None:
    """Test error when replace is combined with other modes on the same line."""

    def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    with pytest.raises(ValueError, match="Cannot combine 'replace' with other modes"):
        ast_patch(
            function_to_patch.__code__,
            [
                Patch("x = x + 10", "x = x + 20", "replace"),
                Patch("x = x + 10", "print('before')", "before"),
            ],
        )


def test_multiple_patches_nested_and_toplevel() -> None:
    """Test applying patches to both nested and top-level statements."""

    def function_to_patch(x: int) -> int:
        if x > 0:
            x = x + 10
        x = x * 2
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("x = x + 10", "x = x + 20", "after"),
            Patch("x = x * 2", "x = x * 3", "replace"),
            Patch("return x", "print('done')", "before"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    if x > 0:
        x = x + 10
        x = x + 20
    x = x * 3
    print('done')
    return x"""
    )


def test_multiple_patches_many_lines() -> None:
    """Test applying many patches to a larger function."""

    def function_to_patch(items: list[int]) -> int:
        total = 0
        count = 0
        for item in items:
            if item > 0:
                total = total + item
                count = count + 1
        return total

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch("total = 0", "print('initializing total')", "after"),
            Patch("total = total + item", "total = total + item * 2", "replace"),
            Patch("count = count + 1", "print(f'count: {count}')", "after"),
            Patch("return total", "print(f'final total: {total}')", "before"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(items: list[int]) -> int:
    total = 0
    print('initializing total')
    count = 0
    for item in items:
        if item > 0:
            total = total + item * 2
            count = count + 1
            print(f'count: {count}')
    print(f'final total: {total}')
    return total"""
    )


def test_multiline_multiple_patches() -> None:
    """Test applying patches to both nested and top-level statements."""

    def function_to_patch(x: int) -> int:
        if x > 0:
            x = x + 10
        x = x * 2
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__,
        [
            Patch(
                "x = x + 10", "x = x + 20\nx = x + 20\nx = x + 20\nx = x + 20", "after"
            ),
            Patch("x = x * 2", "x = x * 3", "after"),
        ],
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""def function_to_patch(x: int) -> int:
    if x > 0:
        x = x + 10
        x = x + 20
        x = x + 20
        x = x + 20
        x = x + 20
    x = x * 2
    x = x * 3
    return x"""
    )


def test_async_function_patch() -> None:
    """Test patching an async function."""

    async def function_to_patch(x: int) -> int:
        x = x + 10
        return x

    res_ast_obj = ast_patch(
        function_to_patch.__code__, [Patch("x = x + 10", "x = x + 20", "replace")]
    )
    res_str = ast.unparse(res_ast_obj)

    assert (
        res_str
        == r"""async def function_to_patch(x: int) -> int:
    x = x + 20
    return x"""
    )
