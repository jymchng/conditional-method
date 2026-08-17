# API Reference

The entire implementation is a C extension (`conditional_method._c`); `cfg` is a thin
import shim.

## `cfg` module

```python
from conditional_method import (
    cfg,
    if_,
    cm,
    cfg_attr,
    assert_all_true,
    _get_failed,
    debug,
    debug_enabled,
)
```

### `@cfg(condition=...)`

Conditional method selection. Aliases: `@cm`, `@if_`
— all three are the **same object** (`cm is if_ is cfg`
is `True`).

- `condition: bool | Callable[[Callable], bool]` — required.
- Use as a factory (`@cfg(condition=...)`) or directly
  (`cfg(func, condition=...)`).

### `@cfg_attr(condition=..., decorators=[...])`

Conditionally apply decorators.

- `condition: bool | Callable[[Callable], bool]` — required.
- `decorators: Sequence[Callable]` — applied in order when true.

### `debug(message)` / `debug_enabled() -> bool`

Opt-in C debug logging, gated by the `__conditional_method_debug__`
environment variable (any value other than `"false"` enables it).

```bash
export __conditional_method_debug__=true
```

### `_get_mod_qual_func_name(func) -> str`

Internal helper returning `module.qualname` for a function, unwrapping
`__wrapped__` / `__func__` / `fget` as needed. Raises `TypeError` when no
name can be determined.

### `assert_all_true() -> None`

Eager module-level validation: raises `TypeError` naming **every** decorated
name whose condition is false (i.e. that ended up as a `_TypeErrorRaiser`
with no `condition=True` winner). Returns `None` when all conditions are
true.

Call it as the last line of a config/feature-flag module to fail fast at
import time instead of at first call:

```python
from conditional_method import cfg, assert_all_true


@cfg(condition=ENABLE_FEATURE_A)
def feature_a(): ...


@cfg(condition=ENABLE_FEATURE_B)
def feature_b(): ...


assert_all_true()  # raises TypeError at import if any feature is disabled
```

### `_get_failed() -> list[str]`

Returns the list of qualified names whose cached value is a `_TypeErrorRaiser`
(empty when all conditions are true). Useful for introspection and tests; it
is what `assert_all_true()` checks under the hood.

## `conditional_method._c` internals

Exposed for testing only (names prefixed with `_` are not part of the
public API):

| Name | Purpose |
| --- | --- |
| `_cm_cache` / `_cfg_attr_cache` | module-level implementation caches |
| `_TypeErrorRaiser` | placeholder object raising `TypeError` on call/`__set_name__` |
| `_CfgCallable` | callable heap type wrapping the module aliases (`cm._cache`) |
| `_raise_exec` | create a `_TypeErrorRaiser` |
| `_cm_wrapper` / `cfg_attr_wrapper` | internal decorator wrappers |
| `set_alloc_fail_count` | **test-only** (`PY_CFG_TESTING` builds) allocation-failure injection |

## Errors

| Situation | Raised |
| --- | --- |
| `@cfg` with no condition | `TypeError` |
| `@cfg` used without brackets | `TypeError` |
| no condition true at class build | `TypeError: None of the conditions is true for ...` |
| condition callable raises `TypeError` | `TypeError: Error calling \`condition\` for ...` |
| `cfg_attr` with a non-sequence `decorators` | `TypeError: decorators must be a sequence` |
| `cfg_attr` with no condition | `ValueError` / `TypeError` |

See [Errors](errors.md) for details.
