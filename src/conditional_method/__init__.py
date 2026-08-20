"""conditional-method: conditional method/decorator selection.

Public API::

    from conditional_method import cfg, cm, if_, cfg_attr

The primary implementation is a C extension module (``conditional_method._c``)
built with the Limited API (abi3, cp39+) so a single wheel covers CPython
3.9-3.14 and wasm/Emscripten.  A pure-Python fallback (``conditional_method._py``)
with the same API is used automatically when the C extension is unavailable
(e.g. an exotic platform without a wheel), so ``import conditional_method``
never fails outright.
"""

from importlib.metadata import PackageNotFoundError, version

# #10: pure-Python fallback with the same public API, used when the C
# extension cannot be imported.
try:
    from . import _c as _impl  # type: ignore
except ImportError:  # pragma: no cover - only reachable when no C wheel exists
    from . import _py as _impl  # type: ignore


# #7: friendly failure API.  ``pending_failures()`` is the public alias of the
# private ``_get_failed()``; ``ConditionFailureError`` carries the failing
# qualnames on a ``TypeError`` subclass so callers can catch and inspect it.
class ConditionFailureError(TypeError):
    """Raised by :func:`assert_all_true` when some decorated names have no
    true condition.

    Attributes:
        failed: the list of decorated qualnames with no true winner.
    """

    def __init__(self, message: str, failed: list[str]) -> None:
        super().__init__(message)
        self.failed = list(failed)


def pending_failures() -> list[str]:
    """Return the qualnames of decorated names that currently have no true
    condition (i.e. would raise on call).  Empty list means all good."""
    return _impl._get_failed()


def assert_all_true() -> None:
    """Raise :class:`ConditionFailureError` if any decorated name has no true
    condition; otherwise return None."""
    failed = pending_failures()
    if failed:
        joined = ", ".join(failed)
        raise ConditionFailureError(
            f"No condition is true for {len(failed)} decorated name(s): {joined}",
            failed,
        )


# Bind the underlying implementation's exports onto this module.
cfg = _impl.cfg
cm = _impl.cm
if_ = _impl.if_
cfg_attr = _impl.cfg_attr
debug = _impl.debug
debug_enabled = _impl.debug_enabled
_get_failed = _impl._get_failed
_get_mod_qual_func_name = _impl._get_mod_qual_func_name

try:
    __version__: str = version("conditional-method")
except PackageNotFoundError:  # pragma: no cover - editable/source installs
    __version__ = "0.0.0+unknown"

__all__ = [
    "cfg",
    "if_",
    "cm",
    "_get_mod_qual_func_name",
    "assert_all_true",
    "pending_failures",
    "ConditionFailureError",
    "_get_failed",
    "cfg_attr",
    "debug",
    "debug_enabled",
]
