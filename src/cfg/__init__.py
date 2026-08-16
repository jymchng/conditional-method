"""python-cfg: conditional method/decorator selection.

Public API::

    from cfg import cm, cfg, if_, conditional_method, cfg_attr

The performance-critical implementation lives in the C extension module
``cfg._c``; ``cfg._py_lib`` is the pure-Python reference implementation
used as a fallback when the extension is not built.
"""

try:  # pragma: no cover - depends on build
    from ._c import (
        conditional_method,
        if_,
        cm,
        cfg_attr,
        _get_mod_qual_func_name,
        cfg,
    )
except ImportError:  # pragma: no cover - fallback to pure Python
    from ._py_lib import (
        conditional_method,
        if_,
        cm,
        cfg_attr,
        _get_mod_qual_func_name,
        cfg,
    )

__all__ = [
    "conditional_method",
    "if_",
    "cm",
    "_get_mod_qual_func_name",
    "cfg_attr",
    "cfg",
]
