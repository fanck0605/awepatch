from __future__ import annotations

import ast
import pickle
import sys
from collections import defaultdict
from dataclasses import dataclass
from importlib.abc import MetaPathFinder, SourceLoader
from importlib.machinery import PathFinder

from awepatch._utils import (
    AWEPATCH_DEBUG,
    AbstractPatcher,
    CompiledPatches,
    IdentType,
    Mode,
    append_patch,
    apply_prepared_patches,
    compile_idents,
    find_matched_node,
    load_stmts,
    persist_patched_source,
    prepare_patches,
)

TYPE_CHECKING = False

if TYPE_CHECKING:
    import os
    from collections.abc import Buffer, Sequence
    from importlib.machinery import ModuleSpec
    from types import CodeType, ModuleType
    from typing import Self


@dataclass(slots=True)
class ModuleInfo:
    spec: ModuleSpec
    tree: ast.AST
    slines: Sequence[str]
    patches: CompiledPatches


class _AwepatchSourceLoader(SourceLoader):
    def __init__(
        self,
        fullname: str,
        origin: str,
        patches: CompiledPatches,
        pkl_tree: bytes,
    ) -> None:
        self._fullname = fullname
        self._origin = origin
        self._path = origin
        self._patches = patches
        self._pkl_tree = pkl_tree

    def get_filename(self, fullname: str) -> str:
        return self._origin

    def get_data(self, path: str) -> bytes:
        tree = pickle.loads(self._pkl_tree)
        prepared = prepare_patches(self._patches, tree)
        apply_prepared_patches(prepared)
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
    def __init__(self, modules: dict[str, ModuleSpec]) -> None:
        super().__init__()
        self._modules = modules

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
        /,
    ) -> ModuleSpec | None:
        return self._modules.get(fullname, None)


class ModulePatcher(AbstractPatcher):
    # Module is not thread-safe for patching. Please ensure no other thread
    # is importing the target module during patching.

    def __init__(self) -> None:
        self._modules: dict[str, ModuleInfo] = {}
        self._finder: _AwepatchSpecFinder | None = None

    def _get_module_info(self, module: str) -> ModuleInfo:
        if (module_info := self._modules.get(module)) is not None:
            return module_info

        spec = PathFinder.find_spec(module, None, None)
        if spec is None or spec.origin is None:
            raise ValueError(f"Module {module} not found")

        with open(spec.origin, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=spec.origin)
        slines = source.splitlines(keepends=True)
        patches: CompiledPatches = defaultdict(dict)
        spec.loader = _AwepatchSourceLoader(
            fullname=module,
            origin=spec.origin,
            patches=patches,
            pkl_tree=pickle.dumps(tree),
        )

        module_info = self._modules[module] = ModuleInfo(
            spec=spec,
            tree=tree,
            slines=slines,
            patches=patches,
        )
        return module_info

    def add_patch(
        self,
        module: str,
        /,
        target: IdentType | tuple[IdentType, ...],
        content: str | Sequence[ast.stmt],
        mode: Mode = "before",
    ) -> Self:
        module_info = self._get_module_info(module)
        ident = compile_idents(target, 0)
        location = find_matched_node(module_info.tree, module_info.slines, ident)
        if location is None:
            raise ValueError(f"Patch target {target} not found in {module}")
        append_patch(
            module_info.patches,
            location,
            load_stmts(content) if isinstance(content, str) else content,
            mode,
        )
        return self

    def apply(self) -> None:
        self._finder = _AwepatchSpecFinder(
            {module: info.spec for module, info in self._modules.items()}
        )
        sys.meta_path.insert(0, self._finder)
        for module in self._modules:
            if module in sys.modules:
                import warnings

                warnings.warn(
                    f"Module {module} is already imported before applying patches, "
                    "the patches may not work as expected!",
                    RuntimeWarning,
                    stacklevel=2,
                )

    def restore(self) -> None:
        if self._finder is not None:
            sys.meta_path.remove(self._finder)
            self._finder = None
