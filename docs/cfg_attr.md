# Usage: `@cfg_attr`

`@cfg_attr` conditionally applies a **chain of decorators** to a function or
method — only when the condition is true.

```python
from conditional_method import cfg_attr


@cfg_attr(
    condition=os.environ.get("FEATURE_FLAG") == "enabled",
    decorators=[log_calls, cache_result],
)
def experimental(value):
    return value * 2
```

## Semantics

- **Condition true** → the decorators are applied **in order** (left to
  right; `decorators[0]` becomes the outermost wrapper) and the decorated
  function is returned and cached by qualname.
- **Condition false** → a `TypeErrorRaiser` is returned; calling the
  decorated name raises `TypeError` (unless a previously-true condition for
  the same qualname is in the cache).
- **Callable conditions** are supported and evaluated per function.
- **`decorators` must be a sequence**; a non-sequence raises `TypeError`
  (`decorators must be a sequence`).

## Factory form

Like `@cfg`, `@cfg_attr` can be used as a factory or directly:

```python
# factory
deco = cfg_attr(condition=ENV == "prod", decorators=[log_calls])

# direct
f = cfg_attr(f, condition=ENV == "prod", decorators=[log_calls])
```

## Feature flags

A common pattern is toggling decorators by environment:

```python
@cfg_attr(
    condition=os.environ.get("FEATURE_FLAG") == "enabled",
    decorators=[log_calls, cache_result],
)
def experimental(input_value): ...
```

When the flag is **off**, the function is replaced by a `TypeErrorRaiser`
and calls raise `TypeError` — the function is effectively disabled without
runtime branching.
