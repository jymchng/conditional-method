"""conditional-method: conditional method/decorator selection.

Public API::

    from cfg import cm, cfg, if_, conditional_method, cfg_attr

The entire implementation is a C extension module (``cfg._c``); there is no
pure-Python implementation. This package file is only an import shim.
"""

from importlib.metadata import PackageNotFoundError, version

from ._c import (
    _get_mod_qual_func_name,
    cfg,
    cfg_attr,
    cm,
    conditional_method,
    debug,
    debug_enabled,
    if_,
)

try:
    __version__: str = version("conditional-method")
except PackageNotFoundError:  # pragma: no cover - editable/source installs
    __version__ = "0.0.0+unknown"

__all__ = [
    "conditional_method",
    "if_",
    "cm",
    "_get_mod_qual_func_name",
    "cfg_attr",
    "cfg",
    "debug",
    "debug_enabled",
]
