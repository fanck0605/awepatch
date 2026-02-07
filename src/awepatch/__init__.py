from __future__ import annotations

from awepatch._function import FunctionPatcher
from awepatch._module import ModulePatcher
from awepatch._utils import AbstractPatcher, Ident
from awepatch._version import __commit_id__, __version__, __version_tuple__

__all__ = (
    "__commit_id__",
    "__version__",
    "__version_tuple__",
    "Ident",
    "AbstractPatcher",
    "ModulePatcher",
    "FunctionPatcher",
)
