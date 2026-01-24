from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from awepatch._version import __commit_id__, __version__, __version_tuple__
from awepatch.function import FunctionPatcher
from awepatch.module import ModulePatcher
from awepatch.utils import AbstractPatcher, Ident, Patch

if TYPE_CHECKING:
    from collections.abc import Callable


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


def patch_callable(
    func: Callable[..., Any],
    /,
    patch: Patch | list[Patch],
) -> AbstractPatcher:
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

    collector = FunctionPatcher()
    patches = _check_patches(patch)
    for p in patches:
        collector.add_patch(func, p.target, p.content, p.mode)
    return collector


# compatibility alias
CallablePatcher: TypeAlias = AbstractPatcher


__all__ = (
    "__commit_id__",
    "__version__",
    "__version_tuple__",
    "CallablePatcher",
    "Patch",
    "Ident",
    "patch_callable",
    "AbstractPatcher",
    "ModulePatcher",
    "FunctionPatcher",
)
