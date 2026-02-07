from __future__ import annotations

import inspect
from functools import partial, wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import pytest

from awepatch import FunctionPatcher, Ident

if TYPE_CHECKING:
    from collections.abc import Callable

_P = ParamSpec("_P")
_R = TypeVar("_R")


def test_patch_function_and_restore() -> None:
    def function_to_patch(x: int) -> int:
        x = x * 2
        return x

    original_result = function_to_patch(5)
    assert original_result == 10

    with FunctionPatcher().add_patch(
        function_to_patch,
        target="x = x * 2",
        content="x = x * 3",
        mode="replace",
    ):
        patched_result = function_to_patch(5)
        assert patched_result == 15

    restored_result = function_to_patch(5)
    assert restored_result == original_result


_y_for_test = 1


def test_patch_function_with_global() -> None:
    def function_to_patch(x: int) -> int:
        global _y_for_test
        _y_for_test = x = x * 2
        return x

    with FunctionPatcher().add_patch(
        function_to_patch,
        target="_y_for_test = x = x * 2",
        content="_y_for_test = x = x * 3",
        mode="replace",
    ):
        patched_result = function_to_patch(5)
        assert patched_result == 15
        assert _y_for_test == 15


def test_patch_function_mode() -> None:
    def fn() -> list[int]:
        a: list[int] = []
        a.append(3)
        return a

    with FunctionPatcher().add_patch(
        fn,
        target="a.append(3)",
        content="a.append(4)",
        mode="replace",
    ):
        assert fn() == [4]

    with FunctionPatcher().add_patch(
        fn,
        target="a.append(3)",
        content="a.append(4)",
        mode="before",
    ):
        assert fn() == [4, 3]

    with FunctionPatcher().add_patch(
        fn,
        target="a.append(3)",
        content="a.append(4)",
        mode="after",
    ):
        assert fn() == [3, 4]


def test_patch_function_with_blank_lines() -> None:
    # do not remove blank lines in `fn` function body
    def fn() -> list[int]:
        a: list[int] = []

        a.append(3)
        return a

    assert (
        inspect.getsource(fn)
        == """    def fn() -> list[int]:
        a: list[int] = []

        a.append(3)
        return a
"""
    )

    with FunctionPatcher().add_patch(
        fn,
        target="a.append(3)",
        content="a.append(4)",
        mode="replace",
    ):
        assert fn() == [4]


def test_patch_method() -> None:
    class MyClass:
        def method_to_patch(self, z: int) -> int:
            z += 1
            return z

    with FunctionPatcher().add_patch(
        MyClass.method_to_patch,
        target="z += 1",
        content="z += 5",
        mode="replace",
    ):
        obj = MyClass()
        assert obj.method_to_patch(10) == 15


def test_patch_obj_method() -> None:
    class MyClass:
        def method_to_patch(self, z: int) -> int:
            z += 1
            return z

    obj = MyClass()
    with FunctionPatcher().add_patch(
        obj.method_to_patch,
        target="z += 1",
        content="z += 5",
        mode="replace",
    ):
        assert obj.method_to_patch(10) == 15


def test_patch_obj_method_with_multiline_string() -> None:
    """Test patching a method that contains a multi-line string."""

    class MyClass:
        def method_to_patch(self, z: str) -> str:
            z = (
                r"""
Hello,

    World!

"""
                + z
            )
            return z

    obj = MyClass()
    with FunctionPatcher().add_patch(
        obj.method_to_patch,
        target="z = (",
        content="z = z.strip()",
        mode="before",
    ):
        assert obj.method_to_patch(" Jack ") == "\nHello,\n\n    World!\n\nJack"


def test_patch_class_method() -> None:
    class MyClass:
        @classmethod
        def class_method_to_patch(cls, z: int) -> int:
            z += 2
            return z

    with FunctionPatcher().add_patch(
        MyClass.class_method_to_patch,
        target="z += 2",
        content="z += 10",
        mode="replace",
    ):
        assert MyClass.class_method_to_patch(10) == 20


def test_patch_static_method() -> None:
    class MyClass:
        @staticmethod
        def static_method_to_patch(z: int) -> int:
            z += 3
            return z

    with FunctionPatcher().add_patch(
        MyClass.static_method_to_patch,
        target="z += 3",
        content="z += 15",
        mode="replace",
    ):
        assert MyClass.static_method_to_patch(10) == 25


def test_patch_partial_function() -> None:
    from functools import partial

    def function_to_patch(a: int, b: int) -> int:
        return a + b

    partial_func = partial(function_to_patch, 5)

    with FunctionPatcher().add_patch(
        partial_func,
        target="return a + b",
        content="return a * b",
        mode="replace",
    ):
        assert partial_func(3) == 15  # 5 * 3


