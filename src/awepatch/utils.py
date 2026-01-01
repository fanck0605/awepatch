from __future__ import annotations

import ast
import inspect
import re
import sys
from functools import partial
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable


def get_origin_function(func: Callable[..., Any]) -> Callable[..., Any]:
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


def find_line_number(lines: list[str], pattern: str | re.Pattern[str]) -> int:
    if not isinstance(pattern, (str, re.Pattern)):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Unknown pattern type: {type(pattern)}")

    lineno = None
    for idx, line in enumerate(lines):
        line = line.strip()

        if (isinstance(pattern, str) and line == pattern) or (
            isinstance(pattern, re.Pattern) and pattern.search(line)
        ):
            if lineno is not None:
                raise ValueError(f"Multiple matches found for pattern: {pattern}")
            lineno = idx + 1

    if lineno is None:
        raise ValueError(f"No match found for pattern: {pattern}")

    return lineno


def load_stmts(code: str) -> list[ast.stmt]:
    return ast.parse(code).body


def get_source_lines(
    obj: CodeType | FunctionType,
) -> list[str]:
    """Get the source lines of a function or code object.

    Args:
        obj (CodeType | FunctionType): The function or code object to get the source
          lines.

    """
    source_lines = inspect.getsourcelines(obj)[0]

    # remove common leading indentation
    indent = len(source_lines[0]) - len(source_lines[0].lstrip())
    source_lines = [line[indent:] for line in source_lines]

    return source_lines


def _find_function_code(module: CodeType) -> CodeType:
    funcs = [
        func
        for func in module.co_consts
        if isinstance(func, CodeType) and func.co_name != "<lambda>"
    ]
    if len(funcs) != 1:
        raise ValueError("Only single function definitions are supported")
    return funcs[0]


def load_function_code(func: ast.Module) -> CodeType:
    """Load a function's code object from its AST module.

    Args:
        func (ast.Module): The AST module containing the function definition.

    Returns:
        CodeType: The code object of the function.

    """
    # ensure only one function definition is present
    if len(func.body) != 1 or not isinstance(func.body[0], ast.FunctionDef):
        raise ValueError("Only single function definitions are supported")

    module_code = compile(func, filename="<dynamic>", mode="exec")
    func_code = _find_function_code(module_code)
    if func_code.co_name != func.body[0].name:
        # This should never happen though better to be safe than sorry
        raise ValueError("Function name mismatch!")
    return func_code


def _modify_ast_node(
    ast_node: ast.AST,
    target: int,
    repl: list[ast.stmt],
    mode: Literal["before", "after", "replace"],
) -> bool:
    """Find and modify the statement at the specified line number in the AST.

    Args:
        ast_node: The AST node to traverse
        target: The target line number
        repl: The list of replacement statements
        mode: The modification mode (before/after/replace)

    Returns:
        True if the target statement was found and modified, False otherwise

    """
    for _, field in ast.iter_fields(ast_node):
        if isinstance(field, list):
            # Search for target statement in list fields
            if _modify_ast_list(field, target, repl, mode):  # pyright: ignore[reportUnknownArgumentType]
                return True
        elif isinstance(field, ast.AST):  # noqa: SIM102
            # Recursively process child nodes
            if _modify_ast_node(field, target, repl, mode):
                return True

    return False


def _modify_ast_list(
    ast_list: list[Any],
    target: int,
    repl: list[ast.stmt],
    mode: Literal["before", "after", "replace"],
) -> bool:
    """Find and modify the target statement in a list of statements.

    Args:
        ast_list: The list of AST statements
        target: The target line number
        repl: The list of replacement statements
        mode: The modification mode (before/after/replace)

    Returns:
        True if the target statement was found and modified, False otherwise

    """
    for idx, item in enumerate(ast_list):
        if not isinstance(item, ast.AST):
            continue

        # First recursively check child nodes
        if _modify_ast_node(item, target, repl, mode):
            return True

        # Check if current statement matches target line number
        if _is_target_stmt(item, target):
            _insert_stmts(ast_list, idx, repl, mode)
            return True

    return False


def _is_target_stmt(stmt: ast.AST, lineno: int) -> bool:
    """Check if the statement contains the target line number."""
    return (
        isinstance(stmt, ast.stmt)
        and stmt.end_lineno is not None
        and stmt.lineno <= lineno <= stmt.end_lineno
    )


def _insert_stmts(
    ast_list: list[Any],
    idx: int,
    stmts: list[ast.stmt],
    mode: Literal["before", "after", "replace"],
) -> None:
    """Insert or replace statements at the specified position."""
    if mode == "before":
        ast_list[idx:idx] = stmts
    elif mode == "after":
        ast_list[idx + 1 : idx + 1] = stmts
    elif mode == "replace":
        ast_list[idx : idx + 1] = stmts


def ast_patch(
    func: CodeType | FunctionType,
    pattern: str | re.Pattern[str],
    repl: str | list[ast.stmt],
    *,
    mode: Literal["before", "after", "replace"] = "before",
) -> ast.Module:
    """Patch the AST of a function or code object.

    Args:
        func (CodeType | FunctionType): The function or code object to patch.
        pattern (str | re.Pattern[str]): The pattern to search for in the source code.
        repl (str | list[ast.stmt]): The replacement code or AST statements.
        mode (Literal["before", "after", "replace"], optional): The mode of patching.
            Defaults to "before".

    Returns:
        ast.Module: The modified AST module contains only one function definition.

    """
    # 1. Get source code and target line number
    source_lines = get_source_lines(func)
    target_lineno = find_line_number(source_lines, pattern)

    # 2. Parse AST and validate
    ast_code = ast.parse("".join(source_lines))
    if len(ast_code.body) != 1 or not isinstance(ast_code.body[0], ast.FunctionDef):
        raise ValueError("Only single function definitions are supported")

    # 3. Clear decorators and prepare replacement statements
    ast_code.body[0].decorator_list.clear()
    repl_stmts = load_stmts(repl) if isinstance(repl, str) else repl

    # 4. Find and modify the target statement in the AST
    if not _modify_ast_node(ast_code, target_lineno, repl_stmts, mode):
        raise ValueError(f"No ast.stmt found for line number: {target_lineno}")

    return ast_code
