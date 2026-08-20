"""conditional-method: conditional method/decorator selection.

Public API::

    from conditional_method import cfg, cm, if_, cfg_attr

The implementation is a C extension module (``conditional_method._c``) built
with the Limited API (abi3, cp39+) so a single wheel covers CPython 3.9-3.14
and wasm/Emscripten.  ``import conditional_method`` requires the C extension;
there is no pure-Python fallback.
"""

from importlib.metadata import PackageNotFoundError, version

from ._c import (
    _get_failed,
    _get_mod_qual_func_name,
    assert_all_true,
    cfg,
    cfg_attr,
    cm,
    debug,
    debug_enabled,
    if_,
)


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
    return _get_failed()


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
