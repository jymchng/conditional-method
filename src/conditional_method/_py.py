"""Pure-Python fallback implementation of conditional-method.

Used automatically by :mod:`conditional_method` when the C extension
(``conditional_method._c``) cannot be imported (e.g. an exotic platform
without a prebuilt wheel).  It mirrors the C extension's observable API:

- ``cfg`` / ``cm`` / ``if_``: conditional method/decorator selection.
- ``cfg_attr``: conditionally apply extra decorators.
- ``assert_all_true`` / ``_get_failed`` / ``pending_failures``: eager
  validation of decorated names.

The cache is a plain dict keyed by qualified name; winners are held strongly
(the fallback is for correctness/compatibility, not peak performance).
"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from functools import update_wrapper
from typing import Any, Callable

# module-global cache: qualname -> winning callable (or TypeErrorRaiser)
_cache: dict[str, Callable[..., Any]] = {}
_failed_qualnames: set[str] = set()
_debug = False


class _TypeErrorRaiser:
    """Stand-in for the C extension's TypeErrorRaiser: raises on call."""

    def __init__(self, qualname: str) -> None:
        self.qualname = qualname

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(
            f"No condition is true for {self.qualname} (conditional-method)"
        )

    def __repr__(self) -> str:
        return f"<TypeErrorRaiser {self.qualname}>"


def _get_mod_qual_func_name(func: Callable[..., Any]) -> str:
    qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", None)
    if not isinstance(qualname, str):
        qualname = "?"
    module = getattr(func, "__module__", None)
    if module:
        return f"{module}.{qualname}"
    return qualname


def debug_enabled() -> bool:
    return _debug


def debug(message: Any) -> None:
    if _debug:
        print(message)


def _get_failed() -> list[str]:
    return sorted(_failed_qualnames)


def pending_failures() -> list[str]:
    return _get_failed()


def assert_all_true() -> None:
    from conditional_method import ConditionFailureError

    failed = _get_failed()
    if failed:
        joined = ", ".join(failed)
        raise ConditionFailureError(
            f"No condition is true for {len(failed)} decorated name(s): {joined}",
            failed,
        )


def _resolve(condition: Any, func: Callable[..., Any]) -> bool:
    if condition is True:
        return True
    if condition is False:
        return False
    if callable(condition):
        return bool(condition(func))
    return bool(condition)


def _decorate(func: Callable[..., Any], condition: Any) -> Callable[..., Any]:
    qualname = _get_mod_qual_func_name(func)
    if _resolve(condition, func):
        _cache[qualname] = func
        _failed_qualnames.discard(qualname)
        return func
    raiser = _TypeErrorRaiser(qualname)
    _cache[qualname] = raiser
    _failed_qualnames.add(qualname)
    return raiser


def cfg(func: Callable[..., Any] | None = None, *, condition: Any = True) -> Any:
    """Conditional method/decorator selection (pure-Python fallback)."""
    if func is None:
        return lambda f: _decorate(f, condition)
    return _decorate(func, condition)


def cm(func: Callable[..., Any] | None = None, *, condition: Any = True) -> Any:
    return cfg(func, condition=condition)


def if_(func: Callable[..., Any] | None = None, *, condition: Any = True) -> Any:
    return cfg(func, condition=condition)


def cfg_attr(
    func: Callable[..., Any] | None = None,
    *,
    condition: Any = True,
    decorators: Sequence[Callable[..., Any]] = (),
) -> Any:
    """Conditionally apply extra decorators when ``condition`` is true."""
    if func is None:
        return lambda f: cfg_attr(f, condition=condition, decorators=decorators)

    qualname = _get_mod_qual_func_name(func)
    if not _resolve(condition, func):
        raiser = _TypeErrorRaiser(qualname)
        _cache[qualname] = raiser
        _failed_qualnames.add(qualname)
        return raiser

    result = func
    for deco in decorators:
        result = deco(result)
    # preserve identity metadata best-effort
    with contextlib.suppress(Exception):
        update_wrapper(result, func)
    _cache[qualname] = result
    _failed_qualnames.discard(qualname)
    return result


__all__ = [
    "cfg",
    "cm",
    "if_",
    "cfg_attr",
    "assert_all_true",
    "pending_failures",
    "_get_failed",
    "_get_mod_qual_func_name",
    "debug",
    "debug_enabled",
]
