from __future__ import annotations

import ast

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
