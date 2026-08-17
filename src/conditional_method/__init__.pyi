"""Type stubs for conditional_method's decorators (C extension).

The implementation is a C extension (`conditional_method._c`); these stubs
give editors/type checkers the precise call patterns via @overload:

  - Factory form:   @cfg(condition=True) def f(): ...      # returns the decorator
  - Direct form:    cfg(func, condition=True)              # applies immediately
  - Same for cfg_attr with decorators=[...]
  - cm / if_ are aliases of cfg.

`condition` is either a bool (static selection) or a callable that receives
the decorated function and returns a bool (evaluated at decoration time).
When False, the decorated function is replaced by a TypeErrorRaiser that
raises TypeError on call/__set_name__ (a build-time guard, not a drop).

Note: cfg_attr applies arbitrary decorators, which may transform the
function's type; we preserve the original type as a best-effort (the C
extension keeps the wrapped callable).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar, overload

_F = TypeVar("_F", bound=Callable[..., Any])

Condition = bool | Callable[[Callable[..., Any]], bool]

@overload
def cfg(func: _F, *, condition: Condition) -> _F: ...
@overload
def cfg(func: _F, condition: Condition) -> _F: ...
@overload
def cfg(*, condition: Condition) -> Callable[[_F], _F]: ...
@overload
def cfg(condition: Condition) -> Callable[[_F], _F]: ...
@overload
def cfg_attr(
    func: _F,
    *,
    condition: Condition,
    decorators: Sequence[Callable[..., Any]] = ...,
) -> _F: ...
@overload
def cfg_attr(
    func: _F,
    condition: Condition,
    decorators: Sequence[Callable[..., Any]] = ...,
) -> _F: ...
@overload
def cfg_attr(
    *,
    condition: Condition,
    decorators: Sequence[Callable[..., Any]] = ...,
) -> Callable[[_F], _F]: ...

# Aliases: cm and if_ are the same object as cfg.
cm = cfg
if_ = cfg

def _get_mod_qual_func_name(func: Any) -> str: ...
def debug(message: Any) -> None: ...
def debug_enabled() -> bool: ...
def assert_all_true() -> None: ...
def _get_failed() -> list[str]: ...

# The C extension submodule (implementation internals; not part of the
# public API but importable, e.g. by the legacy `cfg` shim). No stub is
# shipped for it; treat it as opaque.
_c: Any

# Set at runtime from importlib.metadata (the distribution version).
__version__: str

__all__ = [
    "cfg",
    "cfg_attr",
    "cm",
    "if_",
    "_get_mod_qual_func_name",
    "assert_all_true",
    "_get_failed",
    "debug",
    "debug_enabled",
]
