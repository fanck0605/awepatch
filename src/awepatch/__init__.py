from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from awepatch._version import __commit_id__, __version__, __version_tuple__
from awepatch.utils import (
    Patch,
    ast_patch,
    get_origin_function,
    load_function_code,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@contextmanager
def patch_callable(
    func: Callable[..., Any],
    patches: list[Patch],
) -> Iterator[None]:
    """Context manager to patch a callable's code object using AST manipulation.

    Args:
        func (Callable[..., Any]): The function to patch.
        patches (list[Patch]): List of Patch objects for applying multiple patches.

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
    patched_func_ast = ast_patch(raw_func_code, patches)
    patched_func_code = load_function_code(
        patched_func_ast,
        origin=f"{raw_func_code.co_filename}::{raw_func_code.co_qualname}",
    )

    # replace the function's code object
    func.__code__ = patched_func_code
    try:
        yield
    finally:
        func.__code__ = raw_func_code


__all__ = (
    "__commit_id__",
    "__version__",
    "__version_tuple__",
    "Patch",
    "patch_callable",
)
