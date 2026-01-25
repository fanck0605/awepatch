from __future__ import annotations

import ast
import sys
from collections import defaultdict
from importlib.abc import MetaPathFinder, SourceLoader
from importlib.machinery import PathFinder
from typing import Self

from awepatch.utils import (
    AWEPATCH_DEBUG,
    AbstractPatcher,
    CompiledPatch,
    CompiledPatches,
    IdentType,
    Mode,
    append_patch,
    apply_compiled_patches,
    compile_idents,
    find_matched_node,
    load_stmts,
    persist_patched_source,
)

TYPE_CHECKING = False

if TYPE_CHECKING:
    import os
    from collections.abc import Buffer, Sequence
    from importlib.machinery import ModuleSpec
    from types import CodeType, ModuleType


class _AwepatchSourceLoader(SourceLoader):
    def __init__(
        self,
        fullname: str,
        origin: str,
        patches: list[CompiledPatch],
    ) -> None:
        self._fullname = fullname
        self._origin = origin
        self._path = origin
        self._patches = patches

    def get_filename(self, fullname: str) -> str:
        return self._origin

    def get_data(self, path: str) -> bytes:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=self._origin)
        slines = source.splitlines(keepends=True)
        compiled: CompiledPatches = defaultdict(lambda: defaultdict(dict))
        for patch in self._patches:
            target = find_matched_node(tree, slines, patch.target)
            if target is None:
                raise ValueError(
                    f"Patch target {patch.target} not found in {self._origin}"
                )
            append_patch(
                compiled,
                target,
                patch.stmts,
                patch.mode,
            )
        apply_compiled_patches(compiled)
        source = ast.unparse(tree)
        if AWEPATCH_DEBUG:
            self._path, source = persist_patched_source(
                source,
                self._fullname.rsplit(".", 1)[-1],
                "module",
                origin=self._origin,
            )
        else:
            self._path = "<awepatch>"
        return source.encode("utf-8")

    def source_to_code(
        self,
        data: Buffer | str | ast.Module | ast.Expression | ast.Interactive,
        path: bytes | str | os.PathLike[str],
        *args,  # noqa # type: ignore
        **kwargs,  # noqa # type: ignore
    ) -> CodeType:
        return super().source_to_code(data, self._path, *args, **kwargs)


class _AwepatchSpecFinder(MetaPathFinder):
    def __init__(self, patches: dict[str, list[CompiledPatch]]) -> None:
        super().__init__()
        self._patches = patches

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
        /,
    ) -> ModuleSpec | None:
        if fullname in self._patches:
            spec = PathFinder.find_spec(fullname, path, target)
            if spec is not None and spec.origin is not None:
                spec.loader = _AwepatchSourceLoader(
                    fullname,
                    spec.origin,
                    self._patches[fullname],
                )
                return spec
        return None


class ModulePatcher(AbstractPatcher):
    # Module is not thread-safe for patching. Please ensure no other thread
    # is importing the target module during patching.

    def __init__(self) -> None:
        self._patches: defaultdict[str, list[CompiledPatch]] = defaultdict(list)
        self._finder: _AwepatchSpecFinder | None = None

    def add_patch(
        self,
        module: str,
        /,
        target: IdentType | tuple[IdentType, ...],
        content: str | Sequence[ast.stmt],
        mode: Mode = "before",
    ) -> Self:
        self._patches[module].append(
            CompiledPatch(
                target=compile_idents(target, 0),
                stmts=load_stmts(content) if isinstance(content, str) else content,
                mode=mode,
            )
        )
        return self

    def apply(self) -> None:
        self._finder = _AwepatchSpecFinder(self._patches)
        sys.meta_path.insert(0, self._finder)
        for module in self._patches:
            if module in sys.modules:
                import importlib
                import warnings

                warnings.warn(
                    f"Module {module} is already imported before applying patches. "
                    "Reloading the module to apply patches. "
                    "The patches may not work as expected."
                    "Also, if the module has side effects on import, "
                    "those side effects will be triggered again upon reload.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                importlib.reload(sys.modules[module])

    def restore(self) -> None:
        if self._finder is not None:
            sys.meta_path.remove(self._finder)
            self._finder = None
