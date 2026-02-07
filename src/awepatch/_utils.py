from __future__ import annotations

import ast
import os
import re
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import KW_ONLY, dataclass
from typing import Any, Literal, TypeAlias, cast

TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType


@dataclass(slots=True)
class Ident:
    """Identifier for locating target AST nodes.

    Attributes:
        lineno: The line number of the target node, absolute or relative.
        pattern: The pattern to match the source code of the target node.

    """

    pattern: str | re.Pattern[str]
    _: KW_ONLY
    lineno: int | str


IdentType: TypeAlias = str | re.Pattern[str] | Ident
Mode: TypeAlias = Literal["before", "after", "replace"]


@dataclass(slots=True)
class Patch:
    """A single patch operation.

    Attributes:
        target: The target pattern to search for in the source code.
        patch: The patch code or AST statements.
        mode: The mode of patching (before/after/replace).

    """

    target: IdentType | tuple[IdentType, ...]
    content: str | Sequence[ast.stmt]
    mode: Mode = "before"


@dataclass(slots=True)
class CompiledIdent:
    """Compiled identifier for locating target AST nodes.

    Attributes:
        lineno: The absolute line number of the target node.
        pattern: The pattern to match the source code of the target node.

    """

    pattern: str | re.Pattern[str]
    _: KW_ONLY
    lineno: int | None = None


ASTLocation: TypeAlias = tuple[str | int, ...]
CompiledPatches: TypeAlias = defaultdict[ASTLocation, dict[Mode, Sequence[ast.stmt]]]


@dataclass(slots=True)
class ASTList:
    field: list[Any]

    def __hash__(self) -> int:
        return id(self.field)

    def __eq__(self, value: object) -> bool:
        return self.field is value.field if isinstance(value, ASTList) else False

    def __str__(self) -> str:
        return ast.unparse(ast.Module(body=self.field, type_ignores=[]))


PreparedPatches: TypeAlias = defaultdict[
    ASTList, defaultdict[int, dict[Mode, Sequence[ast.stmt]]]
]


def append_patch(
    compiled: CompiledPatches,
    target: ASTLocation,
    stmts: Sequence[ast.stmt],
    mode: Mode,
) -> None:
    patches = compiled[target]
    if mode == "replace":
        if "replace" in patches:
            raise ValueError(
                f"Multiple 'replace' patches on the same target {target!r}"
            )
        patches[mode] = stmts
    elif mode == "before":
        patches[mode] = [*patches[mode], *stmts] if mode in patches else stmts
    elif mode == "after":
        patches[mode] = [*stmts, *patches[mode]] if mode in patches else stmts
    else:
        raise ValueError(f"Unknown patch mode: {mode!r}")


def prepare_patches(
    compiled: CompiledPatches,
    tree: ast.AST,
) -> PreparedPatches:
    prepared: PreparedPatches = defaultdict(lambda: defaultdict(dict))
    for location, patch in compiled.items():
        assert isinstance(location[-1], int)
        target: Any = tree
        for i in location[:-1]:
            target = target[i] if isinstance(i, int) else getattr(target, i)
        prepared[ASTList(target)][location[-1]] = patch
    return prepared


def load_stmts(code: str) -> list[ast.stmt]:
    return ast.parse(code).body


def _is_match_node(
    node: ast.AST,
    source: Sequence[str],
    ident: CompiledIdent,
) -> bool:
    """Check if the AST node matches the target pattern.

    Args:
        node: The AST node to check
        source: The source code lines
        ident: The target identifier or pattern

    Returns:
        True if the AST node matches the target identifier, False otherwise

    """
    if not isinstance(node, ast.stmt):
        return False

    node_lines = source[node.lineno - 1 : node.end_lineno]
    node_source = "".join(node_lines).lstrip()

    if ident.lineno is not None and ident.lineno != node.lineno:
        return False

    return bool(
        isinstance(ident.pattern, str)
        and node_source.startswith(ident.pattern)
        or isinstance(ident.pattern, re.Pattern)
        and ident.pattern.match(node_source)
    )


def find_matched_node(
    node: ast.AST,
    source: Sequence[str],
    target: tuple[CompiledIdent, ...],
    parent: ASTLocation = (),
) -> ASTLocation | None:
    """Recursively find the target AST node matching the target patterns.

    Args:
        node: The AST node to search
        source: The source code lines
        target: The target patterns
        parent: The location of the parent node (used for recursion)

    Returns:
        The AST node matching the target patterns, or None if not found

    """
    matched: ASTLocation | None = None

    for key, field in ast.iter_fields(node):
        if isinstance(field, list):
            field = cast("list[Any]", field)
            for index, item in enumerate(field):
                if not isinstance(item, ast.AST):
                    continue

                if _is_match_node(item, source, target[0]):
                    if len(target) == 1:
                        tmp_matched = parent + (key, index)
                    else:
                        tmp_matched = find_matched_node(
                            item,
                            source,
                            target[1:],
                            parent + (key, index),
                        )
                else:
                    tmp_matched = find_matched_node(
                        item,
                        source,
                        target,
                        parent + (key, index),
                    )

                if tmp_matched is not None:
                    if matched is not None:
                        raise ValueError(
                            f"Multiple matches found for target pattern {target}"
                        )
                    matched = tmp_matched

        elif isinstance(field, ast.AST):
            if len(target) == 1:
                tmp_matched = find_matched_node(field, source, target, parent + (key,))
            elif _is_match_node(field, source, target[0]):
                tmp_matched = find_matched_node(
                    field, source, target[1:], parent + (key,)
                )
            else:
                tmp_matched = find_matched_node(field, source, target, parent + (key,))
            if tmp_matched is not None:
                if matched is not None:
                    raise ValueError(
                        f"Multiple matches found for target pattern {target}"
                    )
                matched = tmp_matched

    return matched


