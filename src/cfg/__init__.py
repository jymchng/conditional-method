"""Deprecated compatibility alias for ``conditional_method``.

The canonical import module is ``conditional_method`` (distribution:
``conditional-method``). ``cfg`` is kept as a thin re-export shim so code
written against the earlier name keeps working; new code should import
from ``conditional_method``.
"""

from conditional_method import *  # noqa: F401,F403
from conditional_method import (
    __all__,  # noqa: F401  (re-export)
    __version__,  # noqa: F401  (re-export)
    _c,  # noqa: F401  (expose conditional_method._c)
)
