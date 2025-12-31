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
    source_lines = get_source_lines(func)
    target_lineno = find_line_number(source_lines, pattern)
    ast_code = ast.parse("".join(source_lines))

    if len(ast_code.body) != 1 or not isinstance(ast_code.body[0], ast.FunctionDef):
        raise ValueError("Only single function definitions are supported")
    ast_code.body[0].decorator_list.clear()

    repl_stmts = load_stmts(repl) if isinstance(repl, str) else repl

    def modify_ast_node(node: ast.AST) -> bool:
        """Recursively traverse the AST to find and modify the target statement.

        Returns:
            True if a modification was made, False otherwise.

        """
        for _, field in ast.iter_fields(node):
            if isinstance(field, list):
                found = False
                idx = 0
                for idx, item in enumerate(field):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType] # noqa: B007
                    if isinstance(item, ast.AST):
                        # First to modify child nodes, returning early if modified
                        if modify_ast_node(item):
                            return True
                        # Then check if current node matches the lineno
                        if (
                            isinstance(item, ast.stmt)
                            and item.end_lineno is not None
                            and item.lineno <= target_lineno <= item.end_lineno
                        ):
                            found = True
                            break
                # only modify list field if a match was found
                if found:
                    if mode == "before":
                        field[idx:idx] = repl_stmts
                    elif mode == "after":
                        field[idx + 1 : idx + 1] = repl_stmts
                    elif mode == "replace":
                        field[idx : idx + 1] = repl_stmts
                    return True

            elif isinstance(field, ast.AST):
                # Recursively modify child nodes, but checking the current node
                if modify_ast_node(field):
                    return True

        return False

    modified = modify_ast_node(ast_code)
    if not modified:
        raise ValueError(f"No ast.stmt found for line number: {target_lineno}")

    return ast_code
