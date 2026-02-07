from __future__ import annotations

import ast
import inspect
import pickle
import sys
from collections import defaultdict
from collections.abc import Callable
from functools import partial
from types import CodeType, TracebackType

from awepatch._utils import (
    AWEPATCH_DEBUG,
    AbstractPatcher,
    CompiledPatches,
    IdentType,
    Mode,
    append_patch,
    apply_prepared_patches,
    compile_idents,
    find_matched_node,
    load_stmts,
    persist_patched_source,
    prepare_patches,
)

TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any, Self


def _unwrap_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """Get the object wrapped by *func*.

    Follows the chain of :attr:`__wrapped__` or :attr:`__func__` attributes or
    :class:`functools.partial` objects, returning the last object in the chain.

    :exc:`ValueError` is raised if a cycle is encountered.

    """
    f = func  # remember the original func for error reporting
    # Memoise by id to tolerate non-hashable objects, but store objects to
    # ensure they aren't destroyed, which would allow their IDs to be reused.
    memo = {id(f): f}
    recursion_limit = sys.getrecursionlimit()
    while not isinstance(func, type):
        if hasattr(func, "__wrapped__"):
            func = func.__wrapped__  # pyright: ignore[reportFunctionMemberAccess]
        elif hasattr(func, "__func__"):
            func = func.__func__  # pyright: ignore[reportFunctionMemberAccess]
        elif isinstance(func, partial):
            func = func.func
        else:
            break
        id_func = id(func)
        if (id_func in memo) or (len(memo) >= recursion_limit):
            raise ValueError(f"wrapper loop when unwrapping {f!r}")
        memo[id_func] = func
    return func


def _find_function_code(module: CodeType) -> CodeType:
    funcs = [
        func
        for func in module.co_consts
        if isinstance(func, CodeType) and func.co_name != "<lambda>"
    ]
    if len(funcs) != 1:
        raise ValueError("Only single function definitions are supported")
    return funcs[0]


def load_function_code(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    origin: str = "",
) -> CodeType:
    """Load a function's code object from its AST module.

    Args:
        func (ast.Module): The AST module containing the function definition.
        origin (str, optional): The origin location for the function. Defaults to "".

    Returns:
        CodeType: The code object of the function.

    """

    source = ast.unparse(func)

    if AWEPATCH_DEBUG:
        file_path, source = persist_patched_source(
            source,
            name=func.name,
            type="function",
            origin=origin,
        )
        module_code = compile(source, filename=file_path, mode="exec")
    else:
        module_code = compile(source, filename="<awepatch>", mode="exec")

    func_code = _find_function_code(module_code)
    if func_code.co_name != func.name:
        # This should never happen though better to be safe than sorry
        raise ValueError("Function name mismatch!")

    return func_code


def _get_function_def(
    func: CodeType, slines: list[str]
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Get the AST function definition from a code object.

    Args:
        func: The code object
        slines: The source code lines of the function

    Returns:
        The AST function definition

    Raises:
        ValueError: If the function definition is not found in the source

    """

    for node in ast.walk(ast.parse("".join(slines))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func.co_name:
            continue
        node_lineno = (
            node.decorator_list[0].lineno if node.decorator_list else node.lineno
        )
        if node_lineno != func.co_firstlineno:
            continue
        return node

    raise ValueError("Function definition not found in source")


def get_origin_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """Check if the provided object is a valid callable for patching and return the
    original function.

    Args:
        func: The callable to check.

    Returns:
        The original function if valid.

    """
    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    func = _unwrap_function(func)
    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    return func


class _SingleFunctionPatcher:
    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self._orig_code = func.__code__
        self._slines, _ = inspect.findsource(func)
        self._func_def = _get_function_def(func.__code__, self._slines)
        self._func_def.decorator_list.clear()
        self._patches: CompiledPatches = defaultdict(dict)
        self._pkl_func_def = pickle.dumps(self._func_def)

    def add_patch(
        self,
        target: IdentType | tuple[IdentType, ...],
        content: str | Sequence[ast.stmt],
        mode: Mode = "before",
    ) -> None:
        ident = compile_idents(target, self._func_def.lineno)
        stmts = load_stmts(content) if isinstance(content, str) else content

        location = find_matched_node(self._func_def, self._slines, ident)
        if location is None:
            raise ValueError(f"Patch target {target} not found")

        append_patch(
            self._patches,
            location,
            stmts,
            mode,
        )

    def apply(self) -> Callable[..., Any]:
        """Apply the patches to the function."""
        func_def = pickle.loads(self._pkl_func_def)
        prepared = prepare_patches(self._patches, func_def)
        apply_prepared_patches(prepared)
        func_code = load_function_code(func_def, origin=repr(self._func))
        self._func.__code__ = func_code
        return self._func

    def restore(self) -> None:
        """Restore the original function."""
        self._func.__code__ = self._orig_code


class FunctionPatcher(AbstractPatcher):
    """A class for managing multiple CallablePatchers."""

    def __init__(self) -> None:
        """Initialize a MultiPatcher."""
        self._func_patchers: dict[int, _SingleFunctionPatcher] = {}

    def add_patch(
        self,
        func: Callable[..., Any],
        /,
        target: IdentType | tuple[IdentType, ...],
        content: str | Sequence[ast.stmt],
        mode: Mode = "before",
    ) -> Self:
        """Add a new patcher to the MultiPatcher.

        Args:
            func: The function to patch.
            target: The target pattern to patch.
            content: The replacement code or AST statements.
            mode: The mode of patching (before/after/replace). Defaults to "before".

        """
        func = get_origin_function(func)
        if func.__name__ == "<lambda>":
            raise TypeError("Cannot patch lambda functions")
        id_func = id(func)
        if id_func not in self._func_patchers:
            self._func_patchers[id_func] = _SingleFunctionPatcher(func)

        self._func_patchers[id_func].add_patch(target, content, mode)
        return self

    def apply(self) -> None:
        """Apply all patches to their respective functions."""
        for patcher in self._func_patchers.values():
            patcher.apply()

    def restore(self) -> None:
        """Restore all original functions."""
        for patcher in self._func_patchers.values():
            patcher.restore()

    def __enter__(self) -> None:
        """Enter the context manager, applying all patches."""
        self.apply()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the context manager, restoring all original functions."""
        self.restore()
