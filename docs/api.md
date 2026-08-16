# API Reference

The entire implementation is a C extension (`cfg._c`); `cfg` is a thin
import shim.

## `cfg` module

```python
from cfg import cfg, if_, cm, conditional_method, cfg_attr, debug, debug_enabled
```

### `@cfg(condition=...)`

Conditional method selection. Aliases: `@if_`, `@cm`, `@conditional_method`
— all four are the **same object** (`cm is if_ is conditional_method is cfg`
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

## `cfg._c` internals

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
