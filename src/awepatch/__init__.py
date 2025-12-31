from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Literal

from awepatch.utils import (
    ast_patch,
    get_origin_function,
    load_function_code,
)

if TYPE_CHECKING:
    import ast
    import re
    from collections.abc import Callable, Iterator


@contextmanager
def patch_callable(
    func: Callable[..., Any],
    pattern: str | re.Pattern[str],
    repl: str | list[ast.stmt],
    *,
    mode: Literal["before", "after", "replace"] = "before",
) -> Iterator[None]:
    """Context manager to patch a callable's code object using AST manipulation.

    Args:
        func (Callable[..., Any]): The function to patch.
        pattern (str | re.Pattern[str]): The pattern to search for in the AST.
        repl (str | list[ast.stmt]): The replacement code or AST nodes.
        mode (Literal["before", "after", "replace"], optional): The mode of patching.
            Defaults to "before".

    """

    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    func = get_origin_function(func)
    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    if func.__name__ == "<lambda>":
        raise TypeError("Cannot patch lambda functions")

    raw_func_code = func.__code__

    # Patch the function's AST
    patched_func_ast = ast_patch(raw_func_code, pattern, repl, mode=mode)
    patched_func_code = load_function_code(patched_func_ast)

    # replace the function's code object
    func.__code__ = patched_func_code
    try:
        yield
    finally:
        func.__code__ = raw_func_code


__all__ = ("patch_callable",)
