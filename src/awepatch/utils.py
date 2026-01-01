from __future__ import annotations

import ast
import inspect
import re
import sys
from collections import defaultdict
from functools import partial
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable


class Patch(NamedTuple):
    """A single patch operation.

    Attributes:
        pattern: The pattern to search for in the source code.
        repl: The replacement code or AST statements.
        mode: The mode of patching (before/after/replace).

    """

    pattern: str | re.Pattern[str]
    repl: str | list[ast.stmt]
    mode: Literal["before", "after", "replace"] = "before"


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
    for index, line in enumerate(lines):
        line = line.strip()

        if (isinstance(pattern, str) and line == pattern) or (
            isinstance(pattern, re.Pattern) and pattern.search(line)
        ):
            if lineno is not None:
                raise ValueError(f"Multiple matches found for pattern: {pattern}")
            lineno = index + 1

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
    patches: dict[Literal["before", "after", "replace"], list[ast.stmt]],
) -> bool:
    """Find and modify the statement at the specified line number in the AST.

    Args:
        ast_node: The AST node to traverse
        target: The target line number
        patches: Dictionary mapping modes to their replacement statements

    Returns:
        True if the target statement was found and modified, False otherwise

    """
    for _, field in ast.iter_fields(ast_node):
        if isinstance(field, list):
            # Search for target statement in list fields
            if _modify_ast_list(field, target, patches):  # pyright: ignore[reportUnknownArgumentType]
                return True
        elif isinstance(field, ast.AST):  # noqa: SIM102
            # Recursively process child nodes
            if _modify_ast_node(field, target, patches):
                return True

    return False


def _modify_ast_list(
    ast_list: list[Any],
    target: int,
    patches: dict[Literal["before", "after", "replace"], list[ast.stmt]],
) -> bool:
    """Find and modify the target statement in a list of statements.

    Args:
        ast_list: The list of AST statements
        target: The target line number
        patches: Dictionary mapping modes to their replacement statements

    Returns:
        True if the target statement was found and modified, False otherwise

    """
    for index, item in enumerate(ast_list):
        if not isinstance(item, ast.AST):
            continue

        # First recursively check child nodes
        if _modify_ast_node(item, target, patches):
            return True

        # Check if current statement matches target line number
        if _is_target_stmt(item, target):
            _attach_stmts(ast_list, index, patches)
            return True

    return False


def _is_target_stmt(stmt: ast.AST, lineno: int) -> bool:
    """Check if the statement contains the target line number."""
    return (
        isinstance(stmt, ast.stmt)
        and stmt.end_lineno is not None
        and stmt.lineno <= lineno <= stmt.end_lineno
    )


def _attach_stmts(
    stmts: list[Any],
    index: int,
    patches: dict[Literal["before", "after", "replace"], list[ast.stmt]],
) -> None:
    """Insert or replace statements at the specified position with multiple modes.

    Applies patches in order: before, replace, after.
    """
    # Apply 'before' first
    if "before" in patches:
        stmts[index:index] = patches["before"]
        index += len(patches["before"])  # Adjust index after insertion

    # Apply 'replace' (which removes the original statement)
    if "replace" in patches:
        stmts[index : index + 1] = patches["replace"]
        index += len(patches["replace"]) - 1  # Adjust for replacement

    # Apply 'after' last
    if "after" in patches:
        stmts[index + 1 : index + 1] = patches["after"]


def _compile_patches(
    source_lines: list[str],
    patches: list[Patch],
) -> dict[int, dict[Literal["before", "after", "replace"], list[ast.stmt]]]:
    """Compile patches into a dictionary mapping line numbers to mode-specific
    statements.

    Args:
        source_lines: The source code lines of the function
        patches: List of Patch objects to compile

    Returns:
        Dictionary mapping line numbers to dictionaries of mode->statements

    Raises:
        ValueError: If duplicate modes on same line or conflicting patches

    """
    compiled_patches: defaultdict[
        int, dict[Literal["before", "after", "replace"], list[ast.stmt]]
    ] = defaultdict(dict)

    for patch in patches:
        # Get target line number
        target_lineno = find_line_number(source_lines, patch.pattern)

        # Prepare replacement statements
        repl_stmts = (
            load_stmts(patch.repl) if isinstance(patch.repl, str) else patch.repl
        )

        # Check for duplicate mode on the same line
        if patch.mode in compiled_patches[target_lineno]:
            raise ValueError(
                f"Multiple '{patch.mode}' patches on the same line {target_lineno}"
            )

        # Check for conflicting patches: replace cannot be combined with other modes
        existing_modes = compiled_patches[target_lineno]
        if existing_modes and (patch.mode == "replace" or "replace" in existing_modes):
            raise ValueError(
                f"Cannot combine 'replace' with other modes on line {target_lineno}"
            )

        compiled_patches[target_lineno][patch.mode] = repl_stmts

    return compiled_patches


def ast_patch(
    func: CodeType | FunctionType,
    patches: list[Patch],
) -> ast.Module:
    """Patch the AST of a function or code object.

    Args:
        func (CodeType | FunctionType): The function or code object to patch.
        patches (list[Patch]): List of Patch objects for applying multiple patches.

    Returns:
        ast.Module: The modified AST module contains only one function definition.

    """
    # Validate arguments
    if not patches:
        raise ValueError("patches list cannot be empty")

    # 1. Get source code
    source_lines = get_source_lines(func)

    # 2. Parse AST and validate
    ast_code = ast.parse("".join(source_lines))
    if len(ast_code.body) != 1 or not isinstance(ast_code.body[0], ast.FunctionDef):
        raise ValueError("Only single function definitions are supported")

    # 3. Clear decorators
    ast_code.body[0].decorator_list.clear()

    # 4. Pre-compile all patches: find line numbers and prepare replacement statements
    compiled_patches = _compile_patches(source_lines, patches)

    # 5. Apply all compiled patches (each line number only traverses AST once)
    for target_lineno, mode_patches in compiled_patches.items():
        # Find and modify the target statement in the AST with all modes at once
        if not _modify_ast_node(ast_code, target_lineno, mode_patches):
            raise ValueError(f"No ast.stmt found for line number: {target_lineno}")

    return ast_code
