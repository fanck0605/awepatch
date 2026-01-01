from __future__ import annotations

from functools import partial, wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import pytest

from awepatch import patch_callable

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

    with patch_callable(
        function_to_patch,
        "x = x * 2",
        "x = x * 3",
        mode="replace",
    ):
        patched_result = function_to_patch(5)
        assert patched_result == 15

    restored_result = function_to_patch(5)
    assert restored_result == original_result


def test_patch_function_mode() -> None:
    def fn() -> list[int]:
        a: list[int] = []
        a.append(3)
        return a

    with patch_callable(
        fn,
        "a.append(3)",
        "a.append(4)",
        mode="replace",
    ):
        assert fn() == [4]

    with patch_callable(
        fn,
        "a.append(3)",
        "a.append(4)",
        mode="before",
    ):
        assert fn() == [4, 3]

    with patch_callable(
        fn,
        "a.append(3)",
        "a.append(4)",
        mode="after",
    ):
        assert fn() == [3, 4]


def test_patch_method() -> None:
    class MyClass:
        def method_to_patch(self, z: int) -> int:
            z += 1
            return z

    with patch_callable(MyClass.method_to_patch, "z += 1", "z += 5", mode="replace"):
        obj = MyClass()
        assert obj.method_to_patch(10) == 15


def test_patch_obj_method() -> None:
    class MyClass:
        def method_to_patch(self, z: int) -> int:
            z += 1
            return z

    obj = MyClass()
    with patch_callable(obj.method_to_patch, "z += 1", "z += 5", mode="replace"):
        assert obj.method_to_patch(10) == 15


def test_patch_class_method() -> None:
    class MyClass:
        @classmethod
        def class_method_to_patch(cls, z: int) -> int:
            z += 2
            return z

    with patch_callable(
        MyClass.class_method_to_patch, "z += 2", "z += 10", mode="replace"
    ):
        assert MyClass.class_method_to_patch(10) == 20


def test_patch_static_method() -> None:
    class MyClass:
        @staticmethod
        def static_method_to_patch(z: int) -> int:
            z += 3
            return z

    with patch_callable(
        MyClass.static_method_to_patch, "z += 3", "z += 15", mode="replace"
    ):
        assert MyClass.static_method_to_patch(10) == 25


def test_patch_partial_function() -> None:
    from functools import partial

    def function_to_patch(a: int, b: int) -> int:
        return a + b

    partial_func = partial(function_to_patch, 5)

    with patch_callable(partial_func, "return a + b", "return a * b", mode="replace"):
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

    with patch_callable(function_to_patch, "x += 4", "x += 10", mode="replace"):
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
    with patch_callable(method_to_patch, "z += 2", "z += 8", mode="replace"):
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
    with patch_callable(MyClass.method_to_patch, "z += 2", "z += 8", mode="replace"):
        assert MyClass.method_to_patch(10) == 18


def test_wrap_by_function() -> None:
    def method_to_patch(z: int) -> int:
        z += 2
        return z

    method_to_patch = pytest.mark.skip("xxx")(method_to_patch)

    assert method_to_patch(10) == 12

    with patch_callable(method_to_patch, "z += 2", "z += 8", mode="replace"):
        assert method_to_patch(10) == 18


def test_lambda_func() -> None:
    lambda_func: Callable[[int], int] = lambda x: x + 5  # noqa

    assert lambda_func(10) == 15

    with (
        pytest.raises(TypeError, match="Cannot patch lambda functions"),
        patch_callable(lambda_func, "x + 5", "x + 10", mode="replace"),
    ):
        pass
