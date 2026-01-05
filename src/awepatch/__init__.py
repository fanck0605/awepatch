from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from awepatch._version import __commit_id__, __version__, __version_tuple__
from awepatch.utils import (
    Ident,
    Patch,
    ast_patch,
    get_origin_function,
    load_function_code,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import CodeType, TracebackType


def _get_patched_code(
    func: Callable[..., Any],
    patches: list[Patch],
) -> CodeType:
    """Get the patched code object of a function without modifying it.

    Args:
        func (Callable[..., Any]): The function to patch.
        patches (list[Patch]): List of Patch objects for applying multiple patches.

    Returns:
        The patched code object

    """
    # Patch the function's AST
    patched_func_def = ast_patch(func.__code__, patches)
    patched_func_code = load_function_code(
        patched_func_def,
        origin=f"{func.__code__.co_filename}:{func.__code__.co_firstlineno}",
    )
    return patched_func_code


def _check_callable(func: Callable[..., Any]) -> Callable[..., Any]:
    """Check if the provided object is a valid callable for patching and return the
    original function.

    Args:
        func: The callable to check.

    Returns:
        The original function if valid.

    """
    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    func = get_origin_function(func)
    if not callable(func):
        raise TypeError(f"Expected a function, got: {type(func)}")
    if func.__name__ == "<lambda>":
        raise TypeError("Cannot patch lambda functions")
    return func


def _check_patches(patch: Any) -> list[Patch]:  # noqa: ANN401
    """Check and normalize the patches input.

    Args:
        patch: A single Patch or a list of Patch objects.

    Returns:
        A list of Patch objects.

    """
    if isinstance(patch, Patch):
        return [patch]
    elif isinstance(patch, list) and all(isinstance(p, Patch) for p in patch):  # pyright: ignore[reportUnknownVariableType]
        return patch  # pyright: ignore[reportUnknownVariableType]
    else:
        raise TypeError("patch must be a Patch or a list of Patch objects")


class CallablePatcher(ABC):
    @abstractmethod
    def apply(self) -> Callable[..., Any]:
        """Apply the patches to the function."""

    @abstractmethod
    def restore(self) -> None:
        """Restore the original function."""

    def __enter__(self) -> Callable[..., Any]:
        """Enter the context manager, applying the patches."""
        return self.apply()

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        """Exit the context manager, restoring the original function."""
        self.restore()


class _CallablePatcher(CallablePatcher):
    """A class for patching callables using AST manipulation."""

    def __init__(
        self,
        func: Callable[..., Any],
        patch: Patch | list[Patch],
    ) -> None:
        """Initialize a CallablePatcher.

        The CallablePatcher can be used as a context manager to apply patches
        to a callable function.

        Args:
            func (Callable[..., Any]): The function to patch.
            patch (Patch | list[Patch]): Patch or list of Patch objects for applying
                multiple patches.

        """
        func = _check_callable(func)
        patches = _check_patches(patch)

        self._func = func
        self._original_code = func.__code__
        self._patched_code = _get_patched_code(func, patches)

    def apply(self) -> Callable[..., Any]:
        """Apply the patches to the function."""
        self._func.__code__ = self._patched_code
        return self._func

    def restore(self) -> None:
        """Restore the original function."""
        self._func.__code__ = self._original_code


def patch_callable(
    func: Callable[..., Any],
    /,
    patch: Patch | list[Patch],
) -> CallablePatcher:
    """Patch a callable using AST manipulation.

    Args:
        func (Callable[..., Any]): The function to patch.
        patch (Patch | list[Patch]): Patch or list of Patch objects for applying
            multiple patches.

    Examples:
        >>> from awepatch import Patch, patch_callable
        >>> def my_function(x):
        ...     return x + 1
        >>> with patch_callable(my_function, Patch("x + 1", "x + 2", "replace")):
        ...     assert my_function(3) == 5

    """

    return _CallablePatcher(func, patch)


__all__ = (
    "__commit_id__",
    "__version__",
    "__version_tuple__",
    "CallablePatcher",
    "Patch",
    "Ident",
    "patch_callable",
)
