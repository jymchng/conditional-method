# FAQ

## Why is it called `conditional-method` but I import `cfg`?

`conditional-method` is the PyPI distribution name; `cfg` is the import module —
same convention as e.g. `beautifulsoup4` → `bs4`.

## Is there a pure-Python fallback?

No. The entire implementation is the C extension `cfg._c`; the package
contains only a thin `__init__.py` shim. There is deliberately no pure
Python implementation to maintain.

## Why abi3?

abi3 (the Python Limited API / stable ABI) lets one wheel (`cp39-abi3`)
run on **every** CPython 3.9+ release. Users on 3.14 get a wheel built for
3.9 without any rebuild, and maintainers publish far fewer artifacts.

## What happens when two conditions are true?

The **last** true condition wins (source order). Only that implementation
survives on the class.

## What happens when no condition is true?

Class creation fails with
`TypeError: None of the conditions is true for ...` (wrapped in
`RuntimeError` by the interpreter on CPython < 3.13).

## Can conditions be dynamic?

Yes — pass a **callable** condition; it is evaluated lazily each time the
implementation is selected, so it can depend on runtime state.

## Does it work with `@property` / `@classmethod` / `@staticmethod`?

Yes — see [Usage](usage.md). Note the decorator ordering:

```python
@property
@cfg(condition=True)
def prop(self): ...
```

## Is it fast?

The selection happens once at class build time; calling the selected method
is a plain attribute lookup with zero overhead. See [Benchmarks](benchmarks.md).

## Does it have dependencies?

No runtime dependencies.

## How do I debug it?

Set `__conditional_method_debug__=true` (any value except `"false"`) to
enable the C debug logger:

```bash
export __conditional_method_debug__=true
```
