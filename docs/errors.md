# Errors

This page describes every error `python-cfg` can raise and when.

## `TypeError: \`@conditional_method\` must be used as a decorator and \`condition\` must be specified ...`

Raised when `@cfg` is used without a condition:

```python
@cfg  # error
def f(): ...


@cfg(...)  # ok
def f(): ...
```

or when a function is passed directly without a condition:

```python
cfg(f)  # TypeError
```

## `TypeError: None of the conditions is true for \`...\``

Raised at **class build time** when every implementation of a name has a
false condition. The qualname names the affected function.

!!! note "Version difference"

    On CPython < 3.12 this error is wrapped by the interpreter:
    `RuntimeError: Error calling __set_name__ on 'cfg._TypeErrorRaiser' ...`
    with the `TypeError` attached as `__cause__`. On 3.12+ the `TypeError`
    propagates directly (with the wrapper text as a note).

## `TypeError: Error calling \`condition\` for \`...\`: ...`

Raised when a **callable condition** raises `TypeError`; the original error
is embedded in the message. Other exceptions from the condition (e.g.
`ValueError`) propagate **unchanged**.

## `TypeError: decorators must be a sequence`

Raised by `@cfg_attr` when `decorators` is not a sequence (e.g. `42`).

## `ValueError: \`condition\` is required ...`

Raised by `@cfg_attr` when used as a factory with no condition:

```python
cfg_attr()  # ValueError
cfg_attr(condition=None)  # ValueError
```

## `TypeError` from calling a disabled function

When `@cfg_attr(condition=False)` (or a false `@cfg`) leaves a
`TypeErrorRaiser` in place, calling the name raises:

```python
@cfg_attr(condition=False, decorators=[])
def disabled():
    return 1


disabled()  # TypeError: None of the conditions is true for ...
```

## Debug

Enable debug logging to trace decoration:

```bash
export __conditional_method_debug__=true
python your_app.py   # "conditional_method - DEBUG - cm: decorating ..."
```
