from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

from awepatch.utils import (
    _get_function_def,  # pyright: ignore[reportPrivateUsage]
    load_function_code,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def hello() -> int:
    return 4


def test_load_func_code_with_default() -> None:
    def fn_with_default(y: int, x: int = hello()) -> int:
        return x + y

    fn_with_default_def = _get_function_def(
        fn_with_default.__code__, inspect.findsource(fn_with_default)[0]
    )

    fn_with_default_co = load_function_code(fn_with_default_def)  # pyright: ignore[reportArgumentType]
    assert fn_with_default_co.co_name == fn_with_default.__name__
    fn_with_default.__code__ = fn_with_default_co
    assert fn_with_default(1) == 5


def test_load_func_code_with_nested() -> None:
    def fn_with_nested(x: int = 5) -> int:
        def _nested() -> int:
            return 5 + x

        return _nested()

    fn_with_nested_def = _get_function_def(
        fn_with_nested.__code__, inspect.findsource(fn_with_nested)[0]
    )

    fn_with_nested_co = load_function_code(fn_with_nested_def)  # pyright: ignore[reportArgumentType]
    assert fn_with_nested_co.co_name == fn_with_nested.__name__
    fn_with_nested.__code__ = fn_with_nested_co
    assert fn_with_nested(10) == 15


def test_load_func_code_with_lambda() -> None:
    def fn_with_lambda(x: Callable[[], int] = lambda: 5, y: int = 10) -> int:
        return x() + y

    fn_with_lambda_def = _get_function_def(
        fn_with_lambda.__code__, inspect.findsource(fn_with_lambda)[0]
    )

    fn_with_lambda_co = load_function_code(fn_with_lambda_def)  # pyright: ignore[reportArgumentType]
    assert fn_with_lambda_co.co_name == fn_with_lambda.__name__
    fn_with_lambda.__code__ = fn_with_lambda_co
    assert fn_with_lambda(y=9) == 14
    assert fn_with_lambda(x=lambda: 3) == 13
