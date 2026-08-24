"""cg — razor alias for cogym_kernel (zero breaking)."""
import sys as _sys
import importlib as _imp
import os as _os

_ALIASES = {
    ".k": ".kernel",
    ".xp": ".experience",
    ".orc": ".orchestration",
    ".sci": ".science",
    ".w": ".worlds",
}
# physical shims that should NOT be aliased (let filesystem handle them)
_PHYSICAL = {"cg.cli", "cg.executors"}

class _CgLoader:
    def find_spec(self, fullname, path, target=None):
        if fullname in _PHYSICAL:
            return None
        if not (fullname == "cg" or fullname.startswith("cg.")):
            return None
        if fullname == "cg":
            return None
        suffix = fullname[2:]
        for short, long in _ALIASES.items():
            if suffix == short or suffix.startswith(short + "."):
                suffix = suffix.replace(short, long, 1)
                break
        real = "cogym_kernel" + suffix
        try:
            mod = _imp.import_module(real)
            _sys.modules[fullname] = mod
            return mod.__spec__
        except ModuleNotFoundError:
            return None

_sys.meta_path.insert(0, _CgLoader())
try:
    __version__ = _imp.import_module("cogym_kernel").__version__
except Exception:
    __version__ = "0.1.0"