def _compile_ident(ident: IdentType, firstlineno: int) -> CompiledIdent:
    """Check the identifier of a Patch object.

    Args:
        ident: The target identifier to check.
        firstlineno: The first line number of the source code.

    Returns:
        The validated Identifier object.

    Raises:
        ValueError: If the identifier is invalid.

    """
    if isinstance(ident, (str, re.Pattern)):
        return CompiledIdent(pattern=ident)

    if not isinstance(ident, Ident):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError("Unknown identifier type")

    if isinstance(ident.lineno, int):
        return CompiledIdent(lineno=ident.lineno, pattern=ident.pattern)

    if not isinstance(ident.lineno, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(
            "Identifier lineno must be an integer or a positive digital like '+3'"
        )

    if ident.lineno[0] == "+" and ident.lineno[1:].isdigit():
        return CompiledIdent(
            lineno=int(ident.lineno[1:]) + firstlineno, pattern=ident.pattern
        )

    raise TypeError("Identifier lineno is not a valid relative lineno")


def compile_idents(
    ident: IdentType | tuple[IdentType, ...], firstlineno: int
) -> tuple[CompiledIdent, ...]:
    return (
        tuple(_compile_ident(i, firstlineno) for i in ident)
        if isinstance(ident, tuple)
        else (_compile_ident(ident, firstlineno),)
    )


def _apply_stmts_patches(
    stmts: list[Any],
    index: int,
    patches: Mapping[Mode, Sequence[ast.stmt]],
) -> int:
    """Insert or replace statements at the specified position with multiple modes.

    Applies patches in order: before, replace, after.

    Returns:
        The total number of statements added (can be negative if replaced with fewer).

    """
    i = index

    # Apply 'before' first
    if "before" in patches:
        stmts[i:i] = patches["before"]
        i += len(patches["before"])  # Adjust index after insertion

    # Apply 'replace' (which removes the original statement)
    if "replace" in patches:
        stmts[i : i + 1] = patches["replace"]
        i += len(patches["replace"]) - 1  # Adjust for replacement

    # Apply 'after' last
    if "after" in patches:
        stmts[i + 1 : i + 1] = patches["after"]
        i += len(patches["after"])  # Adjust index after insertion

    return i - index  # Total number of statements added


def apply_prepared_patches(prepared: PreparedPatches) -> None:
    """Apply compiled patches to the AST function definition.

    Args:
        prepared: Prepared patches mapping line numbers to mode-specific
          statements

    Returns:
        True if any patches were applied, False otherwise

    """
    for location, index_patches in prepared.items():
        offset = 0
        for index, patches in sorted(index_patches.items()):
            offset += _apply_stmts_patches(location.field, index + offset, patches)


class AbstractPatcher(ABC):
    @abstractmethod
    def apply(self) -> None:
        """Apply the patches to the function."""

    @abstractmethod
    def restore(self) -> None:
        """Restore the original function."""

    def __enter__(self) -> None:
        """Enter the context manager, applying the patches."""
        self.apply()

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        """Exit the context manager, restoring the original function."""
        self.restore()


AWEPATCH_DEBUG = int(os.getenv("AWEPATCH_DEBUG") or 0)


_cache_dir: str | None = None
_cache_dir_lock = threading.Lock()


def _user_cache_dir() -> str:
    """Get or create the cache directory for awepatch."""
    global _cache_dir

    if _cache_dir is not None:
        return _cache_dir

    with _cache_dir_lock:
        if _cache_dir is not None:
            return _cache_dir
        from platformdirs import user_cache_dir

        _cache_dir = user_cache_dir("awepatch", appauthor=False, ensure_exists=True)
        return _cache_dir


def persist_patched_source(
    source: str,
    name: str,
    type: str,
    origin: str = "",
) -> tuple[str, str]:
    """Persist the patched source code to a file and return the file path and source.

    Args:
        source: The source code of the function.
        name: The name of the function.
        type: The type of the function (e.g., "module", "function").
        origin: The origin location for the function. Defaults to "".

    Returns:
        tuple[str, str]: The file path and the source code of the function.

    """
    from binascii import crc32

    from filelock import FileLock

    origin = f" (patched from {origin})" if origin else ""
    source = f"# generated by awepatch{origin}\n{source}"
    bsource = source.encode("utf-8")

    cache_dir = _user_cache_dir()
    file_path = os.path.join(cache_dir, f"{type}_{name}_{crc32(bsource):010x}.py")

    with FileLock(f"{file_path}.lock"):
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(bsource)
    return file_path, source
