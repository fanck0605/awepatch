from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from awepatch.utils import get_source_lines, load_function_code

if TYPE_CHECKING:
    from collections.abc import Callable


def hello() -> int:
    return 4


def test_load_func_code_with_default() -> None:
    def fn_with_default(y: int, x: int = hello()) -> int:
        return x + y

    fn_with_default_ast = ast.parse("".join(get_source_lines(fn_with_default)))

    fn_with_default_co = load_function_code(fn_with_default_ast)
    assert fn_with_default_co.co_name == fn_with_default.__name__
    fn_with_default.__code__ = fn_with_default_co
    assert fn_with_default(1) == 5


def test_load_func_code_with_nested() -> None:
    def fn_with_nested(x: int = 5) -> int:
        def _nested() -> int:
            return 5 + x

        return _nested()

    fn_with_nested_ast = ast.parse("".join(get_source_lines(fn_with_nested)))

    fn_with_nested_co = load_function_code(fn_with_nested_ast)
    assert fn_with_nested_co.co_name == fn_with_nested.__name__
    fn_with_nested.__code__ = fn_with_nested_co
    assert fn_with_nested(10) == 15


def test_load_func_code_with_lambda() -> None:
    def fn_with_lambda(x: Callable[[], int] = lambda: 5, y: int = 10) -> int:
        return x() + y

    fn_with_lambda_ast = ast.parse("".join(get_source_lines(fn_with_lambda)))

    fn_with_lambda_co = load_function_code(fn_with_lambda_ast)
    assert fn_with_lambda_co.co_name == fn_with_lambda.__name__
    fn_with_lambda.__code__ = fn_with_lambda_co
    assert fn_with_lambda(y=9) == 14
    assert fn_with_lambda(x=lambda: 3) == 13