def test_wrapper_function() -> None:
    def wrapper(func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def inner(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return func(*args, **kwargs)

        return inner

    @wrapper
    def function_to_patch(x: int) -> int:
        x += 4
        return x

    with FunctionPatcher().add_patch(
        function_to_patch,
        target="x += 4",
        content="x += 10",
        mode="replace",
    ):
        assert function_to_patch(6) == 16


def test_partialed_wrapped_class_method() -> None:
    def wrapper(func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def inner(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return func(*args, **kwargs)

        return inner

    class MyClass:
        @classmethod
        @wrapper
        def method_to_patch_123(cls, z: int) -> int:
            z += 2
            return z

    method_to_patch = partial(MyClass.method_to_patch_123, 10)
    method_to_patch = wrapper(method_to_patch)

    assert MyClass.method_to_patch_123(10) == 12
    with FunctionPatcher().add_patch(
        method_to_patch,
        target="z += 2",
        content="z += 8",
        mode="replace",
    ):
        assert method_to_patch() == 18


def test_wrapper_and_and_partial_class_method() -> None:
    def wrapper(func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def inner(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            return func(*args, **kwargs)

        return inner

    class MyClass:
        @classmethod
        @wrapper
        def method_to_patch(cls, z: int) -> int:
            z += 2
            return z

    assert MyClass.method_to_patch(10) == 12
    with FunctionPatcher().add_patch(
        MyClass.method_to_patch,
        target="z += 2",
        content="z += 8",
        mode="replace",
    ):
        assert MyClass.method_to_patch(10) == 18


def test_wrap_by_function() -> None:
    def method_to_patch(z: int) -> int:
        z += 2
        return z

    method_to_patch = pytest.mark.skip("xxx")(method_to_patch)

    assert method_to_patch(10) == 12

    with FunctionPatcher().add_patch(
        method_to_patch,
        target="z += 2",
        content="z += 8",
        mode="replace",
    ):
        assert method_to_patch(10) == 18


def test_lambda_func() -> None:
    lambda_func: Callable[[int], int] = lambda x: x + 5  # noqa

    assert lambda_func(10) == 15

    with (
        pytest.raises(TypeError, match="Cannot patch lambda functions"),
        FunctionPatcher().add_patch(
            lambda_func,
            target="x + 5",
            content="x + 10",
            mode="replace",
        ),
    ):
        pass


def test_patch_async_function() -> None:
    import asyncio

    async def async_function_to_patch(x: int) -> int:
        x = x * 2
        return x

    original_result = asyncio.run(async_function_to_patch(5))
    assert original_result == 10

    with FunctionPatcher().add_patch(
        async_function_to_patch,
        target="x = x * 2",
        content="x = x * 3",
        mode="replace",
    ):
        patched_result = asyncio.run(async_function_to_patch(5))
        assert patched_result == 15

    restored_result = asyncio.run(async_function_to_patch(5))
    assert restored_result == original_result


def test_callable_patcher_basic() -> None:
    """Test patch_callable basic functionality."""

    def my_function(x: int) -> int:
        return x + 1

    patcher = FunctionPatcher().add_patch(
        my_function,
        target="return x + 1",
        content="return x + 2",
        mode="replace",
    )

    # Test before applying
    assert my_function(3) == 4

    # Apply patch
    patcher.apply()
    assert my_function(3) == 5  # Original function is also patched

    # Restore
    patcher.restore()
    assert my_function(3) == 4


def test_callable_patcher_context_manager() -> None:
    """Test patch_callable as context manager."""

    def my_function(x: int) -> int:
        return x * 2

    patcher = FunctionPatcher().add_patch(
        my_function,
        target="return x * 2",
        content="return x * 3",
        mode="replace",
    )

    assert my_function(4) == 8

    with patcher:
        assert my_function(4) == 12

    assert my_function(4) == 8


def test_callable_patcher_apply_restore_multiple_times() -> None:
    """Test applying and restoring patches multiple times."""

    def my_function(x: int) -> int:
        return x + 5

    patcher = FunctionPatcher().add_patch(
        my_function,
        target="return x + 5",
        content="return x + 10",
        mode="replace",
    )

    assert my_function(2) == 7

    # Apply, restore, apply again
    patcher.apply()
    assert my_function(2) == 12

    patcher.restore()
    assert my_function(2) == 7

    patcher.apply()
    assert my_function(2) == 12

    patcher.restore()
    assert my_function(2) == 7


def test_match_on_identifier() -> None:
    """Test matching on identifier."""

    def function_to_patch(x: int) -> int:
        x = x * 2
        return x

    absolute_lineno = function_to_patch.__code__.co_firstlineno + 1

    for target in [
        "x = x * 2",
        Ident(lineno="+1", pattern="x = x * 2"),
        Ident(lineno=absolute_lineno, pattern="x = x * 2"),
    ]:
        with FunctionPatcher().add_patch(
            function_to_patch,
            target=target,
            content="x = x * 3",
            mode="replace",
        ):
            patched_result = function_to_patch(5)
            assert patched_result == 15


def test_matching_on_multiple_same_statements() -> None:
    """Test matching on multiple same statements."""

    def function_to_patch(x: int) -> int:
        if x > 0:  # noqa: SIM108
            x = x * 2
        else:
            x = x * 2
        return x

    with pytest.raises(ValueError, match="Multiple matches found for target pattern"):  # noqa: SIM117
        with FunctionPatcher().add_patch(
            function_to_patch,
            target=("if x > 0:", "x = x * 2"),
            content="x = x * 3",
            mode="replace",
        ):
            pass

    with FunctionPatcher().add_patch(
        function_to_patch,
        target=(
            "if x > 0:",
            # we specify the lineno to disambiguate the two same statements
            Ident(lineno="+2", pattern="x = x * 2"),
        ),
        content="x = x * 3",
        mode="replace",
    ):
        assert function_to_patch(5) == 15
        assert function_to_patch(-5) == -10
